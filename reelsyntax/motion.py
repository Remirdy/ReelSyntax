import math


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def smooth(value: float) -> float:
    u = clamp01(value)
    return u * u * (3.0 - 2.0 * u)


def ease(mode: str, value: float) -> float:
    u = clamp01(value)
    if mode == 'linear':
        return u
    if mode == 'expo_out':
        return 1.0 if u >= 1.0 else 1.0 - 2.0 ** (-10.0 * u)
    if mode == 'quint_in_out':
        return 16.0 * (u ** 5) if u < 0.5 else 1.0 - ((-2.0 * u + 2.0) ** 5) / 2.0
    if mode == 'cubic_out':
        return 1.0 - (1.0 - u) ** 3
    if mode == 'back_out':
        c1 = 1.70158
        c3 = c1 + 1.0
        return 1.0 + c3 * ((u - 1.0) ** 3) + c1 * ((u - 1.0) ** 2)
    return smooth(u)


def spring_damper(t: float, zeta: float = 1.0, omega: float = 5.5) -> float:
    t = max(0.0, float(t))
    omega = max(0.05, float(omega))
    zeta = max(0.05, float(zeta))
    if abs(zeta - 1.0) < 1e-4:
        return 1.0 - (1.0 + omega * t) * math.exp(-omega * t)
    if zeta < 1.0:
        wd = omega * math.sqrt(1.0 - zeta * zeta)
        envelope = math.exp(-zeta * omega * t)
        return 1.0 - envelope * (math.cos(wd * t) + (zeta * omega / wd) * math.sin(wd * t))
    s = omega * math.sqrt(zeta * zeta - 1.0)
    r1, r2 = -zeta * omega + s, -zeta * omega - s
    c2 = r1 / (r1 - r2)
    c1 = 1.0 - c2
    return 1.0 - (c1 * math.exp(r1 * t) + c2 * math.exp(r2 * t))


def verlet_ribbon(
    anchor_fn,
    segments: int,
    segment_length: float,
    frame: int,
    fps: float,
    substeps: int = 6,
    iterations: int = 10,
    damping: float = 0.988,
    gravity: float = 180.0,
) -> list[tuple[float, float]]:
    dt = 1.0 / (max(1, substeps) * max(1.0, float(fps)))
    ax0, ay0 = anchor_fn(0.0)
    pos = [[ax0, ay0 + i * segment_length] for i in range(segments + 1)]
    prev = [list(p) for p in pos]
    total_steps = max(0, int(frame)) * max(1, substeps)

    for step in range(1, total_steps + 1):
        t = step * dt
        ax, ay = anchor_fn(t)
        pos[0][0], pos[0][1] = ax, ay
        prev[0][0], prev[0][1] = ax, ay
        for i in range(1, segments + 1):
            vx = (pos[i][0] - prev[i][0]) * damping
            vy = (pos[i][1] - prev[i][1]) * damping
            prev[i][0], prev[i][1] = pos[i][0], pos[i][1]
            pos[i][0] += vx
            pos[i][1] += vy + gravity * dt * dt
        for _ in range(iterations):
            pos[0][0], pos[0][1] = ax, ay
            for i in range(segments):
                dx = pos[i + 1][0] - pos[i][0]
                dy = pos[i + 1][1] - pos[i][1]
                dist = math.hypot(dx, dy) or 1e-6
                diff = (dist - segment_length) / dist
                if i == 0:
                    pos[i + 1][0] -= dx * diff
                    pos[i + 1][1] -= dy * diff
                else:
                    pos[i][0] += dx * 0.5 * diff
                    pos[i][1] += dy * 0.5 * diff
                    pos[i + 1][0] -= dx * 0.5 * diff
                    pos[i + 1][1] -= dy * 0.5 * diff
    return [(p[0], p[1]) for p in pos]
