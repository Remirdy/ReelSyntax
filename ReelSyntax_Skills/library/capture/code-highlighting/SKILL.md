---
name: code-highlighting
description: "Use for code highlighting. Tokenize code with language-aware syntax and animate relevant lines selectively."
metadata:
  category: capture
  stage: ingest
  status: guidance
  version: "2.0.0"
  aliases: "kod animasyonu,syntax highlight"
  requires: ""
---

# Code Highlighting

## Activation
Use for code highlighting when it is a concrete work item. Search aliases: kod animasyonu,syntax highlight. Do not activate for generic video language alone. Read the project brief and relevant hard locks before changing any asset.

## Inputs and output
- Inputs: Authorized source, viewport, demo steps and privacy constraints.
- Output: Capture manifest, frames or truthful demo storyboard.
- Required capability: No specific adapter is mandated; inspect the chosen implementation path.
- Evidence bundle: authorized source and capture manifest, frame references and action log.

## Production recipe
1. Locate shot/task IDs, approved assets, frame rate, duration and relevant constraints. Verify required capability; record assumptions and do not silently substitute missing resources.
2. Tokenize code with language-aware syntax and animate relevant lines selectively.
3. Parse language tokens with known lexer; use accessible contrast and stable code layout; ensure highlighted lines match actual source.
4. Record actual parameters in the editable source or project manifest; produce a representative preview or dry run before full execution. Apply only parameters relevant to the brief, not every technique in this skill.
5. Verify actual source state, viewport, fonts, privacy and content against captured frames.

## Acceptance criteria
- Code shown matches source and highlights track explanation.
- Record the concrete evidence path and frame/time range or measurement, plus target/tolerance and result (`pass`, `fail`, `review`, `blocked`, `not-applicable`). Never award a pass for an unperformed check.
- Check this stage against active project locks and the production profile. Aesthetic judgment requires actual visual/audio review; technical gate success is necessary but not sufficient for release.

## Failure and repair
Recapture from reproducible state or clearly label mock; never fabricate functionality or leak source data. If the required implementation is absent, return the exact blocker and an executable plan; do not present guidance as a rendered result. Recheck the original acceptance condition after repair.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric; load once per production, not for every skill.
- [playwright](https://playwright.dev/docs/screenshots)
- [hyperframes](https://github.com/heygen-com/hyperframes)
- [shotcraft](https://github.com/Vincentwei1021/video-shotcraft)

Original production guidance. External references are starting points, not copied instructions. Verify current APIs and licenses; do not execute unreviewed third-party code.
