# Template parameterization fixture

Use the repository fixture in `examples/foundation/reel.json`. For delivery checks render the Draft profile first.

| Project field | Fixture value |
| --- | --- |
| `scenes.0.params.heading` | `"FORM"` |

```sh
reelsyntax render examples/foundation --set form.heading=TEST --profile draft
```

Inspect the variant reel.json and confirm the original project still reads FORM.
