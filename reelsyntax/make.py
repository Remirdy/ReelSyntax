import copy
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
from pathlib import Path
import re
from typing import Any
import uuid

from ReelSyntax_Skills.tools.registry import atomic_json, canonical, contained_path, digest, read_json

from . import revisions
from .config import ResolvedConfig, load_config
from .formats.registry import discover_formats, get_format
from .formats.runner import FormatRunner, load_runner_state, state_file_path
from .formats.schema import FORMAT_V1_SCHEMA_URL, validate_format_manifest
from .lang.catalog import resolve_ui_locale
from .project import RECIPES, load, validate
from .prompt.compiler import (
    assert_safe_compiled_plan,
    compile_storyboard_to_project,
    ensure_accessible_palette,
    fit_scene_text_fields,
    sanitize_project_id,
)
from .prompt.intent import ParsedIntent, parse_intent, sanitize_user_prompt, wrap_untrusted_prompt_data
from .prompt.providers import LLMProvider, create_provider
from .prompt.repair import generate_with_repair
from .prompt.storyboard import ALLOWED_BEAT_RECIPES, build_storyboard
from .render import check_locks, output_settings
from .skills import file_digest

PALETTE_PRESETS: dict[str, tuple[str, str, str]] = {
    "warm": ("#1f1614", "#f7ede6", "#d97745"),
    "cool": ("#111924", "#eaf2f9", "#4f95c4"),
    "mono": ("#141517", "#f2f3f5", "#9ea4ad"),
    "editorial": ("#f4efe6", "#1d1b18", "#9c4a32"),
    "neon": ("#0d1018", "#f3f6fc", "#38c8a8"),
}

BUILTIN_PROMPT_DIRECT_MANIFEST: dict[str, Any] = {
    "$schema": FORMAT_V1_SCHEMA_URL,
    "id": "prompt-direct",
    "version": "0.1.0",
    "title": {
        "en": "Direct Prompt Reel",
        "tr": "Doğrudan İstem Videosu",
        "de": "Direktes Prompt-Video",
    },
    "category": "social",
    "aspect": ["9:16", "1:1", "16:9", "4:5"],
    "duration_sec": {"min": 4, "max": 180},
    "languages": ["en", "tr", "de", "es", "fr", "pt"],
    "engines": ["pillow"],
    "needs": ["topic_or_text"],
    "optional": ["tone", "formality", "palette"],
    "skills": ["frame-clock", "contrast-audit", "j-cut"],
    "steps": [
        {"id": "idea", "type": "llm", "gate": "approve"},
        {"id": "script", "type": "llm", "gate": "approve"},
        {"id": "look", "type": "llm", "gate": "approve"},
        {"id": "frames", "type": "render", "profile": "snapshot", "gate": "approve"},
        {"id": "pilot", "type": "render", "scope": "first_5s", "profile": "draft", "gate": "approve"},
        {"id": "full", "type": "render", "profile": "draft", "gate": "approve"},
        {"id": "hero", "type": "render", "profile": "hero"},
        {"id": "qc", "type": "qc"},
    ],
    "qc_rules": ["contrast", "safe-area", "required-glyphs", "loudness"],
}

SCENE_INDEX_MENTION_RE = re.compile(r"\b(?:scene|sahne|szene|beat)\s*([1-9]\d?)\b", re.IGNORECASE)
HEX_COLOR_FIND_RE = re.compile(r"#[0-9a-fA-F]{6}\b")
HEADING_COLON_RE = re.compile(r"(?:heading|title|başlık|baslik|titel)\s*[:=]\s*(.+)$", re.IGNORECASE)
SUBHEADING_COLON_RE = re.compile(r"(?:subheading|subtitle|alt\s*başlık|altbaslik|untertitel)\s*[:=]\s*(.+)$", re.IGNORECASE)

