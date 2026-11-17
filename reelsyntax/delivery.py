from fractions import Fraction
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

from .media import executable, local_input_args, run


def write_preview(source: Path, target: Path, fmt: str, frame: int) -> None:
    if source.resolve() == target.resolve():
        raise ValueError('Choose a destination separate from the rendered master')
    if fmt == 'gif':
        filters = 'fps=12,scale=min(640\\,iw):-2:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse'
        options = ['-filter_complex', filters, '-loop', '0', '-f', 'gif']
    elif fmt == 'webm':
        options = [
            '-map',
            '0:v:0',
            '-map',
            '0:a?',
            '-c:v',
            'libvpx-vp9',
            '-crf',
            '34',
            '-b:v',
            '0',
            '-c:a',
            'libopus',
            '-f',
            'webm',
        ]
    else:
        options = ['-vf', f'select=eq(n\\,{frame})', '-frames:v', '1', '-c:v', 'png', '-f', 'image2']
    with tempfile.TemporaryDirectory(dir=target.parent) as temporary:
        result = Path(temporary) / ('preview.png' if fmt == 'poster' else 'preview.' + fmt)
        run(
            [
                executable('ffmpeg'),
                '-nostdin',
                '-v',
                'error',
                *local_input_args(source),
                '-i',
                source,
                *options,
                result,
            ]
        )
        if not result.is_file() or not result.stat().st_size:
            raise ValueError('Encoder produced no preview')
        result.replace(target)


def premiere_timeline(plan, metadata, master_uri, settings):
    fps = Fraction(plan['output']['fps'])
    timebase = round(fps)
    if fps not in (timebase, Fraction(timebase * 1000, 1001)):
        raise ValueError('Premiere XML requires integer or NTSC frame rate')

    def field(parent, key, value):
        ET.SubElement(parent, key).text = str(value)

    def rate(parent):
        node = ET.SubElement(parent, 'rate')
        field(node, 'timebase', timebase)
        field(node, 'ntsc', 'TRUE' if fps != timebase else 'FALSE')

    xml = ET.Element('xmeml', version='5')
    sequence = ET.SubElement(xml, 'sequence', id='sequence-1')
    field(sequence, 'name', plan['id'])
    field(sequence, 'duration', metadata['frames'])
    rate(sequence)
    media = ET.SubElement(sequence, 'media')
    video = ET.SubElement(media, 'video')
    description = ET.SubElement(ET.SubElement(video, 'format'), 'samplecharacteristics')
    rate(description)
    for key in ('width', 'height'):
        field(description, key, settings[key])
    tracks = [('video', 1, ET.SubElement(video, 'track'))]
    if plan['audio']['enabled']:
        audio = ET.SubElement(media, 'audio')
        for channel in (1, 2):
            tracks.append(('audio', channel, ET.SubElement(audio, 'track')))
    for media_type, channel, track in tracks:
        start = 0
        for index, scene in enumerate(plan['scenes']):
            end = start + scene['duration_frames']
            clip = ET.SubElement(track, 'clipitem', id=f'{media_type}-{channel}-{index}')
            field(clip, 'name', scene['id'])
            rate(clip)
            for key, value in [('start', start), ('end', end), ('in', start), ('out', end)]:
                field(clip, key, value)
            file = ET.SubElement(clip, 'file', id='master-1')
            if media_type == 'video' and index == 0:
                field(file, 'name', plan['id'])
                field(file, 'pathurl', master_uri)
                rate(file)
                field(file, 'duration', metadata['frames'])
                streams = ET.SubElement(file, 'media')
                ET.SubElement(streams, 'video').append(ET.fromstring(ET.tostring(description)))
                if plan['audio']['enabled']:
                    field(ET.SubElement(streams, 'audio'), 'channelcount', 2)
            source = ET.SubElement(clip, 'sourcetrack')
            field(source, 'mediatype', media_type)
            field(source, 'trackindex', channel)
            start = end
    ET.indent(xml)
    return ET.tostring(xml, encoding='unicode', xml_declaration=True) + '\n'
