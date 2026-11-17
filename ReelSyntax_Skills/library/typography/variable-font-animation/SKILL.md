---
name: variable-font-animation
description: "Use for variable font animation and tabular counters. Interpolate OpenType wght, wdth, and opsz axes smoothly and lock numeric advance widths to prevent layout jitter."
metadata:
  category: typography
  stage: build
  status: validated
  version: "2.0.0"
  aliases: "variable font,değişken font animasyonu,tabular figures,opentype eksenleri"
  requires: ""
---

# Variable Font Animation

## Activation
Use when animating typographic weight/width emphasis, live telemetry readouts, frame/timecode counters, or kinetic headlines. Search aliases: variable font,değişken font animasyonu,tabular figures,opentype eksenleri. Never activate when `no_text` is locked.

## Inputs and output
- Inputs: Licensed local TTF/OTF font file, axis ranges (`wght`, `wdth`, `opsz`), target string (including localized glyphs), and safe-area bounds.
- Output: Jitter-free rendered typography with verified glyph coverage and measured bounds.
- Required capability: `reelsyntax.typography` or CSS `font-variation-settings` / `font-variant-numeric: tabular-nums`.
- Evidence bundle: Glyph `.notdef` coverage check, worst-case bounding box at maximum axis excursion, and contrast measurement.

## Production recipe
1. Validate `constraints.no_text` is false and verify every character in the copy (including Turkish `ÇĞİÖŞÜçğıöşü`) maps to a non-`.notdef` glyph in the chosen font before rendering.
2. Measure layout clearance at the **widest/heaviest** keyframe (`max(wght)`, `max(wdth)`, maximum tracking), never only at frame 0's light weight.
3. For animated numbers, timers, percentages, and coordinates, enforce tabular figures (`tnum` or fixed per-cell advance width) so changing digits (`1` vs `8`) never shift adjacent labels horizontally.
4. Anchor weight/tracking swells to baseline + optical left/center pin rather than recomputing integer pixel bounding-box centers per frame, preventing 1-pixel staircase wobble.

## Acceptance criteria
- Zero `.notdef` fallback boxes; measured bounds stay inside safe layout margin at all keyframes and motion extrema.
- Numeric counters exhibit zero horizontal label shift across digit changes.
- Record font name/license, measured min contrast ratio ($\ge 4.5:1$ normal, $\ge 3.0:1$ large), and bounds log.

## Failure and repair
If weight interpolation overflows safe width or shimmers on thin hairlines, cap minimum stroke weight for 1080p/540p output, switch optical size (`opsz`) upward, or tighten tracking slightly at peak weight.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric.
- [WCAG Contrast Minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)

Original production guidance and validated runtime math.
