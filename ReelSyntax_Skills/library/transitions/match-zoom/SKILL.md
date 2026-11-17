---
name: match-zoom
description: "Use for match zoom. Align focal content and scale velocity between shots; use only if allowed."
metadata:
  category: transitions
  stage: build
  status: guidance
  version: "2.0.0"
  aliases: "zoom geçişi,match zoom"
  requires: ""
---

# Match Zoom

## Activation
Use for match zoom when it is a concrete work item. Search aliases: zoom geçişi,match zoom. Do not activate for generic video language alone. Read the project brief and relevant hard locks before changing any asset.

## Inputs and output
- Inputs: Adjacent shots or product assets, duration, lock constraints.
- Output: Parametric shot or transition with frame ranges.
- Required capability: No specific adapter is mandated; inspect the chosen implementation path.
- Evidence bundle: outgoing/incoming shot IDs, overlap and transition frames.

## Production recipe
1. Locate shot/task IDs, approved assets, frame rate, duration and relevant constraints. Verify required capability; record assumptions and do not silently substitute missing resources.
2. Align focal content and scale velocity between shots; use only if allowed.
3. Match focal target position, projected scale and velocity across edit; reserve overscan and avoid zoom where prohibited.
4. Record actual parameters in the editable source or project manifest; produce a representative preview or dry run before full execution. Apply only parameters relevant to the brief, not every technique in this skill.
5. Inspect first, seam, peak and last frame, then playback; verify no missing coverage or unintended flash.

## Acceptance criteria
- No sudden subject-center shift and constraints respected.
- Record the concrete evidence path and frame/time range or measurement, plus target/tolerance and result (`pass`, `fail`, `review`, `blocked`, `not-applicable`). Never award a pass for an unperformed check.
- Check this stage against active project locks and the production profile. Aesthetic judgment requires actual visual/audio review; technical gate success is necessary but not sufficient for release.

## Failure and repair
Rework seam alignment, duration or matte; fall back to motivated cut if effect cannot meet constraints. If the required implementation is absent, return the exact blocker and an executable plan; do not present guidance as a rendered result. Recheck the original acceptance condition after repair.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric; load once per production, not for every skill.
- [shotcraft](https://github.com/Vincentwei1021/video-shotcraft)
- [gsap](https://github.com/greensock/gsap-skills)
- [hyperframes](https://github.com/heygen-com/hyperframes)

Original production guidance. External references are starting points, not copied instructions. Verify current APIs and licenses; do not execute unreviewed third-party code.
