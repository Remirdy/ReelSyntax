#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import tomllib

REPO_ROOT = Path(__file__).resolve().parents[1]
SEMVER_RE = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:[-.]?(?P<pre>(?:alpha|beta|rc|a|b|dev)[0-9A-Za-z.-]*))?$"
)


def is_prerelease_version(version: str) -> bool:
    cleaned = version.removeprefix("v")
    match = SEMVER_RE.fullmatch(cleaned)
    if match is None:
        raise ValueError(f"Invalid semantic version: {version!r}")
    return bool(match.group("pre"))


def read_package_versions(root: Path = REPO_ROOT) -> dict[str, str]:
    with (root / "pyproject.toml").open("rb") as handle:
        pyproject_version = str(tomllib.load(handle)["project"]["version"])
    init_text = (root / "reelsyntax/__init__.py").read_text(encoding="utf-8")
    init_match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", init_text)
    if init_match is None:
        raise ValueError("Missing __version__ in reelsyntax/__init__.py")
    server_doc = json.loads((root / "server.json").read_text(encoding="utf-8"))
    server_version = str(server_doc["version"])
    return {
        "pyproject": pyproject_version,
        "init": init_match.group(1),
        "server_json": server_version,
    }


def extract_changelog_section(changelog_text: str, version: str) -> str:
    cleaned = version.removeprefix("v")
    pattern = re.compile(rf"^## \[{re.escape(cleaned)}\][^\n]*\n", re.MULTILINE)
    start_match = pattern.search(changelog_text)
    if start_match is None:
        raise ValueError(f"CHANGELOG.md has no section for [{cleaned}]")
    rest = changelog_text[start_match.end():]
    next_heading = re.search(r"^(?:## \[|\[[^\]]+\]:\s*https?://)", rest, re.MULTILINE)
    body = rest[:next_heading.start()] if next_heading else rest
    stripped = body.strip()
    if not stripped:
        raise ValueError(f"CHANGELOG.md section [{cleaned}] is empty")
    return stripped + "\n"


def verify_release_metadata(root: Path = REPO_ROOT, tag: str | None = None) -> dict[str, object]:
    versions = read_package_versions(root)
    distinct = set(versions.values())
    if len(distinct) != 1:
        raise ValueError(f"Version mismatch across package metadata: {versions}")
    version = next(iter(distinct))
    prerelease = is_prerelease_version(version)
    if tag is not None:
        expected_tag = f"v{version}"
        if tag != expected_tag:
            raise ValueError(f"Git tag {tag!r} does not match package version {expected_tag!r}")
    changelog_text = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    notes = extract_changelog_section(changelog_text, version)
    server_doc = json.loads((root / "server.json").read_text(encoding="utf-8"))
    packages = server_doc.get("packages") or []
    expected_url_fragment = f"/releases/download/v{version}/reelsyntax.mcpb"
    if not packages or expected_url_fragment not in str(packages[0].get("identifier", "")):
        raise ValueError(f"server.json package identifier must reference {expected_url_fragment}")
    return {
        "version": version,
        "prerelease": prerelease,
        "notes_length": len(notes),
    }


def stamp_server_json(mcpb_path: Path, server_json_path: Path, output_path: Path | None = None) -> dict[str, object]:
    mcpb_file = Path(mcpb_path)
    if not mcpb_file.is_file() or mcpb_file.stat().st_size == 0:
        raise ValueError(f"Missing or empty MCP bundle: {mcpb_file}")
    digest_hex = hashlib.sha256(mcpb_file.read_bytes()).hexdigest()
    doc = json.loads(Path(server_json_path).read_text(encoding="utf-8"))
    if not doc.get("packages"):
        raise ValueError("server.json contains no packages array")
    doc["packages"][0]["fileSha256"] = digest_hex
    dest = Path(output_path) if output_path is not None else Path(server_json_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"fileSha256": digest_hex, "output": str(dest)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="release_prepare")
    sub = parser.add_subparsers(dest="command", required=True)

    ver = sub.add_parser("verify")
    ver.add_argument("--tag")
    ver.add_argument("--root", type=Path, default=REPO_ROOT)

    notes = sub.add_parser("notes")
    notes.add_argument("--version", required=True)
    notes.add_argument("--output", type=Path)
    notes.add_argument("--root", type=Path, default=REPO_ROOT)

    stamp = sub.add_parser("stamp-mcpb")
    stamp.add_argument("--mcpb", type=Path, required=True)
    stamp.add_argument("--server-json", type=Path, default=REPO_ROOT / "server.json")
    stamp.add_argument("--output", type=Path)

    pre = sub.add_parser("is-prerelease")
    pre.add_argument("--tag", required=True)

    args = parser.parse_args(argv)
    if args.command == "verify":
        print(json.dumps(verify_release_metadata(args.root, args.tag), indent=2))
        return 0
    if args.command == "notes":
        changelog_text = (args.root / "CHANGELOG.md").read_text(encoding="utf-8")
        section = extract_changelog_section(changelog_text, args.version)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(section, encoding="utf-8")
        else:
            sys.stdout.write(section)
        return 0
    if args.command == "stamp-mcpb":
        print(json.dumps(stamp_server_json(args.mcpb, args.server_json, args.output), indent=2))
        return 0
    if args.command == "is-prerelease":
        sys.stdout.write("true\n" if is_prerelease_version(args.tag) else "false\n")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
