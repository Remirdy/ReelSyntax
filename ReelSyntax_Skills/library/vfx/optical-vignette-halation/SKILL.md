---
name: optical-vignette-halation
description: "Apply subtle natural-lens peripheral falloff and thresholded warm highlight halation in linear light without crushing corners or reducing caption contrast."
metadata:
  category: vfx
  stage: render
  status: validated
  version: "2.0.0"
  aliases: "optical vignette,halation and vignette,optik vinyet ve halasyon,kenar karartma ve ışık halesi,optische Vignettierung,Lichtsaum und Randabfall,viñeteo óptico y halación,vignettage optique et halation"
  requires: ""
---

# Optical Vignette Halation

## Activation
Activate during compositing or shader lookdev (`cinematic-3d`, `retro-lowpoly-cutscene`, `photo-slideshow`, `loop-art`) when clean digital renders look overly clinical and benefit from subtle optical lens falloff and highlight bloom/halation. Search aliases: `optical vignette`, `optik vinyet ve halasyon`, `optische Vignettierung`. Do not apply over flat UI tutorials or on top of burned-in typography layers.

## Decision rules
- **Composite order lock (below typography)**: always apply vignette and halation to the *pictorial scene plate* **before** compositing foreground captions, lower-thirds, or data labels so text luminance and edge crispness never degrade.
- **Natural `cos^4(theta)` falloff in linear light**: compute peripheral falloff in linear light (`I_out = I_lin * cos^4(k * r)`) with corner attenuation capped at `<= 22%` (`k <= 0.42`), plus `+-1/255` triangular dither before 8-bit quantization to prevent circular banding rings.
- **Thresholded red-shifted halation**: trigger halation only on specular/emissive pixels above `L_lin >= 0.82`, blurring predominantly in the red-amber channel (`weights = [1.0, 0.38, 0.08]`, radius `0.008w–0.018w`) and adding at `gain <= 0.14` so midtones never turn muddy.
- **`blackdetect` corner guard**: verify vignetted dark scenes keep frame-mean and `pix_th=0.10` black coverage safely below FFmpeg `blackdetect` triggers (`Y_corner >= 22/255`).

## Parameters and defaults
- `vignette_strength_k`: `0.34` (range `0.20–0.42`; `0.34` yields `~15%` linear corner darkening).
- `aspect_normalized_radius`: `r = hypot((uv.x - 0.5) * aspect_x, (uv.y - 0.5) * aspect_y)` using equidistant diagonal normalization `hypot(0.5, 0.5) = 0.7071`.
- `halation_threshold_lin`: `0.85` linear luminance.
- `halation_radius_norm`: `0.012` of canvas short edge (`~13 px` at `1080p`).
- `halation_gain`: `0.10` (`<= 0.14` ceiling).
- `output_dither_lsb`: `1.0` LSB deterministic blue/hash dither before 8-bit `yuv420p` encode.

## Procedure
1. Convert the rendered background/3D plate from sRGB to linear light (`c_lin`) prior to optical filtering; keep UI/caption overlays in a separate top pass.
2. Extract bright-pass `max(0.0, luminance(c_lin) - halation_threshold_lin)`, blur with separable Gaussian (`radius = halation_radius_norm * min(w, h)`), tint by `[1.0, 0.38, 0.08]`, and add `halation_gain * blurred` in linear light.
3. Multiply by `pow(cos(vignette_strength_k * r_diag), 4.0)` so center `55%` of the frame stays virtually untouched while corners gently focus the eye inward.
4. Apply tone-map / sRGB transfer + deterministic `1`-LSB dither so smooth corner gradients show zero `8`-bit Mach banding after H.264 compression.
5. Composite crisp foreground text/HUD on top and run `qc` (`contrast == pass`, `black == pass`).

## Failure modes and fixes
- **Heavy black oval tunnel (`> 45%` corner drop)**: looks like a cheap photo filter and trips `blackdetect`; cut `vignette_strength_k` to `<= 0.36`.
- **Concentric banding rings on dark gradient after H.264 encode**: compute falloff in float32 linear space and add deterministic `+-0.5..1.0 / 255` dither before uint8 conversion.
- **Glowing captions look blurry**: move halation pass underneath the text composite layer, or lower text luminance below `halation_threshold_lin`.

## Checklist
- [ ] Vignette and halation execute in float linear light *below* foreground typography.
- [ ] Corner falloff stays `<= 22%` (`k <= 0.42`) and clears `blackdetect` (`Y_corner >= 22`).
- [ ] Halation is thresholded (`L_lin >= 0.82`) and subtle (`gain <= 0.14`) so midtones stay crisp.
- [ ] Deterministic `1`-LSB dither prevents 8-bit gradient banding on smooth dark plates.

## Worked examples
- **Example 1 (`1920x1080` low-poly night lantern scene)**: Lantern emissive `L_lin = 1.6` triggers warm `13 px` halation (`gain = 0.11`), `k = 0.34` vignette gently pulls corners from `Y = 48` to `Y = 41` (above `blackdetect`), deterministic hash dither applied, crisp subtitle overlaid last (`contrast = 11.4:1`).
- **Example 2 (`1080x1920` bright editorial slideshow)**: `k = 0.24` (`~8%` subtle corner framing), `halation_gain = 0.0` (disabled on bright graphic cards where bloom adds zero value).

## Resources (load only if needed)
- [Linear-light cos^4 vignette and halation shader reference](references/cos4-and-halation-shader.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
