# Webm export fixture

Use the repository fixture in `examples/foundation/reel.json`. For delivery checks render the Draft profile first.

| Project field | Fixture value |
| --- | --- |
| `audio.enabled` | `true` |

```sh
reelsyntax export examples/foundation --format webm --profile draft
```

Probe the WebM for VP9 video and Opus audio. Decode the final frame.
