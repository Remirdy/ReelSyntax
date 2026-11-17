---
name: signed-distance-fields
description: "Use for signed distance fields. Construct 2D and 3D procedural geometry with smooth polynomial CSG booleans, analytical normals, and soft penumbra shadows."
metadata:
  category: vfx
  stage: build
  status: production-guidance
  version: "2.0.0"
  aliases: "sdf raymarching,signed distance field,smooth boolean,analitik mesafe alanı"
  requires: ""
---

# Signed Distance Fields

## Activation
Use when generating procedural emblems, organic morphs, bevelled industrial forms, or shader raymarched scenes where polygon tessellation would facet or pop. Search aliases: sdf raymarching,signed distance field,smooth boolean,analitik mesafe alanı.

## Inputs and output
- Inputs: Primitive SDF tree, blend radius $k$, camera ray parameters, lighting rig, and target frame resolution.
- Output: Anti-aliased procedural frame sequence or shader module with analytical normals and soft shadows.
- Required capability: Canvas/WebGL shader, Blender shader/geometry nodes, or Python rasterizer.
- Evidence bundle: Raymarch step-count ceiling, silhouette anti-aliasing check, and zero surface-acne verification.

## Production recipe
1. Compose exact Euclidean distance primitives ($d_{\text{box}}, d_{\text{sphere}}, d_{\text{torus}}, d_{\text{capsule}}$) before applying domain repetition or non-uniform scaling; divide step length by the maximum Lipschitz deformation factor.
2. Blend intersections/unions smoothly via quadratic polynomial smooth-min:
   $h = \max(k - |a - b|, 0) / k$, $\text{smin}(a, b, k) = \min(a, b) - \frac{1}{4} h^2 k$ to create machined fillets without extra polygons.
3. Compute surface normals via the 4-sample tetrahedral finite difference ($\epsilon \approx 0.5 \cdot \text{pixel footprint}$ at hit distance $t$) rather than 6-sample central differences.
4. March secondary shadow rays with penumbra factor $s = \min_t (w \cdot d(p + t\mathbf{l}) / t)$ and 5-tap normal-aligned ambient occlusion.
5. Anti-alias 2D SDF contours analytically via `smoothstep(-px, +px, d)` using screen-space derivative width `fwidth(d)`.

## Acceptance criteria
- Bounded raymarch loop ($\le 96$ primary steps) with explicit far-plane bailout; no infinite shader hangs.
- Smooth CSG fillets free of normal discontinuities or self-shadowing banding (`self_bias >= 2 * hit_eps`).
- Record shader/recipe source, step budget, frame render time, and silhouette inspection result.

## Failure and repair
Overstepping silhouettes or shadow banding comes from non-unit gradient fields after twist/bend warps: multiply march step by $0.6\text{–}0.8$ and offset shadow ray origin along the surface normal.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric.
- [Three.js ShaderMaterial](https://threejs.org/docs/#api/en/materials/ShaderMaterial)

Original production guidance.
