# Premiere interchange fixture

Use the repository fixture in `examples/editorial-study/reel.json`. Run its local `prepare.py` first to create the source media. For delivery checks render the Draft profile first.

| Project field | Fixture value |
| --- | --- |
| `scenes.1` | `{"id": "plate", "duration_frames": 24, "recipe": "layer-stack", "engine": "pillow", "params": {"background": "#181d21", "layers": [{"source": ".reelsyntax/inputs/still.png", "name": "Optical study", "x": 80, "y": 45, "width": 480, "height": 270}, {"source": ".reelsyntax/inputs/frame.png", "name": "Frame", "opacity": 0.8}]}}` |

```sh
reelsyntax export examples/editorial-study --format premiere --profile draft
```

Read the second clipitem start and end in the xmeml sequence and verify the master URI.
