# Changelog

## [Unreleased]

### Added

- Add prompt compilation pipeline (`reelsyntax.prompt.intent`, `storyboard`, `compiler`, and bounded 3-attempt schema `repair`) with untrusted-prompt data framing and path/recipe allowlists.
- Add `LLMProvider` protocol and `offline_rules`, `ollama`, `openai_compat`, and `mcp_host` providers (`reelsyntax.prompt.providers`) with loopback-only default network policy and `reelsyntax doctor --providers`.
- Add internationalization foundation (`locales/` with `status.json`, `lang-profiles/` for `en`/`tr`/`de`, `reelsyntax.lang` offline language detection and locale-aware Turkish/German casing, `reelsyntax lang` CLI commands, multilingual negative routing patterns, and Tier 1 golden routing suites).
- Add community format and language issue templates, Discussions and private security advisory routing (`.github/ISSUE_TEMPLATE/config.yml`), and repository label taxonomy (`.github/labels.json`, `tools/sync_labels.py`).
- Add automated security scanning workflow (`.github/workflows/security.yml` with CodeQL, `pip-audit`, and license/CVE dependency review) and grouped Dependabot updates.
- Add PyPI package metadata and subpackage inclusion in `pyproject.toml`, automated release verification/notes/MCPB SHA-256 stamping (`tools/release_prepare.py`), PyPI OIDC Trusted Publishing workflow, and `docs/releasing.md`.
- Expand CI media verification (`doctor`, FFmpeg/Blender path discovery, `render`, and `qc`) across Ubuntu, macOS, and Windows, add standard cross-platform binary fallback paths, and terminate child process trees on Windows timeouts.
- Add canonical versioned JSON Schemas (`docs/schemas/reel.v1.schema.json`, `docs/schemas/config.v1.schema.json`) with `$id` URLs and non-destructive project schema migration (`reelsyntax migrate`).
- Add `reelsyntax.toml` configuration support (`reelsyntax.config`) using Python's `tomllib`, `reelsyntax config show|path|init|validate` CLI commands, and `docs/config.schema.json`.
- Add `tests/test_code_style.py` to enforce zero comments and zero docstrings across new and modified Python, JavaScript, TypeScript, CSS, HTML, and shell source files.
- Expand `ruff` lint checks (`F401`, `F841`, `B006`) and align `.github/PULL_REQUEST_TEMPLATE.md` with the review template.

## [0.1.0] — 2026-11-18

### Added

- Add local delivery variants, templates, locale tables, platform presets, preview exports and caption burn-in.
- Add shape fields, slide, radial, white fade and glitch transitions, browser recipes, nested master compositions and an editor schema.
- Add Premiere XML interchange, HTML QC, flash and loop checks, PCM onset analysis and a searchable skill catalog.
- Add nine lazy production references for existing skills without changing their instruction bodies; version session resources by their own hashes and include verified resource digests in load responses.
- Add local footage trimming, normal-alpha raster layer stacks, bounded optional PSD raster extraction, and independently timed source audio with J/L cuts, fades, pan and source stems.
- Add source asset integrity checks, delivery-protected LRU cache pruning and optional post-delivery disk budgets.
- Add capability-probed offline WebGL2 SDF rendering and native Blender Video Sequencer export with saved-project reopen and frame preview.
- Add native Blender 5.1+ Cycles `aperture` optical-mechanism recipe (`reelsyntax/blender_aperture.py`) and 4-shot `examples/aperture-film` study (`macro`, `iris`, `assembly`, `hero`) with AR meniscus optics, quad-strip 11-blade iris geometry, Metal GPU Cycles rendering, `hero-shot-study.png` plates, SVG schematic export, and per-shot hold-keyframed After Effects 3D camera handoff.
- Integrated the Production v2 specialist pack and expanded the catalog to 517 unique, non-overlapping skills across 25 categories with metadata index v2, SHA-256 integrity checks, dependency/conflict graphs, Turkish/English stemming, negation and audio-drone disambiguation, cumulative session budgets, and a 50-case routing benchmark.
- Added `integrations/BlenderMCP` (`Remirdy/BlenderMCP`) and `integrations/AfterEffectsMCP` (`Remirdy/AfterEffectsMCP`) as independent Git submodules behind a Unified MCP Gateway (`reelsyntax mcp`) exposing 9 progressive meta-tools, `blender:*` and `after_effects:*` namespacing, lazy schema loading, schema-diff auditing, and automated GitHub Actions synchronization (`.github/workflows/sync-submodules.yml`).
- Added deterministic production modules for OKLab/AgX color science, second-order mass-spring-damper camera rigs, Verlet physics ribbons, TrueType typography with `.notdef` glyph coverage and WCAG contrast verification, headless Blender 3.6–5.x CLI rendering with `--fallback`, multi-stem stereo procedural audio, cross-dissolve/wipe transitions, lossless ROI pixel locks, profile `diff` sheets, and `.otio` / `.fcpxml` / `.vtt` / `.srt` / `.svg` exports.

### Changed

- Generate the Markdown catalog with effective statuses and category counts.
- Remove the optional SDK requirement from native OTIO routing metadata and refresh JSON/CSV catalogs together through CLI reindexing.
- Configure FFmpeg installation for the disposable CI media runner, correct optional App-token workflow conditions, and pin official Actions to Node 24 revisions.
- Exclude generated state, outputs and review files from source packages for every example project, including cinematic studies.

### Fixed

- Anchor transition blends to the outgoing scene boundary for the entire transition.
- Fix CRLF skill frontmatter parsing while retaining byte-exact integrity checks; stabilize checkout line endings and UTF-8 CLI output across operating systems.
- Correct editorial master exports: Draft dimensions, absolute encoded media URIs, source-relative markers, OTIO fractional-rate precision, baked-transition metadata and embedded-audio fallback; reject stale render manifests, unknown profiles and out-of-range SVG frames.
- Enforce published MCP meta-tool input types, nullability, nested schemas and bounds before dispatch; add an explicit project workspace boundary and bounded, recoverable stdio parsing.
- Fixed browser renderer readiness/draw hang isolation via a dedicated process-group worker, fixed H.264 VUI and MP4 `bt709` color tag preservation across stream-copy muxing, and added verified router installation support for Codex, Antigravity, Claude Code, and Cursor.

[0.1.0]: https://github.com/Remirdy/ReelSyntax/releases/tag/v0.1.0
