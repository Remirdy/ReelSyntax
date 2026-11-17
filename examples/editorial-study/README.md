# Editorial source study

A three-second local editing example built from ReelSyntax's own rendered Aperture master. It demonstrates decoded-source frame trims, two raster layers, a baked dissolve, and source audio that outlasts the first picture cut (L cut) and leads the last cut (J cut). The middle plate is intentionally held; its freeze interval and the planned audio gap are declared in the QC plan.

After rendering `examples/aperture-film`, run from the repository root with the optional Pillow dependency and separately configured FFmpeg/FFprobe:

```sh
python3 examples/editorial-study/prepare.py
python3 -m reelsyntax validate examples/editorial-study
python3 -m reelsyntax render examples/editorial-study --profile production --cache-budget-mib 512
python3 -m reelsyntax qc examples/editorial-study --profile production
python3 -m reelsyntax export examples/editorial-study --profile production --format blender --frame 48
```

`prepare.py --source /absolute/path/to/another.mp4` can use another local master with at least 127 video frames and sufficient audio. This example treats the source as effects audio; change the declared track kind if using music or voice and update constraints accordingly. Inputs remain local in `.reelsyntax/inputs` and are never modified by the renderer. Run preparation once per example directory; existing input media is preserved. Generated inputs and outputs are excluded from Git and source distributions.
