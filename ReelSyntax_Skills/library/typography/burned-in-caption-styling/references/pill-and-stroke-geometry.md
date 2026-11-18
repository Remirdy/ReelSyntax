# Backing Pill, Outer Stroke, and Descender Padding Math

| Canvas | Font Size | Line Height | Pill Pad `(pad_x, pad_y_top, pad_y_bottom)` | Safe `y` Band (Top..Bottom of Box) |
| --- | ---: | ---: | --- | --- |
| `1080x1920` (`9:16`) | `52 px` | `66 px` | `(24 px, 12 px, 16 px)` | `1340 px .. 1545 px` (`0.70h..0.805h`) |
| `1080x1350` (`4:5`) | `48 px` | `60 px` | `(22 px, 11 px, 15 px)` | `980 px .. 1140 px` (`0.72h..0.84h`) |
| `1920x1080` (`16:9`) | `46 px` | `58 px` | `(22 px, 10 px, 14 px)` | `860 px .. 1010 px` (`0.80h..0.935h`) |

Always measure ascent + descent via `font.getmetrics()` rather than tight per-string `textbbox` height alone so phrases without descenders (`"KONU"`) and phrases with descenders (`"ÇAĞRI"`) produce identical pill heights!
