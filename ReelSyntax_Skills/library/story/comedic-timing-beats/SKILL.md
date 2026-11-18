---
name: comedic-timing-beats
description: "Time setup-subversion beats using rule-of-three escalation, pre-punchline micro-holds, hard cuts on plosive transients, and clipped reaction tails."
metadata:
  category: story
  stage: edit
  status: validated
  version: "2.0.0"
  aliases: "comedic timing,comedy beats,komedi zamanlaması,espri ritmi,Pointen-Timing,Komik-Rhythmus,ritmo cómico,rythme comique"
  requires: ""
---

# Comedic Timing Beats

## Activation
Activate when editing humorous short-form sketches, deadpan explainers, or ironic contrast cuts where frame-level pause and cut placement determine whether a beat lands. Search aliases: `comedic timing`, `komedi zamanlaması`, `Pointen-Timing`. Do not activate for solemn documentary, memorial, or safety-critical messaging.

## Decision rules
- **Rule-of-three baseline**: establish pattern across beat 1 (`T` frames) and beat 2 (`0.85T–1.0T` frames) before subverting on beat 3; never add a fourth setup beat.
- **If the punchline is visual contradiction**: cut hard (`0`-frame transition, zero cross-dissolve) exactly on the final stressed syllable or `4–8` frames after a deadpan pause.
- **If music bed is playing under setup**: drop music gain to `-inf` (hard mute, not slow fade) `6–12` frames before the subversion line, then resume `10–18` frames after the reaction beat.
- **Trim reaction tail**: cut away from the punchline `8–16` frames after peak visual read (`smash-cut exit`) instead of letting the joke linger into awkward decay unless awkwardness is the explicit gag (`>= 45` frames locked stare with declared `freeze` exception).

## Parameters and defaults
- `pre_punch_hold_frames`: `8` frames at `30/1` fps (range `6–14` frames; `0.20s–0.47s`).
- `music_drop_lead_frames`: `9` frames (`0.30s` at `30/1`) hard cut to silence.
- `smash_exit_tail_frames`: `12` frames (`0.40s` at `30/1`) after final punch word or visual reveal.
- `dissolve_allowed_on_punch`: `false` (always `transition.type = "cut"`).

## Procedure
1. Mark the exact frame index of setup 1, setup 2, and the subversion trigger on the rational project frame clock.
2. Tighten setup 2 to `85%–95%` of setup 1's duration so rhythmic momentum accelerates into the turn.
3. Insert `pre_punch_hold_frames` of locked frame and room-tone/silent breath immediately before the subversion cut; register any intentional hold `>= 18` frames in `quality.exceptions.freeze` / `silence`.
4. Execute a `0`-frame hard cut (and optional `camera_scale` jump `>= 1.35x`) on the punchline transient; strip trailing filler words ("so yeah", "basically") after the key noun.
5. Play back at `1.0x` real time across the `3`-second window around the turn and adjust cut point in `2`-frame increments until visual and spoken transients align.

## Failure modes and fixes
- **Cross-dissolve softens the contradiction**: replace dissolve or wipe with an instant `0`-frame hard cut.
- **Punchline word buried in mid-sentence**: rewrite copy so the surprising word is the final word of the clause right before the cut.
- **QC flags intentional deadpan silence/freeze**: declare exact frame bounds `[start_frame, end_frame]` in `reel.json` `quality.exceptions`.

## Checklist
- [ ] Setup beats establish a clear 2-step rhythm before beat-3 subversion.
- [ ] Punchline lands on the final word or frame-0 visual of a `0`-frame hard cut.
- [ ] Pre-punch pause (`6–14` frames) and music mute (`6–12` frames lead) are frame-quantized.
- [ ] Intentional deadpan holds/silences are declared in `quality.exceptions`.

## Worked examples
- **Example 1 (`30/1` fps ironic tutorial cut, EN)**: `0–54f` Beat 1: `"Step 1: Label every layer cleanly."` `54–102f` Beat 2 (`48f`, tighter): `"Step 2: Group precomps by scene."` `102–110f` (`8f` silent hold, music hard-mutes at `96f`). `110–152f` Beat 3 (`0f` hard cut, `1.4x` zoom): `"final_v9_REAL_fixed2.json"`. Cut out at `152f` (`12f` after reveal).
- **Example 2 (`30/1` fps deadpan expectation flip, DE)**: `0–60f` `"Unser Render-Cluster: null Lärm."` `60–69f` (`9f` Stille-Pause). `69–114f` harter Schnitt auf Statuskarte `"WEIL STROMAUSFALL"` mit deklarierter `silence`-Ausnahme `[60, 69]`.

## Resources (load only if needed)
- [Comedic cut and hold frame-offset recipes](references/frame-offset-recipes.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
