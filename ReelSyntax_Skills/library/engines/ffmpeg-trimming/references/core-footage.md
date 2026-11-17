# Core decoded-frame footage trim

Use the `footage` recipe for an authorized local video container. It selects an explicit allowlisted demuxer and restricts input to the file protocol. Remote URLs, playlists, disguised playlists, source symlinks and managed output/cache paths are refused. Copy previous renders into an asset directory before reusing them.

```json
{
  "id": "source-shot",
  "duration_frames": 48,
  "recipe": "footage",
  "engine": "ffmpeg",
  "params": {"source": "assets/source.mp4", "in_frame": 24, "background": "#000000"}
}
```

This scene starts at native decoded source frame 24 and delivers 48 project frames. Source frame rate and project frame rate are separate: the decoded sequence is trimmed, reset to time zero, resampled to project FPS, aspect-fitted and letterboxed. It is not a packet-copy edit and does not infer keyframe positions. Short input fails rather than repeating the last frame.

The picture recipe discards embedded audio. Use independent `audio.tracks` for source sound and J/L cuts; their in-points use project-frame time, not native source-frame indices. Do not claim synchronization from equal numeric in-points when the source and project FPS differ.

Render Draft and inspect its first frame against the intended decoded source frame, plus final frame/count, aspect ratio, letterbox and color. Run QC on the actual MP4 and retain source hashes. PQ/HLG input requires an explicit SDR grade first. Typography and camera overrides are unsupported for this recipe and must not be silently approximated.

The renderer hashes referenced source bytes into affected scene keys and verifies them again before delivery and QC/export. A source mutation during work requires a fresh render. Frame-contract and short-input failures preserve the previous delivered master. `tests/test_ingest.py` exercises actual decoded-frame selection, aspect fit, source integrity, playlist refusal and short-source failure.
