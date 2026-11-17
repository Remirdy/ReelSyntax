---
name: ebu-r128-dialogue-gating
description: "Use for EBU R128 loudness gating and short-form dynamics. Validate gated LUFS, loudness range (LRA), and oversampled true-peak headroom across sparse cues and short bumpers."
metadata:
  category: audio
  stage: review
  status: validated
  version: "2.0.0"
  aliases: "ebu r128,dialogue gating,lufs ölçümü,kısa video ses seviyesi"
  requires: "ffmpeg"
---

# Ebu R128 Dialogue Gating

## Activation
Use when mastering or auditing program loudness, short brand bumpers ($< 5\text{ s}$), sparse procedural UI cues, or dialogue-plus-music mixes. Search aliases: ebu r128,dialogue gating,lufs ölçümü,kısa video ses seviyesi.

## Inputs and output
- Inputs: Encoded delivery file or 48 kHz PCM master, target profile (`web -14 LUFS` or `broadcast -23 LUFS`), and intentional silence intervals.
- Output: Measured integrated LUFS, LRA, true peak (dBTP), and short-program gating diagnostic.
- Required capability: ffmpeg
- Evidence bundle: FFmpeg `loudnorm` / `ebur128` JSON report, true-peak headroom check, and post-AAC re-measurement.

## Production recipe
1. Measure loudness **after** final AAC/Opus lossy encoding as well as on PCM mix: perceptual psychoacoustic coding frequently raises inter-sample true peaks by $0.3\text{–}0.8\text{ dB}$, so target $\le -1.5\text{ dBTP}$ pre-encode to guarantee $\le -1.0\text{ dBTP}$ post-encode.
2. Account for BS.1770-4 / EBU R128 400 ms gating blocks ($-70\text{ LKFS}$ absolute gate, $-10\text{ LU}$ relative gate): on short stings ($< 3\text{ s}$) or sparse motion-design cues separated by intentional silence, blind integrated normalization can over-boost transient hits into clipping or amplify noise floors.
3. For sparse-cue motion studies without continuous beds, govern gain by momentary/short-term ceiling and true-peak safety ($\le -1.0\text{ dBTP}$) while declaring intentional silence intervals explicitly in `quality.exceptions.silence`.
4. Maintain loudness range $\text{LRA} \le 7\text{ LU}$ for mobile/web social feeds and $\le 11\text{–}15\text{ LU}$ for cinema/long-form narrative.

## Acceptance criteria
- Post-encode true peak $\le -1.0\text{ dBTP}$ (or stricter profile spec); zero digital clipping samples; intentional silence preserved un-normalized.
- Record integrated LUFS, true peak dBTP, LRA, and playback intelligibility review.

## Failure and repair
If `loudnorm` single-pass pumps ambience or clips transients on short clips, switch to two-pass linear `loudnorm` (`linear=true` using measured first-pass stats) when headroom permits, or apply fixed gain + lookahead true-peak limiter.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric.
- [EBU R128 Specification](https://tech.ebu.ch/publications/r128)
- [FFmpeg loudnorm Filter](https://ffmpeg.org/ffmpeg-filters.html#loudnorm)

Original production guidance and validated runtime audit.
