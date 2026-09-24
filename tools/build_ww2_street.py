"""
Sparky Discovery — Chapter 1 level: Chinatown shophouse street, Singapore, February 1942.

Reproducible Blender build script (Blender 5.2):
    GLTF_TRANSFORM=/path/to/node_modules/.bin/gltf-transform \
    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python tools/build_ww2_street.py [-- --no-bake] [--no-previews] [--fast]
    (GLTF_TRANSFORM is optional; when set, both GLBs get EXT_meshopt_compression + quantization.)

Outputs
    public/assets/models/ww2-street.glb          desktop tier (1024² textures, detail geometry)
    public/assets/models/ww2-street-mobile.glb   mobile tier (512² textures, no detail geometry)
    tools/ww2-street.blend                       reference scene (desktop state)
    docs/previews/street/*.png                   EEVEE previews
    tools/ww2_street_nodes.json                  node list with three.js-space positions

Textures come from tools/gen_ww2_textures.py (tools/ww2_tex/{1024,512}); regenerated if missing.
Research notes behind every design choice: docs/research/ww2-architecture.md

Conventions (see docs/design.md):
    Blender Z-up, metres. Blender (x, y, z) -> three.js (x, z, -y).
    Street runs along X (x -35..35), road centred on y = 0 (7 m wide).
    Marker empties face their local -Y axis.
    Walkable heights: road/lane/lot 0.00, kerb & drain slabs 0.12, five-foot way & kopitiam 0.24.
"""
import bpy, bmesh, math, random, os, sys, json, subprocess
from mathutils import Vector, Matrix, Euler
from contextlib import contextmanager

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
DO_BAKE = "--no-bake" not in ARGS
DO_PREVIEWS = "--no-previews" not in ARGS
FAST = "--fast" in ARGS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TEX = os.path.join(HERE, "ww2_tex")
OUT_DESKTOP = os.path.join(ROOT, "public", "assets", "models", "ww2-street.glb")
OUT_MOBILE = os.path.join(ROOT, "public", "assets", "models", "ww2-street-mobile.glb")
OUT_BLEND = os.path.join(HERE, "ww2-street.blend")
PREV_DIR = os.path.join(ROOT, "docs", "previews", "street")
NODES_JSON = os.path.join(HERE, "ww2_street_nodes.json")

R = random.Random(1942)

# ======================================================================================
# Colours (sRGB 0..1; converted to linear for the colour attribute)
# ======================================================================================
def lin1(x):
    return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4


def C(r, g, b, a=1.0):
    return (lin1(r), lin1(g), lin1(b), a)


def jitter(c, amt=0.04, rng=R):
    k = 1.0 + rng.uniform(-amt, amt)
    return (c[0] * k, c[1] * k, c[2] * k, c[3])


def mul(c, k):
    return (c[0] * k, c[1] * k, c[2] * k, c[3])


PLASTER = {  # muted lime-wash / earth-pigment colours (see research 1.4)
    "offwhite": C(0.92, 0.90, 0.84), "cream": C(0.94, 0.88, 0.72), "buff": C(0.88, 0.79, 0.63),
    "ochre": C(0.90, 0.76, 0.50), "venred": C(0.80, 0.60, 0.52), "celadon": C(0.74, 0.81, 0.73),
    "bluegrey": C(0.72, 0.78, 0.82), "grey": C(0.80, 0.79, 0.76), "pink": C(0.88, 0.74, 0.68),
    "sand": C(0.86, 0.78, 0.64), "lime": C(0.86, 0.86, 0.72),
}
SHUTTER = {
    "green": C(0.34, 0.46, 0.36), "darkgreen": C(0.22, 0.32, 0.26), "brown": C(0.46, 0.33, 0.24),
    "oxblood": C(0.52, 0.24, 0.20), "bluegrey": C(0.42, 0.50, 0.56), "teal": C(0.28, 0.44, 0.46),
    "cream": C(0.88, 0.84, 0.72),
}
FLOORS = {
    "terracotta": C(0.78, 0.54, 0.44), "redcement": C(0.66, 0.46, 0.40), "cement": C(0.70, 0.68, 0.64),
    "ochre": C(0.84, 0.70, 0.50), "terrazzo": C(0.78, 0.76, 0.70),
}
WHITE = C(1, 1, 1)
GRANITE = C(0.62, 0.61, 0.58)
ROAD = C(0.52, 0.50, 0.47)
EARTH = C(0.60, 0.47, 0.34)
DRAIN = C(0.34, 0.36, 0.32)
TIMBER_RAW = C(0.62, 0.48, 0.34)
TIMBER_DARK = C(0.36, 0.26, 0.18)
BAMBOO = C(0.78, 0.68, 0.42)
IRON = C(0.16, 0.16, 0.17)
RED = C(0.72, 0.14, 0.12)
SACK = C(0.92, 0.88, 0.80)
CEIL = C(0.86, 0.84, 0.78)
SOOT = C(0.10, 0.09, 0.08)

# ======================================================================================
# Geometry builder
# ======================================================================================
MATS = ["M_Plaster", "M_RoofTile", "M_Timber", "M_Floor", "M_Road", "M_Sandbag", "M_Brick",
        "M_Cloth", "M_Windows", "M_Details", "M_Signs", "M_Posters", "M_NowSigns", "M_NowShop", "M_Glass",
        "M_Metal", "M_Emissive"]


class MB:
    __slots__ = ("v", "f", "uv", "col", "sm")

    def __init__(s):
        s.v, s.f, s.uv, s.col, s.sm = [], [], [], [], []


BUCKETS = {}   # (group, tier) -> {mat: MB}
STATE = {"group": "STATIC", "tier": "base"}


@contextmanager
def GROUP(name):
    old = STATE["group"]
    STATE["group"] = name
    try:
        yield
    finally:
        STATE["group"] = old


@contextmanager
def DETAIL():
    old = STATE["tier"]
    STATE["tier"] = "detail"
    try:
        yield
    finally:
        STATE["tier"] = old


_BACK = {"M_Floor": "M_Plaster", "M_Metal": "M_Plaster", "M_Cloth": "M_Plaster", "M_Sandbag": "M_Plaster",
         "M_Brick": "M_Plaster", "M_Emissive": "M_Plaster", "M_Posters": "M_Plaster", "M_Road": "M_Plaster"}
GROUP_MAT_REMAP = {
    "STATIC": {"M_Emissive": "M_Timber", "M_Cloth": "M_Plaster", "M_Posters": "M_Plaster", "M_Metal": "M_Timber",
               "M_Brick": "M_Plaster", "M_Sandbag": "M_Plaster"},
    "WAR_Street": {"M_Cloth": "M_Plaster", "M_Windows": "M_Metal", "M_Emissive": "M_Metal", "M_Posters": "M_Plaster",
                   "M_Floor": "M_Plaster"},
    "OCC_KopiClosed": {"M_Details": "M_Timber", "M_Plaster": "M_Timber", "M_Metal": "M_Timber"},
    "NOW_Street": {"M_Timber": "M_Metal", "M_Details": "M_Metal", "M_Cloth": "M_Plaster", "M_Windows": "M_Metal",
                   "M_Signs": "M_NowSigns", "M_Posters": "M_NowSigns", "M_Sandbag": "M_Plaster", "M_Brick": "M_Plaster",
                   "M_Floor": "M_Plaster", "M_RoofTile": "M_Plaster", "M_Road": "M_Plaster"},
    "NOW_Lights": {"M_Timber": "M_Metal", "M_Plaster": "M_Metal", "M_Cloth": "M_Metal"},
    "NOW_Skyline": {"M_Timber": "M_Plaster", "M_Metal": "M_Plaster"},
    "NOW_Road": {"M_Timber": "M_Plaster", "M_Metal": "M_Plaster"},
    "NOW_Shopfronts": {},
    "Backdrop_West": _BACK,
    "Backdrop_East": _BACK,
    "Backdrop_Far": dict(_BACK, M_Timber="M_Plaster", M_Details="M_Windows", M_Signs="M_Windows"),
    "WIRES_Street": {"M_Timber": "M_Metal"},
    "LAUNDRY_Street": {"M_Timber": "M_Cloth", "M_Metal": "M_Cloth"},
    "PRE_ARPSign": {"M_Timber": "M_Signs"},
    "PRE_Barricade_E": {"M_Metal": "M_Timber"},
    "PRE_Intact_House": {"M_Metal": "M_Timber", "M_Sandbag": "M_Plaster", "M_Floor": "M_Plaster"},
    "DMG_House": {"M_Floor": "M_Plaster", "M_Windows": "M_Timber"},
    "DMG_Debris_Signboard": {"M_Timber": "M_Signs"},
    "DMG_Debris_Lantern": {"M_Timber": "M_Cloth"},
    "DMG_Debris_Sandbags": {"M_Brick": "M_Sandbag"},
    "OCC_Flags": {"M_Timber": "M_Posters"},
    "OCC_Banner": {"M_Metal": "M_Posters"},
    "OCC_RationNotice": {"M_Timber": "M_Posters"},
    "OCC_Sentry": {"M_Metal": "M_Timber", "M_Windows": "M_Timber"},
    "ShelterInterior": {"M_Metal": "M_Timber", "M_Windows": "M_Timber", "M_Cloth": "M_Details"},
}


@contextmanager
def MOBILE():
    old = STATE["tier"]
    STATE["tier"] = "mobile"
    try:
        yield
    finally:
        STATE["tier"] = old


def bucket(mat):
    mat = GROUP_MAT_REMAP.get(STATE["group"], {}).get(mat, mat)
    g = BUCKETS.setdefault((STATE["group"], STATE["tier"]), {})
    if mat not in g:
        g[mat] = MB()
    return g[mat]


# a plain dark texel in each atlas: faces of timber/metal parts that get remapped into an atlas
# material sample this instead of random slices of the atlas (sign edges, poles, frames)
ATLAS_DARK = {"M_Signs": (20 / 1024, 1 - 100 / 1024), "M_Posters": (390 / 1024, 1 - 520 / 1024),
              "M_NowSigns": (1019.5 / 1024, 1 - 1019.5 / 1024), "M_Details": (259 / 1024, 1 - 1020 / 1024),
              "M_Windows": (800 / 1024, 1 - 600 / 1024), "M_NowShop": (4 / 1024, 1 - 200 / 1024)}


def _dark_uv(mat, n):
    tgt = GROUP_MAT_REMAP.get(STATE["group"], {}).get(mat, mat)
    if tgt in ATLAS_DARK and mat not in ATLAS_DARK:
        return [ATLAS_DARK[tgt]] * n
    return None


def emit(mat, wpts, uvs, col, smooth=False):
    d = _dark_uv(mat, len(wpts))
    if d:
        uvs = d
    b = bucket(mat)
    base = len(b.v)
    b.v.extend(wpts)
    b.f.append(tuple(range(base, base + len(wpts))))
    b.uv.append(list(uvs))
    b.col.append(col)
    b.sm.append(smooth)


def emit_indexed(mat, wverts, faces, uvs, col, smooth=True):
    """faces: list of index tuples into wverts; uvs: list (per face) of per-corner uv lists."""
    if _dark_uv(mat, 1):
        uvs = [_dark_uv(mat, len(f)) for f in faces]
    b = bucket(mat)
    base = len(b.v)
    b.v.extend(wverts)
    for f, uv in zip(faces, uvs):
        b.f.append(tuple(base + i for i in f))
        b.uv.append(list(uv))
        b.col.append(col)
        b.sm.append(smooth)


def newell(p):
    nx = ny = nz = 0.0
    n = len(p)
    for i in range(n):
        a, b = p[i], p[(i + 1) % n]
        nx += (a[1] - b[1]) * (a[2] + b[2])
        ny += (a[2] - b[2]) * (a[0] + b[0])
        nz += (a[0] - b[0]) * (a[1] + b[1])
    return (nx, ny, nz)


def boxuv(pts, s=1.0, off=(0.0, 0.0)):
    su, sv = (s, s) if not isinstance(s, tuple) else s
    n = newell(pts)
    ax = max(range(3), key=lambda i: abs(n[i]))
    out = []
    for p in pts:
        if ax == 2:
            u, v = p[0], (p[1] if n[2] > 0 else -p[1])
        elif ax == 1:
            u, v = (p[0] if n[1] < 0 else -p[0]), p[2]
        else:
            u, v = (-p[1] if n[0] < 0 else p[1]), p[2]
        out.append((u / su + off[0], v / sv + off[1]))
    return out


class Frame:
    """Local frame: u along the frontage, v into the building (away from the street), z up."""

    def __init__(s, ox=0.0, oy=0.0, ux=1.0, uy=0.0, oz=0.0):
        s.o = (ox, oy, oz)
        s.U = (ux, uy)
        s.V = (-uy, ux)

    def w(s, p):
        u, v, z = p
        return (s.o[0] + u * s.U[0] + v * s.V[0], s.o[1] + u * s.U[1] + v * s.V[1], s.o[2] + z)

    def sub(s, du, dv, dz=0.0):
        o = s.w((du, dv, dz))
        return Frame(o[0], o[1], s.U[0], s.U[1], o[2])

    def rot(s, ang):
        c, sn = math.cos(ang), math.sin(ang)
        ux, uy = s.U
        return Frame(s.o[0], s.o[1], ux * c - uy * sn, ux * sn + uy * c, s.o[2])

    def dirw(s, du, dv):
        return (du * s.U[0] + dv * s.V[0], du * s.U[1] + dv * s.V[1])


WORLD = Frame()


def face(fr, mat, pts, col, uv=None, s=1.0, off=(0.0, 0.0), smooth=False):
    if uv is None:
        uv = boxuv(pts, s, off)
    emit(mat, [fr.w(p) for p in pts], uv, col, smooth)


def arect(r, W=1024.0):
    x0, y0, x1, y1 = r
    return [(x0 / W, 1 - y1 / W), (x1 / W, 1 - y1 / W), (x1 / W, 1 - y0 / W), (x0 / W, 1 - y0 / W)]


def arect_inset(r, px=2):
    x0, y0, x1, y1 = r
    return (x0 + px, y0 + px, x1 - px, y1 - px)


def box_faces(a, b):
    u0, v0, z0 = a
    u1, v1, z1 = b
    return {
        "-v": [(u0, v0, z0), (u1, v0, z0), (u1, v0, z1), (u0, v0, z1)],
        "+v": [(u1, v1, z0), (u0, v1, z0), (u0, v1, z1), (u1, v1, z1)],
        "-u": [(u0, v1, z0), (u0, v0, z0), (u0, v0, z1), (u0, v1, z1)],
        "+u": [(u1, v0, z0), (u1, v1, z0), (u1, v1, z1), (u1, v0, z1)],
        "+z": [(u0, v0, z1), (u1, v0, z1), (u1, v1, z1), (u0, v1, z1)],
        "-z": [(u0, v1, z0), (u1, v1, z0), (u1, v0, z0), (u0, v0, z0)],
    }


def box(fr, mat, a, b, col, s=1.0, off=(0.0, 0.0), skip=(), uvs=None, cols=None, mats=None):
    a = (min(a[0], b[0]), min(a[1], b[1]), min(a[2], b[2]))
    b = (max(a[0], b[0]), max(a[1], b[1]), max(a[2], b[2]))
    for k, pts in box_faces(a, b).items():
        if k in skip:
            continue
        m = (mats or {}).get(k, mat)
        c = (cols or {}).get(k, col)
        uv = (uvs or {}).get(k)
        face(fr, m, pts, c, uv=uv, s=s, off=off)


def mbox(M, mat, size, col, s=1.0, uvs=None, mats=None, cols=None, skip=()):
    """Box of size (sx,sy,sz) centred on the origin, transformed by 4x4 matrix M (world)."""
    sx, sy, sz = size[0] / 2, size[1] / 2, size[2] / 2
    for k, pts in box_faces((-sx, -sy, -sz), (sx, sy, sz)).items():
        if k in skip:
            continue
        uv = (uvs or {}).get(k) or boxuv(pts, s)
        wp = [tuple(M @ Vector(p)) for p in pts]
        emit((mats or {}).get(k, mat), wp, uv, (cols or {}).get(k, col))


def grid_quad(fr, mat, u0, u1, v0, v1, z, col, s=1.0, nu=None, nv=None, cell=1.0, down=False):
    """Horizontal quad subdivided into a grid (for vertex-AO resolution)."""
    if STATE["group"].startswith("Backdrop"):
        cell *= 3.0
        nu = nv = None
    nu = nu or max(1, int(round(abs(u1 - u0) / cell)))
    nv = nv or max(1, int(round(abs(v1 - v0) / cell)))
    for i in range(nu):
        for j in range(nv):
            a0 = u0 + (u1 - u0) * i / nu
            a1 = u0 + (u1 - u0) * (i + 1) / nu
            b0 = v0 + (v1 - v0) * j / nv
            b1 = v0 + (v1 - v0) * (j + 1) / nv
            if not down:
                pts = [(a0, b0, z), (a1, b0, z), (a1, b1, z), (a0, b1, z)]
            else:
                pts = [(a0, b1, z), (a1, b1, z), (a1, b0, z), (a0, b0, z)]
            face(fr, mat, pts, col, s=s)


def vgrid(fr, mat, u0, u1, z0, z1, v, col, s=1.0, cell=1.2, facing="-v"):
    """Vertical wall quad (in u-z plane at depth v) subdivided."""
    if STATE["group"].startswith("Backdrop"):
        cell *= 3.0
    nu = max(1, int(round(abs(u1 - u0) / cell)))
    nz = max(1, int(round(abs(z1 - z0) / cell)))
    for i in range(nu):
        for j in range(nz):
            a0 = u0 + (u1 - u0) * i / nu
            a1 = u0 + (u1 - u0) * (i + 1) / nu
            b0 = z0 + (z1 - z0) * j / nz
            b1 = z0 + (z1 - z0) * (j + 1) / nz
            if facing == "-v":
                pts = [(a0, v, b0), (a1, v, b0), (a1, v, b1), (a0, v, b1)]
            else:
                pts = [(a1, v, b0), (a0, v, b0), (a0, v, b1), (a1, v, b1)]
            face(fr, mat, pts, col, s=s)


def ugrid(fr, mat, v0, v1, z0, z1, u, col, s=1.0, cell=1.2, facing="-u"):
    if STATE["group"].startswith("Backdrop"):
        cell *= 3.0
    nv = max(1, int(round(abs(v1 - v0) / cell)))
    nz = max(1, int(round(abs(z1 - z0) / cell)))
    for i in range(nv):
        for j in range(nz):
            a0 = v0 + (v1 - v0) * i / nv
            a1 = v0 + (v1 - v0) * (i + 1) / nv
            b0 = z0 + (z1 - z0) * j / nz
            b1 = z0 + (z1 - z0) * (j + 1) / nz
            if facing == "-u":
                pts = [(u, a1, b0), (u, a0, b0), (u, a0, b1), (u, a1, b1)]
            else:
                pts = [(u, a0, b0), (u, a1, b0), (u, a1, b1), (u, a0, b1)]
            face(fr, mat, pts, col, s=s)


def wall_with_holes(fr, mat, u0, u1, z0, z1, holes, v, col, s=1.0, facing="-v", maxcell=1.3):
    """Planar wall in the u-z plane with rectangular holes [(hu0,hz0,hu1,hz1)]."""
    if STATE["group"].startswith("Backdrop"):
        maxcell = max(maxcell, 3.5)
    us = {u0, u1}
    zs = {z0, z1}
    for (a0, b0, a1, b1) in holes:
        us.update([a0, a1])
        zs.update([b0, b1])
    us = sorted(x for x in us if u0 <= x <= u1)
    zs = sorted(x for x in zs if z0 <= x <= z1)

    def refine(vals):
        out = [vals[0]]
        for a, b in zip(vals, vals[1:]):
            n = max(1, int(math.ceil((b - a) / maxcell)))
            for k in range(1, n + 1):
                out.append(a + (b - a) * k / n)
        return out

    us, zs = refine(us), refine(zs)
    for i in range(len(us) - 1):
        for j in range(len(zs) - 1):
            cu, cz = (us[i] + us[i + 1]) / 2, (zs[j] + zs[j + 1]) / 2
            if any(a0 < cu < a1 and b0 < cz < b1 for (a0, b0, a1, b1) in holes):
                continue
            a0, a1, b0, b1 = us[i], us[i + 1], zs[j], zs[j + 1]
            if facing == "-v":
                pts = [(a0, v, b0), (a1, v, b0), (a1, v, b1), (a0, v, b1)]
            else:
                pts = [(a1, v, b0), (a0, v, b0), (a0, v, b1), (a1, v, b1)]
            face(fr, mat, pts, col, s=s)


def recess(fr, hole, v, depth, jamb_col, back_mat, back_col, back_uv=None, jamb_mat="M_Plaster",
           facing="-v", sill=True):
    """Jambs of a rectangular opening at depth v..v+depth and the back quad (window/door)."""
    a0, b0, a1, b1 = hole
    d = depth if facing == "-v" else -depth
    v1 = v + d
    if facing == "-v":
        face(fr, jamb_mat, [(a0, v, b0), (a0, v1, b0), (a0, v1, b1), (a0, v, b1)], jamb_col, s=1.0)   # left jamb (+u)
        face(fr, jamb_mat, [(a1, v1, b0), (a1, v, b0), (a1, v, b1), (a1, v1, b1)], jamb_col, s=1.0)   # right jamb (-u)
        face(fr, jamb_mat, [(a0, v, b1), (a0, v1, b1), (a1, v1, b1), (a1, v, b1)], jamb_col, s=1.0)   # head (-z)
        if sill:
            face(fr, jamb_mat, [(a0, v1, b0), (a0, v, b0), (a1, v, b0), (a1, v1, b0)], jamb_col, s=1.0)  # sill (+z)
        face(fr, back_mat, [(a0, v1, b0), (a1, v1, b0), (a1, v1, b1), (a0, v1, b1)], back_col, uv=back_uv)
    else:
        face(fr, jamb_mat, [(a0, v1, b0), (a0, v, b0), (a0, v, b1), (a0, v1, b1)], jamb_col, s=1.0)
        face(fr, jamb_mat, [(a1, v, b0), (a1, v1, b0), (a1, v1, b1), (a1, v, b1)], jamb_col, s=1.0)
        face(fr, jamb_mat, [(a1, v, b1), (a1, v1, b1), (a0, v1, b1), (a0, v, b1)], jamb_col, s=1.0)
        if sill:
            face(fr, jamb_mat, [(a1, v1, b0), (a1, v, b0), (a0, v, b0), (a0, v1, b0)], jamb_col, s=1.0)
        face(fr, back_mat, [(a1, v1, b0), (a0, v1, b0), (a0, v1, b1), (a1, v1, b1)], back_col, uv=back_uv)


def prism_x(fr, mat, u0, u1, profile, col, s=1.0, caps=True, cap_mat=None, cap_col=None):
    """Extrude a closed (v,z) profile polygon (CCW seen from +u) along u from u0 to u1."""
    n = len(profile)
    for i in range(n):
        (va, za), (vb, zb) = profile[i], profile[(i + 1) % n]
        pts = [(u0, va, za), (u0, vb, zb), (u1, vb, zb), (u1, va, za)]
        face(fr, mat, pts, col, s=s)
    if caps:
        tri = ear_clip(profile)
        for (i, j, k) in tri:
            pa, pb, pc = profile[i], profile[j], profile[k]
            face(fr, cap_mat or mat, [(u1, pa[0], pa[1]), (u1, pb[0], pb[1]), (u1, pc[0], pc[1])], cap_col or col, s=s)
            face(fr, cap_mat or mat, [(u0, pc[0], pc[1]), (u0, pb[0], pb[1]), (u0, pa[0], pa[1])], cap_col or col, s=s)


def ear_clip(poly):
    """Triangulate a simple polygon (list of 2D points, CCW). Returns index triples."""
    idx = list(range(len(poly)))
    area = sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in idx)
    if area < 0:
        idx.reverse()
    tris = []

    def inside(p, a, b, c):
        def sgn(p1, p2, p3):
            return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])
        d1, d2, d3 = sgn(p, a, b), sgn(p, b, c), sgn(p, c, a)
        neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
        pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
        return not (neg and pos)

    guard = 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = poly[i0], poly[i1], poly[i2]
            cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            if cross <= 1e-12:
                continue
            if any(inside(poly[j], a, b, c) for j in idx if j not in (i0, i1, i2)):
                continue
            tris.append((i0, i1, i2))
            idx.pop(k)
            break
        else:
            break
    if len(idx) == 3:
        tris.append(tuple(idx))
    if area < 0:
        tris = [(c, b, a) for (a, b, c) in tris]
    return tris


def cyl(fr, mat, c, r, h, n, col, caps=True, s=1.0, r_top=None, top_uv=None, smooth=True, cap_col=None):
    """Vertical cylinder in frame fr, base centre c=(u,v,z)."""
    rt = r if r_top is None else r_top
    verts = []
    for i in range(n):
        a = math.tau * i / n
        verts.append(fr.w((c[0] + math.cos(a) * r, c[1] + math.sin(a) * r, c[2])))
    for i in range(n):
        a = math.tau * i / n
        verts.append(fr.w((c[0] + math.cos(a) * rt, c[1] + math.sin(a) * rt, c[2] + h)))
    faces, uvs = [], []
    circ = math.tau * max(r, rt)
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
        u0, u1 = i / n * circ / s, (i + 1) / n * circ / s
        uvs.append([(u0, 0), (u1, 0), (u1, h / s), (u0, h / s)])
    emit_indexed(mat, verts, faces, uvs, col, smooth=smooth)
    if caps:
        top = [fr.w((c[0] + math.cos(math.tau * i / n) * rt, c[1] + math.sin(math.tau * i / n) * rt, c[2] + h)) for i in range(n)]
        if top_uv:
            x0, y0, x1, y1 = top_uv
            tuv = [((x0 + (x1 - x0) * (0.5 + 0.5 * math.cos(math.tau * i / n))) / 1024.0,
                    1 - (y0 + (y1 - y0) * (0.5 - 0.5 * math.sin(math.tau * i / n))) / 1024.0) for i in range(n)]
        else:
            tuv = [(0.5 + 0.5 * math.cos(math.tau * i / n) * rt / s, 0.5 + 0.5 * math.sin(math.tau * i / n) * rt / s) for i in range(n)]
        emit(mat if not top_uv else "M_Details", top, tuv, cap_col or col)
        bot = [fr.w((c[0] + math.cos(-math.tau * i / n) * r, c[1] + math.sin(-math.tau * i / n) * r, c[2])) for i in range(n)]
        emit(mat, bot, [(0.5, 0.5)] * n, col)


