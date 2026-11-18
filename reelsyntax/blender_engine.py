from fractions import Fraction
import json
from pathlib import Path
import tempfile
from typing import Any

from .gateway import discover_blender_binary
from .media import run

SUPPORTED_BLENDER_RECIPES = frozenset({
    'prism-monolith',
    'cinematic-3d',
    'stepped-clay',
    'paper-cutout',
    'character-stage',
    'aperture',
    'cassette',
})

BLENDER_SCRIPT = r"""
import json, math, os, sys
import bpy
from mathutils import Vector

cfg_path = sys.argv[sys.argv.index('--') + 1]
cfg = json.loads(open(cfg_path, 'r', encoding='utf-8').read())

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
recipe = cfg.get('recipe', 'prism-monolith')
reduced_motion = bool(cfg.get('reduced_motion', False))

want_cycles = cfg.get('profile') == 'hero'
if want_cycles:
    try:
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = int(cfg.get('samples', 24))
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
if recipe == 'stepped-clay':
    scene.render.use_motion_blur = False

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

def make_mat(name, rgb, rough=0.32, metal=0.18, sss=0.0, bump_scale=0.0, bump_strength=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (*rgb, 1.0)
        bsdf.inputs['Roughness'].default_value = rough
        if 'Metallic' in bsdf.inputs:
            bsdf.inputs['Metallic'].default_value = metal
        if sss > 0.0:
            for key in ('Subsurface Weight', 'Subsurface'):
                if key in bsdf.inputs:
                    bsdf.inputs[key].default_value = sss
            if 'Subsurface Scale' in bsdf.inputs:
                bsdf.inputs['Subsurface Scale'].default_value = 0.0025
        if bump_strength > 0.0:
            tex = nt.nodes.new('ShaderNodeTexNoise')
            tex.inputs['Scale'].default_value = bump_scale
            tex.inputs['Detail'].default_value = 4.0
            bump = nt.nodes.new('ShaderNodeBump')
            bump.inputs['Strength'].default_value = bump_strength
            bump.inputs['Distance'].default_value = 0.015
            nt.links.new(tex.outputs['Fac'], bump.inputs['Height'])
            nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    return mat

def point_at(obj, target):
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()

focus_target = bpy.data.objects.new('RSFocusTarget', None)
scene.collection.objects.link(focus_target)
focus_target.location = (0.45, 0.0, 0.12)

cdata = bpy.data.cameras.new('RSCam')
cdata.lens = float(cfg.get('focal_mm', 52.0))
cdata.sensor_width = 36.0
if recipe in ('cinematic-3d', 'stepped-clay'):
    cdata.dof.use_dof = True
    cdata.dof.focus_object = focus_target
    cdata.dof.aperture_fstop = float(cfg.get('dof_fstop', 4.0))
cam = bpy.data.objects.new('RSCam', cdata)
scene.collection.objects.link(cam)
scene.camera = cam

frames = int(cfg['frames'])
out_dir = cfg['out_dir']
preset = 'locked' if reduced_motion else cfg.get('camera_preset', 'locked')

if recipe == 'stepped-clay':
    mat_ground = make_mat('RS_ClayGround', [c * 0.94 for c in bg_lin], rough=0.84, metal=0.0)
    mat_clay_p = make_mat('RS_ClayPrimary', fg_lin, rough=0.72, metal=0.0, sss=0.22, bump_scale=18.0, bump_strength=0.06)
    mat_clay_a = make_mat('RS_ClayAccent', ac_lin, rough=0.70, metal=0.0, sss=0.24, bump_scale=22.0, bump_strength=0.06)
    bpy.ops.mesh.primitive_plane_add(size=14.0, location=(0.0, 0.0, -0.72))
    bpy.context.active_object.data.materials.append(mat_ground)

    clay_parts = []
    specs = [
        ('primitive_cylinder_add', (0.45, 0.0, -0.35), (0.52, 0.52, 0.28), mat_clay_p),
        ('primitive_uv_sphere_add', (0.45, 0.0, 0.05), (0.44, 0.42, 0.36), mat_clay_a),
        ('primitive_uv_sphere_add', (0.45, 0.0, 0.46), (0.28, 0.28, 0.24), mat_clay_p),
        ('primitive_uv_sphere_add', (1.05, 0.0, 0.16), (0.16, 0.16, 0.16), mat_clay_a),
    ]
    for op_name, loc, scale, mat in specs:
        getattr(bpy.ops.mesh, op_name)(location=loc)
        obj = bpy.context.active_object
        obj.scale = scale
        obj.data.materials.append(mat)
        clay_parts.append((obj, loc))

    for lname, energy, loc, sz in [
        ('Key', 260.0, (2.2, -2.6, 3.0), 3.0),
        ('Fill', 95.0, (-3.0, -2.0, 1.8), 2.8),
        ('Rim', 155.0, (-0.6, 3.0, 2.2), 2.0),
    ]:
        ldata = bpy.data.lights.new(lname, 'AREA')
        ldata.energy = energy
        ldata.size = sz
        lobj = bpy.data.objects.new(lname, ldata)
        scene.collection.objects.link(lobj)
        lobj.location = loc
        point_at(lobj, (0.45, 0.0, 0.1))

    pose_step = max(2, int(cfg.get('pose_step', 3)))
    for f in range(frames):
        qf = min(frames - 1, (f // pose_step) * pose_step)
        u = qf / max(1, frames - 1)
        amp = 0.25 if reduced_motion else 1.0
        for idx, (obj, base_loc) in enumerate(clay_parts):
            phase = u * math.tau + idx * 0.9
            obj.location = (base_loc[0] + 0.05 * amp * math.cos(phase), base_loc[1] + 0.04 * amp * math.sin(phase), base_loc[2] + 0.06 * amp * math.sin(phase))
            obj.rotation_euler = (0.08 * amp * math.sin(phase), 0.0, 0.35 * amp * math.sin(u * math.pi + idx * 0.4))
            obj.keyframe_insert(data_path='location', frame=f + 1)
        if preset == 'dolly_in':
            k = 1.0 - 0.14 * (u * u * (3.0 - 2.0 * u))
            cam.location = (0.45 + 1.45 * k, -3.9 * k, 1.25 * k)
        elif preset == 'orbit':
            ang = -0.22 + 0.44 * (u * u * (3.0 - 2.0 * u))
            cam.location = (0.45 + 4.0 * math.sin(ang), -4.0 * math.cos(ang), 1.28)
        else:
            cam.location = (1.75, -3.9, 1.28)
        point_at(cam, (0.12, 0.0, 0.12))
        scene.render.filepath = os.path.join(out_dir, f'{f:06d}.png')
        bpy.ops.render.render(write_still=True)

    for obj, _ in clay_parts:
        act = obj.animation_data.action if obj.animation_data else None
        if act is not None and hasattr(act, 'fcurves'):
            for fc in act.fcurves:
                mod = fc.modifiers.new(type='STEPPED')
                mod.frame_step = pose_step

elif recipe == 'paper-cutout':
    mat_back = make_mat('RS_PaperBack', bg_lin, rough=0.90, metal=0.0)
    mat_mid = make_mat('RS_PaperMid', [0.55 * bg_lin[i] + 0.45 * fg_lin[i] for i in range(3)], rough=0.88, metal=0.0)
    mat_fg = make_mat('RS_PaperAccent', ac_lin, rough=0.86, metal=0.0)

    bpy.ops.mesh.primitive_plane_add(size=18.0, location=(0.0, 1.6, 0.0), rotation=(math.pi * 0.5, 0.0, 0.0))
    bpy.context.active_object.data.materials.append(mat_back)

    planes = []
    for idx, (loc, scale, mat) in enumerate([
        ((0.65, 1.15, 0.05), (1.35, 1.45, 1.0), mat_mid),
        ((0.55, 0.78, -0.22), (1.25, 0.65, 1.0), mat_mid),
        ((0.72, 0.42, 0.18), (0.58, 0.58, 1.0), mat_fg),
    ]):
        bpy.ops.mesh.primitive_plane_add(size=1.0, location=loc, rotation=(math.pi * 0.5, 0.0, 0.0))
        obj = bpy.context.active_object
        obj.scale = scale
        mod = obj.modifiers.new(name='Thickness', type='SOLIDIFY')
        mod.thickness = 0.014
        obj.data.materials.append(mat)
        planes.append((obj, loc))

    ldata = bpy.data.lights.new('PaperSun', 'AREA')
    ldata.energy = 320.0
    ldata.size = 1.6
    lobj = bpy.data.objects.new('PaperSun', ldata)
    scene.collection.objects.link(lobj)
    lobj.location = (-2.2, -2.6, 2.8)
    point_at(lobj, (0.6, 0.7, 0.0))

    fill = bpy.data.lights.new('PaperFill', 'AREA')
    fill.energy = 110.0
    fill.size = 4.0
    fobj = bpy.data.objects.new('PaperFill', fill)
    scene.collection.objects.link(fobj)
    fobj.location = (1.8, -3.0, 0.8)
    point_at(fobj, (0.6, 0.7, 0.0))

    for f in range(frames):
        u = f / max(1, frames - 1)
        drift = 0.0 if reduced_motion or preset == 'locked' else 0.16 * math.sin(u * math.tau)
        cam.location = (0.15 + drift, -4.1, 0.12)
        point_at(cam, (0.15, 0.7, 0.08))
        scene.render.filepath = os.path.join(out_dir, f'{f:06d}.png')
        bpy.ops.render.render(write_still=True)

elif recipe == 'character-stage':
    mat_ground = make_mat('RS_Ground', [c * 0.92 for c in bg_lin], rough=0.72, metal=0.0)
    bpy.ops.mesh.primitive_plane_add(size=16.0, location=(0.0, 0.0, -0.78))
    plane = bpy.context.active_object
    plane.data.materials.append(mat_ground)

    repo_root = cfg.get('repo_root')
    if repo_root and repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    from reelsyntax.character import blink_aperture, build_blender_character, get_character_preset
    char_id = cfg.get('character', 'scout')
    shot_role = cfg.get('shot_role', 'speaker_a')
    char_pos = cfg.get('character_pos', 'duo' if shot_role in ('establishing', 'two_shot') else ('right' if shot_role == 'speaker_b' else 'left'))
    char_objs = []
    if char_pos == 'duo' or shot_role in ('establishing', 'two_shot'):
        p_a = get_character_preset(char_id)
        p_b = get_character_preset(cfg.get('partner_character', 'archivist'))
        o_a = build_blender_character(char_id, expression=cfg.get('expression', 'neutral'), mouth_open=(cfg.get('mouth_envelope') or [0.0])[0], blink_open=blink_aperture(0, blink_period=p_a['blink_period'], blink_offset=p_a['blink_offset']), yaw_deg=24.0, location=(-0.9, 0.0, 0.0), scale=0.9, name_prefix='RS_A', bpy_module=bpy)
        o_b = build_blender_character(cfg.get('partner_character', 'archivist'), expression=cfg.get('partner_expression', 'neutral'), mouth_open=0.0, blink_open=blink_aperture(0, blink_period=p_b['blink_period'], blink_offset=p_b['blink_offset']), yaw_deg=-24.0, location=(0.9, 0.0, 0.0), scale=0.9, name_prefix='RS_B', bpy_module=bpy)
        char_objs = [o for o in (o_a, o_b) if o is not None]
    else:
        cx = -0.55 if char_pos == 'left' else (0.55 if char_pos == 'right' else 0.0)
        yaw = 22.0 if char_pos == 'left' else (-22.0 if char_pos == 'right' else 0.0)
        p_a = get_character_preset(char_id)
        o_a = build_blender_character(char_id, expression=cfg.get('expression', 'neutral'), mouth_open=(cfg.get('mouth_envelope') or [0.0])[0], blink_open=blink_aperture(0, blink_period=p_a['blink_period'], blink_offset=p_a['blink_offset']), yaw_deg=yaw, location=(cx, 0.0, 0.0), scale=1.0, name_prefix='RS_A', bpy_module=bpy)
        if o_a is not None:
            char_objs = [o_a]

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
        point_at(lobj, (0.0, 0.0, 0.28))

    for f in range(frames):
        u = f / max(1, frames - 1)
        s = u * u * (3.0 - 2.0 * u)
        for idx, cobj in enumerate(char_objs):
            cobj.location.z = 0.02 * math.sin(u * math.tau + idx)
        if preset == 'dolly_in':
            k = 1.0 - 0.14 * s
            cam.location = (0.0, -3.55 * k, 0.36)
        else:
            cam.location = (0.0, -3.55, 0.36)
        point_at(cam, (0.0, 0.0, 0.24))
        scene.render.filepath = os.path.join(out_dir, f'{f:06d}.png')
        bpy.ops.render.render(write_still=True)

else:
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

    for f in range(frames):
        u = 0.0 if reduced_motion else f / max(1, frames - 1)
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
        elif preset == 'crane_rise':
            cam.location = (1.75, -4.05, 1.0 + 0.65 * s)
        else:
            cam.location = (1.85, -4.05, 1.35)
        point_at(cam, (0.1, 0.0, 0.12))
        scene.render.filepath = os.path.join(out_dir, f'{f:06d}.png')
        bpy.ops.render.render(write_still=True)
"""


