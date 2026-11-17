import math

NORMAL = {'type': 'number', 'minimum': 0, 'maximum': 1}
LENGTH = {**NORMAL, 'exclusiveMinimum': 0}
COLOR = {'type': 'string', 'pattern': '^#[0-9a-fA-F]{6}$'}
ANGLE = {'type': 'number', 'minimum': -360, 'maximum': 360}
POINT = {'type': 'array', 'items': NORMAL, 'minItems': 2, 'maxItems': 2}
STYLE = {
    'fill': COLOR,
    'stroke': COLOR,
    'stroke_width': {'type': 'number', 'exclusiveMinimum': 0, 'maximum': 64},
}
CENTER = {'cx': NORMAL, 'cy': NORMAL, 'r': LENGTH}
BOX = {'x': NORMAL, 'y': NORMAL, 'w': LENGTH, 'h': LENGTH}
POINTS = {'points': {'type': 'array', 'minItems': 2, 'maxItems': 128, 'items': POINT}}
GRID = {**BOX, **{k: {'type': 'integer', 'minimum': 2, 'maximum': 48} for k in ('rows', 'columns')}}
SHAPES = {
    'circle': CENTER,
    'ellipse': BOX,
    'rect': BOX,
    'rounded_rect': {**BOX, 'radius': LENGTH},
    'arc': {**CENTER, 'start_deg': ANGLE, 'sweep_deg': ANGLE},
    'pie': {**CENTER, 'start_deg': ANGLE, 'sweep_deg': ANGLE},
    'regular_polygon': {**CENTER, 'sides': {'type': 'integer', 'minimum': 3, 'maximum': 64}},
    'star': {**CENTER, 'sides': {'type': 'integer', 'minimum': 3, 'maximum': 32}},
    'path': POINTS,
    'ribbon': POINTS,
    'bezier': {'points': {**POINTS['points'], 'minItems': 4, 'maxItems': 4}},
    'arrow': {'points': {**POINTS['points'], 'minItems': 2, 'maxItems': 2}},
    'connector': POINTS,
    'grid': GRID,
    'dot_lattice': GRID,
    'mask': {**CENTER},
}


def shape_schema(kind):
    geometry = SHAPES[kind]
    properties = {'type': {'const': kind}, **geometry, **STYLE}
    if kind in ('regular_polygon', 'star'):
        properties['rotate_deg'] = ANGLE
    return {
        'type': 'object',
        'properties': properties,
        'required': ['type', *geometry],
        'additionalProperties': False,
    }


def validate_shapes(shapes):
    from .project import color, fields, integer, number

    def check(value, rule, key):
        if rule['type'] == 'array':
            if not isinstance(value, list) or not rule['minItems'] <= len(value) <= rule['maxItems']:
                raise ValueError(f'{key}: invalid point count')
            for item in value:
                check(item, rule['items'], key)
        elif rule['type'] == 'string':
            color(value, key)
        else:
            validator = integer if rule['type'] == 'integer' else number
            validator(value, rule.get('minimum', 0), rule['maximum'], key)
            if 'exclusiveMinimum' in rule and value <= rule['exclusiveMinimum']:
                raise ValueError(f'{key}: expected a positive length')

    if not isinstance(shapes, list) or not 1 <= len(shapes) <= 128:
        raise ValueError('shapes: expected 1–128 entries')
    for shape in shapes:
        if (
            not isinstance(shape, dict)
            or not isinstance(shape.get('type'), str)
            or shape['type'] not in SHAPES
        ):
            raise ValueError('shapes: unsupported primitive')
        schema = shape_schema(shape['type'])
        fields(shape, schema['properties'], schema['required'], 'shape')
        for key in shape.keys() - {'type'}:
            check(shape[key], schema['properties'][key], key)


