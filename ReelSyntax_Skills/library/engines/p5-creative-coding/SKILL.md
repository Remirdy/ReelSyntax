---
name: p5-creative-coding
description: "Use for p5 creative coding. Use seeded random and explicit frame state for reproducible generative drawing."
metadata:
  category: engines
  stage: build
  status: guidance
  version: "2.0.0"
  aliases: "p5.js,p5js"
  requires: "p5"
---

# P5 Creative Coding

## Activation
Use for p5 creative coding when it is a concrete work item. Search aliases: p5.js,p5js. Do not activate for generic video language alone. Read the project brief and relevant hard locks before changing any asset.

## Inputs and output
- Inputs: Installed engine/version, scene contract and capabilities.
- Output: Engine-specific source, fixture render or explicit unavailable report.
- Required capability: p5
- Evidence bundle: versioned adapter command, fixture source, logs and artifact.

## Production recipe
1. Locate shot/task IDs, approved assets, frame rate, duration and relevant constraints. Verify required capability; record assumptions and do not silently substitute missing resources.
2. Use seeded random and explicit frame state for reproducible generative drawing.
3. Seed random/noise, isolate setup and draw from frame index; set pixel density and export exact frame count; avoid real-time frame drift.
4. Record actual parameters in the editable source or project manifest; produce a representative preview or dry run before full execution. Apply only parameters relevant to the brief, not every technique in this skill.
5. Probe actual installed capabilities and decode representative output; verify deterministic frame/stage behavior.

## Acceptance criteria
- Same seed and frame produce identical output in fixture.
- Record the concrete evidence path and frame/time range or measurement, plus target/tolerance and result (`pass`, `fail`, `review`, `blocked`, `not-applicable`). Never award a pass for an unperformed check.
- Check this stage against active project locks and the production profile. Aesthetic judgment requires actual visual/audio review; technical gate success is necessary but not sufficient for release.

## Failure and repair
Isolate adapter failure, correct version/API mismatch or use approved fallback; report unavailable engines. If the required implementation is absent, return the exact blocker and an executable plan; do not present guidance as a rendered result. Recheck the original acceptance condition after repair.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric; load once per production, not for every skill.
- [ffmpeg](https://ffmpeg.org/ffmpeg-filters.html)
- [threejs](https://threejs.org/docs/)
- [blender](https://docs.blender.org/api/current/)

Original production guidance. External references are starting points, not copied instructions. Verify current APIs and licenses; do not execute unreviewed third-party code.
