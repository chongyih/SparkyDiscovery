"""
Sparky Discovery - Chapter 3 (The First Intake, Aug 1967 - 2 Mar 1968) + Ending (2026) NPC builder.

Reuses the Chapter 1 procedural builder (tools/build_ww2_npcs.py: body, rig, clips, palette,
export) and only swaps in the Chapter 3 cast. Same bones and clip names as every other NPC, plus
three clips APPENDED after the existing ones (so every older clip keeps its index and its motion):

  Attention  heels together, arms straight down pressed to the sides, chin up, very still (breath only)
  March      stiff drill quick-march: straight back, straight arms swinging forward to ~shoulder height
             and back, one stride per beat; loops over the character's walk_period (2 paces per loop)
  Carry      walking with both forearms forward at waist height, hands closed round the end rail of
             an iron bed frame (hand centres at the report's `carry_grips`, fixed in root space)

All three are in-place like Walk/Run (the root bone never moves; the game moves the NPC). The new
clip functions live HERE and are appended to B.CLIPS at runtime only, so build_ww2_npcs.py and every
older NPC GLB are untouched. Likewise the extra palette kinds ('starch', 'pixelcamo'), the extra
headwear ('sun_hat'), props ('chevrons', 'tape'), extras ('pace_stick', 'clipboard', 'paper_bag')
and the hair 'waves' are wrappers installed on B in this process only.

Run (or use tools/build_1967_npcs.sh, which also meshopt-compresses the output):
  /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
      --python tools/build_1967_npcs.py -- [--only farid-ns,osman] [--tier desktop|mobile|both] [--out DIR]

Costume notes (docs/research/1967-history.md, docs/design.md "Chapter 3 cast contract"):
  - No. 4 uniform: Temasek green cotton drill, starched stiff (Roots). Long sleeves down, buttoned cuffs,
    two buttoned chest pockets, shirt tucked in, green web belt, trousers bloused over black boots.
    No headwear (no source for 1967 recruit headdress). Recruits march in step: walk_period 1.0 s for
    everyone in uniform = 120 paces a minute.
  - Farid (18) / Ravi (18): the 1965 face DNA (build_1965_npcs.py 'farid' / 'ravi'), two years older.
  - Ah Hock (18): big and broad, crew cut, stubborn frown.  Leo Pereira (18): Eurasian, wavy hair, grin.
  - Sergeant Osman (~35, regular): same uniform + three chevrons on each upper sleeve, moustache,
    pace stick carried under the left arm (the left arm is held in the carry in every clip).
  - Israeli adviser ("Mexicans"): khaki shirt (sleeves rolled) and trousers, straw sun hat, clipboard.
  - Ah Hock's Ah Ma (~70): dark samfu, grey bun, paper bag of oranges.
  - The Minister (background only): generic 1960s official, NOT a likeness: white long-sleeved shirt,
    dark trousers, glasses.
  - Farid (77, 2026): Farid's face DNA aged: white hair, glasses, batik shirt, trousers, sandals.
  - Irfan (18, 2026): today's SAF No. 4 in pixel camouflage (procedural 'pixelcamo'), short hair.
"""
import os, sys
import numpy as np
from math import sin, cos, pi, radians, degrees, atan, atan2, sqrt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_ww2_npcs as B  # noqa: E402
from mathutils import Vector, Matrix  # noqa: E402

body = B.body
P, rot, limb, sgn, lerp, clamp = B.P, B.rot, B.limb, B.sgn, B.lerp, B.clamp

# ======================================================================================
# Palette kinds (wrap B.paint_swatch; B's own kinds are passed through unchanged)
# ======================================================================================
_orig_paint = B.paint_swatch

def _hex(h): return B.hexrgb(h)

def paint_swatch_1967(spec, U, V):
    if isinstance(spec, dict) and spec.get('kind') == 'starch':
        # starched cotton drill: fine, flat twill + a pressed crease down the front (lathe u = 1 is the front)
        base = _hex(spec['base'])
        img = np.broadcast_to(base, U.shape + (3,)).copy()
        tw = (np.sin((U * 46 + V * 46) * pi) > 0.3).astype(float)
        img *= (1 + spec.get('amt', 0.025) * (tw - 0.5))[..., None]
        if spec.get('crease', True):
            hi = np.exp(-((U - 0.985) / 0.018) ** 2)
            sh = np.exp(-((U - 0.94) / 0.02) ** 2)
            img *= (1 + 0.16 * hi - 0.07 * sh)[..., None]
        return img
    if isinstance(spec, dict) and spec.get('kind') == 'pixelcamo':
        # SAF-style pixelised camouflage: blocky cells, colours picked from smooth blobs + per-cell jitter
        rng = np.random.default_rng(spec.get('seed', 11))
        cols = [_hex(c) for c in spec['colors']]           # ordered light -> dark
        n = spec.get('n', 22)
        bi = np.clip((U * n).astype(int), 0, n - 1); bj = np.clip((V * n).astype(int), 0, n - 1)
        g = rng.random((7, 7)); g2 = rng.random((5, 5)); jit = rng.random((n, n))
        def bil(G, x, y):
            m = G.shape[0] - 1
            x = x * m; y = y * m
            i = np.clip(x.astype(int), 0, m - 1); j = np.clip(y.astype(int), 0, m - 1)
            fx = x - i; fy = y - j
            return (G[j, i] * (1 - fx) * (1 - fy) + G[j, i + 1] * fx * (1 - fy) +
                    G[j + 1, i] * (1 - fx) * fy + G[j + 1, i + 1] * fx * fy)
        cx = (bi + 0.5) / n; cy = (bj + 0.5) / n
        val = 0.62 * bil(g, cx, cy) + 0.38 * bil(g2, cx, cy) + 0.30 * (jit[bj, bi] - 0.5)
        qs = np.quantile(val, spec.get('split', [0.30, 0.58, 0.82]))
        idx = np.digitize(val, qs)
        img = np.zeros(U.shape + (3,))
        for k, c in enumerate(cols):
            img[idx == k] = c
        return img
    return _orig_paint(spec, U, V)

B.paint_swatch = paint_swatch_1967
B.BIG_KINDS = tuple(B.BIG_KINDS) + ('pixelcamo',)    # camo gets a 2x2 atlas cell (sharper pixels)

# ======================================================================================
# Headwear: 'sun_hat' (the advisers' straw hats)
# ======================================================================================
_orig_headwear = B.build_headwear

