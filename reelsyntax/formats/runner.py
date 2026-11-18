import copy
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
from pathlib import Path
from typing import Any, Callable

from ReelSyntax_Skills.tools.registry import atomic_json, contained_path, read_json

from ..project import validate
from ..prompt.compiler import compile_storyboard_to_project
from ..prompt.intent import ParsedIntent, parse_intent, wrap_untrusted_prompt_data
from ..prompt.providers.base import LLMProvider
from ..prompt.repair import generate_with_repair
from ..prompt.storyboard import build_storyboard
from ..schema import project_schema
from .registry import get_format
from .schema import validate_format_manifest

IDEA_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["hook", "angle", "summary"],
    "properties": {
        "hook": {"type": "string", "maxLength": 96},
        "angle": {"type": "string", "maxLength": 140},
        "summary": {"type": "string", "maxLength": 180},
    },
}

LOOK_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["background", "foreground", "accent"],
    "properties": {
        "background": {"type": "string", "maxLength": 7},
        "foreground": {"type": "string", "maxLength": 7},
        "accent": {"type": "string", "maxLength": 7},
    },
}

GateCallback = Callable[[dict[str, Any], dict[str, Any]], str]


def derive_step_seed(project_seed: int, step_id: str) -> int:
    raw = f"{project_seed}:{step_id}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:4], "big")


def state_file_path(project_dir: Path) -> Path:
    return contained_path(Path(project_dir), ".formats/state.json", must_exist=False)


def load_runner_state(project_dir: Path) -> dict[str, Any]:
    path = state_file_path(Path(project_dir).resolve(strict=True))
    if not path.is_file():
        raise ValueError("No format state found in .formats/state.json")
    return read_json(path, max_bytes=1_048_576)


