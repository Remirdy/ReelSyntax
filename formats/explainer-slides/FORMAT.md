# Explainer Slides (`explainer-slides`)

Structured chapter-by-chapter lessons that turn one topic into a short sequence of readable slides with visual proof beats, for widescreen (`16:9`), vertical (`9:16`), square (`1:1`), and portrait (`4:5`) delivery.

## Structural contract

1. **Opening chapter (`CHAPTER 01/N` / `BÖLÜM 01/N` / `KAPITEL 01/N`)** — `kinetic-type` title slide that states the single learning goal in two to three words.
2. **Proof chapters (`02 .. N-1`)** — `assembly` procedural plates that build the idea step by step beside the text column; one concept per slide (`microlearning-chunking`). Enter with a `6`-frame `slide_left`.
3. **Recap slide (`RECAP` / `ÖZET` / `FAZIT`)** — `kinetic-type` summary that restates the takeaway, entered with an `8`-frame `cross_dissolve`.

The progress kicker always shows the chapter index and the chapter count, so viewers know where they are in the lesson.

## Timing defaults (adjustable)

- **Duration:** `15–180 s`; default chapter weights `3 : (5, 4, 5, ...) : 4` so the opening slide is brisk, proof slides get the longest holds, and the recap settles (`rhythm-density-map`).
- **Reading speed:** keep `heading + subheading` at or below the language-profile caption ceiling (`en` `20`, `tr` `18`, `de` `17` CPS); the `reading-speed` QC rule fails slides that exceed it (`reading-speed-audit`).
- **Frame budget:** chapter durations are integer frames that always sum to the requested length (`frame-clock`).

## Claims and sources

The `claims-must-be-sourced` QC rule is active. Any quantitative claim in a `heading`, `subheading`, or `kicker` (for example `40%`, `3x`, `#1`) fails QC unless the project contains a non-empty `sources.json` or `prompt.json` `sources` list. Prefer qualitative wording or attach sources before delivery.

## Typography and safe area

- Keep headings to one short line; long headings spill into the subheading instead of shrinking type below legibility.
- Kickers and headings must clear WCAG contrast (`>= 3.0:1` display, `>= 4.5:1` body) against the slide background (`contrast-audit`).
- Width budgets are measured with the active system font at compile time; examples keep a margin for wider Linux fonts.

## Wired skills

- `educational-explainer` — One learning goal, concrete proof, and a closing recap.
- `microlearning-chunking` — One concept per slide with a visible chapter index.
- `procedural-broll-planner` — Motivated procedural `assembly` plates for abstract proof beats.
- `rhythm-density-map` — Uneven chapter weights instead of metronomic slide lengths.
- `reading-speed-audit` — Per-slide characters-per-second against the locale profile.
- `claims-must-be-sourced` — Quantitative claims require attached sources.
- `contrast-audit` — Foreground, kicker, and background contrast checks.
- `frame-clock` — Integer frame budgeting with exact totals.
- `format-runner-protocol` — Approval gates before draft, full, and hero renders.
- `locale-aware-casing` — Turkish and German display casing for kickers and headings.
- `font-fallback-chain` — Zero missing glyphs for Turkish and German diacritics.
