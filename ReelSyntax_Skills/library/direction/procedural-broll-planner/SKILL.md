---
name: procedural-broll-planner
description: "Translate abstract narration claims into deterministic procedural visual plates—diagrams, metric counters, geometry, and layer stacks—when camera footage is absent."
metadata:
  category: direction
  stage: plan
  status: validated
  version: "2.0.0"
  aliases: "procedural broll,procedural b-roll,prosedürel ara görüntü,üretimsel görsel planlama,prozedurales B-Roll,synthetische Schnittbilder planen,b-roll procedimental,b-roll procédural"
  requires: ""
---

# Procedural B-Roll Planner

## Activation
Activate when a script or voiceover contains abstract concepts, metrics, system flows, or comparisons and the project has zero live-action footage, requiring 100% deterministic procedural visual coverage. Search aliases: `procedural broll`, `prosedürel ara görüntü`, `prozedurales B-Roll`. Do not activate when licensed camera footage already covers every beat.

## Decision rules
- **Zero-wallpaper rule**: never place an unrelated spinning shape behind spoken claims; map every spoken clause to a semantic visual archetype:
  - *Quantitative delta / ratio* -> animated bar/arc proportion plate (`signal-grid` / `data` primitive)
  - *Process / causation (`A -> B -> C`)* -> directed node-arrow state plate
  - *Spatial / structural hierarchy* -> z-depth `layer-stack` callout plate
  - *Threshold / rule boundary* -> split comparison frame (`pass` vs `fail` region)
  - *Focal statement / definition* -> high-contrast `kinetic-type` or `prism-monolith` anchor.
- **Visual state change budget**: every procedural plate held `> 2.2s` (`66` frames at `30/1`) must exhibit at least one motivated state transition (highlight shift, progress sweep, or camera parallax) so `freezedetect` and viewer attention stay active.
- **Seed determinism**: assign an explicit integer `seed` derived from project seed + scene index so re-renders produce bit-consistent procedural geometry.

## Parameters and defaults
- `max_static_hold_frames`: `45` frames (`1.5s` at `30/1`) before secondary motion or highlight step occurs.
- `plate_variety_window`: `2` (never repeat identical procedural recipe + layout geometry across `> 2` consecutive beats).
- `foreground_contrast_min`: `4.5:1` WCAG luminance ratio between procedural background elements and foreground typography.
- `background_density_cap`: `0.35` maximum edge/ink coverage inside text safe-zone boxes.

## Procedure
1. Segment the script into beat clauses and tag each clause with its semantic claim type (`metric`, `causal-flow`, `comparison`, `hierarchy`, `definition`).
2. Select the matching procedural recipe and primitive set (`rect`, `circle`, `arc`, `arrow`, `grid`, `line`) from the claim-to-plate table.
3. Reserve a low-clutter luminance pocket (`background_density_cap <= 0.35`) behind active `heading` / `subheading` bounds so procedural grid lines never slice through letterforms.
4. Schedule one primary motion anchor per beat synchronized to the beat's cue onset (`bar sweep`, `node highlight`, `card slide`), keeping secondary ambient motion subtle (`<= 12 px/s`).
5. Record recipe IDs, shape primitives, palette tokens, and integer seeds into `reel.json` scenes.

## Failure modes and fixes
- **Decorative noise competes with captions**: dim background procedural strokes to `<= 22%` contrast against the canvas base inside the caption safe box.
- **Literal cliché icons for every noun**: represent relationships (scale, bottleneck, filter, split) geometrically rather than stacking literal clipart silhouettes.
- **Unexplained freeze trigger on minimalist plate**: add a subtle `0.03` progress sweep or declare intentional stillness in `quality.exceptions.freeze`.

## Checklist
- [ ] Every beat maps its claim type to a motivated procedural visual archetype.
- [ ] Procedural strokes stay dimmed/cleared behind active text bounding boxes (`>= 4.5:1` text contrast).
- [ ] Consecutive scenes vary recipe or spatial composition within `plate_variety_window`.
- [ ] Explicit deterministic seeds and frame-locked cue animations are saved in `reel.json`.

## Worked examples
- **Example 1 (`18s` / `540f` audio-less architecture brief, EN)**: Beat 1 (`"3 requests hit the gateway"` -> 3 left-to-right arrows converging on a rounded rect), Beat 2 (`"Cache serves 2 instantly"` -> 2 green arcs rebounding in `18f`, 1 amber line continuing), Beat 3 (`"Latency drops 68%"` -> vertical bar shrinking from `100%` to `32%` height).
- **Example 2 (`15s` / `450f` finance explainer, DE)**: Beat 1 (`"Zinseszins schlägt Einmalzahlung"` -> `prism-monolith` hook), Beat 2 (`"Lineares Sparen vs. Kurve"` -> dual polyline sweep over `180f`), Beat 3 (`"Ab Jahr 7 kippt das Verhältnis"` -> vertical threshold marker at column 7).

## Resources (load only if needed)
- [Claim-to-procedural-plate mapping catalog](references/claim-to-plate-mapping.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
