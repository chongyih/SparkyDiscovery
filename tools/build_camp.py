"""
Sparky Discovery — Chapter 3 set: Taman Jurong Camp (1967–68), a barrack floor at night, a night-exercise
clearing and a Queenstown community-centre send-off. Four areas in one GLB.

Reproducible Blender build script (Blender 5.2):
    GLTF_TRANSFORM=/path/to/node_modules/.bin/gltf-transform \
    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python tools/build_camp.py [-- --no-bake] [--no-previews] [--fast] [--retex]

Outputs
    public/assets/models/camp.glb          desktop tier (1024² textures, detail geometry)
    public/assets/models/camp-mobile.glb   mobile tier (512² textures, no detail geometry)
    tools/camp_nodes.json                  markers / colliders in three.js space
    tools/camp_tex/{1024,512}/*.png        camp atlas + ground texture (generated here with numpy; --retex rebuilds)
    docs/previews/camp/*.png               EEVEE previews (ignored by git)

Textures: plaster from tools/ww2_tex (Chapter 1), grass + foliage from tools/voiddeck_tex (prologue), and two
new ones drawn procedurally below (no photographs): `ground` (neutral gravelly tarmac / laterite, tinted by
vertex colour) and `atlas` (glass and timber louvres, doors, planks, army canvas, breeze blocks, zinc, steel
casements, lockers, bark, granite, blanket, lorry grille, tyre tread, notice board, a flat white patch for
untextured parts, and the present-day HDB elevation copied from the void-deck facade texture).
Anything with lettering (the heritage marker, the community-centre sign, the send-off banner) is a plain quad
with 0..1 UVs in its own DECAL_* node; the game draws those at runtime.

Period notes (docs/research/1967-history.md §4): Taman Jurong Camp was several five-storey blocks of one-room
flats, converted in a hurry into barracks, behind an open parade ground; the site is now Taman Jurong Greens
park. The blocks here are generic 1960s slab blocks (open corridors on the square side, louvred windows,
breeze-block stair towers); no real block is copied, and the heritage marker's text is not copied.

Conventions (docs/design.md, "Chapter 3 set contract"): Blender Z-up, metres; Blender (x, y, z) -> three.js
(x, z, -y). The contract and src/chapters/ns-fallback.js give three.js coordinates: P3(x, y, z) converts.
Marker empties face their local -Y axis (three.js +Z at yaw 0). Every object is parented (identity) under one
of AREA_Parade / AREA_Barracks / AREA_Night / AREA_CC.
Node groups:
    THEN_*  1967–68 only (hidden in the present-day Then & Now view)
    NOW_*   present-day park only
    DECAL_* runtime-textured quads (UV 0..1)
    PROP_*  movable props (PROP_Bed: origin at its centre, long axis on local ±Y; PROP_Truck: forward = local -Y)
    COL_*   invisible box colliders; extras aabb_min/aabb_max (three.js), state then/now, area
"""
import bpy, math, random, os, sys, json, subprocess, struct, time
import numpy as np
from mathutils import Vector, Matrix
from contextlib import contextmanager

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
DO_BAKE = "--no-bake" not in ARGS
DO_PREVIEWS = "--no-previews" not in ARGS
FAST = "--fast" in ARGS
RETEX = "--retex" in ARGS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TEX_WW2 = os.path.join(HERE, "ww2_tex")
TEX_VD = os.path.join(HERE, "voiddeck_tex")
TEX_CAMP = os.path.join(HERE, "camp_tex")
OUT_DESKTOP = os.path.join(ROOT, "public", "assets", "models", "camp.glb")
OUT_MOBILE = os.path.join(ROOT, "public", "assets", "models", "camp-mobile.glb")
OUT_BLEND = os.path.join(HERE, "camp.blend")
PREV_DIR = os.path.join(ROOT, "docs", "previews", "camp")
NODES_JSON = os.path.join(HERE, "camp_nodes.json")

R = random.Random(1967)


def P3(x, y, z):
    """three.js position -> Blender."""
    return (x, -z, y)


def F3(yaw):
    """three.js yaw (atan2(fx, fz)) -> Blender facing (dx, dy)."""
    return (math.sin(yaw), -math.cos(yaw))


NORTH = (0.0, 1.0)      # three.js -z
SOUTH = (0.0, -1.0)     # three.js +z
EAST = (1.0, 0.0)
WEST = (-1.0, 0.0)


# ======================================================================================
# Procedural textures (numpy only; written through bpy images)
# ======================================================================================
AW = 1024
ATL = {  # name: (x0, y0, x1, y1) pixels in the 1024 atlas, origin top-left
    "louvre_glass": (0, 0, 256, 256), "louvre_timber": (256, 0, 512, 256), "planks": (512, 0, 768, 256),
    "canvas": (768, 0, 1024, 256),
    "breeze": (0, 256, 256, 512), "zinc": (256, 256, 512, 512), "casement": (512, 256, 768, 512),
    "door_flat": (768, 256, 896, 512), "door_panel": (896, 256, 1024, 512),
    "locker": (0, 512, 128, 768), "bark": (128, 512, 256, 768), "granite": (256, 512, 384, 640),
    "blanket": (384, 512, 512, 640), "grille": (256, 640, 512, 768),
    "flat": (0, 768, 128, 896), "notice": (128, 768, 256, 896), "tyre": (256, 768, 384, 896), "sheet": (384, 768, 512, 896),
    "hdb": (512, 512, 1024, 1024),
}


def pnoise(n, beta=2.0, seed=0, aniso=(1.0, 1.0)):
    r = np.random.default_rng(seed)
    w = r.standard_normal((n, n))
    fy = np.fft.fftfreq(n)[:, None] * aniso[1]
    fx = np.fft.fftfreq(n)[None, :] * aniso[0]
    f = np.sqrt(fx * fx + fy * fy)
    f[0, 0] = 1.0
    spec = np.fft.fft2(w) / (f ** (beta / 2.0))
    spec[0, 0] = 0
    out = np.real(np.fft.ifft2(spec))
    out -= out.min()
    out /= max(out.max(), 1e-9)
    return out


