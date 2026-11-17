---
name: remirdy-blender-nodes
description: "Use for first-party Remirdy BlenderMCP declarative scenes and node graphs. Build, inspect, and animate Geometry Nodes, Shader Nodes, and Compositor graphs over the validated Remirdy Blender bridge."
metadata:
  category: engines
  stage: build
  status: validated
  version: "2.0.0"
  aliases: "remirdy blender,blender node graph,procedural shader geometry,blender bridge"
  requires: "blender-mcp"
---

# Remirdy Blender Nodes

## Activation
Use as the preferred first-party workflow whenever building procedural 3D geometry, PBR shader graphs, compositor looks, or keyframed 3D shots through `Remirdy/BlenderMCP` (`remirdy-blender-studio-mcp`). Never substitute third-party Blender MCP servers that expose raw arbitrary Python execution. Search aliases: remirdy blender,blender node graph,procedural shader geometry,blender bridge.

## Inputs and output
- Inputs: Shot brief, target objects/materials, declarative node/link specification, frame range, and active constraints (`offline`, `no_paid_services`, `camera_locked`).
- Output: Verified Blender scene state, inspected node graph JSON, `.glb`/`.fbx`/`.blend` exports, or rendered frames.
- Required capability: blender-mcp
- Evidence bundle: `blender:get_blender_status` / `blender:inspect_node_graph` readback, `blender:scene_quality_check` report, and exported file digests.

## Production recipe
1. Probe connection via `blender:connect_blender` (default `127.0.0.1:8765`). If Blender's GUI bridge is not running, fall back cleanly to ReelSyntax's headless Blender CLI engine (`reelsyntax render --fallback pillow` or `engine: "blender"`) without faking live bridge execution.
2. Enforce ReelSyntax hard exclusions: never call `comfyui_*`, `multi_llm_*`, `browser_*` web-image scrapers, or paid cloud 3D providers (`MESHY`, `TRIPO`, `RODIN`) when `offline` or `no_paid_services` is active; use local procedural ops (`create_scene_from_prompt`, `build_geometry_node_graph`, `build_shader_node_graph`, `create_model_from_image`).
3. Push an undo point via `blender:checkpoint` before structural edits, construct node trees declaratively (`GeometryNode*`, `ShaderNode*`, `CompositorNode*`), and immediately read back state via `blender:inspect_node_graph` and `blender:get_scene_summary`.
4. Animate procedural parameters with `blender:animate_node_input` or transforms with `blender:keyframe_object` (respecting `camera_locked`!), run `blender:scene_quality_check`, and verify actual output files inside `REMIRDY_WORKSPACE/outputs/`.

## Acceptance criteria
- Node graph readback confirms zero skipped links; `scene_quality_check` passes scale/origin/material checks; exported `.glb`/`.png` exists and decodes cleanly.
- Distinguish live TCP bridge execution from headless `blender --background` CLI execution and mock/unit stub tests.

## Failure and repair
On unknown op or socket mismatch, inspect `inspect_node_graph` socket names (Blender 4.x/5.x `ng.interface` vs 3.x `ng.inputs`), `blender:undo` to the prior checkpoint, and re-apply corrected links.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric.
- [Remirdy BlenderMCP](https://github.com/Remirdy/BlenderMCP)
- [Blender Python API](https://docs.blender.org/api/current/)

First-party Remirdy ecosystem integration skill.
