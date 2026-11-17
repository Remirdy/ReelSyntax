# ReelSyntax

Local skill routing, a progressive Unified MCP Gateway, and deterministic headless video production for coding agents.

**Development status: active development, version 0.1.0, pre-release.** Interfaces and project formats may change. The implemented slices below have local test evidence; the full production roadmap is still in progress. Technical checks do not certify artistic quality or compatibility with every editor and platform.

ReelSyntax pairs a 517-skill specialist catalog with a zero-dependency Python 3.11+ core, optional local renderers (Pillow raster composition and software 3D, isolated headless Chromium Canvas/WebGL2, FFmpeg source footage, and headless Blender), and first-party Git submodule integrations for [`Remirdy/BlenderMCP`](https://github.com/Remirdy/BlenderMCP) and [`Remirdy/AfterEffectsMCP`](https://github.com/Remirdy/AfterEffectsMCP). No mandatory model download, embedding service, paid API, ComfyUI/LTX/Wan stack, or graphical application is required.

## Completed and remaining work

| Area | Completed locally | Remaining |
| --- | --- | --- |
| Skill routing | 517 indexed skills, bounded disclosure, multilingual ranking, constraints, integrity and host installers | Broader independent task evaluation and production feedback |
| Render and review | Draft/Production/Hero, H.264/AAC, exact frame timing, technical QC, selective cache, recovery and approval locks | Broader creative examples, advanced animation and compositing |
| Native 3D and shaders | Four-shot Blender Cycles optical film and an isolated WebGL2 sculpture recipe | More scene recipes, custom shader/Three.js adapters and GPU/platform coverage |
| Source media | Local video trimming, normal-alpha raster layer composition, supported 8-bit RGB PSD layer extraction, independently timed source audio and J/L cuts | Advanced PSD blend modes/masks, HDR grading, retiming and a general nonlinear track model |
| Editorial delivery | OTIO/FCPXML, captions, SVG, native Blender Video Sequencer project and preview export | Native Final Cut/Premiere/Resolve import coverage and richer editable effects |
| Cache management | Dry-run LRU pruning, optional render disk budget, delivery-reference protection and shared operation lock | Long-duration 4K resource benchmarks and broader cross-OS stress testing |
| MCP integrations | Progressive gateway, live stdio discovery, schema/workspace boundaries and JSX static validation | Live interactive Blender bridge and After Effects execution; upstream compatibility patches |
| Distribution | Wheel/sdist; Linux/macOS/Windows core CI on Python 3.11/3.14; Linux FFmpeg media tests and submodule audits | Release packaging/publishing and broader hardware/runtime coverage |

See the [development evidence](docs/development-status.md) and [roadmap](docs/roadmap.md) for exact verification and external gates. PSD extraction reuses an existing optional AfterEffectsMCP Node runtime; it does not require the After Effects application. Interactive application checks remain separate from verified headless operation.

The six-second [Aperture example video](docs/media/aperture-study.mp4) was rendered locally with native Blender Cycles. Its [editable source plan](examples/aperture-film/reel.json) and procedural scene implementation are included.

[![Frame from the rendered Aperture optical mechanism study](docs/media/aperture.png)](docs/media/aperture-study.mp4)

## Quick start

```sh
python3 -m reelsyntax doctor --json
python3 -m reelsyntax integrations --json
python3 -m reelsyntax capabilities --refresh --limit 8
python3 -m reelsyntax skills search "psd animasyon seslendirme senkronu" --json
python3 -m reelsyntax skills explain "kamera sabit yazı olmasın" --stage plan
python3 -m reelsyntax skills load frame-clock
python3 -m reelsyntax skills validate
```

Warm metadata searches read zero specialist instruction bodies. Ranking supports English and Turkish morphology, negative clause exclusions, audio-vs-camera disambiguation, dependency closure, conflict filtering, capability allowlists (`--available`), and cumulative session context budgets.

To install in an isolated virtual environment:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
```

Optional rendering extras are `.[render]` (Pillow) and `.[browser]` (Pillow + Playwright). FFmpeg/FFprobe, Blender, and Adobe After Effects are separate local executables discovered automatically or configured via `REELSYNTAX_FFMPEG`, `REELSYNTAX_FFPROBE`, `REELSYNTAX_BLENDER`, `AE_BINARY`, and `AERENDER_BINARY`. Runtime commands never silently download software or contact remote services.

## Production workflow and quality control

```sh
python3 -m reelsyntax init ./my-film
python3 -m reelsyntax validate ./my-film
python3 -m reelsyntax plan ./my-film
python3 -m reelsyntax render ./my-film --profile draft
python3 -m reelsyntax render ./my-film --profile hero --fallback pillow
python3 -m reelsyntax qc ./my-film --profile hero
python3 -m reelsyntax diff ./my-film --base draft --target hero
python3 -m reelsyntax snapshot ./my-film --frame 45 --profile hero
python3 -m reelsyntax export ./my-film --format otio --profile hero
python3 -m reelsyntax export ./my-film --format fcpxml --profile hero
python3 -m reelsyntax export ./my-film --format blender --profile hero --frame 45
python3 -m reelsyntax cache ./my-film --max-mib 1024
python3 -m reelsyntax handoff ./my-film
```

- **Timing and color**: Canonical rational FPS (`24/1`, `30/1`, `30000/1001`) over sequential integer frames; OKLab perceptual color mixing, linear-light three-point 3D shading with AgX highlight rolloff, and explicit BT.709 VUI/MP4 color metadata.
- **Profiles and caching**: Content-addressed per-scene caches including source asset hashes, `resume` recovery, `checkpoint`/`restore` revisions, whole-scene locks, and lossless pre-encode `locked_regions` pixel protection. `hero` uses recipe-appropriate refinement and emits look development or shot study sheets plus motion extrema. `cache --max-mib N` previews unused-cache removal; add `--apply` to perform it, or pass `render --cache-budget-mib N` for post-delivery pruning. Caches referenced by current deliveries remain protected even when they exceed the requested budget.
- **Objective QC vs creative review**: `qc` verifies FFprobe stream contracts, full decode, 10-microsecond frame cadence, black/freeze/silence intervals, loudness and true peak, WCAG contrast ratios, `.notdef` glyph coverage (including Turkish `ÇĞİÖŞÜçğıöşü`), PCM cue-onset alignment, temporal continuity, and ROI locks. Technical pass never substitutes for human or host-agent visual and audio review.

See [`examples/foundation`](examples/foundation/), [`examples/cinematic-study`](examples/cinematic-study/), [`examples/aperture-film`](examples/aperture-film/), [`examples/editorial-study`](examples/editorial-study/) and [`examples/shader-study`](examples/shader-study/).

## Unified MCP Gateway and agent host setup

Registering `python3 -m reelsyntax mcp` exposes a constant 9-tool progressive MCP surface (`reelsyntax_skills_*`, `gateway_search_tools` → `gateway_describe_tool` → `gateway_call_tool`, `reelsyntax_project_*`), routing across `blender:*` (`integrations/BlenderMCP`) and `after_effects:*` (`integrations/AfterEffectsMCP`) on demand without loading 570+ tool schemas into prompt context.

First-party integration management and host router installation:

```sh
python3 -m reelsyntax install blender --dry-run
python3 -m reelsyntax install after-effects --dry-run
python3 -m reelsyntax install --all
python3 -m reelsyntax update
python3 -m reelsyntax skills install ./my-film --host antigravity
python3 -m reelsyntax skills install ./my-film --host codex
python3 -m reelsyntax skills install ./my-film --host claude
python3 -m reelsyntax skills install ./my-film --host cursor
```

See [first-party MCP & submodule sync](docs/first-party-mcp.md), [CLI reference](docs/cli.md), [project format](docs/project-format.md), [quality](docs/quality.md), [competitive analysis](docs/research/competitive-analysis.md), [security](SECURITY.md), and [development status](docs/development-status.md).

## Verification

```sh
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s ReelSyntax_Skills/tests -v
python3 -m reelsyntax skills test
```

Enable full media and browser integration suites with `REELSYNTAX_MEDIA_TESTS=1` and `REELSYNTAX_BROWSER_TESTS=1`.

## License

MIT. Retain [`LICENSE`](LICENSE). Submodules and optional external tools carry their own licenses.
