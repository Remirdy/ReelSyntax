# Logarithmic Zoom and Sub-Pixel Extent Math

Linear scale interpolation `s(t) = s0 + (s1 - s0)*t` appears faster at wide zoom (`1.0`) than tight zoom (`1.2`). Constant optical magnification velocity requires logarithmic interpolation:

```text
s(t) = s0 * pow(s1 / s0, t),   t = frame / max(1, duration_frames - 1)
crop_w = source_fit_w / s(t)
crop_h = source_fit_h / s(t)
cx(t) = cx0 + (cx1 - cx0) * t
cy(t) = cy0 + (cy1 - cy0) * t
extent = (cx - crop_w/2, cy - crop_h/2, cx + crop_w/2, cy + crop_h/2)
```

Pass floating-point `extent` directly to sub-pixel affine/bicubic transform (`PIL.Image.Transform.EXTENT` with `Resampling.BICUBIC`) after pre-scaling large `> 2x` camera originals down to `1.4x` target dimensions with `Resampling.LANCZOS`.
