import json
from pathlib import Path
import re
from typing import Any

from ReelSyntax_Skills.tools.registry import atomic_json, contained_path, read_json

PKG_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = PKG_DIR.parent
BUNDLED_PROFILES_DIR = PKG_DIR / "data/lang_profiles"
LANG_ID_RE = re.compile(r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
SCRIPT_RE = re.compile(r"^[A-Z][a-z]{3}$")


def profiles_directory(root: Path | None = None) -> Path:
    if root is not None:
        return Path(root) / "lang-profiles"
    repo_candidate = REPO_ROOT / "lang-profiles"
    if repo_candidate.is_dir():
        return repo_candidate
    return BUNDLED_PROFILES_DIR


def validate_profile_data(raw: dict[str, Any], expected_id: str | None = None) -> dict[str, Any]:
    allowed = {
        "id",
        "tier",
        "maintainer",
        "script",
        "direction",
        "quotes",
        "decimal",
        "thousands",
        "caption",
        "line_break",
        "case",
        "required_glyphs",
        "formality_default",
        "formality_options",
        "tts",
        "fonts",
    }
    required = {
        "id",
        "tier",
        "maintainer",
        "script",
        "direction",
        "quotes",
        "decimal",
        "thousands",
        "caption",
        "line_break",
        "case",
        "required_glyphs",
        "formality_default",
        "tts",
        "fonts",
    }
    if not isinstance(raw, dict) or set(raw) - allowed or required - set(raw):
        raise ValueError(f"Language profile has missing or unexpected fields: {sorted(set(raw) ^ required)}")
    pid = raw["id"]
    if not isinstance(pid, str) or not LANG_ID_RE.fullmatch(pid):
        raise ValueError(f"Invalid language profile id: {pid!r}")
    if expected_id is not None and pid != expected_id:
        raise ValueError(f"Language profile id {pid!r} does not match filename {expected_id!r}")
    if type(raw["tier"]) is not int or raw["tier"] not in {1, 2, 3}:
        raise ValueError("tier must be 1, 2, or 3")
    if not isinstance(raw["maintainer"], str) or not raw["maintainer"].strip():
        raise ValueError("maintainer must be a non-empty handle")
    if not isinstance(raw["script"], str) or not SCRIPT_RE.fullmatch(raw["script"]):
        raise ValueError("script must be a 4-letter ISO 15924 code such as Latn")
    if raw["direction"] not in {"ltr", "rtl"}:
        raise ValueError("direction must be 'ltr' or 'rtl'")
    quotes = raw["quotes"]
    if not isinstance(quotes, dict) or set(quotes) != {"open", "close"} or not all(isinstance(quotes[k], str) and quotes[k] for k in ("open", "close")):
        raise ValueError("quotes must specify non-empty open and close strings")
    for sep_key in ("decimal", "thousands"):
        if not isinstance(raw[sep_key], str) or len(raw[sep_key]) != 1:
            raise ValueError(f"{sep_key} must be a 1-character string")
    cap = raw["caption"]
    if not isinstance(cap, dict) or set(cap) != {"max_chars_per_line", "max_lines", "max_cps"}:
        raise ValueError("caption must specify max_chars_per_line, max_lines, and max_cps")
    if type(cap["max_chars_per_line"]) is not int or not 10 <= cap["max_chars_per_line"] <= 80:
        raise ValueError("caption.max_chars_per_line out of bounds [10, 80]")
    if type(cap["max_lines"]) is not int or not 1 <= cap["max_lines"] <= 4:
        raise ValueError("caption.max_lines out of bounds [1, 4]")
    if type(cap["max_cps"]) is not int or not 5 <= cap["max_cps"] <= 35:
        raise ValueError("caption.max_cps out of bounds [5, 35]")
    lb = raw["line_break"]
    if not isinstance(lb, dict) or set(lb) != {"hyphenation", "compound_split"} or any(type(lb[k]) is not bool for k in ("hyphenation", "compound_split")):
        raise ValueError("line_break must specify boolean hyphenation and compound_split")
    case_cfg = raw["case"]
    if not isinstance(case_cfg, dict) or set(case_cfg) != {"upper", "special"} or case_cfg["upper"] not in {"ascii", "locale"} or not isinstance(case_cfg["special"], list):
        raise ValueError("case must specify upper ('ascii' or 'locale') and special list")
    if not isinstance(raw["required_glyphs"], str) or not raw["required_glyphs"]:
        raise ValueError("required_glyphs must be a non-empty string")
    if not isinstance(raw["formality_default"], str) or not raw["formality_default"]:
        raise ValueError("formality_default must be a non-empty string")
    if "formality_options" in raw:
        opts = raw["formality_options"]
        if not isinstance(opts, list) or not opts or raw["formality_default"] not in opts:
            raise ValueError("formality_options must include formality_default")
    tts = raw["tts"]
    if not isinstance(tts, dict) or set(tts) != {"preferred_locales"} or not isinstance(tts["preferred_locales"], list) or not tts["preferred_locales"]:
        raise ValueError("tts.preferred_locales must be a non-empty list")
    fonts = raw["fonts"]
    if not isinstance(fonts, list) or not fonts or any(not isinstance(f, str) or not f for f in fonts):
        raise ValueError("fonts must be a non-empty list of font family names")
    return raw


def list_profiles(root: Path | None = None) -> list[str]:
    directory = profiles_directory(root)
    if not directory.is_dir():
        return []
    return sorted(p.stem for p in directory.glob("*.json") if p.is_file())


def load_profile(locale: str, root: Path | None = None) -> dict[str, Any]:
    directory = profiles_directory(root)
    candidates = [locale.strip().replace("_", "-")]
    primary = candidates[0].split("-", 1)[0].lower()
    if primary not in candidates:
        candidates.append(primary)
    for cand in candidates:
        if not LANG_ID_RE.fullmatch(cand):
            continue
        file_path = contained_path(directory, f"{cand}.json", must_exist=False)
        if file_path.is_file():
            data = read_json(file_path, max_bytes=65_536)
            return validate_profile_data(data, expected_id=cand)
    raise ValueError(f"Unknown language profile: {locale}")


def scaffold_language(locale: str, root: Path = REPO_ROOT) -> dict[str, str]:
    if not isinstance(locale, str) or not LANG_ID_RE.fullmatch(locale):
        raise ValueError(f"Invalid language code: {locale!r}")
    base = Path(root).resolve()
    prof_dir = base / "lang-profiles"
    loc_dir = base / "locales"
    prof_dir.mkdir(parents=True, exist_ok=True)
    loc_dir.mkdir(parents=True, exist_ok=True)

    prof_path = contained_path(prof_dir, f"{locale}.json", must_exist=False)
    cat_path = contained_path(loc_dir, f"{locale}.json", must_exist=False)
    status_path = contained_path(loc_dir, "status.json", must_exist=False)
    if prof_path.exists() or cat_path.exists():
        raise ValueError(f"Language files already exist for {locale}")

    starter_profile = {
        "id": locale,
        "tier": 2,
        "maintainer": "unassigned",
        "script": "Latn",
        "direction": "ltr",
        "quotes": {"open": "“", "close": "”"},
        "decimal": ".",
        "thousands": ",",
        "caption": {"max_chars_per_line": 40, "max_lines": 2, "max_cps": 18},
        "line_break": {"hyphenation": False, "compound_split": False},
        "case": {"upper": "locale", "special": []},
        "required_glyphs": "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
        "formality_default": "neutral",
        "formality_options": ["casual", "neutral", "formal"],
        "tts": {"preferred_locales": [locale]},
        "fonts": ["Noto Sans", "DejaVu Sans"],
    }
    validate_profile_data(starter_profile, expected_id=locale)
    en_source_path = contained_path(loc_dir, "en.json", must_exist=False)
    if en_source_path.is_file():
        en_catalog = json.loads(en_source_path.read_text(encoding="utf-8"))
    else:
        en_catalog = json.loads((PKG_DIR / "data/locales/en.json").read_text(encoding="utf-8"))

    atomic_json(prof_path, starter_profile)
    atomic_json(cat_path, en_catalog)

    if status_path.is_file():
        status_doc = read_json(status_path)
    else:
        status_doc = {"schema_version": 1, "source_locale": "en", "locales": {}}
    status_doc.setdefault("locales", {})[locale] = {
        "tier": 2,
        "name": locale,
        "native_name": locale,
        "maintainer": "unassigned",
        "verified_by_owner": False,
        "verified_at": None,
    }
    atomic_json(status_path, status_doc)
    return {"profile": str(prof_path), "catalog": str(cat_path), "status": str(status_path)}
