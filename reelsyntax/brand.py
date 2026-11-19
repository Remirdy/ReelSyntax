import copy
from dataclasses import dataclass
from fractions import Fraction
import math
from pathlib import Path
from typing import Any

from ReelSyntax_Skills.tools.registry import atomic_json, contained_path, read_json

from .motion import ease, smooth
from .palette import contrast_ratio, hex_to_rgb, mix_oklab, rgb_to_hex
from .project import asset_path, color, fields, load, number, text, validate
from .shapes import validate_shapes
from .typography import draw_tracked_text, measure_tracked_text, resolve_font

STING_FRAMES_30FPS = 54
STING_REVEAL_FRAMES_30FPS = 14
STING_REDUCED_FADE_FRAMES_30FPS = 8
STING_GROUND_HEX = "#1f2430"
STING_INK_HEX = "#f8fafc"
STING_SUBTITLE_HEX = "#94a3b8"
STING_ACCENT_HEX = "#38bdf8"
STING_MIN_WCAG_RATIO = 4.5
MARK_PRESETS = frozenset({"aperture", "hexagon", "ring", "diamond"})

STING_SUBTITLES: dict[str, str] = {
    "en": "Built with ReelSyntax",
    "tr": "ReelSyntax ile üretildi",
    "de": "Erstellt mit ReelSyntax",
    "es": "Creado con ReelSyntax",
    "fr": "Créé avec ReelSyntax",
    "pt": "Criado com ReelSyntax",
}

ISO3_TO_SHORT_LANG: dict[str, str] = {
    "eng": "en",
    "tur": "tr",
    "deu": "de",
    "spa": "es",
    "fra": "fr",
    "por": "pt",
}


@dataclass(frozen=True)
class BrandKit:
    schema_version: int = 1
    name: str = "Studio"
    background: str = STING_GROUND_HEX
    foreground: str = STING_INK_HEX
    accent: str = STING_ACCENT_HEX
    font: str | None = None
    logo: str | None = None
    margin: float = 0.0
    mark: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "name": self.name,
            "background": self.background,
            "foreground": self.foreground,
            "accent": self.accent,
            "margin": self.margin,
        }
        if self.font is not None:
            payload["font"] = self.font
        if self.logo is not None:
            payload["logo"] = self.logo
        if self.mark is not None:
            payload["mark"] = copy.deepcopy(self.mark)
        return payload


def brand_kit_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "ReelSyntax brand kit",
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "schema_version": {"const": 1},
            "name": {"type": "string", "minLength": 1, "maxLength": 80},
            "background": {"type": "string", "pattern": "^#[0-9a-fA-F]{6}$"},
            "foreground": {"type": "string", "pattern": "^#[0-9a-fA-F]{6}$"},
            "accent": {"type": "string", "pattern": "^#[0-9a-fA-F]{6}$"},
            "font": {"type": "string", "minLength": 1, "maxLength": 512},
            "logo": {"type": "string", "minLength": 1, "maxLength": 512},
            "margin": {"type": "number", "minimum": 0.0, "maximum": 0.25},
            "mark": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "preset": {"enum": sorted(MARK_PRESETS)},
                    "stroke_width": {"type": "number", "minimum": 1.0, "maximum": 12.0},
                    "scale": {"type": "number", "minimum": 0.5, "maximum": 2.0},
                    "shapes": {"type": "array", "minItems": 1, "maxItems": 32},
                },
            },
        },
    }


def resolve_attribution(explicit: bool | str | None, config_default: bool = False) -> bool:
    if explicit is None:
        return bool(config_default)
    if type(explicit) is bool:
        return explicit
    if isinstance(explicit, str):
        low = explicit.strip().lower()
        if low in {"on", "true", "1", "yes"}:
            return True
        if low in {"off", "false", "0", "no"}:
            return False
    raise ValueError(f"Expected attribution setting 'on' or 'off', got {explicit!r}")


def sting_duration_frames(fps: str | Fraction) -> int:
    fps_frac = fps if isinstance(fps, Fraction) else Fraction(fps)
    return max(12, int(round(Fraction(STING_FRAMES_30FPS, 30) * fps_frac)))


def localized_sting_subtitle(lang: str | None) -> str:
    if not lang:
        return STING_SUBTITLES["en"]
    clean = lang.strip().lower()
    mapped = ISO3_TO_SHORT_LANG.get(clean, clean.split("-", 1)[0])
    return STING_SUBTITLES.get(mapped, STING_SUBTITLES["en"])


