---
name: algorithm-visualization
description: "Use for algorithm visualization. Animate recorded algorithm states and distinguish comparisons, swaps and final values."
metadata:
  category: data
  stage: build
  status: guidance
  version: "2.0.0"
  aliases: "algoritma animasyonu,sorting"
  requires: ""
---

# Algorithm Visualization

## Activation
Use for algorithm visualization when it is a concrete work item. Search aliases: algoritma animasyonu,sorting. Do not activate for generic video language alone. Read the project brief and relevant hard locks before changing any asset.

## Inputs and output
- Inputs: Verified dataset, units, domain assumptions and learning objective.
- Output: Animated visualization source and data mapping.
- Required capability: No specific adapter is mandated; inspect the chosen implementation path.
- Evidence bundle: source values/units, mapping and reproducible scene.

## Production recipe
1. Locate shot/task IDs, approved assets, frame rate, duration and relevant constraints. Verify required capability; record assumptions and do not silently substitute missing resources.
2. Animate recorded algorithm states and distinguish comparisons, swaps and final values.
3. Map each animation beat to executable algorithm state and invariants; show actual step values and verify against reference implementation.
4. Record actual parameters in the editable source or project manifest; produce a representative preview or dry run before full execution. Apply only parameters relevant to the brief, not every technique in this skill.
5. Cross-check computations and labels against source; inspect axis, geometry and claims at key frames.

## Acceptance criteria
- State trace matches actual algorithm execution.
- Record the concrete evidence path and frame/time range or measurement, plus target/tolerance and result (`pass`, `fail`, `review`, `blocked`, `not-applicable`). Never award a pass for an unperformed check.
- Check this stage against active project locks and the production profile. Aesthetic judgment requires actual visual/audio review; technical gate success is necessary but not sufficient for release.

## Failure and repair
Fix source transformation, visual encoding or explanation before styling; mark uncertainty. If the required implementation is absent, return the exact blocker and an executable plan; do not present guidance as a rendered result. Recheck the original acceptance condition after repair.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric; load once per production, not for every skill.
- [manim](https://docs.manim.community/en/stable/)
- [threejs](https://threejs.org/docs/)
- [wcag](https://www.w3.org/TR/WCAG22/)

Original production guidance. External references are starting points, not copied instructions. Verify current APIs and licenses; do not execute unreviewed third-party code.
