"""
Sparky Discovery — Prologue / Epilogue set: a present-day (2026) HDB void deck in Queenstown,
late afternoon, where 91-year-old Mr. Boon shows Sparky the Brownie camera.

Reproducible Blender build script (Blender 5.2):
    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python tools/build_voiddeck.py [-- --no-bake] [--no-previews] [--fast] [--no-meshopt]

Outputs
    public/assets/models/voiddeck.glb          desktop tier (1024² textures, detail geometry)
    public/assets/models/voiddeck-mobile.glb   mobile tier (512² textures, lighter geometry)
    tools/voiddeck.blend                       reference scene
    tools/voiddeck_nodes.json                  markers with three.js-space positions, tri counts
    docs/previews/voiddeck/*.png               EEVEE previews (placeholder figures on the stools)

Textures: tools/gen_voiddeck_textures.py -> tools/voiddeck_tex/{1024,512} (regenerated if missing;
needs Pillow — set VOIDDECK_PYLIB to a dir containing it).  Research: docs/research/voiddeck.md

Conventions (docs/design.md): metres, Blender Z-up; Blender (x, y, z) -> three.js (x, z, -y).
Marker empties face their local -Y.  Layout (Blender):
    stone table centred on the origin, top at z = 0.75
    void deck floor z = 0, x -24..8, y -4..6, soffit z = 3.0
    open side (sunlit grass, playground, neighbouring slab block) towards -Y,
    lift lobby + letterbox bank on the back wall y = 6 (lobby recess to y = 9),
    block end open towards +X (covered linkway, bicycles), sun low from +X/-Y.
All static geometry is merged into one mesh per tier, one primitive per material.
"""
import bpy, bmesh, math, random, os, sys, json, subprocess, shutil
from mathutils import Vector, Matrix

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
DO_BAKE = "--no-bake" not in ARGS
DO_PREVIEWS = "--no-previews" not in ARGS
FAST = "--fast" in ARGS
DO_MESHOPT = "--no-meshopt" not in ARGS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TEX = os.path.join(HERE, "voiddeck_tex")
OUT_DESKTOP = os.path.join(ROOT, "public", "assets", "models", "voiddeck.glb")
OUT_MOBILE = os.path.join(ROOT, "public", "assets", "models", "voiddeck-mobile.glb")
OUT_BLEND = os.path.join(HERE, "voiddeck.blend")
NODES_JSON = os.path.join(HERE, "voiddeck_nodes.json")
PREV_DIR = os.path.join(ROOT, "docs", "previews", "voiddeck")
GLTF_TOOLS = os.environ.get("SPARKY_NODE_TOOLS", os.path.join(os.environ.get("TMPDIR", "/tmp"), "sparky-gltf-tools"))

R = random.Random(53)
AN = 1024.0  # atlas reference size

# ======================================================================================
# colours (sRGB -> linear, stored in the colour attribute)
# ======================================================================================
def lin1(x):
    return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4


def C(r, g, b, a=1.0):
    return (lin1(r), lin1(g), lin1(b), a)


def J(c, amt=0.05, rng=R):
    k = 1.0 + rng.uniform(-amt, amt)
    return (c[0] * k, c[1] * k, c[2] * k, c[3])


def mulc(c, k):
    return (c[0] * k, c[1] * k, c[2] * k, c[3])


WHITE = C(1, 1, 1)
CREAM = C(0.95, 0.92, 0.84)          # void deck paint
CEIL = C(0.93, 0.92, 0.88)
JADE = C(0.55, 0.70, 0.62)           # pillar / wall dado colour
MAROON = C(0.55, 0.18, 0.18)
FLOOR = C(0.80, 0.75, 0.69)
LOBBY_TILE = C(0.90, 0.90, 0.88)
CONCRETE = C(0.92, 0.90, 0.86)
TERRAZZO = C(1.0, 0.98, 0.95)
GRASS = C(1.0, 1.0, 1.0)
STEEL = C(0.62, 0.63, 0.64)
DARK = C(0.12, 0.12, 0.13)
TERRACOTTA = C(0.72, 0.40, 0.28)
BARK = C(0.36, 0.29, 0.23)
SOIL = C(0.32, 0.24, 0.18)
LEAF = C(0.92, 1.0, 0.90)
TUBE = C(0.95, 0.98, 1.0)

# ======================================================================================
# geometry accumulation — per tier ('base' in both, 'detail' desktop-only, 'mobile' mobile-only)
# ======================================================================================
MATS = ["M_Paint", "M_Floor", "M_Concrete", "M_Terrazzo", "M_Grass", "M_Foliage", "M_Flower", "M_Facade",
        "M_Atlas", "M_Metal", "M_Plastic", "M_Rough", "M_Tube"]


class MB:
    __slots__ = ("v", "f", "uv", "col", "sm")

    def __init__(s):
        s.v, s.f, s.uv, s.col, s.sm = [], [], [], [], []


BUCKETS = {}
STATE = {"tier": "base"}


class Tier:
    def __init__(s, t):
        s.t = t

    def __enter__(s):
        s.old = STATE["tier"]
        STATE["tier"] = s.t

    def __exit__(s, *a):
        STATE["tier"] = s.old


DETAIL = lambda: Tier("detail")
MOBILE = lambda: Tier("mobile")


def bucket(mat):
    t = STATE["tier"]
    if mat == "M_Atlas" and t == "base":
        t = "decal"
    g = BUCKETS.setdefault(t, {})
    if mat not in g:
        g[mat] = MB()
    return g[mat]


def _cols(col, n):
    if isinstance(col, list):
        return col
    return [col] * n


def emit(mat, pts, uvs, col, smooth=False):
    b = bucket(mat)
    base = len(b.v)
    b.v.extend([tuple(p) for p in pts])
    b.f.append(tuple(range(base, base + len(pts))))
    b.uv.append(list(uvs))
    b.col.append(_cols(col, len(pts)))
    b.sm.append(smooth)


def emit_indexed(mat, verts, faces, uvs, cols, smooth=True):
    """faces: index tuples into verts; uvs: per-face lists of uv; cols: per-vertex colour list or one colour."""
    b = bucket(mat)
    base = len(b.v)
    b.v.extend([tuple(p) for p in verts])
    for fi, f in enumerate(faces):
        b.f.append(tuple(base + i for i in f))
        b.uv.append(list(uvs[fi]))
        if isinstance(cols, list):
            b.col.append([cols[i] for i in f])
        else:
            b.col.append([cols] * len(f))
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


def XF(M, p):
    if M is None:
        return tuple(p)
    return tuple(M @ Vector(p))


def poly(mat, pts, col, s=1.0, uv=None, smooth=False, M=None):
    w = [XF(M, p) for p in pts]
    emit(mat, w, uv if uv is not None else boxuv(w, s), col, smooth)


def grid(mat, o, du, dv, nu, nv, col, s=1.0, colfn=None):
    """Subdivided planar quad: o + i/nu*du + j/nv*dv. Normal = du x dv."""
    o, du, dv = Vector(o), Vector(du), Vector(dv)
    for i in range(nu):
        for j in range(nv):
            p = [o + du * (i / nu) + dv * (j / nv), o + du * ((i + 1) / nu) + dv * (j / nv),
                 o + du * ((i + 1) / nu) + dv * ((j + 1) / nv), o + du * (i / nu) + dv * ((j + 1) / nv)]
            p = [tuple(q) for q in p]
            c = [colfn(q) for q in p] if colfn else col
            emit(mat, p, boxuv(p, s), c)


def cells(length, cell):
    return max(1, int(math.ceil(abs(length) / cell - 1e-6)))


def floor_rect(mat, x0, x1, y0, y1, z, col, s=1.0, cell=1.0, down=False, colfn=None):
    nu, nv = cells(x1 - x0, cell), cells(y1 - y0, cell)
    if not down:
        grid(mat, (x0, y0, z), (x1 - x0, 0, 0), (0, y1 - y0, 0), nu, nv, col, s, colfn)
    else:
        grid(mat, (x0, y1, z), (x1 - x0, 0, 0), (0, y0 - y1, 0), nu, nv, col, s, colfn)


