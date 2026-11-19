import math

from .camera import Camera3D
from .lighting import build_monolith_assembly, shade_facet_three_point
from .motion import ease, smooth, spring_damper, verlet_ribbon
from .palette import hex_to_rgb, mix_oklab, rgb_to_hex
from .typography import draw_tracked_text, measure_tracked_text, resolve_font

LEGACY_RECIPES = {'assembly', 'rings', 'signal', 'title'}


def scene_geometry(scene, frame, width, height, seed):
    u = frame / max(1, scene['duration_frames'] - 1)
    phase = u * math.tau
    cx, cy = width * 0.67, height * 0.49
    unit = min(width / 960, height / 540)
    shapes = []
    recipe = scene['recipe']
    if recipe == 'assembly':
        for index in range(7):
            p = smooth((u * 1.7) - index * 0.08)
            target = (index - 3) * 28 * unit
            travel = (1 - p) * (60 + index * 9) * unit
            x = cx + target + travel * math.cos(index * 2.4)
            y = cy + target * 0.5 + travel * math.sin(index * 2.4)
            size = (74 - index * 4) * unit
            angle = 0.65 + 0.4 * (1 - p) + 0.025 * math.sin(phase + index)
            corners = [(x + size * math.cos(angle + j * math.pi / 2), y + size * math.sin(angle + j * math.pi / 2)) for j in range(4)]
            shapes.append(('polygon', corners, index % 3 == 0, 2 * unit))
    elif recipe == 'rings':
        for index in range(10):
            radius = (46 + index * 12) * unit
            points = []
            tilt = 0.3 * math.sin(phase * 0.55 + seed * 0.01)
            for j in range(121):
                angle = j * math.tau / 120
                x = math.cos(angle) * radius
                y = math.sin(angle) * radius * (0.35 + 0.16 * math.cos(phase * 0.6))
                points.append((cx + x * math.cos(tilt) - y * math.sin(tilt), cy + (index - 4.5) * 9 * unit + x * math.sin(tilt) + y * math.cos(tilt)))
            shapes.append(('line', points, index % 3 == 0, (2 if index % 3 else 3) * unit))
    elif recipe in {'signal', 'hud-lock'}:
        for index in range(32):
            x = cx + (index - 15.5) * 9 * unit
            envelope = math.exp(-((index - 15.5) / 12) ** 2)
            amplitude = (22 + 72 * envelope * (0.5 + 0.5 * math.sin(phase * 1.4 + index * 0.25))) * unit
            shapes.append(('line', [(x, cy - amplitude), (x, cy + amplitude)], index % 5 == 0, 4 * unit))
    elif recipe == 'aperture':
        shot = scene.get('params', {}).get('shot', 'hero')
        for r_scale, colored in [(148, False), (124, True), (104, False), (36, True)]:
            r = r_scale * unit
            pts = [(cx + r * math.cos(j * math.tau / 72), cy + r * math.sin(j * math.tau / 72)) for j in range(73)]
            shapes.append(('line', pts, colored, (3 if colored else 2) * unit))
        open_amt = (0.28 + 0.52 * smooth((u - 0.1) / 0.8)) if shot == 'iris' else (0.44 + 0.10 * math.sin(u * math.pi))
        inner_r = (28 + 48 * open_amt) * unit
        outer_r = 100 * unit
        for idx in range(11):
            a0 = idx * math.tau / 11 + open_amt * 0.45
            a1 = a0 + 0.62
            p0 = (cx + outer_r * math.cos(a0), cy + outer_r * math.sin(a0))
            p1 = (cx + inner_r * math.cos(a1), cy + inner_r * math.sin(a1))
            shapes.append(('line', [p0, p1], idx % 3 == 0, 2 * unit))
    elif recipe in {'title', 'kinetic-type', 'prism-monolith', 'data-horizon'}:
        radius = (105 + 12 * math.sin(phase)) * unit
        points = [(cx + radius * math.cos(j * math.tau / 64), cy + radius * math.sin(j * math.tau / 64)) for j in range(65)]
        shapes.append(('line', points, True, 3 * unit))
    return shapes


