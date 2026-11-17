# Runtime coverage

| Area | Local implementation | Coverage boundary |
| --- | --- | --- |
| Skill selection | Metadata search, ranking, bounded load and declared references | The [generated catalog](../ReelSyntax_Skills/CATALOG.md) reports effective status after relation overrides. Guidance alone describes a workflow. |
| Transitions | Cut, cross dissolve, fade through black or white, left wipe, left/right slide, radial reveal, banded glitch | Baked into the master at integer frame positions |
| Geometry | Pillow shape-field, normalized points, path and mask primitives | CPU rasterization, per-scene cache and declared protected regions |
| Camera | Locked, dolly in, orbit, crane rise, dolly zoom | Availability depends on the scene recipe |
| Audio | Six procedural instruments, source tracks, trims, fades, pan, onset analysis | Local 16-bit PCM for onset analysis. Perceptual mix review requires listening. |
| Source media | Positive-speed footage retiming, opt-in HDR conversion, raster PSD masks and selected blend modes | HDR conversion needs FFmpeg zscale and tonemap. PSD adjustment layers, vector masks and complex groups require rasterization. |
| Engines | Pillow, FFmpeg, Blender and offline Chromium | Browser module execution requires explicit opt-in. External recipe packages require a named, installed entry point. |
| Editors | FCPXML, Premiere XML, OTIO and Blender VSE | Native import in Final Cut Pro, Premiere Pro and Resolve is untested. |

## Router hosts

| Host | Project directory | Checked locally | Interactive activation |
| --- | --- | --- | --- |
| Codex / Antigravity | `.agents/skills` | Installer and launcher | Unverified |
| Claude Code | `.claude/skills` | Installer | Unverified |
| Cursor | `.cursor/skills` | Installer | Unverified |
| GitHub Copilot | `.github/skills` | Installer and launcher | Unverified |

GitHub documents project-local discovery in its [Copilot skill guide](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills).
