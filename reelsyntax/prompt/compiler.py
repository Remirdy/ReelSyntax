from fractions import Fraction
import re
from typing import Any

from ..migration import LOCAL_SCHEMA_REF
from ..palette import contrast_ratio, hex_to_rgb, mix_oklab, rgb_to_hex
from ..project import validate
from ..typography import measure_tracked_text, resolve_font
from ..variants import LANGUAGES
from .intent import ParsedIntent
from .storyboard import StoryboardPlan

LEGACY_DRAWING_RECIPES = frozenset({"assembly", "rings", "signal", "title"})

ASPECT_DIMENSIONS_1080P: dict[str, tuple[int, int]] = {
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
    "4:5": (1080, 1350),
}

DISALLOWED_COMPILED_RECIPES = frozenset({"custom-shader", "three-scene"})
SLUG_CLEAN_RE = re.compile(r"[^a-z0-9]+")


def sanitize_project_id(raw_id: str) -> str:
    cleaned = SLUG_CLEAN_RE.sub("-", raw_id.lower()).strip("-")
    return (cleaned or "prompt-reel")[:64].rstrip("-") or "prompt-reel"


def _fits_at_sizes(
    canvas: Any,
    text: str,
    *,
    is_heading: bool,
    is_legacy: bool,
    use_default_font: bool,
    sizes: list[tuple[int, int]],
) -> bool:
    if not text:
        return True
    base_pt = (56 if is_legacy else 48) if is_heading else 19
    track = 0.8 if is_heading else 0.2
    right_frac = 0.43 if is_legacy else 0.50
    for w, h in sizes:
        unit = min(w / 960.0, h / 540.0)
        font = resolve_font(round(base_pt * unit), bold=is_heading, prefer_default=use_default_font)
        max_w = w * (right_frac - 0.07) * 0.96
        if is_legacy:
            box = canvas.textbbox((w * 0.07, h * (0.39 if is_heading else 0.55)), text, font=font)
            if box[2] > w * right_frac * 0.98:
                return False
        else:
            tw, _ = measure_tracked_text(canvas, text, font, tracking_px=track * unit)
            if tw > max_w:
                return False
    return True


