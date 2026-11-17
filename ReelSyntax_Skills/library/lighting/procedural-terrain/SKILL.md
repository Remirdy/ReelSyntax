---
name: procedural-terrain
description: "Use for procedural terrain. Generate terrain from seeded height data and constrain slopes for action paths."
metadata:
  category: lighting
  stage: build
  status: production-guidance
  version: "2.0.0"
  aliases: "arazi,terrain"
  requires: ""
---

# Procedural Terrain

## Activation
Use for procedural terrain when it is a concrete work item. Search aliases: arazi,terrain. Do not activate for generic video language alone. Read the project brief and relevant hard locks before changing any asset.

## Inputs and output
- Inputs: Scene geometry, materials, target mood, engine and camera.
- Output: Light/environment configuration and sample render.
- Required capability: No specific adapter is mandated; inspect the chosen implementation path.
- Evidence bundle: light rig, exposure/color configuration and neutral/hero frames.

## Production recipe
1. Locate shot/task IDs, approved assets, frame rate, duration and relevant constraints. Verify required capability; record assumptions and do not silently substitute missing resources.
2. Generate terrain from seeded height data and constrain slopes for action paths.
3. Generate terrain with unit scale, slope constraints and named seed; inspect collision and LOD at camera path.
4. Record actual parameters in the editable source or project manifest; produce a representative preview or dry run before full execution. Apply only parameters relevant to the brief, not every technique in this skill.
5. Inspect shadows, reflections, highlight rolloff and temporal stability under target output transform.

## Acceptance criteria
- No terrain discontinuity or unintended floating objects.
- Record the concrete evidence path and frame/time range or measurement, plus target/tolerance and result (`pass`, `fail`, `review`, `blocked`, `not-applicable`). Never award a pass for an unperformed check.
- Check this stage against active project locks and the production profile. Aesthetic judgment requires actual visual/audio review; technical gate success is necessary but not sufficient for release.

## Failure and repair
Adjust source size/direction/exposure or sampling before grading; avoid crushing detail to conceal noise. If the required implementation is absent, return the exact blocker and an executable plan; do not present guidance as a rendered result. Recheck the original acceptance condition after repair.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric; load once per production, not for every skill.
- [threejs](https://threejs.org/docs/)
- [blender](https://docs.blender.org/api/current/)

Original production guidance. External references are starting points, not copied instructions. Verify current APIs and licenses; do not execute unreviewed third-party code.
