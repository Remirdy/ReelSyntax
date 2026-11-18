# Minimum Stroke Width, 2x SSAA, and Grid Mip-Fade Formulas

| Element Type | Min Width (`1080p`, `yuv420p`) | Opacity Guidance | SSAA Needed? |
| --- | ---: | --- | --- |
| Background grid line | `2.0 px` | `0.10–0.18` (subtle) | `1x` if axis-aligned, `2x` if perspective |
| Editorial divider rule | `2.0–3.0 px` | `0.60–1.00` | Snap to even `y` (`2 * k`) |
| Data polyline / arc | `3.0–4.5 px` | `1.00` | **Yes (`2x` SSAA)** |
| Callout arrow / pill border | `2.5–3.5 px` | `0.90–1.00` | **Yes (`2x` SSAA)** |

## Procedural grid mip-fade (`cell_px` spacing)
`subgrid_alpha = base_alpha * clamp((cell_px - 12.0) / 16.0, 0.0, 1.0)` — smoothly extinguishes tight sub-grids below `12 px` spacing before Nyquist aliasing begins!
