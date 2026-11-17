# Beat synced editing fixture

Use the repository fixture in `examples/foundation/reel.json`. For delivery checks render the Draft profile first.

| Project field | Fixture value |
| --- | --- |
| `audio.cues.1` | `{"frame": 90, "frequency": 330, "duration_frames": 15}` |

```sh
reelsyntax plan examples/foundation 
```

The second cue and second scene both start at frame 90. Move their anchors together when revising the cut.
