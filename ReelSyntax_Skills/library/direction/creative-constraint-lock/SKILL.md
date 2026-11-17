---
name: creative-constraint-lock
description: "Use for creative constraint lock. Convert prohibitions and fixed properties into explicit locks before scene construction."
metadata:
  category: direction
  stage: plan
  status: production-guidance
  version: "2.0.0"
  aliases: "kısıtlar,kamera sabit,yazı olmasın"
  requires: ""
---

# Creative Constraint Lock

## Activation
Use for creative constraint lock when it is a concrete work item. Search aliases: kısıtlar,kamera sabit,yazı olmasın. Do not activate for generic video language alone. Read the project brief and relevant hard locks before changing any asset.

## Inputs and output
- Inputs: User brief, explicit constraints, available resources.
- Output: Approved decision record or production plan.
- Required capability: No specific adapter is mandated; inspect the chosen implementation path.
- Evidence bundle: brief, reference board and feasibility record.

## Production recipe
1. Locate shot/task IDs, approved assets, frame rate, duration and relevant constraints. Verify required capability; record assumptions and do not silently substitute missing resources.
2. Convert prohibitions and fixed properties into explicit locks before scene construction.
3. Record locks as machine-readable fields (camera matrix, text policy, immutable ROI, language, duration); validate before and after render.
4. Record actual parameters in the editable source or project manifest; produce a representative preview or dry run before full execution. Apply only parameters relevant to the brief, not every technique in this skill.
5. Compare the approved brief, storyboard and hero frames before committing production resources.

## Acceptance criteria
- Changes cannot silently override locked properties.
- Record the concrete evidence path and frame/time range or measurement, plus target/tolerance and result (`pass`, `fail`, `review`, `blocked`, `not-applicable`). Never award a pass for an unperformed check.
- Check this stage against active project locks and the production profile. Aesthetic judgment requires actual visual/audio review; technical gate success is necessary but not sufficient for release.

## Failure and repair
Return to the visual thesis; replace the conflicting motif or reduce scope rather than hiding the conflict with effects. If the required implementation is absent, return the exact blocker and an executable plan; do not present guidance as a rendered result. Recheck the original acceptance condition after repair.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric; load once per production, not for every skill.
- [cinecode](https://github.com/sarpstar/cinecode)
- [openmontage](https://github.com/OpenMontageInc/OpenMontage)
- [shotcraft](https://github.com/Vincentwei1021/video-shotcraft)

Original production guidance. External references are starting points, not copied instructions. Verify current APIs and licenses; do not execute unreviewed third-party code.
