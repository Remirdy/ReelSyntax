---
name: bassline-design
description: "Use for bassline design. Write bass movement in harmonic context and control sub-frequency energy."
metadata:
  category: music
  stage: build
  status: production-guidance
  version: "2.0.0"
  aliases: "bas çizgisi,bassline"
  requires: ""
---

# Bassline Design

## Activation
Use for bassline design when it is a concrete work item. Search aliases: bas çizgisi,bassline. Do not activate for generic video language alone. Read the project brief and relevant hard locks before changing any asset.

## Inputs and output
- Inputs: Approved cue brief, timeline, source rights and tempo.
- Output: Original score, MIDI, cue sheet or audio stems.
- Required capability: No specific adapter is mandated; inspect the chosen implementation path.
- Evidence bundle: original event/cue data, instrument provenance and stems.

## Production recipe
1. Locate shot/task IDs, approved assets, frame rate, duration and relevant constraints. Verify required capability; record assumptions and do not silently substitute missing resources.
2. Write bass movement in harmonic context and control sub-frequency energy.
3. Support harmonic roots and rhythmic intent; avoid masking speech or kick with sub frequencies; test on small speakers.
4. Record actual parameters in the editable source or project manifest; produce a representative preview or dry run before full execution. Apply only parameters relevant to the brief, not every technique in this skill.
5. Review phrase boundaries, melody originality, dialogue masking, dynamics and loop seam.

## Acceptance criteria
- Bass remains coherent with rhythm and chord roots.
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
