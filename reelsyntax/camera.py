import math
from .motion import spring_damper


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(v):
    length = math.sqrt(_dot(v, v)) or 1.0
    return (v[0] / length, v[1] / length, v[2] / length)


class Camera3D:
    def __init__(
        self,
        position: tuple[float, float, float] = (0.0, -4.2, 1.35),
        target: tuple[float, float, float] = (0.0, 0.0, 0.25),
        focal_mm: float = 50.0,
        sensor_width_mm: float = 36.0,
        up: tuple[float, float, float] = (0.0, 0.0, 1.0),
    ):
        self.position = position
        self.target = target
        self.focal_mm = max(12.0, min(200.0, float(focal_mm)))
        self.sensor_width_mm = float(sensor_width_mm)
        self.forward = _norm(_sub(target, position))
        right_raw = _cross(self.forward, up)
        if _dot(right_raw, right_raw) < 1e-8:
            right_raw = (1.0, 0.0, 0.0)
        self.right = _norm(right_raw)
        self.up = _cross(self.right, self.forward)

    @classmethod
    def from_scene(cls, scene: dict, frame: int, fps: float, seed: int, camera_locked: bool = False):
        cfg = scene.get('camera') or {}
        preset = cfg.get('preset', 'locked')
        if camera_locked and preset != 'locked':
            raise ValueError(f"Scene '{scene['id']}' requests camera preset '{preset}' while camera_locked constraint is active")
        t = frame / max(1.0, float(fps))
        u = frame / max(1, scene['duration_frames'] - 1)
        s_crit = spring_damper(t, zeta=1.0, omega=2.4)
        base_pos = tuple(cfg.get('position', (1.9, -4.1, 1.45)))
        base_tgt = tuple(cfg.get('target', (0.0, 0.0, 0.2)))
        focal = float(cfg.get('focal_mm', 52.0))

        if preset == 'locked':
            return cls(position=base_pos, target=base_tgt, focal_mm=focal)
        if preset == 'dolly_in':
            factor = 1.0 - 0.18 * s_crit
            pos = (base_pos[0] * factor, base_pos[1] * factor, base_pos[2] * (1.0 - 0.08 * s_crit))
            return cls(position=pos, target=base_tgt, focal_mm=focal)
        if preset == 'orbit':
            angle = -0.32 + 0.64 * s_crit
            radius = math.hypot(base_pos[0], base_pos[1])
            pos = (radius * math.sin(angle), -radius * math.cos(angle), base_pos[2] + 0.12 * math.sin(u * math.pi))
            return cls(position=pos, target=base_tgt, focal_mm=focal)
        if preset == 'crane_rise':
            pos = (base_pos[0], base_pos[1] * (1.0 - 0.08 * s_crit), base_pos[2] - 0.45 + 0.9 * s_crit)
            return cls(position=pos, target=base_tgt, focal_mm=focal)
        if preset == 'dolly_zoom':
            f0 = focal
            f_now = f0 * (0.68 + 0.64 * s_crit)
            dist0 = math.sqrt(sum((a - b) ** 2 for a, b in zip(base_pos, base_tgt)))
            dist_now = dist0 * (f_now / f0)
            dir_vec = _norm(_sub(base_pos, base_tgt))
            pos = tuple(base_tgt[i] + dir_vec[i] * dist_now for i in range(3))
            return cls(position=pos, target=base_tgt, focal_mm=f_now)
        raise ValueError(f'Unsupported camera preset: {preset}')

    def project(self, point: tuple[float, float, float], width: int, height: int) -> tuple[float, float, float] | None:
        rel = _sub(point, self.position)
        depth = _dot(rel, self.forward)
        if depth <= 0.08:
            return None
        px = _dot(rel, self.right)
        py = _dot(rel, self.up)
        scale = width * (self.focal_mm / self.sensor_width_mm) / depth
        sx = width * 0.72 + px * scale
        sy = height * 0.48 - py * scale
        return (sx, sy, depth)
