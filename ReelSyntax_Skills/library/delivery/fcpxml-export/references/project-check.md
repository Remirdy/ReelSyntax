# Fcpxml export fixture

Use the repository fixture in `examples/editorial-study/reel.json`. Run its local `prepare.py` first to create the source media. For delivery checks render the Draft profile first.

| Project field | Fixture value |
| --- | --- |
| `output.fps` | `"24/1"` |

```sh
reelsyntax export examples/editorial-study --format fcpxml --profile draft
```

Verify the asset-clip offsets correspond to frames 0, 24 and 48 at 24 fps.
