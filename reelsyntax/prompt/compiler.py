from fractions import Fraction
import importlib.util
import re
from typing import Any

from ..migration import LOCAL_SCHEMA_REF
from ..palette import contrast_ratio, hex_to_rgb, mix_oklab, rgb_to_hex
from ..project import validate
from ..typography import measure_tracked_text, resolve_font
from ..variants import LANGUAGES
from .intent import ParsedIntent
from .storyboard import StoryboardPlan, distribute_frames

LEGACY_DRAWING_RECIPES = frozenset({"assembly", "rings", "signal", "title"})

MUSIC_GRID_BPM = 120
FLASH_SAFE_TRANSITIONS = frozenset({"cut", "cross_dissolve"})

WAVE_FORMAT_KICKERS: dict[str, dict[str, dict[str, str]]] = {
    "explainer-slides": {
        "chapter": {"en": "CHAPTER", "tr": "BÖLÜM", "de": "KAPITEL"},
        "recap": {"en": "RECAP", "tr": "ÖZET", "de": "FAZIT"},
    },
    "lyric-video": {
        "line": {"en": "LINE", "tr": "DİZE", "de": "ZEILE"},
    },
    "music-visualizer": {
        "bar": {"en": "BAR", "tr": "ÖLÇÜ", "de": "TAKT"},
    },
    "channel-intro": {
        "open": {"en": "CHANNEL", "tr": "KANAL", "de": "KANAL"},
        "body": {"en": "NOW", "tr": "ŞİMDİ", "de": "JETZT"},
        "close": {"en": "SUBSCRIBE", "tr": "ABONE OL", "de": "ABONNIEREN"},
    },
}

PENTATONIC_HZ = (220, 262, 294, 330, 392)


def music_grid_frames(fps: str, bpm: int = MUSIC_GRID_BPM) -> tuple[int, int]:
    beat = max(1, int(round(float(Fraction(fps)) * 60.0 / bpm)))
    return beat, beat * 4


def quantize_durations_to_grid(durations: list[int], unit: int) -> list[int]:
    total = sum(durations)
    count = len(durations)
    if unit < 12 or count == 0 or total // unit < count:
        return list(durations)
    slots = total // unit
    raw = [slots * d / total for d in durations]
    units = [max(1, int(r)) for r in raw]
    order = sorted(range(count), key=lambda i: (raw[i] - int(raw[i]), -i), reverse=True)
    cursor = 0
    while sum(units) < slots:
        units[order[cursor % count]] += 1
        cursor += 1
    while sum(units) > slots:
        slot = max(range(count), key=lambda i: (units[i], -i))
        units[slot] -= 1
    out = [u * unit for u in units]
    out[-1] += total - sum(out)
    return out


def reweight_durations(durations: list[int], weights: list[int]) -> list[int]:
    if len(weights) != len(durations) or not durations:
        return list(durations)
    return distribute_frames(sum(durations), weights)


def _wave_kicker(format_id: str, role: str, lang: str) -> str:
    table = WAVE_FORMAT_KICKERS[format_id][role]
    return table.get(lang, table["en"])

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
        max_w = w * (right_frac - 0.07) * 0.90
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