def apply_typography_and_hud(canvas, scene: dict, frame: int, w: int, h: int, scale: int = 1) -> list[dict]:
    unit = min(w / 960.0, h / 540.0)
    params = scene.get('params', {})
    recipe = scene['recipe']
    use_default_font = params.get('font_mode') == 'default' or (params.get('font_mode') is None and recipe in LEGACY_RECIPES)

    foreground = params.get('foreground', '#252925')
    background = params.get('background', '#eee9df')
    accent = params.get('accent', '#bb5537')
    muted_rgb = mix_oklab(foreground, background, 0.42)
    muted = rgb_to_hex(muted_rgb)

    if recipe != 'hud-lock':
        canvas.line((w * 0.07, h * 0.85, w * 0.93, h * 0.85), fill=foreground if recipe in LEGACY_RECIPES else muted, width=max(1, round(unit)))
        progress = frame / max(1, scene['duration_frames'] - 1)
        canvas.line((w * 0.07, h * 0.85, w * (0.07 + 0.86 * progress), h * 0.85), fill=accent, width=max(1, round(3 * unit)))

    bounds = []
    kicker = params.get('kicker', '')
    if kicker:
        k_font = resolve_font(round(13 * unit), bold=True, prefer_default=use_default_font)
        kw, _ = measure_tracked_text(canvas, kicker, k_font, tracking_px=1.6 * unit)
        if w * 0.07 + kw > w * 0.48:
            raise ValueError(f"Text exceeds its safe layout region in scene {scene['id']}: kicker")
        k_box = draw_tracked_text(canvas, (w * 0.07, h * 0.29), kicker, k_font, accent, tracking_px=1.6 * unit)
        bounds.append({'field': 'kicker', 'bounds': [round(v / scale, 3) for v in k_box]})

    max_right = w * (0.43 if recipe in LEGACY_RECIPES else 0.50)
    u = frame / max(1, scene['duration_frames'] - 1)
    entrance = 1.0 if recipe in LEGACY_RECIPES else min(1.0, spring_damper(u * 2.2, zeta=1.0, omega=4.2))
    y_slide = (1.0 - entrance) * 14.0 * unit

    for key, size, y_norm, is_bold, track in [('heading', 56 if recipe in LEGACY_RECIPES else 48, 0.39, True, 0.8), ('subheading', 19, 0.55, False, 0.2)]:
        value = params.get(key, '')
        if not value:
            continue
        font = resolve_font(round(size * unit), bold=is_bold, prefer_default=use_default_font)
        x = w * 0.07
        y = h * y_norm + y_slide
        if recipe in LEGACY_RECIPES:
            box = canvas.textbbox((x, h * y_norm), value, font=font)
            if box[2] > max_right or box[3] > h * 0.8:
                raise ValueError(f"Text exceeds its safe layout region in scene {scene['id']}: {key}")
            canvas.text((x, h * y_norm), value, fill=foreground, font=font)
            bounds.append({'field': key, 'bounds': [round(v / scale, 3) for v in box]})
        else:
            tw, th = measure_tracked_text(canvas, value, font, tracking_px=track * unit)
            check_box = canvas.textbbox((x, h * y_norm), value, font=font)
            if x + tw > max_right or check_box[3] > h * 0.80:
                raise ValueError(f"Text exceeds its safe layout region in scene {scene['id']}: {key}")
            text_color = foreground if key == 'heading' else rgb_to_hex(mix_oklab(foreground, background, 0.18))
            drawn_box = draw_tracked_text(canvas, (x, y), value, font, text_color, tracking_px=track * unit)
            bounds.append({'field': key, 'bounds': [round(v / scale, 3) for v in drawn_box]})
    return bounds


