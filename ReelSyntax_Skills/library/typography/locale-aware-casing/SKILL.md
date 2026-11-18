---
name: locale-aware-casing
description: "Transform display headings and kickers using locale-specific uppercase, lowercase, and title-case rules instead of ASCII-biased string methods."
metadata:
  category: typography
  stage: build
  status: validated
  version: "2.0.0"
  aliases: "locale aware casing,localized uppercase,yerel büyük küçük harf,Türkçe İ ı harf dönüşümü,sprachabhängige Großschreibung,lokale Großbuchstaben,mayúsculas según idioma,casse sensible à la langue"
  requires: ""
---

# Locale Aware Casing

## Activation
Activate whenever transforming `heading`, `kicker`, badge, or button strings to all-caps, lowercase, or title case across multilingual renders (`tr`, `de`, `en`, `es`, `fr`, `pt`). Search aliases: `locale aware casing`, `yerel büyük küçük harf`, `sprachabhängige Großschreibung`. Do not activate when `constraints.no_text` is true.

## Decision rules
- **Never call raw Python `str.upper()` / `str.lower()` on Turkish (`tr` / `az`) text**:
  - In `tr`, `"i"` uppercases to `"İ"` (`U+0130`) and `"ı"` (`U+0131`) uppercases to `"I"` (`U+0049`); `"İ"` lowercases to `"i"` and `"I"` lowercases to `"ı"` (avoid combining-dot decomposition `i̇` that renders broken boxes in subset fonts).
- **German (`de`) uppercase `ß` rule**: map `"ß"` to `"SS"` in standard all-caps headlines unless the active display font explicitly verifies glyph coverage for capital `"ẞ"` (`U+1E9E`) and optical kerning is checked.
- **Technical token & unit preservation**: preserve exact casing on SI units and technical acronyms inside title/uppercase passes (`"kHz"`, `"dBFS"`, `"LUFS"`, `"mAh"`, `"pH"`, `"macOS"` -> keep unit symbol `"ms"`, `"MB"` distinct from `"mb"`).
- **NFC normalization lock**: normalize transformed strings to Unicode `NFC` before glyph measurement and rasterization so precomposed diacritics (`Ç`, `Ö`, `Ü`, `Ğ`, `Ş`, `É`) use single font codepoints.

## Parameters and defaults
- `locale_code`: resolved from `video_lang` (`"tr"`, `"de"`, `"en"`, `"es"`, `"fr"`, `"pt"`).
- `german_eszett_upper`: `"SS"` default (`"CAPITAL_ESZETT"` optional if font covers `U+1E9E`).
- `unicode_normalization`: `"NFC"`.
- `preserve_unit_tokens`: `("Hz", "kHz", "MHz", "dB", "dBFS", "dBTP", "LUFS", "ms", "px", "KB", "MB", "GB", "fps")`.

## Procedure
1. Read target `video_lang` before running any display-case transform on `kicker` or `heading` fields.
2. Tokenize protected technical units (`preserve_unit_tokens`) or apply locale-specific character translation maps (`tr`: `str.maketrans({"i": "İ", "ı": "I"})` prior to `.upper()`).
3. Normalize the resulting string with `unicodedata.normalize("NFC", text)` so combining marks never split from base glyphs.
4. Run glyph-coverage check against the active `ImageFont` / FreeType face to verify zero `.notdef` fallback boxes on `İ`, `Ş`, `Ğ`, `Ä`, `Ö`, `Ü`, `Ñ`.
5. Measure pixel bounding box *after* locale casing (`"STRASSE"` is 1 glyph wider than `"straße"`).

## Failure modes and fixes
- **`"ışık ve iz".upper()` turns into `"IŞIK VE IZ"` (wrong `"IZ"` instead of `"İZ"` in Turkish)**: apply `text.replace("i", "İ").replace("ı", "I").upper()` for `locale == "tr"`.
- **`"İSTANBUL".lower()` produces `"i̇stanbul"` with floating extra dot**: replace `"İ"` -> `"i"` and `"I"` -> `"ı"` *before* calling `.lower()`.
- **German `"GROß"` mixes lowercase `ß` inside all-caps word**: map `"ß"` -> `"SS"` (`"GROSS"`) and re-fit line width.

## Checklist
- [ ] Turkish `i <-> İ` and `ı <-> I` map cleanly in both upper and lower directions without `U+0307` residue.
- [ ] German all-caps maps `ß -> SS` (or verified `ẞ`) before width measurement.
- [ ] Output strings are `NFC`-normalized and pass font glyph coverage audit.
- [ ] Line-fit measurement runs *after* casing transformation.

## Worked examples
- **Example 1 (`tr` vertical kicker + heading)**: Input `kicker = "ipucu"`, `heading = "hızlı ışık ayarı"` -> Locale upper (`tr`) produces `"İPUCU"` and `"HIZLI IŞIK AYARI"` (`NFC`, 100% covered in system sans bold).
- **Example 2 (`de` headline width refit)**: Input `"Maßstab für große Größen"` -> All-caps (`de`) produces `"MASSSTAB FÜR GROSSE GRÖSSEN"` (`+3` characters wider -> wrapped cleanly across two balanced lines before draw).

## Resources (load only if needed)
- [Locale casing transformation table and protected units](references/casing-mapping-table.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
