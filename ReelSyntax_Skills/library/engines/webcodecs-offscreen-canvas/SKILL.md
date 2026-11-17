---
name: webcodecs-offscreen-canvas
description: "Use for headless OffscreenCanvas and WebCodecs frame synthesis. Render frame-indexed 2D/WebGL buffers with explicit microsecond timestamps and zero DOM layout overhead."
metadata:
  category: engines
  stage: render
  status: production-guidance
  version: "2.0.0"
  aliases: "webcodecs render,offscreencanvas,tarayıcı kare sentezi"
  requires: "browser"
---

# Webcodecs Offscreen Canvas

## Activation
Use when building high-throughput browser-rendered canvas/shader compositions where DOM screenshot serialization bottlenecks frame export. Search aliases: webcodecs render,offscreencanvas,tarayıcı kare sentezi.

## Inputs and output
- Inputs: Scene geometry/shader state, rational FPS, frame count, and offline headless Chromium context.
- Output: Exact frame sequence or encoded elementary stream with explicit presentation timestamps.
- Required capability: browser
- Evidence bundle: Browser version, readiness canary status, per-frame timestamp check, and decoded frame count.

## Production recipe
1. Launch headless Chromium inside an isolated worker with `chromium_sandbox=True`, `offline=True`, `service_workers='block'`, aborted network routes, and a hard readiness timeout.
2. Allocate an `OffscreenCanvas(width, height)` matching exact even output dimensions and verify local font ink via an alpha canary before starting the frame loop.
3. Step canonical frame index $f \in [0, N)$ explicitly; never use `requestAnimationFrame` or `performance.now()`. Compute microsecond timestamp $t_\mu = \text{round}(10^6 \cdot f \cdot \text{fps\_den} / \text{fps\_num})$.
4. When `VideoEncoder` is used, construct `new VideoFrame(canvas, { timestamp: t_mu, duration: d_mu })`, close every `VideoFrame` immediately after `encode()` to prevent GPU/shared-memory exhaustion, and `await encoder.flush()` before container muxing.

## Acceptance criteria
- Zero network requests permitted; deterministic pixel output on out-of-order frame seeks; zero leaked `VideoFrame` handles.
- Record browser version, frame count, cadence check, and fallback status if headless Chromium is unavailable.

## Failure and repair
If `VideoEncoder` lacks requested H.264 profile support in headless Chromium builds, export lossless PNG/raw RGBA frames from `OffscreenCanvas` and encode via local FFmpeg `libx264` with explicit BT.709 flags.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric.
- [Playwright Screenshots](https://playwright.dev/docs/screenshots)

Original production guidance.
