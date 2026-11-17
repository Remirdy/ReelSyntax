# J cut fixture

Use the repository fixture in `examples/editorial-study/reel.json`. Run its local `prepare.py` first to create the source media. For delivery checks render the Draft profile first.

| Project field | Fixture value |
| --- | --- |
| `audio.tracks.1` | `{"id": "assembly-lead", "source": ".reelsyntax/inputs/source.mp4", "kind": "effects", "start_frame": 40, "in_frame": 60, "duration_frames": 32, "fade_in_frames": 2, "fade_out_frames": 3}` |

```sh
reelsyntax plan examples/editorial-study 
```

The second effects track starts at frame 40, eight frames before the source picture cut.
