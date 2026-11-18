from array import array
from fractions import Fraction
import importlib.util
import math
from pathlib import Path
import sys
from typing import Any, Sequence
import wave

from .camera import Camera3D
from .lighting import shade_facet_three_point
from .palette import hex_to_linear, hex_to_rgb, linear_to_rgb8, mix_oklab, oklab_to_linear_rgb, rgb_to_hex
from .typography import resolve_font

EXPRESSIONS = ('neutral', 'focused', 'surprised', 'happy')
MOUTH_LEVELS = (0.0, 0.35, 0.75, 1.0)
SHOT_ROLES = ('establishing', 'speaker_a', 'speaker_b', 'insert', 'two_shot')
CHARACTER_POSITIONS = ('left', 'right', 'center', 'duo')


def oklch_to_linear(luma: float, chroma: float, hue_deg: float) -> tuple[float, float, float]:
    l_val = max(0.0, min(1.0, float(luma)))
    c_val = max(0.0, float(chroma))
    rad = math.radians(float(hue_deg))
    a_val = c_val * math.cos(rad)
    b_val = c_val * math.sin(rad)
    lin = oklab_to_linear_rgb(l_val, a_val, b_val)
    return (max(0.0, min(1.0, lin[0])), max(0.0, min(1.0, lin[1])), max(0.0, min(1.0, lin[2])))


def oklch_to_hex(luma: float, chroma: float, hue_deg: float) -> str:
    return rgb_to_hex(linear_to_rgb8(oklch_to_linear(luma, chroma, hue_deg)))


def palette_from_oklch(spec: dict[str, tuple[float, float, float]]) -> dict[str, str]:
    return {role: oklch_to_hex(*vals) for role, vals in spec.items()}


_PRESET_OKLCH: dict[str, dict[str, Any]] = {
    'scout': {
        'label': 'Scout',
        'head_shape': 'octa_crest',
        'torso_shape': 'collar_rig',
        'default_facing': 'right',
        'blink_period': 105,
        'blink_offset': 19,
        'blink_duration': 4,
        'default_pitch_hz': 260.0,
        'oklch': {
            'primary': (0.72, 0.14, 58.0),
            'secondary': (0.31, 0.04, 240.0),
            'accent': (0.76, 0.13, 196.0),
            'visor': (0.78, 0.12, 198.0),
            'skin': (0.84, 0.05, 72.0),
            'eye': (0.96, 0.01, 95.0),
            'pupil': (0.18, 0.02, 245.0),
            'brow': (0.24, 0.03, 45.0),
            'mouth_dark': (0.19, 0.04, 20.0),
            'mouth_lip': (0.64, 0.14, 34.0),
        },
    },
    'archivist': {
        'label': 'Archivist',
        'head_shape': 'hex_helm',
        'torso_shape': 'mantle_rig',
        'default_facing': 'left',
        'blink_period': 123,
        'blink_offset': 66,
        'blink_duration': 4,
        'default_pitch_hz': 175.0,
        'oklch': {
            'primary': (0.58, 0.11, 214.0),
            'secondary': (0.28, 0.06, 258.0),
            'accent': (0.79, 0.15, 76.0),
            'visor': (0.80, 0.14, 78.0),
            'skin': (0.87, 0.02, 222.0),
            'eye': (0.95, 0.02, 85.0),
            'pupil': (0.18, 0.03, 250.0),
            'brow': (0.22, 0.03, 248.0),
            'mouth_dark': (0.17, 0.03, 250.0),
            'mouth_lip': (0.61, 0.11, 52.0),
        },
    },
    'relay': {
        'label': 'Relay',
        'head_shape': 'prism_visor',
        'torso_shape': 'collar_rig',
        'default_facing': 'center',
        'blink_period': 117,
        'blink_offset': 91,
        'blink_duration': 4,
        'default_pitch_hz': 215.0,
        'oklch': {
            'primary': (0.63, 0.12, 152.0),
            'secondary': (0.29, 0.05, 168.0),
            'accent': (0.82, 0.15, 86.0),
            'visor': (0.83, 0.14, 88.0),
            'skin': (0.88, 0.03, 96.0),
            'eye': (0.96, 0.01, 100.0),
            'pupil': (0.19, 0.02, 220.0),
            'brow': (0.23, 0.03, 175.0),
            'mouth_dark': (0.18, 0.03, 220.0),
            'mouth_lip': (0.66, 0.12, 42.0),
        },
    },
}

CHARACTER_PRESETS: dict[str, dict[str, Any]] = {
    pid: {
        'id': pid,
        **spec,
        'palette': palette_from_oklch(spec['oklch']),
    }
    for pid, spec in _PRESET_OKLCH.items()
}


def list_character_presets() -> tuple[str, ...]:
    return tuple(CHARACTER_PRESETS.keys())


def get_character_preset(name: str) -> dict[str, Any]:
    key = str(name).strip().lower()
    if key not in CHARACTER_PRESETS:
        raise ValueError(f'Unknown character preset {name!r}; expected one of {sorted(CHARACTER_PRESETS)}')
    return CHARACTER_PRESETS[key]


def expression_parameters(expression: str = 'neutral') -> dict[str, float]:
    key = str(expression).strip().lower()
    table = {
        'neutral': {
            'brow_lift': 0.0,
            'brow_tilt': 0.0,
            'eye_scale_y': 1.0,
            'pupil_scale': 1.0,
            'mouth_base_open': 0.0,
            'mouth_smile': 0.0,
            'head_pitch_deg': 0.0,
        },
        'focused': {
            'brow_lift': -0.028,
            'brow_tilt': -0.26,
            'eye_scale_y': 0.72,
            'pupil_scale': 0.92,
            'mouth_base_open': 0.0,
            'mouth_smile': -0.06,
            'head_pitch_deg': -4.0,
        },
        'surprised': {
            'brow_lift': 0.055,
            'brow_tilt': 0.18,
            'eye_scale_y': 1.28,
            'pupil_scale': 0.74,
            'mouth_base_open': 0.24,
            'mouth_smile': 0.0,
            'head_pitch_deg': 4.5,
        },
        'happy': {
            'brow_lift': 0.025,
            'brow_tilt': 0.14,
            'eye_scale_y': 0.88,
            'pupil_scale': 1.08,
            'mouth_base_open': 0.08,
            'mouth_smile': 0.34,
            'head_pitch_deg': 2.0,
        },
    }
    if key not in table:
        raise ValueError(f'Unknown expression {expression!r}; expected one of {EXPRESSIONS}')
    return dict(table[key])


