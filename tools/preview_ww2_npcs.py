"""
Render EEVEE preview line-ups of the exported NPC GLBs (re-imported, so this also verifies
that skins + clips survive the glTF round trip).

  Blender --background --factory-startup --python tools/preview_ww2_npcs.py -- [--tier desktop|mobile]

Writes docs/previews/npcs/lineup_idle.png, lineup_walk.png, lineup_cower.png, faces.png, lineup_extra.png
"""
import bpy, os, sys, math
from mathutils import Vector, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
MODELS = os.path.join(PROJECT, 'public', 'assets', 'models')
OUT = os.path.join(PROJECT, 'docs', 'previews', 'npcs')
SPARKY = os.path.join(PROJECT, 'public', 'assets', 'models', 'sparky-ww2.glb')   # in-game Sparky, ~1.0 m
ORDER = ['boon', 'siti', 'ahma', 'hassan', 'rajan', 'soldier', 'oldboon']

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
tier = 'desktop'
if '--tier' in argv: tier = argv[argv.index('--tier') + 1]
suffix = '' if tier == 'desktop' else '-mobile'
PREFIX = ''
if '--order' in argv:            # e.g. --order shopkeeper-cn,woman-cn --prefix town_
    ORDER = argv[argv.index('--order') + 1].split(',')
if '--prefix' in argv: PREFIX = argv[argv.index('--prefix') + 1]
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'
sc.render.fps = 30
sc.render.resolution_x = 1800; sc.render.resolution_y = 900
sc.render.film_transparent = False
try:
    sc.eevee.use_shadows = True
except Exception: pass
try:
    sc.eevee.taa_render_samples = 48
except Exception: pass
sc.view_settings.view_transform = 'AgX'
sc.view_settings.look = 'None'

world = bpy.data.worlds.new('W'); sc.world = world
world.use_nodes = True
bg = world.node_tree.nodes['Background']; bg.inputs[0].default_value = (0.42, 0.47, 0.53, 1); bg.inputs[1].default_value = 0.9

def light(name, typ, loc, rot, energy, size=1.0, color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, typ); ld.energy = energy; ld.color = color
    if typ == 'AREA': ld.size = size
    if typ == 'SUN': ld.angle = math.radians(8)
    ob = bpy.data.objects.new(name, ld); ob.location = loc; ob.rotation_euler = Euler([math.radians(a) for a in rot])
    sc.collection.objects.link(ob); return ob

light('Key', 'SUN', (0, 0, 10), (48, 0, -32), 3.2, color=(1.0, 0.96, 0.9))
light('Fill', 'AREA', (-4, -6, 3), (70, 0, -35), 900, size=6, color=(0.85, 0.9, 1.0))
light('Rim', 'AREA', (3, 5, 3.5), (-60, 0, 150), 500, size=4)

# floor
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
floor = bpy.context.active_object
fm = bpy.data.materials.new('Floor'); fm.use_nodes = True
fb = fm.node_tree.nodes['Principled BSDF']; fb.inputs['Base Color'].default_value = (0.55, 0.57, 0.6, 1); fb.inputs['Roughness'].default_value = 0.9
floor.data.materials.append(fm)

chars = {}
x = 0.0
spacing = {'box': 0.9, 'sparky': 1.0, 'boon': 0.85, 'siti': 0.9, 'ahma': 1.0, 'hassan': 1.0, 'rajan': 1.0, 'soldier': 1.0, 'oldboon': 1.0}

# reference 1.0 m box
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0.5))
box = bpy.context.active_object; box.scale = (0.3, 0.3, 1.0); box.location = (0, 0, 0.5)
bm_ = bpy.data.materials.new('Box'); bm_.use_nodes = True
bb = bm_.node_tree.nodes['Principled BSDF']; bb.inputs['Base Color'].default_value = (0.8, 0.35, 0.2, 1)
box.data.materials.append(bm_)
positions = {'box': 0.0}
x = 0.0

