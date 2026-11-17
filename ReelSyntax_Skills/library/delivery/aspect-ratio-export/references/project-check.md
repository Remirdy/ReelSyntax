# Aspect ratio export fixture

Use the repository fixture in `examples/foundation/reel.json`. For delivery checks render the Draft profile first.

| Project field | Fixture value |
| --- | --- |
| `output.width` | `960` |

```sh
reelsyntax render examples/foundation --aspect 9:16 --profile draft
```

Open the returned variant project. Verify width divided by height is 9/16 and read every label at Draft size.
