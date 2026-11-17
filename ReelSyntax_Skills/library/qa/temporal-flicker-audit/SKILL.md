---
name: temporal-flicker-audit
description: "Use for temporal flicker and luminance pop detection. Scan decoded frames outside cut boundaries for single-frame exposure spikes, harsh clipping, and thin-line aliasing."
metadata:
  category: qa
  stage: review
  status: validated
  version: "2.0.0"
  aliases: "temporal flicker,kare titremesi,luminance pop,aliasing kontrolü"
  requires: ""
---

# Temporal Flicker Audit

## Activation
Use during technical and visual QA of rendered sequences to catch single-frame renderer glitches, unseeded noise flicker, highlight clipping spikes, or sub-pixel thin-line shimmer. Search aliases: temporal flicker,kare titremesi,luminance pop,aliasing kontrolü.

## Inputs and output
- Inputs: Rendered video or PNG sequence, scene cut boundary frame indices, and intentional flash/strobe exceptions.
- Output: Per-scene temporal luminance delta telemetry, outlier frame indices, and clipping ratio.
- Required capability: `reelsyntax.quality` frame inspector + FFmpeg/Pillow.
- Evidence bundle: Frame-to-frame $|\Delta Y|$ curve summary, flagged frames, and contact-sheet proof.

## Production recipe
1. Exclude declared hard-cut boundaries (`start_frame` of each scene after scene 0) from inter-frame delta spikes so intentional editorial cuts are never misclassified as glitches.
2. Compute mean Rec.709 luma $Y_f = 0.2126 R + 0.7152 G + 0.0722 B$ across sampled or contiguous frames within each shot.
3. Flag isolated single-frame pops where $|Y_f - \frac{1}{2}(Y_{f-1} + Y_{f+1})|$ exceeds local shot median step by $> 0.08$ normalized luma without matching an intentional flash exception.
4. Measure saturated pixel fraction ($R,G,B \ge 254$ or $\le 1$) to surface blown specular highlights or crushed shadow plateaus.
5. Check 1px–2px diagonal/horizontal strokes under slow motion with supersampling $\ge 2\times$ in `production` and `3\times` in `hero` profiles.

## Acceptance criteria
- Zero unexplained single-frame luma pops inside continuous shots; non-emissive clipping within declared threshold.
- Record checked frame count, max intra-shot $|\Delta Y|$, and status (`pass`, `review`, `fail`).

## Failure and repair
Single-frame pops usually trace to unseeded random calls, division-by-zero at normalized $u=0$ or $u=1$, or corrupt cached frames: seed deterministically from `(project.seed, frame)` and invalidate the affected scene cache.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric.
- [FFmpeg signalstats / deflicker](https://ffmpeg.org/ffmpeg-filters.html)

Original production guidance and validated runtime audit.