def wall(mat, p0, p1, z0, z1, col, s=1.0, cell=1.0, colfn=None):
    """Vertical wall from p0 to p1 (xy); normal = (p1-p0) x Z (right-hand side when walking p0->p1)."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dy)
    grid(mat, (p0[0], p0[1], z0), (dx, dy, 0), (0, 0, z1 - z0), cells(L, cell), cells(z1 - z0, cell), col, s, colfn)


def box(mat, a, b, col, s=1.0, skip=(), M=None, cell=None, cols=None):
    """Axis-aligned box a(min)..b(max); faces: -x,+x,-y,+y,-z,+z. cols: dict face->colour."""
    x0, y0, z0 = a
    x1, y1, z1 = b
    F = {
        "-x": [(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)],
        "+x": [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],
        "-y": [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)],
        "+y": [(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)],
        "-z": [(x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0)],
        "+z": [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
    }
    for k, pts in F.items():
        if k in skip:
            continue
        c = cols.get(k, col) if cols else col
        if cell and M is None:
            p0, p1, p3 = Vector(pts[0]), Vector(pts[1]), Vector(pts[3])
            du, dv = p1 - p0, p3 - p0
            grid(mat, p0, du, dv, cells(du.length, cell), cells(dv.length, cell), c, s)
        else:
            poly(mat, pts, c, s, M=M)


def mbox(mat, size, col, M, s=1.0, skip=(), cols=None):
    """Box centred at local origin (size = full extents), transformed by M."""
    hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
    box(mat, (-hx, -hy, -hz), (hx, hy, hz), col, s, skip, M=M, cols=cols)


def prism(mat, pts2, z0, z1, col, s=1.0, rows=1, caps=(False, True), M=None, colfn=None, skip_edges=()):
    """Extrude a CCW 2D polygon from z0 to z1 (side faces split into `rows`); skip_edges: edge indices
    (edge i = pts2[i] -> pts2[i+1]) not to emit, e.g. faces buried against a wall."""
    n = len(pts2)
    for r in range(rows):
        za = z0 + (z1 - z0) * r / rows
        zb = z0 + (z1 - z0) * (r + 1) / rows
        for i in range(n):
            if i in skip_edges:
                continue
            a, b = pts2[i], pts2[(i + 1) % n]
            q = [(a[0], a[1], za), (b[0], b[1], za), (b[0], b[1], zb), (a[0], a[1], zb)]
            c = [colfn(p) for p in q] if colfn else col
            poly(mat, q, c, s, M=M)
    if caps[1]:
        poly(mat, [(p[0], p[1], z1) for p in pts2], col, s, M=M)
    if caps[0]:
        poly(mat, [(p[0], p[1], z0) for p in reversed(pts2)], col, s, M=M)


def chamfer_rect(cx, cy, hx, hy, c):
    return [(cx - hx + c, cy - hy), (cx + hx - c, cy - hy), (cx + hx, cy - hy + c), (cx + hx, cy + hy - c),
            (cx + hx - c, cy + hy), (cx - hx + c, cy + hy), (cx - hx, cy + hy - c), (cx - hx, cy - hy + c)]


def lathe(mat, prof, n, col, M=None, cap_top=True, cap_bot=False, s=1.0, smooth=True, uvrect=None, a0=0.0,
          colfn=None):
    """Surface of revolution around local Z. prof: [(r, z)] bottom->top. uvrect: atlas rect for u-around."""
    verts, faces, uvs = [], [], []
    for k, (r, z) in enumerate(prof):
        for j in range(n + 1):
            a = a0 + 2 * math.pi * j / n
            verts.append(XF(M, (r * math.cos(a), r * math.sin(a), z)))
    arc = [0.0]
    for k in range(1, len(prof)):
        arc.append(arc[-1] + math.hypot(prof[k][0] - prof[k - 1][0], prof[k][1] - prof[k - 1][1]))
    rmax = max(p[0] for p in prof)
    for k in range(len(prof) - 1):
        for j in range(n):
            i0 = k * (n + 1) + j
            i1 = i0 + 1
            i2 = i1 + (n + 1)
            i3 = i0 + (n + 1)
            faces.append((i0, i1, i2, i3))
            if uvrect:
                x0, y0, x1, y1 = uvrect
                u0 = (x0 + (x1 - x0) * j / n) / AN
                u1 = (x0 + (x1 - x0) * (j + 1) / n) / AN
                t0 = arc[k] / arc[-1]
                t1 = arc[k + 1] / arc[-1]
                v0 = 1 - (y1 - (y1 - y0) * t0) / AN
                v1 = 1 - (y1 - (y1 - y0) * t1) / AN
                uvs.append([(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
            else:
                circ = 2 * math.pi * rmax
                uvs.append([(circ * j / n / s, arc[k] / s), (circ * (j + 1) / n / s, arc[k] / s),
                            (circ * (j + 1) / n / s, arc[k + 1] / s), (circ * j / n / s, arc[k + 1] / s)])
    cols = [colfn(v) for v in verts] if colfn else col
    emit_indexed(mat, verts, faces, uvs, cols, smooth)
    if cap_top and prof[-1][0] > 1e-4:
        r, z = prof[-1]
        pts = [XF(M, (r * math.cos(a0 + 2 * math.pi * j / n), r * math.sin(a0 + 2 * math.pi * j / n), z)) for j in range(n)]
        c = [colfn(p) for p in pts] if colfn else col
        emit(mat, pts, boxuv(pts, s), c)
    if cap_bot and prof[0][0] > 1e-4:
        r, z = prof[0]
        pts = [XF(M, (r * math.cos(a0 + 2 * math.pi * j / n), r * math.sin(a0 + 2 * math.pi * j / n), z)) for j in reversed(range(n))]
        emit(mat, pts, boxuv(pts, s), col)


def disc_uv(mat, c, r, z, n, rect, col=WHITE, M=None):
    """Flat disc (normal +Z) with atlas-mapped UVs (rect inscribed)."""
    x0, y0, x1, y1 = rect
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hw = (x1 - x0) / 2 - 1
    pts, uvs = [], []
    for j in range(n):
        a = 2 * math.pi * j / n
        pts.append(XF(M, (c[0] + r * math.cos(a), c[1] + r * math.sin(a), z)))
        uvs.append(((cx + hw * math.cos(a)) / AN, 1 - (cy - hw * math.sin(a)) / AN))
    emit(mat, pts, uvs, col)


def tube(mat, p0, p1, r, n, col, caps=False, smooth=True, r1=None):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    if L < 1e-6:
        return
    z = d / L
    x = z.cross(Vector((0, 0, 1)))
    if x.length < 1e-4:
        x = z.cross(Vector((1, 0, 0)))
    x.normalize()
    y = z.cross(x)
    r1 = r if r1 is None else r1
    verts = []
    for k, (pc, rr) in enumerate(((p0, r), (p1, r1))):
        for j in range(n):
            a = 2 * math.pi * j / n
            verts.append(tuple(pc + (x * math.cos(a) + y * math.sin(a)) * rr))
    faces, uvs = [], []
    for j in range(n):
        j1 = (j + 1) % n
        faces.append((j, j1, n + j1, n + j))
        uvs.append([(j / n, 0), ((j + 1) / n, 0), ((j + 1) / n, L), (j / n, L)])
    emit_indexed(mat, verts, faces, uvs, col, smooth)
    if caps:
        emit(mat, [verts[n + j] for j in range(n)], [(0, 0)] * n, col)
        emit(mat, [verts[j] for j in reversed(range(n))], [(0, 0)] * n, col)


def torus(mat, M, R_, r, nu, nv, col):
    verts, faces, uvs = [], [], []
    for i in range(nu):
        a = 2 * math.pi * i / nu
        for j in range(nv):
            b = 2 * math.pi * j / nv
            p = ((R_ + r * math.cos(b)) * math.cos(a), r * math.sin(b), (R_ + r * math.cos(b)) * math.sin(a))
            verts.append(XF(M, p))
    for i in range(nu):
        for j in range(nv):
            i1 = (i + 1) % nu
            j1 = (j + 1) % nv
            faces.append((i * nv + j, i * nv + j1, i1 * nv + j1, i1 * nv + j))
            uvs.append([(0, 0)] * 4)
    emit_indexed(mat, verts, faces, uvs, col, True)


_ICO = {}


def ico(sub):
    if sub not in _ICO:
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
        v = [tuple(x.co) for x in bm.verts]
        f = [tuple(x.index for x in fc.verts) for fc in bm.faces]
        bm.free()
        _ICO[sub] = (v, f)
    return _ICO[sub]


def blob(mat, c, r, col, seed=0, sub=1, squash=(1, 1, 1), noise=0.18, s=1.2, flat_bottom=None, colfn=None, uoff=0.0):
    if uoff:
        mat, uoff = "M_Flower", 0.0
    rr = random.Random(seed)
    v, f = ico(sub)
    ph = [rr.uniform(0, 6.28) for _ in range(6)]
    verts = []
    for p in v:
        n = (math.sin(p[0] * 2.3 + ph[0]) + math.sin(p[1] * 2.9 + ph[1]) + math.sin(p[2] * 3.1 + ph[2])
             + 0.5 * math.sin(p[0] * 5.1 + p[1] * 4.3 + ph[3])) / 3.5
        k = r * (1 + noise * n)
        q = [c[0] + p[0] * k * squash[0], c[1] + p[1] * k * squash[1], c[2] + p[2] * k * squash[2]]
        if flat_bottom is not None and q[2] < flat_bottom:
            q[2] = flat_bottom + (q[2] - flat_bottom) * 0.25
        verts.append(tuple(q))
    uvs = []
    for fc in f:
        pts = [verts[i] for i in fc]
        uvs.append([(u + uoff, vv) for (u, vv) in boxuv(pts, s)])
    cols = [colfn(p) for p in verts] if colfn else col
    emit_indexed(mat, verts, f, uvs, cols, True)


def arect(name, inset=1.5):
    x0, y0, x1, y1 = ATLAS[name]
    return (x0 + inset, y0 + inset, x1 - inset, y1 - inset)


def decal(name, center, n, w, h, col=WHITE, off=0.008, rot=0.0, mat="M_Atlas", flipu=False):
    """Atlas decal: quad of w x h centred at `center`, facing normal n (axis-aligned or any)."""
    n = Vector(n).normalized()
    up = Vector((0, 0, 1)) if abs(n.z) < 0.9 else Vector((0, 1, 0))
    du = up.cross(n).normalized() if abs(n.z) < 0.9 else Vector((1, 0, 0))
    dv = n.cross(du).normalized()
    if rot:
        q = Matrix.Rotation(rot, 3, n)
        du, dv = q @ du, q @ dv
    c = Vector(center) + n * off
    pts = [c - du * w / 2 - dv * h / 2, c + du * w / 2 - dv * h / 2, c + du * w / 2 + dv * h / 2, c - du * w / 2 + dv * h / 2]
    x0, y0, x1, y1 = arect(name)
    uv = [(x0 / AN, 1 - y1 / AN), (x1 / AN, 1 - y1 / AN), (x1 / AN, 1 - y0 / AN), (x0 / AN, 1 - y0 / AN)]
    if flipu:
        uv = [uv[1], uv[0], uv[3], uv[2]]
    emit(mat, [tuple(p) for p in pts], uv, col)


def M_at(x, y, z, rz=0.0, rx=0.0, ry=0.0, sc=1.0):
    return (Matrix.Translation((x, y, z)) @ Matrix.Rotation(rz, 4, "Z") @ Matrix.Rotation(ry, 4, "Y")
            @ Matrix.Rotation(rx, 4, "X") @ Matrix.Scale(sc, 4))


ATLAS = {  # mirrors tools/gen_voiddeck_textures.py
    "chess": (0, 0, 320, 320), "liftdoor": (320, 0, 480, 320), "liftind": (480, 0, 640, 64),
    "liftbtn": (480, 64, 560, 224), "lifttag": (560, 64, 640, 224), "letterbox": (640, 0, 1024, 208),
    "blksign": (640, 208, 1024, 320), "notice": (0, 320, 384, 576), "noball": (384, 320, 512, 448),
    "hosereel": (512, 320, 640, 512), "dbbox": (640, 320, 736, 448), "liftsign": (736, 320, 1024, 384),
    "directory": (736, 384, 1024, 512), "cctv": (384, 448, 512, 512), "stooltop": (0, 576, 128, 704),
    "grating": (128, 576, 256, 704), "playpanel": (256, 576, 512, 704), "heritage": (512, 512, 768, 704),
    "lantern_r": (768, 512, 832, 576), "lantern_y": (832, 512, 896, 576), "lantern_p": (896, 512, 960, 576),
    "lantern_b": (960, 512, 1024, 576), "vending": (768, 576, 896, 832), "fitness": (896, 576, 1024, 704),
    "pillar53": (0, 704, 192, 1024), "hopscotch": (192, 704, 320, 1024), "banner": (320, 704, 768, 832),
    "mural": (320, 832, 1024, 1024), "bin": (896, 704, 1024, 832),
}

MARKERS = []   # (name, pos, facing(3d or 2d) or None, props)


def marker(name, pos, face=None, props=None):
    MARKERS.append((name, tuple(pos), face, props or {}))


# ======================================================================================
# layout constants
# ======================================================================================
X0, X1 = -24.0, 8.0         # void deck extent along the block
YF, YB = -4.0, 6.0          # front (open) edge, back wall
ZC = 3.0                    # soffit
ZBEAM = 2.55                # downstand beam bottom
COL_X = [-20.0, -12.0, -4.0, 4.0]
COL_END = 7.7
ROW_Y = [-3.7, 1.8]
PW = 0.30                   # pillar half-width
LOBBY = (-2.6, 2.6, 9.0)    # lobby recess x0, x1, back wall y
YBACK = 9.25                # exterior back face of the block (wall thickness behind the lobby)
ZG = -0.15                  # grass level
SUN_DIR = Vector((0.5 * math.cos(math.radians(13)), -0.866 * math.cos(math.radians(13)), math.sin(math.radians(13)))).normalized()
TABLE_Z = 0.75
STOOL_R = 0.72


def banded_prism(pts2, z1, top_col=None, rows_top=3, band=0.95, skip_edges=()):
    prism("M_Paint", pts2, 0.0, band, JADE, s=2.0, rows=2, caps=(False, False), skip_edges=skip_edges)
    prism("M_Paint", pts2, band, band + 0.08, MAROON, s=2.0, rows=1, caps=(False, False), skip_edges=skip_edges)
    prism("M_Paint", pts2, band + 0.08, z1, top_col or CREAM, s=2.0, rows=rows_top, caps=(False, False), skip_edges=skip_edges)


def banded_wall(p0, p1, z1, cell=1.0):
    wall("M_Paint", p0, p1, 0.0, 0.95, JADE, s=2.5, cell=cell)
    wall("M_Paint", p0, p1, 0.95, 1.03, MAROON, s=2.5, cell=cell * 3)
    wall("M_Paint", p0, p1, 1.03, z1, CREAM, s=2.5, cell=cell)


def pillar_col(p):
    z = p[2]
    if z < 0.95:
        return JADE
    if z < 1.03:
        return MAROON
    return CREAM


# ======================================================================================
# void deck structure
# ======================================================================================
def build_structure():
    # --- floor: 300 mm tiles (texture repeat 1.2 m); finer cells near the table for the AO bake
    floor_rect("M_Floor", -1.5, 1.5, -1.5, 1.5, 0.0, FLOOR, s=1.2, cell=0.25)      # fine core: AO under table/stools
    floor_rect("M_Floor", -8, 8, YF, -1.5, 0.0, FLOOR, s=1.2, cell=0.5)
    floor_rect("M_Floor", -8, 8, 1.5, YB, 0.0, FLOOR, s=1.2, cell=0.5)
    floor_rect("M_Floor", -8, -1.5, -1.5, 1.5, 0.0, FLOOR, s=1.2, cell=0.5)
    floor_rect("M_Floor", 1.5, 8, -1.5, 1.5, 0.0, FLOOR, s=1.2, cell=0.5)
    floor_rect("M_Floor", X0, -8, YF, YB, 0.0, FLOOR, s=1.2, cell=1.0)
    # lobby floor (lighter glazed tiles)
    floor_rect("M_Floor", LOBBY[0], LOBBY[1], YB, LOBBY[2], 0.0, LOBBY_TILE, s=1.2, cell=0.6)
    # slab edge (front step down to the apron) and +X end step
    wall("M_Concrete", (X0, YF), (X1, YF), ZG + 0.03, 0.0, CONCRETE, s=2.0, cell=2.0)
    wall("M_Concrete", (X1, YF), (X1, YB), ZG + 0.03, 0.0, CONCRETE, s=2.0, cell=2.0)
    # --- soffit + beams
    floor_rect("M_Paint", -10, 8, YF, YB, ZC, CEIL, s=2.5, cell=1.0, down=True)
    floor_rect("M_Paint", X0, -10, YF, YB, ZC, CEIL, s=2.5, cell=2.0, down=True)
    floor_rect("M_Paint", LOBBY[0], LOBBY[1], YB, LOBBY[2], 2.8, CEIL, s=2.5, cell=1.0, down=True)
    # front fascia beam (outer face = slab edge of the block above)
    XE = COL_END - 0.15                                   # inner face of the +X end beam
    box("M_Paint", (X0, YF, ZBEAM), (X1, YF + 0.35, ZC), CREAM, s=2.5, skip=("+z", "-x"), cell=1.5)
    # end (+X) beam between the front fascia and the back wall
    box("M_Paint", (XE, YF + 0.35, ZBEAM), (X1, YB, ZC), CREAM, s=2.5, skip=("+z", "-y", "+y"), cell=1.5)
    # cross beams along y (between fascia and back wall), middle beam segments along x between them
    for x in COL_X:
        box("M_Paint", (x - 0.15, YF + 0.35, ZBEAM), (x + 0.15, YB, ZC), CEIL, s=2.5, skip=("+z", "-y", "+y"), cell=1.5)
    xs = [X0] + sum([[x - 0.15, x + 0.15] for x in COL_X], []) + [XE]
    for i in range(0, len(xs), 2):
        box("M_Paint", (xs[i], ROW_Y[1] - 0.15, ZBEAM), (xs[i + 1], ROW_Y[1] + 0.15, ZC), CEIL, s=2.5,
            skip=("+z", "-x", "+x"), cell=1.5)
    # --- pillars (chamfered, jade dado + maroon stripe, cream above)
    for x in COL_X:
        for y in ROW_Y:
            banded_prism(chamfer_rect(x, y, PW, PW, 0.05), ZBEAM)
    for y in ROW_Y:
        banded_prism(chamfer_rect(COL_END, y, PW, PW, 0.05), ZBEAM)
    # engaged end pillar against the back wall: square back corners, no face buried in the wall
    banded_prism([(COL_END - PW + 0.05, YB - 0.6), (COL_END + PW - 0.05, YB - 0.6), (COL_END + PW, YB - 0.55),
                  (COL_END + PW, YB), (COL_END - PW, YB), (COL_END - PW, YB - 0.55)], ZBEAM, skip_edges=(3,))
    # --- back wall (y = YB) with lobby opening; jade dado
    def wall_col(p):
        return JADE if p[2] < 0.95 else (MAROON if p[2] < 1.03 else CREAM)
    banded_wall((LOBBY[1], YB), (X1, YB), ZC)
    banded_wall((X0, YB), (LOBBY[0], YB), ZC)
    # the opening's lintel
    wall("M_Paint", (LOBBY[0], YB), (LOBBY[1], YB), 2.8, ZC, CREAM, s=2.5, cell=1.0)
    # gable end wall at X0 (inner face +x)
    banded_wall((X0, YF), (X0, YB), ZC, cell=1.5)
    # lobby recess walls (tiled lower, painted upper)
    def lob_col(p):
        return LOBBY_TILE if p[2] < 1.5 else CREAM
    wall("M_Floor", (LOBBY[0], YB), (LOBBY[0], LOBBY[2]), 0, 1.5, LOBBY_TILE, s=1.2, cell=0.6)
    wall("M_Paint", (LOBBY[0], YB), (LOBBY[0], LOBBY[2]), 1.5, 2.8, CREAM, s=2.5, cell=0.8)
    wall("M_Floor", (LOBBY[1], LOBBY[2]), (LOBBY[1], YB), 0, 1.5, LOBBY_TILE, s=1.2, cell=0.6)
    wall("M_Paint", (LOBBY[1], LOBBY[2]), (LOBBY[1], YB), 1.5, 2.8, CREAM, s=2.5, cell=0.8)
    wall("M_Floor", (LOBBY[0], LOBBY[2]), (LOBBY[1], LOBBY[2]), 0, 2.8, LOBBY_TILE, s=1.2, cell=0.7)
    # skirting along the back wall
    box("M_Paint", (X0, YB - 0.012, 0), (LOBBY[0], YB, 0.1), mulc(JADE, 0.7), skip=("-z", "+y", "-x", "+x"))
    box("M_Paint", (LOBBY[1], YB - 0.012, 0), (X1, YB, 0.1), mulc(JADE, 0.7), skip=("-z", "+y", "-x", "+x"))

    # --- the block above (seen from outside only): slab edge + storeys + roof
    top = ZC + 0.25 + 11 * 2.8
    zs = ZC + 0.25
    # front (corridor side, -Y) & back (window side, +Y) elevations as per-storey strips
    for k in range(11):
        za, zb = zs + k * 2.8, zs + (k + 1) * 2.8
        facade_strip((X0, YF), (X1, YF), za, zb, "corridor", CREAM)
        facade_strip((X1, YBACK), (X0, YBACK), za, zb, "window", CREAM)
    wall("M_Paint", (X0, YF), (X1, YF), ZC, zs, CREAM, s=3.0, cell=4.0)  # slab edge band
    # ends
    wall("M_Paint", (X1, YF), (X1, YBACK), ZC, top, CREAM, s=3.0, cell=6.0)
    wall("M_Paint", (X1, YB), (X1, YBACK), ZG, ZC, CREAM, s=3.0, cell=3.0)          # end of the lobby core
    wall("M_Paint", (X0, YBACK), (X0, YF), ZC, top, CREAM, s=3.0, cell=6.0)
    wall("M_Paint", (X0 - 0.25, YBACK), (X0 - 0.25, YF), ZG, ZC, CREAM, s=3.0, cell=3.0)   # gable exterior
    box("M_Paint", (X0 - 0.25, YF, ZG), (X0, YF + 0.001, ZC), CREAM, skip=("+y", "-x", "+x", "+z", "-z"))
    # back of the block at ground level (behind the lobby wall) — simple
    wall("M_Paint", (X1, YBACK), (X0 - 0.25, YBACK), ZG, ZC + 0.25, CREAM, s=3.0, cell=4.0)
    # roof + parapet + water tank
    floor_rect("M_Concrete", X0, X1, YF, YBACK, top, CONCRETE, s=4.0, cell=8.0)
    box("M_Paint", (X0 + 6, 0, top), (X0 + 12, 5, top + 3.2), CREAM, s=3.0, skip=("-z",))


def facade_strip(p0, p1, za, zb, kind, col, unit=6.4):
    """One storey of HDB facade texture between p0 and p1 (normal = (p1-p0) x Z)."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dy)
    v0, v1 = (0.5, 1.0) if kind == "corridor" else (0.0, 0.5)
    v0 += 0.002
    v1 -= 0.002
    n = max(1, int(round(L / unit)))
    for i in range(n):
        a = (p0[0] + dx * i / n, p0[1] + dy * i / n)
        b = (p0[0] + dx * (i + 1) / n, p0[1] + dy * (i + 1) / n)
        pts = [(a[0], a[1], za), (b[0], b[1], za), (b[0], b[1], zb), (a[0], a[1], zb)]
        emit("M_Facade", pts, [(0, v0), (1, v0), (1, v1), (0, v1)], J(col, 0.03))


