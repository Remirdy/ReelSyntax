---
name: scene-duration-floor-ceiling
description: "Enforce shot-type minimum readability floors and maximum static-hold ceilings so cuts never flash unreadably or trigger unintended freeze warnings."
metadata:
  category: editing
  stage: plan
  status: validated
  version: "2.0.0"
  aliases: "scene duration bounds,shot length floor ceiling,sahne süresi alt üst sınırı,çekim süresi limitleri,Szenendauer-Grenzen,Einstellungslänge begrenzen,límites de duración de escena,bornes de durée de scène"
  requires: ""
---

# Scene Duration Floor Ceiling

## Activation
Activate when validating generated or hand-edited `reel.json` timelines to guarantee every scene stays above human visual registration floors and below unmotivated stagnation ceilings. Search aliases: `scene duration bounds`, `sahne süresi alt üst sınırı`, `Szenendauer-Grenzen`.

## Decision rules
- **Hard perceptual floor**: reject any standalone scene shorter than `24` frames (`0.80s` at `30/1` fps) when carrying zero text, or shorter than `max(36, ceil(char_count / max_cps * fps) + transition_overlap)` frames when carrying readable text.
- **Transition overlap accounting**: outgoing + incoming transition frames (`transition.duration_frames`) erode settled read time; add `transition_in + transition_out` frames on top of the net readable hold floor.
- **Static-hold ceiling**: any scene exceeding `150` frames (`5.0s` at `30/1` fps) must include at least one internal visual progression (camera drift, counter step, layer highlight, or character gesture) or split into two sub-beats.
- **FFmpeg `freezedetect` awareness**: any completely motionless graphic held `>= 18` frames (`0.60s`) triggers `freezedetect`; either drive continuous subtle motion or register the intentional hold interval in `quality.exceptions.freeze`.

## Parameters and defaults
- `textless_floor_frames`: `24` frames (`0.80s` at `30/1` fps).
- `text_card_floor_frames`: `42` frames (`1.40s` at `30/1` fps) net of transitions.
- `data_chart_floor_frames`: `75` frames (`2.50s` at `30/1` fps) for axis + bar comprehension.
- `single_state_ceiling_frames`: `150` frames (`5.00s` at `30/1` fps).

## Procedure
1. For each scene `i`, compute `overlap_frames = transition_in_frames(i) + transition_out_frames(i)`.
2. Compute required text frames `ceil(visible_chars / target_cps * fps) + overlap_frames` using language-specific `target_cps` (`15` EN, `14` TR, `13` DE).
3. Clamp `duration_frames >= max(shot_type_floor, required_text_frames)`.
4. Split or animate any scene with `duration_frames > single_state_ceiling_frames` so visual state advances at least once every `3.5s`.
5. Re-normalize scene frame sum to target runtime and audit `freeze` exception ranges.

## Failure modes and fixes
- **12-frame dissolve on both ends of a 42-frame card leaves only 18 frames (`0.6s`) legible**: extend card to `60` frames or reduce transitions to `6`-frame wipes.
- **Data chart cut away at `1.2s` before viewer reads axis**: enforce `data_chart_floor_frames >= 75` frames (`2.5s`) and animate bar growth in the first `24` frames only, holding `51` frames settled.
- **8-second title card stalls opening**: cap title/hook card at `<= 60` frames (`2.0s`) and move details into scene 2.

## Checklist
- [ ] Every scene clears its shot-type floor *after* subtracting transition overlaps.
- [ ] Reading duration satisfies language-specific `target_cps` (`13–15` cps).
- [ ] Zero un-animated scenes exceed `150` frames (`5.0s`) without internal progression.
- [ ] Intentional static holds `>= 0.60s` are accounted for in `quality.exceptions.freeze`.

## Worked examples
- **Example 1 (Transition-eroded card fix, EN)**: `duration_frames = 45`, `32` chars (`15` cps -> needs `64f` net) + `6f` incoming wipe + `6f` outgoing wipe = `76f` minimum. Scene resized from `45f` -> `78f` (`net = 66f`, `14.5` cps pass).
- **Example 2 (Overlong German compound card split, DE)**: Single `210f` (`7.0s`) scene with `88` chars split into `s02a` (`102f`, `42` chars = `12.4` cps) and `s02b` (`108f`, `46` chars = `12.8` cps).

## Resources (load only if needed)
- [Shot-type floor and ceiling reference table](references/shot-bound-table.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
