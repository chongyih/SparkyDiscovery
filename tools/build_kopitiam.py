"""
Sparky Discovery — Chapter 2 level: Boon's kopitiam in an early Queenstown HDB block, 9 August 1965.

Reproducible Blender build script (Blender 5.2):
    GLTF_TRANSFORM=/path/to/node_modules/.bin/gltf-transform \
    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python tools/build_kopitiam.py [-- --no-bake] [--no-previews] [--fast]

Outputs
    public/assets/models/kopitiam.glb          desktop tier (1024² textures, detail geometry)
    public/assets/models/kopitiam-mobile.glb   mobile tier (512² textures, no detail geometry)
    tools/kopitiam_nodes.json                  markers / colliders in three.js space
    docs/previews/kopitiam/*.png               EEVEE previews (ignored by git)

Textures are shared with Chapter 1 (tools/ww2_tex, from gen_ww2_textures.py): plaster, timber, floor
tiles, the details atlas (marble, provisions, vent grille), windows atlas, glass and cloth.
Anything with lettering (shop signs, the chalk order board, the 1965 calendar, portraits, the four
wall choices, the TV picture) is a plain quad with 0..1 UVs in its own node; the game draws those
at runtime (canvas / video textures), so Chinese, Malay and Tamil text is shaped by the browser.

The block and its shops are invented (no real Queenstown block is named: see
docs/research/1965-history.md §12). 1960s HDB shop-house block: ground-floor shops opening onto a
covered corridor, seven storeys of flats above, a car park in front.

Conventions (docs/design.md): Blender Z-up, metres; Blender (x, y, z) -> three.js (x, z, -y).
    Corridor runs along X (x -15..15), outer edge y = 0, shopfronts at y = 3.
    Kopitiam: x -4.5..4.5, y 3..12 (two bays). Car park: y < 0 at z = 0. Floors at z = 0.15.
    Marker empties face their local -Y axis.
Node groups:
    THEN_*  1965 only (hidden in the present-day Then & Now view)
    NOW_*   present day only (Then & Now); plaster turns vivid in code
    DECAL_* / WALL_* / TV_Screen   runtime-textured quads (UV 0..1)
    FAN_*   ceiling-fan blades (code spins them about their own centre)
"""
import bpy, math, random, os, sys, json, subprocess
from mathutils import Vector, Matrix
from contextlib import contextmanager

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
DO_BAKE = "--no-bake" not in ARGS
DO_PREVIEWS = "--no-previews" not in ARGS
FAST = "--fast" in ARGS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TEX = os.path.join(HERE, "ww2_tex")
OUT_DESKTOP = os.path.join(ROOT, "public", "assets", "models", "kopitiam.glb")
OUT_MOBILE = os.path.join(ROOT, "public", "assets", "models", "kopitiam-mobile.glb")
OUT_BLEND = os.path.join(HERE, "kopitiam.blend")
PREV_DIR = os.path.join(ROOT, "docs", "previews", "kopitiam")
NODES_JSON = os.path.join(HERE, "kopitiam_nodes.json")

R = random.Random(1965)


# ======================================================================================
# Colours (sRGB 0..1 -> linear for the colour attribute)
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


WHITE = C(1, 1, 1)
CREAM = C(0.93, 0.90, 0.80)        # upper walls / soffit
JADE = C(0.60, 0.74, 0.66)         # 1960s dado green
PALEBLUE = C(0.74, 0.82, 0.86)
PILLAR = C(0.88, 0.86, 0.78)
CEIL = C(0.90, 0.89, 0.84)
TERRAZZO = C(0.86, 0.84, 0.78)
REDCEMENT = C(0.70, 0.50, 0.44)
ROAD = C(0.50, 0.49, 0.47)
KERB = C(0.66, 0.65, 0.62)
GRASS = C(0.42, 0.56, 0.30)
LEAF = C(0.30, 0.46, 0.24)
BARK = C(0.36, 0.29, 0.23)
TIMBER = C(0.56, 0.40, 0.27)
TIMBER_DARK = C(0.34, 0.24, 0.16)
PAINTED_WOOD = C(0.36, 0.52, 0.50)  # counter front: painted teal
IRON = C(0.16, 0.16, 0.17)
STEEL = C(0.62, 0.63, 0.64)
COPPER = C(0.72, 0.42, 0.26)
PORCELAIN = C(0.94, 0.93, 0.89)
RED = C(0.72, 0.16, 0.14)
FACADE = C(0.90, 0.88, 0.80)
FACADE_BAND = C(0.78, 0.84, 0.82)
TUBE = C(0.95, 0.97, 1.0)

# ======================================================================================
# Geometry builder (same scheme as build_ww2_street.py)
# ======================================================================================
MATS = ["M_Plaster", "M_Timber", "M_Floor", "M_Road", "M_Cloth", "M_Windows", "M_Details", "M_NowSigns",
        "M_Glass", "M_Metal", "M_Emissive", "M_Decal", "M_Screen", "M_Lacquer", "M_NowShop", "M_Far"]


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


def bucket(mat):
    g = BUCKETS.setdefault((STATE["group"], STATE["tier"]), {})
    if mat not in g:
        g[mat] = MB()
    return g[mat]


def emit(mat, wpts, uvs, col, smooth=False):
    b = bucket(mat)
    base = len(b.v)
    b.v.extend(wpts)
    b.f.append(tuple(range(base, base + len(wpts))))
    b.uv.append(list(uvs))
    b.col.append(col)
    b.sm.append(smooth)


def emit_indexed(mat, wverts, faces, uvs, col, smooth=True):
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


def face(mat, pts, col, uv=None, s=1.0, smooth=False):
    emit(mat, [tuple(p) for p in pts], uv if uv is not None else boxuv(pts, s), col, smooth)


def arect(r, W=1024.0):
    x0, y0, x1, y1 = r
    return [(x0 / W, 1 - y1 / W), (x1 / W, 1 - y1 / W), (x1 / W, 1 - y0 / W), (x0 / W, 1 - y0 / W)]


UV01 = [(0, 0), (1, 0), (1, 1), (0, 1)]


def box_faces(a, b):
    u0, v0, z0 = a
    u1, v1, z1 = b
    return {
        "-y": [(u0, v0, z0), (u1, v0, z0), (u1, v0, z1), (u0, v0, z1)],
        "+y": [(u1, v1, z0), (u0, v1, z0), (u0, v1, z1), (u1, v1, z1)],
        "-x": [(u0, v1, z0), (u0, v0, z0), (u0, v0, z1), (u0, v1, z1)],
        "+x": [(u1, v0, z0), (u1, v1, z0), (u1, v1, z1), (u1, v0, z1)],
        "+z": [(u0, v0, z1), (u1, v0, z1), (u1, v1, z1), (u0, v1, z1)],
        "-z": [(u0, v1, z0), (u1, v1, z0), (u1, v0, z0), (u0, v0, z0)],
    }


def box(mat, a, b, col, s=1.0, skip=(), uvs=None, cols=None, mats=None):
    a2 = (min(a[0], b[0]), min(a[1], b[1]), min(a[2], b[2]))
    b2 = (max(a[0], b[0]), max(a[1], b[1]), max(a[2], b[2]))
    for k, pts in box_faces(a2, b2).items():
        if k in skip:
            continue
        face((mats or {}).get(k, mat), pts, (cols or {}).get(k, col), uv=(uvs or {}).get(k), s=s)


def M_at(x, y, z, rz=0.0, rx=0.0, ry=0.0):
    return Matrix.Translation((x, y, z)) @ Matrix.Rotation(rz, 4, "Z") @ Matrix.Rotation(ry, 4, "Y") @ Matrix.Rotation(rx, 4, "X")


def mbox(M, mat, size, col, s=1.0, uvs=None, mats=None, cols=None, skip=()):
    sx, sy, sz = size[0] / 2, size[1] / 2, size[2] / 2
    for k, pts in box_faces((-sx, -sy, -sz), (sx, sy, sz)).items():
        if k in skip:
            continue
        uv = (uvs or {}).get(k) or boxuv(pts, s)
        emit((mats or {}).get(k, mat), [tuple(M @ Vector(p)) for p in pts], uv, (cols or {}).get(k, col))


def quad(mat, p0, p1, p2, p3, col=WHITE, uv=UV01):
    emit(mat, [tuple(p0), tuple(p1), tuple(p2), tuple(p3)], uv, col)


def wall_quad_y(mat, x0, x1, z0, z1, y, col, facing="-y", s=1.0, uv=None):
    """Vertical quad in the XZ plane at y, facing -y (towards the car park) or +y."""
    if facing == "-y":
        pts = [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)]
    else:
        pts = [(x1, y, z0), (x0, y, z0), (x0, y, z1), (x1, y, z1)]
    face(mat, pts, col, uv=uv, s=s)


def wall_quad_x(mat, y0, y1, z0, z1, x, col, facing="+x", s=1.0, uv=None):
    if facing == "+x":
        pts = [(x, y0, z0), (x, y1, z0), (x, y1, z1), (x, y0, z1)]
    else:
        pts = [(x, y1, z0), (x, y0, z0), (x, y0, z1), (x, y1, z1)]
    face(mat, pts, col, uv=uv, s=s)


def grid_floor(mat, x0, x1, y0, y1, z, col, s=1.0, cell=1.5, down=False, colfn=None):
    nx = max(1, int(round((x1 - x0) / cell)))
    ny = max(1, int(round((y1 - y0) / cell)))
    for i in range(nx):
        for j in range(ny):
            a, b = x0 + (x1 - x0) * i / nx, x0 + (x1 - x0) * (i + 1) / nx
            c, d = y0 + (y1 - y0) * j / ny, y0 + (y1 - y0) * (j + 1) / ny
            pts = [(a, c, z), (b, c, z), (b, d, z), (a, d, z)]
            if down:
                pts = pts[::-1]
            face(mat, pts, colfn((a + b) / 2, (c + d) / 2) if colfn else col, s=s)


def cyl(mat, c, r, h, n, col, caps=True, s=1.0, r_top=None, smooth=True, cap_col=None):
    rt = r if r_top is None else r_top
    verts = [(c[0] + math.cos(math.tau * i / n) * r, c[1] + math.sin(math.tau * i / n) * r, c[2]) for i in range(n)]
    verts += [(c[0] + math.cos(math.tau * i / n) * rt, c[1] + math.sin(math.tau * i / n) * rt, c[2] + h) for i in range(n)]
    faces, uvs = [], []
    circ = math.tau * max(r, rt)
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
        u0, u1 = i / n * circ / s, (i + 1) / n * circ / s
        uvs.append([(u0, 0), (u1, 0), (u1, h / s), (u0, h / s)])
    emit_indexed(mat, verts, faces, uvs, col, smooth=smooth)
    if caps:
        top = [verts[n + i] for i in range(n)]
        emit(mat, top, [(0.5 + 0.5 * math.cos(math.tau * i / n), 0.5 + 0.5 * math.sin(math.tau * i / n)) for i in range(n)], cap_col or col)
        emit(mat, [verts[i] for i in reversed(range(n))], [(0.5, 0.5)] * n, col)


def tube(mat, p0, p1, r, n, col, s=1.0, caps=False, smooth=True):
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


def sphere(mat, c, r, col, nu=8, nv=6, sz=1.0):
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
        uvs.append([(0, 0)] * 3)
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
        uvs.append([(0, 1)] * 3)
    emit_indexed(mat, verts, faces, uvs, col, smooth=True)


# ======================================================================================
# Registries: markers, colliders
# ======================================================================================
MARKERS = []     # (name, (x,y,z), facing (dx,dy) | (dx,dy,dz) | None, props)
COLLIDERS = []   # (name, (x0,y0,z0,x1,y1,z1), props)
_colcount = {}


def marker(name, pos, face_dir=(0, -1), props=None):
    MARKERS.append((name, tuple(pos), face_dir, props or {}))


def collider(name, a, b, props=None, unique=True):
    props = dict(props or {})
    g = STATE["group"]
    if g.startswith("THEN_"):
        props.setdefault("state", "then")
    elif g.startswith("NOW_"):
        props.setdefault("state", "now")
    x0, y0, z0 = [min(p, q) for p, q in zip(a, b)]
    x1, y1, z1 = [max(p, q) for p, q in zip(a, b)]
    if not unique:
        _colcount[name] = _colcount.get(name, 0) + 1
        name = f"{name}_{_colcount[name]}"
    COLLIDERS.append((name, (x0, y0, z0, x1, y1, z1), props))


def facing(frm, to):
    return (to[0] - frm[0], to[1] - frm[1])


# ======================================================================================
# Layout
# ======================================================================================
ZF = 0.15            # corridor + shop floor
ZS = 3.3             # ground-floor soffit (1st-floor slab underside)
STOREY = 2.8
STOREYS = 7          # "chit lau": seven storeys
Z_ROOF = ZS + (STOREYS - 1) * STOREY + 0.3
X0, X1 = -15.0, 15.0
YE = 0.0             # corridor outer edge (pillar line)
YF = 3.0             # shopfronts
YB = 12.0            # kopitiam back wall
YN = 6.5             # back of the (shallow) neighbour shops
BAYS = [-13.5, -9.0, -4.5, 0.0, 4.5, 9.0, 13.5]
KX0, KX1 = -4.5, 4.5
PIL = 0.22           # pillar half width
TABLES = [(-2.7, 7.4), (0.0, 7.4), (2.7, 7.4), (-2.7, 5.0), (0.0, 5.0), (2.7, 5.0)]   # T1..T6
STOOL_R = 0.64
TV = (3.75, 11.25, 2.2)   # TV sits on a high corner shelf (base centre)