# ======================================================================================
# lift lobby, letterboxes, notices
# ======================================================================================
def build_lobby():
    yb = LOBBY[2]
    for cx in (-1.1, 1.1):
        # stainless frame
        box("M_Metal", (cx - 0.62, yb - 0.05, 0), (cx - 0.52, yb, 2.25), STEEL, skip=("+y", "-z"))
        box("M_Metal", (cx + 0.52, yb - 0.05, 0), (cx + 0.62, yb, 2.25), STEEL, skip=("+y", "-z"))
        box("M_Metal", (cx - 0.52, yb - 0.05, 2.15), (cx + 0.52, yb, 2.25), STEEL, skip=("+y", "-x", "+x"))
        decal("liftdoor", (cx, yb, 1.075), (0, -1, 0), 1.04, 2.15, off=0.02)
        decal("liftind", (cx, yb, 2.42), (0, -1, 0), 0.5, 0.2, off=0.01)
        decal("lifttag", (cx - 0.78, yb, 1.95), (0, -1, 0), 0.16, 0.32, off=0.01)
    decal("liftbtn", (0.0, yb, 1.1), (0, -1, 0), 0.14, 0.28, off=0.012)
    decal("mural", (LOBBY[0], 7.5, 1.9), (1, 0, 0), 2.5, 0.68, off=0.008)
    decal("cctv", (LOBBY[1], 6.8, 2.2), (-1, 0, 0), 0.3, 0.15)
    # lobby signage over the opening
    decal("liftsign", (0.0, YB, 2.94), (0, -1, 0), 1.35, 0.3, off=0.01)
    # main wall features (wall faces -Y at y = YB)
    decal("letterbox", (-4.7, YB, 1.28), (0, -1, 0), 3.0, 1.62, off=0.012)
    box("M_Metal", (-6.2, YB - 0.1, 0.42), (-3.2, YB, 0.47), STEEL, skip=("+y", "-x", "+x"))       # letterbox sill
    box("M_Metal", (-6.2, YB - 0.1, 2.09), (-3.2, YB, 2.14), STEEL, skip=("+y", "-x", "+x"))
    box("M_Metal", (-6.25, YB - 0.1, 0.42), (-6.2, YB, 2.14), STEEL, skip=("+y",))
    box("M_Metal", (-3.2, YB - 0.1, 0.42), (-3.15, YB, 2.14), STEEL, skip=("+y",))
    decal("mural", (-9.8, YB, 1.75), (0, -1, 0), 4.4, 1.2, off=0.008)
    decal("directory", (3.4, YB, 1.55), (0, -1, 0), 1.0, 0.44, off=0.01)
    decal("notice", (5.15, YB, 1.6), (0, -1, 0), 1.5, 1.0, off=0.028)
    box("M_Rough", (4.38, YB - 0.018, 1.08), (5.92, YB, 2.12), C(0.45, 0.32, 0.22), skip=("+y",))
    decal("hosereel", (6.65, YB, 1.0), (0, -1, 0), 0.6, 0.9, off=0.12)
    box("M_Plastic", (6.35, YB - 0.12, 0.55), (6.95, YB, 1.45), C(0.72, 0.12, 0.10), skip=("+y", "-y"))
    decal("dbbox", (-12.9, YB, 1.55), (0, -1, 0), 0.5, 0.67, off=0.1)
    box("M_Metal", (-13.15, YB - 0.1, 1.21), (-12.65, YB, 1.89), C(0.55, 0.57, 0.54), skip=("+y", "-y"))
    decal("cctv", (2.9, YB, 2.25), (0, -1, 0), 0.3, 0.15)
    decal("noball", (-4.0 + PW, ROW_Y[1], 1.55), (1, 0, 0), 0.34, 0.34)
    decal("noball", (-15.2, YB, 1.5), (0, -1, 0), 0.4, 0.4)
    # vending machine
    box("M_Plastic", (-14.4, YB - 0.8, 0), (-13.5, YB - 0.05, 1.8), C(0.70, 0.12, 0.12), skip=("-y", "-z"))
    decal("vending", (-13.95, YB - 0.8, 0.9), (0, -1, 0), 0.9, 1.8, off=0.0)   # the box has no -y face
    # CCTV domes on the ceiling
    for (x, y) in ((1.8, 5.4), (-6.0, -2.6)):
        lathe("M_Plastic", [(0.08, ZC - 0.07), (0.07, ZC - 0.03), (0.08, ZC)], 10, C(0.9, 0.9, 0.9), M=M_at(x, y, 0), cap_top=False)
        blob("M_Plastic", (x, y, ZC - 0.07), 0.055, DARK, sub=1, noise=0.0)


# ======================================================================================
# hero: stone table + 4 stools (terrazzo, mosaic chessboard)
# ======================================================================================
def stone_table(cx, cy, rz=0.0, markers=False):
    M = M_at(cx, cy, 0, rz)
    top_r = 0.45
    lathe("M_Terrazzo", [(0.25, 0.0), (0.25, 0.05), (0.19, 0.09), (0.15, 0.16), (0.13, 0.40), (0.14, 0.60),
                         (0.20, 0.655), (0.40, 0.675), (top_r, 0.69), (top_r + 0.008, 0.72), (top_r, TABLE_Z)],
          28, TERRAZZO, M=M, cap_top=True, s=0.8)
    # mosaic chessboard inlay, very slightly proud of the top
    x0, y0, x1, y1 = arect("chess", 2)
    h = 0.30
    zt = TABLE_Z + 0.006
    box("M_Terrazzo", (-h, -h, TABLE_Z - 0.002), (h, h, zt), TERRAZZO, s=0.8, skip=("+z", "-z"), M=M)
    pts = [XF(M, p) for p in ((-h, -h, zt), (h, -h, zt), (h, h, zt), (-h, h, zt))]
    emit("M_Atlas", pts, [(x0 / AN, 1 - y1 / AN), (x1 / AN, 1 - y1 / AN), (x1 / AN, 1 - y0 / AN), (x0 / AN, 1 - y0 / AN)], WHITE)
    # contact shadow skirt on the floor
    for k in range(4):
        a = rz + k * math.pi / 2
        sx, sy = cx + STOOL_R * math.cos(a), cy + STOOL_R * math.sin(a)
        stool(sx, sy, a)
    if markers:
        marker("PRO_Table", (cx, cy, TABLE_Z), (0, -1), {"board_top": TABLE_Z + 0.006})
        # Boon on the -X stool (faces +X), Sparky on the +X stool (faces -X)
        fe = STOOL_R - 0.17
        marker("PRO_Stool_Boon", (cx - fe, cy, 0.0), (1, 0), {"seat_height": 0.45, "seat_centre_offset": 0.17})
        marker("PRO_Stool_Sparky", (cx + fe, cy, 0.0), (-1, 0), {"seat_height": 0.45, "seat_centre_offset": 0.17})
        marker("PRO_SeatTop_Boon", (cx - STOOL_R, cy, 0.45), (1, 0))
        marker("PRO_SeatTop_Sparky", (cx + STOOL_R, cy, 0.45), (-1, 0))


def stool(x, y, a):
    M = M_at(x, y, 0, a)
    lathe("M_Terrazzo", [(0.16, 0.0), (0.16, 0.03), (0.125, 0.08), (0.11, 0.25), (0.13, 0.38), (0.165, 0.42),
                         (0.17, 0.44), (0.165, 0.45)], 20, TERRAZZO, M=M, cap_top=False, s=0.8)
    disc_uv("M_Atlas", (0, 0), 0.165, 0.45, 20, arect("stooltop", 2), WHITE, M=M)


def skirt(cx, cy, r0, r1, dark, n=20, z=0.003):
    """Soft contact-shadow ring on the floor (floor material, darkened vertex colour -> seamless)."""
    verts, faces, uvs, cols = [], [], [], []
    for k, (r, c) in enumerate(((r0, dark), ((r0 + r1) / 2, 1 - (1 - dark) * 0.35), (r1, 1.0))):
        for j in range(n):
            a = 2 * math.pi * j / n
            verts.append((cx + r * math.cos(a), cy + r * math.sin(a), z))
            cols.append(mulc(FLOOR, c))
    for k in range(2):
        for j in range(n):
            j1 = (j + 1) % n
            faces.append((k * n + j, (k + 1) * n + j, (k + 1) * n + j1, k * n + j1))
    for f in faces:
        uvs.append([(verts[i][0] / 1.2, verts[i][1] / 1.2) for i in f])
    emit_indexed("M_Floor", verts, faces, uvs, cols, False)


# ======================================================================================
# props inside the deck
# ======================================================================================
def pot(x, y, r=0.2, h=0.32, col=TERRACOTTA, seed=0, plant="leafy", sub=1):
    M = M_at(x, y, 0)
    lathe("M_Plastic", [(r * 0.72, 0.0), (r * 0.78, 0.02), (r, h - 0.03), (r * 1.08, h - 0.02), (r * 1.08, h), (r * 0.95, h)],
          10, col, M=M, cap_top=False)
    poly("M_Rough", [(x + r * 0.95 * math.cos(a), y + r * 0.95 * math.sin(a), h - 0.03) for a in
                     [2 * math.pi * j / 10 for j in range(10)]], SOIL)
    rr = random.Random(seed)
    if plant == "leafy":
        for k in range(3):
            blob("M_Foliage", (x + rr.uniform(-0.08, 0.08), y + rr.uniform(-0.08, 0.08), h + 0.18 + k * 0.12),
                 r * rr.uniform(1.0, 1.4), J(LEAF, 0.08, rr), seed=seed * 7 + k, sub=sub, squash=(1, 1, 0.8), s=0.9)
    elif plant == "bougain":
        for k in range(4):
            blob("M_Foliage", (x + rr.uniform(-0.15, 0.15), y + rr.uniform(-0.15, 0.15), h + 0.25 + rr.uniform(0, 0.4)),
                 r * rr.uniform(1.0, 1.5), J(LEAF, 0.08, rr), seed=seed * 7 + k, sub=sub, s=0.9, uoff=0.5)
        tube("M_Rough", (x, y, h), (x + 0.05, y, h + 0.5), 0.02, 4, BARK)
    elif plant == "tall":  # pandan / snake plant: spiky leaves
        for k in range(9):
            a = 2 * math.pi * k / 9 + rr.uniform(-0.2, 0.2)
            L = rr.uniform(0.45, 0.8)
            p0 = (x, y, h - 0.02)
            p1 = (x + math.cos(a) * 0.18, y + math.sin(a) * 0.18, h + L)
            tube("M_Foliage", p0, p1, 0.035, 3, J(LEAF, 0.1, rr), r1=0.008)


