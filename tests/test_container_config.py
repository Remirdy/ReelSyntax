import errno
import json
from pathlib import Path
import re
import shutil
import tempfile
import unittest
from unittest.mock import patch

from ReelSyntax_Skills.tools import registry as skills_registry

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = REPO_ROOT / "Dockerfile"
DOCKERIGNORE = REPO_ROOT / ".dockerignore"
COMPOSE = REPO_ROOT / "docker-compose.yml"
DEVCONTAINER = REPO_ROOT / ".devcontainer/devcontainer.json"
WORKFLOW = REPO_ROOT / ".github/workflows/container.yml"
DOCS = REPO_ROOT / "docs/containers.md"
PUBLISH_CONDITION = "if: startsWith(github.ref, 'refs/tags/v') || github.event_name == 'workflow_dispatch'"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def dockerfile_instructions(text: str) -> list[tuple[str, str]]:
    joined = re.sub(r"\\\r?\n", " ", text)
    rows = []
    for line in joined.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        keyword, _, rest = stripped.partition(" ")
        rows.append((keyword.upper(), rest.strip()))
    return rows


def stages(text: str) -> dict[str, list[tuple[str, str]]]:
    found: dict[str, list[tuple[str, str]]] = {}
    current = None
    for keyword, rest in dockerfile_instructions(text):
        if keyword == "FROM":
            match = re.search(r"\bAS\s+([a-z0-9_-]+)\s*$", rest, re.IGNORECASE)
            current = match.group(1).lower() if match else rest
            found[current] = []
        elif current is not None:
            found[current].append((keyword, rest))
    return found


def workflow_jobs(text: str) -> dict[str, str]:
    body = text.split("\njobs:\n", 1)[1]
    jobs: dict[str, str] = {}
    current = None
    for line in body.splitlines():
        match = re.fullmatch(r"  ([A-Za-z0-9_-]+):\s*", line)
        if match:
            current = match.group(1)
            jobs[current] = ""
        elif current is not None:
            jobs[current] += line + "\n"
    return jobs


class DockerfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = read(DOCKERFILE)
        self.stages = stages(self.text)

    def test_base_image_is_pinned_python_312_slim(self) -> None:
        match = re.search(r"^ARG PYTHON_IMAGE=(\S+)$", self.text, re.MULTILINE)
        self.assertIsNotNone(match)
        image = match.group(1)
        self.assertRegex(image, r"^python:3\.12\.\d+-slim-[a-z]+@sha256:[0-9a-f]{64}$")
        froms = [rest for keyword, rest in dockerfile_instructions(self.text) if keyword == "FROM"]
        self.assertEqual(froms[0], "${PYTHON_IMAGE} AS base")
        for rest in froms[1:]:
            self.assertRegex(rest, r"^base AS [a-z]+$")
        self.assertNotIn(":latest", self.text)

    def test_stages_and_default_target(self) -> None:
        self.assertEqual(list(self.stages), ["base", "build", "dev", "runtime"])

    def test_base_installs_ffmpeg_without_recommends_and_cleans_lists(self) -> None:
        runs = " ".join(rest for keyword, rest in self.stages["base"] if keyword == "RUN")
        self.assertIn("--no-install-recommends", runs)
        self.assertRegex(runs, r"\bffmpeg\b")
        self.assertIn("rm -rf /var/lib/apt/lists/*", runs)

    def test_runtime_installs_wheel_with_pillow_render_extra(self) -> None:
        runtime = self.stages["runtime"]
        runs = " ".join(rest for keyword, rest in runtime if keyword == "RUN")
        self.assertIn('"${wheel}[render]"', runs)
        self.assertIn("COPY --from=build /wheels /wheels", " ".join(f"{k} {r}" for k, r in runtime))
        pyproject = read(REPO_ROOT / "pyproject.toml")
        self.assertRegex(pyproject, r'render = \["Pillow==[0-9.]+"\]')

    def test_runtime_is_non_root_with_workspace_and_cli_entrypoint(self) -> None:
        runtime = self.stages["runtime"]
        users = [rest for keyword, rest in runtime if keyword == "USER"]
        self.assertEqual(len(users), 1)
        self.assertNotIn(users[0].split(":")[0], {"root", "0"})
        self.assertIn(("WORKDIR", "/workspace"), runtime)
        self.assertIn(("VOLUME", '["/workspace"]'), runtime)
        entrypoints = [rest for keyword, rest in runtime if keyword == "ENTRYPOINT"]
        self.assertEqual(len(entrypoints), 1)
        self.assertEqual(json.loads(entrypoints[0]), ["python3", "-m", "reelsyntax"])
        keywords = [keyword for keyword, _ in runtime]
        self.assertLess(keywords.index("USER"), keywords.index("ENTRYPOINT"))
        self.assertGreater(keywords.index("USER"), max(i for i, k in enumerate(keywords) if k == "RUN"))

    def test_build_stage_copies_only_packaging_inputs(self) -> None:
        copies = [rest for keyword, rest in self.stages["build"] if keyword == "COPY"]
        sources = {token for rest in copies for token in rest.split()[:-1]}
        self.assertEqual(sources, {"pyproject.toml", "README.md", "LICENSE", "MANIFEST.in", "reelsyntax", "ReelSyntax_Skills"})
        for source in sources:
            self.assertTrue((REPO_ROOT / source).exists(), source)

    def test_no_secrets_or_network_tools_in_runtime(self) -> None:
        self.assertNotRegex(self.text, r"(?i)\b(api[_-]?key|token|password)\s*=")
        runtime_runs = " ".join(rest for keyword, rest in self.stages["runtime"] if keyword == "RUN")
        self.assertNotIn("curl", runtime_runs)
        self.assertNotIn("sudo", runtime_runs)


