---
name: cultural-adaptation-audit
description: "Audit localized video variants for ambiguous numeric dates, measurement systems, currency assumptions, directional progression cues, and region-locked references."
metadata:
  category: qa
  stage: review
  status: validated
  version: "2.0.0"
  aliases: "cultural adaptation audit,localization qa checklist,kültürel uyarlama denetimi,yerelleştirme kalite kontrolü,Kulturadaptions-Prüfung,Lokalisierungs-Checkliste,auditoría de adaptación cultural,audit d'adaptation culturelle"
  requires: ""
---

# Cultural Adaptation Audit

## Activation
Activate during pre-release review (`review` / `qc` stage) whenever delivering multi-language variants or internationalized templates so locale-specific ambiguities, US-centric units/dates, or visual-direction assumptions never confuse target viewers. Search aliases: `cultural adaptation audit`, `kültürel uyarlama denetimi`, `Kulturadaptions-Prüfung`.

## Decision rules
- **Ban slash-numeric dates (`04/05/2026` is April 5 in US and May 4 in Europe/Turkey)**: always format dates unambiguously as ISO `2026-05-04` in technical logs/badges or localized month-name form (`4 May 2026`, `4 Mayıs 2026`, `4. Mai 2026`).
- **Metric / unit localization**: convert imperial-only examples (`72°F`, `60 mph`, `12 oz`) to metric (`22 °C`, `100 km/h`, `350 ml`) for `tr`, `de`, `es`, `fr`, `pt` audiences unless quoting a locked historical/primary source (in which case show metric in parentheses).
- **24-hour vs 12-hour clock**: use `24`-hour clock (`14:30`, `14.30` TR) for `tr`, `de`, `fr`, `es`, `pt` rather than `"2:30 PM"`.
- **Symbolic & gesture neutrality**: avoid region-specific postal/tax/legal acronyms (`401k`, `SSN`, `ZIP` -> use `"postal code"` / `"posta kodu"` / `"PLZ"`), hand-gesture icons with divergent regional meanings, or red-up / green-down vs green-up / red-down ambiguity without explicit `+` / `−` or `"FASTER"` / `"SLOWER"` labels.
- **RTL layout flip awareness**: if preparing right-to-left (`ar`, `he`, `fa`) adaptations, mirror timeline progress arrows (`right -> left` progression) while keeping media transport icons and mathematical graphs (`+X` right) un-mirrored per RTL UI conventions.

## Parameters and defaults
- `date_style`: `"localized_month"` (`"4 Mayıs 2026"`, `"4. Mai 2026"`) or `"iso8601"` (`"2026-05-04"`).
- `unit_system_non_us`: `"metric"` (`°C`, `km`, `kg`, `ml`).
- `clock_format_eu_tr`: `"24h"`.
- `require_sign_with_color`: `true` (never rely on red/green color alone for good/bad deltas; pair with `▲`/`▼` or `+`/`−` + verbal qualifier).

## Procedure
1. Scan all scene copy (`heading`, `subheading`, `kicker`, `narration`, chart axes) for regex patterns matching slash dates (`\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b`), `AM/PM`, imperial units, and currency symbols.
2. Verify numeric decimal/grouping separators (`numeric-unit-typography`) match `video_lang` across both text cards and chart axis labels.
3. Check metaphors, holiday/season assumptions (for example `"this summer in July"` for global southern-hemisphere copy), and regional institutional acronyms; replace with universally grounded equivalents.
4. Confirm color-coded deltas include explicit textual/directional labels (`"−42% render time"` + check icon) so neither color-vision deficiency nor regional color conventions invert the takeaway.
5. Record audit findings (`pass`, `review`, `fail`) per variant language before final render sign-off.

## Failure modes and fixes
- **Event card reads `"Launch: 03/07"` across EN/TR/DE variants**: replace with `"7 Mar"` / `"7 Mart"` / `"7. März"` (or `"2026-03-07"`) so nobody misreads July 3 vs March 7.
- **Translated Turkish chart keeps `"$"` and `"miles"` in generic example**: adapt example to `"₺"` / `"€"` or currency-neutral units (`"birim"`, `"km"`, `"saniye"`), **never** altering real cited data values without unit conversion math!
- **Untranslated English badge (`"NEW"`, `"STEP 1"`) left inside DE/TR scene**: verify `kicker` strings come from localized format/locale tables (`"YENİ"` / `"NEU"`, `"ADIM 01"` / `"SCHRITT 01"`).

## Checklist
- [ ] Zero ambiguous `MM/DD` vs `DD/MM` numeric slash dates appear on screen.
- [ ] Clock format (`24h` vs `12h`) and measurement units (`°C`, `km`, `ml`) match target locale.
- [ ] Zero leftover English kickers (`STEP`, `HOOK`, `NEW`) remain inside non-English variants.
- [ ] Positive/negative deltas pair color with explicit sign and verbal label.

## Worked examples
- **Example 1 (`en` -> `de` + `tr` release announcement audit)**: Source `"Ships 06/11 at 3 PM — 2.5 miles range"` -> Flagged `06/11`, `3 PM`, `miles`. Adapted `de`: `"Start am 11. Juni um 15:00 Uhr — 4 km Reichweite"`; `tr`: `"11 Haziran saat 15.00'te yayında — 4 km menzil"`.
- **Example 2 (Leftover badge audit)**: Automated scan catches `scenes[0].params.kicker == "HOOK"` on `delivery.language == "tur"` -> Replaced with `"DİKKAT"`.

## Resources (load only if needed)
- [Localization hazard and cultural audit checklist](references/localization-hazard-checklist.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
