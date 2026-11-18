# Headless Blender `bpy` Clay Shader and `FModifierStepped` Recipe

## Key `Principled BSDF` sockets (Blender 4.x+)
- `Base Color`: OKLCH gamut-safe pastel/earth tone
- `Roughness`: `0.68` base + `0.06 * (NoiseTexture(scale=12.0) - 0.5)`
- `Subsurface Weight`: `0.22`, `Subsurface Scale`: `0.0025`, `Subsurface Radius`: `(1.0, 0.45, 0.25)`
- `Specular IOR Level`: `0.38`
- `Normal`: `Bump(strength=0.08, distance=0.002, height=Noise(scale=18.0))` chained into `Bump(strength=0.035, distance=0.0008, height=Wave(scale=55.0, distortion=3.2))`

## Stepped F-Curve quantization
For every `fcurve` in `obj.animation_data.action.fcurves`:
add `mod = fcurve.modifiers.new(type='STEPPED')` with `mod.frame_step = 2` (at `24 fps`) or `3` (at `30 fps`), and set `scene.render.use_motion_blur = False`.