class DockerignoreTests(unittest.TestCase):
    def test_excludes_vcs_state_and_secrets_but_keeps_package_inputs(self) -> None:
        patterns = {line.strip() for line in read(DOCKERIGNORE).splitlines() if line.strip()}
        for required in [".git", ".venv", ".env", ".env.*", "integrations", "**/.reelsyntax", "**/__pycache__"]:
            self.assertIn(required, patterns)
        for kept in ["reelsyntax", "ReelSyntax_Skills", "pyproject.toml", "README.md", "LICENSE", "MANIFEST.in", "ReelSyntax_Skills/tests"]:
            self.assertNotIn(kept, patterns)
        self.assertNotIn("Dockerfile", patterns)


class ComposeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = read(COMPOSE)

    def test_services_use_runtime_target_and_workspace_mount(self) -> None:
        self.assertNotIn("\t", self.text)
        self.assertRegex(self.text, r"(?m)^services:$")
        self.assertRegex(self.text, r"(?m)^  reelsyntax:$")
        self.assertRegex(self.text, r"(?m)^  mcp:$")
        self.assertIn("image: ghcr.io/remirdy/reelsyntax:", self.text)
        self.assertIn("target: runtime", self.text)
        self.assertIn("target: /workspace", self.text)
        self.assertIn('command: ["mcp", "--workspace", "/workspace"]', self.text)

    def test_hardened_offline_defaults(self) -> None:
        for snippet in ["network_mode: none", "read_only: true", "no-new-privileges:true", "- ALL"]:
            self.assertIn(snippet, self.text)
        self.assertNotRegex(self.text, r"(?m)^\s*privileged:\s*true")
        self.assertNotIn("/var/run/docker.sock", self.text)


