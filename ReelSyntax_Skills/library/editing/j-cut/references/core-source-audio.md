# Core J-cut workflow

Use this reference when the brief calls for incoming sound before its picture and local source media is authorized. The core path uses FFmpeg, Pillow review artifacts and independent `audio.tracks`; it does not require an interactive editor or a paid service. It does not infer dialogue boundaries or identify speakers.

## Establish source and record time

1. Run `reelsyntax doctor --json`, validate the project and inspect its rational FPS and scene boundaries.
2. Keep immutable source containers in an asset directory. Managed output/cache paths cannot be sources; copy a previous render into `assets/` first. URLs, playlists, traversal and symlinks are rejected.
3. Record source FPS separately from project FPS. Footage `params.in_frame` counts native decoded source frames. Audio `in_frame`, `start_frame`, fades and duration count project frames.

For two 48-frame shots at 24 fps, the picture cut is frame 48. A six-frame audio lead starts at frame 42. If the incoming source is also 24 fps, set its picture in-point to source frame 6 while incoming audio starts from source frame 0. At record frame 48 both streams then represent source time 0.25 seconds. With another source FPS, calculate the corresponding source-frame in-point and verify the rounding tolerance.

```json
{
  "enabled": true,
  "gain_db": -14,
  "export_stems": true,
  "cues": [],
  "tracks": [
    {"id": "outgoing", "source": "assets/outgoing.mp4", "kind": "effects", "start_frame": 0, "in_frame": 0, "duration_frames": 48, "fade_out_frames": 6},
    {"id": "incoming", "source": "assets/incoming.mp4", "kind": "effects", "start_frame": 42, "in_frame": 0, "duration_frames": 54, "fade_in_frames": 6}
  ]
}
```

This is an `audio` object for a 96-frame project, not a complete project file. Incoming source audio must contain at least 54 project-frame units after its in-point. Source audio is normalized to 48 kHz stereo; fades and source gain add to the master gain. Use the actual declared `kind`: voice or music must respect `no_voice`/`no_music`. The runtime does not classify the content for you.

## Execute and inspect

```sh
reelsyntax validate ./film
reelsyntax render ./film --profile draft
reelsyntax qc ./film --profile draft
reelsyntax snapshot ./film --profile draft --frame 48
```

Inspect `output/draft-stem-source-incoming.wav`, the mixed WAV and actual encoded playback around frames 42–54. Save the intended lead, source/record in-points, source hashes, resulting frame count, measured loudness/peak and playback findings. `qc` checks media integrity, cadence and loudness; it does not establish that an arbitrary incoming sentence is intelligible or narratively correct. Natural leading silence must be evaluated against the source waveform rather than treated as a placement bug.

On short input or unsafe peak, revise the source range or gain; do not pad a missing phrase or silently trim source audio. Keep intentional silence exceptions narrowly scoped and recheck them after timing changes. Mechanical placement, stem boundaries and fractional-rate endpoints are exercised in `tests/test_ingest.py`; creative acceptance still requires listening.