# ---------------------------------------------------------------- block shell
def build_block():
    # corridor floor (red cement tiles) + kerb step down to the car park
    grid_floor("M_Floor", X0, X1, YE, YF, ZF, REDCEMENT, s=0.6, cell=1.5,
               colfn=lambda x, y: jitter(REDCEMENT, 0.05))
    face("M_Plaster", [(X0, YE, 0), (X1, YE, 0), (X1, YE, ZF), (X0, YE, ZF)], KERB)
    # soffit over the corridor and the whole ground floor
    grid_floor("M_Plaster", X0, X1, YE - 0.4, YF, ZS, CEIL, s=2.0, cell=3.0, down=True)
    # slab edge band facing the car park
    box("M_Plaster", (X0, YE - 0.45, ZS - 0.25), (X1, YE, ZS + 0.25), FACADE_BAND, skip=("+y",))
    # pillars along the corridor edge
    for x in BAYS + [X0 + 0.3, X1 - 0.3]:
        box("M_Plaster", (x - PIL, YE, ZF), (x + PIL, YE + 2 * PIL, ZS - 0.25), PILLAR, skip=("-z", "+z"))
        box("M_Plaster", (x - PIL - 0.03, YE - 0.03, ZF), (x + PIL + 0.03, YE + 2 * PIL + 0.03, ZF + 0.9),
            JADE, skip=("-z",))                                   # painted dado on the pillars
        collider("COL_Pillar", (x - PIL, YE, 0), (x + PIL, YE + 2 * PIL, 3.0), unique=False)
    # end walls
    for x, out, inn in ((X0, "-x", "+x"), (X1, "+x", "-x")):
        wall_quad_x("M_Plaster", YE - 0.45, YN + 6, 0, Z_ROOF, x, FACADE, facing=out, s=2.0)
        wall_quad_x("M_Plaster", YE, YF, ZF, ZS, x, CREAM, facing=inn, s=2.0)      # corridor ends
        collider("COL_End", (x - 0.3, YE, 0), (x + 0.3, YF, 3.0), unique=False)
    # blank shopfront walls on the part-bays at each end of the row
    for (xa, xb) in ((X0, BAYS[0]), (BAYS[-1], X1)):
        wall_quad_y("M_Plaster", xa, xb, ZF, ZS, YF, CREAM, s=2.0)
        collider("COL_EndBay", (xa, YF, 0), (xb, YF + 0.3, 3.0), unique=False)
    # upper storeys: slab bands, window strips, laundry-pole brackets
    for k in range(STOREYS - 1):
        z = ZS + k * STOREY
        # sill band
        wall_quad_y("M_Plaster", X0, X1, z + 0.25, z + 1.05, YE - 0.45, FACADE, s=2.0)
        # window strip: glass panes between piers
        for i in range(10):
            xa = X0 + i * 3.0
            wall_quad_y("M_Plaster", xa, xa + 0.5, z + 1.05, z + 2.35, YE - 0.45, FACADE, s=2.0)
            wall_quad_y("M_Glass", xa + 0.5, xa + 3.0, z + 1.05, z + 2.35, YE - 0.35, WHITE, s=1.25)
            box("M_Plaster", (xa + 0.5, YE - 0.45, z + 1.0), (xa + 3.0, YE - 0.35, z + 1.05), FACADE)
        wall_quad_y("M_Plaster", X0, X1, z + 2.35, z + STOREY + 0.25, YE - 0.45, FACADE_BAND if k % 2 else FACADE, s=2.0)
        # projecting slab lip + laundry pole holders
        box("M_Plaster", (X0, YE - 0.7, z + STOREY + 0.13), (X1, YE - 0.45, z + STOREY + 0.25), FACADE_BAND, skip=("+y",))
    # roof parapet
    box("M_Plaster", (X0, YE - 0.5, Z_ROOF), (X1, YN + 6, Z_ROOF + 0.9), FACADE, skip=("-z",))
    # interior top of the block (only seen from far away)
    face("M_Plaster", [(X0, YN + 6, 0), (X0, YN + 6, Z_ROOF), (X1, YN + 6, Z_ROOF), (X1, YN + 6, 0)], FACADE)


def build_laundry():
    """1960s laundry: bamboo poles pushed out of the flats' windows, clothes pegged on them."""
    cols = [C(0.9, 0.9, 0.86), C(0.55, 0.65, 0.78), C(0.82, 0.55, 0.5), C(0.9, 0.82, 0.6), C(0.6, 0.72, 0.62)]
    with GROUP("THEN_Laundry"):
        for k in range(STOREYS - 1):
            z = ZS + k * STOREY + 2.2
            for i in range(10):
                if R.random() < 0.45:
                    continue
                xa = X0 + i * 3.0 + R.uniform(0.8, 2.2)
                tube("M_Timber", (xa, YE - 0.3, z), (xa + R.uniform(-0.2, 0.2), YE - 1.9, z + 0.08), 0.025, 4, C(0.78, 0.68, 0.42), smooth=False)
                for j in range(R.randint(1, 3)):
                    t = 0.3 + 0.45 * j
                    px, py = xa, YE - 0.3 - 1.6 * t
                    c = R.choice(cols)
                    w, d = R.uniform(0.35, 0.6), R.uniform(0.4, 0.8)
                    for fa in (-1, 1):
                        pts = [(px - w / 2 * fa, py, z - d), (px + w / 2 * fa, py, z - d), (px + w / 2 * fa, py, z), (px - w / 2 * fa, py, z)]
                        face("M_Cloth", pts, c, s=0.5)


# ---------------------------------------------------------------- car park + surroundings
def build_outside():
    grid_floor("M_Road", -40, 40, -16, YE, 0.0, ROAD, s=4.0, cell=4.0)
    # painted parking bays
    for i in range(-5, 6):
        x = i * 2.6
        face("M_Plaster", [(x - 0.05, -6.5, 0.004), (x + 0.05, -6.5, 0.004), (x + 0.05, -1.5, 0.004), (x - 0.05, -1.5, 0.004)], C(0.9, 0.88, 0.8))
    # open drain + kerb along the far side, then a grass verge with rain trees
    box("M_Plaster", (-40, -16.6, -0.3), (40, -16.0, 0.0), C(0.45, 0.47, 0.42), skip=("-z", "-y", "+y"))
    grid_floor("M_Road", -40, 40, -40, -16.6, 0.02, GRASS, s=6.0, cell=8.0)
    # distant ground out to the skyline (seen past the east end of the block)
    for (xa, xb, ya, yb) in ((40, 700, -500, 500), (-700, -40, -500, 500), (-40, 40, -500, -40), (-40, 40, 12, 500)):
        face("M_Road", [(xa, ya, -0.02), (xb, ya, -0.02), (xb, yb, -0.02), (xa, yb, -0.02)], mul(GRASS, 0.9), s=6.0)
    for i, x in enumerate((-24, -13, -3, 8, 19, 30)):
        tree(x + R.uniform(-1.5, 1.5), -19 - R.uniform(0, 2), 1.0 + R.uniform(-0.15, 0.2), seed=i)
    for x in (-18, -6, 6, 18):
        lamp_post(x, -15.4)
    # neighbouring blocks: a ten-storey slab across the green, a seven-storey one to the side
    far_block(-45, 35, -44, 10, C(0.86, 0.84, 0.78))
    far_block(26, 60, -26, 7, C(0.84, 0.86, 0.82))


def tree(x, y, sc=1.0, seed=0):
    rr = random.Random(seed)
    tube("M_Timber", (x, y, 0), (x, y, 3.2 * sc), 0.22 * sc, 7, BARK)
    for k in range(3):
        a = k * 2.1 + rr.uniform(0, 1)
        tube("M_Timber", (x, y, 2.7 * sc), (x + math.cos(a) * 2.2 * sc, y + math.sin(a) * 2.2 * sc, 4.4 * sc), 0.11 * sc, 5, BARK)
    for k in range(7):
        a = rr.uniform(0, math.tau)
        r = rr.uniform(0.8, 3.0) * sc
        sphere("M_Cloth", (x + math.cos(a) * r, y + math.sin(a) * r, (4.6 + rr.uniform(-0.3, 0.7)) * sc),
               rr.uniform(1.6, 2.3) * sc, jitter(LEAF, 0.12, rr), nu=8, nv=5, sz=0.55)


def lamp_post(x, y):
    tube("M_Metal", (x, y, 0), (x, y, 6.5), 0.07, 6, C(0.55, 0.56, 0.55))
    tube("M_Metal", (x, y, 6.4), (x, y + 1.2, 6.7), 0.05, 5, C(0.55, 0.56, 0.55))
    box("M_Metal", (x - 0.14, y + 1.05, 6.55), (x + 0.14, y + 1.6, 6.7), C(0.45, 0.46, 0.45))


def far_block(xa, xb, y, storeys, tint):
    h = storeys * STOREY + 3.0
    box("M_Plaster", (xa, y - 10, 0), (xb, y, h), tint, s=4.0, skip=("-z", "-y"))
    for k in range(storeys):
        z = 3.0 + k * STOREY
        wall_quad_y("M_Glass", xa + 1, xb - 1, z + 0.9, z + 2.0, y + 0.02, mul(WHITE, 0.8), facing="+y", s=1.25)
        box("M_Plaster", (xa, y, z + 2.2), (xb, y + 0.6, z + 2.3), mul(tint, 0.95), skip=("-y",))


def far_block_x(ya, yb, x, storeys, tint):
    h = storeys * STOREY + 3.0
    box("M_Plaster", (x - 30, ya, 0), (x, yb, h), tint, s=4.0, skip=("-z",))
    for k in range(storeys):
        z = 3.0 + k * STOREY
        wall_quad_x("M_Glass", ya + 0.5, yb - 0.5, z + 0.9, z + 2.0, x + 0.02, mul(WHITE, 0.8), facing="+x", s=1.25)


# ---------------------------------------------------------------- neighbour shops
SHOPS = [  # x0, x1, kind
    (-13.5, -9.0, "tailor"), (-9.0, -4.5, "provision"), (4.5, 9.0, "bookshop"), (9.0, 13.5, "barber"),
]
WIN_ATLAS = {k: (i % 4 * 256 + 4, i // 4 * 512 + 4, i % 4 * 256 + 252, i // 4 * 512 + 508) for i, k in enumerate(
    ["jal_closed", "jal_open", "french_taped", "panel", "pintu", "blackout", "door", "open"])}
DET = {k: (i % 4 * 256 + 2, i // 4 * 256 + 2, i % 4 * 256 + 254, i // 4 * 256 + 254) for i, k in enumerate(
    ["fanlight", "barred", "tiles", "marble", "planks", "chick", "vent", "drawers", "cloths", "provisions",
     "crate", "checked", "suitcase", "menu", "clock", "pawnscreen"])}


def shop_piers():
    """Masonry piers where the party walls meet the shopfront (no paper-thin seams between units)."""
    for x in (-13.5, -9.0, -4.5, 4.5, 9.0, 13.5):
        box("M_Plaster", (x - 0.13, YF - 0.03, ZF), (x + 0.13, YF + 0.3, ZS), CREAM, s=2.0, skip=("-z", "+z"))
        box("M_Plaster", (x - 0.14, YF - 0.04, ZF), (x + 0.14, YF + 0.31, ZF + 0.9), JADE, s=1.5, skip=("-z",))
        collider("COL_Pier", (x - 0.14, YF - 0.04, 0), (x + 0.14, YF + 0.31, 3.0), unique=False)


def build_shops():
    shop_piers()
    # party walls between units (interior faces), back walls, shop floors/ceilings
    for (x0, x1, kind) in SHOPS:
        grid_floor("M_Floor", x0, x1, YF, YN, ZF, jitter(TERRAZZO, 0.04), s=0.6, cell=1.5)
        grid_floor("M_Plaster", x0, x1, YF, YN, ZS - 0.001, CEIL, s=2.0, cell=2.25, down=True)
        wall_quad_y("M_Plaster", x0, x1, ZF, ZS, YN, CREAM, facing="-y", s=2.0)
        wall_quad_x("M_Plaster", YF, YN, ZF, ZS, x0 + 0.01, CREAM, facing="+x", s=2.0)
        wall_quad_x("M_Plaster", YF, YN, ZF, ZS, x1 - 0.01, CREAM, facing="-x", s=2.0)
        shop_contents(x0, x1, kind)
        # 1965: open front with folding timber doors pushed back; present day: glass shopfront
        with GROUP("THEN_Shops"):
            for xs in (x0 + 0.15, x1 - 0.55):
                wall_quad_y("M_Windows", xs, xs + 0.4, ZF, ZF + 2.5, YF + 0.02, WHITE, uv=arect(WIN_ATLAS["door"]))
            box("M_Timber", (x0, YF, ZF + 2.5), (x1, YF + 0.12, ZS), TIMBER_DARK)
            # signboard (runtime text)
        with GROUP("DECAL_Sign_" + kind.capitalize()):
            quad("M_Decal", (x0 + 0.4, YF - 0.02, ZF + 2.55), (x1 - 0.4, YF - 0.02, ZF + 2.55),
                 (x1 - 0.4, YF - 0.02, ZS - 0.05), (x0 + 0.4, YF - 0.02, ZS - 0.05))
        with GROUP("NOW_Shops"):
            now_shopfront(x0, x1, kind)
        with GROUP("DECAL_NowSign_" + kind.capitalize()):
            quad("M_Decal", (x0 + 0.3, YF - 0.355, ZF + 2.62), (x1 - 0.3, YF - 0.355, ZF + 2.62),
                 (x1 - 0.3, YF - 0.355, ZS - 0.06), (x0 + 0.3, YF - 0.355, ZS - 0.06))
        collider("COL_Shopfront", (x0, YF, 0), (x1, YF + 0.3, 3.0), unique=False)