def tube(mat, p0, p1, r, n, col, s=1.0, caps=False, smooth=True):
    """Cylinder between two world points."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    if L < 1e-6:
        return
    z = d.normalized()
    x = z.orthogonal().normalized()
    y = z.cross(x)
    verts = []
    for end in (p0, p1):
        for i in range(n):
            a = math.tau * i / n
            verts.append(tuple(end + (x * math.cos(a) + y * math.sin(a)) * r))
    faces, uvs = [], []
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
        uvs.append([(i / n, 0), ((i + 1) / n, 0), ((i + 1) / n, L / s), (i / n, L / s)])
    emit_indexed(mat, verts, faces, uvs, col, smooth=smooth)
    if caps:
        emit(mat, [verts[i] for i in reversed(range(n))], [(0, 0)] * n, col)
        emit(mat, [verts[n + i] for i in range(n)], [(0, 0)] * n, col)


def sphere(mat, c, r, col, nu=8, nv=6, sz=1.0, s=1.0):
    c = Vector(c)
    verts = [tuple(c + Vector((0, 0, -r * sz)))]
    for j in range(1, nv):
        th = math.pi * j / nv - math.pi / 2
        for i in range(nu):
            a = math.tau * i / nu
            verts.append(tuple(c + Vector((math.cos(th) * math.cos(a) * r, math.cos(th) * math.sin(a) * r, math.sin(th) * r * sz))))
    verts.append(tuple(c + Vector((0, 0, r * sz))))
    top = len(verts) - 1
    faces, uvs = [], []
    for i in range(nu):
        j = (i + 1) % nu
        faces.append((0, 1 + j, 1 + i))
        uvs.append([(0, 0), (0, 0), (0, 0)])
    for k in range(nv - 2):
        for i in range(nu):
            j = (i + 1) % nu
            a, b = 1 + k * nu + i, 1 + k * nu + j
            faces.append((a, b, b + nu, a + nu))
            uvs.append([(i / nu, k / nv), ((i + 1) / nu, k / nv), ((i + 1) / nu, (k + 1) / nv), (i / nu, (k + 1) / nv)])
    last = 1 + (nv - 2) * nu
    for i in range(nu):
        j = (i + 1) % nu
        faces.append((last + i, last + j, top))
        uvs.append([(0, 1), (0, 1), (0, 1)])
    emit_indexed(mat, verts, faces, uvs, col, smooth=True)


def catenary(p0, p1, sag, n):
    p0, p1 = Vector(p0), Vector(p1)
    pts = []
    for i in range(n + 1):
        t = i / n
        p = p0.lerp(p1, t)
        p.z -= sag * 4 * t * (1 - t)
        pts.append(p)
    return pts


def wire(p0, p1, sag=0.4, r=0.012, n=10, col=IRON, group="WIRES_Street"):
    if group and not STATE["group"].startswith(("OCC_", "PRE_", "DMG_", "LAUNDRY_", "NOW_")):
        with GROUP(group):
            return wire(p0, p1, sag, r, n, col, group=None)
    pts = catenary(p0, p1, sag, n)
    for a, b in zip(pts, pts[1:]):
        tube("M_Metal", a, b, r, 3, col, smooth=False)


def cloth(p_top_left, p_top_right, drop, col, sway=0.0, segs=2):
    """Hanging cloth (garment/banner) as a double-sided quad strip."""
    a, b = Vector(p_top_left), Vector(p_top_right)
    for k in range(segs):
        t0, t1 = k / segs, (k + 1) / segs
        off0 = Vector((sway * t0 * 0.3, sway * t0, -drop * t0))
        off1 = Vector((sway * t1 * 0.3, sway * t1, -drop * t1))
        pts = [tuple(a + off1), tuple(b + off1), tuple(b + off0), tuple(a + off0)]
        emit("M_Cloth", pts, [(0, t1), (1, t1), (1, t0), (0, t0)], col)


# ======================================================================================
# Registries: markers, colliders
# ======================================================================================
MARKERS = []     # (name, (x,y,z), facing(dx,dy) or None, props)
COLLIDERS = []   # (name, (x0,y0,z0,x1,y1,z1), props)
_colcount = {}


def marker(name, pos, face_dir=(0, -1), props=None):
    MARKERS.append((name, pos, face_dir, props or {}))


def collider(name, a, b, props=None, unique=True):
    props = dict(props or {})
    g = STATE["group"]
    if g.startswith("WAR_"):
        props.setdefault("state", "war")      # wartime prop: disable in the present-day (NOW) state
    elif g.startswith("NOW_"):
        props.setdefault("state", "now")      # present-day prop: enable only in the NOW state
    x0, y0, z0 = [min(p, q) for p, q in zip(a, b)]
    x1, y1, z1 = [max(p, q) for p, q in zip(a, b)]
    if not unique:
        _colcount[name] = _colcount.get(name, 0) + 1
        name = f"{name}_{_colcount[name]}"
    COLLIDERS.append((name, (x0, y0, z0, x1, y1, z1), props or {}))


def collider_local(fr, name, a, b, props=None, unique=False):
    pts = [fr.w((u, v, z)) for u in (a[0], b[0]) for v in (a[1], b[1]) for z in (a[2], b[2])]
    xs, ys, zs = zip(*pts)
    collider(name, (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs)), props, unique)


# ======================================================================================
# Street constants
# ======================================================================================
ROAD_HW = 3.5         # road half width
KERB_W = 0.10         # granite kerb 3.5..3.6
DRAIN_Y0, DRAIN_Y1 = 3.6, 4.0
FP = 4.0              # front plane of facades & columns (|y|)
SV = 2.7              # shopfront wall depth behind front plane (five-foot way overall depth)
FFW = 0.24            # five-foot way height
KERB_Z = 0.12
DRAIN_Z = -0.32
GF = 3.9              # first floor level (top of five-foot way / bottom of upper storeys)
FL = 3.4              # upper storey height
DEPTH = 12.1          # modelled house depth
COL_W = 0.45          # column width & depth
X_MIN, X_MAX = -36.0, 36.0

# atlas cells (pixel rects on 1024 canvas)
WIN = {k: (i % 4 * 256 + 4, i // 4 * 512 + 4, i % 4 * 256 + 252, i // 4 * 512 + 508) for i, k in enumerate(
    ["jal_closed", "jal_open", "french_taped", "panel", "pintu", "blackout", "door", "open"])}
DET = {k: (i % 4 * 256 + 2, i // 4 * 256 + 2, i % 4 * 256 + 254, i // 4 * 256 + 254) for i, k in enumerate(
    ["fanlight", "barred", "tiles", "marble", "planks", "chick", "vent", "drawers", "cloths", "provisions",
     "crate", "checked", "suitcase", "menu", "clock", "pawnscreen"])}


def plaque_rect(i):
    return arect_inset(((i % 2) * 512, (i // 2) * 112, (i % 2) * 512 + 512, (i // 2) * 112 + 112), 3)


def vboard_rect(i):
    return arect_inset((i * 64, 672, i * 64 + 64, 960), 2)


SIGN_SMALL = {"arp": (0, 960, 256, 1024), "shelter": (256, 960, 576, 1024), "date1936": (576, 960, 704, 1024),
              "date1938": (704, 960, 832, 1024), "fu": (832, 960, 896, 1024), "houseno": (896, 960, 1024, 1024)}
POSTER = {"p_arp": (0, 0, 256, 384), "p_siren": (256, 0, 512, 384), "p_talk": (512, 0, 768, 384),
          "p_savings": (768, 0, 1024, 384), "banner": (0, 384, 1024, 512), "flag": (0, 512, 192, 640),
          "flag2": (192, 512, 384, 640), "ration": (384, 512, 768, 768), "occ_notice": (0, 640, 384, 1024),
          "news": (768, 512, 1024, 896), "torn": (384, 768, 768, 1024), "sentry": (768, 896, 1024, 1024)}
POSTER = {k: arect_inset(v, 3) for k, v in POSTER.items()}
SIGN_SMALL = {k: arect_inset(v, 3) for k, v in SIGN_SMALL.items()}


def atlas_quad(fr, mat, u0, u1, z0, z1, v, rect, col=WHITE, facing="-v", flip=False):
    uv = arect(rect)
    if flip:
        uv = [uv[1], uv[0], uv[3], uv[2]]
    if facing == "-v":
        face(fr, mat, [(u0, v, z0), (u1, v, z0), (u1, v, z1), (u0, v, z1)], col, uv=uv)
    else:
        face(fr, mat, [(u1, v, z0), (u0, v, z0), (u0, v, z1), (u1, v, z1)], col, uv=uv)


def board(fr, mat, u0, u1, z0, z1, v0, thick, rect, col=WHITE, edge_col=None, back=True):
    """Thin closed board, front face (at v0, facing -v) textured from atlas rect."""
    v1 = v0 + thick
    ec = edge_col or mul(TIMBER_DARK, 1.0)
    atlas_quad(fr, mat, u0, u1, z0, z1, v0, rect, col)
    box(fr, "M_Timber", (u0, v0, z0), (u1, v1, z1), ec, skip=("-v",) if back else ("-v", "+v"))


# ======================================================================================
# Shophouse generator
# ======================================================================================
STYLE_DEF = {
    #          windows  fanlight pilasters roof      win_w win_h
    "early":  dict(n=2, fan=False, pil=False, roof="eave", ww=1.0, wh=1.75),
    "trans1": dict(n=2, fan=True, pil=False, roof="eave", ww=1.1, wh=1.95),
    "late":   dict(n=3, fan=True, pil=True, roof="parapet", ww=1.0, wh=1.95),
    "trans2": dict(n=3, fan=False, pil=True, roof="parapet", ww=1.05, wh=2.0),
    "deco":   dict(n=3, fan=False, pil=True, roof="deco", ww=0.95, wh=1.9),
}


class House:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def upper_height(h):
    return GF + FL * (h.storeys - 1)


def build_columns(fr, us, h_left, style_arch):
    """Columns at party lines (local u positions) of a row frame."""
    for u in us:
        box(fr, "M_Plaster", (u - COL_W / 2, 0, FFW), (u + COL_W / 2, COL_W, GF), jitter(h_left.wall, 0.02), s=1.0)
        if not STATE["group"].startswith("Backdrop"):   # backdrop rows are out of reach
            collider_local(fr, "COL_Pillar", (u - COL_W / 2, 0, 0), (u + COL_W / 2, COL_W, GF), unique=False)
        with DETAIL():
            # plinth + capital mouldings
            box(fr, "M_Plaster", (u - COL_W / 2 - 0.05, -0.05, FFW), (u + COL_W / 2 + 0.05, COL_W + 0.05, FFW + 0.35), mul(h_left.wall, 0.92))
            box(fr, "M_Plaster", (u - COL_W / 2 - 0.06, -0.06, GF - 0.9), (u + COL_W / 2 + 0.06, COL_W + 0.06, GF - 0.78), mul(h_left.wall, 1.02))
            box(fr, "M_Plaster", (u - COL_W / 2 - 0.03, -0.03, GF - 0.78), (u + COL_W / 2 + 0.03, COL_W + 0.03, GF - 0.7), mul(h_left.wall, 0.96))


def build_arcade(fr, h):
    """Beam or arch spanning the five-foot-way opening of one house (between column faces)."""
    a0, a1 = COL_W / 2, h.W - COL_W / 2
    wall = h.wall
    dep = 0.32
    if h.style in ("trans1", "late"):
        zs, zc = GF - 1.05, GF - 0.38   # springing / crown
        n = 10
        span = a1 - a0
        rise = zc - zs
        # segmental arch through (a0,zs),(mid,zc),(a1,zs)
        R_ = (span * span / 4 + rise * rise) / (2 * rise)
        cx = (a0 + a1) / 2
        cz = zc - R_
        pts = []
        for i in range(n + 1):
            x = a0 + span * i / n
            z = cz + math.sqrt(max(R_ * R_ - (x - cx) ** 2, 0))
            pts.append((x, z))
        for (x0, z0), (x1, z1) in zip(pts, pts[1:]):
            face(fr, "M_Plaster", [(x0, 0, z0), (x1, 0, z1), (x1, 0, GF), (x0, 0, GF)], wall)          # front spandrel
            face(fr, "M_Plaster", [(x1, dep, z1), (x0, dep, z0), (x0, dep, GF), (x1, dep, GF)], wall)  # back
            face(fr, "M_Plaster", [(x0, dep, z0), (x1, dep, z1), (x1, 0, z1), (x0, 0, z0)], mul(wall, 0.95))  # soffit
        with DETAIL():
            # keystone + archivolt moulding
            box(fr, "M_Plaster", (cx - 0.14, -0.08, zc - 0.12), (cx + 0.14, 0.0, GF - 0.02), mul(wall, 1.05))
            for (x0, z0), (x1, z1) in zip(pts, pts[1:]):
                face(fr, "M_Plaster", [(x0, -0.06, z0), (x1, -0.06, z1), (x1, -0.06, z1 + 0.12), (x0, -0.06, z0 + 0.12)], mul(wall, 1.04))
                face(fr, "M_Plaster", [(x0, -0.06, z0), (x0, 0, z0), (x1, 0, z1), (x1, -0.06, z1)], mul(wall, 0.9))
                face(fr, "M_Plaster", [(x1, -0.06, z1 + 0.12), (x1, 0, z1 + 0.12), (x0, 0, z0 + 0.12), (x0, -0.06, z0 + 0.12)], mul(wall, 1.0))
    else:
        zb = GF - 0.5
        box(fr, "M_Plaster", (a0, 0, zb), (a1, dep, GF), wall, skip=("+z",))
        with DETAIL():
            box(fr, "M_Plaster", (a0, -0.06, zb), (a1, 0, zb + 0.1), mul(wall, 0.92))


def build_facade(fr, h):
    sd = STYLE_DEF[h.style]
    W, top = h.W, upper_height(h)
    wall = h.wall
    holes = []
    wins = []  # (hole, kind, fan_hole, storey)
    n = h.nwin or sd["n"]
    ww = sd["ww"] if W > 4.8 or n < 3 else sd["ww"] * 0.9
    margin = 0.55 if n == 3 else 0.9
    for k in range(h.storeys - 1):
        zf = GF + FL * k
        sill = zf + (0.75 if k == 0 else 0.35)
        wh = sd["wh"] if k == 0 else sd["wh"] + 0.15
        if h.style == "early":
            sill = zf + 0.95
        for i in range(n):
            cu = margin + (W - 2 * margin) * (i + 0.5) / n
            hole = (cu - ww / 2, sill, cu + ww / 2, sill + wh)
            fan = None
            if sd["fan"]:
                fan = (cu - ww / 2, sill + wh + 0.06, cu + ww / 2, sill + wh + 0.52)
                holes.append((hole[0], hole[1], hole[2], fan[3]))
            else:
                holes.append(hole)
            kind = h.windows[(k * n + i) % len(h.windows)]
            wins.append((hole, kind, fan, k))
            h.__dict__.setdefault("win_list", []).append((hole, fan, k))
    # facade plane with openings (front face of the upper mass)
    wall_with_holes(fr, "M_Plaster", 0, W, GF, top, holes, 0.0, wall, s=2.0)
    for (hole, kind, fan, k) in wins:
        full = (hole[0], hole[1], hole[2], fan[3] if fan else hole[3])
        rd = 0.2
        # jambs over whole opening; window back quad + optional fanlight
        a0, b0, a1, b1 = full
        face(fr, "M_Plaster", [(a0, 0, b0), (a0, rd, b0), (a0, rd, b1), (a0, 0, b1)], mul(wall, 0.9), s=1.0)
        face(fr, "M_Plaster", [(a1, rd, b0), (a1, 0, b0), (a1, 0, b1), (a1, rd, b1)], mul(wall, 0.9), s=1.0)
        face(fr, "M_Plaster", [(a0, 0, b1), (a0, rd, b1), (a1, rd, b1), (a1, 0, b1)], mul(wall, 0.8), s=1.0)
        face(fr, "M_Plaster", [(a0, rd, b0), (a0, 0, b0), (a1, 0, b0), (a1, rd, b0)], mul(wall, 0.95), s=1.0)
        tint = h.shutter if kind in ("jal_closed", "jal_open", "panel") else SHUTTER["cream"]
        atlas_quad(fr, "M_Windows", hole[0], hole[2], hole[1], hole[3], rd, WIN[kind], tint)
        if fan:
            face(fr, "M_Plaster", [(hole[0], rd, hole[3]), (hole[2], rd, hole[3]), (hole[2], rd, fan[1]), (hole[0], rd, fan[1])], mul(wall, 0.9))
            atlas_quad(fr, "M_Details", fan[0], fan[2], fan[1], fan[3], rd, DET["fanlight"], wall)
        # balustrade for full-length French windows on upper floors (not early)
        if h.style != "early":
            box(fr, "M_Details", (hole[0] + 0.02, rd - 0.06, hole[1]), (hole[2] - 0.02, rd - 0.02, hole[1] + 0.8),
                h.shutter, uvs={"-v": arect(DET["vent"]), "+v": arect(DET["vent"])},
                mats={"-u": "M_Timber", "+u": "M_Timber", "+z": "M_Timber", "-z": "M_Timber"})
        with DETAIL():
            # sill, hood moulding and architrave
            box(fr, "M_Plaster", (a0 - 0.1, -0.1, b0 - 0.1), (a1 + 0.1, 0.02, b0), mul(wall, 0.95))
            box(fr, "M_Plaster", (a0 - 0.12, -0.12, b1), (a1 + 0.12, 0.02, b1 + 0.12), mul(wall, 1.03))
            if h.style in ("late", "trans1"):
                box(fr, "M_Plaster", (a0 - 0.08, -0.05, b0), (a0, 0.0, b1), mul(wall, 1.04))
                box(fr, "M_Plaster", (a1, -0.05, b0), (a1 + 0.08, 0.0, b1), mul(wall, 1.04))
            if h.style == "late" and k == 0:
                # ceramic tile panel under the sill (Peranakan-style)
                atlas_quad(fr, "M_Details", a0, a1, b0 - 0.72, b0 - 0.16, -0.015, DET["tiles"], WHITE)
                box(fr, "M_Plaster", (a0, -0.015, b0 - 0.72), (a1, 0.0, b0 - 0.16), wall, skip=("-v", "+v"))
            if h.style == "deco":
                box(fr, "M_Plaster", (a0 - 0.2, -0.35, b1 + 0.05), (a1 + 0.2, 0.0, b1 + 0.13), mul(wall, 1.0))  # hood
    # pilasters
    if sd["pil"]:
        pu = [0.12, W - 0.12]
        if n == 3:
            gap = (W - 2 * margin) / n
            pu += [margin + gap * 1, margin + gap * 2]
        for u in pu:
            pw = 0.24 if 0.2 < u < W - 0.2 else 0.24
            box(fr, "M_Plaster", (u - pw / 2, -0.09, GF), (u + pw / 2, 0.0, top), mul(wall, 1.03), skip=("+v",))
            with DETAIL():
                for k in range(h.storeys - 1):
                    zc = GF + FL * (k + 1) - 0.35
                    box(fr, "M_Plaster", (u - pw / 2 - 0.06, -0.15, zc), (u + pw / 2 + 0.06, 0.0, zc + 0.22), mul(wall, 1.06))
                    box(fr, "M_Plaster", (u - pw / 2 - 0.04, -0.13, GF + FL * k), (u + pw / 2 + 0.04, 0.0, GF + FL * k + 0.25), mul(wall, 0.95))
    # string courses at floor lines
    for k in range(h.storeys - 1):
        zf = GF + FL * k
        box(fr, "M_Plaster", (0, -0.12, zf - 0.02), (W, 0.0, zf + 0.2), mul(wall, 0.97), skip=("+v",))
    if h.style == "deco":
        with DETAIL():
            for u in (W * 0.33, W * 0.67):
                box(fr, "M_Plaster", (u - 0.05, -0.18, GF + 0.2), (u + 0.05, 0.0, top + 0.9), mul(wall, 1.05), skip=("+v",))


def build_roof(fr, h, u0=0.0, u1=None):
    W, top = h.W, upper_height(h)
    u1 = W if u1 is None else u1
    wall = h.wall
    pitch = math.radians(h.pitch)
    kind = STYLE_DEF[h.style]["roof"]
    D = DEPTH
    if kind == "eave":
        # small cornice + projecting timber eave with fascia (Malay-influenced eaves)
        box(fr, "M_Plaster", (u0, -0.2, top), (u1, 0.0, top + 0.28), mul(wall, 1.02), skip=("+v",))
        ve, ze = -0.65, top + 0.28
    else:
        # heavy cornice + parapet
        box(fr, "M_Plaster", (u0, -0.32, top + 0.05), (u1, 0.0, top + 0.4), mul(wall, 1.03), skip=("+v",))
        box(fr, "M_Plaster", (u0, -0.2, top), (u1, 0.0, top + 0.05), mul(wall, 0.95), skip=("+v",))
        ph = 0.85 if kind == "parapet" else 1.0
        box(fr, "M_Plaster", (u0, 0.0, top + 0.4), (u1, 0.28, top + 0.4 + ph), wall)
        box(fr, "M_Plaster", (u0, -0.06, top + 0.4 + ph), (u1, 0.34, top + 0.5 + ph), mul(wall, 1.04))
        with DETAIL():
            prof = [(-0.32, top + 0.05), (-0.32, top + 0.4), (-0.4, top + 0.4), (-0.4, top + 0.48), (0.0, top + 0.48), (0.0, top + 0.05)]
            prism_x(fr, "M_Plaster", u0, u1, [(v, z) for (v, z) in reversed(prof)], mul(wall, 1.05))
            # dentils
            nd = int((u1 - u0) / 0.25)
            for i in range(nd):
                uu = u0 + 0.06 + i * 0.25
                box(fr, "M_Plaster", (uu, -0.26, top - 0.06), (uu + 0.12, -0.2, top + 0.05), mul(wall, 1.0))
            if kind == "parapet" and h.style == "late":
                for i in range(3):
                    cu = (u1 - u0) * (i + 0.5) / 3 + u0
                    atlas_quad(fr, "M_Details", cu - 0.5, cu + 0.5, top + 0.55, top + 1.1, -0.01, DET["vent"], wall)
        if kind == "deco":
            cu = (u0 + u1) / 2
            box(fr, "M_Plaster", (cu - 0.9, -0.05, top + 1.4), (cu + 0.9, 0.3, top + 2.0), wall)
            box(fr, "M_Plaster", (cu - 0.55, -0.05, top + 2.0), (cu + 0.55, 0.3, top + 2.35), mul(wall, 1.02))
            atlas_quad(fr, "M_Signs", cu - 0.42, cu + 0.42, top + 1.47, top + 1.9, -0.06,
                       SIGN_SMALL["date1936" if h.date == 1936 else "date1938"], wall)
            with DETAIL():
                for s_ in (-1, 1):
                    box(fr, "M_Plaster", (cu + s_ * 0.9 - 0.12, -0.1, top + 0.4), (cu + s_ * 0.9 + 0.12, 0.3, top + 1.75), mul(wall, 1.06))
        ve, ze = 0.3, top + 0.55
    zr = ze + (D / 2 - ve) * math.tan(pitch)
    vb, zb = D + 0.35, ze
    vr = D / 2
    tilecol = h.roofcol
    # front and back slopes (tiles run down the slope: u across, v along slope)
    Lf = math.hypot(vr - ve, zr - ze)
    Lb = math.hypot(vb - vr, zr - zb)
    nf = max(1, int(Lf / 1.5))
    for i in range(nf):
        t0, t1 = i / nf, (i + 1) / nf
        va, za = ve + (vr - ve) * t0, ze + (zr - ze) * t0
        vb_, zb_ = ve + (vr - ve) * t1, ze + (zr - ze) * t1
        pts = [(u0, va, za), (u1, va, za), (u1, vb_, zb_), (u0, vb_, zb_)]
        uv = [(p[0] / 1.2 + h.uvoff, -(t * Lf) / 1.2) for p, t in zip(pts, (t0, t0, t1, t1))]
        face(fr, "M_RoofTile", pts, tilecol, uv=uv)
    pts = [(u1, vb, zb), (u0, vb, zb), (u0, vr, zr), (u1, vr, zr)]
    face(fr, "M_RoofTile", pts, mul(tilecol, 0.9), uv=[(p[0] / 1.2, t) for p, t in zip(pts, (0, 0, Lb / 1.2, Lb / 1.2))])
    # underside (closes the prism; the front overhang soffit is visible)
    face(fr, "M_Timber", [(u0, vb, zb), (u1, vb, zb), (u1, ve, ze), (u0, ve, ze)], TIMBER_DARK, s=1.0)
    # gable end caps
    for uu, sgn in ((u0, -1), (u1, 1)):
        tri = [(uu, ve, ze), (uu, vr, zr), (uu, vb, zb)]
        if sgn > 0:
            tri = tri[::-1]
        face(fr, "M_Plaster", tri, mul(wall, 0.9), s=2.0)
    # fascia board for eaves
    if kind == "eave":
        box(fr, "M_Timber", (u0 + 0.004, ve - 0.04, ze - 0.22), (u1 - 0.004, ve + 0.02, ze + 0.04), h.shutter)
    # party-wall fire walls (parapet copings following the slope)
    for (pa, pb) in ((u0, u0 + 0.16), (u1 - 0.16, u1)):
        prof = [(ve + 0.1, ze), (vr, zr), (vb - 0.1, zb), (vb - 0.1, zb + 0.25), (vr, zr + 0.25), (ve + 0.1, ze + 0.25)]
        if kind != "eave":
            prof = [(0.28, ze), (vr, zr), (vb - 0.1, zb), (vb - 0.1, zb + 0.25), (vr, zr + 0.25), (0.28, ze + 0.25)]
        prism_x(fr, "M_Plaster", pa, pb, [(v, z) for v, z in reversed(prof)], mul(wall, 0.85))
    # ridge cap
    tube("M_RoofTile", fr.w((u0, vr, zr + 0.02)), fr.w((u1, vr, zr + 0.02)), 0.09, 5, mul(tilecol, 0.8), s=1.2)
    # jack roof (raised ventilation roof over the ridge)
    if h.jack:
        ja, jb = u0 + 0.5, u1 - 0.5
        jz = zr - 0.25
        box(fr, "M_Timber", (ja, vr - 0.9, jz - 0.4), (jb, vr + 0.9, jz + 0.55), h.shutter,
            uvs={"-v": arect(WIN["jal_closed"]), "+v": arect(WIN["jal_closed"])},
            mats={"-v": "M_Windows", "+v": "M_Windows"})
        jzr = jz + 0.55 + 1.3 * math.tan(pitch)
        for sgn in (-1, 1):
            p = [(ja - 0.15, vr + sgn * 1.3, jz + 0.55), (jb + 0.15, vr + sgn * 1.3, jz + 0.55), (jb + 0.15, vr, jzr), (ja - 0.15, vr, jzr)]
            if sgn > 0:
                p = [p[1], p[0], p[3], p[2]]
            face(fr, "M_RoofTile", p, tilecol, s=1.2)
            face(fr, "M_Timber", p[::-1], TIMBER_DARK, s=1.0)
        for uu, sgn in ((ja - 0.15, -1), (jb + 0.15, 1)):
            tri = [(uu, vr - 1.3, jz + 0.55), (uu, vr, jzr), (uu, vr + 1.3, jz + 0.55)]
            if sgn > 0:
                tri = tri[::-1]
            face(fr, "M_Timber", tri, h.shutter)
    with DETAIL():
        # cover-tile rows on the front slope (V-profile Canton tiles)
        nrow = int((u1 - u0) / 0.2)
        dz = 0.045
        nx, nz = 0.0, 1.0
        # slope normal in (v,z): perpendicular to (vr-ve, zr-ze)
        sv, sz = (vr - ve) / Lf, (zr - ze) / Lf
        nv_, nz_ = -sz, sv
        for i in range(nrow):
            cu = u0 + 0.1 + i * 0.2
            a = (ve + 0.02, ze)
            b = (vr - 0.05, zr)
            for (pa, pb, off1, off2) in (((cu - 0.045, a), (cu, a), 0, 1), ((cu, a), (cu + 0.045, a), 1, 0)):
                pass
            p1 = [(cu - 0.045, a[0], a[1]), (cu, a[0] + nv_ * dz, a[1] + nz_ * dz),
                  (cu, b[0] + nv_ * dz, b[1] + nz_ * dz), (cu - 0.045, b[0], b[1])]
            p2 = [(cu, a[0] + nv_ * dz, a[1] + nz_ * dz), (cu + 0.045, a[0], a[1]),
                  (cu + 0.045, b[0], b[1]), (cu, b[0] + nv_ * dz, b[1] + nz_ * dz)]
            p1 = [p1[1], p1[0], p1[3], p1[2]][::-1]
            p2 = [p2[1], p2[0], p2[3], p2[2]][::-1]
            uvr = [(0.45, 0), (0.5, 0), (0.5, Lf / 1.2), (0.45, Lf / 1.2)]
            face(fr, "M_RoofTile", p1, mul(tilecol, 1.05), uv=uvr)
            face(fr, "M_RoofTile", p2, mul(tilecol, 0.95), uv=uvr)
        # eave end tiles (drip line)
        if kind == "eave":
            tube("M_RoofTile", fr.w((u0, ve + 0.02, ze + 0.03)), fr.w((u1, ve + 0.02, ze + 0.03)), 0.05, 4, mul(tilecol, 0.85), s=1.2)
        # fire-wall front ends: stepped caps
        for (pa, pb) in ((u0, u0 + 0.2), (u1 - 0.2, u1)):
            vv = ve + 0.1 if kind == "eave" else 0.28
            box(fr, "M_Plaster", (pa - 0.02, vv - 0.2, ze - 0.3), (pb + 0.02, vv + 0.3, ze + 0.45), mul(wall, 0.9))
        # gutter & downpipe
        box(fr, "M_Metal", (u1 - 0.12, -0.12, GF + 0.3), (u1 - 0.04, -0.04, top), C(0.30, 0.30, 0.30))
    return zr


def roof_ze(h):
    return upper_height(h) + (0.28 if STYLE_DEF[h.style]["roof"] == "eave" else 0.55)


def build_upper_mass(fr, h, sides=(True, True), top_z=None):
    W, top = h.W, upper_height(h)
    wall = h.wall
    D = DEPTH
    zt = roof_ze(h)
    # five-foot-way ceiling (underside of the first floor) — real overhead cover at z = GF
    grid_quad(fr, "M_Plaster", 0, W, 0, SV, GF, mul(CEIL, 0.95), s=2.0, cell=1.0, down=True)
    # back wall
    vgrid(fr, "M_Plaster", 0, W, FFW, zt, D, mul(wall, 0.85), s=2.0, cell=2.0, facing="+v")
    # side (party) walls; the five-foot-way passage (v 0..SV, z FFW..GF) stays open
    for side, on in zip(("-u", "+u"), sides):
        if not on:
            continue
        wins = []
        if h.side_windows and ((side == "-u" and h.side_windows in ("L", "B")) or (side == "+u" and h.side_windows in ("R", "B"))):
            for k in range(h.storeys - 1):
                zf = GF + FL * k
                for vv in (3.5, 7.5):
                    wins.append((vv, zf + 0.9, vv + 0.95, zf + 2.6))
            wins.append((7.4, 0.9, 8.4, 2.5))
        if side == "-u":
            sf = Frame(*fr.w((0, D, 0))[:2], *fr.dirw(0, -1))
            conv = lambda a, z0, b, z1: (D - b, z0, D - a, z1)
        else:
            sf = Frame(*fr.w((W, 0, 0))[:2], *fr.dirw(0, 1))
            conv = lambda a, z0, b, z1: (a, z0, b, z1)
        holes = [conv(0.0, FFW, SV, GF)] + [conv(*w) for w in wins]
        wall_with_holes(sf, "M_Plaster", 0, D, FFW, zt, holes, 0.0, mul(wall, 0.92), s=2.0, maxcell=2.0)
        for w in wins:
            hole = conv(*w)
            upper = hole[1] > 1.0
            kind = WIN["jal_open" if R.random() < 0.3 else "jal_closed"] if upper else DET["barred"]
            recess(sf, hole, 0.0, 0.18, mul(wall, 0.85), "M_Windows" if upper else "M_Details", h.shutter if upper else SHUTTER["cream"],
                   back_uv=arect(kind))


def shopfront(fr, h):
    """Ground-floor front wall at v = SV (faces the five-foot way)."""
    W = h.W
    wall = mul(h.wall, 0.93)
    z0, z1 = FFW, GF
    gt = h.ground
    a0, a1 = COL_W / 2, W - COL_W / 2
    if gt == "open":
        op = (0.55, FFW, W - 0.55, 3.15)
        wall_with_holes(fr, "M_Plaster", 0, W, z0, z1, [op], SV, wall, s=2.0)
        shop_interior(fr, h, op)
    elif gt == "planks":
        op = (0.5, FFW, W - 0.5, 3.2)
        wall_with_holes(fr, "M_Plaster", 0, W, z0, z1, [op], SV, wall, s=2.0)
        recess(fr, op, SV, 0.12, mul(wall, 0.85), "M_Details", mul(h.shutter, 1.3) if R.random() < 0.5 else WHITE,
               back_uv=arect(DET["planks"]), sill=False)
    elif gt == "door":
        dw = 1.5
        cu = W / 2
        door = (cu - dw / 2, FFW, cu + dw / 2, 2.95)
        wins = [(0.55, 1.0, cu - dw / 2 - 0.45, 2.6), (cu + dw / 2 + 0.45, 1.0, W - 0.55, 2.6)]
        wins = [w for w in wins if w[2] - w[0] > 0.5]
        fan = (door[0], 3.0, door[2], 3.45)
        wall_with_holes(fr, "M_Plaster", 0, W, z0, z1, [door, fan] + wins, SV, wall, s=2.0)
        recess(fr, door, SV, 0.15, mul(wall, 0.85), "M_Windows", h.shutter, back_uv=arect(WIN["door"]), sill=False)
        recess(fr, fan, SV, 0.15, mul(wall, 0.85), "M_Details", WHITE, back_uv=arect(DET["vent"]))
        for w in wins:
            recess(fr, w, SV, 0.15, mul(wall, 0.85), "M_Details", SHUTTER["cream"], back_uv=arect(DET["barred"]))
    elif gt == "pintu":
        dw = 1.6
        cu = W / 2
        door = (cu - dw / 2, FFW, cu + dw / 2, 3.0)
        wins = [(0.55, 1.0, cu - dw / 2 - 0.4, 2.5), (cu + dw / 2 + 0.4, 1.0, W - 0.55, 2.5)]
        wins = [w for w in wins if w[2] - w[0] > 0.5]
        wall_with_holes(fr, "M_Plaster", 0, W, z0, z1, [door] + wins, SV, wall, s=2.0)
        recess(fr, door, SV, 0.15, mul(wall, 0.85), "M_Windows", h.shutter, back_uv=arect(WIN["pintu"]), sill=False)
        for w in wins:
            recess(fr, w, SV, 0.15, mul(wall, 0.85), "M_Details", SHUTTER["cream"], back_uv=arect(DET["barred"]))
        # CNY couplets & 福 on the door frame
        if h.couplets:
            for (uu, idx) in ((door[0] - 0.24, 11), (door[2] + 0.04, 13)):
                atlas_quad(fr, "M_Signs", uu, uu + 0.2, 1.1, 2.7, SV - 0.008, vboard_rect(idx), WHITE)
            atlas_quad(fr, "M_Signs", cu - 0.18, cu + 0.18, 3.1, 3.46, SV - 0.008, arect_inset(SIGN_SMALL["fu"], 1), WHITE)
    elif gt == "kopitiam":
        pass
    # sub-plaque over the shop door (inside the five-foot way)
    if h.plaque is not None and gt in ("open", "planks", "door"):
        pw = min(W - 1.4, 2.6)
        cu = W / 2
        board(fr, "M_Signs", cu - pw / 2, cu + pw / 2, 3.25, 3.25 + pw / 4.57, SV - 0.07, 0.06, plaque_rect(h.plaque))


def shop_interior(fr, h, op):
    """Shallow shop interior behind an open shopfront so it never shows a void."""
    u0, u1 = op[0] + 0.05, op[2] - 0.05
    v0, v1 = SV, SV + 3.4
    zc = 3.25
    dark = C(0.40, 0.37, 0.33)
    grid_quad(fr, "M_Floor", u0 - 0.05, u1 + 0.05, v0, v1, FFW, mul(FLOORS["cement"], 0.8), s=1.2)
    face(fr, "M_Timber", [(u0, v0, zc), (u0, v1, zc), (u1, v1, zc), (u1, v0, zc)], mul(TIMBER_DARK, 0.7))
    face(fr, "M_Plaster", [(u0 - 0.05, v1, FFW), (u0 - 0.05, v0, FFW), (u0 - 0.05, v0, zc), (u0 - 0.05, v1, zc)], dark)
    face(fr, "M_Plaster", [(u1 + 0.05, v0, FFW), (u1 + 0.05, v1, FFW), (u1 + 0.05, v1, zc), (u1 + 0.05, v0, zc)], dark)
    face(fr, "M_Plaster", [(u0, v0, 3.15), (u1, v0, 3.15), (u1, v0, zc), (u0, v0, zc)], dark)
    shelf = {"medical": "drawers", "tailor": "cloths", "provision": "provisions", "rice": "provisions",
             "tea": "provisions", "gold": "drawers", "bicycle": "provisions", "pawn": "drawers"}.get(h.shop, "provisions")
    atlas_quad(fr, "M_Details", u0 - 0.05, u1 + 0.05, FFW, zc, v1, DET[shelf], WHITE, facing="-v")
    face(fr, "M_Plaster", [(u1 + 0.05, v1 + 0.01, FFW), (u0 - 0.05, v1 + 0.01, FFW), (u0 - 0.05, v1 + 0.01, zc), (u1 + 0.05, v1 + 0.01, zc)], dark)
    # counter across the shop mouth + goods
    box(fr, "M_Timber", (u0 + 0.2, SV + 0.5, FFW), (u1 - 0.2, SV + 1.05, FFW + 0.95), TIMBER_DARK)
    box(fr, "M_Timber", (u0 + 0.15, SV + 0.45, FFW + 0.95), (u1 - 0.15, SV + 1.1, FFW + 1.0), mul(TIMBER_RAW, 0.8))
    if h.shop in ("medical", "provision", "tea", "rice"):
        for i in range(int((u1 - u0 - 0.6) / 0.3)):
            cu = u0 + 0.5 + i * 0.3
            cyl(fr, "M_Metal", (cu, SV + 0.78, FFW + 1.0), 0.09, 0.26, 8, C(0.55, 0.62, 0.62), cap_col=RED)
    if h.shop == "tailor":
        # dress form + sewing machine table
        cyl(fr, "M_Timber", (u0 + 0.5, SV + 2.2, FFW), 0.03, 1.1, 5, TIMBER_DARK)
        cyl(fr, "M_Cloth", (u0 + 0.5, SV + 2.2, FFW + 1.05), 0.2, 0.55, 8, C(0.70, 0.66, 0.58), r_top=0.16)
        box(fr, "M_Timber", (u1 - 1.2, SV + 1.8, FFW), (u1 - 0.3, SV + 2.4, FFW + 0.78), TIMBER_DARK)
        box(fr, "M_Metal", (u1 - 1.0, SV + 1.95, FFW + 0.78), (u1 - 0.55, SV + 2.15, FFW + 1.05), IRON)
    if h.shop in ("rice", "provision"):
        for i in range(3):
            cyl(fr, "M_Sandbag", (u0 + 0.5 + i * 0.55, SV + 1.6, FFW), 0.24, 0.6, 7, SACK, r_top=0.2)


def five_foot_floor(fr, h):
    grid_quad(fr, "M_Floor", 0, h.W, 0, SV, FFW, h.floor, s=1.2, cell=1.0)


def build_house(fr, h, sides=(True, True), columns=True, ffw=True, interior=True):
    """Everything belonging to one shophouse, in its own local frame (facade at v=0)."""
    top = upper_height(h)
    if ffw:
        five_foot_floor(fr, h)
    build_arcade(fr, h)
    build_facade(fr, h)
    build_upper_mass(fr, h, sides)
    build_roof(fr, h)
    shopfront(fr, h)
    # ground-floor party walls inside the five-foot way are open; ground mass sides for ends
    # main signboard on the facade above the five-foot way
    if h.plaque is not None:
        pw = min(h.W - 1.0, 3.3)
        ph = pw / 4.57
        z0 = GF + 0.22
        board(fr, "M_Signs", h.W / 2 - pw / 2, h.W / 2 + pw / 2, z0, z0 + ph, -0.2, 0.08, plaque_rect(h.plaque))
    # vertical trade boards on the column fronts
    for (uu, idx) in h.vboards:
        board(fr, "M_Signs", uu - 0.14, uu + 0.14, 1.35, 3.05, -0.04, 0.04, vboard_rect(idx))
    # laundry pole
    if h.laundry:
        build_laundry(fr, h)
    # chick blinds hung in the five-foot-way opening
    if h.chick:
        a0, a1 = COL_W / 2 + 0.05, h.W - COL_W / 2 - 0.05
        if h.chick == "down":
            box(fr, "M_Details", (a0, 0.15, 2.0), (a1, 0.17, GF - 0.5), WHITE, uvs={"-v": arect(DET["chick"]), "+v": arect(DET["chick"])},
                mats={"-u": "M_Timber", "+u": "M_Timber", "+z": "M_Timber", "-z": "M_Timber"})
        else:
            tube("M_Details", fr.w((a0, 0.2, GF - 0.62)), fr.w((a1, 0.2, GF - 0.62)), 0.09, 6, WHITE, s=2.0, caps=True)
    with DETAIL():
        rr = random.Random(int(h.W * 1000 + h.storeys))
        # potted plants on the five-foot way and on upper window sills
        if h.ground in ("pintu", "door") and rr.random() < 0.7:
            for uu in (0.7, h.W - 0.7):
                x, y, z = h.frame.w((uu, SV - 0.35, FFW))
                cyl(WORLD, "M_Plaster", (x, y, z), 0.14, 0.3, 8, C(0.55, 0.32, 0.22), r_top=0.19)
                sphere("M_Cloth", (x, y, z + 0.5), 0.26, jitter(C(0.30, 0.42, 0.24), 0.15), nu=7, nv=5, sz=0.9)
        # bamboo chick blinds half-lowered in front of some upper windows
        if rr.random() < 0.45:
            sd = STYLE_DEF[h.style]
            n = h.nwin or sd["n"]
            margin = 0.55 if n == 3 else 0.9
            i = rr.randrange(n)
            cu = margin + (h.W - 2 * margin) * (i + 0.5) / n
            z1 = GF + 3.05
            box(h.frame, "M_Details", (cu - 0.62, -0.1, z1 - rr.uniform(0.7, 1.4)), (cu + 0.62, -0.08, z1), WHITE,
                uvs={"-v": arect(DET["chick"]), "+v": arect(DET["chick"])})
            tube("M_Timber", h.frame.w((cu - 0.65, -0.09, z1 + 0.03)), h.frame.w((cu + 0.65, -0.09, z1 + 0.03)), 0.03, 5, BAMBOO)
    # lanterns
    for uu in h.lanterns:
        lantern(fr.w((uu, 1.2, GF - 0.25)), 0.5)
    # sandbags against the shopfront (wartime group)
    if h.sandbags:
        with GROUP("WAR_Street" if STATE["group"] == "STATIC" else STATE["group"]):
            for (ua, ub) in h.sandbags:
                sandbag_wall(fr, ua, ub, SV - 0.55, SV - 0.02, FFW, 3 if ub - ua < 1.5 else 2)
                collider_local(fr, "COL_Sandbags", (ua, SV - 0.6, 0), (ub, SV, 1.0), unique=False)


def build_laundry(fr, h):
    with GROUP("LAUNDRY_Street"):
        _build_laundry(fr, h)


def _build_laundry(fr, h):
    k = 0 if h.storeys == 2 else R.choice([0, 1])
    zf = GF + FL * k
    u = h.W * R.choice([0.3, 0.5, 0.7])
    z = zf + 2.2
    p0 = fr.w((u, 0.05, z))
    p1 = fr.w((u + R.uniform(-0.3, 0.3), -1.9, z + 0.35))
    tube("M_Timber", p0, p1, 0.025, 5, BAMBOO, s=0.5)
    garments = [C(0.92, 0.92, 0.88), C(0.45, 0.52, 0.66), C(0.62, 0.34, 0.26), C(0.66, 0.60, 0.46),
                C(0.52, 0.52, 0.50), C(0.86, 0.80, 0.62), C(0.30, 0.36, 0.52)]
    t = 0.2
    P0, P1 = Vector(p0), Vector(p1)
    while t < 0.92:
        w = R.uniform(0.3, 0.55)
        a = P0.lerp(P1, t)
        b = P0.lerp(P1, min(t + w / 1.9, 0.98))
        drop = R.uniform(0.45, 1.0)
        # garments hang perpendicular to the pole: offset sideways along u
        side = Vector((*fr.dirw(1, 0), 0))
        cloth(tuple(a - side * 0.02), tuple(a + side * (w * 0.9)), drop, R.choice(garments), sway=0.02)
        t += w / 1.9 + 0.06


def lantern(top, drop, col=RED):
    top = Vector(top)
    tube("M_Metal", top, top - Vector((0, 0, drop * 0.5)), 0.006, 3, IRON, smooth=False)
    c = top - Vector((0, 0, drop * 0.5 + 0.22))
    sphere("M_Cloth", c, 0.2, col, nu=8, nv=6, sz=1.15)
    cyl(WORLD, "M_Timber", (c.x, c.y, c.z + 0.2), 0.08, 0.05, 6, C(0.2, 0.15, 0.1))
    cyl(WORLD, "M_Timber", (c.x, c.y, c.z - 0.26), 0.08, 0.05, 6, C(0.2, 0.15, 0.1))


def sandbag(M, col=None, size=(0.58, 0.34, 0.16)):
    """Desktop: pillow-shaped sack (32 tris). Mobile: plain box (12 tris)."""
    col = col or jitter(SACK, 0.12)
    with DETAIL():
        _sandbag_pillow(M, col, size)
    with MOBILE():
        mbox(M, "M_Sandbag", (size[0] * 0.92, size[1] * 0.9, size[2]), col, s=0.6,
             uvs={"+z": [(0, 0), (1, 0), (1, 1), (0, 1)], "-v": [(0, 0), (1, 0), (1, 0.3), (0, 0.3)],
                  "+v": [(0, 0), (1, 0), (1, 0.3), (0, 0.3)]})


def _sandbag_pillow(M, col, size):
    sx, sy, sz = size[0] / 2, size[1] / 2, size[2] / 2
    ring = [(sy, 0.0), (sy * 0.7, sz), (-sy * 0.7, sz), (-sy, 0.0), (-sy * 0.7, -sz), (sy * 0.7, -sz)]
    verts = []
    for (x, k) in ((-sx, 0.62), (0.0, 1.0), (sx, 0.62)):
        for (y, z) in ring:
            verts.append(tuple(M @ Vector((x, y * k, z * (0.8 + 0.2 * k)))))
    faces, uvs = [], []
    for r in range(2):
        for i in range(6):
            j = (i + 1) % 6
            faces.append((r * 6 + i, r * 6 + j, (r + 1) * 6 + j, (r + 1) * 6 + i))
            uvs.append([(r / 2, i / 6), (r / 2, (i + 1) / 6), ((r + 1) / 2, (i + 1) / 6), ((r + 1) / 2, i / 6)])
    faces.append((5, 4, 3, 2, 1, 0))
    uvs.append([(0.02, 0.5)] * 6)
    faces.append((12, 13, 14, 15, 16, 17))
    uvs.append([(0.98, 0.5)] * 6)
    emit_indexed("M_Sandbag", verts, faces, uvs, col, smooth=True)


def sandbag_wall(fr, u0, u1, v0, v1, z, rows, bag=(0.58, 0.32, 0.15)):
    """Courses of sandbags between u0..u1 (bags along u), stretching from v0 to v1 in depth."""
    L = bag[0]
    depth = v1 - v0
    nd = max(1, int(round(depth / bag[1])))
    for r in range(rows):
        off = (L / 2) * (r % 2)
        nb = max(1, int((u1 - u0 - off) / L))
        for d in range(nd):
            for i in range(nb):
                cu = u0 + off + L / 2 + i * L
                cv = v0 + bag[1] / 2 + d * (depth / nd)
                cz = z + bag[2] / 2 + r * bag[2] * 0.92
                p = Vector(fr.w((cu + R.uniform(-0.04, 0.04), cv + R.uniform(-0.03, 0.03), cz)))
                ang = math.atan2(fr.U[1], fr.U[0]) + R.uniform(-0.14, 0.14)
                M = Matrix.Translation(p) @ Matrix.Rotation(ang, 4, "Z") @ Matrix.Rotation(R.uniform(-0.08, 0.08), 4, "X") \
                    @ Matrix.Rotation(R.uniform(-0.05, 0.05), 4, "Y")
                k = R.uniform(0.92, 1.06)
                sandbag(M, size=(L * 0.97 * k, bag[1] * 0.95 * R.uniform(0.92, 1.05), bag[2] * R.uniform(0.9, 1.1)))


# ======================================================================================
# Street, rows
# ======================================================================================
def kerb_and_drain(x0, x1, side, bridges=()):
    """Granite kerb, open monsoon drain and five-foot-way edge from x0 to x1 on one side."""
    s = 1 if side == "N" else -1
    fr = Frame(0, 0, 1, 0) if s > 0 else Frame(0, 0, -1, 0)   # v toward the houses
    ua, ub = (x0, x1) if s > 0 else (-x1, -x0)
    # kerb stone: top, road face, drain face
    grid_quad(fr, "M_Plaster", ua, ub, ROAD_HW, DRAIN_Y0, KERB_Z, GRANITE, s=1.0, cell=1.0)
    vgrid(fr, "M_Plaster", ua, ub, 0.0, KERB_Z, ROAD_HW, mul(GRANITE, 0.85), s=1.0, cell=2.0)
    vgrid(fr, "M_Plaster", ua, ub, DRAIN_Z, KERB_Z, DRAIN_Y0, mul(DRAIN, 0.9), s=1.0, cell=2.0, facing="+v")
    grid_quad(fr, "M_Plaster", ua, ub, DRAIN_Y0, DRAIN_Y1, DRAIN_Z, mul(DRAIN, 0.7), s=1.0, cell=1.5)
    vgrid(fr, "M_Plaster", ua, ub, DRAIN_Z, FFW, DRAIN_Y1, GRANITE, s=1.0, cell=2.0)
    for bx in bridges:
        u = bx if s > 0 else -bx
        box(fr, "M_Plaster", (u - 0.55, DRAIN_Y0 - 0.02, KERB_Z - 0.08), (u + 0.55, DRAIN_Y1 + 0.02, KERB_Z + 0.02), mul(GRANITE, 0.95))


def build_row(side, x_start, houses, gap_after=None):
    """houses: list of House (with W). North row runs +X from x_start; south row runs -X from x_start."""
    s = 1 if side == "N" else -1
    x = x_start
    frames = []
    for i, h in enumerate(houses):
        if s > 0:
            fr = Frame(x, FP, 1, 0)
        else:
            fr = Frame(x, -FP, -1, 0)
        frames.append(fr)
        h.x0 = x
        h.frame = fr
        x += s * h.W
    return frames


def party_columns(fr_row, us, h):
    build_columns(fr_row, us, h, False)


def house_group(h):
    return getattr(h, "group", None)


def house_side_exposed(houses, i, d):
    """A party wall is only built where it can be seen: row ends, lane/lot, a taller-than-neighbour
    house, or next to the house that gets bombed (PRE_Intact_House / DMG_House)."""
    j = i + d
    if j < 0 or j >= len(houses):
        return True
    n, h = houses[j], houses[i]
    if getattr(n, "group", None) or getattr(h, "group", None):
        return True
    return roof_ze(n) < roof_ze(h) + 1.0 or n.storeys < h.storeys


def build_houses(houses):
    """Builds houses and the columns at every party line (incl. both ends of the row)."""
    for i, h in enumerate(houses):
        g = getattr(h, "group", None)
        sides = (house_side_exposed(houses, i, -1), house_side_exposed(houses, i, 1))
        if g:
            five_foot_floor(h.frame, h)
            with GROUP(g):
                build_house(h.frame, h, sides=sides, ffw=False)
        else:
            build_house(h.frame, h, sides=sides)
        us = [COL_W / 2 if i == 0 else 0.0]
        if i == len(houses) - 1:
            us.append(h.W - COL_W / 2)
        build_columns(h.frame, us, h, False)


# ======================================================================================
# Props
# ======================================================================================
def M_at(x, y, z, rz=0.0, rx=0.0, ry=0.0):
    return Matrix.Translation((x, y, z)) @ Euler((rx, ry, rz), "XYZ").to_matrix().to_4x4()


def wheel(M, r, w, spokes, col_rim=TIMBER_DARK, col_hub=IRON):
    """Spoked wheel in local XZ plane (axle along local Y), transformed by M."""
    n = 14
    rim = []
    for i in range(n):
        a = math.tau * i / n
        rim.append((math.cos(a) * r, math.sin(a) * r))
    for i in range(n):
        a, b = rim[i], rim[(i + 1) % n]
        p0 = M @ Vector((a[0], 0, a[1]))
        p1 = M @ Vector((b[0], 0, b[1]))
        tube("M_Timber", p0, p1, 0.035, 4, col_rim, smooth=False)
    hub0 = M @ Vector((0, -w / 2, 0))
    hub1 = M @ Vector((0, w / 2, 0))
    tube("M_Metal", hub0, hub1, 0.06, 6, col_hub, caps=True)
    for i in range(spokes):
        a = math.tau * i / spokes
        tube("M_Timber", M @ Vector((0, 0, 0)), M @ Vector((math.cos(a) * r * 0.95, 0, math.sin(a) * r * 0.95)), 0.012, 3, col_rim, smooth=False)


def rickshaw(x, y, rz, broken=True):
    """Hand-pulled rickshaw (jinricksha); if broken, one wheel lies on the road."""
    tilt = math.radians(-9) if broken else 0.0
    base = M_at(x, y, 0, rz)
    body = base @ M_at(0, 0, 0.62 if not broken else 0.48, 0, tilt)
    # seat box, back and folding hood
    mbox(body @ M_at(0, 0, 0.18, 0), "M_Timber", (0.9, 0.62, 0.36), C(0.18, 0.16, 0.14))
    mbox(body @ M_at(0, 0.28, 0.55, 0, math.radians(-12)), "M_Timber", (0.9, 0.08, 0.7), C(0.18, 0.16, 0.14))
    mbox(body @ M_at(0, 0.0, 0.42, 0), "M_Cloth", (0.8, 0.5, 0.1), C(0.46, 0.20, 0.18))
    for i in range(6):
        a = math.radians(10 + i * 14)
        p0 = body @ Vector((-0.46, 0.3 - math.cos(a) * 0.55, 0.45 + math.sin(a) * 0.65))
        p1 = body @ Vector((0.46, 0.3 - math.cos(a) * 0.55, 0.45 + math.sin(a) * 0.65))
        if i < 5:
            a2 = math.radians(10 + (i + 1) * 14)
            q0 = body @ Vector((-0.46, 0.3 - math.cos(a2) * 0.55, 0.45 + math.sin(a2) * 0.65))
            q1 = body @ Vector((0.46, 0.3 - math.cos(a2) * 0.55, 0.45 + math.sin(a2) * 0.65))
            emit("M_Cloth", [tuple(p0), tuple(p1), tuple(q1), tuple(q0)], [(0, 0), (1, 0), (1, 1), (0, 1)], C(0.12, 0.12, 0.12))
    # footboard + shafts
    mbox(body @ M_at(0, -0.55, -0.12, 0), "M_Timber", (0.7, 0.5, 0.04), TIMBER_DARK)
    for sx in (-0.4, 0.4):
        p0 = body @ Vector((sx, 0.1, 0.02))
        p1 = body @ Vector((sx * 0.9, -2.0, -0.05 if not broken else 0.1))
        tube("M_Timber", p0, p1, 0.03, 5, TIMBER_DARK)
    tube("M_Timber", body @ Vector((-0.36, -1.95, 0.05)), body @ Vector((0.36, -1.95, 0.05)), 0.025, 5, TIMBER_DARK)
    # wheels: left mounted, right lying flat on the road
    wheel(base @ M_at(-0.52, 0.05, 0.62, math.radians(90)), 0.62, 0.08, 12)
    if broken:
        wheel(base @ M_at(1.25, 0.4, 0.05, 0.3, math.radians(90)), 0.62, 0.08, 12)
    else:
        wheel(base @ M_at(0.52, 0.05, 0.62, math.radians(90)), 0.62, 0.08, 12)
    tube("M_Metal", base @ Vector((-0.55, 0.05, 0.62 if not broken else 0.5)), base @ Vector((0.5, 0.05, 0.6 if not broken else 0.35)), 0.025, 5, IRON)


def handcart(x, y, rz, load="half"):
    base = M_at(x, y, 0, rz)
    bed = base @ M_at(0, 0, 0.62, 0, math.radians(4))
    mbox(bed, "M_Timber", (1.2, 1.9, 0.06), TIMBER_RAW, s=1.0)
    for sx in (-0.6, 0.6):
        mbox(bed @ M_at(sx, 0, 0.14, 0), "M_Timber", (0.05, 1.9, 0.24), TIMBER_RAW)
    mbox(bed @ M_at(0, 0.95, 0.14, 0), "M_Timber", (1.2, 0.05, 0.24), TIMBER_RAW)
    for sx in (-0.5, 0.5):
        tube("M_Timber", bed @ Vector((sx, -0.9, 0)), bed @ Vector((sx * 0.8, -2.2, -0.1)), 0.03, 5, TIMBER_DARK)
    for sx in (-0.72, 0.72):
        wheel(base @ M_at(sx, 0.2, 0.5, math.radians(90)), 0.5, 0.06, 10)
    tube("M_Metal", base @ Vector((-0.75, 0.2, 0.5)), base @ Vector((0.75, 0.2, 0.5)), 0.025, 5, IRON)
    if load:
        n = 5 if load == "half" else 9
        for i in range(n):
            px, py = R.uniform(-0.4, 0.4), R.uniform(-0.1, 0.8) if load == "half" else R.uniform(-0.8, 0.8)
            kind = R.random()
            M = bed @ M_at(px, py, 0.18 + R.uniform(0, 0.2), R.uniform(-0.5, 0.5))
            if kind < 0.4:
                mbox(M, "M_Details", (0.55, 0.35, 0.2), WHITE, uvs={k: arect(DET["suitcase"]) for k in ("-v", "+v", "+z", "-u", "+u")})
            elif kind < 0.7:
                bundle(M, 0.25)
            else:
                mbox(M, "M_Details", (0.4, 0.3, 0.3), WHITE, uvs={k: arect(DET["crate"]) for k in ("-v", "+v", "+z", "-u", "+u")})


def bundle(M, r, col=None):
    """Cloth bundle (buntil) tied at the top."""
    c = M @ Vector((0, 0, 0))
    sphere("M_Details", tuple(c), r, WHITE, nu=7, nv=5, sz=0.75)
    b = bucket("M_Details")
    # remap last sphere uvs into the checked-cloth cell
    x0, y0, x1, y1 = DET["checked"]
    nfaces = 7 + 7 * 3 + 7
    for k in range(len(b.uv) - nfaces, len(b.uv)):
        b.uv[k] = [((x0 + (x1 - x0) * (0.5 + 0.4 * math.sin(i + k))) / 1024, 1 - (y0 + (y1 - y0) * (0.5 + 0.4 * math.cos(i * 1.3 + k))) / 1024) for i in range(len(b.uv[k]))]
    sphere("M_Cloth", tuple(c + Vector((0, 0, r * 0.8))), r * 0.3, col or C(0.6, 0.2, 0.2), nu=5, nv=4)


def suitcase(M):
    mbox(M, "M_Details", (0.6, 0.2, 0.42), WHITE, uvs={k: arect(DET["suitcase"]) for k in ("-v", "+v", "+z", "-u", "+u", "-z")})


def bicycle(x, y, z, rz, lean=math.radians(12)):
    base = M_at(x, y, z, rz) @ M_at(0, 0, 0, 0, lean)
    r = 0.34
    for px in (-0.52, 0.52):
        wheel(base @ M_at(px, 0, r, 0), r, 0.04, 16, col_rim=IRON, col_hub=IRON)
    pts = {"bb": (0, 0, 0.3), "seat": (-0.18, 0, 0.82), "head": (0.38, 0, 0.8), "rear": (-0.52, 0, r), "front": (0.52, 0, r)}
    P = {k: base @ Vector(v) for k, v in pts.items()}
    for a, b in (("bb", "seat"), ("seat", "head"), ("bb", "head"), ("bb", "rear"), ("seat", "rear"), ("head", "front")):
        tube("M_Metal", P[a], P[b], 0.018, 4, C(0.08, 0.08, 0.09), smooth=False)
    tube("M_Metal", base @ Vector((0.34, -0.28, 0.95)), base @ Vector((0.34, 0.28, 0.95)), 0.014, 4, C(0.5, 0.5, 0.5))
    tube("M_Metal", P["head"], base @ Vector((0.34, 0, 0.95)), 0.016, 4, C(0.08, 0.08, 0.09))
    mbox(base @ M_at(-0.2, 0, 0.87, 0), "M_Timber", (0.24, 0.12, 0.06), C(0.2, 0.12, 0.08))
    # rattan basket on carrier
    mbox(base @ M_at(-0.58, 0, 0.62, 0), "M_Details", (0.36, 0.3, 0.22), WHITE, uvs={k: arect(DET["chick"]) for k in ("-v", "+v", "-u", "+u", "+z")})


def trishaw(x, y, rz):
    base = M_at(x, y, 0, rz)
    # passenger car at front (Singapore side-car trishaws came later; early pedal rickshaw: seat behind)
    mbox(base @ M_at(0, 0.4, 0.62, 0), "M_Timber", (0.95, 0.7, 0.4), C(0.25, 0.3, 0.26))
    mbox(base @ M_at(0, 0.72, 1.0, 0), "M_Timber", (0.95, 0.08, 0.6), C(0.25, 0.3, 0.26))
    for px in (-0.55, 0.55):
        wheel(base @ M_at(px, 0.4, 0.34, math.radians(90)), 0.34, 0.05, 14, col_rim=IRON)
    wheel(base @ M_at(0, -1.2, 0.34, math.radians(90)), 0.34, 0.05, 14, col_rim=IRON)
    for a, b in (((0, -1.2, 0.34), (0, -0.4, 0.6)), ((0, -0.4, 0.6), (0, 0.1, 0.5)), ((0, -0.5, 0.95), (0, -0.4, 0.6)), ((0, -1.1, 1.05), (0, -1.2, 0.34))):
        tube("M_Metal", base @ Vector(a), base @ Vector(b), 0.02, 4, IRON, smooth=False)
    tube("M_Metal", base @ Vector((-0.3, -1.1, 1.05)), base @ Vector((0.3, -1.1, 1.05)), 0.015, 4, IRON)
    mbox(base @ M_at(0, -0.5, 0.98, 0), "M_Timber", (0.2, 0.25, 0.06), C(0.2, 0.12, 0.08))


def hawker_cart(x, y, rz):
    base = M_at(x, y, 0, rz)
    mbox(base @ M_at(0, 0, 0.85, 0), "M_Timber", (1.5, 0.7, 0.08), TIMBER_RAW)
    mbox(base @ M_at(0, 0, 0.5, 0), "M_Timber", (1.4, 0.65, 0.62), mul(TIMBER_RAW, 0.8),
         uvs={"-v": arect(DET["planks"]), "+v": arect(DET["planks"])}, mats={"-v": "M_Details", "+v": "M_Details"})
    for px in (-0.6, 0.6):
        wheel(base @ M_at(px, -0.38, 0.32, 0), 0.3, 0.05, 8)
    for px, py in ((-0.7, -0.3), (0.7, -0.3), (-0.7, 0.3), (0.7, 0.3)):
        tube("M_Timber", base @ Vector((px, py, 0.89)), base @ Vector((px, py, 2.0)), 0.025, 4, TIMBER_DARK)
    mbox(base @ M_at(0, 0, 2.05, 0), "M_Cloth", (1.7, 0.95, 0.04), C(0.60, 0.50, 0.36))
    cyl(WORLD, "M_Metal", tuple(base @ Vector((-0.35, 0, 0.89))), 0.22, 0.3, 10, C(0.25, 0.25, 0.24))   # charcoal stove & pot
    cyl(WORLD, "M_Metal", tuple(base @ Vector((0.3, 0.05, 0.89))), 0.14, 0.12, 8, C(0.55, 0.55, 0.52))
    for i in range(4):
        cyl(WORLD, "M_Metal", tuple(base @ Vector((0.55, -0.2 + i * 0.1, 0.89))), 0.06, 0.05, 6, C(0.85, 0.85, 0.8))


def carrying_pole(x, y, rz):
    """Hawker's shoulder pole with two baskets (set down)."""
    base = M_at(x, y, 0, rz)
    for py in (-0.6, 0.6):
        cyl(WORLD, "M_Details", tuple(base @ Vector((0, py, 0))), 0.25, 0.35, 8, WHITE)
        b = bucket("M_Details")
        for k in range(len(b.uv) - 10, len(b.uv)):
            b.uv[k] = arect(DET["chick"])[: len(b.uv[k])] + [arect(DET["chick"])[0]] * max(0, len(b.uv[k]) - 4)
        for a in (0, 1.57):
            p = base @ Vector((0, py, 0.35))
            tube("M_Metal", p + Vector((math.cos(a) * 0.24, math.sin(a) * 0.24, 0)), p + Vector((0, 0, 0.55)), 0.005, 3, IRON, smooth=False)
    tube("M_Timber", base @ Vector((0.05, -1.0, 0.45)), base @ Vector((0.05, 1.0, 0.1)), 0.03, 5, BAMBOO)


