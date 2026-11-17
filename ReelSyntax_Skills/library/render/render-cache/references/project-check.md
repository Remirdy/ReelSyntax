# Render cache fixture

Use the repository fixture in `examples/foundation/reel.json`. For delivery checks render the Draft profile first.

| Project field | Fixture value |
| --- | --- |
| `scenes.1` | `{"id": "time", "duration_frames": 90, "recipe": "rings", "engine": "pillow", "params": {"heading": "TIME", "subheading": "Motion finds its rhythm.", "accent": "#355f65"}}` |

```sh
reelsyntax cache examples/foundation --max-mib 64
```

Inspect the dry-run selection. Cache rows referenced by a current delivery must survive pruning.
