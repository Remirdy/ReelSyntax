---
name: ken-burns-photo-choreography
description: "Animate sub-pixel pan-and-scale trajectories over still photographs with overscan resolution checks, focal-point protection, and alternating motion vectors."
metadata:
  category: motion
  stage: build
  status: validated
  version: "2.0.0"
  aliases: "ken burns photo,photo pan zoom,fotoğraf kaydırma yakınlaştırma,hareketli fotoğraf kurgusu,Ken-Burns-Kamerafahrt,Foto-Zoomfahrt,efecto ken burns,mouvement ken burns"
  requires: ""
---

# Ken Burns Photo Choreography

## Activation
Activate when animating still photographs, archival scans, or static artwork plates in slideshows, documentaries, and retrospectives so stills breathe cinematically without pixel shimmer or cropped faces. Search aliases: `ken burns photo`, `fotoğraf kaydırma yakınlaştırma`, `Ken-Burns-Kamerafahrt`. Do not activate when `constraints.camera_locked` or `--reduced-motion` is active.

## Decision rules
- **Sub-pixel resampling mandatory**: never quantize per-frame crop offsets `(x, y, w, h)` to integers before scaling — integer pixel stepping produces visible staircase jitter at slow speeds (`0.5–1.5 px/frame`). Sample continuously using floating-point affine/bicubic/Lanczos resampling.
- **Source overscan verification**: if `zoom_end = Z` (for example `1.12`), verify source image short edge `>= target_render_edge * Z` (`>= 1210 px` for `1080p`); if source is smaller, cap `Z <= max(1.03, source_edge / target_edge)` to prevent upscaling blur.
- **Velocity ceiling (`judder` guard)**: keep pan speed `<= 0.035 * canvas_width` per second (`<= 1.25 px/frame` at `1080p30`) and scale rate `<= 0.045 / s` (`1.00 -> 1.12` over `2.7s`).
- **Vector alternation**: alternate consecutive slide trajectories (`push-in -> pull-out -> gentle drift right -> push-in`) so adjacent cross-dissolves never fight opposite high-speed vectors or repeat monotonous zoom-ins.

## Parameters and defaults
- `scale_start` / `scale_end`: `1.00 -> 1.10` (`push_in`) or `1.10 -> 1.00` (`pull_out`).
- `max_pan_norm`: `0.06` normalized canvas width across a `2.5s–3.5s` slide.
- `easing_curve`: linear across cross-dissolve handles (`first/last 12 frames`) so motion never stops dead mid-dissolve, or gentle `sine_in_out` on hard-cut slides.
- `exif_transpose_first`: `true` (apply EXIF orientation transpose before computing crop anchors).

## Procedure
1. Normalize orientation (`exif_transpose`) and check source pixel dimensions against `target_size * scale_max`.
2. Locate the photograph's primary focal anchor `(fx, fy)` (faces, horizon subject, or center `(0.5, 0.5)`) and verify `(fx, fy)` stays inside `[0.22, 0.78]` at both `t = 0` and `t = 1`.
3. Choose motion trajectory alternating across sequence index (`i % 4`: `push_in`, `pull_out`, `pan_right_push`, `pan_left_pull`), keeping velocity linear through any incoming/outgoing `cross_dissolve` overlap.
4. Interpolate scale logarithmically (`s(t) = s0 * (s1 / s0)^t`) so perceived optical zoom speed stays constant from frame 0 to `N-1`, resampling with sub-pixel Lanczos/bicubic filtering.
5. Check rendered output for shimmer on fine architectural lines (apply `0.35 px` pre-filter Gaussian if `> 2.5x` downscale causes moiré).

## Failure modes and fixes
- **Staircase judder on slow zoom**: switch from integer `crop(int(x0), int(y0), ...)` to floating-point `Image.Transform.EXTENT` (`BICUBIC`) or shader UV interpolation, and use logarithmic scale `s0 * (s1/s0)^t`.
- **Slide freezes mid-dissolve**: use linear `t` across the full clip including dissolve handles instead of easing to zero velocity before the dissolve completes.
- **Moiré shimmer on brick/fabric in 4000px photo**: pre-downsample once to `~1.5x` target resolution with `LANCZOS` before per-frame sub-pixel `BICUBIC` crop.

## Checklist
- [ ] EXIF orientation is normalized before computing focal bounds.
- [ ] Source resolution supports `scale_max` without blurry upscaling (`source >= target * scale_max`).
- [ ] Per-frame crop uses floating-point sub-pixel resampling + logarithmic zoom `s0 * (s1/s0)^t`.
- [ ] Motion stays continuous across dissolve handles and alternates direction across slides.

## Worked examples
- **Example 1 (`90` frames / `3.0s` slide with `10f` dissolves at `1080x1920`, EN)**: `2400x3600` portrait photo, face anchor `(0.50, 0.36)`. Pre-downsample to `1620x2430` (`LANCZOS`), animate logarithmic `scale` `1.00 -> 1.10` centered on `(0.50, 0.38)` via `Transform.EXTENT` (`BICUBIC`) with linear `t = f / 89` so dissolve frames `0..9` and `80..89` glide seamlessly.
- **Example 2 (Low-res `960x1200` archival scan on `1080x1350` canvas, DE)**: Source is `< 1.0x` target height -> frame inside a `0.82` editorial matte border (`885x1107` inner plate) and limit `scale` to `1.00 -> 1.04` so zero blur is introduced.

## Resources (load only if needed)
- [Logarithmic zoom and sub-pixel extent math](references/subpixel-pan-math.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
