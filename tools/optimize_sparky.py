"""Optimise the Godot-era Sparky outfits into light, game-ready GLBs for three.js.

Run (normally via tools/optimize_sparky.sh, which also post-processes with gltf-transform):

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python tools/optimize_sparky.py -- --out /tmp/sparky-raw \
        [--outfits ww2,ns,original] [--tiers desktop,mobile]

For every outfit x tier it writes <out>/<stem><suffix>.glb (uncompressed, JPEG textures):
    sparky-ww2.glb / sparky-ww2-mobile.glb      (WW2 civilian, SparkyDiscovery outfits/sparky-ww2-civilian.blend)
    sparky-ns.glb  / sparky-ns-mobile.glb       (NS 1967 recruit + "Rifle" prop mesh)
    sparky-ind.glb / sparky-ind-mobile.glb      (1965 kopitiam helper, tools/build_sparky_1965.py)
    sparky.glb     / sparky-mobile.glb          (original navy hoodie)

What it does (sources are opened read-only, never saved):
  1. Authors extra actions on the untouched 7-bone rig: Run, Talk, Cheer, Snap, Point, Crouch, Sit.
  2. Drops the "Short pile" fibre shells (single-triangle fibres; side-by-side EEVEE renders
     showed only a faint rim fuzz on ears/paws, not worth ~13k tris + 3 materials) and
     studio props, applies non-armature modifiers, decimates every part to a per-tier triangle
     target (big smooth parts hardest, face details least).
  3. Bakes each source material's base colour into a COLOR_0 vertex colour and merges all parts
     into 3 skinned meshes / 3 materials: Sparky_Plush (plush normal map), Sparky_Cloth
     (cotton-weave normal map), Sparky_Face (glossy eyes/nose/mouth); NS also gets "Rifle".
  4. Scales to 1.0 m (feet at 0, facing Blender -Y = three.js +Z) and renames the bones
     arm.L -> arm_L etc. (three.js strips '.' from node names).
  5. Exports GLB (Y-up, rest pose, one glTF animation per action).
"""
import bpy
import bmesh
import math
import os
import sys
from mathutils import Vector, Quaternion, Matrix

