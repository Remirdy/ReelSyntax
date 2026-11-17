---
name: blender-ae-interchange
description: "Use for coordinated BlenderMCP, ReelSyntax, and AfterEffectsMCP multi-tool workflows. Transfer 3D camera rigs, rational FPS timelines, RGBA/depth passes, GLB assets, masks, and audio stems."
metadata:
  category: workflow
  stage: export
  status: validated
  version: "2.0.0"
  aliases: "blender after effects köprüsü,3d kamera aktarımı,blender ae compositing,interchange handoff"
  requires: ""
---

# Blender Ae Interchange

## Activation
Use when orchestrating shots that span 3D scene generation (`Remirdy/BlenderMCP` or headless Blender), deterministic editorial/audio assembly (`ReelSyntax`), and 2.5D typography/VFX finishing (`Remirdy/AfterEffectsMCP`). Search aliases: blender after effects köprüsü,3d kamera aktarımı,blender ae compositing,interchange handoff.

## Inputs and output
- Inputs: Validated `reel.json` plan, 3D camera rig parameters, rendered RGBA/pass sequences, `.glb`/`.fbx` models, masks, and 48 kHz WAV stems.
- Output: Hash-verified `interchange-manifest.json`, matched Blender & After Effects camera rig payloads, `.otio`/`.fcpxml` timelines, and dry-run validated AE actions.
- Required capability: `reelsyntax.interchange` and `reelsyntax.gateway` (`mcp-bridge handoff`).
- Evidence bundle: Camera FOV/zoom parity check, rational frame-count parity across all three tools, SHA-256 pass manifest, and `jsx_dry_run` status.

## Production recipe
1. Lock canonical timing first: express rate as exact rational `num/den` (e.g. `24/1` or `30000/1001`). In Blender 4.x/5.x set **both** `scene.render.fps = num` and `scene.render.fps_base = den` (compensating for integer-only `set_frame_range` when fractional NTSC rates are used).
2. Translate 3D camera optics exactly between Blender/ReelSyntax (right-handed Z-up, 35mm full-frame horizontal sensor $S_w = 36.0\text{ mm}$, focal length $f_{\text{mm}}$) and After Effects (left-handed Y-down pixel space):
   - AE Camera Zoom (pixels): $Z_{\text{ae}} = W \cdot f_{\text{mm}} / S_w$.
   - Coordinate map (scene scale $k$ px/m): $(X_{\text{ae}}, Y_{\text{ae}}, Z_{\text{ae\_pos}}) = (\frac{W}{2} + k X_{\text{bl}},\; \frac{H}{2} - k Z_{\text{bl}},\; k Y_{\text{bl}})$.
3. Render 3D foreground plates as **straight (unmatted) RGBA** PNG or 16-bit half-float EXR sequences with `film_transparent = True`, keeping background/shadow-catcher/emission in separate passes to prevent double-premultiplied dark fringes in After Effects.
4. Pre-verify every transferred file exists and record its SHA-256 digest in `interchange-manifest.json` before invoking `AfterEffectsMCP` import actions.
5. Validate generated After Effects camera/layer actions with `after_effects:jsx_dry_run` before opening AE, and verify final composite delivery with `reelsyntax qc`.

## Acceptance criteria
- Exact frame count and rational duration match across Blender, ReelSyntax, and After Effects within $0$ frames; AE camera horizontal FOV matches $\theta_h = 2\arctan(S_w / (2 f_{\text{mm}}))$ within $10^{-4}\text{ rad}$.
- Every referenced pass/asset verified on disk by SHA-256; graceful fallback path documented when either desktop app is offline.

## Failure and repair
Sliding 2D callouts over 3D renders indicate mismatched sensor gate (`36mm` vs Blender's legacy `32mm` default in older files), integer vs `1001` drop-frame rate mismatch, or ease handle divergence: bake per-frame camera transforms at exact frame indices and enforce $S_w = 36.0\text{ mm}$ on both ends.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric.
- [OpenTimelineIO Specification](https://opentimelineio.readthedocs.io/en/latest/)
- [Remirdy BlenderMCP](https://github.com/Remirdy/BlenderMCP)
- [Remirdy AfterEffectsMCP](https://github.com/Remirdy/AfterEffectsMCP)

First-party Remirdy ecosystem workflow skill.
