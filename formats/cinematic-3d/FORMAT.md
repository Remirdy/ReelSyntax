# Cinematic 3D Studio (`cinematic-3d`)

Studio 3D monolithic look-development and three-point lighting showcase for `16:9`, `9:16`, and `1:1` canvases.

## Creative intent and rendering paths

- **Native Blender (`bpy`) path:** Builds a cyclorama stage, beveled monolith slabs, floating orbital torus, `Key` / `Fill` / `Rim` area lights, `RSFocusTarget` depth of field (`f/4.0`), and Cycles (`hero`) or EEVEE (`draft`/`production`) with `AgX` view transform.
- **Offline Pillow procedural fallback:** Renders soft Gaussian-blurred DoF background bokeh discs, three-point PBR-shaded 3D monolith facets (`AgX` tonemapped), `cos^4` optical vignette (`Y_corner` safely above `blackdetect`), and thresholded warm highlight halation strictly underneath crisp foreground typography.

## Wired skills

- `render-lookdev` — Material, camera, and tone-curve staging across `draft` and `hero`.
- `three-point-lighting` — Key, cool-fill, and fresnel rim separation on dark studio grounds.
- `depth-of-field-budget` — Background `CoC` separation with zero blur on typography planes.
- `optical-vignette-halation` — Linear-light peripheral falloff and thresholded highlight bloom below text.
- `color-script-progression` — Cohesive OKLCH lightness and accent arcs with safe dark floor (`Y >= 44/255`).
- `blender-cycles` — Headless Cycles/EEVEE rendering with deterministic fallback to Pillow when Blender is absent.
- `frame-clock` — Rational `24/1` or `30/1` integer-frame pacing.
- `contrast-audit` — WCAG foreground/accent legibility verification.
