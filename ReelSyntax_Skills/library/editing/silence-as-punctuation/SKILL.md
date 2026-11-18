---
name: silence-as-punctuation
description: "Shape deliberate 8-to-36-frame acoustic pauses before thesis turns or reveals while registering intentional silence windows in QC exceptions."
metadata:
  category: editing
  stage: edit
  status: validated
  version: "2.0.0"
  aliases: "silence as punctuation,dramatic audio pause,noktalama olarak sessizlik,bilinçli ses boşluğu,Stille als Satzzeichen,gezielte Sprechpause,silencio como puntuación,silence de ponctuation"
  requires: ""
---

# Silence As Punctuation

## Activation
Activate when sculpting voiceover, music bed, and sound-effect gaps so key thesis statements, emotional turns, or metric reveals land with weight rather than drowning in wall-to-wall audio. Search aliases: `silence as punctuation`, `noktalama olarak sessizlik`, `Stille als Satzzeichen`. Do not activate when `constraints.no_audio` is true.

## Decision rules
- **Micro-breath vs full pause**:
  - `6–12` frames (`0.20s–0.40s` at `30/1`): comma-weight micro-pause; stays below FFmpeg `silencedetect` `0.50s` threshold automatically.
  - `15–36` frames (`0.50s–1.20s` at `30/1`): period/reveal-weight dramatic pause; **must** either keep a `-42 dBFS` room-tone/pad floor or register `[start_frame, end_frame]` in `reel.json` `quality.exceptions.silence`.
- **Click-free envelope**: apply a `3–6 ms` (`144–288` samples at `48 kHz`) raised-cosine fade-out entering the pause and `3–6 ms` fade-in exiting the pause so zero-crossing discontinuities never click.
- **Scarcity budget**: use at most `1` full dramatic silence (`>= 15f`) per `20s` of runtime; overuse turns punctuation into dead air.

## Parameters and defaults
- `micro_pause_frames`: `9` frames (`0.30s` at `30/1` fps).
- `dramatic_pause_frames`: `21` frames (`0.70s` at `30/1` fps; range `15–36`).
- `declick_ramp_ms`: `5.0` ms (`240` samples at `48000 Hz`).
- `room_tone_floor_dbfs`: `-44.0` dBFS optional subtle air bed when full digital zero (`-inf`) feels like a playback dropout.

## Procedure
1. Identify the single highest-value reveal word or number in the sequence.
2. Cut or duck both narration and music bed `micro_pause_frames` or `dramatic_pause_frames` immediately before that word's onset frame.
3. Apply `declick_ramp_ms` cosine fades on the outgoing music/voice tail and incoming transient so waveform boundaries cross zero smoothly.
4. If pause duration is `>= 15` frames (`>= 0.50s` at `30/1`) and drops below `-50 dBFS`, append `[pause_start_frame, pause_end_frame]` to `quality.exceptions.silence` in `reel.json`.
5. Run `qc` to confirm `silence == pass` (`unexplained == []`) and `true_peak == pass` on the post-pause re-entry accent.

## Failure modes and fixes
- **Digital zero sounds like broken stream on mobile speakers**: lay a `-44 dBFS` filtered room-tone or subtle sub-pad across the gap while muting rhythmic percussion and speech.
- **QC flags `silence: review` on intentional `0.8s` pause**: declare the exact integer frame pair `[start, end]` in `quality.exceptions.silence`.
- **Audible pop on hard mute**: add `5 ms` cosine micro-fade at both ends of the muted interval.

## Checklist
- [ ] Full dramatic silences are capped at `<= 1` per `20s` so contrast stays sharp.
- [ ] Outgoing and incoming audio edges have `3–6 ms` de-click ramps.
- [ ] Pauses `>= 0.50s` below `-50 dBFS` are declared in `quality.exceptions.silence`.
- [ ] Re-entry transient respects the true-peak ceiling (`<= -1.0 dBTP`).

## Worked examples
- **Example 1 (`15s` / `450f` product metric reveal, EN)**: Music + narration run `0–288f`, `5 ms` cosine ramp to digital silence across `288–312f` (`24` frames = `0.80s`), `312f` crisp `sub_impact` + spoken `"Zero retries."` `quality.exceptions.silence` stores `[[288, 312]]` -> `qc` `silence: pass`.
- **Example 2 (`18s` / `540f` narrative turn, DE)**: `0–330f` Aufbau mit Musikbett, `330–339f` (`9` Frames = `0.30s` Kurzpause ohne QC-Ausnahme, da `< 0.50s`), `339f` trockene Pointe ohne Musik, `360f` Musik setzt wieder ein.

## Resources (load only if needed)
- [Acoustic pause duration and de-click envelope specification](references/pause-envelope-spec.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