def plastic_stool(x, y, a, col, stack=1):
    """The ubiquitous moulded plastic stool (kopitiam / void-deck issue), optionally stacked."""
    for k in range(stack):
        M = M_at(x, y, k * 0.07, a)
        # tapered square-ish body (8-sided lathe, 45 deg offset so faces read as a square stool);
        # lower stools of a stack only show their bottom rim below the one above
        prof = [(0.21, 0.0), (0.2, 0.02), (0.165, 0.43), (0.175, 0.44), (0.175, 0.46)]
        if k < stack - 1:
            prof = [(0.21, 0.0), (0.2, 0.02), (0.2 - 0.035 * 0.05 / 0.41, 0.07)]
        lathe("M_Plastic", prof, 8, col, M=M, cap_top=(k == stack - 1), a0=math.pi / 8, smooth=False)


def bicycle(x, y, a, col, basket=False, lean=0.0):
    M = M_at(x, y, 0, a, rx=lean)
    Rw = 0.33
    for wx in (-0.52, 0.52):
        Mw = M @ Matrix.Translation((wx, 0, Rw))
        torus("M_Plastic", Mw, Rw - 0.012, 0.022, 18, 4, DARK)
        with DETAIL():
            torus("M_Metal", Mw, Rw - 0.045, 0.008, 18, 3, STEEL)
            for k in range(8):
                ang = k * math.pi / 8
                p0 = Mw @ Vector((math.cos(ang) * (Rw - 0.05), 0, math.sin(ang) * (Rw - 0.05)))
                p1 = Mw @ Vector((-math.cos(ang) * (Rw - 0.05), 0, -math.sin(ang) * (Rw - 0.05)))
                tube("M_Metal", p0, p1, 0.0025, 3, STEEL, smooth=False)
        tube("M_Metal", Mw @ Vector((0, -0.05, 0)), Mw @ Vector((0, 0.05, 0)), 0.02, 6, STEEL)
    P = lambda px, pz: M @ Vector((px, 0, pz))
    bb, seat, head, rear, front = P(-0.05, 0.30), P(-0.18, 0.82), P(0.40, 0.86), P(-0.52, Rw), P(0.52, Rw)
    for (p0, p1) in ((bb, seat), (seat, head), (bb, head), (bb, rear), (seat, rear), (head, front)):
        tube("M_Plastic", p0, p1, 0.02, 6, col)
    tube("M_Metal", seat, P(-0.2, 0.92), 0.012, 4, STEEL)
    mbox("M_Rough", (0.24, 0.12, 0.05), DARK, M @ Matrix.Translation((-0.2, 0, 0.94)))
    tube("M_Metal", head, P(0.36, 1.0), 0.013, 4, STEEL)
    tube("M_Metal", M @ Vector((0.36, -0.28, 1.0)), M @ Vector((0.36, 0.28, 1.0)), 0.012, 4, STEEL)
    for sy in (-0.28, 0.28):
        tube("M_Rough", M @ Vector((0.36, sy, 1.0)), M @ Vector((0.36, sy * 0.72, 1.0)), 0.018, 5, DARK)
    if basket:
        mbox("M_Metal", (0.26, 0.34, 0.2), C(0.30, 0.30, 0.32), M @ Matrix.Translation((0.62, 0, 0.92)), skip=("+z",))
    with DETAIL():
        mbox("M_Rough", (0.12, 0.05, 0.03), DARK, M @ Matrix.Translation((-0.05, 0.1, 0.3)))
        tube("M_Metal", P(-0.02, 0.3), M @ Vector((-0.1, 0.25, 0.02)), 0.008, 3, STEEL)


def lantern(x, y, z, key, drop=0.25, r=0.13, h=0.28):
    """Octagonal paper lantern with atlas face; string to z + drop."""
    M = M_at(x, y, z - h / 2, R.uniform(0, 1))
    prof = [(r * 0.35, 0.0), (r * 0.80, 0.04), (r, h * 0.3), (r, h * 0.7), (r * 0.80, h - 0.04), (r * 0.35, h)]
    lathe("M_Atlas", prof, 8, WHITE, M=M, cap_top=True, cap_bot=True, smooth=True, uvrect=arect(key, 2))
    tube("M_Rough", (x, y, z + h / 2), (x, y, z + h / 2 + drop), 0.003, 3, DARK, smooth=False)
    # tassel
    tube("M_Plastic", (x, y, z - h / 2), (x, y, z - h / 2 - 0.12), 0.012, 4, C(0.85, 0.15, 0.1), r1=0.02)


def tube_light(x, y, rot=0.0, z=ZC, n_tubes=2, L=1.24):
    """Surface-mounted batten (housing + emissive tubes); returns marker position."""
    M = M_at(x, y, z, rot)
    mbox("M_Paint", (L + 0.04, 0.16, 0.05), C(0.97, 0.97, 0.96), M @ Matrix.Translation((0, 0, -0.025)), skip=("+z",))
    for k in range(n_tubes):
        oy = (k - (n_tubes - 1) / 2) * 0.06
        p0 = M @ Vector((-L / 2, oy, -0.075))
        p1 = M @ Vector((L / 2, oy, -0.075))
        tube("M_Tube", p0, p1, 0.016, 6, TUBE, caps=False)
    return tuple(M @ Vector((0, 0, -0.1)))


def build_props():
    stone_table(0.0, 0.0, 0.0, markers=True)
    table_things()
    birdcage(3.3, -3.25, ZBEAM)
    # hopscotch painted on the floor, left of the table (1 m x 3 m)
    decal("hopscotch", (-2.9, -1.2, 0.0), (0, 0, 1), 1.0, 3.0, off=0.012, rot=math.radians(90 - 8))
    # front-left pillar cluster: potted plants tended by residents
    fx = -4.0
    pot(fx + 0.55, -3.45, 0.22, 0.34, TERRACOTTA, 1, "bougain")
    pot(fx + 0.55, -2.95, 0.16, 0.26, C(0.28, 0.42, 0.62), 2, "leafy")
    pot(fx - 0.5, -3.3, 0.2, 0.4, C(0.82, 0.78, 0.70), 3, "tall")
    pot(fx + 0.1, -3.1 + 0.55, 0.14, 0.24, TERRACOTTA, 4, "leafy")
    # front-right pillar: pots + a stone bench
    pot(4.0 - 0.55, -3.45, 0.18, 0.3, TERRACOTTA, 5, "leafy")
    pot(4.0 - 0.55, -2.9, 0.22, 0.36, C(0.30, 0.50, 0.46), 6, "tall")
    # stone two-seat bench against the middle-row pillar (-4, 1.8), facing the table
    bench(-4.0 + 0.95, ROW_Y[1] - 0.05, math.pi / 2)
    plastic_stool(-4.0 - 0.8, ROW_Y[1] + 0.5, 0.3, C(0.22, 0.42, 0.72))
    plastic_stool(-4.0 - 1.25, ROW_Y[1] - 0.15, -0.5, C(0.85, 0.24, 0.20), stack=3)
    # bicycles parked along the front edge between the right pillars (and a rail)
    for k, (x, a, col, bk) in enumerate(((5.25, math.radians(100), C(0.20, 0.35, 0.55), True),
                                          (6.05, math.radians(80), C(0.80, 0.78, 0.74), False),
                                          (6.85, math.radians(95), C(0.62, 0.16, 0.14), True))):
        bicycle(x, -2.95, a, col, bk, lean=math.radians(4 if k % 2 else -4))
    tube("M_Metal", (4.5, -3.72, 0.55), (7.3, -3.72, 0.55), 0.024, 6, STEEL)
    for x in (4.6, 5.9, 7.2):
        tube("M_Metal", (x, -3.72, 0.0), (x, -3.72, 0.55), 0.024, 6, STEEL)
    # rubbish bin by the right middle pillar
    lathe("M_Plastic", [(0.24, 0.0), (0.26, 0.85), (0.28, 0.86), (0.28, 0.92)], 12, C(0.20, 0.50, 0.30),
          M=M_at(4.0 - 0.6, ROW_Y[1] + 0.1, 0), cap_top=True)
    # pillar block-number panels (face the table and the camera) + no-ball signs
    for x in (-4.0, 4.0, -12.0, -20.0):
        decal("pillar53", (x, ROW_Y[0] + PW, 1.92), (0, 1, 0), 0.5, 0.83, off=0.008)
        decal("pillar53", (x, ROW_Y[0] - PW, 1.92), (0, -1, 0), 0.5, 0.83, off=0.008)
    for x in (-4.0, 4.0, -12.0):
        decal("pillar53", (x, ROW_Y[1] + PW, 1.92), (0, 1, 0), 0.5, 0.83, off=0.008)
    decal("noball", (4.0 - PW, ROW_Y[0], 1.45), (-1, 0, 0), 0.32, 0.32)
    decal("blksign", (COL_END + 0.3, 0.0, 2.78), (1, 0, 0), 1.2, 0.35, off=0.01)
    decal("blksign", (-6.0, YF, 2.78), (0, -1, 0), 1.2, 0.35, off=0.01)
    # downpipe on the front-left pillar
    tube("M_Plastic", (-4.0 - PW - 0.06, ROW_Y[0] - 0.2, 0.05), (-4.0 - PW - 0.06, ROW_Y[0] - 0.2, ZC), 0.05, 8, C(0.70, 0.70, 0.68))
    # Mid-Autumn banner on the front beam's inner face + lanterns strung between beams
    decal("banner", (-2.2, YF + 0.35, 2.74), (0, 1, 0), 2.1, 0.6, off=0.012)
    keys = ["lantern_r", "lantern_y", "lantern_p", "lantern_b"]
    # string A: across the bay just inside the front beam
    ys = -2.9
    tube("M_Rough", (-4.0, ys, 2.62), (4.0, ys, 2.62), 0.004, 3, DARK, smooth=False)
    for k, x in enumerate([-3.4, -2.6, -1.8, -1.0, 1.0, 1.8, 2.6, 3.4]):
        dz = (0.0, 0.08, 0.03, 0.1)[k % 4]
        lantern(x, ys, 2.62 - 0.26 - dz, keys[k % 4], drop=0.14 + dz, r=0.1, h=0.22)
    # fluorescent battens — PRO_Lamp markers, numbered by distance to the table
    lamps = []
    for x in (-10.0, -6.0, -2.0, 2.0, 6.0):
        for y in (-1.3, 3.9):
            lamps.append(tube_light(x, y, math.pi / 2 if x in (-2.0, 2.0) else 0.0, z=ZC))
    for x in (-22.0, -16.0):
        for y in (-1.3, 3.9):
            lamps.append(tube_light(x, y, 0.0))
    lamps.append(tube_light(0.0, 7.5, 0.0, z=2.8))   # lift lobby
    lamps.sort(key=lambda p: math.hypot(p[0], p[1]))
    for i, p in enumerate(lamps):
        marker("PRO_Lamp_%d" % (i + 1), p, None, {"type": "fluorescent", "length": 1.24, "color": "#eef4ff"})


def birdcage(x, y, z_hook):
    """Songbird cage hung from the beam (void-deck bird-singing uncles)."""
    BAMBOO = C(0.78, 0.62, 0.40)
    zb = z_hook - 0.62
    M = M_at(x, y, zb)
    tube("M_Metal", (x, y, z_hook), (x, y, zb + 0.46), 0.004, 3, DARK, smooth=False)
    lathe("M_Rough", [(0.15, 0.0), (0.155, 0.02), (0.155, 0.05), (0.15, 0.06)], 14, BAMBOO, M=M, cap_top=True, cap_bot=True)
    lathe("M_Rough", [(0.15, 0.32), (0.12, 0.38), (0.06, 0.42), (0.015, 0.44)], 14, BAMBOO, M=M, cap_top=True, cap_bot=True)
    for tier, nb in ((DETAIL, 20), (MOBILE, 8)):
        with tier():
            for k in range(nb):
                a = 2 * math.pi * k / nb
                tube("M_Rough", (x + 0.145 * math.cos(a), y + 0.145 * math.sin(a), zb + 0.05),
                     (x + 0.145 * math.cos(a), y + 0.145 * math.sin(a), zb + 0.33), 0.0035, 3, BAMBOO, smooth=False)
    tube("M_Rough", (x - 0.13, y, zb + 0.16), (x + 0.13, y, zb + 0.16), 0.006, 4, BAMBOO)
    blob("M_Plastic", (x + 0.02, y, zb + 0.2), 0.035, C(0.95, 0.78, 0.25), sub=1, squash=(1.4, 0.8, 0.9), noise=0.0)
    blob("M_Plastic", (x + 0.055, y, zb + 0.225), 0.02, C(0.25, 0.25, 0.22), sub=1, noise=0.0)


