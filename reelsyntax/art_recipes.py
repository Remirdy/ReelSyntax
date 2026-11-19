from fractions import Fraction
from functools import lru_cache
import math
from typing import Any

from .camera import Camera3D
from .drawing import apply_typography_and_hud
from .lighting import build_monolith_assembly, shade_facet_three_point
from .palette import agx_tonemap_linear, hex_to_linear, hex_to_rgb, linear_to_rgb8, mix_oklab, rgb_to_hex

ART_RECIPES = frozenset({'cinematic-3d', 'stepped-clay', 'paper-cutout'})


def _sub3(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross3(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot3(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _norm3(v: tuple[float, float, float]) -> tuple[float, float, float]:
    m = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]) or 1.0
    return (v[0] / m, v[1] / m, v[2] / m)


def _clamp_u8(value: float) -> int:
    return max(0, min(255, int(round(value))))


def _soft_shadow_ellipse(canvas: Any, cx: float, cy: float, rx_base: float, ry_base: float, bg_hex: str, unit: float) -> None:
    for ring in range(6, 0, -1):
        rx = rx_base + ring * 11.0 * unit
        ry = ry_base + ring * 3.5 * unit
        sh_col = rgb_to_hex(mix_oklab(bg_hex, '#101318', 0.055 * (7 - ring)))
        canvas.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=sh_col)


@lru_cache(maxsize=8)
def _vignette_mask(w: int, h: int, k: float) -> Any:
    from PIL import Image

    gw, gh = 48, 48
    mask_bytes = bytearray(gw * gh)
    for y in range(gh):
        dy = (y + 0.5) / gh - 0.5
        for x in range(gw):
            dx = (x + 0.5) / gw - 0.5
            r = math.hypot(dx, dy) / 0.70710678
            falloff = max(0.86, math.cos(k * r) ** 4)
            mask_bytes[y * gw + x] = _clamp_u8(falloff * 255.0)
    vig_small = Image.frombytes('L', (gw, gh), bytes(mask_bytes))
    return vig_small.resize((w, h), Image.Resampling.BILINEAR).convert('RGB')


