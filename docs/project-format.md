# Project format v1

`reel.json` declares `schema_version: 1`, a lowercase hyphenated `id`, integer `seed`, `output`, `scenes`, `audio`, optional `camera`, optional `constraints`, and optional `quality`. Unknown fields fail validation.

## Editor JSON Schema and migration

Published schemas carry canonical versioned identifiers:

- `https://remirdy.github.io/ReelSyntax/schemas/reel.v1.schema.json`
- `https://remirdy.github.io/ReelSyntax/schemas/config.v1.schema.json`

`reelsyntax init` writes a local `reel.schema.json` beside `reel.json` and sets `"$schema": "./reel.schema.json"` so Visual Studio Code and JSON Schema-aware editors provide autocomplete and inline validation offline. To map `reel.json` globally in `.vscode/settings.json`:

```json
{
  "json.schemas": [
    {
      "fileMatch": ["**/reel.json"],
      "url": "https://remirdy.github.io/ReelSyntax/schemas/reel.v1.schema.json"
    }
  ]
}
```

Upgrade unversioned or pre-v1 project files with `reelsyntax migrate <project>` (`--dry-run` previews changes without modifying files; applied migrations store a backup under `.reelsyntax/migrations/`).

## Output and canonical timing

`output` contains even `width` and `height` (`64..7680`) and rational `fps` string (`"24/1"`, `"30/1"`, `"30000/1001"` in `[1, 120]`). Timeline intervals are sequential half-open integer frame ranges with zero floating-point drift.

## Scenes, cameras, transitions, and ROI locks

Each scene declares `id`, `duration_frames`, `engine` (`pillow`, `browser`, `ffmpeg`, or `blender` for 3D recipes), `recipe`, and `params`:

- Legacy geometric recipes: `assembly`, `rings`, `signal`, `title`.
- Production recipes:
  - `prism-monolith` — linear-light three-point 3D facet shading, AgX highlight rolloff, contact shadow, and 3D perspective camera (`pillow` software PBR or headless `blender`).
  - `kinetic-type` — Swiss-grid tracked typography with Verlet physical pendulum dynamics.
  - `data-horizon` — staggered multi-bar and spline telemetry chart (`params.series` optional numeric list).
  - `hud-lock` — precision reticle composition with a static lower bar aligned for `locked_regions` verification.
  - `aperture` — native Blender 5.1+ Cycles optical-mechanism study (`engine: "blender"` only, textless; supports `params.shot` in `macro | iris | assembly | hero` and `params.samples` in `8..256`).
  - `shader-sculpture` — bundled WebGL2 SDF studio scene (`engine: "browser"` only), fixed camera, frame-indexed object motion, optional palette colors. Its software or hardware GL driver is capability-probed and recorded. It does not accept custom shaders, typography or camera overrides.
  - `footage` — local decoded source video (`engine: "ffmpeg"` only), with `params.source`, optional native decoded-source `in_frame` and letterbox `background`. Frames after the source in-point are resampled to project FPS and fitted without cropping. Short media fails instead of repeating or padding pictures. Set `hdr_to_sdr: true` for explicit PQ/HLG tone mapping. A positive `speed` multiplier controls picture retiming.
  - `layer-stack` — bottom-to-top local raster layers (`engine: "pillow"` only), opaque `background`, and `params.layers` with `source`, optional `name`, `x`, `y`, `width`, `height`, and `opacity` (`0..1`). Coordinates are project pixels, scaled for Draft; missing size uses raster dimensions. The optional `blend` field accepts normal, multiply, screen and overlay. Media recipes do not apply typography or camera controls.
- Optional `params`: `kicker`, `heading`, `subheading`, `background`, `foreground`, `accent` (`#RRGGBB`), `series`, `font_mode` (`default` or `system`), plus `shot` and `samples` for `aperture`.
- Optional `camera`: `preset` (`locked`, `dolly_in`, `orbit`, `crane_rise`, `dolly_zoom`), `focal_mm` (`12..200` on a `36mm` full-frame horizontal gate), `position` (`[x,y,z]`), `target` (`[x,y,z]`). Non-`locked` presets fail validation when `constraints.camera_locked` is `true`.
- Optional `transition`: `type` (`cut`, `cross_dissolve`, `fade_black`, `fade_white`, `wipe_left`, `slide_left`, `slide_right`, `radial`, `glitch`) and `duration_frames` (`1..duration_frames // 2`).
- Optional `locked_regions`: list of `[x, y, width, height]` pixel rectangles verified losslessly via `reelsyntax lock --scene <id> --roi-profile <profile>`.

## Procedural audio and stems

`audio` declares boolean `enabled`, `gain_db` (`-60..-6`), optional `export_stems` boolean, and `cues`. Each cue declares `frame`, `duration_frames`, `frequency` (`30..8000` Hz), optional `instrument` (`sine`, `sub_impact`, `harmonic_pluck`, `warm_pad`, `whoosh`, `click_transient`), optional stereo `pan` (`-1.0..1.0`), and optional `gain_offset_db` (`-24..6`). Synthesis outputs deterministic 48 kHz 16-bit stereo PCM plus per-instrument stem WAVs when `export_stems` is enabled.

Optional `audio.tracks` contains up to 16 local source clips. Each has a unique `id`, project-relative `source`, declared `kind` (`voice`, `music`, `effects`), timeline `start_frame`, and `duration_frames`. Optional `in_frame` is a source-time offset measured at the **project FPS**, unlike footage's native decoded-frame in-point. Optional `gain_db` (`-60..12`) adds to master gain; `pan` (`-1..1`), `fade_in_frames` and `fade_out_frames` control each track. Endpoints map to rounded 48 kHz sample anchors. Source audio can lead or outlast a picture cut without changing scene durations. Per-source full-timeline stems are exported when enabled; short sources or unsafe peaks fail before replacing a delivered master.

Track `kind` is caller-declared metadata used to enforce `no_voice` and `no_music`; the runtime does not classify speech/music content. Rasterized text inside an imported image is not automatically detected. Assets must be local contained files, with no URLs, absolute paths, traversal or symlinks. Their content hashes participate in selective scene cache keys and are checked again before delivery and QC/export.

Sources cannot live under managed `output`, `review`, `.git` or `.reelsyntax` state/cache paths; `.reelsyntax/inputs` is the designated exception for local example inputs. Copy a prior render into an asset directory before using it as a source. This prevents source overwrite and cache cleanup conflicts.

Source container demuxers are selected explicitly and restricted to the local file protocol. Playlist/indirect media inputs are rejected, including playlists disguised with a supported extension. Supported source extensions are MP4/MOV/M4V/M4A, MKV/WebM, AVI, WAV, MP3, FLAC, AAC, OGG/OGA, AIFF/AIF, TS/MTS/M2TS and MPG/MPEG.

## Optional PSD extraction

`reelsyntax ingest-psd PROJECT --source assets/design.psd --destination assets/design-layers` creates PNG layers and `layers.json` in a new directory, preserving the source. Copy its `params` object into a `layer-stack` scene. Extraction reuses an existing optional AfterEffectsMCP Node runtime with `ag-psd` and `sharp`; no GUI application or automatic installation is involved. Input is bounded to 64 MiB, 16 megapixel 8-bit RGB PSD canvases, 128 layers and 32 megapixels of decoded buffers. Add `--composite` to read simple pixel masks and multiply, screen or overlay raster layers. Vector masks, adjustments, clipping and group opacity require rasterization. Text uses its stored raster pixels rather than editable typography.

See [authoring and delivery](delivery.md) for shape fields, custom browser recipes, locale tables, editable variants and composition snapshots.
