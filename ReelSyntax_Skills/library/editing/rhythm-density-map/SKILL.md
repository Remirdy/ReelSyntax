---
name: rhythm-density-map
description: "Chart shot-length and information-rate waves across timeline quarters so fast bursts alternate with comprehension holds."
metadata:
  category: editing
  stage: plan
  status: validated
  version: "2.0.0"
  aliases: "rhythm density map,pacing wave map,ritim yoğunluk haritası,kurgu tempo eğrisi,Rhythmusdichte-Karte,Tempowellen planen,mapa de ritmo,carte de densité rythmique"
  requires: ""
---

# Rhythm Density Map

## Activation
Activate during timeline planning or rough-cut review when scene durations feel mechanically uniform (every shot `3.0s` flat) or relentlessly rushed from start to finish. Search aliases: `rhythm density map`, `ritim yoğunluk haritası`, `Rhythmusdichte-Karte`. Do not activate for single-shot ambient loops.

## Decision rules
- **Ban metronomic uniformity**: in any video with `>= 4` scenes, standard deviation of scene durations must be `>= 12` frames (`0.40s` at `30/1` fps) unless locked to a strict musical bar grid (`music-visualizer` / `photo-slideshow`).
- **Burst-then-breathe pairing**: follow any rapid cluster of `2–3` dense cuts (`36–54` frames each) with one comprehension anchor (`75–120` frames) carrying lower word density (`<= 11` cps).
- **Quarter-timeline contour**:
  - `Q1 (0%–20%)`: brisk entry (`42–60f` hook)
  - `Q2 (20%–55%)`: grounded medium proof beats (`72–108f`)
  - `Q3 (55%–82%)`: accelerating climax/escalation (`42–66f`)
  - `Q4 (82%–100%)`: resolved wide hold (`72–105f`).

## Parameters and defaults
- `min_duration_stddev_frames`: `12` frames at `30/1` fps across `>= 4` non-grid scenes.
- `burst_shot_range_frames`: `36–54` frames (`1.2s–1.8s`).
- `anchor_shot_range_frames`: `75–120` frames (`2.5s–4.0s`).
- `max_consecutive_burst_shots`: `3` before a mandatory anchor hold.

## Procedure
1. Compute per-scene `duration_frames` and characters-per-second (`cps`) across the draft timeline, plotting `(scene_index, duration_frames, cps)`.
2. Flag flat plateaus (`3+` consecutive scenes within `+-4` frames of each other) and overload spikes (`duration < 48f` AND `cps > 16`).
3. Rebalance total frames (preserving exact project duration sum) by trimming `12–18` frames from transition/setup cards and donating them to proof/payoff anchor cards.
4. Verify no burst run exceeds `max_consecutive_burst_shots` without an anchor hold.
5. Confirm audio/music cue anchors re-snap cleanly to the adjusted integer cut boundaries.

## Failure modes and fixes
- **Five identical `90f` scenes in a `15s` reel**: reshape into `[48f, 96f, 66f, 132f, 108f]` (`sum = 450f`) so hook snaps, proof breathes, and payoff holds.
- **Fast cut paired with dense subheading (`42f` + `34` chars = `24.3` cps)**: either split copy across two beats or lengthen the proof beat to `72f` (`14.2` cps).
- **Ending cuts to black before viewer finishes reading final takeaway**: enforce `Q4` anchor hold `>= 72` frames (`2.4s`).

## Checklist
- [ ] Non-grid multi-scene timelines avoid flat identical scene durations (`stddev >= 12f`).
- [ ] Every `2–3` fast burst cuts are followed by a `>= 75f` comprehension hold.
- [ ] Fast burst shots carry light text load (`<= 4` words, `<= 14` cps).
- [ ] Quarter-4 closing beat holds long enough (`>= 72f`) for unhurried resolution.

## Worked examples
- **Example 1 (`20s` / `600f` 6-scene promo reshape, EN)**: Flat `[100, 100, 100, 100, 100, 100]` -> Sculpted wave `[48, 108, 54, 54, 126, 210? -> 114 + 96]`: `[48, 114, 54, 60, 132, 192?]` -> exact `[54, 114, 54, 60, 126, 92 + 100]` (`6` scenes `[54, 120, 54, 60, 132, 180?]` -> `[54, 120, 54, 66, 132, 174]` = `600f`): fast hook, grounded context, 2-beat escalation burst, deep proof anchor, clean payoff.
- **Example 2 (`15s` / `450f` explainer wave, TR)**: `[48f kanca, 114f kural, 54f örnek-A, 132f örnek-B çözüm, 102f kapanış]` = `450` kare, `stddev = 33.8` kare.

## Resources (load only if needed)
- [Timeline quarter tempo curves by genre](references/quarter-tempo-curves.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