def build_headwear_1967(mb, S, C, q):
    hw = C.get('headwear')
    if not hw or hw['type'] != 'sun_hat':
        return _orig_headwear(mb, S, C, q)
    H = S.H; R = S.head_r
    base = S.head_c + Vector((0, R.y * 0.04, R.z * 0.30))
    F = Matrix.Translation(base) @ Matrix.Rotation(radians(-4), 4, 'X')
    Rb = R.x * 1.78; ch = R.z * 0.84
    prof = [(-0.004, 0.0, 0.0), (0.0, R.x * 1.0, R.y * 1.0), (0.0006, Rb * 0.97, Rb * 0.95),
            (0.008 * H, Rb, Rb * 0.98), (0.013 * H, Rb * 0.96, Rb * 0.94),
            (0.016 * H, R.x * 1.10, R.y * 1.08), (ch * 0.72, R.x * 1.07, R.y * 1.05),
            (ch * 0.95, R.x * 0.94, R.y * 0.90), (ch, 0.0, 0.0)]
    B.lathe(mb, prof, B.qs_even(24, q, 12), F, hw['sw'], 'head', 0)
    # hat band just above the brim
    z0 = 0.016 * H + 0.002
    band = [(z0 - 0.001, R.x * 1.0, R.y * 1.0), (z0, R.x * 1.118, R.y * 1.098),
            (z0 + 0.026 * H, R.x * 1.11, R.y * 1.09), (z0 + 0.026 * H + 0.001, R.x * 1.0, R.y * 1.0)]
    B.lathe(mb, band, B.qs_even(24, q, 12), F, hw.get('band', hw['sw']), 'head', 0)

B.build_headwear = build_headwear_1967

# ======================================================================================
# Hair: optional 'waves' (Leo) - soft ridges across the top of a short cut + a front wave
# ======================================================================================
_orig_hair = B.build_hair

def build_hair_1967(mb, S, C, q):
    _orig_hair(mb, S, C, q)
    hs = C['hair']; wv = hs.get('waves')
    if not wv: return
    hh = S.hh
    for k, (el, az0, az1, amp) in enumerate(wv):
        n = B.qs(7, q, 5); pts = []; rr = []
        for i in range(n):
            t = i / (n - 1)
            az = lerp(az0, az1, t)
            e = el + amp * sin(pi * 2.0 * t + k * 1.3)
            pp, _ = B.head_pt(S, az, e, 0.024 * hh)
            pts.append(pp); rr.append(0.026 * hh * (0.45 + 0.55 * sin(pi * t)))
        B.tube(mb, pts, rr, B.qs(6, q, 5), hs['sw'], 'head', 0)

B.build_hair = build_hair_1967

# ======================================================================================
# Props: 'chevrons' (rank on the upper sleeves), 'tape' (name / service tapes above the pockets)
# ======================================================================================
_orig_props = B.build_props

def sleeve_radius(S, C, side, t):
    """outer radius of the (long) sleeve at distance t from the wrist, same formula as build_arm."""
    A = S.arm_frames[side]; L = A['L']; top = C['outfit']['top']
    sleeve = top.get('sleeve', 0.0)
    if sleeve <= 0: return A['rad'](t)
    t_cuff = L * (1 - sleeve)
    k = clamp((t - t_cuff) / max(L - t_cuff, 1e-6))
    return (A['rad'](t) + A['se'] * lerp(1.0, 0.6, k)) * lerp(top.get('sleeve_flare', 1.0), 1.0, k)

def build_props_1967(mb, S, C, q):
    H = S.H; wt = B.body_w_fn(S)
    base_props = [p_ for p_ in C.get('props', []) if p_['type'] not in ('chevrons', 'tape')]
    new_props = [p_ for p_ in C.get('props', []) if p_['type'] in ('chevrons', 'tape')]
    C2 = dict(C); C2['props'] = base_props
    _orig_props(mb, S, C2, q)
    for pr in new_props:
        if pr['type'] == 'chevrons':
            for side in 'LR':
                s = sgn(side); J = S.joints[side]; d = J['dir']
                a = radians(S.arm_spread)
                n_out = Vector((s * cos(a), 0, sin(a))); fwd = Vector((0, -1, 0))
                t_mid = S.fore_len + S.up_len * pr.get('pos', 0.52)
                w = radians(pr.get('half_angle', 58)); h = pr.get('rise', 0.026) * H; gap = pr.get('gap', 0.017) * H
                for k in range(pr.get('n', 3)):
                    t0 = t_mid - gap * (pr.get('n', 3) - 1) / 2 + gap * k - h / 2
                    pts = []
                    for phi in np.linspace(-w, w, 7):
                        t = t0 + abs(phi) / w * h
                        rr = sleeve_radius(S, C, side, t) + 0.0035 * H
                        axis = J['wr'] - d * t
                        pts.append(axis + (n_out * cos(phi) + fwd * sin(phi)) * rr)
                    B.tube(mb, pts, 0.0042 * H, 4, pr['sw'], B.arm_w_fn(S, side), 0)
        elif pr['type'] == 'tape':
            sd = sgn(pr.get('side', 'R'))
            p_, n_ = B.surf(S, S.chest_z + pr.get('dz', 0.092) * H, sd * pr.get('az', 30), 0.003 * H)
            B.rbox(mb, B.feature_frame(p_, n_), (pr.get('w', 0.085) * H, pr.get('h', 0.018) * H, 0.006 * H),
                   0.0025 * H, pr['sw'], wt, 0, n=2, bend=2.0)

B.build_props = build_props_1967

# ======================================================================================
# Extras (rigid props parented to a bone): 'pace_stick', 'clipboard', 'paper_bag'
# ======================================================================================
_orig_extras = B.build_extras
STICK_R = 0.0075                     # x H