def stool(x, y, z, col=TIMBER_RAW):
    cyl(WORLD, "M_Timber", (x, y, z + 0.42), 0.16, 0.04, 8, col)
    for i in range(4):
        a = math.tau * i / 4 + 0.785
        tube("M_Timber", (x + math.cos(a) * 0.12, y + math.sin(a) * 0.12, z + 0.42), (x + math.cos(a) * 0.16, y + math.sin(a) * 0.16, z), 0.018, 4, col, smooth=False)


def chair(M, col=TIMBER_DARK):
    mbox(M @ M_at(0, 0, 0.45, 0), "M_Timber", (0.4, 0.4, 0.04), col)
    for px, py in ((-0.17, -0.17), (0.17, -0.17), (-0.17, 0.17), (0.17, 0.17)):
        h = 0.45 if py < 0 else 0.92
        mbox(M @ M_at(px, py, h / 2, 0), "M_Timber", (0.035, 0.035, h), col)
    mbox(M @ M_at(0, 0.17, 0.8, 0), "M_Timber", (0.36, 0.025, 0.16), col)


def marble_table(x, y, z, r=0.36, h=0.74):
    cyl(WORLD, "M_Metal", (x, y, z), 0.2, 0.04, 8, IRON)
    cyl(WORLD, "M_Metal", (x, y, z), 0.035, h - 0.04, 6, IRON)
    cyl(WORLD, "M_Timber", (x, y, z + h - 0.05), r + 0.02, 0.04, 14, TIMBER_DARK)
    cyl(WORLD, "M_Details", (x, y, z + h - 0.01), r, 0.03, 14, WHITE, top_uv=DET["marble"], cap_col=WHITE)


def lamp_post(x, y, blackout=True):
    """Cast-iron gas lamp post; lantern head hooded for the blackout."""
    z = KERB_Z if abs(y) < FP else 0
    cyl(WORLD, "M_Metal", (x, y, z), 0.16, 0.5, 8, IRON, r_top=0.1)
    cyl(WORLD, "M_Metal", (x, y, z + 0.5), 0.07, 2.9, 8, IRON, r_top=0.05)
    tube("M_Metal", (x - 0.35, y, z + 3.05), (x + 0.35, y, z + 3.05), 0.02, 4, IRON)  # ladder bar
    cyl(WORLD, "M_Metal", (x, y, z + 3.4), 0.1, 0.12, 6, IRON)
    cyl(WORLD, "M_Windows", (x, y, z + 3.52), 0.16, 0.42, 6, C(0.4, 0.45, 0.45), r_top=0.21, caps=False, smooth=False)
    cyl(WORLD, "M_Metal", (x, y, z + 3.94), 0.25, 0.14, 6, C(0.1, 0.1, 0.1), r_top=0.04)
    if blackout:
        cyl(WORLD, "M_Metal", (x, y, z + 3.62), 0.22, 0.25, 6, C(0.12, 0.12, 0.11), r_top=0.22, caps=False)
    collider("COL_Lamp", (x - 0.18, y - 0.18, 0), (x + 0.18, y + 0.18, 3.0), unique=False)


def utility_pole(x, y, h=8.0):
    z = KERB_Z
    cyl(WORLD, "M_Timber", (x, y, z), 0.13, h, 7, C(0.40, 0.33, 0.26), r_top=0.1, s=1.5)
    with GROUP("WIRES_Street"):
        for k, zz in enumerate((h - 0.4, h - 1.1)):
            mbox(M_at(x, y, z + zz, 0), "M_Timber", (0.1, 1.5, 0.1), C(0.35, 0.28, 0.22))
            for py in (-0.65, -0.25, 0.25, 0.65):
                cyl(WORLD, "M_Metal", (x, y + py, z + zz + 0.05), 0.03, 0.1, 5, C(0.85, 0.85, 0.8))
    collider("COL_Pole", (x - 0.18, y - 0.18, 0), (x + 0.18, y + 0.18, 3.0), unique=False)
    return [(x, y + py, z + zz + 0.14) for zz in (h - 0.4, h - 1.1) for py in (-0.65, -0.25, 0.25, 0.65)]


def pillar_box(x, y, z):
    """Red pillar post box (colonial GR type)."""
    cyl(WORLD, "M_Metal", (x, y, z), 0.24, 1.25, 12, C(0.66, 0.08, 0.06), s=1.0)
    sphere("M_Metal", (x, y, z + 1.25), 0.27, C(0.66, 0.08, 0.06), nu=12, nv=6, sz=0.45)
    mbox(M_at(x, y - 0.22, z + 1.05, 0), "M_Metal", (0.26, 0.06, 0.05), C(0.05, 0.05, 0.05))
    collider("COL_PillarBox", (x - 0.28, y - 0.28, 0), (x + 0.28, y + 0.28, 1.4))


def water_jar(x, y, z, h=0.75):
    cyl(WORLD, "M_Plaster", (x, y, z), 0.2, h * 0.6, 10, C(0.30, 0.20, 0.12), r_top=0.34)
    cyl(WORLD, "M_Plaster", (x, y, z + h * 0.6), 0.34, h * 0.4, 10, C(0.30, 0.20, 0.12), r_top=0.2)
    cyl(WORLD, "M_Timber", (x, y, z + h), 0.23, 0.04, 10, TIMBER_DARK)


def bucket_(x, y, z, col=RED, sand=False):
    cyl(WORLD, "M_Metal", (x, y, z), 0.12, 0.3, 8, col, r_top=0.15, cap_col=C(0.75, 0.62, 0.45) if sand else C(0.2, 0.25, 0.3))


def crate(M, label=True, size=(0.5, 0.35, 0.35)):
    uv = {k: arect(DET["crate"]) for k in ("-v", "+v", "-u", "+u", "+z")}
    mbox(M, "M_Details", size, WHITE, uvs=uv)


def rubble_heap(cx, cy, rx, ry, h, seed, col=C(0.80, 0.76, 0.70), n=10):
    """Irregular heap mesh (plaster/brick dust) as a displaced grid."""
    rr = random.Random(seed)
    verts = []
    for j in range(n + 1):
        for i in range(n + 1):
            u, v = i / n * 2 - 1, j / n * 2 - 1
            d = max(0.0, 1 - (u * u + v * v))
            z = h * d ** 0.8 * (0.75 + rr.uniform(0, 0.5)) if d > 0 else -0.03
            verts.append((cx + u * rx, cy + v * ry, max(z, -0.02)))
    faces, uvs = [], []
    for j in range(n):
        for i in range(n):
            a = j * (n + 1) + i
            faces.append((a, a + 1, a + n + 2, a + n + 1))
            uvs.append([(verts[k][0] / 0.35 + verts[k][2], verts[k][1] / 0.35) for k in (a, a + 1, a + n + 2, a + n + 1)])
    emit_indexed("M_Brick", verts, faces, uvs, col, smooth=True)