def table_things():
    # Mr. Boon's takeaway kopi in a plastic bag (string loop + straw) and his walking cane
    kx, ky = -0.27, -0.24
    blob("M_Plastic", (kx, ky, TABLE_Z + 0.05), 0.042, C(0.64, 0.42, 0.24), sub=2, squash=(0.9, 0.9, 1.25), noise=0.04,
         flat_bottom=TABLE_Z + 0.009)
    blob("M_Plastic", (kx, ky, TABLE_Z + 0.108), 0.014, C(0.92, 0.92, 0.9), sub=1, noise=0.1)            # knot
    tube("M_Plastic", (kx + 0.005, ky, TABLE_Z + 0.07), (kx + 0.03, ky - 0.01, TABLE_Z + 0.19), 0.0035, 5, C(0.95, 0.45, 0.55))
    torus("M_Plastic", M_at(kx - 0.015, ky, TABLE_Z + 0.125, 0.4, rx=0.3), 0.017, 0.0025, 10, 3, C(0.92, 0.92, 0.9))  # string loop
    CANE = C(0.30, 0.20, 0.12)
    tube("M_Plastic", (-0.50, -0.50, 0.0), (-0.40, -0.40, 0.84), 0.013, 6, CANE)
    tube("M_Plastic", (-0.40, -0.40, 0.84), (-0.31, -0.35, 0.86), 0.014, 6, CANE)
    lathe("M_Rough", [(0.017, 0.0), (0.017, 0.03)], 6, DARK, M=M_at(-0.50, -0.50, 0.0), cap_top=True)
    # folded newspaper left on the empty stool
    mbox("M_Plastic", (0.30, 0.21, 0.018), C(0.88, 0.87, 0.83), M_at(0.0, STOOL_R, 0.462, 0.25), skip=("-z",))
    mbox("M_Plastic", (0.30, 0.012, 0.004), C(0.25, 0.25, 0.28), M_at(0.0, STOOL_R, 0.478, 0.25) @ Matrix.Translation((0, 0.06, 0)), skip=("-z",))
    # a child's kick scooter left by the hopscotch
    M = M_at(-2.1, -2.75, 0, math.radians(35))
    mbox("M_Plastic", (0.55, 0.12, 0.03), C(0.25, 0.70, 0.72), M @ Matrix.Translation((0, 0, 0.065)))
    for wx in (-0.25, 0.3):
        torus("M_Plastic", M @ Matrix.Translation((wx, 0, 0.05)), 0.035, 0.015, 10, 4, C(0.95, 0.40, 0.60))
    p0 = M @ Vector((0.3, 0, 0.07))
    p1 = M @ Vector((0.34, 0, 0.78))
    tube("M_Metal", p0, p1, 0.013, 6, STEEL)
    tube("M_Plastic", M @ Vector((0.34, -0.17, 0.78)), M @ Vector((0.34, 0.17, 0.78)), 0.016, 6, C(0.95, 0.40, 0.60))


def bench(x, y, a):
    M = M_at(x, y, 0, a)
    mbox("M_Terrazzo", (1.2, 0.38, 0.07), TERRAZZO, M @ Matrix.Translation((0, 0, 0.415)), s=0.8)
    for sx in (-0.45, 0.45):
        mbox("M_Terrazzo", (0.1, 0.32, 0.38), TERRAZZO, M @ Matrix.Translation((sx, 0, 0.19)), s=0.8, skip=("+z", "-z"))


# ======================================================================================
# outside: verge, drain, paths, playground, trees, linkway, neighbouring blocks
# ======================================================================================
def ground_col(p):
    """Grass: darker near the block, patchy sun-bleached variation (smooth pseudo-noise)."""
    d = min(abs(p[1] - YF), 30.0)
    k = 0.84 + 0.16 * min(1.0, d / 12.0)
    n = (math.sin(p[0] * 0.31 + 1.3) * math.sin(p[1] * 0.27 + 0.4) + 0.5 * math.sin(p[0] * 0.83 - p[1] * 0.61)) / 1.5
    dry = max(0.0, n) * 0.35
    c = mulc(GRASS, k * (1 + 0.08 * n))
    return (c[0] * (1 + dry * 0.9), c[1] * (1 + dry * 0.25), c[2] * (1 - dry * 0.2), 1.0)


def build_outside():
    # drain apron + grating along the front and the +X end
    floor_rect("M_Concrete", X0, X1 + 0.6, YF - 0.6, YF, ZG + 0.03, CONCRETE, s=2.0, cell=2.0)
    floor_rect("M_Concrete", X1, X1 + 0.6, YF, YBACK, ZG + 0.03, CONCRETE, s=2.0, cell=2.0)
    x0, y0, x1, y1 = arect("grating")
    for k in range(int((X1 + 0.9 - X0) / 1.0)):
        xa = X0 + k * 1.0
        pts = [(xa, YF - 0.9, ZG + 0.01), (xa + 1.0, YF - 0.9, ZG + 0.01), (xa + 1.0, YF - 0.6, ZG + 0.01), (xa, YF - 0.6, ZG + 0.01)]
        emit("M_Atlas", pts, [(x0 / AN, 1 - y1 / AN), (x1 / AN, 1 - y1 / AN), (x1 / AN, 1 - y0 / AN), (x0 / AN, 1 - y0 / AN)], C(0.8, 0.8, 0.8))
    for k in range(int((YBACK - YF + 0.9) / 1.0)):
        ya = YF - 0.9 + k * 1.0
        pts = [(X1 + 0.6, ya, ZG + 0.01), (X1 + 0.9, ya, ZG + 0.01), (X1 + 0.9, ya + 1.0, ZG + 0.01), (X1 + 0.6, ya + 1.0, ZG + 0.01)]
        emit("M_Atlas", pts, [(x0 / AN, 1 - y1 / AN), (x0 / AN, 1 - y0 / AN), (x1 / AN, 1 - y0 / AN), (x1 / AN, 1 - y1 / AN)], C(0.8, 0.8, 0.8))
    # grass — finer near the deck
    floor_rect("M_Grass", -30, 14, -16, YF - 0.9, ZG, GRASS, s=3.0, cell=2.0, colfn=ground_col)
    floor_rect("M_Grass", X1 + 0.9, 14, YF - 0.9, 12, ZG, GRASS, s=3.0, cell=2.0, colfn=ground_col)
    floor_rect("M_Grass", -70, 70, -60, -16, ZG, GRASS, s=3.0, cell=6.0, colfn=ground_col)
    floor_rect("M_Grass", -70, -30, -16, 30, ZG, GRASS, s=3.0, cell=10.0)
    floor_rect("M_Grass", 14, 70, -16, 30, ZG, GRASS, s=3.0, cell=8.0)
    floor_rect("M_Grass", -30, X1 + 0.9, YBACK, 30, ZG, GRASS, s=3.0, cell=8.0)
    floor_rect("M_Grass", X1 + 0.9, 14, 12, 30, ZG, GRASS, s=3.0, cell=8.0)
    floor_rect("M_Grass", -30, X0 - 0.25, YF - 0.9, YBACK, ZG, GRASS, s=3.0, cell=4.0)
    # footpath parallel to the block + spur to the deck + covered linkway path
    floor_rect("M_Concrete", -60, 60, -9.6, -8.0, ZG + 0.02, CONCRETE, s=2.0, cell=2.0)
    floor_rect("M_Concrete", -2.7, -1.3, -8.0, YF - 0.9, ZG + 0.02, CONCRETE, s=2.0, cell=1.5)
    floor_rect("M_Concrete", 9.0, 11.0, -8.0, 14.0, ZG + 0.02, CONCRETE, s=2.0, cell=2.0)
    # kerb edges of the footpath (thin side faces so the path reads as raised)
    wall("M_Concrete", (-60, -9.6), (60, -9.6), ZG, ZG + 0.02, CONCRETE, s=2.0, cell=10.0)
    wall("M_Concrete", (60, -8.0), (-60, -8.0), ZG, ZG + 0.02, CONCRETE, s=2.0, cell=10.0)
    # planting strip along the verge: shrubs + bougainvillea
    rr = random.Random(7)
    x = -22.0
    while x < 7.5:
        if -3.0 < x < -1.0:
            x += 2.0
            continue
        bou = rr.random() < 0.35
        c, y, r = J(LEAF, 0.1, rr), -6.1 + rr.uniform(-0.35, 0.35), rr.uniform(0.36, 0.55)
        for tier, sub in ((DETAIL, 2), (MOBILE, 1)):
            with tier():
                blob("M_Foliage", (x, y, ZG + 0.35), r, c, seed=int(x * 10), sub=sub, squash=(1.3, 0.9, 0.7), s=1.0,
                     flat_bottom=ZG + 0.05, uoff=0.5 if bou else 0.0)
        x += rr.uniform(0.6, 0.95)
    # soil bed
    floor_rect("M_Rough", -22.5, -2.7, -6.9, -5.3, ZG + 0.02, SOIL, s=2.0, cell=4.0)
    floor_rect("M_Rough", -1.3, 8.0, -6.9, -5.3, ZG + 0.02, SOIL, s=2.0, cell=4.0)
    build_playground(-2.0, -15.5)
    build_linkway()
    # estate lamp posts
    for x in (-14.0, 12.0, 30.0):
        lamp_post(x, -10.1)
    # heritage marker by the footpath (angled towards the deck)
    M = M_at(-5.2, -7.6, ZG, math.radians(10))
    tube("M_Metal", M @ Vector((-0.35, 0, 0)), M @ Vector((-0.35, 0, 1.2)), 0.03, 6, C(0.2, 0.25, 0.3))
    tube("M_Metal", M @ Vector((0.35, 0, 0)), M @ Vector((0.35, 0, 1.2)), 0.03, 6, C(0.2, 0.25, 0.3))
    mbox("M_Metal", (0.9, 0.04, 0.62), C(0.2, 0.25, 0.3), M @ Matrix.Translation((0, 0.03, 1.15)))
    decal("heritage", tuple(M @ Vector((0, 0.05, 1.15))), tuple((M.to_3x3() @ Vector((0, 1, 0)))), 0.84, 0.56, off=0.008)
    # trees
    rain_tree(-12.5, -13.0, 1, scale=1.15)
    rain_tree(17.0, -8.0, 2, scale=1.0)
    rain_tree(1.5, -25.0, 3, scale=1.1)
    rain_tree(-26.0, -18.0, 4, scale=0.95)
    rain_tree(18.0, 6.0, 5, scale=0.9)
    palm(11.8, -3.5, 6)
    palm(12.4, 1.5, 7)
    # neighbouring blocks
    neighbour_block(-52.0, 8.0, -30.0, 11, C(1.0, 0.90, 0.80), JADE)
    butterfly_block(-20.0, -78.0, 34.0, C(0.82, 0.90, 0.98))
    far_block(40.0, 80.0, -50.0, 14, C(0.92, 0.96, 0.88))
    far_block_x(46.0, -30.0, 22.0, 12, C(1.0, 0.94, 0.82))


def lamp_post(x, y):
    tube("M_Metal", (x, y, ZG), (x, y, ZG + 7.0), 0.07, 8, C(0.45, 0.47, 0.48), r1=0.05)
    tube("M_Metal", (x, y, ZG + 7.0), (x + 0.9, y, ZG + 7.2), 0.04, 6, C(0.45, 0.47, 0.48))
    mbox("M_Metal", (0.6, 0.25, 0.12), C(0.5, 0.52, 0.53), M_at(x + 1.1, y, ZG + 7.2))


