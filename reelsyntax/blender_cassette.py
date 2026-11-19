import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_aperture import area, linear, material, point_at


def solid(name, location, size, mat, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    for vertex in obj.data.vertices:
        for axis in range(3):
            vertex.co[axis] *= size[axis]
    if mat:
        obj.data.materials.append(mat)
    if bevel:
        edge = obj.modifiers.new('Edge radius', 'BEVEL')
        edge.width = bevel
        edge.segments = 5
        obj.modifiers.new('Surface normals', 'WEIGHTED_NORMAL')
    return obj


def round_plate(name, cx, cy, bottom, width, height, depth, radius, mat):
    outline = []
    for x, y, start in [(1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)]:
        for step in range(13):
            a = math.radians(start + step * 7.5)
            outline.append(
                (
                    cx + x * (width / 2 - radius) + radius * math.cos(a),
                    cy + y * (height / 2 - radius) + radius * math.sin(a),
                )
            )
    n = len(outline)
    vertices = [(x, y, z) for z in (bottom, bottom + depth) for x, y in outline]
    faces = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
    faces.extend((i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    if mat:
        mesh.materials.append(mat)
    return obj


def ring(name, x, y, z, outer, inner, depth, mat, bevel=0.006):
    n = 96
    vertices = [
        (x + r * math.cos(i * math.tau / n), y + r * math.sin(i * math.tau / n), zz)
        for r, zz in [(outer, z), (outer, z + depth), (inner, z + depth), (inner, z)]
        for i in range(n)
    ]
    faces = [
        (j * n + i, j * n + (i + 1) % n, ((j + 1) % 4) * n + (i + 1) % n, ((j + 1) % 4) * n + i)
        for j in range(4)
        for i in range(n)
    ]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(mat)
    for i, p in enumerate(mesh.polygons):
        p.use_smooth = i // n in (0, 2)
    if bevel:
        edge = obj.modifiers.new('Rim chamfer', 'BEVEL')
        edge.width = bevel
        edge.segments = 3
        obj.modifiers.new('Face normals', 'WEIGHTED_NORMAL')
    return obj


def cut(obj, tool):
    mod = obj.modifiers.new('Milled opening', 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.object = tool
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(tool, do_unlink=True)


def label(name, body, x, y, z, height, mat, spacing=1):
    data = bpy.data.curves.new(name, 'FONT')
    data.body = body
    data.size = height
    data.space_character = spacing
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = (x, y, z)
    data.materials.append(mat)
    return obj


def build(cfg):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = cfg.get('samples', 32)
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 5
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.seed = cfg.get('seed', 42)
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        for backend in ('METAL', 'OPTIX', 'HIP', 'CUDA', 'ONEAPI'):
            try:
                prefs.compute_device_type = backend
                prefs.get_devices()
            except (TypeError, RuntimeError):
                continue
            if any(d.type == backend for d in prefs.devices):
                for device in prefs.devices:
                    device.use = device.type == backend
                scene.cycles.device = 'GPU'
                break
    except RuntimeError:
        pass
    scene.render.use_persistent_data = True
    scene.render.resolution_x = cfg['width']
    scene.render.resolution_y = cfg['height']
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    world = bpy.data.worlds.new('Studio ambient')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (0.28, 0.32, 0.37, 1)
    world.node_tree.nodes['Background'].inputs[1].default_value = 0.15
    scene.world = world
    shell = material('Graphite moulded ABS', '#31363a', 0.13, 0.34)
    insert = material('Recessed graphite', '#181c1f', 0.10, 0.42)
    ivory = material('Warm uncoated stock', '#e5dcc7', 0, 0.64)
    ink = material('Carbon ink', '#202426', 0.06, 0.45)
    orange = material('Vermilion ink', cfg.get('accent', '#e44928'), 0.05, 0.4)
    chrome = material('Nickel steel', '#c2c2bc', 0.93, 0.21)
    hubs = material('Natural acetal', '#e7dfcb', 0.10, 0.29)
    oxide = material('Ferric tape', '#503526', 0.51, 0.33)
    winding = material('Winding edges', '#89644c', 0.58, 0.29)
    shadow = material('Recess shadow', '#080b0d', 0, 0.51)
    stage = material('Studio surface', cfg.get('background', '#2e383a'), 0.21, 0.32)
    solid('Studio sweep', (0, 0, -0.14), (200, 200, 0.25), stage, 0.06)
    round_plate('Lower shell', 0, 0, 0, 4.38, 2.78, 0.16, 0.19, shell)
    round_plate('Case joint', 0, 0, 0.16, 4.36, 2.76, 0.032, 0.18, shadow)
    body = round_plate('Upper shell', 0, 0, 0.192, 4.38, 2.78, 0.23, 0.19, shell)
    well = round_plate('Transport punch', 0, 0.03, 0.21, 3.25, 1.06, 0.5, 0.49, None)
    cut(body, well)
    bevel = body.modifiers.new('Mould radius', 'BEVEL')
    bevel.width = 0.032
    bevel.segments = 4
    body.modifiers.new('Broad faces', 'WEIGHTED_NORMAL')
    paper = round_plate('Die-cut label', 0, 0.23, 0.422, 4.03, 1.94, 0.012, 0.11, ivory)
    cut(paper, round_plate('Label opening', 0, 0.03, 0.35, 3.35, 1.16, 0.23, 0.53, None))
    round_plate('Transport bed', 0, 0.03, 0.194, 3.28, 1.10, 0.015, 0.5, insert)
    rotors = []
    for side, x in enumerate((-1.02, 1.02)):
        outer = 0.50 if side == 0 else 0.46
        ring('Tape pack', x, 0.03, 0.214, outer, 0.292, 0.11, oxide)
        for j in range(12):
            r = 0.326 + j * (outer - 0.334) / 12
            ring('Wound tape edge', x, 0.03, 0.325, r + 0.0018, r, 0.001, winding, 0)
        ring('Acetal hub flange', x, 0.03, 0.227, 0.322, 0.151, 0.122, hubs)
        ring('Recessed drive', x, 0.03, 0.205, 0.153, 0.109, 0.012, shadow, 0)
        ring('Pressed hub detail', x, 0.03, 0.350, 0.264, 0.254, 0.003, ivory, 0)
        pivot = bpy.data.objects.new('Drive teeth', None)
        bpy.context.collection.objects.link(pivot)
        pivot.location = (x, 0.03, 0.34)
        for j in range(6):
            a = j * math.tau / 6
            tooth = solid('Drive spline', (0, 0, 0), (0.081, 0.055, 0.071), hubs, 0.011)
            tooth.parent = pivot
            tooth.location = (0.148 * math.cos(a), 0.148 * math.sin(a), -0.028)
            tooth.rotation_euler.z = a
            mark = solid('Hub index', (0, 0, 0), (0.034, 0.022, 0.003), insert, 0.002)
            mark.parent = pivot
            mark.location = (0.286 * math.cos(a), 0.286 * math.sin(a), 0.012)
            mark.rotation_euler.z = a
        rotors.append(pivot)
    for x in (-1.36, 1.36):
        ring('Tape guide roller', x, -0.30, 0.222, 0.058, 0.018, 0.120, chrome, 0.003)
    for px, py, qx, qy in [
        (-1.44, -0.20, -1.36, -0.36),
        (-1.36, -0.36, 1.36, -0.36),
        (1.36, -0.36, 1.43, -0.18),
    ]:
        span = solid(
            'Magnetic ribbon',
            ((px + qx) / 2, (py + qy) / 2, 0.263),
            (math.hypot(qx - px, qy - py), 0.008, 0.071),
            oxide,
            0.002,
        )
        span.rotation_euler.z = math.atan2(qy - py, qx - px)
    lens = material('Polished acrylic', '#d2dfd9', 0, 0.025, glass=True)
    shield = round_plate('Clear transport window', 0, 0.03, 0.370, 3.19, 1.00, 0.020, 0.46, lens)
    for x in (-1.02, 1.02):
        bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=0.22, depth=0.16, location=(x, 0.03, 0.380))
        cut(shield, bpy.context.object)
    for i in range(17):
        x = -0.49 + i * 0.061
        solid('Transport scale', (x, -0.29, 0.395), (0.009, 0.075 if i % 4 == 0 else 0.038, 0.007), ivory)
    for x in (-1.99, 1.99):
        for y in (-1.19, 1.19):
            ring('Screw counterbore', x, y, 0.419, 0.094, 0.076, 0.009, shadow)
            bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=12, location=(x, y, 0.423))
            screw = bpy.context.object
            screw.name = 'Nickel screw'
            screw.scale = (0.075, 0.075, 0.018)
            screw.data.materials.append(chrome)
            for angle in (0.52, 0.52 + math.pi / 2):
                slit = solid('Recess in screw head', (x, y, 0.439), (0.089, 0.017, 0.005), shadow, 0.003)
                slit.rotation_euler.z = angle
    round_plate('Head access surround', 0, -1.06, 0.421, 2.96, 0.54, 0.028, 0.1, insert)
    for i in range(46):
        x = -1.32 + i * 0.059
        solid('Grip rib', (x, -1.035, 0.455), (0.018, 0.31, 0.013), shell, 0.006)
    for x in (-1.19, -0.76, 0.76, 1.19):
        ring('Guide aperture', x, -1.24, 0.452, 0.069, 0.051, 0.012, insert, 0.003)
    for x in (-1.1, 0, 1.1):
        tool = solid('Head pocket cutter', (x, -1.389, 0.238), (0.42, 0.19, 0.090), None)
        cut(body, tool)
        solid('Pressure pad', (x, -1.307, 0.229), (0.36, 0.017, 0.059), oxide, 0.008)
    z = 0.436
    label('Series mark', 'FERRO', -1.86, 0.77, z, 0.40, ink, 1.03)
    label('Tape designation', '60', 1.23, 0.73, z, 0.53, orange, 0.95)
    label('Tape formulation', 'NORMAL BIAS   /   IEC TYPE I', -0.46, 0.86, z, 0.104, ink, 1.07)
    label('Stereo mark', 'STEREO   •   2 × 30 MIN', -0.46, 0.70, z, 0.077, ink, 1.08)
    for i, (length, color) in enumerate([(1.54, ink), (1.27, orange), (0.88, orange)]):
        solid(
            'Printed speed stripe', (-1.84 + length / 2, -0.56 - 0.057 * i, z), (length, 0.035, 0.001), color
        )
    label('Side mark', 'SIDE   A', 0.94, -0.69, z, 0.103, ink, 1.14)
    label('Catalog number', '01  /  C60', -0.12, -0.66, z, 0.064, ink, 1.05)
    area('Softbox', (-3, -2, 7), (0, 0, 0.12), 570, '#fff2df', 6, 3.4)
    area('Edge strip', (3, 4, 3), (0, 0, 0.25), 500, '#d6ebff', 4.5, 0.7)
    area('Warm bounce', (-4, 2, 1.7), (0, 0, 0.3), 95, '#ff9d73', 3, 1.6)
    area('Front fill', (1, -5, 2), (0, 0, 0.1), 85, '#e2f1ff', 4, 1.1)
    data = bpy.data.cameras.new('Product lens')
    data.sensor_width = 36
    data.dof.use_dof = True
    data.dof.aperture_blades = 9
    camera = bpy.data.objects.new('Camera', data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera
    return scene, camera, rotors


SHOTS = {
    'label': ((-1.82, -2.42, 2.74), (-0.68, -2.10, 3.03), (-0.68, 0.60, 0.40), 46, 6.3),
    'drive': ((1.93, -1.64, 1.50), (1.18, -1.25, 1.66), (1.01, 0.04, 0.31), 58, 4.5),
    'edge': ((-2.85, -3.17, 0.92), (-1.48, -3.02, 1.34), (-0.57, -0.93, 0.31), 52, 5.6),
    'hero': ((2.62, -4.88, 6.35), (0.76, -5.30, 9.45), (0, -0.06, 0.21), 45, 8.0),
}


def render(cfg):
    scene, camera, rotors = build(cfg)
    a, b, center, lens, aperture = SHOTS[cfg['shot']]
    output = Path(cfg['out_dir'])
    scene.render.fps = cfg['fps_num']
    scene.render.fps_base = cfg['fps_den']
    for f in cfg.get('selected', range(cfg['frames'])):
        t = f / max(1, cfg['frames'] - 1)
        u = 1 - (1 - t) ** 2 if cfg['shot'] == 'hero' else t
        camera.location = Vector(a).lerp(Vector(b), u)
        target = Vector(center)
        camera.data.lens = lens
        camera.data.dof.aperture_fstop = aperture
        point_at(camera, target)
        camera.data.dof.focus_distance = (camera.location - target).length
        seconds = f * cfg['fps_den'] / cfg['fps_num']
        for i, pivot in enumerate(rotors):
            pivot.rotation_euler.z = (0.28 + i + 2.1 * seconds) * (1 if i else 0.88)
        scene.render.filepath = str(output / f'{f:06d}.png')
        bpy.ops.render.render(write_still=True)
    (output / 'cassette-render.json').write_text(
        json.dumps(
            {
                'shot': cfg['shot'],
                'engine': 'CYCLES',
                'device': scene.cycles.device,
                'samples': scene.cycles.samples,
                'blender': bpy.app.version_string,
            }
        )
    )


if __name__ == '__main__':
    render(json.loads(Path(sys.argv[sys.argv.index('--') + 1]).read_text()))