def stick_pose(S, C):
    """Sergeant's pace stick carried under the LEFT arm: upper arm down (a little out, so the stick
       clears the ribs), forearm forward and level, stick along the inner forearm and out behind the
       elbow. Returns chest-space directions + the stick line, all in the rest (design) frame."""
    if 'stick_pose' in S: return S['stick_pose']
    side = 'L'; s = 1.0; J = S.joints[side]; H = S.H
    sr = STICK_R * H
    f = Vector((-s * 0.10, -1.0, -0.03)).normalized()
    m = (f.cross(Vector((0, 0, 1))) * s).normalized()         # medial, horizontal
    r_el = sleeve_radius(S, C, side, S.fore_len) if 'arm_frames' in S else S.arm_r * 1.1
    off = r_el + sr + 0.002 * H
    back, front = 0.20 * H / 1.7, S.fore_len + 2.1 * S.hand_r
    best = None
    for ab_extra in np.arange(0.0, 34.0, 1.0):
        a = radians(S.arm_spread + ab_extra)
        u = Vector((s * sin(a), 0.07, -cos(a))).normalized()
        E = J['sh'] + u * S.up_len
        ok = True
        for tau in np.linspace(-back, 0.5 * S.fore_len, 14):
            Pp = E + f * tau + m * off
            rx, ry = B.torso_r(S, Pp.z)
            dd = sqrt((Pp.x / (rx + sr + 0.003 * H)) ** 2 + (Pp.y / (ry + sr + 0.003 * H)) ** 2)
            if dd < 1.0: ok = False; break
        best = (ab_extra, u, E)
        if ok: break
    ab_extra, u, E = best
    S['stick_pose'] = dict(u=u, f=f, E=E, m=m, off=off, back=back, front=front, ab_extra=ab_extra)
    return S['stick_pose']

def build_extras_1967(S, C, q):
    C['_S'] = S                                    # for the pose override in apply_posture (needs S)
    out = _orig_extras(S, C, q)
    H = S.H
    for ex in C.get('extras', []):
        typ = ex['type']
        if typ == 'pace_stick':
            sp = stick_pose(S, C); J = S.joints['L']
            Rf = J['dir'].rotation_difference(sp['f']).to_matrix()
            Rfi = Rf.inverted()
            to_rest = lambda Pp: J['el'] + Rfi @ (Pp - sp['E'])
            mb = B.MB()
            a0 = sp['E'] + sp['f'] * (-sp['back']) + sp['m'] * sp['off']
            a1 = sp['E'] + sp['f'] * sp['front'] + sp['m'] * sp['off']
            n = B.qs(5, q, 3)
            pts = [to_rest(a0.lerp(a1, k / n)) for k in range(n + 1)]
            r = STICK_R * H
            B.tube(mb, pts, [r * 0.92] + [r] * (n - 1) + [r * 1.05], B.qs(8, q, 6), ex['sw'], 'forearm.L', 0)
            # brass ferrule at the back tip, brass head cap at the front
            for Pp, rr, ln in ((a0, r * 1.12, 0.022 * H), (a1, r * 1.30, 0.03 * H)):
                dirv = (a1 - a0).normalized() * (1 if Pp is a1 else -1)
                c0 = to_rest(Pp - dirv * ln * 0.5); c1 = to_rest(Pp + dirv * ln * 0.35)
                B.tube(mb, [c0, c1], rr, B.qs(8, q, 6), ex['brass'], 'forearm.L', B.GLOSS)
            out.append((ex.get('name', 'PaceStick'), mb, 'forearm.L'))
        elif typ == 'clipboard':
            side = ex.get('side', 'L'); s = sgn(side); J = S.joints[side]
            mb = B.MB()
            hc = J['wr'] + J['dir'] * S.hand_r
            a = radians(S.arm_spread)
            n_out = Vector((s * cos(a), 0, sin(a)))
            yv = -J['dir']; xv = Vector((0, -1, 0)); zv = xv.cross(yv).normalized()
            if zv.dot(n_out) < 0: zv = -zv; xv = -xv
            Rt = Matrix.Rotation(radians(-s * 35), 3, yv)
            xv = Rt @ xv; zv = Rt @ zv
            bw, bh, bt = 0.13 * H, 0.18 * H, 0.0045 * H
            c = hc + J['dir'] * (bh * 0.5 - S.hand_r * 0.55) + Vector((0, -0.012 * H, 0))
            M = Matrix((xv, yv, zv)).transposed().to_4x4(); M.translation = c
            B.rbox(mb, M, (bw, bh, bt), 0.0018 * H, ex['sw'], 'hand.' + side, 0, n=1)
            Mp = M @ Matrix.Translation(Vector((0, -0.004 * H, bt * 0.5 + 0.0008 * H)))
            B.rbox(mb, Mp, (bw * 0.88, bh * 0.86, 0.0012 * H), 0.0005 * H, ex['paper'], 'hand.' + side, 0, n=1)
            Mp2 = M @ Matrix.Translation(Vector((0, -0.004 * H, -bt * 0.5 - 0.0008 * H)))
            B.rbox(mb, Mp2, (bw * 0.88, bh * 0.86, 0.0012 * H), 0.0005 * H, ex['paper'], 'hand.' + side, 0, n=1)
            Mc = M @ Matrix.Translation(Vector((0, bh * 0.44, 0)))
            B.rbox(mb, Mc, (bw * 0.36, 0.022 * H, bt * 2.6), 0.003 * H, ex['clip'], 'hand.' + side, B.GLOSS, n=1)
            out.append((ex.get('name', 'Clipboard'), mb, 'hand.' + side))
        elif typ == 'paper_bag':
            side = ex.get('side', 'R'); s = sgn(side); J = S.joints[side]
            mb = B.MB()
            hc = J['wr'] + J['dir'] * S.hand_r
            bw, bd, bh = 0.105 * H, 0.068 * H, 0.14 * H          # along Y (front-back), X, height
            top = hc.z - S.hand_r * 0.15
            c = Vector((hc.x + s * 0.004 * H, hc.y, top - bh * 0.5))
            M = Matrix.Translation(c)
            B.rbox(mb, M @ Matrix.Rotation(radians(90), 4, 'Z'), (bw, bd, bh), 0.006 * H, ex['sw'], 'hand.' + side, 0,
                   n=B.qs(3, q, 2))
            # a crumpled rim + oranges peeking out of the open top
            rim = [Vector((c.x + s * 0.0 + bd * 0.52 * cos(th), c.y + bw * 0.52 * sin(th), top + 0.004 * H * sin(3 * th)))
                   for th in np.linspace(0, 2 * pi, B.qs_even(12, q, 8), endpoint=False)]
            B.tube(mb, rim, 0.0045 * H, 4, ex['sw'], 'hand.' + side, 0, closed=True)
            ro = 0.030 * H
            for oy, oz in ((-0.028, 0.0), (0.030, -0.004)):
                B.ell(mb, Vector((c.x - s * 0.008 * H, c.y + oy * H, top - ro * 0.35 + oz * H)), (ro, ro, ro * 0.95),
                      B.qs_even(10, q, 6), B.qs(6, q, 4), ex['fruit'], 'hand.' + side, 0)
            out.append((ex.get('name', 'PaperBag'), mb, 'hand.' + side))
    return out

