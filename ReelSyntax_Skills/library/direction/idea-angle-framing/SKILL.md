---
name: idea-angle-framing
description: "Narrow a broad topic into one sharp editorial angle, concrete viewer tension, and bounded thesis before storyboarding."
metadata:
  category: direction
  stage: plan
  status: validated
  version: "2.0.0"
  aliases: "idea angle,editorial angle,konu açısı,fikir çerçeveleme,Themenwinkel,Blickwinkel bestimmen,ángulo editorial,angle éditorial,ângulo editorial"
  requires: ""
---

# Idea Angle Framing

## Activation
Activate when turning a broad topic, product note, or educational subject into a focused short-form premise before writing scenes. Search aliases: `idea angle`, `konu açısı`, `Themenwinkel`. Do not activate when a locked word-for-word script is already supplied.

## Decision rules
- **If the brief names a broad subject without a conflict** (for example, "explain frame rates"): reframe around one measurable failure or trade-off ("why 24 fps pans judder on 60 Hz displays") rather than surveying the whole topic.
- **If the target runtime is `<= 30s`**: enforce `thesis_count = 1`, `supporting_proofs <= 2`, and `excluded_subtopics >= 2`.
- **If the target runtime is `31s–90s`**: allow `supporting_proofs <= 3` plus one counter-example beat.
- **If two candidate angles compete**: score each on `specificity (0–3) + visualizability (0–3) + stake_clarity (0–3)` and discard any angle scoring `< 6` or lacking a concrete visual proof.

## Parameters and defaults
- `thesis_word_ceiling`: `18` words (adjustable default: `14–22` depending on language morphology).
- `tension_type`: `mistake-correction` | `counter-intuitive-metric` | `before-after-delta` | `constraint-challenge` (default: `mistake-correction`).
- `audience_prior`: `novice` | `practitioner` | `specialist` (default: `practitioner`; controls jargon budget `<= 2` undefined terms for `novice`).
- `visual_anchor_required`: `true` (every angle must name at least one observable screen state, object, or chart).

## Procedure
1. Extract the raw subject noun, intended viewer level, and hard duration ceiling from the brief.
2. List three distinct candidate angles using different `tension_type` framings; reject encyclopedia-style overview framings ("everything about X").
3. Write a one-sentence thesis inside `thesis_word_ceiling` words that states both the claim and the consequence of ignoring it.
4. Define an explicit scope fence listing at least two adjacent subtopics that will be omitted so middle beats never drift.
5. Bind the chosen angle to a primary visual proof (comparison split, live metric, diagram state change, or physical action) and hand off to scene breakdown.

## Failure modes and fixes
- **Encyclopedia drift (trying to cover five points in 25 seconds)**: cut all secondary branches into separate follow-up briefs and keep only the highest-contrast proof.
- **Abstract thesis with no visualizable noun**: replace abstract verbs ("improve workflow") with an observable delta ("cut render retries from four passes to one").
- **Clickbait tension that the payoff cannot prove**: downgrade the claim to the exact measured range present in project sources.

## Checklist
- [ ] Single-sentence thesis fits within `thesis_word_ceiling` words.
- [ ] Viewer stake or tension is explicit in beat 1 without exaggeration.
- [ ] At least two adjacent subtopics are explicitly excluded from scope.
- [ ] Chosen angle names a concrete visual proof for the middle beat.

## Worked examples
- **Example 1 (24s technical explainer, EN)**: Raw topic `"video caching"` -> Angle (`counter-intuitive-metric`): `"Scene-level content hashing skips 80% of frame redraws during copy edits."` Excluded: network CDN caching, codec GOP internals. Visual proof: 4-scene timeline where only scene 2 redraws after a title edit.
- **Example 2 (20s culinary tip, TR)**: Raw topic `"kahve demleme"` -> Angle (`mistake-correction`): `"Kaynar su dökmek çekirdeği yakar; 93°C su tatlılığı korur."` Excluded: kavurma profilleri, değirmen tarihi. Visual proof: side-by-side extraction color and temperature badge at `93°C` vs `100°C`.

## Resources (load only if needed)
- [Angle selection matrix and scoring rubric](references/angle-matrix.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
