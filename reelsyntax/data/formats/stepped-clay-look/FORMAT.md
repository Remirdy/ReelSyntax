# Stepped Clay Look (`stepped-clay-look`)

Tactile stepped `10–12` poses/sec sculptural clay showcase for `16:9`, `9:16`, `1:1`, and `4:5` canvases.

## Creative intent and rendering paths

- **Native Blender (`bpy`) path:** Models miniature tabletop clay clusters (`0.12–0.18 m` scale) with matte Principled BSDF (`roughness = 0.72`), warm subsurface scattering (`0.22`), procedural macro-dent + fingerprint noise bump, motion blur disabled, `f/5.6` tabletop DoF, and `FModifierStepped` quantization on twos/threes.
- **Offline Pillow procedural fallback:** Quantizes sculptural clay totem poses cleanly to `2` frames at `24 fps` (`12` poses/sec) or `3` frames at `30 fps` (`10` poses/sec), using warm wrap-key clay shading, soft tabletop contact shadow, and subtle per-pose surface variation.

## Wired skills

- `stepped-clay-lookdev` — Twos/threes stepped cadence, matte clay BSDF, and zero ghosted motion blur.
- `claymation-style` — Tactile sculptural silhouettes and handcrafted surface rhythm.
- `three-point-lighting` — Overhead softbox key, warm bounce fill, and bevel rim separation.
- `depth-of-field-budget` — Tabletop `f/5.6` separation with crisp typography.
- `color-script-progression` — Warm earth tabletop palettes above black-floor tolerances.
- `frame-clock` — Rational integer frame pacing synchronized to pose steps.
- `contrast-audit` — Accessible typography contrast over matte clay backdrops.
