---
name: caption-delivery-package
description: "Use for caption delivery package. Deliver requested burned-in and separate captions plus language tags and transcript where relevant."
metadata:
  category: delivery
  stage: export
  status: guidance
  version: "2.0.0"
  aliases: "altyazı teslimi,subtitle package,caption delivery package,Untertitel-Lieferpaket,SRT-VTT-Auslieferung"
  requires: ""
---

# Caption Delivery Package

## Activation
Use for caption delivery package when it is a concrete work item. Search aliases: altyazı teslimi,subtitle package. Do not activate for generic video language alone. Read the project brief and relevant hard locks before changing any asset.

## Inputs and output
- Inputs: Approved timeline, final assets, output target and delivery specification.
- Output: Verified export or interchange bundle.
- Required capability: No specific adapter is mandated; inspect the chosen implementation path.
- Evidence bundle: deliverable manifest, codec/timebase/color/audio settings and file.

## Production recipe
1. Locate shot/task IDs, approved assets, frame rate, duration and relevant constraints. Verify required capability; record assumptions and do not silently substitute missing resources.
2. Deliver requested burned-in and separate captions plus language tags and transcript where relevant.
3. Package UTF-8 caption tracks, language tags, safe cue timing and optional burned copy; verify player import and exact spoken content.
4. Record actual parameters in the editable source or project manifest; produce a representative preview or dry run before full execution. Apply only parameters relevant to the brief, not every technique in this skill.
5. Decode and probe actual output, test target import/playback if available, validate checksums.

## Acceptance criteria
- Files and final render agree with approved cues and languages.
- Record the concrete evidence path and frame/time range or measurement, plus target/tolerance and result (`pass`, `fail`, `review`, `blocked`, `not-applicable`). Never award a pass for an unperformed check.
- Check this stage against active project locks and the production profile. Aesthetic judgment requires actual visual/audio review; technical gate success is necessary but not sufficient for release.

## Failure and repair
Re-encode or repair interchange mapping without replacing master; report unsupported target features. If the required implementation is absent, return the exact blocker and an executable plan; do not present guidance as a rendered result. Recheck the original acceptance condition after repair.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric; load once per production, not for every skill.
- [ffmpeg](https://ffmpeg.org/ffmpeg-filters.html)
- [otio](https://opentimelineio.readthedocs.io/en/latest/)
- [shotcraft](https://github.com/Vincentwei1021/video-shotcraft)

Original production guidance. External references are starting points, not copied instructions. Verify current APIs and licenses; do not execute unreviewed third-party code.
