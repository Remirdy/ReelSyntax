---
name: transcreation-tone
description: "Adapt hooks, imperatives, humor, and formality registers (du/Sie, sen/siz, tú/usted) across languages by rhetorical function and beat budget rather than literal calques."
metadata:
  category: story
  stage: plan
  status: validated
  version: "2.0.0"
  aliases: "transcreation tone,formality register adaptation,yaratıcı çeviri ve hitap tonu,sen siz resmiyet uyumu,Transkreation und Anredeform,Du-Sie-Tonalität anpassen,transcreación y registro,transcréation et registre"
  requires: ""
---

# Transcreation Tone

## Activation
Activate when authoring or localizing headlines, voiceover scripts, hooks, and calls to action across `en`, `tr`, `de`, `es`, `fr`, and `pt` so localized variants sound native, consistent in formality register, and fit the exact frame budget. Search aliases: `transcreation tone`, `yaratıcı çeviri ve hitap tonu`, `Transkreation und Anredeform`.

## Decision rules
- **Lock one address register (`formality`) across the entire project**: never mix informal `du` / `sen` / `tú` / `tu` in scene 1 with formal `Sie` / `siz` / `usted` / `vous` in the closing CTA!
  - Default `casual` (`du`, `sen`, `tú`, `tu`, `você`) for creator social reels, tutorials, and developer tips.
  - Default `formal` (`Sie`, `siz`, `usted`, `vous`) or **infinitive / nominalized neutral** (`"Jetzt testen"` instead of `"Teste"`/`"Testen Sie"`, `"Hemen deneyin"` / `"Verileri doğrulama"`) for enterprise/institutional explainers and UI labels.
- **Translate rhetorical impact, never English idioms word-for-word**: replace literal calques (`"Stop leaving frames on the table"`, `"Game changer"`, `"No-brainer"`) with concrete native verbs matching the beat's character budget.
- **Syllable & frame budget parity**: if the scene timing is locked (dubbing or multi-language variant sharing a timeline), keep translated spoken syllable duration within `+-12%` of the source beat and display headline character count within the column's `max_cpl`.
- **Word-order sync with visual reveals**: Turkish is `SOV` (verb arrives at the end) and German subordinate clauses push verbs to the end; when a visual accent fires on frame `24`, place the key contrasted **noun or number** at the matching timestamp rather than waiting for the clause-final verb.

## Parameters and defaults
- `formality_register`: `"casual"` | `"neutral_infinitive"` | `"formal"` (default: `"casual"` for social formats, `"neutral_infinitive"` for data/news/product UI).
- `syllable_budget_tolerance`: `0.12` (`+-12%` when sharing fixed scene `duration_frames`).
- `calque_blocklist_check`: flag literal calques of English marketing clichés during review.
- `preserve_proper_nouns_and_cli_flags`: `true` (never translate literal CLI commands like `reelsyntax make` or JSON field names).

## Procedure
1. Record `formality_register` and `tone` (`direct`, `warm`, `analytical`, `playful`) in the brief/storyboard header before writing copy.
2. Identify each beat's communicative act (`hook-challenge`, `mechanism-claim`, `contrast-turn`, `action-invite`) rather than translating token-by-token.
3. Draft native phrasing in the target language using the locked pronoun/verb paradigm (`sen` vs `siz`, `du` vs `Sie` vs infinitive `-en`), keeping literal code/CLI identifiers untouched.
4. Align visual pop/highlight cues to the target language's focal noun or metric position (handling `tr` SOV and `de` V2/verb-final word order).
5. Verify character counts fit `heading` / `subheading` bounds and spoken CPS stays inside `multilingual-caption-profiles` limits.

## Failure modes and fixes
- **Register flip mid-reel (`"Bak..."` in beat 1 -> `"İnceleyiniz"` in beat 5)**: audit all second-person verb suffixes and pronouns across scenes `1..N` for uniform `sen` or uniform `siz`.
- **Stiff calque (`"Masada zaman bırakmayı durdurun"` / `"Hör auf, Zeit auf dem Tisch zu lassen"`)**: rewrite around the real stake (`"Boşa giden dakikaları geri kazan"` / `"Keine Renderzeit mehr verschenken"`).
- **German `Sie` headline overflows `9:16` button (`"Probieren Sie es jetzt aus"`)**: use crisp neutral German infinitive CTA (`"JETZT TESTEN"` — `12` chars, register-safe for everyone).

## Checklist
- [ ] Second-person pronouns and verb endings stay `100%` consistent with `formality_register` from hook to CTA.
- [ ] Idioms and marketing clichés are rewritten natively around concrete verbs/stakes.
- [ ] Visual cue highlights align with target-language noun/metric word order (`SOV` / `V2`).
- [ ] Literal CLI commands, paths, and schema keys remain untranslated.

## Worked examples
- **Example 1 (`hook` + `cta` transcreation across `en` / `tr` / `de`, `casual` creator tone)**:
  - `en`: Hook `"STOP RE-RENDERING EVERYTHING"` / CTA `"Run one edit today"`
  - `tr` (`sen`): Hook `"HER ŞEYİ BAŞTAN İŞLEME"` / CTA `"İlk sahneni bugün dene"`
  - `de` (`neutral_infinitive` headline + `du` sub): Hook `"NICHT ALLES NEU RENDERN"` / CTA `"Teste deine erste Szene"`
- **Example 2 (`formal` enterprise data story)**:
  - `tr` (`siz`): `" Raporunuzu üç adımda doğrulayın"` (consistent `-ın` plural/formal imperative throughout).
  - `de` (`Sie` / infinitive): `"Berichte in drei Schritten prüfen"` (clean infinitive heading) + `"Prüfen Sie Ihre Quellen vor dem Export."`

## Resources (load only if needed)
- [Six-language formality register and imperative paradigm guide](references/register-and-imperative-guide.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
