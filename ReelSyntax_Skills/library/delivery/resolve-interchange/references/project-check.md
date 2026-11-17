# Resolve interchange fixture

Use the repository fixture in `examples/editorial-study/reel.json`. Run its local `prepare.py` first to create the source media. For delivery checks render the Draft profile first.

| Project field | Fixture value |
| --- | --- |
| `scenes.0` | `{"id": "detail", "duration_frames": 24, "recipe": "footage", "engine": "ffmpeg", "params": {"source": ".reelsyntax/inputs/source.mp4", "in_frame": 24}}` |

```sh
reelsyntax export examples/editorial-study --format fcpxml --profile draft
```

Inspect media references and rational frame durations. Record native Resolve import separately.
