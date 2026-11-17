# Loudness normalization fixture

Use the repository fixture in `examples/foundation/reel.json`. For delivery checks render the Draft profile first.

| Project field | Fixture value |
| --- | --- |
| `audio.gain_db` | `-14` |

```sh
reelsyntax qc examples/foundation  --profile draft
```

Read measured integrated loudness and true peak from the decoded master. Gain alone cannot predict either.