def _draw_prism_monolith(canvas, scene, frame, w, h, fps_val, seed, background, foreground, accent, look_mode, dither):
    unit = min(w / 960.0, h / 540.0)
    u = frame / max(1, scene['duration_frames'] - 1)
    grid_col = rgb_to_hex(mix_oklab(background, foreground, 0.09))
    canvas.line((w * 0.07, h * 0.14, w * 0.93, h * 0.14), fill=grid_col, width=max(1, round(unit)))

    shadow_cx, shadow_cy = w * 0.73, h * 0.66
    for ring in range(6, 0, -1):
        rx = (108 + ring * 13) * unit
        ry = (24 + ring * 4) * unit
        sh_col = rgb_to_hex(mix_oklab(background, '#050608', 0.06 * (7 - ring)))
        canvas.ellipse((shadow_cx - rx, shadow_cy - ry, shadow_cx + rx, shadow_cy + ry), fill=sh_col)

    cam = Camera3D.from_scene(scene, frame, fps_val, seed, camera_locked=False)
    facets = build_monolith_assembly(u, seed)
    projected_list = []
    for verts, mat_role in facets:
        proj_pts = []
        depths = []
        valid = True
        for v in verts:
            pr = cam.project(v, w, h)
            if pr is None:
                valid = False
                break
            proj_pts.append((pr[0], pr[1]))
            depths.append(pr[2])
        if not valid:
            continue
        albedo = accent if mat_role == 'accent' else (rgb_to_hex(mix_oklab(background, foreground, 0.22)) if mat_role == 'plinth' else foreground)
        rgb = shade_facet_three_point(verts, cam.position, albedo, accent, look_mode=look_mode, dither=dither)
        edge_rgb = mix_oklab(rgb_to_hex(rgb), foreground, 0.16)
        projected_list.append((sum(depths) / len(depths), proj_pts, rgb, edge_rgb))

    projected_list.sort(key=lambda item: -item[0])
    for _, pts, fill_rgb, edge_rgb in projected_list:
        canvas.polygon(pts, fill=fill_rgb, outline=edge_rgb, width=max(1, round(0.9 * unit)))


def _draw_kinetic_type(canvas, scene, frame, w, h, fps_val, seed, background, foreground, accent):
    unit = min(w / 960.0, h / 540.0)
    u = frame / max(1, scene['duration_frames'] - 1)
    subtle = rgb_to_hex(mix_oklab(background, foreground, 0.12))
    for col_frac in (0.07, 0.52, 0.93):
        canvas.line((w * col_frac, h * 0.14, w * col_frac, h * 0.80), fill=subtle, width=max(1, round(unit)))

    anchor_x, anchor_y = w * 0.73, h * 0.18
    def anchor_fn(t_sec):
        swing = math.sin(t_sec * 3.4 + (seed % 11) * 0.2) * 42.0 * unit
        return (anchor_x + swing, anchor_y)

    nodes = verlet_ribbon(anchor_fn, segments=9, segment_length=28.0 * unit, frame=frame + 18, fps=fps_val, substeps=6, iterations=12, gravity=260.0 * unit)
    canvas.line(nodes, fill=foreground, width=max(2, round(2.6 * unit)), joint='curve')
    for idx, (nx, ny) in enumerate(nodes):
        r = (7.5 if idx == len(nodes) - 1 else 3.2) * unit
        col = accent if idx in {0, len(nodes) - 1} else foreground
        canvas.ellipse((nx - r, ny - r, nx + r, ny + r), fill=col)

    tc_font = resolve_font(round(12 * unit), bold=False)
    draw_tracked_text(canvas, (w * 0.54, h * 0.16), f'FRAME {frame:04d} / {scene["duration_frames"]:04d}', tc_font, rgb_to_hex(mix_oklab(foreground, background, 0.35)), tracking_px=1.1 * unit)


