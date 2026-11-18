# Cross-OS Spatial Grid Descriptor and Tolerance Specification

| Verification Layer | Metric | Bundled Font / Pure Geometry | System Font Fallback Active |
| --- | --- | ---: | ---: |
| Canvas dimensions & frame count | Exact equality | `0` tolerance | `0` tolerance |
| Text bounding box inside safe area | Normalized `[x0, y0, x1, y1]` | `0` clipping allowed | `0` clipping allowed |
| Non-text background/shape cells | Cell mean RGB `|Δ|` (`0..255`) | `<= 2.5` | `<= 3.5` |
| Text-bearing cells | Cell mean RGB `|Δ|` (`0..255`) | `<= 3.0` | `<= 12.0` |
| Whole-frame mean luma | `|ΔY|` (`0..255`) | `<= 1.5` | `<= 4.0` |
