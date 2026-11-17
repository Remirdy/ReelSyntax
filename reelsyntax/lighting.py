import math
from .palette import agx_tonemap_linear, hex_to_linear, linear_to_rgb8


def _sub3(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross3(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm3(v):
    m = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]) or 1.0
    return (v[0] / m, v[1] / m, v[2] / m)


def _dot3(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _rot_z(pt, angle):
    c, s = math.cos(angle), math.sin(angle)
    return (pt[0] * c - pt[1] * s, pt[0] * s + pt[1] * c, pt[2])


def _rot_x(pt, angle):
    c, s = math.cos(angle), math.sin(angle)
    return (pt[0], pt[1] * c - pt[2] * s, pt[1] * s + pt[2] * c)


def _box_faces(cx, cy, cz, sx, sy, sz, yaw=0.0, pitch=0.0, mat='primary'):
    hx, hy, hz = sx * 0.5, sy * 0.5, sz * 0.5
    verts = [
        (-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
        (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz),
    ]
    transformed = []
    for v in verts:
        r = _rot_z(_rot_x(v, pitch), yaw)
        transformed.append((r[0] + cx, r[1] + cy, r[2] + cz))
    quads = [
        (0, 1, 5, 4),
        (1, 2, 6, 5),
        (2, 3, 7, 6),
        (3, 0, 4, 7),
        (4, 5, 6, 7),
        (3, 2, 1, 0),
    ]
    return [([transformed[i] for i in q], mat) for q in quads]


def build_monolith_assembly(progress: float, seed: int) -> list[tuple[list[tuple[float, float, float]], str]]:
    faces = []
    faces.extend(_box_faces(0.0, 0.0, -0.66, 1.68, 1.68, 0.12, yaw=0.24, mat='plinth'))
    for idx in range(4):
        phase = progress * math.tau + idx * 0.85 + (seed % 17) * 0.05
        lift = -0.34 + idx * 0.31 + 0.04 * math.sin(phase)
        yaw = 0.28 + idx * 0.19 + 0.24 * math.sin(progress * math.pi + idx * 0.4)
        width = 1.08 - idx * 0.14
        depth = 0.74 - idx * 0.07
        mat = 'accent' if idx == 2 else 'primary'
        faces.extend(_box_faces(0.0, 0.0, lift, width, depth, 0.22, yaw=yaw, pitch=0.04 * math.cos(phase), mat=mat))
    orbit_ang = -0.55 + 0.95 * math.sin(progress * math.pi)
    ox, oy = 0.92 * math.cos(orbit_ang), 0.92 * math.sin(orbit_ang)
    faces.extend(_box_faces(ox, oy, 0.26 + 0.10 * math.sin(progress * math.tau), 0.18, 0.18, 0.68, yaw=orbit_ang, mat='accent'))
    return faces


def shade_facet_three_point(
    verts: list[tuple[float, float, float]],
    view_pos: tuple[float, float, float],
    albedo_hex: str,
    accent_hex: str,
    look_mode: str = 'agx',
    dither: float = 0.0,
) -> tuple[int, int, int]:
    e1 = _sub3(verts[1], verts[0])
    e2 = _sub3(verts[2], verts[0])
    normal = _norm3(_cross3(e1, e2))
    centroid = tuple(sum(v[i] for v in verts) / len(verts) for i in range(3))
    view_dir = _norm3(_sub3(view_pos, centroid))
    if _dot3(normal, view_dir) < 0:
        normal = (-normal[0], -normal[1], -normal[2])

    albedo = hex_to_linear(albedo_hex)
    rim_tint = hex_to_linear(accent_hex)

    key_dir = _norm3((0.62, -0.58, 0.74))
    fill_dir = _norm3((-0.75, -0.35, 0.32))
    rim_dir = _norm3((-0.22, 0.86, 0.46))

    ndotl_key = max(0.0, _dot3(normal, key_dir))
    ndotl_fill = max(0.0, _dot3(normal, fill_dir))
    ndotl_rim = max(0.0, _dot3(normal, rim_dir))

    half_key = _norm3((key_dir[0] + view_dir[0], key_dir[1] + view_dir[1], key_dir[2] + view_dir[2]))
    spec = max(0.0, _dot3(normal, half_key)) ** 42
    fresnel = (1.0 - max(0.0, _dot3(normal, view_dir))) ** 3

    hemi = 0.16 + 0.08 * (normal[2] * 0.5 + 0.5)
    lin = []
    for ch in range(3):
        diffuse = albedo[ch] * (hemi + 1.55 * ndotl_key + 0.42 * ndotl_fill * (0.85 if ch < 2 else 1.08))
        specular = (0.38 * spec) * (0.95 + 0.1 * rim_tint[ch])
        rim = (0.48 * ndotl_rim * (0.35 + 0.65 * fresnel)) * (0.45 + 0.55 * rim_tint[ch])
        lin.append(diffuse + specular + rim)

    if look_mode == 'neutral':
        clamped = tuple(max(0.0, min(1.0, c / (1.0 + c))) for c in lin)
        return linear_to_rgb8(clamped, dither=0.0)
    mapped = agx_tonemap_linear(tuple(lin), exposure=1.05, punch=1.10)
    return linear_to_rgb8(mapped, dither=dither)
