"""
Procedural textures for the present-day Queenstown HDB void deck (prologue / epilogue set).

Writes tileable material textures + one decal atlas at 1024² (desktop) and 512² (mobile) into
tools/voiddeck_tex/{1024,512}/.  All artwork is original and drawn procedurally (no photographs).
Notices use invented text; no real logos or campaign branding.

Run with any Python that has numpy + Pillow, e.g. Blender's bundled Python:
    PY=/Applications/Blender.app/Contents/Resources/5.2/python/bin/python3.13
    $PY -m pip install --target <dir> pillow
    PYTHONPATH=<dir> $PY tools/gen_voiddeck_textures.py
(tools/build_voiddeck.py runs this automatically when textures are missing; set VOIDDECK_PYLIB
 to the Pillow target dir.)

Atlas layout (pixels in the 1024 atlas, origin top-left) is mirrored in build_voiddeck.py (ATLAS).
"""
import os, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "voiddeck_tex")
N = 1024
rng = np.random.default_rng(53)
random.seed(53)

F_HELV = ("/System/Library/Fonts/Helvetica.ttc", 1)       # Helvetica Bold
F_HELV_R = ("/System/Library/Fonts/Helvetica.ttc", 0)
F_DIN = ("/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf", 0)
F_DINA = ("/System/Library/Fonts/Supplemental/DIN Alternate Bold.ttf", 0)
F_ARB = ("/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf", 0)
F_SC = ("/System/Library/Fonts/Hiragino Sans GB.ttc", 1)   # Simplified Chinese (W6)
F_SC_R = ("/System/Library/Fonts/Hiragino Sans GB.ttc", 0)


def font(spec, size):
    path, idx = spec
    try:
        return ImageFont.truetype(path, int(size), index=idx)
    except Exception:
        try:
            return ImageFont.truetype(path, int(size))
        except Exception:
            return ImageFont.load_default()


# ----------------------------------------------------------------------------------------
# noise helpers
# ----------------------------------------------------------------------------------------
def pnoise(n, beta=2.0, seed=0, aniso=(1.0, 1.0), m=None):
    """Periodic fractal noise via FFT filtering -> tileable, [0,1]."""
    m = m or n
    r = np.random.default_rng(seed)
    w = r.standard_normal((m, n))
    fy = np.fft.fftfreq(m)[:, None] * aniso[1]
    fx = np.fft.fftfreq(n)[None, :] * aniso[0]
    f = np.sqrt(fx * fx + fy * fy)
    f[0, 0] = 1.0
    spec = np.fft.fft2(w) / (f ** (beta / 2.0))
    spec[0, 0] = 0
    out = np.real(np.fft.ifft2(spec))
    out -= out.min()
    out /= max(out.max(), 1e-9)
    return out


def to_img(arr):
    return Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8))


def rgb(c):
    return np.array(c, dtype=np.float32)[None, None, :]


def fill(base, noise, amt):
    return base * (1.0 + (noise[..., None] - 0.5) * amt)


# ----------------------------------------------------------------------------------------
# tileable materials
# ----------------------------------------------------------------------------------------
def tex_paint():
    """Painted concrete / render: near-white, soft mottling, faint roller marks + streaks."""
    a = pnoise(N, 2.2, 1) * 0.6 + pnoise(N, 1.2, 2) * 0.4
    streak = pnoise(N, 2.0, 3, aniso=(6.0, 0.4))
    fine = pnoise(N, 0.6, 4)
    v = 0.90 + (a - 0.5) * 0.10 + (streak - 0.5) * 0.05 + (fine - 0.5) * 0.04
    img = np.stack([v * 1.0, v * 0.99, v * 0.965], -1)
    return to_img(img)


