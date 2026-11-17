---
name: procedural-camera-shake
description: "Use for procedural camera shake. Apply trauma-squared band-limited rotational noise separating handheld breath from impact impulse while respecting camera locks."
metadata:
  category: camera
  stage: build
  status: validated
  version: "2.0.0"
  aliases: "kamera sarsıntısı,camera trauma,handheld shake,darbe sarsıntısı"
  requires: ""
---

# Procedural Camera Shake

## Activation
Use when a shot explicitly calls for handheld presence or impact impulse punctuation. Search aliases: kamera sarsıntısı,camera trauma,handheld shake,darbe sarsıntısı. Never activate if `camera_locked` is true or for calm corporate/editorial typography where shake degrades readability.

## Inputs and output
- Inputs: Seed, canonical frame index, rational FPS, trauma envelope $T(t) \in [0, 1]$, and rig mode (`breath` or `impact`).
- Output: Deterministic rotational offsets $(\Delta\text{pitch}, \Delta\text{yaw}, \Delta\text{roll})$ and bounded micro-translation.
- Required capability: Core `reelsyntax.camera` or engine camera rig.
- Evidence bundle: Peak angular excursion, decay curve, and safe-area text clearance check.

## Production recipe
1. Verify `constraints.camera_locked` is false; hard-fail if shake is requested on a locked camera brief.
2. Drive shake amplitude by $S(t) = T(t)^2$ (quadratic trauma response) with exponential decay $T(t) = T_0 e^{-\lambda (t - t_0)}$ after impact anchors.
3. Favor rotational pitch/yaw/roll over X/Y translation: real lens shake pivots the optical axis, creating natural perspective shift rather than 2D post-crop sliding.
4. Separate frequency bands using seeded value/gradient noise octaves:
   - Handheld operator breath: $0.35\text{–}1.1\text{ Hz}$, max $\pm 0.35^\circ$ pitch/yaw, $\pm 0.15^\circ$ roll.
   - Impact shock: $9\text{–}16\text{ Hz}$ damped over $0.25\text{–}0.45\text{ s}$, max $\pm 1.2^\circ$.
5. Pin HUD/title overlays to screen space or verify title safe-area inset absorbs peak excursion without clipping.

## Acceptance criteria
- Zero random-number drift across rerenders (seeded purely from project `seed` and `t`).
- Trauma decays below $0.01^\circ$ within declared settle window; no edge border exposure.
- Record frame range, peak angle, decay constant, and visual review status.

## Failure and repair
If shake feels jittery or nauseating, cut roll amplitude by $60\%$, lower noise frequency, or convert 2D canvas slide into subtle 3D pitch/yaw rotation.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric.

Original production guidance and validated runtime math.
