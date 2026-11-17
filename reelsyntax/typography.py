from pathlib import Path
import sys


SYSTEM_SANS_CANDIDATES = {
    'darwin': (
        '/System/Library/Fonts/HelveticaNeue.ttc',
        '/System/Library/Fonts/Helvetica.ttc',
        '/System/Library/Fonts/Supplemental/Arial.ttf',
    ),
    'win32': (
        'C:/Windows/Fonts/segoeui.ttf',
        'C:/Windows/Fonts/arial.ttf',
    ),
    'linux': (
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf',
        '/usr/share/fonts/TTF/DejaVuSans.ttf',
    ),
}

SYSTEM_BOLD_CANDIDATES = {
    'darwin': (
        '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
        '/System/Library/Fonts/HelveticaNeue.ttc',
    ),
    'win32': (
        'C:/Windows/Fonts/segoeuib.ttf',
        'C:/Windows/Fonts/arialbd.ttf',
    ),
    'linux': (
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf',
    ),
}


def resolve_font(size: int, bold: bool = False, font_path: str | Path | None = None, prefer_default: bool = False):
    from PIL import ImageFont
    px = max(8 if prefer_default else 4, int(round(size)))
    if prefer_default:
        return ImageFont.load_default(size=px)
    if font_path:
        p = Path(font_path)
        if not p.is_file():
            raise ValueError(f'Configured font file does not exist: {font_path}')
        return ImageFont.truetype(str(p), px)
    plat = 'darwin' if sys.platform == 'darwin' else ('win32' if sys.platform == 'win32' else 'linux')
    table = SYSTEM_BOLD_CANDIDATES if bold else SYSTEM_SANS_CANDIDATES
    for candidate in table.get(plat, ()):
        if Path(candidate).is_file():
            try:
                return ImageFont.truetype(candidate, px)
            except OSError:
                continue
    return ImageFont.load_default(size=px)


def check_glyph_coverage(text: str, font) -> dict:
    from PIL import Image, ImageDraw
    if not text:
        return {'ok': True, 'missing_chars': []}

    def render_glyph(ch: str) -> bytes:
        img = Image.new('L', (64, 64), 0)
        d = ImageDraw.Draw(img)
        d.text((8, 8), ch, fill=255, font=font)
        return img.tobytes()

    notdef_signatures = {render_glyph('\uffff'), render_glyph('\U0010ffff')}
    empty_sig = bytes(64 * 64)
    missing = []
    for ch in dict.fromkeys(text):
        if ch.isspace():
            continue
        sig = render_glyph(ch)
        if sig == empty_sig or sig in notdef_signatures:
            missing.append(ch)
    return {'ok': len(missing) == 0, 'missing_chars': missing}


def measure_tracked_text(canvas, text: str, font, tracking_px: float = 0.0) -> tuple[float, float]:
    if not text:
        return (0.0, 0.0)
    if abs(tracking_px) < 1e-3:
        box = canvas.textbbox((0, 0), text, font=font)
        return (float(box[2] - box[0]), float(box[3] - box[1]))
    width = 0.0
    height = 0.0
    for idx, ch in enumerate(text):
        adv = canvas.textlength(ch, font=font)
        width += adv + (tracking_px if idx + 1 < len(text) else 0.0)
        box = canvas.textbbox((0, 0), ch, font=font)
        height = max(height, float(box[3] - box[1]))
    return (width, height)


def draw_tracked_text(canvas, xy: tuple[float, float], text: str, font, fill, tracking_px: float = 0.0) -> list[float]:
    x0, y0 = xy
    if not text:
        return [x0, y0, x0, y0]
    if abs(tracking_px) < 1e-3:
        box = canvas.textbbox((x0, y0), text, font=font)
        canvas.text((x0, y0), text, fill=fill, font=font)
        return [float(box[0]), float(box[1]), float(box[2]), float(box[3])]
    cursor = float(x0)
    top, bottom = float('inf'), float('-inf')
    for idx, ch in enumerate(text):
        box = canvas.textbbox((cursor, y0), ch, font=font)
        top = min(top, float(box[1]))
        bottom = max(bottom, float(box[3]))
        canvas.text((cursor, y0), ch, fill=fill, font=font)
        cursor += canvas.textlength(ch, font=font) + (tracking_px if idx + 1 < len(text) else 0.0)
    if top == float('inf'):
        top, bottom = y0, y0
    return [float(x0), top, cursor, bottom]
