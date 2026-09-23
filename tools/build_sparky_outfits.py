"""Build chapter costumes from the approved Sparky source without rebuilding his face.

Blender --background --python tools/build_sparky_outfits.py
SPARKY_SKIP_STILLS=1 skips the review renders. Assets retain the seven-bone rig.
"""
import bpy
import math
import os
from mathutils import Vector, Quaternion

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'assets', 'sparky', 'outfits')
os.makedirs(OUT, exist_ok=True)


def material(name, color, cloth=False):
    m = bpy.data.materials['Midnight navy cotton'].copy() if cloth else bpy.data.materials.new(name)
    m.name = name
    m.use_nodes = True
    m.diffuse_color = (*color, 1)
    node = m.node_tree.nodes.get('Principled BSDF')
    node.inputs['Base Color'].default_value = (*color, 1)
    node.inputs['Roughness'].default_value = .88 if cloth else .65
    return m


def skin(obj, bone='body'):
    obj.parent = rig
    group = obj.vertex_groups.new(name=bone)
    group.add(list(range(len(obj.data.vertices))), 1, 'REPLACE')
    modifier = obj.modifiers.new('Sparky skeleton', 'ARMATURE')
    modifier.object = rig
    return obj


def finish(obj, name, mat, bone):
    obj.name = name
    obj.data.materials.append(mat)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    if bone:
        skin(obj, bone)
    return obj


def rounded(name, loc, scale, mat, bone='body', bevel=.025):
    bpy.ops.mesh.primitive_cube_add(size=2, location=loc)
    obj = bpy.context.object
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    modifier = obj.modifiers.new('Soft sewn edges', 'BEVEL')
    modifier.width = bevel
    modifier.segments = 3
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    return finish(obj, name, mat, bone)


def ball(name, loc, scale, mat, bone='body'):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, location=loc)
    obj = bpy.context.object
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(obj, name, mat, bone)


def tube(name, points, radius, mat, bone='body', cyclic=False):
    curve = bpy.data.curves.new(name, 'CURVE')
    curve.dimensions = '3D'
    curve.bevel_depth = radius
    curve.bevel_resolution = 2
    spline = curve.splines.new('POLY')
    spline.points.add(len(points) - 1)
    for point, co in zip(spline.points, points):
        point.co = (*co, 1)
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target='MESH')
    return finish(obj, name, mat, bone)


def surface_y(x, z):
    torso = bpy.data.objects['Hoodie soft torso']
    bpy.context.view_layer.update()
    hit, point, _, _ = torso.ray_cast(torso.matrix_world.inverted() @ Vector((x, -2, z)), Vector((0, 1, 0)))
    return (torso.matrix_world @ point).y if hit else -.18


def patch(name, x, z, width, height, mat, depth=.016):
    """A subdivided panel follows the torso instead of floating at its curved edges."""
    obj = rounded(name, (x, -.3, z), (width, depth, height), mat)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.subdivide(number_cuts=3)
    bpy.ops.object.mode_set(mode='OBJECT')
    inverse = obj.matrix_world.inverted()
    for vertex in obj.data.vertices:
        world = obj.matrix_world @ vertex.co
        world.y = surface_y(world.x, world.z) - depth + vertex.co.y - .004
        vertex.co = inverse @ world
    return obj


def remove_prefixes(prefixes):
    for obj in list(bpy.context.scene.objects):
        if obj.name.startswith(prefixes):
            bpy.data.objects.remove(obj, do_unlink=True)


def replace_material(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)