SCENE_PATCH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["heading", "subheading"],
    "properties": {
        "heading": {"type": "string", "maxLength": 96},
        "subheading": {"type": "string", "maxLength": 120},
        "recipe": {"enum": sorted(ALLOWED_BEAT_RECIPES)},
        "background": {"type": "string", "maxLength": 7},
        "foreground": {"type": "string", "maxLength": 7},
        "accent": {"type": "string", "maxLength": 7},
    },
}

ENGINE_SECONDS_PER_FRAME: dict[str, tuple[float, float]] = {
    "pillow": (0.012, 0.035),
    "chromium": (0.060, 0.140),
    "browser": (0.060, 0.140),
    "webgl": (0.075, 0.180),
    "blender": (0.250, 0.850),
    "ffmpeg": (0.008, 0.020),
}


def select_format_manifest(
    intent: ParsedIntent,
    requested_format: str | None = None,
    *,
    extra_roots: tuple[Path, ...] = (),
) -> dict[str, Any]:
    if requested_format:
        if requested_format == "prompt-direct":
            try:
                return get_format("prompt-direct", extra_roots=extra_roots)
            except ValueError:
                return copy.deepcopy(validate_format_manifest(BUILTIN_PROMPT_DIRECT_MANIFEST))
        return get_format(requested_format, extra_roots=extra_roots)

    available = discover_formats(extra_roots=extra_roots)
    if not available:
        return copy.deepcopy(validate_format_manifest(BUILTIN_PROMPT_DIRECT_MANIFEST))

    by_id = {fmt["id"]: fmt for fmt in available}
    if intent.format_hint and intent.format_hint in by_id:
        return by_id[intent.format_hint]

    lang_primary = intent.video_lang.split("-", 1)[0].lower()
    prompt_lower = intent.sanitized_prompt.lower()
    wants_3d = any(tok in prompt_lower for tok in ("3d", "blender", "clay", "lowpoly", "low-poly", "cutscene"))

    best_score = -10_000
    best_fmt = available[0]
    for fmt in available:
        score = 0
        if intent.aspect in fmt["aspect"]:
            score += 4
        if lang_primary in fmt["languages"]:
            score += 3
        low_d = int(fmt["duration_sec"]["min"])
        high_d = int(fmt["duration_sec"]["max"])
        if low_d <= intent.duration_sec <= high_d:
            score += 2
        if "blender" in fmt["engines"] and not wants_3d:
            score -= 5
        elif "blender" in fmt["engines"] and wants_3d:
            score += 6
        fid_tokens = fmt["id"].split("-")
        score += sum(2 for tok in fid_tokens if len(tok) > 2 and tok in prompt_lower)
        if fmt["id"] in {"social-hook-reel", "kinetic-typography"}:
            score += 1
        if score > best_score:
            best_score = score
            best_fmt = fmt
    return best_fmt


