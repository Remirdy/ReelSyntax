# Kinetic Typography (`kinetic-typography`)

High-contrast, rhythm-driven typographic statements for quotes, tips, manifestos, and concise summaries across vertical (`9:16`), square (`1:1`), portrait (`4:5`), and widescreen (`16:9`) canvases.

## Creative intent and structure

Each reel divides into 3 to 8 sequential statement cards:

1. **Opening claim (`01`)** — Immediate thesis in two to four words, paired with a grounded transient accent on frame `0`.
2. **Supporting beats (`02 .. N-1`)** — Concrete points, contrast pairs, or numbered takeaways paced to comfortable reading speed.
3. **Closing takeaway (`N`)** — Distilled conclusion held long enough for full comprehension without rushing the final cut.

## Timing and reading-speed defaults

Treat the values below as adjustable defaults and tune per audience and language profile (`lang-profiles/`):

- **Minimum card hold:** `45` frames (`1.5 s` at `30 fps`) for two-word hooks; `60–90` frames (`2.0–3.0 s`) for cards with a subheading.
- **Target reading speed:** `<= 15` characters per second (`en`), `<= 14` CPS (`tr`, accounting for agglutinative suffixes), and `<= 13` CPS (`de`, accounting for compound nouns).
- **Transitions:** `6–8` frame `slide_left` or `cross_dissolve` between cards; hard cut when contrasting an opposing claim.

## Typography and safe-area rules

- Keep primary `heading` copy concise so it fits cleanly inside the left editorial column (`x in [0.07w, 0.50w]`) without clipping at `draft` or `snapshot` resolutions.
- Enforce WCAG contrast ratios (`>= 4.5:1` for `subheading` body copy, `>= 3.0:1` for bold display `heading` and `kicker` numerals) and keep dark backgrounds above the broadcast black-detection floor (`Y >= 44/255`).
- Apply locale-aware casing (`locale_upper`) for Turkish (`i -> İ`, `ı -> I`) and German (`ß -> SS` only when all-caps display is active).

## Wired skills

- `kinetic-typography` — Statement hierarchy, entrance damping, and hold pacing.
- `kinetic-layout-choreography` — Shared alignment rails and tight multi-element stagger builds.
- `rhythm-density-map` — Alternating brisk burst cuts with comprehension holds.
- `scene-duration-floor-ceiling` — Net readability floors accounting for transition overlaps.
- `color-script-progression` — Perceptual OKLCH lightness and accent trajectory across acts.
- `idea-angle-framing` — Single sharp editorial angle and scope boundary before scripting.
- `prompt-to-storyboard` — Frame-quantized card breakdown from natural-language briefs.
- `lang-detect-and-route` — Independent UI and target video language resolution.
- `frame-clock` — Integer frame budgeting and drift-free beat boundaries.
- `contrast-audit` — Foreground/background perceptual contrast verification.
- `vertical-safe-zones` — Platform overlay clearance on `9:16` deliverables.
- `easing-design` — Critically damped spring entrances without distracting overshoot.
- `font-fallback-chain` — Zero-`.notdef` diacritic coverage across supported scripts.

## Common failure modes and fixes

- **Crowded heading line:** Spill secondary words into `subheading` rather than shrinking display type below legibility thresholds.
- **Premature cut before comprehension:** Increase `duration_frames` or trim filler adjectives so every card finishes settling before the outgoing transition starts.
- **Ultra-black background false alarm:** Lift near-black `#0a0a0c` backgrounds to charcoal slate (`#2b303a`) so dark cards read cleanly on mobile OLED screens and pass `blackdetect` checks.