def common_clothes(kind):
    remove_prefixes(('DSTA chest', 'Cotton drawstring', 'Drawstring', 'Flat sewn kangaroo',
                     'Pocket top seam', 'Pocket hand opening', 'Short pile Continuous stuffed leg'))
    base = material('Faded indigo cotton' if kind == 'ww2' else 'Temasek green cotton',
                    (.105, .155, .185) if kind == 'ww2' else (.115, .165, .080), True)
    trim = material('Faded cotton seams' if kind == 'ww2' else 'Uniform seams',
                    (.155, .20, .22) if kind == 'ww2' else (.15, .195, .10), True)
    trousers = material('Charcoal cotton trousers' if kind == 'ww2' else 'Green cotton trousers',
                         (.08, .09, .085) if kind == 'ww2' else (.09, .13, .06), True)
    leather = material('Dark cloth shoes' if kind == 'ww2' else 'Black leather boots', (.022, .025, .021))
    for obj in list(bpy.context.scene.objects):
        if obj.type != 'MESH' or not obj.data.materials:
            continue
        name = obj.data.materials[0].name
        if name in ('Midnight navy cotton', 'Hoodie ribbing'):
            replace_material(obj, base)
        elif name == 'Raised navy seams':
            replace_material(obj, trim)
    remove_prefixes(('Continuous stuffed leg',))
    for side, sign in [('L', 1), ('R', -1)]:
        bone = 'leg.' + side
        # Flat sewn trouser hems with the same rigid leg binding as the boots.
        # The original blended plush feet are removed, not buried in the shoes.
        vertices, faces = [], []
        for z, rx, ry in [(.25, .217, .235), (.30, .227, .24), (.39, .194, .204), (.425, .15, .16)]:
            for i in range(32):
                angle = i * math.tau / 32
                vertices.append((sign * .274 + rx * math.cos(angle), -.01 + ry * math.sin(angle), z))
        for ring in range(3):
            for i in range(32):
                a, b = ring * 32 + i, ring * 32 + (i + 1) % 32
                faces.append((a, b, b + 32, a + 32))
        faces.extend([tuple(reversed(range(32))), tuple(range(96, 128))])
        mesh = bpy.data.meshes.new('Trouser leg mesh')
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        obj = bpy.data.objects.new('Trouser leg ' + side, mesh)
        bpy.context.collection.objects.link(obj)
        finish(obj, obj.name, trousers, bone)
        ball('Cloth shoe ' + side if kind == 'ww2' else 'Boot toe ' + side,
             (sign * .28, -.073, .14), (.242, .28, .14), leather, bone)
        rounded('Shoe upper ' + side, (sign * .274, -.01, .194), (.22, .238, .061), leather, bone, .035)
        if kind == 'ns':
            for z in [.16, .195, .23]:
                tube('Boot lace ' + side, [(sign * .274 - .085, -.203, z),
                     (sign * .274 + .085, -.203, z + .012)], .008, trim, bone)
    return base, trim, leather


def civilian():
    base, trim, _ = common_clothes('ww2')
    canvas = material('Warm unbleached canvas', (.40, .325, .215), True)
    stitch = material('Unbleached repair thread', (.57, .51, .38))
    buttons = material('Dark wooden buttons', (.115, .075, .043))
    patch('Short cloth placket', 0, 1.02, .034, .15, trim, .006)
    for z in [.94, 1.035, 1.13]:
        ball('Wood button', (0, surface_y(0, z) - .025, z), (.018, .009, .018), buttons)
    patch('Workwear patch pocket', -.245, .74, .12, .11, base)
    patch('Mended cloth patch', .25, .64, .07, .052, canvas, .004)
    for x in [.19, .22, .25, .28, .31]:
        for z in [.601, .679]:
            tube('Visible repair stitch', [(x, surface_y(x, z) - .016, z - .01),
                 (x, surface_y(x, z) - .016, z + .01)], .0025, stitch)
    # Both sides of the satchel strap follow the body all the way over the shoulder.
    front = []
    back = []
    for i in range(33):
        t = i / 32
        x, z = -.29 + .76 * t, 1.18 - .64 * t
        y = surface_y(x, z)
        front.append((x, y - .035, z))
        back.append((x, -y + .035, z))
    for name, points in [('Satchel front strap', front), ('Satchel rear strap', back)]:
        for offset in [-.017, 0, .017]:
            tube(name, [(x + offset, y, z) for x, y, z in points], .012, canvas)
    tube('Satchel shoulder loop', [front[0], (-.29, 0, 1.25), back[0]], .025, canvas)
    tube('Satchel side strap', [back[-1], (.56, .14, .54), (.58, -.06, .54), (.50, -.25, .54)], .025, canvas)
    rounded('Canvas satchel', (.48, -.26, .52), (.15, .11, .16), canvas, bevel=.05)
    rounded('Satchel folded flap', (.48, -.373, .60), (.152, .018, .075), canvas)
    ball('Satchel button', (.48, -.399, .56), (.018, .01, .018), buttons)


