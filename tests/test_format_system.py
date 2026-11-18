import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from reelsyntax.formats import (
    FormatRunner,
    discover_formats,
    format_schema,
    load_runner_state,
    scaffold_format,
    validate_format_directory,
    validate_format_manifest,
)
from reelsyntax.prompt import OfflineRulesProvider

REPO_ROOT = Path(__file__).resolve().parents[1]


class FormatSystemTests(unittest.TestCase):
    def test_published_format_schema_matches_generator(self) -> None:
        published = json.loads((REPO_ROOT / "docs/schemas/format.v1.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(published, format_schema())

    def test_scaffold_and_reject_invalid_or_executable_formats(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            res = scaffold_format("sample-card", category="social", base_dir=root)
            self.assertTrue(res["valid"])
            fmt_dir = Path(res["path"])

            found = discover_formats(category="social", extra_roots=(root,))
            self.assertIn("sample-card", [f["id"] for f in found])

            base_manifest = json.loads((fmt_dir / "format.json").read_text(encoding="utf-8"))
            no_de = copy.deepcopy(base_manifest)
            del no_de["title"]["de"]
            with self.assertRaisesRegex(ValueError, "must provide 'en', 'tr', and 'de'"):
                validate_format_manifest(no_de)

            ungated_hero = copy.deepcopy(base_manifest)
            ungated_hero["steps"] = [{"id": "hero", "type": "render", "profile": "hero"}]
            with self.assertRaisesRegex(ValueError, "preceding approval gate"):
                validate_format_manifest(ungated_hero)

            evil_script = fmt_dir / "references/hook.py"
            evil_script.write_text("VALUE = 1\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "forbidden executable/code file"):
                validate_format_directory(fmt_dir)
            evil_script.unlink()
            self.assertTrue(validate_format_directory(fmt_dir)["valid"])

    def test_runner_gates_hero_protection_edit_invalidation_and_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fmt_res = scaffold_format("focus-reel", category="social", base_dir=root / "formats")
            manifest = fmt_res["manifest"]
            runner = FormatRunner(manifest, OfflineRulesProvider(), dry_run_render=True)

            proj = root / "project"
            runner.initialize_project(proj, "5 focus tips, 9:16, 10s, calm colors", seed=77)

            paused = runner.run(proj, auto_approve=False)
            self.assertEqual(paused["status"], "awaiting_approval")
            self.assertEqual(paused["pending_gate"], "idea")
            self.assertNotIn("hero", paused["completed_steps"])

            tampered = load_runner_state(proj)
            tampered["current_step_index"] = next(i for i, s in enumerate(manifest["steps"]) if s["id"] == "hero")
            (proj / ".formats/state.json").write_text(json.dumps(tampered), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Hero render blocked"):
                runner.run(proj, auto_approve=False)

            runner.initialize_project(proj, "5 focus tips, 9:16, 10s, calm colors", seed=77)
            runner.run(proj, auto_approve=False)
            runner.approve_pending_gate(proj)
            at_script = runner.run(proj, auto_approve=False)
            self.assertEqual(at_script["pending_gate"], "script")

            idea_seed_before = at_script["step_seeds"]["idea"]
            runner.edit_step(proj, "script", "make the opening punchier")
            after_edit = load_runner_state(proj)
            self.assertIn("idea", after_edit["approvals"])
            self.assertNotIn("script", after_edit["completed_steps"])
            self.assertEqual(after_edit["step_seeds"]["idea"], idea_seed_before)

            finished = runner.run(proj, auto_approve=True)
            self.assertEqual(finished["status"], "completed")
            self.assertIn("hero", finished["completed_steps"])
            self.assertIn("qc", finished["completed_steps"])
            self.assertTrue((proj / "reel.json").is_file())

    def test_cli_formats_new_validate_show_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / "custom-formats"
            env = {"REELSYNTAX_FORMATS_DIR": str(base_dir), "PATH": ""}
            new_res = subprocess.run(
                [sys.executable, "-m", "reelsyntax", "formats", "new", "demo-format", "--base-dir", str(base_dir), "--json"],
                capture_output=True,
                text=True,
                env={**subprocess.os.environ, **env},
                timeout=20,
                check=False,
            )
            self.assertEqual(new_res.returncode, 0, new_res.stderr)
            val_res = subprocess.run(
                [sys.executable, "-m", "reelsyntax", "formats", "validate", "demo-format", "--json"],
                capture_output=True,
                text=True,
                env={**subprocess.os.environ, **env},
                timeout=20,
                check=False,
            )
            self.assertEqual(val_res.returncode, 0, val_res.stderr)
            self.assertTrue(json.loads(val_res.stdout)["result"]["valid"])


if __name__ == "__main__":
    unittest.main()