def build_playground(cx, cy):
    # rubber floor (terracotta + green patches) with a low kerb
    floor_rect("M_Rough", cx - 5.5, cx + 5.5, cy - 3.8, cy + 3.8, ZG + 0.03, C(0.62, 0.34, 0.26), s=2.0, cell=2.0)
    for (a, b, c) in (((cx - 4.5, cy - 2.5), (cx - 1.5, cy + 0.5), C(0.30, 0.55, 0.42)),
                      ((cx + 1.5, cy - 0.5), (cx + 4.6, cy + 2.8), C(0.26, 0.46, 0.66))):
        floor_rect("M_Rough", a[0], b[0], a[1], b[1], ZG + 0.045, c, s=2.0, cell=3.0)
    box("M_Concrete", (cx - 5.6, cy + 3.8, ZG), (cx + 5.6, cy + 3.95, ZG + 0.2), CONCRETE, skip=("-z",))
    box("M_Concrete", (cx - 5.6, cy - 3.95, ZG), (cx + 5.6, cy - 3.8, ZG + 0.2), CONCRETE, skip=("-z",))
    box("M_Concrete", (cx - 5.6, cy - 3.8, ZG), (cx - 5.45, cy + 3.8, ZG + 0.2), CONCRETE, skip=("-z", "-y", "+y"))
    box("M_Concrete", (cx + 5.45, cy - 3.8, ZG), (cx + 5.6, cy + 3.8, ZG + 0.2), CONCRETE, skip=("-z", "-y", "+y"))
    z0 = ZG + 0.03
    YEL, RED_, BLU, GRN = C(0.96, 0.74, 0.18), C(0.86, 0.26, 0.20), C(0.22, 0.46, 0.78), C(0.26, 0.62, 0.40)
    towers = [((cx - 2.2, cy), 1.3, RED_), ((cx + 1.4, cy + 0.2), 1.6, BLU)]
    for (tx, ty), h, rc in towers:
        for sx in (-0.6, 0.6):
            for sy in (-0.6, 0.6):
                tube("M_Plastic", (tx + sx, ty + sy, z0), (tx + sx, ty + sy, z0 + h + 1.3), 0.05, 8, YEL)
        box("M_Plastic", (tx - 0.65, ty - 0.65, z0 + h - 0.06), (tx + 0.65, ty + 0.65, z0 + h), GRN)
        # pyramid roof
        top = (tx, ty, z0 + h + 2.0)
        cs = [(tx - 0.8, ty - 0.8), (tx + 0.8, ty - 0.8), (tx + 0.8, ty + 0.8), (tx - 0.8, ty + 0.8)]
        for i in range(4):
            a, b = cs[i], cs[(i + 1) % 4]
            poly("M_Plastic", [(a[0], a[1], z0 + h + 1.3), (b[0], b[1], z0 + h + 1.3), top], rc)
        poly("M_Plastic", [(p[0], p[1], z0 + h + 1.3) for p in reversed(cs)], mulc(rc, 0.7))   # roof underside
        # panel on the tower
        decal("playpanel", (tx, ty + 0.66, z0 + h + 0.4), (0, 1, 0), 1.0, 0.5, off=0.008)
        box("M_Plastic", (tx - 0.55, ty + 0.62, z0 + h + 0.15), (tx + 0.55, ty + 0.66, z0 + h + 0.65), YEL)
    # bridge between towers
    box("M_Plastic", (cx - 1.55, cy - 0.35, z0 + 1.35), (cx + 0.8, cy + 0.35, z0 + 1.42), YEL)
    for sy in (-0.35, 0.35):
        tube("M_Plastic", (cx - 1.55, cy + sy, z0 + 2.0), (cx + 0.8, cy + sy, z0 + 2.1), 0.035, 6, BLU)
    # slide from the blue tower down towards the deck (+Y)
    tx, ty = towers[1][0]
    n = 8
    pts_l, pts_r = [], []
    for k in range(n + 1):
        t = k / n
        yy = ty + 0.65 + t * 2.6
        zz = z0 + 1.6 * (1 - t) ** 1.4 + 0.25 * t
        pts_l.append((tx - 0.3, yy, zz))
        pts_r.append((tx + 0.3, yy, zz))
    T = 0.015   # sheet thickness: top/bottom and inner/outer faces are never coplanar
    dn = lambda p: (p[0], p[1], p[2] - T)
    for k in range(n):
        poly("M_Plastic", [pts_l[k], pts_r[k], pts_r[k + 1], pts_l[k + 1]], RED_)
        poly("M_Plastic", [dn(pts_l[k + 1]), dn(pts_r[k + 1]), dn(pts_r[k]), dn(pts_l[k])], mulc(RED_, 0.8))
        for side, sx in ((pts_l, -1), (pts_r, 1)):
            a, b = side[k], side[k + 1]
            ao = (a[0] + sx * T, a[1], a[2])
            bo = (b[0] + sx * T, b[1], b[2])
            wall_in = [a, b, (b[0], b[1], b[2] + 0.15), (a[0], a[1], a[2] + 0.15)]
            wall_out = [(ao[0], ao[1], ao[2] + 0.15), (bo[0], bo[1], bo[2] + 0.15), bo, ao]
            if sx > 0:
                wall_in, wall_out = list(reversed(wall_in)), list(reversed(wall_out))
            poly("M_Plastic", wall_in, RED_)
            poly("M_Plastic", wall_out, RED_)
    # spring riders
    for (x, y, c) in ((cx - 3.6, cy + 2.4, GRN), (cx - 4.2, cy - 2.4, YEL)):
        tube("M_Metal", (x, y, z0), (x, y, z0 + 0.35), 0.05, 6, STEEL)
        blob("M_Plastic", (x, y, z0 + 0.55), 0.28, c, sub=1, squash=(1.3, 0.6, 0.8), noise=0.05)
    box("M_Metal", (cx + 5.5, cy + 3.99, 0.7), (cx + 6.1, cy + 4.01, 1.3), C(0.2, 0.25, 0.3))
    decal("fitness", (cx + 5.8, cy + 4.01, 1.0), (0, 1, 0), 0.6, 0.6, off=0.008)
    tube("M_Metal", (cx + 5.8, cy + 3.97, ZG), (cx + 5.8, cy + 3.97, 0.7), 0.03, 6, STEEL)


def build_linkway():
    # covered linkway along +X side: posts + curved-ish roof
    x0, x1 = 9.0, 11.0
    for y in [-9.0 + 3.0 * k for k in range(8)]:
        for x in (x0 + 0.1, x1 - 0.1):
            tube("M_Metal", (x, y, ZG), (x, y, 2.65), 0.05, 6, C(0.42, 0.46, 0.44))
    ya, yb = -9.6, 13.0
    prof = [(x0 - 0.25, 2.6), (x0 + 0.5, 2.78), (10.0, 2.84), (x1 - 0.5, 2.78), (x1 + 0.25, 2.6)]
    for i in range(len(prof) - 1):
        a, b = prof[i], prof[i + 1]
        grid("M_Metal", (a[0], ya, a[1]), (b[0] - a[0], 0, b[1] - a[1]), (0, yb - ya, 0), 1, 8, C(0.36, 0.44, 0.40), s=2.0)
        grid("M_Metal", (a[0], yb, a[1] - 0.012), (b[0] - a[0], 0, b[1] - a[1]), (0, ya - yb, 0), 1, 8, C(0.55, 0.58, 0.56), s=2.0)
    box("M_Metal", (x0 - 0.25, ya, 2.5), (x0 - 0.2, yb, 2.62), C(0.36, 0.44, 0.40))
    box("M_Metal", (x1 + 0.2, ya, 2.5), (x1 + 0.25, yb, 2.62), C(0.36, 0.44, 0.40))


def rain_tree(x, y, seed, scale=1.0):
    rr = random.Random(seed * 101)
    s = scale
    zt = ZG
    lathe("M_Rough", [(0.42 * s, 0), (0.33 * s, 0.4), (0.3 * s, 2.2 * s), (0.26 * s, 3.3 * s)], 8, BARK, M=M_at(x, y, zt), cap_top=False, s=1.0)
    crown = []
    for k in range(6):
        a = k * 2 * math.pi / 6 + rr.uniform(-0.3, 0.3)
        L = rr.uniform(2.6, 3.6) * s
        tip = (x + math.cos(a) * L, y + math.sin(a) * L, zt + rr.uniform(4.6, 5.8) * s)
        tube("M_Rough", (x, y, zt + 3.1 * s), tip, 0.17 * s, 5, BARK, r1=0.07 * s)
        crown.append(tip)
    # umbrella canopy: desktop gets finer blobs, mobile coarser + fewer
    pts = []
    for k in range(13):
        a = rr.uniform(0, 2 * math.pi)
        rad = math.sqrt(rr.uniform(0.0, 1.0)) * 4.6 * s
        pts.append((x + math.cos(a) * rad, y + math.sin(a) * rad, zt + (6.4 - 0.18 * rad / s) * s + rr.uniform(-0.3, 0.4),
                    rr.uniform(1.6, 2.3) * s))
    def lc(p):
        k = 0.62 + 0.42 * max(0.0, min(1.0, (p[2] - (zt + 4.5 * s)) / (3.5 * s)))
        return mulc(LEAF, k)
    for i, (px, py, pz, r) in enumerate(pts):
        with DETAIL():
            blob("M_Foliage", (px, py, pz), r, LEAF, seed=seed * 50 + i, sub=2, squash=(1.25, 1.25, 0.62), s=2.5,
                 noise=0.22, colfn=lc)
        if i % 3 != 2:
            with MOBILE():
                blob("M_Foliage", (px, py, pz), r * 1.12, LEAF, seed=seed * 50 + i, sub=1, squash=(1.25, 1.25, 0.62),
                     s=2.5, noise=0.2, colfn=lc)


def palm(x, y, seed):
    rr = random.Random(seed)
    top = (x + rr.uniform(-0.4, 0.4), y + rr.uniform(-0.4, 0.4), ZG + rr.uniform(5.0, 6.5))
    tube("M_Rough", (x, y, ZG), top, 0.2, 7, C(0.55, 0.50, 0.44), r1=0.14)
    for k in range(9):
        a = 2 * math.pi * k / 9 + rr.uniform(-0.2, 0.2)
        L = rr.uniform(2.0, 2.8)
        mid = (top[0] + math.cos(a) * L * 0.5, top[1] + math.sin(a) * L * 0.5, top[2] + 0.35)
        tip = (top[0] + math.cos(a) * L, top[1] + math.sin(a) * L, top[2] - 0.7)
        w = 0.45
        px, py = -math.sin(a) * w, math.cos(a) * w
        for (p, q) in ((top, mid), (mid, tip)):
            ww = 1.0 if p is top else 0.6
            quad = [(p[0] - px * ww * 0.3, p[1] - py * ww * 0.3, p[2]), (p[0] + px * ww * 0.3, p[1] + py * ww * 0.3, p[2]),
                    (q[0] + px * ww, q[1] + py * ww, q[2]), (q[0] - px * ww, q[1] - py * ww, q[2])]
            poly("M_Foliage", quad, mulc(LEAF, 0.9), s=1.5)   # M_Foliage is double-sided


def neighbour_block(xa, xb, y, storeys, tint, band):
    """Slab block facing +Y (window side, laundry poles) with an open void deck at ground level."""
    d = 7.0
    yf, yb = y, y - d
    zs = ZC + 0.25
    top = zs + storeys * 2.8
    for k in range(storeys):
        facade_strip((xb, yf), (xa, yf), zs + k * 2.8, zs + (k + 1) * 2.8, "window", tint)
    wall("M_Paint", (xb, yf), (xa, yf), ZC - 0.5, zs, tint, s=4.0, cell=8.0)
    wall("M_Paint", (xb, yb), (xb, yf), ZG, top, tint, s=4.0, cell=8.0)
    wall("M_Paint", (xa, yf), (xa, yb), ZG, top, tint, s=4.0, cell=8.0)
    floor_rect("M_Concrete", xa, xb, yb, yf, top, CONCRETE, s=4.0, cell=16.0)
    # gable ends: a painted accent band + small ventilation windows (HDB gables are otherwise blank)
    for (gx, sgn) in ((xb, 1), (xa, -1)):
        yl, yr = (yb + 2.2, yf - 2.2) if sgn > 0 else (yf - 2.2, yb + 2.2)
        wall("M_Paint", (gx + 0.03 * sgn, yl), (gx + 0.03 * sgn, yr), ZC, top - 1.0, mulc(band, 0.9), s=4.0, cell=12.0)
        for k in range(storeys):
            z = zs + k * 2.8 + 1.4
            box("M_Rough", (gx - 0.02 if sgn > 0 else gx - 0.05, (yb + yf) / 2 - 0.5, z), (gx + 0.05 if sgn > 0 else gx + 0.02, (yb + yf) / 2 + 0.5, z + 0.5), C(0.2, 0.2, 0.22))
    # void deck: soffit, back wall (dark interior), pillars with a coloured dado
    floor_rect("M_Paint", xa, xb, yb, yf, ZC - 0.5, mulc(tint, 0.8), s=4.0, cell=8.0, down=True)
    wall("M_Paint", (xb, yb + 2.5), (xa, yb + 2.5), ZG, ZC - 0.5, mulc(tint, 0.62), s=4.0, cell=6.0)
    floor_rect("M_Floor", xa, xb, yb + 2.5, yf, ZG + 0.1, C(0.8, 0.78, 0.74), s=1.2, cell=8.0)
    # inner faces of the gable ends at void-deck level (seen through the open deck)
    wall("M_Paint", (xa + 0.25, yb + 2.5), (xa + 0.25, yf), ZG, ZC - 0.5, mulc(tint, 0.7), s=4.0, cell=4.0)   # faces +x
    wall("M_Paint", (xb - 0.25, yf), (xb - 0.25, yb + 2.5), ZG, ZC - 0.5, mulc(tint, 0.7), s=4.0, cell=4.0)   # faces -x
    wall("M_Concrete", (xb, yf), (xa, yf), ZG, ZG + 0.1, CONCRETE, s=2.0, cell=8.0)
    x = xa + 3.0
    while x < xb - 1.0:
        prism("M_Paint", chamfer_rect(x, yf - 0.5, 0.3, 0.3, 0.05), ZG, 0.9, band, s=2.0, rows=1, caps=(False, False))
        prism("M_Paint", chamfer_rect(x, yf - 0.5, 0.3, 0.3, 0.05), 0.9, ZC - 0.5, tint, s=2.0, rows=1, caps=(False, False))
        x += 6.4
    # a few residents' things under the neighbour's void deck
    for k, x in enumerate((xb - 9.0, xb - 22.0)):
        lathe("M_Terrazzo", [(0.2, ZG + 0.1), (0.14, ZG + 0.4), (0.45, ZG + 0.75)], 10, TERRAZZO, M=M_at(x, yf - 3.0, 0), s=0.8)
    # roof: parapet + lift motor room
    box("M_Paint", ((xa + xb) / 2 - 4, yb + 1.5, top), ((xa + xb) / 2 + 2, yb + 5.5, top + 3.0), tint, skip=("-z",))


def butterfly_block(cx, cy, R_, tint):
    """Nod to Blk 168A Queensway: two gently curved wings (not a replica)."""
    storeys = 16
    zs = ZC
    for side in (-1, 1):
        pts = []
        for k in range(7):
            a = math.radians(8 + k * 9) * side
            pts.append((cx + math.sin(a) * R_ * 1.3, cy + R_ - math.cos(a) * R_))
        for i in range(len(pts) - 1):
            p0, p1 = (pts[i + 1], pts[i]) if side > 0 else (pts[i], pts[i + 1])
            for k in range(0, storeys, 2):
                facade_strip(p0, p1, zs + k * 2.8, zs + (k + 2) * 2.8, "corridor" if k % 4 else "window", tint, unit=12.0)
            wall("M_Paint", p0, p1, ZG, zs, mulc(tint, 0.6), s=4.0, cell=12.0)


def far_block(xa, xb, y, storeys, tint):
    top = ZC + storeys * 2.8
    for k in range(0, storeys, 1):
        facade_strip((xb, y), (xa, y), ZC + k * 2.8, ZC + (k + 1) * 2.8, "corridor", tint)
    wall("M_Paint", (xb, y), (xa, y), ZG, ZC, mulc(tint, 0.55), s=4.0, cell=12.0)
    wall("M_Paint", (xa, y), (xa, y - 8), ZG, top, tint, s=4.0, cell=12.0)
    wall("M_Paint", (xb, y - 8), (xb, y), ZG, top, tint, s=4.0, cell=12.0)


