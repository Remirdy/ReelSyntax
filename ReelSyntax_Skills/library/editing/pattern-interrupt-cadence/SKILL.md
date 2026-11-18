---
name: pattern-interrupt-cadence
description: "Schedule motivated visual, spatial, or sonic pattern interrupts every 3.5 to 6.0 seconds to prevent viewer habituation without frantic cutting."
metadata:
  category: editing
  stage: edit
  status: validated
  version: "2.0.0"
  aliases: "pattern interrupt,interrupt cadence,örüntü kırıcı ritim,dikkat tazeleme kesmesi,Musterunterbrechung,Aufmerksamkeitswechsel,interrupción de patrón,rupture de rythme"
  requires: ""
---

# Pattern Interrupt Cadence

## Activation
Activate when editing spoken explainers, kinetic statements, or product walkthroughs longer than `10` seconds where uniform framing and steady cadence risk mid-reel viewer habituation. Search aliases: `pattern interrupt`, `örüntü kırıcı ritim`, `Musterunterbrechung`. Do not activate when `--reduced-motion` or contemplative single-take stillness is locked.

## Decision rules
- **Interrupt interval window**: trigger one motivated sensory shift every `105–180` frames (`3.5s–6.0s` at `30/1` fps) on vertical shorts, or every `150–270` frames (`5.0s–9.0s`) on widescreen explainers.
- **Semantic motivation requirement**: every interrupt must align with a clause turn, contrast word (`"however"`, `"ama"`, `"jedoch"`), or new step — never fire random zooms mid-phrase.
- **Modality rotation**: never use the same interrupt mechanism twice in a row; rotate across `scale_step` (`1.0 -> 1.18x`), `polarity_flip` (dark slate <-> light bone card), `spatial_split` (full-bleed -> `50/50` comparison), and `sonic_drop` (bed mute + crisp transient).
- **Minimum settle floor**: leave at least `45` frames (`1.5s`) of clean settled reading after any interrupt before firing another.

## Parameters and defaults
- `vertical_interval_frames`: `105–180` frames at `30/1` fps (adjustable default).
- `widescreen_interval_frames`: `150–270` frames at `30/1` fps.
- `scale_jump_ratio`: `1.18` minimum (`< 1.12` looks like an accidental framing error; `> 1.45` feels jarring unless comedic).
- `consecutive_same_modality_max`: `1`.

## Procedure
1. Plot existing cut and state-change timestamps across the rational timeline and highlight any static stretch exceeding `vertical_interval_frames`.
2. Locate the nearest syntactic turn or stressed keyword inside each overlong stretch.
3. Assign an interrupt modality different from its immediate predecessor (`scale_step`, `polarity_flip`, `diagram_callout`, or `sonic_drop`).
4. Verify text safe zones and WCAG contrast (`>= 4.5:1`) hold both before and after the interrupt state change.
5. Inspect full-speed playback to confirm interrupts clarify structure rather than creating visual noise.

## Failure modes and fixes
- **Sub-threshold scale jump (`1.05x`)**: looks like a mistake jump cut; either commit to `>= 1.18x` punch-in or switch to a diagram overlay card.
- **Hyperactive sub-1.5s strobe cutting**: merge adjacent micro-cuts and restore `>= 45` frames settle time per thought.
- **Polarity flip flashes too brightly**: cap light-card luminance below `Y = 222` (`#DCE2EC`) rather than pure `#FFFFFF` to respect flash-safety comfort.

## Checklist
- [ ] Zero unmotivated static stretches exceed `180` frames (`6.0s` vertical) without a state shift.
- [ ] Every interrupt lands on a semantic turn or emphasized word.
- [ ] Consecutive interrupts rotate modality (`scale` -> `polarity` -> `callout` -> `sonic`).
- [ ] Scale punch-ins clear the `>= 1.18x` perceptual threshold while keeping text in safe bounds.

## Worked examples
- **Example 1 (`18s` / `540f` vertical explainer, EN)**: `0f` hook (`prism-monolith` dark), `114f` (`3.8s`) `polarity_flip` to bone-slate comparison split on `"Instead"`, `246f` (`8.2s`) `diagram_callout` arrow highlight, `378f` (`12.6s`) `sonic_drop` + `1.22x` punch-in on key metric, `468f` resolved payoff card.
- **Example 2 (`16s` / `480f` technical tip, TR)**: `0f` başlık kartı, `120f` (`4.0s`) `"Ancak"` kelimesinde `50/50` bölünmüş ekran geçişi, `264f` (`8.8s`) vurgu ses efektiyle grafik bar animasyonu, `390f` özet kartı.

## Resources (load only if needed)
- [Pattern interrupt modality taxonomy and spacing guide](references/interrupt-taxonomy.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