def _draw_data_horizon(canvas, scene, frame, w, h, background, foreground, accent):
    unit = min(w / 960.0, h / 540.0)
    u = frame / max(1, scene['duration_frames'] - 1)
    values = scene.get('params', {}).get('series') or [28.0, 44.0, 39.0, 62.0, 74.0, 68.0, 89.0, 95.0]
    vmin, vmax = min(0.0, min(values)), max(values) * 1.12 or 1.0
    left, right = w * 0.54, w * 0.91
    top, bottom = h * 0.22, h * 0.75
    grid_col = rgb_to_hex(mix_oklab(background, foreground, 0.13))

    for step in range(5):
        gy = bottom - (bottom - top) * (step / 4.0)
        canvas.line((left, gy, right, gy), fill=grid_col, width=max(2, round(1.8 * unit)))

    count = len(values)
    slot = (right - left) / max(1, count)
    bar_w = slot * 0.56
    spline_pts = []
    label_font = resolve_font(round(11 * unit), bold=True)

    for idx, val in enumerate(values):
        local_u = ease('cubic_out', (u * 1.45) - idx * (0.42 / max(1, count)))
        norm_h = ((val - vmin) / (vmax - vmin)) * local_u
        bx0 = left + idx * slot + (slot - bar_w) * 0.5
        bx1 = bx0 + bar_w
        by0 = bottom - norm_h * (bottom - top)
        is_peak = val == max(values)
        bar_col = accent if is_peak else rgb_to_hex(mix_oklab(foreground, background, 0.25))
        canvas.rectangle((bx0, by0, bx1, bottom), fill=bar_col)
        spline_pts.append(((bx0 + bx1) * 0.5, by0 - 8.0 * unit))
        if is_peak and local_u > 0.65:
            canvas.text((bx0 - 2 * unit, by0 - 22 * unit), f'{val:.0f}', fill=accent, font=label_font)

    if len(spline_pts) >= 2:
        canvas.line(spline_pts, fill=foreground, width=max(2, round(2.2 * unit)), joint='curve')


def _draw_hud_lock(canvas, scene, frame, w, h, seed, background, foreground, accent):
    unit = min(w / 960.0, h / 540.0)
    u = frame / max(1, scene['duration_frames'] - 1)
    cx, cy = w * 0.72, h * 0.43
    for idx in range(6):
        rad = (34 + idx * 21 + 8.0 * math.sin(u * math.tau + idx * 0.7)) * unit
        direction = 1 if idx % 2 == 0 else -1
        a0 = (u * 320 * direction + idx * 52 + (seed % 23)) % 360
        canvas.arc((cx - rad, cy - rad, cx + rad, cy + rad), start=a0, end=a0 + 185, fill=accent if idx % 2 == 0 else foreground, width=max(2, round(3.0 * unit)))
    sweep_ang = u * math.tau * 1.5
    outer = 148 * unit
    sx = cx + outer * math.cos(sweep_ang)
    sy = cy + outer * math.sin(sweep_ang)
    canvas.line((cx, cy, sx, sy), fill=accent, width=max(2, round(2.5 * unit)))
    for tick in range(16):
        tang = tick * math.tau / 16 + u * 0.8
        r_in = (146 + 6 * math.sin(u * math.tau * 2 + tick)) * unit
        r_out = r_in + 12 * unit
        canvas.line((cx + r_in * math.cos(tang), cy + r_in * math.sin(tang), cx + r_out * math.cos(tang), cy + r_out * math.sin(tang)), fill=foreground, width=max(1, round(1.8 * unit)))

    bar_top = int(round(h * 0.84))
    bar_bg = rgb_to_hex(mix_oklab(foreground, background, 0.10))
    bar_fg = background
    canvas.rectangle((0, bar_top, w, h), fill=bar_bg)
    canvas.line((0, bar_top, w, bar_top), fill=foreground, width=max(2, round(2 * unit)))
    lock_font = resolve_font(round(13 * unit), bold=True)
    draw_tracked_text(canvas, (w * 0.07, bar_top + (h - bar_top) * 0.34), 'REELSYNTAX  //  PROTECTED LOWER REGION LOCKED', lock_font, bar_fg, tracking_px=1.4 * unit)


