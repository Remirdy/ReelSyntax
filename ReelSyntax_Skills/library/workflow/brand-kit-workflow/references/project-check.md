# Brand kit workflow fixture

Use the repository fixture in `examples/foundation/reel.json`. For delivery checks render the Draft profile first.

| Project field | Fixture value |
| --- | --- |
| `scenes.0.params.accent` | `"#bb5537"` |

```sh
reelsyntax plan examples/foundation 
```

Place {"accent":"#355f65"} in brand.json. Render --brand brand.json and inspect the resolved scene parameters.
