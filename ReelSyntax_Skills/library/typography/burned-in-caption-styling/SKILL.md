---
name: burned-in-caption-styling
description: "Render legible open burned-in captions with anchored baselines, semi-opaque pill or stroke backing, >= 7:1 contrast, and restrained active-word emphasis."
metadata:
  category: typography
  stage: build
  status: validated
  version: "2.0.0"
  aliases: "burned in captions,open caption styling,gömülü altyazı tasarımı,ekrana işlenmiş altyazı,eingebrannte Untertitel,offene Untertitel gestalten,subtítulos incrustados,sous-titres incrustés"
  requires: ""
---

# Burned In Caption Styling

## Activation
Activate when rendering open (always-visible) burned-in captions onto vertical shorts, social explainers, or muted-autoplay previews where busy backgrounds and mobile viewing demand instant effortless legibility. Search aliases: `burned in captions`, `gömülü altyazı tasarımı`, `eingebrannte Untertitel`. Do not activate when `constraints.no_text` is true or when delivering clean textless masters with external `.srt`/`.vtt` sidecars only.

## Decision rules
- **Guaranteed contrast backing (`>= 7.0:1` AAA target)**: never place bare white text directly over arbitrary video/photo luminance; enclose captions in a rounded semi-opaque pill (`rgba(15, 20, 28, 0.82)`, corner radius `0.32 * line_height`) OR render an *outside* stroke (`>= 0.09 * font_px` dark outline drawn *underneath* the fill, never eating inward into glyph stems) + subtle drop shadow.
- **Baseline vertical lock**: anchor line-1 baseline at a fixed `y` (`0.74h` on `9:16` clearing bottom `18%` UI zone; `0.86h` on `16:9`) so switching between `1`-line and `2`-line phrases never bounces the top reading line up and down.
- **Restrained active-word highlight**: if highlighting the currently spoken word, change *color or background pill* only (`#F8FAFC` -> `#38BDF8` or `#FACC15`), **never** scale active words `1.25x` mid-line (which reflows neighbor words left and right on every syllable!).
- **Chunk size**: `2–6` words per visible phrase (`<= 2` lines, `<= 32` chars/line vertical, `<= 42` chars/line widescreen).

## Parameters and defaults
- `font_px_vertical_1080x1920`: `52` px semi-bold/bold sans (`0.048 * width`).
- `font_px_widescreen_1920x1080`: `46` px semi-bold sans (`0.042 * height`).
- `pill_bg_rgba`: `(15, 20, 28, 210)` (`~82%` alpha charcoal) with padding `(0.45 * em, 0.24 * em)`.
- `anchor_y_vertical`: `0.74 * height` (`1420 px` on `1920h`, well above `1575 px` bottom `18%` safe line).
- `active_word_reflow_allowed`: `false` (constant advance width across active/inactive states).

## Procedure
1. Pre-measure the complete `1–2` line phrase once using fixed font weight and size so horizontal word `(x, y)` coordinates remain `100%` stationary throughout the phrase's active interval.
2. Draw the rounded backing pill (or outer stroke + shadow pass) behind the phrase bounding box, clamping outer pill margins inside `[0.08w, 0.92w]` (`[0.08w, 0.84w]` on `9:16` if right-rail icons overlap `0.74h`).
3. Render inactive words in high-luminance neutral ink (`#F8FAFC`) and active spoken word in high-luminance accent (`#FDE047` or `#7DD3FC`), verifying both inks achieve `>= 7.0:1` contrast against `pill_bg_rgba`.
4. Hold the final word of each sentence at least `6` frames (`0.20s`) before clearing or cutting to the next phrase, leaving a `2`-frame clean transition or instant swap on speech onset.
5. Verify zero descender clipping (`g`, `j`, `p`, `q`, `y`, `ç`, `ğ`, `ş`) inside the backing pill (`bottom_pad >= 0.28 * font_px`).

## Failure modes and fixes
- **Active word bolding/scaling jitters neighboring words every `180 ms`**: pre-layout all words in the same font weight and highlight via fill color or fixed-margin under-pill only.
- **Center stroke eats thin glyph counters**: draw stroke pass *first* in full outline width, then draw crisp fill pass *on top* so interior glyph strokes stay 100% intact.
- **Bottom of `2`-line caption collides with platform caption/account overlay**: keep bottom of line 2 `<= 0.82h` (`>= 18%` bottom clearance on `9:16`).

## Checklist
- [ ] Backing pill or under-stroke guarantees `>= 7.0:1` contrast over white and dark backgrounds alike.
- [ ] Word `(x, y)` positions never jitter horizontally during active-word highlighting.
- [ ] Descenders (`ğ`, `ş`, `ç`, `p`, `y`) fit cleanly inside pill bottom padding.
- [ ] Entire `2`-line block stays above the `0.82h` bottom safe-zone line on `9:16`.

## Worked examples
- **Example 1 (`1080x1920` `9:16` spoken tutorial)**: `52 px` Sans Bold, phrase `"Cache skips eighty percent
of redundant frame redraws"` (`26` + `26` chars), `rgba(15,20,28,210)` rounded pill (`r = 16 px`), top line anchored at `y = 1380 px`, bottom edge at `1512 px` (`< 1574 px` safe ceiling), active word tinted `#FDE047` (`13.4:1` contrast on pill).
- **Example 2 (`1920x1080` `16:9` cutscene open captions)**: `44 px` Sans Medium, single-color `#F8FAFC` (no karaoke highlight for narrative tone), `4 px` under-stroke `#0F172A` + `rgba(15,23,42,185)` pill at `y = 920 px`.

## Resources (load only if needed)
- [Backing pill, outer stroke, and descender padding math](references/pill-and-stroke-geometry.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
