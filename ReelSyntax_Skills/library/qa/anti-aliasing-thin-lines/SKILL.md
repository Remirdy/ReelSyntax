---
name: anti-aliasing-thin-lines
description: "Eliminate single-pixel line buzz, diagonal stair-stepping, and pan-induced moiré shimmer using minimum stroke floors, integer grid snapping, and 2x supersampling."
metadata:
  category: qa
  stage: render
  status: validated
  version: "2.0.0"
  aliases: "anti aliasing thin lines,thin stroke shimmer fix,ince çizgi kenar yumuşatma,titreyen ızgara çizgisi düzeltme,Kantenglättung dünner Linien,Flimmern feiner Linien beheben,antialiasing de líneas finas,anticrénelage des lignes fines"
  requires: ""
---

# Anti Aliasing Thin Lines

## Activation
Activate when rendering `signal-grid` backgrounds, `data-story` axes/polylines, architectural wireframes, divider rules, or fine geometric vector art where `1 px` strokes crawl, buzz across frames, or vanish under `4:2:0` video compression. Search aliases: `anti aliasing thin lines`, `ince çizgi kenar yumuşatma`, `Kantenglättung dünner Linien`.

## Decision rules
- **Ban `1 px` high-contrast strokes on `1080p` video**: a `1.0 px` line moving at non-integer speed alternates between `1` full-bright pixel and `2` half-bright pixels every frame (`50%` peak luminance modulation -> severe temporal buzz!), and `yuv420p` (`2x2` chroma blocks) smears colored `1 px` lines immediately. Enforce `stroke_width >= 2.0 px` (`>= 2.5 px` for colored accents) at `1080p`!
- **`2x` SSAA supersampling for diagonal/curved vector primitives**: Pillow `ImageDraw.line` / `arc` / `polygon` is `1`-sample point-rasterized by default (jagged staircases on diagonals); draw vector shape layers into a `(2 * width, 2 * height)` RGBA buffer with `2 * stroke_width` and downsample with `Resampling.LANCZOS` or `BICUBIC` (`4x` coverage anti-aliasing)!
- **Integer pixel snapping on static horizontal/vertical rules**: snap stationary divider rules and chart axes to integer pixel centers (`round(y) + 0.5` or exact even integer bounds in `2x` SSAA) so static grid lines look uniformly crisp rather than alternating `1 px` sharp and `2 px` blurry across columns.
- **Reduce contrast, not thickness, for subtle background grids**: to make a background `signal-grid` feel delicate, draw `2.0 px` lines at low `12%–18%` opacity rather than `0.5–1.0 px` lines at `80%` opacity!

## Parameters and defaults
- `min_neutral_stroke_px_1080p`: `2.0` px (scale proportionally `max(1, round(2.0 * min(w, h) / 1080))`, keeping `>= 1.5 px` pre-SSAA).
- `min_colored_stroke_px_1080p`: `2.5–3.0` px (survives `yuv420p` `2x2` chroma subsampling cleanly).
- `vector_ssaa_factor`: `2` (`2x` width & height supersampling on `production` / `hero` profiles; `1x` optional fast path on `snapshot`).
- `background_grid_alpha`: `0.14` (`12%–20%` contrast over ground).

## Procedure
1. Audit all `line`, `grid`, `arc`, `polygon`, `arrow`, and border `rect` stroke parameters in the scene recipe; clamp widths to `>= min_neutral_stroke_px` (`>= min_colored_stroke_px` for high-chroma accents).
2. Snap stationary horizontal and vertical axis/divider coordinates to integer pixel boundaries at target resolution.
3. Allocate a `2x` supersampled canvas (`2W x 2H`) for geometric primitives, scale coordinates and stroke widths by `2.0`, draw primitives, and downsample to `(W, H)` with `Resampling.BICUBIC` / `LANCZOS`.
4. If camera slowly zooms/pans over a dense procedural grid, fade out high-frequency secondary subdivisions when cell spacing drops below `14 px` (procedural mip-level fade) to eliminate Nyquist moiré!
5. Run `temporal-flicker-audit` / `qc` motion checks to verify zero high-frequency line buzz across consecutive frames.

## Failure modes and fixes
- **Diagonal arrow shaft looks like staircase bricks**: render shape layer at `2x` SSAA and downsample with `BICUBIC` / `LANCZOS`.
- **Background grid shimmers violently during `slow_dolly`**: widen grid lines from `1 px` (`alpha 0.6`) to `2 px` (`alpha 0.15`) and fade minor `8 px` sub-grid lines to `0.0` alpha.
- **Thin red chart line turns into dark grey dashed mush in `.mp4`**: widen line to `3.5 px` and lift luminance (`#FB7185` coral instead of dark `#B91C1C` pure red).

## Checklist
- [ ] Zero strokes `< 2.0 px` (`< 2.5 px` colored) appear at `1080p` master resolution.
- [ ] Diagonal and curved vector shapes use `2x` SSAA supersampling on production renders.
- [ ] Static horizontal/vertical dividers snap to exact pixel boundaries for uniform crispness.
- [ ] Dense grids fade minor subdivisions before spacing drops below `14 px` during zooms.

## Worked examples
- **Example 1 (`1920x1080` `line-chart-animation` polyline)**: `3.5 px` `#38BDF8` curve rendered in `3840x2160` (`7.0 px` stroke) and downsampled (`BICUBIC`) over `2.0 px` (`alpha 0.14`) integer-snapped horizontal y-axis guides -> razor-smooth curve with zero frame-to-frame shimmer.
- **Example 2 (`1080x1920` `kinetic-typography` accent rule)**: `3 px` `#F59E0B` horizontal divider at exact `y = 612..615 px` (`even` integer bounds survive `yuv420p` cleanly).

## Resources (load only if needed)
- [Minimum stroke width, 2x SSAA, and grid mip-fade formulas](references/stroke-width-and-ssaa-rules.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
