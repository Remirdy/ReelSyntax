# Quality and evidence

ReelSyntax implements the objective technical gates of the [Production quality contract](../ReelSyntax_Skills/QUALITY_STANDARD.md) while keeping subjective creative evaluation explicit. No automated command certifies AAA artistic quality.

## Technical checks executed by `reelsyntax qc`

1. **Stream and container integrity**: FFprobe exact decoded frame count, even dimensions, rational frame rate, duration tolerance (`<= 1` frame), H.264/48 kHz AAC presence, and full `ffmpeg -xerror` null decode.
2. **Exact timestamp cadence**: Every decoded video frame `best_effort_timestamp_time` verified within `10` microseconds of `i / fps`.
3. **Color metadata**: Stream VUI and MP4 container verified for explicit `bt709` color space, transfer, primaries, and `tv` range.
4. **Anomaly and loudness scanning**: `blackdetect`, `freezedetect`, `silencedetect` (checked against bounded half-open `quality.exceptions`), integrated loudness measurement, and `true_peak <= -1.0 dBTP`.
5. **Typography contrast and glyph coverage**: Foreground/kicker vs background WCAG 2.2 luminance ratio (`>= 3.0:1` large / `>= 4.5:1` normal) plus `.notdef` missing-glyph rendering verification across all scene strings (including Turkish `ÇĞİÖŞÜçğıöşü`).
6. **Cue onset alignment**: Actual synthesized PCM waveform inspected around each declared `audio.cues` frame to confirm nonzero onset energy within `<= 2` video frames.
7. **Temporal continuity and ROI locks**: Intra-shot mean luminance spike screening and lossless pre-encode crop SHA-256 verification for locked pixel regions (`locked_regions`).

## Hero profile obligations

Selecting `--profile hero` uses `3x` Lanczos supersampling on CPU scenes (or `CYCLES` on headless Blender scenes) and generates `review/hero-lookdev-ab.png` (neutral vs AgX graded comparison) and `review/hero-motion-extrema.png`. `creative_review`, `cue_sync` playback perception, and `glyph_integrity` visual shaping remain `review` items requiring human or host-agent inspection of actual frames.
