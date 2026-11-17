# Audio stem export fixture

Use the repository fixture in `examples/foundation/reel.json`. For delivery checks render the Draft profile first.

| Project field | Fixture value |
| --- | --- |
| `audio.cues.0` | `{"frame": 0, "frequency": 220, "duration_frames": 15}` |

```sh
reelsyntax render examples/foundation  --profile draft
```

Enable audio.export_stems and inspect each WAV for sample rate, channel count and cue placement.
