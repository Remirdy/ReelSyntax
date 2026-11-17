# L cut fixture

Use the repository fixture in `examples/editorial-study/reel.json`. Run its local `prepare.py` first to create the source media. For delivery checks render the Draft profile first.

| Project field | Fixture value |
| --- | --- |
| `audio.tracks.0` | `{"id": "detail-tail", "source": ".reelsyntax/inputs/source.mp4", "kind": "effects", "start_frame": 0, "in_frame": 24, "duration_frames": 32, "fade_out_frames": 4}` |

```sh
reelsyntax plan examples/editorial-study 
```

The first sound ends at frame 32, eight frames into the following picture.
