---
name: video-stitching
description: "Use for video stitching. Normalize streams when necessary; preserve timestamps and avoid redundant encodes."
metadata:
  category: editing
  stage: edit
  status: production-guidance
  version: "2.0.0"
  aliases: "video birleştir,concat"
  requires: ""
---

# Video Stitching

## Activation
Use for video stitching when it is a concrete work item. Search aliases: video birleştir,concat. Do not activate for generic video language alone. Read the project brief and relevant hard locks before changing any asset.

## Inputs and output
- Inputs: Source files, timestamps, timeline plan, handles and constraints.
- Output: Non-destructive edit decisions and preview.
- Required capability: No specific adapter is mandated; inspect the chosen implementation path.
- Evidence bundle: source/record in-out points, handles and edit preview.

## Production recipe
1. Locate shot/task IDs, approved assets, frame rate, duration and relevant constraints. Verify required capability; record assumptions and do not silently substitute missing resources.
2. Normalize streams when necessary; preserve timestamps and avoid redundant encodes.
3. Normalize dimensions, pixel format, FPS/timebase, audio layout and color before concat; retain exact frame and sample counts.
4. Record actual parameters in the editable source or project manifest; produce a representative preview or dry run before full execution. Apply only parameters relevant to the brief, not every technique in this skill.
5. Watch full edit at normal speed, then inspect cut boundaries and frame/audio duration reconciliation.

## Acceptance criteria
- Joined video has continuous timing and coherent sound.
- Record the concrete evidence path and frame/time range or measurement, plus target/tolerance and result (`pass`, `fail`, `review`, `blocked`, `not-applicable`). Never award a pass for an unperformed check.
- Check this stage against active project locks and the production profile. Aesthetic judgment requires actual visual/audio review; technical gate success is necessary but not sufficient for release.

## Failure and repair
Correct source range, overlap, sync or coverage; preserve source and locked regions. If the required implementation is absent, return the exact blocker and an executable plan; do not present guidance as a rendered result. Recheck the original acceptance condition after repair.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric; load once per production, not for every skill.
- [ffmpeg](https://ffmpeg.org/ffmpeg-filters.html)
- [vidmoat](https://github.com/vidmoat/skills)
- [hypit](https://github.com/hypit-ai/hypit)

Original production guidance. External references are starting points, not copied instructions. Verify current APIs and licenses; do not execute unreviewed third-party code.
