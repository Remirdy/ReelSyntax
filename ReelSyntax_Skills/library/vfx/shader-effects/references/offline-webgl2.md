# Bundled offline WebGL2 path

Use this reference for the implemented `shader-sculpture` recipe when a deterministic procedural studio object suits the brief. It uses a bundled GLSL ES 3.00 shader in the isolated offline Chromium worker. It does not accept arbitrary shader code, Three.js scenes, text overlays or custom camera rigs.

```json
{
  "id": "sculpture",
  "duration_frames": 48,
  "recipe": "shader-sculpture",
  "engine": "browser",
  "params": {"background": "#181e23", "foreground": "#526268", "accent": "#c3a16e"}
}
```

This is a scene fragment; place it in a validated project with explicit rational FPS. Only the palette is configurable. The studio camera is fixed, and object phase comes from the requested frame and seed. The implementation performs bounded SDF raymarching, direct GGX lighting, shadows and ambient occlusion with Reinhard tone mapping followed by sRGB encoding. It does not apply the Blender recipe's AgX transform.

1. Verify optional Pillow/Playwright and an authorized Chromium binary with `doctor`. Runtime commands never install the browser automatically.
2. Render `examples/shader-study` in Draft, then inspect the real video and `output/draft-manifest.json`.
3. Record the WebGL version, shading-language version, actual renderer and maximum texture size from `environment.webgl`. The verified local Chromium chose SwiftShader software rendering; browser availability is not proof of hardware acceleration.
4. Inspect first/middle/last frames, silhouettes, shadow contact, edge aliasing and temporal changes. Run QC and test seeking to a frame twice in the same driver/runtime before claiming repeatability.

WebGL2 probe, shader compile/link, context-loss and draw failures are explicit errors. Do not substitute a different visual recipe or label a blank frame a fallback. The worker retains its offline network boundary and hard process timeout. Same-runtime deterministic seeks and Canvas/WebGL switching are covered by `tests/test_webgl.py`; cross-driver numerical equality and native GPU performance remain unverified.

If the brief requires custom uniforms, imported models, volumetrics or authored shader graphs, treat that work as an engine extension with its own tests and look development. The bundled recipe is not evidence that those features are already implemented.