class DevcontainerTests(unittest.TestCase):
    def test_devcontainer_builds_dev_target_as_non_root(self) -> None:
        config = json.loads(read(DEVCONTAINER))
        self.assertEqual(config["build"]["dockerfile"], "../Dockerfile")
        self.assertEqual(config["build"]["context"], "..")
        self.assertEqual(config["build"]["target"], "dev")
        self.assertNotIn(config["remoteUser"], {"root", "0"})
        self.assertIn("pip install --user -e .", config["postCreateCommand"])
        self.assertIn("charliermarsh.ruff", config["customizations"]["vscode"]["extensions"])
        dev_stage = stages(read(DOCKERFILE))["dev"]
        users = [rest for keyword, rest in dev_stage if keyword == "USER"]
        self.assertEqual(users, [config["remoteUser"]])


class ContainerWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = read(WORKFLOW)
        self.jobs = workflow_jobs(self.text)

    def test_triggers_and_default_permissions(self) -> None:
        self.assertRegex(self.text, r"(?m)^  pull_request:")
        self.assertRegex(self.text, r"(?m)^  workflow_dispatch:")
        self.assertIn("tags: ['v*']", self.text)
        top = self.text.split("\njobs:\n", 1)[0]
        self.assertRegex(top, r"(?m)^permissions:\n  contents: read$")
        self.assertNotIn("packages: write", top)

    def test_verify_job_builds_and_runs_doctor_without_registry_access(self) -> None:
        verify = self.jobs["verify"]
        self.assertNotIn("if:", verify.split("steps:", 1)[0])
        self.assertIn("docker build --target runtime", verify)
        self.assertRegex(verify, r"docker run --rm .*python3 -m reelsyntax doctor --json|docker run --rm .*--entrypoint python3 \S+ -m reelsyntax doctor --json")
        self.assertIn("docker compose config", verify)
        self.assertIn("--target dev", verify)
        for forbidden in ["docker push", "docker login", "packages: write", "secrets."]:
            self.assertNotIn(forbidden, verify)

    def test_publish_is_gated_to_tags_or_manual_dispatch(self) -> None:
        self.assertEqual(set(self.jobs), {"verify", "publish"})
        publish = self.jobs["publish"]
        header = publish.split("steps:", 1)[0]
        self.assertIn("needs: verify", header)
        self.assertIn(PUBLISH_CONDITION, header)
        self.assertIn("packages: write", header)
        self.assertIn("docker push --all-tags ghcr.io/remirdy/reelsyntax", publish)
        self.assertEqual(self.text.count("docker push"), 1)
        self.assertEqual(self.text.count("docker login"), 1)
        self.assertIn("--password-stdin", publish)

    def test_actions_are_pinned_to_full_commit_shas(self) -> None:
        uses = re.findall(r"uses:\s*(\S+)", self.text)
        self.assertTrue(uses)
        for ref in uses:
            self.assertRegex(ref, r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")


class ContainerDocsTests(unittest.TestCase):
    def test_docs_cover_usage_and_are_linked(self) -> None:
        text = read(DOCS)
        for snippet in ["docker compose", "ghcr.io/remirdy/reelsyntax", "Codespaces", "/workspace", "doctor --json", "REELSYNTAX_UID"]:
            self.assertIn(snippet, text)
        self.assertIn("containers.md", read(REPO_ROOT / "mkdocs.yml"))


class ReadOnlyContainerRuntimeTests(unittest.TestCase):
    def test_load_index_survives_erofs_when_freshness_cache_is_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample = skills_registry.ROOT / "library/render/frame-clock/SKILL.md"
            target = root / "library/render/frame-clock/SKILL.md"
            target.parent.mkdir(parents=True)
            target.write_bytes(sample.read_bytes())
            skills_registry.atomic_json(root / "registry/relations.json", {"frame-clock": {"requires": []}})
            skills_registry.rebuild(root)
            shutil.rmtree(root / ".reelsyntax")

            def raise_erofs(*args, **kwargs):
                raise OSError(errno.EROFS, "Read-only file system")

            with patch.object(skills_registry, "atomic_json", side_effect=raise_erofs):
                doc = skills_registry.load_index(root)
            self.assertEqual(len(doc["skills"]), 1)
            self.assertIn("not writable", doc["maintenance_warning"])


if __name__ == "__main__":
    unittest.main()
