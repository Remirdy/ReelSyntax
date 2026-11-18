# Lyric Video (`lyric-video`)

Phrase-timed typographic lyric videos where every lyric line is one card on a musical beat grid, for vertical (`9:16`), widescreen (`16:9`), square (`1:1`), and portrait (`4:5`) delivery.

## Lyrics rights boundary

- Use only lyrics you wrote yourself, lyrics in the public domain, or lyrics you have a written license to display.
- Do not paste copyrighted song lyrics you do not control. The offline planner only reuses text from your own brief; it never fetches or reproduces third-party lyrics.
- The bundled examples use an original, brand-free demo verse (`Lanterns drift above the quiet water`) written for this package.

## Structural contract

1. **One phrase per card** — each scene is a `kinetic-type` card with a line kicker (`LINE 01` / `DİZE 01` / `ZEILE 01`), the hook word as the display `heading`, and the rest of the phrase as the `subheading`.
2. **Typography hierarchy** — display heading for the stressed word, lighter body subheading for the remaining phrase, and a small accent kicker for line position (`burned-in-caption-styling`).
3. **Soft phrase changes** — `6`-frame `cross_dissolve` between lines; no flashes or hard strobes.

## Beat grid

- Default grid: `120 BPM`; at `30 fps` one beat is `15` frames and one bar is `60` frames (`bar-grid-music-alignment`).
- Every card length is quantized to whole beats, so phrase changes land on beats; any remainder frames are absorbed by the final card so the total stays exact (`frame-clock`).
- A `harmonic_pluck` cue marks the first frame of every phrase.

## Readability defaults

- Keep each card at or below the locale caption ceiling (`en` `20`, `tr` `18`, `de` `17` CPS); the `reading-speed` QC rule is active.
- Split long phrases across two cards instead of shrinking type; avoid single-word orphans on the subheading line (`orphan-widow-line-balance`).

## Wired skills

- `lyric-video` — Phrase-level timing and display hierarchy.
- `burned-in-caption-styling` — Stable, high-contrast lyric text without active-word jitter.
- `bar-grid-music-alignment` — Beat-quantized scene boundaries without cumulative drift.
- `contrast-audit` — Text contrast against the card background.
- `frame-clock` — Integer frame totals on the beat grid.
- `orphan-widow-line-balance` — Balanced phrase splits.
- `format-runner-protocol` — Approval gates before draft, full, and hero renders.
- `locale-aware-casing` — Turkish `İ`/`ı` and German display casing.
- `font-fallback-chain` — Zero missing glyphs for Turkish and German diacritics.
