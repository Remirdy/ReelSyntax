# Frame-driven motion fixture

A six-second original, deterministic 2D motion design test; not an AAA film, photoreal 3D sample or host integration test. `preview.mp4` includes original synthesized audio. The numbered frame counter is intentional. Pillow and FFmpeg/ffprobe are required only for this example and media QA; the offline router uses the Python standard library. Supply a locally available licensed TTF/OTF font; no font is bundled. The included render used locally installed Lato Medium.

From the pack root:

```sh
python examples/hero-fixture/render.py --font /path/to/font.ttf --output examples/hero-fixture/new.mp4
python tools/quality_audit.py examples/hero-fixture/new.mp4 --profile examples/hero-fixture/profile.json
```

`audit.json` is the actual probe/scan report for the bundled preview. `negative-audit.json` records a separate intentionally invalid 320×180, 2-second black silent fixture. Recreate the negative case using FFmpeg `color=black:s=320x180:r=30:d=2` and `anullsrc=r=48000:cl=mono`; audit with the same profile. Technical pass is not final creative approval. The fixture does not exercise all 500 skills or optional render engines.
