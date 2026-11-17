# First-party MCP ecosystem, submodules, and automatic synchronization

ReelSyntax integrates two first-party repositories maintained by the same owner as canonical creative production peers:

- `integrations/BlenderMCP` → [`Remirdy/BlenderMCP`](https://github.com/Remirdy/BlenderMCP) (`remirdy-blender-studio-mcp`, MIT, pinned at `bbbd1128dc16937fb5cc8ce56669f472cbb5dd68`)
- `integrations/AfterEffectsMCP` → [`Remirdy/AfterEffectsMCP`](https://github.com/Remirdy/AfterEffectsMCP) (`motionpilot-ae-mcp`, MIT, pinned at `498711d538c220f34e11bed84a67f29bcaf2990f`)

Both repositories remain completely independent Git submodules with their own commit histories, releases, and licenses. Their source code is not vendored into ReelSyntax packages (`MANIFEST.in` prunes `integrations/`). ReelSyntax remains functional when neither submodule is initialized.

## Unified MCP Gateway (`reelsyntax mcp`)

Host coding agents (Antigravity, Claude Code, Codex, Cursor) only need to register a single stdio MCP server:

```json
{
  "mcpServers": {
    "reelsyntax": {
      "command": "python3",
      "args": ["-m", "reelsyntax", "mcp", "--workspace", "/absolute/path/to/projects"],
      "cwd": "/absolute/path/to/ReelSyntax"
    }
  }
}
```

Set `--workspace` to an existing directory authorized for project access. Relative project paths resolve inside it. Project validate/plan/QC reject traversal, outside absolute paths and symlinks beneath that root. This boundary covers ReelSyntax project tools; downstream Blender/After Effects tools retain their own native filesystem and execution permissions.

Every meta-tool call is validated against its published input schema before dispatch. The shared validator checks types/nullability, nested containers, required/unknown properties, numeric and length bounds, enums, and `allOf`/`anyOf`/`oneOf`. It is a dependency-free subset, not a complete JSON Schema implementation: reference resolution, formats, regex patterns and conditional keywords remain downstream validation responsibilities.

Standard stdio uses UTF-8 newline-delimited JSON-RPC as described in the [MCP transport specification](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports). Existing `Content-Length` framing is retained as a compatibility extension. Input messages are limited to 1 MiB and compatibility headers to 8 KiB. Invalid JSON returns a parse error without dropping the next bounded message; invalid framing sizes or truncated frames close the stream safely.

Together, `BlenderMCP` (~303 tools) and `AfterEffectsMCP` (~270 tools) expose more than 570 tool definitions, including identically named tools with incompatible schemas such as `render_preview`. Eagerly exposing all 570+ schemas in `tools/list` wastes tens of thousands of prompt tokens and causes name collisions.

ReelSyntax's Unified MCP Gateway exposes a constant 9-tool meta-surface:

1. `reelsyntax_skills_search`, `reelsyntax_skills_get`, `reelsyntax_skills_explain` — progressive retrieval across 517+ production skills plus matching MCP tool summaries.
2. `gateway_search_tools` — progressive search returning concise `blender:<tool>` and `after_effects:<tool>` summaries without full JSON schemas.
3. `gateway_describe_tool` — lazy second-phase fetch returning the full JSON `inputSchema`, schema SHA-256, and compatible ReelSyntax skill IDs for a single selected namespaced tool.
4. `gateway_call_tool` — validates arguments against the discovered JSON schema and active project constraints (`offline`, `no_paid_services`, `no_text`), starts the target MCP server on demand, recovers automatically from transient child-process exits, and returns structured results.
5. `reelsyntax_project_validate`, `reelsyntax_project_plan`, `reelsyntax_project_qc` — scoped local project operations.

When `offline` or `no_paid_services` is enabled (the default), the gateway automatically blocks external generative/cloud tools (`comfyui_*`, `runway_*`, `generate_ai_*`, `multi_llm_*`, cloud image-to-3D) to preserve ReelSyntax's architectural boundaries.

## Local reuse, installation, and updates

```sh
python3 -m reelsyntax doctor --json
python3 -m reelsyntax integrations --json
python3 -m reelsyntax capabilities --refresh --limit 10
python3 -m reelsyntax install blender --dry-run
python3 -m reelsyntax install after-effects --dry-run
python3 -m reelsyntax install --all
python3 -m reelsyntax update --json
python3 -m reelsyntax update blender --apply
python3 -m reelsyntax update blender --rollback
```

`resolve_integration()` inspects explicit environment overrides (`REELSYNTAX_BLENDER_MCP_ROOT`, `REELSYNTAX_AE_MCP_ROOT`), initialized submodules under `integrations/`, and existing sibling checkouts before proposing any environment setup. When a compatible virtual environment or built `dist/index.js` already exists locally, `install` reuses it without redundant downloads.

## Coordinated Blender ↔ ReelSyntax ↔ After Effects handoff

`python3 -m reelsyntax handoff <project>` generates `output/interchange/interchange-manifest.json` and `after-effects-camera.jsx`:

- Locks exact rational frame rate (`num/den`) and total frame count across all three tools.
- Converts 3D camera optics from Blender/ReelSyntax right-handed Z-up world coordinates (`36.0 mm` horizontal full-frame sensor gate) into After Effects 3D camera zoom pixels (`width * focal_mm / 36.0`) and left-handed Y-down coordinates.
- Pre-hashes rendered video/WAV/pass files by SHA-256 and validates the generated ExtendScript camera script live through `after_effects:jsx_dry_run` when `AfterEffectsMCP` is available.

## Evidence-backed upstream improvement proposals

Source audit of both first-party repositories identified the following concrete upstream improvements (compensated locally in ReelSyntax's gateway adapter without modifying upstream repositories unrequested):

### `Remirdy/AfterEffectsMCP` (`498711d5`)
1. **Dynamic year & sibling `aerender` discovery (`src/ae/runner.ts:17-73`)**: `MAC_CANDIDATES` hardcodes `2026..2023` and checks `path.join(app, "Contents/aerender")`. On macOS with Adobe After Effects 2027, the app is `/Applications/Adobe After Effects 2027/Adobe After Effects 2027.app` and `aerender` sits alongside the bundle at `/Applications/Adobe After Effects 2027/aerender`. *Adapter compensation*: ReelSyntax globs `/Applications/Adobe After Effects*` in descending order and injects `AE_BINARY` and `AERENDER_BINARY` into `AfterEffectsMCP`'s environment. *Upstream fix*: replace `MAC_CANDIDATES`/`WIN_CANDIDATES` static years with descending directory globbing and check `path.join(path.dirname(app), "aerender")`.
2. **Portable MCP config path (`src/mcp/connector.ts:45`)**: Replace the hardcoded developer-home MCP configuration path with `path.join(os.homedir(), ".gemini/antigravity/mcp_config.json")` plus `REELSYNTAX_MCP_CONFIG` override.
3. **Structured JSON result sidecar (`src/ae/runner.ts:97-113`, `src/ae/jsxGenerator.ts:48-53`)**: Replace pipe-delimited `__result.ok + "|" + __result.output + "|" + __result.error` parsing with JSON serialization so pipe characters or multiline ExtendScript errors cannot corrupt parsing; escape quotes in macOS `osascript` `DoScriptFile` paths.
4. **Fail-closed missing Alembic check (`src/vfx/alembic.ts:23-33`)**: Return `{ ok: false, error: ... }` instead of writing `"MOCK_ALEMBIC_VDB_SIMULATION_DATA"` when `alembicPath` is absent. *Adapter compensation*: ReelSyntax's gateway rejects `after_effects:houdini_alembic_bridge` calls before dispatch if `alembicPath` does not exist on disk.
5. **Dedicated pass & camera rig tools**: Add `import_image_sequence_pass` (rational FPS, straight/premultiplied alpha mode, linear/BT.709 interpretation) and `import_camera_rig_json` so multi-keyframe 3D camera tracks do not require custom `execute_after_effects_actions` batches.

### `Remirdy/BlenderMCP` (`bbbd1128`)
1. **Blender 4.x/5.x dynamic engine & OCIO `AgX` detection (`blender_addon/blender_ops/render_ops.py:170-190`)**: Static `bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items` omits `CYCLES` in Blender 5.1, and static `ColorManagedViewSettings.bl_rna` omits dynamic OpenColorIO views (`AgX`, `Filmic`), causing fallback to `BLENDER_EEVEE` + `Standard`. *Upstream fix*: assign `scene.render.engine = "CYCLES"` / `scene.view_settings.view_transform = "AgX"` inside `try/except TypeError` on the live `scene` instance (verified on Blender 5.1.2 in `reelsyntax/blender_engine.py`).
2. **Rational frame rate `fps_base` (`blender_addon/blender_ops/animation_ops.py:225-233`)**: Add optional `fps_num` / `fps_base` parameters to `op_set_frame_range` so `24000/1001` and `30000/1001` timelines do not truncate to integers.
3. **Transparent RGBA / EXR frame-sequence render op (`blender_addon/blender_ops/render_ops.py`)**: Add `op_render_frame_sequence(start, end, format="PNG"|"OPEN_EXR_MULTILAYER", film_transparent=True, passes=[...])` alongside single-frame `render_final` and fixed `export_turntable_animation`.
4. **Camera lens & DOF animation allowlist (`blender_addon/blender_ops/animation_ops.py:39-42`)**: Allow keyframing `data.lens` and `data.dof.focus_distance` on `CAMERA` objects for dolly-zoom and rack-focus shots.
5. **Duplicate tool registration & explicit FastMCP version (`server/tools/agent_tools.py`, `server/mcp_server.py:83`)**: Remove the duplicate `create_ai_director_storyboard` registration in `agent_tools.py` and pass package version `0.2.0` to `FastMCP(...)` so `initialize` reports package version rather than MCP SDK version.

## Manual GitHub configuration for automatic synchronization

The repository includes `.github/workflows/sync-submodules.yml` and ready-to-copy upstream dispatch workflows in [`docs/upstream-workflows/`](upstream-workflows/):

1. **Create or select a GitHub App (recommended over personal PATs)**:
   - Install the GitHub App on `Remirdy/ReelSyntax`, `Remirdy/BlenderMCP`, and `Remirdy/AfterEffectsMCP`.
   - Repository permissions on `Remirdy/ReelSyntax`: **Contents: Read & write**, **Pull requests: Read & write**, **Issues: Read & write**, **Metadata: Read-only**.
2. **Add repository secrets on `Remirdy/ReelSyntax`**:
   - `SYNC_APP_ID` and `SYNC_APP_PRIVATE_KEY` (or fallback fine-grained token `SUBMODULE_SYNC_TOKEN` scoped only to `Remirdy/ReelSyntax` with Contents, Pull requests, and Issues read/write).
3. **Enable Auto-Merge and Branch Protection on `Remirdy/ReelSyntax`**:
   - Under **Settings → General → Pull Requests**, enable **Allow auto-merge** and **Automatically delete head branches**.
   - Under **Settings → Rules / Branches** for `main`, require pull requests and require status checks (`core`, `media`, `submodules` from `.github/workflows/check.yml`) to pass before merging.
4. **Optional instant `repository_dispatch` from upstream repos** (6-hour cron and manual `workflow_dispatch` already work without this step):
   - Copy `docs/upstream-workflows/BlenderMCP-notify-reelsyntax.yml` to `.github/workflows/notify-reelsyntax.yml` in `Remirdy/BlenderMCP` and `docs/upstream-workflows/AfterEffectsMCP-notify-reelsyntax.yml` to `.github/workflows/notify-reelsyntax.yml` in `Remirdy/AfterEffectsMCP` when authorized.
   - Add `REELSYNTAX_SYNC_APP_ID` + `REELSYNTAX_SYNC_APP_PRIVATE_KEY` (or `REELSYNTAX_DISPATCH_TOKEN` with `Contents: write` on `Remirdy/ReelSyntax`) to those two repositories' Actions secrets.
