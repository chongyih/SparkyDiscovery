"""Sparky's Chapter 2 costume (9 August 1965): a kopitiam helper.

Reuses the costume helpers from the original project's tools/build_sparky_outfits.py (same approved
bear, seven-bone rig and clips; the source sparky.blend is opened read-only and never saved) and adds:
    pale-blue cotton shirt with a collar, button placket and breast pocket (+ pencil
    for taking orders), khaki shorts, white canvas shoes with dark rubber soles, and a striped
    kopitiam face towel over the right shoulder. The hood comes off (as for the NS recruit) so the
    collar reads.

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python tools/build_sparky_1965.py
Writes tools/sparky_outfits/sparky-1965-helper.blend (review renders go to docs/previews/sparky/);
then `OUTFITS=ind tools/optimize_sparky.sh` makes public/assets/models/sparky-ind(-mobile).glb.
SPARKY_SKIP_STILLS=1 skips the renders.

An artistic costume, not a reconstruction: cotton shirts, shorts, canvas shoes and the striped
face towel over the shoulder are everyday 1960s Singapore working wear, adapted for a plush bear.
"""
import bpy
import math
import os
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OLD = os.environ.get('SPARKY_PROJECT', '/Users/cy/Code/Games/SparkyDiscovery')
OUT = os.path.join(HERE, 'sparky_outfits')
os.makedirs(OUT, exist_ok=True)

# Load the helper functions only (the original file builds its own outfits after this marker).
src = open(os.path.join(OLD, 'tools', 'build_sparky_outfits.py')).read()
src = src[:src.index("for kind in ['ww2', 'ns']:")]
G = {'__file__': os.path.join(OLD, 'tools', 'build_sparky_outfits.py'), '__name__': 'sparky_outfit_helpers'}
exec(compile(src, 'build_sparky_outfits.py', 'exec'), G)
material, rounded, ball, tube, patch, finish = (G[k] for k in ('material', 'rounded', 'ball', 'tube', 'patch', 'finish'))
surface_y, remove_prefixes, replace_material = G['surface_y'], G['remove_prefixes'], G['replace_material']


def cast_z(x, y, objs):
    """Highest surface point of objs above (x, y)."""
    best = None
    bpy.context.view_layer.update()
    for o in objs:
        inv = o.matrix_world.inverted()
        hit, p, _, _ = o.ray_cast(inv @ Vector((x, y, 3)), inv.to_3x3() @ Vector((0, 0, -1)))
        if hit:
            z = (o.matrix_world @ p).z
            best = z if best is None else max(best, z)
    return best


def ribbon(name, centre, half_width, mat, thickness=.01, bone='body'):
    """A flat strip along a centreline (width along x), given thickness."""
    verts, faces = [], []
    for p in centre:
        verts += [(p[0] - half_width, p[1], p[2]), (p[0] + half_width, p[1], p[2])]
    for i in range(len(centre) - 1):
        a = 2 * i
        faces.append((a, a + 1, a + 3, a + 2))
    mesh = bpy.data.meshes.new(name + ' mesh')
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    finish(obj, name, mat, bone)
    solid = obj.modifiers.new('Cloth thickness', 'SOLIDIFY')
    solid.thickness = thickness
    solid.offset = 0
    return obj


