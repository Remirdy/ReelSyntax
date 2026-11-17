# Black frame detection fixture

Use the repository fixture in `examples/foundation/reel.json`. For delivery checks render the Draft profile first.

| Project field | Fixture value |
| --- | --- |
| `quality.exceptions` | `{"freeze": [[65, 90]], "silence": [[15, 90], [105, 180], [195, 240]]}` |

```sh
reelsyntax qc examples/foundation  --profile draft
```

Inspect the black check and distinguish complete fades from unexpected black intervals.
