# Data Story (`data-story`)

Animated bar and comparison data plates with strict source provenance, tabular numeric clarity, and anti-aliased grid strokes across `9:16`, `16:9`, `1:1`, and `4:5`.

## Structural contract

1. **Baseline plate (`DATA` / `VERİ` / `DATEN`)** — Establishes baseline metrics with animated rising bars (`data-horizon`).
2. **Comparison plate (`02`)** — Highlights peak shift via accent color separation and `>= 2 px` grid lines.
3. **Takeaway beat (`03`)** — Distills the qualitative insight or verified finding cleanly inside safe reading-speed caps.

## Provenance and numeric formatting

- Quantitative assertions (`%`, `x`, multipliers, rankings) are backed by `sources.json` or brief-derived `prompt.json` `sources` entries so `claims_sourced` validates deterministically offline.
- Prompts without external numeric tables compile cleanly using qualitative structural labels without inventing unverified metrics.

## Wired skills

- `claims-must-be-sourced` — Prevents fabricated metrics and links claims to provenance.
- `numeric-unit-typography` — Tabular digit rhythm, locale percent placement, and clean unit spacing.
- `anti-aliasing-thin-lines` — Minimum `>= 2 px` grid strokes and `2x`/`3x` SSAA for production/hero masters.
- `reading-speed-audit` — Keeps labels well inside locale CPS caps.
- `contrast-audit` — Verifies WCAG foreground/background ratios across bars and labels.
- `frame-clock` — Exact integer frame distribution across scenes.