def save_png(arr, path):
    h, w = arr.shape[:2]
    rgba = np.ones((h, w, 4), np.float32)
    rgba[..., :3] = np.clip(arr, 0, 1)
    img = bpy.data.images.new("tmp_" + os.path.basename(path), w, h, alpha=False)
    img.pixels.foreach_set(rgba[::-1].ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def load_png(path):
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    a = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    return a.reshape(h, w, 4)[::-1, :, :3].copy()


def down2(a):
    h, w = a.shape[:2]
    return a.reshape(h // 2, 2, w // 2, 2, 3).mean(axis=(1, 3))


def tex_ground():
    N = AW
    lo, mid, fine = pnoise(N, 3.0, 11), pnoise(N, 2.0, 12), pnoise(N, 0.7, 13)
    v = 0.80 + (lo - 0.5) * 0.14 + (mid - 0.5) * 0.08 + (fine - 0.5) * 0.12
    rs = np.random.default_rng(14)
    for _ in range(14000):
        x, y = rs.integers(0, N - 4, 2)
        s = int(rs.integers(1, 4))
        v[y:y + s, x:x + s] += rs.uniform(-0.28, 0.18)
    for _ in range(9):
        x, y = rs.uniform(0, N, 2)
        a = rs.uniform(0, math.tau)
        for _s in range(int(rs.integers(60, 160))):
            a += rs.uniform(-0.45, 0.45)
            x, y = (x + math.cos(a) * 2.0) % N, (y + math.sin(a) * 2.0) % N
            v[int(y), int(x)] -= 0.22
    blot = pnoise(N, 2.6, 15)
    v -= np.clip(blot - 0.7, 0, 1) * 0.5
    return np.stack([v * 1.0, v * 0.965, v * 0.915], -1)


def tex_atlas():
    a = np.full((AW, AW, 3), 0.8, np.float32)
    n1, n2 = pnoise(AW, 2.0, 21), pnoise(AW, 0.8, 22)
    grain_h = pnoise(AW, 1.6, 23, aniso=(0.06, 1.0))     # horizontal streaks
    grain_v = pnoise(AW, 1.6, 24, aniso=(1.0, 0.06))     # vertical streaks

    def fill(x0, y0, x1, y1, col):
        a[int(y0):int(y1), int(x0):int(x1)] = col

    def mul(x0, y0, x1, y1, k):
        a[int(y0):int(y1), int(x0):int(x1)] *= k

    def noisy(box, field, amt):
        x0, y0, x1, y1 = box
        a[y0:y1, x0:x1] *= (1 + (field[y0:y1, x0:x1] - 0.5) * amt)[..., None]

    def bevel(x0, y0, x1, y1, w=3, lt=1.15, dk=0.7):
        mul(x0, y0, x1, y0 + w, lt)
        mul(x0, y0, x0 + w, y1, lt)
        mul(x0, y1 - w, x1, y1, dk)
        mul(x1 - w, y0, x1, y1, dk)

    # glass louvres in steel frames (two leaves)
    x0, y0, x1, y1 = ATL["louvre_glass"]
    fill(x0, y0, x1, y1, (0.30, 0.36, 0.34))
    for lx0, lx1 in ((x0 + 12, x0 + 124), (x0 + 132, x0 + 244)):
        n = 12
        hgt = (y1 - y0 - 28) / n
        for j in range(n):
            sy = y0 + 14 + j * hgt
            for r in range(int(hgt) - 3):
                t = r / hgt
                fill(lx0 + 5, sy + r, lx1 - 5, sy + r + 1, (0.74 - 0.26 * t, 0.82 - 0.24 * t, 0.85 - 0.22 * t))
            fill(lx0 + 5, sy + 1, lx1 - 5, sy + 3, (0.92, 0.95, 0.96))
            fill(lx0 + 5, sy + hgt - 3, lx1 - 5, sy + hgt, (0.12, 0.15, 0.15))
        bevel(lx0, y0 + 12, lx1, y1 - 12, 4, 1.2, 0.65)
    noisy(ATL["louvre_glass"], n2, 0.12)
    # painted timber louvre shutters (neutral cream; tinted by vertex colour)
    x0, y0, x1, y1 = ATL["louvre_timber"]
    fill(x0, y0, x1, y1, (0.86, 0.84, 0.78))
    bevel(x0, y0, x1, y1, 7, 1.1, 0.72)
    for lx0, lx1 in ((x0 + 10, x0 + 126), (x0 + 130, x0 + 246)):
        bevel(lx0, y0 + 10, lx1, y1 - 10, 5, 1.12, 0.7)
        n = 15
        hgt = (y1 - y0 - 44) / n
        for j in range(n):
            sy = y0 + 22 + j * hgt
            for r in range(int(hgt)):
                t = r / hgt
                fill(lx0 + 11, sy + r, lx1 - 11, sy + r + 1, [(0.94 - 0.32 * t) * c for c in (0.97, 0.95, 0.9)])
            fill(lx0 + 11, sy + hgt - 2, lx1 - 11, sy + hgt, (0.3, 0.28, 0.25))
    noisy(ATL["louvre_timber"], n1, 0.14)
    # timber planks (horizontal), neutral light wood
    x0, y0, x1, y1 = ATL["planks"]
    rs = np.random.default_rng(31)
    for j in range(5):
        py0, py1 = y0 + j * 51.2, y0 + (j + 1) * 51.2
        fill(x0, py0, x1, py1, [c * rs.uniform(0.9, 1.08) for c in (0.82, 0.68, 0.52)])
        fill(x0, py1 - 3, x1, py1, (0.30, 0.24, 0.18))
        for nx in (x0 + 10, x1 - 14):
            fill(nx, py0 + 22, nx + 4, py0 + 26, (0.25, 0.22, 0.2))
    noisy(ATL["planks"], grain_h, 0.4)
    # army canvas / tarpaulin (neutral; tinted olive or cream), with a stitched seam
    x0, y0, x1, y1 = ATL["canvas"]
    fill(x0, y0, x1, y1, (0.84, 0.83, 0.79))
    yy, xx = np.mgrid[y0:y1, x0:x1]
    a[y0:y1, x0:x1] *= (1 + 0.035 * np.sin(xx * 1.7) * np.sin(yy * 1.7))[..., None]
    noisy(ATL["canvas"], n1, 0.2)
    fill(x0, y0 + 124, x1, y0 + 132, (0.66, 0.65, 0.61))
    for sx in range(x0, x1, 9):
        fill(sx, y0 + 119, sx + 5, y0 + 121, (0.6, 0.6, 0.56))
        fill(sx, y0 + 135, sx + 5, y0 + 137, (0.6, 0.6, 0.56))
    # breeze blocks (1960s ventilation blocks): 4 x 4 blocks with a circle + quarter-circle pattern
    x0, y0, x1, y1 = ATL["breeze"]
    fill(x0, y0, x1, y1, (0.86, 0.85, 0.80))
    yy, xx = np.mgrid[0:64, 0:64]
    d_c = np.hypot(xx - 31.5, yy - 31.5)
    d_k = np.minimum.reduce([np.hypot(xx - cx, yy - cy) for cx in (0, 63) for cy in (0, 63)])
    hole = (d_c < 17) | (d_k < 13)
    rim = ((d_c >= 17) & (d_c < 20)) | ((d_k >= 13) & (d_k < 16))
    for bi in range(4):
        for bj in range(4):
            sub = a[y0 + bj * 64:y0 + bj * 64 + 64, x0 + bi * 64:x0 + bi * 64 + 64]
            sub[hole] = (0.09, 0.09, 0.09)
            sub[rim] *= 0.85
            sub[:3, :] *= 0.75
            sub[:, :3] *= 0.75
    noisy(ATL["breeze"], n1, 0.16)
    # corrugated zinc sheet
    x0, y0, x1, y1 = ATL["zinc"]
    xx = np.arange(x1 - x0)
    stripe = 0.72 + 0.16 * np.sin(xx * math.tau / 16)
    a[y0:y1, x0:x1] = stripe[None, :, None] * np.array([0.92, 0.93, 0.94])
    rust = np.clip(grain_v[y0:y1, x0:x1] - 0.55, 0, 1) * 1.6
    a[y0:y1, x0:x1] *= (1 - rust[..., None] * np.array([0.25, 0.4, 0.55]))
    # steel casement windows (community centre)
    x0, y0, x1, y1 = ATL["casement"]
    fill(x0, y0, x1, y1, (0.93, 0.93, 0.9))
    cw, rh = (x1 - x0 - 20) / 3, (y1 - y0 - 20) / 4
    for i in range(3):
        for j in range(4):
            px0, py0 = x0 + 10 + i * cw + 3, y0 + 10 + j * rh + 3
            px1, py1 = px0 + cw - 6, py0 + rh - 6
            for r in range(int(py1 - py0)):
                t = r / (py1 - py0)
                fill(px0, py0 + r, px1, py0 + r + 1, (0.36 - 0.18 * t, 0.43 - 0.2 * t, 0.46 - 0.2 * t))
            fill(px0 + 6, py0 + 4, px0 + 9, py1 - 6, (0.55, 0.62, 0.64))
    # doors: flush timber with a vent at the top, and a four-panel door
    x0, y0, x1, y1 = ATL["door_flat"]
    fill(x0, y0, x1, y1, (0.42, 0.40, 0.37))
    fill(x0 + 6, y0 + 6, x1 - 6, y1, (0.82, 0.80, 0.74))
    noisy((x0 + 6, y0 + 6, x1 - 6, y1), grain_v, 0.25)
    for k in range(5):
        fill(x0 + 22, y0 + 18 + k * 7, x1 - 22, y0 + 21 + k * 7, (0.18, 0.17, 0.16))
    fill(x1 - 26, y0 + 132, x1 - 18, y0 + 150, (0.2, 0.2, 0.2))
    fill(x0 + 6, y1 - 16, x1 - 6, y1, (0.62, 0.6, 0.56))
    x0, y0, x1, y1 = ATL["door_panel"]
    fill(x0, y0, x1, y1, (0.42, 0.40, 0.37))
    fill(x0 + 6, y0 + 6, x1 - 6, y1, (0.84, 0.82, 0.76))
    for (px0, py0, px1, py1) in ((x0 + 16, y0 + 18, x0 + 60, y0 + 118), (x0 + 68, y0 + 18, x1 - 16, y0 + 118),
                                 (x0 + 16, y0 + 132, x0 + 60, y1 - 18), (x0 + 68, y0 + 132, x1 - 16, y1 - 18)):
        bevel(px0, py0, px1, py1, 4, 0.72, 1.15)
    fill(x1 - 22, y0 + 124, x1 - 15, y0 + 138, (0.2, 0.2, 0.2))
    noisy(ATL["door_panel"], grain_v, 0.18)
    # steel locker: two doors with vents
    x0, y0, x1, y1 = ATL["locker"]
    fill(x0, y0, x1, y1, (0.80, 0.82, 0.81))
    bevel(x0, y0, x1, y1, 4, 1.1, 0.65)
    fill(x0 + 62, y0, x0 + 66, y1, (0.3, 0.32, 0.32))
    for dx in (x0 + 10, x0 + 74):
        for k in range(6):
            fill(dx + 6, y0 + 16 + k * 7, dx + 38, y0 + 19 + k * 7, (0.25, 0.27, 0.27))
            fill(dx + 6, y1 - 58 + k * 7, dx + 38, y1 - 55 + k * 7, (0.25, 0.27, 0.27))
        fill(dx + 40, y0 + 110, dx + 44, y0 + 140, (0.3, 0.3, 0.3))
        fill(dx + 12, y0 + 70, dx + 32, y0 + 82, (0.95, 0.95, 0.92))
    # bark
    x0, y0, x1, y1 = ATL["bark"]
    v = 0.55 + (grain_v[y0:y1, x0:x1] - 0.5) * 0.9
    a[y0:y1, x0:x1] = v[..., None] * np.array([0.66, 0.58, 0.50])
    # granite (heritage marker)
    x0, y0, x1, y1 = ATL["granite"]
    v = 0.34 + (n2[y0:y1, x0:x1] - 0.5) * 0.12
    sp = np.random.default_rng(41).random((y1 - y0, x1 - x0))
    v = np.where(sp > 0.95, v + 0.16, np.where(sp < 0.05, v - 0.08, v))
    a[y0:y1, x0:x1] = v[..., None] * np.array([1.0, 0.99, 0.97])
    # grey army blanket with two dark stripes
    x0, y0, x1, y1 = ATL["blanket"]
    fill(x0, y0, x1, y1, (0.60, 0.58, 0.54))
    noisy(ATL["blanket"], n2, 0.35)
    for sy in (y0 + 20, y1 - 28):
        fill(x0, sy, x1, sy + 8, (0.26, 0.25, 0.24))
    # lorry radiator grille
    x0, y0, x1, y1 = ATL["grille"]
    fill(x0, y0, x1, y1, (0.5, 0.5, 0.48))
    for bx in range(x0 + 14, x1 - 14, 11):
        fill(bx, y0 + 12, bx + 5, y1 - 12, (0.07, 0.07, 0.07))
    fill(x0 + 10, y0 + 60, x1 - 10, y0 + 66, (0.5, 0.5, 0.48))
    bevel(x0, y0, x1, y1, 8, 1.15, 0.6)
    # flat white (untextured parts: vertex colour only)
    fill(*ATL["flat"], (0.98, 0.98, 0.98))
    # cork notice board with pinned sheets (no text)
    x0, y0, x1, y1 = ATL["notice"]
    fill(x0, y0, x1, y1, (0.35, 0.25, 0.18))
    fill(x0 + 8, y0 + 8, x1 - 8, y1 - 8, (0.66, 0.48, 0.32))
    noisy(ATL["notice"], n2, 0.3)
    rs = np.random.default_rng(51)
    for _ in range(6):
        px, py = rs.integers(x0 + 12, x1 - 50), rs.integers(y0 + 12, y1 - 56)
        w, h = rs.integers(28, 44), rs.integers(36, 50)
        fill(px, py, px + w, py + h, (0.95, 0.94, 0.9) if rs.random() < 0.7 else (0.95, 0.9, 0.7))
        for ln in range(py + 8, py + h - 6, 6):
            fill(px + 5, ln, px + w - 5 - rs.integers(0, 12), ln + 2, (0.55, 0.55, 0.58))
        fill(px + w // 2 - 2, py + 2, px + w // 2 + 2, py + 6, (0.8, 0.15, 0.1))
    # tyre tread
    x0, y0, x1, y1 = ATL["tyre"]
    fill(x0, y0, x1, y1, (0.13, 0.13, 0.13))
    for ty in range(y0 + 4, y1 - 4, 16):
        fill(x0 + 10, ty, x0 + 58, ty + 8, (0.24, 0.24, 0.24))
        fill(x0 + 70, ty + 8, x1 - 10, ty + 16, (0.24, 0.24, 0.24))
    # white sheet / pillow ticking
    x0, y0, x1, y1 = ATL["sheet"]
    fill(x0, y0, x1, y1, (0.93, 0.92, 0.88))
    noisy(ATL["sheet"], n1, 0.2)
    for sx in range(x0 + 6, x1, 16):
        fill(sx, y0, sx + 2, y1, (0.82, 0.84, 0.9))
    # present-day HDB elevation (from the void-deck facade texture)
    fac = load_png(os.path.join(TEX_VD, "1024", "facade.png"))
    x0, y0, x1, y1 = ATL["hdb"]
    a[y0:y1, x0:x1] = down2(fac)
    return a


def ensure_textures():
    need = RETEX or not all(os.path.exists(os.path.join(TEX_CAMP, str(r), f + ".png")) for r in (1024, 512) for f in ("atlas", "ground"))
    if not need:
        return
    for r in (1024, 512):
        os.makedirs(os.path.join(TEX_CAMP, str(r)), exist_ok=True)
    for name, fn in (("ground", tex_ground), ("atlas", tex_atlas)):
        arr = fn()
        save_png(arr, os.path.join(TEX_CAMP, "1024", name + ".png"))
        save_png(down2(arr), os.path.join(TEX_CAMP, "512", name + ".png"))
        print("texture", name)


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
CREAM = C(0.93, 0.90, 0.81)
OFFWHITE = C(0.96, 0.94, 0.88)
CEIL = C(0.90, 0.89, 0.85)
CEMENT = C(0.78, 0.76, 0.71)
JADE = C(0.58, 0.73, 0.64)
PALEBLUE = C(0.66, 0.78, 0.85)
OCHRE = C(0.88, 0.74, 0.54)
SALMON = C(0.86, 0.64, 0.54)
TARMAC = C(0.56, 0.53, 0.49)
LATERITE = C(0.84, 0.55, 0.36)
DIRT = C(0.66, 0.52, 0.40)
GRASS_THEN = C(0.90, 0.84, 0.60)
GRASS_OUT = C(0.84, 0.82, 0.62)
GRASS_NOW = C(1.0, 1.0, 0.96)
LEAF = C(0.92, 1.0, 0.88)
LEAF_DARK = C(0.70, 0.80, 0.66)
BARK = C(0.72, 0.64, 0.56)
TIMBER = C(0.86, 0.72, 0.56)
TIMBER_DARK = C(0.52, 0.40, 0.30)
IRON = C(0.22, 0.24, 0.23)
BEDGREEN = C(0.26, 0.34, 0.29)
STEEL = C(0.62, 0.64, 0.64)
ARMY = C(0.30, 0.35, 0.24)
ARMY_DARK = C(0.20, 0.23, 0.17)
CANVAS_OLIVE = C(0.62, 0.64, 0.46)
CANVAS_CREAM = C(1.0, 0.97, 0.90)
RED = C(0.74, 0.18, 0.15)
TEMASEK = C(0.36, 0.45, 0.31)
TYRE = C(0.15, 0.15, 0.15)
GLASS_DARK = C(0.55, 0.58, 0.62)
DOORS = [C(0.36, 0.52, 0.48), C(0.40, 0.48, 0.64), C(0.58, 0.40, 0.30), C(0.46, 0.56, 0.40), C(0.62, 0.30, 0.26)]
WARM = C(1.0, 0.86, 0.62)


# ======================================================================================
# Geometry builder (same scheme as build_kopitiam.py), plus an area and a transform stack
# ======================================================================================
MATS = ["M_Plaster", "M_Ground", "M_Grass", "M_Foliage", "M_Atlas", "M_Water", "M_Emissive", "M_Decal"]


class MB:
    __slots__ = ("v", "f", "uv", "col", "sm")

    def __init__(s):
        s.v, s.f, s.uv, s.col, s.sm = [], [], [], [], []


BUCKETS = {}       # (group, tier) -> {mat: MB}
GROUP_AREA = {}    # group -> area
OBJ_XF = {}        # group -> object matrix (geometry emitted in local space)
STATE = {"group": None, "tier": "base", "area": None, "xf": None}
AREAS = ["Parade", "Barracks", "Night", "CC"]


@contextmanager
def AREA(name):
    old = (STATE["area"], STATE["group"])
    STATE["area"], STATE["group"] = name, name + "_Static"
    try:
        yield
    finally:
        STATE["area"], STATE["group"] = old


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


@contextmanager
def XF(M):
    old = STATE["xf"]
    STATE["xf"] = M if old is None else old @ M
    try:
        yield
    finally:
        STATE["xf"] = old


def bucket(mat):
    g = STATE["group"]
    GROUP_AREA.setdefault(g, STATE["area"])
    b = BUCKETS.setdefault((g, STATE["tier"]), {})
    if mat not in b:
        b[mat] = MB()
    return b[mat]


def _xf(pts):
    M = STATE["xf"]
    if M is None:
        return [tuple(p) for p in pts]
    return [tuple(M @ Vector(p)) for p in pts]


def emit(mat, wpts, uvs, col, smooth=False):
    b = bucket(mat)
    base = len(b.v)
    b.v.extend(_xf(wpts))
    b.f.append(tuple(range(base, base + len(wpts))))
    b.uv.append(list(uvs))
    b.col.append(col)
    b.sm.append(smooth)


def emit_indexed(mat, wverts, faces, uvs, col, smooth=True):
    b = bucket(mat)
    base = len(b.v)
    b.v.extend(_xf(wverts))
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
    pts = [tuple(p) for p in pts]
    if uv is None and mat == "M_Atlas":
        uv = [FLAT] * len(pts)
    elif uv is None and mat in UNTEXTURED:
        uv = [(0.5, 0.5)] * len(pts)
    emit(mat, pts, uv if uv is not None else boxuv(pts, s), col, smooth)


def faceN(mat, pts, col, n, uv=None, s=1.0):
    """Face whose winding is fixed so its normal points along n."""
    pts = [tuple(p) for p in pts]
    nn = newell(pts)
    if nn[0] * n[0] + nn[1] * n[1] + nn[2] * n[2] < 0:
        pts = pts[::-1]
        if uv is not None:
            uv = list(uv)[::-1]
    face(mat, pts, col, uv=uv, s=s)


def cuv(cell, u, v, ins=3):
    x0, y0, x1, y1 = ATL[cell]
    x = x0 + ins + u * (x1 - x0 - 2 * ins)
    yi = y1 - ins - v * (y1 - y0 - 2 * ins)
    return (x / AW, 1 - yi / AW)


def cquad(cell, u0=0.0, v0=0.0, u1=1.0, v1=1.0):
    return [cuv(cell, u0, v0), cuv(cell, u1, v0), cuv(cell, u1, v1), cuv(cell, u0, v1)]


FLAT = cuv("flat", 0.5, 0.5)


def tiled(p0, du, dv, W, H, cell, col, tw=1.2, th=1.2, mat="M_Atlas"):
    """Panel from p0 spanning W along unit vector du and H along dv (normal = du x dv), tiling one atlas cell
    every tw x th metres (partial tiles get partial UVs)."""
    p0, du, dv = Vector(p0), Vector(du), Vector(dv)
    nu, nv = max(1, math.ceil(W / tw - 1e-6)), max(1, math.ceil(H / th - 1e-6))
    for i in range(nu):
        u0, u1 = i * tw, min(W, (i + 1) * tw)
        for j in range(nv):
            v0, v1 = j * th, min(H, (j + 1) * th)
            pts = [p0 + du * u0 + dv * v0, p0 + du * u1 + dv * v0, p0 + du * u1 + dv * v1, p0 + du * u0 + dv * v1]
            emit(mat, [tuple(q) for q in pts], cquad(cell, 0, 0, (u1 - u0) / tw, (v1 - v0) / th), col)
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


def box(mat, a, b, col, s=1.0, skip=(), cells=None, cols=None, mats=None, cell="flat"):
    """Axis-aligned box. For M_Atlas faces, `cell` / `cells` pick the atlas cell (stretched over each face)."""
    a2 = (min(a[0], b[0]), min(a[1], b[1]), min(a[2], b[2]))
    b2 = (max(a[0], b[0]), max(a[1], b[1]), max(a[2], b[2]))
    for k, pts in box_faces(a2, b2).items():
        if k in skip:
            continue
        m = (mats or {}).get(k, mat)
        c = (cells or {}).get(k, cell)
        uv = None
        if m == "M_Atlas":
            uv = [FLAT] * 4 if c == "flat" else cquad(c)
        face(m, pts, (cols or {}).get(k, col), uv=uv, s=s)


def abox(a, b, col, **kw):
    box("M_Atlas", a, b, col, **kw)


def M_at(x, y, z, rz=0.0, rx=0.0, ry=0.0):
    return Matrix.Translation((x, y, z)) @ Matrix.Rotation(rz, 4, "Z") @ Matrix.Rotation(ry, 4, "Y") @ Matrix.Rotation(rx, 4, "X")


def mbox(M, mat, size, col, s=1.0, skip=(), cell="flat", cells=None, cols=None):
    sx, sy, sz = size[0] / 2, size[1] / 2, size[2] / 2
    for k, pts in box_faces((-sx, -sy, -sz), (sx, sy, sz)).items():
        if k in skip:
            continue
        wp = [tuple(M @ Vector(p)) for p in pts]
        c = (cells or {}).get(k, cell)
        if mat == "M_Atlas":
            uv = [FLAT] * 4 if c == "flat" else cquad(c)
        else:
            uv = boxuv(wp, s)
        emit(mat, wp, uv, (cols or {}).get(k, col))


def quad(mat, p0, p1, p2, p3, col=WHITE, uv=UV01):
    emit(mat, [tuple(p0), tuple(p1), tuple(p2), tuple(p3)], uv, col)


def wall_y(mat, x0, x1, z0, z1, y, col, facing="-y", s=1.0, cell=None, uv=None):
    if facing == "-y":
        pts = [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)]
    else:
        pts = [(x1, y, z0), (x0, y, z0), (x0, y, z1), (x1, y, z1)]
    if cell:
        uv = [FLAT] * 4 if cell == "flat" else cquad(cell)
    face(mat, pts, col, uv=uv, s=s)


def wall_x(mat, y0, y1, z0, z1, x, col, facing="+x", s=1.0, cell=None, uv=None):
    if facing == "+x":
        pts = [(x, y0, z0), (x, y1, z0), (x, y1, z1), (x, y0, z1)]
    else:
        pts = [(x, y1, z0), (x, y0, z0), (x, y0, z1), (x, y1, z1)]
    if cell:
        uv = [FLAT] * 4 if cell == "flat" else cquad(cell)
    face(mat, pts, col, uv=uv, s=s)


def vj(x, y, amt=0.06, f=0.21):
    """Smooth, position-only colour variation (so neighbouring cells share vertex colours)."""
    return 1.0 + amt * (math.sin(x * f + 1.7 * math.sin(y * f * 0.7)) * math.cos(y * f * 1.3 + 0.5 * math.sin(x * f * 0.9))
                        + 0.5 * math.sin(x * f * 2.9 + y * f * 2.3))


def vcols(pts, col, amt=0.06):
    return [mul(col, vj(p[0], p[1], amt)) for p in pts]


def grid_floor(mat, x0, x1, y0, y1, z, col, s=1.0, cell=1.5, down=False, colfn=None, zfn=None, vamt=0.0, smooth=False):
    nx = max(1, int(round((x1 - x0) / cell)))
    ny = max(1, int(round((y1 - y0) / cell)))
    for i in range(nx):
        for j in range(ny):
            a, b = x0 + (x1 - x0) * i / nx, x0 + (x1 - x0) * (i + 1) / nx
            c, d = y0 + (y1 - y0) * j / ny, y0 + (y1 - y0) * (j + 1) / ny
            if zfn:
                pts = [(a, c, zfn(a, c)), (b, c, zfn(b, c)), (b, d, zfn(b, d)), (a, d, zfn(a, d))]
            else:
                pts = [(a, c, z), (b, c, z), (b, d, z), (a, d, z)]
            if down:
                pts = pts[::-1]
            cc = colfn((a + b) / 2, (c + d) / 2) if colfn else col
            if vamt:
                cc = vcols(pts, cc, vamt)
            face(mat, pts, cc, s=s, smooth=smooth)


UNTEXTURED = ("M_Emissive", "M_Water", "M_Decal")


def _uvmap(mat, cell, fu, fv, mu, mv):
    if mat in UNTEXTURED:
        return (0.5, 0.5)
    if mat == "M_Atlas":
        return FLAT if (cell or "flat") == "flat" else cuv(cell, min(max(fu, 0), 1), min(max(fv, 0), 1))
    return (mu, mv)


def cyl(mat, c, r, h, n, col, caps=True, s=1.0, r_top=None, smooth=True, cap_col=None, cell=None):
    rt = r if r_top is None else r_top
    verts = [(c[0] + math.cos(math.tau * i / n) * r, c[1] + math.sin(math.tau * i / n) * r, c[2]) for i in range(n)]
    verts += [(c[0] + math.cos(math.tau * i / n) * rt, c[1] + math.sin(math.tau * i / n) * rt, c[2] + h) for i in range(n)]
    faces, uvs = [], []
    circ = math.tau * max(r, rt)
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
        u0, u1 = i / n * circ / s, (i + 1) / n * circ / s
        uvs.append([_uvmap(mat, cell, i / n, 0, u0, 0), _uvmap(mat, cell, (i + 1) / n, 0, u1, 0),
                    _uvmap(mat, cell, (i + 1) / n, 1, u1, h / s), _uvmap(mat, cell, i / n, 1, u0, h / s)])
    emit_indexed(mat, verts, faces, uvs, col, smooth=smooth)
    if caps:
        cu = [FLAT] * n if mat == "M_Atlas" else [(0.5 + 0.5 * math.cos(math.tau * i / n), 0.5 + 0.5 * math.sin(math.tau * i / n)) for i in range(n)]
        emit(mat, [verts[n + i] for i in range(n)], cu, cap_col or col)
        emit(mat, [verts[i] for i in reversed(range(n))], [FLAT if mat == "M_Atlas" else (0.5, 0.5)] * n, col)


def tube(mat, p0, p1, r, n, col, s=1.0, caps=False, smooth=True, cell=None, r1=None):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    if L < 1e-6:
        return
    z = d.normalized()
    x = z.orthogonal().normalized()
    y = z.cross(x)
    rr = (r, r if r1 is None else r1)
    verts = []
    for k, end in enumerate((p0, p1)):
        for i in range(n):
            a = math.tau * i / n
            verts.append(tuple(end + (x * math.cos(a) + y * math.sin(a)) * rr[k]))
    faces, uvs = [], []
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
        uvs.append([_uvmap(mat, cell, i / n, 0, i / n, 0), _uvmap(mat, cell, (i + 1) / n, 0, (i + 1) / n, 0),
                    _uvmap(mat, cell, (i + 1) / n, 1, (i + 1) / n, L / s), _uvmap(mat, cell, i / n, 1, i / n, L / s)])
    emit_indexed(mat, verts, faces, uvs, col, smooth=smooth)
    if caps:
        f0 = FLAT if mat == "M_Atlas" else (0, 0)
        emit(mat, [verts[i] for i in reversed(range(n))], [f0] * n, col)
        emit(mat, [verts[n + i] for i in range(n)], [f0] * n, col)


def sphere(mat, c, r, col, nu=8, nv=6, sz=1.0, s=None, cell=None):
    """UV sphere. Tiling materials get metre-scaled UVs (s = texture tile size)."""
    s = s or 2.0
    c = Vector(c)
    verts = [tuple(c + Vector((0, 0, -r * sz)))]
    for j in range(1, nv):
        th = math.pi * j / nv - math.pi / 2
        for i in range(nu):
            a = math.tau * i / nu
            verts.append(tuple(c + Vector((math.cos(th) * math.cos(a) * r, math.cos(th) * math.sin(a) * r, math.sin(th) * r * sz))))
    verts.append(tuple(c + Vector((0, 0, r * sz))))
    top = len(verts) - 1
    circ = math.tau * r / s
    hgt = math.pi * r * max(sz, 0.5) / s

    def U(i, k):
        return _uvmap(mat, cell, i / nu, k / nv, i / nu * circ, k / nv * hgt)

    faces, uvs = [], []
    for i in range(nu):
        j = (i + 1) % nu
        faces.append((0, 1 + j, 1 + i))
        uvs.append([U(i + 0.5, 0), U(i + 1, 1), U(i, 1)])
    for k in range(nv - 2):
        for i in range(nu):
            j = (i + 1) % nu
            a, b = 1 + k * nu + i, 1 + k * nu + j
            faces.append((a, b, b + nu, a + nu))
            uvs.append([U(i, k + 1), U(i + 1, k + 1), U(i + 1, k + 2), U(i, k + 2)])
    last = 1 + (nv - 2) * nu
    for i in range(nu):
        j = (i + 1) % nu
        faces.append((last + i, last + j, top))
        uvs.append([U(i, nv - 1), U(i + 1, nv - 1), U(i + 0.5, nv)])
    emit_indexed(mat, verts, faces, uvs, col, smooth=True)


def prism_x(mat, profile, x0, x1, col, cell="flat", caps=True, inside_col=None):
    """Extrude a (y, z) profile polyline along x (e.g. the lorry's canvas tilt). Outer faces + optional inner."""
    n = len(profile)
    for i in range(n - 1):
        (ya, za), (yb, zb) = profile[i], profile[i + 1]
        pts = [(x0, ya, za), (x1, ya, za), (x1, yb, zb), (x0, yb, zb)]
        uv = [FLAT] * 4 if cell == "flat" else cquad(cell, 0, i / (n - 1), 1, (i + 1) / (n - 1))
        emit(mat, pts, uv, col)
        if inside_col is not None:
            emit(mat, pts[::-1], uv[::-1], inside_col)


# ======================================================================================
# Registries: markers, colliders
# ======================================================================================
MARKERS = []     # (name, pos, facing, props, area)
COLLIDERS = []   # (name, (x0,y0,z0,x1,y1,z1), props, area)
_colcount = {}


def marker(name, pos, face_dir=(0, -1), props=None):
    assert all(m[0] != name for m in MARKERS), "duplicate marker " + name
    MARKERS.append((name, tuple(pos), face_dir, props or {}, STATE["area"]))


def marker3(name, pos3, yaw=None, props=None, look=None):
    """Marker from three.js coords (as in ns-fallback.js); yaw in three.js convention, or a look-at target (three)."""
    p = P3(*pos3)
    if look is not None:
        t = P3(*look)
        fd = (t[0] - p[0], t[1] - p[1], t[2] - p[2])
    else:
        fd = F3(yaw) if yaw is not None else None
    marker(name, p, fd, props)


def collider(name, a, b, props=None, unique=True):
    props = dict(props or {})
    g = STATE["group"] or ""
    if g.startswith("THEN_"):
        props.setdefault("state", "then")
    elif g.startswith("NOW_"):
        props.setdefault("state", "now")
    props.setdefault("area", STATE["area"])
    x0, y0, z0 = [min(p, q) for p, q in zip(a, b)]
    x1, y1, z1 = [max(p, q) for p, q in zip(a, b)]
    if not unique:
        _colcount[name] = _colcount.get(name, 0) + 1
        name = f"{name}_{_colcount[name]}"
    assert all(c[0] != name for c in COLLIDERS), "duplicate collider " + name
    COLLIDERS.append((name, (x0, y0, z0, x1, y1, z1), props, STATE["area"]))


def facing(frm, to):
    return (to[0] - frm[0], to[1] - frm[1])


# ======================================================================================
# Shared props
# ======================================================================================
def tree(x, y, sc=1.0, seed=0, kind="rain", z0=0.0, col_name=None, dense=True):
    """Rain tree (broad umbrella) / angsana (rounder) / casuarina (tall, narrow). Trunk on the atlas bark cell."""
    rr = random.Random(seed)
    lc = jitter(LEAF, 0.1, rr)
    if kind == "casuarina":
        h = 9.0 * sc
        tube("M_Atlas", (x, y, z0), (x, y, z0 + h), 0.16 * sc, 6, BARK, cell="bark", r1=0.07 * sc)
        for k in range(5):
            zz = z0 + h * (0.35 + 0.14 * k)
            sphere("M_Foliage", (x + rr.uniform(-0.3, 0.3), y + rr.uniform(-0.3, 0.3), zz), (1.5 - 0.2 * k) * sc,
                   mul(lc, 0.85), nu=7, nv=5, sz=0.9, s=2.0)
    else:
        th = (3.0 if kind == "rain" else 3.8) * sc
        tube("M_Atlas", (x, y, z0 - 0.1), (x, y, z0 + th), 0.24 * sc, 7, BARK, cell="bark", r1=0.19 * sc)
        spread = (3.4 if kind == "rain" else 2.2) * sc
        nb = 4 if kind == "rain" else 3
        for k in range(nb):
            a = k * math.tau / nb + rr.uniform(0, 1)
            tube("M_Atlas", (x, y, z0 + th - 0.3), (x + math.cos(a) * spread * 0.7, y + math.sin(a) * spread * 0.7, z0 + th + 1.5 * sc),
                 0.12 * sc, 5, BARK, cell="bark", r1=0.07 * sc)
        nblob = (9 if kind == "rain" else 7) if dense else 5
        for k in range(nblob):
            a = rr.uniform(0, math.tau)
            r = rr.uniform(0.3, 1.0) * spread
            zc = z0 + th + (1.8 + rr.uniform(-0.3, 0.8)) * sc
            sphere("M_Foliage", (x + math.cos(a) * r, y + math.sin(a) * r, zc), rr.uniform(1.8, 2.5) * sc,
                   jitter(lc, 0.12, rr), nu=8, nv=5, sz=0.55 if kind == "rain" else 0.75, s=2.0)
    if col_name:
        collider(col_name, (x - 0.3 * sc, y - 0.3 * sc, 0), (x + 0.3 * sc, y + 0.3 * sc, 4), unique=False)


def shrub(x, y, r, col=LEAF, z0=0.0, seed=0, n=3):
    rr = random.Random(seed)
    for k in range(n):
        a = rr.uniform(0, math.tau)
        d = rr.uniform(0, r * 0.6)
        sphere("M_Foliage", (x + math.cos(a) * d, y + math.sin(a) * d, z0 + r * 0.35), r * rr.uniform(0.6, 0.9),
               jitter(col, 0.12, rr), nu=7, nv=4, sz=0.7, s=1.5)


def bed_frame(M, col=BEDGREEN, mattress=False, detail=True, blanket=False):
    """Iron single bed, 1.9 x 0.8 m, long axis on local Y (head at +Y), feet on z = 0 (local)."""
    L, W = 1.9, 0.8
    hy, hx = L / 2, W / 2
    with XF(M):
        for (px, py, ph) in ((-hx, hy, 0.85), (hx, hy, 0.85), (-hx, -hy, 0.62), (hx, -hy, 0.62)):
            tube("M_Atlas", (px, py, 0), (px, py, ph), 0.018, 5, col, smooth=False)
        for (py, ph) in ((hy, 0.85), (-hy, 0.62)):
            tube("M_Atlas", (-hx, py, ph - 0.02), (hx, py, ph - 0.02), 0.016, 5, col, smooth=False)
            tube("M_Atlas", (-hx, py, 0.36), (hx, py, 0.36), 0.014, 4, col, smooth=False)
            nb = 5 if detail else 3
            for k in range(1, nb):
                bx = -hx + W * k / nb
                tube("M_Atlas", (bx, py, 0.36), (bx, py, ph - 0.03), 0.009, 4, col, smooth=False)
        # angle-iron side rails + the wire spring
        for sx in (-1, 1):
            box("M_Atlas", (sx * hx - 0.02, -hy, 0.34), (sx * hx + 0.02, hy, 0.39), col)
        box("M_Atlas", (-hx + 0.02, -hy + 0.02, 0.355), (hx - 0.02, hy - 0.02, 0.365), mul(STEEL, 0.7), skip=("-x", "+x", "-y", "+y"))
        if mattress:
            box("M_Atlas", (-hx + 0.02, -hy + 0.03, 0.365), (hx - 0.02, hy - 0.03, 0.46), C(0.86, 0.84, 0.76), cell="sheet",
                cells={"-x": "flat", "+x": "flat", "-y": "flat", "+y": "flat"}, skip=("-z",))
            box("M_Atlas", (-hx + 0.08, hy - 0.42, 0.46), (hx - 0.08, hy - 0.08, 0.53), OFFWHITE, cell="sheet", skip=("-z",))
            if blanket:
                box("M_Atlas", (-hx + 0.05, -hy + 0.06, 0.46), (hx - 0.05, -hy + 0.5, 0.52), WHITE, cell="blanket", skip=("-z",))


# ======================================================================================
# 1960s slab block of one-room flats (open corridor on the front = local -y side)
# ======================================================================================
BAY = 3.3
STOREY = 2.97          # 18 risers of 0.165
FLAT_DEPTH = 6.2
CORR = 1.8


def slab_block(x0, nb, yf, storeys=5, accent=JADE, base=0.0, tower=True, detail=True, lit=0.0, seed=0, laundry=True):
    """Front (corridor side) faces -y at y = yf; ground floor at z = base. Returns dims."""
    rr = random.Random(seed)
    x1 = x0 + nb * BAY
    yw, yb = yf + CORR, yf + CORR + FLAT_DEPTH
    zr = base + storeys * STOREY
    # plinth / ground floor slab (corridor floor on the ground)
    grid_floor("M_Plaster", x0, x1, yf - 0.25, yw, base + 0.001, CEMENT, s=2.0, cell=BAY)
    face("M_Plaster", [(x0, yf - 0.25, base - 0.3), (x1, yf - 0.25, base - 0.3), (x1, yf - 0.25, base + 0.001), (x0, yf - 0.25, base + 0.001)], mul(CEMENT, 0.85), s=2.0)
    # columns along the corridor front
    for i in range(nb + 1):
        x = x0 + i * BAY
        box("M_Plaster", (x - 0.16, yf - 0.12, base), (x + 0.16, yf + 0.2, zr + 0.55), OFFWHITE, s=2.0, skip=("-z", "+z", "+y"))
    for k in range(storeys):
        z = base + k * STOREY
        zc = z + STOREY - 0.15
        for i in range(nb):
            xa, xb = x0 + i * BAY, x0 + (i + 1) * BAY
            # corridor ceiling + (upper floors) corridor floor, slab band and solid parapet
            face("M_Plaster", [(xa, yw, zc), (xb, yw, zc), (xb, yf, zc), (xa, yf, zc)], CEIL, s=2.0)
            if k >= 1:
                face("M_Plaster", [(xa, yf, z), (xb, yf, z), (xb, yw, z), (xa, yw, z)], CEMENT, s=2.0)
                wall_y("M_Plaster", xa + 0.16, xb - 0.16, z - 0.15, z + 0.12, yf - 0.02, accent, s=2.0)
                wall_y("M_Plaster", xa + 0.16, xb - 0.16, z + 0.12, z + 1.0, yf - 0.02, CREAM, s=2.0)
                face("M_Plaster", [(xa + 0.16, yf - 0.02, z + 1.0), (xb - 0.16, yf - 0.02, z + 1.0), (xb - 0.16, yf + 0.12, z + 1.0), (xa + 0.16, yf + 0.12, z + 1.0)], OFFWHITE, s=2.0)
                wall_y("M_Plaster", xa + 0.16, xb - 0.16, z, z + 1.0, yf + 0.12, CREAM, facing="+y", s=2.0)
            # slab edge above the top floor
            if k == storeys - 1:
                wall_y("M_Plaster", xa + 0.16, xb - 0.16, zc, zr + 0.55, yf - 0.02, CREAM, s=2.0)
            # flat front: wall, door, louvred window, breeze-block fanlight
            wall_y("M_Plaster", xa, xb, z, zc, yw, jitter(OFFWHITE, 0.03, rr), s=2.0)
            dc = rr.choice(DOORS)
            wall_y("M_Atlas", xa + 0.35, xa + 1.25, z, z + 2.1, yw - 0.012, dc, cell="door_flat")
            wall_y("M_Atlas", xa + 0.35, xa + 1.25, z + 2.18, z + 2.5, yw - 0.012, WHITE, uv=cquad("breeze", 0, 0, 1, 0.25))
            lit_here = lit and rr.random() < lit
            wall_y("M_Atlas", xa + 1.65, xa + 2.95, z + 1.0, z + 2.15, yw - 0.012, mul(WHITE, 0.55) if lit else WHITE,
                   cell="louvre_glass" if rr.random() < 0.7 else "louvre_timber")
            if lit_here:
                wall_y("M_Emissive", xa + 1.72, xa + 2.88, z + 1.06, z + 2.09, yw - 0.02, WARM)
            if detail and k >= 1 and rr.random() < 0.35:
                with DETAIL():
                    for q in range(rr.randint(1, 3)):     # potted plants on the parapet ledge
                        px = xa + 0.5 + q * 0.45 + rr.uniform(0, 0.3)
                        cyl("M_Atlas", (px, yf + 0.3, z), 0.12, 0.22, 7, C(0.62, 0.36, 0.26), caps=False)
                        sphere("M_Atlas", (px, yf + 0.3, z + 0.34), 0.2, C(0.36, 0.55, 0.30), nu=6, nv=4, sz=0.9)
            # back: wall + two louvre windows (+ laundry poles on the desktop tier)
            wall_y("M_Plaster", xa, xb, z - 0.15 if k else base - 0.3, z + STOREY - 0.15 if k < storeys - 1 else zr + 0.55, yb, jitter(CREAM, 0.03, rr), facing="+y", s=2.0)
            for wx in (xa + 0.4, xa + 1.9):
                wall_y("M_Atlas", wx, wx + 1.0, z + 1.0, z + 2.1, yb + 0.012, WHITE, facing="+y", cell="louvre_glass")
            if detail and laundry and k >= 1 and rr.random() < 0.5:
                with DETAIL():
                    zz = z + 2.2
                    px = xa + rr.uniform(0.8, 2.4)
                    tube("M_Atlas", (px, yb, zz), (px + rr.uniform(-0.2, 0.2), yb + 1.9, zz + 0.1), 0.025, 4, C(0.8, 0.7, 0.45), smooth=False)
                    for q in range(rr.randint(1, 3)):
                        t = 0.35 + 0.28 * q
                        cx, cy = px, yb + 1.9 * t
                        w, d = rr.uniform(0.35, 0.6), rr.uniform(0.4, 0.8)
                        c = rr.choice([C(0.92, 0.92, 0.88), C(0.55, 0.65, 0.78), C(0.82, 0.55, 0.5), C(0.9, 0.82, 0.6), TEMASEK])
                        for fa in (-1, 1):
                            face("M_Atlas", [(cx - w / 2 * fa, cy, zz - d), (cx + w / 2 * fa, cy, zz - d), (cx + w / 2 * fa, cy, zz), (cx - w / 2 * fa, cy, zz)], c)
    # end walls (full depth, full height)
    box("M_Plaster", (x0 - 0.2, yf - 0.12, base - 0.3), (x0, yb, zr + 0.55), CREAM, s=2.0, skip=("-z",))
    box("M_Plaster", (x1, yf - 0.12, base - 0.3), (x1 + 0.2, yb, zr + 0.55), CREAM, s=2.0, skip=("-z",))
    # roof slab + parapet + tanks
    face("M_Plaster", [(x0, yf, zr + 0.2), (x1, yf, zr + 0.2), (x1, yb, zr + 0.2), (x0, yb, zr + 0.2)], mul(CEMENT, 0.8), s=3.0)
    box("M_Plaster", (x0, yb - 0.15, zr + 0.2), (x1, yb, zr + 0.55), CREAM, s=2.0, skip=("-z", "+y"))
    box("M_Plaster", (x0 + 2, yb - 4.0, zr + 0.2), (x0 + 5, yb - 1.0, zr + 1.9), mul(CEMENT, 0.95), s=2.0, skip=("-z",))
    return dict(x0=x0, x1=x1, yf=yf, yw=yw, yb=yb, zr=zr)


# ---- the stair tower in front of a block's east end: open ground storey, breeze-block screens above.
# Flight A rises toward +y (three -z) in the west strip, a half landing at the block face, flight B rises +x
# along the block face to the first-floor landing (NE corner). Local x is relative to flight A's centre line
# (three x = 22), local y relative to the block front (yf).
TW = dict(xw=-1.10, xa0=-0.95, xa1=0.60, run0=-5.15, xb0=0.80, xb1=3.00, xe=4.40, xe1=4.75, ys=-5.45, yface=-0.20)
NRISE, RISE, TREAD_A, TREAD_B = 9, 0.165, 0.25, 0.275


def stair_tower(cx, yf, zr, base=0.0, walk=False, accent=JADE):
    t = TW
    xw, xa0, xa1 = cx + t["xw"], cx + t["xa0"], cx + t["xa1"]
    xb0, xb1, xe, xe1 = cx + t["xb0"], cx + t["xb1"], cx + t["xe"], cx + t["xe1"]
    yA0 = yf + t["run0"]                  # riser 1 of flight A
    yL0 = yA0 + (NRISE - 1) * TREAD_A     # riser 9 = start of the half landing
    ys = yf + t["ys"]                     # south face of the tower
    yN = yf + t["yface"]                  # north edge of the landing / flight B
    yB0 = yN - 1.4                        # south edge of the flight B strip
    zL = base + NRISE * RISE              # half landing
    z1 = base + STOREY                    # first floor
    zt_all = zr + 2.4
    # --- flight A: solid stepped mass (treads + risers; the sides are walls)
    for i in range(1, NRISE):
        ya, yb2 = yA0 + (i - 1) * TREAD_A, yA0 + i * TREAD_A
        zt = base + i * RISE
        face("M_Plaster", [(xa0, ya, zt), (xa1, ya, zt), (xa1, yb2, zt), (xa0, yb2, zt)], CEMENT, s=1.0)
        face("M_Plaster", [(xa0, ya, zt - RISE), (xa1, ya, zt - RISE), (xa1, ya, zt), (xa0, ya, zt)], mul(CEMENT, 0.9), s=1.0)
        face("M_Plaster", [(xa0, ya - 0.002, zt - 0.035), (xa1, ya - 0.002, zt - 0.035), (xa1, ya - 0.002, zt), (xa0, ya - 0.002, zt)], mul(CEMENT, 0.68), s=1.0)
    face("M_Plaster", [(xa0, yL0, zL - RISE), (xb0, yL0, zL - RISE), (xb0, yL0, zL), (xa0, yL0, zL)], mul(CEMENT, 0.9), s=1.0)
    grid_floor("M_Plaster", xa0, xb0, yL0, yN, zL, CEMENT, s=1.0, cell=0.8)
    # --- flight B (and its twin one storey up): treads/risers with a sloped soffit, rising +x
    def flight_b(zlo):
        for i in range(1, NRISE):
            xa_, xb_ = xb0 + (i - 1) * TREAD_B, xb0 + i * TREAD_B
            zt = zlo + i * RISE
            face("M_Plaster", [(xa_, yB0, zt), (xb_, yB0, zt), (xb_, yN, zt), (xa_, yN, zt)], CEMENT, s=1.0)
            face("M_Plaster", [(xa_, yN, zt - RISE), (xa_, yB0, zt - RISE), (xa_, yB0, zt), (xa_, yN, zt)], mul(CEMENT, 0.9), s=1.0)
            zs0, zs1 = zlo + (i - 1) * RISE - 0.25, zlo + i * RISE - 0.25
            face("M_Plaster", [(xa_, yB0, zs0), (xb_, yB0, zs1), (xb_, yB0, zt), (xa_, yB0, zt)], mul(CREAM, 0.9), s=1.0)
        face("M_Plaster", [(xb1, yN, zlo + (NRISE - 1) * RISE), (xb1, yB0, zlo + (NRISE - 1) * RISE), (xb1, yB0, zlo + NRISE * RISE), (xb1, yN, zlo + NRISE * RISE)],
             mul(CEMENT, 0.9), s=1.0)
        faceN("M_Plaster", [(xb0, yB0, zlo - 0.25), (xb1, yB0, zlo + (NRISE - 1) * RISE - 0.25), (xb1, yN, zlo + (NRISE - 1) * RISE - 0.25), (xb0, yN, zlo - 0.25)],
              CEIL, (0.3, 0, -1), s=2.0)
    flight_b(zL)
    flight_b(zL + STOREY)
    # flight A's twin above (its soffit is the ceiling over flight A), the landing above, the first floor
    faceN("M_Plaster", [(xa0, yA0, z1 - 0.2), (xa1, yA0, z1 - 0.2), (xa1, yL0, z1 + zL - base - 0.3), (xa0, yL0, z1 + zL - base - 0.3)], CEIL, (0, 0.3, -1), s=2.0)
    face("M_Plaster", [(xa0, ys, z1 - 0.2), (xa0, yA0, z1 - 0.2), (xa1, yA0, z1 - 0.2), (xa1, ys, z1 - 0.2)], CEIL, s=2.0)
    face("M_Plaster", [(xa0, yL0, z1 + zL - base - 0.15), (xa0, yN, z1 + zL - base - 0.15), (xb0, yN, z1 + zL - base - 0.15), (xb0, yL0, z1 + zL - base - 0.15)], CEIL, s=2.0)
    grid_floor("M_Plaster", xb1, xe, yB0, yN, z1, CEMENT, s=1.0, cell=0.7)
    face("M_Plaster", [(xa1, ys, z1 + 0.001), (xe, ys, z1 + 0.001), (xe, yB0, z1 + 0.001), (xa1, yB0, z1 + 0.001)], CEMENT, s=2.0)
    face("M_Plaster", [(xb1, yB0, z1 + STOREY - 0.15), (xb1, yN, z1 + STOREY - 0.15), (xe, yN, z1 + STOREY - 0.15), (xe, yB0, z1 + STOREY - 0.15)], CEIL, s=2.0)
    # --- west side of flight A: a parapet that follows the flight, open above it to the first floor
    top = [(ys, base + 1.0), (yA0, base + 1.0), (yL0, zL + 1.0), (yN + 0.2, zL + 1.0)]
    for (ya, za), (yb2, zb) in zip(top[:-1], top[1:]):
        faceN("M_Plaster", [(xw, ya, base - 0.3), (xw, yb2, base - 0.3), (xw, yb2, zb), (xw, ya, za)], CREAM, (-1, 0, 0), s=2.0)
        zi_a = base + max(0, min(NRISE - 1, (ya - yA0) / TREAD_A)) * RISE if ya < yL0 else zL
        zi_b = base + max(0, min(NRISE - 1, (yb2 - yA0) / TREAD_A)) * RISE if yb2 <= yL0 else zL
        faceN("M_Plaster", [(xa0, ya, zi_a), (xa0, yb2, zi_b), (xa0, yb2, zb), (xa0, ya, za)], mul(CREAM, 0.95), (1, 0, 0), s=2.0)
        faceN("M_Plaster", [(xw, ya, za), (xw, yb2, zb), (xa0, yb2, zb), (xa0, ya, za)], OFFWHITE, (0, 0, 1), s=2.0)
    face("M_Plaster", [(xw, ys, base - 0.3), (xa0, ys, base - 0.3), (xa0, ys, base + 1.0), (xw, ys, base + 1.0)], CREAM, s=2.0)
    box("M_Plaster", (xw, ys, z1 - 0.2), (xa0, yN + 0.2, zt_all), CREAM, s=2.0)
    # --- north side (against the block): parapet over the landing / flight B / first-floor landing, solid below
    yo, yi = yN + 0.2, yN
    for (xa_, xb_, za_, zb_) in ((xa0, xb0, zL, zL), (xb0, xb1, zL, z1), (xb1, xe, z1, z1)):
        faceN("M_Plaster", [(xa_, yo, base - 0.3), (xb_, yo, base - 0.3), (xb_, yo, zb_ + 1.0), (xa_, yo, za_ + 1.0)], CREAM, (0, 1, 0), s=2.0)
        faceN("M_Plaster", [(xa_, yi, za_), (xb_, yi, zb_), (xb_, yi, zb_ + 1.0), (xa_, yi, za_ + 1.0)], mul(CREAM, 0.95), (0, -1, 0), s=2.0)
        faceN("M_Plaster", [(xa_, yi, za_ + 1.0), (xb_, yi, zb_ + 1.0), (xb_, yo, zb_ + 1.0), (xa_, yo, za_ + 1.0)], OFFWHITE, (0, 0, 1), s=2.0)
    # --- the store (under the first floor, SE), the east wall, the screened tower above
    box("M_Plaster", (xa1, ys, base - 0.3), (xe1, yB0, z1), CREAM, s=2.0, skip=("-z", "+z"))
    box("M_Plaster", (xe, yB0, base - 0.3), (xe1, yN + 0.2, z1), CREAM, s=2.0, skip=("-z", "+z"))
    wall_x("M_Plaster", yB0, yN, base, zL, xb0 - 0.001, mul(CREAM, 0.9), facing="-x", s=2.0)
    wall_x("M_Atlas", yB0 + 0.2, yB0 + 1.1, base, base + 2.0, xb0 - 0.012, DOORS[1], facing="-x", cell="door_panel")
    box("M_Plaster", (xe, ys, z1), (xe1, yN + 0.2, zt_all), CREAM, s=2.0, skip=("-z",))
    box("M_Plaster", (xa0, ys, z1), (xe, ys + 0.15, zt_all), CREAM, s=2.0, skip=("-z", "+y"))
    for k in range(1, 6):
        zk = base + k * STOREY
        if zk + 2.0 > zt_all:
            break
        hh = 1.8
        tiled((xw - 0.012, yN - 0.3, zk + 0.55), (0, -1, 0), (0, 0, 1), yN - 0.3 - ys - 0.5, hh, "breeze", WHITE)
        tiled((xw + 0.35, ys - 0.012, zk + 0.55), (1, 0, 0), (0, 0, 1), xe1 - xw - 0.7, hh, "breeze", WHITE)
        tiled((xe1 + 0.012, ys + 0.5, zk + 0.55), (0, 1, 0), (0, 0, 1), yN - 0.3 - ys - 0.5, hh, "breeze", WHITE)
        # slab band round the outside of the tower (south, west and east faces only: keeps headroom over the flights)
        box("M_Plaster", (xw - 0.04, ys - 0.04, zk - 0.2), (xe1 + 0.04, ys + 0.16, zk + 0.1), accent, s=2.0, skip=("+y",))
        box("M_Plaster", (xw - 0.04, ys + 0.16, zk - 0.2), (xw + 0.16, yN + 0.2, zk + 0.1), accent, s=2.0, skip=("+y", "-y", "+x"))
        box("M_Plaster", (xe1 - 0.16, ys + 0.16, zk - 0.2), (xe1 + 0.04, yN + 0.2, zk + 0.1), accent, s=2.0, skip=("+y", "-y", "-x"))
    # tower top + water tank
    box("M_Plaster", (xw - 0.06, ys - 0.06, zt_all), (xe1 + 0.06, yN + 0.26, zt_all + 0.25), OFFWHITE, s=2.0, skip=("-z",))
    box("M_Plaster", (xw + 0.6, ys + 0.8, zt_all + 0.25), (xe1 - 0.6, yN - 0.6, zt_all + 1.6), mul(CEMENT, 0.9), s=2.0, skip=("-z",))
    # steel handrails (desktop)
    with DETAIL():
        tube("M_Atlas", (xa0 + 0.06, yA0, base + 0.92), (xa0 + 0.06, yL0, zL + 0.92), 0.022, 6, IRON)
        tube("M_Atlas", (xb0, yN - 0.06, zL + 0.92), (xb1, yN - 0.06, z1 + 0.92), 0.022, 6, IRON)
    return dict(xw=xw, xa0=xa0, xa1=xa1, xb0=xb0, xb1=xb1, xe=xe, xe1=xe1, yA0=yA0, yL0=yL0, ys=ys, yN=yN, yB0=yB0, zL=zL, z1=z1)


# ======================================================================================
# AREA_Parade — Taman Jurong Camp, 1967–68
# ======================================================================================
RX0, RX1, RY0, RY1 = -84.0, 84.0, -48.0, 56.0      # the THEN / NOW ground region (Blender); outside is static
SQ = (-30.0, 30.0, -20.0, 20.0)                     # the square (three x -30..30, z -20..20)
BLOCK_A = dict(x0=-19.2, nb=14, yf=33.6)            # three z -33.6..-41.6; stair tower at x = 22
BLOCK_B = dict(x0=-62.0, nb=12, yf=36.5)
BLOCK_C = dict(x0=34.0, nb=12, yf=37.0)
STAIR_CX = 22.0
DAIS = (5.0, 11.0, -26.0, -22.6, 0.6)               # x0, x1, y0, y1 (three z 22.6..26), height
STANDS = [(-10.5, 3.6), (12.4, 26.5)]               # x ranges; front at three z 24.3
STAND_FRONT = -24.3
ROW_D, ROW_H0, ROW_DH = 1.2, 0.25, 0.42


def ground_type(x, y):
    if SQ[0] <= x < SQ[1] and SQ[2] <= y < SQ[3]:
        return "square"
    if 22.0 <= y < 31.0 and -78 <= x < 78:
        return "road"
    if y >= 31.0 and -70 <= x < 80:
        return "apron"
    if -44 <= x < -38 and -44 <= y < 31:
        return "road"
    if -14 <= x < 30 and -32 <= y < SQ[2]:
        return "laterite"
    if SQ[2] - 2 <= y < SQ[3] + 2 and SQ[0] - 2 <= x < SQ[1] + 2:
        return "laterite"
    return "grass"


def build_parade_ground():
    rr = random.Random(5)
    # static ground: outside the THEN/NOW region + a hidden sub-layer under it (so the ground ray always hits)
    def outside(x0, x1, y0, y1, cell):
        nx, ny = int(round((x1 - x0) / cell)), int(round((y1 - y0) / cell))
        for i in range(nx):
            for j in range(ny):
                a, b = x0 + i * cell, x0 + (i + 1) * cell
                c, d = y0 + j * cell, y0 + (j + 1) * cell
                if RX0 <= a and b <= RX1 and RY0 <= c and d <= RY1:
                    continue
                pts = [(a, c, 0), (b, c, 0), (b, d, 0), (a, d, 0)]
                face("M_Grass", pts, vcols(pts, GRASS_OUT, 0.06), s=3.0)
    outside(-100, 100, -100, 100, 4.0)
    for (a, b, c, d) in ((-124, 124, 100, 124), (-124, 124, -124, -100), (-124, -100, -100, 100), (100, 124, -100, 100)):
        grid_floor("M_Grass", a, b, c, d, 0.0, GRASS_OUT, s=3.0, cell=12.0)
    for (a, b, c, d) in ((-420, 420, 124, 420), (-420, 420, -420, -124), (-420, -124, -124, 124), (124, 420, -124, 124)):
        grid_floor("M_Grass", a, b, c, d, -0.02, GRASS_OUT, s=3.0, cell=48.0)
    grid_floor("M_Grass", RX0, RX1, RY0, RY1, -0.05, GRASS_OUT, s=3.0, cell=28.0)
    # 1967: tarmac square, laterite roads and aprons, patchy grass (THEN_Square)
    with GROUP("THEN_Square"):
        for x0, x1, cell in ((RX0, -44.0, 4.0), (-44.0, 44.0, 2.0), (44.0, RX1, 4.0)):
            nx, ny = int(round((x1 - x0) / cell)), int(round((RY1 - RY0) / cell))
            for i in range(nx):
                for j in range(ny):
                    a, b = x0 + i * cell, x0 + (i + 1) * cell
                    c, d = RY0 + j * cell, RY0 + (j + 1) * cell
                    t = ground_type((a + b) / 2, (c + d) / 2)
                    pts = [(a, c, 0), (b, c, 0), (b, d, 0), (a, d, 0)]
                    if t == "square":
                        face("M_Ground", pts, vcols(pts, TARMAC, 0.04), s=4.0)
                    elif t in ("road", "laterite"):
                        face("M_Ground", pts, vcols(pts, LATERITE, 0.06), s=3.0)
                    elif t == "apron":
                        face("M_Ground", pts, vcols(pts, mul(LATERITE, 0.9), 0.05), s=3.0)
                    else:
                        face("M_Grass", pts, vcols(pts, GRASS_THEN, 0.07), s=3.0)
        # concrete kerb round the square
        x0, x1, y0, y1 = SQ
        for (a, b) in (((x0 - 0.25, y0 - 0.25), (x1 + 0.25, y0)), ((x0 - 0.25, y1), (x1 + 0.25, y1 + 0.25)),
                       ((x0 - 0.25, y0), (x0, y1)), ((x1, y0), (x1 + 0.25, y1))):
            box("M_Ground", (a[0], a[1], 0), (b[0], b[1], 0.07), C(0.86, 0.85, 0.8), s=2.0, skip=("-z",))
        # painted white right-marker spots along the north edge of the square (the drill line's markers)
        for x in range(-24, 25, 6):
            box("M_Ground", (x - 0.12, 16.5, 0), (x + 0.12, 16.74, 0.012), C(0.95, 0.94, 0.9), s=2.0, skip=("-z", "-x", "+x", "-y", "+y"))


def build_blocks():
    with GROUP("THEN_Blocks"):
        A = slab_block(BLOCK_A["x0"], BLOCK_A["nb"], BLOCK_A["yf"], accent=JADE, seed=1)
        slab_block(BLOCK_B["x0"], BLOCK_B["nb"], BLOCK_B["yf"], accent=PALEBLUE, seed=2)
        slab_block(BLOCK_C["x0"], BLOCK_C["nb"], BLOCK_C["yf"], accent=OCHRE, seed=3)
        st = stair_tower(STAIR_CX, A["yf"], A["zr"], walk=True, accent=JADE)
        # visual towers on the other two blocks
        B = BLOCK_B
        stair_tower(B["x0"] + B["nb"] * BAY - 5.2, B["yf"], 5 * STOREY, accent=PALEBLUE)
        Cb = BLOCK_C
        stair_tower(Cb["x0"] + Cb["nb"] * BAY - 5.2, Cb["yf"], 5 * STOREY, accent=OCHRE)
        # notice board + fire buckets at block A's foot (period camp dressing)
        wall_y("M_Atlas", 14.2, 15.6, 1.0, 1.9, A["yw"] - 0.02, WHITE, cell="notice")
        with DETAIL():
            for i in range(4):
                cyl("M_Atlas", (10.6 + i * 0.4, A["yw"] - 0.25, 1.1), 0.13, 0.28, 8, RED, r_top=0.15)
            box("M_Atlas", (10.3, A["yw"] - 0.06, 1.35), (12.1, A["yw"] - 0.01, 1.4), RED)
        # --- colliders (block A walkable at the ground and on the stair; B and C solid)
        yf, yw, yb, x0, x1 = A["yf"], A["yw"], A["yb"], A["x0"], A["x1"]
        collider("COL_BlockA_Flats", (x0, yw, 0), (x1, yb, 16))
        collider("COL_BlockA_EndW", (x0 - 0.25, yf - 0.15, 0), (x0, yb, 16))
        collider("COL_BlockA_EndE", (x1, yf - 0.15, 0), (x1 + 0.25, yb, 16))
        for i in range(BLOCK_A["nb"] + 1):
            x = x0 + i * BAY
            if st["xw"] - 0.3 < x < st["xe1"] + 0.3:
                continue
            collider("COL_BlockA_Col", (x - 0.16, yf - 0.12, 0), (x + 0.16, yf + 0.2, 3), unique=False)
        collider("COL_BlockA_Parapet1", (x0, yf - 0.12, STOREY - 0.1), (st["xb1"], yf + 0.15, STOREY + 2.0))
        for nm, Bk in (("B", BLOCK_B), ("C", BLOCK_C)):
            bx0, bx1 = Bk["x0"], Bk["x0"] + Bk["nb"] * BAY
            collider(f"COL_Block{nm}", (bx0 - 0.25, Bk["yf"] - 0.15, 0), (bx1 + 0.25, Bk["yf"] + CORR + FLAT_DEPTH, 16))
            tx = bx1 - 5.2
            collider(f"COL_Block{nm}_Tower", (tx + TW["xw"], Bk["yf"] + TW["ys"], 0), (tx + TW["xe1"], Bk["yf"], 16))
        # the stair: walls round flight A, the landing, flight B, and the first-floor landing (a dead end)
        collider("COL_Stair_W", (st["xw"] - 0.05, st["ys"], 0), (st["xa0"], st["yN"] + 0.25, 16))
        collider("COL_Stair_Store", (st["xa1"], st["ys"], 0), (st["xe1"], st["yB0"], 16))
        collider("COL_Stair_UnderB", (st["xb0"], st["yB0"], 0), (st["xe1"], st["yN"], 1.3))
        collider("COL_Stair_N", (st["xw"], st["yN"], 0.6), (st["xe1"], yf + 0.2, 16))
        collider("COL_Stair_E", (st["xe"], st["yB0"], 0), (st["xe1"] + 0.1, yf + 0.2, 16))
    return A, st


def build_stair_dressing(A, st):
    """Parapets on the open ground storey of the tower, the bed stack on the first-floor landing."""
    with GROUP("THEN_BedPile"):
        # the pile of iron bed frames by the stair foot (against the store wall of the tower), and two cupboards
        ys = st["ys"]
        rr = random.Random(9)
        for k in range(4):              # lying stacked flat
            bed_frame(M_at(24.25 + rr.uniform(-0.05, 0.05), ys - 1.1, k * 0.40, math.pi / 2 + rr.uniform(-0.06, 0.06)), detail=k == 3)
        for k in range(3):              # leaning on the wall
            bed_frame(M_at(25.6 + k * 0.1, ys - 0.28 - k * 0.12, 0.0, math.pi / 2, rx=math.radians(-72 + k * 4)), detail=False)
        for k, (lx, ly) in enumerate(((27.35, ys + 0.9), (27.4, ys + 2.0))):
            mbox(M_at(lx, ly, 0.9, math.radians(90 + 6 * (k * 2 - 1))), "M_Atlas", (0.9, 0.5, 1.8), C(0.58, 0.66, 0.60), cells={"-y": "locker"})
        collider("COL_BedPile", (23.2, ys - 1.65, 0), (26.9, ys, 1.8))
        collider("COL_Cupboards", (26.95, ys + 0.3, 0), (27.75, ys + 2.6, 1.8))
        # beds waiting on the first-floor landing (why the stair stops there)
        z1 = st["z1"]
        for k in range(3):
            bed_frame(M_at(st["xb1"] + 0.55 + k * 0.28, st["yB0"] + 0.25, z1, 0.0, rx=math.radians(-80)), detail=False)


def build_prop_bed():
    """The carried bed (PROP_Bed): origin at its centre, long axis along local ±Y."""
    pos = P3(22.0, 0.45, -27.4)
    with GROUP("PROP_Bed"):
        bed_frame(Matrix.Translation((0, 0, -0.425)), col=BEDGREEN, detail=True)
    OBJ_XF["PROP_Bed"] = Matrix.Translation(pos) @ Matrix.Rotation(math.pi, 4, "Z")


def build_dais():
    x0, x1, y0, y1, h = DAIS
    with GROUP("THEN_Dais"):
        # platform: plank top, white canvas skirt with a red band
        abox((x0, y0, 0), (x1, y1, h), WHITE, cell="planks", skip=("-z",), cells={"-y": "canvas", "+y": "canvas", "-x": "canvas", "+x": "canvas"},
             cols={"+z": TIMBER, "-y": CANVAS_CREAM, "+y": CANVAS_CREAM, "-x": CANVAS_CREAM, "+x": CANVAS_CREAM})
        box("M_Atlas", (x0 - 0.01, y1 - 0.02, h - 0.14), (x1 + 0.01, y1 + 0.01, h - 0.06), RED, skip=("-z", "+z"))
        # steps at the back
        for k in range(3):
            abox((6.8, y0 - 0.3 * (k + 1), 0), (9.2, y0 - 0.3 * k, h * (3 - k) / 4), TIMBER_DARK, cell="planks", skip=("-z",))
        # awning: four white posts, a pitched canvas roof, scalloped valance
        zt = h + 2.55
        for (px, py) in ((x0 + 0.12, y1 - 0.12), (x1 - 0.12, y1 - 0.12), (x0 + 0.12, y0 + 0.12), (x1 - 0.12, y0 + 0.12)):
            box("M_Atlas", (px - 0.06, py - 0.06, h), (px + 0.06, py + 0.06, zt), OFFWHITE, skip=("-z",))
        ym = (y0 + y1) / 2
        ridge = zt + 0.7
        for (ya, yb_) in ((y1 + 0.3, ym), (y0 - 0.3, ym)):
            pts = [(x0 - 0.3, ya, zt), (x1 + 0.3, ya, zt), (x1 + 0.3, yb_, ridge), (x0 - 0.3, yb_, ridge)]
            faceN("M_Atlas", pts, CANVAS_CREAM, (0, (ya - ym), 1), uv=cquad("canvas"))
            faceN("M_Atlas", pts, mul(CANVAS_CREAM, 0.8), (0, -(ya - ym), -1), uv=cquad("canvas"))
        for (yy, nrm) in ((y1 + 0.3, -1), (y0 - 0.3, 1)):
            ns = 12
            for k in range(ns):
                xa = x0 - 0.3 + (x1 - x0 + 0.6) * k / ns
                xb = x0 - 0.3 + (x1 - x0 + 0.6) * (k + 1) / ns
                pts = [(xa, yy, zt - 0.22), ((xa + xb) / 2, yy, zt - 0.34), (xb, yy, zt - 0.22), (xb, yy, zt), (xa, yy, zt)]
                c = RED if k % 2 else CANVAS_CREAM
                faceN("M_Atlas", pts, c, (0, nrm, 0))
                faceN("M_Atlas", pts, mul(c, 0.8), (0, -nrm, 0))
        # gable ends
        for xx, nrm in ((x0 - 0.3, -1), (x1 + 0.3, 1)):
            pts = [(xx, y1 + 0.3, zt), (xx, y0 - 0.3, zt), (xx, ym, ridge)]
            faceN("M_Atlas", pts, CANVAS_CREAM, (nrm, 0, 0))
            faceN("M_Atlas", pts, mul(CANVAS_CREAM, 0.8), (-nrm, 0, 0))
        # lectern + microphone at the front, VIP chairs behind
        abox((7.7, y1 - 0.75, h), (8.3, y1 - 0.4, h + 1.05), TIMBER_DARK, cell="planks", skip=("-z",))
        tube("M_Atlas", (8.0, y1 - 0.5, h + 1.05), (8.0, y1 - 0.25, h + 1.4), 0.008, 4, IRON, smooth=False)
        sphere("M_Atlas", (8.0, y1 - 0.25, h + 1.42), 0.03, IRON, nu=6, nv=4)
        for k in range(6):
            cx = 5.6 + k * 0.95
            folding_chair(cx, y0 + 0.9, h, NORTH)
        # flagpole (bare: the flag is a runtime decal)
        fx, fy = 3.6, y1 + 0.6
        box("M_Plaster", (fx - 0.45, fy - 0.45, 0), (fx + 0.45, fy + 0.45, 0.3), CEMENT, skip=("-z",))
        cyl("M_Atlas", (fx, fy, 0.3), 0.075, 11.5, 10, OFFWHITE, r_top=0.04, caps=False)
        sphere("M_Atlas", (fx, fy, 11.85), 0.09, C(0.85, 0.72, 0.3), nu=8, nv=5)
        with DETAIL():
            tube("M_Atlas", (fx + 0.05, fy, 1.2), (fx + 0.05, fy, 11.7), 0.004, 3, OFFWHITE, smooth=False)
            box("M_Atlas", (fx + 0.07, fy - 0.03, 1.1), (fx + 0.1, fy + 0.03, 1.3), IRON)
        marker("SNAP_Flagpole", (fx, fy, 6.0), SOUTH)
        collider("COL_Dais", (x0 - 0.1, y0 - 1.0, 0), (x1 + 0.1, y1 + 0.35, 1.8))
        collider("COL_Flagpole", (fx - 0.45, fy - 0.45, 0), (fx + 0.45, fy + 0.45, 3))


def folding_chair(x, y, z, fdir, col=C(0.40, 0.46, 0.42)):
    rz = math.atan2(fdir[0], -fdir[1])
    M = M_at(x, y, z, rz)
    with XF(M):
        box("M_Atlas", (-0.21, -0.2, 0.43), (0.21, 0.2, 0.46), TIMBER)
        box("M_Atlas", (-0.21, 0.17, 0.62), (0.21, 0.2, 0.86), TIMBER)
        for sx in (-0.19, 0.19):
            tube("M_Atlas", (sx, -0.2, 0), (sx, 0.19, 0.9), 0.012, 4, col, smooth=False)
            tube("M_Atlas", (sx, 0.2, 0), (sx, -0.18, 0.45), 0.012, 4, col, smooth=False)


def build_stands():
    seats = []
    with GROUP("THEN_Stands"):
        for si, (sa, sb) in enumerate(STANDS):
            nrows = 4
            for r in range(nrows):
                yf_ = STAND_FRONT - r * ROW_D
                yk = yf_ - ROW_D
                h = ROW_H0 + r * ROW_DH
                abox((sa, yk, 0), (sb, yf_, h), WHITE, cell="planks", skip=("-z", "+y" if r else "none"),
                     cols={"+z": jitter(TIMBER, 0.05), "-y": TIMBER_DARK, "+y": mul(TIMBER, 0.8), "-x": TIMBER_DARK, "+x": TIMBER_DARK})
                if r:
                    abox((sa, yf_ - 0.02, 0), (sb, yf_, h), mul(TIMBER, 0.78), cell="planks", skip=("-z", "-y"))
                # bench: plank seat on the back half of the row
                by0, by1 = yk + 0.08, yk + 0.42
                abox((sa + 0.1, by0, h + 0.4), (sb - 0.1, by1, h + 0.45), TIMBER, cell="planks", skip=("-z",))
                for bx in np.arange(sa + 0.4, sb - 0.2, 1.8):
                    abox((bx, by0 + 0.1, h), (bx + 0.06, by1 - 0.1, h + 0.4), TIMBER_DARK, skip=("-z", "+z"))
                # seat positions on this row: feet on the platform, seat 0.45 behind
                nseat = int((sb - sa - 0.6) / 0.62)
                for k in range(nseat):
                    seats.append((si, r, sa + 0.6 + k * 0.62, by1 + 0.18, h))
            # awning: posts front and back, a mono-pitch army-canvas roof
            yb_ = STAND_FRONT - nrows * ROW_D
            zf, zb = 3.5, 4.6
            xs = list(np.arange(sa + 0.1, sb, 3.5)) + [sb - 0.1]
            for px in xs:
                box("M_Atlas", (px - 0.07, STAND_FRONT - 0.2, 0), (px + 0.07, STAND_FRONT - 0.06, zf), mul(TIMBER, 0.85), skip=("-z",))
                box("M_Atlas", (px - 0.07, yb_ - 0.14, 0), (px + 0.07, yb_, zb), mul(TIMBER, 0.85), skip=("-z",))
                tube("M_Atlas", (px, STAND_FRONT - 0.13, zf - 0.1), (px, yb_ - 0.07, zb - 0.1), 0.05, 4, TIMBER_DARK, smooth=False)
            pts = [(sa - 0.4, STAND_FRONT + 0.4, zf), (sb + 0.4, STAND_FRONT + 0.4, zf), (sb + 0.4, yb_ - 0.4, zb + 0.05), (sa - 0.4, yb_ - 0.4, zb + 0.05)]
            nsec = max(1, int(round((sb - sa) / 3.5)))
            for k in range(nsec):
                xa, xb = sa - 0.4 + (sb - sa + 0.8) * k / nsec, sa - 0.4 + (sb - sa + 0.8) * (k + 1) / nsec
                pp = [(xa, pts[0][1], zf), (xb, pts[0][1], zf), (xb, pts[2][1], zb + 0.05), (xa, pts[2][1], zb + 0.05)]
                faceN("M_Atlas", pp, jitter(CANVAS_OLIVE, 0.04), (0, 0.2, 1), uv=cquad("canvas"))
                faceN("M_Atlas", pp, mul(CANVAS_OLIVE, 0.75), (0, -0.2, -1), uv=cquad("canvas"))
                # front valance
                vv = [(xa, STAND_FRONT + 0.4, zf - 0.35), (xb, STAND_FRONT + 0.4, zf - 0.35), (xb, STAND_FRONT + 0.4, zf), (xa, STAND_FRONT + 0.4, zf)]
                faceN("M_Atlas", vv, mul(CANVAS_OLIVE, 0.9), (0, 1, 0), uv=cquad("canvas", 0, 0.45, 1, 0.55))
                faceN("M_Atlas", vv, mul(CANVAS_OLIVE, 0.7), (0, -1, 0), uv=cquad("canvas", 0, 0.45, 1, 0.55))
            collider(f"COL_Stand_{si + 1}", (sa - 0.1, yb_ - 0.2, 0), (sb + 0.1, STAND_FRONT, 3.0))
        # folding chairs in front of the stands (guests), leaving STAND_X clear
        for x in (-8.8, -8.2, -7.6, 0.4, 1.0, 1.6, 2.2, 16.6, 17.2, 17.8, 18.4, 22.8, 23.4, 24.0):
            folding_chair(x, STAND_FRONT + 1.2, 0.0, NORTH)
    return seats


def build_edge():
    """1967: low concrete-post fence with pipe rails, a guarded gate, camp trees, lamp posts."""
    with GROUP("THEN_Edge"):
        fx0, fx1, fy0, fy1 = -80.0, 80.0, -44.0, 52.0
        gate = (-44.0, -38.0)       # the west road leaves through the south fence here (x range)
        runs = [((fx0, fy0), (gate[0], fy0)), ((gate[1], fy0), (fx1, fy0)), ((fx1, fy0), (fx1, fy1)), ((fx1, fy1), (fx0, fy1)), ((fx0, fy1), (fx0, fy0))]
        for (a, b) in runs:
            L = math.dist(a, b)
            n = max(1, int(L / 3.0))
            for k in range(n + 1):
                t = k / n
                px, py = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
                box("M_Atlas", (px - 0.07, py - 0.07, 0), (px + 0.07, py + 0.07, 1.15), CEMENT, skip=("-z",))
            for zz in (0.5, 1.0):
                tube("M_Atlas", (a[0], a[1], zz), (b[0], b[1], zz), 0.025, 5, OFFWHITE)
            with DETAIL():
                tube("M_Atlas", (a[0], a[1], 1.3), (b[0], b[1], 1.3), 0.006, 3, IRON, smooth=False)
            collider("COL_Fence", (min(a[0], b[0]) - 0.15, min(a[1], b[1]) - 0.15, 0), (max(a[0], b[0]) + 0.15, max(a[1], b[1]) + 0.15, 2.0), unique=False)
        # gate posts, boom barrier, guard hut
        for gx in gate:
            box("M_Plaster", (gx - 0.25, fy0 - 0.25, 0), (gx + 0.25, fy0 + 0.25, 1.6), OFFWHITE, s=2.0, skip=("-z",))
        for k in range(8):
            xa = gate[0] + 0.3 + k * 0.68
            box("M_Atlas", (xa, fy0 - 0.05, 0.95), (xa + 0.68, fy0 + 0.05, 1.05), RED if k % 2 else OFFWHITE)
        hx, hy = gate[1] + 2.5, fy0 + 3.0
        box("M_Plaster", (hx, hy, 0), (hx + 2.4, hy + 2.2, 2.5), CREAM, s=2.0, skip=("-z",))
        box("M_Plaster", (hx - 0.3, hy - 0.3, 2.5), (hx + 2.7, hy + 2.5, 2.65), OFFWHITE, s=2.0)
        wall_x("M_Atlas", hy + 0.4, hy + 1.8, 1.0, 2.0, hx - 0.012, mul(WHITE, 0.8), facing="-x", cell="casement")
        wall_y("M_Atlas", hx + 0.8, hx + 1.7, 0, 2.1, hy - 0.012, DOORS[3], cell="door_flat")
        collider("COL_GuardHut", (hx, hy, 0), (hx + 2.4, hy + 2.2, 3))
        # camp trees (rain trees, angsana, a casuarina line to the east)
        spots = [(-30, -36, "rain"), (-12, -38, "angsana"), (6, -39, "rain"), (24, -37, "angsana"), (40, -36, "rain"), (58, -38, "rain"),
                 (-58, -22, "rain"), (-62, 0, "angsana"), (-56, 18, "rain"), (-50, 40, "angsana"),
                 (60, -20, "rain"), (64, 2, "angsana"), (58, 22, "rain"), (-14, 28.5, "angsana"), (30.5, 29, "angsana")]
        for i, (x, y, kind) in enumerate(spots):
            tree(x, y, 1.0 + R.uniform(-0.1, 0.15), seed=100 + i, kind=kind, col_name="COL_Tree")
        for i in range(8):
            tree(74, -34 + i * 9.5, 0.9, seed=200 + i, kind="casuarina")
        # lamp posts along the road in front of the blocks
        for x in (-50, -30, -10, 10, 30, 50):
            tube("M_Atlas", (x, 30.4, 0), (x, 30.4, 6.2), 0.07, 6, C(0.55, 0.56, 0.55))
            tube("M_Atlas", (x, 30.4, 6.1), (x, 29.3, 6.4), 0.05, 5, C(0.55, 0.56, 0.55))
            box("M_Atlas", (x - 0.14, 28.9, 6.25), (x + 0.14, 29.5, 6.4), C(0.45, 0.46, 0.45))
        # a parked Land Rover-ish jeep shape and a water tanker trailer by block C (camp life, far away)
        with DETAIL():
            for (jx, jy) in ((40.0, 27.0), (45.5, 27.2)):
                jeep(jx, jy)


def jeep(x, y):
    M = M_at(x, y, 0, math.pi / 2)
    with XF(M):
        abox((-0.8, -1.9, 0.45), (0.8, 1.7, 1.15), ARMY, skip=("-z",))
        abox((-0.75, -1.9, 1.15), (0.75, -0.6, 1.25), ARMY_DARK)
        face("M_Atlas", [(-0.72, -0.62, 1.25), (0.72, -0.62, 1.25), (0.72, -0.52, 1.75), (-0.72, -0.52, 1.75)], GLASS_DARK, uv=cquad("louvre_glass", 0.1, 0.1, 0.4, 0.3))
        prism_x("M_Atlas", [(-0.5, 1.15), (-0.5, 1.8), (1.7, 1.8), (1.7, 1.15)], -0.78, 0.78, CANVAS_OLIVE, cell="canvas")
        for (wx, wy) in ((-0.8, -1.25), (0.8, -1.25), (-0.8, 1.1), (0.8, 1.1)):
            tube("M_Atlas", (wx - 0.12, wy, 0.38), (wx + 0.12, wy, 0.38), 0.38, 10, TYRE, cell="tyre", caps=True)


def build_parade_static():
    rr = random.Random(77)
    # far treeline (secondary jungle and plantation round Jurong) + low hills
    for i in range(170):
        a = rr.uniform(0, math.tau)
        d = rr.uniform(128, 168)
        x, y = math.cos(a) * d, math.sin(a) * d
        r = rr.uniform(5, 9)
        sphere("M_Foliage", (x, y, r * 0.55), r, jitter(LEAF_DARK, 0.15, rr), nu=9, nv=5, sz=0.75, s=4.0)
    with DETAIL():
        for i in range(120):
            a = rr.uniform(0, math.tau)
            d = rr.uniform(118, 175)
            x, y = math.cos(a) * d, math.sin(a) * d
            r = rr.uniform(3.5, 6)
            sphere("M_Foliage", (x, y, r * 0.9 + rr.uniform(0, 4)), r, jitter(LEAF, 0.15, rr), nu=8, nv=5, sz=0.8, s=4.0)
    for (hx, hy, hr, hh) in ((-240, -220, 110, 26), (60, -300, 140, 30), (290, -60, 120, 22), (-300, 120, 130, 28), (180, 260, 110, 20)):
        sphere("M_Foliage", (hx, hy, -2), hr, jitter(LEAF_DARK, 0.08, rr), nu=18, nv=8, sz=hh / hr, s=8.0)


def build_now():
    rr = random.Random(2017)
    with GROUP("NOW_Lawn"):
        grid_floor("M_Grass", RX0, RX1, RY0, RY1, 0.0, GRASS_NOW, s=3.0, cell=4.0, vamt=0.06)
    # jogging path: a rounded loop round the old square + a branch to the south-west entrance
    a_, b_, p_ = 38.0, 19.0, 3.0
    W = 2.2
    with GROUP("NOW_Path"):
        pts = []
        n = 120
        for k in range(n):
            t = math.tau * k / n
            c, s = math.cos(t), math.sin(t)
            x = a_ * math.copysign(abs(c) ** (2 / p_), c)
            y = b_ * math.copysign(abs(s) ** (2 / p_), s)
            pts.append((x, y))
        path_strip(pts, W, closed=True)
        path_strip([(-30.0, -14.2), (-36.0, -24.0), (-44.0, -36.0), (-52.0, -47.0)], W, closed=False)
    with GROUP("NOW_Trees"):
        spots = [(-44, 34), (-22, 38), (4, 40), (28, 36), (52, 32), (-48, -8), (-50, 14), (48, -14), (50, 10), (-18, -30), (22, -30),
                 (-60, -30), (62, -30), (-66, 30), (68, 28), (0, 30)]
        for i, (x, y) in enumerate(spots):
            tree(x, y, 1.0 + rr.uniform(-0.1, 0.2), seed=300 + i, kind="rain" if i % 3 else "angsana", col_name="COL_NowTree")
        for i in range(24):      # younger trees along the path
            t = math.tau * (i + 0.5) / 24
            c, s = math.cos(t), math.sin(t)
            x = (a_ + 4.5) * math.copysign(abs(c) ** (2 / p_), c)
            y = (b_ + 4.5) * math.copysign(abs(s) ** (2 / p_), s)
            if (abs(x - 4) < 5 and y < -10) or math.hypot(x + 26, y + 26) < 16:
                continue
            tree(x, y, 0.55, seed=400 + i, kind="angsana", dense=False)
        for i, (x, y) in enumerate(((1.5, -14.2), (6.6, -14.4), (-10, -15.5), (14, -15.4), (-26, 8), (26, -6))):
            shrub(x, y, 0.9, LEAF, seed=500 + i)
        # benches + slim modern lamp posts along the path
        for i, (x, y, fd) in enumerate(((-8.0, -21.4, NORTH), (12.0, -21.4, NORTH), (-20, 21.4, SOUTH), (20, 21.4, SOUTH), (41.4, 0.0, WEST), (-41.4, 0.0, EAST))):
            park_bench(x, y, fd)
            collider("COL_NowBench", (x - 0.9, y - 0.45, 0), (x + 0.9, y + 0.45, 0.8), unique=False)
        for i in range(12):
            t = math.tau * i / 12
            c, s = math.cos(t), math.sin(t)
            x = (a_ + 1.7) * math.copysign(abs(c) ** (2 / p_), c)
            y = (b_ + 1.7) * math.copysign(abs(s) ** (2 / p_), s)
            if math.hypot(x + 26, y + 26) < 12:
                continue
            tube("M_Atlas", (x, y, 0), (x, y, 4.2), 0.05, 6, C(0.3, 0.33, 0.35))
            box("M_Atlas", (x - 0.2, y - 0.08, 4.2), (x + 0.2, y + 0.08, 4.3), C(0.3, 0.33, 0.35))
    with GROUP("NOW_Marker"):
        # the heritage marker: a low granite plinth with a sloped plate face towards the path (generic; no real text)
        mx, my = 4.0, -16.0
        abox((mx - 1.3, my - 1.1, 0), (mx + 1.3, my + 0.9, 0.04), C(0.80, 0.78, 0.74), skip=("-z",))
        abox((mx - 0.72, my - 0.42, 0.04), (mx + 0.72, my + 0.42, 0.14), C(0.7, 0.7, 0.7), cell="granite", skip=("-z",))
        yF, yB, zF, zB = my - 0.34, my + 0.34, 0.5, 1.02
        xa, xb = mx - 0.6, mx + 0.6
        g = C(0.62, 0.62, 0.62)
        face("M_Atlas", [(xa, yF, 0.14), (xb, yF, 0.14), (xb, yF, zF), (xa, yF, zF)], g, uv=cquad("granite", 0, 0, 1, 0.3))
        face("M_Atlas", [(xb, yB, 0.14), (xa, yB, 0.14), (xa, yB, zB), (xb, yB, zB)], g, uv=cquad("granite"))
        face("M_Atlas", [(xa, yF, zF), (xb, yF, zF), (xb, yB, zB), (xa, yB, zB)], mul(g, 0.8), uv=cquad("granite"))
        faceN("M_Atlas", [(xa, yB, 0.14), (xa, yF, 0.14), (xa, yF, zF), (xa, yB, zB)], g, (-1, 0, 0), uv=[cuv("granite", 0, 0), cuv("granite", 1, 0), cuv("granite", 1, 0.5), cuv("granite", 0, 1)])
        faceN("M_Atlas", [(xb, yF, 0.14), (xb, yB, 0.14), (xb, yB, zB), (xb, yF, zF)], g, (1, 0, 0), uv=[cuv("granite", 0, 0), cuv("granite", 1, 0), cuv("granite", 1, 1), cuv("granite", 0, 0.5)])
        collider("COL_Marker", (xa - 0.1, yF - 0.1, 0), (xb + 0.1, yB + 0.1, 1.1))
    # decal plate on the sloped face (0.9 x 0.6 m), 1.5 cm proud
    n = Vector((0, -(zB - zF), (yB - yF))).normalized()
    slope = Vector((0, yB - yF, zB - zF)).normalized()
    ctr = Vector((mx, (yF + yB) / 2, (zF + zB) / 2)) + n * 0.015
    with GROUP("DECAL_Marker"):
        c0 = ctr - slope * 0.3
        c1 = ctr + slope * 0.3
        quad("M_Decal", c0 + Vector((-0.45, 0, 0)), c0 + Vector((0.45, 0, 0)), c1 + Vector((0.45, 0, 0)), c1 + Vector((-0.45, 0, 0)))
    marker("SNAP_Marker", tuple(ctr + n * 0.35), tuple(-n), {"note": "above DECAL_Marker, looking at the plate"})
    with GROUP("NOW_Blocks"):
        hdb_now(-78.0, 70.0, 9, 13, C(0.95, 0.92, 0.84), 0.0)
        hdb_now(4.0, 66.0, 8, 11, C(0.88, 0.93, 0.95), 0.0)
        hdb_now(106.0, -34.0, 9, 14, C(0.94, 0.88, 0.84), math.pi / 2)
        hdb_now(-40.0, -76.0, 8, 12, C(0.9, 0.95, 0.88), math.pi)
        hdb_now(-106.0, 26.0, 8, 12, C(0.95, 0.9, 0.8), -math.pi / 2)


def path_strip(pts, W, closed=True, z=0.035, col=C(0.62, 0.36, 0.30)):
    n = len(pts)
    rng = range(n) if closed else range(n - 1)
    for k in rng:
        a, b = pts[k], pts[(k + 1) % n]
        pa = pts[k - 1] if (closed or k > 0) else a
        pb = pts[(k + 2) % n] if (closed or k + 2 < n) else b
        def perp(p, q):
            dx, dy = q[0] - p[0], q[1] - p[1]
            L = math.hypot(dx, dy) or 1
            return (-dy / L, dx / L)
        na, nb = perp(pa, b), perp(a, pb)
        h = W / 2
        q = [(a[0] - na[0] * h, a[1] - na[1] * h, z), (b[0] - nb[0] * h, b[1] - nb[1] * h, z),
             (b[0] + nb[0] * h, b[1] + nb[1] * h, z), (a[0] + na[0] * h, a[1] + na[1] * h, z)]
        faceN("M_Ground", q, jitter(col, 0.03), (0, 0, 1), s=3.0)
        for side in (-1, 1):   # tiny kerb faces so the edge reads
            e0 = (a[0] + na[0] * h * side, a[1] + na[1] * h * side)
            e1 = (b[0] + nb[0] * h * side, b[1] + nb[1] * h * side)
            faceN("M_Ground", [(e0[0], e0[1], 0), (e1[0], e1[1], 0), (e1[0], e1[1], z), (e0[0], e0[1], z)], mul(col, 0.8),
                  (na[0] * side, na[1] * side, 0), s=3.0)


def park_bench(x, y, fdir):
    rz = math.atan2(fdir[0], -fdir[1])
    with XF(M_at(x, y, 0, rz)):
        abox((-0.8, -0.2, 0.42), (0.8, 0.2, 0.46), TIMBER, cell="planks")
        abox((-0.8, 0.18, 0.55), (0.8, 0.22, 0.85), TIMBER, cell="planks")
        for sx in (-0.7, 0.7):
            abox((sx - 0.03, -0.2, 0), (sx + 0.03, 0.22, 0.42), C(0.25, 0.27, 0.28), skip=("-z",))


def hdb_now(x0, yf, npanel, storeys, tint, rz):
    """Present-day HDB slab: corridor elevation on the front (-y local), window elevation behind."""
    W, H, D = 6.4, 2.8, 12.0
    L = npanel * W
    ztop = 3.2 + storeys * H
    M = Matrix.Translation((x0, yf, 0)) @ Matrix.Rotation(rz, 4, "Z")
    with XF(M):
        for i in range(npanel):
            xa, xb = i * W, (i + 1) * W
            for k in range(storeys):
                z = 3.2 + k * H
                face("M_Atlas", [(xa, 0, z), (xb, 0, z), (xb, 0, z + H), (xa, 0, z + H)], tint, uv=cquad("hdb", 0, 0.5, 1, 1))
                face("M_Atlas", [(xb, D, z), (xa, D, z), (xa, D, z + H), (xb, D, z + H)], tint, uv=cquad("hdb", 0, 0, 1, 0.5))
            # void deck
            face("M_Atlas", [(xa, 0.8, 0), (xb, 0.8, 0), (xb, 0.8, 3.2), (xa, 0.8, 3.2)], mul(tint, 0.45))
            box("M_Atlas", (xa - 0.25, -0.1, 0), (xa + 0.25, 0.4, 3.2), tint, skip=("-z", "+z"))
        box("M_Atlas", (-0.3, -0.2, 0), (0, D + 0.2, ztop + 1.0), tint, skip=("-z",))
        box("M_Atlas", (L, -0.2, 0), (L + 0.3, D + 0.2, ztop + 1.0), tint, skip=("-z",))
        box("M_Atlas", (0, 0, ztop), (L, D, ztop + 1.0), mul(tint, 0.95), skip=("-z",))
        # roof "hat" (a pitched feature typical of later HDB blocks)
        for (ya, yb) in ((-0.4, D / 2), (D + 0.4, D / 2)):
            faceN("M_Atlas", [(-0.4, ya, ztop + 1.0), (L + 0.4, ya, ztop + 1.0), (L + 0.4, yb, ztop + 3.0), (-0.4, yb, ztop + 3.0)],
                  C(0.72, 0.36, 0.28), (0, ya - yb, 1))


def parade_markers(A, st, seats):
    # --- stair (three.js values as in ns-fallback.js; heights from the geometry)
    zL = st["zL"]
    marker3("SPAWN_Sparky", (22.0, 0.0, -26.2), math.pi)
    marker3("STAIR_Bottom", (22.0, 0.0, -28.4), math.pi)
    marker3("STAIR_Landing", (22.0, zL, -31.2), math.pi, {"note": "half landing (first landing), top of the 9-step flight"})
    marker3("STAIR_Top", (22.0, zL, -31.6), math.pi, {"note": "first landing; the built flight continues east to the first floor"})
    marker3("BED_Start", (22.0, 0.45, -27.4), math.pi, {"note": "carried bed centre at the stair foot; facing = up the stair"})
    marker3("BED_Landing", (22.0, zL + 0.45, -31.0), math.pi)
    marker3("NPC_Osman_Stair", (19.6, 0.0, -26.4), math.pi / 2)
    # Leo halfway up flight A, on tread 5, walking down
    i = 5
    zc = -(st["yA0"] + (i - 0.5) * TREAD_A)
    marker3("NPC_Leo_Stair", (22.2, i * RISE, zc), 0.0)
    marker3("NPC_Ravi_Stair", (24.4, 0.0, -25.8), math.pi, {"note": "arriving at the stair with his cupboard"})
    marker3("NPC_Farid_Landing", (21.55, zL, -32.5), 0.0)
    # --- day-one drill line, sergeant, advisers
    for k, x in enumerate((-2, -1, 0, 1, 2)):
        marker3(f"DRILL_{k + 1}", (x, 0.0, 0.0), math.pi, {"who": ["Leo", "Farid", "Sparky", "AhHock", "Ravi"][k]})
    marker3("NPC_Osman_Drill", (0.0, 0.0, -4.0), 0.0)
    marker3("NPC_Adviser_1", (-14.0, 0.0, -6.0), math.pi / 2)
    marker3("NPC_Adviser_2", (-15.0, 0.0, -4.6), math.pi / 2)
    marker3("SNAP_Mexicans", (-14.5, 1.6, -5.3), -math.pi / 2)
    # --- passing out
    for k, x in enumerate((-14, -13, -12, -11, -10)):
        marker3(f"PARADE_{k + 1}", (x, 0.0, 12.0), math.pi)
    marker3("PARADE_Halt", (22.0, 0.0, 12.0), math.pi / 2)
    marker3("NPC_Minister", (8.0, DAIS[4], 24.0), math.pi)
    marker3("STAND_X", (12.0, 0.0, 19.5), math.pi, {"note": "Boon's spot (Ravi's X), in front of the east stand"})
    # seats: 8 on each stand, rows 0-2, spread out (feet on the row platform, seat 0.45 behind)
    pick = []
    for si in (1, 0):
        s = [q for q in seats if q[0] == si and q[1] <= 2]
        step = max(1, len(s) // 8)
        pick += s[::step][:8]
    for k, (si, r, x, y, h) in enumerate(pick[:16]):
        marker(f"STAND_Seat_{k + 1}", (x, y, h), NORTH, {"seat_height": 0.45, "seat_centre_offset": 0.2, "stand": ["west", "east"][si], "row": r})
    stand_npc = {"Siti": (13.6, 20.6), "Rajan": (14.6, 20.6), "Rohani": (16.0, 21.0), "AhPek": (17.0, 21.0),
                 "Letchumi": (0.6, 21.0), "Neighbour": (1.6, 21.0), "AhMa": (2.8, 21.0)}
    for k, (x, z) in stand_npc.items():
        marker3(f"NPC_{k}_Stand", (x, 0.0, z), math.pi, {"note": "standing in front of the stands"})
    # --- cameras (positions as in ns-fallback.js; facings aim at what they frame)
    marker3("CAM_Title", (-26.0, 6.0, 26.0), look=(0.0, 3.5, -30.0))
    marker3("CAM_DrillDay", (-3.6, 2.3, 4.6), look=(0.0, 0.7, -1.2))
    marker3("CAM_Parade", (-8.0, 1.8, 5.0), look=(-12.0, 0.9, 12.0))
    marker3("THEN_NOW_Camera", (-26.0, 1.45, 26.0), look=(8.0, 1.2, -8.0))
    marker3("SNAP_Stair", (22.0, 1.6, -27.0), math.pi)


def build_parade():
    with AREA("Parade"):
        build_parade_ground()
        A, st = build_blocks()
        build_stair_dressing(A, st)
        build_prop_bed()
        build_dais()
        seats = build_stands()
        build_edge()
        build_parade_static()
        build_now()
        parade_markers(A, st, seats)


# ======================================================================================
# AREA_Barracks — a barrack floor at night (x = 200)
# ======================================================================================
BX0, BX1 = 190.0, 210.0
ROOMS = [191.0, 197.0, 203.0, 209.0]      # partition lines (three x)
YP = -0.25        # parapet line (three z 0.25)
YFW = 1.8         # room front wall (three z -1.8..-1.95)
YBW = 6.05        # room back wall inner face (three z -6.05)
ZC = 2.82


def build_barracks():
    with AREA("Barracks"):
        rr = random.Random(68)
        base = -(3 * STOREY)        # this is the fourth floor ("four floors later")
        # floor: corridor (cement) + rooms (terrazzo-ish)
        grid_floor("M_Ground", BX0, BX1, YP, YFW, 0.0, C(0.74, 0.72, 0.68), s=2.0, cell=1.0)
        for i in range(3):
            grid_floor("M_Ground", ROOMS[i] + 0.075, ROOMS[i + 1] - 0.075, YFW + 0.15, YBW, 0.0, C(0.80, 0.77, 0.70), s=1.5, cell=0.75)
        # corridor ceiling, room ceilings
        grid_floor("M_Plaster", BX0, BX1, YP, YFW, ZC, CEIL, s=2.0, cell=2.0, down=True)
        grid_floor("M_Plaster", ROOMS[0], ROOMS[3], YFW, YBW, ZC, CEIL, s=2.0, cell=1.5, down=True)
        # parapet with columns; slab bands above and below (the floors above/below seen over the parapet)
        box("M_Plaster", (BX0, YP - 0.15, base), (BX1, YP, 1.0), CREAM, s=2.0, skip=("-z",))
        box("M_Plaster", (BX0, YP - 0.15, ZC), (BX1, YP, ZC + 0.45), JADE, s=2.0, skip=("+y",))
        box("M_Plaster", (BX0, YP - 0.15, ZC + 0.45), (BX1, YP, ZC + 1.3), CREAM, s=2.0, skip=("-z",))
        for x in (BX0, 196.6, 203.4, BX1):
            box("M_Plaster", (x - 0.16, YP - 0.2, base), (x + 0.16, YP + 0.14, ZC + 1.3), OFFWHITE, s=2.0, skip=("-z", "+z"))
            collider("COL_Bar_Column", (x - 0.16, YP - 0.2, 0), (x + 0.16, YP + 0.14, 3), unique=False)
        collider("COL_Bar_Parapet", (BX0, YP - 0.3, 0), (BX1, YP, 3))
        # corridor ends: west wall (fire buckets), east wall with a breeze-block screen
        box("M_Plaster", (BX0 - 0.25, YP - 0.15, 0), (BX0, YBW + 0.2, ZC + 0.2), CREAM, s=2.0)
        box("M_Plaster", (BX1, YP - 0.15, 0), (BX1 + 0.25, YBW + 0.2, ZC + 0.2), CREAM, s=2.0)
        tiled((BX1 - 0.012, YFW - 0.2, 0.9), (0, -1, 0), (0, 0, 1), YFW - YP - 0.4, 1.6, "breeze", mul(WHITE, 0.7))
        for i in range(3):
            cyl("M_Atlas", (BX0 + 0.25, 0.4 + i * 0.4, 1.0), 0.13, 0.28, 8, RED, r_top=0.15)
        box("M_Atlas", (BX0, 0.15, 1.3), (BX0 + 0.05, 1.45, 1.35), RED)
        wall_x("M_Atlas", 0.3, 1.2, 1.5, 2.3, BX0 + 0.012, WHITE, facing="+x", cell="notice")
        collider("COL_Bar_EndW", (BX0 - 0.3, YP, 0), (BX0, YBW, 3))
        collider("COL_Bar_EndE", (BX1, YP, 0), (BX1 + 0.3, YBW, 3))
        # room front wall with doorways and louvred windows (per room: door x+0.3..1.2, window x+3.0..4.5)
        yw0, yw1 = YFW, YFW + 0.15
        segs = []
        cur = BX0
        for i in range(3):
            xr = ROOMS[i]
            d0, d1 = xr + 0.3, xr + 1.2
            w0, w1 = xr + 3.0, xr + 4.5
            segs.append((cur, d0, 0, ZC))
            segs.append((d0, d1, 2.1, ZC))
            segs.append((d1, w0, 0, ZC))
            segs.append((w0, w1, 0, 1.0))
            segs.append((w0, w1, 2.15, ZC))
            cur = w1
            # louvres in the window (both faces; dark night glass) + a door leaf swung open into the room
            wall_y("M_Atlas", w0, w1, 1.0, 2.15, (yw0 + yw1) / 2, mul(WHITE, 0.62), cell="louvre_glass")
            wall_y("M_Atlas", w0, w1, 1.0, 2.15, (yw0 + yw1) / 2, mul(WHITE, 0.45), facing="+y", cell="louvre_glass")
            mbox(M_at(d0 + 0.02, yw1 + 0.45, 1.05, 0), "M_Atlas", (0.04, 0.9, 2.08), rr.choice(DOORS), cells={"+x": "door_flat", "-x": "door_flat"})
            # dark door-frame reveal
            box("M_Atlas", (d0 - 0.05, yw0 - 0.01, 0), (d0, yw1 + 0.01, 2.15), TIMBER_DARK, skip=("-z",))
            box("M_Atlas", (d1, yw0 - 0.01, 0), (d1 + 0.05, yw1 + 0.01, 2.15), TIMBER_DARK, skip=("-z",))
            box("M_Atlas", (d0 - 0.05, yw0 - 0.01, 2.1), (d1 + 0.05, yw1 + 0.01, 2.15), TIMBER_DARK)
        segs.append((cur, BX1, 0, ZC))
        for (a, b, z0, z1) in segs:
            box("M_Plaster", (a, yw0, z0), (b, yw1, z1), CREAM, s=2.0, skip=("+z",) if z1 >= ZC else (),
                cols={"-y": C(0.86, 0.9, 0.84)})
            if z0 == 0 and z1 >= ZC:
                collider("COL_Bar_Front", (a, yw0, 0), (b, yw1, 3), unique=False)
            if z1 == 1.0:
                collider("COL_Bar_Window", (a, yw0, 0), (b, yw1, 3), unique=False)
        # green dado on the corridor side
        box("M_Plaster", (BX0, yw0 - 0.01, 0), (BX1, yw0, 0.12), mul(JADE, 0.8), skip=("-z", "+y"))
        # partitions + back wall with two louvre windows per room
        for x in ROOMS[1:3]:
            box("M_Plaster", (x - 0.075, yw1, 0), (x + 0.075, YBW, ZC), OFFWHITE, s=2.0, skip=("+z",))
            collider("COL_Bar_Partition", (x - 0.075, yw1, 0), (x + 0.075, YBW, 3), unique=False)
        for i in range(3):
            xr = ROOMS[i]
            segs = [(xr, xr + 0.7, 0, ZC), (xr + 0.7, xr + 2.0, 0, 1.0), (xr + 0.7, xr + 2.0, 2.1, ZC), (xr + 2.0, xr + 4.0, 0, ZC),
                    (xr + 4.0, xr + 5.3, 0, 1.0), (xr + 4.0, xr + 5.3, 2.1, ZC), (xr + 5.3, xr + 6.0, 0, ZC)]
            for (a, b, z0, z1) in segs:
                box("M_Plaster", (a, YBW, z0), (b, YBW + 0.15, z1), OFFWHITE, s=2.0, skip=("+z", "+y"))
            for wx in (xr + 0.7, xr + 4.0):
                wall_y("M_Atlas", wx, wx + 1.3, 1.0, 2.1, YBW + 0.075, mul(WHITE, 0.5), facing="-y", cell="louvre_glass")
                wall_y("M_Plaster", wx, wx + 1.3, 1.0, 2.1, YBW + 0.2, C(0.02, 0.025, 0.04), facing="-y")
            box("M_Plaster", (xr, YBW, 0), (xr + 6.0, YBW + 0.01, 0.12), mul(JADE, 0.8), skip=("-z", "+y"))
        collider("COL_Bar_Back", (ROOMS[0], YBW, 0), (ROOMS[3], YBW + 0.3, 3))
        collider("COL_Bar_RoomW", (ROOMS[0] - 0.3, yw1, 0), (ROOMS[0], YBW, 3))
        collider("COL_Bar_RoomE", (ROOMS[3], yw1, 0), (ROOMS[3] + 0.3, YBW, 3))
        box("M_Plaster", (ROOMS[0] - 0.15, yw1, 0), (ROOMS[0], YBW, ZC), OFFWHITE, s=2.0, skip=("-x", "+z"))
        box("M_Plaster", (ROOMS[3], yw1, 0), (ROOMS[3] + 0.15, YBW, ZC), OFFWHITE, s=2.0, skip=("+x", "+z"))
        # --- room furniture: three iron beds each (heads to the back wall), lockers, uniforms on hooks, a bulb
        BY = YBW - 0.1 - 0.95        # bed centre (Blender y)
        for i in range(3):
            xr = ROOMS[i]
            xm = xr + 3.0
            for j, bx in enumerate((xr + 1.0, xr + 3.0, xr + 5.0)):
                bunk = (i == 2 and j == 2)
                bxx = bx + (0.0 if not bunk else 0.0)
                bed_frame(Matrix.Translation((bxx, BY, 0)), mattress=True, blanket=True, col=BEDGREEN)
                if bunk:     # Leo's double-decker
                    for (px, py) in ((-0.4, 0.95), (0.4, 0.95), (-0.4, -0.95), (0.4, -0.95)):
                        tube("M_Atlas", (bxx + px, BY + py, 0.6), (bxx + px, BY + py, 1.95), 0.02, 5, BEDGREEN, smooth=False)
                    bed_frame(Matrix.Translation((bxx, BY, 1.0)), mattress=True, blanket=True, col=BEDGREEN, detail=False)
                    for k in range(4):     # ladder at the foot
                        tube("M_Atlas", (bxx - 0.3, BY - 0.96, 0.3 + k * 0.3), (bxx + 0.3, BY - 0.96, 0.3 + k * 0.3), 0.012, 4, BEDGREEN, smooth=False)
                collider("COL_Bar_Bed", (bxx - 0.42, BY - 0.97, 0), (bxx + 0.42, BY + 0.97, 1.0 if not bunk else 2.0), unique=False)
                with DETAIL():   # boots under the bed, a kit bag
                    for q in (-0.09, 0.09):
                        box("M_Atlas", (bxx + 0.1 + q - 0.05, BY - 0.9, 0), (bxx + 0.1 + q + 0.05, BY - 0.62, 0.14), C(0.06, 0.06, 0.06), skip=("-z",))
                    if (i + j) % 2:
                        cyl("M_Atlas", (bxx - 0.2, BY - 1.25, 0), 0.2, 0.55, 8, TEMASEK, r_top=0.14)
            # lockers against the side walls near the front
            for (lx, rz) in ((xr + 0.26, math.pi / 2), (xr + 6.0 - 0.26, -math.pi / 2)):
                mbox(M_at(lx, YFW + 0.95, 0.9, rz), "M_Atlas", (0.9, 0.48, 1.8), C(0.52, 0.60, 0.54), cells={"-y": "locker"})
                collider("COL_Bar_Locker", (lx - 0.25, YFW + 0.45, 0), (lx + 0.25, YFW + 1.45, 2), unique=False)
            # uniforms on hooks (hook rail on the east side wall)
            hx = xr + 6.0 - 0.09
            box("M_Atlas", (hx - 0.02, 3.35, 1.72), (hx + 0.03, 4.95, 1.78), TIMBER_DARK)
            for q in range(3):
                hy = 3.65 + q * 0.5
                shirt(hx - 0.07, hy, 1.72, rz=math.pi / 2)
            # the bulb: flex, enamel shade, bulb
            tube("M_Atlas", (xm, 3.9, ZC), (xm, 3.9, 2.42), 0.006, 3, IRON, smooth=False)
            cyl("M_Atlas", (xm, 3.9, 2.34), 0.2, 0.1, 10, C(0.25, 0.32, 0.28), r_top=0.05, caps=False)
            sphere("M_Emissive", (xm, 3.9, 2.3), 0.055, WARM, nu=8, nv=5)
            marker(f"LAMP_Bar_{i + 1}", (xm, 3.9, 2.28), None)
        # (A starched uniform "standing up on its own" used to stand here; in playtest it read as a headless man,
        #  so it's gone. The fact stays on the album's real-vs-imagined page. Marker kept for compatibility.)
        ux, uy = 198.8, 2.6
        # --- outside, four storeys down: the opposite block with a few lit windows, the ground, trees
        grid_floor("M_Ground", 160, 240, -48, YP - 0.2, base, C(0.30, 0.32, 0.27), s=4.0, cell=8.0)
        with XF(Matrix.Translation((222.0, -26.0, 0)) @ Matrix.Rotation(math.pi, 4, "Z")):
            slab_block(0.0, 12, 0.0, storeys=5, accent=JADE, base=base, detail=False, lit=0.28, seed=7, laundry=False)
        for i, x in enumerate((168, 178, 232, 238)):
            tree(x, -14 - (i % 2) * 5, 1.1, seed=600 + i, z0=base, dense=False)
        # markers
        marker3("BAR_Spawn", (192.0, 0.0, -0.9), math.pi / 2)
        by3 = -BY
        foot = -(BY - 0.95) + 0.35       # three z just in front of the bed foot
        marker3("BAR_Farid", (194.0, 0.0, foot), 0.0, {"seat_height": 0.46, "note": "sitting on the foot of his bed"})
        marker3("BAR_AhHock", (200.0, 0.0, foot), 0.0, {"seat_height": 0.46, "note": "sitting on the bed he carried"})
        marker3("BAR_Ravi", (206.0, 0.0, foot), 0.0, {"seat_height": 0.46, "lie_pos": [206.0, 0.53, round(by3, 3)], "note": "his bed (lie_pos = mattress centre)"})
        marker3("BAR_Leo", (208.0, 1.0, foot), 0.0, {"seat_height": 0.46, "note": "top bunk (marker raised so the Sit pose rests on the top mattress)"})
        marker3("BAR_Uniform", (ux, 0.0, -uy), 0.0)
        marker3("SNAP_Uniform", (ux, 1.0, -uy + 0.05), 0.0)
        marker3("CAM_Barracks", (190.7, 1.6, -0.8), look=(209.0, 1.1, -1.4))


def shirt(x, y, z, rz=0.0, col=TEMASEK):
    with XF(M_at(x, y, z, rz)):
        box("M_Atlas", (-0.22, -0.02, -0.62), (0.22, 0.03, -0.06), col)
        for sx in (-1, 1):
            box("M_Atlas", (sx * 0.22, -0.02, -0.56), (sx * 0.3, 0.03, -0.08), mul(col, 0.9))
        box("M_Atlas", (-0.1, -0.03, -0.08), (0.1, 0.035, -0.02), mul(col, 1.1))


def standing_uniform(x, y, col=TEMASEK):
    for sx in (-0.1, 0.1):
        cyl("M_Atlas", (x + sx, y, 0.05), 0.085, 0.78, 8, mul(col, 0.92), r_top=0.095)
        box("M_Atlas", (x + sx - 0.07, y - 0.13, 0), (x + sx + 0.07, y + 0.06, 0.1), C(0.07, 0.07, 0.07), skip=("-z",))   # boots
    box("M_Atlas", (x - 0.2, y - 0.1, 0.8), (x + 0.2, y + 0.1, 0.9), mul(col, 0.9))
    box("M_Atlas", (x - 0.22, y - 0.11, 0.9), (x + 0.22, y + 0.11, 1.34), col, skip=("-z",))
    for sx in (-1, 1):    # stiff sleeves
        tube("M_Atlas", (x + sx * 0.24, y, 1.3), (x + sx * 0.3, y, 0.92), 0.06, 6, mul(col, 0.95), caps=True)
    for sx in (-1, 1):    # chest pockets
        box("M_Atlas", (x + sx * 0.11 - 0.06, y - 0.115, 1.12), (x + sx * 0.11 + 0.06, y - 0.11, 1.24), mul(col, 0.85), skip=("+y",))
    box("M_Atlas", (x - 0.1, y - 0.1, 1.34), (x + 0.1, y + 0.08, 1.4), mul(col, 1.08))


# ======================================================================================
# AREA_Night — scrub and a stream at night (x = -200)
# ======================================================================================
NCX = -200.0


def stream_y(x):
    """Stream centreline (Blender y; three z = -y) across the north side of the clearing."""
    return 9.7 + 0.9 * math.sin((x - NCX) * 0.17) + 0.4 * math.sin((x - NCX) * 0.41 + 1.0)


def night_h(x, y):
    d = abs(y - stream_y(x))
    h = 0.05 * math.sin(x * 0.7) * math.sin(y * 0.55) + 0.04 * math.sin(x * 1.9 + y * 1.3)
    if d < 1.8:
        h -= 0.52 * (1 - (d / 1.8) ** 2)
    return h


def build_night():
    with AREA("Night"):
        rr = random.Random(1968)
        # ground: fine cells in the clearing, coarse outside; muddy banks where the ground dips
        def colfn(x, y):
            h = night_h(x, y)
            return None if h > -0.12 else h
        for (x0, x1, y0, y1, cell) in ((NCX - 14, NCX + 14, -14.0, 14.0, 1.0),):
            nx, ny = int(round((x1 - x0) / cell)), int(round((y1 - y0) / cell))
            for i in range(nx):
                for j in range(ny):
                    a, b = x0 + i * cell, x0 + (i + 1) * cell
                    c, d = y0 + j * cell, y0 + (j + 1) * cell
                    pts = [(a, c, night_h(a, c)), (b, c, night_h(b, c)), (b, d, night_h(b, d)), (a, d, night_h(a, d))]
                    hc = night_h((a + b) / 2, (c + d) / 2)
                    if hc < -0.1:
                        face("M_Ground", pts, vcols(pts, C(0.50, 0.42, 0.34), 0.06), s=2.0, smooth=True)
                    else:
                        face("M_Grass", pts, vcols(pts, C(0.66, 0.70, 0.52), 0.08), s=2.5, smooth=True)
        outer = 60.0
        cell = 4.0
        for i in range(int(2 * outer / cell)):
            for j in range(int(2 * outer / cell)):
                a, b = NCX - outer + i * cell, NCX - outer + (i + 1) * cell
                c, d = -outer + j * cell, -outer + (j + 1) * cell
                if NCX - 14 <= a and b <= NCX + 14 and -14 <= c and d <= 14:
                    continue
                pts = [(a, c, night_h(a, c)), (b, c, night_h(b, c)), (b, d, night_h(b, d)), (a, d, night_h(a, d))]
                face("M_Grass", pts, vcols(pts, C(0.56, 0.62, 0.46), 0.08), s=2.5, smooth=True)
        # the water: a strip following the stream, 0.26 m below the clearing
        xs = np.arange(NCX - outer, NCX + outer + 0.01, 1.0)
        for x0_, x1_ in zip(xs[:-1], xs[1:]):
            y0a, y0b = stream_y(x0_), stream_y(x1_)
            quad("M_Water", (x0_, y0a - 1.35, -0.26), (x1_, y0b - 1.35, -0.26), (x1_, y0b + 1.35, -0.26), (x0_, y0a + 1.35, -0.26),
                 C(0.30, 0.38, 0.42), uv=UV01)
        # rocks along the banks and in the stream
        for k in range(26):
            x = NCX + rr.uniform(-20, 20)
            y = stream_y(x) + rr.choice((-1, 1)) * rr.uniform(0.8, 1.9)
            sphere("M_Atlas", (x, y, night_h(x, y) - 0.05), rr.uniform(0.15, 0.4), jitter(C(0.55, 0.54, 0.5), 0.1, rr), nu=6, nv=4, sz=0.6)
        # the big tree the section crouches under
        tx, ty = NCX, 1.5
        tube("M_Atlas", (tx, ty, -0.2), (tx, ty, 3.6), 0.55, 9, BARK, cell="bark", r1=0.42)
        for k in range(5):
            a = k * math.tau / 5 + 0.3
            tube("M_Atlas", (tx, ty, 3.0), (tx + math.cos(a) * 3.8, ty + math.sin(a) * 3.8, 5.6), 0.22, 6, BARK, cell="bark", r1=0.1)
            tube("M_Atlas", (tx + math.cos(a) * 0.3, ty + math.sin(a) * 0.3, 0.25), (tx + math.cos(a) * 1.3, ty + math.sin(a) * 1.3, -0.1), 0.2, 5, BARK, cell="bark", r1=0.06)
        for k in range(14):
            a = rr.uniform(0, math.tau)
            r = rr.uniform(0.5, 5.5)
            sphere("M_Foliage", (tx + math.cos(a) * r, ty + math.sin(a) * r, 6.2 + rr.uniform(-0.4, 1.0)), rr.uniform(2.3, 3.2),
                   jitter(LEAF_DARK, 0.12, rr), nu=9, nv=5, sz=0.55, s=2.0)
        collider("COL_Night_Tree", (tx - 0.6, ty - 0.6, 0), (tx + 0.6, ty + 0.6, 4))
        # a fallen log on the south bank (the rest halt sits on it)
        ly = stream_y(NCX) - 2.55
        tube("M_Atlas", (NCX - 3.2, ly, night_h(NCX - 3.2, ly) + 0.22), (NCX + 3.0, ly - 0.1, night_h(NCX + 3.0, ly) + 0.2), 0.24, 8, BARK, cell="bark", caps=True, r1=0.2)
        collider("COL_Night_Log", (NCX - 3.3, ly - 0.35, 0), (NCX + 3.1, ly + 0.25, 0.45))
        # scrub ring: shrubs, a few trees, dense edge (and colliders so nobody walks into the dark)
        for k in range(46):
            a = k * math.tau / 46 + rr.uniform(-0.05, 0.05)
            d = rr.uniform(11.5, 14.0)
            x, y = NCX + math.cos(a) * d, math.sin(a) * d
            if abs(y - stream_y(x)) < 2.0:
                continue
            shrub(x, y, rr.uniform(1.0, 1.8), LEAF_DARK, z0=night_h(x, y), seed=700 + k, n=3)
        for k in range(18):
            a = rr.uniform(0, math.tau)
            d = rr.uniform(16, 30)
            x, y = NCX + math.cos(a) * d, math.sin(a) * d
            tree(x, y, rr.uniform(0.9, 1.3), seed=800 + k, kind=rr.choice(("rain", "angsana", "angsana")), z0=night_h(x, y), dense=False)
        for k in range(60):
            a = rr.uniform(0, math.tau)
            d = rr.uniform(30, 55)
            x, y = NCX + math.cos(a) * d, math.sin(a) * d
            r = rr.uniform(4, 7)
            sphere("M_Foliage", (x, y, r * 0.6), r, jitter(LEAF_DARK, 0.15, rr), nu=8, nv=5, sz=0.8, s=3.0)
        for k in range(7):
            x, y = NCX + rr.uniform(-9, 9), rr.uniform(-9, 5)
            if math.hypot(x - tx, y - ty) < 3.5 or abs(x - NCX) < 3 and y < -5:
                continue
            shrub(x, y, rr.uniform(0.6, 0.9), LEAF, z0=night_h(x, y), seed=900 + k, n=2)
            collider("COL_Night_Shrub", (x - 0.5, y - 0.5, 0), (x + 0.5, y + 0.5, 1.2), unique=False)
        # lalang (tall grass) clumps: single triangles, flat colour
        def lalang(x, y, n, hmax):
            z0 = night_h(x, y)
            for q in range(n):
                a = rr.uniform(0, math.tau)
                rx, ry = x + math.cos(a) * rr.uniform(0, 0.35), y + math.sin(a) * rr.uniform(0, 0.35)
                h = rr.uniform(0.5, hmax)
                lean = rr.uniform(0.1, 0.35)
                tx_, ty_ = rx + math.cos(a) * lean, ry + math.sin(a) * lean
                w = 0.03
                pa = (rx - math.sin(a) * w, ry + math.cos(a) * w, z0 - 0.02)
                pb = (rx + math.sin(a) * w, ry - math.cos(a) * w, z0 - 0.02)
                pt = (tx_, ty_, z0 + h)
                c = jitter(C(0.66, 0.68, 0.42), 0.12, rr)
                face("M_Atlas", [pa, pb, pt], c)
                face("M_Atlas", [pb, pa, pt], mul(c, 0.8))
        for k in range(40):
            x, y = NCX + rr.uniform(-12, 12), rr.uniform(-12, 7.5)
            if math.hypot(x - tx, y - ty) < 2.5 or (abs(x - NCX) < 2.5 and -12 < y < -3) or abs(y - stream_y(x)) < 2.2:
                continue
            lalang(x, y, 12, 1.1)
        with DETAIL():
            for k in range(70):
                x, y = NCX + rr.uniform(-13, 13), rr.uniform(-13, 13)
                if math.hypot(x - tx, y - ty) < 2.5 or (abs(x - NCX) < 2.5 and -12 < y < -3) or abs(y - stream_y(x)) < 1.4:
                    continue
                lalang(x, y, 14, 1.3)
        for (a, b) in (((NCX - 13.5, -14), (NCX - 12.5, 14)), ((NCX + 12.5, -14), (NCX + 13.5, 14)), ((NCX - 13.5, -14), (NCX + 13.5, -13)), ((NCX - 13.5, 13), (NCX + 13.5, 14))):
            collider("COL_Night_Edge", (a[0], a[1], 0), (b[0], b[1], 3), unique=False)
        # markers (three.js; the stream is at z ≈ -9.7)
        sy = stream_y(NCX)
        marker3("NIGHT_Spawn", (-200.0, night_h(NCX, -4.5), 4.5), math.pi)
        for k, x in enumerate((-2, -1, 0, 1, 2)):
            zz = 0.6 + abs(x) * 0.3
            marker3(f"NIGHT_Group_{k + 1}", (NCX + x * 0.9, night_h(NCX + x * 0.9, -zz), zz), math.pi, {"pose": "crouch", "note": "under the big tree"})
        marker3("NIGHT_Stream", (-200.0, night_h(NCX, sy - 1.9), -(sy - 1.9)), math.pi, {"note": "the stream's south bank"})
        for k, x in enumerate((-2, -1, 0, 1, 2)):
            y = ly + 0.5
            marker3(f"NIGHT_Rest_{k + 1}", (NCX + x * 1.0, night_h(NCX + x * 1.0, y), -y), math.pi,
                    {"seat_height": 0.44, "note": "sitting on the log, facing the stream"})
        marker3("CAM_Night", (-203.5, 1.7, 5.0), look=(-200.0, 1.0, -2.0))


# ======================================================================================
# AREA_CC — community-centre send-off, Queenstown, 1967 (three z = 200)
# ======================================================================================
def build_cc():
    with AREA("CC"):
        rr = random.Random(903)
        # (Blender y = -three z) building front at three z 193.5, fence/gate at 197, road from 203.6
        YBF, YBB = -193.5, -185.0       # building front / back
        YGATE = -197.0
        YKERB = -203.6
        YROAD1 = -210.0
        # ground
        def gtype(x, y):
            if YKERB >= y > YROAD1 and -70 < x < 70:
                return "road"
            if -16 <= x <= 16 and YGATE <= y <= YBF:
                return "forecourt"
            if YGATE > y > YKERB and -40 < x < 40:
                return "verge"
            return "grass"
        for (x0, x1, y0, y1, cell) in ((-40.0, 40.0, -214.0, -182.0, 2.0),):
            nx, ny = int(round((x1 - x0) / cell)), int(round((y1 - y0) / cell))
            for i in range(nx):
                for j in range(ny):
                    a, b = x0 + i * cell, x0 + (i + 1) * cell
                    c, d = y0 + j * cell, y0 + (j + 1) * cell
                    t = gtype((a + b) / 2, (c + d) / 2)
                    pts = [(a, c, 0), (b, c, 0), (b, d, 0), (a, d, 0)]
                    if t == "road":
                        face("M_Ground", pts, vcols(pts, C(0.46, 0.45, 0.43), 0.03), s=4.0)
                    elif t == "forecourt":
                        face("M_Ground", pts, vcols(pts, C(0.84, 0.80, 0.72), 0.04), s=3.0)
                    elif t == "verge":
                        face("M_Ground", pts, vcols(pts, LATERITE, 0.06), s=3.0) if abs((a + b) / 2) < 7 else face("M_Grass", pts, vcols(pts, GRASS_THEN, 0.07), s=3.0)
                    else:
                        face("M_Grass", pts, vcols(pts, GRASS_THEN, 0.07), s=3.0)
        for (x0, x1, y0, y1) in ((-160, 160, -182, -60), (-160, 160, -330, -214), (-160, -40, -214, -182), (40, 160, -214, -182)):
            grid_floor("M_Grass", x0, x1, y0, y1, 0.0, GRASS_OUT, s=3.0, cell=20.0)
        # road: kerbs, centre line, a monsoon drain on the far side
        for yk in (YKERB, YROAD1):
            for xk in range(-70, 70, 20):
                box("M_Ground", (xk, yk - 0.15, 0), (xk + 20, yk + 0.15, 0.08), C(0.82, 0.8, 0.76), s=2.0, skip=("-z", "-x", "+x"))
        for x in np.arange(-66, 66, 4.0):
            box("M_Ground", (x, (YKERB + YROAD1) / 2 - 0.06, 0), (x + 2.0, (YKERB + YROAD1) / 2 + 0.06, 0.01), C(0.95, 0.94, 0.88), s=2.0, skip=("-z", "-x", "+x", "-y", "+y"))
        for xk in range(-70, 70, 20):
            xl = xk + 20
            face("M_Ground", [(xk, YROAD1 - 1.4, -0.4), (xl, YROAD1 - 1.4, -0.4), (xl, YROAD1 - 0.6, -0.4), (xk, YROAD1 - 0.6, -0.4)], C(0.3, 0.3, 0.28), s=2.0)
            for yy, nrm in ((YROAD1 - 0.6, -1), (YROAD1 - 1.4, 1)):
                faceN("M_Ground", [(xk, yy, -0.4), (xl, yy, -0.4), (xl, yy, 0), (xk, yy, 0)], C(0.55, 0.55, 0.52), (0, nrm, 0), s=2.0)
        # --- the community centre: single storey, flat roof with a deep canopy, breeze blocks, steel casements
        X0, X1 = -14.0, 14.0
        ZF, ZW, ZR = 0.3, 3.6, 3.85
        box("M_Plaster", (X0 - 0.3, YBF - 1.6, 0), (X1 + 0.3, YBB, ZF), C(0.8, 0.78, 0.72), s=2.0, skip=("-z",))     # plinth + verandah
        grid_floor("M_Ground", X0 - 0.3, X1 + 0.3, YBF - 1.6, YBF, ZF + 0.002, C(0.86, 0.8, 0.72), s=1.5, cell=1.0)
        for k in range(2):     # two steps up to the verandah
            box("M_Plaster", (-3.0, YBF - 1.6 - 0.3 * (k + 1), 0), (3.0, YBF - 1.6 - 0.3 * k, ZF * (2 - k) / 3), C(0.8, 0.78, 0.72), s=2.0, skip=("-z",))
        # walls
        box("M_Plaster", (X0, YBF, ZF), (X1, YBB, ZW), CREAM, s=2.0, skip=("-z", "+z", "-y"))
        dado = C(0.62, 0.76, 0.66)
        bays = np.linspace(X0, X1, 9)
        for i in range(8):
            xa, xb = bays[i], bays[i + 1]
            if i in (3, 4):      # the entrance bays
                continue
            wall_y("M_Plaster", xa, xb, ZF, ZF + 0.9, YBF, dado, s=2.0)
            wall_y("M_Plaster", xa, xb, ZF + 0.9, ZW, YBF, CREAM, s=2.0)
            if i in (1, 6):
                tiled((xa + 0.2, YBF - 0.012, ZF + 0.2), (1, 0, 0), (0, 0, 1), xb - xa - 0.4, ZW - 0.5 - ZF, "breeze", WHITE)
            else:
                wall_y("M_Atlas", xa + 0.3, xb - 0.3, ZF + 1.0, ZW - 0.4, YBF - 0.012, WHITE, cell="casement")
        # entrance: portico with a taller fascia (the sign), an open doorway with a dark lobby
        ex0, ex1 = bays[3], bays[5]
        wall_y("M_Plaster", ex0, ex1, ZF + 2.6, ZW, YBF, CREAM, s=2.0)
        for (a, b) in ((ex0, -1.4), (1.4, ex1)):
            wall_y("M_Plaster", a, b, ZF, ZF + 2.6, YBF, CREAM, s=2.0)
        box("M_Plaster", (-1.4, YBF, ZF), (1.4, YBF + 2.2, ZF + 2.6), C(0.14, 0.13, 0.12), s=2.0, skip=("-y", "-z"))
        for sx in (-1, 1):   # open door leaves
            mbox(M_at(sx * 1.35, YBF + 0.45, ZF + 1.2, 0), "M_Atlas", (0.05, 0.9, 2.4), C(0.62, 0.44, 0.3), cells={"+x": "door_panel", "-x": "door_panel"})
        wall_y("M_Atlas", 2.0, 3.0, ZF + 1.0, ZF + 2.1, YBF - 0.012, WHITE, cell="notice")
        # roof slab + canopy on slim columns, a raised fascia over the entrance for the sign
        box("M_Plaster", (X0 - 0.5, YBF - 2.1, ZW), (X1 + 0.5, YBB + 0.4, ZR), OFFWHITE, s=2.0)
        box("M_Plaster", (X0 - 0.5, YBF - 2.15, ZW - 0.25), (X1 + 0.5, YBF - 2.05, ZR + 0.05), C(0.6, 0.74, 0.68), s=2.0, skip=("+y",))
        for x in np.linspace(X0 + 0.2, X1 - 0.2, 7):
            if abs(x) < 3.2:
                continue
            cyl("M_Atlas", (x, YBF - 1.85, ZF), 0.09, ZW - ZF, 8, OFFWHITE, caps=False)
        box("M_Plaster", (-3.4, YBF - 2.2, ZR), (3.4, YBF - 1.6, ZR + 1.1), OFFWHITE, s=2.0)
        for x in (-3.0, 3.0):
            box("M_Plaster", (x - 0.2, YBF - 2.1, 0), (x + 0.2, YBF - 1.7, ZW), OFFWHITE, s=2.0, skip=("-z",))
        with GROUP("DECAL_CCSign"):
            quad("M_Decal", (-2.5, YBF - 2.21, ZR + 0.12), (2.5, YBF - 2.21, ZR + 0.12), (2.5, YBF - 2.21, ZR + 1.0), (-2.5, YBF - 2.21, ZR + 1.0))
        collider("COL_CC_Building", (X0 - 0.3, YBF, 0), (X1 + 0.3, YBB, 4))
        collider("COL_CC_Verandah", (X0 - 0.3, YBF - 1.6, 0), (-3.0, YBF, 4))
        collider("COL_CC_Verandah2", (3.0, YBF - 1.6, 0), (X1 + 0.3, YBF, 4))
        # --- low fence with a gate (pillars, pipe rails on a dwarf wall), and its side returns
        for (a, b) in ((-16.0, -2.0), (2.0, 16.0)):
            box("M_Plaster", (a, YGATE - 0.1, 0), (b, YGATE + 0.1, 0.45), CREAM, s=2.0, skip=("-z",))
            for zz in (0.7, 0.95):
                tube("M_Atlas", (a, YGATE, zz), (b, YGATE, zz), 0.022, 5, C(0.35, 0.52, 0.46))
            for x in np.arange(a, b + 0.01, 1.75):
                box("M_Atlas", (x - 0.02, YGATE - 0.02, 0.45), (x + 0.02, YGATE + 0.02, 0.97), C(0.35, 0.52, 0.46))
            collider("COL_CC_Fence", (a, YGATE - 0.15, 0), (b, YGATE + 0.15, 1.2), unique=False)
        for x in (-16.0, 16.0):
            box("M_Plaster", (x - 0.1, YGATE, 0), (x + 0.1, YBF - 1.6, 0.9), CREAM, s=2.0, skip=("-z",))
            collider("COL_CC_FenceSide", (x - 0.15, YGATE, 0), (x + 0.15, YBF, 1.2), unique=False)
        for x in (-2.0, 2.0):
            box("M_Plaster", (x - 0.25, YGATE - 0.25, 0), (x + 0.25, YGATE + 0.25, 1.4), OFFWHITE, s=2.0, skip=("-z",))
            box("M_Plaster", (x - 0.3, YGATE - 0.3, 1.4), (x + 0.3, YGATE + 0.3, 1.5), C(0.62, 0.76, 0.66), s=2.0)
            collider("COL_CC_GatePost", (x - 0.25, YGATE - 0.25, 0), (x + 0.25, YGATE + 0.25, 1.5), unique=False)
        for sx in (-1, 1):     # gate leaves swung open inward
            gx = sx * 1.75
            with XF(M_at(gx, YGATE + 0.1, 0, 0)):
                for zz in (0.15, 0.95):
                    tube("M_Atlas", (0, 0, zz), (0, 1.5, zz), 0.02, 5, C(0.35, 0.52, 0.46))
                for yy in np.arange(0.0, 1.51, 0.15):
                    tube("M_Atlas", (0, yy, 0.12), (0, yy, 0.98), 0.01, 4, C(0.35, 0.52, 0.46), smooth=False)
        # --- banner between two poles inside the fence (runtime text)
        for x in (-7.2, -0.8):
            cyl("M_Atlas", (x, -196.2, 0), 0.05, 3.3, 8, OFFWHITE, caps=True)
            collider("COL_CC_BannerPole", (x - 0.1, -196.3, 0), (x + 0.1, -196.1, 3), unique=False)
        with GROUP("DECAL_Banner"):
            quad("M_Decal", (-7.0, -196.22, 2.1), (-1.0, -196.22, 2.1), (-1.0, -196.22, 3.1), (-7.0, -196.22, 3.1))
        box("M_Atlas", (-7.0, -196.18, 2.1), (-1.0, -196.14, 3.1), OFFWHITE)
        # the MP's gift table (white cloth)
        abox((-6.0, -198.8, 0), (-4.2, -198.1, 0.75), CANVAS_CREAM, cell="sheet", skip=("-z",))
        for k in range(5):
            box("M_Atlas", (-5.9 + k * 0.33, -198.6, 0.75), (-5.72 + k * 0.33, -198.42, 0.83), RED if k % 2 else C(0.9, 0.78, 0.4))
        collider("COL_CC_Table", (-6.1, -198.9, 0), (-4.1, -198.0, 0.9))
        # music stands for the small band
        for k in range(4):
            x = -8.0 + k * 1.0
            tube("M_Atlas", (x, -195.7, 0), (x, -195.7, 1.05), 0.012, 4, IRON, smooth=False)
            face("M_Atlas", [(x - 0.2, -195.72, 1.0), (x + 0.2, -195.72, 1.0), (x + 0.2, -195.6, 1.3), (x - 0.2, -195.6, 1.3)], IRON)
        # trees, lamp posts, a bus-stop pole
        for i, (x, y, k) in enumerate(((-12.5, -195.3, "angsana"), (12.5, -195.3, "angsana"), (-24, -200, "rain"), (26, -199, "rain"), (-30, -217, "rain"), (18, -218, "angsana"), (40, -215, "rain"))):
            tree(x, y, 0.95, seed=1000 + i, kind=k, col_name="COL_CC_Tree")
        for x in (-30, -10, 10, 30):
            tube("M_Atlas", (x, YROAD1 - 2.2, 0), (x, YROAD1 - 2.2, 6.5), 0.07, 6, C(0.55, 0.56, 0.55))
            tube("M_Atlas", (x, YROAD1 - 2.2, 6.4), (x, YROAD1 - 1.0, 6.7), 0.05, 5, C(0.55, 0.56, 0.55))
            box("M_Atlas", (x - 0.14, YROAD1 - 1.2, 6.55), (x + 0.14, YROAD1 - 0.6, 6.7), C(0.45, 0.46, 0.45))
        # 1960s Queenstown slab blocks behind the community centre and across the road
        slab_block(-50.0, 11, -172.0, storeys=7, accent=PALEBLUE, detail=True, seed=11)
        slab_block(8.0, 10, -168.0, storeys=7, accent=SALMON, detail=True, seed=12)
        with XF(Matrix.Translation((70.0, -236.0, 0)) @ Matrix.Rotation(math.pi, 4, "Z")):
            slab_block(0.0, 14, 0.0, storeys=7, accent=JADE, detail=False, seed=13)
        for k in range(12):
            tree(-60 + k * 11 + rr.uniform(-2, 2), -176 + rr.uniform(-2, 2), 0.9, seed=1100 + k, kind="rain", dense=False)
        # --- the lorry
        build_truck()
        # markers (three.js, as in ns-fallback.js)
        marker3("CC_Spawn", (-3.0, 0.0, 206.0), math.pi)
        marker3("CC_Truck_Tail", (3.4, 0.0, 205.4), math.pi / 2, {"note": "behind the tailboard, facing the lorry"})
        marker3("CC_Gate", (0.0, 0.0, 197.0), math.pi)
        marker3("CC_Boon_Spot", (-1.2, 0.0, 197.6), 0.0, {"note": "left empty"})
        for k, x in enumerate((-8, -7, -6, -5)):
            marker3(f"CC_Band_{k + 1}", (x, 0.0, 195.3), 0.0, {"note": "facing the gate and the road"})
        fam = [(-6.0, 199.6), (-4.4, 200.2), (-2.4, 199.4), (-0.4, 200.3), (1.6, 199.7), (-6.6, 201.4), (-5.0, 202.0), (-2.9, 201.6), (0.2, 201.5), (2.4, 201.0)]
        tail = (3.4, 205.4)
        for k, (x, z) in enumerate(fam):
            marker3(f"CC_Family_{k + 1}", (x, 0.0, z), math.atan2(tail[0] - x, tail[1] - z))
        cc = {"Rajan": (1.2, 201.2), "Ravi": (1.9, 201.8), "Siti": (-1.6, 202.2), "Farid": (-0.8, 202.9), "AhMa": (-8.2, 203.0),
              "Neighbour": (-3.2, 200.6), "MP": (-5.1, 197.7)}
        for k, (x, z) in cc.items():
            yaw = math.atan2(tail[0] - x, tail[1] - z)
            if k == "MP":
                yaw = 0.0
            if k == "AhMa":
                yaw = math.atan2(6.0, 2.0)
            marker3(f"NPC_{k}_CC", (x, 0.0, z), yaw)
        marker3("CAM_CC", (-8.0, 2.2, 211.0), look=(2.0, 1.4, 199.0))


def build_truck():
    """Canvas-topped 1960s British-style army three-tonner, tailboard down. Local: forward = -Y, ground z = 0."""
    with GROUP("PROP_Truck"):
        # wheels (single front, single rear on big tyres), axle beams
        for (wy, wr) in ((-2.35, 0.5), (1.6, 0.5)):
            for sx in (-1, 1):
                x0, x1 = sx * 0.78, sx * 1.1
                tube("M_Atlas", (x0, wy, wr), (x1, wy, wr), wr, 14, TYRE, cell="tyre", caps=True)
                tube("M_Atlas", (x1 + 0.001 * sx, wy, wr), (x1 + 0.02 * sx, wy, wr), 0.28, 10, ARMY_DARK, caps=True)
            box("M_Atlas", (-0.8, wy - 0.06, wr - 0.06), (0.8, wy + 0.06, wr + 0.06), ARMY_DARK)
        # chassis rails
        for sx in (-1, 1):
            box("M_Atlas", (sx * 0.42 - 0.07, -3.55, 0.62), (sx * 0.42 + 0.07, 3.6, 0.82), ARMY_DARK)
        # bonnet, grille, mudguards, headlamps, bumper
        box("M_Atlas", (-0.56, -3.42, 0.85), (0.56, -2.3, 1.62), ARMY, skip=("-z",))
        face("M_Atlas", [(-0.5, -3.425, 0.9), (0.5, -3.425, 0.9), (0.5, -3.425, 1.56), (-0.5, -3.425, 1.56)], mul(ARMY, 1.3), uv=cquad("grille"))
        for sx in (-1, 1):
            prof = [(-3.35, 0.95), (-3.1, 1.12), (-2.75, 1.2), (-2.2, 1.2), (-1.9, 1.05), (-1.8, 0.85)]
            for (ya, za), (yb, zb) in zip(prof[:-1], prof[1:]):
                pts = [(sx * 0.6, ya, za), (sx * 1.18, ya, za), (sx * 1.18, yb, zb), (sx * 0.6, yb, zb)]
                faceN("M_Atlas", pts, ARMY, (0, -(zb - za), (yb - ya)))
                faceN("M_Atlas", pts, ARMY_DARK, (0, (zb - za), -(yb - ya)))
            tube("M_Atlas", (sx * 0.86, -3.12, 1.3), (sx * 0.86, -3.3, 1.3), 0.11, 10, ARMY_DARK, caps=True)
            faceN("M_Atlas", [(sx * 0.86 + 0.09 * math.cos(math.tau * q / 10), -3.305, 1.3 + 0.09 * math.sin(math.tau * q / 10)) for q in range(10)], C(0.95, 0.93, 0.82), (0, -1, 0))
        box("M_Atlas", (-1.18, -3.62, 0.6), (1.18, -3.45, 0.82), ARMY_DARK)
        for sx in (-1, 1):
            box("M_Atlas", (sx * 0.7 - 0.18, -3.63, 0.63), (sx * 0.7 + 0.18, -3.625, 0.79), OFFWHITE, skip=("+y",))   # blank plates
        # cab
        cy0, cy1, cz0, cz1 = -2.3, -1.0, 0.95, 2.45
        box("M_Atlas", (-1.1, cy0, cz0), (1.1, cy1, 1.75), ARMY, skip=("-z",))
        box("M_Atlas", (-1.1, cy0 + 0.1, 1.75), (1.1, cy1, cz1), ARMY, skip=("-z", "-y"))
        face("M_Atlas", [(-1.05, cy0 + 0.1, 1.75), (1.05, cy0 + 0.1, 1.75), (1.05, cy0 + 0.1, 2.33), (-1.05, cy0 + 0.1, 2.33)], ARMY)
        for (xa, xb) in ((-1.0, -0.05), (0.05, 1.0)):    # split windscreen
            face("M_Atlas", [(xa, cy0 + 0.09, 1.8), (xb, cy0 + 0.09, 1.8), (xb, cy0 + 0.09, 2.3), (xa, cy0 + 0.09, 2.3)], GLASS_DARK, uv=cquad("casement", 0.05, 0.3, 0.3, 0.5))
        for sx in (-1, 1):
            faceN("M_Atlas", [(sx * 1.102, cy0 + 0.25, 1.82), (sx * 1.102, cy1 - 0.2, 1.82), (sx * 1.102, cy1 - 0.2, 2.3), (sx * 1.102, cy0 + 0.25, 2.3)], GLASS_DARK, (sx, 0, 0), uv=cquad("casement", 0.05, 0.3, 0.3, 0.5))
            faceN("M_Atlas", [(sx * 1.103, cy0 + 0.2, 1.0), (sx * 1.103, cy1 - 0.15, 1.0), (sx * 1.103, cy1 - 0.15, 1.02), (sx * 1.103, cy0 + 0.2, 1.02)], ARMY_DARK, (sx, 0, 0))
            tube("M_Atlas", (sx * 1.1, cy0 + 0.2, 2.1), (sx * 1.35, cy0 + 0.05, 2.1), 0.015, 4, IRON, smooth=False)
            box("M_Atlas", (sx * 1.35 - 0.02, cy0 - 0.02, 1.95), (sx * 1.35 + 0.02, cy0 + 0.12, 2.2), IRON)
            box("M_Atlas", (sx * 1.1, cy0 + 0.3, 0.72), (sx * 1.1 + sx * 0.02, cy0 + 0.75, 0.76), IRON)   # step
        box("M_Atlas", (-1.12, cy0 + 0.08, cz1), (1.12, cy1 + 0.02, cz1 + 0.05), ARMY_DARK)
        # spare wheel behind the cab
        tube("M_Atlas", (0.5, -0.95, 1.55), (0.5, -0.72, 1.55), 0.48, 12, TYRE, cell="tyre", caps=True)
        # cargo body: floor, drop sides, front bulkhead
        by0, by1 = -0.85, 3.6
        box("M_Atlas", (-1.2, by0, 1.05), (1.2, by1, 1.25), ARMY_DARK)
        for sx in (-1, 1):
            box("M_Atlas", (sx * 1.2 - 0.04, by0, 1.25), (sx * 1.2 + 0.04, by1, 1.78), ARMY, cells={"+x": "planks", "-x": "planks"}, cols={"+x": mul(ARMY, 1.2), "-x": mul(ARMY, 1.2)})
            for yy in np.linspace(by0 + 0.3, by1 - 0.3, 4):
                box("M_Atlas", (sx * 1.25 - 0.02, yy - 0.04, 1.2), (sx * 1.25 + 0.02, yy + 0.04, 1.8), ARMY_DARK)
        box("M_Atlas", (-1.2, by0 - 0.05, 1.25), (1.2, by0 + 0.03, 1.95), ARMY)
        # tailboard lowered flat on chains, a hook-on ladder to the road
        box("M_Atlas", (-1.18, by1, 1.18), (1.18, by1 + 0.5, 1.25), ARMY, cells={"+z": "planks"}, cols={"+z": mul(ARMY, 1.25)})
        for sx in (-1, 1):
            tube("M_Atlas", (sx * 1.15, by1 - 0.02, 1.76), (sx * 1.15, by1 + 0.48, 1.25), 0.012, 4, IRON, smooth=False)
            tube("M_Atlas", (sx * 0.3, by1 + 0.48, 1.2), (sx * 0.3, by1 + 0.85, 0.0), 0.02, 5, IRON, smooth=False)
        for k in range(3):
            zz = 0.3 + k * 0.32
            yy = by1 + 0.85 - (zz / 1.2) * 0.37
            tube("M_Atlas", (-0.3, yy, zz), (0.3, yy, zz), 0.016, 4, IRON, smooth=False)
        # canvas tilt over hoops; the back rolled up (open), dark inside
        prof = [(1.18, 1.78), (1.18, 2.65), (1.05, 2.9), (0.6, 3.05), (0.0, 3.1), (-0.6, 3.05), (-1.05, 2.9), (-1.18, 2.65), (-1.18, 1.78)]
        prof_xz = [(x, z) for (x, z) in prof]
        for (xa_, za), (xb_, zb) in zip(prof_xz[:-1], prof_xz[1:]):
            pts = [(xa_, by0, za), (xb_, by0, zb), (xb_, by1, zb), (xa_, by1, za)]
            mid = ((xa_ + xb_) / 2, (za + zb) / 2 - 2.3)
            outward = (mid[0], 0, mid[1])
            faceN("M_Atlas", pts, jitter(CANVAS_OLIVE, 0.03), outward, uv=cquad("canvas"))
            faceN("M_Atlas", pts, C(0.12, 0.13, 0.1), (-outward[0], 0, -outward[2]), uv=cquad("canvas"))
        front = [(x, by0 - 0.001, z) for (x, z) in prof]
        faceN("M_Atlas", front, jitter(CANVAS_OLIVE, 0.03), (0, -1, 0))
        faceN("M_Atlas", [(x, by0 + 0.03, z) for (x, z) in prof], C(0.12, 0.13, 0.1), (0, 1, 0))
        # hoops showing at the open back + the rolled flap
        for (xa_, za), (xb_, zb) in zip(prof[:-1], prof[1:]):
            tube("M_Atlas", (xa_, by1 - 0.05, za), (xb_, by1 - 0.05, zb), 0.02, 4, ARMY_DARK, smooth=False)
        tube("M_Atlas", (-1.0, by1 + 0.02, 2.95), (1.0, by1 + 0.02, 2.95), 0.12, 8, mul(CANVAS_OLIVE, 0.9), cell="canvas", caps=True)
        # benches inside for the recruits
        with DETAIL():
            for sx in (-1, 1):
                box("M_Atlas", (sx * 0.95 - 0.18, by0 + 0.2, 1.62), (sx * 0.95 + 0.18, by1 - 0.1, 1.67), TIMBER, cell="planks")
                for yy in np.linspace(by0 + 0.4, by1 - 0.4, 3):
                    box("M_Atlas", (sx * 0.95 - 0.02, yy - 0.02, 1.25), (sx * 0.95 + 0.02, yy + 0.02, 1.62), IRON)
            box("M_Atlas", (0.75, -0.7, 0.55), (1.05, 0.2, 0.9), ARMY_DARK)       # fuel tank
            for q in range(2):
                box("M_Atlas", (-1.1, -0.6 + q * 0.4, 0.55), (-0.95, -0.3 + q * 0.4, 0.95), ARMY_DARK)   # jerrycans
    pos = P3(7.05, 0.0, 205.4)
    OBJ_XF["PROP_Truck"] = Matrix.Translation(pos) @ Matrix.Rotation(math.pi / 2, 4, "Z")
    # the lorry's footprint collider (world space; code can disable COL_Truck if the lorry drives off)
    with GROUP("CC_Static"):
        collider("COL_Truck", (3.35 + 0.3, -206.65, 0), (10.75, -204.15, 3.2), {"prop": "PROP_Truck"})


# ======================================================================================
def build_level():
    build_parade()
    build_barracks()
    build_night()
    build_cc()


CONTRACT_NODES = (
    ["AREA_Parade", "AREA_Barracks", "AREA_Night", "AREA_CC", "THEN_Square", "THEN_Blocks", "THEN_BedPile", "PROP_Bed", "THEN_Dais",
     "THEN_Stands", "NOW_Lawn", "NOW_Path", "NOW_Marker", "DECAL_Marker", "NOW_Blocks", "NOW_Trees",
     "SPAWN_Sparky", "STAIR_Bottom", "STAIR_Landing", "STAIR_Top", "BED_Start", "BED_Landing", "NPC_Osman_Stair", "NPC_Leo_Stair",
     "NPC_Ravi_Stair", "NPC_Farid_Landing", "NPC_Osman_Drill", "NPC_Adviser_1", "NPC_Adviser_2", "SNAP_Mexicans", "PARADE_Halt",
     "STAND_X", "NPC_Minister", "NPC_Siti_Stand", "NPC_Rajan_Stand", "NPC_Rohani_Stand", "NPC_AhPek_Stand", "NPC_Letchumi_Stand",
     "NPC_Neighbour_Stand", "NPC_AhMa_Stand", "CAM_Title", "CAM_DrillDay", "CAM_Parade", "THEN_NOW_Camera", "SNAP_Marker",
     "BAR_Spawn", "BAR_Farid", "BAR_AhHock", "BAR_Ravi", "BAR_Leo", "BAR_Uniform", "SNAP_Uniform", "CAM_Barracks",
     "NIGHT_Spawn", "NIGHT_Stream", "CAM_Night",
     "DECAL_CCSign", "PROP_Truck", "DECAL_Banner", "CC_Spawn", "CC_Truck_Tail", "CC_Gate", "CC_Boon_Spot", "NPC_Rajan_CC", "NPC_Ravi_CC",
     "NPC_Siti_CC", "NPC_Farid_CC", "NPC_AhMa_CC", "NPC_Neighbour_CC", "NPC_MP_CC", "CAM_CC"]
    + [f"DRILL_{i}" for i in range(1, 6)] + [f"PARADE_{i}" for i in range(1, 6)] + [f"STAND_Seat_{i}" for i in range(1, 17)]
    + [f"LAMP_Bar_{i}" for i in range(1, 4)] + [f"NIGHT_Group_{i}" for i in range(1, 6)] + [f"NIGHT_Rest_{i}" for i in range(1, 6)]
    + [f"CC_Band_{i}" for i in range(1, 5)] + [f"CC_Family_{i}" for i in range(1, 11)]
)


# ======================================================================================
# Blender objects, materials
# ======================================================================================
MAT_DEF = {
    #  name           (dir, texture)             rough metal
    "M_Plaster": ((TEX_WW2, "plaster"), 0.92, 0.0),
    "M_Ground": ((TEX_CAMP, "ground"), 0.95, 0.0),
    "M_Grass": ((TEX_VD, "grass"), 0.96, 0.0),
    "M_Foliage": ((TEX_VD, "foliage"), 0.9, 0.0),
    "M_Atlas": ((TEX_CAMP, "atlas"), 0.72, 0.0),
    "M_Water": (None, 0.08, 0.0),
    "M_Emissive": (None, 0.5, 0.0),
    "M_Decal": (None, 0.7, 0.0),
}
IMAGES = {}
UV_WARN = {}
TILING = {"M_Plaster", "M_Ground", "M_Grass", "M_Foliage"}
UV_TILE = 32.0


def make_materials(res):
    mats = {}
    for name, (tex, rough, metal) in MAT_DEF.items():
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        m.use_backface_culling = True
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
            d, tn = tex
            img = bpy.data.images.load(os.path.join(d, str(res), tn + ".png"), check_existing=False)
            img.name = tn
            IMAGES[tn] = (img, d)
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
            bsdf.inputs["Emission Color"].default_value = (1.0, 0.8, 0.52, 1.0)
            bsdf.inputs["Emission Strength"].default_value = 3.0
        mats[name] = m
    return mats


def swap_textures(res):
    for tn, (img, d) in IMAGES.items():
        img.filepath = os.path.join(d, str(res), tn + ".png")
        img.reload()


def object_name(group, tier):
    return group if tier == "base" else group + "_" + tier


def make_mesh_object(name, mats_dict, mats, coll):
    verts, faces, uvs, cols, midx, sm = [], [], [], [], [], []
    slots = []
    weld = {}
    for mname in MATS:
        b = mats_dict.get(mname)
        if not b or not b.f:
            continue
        si = len(slots)
        slots.append(mname)
        remap = []
        for p in b.v:     # weld coincident positions (loop UVs / colours stay per corner; the exporter splits as needed)
            k = (round(p[0], 4), round(p[1], 4), round(p[2], 4))
            if k not in weld:
                weld[k] = len(verts)
                verts.append(p)
            remap.append(weld[k])
        tiling = mname in TILING
        for f, uv, c, s_ in zip(b.f, b.uv, b.col, b.sm):
            ff = [remap[i] for i in f]
            if len(set(ff)) < len(ff):
                continue
            faces.append(ff)
            if tiling:     # offsets in steps of 8 tiles so neighbouring faces keep identical UVs (and share vertices)
                du = math.floor(min(q[0] for q in uv) / 8.0) * 8.0
                dv = math.floor(min(q[1] for q in uv) / 8.0) * 8.0
                span = max(max(q[0] for q in uv) - du, max(q[1] for q in uv) - dv)
                if span > UV_TILE:
                    UV_WARN[name] = max(UV_WARN.get(name, 0), span)
                uv = [(min((q[0] - du) / UV_TILE, 1.0), min((q[1] - dv) / UV_TILE, 1.0)) for q in uv]
            uvs.extend(uv)
            cols.extend(c if isinstance(c, list) else [c] * len(f))
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
    roots = {}
    for a in AREAS:
        e = bpy.data.objects.new("AREA_" + a, None)
        e.empty_display_type = "PLAIN_AXES"
        coll.objects.link(e)
        roots[a] = e
    objs = {}
    for (group, tier), md in sorted(BUCKETS.items()):
        name = object_name(group, tier)
        ob = make_mesh_object(name, md, mats, coll)
        if ob:
            if group in OBJ_XF:
                ob.matrix_world = OBJ_XF[group]
            ob.parent = roots[GROUP_AREA[group]]
            objs[name] = ob
            ob["tier"] = tier
            ob["group"] = group
    cols = []
    for (name, (x0, y0, z0, x1, y1, z1), props, area) in COLLIDERS:
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
        ob.parent = roots[area]
        cols.append(ob)
    empties = []
    for (name, pos, fdir, props, area) in MARKERS:
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
        ob.parent = roots[area]
        empties.append(ob)
    return objs, cols, empties, roots


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
    sc.world.light_settings.distance = 2.4
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
    t0 = time.time()
    res = bpy.ops.object.bake(type="AO", target="VERTEX_COLORS")
    print("BAKE", res, len(objs), "objects", round(time.time() - t0, 1), "s")
    for ob in objs:
        me = ob.data
        n = len(me.loops)
        ao = np.empty(n * 4, dtype=np.float32)
        col = np.empty(n * 4, dtype=np.float32)
        me.color_attributes["AO"].data.foreach_get("color", ao)
        me.color_attributes["Col"].data.foreach_get("color", col)
        a = ao.reshape(-1, 4)[:, 0].astype(np.float64)
        # average the AO of corners that share a vertex and a face orientation (so the exporter can share them)
        lv = np.empty(n, dtype=np.int64)
        me.loops.foreach_get("vertex_index", lv)
        pn = np.empty(len(me.polygons) * 3, dtype=np.float32)
        me.polygons.foreach_get("normal", pn)
        ltot = np.empty(len(me.polygons), dtype=np.int32)
        me.polygons.foreach_get("loop_total", ltot)
        psm = np.empty(len(me.polygons), dtype=bool)
        me.polygons.foreach_get("use_smooth", psm)
        qn = np.round(pn.reshape(-1, 3) * 20).astype(np.int64)
        qn[psm] = 0
        ln = np.repeat(qn, ltot, axis=0)
        key = lv * 1000003 + (ln[:, 0] + 50) * 10201 + (ln[:, 1] + 50) * 101 + (ln[:, 2] + 50)
        _, inv = np.unique(key, return_inverse=True)
        sums = np.bincount(inv, weights=a)
        cnts = np.bincount(inv)
        a = (sums / cnts)[inv]
        k = 0.36 + 0.64 * np.clip(a, 0, 1) ** 0.85
        mi = np.empty(len(me.polygons), dtype=np.int32)
        me.polygons.foreach_get("material_index", mi)
        lt = np.empty(len(me.polygons), dtype=np.int32)
        me.polygons.foreach_get("loop_total", lt)
        loop_mat = np.repeat(mi, lt)
        names = [m.name for m in me.materials]
        for keep in ("M_Emissive", "M_Decal", "M_Water"):
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
            d.data.name = base
            objs[base] = d
            del objs[name]
            continue
        bpy.ops.object.select_all(action="DESELECT")
        objs[base].select_set(True)
        d.select_set(True)
        bpy.context.view_layer.objects.active = objs[base]
        bpy.ops.object.join()
        del objs[name]


def stats(objs):
    """(triangles, draw calls) per area for the given mesh objects."""
    out = {}
    for ob in objs:
        if ob.type != "MESH" or ob.name.startswith("COL_"):
            continue
        me = ob.data
        me.calc_loop_triangles()
        used = set(p.material_index for p in me.polygons)
        a = ob.parent.name if ob.parent else "?"
        t, d = out.get(a, (0, 0))
        out[a] = (t + len(me.loop_triangles), d + len(used))
    tot = (sum(v[0] for v in out.values()), sum(v[1] for v in out.values()))
    return tot, out


def to_three(p):
    return [round(p[0], 3), round(p[2], 3), round(-p[1], 3)]


def write_nodes_json(objs, cols, empties, extra):
    data = {"markers": {}, "colliders": {}, "meshes": {}}
    for e in empties:
        d = e.matrix_world.to_3x3() @ Vector((0, -1, 0))
        data["markers"][e.name] = {"three_pos": to_three(e.matrix_world.translation), "three_facing": to_three(d),
                                   "area": e.parent.name if e.parent else None,
                                   "props": {k: (v.to_list() if hasattr(v, "to_list") else v) for k, v in e.items()}}
    for c in cols:
        data["colliders"][c.name] = {"three_center": to_three(c.location), "aabb_min": list(c["aabb_min"]), "aabb_max": list(c["aabb_max"]),
                                     "area": c.parent.name if c.parent else None, "state": c.get("state")}
    for name, ob in objs.items():
        ob.data.calc_loop_triangles()
        data["meshes"][name] = {"tris": len(ob.data.loop_triangles), "materials": [m.name for m in ob.data.materials],
                                "area": ob.parent.name if ob.parent else None}
    data.update(extra)
    with open(NODES_JSON, "w") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)


def glb_node_names(path):
    with open(path, "rb") as f:
        f.read(12)
        ln, typ = struct.unpack("<II", f.read(8))
        js = json.loads(f.read(ln))
    return {n.get("name") for n in js.get("nodes", [])}, js


def check_contract(path):
    names, js = glb_node_names(path)
    missing = [n for n in CONTRACT_NODES if n not in names]
    print("CONTRACT", os.path.basename(path), "missing:", missing or "none", "| nodes", len(names), "| meshes", len(js.get("meshes", [])))
    assert not missing, missing


# ======================================================================================
# Previews
# ======================================================================================
def preview_world(day=True):
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
    nt = w.node_tree
    bg = nt.nodes.get("Background")
    if day:
        bg.inputs["Color"].default_value = (0.50, 0.62, 0.78, 1)
        bg.inputs["Strength"].default_value = 0.9
    else:
        bg.inputs["Color"].default_value = (0.03, 0.045, 0.09, 1)
        bg.inputs["Strength"].default_value = 1.0
    for n in ("PREVIEW_Sun", "PREVIEW_Moon"):
        ob = bpy.data.objects.get(n)
        if ob:
            ob.hide_render = True
    name = "PREVIEW_Sun" if day else "PREVIEW_Moon"
    ob = bpy.data.objects.get(name)
    if not ob:
        ld = bpy.data.lights.new(name, "SUN")
        ob = bpy.data.objects.new(name, ld)
        sc.collection.objects.link(ob)
        if day:
            ld.energy, ld.color = 3.6, (1.0, 0.94, 0.84)
            ob.rotation_euler = (math.radians(48), 0, math.radians(-35))
        else:
            ld.energy, ld.color = 0.35, (0.6, 0.7, 1.0)
            ob.rotation_euler = (math.radians(55), 0, math.radians(120))
    ob.hide_render = False
    sc.view_settings.exposure = 0.0 if day else 1.4


def point_light(name, loc, energy, color=(1.0, 0.8, 0.55), radius=0.05):
    ld = bpy.data.lights.new(name, "POINT")
    ld.energy, ld.color = energy, color
    ld.shadow_soft_size = radius
    ob = bpy.data.objects.new(name, ld)
    ob.location = loc
    bpy.context.scene.collection.objects.link(ob)
    return ob


def camera(name, loc, target, lens=22):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_start, cd.clip_end = 0.05, 900
    ob = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return ob


def set_view(objs, area, state):
    for n, ob in objs.items():
        a = ob.parent.name[5:] if ob.parent else ""
        vis = a == area
        if n.startswith("NOW_"):
            vis = vis and state == "now"
        elif n.startswith("THEN_"):
            vis = vis and state != "now"
        ob.hide_render = not vis


def previews(objs, empties):
    os.makedirs(PREV_DIR, exist_ok=True)
    mk = {e.name: e for e in empties}
    lamps = []
    for i in range(1, 4):
        lamps.append(point_light(f"PREV_Lamp{i}", mk[f"LAMP_Bar_{i}"].matrix_world.translation, 180))
    torch = point_light("PREV_Torch", P3(-199.2, 1.2, 0.2), 35, (1.0, 0.92, 0.78), 0.2)
    shots = [
        ("01_parade_hero", "Parade", "then", P3(-6, 1.7, 14), P3(8, 6, -34), 18),
        ("02_parade_title", "Parade", "then", P3(-26, 6, 26), P3(0, 3.5, -30), 20),
        ("03_stairwell", "Parade", "then", P3(17.0, 1.7, -21.0), P3(22.5, 1.4, -31.0), 18),
        ("04_stair_inside", "Parade", "then", P3(22.0, 1.25, -25.6), P3(22.2, 1.9, -33.0), 14),
        ("05_dais_stands", "Parade", "then", P3(6, 1.7, 6), P3(8, 1.6, 26), 18),
        ("06_drill_cam", "Parade", "then", P3(-3.6, 2.3, 4.6), P3(0, 0.7, -1.2), 20),
        ("07_thennow_then", "Parade", "then", P3(-26, 1.45, 26), P3(8, 1.2, -8), 20),
        ("08_thennow_now", "Parade", "now", P3(-26, 1.45, 26), P3(8, 1.2, -8), 20),
        ("09_marker", "Parade", "now", P3(3.2, 1.3, 18.8), P3(4, 0.7, 16), 22),
        ("10_parade_aerial", "Parade", "then", P3(-60, 45, 60), P3(0, 0, -10), 24),
        ("11_barracks_corridor", "Barracks", "then", P3(190.7, 1.6, -0.8), P3(209, 1.1, -1.4), 16),
        ("12_barracks_room", "Barracks", "then", P3(203.4, 1.6, -2.3), P3(207.5, 0.8, -5.5), 14),
        ("13_night", "Night", "then", P3(-203.5, 1.7, 5.0), P3(-200, 1.0, -2), 18),
        ("14_cc", "CC", "then", P3(-8, 2.2, 211), P3(2, 1.4, 199), 18),
        ("15_truck", "CC", "then", P3(0.5, 1.5, 208.5), P3(6.5, 1.4, 205.2), 18),
    ]
    only = [a for a in ARGS if a.startswith("--shot=")]
    for fname, area, state, loc, tgt, lens in shots:
        if only and not any(fname.startswith(o[7:]) for o in only):
            continue
        night = area in ("Barracks", "Night")
        preview_world(day=not night)
        for l in lamps:
            l.hide_render = area != "Barracks"
        torch.hide_render = area != "Night"
        set_view(objs, area, state)
        cam = camera("PREV_" + fname, loc, tgt, lens=lens)
        bpy.context.scene.camera = cam
        bpy.context.scene.render.filepath = os.path.join(PREV_DIR, fname + ".png")
        bpy.ops.render.render(write_still=True)
        print("render", fname)


# ======================================================================================
def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ensure_textures()
    build_level()
    mats = make_materials(1024)
    objs, cols, empties, roots = make_objects(mats)
    if DO_BAKE:
        runtime = ("DECAL_", "PROP_Truck")
        then_bake = [o for n, o in objs.items() if not n.startswith(runtime) and not n.startswith("NOW_")]
        bake_ao(then_bake, {n for n in objs if n.startswith("NOW_")})
        now_bake = [o for n, o in objs.items() if n.startswith("NOW_")]
        if now_bake:
            bake_ao(now_bake, {n for n in objs if n.startswith("THEN_")})
        bake_ao([objs["PROP_Truck"]] + [o for n, o in objs.items() if n.startswith("PROP_Truck_")], set())
    # mobile: base tier only, 512² textures
    swap_textures(512)
    mob = [o for n, o in objs.items() if not n.endswith("_detail")]
    st_m = stats(mob)
    export_glb(OUT_MOBILE, mob + cols + empties + list(roots.values()), q=74)
    meshopt(OUT_MOBILE)
    # desktop: detail merged, 1024² textures
    swap_textures(1024)
    join_detail(objs)
    st_d = stats(list(objs.values()))
    export_glb(OUT_DESKTOP, list(objs.values()) + cols + empties + list(roots.values()), q=80)
    meshopt(OUT_DESKTOP)
    check_contract(OUT_MOBILE)
    check_contract(OUT_DESKTOP)
    extra = {"tris": {"mobile": st_m[0][0], "desktop": st_d[0][0]}, "draw_calls": {"mobile": st_m[0][1], "desktop": st_d[0][1]},
             "per_area": {"mobile": st_m[1], "desktop": st_d[1]},
             "sizes_mb": {"mobile": round(os.path.getsize(OUT_MOBILE) / 1e6, 2), "desktop": round(os.path.getsize(OUT_DESKTOP) / 1e6, 2)},
             "areas": {"AREA_Parade": {"centre": [0, 0, -4], "walk_bounds": [-78, 78, -50, 42]},
                       "AREA_Barracks": {"centre": [200, 0, -2], "walk_bounds": [190.3, 209.7, -6.0, 0.1]},
                       "AREA_Night": {"centre": [-200, 0, -2], "walk_bounds": [-212.5, -187.5, -12.5, 12.5]},
                       "AREA_CC": {"centre": [0, 0, 200], "walk_bounds": [-30, 30, 186, 212]}}}
    write_nodes_json(objs, cols, empties, extra)
    print("TRIS mobile", st_m[0][0], "draws", st_m[0][1], "| desktop", st_d[0][0], "draws", st_d[0][1])
    print("PER AREA mobile", st_m[1])
    print("PER AREA desktop", st_d[1])
    print("objects", len(objs), "colliders", len(cols), "markers", len(empties))
    if UV_WARN:
        print("UV_WARN (tiling span > 32 tiles, clamped):", UV_WARN)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    if DO_PREVIEWS:
        previews(objs, empties)


main()
