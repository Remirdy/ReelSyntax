from fractions import Fraction
import json
from pathlib import Path
import tempfile

from .gateway import discover_blender_binary
from .media import run

BLENDER_SCRIPT = r"""
import json, math, os, sys
import bpy
from mathutils import Vector

cfg_path = sys.argv[sys.argv.index('--') + 1]
cfg = json.loads(open(cfg_path, 'r', encoding='utf-8').read())

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# Instance-level engine & OCIO AgX detection compatible with Blender 3.6–5.x.
want_cycles = cfg.get('profile') == 'hero'
if want_cycles:
    try:
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = 24
        scene.cycles.use_denoising = False
    except Exception:
        want_cycles = False
if not want_cycles:
    for eng in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
        try:
            scene.render.engine = eng
            break
        except Exception:
            pass
    if hasattr(scene.eevee, 'taa_render_samples'):
        scene.eevee.taa_render_samples = 16 if cfg.get('profile') == 'draft' else 32

for vt in ('AgX', 'Filmic', 'Standard'):
    try:
        scene.view_settings.view_transform = vt
        break
    except Exception:
        continue

scene.render.resolution_x = int(cfg['width'])
scene.render.resolution_y = int(cfg['height'])
scene.render.resolution_percentage = 100
scene.render.fps = int(cfg['fps_num'])
scene.render.fps_base = float(cfg['fps_den'])
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'

def srgb_to_lin(hex_color):
    h = hex_color.lstrip('#')
    vals = [int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4)]
    return [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in vals]

bg_lin = srgb_to_lin(cfg['background'])
fg_lin = srgb_to_lin(cfg['foreground'])
ac_lin = srgb_to_lin(cfg['accent'])

world = bpy.data.worlds.new('RSWorld')
scene.world = world
world.use_nodes = True
bg_node = world.node_tree.nodes.get('Background')
if bg_node:
    bg_node.inputs[0].default_value = (*bg_lin, 1.0)
    bg_node.inputs[1].default_value = 0.85

def make_mat(name, rgb, rough=0.32, metal=0.18):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (*rgb, 1.0)
        bsdf.inputs['Roughness'].default_value = rough
        if 'Metallic' in bsdf.inputs:
            bsdf.inputs['Metallic'].default_value = metal
    return mat

mat_ground = make_mat('RS_Ground', [c * 0.92 for c in bg_lin], rough=0.72, metal=0.0)
mat_primary = make_mat('RS_Primary', fg_lin, rough=0.28, metal=0.35)
mat_accent = make_mat('RS_Accent', ac_lin, rough=0.22, metal=0.45)

bpy.ops.mesh.primitive_plane_add(size=16.0, location=(0.0, 0.0, -0.78))
plane = bpy.context.active_object
plane.data.materials.append(mat_ground)

slabs = []
for idx in range(4):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.45, 0.0, -0.35 + idx * 0.34))
    obj = bpy.context.active_object
    obj.scale = (0.64 - idx * 0.07, 0.44 - idx * 0.04, 0.12)
    bpy.ops.object.modifier_add(type='BEVEL')
    obj.modifiers['Bevel'].width = 0.02
    obj.modifiers['Bevel'].segments = 2
    obj.data.materials.append(mat_accent if idx == 2 else mat_primary)
    slabs.append(obj)

bpy.ops.mesh.primitive_torus_add(major_radius=0.92, minor_radius=0.035, location=(0.45, 0.0, 0.18))
ring = bpy.context.active_object
ring.data.materials.append(mat_accent)

def point_at(obj, target):
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()

for lname, energy, loc in [
    ('Key', 220.0, (2.8, -3.0, 3.2)),
    ('Fill', 85.0, (-3.2, -2.0, 1.8)),
    ('Rim', 160.0, (-0.8, 3.2, 2.4)),
]:
    ldata = bpy.data.lights.new(lname, 'AREA')
    ldata.energy = energy
    ldata.size = 2.2
    lobj = bpy.data.objects.new(lname, ldata)
    scene.collection.objects.link(lobj)
    lobj.location = loc
    point_at(lobj, (0.45, 0.0, 0.1))

cdata = bpy.data.cameras.new('RSCam')
cdata.lens = float(cfg.get('focal_mm', 52.0))
cdata.sensor_width = 36.0
cam = bpy.data.objects.new('RSCam', cdata)
scene.collection.objects.link(cam)
scene.camera = cam

frames = int(cfg['frames'])
out_dir = cfg['out_dir']
preset = cfg.get('camera_preset', 'locked')

for f in range(frames):
    u = f / max(1, frames - 1)
    s = u * u * (3.0 - 2.0 * u)
    for idx, obj in enumerate(slabs):
        obj.rotation_euler = (0.04 * math.cos(u * math.tau + idx), 0.0, 0.28 + idx * 0.2 + 0.32 * math.sin(u * math.pi + idx * 0.4))
        obj.location.z = -0.35 + idx * 0.34 + 0.04 * math.sin(u * math.tau + idx)
    ring.rotation_euler = (0.42 + 0.18 * math.sin(u * math.tau), 0.22, u * math.pi)
    if preset == 'orbit':
        ang = -0.28 + 0.56 * s
        cam.location = (0.45 + 4.2 * math.sin(ang), -4.2 * math.cos(ang), 1.35)
    elif preset == 'dolly_in':
        k = 1.0 - 0.16 * s
        cam.location = (0.45 + 1.5 * k, -4.1 * k, 1.35 * k)
    else:
        cam.location = (1.85, -4.05, 1.35)
    point_at(cam, (0.1, 0.0, 0.12))
    scene.render.filepath = os.path.join(out_dir, f'{f:06d}.png')
    bpy.ops.render.render(write_still=True)
"""


