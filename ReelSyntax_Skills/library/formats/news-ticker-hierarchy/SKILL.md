---
name: news-ticker-hierarchy
description: "Design structured news-brief layouts with clear primary-headline dominance, judder-free integer-pixel ticker crawls, source badges, and zero dual-reading overload."
metadata:
  category: formats
  stage: build
  status: validated
  version: "2.0.0"
  aliases: "news ticker hierarchy,broadcast ticker crawl,haber bandı hiyerarşisi,kayan alt bant düzeni,Nachrichtenticker-Hierarchie,Laufband-Layout gestalten,jerarquía de cintillo informativo,hiérarchie de bandeau d'actualité"
  requires: ""
---

# News Ticker Hierarchy

## Activation
Activate when building `news-ticker` briefings, release status digests, or market/metric updates combining a primary story viewport, lower-third headline banner, and bottom scrolling crawl bar. Search aliases: `news ticker hierarchy`, `haber bandı hiyerarşisi`, `Nachrichtenticker-Hierarchie`. Do not activate when `constraints.no_text` is true.

## Decision rules
- **Exact integer pixels-per-frame crawl speed (zero shimmer/judder law)**: a horizontal ticker scrolling at fractional `3.7 px/frame` alternates `3 px` and `4 px` glyph advances, causing severe strobing judder across every vertical letter stem! Always lock ticker velocity to an **exact integer `px/frame`**:
  - `30/1` fps at `1080w` (`9:16`): `4 px/frame` (`120 px/s`) or `5 px/frame` (`150 px/s`).
  - `30/1` fps at `1920w` (`16:9`): `5 px/frame` (`150 px/s`) or `6 px/frame` (`180 px/s`).
  - `60/1` fps: `3 px/frame` (`180 px/s`) — smoothest broadcast crawl.
- **Strict 3-tier attentional hierarchy (prevent cognitive split)**:
  1. `Tier 1 — Main Viewport (`70%` area)`: `1` bold visual/chart or photo + `<= 6`-word headline banner (`48–60 px`).
  2. `Tier 2 — Category / Source Pill (`top-left` or above banner)`: static `2–3` word topic + verified source label (`28–32 px`).
  3. `Tier 3 — Bottom Crawl Ticker (`height = 0.055h`)`: short secondary bullet items separated by `"  •  "` (`<= 8` words per bullet); **never** put essential thesis numbers *only* in the scrolling ticker while speaking a different number!
- **`--reduced-motion` static-flip mode**: when `--reduced-motion` is active, replace horizontal continuous crawl with discrete `3.0s` (`90`-frame) static item flips (`8`-frame opacity swap) inside the bottom bar!

## Parameters and defaults
- `crawl_px_per_frame_30fps`: `4` px (`9:16` `1080w`) or `6` px (`16:9` `1920w`) — exact integer!
- `banner_bottom_y_16x9`: `0.86 * height` (crawl sits `0.86h..0.92h`, headline banner `0.74h..0.86h`).
- `banner_bottom_y_9x16`: `0.79 * height` (crawl sits `0.74h..0.795h` **above** the bottom `18%` social UI overlay zone!).
- `bullet_separator`: `"   ◆   "` or `"   •   "`.
- `banner_contrast_min`: `7.0:1` (`#F8FAFC` on `#0F172A` navy/charcoal bar; `#0F172A` on `#FACC15` or `#38BDF8` category tag).

## Procedure
1. Partition the canvas into non-overlapping zones (`viewport`, `category_source_tag`, `headline_banner`, `crawl_strip`) respecting `vertical-safe-zones` (`<= 0.80h` bottom edge on `9:16`).
2. Pre-render the concatenated crawl string (`item_1 ◆ item_2 ◆ item_3 ◆ `) once into a horizontal strip buffer `strip_img` at `1.0x` scale so per-frame blitting shifts by exact integer `dx = -(frame * crawl_px_per_frame) % strip_width` (`zero` sub-pixel blur, `10x` faster render!).
3. Keep the `headline_banner` static throughout each story beat (`>= 90` frames / `3.0s`) while the viewport plate updates on beat cuts (`inverted-pyramid` order: Lead Fact -> Key Metric -> Context -> Takeaway).
4. Display an explicit `Source:` / `Kaynak:` / `Quelle:` badge whenever quantitative claims appear (`claims-must-be-sourced`).
5. Implement `--reduced-motion` fallback switching the crawl strip to `90`-frame static bullet pagination.

## Failure modes and fixes
- **Crawl stutters and blurs eyes**: change float `speed_px_sec = 137.0` to exact integer `px_per_frame = 4` (`120 px/s`) or `5` (`150 px/s`) and blit from a pre-rasterized strip at integer `x`.
- **Bottom ticker on `9:16` (`y = 1820 px`) is completely hidden under platform caption UI**: place `9:16` lower-third + ticker stack at `y = 0.66h..0.795h` (`1267..1526 px`) with clean dark slate below `1526 px`.
- **Viewer cannot read fast `2`-line headline AND fast crawl AND chart simultaneously**: limit `headline_banner` to `1` concise line (`<= 34` chars) and keep crawl bullets secondary (`3–6` words each).

## Checklist
- [ ] Horizontal ticker advances by an exact integer `px/frame` from a pre-rendered strip buffer.
- [ ] On `9:16`, headline banner and crawl strip sit completely above `0.82h` (`>= 18%` bottom clearance).
- [ ] Main headline is `1` static concise line (`>= 7.0:1` contrast) with localized `Source:` attribution when citing data.
- [ ] `--reduced-motion` switches continuous crawl to `3.0s` static item pagination.

## Worked examples
- **Example 1 (`16:9` `1920x1080` `18s` release briefing at `30/1` fps, EN)**: Viewport (`0..800 px`) shows `3` sequential metric cards (`180f` each); static category pill `"RELEASE 0.2"`, headline banner (`800..920 px`) `"SCENE CACHE CUTS REBUILD TIME BY 74%"`, `Source: Local Benchmark Suite`, crawl strip (`920..982 px`) scrolling at exact `6 px/frame` (`180 px/s`).
- **Example 2 (`9:16` `1080x1920` `15s` daily tech brief, DE)**: Kopfbereich frei ab `y = 240 px`, Hauptgrafik `240..1260 px`, Schlagzeilenbalken `1260..1420 px` (`"NEUES SCHEMA VALIDIERT IN 4 MS"`), Laufband `1420..1510 px` mit `4 px/Frame` (`120 px/s`), unterer Sicherheitsbereich `1510..1920 px` ruhig abgedunkelt.

## Resources (load only if needed)
- [Broadcast & vertical ticker zone coordinates and integer crawl speeds](references/ticker-speed-and-zone-spec.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
