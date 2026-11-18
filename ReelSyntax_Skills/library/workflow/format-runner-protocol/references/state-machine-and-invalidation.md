# Format Runner State Machine and Invalidation Matrix

```text
idea ──► script ──► look ──► frames (snapshot) ──► pilot (5s draft) ──► full (draft) ──► hero ──► qc
 │         │         │
 └─────────┴─────────┴──► Editing any step marks all steps to its right as "stale"
```

| Step ID | Typical Wall Time | Output Artifact | Gate Behavior (`interactive` / `--yes`) |
| --- | ---: | --- | --- |
| `idea` | `< 1s` | `prompt.json` (`intent`) | Pause for angle edit / Auto-continue |
| `script` | `1–3s` | `prompt.json` (`storyboard`) | Pause for copy edit / Auto-continue |
| `look` | `< 1s` | `reel.json` | Pause for palette/font check / Auto-continue |
| `frames` | `1–2s` | `review/snapshots/*.png` | Visual layout check / Auto-continue |
| `pilot` | `2–6s` | `output/pilot-draft.mp4` | Motion & audio check / Auto-continue |
| `full` | `4–15s` | `output/draft.mp4` | **Unlocks `hero`** |
| `hero` | `8s–3m` | `output/hero.mp4` | Master encode |
| `qc` | `2–5s` | `review/hero-qc.json` | Final technical verdict |
