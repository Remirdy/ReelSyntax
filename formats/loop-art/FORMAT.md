# Seamless Loop Art (`loop-art`)

Mathematically seamless periodic visual loops driven by a half-open phase clock `theta = 2 * pi * frame / total_frames` with integer harmonics and flash-safe gentle cadence.

## Periodic seam contract

- **Half-open clock (`frame / total_frames`):** Frame `N - 1` lands one exact step before `frame = 0`, eliminating single-frame duplicate freeze stutters while passing `qc --loop` (`loop_picture <= 8`).
- **Integer harmonic cycles (`k in {1, 2}`):** All orbital trajectories and wave modulations complete exact integer periods across `duration_frames`, keeping temporal oscillation frequency well below the WCAG `3 Hz` flash limit.
- **Steady caption layer:** Optional titles render without entrance jumps or linear progress bars so endpoints wrap seamlessly.

## Wired skills

- `loop-seam-audit` — Verifies visual and audio wrap continuity (`--loop`).
- `shader-loop-art` — Half-open `2 * pi * frame / N` periodic phase clock.
- `loop-design` — Continuous multi-harmonic closed trajectories.
- `flash-safety` — Sub-2Hz smooth tonal motion free of strobing reversals.
- `frame-clock` — Exact integer period duration matching rational FPS.
