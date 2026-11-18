from fractions import Fraction
from typing import Any

from ..lang.profiles import load_profile


def wrap_caption_lines(text: str, *, lang: str = "en") -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    prof = load_profile(lang.split("-", 1)[0].lower())
    max_chars = int(prof["caption"]["max_chars_per_line"])
    max_lines = int(prof["caption"]["max_lines"])

    words = cleaned.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip() if current else word
        if len(candidate) <= max_chars or not current:
            current = candidate[:max_chars] if len(candidate) > max_chars and not current else candidate
        else:
            lines.append(current)
            current = word[:max_chars]
            if len(lines) >= max_lines:
                break
    if current and len(lines) < max_lines:
        lines.append(current)
    return lines[:max_lines]


def build_scene_word_timings(
    scenes: list[dict[str, Any]],
    *,
    fps: str | Fraction = "30/1",
    max_cps: int = 18,
) -> list[dict[str, Any]]:
    _ = max_cps
    table: list[dict[str, Any]] = []
    cursor = 0
    for scene in scenes:
        dur = int(scene["duration_frames"])
        params = scene.get("params", {})
        phrase = " ".join(str(params.get(k, "")) for k in ("heading", "subheading")).strip()
        words = [w for w in phrase.split() if w]
        if words and dur >= len(words):
            base = dur // len(words)
            rem = dur % len(words)
            w_cursor = cursor
            for idx, word in enumerate(words):
                span = base + (1 if idx < rem else 0)
                clean_word = word.replace("{", "(").replace("}", ")").replace("\\", "/")[:160]
                table.append({
                    "start": w_cursor,
                    "end": w_cursor + span,
                    "text": clean_word,
                })
                w_cursor += span
        elif words and dur >= 1:
            clean_joined = " ".join(words).replace("{", "(").replace("}", ")").replace("\\", "/")[:160]
            table.append({"start": cursor, "end": cursor + dur, "text": clean_joined})
        cursor += dur
    return table
