# Platform encoding fixture

Use the repository fixture in `examples/foundation/reel.json`. For delivery checks render the Draft profile first.

| Project field | Fixture value |
| --- | --- |
| `output.fps` | `"30/1"` |

```sh
reelsyntax render examples/foundation --target youtube --profile draft
```

Inspect the returned master for H.264 video, AAC when audio is enabled, and the original rational frame rate.
