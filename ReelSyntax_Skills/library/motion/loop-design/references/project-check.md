# Loop design fixture

Use the repository fixture in `examples/foundation/reel.json`. For delivery checks render the Draft profile first.

| Project field | Fixture value |
| --- | --- |
| `scenes.2.duration_frames` | `60` |

```sh
reelsyntax qc examples/foundation --loop --profile draft
```

Inspect loop_picture. This three-shot study has different first and last frames.
