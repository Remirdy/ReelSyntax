from pathlib import Path
import re
from typing import Any

from ReelSyntax_Skills.tools.registry import contained_path, read_json

FORMAT_V1_SCHEMA_URL = "https://remirdy.github.io/ReelSyntax/schemas/format.v1.schema.json"
FORMAT_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER_SIMPLE_RE = re.compile(r"^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?$")

FORMAT_CATEGORIES = frozenset({
    "social",
    "personal",
    "education",
    "music",
    "creator",
    "business",
    "art",
    "comedy",
})

FORMAT_ASPECTS = frozenset({"9:16", "1:1", "16:9", "4:5"})
FORMAT_ENGINES = frozenset({"pillow", "chromium", "browser", "webgl", "blender", "ffmpeg"})
STEP_TYPES = frozenset({"llm", "render", "qc"})
RENDER_PROFILES = frozenset({"snapshot", "draft", "production", "hero"})
RENDER_SCOPES = frozenset({"first_5s", "full"})

FORBIDDEN_PACKAGE_EXTENSIONS = frozenset({
    ".py", ".pyc", ".pyo", ".pyd", ".so", ".dll", ".dylib", ".exe",
    ".sh", ".bash", ".zsh", ".bat", ".cmd", ".ps1", ".js", ".mjs",
    ".cjs", ".ts", ".tsx", ".jsx", ".wasm", ".jar", ".rb", ".pl",
})


def format_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": FORMAT_V1_SCHEMA_URL,
        "title": "ReelSyntax format manifest",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "id",
            "version",
            "title",
            "category",
            "aspect",
            "duration_sec",
            "languages",
            "engines",
            "needs",
            "steps",
            "qc_rules",
        ],
        "properties": {
            "$schema": {"type": "string"},
            "id": {"type": "string", "pattern": FORMAT_ID_RE.pattern, "maxLength": 64},
            "version": {"type": "string", "pattern": SEMVER_SIMPLE_RE.pattern},
            "title": {
                "type": "object",
                "required": ["en", "tr", "de"],
                "additionalProperties": {"type": "string", "minLength": 1, "maxLength": 120},
            },
            "category": {"enum": sorted(FORMAT_CATEGORIES)},
            "aspect": {
                "type": "array",
                "minItems": 1,
                "items": {"enum": sorted(FORMAT_ASPECTS)},
            },
            "duration_sec": {
                "type": "object",
                "additionalProperties": False,
                "required": ["min", "max"],
                "properties": {
                    "min": {"type": "integer", "minimum": 1, "maximum": 600},
                    "max": {"type": "integer", "minimum": 1, "maximum": 600},
                },
            },
            "languages": {
                "type": "array",
                "minItems": 1,
                "items": {"type": "string", "minLength": 2, "maxLength": 16},
            },
            "engines": {
                "type": "array",
                "minItems": 1,
                "items": {"enum": sorted(FORMAT_ENGINES)},
            },
            "needs": {
                "type": "array",
                "items": {"type": "string", "minLength": 1, "maxLength": 64},
            },
            "optional": {
                "type": "array",
                "items": {"type": "string", "minLength": 1, "maxLength": 64},
            },
            "skills": {
                "type": "array",
                "items": {"type": "string", "pattern": FORMAT_ID_RE.pattern},
            },
            "steps": {
                "type": "array",
                "minItems": 1,
                "maxItems": 24,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["id", "type"],
                    "properties": {
                        "id": {"type": "string", "pattern": FORMAT_ID_RE.pattern},
                        "type": {"enum": sorted(STEP_TYPES)},
                        "gate": {"const": "approve"},
                        "profile": {"enum": sorted(RENDER_PROFILES)},
                        "scope": {"enum": sorted(RENDER_SCOPES)},
                    },
                },
            },
            "qc_rules": {
                "type": "array",
                "minItems": 1,
                "items": {"type": "string", "minLength": 1, "maxLength": 64},
            },
        },
    }


