import hashlib
import re
from typing import Any

from ...lang.casing import locale_upper
from ...lang.detect import detect_language

PALETTE_PRESETS: dict[str, tuple[str, str, str]] = {
    "calm": ("#14191f", "#edf1f5", "#4c8b93"),
    "warm": ("#1f1713", "#f4ece4", "#d06a3f"),
    "high_contrast": ("#0d0f12", "#f7f8fa", "#e04f3e"),
    "editorial": ("#efeae1", "#202421", "#b85236"),
}

STOP_TOKENS = frozenset({
    "make", "create", "video", "short", "vertical", "horizontal", "with", "without",
    "calm", "warm", "colors", "for", "and", "the", "bir", "kisa", "kısa", "dikey",
    "yatay", "renkler", "sakin", "ile", "ve", "kurzes", "mit", "ruhigen", "farben",
})


def _deterministic_int(seed: int | None, salt: str, modulo: int) -> int:
    raw = f"{seed if seed is not None else 42}:{salt}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:4], "big") % max(1, modulo)


def _extract_topic_phrases(prompt: str, lang: str, count: int) -> list[str]:
    cleaned = re.sub(r"\b(?:9:16|16:9|1:1|4:5|\d+\s*(?:s|sec|seconds|sn|saniye|sekunden))\b", " ", prompt, flags=re.I)
    segments = [
        seg.strip(" -•*\t.")
        for seg in re.split(r"[,;\n•|]+", cleaned)
        if seg.strip(" -•*\t.")
    ]
    meaningful = [s for s in segments if len(s) >= 3]
    if not meaningful:
        meaningful = [prompt.strip() or ("Odak" if lang == "tr" else "Fokus" if lang == "de" else "Focus")]
    base_topic = meaningful[0][:64]
    defaults_by_lang = {
        "tr": [
            base_topic,
            "Net adımlar ve sade odak",
            "Ölçülü ritim ve okunaklı düzen",
            "Kalıcı özet ve sonraki adım",
        ],
        "de": [
            base_topic,
            "Klare Schritte und ruhiger Fokus",
            "Präziser Rhythmus und Lesbarkeit",
            "Kompaktes Fazit zum Abschluss",
        ],
        "en": [
            base_topic,
            "Clear structure and steady focus",
            "Measured pacing and clean contrast",
            "Concise takeaway that sticks",
        ],
    }
    pool = meaningful + defaults_by_lang.get(lang, defaults_by_lang["en"])
    deduped: list[str] = []
    for item in pool:
        trimmed = item[:72].strip()
        if trimmed and trimmed not in deduped:
            deduped.append(trimmed)
        if len(deduped) >= count:
            break
    while len(deduped) < count:
        deduped.append(f"{base_topic} {len(deduped) + 1}"[:72])
    return deduped[:count]


def _pick_palette(prompt: str, seed: int | None) -> tuple[str, str, str]:
    low = prompt.lower()
    if any(k in low for k in ("editorial", "paper", "light", "açık", "hell")):
        return PALETTE_PRESETS["editorial"]
    if any(k in low for k in ("warm", "sunset", "sıcak", "warmen")):
        return PALETTE_PRESETS["warm"]
    if any(k in low for k in ("calm", "sakin", "ruhig", "minimal")):
        return PALETTE_PRESETS["calm"]
    keys = sorted(PALETTE_PRESETS)
    return PALETTE_PRESETS[keys[_deterministic_int(seed, "palette", len(keys))]]


def _default_for_property(prop_name: str, prop_schema: dict[str, Any], prompt: str, lang: str, seed: int | None) -> Any:
    if "const" in prop_schema:
        return prop_schema["const"]
    if "enum" in prop_schema and prop_schema["enum"]:
        choices = list(prop_schema["enum"])
        if lang in choices:
            return lang
        return choices[_deterministic_int(seed, prop_name, len(choices))]
    prop_type = prop_schema.get("type")
    bg, fg, acc = _pick_palette(prompt, seed)
    phrases = _extract_topic_phrases(prompt, lang, 4)

    if prop_type == "string":
        if prop_name in {"language", "lang", "video_lang"}:
            return lang
        if prop_name == "background":
            return bg
        if prop_name == "foreground":
            return fg
        if prop_name == "accent":
            return acc
        if prop_name in {"aspect", "aspect_ratio"}:
            return "9:16" if "9:16" in prompt else ("1:1" if "1:1" in prompt else "16:9")
        if prop_name in {"heading", "hook", "title"}:
            words = [w for w in re.findall(r"[^\W_]+", phrases[0]) if w.lower() not in STOP_TOKENS]
            short = " ".join(words[:3]) if words else phrases[0][:24]
            return locale_upper(short[:32], lang)
        if prop_name in {"subheading", "summary", "angle", "thesis", "payoff", "body"}:
            return phrases[min(1, len(phrases) - 1)][:96]
        return phrases[0][:64]
    if prop_type == "boolean":
        return False
    if prop_type == "integer":
        low = int(prop_schema.get("minimum", 1))
        high = int(prop_schema.get("maximum", max(low, 10)))
        if "duration" in prop_name:
            return max(low, min(high, 60))
        return low
    if prop_type == "number":
        low_f = float(prop_schema.get("minimum", 0.0))
        return low_f
    if prop_type == "array":
        item_schema = prop_schema.get("items", {"type": "string"})
        min_items = max(int(prop_schema.get("minItems", 1)), 3 if prop_name in {"scenes", "beats", "lines"} else 1)
        max_items = int(prop_schema.get("maxItems", max(min_items, 8)))
        count = min(max_items, min_items)
        result_list = []
        for idx in range(count):
            if item_schema.get("type") == "object":
                obj = _build_from_object_schema(item_schema, phrases[idx % len(phrases)], lang, (seed or 0) + idx + 1, idx)
                result_list.append(obj)
            elif item_schema.get("type") == "number":
                result_list.append(float((idx + 1) * 10))
            elif item_schema.get("type") == "integer":
                result_list.append(idx + 1)
            else:
                result_list.append(phrases[idx % len(phrases)])
        return result_list
    if prop_type == "object":
        return _build_from_object_schema(prop_schema, prompt, lang, seed, 0)
    return ""


def _build_from_object_schema(
    schema: dict[str, Any],
    prompt: str,
    lang: str,
    seed: int | None,
    index: int,
) -> dict[str, Any]:
    props = schema.get("properties", {})
    required = schema.get("required") or list(props.keys())
    out: dict[str, Any] = {}
    for key in props:
        if key in required or key in {"heading", "subheading", "background", "foreground", "accent", "recipe", "engine", "duration_frames"}:
            if key == "id":
                out[key] = f"beat-{index + 1}"
            else:
                out[key] = _default_for_property(key, props[key], prompt, lang, (seed or 0) + index)
    return out


class OfflineRulesProvider:
    name = "offline_rules"

    def generate_json(
        self,
        system: str,
        user: str,
        schema: dict[str, Any],
        *,
        seed: int | None = None,
    ) -> dict[str, Any]:
        _ = system
        explicit_lang_match = re.search(r"\boutput_language\s*[:=]\s*([a-z]{2,3})\b", user, flags=re.I)
        lang = explicit_lang_match.group(1).lower() if explicit_lang_match else detect_language(user, default="en")
        return _build_from_object_schema(schema, user, lang, seed, 0)