def _apply_cos4_vignette_and_halation(image: Any, unit: float, look_mode: str, k: float = 0.24) -> Any:
    from PIL import Image, ImageChops, ImageFilter

    w, h = image.size
    vig = _vignette_mask(w, h, k)
    result = ImageChops.multiply(image, vig)

    if look_mode == 'agx':
        bw = max(64, w // 4)
        bh = max(64, h // 4)
        small = result.resize((bw, bh), Image.Resampling.BILINEAR)
        bright = small.point(lambda c: max(0, (c - 208) * 3))
        blur_r = max(2, int(round(min(w, h) * 0.004)))
        glow = bright.filter(ImageFilter.GaussianBlur(radius=blur_r))
        warm_tint = Image.new('RGB', (bw, bh), (255, 118, 38))
        tinted = ImageChops.multiply(glow, warm_tint)
        upscaled = tinted.resize((w, h), Image.Resampling.BILINEAR)
        result = ImageChops.add(result, upscaled, scale=4, offset=0)
    return result


def _draw_cinematic_3d(
    scene: dict[str, Any],
    frame: int,
    w: int,
    h: int,
    fps_val: float,
    seed: int,
    background: str,
    foreground: str,
    accent: str,
    look_mode: str,
    dither: float,
    reduced_motion: bool,
) -> Any:
    from PIL import Image, ImageDraw, ImageFilter

    unit = min(w / 960.0, h / 540.0)
    dur = max(1, int(scene['duration_frames']))
    active_frame = 0 if reduced_motion else frame
    u = active_frame / max(1, dur - 1)

    bg_plate = Image.new('RGB', (w, h), background)
    bg_draw = ImageDraw.Draw(bg_plate)
    bokeh_specs = (
        (0.62, 0.24, 54.0, accent, 0.16),
        (0.84, 0.34, 42.0, foreground, 0.12),
        (0.76, 0.68, 60.0, accent, 0.11),
        (0.56, 0.56, 36.0, foreground, 0.10),
    )
    for idx, (bx, by, br, col_hex, mix_t) in enumerate(bokeh_specs):
        drift = 0.0 if reduced_motion else 0.015 * math.sin(u * math.tau + idx * 1.3 + (seed % 19) * 0.1)
        cx = (bx + drift) * w
        cy = (by - drift * 0.6) * h
        rad = br * unit
        fill_col = rgb_to_hex(mix_oklab(background, col_hex, mix_t))
        bg_draw.ellipse((cx - rad, cy - rad, cx + rad, cy + rad), fill=fill_col)
    bg_plate = bg_plate.filter(ImageFilter.GaussianBlur(radius=max(2, int(round(10 * unit)))))

    draw = ImageDraw.Draw(bg_plate)
    grid_col = rgb_to_hex(mix_oklab(background, foreground, 0.10))
    draw.line((w * 0.07, h * 0.14, w * 0.93, h * 0.14), fill=grid_col, width=max(1, round(unit)))
    draw.line((w * 0.53, h * 0.70, w * 0.92, h * 0.70), fill=grid_col, width=max(1, round(unit)))

    _soft_shadow_ellipse(draw, w * 0.72, h * 0.66, 108.0 * unit, 22.0 * unit, background, unit)

    cam = Camera3D.from_scene(scene, active_frame, fps_val, seed, camera_locked=reduced_motion)
    facets = build_monolith_assembly(u, seed)
    projected: list[tuple[float, list[tuple[float, float]], tuple[int, int, int], tuple[int, int, int]]] = []
    for verts, mat_role in facets:
        pts: list[tuple[float, float]] = []
        depths: list[float] = []
        ok = True
        for v in verts:
            pr = cam.project(v, w, h)
            if pr is None:
                ok = False
                break
            pts.append((pr[0], pr[1]))
            depths.append(pr[2])
        if not ok:
            continue
        if mat_role == 'accent':
            albedo = accent
        elif mat_role == 'plinth':
            albedo = rgb_to_hex(mix_oklab(background, foreground, 0.24))
        else:
            albedo = foreground
        rgb = shade_facet_three_point(verts, cam.position, albedo, accent, look_mode=look_mode, dither=dither)
        edge_rgb = mix_oklab(rgb_to_hex(rgb), foreground, 0.18)
        projected.append((sum(depths) / len(depths), pts, rgb, edge_rgb))

    projected.sort(key=lambda item: -item[0])
    outline_w = max(1, round(0.9 * unit))
    for _, pts, fill_rgb, edge_rgb in projected:
        draw.polygon(pts, fill=fill_rgb, outline=edge_rgb, width=outline_w)

    return _apply_cos4_vignette_and_halation(bg_plate, unit, look_mode, k=0.25)


def _clay_prism_faces(
    cx: float,
    cy: float,
    cz: float,
    rx: float,
    ry: float,
    height: float,
    sides: int,
    yaw: float,
    tilt: float,
    mat: str,
) -> list[tuple[list[tuple[float, float, float]], str]]:
    top_ring: list[tuple[float, float, float]] = []
    bot_ring: list[tuple[float, float, float]] = []
    cy_cos, cy_sin = math.cos(yaw), math.sin(yaw)
    ct, st = math.cos(tilt), math.sin(tilt)
    hz = height * 0.5
    for idx in range(sides):
        ang = idx * math.tau / sides
        lx = rx * math.cos(ang)
        ly = ry * math.sin(ang)
        for z_off, dest in ((-hz, bot_ring), (hz, top_ring)):
            y1 = ly * ct - z_off * st
            z1 = ly * st + z_off * ct
            x2 = lx * cy_cos - y1 * cy_sin
            y2 = lx * cy_sin + y1 * cy_cos
            dest.append((cx + x2, cy + y2, cz + z1))
    faces: list[tuple[list[tuple[float, float, float]], str]] = []
    for idx in range(sides):
        nxt = (idx + 1) % sides
        faces.append(([bot_ring[idx], bot_ring[nxt], top_ring[nxt], top_ring[idx]], mat))
    faces.append((list(top_ring), mat))
    faces.append((list(reversed(bot_ring)), mat))
    return faces


def _build_clay_sculpture(
    u_step: float,
    seed: int,
    step_index: int,
    amp: float,
) -> list[tuple[list[tuple[float, float, float]], str]]:
    faces: list[tuple[list[tuple[float, float, float]], str]] = []
    faces.extend(_clay_prism_faces(0.0, 0.0, -0.62, 0.92, 0.92, 0.14, 12, yaw=0.2, tilt=0.0, mat='plinth'))
    wobble = amp * math.sin(u_step * math.tau + (seed % 13) * 0.2)
    squash = 1.0 + 0.08 * amp * math.cos(u_step * math.tau * 2.0)
    faces.extend(_clay_prism_faces(0.0, 0.0, -0.24, 0.56 / squash, 0.52 / squash, 0.48 * squash, 10, yaw=0.3 + wobble * 0.5, tilt=0.05 * wobble, mat='primary'))
    faces.extend(_clay_prism_faces(0.04 * wobble, 0.0, 0.22, 0.42 * squash, 0.42 * squash, 0.34, 10, yaw=-0.4 - wobble * 0.7, tilt=-0.08 * wobble, mat='accent'))
    faces.extend(_clay_prism_faces(-0.03 * wobble, 0.02, 0.58, 0.26, 0.26, 0.26, 8, yaw=0.6 + wobble * 0.9, tilt=0.06 * wobble, mat='primary'))
    orb_ang = u_step * math.tau * 0.75 + (step_index % 3) * 0.02
    ox = 0.74 * math.cos(orb_ang)
    oy = 0.74 * math.sin(orb_ang)
    oz = 0.16 + 0.14 * amp * math.sin(u_step * math.tau)
    faces.extend(_clay_prism_faces(ox, oy, oz, 0.17, 0.17, 0.19, 8, yaw=orb_ang, tilt=0.14, mat='accent'))
    return faces


def _shade_clay_facet(
    verts: list[tuple[float, float, float]],
    view_pos: tuple[float, float, float],
    albedo_hex: str,
    accent_hex: str,
    facet_seed: int,
    look_mode: str,
    dither: float,
) -> tuple[int, int, int]:
    e1 = _sub3(verts[1], verts[0])
    e2 = _sub3(verts[2], verts[0])
    normal = _norm3(_cross3(e1, e2))
    centroid = tuple(sum(v[i] for v in verts) / len(verts) for i in range(3))
    view_dir = _norm3(_sub3(view_pos, centroid))
    if _dot3(normal, view_dir) < 0:
        normal = (-normal[0], -normal[1], -normal[2])

    albedo = hex_to_linear(albedo_hex)
    warm_sss = (0.98, 0.48, 0.26)
    rim_tint = hex_to_linear(accent_hex)

    key_dir = _norm3((0.55, -0.50, 0.78))
    fill_dir = _norm3((-0.72, -0.35, 0.42))
    rim_dir = _norm3((-0.20, 0.85, 0.46))

    ndotl_key = max(0.0, _dot3(normal, key_dir))
    ndotl_fill = max(0.0, _dot3(normal, fill_dir))
    ndotl_rim = max(0.0, _dot3(normal, rim_dir))
    wrap_key = max(0.0, (_dot3(normal, key_dir) + 0.35) / 1.35)

    fresnel = (1.0 - max(0.0, _dot3(normal, view_dir))) ** 2.6
    dent_var = 1.0 + (((facet_seed * 37) % 11) - 5) * 0.008
    hemi = 0.20 + 0.08 * (normal[2] * 0.5 + 0.5)

    lin: list[float] = []
    for ch in range(3):
        diffuse = albedo[ch] * dent_var * (hemi + 1.25 * ndotl_key + 0.45 * ndotl_fill)
        sss = (0.22 * wrap_key) * (0.6 * albedo[ch] + 0.4 * warm_sss[ch])
        rim = (0.34 * ndotl_rim * (0.30 + 0.70 * fresnel)) * (0.55 * rim_tint[ch] + 0.45 * warm_sss[ch])
        lin.append(diffuse + sss + rim)

    if look_mode == 'neutral':
        clamped = (
            max(0.0, min(1.0, lin[0] / (1.0 + lin[0]))),
            max(0.0, min(1.0, lin[1] / (1.0 + lin[1]))),
            max(0.0, min(1.0, lin[2] / (1.0 + lin[2]))),
        )
        return linear_to_rgb8(clamped, dither=0.0)
    mapped = agx_tonemap_linear((lin[0], lin[1], lin[2]), exposure=1.02, punch=1.06)
    return linear_to_rgb8(mapped, dither=dither)


def _draw_stepped_clay(
    scene: dict[str, Any],
    frame: int,
    w: int,
    h: int,
    fps_val: float,
    seed: int,
    background: str,
    foreground: str,
    accent: str,
    look_mode: str,
    dither: float,
    reduced_motion: bool,
) -> Any:
    from PIL import Image, ImageDraw

    unit = min(w / 960.0, h / 540.0)
    dur = max(1, int(scene['duration_frames']))
    pose_step = 2 if fps_val <= 25.0 else 3
    step_index = frame // pose_step
    quantized_frame = min(dur - 1, step_index * pose_step)
    u_step = quantized_frame / max(1, dur - 1)

    image = Image.new('RGB', (w, h), background)
    draw = ImageDraw.Draw(image)
    sweep_col = rgb_to_hex(mix_oklab(background, foreground, 0.11))
    draw.line((w * 0.07, h * 0.14, w * 0.93, h * 0.14), fill=sweep_col, width=max(1, round(unit)))
    draw.arc((w * 0.50, h * 0.54, w * 0.96, h * 0.80), start=180, end=360, fill=sweep_col, width=max(1, round(1.5 * unit)))

    _soft_shadow_ellipse(draw, w * 0.72, h * 0.66, 98.0 * unit, 21.0 * unit, background, unit)

    cam_frame = 0 if reduced_motion else quantized_frame
    cam = Camera3D.from_scene(scene, cam_frame, fps_val, seed, camera_locked=reduced_motion)
    amp = 0.25 if reduced_motion else 1.0
    facets = _build_clay_sculpture(u_step, seed, step_index, amp)
    projected: list[tuple[float, list[tuple[float, float]], tuple[int, int, int], tuple[int, int, int]]] = []
    for idx, (verts, mat_role) in enumerate(facets):
        pts: list[tuple[float, float]] = []
        depths: list[float] = []
        ok = True
        for v in verts:
            pr = cam.project(v, w, h)
            if pr is None:
                ok = False
                break
            pts.append((pr[0], pr[1]))
            depths.append(pr[2])
        if not ok:
            continue
        if mat_role == 'accent':
            albedo = accent
        elif mat_role == 'plinth':
            albedo = rgb_to_hex(mix_oklab(background, foreground, 0.26))
        else:
            albedo = rgb_to_hex(mix_oklab(foreground, '#f4d9c0', 0.12))
        rgb = _shade_clay_facet(verts, cam.position, albedo, accent, step_index * 19 + idx, look_mode, dither)
        edge_rgb = mix_oklab(rgb_to_hex(rgb), background, 0.20)
        projected.append((sum(depths) / len(depths), pts, rgb, edge_rgb))

    projected.sort(key=lambda item: -item[0])
    outline_w = max(1, round(1.1 * unit))
    for _, pts, fill_rgb, edge_rgb in projected:
        draw.polygon(pts, fill=fill_rgb, outline=edge_rgb, width=outline_w)

    return image


@lru_cache(maxsize=24)
def _grained_paper_fill(w: int, h: int, fill_rgb: tuple[int, int, int], layer_seed: int) -> Any:
    from PIL import Image

    tw, th = 64, 64
    buf = bytearray(tw * th * 3)
    for y in range(th):
        for x in range(tw):
            hval = ((x * 73856093) ^ (y * 19349663) ^ (layer_seed * 83492791)) & 0xFF
            delta = (hval % 7) - 3
            idx = (y * tw + x) * 3
            buf[idx] = _clamp_u8(fill_rgb[0] + delta)
            buf[idx + 1] = _clamp_u8(fill_rgb[1] + delta)
            buf[idx + 2] = _clamp_u8(fill_rgb[2] + delta)
    tile = Image.frombytes('RGB', (tw, th), bytes(buf))
    canvas = Image.new('RGB', (w, h), fill_rgb)
    for yy in range(0, h, th):
        for xx in range(0, w, tw):
            canvas.paste(tile, (xx, yy))
    return canvas


def _composite_paper_layer(
    base_rgba: Any,
    mask: Any,
    fill_rgb: tuple[int, int, int],
    delta_z: float,
    dx: float,
    dy: float,
    alpha_scale: float,
    unit: float,
    layer_seed: int,
) -> None:
    from PIL import Image, ImageChops, ImageFilter

    if alpha_scale <= 0.01:
        return
    w, h = base_rgba.size
    shift_x = int(round(dx))
    shift_y = int(round(dy))

    shifted_mask = ImageChops.offset(mask, shift_x, shift_y)
    if alpha_scale < 0.999:
        shifted_mask = shifted_mask.point(lambda p: _clamp_u8(p * alpha_scale))

    sh_dx = int(round(0.64 * 4.0 * delta_z * unit))
    sh_dy = int(round(0.77 * 4.0 * delta_z * unit))
    sh_blur = max(1.0, 2.8 * delta_z * unit)
    shadow_mask = ImageChops.offset(shifted_mask, sh_dx, sh_dy).filter(ImageFilter.GaussianBlur(radius=sh_blur))
    shadow_alpha = shadow_mask.point(lambda p: _clamp_u8(p * 0.34))
    shadow_layer = Image.new('RGBA', (w, h), (18, 20, 30, 255))
    shadow_layer.putalpha(shadow_alpha)
    base_rgba.alpha_composite(shadow_layer)

    rim_shift = max(1, int(round(1.6 * unit)))
    rim_mask = ImageChops.subtract(shifted_mask, ImageChops.offset(shifted_mask, rim_shift, rim_shift))
    rim_alpha = rim_mask.point(lambda p: _clamp_u8(p * 0.36))
    rim_layer = Image.new('RGBA', (w, h), (252, 246, 234, 255))
    rim_layer.putalpha(rim_alpha)

    paper_rgb = _grained_paper_fill(w, h, fill_rgb, layer_seed)
    paper_shifted = ImageChops.offset(paper_rgb, shift_x, shift_y).convert('RGBA')
    paper_shifted.putalpha(shifted_mask)
    base_rgba.alpha_composite(paper_shifted)
    base_rgba.alpha_composite(rim_layer)


def _draw_paper_cutout(
    scene: dict[str, Any],
    frame: int,
    w: int,
    h: int,
    seed: int,
    background: str,
    foreground: str,
    accent: str,
    reduced_motion: bool,
) -> Any:
    from PIL import Image, ImageDraw

    unit = min(w / 960.0, h / 540.0)
    dur = max(1, int(scene['duration_frames']))
    u = frame / max(1, dur - 1)
    cam_preset = (scene.get('camera') or {}).get('preset', 'locked')
    static_unfold = bool(reduced_motion or cam_preset == 'locked')

    bg_rgb = hex_to_rgb(background)
    canvas = _grained_paper_fill(w, h, bg_rgb, seed).convert('RGBA')

    base_px = 0.0 if static_unfold else math.sin(u * math.tau) * 8.5 * unit
    base_py = 0.0 if static_unfold else math.cos(u * math.pi) * 3.5 * unit

    def layer_alpha(reveal_start: float) -> float:
        if not static_unfold:
            return 1.0
        span = 6.0
        return max(0.0, min(1.0, (frame + 1.0 - reveal_start) / span))

    m1 = Image.new('L', (w, h), 0)
    d1 = ImageDraw.Draw(m1)
    d1.rounded_rectangle(
        (w * 0.52, h * 0.15, w * 0.92, h * 0.80),
        radius=max(6, int(round(18 * unit))),
        fill=255,
    )
    _composite_paper_layer(
        canvas,
        m1,
        mix_oklab(background, foreground, 0.14),
        delta_z=1.0,
        dx=base_px * 0.35,
        dy=base_py * 0.35,
        alpha_scale=layer_alpha(0.0),
        unit=unit,
        layer_seed=seed + 11,
    )

    m2 = Image.new('L', (w, h), 0)
    d2 = ImageDraw.Draw(m2)
    hill_pts: list[tuple[float, float]] = [(w * 0.50, h * 0.80)]
    for step_i in range(19):
        t = step_i / 18.0
        hx = w * (0.50 + 0.44 * t)
        hy = h * (0.60 - 0.12 * math.sin(t * math.pi) - 0.04 * math.sin(t * math.tau + 0.6))
        hill_pts.append((hx, hy))
    hill_pts.append((w * 0.94, h * 0.80))
    d2.polygon(hill_pts, fill=255)
    _composite_paper_layer(
        canvas,
        m2,
        mix_oklab(background, foreground, 0.28),
        delta_z=1.5,
        dx=base_px * 0.68,
        dy=base_py * 0.68,
        alpha_scale=layer_alpha(3.0),
        unit=unit,
        layer_seed=seed + 23,
    )

    m3 = Image.new('L', (w, h), 0)
    d3 = ImageDraw.Draw(m3)
    cx, cy = w * 0.72, h * 0.42
    rad = 84.0 * unit
    pts: list[tuple[float, float]] = []
    for i in range(12):
        ang = i * math.tau / 12.0 - math.pi / 2.0
        r_i = rad if i % 2 == 0 else rad * 0.62
        pts.append((cx + r_i * math.cos(ang), cy + r_i * math.sin(ang)))
    d3.polygon(pts, fill=255)
    inner_r = rad * 0.26
    d3.ellipse((cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r), fill=0)
    _composite_paper_layer(
        canvas,
        m3,
        hex_to_rgb(accent),
        delta_z=1.6,
        dx=base_px * 1.0,
        dy=base_py * 1.0,
        alpha_scale=layer_alpha(6.0),
        unit=unit,
        layer_seed=seed + 37,
    )

    return canvas.convert('RGB')


def draw_art_scene(
    scene: dict[str, Any],
    frame: int,
    output: dict[str, Any],
    seed: int,
    supersampling: int = 1,
    look_mode: str = 'agx',
    reduced_motion: bool = False,
) -> tuple[Any, list[dict[str, Any]]]:
    from PIL import Image, ImageDraw

    width, height = int(output['width']), int(output['height'])
    fps_val = float(Fraction(output.get('fps', '30/1')))
    scale = max(1, int(supersampling))
    w, h = width * scale, height * scale
    params = scene.get('params', {})
    recipe = scene['recipe']
    is_dark = recipe in {'cinematic-3d', 'stepped-clay'}
    default_bg = '#14171c' if is_dark else '#eee9df'
    default_fg = '#ede8de' if is_dark else '#252925'
    background = str(params.get('background', default_bg))
    foreground = str(params.get('foreground', default_fg))
    accent = str(params.get('accent', '#bb5537'))
    dither = (((frame * 73 + seed * 19) % 17) / 17.0 - 0.5) * 0.75 if scale >= 2 else 0.0

    if recipe == 'cinematic-3d':
        image = _draw_cinematic_3d(
            scene, frame, w, h, fps_val, seed, background, foreground, accent, look_mode, dither, reduced_motion
        )
    elif recipe == 'stepped-clay':
        image = _draw_stepped_clay(
            scene, frame, w, h, fps_val, seed, background, foreground, accent, look_mode, dither, reduced_motion
        )
    elif recipe == 'paper-cutout':
        image = _draw_paper_cutout(
            scene, frame, w, h, seed, background, foreground, accent, reduced_motion
        )
    else:
        raise ValueError(f'Unsupported art recipe: {recipe!r}')

    canvas = ImageDraw.Draw(image)
    bounds = apply_typography_and_hud(canvas, scene, frame, w, h, scale=scale)
    if scale > 1:
        image = image.resize((width, height), Image.Resampling.LANCZOS)
    return image, bounds
