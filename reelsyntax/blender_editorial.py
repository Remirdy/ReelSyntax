import json
from pathlib import Path
import sys
from urllib.parse import unquote, urlparse

import bpy


cfg = json.loads(Path(sys.argv[sys.argv.index('--') + 1]).read_text(encoding='utf-8'))
timeline = cfg['timeline']
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
sequence = scene.sequence_editor_create()
strips = sequence.strips if hasattr(sequence, 'strips') else sequence.sequences
output = timeline['metadata']['output_settings']
scene.render.resolution_x, scene.render.resolution_y = output['width'], output['height']
scene.render.resolution_percentage = 100
num, den = (int(v) for v in output['fps'].split('/'))
scene.render.fps = num if num <= 32767 else round(num / den)
scene.render.fps_base = den if num <= 32767 else scene.render.fps * den / num
scene.render.use_sequencer = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.view_settings.view_transform = 'Standard'
scene.view_settings.look = 'None'
scene.sequencer_colorspace_settings.name = 'sRGB'
scene.frame_start = 1
records = []


def local_file(reference):
    uri = urlparse(reference['target_url'])
    if uri.scheme != 'file' or uri.netloc:
        raise ValueError('Blender editorial export requires local file media URIs')
    path = unquote(uri.path)
    if sys.platform == 'win32' and path.startswith('/'):
        path = path[1:]
    if not Path(path).is_file():
        raise ValueError('Editorial media is missing: ' + path)
    return path


cursor = 0
for track in timeline['tracks']['children']:
    if track['kind'] == 'Video':
        for clip in track['children']:
            start = int(clip['source_range']['start_time']['value'])
            duration = int(clip['source_range']['duration']['value'])
            strip = strips.new_movie(clip['name'], local_file(clip['media_reference']), channel=1, frame_start=1)
            strip.frame_offset_start = start
            strip.frame_final_duration = duration
            strip.channel = 1
            records.append({'name': clip['name'], 'source_in': strip.frame_offset_start, 'timeline_in': strip.frame_final_start - 1, 'duration_frames': strip.frame_final_duration})
            for marker in clip.get('markers', []):
                scene.timeline_markers.new(marker['name'], frame=int(marker['marked_range']['start_time']['value']) + 1)
            cursor += duration
    elif track['kind'] == 'Audio':
        clip = track['children'][0]
        strip = strips.new_sound(track['name'], local_file(clip['media_reference']), channel=2, frame_start=1)
        strip.frame_final_duration = int(clip['source_range']['duration']['value'])
        for marker in clip.get('markers', []):
            scene.timeline_markers.new(marker['name'], frame=int(marker['marked_range']['start_time']['value']) + 1)

scene.frame_end = cursor
scene.frame_set(cfg['preview_frame'] + 1)
bpy.ops.wm.save_as_mainfile(filepath=cfg['destination'], check_existing=False)
bpy.ops.wm.open_mainfile(filepath=cfg['destination'])
scene = bpy.context.scene
scene.render.filepath = cfg['preview']
bpy.ops.render.render(write_still=True)
Path(cfg['report']).write_text(json.dumps({'blender_version': bpy.app.version_string, 'frames': cursor, 'frame_start': scene.frame_start, 'frame_end': scene.frame_end, 'fps': output['fps'], 'preview_frame': cfg['preview_frame'], 'clips': records}), encoding='utf-8')
