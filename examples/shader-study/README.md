# WebGL2 shader study

A two-second bundled SDF sculpture scene rendered in the isolated offline Chromium worker. The shader uses deterministic frame phase, raymarched geometry, direct GGX lighting, soft shadows, ambient occlusion, Reinhard tone mapping and sRGB encoding. It does not use Blender or downloaded JavaScript frameworks. This is a shader capability example, not an alternative quality claim for the Cycles optical film.

```sh
python3 -m reelsyntax validate examples/shader-study
python3 -m reelsyntax render examples/shader-study --profile draft
python3 -m reelsyntax qc examples/shader-study --profile draft
```

Install the optional browser dependency and an authorized Chromium binary separately. WebGL2 availability and the actual driver are checked before rendering and stored in the render environment; unsupported drivers fail clearly. On the verified workstation, Chromium selected SwiftShader software rendering. Cross-driver pixel equality is not guaranteed. No GUI interaction is used.