B.build_extras = build_extras_1967

# ======================================================================================
# New clips (appended after every existing clip)
# ======================================================================================
def _posture(C):
    po = C.get('posture', {})
    return po.get('spine', 0), po.get('chest', 0), po.get('head', 0)

def _leg_outer_x(S, C, side, z):
    """outer surface x of the leg (incl. trousers) at height z, rest pose."""
    low = C['outfit'].get('lower') or {}
    t = clamp((z - S.ankle_z) / (S.hip_z - S.ankle_z))
    r = S.leg_r * lerp(0.70, 1.0, t ** 0.8) + low.get('leg_ease', 0.006) * S.H * 1.05
    return S.leg_x + r

def attention_hand(p, S, C, side):
    """hand-centre target for arms 'pressed to the sides'. The toy body is wider at the ribs than at
       the shoulder joints, so (as in the rest A-pose) the upper arm sinks a little into the shirt; we
       go ~30% tighter than the rest spread and only require the fist to clear the hip and thigh."""
    s = sgn(side); H = S.H
    sh, _ = B.shoulder_world(p, S, C, side)
    L = (S.up_len + S.fore_len) * 0.975 + S.hand_r
    belt = 0.012 * H if any(pr['type'] == 'belt' for pr in C.get('props', [])) else 0.0
    for a_deg in np.arange(max(2.0, 0.68 * S.arm_spread), 30.0, 0.5):
        a = radians(a_deg)
        d = Vector((s * sin(a), -0.035, -cos(a))).normalized()
        ok = True
        for f in np.linspace(0.90, 1.08, 6):             # fist (centre at f = 1)
            Q = sh + d * (L * f); rq = S.hand_r * 0.62
            need = 0.0
            if Q.z > S.crotch - 0.01 * H:
                rx, _ = B.torso_r(S, Q.z)
                if abs(Q.z - S.anchors['waist']) < 0.025 * H: rx += belt
                need = max(need, rx)
            if Q.z < S.hip_z + 0.02 * H:
                need = max(need, _leg_outer_x(S, C, side, Q.z))
            if s * Q.x - rq < need: ok = False; break
        if ok: break
    S.setdefault('attention_deg', {})[side] = float(a_deg)
    return sh + d * L, d

def c_attention(t, S, C):
    """Sedia! heels together, feet turned out, legs braced, trunk straight and chest up, chin up,
       arms straight and pressed to the sides, fists closed; only a slow breath moves."""
    p = P(); ps, pc, phd = _posture(C); H = S.H
    b = sin(2 * pi * t)
    rot(p, 'spine', rx=-ps - 0.25 * b); rot(p, 'chest', rx=-pc - 2.5 - 0.55 * b)
    rot(p, 'head', rx=-phd - 5.0 + 0.2 * b)
    p['hips'].z += 0.0012 * H * b
    # legs: adduct so the heels meet, turn the feet out ~ 30 deg in total
    low = C['outfit'].get('lower') or {}
    ank_r = S.leg_r * 0.70 + max(low.get('leg_ease', 0.006), 0.010) * H
    x_a = max(ank_r * 1.02, S.leg_x * 0.45)
    ad = degrees(atan((S.leg_x - x_a) / S.leg_len)) if S.leg_x > x_a else 0.0
    for side in 'LR':
        limb(p, 'thigh', side, ab=-ad, tw=11)
        limb(p, 'foot', side, ab=ad, tw=4)
    p['hips'].z -= S.leg_len * (1 - cos(radians(ad)))
    for side in 'LR':
        s = sgn(side)
        hc, d = attention_hand(p, S, C, side)
        hdir = (d + Vector((-s * 0.06, -0.03, 0))).normalized()
        B.arm_ik(p, S, C, side, hc, hdir, Vector((s * 0.15, 1.0, 0.0)))
    return p

def c_march(t, S, C):
    """Dari kiri, cepat jalan! Quick march: straight legs forward (heel first), straight back, arms
       straight, swinging forward to about shoulder height and back. 2 paces per loop, in place."""
    p = P(); ph = 2 * pi * t; H = S.H
    ps, pc, phd = _posture(C)
    A, kneeA = 25.0, 30.0
    legs = {}
    for side, off in (('L', 0.0), ('R', pi)):
        a = ph + off
        th = -A * sin(a)
        kn = 3 + kneeA * max(0.0, cos(a)) ** 1.6
        ft = -(th + kn) - 7 * max(0.0, cos(a)) + 5 * max(0.0, -cos(a)) * max(0.0, sin(a))
        limb(p, 'thigh', side, flex=th); limb(p, 'shin', side, flex=kn); limb(p, 'foot', side, flex=ft)
        legs[side] = (th, kn)
    B.ground(p, S, legs)
    rot(p, 'hips', rz=-2.5 * sin(ph)); rot(p, 'chest', rz=3.0 * sin(ph))
    p['hips'].x += -0.006 * H * cos(ph)
    rot(p, 'spine', rx=-ps); rot(p, 'chest', rx=-pc - 2.5); rot(p, 'head', rx=-phd - 3.0, rz=-1.0 * sin(ph))
    for side, off in (('L', 0.0), ('R', pi)):
        sv = sin(ph + off)
        f = sv * (1.5 - 0.5 * sv * sv)             # flatter at the ends: the arm "arrives" crisply
        flex = 60.0 * f - 25.0 * f * f              # +35 behind ... -85 in front (about shoulder height)
        limb(p, 'upperarm', side, flex=flex, ab=-0.25 * S.arm_spread + 3.0 * max(0.0, -f))
        limb(p, 'forearm', side, flex=-5.0 - 3.0 * max(0.0, -f))
        limb(p, 'hand', side, flex=-8.0)
    return p

def carry_grips(S):
    """hand-centre positions (root space, Blender coords) for Carry: end rail of a bed frame held
       in front, at about waist height, a little wider than the shoulders."""
    H = S.H; out = {}
    for side in 'LR':
        s = sgn(side)
        out[side] = Vector((s * max(S.sh_x * 1.12, 0.10 * H), -(0.78 * (S.fore_len + S.hand_r) + 0.35 * S.hd),
                            S.z_sh - S.up_len * 0.98 - 0.045 * H))
    return out