def debris_chunks(cx, cy, rx, ry, n, seed, zmax=0.6):
    rr = random.Random(seed)
    for i in range(n):
        x, y = cx + rr.uniform(-rx, rx), cy + rr.uniform(-ry, ry)
        s = rr.uniform(0.12, 0.45)
        M = M_at(x, y, rr.uniform(0.02, zmax) * (1 - ((x - cx) / rx) ** 2), rr.uniform(0, 6.28), rr.uniform(-0.6, 0.6), rr.uniform(-0.6, 0.6))
        kind = rr.random()
        if kind < 0.5:
            mbox(M, "M_Brick", (s, s * 0.6, s * 0.4), C(0.9, 0.85, 0.8), s=1.0)
        elif kind < 0.8:
            mbox(M, "M_Plaster", (s * 1.3, s, 0.08), jitter(C(0.85, 0.80, 0.70), 0.1), s=2.0)
        else:
            mbox(M, "M_Timber", (s * 3, 0.1, 0.1), C(0.25, 0.18, 0.12))


# ======================================================================================
# Level layout
# ======================================================================================
def H(W, storeys, style, wall, shutter, windows, ground, floor="terracotta", plaque=None, vboards=(),
      laundry=False, chick=None, lanterns=(), sandbags=(), jack=False, pitch=26, roofcol=None,
      side_windows=None, couplets=False, shop=None, date=1936, nwin=None, **kw):
    h = House(W=W, storeys=storeys, style=style, wall=jitter(PLASTER[wall], 0.03), shutter=SHUTTER[shutter],
              windows=windows, ground=ground, floor=FLOORS[floor], plaque=plaque, vboards=list(vboards),
              laundry=laundry, chick=chick, lanterns=list(lanterns), sandbags=list(sandbags), jack=jack,
              pitch=pitch, roofcol=roofcol or jitter(C(1.0, 0.97, 0.94), 0.08), side_windows=side_windows,
              couplets=couplets, shop=shop, date=date, nwin=nwin, uvoff=R.random())
    h.__dict__.update(kw)
    return h


JC, JO, FT, PN, BO = "jal_closed", "jal_open", "french_taped", "panel", "blackout"

NORTH_W = [  # x -36 .. -8.5
    H(5.6, 3, "trans1", "buff", "darkgreen", [JC, PN, JC, JO], "planks", "redcement", side_windows="L", laundry=True,
      sandbags=[(0.6, 2.2)], jack=True),
    H(5.0, 2, "late", "celadon", "brown", [FT, FT, JO], "door", "terracotta", plaque=5, vboards=[(0.0, 8)], shop="photo",
      lanterns=[2.5], couplets=True),
    H(6.2, 3, "late", "cream", "green", [JC, FT, JC, JO, JC, BO], "open", "terracotta", plaque=1,
      vboards=[(0.0, 1), (6.2, 2)], shop="medical", chick="up", jack=True),
    H(5.2, 2, "early", "offwhite", "oxblood", [JO, JC], "pintu", "redcement", laundry=True, couplets=True,
      sandbags=[(0.4, 1.4), (3.8, 4.8)]),
    H(5.5, 3, "trans2", "ochre", "brown", [JC, JC, PN, FT, JC, JC], "planks", "cement", plaque=7, vboards=[(0.0, 10)], shop="tea",
      chick="down"),
]
KOPI = H(6.0, 2, "late", "venred", "darkgreen", [JO, FT, JO], "kopitiam", "terrazzo", plaque=0,
         vboards=[(0.0, 0), (6.0, 0)], lanterns=[1.6, 4.4], side_windows="R", shop="kopitiam", jack=True)
NORTH_E = [  # x 2.5 .. 36
    H(5.5, 3, "trans1", "bluegrey", "bluegrey", [JC, JO, PN, JC], "door", "cement", plaque=10, vboards=[(5.5, 15)],
      side_windows="L", laundry=True, shop="lodging"),
    H(5.2, 2, "trans2", "sand", "teal", [JC, FT, JC], "open", "terracotta", plaque=8, shop="rice", group="PRE_Intact_House",
      chick="up"),
    H(5.6, 2, "early", "grey", "darkgreen", [JC, JO], "pintu", "redcement", laundry=True, couplets=True,
      sandbags=[(0.4, 1.6)]),
    H(5.6, 3, "late", "pink", "green", [JC, FT, JO, JC, JC, JC], "open", "terracotta", plaque=3, vboards=[(0.0, 5), (5.6, 6)],
      shop="provision", chick="up", lanterns=[2.8], jack=True),
    H(5.6, 2, "deco", "lime", "brown", [FT, FT, FT], "open", "terrazzo", plaque=11, shop="bicycle", date=1938),
    H(6.0, 3, "trans1", "offwhite", "oxblood", [JC, JC, PN, PN], "planks", "cement", plaque=6, vboards=[(6.0, 9)], shop="pawn",
      side_windows="R", laundry=True),
]
SOUTH_E = [  # x 36 .. 27 (running west)
    H(4.5, 2, "early", "sand", "brown", [JC, JO], "pintu", "redcement", side_windows="L", couplets=True, laundry=True),
    H(4.5, 2, "trans2", "buff", "teal", [JC, FT], "open", "cement", plaque=9, shop="clogs", side_windows="R", nwin=2),
]
SOUTH_W = [  # x 17 .. -36 (running west)
    H(5.2, 2, "trans1", "offwhite", "green", [JC, JO], "pintu", "terracotta", side_windows="L", couplets=True,
      sandbags=[(0.4, 1.5), (3.7, 4.8)]),
    H(5.6, 3, "late", "ochre", "oxblood", [JC, PN, JC, JC, JC, JC], "planks", "terracotta", plaque=4, vboards=[(0.0, 7), (5.6, 7)],
      shop="gold", jack=True),
    H(5.0, 2, "early", "celadon", "darkgreen", [JO, JC], "pintu", "redcement", laundry=True),
    H(6.0, 3, "late", "cream", "bluegrey", [FT, FT, FT, JC, JO, JC], "open", "terracotta", plaque=2, vboards=[(0.0, 3), (6.0, 4)],
      shop="tailor", lanterns=[3.0], chick="up", sandbags=[(0.5, 1.5)]),
    H(4.8, 2, "deco", "grey", "brown", [JC, FT, JC], "door", "terrazzo", date=1936, laundry=True),
    H(5.4, 3, "trans2", "pink", "green", [JC, JC, JO, JC, PN, JC], "planks", "cement", chick="down", jack=True),
    H(6.2, 2, "late", "buff", "teal", [JC, BO, JC], "pintu", "terracotta", couplets=True, laundry=True),
    H(5.0, 3, "trans1", "venred", "darkgreen", [JC, JO, JC, JC], "door", "redcement", laundry=True),
    H(4.6, 2, "early", "offwhite", "oxblood", [PN, JC], "planks", "redcement"),
    H(5.2, 3, "late", "sand", "green", [JC, FT, JC, JO, JC, JC], "pintu", "terracotta", side_windows="R", jack=True, laundry=True),
]


def layout_rows():
    # North west part
    x = X_MIN
    for h in NORTH_W:
        h.frame = Frame(x, FP, 1, 0)
        h.x0 = x
        x += h.W
    KOPI.frame = Frame(x, FP, 1, 0)
    KOPI.x0 = x
    x = 2.5
    for h in NORTH_E:
        h.frame = Frame(x, FP, 1, 0)
        h.x0 = x
        x += h.W
    x = X_MAX
    for h in SOUTH_E:
        h.frame = Frame(x, -FP, -1, 0)
        h.x0 = x
        x -= h.W
    x = 17.0
    for h in SOUTH_W:
        h.frame = Frame(x, -FP, -1, 0)
        h.x0 = x
        x -= h.W
    assert abs(sum(h.W for h in NORTH_W) - 27.5) < 1e-6, sum(h.W for h in NORTH_W)
    assert abs(sum(h.W for h in NORTH_E) - 33.5) < 1e-6, sum(h.W for h in NORTH_E)
    assert abs(sum(h.W for h in SOUTH_W) - 53.0) < 1e-6, sum(h.W for h in SOUTH_W)


# ======================================================================================
# Kopitiam (Ah Ma's "Hock Kee" coffee shop) — corner house by the lane
# ======================================================================================
KOPI_D = 10.0   # interior depth (v)
# (u, v, chair angles in degrees) — local kopitiam frame (u = x + 8.5, v = y - 4.0)
KOPI_TABLES = [(1.3, 4.2, (270, 180)), (1.3, 6.2, (180, 90, 0)), (3.0, 5.2, (90, 270))]


def kopitiam_interior(h):
    fr = h.frame
    W = h.W
    ui0, ui1 = 0.15, W - 0.2
    # header beam at the (removed) shopfront line — the whole front folds open
    box(fr, "M_Plaster", (0.0, SV - 0.12, 3.3), (W, SV + 0.18, GF), mul(h.wall, 0.95), skip=("+z",))
    # terrazzo floor in a two-tone grid (cream / grey-green)
    n_u, n_v = 8, 12
    for i in range(n_u):
        for j in range(n_v):
            a0 = ui0 + (ui1 - ui0) * i / n_u
            a1 = ui0 + (ui1 - ui0) * (i + 1) / n_u
            b0 = SV + (KOPI_D - SV) * j / n_v
            b1 = SV + (KOPI_D - SV) * (j + 1) / n_v
            c = FLOORS["terrazzo"] if (i + j) % 2 == 0 else C(0.56, 0.60, 0.54)
            face(fr, "M_Floor", [(a0, b0, FFW), (a1, b0, FFW), (a1, b1, FFW), (a0, b1, FFW)], c, s=1.2)
    dado = C(0.36, 0.50, 0.44)
    upper = C(0.90, 0.88, 0.80)
    # side walls: dado + whitewash, tile band
    for uu, facing in ((ui0, "+u"), (ui1, "-u")):
        ugrid(fr, "M_Plaster", SV, KOPI_D, FFW, 1.25, uu, dado, s=2.0, cell=1.5, facing=facing)
        ugrid(fr, "M_Plaster", SV, KOPI_D, 1.25, GF, uu, upper, s=2.0, cell=1.5, facing=facing)
        sf = Frame(*fr.w((uu, KOPI_D if facing == "+u" else SV, 0))[:2], *fr.dirw(0, -1 if facing == "+u" else 1))
        L = KOPI_D - SV
        for k in range(int(L / 0.6)):
            atlas_quad(sf, "M_Details", k * 0.6, k * 0.6 + 0.6, 1.25, 1.55, -0.01, DET["tiles"], WHITE)
    # interior side window (lane side)
    sf = Frame(*fr.w((ui1, SV, 0))[:2], *fr.dirw(0, 1))
    atlas_quad(sf, "M_Details", 7.4 - SV, 8.4 - SV, 0.9, 2.5, -0.01, DET["barred"], SHUTTER["cream"])
    # back wall with kitchen doorway
    door = (3.9, FFW, 4.9, 2.4)
    wall_with_holes(fr, "M_Plaster", ui0, ui1, FFW, GF, [door], KOPI_D, upper, s=2.0)
    recess(fr, door, KOPI_D, 0.3, upper, "M_Windows", WHITE, back_uv=arect(WIN["open"]), sill=False)
    box(fr, "M_Plaster", (ui0, KOPI_D - 0.01, FFW), (ui1, KOPI_D, 1.25), dado, skip=("+v",))
    # ceiling (timber boards) + joists
    grid_quad(fr, "M_Timber", ui0, ui1, SV, KOPI_D, GF, mul(TIMBER_RAW, 0.8), s=1.0, cell=1.5, down=True)
    with DETAIL():
        for k in range(8):
            vv = SV + 0.4 + k * 0.95
            box(fr, "M_Timber", (ui0, vv, GF - 0.18), (ui1, vv + 0.12, GF), TIMBER_DARK)
        # ceiling fan (1930s electric)
        fc = fr.w((W / 2, 5.4, GF - 0.18))
        tube("M_Metal", fc, (fc[0], fc[1], fc[2] - 0.5), 0.02, 4, IRON)
        cyl(WORLD, "M_Metal", (fc[0], fc[1], fc[2] - 0.62), 0.1, 0.12, 8, IRON)
        for k in range(4):
            a = k * math.pi / 2 + 0.3
            mbox(M_at(fc[0] + math.cos(a) * 0.4, fc[1] + math.sin(a) * 0.4, fc[2] - 0.56, a), "M_Timber", (0.62, 0.12, 0.012), TIMBER_DARK)
    # hanging bulb (emissive, unlit by day)
    bc = fr.w((W / 2, 3.6, GF))
    tube("M_Metal", bc, (bc[0], bc[1], bc[2] - 0.7), 0.006, 3, IRON, smooth=False)
    sphere("M_Emissive", (bc[0], bc[1], bc[2] - 0.78), 0.06, C(1.0, 0.85, 0.6), nu=6, nv=4)
    cyl(WORLD, "M_Metal", (bc[0], bc[1], bc[2] - 0.76), 0.18, 0.06, 8, C(0.3, 0.35, 0.3), r_top=0.04, caps=False)

    # --- counter with glass biscuit jars, the kopi boiler on its charcoal stove ---
    cu0, cu1, cv0, cv1 = 0.35, 3.6, 7.55, 8.2
    box(fr, "M_Timber", (cu0, cv0, FFW), (cu1, cv1, FFW + 0.95), C(0.40, 0.26, 0.16), s=1.0)
    box(fr, "M_Details", (cu0 - 0.03, cv0 - 0.03, FFW + 0.95), (cu1 + 0.03, cv1 + 0.03, FFW + 1.0), WHITE,
        uvs={"+z": arect(DET["marble"])}, mats={k: "M_Timber" for k in ("-v", "+v", "-u", "+u", "-z")},
        cols={k: TIMBER_DARK for k in ("-v", "+v", "-u", "+u", "-z")})
    collider_local(fr, "COL_Kopi_Counter", (cu0, cv0, 0), (cu1, cv1, 1.2), unique=True)
    for i in range(6):
        cu = cu0 + 0.3 + i * 0.52
        cyl(fr, "M_Metal", (cu, cv0 + 0.28, FFW + 1.0), 0.1, 0.26, 8, C(0.60, 0.68, 0.70), cap_col=RED)
        cyl(fr, "M_Cloth", (cu, cv0 + 0.28, FFW + 1.02), 0.08, 0.14, 8, R.choice([C(0.85, 0.7, 0.4), C(0.8, 0.5, 0.3), C(0.9, 0.85, 0.7)]))
    # stove + boiler behind the counter (0.75 m gap behind the counter for Ah Ma)
    box(fr, "M_Plaster", (0.4, 8.95, FFW), (2.2, 9.95, FFW + 0.8), C(0.62, 0.42, 0.34), s=1.0)
    box(fr, "M_Plaster", (0.35, 8.9, FFW + 0.8), (2.25, 9.98, FFW + 0.86), C(0.5, 0.5, 0.48))
    cyl(fr, "M_Metal", (0.95, 9.45, FFW + 0.86), 0.32, 0.62, 12, C(0.72, 0.42, 0.26), r_top=0.3)   # copper urn
    cyl(fr, "M_Metal", (0.95, 9.45, FFW + 1.48), 0.3, 0.1, 12, C(0.60, 0.36, 0.22), r_top=0.12)
    tube("M_Metal", fr.w((0.95, 9.13, FFW + 1.0)), fr.w((0.95, 8.95, FFW + 1.0)), 0.03, 5, C(0.7, 0.6, 0.3))
    for (ku, kv) in ((1.7, 9.25), (1.95, 9.7)):
        cyl(fr, "M_Metal", (ku, kv, FFW + 0.86), 0.13, 0.22, 8, C(0.55, 0.55, 0.52), r_top=0.08)
        tube("M_Metal", fr.w((ku, kv - 0.1, FFW + 0.98)), fr.w((ku, kv - 0.28, FFW + 1.12)), 0.018, 4, C(0.55, 0.55, 0.52))
    # kopi sock strainer on a stand at the counter's end
    tube("M_Metal", fr.w((3.3, 7.85, FFW + 1.0)), fr.w((3.3, 7.85, FFW + 1.5)), 0.01, 3, IRON, smooth=False)
    cyl(fr, "M_Cloth", (3.3, 7.85, FFW + 1.12), 0.02, 0.3, 6, C(0.55, 0.40, 0.24), r_top=0.07)
    collider_local(fr, "COL_Kopi_Stove", (0.35, 8.9, 0), (2.25, 9.98, 1.6), unique=True)
    # shelves with tins behind; price board; clock + calendar; altar shelf
    atlas_quad(fr, "M_Details", 2.5, 4.6, 1.3, 2.6, KOPI_D - 0.02, DET["provisions"], WHITE)
    board(fr, "M_Details", 0.5, 1.7, 2.1, 3.3, KOPI_D - 0.05, 0.04, DET["menu"])
    sf = Frame(*fr.w((ui0, KOPI_D, 0))[:2], *fr.dirw(0, -1))
    board(sf, "M_Details", 2.0, 3.2, 1.9, 3.1, -0.04, 0.03, DET["clock"])
    box(fr, "M_Timber", (3.9, KOPI_D - 0.45, 2.75), (5.3, KOPI_D, 2.82), RED)   # altar shelf
    board(fr, "M_Signs", 4.05, 5.15, 2.86, 3.1, KOPI_D - 0.08, 0.04, plaque_rect(0))
    sphere("M_Emissive", fr.w((4.6, KOPI_D - 0.25, 2.9)), 0.05, C(1.0, 0.3, 0.2), nu=6, nv=4)
    # three marble-top tables on the left half; the right half (u 3.9..5.8) is a clear
    # 1.9 m walkway from the five-foot way to the counter's end
    for ti, (tu, tv, angles) in enumerate(KOPI_TABLES):
        x, y, _ = fr.w((tu, tv, 0))
        marble_table(x, y, FFW)
        collider("COL_Kopi_Table_%d" % (ti + 1), (x - 0.4, y - 0.4, 0), (x + 0.4, y + 0.4, 1.0))
        for a_deg in angles:
            a = math.radians(a_deg)
            cx, cy = x + math.cos(a) * 0.62, y + math.sin(a) * 0.62
            chair(M_at(cx, cy, FFW, a - math.pi / 2), TIMBER_DARK)
        with DETAIL():
            for k in range(R.randint(1, 2)):
                a = R.uniform(0, 6.28)
                cyl(WORLD, "M_Plaster", (x + math.cos(a) * 0.2, y + math.sin(a) * 0.2, FFW + 0.75), 0.04, 0.07, 8, C(0.92, 0.9, 0.85))
    with DETAIL():
        # songbird cage hung in the five-foot way (a kopitiam institution)
        bc = Vector(fr.w((2.6, 1.2, GF - 0.2)))
        tube("M_Metal", bc, bc - Vector((0, 0, 0.6)), 0.005, 3, IRON, smooth=False)
        cyl(WORLD, "M_Timber", tuple(bc - Vector((0, 0, 1.05))), 0.15, 0.03, 10, TIMBER_DARK)
        for k in range(10):
            a = math.tau * k / 10
            tube("M_Timber", bc - Vector((-math.cos(a) * 0.15, -math.sin(a) * 0.15, 1.02)), bc - Vector((0, 0, 0.6)), 0.005, 3, BAMBOO, smooth=False)
    # colliders for the kopitiam shell
    collider("COL_Kopi_Back", fr.w((0, KOPI_D, 0)), fr.w((W, DEPTH, 4.5)))
    collider("COL_Kopi_WallE", fr.w((W - 0.2, SV, 0)), fr.w((W, DEPTH, 4.5)))


# ======================================================================================
# Street surfaces
# ======================================================================================
def road_surfaces():
    fr = WORLD
    grid_quad(fr, "M_Road", X_MIN, X_MAX, -ROAD_HW, ROAD_HW, 0.0, ROAD, s=4.0, cell=1.0)
    # cross streets (South Bridge Road stand-in to the east, another to the west)
    grid_quad(fr, "M_Road", X_MAX, 44.6, -46, 46, 0.0, ROAD, s=4.0, cell=2.0)
    grid_quad(fr, "M_Road", -44.6, X_MIN, -46, 46, 0.0, ROAD, s=4.0, cell=2.0)
    # lane and lot
    grid_quad(fr, "M_Road", -2.5, 2.5, DRAIN_Y1, 12.0, 0.0, C(0.52, 0.46, 0.38), s=4.0, cell=1.0)
    grid_quad(fr, "M_Road", 17.0, 27.0, -17.0, -DRAIN_Y1, 0.0, EARTH, s=3.0, cell=1.0)
    # kerbs / drains
    kerb_segment("N", X_MIN, -2.5, bridges=[-33.2, -27.9, -22.3, -16.6, -11.25, -5.5])
    kerb_segment("N", 2.5, X_MAX, bridges=[5.25, 10.6, 16.0, 21.6, 27.2, 33.0])
    kerb_segment("S", X_MIN, 17.0, bridges=[14.4, 9.0, 3.7, -1.8, -7.2, -12.3, -18.1, -23.7, -28.5, -33.4])
    kerb_segment("S", 27.0, X_MAX, bridges=[29.25, 33.75])
    # drain covered by slabs across the lane mouth and the lot entrance
    for (xa, xb, s) in ((-2.5, 2.5, 1), (17.0, 27.0, -1)):
        fr2 = Frame(0, 0, 1, 0) if s > 0 else Frame(0, 0, -1, 0)
        ua, ub = (xa, xb) if s > 0 else (-xb, -xa)
        box(fr2, "M_Plaster", (ua, ROAD_HW, -0.2), (ub, DRAIN_Y1, KERB_Z), mul(GRANITE, 0.9), skip=("-z",))
    # corner kerbs along the cross streets (so the street ends read as junctions)
    for xs, sgn in ((X_MAX, 1), (X_MIN, -1)):
        for ys in (1, -1):
            y0, y1 = (FP, 46) if ys > 0 else (-46, -FP)
            box(WORLD, "M_Plaster", (xs - 0.0 if sgn > 0 else xs - 0.1, y0, 0), (xs + 0.1 if sgn > 0 else xs, y1, FFW), GRANITE)


def kerb_segment(side, x0, x1, bridges=()):
    kerb_and_drain(x0, x1, side, bridges=[b for b in bridges if x0 < b < x1])


# ======================================================================================
# Lane (north, x -2.5..2.5) and the open lot with the shelter (south, x 17..27)
# ======================================================================================
def build_lane():
    # end wall with a timber back gate
    fr = Frame(-2.5, 12.0, 1, 0)
    gate = (1.6, 0.0, 3.4, 2.3)
    wall_with_holes(fr, "M_Plaster", 0, 5.0, 0.0, 3.0, [gate], 0.0, jitter(PLASTER["grey"]), s=2.0)
    recess(fr, gate, 0.0, 0.12, PLASTER["grey"], "M_Details", mul(SHUTTER["brown"], 1.4), back_uv=arect(DET["planks"]), sill=False)
    box(fr, "M_Plaster", (-0.05, 0.0, 3.0), (5.05, 0.3, 3.12), PLASTER["grey"])
    box(fr, "M_Plaster", (0, 0.12, 0), (5.0, 4.5, 3.0), mul(PLASTER["grey"], 0.9), skip=("-v", "-z"))
    collider("COL_Lane_End", (-2.5, 11.9, 0), (2.5, 12.6, 3.2))
    # washing lines across the lane (between upper windows)
    with GROUP("LAUNDRY_Street"):
        lane_washing()
    with GROUP("WAR_Street"):
        lane_props()


def lane_washing():
    for (yy, zz) in ((7.0, 5.4), (9.6, 6.1)):
        wire((-2.5, yy, zz), (2.5, yy + 0.3, zz + 0.1), sag=0.35, r=0.008, n=6, col=C(0.6, 0.55, 0.45))
        for k in range(4):
            t = 0.12 + k * 0.22
            p = Vector((-2.5 + 5 * t, yy + 0.3 * t, zz + 0.1 * t - 0.35 * 4 * t * (1 - t)))
            cloth(tuple(p), tuple(p + Vector((0.5, 0.03, 0))), R.uniform(0.5, 0.9), R.choice([C(0.9, 0.9, 0.86), C(0.46, 0.5, 0.62), C(0.66, 0.4, 0.3), C(0.75, 0.7, 0.55)]))


def lane_props():
    water_jar(-2.0, 11.2, 0.0)
    water_jar(1.9, 11.4, 0.0, 0.6)
    collider("COL_Lane_Jars", (-2.5, 10.8, 0), (2.5, 11.9, 1.0))
    # noodle hawker's pushcart parked at the lane mouth
    hawker_cart(0.3, 6.4, math.radians(90))
    collider("COL_Hawker", (-0.2, 5.5, 0), (0.8, 7.3, 2.1))
    carrying_pole(-1.6, 8.8, math.radians(10))
    collider("COL_Baskets", (-2.0, 7.9, 0), (-1.2, 9.7, 0.6))


