---
name: leitmotif-continuity
description: "Use for leitmotif continuity. Reuse an original motif with variations in orchestration and tempo by character or theme."
metadata:
  category: music
  stage: build
  status: guidance
  version: "2.0.0"
  aliases: "leitmotif,karakter teması"
  requires: ""
---

# Leitmotif Continuity

## Activation
Use for leitmotif continuity when it is a concrete work item. Search aliases: leitmotif,karakter teması. Do not activate for generic video language alone. Read the project brief and relevant hard locks before changing any asset.

## Inputs and output
- Inputs: Approved cue brief, timeline, source rights and tempo.
- Output: Original score, MIDI, cue sheet or audio stems.
- Required capability: No specific adapter is mandated; inspect the chosen implementation path.
- Evidence bundle: original event/cue data, instrument provenance and stems.

## Production recipe
1. Locate shot/task IDs, approved assets, frame rate, duration and relevant constraints. Verify required capability; record assumptions and do not silently substitute missing resources.
2. Reuse an original motif with variations in orchestration and tempo by character or theme.
3. Retain motif identity by contour/rhythm while changing harmony or orchestration; track usage by episode and avoid repetition fatigue.
4. Record actual parameters in the editable source or project manifest; produce a representative preview or dry run before full execution. Apply only parameters relevant to the brief, not every technique in this skill.
5. Review phrase boundaries, melody originality, dialogue masking, dynamics and loop seam.

## Acceptance criteria
- Motif identity survives while scene emotion changes.
- Record the concrete evidence path and frame/time range or measurement, plus target/tolerance and result (`pass`, `fail`, `review`, `blocked`, `not-applicable`). Never award a pass for an unperformed check.
- Check this stage against active project locks and the production profile. Aesthetic judgment requires actual visual/audio review; technical gate success is necessary but not sufficient for release.

## Failure and repair
Change orchestration, timing or harmony; preserve licensed/source constraints and avoid copied motifs. If the required implementation is absent, return the exact blocker and an executable plan; do not present guidance as a rendered result. Recheck the original acceptance condition after repair.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric; load once per production, not for every skill.
- [web-audio](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)
- [ffmpeg](https://ffmpeg.org/ffmpeg-filters.html)
- [cinecode](https://github.com/sarpstar/cinecode)

Original production guidance. External references are starting points, not copied instructions. Verify current APIs and licenses; do not execute unreviewed third-party code.
