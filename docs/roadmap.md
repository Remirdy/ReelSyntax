# Roadmap

ReelSyntax ships only commands and engines verified in its runtime while maintaining the [indexed production skills](../ReelSyntax_Skills/CATALOG.md) and first-party submodules (`integrations/BlenderMCP`, `integrations/AfterEffectsMCP`).

## Delivered in 0.1.0

- Skill routing with metadata search, localized aliases, context budgets and opt-in references. See the [catalog](../ReelSyntax_Skills/CATALOG.md) for effective statuses.
- Project validation, local editor schema, source-media and procedural renderers, cache reuse and technical QC.
- Templates, queue jobs, locale and aspect variants, source retiming, selected PSD compositing, opt-in tone mapping and nested master compositions.
- GIF, poster, WebM, captions, Blender VSE, OTIO, FCPXML and Premiere XML delivery.
- A progressive MCP gateway and a desktop bundle. BlenderMCP and AfterEffectsMCP remain independent integrations.
- Local checks for custom GLSL and browser bundles, plus a one-minute static UHD resource measurement.

## Further verification

| Area | Next evidence |
| --- | --- |
| Editing applications | Open the exported timelines in Final Cut Pro, Premiere Pro and Resolve and record import logs and source ranges. |
| Rendering | Compare custom shaders and bundled Three.js scenes on additional GPU drivers. Measure cache growth with moving UHD footage. |
| Compositing | Add fixtures for PSD vector masks, adjustment layers, grouped blending and grade comparisons on HDR source material. |
| Integrations | Verify the interactive Blender bridge and After Effects workflow on supported application versions. |
| Routing | Collect independent search cases and verify native activation in host sessions. |
