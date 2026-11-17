# Changelog

## 0.1.0 — Unreleased

- Add preview/apply scene edit transactions, explicit audio anchoring, original-source backups and reversible undo protected by plan hashes, approval locks and the shared render/cache mutex.
- Fix CRLF skill frontmatter parsing while retaining byte-exact integrity checks; stabilize checkout line endings and UTF-8 CLI output across operating systems.
- Configure FFmpeg installation for the disposable CI media runner, correct optional App-token workflow conditions, and pin official Actions to Node 24 revisions.
- Add local footage trimming, normal-alpha raster layer stacks, bounded optional PSD raster extraction, and independently timed source audio with J/L cuts, fades, pan and source stems.
- Add source asset integrity checks, delivery-protected LRU cache pruning and optional post-delivery disk budgets.
- Add capability-probed offline WebGL2 SDF rendering and native Blender Video Sequencer export with saved-project reopen and frame preview.
- Correct editorial master exports: Draft dimensions, absolute encoded media URIs, source-relative markers, OTIO fractional-rate precision, baked-transition metadata and embedded-audio fallback; reject stale render manifests, unknown profiles and out-of-range SVG frames.
- Enforce published MCP meta-tool input types, nullability, nested schemas and bounds before dispatch; add an explicit project workspace boundary and bounded, recoverable stdio parsing.
- Add native Blender 5.1+ Cycles `aperture` optical-mechanism recipe (`reelsyntax/blender_aperture.py`) and 4-shot `examples/aperture-film` study (`macro`, `iris`, `assembly`, `hero`) with AR meniscus optics, quad-strip 11-blade iris geometry, Metal GPU Cycles rendering, `hero-shot-study.png` plates, SVG schematic export, and per-shot hold-keyframed After Effects 3D camera handoff.
- Exclude generated state, outputs and review files from source packages for every example project, including cinematic studies.

- Integrated the Production v2 specialist pack and expanded the catalog to 517 unique, non-overlapping skills across 25 categories with metadata index v2, SHA-256 integrity checks, dependency/conflict graphs, Turkish/English stemming, negation and audio-drone disambiguation, cumulative session budgets, and a 50-case routing benchmark.
- Added `integrations/BlenderMCP` (`Remirdy/BlenderMCP`) and `integrations/AfterEffectsMCP` (`Remirdy/AfterEffectsMCP`) as independent Git submodules behind a Unified MCP Gateway (`reelsyntax mcp`) exposing 9 progressive meta-tools, `blender:*` and `after_effects:*` namespacing, lazy schema loading, schema-diff auditing, and automated GitHub Actions synchronization (`.github/workflows/sync-submodules.yml`).
- Added deterministic production modules for OKLab/AgX color science, second-order mass-spring-damper camera rigs, Verlet physics ribbons, TrueType typography with `.notdef` glyph coverage and WCAG contrast verification, headless Blender 3.6–5.x CLI rendering with `--fallback`, multi-stem stereo procedural audio, cross-dissolve/wipe transitions, lossless ROI pixel locks, profile `diff` sheets, and `.otio` / `.fcpxml` / `.vtt` / `.srt` / `.svg` exports.
- Fixed browser renderer readiness/draw hang isolation via a dedicated process-group worker, fixed H.264 VUI and MP4 `bt709` color tag preservation across stream-copy muxing, and added verified router installation support for Codex, Antigravity, Claude Code, and Cursor.
