# Aperture — an optical mechanism study

An original six-second, four-shot native Blender film: a material macro, an opening iris, an exploded assembly, and a final studio composition. The mechanism is a fictional design study, not a simulation or specification of a real optical product.

The scene uses procedural graphite, champagne titanium, steel and protective glass; modeled grip flutes and concentric machining; eleven separate iris blades; a seamless studio cyclorama; directed area lights; depth of field; and a single AgX output transform. No downloaded models, HDRIs, textures, stock footage, narration, music samples or model weights are used. A deterministic local stereo cue/stem mix accompanies the movement.

## Reproduce

Use the checkout's authorized media tools and optional Pillow dependency, plus a separately installed Blender with Cycles:

```sh
python3 -m reelsyntax validate examples/aperture-film
python3 -m reelsyntax render examples/aperture-film --profile draft --timeout 3600
python3 -m reelsyntax render examples/aperture-film --profile hero --timeout 3600
python3 -m reelsyntax qc examples/aperture-film --profile hero
```

For this workstation, `source .tools/env.sh` configures project-local FFmpeg/FFprobe paths. It is a local setup file and is not distributed. The new recipe requires native Blender; it fails clearly if that renderer is absent instead of substituting a different design.

`reel.json` is the editable frame/shot/sound plan. The reusable scene implementation is `reelsyntax/blender_aperture.py`; `blender_engine.py` integrates it with the standard renderer and content-addressed scene cache. The shots share one model and lighting setup. Parameters select `macro`, `iris`, `assembly` or `hero`; palette and camera configuration are editable. Typography overlays are deliberately unsupported for this textless recipe.

Delivery is `output/hero.mp4` at 1280×720, 24 fps, 144 frames (24 + 36 + 48 + 36), with stereo AAC audio. Separate mix/stem WAV files, manifest, review frames, filmstrip and QC evidence are generated alongside it. Generated media/state stays local and is excluded from source packages; these paths are deliverables only once rendering succeeds.

The source currently targets Blender 5.1.2's Principled material sockets. Cycles selects an available Metal device on macOS; other environments use the CPU. The actual device, sample count and duration are recorded in each scene cache's engine evidence. Cross-platform device support and numerical image equality are not certified by one workstation's render.

Inspect actual playback, motion, focus, surface continuity and sound before approving the film. Technical QC is separate from creative acceptance; this example carries no AAA certification.
