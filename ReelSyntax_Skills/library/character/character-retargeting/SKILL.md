---
name: character-retargeting
description: "Use for character retargeting. Map source and target skeleton with rest-pose correction and scale handling."
metadata:
  category: character
  stage: build
  status: production-guidance
  version: "2.0.0"
  aliases: "retarget,mixamo"
  requires: ""
---

# Character Retargeting

## Activation
Use for character retargeting when it is a concrete work item. Search aliases: retarget,mixamo. Do not activate for generic video language alone. Read the project brief and relevant hard locks before changing any asset.

## Inputs and output
- Inputs: Approved character ID, rig/model, shot intent and timing.
- Output: Pose, animation clip, rig or continuity record.
- Required capability: No specific adapter is mandated; inspect the chosen implementation path.
- Evidence bundle: identity/rig IDs, pose samples and contact trace.

## Production recipe
1. Locate shot/task IDs, approved assets, frame rate, duration and relevant constraints. Verify required capability; record assumptions and do not silently substitute missing resources.
2. Map source and target skeleton with rest-pose correction and scale handling.
3. Map joints, axes and scale between rigs; compare rest pose and root motion; fix foot sliding and extreme orientations.
4. Record actual parameters in the editable source or project manifest; produce a representative preview or dry run before full execution. Apply only parameters relevant to the brief, not every technique in this skill.
5. Review silhouette, contact, extreme pose and continuity frames at full speed and frame-by-frame.

## Acceptance criteria
- Test animation preserves foot placement and joint orientation.
- Record the concrete evidence path and frame/time range or measurement, plus target/tolerance and result (`pass`, `fail`, `review`, `blocked`, `not-applicable`). Never award a pass for an unperformed check.
- Check this stage against active project locks and the production profile. Aesthetic judgment requires actual visual/audio review; technical gate success is necessary but not sufficient for release.

## Failure and repair
Repair pose timing, joint weights or contact constraints; do not replace character identity to hide errors. If the required implementation is absent, return the exact blocker and an executable plan; do not present guidance as a rendered result. Recheck the original acceptance condition after repair.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric; load once per production, not for every skill.
- [threejs](https://threejs.org/docs/)
- [blender](https://docs.blender.org/api/current/)
- [cinema-skills](https://github.com/DenisHumen/cinema-skills)

Original production guidance. External references are starting points, not copied instructions. Verify current APIs and licenses; do not execute unreviewed third-party code.
