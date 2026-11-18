# 2.5D Z-Plane Shadow, Bevel, and Parallax Equations (`1080p` Reference)

For layer `i` at elevation `z_i` above receiver plane `z_recv` (`Δz = max(0.25, z_i - z_recv)`), scale factor `S = min(width, height) / 1080.0`:

- `shadow_dx = 0.64 * 4.0 * Δz * S`
- `shadow_dy = 0.77 * 4.0 * Δz * S`
- `shadow_blur_radius = 3.0 * Δz * S`
- `shadow_alpha = clamp(0.40 - 0.03 * Δz, 0.18, 0.40)` (higher planes cast broader, slightly more diffuse umbra)
- `bevel_dx = -0.64 * 1.6 * S`, `bevel_dy = -0.77 * 1.6 * S` (light-facing cut thickness rim)
- `parallax_offset(t) = cam_drift_px(t) * (z_i / 3.0) * S`
