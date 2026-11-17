# Font render audit fixture

Use the repository fixture in `examples/foundation/reel.json`. For delivery checks render the Draft profile first.

| Project field | Fixture value |
| --- | --- |
| `scenes.0.params` | `{"heading": "FORM", "subheading": "Parts find their place.", "accent": "#bb5537"}` |

```sh
reelsyntax qc examples/foundation  --profile draft
```

Read glyph_coverage and inspect a decoded frame at normal size for clipped ascenders or missing glyphs.
