"""Re-import an optimised Sparky GLB and render EEVEE preview stills for a visual check.

    Blender --background --factory-startup --python tools/render_sparky_previews.py -- \
        --glb public/assets/models/sparky-ww2.glb --out docs/previews/sparky [--prefix sparky-ww2]

Writes <prefix>_<pose>.png (front 3/4) plus <prefix>_face.png (close-up) and prints a summary
(tris, meshes, materials, vertex colours, clip frame ranges) of what Blender re-imported.
"""
import bpy
import math
import os
import sys
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
opts = dict(zip(argv[::2], argv[1::2]))
GLB = os.path.abspath(opts['--glb'])
OUT = os.path.abspath(opts['--out'])
PREFIX = opts.get('--prefix', os.path.splitext(os.path.basename(GLB))[0])
os.makedirs(OUT, exist_ok=True)

# (label, clip, fraction of clip length or None for rest pose, extra props)
POSES = [
    ('rest', None, 0, ''),
    ('walk', 'Walk', 0.25, ''),
    ('run', 'Run', 0.25, ''),
    ('cheer', 'Cheer', 13 / 29, ''),
    ('snap', 'Snap', 16 / 26, ''),
    ('sit', 'Sit', 0.1, 'bench'),
    ('crouch', 'Crouch', 0.3, ''),
    ('point', 'Point', 20 / 36, ''),
    ('talk', 'Talk', 0.3, ''),
    ('sit-side', 'Sit', 0.1, 'bench side'),
    ('point-side', 'Point', 20 / 36, 'side'),
    ('run-side', 'Run', 0.25, 'side'),
    ('crouch-side', 'Crouch', 0.3, 'side'),
]
POSES += [('carry', 'CarryIdle', 0.2, 'rifle'), ('carry-walk', 'CarryWalk', 0.25, 'rifle')]
if len(opts.get('--poses', '')):
    POSES = [p for p in POSES if p[0] in opts['--poses'].split(',')]

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = scene.render.resolution_y = 640
scene.render.fps = 24
scene.view_settings.view_transform = 'AgX'
world = bpy.data.worlds.new('World')
scene.world = world
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.32, 0.36, 0.42, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.9

bpy.ops.import_scene.gltf(filepath=GLB)
rig = next(o for o in scene.objects if o.type == 'ARMATURE')
meshes = [o for o in scene.objects if o.type == 'MESH' and len(o.vertex_groups)]  # skip importer bone shapes

# ---- summary
dg = bpy.context.evaluated_depsgraph_get()
tot = 0
for o in meshes:
    me = o.data
    me.calc_loop_triangles()
    tot += len(me.loop_triangles)
    print('SUMMARY mesh %-14s tris=%6d mats=%s colors=%s uv=%d groups=%s' % (
        o.name, len(me.loop_triangles), [m.name for m in me.materials], [c.name for c in me.color_attributes],
        len(me.uv_layers), sorted(g.name for g in o.vertex_groups)))
print('SUMMARY total tris', tot, 'bones', [b.name for b in rig.data.bones])
for a in bpy.data.actions:
    print('SUMMARY action %-10s frames %s' % (a.name, tuple(a.frame_range)))
mn = Vector([min((o.matrix_world @ Vector(c))[i] for o in meshes for c in o.bound_box) for i in range(3)])
mx = Vector([max((o.matrix_world @ Vector(c))[i] for o in meshes for c in o.bound_box) for i in range(3)])
print('SUMMARY bounds (Blender Z-up)', tuple(round(x, 3) for x in mn), tuple(round(x, 3) for x in mx))

# ---- studio
bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
floor = bpy.context.object
fm = bpy.data.materials.new('floor')
fm.use_nodes = True
fm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.45, 0.47, 0.5, 1)
floor.data.materials.append(fm)
# seat 0.40 m high; its front edge is right under his origin (Blender -Y = forward)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0.205, 0.2))
bench = bpy.context.object
bench.scale = (1.2, 0.4, 0.4)
bm = bpy.data.materials.new('bench')
bm.use_nodes = True
bm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.35, 0.22, 0.12, 1)
bench.data.materials.append(bm)
bpy.ops.object.light_add(type='SUN', rotation=(math.radians(50), math.radians(10), math.radians(25)))
bpy.context.object.data.energy = 3.2
bpy.context.object.data.angle = math.radians(8)
bpy.ops.object.light_add(type='AREA', location=(-2.5, -2.5, 2.0))
fill = bpy.context.object
fill.data.energy = 250
fill.data.size = 3
fill.rotation_euler = (Vector((0, 0, 0.6)) - fill.location).to_track_quat('-Z', 'Y').to_euler()
bpy.ops.object.camera_add()
cam = bpy.context.object
scene.camera = cam


def aim(loc, target, lens, ortho=False):
    cam.location = loc
    cam.data.type = 'ORTHO' if ortho else 'PERSP'
    cam.data.ortho_scale = 1.5
    cam.data.lens = lens
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()


def find_action(name):
    for a in bpy.data.actions:
        if a.name == name or a.name.startswith(name + '_') or a.name.startswith(name + '.'):
            return a
    raise KeyError(name)


ad = rig.animation_data or rig.animation_data_create()
for t in ad.nla_tracks:
    t.mute = True


def set_clip(name, frac):
    if name is None:
        ad.action = None
        for pb in rig.pose.bones:
            pb.rotation_quaternion = (1, 0, 0, 0)
            pb.location = (0, 0, 0)
            pb.scale = (1, 1, 1)
        scene.frame_set(0)
        return
    act = find_action(name)
    ad.action = act
    if ad.action_slot is None and len(act.slots):
        ad.action_slot = act.slots[0]
    f0, f1 = act.frame_range
    frame = f0 + (f1 - f0) * frac
    scene.frame_set(int(frame), subframe=frame - int(frame))


rifle = bpy.data.objects.get('Rifle')
for label, clip, frac, extra in POSES:
    if clip and not any(a.name == clip or a.name.startswith(clip + '_') for a in bpy.data.actions):
        continue
    if rifle:
        rifle.hide_render = 'rifle' not in extra   # the game hides it unless carrying
    set_clip(clip, frac)
    bench.hide_render = 'bench' not in extra
    tz = 0.52 if 'bench' in extra else 0.47
    if 'side' in extra:
        aim((4.0, 0, tz + 0.35), (0, 0, tz), 62, ortho=True)   # orthographic, from his left
    else:
        aim((1.25, -3.1, 1.0), (0, 0, tz), 62)
    if 'bench' in extra:
        # seat check: lowest deformed vertex above the bench footprint (y in [0.005, 0.405])
        dg = bpy.context.evaluated_depsgraph_get()
        low = []
        for o in meshes:
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
            low += [(ev.matrix_world @ v.co) for v in me.vertices]
            ev.to_mesh_clear()
        over = [v.z for v in low if 0.005 <= v.y <= 0.405 and abs(v.x) < 0.6]
        print('SUMMARY sit: lowest point over bench z=%.3f (seat 0.40), lowest overall z=%.3f' % (min(over), min(v.z for v in low)))
    scene.render.filepath = os.path.join(OUT, '%s_%s.png' % (PREFIX, label))
    bpy.ops.render.render(write_still=True)
    print('RENDERED', scene.render.filepath)

set_clip(None, 0)
bench.hide_render = True
if rifle:
    rifle.hide_render = True
aim((0.35, -1.6, 0.8), (0, 0, 0.74), 85)
scene.render.filepath = os.path.join(OUT, '%s_face.png' % PREFIX)
bpy.ops.render.render(write_still=True)
print('RENDERED', scene.render.filepath)