def _validate_mark(raw_mark: Any) -> dict[str, Any]:
    fields(raw_mark, {"preset", "stroke_width", "scale", "shapes"}, set(), "brand.mark")
    normalized: dict[str, Any] = {}
    preset = raw_mark.get("preset", "aperture")
    if not isinstance(preset, str) or preset not in MARK_PRESETS:
        raise ValueError(f"brand.mark.preset: expected one of {sorted(MARK_PRESETS)}")
    normalized["preset"] = preset
    if "stroke_width" in raw_mark:
        number(raw_mark["stroke_width"], 1.0, 12.0, "brand.mark.stroke_width")
        normalized["stroke_width"] = float(raw_mark["stroke_width"])
    else:
        normalized["stroke_width"] = 2.5
    if "scale" in raw_mark:
        number(raw_mark["scale"], 0.5, 2.0, "brand.mark.scale")
        normalized["scale"] = float(raw_mark["scale"])
    else:
        normalized["scale"] = 1.0
    if "shapes" in raw_mark:
        validate_shapes(raw_mark["shapes"])
        if len(raw_mark["shapes"]) > 32:
            raise ValueError("brand.mark.shapes: expected 1..32 entries")
        normalized["shapes"] = copy.deepcopy(raw_mark["shapes"])
    return normalized


def validate_brand_kit(
    raw: dict[str, Any] | BrandKit,
    *,
    min_contrast: float = STING_MIN_WCAG_RATIO,
    project_root: Path | None = None,
) -> BrandKit:
    doc = raw.to_dict() if isinstance(raw, BrandKit) else raw
    fields(
        doc,
        {"schema_version", "name", "background", "foreground", "accent", "font", "logo", "margin", "mark"},
        set(),
        "brand",
    )
    version = doc.get("schema_version", 1)
    if type(version) is not int or version != 1:
        raise ValueError("brand.schema_version: only version 1 is supported")

    name = doc.get("name", "Studio")
    text(name, "brand.name", 80)
    if not name.strip():
        raise ValueError("brand.name: must not be empty")

    bg = str(doc.get("background", STING_GROUND_HEX))
    fg = str(doc.get("foreground", STING_INK_HEX))
    ac = str(doc.get("accent", STING_ACCENT_HEX))
    color(bg, "brand.background")
    color(fg, "brand.foreground")
    color(ac, "brand.accent")

    fg_ratio = contrast_ratio(hex_to_rgb(fg), hex_to_rgb(bg))
    if fg_ratio < min_contrast:
        raise ValueError(
            f"brand contrast ratio {fg_ratio:.2f}:1 between foreground {fg} and background {bg} is below {min_contrast:.1f}:1"
        )
    ac_ratio = contrast_ratio(hex_to_rgb(ac), hex_to_rgb(bg))
    if ac_ratio < 3.0:
        raise ValueError(
            f"brand accent contrast ratio {ac_ratio:.2f}:1 between accent {ac} and background {bg} is below 3.0:1"
        )

    margin = float(doc.get("margin", 0.0))
    number(margin, 0.0, 0.25, "brand.margin")

    font_val = doc.get("font")
    if font_val is not None:
        asset_path(font_val, "brand.font")
        if project_root is not None:
            contained_path(project_root, font_val, must_exist=True)

    logo_val = doc.get("logo")
    if logo_val is not None:
        asset_path(logo_val, "brand.logo")
        if project_root is not None:
            contained_path(project_root, logo_val, must_exist=True)

    mark_val = _validate_mark(doc["mark"]) if doc.get("mark") is not None else None

    return BrandKit(
        schema_version=1,
        name=name.strip(),
        background=bg.lower(),
        foreground=fg.lower(),
        accent=ac.lower(),
        font=font_val,
        logo=logo_val,
        margin=margin,
        mark=mark_val,
    )


def load_brand_kit(
    path: Path | str,
    *,
    project_root: Path | None = None,
    min_contrast: float = STING_MIN_WCAG_RATIO,
) -> BrandKit:
    target = Path(path)
    is_rooted = target.is_absolute() or bool(target.drive) or bool(target.root)
    if project_root is not None and not is_rooted:
        rel_str = path.as_posix() if isinstance(path, Path) else path
        resolved = contained_path(project_root, rel_str, must_exist=True)
    else:
        if target.is_symlink():
            raise ValueError("Brand kit path cannot be a symbolic link")
        resolved = target.resolve(strict=True)
    raw = read_json(resolved, max_bytes=65_536)
    return validate_brand_kit(raw, min_contrast=min_contrast, project_root=project_root)


