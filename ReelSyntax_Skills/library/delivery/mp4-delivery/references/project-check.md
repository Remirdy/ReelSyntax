# Mp4 delivery fixture

Use the repository fixture in `examples/foundation/reel.json`. For delivery checks render the Draft profile first.

| Project field | Fixture value |
| --- | --- |
| `output` | `{"width": 960, "height": 540, "fps": "30/1"}` |

```sh
reelsyntax qc examples/foundation  --profile draft
```

Check frame count, dimensions and codec in the QC report before reviewing playback.
