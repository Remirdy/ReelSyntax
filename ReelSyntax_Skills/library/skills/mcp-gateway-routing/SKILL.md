---
name: mcp-gateway-routing
description: "Use for Unified MCP Gateway routing and progressive tool discovery. Expose constant meta-tools, namespace blender:* and after_effects:* schemas lazily, and detect upstream tool schema drift."
metadata:
  category: skills
  stage: operate
  status: validated
  version: "2.0.0"
  aliases: "mcp gateway,progressive tool discovery,namespaced mcp tools,birleşik mcp geçidi"
  requires: ""
---

# Mcp Gateway Routing

## Activation
Use when configuring, querying, updating, or auditing ReelSyntax's Unified MCP Gateway across `integrations/BlenderMCP`, `integrations/AfterEffectsMCP`, and host coding agents (Codex, Antigravity, Claude Code, Cursor). Search aliases: mcp gateway,progressive tool discovery,namespaced mcp tools,birleşik mcp geçidi.

## Inputs and output
- Inputs: Host MCP request or CLI query, submodule capability index, active project constraints, and live downstream stdio servers.
- Output: Bounded namespaced tool shortlist (`blender:<tool>`, `after_effects:<tool>`), lazily fetched JSON schema for selected tool, validated call result, or schema-diff report.
- Required capability: Core `reelsyntax.gateway` and `reelsyntax.mcp_server`.
- Evidence bundle: Gateway capability digest, `tools/list` token footprint check, schema compatibility diff, and live vs simulated execution flag.

## Production recipe
1. Never inject all 570+ downstream MCP tool schemas (`BlenderMCP` + `AfterEffectsMCP`) into `tools/list`; expose only the constant, byte-stable ReelSyntax Gateway meta-tools (`reelsyntax:skills_*`, `gateway:search_tools`, `gateway:describe_tool`, `gateway:call_tool`, `reelsyntax:project_*`) so host LLM prompt caches stay warm and context consumption stays bounded.
2. Enforce strict hierarchical namespacing (`blender:<tool_name>`, `after_effects:<tool_name>`) to eliminate collisions such as `render_preview` (which exists on both `BlenderMCP` and `AfterEffectsMCP` with incompatible schemas!).
3. Run two-phase progressive schema promotion:
   - Phase 1 (`gateway:search_tools`): rank indexed capabilities by intent, stage, assets, and active skills; filter out `comfyui_*` and paid cloud generators when `offline` or `no_paid_services` is set.
   - Phase 2 (`gateway:describe_tool`): return the full `inputSchema` only for the chosen namespaced tool, then validate arguments before spawning/calling the downstream server on demand (`gateway:call_tool`).
4. On `reelsyntax update` or CI submodule synchronization, diff incoming `tools/list` snapshots against the last known working capability snapshot to classify **added**, **modified (breaking vs additive)**, and **removed** tools before advancing submodule pointers.

## Acceptance criteria
- Primary `tools/list` stays $\le 12$ meta-tools regardless of downstream catalog growth; name collisions (`blender:render_preview` vs `after_effects:render_preview`) resolve unambiguously.
- Uninitialized submodules degrade gracefully without breaking core ReelSyntax routing, validation, or local rendering.

## Failure and repair
If a downstream MCP server crashes or times out mid-call, terminate its process group, mark its session disconnected for clean lazy re-initialization on retry, and return an explicit structured error with available ReelSyntax fallbacks.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric.
- [Agent Skills Specification](https://agentskills.io/specification)

First-party Remirdy ecosystem gateway skill.