def draw(scene, frame, output, seed, supersampling=1, look_mode='agx', reduced_motion=False):
    from fractions import Fraction
    from PIL import Image, ImageDraw
    width, height = output['width'], output['height']
    fps_val = float(Fraction(output.get('fps', '30/1')))
    scale = max(1, int(supersampling))
    w, h = width * scale, height * scale
    params = scene['params']
    recipe = scene['recipe']
    if recipe == 'brand-sting':
        from .brand import render_brand_sting_frame
        image, bounds = render_brand_sting_frame(scene, frame, w, h, fps_val, scale=scale, reduced_motion=reduced_motion)
        if scale > 1:
            image = image.resize((width, height), Image.Resampling.LANCZOS)
        return image, bounds
    default_bg = '#14171c' if recipe == 'prism-monolith' else '#eee9df'
    default_fg = '#ede8de' if recipe == 'prism-monolith' else '#252925'
    background, foreground, accent = (params.get(k, v) for k, v in [('background', default_bg), ('foreground', default_fg), ('accent', '#bb5537')])

    image = Image.new('RGB', (w, h), background)
    canvas = ImageDraw.Draw(image)
    dither = (((frame * 73 + seed * 19) % 17) / 17.0 - 0.5) * 0.75 if scale >= 2 else 0.0

    if recipe in {'news-ticker', 'loop-art'}:
        from .format_plates import draw_loop_art, draw_news_ticker
        rm = bool(output.get('reduced_motion', False))
        if recipe == 'news-ticker':
            bounds = draw_news_ticker(canvas, image, scene, frame, w, h, seed, scale=scale, reduced_motion=rm)
        else:
            bounds = draw_loop_art(canvas, image, scene, frame, w, h, seed, scale=scale, reduced_motion=rm)
        if scale > 1:
            image = image.resize((width, height), Image.Resampling.LANCZOS)
        return image, bounds
    if recipe == 'shape-field':
        from .shapes import paint_shapes
        paint_shapes(image, params['shapes'], background, scene.get('locked_regions', []), output.get('original_size', (width, height)), frame, fps_val)
        if scale > 1:
            image = image.resize((width, height), Image.Resampling.LANCZOS)
        return image, []
    if recipe == 'character-stage':
        from .character import draw_character_scene
        bounds = draw_character_scene(canvas, scene, frame, w, h, fps_val, seed, background, foreground, accent, scale=scale, look_mode=look_mode, dither=dither)
        if scale > 1:
            image = image.resize((width, height), Image.Resampling.LANCZOS)
        return image, bounds
    if recipe in LEGACY_RECIPES:
        for kind, points, colored, thickness in scene_geometry(scene, frame, w, h, seed):
            fill = accent if colored else foreground
            if kind == 'polygon':
                canvas.polygon(points, fill=background, outline=fill, width=max(1, round(thickness)))
            else:
                canvas.line(points, fill=fill, width=max(1, round(thickness)), joint='curve')
    elif recipe == 'prism-monolith':
        _draw_prism_monolith(canvas, scene, frame, w, h, fps_val, seed, background, foreground, accent, look_mode, dither)
    elif recipe == 'kinetic-type':
        _draw_kinetic_type(canvas, scene, frame, w, h, fps_val, seed, background, foreground, accent)
    elif recipe == 'data-horizon':
        _draw_data_horizon(canvas, scene, frame, w, h, background, foreground, accent)
    elif recipe == 'hud-lock':
        _draw_hud_lock(canvas, scene, frame, w, h, seed, background, foreground, accent)

    bounds = apply_typography_and_hud(canvas, scene, frame, w, h, scale=scale)
    if scale > 1:
        image = image.resize((width, height), Image.Resampling.LANCZOS)
    return image, bounds
