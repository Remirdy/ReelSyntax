import copy
from fractions import Fraction
import math
from pathlib import Path
import re
from typing import Any

from ReelSyntax_Skills.tools.registry import atomic_json, contained_path, digest, read_json

from .project import validate
from .schema import REEL_V1_SCHEMA_URL, project_schema

CURRENT_SCHEMA_VERSION = 1
LOCAL_SCHEMA_REF = "./reel.schema.json"

NTSC_RATIONALS: dict[str, str] = {
    "23.976": "24000/1001",
    "23.98": "24000/1001",
    "29.97": "30000/1001",
    "59.94": "60000/1001",
}


def normalize_fps_value(value: Any) -> str:
    if isinstance(value, str):
        stripped = value.strip()
        if re.fullmatch(r"[1-9][0-9]*/[1-9][0-9]*", stripped):
            return stripped
        if re.fullmatch(r"[1-9][0-9]*", stripped):
            return f"{stripped}/1"
        if stripped in NTSC_RATIONALS:
            return NTSC_RATIONALS[stripped]
        try:
            as_num = float(stripped)
        except ValueError as error:
            raise ValueError(f"output.fps: cannot migrate fps value {value!r}") from error
        return normalize_fps_value(as_num)
    if type(value) is int and value >= 1:
        return f"{value}/1"
    if type(value) is float and math.isfinite(value) and value > 0:
        for approx, rational in ((23.976, "24000/1001"), (29.97, "30000/1001"), (59.94, "60000/1001")):
            if abs(value - approx) < 0.02:
                return rational
        rounded = round(value)
        if abs(value - rounded) < 1e-6 and rounded >= 1:
            return f"{rounded}/1"
    raise ValueError(f"output.fps: cannot migrate fps value {value!r}")


def migrate_plan(raw_plan: dict[str, Any], *, remote_schema: bool = False) -> tuple[dict[str, Any], list[str], int]:
    if not isinstance(raw_plan, dict):
        raise ValueError("Project file must contain a JSON object")

    plan = copy.deepcopy(raw_plan)
    changes: list[str] = []

    raw_version = plan.get("schema_version")
    if raw_version is None:
        from_version = 0
        plan["schema_version"] = CURRENT_SCHEMA_VERSION
        changes.append("Set missing schema_version to 1")
    elif type(raw_version) is int and raw_version == 0:
        from_version = 0
        plan["schema_version"] = CURRENT_SCHEMA_VERSION
        changes.append("Upgraded schema_version from 0 to 1")
    elif type(raw_version) is int and raw_version == CURRENT_SCHEMA_VERSION:
        from_version = CURRENT_SCHEMA_VERSION
    elif type(raw_version) is int and raw_version > CURRENT_SCHEMA_VERSION:
        raise ValueError(
            f"Project requires schema_version {raw_version}; installed ReelSyntax supports up to version {CURRENT_SCHEMA_VERSION}"
        )
    else:
        raise ValueError(f"Invalid schema_version: {raw_version!r}")

    desired_schema = REEL_V1_SCHEMA_URL if remote_schema else plan.get("$schema", LOCAL_SCHEMA_REF)
    if plan.get("$schema") != desired_schema:
        plan["$schema"] = desired_schema
        changes.append(f"Set $schema to {desired_schema}")

    output = plan.get("output")
    if not isinstance(output, dict):
        raise ValueError("output: expected an object")
    if "fps" in output:
        normalized_fps = normalize_fps_value(output["fps"])
        if output["fps"] != normalized_fps:
            output["fps"] = normalized_fps
            changes.append(f"Normalized output.fps to {normalized_fps}")
    fps_fraction = Fraction(output["fps"]) if isinstance(output.get("fps"), str) and "/" in output["fps"] else Fraction(30, 1)

    scenes = plan.get("scenes")
    if isinstance(scenes, list):
        for idx, scene in enumerate(scenes):
            if not isinstance(scene, dict):
                continue
            sid = scene.get("id", f"scene-{idx + 1}")
            if "duration_frames" not in scene and "duration_sec" in scene:
                sec = scene.pop("duration_sec")
                if type(sec) not in {int, float} or not math.isfinite(sec) or sec <= 0:
                    raise ValueError(f"{sid}.duration_sec: expected positive number")
                frames = max(1, int(round(float(sec) * float(fps_fraction))))
                scene["duration_frames"] = frames
                changes.append(f"Converted {sid}.duration_sec ({sec}) to duration_frames ({frames})")
            if "params" not in scene:
                scene["params"] = {}
                changes.append(f"Added empty params object on scene {sid}")
            params = scene.get("params")
            if isinstance(params, dict):
                if "title" in params:
                    legacy_title = params.pop("title")
                    if "heading" not in params:
                        params["heading"] = legacy_title
                    changes.append(f"Renamed {sid}.params.title to heading")
                if "subtitle" in params:
                    legacy_sub = params.pop("subtitle")
                    if "subheading" not in params:
                        params["subheading"] = legacy_sub
                    changes.append(f"Renamed {sid}.params.subtitle to subheading")

    if "audio" not in plan:
        plan["audio"] = {"enabled": False, "gain_db": -14, "cues": []}
        changes.append("Added default disabled audio block")
    elif isinstance(plan["audio"], dict):
        audio = plan["audio"]
        if "volume_db" in audio:
            vol = audio.pop("volume_db")
            if "gain_db" not in audio:
                audio["gain_db"] = vol
            changes.append("Renamed audio.volume_db to audio.gain_db")
        if "gain_db" not in audio:
            audio["gain_db"] = -14
            changes.append("Set default audio.gain_db to -14")
        if "cues" not in audio:
            audio["cues"] = []
            changes.append("Added empty audio.cues list")

    validate(plan)
    return plan, changes, from_version


def migrate_project(
    project: str | Path,
    *,
    dry_run: bool = False,
    remote_schema: bool = False,
) -> dict[str, Any]:
    root = Path(project).resolve(strict=True)
    reel_path = contained_path(root, "reel.json")
    raw_bytes = reel_path.read_bytes()
    original = read_json(reel_path, max_bytes=2_000_000)
    migrated, changes, from_version = migrate_plan(original, remote_schema=remote_schema)

    local_schema_path = contained_path(root, "reel.schema.json", must_exist=False)
    write_local_schema = migrated.get("$schema") == LOCAL_SCHEMA_REF and not local_schema_path.is_file()
    if write_local_schema:
        changes.append("Write local reel.schema.json for editor completion")

    changed = bool(changes) and (migrated != original or write_local_schema)
    backup_rel: str | None = None

    if changed and not dry_run:
        if migrated != original:
            short_hash = digest(raw_bytes)[:12]
            backup_rel = f".reelsyntax/migrations/reel.before-v{CURRENT_SCHEMA_VERSION}-{short_hash}.json"
            backup_path = contained_path(root, backup_rel, must_exist=False)
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            if not backup_path.exists():
                backup_path.write_bytes(raw_bytes)
            atomic_json(reel_path, migrated)
        if write_local_schema:
            atomic_json(local_schema_path, project_schema())

    metadata = validate(migrated)
    return {
        "project": str(root),
        "from_version": from_version,
        "to_version": CURRENT_SCHEMA_VERSION,
        "changed": changed,
        "dry_run": dry_run,
        "backup": backup_rel,
        "changes": changes,
        **metadata,
    }
