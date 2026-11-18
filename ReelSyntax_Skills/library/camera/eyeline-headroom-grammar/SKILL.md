---
name: eyeline-headroom-grammar
description: "Position subject eyelines, proportional headroom, directional look space, and 180-degree screen vectors across portrait and widescreen frames."
metadata:
  category: camera
  stage: plan
  status: validated
  version: "2.0.0"
  aliases: "eyeline headroom,headroom and lead room,bakış çizgisi ve baş boşluğu,kadraj bakış boşluğu,Augenhöhe und Kopffreiheit,Blickraum im Bild,línea de mirada y aire,ligne de regard et air"
  requires: ""
---

# Eyeline Headroom Grammar

## Activation
Activate when framing 3D characters, portrait photographs, illustrated avatars, or focal hero objects across cuts or multi-aspect variants (`16:9`, `9:16`, `1:1`, `4:5`). Search aliases: `eyeline headroom`, `bakış çizgisi ve baş boşluğu`, `Augenhöhe und Kopffreiheit`. Do not activate for pure flat full-frame typography with no directional subject.

## Decision rules
- **Eyeline vertical band**:
  - `16:9` / `1:1`: place primary subject eyes on `y ∈ [0.32h, 0.38h]` from top edge.
  - `9:16` / `4:5`: lower eyeline slightly to `y ∈ [0.34h, 0.41h]` so crown headroom clears top `12%` platform UI chrome (`y >= 0.12h`).
- **Proportional headroom by shot size**: wide shot `8%–12%` top clearance above head crown; medium shot `4%–7%`; close-up `1%–3%` (slight hair crop permissible before chin crop). Never leave `> 18%` dead ceiling above a medium/close subject unless framing intentional isolation.
- **Lead / look-room ratio**: when a character or directional object faces left or right (`yaw >= 15°`), allocate `1.6x–2.2x` more horizontal space in front of the gaze than behind the head (`x_subject ≈ 0.36w` looking right, `0.64w` looking left).
- **Eyeline jump continuity across cuts**: keep screen-space `(x, y)` gaze target displacement `<= 0.18` normalized canvas width on same-subject scale cuts, or flip cleanly across symmetric `0.36w <-> 0.64w` anchors on shot-reverse-shot while preserving the `180°` axis.

## Parameters and defaults
- `eyeline_y_widescreen`: `0.35` normalized height from top (`0.32–0.38`).
- `eyeline_y_vertical`: `0.37` normalized height from top (`0.34–0.41`, crown `>= 0.12`).
- `look_room_ratio`: `1.8` (`front_margin / back_margin`).
- `axis_preserved`: `true` (opposing speakers look Left-to-Right vs Right-to-Left, never both off the same screen edge).

## Procedure
1. Measure subject bounding box (`crown_y`, `eye_y`, `chin_y`, `gaze_vector_deg`) in normalized `[0..1]` canvas coordinates for the target aspect ratio.
2. Adjust camera `pitch` / vertical target offset until `eye_y` lands inside the aspect-specific band and `crown_y >= 0.12` on vertical canvases.
3. Offset horizontal framing toward the rear of the head so `front_margin / back_margin` lands in `[1.6, 2.2]`, leaving the opposite side open for callout text or the listening character.
4. Check consecutive dialogue/cutscene shots to confirm speaker A (`x = 0.36`, looking `+X`) and speaker B (`x = 0.64`, looking `-X`) maintain opposing eyeline vectors.
5. Re-verify eyeline and crown coordinates whenever exporting aspect variants (`16:9` -> `9:16` pan-and-scan).

## Failure modes and fixes
- **Center-vertical eye placement (`eye_y = 0.50`)**: wastes upper half as empty ceiling ("sinking character"); tilt camera down or raise subject anchor to `eye_y = 0.35–0.37`.
- **Short-siding (character noses into near frame edge)**: shift horizontal target to restore `1.8x` look space unless deliberately staging claustrophobia.
- **`9:16` crop slices character forehead under status bar**: enforce `crown_y >= 0.12` during vertical variant reframe.

## Checklist
- [ ] `eye_y` sits in `[0.32, 0.38]` (`16:9`) or `[0.34, 0.41]` (`9:16` with `crown_y >= 0.12`).
- [ ] Headroom scales proportionally from wide (`8–12%`) to close-up (`1–3%`).
- [ ] Angled subjects maintain `1.6x–2.2x` look room in the gaze direction.
- [ ] Opposing dialogue cuts preserve the `180°` screen-direction axis.

## Worked examples
- **Example 1 (`9:16` `1080x1920` character medium shot)**: Character looking right (`+28°` yaw) placed at `x = 390 px` (`0.36w`), `eye_y = 700 px` (`0.365h`), `crown_y = 260 px` (`0.135h`, safely below `230 px` top UI zone), leaving `x = 580..980 px` open for speech/caption balance.
- **Example 2 (Two-character cutscene reverse shot, `16:9`)**: Shot 1 Hero at `x = 0.36w, eye_y = 0.34h` looking right; Shot 2 Companion at `x = 0.64w, eye_y = 0.35h` looking left (`|Δeye_y| = 0.01`, clean axis match).

## Resources (load only if needed)
- [Aspect-ratio eyeline and headroom coordinate table](references/aspect-eyeline-coordinates.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
