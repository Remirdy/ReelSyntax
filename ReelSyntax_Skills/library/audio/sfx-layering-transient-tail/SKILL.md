---
name: sfx-layering-transient-tail
description: "Synthesize or layer clean UI, transition, and impact sound effects across non-overlapping sub-body, mid-transient, and airy-tail bands locked to exact frame onsets."
metadata:
  category: audio
  stage: build
  status: validated
  version: "2.0.0"
  aliases: "sfx transient tail layering,layered sound effects,katmanlı ses efekti tasarımı,atak gövde kuyruk katmanlama,SFX-Schichtung Attack und Tail,Klangschichten für Übergänge,capas de efectos de sonido,superposition d'effets sonores"
  requires: ""
---

# SFX Layering Transient Tail

## Activation
Activate when crafting motion-design accents, hook impacts, wipe whooshes, counter ticks, or object collisions so sound cues feel tactile and dimensional without muddying spoken narration. Search aliases: `sfx transient tail layering`, `katmanlı ses efekti tasarımı`, `SFX-Schichtung Attack und Tail`. Do not activate when `constraints.no_audio` is true.

## Decision rules
- **Three-part temporal + spectral anatomy**: build hero accents from up to three non-competing components rather than stacking three full-range samples on the same frequencies:
  1. **Pre-lead / Whoosh (`-6..-1` frames before cut, `300–2200 Hz` swept bandpass noise)**: anticipates motion velocity.
  2. **Transient snap (`0..+1` frame at visual contact, `1.8–4.5 kHz` `4–15 ms` click/wood/pluck)**: gives frame-accurate perceptual sync.
  3. **Weight + Tail (`0..+12` frames, `55–95 Hz` pitch-dropped sine body + `4–9 kHz` soft filtered air decay)**: conveys mass and space.
- **Dialogue frequency pocket (`400 Hz – 2.5 kHz` protection)**: whenever voiceover is active at the same timestamp, omit or carve `-6 dB` out of the `500–2200 Hz` midband of SFX layers and scale SFX gain down `-5 dB` (`sfx_under_speech_gain = -16 dBFS` peak vs `-9 dBFS` solo).
- **Sample-accurate onset anchor**: place the peak of the **transient snap** (`layer 2`), not the start of a slow fade-in whoosh, at `round(cue_frame * 48000 / fps)` (`+-1` frame max offset for `cue_onset_alignment == pass`).

## Parameters and defaults
- `sample_rate_hz`: `48000` Hz.
- `lead_whoosh_frames`: `5` frames (`~167 ms` at `30/1` fps) peaking `1` frame before cut.
- `transient_attack_ms`: `2.0` ms, decay `12.0` ms.
- `sub_body_freq_sweep_hz`: `92 Hz -> 52 Hz` exponential drop over `140 ms` (audible on small laptop/phone harmonics when paired with `2nd` harmonic `184 -> 104 Hz` at `-9 dB`!).
- `max_cues_per_3s`: `4` (avoid machine-gun UI tick fatigue on every single letter!).

## Procedure
1. Classify each visual event by scale (`micro_tick` for counters/badges, `card_whoosh` for slide wipes, `hero_impact` for opening hook / climax).
2. Anchor `sample_anchor = round(event_frame * 48000 / fps)`: start `lead_whoosh` at `max(0, sample_anchor - lead_samples)` and fire `transient_snap` + `sub_body` precisely at `sample_anchor`.
3. Add a subtle `2nd` harmonic (`2 * f0`) to `sub_body` cues (`<= 90 Hz`) so tiny mobile speakers perceive bass pitch via missing-fundamental psychoacoustics without overdriving excursion.
4. Check concurrency with voiceover intervals; attenuate midband SFX energy by `-5 dB` whenever overlapping spoken words.
5. Verify sum of simultaneous stems stays below `-1.0 dBTP` and passes `qc` `cue_onset_alignment`.

## Failure modes and fixes
- **Whoosh starts *at* the cut frame, sounding `150 ms` late**: shift whoosh start earlier by `5` frames so its crest lands directly on the cut frame!
- **`55 Hz` pure sine impact is completely inaudible on phones**: blend `-9 dB` `2nd` harmonic (`110 Hz`) + crisp `2.6 kHz` `10 ms` transient click.
- **Every bullet-point word fires a loud whoosh (`12` whooshes in `6s`)**: reserve `hero_impact` for beat 1, use subtle `-22 dBFS` `8 ms` ticks for list items, and leave minor subheadings silent.

## Checklist
- [ ] Transient peak aligns with `round(cue_frame * 48000 / fps)` (`lead_whoosh` precedes the cut).
- [ ] Sub-bass impacts include `2nd`-harmonic overtone (`100–180 Hz`) for small-speaker translation.
- [ ] SFX overlapping speech carve `500–2200 Hz` and drop `-5 dB` so words never mask.
- [ ] Cue density stays purposeful (`<= 4` accents per `3s`, zero repetitive ear fatigue).

## Worked examples
- **Example 1 (`social-hook-reel` frame-0 `hero_impact` + frame-54 `wipe_left`)**: Frame `0` (`sample 0`): `2 ms` `2.8 kHz` snap + `92->52 Hz` fundamental/2nd-harmonic drop (`160 ms`). Frame `54` (`sample 86400`): bandpass noise sweep (`400->1900 Hz`) runs `samples 79200..86400` (`f = 49..54`), soft `2.2 kHz` settle click at `sample 86400`.
- **Example 2 (Animated `3`-bar chart ticks)**: Staggered bar completions at `f = 18, 24, 30` trigger ascending pitched marimba/sine ticks (`523 Hz`, `659 Hz`, `784 Hz`, `22 ms` decay at `-19 dBFS`) clear of voiceover.

## Resources (load only if needed)
- [Three-band procedural SFX synthesis recipes](references/three-band-sfx-recipes.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
