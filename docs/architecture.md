# Runtime, submodule, and dependency boundaries

The core runtime uses Python 3.11+ and its standard library so skill routing, project validation, timeline interchange (`otio`, `fcpxml`, `vtt`, `srt`, `svg`), state ledgers, and the Unified MCP Gateway (`reelsyntax mcp`) require zero mandatory third-party packages.

Pillow, Playwright/Chromium, FFmpeg/FFprobe, Blender, and Adobe After Effects are optional rendering or compositing capabilities. Runtime commands never silently download software, fetch remote assets, or invoke paid APIs.

## Package and repository layout

- `reelsyntax`: CLI, project validation, rational timing, deterministic 2D/3D procedural rendering (`palette`, `motion`, `camera`, `lighting`, `typography`, `drawing`, `blender_engine`, `browser`), procedural multi-stem audio (`sound`), quality/diff inspection (`quality`, `diff`), editorial interchange (`interchange`), and the Unified MCP Gateway (`gateway`, `mcp_server`, `sync_audit`).
- `ReelSyntax_Skills`: 517 unique specialist skills (`library/`), metadata index v2 (`registry/index.json`), dependency/conflict/status graph (`registry/relations.json`), single host router entry (`.agents/skills/reelsyntax-router/SKILL.md`), and evaluation dataset (`tests/routing-eval.json`).
- `integrations/BlenderMCP` and `integrations/AfterEffectsMCP`: independent Git submodules pointing to `Remirdy/BlenderMCP` and `Remirdy/AfterEffectsMCP`. Their source trees are excluded from Python wheel/sdist builds, and ReelSyntax remains functional when neither submodule is initialized.

## Progressive disclosure across skills and MCP tools

1. **Skills**: All 517 specialist bodies remain outside native host discovery. Only `reelsyntax-router` is installed into `.agents/skills` (Codex, Antigravity), `.claude/skills` (Claude Code), or `.cursor/skills` (Cursor). Warm metadata searches open zero specialist bodies; body and resource loads are explicit, SHA-256 verified, and bounded by session token budgets.
2. **Unified MCP Gateway**: Instead of exposing 570+ downstream `BlenderMCP` and `AfterEffectsMCP` tool schemas in `tools/list`, `reelsyntax mcp` exposes 9 constant meta-tools (`gateway_search_tools` → `gateway_describe_tool` → `gateway_call_tool` plus scoped `reelsyntax_*` operations) with `blender:*` and `after_effects:*` namespacing, lazy server startup, schema validation, and automatic offline/paid-service filtering.
