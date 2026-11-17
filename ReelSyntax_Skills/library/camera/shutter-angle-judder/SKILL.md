---
name: shutter-angle-judder
description: "Use for shutter angle and pan judder validation. Enforce 180-degree shutter exposure math and maximum per-frame screen displacement at 24/25/30 fps."
metadata:
  category: camera
  stage: review
  status: guidance
  version: "2.0.0"
  aliases: "shutter angle,pan judder,180 derece obtüratör,titreme kontrolü"
  requires: ""
---

# Shutter Angle Judder

## Activation
Use when planning horizontal/vertical camera pans, fast typography scrolls, or reviewing 24/25/30 fps renders for stroboscopic edge judder. Search aliases: shutter angle,pan judder,180 derece obtüratör,titreme kontrolü.

## Inputs and output
- Inputs: Rational frame rate, horizontal FOV or pixel travel distance, shutter angle (degrees), and contrast ratio of moving edges.
- Output: Per-frame screen-fraction displacement report and motion-blur / timing adjustment recommendation.
- Required capability: No external engine required for analytical audit.
- Evidence bundle: Measured displacement in pixels/frame and frames-per-screen-width traversal time.

## Production recipe
1. Compute exposure time from shutter angle $\theta$: $t_{\text{exp}} = (\theta / 360^\circ) \cdot (1 / \text{fps})$. Standard cinema cadence uses $\theta = 180^\circ$ ($1/48\text{ s}$ at $24\text{ fps}$); crisp product graphics often use $90^\circ\text{–}144^\circ$.
2. Enforce the ASC screen-traversal rule on high-contrast unblurred edges: an object or background vertical edge should take at least $7\text{ seconds}$ ($168\text{ frames}$ at $24\text{ fps}$, $\le 0.6\%$ screen width per frame) to cross the full frame width, or cross in $< 8\text{ frames}$ as a deliberate whip-pan.
3. Avoid the strobing danger zone ($1.2\%\text{–}4.5\%$ frame width per frame at $24\text{ fps}$ without directional blur).
4. For vertical credit rolls or kinetic subheadings without motion blur, quantize per-frame pixel velocity to an integer multiple of pixels/frame to eliminate sub-pixel aliasing shimmer.

## Acceptance criteria
- Pan speed stays outside the stroboscopic judder band or applies commensurate directional motion blur.
- Integer-pixel scroll quantization verified when crisp unblurred type translates continuously.
- Record concrete frame interval, pixels/frame displacement, shutter setting, and review verdict.

## Failure and repair
Either lengthen pan duration, widen focal length, add physically weighted ease-in/out holds, enable directional motion blur matching $\theta = 180^\circ$, or switch intentional UI demos to $60\text{ fps}$ when delivery specs permit.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric.
- [FFmpeg tblend / minterpolate](https://ffmpeg.org/ffmpeg-filters.html)

Original production guidance.