def recruit():
    base, trim, leather = common_clothes('ns')
    remove_prefixes(('Continuous fabric hood', 'Soft folded hood edge', 'Fine hood stitching', 'Soft knitted hem'))
    for side, sign in [('L', 1), ('R', -1)]:
        sleeve = bpy.data.objects['Soft sleeve ' + side]
        sleeve.vertex_groups.clear()
        group = sleeve.vertex_groups.new(name='arm.' + side)
        group.add(list(range(len(sleeve.data.vertices))), 1, 'REPLACE')
        ball('Rounded shoulder ' + side, (sign * .43, 0, 1.075), (.15, .163, .16), base)
    brass = material('Dull brass fasteners', (.25, .215, .10))
    webbing = material('Olive cotton webbing', (.23, .26, .135), True)
    patch('Shirt button placket', 0, .80, .025, .30, trim, .006)
    for z in [.61, .76, .91, 1.065]:
        ball('Shirt button', (0, surface_y(0, z) - .023, z), (.013, .009, .013), brass)
    for sign in [-1, 1]:
        patch('Shirt breast pocket', sign * .225, .90, .116, .107, base)
        patch('Breast pocket flap', sign * .225, .982, .122, .03, trim)
        ball('Pocket button', (sign * .225, surface_y(sign * .225, .965) - .043, .965), (.012, .008, .012), brass)
        # Folded triangular collar, no rank or modern insignia.
        vertices = [(sign * .035, -.218, 1.21), (sign * .23, -.222, 1.15),
                    (sign * .125, -.29, 1.025)]
        mesh = bpy.data.meshes.new('Collar mesh')
        mesh.from_pydata(vertices, [], [(0, 1, 2)])
        mesh.update()
        obj = bpy.data.objects.new('Folded shirt collar', mesh)
        bpy.context.collection.objects.link(obj)
        finish(obj, obj.name, trim, 'body')
        solid = obj.modifiers.new('Collar thickness', 'SOLIDIFY')
        solid.thickness = .012
    # Small soft field cap leaves both characteristic ears exposed.
    ball('Green field cap crown', (0, -.07, 1.996), (.345, .295, .16), base, 'head')
    ball('Field cap band', (0, -.092, 1.969), (.355, .299, .05), trim, 'head')
    ball('Soft cap peak', (0, -.315, 1.954), (.34, .255, .022), base, 'head')
    # A flat web belt follows the waist, with a small rectangular buckle.
    torso = bpy.data.objects['Hoodie soft torso']
    vertices, faces = [], []
    bpy.context.view_layer.update()
    for z in [.44, .51]:
        for t in range(64):
            direction = Vector((math.cos(t * 2 * math.pi / 64), math.sin(t * 2 * math.pi / 64), 0))
            origin = Vector((0, 0, z))
            hit, point, _, _ = torso.ray_cast(torso.matrix_world.inverted() @ origin, direction)
            assert hit
            vertices.append(torso.matrix_world @ point + direction * .012)
    for t in range(64):
        nxt = (t + 1) % 64
        faces.append((t, nxt, nxt + 64, t + 64))
    mesh = bpy.data.meshes.new('Webbing belt band')
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new('Waist web belt', mesh)
    bpy.context.collection.objects.link(obj)
    finish(obj, obj.name, webbing, 'body')
    solid = obj.modifiers.new('Belt thickness', 'SOLIDIFY')
    solid.thickness = .014
    rounded('Belt buckle', (0, -.337, .475), (.054, .012, .039), brass, bevel=.009)


def carry_animations():
    """Keep the existing gait but solve rigid plush arms to two fixed grip points."""
    # Short rigid arms cannot perform realistic elbow/wrist articulation. These
    # are authored carrying poses; the separate prop follows the body bone.
    targets = {'L': Vector((.34, -.53, 1.005)), 'R': Vector((-.25, -.53, .858))}
    for source_name in ['Idle', 'Walk']:
        action = bpy.data.actions[source_name].copy()
        action.name = 'Carry' + source_name
        rig.animation_data.action = action
        for frame in range(1, (97 if source_name == 'Idle' else 33) + 1):
            bpy.context.scene.frame_set(frame)
            for side in ['L', 'R']:
                bone = rig.pose.bones['arm.' + side]
                paw = bpy.data.objects['Mitten paw ' + side]
                center = sum((paw.matrix_world @ v.co for v in paw.data.vertices), Vector()) / len(paw.data.vertices)
                pivot = bone.bone.head_local
                rest = center - pivot
                desired = targets[side] - pivot
                # Match both direction AND reach so the mittens keep contact.
                basis = bone.bone.matrix_local.to_quaternion()
                bone.rotation_quaternion = basis.inverted() @ rest.rotation_difference(desired) @ basis
                bone.scale = (desired.length / rest.length,) * 3
                bone.keyframe_insert(data_path='rotation_quaternion', frame=frame, group=bone.name)
                bone.keyframe_insert(data_path='scale', frame=frame, group=bone.name)
        track = rig.animation_data.nla_tracks.new()
        track.name = action.name
        track.strips.new(action.name, 1, action)
        track.mute = True
    # Explicit unit-scale tracks prevent carry scale leaking into unarmed clips.
    for name in ['Idle', 'Walk', 'Wave']:
        rig.animation_data.action = bpy.data.actions[name]
        for side in ['L', 'R']:
            bone = rig.pose.bones['arm.' + side]
            bone.scale = (1, 1, 1)
            for frame in [1, int(rig.animation_data.action.frame_range[1])]:
                bone.keyframe_insert(data_path='scale', frame=frame, group=bone.name)


