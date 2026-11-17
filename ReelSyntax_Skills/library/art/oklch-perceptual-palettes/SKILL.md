---
name: oklch-perceptual-palettes
description: "Use for perceptual OKLab and OKLCH color palettes. Interpolate gradients, lighting tints, and data series with uniform perceived lightness and preserved chroma."
metadata:
  category: art
  stage: plan
  status: validated
  version: "2.0.0"
  aliases: "oklch renk paleti,oklab gradient,perceptual color space,algısal renk geçişi"
  requires: ""
---

# Oklch Perceptual Palettes

## Activation
Use when constructing brand/cinematic palettes, interpolating multi-stop color ramps, designing accessible chart series, or blending warm-to-cool lighting without muddy gray midpoints. Search aliases: oklch renk paleti,oklab gradient,perceptual color space,algısal renk geçişi.

## Inputs and output
- Inputs: Anchor `#RRGGBB` colors or target lightness/chroma/hue $(L, C, h)$ roles (`background`, `surface`, `foreground`, `accent`).
- Output: Gamut-mapped `#RRGGBB` tokens, smooth perceptual ramps, and verified WCAG contrast ratios.
- Required capability: Core `reelsyntax.palette` module.
- Evidence bundle: Palette hex table, OKLab lightness separation $\Delta L$, and foreground/background contrast ratios.

## Production recipe
1. Transform sRGB anchors through inverse companding into linear RGB, then into Björn Ottosson's OKLab $(L, a, b)$ and cylindrical OKLCH $(L, C, h)$.
2. Maintain intentional lightness hierarchy: primary copy vs background $|\Delta L| \ge 0.48$ (verifying WCAG relative luminance ratio $\ge 4.5:1$); secondary muted UI vs background $\ge 3.0:1$.
3. Interpolate color transitions in OKLab (or shortest-arc OKLCH when preserving saturation between complementary hues) instead of gamma sRGB, eliminating murky desaturated midpoints.
4. Soft-clamp out-of-gamut $(L, C, h)$ back into sRGB by binary-searching chroma $C \to C^*$ at fixed $(L, h)$ rather than per-channel RGB clipping, preserving exact perceived lightness and hue angle.
5. Restrain palette complexity: typically 1 dominant ground, 1 primary ink, 1 neutral structure tone, and 1–2 motivated accents; avoid unmotivated rainbow neon gradients.

## Acceptance criteria
- Every text/foreground pairing meets its declared WCAG contrast heuristic; zero unintended sRGB channel clipping during gamut mapping.
- Record hex values, $(L, C, h)$ coordinates, and measured contrast ratios.

## Failure and repair
If an accent vibrates against dark or warm paper grounds, hold hue $h$ constant and adjust OKLab $L$ and $C$ independently until contrast and visual hierarchy read cleanly.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric.
- [WCAG 2.2 Contrast](https://www.w3.org/TR/WCAG22/)

Original production guidance and validated runtime math.
