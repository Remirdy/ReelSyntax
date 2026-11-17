---
name: rtl-text-layout
description: "Use for rtl text layout. Use proper bidirectional shaping and isolate mixed-direction tokens."
metadata:
  category: typography
  stage: build
  status: production-guidance
  version: "2.0.0"
  aliases: "arapça,sağdan sola,rtl"
  requires: ""
---

# Rtl Text Layout

## Activation
Use for rtl text layout when it is a concrete work item. Search aliases: arapça,sağdan sola,rtl. Do not activate for generic video language alone. Read the project brief and relevant hard locks before changing any asset.

## Inputs and output
- Inputs: Exact approved copy, language, fonts, timing and safe regions.
- Output: Text layout, caption cues or animated type source.
- Required capability: No specific adapter is mandated; inspect the chosen implementation path.
- Evidence bundle: font and layout manifest, exact text, sampled bounding boxes.

## Production recipe
1. Locate shot/task IDs, approved assets, frame rate, duration and relevant constraints. Verify required capability; record assumptions and do not silently substitute missing resources.
2. Use proper bidirectional shaping and isolate mixed-direction tokens.
3. Apply bidi algorithm and shaping with correct direction; do not reverse raw strings; inspect numerals, punctuation and mixed scripts.
4. Record actual parameters in the editable source or project manifest; produce a representative preview or dry run before full execution. Apply only parameters relevant to the brief, not every technique in this skill.
5. Compare expected glyphs and content against actual output; inspect smallest delivery and longest locale.

## Acceptance criteria
- RTL sample lines display in correct reading order.
- Record the concrete evidence path and frame/time range or measurement, plus target/tolerance and result (`pass`, `fail`, `review`, `blocked`, `not-applicable`). Never award a pass for an unperformed check.
- Check this stage against active project locks and the production profile. Aesthetic judgment requires actual visual/audio review; technical gate success is necessary but not sufficient for release.

## Failure and repair
Remeasure shaping, wrap or re-anchor text before shrinking; do not add or alter copy without permission. If the required implementation is absent, return the exact blocker and an executable plan; do not present guidance as a rendered result. Recheck the original acceptance condition after repair.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric; load once per production, not for every skill.
- [hyperframes](https://github.com/heygen-com/hyperframes)
- [remotion-skills](https://github.com/remotion-dev/skills)
- [wcag](https://www.w3.org/TR/WCAG22/)

Original production guidance. External references are starting points, not copied instructions. Verify current APIs and licenses; do not execute unreviewed third-party code.
