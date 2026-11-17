# Cinematic and editorial production study

An eight-second (192 frames at `24/1` fps, `1280x720`) four-scene showcase exercising:

- **`prism-monolith`**: scene-referred linear three-point shading, AgX highlight rolloff, grounded contact shadow, and inertial `dolly_in` 3D camera projection.
- **`kinetic-type`**: Swiss-grid typography with Turkish (`ÇĞİÖŞÜ`) glyph coverage verification, optical tracking, and a deterministic Verlet pendulum ribbon.
- **`data-horizon`**: staggered multi-bar and spline data visualization.
- **`hud-lock`**: protected lower-region (`locked_regions`) compliance bar verified losslessly across revisions.
- **Cross-dissolve editorial transitions**, **multi-stem stereo procedural audio** (`sub_impact`, `whoosh`, `harmonic_pluck`, `warm_pad`), **Hero lookdev A/B + motion extrema contact sheets**, **OTIO / FCPXML / WebVTT exports**, and **first-party BlenderMCP / AfterEffectsMCP handoff packaging**.

```sh
python3 -m reelsyntax validate examples/cinematic-study
python3 -m reelsyntax render examples/cinematic-study --profile draft
python3 -m reelsyntax render examples/cinematic-study --profile hero
python3 -m reelsyntax lock examples/cinematic-study --scene lockup --roi-profile hero
python3 -m reelsyntax qc examples/cinematic-study --profile hero
python3 -m reelsyntax diff examples/cinematic-study --base draft --target hero
python3 -m reelsyntax export examples/cinematic-study --format otio --profile hero
python3 -m reelsyntax export examples/cinematic-study --format fcpxml --profile hero
python3 -m reelsyntax export examples/cinematic-study --format vtt --profile hero
python3 -m reelsyntax handoff examples/cinematic-study
```
