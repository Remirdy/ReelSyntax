---
name: whip-pan
description: "Use for whip pan. Accelerate rotation into a short motion-blurred reveal with matched next-shot direction."
metadata:
  category: camera
  stage: plan
  status: guidance
  version: "2.0.0"
  aliases: "hızlı pan,whip pan"
  requires: ""
---

# Whip Pan

## Activation
Use for whip pan when it is a concrete work item. Search aliases: hızlı pan,whip pan. Do not activate for generic video language alone. Read the project brief and relevant hard locks before changing any asset.

## Inputs and output
- Inputs: Scene geometry, subject, approved shot duration, camera constraints.
- Output: Camera parameters, path or framing specification.
- Required capability: No specific adapter is mandated; inspect the chosen implementation path.
- Evidence bundle: camera parameters, transforms and sampled frames.

## Production recipe
1. Locate shot/task IDs, approved assets, frame rate, duration and relevant constraints. Verify required capability; record assumptions and do not silently substitute missing resources.
2. Accelerate rotation into a short motion-blurred reveal with matched next-shot direction.
3. Match angular direction and exposure across cut; tune short shutter blur around rotation, not whole shot; inspect peak for unintended white flash.
4. Record actual parameters in the editable source or project manifest; produce a representative preview or dry run before full execution. Apply only parameters relevant to the brief, not every technique in this skill.
5. Review start, middle, end and motion extrema; inspect a projection or transform trace where available.

## Acceptance criteria
- The transition hides the intended seam without a flash artifact.
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
