# Dual-Text Pronunciation Lexicon Schema and Unit Expansions

```json
{
  "schema_version": 1,
  "entries": {
    "JSON": {"en": "jay-son", "tr": "ceyson", "de": "dschäison"},
    "CLI": {"en": "C-L-I", "tr": "komut satırı", "de": "C-L-I"},
    "LUFS": {"en": "luffs", "tr": "lufs", "de": "L-U-F-S"},
    "WCAG": {"en": "W-C-A-G", "tr": "W-C-A-G", "de": "W-C-A-G"},
    "sRGB": {"en": "S-R-G-B", "tr": "S-R-G-B", "de": "S-R-G-B"}
  }
}
```

Apply longer multi-token matches (`"30/1 fps"`, `"−14 LUFS"`) before single-word dictionary lookups so unit compounds expand cleanly.
