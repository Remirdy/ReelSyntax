# Music Visualizer (`music-visualizer`)

Deterministic, bar-synced procedural visuals that respond to a musical grid with a `signal` bar field and `rings` arc orbits, for vertical (`9:16`), widescreen (`16:9`), square (`1:1`), and portrait (`4:5`) delivery.

## Structural contract

1. **Signal sections** — even-numbered sections use the `signal` recipe: a grid of vertical bars whose amplitude envelope breathes once per section.
2. **Arc sections** — odd-numbered sections use the `rings` recipe: tilted arc orbits that rotate slowly around the visual center.
3. **Bar kicker** — each section shows the starting bar (`BAR 01` / `ÖLÇÜ 01` / `TAKT 01`) beside a short title and an optional one-line mood subheading.

The same seed, prompt, and duration always produce identical frames.

## Bar grid

- Default grid: `120 BPM`; at `30 fps` one beat is `15` frames and one bar is `60` frames (`bar-grid-music-alignment`).
- Section lengths are quantized to whole bars (falling back to whole beats for very short pieces); remainder frames go to the final section so totals stay exact (`frame-clock`).
- A `harmonic_pluck` cue sounds on every bar downbeat, cycling through a pentatonic set (`220`, `262`, `294`, `330`, `392 Hz`).

## Flash safety

- No luminance flashes: the `signal` envelope completes `1.4` cycles per section and the `rings` tilt about `0.6`, so bar-length sections (`>= 2 s` at the default grid) move below `1 Hz`, and even the one-beat fallback (`0.5 s`) stays below `3 Hz`. Bar cues run at `0.5 Hz` (`flash-safety`).
- Only `cross_dissolve` transitions are used; `glitch`, `fade_white`, and other high-contrast cuts are excluded.
- Text and geometry colors keep their contrast against a non-black background (`contrast-audit`).

## Wired skills

- `music-visualizer` — Section structure and grid-driven response.
- `bar-grid-music-alignment` — Bar-quantized section boundaries and downbeat cues.
- `flash-safety` — Motion and transition rates below `3 Hz` with no full-frame flashes.
- `shader-loop-art` — Seamless, seed-deterministic procedural geometry.
- `frame-clock` — Integer frame totals on the bar grid.
- `contrast-audit` — Kicker and title contrast.
- `format-runner-protocol` — Approval gates before draft, full, and hero renders.
