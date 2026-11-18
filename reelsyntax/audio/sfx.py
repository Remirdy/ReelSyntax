from typing import Any

TRANSITION_SFX_MAP: dict[str, dict[str, Any]] = {
    "wipe_left": {"instrument": "whoosh", "frequency": 340, "duration_frames": 10},
    "slide_left": {"instrument": "whoosh", "frequency": 310, "duration_frames": 9},
    "slide_right": {"instrument": "whoosh", "frequency": 310, "duration_frames": 9},
    "radial": {"instrument": "harmonic_pluck", "frequency": 494, "duration_frames": 12},
    "glitch": {"instrument": "click_transient", "frequency": 1420, "duration_frames": 6},
    "cross_dissolve": {"instrument": "warm_pad", "frequency": 294, "duration_frames": 14},
}


def build_transition_sfx_cues(scenes: list[dict[str, Any]], *, include_opening_hit: bool = False) -> list[dict[str, Any]]:
    cues: list[dict[str, Any]] = []
    cursor = 0
    for idx, scene in enumerate(scenes):
        dur = int(scene["duration_frames"])
        if idx == 0 and include_opening_hit:
            cues.append({
                "frame": 0,
                "frequency": 68,
                "duration_frames": min(16, dur),
                "instrument": "sub_impact",
            })
        elif idx > 0 and "transition" in scene:
            ttype = str(scene["transition"].get("type", "cut"))
            spec = TRANSITION_SFX_MAP.get(ttype)
            if spec is not None:
                lead = min(int(scene["transition"].get("duration_frames", 6)), cursor)
                start_f = max(0, cursor - lead // 2)
                cues.append({
                    "frame": start_f,
                    "frequency": int(spec["frequency"]),
                    "duration_frames": min(int(spec["duration_frames"]), dur),
                    "instrument": str(spec["instrument"]),
                })
        cursor += dur
    return cues
