import math
import re
from typing import Any

from .palette import contrast_ratio, hex_to_rgb, mix_oklab, rgb_to_hex
from .typography import draw_tracked_text, measure_tracked_text, resolve_font

BULLET_SPLIT_RE = re.compile(r"\s*(?:•|◆|\||—|;)\s*")


def _pick_badge_fg(bg_hex: str) -> str:
    bg_rgb = hex_to_rgb(bg_hex)
    dark = "#0f141a"
    light = "#f7f9fc"
    return dark if contrast_ratio(hex_to_rgb(dark), bg_rgb) >= contrast_ratio(hex_to_rgb(light), bg_rgb) else light


def _fit_font_for_width(canvas: Any, text: str, max_width: float, start_px: int, min_px: int, *, bold: bool, tracking: float) -> tuple[Any, float, float]:
    px = max(min_px, start_px)
    while px >= min_px:
        font = resolve_font(px, bold=bold)
        tw, th = measure_tracked_text(canvas, text, font, tracking_px=tracking)
        if tw <= max_width or px == min_px:
            return font, tw, th
        px = max(min_px, px - 2)
    font = resolve_font(min_px, bold=bold)
    tw, th = measure_tracked_text(canvas, text, font, tracking_px=tracking)
    return font, tw, th


def _paginate_ticker_text(text: str) -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    parts = [p.strip() for p in BULLET_SPLIT_RE.split(cleaned) if p.strip()]
    if len(parts) >= 2:
        return parts
    words = cleaned.split(" ")
    if len(words) < 4:
        return [cleaned]
    mid = (len(words) + 1) // 2
    return [" ".join(words[:mid]), " ".join(words[mid:])]


def _draw_stage_telemetry(canvas: Any, stage: tuple[float, float, float, float], frame: int, duration_frames: int, unit: float, seed: int, background: str, foreground: str, accent: str, reduced_motion: bool) -> None:
    sx0, sy0, sx1, sy1 = stage
    sw = sx1 - sx0
    sh = sy1 - sy0
    stage_bg = rgb_to_hex(mix_oklab(background, foreground, 0.06))
    grid_col = rgb_to_hex(mix_oklab(background, foreground, 0.16))
    stroke_w = max(2, round(1.8 * unit))
    canvas.rectangle((sx0, sy0, sx1, sy1), fill=stage_bg, outline=grid_col, width=stroke_w)

    for row in range(1, 4):
        gy = sy0 + sh * (row / 4.0)
        canvas.line((sx0 + sw * 0.04, gy, sx1 - sw * 0.04, gy), fill=grid_col, width=stroke_w)

    u = 0.0 if reduced_motion else (frame / max(1, duration_frames - 1))
    bar_count = 14
    pad_x = sw * 0.07
    usable_w = sw - 2.0 * pad_x
    slot = usable_w / bar_count
    bar_w = max(4.0, slot * 0.54)
    base_y = sy1 - sh * 0.14
    max_bar_h = sh * 0.64
    pts: list[tuple[float, float]] = []

    for idx in range(bar_count):
        phase = (seed % 17) * 0.31 + idx * 0.52 + u * math.tau
        val = 0.32 + 0.56 * (0.5 + 0.5 * math.sin(phase))
        bx0 = sx0 + pad_x + idx * slot + (slot - bar_w) * 0.5
        bx1 = bx0 + bar_w
        by0 = base_y - val * max_bar_h
        is_hi = idx % 4 == 2
        col = accent if is_hi else rgb_to_hex(mix_oklab(foreground, background, 0.34))
        canvas.rectangle((bx0, by0, bx1, base_y), fill=col)
        pts.append(((bx0 + bx1) * 0.5, by0 - 6.0 * unit))

    if len(pts) >= 2:
        canvas.line(pts, fill=foreground, width=max(2, round(2.2 * unit)), joint="curve")


