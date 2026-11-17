# Research and source map

Research date: 2026-11-17. Sources below were inspected through public search/open results, not cloned, installed or executed. The catalog contains independently written procedures; upstream links are domain-level starting points, not a claim that each exact skill exists upstream or each linked page was checked line-by-line. No upstream skill files, code or media are bundled. Recheck licenses and exact versions before any future import or integration.

| Source | How it informs the ReelSyntax system |
|---|---|
| [Agent Skills specification](https://agentskills.io/specification) | Portable skill structure, metadata-first progressive loading. |
| [OpenAI skills](https://developers.openai.com/codex/skills) / [OpenAI skill tooling](https://developers.openai.com/plugins/concepts/skills) | Host skills as reusable instructions and tool orchestration. |
| [Claude Code skills](https://code.claude.com/docs/en/skills) | Discovery conventions and on-demand instruction access. |
| [Cursor skills](https://cursor.com/docs/skills) | Host discovery and packaging conventions. |
| [CineCode](https://github.com/sarpstar/cinecode) | Code-first filmmaking, creative planning, procedural media. |
| [OpenMontage](https://github.com/OpenMontageInc/OpenMontage) | Large multidisciplinary production knowledge ecosystem; compare workflow breadth without importing files. |
| [HyperFrames](https://github.com/heygen-com/hyperframes) | HTML compositions, frame-seekable motion, reusable production blocks. |
| [Video Shotcraft](https://github.com/Vincentwei1021/video-shotcraft) | Shot recipes, product demonstrations and motion preview methodology. |
| [Remotion skills](https://github.com/remotion-dev/skills) | Frame-driven composition references; verify Remotion usage terms independently. |
| [GSAP skills](https://github.com/greensock/gsap-skills) | Timeline and animation practices. |
| [Hypit](https://github.com/hypit-ai/hypit) | Word-anchored editing and variant workflows as research topics; no cloning or likeness replacement. |
| [Cinema skills](https://github.com/DenisHumen/cinema-skills) | Film craft, writing, continuity and finishing gaps. |
| [Vidmoat](https://github.com/vidmoat/skills) | Editing, pacing, audio and format-focused workflows. |
| [Awesome video skills](https://github.com/ella-wang-opus/awesome-video-skills) | Discovery leads for video specialist packs. |
| [Awesome agent video skills](https://github.com/clonn/awesome-agent-video-skills) | Broad repository discovery: directory claims 184 projects; not all individually reviewed. |
| [Awesome video editing](https://github.com/devanasolver/awesome-video-editing) | Editing tools and media rights research leads. |
| [24fps skills directory](https://24fps.dev/skills) | Motion, product films, explainers and postproduction discovery leads; directory claims 576 skills, not individually audited. |
| [Design skill catalog](https://github.com/podo/design-agent-skills) | Motion design and creative-coding discovery leads. |
| [FFmpeg filters](https://ffmpeg.org/ffmpeg-filters.html) | Media filters, composition, sound and quality verification. |
| [three.js documentation](https://threejs.org/docs/) | Geometry, camera, materials and frame-driven animation interfaces. |
| [MDN Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API) | Audio graph, synthesis and analysis. |
| [OpenTimelineIO](https://opentimelineio.readthedocs.io/en/latest/) | Editorial interchange; not a native media container. |
| [Manim Community](https://docs.manim.community/en/stable/) | Mathematical and scientific animation reference. |
| [Playwright screenshots](https://playwright.dev/docs/screenshots) | Controlled browser capture. |
| [WCAG 2.2](https://www.w3.org/TR/WCAG22/) | Accessibility reference, including contrast and flashing guidance; not a film certification. |
| [Blender Python API](https://docs.blender.org/api/current/) | Intended version-specific implementation reference; direct fetch blocked in this research session, so verify in development. |

**Open research tasks:** verify Antigravity's current directory and invocation mechanisms; inspect actual supported integration versions; inspect individual external repositories and license texts before adopting anything; extend the routing evaluation dataset beyond seed exact-phrase queries; implement and validate renderer fixtures. Never treat public availability as a permission to redistribute. The original MIT project must not silently incorporate AGPL or unlicensed source. Preserve compatible license notices where needed. No LTX, Wan or ComfyUI integration.

## v2 technical references examined

- [Agent Skills specification repository](https://github.com/agentskills/agentskills): staged discovery and activation; keep the specialist corpus outside automatic host discovery.
- [FFmpeg filters](https://ffmpeg.org/ffmpeg-filters.html): black, freeze, silence and loudness scanning; verify installed filter support.
- [EBU R128](https://tech.ebu.ch/publications/r128): broadcast loudness target; not a universal web-media target.
- [ACES output transforms](https://docs.acescentral.com/system-components/output-transforms/): working/display transform separation.
- [Three.js color management](https://threejs.org/manual/pages/color-management.html): distinguish color and data textures and working/display color space.
- [WCAG contrast minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html): contrast reference adapted as a readability heuristic, not film certification.
- [Animation principles overview](https://www.lafilm.edu/blog/history-and-use-12-principles-of-animation/): staging, anticipation, timing and follow-through.
- [Video Shotcraft public fork](https://github.com/syklayou-glitch/video-shotcraft): example of a recipe and motion-preview-oriented competitor. No source code or recipe copied.

This is a targeted research pass, not an exhaustive audit of all GitHub or every external source. The 500 technical recipes are independently authored. Individual engine APIs, production outcomes and license terms need further verification in the actual integration environment.

## Integrated ecosystem and v2.1 expansion (2026-11-17)

- Verified Antigravity workspace skill discovery (`.agents/skills/<name>/SKILL.md` with progressive `name` + `description` disclosure) against Antigravity's built-in `agy-customizations` documentation.
- Audited first-party [`Remirdy/BlenderMCP`](https://github.com/Remirdy/BlenderMCP) (303 live MCP tools, TCP operation registry, declarative node graphs) and [`Remirdy/AfterEffectsMCP`](https://github.com/Remirdy/AfterEffectsMCP) (270 live MCP tools, `ag-psd` visual analysis, ExtendScript generation, `jsx_dry_run`, hybrid VFX presets) and integrated both as Git submodules behind ReelSyntax's progressive MCP Gateway.
- Added 17 original specialist skills covering second-order camera inertia, shutter-angle pan judder, trauma-squared camera shake, AgX/ACES tone mapping, signed distance fields, Verlet constraint physics, variable fonts and tabular figures, OKLab/OKLCH perceptual palettes, headless WebCodecs/OffscreenCanvas, OpenUSD `.usda` stage assembly, EBU R128 dialogue gating, temporal flicker auditing, and first-party Remirdy MCP pipelines (`517` unique skills total).