def build_lot():
    """Open lot: brick & sandbag surface shelter, ARP wardens' post, poster wall."""
    # rear walls of the next street's houses closing the lot (y = -17)
    fr = Frame(23.9, -17.0, -1, 0)   # faces +y (toward the street)
    rear_h = 7.6
    holes = [(1.0, 3.8, 1.8, 5.2), (3.6, 3.8, 4.4, 5.2), (6.2, 3.8, 7.0, 5.2),
             (2.2, 0.8, 3.0, 1.9), (5.6, 0.8, 6.4, 1.9)]
    wall_with_holes(fr, "M_Plaster", 0, 8.4, 0, rear_h, holes, 0.0, jitter(PLASTER["grey"]), s=2.0)
    for hh in holes:
        recess(fr, hh, 0.0, 0.15, PLASTER["grey"], "M_Windows" if hh[1] > 2 else "M_Details", SHUTTER["brown"],
               back_uv=arect(WIN["jal_closed"] if hh[1] > 2 else DET["barred"]))
    box(fr, "M_Plaster", (0, 0.0, rear_h), (8.4, 11.0, rear_h + 0.3), mul(PLASTER["grey"], 0.9), skip=("-z",))
    ugrid(fr, "M_Plaster", 0, 11.0, 0, rear_h, 0.0, mul(PLASTER["grey"], 0.85), s=2.0, cell=3.0, facing="-u")
    h = House(W=13.0, storeys=2, style="early", wall=PLASTER["grey"], shutter=SHUTTER["brown"], pitch=24,
              roofcol=C(0.9, 0.86, 0.82), jack=False, uvoff=0.3, date=1936)
    collider("COL_Lot_Back", (16.0, -17.6, 0), (28.0, -16.0, 4.0))
    # boundary wall in front of the rear kitchens
    box(WORLD, "M_Brick", (17.0, -16.6, 0), (27.0, -16.35, 2.1), C(0.95, 0.9, 0.85), s=(0.96, 0.8))
    box(WORLD, "M_Plaster", (16.95, -16.65, 2.1), (27.05, -16.3, 2.2), GRANITE)

    with GROUP("WAR_Street"):
        # --- the shelter: brick walls, concrete slab, banked sandbags, sandbagged entrance porch ---
        sx0, sx1, sy0, sy1 = 18.2, 24.2, -14.6, -10.2
        wall_h = 2.35
        door_x = 21.2
        fr = Frame(sx0, sy1, 1, 0)  # local: u along x, v = -(y - sy1) ... use world boxes instead
        brick = C(0.80, 0.74, 0.68)
        box(WORLD, "M_Brick", (sx0, sy0, 0), (sx1, sy0 + 0.35, wall_h), brick, s=(0.96, 0.8))
        box(WORLD, "M_Brick", (sx0, sy0, 0), (sx0 + 0.35, sy1, wall_h), brick, s=(0.96, 0.8))
        box(WORLD, "M_Brick", (sx1 - 0.35, sy0, 0), (sx1, sy1, wall_h), brick, s=(0.96, 0.8))
        frn = Frame(sx0, sy1, 1, 0)  # north wall faces -v? north wall faces +y: use frame with u=+x, v=-y
        frn = Frame(sx0, sy1, 1, 0)
        # north wall as box segments leaving the door
        box(WORLD, "M_Brick", (sx0, sy1 - 0.35, 0), (door_x - 0.5, sy1, wall_h), brick, s=(0.96, 0.8))
        box(WORLD, "M_Brick", (door_x + 0.5, sy1 - 0.35, 0), (sx1, sy1, wall_h), brick, s=(0.96, 0.8))
        box(WORLD, "M_Brick", (door_x - 0.5, sy1 - 0.35, 1.95), (door_x + 0.5, sy1, wall_h), brick, s=(0.96, 0.8))
        # dark interior behind the door (the playable interior is the separate room at X = 200)
        box(WORLD, "M_Plaster", (door_x - 0.5, sy1 - 1.2, 0), (door_x + 0.5, sy1 - 0.35, 1.95), C(0.05, 0.05, 0.05), skip=("+v",))
        box(WORLD, "M_Timber", (door_x - 0.48, sy1 - 0.3, 0.0), (door_x - 0.05, sy1 - 0.25, 1.9), C(0.35, 0.25, 0.18))  # door leaf ajar
        # roof slab
        box(WORLD, "M_Plaster", (sx0 - 0.25, sy0 - 0.25, wall_h), (sx1 + 0.25, sy1 + 0.25, wall_h + 0.3), C(0.66, 0.65, 0.62), s=2.0)
        # banked sandbags against the walls (except the door) and a row on the roof edge
        fr_s = Frame(sx1, sy0, -1, 0)      # south face: u along -x, v into shelter (+y)
        sandbag_wall(fr_s, 0, sx1 - sx0, -0.7, -0.02, 0.0, 8)
        fr_w = Frame(sx0, sy0, 0, 1)       # west face: u along +y, v = +x (into shelter)
        sandbag_wall(fr_w, 0, sy1 - sy0, -0.7, -0.02, 0.0, 8)
        fr_e = Frame(sx1, sy1, 0, -1)      # east face: u along -y, v = -x
        sandbag_wall(fr_e, 0, sy1 - sy0, -0.7, -0.02, 0.0, 8)
        fr_n = Frame(sx0, sy1, 1, 0)       # north face: v = +y... north face outward is +y -> use u=-x frame
        fr_n = Frame(sx1, sy1, -1, 0)
        fr_n = Frame(sx0, sy1, 1, 0)
        fr_n2 = Frame(sx1, sy1, -1, 0)
        # north face outward normal is +y, frame with u=+x has v=+y (outward) -> bags at v 0.02..0.7
        sandbag_wall(fr_n, 0, door_x - 0.9 - sx0, 0.02, 0.7, 0.0, 8)
        sandbag_wall(fr_n, door_x + 0.9 - sx0, sx1 - sx0, 0.02, 0.7, 0.0, 8)
        for f_, L in ((fr_s, sx1 - sx0), (fr_w, sy1 - sy0), (fr_e, sy1 - sy0)):
            sandbag_wall(f_, 0.2, L - 0.2, 0.0, 0.34, wall_h + 0.3, 2)
        # entrance porch: sandbag wing walls + timber lintel + sandbags over
        for (a, b) in ((door_x - 0.9, door_x - 0.55), (door_x + 0.55, door_x + 0.9)):
            frp = Frame(a, sy1, 0, 1)   # u along +y
            sandbag_wall(Frame(a, sy1 + 0.02, 0, 1), 0.0, 1.8, -0.35, 0.0, 0.0, 12, bag=(0.45, 0.35, 0.15))
        box(WORLD, "M_Timber", (door_x - 0.95, sy1, 1.8), (door_x + 0.95, sy1 + 1.85, 1.92), TIMBER_RAW)
        sandbag_wall(Frame(door_x - 0.9, sy1 + 0.1, 1, 0), 0, 1.8, 0.0, 1.7, 1.92, 1)
        # sign above the porch
        frs = Frame(door_x + 0.8, sy1 + 1.97, -1, 0)
        board(frs, "M_Signs", 0.0, 1.6, 2.3, 2.62, 0.0, 0.04, SIGN_SMALL["shelter"])
        tube("M_Timber", (door_x - 0.9, sy1 + 1.93, 0), (door_x - 0.9, sy1 + 1.93, 2.6), 0.04, 5, TIMBER_DARK)
        tube("M_Timber", (door_x + 0.9, sy1 + 1.93, 0), (door_x + 0.9, sy1 + 1.93, 2.6), 0.04, 5, TIMBER_DARK)
        collider("COL_Shelter", (sx0 - 0.75, sy0 - 0.75, 0), (sx1 + 0.75, sy1 + 0.05, 3.0))
        collider("COL_Shelter_N_W", (sx0 - 0.75, sy1, 0), (door_x - 0.9, sy1 + 0.75, 2.0))
        collider("COL_Shelter_N_E", (door_x + 0.9, sy1, 0), (sx1 + 0.75, sy1 + 0.75, 2.0))
        collider("COL_Shelter_Porch_W", (door_x - 1.3, sy1, 0), (door_x - 0.55, sy1 + 1.85, 2.0))
        collider("COL_Shelter_Porch_E", (door_x + 0.55, sy1, 0), (door_x + 1.3, sy1 + 1.85, 2.0))

        # --- ARP wardens' post: sandbagged enclosure with a zinc roof ---
        ax0, ax1, ay0, ay1 = 17.35, 20.3, -7.2, -4.4
        sandbag_wall(Frame(ax0, ay0, 0, 1), 0.0, ay1 - ay0, 0.0, 0.38, 0.0, 9)
        sandbag_wall(Frame(ax1, ay0, 1, 0), -(ax1 - ax0), 0.0, 0.0, 0.38, 0.0, 9)
        sandbag_wall(Frame(ax1 - 0.38, ay0, 0, 1), 0.4, ay1 - ay0, 0.0, 0.38, 0.0, 9)
        sandbag_wall(Frame(ax0, ay1 - 0.38, 1, 0), 0.4, 1.3, 0.0, 0.38, 0.0, 9)
        for (px, py) in ((ax0 + 0.1, ay0 + 0.1), (ax1 - 0.1, ay0 + 0.1), (ax0 + 0.1, ay1 - 0.1), (ax1 - 0.1, ay1 - 0.1)):
            tube("M_Timber", (px, py, 0), (px, py, 2.25), 0.05, 5, TIMBER_RAW)
        for k in range(6):
            y0 = ay0 - 0.25 + k * (ay1 - ay0 + 0.5) / 6
            mbox(M_at((ax0 + ax1) / 2, y0 + 0.28, 2.3, 0, 0, math.radians(5)), "M_Metal", (ax1 - ax0 + 0.5, 0.56, 0.02),
                 jitter(C(0.48, 0.48, 0.46), 0.1))
        # table, telephone, stirrup pump, buckets, stretcher, helmets
        box(WORLD, "M_Timber", (18.0, -6.9, 0), (19.4, -6.3, 0.78), TIMBER_RAW)
        mbox(M_at(18.4, -6.6, 0.85, 0), "M_Metal", (0.18, 0.14, 0.12), IRON)
        for k in range(4):
            bucket_(20.6 + k * 0.33, -4.35, 0.0, C(0.58, 0.13, 0.11), sand=(k % 2 == 0))
        tube("M_Metal", (21.95, -4.6, 0.0), (21.95, -4.6, 0.75), 0.03, 5, C(0.5, 0.45, 0.3))  # stirrup pump
        mbox(M_at(21.95, -4.6, 0.02, 0), "M_Metal", (0.3, 0.12, 0.03), C(0.5, 0.45, 0.3))
        mbox(M_at(17.6, -7.5, 0.9, math.radians(90), math.radians(78)), "M_Cloth", (1.9, 0.55, 0.04), C(0.55, 0.52, 0.4))
        for k in range(2):
            sphere("M_Metal", (19.7 + k * 0.3, -6.9, 1.9), 0.17, C(0.28, 0.30, 0.24), nu=8, nv=4, sz=0.45)
        collider("COL_ARP_Post", (ax0 - 0.05, ay0 - 0.35, 0), (ax1 + 0.05, ay1 + 0.05, 2.4))
        collider("COL_ARP_Buckets", (20.4, -4.7, 0), (22.2, -4.1, 0.9))
        # sign (PRE: the ARP post is gone under the occupation)
        with GROUP("PRE_ARPSign"):
            board(Frame(ax0 + 2.5, ay1 + 0.1, -1, 0), "M_Signs", 0.0, 2.1, 1.55, 2.08, 0.0, 0.04, SIGN_SMALL["arp"])
        # pile of spare sandbags and empty sacks, planks
        for k in range(9):
            M = M_at(25.4 + R.uniform(-0.6, 0.6), -5.6 + R.uniform(-0.4, 0.4), 0.08 + (k // 4) * 0.14, R.uniform(0, 3))
            sandbag(M)
        collider("COL_Lot_Bags", (24.6, -6.2, 0), (26.2, -5.0, 0.5))
        for k in range(5):
            mbox(M_at(25.7, -14.0 + k * 0.05, 0.05 + k * 0.05, math.radians(90) + R.uniform(-0.1, 0.1)), "M_Timber", (3.0, 0.25, 0.05), TIMBER_RAW)
        handcart(26.0, -12.0, math.radians(200), load=None)
        collider("COL_Lot_Cart", (25.0, -14.2, 0), (26.9, -10.0, 1.0))


def poster_wall_pre():
    """British war-effort / ARP posters on the lot gable wall (x = 27, facing -x)."""
    fr = Frame(27.0, -4.0, 0, -1)   # u along -y, v = +x?  (-uy, ux) = (1, 0) -> v points +x (into wall)
    with GROUP("PRE_Posters"):
        for k, (key, u) in enumerate((("p_arp", 2.6), ("p_siren", 3.9), ("p_talk", 5.2), ("p_savings", 6.5))):
            z0 = 0.75 + (0.08 if k % 2 else 0)
            atlas_quad(fr, "M_Posters", u, u + 1.0, z0, z0 + 1.5, -0.012, POSTER[key], WHITE)
        # posters on a couple of five-foot-way columns along the street
        for (x, y, key, s) in ((-13.775, FP - 0.0, "p_siren", 1), (-0.6, -FP, "p_talk", -1), (9.0, -FP, "p_arp", -1)):
            f = Frame(x - 0.22 * s, y, 1 * s, 0)
            atlas_quad(f, "M_Posters", 0.0, 0.44, 1.2, 1.86, -0.012, POSTER[key], WHITE)
    with GROUP("OCC_Notices"):
        atlas_quad(fr, "M_Posters", 2.9, 4.3, 0.8, 2.2, -0.024, POSTER["occ_notice"], WHITE)
        atlas_quad(fr, "M_Posters", 4.5, 5.9, 1.0, 1.9, -0.022, POSTER["torn"], WHITE)
        atlas_quad(fr, "M_Posters", 6.1, 7.5, 0.8, 2.2, -0.024, POSTER["occ_notice"], mul(WHITE, 0.92))
        for (x, y, s) in ((-13.775, FP, 1), (-0.6, -FP, -1)):
            f = Frame(x - 0.22 * s, y, 1 * s, 0)
            atlas_quad(f, "M_Posters", 0.0, 0.44, 1.2, 1.86, -0.024, POSTER["occ_notice"], WHITE)


# ======================================================================================
# Street props and dressing
# ======================================================================================
def satay_cart(x, y, rz):
    """Pak Hassan's two-wheeled satay pushcart — one wheel has come off."""
    base = M_at(x, y, 0, rz)
    tilt = math.radians(-8)
    body = base @ M_at(0, 0, 0.0, 0, tilt)
    mbox(body @ M_at(0, 0, 0.72, 0), "M_Timber", (1.5, 0.62, 0.05), TIMBER_RAW)
    mbox(body @ M_at(0, 0, 0.45, 0), "M_Details", (1.4, 0.56, 0.5), WHITE,
         uvs={"-v": arect(DET["planks"]), "+v": arect(DET["planks"]), "-u": arect(DET["planks"]), "+u": arect(DET["planks"])})
    # charcoal grill trough on top
    mbox(body @ M_at(0.1, 0, 0.84, 0), "M_Metal", (1.1, 0.24, 0.18), C(0.22, 0.2, 0.18))
    mbox(body @ M_at(0.1, 0, 0.935, 0), "M_Emissive", (1.0, 0.18, 0.01), C(0.45, 0.12, 0.05))
    for k in range(9):
        tube("M_Timber", body @ Vector((-0.35 + k * 0.1, -0.2, 0.97)), body @ Vector((-0.35 + k * 0.1, 0.25, 0.97)), 0.006, 3, BAMBOO, smooth=False)
        cyl(WORLD, "M_Plaster", tuple(body @ Vector((-0.35 + k * 0.1, 0.02, 0.955))), 0.018, 0.035, 5, C(0.45, 0.22, 0.1))
    # push handles
    for py in (-0.25, 0.25):
        tube("M_Timber", body @ Vector((-0.7, py, 0.72)), body @ Vector((-1.4, py, 0.9)), 0.025, 5, TIMBER_DARK)
    # wheels: one on, one off lying against the kerb
    wheel(base @ M_at(0.2, 0.36, 0.42, 0), 0.42, 0.06, 10)
    wheel(base @ M_at(0.9, -1.0, 0.04, 0.5, math.radians(90)), 0.42, 0.06, 10)
    tube("M_Metal", base @ Vector((0.2, 0.36, 0.42)), base @ Vector((0.2, -0.3, 0.32)), 0.022, 5, IRON)
    # stool, basket of skewers, peanut-sauce pot, fan
    stool(*tuple(base @ Vector((-0.6, -0.95, 0))))
    cyl(WORLD, "M_Details", tuple(base @ Vector((0.9, 0.9, 0))), 0.26, 0.3, 8, WHITE)
    cyl(WORLD, "M_Metal", tuple(base @ Vector((-0.1, 0.9, 0))), 0.16, 0.24, 8, C(0.5, 0.45, 0.4), cap_col=C(0.5, 0.3, 0.12))
    carrying_pole(*tuple(base @ Vector((1.8, 0.2, 0)))[:2], rz + 0.3)


def street_props():
    with GROUP("WAR_Street"):
        _street_props()


def _street_props():
    # Pak Hassan's broken satay cart (south kerb)
    satay_cart(-12.2, -2.35, math.radians(4))
    collider("COL_SatayCart", (-13.7, -3.5, 0), (-10.6, -1.4, 1.1))
    # a parked (intact) rickshaw by the north kerb and a pedal trishaw on the south side
    rickshaw(-18.2, 2.55, math.radians(-90), broken=False)
    collider("COL_Rickshaw", (-20.4, 1.9, 0), (-17.6, 3.2, 1.6))
    trishaw(8.2, -2.7, math.radians(90))
    collider("COL_Trishaw", (6.7, -3.4, 0), (9.2, -2.0, 1.4))
    # bicycle leaning on the column at x = -14 (SNAP_Bicycle)
    bicycle(-13.0, 4.33, FFW, 0.0, lean=math.radians(-10))
    collider("COL_Bicycle", (-13.6, 4.1, 0), (-12.3, 4.6, 1.0))
    # half-loaded handcart of a family leaving (haste)
    handcart(-21.4, 2.25, math.radians(-100), load="half")
    collider("COL_Handcart", (-23.0, 1.5, 0), (-19.4, 3.1, 1.2))
    # bundles, suitcases, baskets on the five-foot ways
    for (x, y, kind) in ((-17.4, 6.2, "b"), (-16.9, 6.3, "s"), (-16.2, 6.25, "b"), (-7.8, -6.2, "s"), (-7.2, -6.35, "b"),
                         (-6.7, -6.2, "c"), (4.2, 6.2, "s"), (4.8, 6.3, "b"), (-24.7, -6.25, "c"), (-24.1, -6.3, "s")):
        if kind == "b":
            bundle(M_at(x, y, FFW + 0.2, R.uniform(0, 3)), 0.24)
        elif kind == "s":
            suitcase(M_at(x, y, FFW + 0.21, R.uniform(-0.2, 0.2)))
        else:
            crate(M_at(x, y, FFW + 0.18, R.uniform(-0.3, 0.3)))
    collider("COL_Bundles_1", (-17.8, 5.9, 0), (-15.9, 6.7, 0.7))
    collider("COL_Bundles_2", (-8.2, -6.7, 0), (-6.3, -5.9, 0.7))
    collider("COL_Bundles_3", (3.8, 5.9, 0), (5.2, 6.7, 0.7))
    collider("COL_Bundles_4", (-25.1, -6.7, 0), (-23.7, -5.9, 0.7))
    # a lost slipper on the road
    mbox(M_at(3.1, -0.9, 0.012, 0.6), "M_Cloth", (0.26, 0.1, 0.02), C(0.3, 0.28, 0.25))
    mbox(M_at(3.2, -0.87, 0.03, 0.6), "M_Cloth", (0.08, 0.09, 0.02), C(0.55, 0.2, 0.18))
    # Siti's newspaper bundle and stand
    box(WORLD, "M_Timber", (-28.0, 6.0, FFW), (-27.2, 6.6, FFW + 0.55), TIMBER_RAW)
    for k in range(4):
        mbox(M_at(-27.6 + R.uniform(-0.05, 0.05), 6.3, FFW + 0.6 + k * 0.04, R.uniform(-0.1, 0.1)), "M_Plaster", (0.5, 0.38, 0.04), C(0.86, 0.83, 0.76))
    collider("COL_NewsStand", (-28.1, 5.9, 0), (-27.1, 6.7, 0.9))
    # letter-writer's table + stool on the south five-foot way
    box(WORLD, "M_Timber", (3.3, -5.4, FFW + 0.7), (4.3, -4.8, FFW + 0.74), TIMBER_RAW)
    for (px, py) in ((3.35, -5.35), (4.25, -5.35), (3.35, -4.85), (4.25, -4.85)):
        box(WORLD, "M_Timber", (px - 0.02, py - 0.02, FFW), (px + 0.02, py + 0.02, FFW + 0.7), TIMBER_DARK)
    stool(3.8, -5.9, FFW)
    collider("COL_LetterTable", (3.2, -5.5, 0), (4.4, -4.7, 1.0))
    # water jars at house doors
    for (x, y) in ((-15.7, 6.35), (-26.9, -6.35), (-31.6, 6.4), (15.0, 6.35), (34.2, -6.35)):
        water_jar(x, y, FFW)
        collider("COL_Jar", (x - 0.36, y - 0.36, 0), (x + 0.36, y + 0.36, 1.0), unique=False)
    # sacks and tins outside the provision and rice shops
    for (x0, y0) in ((19.6, 6.25), (23.0, 6.25)):
        for k in range(3):
            cyl(WORLD, "M_Sandbag", (x0 + k * 0.5, y0, FFW), 0.22, 0.55, 7, SACK, r_top=0.18)
    collider("COL_Sacks_1", (19.3, 5.95, 0), (20.9, 6.7, 0.8))
    collider("COL_Sacks_2", (22.7, 5.95, 0), (24.3, 6.7, 0.8))
    # bicycles for sale outside the bicycle shop
    for k in range(2):
        bicycle(25.4 + k * 1.6, 6.3, FFW, 0.0, lean=math.radians(4))
    collider("COL_Bikes", (24.8, 6.0, 0), (28.6, 6.7, 1.0))
    # pillar post box
    pillar_box(-12.3, -4.4, FFW)
    # lamp posts (gas, blackout hoods) and timber utility poles with wires
    for x in (-31.2, 1.8, 14.8, 31.0):
        lamp_post(x, 3.62)
    for x in (-31.5, -14.8, 4.6, 22.0):
        lamp_post(x, -3.62)
    poles_n = [utility_pole(x, 3.62) for x in (-33.0, -8.3, 7.0, 19.8, 33.8)]
    poles_s = [utility_pole(x, -3.62) for x in (-26.5, -10.0, 11.6, 28.0)]
    for poles in (poles_n, poles_s):
        for a, b in zip(poles, poles[1:]):
            for k in (1, 2, 5, 6):
                wire(a[k], b[k], sag=0.35 + R.uniform(0, 0.15))
    # spans across the street and service drops to the facades
    for a, b in ((poles_n[1], poles_s[1]), (poles_n[3], poles_s[2]), (poles_n[4], poles_s[3])):
        wire(a[0], b[3], sag=0.6)
    for p in poles_n:
        wire(p[7], (p[7][0] + R.uniform(-1.5, 1.5), FP + 0.05, 6.3), sag=0.25, r=0.008)
    for p in poles_s:
        wire(p[0], (p[0][0] + R.uniform(-1.5, 1.5), -FP - 0.05, 6.3), sag=0.25, r=0.008)
    # sandbag blast wall in front of the goldsmith's shuttered window
    sandbag_wall(Frame(11.4, -FP - SV + 0.55, -1, 0), 0.2, 4.8, -0.55, 0.0, FFW, 4)


def street_end_west():
    with GROUP("WAR_Street"):
        _street_end_west()


def _street_end_west():
    """Rubble-free but closed west end: an unhitched bullock cart (牛車水), handcarts, sandbags."""
    x = -34.9
    base = M_at(x - 0.6, 1.2, 0, math.radians(8))
    mbox(base @ M_at(0, 0, 1.0, 0), "M_Timber", (1.6, 3.0, 0.08), TIMBER_RAW)
    for sx in (-0.8, 0.8):
        mbox(base @ M_at(sx, 0, 1.25, 0), "M_Timber", (0.06, 3.0, 0.5), TIMBER_RAW)
    for k in range(6):
        a = math.radians(15 + k * 25)
        mbox(base @ M_at(math.cos(a) * 0.85 * -1 if k > 2 else math.cos(a) * 0.85, 0, 1.5 + math.sin(a) * 0.9, 0, 0, a - math.pi / 2),
             "M_Details", (0.5, 2.6, 0.05), WHITE, uvs={"+z": arect(DET["chick"]), "-z": arect(DET["chick"])})
    for sx in (-0.95, 0.95):
        wheel(base @ M_at(sx, 0.2, 0.9, math.radians(90)), 0.9, 0.1, 12)
    for sx in (-0.4, 0.4):
        tube("M_Timber", base @ Vector((sx, -1.5, 1.0)), base @ Vector((sx * 0.3, -3.4, 0.1)), 0.04, 5, TIMBER_DARK)
    handcart(x, -2.2, math.radians(80), load="full")
    sandbag_wall(Frame(x - 0.4, -6.7, 0, 1), 0.0, 3.2, 0.0, 0.7, 0.0, 5)
    sandbag_wall(Frame(x - 0.4, 3.6, 0, 1), 0.0, 3.1, 0.0, 0.7, FFW, 5)
    collider("COL_Bound_W", (-35.6, -7.0, 0), (-34.6, 7.0, 4.0))


def street_end_east():
    x = 34.9
    with GROUP("PRE_Barricade_E"):
        # British roadblock: timber trestles with barbed wire + sandbags
        for y in (-2.6, 0.0, 2.6):
            b = M_at(x, y, 0, 0)
            for sy in (-1.0, 1.0):
                for sx in (-0.35, 0.35):
                    tube("M_Timber", b @ Vector((0, sy, 1.1)), b @ Vector((sx, sy * 1.05, 0)), 0.04, 4, TIMBER_RAW, smooth=False)
            tube("M_Timber", b @ Vector((0, -1.2, 1.1)), b @ Vector((0, 1.2, 1.1)), 0.05, 5, TIMBER_RAW)
            for k in range(7):
                a0 = b @ Vector((0.1 * math.sin(k), -1.2 + k * 0.4, 0.3 + 0.8 * abs(math.sin(k * 1.7))))
                a1 = b @ Vector((-0.1 * math.sin(k), -1.0 + k * 0.4, 0.35 + 0.8 * abs(math.cos(k * 1.3))))
                tube("M_Metal", a0, a1, 0.008, 3, C(0.3, 0.28, 0.25), smooth=False)
        sandbag_wall(Frame(x + 0.3, -3.5, 0, 1), 0.0, 7.0, 0.0, 0.7, 0.0, 3)
    with GROUP("OCC_Sentry"):
        # Japanese sentry post: small box with a striped barrier across the street end
        sb = M_at(x + 0.2, 4.9, FFW, math.radians(180))
        mbox(sb @ M_at(0, 0, 1.2, 0), "M_Timber", (1.2, 1.2, 2.4), C(0.66, 0.62, 0.52))
        mbox(sb @ M_at(0, -0.61, 1.2, 0), "M_Windows", (0.9, 0.02, 2.0), C(0.2, 0.2, 0.2), uvs={"-v": arect(WIN["open"])})
        mbox(sb @ M_at(0, 0, 2.5, 0), "M_Metal", (1.5, 1.5, 0.12), C(0.3, 0.3, 0.3))
        board(Frame(x - 0.45, 4.3, 0, -1).rot(0), "M_Posters", 0.0, 0.9, 1.4, 1.85, -0.01, 0.02, POSTER["sentry"])
        for y in (-3.0, 3.0):
            box(WORLD, "M_Timber", (x - 0.3, y - 0.3, 0), (x + 0.3, y + 0.3, 1.0), C(0.5, 0.4, 0.3))
        for k in range(8):
            y0 = -3.2 + k * 0.8
            tube("M_Metal", (x, y0, 1.05), (x, y0 + 0.8, 1.05), 0.05, 6, WHITE if k % 2 == 0 else C(0.12, 0.12, 0.12))
    collider("COL_Bound_E", (34.6, -7.0, 0), (35.6, 7.0, 4.0))


# ======================================================================================
# Bomb damage state (N8 at x 8 .. 13.2)
# ======================================================================================
DMG_X0, DMG_W = 8.0, 5.2


def build_damage():
    fr = Frame(DMG_X0, FP, 1, 0)
    W = DMG_W
    wall = PLASTER["sand"]
    scorch = C(0.28, 0.25, 0.22)
    rr = random.Random(12)
    with GROUP("DMG_House"):
        # ground-floor piers survive, shopfront planks smashed
        for (a, b) in ((0.0, 0.7), (W - 0.7, W)):
            box(fr, "M_Plaster", (a, SV, FFW), (b, SV + 0.3, GF - rr.uniform(0.2, 0.9)), mul(wall, 0.8))
        box(fr, "M_Plaster", (0.0, 0.0, FFW), (0.45, 0.45, GF - 0.4), mul(wall, 0.85))
        # charred interior: floor, walls, back wall
        grid_quad(fr, "M_Floor", 0.2, W - 0.2, SV, DEPTH - 0.3, FFW, mul(FLOORS["cement"], 0.45), s=1.2)
        for uu, facing in ((0.02, "+u"), (W - 0.02, "-u")):
            ugrid(fr, "M_Plaster", SV, DEPTH, FFW, 7.5, uu, scorch, s=2.0, cell=1.5, facing=facing)
        # jagged back wall
        n = 8
        for i in range(n):
            a0, a1 = W * i / n, W * (i + 1) / n
            ztop = rr.uniform(3.5, 6.5)
            box(fr, "M_Brick", (a0, DEPTH - 0.3, FFW), (a1, DEPTH, ztop), C(0.7, 0.62, 0.55), s=(0.96, 0.8))
        # jagged remnant of the first-floor facade
        for i in range(n):
            a0, a1 = W * i / n, W * (i + 1) / n
            if 0.3 < (a0 + a1) / 2 / W < 0.65:
                ztop = GF + rr.uniform(0.2, 0.7)
            else:
                ztop = GF + rr.uniform(1.0, 2.6)
            box(fr, "M_Plaster", (a0, 0.0, GF - 0.5), (a1, 0.3, ztop), mul(wall, rr.uniform(0.42, 0.68)),
                cols={"+z": C(0.7, 0.6, 0.5), "+v": scorch})
            box(fr, "M_Brick", (a0 + 0.02, 0.05, ztop - 0.2), (a1 - 0.02, 0.25, ztop + rr.uniform(0.0, 0.25)), C(0.8, 0.7, 0.6), s=(0.96, 0.8))
        # one broken shutter left hanging from the remnant window
        mbox(M_at(DMG_X0 + 1.2, FP - 0.25, GF + 1.1, 0.4, 0.0, math.radians(20)), "M_Windows", (0.55, 0.04, 1.6), SHUTTER["teal"],
             uvs={"-v": arect(WIN["jal_closed"]), "+v": arect(WIN["jal_closed"])})
        # exposed floor joists (some broken, some hanging)
        for k in range(7):
            u = 0.35 + k * (W - 0.7) / 6
            L = rr.uniform(1.5, 6.0)
            if k in (2, 4):
                p0 = fr.w((u, 0.2, GF))
                p1 = fr.w((u + rr.uniform(-0.4, 0.4), 3.0, FFW + 0.5))
                tube("M_Timber", p0, p1, 0.09, 4, C(0.22, 0.16, 0.12), smooth=False)
            else:
                box(fr, "M_Timber", (u - 0.07, max(0.0, SV - L + 3.0), GF - 0.22), (u + 0.07, min(DEPTH, SV + L), GF), C(0.3, 0.22, 0.15))
        # first-floor boards remaining at the back
        box(fr, "M_Timber", (0.1, 7.0, GF), (W - 0.1, DEPTH - 0.3, GF + 0.06), C(0.28, 0.2, 0.14))
        # collapsed roof slab sloping down into the house, tiles still on it
        slab = [(0.1, 3.2, FFW + 1.0), (W - 0.1, 3.0, FFW + 0.8), (W - 0.3, 8.8, 6.0), (0.2, 9.0, 6.6)]
        face(fr, "M_RoofTile", slab, C(0.8, 0.75, 0.7), s=1.2)
        face(fr, "M_Timber", slab[::-1], C(0.2, 0.15, 0.1), s=1.0)
        for k in range(6):
            u = 0.4 + k * 0.9
            tube("M_Timber", fr.w((u, 3.2, FFW + 1.0)), fr.w((u + 0.1, 9.6, 7.0)), 0.06, 4, C(0.25, 0.18, 0.12), smooth=False)
        # rafters still standing against the neighbour's wall at the back
        for k in range(4):
            tube("M_Timber", fr.w((0.3 + k * 1.4, 9.5, 7.2)), fr.w((0.2 + k * 1.4, DEPTH, 8.5)), 0.06, 4, C(0.25, 0.18, 0.12), smooth=False)
        # soot on neighbouring facades
        for (u0, u1) in ((-1.4, -0.02), (W + 0.02, W + 1.6)):
            face(fr, "M_Plaster", [(u0, -0.02, 4.2), (u1, -0.02, 4.2), (u1, -0.02, 8.8), (u0, -0.02, 8.8)], SOOT)
        # rubble heap on the five-foot way spilling into the road, plus chunks and beams
        rubble_heap(DMG_X0 + W / 2, FP + 0.9, W / 2 + 0.6, 2.6, 1.5, 5, n=12)
        rubble_heap(DMG_X0 + W / 2 + 0.3, FP + 5.0, W / 2 - 0.3, 2.4, 1.2, 6, n=8)
        debris_chunks(DMG_X0 + W / 2, FP + 0.6, W / 2 + 0.6, 2.2, 60, 7, zmax=1.2)
        debris_chunks(DMG_X0 + W / 2, 2.9, W / 2, 0.7, 25, 8, zmax=0.2)
        for k in range(4):
            p0 = (DMG_X0 + rr.uniform(0, W), FP + rr.uniform(-1.2, 1.5), rr.uniform(0.2, 1.0))
            p1 = (p0[0] + rr.uniform(-2, 2), p0[1] + rr.uniform(-1.5, 1.5), rr.uniform(0.1, 1.6))
            tube("M_Timber", p0, p1, 0.08, 4, C(0.22, 0.16, 0.12), smooth=False)
        # broken shutters on the rubble
        for k in range(3):
            mbox(M_at(DMG_X0 + 0.8 + k * 1.6, FP + rr.uniform(-0.5, 0.6), 0.6 + rr.uniform(0, 0.4), rr.uniform(0, 3), rr.uniform(-0.5, 0.5), rr.uniform(-0.3, 0.3)),
                 "M_Windows", (0.5, 0.04, 1.4), SHUTTER["teal"], uvs={"-v": arect(WIN["jal_closed"]), "+v": arect(WIN["panel"])})
    with GROUP("DMG_Debris_Signboard"):
        M = M_at(DMG_X0 + 2.4, 2.75, 0.14, math.radians(-8), math.radians(-78), 0)
        mbox(M, "M_Timber", (3.0, 0.66, 0.08), TIMBER_DARK, uvs={"+z": arect(plaque_rect(8))}, mats={"+z": "M_Signs"}, cols={"+z": WHITE})
    with GROUP("DMG_Debris_Lantern"):
        sphere("M_Cloth", (DMG_X0 + 4.6, 2.2, 0.1), 0.22, RED, nu=8, nv=5, sz=0.4)
        cyl(WORLD, "M_Timber", (DMG_X0 + 4.9, 2.1, 0.0), 0.08, 0.05, 6, C(0.2, 0.15, 0.1))
    with GROUP("DMG_Debris_Sandbags"):
        for k in range(7):
            M = M_at(13.5 + rr.uniform(0, 2.2), 2.4 + rr.uniform(-0.8, 2.6), 0.08 if rr.random() < 0.6 else FFW + 0.08, rr.uniform(0, 3), rr.uniform(-0.2, 0.2))
            if M.translation.y > DRAIN_Y0 and M.translation.y < FP:
                M.translation.z = KERB_Z + 0.08
            sandbag(M, size=(0.58, 0.34, 0.12))
        rubble_heap(14.6, 3.0, 0.8, 0.4, 0.08, 9, col=C(0.8, 0.72, 0.55), n=5)   # spilt sand
    # rubble colliders (enabled by the game only in the damaged state)
    collider("COL_DMG_1", (DMG_X0 - 0.4, FP, 0), (DMG_X0 + W + 0.4, FP + SV, 1.6))
    collider("COL_DMG_2", (DMG_X0 - 0.2, 2.3, 0), (DMG_X0 + W + 0.2, FP, 0.9))
    collider("COL_DMG_3", (DMG_X0, FP + SV, 0), (DMG_X0 + W, DEPTH + FP, 4.0))
    marker("DMG_Fire_1", (DMG_X0 + 1.4, FP + 0.4, GF + 0.6), (0, -1))
    marker("DMG_Fire_2", (DMG_X0 + 3.6, 3.2, 0.5), (0, -1))
    marker("DMG_Fire_3", (DMG_X0 + 2.6, FP + 6.0, 1.2), (0, -1))


# ======================================================================================
# Occupation dressing
# ======================================================================================
def build_occupation():
    with GROUP("OCC_Flags"):
        # Hinomaru flags on short poles from upper windows (every other house)
        for i, h in enumerate(NORTH_W + NORTH_E + SOUTH_E + SOUTH_W):
            if i % 2 or getattr(h, "group", None):
                continue
            fr = h.frame
            u = h.W * 0.5
            z = GF + 0.9
            p0 = Vector(fr.w((u, 0.0, z)))
            p1 = Vector(fr.w((u, -1.3, z + 0.9)))
            tube("M_Timber", p0, p1, 0.02, 4, BAMBOO)
            d = (p1 - p0).normalized()
            side = Vector((*fr.dirw(1, 0), 0))
            a = p1 - d * 0.1
            b = p1 - d * 0.95
            q = [tuple(b), tuple(a), tuple(a - Vector((0, 0, 0.6))), tuple(b - Vector((0, 0, 0.6)))]
            uv = arect(POSTER["flag" if i % 4 else "flag2"])
            emit("M_Posters", [q[3], q[2], q[1], q[0]], [uv[0], uv[1], uv[2], uv[3]], WHITE)
            emit("M_Posters", [q[2], q[3], q[0], q[1]], [uv[1], uv[0], uv[3], uv[2]], WHITE)
    with GROUP("OCC_Banner"):
        # "昭南島 SYONAN-TO" banner strung across the street
        x = 4.0
        y0, y1 = -3.4, 3.4
        z1, z0 = 6.6, 5.75
        uv = arect(POSTER["banner"])
        emit("M_Posters", [(x, y1, z0), (x, y0, z0), (x, y0, z1), (x, y1, z1)], uv, WHITE)
        emit("M_Posters", [(x - 0.005, y0, z0), (x - 0.005, y1, z0), (x - 0.005, y1, z1), (x - 0.005, y0, z1)], uv, WHITE)
        wire((x, -FP, 6.8), (x, y0, z1), sag=0.1, r=0.01)
        wire((x, y1, z1), (x, FP, 6.8), sag=0.1, r=0.01)
    with GROUP("OCC_RationNotice"):
        f = Frame(18.8 + 0.6, FP + SV - 0.06, 1, 0)
        board(f, "M_Posters", 0.0, 1.3, 1.1, 1.97, 0.0, 0.05, POSTER["ration"])
        tube("M_Timber", f.w((0.1, 0.02, 0.0 + FFW)), f.w((0.1, 0.02, 2.0)), 0.03, 4, TIMBER_DARK)


def build_kopi_closed():
    """Epilogue: the kopitiam is shuttered; Ah Ma sits on a crate outside (EPI_AhMa)."""
    fr = KOPI.frame
    with GROUP("OCC_KopiClosed"):
        n = 8
        for k in range(n):
            a0 = 0.25 + (KOPI.W - 0.5) * k / n
            a1 = 0.25 + (KOPI.W - 0.5) * (k + 1) / n - 0.012
            box(fr, "M_Timber", (a0, SV - 0.1, FFW), (a1, SV - 0.02, 3.3), jitter(C(0.52, 0.40, 0.30), 0.06), s=1.0)
        box(fr, "M_Timber", (0.2, SV - 0.16, 1.55), (KOPI.W - 0.2, SV - 0.1, 1.67), C(0.28, 0.24, 0.2))   # locking bar
        x, y, _ = fr.w((3.0, 1.95, 0))
        mbox(M_at(x, y, FFW + 0.225, math.radians(3)), "M_Timber", (0.5, 0.4, 0.45), C(0.62, 0.50, 0.36))
    collider("COL_OCC_KopiShutters", fr.w((0.2, SV - 0.16, 0)), fr.w((KOPI.W - 0.2, SV, 3.3)), {"state": "occ"})


# ======================================================================================
# Present day ("Then & Now" intro): NOW_* dressing, hidden by default
# ======================================================================================
NOW_RECT = {"sign%d" % i: ((i % 2) * 512 + 3, (i // 2) * 128 + 3, (i % 2) * 512 + 509, (i // 2) * 128 + 125) for i in range(6)}
NOW_RECT.update({"umbrella": (2, 386, 254, 638), "ac": (258, 386, 510, 638), "aboard": (514, 386, 766, 638),
                 "plaque": (770, 386, 1022, 638), "mural": (2, 642, 766, 1022),
                 "ped": (770, 642, 894, 766), "noentry": (898, 642, 1022, 766), "bus": (770, 770, 1022, 894),
                 "street": (770, 898, 1022, 1022)})


def now_cafe_set(x, y, z, col=C(0.14, 0.22, 0.2), rot=0.0):
    cyl(WORLD, "M_Metal", (x, y, z), 0.2, 0.03, 8, col)
    cyl(WORLD, "M_Metal", (x, y, z), 0.03, 0.72, 6, col)
    cyl(WORLD, "M_Metal", (x, y, z + 0.72), 0.3, 0.03, 12, C(0.86, 0.85, 0.82))
    for sgn in (-1, 1):
        cx, cy = x + math.cos(rot) * 0.55 * sgn, y + math.sin(rot) * 0.55 * sgn
        M = M_at(cx, cy, z, rot + (math.pi / 2 if sgn > 0 else -math.pi / 2))
        mbox(M @ M_at(0, 0, 0.45, 0), "M_Metal", (0.4, 0.4, 0.03), col)
        mbox(M @ M_at(0, 0.19, 0.68, 0), "M_Metal", (0.4, 0.03, 0.42), col)
        for px, py in ((-0.17, -0.17), (0.17, -0.17), (-0.17, 0.17), (0.17, 0.17)):
            mbox(M @ M_at(px, py, 0.225, 0), "M_Metal", (0.025, 0.025, 0.45), col)
    collider("COL_NOW_Cafe", (x - 0.8, y - 0.35, 0), (x + 0.8, y + 0.35, 1.0), unique=False)


def now_umbrella(x, y, r=1.25):
    tube("M_Metal", (x, y, 0.0), (x, y, 2.45), 0.025, 6, C(0.85, 0.85, 0.82))
    cyl(WORLD, "M_Metal", (x, y, 0.0), 0.28, 0.08, 10, C(0.2, 0.2, 0.2))
    n = 8
    x0, y0, x1, y1 = NOW_RECT["umbrella"]
    for i in range(n):
        a0, a1 = math.tau * i / n, math.tau * (i + 1) / n
        p0 = (x + math.cos(a0) * r, y + math.sin(a0) * r, 2.05)
        p1 = (x + math.cos(a1) * r, y + math.sin(a1) * r, 2.05)
        top = (x, y, 2.5)
        uv = [(x0 / 1024, 1 - y1 / 1024), (x1 / 1024, 1 - y1 / 1024), ((x0 + x1) / 2048, 1 - y0 / 1024)]
        emit("M_NowSigns", [p0, p1, top], uv, WHITE)
        emit("M_NowSigns", [top, p1, p0], uv[::-1], mul(WHITE, 0.8))
    collider("COL_NOW_Umbrella", (x - 0.3, y - 0.3, 0), (x + 0.3, y + 0.3, 2.4), unique=False)


def now_planter(x, y, z, w=0.9, d=0.45, rz=0.0, col=C(0.32, 0.33, 0.33)):
    M = M_at(x, y, z + 0.25, rz)
    mbox(M, "M_Plaster", (w, d, 0.5), col, s=1.0)
    rr = random.Random(int(x * 100 + y * 10))
    for k in range(3):
        o = M @ Vector((rr.uniform(-w / 3, w / 3), rr.uniform(-0.05, 0.05), 0.35))
        sphere("M_Plaster", tuple(o), rr.uniform(0.22, 0.32), jitter(C(0.30, 0.45, 0.24), 0.15), nu=7, nv=5, sz=0.9)
    collider("COL_NOW_Planter", (x - w / 2 - 0.05, y - w / 2 - 0.05, 0) if abs(math.sin(rz)) > 0.7 else (x - w / 2, y - d / 2, 0),
             (x + w / 2 + 0.05, y + w / 2 + 0.05, 1.0) if abs(math.sin(rz)) > 0.7 else (x + w / 2, y + d / 2, 1.0), unique=False)


def now_bollard(x, y, z=0.0):
    cyl(WORLD, "M_Metal", (x, y, z), 0.1, 0.85, 8, C(0.12, 0.12, 0.13))
    sphere("M_Metal", (x, y, z + 0.85), 0.1, C(0.12, 0.12, 0.13), nu=8, nv=4, sz=0.6)
    collider("COL_NOW_Bollard", (x - 0.12, y - 0.12, 0), (x + 0.12, y + 0.12, 0.95), unique=False)


def now_lamp(x, y, side=1):
    """Slim modern street lamp: tapered pole with an LED head on a short arm over the road."""
    z = KERB_Z
    cyl(WORLD, "M_Metal", (x, y, z), 0.13, 0.35, 8, C(0.30, 0.31, 0.32), r_top=0.09)
    cyl(WORLD, "M_Metal", (x, y, z + 0.35), 0.08, 6.1, 8, C(0.36, 0.37, 0.38), r_top=0.05)
    tip = (x, y - side * 1.1, z + 6.55)
    tube("M_Metal", (x, y, z + 6.4), tip, 0.04, 5, C(0.36, 0.37, 0.38))
    mbox(M_at(tip[0], tip[1], tip[2] - 0.02, 0), "M_Metal", (0.34, 0.62, 0.08), C(0.3, 0.3, 0.3))
    mbox(M_at(tip[0], tip[1], tip[2] - 0.065, 0), "M_Emissive", (0.28, 0.52, 0.01), C(1.0, 0.97, 0.9))
    collider("COL_NOW_Lamp", (x - 0.15, y - 0.15, 0), (x + 0.15, y + 0.15, 3.0), unique=False)


def now_car(x, y, rz, col):
    """Generic low-poly modern hatchback (no brand)."""
    base = M_at(x, y, 0, rz)
    mbox(base @ M_at(0, 0, 0.62, 0), "M_Metal", (4.3, 1.76, 0.62), col)
    cab = [(-1.35, -0.8, 0.93), (1.05, -0.8, 0.93), (1.05, 0.8, 0.93), (-1.35, 0.8, 0.93),
           (-0.95, -0.7, 1.45), (0.55, -0.7, 1.45), (0.55, 0.7, 1.45), (-0.95, 0.7, 1.45)]
    P = [tuple(base @ Vector(v)) for v in cab]
    glass = C(0.10, 0.12, 0.14)
    for (i, j, k, l, c) in ((0, 1, 5, 4, glass), (2, 3, 7, 6, glass), (1, 2, 6, 5, glass), (3, 0, 4, 7, glass), (4, 5, 6, 7, col)):
        emit("M_Metal", [P[i], P[j], P[k], P[l]], [(0, 0)] * 4, c)
    R3 = base.to_3x3()
    for px in (-1.35, 1.35):
        for py in (-0.82, 0.82):
            c = base @ Vector((px, py, 0.33))
            tube("M_Metal", tuple(c - R3 @ Vector((0, 0.11, 0))), tuple(c + R3 @ Vector((0, 0.11, 0))), 0.32, 10,
                 C(0.06, 0.06, 0.06), caps=True)
    for py in (-0.6, 0.6):
        mbox(base @ M_at(2.155, py, 0.72, 0), "M_Emissive", (0.02, 0.3, 0.1), C(1.0, 0.95, 0.85))
        mbox(base @ M_at(-2.155, py, 0.75, 0), "M_Metal", (0.02, 0.3, 0.1), C(0.7, 0.05, 0.05))
    collider("COL_NOW_Car", (x - 2.2, y - 0.95, 0), (x + 2.2, y + 0.95, 1.5), unique=False)


def now_sign_pole(x, y, rect, w, h, rz=0.0, top=2.6):
    tube("M_Metal", (x, y, 0.0), (x, y, top + h / 2), 0.035, 6, C(0.55, 0.56, 0.57))
    f = Frame(x - math.cos(rz) * w / 2, y - math.sin(rz) * w / 2, math.cos(rz), math.sin(rz))
    board(f, "M_NowSigns", 0.0, w, top - h / 2, top + h / 2, -0.06, 0.02, rect, edge_col=C(0.3, 0.3, 0.3))
    collider("COL_NOW_SignPole", (x - 0.1, y - 0.1, 0), (x + 0.1, y + 0.1, 2.2), unique=False)


def now_bin(x, y, z):
    cyl(WORLD, "M_Metal", (x, y, z), 0.28, 0.95, 10, C(0.16, 0.34, 0.24))
    cyl(WORLD, "M_Metal", (x, y, z + 0.95), 0.3, 0.08, 10, C(0.2, 0.2, 0.2))
    collider("COL_NOW_Bin", (x - 0.32, y - 0.32, 0), (x + 0.32, y + 0.32, 1.1), unique=False)


def now_scooter(x, y, z, rz):
    b = M_at(x, y, z, rz)
    mbox(b @ M_at(0, 0, 0.1, 0), "M_Metal", (0.9, 0.16, 0.05), C(0.15, 0.15, 0.15))
    tube("M_Metal", tuple(b @ Vector((0.42, 0, 0.1))), tuple(b @ Vector((0.5, 0, 1.05))), 0.02, 5, C(0.2, 0.2, 0.2))
    tube("M_Metal", tuple(b @ Vector((0.5, -0.22, 1.05))), tuple(b @ Vector((0.5, 0.22, 1.05))), 0.015, 4, C(0.1, 0.1, 0.1))
    R3 = b.to_3x3()
    for px in (-0.42, 0.44):
        c = b @ Vector((px, 0, 0.1))
        tube("M_Metal", tuple(c - R3 @ Vector((0, 0.03, 0))), tuple(c + R3 @ Vector((0, 0.03, 0))), 0.1, 8, C(0.05, 0.05, 0.05), caps=True)


def now_tree(x, y, z, h=3.8, r=1.1):
    """Small street tree (frangipani-like) in a square granite planter."""
    mbox(M_at(x, y, z + 0.3, 0), "M_Plaster", (1.2, 1.2, 0.6), C(0.55, 0.54, 0.52))
    cyl(WORLD, "M_Plaster", (x, y, z + 0.6), 0.12, h - 1.2, 7, C(0.40, 0.34, 0.28), r_top=0.08)
    rr = random.Random(int(x * 13 + y * 7))
    for k in range(5):
        a = k * 1.3
        sphere("M_Plaster", (x + math.cos(a) * r * 0.55, y + math.sin(a) * r * 0.55, z + h - 0.4 + rr.uniform(-0.2, 0.3)),
               r * rr.uniform(0.55, 0.75), jitter(C(0.30, 0.46, 0.24), 0.12), nu=7, nv=5, sz=0.8)
    collider("COL_NOW_Tree", (x - 0.62, y - 0.62, 0), (x + 0.62, y + 0.62, 1.0), unique=False)


def now_ac_unit(p, normal, up=(0, 0, 1)):
    """Air-con condenser on a bracket, hung on a side/rear wall; normal points out of the wall."""
    n = Vector((normal[0], normal[1], 0)).normalized()
    ang = math.atan2(n.y, n.x) + math.pi / 2
    c = Vector(p) + n * 0.2
    M = M_at(c.x, c.y, c.z, ang)
    mbox(M, "M_Metal", (0.85, 0.32, 0.6), C(0.82, 0.82, 0.8), uvs=None, skip=("-v",))
    x0, y0, x1, y1 = NOW_RECT["ac"]
    q = [M @ Vector(v) for v in ((-0.425, -0.161, -0.3), (0.425, -0.161, -0.3), (0.425, -0.161, 0.3), (-0.425, -0.161, 0.3))]
    emit("M_NowSigns", [tuple(v) for v in q], arect((x0, y0, x1, y1)), WHITE)
    mbox(M @ M_at(0, 0.02, -0.33, 0), "M_Metal", (0.9, 0.36, 0.04), C(0.3, 0.3, 0.3))
    tube("M_Metal", tuple(M @ Vector((0.3, 0.1, -0.3))), tuple(M @ Vector((0.3, 0.14, -1.6))), 0.015, 4, C(0.9, 0.9, 0.88))


def now_sign(h, idx):
    """Modern signboard fixed in front of the old plaque (generic names, no real brands)."""
    fr = h.frame
    pw = min(h.W - 0.9, 3.4)
    ph = pw / 4.0
    z0 = GF + 0.18
    board(fr, "M_NowSigns", h.W / 2 - pw / 2, h.W / 2 + pw / 2, z0, z0 + ph, -0.34, 0.05, arect_inset(NOW_RECT["sign%d" % idx], 0))


THEN_NOW_CAM = (-30.0, 4.1)   # NOW props are kept > 3 m from it and out of the central third of its view


def build_now():
    """Present-day Telok Ayer (NOW_* groups; hidden in 1942)."""
    build_now_skyline()
    build_now_road()
    build_now_shopfronts()
    with GROUP("NOW_Street"):
        # cafe sets on the five-foot ways (against the shopfronts; walkway stays clear)
        for (x, side) in ((-23.6, 1), (-11.2, 1), (5.2, 1), (27.2, 1), (-20.0, -1), (-3.2, -1), (13.8, -1), (33.0, -1)):
            now_cafe_set(x, side * (FP + SV - 0.55), FFW)
        # outdoor seating with umbrellas in the pocket park (open air)
        for (x, y) in ((19.0, -6.2), (24.6, -6.4)):
            now_umbrella(x, y)
            now_cafe_set(x, y, 0.0, col=C(0.3, 0.2, 0.14))
        # planters: north ones only beyond the THEN_NOW view's near field; south row; street ends
        for x in (11.0, 29.0):
            now_planter(x, FP + 0.35, FFW)
        for x in (-18.0, -1.0, 16.0, 34.0):
            now_planter(x, -FP - 0.35, FFW)
        for xe in (-34.9, 34.9):
            for y in (-2.6, -0.9, 0.9, 2.6):
                now_planter(xe, y, 0.0, w=1.3, d=0.6, rz=math.pi / 2)
            for y in (-5.4, 5.4):
                now_bollard(xe, y, FFW)
        for x in (-1.8, 0.0, 1.8):
            now_bollard(x, 4.3)
        for x in (18.5, 21.0, 23.5, 25.8):
            now_bollard(x, -4.3)
        # slim modern lamps (the gas lamps are WAR_)
        for x in (-31.2, 1.8, 14.8, 31.0):
            now_lamp(x, 3.62, side=1)
        for x in (-31.5, -14.8, 4.6, 22.0):
            now_lamp(x, -3.62, side=-1)
        # traffic / pedestrian / bus-stop / street-name signs (south kerb, out of the photo's centre)
        now_sign_pole(2.2, -3.66, NOW_RECT["ped"], 0.6, 0.6, rz=math.pi)
        now_sign_pole(-2.2, -3.66, NOW_RECT["ped"], 0.6, 0.6, rz=math.pi)
        now_sign_pole(-27.0, -3.66, NOW_RECT["bus"], 1.2, 0.6, rz=math.pi, top=2.4)
        now_sign_pole(33.8, 3.66, NOW_RECT["noentry"], 0.6, 0.6, rz=0.0)
        now_sign_pole(-34.4, -3.8, NOW_RECT["street"], 1.1, 0.55, rz=math.pi, top=2.7)
        # parked modern cars (south kerb bays)
        for (x, col) in ((-22.0, C(0.92, 0.92, 0.9)), (-14.6, C(0.55, 0.57, 0.6)), (-7.2, C(0.12, 0.13, 0.15))):
            now_car(x, -2.45, 0.0, col)
        # bins, e-scooters, bicycles
        for (x, y) in ((-16.5, -4.35), (8.0, 4.35), (26.0, -4.35)):
            now_bin(x, y, FFW)
        for k in range(3):
            now_scooter(-3.8 + k * 0.5, -6.3, FFW, math.radians(90))
        collider("COL_NOW_Scooters", (-4.1, -6.7, 0), (-2.5, -5.8, 1.1))
        for k in range(3):
            bicycle(3.4 + k * 0.75, 6.25, FFW, math.radians(90), lean=0.0)
        tube("M_Metal", (3.1, 6.6, FFW + 0.45), (5.2, 6.6, FFW + 0.45), 0.02, 5, C(0.6, 0.6, 0.6))
        collider("COL_NOW_Bikes", (3.0, 5.7, 0), (5.4, 6.7, 1.0))
        # street trees in planters at the south kerb
        for x in (4.0, 26.0):
            now_tree(x, -3.0, 0.0)
        # air-con condensers on exposed side walls (not on conserved front facades)
        for z in (5.2, 8.4):
            now_ac_unit((-36.0, 10.5, z), (-1, 0))
            now_ac_unit((-2.5, 10.8, z - 0.6), (1, 0))
            now_ac_unit((2.5, 9.6, z), (-1, 0))
            now_ac_unit((17.0, -12.5, z - 0.4), (1, 0))
            now_ac_unit((27.0, -13.2, z), (-1, 0))
        now_ac_unit((36.0, 9.8, 6.0), (1, 0))
        # modern signboards in front of some old plaques
        for h, idx in ((NORTH_W[1], 0), (NORTH_W[4], 1), (NORTH_E[0], 2), (NORTH_E[4], 3), (SOUTH_W[3], 4), (SOUTH_W[1], 5)):
            now_sign(h, idx)
        # pocket park on the old shelter lot: benches, trees, heritage marker, mural
        for (x, y) in ((19.2, -10.4), (24.2, -10.4)):
            mbox(M_at(x, y, 0.42, 0), "M_Metal", (1.6, 0.45, 0.05), C(0.45, 0.32, 0.22))
            mbox(M_at(x, y + 0.2, 0.7, 0), "M_Metal", (1.6, 0.04, 0.4), C(0.45, 0.32, 0.22))
            for px in (-0.7, 0.7):
                mbox(M_at(x + px, y, 0.21, 0), "M_Metal", (0.05, 0.4, 0.42), C(0.15, 0.15, 0.15))
            collider("COL_NOW_Bench", (x - 0.85, y - 0.3, 0), (x + 0.85, y + 0.3, 0.9), unique=False)
        for (x, y) in ((18.8, -13.8), (25.2, -13.2)):
            cyl(WORLD, "M_Plaster", (x, y, 0), 0.18, 3.0, 8, C(0.36, 0.28, 0.2), r_top=0.12)
            for k in range(4):
                sphere("M_Plaster", (x + math.cos(k * 1.6) * 0.8, y + math.sin(k * 1.6) * 0.8, 3.5 + (k % 2) * 0.5), 1.2,
                       jitter(C(0.28, 0.42, 0.22), 0.12), nu=8, nv=6, sz=0.8)
            collider("COL_NOW_Tree", (x - 0.25, y - 0.25, 0), (x + 0.25, y + 0.25, 3.0), unique=False)
        tube("M_Metal", (21.8, -8.6, 0.0), (21.8, -8.6, 1.1), 0.04, 6, C(0.2, 0.2, 0.2))
        board(Frame(21.8 + 0.45, -8.57, -1, 0), "M_NowSigns", 0.0, 0.9, 1.1, 1.55, 0.0, 0.03, NOW_RECT["plaque"], edge_col=C(0.2, 0.2, 0.2))
        collider("COL_NOW_Plaque", (21.3, -8.8, 0), (22.3, -8.4, 1.6))
        atlas_quad(Frame(23.6, -16.99, -1, 0), "M_NowSigns", 0.0, 7.6, 2.5, 6.3, 0.0, NOW_RECT["mural"], WHITE)
    with GROUP("NOW_Lights"):
        # festoon string lights zig-zagging across the street (start 10 m ahead of THEN_NOW_Camera)
        for x in (-20.0, -8.0, 4.0, 16.0):
            a = Vector((x, FP + 0.02, 5.9))
            b = Vector((x + 6.0, -FP - 0.02, 5.9))
            pts = catenary(a, b, 0.55, 16)
            for p0, p1 in zip(pts, pts[1:]):
                tube("M_Metal", p0, p1, 0.008, 3, C(0.1, 0.1, 0.1), smooth=False)
            for p in pts[1:-1]:
                sphere("M_Emissive", tuple(p - Vector((0, 0, 0.08))), 0.045, C(1.0, 0.85, 0.55), nu=5, nv=3)


# ---- present-day CBD skyline (Telok Ayer backs onto Tanjong Pagar / Raffles Place) ----
TOWERS = [
    # (x, y, w, d, h, kind)
    (135.0, -55.0, 24.0, 22.0, 290.0, "slim"),     # very tall slim tower
    (95.0, 32.0, 34.0, 30.0, 205.0, "setback"),
    (70.0, -78.0, 40.0, 28.0, 165.0, "flat"),
    (165.0, 22.0, 30.0, 30.0, 235.0, "crown"),
    (-18.0, -98.0, 38.0, 30.0, 150.0, "setback"),
    (32.0, -112.0, 30.0, 26.0, 190.0, "slim"),
    (-82.0, -72.0, 32.0, 32.0, 128.0, "flat"),
    (62.0, 98.0, 28.0, 28.0, 172.0, "crown"),
    (-62.0, 112.0, 30.0, 30.0, 118.0, "flat"),
    (205.0, -22.0, 40.0, 40.0, 262.0, "setback"),
    (118.0, -112.0, 34.0, 30.0, 210.0, "flat"),
]


def build_now_skyline():
    with GROUP("NOW_Skyline"):
        rr = random.Random(2026)
        for (x, y, w, d, h, kind) in TOWERS:
            ang = rr.uniform(-0.15, 0.15)
            podium = 16.0
            mbox(M_at(x, y, podium / 2, ang), "M_Plaster", (w + 10, d + 10, podium), C(0.62, 0.62, 0.62), s=4.0)
            segs = [(0.0, h * 0.62, 1.0), (h * 0.62, h * 0.85, 0.82), (h * 0.85, h, 0.64)] if kind == "setback" else [(0.0, h, 1.0)]
            for (z0, z1, k) in segs:
                M = M_at(x, y, podium + (z0 + z1) / 2, ang)
                mbox(M, "M_Glass", (w * k, d * k, z1 - z0), C(0.86, 0.90, 0.96), s=(12.0, 16.0))
                for f in range(int((z1 - z0) / 4)):
                    if rr.random() < 0.13:
                        zz = podium + z0 + f * 4 + 1.6
                        for side in (-1, 1):
                            mbox(M_at(x, y, zz, ang) @ M_at(0, side * (d * k / 2 + 0.06), 0, 0), "M_Emissive",
                                 (w * k * rr.uniform(0.3, 0.9), 0.02, 1.4), C(1.0, 0.96, 0.86))
            top = podium + h
            if kind == "slim":
                prof = [(-d / 2, 0.0), (d / 2, 0.0), (0.0, 22.0)]
                prism_x(Frame(x - w / 2, y - 0.0, 1, 0), "M_Glass", 0.0, w, [(v, top + z) for (v, z) in prof],
                        C(0.8, 0.86, 0.94), s=(12.0, 16.0))
            elif kind == "crown":
                mbox(M_at(x, y, top + 6, ang), "M_Plaster", (w * 0.7, d * 0.7, 12.0), C(0.7, 0.72, 0.74), s=4.0)
                cyl(WORLD, "M_Plaster", (x, y, top + 12), 0.6, 20.0, 6, C(0.75, 0.75, 0.75), r_top=0.1)
            else:
                mbox(M_at(x, y, top + 2.5, ang), "M_Plaster", (w * 0.5, d * 0.5, 5.0), C(0.66, 0.66, 0.66), s=4.0)


def build_now_road():
    """Modern asphalt, lane markings, zebra crossing, parking bays, clean five-foot-way tiles."""
    with GROUP("NOW_Road"):
        ZR = 0.012        # overlay above the 1942 road (>= 5 mm, avoids z-fighting at near 0.12)
        ZM = 0.024        # paint markings
        dark = C(0.24, 0.24, 0.25)
        grid_quad(WORLD, "M_Road", X_MIN, X_MAX, -ROAD_HW, ROAD_HW, ZR, dark, s=4.0, cell=1.0)
        grid_quad(WORLD, "M_Road", X_MAX, 44.6, -46, 46, ZR, dark, s=4.0, cell=2.0)
        grid_quad(WORLD, "M_Road", -44.6, X_MIN, -46, 46, ZR, dark, s=4.0, cell=2.0)
        white, yellow = C(0.95, 0.95, 0.92), C(0.95, 0.76, 0.16)

        def paint(x0, x1, y0, y1, col):
            face(WORLD, "M_Plaster", [(x0, y0, ZM), (x1, y0, ZM), (x1, y1, ZM), (x0, y1, ZM)], col, s=2.0)
        x = -34.0
        while x < 34.0:                         # dashed centre line (not through the crossing)
            if not (-4.5 < x < 3.0):
                paint(x, x + 3.0, -0.06, 0.06, white)
            x += 6.0
        for yy in (3.22, 3.36):                 # double yellow lines along the north kerb
            paint(-34.5, -3.0, yy - 0.05, yy + 0.05, yellow)
            paint(3.0, 34.5, yy - 0.05, yy + 0.05, yellow)
        yb = -3.3
        while yb < 3.3:                         # zebra crossing at the lane mouth
            paint(-1.6, 1.6, yb, yb + 0.5, white)
            yb += 1.0
        for (xa, xb) in ((-13.0, -2.4), (2.4, 13.0)):     # white zig-zags on the approaches
            for yline in (-0.3, 0.3, 3.0):
                n = int((xb - xa) / 1.0)
                for k in range(n):
                    x0 = xa + k * 1.0
                    ya = yline + (0.18 if k % 2 else -0.18)
                    yb2 = yline + (-0.18 if k % 2 else 0.18)
                    p = [(x0, ya - 0.05, ZM), (x0 + 1.0, yb2 - 0.05, ZM), (x0 + 1.0, yb2 + 0.05, ZM), (x0, ya + 0.05, ZM)]
                    face(WORLD, "M_Plaster", p if newell(p)[2] > 0 else p[::-1], white, s=2.0)
        for xb in (-25.8, -18.4, -11.0, -3.6):  # parking bays, south side
            paint(xb - 0.05, xb + 0.05, -3.5, -1.3, white)
        paint(-25.8, -3.6, -1.35, -1.25, white)
        paint(-2.45, -2.15, -3.4, 0.0, white)   # stop lines at the crossing
        paint(2.15, 2.45, 0.0, 3.4, white)
        for (xa, xb, side) in ((X_MIN, -2.5, 1), (2.5, X_MAX, 1), (X_MIN, 17.0, -1), (27.0, X_MAX, -1)):
            y0, y1 = (FP, FP + SV) if side > 0 else (-FP - SV, -FP)
            grid_quad(WORLD, "M_Floor", xa, xb, y0, y1, FFW + 0.012, C(0.86, 0.84, 0.80), s=1.2, cell=2.0)


def build_now_shopfronts():
    """Glass shopfronts with warm interiors in front of the old ground floors; some upper
    windows opened (shutters folded back, lit rooms)."""
    rr = random.Random(77)
    cells = [(i % 2 * 512 + 6, i // 2 * 384 + 6, i % 2 * 512 + 506, i // 2 * 384 + 378) for i in range(4)]
    wcells = [(i * 256 + 4, 772, i * 256 + 252, 1020) for i in range(4)]
    with GROUP("NOW_Shopfronts"):
        for i, h in enumerate(NORTH_W + NORTH_E + SOUTH_E + SOUTH_W):
            fr = h.frame
            atlas_quad(fr, "M_NowShop", 0.5, h.W - 0.5, FFW, 3.18, SV - 0.03, cells[(i * 3) % 4], WHITE)
            for (hole, fan, k) in getattr(h, "win_list", []):
                if rr.random() < 0.55:
                    top = fan[3] if fan else hole[3]
                    atlas_quad(fr, "M_NowShop", hole[0], hole[2], hole[1], top, 0.19, wcells[rr.randrange(4)], WHITE)


# ======================================================================================
# Backdrops: cross-street rows, back rows, landmarks, far skyline
# ======================================================================================
def random_house(rr, W, lite=True):
    style = rr.choice(["early", "trans1", "late", "trans2", "deco", "early", "trans1"])
    st = rr.choice([2, 2, 3, 3]) if style != "early" else 2
    wins = [rr.choice([JC, JC, JO, PN, FT]) for _ in range(6)]
    ground = rr.choice(["planks", "door", "pintu", "planks"])
    h = H(W, st, style, rr.choice(list(PLASTER.keys())), rr.choice(list(SHUTTER.keys())), wins, ground,
          rr.choice(list(FLOORS.keys())), plaque=rr.choice([None, None, rr.randrange(12)]),
          laundry=rr.random() < 0.3, jack=rr.random() < 0.3, date=rr.choice([1936, 1938]))
    return h


def backdrop_row(x0, y0, ux, uy, length, seed, first_side_windows=False):
    rr = random.Random(seed)
    u = 0.0
    hs = []
    while u < length - 3.5:
        W = min(rr.uniform(4.6, 6.4), length - u)
        if length - u - W < 4.0:
            W = length - u
        h = random_house(rr, W)
        fr = Frame(x0 + ux * u, y0 + uy * u, ux, uy)
        h.frame = fr
        hs.append(h)
        u += W
    for i, h in enumerate(hs):
        build_house(h.frame, h, sides=(house_side_exposed(hs, i, -1), house_side_exposed(hs, i, 1)))
        build_columns(h.frame, [0.0 + (COL_W / 2 if i == 0 else 0)] + ([h.W - COL_W / 2] if i == len(hs) - 1 else []), h, False)
    return hs


def back_blocks(y_face, sign, xs, seed, rear_windows=True):
    """Rear walls & roofs of the next streets' houses (visible above/between our rows)."""
    rr = random.Random(seed)
    for (xa, xb) in xs:
        x = xa
        while x < xb - 0.5:
            W = min(rr.uniform(4.5, 6.5), xb - x)
            ht = rr.choice([7.2, 7.6, 10.6, 11.0])
            col = jitter(PLASTER[rr.choice(list(PLASTER.keys()))], 0.05)
            fr = Frame(x, y_face, 1, 0) if sign > 0 else Frame(x + W, y_face, -1, 0)
            # fr faces toward our street: front plane v=0 at y_face, depth into the block
            holes = []
            if rear_windows:
                for k in range(2 if ht < 9 else 3):
                    zf = 0.9 + k * 3.4
                    holes.append((W * 0.5 - 0.4, zf, W * 0.5 + 0.4, zf + 1.3))
            wall_with_holes(fr, "M_Plaster", 0, W, 0, ht, holes, 0.0, col, s=2.0, maxcell=2.5)
            for hh in holes:
                recess(fr, hh, 0.0, 0.12, col, "M_Windows", SHUTTER[rr.choice(list(SHUTTER.keys()))], back_uv=arect(WIN[rr.choice([JC, JO, PN])]))
            hh = House(W=W, storeys=2 if ht < 9 else 3, style="early", wall=col, shutter=SHUTTER["brown"], pitch=25,
                       roofcol=jitter(C(0.95, 0.92, 0.9), 0.08), jack=rr.random() < 0.25, uvoff=rr.random(), date=1936)
            # simple mass + roof (reuse roof builder with eave kind)
            ugrid(fr, "M_Plaster", 0, DEPTH, 0, ht, 0.0, mul(col, 0.9), s=2.0, cell=4.0, facing="-u")
            ugrid(fr, "M_Plaster", 0, DEPTH, 0, ht, W, mul(col, 0.9), s=2.0, cell=4.0, facing="+u")
            roof_simple(fr, W, ht, hh)
            x += W


def roof_simple(fr, W, top, h):
    pitch = math.radians(h.pitch)
    ve, ze = -0.4, top
    vr = DEPTH / 2
    zr = ze + (vr - ve) * math.tan(pitch)
    vb = DEPTH + 0.4
    face(fr, "M_RoofTile", [(-0.05, ve, ze), (W + 0.05, ve, ze), (W + 0.05, vr, zr), (-0.05, vr, zr)], h.roofcol,
         uv=[(0, 0), (W / 1.2, 0), (W / 1.2, -(vr - ve) / 1.1), (0, -(vr - ve) / 1.1)])
    face(fr, "M_RoofTile", [(W + 0.05, vb, ze), (-0.05, vb, ze), (-0.05, vr, zr), (W + 0.05, vr, zr)], mul(h.roofcol, 0.9),
         uv=[(0, 0), (W / 1.2, 0), (W / 1.2, (vb - vr) / 1.1), (0, (vb - vr) / 1.1)])
    face(fr, "M_Timber", [(-0.05, vb, ze), (W + 0.05, vb, ze), (W + 0.05, ve, ze), (-0.05, ve, ze)], TIMBER_DARK)
    for uu, sgn in ((-0.05, -1), (W + 0.05, 1)):
        tri = [(uu, ve, ze), (uu, vr, zr), (uu, vb, ze)]
        face(fr, "M_Plaster", tri if sgn < 0 else tri[::-1], mul(h.wall, 0.85), s=2.0)
    if h.jack:
        box(fr, "M_Timber", (W * 0.3, vr - 0.8, zr - 0.3), (W * 0.7, vr + 0.8, zr + 0.4), TIMBER_DARK)


def gopuram():
    """Sri Mariamman Temple gopuram (1925, six tiers), simplified silhouette facing west down our street."""
    x0 = 45.0
    fr = Frame(x0, 5.5, 0, -1)     # u along -y, v = +x (into the temple)
    W, Dp = 11.0, 6.5
    cream = C(0.92, 0.86, 0.72)
    ochre = C(0.86, 0.72, 0.50)
    # plinth with the entrance
    door = (W / 2 - 1.2, 0.0, W / 2 + 1.2, 4.3)
    wall_with_holes(fr, "M_Plaster", 0, W, 0, 5.2, [door], 0.0, cream, s=2.0)
    recess(fr, door, 0.0, 1.2, mul(cream, 0.8), "M_Windows", C(0.5, 0.35, 0.25), back_uv=arect(WIN["door"]), sill=False)
    box(fr, "M_Plaster", (0, 0.01, 0), (W, Dp, 5.2), cream, skip=("-v", "-z"))
    box(fr, "M_Plaster", (-0.2, -0.25, 5.2), (W + 0.2, Dp + 0.25, 5.55), ochre)
    zc = 5.55
    pal = [C(0.80, 0.84, 0.86), C(0.90, 0.80, 0.76), C(0.82, 0.86, 0.78), C(0.92, 0.86, 0.70), C(0.92, 0.90, 0.86)]
    tw = []
    for t in range(6):
        w = W * (0.88 - 0.085 * t)
        d = Dp * (0.9 - 0.06 * t)
        u0 = (W - w) / 2
        v0 = (Dp - d) / 2
        th = 1.6 - 0.07 * t
        # tapered tier: slightly battered walls (top narrower than bottom)
        w2, d2 = w - 0.5, d - 0.3
        pts_b = [(u0, v0), (u0 + w, v0), (u0 + w, v0 + d), (u0, v0 + d)]
        pts_t = [(u0 + 0.25, v0 + 0.15), (u0 + w - 0.25, v0 + 0.15), (u0 + w - 0.25, v0 + d - 0.15), (u0 + 0.25, v0 + d - 0.15)]
        for i in range(4):
            j = (i + 1) % 4
            face(fr, "M_Plaster", [(*pts_b[i], zc), (*pts_b[j], zc), (*pts_t[j], zc + th), (*pts_t[i], zc + th)][::-1], jitter(cream, 0.03), s=2.0)
        box(fr, "M_Plaster", (u0 + 0.05, v0 - 0.1, zc + th - 0.16), (u0 + w - 0.05, v0 + d + 0.1, zc + th), ochre)
        # sculpted figures / niches along front & back (sparser, faded: pre-1960s restoration)
        nfig = max(3, int(w / 0.75))
        for i in range(nfig):
            cu = u0 + 0.35 + (w - 0.7) * (i + 0.5) / nfig
            for vv, sgn in ((v0 + 0.1, -1), (v0 + d - 0.1, 1)):
                c = pal[(i * 3 + t) % len(pal)]
                box(fr, "M_Plaster", (cu - 0.13, vv - 0.18 if sgn < 0 else vv, zc + 0.2), (cu + 0.13, vv if sgn < 0 else vv + 0.18, zc + th - 0.45), c)
                with DETAIL():
                    sphere("M_Plaster", fr.w((cu, vv + sgn * 0.09, zc + th - 0.36)), 0.11, c, nu=6, nv=4)
            # dark window niche in the centre of each tier
        box(fr, "M_Plaster", (W / 2 - 0.35, v0 - 0.05, zc + 0.25), (W / 2 + 0.35, v0 + 0.1, zc + th - 0.35), C(0.25, 0.22, 0.2))
        zc += th
        tw.append(w)
    # barrel-vault crown (shala) with horned ends and kalasam finials
    cw = tw[-1] - 0.3
    u0 = (W - cw) / 2
    prof = []
    for i in range(11):
        a = math.pi * i / 10
        prof.append((Dp / 2 + math.cos(a) * 1.25, zc + math.sin(a) * 1.6))
    prism_x(fr, "M_Plaster", u0, u0 + cw, prof[::-1], C(0.9, 0.78, 0.55))
    for uu in (u0 - 0.35, u0 + cw):
        box(fr, "M_Plaster", (uu, Dp / 2 - 0.4, zc), (uu + 0.35, Dp / 2 + 0.4, zc + 1.1), C(0.9, 0.78, 0.55))
        cyl(fr, "M_Plaster", (uu + 0.17, Dp / 2, zc + 1.1), 0.2, 0.6, 6, C(0.9, 0.78, 0.55), r_top=0.05)
    for i in range(7):
        cu = u0 + cw * (i + 0.5) / 7
        cyl(fr, "M_Metal", (cu, Dp / 2, zc + 1.55), 0.1, 0.7, 6, C(0.75, 0.6, 0.3), r_top=0.02)
    # temple compound wall either side of the gopuram
    for (ya, yb) in ((5.5, 13.0), (-12.0, -5.5)):
        f2 = Frame(x0, yb, 0, -1)
        L = yb - ya
        vgrid(f2, "M_Plaster", 0, L, 0, 3.4, 0.0, cream, s=2.0, cell=2.0)
        box(f2, "M_Plaster", (0, 0.0, 3.4), (L, 0.5, 3.7), ochre)
        box(f2, "M_Plaster", (0, 0.01, 0), (L, 0.5, 3.4), cream, skip=("-v", "-z"))
        with DETAIL():
            for i in range(int(L / 1.2)):
                box(f2, "M_Plaster", (0.4 + i * 1.2, 0.1, 3.7), (0.8 + i * 1.2, 0.4, 4.2), pal[i % len(pal)])
    # halls behind (low, flat-roofed) + a small vimana dome
    box(WORLD, "M_Plaster", (51.5, -11.0, 0), (72.0, 12.0, 5.5), mul(cream, 0.95), s=3.0)
    box(WORLD, "M_Plaster", (51.3, -11.2, 5.5), (72.2, 12.2, 5.9), ochre)
    for (cx, cy, r) in ((64.0, 0.5, 2.0), (58.0, 7.5, 1.1), (58.0, -6.5, 1.1)):
        box(WORLD, "M_Plaster", (cx - r * 1.2, cy - r * 1.2, 5.9), (cx + r * 1.2, cy + r * 1.2, 7.5), cream)
        sphere("M_Plaster", (cx, cy, 7.5), r, C(0.92, 0.84, 0.62), nu=10, nv=6, sz=1.3)
        cyl(WORLD, "M_Metal", (cx, cy, 7.5 + r * 1.25), 0.12, 0.6, 6, C(0.75, 0.6, 0.3), r_top=0.02)


def minaret(x, y, h=17.0, r=1.15):
    cream = C(0.94, 0.92, 0.86)
    levels = 7
    lh = (h - 3.0) / levels
    z = 0.0
    cyl(WORLD, "M_Plaster", (x, y, 0), r * 1.15, 3.0, 8, cream, smooth=False)
    z = 3.0
    for i in range(levels):
        rr_ = r * (1.0 - 0.04 * i)
        cyl(WORLD, "M_Plaster", (x, y, z), rr_, lh - 0.2, 8, jitter(cream, 0.02), smooth=False)
        cyl(WORLD, "M_Plaster", (x, y, z + lh - 0.2), rr_ * 1.12, 0.2, 8, mul(cream, 0.92), smooth=False)
        # double arch-shaped niches (dark recesses) on each face
        for k in range(8):
            a = math.tau * (k + 0.5) / 8
            nx, ny = math.cos(a), math.sin(a)
            fr = Frame(x + nx * rr_ * 0.93 - ny * 0.3, y + ny * rr_ * 0.93 + nx * 0.3, -ny, nx)
            fr = Frame(x + nx * rr_ * 0.925 + ny * 0.28, y + ny * rr_ * 0.925 - nx * 0.28, -ny, nx)
            atlas_quad(fr, "M_Windows", 0.0, 0.56, z + 0.25, z + lh - 0.5, -0.01, WIN["open"], C(0.8, 0.8, 0.8), facing="+v")
        z += lh
    sphere("M_Plaster", (x, y, z + 0.1), r * 0.9, cream, nu=8, nv=6, sz=1.2)
    cyl(WORLD, "M_Metal", (x, y, z + r * 1.1), 0.08, 1.2, 6, C(0.7, 0.6, 0.3), r_top=0.01)


def jamae_mosque():
    """Jamae (Chulia) Mosque gateway: twin octagonal minarets + miniature palace facade."""
    ya, yb = -28.8, -19.2
    minaret(46.4, yb, 17.0)
    minaret(46.4, ya, 17.0)
    fr = Frame(45.4, yb - 1.0, 0, -1)
    L = (yb - ya) - 2.0
    cream = C(0.94, 0.92, 0.86)
    gate = (L / 2 - 1.1, 0.0, L / 2 + 1.1, 3.6)
    holes = [gate] + [(0.6 + i * 1.3, 5.2, 1.2 + i * 1.3, 6.6) for i in range(6)]
    wall_with_holes(fr, "M_Plaster", 0, L, 0, 7.6, holes, 0.0, cream, s=2.0)
    for hh in holes:
        recess(fr, hh, 0.0, 0.3, mul(cream, 0.85), "M_Windows", C(0.4, 0.5, 0.45),
               back_uv=arect(WIN["door"] if hh is gate else WIN["jal_closed"]), sill=hh is not gate)
    box(fr, "M_Plaster", (0, 0.01, 0), (L, 3.0, 7.6), cream, skip=("-v", "-z"))
    box(fr, "M_Plaster", (-0.1, -0.2, 7.6), (L + 0.1, 3.1, 7.9), mul(cream, 0.94))
    for i in range(8):
        cu = 0.3 + i * (L - 0.6) / 7
        box(fr, "M_Plaster", (cu - 0.18, -0.1, 7.9), (cu + 0.18, 0.26, 8.9), cream)
        cyl(fr, "M_Plaster", (cu, 0.08, 8.9), 0.2, 0.3, 6, cream, r_top=0.02)
    # prayer hall behind with a pitched roof
    box(WORLD, "M_Plaster", (48.6, -28.0, 0), (66.0, -20.0, 6.5), cream, s=3.0)
    hh = House(W=17.4, storeys=2, style="early", wall=cream, shutter=SHUTTER["green"], pitch=22, roofcol=C(0.8, 0.8, 0.78), jack=False)
    roof_simple(Frame(48.6, -20.0, 0, -1), 8.0, 6.5, hh) if False else None
    face(WORLD, "M_RoofTile", [(48.4, -20.0, 6.5), (48.4, -28.0, 6.5), (66.2, -28.0, 6.5), (66.2, -20.0, 6.5)][::-1], C(0.7, 0.7, 0.7), s=1.2)
    mbox(M_at(57.3, -24.0, 7.6, 0), "M_RoofTile", (17.8, 8.4, 2.2), C(0.8, 0.8, 0.78), s=1.2)


def far_skyline():
    """Distant low-poly masses in the haze (godowns, office blocks) + Cathay Building silhouette."""
    rr = random.Random(77)
    for k in range(70):
        a = rr.uniform(0, math.tau)
        d = rr.uniform(75, 190)
        x, y = math.cos(a) * d * 1.2, math.sin(a) * d
        if abs(y) < 50 and abs(x) < 60:
            continue
        if any(abs(x - tx) < tw / 2 + 25 and abs(y - ty) < td / 2 + 25 for (tx, ty, tw, td, _h, _k) in TOWERS):
            continue
        w, dd, h = rr.uniform(10, 30), rr.uniform(10, 25), rr.uniform(9, 24)
        M = M_at(x, y, h / 2, rr.uniform(-0.3, 0.3) + (0 if rr.random() < 0.5 else math.pi / 2))
        col = jitter(C(0.78, 0.76, 0.72), 0.08)
        mbox(M, "M_Plaster", (w, dd, h), col, s=6.0)
        if rr.random() < 0.6:
            mbox(M @ M_at(0, 0, h / 2 + 1.2, 0), "M_RoofTile", (w * 0.9, dd * 0.9, 2.4), C(0.7, 0.62, 0.58), s=3.0)
    # Cathay Building (1939/40, ~83 m) far to the north up the eastern cross street
    cx, cy = 60.0, 470.0
    col = C(0.84, 0.82, 0.76)
    mbox(M_at(cx, cy, 20, 0), "M_Plaster", (46, 22, 40), col, s=8.0)
    mbox(M_at(cx, cy, 52, 0), "M_Plaster", (22, 18, 24), col, s=8.0)
    mbox(M_at(cx, cy, 70, 0), "M_Plaster", (13, 12, 12), col, s=8.0)
    mbox(M_at(cx, cy, 79, 0), "M_Plaster", (6, 6, 8), col, s=8.0)


def ground_plane():
    # large hazy ground plane under the skyline so the horizon never shows void
    for (xa, xb, ya, yb) in ((-400, 400, 46, 600), (-400, 400, -600, -46), (-400, -44.6, -46, 46), (44.6, 400, -46, 46),
                             (-44.6, 44.6, 6.8, 46), (-44.6, 44.6, -46, -6.8)):
        grid_quad(WORLD, "M_Road", xa, xb, ya, yb, -0.05, C(0.36, 0.34, 0.30), s=12.0, cell=200.0)


# ======================================================================================
# Shelter interior (separate room at X = 200)
# ======================================================================================
def shelter_interior():
    with GROUP("ShelterInterior"):
        x0, x1, y0, y1, h = 196.0, 203.0, -2.0, 2.0, 2.35
        brick = C(0.85, 0.78, 0.7)
        # walls (inward facing), floor, ceiling
        grid_quad(WORLD, "M_Floor", x0, x1, y0, y1, 0.0, C(0.55, 0.53, 0.5), s=1.2, cell=1.0)
        grid_quad(WORLD, "M_Plaster", x0, x1, y0, y1, h, C(0.5, 0.5, 0.48), s=2.0, cell=1.0, down=True)
        fN = Frame(x0, y1, 1, 0)    # north wall seen from inside: faces -y
        vgrid(fN, "M_Brick", 0, x1 - x0, 0, h, 0.0, brick, s=(0.96, 0.8), cell=1.0)
        fS = Frame(x1, y0, -1, 0)
        vgrid(fS, "M_Brick", 0, x1 - x0, 0, h, 0.0, brick, s=(0.96, 0.8), cell=1.0)
        fE = Frame(x1, y1, 0, -1)
        vgrid(fE, "M_Brick", 0, y1 - y0, 0, h, 0.0, brick, s=(0.96, 0.8), cell=1.0)
        fW = Frame(x0, y0, 0, 1)
        door = (1.5, 0.0, 2.5, 1.95)
        wall_with_holes(fW, "M_Brick", 0, y1 - y0, 0, h, [door], 0.0, brick, s=(0.96, 0.8))
        recess(fW, door, 0.0, 0.3, brick, "M_Windows", C(0.5, 0.4, 0.3), back_uv=arect(WIN["door"]), jamb_mat="M_Brick", sill=False)
        # outside shell (closed for shadows)
        box(WORLD, "M_Brick", (x0 - 0.35, y0 - 0.35, -0.01), (x1 + 0.35, y1 + 0.35, h + 0.3), mul(brick, 0.7), skip=("-z",))
        # timber roof beams
        for k in range(4):
            xx = x0 + 1.0 + k * 1.7
            box(WORLD, "M_Timber", (xx, y0, h - 0.2), (xx + 0.15, y1, h), TIMBER_DARK)
        # benches along both long walls
        for (ya, yb) in ((y0 + 0.05, y0 + 0.5), (y1 - 0.5, y1 - 0.05)):
            box(WORLD, "M_Timber", (x0 + 1.2, ya, 0.42), (x1 - 0.9, yb, 0.47), TIMBER_RAW)
            for k in range(4):
                xx = x0 + 1.4 + k * 1.5
                box(WORLD, "M_Brick", (xx, ya + 0.05, 0), (xx + 0.24, yb - 0.05, 0.42), brick, s=(0.96, 0.8))
        # sandbags stacked by the door, bundles, a mat, water tin, crates
        sandbag_wall(Frame(x0 + 0.05, y0 + 0.05, 0, 1), 0.0, 1.2, 0.0, 0.7, 0.0, 5)
        crate(M_at(x1 - 0.45, y1 - 0.45, 0.28, 0.1), size=(0.6, 0.55, 0.56))
        crate(M_at(x1 - 0.45, y0 + 0.5, 0.2, -0.2), size=(0.5, 0.45, 0.4))
        bundle(M_at(x1 - 1.2, y0 + 0.35, 0.72, 0), 0.22)
        suitcase(M_at(x0 + 1.6, y1 - 0.3, 0.68, 0.0))
        mbox(M_at(199.5, 0.0, 0.01, 0.05), "M_Details", (2.0, 1.2, 0.01), WHITE, uvs={"+z": arect(DET["chick"])})
        water_jar(x1 - 0.4, 0.0, 0.0, 0.6)
        # wireless set (1930s tombstone radio) on the crate
        rx, ry = x1 - 0.45, y1 - 0.45
        mbox(M_at(rx, ry, 0.56 + 0.22, math.radians(180)), "M_Timber", (0.4, 0.24, 0.44), C(0.45, 0.28, 0.16))
        mbox(M_at(rx, ry - 0.125, 0.56 + 0.28, math.radians(180)), "M_Cloth", (0.28, 0.01, 0.2), C(0.7, 0.6, 0.42))
        mbox(M_at(rx, ry - 0.125, 0.56 + 0.1, math.radians(180)), "M_Emissive", (0.2, 0.01, 0.05), C(1.0, 0.8, 0.45))
        box(WORLD, "M_Metal", (rx - 0.3, ry - 0.1, 0.56), (rx - 0.2, ry + 0.1, 0.7), IRON)  # battery
        # oil lamp (hurricane lantern) on a hook, candles on the other crate
        lp = (x0 + 3.5, y1 - 0.12, 1.9)
        tube("M_Metal", (lp[0], y1, lp[2] + 0.1), (lp[0], y1 - 0.12, lp[2] + 0.1), 0.01, 4, IRON)
        cyl(WORLD, "M_Metal", (lp[0], lp[1], lp[2] - 0.3), 0.09, 0.05, 8, C(0.3, 0.3, 0.28))
        cyl(WORLD, "M_Emissive", (lp[0], lp[1], lp[2] - 0.25), 0.06, 0.16, 8, C(1.0, 0.75, 0.4))
        cyl(WORLD, "M_Metal", (lp[0], lp[1], lp[2] - 0.09), 0.08, 0.05, 8, C(0.3, 0.3, 0.28), r_top=0.03)
        for k in range(3):
            cx, cy = x1 - 0.55 + k * 0.08, y0 + 0.45 + (k % 2) * 0.08
            cyl(WORLD, "M_Plaster", (cx, cy, 0.4), 0.02, 0.1 + k * 0.03, 6, C(0.95, 0.92, 0.85))
            sphere("M_Emissive", (cx, cy, 0.52 + k * 0.03), 0.015, C(1.0, 0.7, 0.3), nu=5, nv=3, sz=1.8)
    # colliders for the room
    collider("COL_Int_WallN", (195.6, 2.0, 0), (203.4, 2.4, 2.6))
    collider("COL_Int_WallS", (195.6, -2.4, 0), (203.4, -2.0, 2.6))
    collider("COL_Int_WallE", (203.0, -2.4, 0), (203.4, 2.4, 2.6))
    collider("COL_Int_WallW", (195.6, -2.4, 0), (196.0, 2.4, 2.6))
    collider("COL_Int_BenchN", (197.2, 1.45, 0), (202.1, 2.0, 0.5))
    collider("COL_Int_BenchS", (197.2, -2.0, 0), (202.1, -1.45, 0.5))
    collider("COL_Int_Crates", (202.1, -2.0, 0), (203.0, -1.0, 0.8))
    collider("COL_Int_Radio", (202.1, 1.0, 0), (203.0, 2.0, 1.1))
    collider("COL_Int_Bags", (196.0, -2.0, 0), (196.8, -0.8, 0.8))
    marker("INT_Spawn", (196.8, 0.3, 0.0), (1, 0))
    marker("INT_Radio", (202.55, 1.35, 0.56), (0, -1), {"note": "radio sits on the crate; marker at its base, facing into the room"})
    for i, x in enumerate((198.0, 198.9, 199.8, 200.7)):
        marker("INT_Seat_%d" % (i + 1), (x, -1.72, 0.47), (0, 1), {"seat_height": 0.47})
    marker("INT_Seat_5", (199.4, 1.72, 0.47), (0, -1), {"seat_height": 0.47})
    marker("INT_Camera", (199.4, 0.9, 1.35), (0, -1), {"note": "eye-height camera for the candlelit family photo, looking at the south bench"})


# ======================================================================================
# Markers & contract nodes
# ======================================================================================
def contract_markers():
    marker("SPAWN_Sparky", (-33.0, 5.4, FFW), (1, 0))
    marker("NPC_Siti", (-28.6, 5.3, FFW), (-1, 0), {"note": "newspaper stand behind her"})
    marker("NPC_Rajan", (18.9, -3.0, 0.0), (-1, 0), {"note": "at the ARP wardens' post by the shelter lot"})
    marker("NPC_AhMa", (-6.1, 12.55, FFW), (0, -1), {"note": "behind the kopitiam counter (0.75 m gap to the stove)"})
    marker("NPC_Boon", (-4.55, 11.85, FFW), (0, -1), {"note": "crouched at the right-hand end of the kopitiam counter; open >= 1.8 m to his right and in front"})
    marker("NPC_Hassan", (-10.5, -1.8, 0.0), (-1, 0), {"note": "beside his broken satay cart"})
    marker("DROP_1", (-22.3, 6.15, FFW), (0, 1), {"shop": "Chee Seng Tong medical hall 濟生堂"})
    marker("DROP_2", (-1.8, -6.15, FFW), (0, -1), {"shop": "Mei Hua tailor 美華洋服"})
    marker("DROP_3", (21.6, 6.15, FFW), (0, 1), {"shop": "Nam Hong provision shop 南豐號"})
    marker("SNAP_Poster", (22.4, -6.2, 0.0), (4.6, -2.8), {"target": [27.0, 1.5, 9.0]})
    marker("SNAP_Bicycle", (-12.95, 1.9, 0.0), (0, 1), {"target": [-12.95, 0.8, -4.33]})
    marker("SNAP_Smoke", (-30.0, 0.5, 0.0), (-290 + 30, 40 - 0.5), {"target_node": "SMOKE_2"})
    marker("SHELTER_Entrance", (21.2, -8.1, 0.0), (0, -1), {"note": "mouth of the sandbagged porch; door is 2 m further -y (three.js +z)"})
    marker("SMOKE_1", (-230.0, -150.0, 0.0), (0, -1), {"source": "Pulau Bukom oil tanks direction"})
    marker("SMOKE_2", (-290.0, 40.0, 0.0), (0, -1), {"source": "Normanton oil depot direction"})
    marker("SMOKE_3", (-120.0, -260.0, 0.0), (0, -1), {"source": "harbour oil tanks"})
    marker("EPI_Spawn", (21.2, -7.4, 0.0), (0, 1), {"note": "coming out of the shelter"})
    marker("EPI_Queue_1", (21.6, 5.5, FFW), (0, 1), {"note": "rice-ration queue at Nam Hong provision shop"})
    for i, x in enumerate((20.7, 19.8, 18.9, 18.0, 17.1)):
        marker("EPI_Queue_%d" % (i + 2), (x, 5.5, FFW), (1, 0))
    marker("EPI_AhMa", (-5.5, 5.95, FFW), (0, -1), {"note": "Ah Ma sits on the crate outside the shuttered kopitiam (OCC_KopiClosed)", "seat_height": 0.45})
    # shopkeepers behind their counters, facing the street
    marker("SHOPKEEPER_1", (-22.3, FP + SV + 1.55, FFW), (0, -1), {"shop": "medical hall (DROP_1)"})
    marker("SHOPKEEPER_2", (-1.8, -(FP + SV + 1.55), FFW), (0, 1), {"shop": "tailor (DROP_2)"})
    marker("SHOPKEEPER_3", (21.6, FP + SV + 1.55, FFW), (0, -1), {"shop": "provision shop (DROP_3)"})
    # kopitiam customers: marker on the floor at the chair seat's front edge, facing the table
    for i, (ti, a_deg) in enumerate(((0, 270), (1, 180), (2, 90))):
        tu, tv, _ = KOPI_TABLES[ti]
        a = math.radians(a_deg)
        x, y = -8.5 + tu + math.cos(a) * 0.42, FP + tv + math.sin(a) * 0.42
        marker("KOPI_Customer_%d" % (i + 1), (round(x, 3), round(y, 3), FFW), (-math.cos(a), -math.sin(a)),
               {"seat_height": 0.45, "table": i + 1})
    # background townsfolk spots (against shopfronts / at kerbs, off the main routes)
    for i, (pos, fdir, note) in enumerate((
            ((-25.5, -2.9, 0.0), (1, 0), "road, south kerb"),
            ((-9.6, 6.3, FFW), (0, -1), "north five-foot way, tea merchant's shutters"),
            ((5.4, -6.3, FFW), (0, 1), "south five-foot way, by the letter-writer"),
            ((15.9, 2.7, 0.0), (0, 1), "road, north kerb by the lamp post"),
            ((29.6, 6.3, FFW), (0, -1), "north five-foot way, pawnshop front"),
            ((-8.0, -2.9, 0.0), (0, 1), "road, south kerb opposite the kopitiam"))):
        marker("STREET_Extra_%d" % (i + 1), pos, fdir, {"note": note})
    # Then & Now: eye height of Sparky (1.0 m) on the five-foot way near SPAWN_Sparky, looking down the
    # street along the arcade to the Sri Mariamman gopuram
    tgt = Vector((46.0, 1.2, 8.0))
    cam = Vector((-30.0, 4.1, FFW + 1.0))
    marker("THEN_NOW_Camera", tuple(cam), tuple(tgt - cam), {"note": "old Mr. Boon's 1942 photo viewpoint; -Y axis looks at the gopuram", "fov_deg": 55})


def walkable_steps():
    """Walkable raised surfaces as boxes (top = walk height). Treat as ground/step-up, not walls."""
    p = lambda top: {"walkable": True, "top": top}
    collider("COL_Step_FFW_N_W", (X_MIN, FP, -0.4), (-2.5, FP + SV, FFW), p(FFW))
    collider("COL_Step_FFW_N_E", (2.5, FP, -0.4), (X_MAX, FP + SV, FFW), p(FFW))
    collider("COL_Step_FFW_S_W", (X_MIN, -FP - SV, -0.4), (17.0, -FP, FFW), p(FFW))
    collider("COL_Step_FFW_S_E", (27.0, -FP - SV, -0.4), (X_MAX, -FP, FFW), p(FFW))
    collider("COL_Step_Kopitiam", (-8.5, FP + SV, -0.4), (-2.5, FP + KOPI_D, FFW), p(FFW))
    collider("COL_Step_Kerb_N", (X_MIN, ROAD_HW, -0.4), (X_MAX, FP, KERB_Z), p(KERB_Z))
    collider("COL_Step_Kerb_S", (X_MIN, -FP, -0.4), (X_MAX, -ROAD_HW, KERB_Z), p(KERB_Z))


def block_colliders():
    collider("COL_Block_NW", (X_MIN, FP + SV, 0), (-8.5, FP + DEPTH, 12.0))
    collider("COL_Block_NE", (2.5, FP + SV, 0), (X_MAX, FP + DEPTH, 12.0))
    collider("COL_Block_SW", (X_MIN, -FP - DEPTH, 0), (17.0, -FP - SV, 12.0))
    collider("COL_Block_SE", (27.0, -FP - DEPTH, 0), (X_MAX, -FP - SV, 12.0))


def night_rumour_fire_markers():
    # night blackout search: spawn by the shelter, a trail of clues west, Boon hiding at the far end
    marker("NIGHT_Spawn", (21.0, -5.6, 0.0), (-1, 0.15), {"note": "just outside the shelter lot, facing up the street (west)"})
    marker("NIGHT_Clue_1", (4.2, -5.5, FFW), (-1, 0), {"surface": "south five-foot way (covered)"})
    marker("NIGHT_Clue_2", (-12.8, 0.6, 0.0), (-1, 0), {"surface": "open road (no cover)"})
    marker("NIGHT_Clue_3", (-29.2, 5.6, FFW), (-1, 0), {"surface": "north five-foot way (covered)"})
    marker("NIGHT_Boon", (-31.45, -5.55, FFW), (1, 0), {"note": "crouched against the east end of the tipped handcart; open approach from the east (>= 1.2 m)"})
    # dusk rumours: small groups of neighbours
    marker("RUMOUR_1", (-5.4, 2.6, 0.0), (0, 1), {"note": "outside the kopitiam", "group_radius": 1.2})
    marker("RUMOUR_2", (1.8, 2.5, 0.0), (0.3, 1), {"note": "by the lamp post at the lane mouth", "group_radius": 1.0})
    marker("RUMOUR_3", (10.6, 1.4, 0.0), (0, 1), {"note": "looking at the bombed house", "group_radius": 1.4})
    marker("RUMOUR_4", (-18.1, -5.8, FFW), (0, -1), {"note": "at a doorway on the south five-foot way", "group_radius": 1.0})
    # distant fires (burning roofs / sheds) for night lighting
    marker("FIRE_1", (-20.0, 22.0, 10.5), (0, -1), {"note": "roof of the next street, north"})
    marker("FIRE_2", (8.0, -22.5, 9.0), (0, -1), {"note": "roof of the next street, south"})
    marker("FIRE_3", (-56.0, -14.0, 8.0), (0, -1), {"note": "beyond the west cross street"})
    marker("FIRE_4", (60.0, 22.0, 6.5), (0, -1), {"note": "godown behind the east cross street"})
    marker("FIRE_5", (-95.0, 70.0, 12.0), (0, -1), {"note": "far fire on the skyline"})


def night_hiding_spot():
    with GROUP("WAR_Street"):
        _night_hiding_spot()


def _night_hiding_spot():
    """Tipped handcart + baskets in the doorway of the far west house (NIGHT_Boon crouches at its
    east end; the approach from the east along the five-foot way is open, >= 1.2 m wide)."""
    base = M_at(-33.1, -5.25, FFW, math.radians(-4), math.radians(6))
    mbox(base @ M_at(0, 0, 0.35, 0), "M_Timber", (1.9, 0.08, 0.7), TIMBER_RAW)
    mbox(base @ M_at(0, -0.45, 0.08, 0), "M_Timber", (1.9, 0.9, 0.06), TIMBER_RAW)
    wheel(M_at(-34.2, -5.0, FFW + 0.45, math.radians(0)), 0.45, 0.06, 10)
    for k in range(2):   # baskets tucked behind (west of) the cart, out of the approach
        cyl(WORLD, "M_Details", (-34.25 + k * 0.42, -6.35, FFW), 0.18, 0.3, 8, WHITE)
    collider("COL_NightCart", (-34.4, -6.6, 0), (-32.0, -4.9, 1.0))


def platform_ends():
    """Closing faces of the raised five-foot way at the lane, the lot and the row ends."""
    for (x, sgn_face, side) in ((-2.5, 1, "N"), (2.5, -1, "N"), (17.0, 1, "S"), (27.0, -1, "S"), (X_MIN, -1, "N"), (X_MAX, 1, "N"),
                                (X_MIN, -1, "S"), (X_MAX, 1, "S")):
        ya, yb = (DRAIN_Y1, FP + SV) if side == "N" else (-FP - SV, -DRAIN_Y1)
        if sgn_face > 0:
            pts = [(x, ya, DRAIN_Z), (x, yb, DRAIN_Z), (x, yb, FFW), (x, ya, FFW)]
        else:
            pts = [(x, yb, DRAIN_Z), (x, ya, DRAIN_Z), (x, ya, FFW), (x, yb, FFW)]
        face(WORLD, "M_Plaster", pts, GRANITE, s=1.0)


def trolleybus_wires():
    with GROUP("WAR_Street"):
        _trolleybus_wires()


def _trolleybus_wires():
    """Twin trolleybus wires along the eastern cross street (trolleybuses from 1929)."""
    ys = list(range(-44, 46, 18))
    for y in ys:
        for x in (36.4, 44.2):
            cyl(WORLD, "M_Metal", (x, y, 0.0), 0.12, 7.2, 8, C(0.25, 0.26, 0.26), r_top=0.09)
        wire((36.4, y, 6.9), (44.2, y, 6.9), sag=0.25, r=0.01)
    for xw in (39.6, 40.2, 41.0, 41.6):
        for a, b in zip(ys, ys[1:]):
            wire((xw, a, 6.4), (xw, b, 6.4), sag=0.15, r=0.009, n=6)


# ======================================================================================
# Build everything
# ======================================================================================
def build_level():
    layout_rows()
    road_surfaces()
    platform_ends()
    build_houses(NORTH_W + [KOPI])
    kopitiam_interior(KOPI)
    build_houses(NORTH_E)
    build_houses(SOUTH_E)
    build_houses(SOUTH_W)
    build_lane()
    build_lot()
    poster_wall_pre()
    street_props()
    night_hiding_spot()
    street_end_west()
    street_end_east()
    build_damage()
    build_occupation()
    build_kopi_closed()
    build_now()
    # backdrops (own chunks so three.js can frustum-cull them)
    with GROUP("Backdrop_West"):
        backdrop_row(-45.0, -46.0, 0, 1, 92.0, 101)                 # west cross street, far side (faces +x)
        backdrop_row(-36.0, 46.0, 0, -1, 29.9, 102)                 # west cross street, our side north (faces -x)
        backdrop_row(-36.0, -16.1, 0, -1, 29.9, 103)                # west cross street, our side south
    with GROUP("Backdrop_East"):
        backdrop_row(36.0, 16.1, 0, 1, 29.9, 104)                   # east cross street, our side north (faces +x)
        backdrop_row(36.0, -46.0, 0, 1, 29.9, 105)                  # east cross street, our side south
        backdrop_row(45.0, 46.0, 0, -1, 33.0, 106)                  # east far side north of the temple (faces -x)
        backdrop_row(45.0, -12.0, 0, -1, 6.2, 107)                  # between temple and mosque
        backdrop_row(45.0, -29.8, 0, -1, 16.2, 108)                 # south of the mosque
        gopuram()
        jamae_mosque()
    with GROUP("Backdrop_Far"):
        back_blocks(17.0, 1, [(-23.5, 23.5)], 201)
        back_blocks(-17.0, -1, [(-23.5, 15.5)], 202)
        far_skyline()
        ground_plane()
    trolleybus_wires()
    shelter_interior()
    contract_markers()
    night_rumour_fire_markers()
    walkable_steps()
    block_colliders()


# ======================================================================================
# Blender objects, materials
# ======================================================================================
MAT_DEF = {
    #  name          texture     rough metal  doubleSided
    "M_Plaster": ("plaster", 0.92, 0.0, False),
    "M_RoofTile": ("roof", 0.8, 0.0, False),
    "M_Timber": ("timber", 0.78, 0.0, False),
    "M_Floor": ("floor", 0.62, 0.0, False),
    "M_Road": ("road", 0.93, 0.0, False),
    "M_Sandbag": ("sandbag", 1.0, 0.0, False),
    "M_Brick": ("brick", 0.9, 0.0, False),
    "M_Cloth": ("cloth", 0.95, 0.0, True),
    "M_Windows": ("windows", 0.55, 0.0, False),
    "M_Details": ("details", 0.55, 0.0, False),
    "M_Signs": ("signs", 0.45, 0.0, False),
    "M_Posters": ("posters", 0.8, 0.0, False),
    "M_NowSigns": ("now", 0.5, 0.0, False),
    "M_NowShop": ("nowshop", 0.25, 0.0, False),
    "M_Glass": ("glass", 0.12, 0.6, False),
    "M_Metal": (None, 0.5, 0.55, False),
    "M_Emissive": (None, 0.5, 0.0, False),
}
IMAGES = {}
# Tiling materials: UVs are shifted per face by whole tiles and divided by UV_TILE so they fit
# [0,1] (quantisable to 16 bit); a Mapping node (-> KHR_texture_transform scale) restores them.
TILING = {"M_Plaster", "M_RoofTile", "M_Timber", "M_Floor", "M_Road", "M_Sandbag", "M_Brick", "M_Cloth", "M_Glass"}
UV_TILE = 32.0


def make_materials(res):
    mats = {}
    for name, (tex, rough, metal, ds) in MAT_DEF.items():
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        m.use_backface_culling = not ds
        nt = m.node_tree
        for n in list(nt.nodes):
            nt.nodes.remove(n)
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.location = (-300, 0)
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = metal
        attr = nt.nodes.new("ShaderNodeVertexColor")
        attr.layer_name = "Col"
        attr.location = (-900, -200)
        if tex:
            img = bpy.data.images.load(os.path.join(TEX, str(res), tex + ".png"), check_existing=False)
            img.name = tex
            IMAGES[tex] = img
            it = nt.nodes.new("ShaderNodeTexImage")
            it.image = img
            it.location = (-900, 200)
            if name in TILING:
                uvn = nt.nodes.new("ShaderNodeUVMap")
                uvn.uv_map = "UVMap"
                uvn.location = (-1400, 200)
                mp = nt.nodes.new("ShaderNodeMapping")
                mp.vector_type = "POINT"
                mp.inputs["Scale"].default_value = (UV_TILE, UV_TILE, 1.0)
                mp.location = (-1150, 200)
                nt.links.new(uvn.outputs["UV"], mp.inputs["Vector"])
                nt.links.new(mp.outputs["Vector"], it.inputs["Vector"])
            mix = nt.nodes.new("ShaderNodeMix")
            mix.data_type = "RGBA"
            mix.blend_type = "MULTIPLY"
            mix.inputs[0].default_value = 1.0
            mix.location = (-550, 100)
            nt.links.new(it.outputs["Color"], mix.inputs[6])
            nt.links.new(attr.outputs["Color"], mix.inputs[7])
            nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
        else:
            nt.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
        if name == "M_NowShop":
            # interiors glow warm: the same atlas drives the emissive map
            nt.links.new(it.outputs["Color"], bsdf.inputs["Emission Color"])
            bsdf.inputs["Emission Strength"].default_value = 0.45
        if name == "M_Emissive":
            bsdf.inputs["Emission Color"].default_value = (1.0, 0.72, 0.4, 1.0)
            bsdf.inputs["Emission Strength"].default_value = 2.0
        mats[name] = m
    return mats


LOWRES_ALWAYS = {"glass", "nowshop"}   # distant / emissive: 512² is enough on desktop too


def swap_textures(res):
    for tex, img in IMAGES.items():
        img.filepath = os.path.join(TEX, str(512 if tex in LOWRES_ALWAYS else res), tex + ".png")
        img.reload()


def object_name(group, tier):
    base = "Street_Static" if group == "STATIC" else group
    return base if tier == "base" else base + "_" + tier


def make_mesh_object(name, mats_dict, mats, coll):
    verts, faces, uvs, cols, midx, sm = [], [], [], [], [], []
    slots = []
    for mname in MATS:
        b = mats_dict.get(mname)
        if not b or not b.f:
            continue
        off = len(verts)
        si = len(slots)
        slots.append(mname)
        verts.extend(b.v)
        tiling = mname in TILING
        for f, uv, c, s_ in zip(b.f, b.uv, b.col, b.sm):
            faces.append([i + off for i in f])
            if tiling:
                du = math.floor(min(q[0] for q in uv))
                dv = math.floor(min(q[1] for q in uv))
                uv = [(min((q[0] - du) / UV_TILE, 1.0), min((q[1] - dv) / UV_TILE, 1.0)) for q in uv]
            uvs.extend(uv)
            cols.extend([c] * len(f))
            midx.append(si)
            sm.append(s_)
    if not faces:
        return None
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    for mname in slots:
        me.materials.append(mats[mname])
    uvl = me.uv_layers.new(name="UVMap")
    flat = [c for uv in uvs for c in uv]
    uvl.data.foreach_set("uv", flat)
    ca = me.color_attributes.new("Col", "FLOAT_COLOR", "CORNER")
    ca.data.foreach_set("color", [c for col in cols for c in col])
    me.polygons.foreach_set("material_index", midx)
    me.polygons.foreach_set("use_smooth", sm)
    me.color_attributes.active_color = ca
    me.color_attributes.render_color_index = me.color_attributes.active_color_index
    me.validate(clean_customdata=False)
    me.update()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


CHUNKS = [("A", -1e9, -14.0), ("B", -14.0, 2.5), ("C", 2.5, 17.0), ("D", 17.0, 1e9)]


def split_by_x(md):
    """Split a {mat: MB} dict into street chunks by face-centroid x (chunk edges at party lines)."""
    out = {c[0]: {} for c in CHUNKS}
    for mname, b in md.items():
        maps = {c[0]: {} for c in CHUNKS}
        for f, uv, col, sm in zip(b.f, b.uv, b.col, b.sm):
            cx = sum(b.v[i][0] for i in f) / len(f)
            key = next(c[0] for c in CHUNKS if c[1] <= cx < c[2])
            nb = out[key].setdefault(mname, MB())
            vm = maps[key]
            nf = []
            for i in f:
                if i not in vm:
                    vm[i] = len(nb.v)
                    nb.v.append(b.v[i])
                nf.append(vm[i])
            nb.f.append(tuple(nf))
            nb.uv.append(uv)
            nb.col.append(col)
            nb.sm.append(sm)
    return out


def make_objects(mats):
    coll = bpy.context.scene.collection
    objs = {}
    for (group, tier), md in sorted(BUCKETS.items()):
        parts = {"": md}
        if group == "STATIC":
            parts = {"_" + k: v for k, v in split_by_x(md).items()}
        for suffix, pmd in parts.items():
            name = object_name(group, tier).replace("Street_Static", "Street_Static" + suffix)
            ob = make_mesh_object(name, pmd, mats, coll)
            if ob:
                objs[name] = ob
                ob["tier"] = tier
                ob["group"] = group
    cols = []
    for (name, (x0, y0, z0, x1, y1, z1), props) in COLLIDERS:
        me = bpy.data.meshes.new(name)
        hx, hy, hz = (x1 - x0) / 2, (y1 - y0) / 2, (z1 - z0) / 2
        v = [(-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz), (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)]
        f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        me.from_pydata(v, [], f)
        ob = bpy.data.objects.new(name, me)
        ob.location = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
        ob.display_type = "WIRE"
        ob.hide_render = True
        for k, val in props.items():
            ob[k] = val
        # world-space AABB in three.js coordinates (robust even after mesh quantization
        # moves the dequantisation scale/offset onto the node transform)
        ob["aabb_min"] = [round(x0, 3), round(z0, 3), round(-y1, 3)]
        ob["aabb_max"] = [round(x1, 3), round(z1, 3), round(-y0, 3)]
        coll.objects.link(ob)
        cols.append(ob)
    empties = []
    for (name, pos, fdir, props) in MARKERS:
        ob = bpy.data.objects.new(name, None)
        ob.empty_display_type = "SINGLE_ARROW"
        ob.empty_display_size = 0.6
        ob.location = pos
        if fdir and len(fdir) == 3:
            ob.rotation_euler = Vector(fdir).to_track_quat("-Y", "Z").to_euler()
        elif fdir:
            # local -Y must point along fdir:  rotZ = atan2(dx, -dy)
            ob.rotation_euler = (0, 0, math.atan2(fdir[0], -fdir[1]))
        for k, val in props.items():
            ob[k] = val
        coll.objects.link(ob)
        empties.append(ob)
    return objs, cols, empties


# ======================================================================================
# AO bake into the colour attribute (Cycles, bake-to-vertex-colours)
# ======================================================================================
def bake_ao(objs, hide):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        sc.cycles.device = "GPU"
    except Exception as e:
        print("cycles GPU not available:", e)
    sc.cycles.samples = 12 if FAST else 32
    if sc.world is None:
        sc.world = bpy.data.worlds.new("World")
    sc.world.light_settings.distance = 1.8
    for ob in bpy.context.scene.objects:
        ob.hide_render = ob.name in hide or ob.name.startswith("COL_") or ob.hide_render
    for ob in objs:
        me = ob.data
        ao = me.color_attributes.get("AO") or me.color_attributes.new("AO", "FLOAT_COLOR", "CORNER")
        me.color_attributes.active_color = ao
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    import time
    t0 = time.time()
    res = bpy.ops.object.bake(type="AO", target="VERTEX_COLORS")
    print("BAKE", res, len(objs), "objects", round(time.time() - t0, 1), "s")
    import numpy as np
    for ob in objs:
        me = ob.data
        n = len(me.loops)
        ao = np.empty(n * 4, dtype=np.float32)
        col = np.empty(n * 4, dtype=np.float32)
        me.color_attributes["AO"].data.foreach_get("color", ao)
        me.color_attributes["Col"].data.foreach_get("color", col)
        a = ao.reshape(-1, 4)[:, 0]
        print("  AO", ob.name, "min %.2f mean %.2f" % (float(a.min()), float(a.mean())))
        k = 0.38 + 0.62 * np.clip(a, 0, 1) ** 0.8
        c = col.reshape(-1, 4)
        c[:, :3] *= k[:, None]
        me.color_attributes["Col"].data.foreach_set("color", c.ravel())
        me.color_attributes.remove(me.color_attributes["AO"])
        ca = me.color_attributes["Col"]
        me.color_attributes.active_color = ca
        me.color_attributes.render_color_index = me.color_attributes.active_color_index
    for ob in bpy.context.scene.objects:
        if ob.name in hide:
            ob.hide_render = False


def ground_darkening(objs):
    """Splash-back grime near the ground on walls (cheap 'weathering' in vertex colour)."""
    import numpy as np
    for ob in objs:
        me = ob.data
        n = len(me.loops)
        co = np.empty(len(me.vertices) * 3, dtype=np.float32)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        li = np.empty(n, dtype=np.int32)
        me.loops.foreach_get("vertex_index", li)
        z = co[li, 2]
        mi = np.empty(len(me.polygons), dtype=np.int32)
        me.polygons.foreach_get("material_index", mi)
        ls = np.empty(len(me.polygons), dtype=np.int32)
        me.polygons.foreach_get("loop_start", ls)
        lt = np.empty(len(me.polygons), dtype=np.int32)
        me.polygons.foreach_get("loop_total", lt)
        loop_mat = np.repeat(mi, lt)
        plaster_slots = [i for i, m in enumerate(me.materials) if m and m.name in ("M_Plaster", "M_Brick")]
        mask = np.isin(loop_mat, plaster_slots) & (z > -0.1) & (z < 1.4)
        col = np.empty(n * 4, dtype=np.float32)
        me.color_attributes["Col"].data.foreach_get("color", col)
        c = col.reshape(-1, 4)
        f = 1.0 - 0.28 * np.clip(1.0 - (z - FFW) / 1.1, 0, 1)
        c[mask, 0] *= f[mask]
        c[mask, 1] *= f[mask] * 0.98
        c[mask, 2] *= f[mask] * 0.95
        me.color_attributes["Col"].data.foreach_set("color", c.ravel())


# ======================================================================================
# Export
# ======================================================================================
def export_glb(path, objs, q=85):
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objs:
        ob.hide_set(False)
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    kw = dict(filepath=path, export_format="GLB", use_selection=True, export_extras=True, export_yup=True,
              export_apply=True, export_vertex_color="ACTIVE", export_all_vertex_colors=False,
              export_active_vertex_color_when_no_material=False,
              export_image_format="JPEG", export_jpeg_quality=q, export_image_quality=q,
              export_materials="EXPORT", export_texcoords=True, export_normals=True, export_tangents=False,
              export_cameras=False, export_lights=False, export_animations=False)
    bpy.ops.export_scene.gltf(**kw)
    print("exported", path, os.path.getsize(path) / 1e6, "MB")


MOBILE_BACKUP = {}


def join_tier(objs, suffix, keep=True):
    """For the mobile export: temporarily merge *_mobile meshes into their base object."""
    for name in [n for n in objs if n.endswith(suffix)]:
        base = name[: -len(suffix)]
        m = objs[name]
        if base not in objs:
            MOBILE_BACKUP[base] = None
            m.name = base
            objs[base] = m
            del objs[name]
            continue
        MOBILE_BACKUP[base] = objs[base].data.copy()
        tmp = m.copy()
        tmp.data = m.data.copy()
        bpy.context.scene.collection.objects.link(tmp)
        bpy.ops.object.select_all(action="DESELECT")
        objs[base].select_set(True)
        tmp.select_set(True)
        bpy.context.view_layer.objects.active = objs[base]
        bpy.ops.object.join()


def restore_tier(objs):
    for base, data in MOBILE_BACKUP.items():
        if data is None:
            ob = objs.pop(base)
            bpy.data.objects.remove(ob, do_unlink=True)
        else:
            objs[base].data = data


def meshopt(path):
    """Post-process with glTF-Transform (EXT_meshopt_compression + KHR_mesh_quantization).
    Set GLTF_TRANSFORM to the gltf-transform CLI (installed outside the project, e.g.
    `npm i @gltf-transform/cli` in a scratch dir). Skipped if not set."""
    cli = os.environ.get("GLTF_TRANSFORM")
    if not cli or not os.path.exists(cli):
        print("GLTF_TRANSFORM not set: skipping meshopt for", path)
        return
    tmp = path + ".tmp.glb"
    subprocess.check_call([cli, "meshopt", path, tmp, "--level", "high", "--quantize-position", "16",
                           "--quantize-texcoord", "16", "--quantize-normal", "10", "--quantize-color", "8"])
    os.replace(tmp, path)
    print("meshopt", path, os.path.getsize(path) / 1e6, "MB")


def join_detail(objs):
    for name in list(objs.keys()):
        if not name.endswith("_detail"):
            continue
        base = name[: -len("_detail")]
        d = objs[name]
        if base not in objs:
            d.name = base
            objs[base] = d
            del objs[name]
            continue
        bpy.ops.object.select_all(action="DESELECT")
        objs[base].select_set(True)
        d.select_set(True)
        bpy.context.view_layer.objects.active = objs[base]
        bpy.ops.object.join()
        del objs[name]


def tri_count(objs):
    t = 0
    for ob in objs:
        if ob.type == "MESH" and not ob.name.startswith("COL_"):
            ob.data.calc_loop_triangles()
            t += len(ob.data.loop_triangles)
    return t


def to_three(p):
    return [round(p[0], 3), round(p[2], 3), round(-p[1], 3)]


def _plain(v):
    if hasattr(v, "to_list"):
        return v.to_list()
    if hasattr(v, "to_dict"):
        return v.to_dict()
    return v


def write_nodes_json(objs, cols, empties):
    data = {"markers": {}, "colliders": {}, "meshes": {}}
    for e in empties:
        d = e.matrix_world.to_3x3() @ Vector((0, -1, 0))
        data["markers"][e.name] = {"three_pos": to_three(e.location), "three_facing": to_three(d),
                                   "props": {k: _plain(v) for k, v in e.items()}}
    for c in cols:
        x, y, z = c.location
        hx, hy, hz = [max(abs(v.co[i]) for v in c.data.vertices) for i in range(3)]
        data["colliders"][c.name] = {"three_center": to_three((x, y, z)), "three_half": [round(hx, 3), round(hz, 3), round(hy, 3)],
                                     "props": {k: _plain(v) for k, v in c.items()}}
    for name, ob in objs.items():
        ob.data.calc_loop_triangles()
        data["meshes"][name] = {"tris": len(ob.data.loop_triangles), "materials": [m.name for m in ob.data.materials]}
    with open(NODES_JSON, "w") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)


# ======================================================================================
# Previews (EEVEE)
# ======================================================================================
def preview_setup():
    sc = bpy.context.scene
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            sc.render.engine = eng
            break
        except Exception:
            pass
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    sc.render.resolution_percentage = 100
    try:
        sc.eevee.taa_render_samples = 24 if FAST else 48
    except Exception:
        pass
    for attr in ("use_raytracing", "use_shadows"):
        if hasattr(sc.eevee, attr):
            try:
                setattr(sc.eevee, attr, True)
            except Exception:
                pass
    try:
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    if sc.world is None:
        sc.world = bpy.data.worlds.new("World")
    w = sc.world
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    grad = nt.nodes.new("ShaderNodeTexGradient")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs[0])
    ramp.color_ramp.elements[0].position = 0.5
    ramp.color_ramp.elements[0].color = (0.50, 0.50, 0.48, 1)
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = (0.36, 0.40, 0.45, 1)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    sun_d = bpy.data.lights.new("Sun", "SUN")
    sun_d.energy = 3.2
    sun_d.color = (1.0, 0.92, 0.82)
    sun_d.angle = math.radians(4)
    sun = bpy.data.objects.new("PREVIEW_Sun", sun_d)
    sun.rotation_euler = (math.radians(38), math.radians(0), math.radians(-35))
    sc.collection.objects.link(sun)
    # smoke column proxies at SMOKE_ markers (preview only — the game renders particles)
    sm = bpy.data.materials.new("PREVIEW_Smoke")
    sm.use_nodes = True
    b = sm.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.03, 0.03, 0.03, 1)
    b.inputs["Roughness"].default_value = 1.0
    prev = [sun]
    for (name, pos, _, _) in MARKERS:
        if not name.startswith("SMOKE_"):
            continue
        rr = random.Random(name)
        for k in range(26):
            t = k / 25
            r = 8 + 55 * t
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=r,
                                                  location=(pos[0] + 120 * t * t + rr.uniform(-6, 6), pos[1] + 40 * t * t, 10 + 260 * t))
            o = bpy.context.active_object
            o.name = "PREVIEW_" + name + "_%d" % k
            o.data.materials.append(sm)
            prev.append(o)
    return prev


def camera(name, loc, target, lens=24, ortho=None, clip=(0.05, 2000)):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_start, cd.clip_end = clip
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    ob = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


def render(cam, fname):
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.filepath = os.path.join(PREV_DIR, fname)
    bpy.ops.render.render(write_still=True)
    print("render", fname)


def set_state(objs_all, state):
    """state: 'pre' | 'damaged' | 'epilogue' | 'now'"""
    for ob in objs_all:
        n = ob.name
        vis = True
        if n.startswith("COL_"):
            vis = False
        elif n.startswith("NOW_"):
            vis = state == "now"
        elif state == "now":
            vis = not n.startswith(("WAR_", "WIRES_", "LAUNDRY_", "OCC_", "DMG_", "PRE_")) or n == "PRE_Intact_House"
        elif n.startswith("PRE_"):
            vis = state == "pre" or (state == "damaged" and n != "PRE_Intact_House")
        elif n.startswith("OCC_"):
            vis = state == "epilogue"
        elif n.startswith("DMG_"):
            vis = state in ("damaged", "epilogue")
        ob.hide_render = not vis


def label_objects():
    """Text labels + arrows for the overhead layout preview (preview only, not exported)."""
    mat = bpy.data.materials.new("PREVIEW_Label")
    mat.use_nodes = True
    nt = mat.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.9, 0.05, 0.05, 1)
    b.inputs["Emission Color"].default_value = (1, 0.1, 0.05, 1)
    b.inputs["Emission Strength"].default_value = 3.0
    out = []
    for (name, pos, fdir, _) in MARKERS:
        if abs(pos[0]) > 60 or abs(pos[1]) > 30:
            continue
        cu = bpy.data.curves.new("L_" + name, "FONT")
        cu.body = name.replace("_", " ")
        cu.size = 0.55
        cu.align_x = "CENTER"
        ob = bpy.data.objects.new("PREVIEW_L_" + name, cu)
        ob.location = (pos[0], pos[1] + 0.45, 3.0)
        ob.data.materials.append(mat)
        bpy.context.scene.collection.objects.link(ob)
        out.append(ob)
        me = bpy.data.meshes.new("A_" + name)
        a = math.atan2(fdir[0], -fdir[1]) if fdir else 0
        pts = [(-0.25, 0.1, 0), (0.25, 0.1, 0), (0, -0.55, 0)]
        rot = Matrix.Rotation(a, 3, "Z")
        me.from_pydata([tuple(rot @ Vector(p)) for p in pts], [], [(0, 1, 2)])
        ao = bpy.data.objects.new("PREVIEW_A_" + name, me)
        ao.location = (pos[0], pos[1], 3.0)
        ao.data.materials.append(mat)
        bpy.context.scene.collection.objects.link(ao)
        out.append(ao)
    return out


def previews(all_objs):
    os.makedirs(PREV_DIR, exist_ok=True)
    prev = preview_setup()
    sc = bpy.context.scene
    E = FFW + 1.5
    set_state(all_objs, "pre")
    render(camera("CAM_spawn", (-34.6, 4.7, E), (-20, 3.0, 2.2), lens=22), "01_spawn_eye_level.png")
    render(camera("CAM_road", (-33.5, -0.8, 1.7), (0, 0.6, 3.2), lens=20), "02_street_from_west.png")
    render(camera("CAM_kopi", (-5.2, -2.2, 1.6), (-5.5, 8.0, 2.2), lens=22), "03_kopitiam.png")
    render(camera("CAM_kopi_in", (-3.3, 12.9, 1.7), (-6.8, 6.0, 0.9), lens=18), "04_kopitiam_interior.png")
    render(camera("CAM_shelter", (20.6, -1.2, 1.7), (22.5, -11.0, 1.2), lens=20), "05_shelter_lot.png")
    render(camera("CAM_east", (22.0, 1.2, 1.7), (46.0, 0.0, 8.0), lens=24), "06_east_end_gopuram.png")
    render(camera("CAM_ffw", (-24.0, 5.5, E), (-8.0, 5.3, 2.2), lens=20), "07_five_foot_way.png")
    set_state(all_objs, "damaged")
    render(camera("CAM_dmg", (4.0, -1.8, 1.7), (10.6, 5.0, 3.0), lens=24), "08_bomb_damage.png")
    set_state(all_objs, "epilogue")
    render(camera("CAM_epi", (-10.0, -1.6, 1.7), (21.0, 4.0, 2.4), lens=24), "09_epilogue_syonan.png")
    render(camera("CAM_epi2", (14.5, 1.0, 1.7), (21.6, 6.0, 1.4), lens=24), "10_epilogue_ration_queue.png")
    render(camera("CAM_epi3", (-5.4, 1.2, 1.5), (-5.5, 7.0, 1.2), lens=24), "10b_epilogue_kopitiam_closed.png")
    # Then & Now pair from THEN_NOW_Camera (Sparky's eye, 1.0 m)
    tn = next(m for m in MARKERS if m[0] == "THEN_NOW_Camera")
    cam_tn = camera("CAM_thennow", tn[1], tuple(Vector(tn[1]) + Vector(tn[2])), lens=26)
    set_state(all_objs, "pre")
    render(cam_tn, "15_then_now_1942.png")
    set_state(all_objs, "now")
    render(cam_tn, "16_then_now_present.png")
    render(camera("CAM_now2", (-5.0, -1.5, 1.6), (6.0, 5.0, 2.2), lens=22), "17_present_day_street.png")
    render(camera("CAM_now3", (20.5, -2.5, 1.7), (21.5, -12.0, 2.0), lens=22), "18_present_day_pocket_park.png")
    set_state(all_objs, "pre")
    render(camera("CAM_kopi_walk", (-3.2, 6.2, 1.5), (-5.2, 12.5, 0.6), lens=20), "04b_kopitiam_walkway.png")
    render(camera("CAM_nightboon", (-27.5, -5.2, 1.3), (-32.5, -5.6, 0.4), lens=24), "19_night_boon_hiding.png")
    # shelter interior: candle-lit
    set_state(all_objs, "pre")
    for o in prev:
        if o.name == "PREVIEW_Sun":
            o.hide_render = True
    bg = sc.world.node_tree.nodes.get("Background")
    old = bg.inputs["Strength"].default_value
    bg.inputs["Strength"].default_value = 0.03
    lamps = []
    for (pos, e, c) in (((199.5, 1.7, 1.66), 160, (1.0, 0.62, 0.3)), ((202.45, -1.5, 0.62), 40, (1.0, 0.6, 0.25))):
        ld = bpy.data.lights.new("P", "POINT")
        ld.energy = e
        ld.color = c
        ld.shadow_soft_size = 0.05
        lo = bpy.data.objects.new("PREVIEW_Lamp", ld)
        lo.location = pos
        sc.collection.objects.link(lo)
        lamps.append(lo)
    render(camera("CAM_int", (196.7, 0.9, 1.55), (201.5, -0.6, 0.7), lens=18), "11_shelter_interior.png")
    for lo in lamps:
        lo.hide_render = True
    bg.inputs["Strength"].default_value = old
    for o in prev:
        if o.name == "PREVIEW_Sun":
            o.hide_render = False
    # overhead plan cut at z = 3.7 (below the five-foot-way ceilings) with labelled markers
    labels = label_objects()
    bpy.ops.mesh.primitive_plane_add(size=300, location=(0, 0, -1.0))
    pl = bpy.context.active_object
    pl.name = "PREVIEW_PlanFloor"
    pm = bpy.data.materials.new("PREVIEW_PlanFloor")
    pm.use_nodes = True
    pm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.08, 0.08, 0.08, 1)
    pl.data.materials.append(pm)
    sc.render.resolution_x, sc.render.resolution_y = 2400, 1000
    cam = camera("CAM_plan", (0.0, 0.0, 60.0), (0.0, 0.0, 0.0), ortho=86, clip=(60.0 - 3.7, 80.0))
    cam.rotation_euler = (0, 0, 0)
    render(cam, "12_overhead_layout_markers.png")
    for ob in all_objs:
        if ob.name.startswith("COL_"):
            ob.hide_render = False
            if not ob.data.materials:
                m = bpy.data.materials.get("PREVIEW_Col") or bpy.data.materials.new("PREVIEW_Col")
                m.use_nodes = True
                m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.1, 0.4, 1.0, 1)
                m.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.35
                try:
                    m.surface_render_method = "BLENDED"
                except Exception:
                    m.blend_method = "BLEND"
                ob.data.materials.append(m)
    render(cam, "13_overhead_colliders.png")
    cam2 = camera("CAM_aerial", (-45.0, -40.0, 38.0), (5.0, 2.0, 0.0), lens=30)
    for ob in all_objs:
        if ob.name.startswith("COL_"):
            ob.hide_render = True
    for o in labels:
        o.hide_render = True
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    render(cam2, "14_aerial.png")