def validate_format_manifest(raw: dict[str, Any], expected_id: str | None = None) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("format.json: expected a JSON object")
    allowed = {
        "$schema",
        "id",
        "version",
        "title",
        "category",
        "aspect",
        "duration_sec",
        "languages",
        "engines",
        "needs",
        "optional",
        "skills",
        "steps",
        "qc_rules",
    }
    required = {
        "id",
        "version",
        "title",
        "category",
        "aspect",
        "duration_sec",
        "languages",
        "engines",
        "needs",
        "steps",
        "qc_rules",
    }
    missing = sorted(required - set(raw))
    if missing:
        raise ValueError(f"format.json: missing required fields {missing}")
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"format.json: unknown fields {unknown}")

    fid = raw["id"]
    if not isinstance(fid, str) or not FORMAT_ID_RE.fullmatch(fid) or len(fid) > 64:
        raise ValueError(f"format.json.id: expected lowercase hyphenated identifier, got {fid!r}")
    if expected_id is not None and fid != expected_id:
        raise ValueError(f"format.json.id: {fid!r} does not match directory name {expected_id!r}")
    if not isinstance(raw["version"], str) or not SEMVER_SIMPLE_RE.fullmatch(raw["version"]):
        raise ValueError(f"format.json.version: invalid semantic version {raw['version']!r}")

    title = raw["title"]
    if not isinstance(title, dict) or not {"en", "tr", "de"} <= set(title):
        raise ValueError("format.json.title: must provide 'en', 'tr', and 'de' localized titles")
    for k, v in title.items():
        if not isinstance(v, str) or not 1 <= len(v.strip()) <= 120:
            raise ValueError(f"format.json.title.{k}: expected non-empty string up to 120 characters")

    if raw["category"] not in FORMAT_CATEGORIES:
        raise ValueError(f"format.json.category: {raw['category']!r} must be one of {sorted(FORMAT_CATEGORIES)}")

    aspects = raw["aspect"]
    if not isinstance(aspects, list) or not aspects or any(a not in FORMAT_ASPECTS for a in aspects):
        raise ValueError(f"format.json.aspect: expected non-empty list from {sorted(FORMAT_ASPECTS)}")

    dur = raw["duration_sec"]
    if not isinstance(dur, dict) or set(dur) != {"min", "max"}:
        raise ValueError("format.json.duration_sec: must contain integer 'min' and 'max'")
    if type(dur["min"]) is not int or type(dur["max"]) is not int or not (1 <= dur["min"] <= dur["max"] <= 600):
        raise ValueError("format.json.duration_sec: expected 1 <= min <= max <= 600")

    langs = raw["languages"]
    if not isinstance(langs, list) or not langs or any(not isinstance(x, str) or not x for x in langs):
        raise ValueError("format.json.languages: expected non-empty string array")

    engines = raw["engines"]
    if not isinstance(engines, list) or not engines or any(e not in FORMAT_ENGINES for e in engines):
        raise ValueError(f"format.json.engines: expected non-empty list from {sorted(FORMAT_ENGINES)}")

    for list_key in ("needs", "optional", "qc_rules", "skills"):
        if list_key not in raw:
            continue
        val = raw[list_key]
        if not isinstance(val, list) or any(not isinstance(x, str) or not x for x in val):
            raise ValueError(f"format.json.{list_key}: expected list of non-empty strings")
    if not raw["qc_rules"]:
        raise ValueError("format.json.qc_rules: must specify at least one QC rule")

    steps = raw["steps"]
    if not isinstance(steps, list) or not 1 <= len(steps) <= 24:
        raise ValueError("format.json.steps: expected 1..24 step objects")
    seen_steps: set[str] = set()
    has_approval_before_hero = False
    for idx, step in enumerate(steps):
        if not isinstance(step, dict) or set(step) - {"id", "type", "gate", "profile", "scope"} or {"id", "type"} - set(step):
            raise ValueError(f"format.json.steps[{idx}]: invalid step keys")
        sid = step["id"]
        if not isinstance(sid, str) or not FORMAT_ID_RE.fullmatch(sid) or sid in seen_steps:
            raise ValueError(f"format.json.steps[{idx}].id: invalid or duplicate step id {sid!r}")
        seen_steps.add(sid)
        stype = step["type"]
        if stype not in STEP_TYPES:
            raise ValueError(f"format.json.steps[{idx}].type: unsupported step type {stype!r}")
        if "gate" in step and step["gate"] != "approve":
            raise ValueError(f"format.json.steps[{idx}].gate: only 'approve' is supported")
        if step.get("gate") == "approve":
            has_approval_before_hero = True
        if stype == "render":
            prof = step.get("profile")
            if prof not in RENDER_PROFILES:
                raise ValueError(f"format.json.steps[{idx}].profile: render step requires profile in {sorted(RENDER_PROFILES)}")
            if prof == "hero" and not has_approval_before_hero:
                raise ValueError("format.json.steps: 'hero' render step requires at least one preceding approval gate")
            if "scope" in step and step["scope"] not in RENDER_SCOPES:
                raise ValueError(f"format.json.steps[{idx}].scope: unsupported scope {step['scope']!r}")
        elif "profile" in step or "scope" in step:
            raise ValueError(f"format.json.steps[{idx}]: profile/scope are valid only on render steps")
    return raw


def assert_data_only_directory(format_dir: Path) -> int:
    root = Path(format_dir).resolve(strict=True)
    file_count = 0
    stack = [root]
    while stack:
        current = stack.pop()
        for entry in sorted(current.iterdir(), key=lambda p: p.name):
            if entry.is_symlink():
                raise ValueError(f"Format package cannot contain symbolic links: {entry.relative_to(root)}")
            if entry.is_dir():
                if entry.name in {".git", "__pycache__", "node_modules"}:
                    raise ValueError(f"Format package cannot contain {entry.name} directory")
                stack.append(entry)
                continue
            file_count += 1
            if entry.suffix.lower() in FORBIDDEN_PACKAGE_EXTENSIONS:
                raise ValueError(f"Format package contains forbidden executable/code file: {entry.relative_to(root)}")
            if entry.stat().st_size > 16_777_216:
                raise ValueError(f"Format package file exceeds 16 MiB limit: {entry.relative_to(root)}")
    return file_count


def validate_format_directory(format_dir: Path) -> dict[str, Any]:
    root = Path(format_dir).resolve(strict=True)
    file_count = assert_data_only_directory(root)
    manifest_path = contained_path(root, "format.json")
    doc_path = contained_path(root, "FORMAT.md")
    skel_path = contained_path(root, "template/reel.skel.json")
    if doc_path.stat().st_size < 20:
        raise ValueError("FORMAT.md must contain a non-empty format specification")
    manifest = validate_format_manifest(read_json(manifest_path, max_bytes=131_072), expected_id=root.name)
    skel = read_json(skel_path, max_bytes=524_288)
    if not isinstance(skel, dict) or skel.get("schema_version") != 1:
        raise ValueError("template/reel.skel.json must be a version 1 project skeleton object")
    for field_key in ("scenes", "output", "audio"):
        if field_key not in skel:
            raise ValueError(f"template/reel.skel.json missing required skeleton field {field_key!r}")
    return {
        "id": manifest["id"],
        "version": manifest["version"],
        "category": manifest["category"],
        "path": str(root),
        "files_checked": file_count,
        "valid": True,
        "manifest": manifest,
    }
