# Gif preview fixture

Use the repository fixture in `examples/foundation/reel.json`. For delivery checks render the Draft profile first.

| Project field | Fixture value |
| --- | --- |
| `output.fps` | `"30/1"` |

```sh
reelsyntax export examples/foundation --format gif --profile draft
```

Inspect the GIF loop boundary and compare the displayed first scene to the project.
