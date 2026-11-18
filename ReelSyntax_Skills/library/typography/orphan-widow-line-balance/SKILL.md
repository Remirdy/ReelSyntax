---
name: orphan-widow-line-balance
description: "Balance multi-line headings, subheadings, and captions using optical pixel-width ratios and linguistic phrase-break penalties so trailing single-word orphans never appear."
metadata:
  category: typography
  stage: build
  status: validated
  version: "2.0.0"
  aliases: "orphan widow balance,balanced line wrapping,yetim dul satır dengesi,dengeli satır kırma,Hurenkinder und Schusterjungen vermeiden,ausgewogener Zeilenumbruch,equilibrio de líneas huérfanas,équilibre des lignes orphelines"
  requires: ""
---

# Orphan Widow Line Balance

## Activation
Activate whenever wrapping multi-word `heading`, `subheading`, quote, or `2`-line subtitle strings into display boxes so greedy word-wrapping never leaves a lonely `2–4` character orphan word dangling on the final line. Search aliases: `orphan widow balance`, `yetim dul satır dengesi`, `ausgewogener Zeilenumbruch`. Do not activate when `constraints.no_text` is true.

## Decision rules
- **Ban greedy-wrap orphans**: a greedy wrapper fills line 1 to `98%` width and drops `"now."` (`11%` width) onto line 2; reject any multi-line wrap where `last_line_px / max_line_px < 0.38` when a `2`-word final line fits inside `max_column_px`.
- **Optical width ratio target**: for `2`-line blocks, aim for `min(w1, w2) / max(w1, w2) >= 0.65` (slightly bottom-heavy trapezoid `w2 >= w1` preferred for centered subtitles; slightly top-heavy `w1 >= w2` preferred for left-aligned editorial headings).
- **Syntactic phrase protection (never split tight pairs)**: apply high break penalties after prepositions, articles, conjunctions, negation particles, or between a number and its unit:
  - `en`: never end line 1 with `a`, `an`, `the`, `to`, `of`, `in`, `for`, `not`.
  - `tr`: never split postpositions (`için`, `ile`, `gibi`, `kadar`, `göre`) or question clitics (`mi`, `mı`, `mu`, `mü`) onto a lonely line away from their noun, and never split `"bir"` from its following noun when avoidable.
  - `de`: never end line 1 with `der`, `die`, `das`, `ein`, `eine`, `zu`, `mit`, `für`, `und`, `nicht`.
  - All locales: bind numbers to units (`"48 kHz"`, `"24 fps"`, `"%80"`).

## Parameters and defaults
- `min_last_line_ratio`: `0.38` (`>= 0.65` target balance on `2`-line captions).
- `clitic_preposition_penalty`: `400.0` (squared-slack cost units; strongly discourages dangling function words).
- `punctuation_break_bonus`: `-120.0` (strongly prefers breaking right after `,`, `;`, `:`, `—`, `-`).
- `max_subheading_lines`: `3` (`2` preferred).

## Procedure
1. Replace regular spaces inside inseparable numeric/unit pairs (`"30 fps"`, `"14 LUFS"`, `"100 MB"`) with non-breaking spaces (` `).
2. Enumerate candidate line-break partitions yielding the minimum required line count `K = ceil(total_px / max_column_px)` (typically `K = 2` or `3`).
3. Score each valid partition (where every line `<= max_column_px`) by minimizing `sum((mean_px - line_px)^2) + linguistic_break_penalties`.
4. Verify `last_line_px / max(line_px) >= min_last_line_ratio` whenever `total_words >= 4`.
5. Render the optimal partition and record final multi-line `bounds` for safe-zone inspection.

## Failure modes and fixes
- **Greedy wrap produces `"Deliver frame-accurate masters / fast"` (`94%` / `14%`)**: balanced DP wrap selects `"Deliver frame-accurate / masters fast"` (`61%` / `47%`, ratio `0.77`).
- **Preposition dangles at end of line 1 (`"Built for the / local studio"`)**: `clitic_preposition_penalty` shifts break before `"for"` -> `"Built / for the local studio"` or `"Built for / the local studio"` (`"Built for"` < `"Built"`? Wait: `"Built for"` keeps `"the local studio"` intact -> `"Built for / the local studio"`!).
- **Number separated from unit (`"Render at 60
fps"`)**: ` ` binds `"60 fps"` as one atomic token.

## Checklist
- [ ] Numeric + unit pairs are bound with ` ` before wrapping.
- [ ] Multi-line blocks achieve `last_line_px / max_line_px >= 0.38` (`>= 0.65` on `2`-line captions).
- [ ] Articles, prepositions, postpositions (`için`, `ile`), and negations never dangle at line ends.
- [ ] Clause punctuation (`,`, `:`, `-`) is preferred as the primary break seam.

## Worked examples
- **Example 1 (`en` `2`-line subheading)**: `"Verify every rendered frame before final export"` -> Greedy: `"Verify every rendered frame before final / export"` (`orphan!`). Balanced DP: `"Verify every rendered frame / before final export"` (`28` / `19` chars, preposition `"before"` starts line 2 cleanly).
- **Example 2 (`tr` `2`-line caption)**: `"Yüksek kontrastlı başlıklar mobil ekranda hızla okunur"` -> Balanced DP: `"Yüksek kontrastlı başlıklar / mobil ekranda hızla okunur"` (`27` / `26` chars, `0.96` width ratio, noun phrase + verb phrase cleanly separated).

## Resources (load only if needed)
- [Dynamic-programming balanced line breaker algorithm](references/dp-line-breaker.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
