---
name: audio-sync-audit
description: "Use for audio sync audit. Compare expected cue times to observed audio and visual events."
metadata:
  category: qa
  stage: review
  status: guidance
  version: "2.0.0"
  aliases: "ses görüntü kontrolü,av sync"
  requires: ""
---

# Audio Sync Audit

## Activation
Use for audio sync audit when it is a concrete work item. Search aliases: ses görüntü kontrolü,av sync. Do not activate for generic video language alone. Read the project brief and relevant hard locks before changing any asset.

## Inputs and output
- Inputs: Rendered media, brief constraints, expected metrics and references.
- Output: Timecoded defect report or corrected derivative.
- Required capability: No specific adapter is mandated; inspect the chosen implementation path.
- Evidence bundle: timecoded defect/evidence report and before/after comparison.

## Production recipe
1. Locate shot/task IDs, approved assets, frame rate, duration and relevant constraints. Verify required capability; record assumptions and do not silently substitute missing resources.
2. Compare expected cue times to observed audio and visual events.
3. Compare expected audio anchors vs video frame events and track start/end; report drift and tolerance in milliseconds; review lip sync by playback.
4. Record actual parameters in the editable source or project manifest; produce a representative preview or dry run before full execution. Apply only parameters relevant to the brief, not every technique in this skill.
5. Separate machine-measurable results from manual review; compare exact intentional exceptions; keep hard gates independent of aesthetic ratings.

## Acceptance criteria
- Offset and drift remain within project tolerance.
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
