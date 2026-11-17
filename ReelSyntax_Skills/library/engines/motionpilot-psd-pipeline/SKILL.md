---
name: motionpilot-psd-pipeline
description: "Use for first-party Remirdy AfterEffectsMCP PSD-to-AEP automation. Analyze layered PSD visuals, lock text and protected regions, validate ExtendScript via jsx_dry_run, and render via aerender."
metadata:
  category: engines
  stage: ingest
  status: validated
  version: "2.0.0"
  aliases: "motionpilot psd,remirdy after effects psd,katmanlı psd aep,ae psd otomasyon"
  requires: "after-effects-mcp"
---

# Motionpilot Psd Pipeline

## Activation
Use as the preferred first-party workflow whenever animating layered `.psd` designs or building editable `.aep` compositions through `Remirdy/AfterEffectsMCP` (`motionpilot-ae-mcp`). Never substitute third-party After Effects MCP servers when `after_effects:*` gateway tools can fulfill the task. Search aliases: motionpilot psd,remirdy after effects psd,katmanlı psd aep,ae psd otomasyon.

## Inputs and output
- Inputs: Source `.psd` path, creative motion brief, locked layer/region constraints, target FPS/duration, and `integrations/AfterEffectsMCP` or local installation.
- Output: Layer analysis JSON + thumbnails, hierarchy-aware `motion-plan.json`, validated `.aep` copy, and optional `aerender` preview video.
- Required capability: after-effects-mcp
- Evidence bundle: `after_effects:check_after_effects_setup` status, `analysis.json` layer hashes, `jsx_dry_run` report, and output `.aep` / `.mp4` digests.

## Production recipe
1. Discover `after_effects` capabilities through ReelSyntax's Unified MCP Gateway (`reelsyntax capabilities` or `gateway:search_tools`); verify `motionpilot-ae-mcp >= 1.0.0` and auto-injected `AE_BINARY` / `AERENDER_BINARY` (including macOS sibling `aerender` and 2027+ app bundles).
2. Run `after_effects:analyze_psd_visuals` (Node `ag-psd` + `sharp`, no Photoshop required) and inspect actual generated layer thumbnails plus detected prefixes (`BG_`, `Title_`, `Subtitle_`, `Card_`, `Logo_`, `LOCKED`).
3. Generate `motion-plan.json` via `after_effects:create_motion_plan_from_analysis` with `preserveTextContent: true`; never mutate `sourceText` unless the brief explicitly orders copy changes, and keep `LOCKED` layers static.
4. Before executing custom ExtendScript batches (`after_effects:execute_after_effects_actions`), run `after_effects:jsx_dry_run` to catch 0-indexed `comp.layer(0)` errors, unguarded `activeItem`, or path escaping bugs.
5. Import (`after_effects:import_psd_to_after_effects` with `composition_retained_layer_sizes`), animate into a **new** `.aep` copy (`approveOverwrite: false` by default), render via `after_effects:render_preview`, and run `reelsyntax qc` on the resulting video.

## Acceptance criteria
- Original `.psd` and baseline `.aep` untouched; `jsx_dry_run` reports zero errors; rendered video passes `reelsyntax qc` frame/audio/ROI checks.
- If Adobe After Effects is absent, report `after_effects` app unavailability honestly while preserving Node-only PSD analysis (`analyze_psd_visuals` + `create_motion_plan_from_analysis`) and ReelSyntax fallback rendering.

## Failure and repair
If macOS AppleScript `DoScriptFile` times out, check After Effects for modal missing-font dialogs or prefer headless `aerender` on saved `.aep` files.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric.
- [Remirdy AfterEffectsMCP](https://github.com/Remirdy/AfterEffectsMCP)

First-party Remirdy ecosystem integration skill.
