# Core L-cut workflow

Use independent source audio when the outgoing sound should continue over the next picture. Read the brief's voice/music constraints and preserve the original source containers. This workflow uses the existing core source-audio mixer; it does not automatically link a track to a picture scene.

For a 24 fps timeline with a picture cut at frame 48, continuing outgoing sound until frame 54 creates a six-frame tail. The outgoing source must contain that extra audio handle even when its picture is trimmed to 48 frames.

```json
{
  "enabled": true,
  "gain_db": -14,
  "export_stems": true,
  "cues": [],
  "tracks": [
    {"id": "outgoing-tail", "source": "assets/outgoing.mp4", "kind": "effects", "start_frame": 0, "in_frame": 0, "duration_frames": 54, "fade_out_frames": 6},
    {"id": "incoming", "source": "assets/incoming.mp4", "kind": "effects", "start_frame": 54, "in_frame": 6, "duration_frames": 42, "fade_in_frames": 2}
  ]
}
```

This audio fragment fits a 96-frame project. When incoming picture starts at frame 48 from source time zero and both FPS values are 24, starting its audio at record frame 54 from source frame 6 keeps the incoming sound synchronized. Audio in-points use project-frame time; picture in-points count native decoded source frames. Recalculate when source FPS differs.

Render Draft, run `qc`, and review the outgoing stem, mix and encoded video across frames 48–54. Record the exact tail and source handle. Speech/music kinds are declared metadata, not automatic content recognition. Perceived continuity, dialogue masking and dramatic pauses require playback review; do not award those passes from a successful render alone.

Short source handles or unsafe peaks fail before the previous master is replaced. Adjust ranges/gain explicitly, then rerender. A later picture reorder does not inherently retime these independent tracks; revise the declared record anchors with the edit plan. The full local source example is `examples/editorial-study/reel.json`; renderer regressions cover both J/L placement and full-timeline source stems.