def paint_shapes(image, shapes, background, regions, original_size, frame=0, fps=30):
    from PIL import Image, ImageDraw

    width, height = image.size
    unit = min(width, height)
    draw = ImageDraw.Draw(image)
    for shape in shapes:
        kind = shape['type']
        stroke = shape.get('stroke')
        fill = shape.get('fill', None if stroke else '#252925')
        line = stroke or fill
        pen = max(1, round(shape.get('stroke_width', 2) * min(width / 960, height / 540)))
        if 'cx' in shape:
            x, y, radius = shape['cx'] * width, shape['cy'] * height, shape['r'] * unit
            box = (x - radius, y - radius, x + radius, y + radius)
        elif 'w' in shape:
            x, y = shape['x'] * width, shape['y'] * height
            dx, dy = shape['w'] * width, shape['h'] * height
            box = (x, y, x + dx, y + dy)
        else:
            points = [(a * width, b * height) for a, b in shape['points']]
        if kind == 'mask':
            alpha = Image.new('L', image.size)
            ImageDraw.Draw(alpha).ellipse(box, fill=255)
            image.paste(Image.composite(image, Image.new(image.mode, image.size, background), alpha))
        elif kind in ('circle', 'ellipse', 'rect', 'rounded_rect'):
            if kind == 'rounded_rect':
                draw.rounded_rectangle(
                    box, radius=shape['radius'] * unit, fill=fill, outline=stroke, width=pen
                )
            else:
                primitive = draw.rectangle if kind == 'rect' else draw.ellipse
                primitive(box, fill=fill, outline=stroke, width=pen)
        elif kind in ('arc', 'pie'):
            start, end = sorted((shape['start_deg'], shape['start_deg'] + shape['sweep_deg']))
            if kind == 'arc':
                draw.arc(box, start, end, fill=line, width=pen)
            else:
                draw.pieslice(box, start, end, fill=fill, outline=stroke, width=pen)
        elif kind in ('regular_polygon', 'star'):
            count = shape['sides'] * (2 if kind == 'star' else 1)
            vertices = []
            for i in range(count):
                angle = math.tau * i / count + math.radians(shape.get('rotate_deg', -90))
                r = radius * (0.45 if kind == 'star' and i % 2 else 1)
                vertices.append((x + r * math.cos(angle), y + r * math.sin(angle)))
            draw.polygon(vertices, fill=fill, outline=stroke, width=pen)
        elif kind in ('grid', 'dot_lattice'):
            xs = [x + dx * i / (shape['columns'] - 1) for i in range(shape['columns'])]
            ys = [y + dy * j / (shape['rows'] - 1) for j in range(shape['rows'])]
            for px in xs:
                if kind == 'grid':
                    draw.line((px, y, px, y + dy), fill=line, width=pen)
                else:
                    for py in ys:
                        draw.ellipse((px - pen, py - pen, px + pen, py + pen), fill=line)
            if kind == 'grid':
                for py in ys:
                    draw.line((x, py, x + dx, py), fill=line, width=pen)
        else:
            if kind == 'bezier':
                curve = []
                for i in range(65):
                    t = i / 64
                    weights = ((1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t * t * (1 - t), t**3)
                    curve.append(tuple(sum(p[axis] * w for p, w in zip(points, weights)) for axis in (0, 1)))
                points = curve
            if kind == 'ribbon':
                from .motion import verlet_ribbon

                def anchor(t):
                    position = min(len(points) - 1, max(0, t * fps / 120 * (len(points) - 1)))
                    i = min(int(position), len(points) - 2)
                    return tuple(
                        points[i][axis] + (points[i + 1][axis] - points[i][axis]) * (position - i)
                        for axis in (0, 1)
                    )

                points = verlet_ribbon(
                    anchor,
                    8,
                    unit * 0.018,
                    min(frame, 120),
                    fps,
                    substeps=2,
                    iterations=3,
                    gravity=unit * 0.4,
                )
            draw.line(points, fill=line, width=pen if kind != 'ribbon' else 4 * pen, joint='curve')
            if kind == 'arrow':
                (a, b), (c, d) = points
                angle = math.atan2(d - b, c - a)
                ends = [
                    (c - 5 * pen * math.cos(angle + v), d - 5 * pen * math.sin(angle + v))
                    for v in (-0.5, 0.5)
                ]
                draw.polygon([(c, d), *ends], fill=line)
    for x, y, w, h in regions:
        sx, sy = width / original_size[0], height / original_size[1]
        tile = image.crop((int(x * sx), int(y * sy), math.ceil((x + w) * sx), math.ceil((y + h) * sy)))
        if tile.getextrema() != Image.new('RGB', (1, 1), background).getextrema():
            raise ValueError('Shape overlaps a locked region')
