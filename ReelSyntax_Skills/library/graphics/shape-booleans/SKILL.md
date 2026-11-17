---
name: shape-booleans
description: "Use for shape booleans. Use union, difference and intersection on normalized contours."
metadata:
  category: graphics
  stage: build
  status: guidance
  version: "2.0.0"
  aliases: "şekil birleşimi,boolean 2d"
  requires: ""
---

# Shape Booleans

## Activation
Use for shape booleans when it is a concrete work item. Search aliases: şekil birleşimi,boolean 2d. Do not activate for generic video language alone. Read the project brief and relevant hard locks before changing any asset.

## Inputs and output
- Inputs: Canvas dimensions, source or procedural shapes, timing, style rules.
- Output: Reusable 2D composition or vector source.
- Required capability: No specific adapter is mandated; inspect the chosen implementation path.
- Evidence bundle: editable vector or scene, parameter manifest and raster preview.

## Production recipe
1. Locate shot/task IDs, approved assets, frame rate, duration and relevant constraints. Verify required capability; record assumptions and do not silently substitute missing resources.
2. Use union, difference and intersection on normalized contours.
3. Normalize fill rule and coordinate transforms; test union/intersection with holes and near-coincident edges; preserve topology.
4. Record actual parameters in the editable source or project manifest; produce a representative preview or dry run before full execution. Apply only parameters relevant to the brief, not every technique in this skill.
5. Inspect edges, alpha, aliasing and smallest target scale; repeat render at selected frame indices.

## Acceptance criteria
- Resulting fill rules preserve holes and boundaries.
- Record the concrete evidence path and frame/time range or measurement, plus target/tolerance and result (`pass`, `fail`, `review`, `blocked`, `not-applicable`). Never award a pass for an unperformed check.
- Check this stage against active project locks and the production profile. Aesthetic judgment requires actual visual/audio review; technical gate success is necessary but not sufficient for release.

## Failure and repair
Correct coordinates, path topology, compositing or resource loading; retain original vectors. If the required implementation is absent, return the exact blocker and an executable plan; do not present guidance as a rendered result. Recheck the original acceptance condition after repair.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric; load once per production, not for every skill.
- [hyperframes](https://github.com/heygen-com/hyperframes)
- [threejs](https://threejs.org/docs/)
- [gsap](https://github.com/greensock/gsap-skills)

Original production guidance. External references are starting points, not copied instructions. Verify current APIs and licenses; do not execute unreviewed third-party code.
