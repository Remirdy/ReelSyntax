import json
import math
from pathlib import Path
import sys
import time

import bpy
from mathutils import Vector


def smooth(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def linear(hex_color):
    values = [int(hex_color.lstrip('#')[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values)


def material(name, color, metallic=0.0, roughness=.3, glass=False):
    mat = bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    tree = mat.node_tree
    surface = tree.nodes.get('Principled BSDF')
    surface.inputs['Base Color'].default_value = (*linear(color), 1)
    surface.inputs['Metallic'].default_value = metallic
    surface.inputs['Roughness'].default_value = roughness
    if glass:
        surface.inputs['Roughness'].default_value = .018
        surface.inputs['Transmission Weight'].default_value = 1
        surface.inputs['IOR'].default_value = 1.44
        surface.inputs['Coat Weight'].default_value = .22
        surface.inputs['Coat Roughness'].default_value = .03
        surface.inputs['Coat IOR'].default_value = 1.38
        output_node = tree.nodes.get('Material Output')
        light_path = tree.nodes.new('ShaderNodeLightPath')
        transparent = tree.nodes.new('ShaderNodeBsdfTransparent')
        transparent.inputs['Color'].default_value = (.93, .97, .96, 1)
        mix = tree.nodes.new('ShaderNodeMixShader')
        tree.links.new(light_path.outputs['Is Shadow Ray'], mix.inputs['Fac'])
        tree.links.new(surface.outputs['BSDF'], mix.inputs[1])
        tree.links.new(transparent.outputs['BSDF'], mix.inputs[2])
        tree.links.new(mix.outputs['Shader'], output_node.inputs['Surface'])
    else:
        coord = tree.nodes.new('ShaderNodeTexCoord')
        noise = tree.nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = 450
        noise.inputs['Detail'].default_value = 2
        tree.links.new(coord.outputs['Generated'], noise.inputs['Vector'])
        bump = tree.nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = .025 if metallic else .015
        bump.inputs['Distance'].default_value = .0015
        tree.links.new(noise.outputs['Fac'], bump.inputs['Height'])
        tree.links.new(bump.outputs['Normal'], surface.inputs['Normal'])
        if metallic:
            surface.inputs['Anisotropic'].default_value = .35
    return mat


def mesh_object(name, vertices, faces, mat, bevel=0.0):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    for face in mesh.polygons:
        face.use_smooth = True
    if bevel:
        modifier = obj.modifiers.new('Manufactured edge', 'BEVEL')
        modifier.width = bevel
        modifier.segments = 3
        modifier.limit_method = 'ANGLE'
        modifier.harden_normals = True
    return obj


def lathe(name, profile, mat, segments=160, bevel=.008):
    vertices = []
    for radius, y in profile:
        vertices.extend((radius * math.cos(i * math.tau / segments), y, radius * math.sin(i * math.tau / segments)) for i in range(segments))
    faces = []
    for row in range(len(profile)):
        following = (row + 1) % len(profile)
        for i in range(segments):
            j = (i + 1) % segments
            faces.append((row * segments + i, row * segments + j, following * segments + j, following * segments + i))
    obj = mesh_object(name, vertices, faces, mat, bevel)
    for row, (_, y) in enumerate(profile):
        next_y = profile[(row+1) % len(profile)][1]
        if math.isclose(y, next_y, abs_tol=1e-8):
            for index in range(row*segments, (row+1)*segments):
                obj.data.polygons[index].use_smooth = False
    return obj


def meniscus_lens(name, radius, y_front_center, sag_front, thickness, mat, segments=144, rings=16):
    vertices = [(0.0, y_front_center, 0.0)]
    for k in range(1, rings + 1):
        t = k / rings
        r = radius * t
        yf = y_front_center + sag_front * t * t
        vertices.extend((r * math.cos(i * math.tau / segments), yf, r * math.sin(i * math.tau / segments)) for i in range(segments))
    back_ring_start = len(vertices)
    for k in range(rings, 0, -1):
        t = k / rings
        r = radius * t
        yb = (y_front_center + thickness) + (sag_front * 0.92) * t * t
        vertices.extend((r * math.cos(i * math.tau / segments), yb, r * math.sin(i * math.tau / segments)) for i in range(segments))
    back_pole = len(vertices)
    vertices.append((0.0, y_front_center + thickness, 0.0))

    faces = []
    for i in range(segments):
        j = (i + 1) % segments
        faces.append((0, 1 + j, 1 + i))
    total_ring_rows = 2 * rings
    for row in range(total_ring_rows - 1):
        r0 = 1 + row * segments
        r1 = 1 + (row + 1) * segments
        for i in range(segments):
            j = (i + 1) % segments
            faces.append((r0 + i, r0 + j, r1 + j, r1 + i))
    last_ring = 1 + (total_ring_rows - 1) * segments
    for i in range(segments):
        j = (i + 1) % segments
        faces.append((last_ring + i, last_ring + j, back_pole))
    obj = mesh_object(name, vertices, faces, mat, bevel=0.0)
    rim_row = rings - 1
    for i in range(segments):
        obj.data.polygons[segments + rim_row * segments + i].use_smooth = False
    return obj


def ring(name, outer, inner, y, depth, mat, bevel=.006):
    return lathe(name, [(outer, y), (inner, y), (inner, y + depth), (outer, y + depth)], mat, bevel=bevel)


def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def area(name, location, target, energy, color, width, height):
    light = bpy.data.lights.new(name, 'AREA')
    light.energy = energy
    light.color = linear(color)
    light.shape = 'RECTANGLE'
    light.size = width
    light.size_y = height
    obj = bpy.data.objects.new(name, light)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    point_at(obj, target)
    return obj


def build(cfg):
    if not (5, 1, 0) <= bpy.app.version < (6, 0, 0):
        raise RuntimeError('The Aperture recipe requires Blender 5.1–5.x; other recipes retain their own compatibility')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = int(cfg.get('samples', 16 if cfg.get('profile') == 'draft' else 24))
    scene.cycles.use_denoising = True
    scene.cycles.seed = 108
    scene.cycles.max_bounces = 6
    scene.cycles.diffuse_bounces = 2
    scene.cycles.glossy_bounces = 4
    scene.cycles.transmission_bounces = 4
    scene.cycles.transparent_max_bounces = 4
    scene.cycles.blur_glossy = .5
    scene.cycles.sample_clamp_direct = 10.0
    scene.cycles.sample_clamp_indirect = 5.0
    scene.cycles.adaptive_threshold = .025
    device = 'CPU'
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'METAL'
        prefs.get_devices()
        if any(d.type == 'METAL' for d in prefs.devices):
            for item in prefs.devices:
                item.use = item.type == 'METAL'
            scene.cycles.device = 'GPU'
            device = 'METAL'
    except (TypeError, RuntimeError):
        pass
    scene.render.use_persistent_data = True
    scene.render.resolution_x = int(cfg['width'])
    scene.render.resolution_y = int(cfg['height'])
    scene.render.resolution_percentage = 100
    scene.render.fps = int(cfg['fps_num'])
    scene.render.fps_base = float(cfg['fps_den'])
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.color_depth = '8'
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.exposure = .25
    world = bpy.data.worlds.new('Dark studio')
    if world.node_tree is None:
        world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.18, .22, .3, 1)
    world.node_tree.nodes['Background'].inputs[1].default_value = .06
    scene.world = world

    graphite = material('Anodized graphite', cfg.get('foreground', '#20262a'), .90, .25)
    gold = material('Brushed champagne titanium', cfg.get('accent', '#bd9a66'), .92, .23)
    steel = material('Machined blade steel', '#586269', .85, .26)
    black = material('Optical interior', '#070a0b', .35, .32)
    glass = material('Coated optical glass', '#e6f4f0', 0, .018, glass=True)
    floor_material = material('Studio charcoal', cfg.get('background', '#181d21'), .35, .33)
    body = lathe('Anodized barrel', [(1.01,.4),(1.055,.32),(1.055,-.26),(1.00,-.39),(.76,-.39),(.73,-.28),(.73,.3),(.83,.4)], graphite)
    rear = ring('Rear mechanical collar', 1.02, .77, .28, .18, steel)
    trim = ring('Precision front bezel', 1.015, .79, -.43, .055, gold)
    ring('Lens inner lip', .79, .705, -.42, .08, graphite)
    ring('Internal step one', .705, .64, -.27, .12, black)
    ring('Internal step two', .64, .49, -.12, .18, black)
    ring('Deep reflective baffle', .49, .22, .05, .18, graphite)
    lens = meniscus_lens('Optical protective element', .70, -.582, .082, .026, glass)
    sensor = ring('Sensor glint', .24, .19, .24, .015, gold)
    ring('Sensor rear closure', .20, .001, .255, .012, black)

    for index in range(64):
        angle = index * math.tau / 64
        bpy.ops.mesh.primitive_cube_add(size=1, location=(1.05*math.cos(angle), .035, 1.05*math.sin(angle)))
        tooth = bpy.context.object
        tooth.name = f'Grip flute {index:02d}'
        tooth.scale = (.019, .235, .026)
        tooth.rotation_euler.y = -angle
        tooth.data.materials.append(graphite)
        bevel = tooth.modifiers.new('Edge highlight', 'BEVEL')
        bevel.width = .008
        bevel.segments = 2
    for index in range(5):
        ring(f'Fine concentric machining {index}', .91 + index*.014, .907 + index*.014, -.441, .002, steel, bevel=.001)
    for index in range(8):
        angle = index * math.tau / 8
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=.028, location=(.858*math.cos(angle),-.455,.858*math.sin(angle)))
        screw = bpy.context.object
        screw.name = f'Polished fastener {index}'
        screw.scale.y = .35
        screw.data.materials.append(steel)

    blades = []
    arc_steps = 12
    for index in range(11):
        angle = index * math.tau / 11
        pivot = Vector((.64*math.cos(angle), -.385+index*.0035, .64*math.sin(angle)))
        outline = []
        for i in range(arc_steps + 1):
            a = angle + math.radians(-8 + 67*i/arc_steps)
            outline.append(Vector((.70*math.cos(a),pivot.y,.70*math.sin(a))) - pivot)
        for i in range(arc_steps + 1):
            a = angle + math.radians(76 - 67*i/arc_steps)
            radius = .20 + .03*math.sin(i*math.pi/arc_steps)
            outline.append(Vector((radius*math.cos(a),pivot.y,radius*math.sin(a))) - pivot)
        total_v = len(outline)
        blade_faces = [(i, total_v - 1 - i, total_v - 2 - i, i + 1) for i in range(arc_steps)]
        blade = mesh_object(f'Iris blade {index:02d}', outline, blade_faces, steel)
        for face in blade.data.polygons:
            face.use_smooth = False
        blade.location = pivot
        solidify = blade.modifiers.new('Blade gauge', 'SOLIDIFY')
        solidify.thickness = .0025
        solidify.offset = 0.0
        bevel = blade.modifiers.new('Blade rim', 'BEVEL')
        bevel.width = .0012
        bevel.segments = 2
        blades.append(blade)

    sweep = [(-30, -1.085), (3, -1.085)]
    sweep.extend((3+4*math.sin(i*math.pi/48), -1.085+4*(1-math.cos(i*math.pi/48))) for i in range(1,25))
    sweep.append((7, 20))
    vertices = [(x,y,z) for y,z in sweep for x in (-20,20)]
    faces = [(i*2,i*2+1,i*2+3,i*2+2) for i in range(len(sweep)-1)]
    mesh_object('Seamless studio cyclorama',vertices,faces,floor_material)
    area('Warm overhead softbox', (1,-2.5,4), (0,0,0), 700, '#ffe2bd', 4, 1.2)
    area('Cool edge strip', (-3,1.2,2.8), (0,0,0), 900, '#bed6f1', 3, .55)
    area('Glass reflection card', (-2.1,-3.1,1.35), (0,-.42,0), 95, '#e7f3ff', .32, 2.2)
    area('Right warm strip', (3,1,.8), (0,0,0), 500, '#eabf8d', .6, 2.8)
    bounce = area('Low bounce', (1.2,-3.2,-.65), (0,-.35,0), 55, '#ffffff', 2.2, .7)
    bounce.visible_glossy = False

    camera_data = bpy.data.cameras.new('Directed optics camera')
    camera = bpy.data.objects.new('Directed optics camera', camera_data)
    bpy.context.collection.objects.link(camera)
    camera_data.sensor_width = 36
    camera_data.clip_start = .02
    camera_data.dof.use_dof = True
    scene.camera = camera
    focus = bpy.data.objects.new('Focus target', None)
    bpy.context.collection.objects.link(focus)
    camera_data.dof.focus_object = focus
    return scene, camera, focus, blades, lens, trim, rear, device


def render(cfg):
    started = time.perf_counter()
    scene, camera, focus, blades, lens, trim, rear, device = build(cfg)
    output = Path(cfg['out_dir'])
    output.mkdir(parents=True, exist_ok=True)
    shot = cfg.get('shot', 'hero')
    frames = int(cfg['frames'])
    selected = cfg.get('preview_frames', list(range(frames)))
    for frame in selected:
        u = frame / max(1, frames-1)
        s = smooth(u)
        motion = s if cfg.get('camera_preset', 'dolly_in') != 'locked' else .5
        opening = .28 + .12*math.sin(math.pi*u)
        separation = 0.0
        if shot == 'macro':
            camera.location = (1.50-.12*motion, -1.45-.12*motion, .62-.2*motion)
            target = (.64,-.35,.24)
            camera.data.lens = 85
            camera.data.dof.aperture_fstop = 3.8
        elif shot == 'iris':
            camera.location = (.08+.09*motion, -3.05+.13*motion, .12-.05*motion)
            target = (0,-.46,0)
            camera.data.lens = 91
            camera.data.dof.aperture_fstop = 4.5
            opening = -.20 + .72*smooth((u-.12)/.7)
        elif shot == 'assembly':
            camera.location = (3.5-.35*motion, -5.4+.15*motion, 1.6-.18*motion)
            target = (0,-.35,.0)
            camera.data.lens = 53
            camera.data.dof.aperture_fstop = 6.3
            separation = 1.15*(1-smooth((u-.12)/.76))
            opening = .50 - .18*s
        else:
            camera.location = (3.1-.35*motion, -7.1+.10*motion, 1.45-.08*motion)
            target = (0,0,-.04)
            camera.data.lens = 57
            camera.data.dof.aperture_fstop = 5.6
        camera.data.lens = float(cfg.get('focal_mm', camera.data.lens))
        if cfg.get('camera_target') is not None:
            target = cfg['camera_target']
        if cfg.get('camera_position') is not None:
            camera.location = Vector(target) + (Vector(cfg['camera_position']) - Vector(target)) * (1-.08*motion)
        focus.location = target
        point_at(camera, target)
        for index, blade in enumerate(blades):
            blade.rotation_euler.y = opening
        lens.location.y = -separation
        trim.location.y = -.48*separation
        rear.location.y = .2*separation
        scene.frame_set(frame+1)
        if cfg.get('save_blend') and frame == selected[0]:
            bpy.ops.wm.save_as_mainfile(filepath=str(Path(cfg['save_blend']).resolve()))
        scene.render.filepath = str(output/f'{frame:06d}.png')
        bpy.ops.render.render(write_still=True)
        print(f'RS_APERTURE_FRAME={frame}', flush=True)
    samples = scene.cycles.samples
    report = {'engine': scene.render.engine, 'device': device, 'samples': samples, 'shot': shot,
              'frames': selected, 'elapsed_seconds': time.perf_counter()-started, 'blender': bpy.app.version_string}
    (output/'aperture-render.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    config = Path(sys.argv[sys.argv.index('--')+1])
    render(json.loads(config.read_text(encoding='utf-8')))
