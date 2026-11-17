# Ffmpeg trimming fixture

Use the repository fixture in `examples/editorial-study/reel.json`. Run its local `prepare.py` first to create the source media. For delivery checks render the Draft profile first.

| Project field | Fixture value |
| --- | --- |
| `scenes.0.params` | `{"source": ".reelsyntax/inputs/source.mp4", "in_frame": 24}` |

```sh
reelsyntax plan examples/editorial-study 
```

Source in_frame is measured in native decoded source frames. Scene duration is measured at output rate.