# ======================================================================================
# main
# ======================================================================================
def ensure_textures():
    need = [os.path.join(TEX, r, n + ".png") for r in ("1024", "512") for n in
            ("plaster", "roof", "timber", "floor", "road", "sandbag", "brick", "cloth", "windows", "details", "signs", "posters", "now",
             "glass", "nowshop")]
    if all(os.path.exists(p) for p in need):
        return
    print("generating textures ...")
    subprocess.check_call([sys.executable, os.path.join(HERE, "gen_ww2_textures.py")], env=dict(os.environ))


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ensure_textures()
    build_level()
    mats = make_materials(1024)
    objs, cols, empties = make_objects(mats)
    ground_darkening([o for o in objs.values()])
    if DO_BAKE:
        skip = ("DMG_", "OCC_", "PRE_Posters", "PRE_Barricade", "PRE_ARPSign", "WIRES_", "LAUNDRY_")
        mobile_names = {n for n in objs if n.endswith("_mobile")}
        static_bake = [o for n, o in objs.items() if not n.startswith(skip) and n not in mobile_names]
        hide = {n for n in objs if n.startswith(("DMG_", "OCC_"))} | mobile_names
        bake_ao(static_bake, hide)
        mob_bake = [objs[n] for n in mobile_names if not n.startswith(skip)]
        hide = {n for n in objs if n.startswith(("DMG_", "OCC_")) or n.endswith("_detail")}
        if mob_bake:
            bake_ao(mob_bake, hide)
        dmg = [o for n, o in objs.items() if n.startswith("DMG_") and not n.endswith("_mobile")]
        hide = {n for n in objs if n.startswith(("PRE_Intact_House", "OCC_"))} | mobile_names
        if dmg:
            bake_ao(dmg, hide)
    # --- mobile tier: base + *_mobile (renamed to the base name on export), 512² textures ---
    swap_textures(512)
    join_tier(objs, "_mobile", keep=True)
    mob = [o for n, o in objs.items() if not n.endswith(("_detail", "_mobile"))] + cols + empties
    os.makedirs(os.path.dirname(OUT_MOBILE), exist_ok=True)
    tri_m = tri_count(mob)
    export_glb(OUT_MOBILE, mob)
    meshopt(OUT_MOBILE)
    # --- desktop tier: detail merged, 1024² textures ---
    swap_textures(1024)
    restore_tier(objs)
    for n in [n for n in objs if n.endswith("_mobile")]:
        bpy.data.objects.remove(objs.pop(n), do_unlink=True)
    join_detail(objs)
    desk = list(objs.values()) + cols + empties
    tri_d = tri_count(desk)
    export_glb(OUT_DESKTOP, desk, q=72)
    meshopt(OUT_DESKTOP)
    write_nodes_json(objs, cols, empties)
    print("TRIS mobile", tri_m, "desktop", tri_d)
    with open(NODES_JSON) as f:
        nd = json.load(f)
    nd["tris"] = {"mobile": tri_m, "desktop": tri_d}
    with open(NODES_JSON, "w") as f:
        json.dump(nd, f, indent=1, ensure_ascii=False)
    print("OBJECTS", {n: len(o.data.materials) for n, o in objs.items()})
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    if DO_PREVIEWS:
        previews(list(objs.values()) + cols)
        bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)


main()