def import_glb(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    roots = [o for o in new if o.parent is None]
    return new, roots

stats = {}
if os.path.exists(SPARKY):
    new, roots = import_glb(SPARKY)
    x += spacing['sparky']
    for r in roots: r.location.x += x
    positions['sparky'] = x
    chars['sparky'] = (new, roots)
    sm = [o for o in new if o.type == 'MESH']
    bpy.context.view_layer.update()
    print('[SPARKY] height', round(max((m.matrix_world @ Vector(c)).z for m in sm for c in m.bound_box), 3))

for cid in ORDER:
    path = os.path.join(MODELS, f'npc-{cid}{suffix}.glb')
    new, roots = import_glb(path)
    x += spacing.get(cid, 1.0)
    for r in roots: r.location.x += x
    positions[cid] = x
    arm = next(o for o in new if o.type == 'ARMATURE')
    meshes = [o for o in new if o.type == 'MESH']
    tris = 0
    for m in meshes:
        m.data.calc_loop_triangles(); tris += len(m.data.loop_triangles)
    chars[cid] = (new, roots, arm)
    stats[cid] = dict(tris=tris, file_kb=round(os.path.getsize(path) / 1024), height=round(max((m.matrix_world @ Vector(c)).z for m in meshes for c in m.bound_box), 3))

# clip lookup per armature: glTF importer keeps actions in NLA tracks
def clip_action(arm, clip):
    ad = arm.animation_data
    cands = []
    if ad:
        for tr in ad.nla_tracks:
            for st in tr.strips:
                if st.action and (st.action.name == clip or st.action.name.startswith(clip + '_') or tr.name == clip):
                    cands.append((st.action, st))
        if ad.action and ad.action.name.startswith(clip):
            cands.append((ad.action, None))
    for a in bpy.data.actions:
        if a.name == clip or a.name.startswith(clip + '_'):
            cands.append((a, None))
    return cands[0] if cands else (None, None)

def set_clip(clip, frame):
    for cid, v in chars.items():
        if cid == 'sparky': continue
        arm = v[2]
        ad = arm.animation_data or arm.animation_data_create()
        for tr in ad.nla_tracks: tr.mute = True
        act, st = clip_action(arm, clip)
        if act is None:
            print('!! missing clip', clip, 'on', cid); continue
        ad.action = act
        try:
            if st is not None and st.action_slot is not None:
                ad.action_slot = st.action_slot
            elif len(act.slots):
                ad.action_slot = act.slots[0]
        except Exception as e:
            print('slot', e)
    sc.frame_set(frame)

# report clips
for cid in ORDER:
    arm = chars[cid][2]
    names = []
    ad = arm.animation_data
    if ad:
        for tr in ad.nla_tracks:
            for st in tr.strips:
                names.append(f'{tr.name}:{st.action.name}[{st.frame_start:.0f}-{st.frame_end:.0f}]')
    print('[CLIPS]', cid, stats[cid], names)

cam_d = bpy.data.cameras.new('Cam'); cam = bpy.data.objects.new('Cam', cam_d); sc.collection.objects.link(cam)
sc.camera = cam

def shoot(fname, center_x, dist, height, focal=50, look_z=0.8, yaw=0.0, resx=1800, resy=900):
    sc.render.resolution_x = resx; sc.render.resolution_y = resy
    cam_d.lens = focal
    a = math.radians(yaw)
    cam.location = (center_x + dist * math.sin(a), -dist * math.cos(a), height)
    d = Vector((center_x, 0, look_z)) - cam.location
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = os.path.join(OUT, PREFIX + fname)
    bpy.ops.render.render(write_still=True)
    print('[PNG]', sc.render.filepath)

mid = x / 2
if PREFIX:
    set_clip('Sit', 1)
    shoot(f'lineup_sit{suffix}.png', mid, 12.5, 1.3, focal=50, look_z=0.6, yaw=35)
set_clip('Idle', 1)
shoot(f'lineup_idle{suffix}.png', mid, 12.5, 1.5, focal=50, look_z=0.8, yaw=8)
set_clip('Walk', 7)
shoot(f'lineup_walk{suffix}.png', mid, 12.5, 1.5, focal=50, look_z=0.8, yaw=30)
set_clip('Cower', 10)
shoot(f'lineup_cower{suffix}.png', mid, 12.5, 1.5, focal=50, look_z=0.7, yaw=20)
if tier == 'desktop' and not PREFIX:
    set_clip('Idle', 1)
    # face close-ups: frame the heads
    shoot('faces.png', positions['siti'] + (positions['hassan'] - positions['siti']) / 2, 6.0, 1.45, focal=85, look_z=1.25, yaw=0)
    shoot('faces_2.png', positions['hassan'] + (positions['soldier'] - positions['hassan']) / 2, 6.0, 1.6, focal=85, look_z=1.4, yaw=0)
    shoot('faces_boon.png', positions['boon'], 3.0, 1.0, focal=85, look_z=0.9, yaw=0, resx=900, resy=900)
    set_clip('Wave', 20)
    shoot('lineup_wave.png', mid, 12.5, 1.5, focal=50, look_z=0.8, yaw=-10)
    set_clip('Sit', 1)
    shoot('lineup_sit.png', mid, 12.5, 1.3, focal=50, look_z=0.6, yaw=35)
    set_clip('Idle', 1)
    shoot('lineup_back.png', mid, 12.5, 1.6, focal=50, look_z=0.8, yaw=150)
    set_clip('Run', 5)
    shoot('lineup_run.png', mid, 12.5, 1.4, focal=50, look_z=0.8, yaw=60)
    set_clip('Cower', 10)
    shoot('lineup_cower_side.png', mid, 12.5, 1.4, focal=50, look_z=0.6, yaw=70)
    set_clip('Talk', 15)
    shoot('lineup_talk.png', mid, 12.5, 1.5, focal=50, look_z=0.8, yaw=-20)
