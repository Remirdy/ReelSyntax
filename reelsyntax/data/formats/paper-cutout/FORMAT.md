# Paper Cutout (`paper-cutout`)

Layered 2.5D Z-offset paper silhouettes with unified directional shadow, local fiber texture, cut-edge highlights, and gentle parallax (`--reduced-motion` static unfold).

## Creative intent and rendering paths

- **Offline Pillow procedural renderer:** Composites Z-ordered cardstock silhouettes with one locked top-left global light vector (`~130°`), drop shadows proportional to plane gap `Δz`, `1.5–2 px` ivory cut-edge rims, and local-coordinate paper grain baked before parallax translation. Under `--reduced-motion` or `camera_locked`, parallax drops to zero and layers unfold cleanly in sequence.
- **Optional Blender (`bpy`) path:** Builds physical stacked cardstock planes along `Y` with `Solidify` edge thickness, matte paper BSDF (`roughness = 0.88`), unified directional shadow light, and gentle parallax camera drift.

## Wired skills

- `paper-cutout-layering` — Z-gap proportional shadows, cut-edge bevels, and local grain.
- `paper-cut-style` — Coherent stacked cardstock staging across vertical and widescreen ratios.
- `alpha-compositing-2d` — Clean premultiplied-style RGBA layer ordering and soft drop shadows.
- `color-script-progression` — Editorial parchment and terracotta matte palettes.
- `contrast-audit` — High-contrast label rail over uncluttered backing paper.
- `frame-clock` — Rational `30/1` frame allocation and smooth dissolves.
