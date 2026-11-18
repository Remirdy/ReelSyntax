#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import re
import subprocess

REPO_ROOT = Path(__file__).resolve().parents[1]
HEX_COLOR_RE = re.compile(r"^[0-9a-fA-F]{6}$")


def load_labels(path: Path = REPO_ROOT / ".github/labels.json") -> list[dict[str, str]]:
    items = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(items, list) or not items:
        raise ValueError("labels.json must be a non-empty list")
    seen: set[str] = set()
    validated: list[dict[str, str]] = []
    for entry in items:
        if not isinstance(entry, dict) or set(entry) != {"name", "color", "description"}:
            raise ValueError(f"Invalid label entry: {entry!r}")
        name = entry["name"]
        color = entry["color"]
        desc = entry["description"]
        if not isinstance(name, str) or not 1 <= len(name) <= 50 or name.lower() in seen:
            raise ValueError(f"Invalid or duplicate label name: {name!r}")
        if not isinstance(color, str) or not HEX_COLOR_RE.fullmatch(color):
            raise ValueError(f"Invalid 6-digit hex color for {name}: {color!r}")
        if not isinstance(desc, str) or not 1 <= len(desc) <= 100:
            raise ValueError(f"Invalid label description for {name}: {desc!r}")
        seen.add(name.lower())
        validated.append({"name": name, "color": color.lower(), "description": desc})
    return validated


def sync_labels(*, repo: str | None = None, apply: bool = False) -> dict[str, object]:
    labels = load_labels()
    if not apply:
        return {"mode": "dry-run", "count": len(labels), "labels": [x["name"] for x in labels]}
    for item in labels:
        cmd = [
            "gh",
            "label",
            "create",
            item["name"],
            "--color",
            item["color"],
            "--description",
            item["description"],
            "--force",
        ]
        if repo:
            cmd.extend(["--repo", repo])
        subprocess.run(cmd, check=True, timeout=20)
    return {"mode": "applied", "count": len(labels), "labels": [x["name"] for x in labels]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sync_labels")
    parser.add_argument("--repo")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    print(json.dumps(sync_labels(repo=args.repo, apply=args.apply), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
