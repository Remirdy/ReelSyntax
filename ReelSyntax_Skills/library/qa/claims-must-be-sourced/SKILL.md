---
name: claims-must-be-sourced
description: "Require verifiable source citations in project provenance and on-screen attribution for every quantitative statistic, multiplier, benchmark, or factual claim."
metadata:
  category: qa
  stage: review
  status: validated
  version: "2.0.0"
  aliases: "claims must be sourced,quantitative claim citation,iddialar kaynaklı olmalı,sayısal veri kaynak doğrulama,Quellenpflicht für Zahlenangaben,Belegprüfung für Behauptungen,citas obligatorias para datos,sources requises pour affirmations"
  requires: ""
---

# Claims Must Be Sourced

## Activation
Activate whenever planning, compiling, or running `qc` on `data-story`, `news-ticker`, `product-promo`, or `explainer-slides` projects containing percentages (`98%`), multipliers (`3.4x`), currency figures, rankings, or scientific/benchmark assertions. Search aliases: `claims must be sourced`, `iddialar kaynaklı olmalı`, `Quellenpflicht für Zahlenangaben`.

## Decision rules
- **Zero fabricated metrics**: if a user brief requests `"a chart about battery life"` without supplying numbers, either use qualitative structural labels (`"Baseline"` vs `"Optimized"` without fake percentages) OR require explicit user-supplied `sources.json` / `data.csv` before rendering numeric claims.
- **Machine-verifiable provenance link**: every quantitative token matching `%`, `x faster`, currency, or benchmark delta in `heading`, `subheading`, `kicker`, or `narration` must map to an entry in `<project>/sources.json` or `prompt.json` `sources[]` (`claim`, `source`, `date_or_version`).
- **Visible viewer citation on data & news formats**: on `data-story` and `news-ticker` scenes displaying quantitative assertions, render a legible `Source: <short_citation>` (`Kaynak:`, `Quelle:`) footnote (`>= 24 px` at `1080p`, `>= 4.5:1` contrast) so viewers never have to trust unattributed numbers.
- **Baseline & condition disclosure**: never state `"3x faster"` in isolation if the source specifies a bounded condition; include the qualifier in `subheading` or `source` (`"Local 4-scene draft rebuild, 2026-11"`).

## Parameters and defaults
- `sources_file`: `<project>/sources.json`.
- `citation_min_font_px_1080p`: `24` px (`>= 4.5:1` WCAG contrast).
- `unverified_number_policy`: `"fail_qc"` when `claims-must-be-sourced` rule is active in format `qc_rules`.
- `qualitative_fallback_allowed`: `true` during `idea`/`script` draft only when zero fake digits appear on screen.

## Procedure
1. Scan all scene copy and narration against quantitative claim patterns (`%`, `\d+(\.\d+)?x`, currency symbols, comparative superlatives tied to numbers).
2. Cross-reference every detected claim against `sources.json` (`[{"claim": "...", "source": "...", "url_or_artifact": "..."}]`).
3. Verify the rendered number matches the cited source value exactly (including unit conversions checked by `cultural-adaptation-audit`).
4. Add a concise localized `Source:` / `Kaynak:` / `Quelle:` caption on the visual frame carrying the metric.
5. Run `reelsyntax qc --rules claims-must-be-sourced` and confirm `claims_sourced == pass`.

## Failure modes and fixes
- **Brief compiler invents `"87% of teams prefer..."` to fill a template slot**: forbid numeric invention in storyboard rules; emit qualitative contrast (`"Manual rebuild"` vs `"Cached scene rebuild"`) until real measurements are provided.
- **`sources.json` exists but is empty `[]`**: `check_claims_sourced` rejects empty ledgers (`status: fail`); populate concrete claim-to-source records.
- **Tiny `11 px` `#475569` source footnote unreadable after H.264 encode**: raise footnote to `>= 24 px` and `>= 4.5:1` contrast.

## Checklist
- [ ] Zero invented percentages, multipliers, or rankings appear anywhere in `reel.json`.
- [ ] Every quantitative claim maps to a non-empty record in `sources.json` or `prompt.json`.
- [ ] Data and news scenes display a legible localized `Source:` / `Kaynak:` / `Quelle:` label (`>= 24 px`).
- [ ] `qc` check `claims_sourced` returns `pass`.

## Worked examples
- **Example 1 (`product-promo` benchmark card, EN)**: Scene heading `"74% FASTER REBUILDS"`, subheading `"1-scene text edit on 4-scene 1080p30 project"`, `sources.json`: `[{"claim": "74% FASTER REBUILDS", "source": "Local cache benchmark v0.2 (3.1s vs 11.9s)"}]` -> `claims_sourced: pass`.
- **Example 2 (Prompt without numbers, DE)**: Brief `"Zeige warum Caching Zeit spart"` -> Storyboard uses visual `4`-block diagram (`3` blocks green `"AUS CACHE"`, `1` block amber `"NEU BERECHNET"`) instead of inventing a fake percentage.

## Resources (load only if needed)
- [`sources.json` provenance ledger schema](references/sources-ledger-schema.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
