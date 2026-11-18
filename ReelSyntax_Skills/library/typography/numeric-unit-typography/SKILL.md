---
name: numeric-unit-typography
description: "Format animated counters, metrics, percentages, currencies, and SI units using tabular lining figures, true minus glyphs, non-breaking spaces, and locale separators."
metadata:
  category: typography
  stage: build
  status: validated
  version: "2.0.0"
  aliases: "numeric unit typography,tabular figures formatting,sayı ve birim tipografisi,rakam hizalama kuralları,Zahlen- und Einheitentypografie,Tabellenziffern formatieren,tipografía numérica y unidades,typographie des nombres et unités"
  requires: ""
---

# Numeric Unit Typography

## Activation
Activate whenever rendering animated metric counters (`0 -> 98%`), data-story axis labels, countdown timers, benchmark deltas (`-14 LUFS`, `+3.4x`), or prices across localized videos. Search aliases: `numeric unit typography`, `sayı ve birim tipografisi`, `Zahlen- und Einheitentypografie`. Do not activate when `constraints.no_text` is true.

## Decision rules
- **Tabular figures (`tnum`) or fixed-advance digit cells on animated counters**: proportional `"1"` is narrower than `"8"`, causing the entire `%` or unit label to jitter sideways on every frame of a rolling counter; enable OpenType `tnum` + `lnum` or advance each digit `"0".."9"` by `max_digit_advance_px` when animating numbers.
- **Locale-accurate percent, decimal, and thousands formatting**:
  - `en`: `"98.4%"`, `"12,500"`, `"$49"`
  - `tr`: `"%98,4"` (percent sign **precedes** the number in Turkish with no space!), `"12.500"`, `"49 ₺"`
  - `de`: `"98,4 %"` (non-breaking thin/narrow space before `%` and units!), `"12.500"`, `"49 €"`
  - `fr`: `"98,4 %"`, `"12 500"`.
- **True typographic minus & multiplication**: use Unicode minus `"−"` (`U+2212`, matching `"+"` stroke height and width) instead of stubby ASCII hyphen `"-"` on negative metrics (`"−14 LUFS"`, `"−32%"` / `"−%32"`), and `"×"` (`U+00D7`) for multipliers (`"3,2×"` / `"3.2×"`), provided the active font covers `U+2212` and `U+00D7`.
- **SI unit spacing**: separate value and unit (`"48 kHz"`, `"24 fps"`, `"93 °C"` or `"93°C"` per house style, never `"48khz"` lowercase `k`/`h` error).

## Parameters and defaults
- `animated_digit_mode`: `"tabular_cell"` (`cell_width = max(advance('0'..'9'))`).
- `nbsp_char`: `" "` (falls back cleanly in every Latin font, unlike ` ` which some legacy fonts lack).
- `minus_char`: `"−"` when font glyph check passes, else `"-"`.
- `counter_settle_hold_ratio`: `>= 0.55` (finish counting in the first `<= 45%` of scene frames so the final exact number holds still for `>= 55%` of the shot!).

## Procedure
1. Format raw float/int values through the `video_lang` number formatter (decimal mark, grouping separator, Turkish prefix `%N` vs German `N %` vs English `N%`).
2. Check active font glyph support for `U+2212` (`−`), `U+00D7` (`×`), and currency symbols (`₺`, `€`, `$`); fall back cleanly only if a glyph is absent.
3. Join numeric strings and SI units (`ms`, `s`, `fps`, `Hz`, `kHz`, `MB`, `GB`, `LUFS`, `dB`) with `" "`.
4. When animating a counter across frames `0..K`, draw digits on a fixed `max_digit_advance_px` grid (right-aligned to the decimal point) and lock the final target value from frame `K` through `duration_frames - 1` (`K <= 0.45 * duration_frames`).
5. Verify tabular alignment across stacked table rows or bar-chart labels.

## Failure modes and fixes
- **Turkish promo prints `"98%"` instead of `"%98"`**: route percentage formatting through `video_lang` profile (`tr` prefix `"%" + formatted_num`).
- **Rolling counter shakes horizontally every frame as `"1"` becomes `"8"`**: render digits using fixed `max_digit_advance_px` cell steps or a monospace/`tnum` face.
- **Counter keeps spinning until the very last frame of the cut**: finish the ease-out count by `40%` of scene duration so viewers actually read the final value.

## Checklist
- [ ] Percentages, decimals, and thousands follow `video_lang` conventions (`%98,4` TR, `98,4 %` DE, `98.4%` EN).
- [ ] Numbers and SI units are bound with `" "` and exact unit capitalization (`kHz`, `LUFS`, `MB`).
- [ ] Animated counters use fixed tabular digit widths (`zero` horizontal jitter).
- [ ] Rolling counters lock onto their final value for `>= 55%` of scene frames.

## Worked examples
- **Example 1 (`75`-frame benchmark scene across EN / TR / DE)**: Raw metric `delta = -0.684`, `latency_ms = 14.2`.
  - `en`: `"−68.4%"` / `"14.2 ms"`
  - `tr`: `"−%68,4"` / `"14,2 ms"`
  - `de`: `"−68,4 %"` / `"14,2 ms"`
  Count animates `0..30f` (`cubic_out`) on `34 px` fixed digit cells, holds locked `30..75f` (`1.50s`).
- **Example 2 (Countdown timer `10 -> 0`)**: Fixed `2`-digit tabular anchor centered on `(0.5w, 0.5h)` so transition `10 -> 9` never jumps half a digit left.

## Resources (load only if needed)
- [Locale number, percentage, currency, and SI unit formatting rules](references/locale-number-unit-rules.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
