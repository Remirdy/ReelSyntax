# Render queue fixture

Use the repository fixture in `examples/foundation/reel.json`. For delivery checks render the Draft profile first.

| Project field | Fixture value |
| --- | --- |
| `output` | `{"width": 960, "height": 540, "fps": "30/1"}` |

```sh
reelsyntax status examples/foundation 
```

For queue delivery use a JSON array such as [{"aspect":"1:1"},{"aspect":"9:16"}] and render --queue jobs.json. Check both returned projects.
