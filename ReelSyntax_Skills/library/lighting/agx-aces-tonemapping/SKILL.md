---
name: agx-aces-tonemapping
description: "Use for AgX and ACES tone mapping. Evaluate lighting in unbounded scene-referred linear RGB and apply gamut-preserving highlight desaturation exactly once."
metadata:
  category: lighting
  stage: render
  status: validated
  version: "2.0.0"
  aliases: "agx tonemapping,aces output transform,filmic highlight rolloff,renk sıkıştırma"
  requires: ""
---

# Agx Aces Tonemapping

## Activation
Use when rendering 3D lighting, specular highlights, emissive materials, or compositing linear passes to sRGB / BT.709 delivery. Search aliases: agx tonemapping,aces output transform,filmic highlight rolloff,renk sıkıştırma.

## Inputs and output
- Inputs: Linear scene-referred RGB buffers/shaders, chosen display view transform (`AgX`, `ACES`, or `neutral`), and target delivery transfer (`bt709` / `sRGB`).
- Output: Display-referred RGB frames with preserved highlight hue and declared color tags.
- Required capability: `reelsyntax.palette` linear-light pipeline, Blender 4.x/5.x `AgX`, or Three.js color management.
- Evidence bundle: Clipped-pixel percentage ($< 0.5\%$ non-emissive), neutral vs hero look comparison frame, and FFprobe BT.709 stream metadata.

## Production recipe
1. Convert all albedo/palette hex colors (`#RRGGBB`) from sRGB electro-optical transfer into linear light before multiplying light intensities or blending alpha; never compute lighting directly in gamma-encoded sRGB.
2. Apply an inset matrix prior to per-channel sigmoid compression (AgX principle): attenuate purity slightly as luminance approaches shoulder saturation so intense warm/blue lights desaturate gracefully toward white rather than skewing cyan/magenta/yellow as raw per-channel clipping or unguarded ACES sRGB RRT can do.
3. Apply the view/display output transform **exactly once** at final display encoding. In Blender 4.x/5.x set `scene.view_settings.view_transform = "AgX"` on the scene instance (do not query static `bl_rna` enum items, which omit dynamic OCIO views).
4. Add deterministic $\pm 0.5\text{ LSB}$ triangular dither before 8-bit `yuv420p` quantization to suppress sky/vignette Mach banding.

## Acceptance criteria
- Specular highlights roll off smoothly without hard flat-topped RGB channel plateaus or hue inversion.
- Exactly one output transform applied; video stream carries explicit `bt709` primaries/transfer/matrix.
- Record neutral vs graded comparison path and measured peak/clipped pixel ratio.

## Failure and repair
Double-tonemapped (milky/washed) or double-gamma (dark/crushed) output indicates mismatched input texture color spaces or stacked display transforms: trace linear-to-display boundary and disable duplicate LUT/view stages.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric.
- [ACES Output Transforms](https://docs.acescentral.com/system-components/output-transforms/)
- [Three.js Color Management](https://threejs.org/manual/pages/color-management.html)

Original production guidance and validated runtime math.
