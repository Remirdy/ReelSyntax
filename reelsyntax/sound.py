from fractions import Fraction
import math
from pathlib import Path
import struct
import wave

from .contracts import Project


def _voice_sample(instrument: str, local: float, length: float, frequency: float, noise_val: float) -> float:
    if instrument == 'sine':
        fade = max(0.0, min(1.0, local / 0.008, (length - local) / 0.025))
        return math.exp(-6.0 * local) * math.sin(math.tau * frequency * local) * fade
    if instrument == 'sub_impact':
        fade = max(0.0, min(1.0, local / 0.004, (length - local) / 0.06))
        sweep_phase = math.tau * (frequency * local + 36.0 * (1.0 - math.exp(-14.0 * local)) / 14.0)
        body = 0.78 * math.exp(-4.5 * local) * math.sin(sweep_phase)
        punch = 0.22 * math.exp(-38.0 * local) * math.sin(math.tau * frequency * 2.5 * local)
        return (body + punch) * fade
    if instrument == 'harmonic_pluck':
        fade = max(0.0, min(1.0, local / 0.003, (length - local) / 0.04))
        h1 = 0.62 * math.exp(-5.0 * local) * math.sin(math.tau * frequency * local)
        h2 = 0.25 * math.exp(-9.0 * local) * math.sin(math.tau * frequency * 2.0 * local)
        h3 = 0.13 * math.exp(-15.0 * local) * math.sin(math.tau * frequency * 3.0 * local)
        return (h1 + h2 + h3) * fade
    if instrument == 'warm_pad':
        fade = max(0.0, min(1.0, local / min(0.18, length * 0.35), (length - local) / min(0.22, length * 0.4)))
        s1 = 0.50 * math.sin(math.tau * frequency * local)
        s2 = 0.30 * math.sin(math.tau * (frequency * 1.4983) * local)
        s3 = 0.20 * math.sin(math.tau * (frequency * 0.5) * local)
        return (s1 + s2 + s3) * fade * 0.65
    if instrument == 'whoosh':
        u = local / max(1e-4, length)
        bell = math.sin(math.pi * min(1.0, max(0.0, u))) ** 2
        mod = 0.55 * noise_val + 0.45 * math.sin(math.tau * (frequency * (0.6 + 0.8 * u)) * local)
        return bell * mod * 0.85
    if instrument == 'click_transient':
        fade = max(0.0, min(1.0, (length - local) / max(0.005, length)))
        return math.exp(-85.0 * local) * math.sin(math.tau * frequency * local) * fade
    return 0.0


