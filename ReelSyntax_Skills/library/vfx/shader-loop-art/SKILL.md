---
name: shader-loop-art
description: "Author mathematically seamless periodic GLSL and procedural visual loops using 2*pi*f/N phase clocks, circular 4D noise trajectories, and stutter-free terminal frames."
metadata:
  category: vfx
  stage: build
  status: validated
  version: "2.0.0"
  aliases: "shader loop art,seamless glsl loop,kesintisiz gölgelendirici döngüsü,periyodik prosedürel döngü sanatı,nahtlose Shader-Schleife,periodische GLSL-Animation,arte de bucle en shader,boucle procédurale shader sans couture"
  requires: ""
---

# Shader Loop Art

## Activation
Activate when authoring `loop-art`, `music-visualizer` backgrounds, or ambient procedural plates (`shader-sculpture` / `custom-shader` / `procedural` Canvas/Pillow) that must repeat `N -> 0` infinitely with zero position jump, zero velocity kink, and zero double-rendered seam frame. Search aliases: `shader loop art`, `kesintisiz gölgelendirici döngüsü`, `nahtlose Shader-Schleife`.

## Decision rules
- **Half-open periodic phase `theta = 2 * pi * frame / total_frames` (NEVER `frame / (total_frames - 1)`)**:
  - If `frame = 0` maps to `0` and `frame = N - 1` maps to `2 * pi`, then frame `N - 1` and frame `0` are identical duplicates, causing a `1`-frame freeze stutter on every single loop wrap!
  - Mapping `u = frame / total_frames` (`frame ∈ [0, N - 1]`) puts `frame = N - 1` exactly one frame step `(N - 1)/N` before `frame = 0`, so `N - 1 -> 0` advances smoothly at uniform angular velocity `Δtheta = 2 * pi / N`.
- **Integer harmonic frequencies only**: every time-dependent term (`sin(k * theta)`, rotation `m * theta`, palette cycle `p * theta`) **must** use exact integer multipliers `k, m, p ∈ Z` (`1, 2, 3, -1...`); a fractional multiplier like `1.5 * theta` snaps discontinuously at `u = 1 -> 0`!
- **Periodic noise via circular `(cos(theta), sin(theta))` embedding**: never scroll noise linearly (`noise(uv + vec2(u, 0.0))` snaps at `u = 1`); sample `3D`/`4D` continuous noise along a closed circle `(p.x, p.y, R * cos(theta), R * sin(theta))` so both value *and* all temporal derivatives `d/dt` match identically across the wrap!
- **Audio seam matching**: if paired with audio, synthesize periodic harmonic cycles (`integer` cycles over `total_samples`) or apply an equal-power wrap crossfade so `loop-seam-audit` passes both visual (`RMSE <= 2.5%` step) and audio zero-crossing continuity.

## Parameters and defaults
- `phase_formula`: `theta = TAU * float(frame) / float(total_frames)` (`TAU = 6.283185307179586`).
- `noise_circle_radius_R`: `0.65–1.40` (larger `R` = faster organic evolution per loop cycle; scale `R` proportionally to loop duration `D_sec` via `R ≈ 0.18 * D_sec`).
- `harmonic_multipliers`: integers `1, 2, 3` only (`assert int(k) == k`).
- `flash_safety_max_hz`: keep temporal oscillation multiplier `k / D_sec < 2.0 Hz` (`< 3 Hz` WCAG flash limit!).

## Procedure
1. Derive normalized half-open loop progress `u = frame / total_frames` (`0 <= frame < total_frames`) and `theta = 2 * pi * u`.
2. Replace every linear `time` variable in SDF rotations, domain warps, and color phase shifts with `sin(k * theta)`, `cos(k * theta)`, or `k * theta` (`k ∈ Z`) for `2 * pi`-periodic functions (like `cos`, `sin`, rotation matrices).
3. Route organic turbulence through circular noise coordinates `(uv.x, uv.y, R * cos(theta), R * sin(theta))`.
4. Add `1`-LSB deterministic spatial dither before `8`-bit quantization so smooth shader gradients avoid H.264 banding without introducing frame-0 seam noise.
5. Run `qc --loop` (`loop-seam-audit`) verifying `diff(frame[N-1], frame[0]) ≈ diff(frame[N-2], frame[N-1])` (neither `0.0` duplicate freeze nor `> 3x` jump spike!).

## Failure modes and fixes
- **1-frame hiccup pause at loop wrap**: caused by dividing by `(total_frames - 1)` instead of `total_frames`; fix denominator to `total_frames`.
- **Sudden pop in background clouds at `00:00`**: linear `uv.x + t * 0.3` left in secondary pass; convert to `4D` circular path or integer lattice tile period `uv.x + floor_period * u`.
- **High-harmonic `sin(18.0 * theta)` on a `4s` loop strobes at `4.5 Hz` (fails `flash-safety`)**: cap luminance-modulating harmonics so `k / duration_sec <= 2.0 Hz`.

## Checklist
- [ ] Phase uses half-open `2 * pi * frame / total_frames` (`frame = N-1` is not a duplicate of `frame = 0`).
- [ ] Every frequency multiplier `k` on `theta` is an exact integer.
- [ ] Noise fields sample closed circular `(R * cos(theta), R * sin(theta))` coordinates.
- [ ] `qc --loop` confirms step between `frame[N-1]` and `frame[0]` matches median inter-frame motion (`zero` seam pop and `< 3 Hz` flash rate).

## Worked examples
- **Example 1 (`6s` / `180f` SDF torus-knot loop at `30/1` fps)**: `theta = TAU * frame / 180.0`, Y-rotation `1 * theta`, X-tumble `sin(2 * theta) * 0.25`, surface ripple `simplex4D(vec4(pos * 2.0, 1.1 * cos(theta), 1.1 * sin(theta)))`. Inter-frame mean pixel delta at `178->179` is `1.42/255` and at `179->0` is `1.44/255` (`seam_ratio = 1.01`, seamless!).
- **Example 2 (Tiled seamless grid scroll)**: Grid cell period `P = 0.125` UV units -> `uv.y + 2.0 * P * (frame / 180.0)` shifts by exact `2` grid periods across `180` frames and wraps invisibly to `frame 0`.

## Resources (load only if needed)
- [Periodic GLSL phase, circular noise, and seam-ratio verification math](references/periodic-phase-and-noise-math.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