def probe_blender_scene_support(scene: dict[str, Any] | None = None) -> dict[str, Any]:
    bl_info = discover_blender_binary()
    recipe = scene.get('recipe') if isinstance(scene, dict) else None
    native_supported = recipe in SUPPORTED_BLENDER_RECIPES if recipe else True
    fallback_available = recipe not in {'aperture', 'cassette'}
    return {
        'blender_available': bool(bl_info.get('available')),
        'binary': bl_info.get('binary'),
        'version': bl_info.get('version'),
        'recipe': recipe,
        'native_bpy_supported': native_supported,
        'pillow_fallback_available': fallback_available,
        'recommended_engine': 'blender' if (bl_info.get('available') and native_supported) else 'pillow',
    }


def build_blender_scene_payload(
    scene: dict[str, Any],
    output: dict[str, Any],
    profile: str,
    destination_dir: Path,
    *,
    reduced_motion: bool = False,
) -> dict[str, Any]:
    fps = Fraction(output['fps'])
    params = scene.get('params', {})
    cam_cfg = scene.get('camera') or {}
    recipe = scene['recipe']
    default_bg = '#181d21' if recipe == 'aperture' else ('#eee9df' if recipe == 'paper-cutout' else '#16191e')
    default_fg = '#20262a' if recipe == 'aperture' else ('#252925' if recipe == 'paper-cutout' else '#ece8df')
    default_ac = '#bd9a66' if recipe == 'aperture' else '#c8643b'
    payload: dict[str, Any] = {
        'recipe': recipe,
        'repo_root': str(Path(__file__).resolve().parents[1]),
        'width': output['width'],
        'height': output['height'],
        'fps_num': fps.numerator,
        'fps_den': fps.denominator,
        'frames': scene['duration_frames'],
        'profile': profile,
        'reduced_motion': bool(reduced_motion),
        'background': params.get('background', default_bg),
        'foreground': params.get('foreground', default_fg),
        'accent': params.get('accent', default_ac),
        'focal_mm': cam_cfg.get('focal_mm', 44.0 if recipe == 'character-stage' else 52.0),
        'camera_preset': 'locked' if reduced_motion else cam_cfg.get('preset', 'locked'),
        'out_dir': str(destination_dir),
        'shot': params.get('shot', 'hero'),
        'character': params.get('character', 'scout'),
        'partner_character': params.get('partner_character', 'archivist'),
        'expression': params.get('expression', 'neutral'),
        'partner_expression': params.get('partner_expression', 'neutral'),
        'shot_role': params.get('shot_role', 'speaker_a'),
        'character_pos': params.get('character_pos', 'left'),
        'mouth_envelope': params.get('mouth_envelope', []),
    }
    if recipe == 'cinematic-3d':
        payload['samples'] = params.get('samples', 16 if profile == 'draft' else 24)
        payload['dof_fstop'] = 4.0
    elif recipe == 'stepped-clay':
        payload['samples'] = params.get('samples', 16 if profile == 'draft' else 24)
        payload['dof_fstop'] = 5.6
        payload['pose_step'] = 2 if float(fps) <= 25.0 else 3
    elif recipe == 'cassette':
        payload.update(
            samples=params.get('samples', 16 if profile == 'draft' else 36),
            background=params.get('background', '#2e383a'),
            accent=params.get('accent', '#d8371e'),
        )
    elif recipe == 'aperture':
        payload['samples'] = params.get('samples', 20 if profile == 'draft' else 48)
        payload['focal_mm'] = cam_cfg.get('focal_mm', {'macro': 85, 'iris': 91, 'assembly': 53, 'hero': 57}[payload['shot']])
        payload['camera_position'] = cam_cfg.get('position')
        payload['camera_target'] = cam_cfg.get('target')
    return payload


