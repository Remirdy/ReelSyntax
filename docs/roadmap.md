# Roadmap

ReelSyntax ships only commands and engines verified in its runtime while maintaining 517 specialist production skills and first-party submodules (`integrations/BlenderMCP`, `integrations/AfterEffectsMCP`).

## Completed in current milestone

1. **Baseline & Hero media gates**: Real H.264/48 kHz AAC BT.709 rendering, full decode, 10-microsecond timestamp cadence check, WCAG contrast & `.notdef` glyph coverage verification, cue-onset alignment, temporal continuity screening, selective scene cache hits, interrupted-job recovery, and Hero lookdev A/B + motion extrema sheets.
2. **Browser & Blender 5.x execution**: Subprocess-isolated Chromium Canvas renderer with hard readiness timeout + offline network block, and headless Blender 5.1.2 3D scene adapter with `AgX` color management and `--fallback pillow`.
3. **517-skill router & Antigravity/Codex/Claude/Cursor installer**: Systematic Turkish/English stemming, negation/drone disambiguation, dependency/conflict DAGs, cumulative session token budgets, `skills explain`, and 50-case benchmark (`top1: 98%+`, `no_match_error: 0%`, `violations: 0%`).
4. **First-party MCP submodules, Unified Gateway, and CI auto-sync**: `integrations/BlenderMCP` and `integrations/AfterEffectsMCP` Git submodules, 9-tool progressive stdio MCP Gateway (`reelsyntax mcp`), capability schema-diff detector (`sync_audit`), `install`/`update`/`capabilities`/`integrations`/`handoff`, and `.github/workflows/sync-submodules.yml`.
5. **Editorial interchange & ROI locks**: Zero-dependency `.otio`, `.fcpxml` (v1.10), `.vtt`, `.srt`, `.svg` exports, `diff` profile comparison sheets, multi-stem stereo procedural audio, and lossless `locked_regions` pixel verification.
6. **Local source media and layered ingest**: FFmpeg decoded-frame video trims, alpha raster layer stacks, bounded optional 8-bit RGB PSD layer extraction, asset-hash invalidation, and independently positioned stereo source tracks with J/L cuts, fades and WAV stems.
7. **WebGL2 shader path**: Capability-probed fixed-camera SDF sculpture inside the offline Chromium worker, deterministic seeks, Canvas/WebGL switching and driver evidence; no downloaded JavaScript framework.
8. **Disk cache budgets**: Shared operation lock, dry-run LRU pruning, delivery/state reference protection, and optional post-delivery cache budget.
9. **Native Blender editorial delivery**: Segmented flattened master in Video Sequencer, separately timed mix, markers, rational timing, `.blend` save/reopen and frame preview verification.
10. **Remote regression matrix**: All eight GitHub Checks jobs passed on the published source: Linux/macOS/Windows core tests on Python 3.11/3.14, Linux FFmpeg media checks and submodule audits. Optional GUI/GPU engines are separate gates.
11. **Scene edit transactions**: Preview/apply move/insert/duplicate/remove/update, explicit absolute or scene-following audio anchors, original-source backups, optimistic plan hashes and reversible snapshot undo. Render/cache/revision/approval operations share the project mutex. General split/slip/retiming and named picture/audio links remain deferred.

## Next engineering slices

1. **Upstream first-party PRs (upon owner authorization)**: Apply the documented `runner.ts` 2027/`aerender` discovery and JSON sidecar patch in `Remirdy/AfterEffectsMCP`, and the Blender 5.x `AgX`/rational `fps_base`/sequence-render patch in `Remirdy/BlenderMCP`.
2. **Richer editing and source support**: General nonlinear track/nested-composition model, retiming, advanced PSD masks/blend modes and HDR-to-SDR grading. Current ingest deliberately rejects unsupported compositing and HDR footage.
3. **More rendering adapters**: Three.js scene authoring, user-configurable shaders, more native recipes and hardware-specific visual validation. The bundled WebGL2 path is implemented; custom WebGL/Three.js code is not yet accepted.
4. **Wider application/hardware verification**: Long 4K disk/memory benchmarks; native Final Cut/Premiere/Resolve import checks and optional engine tests across more drivers. Core cross-platform CI is verified; Blender's native editorial file does not certify other editors.
5. **Interactive application bridges**: The latest local MCP probe could not reach Blender at `127.0.0.1:8765`; the After Effects project-info call timed out after 300 seconds. Headless render/export and static JSX validation remain independently verified. Desktop UI automation is excluded from this workflow.

This is an active pre-release roadmap, not a claim that the complete master product specification has shipped. Publishing a source commit is separate from releasing a package or opening upstream pull requests.