def c_carry(t, S, C):
    """walking while holding the end of an iron bed frame in front: forearms forward at waist height,
       fists closed round the rail, a slight lean back against the weight, shorter heavier steps."""
    p = P(); e = C['energy']; ph = 2 * pi * t; H = S.H
    ps, pc, phd = _posture(C)
    B.walk_pose(p, S, C, ph, A=14 + 3 * e, Aarm=0, kneeA=30 + 6 * e, lean=-2)
    rot(p, 'hips', rz=3.0 * sin(ph)); rot(p, 'chest', rz=-5.0 * sin(ph))    # damp the walk's twist
    rot(p, 'spine', rx=-0.6 * ps - 1.5); rot(p, 'chest', rx=-0.6 * pc - 1.0)
    rot(p, 'head', rx=-0.5 * phd - 1.0)
    p['hips'].z -= 0.006 * H                                                  # knees a touch softer
    g = carry_grips(S)
    for side in 'LR':
        s = sgn(side)
        B.arm_ik(p, S, C, side, g[side], Vector((-s * 0.18, -0.86, -0.46)).normalized(),
                 Vector((s * 0.55, 0.55, -0.62)))
    return p

B.CLIPS.extend([
    # appended for Chapter 3 (first intake) - baked after all the older clips, which stay unchanged
    ('Attention', 3.0, True, c_attention),   # Sedia: heels together, arms at the sides, chin up (breath only)
    ('March', None, True, c_march),          # drill quick march, 2 paces per loop (walk_period); in place
    ('Carry', None, True, c_carry),          # walking, hands on a bed frame's end rail at `carry_grips`
])

# --------------------------------------------------------------------------------------
# Per-character pose override: Sergeant Osman keeps the pace stick under his left arm in every clip
# --------------------------------------------------------------------------------------
_orig_apply_posture = B.apply_posture

def apply_posture_1967(p, C, clip):
    _orig_apply_posture(p, C, clip)
    if C.get('stick_carry') and '_S' in C:
        sp = stick_pose(C['_S'], C); J = C['_S'].joints['L']
        Ru = J['dir'].rotation_difference(sp['u']).to_matrix()
        Rf = J['dir'].rotation_difference(sp['f']).to_matrix()
        p['mat']['upperarm.L'] = Ru                          # relative to the (posed) chest
        p['mat']['forearm.L'] = Ru.inverted() @ Rf
        p['mat']['hand.L'] = Matrix.Identity(3)

B.apply_posture = apply_posture_1967

# --------------------------------------------------------------------------------------
# Report: add the new clips' numbers (speeds, carry grips) to npc_build_report.json
# --------------------------------------------------------------------------------------
_orig_build_character = B.build_character

def build_character_1967(cid, tier_name):
    info = _orig_build_character(cid, tier_name)
    C = B.CHARACTERS[cid]; S = B.derive(C); e = C['energy']
    per = C.get('walk_period', 1.0)
    info['march_speed_mps'] = round(4 * S.leg_len * 0.97 * sin(radians(25.0)) / per, 3)
    info['march_paces_per_min'] = round(120.0 / per, 1)
    info['carry_speed_mps'] = round(4 * S.leg_len * 0.97 * sin(radians(14 + 3 * e)) / per, 3)
    info['carry_grips'] = {k: [round(x, 3) for x in v] for k, v in carry_grips(S).items()}
    info['carry_grip_height'] = round(carry_grips(S)['L'].z, 3)
    if C.get('stick_carry'): info['pace_stick'] = 'under the left arm in every clip (node PaceStick)'
    return info

B.build_character = build_character_1967

# ======================================================================================
# The cast
# ======================================================================================
# No. 4 uniform in Temasek green (starched cotton drill). Colours tuned under AgX in the previews.
NO4 = '#52603a'; NO4_LO = '#4c5a35'
def no4_palette(**kw):
    pal = {
        'no4': dict(kind='starch', base=NO4, amt=0.022),
        'no4_lo': dict(kind='starch', base=NO4_LO, amt=0.022),
        'button': '#46532f', 'webbelt': dict(kind='twill', base='#4a5634', amt=0.07), 'brass': '#a8904e',
        'boot': '#141414',
    }
    pal.update(kw); return pal

def no4_outfit(shirt='no4', trousers='no4_lo', cuff=True):
    return dict(
        top=dict(sw=shirt, hem='waist', ease=0.009, flare=1.0, sleeve=1.0, sleeve_ease=0.007, sleeve_flare=1.05,
                 cuff=dict(sw=shirt, roll=True) if cuff else None, collar='shirt', buttons='button', pockets=True),
        lower=dict(type='trousers', sw=trousers, hem=('ankle', 0.075), top='waist', ease=0.006,
                   leg_ease=0.012, leg_flare=1.24),
        legwear=[dict(sw='boot', z0=('ankle', -0.012), z1=('ankle', 0.078), ease=0.011, prio=4)],
        feet=dict(type='boots', sw='boot'),
    )

NO4_PROPS = [dict(type='belt', sw='webbelt', buckle='brass')]

