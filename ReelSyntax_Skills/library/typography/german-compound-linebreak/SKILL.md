---
name: german-compound-linebreak
description: "Wrap long German and Nordic compound nouns cleanly at morphological constituent seams using explicit hyphens or soft-hyphen hints instead of mid-morpheme clipping."
metadata:
  category: typography
  stage: build
  status: validated
  version: "2.0.0"
  aliases: "german compound linebreak,compound word hyphenation,Almanca birleşik kelime satır kırma,uzun kelime bölme,Komposita-Zeilenumbruch,Worttrennung bei Komposita,división de palabras compuestas,césure des mots composés"
  requires: ""
---

# German Compound Linebreak

## Activation
Activate when rendering German (`de`) headings, kickers, chart labels, or `9:16` vertical cards where single compound tokens (`18–32` characters, such as `Bildwiederholfrequenz` or `Hintergrundbeleuchtung`) exceed column width or force unreadable font-size downscaling. Search aliases: `german compound linebreak`, `Almanca birleşik kelime satır kırma`, `Komposita-Zeilenumbruch`. Do not activate when `constraints.no_text` is true.

## Decision rules
- **Never shrink display font `< 62%` of nominal size just to keep one compound on a single line**: if a single token exceeds `max_column_px` at `>= 0.72 * nominal_px`, break at the primary morphological constituent seam (`Kompositafuge`) rather than shrinking the whole headline to micro-type.
- **Break at constituent boundaries, never arbitrary character counts**: split between root nouns or after linking morphemes (`-ungs-`, `-heits-`, `-keits-`, `-schafts-`, `-ions-`, `-itäts-`, `Fugen-s`) — for example `"Hintergrund-
beleuchtung"`, **never** `"Hintergrun-
dbeleuchtung"`.
- **Editorial `Bindestrich` option for display caps**: in `2–3` word vertical headlines, prefer idiomatic hyphenated constituent styling (`"ECHTZEIT-
VORSCHAU"`, `"KONTRAST-
PRÜFUNG"`) when breaking across two display lines so both stems scan instantly.
- **Minimum stem fragment length**: never leave `< 4` characters on either side of a compound break (`"AU-
DIO"` is forbidden; keep `"AUDIO-
PEGEL"`).

## Parameters and defaults
- `compound_trigger_chars`: `16` characters on `9:16` vertical columns (`22` on `16:9`).
- `min_font_scale_before_break`: `0.72` of nominal display font size.
- `min_constituent_chars`: `4` characters before and after hyphen break.
- `visible_break_glyph`: `"-"` (`U+002D`) rendered only when the soft-hyphen (`­`) opportunity is actually taken at line wrap.

## Procedure
1. Detect tokens with `len(token) >= compound_trigger_chars` that overflow `max_column_px` at `0.75 * nominal_font_px`.
2. Locate morphological constituent seams using linking-suffix patterns (`ung(s)`, `heit(s)`, `keit(s)`, `tion(s)`, `ität(s)`, `werk(s)`, `system`, `frequenz`, `kontrolle`, `prüfung`, `steuerung`, `analyse`) or explicit soft-hyphen (`­`) hints in copy.
3. Choose the seam closest to the token's optical midpoint (`0.40–0.62` of character length) that satisfies `min_constituent_chars >= 4` on both halves.
4. Materialize `"-"` + newline at the chosen seam if wrapped, stripping unused `­` codepoints from non-wrapped tokens so invisible control chars never render as tofu boxes in bitmap/system fonts.
5. Re-measure two-line bounding box height and confirm vertical safe-zone clearance.

## Failure modes and fixes
- **Literal `­` rendered as missing-glyph rectangle `□`**: strip all unconsumed `­` characters prior to `ImageDraw.text()` and emit standard `"-"` only on active line breaks.
- **Awkward `2`-letter stub (`"Ab-
schnitt"` in huge display caps)**: keep `<= 10` char words intact on one line and only split `>= 16` char multi-stem compounds at major noun joins (`>= 4` chars each side).
- **Three-way hyphenation (`A-
B-
C`) on one word**: cap hyphenation at `<= 1` break per compound word; rewrite copy (`"Frequenz der Bilder"`) if a triple compound still overflows.

## Checklist
- [ ] Tokens `>= 16` chars split at true morphological constituent seams rather than shrinking below `72%` font scale.
- [ ] Both halves around a break contain `>= 4` characters and at most `1` hyphen break per word.
- [ ] Unused `­` soft hyphens are stripped before glyph rasterization.
- [ ] Resulting `2`-line block passes `text_overflow` and `vertical_safe_zones` checks.

## Worked examples
- **Example 1 (`9:16` `1080x1920` heading, DE)**: `"BILDWIEDERHOLFREQUENZ"` (`21` chars) overflows `464 px` column at `64 px` bold -> Seam split at `"BILDWIEDERHOL-
FREQUENZ"` (`14` + `8` chars), fits cleanly at `54 px` (`84%` nominal scale) with zero clipping.
- **Example 2 (`16:9` chart title, DE)**: `"Speicherplatz­verbrauch im Vergleich"` -> Fits on one line at `1920x1080`, so `­` is stripped cleanly before draw (`"Speicherplatzverbrauch im Vergleich"`).

## Resources (load only if needed)
- [German morphological seam patterns and break priorities](references/compound-seam-rules.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