def tex_concrete():
    a = pnoise(N, 2.0, 11)
    b = pnoise(N, 0.4, 12)
    spots = (pnoise(N, 0.2, 13) > 0.78).astype(np.float32) * 0.06
    v = 0.74 + (a - 0.5) * 0.18 + (b - 0.5) * 0.10 - spots
    # expansion joints every 1/2 texture (texture = 2 m)
    x = np.arange(N)
    j = ((np.abs((x % (N // 2)) - 0) < 3) | (np.abs((x % (N // 2)) - N // 2) < 3)).astype(np.float32)
    v = v - j[None, :] * 0.18
    img = np.stack([v * 1.0, v * 0.98, v * 0.94], -1)
    return to_img(img)


def tex_floor():
    """300 mm homogeneous tiles, 4x4 per texture (1.2 m repeat), warm grey-beige, speckled, worn."""
    t = N // 4
    speck = pnoise(N, 0.1, 21)
    speck2 = pnoise(N, 0.05, 22)
    base = np.zeros((N, N, 3), np.float32)
    rr = np.random.default_rng(7)
    for i in range(4):
        for j in range(4):
            k = 1.0 + rr.uniform(-0.045, 0.045)
            warm = rr.uniform(-0.015, 0.015)
            base[i * t:(i + 1) * t, j * t:(j + 1) * t] = [0.76 * k + warm, 0.735 * k, 0.69 * k - warm]
    wear = pnoise(N, 2.4, 23)
    v = 1.0 + (speck - 0.5) * 0.22 + (speck2 - 0.5) * 0.12 + (wear - 0.5) * 0.10
    img = base * v[..., None]
    # dark and light fleck grains
    fl = rr.random((N, N))
    img[fl > 0.985] *= 0.72
    img[fl < 0.010] *= 1.12
    # grout lines
    g = np.zeros((N, N), np.float32)
    x = np.arange(N)
    d = np.minimum(x % t, t - (x % t))
    line = np.clip(1.0 - (d - 1.5) / 2.0, 0, 1)
    g = np.maximum(line[None, :], line[:, None])
    img = img * (1 - g[..., None] * 0.42)
    # soft bevel highlight just inside the grout
    bev = np.clip(1.0 - np.abs(d - 5.0) / 3.0, 0, 1)
    bevm = np.maximum(bev[None, :], bev[:, None]) * (1 - g)
    img = img * (1 + bevm[..., None] * 0.03)
    return to_img(img)


def tex_terrazzo():
    """Polished terrazzo: cement matrix with marble chips (white, black, rust, jade)."""
    base = np.zeros((N, N, 3), np.float32) + np.array([0.70, 0.68, 0.63])
    mat = pnoise(N, 1.6, 31)
    base *= (1 + (mat - 0.5) * 0.12)[..., None]
    im = to_img(base)
    d = ImageDraw.Draw(im)
    rr = random.Random(31)
    cols = [((236, 232, 222), 0.42), ((40, 38, 36), 0.18), ((150, 84, 62), 0.14), ((120, 140, 118), 0.10),
            ((200, 190, 170), 0.16)]
    for _ in range(5200):
        c = rr.choices([c for c, _ in cols], [w for _, w in cols])[0]
        r = rr.choice([1.2, 1.8, 2.5, 3.2, 4.5, 6.0]) * rr.uniform(0.7, 1.3)
        x, y = rr.uniform(0, N), rr.uniform(0, N)
        k = rr.randint(4, 7)
        a0 = rr.uniform(0, 6.28)
        pts = [(x + r * rr.uniform(0.6, 1.2) * math.cos(a0 + i * 6.283 / k),
                y + r * rr.uniform(0.6, 1.2) * math.sin(a0 + i * 6.283 / k)) for i in range(k)]
        k_ = rr.uniform(0.9, 1.08)
        cc = tuple(int(v * k_) for v in c)
        for ox in (-N, 0, N):
            for oy in (-N, 0, N):
                if -12 < x + ox < N + 12 and -12 < y + oy < N + 12:
                    d.polygon([(px + ox, py + oy) for px, py in pts], fill=cc)
    return im.filter(ImageFilter.GaussianBlur(0.6))


def tex_grass():
    a = pnoise(N, 2.2, 41)
    b = pnoise(N, 1.0, 42)
    blades = pnoise(N, 0.3, 43, aniso=(1.0, 3.0))
    dry = np.clip((pnoise(N, 2.6, 44) - 0.55) * 3.0, 0, 1)
    g = np.stack([0.36 + a * 0.10, 0.52 + a * 0.14, 0.20 + a * 0.05], -1)
    dryc = np.array([0.62, 0.60, 0.34])
    g = g * (1 - dry[..., None] * 0.55) + dryc * dry[..., None] * 0.55
    g *= (0.80 + b * 0.25 + (blades - 0.5) * 0.35)[..., None]
    return to_img(g)


def tex_foliage(flower=False):
    """Tileable tropical leaf clumps (rain tree / shrubs); flower=True: bougainvillea bracts."""
    im = Image.new("RGB", (N, N), (46, 78, 38))
    d = ImageDraw.Draw(im)
    rr = random.Random(51 + flower)
    for half in ((1,) if flower else (0,)):
        for _ in range(8400 if half == 0 else 6400):
            x = rr.uniform(0, N)
            y = rr.uniform(0, N)
            L = rr.uniform(10, 24)
            a = rr.uniform(0, 6.283)
            w = L * 0.42
            sh = rr.uniform(0.55, 1.25)
            if half == 1 and rr.random() < 0.5:
                c = (int(205 * sh), int(40 * sh), int(128 * sh))     # magenta bract
                L *= 0.75
                w = L * 0.7
            else:
                c = (int(58 * sh), int(104 * sh), int(44 * sh)) if rr.random() < 0.8 else (int(92 * sh), int(128 * sh), int(52 * sh))
            ca, sa = math.cos(a), math.sin(a)
            pts = []
            for t, s in ((0, 0), (0.35, w), (1, 0), (0.35, -w)):
                px = x + ca * t * L - sa * s * 0.5
                py = y + sa * t * L + ca * s * 0.5
                pts.append((px, py))
            for ox in (-N, 0, N):
                for oy in (-N, 0, N):
                    if -30 < x + ox < N + 30 and -30 < y + oy < N + 30:
                        d.polygon([(px + ox, py + oy) for px, py in pts], fill=tuple(min(255, v) for v in c))
    arr = np.asarray(im).astype(np.float32) / 255
    shade = pnoise(N, 2.0, 52)
    arr *= (0.7 + 0.5 * shade)[..., None]
    return to_img(arr).filter(ImageFilter.GaussianBlur(0.5))


def tex_facade():
    """HDB slab block elevations. Top half (v 0.5..1): corridor side, one storey (2.8 m) x 6.4 m.
    Bottom half: window side with laundry poles, aircon ledges. Neutral-cream; tinted per block."""
    W, H = N, N // 2
    im = Image.new("RGB", (N, N), (230, 222, 204))
    d = ImageDraw.Draw(im)
    # ---- corridor side (top half, image y 0..512)
    y0 = 0
    slab = int(H * 0.11)
    par = int(H * 0.36)
    d.rectangle([0, y0, W, y0 + slab], fill=(236, 230, 214))                   # slab edge band
    d.rectangle([0, y0 + slab, W, y0 + H - par], fill=(70, 64, 58))            # corridor shadow
    # back wall with doors/windows
    for i, x in enumerate(range(0, W, W // 3)):
        u = W // 3
        d.rectangle([x + 6, y0 + slab + 10, x + u - 6, y0 + H - par], fill=(112, 102, 90))
        # door
        d.rectangle([x + 24, y0 + slab + 34, x + 24 + 70, y0 + H - par], fill=(96, 62, 44))
        d.rectangle([x + 20, y0 + slab + 30, x + 28 + 70, y0 + slab + 36], fill=(150, 140, 120))
        # gate grille
        for gx in range(x + 22, x + 96, 9):
            d.line([gx, y0 + slab + 36, gx, y0 + H - par], fill=(40, 40, 40), width=2)
        # windows with grilles & curtains
        wx = x + 130
        d.rectangle([wx, y0 + slab + 50, wx + 170, y0 + slab + 150], fill=(160, 170, 170))
        cur = [(198, 170, 120), (170, 190, 205), (220, 200, 190), (150, 170, 140)][i % 4]
        d.rectangle([wx + 4, y0 + slab + 54, wx + 70, y0 + slab + 146], fill=cur)
        for gx in range(wx, wx + 171, 17):
            d.line([gx, y0 + slab + 50, gx, y0 + slab + 150], fill=(60, 60, 60), width=2)
        # shoe rack / potted plants along corridor
        d.rectangle([x + 110, y0 + H - par - 26, x + 150, y0 + H - par], fill=(80, 80, 88))
        for k in range(3):
            px = x + 230 + k * 22
            d.ellipse([px - 12, y0 + H - par - 40, px + 12, y0 + H - par - 12], fill=(60, 110, 50))
            d.rectangle([px - 8, y0 + H - par - 16, px + 8, y0 + H - par], fill=(150, 80, 50))
    # ceiling lamps in corridor
    for x in range(W // 6, W, W // 3):
        d.rectangle([x - 26, y0 + slab + 4, x + 26, y0 + slab + 10], fill=(255, 250, 235))
    # parapet (solid lower wall) + coping
    d.rectangle([0, y0 + H - par, W, y0 + H], fill=(232, 224, 206))
    d.rectangle([0, y0 + H - par, W, y0 + H - par + 12], fill=(246, 242, 232))
    d.rectangle([0, y0 + H - 44, W, y0 + H - 28], fill=(176, 92, 70))            # colour stripe
    # ---- window side (bottom half, image y 512..1024)
    y0 = H
    d.rectangle([0, y0, W, y0 + H], fill=(228, 220, 202))
    d.rectangle([0, y0, W, y0 + 36], fill=(238, 232, 218))
    for i, x in enumerate(range(0, W, W // 2)):
        u = W // 2
        # two windows per unit
        for k, (wx, ww) in enumerate(((x + 40, 170), (x + 270, 200))):
            d.rectangle([wx - 8, y0 + 120, wx + ww + 8, y0 + 132], fill=(244, 240, 230))   # hood
            d.rectangle([wx, y0 + 132, wx + ww, y0 + 290], fill=(92, 104, 110))
            d.rectangle([wx + 6, y0 + 138, wx + ww // 2 - 3, y0 + 284], fill=(140, 156, 160))
            d.rectangle([wx + ww // 2 + 3, y0 + 138, wx + ww - 6, y0 + 284], fill=(120, 136, 142))
            cur = [(206, 180, 130), (180, 200, 210), (230, 210, 200)][(i + k) % 3]
            d.rectangle([wx + 8, y0 + 140, wx + 40, y0 + 282], fill=cur)
            d.rectangle([wx - 8, y0 + 290, wx + ww + 8, y0 + 302], fill=(240, 236, 226))   # sill
        # aircon ledge + compressor
        d.rectangle([x + 20, y0 + 340, x + 250, y0 + 352], fill=(210, 204, 190))
        d.rectangle([x + 60, y0 + 300, x + 150, y0 + 340], fill=(222, 222, 216))
        d.ellipse([x + 70, y0 + 306, x + 100, y0 + 336], fill=(150, 150, 146))
        # laundry poles with clothes
        for p in range(3):
            py = y0 + 316 + p * 12
            d.line([x + 262, py, x + 500, py], fill=(200, 200, 196), width=3)
            px = x + 270
            rr = random.Random(i * 10 + p)
            while px < x + 490:
                cw = rr.randint(18, 42)
                ch = rr.randint(30, 80)
                cc = rr.choice([(236, 236, 230), (80, 110, 160), (200, 90, 80), (240, 200, 90), (120, 160, 120),
                                (60, 60, 70), (230, 170, 180), (170, 200, 220)])
                if rr.random() < 0.7:
                    d.rectangle([px, py, px + cw, py + ch], fill=cc)
                px += cw + rr.randint(4, 16)
    # soft weathering streaks
    arr = np.asarray(im).astype(np.float32) / 255
    st = pnoise(N, 2.0, 61, aniso=(8.0, 0.3))
    arr *= (0.94 + 0.08 * st)[..., None]
    return to_img(arr).filter(ImageFilter.GaussianBlur(0.4))


# ----------------------------------------------------------------------------------------
# decal atlas
# ----------------------------------------------------------------------------------------
ATLAS = {  # name: (x0, y0, x1, y1) pixels in the 1024 atlas
    "chess": (0, 0, 320, 320),
    "liftdoor": (320, 0, 480, 320),
    "liftind": (480, 0, 640, 64),
    "liftbtn": (480, 64, 560, 224),
    "lifttag": (560, 64, 640, 224),
    "letterbox": (640, 0, 1024, 208),
    "blksign": (640, 208, 1024, 320),
    "notice": (0, 320, 384, 576),
    "noball": (384, 320, 512, 448),
    "hosereel": (512, 320, 640, 512),
    "dbbox": (640, 320, 736, 448),
    "liftsign": (736, 320, 1024, 384),
    "directory": (736, 384, 1024, 512),
    "cctv": (384, 448, 512, 512),
    "stooltop": (0, 576, 128, 704),
    "grating": (128, 576, 256, 704),
    "playpanel": (256, 576, 512, 704),
    "heritage": (512, 512, 768, 704),
    "lantern_r": (768, 512, 832, 576),
    "lantern_y": (832, 512, 896, 576),
    "lantern_p": (896, 512, 960, 576),
    "lantern_b": (960, 512, 1024, 576),
    "vending": (768, 576, 896, 832),
    "fitness": (896, 576, 1024, 704),
    "pillar53": (0, 704, 192, 1024),
    "hopscotch": (192, 704, 320, 1024),
    "banner": (320, 704, 768, 832),
    "mural": (320, 832, 1024, 1024),
    "bin": (896, 704, 1024, 832),
}


def jit(c, rr, lo, hi):
    k = rr.uniform(lo, hi)
    return tuple(max(0, min(255, int(v * k))) for v in c)


def shade_box(d, b, fill, dk=0.72, lt=1.12, w=3):
    x0, y0, x1, y1 = b
    d.rectangle(b, fill=fill)
    L = tuple(min(255, int(c * lt)) for c in fill)
    D = tuple(int(c * dk) for c in fill)
    d.rectangle([x0, y0, x1, y0 + w - 1], fill=L)
    d.rectangle([x0, y0, x0 + w - 1, y1], fill=L)
    d.rectangle([x0, y1 - w + 1, x1, y1], fill=D)
    d.rectangle([x1 - w + 1, y0, x1, y1], fill=D)


def text_c(d, cx, cy, s, spec, size, fill, anchor="mm"):
    d.text((cx, cy), s, font=font(spec, size), fill=fill, anchor=anchor)


def fit(d, box, s, spec, fill, max_size=200, anchor="mm"):
    x0, y0, x1, y1 = box
    size = max_size
    while size > 6:
        f = font(spec, size)
        l, t, r, b = d.textbbox((0, 0), s, font=f)
        if r - l <= (x1 - x0) and b - t <= (y1 - y0):
            break
        size -= 1
    d.text(((x0 + x1) / 2, (y0 + y1) / 2), s, font=font(spec, size), fill=fill, anchor="mm")


def atlas():
    im = Image.new("RGB", (N, N), (200, 196, 188))
    d = ImageDraw.Draw(im)
    rr = random.Random(99)

    # --- chess: mosaic chessboard, 8x8 cells, each of 3x3 small tiles, blue border ring
    x0, y0, x1, y1 = ATLAS["chess"]
    d.rectangle([x0, y0, x1, y1], fill=(150, 146, 138))                # grout
    S = x1 - x0
    border = 16
    cell = (S - 2 * border) / 8.0
    # border tiles
    n_b = 20
    for k in range(n_b):
        for side in range(4):
            t0 = k * S / n_b
            if side == 0:
                b = (x0 + t0, y0, x0 + t0 + S / n_b, y0 + border)
            elif side == 1:
                b = (x0 + t0, y1 - border, x0 + t0 + S / n_b, y1)
            elif side == 2:
                b = (x0, y0 + t0, x0 + border, y0 + t0 + S / n_b)
            else:
                b = (x1 - border, y0 + t0, x1, y0 + t0 + S / n_b)
            c = (58, 92, 128) if (k % 2 == 0) else (212, 206, 190)
            c = jit(c, rr, 0.9, 1.08)
            d.rectangle([b[0] + 1, b[1] + 1, b[2] - 1, b[3] - 1], fill=c)
    for i in range(8):
        for j in range(8):
            dark = (i + j) % 2 == 0
            base = (118, 44, 38) if dark else (226, 214, 188)
            cx0 = x0 + border + j * cell
            cy0 = y0 + border + i * cell
            for a in range(3):
                for b_ in range(3):
                    s3 = cell / 3
                    c = jit(base, rr, 0.84, 1.08)
                    if rr.random() < 0.03:              # chipped tile
                        c = (160, 156, 146)
                    d.rectangle([cx0 + b_ * s3 + 1, cy0 + a * s3 + 1, cx0 + (b_ + 1) * s3 - 1, cy0 + (a + 1) * s3 - 1], fill=c)

    # --- stool top: small mosaic tiles, cream with a jade ring (mapped as a disc)
    x0, y0, x1, y1 = ATLAS["stooltop"]
    d.rectangle([x0, y0, x1, y1], fill=(150, 146, 138))
    cx, cy, R = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2
    s = 10
    for gy in range(y0, y1, s):
        for gx in range(x0, x1, s):
            r = math.hypot(gx + s / 2 - cx, gy + s / 2 - cy) / R
            base = (70, 120, 110) if 0.62 < r < 0.80 else ((118, 44, 38) if r < 0.22 else (222, 212, 190))
            c = jit(base, rr, 0.86, 1.08)
            d.rectangle([gx + 1, gy + 1, gx + s - 1, gy + s - 1], fill=c)

    # --- lift door pair (brushed stainless, centre seam, vision-less)
    x0, y0, x1, y1 = ATLAS["liftdoor"]
    arr = np.zeros((y1 - y0, x1 - x0, 3), np.float32)
    br = pnoise(max(x1 - x0, y1 - y0), 1.0, 71, aniso=(0.2, 8.0))[: y1 - y0, : x1 - x0]
    arr[:] = np.array([0.70, 0.71, 0.72])
    arr *= (0.9 + 0.2 * br)[..., None]
    grad = np.linspace(1.08, 0.86, y1 - y0)[:, None, None]
    arr *= grad
    im.paste(to_img(arr), (x0, y0))
    mid = (x0 + x1) // 2
    d.rectangle([mid - 1, y0, mid + 1, y1], fill=(60, 62, 64))
    d.rectangle([x0, y0, x0 + 3, y1], fill=(120, 122, 124))
    d.rectangle([x1 - 4, y0, x1, y1], fill=(120, 122, 124))
    # --- lift indicator: dark panel, red LED "1", arrows
    x0, y0, x1, y1 = ATLAS["liftind"]
    d.rectangle([x0, y0, x1, y1], fill=(170, 172, 174))
    d.rectangle([x0 + 20, y0 + 10, x1 - 20, y1 - 10], fill=(18, 18, 20))
    text_c(d, (x0 + x1) / 2 + 10, (y0 + y1) / 2, "1", F_DINA, 40, (255, 70, 40))
    d.polygon([(x0 + 40, y0 + 38), (x0 + 52, y0 + 22), (x0 + 64, y0 + 38)], fill=(90, 255, 120))
    # --- lift call buttons
    x0, y0, x1, y1 = ATLAS["liftbtn"]
    shade_box(d, (x0, y0, x1, y1), (182, 184, 186))
    for k, yy in enumerate((y0 + 55, y0 + 105)):
        d.ellipse([x0 + 22, yy - 18, x0 + 58, yy + 18], fill=(90, 92, 96))
        d.ellipse([x0 + 27, yy - 13, x0 + 53, yy + 13], fill=(220, 222, 224))
        if k == 0:
            d.polygon([(x0 + 40, yy - 8), (x0 + 49, yy + 6), (x0 + 31, yy + 6)], fill=(60, 60, 60))
        else:
            d.polygon([(x0 + 40, yy + 8), (x0 + 49, yy - 6), (x0 + 31, yy - 6)], fill=(60, 60, 60))
    # --- lift tag ("A" plate)
    x0, y0, x1, y1 = ATLAS["lifttag"]
    shade_box(d, (x0, y0, x1, y1), (40, 70, 110))
    text_c(d, (x0 + x1) / 2, y0 + 45, "LIFT", F_HELV, 20, (255, 255, 255))
    text_c(d, (x0 + x1) / 2, y0 + 105, "A", F_HELV, 64, (255, 255, 255))

    # --- letterbox bank: grid of small grey doors with unit numbers and key locks
    x0, y0, x1, y1 = ATLAS["letterbox"]
    d.rectangle([x0, y0, x1, y1], fill=(120, 124, 128))
    cols, rows = 12, 8
    cw, ch = (x1 - x0 - 8) / cols, (y1 - y0 - 30) / rows
    d.rectangle([x0, y0, x1, y0 + 22], fill=(60, 64, 70))
    text_c(d, (x0 + x1) / 2, y0 + 11, "BLK 53  LETTER BOXES  信箱", F_SC, 14, (240, 240, 240))
    for r in range(rows):
        for c in range(cols):
            bx = x0 + 4 + c * cw
            by = y0 + 26 + r * ch
            col = (176, 180, 184) if (r + c) % 7 else (168, 172, 178)
            shade_box(d, (int(bx + 1), int(by + 1), int(bx + cw - 1), int(by + ch - 1)), col, w=2)
            d.rectangle([int(bx + 4), int(by + 4), int(bx + cw - 5), int(by + 8)], fill=(40, 40, 44))  # slot
            d.ellipse([int(bx + cw - 12), int(by + ch - 12), int(bx + cw - 6), int(by + ch - 6)], fill=(210, 190, 110))
            unit = "#%02d-%d" % (12 - r, 101 + c)
            d.text((int(bx + 4), int(by + ch - 12)), unit, font=font(F_HELV_R, 8), fill=(50, 50, 50))
            if rr.random() < 0.08:  # a flyer sticking out
                d.rectangle([int(bx + 6), int(by + 1), int(bx + cw - 8), int(by + 6)], fill=(240, 220, 120))

    # --- block sign plate: "BLK 53" white on maroon, plus small line
    x0, y0, x1, y1 = ATLAS["blksign"]
    shade_box(d, (x0, y0, x1, y1), (128, 38, 40))
    fit(d, (x0 + 20, y0 + 8, x1 - 20, y1 - 26), "BLK 53", F_HELV, (250, 246, 236), 90)
    text_c(d, (x0 + x1) / 2, y1 - 14, "STRATHMORE  ·  QUEENSTOWN", F_HELV, 16, (240, 220, 210))

    # --- notice board: cork frame + notices (invented text)
    x0, y0, x1, y1 = ATLAS["notice"]
    shade_box(d, (x0, y0, x1, y1), (120, 84, 54), w=6)
    d.rectangle([x0 + 10, y0 + 30, x1 - 10, y1 - 10], fill=(176, 140, 96))
    d.rectangle([x0, y0, x1, y0 + 26], fill=(28, 70, 110))
    text_c(d, (x0 + x1) / 2, y0 + 13, "NOTICE BOARD  告示板  PAPAN NOTIS", F_SC, 15, (255, 255, 255))
    notes = [
        ((x0 + 18, y0 + 38, x0 + 128, y0 + 180), (255, 252, 244), "MID-AUTUMN\nCELEBRATION", "中秋晚会\n25 Sep · 7.30pm\nVoid Deck Blk 53\nLanterns · Mooncakes", (200, 60, 40)),
        ((x0 + 138, y0 + 40, x0 + 244, y0 + 150), (255, 255, 255), "LIFT\nMAINTENANCE", "Lift A: 3 Oct 2026\n9am – 12pm\nWe apologise for\nthe inconvenience.", (30, 60, 110)),
        ((x0 + 254, y0 + 36, x0 + 366, y0 + 176), (250, 240, 150), "STOP\nDENGUE", "Check for\nstagnant water\nevery week.\n防止骨痛热症", (40, 40, 40)),
        ((x0 + 140, y0 + 160, x0 + 246, y0 + 240), (220, 238, 250), "SENIOR\nWELLNESS", "Morning exercise\nTue & Thu 7am\n乐龄健身", (20, 90, 70)),
        ((x0 + 22, y0 + 190, x0 + 124, y0 + 242), (255, 255, 255), "BLOCK\nWASHING", "Fri 8am", (40, 40, 40)),
        ((x0 + 262, y0 + 186, x0 + 364, y0 + 242), (255, 226, 226), "BE KIND", "to neighbours\n邻里和睦", (160, 30, 40)),
    ]
    for (b, paper, title, body, tc) in notes:
        bx0, by0, bx1, by1 = b
        d.rectangle([bx0 + 3, by0 + 3, bx1 + 3, by1 + 3], fill=(120, 92, 60))
        d.rectangle(b, fill=paper)
        d.rectangle([bx0, by0, bx1, by0 + 6], fill=tc)
        tf = font(F_HELV, 13)
        d.multiline_text((bx0 + 6, by0 + 10), title, font=tf, fill=tc, spacing=1)
        bf = font(F_SC_R, 9)
        nl = title.count("\n") + 1
        d.multiline_text((bx0 + 6, by0 + 14 + nl * 15), body, font=bf, fill=(50, 50, 50), spacing=2)
        d.ellipse([(bx0 + bx1) / 2 - 3, by0 + 1, (bx0 + bx1) / 2 + 3, by0 + 7], fill=(200, 30, 30))
    # little lantern drawing on the mid-autumn notice
    d.ellipse([x0 + 90, y0 + 146, x0 + 118, y0 + 172], fill=(230, 80, 50))

    # --- no ball games sign (4 lines, English/Chinese/Malay; Tamil omitted — no text shaping)
    x0, y0, x1, y1 = ATLAS["noball"]
    shade_box(d, (x0, y0, x1, y1), (250, 250, 246), w=3)
    d.ellipse([x0 + 34, y0 + 8, x0 + 94, y0 + 68], outline=(200, 30, 30), width=7)
    d.ellipse([x0 + 50, y0 + 24, x0 + 78, y0 + 52], fill=(40, 40, 40))
    d.line([x0 + 43, y0 + 17, x0 + 85, y0 + 59], fill=(200, 30, 30), width=7)
    text_c(d, (x0 + x1) / 2, y0 + 82, "NO BALL GAMES", F_HELV, 13, (30, 30, 30))
    text_c(d, (x0 + x1) / 2, y0 + 98, "请勿玩球", F_SC, 13, (30, 30, 30))
    text_c(d, (x0 + x1) / 2, y0 + 114, "DILARANG BERMAIN BOLA", F_HELV, 9, (30, 30, 30))

    # --- fire hose reel cabinet
    x0, y0, x1, y1 = ATLAS["hosereel"]
    shade_box(d, (x0, y0, x1, y1), (196, 38, 34), w=5)
    d.rectangle([x0 + 12, y0 + 12, x1 - 12, y0 + 44], fill=(250, 250, 250))
    text_c(d, (x0 + x1) / 2, y0 + 28, "HOSE REEL", F_HELV, 17, (190, 30, 30))
    d.ellipse([x0 + 24, y0 + 64, x1 - 24, y0 + 144], outline=(120, 20, 20), width=6)
    d.ellipse([x0 + 50, y0 + 90, x1 - 50, y0 + 118], fill=(120, 20, 20))
    d.rectangle([x1 - 20, y0 + 80, x1 - 12, y0 + 120], fill=(200, 200, 200))
    text_c(d, (x0 + x1) / 2, y1 - 22, "消防水喉", F_SC, 16, (255, 240, 240))
    # --- DB box
    x0, y0, x1, y1 = ATLAS["dbbox"]
    shade_box(d, (x0, y0, x1, y1), (170, 174, 168), w=4)
    d.polygon([(x0 + 48, y0 + 20), (x0 + 30, y0 + 60), (x0 + 50, y0 + 58), (x0 + 40, y0 + 96), (x0 + 66, y0 + 50), (x0 + 48, y0 + 52)], fill=(250, 200, 20))
    d.rectangle([x1 - 16, y0 + 50, x1 - 10, y0 + 76], fill=(60, 60, 60))
    # --- lift lobby sign strip
    x0, y0, x1, y1 = ATLAS["liftsign"]
    shade_box(d, (x0, y0, x1, y1), (28, 70, 110), w=3)
    text_c(d, x0 + 90, (y0 + y1) / 2, "LIFT LOBBY", F_HELV, 24, (255, 255, 255))
    text_c(d, x0 + 200, (y0 + y1) / 2, "电梯", F_SC, 24, (255, 255, 255))
    d.polygon([(x1 - 50, y0 + 44), (x1 - 30, y0 + 20), (x1 - 10, y0 + 44)], fill=(255, 255, 255))
    # --- block directory
    x0, y0, x1, y1 = ATLAS["directory"]
    shade_box(d, (x0, y0, x1, y1), (240, 238, 230), w=3)
    d.rectangle([x0, y0, x1, y0 + 30], fill=(128, 38, 40))
    text_c(d, (x0 + x1) / 2, y0 + 15, "BLK 53   UNITS #02-101 – #12-112", F_HELV, 14, (255, 255, 255))
    for k in range(5):
        d.rectangle([x0 + 14, y0 + 42 + k * 16, x1 - 14, y0 + 48 + k * 16], fill=(170, 166, 156))
    # --- CCTV sign
    x0, y0, x1, y1 = ATLAS["cctv"]
    shade_box(d, (x0, y0, x1, y1), (250, 214, 40), w=2)
    text_c(d, (x0 + x1) / 2, y0 + 20, "CCTV", F_HELV, 22, (20, 20, 20))
    text_c(d, (x0 + x1) / 2, y0 + 46, "IN OPERATION", F_HELV, 12, (20, 20, 20))

    # --- drain grating
    x0, y0, x1, y1 = ATLAS["grating"]
    d.rectangle([x0, y0, x1, y1], fill=(22, 22, 22))
    for gx in range(x0, x1, 10):
        d.rectangle([gx, y0, gx + 5, y1], fill=(92, 92, 88))
    for gy in range(y0, y1, 32):
        d.rectangle([x0, gy, x1, gy + 4], fill=(80, 80, 76))
    # --- playground panel (bright, tic-tac-toe + holes)
    x0, y0, x1, y1 = ATLAS["playpanel"]
    shade_box(d, (x0, y0, x1, y1), (240, 184, 40), w=5)
    for i in range(3):
        for j in range(3):
            c = [(220, 60, 50), (40, 120, 200)][(i * 3 + j) % 2]
            d.ellipse([x0 + 20 + j * 34, y0 + 16 + i * 34, x0 + 48 + j * 34, y0 + 44 + i * 34], fill=c)
    d.ellipse([x0 + 150, y0 + 24, x0 + 230, y0 + 104], fill=(40, 150, 90))
    d.ellipse([x0 + 170, y0 + 44, x0 + 210, y0 + 84], fill=(240, 184, 40))
    # --- heritage marker board (invented design; no real logo)
    x0, y0, x1, y1 = ATLAS["heritage"]
    shade_box(d, (x0, y0, x1, y1), (38, 58, 72), w=4)
    d.rectangle([x0 + 10, y0 + 10, x1 - 10, y0 + 40], fill=(214, 170, 90))
    text_c(d, (x0 + x1) / 2, y0 + 25, "QUEENSTOWN", F_HELV, 20, (38, 40, 44))
    text_c(d, (x0 + x1) / 2, y0 + 56, "Singapore's first satellite town", F_HELV_R, 13, (240, 236, 226))
    text_c(d, (x0 + x1) / 2, y0 + 74, "planned 1953 · first HDB flats 1960", F_HELV_R, 11, (210, 210, 200))
    # tiny line drawing of slab blocks
    for k, (bx, bw, bh) in enumerate(((x0 + 24, 70, 70), (x0 + 104, 50, 90), (x0 + 164, 70, 60))):
        d.rectangle([bx, y1 - 12 - bh, bx + bw, y1 - 12], outline=(214, 170, 90), width=2)
        for yy in range(y1 - 12 - bh + 8, y1 - 12, 10):
            d.line([bx + 4, yy, bx + bw - 4, yy], fill=(214, 170, 90), width=1)
    # --- lanterns (mid-autumn): paper lantern faces
    for key, c in (("lantern_r", (214, 44, 36)), ("lantern_y", (240, 176, 40)), ("lantern_p", (220, 80, 130)), ("lantern_b", (60, 130, 200))):
        x0, y0, x1, y1 = ATLAS[key]
        arr = np.zeros((y1 - y0, x1 - x0, 3), np.float32)
        yy = np.linspace(-1, 1, y1 - y0)[:, None]
        xx = np.linspace(-1, 1, x1 - x0)[None, :]
        glow = np.clip(1.2 - 0.5 * (xx ** 2 + yy ** 2), 0, 1.2)
        arr[:] = np.array(c, np.float32) / 255
        arr *= glow[..., None]
        ribs = (np.abs(np.sin((yy + 1) * math.pi * 4)) < 0.12).astype(np.float32)
        arr *= (1 - ribs[..., None] * 0.35) * np.ones_like(xx)[..., None]
        im.paste(to_img(arr), (x0, y0))
        d.rectangle([x0, y0, x1, y0 + 5], fill=(200, 160, 60))
        d.rectangle([x0, y1 - 6, x1, y1], fill=(200, 160, 60))
        text_c(d, (x0 + x1) / 2, (y0 + y1) / 2, "福", F_SC, 28, (255, 226, 120) if key != "lantern_y" else (180, 40, 30))
    # --- vending machine front
    x0, y0, x1, y1 = ATLAS["vending"]
    shade_box(d, (x0, y0, x1, y1), (200, 40, 40), w=4)
    d.rectangle([x0 + 10, y0 + 12, x1 - 36, y0 + 170], fill=(30, 34, 40))
    for r in range(4):
        for c in range(4):
            cc = rr.choice([(240, 200, 60), (60, 160, 220), (230, 90, 60), (90, 190, 110), (240, 240, 240)])
            d.rectangle([x0 + 16 + c * 18, y0 + 20 + r * 38, x0 + 28 + c * 18, y0 + 48 + r * 38], fill=cc)
        d.rectangle([x0 + 12, y0 + 50 + r * 38, x1 - 38, y0 + 54 + r * 38], fill=(160, 160, 160))
    d.rectangle([x1 - 30, y0 + 40, x1 - 12, y0 + 110], fill=(60, 60, 60))
    d.rectangle([x0 + 16, y1 - 60, x1 - 40, y1 - 30], fill=(20, 20, 20))
    text_c(d, (x0 + x1) / 2, y0 + 200, "COLD DRINKS", F_HELV, 12, (255, 255, 255))
    # --- fitness corner sign
    x0, y0, x1, y1 = ATLAS["fitness"]
    shade_box(d, (x0, y0, x1, y1), (40, 130, 90), w=3)
    text_c(d, (x0 + x1) / 2, y0 + 40, "PLAYGROUND", F_HELV, 15, (255, 255, 255))
    text_c(d, (x0 + x1) / 2, y0 + 64, "游乐场", F_SC, 16, (255, 255, 255))
    text_c(d, (x0 + x1) / 2, y0 + 92, "TAMAN PERMAINAN", F_HELV, 9, (255, 255, 255))
    # --- painted pillar block number panel: cream band, maroon "53" (lower "BLK")
    x0, y0, x1, y1 = ATLAS["pillar53"]
    d.rectangle([x0, y0, x1, y1], fill=(236, 226, 204))
    d.rectangle([x0, y0, x1, y0 + 10], fill=(128, 38, 40))
    d.rectangle([x0, y1 - 10, x1, y1], fill=(128, 38, 40))
    text_c(d, (x0 + x1) / 2, y0 + 50, "BLK", F_HELV, 44, (128, 38, 40))
    fit(d, (x0 + 8, y0 + 80, x1 - 8, y1 - 24), "53", F_HELV, (128, 38, 40), 220)
    # --- hopscotch (painted on floor, 1 x 3 m -> 128 x 384; white/yellow worn paint)
    x0, y0, x1, y1 = ATLAS["hopscotch"]
    arr = np.asarray(Image.open(os.path.join(OUT, "_floor_crop.png"))) if os.path.exists(os.path.join(OUT, "_floor_crop.png")) else None
    d.rectangle([x0, y0, x1, y1], fill=(196, 190, 178))
    layout = [(1, [0]), (2, [0]), (3, [0]), (4, [-1, 1]), (6, [0]), (7, [-1, 1]), (9, [0])]
    h = (y1 - y0) / 7.0
    ww = (x1 - x0) / 2.0
    for k, (num, pos) in enumerate(layout):
        yb = y1 - (k + 1) * h
        for p in pos:
            if p == 0:
                bx0, bx1 = x0 + ww / 2, x0 + ww * 1.5
            elif p < 0:
                bx0, bx1 = x0 + 2, x0 + ww
            else:
                bx0, bx1 = x0 + ww, x1 - 2
            d.rectangle([bx0, yb + 2, bx1, yb + h - 2], outline=(250, 236, 150), width=4)
            n = num if len(pos) == 1 else (num if p < 0 else num + 1)
            text_c(d, (bx0 + bx1) / 2, yb + h / 2, str(n), F_ARB, 24, (250, 250, 240))
    # --- mid-autumn banner (fabric strip hung from beam)
    x0, y0, x1, y1 = ATLAS["banner"]
    shade_box(d, (x0, y0, x1, y1), (176, 30, 34), w=4)
    d.rectangle([x0 + 6, y0 + 6, x1 - 6, y0 + 12], fill=(230, 180, 70))
    d.rectangle([x0 + 6, y1 - 12, x1 - 6, y1 - 6], fill=(230, 180, 70))
    text_c(d, x0 + 118, (y0 + y1) / 2, "中秋快乐", F_SC, 46, (255, 222, 120))
    text_c(d, x0 + 300, (y0 + y1) / 2 - 16, "Happy Mid-Autumn", F_HELV, 18, (255, 240, 210))
    text_c(d, x0 + 300, (y0 + y1) / 2 + 18, "Blk 53 Residents", F_HELV_R, 15, (255, 230, 200))
    d.ellipse([x1 - 44, y0 + 40, x1 - 14, y0 + 70], fill=(250, 210, 90))
    # --- community mural (lift lobby core wall): stylised Queenstown slab blocks at sunset
    x0, y0, x1, y1 = ATLAS["mural"]
    Wm, Hm = x1 - x0, y1 - y0
    yy = np.linspace(0, 1, Hm)[:, None, None]
    sky = (1 - yy) * np.array([0.98, 0.78, 0.52]) + yy * np.array([0.96, 0.60, 0.46])
    im.paste(to_img(np.broadcast_to(sky, (Hm, Wm, 3)).copy()), (x0, y0))
    d.ellipse([x0 + 520, y0 + 30, x0 + 600, y0 + 110], fill=(255, 236, 170))
    bl = [(20, 110, 70, (238, 226, 206)), (100, 150, 60, (200, 214, 222)), (170, 90, 90, (236, 204, 180)),
          (280, 130, 50, (226, 232, 214)), (340, 60, 110, (240, 220, 200)), (470, 120, 80, (210, 200, 226)),
          (560, 160, 100, (238, 214, 190))]
    for (bx, bw, bh, c) in bl:
        d.rectangle([x0 + bx, y1 - 40 - bh, x0 + bx + bw, y1 - 40], fill=c)
        for fy in range(y1 - 40 - bh + 10, y1 - 44, 12):
            d.line([x0 + bx + 3, fy, x0 + bx + bw - 3, fy], fill=tuple(int(v * 0.7) for v in c), width=3)
    for k in range(9):
        tx = x0 + 30 + k * 75
        d.ellipse([tx - 30, y1 - 80, tx + 30, y1 - 30], fill=(70, 130, 70))
        d.rectangle([tx - 3, y1 - 40, tx + 3, y1 - 20], fill=(90, 60, 40))
    d.rectangle([x0, y1 - 22, x1, y1], fill=(110, 160, 90))
    for k, cc in enumerate([(220, 70, 60), (60, 130, 200), (240, 190, 60), (230, 120, 170)]):
        px = x0 + 120 + k * 120
        d.ellipse([px - 8, y1 - 50, px + 8, y1 - 34], fill=(60, 40, 30))
        d.rectangle([px - 7, y1 - 34, px + 7, y1 - 14], fill=cc)
    text_c(d, x0 + 170, y0 + 34, "Our Queenstown", F_ARB, 34, (120, 50, 40))
    text_c(d, x0 + 170, y0 + 68, "我们的女皇镇 · Since 1953", F_SC, 18, (120, 50, 40))
    # --- rubbish bin (green, lid label)
    x0, y0, x1, y1 = ATLAS["bin"]
    d.rectangle([x0, y0, x1, y1], fill=(36, 110, 70))
    for k in range(6):
        d.rectangle([x0 + k * 22, y0, x0 + k * 22 + 3, y1], fill=(28, 90, 58))
    d.rectangle([x0 + 24, y0 + 40, x1 - 24, y0 + 80], fill=(250, 250, 250))
    text_c(d, (x0 + x1) / 2, y0 + 60, "LITTER", F_HELV, 14, (36, 110, 70))

    # overall slight print softness + subtle dirt
    arr = np.asarray(im).astype(np.float32) / 255
    dirt = pnoise(N, 2.0, 98)
    arr *= (0.96 + 0.06 * dirt)[..., None]
    return to_img(arr)


def save(img, name):
    for res in (1024, 512):
        dd = os.path.join(OUT, str(res))
        os.makedirs(dd, exist_ok=True)
        im = img if res == 1024 else img.resize((res, res), Image.LANCZOS)
        im.save(os.path.join(dd, name + ".png"), optimize=True)
    print("tex", name)


def main():
    save(tex_paint(), "paint")
    save(tex_concrete(), "concrete")
    save(tex_floor(), "floor")
    save(tex_terrazzo(), "terrazzo")
    save(tex_grass(), "grass")
    save(tex_foliage(), "foliage")
    save(tex_foliage(True), "flower")
    save(tex_facade(), "facade")
    save(atlas(), "atlas")


if __name__ == "__main__":
    main()