def _trim_to_fit(
    canvas: Any,
    text: str,
    *,
    is_heading: bool,
    is_legacy: bool,
    use_default_font: bool,
    sizes: list[tuple[int, int]],
) -> tuple[str, str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return "", ""
    if _fits_at_sizes(canvas, cleaned, is_heading=is_heading, is_legacy=is_legacy, use_default_font=use_default_font, sizes=sizes):
        return cleaned, ""
    words = cleaned.split(" ")
    for take in range(len(words) - 1, 0, -1):
        prefix = " ".join(words[:take])
        if _fits_at_sizes(canvas, prefix, is_heading=is_heading, is_legacy=is_legacy, use_default_font=use_default_font, sizes=sizes):
            remainder = " ".join(words[take:])
            return prefix, remainder
    first_word = words[0]
    remainder_words = " ".join(words[1:])
    for char_len in range(len(first_word), 0, -1):
        candidate = first_word[:char_len]
        if _fits_at_sizes(canvas, candidate, is_heading=is_heading, is_legacy=is_legacy, use_default_font=use_default_font, sizes=sizes):
            leftover = (first_word[char_len:] + (" " + remainder_words if remainder_words else "")).strip()
            return candidate, leftover
    return "", cleaned


def fit_scene_text_fields(
    heading: str,
    subheading: str,
    *,
    recipe: str,
    width: int,
    height: int,
    spill_heading_to_subheading: bool = True,
    use_system_font: bool = True,
) -> tuple[str, str]:
    from PIL import Image, ImageDraw

    probe_img = Image.new("RGB", (64, 64))
    canvas = ImageDraw.Draw(probe_img)
    is_legacy = recipe in LEGACY_DRAWING_RECIPES
    use_default = is_legacy and not use_system_font
    snap_size = (480, 270) if width >= height else (360, 640)
    draft_size = (max(128, width // 2), max(128, height // 2))
    sizes = [(width, height), draft_size, snap_size, (width * 2, height * 2)]

    fitted_h, overflow_h = _trim_to_fit(
        canvas,
        heading[:120],
        is_heading=True,
        is_legacy=is_legacy,
        use_default_font=use_default,
        sizes=sizes,
    )
    combined_sub = subheading[:120]
    if spill_heading_to_subheading and overflow_h and not combined_sub:
        combined_sub = overflow_h[:120]
    elif spill_heading_to_subheading and overflow_h and combined_sub:
        combined_sub = f"{overflow_h} - {combined_sub}"[:120]

    fitted_sub, _ = _trim_to_fit(
        canvas,
        combined_sub,
        is_heading=False,
        is_legacy=is_legacy,
        use_default_font=use_default,
        sizes=sizes,
    )
    return fitted_h, fitted_sub


def ensure_accessible_palette(background: str, foreground: str, accent: str) -> tuple[str, str, str]:
    bg_rgb = hex_to_rgb(background)
    fg_rgb = hex_to_rgb(foreground)
    ac_rgb = hex_to_rgb(accent)

    bg_is_dark = sum(bg_rgb) < 384
    if bg_is_dark:
        bg_luma = 0.2126 * bg_rgb[0] + 0.7152 * bg_rgb[1] + 0.0722 * bg_rgb[2]
        lift = 0.0
        while bg_luma < 44.0 and lift < 0.6:
            lift = min(0.6, lift + 0.06)
            bg_rgb = mix_oklab(background, "#5c626e", lift)
            bg_luma = 0.2126 * bg_rgb[0] + 0.7152 * bg_rgb[1] + 0.0722 * bg_rgb[2]
    pole_hex = "#fafafc" if bg_is_dark else "#14161a"

    step = 0.0
    while contrast_ratio(fg_rgb, bg_rgb) < 4.6 and step < 1.0:
        step = min(1.0, step + 0.15)
        fg_rgb = mix_oklab(foreground, pole_hex, step)

    ac_step = 0.0
    while contrast_ratio(ac_rgb, bg_rgb) < 3.2 and ac_step < 1.0:
        ac_step = min(1.0, ac_step + 0.15)
        ac_rgb = mix_oklab(accent, pole_hex, ac_step)

    return rgb_to_hex(bg_rgb), rgb_to_hex(fg_rgb), rgb_to_hex(ac_rgb)


def assert_safe_compiled_plan(plan: dict[str, Any]) -> None:
    for scene in plan.get("scenes", []):
        if scene.get("recipe") in DISALLOWED_COMPILED_RECIPES:
            raise ValueError(f"Compiled prompt plans cannot select executable recipe {scene['recipe']!r}")
        params = scene.get("params", {})
        for forbidden_key in ("fragment_file", "module_file"):
            if forbidden_key in params:
                raise ValueError(f"Compiled prompt plans cannot populate {forbidden_key}")
        if "source" in params:
            src = str(params["source"])
            if "://" in src or src.startswith("/") or ".." in src:
                raise ValueError(f"Unsafe compiled asset path: {src!r}")


def compile_storyboard_to_project(
    storyboard: StoryboardPlan,
    intent: ParsedIntent,
    *,
    project_id: str = "prompt-reel",
    seed: int = 42,
) -> dict[str, Any]:
    width, height = ASPECT_DIMENSIONS_1080P.get(storyboard.aspect, (1080, 1920))
    bg_hex, fg_hex, ac_hex = ensure_accessible_palette(
        storyboard.background,
        storyboard.foreground,
        storyboard.accent,
    )

    camera_locked = bool(intent.constraints.get("camera_locked"))
    no_audio = bool(intent.constraints.get("no_audio"))
    no_text = bool(intent.constraints.get("no_text"))

    scenes: list[dict[str, Any]] = []
    cues: list[dict[str, Any]] = []
    silence_exceptions: list[list[int]] = []
    cursor = 0
    note_frequencies = (220, 277, 330, 392, 440, 523)

    is_kinetic_fmt = intent.format_hint == "kinetic-typography"
    is_hook_fmt = intent.format_hint == "social-hook-reel"
    lang_primary = intent.video_lang.split("-", 1)[0].lower()
    total_beats = len(storyboard.beats)
    fps_float = float(Fraction(storyboard.fps))
    max_hook_frames = max(24, int(round(2.0 * fps_float)))

    beat_durations = [int(b.duration_frames) for b in storyboard.beats]
    if is_hook_fmt and total_beats >= 2 and beat_durations[0] > max_hook_frames:
        excess = beat_durations[0] - max_hook_frames
        beat_durations[0] = max_hook_frames
        beat_durations[-1] += excess

    hook_kickers = {"tr": "DİKKAT", "de": "STOPP", "en": "HOOK"}
    payoff_kickers = {"tr": "SONUÇ", "de": "FAZIT", "en": "PAYOFF"}

    for idx, beat in enumerate(storyboard.beats):
        dur_frames = beat_durations[idx]
        chosen_recipe = beat.recipe
        if is_kinetic_fmt:
            chosen_recipe = "signal" if (idx == total_beats - 1 and total_beats >= 3) else "kinetic-type"
        elif is_hook_fmt:
            if idx == 0:
                chosen_recipe = "prism-monolith"
            elif idx == total_beats - 1:
                chosen_recipe = "kinetic-type"
        params: dict[str, Any] = {
            "background": bg_hex,
            "foreground": fg_hex,
            "accent": ac_hex,
        }
        if chosen_recipe in LEGACY_DRAWING_RECIPES:
            params["font_mode"] = "system"
        if not no_text:
            if is_kinetic_fmt:
                params["kicker"] = f"{idx + 1:02d}"
            elif is_hook_fmt:
                if idx == 0:
                    params["kicker"] = hook_kickers.get(lang_primary, "HOOK")
                elif idx == total_beats - 1:
                    params["kicker"] = payoff_kickers.get(lang_primary, "PAYOFF")
                else:
                    params["kicker"] = f"{idx + 1:02d}"
            fitted_h, fitted_sub = fit_scene_text_fields(
                beat.heading or "",
                beat.subheading or "",
                recipe=chosen_recipe,
                width=width,
                height=height,
            )
            if fitted_h:
                params["heading"] = fitted_h
            if fitted_sub:
                params["subheading"] = fitted_sub
        if chosen_recipe == "data-horizon":
            params["series"] = [24.0, 42.0, 68.0, 91.0]

        scene_entry: dict[str, Any] = {
            "id": sanitize_project_id(beat.id),
            "duration_frames": dur_frames,
            "recipe": chosen_recipe,
            "engine": "pillow",
            "params": params,
        }
        if idx > 0 and dur_frames >= 24:
            if is_hook_fmt and idx == 1:
                trans_type = "wipe_left"
            elif (is_kinetic_fmt or is_hook_fmt) and idx < total_beats - 1:
                trans_type = "slide_left"
            else:
                trans_type = "cross_dissolve"
            scene_entry["transition"] = {
                "type": trans_type,
                "duration_frames": min(6 if trans_type in {"slide_left", "wipe_left"} else 8, dur_frames // 4),
            }
        if not camera_locked and chosen_recipe == "prism-monolith":
            scene_entry["camera"] = {"preset": "dolly_in", "focal_mm": 50.0}
        scenes.append(scene_entry)

        if not no_audio:
            cue_dur = min(18, dur_frames)
            if is_hook_fmt and idx == 0:
                cues.append({
                    "frame": cursor,
                    "frequency": 68,
                    "duration_frames": cue_dur,
                    "instrument": "sub_impact",
                })
            else:
                cues.append({
                    "frame": cursor,
                    "frequency": note_frequencies[idx % len(note_frequencies)],
                    "duration_frames": cue_dur,
                    "instrument": "harmonic_pluck" if idx % 2 == 0 else "warm_pad",
                })
            if cursor + cue_dur < cursor + dur_frames:
                silence_exceptions.append([cursor + cue_dur, cursor + dur_frames])
        cursor += dur_frames

    iso3 = LANGUAGES.get(lang_primary, "eng")

    plan: dict[str, Any] = {
        "$schema": LOCAL_SCHEMA_REF or "./reel.schema.json",
        "schema_version": 1,
        "id": sanitize_project_id(project_id),
        "seed": int(seed) & 0xFFFFFFFF,
        "output": {
            "width": width,
            "height": height,
            "fps": storyboard.fps,
        },
        "delivery": {
            "language": iso3,
        },
        "constraints": dict(intent.constraints),
        "scenes": scenes,
        "audio": {
            "enabled": not no_audio,
            "gain_db": -14,
            "cues": [] if no_audio else cues,
        },
    }
    exc_map: dict[str, list[list[int]]] = {}
    if silence_exceptions and not no_audio:
        exc_map["silence"] = silence_exceptions
    if cursor > 0:
        exc_map["freeze"] = [[0, cursor]]
    if exc_map:
        plan["quality"] = {"exceptions": exc_map}

    assert_safe_compiled_plan(plan)
    validate(plan)
    return plan
