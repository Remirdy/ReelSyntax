---
name: golden-frame-regression
description: "Verify cross-platform visual render consistency across Linux, macOS, and Windows using golden reference descriptors, structural band tolerances, and font-metric isolation."
metadata:
  category: qa
  stage: review
  status: validated
  version: "2.0.0"
  aliases: "golden frame regression,visual render regression test,altın kare görsel regresyon,işletim sistemleri arası kare testi,Golden-Frame-Regressionstest,Plattformübergreifender Bildvergleich,regresión visual de fotogramas dorados,régression visuelle d'images de référence"
  requires: ""
---

# Golden Frame Regression

## Activation
Activate when authoring automated CI visual regression suites (`tests/test_visual_regression.py`) or locking format templates so refactors in drawing, shaders, transitions, or color management never introduce silent layout drift, inverted channels, or missing layers across Ubuntu, macOS, and Windows. Search aliases: `golden frame regression`, `altın kare görsel regresyon`, `Golden-Frame-Regressionstest`.

## Decision rules
- **Why byte-identical SHA-256 fails across OSes when system fonts are active**: Ubuntu (`DejaVuSans`), macOS (`Arial`/`Helvetica`), and Windows (`Arial` ClearType/FreeType hinting) rasterize glyph edges differently by `1–6%` ink coverage, and `libx264` thread/SIMD rounding can shift `1` LSB; use **two-tier tolerances**:
  1. *Bundled-font or pure geometric/shader regions*: tight pixel-mean `MAE <= 1.5 / 255` (`0.006` normalized) and `PSNR >= 42 dB` on raw pre-encode RGBA frames (`<= 3.0 / 255` post-H.264 decode).
  2. *System-font text bands*: coarse downsample (`16x16` or `32x18` grid mean RGB/luma signature, tolerance `<= 8.0 / 255` per cell) + exact ink-bounding-box containment (`x0, y0, x1, y1` inside safe zones) + contrast verification!
- **Sample canonical deterministic frame anchors**: test `3` diagnostic frames per format (`frame 0` hook/opening state, `transition midpoint` frame, and `settled payoff` frame) at fixed `seed` and fixed dimensions (`540x960` or `480x270` fast CI profile).
- **Save diff heatmaps on failure**: whenever a golden check fails in CI, emit observed `(cell, delta_rgb)` diagnostics (and optional `diff.png` into test artifact dir) rather than a cryptic boolean `False`.

## Parameters and defaults
- `grid_cols` x `grid_rows`: `12 x 16` (`9:16`) or `16 x 9` (`16:9`) spatial block descriptor (`JSON`-serializable, zero multi-megabyte binary bloat in git!).
- `geometric_block_mae_max`: `2.5` (`0..255` RGB units across non-text blocks).
- `system_font_block_mae_max`: `12.0` (`0..255` RGB units across blocks containing system-font glyphs, catching background/color/layout bugs while tolerating DejaVu vs Arial stem width).
- `fixed_test_seed`: explicit integer seed (for example `42`) locked in fixture `reel.json`.

## Procedure
1. Construct a minimal deterministic fixture per format with explicit `seed`, locked palette hexes, and known frame count (`90–150` frames).
2. Render pre-encode or decoded sample frames (`f_start`, `f_mid`, `f_end`) and compute compact spatial block descriptors (`mean_r`, `mean_g`, `mean_b`, `luma_std`, `text_ink_ratio` over `grid_cols x grid_rows`) into `tests/golden/visual_baselines.json`.
3. Separate assertions into **exact invariants** (canvas `(W, H)`, frame count, non-empty ink bounds inside `[0.06, 0.94]`, WCAG contrast) and **bounded perceptual similarity** (`block_mae <= tolerance`).
4. Run the identical suite on `ubuntu-latest`, `macos-latest`, and `windows-latest` in CI (`media` matrix) without OS-specific skips.
5. Update `visual_baselines.json` only via an explicit `--update-golden` maintenance script reviewed in PR diff when visual design intentionally changes.

## Failure modes and fixes
- **CI fails on Ubuntu because `"STOP GUESSING"` is `8%` wider in `DejaVuSans-Bold` than macOS `Arial Bold`**: keep fixture copy within cross-OS `90%` width safety margin or bundle an `OFL-1.1` font file for pixel-tight typography tests.
- **Committing `40` raw `1080p` `.png` golden images bloats git repo by `35 MB`**: store compact `12x16` / `16x9` float/uint8 spatial grid descriptors + perceptual hashes in JSON (`< 12 KB` total!).
- **Unseeded `random.random()` causes flaky CI failures**: require `random.Random(project_seed + scene_index)` everywhere in procedural recipes.

## Checklist
- [ ] Fixtures lock explicit integer `seed`, dimensions, and palette tokens.
- [ ] Baselines test opening (`f=0`), transition midpoint, and settled payoff frames.
- [ ] Tolerances separate geometric/background accuracy (`<= 2.5/255`) from cross-OS system-font hinting (`<= 12/255` + safe-box bounds).
- [ ] Golden baselines are compact JSON descriptors passing identically on Linux, macOS, and Windows.

## Worked examples
- **Example 1 (`social-hook-reel` cross-OS baseline)**: `540x960` draft render, frames `[0, 57, 120]` (`hook`, `wipe_left midpoint`, `payoff`). `12x16` cell RGB grid stored in `tests/golden/visual_baselines.json` (`8 KB`); catches a `wipe_left` direction inversion (`MAE = 64.2 > 12.0` -> immediate fail) while passing macOS `Arial` vs Ubuntu `DejaVuSans` (`MAE = 3.1 <= 12.0`).
- **Example 2 (Channel-swap bug detection)**: BGR vs RGB bug in a shader buffer shifts `#38BDF8` accent to `#F8BD38` (`|ΔR| = 192`, `|ΔB| = 192` -> caught on cell `(3, 5)` in `< 0.2s`).

## Resources (load only if needed)
- [Cross-OS spatial grid descriptor and tolerance specification](references/cross-os-tolerance-spec.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