def kopitiam_helper():
    rig = G['rig']
    remove_prefixes(('DSTA chest', 'Cotton drawstring', 'Drawstring', 'Flat sewn kangaroo',
                     'Pocket top seam', 'Pocket hand opening', 'Short pile Continuous stuffed leg',
                     'Continuous fabric hood', 'Soft folded hood edge', 'Fine hood stitching', 'Soft knitted hem'))
    shirt = material('Pale blue cotton shirt', (.28, .43, .60), True)
    seams = material('Pale blue shirt seams', (.23, .36, .51), True)
    shorts = material('Khaki cotton shorts', (.30, .235, .13), True)
    canvas = material('White canvas shoes', (.70, .68, .62), True)
    rubber = material('Dark rubber soles', (.03, .03, .028))
    buttons = material('White shirt buttons', (.80, .80, .76))
    towel = material('White towel cotton', (.80, .79, .74), True)
    stripe = material('Red towel stripe', (.55, .05, .04), True)
    pencil = material('Yellow pencil', (.80, .55, .05))
    for obj in list(bpy.context.scene.objects):
        if obj.type != 'MESH' or not obj.data.materials:
            continue
        name = obj.data.materials[0].name
        if name in ('Midnight navy cotton', 'Hoodie ribbing'):
            replace_material(obj, shirt)
        elif name == 'Raised navy seams':
            replace_material(obj, seams)
    remove_prefixes(('Continuous stuffed leg',))
    # Short trousers + canvas shoes (same leg binding as the other costumes).
    for side, sign in [('L', 1), ('R', -1)]:
        bone = 'leg.' + side
        vertices, faces = [], []
        for z, rx, ry in [(.25, .217, .235), (.30, .227, .24), (.39, .194, .204), (.425, .15, .16)]:
            for i in range(32):
                a = i * math.tau / 32
                vertices.append((sign * .274 + rx * math.cos(a), -.01 + ry * math.sin(a), z))
        for r in range(3):
            for i in range(32):
                a, b = r * 32 + i, r * 32 + (i + 1) % 32
                faces.append((a, b, b + 32, a + 32))
        faces.extend([tuple(reversed(range(32))), tuple(range(96, 128))])
        mesh = bpy.data.meshes.new('Trouser leg mesh')
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        obj = bpy.data.objects.new('Trouser leg ' + side, mesh)
        bpy.context.collection.objects.link(obj)
        finish(obj, obj.name, shorts, bone)
        # turned-up hem of the shorts
        tube('Shorts hem ' + side, [(sign * .274 + .222 * math.cos(a), -.01 + .238 * math.sin(a), .262)
                                    for a in [i * math.tau / 32 for i in range(32)]], .014, shorts, bone, cyclic=True)
        ball('Cloth shoe ' + side, (sign * .28, -.073, .14), (.242, .28, .14), canvas, bone)
        rounded('Shoe upper ' + side, (sign * .274, -.01, .194), (.22, .238, .061), canvas, bone, .035)
        ball('Rubber sole ' + side, (sign * .28, -.07, .03), (.236, .274, .036), rubber, bone)
        for z in [.17, .205]:
            tube('Shoe lace ' + side, [(sign * .274 - .07, -.232, z), (sign * .274 + .07, -.232, z + .01)], .007, buttons, bone)
    # No hood: rounded shoulders, sleeves follow the arms (as for the NS recruit).
    for side, sign in [('L', 1), ('R', -1)]:
        sleeve = bpy.data.objects['Soft sleeve ' + side]
        sleeve.vertex_groups.clear()
        grp = sleeve.vertex_groups.new(name='arm.' + side)
        grp.add(list(range(len(sleeve.data.vertices))), 1, 'REPLACE')
        ball('Rounded shoulder ' + side, (sign * .43, 0, 1.075), (.15, .163, .16), shirt)
    # Shirt: placket, buttons, a breast pocket with a pencil, a soft collar.
    patch('Shirt button placket', 0, .82, .03, .30, seams, .006)
    for z in [.62, .77, .92, 1.07]:
        ball('Shirt button', (0, surface_y(0, z) - .023, z), (.014, .009, .014), buttons)
    patch('Shirt breast pocket', .225, .90, .116, .107, shirt)
    tube('Pencil', [(.262, surface_y(.262, .95) - .045, .93), (.27, surface_y(.27, 1.02) - .05, 1.04)], .011, pencil)
    tube('Pencil tip', [(.27, surface_y(.27, 1.02) - .05, 1.04), (.2705, surface_y(.27, 1.02) - .05, 1.058)], .011, rubber)
    for sign in [-1, 1]:
        verts = [(sign * .03, -.222, 1.215), (sign * .24, -.226, 1.155), (sign * .12, -.295, 1.02)]
        mesh = bpy.data.meshes.new('Collar mesh')
        mesh.from_pydata(verts, [], [(0, 1, 2)])
        mesh.update()
        obj = bpy.data.objects.new('Folded shirt collar', mesh)
        bpy.context.collection.objects.link(obj)
        finish(obj, obj.name, seams, 'body')
        obj.modifiers.new('Collar thickness', 'SOLIDIFY').thickness = .012
    # The kopitiam face towel over the right shoulder, hanging down front and back.
    torso = bpy.data.objects['Hoodie soft torso']
    shoulder = bpy.data.objects['Rounded shoulder R']
    x = -.33
    front, back = [], []
    for i in range(9):
        z = .72 + (1.16 - .72) * i / 8
        y = surface_y(x, z)
        front.append((x, y - .028, z))
        back.append((x, -y + .028, z - .06))
    top = cast_z(x, 0, [torso, shoulder]) or 1.24
    arc = []
    for i in range(1, 6):
        a = math.pi * i / 6
        arc.append((x, -math.cos(a) * abs(front[-1][1]), front[-1][2] + math.sin(a) * (top + .03 - front[-1][2])))
    centre = front + arc + back[::-1]
    ribbon('Kopitiam towel', centre, .075, towel)
    for zz in (.76, .785):
        band = [(x, surface_y(x, z) - .036, z) for z in (zz - .007, zz + .007)]
        ribbon('Towel stripe', band, .076, stripe, .004)


def select_character(rig):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.context.scene.objects:
        if obj == rig or obj.parent == rig:
            obj.select_set(True)
    bpy.context.view_layer.objects.active = rig


bpy.ops.wm.open_mainfile(filepath=os.path.join(OLD, 'assets', 'sparky', 'sparky.blend'))
rig = bpy.data.objects['Sparky_Rig']
G['rig'] = rig
rig.animation_data.action = None
for bone in rig.pose.bones:
    bone.rotation_quaternion = (1, 0, 0, 0)
    bone.location = (0, 0, 0)
    bone.scale = (1, 1, 1)
kopitiam_helper()
stem = 'sparky-1965-helper'
scene = bpy.context.scene
rig.animation_data.action = bpy.data.actions['Idle']
scene.frame_set(1)
scene.render.resolution_x = scene.render.resolution_y = 900
scene.cycles.samples = 24
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, stem + '.blend'))
if os.environ.get('SPARKY_SKIP_STILLS') != '1':
    for view, loc in [('preview', (2.4, -7, 2.7)), ('back', (3, 7, 2.7)), ('side', (-7, -1.5, 2.2))]:
        scene.camera.location = loc
        scene.camera.rotation_euler = (Vector((0, 0, 1.04)) - scene.camera.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = os.path.join(os.path.dirname(HERE), 'docs', 'previews', 'sparky', stem + '-' + view + '.png')
        bpy.ops.render.render(write_still=True)
print('SPARKY_OUTFIT_BUILT', stem, flush=True)
