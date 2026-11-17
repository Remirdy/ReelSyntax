# Batch production fixture

Use the repository fixture in `examples/foundation/reel.json`. For delivery checks render the Draft profile first.

| Project field | Fixture value |
| --- | --- |
| `output.height` | `540` |

```sh
reelsyntax render examples/foundation --aspect 16:9,1:1 --profile draft
```

Inspect each returned project and confirm that it owns an independent manifest.
