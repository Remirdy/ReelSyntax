# Word timed captions fixture

Use the repository fixture in `examples/foundation/reel.json`. For delivery checks render the Draft profile first.

| Project field | Fixture value |
| --- | --- |
| `scenes.0.params.heading` | `"FORM"` |

```sh
reelsyntax export examples/foundation --format vtt --profile draft
```

The first cue starts at zero. For individual words supply a timed word table to captions burn --style word-pop.