def far_block_x(x, ya, yb, storeys, tint):
    top = ZC + storeys * 2.8
    for k in range(storeys):
        facade_strip((x, yb), (x, ya), ZC + k * 2.8, ZC + (k + 1) * 2.8, "window", tint)   # faces -X
    wall("M_Paint", (x, yb), (x, ya), ZG, ZC, mulc(tint, 0.55), s=4.0, cell=12.0)
    wall("M_Paint", (x, ya), (x + 8, ya), ZG, top, tint, s=4.0, cell=12.0)


# ======================================================================================
# markers (cameras, sun)
# ======================================================================================
def contract_markers():
    tgt = Vector((0, 0, TABLE_Z))
    wide = Vector((1.0, 3.87, 2.2))
    marker("PRO_Camera_Wide", tuple(wide), tuple((tgt + Vector((0, 0, 0.2)) - wide).normalized()), {"fov": 55, "look_at": "PRO_Table"})
    close = Vector((-0.56, 0.83, 1.1))
    marker("PRO_Camera_Close", tuple(close), tuple((tgt + Vector((0, 0, 0.08)) - close).normalized()), {"fov": 55, "look_at": "PRO_Table"})
    marker("PRO_Sun", tuple(SUN_DIR * 100.0), tuple(-SUN_DIR), {"elevation_deg": 13, "color": "#ffc98a",
                                                                "note": "direction from origin = direction to the sun"})


def build_level():
    build_structure()
    build_lobby()
    build_props()
    build_outside()
    contract_markers()


# ======================================================================================
# materials / objects
# ======================================================================================
MAT_DEF = {  # name: (texture, roughness, metallic)
    "M_Paint": ("paint", 0.85, 0.0),
    "M_Floor": ("floor", 0.42, 0.0),
    "M_Concrete": ("concrete", 0.9, 0.0),
    "M_Terrazzo": ("terrazzo", 0.35, 0.0),
    "M_Grass": ("grass", 0.95, 0.0),
    "M_Foliage": ("foliage", 0.8, 0.0),
    "M_Flower": ("flower", 0.8, 0.0),
    "M_Facade": ("facade", 0.85, 0.0),
    "M_Atlas": ("atlas", 0.55, 0.0),
    "M_Metal": (None, 0.35, 0.7),
    "M_Plastic": (None, 0.5, 0.0),
    "M_Rough": (None, 0.92, 0.0),
    "M_Tube": (None, 0.3, 0.0),
}
IMAGES = {}


def make_materials(res):
    mats = {}
    for name, (tex, rough, metal) in MAT_DEF.items():
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        m.use_backface_culling = name not in ("M_Foliage", "M_Flower")
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
            mix = nt.nodes.new("ShaderNodeMix")
            mix.data_type = "RGBA"
            mix.blend_type = "MULTIPLY"
            mix.inputs[0].default_value = 1.0
            nt.links.new(it.outputs["Color"], mix.inputs[6])
            nt.links.new(attr.outputs["Color"], mix.inputs[7])
            nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
        else:
            nt.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
        if name == "M_Tube":
            bsdf.inputs["Emission Color"].default_value = (0.92, 0.96, 1.0, 1.0)
            bsdf.inputs["Emission Strength"].default_value = 4.0
        mats[name] = m
    return mats


def swap_textures(res):
    for tex, img in IMAGES.items():
        img.filepath = os.path.join(TEX, str(res), tex + ".png")
        img.reload()


def make_mesh_object(name, md, mats):
    verts, faces, uvs, cols, midx, sm = [], [], [], [], [], []
    slots = []
    for mname in MATS:
        b = md.get(mname)
        if not b or not b.f:
            continue
        off = len(verts)
        si = len(slots)
        slots.append(mname)
        verts.extend(b.v)
        for f, uv, c, s_ in zip(b.f, b.uv, b.col, b.sm):
            faces.append([i + off for i in f])
            uvs.extend(uv)
            cols.extend(c)
            midx.append(si)
            sm.append(s_)
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
    bpy.context.scene.collection.objects.link(ob)
    return ob


def make_objects(mats):
    objs = {}
    for tier in ("base", "detail", "mobile", "decal"):
        if tier in BUCKETS:
            objs[tier] = make_mesh_object("VoidDeck" if tier == "base" else "VoidDeck_" + tier, BUCKETS[tier], mats)
    empties = []
    for (name, pos, face, props) in MARKERS:
        ob = bpy.data.objects.new(name, None)
        ob.empty_display_type = "SINGLE_ARROW"
        ob.empty_display_size = 0.4
        ob.location = pos
        if face is not None:
            if len(face) == 2:
                ob.rotation_euler = (0, 0, math.atan2(face[0], -face[1]))
            else:
                # local -Y along the 3D direction, local +Z roughly up
                ob.rotation_euler = Vector(face).to_track_quat("-Y", "Z").to_euler()
        for k, v in props.items():
            ob[k] = v
        bpy.context.scene.collection.objects.link(ob)
        empties.append(ob)
    return objs, empties


# ======================================================================================
# AO bake into the colour attribute (Cycles, bake-to-vertex-colours): contact AO x openness
# ======================================================================================
def bake_ao(objs, hidden=()):
    import numpy as np
    sc = bpy.context.scene
    for ob in bpy.context.scene.objects:
        ob.hide_render = any(ob == h for h in hidden if h is not None)
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
    sc.cycles.samples = 16 if FAST else 48
    if sc.world is None:
        sc.world = bpy.data.worlds.new("World")
    results = {}
    for tag, dist in (("short", 0.7), ("long", 7.0)):
        sc.world.light_settings.distance = dist
        for ob in objs:
            me = ob.data
            a = me.color_attributes.get("AO") or me.color_attributes.new("AO", "FLOAT_COLOR", "CORNER")
            me.color_attributes.active_color = a
        bpy.ops.object.select_all(action="DESELECT")
        for ob in objs:
            ob.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.bake(type="AO", target="VERTEX_COLORS")
        for ob in objs:
            me = ob.data
            buf = np.empty(len(me.loops) * 4, dtype=np.float32)
            me.color_attributes["AO"].data.foreach_get("color", buf)
            results[(ob.name, tag)] = buf.reshape(-1, 4)[:, 0].copy()
            r_ = results[(ob.name, tag)]
            print("AO bake", ob.name, tag, "loops", len(r_), "min %.3f mean %.3f" % (float(r_.min()), float(r_.mean())))
    for ob in objs:
        me = ob.data
        n = len(me.loops)
        col = np.empty(n * 4, dtype=np.float32)
        me.color_attributes["Col"].data.foreach_get("color", col)
        c = col.reshape(-1, 4)
        s_ = np.clip(results[(ob.name, "short")], 0, 1)
        l_ = np.clip(results[(ob.name, "long")], 0, 1)
        k = (0.22 + 0.78 * s_ ** 1.15) * (0.62 + 0.38 * l_)
        # per-loop material + position for exceptions / warm bounce
        mi = np.empty(len(me.polygons), dtype=np.int32)
        me.polygons.foreach_get("material_index", mi)
        lt = np.empty(len(me.polygons), dtype=np.int32)
        me.polygons.foreach_get("loop_total", lt)
        loop_mat = np.repeat(mi, lt)
        names = [m.name for m in me.materials]
        if "M_Tube" in names:
            k[loop_mat == names.index("M_Tube")] = 1.0
        co = np.empty(len(me.vertices) * 3, dtype=np.float32)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        li = np.empty(n, dtype=np.int32)
        me.loops.foreach_get("vertex_index", li)
        p = co[li]
        c[:, :3] *= k[:, None]
        # warm bounce from the sunlit verge onto the soffit/beams/pillars near the open edge
        inside = (p[:, 0] > X0) & (p[:, 0] < X1) & (p[:, 1] > YF - 0.1) & (p[:, 1] < YB) & (p[:, 2] > 1.2) & (p[:, 2] < ZC + 0.01)
        w = np.clip(1.0 - (p[:, 1] - YF) / 6.0, 0, 1) * inside
        c[:, 0] *= 1 + 0.10 * w
        c[:, 1] *= 1 + 0.03 * w
        c[:, 2] *= 1 - 0.06 * w
        me.color_attributes["Col"].data.foreach_set("color", c.ravel())
        me.color_attributes.remove(me.color_attributes["AO"])
        ca = me.color_attributes["Col"]
        me.color_attributes.active_color = ca
        me.color_attributes.render_color_index = me.color_attributes.active_color_index



# ======================================================================================
# geometry audit: coplanar / near-coplanar overlapping faces (z-fighting) + inside-out faces
# ======================================================================================
def audit(ob, gap=0.005, verbose=20):
    """Flags (a) overlapping faces whose planes are within `gap` and that face the same way
    (z-fight candidates, incl. exact duplicates), (b) back-to-back coplanar overlaps, and
    (c) faces whose normal ray immediately enters a closed volume (likely inside-out)."""
    import numpy as np
    from mathutils.bvhtree import BVHTree
    me = ob.data
    names = [m.name for m in me.materials]
    polys = []
    for p in me.polygons:
        if p.area < 1e-6:
            continue
        n = p.normal.copy()
        pts = [me.vertices[i].co.copy() for i in p.vertices]
        polys.append((p.index, n, n.dot(pts[0]), pts, names[p.material_index]))
    # spatial hash on dominant axis
    buckets = {}
    for rec in polys:
        idx, n, d, pts, mat = rec
        ax = max(range(3), key=lambda i: abs(n[i]))
        key = (ax, round(d * (1 if n[ax] > 0 else -1) / gap))
        buckets.setdefault(key, []).append(rec)

    def proj(pts, ax):
        a, b = [i for i in range(3) if i != ax]
        return [(q[a], q[b]) for q in pts]

    def sat_overlap(A, B, tol=0.002):
        for P in (A, B):
            m = len(P)
            for i in range(m):
                x0, y0 = P[i]
                x1, y1 = P[(i + 1) % m]
                nx, ny = y1 - y0, x0 - x1
                L = math.hypot(nx, ny)
                if L < 1e-9:
                    continue
                nx, ny = nx / L, ny / L
                pa = [nx * x + ny * y for x, y in A]
                pb = [nx * x + ny * y for x, y in B]
                if min(max(pa), max(pb)) - max(min(pa), min(pb)) < tol:
                    return False
        return True

    same, opp = [], []
    seen = set()
    for (ax, k), lst in buckets.items():
        cand = []
        for dk in (-1, 0, 1):
            cand += buckets.get((ax, k + dk), []) if dk else []
        grid = {}
        for rec in lst + cand:
            P = proj(rec[3], ax)
            xs = [q[0] for q in P]
            ys = [q[1] for q in P]
            rec2 = (rec, P, (min(xs), min(ys), max(xs), max(ys)))
            for gx in range(int(math.floor(min(xs))), int(math.floor(max(xs))) + 1):
                for gy in range(int(math.floor(min(ys))), int(math.floor(max(ys))) + 1):
                    grid.setdefault((gx, gy), []).append(rec2)
        for cell in grid.values():
            for i in range(len(cell)):
                for j in range(i + 1, len(cell)):
                    (ra, Pa, ba), (rb, Pb, bb) = cell[i], cell[j]
                    ia, ib = ra[0], rb[0]
                    if ia == ib or (min(ia, ib), max(ia, ib)) in seen:
                        continue
                    if abs(ra[1].dot(rb[1])) < 0.999:
                        continue
                    sgn = 1 if ra[1].dot(rb[1]) > 0 else -1
                    dd = abs(ra[2] - sgn * rb[2])
                    if dd > gap:
                        continue
                    if ba[2] < bb[0] or bb[2] < ba[0] or ba[3] < bb[1] or bb[3] < ba[1]:
                        continue
                    if not sat_overlap(Pa, Pb):
                        continue
                    seen.add((min(ia, ib), max(ia, ib)))
                    c = sum(ra[3], Vector()) / len(ra[3])
                    (same if sgn > 0 else opp).append((dd, ra[4], rb[4], tuple(round(v, 2) for v in c)))
    # inside-out heuristic
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    bvh = BVHTree.FromBMesh(bm)
    inv = []
    ds = {"M_Foliage", "M_Flower"}
    for f in bm.faces:
        mat = names[f.material_index]
        if mat in ds or f.calc_area() < 0.01:
            continue
        c = f.calc_center_median()
        n = f.normal
        hit = bvh.ray_cast(c + n * 0.002, n, 40.0)
        if hit[0] is None:
            continue
        hf = bm.faces[hit[2]]
        if names[hf.material_index] in ds:
            continue
        if hit[1].dot(n) > 0.3 and 0.05 < hit[3] < 6.0:
            inv.append((round(hit[3], 2), mat, names[hf.material_index], tuple(round(v, 2) for v in c) + tuple(round(v, 1) for v in n)))
    bm.free()
    print("AUDIT %s: same-facing overlaps within %.0f mm: %d | back-to-back coplanar: %d | inside-out suspects: %d"
          % (ob.name, gap * 1000, len(same), len(opp), len(inv)))
    groups = {}
    for tag, lst in (("SAME", same), ("OPP", opp), ("INV", inv)):
        for r in lst:
            g = groups.setdefault((tag, r[1], r[2]), [])
            g.append(r[3])
    for (tag, a_, b_), lst in sorted(groups.items()):
        print("   %-4s %-11s %-11s x%-4d e.g. %s" % (tag, a_, b_, len(lst), " ".join(str(q) for q in lst[:4])))
    return same, opp, inv

# ======================================================================================
# export
# ======================================================================================
def export_glb(path, objs):
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objs:
        ob.hide_set(False)
        ob.hide_render = False
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    kw = dict(filepath=path, export_format="GLB", use_selection=True, export_extras=True, export_yup=True,
              export_apply=True, export_vertex_color="ACTIVE", export_all_vertex_colors=False,
              export_active_vertex_color_when_no_material=False,
              export_image_format="JPEG", export_jpeg_quality=88, export_image_quality=88,
              export_materials="EXPORT", export_texcoords=True, export_normals=True, export_tangents=False,
              export_cameras=False, export_lights=False, export_animations=False)
    bpy.ops.export_scene.gltf(**kw)
    print("exported", path, os.path.getsize(path) / 1e6, "MB")


