# Poster thumbnail fixture

Use the repository fixture in `examples/foundation/reel.json`. For delivery checks render the Draft profile first.

| Project field | Fixture value |
| --- | --- |
| `scenes.0.duration_frames` | `90` |

```sh
reelsyntax export examples/foundation --format poster --frame 45 --profile draft
```

Inspect the PNG from the middle of the first scene. Its dimensions must match the rendered profile.
