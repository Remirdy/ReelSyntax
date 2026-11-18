---
name: kinetic-layout-choreography
description: "Coordinate multi-element grid entrances, shared alignment rails, 3-to-5-frame stagger offsets, and clean simultaneous exits for typographic and diagram cards."
metadata:
  category: motion
  stage: build
  status: validated
  version: "2.0.0"
  aliases: "kinetic layout,staggered grid choreography,kinetik yerleşim koreografisi,kademeli ızgara hareketi,kinetisches Layout,gestaffelte Raster-Choreografie,coreografía de diseño cinético,chorégraphie de grille cinétique"
  requires: ""
---

# Kinetic Layout Choreography

## Activation
Activate when animating multi-part editorial cards (`kicker` + `heading` + divider rule + `subheading` + metric badge) so elements enter along disciplined spatial rails rather than flying in from four competing directions. Search aliases: `kinetic layout`, `kinetik yerleşim koreografisi`, `kinetisches Layout`. Do not activate when `constraints.no_text` is true.

## Decision rules
- **Single dominant motion vector per card**: translate all text/rule elements along one shared axis (`+Y` upward rise of `18–28 px` or `+X` left-rail reveal), never mixing left-fly, top-drop, spin, and bounce on the same card.
- **Tight stagger budget**: stagger sequential hierarchy levels (`kicker -> heading -> rule -> subheading`) by `3–5` frames (`0.10s–0.17s` at `30/1` fps) and finish *all* entrance motion within the first `22` frames (`0.73s`) so `>= 65%` of scene duration is calm, readable hold.
- **Fast unified exit**: never reverse-stagger 4 elements slowly on exit (`20+` frames wasted); clear the card together in `6–8` frames or cut cleanly on the beat.
- **Critically damped deceleration**: use `cubic_out` (`1 - (1 - u)^3`) or critically damped spring (`zeta = 1.0`) — zero rubbery overshoot on body or data copy.

## Parameters and defaults
- `shared_left_rail_x`: `0.08` normalized canvas width (`9:16` and `16:9` editorial alignment).
- `stagger_step_frames`: `4` frames at `30/1` fps (`3–5` frames).
- `element_entrance_frames`: `12` frames (`0.40s` at `30/1` fps).
- `max_total_build_frames`: `22` frames (`kicker` starts at `0f`, `subheading` settles by `22f`).
- `rise_offset_px`: `22` px at `1080p` (`0.02 * width`, scaled proportionally at draft/snapshot sizes).

## Procedure
1. Snap every element on the card to at most `2` vertical alignment rails (for example `x = 0.08w` primary rail and `x = 0.56w` metric rail) and a `8 px` baseline rhythm.
2. Assign entrance start frames in reading-hierarchy order: `kicker` (`f = 0..10`), divider line sweep (`f = 2..14`), `heading` (`f = 4..16`), `subheading` (`f = 8..20`).
3. Mask or opacity-ramp (`cubic_out`) each element over `rise_offset_px` upward translation; verify zero bounding-box collision at every intermediate frame `f = 0..22`.
4. Hold exact pixel lock across `f = 22 .. duration - exit_frames` so eye fixation is effortless.
5. Clear simultaneously via cut or `6–8` frame card transition into the next scene.

## Failure modes and fixes
- **Slow cascade takes `48` frames (`1.6s`) to finish building**: compress `stagger_step_frames` from `12f` down to `4f` so the whole hierarchy settles by frame `20`.
- **Elements fly in from left, right, top, and bottom ("pinball slide")**: unify all entrances to `+22 px` vertical masked rise along `shared_left_rail_x`.
- **Scale-coupled offset breaks draft preview**: express offsets as fractions of canvas height (`0.012 * height`) rather than hardcoded `1080p` pixel constants.

## Checklist
- [ ] Card elements snap to `<= 2` vertical alignment rails.
- [ ] All elements share one unified entrance axis and critically damped `cubic_out` curve.
- [ ] Entire multi-element build completes by frame `22` (`<= 0.75s` at `30/1` fps).
- [ ] Offsets scale proportionally across `snapshot`, `draft`, and `production` resolutions.

## Worked examples
- **Example 1 (`72` frames / `2.4s` vertical statement card, `30/1` fps)**: Rail `x = 0.08w`. `0–10f` kicker `"02 / CACHE"` fades in, `2–14f` `2px` accent rule sweeps `w = 0 -> 0.42w`, `4–16f` heading `"SKIP REDRAWS"` rises `0.012h -> 0`, `8–20f` subheading settles. Frames `20–66` (`1.53s`) clean hold; `66–72f` `slide_left` exit.
- **Example 2 (`--reduced-motion` variant)**: Replace `0.012h` translation with pure `8`-frame opacity cross-fade (`stagger = 2f`) and `0f` cut exit.

## Resources (load only if needed)
- [Multi-element stagger timing sheet](references/stagger-timing-sheet.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