def estimate_render_budget(plan: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    total_frames = sum(int(s["duration_frames"]) for s in plan["scenes"])
    fps_val = float(Fraction(plan["output"]["fps"]))
    prod_w = int(plan["output"]["width"])
    prod_h = int(plan["output"]["height"])
    draft_out = output_settings(plan, "draft")
    draft_w = int(draft_out["width"])
    draft_h = int(draft_out["height"])

    engines = sorted({str(s["engine"]) for s in plan["scenes"]} | {"ffmpeg"})
    draft_sec = 0.6
    hero_sec = 0.9
    for scene in plan["scenes"]:
        d_rate, h_rate = ENGINE_SECONDS_PER_FRAME.get(str(scene["engine"]), (0.03, 0.08))
        frames = int(scene["duration_frames"])
        draft_sec += frames * d_rate
        hero_sec += frames * h_rate

    bytes_per_frame_pair = (draft_w * draft_h + prod_w * prod_h) * 0.45
    cache_mib = round((total_frames * bytes_per_frame_pair) / (1024 * 1024), 2)
    gates = [s["id"] for s in manifest["steps"] if s.get("gate") == "approve"]

    return {
        "scenes": len(plan["scenes"]),
        "frames": total_frames,
        "fps": plan["output"]["fps"],
        "duration_sec": round(total_frames / fps_val, 2),
        "draft_resolution": [draft_w, draft_h],
        "production_resolution": [prod_w, prod_h],
        "engines_required": engines,
        "estimated_cache_mib": max(0.5, cache_mib),
        "estimated_draft_sec": round(draft_sec, 2),
        "estimated_hero_sec": round(hero_sec, 2),
        "approval_gates": gates,
    }


def _resolve_provider(
    cfg: ResolvedConfig,
    *,
    provider_name: str | None = None,
    model: str | None = None,
    allow_network: bool = False,
) -> LLMProvider:
    effective_net = bool(allow_network or cfg.general.allow_network)
    return create_provider(
        provider_name,
        model=model,
        allow_network=effective_net,
        config=cfg,
    )


def _choose_output_dir(slug: str, explicit_out: Path | str | None) -> Path:
    if explicit_out is not None:
        return Path(explicit_out).absolute()
    base_parent = Path.cwd() / "out"
    candidate = base_parent / slug
    if not candidate.exists() or not any(candidate.iterdir()):
        return candidate
    suffix = 2
    while True:
        numbered = base_parent / f"{slug}-{suffix}"
        if not numbered.exists() or not any(numbered.iterdir()):
            return numbered
        suffix += 1


def write_prompt_provenance(
    project_dir: Path,
    *,
    raw_prompt: str,
    intent: ParsedIntent,
    manifest: dict[str, Any],
    provider_name: str,
    seed: int,
    ui_lang: str,
    attribution: bool,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    payload: dict[str, Any] = {
        "schema_version": 1,
        "prompt": intent.sanitized_prompt,
        "prompt_sha256": hashlib.sha256(raw_prompt.encode("utf-8")).hexdigest(),
        "format_id": manifest["id"],
        "format_version": manifest["version"],
        "routed_skills": list(intent.routed_skills),
        "provider": provider_name,
        "seed": int(seed) & 0xFFFFFFFF,
        "languages": {
            "prompt_lang": intent.prompt_lang,
            "video_lang": intent.video_lang,
            "ui_lang": ui_lang,
        },
        "aspect": intent.aspect,
        "duration_sec": intent.duration_sec,
        "attribution": bool(attribution),
        "created_at": now,
        "updated_at": now,
        "revisions": [],
    }
    atomic_json(contained_path(project_dir, "prompt.json", must_exist=False), payload)
    return payload


def _append_prompt_revision(project_dir: Path, entry: dict[str, Any]) -> None:
    path = contained_path(project_dir, "prompt.json", must_exist=False)
    if not path.is_file():
        return
    doc = read_json(path)
    if not isinstance(doc, dict):
        return
    doc.setdefault("revisions", []).append(entry)
    doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    atomic_json(path, doc)


def _format_runner_response(project_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    pending = state.get("pending_gate")
    out: dict[str, Any] = {
        "project": str(project_root),
        "format_id": state["format_id"],
        "format_version": state["format_version"],
        "provider": state["provider"],
        "seed": state["seed"],
        "status": state["status"],
        "current_step_index": state["current_step_index"],
        "pending_gate": pending,
        "completed_steps": state["completed_steps"],
        "approvals": list(state.get("approvals", {}).keys()),
        "routed_skills": state["intent"]["routed_skills"],
        "languages": {
            "prompt_lang": state["intent"]["prompt_lang"],
            "video_lang": state["intent"]["video_lang"],
        },
    }
    if pending:
        out["next_actions"] = {
            "approve": f"reelsyntax step {project_root} {pending} --approve",
            "edit": f"reelsyntax step {project_root} {pending} --edit \"...\"",
            "back": f"reelsyntax step {project_root} {pending} --back",
        }
    return out


def make_video(
    prompt: str,
    *,
    format_id: str | None = None,
    out_dir: Path | str | None = None,
    provider_name: str | None = None,
    model: str | None = None,
    video_lang: str | None = None,
    ui_lang: str | None = None,
    aspect: str | None = None,
    duration_sec: int | None = None,
    seed: int = 42,
    yes: bool = False,
    dry_run: bool = False,
    allow_network: bool = False,
    attribution: bool = False,
    extra_format_roots: tuple[Path, ...] = (),
    dry_run_render: bool = False,
) -> dict[str, Any]:
    cfg = load_config()
    resolved_ui = resolve_ui_locale(explicit=ui_lang or (cfg.general.ui_lang if cfg.general.ui_lang != "auto" else None))
    cfg_video_lang = video_lang or (cfg.general.video_lang if cfg.general.video_lang != "auto" else None)
    effective_attribution = bool(attribution or cfg.general.attribution)
    provider = _resolve_provider(cfg, provider_name=provider_name, model=model, allow_network=allow_network)

    initial_intent = parse_intent(
        prompt,
        video_lang=cfg_video_lang,
        format_id=format_id,
        aspect=aspect,
        duration_sec=duration_sec,
    )
    manifest = select_format_manifest(initial_intent, requested_format=format_id, extra_roots=extra_format_roots)

    low_d = int(manifest["duration_sec"]["min"])
    high_d = int(manifest["duration_sec"]["max"])
    effective_dur = max(low_d, min(high_d, initial_intent.duration_sec))
    effective_aspect = initial_intent.aspect if initial_intent.aspect in manifest["aspect"] else manifest["aspect"][0]

    bounded_intent = parse_intent(
        prompt,
        video_lang=cfg_video_lang,
        format_id=manifest["id"],
        aspect=effective_aspect,
        duration_sec=effective_dur,
    )
    slug = sanitize_project_id(f"{manifest['id']}-{bounded_intent.sanitized_prompt[:28]}")

    if dry_run:
        storyboard = build_storyboard(bounded_intent, provider, seed=seed)
        compiled = compile_storyboard_to_project(storyboard, bounded_intent, project_id=slug, seed=seed)
        budget = estimate_render_budget(compiled, manifest)
        return {
            "dry_run": True,
            "format_id": manifest["id"],
            "format_version": manifest["version"],
            "provider": provider.name,
            "seed": int(seed) & 0xFFFFFFFF,
            "attribution": effective_attribution,
            "languages": {
                "prompt_lang": bounded_intent.prompt_lang,
                "video_lang": bounded_intent.video_lang,
                "ui_lang": resolved_ui,
            },
            "routed_skills": list(bounded_intent.routed_skills),
            "budget": budget,
            "plan_summary": {
                "id": compiled["id"],
                "scene_count": len(compiled["scenes"]),
                "frames": budget["frames"],
                "scenes": [
                    {
                        "id": s["id"],
                        "recipe": s["recipe"],
                        "duration_frames": s["duration_frames"],
                    }
                    for s in compiled["scenes"]
                ],
            },
        }

    target_dir = _choose_output_dir(slug, out_dir)
    runner = FormatRunner(manifest, provider, max_attempts=cfg.provider.max_repairs, dry_run_render=dry_run_render)
    runner.initialize_project(
        target_dir,
        prompt,
        seed=seed,
        video_lang=bounded_intent.video_lang,
        aspect=bounded_intent.aspect,
        duration_sec=bounded_intent.duration_sec,
    )
    write_prompt_provenance(
        target_dir,
        raw_prompt=prompt,
        intent=bounded_intent,
        manifest=manifest,
        provider_name=provider.name,
        seed=seed,
        ui_lang=resolved_ui,
        attribution=effective_attribution,
    )
    from .assets.license import write_licenses_markdown

    write_licenses_markdown(target_dir)
    state = runner.run(target_dir, auto_approve=yes)
    result = _format_runner_response(target_dir, state)
    result["attribution"] = effective_attribution
    return result


def step_project(
    project_dir: Path | str,
    step_id: str,
    *,
    approve: bool = False,
    edit: str | None = None,
    back: bool = False,
    yes: bool = False,
    provider_name: str | None = None,
    model: str | None = None,
    allow_network: bool = False,
    extra_format_roots: tuple[Path, ...] = (),
    dry_run_render: bool = False,
) -> dict[str, Any]:
    actions_chosen = sum([bool(approve), edit is not None, bool(back)])
    if actions_chosen > 1:
        raise ValueError("Choose at most one of --approve, --edit, or --back")

    root = Path(project_dir).resolve(strict=True)
    cfg = load_config()
    saved_state = load_runner_state(root)
    chosen_provider_name = provider_name or saved_state.get("provider")
    provider = _resolve_provider(cfg, provider_name=chosen_provider_name, model=model, allow_network=allow_network)
    runner = FormatRunner.from_project(
        root,
        provider,
        extra_roots=extra_format_roots,
        dry_run_render=dry_run_render,
    )
    valid_ids = [s["id"] for s in runner.manifest["steps"]]
    if step_id not in valid_ids:
        raise ValueError(f"Unknown step {step_id!r} for format {runner.manifest['id']!r}; valid steps: {valid_ids}")

    if approve:
        runner.approve_pending_gate(root, expected_step_id=step_id)
        state = runner.run(root, auto_approve=yes)
        return _format_runner_response(root, state)

    if edit is not None:
        cleaned_edit = sanitize_user_prompt(edit)
        runner.edit_step(root, step_id, cleaned_edit)
        _append_prompt_revision(
            root,
            {
                "kind": "step_edit",
                "step_id": step_id,
                "instruction": cleaned_edit,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        state = runner.run(root, auto_approve=yes, stop_after_step=None if yes else step_id)
        return _format_runner_response(root, state)

    if back:
        backed = runner.step_back(root, step_id)
        target_sid = valid_ids[int(backed["current_step_index"])]
        state = runner.run(root, auto_approve=yes, stop_after_step=None if yes else target_sid)
        return _format_runner_response(root, state)

    state = runner.run(root, auto_approve=yes, stop_after_step=step_id)
    return _format_runner_response(root, state)


def has_active_format_state(project_dir: Path | str) -> bool:
    root = Path(project_dir)
    if not root.is_dir():
        return False
    sf = state_file_path(root)
    if not sf.is_file():
        return False
    state = read_json(sf)
    return isinstance(state, dict) and state.get("status") != "completed"


def resume_format_project(
    project_dir: Path | str,
    *,
    yes: bool = False,
    provider_name: str | None = None,
    model: str | None = None,
    allow_network: bool = False,
    extra_format_roots: tuple[Path, ...] = (),
    dry_run_render: bool = False,
) -> dict[str, Any]:
    root = Path(project_dir).resolve(strict=True)
    stale_lock = contained_path(root, ".reelsyntax/render.lock", must_exist=False)
    if stale_lock.exists():
        stale_lock.unlink(missing_ok=True)
    cfg = load_config()
    saved_state = load_runner_state(root)
    chosen_provider_name = provider_name or saved_state.get("provider")
    provider = _resolve_provider(cfg, provider_name=chosen_provider_name, model=model, allow_network=allow_network)
    runner = FormatRunner.from_project(
        root,
        provider,
        extra_roots=extra_format_roots,
        dry_run_render=dry_run_render,
    )
    state = runner.run(root, auto_approve=yes)
    return _format_runner_response(root, state)


def _collect_roi_locked_scene_ids(root: Path) -> set[str]:
    rs_dir = root / ".reelsyntax"
    if not rs_dir.is_dir():
        return set()
    ids: set[str] = set()
    for path in sorted(rs_dir.glob("roi-locks-*.json")):
        if path.is_file():
            ledger = read_json(path)
            if isinstance(ledger, dict):
                ids.update(str(k) for k in ledger.keys())
    return ids


def _select_revision_targets(
    scenes: list[dict[str, Any]],
    instruction: str,
    explicit_scene_id: str | None,
    locked_ids: set[str],
    roi_locked_ids: set[str],
) -> list[int]:
    id_to_idx = {str(s["id"]): idx for idx, s in enumerate(scenes)}
    if explicit_scene_id is not None:
        if explicit_scene_id not in id_to_idx:
            raise ValueError(f"Unknown scene: {explicit_scene_id}")
        if explicit_scene_id in locked_ids:
            raise ValueError(f"Scene {explicit_scene_id!r} is locked; unlock before revising")
        return [id_to_idx[explicit_scene_id]]

    lowered = instruction.lower()
    mentioned_indices: list[int] = []
    for sid, idx in id_to_idx.items():
        if re.search(rf"\b{re.escape(sid.lower())}\b", lowered):
            if sid in locked_ids:
                raise ValueError(f"Scene {sid!r} is locked; unlock before revising")
            mentioned_indices.append(idx)

    num_match = SCENE_INDEX_MENTION_RE.search(instruction)
    if num_match:
        one_based = int(num_match.group(1))
        if not 1 <= one_based <= len(scenes):
            raise ValueError(f"Scene index {one_based} is out of range (1..{len(scenes)})")
        idx = one_based - 1
        sid = str(scenes[idx]["id"])
        if sid in locked_ids:
            raise ValueError(f"Scene {sid!r} is locked; unlock before revising")
        if idx not in mentioned_indices:
            mentioned_indices.append(idx)

    if mentioned_indices:
        return sorted(mentioned_indices)

    unlocked = [
        idx
        for idx, s in enumerate(scenes)
        if str(s["id"]) not in locked_ids and str(s["id"]) not in roi_locked_ids
    ]
    if not unlocked:
        unlocked = [idx for idx, s in enumerate(scenes) if str(s["id"]) not in locked_ids]
    if not unlocked:
        raise ValueError("All scenes in project are locked; cannot apply revision")
    return unlocked


def _apply_instruction_to_scene(
    scene: dict[str, Any],
    instruction: str,
    provider: LLMProvider,
    *,
    video_lang: str,
    seed: int,
    preserve_roi: bool,
) -> dict[str, Any]:
    updated = copy.deepcopy(scene)
    params = dict(updated.get("params", {}))
    clean_inst = sanitize_user_prompt(instruction)[:600]
    lowered = clean_inst.lower()

    heading_match = HEADING_COLON_RE.search(clean_inst)
    subheading_match = SUBHEADING_COLON_RE.search(clean_inst)
    hex_colors = HEX_COLOR_FIND_RE.findall(clean_inst)

    matched_palette: tuple[str, str, str] | None = None
    for pal_name, triple in PALETTE_PRESETS.items():
        if re.search(rf"\b{re.escape(pal_name)}\b", lowered):
            matched_palette = triple
            break

    requested_recipe: str | None = None
    for candidate_recipe in sorted(ALLOWED_BEAT_RECIPES):
        if candidate_recipe in lowered and candidate_recipe in RECIPES:
            requested_recipe = candidate_recipe
            break

    explicit_handled = False
    if heading_match:
        params["heading"] = heading_match.group(1).strip()[:120]
        explicit_handled = True
    if subheading_match:
        params["subheading"] = subheading_match.group(1).strip()[:120]
        if "dialogue" in params:
            params["dialogue"] = params["subheading"]
        explicit_handled = True

    if not preserve_roi:
        if matched_palette is not None:
            bg, fg, acc = ensure_accessible_palette(*matched_palette)
            params["background"] = bg
            params["foreground"] = fg
            params["accent"] = acc
            explicit_handled = True
        elif hex_colors:
            cur_bg = str(params.get("background", "#14191f"))
            cur_fg = str(params.get("foreground", "#edf1f5"))
            cur_ac = str(params.get("accent", "#4c8b93"))
            if len(hex_colors) >= 3:
                cur_bg, cur_fg, cur_ac = hex_colors[0], hex_colors[1], hex_colors[2]
            elif "background" in lowered or "arka plan" in lowered or "hintergrund" in lowered:
                cur_bg = hex_colors[0]
            else:
                cur_ac = hex_colors[0]
            bg, fg, acc = ensure_accessible_palette(cur_bg, cur_fg, cur_ac)
            params["background"] = bg
            params["foreground"] = fg
            params["accent"] = acc
            explicit_handled = True

        if requested_recipe is not None and updated.get("engine") == "pillow":
            updated["recipe"] = requested_recipe
            if requested_recipe == "data-horizon" and "series" not in params:
                params["series"] = [24.0, 42.0, 68.0, 91.0]
            explicit_handled = True

    if not explicit_handled:
        if provider.name == "offline_rules":
            cleaned_label = SCENE_INDEX_MENTION_RE.sub("", clean_inst).strip(" :,-")
            if cleaned_label:
                params["subheading"] = cleaned_label[:120]
        else:
            patch_out, _ = generate_with_repair(
                provider,
                system="Revise the scene heading and subheading according to the user's instruction.",
                user=wrap_untrusted_prompt_data(
                    f"Current heading: {params.get('heading', '')}\nCurrent subheading: {params.get('subheading', '')}\nRevision: {clean_inst}",
                    video_lang=video_lang,
                    aspect="9:16",
                    duration_sec=5,
                ),
                schema=SCENE_PATCH_SCHEMA,
                seed=seed,
            )
            if patch_out.get("heading"):
                params["heading"] = str(patch_out["heading"])[:120]
            if patch_out.get("subheading"):
                params["subheading"] = str(patch_out["subheading"])[:120]
            if not preserve_roi and all(k in patch_out for k in ("background", "foreground", "accent")):
                bg, fg, acc = ensure_accessible_palette(
                    str(patch_out["background"]),
                    str(patch_out["foreground"]),
                    str(patch_out["accent"]),
                )
                params["background"] = bg
                params["foreground"] = fg
                params["accent"] = acc

    updated["params"] = params
    return updated


def revise_project(
    project_dir: Path | str,
    instruction: str,
    *,
    scene_id: str | None = None,
    provider_name: str | None = None,
    model: str | None = None,
    allow_network: bool = False,
    render_after: bool = False,
    profile: str | None = None,
) -> dict[str, Any]:
    clean_instruction = sanitize_user_prompt(instruction)
    root, plan, metadata = load(project_dir)
    cfg = load_config()
    provider = _resolve_provider(cfg, provider_name=provider_name, model=model, allow_network=allow_network)

    lock_file = contained_path(root, ".reelsyntax/scene-locks.json", must_exist=False)
    locked_ledger = read_json(lock_file) if lock_file.is_file() else {}
    locked_ids = set(locked_ledger.keys()) if isinstance(locked_ledger, dict) else set()
    roi_locked_ids = _collect_roi_locked_scene_ids(root)

    target_indices = _select_revision_targets(
        plan["scenes"],
        clean_instruction,
        scene_id,
        locked_ids,
        roi_locked_ids,
    )

    short_uid = uuid.uuid4().hex[:8]
    ckpt_name = f"pre-revise-{short_uid}"
    revisions.checkpoint(root, ckpt_name)

    video_lang = "en"
    prov_path = contained_path(root, "prompt.json", must_exist=False)
    if prov_path.is_file():
        prov_doc = read_json(prov_path)
        if isinstance(prov_doc, dict):
            video_lang = str(prov_doc.get("languages", {}).get("video_lang", "en"))

    updated_plan = copy.deepcopy(plan)
    changed_ids: list[str] = []
    preserved_ids: list[str] = []

    for idx, before_scene in enumerate(plan["scenes"]):
        sid = str(before_scene["id"])
        if idx not in target_indices:
            preserved_ids.append(sid)
            continue
        preserve_roi = bool(before_scene.get("locked_regions")) or (sid in roi_locked_ids)
        step_seed = (int(plan.get("seed", 42)) + idx + 1) & 0xFFFFFFFF
        after_scene = _apply_instruction_to_scene(
            before_scene,
            clean_instruction,
            provider,
            video_lang=video_lang,
            seed=step_seed,
            preserve_roi=preserve_roi,
        )
        after_scene["duration_frames"] = before_scene["duration_frames"]
        if after_scene.get("engine") == "pillow":
            a_params = dict(after_scene.get("params", {}))
            if "heading" in a_params or "subheading" in a_params:
                fh, fsub = fit_scene_text_fields(
                    str(a_params.get("heading", "")),
                    str(a_params.get("subheading", "")),
                    recipe=str(after_scene["recipe"]),
                    width=int(plan["output"]["width"]),
                    height=int(plan["output"]["height"]),
                )
                if fh:
                    a_params["heading"] = fh
                if fsub:
                    a_params["subheading"] = fsub
                after_scene["params"] = a_params
        if before_scene.get("locked_regions"):
            after_scene["locked_regions"] = copy.deepcopy(before_scene["locked_regions"])
        updated_plan["scenes"][idx] = after_scene
        if canonical(before_scene) != canonical(after_scene):
            changed_ids.append(sid)
        else:
            preserved_ids.append(sid)

    for idx in target_indices:
        candidate = updated_plan["scenes"][idx]
        assert_safe_compiled_plan({"scenes": [candidate]})
    validate(updated_plan)
    check_locks(root, updated_plan)

    rev_id = uuid.uuid4().hex
    reel_path = contained_path(root, "reel.json")
    backup_reel = contained_path(root, f".reelsyntax/revisions/{rev_id}.reel.json", must_exist=False)
    history_json = contained_path(root, f".reelsyntax/revisions/{rev_id}.json", must_exist=False)
    backup_reel.parent.mkdir(parents=True, exist_ok=True)
    backup_reel.write_bytes(reel_path.read_bytes())

    after_sha = digest(canonical(updated_plan))
    atomic_json(
        history_json,
        {
            "schema_version": 1,
            "operation": "revise",
            "checkpoint": ckpt_name,
            "instruction": clean_instruction,
            "changed_scenes": changed_ids,
            "preserved_scenes": preserved_ids,
            "before_source": backup_reel.relative_to(root).as_posix(),
            "before_source_sha256": file_digest(backup_reel),
            "before_plan_sha256": metadata["plan_sha256"],
            "after_sha256": after_sha,
        },
    )
    atomic_json(reel_path, updated_plan)
    _append_prompt_revision(
        root,
        {
            "kind": "revise",
            "revision_id": rev_id,
            "checkpoint": ckpt_name,
            "instruction": clean_instruction,
            "changed_scenes": changed_ids,
            "preserved_scenes": preserved_ids,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    response: dict[str, Any] = {
        "project": str(root),
        "revision": rev_id,
        "checkpoint": ckpt_name,
        "changed_scenes": changed_ids,
        "preserved_scenes": preserved_ids,
        "plan_sha256": after_sha,
    }
    if render_after:
        from .render import render

        eff_prof = profile or cfg.render.default_profile
        rendered = render(root, profile=eff_prof)
        response["render"] = {
            "profile": eff_prof,
            "artifact": rendered["artifact"],
            "cache_hits": [s["id"] for s in rendered["scenes"] if s.get("cache_hit")],
            "rendered_scenes": [s["id"] for s in rendered["scenes"] if not s.get("cache_hit")],
        }
    return response