def shop_contents(x0, x1, kind):
    cx = (x0 + x1) / 2
    with GROUP("THEN_Shops"):
        if kind == "bookshop":
            for xs in (x0 + 0.2, cx + 0.1):
                wall_quad_y("M_Details", xs, xs + 1.9, ZF + 0.3, ZF + 2.3, YN - 0.02, WHITE, uv=arect(DET["drawers"]))
                box("M_Timber", (xs, YN - 0.45, ZF), (xs + 1.9, YN - 0.02, ZF + 0.3), TIMBER_DARK)
            # a low table of books and exercise books at the front
            box("M_Timber", (cx - 1.0, YF + 0.4, ZF), (cx + 1.0, YF + 1.2, ZF + 0.8), TIMBER)
            for i in range(6):
                bx = cx - 0.85 + i * 0.3
                box("M_Plaster", (bx, YF + 0.5, ZF + 0.8), (bx + 0.24, YF + 0.85, ZF + 0.8 + R.uniform(0.03, 0.12)),
                    R.choice([C(0.8, 0.3, 0.25), C(0.3, 0.45, 0.7), C(0.9, 0.85, 0.7), C(0.35, 0.6, 0.4)]))
        elif kind == "provision":
            wall_quad_y("M_Details", x0 + 0.3, x1 - 0.3, ZF + 0.4, ZF + 2.4, YN - 0.02, WHITE, uv=arect(DET["provisions"]))
            for i in range(5):
                sphere("M_Cloth", (x0 + 0.7 + i * 0.75, YF + 0.7, ZF + 0.3), 0.3, C(0.9, 0.86, 0.76), nu=8, nv=5, sz=1.1)
        elif kind == "tailor":
            wall_quad_y("M_Details", x0 + 0.3, x1 - 0.3, ZF + 0.5, ZF + 2.3, YN - 0.02, WHITE, uv=arect(DET["cloths"]))
            box("M_Timber", (cx - 1.1, YF + 1.0, ZF), (cx + 1.1, YF + 1.8, ZF + 0.85), TIMBER)
            cyl("M_Cloth", (cx - 1.4, YF + 1.2, ZF), 0.18, 1.35, 8, C(0.85, 0.83, 0.78))    # dress form
        elif kind == "barber":
            wall_quad_y("M_Glass", x0 + 0.6, x1 - 0.6, ZF + 1.0, ZF + 2.2, YN - 0.02, C(0.9, 0.95, 1.0), s=1.0)  # mirror
            box("M_Timber", (cx - 0.35, YF + 1.6, ZF), (cx + 0.35, YF + 2.2, ZF + 0.5), C(0.7, 0.2, 0.18))
            box("M_Timber", (cx - 0.35, YF + 2.05, ZF + 0.5), (cx + 0.35, YF + 2.2, ZF + 1.2), C(0.7, 0.2, 0.18))
            # barber's pole by the pillar
            for k in range(8):
                cyl("M_Plaster", (x0 + 0.35, YF - 0.25, ZF + 1.0 + k * 0.12), 0.07, 0.12, 8,
                    [C(0.85, 0.15, 0.12), WHITE, C(0.2, 0.3, 0.7), WHITE][k % 4], caps=(k == 7))


# ---------------------------------------------------------------- the kopitiam
def build_kopitiam():
    # shell: floor, walls with a painted green dado, ceiling
    grid_floor("M_Floor", KX0, KX1, YF, YB, ZF, TERRAZZO, s=0.5, cell=1.5,
               colfn=lambda x, y: jitter(TERRAZZO, 0.03))
    for (x, fa) in ((KX0 + 0.01, "+x"), (KX1 - 0.01, "-x")):
        wall_quad_x("M_Plaster", YF, YB, ZF, ZF + 1.3, x, JADE, facing=fa, s=1.5)
        wall_quad_x("M_Plaster", YF, YB, ZF + 1.3, ZS, x, CREAM, facing=fa, s=2.0)
        box("M_Timber", (x - 0.02, YF, ZF + 1.28), (x + 0.02, YB, ZF + 1.34), TIMBER_DARK)
    # back wall with a doorway to the kitchen (x -0.15..0.85)
    for (xa, xb) in ((KX0, -0.15), (0.85, KX1)):
        wall_quad_y("M_Plaster", xa, xb, ZF, ZF + 1.3, YB - 0.01, JADE, facing="-y", s=1.5)
        wall_quad_y("M_Plaster", xa, xb, ZF + 1.3, ZS, YB - 0.01, CREAM, facing="-y", s=2.0)
        box("M_Timber", (xa, YB - 0.03, ZF + 1.28), (xb, YB, ZF + 1.34), TIMBER_DARK)
    wall_quad_y("M_Plaster", -0.15, 0.85, ZF + 2.2, ZS, YB - 0.01, CREAM, facing="-y", s=2.0)
    # dim kitchen behind the doorway (faces point inwards, so it reads as a room from the shop)
    kd = C(0.24, 0.21, 0.18)
    kx0, kx1, ky1 = -0.9, 1.6, YB + 1.6
    grid_floor("M_Floor", kx0, kx1, YB, ky1, ZF, mul(TERRAZZO, 0.45), s=0.5, cell=1.0)
    wall_quad_y("M_Plaster", kx0, kx1, ZF, ZS, ky1, kd, facing="-y", s=2.0)
    wall_quad_x("M_Plaster", YB, ky1, ZF, ZS, kx0, kd, facing="+x", s=2.0)
    wall_quad_x("M_Plaster", YB, ky1, ZF, ZS, kx1, kd, facing="-x", s=2.0)
    grid_floor("M_Plaster", kx0, kx1, YB, ky1, ZS - 0.001, mul(kd, 0.8), s=2.0, cell=1.0, down=True)
    for (xa, xb) in ((kx0, -0.15), (0.85, kx1)):                      # back of the shop wall, seen from inside
        wall_quad_y("M_Plaster", xa, xb, ZF, ZS, YB + 0.01, kd, facing="+y", s=2.0)
    wall_quad_y("M_Plaster", -0.15, 0.85, ZF + 2.2, ZS, YB + 0.01, kd, facing="+y", s=2.0)
    # a charcoal stove, a sink and a shelf of tins, just visible past the curtain
    box("M_Plaster", (0.9, ky1 - 0.6, ZF), (1.55, ky1 - 0.02, ZF + 0.85), C(0.32, 0.3, 0.28))
    cyl("M_Metal", (1.22, ky1 - 0.31, ZF + 0.85), 0.2, 0.25, 12, C(0.3, 0.3, 0.3))
    box("M_Plaster", (-0.85, ky1 - 0.5, ZF), (-0.2, ky1 - 0.02, ZF + 0.8), C(0.55, 0.55, 0.52))
    box("M_Timber", (-0.6, ky1 - 0.3, ZF + 1.6), (1.4, ky1 - 0.02, ZF + 1.64), TIMBER_DARK)
    for k in range(6):
        cyl("M_Metal", (-0.45 + k * 0.32, ky1 - 0.16, ZF + 1.64), 0.07, 0.18, 8, C(0.55, 0.5, 0.4))
    collider("COL_Kitchen", (-0.15, YB, 0), (0.85, YB + 0.3, 3.0))
    with GROUP("THEN_Kopitiam"):
        face("M_Cloth", [(-0.12, YB - 0.04, ZF + 0.9), (0.4, YB - 0.04, ZF + 0.9), (0.4, YB - 0.04, ZF + 2.15), (-0.12, YB - 0.04, ZF + 2.15)],
             C(0.35, 0.5, 0.62), s=0.5)
    grid_floor("M_Plaster", KX0, KX1, YF, YB, ZS - 0.001, CEIL, s=2.0, cell=3.0, down=True)
    # front: shop fascia over the open front, folding timber doors pushed back against the side walls
    box("M_Plaster", (KX0, YF - 0.05, ZF + 2.6), (KX1, YF + 0.15, ZS), CREAM, skip=("+z",))
    with GROUP("DECAL_ShopSign"):
        quad("M_Decal", (KX0 + 0.5, YF - 0.07, ZF + 2.62), (KX1 - 0.5, YF - 0.07, ZF + 2.62),
             (KX1 - 0.5, YF - 0.07, ZS - 0.04), (KX0 + 0.5, YF - 0.07, ZS - 0.04))
    with GROUP("THEN_Kopitiam"):
        for (xa, sgn) in ((KX0 + 0.15, 1), (KX1 - 0.55, -1)):
            for k in range(3):
                x = xa + sgn * k * 0.04 if sgn > 0 else xa - k * 0.04
                wall_quad_y("M_Windows", x, x + 0.4, ZF, ZF + 2.5, YF + 0.05 + k * 0.03, WHITE, uv=arect(WIN_ATLAS["door"]))
    collider("COL_Kopi_WallW", (KX0 - 0.3, YF, 0), (KX0, YB, 3.0))
    collider("COL_Kopi_WallE", (KX1, YF, 0), (KX1 + 0.3, YB, 3.0))
    collider("COL_Kopi_Back", (KX0, YB, 0), (KX1, YB + 0.3, 3.0))
    with GROUP("THEN_Kopitiam"):
        kopitiam_counter()
        kopitiam_tables()
        kopitiam_walls()
        kopitiam_ceiling()
        kopitiam_tv()
    with GROUP("NOW_Kopitiam"):
        # present day: an open-fronted minimart, roller shutters up, goods spilling into the corridor
        now_minimart()
    with GROUP("DECAL_NowSign"):
        quad("M_Decal", (KX0 + 0.5, YF - 0.355, ZF + 2.62), (KX1 - 0.5, YF - 0.355, ZF + 2.62),
             (KX1 - 0.5, YF - 0.355, ZS - 0.06), (KX0 + 0.5, YF - 0.355, ZS - 0.06))


