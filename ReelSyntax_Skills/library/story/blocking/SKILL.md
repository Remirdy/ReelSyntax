---
name: blocking
description: "Use for blocking. Plot positions, eyelines and movement paths in a top-down diagram or coordinates."
metadata:
  category: story
  stage: plan
  status: guidance
  version: "2.0.0"
  aliases: "sahne konumlama,oyuncu yerleşimi"
  requires: ""
---

# Blocking

## Activation
Use for blocking when it is a concrete work item. Search aliases: sahne konumlama,oyuncu yerleşimi. Do not activate for generic video language alone. Read the project brief and relevant hard locks before changing any asset.

## Inputs and output
- Inputs: Brief, scene IDs, duration, approved sources where applicable.
- Output: Timecoded script, shot plan or continuity artifact.
- Required capability: No specific adapter is mandated; inspect the chosen implementation path.
- Evidence bundle: timecoded beats, shot ledger and animatic.

## Production recipe
1. Locate shot/task IDs, approved assets, frame rate, duration and relevant constraints. Verify required capability; record assumptions and do not silently substitute missing resources.
2. Plot positions, eyelines and movement paths in a top-down diagram or coordinates.
3. Use floor plan with camera axis and eyeline vectors; test contact poses and entrances; preserve screen direction except intentional axis reset.
4. Record actual parameters in the editable source or project manifest; produce a representative preview or dry run before full execution. Apply only parameters relevant to the brief, not every technique in this skill.
5. Review causal order, readability and playback timing with and without audio.

## Acceptance criteria
- Characters do not teleport or break intended geography.
- Record the concrete evidence path and frame/time range or measurement, plus target/tolerance and result (`pass`, `fail`, `review`, `blocked`, `not-applicable`). Never award a pass for an unperformed check.
- Check this stage against active project locks and the production profile. Aesthetic judgment requires actual visual/audio review; technical gate success is necessary but not sufficient for release.

## Failure and repair
Reallocate frames, cut redundant beats or repair coverage; preserve approved facts and ending. If the required implementation is absent, return the exact blocker and an executable plan; do not present guidance as a rendered result. Recheck the original acceptance condition after repair.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric; load once per production, not for every skill.
- [cinecode](https://github.com/sarpstar/cinecode)
- [openmontage](https://github.com/OpenMontageInc/OpenMontage)
- [cinema-skills](https://github.com/DenisHumen/cinema-skills)

Original production guidance. External references are starting points, not copied instructions. Verify current APIs and licenses; do not execute unreviewed third-party code.
