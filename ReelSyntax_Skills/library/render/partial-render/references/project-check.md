# Partial render fixture

Use the repository fixture in `examples/foundation/reel.json`. For delivery checks render the Draft profile first.

| Project field | Fixture value |
| --- | --- |
| `scenes.0.params` | `{"heading": "FORM", "subheading": "Parts find their place.", "accent": "#bb5537"}` |

```sh
reelsyntax render examples/foundation  --profile draft
```

Render twice and compare per-scene cache keys. Editing only the first heading changes its scene key.
