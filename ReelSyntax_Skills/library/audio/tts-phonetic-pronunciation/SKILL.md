---
name: tts-phonetic-pronunciation
description: "Normalize acronyms, version strings, SI units, numbers, and cross-language loanwords into spoken pronunciation lexicons for local speech synthesis without altering visible captions."
metadata:
  category: audio
  stage: build
  status: validated
  version: "2.0.0"
  aliases: "tts phonetic pronunciation,speech pronunciation lexicon,seslendirme telaffuz sözlüğü,kısaltma okunuş düzeltme,Aussprache-Lexikon für Sprachsynthese,Phonetische Aussprache steuern,pronunciación fonética de síntesis,prononciation phonétique vocale"
  requires: ""
---

# TTS Phonetic Pronunciation

## Activation
Activate whenever feeding technical terms, CLI commands, version numbers (`v2.4.0`), SI units (`48 kHz`, `-14 LUFS`), or cross-language nouns into a local text-to-speech synthesizer so spoken output sounds natural while burned-in captions retain clean orthography. Search aliases: `tts phonetic pronunciation`, `seslendirme telaffuz sözlüğü`, `Aussprache-Lexikon für Sprachsynthese`. Do not activate when `constraints.no_audio` or `constraints.no_voice` is true.

## Decision rules
- **Dual-string separation (`display_text` vs `spoken_text`)**: never mutate `heading`, `subheading`, or `.vtt` caption strings with phonetic respellings (`"Jey-son"`, `"ef-ef-em-peg"`); store spoken overrides in a separate `spoken_text` field or per-project `pronunciations.json` map applied strictly to the synthesizer input!
- **Expand symbols & units in target `video_lang` before synthesis**:
  - `"48 kHz"` -> `en`: `"forty-eight kilohertz"`, `tr`: `"kırk sekiz kiloherz"`, `de`: `"achtundvierzig Kilohertz"`.
  - `"-14 dB"` -> `en`: `"minus fourteen decibels"`, `tr`: `"eksi on dört desibel"`, `de`: `"minus vierzehn Dezibel"`.
  - `"v1.2"` -> `en`: `"version one point two"`, `tr`: `"sürüm bir nokta iki"`, `de`: `"Version eins Punkt zwei"`.
- **Acronym disambiguation (letter-by-letter vs word)**: spell initialisms with hyphens/spaces (`"J S O N"` -> `"jay-son"` word vs `"C P U"` -> `"C-P-U"`, `"T R"` -> `"T-R"`), using IPA (`phoneme` tags) when the local synthesis engine supports IPA, or orthographic syllable respelling as universal fallback.
- **Strip silent markup**: remove markdown backticks, URL schemes (`https://`), file slashes (`output/draft.mp4` -> `"output slash draft dot M-P-4"`), and soft hyphens (`­`) before synthesis.

## Parameters and defaults
- `lexicon_path`: optional `<project>/pronunciations.json` (`{"JSON": {"en": "jay-son", "tr": "ceyson", "de": "dschäison"}}`).
- `expand_units_and_signs`: `true` (`%`, `−`, `×`, `ms`, `fps`, `Hz`, `kHz`, `MB`, `GB`, `LUFS`, `dB`).
- `caption_source`: `"orthographic_display_text"` (never phonetic respelling).
- `pause_comma_injection`: insert `", "` around parenthetical clauses exceeding `14` words so synthesized breath groups stay natural.

## Procedure
1. Keep canonical orthographic strings in scene `params` and caption cues.
2. Run deterministic pre-TTS text normalization for `video_lang`: expand signs (`%98` -> `"yüzde doksan sekiz"` in `tr`), version dots, slashes, and SI unit symbols.
3. Apply project/domain `pronunciations.json` token replacements using whole-word boundary matching (`TOKEN`).
4. Synthesize `voice.wav` from `spoken_text`, then align word/clause timestamps back onto the canonical `display_text` token sequence for captions.
5. Audition every acronym, proper noun, and decimal number in `1.0x` playback to catch letter-swallowing or wrong stress.

## Failure modes and fixes
- **Caption prints `"ceyson şeması"` on screen**: revert caption source to `display_text` (`"JSON şeması"`) and confine `"ceyson"` strictly to the TTS input buffer.
- **Synthesizer reads `"24/1 fps"` as `"twenty-four firsts f-p-s"`**: expand rational FPS notation `"30/1 fps"` -> `"thirty frames per second"` (`"saniyede otuz kare"`, `"dreißig Bilder pro Sekunde"`).
- **Turkish `"İ"` or `"ğ"` dropped by English voice model**: verify `lang-detect-and-route` selected a native `tr` voice model before applying `tr` phonetic rules.

## Checklist
- [ ] `display_text` (captions/cards) and `spoken_text` (TTS input) are strictly separated.
- [ ] Signs, decimals, rationals (`30/1`), and SI units expand into full words in `video_lang`.
- [ ] Domain acronyms (`JSON`, `CLI`, `RGB`, `YUV`, `LUFS`) have explicit spoken forms.
- [ ] Markdown backticks, slashes, and `­` soft hyphens are stripped from `spoken_text`.

## Worked examples
- **Example 1 (Technical EN line)**:
  - `display_text`: `"Encode 1080p at 30/1 fps and −14 LUFS via CLI."`
  - `spoken_text`: `"Encode ten-eighty-P at thirty frames per second and minus fourteen luffs via C-L-I."`
- **Example 2 (Technical TR line)**:
  - `display_text`: `"JSON şeması %80 daha az sahne yeniler."`
  - `spoken_text`: `"ceyson şeması, yüzde seksen daha az sahne yeniler."`

## Resources (load only if needed)
- [Dual-text pronunciation lexicon schema and unit expansions](references/dual-text-lexicon-schema.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
