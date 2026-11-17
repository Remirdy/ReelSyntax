from array import array
from contextlib import ExitStack
from fractions import Fraction
import math
import os
import sys
import tempfile
import wave

from ReelSyntax_Skills.tools.registry import contained_path
from .media import executable, local_input_args, run


def _pcm(raw):
    values = array('h', raw)
    if sys.byteorder != 'little':
        values.byteswap()
    return values


def _encode(values):
    result = array('h', (round(max(-1, min(1, v)) * 32767) for v in values))
    if sys.byteorder != 'little':
        result.byteswap()
    return result.tobytes()


def mix_sources(root, path, plan, sound, stem_dir, timeout=180):
    fps, rate = Fraction(plan['output']['fps']), 48000
    sample_at = lambda frame: round(Fraction(frame * rate, 1) / fps)
    total = sound['samples']
    peak = squares = 0.0
    stems = []
    with tempfile.TemporaryDirectory(prefix='source-audio-', dir=path.parent) as tmp, ExitStack() as stack:
        base = stack.enter_context(wave.open(str(path), 'rb'))
        tracks = []
        for idx, track in enumerate(plan['audio']['tracks']):
            source = contained_path(root, track['source'])
            anchor = sample_at(track['start_frame'])
            start = sample_at(track.get('in_frame', 0))
            count = sample_at(track['start_frame'] + track['duration_frames']) - anchor
            decoded = os.path.join(tmp, f'{idx}.wav')
            run([
                executable('ffmpeg'), '-v', 'error', '-nostdin', '-y', *local_input_args(source), '-i', str(source), '-map', '0:a:0',
                '-af', f'aresample={rate},atrim=start_sample={start}:end_sample={start + count},asetpts=PTS-STARTPTS',
                '-ar', str(rate), '-ac', '2', '-c:a', 'pcm_s16le', decoded,
            ], timeout=timeout)
            stream = stack.enter_context(wave.open(decoded, 'rb'))
            if stream.getnframes() != count:
                raise ValueError(f"Audio source '{track['source']}' is too short for track '{track['id']}'")
            stem = None
            if plan['audio'].get('export_stems'):
                stem_dir.mkdir(parents=True, exist_ok=True)
                name = f"stem-source-{track['id']}.wav"
                stem = stack.enter_context(wave.open(str(stem_dir / name), 'wb'))
                stem.setparams((2, 2, rate, 0, 'NONE', 'not compressed'))
                stems.append(name)
            angle = (track.get('pan', 0) + 1) * math.pi / 4
            gain = 10 ** ((plan['audio']['gain_db'] + track.get('gain_db', 0)) / 20)
            tracks.append((track, stream, stem, anchor, count, gain * math.cos(angle) * math.sqrt(2), gain * math.sin(angle) * math.sqrt(2)))
        mixed = os.path.join(tmp, 'mix.wav')
        output = stack.enter_context(wave.open(mixed, 'wb'))
        output.setparams((2, 2, rate, 0, 'NONE', 'not compressed'))
        for cursor in range(0, total, 4096):
            count = min(4096, total - cursor)
            values = [v / 32768 for v in _pcm(base.readframes(count))]
            for track, stream, stem, anchor, length, gl, gr in tracks:
                contribution = [0.0] * (count * 2)
                first, last = max(cursor, anchor), min(cursor + count, anchor + length)
                if first < last:
                    local = first - anchor
                    stream.setpos(local)
                    samples = _pcm(stream.readframes(last - first))
                    fade_in = sample_at(track.get('fade_in_frames', 0))
                    fade_out = sample_at(track.get('fade_out_frames', 0))
                    for i in range(last - first):
                        envelope = min(1.0, (local + i) / fade_in if fade_in else 1.0, (length - 1 - local - i) / fade_out if fade_out else 1.0)
                        offset = (first - cursor + i) * 2
                        contribution[offset] = samples[2 * i] / 32768 * gl * envelope
                        contribution[offset + 1] = samples[2 * i + 1] / 32768 * gr * envelope
                values = [a + b for a, b in zip(values, contribution)]
                if max(abs(v) for v in contribution) > 0.99:
                    raise ValueError('Source audio stem exceeds safe sample peak; reduce track/master gain')
                if stem:
                    stem.writeframesraw(_encode(contribution))
            peak = max(peak, max(abs(v) for v in values))
            if peak > 0.99:
                raise ValueError('Source audio mix exceeds safe sample peak; reduce track/master gain')
            squares += sum(v * v for v in values)
            output.writeframesraw(_encode(values))
        stack.close()
        os.replace(mixed, path)
    return dict(sound, stems=[*sound['stems'], *stems], source_tracks=len(tracks), sample_peak_dbfs=20 * math.log10(peak) if peak else None, rms_dbfs=10 * math.log10(squares / (total * 2)) if squares else None, content=sound['content'] + '; frame-anchored local source tracks')
