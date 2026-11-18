# Photo Slideshow (`photo-slideshow`)

Warm, beat-paced photo and chapter slideshows for travel recaps, event albums, portfolios, and milestone retrospectives across `9:16`, `1:1`, `4:5`, and `16:9`.

## Creative intent and structure

Interleaves editorial chapter cards with centered high-resolution photo plates (`layer-stack`) over a cohesive matte backdrop:

1. **Title card** — Sets date, location, or theme with warm arpeggio accompaniment.
2. **Photo plates** — User images placed in `assets/` (auto-registered as `User-Provided` in `.reelsyntax/asset-licenses.json`), or deterministic `CC0-1.0` starter plates (`photo-plate-warm`, `photo-plate-cool`) when previewing before photos are added.
3. **Closing memory card** — Gentle `cross_dissolve` resolve with generous reading hold.

## Pacing and transition defaults

Treat the values below as adjustable defaults:

- **Hold per slide:** `60–90` frames (`2.0–3.0 s` at `30 fps`) so viewers can absorb composition details before the next dissolve.
- **Transitions:** `8–12` frame `cross_dissolve` between chapters and plates.
- **Framing:** Keep `9%` matte border (`0.82` inner plate scale) so EXIF-transposed portraits and squares sit cleanly inside vertical and horizontal safe zones without cropping faces.

## Wired skills

- `frame-clock` — Exact slide durations aligned to harmonic beat cues.
- `contrast-audit` — Accessible matte and caption contrast.
- `beat-synced-editing` — Dissolve anchor alignment with musical downbeats.
- `j-cut` — Continuous audio bed bridging across slide dissolves.
- `vertical-safe-zones` — Safe framing margins around centered photo plates.
- `easing-design` — Smooth chapter card entrances.

## Failure modes and fixes

- **Rotated mobile photos:** `render_layers` applies `ImageOps.exif_transpose` automatically before scaling.
- **Unregistered photo files:** Place photos inside `<project>/assets/` before running `make` or register external files via `reelsyntax assets register <project> <photo>`.
