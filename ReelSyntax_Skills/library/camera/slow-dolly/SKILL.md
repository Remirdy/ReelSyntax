---
name: slow-dolly
description: "Use for slow dolly. Translate camera along a planned path with eased endpoints and parallax control."
metadata:
  category: camera
  stage: plan
  status: guidance
  version: "2.0.0"
  aliases: "dolly,kamera yaklaşma"
  requires: ""
---

# Slow Dolly

## Activation
Use for slow dolly when it is a concrete work item. Search aliases: dolly,kamera yaklaşma. Do not activate for generic video language alone. Read the project brief and relevant hard locks before changing any asset.

## Inputs and output
- Inputs: Scene geometry, subject, approved shot duration, camera constraints.
- Output: Camera parameters, path or framing specification.
- Required capability: No specific adapter is mandated; inspect the chosen implementation path.
- Evidence bundle: camera parameters, transforms and sampled frames.

## Production recipe
1. Locate shot/task IDs, approved assets, frame rate, duration and relevant constraints. Verify required capability; record assumptions and do not silently substitute missing resources.
2. Translate camera along a planned path with eased endpoints and parallax control.
3. Animate position along explicit path with continuous velocity; choose ramp relative to shot length; test foreground parallax and clipping at extremes.
4. Record actual parameters in the editable source or project manifest; produce a representative preview or dry run before full execution. Apply only parameters relevant to the brief, not every technique in this skill.
5. Review start, middle, end and motion extrema; inspect a projection or transform trace where available.

## Acceptance criteria
- Subject stays readable and move has no abrupt velocity jump.
- Record the concrete evidence path and frame/time range or measurement, plus target/tolerance and result (`pass`, `fail`, `review`, `blocked`, `not-applicable`). Never award a pass for an unperformed check.
- Check this stage against active project locks and the production profile. Aesthetic judgment requires actual visual/audio review; technical gate success is necessary but not sufficient for release.

## Failure and repair
Repair path, lens, collision or orientation at the shot level; do not add unrequested movement. If the required implementation is absent, return the exact blocker and an executable plan; do not present guidance as a rendered result. Recheck the original acceptance condition after repair.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric; load once per production, not for every skill.
- [shotcraft](https://github.com/Vincentwei1021/video-shotcraft)
- [cinema-skills](https://github.com/DenisHumen/cinema-skills)
- [threejs](https://threejs.org/docs/)

Original production guidance. External references are starting points, not copied instructions. Verify current APIs and licenses; do not execute unreviewed third-party code.
