---
name: chroma-subsampling-text-guard
description: "Prevent 4:2:0 (yuv420p) chroma subsampling fringing on colored typography and UI badges by enforcing luminance contrast floors, even-pixel alignment, and stroke minimums."
metadata:
  category: delivery
  stage: export
  status: validated
  version: "2.0.0"
  aliases: "chroma subsampling text guard,yuv420p colored text fix,kroma alt örnekleme metin koruması,renkli yazı kenar dağılması önleme,Chroma-Subsampling-Textschutz,Farbsäume bei 4:2:0-Text vermeiden,protección de texto en submuestreo croma,protection du texte en sous-échantillonnage chroma"
  requires: "ffmpeg"
---

# Chroma Subsampling Text Guard

## Activation
Activate whenever encoding H.264/H.265/WebM deliverables in standard `yuv420p` (`4:2:0` chroma subsampling required for universal browser and mobile hardware decode) that contain colored headlines, red/magenta/blue badges, or terminal syntax highlighting. Search aliases: `chroma subsampling text guard`, `kroma alt örnekleme metin koruması`, `Chroma-Subsampling-Textschutz`. Requires `ffmpeg`.

## Decision rules
- **Why pure chroma contrast fails in `4:2:0`**: `yuv420p` stores full-resolution luma `Y` (`1920x1080`) but **quarter-resolution** chroma `Cb, Cr` (`960x540`); saturated red `#EF4444` (`Y ≈ 89`) on mid-dark grey `#4B5563` (`Y ≈ 84`) has almost zero `Y` difference (`|ΔY| = 5`!), so `2x2` chroma averaging blurs every glyph stem into illegible blocky fringe!
- **Mandatory BT.709 `|ΔY|` luma separation**: in addition to WCAG contrast `>= 4.5:1`, require `|Y_fg - Y_bg| >= 85` (8-bit `0..255`, where `Y = 0.2126 R + 0.7152 G + 0.0722 B`) for any text `< 48 px` encoded as `yuv420p`!
- **Desaturate glyphs slightly or put high chroma in the pill, not thin stems**: instead of `#FF0033` thin text on `#111827`, render crisp near-white `#FFF1F2` text (`Y = 244`) inside a `#BE123C` crimson pill (`Y = 54`, `|ΔY| = 190`!) — full-resolution `Y` carries `100%` of the glyph edge sharpness!
- **High-quality chroma downsampler flags**: pass `-sws_flags lanczos+accurate_rnd+full_chroma_int` when converting RGB frames to `yuv420p` in FFmpeg so `Cb/Cr` downsampling avoids coarse nearest-neighbor stair-stepping, and reserve `yuv444p` strictly for archival/pro mezzanine masters (`mov-master`), never web `.mp4` (since mobile/Safari hardware decoders reject H.264 `yuv444p`!).

## Parameters and defaults
- `web_pixel_format`: `"yuv420p"` (mandatory for universal H.264 `high` profile playback; verify target player matrix if considering `yuv444p`).
- `min_luma_delta_8bit`: `85` (`|Y_fg - Y_bg|` on `0..255` BT.709 scale for text `< 48 px`).
- `max_small_text_oklch_c`: `0.13` on text `< 36 px` (use bright pastel tints `#FDA4AF`, `#7DD3FC`, `#86EFAC` rather than deep pure primaries `#FF0000`, `#0000FF`).
- `ffmpeg_sws_flags`: `"lanczos+accurate_rnd+full_chroma_int"`.

## Procedure
1. Compute BT.709 `Y = 0.2126 * R + 0.7152 * G + 0.0722 * B` for every foreground text ink and its immediate backing surface (`ground` or `pill`).
2. Flag any text `< 48 px` with `|Y_fg - Y_bg| < 85` or pure saturated red/blue (`OKLCH C > 0.16`) over dark ground.
3. Repair flagged pairs either by lifting glyph lightness into a luminous tint (`#FCA5A5` / `#FDE047` / `#F8FAFC`) OR inverting so `#F8FAFC` white glyphs sit inside the colored accent badge (`#DC2626` / `#2563EB`).
4. Align solid colored badge rectangles to **even** `(2*x, 2*y)` pixel coordinates so `2x2` `yuv420p` macro-pixel boundaries never straddle badge edges by `1` odd pixel.
5. Encode `yuv420p` with `-sws_flags lanczos+accurate_rnd+full_chroma_int -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv` and inspect decoded `200%` crop on colored glyphs.

## Failure modes and fixes
- **Red warning text (`#DC2626` on `#1E293B`) looks fuzzy and dark after `.mp4` encode**: swap to `#F8FAFC` white text inside a `#B91C1C` even-pixel-aligned pill (`|ΔY|` jumps from `32` to `188` — razor-sharp in `yuv420p`!).
- **Switching web `.mp4` to `-pix_fmt yuv444p` breaks playback on iOS/browsers**: keep `-pix_fmt yuv420p` for web `.mp4` and fix luma contrast + `sws_flags` instead!
- **Code syntax highlighting uses dark blue `#1D4ED8` keywords on `#0F172A` terminal**: lift syntax token palette to luminous sky `#7DD3FC` (`Y = 197` vs `Y = 22`, `|ΔY| = 175`).

## Checklist
- [ ] All text `< 48 px` clears `|ΔY| >= 85` (BT.709 `0..255` luma difference) in addition to WCAG contrast.
- [ ] High-chroma brand/alert colors sit in even-pixel-aligned backing pills behind white/dark ink rather than thin `< 36 px` glyph stems.
- [ ] Web `.mp4` retains universal `yuv420p` compatibility with `lanczos+accurate_rnd+full_chroma_int` scaling.
- [ ] Decoded `.mp4` frames show crisp un-smeared glyph counters at `1:1` pixel inspection.

## Worked examples
- **Example 1 (`code-highlighting` terminal palette upgrade for `yuv420p`)**: Background `#1E2430` (`Y = 36`). Replace muddy red `#EF4444` (`Y = 104`, `ΔY = 68` borderline) and royal blue `#2563EB` (`Y = 93`, `ΔY = 57` blurry!) with coral `#FDA4AF` (`Y = 186`, `ΔY = 150`) and sky `#7DD3FC` (`Y = 197`, `ΔY = 161`).
- **Example 2 (`news-ticker` `"LIVE"` / `"CANLI"` badge)**: Even-aligned rect `(80, 72, 196, 116)` filled `#DC2626` with `#F8FAFC` bold text (`|ΔY| = 169`), zero red bleed across `2x2` chroma blocks.

## Resources (load only if needed)
- [`yuv420p` luma-separation math and FFmpeg `swscale` flags](references/yuv420p-luminance-and-swscale-guide.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
