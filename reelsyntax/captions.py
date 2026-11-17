from fractions import Fraction
from pathlib import Path
import tempfile

from ReelSyntax_Skills.tools.registry import contained_path, read_json
from .media import executable, local_input_args, run
from .project import fields, integer, load, text
from .skills import file_digest


def caption_events(plan, words):
    total = sum(scene['duration_frames'] for scene in plan['scenes'])
    if words is not None:
        if not isinstance(words, list) or not 1 <= len(words) <= 50000:
            raise ValueError('Expected a nonempty word timing table')
        previous = 0
        for word in words:
            fields(word, {'start', 'end', 'text'}, {'start', 'end', 'text'}, 'caption')
            integer(word['start'], previous, total - 1, 'caption.start')
            integer(word['end'], word['start'] + 1, total, 'caption.end')
            text(word['text'], 'caption.text', 160)
            previous = word['end']
            yield word['start'], word['end'], word['text']
        return
    cursor = 0
    for scene in plan['scenes']:
        duration = scene['duration_frames']
        value = ' '.join(scene['params'].get(k, '') for k in ('heading', 'subheading')).strip()
        if value:
            yield cursor, cursor + duration, value
        cursor += duration


def burn(project, profile, style, timing_file):
    root, plan, metadata = load(project)
    if plan.get('constraints', {}).get('no_text'):
        raise ValueError('no_text conflicts with burned captions')
    master = contained_path(root, f'output/{profile}.mp4')
    record = read_json(contained_path(root, f'output/{profile}-manifest.json'))
    from .ingest import verify_sources

    verify_sources(root, record)
    if record['plan_sha256'] != metadata['plan_sha256'] or record['artifact_sha256'] != file_digest(master):
        raise ValueError('Render the current project before burning captions')
    if style == 'word-pop' and not timing_file:
        raise ValueError('word-pop requires --words with actual word timings')
    words = read_json(contained_path(root, timing_file)) if timing_file else None
    events = list(caption_events(plan, words))
    if not events:
        raise ValueError('No caption text on this timeline')
    fps = Fraction(plan['output']['fps'])

    def stamp(frame):
        cs = round(Fraction(frame * 100, 1) / fps)
        return f'{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}'

    width, height = (record['output_settings'][k] for k in ('width', 'height'))
    size = max(12, round(height * 0.055))
    body = [
        f'[Script Info]\nScriptType: v4.00+\nPlayResX: {width}\nPlayResY: {height}\n[V4+ Styles]',
        'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
        f'Style: Caption,Arial,{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,16,16,{height // 12},1',
        '[Events]',
        'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text',
    ]
    for start, end, value in events:
        if any(char in value for char in '{}\\'):
            raise ValueError('Caption braces and ASS escape sequences require literal-text conversion')
        effect = r'{\fscx85\fscy85\t(0,80,\fscx100\fscy100)}' if style == 'word-pop' else ''
        body.append(f'Dialogue: 0,{stamp(start)},{stamp(end)},Caption,,0,0,0,,{effect}{value}')
    target = contained_path(root, f'output/{profile}-captioned.mp4', must_exist=False)
    with tempfile.TemporaryDirectory(dir=target.parent) as temp:
        Path(temp, 'captions.ass').write_text('\n'.join(body) + '\n', encoding='utf-8')
        run(
            [
                executable('ffmpeg'),
                '-nostdin',
                '-v',
                'error',
                *local_input_args(master),
                '-i',
                master,
                '-vf',
                'ass=captions.ass',
                '-c:v',
                'libx264',
                '-threads',
                '2',
                '-c:a',
                'copy',
                'result.mp4',
            ],
            cwd=temp,
        )
        Path(temp, 'result.mp4').replace(target)
    return {'artifact': target.relative_to(root).as_posix(), 'caption_count': len(events)}