def kopitiam_counter():
    # L-shaped counter: long run along y = 9.2..9.9 from the west wall to x = 0.3
    cx0, cx1, cy0, cy1 = KX0 + 0.05, 0.3, 9.2, 9.9
    box("M_Timber", (cx0, cy0, ZF), (cx1, cy1, ZF + 0.95), PAINTED_WOOD, s=1.0)
    box("M_Timber", (cx0, cy0 - 0.02, ZF), (cx1, cy0, ZF + 0.12), TIMBER_DARK)            # kick board
    box("M_Details", (cx0 - 0.03, cy0 - 0.05, ZF + 0.95), (cx1 + 0.05, cy1 + 0.03, ZF + 1.0), WHITE,
        uvs={"+z": arect(DET["marble"])}, mats={k: "M_Timber" for k in ("-y", "+y", "-x", "+x", "-z")},
        cols={k: TIMBER_DARK for k in ("-y", "+y", "-x", "+x", "-z")})
    collider("COL_Counter", (KX0, cy0 - 0.05, 0), (cx1 + 0.08, YB, 1.3))
    top = ZF + 1.0
    # glass cabinet of biscuits / kaya toast at the west end
    box("M_Glass", (cx0 + 0.1, cy0 + 0.05, top), (cx0 + 1.2, cy1 - 0.05, top + 0.45), C(0.9, 0.95, 0.95), s=0.5)
    for i in range(4):
        cyl("M_Metal", (cx0 + 0.25 + i * 0.26, cy0 + 0.35, top), 0.09, 0.22, 8, C(0.6, 0.68, 0.7), cap_col=RED)
    # the money tin + the radio on the counter
    cyl("M_Metal", (-1.4, cy0 + 0.35, top), 0.09, 0.12, 10, C(0.72, 0.62, 0.38))
    marker("SNAP_MoneyTin", (-1.4, cy0 + 0.35, top + 0.1), (0, -1))
    mbox(M_at(-0.35, cy0 + 0.4, top + 0.13, 0.25), "M_Timber", (0.42, 0.2, 0.26), TIMBER, mats={"-y": "M_Details"},
         uvs={"-y": arect(DET["vent"])})
    tube("M_Metal", (-0.2, cy0 + 0.45, top + 0.26), (-0.05, cy0 + 0.5, top + 0.62), 0.006, 3, STEEL, smooth=False)
    marker("RADIO", (-0.35, cy0 + 0.4, top + 0.13), (0, -1))
    # cups stacked on a tray ready for Sparky
    for i in range(6):
        cyl("M_Plaster", (-2.3 + (i % 3) * 0.12, cy0 + 0.25 + (i // 3) * 0.12, top), 0.045, 0.08, 8, PORCELAIN)
    marker("COUNTER_Cup", (-1.9, cy0 + 0.25, top), (0, -1))
    marker("COUNTER_Serve", (-1.9, cy0 - 0.75, ZF), (0, 1))          # where Sparky stands to make a drink
    # behind the counter: the charcoal stove + copper urn, kettles, shelves, Rediffusion box, order board
    box("M_Plaster", (KX0 + 0.15, 11.1, ZF), (KX0 + 1.9, YB - 0.02, ZF + 0.8), C(0.62, 0.42, 0.34), s=1.0)
    box("M_Plaster", (KX0 + 0.1, 11.05, ZF + 0.8), (KX0 + 1.95, YB - 0.02, ZF + 0.86), C(0.5, 0.5, 0.48))
    cyl("M_Metal", (KX0 + 0.7, 11.55, ZF + 0.86), 0.3, 0.6, 12, COPPER, r_top=0.28)
    cyl("M_Metal", (KX0 + 0.7, 11.55, ZF + 1.46), 0.28, 0.1, 12, mul(COPPER, 0.85), r_top=0.1)
    for (kx, ky) in ((KX0 + 1.4, 11.35), (KX0 + 1.65, 11.75)):
        cyl("M_Metal", (kx, ky, ZF + 0.86), 0.12, 0.22, 8, STEEL, r_top=0.08)
        tube("M_Metal", (kx, ky - 0.1, ZF + 0.98), (kx, ky - 0.26, ZF + 1.12), 0.016, 4, STEEL)
    for k in range(2):
        z = ZF + 1.45 + k * 0.5
        box("M_Timber", (-2.3, YB - 0.35, z), (0.0, YB - 0.02, z + 0.04), TIMBER_DARK)
    wall_quad_y("M_Details", -2.25, -0.05, ZF + 1.49, ZF + 2.4, YB - 0.03, WHITE, uv=arect(DET["provisions"]))
    with GROUP("DECAL_OrderBoard"):
        quad("M_Decal", (-2.35, YB - 0.04, ZF + 2.45), (-0.05, YB - 0.04, ZF + 2.45),
             (-0.05, YB - 0.04, ZF + 3.08), (-2.35, YB - 0.04, ZF + 3.08))
    box("M_Timber", (-2.42, YB - 0.05, ZF + 2.4), (0.02, YB - 0.02, ZF + 3.13), TIMBER_DARK, skip=("-y",))
    # Rediffusion box, high on the wall: wooden cabinet with a woven speaker grille
    mbox(M_at(KX0 + 1.1, YB - 0.14, ZF + 2.6), "M_Timber", (0.5, 0.22, 0.38), TIMBER, mats={"-y": "M_Details"},
         uvs={"-y": arect(DET["vent"])})
    marker("SNAP_Rediffusion", (KX0 + 1.1, YB - 0.3, ZF + 2.6), (0, -1))
    marker("NPC_Boon", (-1.8, 10.6, ZF), (0, -1))
    marker("NPC_Farid", (0.9, 9.35, ZF), (-1, -0.4))


def stool(x, y, col=TIMBER):
    cyl("M_Timber", (x, y, ZF + 0.42), 0.17, 0.04, 10, col)
    for k in range(3):
        a = k * math.tau / 3 + 0.4
        tube("M_Timber", (x + math.cos(a) * 0.1, y + math.sin(a) * 0.1, ZF + 0.42), (x + math.cos(a) * 0.16, y + math.sin(a) * 0.16, ZF), 0.017, 4, mul(col, 0.8), smooth=False)


def kopitiam_tables():
    for ti, (x, y) in enumerate(TABLES):
        n = ti + 1
        cyl("M_Metal", (x, y, ZF), 0.24, 0.03, 12, IRON)
        cyl("M_Metal", (x, y, ZF + 0.03), 0.04, 0.66, 8, IRON)
        cyl("M_Plaster", (x, y, ZF + 0.69), 0.38, 0.05, 20, C(0.88, 0.87, 0.84), caps=False)
        top = [(x + math.cos(math.tau * i / 20) * 0.38, y + math.sin(math.tau * i / 20) * 0.38, ZF + 0.74) for i in range(20)]
        u0, v0, u1, v1 = arect(DET["marble"])[0][0], arect(DET["marble"])[0][1], arect(DET["marble"])[2][0], arect(DET["marble"])[2][1]
        emit("M_Details", top, [(u0 + (u1 - u0) * (0.5 + 0.5 * math.cos(math.tau * i / 20)), v0 + (v1 - v0) * (0.5 + 0.5 * math.sin(math.tau * i / 20))) for i in range(20)], WHITE)
        marker(f"TABLE_T{n}", (x, y, ZF + 0.74), (0, -1))
        collider(f"COL_Table_T{n}", (x - 0.42, y - 0.42, 0), (x + 0.42, y + 0.42, 1.0))
        for si, a_deg in enumerate((225, 315, 45, 135)):
            a = math.radians(a_deg)
            sx, sy = x + math.cos(a) * STOOL_R, y + math.sin(a) * STOOL_R
            stool(sx, sy, jitter(TIMBER, 0.08))
            marker(f"SEAT_T{n}_{'abcd'[si]}", (sx, sy, ZF), facing((sx, sy), (x, y)), {"seat_height": 0.46})
        with DETAIL():
            for k in range(R.randint(0, 2)):
                a = R.uniform(0, 6.28)
                cyl("M_Plaster", (x + math.cos(a) * 0.18, y + math.sin(a) * 0.18, ZF + 0.74), 0.045, 0.08, 8, PORCELAIN)
    # a long bench at the back of the room, between the tables and the family wall, facing the TV corner
    bx0, bx1, by = 1.4, 3.2, 9.4
    box("M_Timber", (bx0, by - 0.18, ZF + 0.42), (bx1, by + 0.18, ZF + 0.46), TIMBER)
    for bx in (bx0 + 0.1, bx1 - 0.14):
        box("M_Timber", (bx, by - 0.15, ZF), (bx + 0.04, by + 0.15, ZF + 0.42), TIMBER_DARK)
    collider("COL_Bench", (bx0, by - 0.2, 0), (bx1, by + 0.2, 0.5))
    marker("BENCH_1", (1.95, by + 0.02, ZF), (0, 1), {"seat_height": 0.46})
    marker("BENCH_2", (2.65, by + 0.02, ZF), (0, 1), {"seat_height": 0.46})


def kopitiam_walls():
    # the family wall (east of the kitchen door): Ah Ma's portrait, Papa's slot, and the 9 August item
    for (name, x0, x1) in (("DECAL_Portrait_AhMa", 1.25, 1.85), ("DECAL_Portrait_Papa", 2.05, 2.65)):
        box("M_Timber", (x0 - 0.05, YB - 0.05, ZF + 1.95), (x1 + 0.05, YB - 0.02, ZF + 2.75), TIMBER_DARK, skip=("+y",))
        with GROUP(name):
            quad("M_Decal", (x0, YB - 0.055, ZF + 2.0), (x1, YB - 0.055, ZF + 2.0), (x1, YB - 0.055, ZF + 2.7), (x0, YB - 0.055, ZF + 2.7))
    # red altar shelf with a small emissive oil lamp above the portraits
    box("M_Timber", (1.15, YB - 0.3, ZF + 2.82), (2.75, YB - 0.02, ZF + 2.87), RED)
    sphere("M_Emissive", (1.95, YB - 0.16, ZF + 2.93), 0.04, C(1.0, 0.35, 0.2), nu=6, nv=4)
    # wall choice slots (each its own node; code shows the one the player picks)
    slots = {"WALL_Newspaper": (1.3, 2.2, 1.05, 1.85), "WALL_Flag": (1.2, 2.5, 1.1, 1.85),
             "WALL_Sign": (1.1, 2.7, 1.25, 1.75), "WALL_Calendar": (1.5, 2.05, 1.05, 1.8)}
    for name, (x0, x1, z0, z1) in slots.items():
        with GROUP(name):
            quad("M_Decal", (x0, YB - 0.06, ZF + z0), (x1, YB - 0.06, ZF + z0), (x1, YB - 0.06, ZF + z1), (x0, YB - 0.06, ZF + z1))
    marker("WALL_Focus", (1.9, YB - 0.1, ZF + 1.8), (0, -1))
    # right of the family wall, under the TV shelf: a congratulations mirror from the shop's opening
    # (gold lettering, red cloth) and a coffee supplier's 1965 calendar poster (runtime text)
    mx0, mx1, mz0, mz1 = 2.92, 3.78, ZF + 1.42, ZF + 1.97
    box("M_Metal", (mx0 - 0.05, YB - 0.05, mz0 - 0.05), (mx1 + 0.05, YB - 0.02, mz1 + 0.05), C(0.72, 0.58, 0.3), skip=("+y",))
    with GROUP("DECAL_Mirror"):
        quad("M_Decal", (mx0, YB - 0.055, mz0), (mx1, YB - 0.055, mz0), (mx1, YB - 0.055, mz1), (mx0, YB - 0.055, mz1))
    box("M_Cloth", (mx0 - 0.02, YB - 0.075, mz1 - 0.06), (mx1 + 0.02, YB - 0.06, mz1 + 0.02), RED)
    for sx in (mx0 + 0.02, mx1 - 0.02):
        sphere("M_Cloth", (sx, YB - 0.085, mz1 - 0.02), 0.035, RED, nu=6, nv=4)
    with GROUP("DECAL_Poster"):
        px0, px1, pz0, pz1 = 4.0, 4.42, ZF + 1.38, ZF + 1.97
        quad("M_Decal", (px0, YB - 0.04, pz0), (px1, YB - 0.04, pz0), (px1, YB - 0.04, pz1), (px0, YB - 0.04, pz1))
    tube("M_Timber", (4.0, YB - 0.045, ZF + 1.975), (4.42, YB - 0.045, ZF + 1.975), 0.008, 4, TIMBER_DARK, caps=True)
    # the 1965 calendar near the counter
    with GROUP("DECAL_Calendar"):
        quad("M_Decal", (-3.95, YB - 0.04, ZF + 1.75), (-3.45, YB - 0.04, ZF + 1.75), (-3.45, YB - 0.04, ZF + 2.45), (-3.95, YB - 0.04, ZF + 2.45))
    # a wall clock over the doorway
    cyl("M_Timber", (0.35, YB - 0.05, ZF + 2.55), 0.16, 0.04, 16, TIMBER_DARK)
    # posters / notices on the west wall (runtime text)
    with GROUP("DECAL_Notice"):
        x = KX0 + 0.02
        quad("M_Decal", (x, 5.2, ZF + 1.55), (x, 6.1, ZF + 1.55), (x, 6.1, ZF + 2.55), (x, 5.2, ZF + 2.55))


def kopitiam_ceiling():
    for i, (fx, fy) in enumerate(((-1.6, 6.3), (1.6, 6.3))):
        tube("M_Metal", (fx, fy, ZS), (fx, fy, ZS - 0.55), 0.018, 5, IRON)
        with GROUP(f"FAN_{i + 1}"):
            cyl("M_Metal", (fx, fy, ZS - 0.68), 0.11, 0.13, 10, C(0.35, 0.42, 0.38))
            for k in range(3):
                a = k * math.tau / 3 + 0.3 * i
                mbox(M_at(fx + math.cos(a) * 0.45, fy + math.sin(a) * 0.45, ZS - 0.62, a), "M_Metal", (0.7, 0.13, 0.012), C(0.4, 0.46, 0.42))
        marker(f"FAN_{i + 1}_Axis", (fx, fy, ZS - 0.62), None)
    for (lx, ly) in ((-2.6, 4.4), (2.6, 4.4), (-2.6, 8.4), (2.6, 8.4), (0, 10.6)):
        box("M_Metal", (lx - 0.62, ly - 0.05, ZS - 0.06), (lx + 0.62, ly + 0.05, ZS), C(0.85, 0.85, 0.82))
        tube("M_Emissive", (lx - 0.58, ly, ZS - 0.08), (lx + 0.58, ly, ZS - 0.08), 0.018, 6, TUBE, caps=True)
        marker("LAMP", (lx, ly, ZS - 0.1), None)


def rrect(cx, cz, w, h, r, seg=4):
    """Rounded rectangle in a local (x, z) plane, counter-clockwise seen from -y (the front)."""
    out = []
    for sx, sz, a0 in ((1, -1, -90), (1, 1, 0), (-1, 1, 90), (-1, -1, 180)):
        for k in range(seg + 1):
            a = math.radians(a0 + 90 * k / seg)
            out.append((cx + sx * (w / 2 - r) + r * math.cos(a), cz + sz * (h / 2 - r) + r * math.sin(a)))
    return out


def extrude(M, mat, loop, y0, y1, col, front=True, back=True, inward=False, loop1=None, s=0.5):
    """Prism along local +y from y0 (front) to y1, smooth-shaded sides; loop1 tapers the back."""
    n = len(loop)
    loop1 = loop1 or loop
    verts = [tuple(M @ Vector((x, y0, z))) for x, z in loop] + [tuple(M @ Vector((x, y1, z))) for x, z in loop1]
    faces, uvs = [], []
    for i in range(n):
        j = (i + 1) % n
        f = (i, j, n + j, n + i) if inward else (j, i, n + i, n + j)
        faces.append(f)
        uvs.append(boxuv([verts[k] for k in f], s))
    emit_indexed(mat, verts, faces, uvs, col, smooth=True)
    if front:
        pts = verts[:n]
        emit(mat, pts, boxuv(pts, s), col)
    if back:
        pts = verts[n:][::-1]
        emit(mat, pts, boxuv(pts, s), col)


def ring(M, mat, outer, inner, y, col):
    """Flat frame between two loops of equal length (facing -y)."""
    n = len(outer)
    for i in range(n):
        j = (i + 1) % n
        pts = [tuple(M @ Vector((x, y, z))) for x, z in (outer[i], outer[j], inner[j], inner[i])]
        emit(mat, pts, boxuv(pts, 0.5), col)


TV_WALNUT = C(0.42, 0.25, 0.14)
TV_BAKELITE = C(0.16, 0.11, 0.08)
TV_GOLD = C(0.80, 0.68, 0.44)
TV_GRILLE = C(0.78, 0.70, 0.55)


def kopitiam_tv():
    """A 1960s table television (walnut cabinet, curved screen behind a gold mask, speaker grille,
    two bakelite knobs, rabbit-ear aerial on a lace doily) on a corner shelf with wooden brackets."""
    x, y, z = TV
    d = Vector((-0.72, -1.0, 0.0)).normalized()       # the screen faces the room (front-west)
    t = Vector((-d.y, d.x, 0.0))
    # corner shelf: front edge square to the set, ends clipped so it stays in the corner
    tx, ty = x + 0.2, y + 0.2                         # the set is tucked towards the corner
    F = Vector((tx, ty, 0)) + d * 0.26
    wall_y, wall_x = YB - 0.02, KX1 - 0.02
    xa, yb_ = 3.2, 10.9
    a = F + t * ((xa - F.x) / t.x)                    # front edge meets the clip at x = 3.2
    b = F + t * ((yb_ - F.y) / t.y)                   # ... and at y = 10.9
    poly = [(xa, wall_y), (xa, a.y), (b.x, b.y), (wall_x, yb_), (wall_x, wall_y)]
    cx_ = sum(p_[0] for p_ in poly) / len(poly)
    cy_ = sum(p_[1] for p_ in poly) / len(poly)
    top = [(px, py, z) for px, py in poly]
    bot = [(px, py, z - 0.045) for px, py in poly]
    face("M_Timber", top if newell(top)[2] > 0 else top[::-1], TIMBER_DARK)
    face("M_Timber", bot if newell(bot)[2] < 0 else bot[::-1], TIMBER_DARK)
    for i in range(len(poly)):
        p0, p1 = top[i], top[(i + 1) % len(poly)]
        q0, q1 = bot[i], bot[(i + 1) % len(poly)]
        side = [q0, q1, p1, p0]
        nrm = newell(side)
        out = ((p0[0] + p1[0]) / 2 - cx_, (p0[1] + p1[1]) / 2 - cy_)
        face("M_Timber", side if nrm[0] * out[0] + nrm[1] * out[1] > 0 else side[::-1], TIMBER_DARK)
    tube("M_Timber", (a.x + d.x * 0.012, a.y + d.y * 0.012, z - 0.012), (b.x + d.x * 0.012, b.y + d.y * 0.012, z - 0.012),
         0.022, 6, TIMBER, caps=True)
    # two wooden knee brackets under the shelf, one on each wall
    for (p, q) in (((wall_x - 0.55, wall_y), (wall_x - 0.55, wall_y - 0.42)), ((wall_x, wall_y - 0.7), (wall_x - 0.42, wall_y - 0.7))):
        pts = [(p[0], p[1], z - 0.045), (q[0], q[1], z - 0.045), (p[0], p[1], z - 0.5)]
        for off in (-0.018, 0.018):
            dx, dy = (off, 0) if p[1] != q[1] else (0, off)
            tri3 = [(px + dx, py + dy, pz) for px, py, pz in pts]
            face("M_Timber", tri3 if (newell(tri3)[0] * dx + newell(tri3)[1] * dy) > 0 else tri3[::-1], TIMBER)
        box("M_Timber", (min(p[0], q[0]) - 0.018, min(p[1], q[1]) - 0.018, z - 0.06), (max(p[0], q[0]) + 0.018, max(p[1], q[1]) + 0.018, z - 0.045), TIMBER)
    # the set, in its own frame: local x = across the screen, -y = the front, z = up
    W, H, D = 0.72, 0.5, 0.34
    feet = 0.035
    rz = math.atan2(d.y, d.x) + math.pi / 2
    Mt = M_at(tx, ty, z + feet + H / 2, rz)
    y0 = -D / 2
    extrude(Mt, "M_Lacquer", rrect(0, 0, W, H, 0.055, 5), y0, D / 2, TV_WALNUT)
    # the tube's bakelite back, tapering towards the wall
    extrude(Mt, "M_Lacquer", rrect(0, 0.01, W - 0.12, H - 0.1, 0.05, 3), D / 2, D / 2 + 0.2, TV_BAKELITE, front=False,
            loop1=rrect(0, 0.03, 0.3, 0.24, 0.04, 3))
    # stub feet with brass caps
    for fx in (-W / 2 + 0.07, W / 2 - 0.07):
        for fy in (y0 + 0.06, D / 2 - 0.06):
            p = Mt @ Vector((fx, fy, -H / 2))
            cyl("M_Lacquer", (p.x, p.y, z), 0.02, feet, 8, TV_BAKELITE, r_top=0.026)
    # screen: curved glass behind a gold mask (screen centre offset to the left, speaker on the right)
    scx, scz = -0.1, 0.01
    SW, SH = 0.44, 0.33
    mask_out = rrect(scx, scz, SW + 0.06, SH + 0.06, 0.05, 5)
    mask_in = rrect(scx, scz, SW, SH, 0.045, 5)
    ym = y0 - 0.014
    ring(Mt, "M_Metal", mask_out, mask_in, ym, TV_GOLD)
    extrude(Mt, "M_Metal", mask_out, ym, y0, TV_GOLD, front=False, back=False)
    extrude(Mt, "M_Lacquer", mask_in, ym, y0 + 0.002, TV_BAKELITE, front=False, back=False, inward=True)
    NX, NZ = 12, 9
    sv, sf, suv = [], [], []
    for j in range(NZ + 1):
        for i in range(NX + 1):
            u, v = i / NX, j / NZ
            bulge = 0.016 * (1 - (2 * u - 1) ** 2) * (1 - (2 * v - 1) ** 2)
            sv.append(tuple(Mt @ Vector((scx - SW / 2 + SW * u, y0 - 0.002 - bulge, scz - SH / 2 + SH * v))))
    for j in range(NZ):
        for i in range(NX):
            k = j * (NX + 1) + i
            sf.append((k, k + 1, k + NX + 2, k + NX + 1))
            suv.append([(i / NX, j / NZ), ((i + 1) / NX, j / NZ), ((i + 1) / NX, (j + 1) / NZ), (i / NX, (j + 1) / NZ)])
    with GROUP("TV_Screen"):
        emit_indexed("M_Screen", sv, sf, suv, WHITE, smooth=True)
    # speaker panel: woven grille behind gold slats, channel + volume knobs above it
    px_ = W / 2 - 0.1
    grille = rrect(px_, -0.07, 0.13, 0.26, 0.02, 2)
    extrude(Mt, "M_Cloth", grille, y0 - 0.004, y0, TV_GRILLE, back=False, s=0.08)
    for k in range(5):
        gz = -0.18 + k * 0.055
        p0, p1 = Mt @ Vector((px_ - 0.06, y0 - 0.009, gz)), Mt @ Vector((px_ + 0.06, y0 - 0.009, gz))
        tube("M_Metal", tuple(p0), tuple(p1), 0.004, 4, TV_GOLD, caps=True)
    for kz, kr in ((0.16, 0.034), (0.08, 0.024)):
        c0 = Mt @ Vector((px_, y0, kz))
        c1 = Mt @ Vector((px_, y0 - 0.03, kz))
        ax = (c1 - c0).normalized()
        tube("M_Lacquer", tuple(c0), tuple(c1), kr, 12, TV_BAKELITE, caps=False)
        cap = [tuple(c1 + (Mt.to_3x3() @ Vector((math.cos(math.tau * i / 12), 0, math.sin(math.tau * i / 12)))) * kr * 0.72) for i in range(12)]
        emit("M_Metal", cap if Vector(newell(cap)).dot(-ax) < 0 else cap[::-1], [(0, 0)] * 12, TV_GOLD)
        tick = [c1 + Mt.to_3x3() @ Vector(v_) for v_ in ((-0.003, -0.001, 0.0), (0.003, -0.001, 0.0), (0.003, -0.001, kr * 0.9), (-0.003, -0.001, kr * 0.9))]
        quad("M_Metal", *[tuple(p) for p in tick], col=TV_GOLD)
    # maker's badge under the screen
    mbox(Mt @ Matrix.Translation((scx, y0 - 0.004, scz - SH / 2 - 0.055)), "M_Metal", (0.11, 0.008, 0.018), TV_GOLD)
    # lace doily + rabbit ears on top
    topc = Mt @ Vector((0.02, 0.02, H / 2))
    cyl("M_Cloth", (topc.x, topc.y, topc.z), 0.15, 0.003, 16, C(0.96, 0.95, 0.9), s=0.1)
    cyl("M_Lacquer", (topc.x, topc.y, topc.z + 0.003), 0.055, 0.03, 12, TV_BAKELITE, r_top=0.045)
    base = Vector((topc.x, topc.y, topc.z + 0.033))
    for s_ in (-1, 1):
        dirv = (Mt.to_3x3() @ Vector((0.42 * s_, 0.12, 0.9))).normalized()
        mid = base + dirv * 0.26
        tip = base + dirv * 0.5
        tube("M_Metal", tuple(base), tuple(mid), 0.006, 5, STEEL)
        tube("M_Metal", tuple(mid), tuple(tip), 0.0035, 4, STEEL)
        sphere("M_Metal", tuple(tip), 0.011, STEEL, nu=6, nv=4)
    front = Mt @ Vector((scx, y0 - 0.02, scz))
    fd = (front - Mt @ Vector((scx, 0, scz)))
    marker("TV", tuple(front), (fd.x, fd.y, 0.0))
    marker("SNAP_TV", tuple(front), (fd.x, fd.y, 0.0))


# ---------------------------------------------------------------- Queenstown today (Then & Now)
# What the same corner looks like now (docs/research/1965-history.md §14): the early blocks are still
# lived in (Stirling Road's first HDB blocks of 1960 are 7-storey rental blocks with laundry-pole
# sockets), repainted, with air-con condensers, open-fronted neighbourhood shops and parked cars;
# over the rooftops, SkyVille@Dawson (3 linked 47-storey towers, sky gardens) and SkyTerrace@Dawson
# (5 towers of 40-43 storeys on a car-park podium), and the East-West Line on its viaduct (1988).
NOW_ACCENT = C(0.66, 0.52, 0.45)      # repainted terracotta piers (the era shader saturates plaster)
PLASTIC = [C(0.20, 0.42, 0.75), C(0.85, 0.45, 0.12), C(0.75, 0.16, 0.14), C(0.25, 0.6, 0.35)]
NOW_R = random.Random(2026)


def shutter_box(x0, x1):
    """Roller shutter rolled up under the fascia, with its side guides."""
    box("M_Metal", (x0, YF - 0.28, ZF + 2.48), (x1, YF - 0.02, ZF + 2.62), C(0.62, 0.64, 0.66))
    for xs in (x0 + 0.02, x1 - 0.08):
        box("M_Metal", (xs, YF - 0.08, ZF), (xs + 0.06, YF - 0.02, ZF + 2.5), C(0.55, 0.57, 0.6))


def plastic_table(x, y, rz=0.0):
    """Round marble-topped coffee-shop table with plastic stools, as in today's eating houses."""
    cyl("M_Metal", (x, y, ZF), 0.2, 0.03, 10, IRON)
    tube("M_Metal", (x, y, ZF), (x, y, ZF + 0.72), 0.035, 6, IRON)
    cyl("M_Plaster", (x, y, ZF + 0.72), 0.42, 0.03, 16, C(0.95, 0.94, 0.9))
    for k in range(4):
        a = rz + k * math.tau / 4
        sx, sy = x + math.cos(a) * 0.62, y + math.sin(a) * 0.62
        cyl("M_Lacquer", (sx, sy, ZF), 0.17, 0.44, 10, NOW_R.choice(PLASTIC), r_top=0.14)


def now_shopfront(x0, x1, kind):
    box("M_Metal", (x0, YF - 0.05, ZF), (x1, YF + 0.02, ZF + 0.12), STEEL)
    box("M_Metal", (x0, YF - 0.34, ZF + 2.6), (x1, YF - 0.02, ZS - 0.02), C(0.93, 0.93, 0.9))        # lit fascia box
    if kind == "provision":
        # an eating house: open front, drinks stall at the back, tables out into the corridor
        shutter_box(x0, x1)
        wall_quad_y("M_Details", x0 + 0.2, x1 - 0.2, ZF, ZF + 1.3, YN - 0.03, WHITE, uv=arect(DET["tiles"]))
        box("M_Metal", (x0 + 0.5, YN - 1.2, ZF), (x1 - 0.5, YN - 0.55, ZF + 0.95), C(0.7, 0.72, 0.74))
        wall_quad_y("M_NowSigns", x0 + 1.2, x1 - 1.2, ZF + 1.6, ZF + 2.5, YN - 0.03, WHITE, uv=arect((512, 384, 768, 640)))
        box("M_Emissive", (x0 + 0.6, YN - 0.9, ZF + 0.95), (x0 + 1.3, YN - 0.55, ZF + 2.1), C(0.9, 0.95, 1.0))   # drinks fridge
        for (tx, ty) in ((x0 + 1.3, 4.6), (x1 - 1.3, 4.4), (x0 + 2.4, 1.7), (x1 - 1.1, 1.6)):
            plastic_table(tx, ty, NOW_R.uniform(0, 1))
    else:
        # glass shopfront, lit inside
        atlas = {"tailor": (512, 384, 1024, 768), "bookshop": (0, 384, 512, 768), "barber": (512, 0, 1024, 384)}[kind]
        wall_quad_y("M_NowShop", x0 + 0.1, x1 - 0.1, ZF + 0.12, ZF + 2.55, YF - 0.02, WHITE, uv=arect(atlas))
        for xs in (x0 + 0.05, (x0 + x1) / 2, x1 - 0.1):
            box("M_Metal", (xs, YF - 0.06, ZF), (xs + 0.06, YF, ZF + 2.6), C(0.2, 0.2, 0.22))
    for xx in (x0 + 0.8, x1 - 0.8):
        tube("M_Emissive", (xx - 0.55, 4.5, ZS - 0.06), (xx + 0.55, 4.5, ZS - 0.06), 0.02, 6, TUBE, caps=True)


def now_minimart():
    shutter_box(KX0, KX1)
    box("M_Metal", (KX0, YF - 0.34, ZF + 2.6), (KX1, YF - 0.02, ZS - 0.02), C(0.93, 0.93, 0.9))
    # aisles of shelves inside, bright ceiling panels
    for k in range(3):
        y = 5.0 + k * 2.2
        box("M_Metal", (-3.5, y, ZF), (3.5, y + 0.5, ZF + 1.6), C(0.85, 0.86, 0.88))
        for fy, face_ in ((y - 0.01, "-y"), (y + 0.51, "+y")):
            wall_quad_y("M_Details", -3.4, 3.4, ZF + 0.15, ZF + 1.55, fy, WHITE, facing=face_, uv=arect(DET["provisions"]))
        tube("M_Emissive", (-2.5, y + 0.25, ZS - 0.06), (2.5, y + 0.25, ZS - 0.06), 0.025, 6, TUBE, caps=True)
    # out front: tiered display racks, bottled water, a drinks chiller, buckets and brooms
    for (ra, rb) in ((-3.9, -1.9), (1.3, 2.9)):
        for t_ in range(3):
            y0 = 2.35 + t_ * 0.18
            box("M_Details", (ra, y0, ZF), (rb, 2.95, ZF + 0.35 + t_ * 0.28), WHITE,
                uvs={"-y": arect(DET["provisions"])}, mats={k: "M_Metal" for k in ("+y", "-x", "+x", "-z", "+z")},
                cols={k: C(0.75, 0.2, 0.18) for k in ("+z", "-x", "+x")})
    for (wx, wy) in ((-1.5, 2.55), (-1.5, 2.25), (-1.05, 2.55)):
        for k in range(2):
            box("M_Plaster", (wx - 0.2, wy - 0.14, ZF + k * 0.3), (wx + 0.2, wy + 0.14, ZF + 0.3 + k * 0.3), C(0.55, 0.75, 0.92))
    box("M_Metal", (3.2, 2.35, ZF), (3.95, 2.95, ZF + 1.95), C(0.78, 0.16, 0.14))
    wall_quad_y("M_NowShop", 3.27, 3.88, ZF + 0.2, ZF + 1.75, 2.34, WHITE, uv=arect((0, 440, 240, 740)))
    for k, col in enumerate(PLASTIC[:3]):
        cyl("M_Lacquer", (-4.05 + k * 0.05, 2.1 - k * 0.32, ZF), 0.16, 0.3, 10, col, r_top=0.19)
    for k in range(2):
        tube("M_Timber", (-4.2, 2.8 - k * 0.12, ZF + 0.05), (-4.25, 2.85 - k * 0.12, ZF + 1.3), 0.015, 4, C(0.8, 0.7, 0.4))
        box("M_Cloth", (-4.32, 2.72 - k * 0.12, ZF), (-4.12, 2.88 - k * 0.12, ZF + 0.25), C(0.3, 0.55, 0.3))


def now_facade():
    with GROUP("NOW_Facade"):
        for k in range(STOREYS - 1):
            z = ZS + k * STOREY
            for i in range(10):
                xa = X0 + i * 3.0
                wall_quad_y("M_Plaster", xa, xa + 0.5, z + 1.0, z + 2.4, YE - 0.47, NOW_ACCENT, s=2.0)
                if NOW_R.random() < 0.5:                                  # air-con condenser under the window
                    cx = xa + 0.5 + NOW_R.uniform(0.5, 2.0)
                    box("M_Metal", (cx - 0.38, YE - 0.8, z + 0.45), (cx + 0.38, YE - 0.47, z + 0.95), C(0.88, 0.89, 0.87),
                        mats={"-y": "M_NowSigns"}, uvs={"-y": arect((262, 390, 506, 634))})
                    for bx in (cx - 0.3, cx + 0.3):
                        tube("M_Metal", (bx, YE - 0.47, z + 0.43), (bx, YE - 0.8, z + 0.43), 0.012, 4, IRON)
                if NOW_R.random() < 0.35:                                 # steel laundry rack in the old pole sockets
                    lx = xa + 0.5 + NOW_R.uniform(0.3, 1.9)
                    for j in range(3):
                        tube("M_Metal", (lx + j * 0.3, YE - 0.47, z + 1.0), (lx + j * 0.3, YE - 1.35, z + 1.0), 0.013, 4, STEEL)
                    for g_ in range(NOW_R.randint(1, 4)):
                        gx = lx + NOW_R.randint(0, 2) * 0.3
                        gy = YE - 0.7 - g_ * 0.18
                        w, dz = NOW_R.uniform(0.3, 0.5), NOW_R.uniform(0.35, 0.65)
                        c = C(*[NOW_R.uniform(0.3, 0.95) for _ in range(3)])
                        for fa in (-1, 1):
                            face("M_Cloth", [(gx - w / 2 * fa, gy, z + 1.0 - dz), (gx + w / 2 * fa, gy, z + 1.0 - dz),
                                             (gx + w / 2 * fa, gy, z + 1.0), (gx - w / 2 * fa, gy, z + 1.0)], c, s=0.5)
        # fire hose reel on a corridor pillar, a CCTV dome under the soffit
        box("M_Metal", (4.28, YE - 0.1, ZF + 0.95), (4.72, YE, ZF + 1.6), C(0.8, 0.12, 0.1))
        box("M_Metal", (4.3, YE - 0.105, ZF + 1.42), (4.7, YE - 0.1, ZF + 1.52), WHITE)
        sphere("M_Metal", (2.2, 0.4, ZS - 0.05), 0.07, C(0.15, 0.15, 0.17), nu=8, nv=4, sz=0.7)
    # block number, on the pillars and big on the parapet
    with GROUP("DECAL_NowBlockNo"):
        for px in (-4.5, 4.5):
            quad("M_Decal", (px - 0.2, YE - 0.004, ZF + 2.1), (px + 0.2, YE - 0.004, ZF + 2.1),
                 (px + 0.2, YE - 0.004, ZF + 2.5), (px - 0.2, YE - 0.004, ZF + 2.5))
        quad("M_Decal", (-1.2, YE - 0.52, Z_ROOF - 1.4), (1.2, YE - 0.52, Z_ROOF - 1.4), (1.2, YE - 0.52, Z_ROOF), (-1.2, YE - 0.52, Z_ROOF))
    # heritage-trail style marker at the edge of the corridor
    with GROUP("NOW_Street"):
        tube("M_Metal", (-2.25, -0.75, 0), (-2.25, -0.75, 1.0), 0.03, 6, C(0.3, 0.32, 0.3))
        mbox(M_at(-2.25, -0.78, 1.15, 0, rx=-0.35), "M_Metal", (0.62, 0.05, 0.42), C(0.3, 0.32, 0.3))
    with GROUP("DECAL_NowMarker"):
        Mm = M_at(-2.25, -0.78, 1.15, 0, rx=-0.35)
        quad("M_Decal", *[tuple(Mm @ Vector(p)) for p in ((-0.29, -0.03, -0.19), (0.29, -0.03, -0.19), (0.29, -0.03, 0.19), (-0.29, -0.03, 0.19))])


def car(x, y, rz, col):
    """A modern hatchback/sedan, ~4.4 m long (local x = length, y = width, z = up)."""
    M = M_at(x, y, 0, rz)
    prof = [(-2.2, 0.28), (2.2, 0.28), (2.22, 0.72), (1.95, 0.92), (0.95, 1.0), (0.35, 1.42), (-1.35, 1.44), (-1.95, 1.05), (-2.22, 0.95)]
    extrude(M, "M_Metal", prof, -0.87, 0.87, col)
    glass = C(0.12, 0.15, 0.18)
    for sgn in (-1, 1):
        yy = sgn * 0.875
        pts = [(-1.3, 1.02), (0.85, 1.02), (0.4, 1.36), (-1.25, 1.38)]
        w = [tuple(M @ Vector((px, yy, pz))) for px, pz in pts]
        face("M_Glass", w if sgn < 0 else w[::-1], glass)
        for wx in (-1.45, 1.45):
            c0 = M @ Vector((wx, yy * 0.98, 0.3))
            tube("M_Metal", tuple(c0), tuple(M @ Vector((wx, yy * 0.98 + sgn * 0.08, 0.3))), 0.3, 10, IRON, caps=True)
    for (pa, pb, out) in (((0.95, 1.0), (0.35, 1.42), (0.6, 0, 0.8)), ((-1.35, 1.44), (-1.95, 1.05), (-0.55, 0, 0.83))):
        o = Vector(out)
        w = [M @ (Vector((pa[0], -0.8, pa[1])) + o * 0.012), M @ (Vector((pa[0], 0.8, pa[1])) + o * 0.012),
             M @ (Vector((pb[0], 0.8, pb[1])) + o * 0.012), M @ (Vector((pb[0], -0.8, pb[1])) + o * 0.012)]
        w = [tuple(p) for p in w]
        face("M_Glass", w if Vector(newell(w)).dot(M.to_3x3() @ o) > 0 else w[::-1], glass)
    for sgn in (-1, 1):
        mbox(M @ Matrix.Translation((2.21, sgn * 0.62, 0.66)), "M_Emissive", (0.03, 0.26, 0.09), C(1, 0.98, 0.9))
        mbox(M @ Matrix.Translation((-2.21, sgn * 0.62, 0.8)), "M_Metal", (0.03, 0.3, 0.1), C(0.7, 0.05, 0.05))


def now_carpark():
    with GROUP("NOW_Street"):
        cols = [C(0.92, 0.92, 0.9), C(0.6, 0.62, 0.64), C(0.08, 0.08, 0.09), C(0.62, 0.1, 0.1), C(0.15, 0.22, 0.4), C(0.85, 0.85, 0.83)]
        for i, bx in enumerate((-12.0, -9.4, -3.9, 6.5, 9.1, 11.7)):
            car(bx + NOW_R.uniform(-0.1, 0.1), -4.0 + NOW_R.uniform(-0.2, 0.2), math.pi / 2 + NOW_R.uniform(-0.03, 0.03), cols[i])
        # covered linkway from the block across the car park: slim posts, curved roof, concrete path
        lx0, lx1, ly0, ly1 = -7.4, -5.8, -15.6, -0.5
        box("M_Plaster", (lx0, ly0, 0), (lx1, ly1, 0.1), C(0.74, 0.73, 0.7))
        for yy in [ly1 - 0.3 - k * 3.0 for k in range(6)]:
            tube("M_Metal", (lx0 + 0.1, yy, 0.1), (lx0 + 0.1, yy, 2.75), 0.06, 8, C(0.3, 0.42, 0.4))
        n = 8
        roof = [(lx0 - 0.2 + (lx1 - lx0 + 0.4) * k / n, 2.75 + 0.22 * math.sin(math.pi * k / n)) for k in range(n + 1)]
        for k in range(n):
            (xa, za), (xb, zb) = roof[k], roof[k + 1]
            for pts in ([(xa, ly0, za), (xb, ly0, zb), (xb, ly1, zb), (xa, ly1, za)],):
                face("M_Metal", pts[::-1], C(0.55, 0.62, 0.6))     # top
                face("M_Metal", pts, C(0.8, 0.82, 0.8))            # underside
        box("M_Metal", (lx0, ly0, 2.62), (lx0 + 0.2, ly1, 2.76), C(0.3, 0.42, 0.4))


def now_block(cx, cy, length, storeys, tint, accent, rz=0.0):
    """A present-day HDB slab (long facade on local -y): window bands, two lift/stair cores in colour."""
    M = M_at(cx, cy, 0, rz)
    h = storeys * 2.8 + 2.0
    dep = 11.0
    mbox(M @ Matrix.Translation((0, 0, h / 2)), "M_Far", (length, dep, h), tint, s=4.0, skip=("-z",))
    for k in range(storeys):
        z = 2.5 + k * 2.8
        for sgn in (-1, 1):
            pts = [M @ Vector((-length / 2 + 0.8, sgn * (dep / 2 + 0.03), z + 0.8)), M @ Vector((length / 2 - 0.8, sgn * (dep / 2 + 0.03), z + 0.8)),
                   M @ Vector((length / 2 - 0.8, sgn * (dep / 2 + 0.03), z + 1.9)), M @ Vector((-length / 2 + 0.8, sgn * (dep / 2 + 0.03), z + 1.9))]
            face("M_Glass", [tuple(p) for p in (pts if sgn < 0 else pts[::-1])], mul(WHITE, 0.85), s=1.25)
        mbox(M @ Matrix.Translation((0, -dep / 2 - 0.4, z + 0.3)), "M_Far", (length, 0.8, 0.18), mul(tint, 0.93), s=4.0)
    for fx in (-length / 4, length / 4):
        mbox(M @ Matrix.Translation((fx, -dep / 2 - 0.9, (h + 3) / 2)), "M_Far", (3.2, 1.8, h + 3), accent, s=4.0, skip=("-z",))
    mbox(M @ Matrix.Translation((0, 0, h + 0.4)), "M_Far", (length + 0.3, dep + 0.3, 0.8), accent, s=4.0)


def sky_tower(cx, cy, w, d, storeys, rz, gardens, col=C(0.93, 0.93, 0.91)):
    """A Dawson-style 40+ storey HDB tower: fins and window bands, open sky-garden floors, a green roof."""
    M = M_at(cx, cy, 0, rz)
    fh = 2.9
    cuts = sorted(set([0] + gardens + [storeys]))
    for a, b in zip(cuts, cuts[1:]):
        za = a * fh + (2 * fh if a in gardens else 0)
        zb = b * fh
        if zb <= za:
            continue
        mbox(M @ Matrix.Translation((0, 0, (za + zb) / 2)), "M_Far", (w, d, zb - za), col, s=4.0)
        for k in range(int((zb - za) / fh)):
            z = za + k * fh + 1.0
            for sgn, ww in ((-1, w), (1, w)):
                pts = [M @ Vector((-ww / 2 + 0.6, sgn * (d / 2 + 0.03), z)), M @ Vector((ww / 2 - 0.6, sgn * (d / 2 + 0.03), z)),
                       M @ Vector((ww / 2 - 0.6, sgn * (d / 2 + 0.03), z + 1.2)), M @ Vector((-ww / 2 + 0.6, sgn * (d / 2 + 0.03), z + 1.2))]
                face("M_Glass", [tuple(p) for p in (pts if sgn < 0 else pts[::-1])], mul(WHITE, 0.8), s=1.25)
        for fx in [(-w / 2 + 0.4 + i * (w - 0.8) / 6) for i in range(7)]:
            mbox(M @ Matrix.Translation((fx, -d / 2 - 0.35, (za + zb) / 2)), "M_Far", (0.35, 0.7, zb - za), mul(col, 0.97), s=4.0)
    for g_ in gardens:
        z = g_ * fh
        mbox(M @ Matrix.Translation((0, 0, z + fh)), "M_Far", (w * 0.35, d * 0.5, 2 * fh), mul(col, 0.9), s=4.0)
        for gx in (-w / 3, 0, w / 3):
            sphere("M_Cloth", tuple(M @ Vector((gx, -d / 4, z + 1.2))), 1.8, LEAF, nu=8, nv=4, sz=0.6)
    mbox(M @ Matrix.Translation((0, 0, storeys * fh + 0.6)), "M_Far", (w + 0.4, d + 0.4, 1.2), mul(col, 0.95), s=4.0)
    for gx in (-w / 3, 0, w / 3):
        sphere("M_Cloth", tuple(M @ Vector((gx, 0, storeys * fh + 1.6))), 2.0, LEAF, nu=8, nv=4, sz=0.5)
    return M


def now_skyline():
    """Beyond the east end of the block (seen as the photo is lined up): Dawson's towers and the MRT."""
    with GROUP("NOW_Skyline"):
        cam = Vector((0.8, -8.5, 0))
        def at(bearing_deg, dist):
            a = math.radians(bearing_deg)
            return cam + Vector((math.sin(a), math.cos(a), 0)) * dist
        # SkyVille@Dawson-style: three 47-storey towers joined by sky bridges at the garden floors
        gardens = [3, 14, 25, 36]
        pts = [at(b, 250) for b in (66, 71, 76)]
        for p in pts:
            sky_tower(p.x, p.y, 20, 14, 47, math.radians(-71), gardens)
        for p, q in zip(pts, pts[1:]):
            for g_ in gardens[1:]:
                z = g_ * 2.9 + 1.5
                tube("M_Far", (p.x, p.y, z), (q.x, q.y, z), 1.6, 4, C(0.9, 0.9, 0.88), caps=True)
        # SkyTerrace@Dawson-style: five 40-43 storey towers on a car-park podium
        pod = at(92, 300)
        box("M_Far", (pod.x - 40, pod.y - 45, 0), (pod.x + 25, pod.y + 45, 12), C(0.8, 0.8, 0.78), s=4.0, skip=("-z",))
        for i, st in enumerate((40, 43, 41, 43, 40)):
            sky_tower(pod.x - 10 + (i % 2) * 14, pod.y - 36 + i * 18, 16, 13, st, math.radians(-92), [], C(0.9, 0.89, 0.86))
        # older and newer HDB slabs in between
        for (b, dist, st, tint, acc) in ((63, 190, 16, C(0.9, 0.87, 0.8), C(0.7, 0.5, 0.42)),
                                        (82, 175, 24, C(0.9, 0.9, 0.88), C(0.45, 0.6, 0.66)),
                                        (97, 160, 12, C(0.92, 0.9, 0.85), C(0.62, 0.66, 0.5)),
                                        (110, 210, 20, C(0.88, 0.88, 0.86), C(0.72, 0.62, 0.45))):
            p = at(b, dist)
            now_block(p.x, p.y, 48, st, tint, acc, math.radians(-b))    # long facade towards the camera
        # the East-West Line viaduct on its piers
        vx = 70.0
        box("M_Far", (vx - 4.5, -420, 11.0), (vx + 4.5, 420, 12.4), C(0.74, 0.74, 0.72), s=4.0)
        for sgn in (-1, 1):
            box("M_Far", (vx + sgn * 4.5 - 0.25, -420, 12.4), (vx + sgn * 4.5 + 0.25, 420, 13.4), C(0.78, 0.78, 0.76), s=4.0)
        for yy in range(-405, 420, 30):
            box("M_Far", (vx - 1.1, yy - 1.1, 0), (vx + 1.1, yy + 1.1, 11.0), C(0.72, 0.72, 0.7), s=4.0, skip=("-z",))
            box("M_Far", (vx - 4.0, yy - 1.3, 9.8), (vx + 4.0, yy + 1.3, 11.0), C(0.72, 0.72, 0.7), s=4.0)
    with GROUP("NOW_Train"):
        # six cars (runtime slides the group along the viaduct)
        for k in range(6):
            y0 = -70 + k * 23.2
            box("M_Metal", (vx - 1.6, y0, 12.6), (vx + 1.6, y0 + 22.6, 16.2), C(0.9, 0.91, 0.92))
            for sgn in (-1, 1):
                xx = vx + sgn * 1.605
                wall_quad_x("M_Glass", y0 + 1.2, y0 + 21.4, 14.2, 15.4, xx, C(0.2, 0.24, 0.28), facing="+x" if sgn > 0 else "-x", s=1.25)
                wall_quad_x("M_Far", y0, y0 + 22.6, 13.2, 13.6, xx + sgn * 0.005, C(0.1, 0.55, 0.3), facing="+x" if sgn > 0 else "-x")


# ---------------------------------------------------------------- corridor dressing
def build_corridor_props():
    with GROUP("THEN_Street"):
        # bicycles parked by the pillars, a hawker's push-cart in the car park, a rattan birdcage
        for (bx, rz) in ((-11.3, 0.1), (-6.8, -0.05), (10.8, 0.05)):
            bicycle(bx, 0.6, rz)
        # the cart body rides on two upright bicycle-type wheels, a leg at the front, handles at the back
        box("M_Timber", (6.0, -3.2, 0.5), (7.6, -2.3, 1.2), TIMBER)
        for wy in (-3.28, -2.22):
            tube("M_Metal", (6.95, wy - 0.03, 0.36), (6.95, wy + 0.03, 0.36), 0.36, 14, IRON, caps=True)      # tyre
            tube("M_Metal", (6.95, wy - 0.035, 0.36), (6.95, wy + 0.035, 0.36), 0.08, 8, STEEL, caps=True)    # hub
        tube("M_Metal", (6.95, -3.3, 0.36), (6.95, -2.2, 0.36), 0.02, 5, STEEL)                                # axle
        for ly in (-3.1, -2.4):
            tube("M_Timber", (6.1, ly, 0.0), (6.1, ly, 0.52), 0.035, 5, TIMBER_DARK, caps=True)                  # front legs
            tube("M_Timber", (7.6, ly, 0.95), (8.25, ly, 0.85), 0.025, 5, TIMBER_DARK, caps=True)                # handles
        box("M_Cloth", (5.9, -3.3, 1.9), (7.7, -2.2, 1.95), C(0.85, 0.35, 0.3))
        collider("COL_Cart", (5.95, -3.35, 0), (8.3, -2.15, 1.3))
        for (px, py) in ((6.0, -3.2), (7.6, -3.2), (6.0, -2.3), (7.6, -2.3)):
            tube("M_Timber", (px, py, 1.2), (px, py, 1.9), 0.02, 4, TIMBER_DARK, smooth=False)
        with DETAIL():
            bc = Vector((-3.0, 1.2, ZS - 0.2))
            tube("M_Metal", bc, bc - Vector((0, 0, 0.5)), 0.005, 3, IRON, smooth=False)
            cyl("M_Timber", tuple(bc - Vector((0, 0, 0.95))), 0.15, 0.03, 10, TIMBER_DARK)
            for k in range(10):
                a = math.tau * k / 10
                tube("M_Timber", bc - Vector((-math.cos(a) * 0.15, -math.sin(a) * 0.15, 0.92)), bc - Vector((0, 0, 0.5)), 0.005, 3, C(0.78, 0.68, 0.42), smooth=False)
    with GROUP("NOW_Street"):
        # present day: bicycle rack, recycling bins, potted plants, a notice board
        for i in range(4):
            bicycle(-12.5 + i * 0.7, -0.6, math.pi / 2)
        for (bx, col) in ((11.0, C(0.2, 0.45, 0.8)), (11.8, C(0.25, 0.55, 0.3))):
            box("M_Metal", (bx, -0.9, 0), (bx + 0.6, -0.3, 1.05), col)
        for px in (-6.0, -2.0, 2.0, 6.0):
            cyl("M_Plaster", (px, -0.6, 0), 0.28, 0.45, 10, C(0.45, 0.42, 0.4))
            sphere("M_Cloth", (px, -0.6, 0.75), 0.42, LEAF, nu=8, nv=5, sz=0.9)
        box("M_Metal", (X0 + 0.02, 0.8, 1.0), (X0 + 0.06, 2.4, 2.0), C(0.25, 0.3, 0.36))


def bicycle(x, y, rz):
    M = M_at(x, y, 0, rz)
    for dx in (-0.5, 0.5):
        c = M @ Vector((dx, 0, 0.33))
        ax = M.to_3x3() @ Vector((1, 0, 0))
        n = 10
        pts = [c + (ax * math.cos(math.tau * k / n) + Vector((0, 0, 1)) * math.sin(math.tau * k / n)) * 0.33 for k in range(n + 1)]
        for a, b in zip(pts, pts[1:]):
            tube("M_Metal", a, b, 0.012, 3, IRON, smooth=False)
    for (a, b) in (((-0.5, 0, 0.33), (0.0, 0, 0.75)), ((0.0, 0, 0.75), (0.5, 0, 0.33)), ((-0.1, 0, 0.35), (0.45, 0, 0.8)),
                   ((0.0, 0, 0.75), (0.45, 0, 0.8)), ((-0.1, 0, 0.35), (-0.5, 0, 0.33)), ((0.45, 0, 0.8), (0.45, 0, 0.98))):
        tube("M_Metal", M @ Vector(a), M @ Vector(b), 0.016, 4, C(0.15, 0.25, 0.2), smooth=False)
    tube("M_Metal", M @ Vector((0.45, -0.25, 0.98)), M @ Vector((0.45, 0.25, 0.98)), 0.014, 4, IRON, smooth=False)


# ---------------------------------------------------------------- contract markers
def contract_markers():
    marker("SPAWN_Sparky", (0.6, 1.4, ZF), (0, 1))
    marker("THEN_NOW_Camera", (0.8, -8.5, 1.45), (0.0, 1.0, 0.05), {"note": "Then & Now viewpoint in the car park"})
    # cast at their 1965 morning spots (seats are resolved in code from SEAT_T* markers)
    marker("NPC_AhPek", TABLES[0] + (ZF,), (0, -1), {"seat": "SEAT_T1_c"})
    marker("NPC_Rohani", TABLES[3] + (ZF,), (0, -1), {"seat": "SEAT_T4_b"})
    marker("NPC_Letchumi", TABLES[5] + (ZF,), (0, -1), {"seat": "SEAT_T6_a"})
    marker("NPC_Ravi", TABLES[4] + (ZF,), (0, -1), {"seat": "SEAT_T5_d"})
    marker("NPC_SitiTable", TABLES[2] + (ZF,), (0, -1), {"seat": "SEAT_T3_c"})
    marker("NPC_Siti", (6.7, 1.7, ZF), (-1, 0))                # at the bookshop, in the corridor
    marker("NPC_Rajan", (-12.5, 1.5, ZF), (1, 0))              # arrives from the west end of the corridor
    marker("RAJAN_Door", (-3.4, 3.6, ZF), (1, 1))
    # corridor rumour-mongers (errand beat)
    for i, (x, y, fx) in enumerate(((10.9, 1.6, -1), (3.5, 1.7, 1), (-6.6, 1.8, 1), (8.2, 2.0, -1), (12.2, 2.2, -1))):   # clear of the pillars
        marker(f"RUMOUR_{i + 1}", (x, y, ZF), (fx, 0))
    # evening crowd: standing spots facing the TV (inside and in the doorway)
    spots = [(-3.6, 4.0), (-3.2, 3.5), (-1.8, 3.4), (-0.9, 3.9), (-1.3, 6.2), (1.3, 6.2), (-3.9, 6.2), (3.9, 6.6),
             (-2.3, 2.6), (-1.0, 2.5), (0.4, 2.6), (1.8, 2.5), (3.0, 2.8), (-3.6, 2.2)]
    for i, (x, y) in enumerate(spots):
        marker(f"CROWD_{i + 1}", (x, y, ZF if y > YE else 0), facing((x, y), (TV[0], TV[1])))
    # camera helpers
    marker("CAM_Wide", (-3.9, 3.4, 2.5), (0.75, 1.0, -0.33))
    marker("CAM_TVCrowd", (3.2, 10.6, 2.0), (-0.72, -1.0, -0.22))
    marker("CAM_Counter", (-1.0, 7.0, 1.55), (-0.3, 1.0, -0.12))
    marker("CAM_Wall", (1.9, 9.8, 1.6), (0.0, 1.0, 0.05))
    marker("CAM_Corridor", (-1.5, -2.2, 1.9), (0.6, 1.0, -0.15))


def build_level():
    build_block()
    build_laundry()
    build_outside()
    build_shops()
    build_kopitiam()
    build_corridor_props()
    now_facade()
    now_carpark()
    now_skyline()
    contract_markers()


# ======================================================================================
# Blender objects, materials
# ======================================================================================
MAT_DEF = {
    #  name           texture     rough metal  doubleSided
    "M_Plaster": ("plaster", 0.92, 0.0, False),
    "M_Timber": ("timber", 0.78, 0.0, False),
    "M_Floor": ("floor", 0.45, 0.0, False),
    "M_Road": ("road", 0.93, 0.0, False),
    "M_Cloth": ("cloth", 0.95, 0.0, True),
    "M_Windows": ("windows", 0.55, 0.0, False),
    "M_Details": ("details", 0.45, 0.0, False),
    "M_NowSigns": ("now", 0.5, 0.0, False),
    "M_Glass": ("glass", 0.12, 0.6, False),
    "M_Metal": (None, 0.5, 0.55, False),
    "M_Emissive": (None, 0.5, 0.0, False),
    "M_Decal": (None, 0.7, 0.0, False),
    "M_Screen": (None, 0.25, 0.0, False),
    "M_Lacquer": (None, 0.3, 0.0, False),
    "M_NowShop": ("nowshop", 0.25, 0.0, False),
    "M_Far": (None, 0.9, 0.0, False),          # present-day skyline (not saturated by the era shader)
}
IMAGES = {}
TILING = {"M_Plaster", "M_Timber", "M_Floor", "M_Road", "M_Cloth", "M_Glass"}
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
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = metal
        attr = nt.nodes.new("ShaderNodeVertexColor")
        attr.layer_name = "Col"
        if tex:
            img = bpy.data.images.load(os.path.join(TEX, str(res), tex + ".png"), check_existing=False)
            img.name = tex
            IMAGES[tex] = img
            it = nt.nodes.new("ShaderNodeTexImage")
            it.image = img
            if name in TILING:
                uvn = nt.nodes.new("ShaderNodeUVMap")
                uvn.uv_map = "UVMap"
                mp = nt.nodes.new("ShaderNodeMapping")
                mp.vector_type = "POINT"
                mp.inputs["Scale"].default_value = (UV_TILE, UV_TILE, 1.0)
                nt.links.new(uvn.outputs["UV"], mp.inputs["Vector"])
                nt.links.new(mp.outputs["Vector"], it.inputs["Vector"])
            mix = nt.nodes.new("ShaderNodeMix")
            mix.data_type = "RGBA"
            mix.blend_type = "MULTIPLY"
            mix.inputs[0].default_value = 1.0
            nt.links.new(it.outputs["Color"], mix.inputs[6])
            nt.links.new(attr.outputs["Color"], mix.inputs[7])
            nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
        else:
            nt.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
        if name == "M_Emissive":
            bsdf.inputs["Emission Color"].default_value = (0.95, 0.97, 1.0, 1.0)
            bsdf.inputs["Emission Strength"].default_value = 2.0
        if name == "M_NowShop" and tex:                       # lit shop interiors behind glass
            nt.links.new(it.outputs["Color"], bsdf.inputs["Emission Color"])
            bsdf.inputs["Emission Strength"].default_value = 0.55
        if name == "M_Screen":
            bsdf.inputs["Base Color"].default_value = (0.08, 0.09, 0.09, 1.0)
        mats[name] = m
    return mats


LOWRES_ALWAYS = {"glass"}


def swap_textures(res):
    for tex, img in IMAGES.items():
        img.filepath = os.path.join(TEX, str(512 if tex in LOWRES_ALWAYS else res), tex + ".png")
        img.reload()


def object_name(group, tier):
    base = "Kopitiam_Static" if group == "STATIC" else group
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
    uvl.data.foreach_set("uv", [c for uv in uvs for c in uv])
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


def make_objects(mats):
    coll = bpy.context.scene.collection
    objs = {}
    for (group, tier), md in sorted(BUCKETS.items()):
        name = object_name(group, tier)
        ob = make_mesh_object(name, md, mats, coll)
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
        ob["aabb_min"] = [round(x0, 3), round(z0, 3), round(-y1, 3)]
        ob["aabb_max"] = [round(x1, 3), round(z1, 3), round(-y0, 3)]
        coll.objects.link(ob)
        cols.append(ob)
    empties = []
    for (name, pos, fdir, props) in MARKERS:
        ob = bpy.data.objects.new(name, None)
        ob.empty_display_type = "SINGLE_ARROW"
        ob.empty_display_size = 0.4
        ob.location = pos
        if fdir and len(fdir) == 3:
            ob.rotation_euler = Vector(fdir).normalized().to_track_quat("-Y", "Z").to_euler()
        elif fdir:
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
    sc.cycles.samples = 12 if FAST else 40
    if sc.world is None:
        sc.world = bpy.data.worlds.new("World")
    sc.world.light_settings.distance = 2.2
    for ob in bpy.context.scene.objects:
        ob.hide_render = ob.name in hide or ob.name.startswith("COL_") or ob.type != "MESH"
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
        k = 0.36 + 0.64 * np.clip(a, 0, 1) ** 0.85
        # emissive tubes stay bright
        mi = np.empty(len(me.polygons), dtype=np.int32)
        me.polygons.foreach_get("material_index", mi)
        lt = np.empty(len(me.polygons), dtype=np.int32)
        me.polygons.foreach_get("loop_total", lt)
        loop_mat = np.repeat(mi, lt)
        names = [m.name for m in me.materials]
        for keep in ("M_Emissive", "M_Decal", "M_Screen"):
            if keep in names:
                k[loop_mat == names.index(keep)] = 1.0
        c = col.reshape(-1, 4)
        c[:, :3] *= k[:, None]
        me.color_attributes["Col"].data.foreach_set("color", c.ravel())
        me.color_attributes.remove(me.color_attributes["AO"])
        ca = me.color_attributes["Col"]
        me.color_attributes.active_color = ca
        me.color_attributes.render_color_index = me.color_attributes.active_color_index
    for ob in bpy.context.scene.objects:
        if ob.type == "MESH" and not ob.name.startswith("COL_"):
            ob.hide_render = False


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
    props = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
    bpy.ops.export_scene.gltf(**{k: v for k, v in kw.items() if k in props})
    print("exported", path, round(os.path.getsize(path) / 1e6, 2), "MB")


def meshopt(path):
    cli = os.environ.get("GLTF_TRANSFORM") or os.path.join(os.environ.get("TMPDIR", "/tmp"), "sparky-gltf-tools", "node_modules", ".bin", "gltf-transform")
    if not os.path.exists(cli):
        print("gltf-transform not found: skipping meshopt for", path)
        return
    tmp = path + ".tmp.glb"
    subprocess.check_call([cli, "meshopt", path, tmp, "--level", "high", "--quantize-position", "16",
                           "--quantize-texcoord", "16", "--quantize-normal", "10", "--quantize-color", "8"])
    os.replace(tmp, path)
    print("meshopt", path, round(os.path.getsize(path) / 1e6, 2), "MB")


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


def write_nodes_json(objs, cols, empties, extra):
    data = {"markers": {}, "colliders": {}, "meshes": {}}
    for e in empties:
        d = e.matrix_world.to_3x3() @ Vector((0, -1, 0))
        data["markers"][e.name] = {"three_pos": to_three(e.location), "three_facing": to_three(d),
                                   "props": {k: (v.to_list() if hasattr(v, "to_list") else v) for k, v in e.items()}}
    for c in cols:
        data["colliders"][c.name] = {"three_center": to_three(c.location)}
    for name, ob in objs.items():
        ob.data.calc_loop_triangles()
        data["meshes"][name] = {"tris": len(ob.data.loop_triangles), "materials": [m.name for m in ob.data.materials]}
    data.update(extra)
    with open(NODES_JSON, "w") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)


# ======================================================================================
# Previews
# ======================================================================================
def preview_setup():
    sc = bpy.context.scene
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            sc.render.engine = eng
            break
        except Exception:
            pass
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    try:
        sc.eevee.taa_render_samples = 16 if FAST else 32
    except Exception:
        pass
    try:
        sc.view_settings.view_transform = "AgX"
    except Exception:
        pass
    if sc.world is None:
        sc.world = bpy.data.worlds.new("World")
    w = sc.world
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.55, 0.62, 0.7, 1)
        bg.inputs["Strength"].default_value = 0.9
    sun_d = bpy.data.lights.new("Sun", "SUN")
    sun_d.energy = 3.5
    sun_d.color = (1.0, 0.94, 0.84)
    sun = bpy.data.objects.new("PREVIEW_Sun", sun_d)
    sun.rotation_euler = (math.radians(50), 0, math.radians(-30))
    sc.collection.objects.link(sun)
    pt = bpy.data.lights.new("Fill", "AREA")
    pt.energy = 250
    pt.size = 6
    ptl = bpy.data.objects.new("PREVIEW_Fill", pt)
    ptl.location = (0, 7.5, ZS - 0.1)
    sc.collection.objects.link(ptl)


def camera(name, loc, target, lens=22):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_start, cd.clip_end = 0.05, 600
    ob = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return ob


def set_state(objs, state):
    for n, ob in objs.items():
        if n.startswith("NOW_") or n.startswith("DECAL_NowSign"):
            ob.hide_render = state != "now"
        elif n.startswith("THEN_"):
            ob.hide_render = state == "now"
        elif n.startswith("WALL_") or n == "DECAL_Portrait_Papa":
            ob.hide_render = True


def previews(objs):
    os.makedirs(PREV_DIR, exist_ok=True)
    preview_setup()
    shots = [("01_front_then", "then", (0.8, -8.5, 1.45), (0.8, 6, 1.8)),
             ("02_interior_wide", "then", (-3.9, 3.4, 2.5), (1.5, 10.5, 1.0)),
             ("03_counter", "then", (-1.0, 6.6, 1.55), (-1.9, 11.5, 1.2)),
             ("04_tv_corner", "then", (-1.5, 5.0, 1.6), (3.7, 11.2, 2.3)),
             ("05_corridor", "then", (-10, 1.4, 1.6), (6, 2.0, 1.2)),
             ("06_front_now", "now", (0.8, -8.5, 1.45), (0.8, 6, 1.8)),
             ("07_aerial", "then", (-22, -34, 26), (0, 3, 3))]
    for fname, state, loc, tgt in shots:
        set_state(objs, state)
        cam = camera("PREV_" + fname, loc, tgt, lens=16 if "aerial" not in fname else 28)
        bpy.context.scene.camera = cam
        bpy.context.scene.render.filepath = os.path.join(PREV_DIR, fname + ".png")
        bpy.ops.render.render(write_still=True)
        print("render", fname)


# ======================================================================================
def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    build_level()
    mats = make_materials(1024)
    objs, cols, empties = make_objects(mats)
    if DO_BAKE:
        runtime = ("DECAL_", "WALL_", "TV_Screen", "FAN_")
        then_bake = [o for n, o in objs.items() if not n.startswith(runtime) and not n.startswith("NOW_")]
        bake_ao(then_bake, {n for n in objs if n.startswith("NOW_")})
        now_bake = [o for n, o in objs.items() if n.startswith("NOW_")]
        if now_bake:
            bake_ao(now_bake, {n for n in objs if n.startswith("THEN_")})
    # mobile: base tier only, 512² textures
    swap_textures(512)
    mob = [o for n, o in objs.items() if not n.endswith("_detail")] + cols + empties
    tri_m = tri_count(mob)
    export_glb(OUT_MOBILE, mob)
    meshopt(OUT_MOBILE)
    # desktop: detail merged, 1024² textures
    swap_textures(1024)
    join_detail(objs)
    desk = list(objs.values()) + cols + empties
    tri_d = tri_count(desk)
    export_glb(OUT_DESKTOP, desk, q=78)
    meshopt(OUT_DESKTOP)
    write_nodes_json(objs, cols, empties, {"tris": {"mobile": tri_m, "desktop": tri_d}})
    print("TRIS mobile", tri_m, "desktop", tri_d, "objects", len(objs), "colliders", len(cols), "markers", len(empties))
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    if DO_PREVIEWS:
        previews(objs)


main()
