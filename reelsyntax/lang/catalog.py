import os
from pathlib import Path
import re
from typing import Any

from ReelSyntax_Skills.tools.registry import contained_path, read_json

PKG_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = PKG_DIR.parent
BUNDLED_LOCALES_DIR = PKG_DIR / "data/locales"
LOCALE_TAG_RE = re.compile(r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
TIER1_LOCALES = ("en", "tr", "de")
TIER2_LOCALES = ("es", "fr", "pt")
SUPPORTED_LOCALES = TIER1_LOCALES + TIER2_LOCALES

PSEUDO_MAP = str.maketrans({
    "a": "à", "e": "ë", "i": "ï", "o": "ô", "u": "ü",
    "A": "À", "E": "Ë", "I": "Ï", "O": "Ô", "U": "Ü",
})


def locales_directory(root: Path | None = None) -> Path:
    if root is not None:
        return Path(root) / "locales"
    repo_candidate = REPO_ROOT / "locales"
    if repo_candidate.is_dir():
        return repo_candidate
    return BUNDLED_LOCALES_DIR


def load_locale_status(root: Path | None = None) -> dict[str, Any]:
    loc_dir = locales_directory(root)
    status_path = contained_path(loc_dir, "status.json")
    doc = read_json(status_path, max_bytes=131_072)
    if not isinstance(doc, dict) or doc.get("schema_version") != 1 or not isinstance(doc.get("locales"), dict):
        raise ValueError("Invalid locales/status.json structure")
    for code, entry in doc["locales"].items():
        if not LOCALE_TAG_RE.fullmatch(code):
            raise ValueError(f"Invalid locale key in status.json: {code!r}")
        if type(entry.get("verified_by_owner")) is not bool:
            raise ValueError(f"verified_by_owner must be boolean for locale {code}")
        if type(entry.get("tier")) is not int or entry["tier"] not in {1, 2, 3}:
            raise ValueError(f"Invalid tier for locale {code}")
    return doc


def fallback_chain(locale: str) -> list[str]:
    cleaned = (locale or "en").strip().replace("_", "-")
    chain: list[str] = []
    parts = [p for p in cleaned.split("-") if p]
    while parts:
        candidate = "-".join([parts[0].lower(), *parts[1:]])
        if LOCALE_TAG_RE.fullmatch(candidate) and candidate not in chain:
            chain.append(candidate)
        parts.pop()
    if "en" not in chain:
        chain.append("en")
    return chain


def resolve_ui_locale(explicit: str | None = None, environ: dict[str, str] | None = None) -> str:
    env = os.environ if environ is None else environ
    if explicit and explicit != "auto":
        return explicit.strip().replace("_", "-")
    from ..config import load_config

    cfg_lang = load_config(environ=env).general.ui_lang
    if cfg_lang and cfg_lang != "auto":
        return cfg_lang
    for key in ("REELSYNTAX_UI_LANG", "LC_ALL", "LC_MESSAGES", "LANG"):
        raw = env.get(key, "")
        if not raw or raw in {"C", "POSIX", "C.UTF-8"}:
            continue
        code = raw.split(".", 1)[0].replace("_", "-")
        primary = code.split("-", 1)[0].lower()
        if LOCALE_TAG_RE.fullmatch(primary):
            return primary
    return "en"


def load_catalog(locale: str, root: Path | None = None) -> dict[str, Any]:
    loc_dir = locales_directory(root)
    if not LOCALE_TAG_RE.fullmatch(locale):
        raise ValueError(f"Invalid locale identifier: {locale!r}")
    path = contained_path(loc_dir, f"{locale}.json")
    data = read_json(path, max_bytes=524_288)
    if not isinstance(data, dict) or not data:
        raise ValueError(f"Locale catalog {locale}.json must be a non-empty JSON object")
    for key, val in data.items():
        if not isinstance(key, str) or not key:
            raise ValueError("Catalog keys must be non-empty strings")
        if isinstance(val, str):
            continue
        if isinstance(val, dict) and "other" in val and all(isinstance(v, str) for v in val.values()):
            continue
        raise ValueError(f"Invalid catalog entry {key!r} in {locale}.json")
    return data


def _select_plural_form(entry: dict[str, str], count: int | float) -> str:
    if count == 0 and "zero" in entry:
        return entry["zero"]
    if count == 1 and "one" in entry:
        return entry["one"]
    return entry["other"]


def translate(key: str, locale: str = "en", *, root: Path | None = None, **params: Any) -> str:
    loc_dir = locales_directory(root)
    template: str | dict[str, str] | None = None
    for cand in fallback_chain(locale):
        path = contained_path(loc_dir, f"{cand}.json", must_exist=False)
        if not path.is_file():
            continue
        cat = load_catalog(cand, root=root)
        if key in cat:
            template = cat[key]
            break
    if template is None:
        raise KeyError(f"Unknown localization key: {key}")
    if isinstance(template, dict):
        count_val = params.get("count", 0)
        raw_str = _select_plural_form(template, count_val)
    else:
        raw_str = template
    return raw_str.format(**params) if params else raw_str


def pseudo_localize(text: str, expansion_ratio: float = 0.35) -> str:
    parts = re.split(r"(\{[a-zA-Z0-9_]+\})", text)
    transformed: list[str] = []
    plain_len = 0
    for part in parts:
        if part.startswith("{") and part.endswith("}"):
            transformed.append(part)
        else:
            plain_len += len(part)
            transformed.append(part.translate(PSEUDO_MAP))
    pad_count = max(2, int(round(plain_len * expansion_ratio)))
    padding = "·" * pad_count
    return f"[{''.join(transformed)} {padding}]"


def validate_language(locale: str, root: Path | None = None) -> dict[str, Any]:
    from .profiles import load_profile

    en_cat = load_catalog("en", root=root)
    target_cat = load_catalog(locale, root=root)
    status = load_locale_status(root=root)
    if locale not in status["locales"]:
        raise ValueError(f"Locale {locale!r} is missing from locales/status.json")
    missing_keys = sorted(set(en_cat) - set(target_cat))
    extra_keys = sorted(set(target_cat) - set(en_cat))
    if missing_keys or extra_keys:
        raise ValueError(f"Catalog {locale}.json key mismatch: missing={missing_keys}, extra={extra_keys}")
    for key, en_val in en_cat.items():
        tgt_val = target_cat[key]
        if isinstance(en_val, dict) != isinstance(tgt_val, dict):
            raise ValueError(f"Catalog {locale}.json entry {key!r} plural/scalar mismatch with en.json")
        en_vars = set(re.findall(r"\{([a-zA-Z0-9_]+)\}", str(en_val)))
        tgt_vars = set(re.findall(r"\{([a-zA-Z0-9_]+)\}", str(tgt_val)))
        if en_vars != tgt_vars:
            raise ValueError(f"Catalog {locale}.json entry {key!r} placeholder mismatch: {tgt_vars} != {en_vars}")
    prof = load_profile(locale, root=root)
    meta = status["locales"][locale]
    return {
        "locale": locale,
        "tier": meta["tier"],
        "verified_by_owner": meta["verified_by_owner"],
        "draft_translation": not meta["verified_by_owner"] and locale != status.get("source_locale", "en"),
        "keys": len(target_cat),
        "required_glyphs": prof["required_glyphs"],
        "valid": True,
    }
