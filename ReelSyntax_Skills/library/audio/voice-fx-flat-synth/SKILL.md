---
name: voice-fx-flat-synth
description: "Shape stylized radio, intercom, retro-console chatter, or dry synthetic robot voices with controlled bandpass, subtle bit quantization, and intelligibility protection."
metadata:
  category: audio
  stage: build
  status: validated
  version: "2.0.0"
  aliases: "voice fx synth,stylized radio robot voice,stilize telsiz robot sesi,retro oyun ses efekti,stilisierte Funk- und Roboterstimme,Synthetische Stimmcharakteristik,efectos de voz sintética,effets de voix synthétique"
  requires: ""
---

# Voice FX Flat Synth

## Activation
Activate when producing retro low-poly cutscenes, sci-fi HUD briefings, mission-control intercom callouts, or stylized character chatter where leaning into crisp, intentional synthetic vocal texture beats uncanny pseudo-natural speech. Search aliases: `voice fx synth`, `stilize telsiz robot sesi`, `stilisierte Funk- und Roboterstimme`. Do not activate for warm human documentary narration or when `constraints.no_audio` / `no_voice` is true.

## Decision rules
- **Consonant intelligibility band (`1.5 kHz – 3.8 kHz`) is sacred**: never low-pass stylized dialogue below `3.2 kHz` or drown it in `> 25%` wet reverb; consonant articulation (`t`, `k`, `s`, `ş`, `ç`, `f`) lives in `1.5–4.0 kHz` and must remain crisp.
- **Choose one clean character archetype instead of stacking five effects**:
  - `field_intercom`: high-pass `280 Hz` + low-pass `3600 Hz` + soft `tanh` drive (`1.6x`) + `8 ms` dry cockpit slapback (`10%` wet) + `15 ms` squelch click at start/end.
  - `retro_blip_chatter`: syllable-synced pitched triangle/pulse blips (`180–340 Hz` per character register, `45 ms` envelope per vowel) paired with synchronized open dialogue captions (`retro-cutscene-directing`).
  - `flat_droid_monotone`: flatten pitch variance (`0.25x` F0 contour), `12`-bit amplitude quantization (`4096` steps — audible sheen without harsh `4`-bit screech), and subtle `14 ms` metallic comb (`12%` wet).
- **Mandatory open captions on heavy stylization**: whenever `bandpass` or `retro_blip_chatter` is active, enable synchronized captions so `100%` of words remain effortless on phone speakers.

## Parameters and defaults
- `intercom_hp_hz` / `intercom_lp_hz`: `280 Hz` / `3600 Hz` (`2nd`-order Butterworth).
- `saturation_drive`: `1.5` (`tanh(drive * x) / tanh(drive)` level-compensated).
- `bit_depth_floor`: `11–12` bits for speech (`>= 10` bits; never `< 8` bits on spoken words).
- `post_fx_peak_ceiling_dbtp`: `-1.5` dBTP before stem mixing.

## Procedure
1. Normalize clean input speech or synthesized phoneme stem to `-18 LUFS` and trim leading/trailing digital hum before applying nonlinear FX.
2. Apply high-pass (`280 Hz`) *before* `tanh` saturation or bit-quantization so low-frequency plosives (`p`, `b`) do not intermodulate and fart out the midband.
3. Apply the selected character filter (`field_intercom`, `flat_droid_monotone`, or `retro_blip_chatter` syllable synth) at `48000 Hz` sample rate.
4. Apply post-FX presence trim (`+2 dB` wide bell at `2.4 kHz` if needed, de-esser clamp above `5.5 kHz`) and brickwall true-peak limit at `-1.5 dBTP`.
5. Extract amplitude envelope per frame (`0..duration_frames - 1`) for character `mouth_envelope` lip-sync (`mouth_sync == pass`).

## Failure modes and fixes
- **8-bit crusher turns quiet breath tails into loud gating buzz**: gate input below `-46 dBFS` *before* quantizing, and use `12`-bit quantization (`4096` levels) instead of `6–8` bits.
- **Narrow `400–2000 Hz` filter makes `"s"` and `"f"` indistinguishable**: widen low-pass cutoff to `3600–4200 Hz`.
- **Resonance spike pierces ears on mobile speaker**: cap filter `Q <= 0.85` and check peak spectrum in `2–4 kHz`.

## Checklist
- [ ] High-pass (`>= 250 Hz`) precedes any saturation or bit-quantization stage.
- [ ] Low-pass cutoff stays `>= 3400 Hz` so consonant clarity is preserved.
- [ ] Quiet pauses are gated cleanly before nonlinear crushing (zero noise-floor buzz).
- [ ] Synchronized captions and frame-accurate `mouth_envelope` accompany stylized speech.

## Worked examples
- **Example 1 (`retro-lowpoly-cutscene` two-character contrast)**: Character A (Scout) uses `field_intercom` (`280–3800 Hz`, `1.4x` soft `tanh`) + `210 Hz` pitch center; Character B (Archivist) uses `flat_droid_monotone` (`12`-bit sheen, `150 Hz` pitch center) — distinct vocal silhouettes even with eyes closed.
- **Example 2 (Silent-speech retro RPG blip option)**: `65 ms` triangle-wave blips (`A: 290 Hz +- 25 Hz`, `B: 195 Hz +- 18 Hz` deterministic hash per syllable) synced `1:1` with typewriter subtitle reveal and `mouth_envelope`.

## Resources (load only if needed)
- [Stylized vocal DSP chains and parameter bounds](references/dsp-voice-presets.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