def _save_runner_state(project_dir: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    atomic_json(state_file_path(project_dir), state)


def _clamp_duration(intent: ParsedIntent, manifest: dict[str, Any]) -> ParsedIntent:
    low = int(manifest["duration_sec"]["min"])
    high = int(manifest["duration_sec"]["max"])
    clamped_dur = max(low, min(high, intent.duration_sec))
    allowed_aspects = manifest["aspect"]
    chosen_aspect = intent.aspect if intent.aspect in allowed_aspects else allowed_aspects[0]
    if clamped_dur == intent.duration_sec and chosen_aspect == intent.aspect:
        return intent
    return ParsedIntent(
        raw_prompt=intent.raw_prompt,
        sanitized_prompt=intent.sanitized_prompt,
        prompt_lang=intent.prompt_lang,
        video_lang=intent.video_lang,
        aspect=chosen_aspect,
        duration_sec=clamped_dur,
        fps=intent.fps,
        tone=intent.tone,
        formality=intent.formality,
        palette=intent.palette,
        format_hint=manifest["id"],
        constraints=intent.constraints,
        routed_skills=intent.routed_skills,
    )


def _slice_pilot_plan(plan: dict[str, Any], max_seconds: int = 5) -> dict[str, Any]:
    fps = Fraction(plan["output"]["fps"])
    max_frames = max(24, int(round(max_seconds * float(fps))))
    pilot = copy.deepcopy(plan)
    kept_scenes: list[dict[str, Any]] = []
    remaining = max_frames
    for scene in pilot["scenes"]:
        if remaining <= 0:
            break
        take = min(scene["duration_frames"], remaining)
        if take < 12:
            break
        scene_copy = copy.deepcopy(scene)
        scene_copy["duration_frames"] = take
        if "transition" in scene_copy and scene_copy["transition"].get("duration_frames", 1) > take // 2:
            scene_copy["transition"]["duration_frames"] = max(1, take // 2)
        kept_scenes.append(scene_copy)
        remaining -= take
    if not kept_scenes:
        first = copy.deepcopy(pilot["scenes"][0])
        first["duration_frames"] = min(first["duration_frames"], max_frames)
        kept_scenes = [first]
    total_pilot = sum(s["duration_frames"] for s in kept_scenes)
    pilot["scenes"] = kept_scenes
    if pilot["audio"]["enabled"]:
        cues = []
        for cue in pilot["audio"]["cues"]:
            if cue["frame"] < total_pilot:
                c_copy = dict(cue)
                c_copy["duration_frames"] = min(c_copy["duration_frames"], total_pilot - cue["frame"])
                cues.append(c_copy)
        pilot["audio"]["cues"] = cues
    if "quality" in pilot and "exceptions" in pilot["quality"]:
        trimmed_exc: dict[str, list[list[int]]] = {}
        for key, intervals in pilot["quality"]["exceptions"].items():
            clipped = [[a, min(b, total_pilot)] for a, b in intervals if a < total_pilot and min(b, total_pilot) > a]
            if clipped:
                trimmed_exc[key] = clipped
        pilot["quality"] = {"exceptions": trimmed_exc} if trimmed_exc else {}
        if not pilot["quality"]:
            pilot.pop("quality", None)
    validate(pilot)
    return pilot


def _execute_render_step(
    project_root: Path,
    step: dict[str, Any],
    *,
    dry_run_render: bool = False,
) -> dict[str, Any]:
    prof = step["profile"]
    scope = step.get("scope", "full")
    plan = read_json(contained_path(project_root, "reel.json"))

    if dry_run_render:
        return {
            "profile": prof,
            "scope": scope,
            "simulated": True,
            "frames": sum(s["duration_frames"] for s in plan["scenes"]),
        }

    if prof == "snapshot":
        from ..drawing import draw_scene_frame

        snap_dir = contained_path(project_root, ".formats/snapshots", must_exist=False)
        snap_dir.mkdir(parents=True, exist_ok=True)
        previews: list[str] = []
        for scene in plan["scenes"]:
            if scene["engine"] == "pillow":
                mid = scene["duration_frames"] // 2
                img = draw_scene_frame(scene, mid, 480, 270 if plan["output"]["width"] >= plan["output"]["height"] else 854, Fraction(plan["output"]["fps"]), plan["seed"])
                out_file = snap_dir / f"{scene['id']}.png"
                img.save(out_file)
                previews.append(out_file.relative_to(project_root).as_posix())
        return {"profile": "snapshot", "previews": previews}

    from ..render import render

    if scope == "first_5s":
        pilot_dir = contained_path(project_root, ".formats/pilot", must_exist=False)
        pilot_dir.mkdir(parents=True, exist_ok=True)
        pilot_plan = _slice_pilot_plan(plan, max_seconds=5)
        atomic_json(pilot_dir / "reel.json", pilot_plan)
        res = render(pilot_dir, profile="draft")
        return {
            "profile": "draft",
            "scope": "first_5s",
            "artifact": f".formats/pilot/{res['artifact']}",
            "frames": res["frames"],
        }

    res = render(project_root, profile=prof)
    return {"profile": prof, "scope": "full", "artifact": res["artifact"], "frames": res["frames"]}


def invalidate_from_step(state: dict[str, Any], manifest: dict[str, Any], step_id: str) -> int:
    step_ids = [s["id"] for s in manifest["steps"]]
    if step_id not in step_ids:
        raise ValueError(f"Step {step_id!r} does not exist in format {manifest['id']!r}")
    idx = step_ids.index(step_id)
    for sid in step_ids[idx:]:
        state["completed_steps"].pop(sid, None)
        state["approvals"].pop(sid, None)
    state["current_step_index"] = idx
    state["status"] = "in_progress"
    return idx


class FormatRunner:
    def __init__(
        self,
        manifest: dict[str, Any],
        provider: LLMProvider,
        *,
        max_attempts: int = 3,
        dry_run_render: bool = False,
    ) -> None:
        self.manifest = validate_format_manifest(manifest)
        self.provider = provider
        self.max_attempts = max_attempts
        self.dry_run_render = dry_run_render

    @classmethod
    def from_id(
        cls,
        format_id: str,
        provider: LLMProvider,
        *,
        extra_roots: tuple[Path, ...] = (),
        max_attempts: int = 3,
        dry_run_render: bool = False,
    ) -> "FormatRunner":
        manifest = get_format(format_id, extra_roots=extra_roots)
        return cls(manifest, provider, max_attempts=max_attempts, dry_run_render=dry_run_render)

    def initialize_project(
        self,
        project_dir: Path | str,
        prompt: str,
        *,
        seed: int = 42,
        video_lang: str | None = None,
        aspect: str | None = None,
        duration_sec: int | None = None,
    ) -> dict[str, Any]:
        root = Path(project_dir).absolute()
        if root.is_symlink():
            raise ValueError("Project path cannot be a symbolic link")
        root.mkdir(parents=True, exist_ok=True)

        parsed = parse_intent(
            prompt,
            video_lang=video_lang,
            format_id=self.manifest["id"],
            aspect=aspect,
            duration_sec=duration_sec,
        )
        bounded_intent = _clamp_duration(parsed, self.manifest)
        atomic_json(root / "reel.schema.json", project_schema())

        state: dict[str, Any] = {
            "schema_version": 1,
            "format_id": self.manifest["id"],
            "format_version": self.manifest["version"],
            "provider": self.provider.name,
            "seed": int(seed) & 0xFFFFFFFF,
            "prompt": prompt,
            "intent": bounded_intent.to_dict(),
            "current_step_index": 0,
            "status": "initialized",
            "step_seeds": {},
            "step_edits": {},
            "completed_steps": {},
            "approvals": {},
        }
        _save_runner_state(root, state)
        return state

    def run(
        self,
        project_dir: Path | str,
        *,
        auto_approve: bool = False,
        gate_callback: GateCallback | None = None,
        stop_after_step: str | None = None,
    ) -> dict[str, Any]:
        root = Path(project_dir).resolve(strict=True)
        state = load_runner_state(root)
        steps = self.manifest["steps"]
        intent = ParsedIntent(
            **{
                **state["intent"],
                "routed_skills": tuple(state["intent"]["routed_skills"]),
            }
        )

        idx = int(state["current_step_index"])
        while idx < len(steps):
            step = steps[idx]
            sid = step["id"]
            step_seed = derive_step_seed(state["seed"], sid)
            state["step_seeds"][sid] = step_seed

            if step.get("profile") == "hero":
                gated_ids = [s["id"] for s in steps[:idx] if s.get("gate") == "approve"]
                unapproved = [gid for gid in gated_ids if not state["approvals"].get(gid)]
                if unapproved and not auto_approve:
                    raise ValueError(f"Hero render blocked: unapproved gates {unapproved}")

            if sid not in state["completed_steps"]:
                output = self._run_single_step(root, step, intent, state, step_seed)
                state["completed_steps"][sid] = output
                _save_runner_state(root, state)

            if step.get("gate") == "approve" and not state["approvals"].get(sid):
                if auto_approve:
                    state["approvals"][sid] = {"approved": True, "mode": "auto"}
                    _save_runner_state(root, state)
                elif gate_callback is not None:
                    decision = gate_callback(step, state["completed_steps"][sid])
                    if decision == "approve":
                        state["approvals"][sid] = {"approved": True, "mode": "callback"}
                        _save_runner_state(root, state)
                    elif decision == "back" and idx > 0:
                        prev_id = steps[idx - 1]["id"]
                        idx = invalidate_from_step(state, self.manifest, prev_id)
                        _save_runner_state(root, state)
                        continue
                    elif decision == "edit":
                        idx = invalidate_from_step(state, self.manifest, sid)
                        _save_runner_state(root, state)
                        state["status"] = "awaiting_edit"
                        _save_runner_state(root, state)
                        return state
                    else:
                        state["current_step_index"] = idx
                        state["status"] = "awaiting_approval"
                        state["pending_gate"] = sid
                        _save_runner_state(root, state)
                        return state
                else:
                    state["current_step_index"] = idx
                    state["status"] = "awaiting_approval"
                    state["pending_gate"] = sid
                    _save_runner_state(root, state)
                    return state

            state.pop("pending_gate", None)
            idx += 1
            state["current_step_index"] = idx
            _save_runner_state(root, state)
            if stop_after_step == sid:
                state["status"] = "paused"
                _save_runner_state(root, state)
                return state

        state["status"] = "completed"
        _save_runner_state(root, state)
        return state

    def approve_pending_gate(self, project_dir: Path | str) -> dict[str, Any]:
        root = Path(project_dir).resolve(strict=True)
        state = load_runner_state(root)
        idx = int(state["current_step_index"])
        steps = self.manifest["steps"]
        if idx >= len(steps):
            return state
        sid = steps[idx]["id"]
        if sid not in state["completed_steps"]:
            raise ValueError(f"Cannot approve step {sid!r} before it executes")
        state["approvals"][sid] = {"approved": True, "mode": "manual"}
        state.pop("pending_gate", None)
        state["current_step_index"] = idx + 1
        state["status"] = "in_progress"
        _save_runner_state(root, state)
        return state

    def edit_step(self, project_dir: Path | str, step_id: str, instruction: str) -> dict[str, Any]:
        root = Path(project_dir).resolve(strict=True)
        state = load_runner_state(root)
        invalidate_from_step(state, self.manifest, step_id)
        state.setdefault("step_edits", {})[step_id] = instruction.strip()
        _save_runner_state(root, state)
        return state

    def _run_single_step(
        self,
        root: Path,
        step: dict[str, Any],
        intent: ParsedIntent,
        state: dict[str, Any],
        step_seed: int,
    ) -> dict[str, Any]:
        sid = step["id"]
        stype = step["type"]
        edit_note = state.get("step_edits", {}).get(sid, "")
        augmented_prompt = f"{intent.sanitized_prompt}\nRevision note: {edit_note}" if edit_note else intent.sanitized_prompt
        step_intent = parse_intent(
            augmented_prompt,
            video_lang=intent.video_lang,
            format_id=self.manifest["id"],
            aspect=intent.aspect,
            duration_sec=intent.duration_sec,
            tone=intent.tone,
            formality=intent.formality,
        )

        if stype == "llm":
            if sid == "idea":
                out, attempts = generate_with_repair(
                    self.provider,
                    system="Propose a concise video hook, angle, and summary in the target language.",
                    user=wrap_untrusted_prompt_data(
                        step_intent.sanitized_prompt,
                        video_lang=step_intent.video_lang,
                        aspect=step_intent.aspect,
                        duration_sec=step_intent.duration_sec,
                    ),
                    schema=IDEA_SCHEMA,
                    seed=step_seed,
                    max_attempts=self.max_attempts,
                )
                return {**out, "attempts": attempts}
            if sid == "look":
                out, attempts = generate_with_repair(
                    self.provider,
                    system="Select accessible hex colors (background, foreground, accent) for the video.",
                    user=wrap_untrusted_prompt_data(
                        step_intent.sanitized_prompt,
                        video_lang=step_intent.video_lang,
                        aspect=step_intent.aspect,
                        duration_sec=step_intent.duration_sec,
                    ),
                    schema=LOOK_SCHEMA,
                    seed=step_seed,
                    max_attempts=self.max_attempts,
                )
                if (root / "reel.json").is_file():
                    from ..prompt.compiler import ensure_accessible_palette

                    bg, fg, acc = ensure_accessible_palette(
                        out.get("background", "#14191f"),
                        out.get("foreground", "#edf1f5"),
                        out.get("accent", "#4c8b93"),
                    )
                    plan = read_json(root / "reel.json")
                    for scene in plan["scenes"]:
                        scene["params"]["background"] = bg
                        scene["params"]["foreground"] = fg
                        scene["params"]["accent"] = acc
                    validate(plan)
                    atomic_json(root / "reel.json", plan)
                return {**out, "attempts": attempts}

            storyboard = build_storyboard(step_intent, self.provider, seed=step_seed, max_attempts=self.max_attempts)
            compiled = compile_storyboard_to_project(
                storyboard,
                step_intent,
                project_id=root.name,
                seed=state["seed"],
            )
            atomic_json(root / "reel.json", compiled)
            return {
                "scene_count": len(compiled["scenes"]),
                "frames": sum(s["duration_frames"] for s in compiled["scenes"]),
                "attempts": storyboard.attempts,
            }

        if stype == "render":
            if not (root / "reel.json").is_file():
                storyboard = build_storyboard(step_intent, self.provider, seed=step_seed, max_attempts=self.max_attempts)
                compiled = compile_storyboard_to_project(storyboard, step_intent, project_id=root.name, seed=state["seed"])
                atomic_json(root / "reel.json", compiled)
            return _execute_render_step(root, step, dry_run_render=self.dry_run_render)

        if stype == "qc":
            if self.dry_run_render:
                plan = read_json(contained_path(root, "reel.json"))
                meta = validate(plan)
                return {"technical_status": "pass", "simulated": True, **meta}
            from ..quality import check

            target_prof = "hero" if (root / "output/hero-manifest.json").is_file() else "draft"
            qc_res = check(root, profile=target_prof)
            return {
                "profile": target_prof,
                "technical_status": qc_res["technical_status"],
                "checks_count": len(qc_res["checks"]),
            }

        raise ValueError(f"Unsupported runner step type: {stype!r}")
