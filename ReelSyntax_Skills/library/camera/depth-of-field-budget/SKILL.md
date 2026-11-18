---
name: depth-of-field-budget
description: "Calibrate focal distance, f-stop circle-of-confusion blur, and sample counts so background separation stays clean without blurring legible planes or stalling renders."
metadata:
  category: camera
  stage: build
  status: validated
  version: "2.0.0"
  aliases: "depth of field budget,dof blur budget,alan derinliği bütçesi,odak bulanıklığı sınırı,Schärfentiefe-Budget,Unschärfekreis planen,presupuesto de profundidad de campo,budget de profondeur de champ"
  requires: ""
---

# Depth Of Field Budget

## Activation
Activate when configuring 3D camera aperture (`f-stop`), 2.5D multi-plane Z-blur, or background defocus plates where subject separation must be balanced against legibility and render-time noise. Search aliases: `depth of field budget`, `alan derinliği bütçesi`, `Schärfentiefe-Budget`. Do not blur planes carrying primary caption or data text.

## Decision rules
- **Zero-blur rule on typography planes**: any plane carrying readable text, UI numerals, or axis ticks must sit strictly inside the sharp hyperfocal/focus zone (`circle_of_confusion_px <= 0.75 px`).
- **Perceptible separation vs miniature toy look**:
  - Clean product/character separation on `35mm` full-frame sensor equivalent: target background `CoC ∈ [6 px, 18 px]` at `1080p` (`f/2.8–f/4.0` at `1.5m–2.5m` subject distance).
  - Avoid extreme `f/0.95` blur (`CoC > 36 px`) on room-scale scenes, which creates miniature tilt-shift distortion and noisy bokeh fireflies at low sample counts.
- **Render sample coupling**: in ray-traced engines, doubling `CoC` radius requires `~1.5x–2.0x` camera samples or post-compositing defocus to prevent noisy bokeh rings; prefer compositor Z-defocus (`<= 12 px` radius) on `draft` profile and true optical DoF only on `hero`/`production` profiles.

## Parameters and defaults
- `sensor_width_mm`: `36.0` mm full-frame reference.
- `default_fstop_portrait`: `2.8` (`f/2.8` — clean separation without eyelash-only razor focus).
- `default_fstop_tabletop`: `5.6` (`f/5.6` — keeps front-to-back object bevels sharp).
- `max_bg_coc_px_1080p`: `18.0` px (`draft` compositor cap `10.0` px).
- `focus_target_mode`: `"explicit_empty_or_bone"` (bind focus distance to tracked hero bone/null rather than static distance whenever camera dollies).

## Procedure
1. Compute optical circle of confusion in pixels: `CoC_px = |(S2 - S1) / S2| * (f^2 / (N * (S1 - f))) * (width_px / sensor_width_mm)` for focal length `f`, f-number `N`, focus distance `S1`, and background depth `S2`.
2. Verify the entire hero silhouette or product front-to-back depth (`S1 +- Δs`) stays within `CoC_px <= 1.2 px` (increase `N` from `f/2.0` to `f/4.0–f/5.6` if nose/ears go soft).
3. Bind `focus_distance` to the hero empty/anchor when `dolly_in` or `orbit` motion is active so focus never drifts off the subject mid-shot.
4. Cap `draft` profile samples and defocus radius to stay inside frame render budgets, enabling full optical bokeh + denoiser albedo/normal passes on `hero` / `production`.
5. Inspect highlight bokeh discs on high-contrast specular edges for fireflies or Z-buffer haloing.

## Failure modes and fixes
- **Camera dollies in while `focus_distance` stays fixed -> hero goes blurry at frame 60**: parent focus target to hero head/center anchor instead of a constant meter value.
- **Noisy speckled bokeh highlights in Cycles**: clamp glossy indirect (`sample_clamp_indirect = 8.0`), pass normal+albedo to denoiser, or widen f-stop one stop (`f/2.0 -> f/2.8`).
- **2.5D Z-blur bleeds dark edge halos around foreground cutout**: premultiply alpha and dilate depth matte edge before applying background blur, or blur the background layer *before* compositing sharp foreground layers.

## Checklist
- [ ] Hero depth extent (`front` to `back` of focal object) stays within `CoC <= 1.2 px`.
- [ ] All text and data callout layers sit at `CoC <= 0.75 px` (`0 px` preferred).
- [ ] Moving cameras track an explicit focus target anchor rather than a static scalar distance.
- [ ] Bokeh noise and Z-edge halos are clean at target sample budget.

## Worked examples
- **Example 1 (`50mm` character medium shot at `S1 = 1.8m`, background wall at `S2 = 4.5m`, `1920x1080`)**: At `f/2.8`, `CoC_bg = 0.6 * (2500 / (2.8 * 1750)) * (1920 / 36) ≈ 16.3 px` (soft, clean background separation) while `+-6 cm` head depth stays `<= 1.1 px` sharp.
- **Example 2 (2.5D `layer-stack` photo/paper scene)**: Background plate rendered with `gaussian_radius = 6 px` *prior* to compositing sharp midground card (`0 px`) and foreground typography (`0 px`) — zero edge halo and zero extra ray samples.

## Resources (load only if needed)
- [Circle-of-confusion formula and render sample budget table](references/coc-and-sample-table.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