def blink_aperture(
    frame: int,
    *,
    blink_period: int = 105,
    blink_offset: int = 19,
    blink_duration: int = 4,
) -> float:
    period = max(16, int(blink_period))
    dur = max(1, min(period // 2, int(blink_duration)))
    phase = (int(frame) + int(blink_offset)) % period
    if phase >= dur:
        return 1.0
    if dur >= 3 and phase in (0, dur - 1):
        return 0.22
    return 0.0


def is_blinking(
    frame: int,
    *,
    blink_period: int = 105,
    blink_offset: int = 19,
    blink_duration: int = 4,
) -> bool:
    return blink_aperture(
        frame,
        blink_period=blink_period,
        blink_offset=blink_offset,
        blink_duration=blink_duration,
    ) < 0.5


def quantize_mouth_level(norm_amp: float) -> float:
    val = max(0.0, min(1.0, float(norm_amp)))
    if val < 0.12:
        return 0.0
    if val < 0.52:
        return 0.35
    if val < 0.84:
        return 0.75
    return 1.0


def _read_wav_mono_samples(wav_path: Path) -> tuple[list[float], int]:
    with wave.open(str(wav_path), 'rb') as rf:
        channels = rf.getnchannels()
        sampwidth = rf.getsampwidth()
        rate = rf.getframerate()
        nframes = rf.getnframes()
        raw = rf.readframes(nframes)
    if sampwidth != 2 or channels < 1:
        raise ValueError('Mouth envelope extraction requires 16-bit PCM WAV')
    pcm = array('h', raw)
    if sys.byteorder != 'little':
        pcm.byteswap()
    mono = [pcm[i * channels] / 32768.0 for i in range(nframes)]
    return mono, rate


def _normalize_audio_sequence(seq: Sequence[float | int]) -> list[float]:
    if not seq:
        return []
    raw_vals = [float(x) for x in seq]
    peak = max(abs(v) for v in raw_vals)
    if peak > 1.5:
        return [max(-1.0, min(1.0, v / 32768.0)) for v in raw_vals]
    return [max(-1.0, min(1.0, v)) for v in raw_vals]


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * pct))))
    return ordered[idx]


def _resample_or_pad_envelope(values: list[float], target_frames: int) -> list[float]:
    if len(values) == target_frames:
        return values
    if not values:
        return [0.0] * target_frames
    if target_frames == 1:
        return [values[0]]
    out: list[float] = []
    src_last = len(values) - 1
    dst_last = target_frames - 1
    for i in range(target_frames):
        pos = (i * src_last) / dst_last
        lo = int(math.floor(pos))
        hi = min(src_last, lo + 1)
        frac = pos - lo
        out.append(values[lo] * (1.0 - frac) + values[hi] * frac)
    return out


def build_mouth_envelope(
    audio_samples_or_duration: Sequence[float | int] | Path | str | float | int,
    fps: str | float | Fraction = '30/1',
    *,
    duration_frames: int | None = None,
    sample_rate: int = 48000,
    seed: int = 42,
    speech_text: str = '',
    quantize: bool = True,
) -> list[float]:
    fps_val = float(Fraction(str(fps)) if isinstance(fps, str) else Fraction(fps))
    if fps_val <= 0:
        raise ValueError('fps must be positive')
    if duration_frames is not None and (type(duration_frames) is not int or duration_frames < 1):
        raise ValueError('duration_frames must be a positive integer')

    if isinstance(audio_samples_or_duration, (Path, str)):
        samples, rate = _read_wav_mono_samples(Path(audio_samples_or_duration))
        total_frames = duration_frames or max(1, int(round((len(samples) / max(1, rate)) * fps_val)))
        return _envelope_from_samples(samples, rate, fps_val, total_frames, quantize=quantize)

    if isinstance(audio_samples_or_duration, bool):
        raise ValueError('audio_samples_or_duration cannot be a boolean')

    if isinstance(audio_samples_or_duration, (int, float)):
        dur_sec = float(audio_samples_or_duration)
        if not math.isfinite(dur_sec) or dur_sec < 0.0:
            raise ValueError('Duration must be non-negative and finite')
        total_frames = duration_frames or max(1, int(round(dur_sec * fps_val)))
        return _synthetic_mouth_envelope(total_frames, fps_val, seed=seed, speech_text=speech_text, quantize=quantize)

    if isinstance(audio_samples_or_duration, (Sequence, array)):
        samples = _normalize_audio_sequence(audio_samples_or_duration)
        total_frames = duration_frames or max(1, int(round((len(samples) / max(1, sample_rate)) * fps_val)))
        return _envelope_from_samples(samples, sample_rate, fps_val, total_frames, quantize=quantize)

    raise ValueError('Unsupported audio_samples_or_duration type for build_mouth_envelope')


def _envelope_from_samples(
    samples: list[float],
    rate: int,
    fps_val: float,
    total_frames: int,
    *,
    quantize: bool,
) -> list[float]:
    if not samples:
        return [0.0] * total_frames
    raw_frames = max(1, int(round((len(samples) / max(1, rate)) * fps_val)))
    rms_list: list[float] = []
    for vf in range(raw_frames):
        s0 = int(round((vf / fps_val) * rate))
        s1 = min(len(samples), max(s0 + 1, int(round(((vf + 1) / fps_val) * rate))))
        if s0 >= len(samples):
            rms_list.append(0.0)
            continue
        sq = sum(samples[i] * samples[i] for i in range(s0, s1))
        rms_list.append(math.sqrt(sq / max(1, s1 - s0)))
    if len(rms_list) != total_frames:
        rms_list = _resample_or_pad_envelope(rms_list, total_frames)
    noise_floor = 0.008
    active_rms = [r for r in rms_list if r >= noise_floor]
    p95 = max(0.05, _percentile(active_rms, 0.95)) if active_rms else 0.2
    out: list[float] = []
    for r in rms_list:
        if r < noise_floor:
            out.append(0.0)
        else:
            norm = min(1.0, r / p95)
            out.append(quantize_mouth_level(norm) if quantize else round(norm, 4))
    return out