def rifle():
    """Simplified early M16 silhouette: fixed stock, carry handle, straight magazine.

    A visual prop only. Mesh coordinates are baked into the character's rest
    space; one body-bone skin keeps it aligned to the authored carrying clips.
    """
    polymer = material('Rifle charcoal furniture', (.022, .029, .025))
    steel = material('Rifle grey metal', (.075, .085, .077))
    objects_before = set(bpy.context.scene.objects)
    rounded('Rifle fixed stock', (-.55, 0, 0), (.23, .045, .085), polymer, None)
    rounded('Rifle receiver', (-.20, 0, .01), (.15, .038, .058), steel, None, .012)
    rounded('Rifle handguard', (.15, 0, .025), (.21, .048, .056), polymer, None)
    tube('Rifle barrel', [(.35, 0, .026), (.69, 0, .026)], .018, steel, None)
    rounded('Rifle muzzle', (.7, 0, .026), (.035, .026, .026), steel, None, .006)
    rounded('Rifle straight magazine', (-.09, 0, -.102), (.052, .035, .083), steel, None, .008)
    grip = rounded('Rifle pistol grip', (-.30, 0, -.105), (.035, .035, .074), polymer, None, .009)
    grip.rotation_euler.y = -.22
    tube('Rifle carry handle', [(-.33, 0, .07), (-.31, 0, .142), (-.12, 0, .142), (-.09, 0, .07)], .014, steel, None)
    tube('Rifle front sight', [(.43, 0, .037), (.46, 0, .132), (.51, 0, .037)], .012, steel, None)
    objects = list(set(bpy.context.scene.objects) - objects_before)
    rotation = Quaternion(Vector((0, 1, 0)), -.245)
    offset = Vector((0, -.53, .93))
    for obj in objects:
        bpy.context.view_layer.update()
        matrix = obj.matrix_world.copy()
        for vertex in obj.data.vertices:
            vertex.co = rotation @ (matrix @ vertex.co) + offset
        obj.matrix_world.identity()
        skin(obj)
    return objects


def select_character(exclude=()):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.context.scene.objects:
        if (obj == rig or obj.parent == rig) and obj not in exclude:
            obj.select_set(True)
    bpy.context.view_layer.objects.active = rig


def export(path):
    bpy.ops.export_scene.gltf(filepath=path, use_selection=True, export_format='GLB',
        export_animations=True, export_animation_mode='ACTIONS', export_skins=True, export_yup=True)


for kind in ['ww2', 'ns']:
    bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, 'assets', 'sparky', 'sparky.blend'))
    rig = bpy.data.objects['Sparky_Rig']
    rig.animation_data.action = None
    for bone in rig.pose.bones:
        bone.rotation_quaternion = (1, 0, 0, 0)
        bone.location = (0, 0, 0)
        bone.scale = (1, 1, 1)
    if kind == 'ww2':
        civilian()
        prop = []
    else:
        recruit()
        carry_animations()
        prop = rifle()
    stem = 'sparky-' + ('ww2-civilian' if kind == 'ww2' else 'ns-1967')
    rig.animation_data.action = None
    for bone in rig.pose.bones:
        bone.rotation_quaternion = (1, 0, 0, 0)
        bone.location = (0, 0, 0)
        bone.scale = (1, 1, 1)
    select_character()
    export(os.path.join(OUT, stem + '.glb'))
    # The rifle is a separate set of named meshes in the NS GLB. Toggle all
    # Rifle* meshes together. They share the skeleton, avoiding socket drift.
    scene = bpy.context.scene
    rig.animation_data.action = bpy.data.actions['Idle']
    scene.frame_set(1)
    for obj in prop:
        obj.hide_render = True
        obj.hide_set(True)
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 1000
    scene.cycles.samples = 24
    scene.camera.location = (2.4, -7, 2.7)
    scene.camera.rotation_euler = (Vector((0, 0, 1.04)) - scene.camera.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, stem + '.blend'))
    if os.environ.get('SPARKY_SKIP_STILLS') != '1':
        for view, location in [('preview', (2.4, -7, 2.7)), ('back', (3, 7, 2.7))]:
            scene.camera.location = location
            scene.camera.rotation_euler = (Vector((0, 0, 1.04)) - scene.camera.location).to_track_quat('-Z', 'Y').to_euler()
            scene.render.filepath = os.path.join(OUT, stem + '-' + view + '.png')
            bpy.ops.render.render(write_still=True)
        if prop:
            for obj in prop:
                obj.hide_render = False
                obj.hide_set(False)
            rig.animation_data.action = bpy.data.actions['CarryIdle']
            scene.frame_set(1)
            scene.camera.location = (2.4, -7, 2.7)
            scene.camera.rotation_euler = (Vector((0, 0, 1.04)) - scene.camera.location).to_track_quat('-Z', 'Y').to_euler()
            scene.render.filepath = os.path.join(OUT, stem + '-rifle.png')
            bpy.ops.render.render(write_still=True)
    print('SPARKY_OUTFIT_BUILT', stem, flush=True)
