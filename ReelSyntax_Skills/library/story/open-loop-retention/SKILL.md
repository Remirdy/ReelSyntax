---
name: open-loop-retention
description: "Plant a concrete unanswered question in the opening beat, advance partial evidence across middle beats, and close the loop cleanly before the final hold."
metadata:
  category: story
  stage: plan
  status: validated
  version: "2.0.0"
  aliases: "open loop,open loop retention,açık döngü kurgusu,merak boşluğu,Offene Schleife,Spannungsbogen halten,bucle abierto,boucle ouverte"
  requires: ""
---

# Open Loop Retention

## Activation
Activate when structuring short-form narrative, explainer, or reveal scripts to prevent mid-video viewer drop-off through controlled information gaps. Search aliases: `open loop`, `açık döngü kurgusu`, `Offene Schleife`. Do not activate for ambient loops or non-narrative visualizers.

## Decision rules
- **If runtime is `< 20s`**: open exactly `1` primary loop in beat 1 (`<= 2.0s`) and close it at `75%–88%` of total runtime; never stack nested loops in sub-20s pieces.
- **If runtime is `20s–60s`**: allow `1` primary loop (`0% -> 85%`) plus `1` micro-loop (`25% -> 60%`) that bridges the midpoint sag.
- **If an open loop is planted**: every intermediate beat must deliver a tangible narrowing clue (eliminated hypothesis, partial measurement, or visible assembly stage) rather than stalling with filler phrases ("wait till the end").
- **Unclosed loop ban**: `open_loops_remaining_at_end == 0` unless an explicit multi-part series tag is declared in the brief.

## Parameters and defaults
- `plant_deadline_sec`: `2.0` seconds from frame 0.
- `clue_cadence_sec`: `3.5–5.0` seconds maximum gap between concrete progress clues.
- `closure_window_pct`: `0.78–0.90` of total timeline duration, leaving `10%–22%` for synthesis or action card.
- `max_concurrent_loops`: `1` (`< 20s`) or `2` (`20s–60s`).

## Procedure
1. Formulate the opening gap as an observable anomaly, concrete bet, or missing variable shown visually in beat 1 (avoid vague rhetorical questions).
2. Map each middle beat to a specific state progression (`clue_1 -> clue_2 -> threshold_turn`) so viewer certainty rises monotonically without giving away the final value early.
3. Place a midpoint re-tension beat at `45%–55%` duration when runtime exceeds `20s` (for example, showing why the obvious guess fails).
4. Deliver the exact answer or visual reveal inside `closure_window_pct` using the clearest shot in the sequence.
5. Audit the script ledger to verify every planted question has a matching timestamped resolution beat.

## Failure modes and fixes
- **Stalling filler ("watch until the end" with zero progress)**: delete meta-pleas and replace with an immediateeliminated option or live measurement step.
- **Premature closure at 35% runtime**: move the answer beat to `80%` runtime and reorder the middle beats from symptom -> failed naive fix -> root mechanism -> answer.
- **Bait-and-switch payoff**: ensure the frame-0 visual promise matches the exact artifact revealed at closure.

## Checklist
- [ ] Opening gap is planted visually and verbally within `plant_deadline_sec`.
- [ ] Every middle beat advances measurable progress toward closure (zero stall lines).
- [ ] Primary loop closes inside `78%–90%` of total duration.
- [ ] Zero unanswered promises remain at the final frame.

## Worked examples
- **Example 1 (`18s` / `540f` benchmark reel, EN)**: `0–48f` plant: two identical exports, one `42 MB` and one `6.8 MB` at indistinguishable sharpness — which flag changed? `48–210f` clue 1: resolution and frame rate are identical (`1080p30`). `210–390f` clue 2: constant-rate-factor sweep vs audio stream copy. `390–468f` closure (`80%`): `-pix_fmt yuv420p -crf 20 -preset slow` vs uncompressed audio WAV. `468–540f` takeaway card.
- **Example 2 (`24s` / `720f` design critique, TR)**: `0–54f` plant: iki afişte aynı font var ama sağdaki neden anında okunuyor? `54–300f` clue 1: harf boyutu aynı (`64px`). `300–540f` clue 2: satır aralığı değil, arka plan parlaklık tabanı. `540–630f` closure: `7.2:1` kontrast ve `%12` kenar boşluğu. `630–720f` özet.

## Resources (load only if needed)
- [Loop closure ledger and midpoint patterns](references/loop-closure-patterns.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
