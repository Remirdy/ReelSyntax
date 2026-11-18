---
name: stepped-clay-lookdev
description: "Build tactile 3D claymation shaders and stepped 12-fps animation F-curves in Blender with world-scale thumbprint normals, warm subsurface scatter, and tabletop lighting."
metadata:
  category: modeling
  stage: build
  status: validated
  version: "2.0.0"
  aliases: "stepped clay lookdev,3d stop motion clay shader,kademeli kil görünüm geliştirme,3B kil gölgelendirici ve adım kare,gestuftes Knet-Lookdev,3D-Stop-Motion-Tonmaterial,lookdev de arcilla escalonada,lookdev argile saccadée"
  requires: "blender"
---

# Stepped Clay Lookdev

## Activation
Activate when building `stepped-clay-look` 3D scenes in headless Blender where procedural geometry, props, or characters should read as handcrafted tabletop plasticine animated on twos/threes rather than slick CG plastic. Search aliases: `stepped clay lookdev`, `kademeli kil görünüm geliştirme`, `gestuftes Knet-Lookdev`. Requires `blender`.

## Decision rules
- **Decouple character/object step cadence from camera cadence**: quantize object/character pose F-curves to twos or threes (`step = 2` or `3` frames at `24/1` or `30/1` fps -> `12` or `10` poses/sec using `CONSTANT` / `STEPPED` F-curve modifier) while keeping slow camera dollies either `1`-step smooth OR matched `2`-step **without** mixing `2`-step objects and `3`-step camera beat-frequency strobing!
- **Two-frequency surface normal recipe (macro dent + micro fingerprint)**:
  - Macro hand-pressed wobble: procedural 3D `Noise` (`scale = 3.5` per `10 cm` object, `strength = 0.08`) displacing/bumping broad planes so no sphere looks mathematically perfect.
  - Micro fingerprint ridges: anisotropic wave/Voronoi ridges (`scale = 42.0`, `strength = 0.035`), *seeded per pose step* (`floor(frame / step) * 17`) at `20%` blend if simulating subtle re-sculpting shimmer (`clay boil`), or object-space locked for calm commercials!
- **Matte waxy Principled BSDF bounds**: `roughness ∈ [0.64, 0.78]` (never glossy `< 0.35`), `subsurface_weight = 0.18–0.30` with warm radius `(1.0, 0.45, 0.25) * 2.5 mm` at `10 cm` tabletop scale so thin ears/edges catch warm backlight without turning into translucent wax candles.
- **`freezedetect` & motion blur rule**: disable long `180°` smooth motion blur on stepped clay (stop-motion frames are crisp stills per exposure; use `shutter <= 0.15` or off), and ensure `step <= 3` (`<= 0.10s` hold) so `freezedetect` (`0.60s`) never trips during active animation.

## Parameters and defaults
- `object_scale_cm`: `8.0–18.0` cm physical tabletop scale (drives realistic `f/4.0–f/5.6` DoF and `2.5 mm` SSS radius).
- `pose_step_frames`: `2` at `24/1` fps (`12` poses/sec) or `3` at `30/1` fps (`10` poses/sec).
- `base_roughness`: `0.70` (`+-0.06` noise variation in roughness channel).
- `subsurface_weight`: `0.22`.
- `clay_boil_amount`: `0.15` (`0.0` for calm product/educational shots).

## Procedure
1. Model scenes at real miniature tabletop dimensions (`1 Blender unit = 1 m`, hero props `0.08–0.18 m` tall) on a physical sweep cyclorama card.
2. Build the procedural clay node group (`Principled BSDF` + macro noise bump + micro fingerprint ridge bump + roughness variation + subtle SSS) in `Blender` Python (`bpy.data.materials`).
3. Attach Blender `FModifierStepped` (`frame_step = pose_step_frames`, `use_frame_start = False`) to all animated object/armature F-curves.
4. Light with a large softbox overhead-front key (`area light size = 0.6 m` at `0.9 m` distance), warm bounce card fill, and crisp rim light to reveal thumbprint bevels.
5. Render a `3`-frame snapshot (`frame 0, 2, 4`) to verify silhouette readability, warm edge scatter, and clean denoised contact shadows before full render.

## Failure modes and fixes
- **Clay looks like shiny melted candle wax**: lower `subsurface_weight` from `0.8` down to `0.22`, scale `subsurface_scale` to `0.0025 m`, and raise `roughness` to `0.70`.
- **Fingerprint bump turns into noisy grey static at distance**: clamp micro-bump `strength <= 0.04` and scale ridge frequency to `~1.2–2.0 mm` physical spacing (`>= 2.5 px` at camera distance).
- **Smooth `0.5` shutter blurs stepped jump frames into ghosted double-images**: set Cycles/EEVEE motion blur `off` (or `shutter = 0.08` micro-soften only).

## Checklist
- [ ] Miniature tabletop scale (`0.08–0.18 m`), `roughness ∈ [0.64, 0.78]`, and `SSS ≈ 0.22` are matched.
- [ ] Macro hand-dent + micro thumbprint bump stay readable (`>= 2 px` ridge spacing, zero shimmer static).
- [ ] `FModifierStepped` (`step = 2` or `3`) is applied cleanly without ghosted motion blur.
- [ ] Softbox key + rim light separate tactile edges against the cyclorama background (`contrast == pass`).

## Worked examples
- **Example 1 (`24/1` fps `12s` clay mascot opener)**: `0.12 m` rounded clay character on `#2B303A` matte sweep, terracotta `#E06D53` clay (`roughness = 0.72`, `SSS = 0.24`), `FModifierStepped(frame_step=2)`, `50mm` camera at `0.95 m` (`f/4.5`), motion blur `off`.
- **Example 2 (`30/1` fps tactile chart bars)**: Three beveled clay blocks extruding upward on `step = 3` (`10` poses/sec) with `0.0` clay boil so metric labels remain calm and distraction-free.

## Resources (load only if needed)
- [Headless Blender `bpy` clay shader and `FModifierStepped` recipe](references/blender-clay-node-and-fcurve-spec.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