def synthesize(path, plan: Project, stem_dir: Path | None = None) -> dict:
    rate = 48000
    fps = Fraction(plan['output']['fps'])
    frames = sum(x['duration_frames'] for x in plan['scenes'])
    duration = Fraction(frames, 1) / fps
    samples = math.ceil(duration * rate)
    base_amp = 10 ** (plan['audio']['gain_db'] / 20)

    legacy_exact = (
        not plan['audio'].get('export_stems')
        and all(set(c.keys()) <= {'frame', 'frequency', 'duration_frames'} for c in plan['audio']['cues'])
    )

    if legacy_exact:
        cues = [(Fraction(c['frame'], 1) / fps, Fraction(c['duration_frames'], 1) / fps, c['frequency']) for c in plan['audio']['cues']]
        state, filtered = plan['seed'] or 1, 0.0
        peak = square_sum = 0.0
        with wave.open(str(path), 'wb') as stream:
            stream.setparams((2, 2, rate, 0, 'NONE', 'not compressed'))
            chunk = bytearray()
            for index in range(samples):
                time_s = index / rate
                state = (1664525 * state + 1013904223) & 0xffffffff
                filtered = filtered * 0.96 + ((state / 2**32) * 2 - 1) * 0.04
                envelope = max(0, min(1, time_s / 0.02, (float(duration) - time_s) / 0.03))
                value = filtered * (0.0 if plan['audio'].get('tracks') and not cues else 0.012)
                for start, length, frequency in cues:
                    local = time_s - float(start)
                    if 0 <= local < float(length):
                        fade = min(1, local / 0.008, (float(length) - local) / 0.025)
                        value += base_amp * math.exp(-6 * local) * math.sin(math.tau * frequency * local) * max(0, fade)
                value *= envelope
                peak = max(peak, abs(value))
                square_sum += value * value
                if abs(value) > 0.99:
                    raise ValueError('Audio cues overlap above safe sample peak; reduce audio.gain_db')
                sample = max(-32768, min(32767, round(value * 32767)))
                chunk.extend(struct.pack('<hh', sample, sample))
                if len(chunk) >= 65536:
                    stream.writeframesraw(chunk)
                    chunk.clear()
            stream.writeframes(chunk)
        return {
            'sample_rate': rate,
            'channels': 2,
            'samples': samples,
            'sample_peak_dbfs': 20 * math.log10(peak) if peak else None,
            'rms_dbfs': 10 * math.log10(square_sum / samples) if square_sum else None,
            'duration_rational': str(duration),
            'stems': [],
            'content': 'deterministic procedural cues and quiet noise ambience; no voice or music track',
        }

    parsed_cues = []
    stem_names = set()
    for c in plan['audio']['cues']:
        inst = c.get('instrument', 'sine')
        pan = float(c.get('pan', 0.0))
        gain_mul = 10 ** (float(c.get('gain_offset_db', 0.0)) / 20.0)
        angle = (pan + 1.0) * (math.pi * 0.25)
        gain_l, gain_r = math.cos(angle) * math.sqrt(2.0) * 0.70710678, math.sin(angle) * math.sqrt(2.0) * 0.70710678
        parsed_cues.append((float(Fraction(c['frame'], 1) / fps), float(Fraction(c['duration_frames'], 1) / fps), float(c['frequency']), inst, base_amp * gain_mul, gain_l, gain_r))
        stem_names.add(inst)

    want_stems = bool(plan['audio'].get('export_stems')) and stem_dir is not None
    stem_buffers = {name: bytearray() for name in sorted(stem_names)} if want_stems else {}

    state, filtered = plan['seed'] or 1, 0.0
    peak = square_sum = 0.0
    dur_f = float(duration)
    with wave.open(str(path), 'wb') as stream:
        stream.setparams((2, 2, rate, 0, 'NONE', 'not compressed'))
        chunk = bytearray()
        for index in range(samples):
            time_s = index / rate
            state = (1664525 * state + 1013904223) & 0xffffffff
            raw_noise = (state / 2**32) * 2.0 - 1.0
            filtered = filtered * 0.94 + raw_noise * 0.06
            envelope = max(0.0, min(1.0, time_s / 0.02, (dur_f - time_s) / 0.03))
            left = filtered * 0.008
            right = filtered * 0.008
            per_stem_lr = {name: [0.0, 0.0] for name in stem_buffers}

            for start, length, freq, inst, amp, gl, gr in parsed_cues:
                local = time_s - start
                if 0.0 <= local < length:
                    sig = amp * _voice_sample(inst, local, length, freq, filtered * 4.0)
                    sl, sr = sig * gl, sig * gr
                    left += sl
                    right += sr
                    if want_stems:
                        per_stem_lr[inst][0] += sl
                        per_stem_lr[inst][1] += sr

            left *= envelope
            right *= envelope
            peak = max(peak, abs(left), abs(right))
            square_sum += 0.5 * (left * left + right * right)
            if max(abs(left), abs(right)) > 0.99:
                raise ValueError('Audio cues overlap above safe sample peak; reduce audio.gain_db')
            s_l = max(-32768, min(32767, round(left * 32767)))
            s_r = max(-32768, min(32767, round(right * 32767)))
            chunk.extend(struct.pack('<hh', s_l, s_r))
            if want_stems:
                for name, (stl, str_) in per_stem_lr.items():
                    sl_i = max(-32768, min(32767, round(stl * envelope * 32767)))
                    sr_i = max(-32768, min(32767, round(str_ * envelope * 32767)))
                    stem_buffers[name].extend(struct.pack('<hh', sl_i, sr_i))
            if len(chunk) >= 65536:
                stream.writeframesraw(chunk)
                chunk.clear()
        stream.writeframes(chunk)

    written_stems = []
    if want_stems and stem_dir is not None:
        stem_dir.mkdir(parents=True, exist_ok=True)
        for name, pcm_bytes in stem_buffers.items():
            stem_path = stem_dir / f'stem-{name}.wav'
            with wave.open(str(stem_path), 'wb') as s_out:
                s_out.setparams((2, 2, rate, 0, 'NONE', 'not compressed'))
                s_out.writeframes(pcm_bytes)
            written_stems.append(stem_path.name)

    return {
        'sample_rate': rate,
        'channels': 2,
        'samples': samples,
        'sample_peak_dbfs': 20 * math.log10(peak) if peak else None,
        'rms_dbfs': 10 * math.log10(square_sum / samples) if square_sum else None,
        'duration_rational': str(duration),
        'stems': written_stems,
        'content': 'deterministic multi-instrument stereo procedural audio; no voice or music track',
    }
