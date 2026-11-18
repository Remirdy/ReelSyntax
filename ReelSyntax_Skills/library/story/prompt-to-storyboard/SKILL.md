---
name: prompt-to-storyboard
description: "Convert a short natural-language brief into frame-quantized scene cards with visual action, on-screen copy, audio cue, and recipe assignment."
metadata:
  category: story
  stage: plan
  status: validated
  version: "2.0.0"
  aliases: "prompt to storyboard,brief to scenes,istemden öykü panosuna,metinden sahne planına,Kurztext zu Storyboard,Entwurf zu Szenenplan,texto a guion gráfico,brief vers scénarimage"
  requires: ""
---

# Prompt To Storyboard

## Activation
Activate when decomposing a single-paragraph user brief into discrete, frame-accurate scene cards ready for timeline compilation. Search aliases: `prompt to storyboard`, `istemden öykü panosuna`, `Kurztext zu Storyboard`. Do not activate when scenes and durations are already itemized in a validated project plan.

## Decision rules
- **If target duration is `D` seconds at rational rate `F` fps**: allocate integer `duration_frames` per scene so `sum(duration_frames) == round(D * F)` with zero fractional remainder.
- **If the brief has no explicit beat count**: partition into `clamp(round(D / 3.8), 3, 12)` scenes (`4–5` scenes for `15s–20s`, `6–8` scenes for `25s–35s`).
- **If two consecutive cards share the same visual recipe and camera framing**: either merge them into one card with progressive reveal or differentiate shot scale/recipe to prevent jump-cut monotony.
- **If spoken narration is enabled**: derive scene frame budgets from estimated spoken syllable duration plus `8–12` padding frames before locking visual transitions.

## Parameters and defaults
- `fps`: `"30/1"` rational clock (adjustable default; verify project target rate such as `"24/1"` or `"60/1"`).
- `hook_ceiling_frames`: `54` frames (`1.8s` at `30/1`) for social vertical formats; `75` frames (`2.5s`) for widescreen explainers.
- `min_scene_frames`: `36` frames (`1.2s` at `30/1`) so visual layout settles before cutting.
- `heading_char_budget`: `22` characters for `9:16` vertical cards; `38` characters for `16:9` widescreen cards.

## Procedure
1. Parse the brief into four structural slots: `hook`, `context/problem`, `proof/steps` (`1..N` beats), and `payoff/call-to-action`.
2. Assign each beat an integer `duration_frames` aligned to `fps`, enforcing `hook_ceiling_frames` on beat 1 and `min_scene_frames` on all beats.
3. Populate non-overlapping `heading`, `subheading`, and `kicker` fields per card: `heading` carries the visual anchor noun, `subheading` carries the qualifier, and narration avoids verbatim reading of `kicker` badges.
4. Map each beat to a deterministic visual recipe (`kinetic-type`, `prism-monolith`, `layer-stack`, `signal-grid`, or format-specific scene template) and explicit camera preset.
5. Reconcile total frame sum, transition overlap frames, and reading-speed characters-per-second (`<= 17` cps default) before emitting the scene array.

## Failure modes and fixes
- **Wall-of-text brief copied straight into `heading`**: extract a `2–4` word punch noun phrase for `heading` and move explanatory clauses to narration or `subheading`.
- **Duration rounding drift (`898` frames instead of `900`)**: absorb residual `+-1..4` frames into the final payoff hold scene.
- **Repetitive recipe fatigue**: cap identical consecutive recipe runs at `2` scenes unless differentiated by palette inversion or camera scale step.

## Checklist
- [ ] Sum of scene `duration_frames` equals exact rational target frame count.
- [ ] Scene 1 finishes at or below `hook_ceiling_frames`.
- [ ] Every card specifies visual recipe, camera preset, copy fields, and cue anchor.
- [ ] On-screen copy stays within `heading_char_budget` and `<= 17` cps reading pace.

## Worked examples
- **Example 1 (`15s` vertical brief at `30/1` = `450` frames, EN)**: Brief `"Show 3 keyboard habits that save an hour a day"` -> `s01_hook` (`54f`, `prism-monolith`, heading `"1 HOUR BACK"`), `s02_step1` (`114f`, `kinetic-type`, `"JUMP BY WORD"`), `s03_step2` (`114f`, `signal-grid`, `"SPLIT PANES"`), `s04_step3` (`108f`, `kinetic-type`, `"HISTORY SEARCH"`), `s05_payoff` (`60f`, `prism-monolith`, `"PICK ONE TODAY"`). Sum = `450` frames.
- **Example 2 (`12s` widescreen brief at `24/1` = `288` frames, DE)**: Brief `"Warum dunkle Hintergründe im Schnitt absaufen"` -> `s01_hook` (`48f`, `"SCHWARZ SÄUFT AB"`), `s02_proof` (`144f`, luminance floor `Y=16..44` diagram), `s03_payoff` (`96f`, `"BODEN AUF Y44 HEBEN"`). Sum = `288` frames.

## Resources (load only if needed)
- [Scene card frame allocation table](references/scene-card-allocation.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
