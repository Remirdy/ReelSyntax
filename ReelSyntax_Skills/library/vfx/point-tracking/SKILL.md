---
name: point-tracking
description: "Use for point tracking. Track stable features and reject outliers before applying translation or stabilization."
metadata:
  category: vfx
  stage: build
  status: production-guidance
  version: "2.0.0"
  aliases: "nokta takibi,motion tracking"
  requires: ""
---

# Point Tracking

## Activation
Use for point tracking when it is a concrete work item. Search aliases: nokta takibi,motion tracking. Do not activate for generic video language alone. Read the project brief and relevant hard locks before changing any asset.

## Inputs and output
- Inputs: Source plate or scene layers, timebase, alpha and color metadata.
- Output: Editable effect/composite and sample frames.
- Required capability: No specific adapter is mandated; inspect the chosen implementation path.
- Evidence bundle: source plate hashes, passes/matte, effect parameters and composite.

## Production recipe
1. Locate shot/task IDs, approved assets, frame rate, duration and relevant constraints. Verify required capability; record assumptions and do not silently substitute missing resources.
2. Track stable features and reject outliers before applying translation or stabilization.
3. Track stable features with forward/backward consistency; handle occlusion and reset track rather than extrapolating indefinitely.
4. Record actual parameters in the editable source or project manifest; produce a representative preview or dry run before full execution. Apply only parameters relevant to the brief, not every technique in this skill.
5. A/B plate and composite at edges, motion extrema and target scale; check alpha/color/temporal stability.

## Acceptance criteria
- Tracked anchors remain within tolerance.
- Record the concrete evidence path and frame/time range or measurement, plus target/tolerance and result (`pass`, `fail`, `review`, `blocked`, `not-applicable`). Never award a pass for an unperformed check.
- Check this stage against active project locks and the production profile. Aesthetic judgment requires actual visual/audio review; technical gate success is necessary but not sufficient for release.

## Failure and repair
Repair matte/tracking/space or tame effect strength; re-render affected passes rather than entire project. If the required implementation is absent, return the exact blocker and an executable plan; do not present guidance as a rendered result. Recheck the original acceptance condition after repair.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric; load once per production, not for every skill.
- [ffmpeg](https://ffmpeg.org/ffmpeg-filters.html)
- [threejs](https://threejs.org/docs/)
- [blender](https://docs.blender.org/api/current/)

Original production guidance. External references are starting points, not copied instructions. Verify current APIs and licenses; do not execute unreviewed third-party code.
