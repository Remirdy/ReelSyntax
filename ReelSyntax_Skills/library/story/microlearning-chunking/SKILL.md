---
name: microlearning-chunking
description: "Structure educational shorts under strict cognitive-load ceilings using concept-anchor, worked visual proof, and active micro-recall beats."
metadata:
  category: story
  stage: plan
  status: validated
  version: "2.0.0"
  aliases: "microlearning,microlearning chunking,mikro öğrenme,kavram parçalama,Mikrolernen,Lernhäppchen strukturieren,microaprendizaje,micro-apprentissage"
  requires: ""
---

# Microlearning Chunking

## Activation
Activate when planning instructional, technical, language-learning, or science shorts (`15s–90s`) aimed at durable viewer comprehension rather than passive entertainment. Search aliases: `microlearning`, `mikro öğrenme`, `Mikrolernen`. Do not activate for pure product teasers or mood montages.

## Decision rules
- **New-term ceiling**: introduce at most `2` unfamiliar domain terms in `<= 30s` (`<= 4` in `60s`), defining each visually on the same frame it is spoken.
- **Dual-channel split (anti-redundancy rule)**: never print a `20`-word prose definition on screen while speaking a different sentence; pair `2–4` keyword labels + spatial diagram on screen with spoken causal explanation.
- **Mandatory 4-beat instructional arc**:
  1. `misconception_or_goal` (`15%` duration)
  2. `core_rule` (`25%` duration)
  3. `worked_instance` (`40%` duration)
  4. `micro_recall_prompt` (`20%` duration — viewer predicts or spots the rule in a fresh 3-second case).
- **If a procedure has `> 4` sequential steps**: group into `2–3` named macro-phases (`Prepare -> Execute -> Verify`) instead of listing `7` ungrouped bullets.

## Parameters and defaults
- `max_new_terms_per_30s`: `2` terms.
- `max_simultaneous_callouts`: `3` visual labels on any single frame.
- `worked_example_share`: `0.35–0.45` of total video duration.
- `recall_pause_frames`: `36–48` frames (`1.2s–1.6s` at `30/1`) between posing the micro-check and highlighting the answer badge.

## Procedure
1. Write the single measurable learning objective as an observable viewer action ("identify whether a rational fps needs drop-frame timecode").
2. Audit script vocabulary against target learner prior; strip or replace incidental jargon above `max_new_terms_per_30s`.
3. Design the `worked_instance` beat with real numbers/inputs changing state step-by-step, keeping `<= 3` visual callouts visible simultaneously.
4. Add a `micro_recall_prompt` beat near the end presenting a compact new input, holding `recall_pause_frames`, and highlighting the correct element visually.
5. Verify reading speed (`<= 15` cps recommended for instructional copy, stricter than entertainment's `17–20` cps).

## Failure modes and fixes
- **Definition dump with zero worked instance**: cut half the abstract explanation and show one concrete numeric or visual transformation (`input -> rule -> output`).
- **Split-attention overload (diagram + dense paragraph + fast speech)**: reduce on-screen text to node labels (`<= 3` words each) positioned directly beside the diagram parts.
- **Passive summary ending ("today we learned X")**: replace summary card with a `3`-second spot-the-fix micro-quiz and visual highlight reveal.

## Checklist
- [ ] Learning objective is one concrete skill, not a multi-chapter survey.
- [ ] Unfamiliar domain terms stay `<= 2` per `30s` and appear visually when defined.
- [ ] At least `35%` of total frames show a concrete worked example.
- [ ] Final segment includes an active micro-recall check with `1.2s–1.6s` think hold.

## Worked examples
- **Example 1 (`30s` / `900f` color contrast lesson, EN)**: `0–120f` Goal: why gray-on-dark UI captions fail mobile readability. `120–330f` Core rule: luminance contrast `>= 4.5:1` for normal copy (`#94A3B8` on `#0F172A` = `6.4:1` pass vs `#475569` = `2.3:1` fail). `330–690f` Worked instance: live swatch step from `#475569` -> `#CBD5E1` (`11.2:1`). `690–900f` Recall check: two badges shown for `42f`, green border lights up the passing pair.
- **Example 2 (`24s` / `720f` Turkish grammar/typography tip, TR)**: `0–108f` Hedef: büyük harfte `İ` ve `I` dönüşümü. `108–270f` Kural: Türkçe yerel ayarında `i -> İ`, `ı -> I`. `270–570f` Örnek: `"ışık ve iz"` -> `"IŞIK VE İZ"` (yanlış `"ISIK VE IZ"` üstü çizili). `570–720f` Mini test (`36f` bekleme + doğru kutu vurgusu).

## Resources (load only if needed)
- [Instructional cognitive-load budget and beat templates](references/cognitive-load-budget.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
