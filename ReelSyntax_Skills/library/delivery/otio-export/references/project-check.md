# Otio export fixture

Use the repository fixture in `examples/editorial-study/reel.json`. Run its local `prepare.py` first to create the source media. For delivery checks render the Draft profile first.

| Project field | Fixture value |
| --- | --- |
| `scenes.2.transition` | `{"type": "cross_dissolve", "duration_frames": 6}` |

```sh
reelsyntax export examples/editorial-study --format otio --profile draft
```

Inspect the last clip metadata for the baked transition. Source ranges point into the rendered master.