CAST_1967 = {
    # ---------------------------------------------------------------- Farid, 18, recruit
    # 1965 'farid' face DNA (eye 1.02 @ 21/-5, brows 0.5/0.8/1.6, mouth 9.5/5.5, nose 0.95), two years older:
    # taller (1.58 -> 1.66), a little less head, the grin slightly held in. Same side-parted hairline, cut shorter.
    'farid-ns': dict(
        name='FaridNS', file='npc-farid-ns', age=18,
        body=body(height=1.66, head_frac=0.29, head_aspect=(0.96, 0.92), leg_frac=0.465,
                  torso_w=0.242, torso_depth=0.77, hip_ratio=0.9, belly=0.0, neck_r=0.040,
                  arm_r=0.034, leg_r=0.042, hand_r=0.043, foot_len=0.15, arm_len=1.03, arm_spread=12),
        energy=1.2, walk_period=1.0, run_period=0.60, posture=dict(spine=0, chest=-3, head=1),
        idle_arms='relaxed',
        palette=no4_palette(**{
            'skin': '#a8734f', 'skin_shade': '#94623f',
            'face': dict(kind='face', skin='#a8734f', blush='#b0604d'),
            'hair': dict(kind='strands', base='#16110e'),
        }),
        hair=dict(style='short', sw='hair', scale=(1.03, 1.04, 1.03),
                  line=[(0, 40), (25, 36), (50, 32), (70, 12), (86, -6), (100, -8), (140, -24), (180, -30)]),
        face=dict(eye=1.0, eye_az=21, eye_el=-5, brow=dict(inner=0.5, outer=0.8, arch=1.6, r=1.12),
                  mouth=dict(w=9.5, smile=4.8, el=-28), nose=0.97, blush=0.3),
        outfit=no4_outfit(),
        props=list(NO4_PROPS),
        headwear=None,
    ),
    # ---------------------------------------------------------------- Ah Hock, 18, recruit
    'ahhock-ns': dict(
        name='AhHockNS', file='npc-ahhock-ns', age=18,
        body=body(height=1.74, head_frac=0.28, head_aspect=(1.0, 0.95), leg_frac=0.46,
                  torso_w=0.285, torso_depth=0.80, hip_ratio=0.93, belly=0.02, neck_r=0.047,
                  arm_r=0.040, leg_r=0.048, hand_r=0.047, foot_len=0.155, arm_len=1.02, arm_spread=13),
        energy=0.9, walk_period=1.0, run_period=0.68, posture=dict(spine=2, chest=1, head=-2),
        idle_arms='relaxed',
        palette=no4_palette(**{
            'skin': '#dcae86', 'skin_shade': '#c79670',
            'face': dict(kind='face', skin='#dcae86', blush='#d98c74'),
            'hair': dict(kind='strands', base='#141110'),
        }),
        hair=dict(style='short', sw='hair', scale=(1.022, 1.03, 1.028),
                  line=[(0, 42), (25, 40), (55, 26), (80, 14), (100, 8), (140, -10), (180, -18)]),
        face=dict(eye=0.88, eye_az=21, eye_el=-5, brow=dict(inner=-1.6, outer=0.4, arch=0.5, r=1.5),
                  mouth=dict(w=7.0, smile=0.8, el=-29), nose=1.12, blush=0.35),
        outfit=no4_outfit(),
        props=list(NO4_PROPS),
        headwear=None,
    ),
    # ---------------------------------------------------------------- Ravi, 18, recruit
    # 1965 'ravi' face DNA (eye 0.98 @ 20/-4, brows 0.8/0.2/1.2, mouth 7.5/2.5, nose 1.1), slim, taller.
    'ravi-ns': dict(
        name='RaviNS', file='npc-ravi-ns', age=18,
        body=body(height=1.68, head_frac=0.285, head_aspect=(0.94, 0.91), leg_frac=0.475,
                  torso_w=0.232, torso_depth=0.76, hip_ratio=0.9, belly=0.0, neck_r=0.039,
                  arm_r=0.031, leg_r=0.039, hand_r=0.042, foot_len=0.15, arm_len=1.03, arm_spread=10),
        energy=0.85, walk_period=1.0, run_period=0.64, posture=dict(spine=2, chest=0, head=-2),
        idle_arms='relaxed',
        palette=no4_palette(**{
            'skin': '#74492f', 'skin_shade': '#633d27',
            'face': dict(kind='face', skin='#74492f', blush='#7f4735'),
            'hair': dict(kind='strands', base='#120e0c'),
        }),
        hair=dict(style='short', sw='hair', scale=(1.035, 1.045, 1.03),
                  line=[(0, 38), (30, 34), (60, 18), (86, -6), (100, -8), (140, -24), (180, -32)]),
        face=dict(eye=0.98, eye_az=20, eye_el=-4, brow=dict(inner=0.8, outer=0.2, arch=1.2, r=1.2),
                  mouth=dict(w=7.5, smile=2.2, el=-29), nose=1.1, blush=0.2),
        outfit=no4_outfit(),
        props=list(NO4_PROPS),
        headwear=None,
    ),
    # ---------------------------------------------------------------- Leo Pereira, 18, recruit (Eurasian)
    'leo-ns': dict(
        name='LeoNS', file='npc-leo-ns', age=18,
        body=body(height=1.70, head_frac=0.285, head_aspect=(0.95, 0.92), leg_frac=0.47,
                  torso_w=0.24, torso_depth=0.76, hip_ratio=0.89, belly=0.0, neck_r=0.039,
                  arm_r=0.033, leg_r=0.041, hand_r=0.043, foot_len=0.152, arm_len=1.03, arm_spread=12),
        energy=1.35, walk_period=1.0, run_period=0.58, posture=dict(spine=-1, chest=-3, head=2),
        idle_arms='relaxed',
        palette=no4_palette(**{
            'skin': '#dcaa85', 'skin_shade': '#c7916c',
            'face': dict(kind='face', skin='#dcaa85', blush='#dc8a72'),
            'hair': dict(kind='strands', base='#3a281c'),
        }),
        hair=dict(style='crop', sw='hair', scale=(1.05, 1.06, 1.05),
                  line=[(0, 34), (15, 30), (35, 32), (60, 16), (86, -6), (100, -10), (140, -26), (180, -34)],
                  waves=[(50, -48, 48, 3.0), (66, -56, 56, 3.5)]),
        face=dict(eye=1.0, eye_az=21, eye_el=-5, brow=dict(inner=1.6, outer=0.4, arch=2.2, r=1.05),
                  mouth=dict(w=10.0, smile=5.5, el=-28, open=True), nose=1.08, blush=0.4),
        outfit=no4_outfit(),
        props=list(NO4_PROPS),
        headwear=None,
    ),
    # ---------------------------------------------------------------- Sergeant Osman, ~35, regular
    'osman': dict(
        name='Osman', file='npc-osman', age=35,
        body=body(height=1.72, head_frac=0.28, head_aspect=(0.94, 0.91), leg_frac=0.46,
                  torso_w=0.262, torso_depth=0.80, hip_ratio=0.92, belly=0.02, neck_r=0.044,
                  arm_r=0.037, leg_r=0.045, hand_r=0.044, foot_len=0.155, arm_len=1.02, arm_spread=11),
        energy=0.8, walk_period=1.0, run_period=0.68, posture=dict(spine=-1, chest=-3, head=-1),
        idle_arms='relaxed', stick_carry=True,
        palette=no4_palette(**{
            'skin': '#9a6947', 'skin_shade': '#875a3b',
            'face': dict(kind='face', skin='#9a6947', blush='#a55c4a'),
            'hair': dict(kind='strands', base='#15110f'),
            'chevron': '#d3c796', 'stick': dict(kind='twill', base='#4e2e1c', amt=0.06), 'stick_brass': '#c29c4a',
        }),
        hair=dict(style='short', sw='hair', scale=(1.028, 1.036, 1.03),
                  line=[(0, 44), (40, 36), (70, 12), (86, -2), (100, -4), (140, -20), (180, -26)]),
        face=dict(eye=0.86, eye_az=20, eye_el=-5, brow=dict(inner=-0.6, outer=0.2, arch=0.5, r=1.45),
                  mouth=dict(w=7.0, smile=0.6, el=-30), nose=1.08, blush=0.2, moustache='thick', lids=True),
        outfit=no4_outfit(),
        props=list(NO4_PROPS) + [dict(type='chevrons', sw='chevron', n=3)],
        extras=[dict(type='pace_stick', name='PaceStick', sw='stick', brass='stick_brass')],
        headwear=None,
    ),
    # ---------------------------------------------------------------- Israeli adviser ("Mexican")
    'adviser': dict(
        name='Adviser', file='npc-adviser', age=38,
        body=body(height=1.74, head_frac=0.28, head_aspect=(0.94, 0.92), leg_frac=0.47,
                  torso_w=0.25, torso_depth=0.80, hip_ratio=0.93, belly=0.03, neck_r=0.042,
                  arm_r=0.035, leg_r=0.043, hand_r=0.043, foot_len=0.155, arm_len=1.02, arm_spread=11),
        energy=0.85, walk_period=1.05, run_period=0.70, posture=dict(spine=1, chest=-1, head=0),
        idle_arms='relaxed',
        palette={
            'skin': '#d7a17a', 'skin_shade': '#c28a64',
            'face': dict(kind='face', skin='#d7a17a', blush='#d6836c'),
            'hair': dict(kind='strands', base='#4a3526'),
            'khaki': dict(kind='twill', base='#b9a26f', amt=0.05),
            'khaki_dk': dict(kind='twill', base='#a8905f', amt=0.05),
            'button': '#8d7a50', 'belt': '#5a3b24', 'brass': '#b8954a', 'shoe': '#4a2e1c',
            'straw': dict(kind='twill', base='#d9c285', amt=0.12), 'band': '#5b3b27',
            'board': '#8a6a45', 'paper': '#f1eee5', 'clip': '#b9bcc1',
        },
        hair=dict(style='short', sw='hair', scale=(1.03, 1.04, 1.03),
                  line=[(0, 44), (40, 34), (70, 8), (86, -12), (100, -10), (140, -28), (180, -34)]),
        face=dict(eye=0.9, eye_az=20, eye_el=-4, brow=dict(inner=0.3, outer=-0.3, arch=1.0, r=1.3),
                  mouth=dict(w=8.0, smile=2.5, el=-30), nose=1.18, blush=0.35),
        outfit=dict(
            top=dict(sw='khaki', hem='waist', ease=0.011, flare=1.0, sleeve=0.52, sleeve_ease=0.009,
                     sleeve_flare=1.08, cuff=dict(sw='khaki', roll=True), collar='shirt', buttons='button', pockets=True),
            lower=dict(type='trousers', sw='khaki_dk', hem=('ankle', 0.012), top='waist', ease=0.006,
                       leg_ease=0.009, leg_flare=1.08),
            feet=dict(type='boots', sw='shoe'),
        ),
        props=[dict(type='belt', sw='belt', buckle='brass')],
        extras=[dict(type='clipboard', name='Clipboard', side='L', sw='board', paper='paper', clip='clip')],
        headwear=dict(type='sun_hat', sw='straw', band='band'),
    ),
    # ---------------------------------------------------------------- Ah Hock's Ah Ma, ~70
    'ahhockma': dict(
        name='AhHockMa', file='npc-ahhockma', age=71,
        body=body(height=1.48, head_frac=0.29, head_aspect=(0.98, 0.94), leg_frac=0.41,
                  torso_w=0.25, torso_depth=0.84, hip_ratio=1.05, belly=0.05, neck_r=0.040,
                  arm_r=0.033, leg_r=0.043, hand_r=0.042, foot_len=0.135, arm_len=1.0, arm_spread=12),
        energy=0.65, walk_period=1.2, run_period=0.82, posture=dict(spine=11, chest=9, head=-14),
        idle_arms='relaxed',
        palette={
            'skin': '#dcb28c', 'skin_shade': '#c79a74',
            'face': dict(kind='face', skin='#dcb28c', blush='#d98e78'),
            'hair': dict(kind='strands', base='#b3aea6'), 'brow': '#8e8982',
            'samfu': dict(kind='twill', base='#2c3140', amt=0.04), 'frog': '#6d7384',
            'trousers': dict(kind='twill', base='#1f1f22', amt=0.04),
            'shoe': '#1b1a1b', 'pin': '#6a4a2e', 'jade': '#6fae8a',
            'kraft': dict(kind='twill', base='#b98f5c', amt=0.08), 'orange': '#f0892a',
        },
        hair=dict(style='bun', sw='hair', scale=(1.04, 1.05, 1.04), pin='pin',
                  line=[(0, 44), (25, 38), (55, 22), (80, 12), (100, 2), (140, -28), (180, -40)]),
        face=dict(eye=0.8, eye_az=21, eye_el=-6, brow=dict(inner=1.8, outer=-2.2, arch=0.8, r=0.95, sw='brow'),
                  mouth=dict(w=7.5, smile=2.0, el=-29), nose=0.98, blush=0.45, smile_lines=True, lids=True),
        outfit=dict(
            top=dict(sw='samfu', hem=('hip', -0.03), ease=0.016, flare=1.10, sleeve=0.84, sleeve_ease=0.010,
                     sleeve_flare=1.40, collar='mandarin', placket='frog'),
            lower=dict(type='trousers', sw='trousers', hem=('ankle', 0.010), top='waist', ease=0.006,
                       leg_ease=0.013, leg_flare=1.30),
            feet=dict(type='slippers', sw='shoe'),
        ),
        props=[dict(type='bangle', side='L', sw='jade')],
        extras=[dict(type='paper_bag', name='PaperBag', side='R', sw='kraft', fruit='orange')],
        headwear=None,
    ),
    # ---------------------------------------------------------------- the Minister (background, generic)
    'minister': dict(
        name='Minister', file='npc-minister', age=52,
        body=body(height=1.68, head_frac=0.28, head_aspect=(0.96, 0.93), leg_frac=0.45,
                  torso_w=0.258, torso_depth=0.84, hip_ratio=0.98, belly=0.06, neck_r=0.043,
                  arm_r=0.035, leg_r=0.044, hand_r=0.043, foot_len=0.15, arm_len=1.02, arm_spread=11),
        energy=0.8, walk_period=1.08, run_period=0.72, posture=dict(spine=1, chest=-1, head=0),
        idle_arms='clasp',
        palette={
            'skin': '#e0b690', 'skin_shade': '#c99d78',
            'face': dict(kind='face', skin='#e0b690', blush='#dc907c'),
            'hair': dict(kind='strands', base='#26211f'),
            'shirt': dict(kind='twill', base='#f3f2ee', amt=0.02),
            'trousers': dict(kind='twill', base='#34373e', amt=0.04),
            'button': '#e1e0da', 'belt': '#1f1b19', 'metal': '#c9ccd1', 'shoe': '#1a1512', 'frame': '#2a2522',
        },
        hair=dict(style='short', sw='hair', scale=(1.035, 1.045, 1.035), top_el=80,
                  line=[(0, 50), (12, 46), (30, 40), (60, 14), (86, -8), (100, -10), (140, -28), (180, -34)]),
        face=dict(eye=0.88, eye_az=21, eye_el=-5, brow=dict(inner=0.2, outer=-0.4, arch=1.0, r=1.2),
                  mouth=dict(w=8.0, smile=2.8, el=-29), nose=1.02, blush=0.3,
                  glasses=dict(sw='frame')),
        outfit=dict(
            top=dict(sw='shirt', hem='waist', ease=0.011, flare=1.0, sleeve=1.0, sleeve_ease=0.008,
                     sleeve_flare=1.06, cuff=dict(sw='shirt', roll=True), collar='shirt', buttons='button', pockets='L'),
            lower=dict(type='trousers', sw='trousers', hem=('ankle', 0.012), top='waist', ease=0.006,
                       leg_ease=0.009, leg_flare=1.08),
            feet=dict(type='shoes', sw='shoe'),
        ),
        props=[dict(type='belt', sw='belt', buckle='metal')],
        headwear=None,
    ),
    # ---------------------------------------------------------------- Farid, 77 (2026)
    # Farid's face DNA aged 59 years: same eye placement, brow shape and grin, a little smaller eyes,
    # grey brows, smile lines, glasses, white hair (receding at the temples), a gentle stoop.
    'farid77': dict(
        name='Farid77', file='npc-farid77', age=77,
        body=body(height=1.62, head_frac=0.295, head_aspect=(0.96, 0.92), leg_frac=0.44,
                  torso_w=0.25, torso_depth=0.82, hip_ratio=0.97, belly=0.05, neck_r=0.041,
                  arm_r=0.034, leg_r=0.042, hand_r=0.043, foot_len=0.145, arm_len=1.02, arm_spread=11),
        energy=0.75, walk_period=1.12, run_period=0.78, posture=dict(spine=6, chest=4, head=-6),
        idle_arms='clasp',
        palette={
            'skin': '#a2704d', 'skin_shade': '#8f5f3e',
            'face': dict(kind='face', skin='#a2704d', blush='#a95f4b'),
            'hair': dict(kind='strands', base='#e7e4dd'), 'brow': '#bdb8af',
            'batik': dict(kind='batik', base='#2f5877', motif='#e6cf98', dark='#1c364b', border='#8a5a2e'),
            'trousers': dict(kind='twill', base='#5e6063', amt=0.04),
            'button': '#d9d2bf', 'sandal': '#4d3526', 'sstrap': '#3b281c', 'frame': '#3a2e28',
        },
        hair=dict(style='short', sw='hair', scale=(1.03, 1.04, 1.03),
                  line=[(0, 48), (25, 44), (45, 38), (70, 12), (86, -6), (100, -8), (140, -24), (180, -30)]),
        face=dict(eye=0.9, eye_az=21, eye_el=-5, brow=dict(inner=0.5, outer=0.2, arch=1.6, r=1.15, sw='brow'),
                  mouth=dict(w=9.5, smile=5.0, el=-28), nose=1.02, blush=0.3, smile_lines=True,
                  glasses=dict(sw='frame')),
        outfit=dict(
            top=dict(sw='batik', hem=('hip', -0.025), ease=0.013, flare=1.05, sleeve=0.42, sleeve_ease=0.010,
                     sleeve_flare=1.18, collar='shirt', buttons='button', pockets='L'),
            lower=dict(type='trousers', sw='trousers', hem=('ankle', 0.012), top='waist', ease=0.006,
                       leg_ease=0.010, leg_flare=1.1),
            feet=dict(type='sandals', sw='sandal', strap='sstrap'),
        ),
        props=[],
        headwear=None,
    ),
    # ---------------------------------------------------------------- Irfan, 18 (2026), Farid's grandson
    # Today's SAF No. 4: pixelised camouflage shirt and trousers, black boots, name + service tapes.
    'irfan': dict(
        name='Irfan', file='npc-irfan', age=18,
        body=body(height=1.72, head_frac=0.285, head_aspect=(0.95, 0.92), leg_frac=0.47,
                  torso_w=0.242, torso_depth=0.77, hip_ratio=0.9, belly=0.0, neck_r=0.040,
                  arm_r=0.034, leg_r=0.042, hand_r=0.043, foot_len=0.152, arm_len=1.03, arm_spread=12),
        energy=1.2, walk_period=1.0, run_period=0.60, posture=dict(spine=0, chest=-2, head=1),
        idle_arms='relaxed',
        palette={
            'skin': '#b07a55', 'skin_shade': '#9c6744',
            'face': dict(kind='face', skin='#b07a55', blush='#b6644f'),
            'hair': dict(kind='strands', base='#141110'),
            'camo': dict(kind='pixelcamo', colors=['#8f9467', '#667149', '#4a5634', '#5b4a36'], n=26, seed=5),
            'button': '#3c4530', 'webbelt': dict(kind='twill', base='#2d3226', amt=0.06), 'brass': '#3a3d38',
            'boot': '#121212', 'tape': '#1c1f1a',
        },
        hair=dict(style='short', sw='hair', scale=(1.028, 1.036, 1.028),
                  line=[(0, 40), (25, 38), (50, 30), (70, 16), (86, 4), (100, 2), (140, -14), (180, -22)]),
        face=dict(eye=1.0, eye_az=21, eye_el=-5, brow=dict(inner=0.6, outer=0.8, arch=1.5, r=1.05),
                  mouth=dict(w=9.5, smile=5.5, el=-28, open=True), nose=0.98, blush=0.3),
        outfit=no4_outfit(shirt='camo', trousers='camo'),
        props=[dict(type='belt', sw='webbelt', buckle='brass'),
               dict(type='tape', side='R', sw='tape'), dict(type='tape', side='L', sw='tape')],
        headwear=None,
    ),
}

B.CHARACTERS.clear()
B.CHARACTERS.update(CAST_1967)

if __name__ == '__main__':
    B.main()
