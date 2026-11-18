---
title: ReelSyntax
hide:
  - navigation
  - toc
---

<div class="rs-hero" markdown>

<span class="rs-badge">Pre-release 0.1.0</span>

<p class="rs-eyebrow">Local · Deterministic · Frame-accurate</p>

# Video as a project file

<p class="rs-lead">Render a frame-based video project locally, review the encoded master and deliver it as a video, a still or an editor timeline. Renderers run on your machine. The Python core has no required third-party dependencies.</p>

<div class="rs-actions">
  <a class="rs-btn rs-btn--primary" href="getting-started/">Getting started</a>
  <a class="rs-btn rs-btn--ghost" href="delivery/">Authoring and delivery</a>
  <a class="rs-btn rs-btn--ghost" href="https://github.com/Remirdy/ReelSyntax">View on GitHub</a>
</div>

```sh
reelsyntax init ./my-film
reelsyntax render ./my-film --profile draft
reelsyntax qc ./my-film --profile draft --html
```

</div>

## What you get

<div class="rs-grid" markdown>

<div class="rs-card" markdown>
### A validated project
A `reel.json` with canonical rational FPS, a frame plan and a schema. Invalid projects fail before anything renders.
</div>

<div class="rs-card" markdown>
### Local renderers
Pillow, Chromium, Blender and FFmpeg, discovered on your machine. Runtime commands never download software or contact remote services.
</div>

<div class="rs-card" markdown>
### Objective QC
FFprobe stream contracts, full decode, frame cadence, black, freeze and silence intervals, loudness and contrast. Technical pass never replaces a human review.
</div>

<div class="rs-card" markdown>
### Cached and resumable
Content-addressed scene caches, `resume` recovery, checkpoints and protected pixel regions keep long renders repeatable.
</div>

<div class="rs-card" markdown>
### Editor interchange
Export OTIO, FCPXML and Premiere XML. See [runtime coverage](runtime-coverage.md) for what is tested and what is not.
</div>

<div class="rs-card" markdown>
### Agent-ready
A unified MCP gateway routes across a searchable skill catalog, BlenderMCP and AfterEffectsMCP without loading every tool schema.
</div>

</div>

## Example gallery

<div class="rs-gallery" markdown>

<figure markdown>
![Aperture optical study](media/aperture.gif)
<figcaption>Aperture · native Blender Cycles</figcaption>
</figure>

<figure markdown>
![Cinematic study](media/cinematic-study.gif)
<figcaption>Cinematic study · cassette</figcaption>
</figure>

<figure markdown>
![Editorial study](media/editorial-study.gif)
<figcaption>Editorial study · footage and layers</figcaption>
</figure>

<figure markdown>
![Shader study](media/shader-study.gif)
<figcaption>Shader study · offline WebGL2</figcaption>
</figure>

</div>

## Where next

- [Installation](installation.md), then [create and render a project](delivery.md).
- Browse the [skill catalog](catalog.md) or use the site search.
- Read the [quality report](quality.md) and the [project format](project-format.md).
- Something broken? See [troubleshooting](troubleshooting.md).
