---
name: reelscript-authoring
description: "Use for reelscript authoring. Represent project scenes, assets, audio, constraints and timebase in versioned validated format."
metadata:
  category: workflow
  stage: operate
  status: guidance
  version: "2.0.0"
  aliases: "reelscript,video yaml"
  requires: ""
---

# Reelscript Authoring

## Activation
Use for reelscript authoring when it is a concrete work item. Search aliases: reelscript,video yaml. Do not activate for generic video language alone. Read the project brief and relevant hard locks before changing any asset.

## Inputs and output
- Inputs: Project manifest, approved state, assets and requested operations.
- Output: Versioned state, job plan or validated checkpoint.
- Required capability: No specific adapter is mandated; inspect the chosen implementation path.
- Evidence bundle: versioned project manifest, audit trail and stage artifacts.

## Production recipe
1. Locate shot/task IDs, approved assets, frame rate, duration and relevant constraints. Verify required capability; record assumptions and do not silently substitute missing resources.
2. Represent project scenes, assets, audio, constraints and timebase in versioned validated format.
3. Author versioned project with explicit FPS, dimensions, scenes, asset IDs, time ranges, locks and output profile; separate machine fields from creative notes.
4. Record actual parameters in the editable source or project manifest; produce a representative preview or dry run before full execution. Apply only parameters relevant to the brief, not every technique in this skill.
5. Validate state transitions, dependency invalidation, hard locks and recovery with a minimal fixture.

## Acceptance criteria
- Manifest validates against repository schema or reports missing schema.
- Record the concrete evidence path and frame/time range or measurement, plus target/tolerance and result (`pass`, `fail`, `review`, `blocked`, `not-applicable`). Never award a pass for an unperformed check.
- Check this stage against active project locks and the production profile. Aesthetic judgment requires actual visual/audio review; technical gate success is necessary but not sufficient for release.

## Failure and repair
Rollback to last verified checkpoint and reroute affected work; preserve approved assets and evidence. If the required implementation is absent, return the exact blocker and an executable plan; do not present guidance as a rendered result. Recheck the original acceptance condition after repair.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric; load once per production, not for every skill.
- [openmontage](https://github.com/OpenMontageInc/OpenMontage)
- [hypit](https://github.com/hypit-ai/hypit)
- [cinecode](https://github.com/sarpstar/cinecode)

Original production guidance. External references are starting points, not copied instructions. Verify current APIs and licenses; do not execute unreviewed third-party code.
