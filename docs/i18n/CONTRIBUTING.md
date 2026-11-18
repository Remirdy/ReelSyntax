# Contributing a language

ReelSyntax separates three language settings:

1. **Interface language (`--ui-lang`)**: CLI and local Web UI messages from `locales/<lang>.json`.
2. **Prompt language**: Detected offline from the user's input text unless overridden.
3. **Video language (`--lang`)**: On-screen typography, captions, and speech synthesis governed by `lang-profiles/<lang>.json`.

## Support tiers

- **Tier 1 (`en`, `tr`, `de`)**: Complete UI catalog, documentation, routing aliases and morphology, caption rules, glyph QC, official format templates, and golden routing benchmarks.
- **Tier 2**: Complete UI catalog, routing aliases, caption profile, glyph QC, at least one golden routing benchmark file (`tests/i18n/golden/<lang>.json`), and a named maintainer.
- **Tier 3 (RTL and CJK scripts)**: Requires verified bidirectional or non-whitespace line-breaking tests across both Chromium and Pillow rendering paths before being listed as supported.

## Scaffolding and validating a new language

```sh
reelsyntax lang new fr
reelsyntax lang validate fr
reelsyntax glyphs fr
```

1. Edit `lang-profiles/<lang>.json` with accurate quotation marks, decimal/thousands separators, `caption` limits (`max_chars_per_line`, `max_lines`, `max_cps`), `required_glyphs`, and `formality_default`.
2. Translate every key in `locales/<lang>.json`, keeping `{placeholder}` names identical to `locales/en.json`. Consult the [glossary](glossary.md) for canonical terminology.
3. Keep `"verified_by_owner": false` in `locales/status.json`. Only the repository owner sets verification status after review; unverified locales display a draft notice.
4. Add `tests/i18n/golden/<lang>.json` and run `python -m unittest tests.test_i18n -v`.
