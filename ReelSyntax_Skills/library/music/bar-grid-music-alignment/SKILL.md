---
name: bar-grid-music-alignment
description: "Quantize musical tempo, bar/beat frame boundaries, harmonic loop seams, and final cadence resolves onto exact integer project frames."
metadata:
  category: music
  stage: edit
  status: validated
  version: "2.0.0"
  aliases: "bar grid music alignment,tempo to frame grid,müzik ölçü ızgarası hizalama,BPM kare senkronu,Taktraster-Musikausrichtung,BPM auf Bildraster abstimmen,alineación musical por compases,alignement musical sur grille de mesures"
  requires: ""
---

# Bar Grid Music Alignment

## Activation
Activate when generating procedural music beds, cutting `photo-slideshow` / `lyric-video` / `music-visualizer` / `social-hook-reel` scenes to musical bars, or looping background stems without cumulative sub-frame beat drift. Search aliases: `bar grid music alignment`, `müzik ölçü ızgarası hizalama`, `Taktraster-Musikausrichtung`. Do not activate when `constraints.no_audio` or `constraints.no_music` is true.

## Decision rules
- **Choose exact-integer-frame tempos when synthesizing procedural beds**: at `30/1` fps, `120 BPM` (`15` frames/beat, `60` frames/bar in `4/4`), `100 BPM` (`18` frames/beat, `72` frames/bar), `112.5 BPM` (`16` frames/beat, `64` frames/bar), and `150 BPM` (`12` frames/beat, `48` frames/bar) yield **zero** fractional frame rounding across hundreds of bars!
- **Rational rounding when BPM is fixed externally**: for an external track (for example `128 BPM` at `30/1` fps = `14.0625` frames/beat), never add `round(14.0625) = 14` repeatedly (`0.0625 * 32 = 2` full frames drift by bar 8!); always compute `beat_frame(k) = round(k * 60 * fps / bpm)` from beat `0` plus measured `first_downbeat_offset_sec`!
- **Cut on bar/half-bar structural grid, not every quarter note**: cutting on every single beat (`0.5s`) turns slideshows into strobes; cut on `1`-bar (`4` beats = `60f` at `120 BPM`) or `2`-bar (`8` beats = `120f`) phrase boundaries, using off-beat `eighth`-note syncopation sparingly for high-energy climax turns.
- **Cadence resolve before end card**: land a tonic downbeat (`bar 1, beat 1`) at the entrance of the closing scene and let a natural `0.8–1.5s` chord ring + `15 ms` cosine tail finish cleanly before the final frame (never chop a mid-bar drum fill off at `EOF`!).

## Parameters and defaults
- `preferred_bpms_30fps`: `(90.0, 100.0, 112.5, 120.0, 125.0, 150.0)`.
- `preferred_bpms_24fps`: `(90.0, 96.0, 108.0, 120.0, 144.0)`.
- `time_signature`: `"4/4"` default (`beats_per_bar = 4`).
- `cut_subdivision`: `"1_bar"` or `"2_bars"` (`"half_bar"` for short climax bursts only).
- `ending_ringout_frames`: `30–45` frames (`1.0–1.5s` tonic sustain + clean fade to `-inf` `3` frames before `total_frames`).

## Procedure
1. Select an exact-integer-frame BPM for procedural synthesis (or measure `bpm` + `downbeat_0_samples` on user-supplied music).
2. Generate the canonical bar/beat table `frame(b) = round((downbeat_0_sec + b * 60 / bpm) * fps)` using `fractions.Fraction` so zero cumulative float drift occurs.
3. Snap scene durations so `scene_cut_frames` fall on bar downbeats (`b % 4 == 0`) or half-bars (`b % 2 == 0`).
4. Align `cross_dissolve` midpoints (`cut_frame`) — not dissolve start frames — onto the bar downbeat so the new visual reaches `50%+` dominance right on the musical accent!
5. Place a resolved root-chord hit on the final scene's downbeat and fade to clean zero `2–3` frames before `total_frames`.

## Failure modes and fixes
- **Cumulative rounding (`14 + 14 + 14...` for `128 BPM`) drifts `3` frames off the kick drum by `15s`**: compute `round(b * Fraction(60, 128) * fps)` from `b = 0` for every beat index `b` (`[0, 14, 28, 42, 56, 70, 84, 98, 112.5->112, 127...]`).
- **Dissolve *starts* on the downbeat, feeling visually sluggish**: center or finish the dissolve on the downbeat (`start = downbeat - dissolve_frames // 2`).
- **Music chopped mid-snare on the last frame**: re-arrange stem loop count to `floor(duration / bar_sec) - 1` bars plus a tonic chord ring-out bar.

## Checklist
- [ ] Beat-to-frame indices derive from rational `b * 60 * fps / bpm` without cumulative rounding drift.
- [ ] Procedural beds pick frame-commensurate BPMs (`100`, `112.5`, `120`, `150` at `30/1` fps).
- [ ] Hard cuts land on downbeats and dissolves straddle the downbeat symmetrically.
- [ ] Final bar resolves on the tonic chord and fades cleanly before `EOF`.

## Worked examples
- **Example 1 (`16s` / `480f` `photo-slideshow` at `30/1` fps, `112.5 BPM`, `4/4`)**: `1` beat = `16` frames, `1` bar = `64` frames (`2.133s`). `7` bars = `448` frames + `32`-frame (`half-bar`) resolved tail hold = `480` frames exact: Title (`64f`), Slide 1 (`128f` = `2` bars), Slide 2 (`64f`), Slide 3 (`128f`), End card (`96f` with tonic chord at `f = 384` and clean fade by `f = 477`).
- **Example 2 (`15s` / `450f` `social-hook-reel` at `30/1` fps, `120 BPM`)**: `1` bar = `60` frames (`2.0s`). Hook = `1` bar (`60f`), Proof 1 = `2` bars (`120f`), Proof 2 = `2` bars (`120f`), Burst = `1` bar (`60f`), Payoff = `1.5` bars (`90f` tonic hit at `f = 360`, ring-out `360..447f`). Sum = `450` frames.

## Resources (load only if needed)
- [Frame-commensurate BPM lookup table for 24, 25, 30, and 60 fps](references/integer-frame-bpm-table.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
