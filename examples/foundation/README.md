# Foundation motion study

Original eight-second, three-scene procedural source: assembling shapes, wire rings and a changing signal. No downloaded models, samples, music or fonts are bundled. The runtime uses Pillow's packaged default font for the CPU renderer and a local generic font for the optional browser path; full shaping/glyph correctness requires visual review.

From the checkout:

```sh
python3 -m reelsyntax validate examples/foundation
python3 -m reelsyntax render examples/foundation --profile draft
python3 -m reelsyntax render examples/foundation --profile production
python3 -m reelsyntax qc examples/foundation --profile production
python3 -m reelsyntax snapshot examples/foundation --profile production --frame 135
```

Install optional render dependencies and FFmpeg/FFprobe separately first. `review/` and `output/` are generated and ignored by Git. Source-frame previews are not evidence of an encoded video. The final development status records which actual media commands ran. No AAA aesthetic claim is made for this fixture.
