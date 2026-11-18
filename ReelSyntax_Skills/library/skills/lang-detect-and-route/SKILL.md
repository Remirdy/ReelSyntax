---
name: lang-detect-and-route
description: "Detect brief language offline via script diacritics and stopword profiles, keeping CLI interface locale separate from target video language."
metadata:
  category: skills
  stage: plan
  status: validated
  version: "2.0.0"
  aliases: "language detection,lang detect route,dil algılama ve yönlendirme,hedef dil seçimi,Spracherkennung und Routing,Zielsprache erkennen,detección de idioma,détection de langue"
  requires: ""
---

# Lang Detect And Route

## Activation
Activate at the start of prompt routing, storyboard compilation, or caption generation to resolve `ui_lang` (terminal messages) and `video_lang` (on-screen copy, casing rules, reading-speed profile, and speech voice) independently. Search aliases: `language detection`, `dil algılama ve yönlendirme`, `Spracherkennung und Routing`. Do not guess when `--video-lang` is explicitly passed.

## Decision rules
- **Explicit precedence order**:
  1. CLI `--video-lang` flag
  2. Explicit target-language request inside brief (`"in German"`, `"Türkçe video"`, `"auf Englisch"`)
  3. Project `reelsyntax.toml` `general.video_lang` (when not `"auto"`)
  4. Deterministic offline script + stopword detector on the brief text
  5. Fallback `"en"` with `confidence: "low"` logged.
- **UI vs video independence**: never overwrite `ui_lang` because the video brief is in another language (a Turkish CLI user requesting an English promo keeps Turkish CLI diagnostics while generating English scenes, font chains, and `eng` delivery metadata).
- **Diacritic fast-path**: Turkish-exclusive graphemes (`ğ`, `Ğ`, `ı`, `İ`, `ş`, `Ş`) weight `+4.0` toward `tr`; German `ß` weights `+4.5` toward `de`; shared umlauts (`ö`, `ü`, `ä`) require stopword disambiguation (`ve/için/bir/ile` vs `und/für/nicht/mit`).

## Parameters and defaults
- `supported_tier1`: `("en", "tr", "de")`, extensible via `lang-profiles/*.json` (`es`, `fr`, `pt`).
- `min_confidence_margin`: `1.5` score delta between rank-1 and rank-2 language before marking `confidence = "high"`.
- `iso639_delivery_map`: `{"en": "eng", "tr": "tur", "de": "deu", "es": "spa", "fr": "fra", "pt": "por"}`.
- `preserve_technical_loanwords`: `true` (tokens like `render`, `fps`, `shader`, `cache`, `JSON` are neutral and zero-weighted during detection).

## Procedure
1. Check explicit overrides (`--video-lang`, project config) and inspect brief for explicit target-language directives (`"in Turkish"`, `"auf Deutsch"`).
2. Strip neutral technical loanwords, numbers, and paths before scoring character n-grams, script-specific diacritics, and function-word frequencies.
3. Resolve `video_lang` and load its matching `lang-profiles/<code >.json` (uppercase rules, reading speed CPS limit, expansion factor, font fallback list, and TTS voice family).
4. Stamp `delivery.language` with the ISO 639-2/B three-letter code (`eng`, `tur`, `deu`) in `reel.json` and record `detected_lang` + `confidence` in `prompt.json`.
5. Trigger downstream script-specific checks (`turkish-glyph-audit` for `tr`, `german-compound-linebreak` for `de`).

## Failure modes and fixes
- **Shared umlauts (`ö`, `ü`) misclassify Turkish as German or vice versa**: require function-word confirmation (`bir`, `için`, `olarak` vs `ein`, `für`, `oder`) alongside `ö/ü` counts.
- **Short mixed-jargon prompt (`"FPS render test sahnesi"`) misroutes to English**: zero-weight cross-language technical nouns (`fps`, `render`, `test`, `video`) so `"sahnesi"` (`-si` possessive + Turkish lexeme) wins cleanly.
- **UI messages unexpectedly switch language**: read `ui_lang` strictly from `--lang` / `REELSYNTAX_LANG` / `general.ui_lang`, never from `video_lang`.

## Checklist
- [ ] Explicit `--video-lang` and `"in <lang>"` directives override statistical detection.
- [ ] `ui_lang` and `video_lang` remain decoupled across CLI, storyboard, and QC.
- [ ] Technical loanwords (`render`, `fps`, `cache`) do not skew language detection.
- [ ] Resolved language loads matching casing, CPS, font chain, and `delivery.language` tag.

## Worked examples
- **Example 1 (Mixed technical Turkish brief)**: `--lang en`, brief `"30 fps dikey tanıtım sahnesi oluştur"` -> `ui_lang = "en"`, `fps` ignored as loanword, `ı`/`ü` + `"için/sahnesi/oluştur"` -> `video_lang = "tr"`, `delivery.language = "tur"`, Turkish dotted-`İ` uppercase rules activated.
- **Example 2 (Cross-language request)**: `--lang tr`, brief `"Produktstart für Entwickler auf Deutsch, 15 Sekunden"` -> `ui_lang = "tr"`, explicit `"auf Deutsch"` + `für` -> `video_lang = "de"`, `delivery.language = "deu"`.

## Resources (load only if needed)
- [Offline language signature weights and edge cases](references/language-signatures.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
