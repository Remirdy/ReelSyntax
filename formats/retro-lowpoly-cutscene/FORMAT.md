# Retro Low-Poly Cutscene (`retro-lowpoly-cutscene`)

Original, brand-free faceted 3D character dialogue cutscenes (`18–45 s`, default `24 s`) featuring modular low-poly rigs, a 5-shot `180°` staging grammar, quantized lip-sync mouth envelopes, staggered natural blink cycles, stylized retro chirp voices, and a beveled HUD dialogue box anchored safely above the bottom `18%` screen margin.

## Structural contract

1. **Establishing wide (`~13%` duration)** — Two-shot introducing the spatial layout and retro relay beacon (`Scout` at `x = 0.30w` looking right, `Archivist` at `x = 0.70w` looking left).
2. **Speaker A medium (`~21%` duration)** — Over-the-shoulder/medium framing on `Scout` (`x = 0.36w`) with `focused` expression and speech-synced `mouth_envelope`.
3. **Speaker B reverse (`~21%` duration)** — Reverse medium on `Archivist` (`x = 0.64w`) preserving the `180°` screen axis with `surprised` expression and distinct vocal pitch.
4. **Insert clue (`~16%` duration)** — Close-up on the faceted telemetry crystal shifting from amber to cyan.
5. **Two-shot resolve (`~29%` duration)** — Closing two-shot payoff (`happy` expressions) with clean settle hold.

## HUD safe zone and lip-sync guarantees

- **Beveled dialogue box (`y <= 0.812h`)**: Sits strictly above the bottom `18%` mobile/player UI chrome (`>= 0.188h` bottom clearance on `9:16`, `4:5`, `1:1`, and `16:9`).
- **Mouth envelope synchronization**: Quantized `{0.0, 0.35, 0.75, 1.0}` RMS jaw curves match scene `duration_frames` (`0`-frame delta, satisfying `mouth_sync <= 2` frames).
- **Staggered blinks**: `Scout` and `Archivist` use prime-offset blink seeds (`+47` frame separation) so characters never blink in lockstep.

## Wired skills

- `retro-cutscene-directing` — 5-shot `180°` cutscene pacing and original brand-free staging.
- `low-poly-style` — Faceted flat-shaded geometry, OKLCH palettes, and crisp silhouettes.
- `lip-sync` — Frame-accurate quantized jaw envelope aligned with stylized speech energy.
- `voice-fx-flat-synth` — Intelligibility-safe retro dialogue chirp synthesis and vocal contrast.
- `eyeline-headroom-grammar` — Aspect-aware eyeline placement (`0.34h–0.41h`) and `1.8x` look space.
- `content-policy-boundaries` — Strictly original geometric characters and zero trademarked IP.
- `frame-clock` — Rational FPS and exact integer frame conservation across all five shots.
- `contrast-audit` — High-contrast beveled dialogue box and readable character palette tokens.
- `vertical-safe-zones` — Text bounds kept clear of top/bottom platform UI overlays.
- `reading-speed-audit` — Dialogue pacing kept inside language-specific CPS ceilings.
