import math


def blend(previous, incoming, kind, progress):
    from PIL import Image, ImageDraw

    if progress <= 0:
        return previous.copy()
    if progress >= 1:
        return incoming.copy()
    width, height = previous.size
    distance = round(width * progress)
    if kind == 'cross_dissolve':
        return Image.blend(previous, incoming, progress)
    if kind in ('fade_black', 'fade_white'):
        middle = Image.new('RGB', previous.size, 'white' if kind == 'fade_white' else 'black')
        if progress < 0.5:
            return Image.blend(previous, middle, progress * 2)
        return Image.blend(middle, incoming, progress * 2 - 1)
    result = previous.copy()
    if kind == 'wipe_left':
        result.paste(incoming.crop((0, 0, distance, height)), (0, 0))
    elif kind in ('slide_left', 'slide_right'):
        direction = -1 if kind == 'slide_left' else 1
        result.paste(previous, (direction * distance, 0))
        result.paste(incoming, (direction * (distance - width), 0))
    elif kind == 'radial':
        mask = Image.new('L', previous.size)
        radius = math.hypot(width, height) * progress / 2
        ImageDraw.Draw(mask).ellipse(
            (width / 2 - radius, height / 2 - radius, width / 2 + radius, height / 2 + radius), fill=255
        )
        result.paste(incoming, mask=mask)
    elif kind == 'glitch':
        for i in range(16):
            start = height * i // 16
            stop = height * (i + 1) // 16
            span = min(width, max(0, round(distance + width * 0.18 * math.sin((i + 1) * 7 + progress * 9))))
            result.paste(incoming.crop((0, start, span, stop)), (0, start))
    else:
        raise ValueError(f'Unsupported transition {kind}')
    return result
