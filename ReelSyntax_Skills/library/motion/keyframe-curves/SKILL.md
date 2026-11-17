---
name: keyframe-curves
description: "Use for keyframe curves. Set key poses and interpolate with explicit easing and frame indices."
metadata:
  category: motion
  stage: build
  status: production-guidance
  version: "2.0.0"
  aliases: "keyframe,eğri animasyonu"
  requires: ""
---

# Keyframe Curves

## Activation
Use for keyframe curves when it is a concrete work item. Search aliases: keyframe,eğri animasyonu. Do not activate for generic video language alone. Read the project brief and relevant hard locks before changing any asset.

## Inputs and output
- Inputs: Animation targets, timebase, key states and locked parameters.
- Output: Seekable animation parameters or source.
- Required capability: No specific adapter is mandated; inspect the chosen implementation path.
- Evidence bundle: frame-indexed keyframes and motion trace.

## Production recipe
1. Locate shot/task IDs, approved assets, frame rate, duration and relevant constraints. Verify required capability; record assumptions and do not silently substitute missing resources.
2. Set key poses and interpolate with explicit easing and frame indices.
3. Define normalized t with explicit frame endpoints; set interpolation and tangent continuity; review velocity plots and intermediate poses.
4. Record actual parameters in the editable source or project manifest; produce a representative preview or dry run before full execution. Apply only parameters relevant to the brief, not every technique in this skill.
5. Inspect intermediate poses, contact/extrema and two-cycle playback for loops.

## Acceptance criteria
- Endpoints land exactly and curves avoid unintended overshoot.
- Record the concrete evidence path and frame/time range or measurement, plus target/tolerance and result (`pass`, `fail`, `review`, `blocked`, `not-applicable`). Never award a pass for an unperformed check.
- Check this stage against active project locks and the production profile. Aesthetic judgment requires actual visual/audio review; technical gate success is necessary but not sufficient for release.

## Failure and repair
Correct timing, tangents, anchors or interpolation; avoid masking discontinuity with blur. If the required implementation is absent, return the exact blocker and an executable plan; do not present guidance as a rendered result. Recheck the original acceptance condition after repair.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric; load once per production, not for every skill.
- [gsap](https://github.com/greensock/gsap-skills)
- [hyperframes](https://github.com/heygen-com/hyperframes)
- [threejs](https://threejs.org/docs/)

Original production guidance. External references are starting points, not copied instructions. Verify current APIs and licenses; do not execute unreviewed third-party code.
