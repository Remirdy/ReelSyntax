import base64
from collections import deque
from fractions import Fraction
from html import escape
import json
from pathlib import Path
import tempfile

from .media import executable, run


def motion_checks(artifact, fps, frames, loop=False):
    from PIL import Image, ImageChops, ImageStat

    width, height = 16, 9
    size = width * height * 3
    changes = deque()
    flagged = []
    first = previous = None
    last_direction = 0
    with tempfile.TemporaryDirectory() as directory:
        samples = Path(directory) / 'samples.rgb'
        run(
            [
                executable('ffmpeg'),
                '-v',
                'error',
                '-nostdin',
                '-i',
                artifact,
                '-map',
                '0:v:0',
                '-vf',
                f'scale={width}:{height}:flags=area',
                '-fps_mode',
                'passthrough',
                '-an',
                '-pix_fmt',
                'rgb24',
                '-f',
                'rawvideo',
                samples,
            ]
        )
        if samples.stat().st_size != frames * size:
            raise ValueError('Unexpected number of decoded frames during motion review')
        with samples.open('rb') as stream:
            for index in range(frames):
                current = Image.frombytes('RGB', (width, height), stream.read(size))
                if first is None:
                    first = current
                if previous is not None:
                    a, b = previous.convert('L'), current.convert('L')
                    histogram = ImageChops.subtract(b, a).histogram()
                    reverse = ImageChops.subtract(a, b).histogram()
                    direction = (
                        1
                        if sum(histogram[26:]) >= width * height / 4
                        else -1
                        if sum(reverse[26:]) >= width * height / 4
                        else 0
                    )
                    if direction and direction != last_direction:
                        changes.append(index)
                        last_direction = direction
                    while changes and index - changes[0] >= fps:
                        changes.popleft()
                    if len(changes) >= 7 and (not flagged or index - flagged[-1] >= fps):
                        flagged.append(index)
                previous = current
    checks = [
        {
            'id': 'flash_screening',
            'status': 'review' if flagged else 'pass',
            'observed': {'flagged_frames': flagged},
            'expected': 'Review repeated opposing luma changes across a quarter of the sampled picture. This screen does not certify photosensitivity safety.',
        }
    ]
    if loop:
        delta = sum(ImageStat.Stat(ImageChops.difference(first, previous)).mean) / 3
        checks.append(
            {
                'id': 'loop_picture',
                'status': 'review' if delta > 8 else 'pass',
                'observed': round(delta, 3),
                'expected': 'Mean endpoint RGB difference at most 8/255 on a 16 by 9 sample',
            }
        )
    return checks


def html_report(report, filmstrip):
    def cell(value):
        return escape(json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value)

    title = 'Quality report · ' + escape(report['profile'])
    rows = ''.join(
        '<tr>'
        + ''.join('<td>' + cell(check[key]) + '</td>' for key in ('id', 'status', 'observed', 'expected'))
        + '</tr>'
        for check in report['checks']
    )
    image = base64.b64encode(filmstrip.read_bytes()).decode('ascii')
    return (
        f'<!doctype html><html lang="en"><meta charset="utf-8"><title>{title}</title>'
        '<style>body{font:1rem system-ui;margin:2rem auto;max-width:70rem;padding:1rem}img{max-width:100%}table{border-collapse:collapse}th,td{text-align:left;vertical-align:top;padding:.5rem;border-bottom:1px solid #ccc;overflow-wrap:anywhere}</style>'
        f'<h1>{title}</h1><p>{cell(report["artifact"])} · {cell(report["technical_status"])}</p><img alt="Sampled scene frames" src="data:image/png;base64,{image}">'
        f'<table><thead><tr><th>Check<th>Status<th>Observed<th>Expected</thead><tbody>{rows}</tbody></table></html>'
    )


def audio_onsets(path, fps, emit):
    from array import array
    import math
    import sys
    import wave

    fps = Fraction(fps)
    if not 1 <= fps <= 120:
        raise ValueError('Expected a frame rate between 1 and 120')
    try:
        source = wave.open(str(path), 'rb')
    except (EOFError, wave.Error) as error:
        raise ValueError('Source must be a valid PCM WAV file') from error
    with source as stream:
        channels, rate = stream.getnchannels(), stream.getframerate()
        if stream.getsampwidth() != 2 or channels not in (1, 2):
            raise ValueError('Onset analysis requires mono or stereo 16-bit PCM WAV')
        window = max(1, round(rate * 0.01))
        frames = math.ceil(Fraction(stream.getnframes(), rate) * fps)
        position = 0
        baseline = 0.0
        hits = []
        while raw := stream.readframes(window):
            samples = array('h', raw)
            if sys.byteorder != 'little':
                samples.byteswap()
            rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples))
            frame = min(frames - 1, round(Fraction(position, rate) * fps))
            if rms > max(400, 2.4 * baseline) and (not hits or (frame - hits[-1]) / fps >= 0.08):
                hits.append(frame)
            baseline = 0.8 * baseline + 0.2 * rms
            position += len(samples) // channels
    result = {'frames': frames, 'fps': str(fps), 'onset_frames': hits}
    if emit:
        result['cues'] = [
            {'frame': frame, 'duration_frames': 1, 'frequency': 880, 'instrument': 'click_transient'}
            for frame in hits
        ]
    return result