def _trim_by_char_budget(text: str, max_chars: int) -> tuple[str, str]:
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_chars:
        return cleaned, ""
    words = cleaned.split(" ")
    for take in range(len(words) - 1, 0, -1):
        prefix = " ".join(words[:take])
        if len(prefix) <= max_chars:
            return prefix, " ".join(words[take:])
    return words[0][:max_chars], (words[0][max_chars:] + " " + " ".join(words[1:])).strip()


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
    if importlib.util.find_spec("PIL") is None:
        scale_ratio = max(0.6, width / 1080.0)
        h_budget = max(8, int(round(12 * scale_ratio)))
        sub_budget = max(16, int(round(32 * scale_ratio)))
        fh, over = _trim_by_char_budget(heading[:120], h_budget)
        c_sub = subheading[:120]
        if spill_heading_to_subheading and over and not c_sub:
            c_sub = over[:120]
        elif spill_heading_to_subheading and over and c_sub:
            c_sub = f"{over} - {c_sub}"[:120]
        fsub, _ = _trim_by_char_budget(c_sub, sub_budget)
        return fh, fsub

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
    is_explainer_fmt = intent.format_hint == "explainer-slides"
    is_lyric_fmt = intent.format_hint == "lyric-video"
    is_visualizer_fmt = intent.format_hint == "music-visualizer"
    is_intro_fmt = intent.format_hint == "channel-intro"
    lang_primary = intent.video_lang.split("-", 1)[0].lower()
    total_beats = len(storyboard.beats)
    fps_float = float(Fraction(storyboard.fps))
    max_hook_frames = max(24, int(round(2.0 * fps_float)))
    grid_beat, grid_bar = music_grid_frames(storyboard.fps)

    beat_durations = [int(b.duration_frames) for b in storyboard.beats]
    if is_hook_fmt and total_beats >= 2 and beat_durations[0] > max_hook_frames:
        excess = beat_durations[0] - max_hook_frames
        beat_durations[0] = max_hook_frames
        beat_durations[-1] += excess
    if is_explainer_fmt and total_beats >= 3:
        beat_durations = reweight_durations(
            beat_durations,
            [3] + [5 if i % 2 == 0 else 4 for i in range(total_beats - 2)] + [4],
        )
    elif is_intro_fmt and total_beats >= 3:
        beat_durations = reweight_durations(beat_durations, [4] + [5] * (total_beats - 2) + [3])
    elif is_lyric_fmt:
        beat_durations = quantize_durations_to_grid(beat_durations, grid_beat)
    elif is_visualizer_fmt:
        bar_snapped = quantize_durations_to_grid(beat_durations, grid_bar)
        beat_durations = bar_snapped if bar_snapped != beat_durations else quantize_durations_to_grid(beat_durations, grid_beat)

    hook_kickers = {"tr": "DİKKAT", "de": "STOPP", "en": "HOOK"}
    payoff_kickers = {"tr": "SONUÇ", "de": "FAZIT", "en": "PAYOFF"}

    for idx, beat in enumerate(storyboard.beats):
        dur_frames = beat_durations[idx]
        chosen_recipe = beat.recipe
        is_last = idx == total_beats - 1
        if is_kinetic_fmt:
            chosen_recipe = "signal" if (is_last and total_beats >= 3) else "kinetic-type"
        elif is_hook_fmt:
            if idx == 0:
                chosen_recipe = "prism-monolith"
            elif is_last:
                chosen_recipe = "kinetic-type"
        elif is_explainer_fmt:
            chosen_recipe = "kinetic-type" if (idx == 0 or is_last) else "assembly"
        elif is_lyric_fmt:
            chosen_recipe = "kinetic-type"
        elif is_visualizer_fmt:
            chosen_recipe = "signal" if idx % 2 == 0 else "rings"
        elif is_intro_fmt:
            chosen_recipe = "prism-monolith" if idx == 0 else "kinetic-type"
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
                elif is_last:
                    params["kicker"] = payoff_kickers.get(lang_primary, "PAYOFF")
                else:
                    params["kicker"] = f"{idx + 1:02d}"
            elif is_explainer_fmt:
                if is_last and total_beats >= 3:
                    params["kicker"] = _wave_kicker("explainer-slides", "recap", lang_primary)
                else:
                    params["kicker"] = f"{_wave_kicker('explainer-slides', 'chapter', lang_primary)} {idx + 1:02d}/{total_beats:02d}"
            elif is_lyric_fmt:
                params["kicker"] = f"{_wave_kicker('lyric-video', 'line', lang_primary)} {idx + 1:02d}"
            elif is_visualizer_fmt:
                bar_aligned = sum(beat_durations[:idx]) % grid_bar == 0 and dur_frames >= grid_bar
                start_bar = sum(beat_durations[:idx]) // grid_bar + 1 if bar_aligned else idx + 1
                params["kicker"] = f"{_wave_kicker('music-visualizer', 'bar', lang_primary)} {start_bar:02d}"
            elif is_intro_fmt:
                role = "open" if idx == 0 else ("close" if is_last and total_beats >= 3 else "body")
                params["kicker"] = _wave_kicker("channel-intro", role, lang_primary)
            intro_card_only = is_intro_fmt and (idx == 0 or (is_last and total_beats >= 3))
            fitted_h, fitted_sub = fit_scene_text_fields(
                beat.heading or "",
                "" if intro_card_only else (beat.subheading or ""),
                recipe=chosen_recipe,
                width=width,
                height=height,
                spill_heading_to_subheading=not intro_card_only,
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
            elif (is_kinetic_fmt or is_hook_fmt or is_explainer_fmt) and idx < total_beats - 1:
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
            elif is_visualizer_fmt:
                for bar_offset in range(0, dur_frames, grid_bar):
                    remaining = dur_frames - bar_offset
                    if remaining < 6 and bar_offset > 0:
                        continue
                    bar_index = (cursor + bar_offset) // grid_bar
                    cues.append({
                        "frame": cursor + bar_offset,
                        "frequency": PENTATONIC_HZ[bar_index % len(PENTATONIC_HZ)],
                        "duration_frames": min(18, remaining),
                        "instrument": "harmonic_pluck",
                    })
            elif is_lyric_fmt:
                cues.append({
                    "frame": cursor,
                    "frequency": PENTATONIC_HZ[idx % len(PENTATONIC_HZ)],
                    "duration_frames": cue_dur,
                    "instrument": "harmonic_pluck",
                })
            elif is_intro_fmt:
                cues.append({
                    "frame": cursor,
                    "frequency": 262 if (is_last and total_beats >= 3) else (392 if idx == 0 else 523),
                    "duration_frames": cue_dur,
                    "instrument": "warm_pad" if (is_last and total_beats >= 3) else "harmonic_pluck",
                })
            else:
                cues.append({
                    "frame": cursor,
                    "frequency": note_frequencies[idx % len(note_frequencies)],
                    "duration_frames": cue_dur,
                    "instrument": "harmonic_pluck" if idx % 2 == 0 else "warm_pad",
                })
        cursor += dur_frames

    if not no_audio:
        ordered_cues = sorted(cues, key=lambda c: int(c["frame"]))
        for pos, cue in enumerate(ordered_cues):
            gap_start = int(cue["frame"]) + int(cue["duration_frames"])
            gap_end = int(ordered_cues[pos + 1]["frame"]) if pos + 1 < len(ordered_cues) else cursor
            if gap_start < gap_end:
                silence_exceptions.append([gap_start, gap_end])

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