def render_blender_scene(scene: dict, output: dict, profile: str, destination_dir: Path, timeout: int = 180) -> tuple[dict, list[dict]]:
    from PIL import Image, ImageDraw
    from .drawing import apply_typography_and_hud

    bl_info = discover_blender_binary()
    if not bl_info['available']:
        raise ValueError("Blender executable is unavailable; install Blender, set REELSYNTAX_BLENDER, or pass '--fallback pillow'")

    fps = Fraction(output['fps'])
    params = scene.get('params', {})
    cam_cfg = scene.get('camera') or {}
    payload = {
        'width': output['width'],
        'height': output['height'],
        'fps_num': fps.numerator,
        'fps_den': fps.denominator,
        'frames': scene['duration_frames'],
        'profile': profile,
        'background': params.get('background', '#181d21' if scene['recipe'] == 'aperture' else '#16191e'),
        'foreground': params.get('foreground', '#20262a' if scene['recipe'] == 'aperture' else '#ece8df'),
        'accent': params.get('accent', '#bd9a66' if scene['recipe'] == 'aperture' else '#c8643b'),
        'focal_mm': cam_cfg.get('focal_mm', 52.0),
        'camera_preset': cam_cfg.get('preset', 'locked'),
        'out_dir': str(destination_dir),
        'shot': params.get('shot', 'hero'),
    }
    if scene['recipe'] == 'aperture':
        payload['samples'] = params.get('samples', 20 if profile == 'draft' else 48)
        payload['focal_mm'] = cam_cfg.get('focal_mm', {'macro': 85, 'iris': 91, 'assembly': 53, 'hero': 57}[payload['shot']])
        payload['camera_position'] = cam_cfg.get('position')
        payload['camera_target'] = cam_cfg.get('target')

    with tempfile.TemporaryDirectory(prefix='rs-bl-') as tmp:
        tmp_path = Path(tmp)
        script_file = tmp_path / 'render_scene.py'
        cfg_file = tmp_path / 'config.json'
        if scene['recipe'] == 'aperture':
            script_file = Path(__file__).with_name('blender_aperture.py')
        else:
            script_file.write_text(BLENDER_SCRIPT, encoding='utf-8')
        cfg_file.write_text(json.dumps(payload), encoding='utf-8')
        run([bl_info['binary'], '--background', '--factory-startup', '--python-exit-code', '1', '--python', str(script_file), '--', str(cfg_file)], timeout=timeout)

    evidence = {}
    if scene['recipe'] == 'aperture':
        evidence_file = destination_dir / 'aperture-render.json'
        evidence = json.loads(evidence_file.read_text(encoding='utf-8'))
        evidence_file.unlink()

    layouts = []
    sample_frames = {0, scene['duration_frames'] // 2, scene['duration_frames'] - 1}
    for f in range(scene['duration_frames']):
        frame_file = destination_dir / f'{f:06d}.png'
        if not frame_file.is_file():
            raise ValueError(f'Blender rendered no output at frame {f}')
        with Image.open(frame_file) as im:
            rgb = im.convert('RGB')
        bounds = []
        if scene['recipe'] != 'aperture':
            canvas = ImageDraw.Draw(rgb)
            bounds = apply_typography_and_hud(canvas, scene, f, output['width'], output['height'], scale=1)
            rgb.save(frame_file)
        if f in sample_frames:
            layouts.append({'frame': f, 'text': bounds})
    return {'blender_version': bl_info['version'], 'render': evidence}, layouts
