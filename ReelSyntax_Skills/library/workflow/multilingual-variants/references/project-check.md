# Multilingual variants fixture

Use the repository fixture in `examples/foundation/reel.json`. For delivery checks render the Draft profile first.

| Project field | Fixture value |
| --- | --- |
| `scenes.0.params` | `{"heading": "FORM", "subheading": "Parts find their place.", "accent": "#bb5537"}` |

```sh
reelsyntax plan examples/foundation 
```

Provide strings.de.json with {"form.heading":"FORM"}. Render --locale de and inspect stream language deu.