def draw_news_ticker(
    canvas: Any,
    image: Any,
    scene: dict[str, Any],
    frame: int,
    w: int,
    h: int,
    seed: int,
    scale: int = 1,
    reduced_motion: bool = False,
) -> list[dict[str, Any]]:
    from PIL import Image, ImageDraw

    unit = min(w / 960.0, h / 540.0)
    params = scene.get("params", {})
    background = str(params.get("background", "#1e2430"))
    foreground = str(params.get("foreground", "#f4f6f9"))
    accent = str(params.get("accent", "#e06246"))
    duration = max(1, int(scene.get("duration_frames", 60)))
    is_vertical = h > w

    if is_vertical:
        stage_box = (w * 0.06, h * 0.125, w * 0.94, h * 0.555)
        kicker_y0, kicker_y1 = h * 0.568, h * 0.610
        banner_y0, banner_y1 = h * 0.620, h * 0.720
        strip_y0, strip_y1 = h * 0.730, h * 0.794
    else:
        stage_box = (w * 0.05, h * 0.10, w * 0.95, h * 0.635)
        kicker_y0, kicker_y1 = h * 0.648, h * 0.698
        banner_y0, banner_y1 = h * 0.710, h * 0.820
        strip_y0, strip_y1 = h * 0.832, h * 0.905

    _draw_stage_telemetry(canvas, stage_box, frame, duration, unit, seed, background, foreground, accent, reduced_motion)

    bounds: list[dict[str, Any]] = []
    margin_x = w * 0.04
    right_x = w * 0.96
    stroke_w = max(2, round(2.0 * unit))

    kicker = str(params.get("kicker", "")).strip()
    if kicker:
        k_font = resolve_font(round(14 * unit), bold=True)
        kw, kh = measure_tracked_text(canvas, kicker, k_font, tracking_px=1.2 * unit)
        pad_kx = 12.0 * unit
        kx0 = margin_x
        kx1 = min(right_x, kx0 + kw + 2.0 * pad_kx)
        canvas.rectangle((kx0, kicker_y0, kx1, kicker_y1), fill=accent)
        k_fg = _pick_badge_fg(accent)
        ky = kicker_y0 + max(2.0, (kicker_y1 - kicker_y0 - kh) * 0.42)
        k_box = draw_tracked_text(canvas, (kx0 + pad_kx, ky), kicker, k_font, k_fg, tracking_px=1.2 * unit)
        bounds.append({"field": "kicker", "bounds": [round(v / scale, 3) for v in k_box]})

    banner_bg = rgb_to_hex(mix_oklab(background, foreground, 0.07))
    banner_border = rgb_to_hex(mix_oklab(background, foreground, 0.24))
    canvas.rectangle((margin_x, banner_y0, right_x, banner_y1), fill=banner_bg, outline=banner_border, width=stroke_w)
    spine_w = max(4.0, 10.0 * unit)
    canvas.rectangle((margin_x, banner_y0, margin_x + spine_w, banner_y1), fill=accent)

    heading = str(params.get("heading", "")).strip()
    if heading:
        text_x0 = margin_x + spine_w + 14.0 * unit
        max_hw = (right_x - 14.0 * unit) - text_x0
        h_track = 0.5 * unit
        h_font, _, hh = _fit_font_for_width(
            canvas,
            heading,
            max_hw,
            round(32 * unit),
            round(16 * unit),
            bold=True,
            tracking=h_track,
        )
        hy = banner_y0 + max(4.0, (banner_y1 - banner_y0 - hh) * 0.44)
        h_box = draw_tracked_text(canvas, (text_x0, hy), heading, h_font, foreground, tracking_px=h_track)
        bounds.append({"field": "heading", "bounds": [round(v / scale, 3) for v in h_box]})

    strip_bg = rgb_to_hex(mix_oklab(background, "#0c1016", 0.35) if sum(hex_to_rgb(background)) < 384 else mix_oklab(background, foreground, 0.14))
    canvas.rectangle((margin_x, strip_y0, right_x, strip_y1), fill=strip_bg, outline=banner_border, width=stroke_w)

    subheading = str(params.get("subheading", "")).strip()
    if subheading:
        ix0 = int(round(margin_x + 12.0 * unit))
        ix1 = int(round(right_x - 12.0 * unit))
        iy0 = int(round(strip_y0 + 3.0 * unit))
        iy1 = int(round(strip_y1 - 3.0 * unit))
        strip_w = max(16, ix1 - ix0)
        strip_h = max(16, iy1 - iy0)
        s_font = resolve_font(round(16 * unit), bold=False)

        if reduced_motion:
            pages = _paginate_ticker_text(subheading)
            if not pages:
                pages = [subheading]
            page_dur = max(24, duration // len(pages))
            page_idx = min(len(pages) - 1, frame // page_dur)
            page_text = pages[page_idx]
            badge_text = f"{page_idx + 1}/{len(pages)}"
            bw, _ = measure_tracked_text(canvas, badge_text, s_font, tracking_px=0.2 * unit)
            avail_w = max(40.0, strip_w - bw - 16.0 * unit)
            fit_font, _, sh = _fit_font_for_width(
                canvas,
                page_text,
                avail_w,
                round(16 * unit),
                round(11 * unit),
                bold=False,
                tracking=0.2 * unit,
            )
            sy = iy0 + max(1.0, (strip_h - sh) * 0.42)
            s_box = draw_tracked_text(canvas, (float(ix0), sy), page_text, fit_font, foreground, tracking_px=0.2 * unit)
            draw_tracked_text(canvas, (float(ix1) - bw - 2.0 * unit, sy), badge_text, s_font, accent, tracking_px=0.2 * unit)
            bounds.append({"field": "subheading", "bounds": [round(v / scale, 3) for v in s_box]})
        else:
            unit_chunk = f"{subheading}   ◆   "
            chunk_w_f, chunk_h_f = measure_tracked_text(canvas, unit_chunk, s_font, tracking_px=0.2 * unit)
            unit_w = max(32, int(math.ceil(chunk_w_f)))
            repeats = max(2, math.ceil((strip_w + unit_w) / unit_w))
            tile_w = unit_w * repeats
            tile_img = Image.new("RGBA", (tile_w, strip_h), (0, 0, 0, 0))
            tile_draw = ImageDraw.Draw(tile_img)
            text_y = max(1.0, (strip_h - chunk_h_f) * 0.40)
            for rep in range(repeats):
                draw_tracked_text(tile_draw, (rep * unit_w, text_y), unit_chunk, s_font, foreground, tracking_px=0.2 * unit)

            px_per_frame = max(2, round(4 * w / 1080.0))
            offset = (frame * px_per_frame) % tile_w
            first_w = min(strip_w, tile_w - offset)
            slice_a = tile_img.crop((offset, 0, offset + first_w, strip_h))
            image.paste(slice_a, (ix0, iy0), slice_a)
            if first_w < strip_w:
                rem = strip_w - first_w
                slice_b = tile_img.crop((0, 0, rem, strip_h))
                image.paste(slice_b, (ix0 + first_w, iy0), slice_b)
            bounds.append({
                "field": "subheading",
                "bounds": [round(ix0 / scale, 3), round(iy0 / scale, 3), round(ix1 / scale, 3), round(iy1 / scale, 3)],
            })

    return bounds


def draw_loop_art(
    canvas: Any,
    image: Any,
    scene: dict[str, Any],
    frame: int,
    w: int,
    h: int,
    seed: int,
    scale: int = 1,
    reduced_motion: bool = False,
) -> list[dict[str, Any]]:
    _ = image
    unit = min(w / 960.0, h / 540.0)
    params = scene.get("params", {})
    background = str(params.get("background", "#1e2430"))
    foreground = str(params.get("foreground", "#f4f6f9"))
    accent = str(params.get("accent", "#5aa6b0"))
    total = max(1, int(scene.get("duration_frames", 180)))
    u = 0.0 if reduced_motion else ((frame % total) / float(total))
    theta = math.tau * u

    heading = str(params.get("heading", "")).strip()
    subheading = str(params.get("subheading", "")).strip()
    kicker = str(params.get("kicker", "")).strip()
    has_text = bool(heading or subheading or kicker)

    cx = w * 0.50
    cy = h * (0.39 if has_text and h > w else (0.42 if has_text else 0.50))
    base_r = min(w, h) * (0.26 if has_text and h > w else 0.30)
    stroke_w = max(2, round(2.2 * unit))
    phase_seed = (seed % 29) * 0.21

    for ring_idx in range(4):
        ring_r = base_r * (0.45 + 0.18 * ring_idx)
        sign = 1.0 if ring_idx % 2 == 0 else -1.0
        mix_t = 0.20 + 0.22 * ring_idx
        ring_col = accent if ring_idx == 3 else rgb_to_hex(mix_oklab(foreground, background, mix_t))
        pts: list[tuple[float, float]] = []
        steps = 96
        for step in range(steps + 1):
            ang = math.tau * (step / steps)
            mod = 1.0 + 0.09 * math.sin(3.0 * ang + sign * theta + phase_seed) + 0.05 * math.cos(2.0 * ang - theta)
            r_cur = ring_r * mod
            pts.append((cx + r_cur * math.cos(ang), cy + r_cur * math.sin(ang)))
        canvas.line(pts, fill=ring_col, width=stroke_w, joint="curve")

    orbit_pts: list[tuple[float, float]] = []
    orbit_steps = 120
    for step in range(orbit_steps + 1):
        phi = math.tau * (step / orbit_steps)
        ox = cx + base_r * 0.84 * math.cos(phi + theta) * (0.82 + 0.18 * math.cos(2.0 * phi - theta))
        oy = cy + base_r * 0.84 * math.sin(phi + theta) * (0.82 + 0.18 * math.sin(2.0 * phi + theta))
        orbit_pts.append((ox, oy))
    canvas.line(orbit_pts, fill=accent, width=max(2, round(2.8 * unit)), joint="curve")

    node_r = max(5.0, 8.5 * unit)
    for node_idx in range(2):
        na = theta + node_idx * math.pi + phase_seed
        nx = cx + base_r * 0.96 * math.cos(na)
        ny = cy + base_r * 0.96 * math.sin(na)
        col = accent if node_idx == 0 else foreground
        canvas.ellipse((nx - node_r, ny - node_r, nx + node_r, ny + node_r), fill=col)

    bounds: list[dict[str, Any]] = []
    if not has_text:
        return bounds

    left_x = w * 0.08
    max_tw = w * 0.84
    y_cursor = h * (0.64 if h > w else 0.72)

    if kicker:
        k_font = resolve_font(round(13 * unit), bold=True)
        k_box = draw_tracked_text(canvas, (left_x, y_cursor), kicker, k_font, accent, tracking_px=1.4 * unit)
        bounds.append({"field": "kicker", "bounds": [round(v / scale, 3) for v in k_box]})
        y_cursor = k_box[3] + 8.0 * unit

    if heading:
        h_font, _, _ = _fit_font_for_width(
            canvas,
            heading,
            max_tw,
            round(36 * unit),
            round(18 * unit),
            bold=True,
            tracking=0.6 * unit,
        )
        h_box = draw_tracked_text(canvas, (left_x, y_cursor), heading, h_font, foreground, tracking_px=0.6 * unit)
        bounds.append({"field": "heading", "bounds": [round(v / scale, 3) for v in h_box]})
        y_cursor = h_box[3] + 8.0 * unit

    if subheading:
        s_font, _, _ = _fit_font_for_width(
            canvas,
            subheading,
            max_tw,
            round(18 * unit),
            round(12 * unit),
            bold=False,
            tracking=0.2 * unit,
        )
        sub_col = rgb_to_hex(mix_oklab(foreground, background, 0.18))
        s_box = draw_tracked_text(canvas, (left_x, y_cursor), subheading, s_font, sub_col, tracking_px=0.2 * unit)
        bounds.append({"field": "subheading", "bounds": [round(v / scale, 3) for v in s_box]})

    return bounds