def meshopt(path):
    exe = os.path.join(GLTF_TOOLS, "node_modules", ".bin", "gltf-transform")
    if not os.path.exists(exe):
        print("gltf-transform not found at", exe, "- skipping meshopt (see tools/build_ww2_npcs.sh for install)")
        return
    tmp = path + ".tmp.glb"
    subprocess.check_call([exe, "meshopt", path, tmp, "--level", "medium"])
    shutil.move(tmp, path)
    print("meshopt", path, os.path.getsize(path) / 1e6, "MB")


def tri_count(objs):
    t = 0
    for ob in objs:
        if ob.type == "MESH":
            ob.data.calc_loop_triangles()
            t += len(ob.data.loop_triangles)
    return t


def to_three(p):
    return [round(p[0], 3), round(p[2], 3), round(-p[1], 3)]


def write_nodes_json(empties, stats):
    data = {"markers": {}, "stats": stats}
    for e in empties:
        d = e.matrix_world.to_3x3() @ Vector((0, -1, 0))
        data["markers"][e.name] = {"three_pos": to_three(e.location), "three_facing": to_three(d),
                                   "props": {k: v for k, v in e.items()}}
    with open(NODES_JSON, "w") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)


# ======================================================================================
# previews (EEVEE) with placeholder figures
# ======================================================================================
def pmat(name, col, rough=0.8, emit=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = C(*col)
    b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = C(*emit)
        b.inputs["Emission Strength"].default_value = 3.0
    return m


def pmesh(name, prim, mat, **kw):
    getattr(bpy.ops.mesh, prim)(**kw)
    o = bpy.context.active_object
    o.name = "PREVIEW_" + name
    o.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return o


def capsule(name, p0, p1, r, mat):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    o = pmesh(name, "primitive_cylinder_add", mat, radius=r, depth=d.length, vertices=20, location=(p0 + p1) / 2)
    o.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    a = pmesh(name + "_a", "primitive_uv_sphere_add", mat, radius=r, location=p0, segments=16, ring_count=8)
    b = pmesh(name + "_b", "primitive_uv_sphere_add", mat, radius=r, location=p1, segments=16, ring_count=8)
    return [o, a, b]


def placeholder_figures():
    """Seated stand-ins: Mr. Boon (1.55 m standing) on the -X stool, Sparky (1.0 m) on the +X stool."""
    shirt = pmat("P_Shirt", (0.95, 0.94, 0.90))
    pants = pmat("P_Pants", (0.42, 0.42, 0.44))
    skin = pmat("P_Skin", (0.82, 0.64, 0.50))
    hair = pmat("P_Hair", (0.90, 0.90, 0.88))
    fur = pmat("P_Fur", (0.86, 0.76, 0.62), 0.95)
    hood = pmat("P_Hood", (0.50, 0.62, 0.70), 0.9)
    cam = pmat("P_Camera", (0.10, 0.10, 0.10), 0.5)
    obs = []
    sx = -STOOL_R
    obs += capsule("Boon_torso", (sx - 0.02, 0, 0.62), (sx + 0.02, 0, 1.02), 0.16, shirt)
    obs.append(pmesh("Boon_head", "primitive_uv_sphere_add", skin, radius=0.135, location=(sx + 0.05, 0, 1.30)))
    obs.append(pmesh("Boon_hair", "primitive_uv_sphere_add", hair, radius=0.14, location=(sx + 0.02, 0, 1.34), scale=(1, 1, 0.8)))
    for sy in (-0.1, 0.1):
        obs += capsule("Boon_thigh", (sx, sy, 0.52), (sx + 0.38, sy, 0.52), 0.075, pants)
        obs += capsule("Boon_shin", (sx + 0.4, sy, 0.5), (sx + 0.42, sy, 0.06), 0.06, pants)
        obs += capsule("Boon_arm", (sx + 0.02, sy * 2.0, 1.0), (sx + 0.34, sy * 0.9, 0.84), 0.055, shirt)
    # the Brownie on the table (preview stand-in; the game adds the real prop)
    b = pmesh("Brownie", "primitive_cube_add", cam, size=1, location=(0.0, 0.0, TABLE_Z + 0.075))
    b.scale = (0.09, 0.12, 0.14)
    b.rotation_euler = (0, 0, -0.5)
    tx = STOOL_R
    obs += capsule("Sparky_body", (tx, 0, 0.62), (tx, 0, 0.70), 0.2, hood)
    obs.append(pmesh("Sparky_head", "primitive_uv_sphere_add", fur, radius=0.19, location=(tx - 0.02, 0, 0.98)))
    obs.append(pmesh("Sparky_hood", "primitive_uv_sphere_add", hood, radius=0.205, location=(tx + 0.02, 0, 1.0)))
    for sy in (-0.12, 0.12):
        obs.append(pmesh("Sparky_ear", "primitive_uv_sphere_add", fur, radius=0.065, location=(tx, sy * 1.2, 1.16)))
        obs += capsule("Sparky_leg", (tx - 0.05, sy, 0.5), (tx - 0.28, sy, 0.48), 0.07, pants)
        obs += capsule("Sparky_arm", (tx - 0.04, sy * 1.7, 0.74), (tx - 0.26, sy * 1.2, 0.80), 0.06, hood)
    obs.append(pmesh("Sparky_snout", "primitive_uv_sphere_add", fur, radius=0.07, location=(tx - 0.19, 0, 0.95)))
    return obs, b


def preview_setup():
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    sc.render.resolution_percentage = 100
    try:
        sc.eevee.taa_render_samples = 32 if FAST else 64
        sc.eevee.use_raytracing = True
        sc.eevee.use_shadows = True
    except Exception as e:
        print("eevee opts", e)
    try:
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    w = sc.world or bpy.data.worlds.new("World")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs[0])
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.95, 0.80, 0.62, 1)
    ramp.color_ramp.elements[1].position = 0.5
    ramp.color_ramp.elements[1].color = (0.52, 0.66, 0.84, 1)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.55
    # what the camera sees: a soft late-afternoon sky (peach horizon -> pale blue)
    bg2 = nt.nodes.new("ShaderNodeBackground")
    ramp2 = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(sep.outputs["Z"], ramp2.inputs[0])
    ramp2.color_ramp.elements[0].position = 0.0
    ramp2.color_ramp.elements[0].color = (0.92, 0.70, 0.52, 1)
    ramp2.color_ramp.elements[1].position = 0.3
    ramp2.color_ramp.elements[1].color = (0.40, 0.56, 0.78, 1)
    nt.links.new(ramp2.outputs["Color"], bg2.inputs["Color"])
    bg2.inputs["Strength"].default_value = 0.8
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
    nt.links.new(bg.outputs["Background"], mix.inputs[1])
    nt.links.new(bg2.outputs["Background"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    sd = bpy.data.lights.new("Sun", "SUN")
    sd.energy = 4.2
    sd.color = (1.0, 0.80, 0.58)
    sd.angle = math.radians(1.5)
    sun = bpy.data.objects.new("PREVIEW_Sun", sd)
    sun.rotation_euler = (-SUN_DIR).to_track_quat("-Z", "Y").to_euler()
    sc.collection.objects.link(sun)
    sd.use_shadow = True
    bpy.context.view_layer.update()
    print("SUN light travel dir", tuple(sun.matrix_world.to_3x3() @ Vector((0, 0, -1))), "expected", tuple(-SUN_DIR))
    prev = [sun]
    for (name, pos, _, props) in MARKERS:
        if not name.startswith("PRO_Lamp_"):
            continue
        ld = bpy.data.lights.new("L_" + name, "AREA")
        ld.shape = "RECTANGLE"
        ld.size, ld.size_y = 1.2, 0.12
        ld.energy = 14
        ld.color = (0.90, 0.95, 1.0)
        lo = bpy.data.objects.new("PREVIEW_" + name, ld)
        lo.location = (pos[0], pos[1], pos[2] - 0.01)
        sc.collection.objects.link(lo)
        prev.append(lo)
    return prev


def camera(name, loc, target, vfov=55.0):
    cd = bpy.data.cameras.new(name)
    cd.sensor_fit = "VERTICAL"
    cd.angle_y = math.radians(vfov)
    cd.clip_start, cd.clip_end = 0.05, 1500
    ob = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return ob


def render(cam, fname):
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.filepath = os.path.join(PREV_DIR, fname)
    bpy.ops.render.render(write_still=True)
    print("render", fname)


def previews(tag, show_figs=True):
    os.makedirs(PREV_DIR, exist_ok=True)
    mk = {n: p for (n, p, _, _) in MARKERS}
    t = Vector(mk["PRO_Table"])
    render(camera("CAM_wide", mk["PRO_Camera_Wide"], t + Vector((0, 0, 0.2))), "01_wide%s.png" % tag)
    render(camera("CAM_close", mk["PRO_Camera_Close"], t + Vector((0, 0, 0.08))), "02_close%s.png" % tag)
    if tag:
        return
    render(camera("CAM_lobby", (1.5, -3.2, 1.5), (-1.0, 6.5, 1.3)), "03_towards_lobby.png")
    render(camera("CAM_outside", (4.0, -14.0, 1.6), (-1.0, 0.0, 2.5)), "04_from_playground.png")
    render(camera("CAM_side", (-9.0, -1.5, 1.4), (4.0, -1.0, 1.0)), "05_along_deck.png")
    c = camera("CAM_aerial", (30.0, -45.0, 32.0), (-2.0, -6.0, 0.0), vfov=40)
    render(c, "06_aerial.png")


# ======================================================================================
# main
# ======================================================================================
def ensure_textures():
    need = [os.path.join(TEX, r, n + ".png") for r in ("1024", "512") for n in
            ("paint", "concrete", "floor", "terrazzo", "grass", "foliage", "flower", "facade", "atlas")]
    if all(os.path.exists(p) for p in need):
        return
    print("generating textures ...")
    env = dict(os.environ)
    if os.environ.get("VOIDDECK_PYLIB"):
        env["PYTHONPATH"] = os.environ["VOIDDECK_PYLIB"]
    subprocess.check_call([sys.executable, os.path.join(HERE, "gen_voiddeck_textures.py")], env=env)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ensure_textures()
    build_level()
    mats = make_materials(1024)
    objs, empties = make_objects(mats)
    if DO_BAKE:
        dec = [objs["decal"]] if "decal" in objs else []
        # 1) structure + desktop detail, without mobile stand-ins and without decals (decals must not
        #    occlude the surface they sit on — that is what caused the dark smudges under overlays)
        bake_ao([o for t, o in objs.items() if t in ("base", "detail")], hidden=[objs.get("mobile")] + dec)
        if "mobile" in objs:
            bake_ao([objs["mobile"]], hidden=[objs.get("detail")] + dec)
        if dec:
            bake_ao(dec, hidden=[objs.get("mobile")])
        for ob in objs.values():
            ob.hide_render = False
    if "decal" in objs:
        bpy.ops.object.select_all(action="DESELECT")
        objs["base"].select_set(True)
        objs["decal"].select_set(True)
        bpy.context.view_layer.objects.active = objs["base"]
        bpy.ops.object.join()
        del objs["decal"]
    stats = {}
    # --- mobile: base + mobile-only, 512² textures
    swap_textures(512)
    mob = [objs["base"]] + ([objs["mobile"]] if "mobile" in objs else [])
    stats["mobile_tris"] = tri_count(mob)
    os.makedirs(os.path.dirname(OUT_MOBILE), exist_ok=True)
    # join mobile-only into a copy of base for a single mesh
    bpy.ops.object.select_all(action="DESELECT")
    base_m = objs["base"].copy()
    base_m.data = objs["base"].data.copy()
    base_m.name = "VoidDeck_m"
    bpy.context.scene.collection.objects.link(base_m)
    if "mobile" in objs:
        base_m.select_set(True)
        objs["mobile"].select_set(True)
        bpy.context.view_layer.objects.active = base_m
        bpy.ops.object.join()
    objs["base"].name = "VoidDeck_desktop"
    base_m.name = "VoidDeck"
    if "--audit" in ARGS or True:
        am = audit(base_m, verbose=0)
        stats["audit_mobile"] = {"same_facing_overlaps": len(am[0]), "back_to_back": len(am[1]), "inside_out_suspects": len(am[2])}
    export_glb(OUT_MOBILE, [base_m] + empties)
    base_m.name = "VoidDeck_mobile"
    objs["base"].name = "VoidDeck"
    # --- desktop: base + detail, 1024² textures
    swap_textures(1024)
    bpy.ops.object.select_all(action="DESELECT")
    desk = objs["base"]
    if "detail" in objs:
        desk.select_set(True)
        objs["detail"].select_set(True)
        bpy.context.view_layer.objects.active = desk
        bpy.ops.object.join()
    stats["desktop_tris"] = tri_count([desk])
    if "--audit" in ARGS or True:
        sa, op, iv = audit(desk)
        stats["audit"] = {"same_facing_overlaps": len(sa), "back_to_back": len(op), "inside_out_suspects": len(iv)}
    for ob in (base_m,):
        ob.hide_render = True
        ob.hide_set(True)
    export_glb(OUT_DESKTOP, [desk] + empties)
    if DO_MESHOPT:
        meshopt(OUT_DESKTOP)
        meshopt(OUT_MOBILE)
    stats["desktop_bytes"] = os.path.getsize(OUT_DESKTOP)
    stats["mobile_bytes"] = os.path.getsize(OUT_MOBILE)
    stats["materials"] = [m.name for m in desk.data.materials]
    print("STATS", stats)
    write_nodes_json(empties, stats)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    if DO_PREVIEWS:
        figs, _ = placeholder_figures()
        preview_setup()
        base_m.hide_render = True
        previews("")
        # mobile-tier look check: swap to the mobile mesh + 512 textures
        if "--mobile-preview" in ARGS:
            swap_textures(512)
            desk.hide_render = True
            base_m.hide_render = False
            previews("_mobile")


main()
