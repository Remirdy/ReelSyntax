import os
from pathlib import Path
import sys
from typing import Any

from ReelSyntax_Skills.tools.registry import atomic_json, read_json

from ..project import starter
from .schema import FORMAT_CATEGORIES, FORMAT_ID_RE, FORMAT_V1_SCHEMA_URL, validate_format_directory, validate_format_manifest

PKG_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = PKG_DIR.parent
BUNDLED_FORMATS_DIR = PKG_DIR / "data/formats"


def user_formats_directory(environ: dict[str, str] | None = None, platform_name: str | None = None) -> Path:
    env = os.environ if environ is None else environ
    plat = sys.platform if platform_name is None else platform_name
    explicit = env.get("REELSYNTAX_FORMATS_DIR")
    if explicit:
        return Path(explicit).expanduser()
    if plat == "win32":
        appdata = env.get("LOCALAPPDATA") or env.get("APPDATA")
        base = Path(appdata) if appdata else (Path.home() / "AppData/Local")
        return base / "reelsyntax/formats"
    xdg_data = env.get("XDG_DATA_HOME")
    if xdg_data:
        return Path(xdg_data).expanduser() / "reelsyntax/formats"
    if plat == "darwin":
        return Path.home() / "Library/Application Support/reelsyntax/formats"
    return Path.home() / ".local/share/reelsyntax/formats"


def format_search_roots(extra_roots: tuple[Path, ...] = ()) -> list[Path]:
    candidates: list[Path] = list(extra_roots)
    repo_formats = REPO_ROOT / "formats"
    if repo_formats.is_dir():
        candidates.append(repo_formats)
    if BUNDLED_FORMATS_DIR.is_dir():
        candidates.append(BUNDLED_FORMATS_DIR)
    u_dir = user_formats_directory()
    if u_dir.is_dir():
        candidates.append(u_dir)
    deduped: list[Path] = []
    seen: set[Path] = set()
    for path in candidates:
        resolved = path.resolve()
        if resolved not in seen and resolved.is_dir():
            seen.add(resolved)
            deduped.append(resolved)
    return deduped


def discover_formats(category: str | None = None, extra_roots: tuple[Path, ...] = ()) -> list[dict[str, Any]]:
    if category is not None and category not in FORMAT_CATEGORIES:
        raise ValueError(f"Unknown format category: {category!r}")
    found: dict[str, dict[str, Any]] = {}
    for root in format_search_roots(extra_roots):
        for child in sorted(root.iterdir(), key=lambda p: p.name):
            if not child.is_dir() or child.is_symlink() or child.name.startswith("."):
                continue
            manifest_file = child / "format.json"
            if not manifest_file.is_file():
                continue
            manifest = validate_format_manifest(read_json(manifest_file, max_bytes=131_072), expected_id=child.name)
            if category and manifest["category"] != category:
                continue
            if manifest["id"] not in found:
                found[manifest["id"]] = {
                    **manifest,
                    "path": str(child),
                }
    return [found[k] for k in sorted(found)]


def get_format(format_id: str, extra_roots: tuple[Path, ...] = ()) -> dict[str, Any]:
    candidate_path = Path(format_id)
    if candidate_path.is_dir() and (candidate_path / "format.json").is_file():
        validated = validate_format_directory(candidate_path)
        return {**validated["manifest"], "path": validated["path"]}
    if not FORMAT_ID_RE.fullmatch(format_id):
        raise ValueError(f"Invalid format identifier: {format_id!r}")
    for root in format_search_roots(extra_roots):
        target = root / format_id
        if target.is_dir() and (target / "format.json").is_file():
            validated = validate_format_directory(target)
            return {**validated["manifest"], "path": validated["path"]}
    raise ValueError(f"Unknown format: {format_id}")


def scaffold_format(target: str | Path, *, category: str = "social", base_dir: Path | None = None) -> dict[str, Any]:
    if category not in FORMAT_CATEGORIES:
        raise ValueError(f"Unsupported category: {category!r}")
    raw_str = str(target)
    if "/" not in raw_str and "\\" not in raw_str and FORMAT_ID_RE.fullmatch(raw_str):
        fid = raw_str
        parent = Path(base_dir) if base_dir is not None else (REPO_ROOT / "formats" if (REPO_ROOT / "pyproject.toml").is_file() else Path.cwd())
        dest = parent / fid
    else:
        dest = Path(target).absolute()
        fid = dest.name
        if not FORMAT_ID_RE.fullmatch(fid):
            raise ValueError(f"Format directory name must be lowercase hyphenated: {fid!r}")

    if dest.exists() and any(dest.iterdir()):
        raise ValueError(f"Format target directory already exists and is not empty: {dest}")
    (dest / "template").mkdir(parents=True, exist_ok=True)
    (dest / "references").mkdir(parents=True, exist_ok=True)
    (dest / "examples").mkdir(parents=True, exist_ok=True)

    human_title = fid.replace("-", " ").title()
    manifest = {
        "$schema": FORMAT_V1_SCHEMA_URL,
        "id": fid,
        "version": "0.1.0",
        "title": {
            "en": human_title,
            "tr": human_title,
            "de": human_title,
        },
        "category": category,
        "aspect": ["9:16", "1:1", "16:9"],
        "duration_sec": {"min": 6, "max": 60},
        "languages": ["en", "tr", "de"],
        "engines": ["pillow"],
        "needs": ["topic_or_text"],
        "optional": ["tone", "formality", "palette"],
        "skills": ["frame-clock", "contrast-audit"],
        "steps": [
            {"id": "idea", "type": "llm", "gate": "approve"},
            {"id": "script", "type": "llm", "gate": "approve"},
            {"id": "look", "type": "llm", "gate": "approve"},
            {"id": "frames", "type": "render", "profile": "snapshot", "gate": "approve"},
            {"id": "pilot", "type": "render", "scope": "first_5s", "profile": "draft", "gate": "approve"},
            {"id": "full", "type": "render", "profile": "draft", "gate": "approve"},
            {"id": "hero", "type": "render", "profile": "hero"},
            {"id": "qc", "type": "qc"},
        ],
        "qc_rules": ["contrast", "safe-area", "required-glyphs", "loudness"],
    }
    skel = starter()
    skel["id"] = fid
    doc_md = (
        f"# {human_title}\n\n"
        f"Declarative prompt-to-video format (`{fid}`, category `{category}`).\n\n"
        f"## Inputs\n\n"
        f"- Required: `topic_or_text`\n"
        f"- Optional: `tone`, `formality`, `palette`\n\n"
        f"## Steps and gates\n\n"
        f"Runs `idea -> script -> look -> frames -> pilot -> full -> hero -> qc` with approval gates before final master delivery.\n"
    )

    atomic_json(dest / "format.json", manifest)
    atomic_json(dest / "template/reel.skel.json", skel)
    (dest / "FORMAT.md").write_text(doc_md, encoding="utf-8")
    return validate_format_directory(dest)
