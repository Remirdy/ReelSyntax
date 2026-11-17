# Authoring and delivery

## Projects and templates

```sh
reelsyntax init promo --template promo
reelsyntax schema --output reel.schema.json
reelsyntax from-readme README.md --output introduction
reelsyntax from-outline outline.md --output talk
reelsyntax from-mermaid diagram.mmd --output diagram
reelsyntax watch promo
```

New projects include a local JSON Schema for editor completion. Run `validate` for duration, resource and cross-field checks. The Markdown importers paginate headings and paragraphs into local raster cards. Diagram input supports directed Mermaid flowcharts with named nodes, quoted labels and straight arrows, up to twelve nodes. Unsupported syntax reports the offending expression. Watch renders Draft after plan or asset changes and writes `review/preview.html`. Use `--once` for a single pass.

## Delivery variants

```sh
reelsyntax render promo --set form.heading=OPEN --aspect 16:9,9:16,1:1
reelsyntax render promo --target shorts --locale de --brand brand.json
reelsyntax render promo --queue jobs.json
```

A delivery variant is a separate project under `.reelsyntax/variants/`. The result identifies its directory. Use that directory for QC and exports. Scene locks, ROI approvals and referenced assets are carried into the variant. Ratios retain the longest side, rounded down to an exact even-pixel ratio. Check your translated copy in each format.

| Input | Example | Contract |
| --- | --- | --- |
| `strings.de.json` | `{"form.heading":"FORM","time.heading":"ZEIT"}` | Scene ID and field map. Values replace existing text fields. The primary language is written to the MP4 streams. |
| `brand.json` | `{"accent":"#396365","font":"assets/brand.ttf","logo":"assets/mark.png","margin":0.08}` | Optional colors, local Pillow font, local image and inset fraction. |
| `jobs.json` | `[{"target":"youtube"},{"aspect":"1:1","values":{"form.heading":"TEST"}}]` | Up to 64 sequential deliveries. Identical resolved jobs share a project. |

Targets are project presets for H.264 delivery. YouTube uses 16:9 at 8 Mbit/s, Shorts 9:16 at 8 Mbit/s, Reels and TikTok 9:16 at 6 Mbit/s, X 16:9 at 5 Mbit/s, and LinkedIn 1:1 at 6 Mbit/s. Audio targets are −14 LUFS for YouTube, Shorts, Reels and TikTok, and −16 LUFS for X and LinkedIn. Insets reserve 5–14% on each edge. Platform overlays can vary by device.

## Audio, captions and review

```sh
reelsyntax audio analyze narration.wav --fps 24/1 --emit-cues
reelsyntax captions burn promo --profile draft
reelsyntax captions burn promo --style word-pop --words words.json
reelsyntax qc promo --html --loop
reelsyntax export promo --format gif --profile draft
reelsyntax export promo --format webm --profile draft
reelsyntax export promo --format poster --profile draft --frame 12
```

Onset detection measures short-window RMS in local mono or stereo 16-bit PCM WAV files. Returned cue rows can be reviewed and copied into the project. Plain caption burn-in uses the scene headings and subheadings. Word-pop takes explicit frame intervals such as `[{"start":0,"end":12,"text":"First"}]`. The end is exclusive. Burn-in requires FFmpeg with libass. WebM uses VP9 and Opus. GIF is silent. The still export produces a PNG from a decoded master frame.

## Extending scenes

An installed Python package can register a callable in the `reelsyntax.recipes` entry-point group. The callable receives a JSON object and a new project directory and returns a version 1 project dictionary. It may write its own assets there. Only select a trusted installation. Invoke it with `reelsyntax from-plugin NAME --params params.json --output film --allow-plugin`.

For a local fragment shader, set the recipe to `custom-shader`, engine to `browser`, and `params.fragment_file` to a project-relative GLSL ES 3 fragment file. The shader receives the same `resolution`, `phase`, `background`, `primary` and `accent` uniforms as the built-in sculpture.

For Three.js, supply a self-contained browser bundle as `params.module_file` on a `three-scene` scene. It must define `window.renderReelFrame(canvas, args)`, where args contains frame, frames, width, height and seed. Bundle the Three.js dependency locally. Rendering executes the bundle only with `--allow-browser-module`. Use the provided canvas and its existing WebGL2 context.

`reelsyntax compose child-a child-b --profile draft --output parent` nests rendered child masters as independent footage and sound tracks at a shared frame rate. The result snapshots the supplied child versions. Recompose into a new directory after changing a child.

## Shapes, source media and transitions

`shape-field` uses Pillow. Supply one to 128 entries in `params.shapes`. Circle, regular polygon, star, arc, pie and mask use `cx`, `cy` and `r`. Rectangle, rounded rectangle, ellipse, grid and dot lattice use `x`, `y`, `w` and `h`. Path, connector, ribbon and arrow use normalized point lists. Cubic Bézier uses exactly four points. A circular mask clips earlier shapes. See the [editor schema](reel.schema.json) for accepted identifiers, geometry and limits.

```json
{"id":"dial","engine":"pillow","recipe":"shape-field","duration_frames":24,"params":{"background":"#eee9df","shapes":[{"type":"arc","cx":0.5,"cy":0.5,"r":0.22,"start_deg":-90,"sweep_deg":270,"stroke":"#355f65","stroke_width":4}]}}
```

Incoming scene transitions support `slide_left`, `slide_right`, `fade_white`, `radial` and `glitch` alongside the original modes. Duration is in frames. Footage accepts `speed` from 0.05 to 16 and `hdr_to_sdr: true` for PQ or HLG conversion. Picture speed and source audio tracks are independent. PSD extraction with `ingest-psd --composite` handles supported pixel masks and multiply, screen and overlay raster layers.

## CI and packaging

The repository provides a composite render action. Use `Remirdy/ReelSyntax@v0.1.0` after checking out a project on a runner with Python, FFmpeg and FFprobe. Set the `project` input to its directory. It writes the report to the Actions summary. Optional same-repository PR comments require `comment: 'true'` and pull-request write permission.

The MCP desktop bundle includes the Python gateway and the indexed skill library. Import the `.mcpb` release asset in a compatible client, select the project workspace and provide Python 3.11 or later on PATH. Optional Blender and After Effects integrations require their own local runtimes.
