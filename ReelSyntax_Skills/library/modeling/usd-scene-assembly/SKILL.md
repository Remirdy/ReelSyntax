---
name: usd-scene-assembly
description: "Use for OpenUSD scene assembly. Structure non-destructive .usda sublayers, asset payloads, lookdev VariantSets, and rational timeSamples for 3D cinematic pipelines."
metadata:
  category: modeling
  stage: export
  status: guidance
  version: "2.0.0"
  aliases: "openusd,usda sahne,usd variant,universal scene description"
  requires: ""
---

# Usd Scene Assembly

## Activation
Use when assembling multi-shot 3D scenes, exchanging non-destructive camera/lighting overrides with Blender or USD-capable DCCs, or managing lookdev variants without duplicating heavy geometry. Search aliases: openusd,usda sahne,usd variant,universal scene description.

## Inputs and output
- Inputs: Shot timeline, rational FPS, geometry asset paths, camera transforms, and material variants.
- Output: Valid UTF-8 `.usda` stage hierarchy separating geometry, lookdev, lighting, and shot animation layers.
- Required capability: ASCII `.usda` writer or Blender `bpy.ops.wm.usd_export` when installed.
- Evidence bundle: Stage metadata (`upAxis`, `metersPerUnit`, `timeCodesPerSecond`), resolved asset references, and round-trip import report.

## Production recipe
1. Declare stage root metadata explicitly at the top of every `.usda` file: `upAxis = "Z"` (Blender convention) or `"Y"` (USD/stage convention—never mix unannounced), `metersPerUnit = 1.0`, `startTimeCode`, `endTimeCode`, and `timeCodesPerSecond`.
2. Split shot assembly into non-destructive opinion layers (`layout.usda`, `lookdev.usda`, `lighting.usda`, `camera_shot010.usda`) composed via `subLayers` so revising lighting never rewrites geometry or approved camera animation.
3. Wrap heavy meshes behind `payload` arcs and bind material options through a `VariantSet` (`draft_clay`, `production_pbr`, `hero_agx`).
4. Express camera focal length (`focalLength` in tenths of mm or mm per USD `UsdGeomCamera` schema: standard USD uses **millimeters** for `focalLength` and `horizontalAperture`, e.g. `focalLength = 50`, `horizontalAperture = 36`) and verify aperture units on import.

## Acceptance criteria
- All relative asset/sublayer paths stay inside project root without symlinks or absolute machine leaks.
- Stage opens with matching frame range, unit scale, and camera FOV in target consumer.
- Record `.usda` digest, declared `upAxis`/`metersPerUnit`, and import check status.

## Failure and repair
90-degree tilted scenes or 100x scale jumps indicate `upAxis` (`Y` vs `Z`) or `metersPerUnit` (`0.01` cm vs `1.0` m) mismatch: fix root stage metadata rather than baking ad-hoc object transforms.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric.
- [Blender USD Export](https://docs.blender.org/api/current/bpy.ops.wm.html)

Original production guidance.
