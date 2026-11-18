---
name: paper-cutout-layering
description: "Construct 2.5D multi-plane paper cutout scenes with Z-coupled drop-shadow offsets, subtle white cut-edge bevels, local fiber texture, and parallax camera drift."
metadata:
  category: graphics
  stage: build
  status: validated
  version: "2.0.0"
  aliases: "paper cutout layering,2.5d paper parallax build,çok katmanlı kağıt kesme kurulumu,kağıt katman gölge ve paralaks,Papier-Schnitt-Ebenenaufbau,mehrschichtiger Scherenschnitt-Parallax,capas de recorte de papel,superposition de papier découpé"
  requires: ""
---

# Paper Cutout Layering

## Activation
Activate when building `paper-cutout` scenes in Pillow, Canvas/SVG, or 2.5D planes where flat vector shapes must read as physical stacked cardstock with consistent directional shadows, cut-edge thickness, and multi-plane parallax. Search aliases: `paper cutout layering`, `çok katmanlı kağıt kesme kurulumu`, `Papier-Schnitt-Ebenenaufbau`.

## Decision rules
- **Single global light vector across all planes**: lock one directional shadow angle (`azimuth = 130°` top-left light casting down-right `(dx > 0, dy > 0)`) across every cutout layer `z = 0..K`; inconsistent shadow directions break the physical paper illusion immediately.
- **Shadow offset & blur proportional to plane gap `Δz`, not absolute `z`**: a sticker resting directly on card `2` (`Δz = 1`) casts a tight crisp shadow (`offset = 4 px, blur = 3 px`) onto card `2`, while card `2` floating `Δz = 4` above background `0` casts a wider softer shadow (`offset = 16 px, blur = 12 px`) onto background `0`!
- **Physical cut-edge rim (`1.5–2.5 px`)**: draw a `1.5–2 px` warm ivory/tinted top-left inner/outer bevel rim along cut silhouettes (`opacity = 0.35`) so dark-on-dark cardstock layers still separate cleanly as physical die-cut thickness.
- **Texture locked to layer coordinates**: bind subtle cotton/kraft fiber noise (`+-3/255` monochromatic grain) to each layer's **local** `(u, v)` coordinates so grain moves *with* the paper piece during slides or parallax pans rather than swimming like a dirty lens window!

## Parameters and defaults
- `plane_count`: `4–6` planes (`z0` backing mat, `z1` horizon/frame, `z2` midground shapes, `z3` hero focal cutout, `z4` foreground frame arch / typography card).
- `light_dir_unit`: `(0.64, 0.77)` (`~50°` down-right shadow cast from top-left key).
- `shadow_px_per_z_unit`: `4.0` px offset and `3.0` px Gaussian blur per `Δz = 1.0` at `1080p` (`rgba(14, 18, 26, 0.34)` multiply).
- `parallax_px_per_z_unit`: `9.0` px horizontal/vertical drift across scene duration (`0.0` when `camera_locked` / `--reduced-motion`).
- `paper_grain_lsb`: `3.5` (`+-3.5/255` deterministic hash grain in local layer space).

## Procedure
1. Assign each scene element an explicit integer/float plane height `z ∈ [0.0, 5.0]` sorted back-to-front.
2. Pre-generate or sample deterministic cotton-paper grain per layer seed in local coordinates and tint with warm/editorial matte paper swatches (`OKLCH C <= 0.11`, zero neon `#00FF00` RGB primaries).
3. For each layer `i > 0` at frame `f`, compute parallax offset `p_i(f) = camera_pan(f) * (z_i / z_ref)`.
4. Composite in strict painter's order (`z0 -> zK`): for layer `i`, draw its blurred alpha-matte drop shadow shifted by `light_dir * shadow_px_per_z * (z_i - z_{i-1})`, draw the `1.5 px` top-left cut-edge highlight rim, then composite the opaque grained paper silhouette.
5. Place primary text on a dedicated flat cream/charcoal label strip (`z_top`) with zero grain interference above `>= 7.0:1` WCAG contrast.

## Failure modes and fixes
- **Screen-space static grain makes moving paper look like moving masks over wallpaper**: generate grain inside each layer's own RGBA buffer *before* translating by `p_i(f)`.
- **Pure black `rgba(0,0,0,0.85)` drop shadows look muddy and digital**: tint shadow color subtly toward deep warm indigo/umber (`rgba(22, 20, 32, 0.34)`) and soften blur proportionally to `Δz`.
- **Foreground arch frame clips caption safe zone**: restrict `z4` decorative border cutouts to the outer `7%` canvas perimeter outside `vertical_safe_zones`.

## Checklist
- [ ] All layers share one unified top-left light vector (`dx, dy` proportional to `Δz`).
- [ ] Paper fiber grain is baked in local layer coordinates (moves with the cutout).
- [ ] `1.5–2 px` cut-edge bevel rim separates overlapping dark or light cardstock tones.
- [ ] Label card typography maintains `>= 7.0:1` contrast and stays inside safe zones.

## Worked examples
- **Example 1 (`1080x1920` 5-plane botanical/editorial story card)**: `z0` warm sand `#E8E1D5`, `z1` recessed arch window (`z=1`, inner cutout shadow `4px`), `z2` terracotta hill (`#C86D51`, `z=2`), `z3` hero paper bird (`#F7F3EB`, `z=3.5`, `10px` soft shadow + `2px` ivory rim), `z4` charcoal title banner (`#23252C` with `#FAF6EE` type = `13.1:1`). Gentle `24 px` parallax drift over `75` frames.
- **Example 2 (`--reduced-motion` cutout card)**: `parallax_px_per_z_unit = 0`, cards reveal via clean `8`-frame sequential paper unfold opacity/drop settle (`z1 -> z2 -> z3`).

## Resources (load only if needed)
- [2.5D Z-plane shadow, bevel, and parallax equations](references/z-plane-shadow-and-parallax-math.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