def _synthetic_mouth_envelope(
    total_frames: int,
    fps_val: float,
    *,
    seed: int,
    speech_text: str,
    quantize: bool,
) -> list[float]:
    clean = speech_text.strip()
    if not clean:
        lead = min(2, total_frames // 8)
        tail = min(3, total_frames // 6)
        state = (int(seed) or 19) & 0xFFFFFFFF
        out: list[float] = []
        for idx in range(total_frames):
            if idx < lead or idx >= total_frames - tail:
                out.append(0.0)
                continue
            state = (1664525 * state + 1013904223) & 0xFFFFFFFF
            t_sec = idx / fps_val
            syllable_wave = 0.52 + 0.48 * math.sin(t_sec * math.tau * 4.6 + (seed % 7) * 0.4)
            mod = 0.72 + 0.28 * ((state & 0xFF) / 255.0)
            amp = max(0.0, min(1.0, syllable_wave * mod))
            out.append(quantize_mouth_level(amp) if quantize else round(amp, 4))
        return out

    tokens = [ch for ch in clean if not ch.isspace()]
    lead = 2 if total_frames >= 16 else 0
    tail = 4 if total_frames >= 20 else 0
    active_span = max(1, total_frames - lead - tail)
    state = (int(seed) or 23) & 0xFFFFFFFF
    vowels = set('aeiouyAEIOUYäöüÄÖÜıİğĞşŞçÇ')
    pauses = set(',.;:!?—-')
    env: list[float] = []
    for f in range(total_frames):
        if f < lead or f >= total_frames - tail:
            env.append(0.0)
            continue
        u = (f - lead) / active_span
        tok_idx = min(len(tokens) - 1, int(u * len(tokens)))
        ch = tokens[tok_idx]
        if ch in pauses:
            env.append(0.0)
            continue
        state = (1664525 * state + 1013904223) & 0xFFFFFFFF
        local_cycle = abs(math.sin((f - lead) * (math.pi / max(3.0, fps_val / 7.5)) + (tok_idx % 5) * 0.5))
        base = 0.92 if ch in vowels else 0.56
        jitter = 0.85 + 0.25 * ((state & 0xFF) / 255.0)
        amp = max(0.0, min(1.0, local_cycle * base * jitter))
        env.append(quantize_mouth_level(amp) if quantize else round(amp, 4))
    return env


def _rotate_xyz(pt: tuple[float, float, float], pitch_deg: float, roll_deg: float, yaw_deg: float) -> tuple[float, float, float]:
    x, y, z = pt
    if pitch_deg:
        rp = math.radians(pitch_deg)
        cp, sp = math.cos(rp), math.sin(rp)
        y, z = y * cp - z * sp, y * sp + z * cp
    if roll_deg:
        rr = math.radians(roll_deg)
        cr, sr = math.cos(rr), math.sin(rr)
        x, z = x * cr + z * sr, -x * sr + z * cr
    if yaw_deg:
        ry = math.radians(yaw_deg)
        cy, sy = math.cos(ry), math.sin(ry)
        x, y = x * cy - y * sy, x * sy + y * cy
    return (x, y, z)


def _add_box(
    verts: list[tuple[float, float, float]],
    faces: list[tuple[int, ...]],
    roles: list[str],
    cx: float,
    cy: float,
    cz: float,
    sx: float,
    sy: float,
    sz: float,
    role: str,
    *,
    top_scale: float = 1.0,
    tilt_x: float = 0.0,
    tilt_z: float = 0.0,
) -> None:
    hx, hy, hz = sx * 0.5, sy * 0.5, sz * 0.5
    tx, ty = hx * top_scale, hy * top_scale
    local = [
        (-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
        (-tx, -ty, hz), (tx, -ty, hz), (tx, ty, hz), (-tx, ty, hz),
    ]
    base = len(verts)
    for p in local:
        rp = _rotate_xyz(p, tilt_x, 0.0, tilt_z)
        verts.append((rp[0] + cx, rp[1] + cy, rp[2] + cz))
    quads = (
        (0, 1, 5, 4),
        (1, 2, 6, 5),
        (2, 3, 7, 6),
        (3, 0, 4, 7),
        (4, 5, 6, 7),
        (3, 2, 1, 0),
    )
    for q in quads:
        faces.append(tuple(base + idx for idx in q))
        roles.append(role)


def _add_prism(
    verts: list[tuple[float, float, float]],
    faces: list[tuple[int, ...]],
    roles: list[str],
    cx: float,
    cy: float,
    cz: float,
    rx_bot: float,
    ry_bot: float,
    rx_top: float,
    ry_top: float,
    height: float,
    sides: int,
    role: str,
    *,
    angle_offset: float = 0.0,
) -> None:
    hz = height * 0.5
    base = len(verts)
    for z_val, rx, ry in ((-hz, rx_bot, ry_bot), (hz, rx_top, ry_top)):
        for i in range(sides):
            ang = math.tau * i / sides + angle_offset
            verts.append((cx + rx * math.cos(ang), cy + ry * math.sin(ang), cz + z_val))
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((base + i, base + j, base + sides + j, base + sides + i))
        roles.append(role)
    faces.append(tuple(base + sides + i for i in range(sides)))
    roles.append(role)
    faces.append(tuple(base + i for i in range(sides - 1, -1, -1)))
    roles.append(role)


def _add_front_quad(
    verts: list[tuple[float, float, float]],
    faces: list[tuple[int, ...]],
    roles: list[str],
    pts: list[tuple[float, float, float]],
    role: str,
) -> None:
    base = len(verts)
    verts.extend(pts)
    faces.append(tuple(base + i for i in range(len(pts))))
    roles.append(role)


def build_character_mesh_data(
    preset_id: str,
    *,
    expression: str = 'neutral',
    mouth_open: float = 0.0,
    blink_open: float = 1.0,
    yaw_deg: float = 0.0,
    pitch_deg: float = 0.0,
    roll_deg: float = 0.0,
    location: tuple[float, float, float] = (0.0, 0.0, 0.0),
    scale: float = 1.0,
    phase: float = 0.0,
) -> dict[str, Any]:
    preset = get_character_preset(preset_id)
    expr = expression_parameters(expression)
    m_open = max(0.0, min(1.0, float(mouth_open) + expr['mouth_base_open'] * (1.0 - float(mouth_open))))
    b_open = max(0.0, min(1.0, float(blink_open)))
    head_shape = preset['head_shape']
    breath_z = 0.014 * math.sin(phase)

    torso_verts: list[tuple[float, float, float]] = []
    torso_faces: list[tuple[int, ...]] = []
    torso_roles: list[str] = []

    _add_prism(
        torso_verts, torso_faces, torso_roles,
        0.0, 0.0, -0.34 + breath_z * 0.5,
        0.40, 0.25, 0.48, 0.29, 0.44, 6, 'primary', angle_offset=math.pi / 6.0,
    )
    _add_box(torso_verts, torso_faces, torso_roles, 0.0, 0.0, -0.05 + breath_z * 0.6, 0.22, 0.18, 0.16, 'secondary', top_scale=0.88)

    if preset['torso_shape'] == 'mantle_rig':
        _add_box(torso_verts, torso_faces, torso_roles, -0.38, 0.02, -0.11 + breath_z, 0.26, 0.34, 0.14, 'secondary', top_scale=0.84, tilt_z=14.0)
        _add_box(torso_verts, torso_faces, torso_roles, 0.38, 0.02, -0.11 + breath_z, 0.26, 0.34, 0.14, 'secondary', top_scale=0.84, tilt_z=-14.0)
        _add_box(torso_verts, torso_faces, torso_roles, 0.0, -0.27, -0.27 + breath_z * 0.6, 0.20, 0.05, 0.14, 'accent', top_scale=0.85)
    else:
        _add_box(torso_verts, torso_faces, torso_roles, -0.34, 0.01, -0.12 + breath_z, 0.24, 0.28, 0.12, 'accent', top_scale=0.76, tilt_z=18.0)
        _add_box(torso_verts, torso_faces, torso_roles, 0.34, 0.01, -0.12 + breath_z, 0.24, 0.28, 0.12, 'accent', top_scale=0.76, tilt_z=-18.0)
        _add_box(torso_verts, torso_faces, torso_roles, 0.0, -0.25, -0.24 + breath_z * 0.6, 0.26, 0.05, 0.10, 'secondary', top_scale=0.9)

    head_verts: list[tuple[float, float, float]] = []
    head_faces: list[tuple[int, ...]] = []
    head_roles: list[str] = []

    if head_shape == 'hex_helm':
        _add_prism(head_verts, head_faces, head_roles, 0.0, 0.0, 0.38, 0.27, 0.26, 0.32, 0.28, 0.56, 6, 'skin', angle_offset=math.pi / 6.0)
        _add_box(head_verts, head_faces, head_roles, 0.0, 0.06, 0.66, 0.62, 0.54, 0.18, 'primary', top_scale=0.82)
        _add_box(head_verts, head_faces, head_roles, 0.29, 0.04, 0.54, 0.09, 0.20, 0.44, 'accent', top_scale=0.7)
        _add_box(head_verts, head_faces, head_roles, 0.31, -0.06, 0.80, 0.04, 0.05, 0.26, 'visor', top_scale=0.65)
    elif head_shape == 'prism_visor':
        _add_prism(head_verts, head_faces, head_roles, 0.0, 0.0, 0.37, 0.28, 0.26, 0.31, 0.27, 0.52, 8, 'skin', angle_offset=math.pi / 8.0)
        _add_box(head_verts, head_faces, head_roles, 0.0, 0.03, 0.66, 0.58, 0.52, 0.16, 'primary', top_scale=0.72)
        _add_box(head_verts, head_faces, head_roles, -0.34, 0.0, 0.39, 0.10, 0.22, 0.22, 'accent', top_scale=0.85)
        _add_box(head_verts, head_faces, head_roles, 0.34, 0.0, 0.39, 0.10, 0.22, 0.22, 'accent', top_scale=0.85)
    else:
        _add_prism(head_verts, head_faces, head_roles, 0.0, 0.0, 0.37, 0.28, 0.27, 0.32, 0.28, 0.52, 8, 'skin', angle_offset=math.pi / 8.0)
        _add_box(head_verts, head_faces, head_roles, 0.0, 0.04, 0.65, 0.60, 0.52, 0.15, 'primary', top_scale=0.78)
        _add_box(head_verts, head_faces, head_roles, -0.25, 0.14, 0.72, 0.14, 0.34, 0.16, 'primary', top_scale=0.62, tilt_x=-18.0, tilt_z=12.0)
        _add_box(head_verts, head_faces, head_roles, 0.25, 0.14, 0.72, 0.14, 0.34, 0.16, 'primary', top_scale=0.62, tilt_x=-18.0, tilt_z=-12.0)
        _add_box(head_verts, head_faces, head_roles, -0.33, -0.02, 0.42, 0.08, 0.18, 0.16, 'visor', top_scale=0.8)
        _add_box(head_verts, head_faces, head_roles, 0.33, -0.02, 0.42, 0.08, 0.18, 0.16, 'visor', top_scale=0.8)

    _add_box(head_verts, head_faces, head_roles, 0.0, -0.29, 0.36, 0.06, 0.07, 0.10, 'primary', top_scale=0.7)

    jaw_drop = m_open * 0.075
    _add_box(head_verts, head_faces, head_roles, 0.0, -0.04, 0.11 - jaw_drop, 0.40, 0.38, 0.11, 'secondary', top_scale=1.08)

    face_y = -0.295
    eye_z = 0.43
    eye_h = 0.062 * expr['eye_scale_y'] * max(0.08, b_open)
    eye_w = 0.064
    for side in (-1.0, 1.0):
        ex = side * 0.125
        if b_open <= 0.15:
            _add_front_quad(
                head_verts, head_faces, head_roles,
                [
                    (ex - eye_w, face_y - 0.008, eye_z - 0.012),
                    (ex + eye_w, face_y - 0.008, eye_z - 0.012),
                    (ex + eye_w, face_y - 0.008, eye_z + 0.012),
                    (ex - eye_w, face_y - 0.008, eye_z + 0.012),
                ],
                'brow',
            )
        else:
            _add_front_quad(
                head_verts, head_faces, head_roles,
                [
                    (ex - eye_w, face_y - 0.006, eye_z - eye_h),
                    (ex + eye_w, face_y - 0.006, eye_z - eye_h),
                    (ex + eye_w, face_y - 0.006, eye_z + eye_h),
                    (ex - eye_w, face_y - 0.006, eye_z + eye_h),
                ],
                'eye',
            )
            pw = 0.032 * expr['pupil_scale']
            ph = min(eye_h * 0.85, 0.040 * expr['pupil_scale'])
            _add_front_quad(
                head_verts, head_faces, head_roles,
                [
                    (ex - pw, face_y - 0.012, eye_z - ph),
                    (ex + pw, face_y - 0.012, eye_z - ph),
                    (ex + pw, face_y - 0.012, eye_z + ph),
                    (ex - pw, face_y - 0.012, eye_z + ph),
                ],
                'pupil',
            )

        brow_z = eye_z + 0.092 + expr['brow_lift']
        inner_dy = expr['brow_tilt'] * 0.035
        outer_dy = -expr['brow_tilt'] * 0.025
        bw_in = ex - side * 0.072
        bw_out = ex + side * 0.076
        _add_front_quad(
            head_verts, head_faces, head_roles,
            [
                (bw_in, face_y - 0.014, brow_z + inner_dy - 0.014),
                (bw_out, face_y - 0.014, brow_z + outer_dy - 0.014),
                (bw_out, face_y - 0.014, brow_z + outer_dy + 0.018),
                (bw_in, face_y - 0.014, brow_z + inner_dy + 0.018),
            ],
            'brow',
        )

    mouth_z = 0.22 - jaw_drop * 0.4
    mouth_w = 0.115 - 0.02 * m_open
    mouth_h = 0.016 + 0.068 * m_open
    smile_dz = expr['mouth_smile'] * 0.045
    _add_front_quad(
        head_verts, head_faces, head_roles,
        [
            (-mouth_w * 1.15, face_y - 0.008, mouth_z - mouth_h - 0.014 + smile_dz * 0.5),
            (mouth_w * 1.15, face_y - 0.008, mouth_z - mouth_h - 0.014 + smile_dz * 0.5),
            (mouth_w * 1.18, face_y - 0.008, mouth_z + mouth_h + 0.014 + smile_dz),
            (-mouth_w * 1.18, face_y - 0.008, mouth_z + mouth_h + 0.014 + smile_dz),
        ],
        'mouth_lip',
    )
    if m_open > 0.05:
        _add_front_quad(
            head_verts, head_faces, head_roles,
            [
                (-mouth_w * 0.88, face_y - 0.013, mouth_z - mouth_h * 0.85),
                (mouth_w * 0.88, face_y - 0.013, mouth_z - mouth_h * 0.85),
                (mouth_w * 0.92, face_y - 0.013, mouth_z + mouth_h * 0.85 + smile_dz * 0.4),
                (-mouth_w * 0.92, face_y - 0.013, mouth_z + mouth_h * 0.85 + smile_dz * 0.4),
            ],
            'mouth_dark',
        )

    eff_pitch = pitch_deg + expr['head_pitch_deg']
    head_pivot = (0.0, 0.0, 0.10)
    transformed_head: list[tuple[float, float, float]] = []
    for vx, vy, vz in head_verts:
        rx, ry, rz = _rotate_xyz((vx - head_pivot[0], vy - head_pivot[1], vz - head_pivot[2]), eff_pitch, roll_deg, yaw_deg * 0.35)
        transformed_head.append((rx + head_pivot[0], ry + head_pivot[1], rz + head_pivot[2] + breath_z))

    all_local = torso_verts + transformed_head
    offset = len(torso_verts)
    shifted_head_faces = [tuple(idx + offset for idx in f) for f in head_faces]
    all_faces = torso_faces + shifted_head_faces
    all_roles = torso_roles + head_roles

    final_verts: list[tuple[float, float, float]] = []
    for pt in all_local:
        rx, ry, rz = _rotate_xyz(pt, 0.0, 0.0, yaw_deg)
        final_verts.append((
            rx * scale + location[0],
            ry * scale + location[1],
            rz * scale + location[2],
        ))

    return {
        'preset': preset['id'],
        'expression': expression,
        'mouth_open': round(m_open, 4),
        'blink_open': round(b_open, 4),
        'vertices': final_verts,
        'faces': all_faces,
        'face_roles': all_roles,
        'materials': dict(preset['palette']),
    }


def _build_relay_prop_facets(u: float, accent_hex: str, fg_hex: str, bg_hex: str) -> list[tuple[list[tuple[float, float, float]], str]]:
    verts: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    roles: list[str] = []
    _add_prism(verts, faces, roles, 0.0, 0.0, -0.35, 0.72, 0.72, 0.56, 0.56, 0.36, 8, 'base', angle_offset=math.pi / 8.0)
    _add_box(verts, faces, roles, 0.0, 0.0, -0.10, 0.52, 0.52, 0.16, 'trim', top_scale=0.88)

    rot = u * math.tau * 0.75
    hover = 0.24 + 0.05 * math.sin(u * math.tau)
    diamond = [
        (0.0, 0.0, hover + 0.34),
        (0.24, 0.0, hover),
        (0.0, 0.24, hover),
        (-0.24, 0.0, hover),
        (0.0, -0.24, hover),
        (0.0, 0.0, hover - 0.30),
    ]
    d_base = len(verts)
    for pt in diamond:
        rx, ry, rz = _rotate_xyz((pt[0], pt[1], pt[2] - hover), 12.0, 0.0, math.degrees(rot))
        verts.append((rx, ry, rz + hover))
    for i in range(4):
        j = (i + 1) % 4
        faces.append((d_base + 0, d_base + 1 + i, d_base + 1 + j))
        roles.append('core')
        faces.append((d_base + 5, d_base + 1 + j, d_base + 1 + i))
        roles.append('core')

    active_core = '#4cd6d0' if u >= 0.45 else accent_hex
    role_map = {
        'base': rgb_to_hex(mix_oklab(bg_hex, fg_hex, 0.26)),
        'trim': fg_hex,
        'core': active_core,
    }
    return [([verts[i] for i in f], role_map[r]) for f, r in zip(faces, roles)]


def _sub3(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot3(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _project_at(
    point: tuple[float, float, float],
    cam: Camera3D,
    screen_cx: float,
    screen_cy: float,
    pixel_unit: float,
) -> tuple[float, float, float] | None:
    rel = _sub3(point, cam.position)
    depth = _dot3(rel, cam.forward)
    if depth <= 0.1:
        return None
    px = _dot3(rel, cam.right)
    py = _dot3(rel, cam.up)
    proj_scale = pixel_unit * (cam.focal_mm / cam.sensor_width_mm) / depth
    return (screen_cx + px * proj_scale, screen_cy - py * proj_scale, depth)


def _render_faceted_list(
    canvas: Any,
    faceted_polys: list[tuple[list[tuple[float, float, float]], str]],
    cam: Camera3D,
    screen_cx: float,
    screen_cy: float,
    pixel_unit: float,
    accent_hex: str,
    edge_hex: str,
    unit: float,
    look_mode: str,
    dither: float,
) -> None:
    projected: list[tuple[float, list[tuple[float, float]], tuple[int, int, int], tuple[int, int, int]]] = []
    for verts, albedo_hex in faceted_polys:
        pts: list[tuple[float, float]] = []
        depths: list[float] = []
        valid = True
        for v in verts:
            pr = _project_at(v, cam, screen_cx, screen_cy, pixel_unit)
            if pr is None:
                valid = False
                break
            pts.append((pr[0], pr[1]))
            depths.append(pr[2])
        if not valid:
            continue
        rgb = shade_facet_three_point(verts, cam.position, albedo_hex, accent_hex, look_mode=look_mode, dither=dither)
        edge_rgb = mix_oklab(rgb_to_hex(rgb), edge_hex, 0.22)
        projected.append((sum(depths) / len(depths), pts, rgb, edge_rgb))

    projected.sort(key=lambda item: -item[0])
    outline_w = max(1, round(0.8 * unit))
    for _, pts, fill_rgb, outline_rgb in projected:
        canvas.polygon(pts, fill=fill_rgb, outline=outline_rgb, width=outline_w)


def _wrap_text_to_width(canvas: Any, text: str, font: Any, max_width: float, max_lines: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    current = ''
    for word in words:
        cand = f'{current} {word}'.strip() if current else word
        box = canvas.textbbox((0, 0), cand, font=font)
        if (box[2] - box[0]) <= max_width or not current:
            current = cand
        else:
            lines.append(current)
            current = word
            if len(lines) >= max_lines:
                break
    if current and len(lines) < max_lines:
        lines.append(current)
    return lines[:max_lines]


def _draw_emblem_glyph(canvas: Any, head_shape: str, cx: float, cy: float, r: float, fill_col: str, accent_col: str) -> None:
    if head_shape == 'hex_helm':
        pts = [(cx + r * math.cos(math.tau * i / 6.0 - math.pi / 2.0), cy + r * math.sin(math.tau * i / 6.0 - math.pi / 2.0)) for i in range(6)]
    elif head_shape == 'prism_visor':
        pts = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
    else:
        pts = [(cx, cy - r), (cx + r * 0.9, cy - r * 0.35), (cx + r * 0.65, cy + r), (cx - r * 0.65, cy + r), (cx - r * 0.9, cy - r * 0.35)]
    canvas.polygon(pts, fill=fill_col, outline=accent_col)
    inner_r = r * 0.42
    canvas.polygon([(cx, cy - inner_r), (cx + inner_r, cy), (cx, cy + inner_r), (cx - inner_r, cy)], fill=accent_col)


def _draw_beveled_dialogue_hud(
    canvas: Any,
    *,
    w: int,
    h: int,
    unit: float,
    scale: int,
    speaker: str,
    dialogue: str,
    preset_id: str,
    u: float,
    background: str,
    foreground: str,
    accent: str,
) -> list[dict[str, Any]]:
    if not speaker and not dialogue:
        return []
    is_dark = sum(hex_to_rgb(background)) < 384
    panel_hex = rgb_to_hex(mix_oklab(background, '#080b10' if is_dark else '#ffffff', 0.36))
    bevel_hi = rgb_to_hex(mix_oklab(accent, foreground, 0.35))
    bevel_lo = rgb_to_hex(mix_oklab(panel_hex, '#000000' if is_dark else foreground, 0.4))
    pill_bg = rgb_to_hex(mix_oklab(panel_hex, accent, 0.25))

    is_vertical = h > w
    box_x0 = int(round(w * 0.055))
    box_x1 = int(round(w * 0.945))
    box_y1 = int(round(h * 0.812))
    box_y0 = int(round(h * (0.645 if is_vertical else 0.675)))
    chamfer = max(4, round(10 * unit))

    outer_pts = [
        (box_x0 + chamfer, box_y0),
        (box_x1 - chamfer, box_y0),
        (box_x1, box_y0 + chamfer),
        (box_x1, box_y1 - chamfer),
        (box_x1 - chamfer, box_y1),
        (box_x0 + chamfer, box_y1),
        (box_x0, box_y1 - chamfer),
        (box_x0, box_y0 + chamfer),
    ]
    canvas.polygon(outer_pts, fill=panel_hex, outline=bevel_hi, width=max(1, round(2.0 * unit)))
    inset = max(2, round(4 * unit))
    inner_pts = [
        (box_x0 + chamfer + inset, box_y0 + inset),
        (box_x1 - chamfer - inset, box_y0 + inset),
        (box_x1 - inset, box_y0 + chamfer + inset),
        (box_x1 - inset, box_y1 - chamfer - inset),
        (box_x1 - chamfer - inset, box_y1 - inset),
        (box_x0 + chamfer + inset, box_y1 - inset),
        (box_x0 + inset, box_y1 - chamfer - inset),
        (box_x0 + inset, box_y0 + chamfer + inset),
    ]
    canvas.polygon(inner_pts, outline=bevel_lo, width=max(1, round(1.0 * unit)))

    preset = get_character_preset(preset_id)
    bounds: list[dict[str, Any]] = []
    pad_x = max(8, round(16 * unit))
    pad_y = max(6, round(12 * unit))

    if is_vertical:
        emblem_r = max(6.0, 12.0 * unit)
        _draw_emblem_glyph(canvas, preset['head_shape'], box_x0 + pad_x + emblem_r, box_y0 + pad_y + emblem_r, emblem_r, preset['palette']['primary'], accent)
        text_left = box_x0 + pad_x
        if speaker:
            sp_font = resolve_font(max(9, round(15 * unit)), bold=True)
            sp_x = box_x0 + pad_x + emblem_r * 2.4 + 6 * unit
            sp_y = box_y0 + pad_y
            sp_box = canvas.textbbox((sp_x, sp_y), speaker, font=sp_font)
            canvas.rectangle((sp_box[0] - 6 * unit, sp_box[1] - 3 * unit, sp_box[2] + 6 * unit, sp_box[3] + 3 * unit), fill=pill_bg, outline=accent, width=max(1, round(unit)))
            canvas.text((sp_x, sp_y), speaker, fill=foreground, font=sp_font)
            bounds.append({'field': 'speaker', 'bounds': [round(v / scale, 3) for v in sp_box]})
            line_top = sp_box[3] + max(6, round(10 * unit))
        else:
            line_top = box_y0 + pad_y
        text_max_w = max(40.0, (box_x1 - pad_x) - text_left)
    else:
        badge_w = int(round((box_x1 - box_x0) * 0.21))
        div_x = box_x0 + badge_w
        canvas.line((div_x, box_y0 + pad_y, div_x, box_y1 - pad_y), fill=bevel_lo, width=max(1, round(1.2 * unit)))
        emblem_r = max(6.0, min(15.0 * unit, (box_y1 - box_y0) * 0.22))
        _draw_emblem_glyph(canvas, preset['head_shape'], box_x0 + badge_w * 0.5, box_y0 + (box_y1 - box_y0) * 0.40, emblem_r, preset['palette']['primary'], accent)
        if speaker:
            sp_font = resolve_font(max(8, round(13 * unit)), bold=True)
            sp_probe = canvas.textbbox((0, 0), speaker, font=sp_font)
            if (sp_probe[2] - sp_probe[0]) > badge_w - pad_x:
                sp_font = resolve_font(max(7, round(10 * unit)), bold=True)
                sp_probe = canvas.textbbox((0, 0), speaker, font=sp_font)
            sp_w = sp_probe[2] - sp_probe[0]
            sp_x = box_x0 + max(4, (badge_w - sp_w) * 0.5)
            sp_y = box_y0 + (box_y1 - box_y0) * 0.68
            sp_box = canvas.textbbox((sp_x, sp_y), speaker, font=sp_font)
            canvas.text((sp_x, sp_y), speaker, fill=foreground, font=sp_font)
            bounds.append({'field': 'speaker', 'bounds': [round(v / scale, 3) for v in sp_box]})
        text_left = div_x + pad_x
        line_top = box_y0 + pad_y
        text_max_w = max(40.0, (box_x1 - pad_x) - text_left)

    if dialogue:
        reveal_u = min(1.0, 0.25 + 0.75 * (u / 0.55))
        visible_chars = max(min(len(dialogue), 12), int(round(len(dialogue) * reveal_u)))
        shown_text = dialogue[:visible_chars]
        font_px = max(8, round((19 if is_vertical else 18) * unit))
        d_font = resolve_font(font_px, bold=False)
        wrapped = _wrap_text_to_width(canvas, shown_text, d_font, text_max_w, 3 if is_vertical else 2)
        if len(wrapped) == 1:
            line_h = max(10, round(font_px * 1.28))
        else:
            line_h = max(9, round(font_px * 1.24))
        avail_h = max(12, box_y1 - pad_y * 0.6 - line_top)
        if len(wrapped) * line_h > avail_h and font_px > 8:
            font_px = max(8, int(font_px * avail_h / max(1, len(wrapped) * line_h)))
            d_font = resolve_font(font_px, bold=False)
            wrapped = _wrap_text_to_width(canvas, shown_text, d_font, text_max_w, 3 if is_vertical else 2)
            line_h = max(8, round(font_px * 1.2))
        for idx, line in enumerate(wrapped):
            ly = line_top + idx * line_h
            l_box = canvas.textbbox((text_left, ly), line, font=d_font)
            if l_box[3] <= box_y1 - 2:
                canvas.text((text_left, ly), line, fill=foreground, font=d_font)
                bounds.append({'field': f'dialogue_{idx}', 'bounds': [round(v / scale, 3) for v in l_box]})

    return bounds


def _draw_retro_stage_backdrop(
    canvas: Any,
    w: int,
    h: int,
    unit: float,
    seed: int,
    u: float,
    background: str,
    foreground: str,
    accent: str,
) -> None:
    horizon_y = int(round(h * 0.56))
    grid_col = rgb_to_hex(mix_oklab(background, foreground, 0.14))
    accent_dim = rgb_to_hex(mix_oklab(background, accent, 0.24))
    sky_band = rgb_to_hex(mix_oklab(background, accent, 0.08))
    canvas.rectangle((0, int(round(h * 0.44)), w, horizon_y), fill=sky_band)
    canvas.line((0, horizon_y, w, horizon_y), fill=accent_dim, width=max(1, round(1.5 * unit)))

    for row in range(1, 7):
        t = (row / 6.0) ** 1.65
        gy = horizon_y + (h - horizon_y) * t
        canvas.line((0, gy, w, gy), fill=grid_col, width=max(1, round(unit)))
    vanish_x = w * 0.5
    for col in range(-6, 7):
        top_x = vanish_x + col * (w * 0.08)
        bot_x = vanish_x + col * (w * 0.24)
        canvas.line((top_x, horizon_y, bot_x, h), fill=grid_col, width=max(1, round(unit)))

    state = (int(seed) or 42) & 0xFFFFFFFF
    for idx in range(14):
        state = (1664525 * state + 1013904223) & 0xFFFFFFFF
        sx = int(((state >> 16) % 900) / 1000.0 * w * 0.90 + w * 0.05)
        state = (1664525 * state + 1013904223) & 0xFFFFFFFF
        sy = int(((state >> 16) % 400) / 1000.0 * h * 0.85 + h * 0.06)
        r = (2.2 if idx % 3 == 0 else 1.4) * unit * (0.85 + 0.15 * math.sin(u * math.tau + idx))
        col = accent if idx % 4 == 0 else rgb_to_hex(mix_oklab(background, foreground, 0.35))
        canvas.ellipse((sx - r, sy - r, sx + r, sy + r), fill=col)


def draw_character_scene(
    canvas: Any,
    scene: dict[str, Any],
    frame: int,
    w: int,
    h: int,
    fps_val: float,
    seed: int,
    background: str,
    foreground: str,
    accent: str,
    *,
    scale: int = 1,
    look_mode: str = 'agx',
    dither: float = 0.0,
) -> list[dict[str, Any]]:
    unit = min(w / 960.0, h / 540.0)
    dur = max(1, int(scene.get('duration_frames', 60)))
    u = frame / max(1, dur - 1)
    params = scene.get('params', {})

    _draw_retro_stage_backdrop(canvas, w, h, unit, seed, u, background, foreground, accent)

    char_id = str(params.get('character', 'scout'))
    partner_id = str(params.get('partner_character', 'archivist'))
    expr = str(params.get('expression', 'neutral'))
    partner_expr = str(params.get('partner_expression', 'neutral'))
    shot_role = str(params.get('shot_role', 'speaker_a'))
    char_pos = str(params.get('character_pos', 'duo' if shot_role in ('establishing', 'two_shot') else ('right' if shot_role == 'speaker_b' else 'left')))
    base_blink_offset = int(params.get('blink_offset', 0))

    mouth_env = params.get('mouth_envelope')
    if isinstance(mouth_env, list) and mouth_env:
        mouth_val = float(mouth_env[min(max(0, frame), len(mouth_env) - 1)])
    else:
        mouth_val = 0.0

    cam_cfg = dict(scene.get('camera') or {})
    if 'position' not in cam_cfg:
        cam_cfg['position'] = [0.0, -3.55, 0.36]
    if 'target' not in cam_cfg:
        cam_cfg['target'] = [0.0, 0.0, 0.28]
    if 'focal_mm' not in cam_cfg:
        cam_cfg['focal_mm'] = 44.0
    cam = Camera3D.from_scene({**scene, 'camera': cam_cfg}, frame, fps_val, seed, camera_locked=False)

    pixel_unit = max(w * 0.92, min(w, h) * 1.15) if h > w else min(w, h) * 1.02
    eye_y_frac = 0.365 if h > w else 0.355
    stage_cy = h * (eye_y_frac + 0.055)

    if shot_role == 'insert':
        prop_polys = _build_relay_prop_facets(u, accent, foreground, background)
        sh_col = rgb_to_hex(mix_oklab(background, '#050608', 0.32))
        canvas.ellipse((w * 0.36, h * 0.56, w * 0.64, h * 0.62), fill=sh_col)
        _render_faceted_list(canvas, prop_polys, cam, w * 0.50, stage_cy, pixel_unit * 1.15, accent, foreground, unit, look_mode, dither)
    elif char_pos == 'duo' or shot_role in ('establishing', 'two_shot'):
        p_a = get_character_preset(char_id)
        p_b = get_character_preset(partner_id)
        blink_a = blink_aperture(frame, blink_period=p_a['blink_period'], blink_offset=p_a['blink_offset'] + base_blink_offset, blink_duration=p_a['blink_duration'])
        blink_b = blink_aperture(frame, blink_period=p_b['blink_period'], blink_offset=p_b['blink_offset'] + base_blink_offset, blink_duration=p_b['blink_duration'])

        prop_polys = _build_relay_prop_facets(u, accent, foreground, background)
        _render_faceted_list(canvas, prop_polys, cam, w * 0.50, stage_cy + 14 * unit, pixel_unit * 0.56, accent, foreground, unit, look_mode, dither)

        mesh_a = build_character_mesh_data(
            char_id,
            expression=expr,
            mouth_open=mouth_val if shot_role != 'establishing' else 0.0,
            blink_open=blink_a,
            yaw_deg=24.0 + 3.0 * math.sin(u * math.tau),
            scale=0.86,
            phase=u * math.tau,
        )
        mesh_b = build_character_mesh_data(
            partner_id,
            expression=partner_expr,
            mouth_open=0.0,
            blink_open=blink_b,
            yaw_deg=-24.0 - 3.0 * math.sin(u * math.tau + 0.8),
            scale=0.86,
            phase=u * math.tau + 1.4,
        )
        polys_a = [([mesh_a['vertices'][i] for i in f], mesh_a['materials'][r]) for f, r in zip(mesh_a['faces'], mesh_a['face_roles'])]
        polys_b = [([mesh_b['vertices'][i] for i in f], mesh_b['materials'][r]) for f, r in zip(mesh_b['faces'], mesh_b['face_roles'])]
        _render_faceted_list(canvas, polys_a, cam, w * 0.30, stage_cy, pixel_unit * 0.92, accent, foreground, unit, look_mode, dither)
        _render_faceted_list(canvas, polys_b, cam, w * 0.70, stage_cy, pixel_unit * 0.92, accent, foreground, unit, look_mode, dither)
    else:
        preset = get_character_preset(char_id)
        blink_v = blink_aperture(frame, blink_period=preset['blink_period'], blink_offset=preset['blink_offset'] + base_blink_offset, blink_duration=preset['blink_duration'])
        if char_pos == 'left':
            cx_frac, yaw = 0.36, 22.0
        elif char_pos == 'right':
            cx_frac, yaw = 0.64, -22.0
        else:
            cx_frac, yaw = 0.50, 0.0
        yaw_anim = yaw + 3.5 * math.sin(u * math.tau)
        mesh = build_character_mesh_data(
            char_id,
            expression=expr,
            mouth_open=mouth_val,
            blink_open=blink_v,
            yaw_deg=yaw_anim,
            scale=1.0,
            phase=u * math.tau,
        )
        polys = [([mesh['vertices'][i] for i in f], mesh['materials'][r]) for f, r in zip(mesh['faces'], mesh['face_roles'])]
        _render_faceted_list(canvas, polys, cam, w * cx_frac, stage_cy, pixel_unit, accent, foreground, unit, look_mode, dither)

    speaker = str(params.get('speaker') or params.get('kicker') or '').strip()
    dialogue = str(params.get('dialogue') or params.get('subheading') or params.get('heading') or '').strip()
    return _draw_beveled_dialogue_hud(
        canvas,
        w=w,
        h=h,
        unit=unit,
        scale=scale,
        speaker=speaker,
        dialogue=dialogue,
        preset_id=char_id,
        u=u,
        background=background,
        foreground=foreground,
        accent=accent,
    )


def has_bpy() -> bool:
    return importlib.util.find_spec('bpy') is not None


def build_blender_character(
    preset_id: str,
    *,
    expression: str = 'neutral',
    mouth_open: float = 0.0,
    blink_open: float = 1.0,
    yaw_deg: float = 0.0,
    pitch_deg: float = 0.0,
    roll_deg: float = 0.0,
    location: tuple[float, float, float] = (0.0, 0.0, 0.0),
    scale: float = 1.0,
    name_prefix: str = 'RS_Char',
    collection: Any = None,
    bpy_module: Any = None,
) -> Any:
    bpy_mod = bpy_module
    if bpy_mod is None:
        if not has_bpy():
            return None
        import bpy as imported_bpy
        bpy_mod = imported_bpy

    mesh_spec = build_character_mesh_data(
        preset_id,
        expression=expression,
        mouth_open=mouth_open,
        blink_open=blink_open,
        yaw_deg=yaw_deg,
        pitch_deg=pitch_deg,
        roll_deg=roll_deg,
        location=location,
        scale=scale,
    )
    mesh_name = f'{name_prefix}_{mesh_spec["preset"]}_Mesh'
    obj_name = f'{name_prefix}_{mesh_spec["preset"]}'
    mesh = bpy_mod.data.meshes.new(mesh_name)
    mesh.from_pydata(mesh_spec['vertices'], [], mesh_spec['faces'])
    mesh.update()

    role_to_slot: dict[str, int] = {}
    for role, hex_col in mesh_spec['materials'].items():
        mat_name = f'{name_prefix}_{mesh_spec["preset"]}_{role}'
        mat = bpy_mod.data.materials.get(mat_name) if hasattr(bpy_mod.data.materials, 'get') else None
        if mat is None:
            mat = bpy_mod.data.materials.new(mat_name)
            mat.use_nodes = True
            lin = hex_to_linear(hex_col)
            bsdf = next((n for n in mat.node_tree.nodes if getattr(n, 'type', None) == 'BSDF_PRINCIPLED'), None)
            if bsdf is not None:
                bsdf.inputs['Base Color'].default_value = (lin[0], lin[1], lin[2], 1.0)
                if 'Roughness' in bsdf.inputs:
                    bsdf.inputs['Roughness'].default_value = 0.58
                if 'Metallic' in bsdf.inputs:
                    bsdf.inputs['Metallic'].default_value = 0.08
        role_to_slot[role] = len(role_to_slot)
        mesh.materials.append(mat)

    for poly, role in zip(mesh.polygons, mesh_spec['face_roles']):
        poly.use_smooth = False
        poly.material_index = role_to_slot[role]

    obj = bpy_mod.data.objects.new(obj_name, mesh)
    target_col = collection if collection is not None else bpy_mod.context.scene.collection
    target_col.objects.link(obj)
    return obj
