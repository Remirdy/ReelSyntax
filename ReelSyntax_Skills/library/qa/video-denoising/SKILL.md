---
name: video-denoising
description: "Use for video denoising. Apply conservative spatial or temporal filtering and preserve detail and cadence."
metadata:
  category: qa
  stage: review
  status: guidance
  version: "2.0.0"
  aliases: "video gürültü azaltma,denoise"
  requires: ""
---

# Video Denoising

## Activation
Use for video denoising when it is a concrete work item. Search aliases: video gürültü azaltma,denoise. Do not activate for generic video language alone. Read the project brief and relevant hard locks before changing any asset.

## Inputs and output
- Inputs: Rendered media, brief constraints, expected metrics and references.
- Output: Timecoded defect report or corrected derivative.
- Required capability: No specific adapter is mandated; inspect the chosen implementation path.
- Evidence bundle: timecoded defect/evidence report and before/after comparison.

## Production recipe
1. Locate shot/task IDs, approved assets, frame rate, duration and relevant constraints. Verify required capability; record assumptions and do not silently substitute missing resources.
2. Apply conservative spatial or temporal filtering and preserve detail and cadence.
3. Compare temporal/spatial denoise on representative moving details; avoid waxy faces, ghosting and flicker; retain original and settings.
4. Record actual parameters in the editable source or project manifest; produce a representative preview or dry run before full execution. Apply only parameters relevant to the brief, not every technique in this skill.
5. Separate machine-measurable results from manual review; compare exact intentional exceptions; keep hard gates independent of aesthetic ratings.

## Acceptance criteria
- A/B crops show improvement without waxy artifacts or trails.
- Record the concrete evidence path and frame/time range or measurement, plus target/tolerance and result (`pass`, `fail`, `review`, `blocked`, `not-applicable`). Never award a pass for an unperformed check.
- Check this stage against active project locks and the production profile. Aesthetic judgment requires actual visual/audio review; technical gate success is necessary but not sufficient for release.

## Failure and repair
Localize root cause, patch smallest scope, rerun relevant checks and record unresolved issues. If the required implementation is absent, return the exact blocker and an executable plan; do not present guidance as a rendered result. Recheck the original acceptance condition after repair.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric; load once per production, not for every skill.
- [ffmpeg](https://ffmpeg.org/ffmpeg-filters.html)
- [wcag](https://www.w3.org/TR/WCAG22/)
- [openmontage](https://github.com/OpenMontageInc/OpenMontage)

Original production guidance. External references are starting points, not copied instructions. Verify current APIs and licenses; do not execute unreviewed third-party code.
