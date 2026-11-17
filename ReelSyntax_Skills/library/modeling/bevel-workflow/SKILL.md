---
name: bevel-workflow
description: "Use for bevel workflow. Choose bevel width relative to object scale and control normal smoothing."
metadata:
  category: modeling
  stage: build
  status: production-guidance
  version: "2.0.0"
  aliases: "bevel,kenar yuvarlama"
  requires: ""
---

# Bevel Workflow

## Activation
Use for bevel workflow when it is a concrete work item. Search aliases: bevel,kenar yuvarlama. Do not activate for generic video language alone. Read the project brief and relevant hard locks before changing any asset.

## Inputs and output
- Inputs: Model reference, dimensions, target engine and resource budget.
- Output: Editable mesh, material, asset manifest or validation report.
- Required capability: No specific adapter is mandated; inspect the chosen implementation path.
- Evidence bundle: source mesh, material/texture manifest and turntable or hero test.

## Production recipe
1. Locate shot/task IDs, approved assets, frame rate, duration and relevant constraints. Verify required capability; record assumptions and do not silently substitute missing resources.
2. Choose bevel width relative to object scale and control normal smoothing.
3. Use real-scale bevel width smaller than adjacent features; set segments by silhouette and specular needs; inspect grazing highlights.
4. Record actual parameters in the editable source or project manifest; produce a representative preview or dry run before full execution. Apply only parameters relevant to the brief, not every technique in this skill.
5. Inspect wireframe, silhouette, grazing highlights and scale; verify export in a second reader when practical.

## Acceptance criteria
- Highlights reveal edges without pinching or self-intersection.
- Record the concrete evidence path and frame/time range or measurement, plus target/tolerance and result (`pass`, `fail`, `review`, `blocked`, `not-applicable`). Never award a pass for an unperformed check.
- Check this stage against active project locks and the production profile. Aesthetic judgment requires actual visual/audio review; technical gate success is necessary but not sufficient for release.

## Failure and repair
Fix mesh, transforms, texture conventions or material parameters before increasing render samples. If the required implementation is absent, return the exact blocker and an executable plan; do not present guidance as a rendered result. Recheck the original acceptance condition after repair.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric; load once per production, not for every skill.
- [threejs](https://threejs.org/docs/)
- [blender](https://docs.blender.org/api/current/)

Original production guidance. External references are starting points, not copied instructions. Verify current APIs and licenses; do not execute unreviewed third-party code.
