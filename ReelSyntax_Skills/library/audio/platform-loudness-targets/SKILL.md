---
name: platform-loudness-targets
description: "Master integrated program loudness, short-term dynamics, loudness range, and true-peak ceilings using adjustable delivery presets and dual-pass measurement."
metadata:
  category: audio
  stage: export
  status: validated
  version: "2.0.0"
  aliases: "platform loudness targets,lufs true peak mastering,platform ses yüksekliği hedefleri,LUFS ve tavan seviye ayarı,Plattform-Lautheitsziele,LUFS und True-Peak-Mastering,objetivos de sonoridad por plataforma,cibles de sonie et crête vraie"
  requires: "ffmpeg"
---

# Platform Loudness Targets

## Activation
Activate during final audio mixdown and master export (`export` / `render` stage) to match integrated loudness (`LUFS`), loudness range (`LRA`), and inter-sample true-peak (`dBTP`) to the target viewing environment without pumping or codec clipping. Search aliases: `platform loudness targets`, `platform ses yüksekliği hedefleri`, `Plattform-Lautheitsziele`. Requires `ffmpeg`; do not activate when `constraints.no_audio` is true.

## Decision rules
- **Select preset by playback environment** (treat values below as adjustable defaults and verify against current official platform/broadcaster technical specs before commercial delivery):
  - `social_shortform` (vertical/feed web & mobile): `-14.0 LUFS` integrated (`+-1.0 LU`), `-1.0 dBTP` true peak (`-1.5 dBTP` safer before lossy AAC `128–192 kbps` re-encoding!), `LRA <= 7.0 LU`.
  - `mobile_podcast_speech` (voice-led explainer): `-16.0 LUFS` integrated (`+-1.0 LU`), `-1.0 dBTP` true peak, `LRA <= 6.0 LU`.
  - `broadcast_master` (EBU R128 reference): `-23.0 LUFS` integrated (`+-0.5 LU`), `-1.0 dBTP` (`-2.0 dBTP` some broadcasters), `LRA <= 11.0 LU`.
- **Short-form (< 10s) measurement caveat**: ITU-R BS.1770 / EBU R128 integrated gating requires sufficient active speech/program duration; on clips `< 6s` or sparse SFX-only stings, inspect `short-term max` (`<= -11 LUFS`) and `momentary max` (`<= -9 LUFS`) alongside `input_i` so a mostly-silent sting isn't boosted into a `-2 LUFS` ear-splitting transient!
- **Dual-pass linear normalization over single-pass dynamic pumping**: run pass-1 `loudnorm=print_format=json` to measure `input_i`, `input_tp`, `input_lra`, `input_thresh`, then apply pass-2 linear gain + true-peak limiter whenever linear gain satisfies `target_tp` (avoiding single-pass dynamic gain riding on short clips).

## Parameters and defaults
- `default_preset`: `"social_shortform"` (`target_i = -14.0`, `target_tp = -1.5`, `target_lra = 7.0` — adjustable in `reelsyntax.toml` or `reel.json`).
- `aac_headroom_margin_dbtp`: `-1.5` dBTP pre-encode ceiling so lossy psychoacoustic reconstruction stays `<= -1.0 dBTP` post-decode.
- `tolerance_lu`: `1.0` LU (`0.5` LU for strict broadcast).
- `sparse_audio_guard`: if active non-silent duration `< 2.5s`, cap momentary loudness `<= -10.0 LUFS` instead of blind integrated gain boost.

## Procedure
1. Balance stem hierarchy *before* master normalization: dialogue anchor around `-16 LUFS`, ducked music bed `-28..-24 LUFS` (`10–14 dB` below speech), SFX peaks `-16..-10 dBFS`.
2. Run pass-1 FFmpeg `ebur128` / `loudnorm=print_format=json` on the summed `48 kHz` float WAV master.
3. Check whether clip is short/sparse (`< 6s` or `< 35%` gated blocks); if sparse, clamp positive gain so `momentary_max <= -10 LUFS` and `true_peak <= -1.5 dBTP`.
4. Run pass-2 `loudnorm` with measured `measured_I`, `measured_TP`, `measured_LRA`, `measured_thresh`, `linear=true` + true-peak ceiling `-1.5 dBTP`.
5. Decode the final AAC `.mp4` stream in `qc` to verify post-codec `loudness` and `true_peak <= -1.0 dBTP` both pass.

## Failure modes and fixes
- **Lossy AAC encode pushes `-1.0 dBTP` WAV master to `-0.4 dBTP` (`true_peak: fail` in QC)**: master WAV to `-1.5 dBTP` (`0.5 dB` lossy codec reconstruction headroom) and encode AAC at `>= 192k`.
- **Single-pass `loudnorm` swells quiet intro pad by `+12 dB` before speech enters**: always use two-pass `loudnorm` with `linear=true` on pre-balanced stems.
- **2-second brand sting normalized to `-14 LUFS` integrated sounds twice as loud as speech**: cap short stings by `momentary_max <= -12 LUFS` and `-1.5 dBTP`.

## Checklist
- [ ] Stem balance (speech vs ducked music vs SFX) is set prior to master loudness pass.
- [ ] Two-pass linear `loudnorm` (with sparse/short-clip guard) avoids intro gain pumping.
- [ ] Pre-AAC true-peak ceiling is `-1.5 dBTP` so decoded `.mp4` stays `<= -1.0 dBTP`.
- [ ] Post-encode `qc` verifies `loudness` and `true_peak == pass`.

## Worked examples
- **Example 1 (`18s` spoken social reel, `social_shortform` preset)**: Pass 1 measures `input_i = -19.4 LUFS`, `input_tp = -5.8 dBTP`, `input_lra = 5.2 LU`. Pure linear gain `+5.4 dB` puts peak at `-0.4 dBTP` (`> -1.5`), so pass 2 applies `+5.4 dB` with transparent true-peak limiting at `-1.5 dBTP` -> Decoded MP4 measures `-14.1 LUFS`, `-1.2 dBTP` (`pass`).
- **Example 2 (`2.4s` brand sting, sparse guard)**: Pass 1 measures `input_i = -22.0 LUFS` (because `1.2s` is tail decay) and `momentary_max = -11.5 LUFS`. Sparse guard caps gain at `+0.0 dB` (`momentary_max` stays `-11.5 LUFS`, `tp = -2.1 dBTP`) so the sting sits gracefully after a `-14 LUFS` reel.

## Resources (load only if needed)
- [Adjustable loudness preset table and two-pass FFmpeg parameters](references/delivery-loudness-presets.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
