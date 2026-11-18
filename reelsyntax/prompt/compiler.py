import re
from typing import Any

from ..migration import LOCAL_SCHEMA_REF
from ..palette import contrast_ratio, hex_to_rgb, mix_oklab, rgb_to_hex
from ..project import validate
from ..variants import LANGUAGES
from .intent import ParsedIntent
from .storyboard import StoryboardPlan

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


def ensure_accessible_palette(background: str, foreground: str, accent: str) -> tuple[str, str, str]:
    bg_rgb = hex_to_rgb(background)
    fg_rgb = hex_to_rgb(foreground)
    ac_rgb = hex_to_rgb(accent)

    bg_is_dark = sum(bg_rgb) < 384
    pole = (250, 250, 252) if bg_is_dark else (20, 22, 26)

    step = 0.0
    while contrast_ratio(fg_rgb, bg_rgb) < 4.6 and step < 1.0:
        step = min(1.0, step + 0.15)
        fg_rgb = mix_oklab(fg_rgb, pole, step)

    ac_step = 0.0
    while contrast_ratio(ac_rgb, bg_rgb) < 3.2 and ac_step < 1.0:
        ac_step = min(1.0, ac_step + 0.15)
        ac_rgb = mix_oklab(ac_rgb, pole, ac_step)

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

    for idx, beat in enumerate(storyboard.beats):
        params: dict[str, Any] = {
            "background": bg_hex,
            "foreground": fg_hex,
            "accent": ac_hex,
        }
        if not no_text:
            if beat.heading:
                params["heading"] = beat.heading[:120]
            if beat.subheading:
                params["subheading"] = beat.subheading[:120]
        if beat.recipe == "data-horizon":
            params["series"] = [24.0, 42.0, 68.0, 91.0]

        scene_entry: dict[str, Any] = {
            "id": sanitize_project_id(beat.id),
            "duration_frames": beat.duration_frames,
            "recipe": beat.recipe,
            "engine": "pillow",
            "params": params,
        }
        if idx > 0 and beat.duration_frames >= 24:
            scene_entry["transition"] = {
                "type": "cross_dissolve",
                "duration_frames": min(8, beat.duration_frames // 4),
            }
        if not camera_locked and beat.recipe == "prism-monolith":
            scene_entry["camera"] = {"preset": "dolly_in", "focal_mm": 50.0}
        scenes.append(scene_entry)

        if not no_audio:
            cue_dur = min(18, beat.duration_frames)
            cues.append({
                "frame": cursor,
                "frequency": note_frequencies[idx % len(note_frequencies)],
                "duration_frames": cue_dur,
                "instrument": "harmonic_pluck" if idx % 2 == 0 else "warm_pad",
            })
            if cursor + cue_dur < cursor + beat.duration_frames:
                silence_exceptions.append([cursor + cue_dur, cursor + beat.duration_frames])
        cursor += beat.duration_frames

    lang_primary = intent.video_lang.split("-", 1)[0].lower()
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
    if silence_exceptions and not no_audio:
        plan["quality"] = {"exceptions": {"silence": silence_exceptions}}

    assert_safe_compiled_plan(plan)
    validate(plan)
    return plan