def render_blender_scene(
    scene: dict[str, Any],
    output: dict[str, Any],
    profile: str,
    destination_dir: Path,
    timeout: int = 180,
    *,
    reduced_motion: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    from PIL import Image, ImageDraw
    from .drawing import apply_typography_and_hud

    bl_info = discover_blender_binary()
    if not bl_info['available']:
        raise ValueError("Blender executable is unavailable; install Blender, set REELSYNTAX_BLENDER, or pass '--fallback pillow'")

    payload = build_blender_scene_payload(scene, output, profile, destination_dir, reduced_motion=reduced_motion)

    with tempfile.TemporaryDirectory(prefix='rs-bl-') as tmp:
        tmp_path = Path(tmp)
        script_file = tmp_path / 'render_scene.py'
        cfg_file = tmp_path / 'config.json'
        if scene['recipe'] in ('aperture', 'cassette'):
            script_file = Path(__file__).with_name(f"blender_{scene['recipe']}.py")
        else:
            script_file.write_text(BLENDER_SCRIPT, encoding='utf-8')
        cfg_file.write_text(json.dumps(payload), encoding='utf-8')
        run([bl_info['binary'], '--background', '--factory-startup', '--python-exit-code', '1', '--python', str(script_file), '--', str(cfg_file)], timeout=timeout)

    evidence: dict[str, Any] = {}
    if scene['recipe'] in ('aperture', 'cassette'):
        evidence_file = destination_dir / f"{scene['recipe']}-render.json"
        evidence = json.loads(evidence_file.read_text(encoding='utf-8'))
        evidence_file.unlink()

    params = scene.get('params', {})
    layouts: list[dict[str, Any]] = []
    sample_frames = {0, scene['duration_frames'] // 2, scene['duration_frames'] - 1}
    for f in range(scene['duration_frames']):
        frame_file = destination_dir / f'{f:06d}.png'
        if not frame_file.is_file():
            raise ValueError(f'Blender rendered no output at frame {f}')
        with Image.open(frame_file) as im:
            rgb = im.convert('RGB')
        bounds: list[dict[str, Any]] = []
        if scene['recipe'] == 'character-stage':
            from .character import _draw_beveled_dialogue_hud
            canvas = ImageDraw.Draw(rgb)
            unit = min(output['width'] / 960.0, output['height'] / 540.0)
            u_val = f / max(1, scene['duration_frames'] - 1)
            speaker = str(params.get('speaker') or params.get('kicker') or '').strip()
            dialogue = str(params.get('dialogue') or params.get('subheading') or params.get('heading') or '').strip()
            bounds = _draw_beveled_dialogue_hud(
                canvas,
                w=output['width'],
                h=output['height'],
                unit=unit,
                scale=1,
                speaker=speaker,
                dialogue=dialogue,
                preset_id=str(params.get('character', 'scout')),
                u=u_val,
                background=payload['background'],
                foreground=payload['foreground'],
                accent=payload['accent'],
            )
            rgb.save(frame_file)
        elif scene['recipe'] not in ('aperture', 'cassette'):
            canvas = ImageDraw.Draw(rgb)
            bounds = apply_typography_and_hud(canvas, scene, f, output['width'], output['height'], scale=1)
            rgb.save(frame_file)
        if f in sample_frames:
            layouts.append({'frame': f, 'text': bounds})
    return {'blender_version': bl_info['version'], 'render': evidence}, layouts
