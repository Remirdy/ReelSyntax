# Caption delivery package fixture

Use the repository fixture in `examples/foundation/reel.json`. For delivery checks render the Draft profile first.

| Project field | Fixture value |
| --- | --- |
| `scenes.1.params` | `{"heading": "TIME", "subheading": "Motion finds its rhythm.", "accent": "#355f65"}` |

```sh
reelsyntax export examples/foundation --format srt --profile draft
```

The second title begins at three seconds. Check comma-separated millisecond timestamps.
