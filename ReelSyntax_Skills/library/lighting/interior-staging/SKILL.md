---
name: interior-staging
description: "Use for interior staging. Arrange room geometry, props and sightlines consistent with setting and culture."
metadata:
  category: lighting
  stage: build
  status: guidance
  version: "2.0.0"
  aliases: "iç mekan,sınıf ortamı"
  requires: ""
---

# Interior Staging

## Activation
Use for interior staging when it is a concrete work item. Search aliases: iç mekan,sınıf ortamı. Do not activate for generic video language alone. Read the project brief and relevant hard locks before changing any asset.

## Inputs and output
- Inputs: Scene geometry, materials, target mood, engine and camera.
- Output: Light/environment configuration and sample render.
- Required capability: No specific adapter is mandated; inspect the chosen implementation path.
- Evidence bundle: light rig, exposure/color configuration and neutral/hero frames.

## Production recipe
1. Locate shot/task IDs, approved assets, frame rate, duration and relevant constraints. Verify required capability; record assumptions and do not silently substitute missing resources.
2. Arrange room geometry, props and sightlines consistent with setting and culture.
3. Block floor, walls, practical lights and furniture at real dimensions; inspect camera access and motivated depth layers.
4. Record actual parameters in the editable source or project manifest; produce a representative preview or dry run before full execution. Apply only parameters relevant to the brief, not every technique in this skill.
5. Inspect shadows, reflections, highlight rolloff and temporal stability under target output transform.

## Acceptance criteria
- Camera path and character placement fit actual room layout.
- Record the concrete evidence path and frame/time range or measurement, plus target/tolerance and result (`pass`, `fail`, `review`, `blocked`, `not-applicable`). Never award a pass for an unperformed check.
- Check this stage against active project locks and the production profile. Aesthetic judgment requires actual visual/audio review; technical gate success is necessary but not sufficient for release.

## Failure and repair
Adjust source size/direction/exposure or sampling before grading; avoid crushing detail to conceal noise. If the required implementation is absent, return the exact blocker and an executable plan; do not present guidance as a rendered result. Recheck the original acceptance condition after repair.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric; load once per production, not for every skill.
- [threejs](https://threejs.org/docs/)
- [blender](https://docs.blender.org/api/current/)

Original production guidance. External references are starting points, not copied instructions. Verify current APIs and licenses; do not execute unreviewed third-party code.
