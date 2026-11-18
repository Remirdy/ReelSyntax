# News Ticker Briefing (`news-ticker`)

Structured broadcast briefing with a telemetry viewport, category/source badge, static headline banner, and integer-pixel bottom ticker crawl (switching to static pagination under `--reduced-motion`).

## Layout & safe-zone contract

- **Strict `9:16` bottom clearance (`>= 18%`):** On vertical deliveries, the telemetry viewport, category badge, headline banner, and crawl strip all sit strictly inside `y <= 0.80h`, leaving the bottom `20%` unobstructed above platform UI chrome.
- **Integer-pixel crawl:** Continuous crawls pre-rasterize a strip buffer and shift by an exact integer `px/frame` (`round(4 * width / 1080)`), preventing fractional-pixel stem judder.
- **`--reduced-motion` static pagination:** Automatically switches the continuous horizontal crawl to discrete static pages with page-index indicators (`1/N`).

## Wired skills

- `news-ticker-hierarchy` — 3-tier attention hierarchy and integer-px crawl buffer.
- `lower-thirds` — High-contrast banner and category tag geometry.
- `claims-must-be-sourced` — Provenance checks when numeric claims appear.
- `contrast-audit` — Dynamic badge contrast and `>= 7:1` banner readability.
- `reading-speed-audit` — Balanced headline and bullet length per beat.
- `frame-clock` — Exact integer frame allocation across briefing segments.