# --------------------------------------------------------------------------- config
SRC = os.environ.get('SPARKY_SRC', '/Users/cy/Code/Games/SparkyDiscovery/assets/sparky')
OUTFITS = {
    'ww2': (os.path.join(SRC, 'outfits', 'sparky-ww2-civilian.blend'), 'sparky-ww2'),
    'ns': (os.path.join(SRC, 'outfits', 'sparky-ns-1967.blend'), 'sparky-ns'),
    'ind': (os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sparky_outfits', 'sparky-1965-helper.blend'), 'sparky-ind'),
    'original': (os.path.join(SRC, 'sparky.blend'), 'sparky'),
}
TIERS = {
    # jpeg: texture quality. Source normal maps are 512^2 (no more detail exists), so both tiers
    # keep 512^2; desktop gets higher JPEG quality and ~2.5x the geometry.
    'desktop': dict(suffix='', jpeg=95),
    'mobile': dict(suffix='-mobile', jpeg=85),
}
SOURCE_HEIGHT = 2.1156          # ear tips of the hooded source, in Blender units
SCALE = 1.0 / SOURCE_HEIGHT     # -> 1.0 m tall (shared by all outfits so clips are identical)
BENCH_HEIGHT = 0.40             # metres; Sit clip puts his seat on this height
FPS = 24
BONE_RENAME = {'arm.L': 'arm_L', 'arm.R': 'arm_R', 'leg.L': 'leg_L', 'leg.R': 'leg_R'}

# Source material -> merged group (anything unlisted -> 'cloth')
GROUP_OF = {
    'Warm honey plush': 'plush', 'Soft cream muzzle': 'plush',
    'Glossy button eyes': 'face', 'Embroidered charcoal': 'face',
    'Rifle charcoal furniture': 'rifle', 'Rifle grey metal': 'rifle',
    'Plush fibre 0': 'pile', 'Plush fibre 1': 'pile', 'Plush fibre 2': 'pile',
}
GROUP_OBJECT = {'plush': 'Sparky_Plush', 'cloth': 'Sparky_Cloth', 'face': 'Sparky_Face', 'rifle': 'Rifle'}

# Per-part triangle targets: (substring, mobile, desktop). None = keep as is. First match wins.
TARGETS = [
    ('Short pile', 0, 0),                       # fibre shells: dropped
    ('Bear head', 2400, 7000),
    ('Continuous fabric hood', 1800, 5500),
    ('Soft folded hood edge', 450, 1400),
    ('Fine hood stitching', 300, 1000),
    ('Hoodie soft torso', 1300, None),
    ('Soft sleeve', 700, None),
    ('Fabric cuff', 260, 700),
    ('Soft knitted hem', 360, None),
    ('Soft ear', 320, 900),
    ('Ear inset', 200, 700),
    ('Mitten paw', 320, 900),
    ('Button eye', 220, 800),
    ('Velvet nose', 260, 800),
    ('Embroidered', None, None),
    ('Continuous stuffed leg', 500, None),
    ('DSTA chest lettering', 1300, None),
    ('Drawstring knot', 110, 400),
    ('Drawstring tip', 110, 400),
    ('Flat sewn kangaroo pocket', 350, 1000),
    ('Short cloth placket', 140, 500),
    ('Workwear patch pocket', 140, 500),
    ('Mended cloth patch', 140, 500),
    ('Shirt breast pocket', 140, 500),
    ('Breast pocket flap', 140, 500),
    ('Shirt button placket', 140, 500),
    ('Wood button', 70, 240),
    ('Satchel button', 70, 240),
    ('Shirt button', 70, 240),
    ('Pocket button', 70, 240),
    ('Cloth shoe', 340, None),
    ('Boot toe', 340, None),
    ('Shoe upper', 120, None),
    ('Satchel front strap', 100, 300),
    ('Satchel rear strap', 100, 300),
    ('Canvas satchel', 120, None),
    ('Satchel folded flap', 120, None),
    ('Rounded shoulder', 300, 960),
    ('Green field cap crown', 380, None),
    ('Field cap band', 220, 700),
    ('Soft cap peak', 240, 700),
    ('Belt buckle', 80, None),
    ('Rifle', 70, None),                         # only the 188-tri bevelled boxes get reduced
]
SYMMETRIC = ('Bear head', 'Continuous fabric hood', 'Soft folded hood edge', 'Fine hood stitching',
             'Hoodie soft torso', 'Soft knitted hem', 'Velvet nose', 'Flat sewn kangaroo pocket',
             'Green field cap crown', 'Field cap band', 'Soft cap peak')


def log(*a):
    print('[optimize_sparky]', *a, flush=True)


# --------------------------------------------------------------------------- animation helpers
def rx(deg):
    return Quaternion((1, 0, 0), math.radians(deg))


def ry(deg):
    return Quaternion((0, 1, 0), math.radians(deg))


def rz(deg):
    return Quaternion((0, 0, 1), math.radians(deg))


def ease(t):
    return t * t * (3 - 2 * t)


def channelbag_fcurves(action):
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                yield bag, list(bag.fcurves)


class Poser:
    """Pose the plush rig with readable parameters and key every frame.

    Conventions (Blender armature space, character faces -Y, Z up):
      * pitch  > 0: lean/nod forward (top moves towards -Y)
      * roll   > 0: tilt to the character's left (+X), yaw > 0: turn face to his left
      * arm direction (out, fwd, up) is given for the LEFT arm and mirrored for the right,
        relative to the torso; it is applied as a delta from the Idle arm rotation so crossfades
        from Idle never twist the sleeves.
      * leg fwd > 0 swings the foot forward, out > 0 splays it outward, lift raises the leg.
      * root/body offsets (side, fwd, up) are in source units (2.1156 = full height).
    """

    def __init__(self, rig):
        self.rig = rig
        self.R = {pb.name: pb.bone.matrix_local.to_quaternion() for pb in rig.pose.bones}
        idle = bpy.data.actions['Idle']
        self.assign(idle)
        bpy.context.scene.frame_set(1)
        bpy.context.view_layer.update()
        self.w_idle, self.relaxed = {}, {}
        for side in 'LR':
            pb = rig.pose.bones['arm.' + side]
            r = self.R[pb.name]
            self.w_idle[side] = r @ pb.rotation_quaternion @ r.inverted()
            paw = bpy.data.objects['Mitten paw ' + side]
            centre = sum((paw.matrix_world @ v.co for v in paw.data.vertices), Vector()) / len(paw.data.vertices)
            # evaluate the rest-pose direction (paw vertices are stored in rest space)
            rest_dir = (centre - pb.bone.head_local).normalized()
            self.relaxed[side] = self.w_idle[side] @ rest_dir
        self.hip = {s: rig.data.bones['leg.' + s].head_local.copy() for s in 'LR'}
        self.leg_len = (self.hip['L'].z - 0.0)
        # relaxed arm in (out, fwd, up)
        d = self.relaxed['L']
        self.REL_ARM = (d.x, -d.y, d.z)
        self.assign(None)

    def assign(self, action):
        ad = self.rig.animation_data or self.rig.animation_data_create()
        ad.action = action
        if action is not None and ad.action_slot is None and len(action.slots):
            ad.action_slot = action.slots[0]

    def base(self):
        return dict(root=(0, 0, 0), root_pitch=0, body=(0, 0, 0), body_pitch=0, body_roll=0, body_yaw=0,
                    head_pitch=0, head_roll=0, head_yaw=0, armL=self.REL_ARM, armR=self.REL_ARM,
                    legL=(0, 0, 0), legR=(0, 0, 0))  # leg: (fwd deg, out deg, lift)

    @staticmethod
    def world_vec(side_fwd_up):
        s, f, u = side_fwd_up
        return Vector((s, -f, u))

    def arm_q(self, side, d):
        out, fwd, up = d
        target = Vector((out if side == 'L' else -out, -fwd, up)).normalized()
        return self.relaxed[side].rotation_difference(target) @ self.w_idle[side]

    @staticmethod
    def leg_q(side, fwd, out):
        return (ry(-out) if side == 'L' else ry(out)) @ rx(-fwd)

    def world_pose(self, p):
        """-> {bone: (world rotation, world location offset)}"""
        return {
            'root': (rx(p['root_pitch']), self.world_vec(p['root'])),
            'body': (rz(p['body_yaw']) @ ry(p['body_roll']) @ rx(p['body_pitch']), self.world_vec(p['body'])),
            'head': (rz(p['head_yaw']) @ ry(p['head_roll']) @ rx(p['head_pitch']), Vector()),
            'arm.L': (self.arm_q('L', p['armL']), Vector()),
            'arm.R': (self.arm_q('R', p['armR']), Vector()),
            'leg.L': (self.leg_q('L', *p['legL'][:2]), Vector((0, 0, p['legL'][2]))),
            'leg.R': (self.leg_q('R', *p['legR'][:2]), Vector((0, 0, p['legR'][2]))),
        }

    def apply(self, p):
        prev = {}
        for name, (q, loc) in self.world_pose(p).items():
            pb = self.rig.pose.bones[name]
            r = self.R[name]
            local = r.inverted() @ q @ r
            last = pb.rotation_quaternion
            if local.dot(last) < 0:
                local.negate()
            pb.rotation_quaternion = local
            pb.location = r.inverted() @ loc
            pb.scale = (1, 1, 1)
            prev[name] = local
        return prev

    def bake(self, name, frames, pose_at):
        """Create action `name` keyed on every frame 1..frames from pose_at(frame)->params."""
        action = bpy.data.actions.new(name)
        action.use_fake_user = True
        self.assign(action)
        for pb in self.rig.pose.bones:
            pb.rotation_quaternion = (1, 0, 0, 0)
        for f in range(1, frames + 1):
            self.apply(pose_at(f))
            for pb in self.rig.pose.bones:
                for path in ('rotation_quaternion', 'location', 'scale'):
                    pb.keyframe_insert(data_path=path, frame=f, group=pb.name)
        track = self.rig.animation_data.nla_tracks.new()
        track.name = name
        track.strips.new(name, 1, action)
        track.mute = True
        self.assign(None)
        log('authored', name, frames, 'frames', round((frames - 1) / FPS, 3), 's')
        return action

    def keyed(self, keys):
        """keys: [(frame, params-override-dict)] -> pose_at(frame) with smoothstep easing."""
        full = []
        for frame, over in keys:
            p = self.base()
            p.update(over)
            full.append((frame, p))

        def lerp(a, b, t):
            if isinstance(a, tuple):
                return tuple(x + (y - x) * t for x, y in zip(a, b))
            return a + (b - a) * t

        def pose_at(f):
            if f <= full[0][0]:
                return full[0][1]
            for (f0, p0), (f1, p1) in zip(full, full[1:]):
                if f0 <= f <= f1:
                    t = ease((f - f0) / (f1 - f0))
                    return {k: lerp(p0[k], p1[k], t) for k in p0}
            return full[-1][1]
        return pose_at


def author_actions(rig):
    P = Poser(rig)
    REL = P.REL_ARM
    tau = math.tau

    def pose(**kw):
        p = P.base()
        p.update(kw)
        return p

    def swing_arm(angle_deg, out=0.42, lift=0.0):
        a = math.radians(angle_deg)
        return (out, math.sin(a), -math.cos(a) + lift)

    # ---- Run: loop, 16-frame cycle (0.667 s), longer stride, forward lean, bouncy.
    def run(f):
        ph = tau * (f - 1) / 16
        s, c = math.sin(ph), math.cos(ph)
        lift_l = 0.07 * max(0.0, c) ** 1.5
        lift_r = 0.07 * max(0.0, -c) ** 1.5
        return pose(
            root=(0.022 * s, 0, -0.075 + 0.13 * abs(c)),
            body_pitch=13 + 3 * math.cos(2 * ph), body_yaw=8 * s, body_roll=-2.5 * s,
            head_pitch=-9 + 2.5 * math.cos(2 * ph), head_yaw=-6 * s, head_roll=2 * s,
            armL=swing_arm(-48 * math.sin(ph - 0.35), 0.48, 0.12), armR=swing_arm(48 * math.sin(ph - 0.35), 0.48, 0.12),
            legL=(38 * s, 3, lift_l), legR=(-38 * s, 3, lift_r))
    P.bake('Run', 17, run)

    # ---- Talk: loop, 2 s. Gentle head bob, right paw gestures while explaining.
    def talk(f):
        ph = tau * (f - 1) / 48
        return pose(
            root=(0, 0, 0.008 * (1 - math.cos(2 * ph))),
            body_pitch=1.5 * math.sin(2 * ph + 0.6), body_roll=1.5 * math.sin(ph), body_yaw=-4 + 2 * math.sin(ph),
            head_pitch=4 * math.sin(2 * ph), head_roll=5 * math.sin(ph + 0.4), head_yaw=4 + 5 * math.sin(ph + 1.2),
            armR=(0.55 + 0.12 * math.sin(ph), 0.62 + 0.12 * math.sin(2 * ph + 0.5), -0.28 + 0.2 * math.sin(2 * ph)),
            armL=(REL[0], REL[1] + 0.05 * math.sin(ph), REL[2]))
    P.bake('Talk', 49, talk)

    # ---- Cheer: one-shot ~1.2 s. Anticipation squash, hop with both arms up, land, settle.
    up_v = (0.5, 0.12, 0.86)
    P.bake('Cheer', 30, P.keyed([
        (1, {}),
        (6, dict(body=(0, 0, -0.05), body_pitch=10, head_pitch=8, armL=(0.62, -0.25, -0.75), armR=(0.62, -0.25, -0.75),
                 legL=(0, 5, 0), legR=(0, 5, 0))),
        (11, dict(root=(0, 0, 0.2), body_pitch=-7, head_pitch=-14, armL=up_v, armR=up_v,
                  legL=(10, 9, 0), legR=(10, 9, 0))),
        (14, dict(root=(0, 0, 0.24), body_pitch=-8, head_pitch=-16, armL=(0.42, 0.1, 0.9), armR=(0.42, 0.1, 0.9),
                  legL=(6, 10, 0), legR=(6, 10, 0))),
        (18, dict(root=(0, 0, 0.0), body_pitch=3, head_pitch=-8, armL=(0.55, 0.1, 0.83), armR=(0.55, 0.1, 0.83))),
        (20, dict(body=(0, 0, -0.045), body_pitch=7, head_pitch=2, armL=(0.62, 0.1, 0.78), armR=(0.62, 0.1, 0.78),
                  legL=(0, 4, 0), legR=(0, 4, 0))),
        (23, dict(body_pitch=-3, head_pitch=-9, head_roll=5, armL=(0.42, 0.1, 0.9), armR=(0.42, 0.1, 0.9))),
        (30, {}),
    ]))

    # ---- Snap: one-shot ~1.1 s. Paws to chest holding a box camera, look down into the
    # viewfinder, "click" (tiny dip), hold, lower. Paws meet ~0.25 m in front of the chest.
    cam_l = (-0.27, 0.55, -0.13)
    P.bake('Snap', 27, P.keyed([
        (1, {}),
        (7, dict(body_pitch=5, head_pitch=16, armL=(-0.25, 0.55, -0.04), armR=(-0.25, 0.55, -0.04))),
        (10, dict(body_pitch=6, head_pitch=24, armL=cam_l, armR=cam_l)),
        (13, dict(body=(0, 0, -0.018), body_pitch=8, head_pitch=27, armL=(-0.27, 0.55, -0.17), armR=(-0.27, 0.55, -0.17))),
        (15, dict(body_pitch=6, head_pitch=24, armL=cam_l, armR=cam_l)),
        (19, dict(body_pitch=6, head_pitch=23, head_roll=3, armL=cam_l, armR=cam_l)),
        (27, {}),
    ]))

    # ---- Point: one-shot 1.5 s, right arm points forward (three.js +Z), slight lean in.
    point_r = (0.08, 0.96, 0.25)
    P.bake('Point', 37, P.keyed([
        (1, {}),
        (6, dict(body_yaw=-4, armR=(0.6, -0.2, -0.75), head_pitch=3)),
        (11, dict(body_yaw=12, body_pitch=5, head_yaw=-10, head_pitch=-4, armR=(0.08, 0.93, 0.36),
                  armL=(0.55, -0.18, -0.8))),
        (14, dict(body_yaw=10, body_pitch=4, head_yaw=-8, head_pitch=-3, armR=point_r, armL=(0.55, -0.15, -0.8))),
        (28, dict(body_yaw=10, body_pitch=4, head_yaw=-8, head_pitch=-2, head_roll=3, armR=(0.08, 0.96, 0.22),
                  armL=(0.55, -0.15, -0.8))),
        (37, {}),
    ]))

    # ---- Crouch: loop 2 s. Squats low, curls forward, paws pressed over his head, trembling.
    leg_fwd, leg_out = 45, 16
    drop = P.hip['L'].z * (1 - math.cos(math.radians(leg_fwd)) * math.cos(math.radians(leg_out)))

    def crouch(f):
        ph = tau * (f - 1) / 48
        shiver = math.sin(8 * ph)
        return pose(
            root=(0, 0, -drop + 0.004 * shiver),
            body_pitch=24 + 2 * math.sin(ph), body_roll=1.2 * shiver, body=(0, 0, 0.01 * math.sin(2 * ph)),
            head_pitch=15 - 5 * max(0.0, math.sin(ph)) ** 3, head_yaw=4 * math.sin(ph) ** 3, head_roll=-1.0 * shiver,
            armL=(0.18, 0.5, 0.85), armR=(0.18, 0.5, 0.85),
            legL=(leg_fwd, leg_out, 0), legR=(leg_fwd, leg_out, 0))
    P.bake('Crouch', 49, crouch)

    # ---- Sit: loop 3 s on a bench whose seat is BENCH_HEIGHT above the floor his origin stands on.
    # Legs dangle forward over the front edge and swing, paws rest beside the hips.
    def sit(f):
        ph = tau * (f - 1) / 72
        kick = math.sin(2 * ph)
        return pose(
            root=(0, 0, 0.006 * math.sin(2 * ph)),
            # hips flex: torso settles down between the raised thighs so his bottom meets the seat
            body=(0, 0.02, -0.16 + 0.006 * math.sin(2 * ph + 1)),
            body_pitch=-4 + 1.5 * math.sin(2 * ph + 1), body_roll=1.2 * math.sin(ph),
            head_pitch=-2 + 3 * math.sin(2 * ph + 0.3), head_yaw=14 * math.sin(ph), head_roll=4 * math.sin(ph + 0.5),
            armL=(0.52, 0.28, -0.8), armR=(0.52, 0.28, -0.8),
            legL=(SIT_LEG_FWD + 9 * kick, 8, 0), legR=(SIT_LEG_FWD - 9 * kick, 8, 0))
    settle_on_seat(rig, P, P.bake('Sit', 73, sit), 73)


SIT_LEG_FWD = 62
SEAT_EDGE = 0.01   # source units behind the origin (Blender +Y): the seat's front edge is at his origin


def settle_on_seat(rig, P, action, frames):
    """Lift the Sit clip so the lowest point over the seat (all frames) rests on BENCH_HEIGHT."""
    P.assign(action)
    lowest = 1e9
    for f in range(1, frames + 1):
        bpy.context.scene.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        for obj in rig.children:
            if obj.type != 'MESH' or obj.name.startswith(('Short pile', 'Rifle')):
                continue
            ev = obj.evaluated_get(dg)
            me = ev.to_mesh()
            for v in me.vertices:
                w = ev.matrix_world @ v.co
                if w.y > SEAT_EDGE:   # only what is over the seat (the dangling feet are in front)
                    lowest = min(lowest, w.z)
            ev.to_mesh_clear()
    lift = BENCH_HEIGHT * SOURCE_HEIGHT - lowest
    r = P.R['root']
    local = r.inverted() @ Vector((0, 0, lift))
    for bag, fcurves in channelbag_fcurves(action):
        for fc in fcurves:
            if fc.data_path == 'pose.bones["root"].location':
                for k in fc.keyframe_points:
                    for attr in ('co', 'handle_left', 'handle_right'):
                        getattr(k, attr)[1] += local[fc.array_index]
    P.assign(None)
    log('Sit: lowest seat point %.3f -> lifted by %.3f source units (seat %.2f m)' % (lowest, lift, BENCH_HEIGHT))


# --------------------------------------------------------------------------- mesh helpers
def target_for(name, tris, tier):
    for key, mobile, desktop in TARGETS:
        if key in name:
            t = mobile if tier == 'mobile' else desktop
            return tris if t is None else min(tris, t)
    return tris


def tri_count(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def select_only(objs, active=None):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active or objs[0]


def base_color(mat):
    bsdf = mat.node_tree.nodes.get('Principled BSDF') if mat and mat.use_nodes else None
    if bsdf is None:
        return (0.5, 0.5, 0.5, 1)
    return tuple(bsdf.inputs['Base Color'].default_value)


def box_uv(me, scale=1.6):
    uv = me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        n = poly.normal
        axis = max(range(3), key=lambda i: abs(n[i]))
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            a, b = [co[i] for i in range(3) if i != axis]
            uv.data[li].uv = (a * scale, b * scale)


def prepare_part(obj, tier):
    """Apply modifiers/transforms, bake colour, decimate. Returns group name or None (dropped)."""
    mats = [s.material for s in obj.material_slots]
    group = GROUP_OF.get(mats[0].name if mats and mats[0] else '', 'cloth')
    if group == 'pile' or target_for(obj.name, 1, tier) == 0:
        bpy.data.objects.remove(obj, do_unlink=True)
        return None
    if obj.data.users > 1:
        obj.data = obj.data.copy()
    for m in list(obj.modifiers):
        if m.type == 'ARMATURE':
            obj.modifiers.remove(m)
    select_only([obj])
    for m in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)
    mw = obj.matrix_world.copy()
    obj.parent = None
    obj.matrix_world = mw
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    me = obj.data
    # UVs: exactly one layer called UVMap so joins merge it
    while len(me.uv_layers) > 1:
        me.uv_layers.remove(me.uv_layers[-1])
    if len(me.uv_layers) == 0:
        box_uv(me)
    me.uv_layers[0].name = 'UVMap'
    # Vertex colour = source base colour (linear), per face so multi-material parts keep colours
    col = me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER')
    for poly in me.polygons:
        mat = mats[poly.material_index] if poly.material_index < len(mats) else mats[0]
        c = base_color(mat)
        for li in poly.loop_indices:
            col.data[li].color = (c[0], c[1], c[2], 1.0)
    me.materials.clear()
    # Weld duplicate verts (bevel+subdivide seams) so the decimator can collapse across them
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.to_mesh(me)
    bm.free()
    tris = tri_count(me)
    target = target_for(obj.name, tris, tier)
    # Decimate
    if target < tris:
        mod = obj.modifiers.new('decimate', 'DECIMATE')
        mod.decimate_type = 'COLLAPSE'
        mod.ratio = target / tris
        mod.use_collapse_triangulate = True
        if obj.name.startswith(SYMMETRIC):
            mod.use_symmetry = True
            mod.symmetry_axis = 'X'
        bpy.ops.object.modifier_apply(modifier=mod.name)
    for poly in me.polygons:
        poly.use_smooth = True
    log('  part %-34s %-5s %6d -> %6d (target %d)' % (obj.name[:34], group, tris, tri_count(me), target))
    return group


def make_material(name, group, src_mats, rough):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    # closed plush/face parts are single-sided; the cloth hood is an open shell -> double-sided
    mat.use_backface_culling = group in ('plush', 'face', 'rifle')
    nt = mat.node_tree
    bsdf = nt.nodes['Principled BSDF']
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = 0.0
    bsdf.inputs['Sheen Weight'].default_value = 0.0
    attr = nt.nodes.new('ShaderNodeVertexColor')
    attr.layer_name = 'Col'
    nt.links.new(attr.outputs['Color'], bsdf.inputs['Base Color'])
    src = next((bpy.data.materials.get(n) for n in src_mats if bpy.data.materials.get(n)), None)
    if src is not None:
        img = next((n.image for n in src.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image), None)
        nm_src = next((n for n in src.node_tree.nodes if n.type == 'NORMAL_MAP'), None)
        if img is not None and nm_src is not None:
            tex = nt.nodes.new('ShaderNodeTexImage')
            tex.image = img
            img.colorspace_settings.name = 'Non-Color'
            img.name = {'plush': 'sparky_plush_normal', 'cloth': 'sparky_cotton_normal'}[group]
            nm = nt.nodes.new('ShaderNodeNormalMap')
            nm.inputs['Strength'].default_value = nm_src.inputs['Strength'].default_value
            nt.links.new(tex.outputs['Color'], nm.inputs['Color'])
            nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
    return mat


# --------------------------------------------------------------------------- build
def build(outfit, tier, out_dir):
    path, stem = OUTFITS[outfit]
    bpy.ops.wm.open_mainfile(filepath=path)
    scene = bpy.context.scene
    scene.render.fps = FPS
    rig = bpy.data.objects['Sparky_Rig']
    rig.animation_data.action = None
    for pb in rig.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
    for obj in bpy.data.objects:
        obj.hide_set(False)
        obj.hide_viewport = False
        obj.hide_select = False
    roughness_cloth = bpy.data.materials['Midnight navy cotton'].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value \
        if outfit == 'original' else 0.88

    author_actions(rig)

    # ---- parts
    parts = [o for o in rig.children if o.type == 'MESH']
    for o in [o for o in bpy.data.objects if o not in parts and o != rig]:
        bpy.data.objects.remove(o, do_unlink=True)   # studio camera/lights/floor
    src_tris = sum(tri_count(o.data) for o in parts)
    groups = {}
    for obj in parts:
        name = obj.name
        g = prepare_part(obj, tier)
        if g:
            groups.setdefault(g, []).append(bpy.data.objects[name])
    # ---- merge per group
    mats = {
        'plush': make_material('Sparky_Plush', 'plush', ['Warm honey plush'], 0.95),
        'cloth': make_material('Sparky_Cloth', 'cloth', ['Faded indigo cotton', 'Temasek green cotton', 'Midnight navy cotton'], roughness_cloth),
        'face': make_material('Sparky_Face', 'face', [], 0.3),
        'rifle': make_material('Rifle', 'rifle', [], 0.6),
    }
    merged = []
    for g, objs in groups.items():
        select_only(objs)
        if len(objs) > 1:
            bpy.ops.object.join()
        obj = bpy.context.view_layer.objects.active
        obj.name = obj.data.name = GROUP_OBJECT[g]
        obj.data.materials.clear()
        obj.data.materials.append(mats[g])
        # clean skin weights: max 4 influences, normalised, only real bones
        for vg in list(obj.vertex_groups):
            if vg.name not in rig.data.bones:
                obj.vertex_groups.remove(vg)
        select_only([obj])
        bpy.ops.object.vertex_group_limit_total(limit=4)
        bpy.ops.object.vertex_group_normalize_all(lock_active=False)
        unweighted = sum(1 for v in obj.data.vertices if not any(ge.weight > 0 for ge in v.groups))
        assert unweighted == 0, (obj.name, unweighted)
        for poly in obj.data.polygons:
            poly.material_index = 0
        merged.append(obj)
    for m in list(bpy.data.materials):
        if m.users == 0:
            bpy.data.materials.remove(m)

    # ---- scale to metres, feet on the floor
    S = Matrix.Scale(SCALE, 4)
    for obj in merged:
        obj.data.transform(S)
        obj.data.update()
    select_only([rig])
    bpy.ops.object.mode_set(mode='EDIT')
    for eb in rig.data.edit_bones:
        eb.head = eb.head * SCALE
        eb.tail = eb.tail * SCALE
    bpy.ops.object.mode_set(mode='OBJECT')
    for action in bpy.data.actions:
        for bag, fcurves in channelbag_fcurves(action):
            for fc in fcurves:
                if fc.data_path.endswith('.location'):
                    for k in fc.keyframe_points:
                        k.co[1] *= SCALE
                        k.handle_left[1] *= SCALE
                        k.handle_right[1] *= SCALE
    min_z = min(v.co.z for obj in merged for v in obj.data.vertices if obj.name != 'Rifle')
    assert abs(min_z) < 0.01, min_z

    # ---- rename bones (three.js drops '.' from names) and fix groups/fcurves
    for old, new in BONE_RENAME.items():
        rig.data.bones[old].name = new
        for obj in merged:
            vg = obj.vertex_groups.get(old)
            if vg:
                vg.name = new
    for action in bpy.data.actions:
        for bag, fcurves in channelbag_fcurves(action):
            for fc in fcurves:
                for old, new in BONE_RENAME.items():
                    if '"%s"' % old in fc.data_path:
                        fc.data_path = fc.data_path.replace('"%s"' % old, '"%s"' % new)
            for grp in bag.groups:
                if grp.name in BONE_RENAME:
                    grp.name = BONE_RENAME[grp.name]

    # ---- parent & skin
    for obj in merged:
        obj.parent = rig
        obj.matrix_parent_inverse.identity()
        mod = obj.modifiers.new('Armature', 'ARMATURE')
        mod.object = rig
    rig.animation_data.action = None
    for pb in rig.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)

    tris = {o.name: tri_count(o.data) for o in merged}
    log(stem + TIERS[tier]['suffix'], 'source tris', src_tris, '->', tris, 'total', sum(tris.values()))
    log('actions', [(a.name, tuple(a.frame_range)) for a in bpy.data.actions])

    # ---- export
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, stem + TIERS[tier]['suffix'] + '.glb')
    select_only([rig] + merged, rig)
    bpy.ops.export_scene.gltf(
        filepath=out, export_format='GLB', use_selection=True, export_apply=False,
        export_yup=True, export_skins=True, export_all_influences=False, export_def_bones=False,
        export_leaf_bone=False, export_rest_position_armature=True, export_morph=False,
        export_animations=True, export_animation_mode='ACTIONS', export_force_sampling=True,
        export_anim_slide_to_zero=True, export_optimize_animation_size=False, export_reset_pose_bones=True,
        export_frame_step=1, export_vertex_color='MATERIAL', export_tangents=False,
        export_image_format='JPEG', export_jpeg_quality=TIERS[tier]['jpeg'], export_image_quality=TIERS[tier]['jpeg'],
        export_cameras=False, export_lights=False, export_extras=False)
    log('WROTE', out)
    return out


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    opts = {'--out': None, '--outfits': 'ww2,ns,original', '--tiers': 'desktop,mobile'}
    for i in range(0, len(argv) - 1, 2):
        opts[argv[i]] = argv[i + 1]
    if not opts['--out']:
        raise SystemExit('usage: ... --python optimize_sparky.py -- --out DIR [--outfits ww2,ns,original] [--tiers desktop,mobile]')
    for outfit in opts['--outfits'].split(','):
        for tier in opts['--tiers'].split(','):
            build(outfit, tier, opts['--out'])


if __name__ == '__main__':
    main()
