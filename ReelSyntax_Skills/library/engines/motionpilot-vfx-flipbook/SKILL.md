---
name: motionpilot-vfx-flipbook
description: "Use for first-party Remirdy AfterEffectsMCP VFX and flipbook generation. Author hybrid AE/raster VFX plates, normal maps, and Unity/Unreal sprite-sheet packages with overdraw and loop-seam audits."
metadata:
  category: engines
  stage: build
  status: validated
  version: "2.0.0"
  aliases: "motionpilot vfx,ae flipbook paket,after effects oyun efekti,vfx sprite sheet"
  requires: "after-effects-mcp"
---

# Motionpilot Vfx Flipbook

## Activation
Use when generating cinema/game/social VFX compositions, transparent RGBA particle plates, distortion normal maps, or Unity/Unreal flipbook packages via `Remirdy/AfterEffectsMCP`. Search aliases: motionpilot vfx,ae flipbook paket,after effects oyun efekti,vfx sprite sheet.

## Inputs and output
- Inputs: Effect brief, target domain (`cinema`, `game`, `social`), resolution/grid dimensions, alpha mode, and active project constraints (`offline`, `no_paid_services`).
- Output: Editable `.aep` VFX comp or standalone Node-rendered RGBA PNG sequence, normal map sequence, packed atlas, and engine manifest.
- Required capability: after-effects-mcp
- Evidence bundle: Preset/plate manifest, `detect_alpha_bleeding_edges` / `validate_loop_seam` / `audit_vfx_overdraw` results, and contact sheet.

## Production recipe
1. Query `after_effects:list_vfx_presets` via the MCP Gateway to inspect available hybrid presets (`cinema.atmospheric_fog`, `cinema.light_rays`, `game.energy_burst`, `game.shockwave`, etc.) that automatically fall back to stock After Effects effects when Trapcode/Saber/Optical Flares are absent.
2. Enforce ReelSyntax constraint gates: when `offline` or `no_paid_services` is true, never invoke `generate_ai_plate`, `generate_ai_video_shot`, or `runway_generate_video`; use deterministic `create_raster_vfx_plate`, `apply_vfx`, or `build_complex_vfx`.
3. For transparent compositing plates or game flipbooks, generate straight-alpha RGBA frames (`create_raster_vfx_plate` + optional `generate_vfx_normal_map_sequence`), pack via `pack_flipbook_atlas`, and run `detect_alpha_bleeding_edges`, `validate_loop_seam`, and `audit_vfx_overdraw`.
4. Pre-verify any `.abc` Alembic input exists on disk with non-zero SHA-256 before calling `houdini_alembic_bridge` so missing paths never fall back to mock placeholder files.

## Acceptance criteria
- Straight/premultiplied alpha contract declared explicitly; zero dark halo edge bleed; seamless loop seam where `loop: true` is requested.
- Record gateway tool calls, artifact SHA-256 digests, overdraw/memory metrics, and visual review verdict.

## Failure and repair
If edge fringing appears when compositing over bright backgrounds, run `auto_crop_alpha_frames` and `normalize_flipbook_brightness_alpha` or switch matte interpretation to straight unmatted RGBA.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric.
- [Remirdy AfterEffectsMCP](https://github.com/Remirdy/AfterEffectsMCP)

First-party Remirdy ecosystem integration skill.