def init_brand_kit(
    target: Path | str,
    *,
    name: str = "Studio",
    background: str = STING_GROUND_HEX,
    foreground: str = STING_INK_HEX,
    accent: str = STING_ACCENT_HEX,
    font: str | None = None,
    logo: str | None = None,
    margin: float = 0.0,
    mark: dict[str, Any] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    dest = Path(target).expanduser().absolute()
    if dest.is_symlink():
        raise ValueError("Refusing to write brand kit through a symbolic link")
    if dest.suffix.lower() != ".json":
        dest = dest / "brand.json"
    if dest.is_symlink():
        raise ValueError("Refusing to write brand kit through a symbolic link")
    if dest.exists() and not force:
        raise ValueError(f"Brand kit already exists: {dest} (pass --force to overwrite)")
    kit = validate_brand_kit(
        BrandKit(
            schema_version=1,
            name=name,
            background=background,
            foreground=foreground,
            accent=accent,
            font=font,
            logo=logo,
            margin=margin,
            mark=mark or {"preset": "aperture", "stroke_width": 2.5, "scale": 1.0},
        )
    )
    atomic_json(dest, kit.to_dict())
    fg_ratio = round(contrast_ratio(hex_to_rgb(kit.foreground), hex_to_rgb(kit.background)), 2)
    ac_ratio = round(contrast_ratio(hex_to_rgb(kit.accent), hex_to_rgb(kit.background)), 2)
    return {
        "path": str(dest),
        "valid": True,
        "brand_kit": kit.to_dict(),
        "contrast": {"foreground_ratio": fg_ratio, "accent_ratio": ac_ratio},
    }


def apply_brand_kit(
    plan: dict[str, Any],
    brand_kit: dict[str, Any] | BrandKit | Path | str,
    *,
    project_root: Path | None = None,
    min_contrast: float = STING_MIN_WCAG_RATIO,
) -> dict[str, Any]:
    if isinstance(brand_kit, (Path, str)):
        kit = load_brand_kit(brand_kit, project_root=project_root, min_contrast=min_contrast)
    else:
        kit = validate_brand_kit(brand_kit, min_contrast=min_contrast, project_root=project_root)

    updated = copy.deepcopy(plan)
    for scene in updated["scenes"]:
        if scene.get("recipe") == "brand-sting":
            continue
        params = dict(scene.get("params", {}))
        params["background"] = kit.background
        if scene.get("recipe") not in {"footage", "layer-stack", "shape-field"}:
            params["foreground"] = kit.foreground
            params["accent"] = kit.accent
        scene["params"] = params

    delivery = dict(updated.get("delivery", {}))
    if kit.font is not None:
        delivery["font"] = kit.font
    if kit.logo is not None:
        delivery["logo"] = kit.logo
    if kit.margin > 0.0:
        delivery["margin"] = kit.margin
    elif "margin" in delivery and kit.margin == 0.0:
        delivery.pop("margin", None)
    if delivery:
        updated["delivery"] = delivery

    validate(updated)
    return updated


def apply_brand_kit_to_project(
    project_dir: Path | str,
    brand_path: Path | str,
    *,
    min_contrast: float = STING_MIN_WCAG_RATIO,
) -> dict[str, Any]:
    from .render import check_locks

    root, plan, _ = load(project_dir)
    updated = apply_brand_kit(plan, brand_path, project_root=root, min_contrast=min_contrast)
    check_locks(root, updated)
    atomic_json(contained_path(root, "reel.json"), updated)
    meta = validate(updated)
    return {"project": str(root), "applied": True, **meta}


def is_loop_preserving(plan: dict[str, Any], *, format_id: str | None = None, loop: bool = False) -> bool:
    if loop:
        return True
    if format_id == "loop-art":
        return True
    return False


def append_closing_sting(
    plan: dict[str, Any],
    *,
    attribution: bool,
    video_lang: str | None = None,
    format_id: str | None = None,
    loop: bool = False,
) -> dict[str, Any]:
    updated = copy.deepcopy(plan)
    if not attribution:
        return updated

    if is_loop_preserving(updated, format_id=format_id, loop=loop):
        updated["delivery"] = {**updated.get("delivery", {}), "attribution": "metadata-only-loop"}
        validate(updated)
        return updated

    existing_ids = {str(s["id"]) for s in updated["scenes"]}
    sting_id = "brand-sting"
    suffix = 2
    while sting_id in existing_ids:
        sting_id = f"brand-sting-{suffix}"
        suffix += 1

    fps_str = str(updated["output"]["fps"])
    fps_frac = Fraction(fps_str)
    fps_float = float(fps_frac)
    start_frame = sum(int(s["duration_frames"]) for s in updated["scenes"])
    dur = sting_duration_frames(fps_frac)
    lang_hint = video_lang or str(updated.get("delivery", {}).get("language", "eng"))
    subtitle = localized_sting_subtitle(lang_hint)
    trans_frames = min(8, max(1, dur // 4))

    sting_scene: dict[str, Any] = {
        "id": sting_id,
        "duration_frames": dur,
        "recipe": "brand-sting",
        "engine": "pillow",
        "transition": {"type": "cross_dissolve", "duration_frames": trans_frames},
        "params": {
            "background": STING_GROUND_HEX,
            "foreground": STING_INK_HEX,
            "accent": STING_ACCENT_HEX,
            "heading": "Remirdy",
            "subheading": subtitle,
        },
    }
    updated["scenes"].append(sting_scene)
    updated["delivery"] = {**updated.get("delivery", {}), "attribution": "remirdy-sting-v1"}

    total_after = start_frame + dur
    quality = dict(updated.get("quality", {}))
    exceptions = {k: [list(pair) for pair in v] for k, v in quality.get("exceptions", {}).items()}
    exceptions.setdefault("freeze", []).append([start_frame, total_after])

    audio = updated["audio"]
    constraints = updated.get("constraints", {})
    chime_end = start_frame
    if audio["enabled"] and not constraints.get("no_audio") and not constraints.get("no_music"):
        chime_frames = max(6, min(dur, int(round(0.38 * fps_float))))
        gain_offset = max(-24.0, min(6.0, round(-18.0 - float(audio["gain_db"]), 3)))
        audio["cues"].append({
            "frame": start_frame,
            "frequency": 440,
            "duration_frames": chime_frames,
            "instrument": "warm_pad",
            "gain_offset_db": gain_offset,
        })
        chime_end = start_frame + chime_frames
    if audio["enabled"] and chime_end < total_after:
        exceptions.setdefault("silence", []).append([chime_end, total_after])

    updated["quality"] = {"exceptions": exceptions}
    validate(updated)
    return updated


def _fit_centered_font(canvas: Any, value: str, max_w: float, start_pt: float, min_pt: float, *, bold: bool, track_px: float) -> Any:
    pt = float(start_pt)
    while pt > min_pt:
        font = resolve_font(round(pt), bold=bold)
        tw, _ = measure_tracked_text(canvas, value, font, tracking_px=track_px)
        if tw <= max_w:
            return font
        pt *= 0.9
    return resolve_font(round(min_pt), bold=bold)


def _draw_aperture_mark(
    base_image: Any,
    cx: float,
    cy: float,
    radius: float,
    unit: float,
    reveal_u: float,
    foreground: str,
    accent: str,
    scale: int,
) -> None:
    from PIL import Image, ImageDraw

    ss = 2 if scale < 2 else 1
    half = max(16, int(math.ceil(radius * 1.45)))
    tile_w = half * 2
    tile = Image.new("RGBA", (tile_w * ss, tile_w * ss), (0, 0, 0, 0))
    td = ImageDraw.Draw(tile)
    tcx, tcy = half * ss, half * ss
    tr = radius * ss
    stroke_w = max(2, round(2.6 * unit * ss))
    blade_w = max(2, round(2.0 * unit * ss))

    rot = (1.0 - reveal_u) * 0.28
    ring_scale = 0.65 + 0.35 * reveal_u
    hex_pts = [
        (
            tcx + tr * ring_scale * math.cos(k * math.tau / 6.0 - math.pi / 6.0 + rot),
            tcy + tr * ring_scale * math.sin(k * math.tau / 6.0 - math.pi / 6.0 + rot),
        )
        for k in range(6)
    ]
    ac_rgb = hex_to_rgb(accent)
    fg_rgb = hex_to_rgb(foreground)
    alpha_byte = max(0, min(255, round(255 * (0.25 + 0.75 * reveal_u))))
    ac_rgba = (*ac_rgb, alpha_byte)
    fg_rgba = (*fg_rgb, alpha_byte)

    td.line([*hex_pts, hex_pts[0]], fill=ac_rgba, width=stroke_w, joint="curve")
    inner_r = tr * 0.56 * ring_scale
    td.ellipse((tcx - inner_r, tcy - inner_r, tcx + inner_r, tcy + inner_r), outline=fg_rgba, width=blade_w)

    blade_reach = max(0.05, reveal_u)
    outer_ring = tr * 0.78 * ring_scale
    core_ring = tr * (0.24 + 0.08 * reveal_u)
    for k in range(6):
        a0 = k * math.tau / 6.0 + rot
        a1 = a0 + 0.85 * blade_reach
        p0 = (tcx + outer_ring * math.cos(a0), tcy + outer_ring * math.sin(a0))
        p1 = (tcx + core_ring * math.cos(a1), tcy + core_ring * math.sin(a1))
        td.line((p0, p1), fill=fg_rgba, width=blade_w)

    if ss > 1:
        tile = tile.resize((tile_w, tile_w), Image.Resampling.LANCZOS)
    px = int(round(cx - half))
    py = int(round(cy - half))
    base_rgba = base_image.convert("RGBA")
    base_rgba.paste(tile, (px, py), tile)
    base_image.paste(base_rgba.convert("RGB"))


def render_brand_sting_frame(
    scene: dict[str, Any],
    frame: int,
    w: int,
    h: int,
    fps_val: float,
    scale: int = 1,
    reduced_motion: bool = False,
) -> tuple[Any, list[dict[str, Any]]]:
    from PIL import Image, ImageDraw

    params = scene.get("params", {})
    background = str(params.get("background", STING_GROUND_HEX))
    foreground = str(params.get("foreground", STING_INK_HEX))
    accent = str(params.get("accent", STING_ACCENT_HEX))
    heading = str(params.get("heading", "Remirdy"))
    subheading = str(params.get("subheading", STING_SUBTITLES["en"]))

    unit = min(w / 960.0, h / 540.0)
    reveal_frames = max(1, int(round(STING_REVEAL_FRAMES_30FPS * fps_val / 30.0)))
    fade_frames = max(1, int(round(STING_REDUCED_FADE_FRAMES_30FPS * fps_val / 30.0)))

    if reduced_motion:
        reveal_u = 1.0
        opacity_u = smooth(min(1.0, frame / float(fade_frames)))
    else:
        reveal_u = ease("cubic_out", min(1.0, frame / float(reveal_frames)))
        opacity_u = smooth(min(1.0, frame / float(max(1, reveal_frames // 2))))

    image = Image.new("RGB", (w, h), background)
    canvas = ImageDraw.Draw(image)

    mark_r = min(w, h) * 0.088
    mark_cy = h * 0.37
    _draw_aperture_mark(image, w * 0.5, mark_cy, mark_r, unit, reveal_u, foreground, accent, scale)

    bounds: list[dict[str, Any]] = []
    max_text_w = w * 0.72
    y_offset = (0.0 if reduced_motion else (1.0 - reveal_u) * 8.0 * unit)

    if heading:
        h_track = 1.4 * unit
        h_font = _fit_centered_font(canvas, heading, max_text_w, 42.0 * unit, 12.0 * unit, bold=True, track_px=h_track)
        hw, hh = measure_tracked_text(canvas, heading, h_font, tracking_px=h_track)
        hx = (w - hw) * 0.5
        hy = h * 0.50 + y_offset
        h_box = draw_tracked_text(canvas, (hx, hy), heading, h_font, foreground, tracking_px=h_track)
        bounds.append({"field": "heading", "bounds": [round(v / scale, 3) for v in h_box]})

    if subheading:
        s_track = 0.6 * unit
        s_font = _fit_centered_font(canvas, subheading, max_text_w, 17.0 * unit, 9.0 * unit, bold=False, track_px=s_track)
        sw, _ = measure_tracked_text(canvas, subheading, s_font, tracking_px=s_track)
        sx = (w - sw) * 0.5
        sy = h * 0.585 + y_offset
        sub_color = STING_SUBTITLE_HEX
        if contrast_ratio(hex_to_rgb(sub_color), hex_to_rgb(background)) < STING_MIN_WCAG_RATIO:
            sub_color = rgb_to_hex(mix_oklab(foreground, background, 0.25))
        s_box = draw_tracked_text(canvas, (sx, sy), subheading, s_font, sub_color, tracking_px=s_track)
        bounds.append({"field": "subheading", "bounds": [round(v / scale, 3) for v in s_box]})

    if opacity_u < 1.0:
        ground = Image.new("RGB", (w, h), background)
        image = Image.blend(ground, image, opacity_u)

    return image, bounds
