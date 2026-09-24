"""
Procedural texture generator for the WW2 Chinatown street level (Chapter 1).

Generates tileable material textures and three atlases (windows, details, signs, posters)
at 1024² (desktop) and 512² (mobile) into tools/ww2_tex/{1024,512}/.

Run with any Python that has numpy + Pillow, e.g. Blender's bundled Python:
    PY=/Applications/Blender.app/Contents/Resources/5.2/python/bin/python3.13
    $PY -m pip install --target <some_dir> pillow
    PYTHONPATH=<some_dir> $PY tools/gen_ww2_textures.py
(build_ww2_street.py calls this automatically if textures are missing and PIL is importable.)

All artwork is original (drawn procedurally); no photographs are used.
Fonts: macOS system fonts (Songti TC for Traditional Chinese, Hiragino Mincho for Japanese,
Gill Sans / Rockwell / Futura for period English lettering).
"""
import os, math, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "ww2_tex")
N = 1024

FONT_TC = ("/System/Library/Fonts/Supplemental/Songti.ttc", 2)      # Songti TC Bold
FONT_TC_REG = ("/System/Library/Fonts/Supplemental/Songti.ttc", 7)  # Songti TC Regular
FONT_HEI = ("/System/Library/Fonts/STHeiti Medium.ttc", 0)          # Heiti TC
FONT_JP = ("/System/Library/Fonts/ヒラギノ明朝 ProN.ttc", 2)          # Hiragino Mincho W6
FONT_GILL = ("/System/Library/Fonts/Supplemental/GillSans.ttc", 1)
FONT_ROCK = ("/System/Library/Fonts/Supplemental/Rockwell.ttc", 1)
FONT_FUT = ("/System/Library/Fonts/Supplemental/Futura.ttc", 2)
FONT_COPPER = ("/System/Library/Fonts/Supplemental/Copperplate.ttc", 1)


def font(spec, size):
    path, idx = spec
    try:
        return ImageFont.truetype(path, size, index=idx)
    except Exception:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            return ImageFont.load_default()


rng = np.random.default_rng(1942)
random.seed(1942)


# ----------------------------------------------------------------------------------------
# noise helpers (periodic -> tileable)
# ----------------------------------------------------------------------------------------
def pnoise(n, beta=2.0, seed=0, aniso=(1.0, 1.0), m=None):
    """Periodic fractal noise via FFT filtering. Returns float array in [0,1]."""
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
    arr = np.clip(arr, 0, 1)
    return Image.fromarray((arr * 255).astype(np.uint8))


def rgb(a, b, c):
    return np.stack([a, b, c], axis=-1)


# ----------------------------------------------------------------------------------------
# tileable materials
# ----------------------------------------------------------------------------------------
def tex_plaster():
    """Weathered lime plaster (near-white; per-house colour comes from vertex colour)."""
    lo = pnoise(N, 3.0, 1)
    mid = pnoise(N, 2.2, 2)
    fine = pnoise(N, 0.8, 3)
    streak = pnoise(N, 2.6, 4, aniso=(1.0, 0.08))  # vertical rain streaks
    v = 0.86 + (lo - 0.5) * 0.10 + (mid - 0.5) * 0.06 + (fine - 0.5) * 0.05
    v -= np.clip(streak - 0.55, 0, 1) * 0.35
    # mould/dirt blotches
    blot = pnoise(N, 2.8, 5)
    v -= np.clip(blot - 0.68, 0, 1) * 0.6
    # patches of fresher lime wash
    patch = pnoise(N, 3.2, 6)
    v += np.clip(patch - 0.72, 0, 1) * 0.35
    r = v * 1.00
    g = v * 0.985
    b = v * 0.955
    img = to_img(rgb(r, g, b))
    d = ImageDraw.Draw(img)
    # hairline cracks (drawn with wrap-around)
    for i in range(14):
        x, y = random.uniform(0, N), random.uniform(0, N)
        ang = random.uniform(0, math.tau)
        for s in range(random.randint(20, 60)):
            ang += random.uniform(-0.5, 0.5)
            nx, ny = x + math.cos(ang) * 6, y + math.sin(ang) * 6
            for ox in (-N, 0, N):
                for oy in (-N, 0, N):
                    d.line([(x + ox, y + oy), (nx + ox, ny + oy)], fill=(120, 115, 105), width=1)
            x, y = nx % N, ny % N
    return img


def tex_roof():
    """Canton-style V-profile clay tiles. u = across the slope, v = down the slope.
    Texture spans 1.2 m x 1.2 m: 6 channels (pan + cover), 5 overlap courses."""
    H = W = N
    img = np.zeros((H, W, 3))
    ch = W // 6
    courses = 5
    ch_h = H // courses
    var = pnoise(N, 2.5, 11)
    grime = pnoise(N, 2.0, 12)
    lich = pnoise(N, 1.6, 13)
    xs = np.arange(W)
    ys = np.arange(H)
    X, Y = np.meshgrid(xs, ys)
    cx = (X % ch) / ch  # 0..1 across channel
    # cover tile occupies centre 45% (convex), pan the rest (concave)
    cover = np.abs(cx - 0.5) < 0.22
    t_cov = np.clip(1 - ((cx - 0.5) / 0.22) ** 2, 0, 1)
    t_pan = np.clip(np.abs(cx - 0.5) / 0.5, 0, 1)
    shade = np.where(cover, 0.62 + 0.38 * np.sqrt(t_cov), 0.35 + 0.35 * (1 - t_pan) * 0 + 0.25 * t_pan)
    # course overlap: tiles lap every ch_h; bottom edge of each course casts a shadow band
    cy = (Y % ch_h) / ch_h
    lap = np.clip((cy - 0.86) / 0.14, 0, 1)
    shade *= 1 - 0.45 * lap
    shade *= 0.92 + 0.16 * (cy)  # slight gradient per tile
    # per-tile colour variation
    tile_id = (X // ch) * 31 + (Y // ch_h) * 17 + cover.astype(int) * 7
    r = np.random.default_rng(99)
    tv = r.uniform(0.82, 1.12, size=tile_id.max() + 1)[tile_id]
    base_r = 0.66 * tv
    base_g = 0.36 * tv * (0.95 + 0.1 * var)
    base_b = 0.24 * tv
    R = base_r * shade
    G = base_g * shade
    B = base_b * shade
    # soot / grime and lichen
    gm = np.clip(grime - 0.45, 0, 1) * 0.9
    R = R * (1 - gm) + 0.18 * gm
    G = G * (1 - gm) + 0.17 * gm
    B = B * (1 - gm) + 0.15 * gm
    lm = np.clip(lich - 0.7, 0, 1) * 1.2
    R = R * (1 - lm) + 0.45 * lm * shade
    G = G * (1 - lm) + 0.44 * lm * shade
    B = B * (1 - lm) + 0.33 * lm * shade
    return to_img(rgb(R, G, B))


def tex_timber():
    """Painted timber boards, weathered. Light neutral so vertex colour gives the paint."""
    grain = pnoise(N, 1.8, 21, aniso=(1.0, 0.05))
    fine = pnoise(N, 0.8, 22)
    chip = pnoise(N, 2.4, 23)
    v = 0.80 + (grain - 0.5) * 0.18 + (fine - 0.5) * 0.06
    X = np.arange(N)[None, :].repeat(N, 0)
    board = (X % (N // 8))
    v *= np.where(board < 3, 0.55, 1.0)
    # worn paint: soft, low-contrast patches (earlier hard dark-red chips read as stains)
    wear = np.clip((chip - 0.66) / 0.12, 0, 1) * 0.22
    r = v * (1 - wear * 0.9)
    g = v * 0.98 * (1 - wear)
    b = v * 0.94 * (1 - wear * 1.1)
    return to_img(rgb(r, g, b))


def tex_floor():
    """Five-foot-way floor: 300 mm clay tiles (4x4 over 1.2 m), worn, with grout."""
    X, Y = np.meshgrid(np.arange(N), np.arange(N))
    t = N // 4
    gx = (X % t)
    gy = (Y % t)
    grout = (gx < 6) | (gy < 6)
    wear = pnoise(N, 2.2, 31)
    fine = pnoise(N, 0.9, 32)
    r = np.random.default_rng(5)
    tv = r.uniform(0.85, 1.1, size=(16,))[((X // t) % 4) * 4 + (Y // t) % 4]
    v = (0.80 + (fine - 0.5) * 0.12) * tv
    v -= np.clip(wear - 0.6, 0, 1) * 0.4
    edge = np.minimum(np.minimum(gx, t - gx), np.minimum(gy, t - gy))
    v *= np.clip(0.85 + edge / 40.0, 0, 1)
    v = np.where(grout, 0.42 + fine * 0.1, v)
    R = v * 1.0
    G = v * 0.93
    B = v * 0.86
    return to_img(rgb(R, G, B))


def tex_road():
    """Tarred road with aggregate, patches, cracks (mid grey; tinted by vertex colour)."""
    lo = pnoise(N, 2.8, 41)
    mid = pnoise(N, 1.6, 42)
    fine = pnoise(N, 0.2, 43)
    v = 0.62 + (lo - 0.5) * 0.18 + (mid - 0.5) * 0.10 + (fine - 0.5) * 0.18
    patch = pnoise(N, 3.4, 44)
    v = np.where(patch > 0.72, v * 0.86, v)  # darker tar patches
    dust = pnoise(N, 2.2, 45)
    v += np.clip(dust - 0.6, 0, 1) * 0.35
    R = v * 1.0
    G = v * 0.97
    B = v * 0.92
    img = to_img(rgb(R, G, B))
    d = ImageDraw.Draw(img)
    for i in range(18):
        x, y = random.uniform(0, N), random.uniform(0, N)
        ang = random.uniform(0, math.tau)
        for s in range(random.randint(15, 45)):
            ang += random.uniform(-0.7, 0.7)
            nx, ny = x + math.cos(ang) * 8, y + math.sin(ang) * 8
            for ox in (-N, 0, N):
                for oy in (-N, 0, N):
                    d.line([(x + ox, y + oy), (nx + ox, ny + oy)], fill=(70, 68, 64), width=2)
            x, y = nx % N, ny % N
    return img


def tex_sandbag():
    """Hessian sack, one bag per texture: weave + seam + fold wrinkles."""
    X, Y = np.meshgrid(np.arange(N), np.arange(N))
    weave = (np.sin(X * math.tau / 8.0) * np.sin(Y * math.tau / 8.0)) * 0.5 + 0.5
    fine = pnoise(N, 0.6, 51)
    wr = pnoise(N, 2.4, 52, aniso=(0.3, 1.0))
    dirt = pnoise(N, 2.4, 53)
    v = 0.72 + (weave - 0.5) * 0.12 + (fine - 0.5) * 0.1 + (wr - 0.5) * 0.25
    v -= np.clip(dirt - 0.55, 0, 1) * 0.5
    # tied seam near one end + edges darker (curvature)
    u = X / N
    w = Y / N
    v *= 0.75 + 0.25 * np.sin(np.clip(w, 0, 1) * math.pi) ** 0.5
    v *= np.where(np.abs(u - 0.9) < 0.012, 0.6, 1.0)
    R = v * 0.76
    G = v * 0.69
    B = v * 0.56
    return to_img(rgb(R, G, B))


def tex_brick():
    """Brick, 4 bricks x 10 courses over 0.96 m x 0.80 m (stretcher bond)."""
    X, Y = np.meshgrid(np.arange(N), np.arange(N))
    cw = N / 4.0
    chh = N / 10.0
    row = (Y // chh).astype(int)
    xo = (X + (row % 2) * cw / 2) % N
    bx = (xo % cw)
    by = (Y % chh)
    mortar = (bx < 7) | (by < 7)
    bid = ((xo // cw).astype(int) + row * 5)
    r = np.random.default_rng(7)
    tv = r.uniform(0.75, 1.15, size=bid.max() + 1)[bid]
    hue = r.uniform(-0.06, 0.06, size=bid.max() + 1)[bid]
    fine = pnoise(N, 1.0, 61)
    soot = pnoise(N, 2.4, 62)
    R = (0.56 + hue) * tv * (0.9 + fine * 0.2)
    G = 0.36 * tv * (0.9 + fine * 0.2)
    B = 0.28 * tv * (0.9 + fine * 0.2)
    m = 0.62 + fine * 0.1
    R = np.where(mortar, m, R)
    G = np.where(mortar, m * 0.96, G)
    B = np.where(mortar, m * 0.9, B)
    s = np.clip(soot - 0.55, 0, 1) * 0.8
    R, G, B = R * (1 - s), G * (1 - s), B * (1 - s)
    return to_img(rgb(R, G, B))


def tex_cloth():
    """Fine cotton weave, near white (tinted per garment / awning / lantern)."""
    X, Y = np.meshgrid(np.arange(N), np.arange(N))
    weave = (np.sin(X * math.tau / 4.0) + np.sin(Y * math.tau / 4.0)) * 0.25 + 0.5
    fine = pnoise(N, 1.2, 71)
    fold = pnoise(N, 2.6, 72, aniso=(1.0, 0.25))
    v = 0.86 + (weave - 0.5) * 0.06 + (fine - 0.5) * 0.08 + (fold - 0.5) * 0.14
    return to_img(rgb(v, v * 0.985, v * 0.96))


# ----------------------------------------------------------------------------------------
# drawing helpers for atlases (drawn at 1024 base resolution)
# ----------------------------------------------------------------------------------------
def shade_rect(d, box, fill, edge_dark=0.7, edge_light=1.15, w=3):
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=fill)
    dk = tuple(int(c * edge_dark) for c in fill)
    lt = tuple(min(255, int(c * edge_light)) for c in fill)
    d.line([(x0, y1), (x1, y1)], fill=dk, width=w)
    d.line([(x1, y0), (x1, y1)], fill=dk, width=w)
    d.line([(x0, y0), (x1, y0)], fill=lt, width=w)
    d.line([(x0, y0), (x0, y1)], fill=lt, width=w)


FRAME = (228, 224, 212)      # neutral light (vertex colour tints)
FRAME_DK = (150, 146, 136)
GLASS = (46, 58, 66)
GLASS_HI = (86, 100, 108)
TAPE = (222, 212, 180)
DARK = (22, 20, 18)


def louvre_leaf(d, box, n=None):
    x0, y0, x1, y1 = box
    shade_rect(d, box, FRAME)
    m = 12
    inner = (x0 + m, y0 + m, x1 - m, y1 - m)
    d.rectangle(inner, fill=FRAME_DK)
    h = inner[3] - inner[1]
    n = n or int(h / 14)
    step = h / n
    for i in range(n):
        yy = inner[1] + i * step
        d.rectangle((inner[0], yy, inner[2], yy + step * 0.62), fill=FRAME)
        d.line([(inner[0], yy + step * 0.62), (inner[2], yy + step * 0.62)], fill=(90, 86, 80), width=2)
    # middle rail
    my = (y0 + y1) // 2
    shade_rect(d, (x0 + 4, my - 8, x1 - 4, my + 8), FRAME)


def glazed_leaf(d, box, tape=True, cols=2, rows=4):
    x0, y0, x1, y1 = box
    shade_rect(d, box, FRAME)
    m = 10
    ix0, iy0, ix1, iy1 = x0 + m, y0 + m, x1 - m, y1 - m
    pw = (ix1 - ix0) / cols
    ph = (iy1 - iy0) / rows
    for c in range(cols):
        for r in range(rows):
            px0 = ix0 + c * pw + 3
            py0 = iy0 + r * ph + 3
            px1 = ix0 + (c + 1) * pw - 3
            py1 = iy0 + (r + 1) * ph - 3
            d.rectangle((px0, py0, px1, py1), fill=GLASS)
            d.line([(px0 + 4, py1 - 6), (px1 - 8, py0 + 4)], fill=GLASS_HI, width=2)
            if tape:
                d.line([(px0, py0), (px1, py1)], fill=TAPE, width=5)
                d.line([(px0, py1), (px1, py0)], fill=TAPE, width=5)


def panel_leaf(d, box, panels=3):
    x0, y0, x1, y1 = box
    shade_rect(d, box, FRAME)
    m = 14
    ph = (y1 - y0 - m * (panels + 1)) / panels
    for i in range(panels):
        py = y0 + m + i * (ph + m)
        shade_rect(d, (x0 + m, py, x1 - m, py + ph), (208, 204, 192), edge_dark=1.15, edge_light=0.7, w=4)


def window_atlas():
    img = Image.new("RGB", (N, N), (200, 196, 186))
    d = ImageDraw.Draw(img)
    cw, chh = 256, 512
    cells = []
    for row in range(2):
        for col in range(4):
            cells.append((col * cw, row * chh, (col + 1) * cw, (row + 1) * chh))

    def frame(c):
        x0, y0, x1, y1 = c
        d.rectangle(c, fill=FRAME_DK)
        return (x0 + 8, y0 + 8, x1 - 8, y1 - 8)

    # W0 louvred jalousie closed
    c = frame(cells[0]); mx = (c[0] + c[2]) // 2
    louvre_leaf(d, (c[0], c[1], mx, c[3])); louvre_leaf(d, (mx, c[1], c[2], c[3]))
    # W1 one leaf open -> interior darkness + inner taped glass leaf
    c = frame(cells[1]); mx = (c[0] + c[2]) // 2
    d.rectangle(c, fill=DARK)
    glazed_leaf(d, (mx, c[1], c[2], c[3]), tape=True, cols=1, rows=5)
    d.rectangle((c[0], c[1], c[0] + 30, c[3]), fill=FRAME)  # open leaf edge-on
    for y in range(c[1], c[3], 14):
        d.line([(c[0], y), (c[0] + 30, y)], fill=FRAME_DK, width=3)
    # W2 French glazed, taped
    c = frame(cells[2]); mx = (c[0] + c[2]) // 2
    glazed_leaf(d, (c[0], c[1], mx, c[3]), True, 2, 5); glazed_leaf(d, (mx, c[1], c[2], c[3]), True, 2, 5)
    # W3 panelled shutters closed
    c = frame(cells[3]); mx = (c[0] + c[2]) // 2
    panel_leaf(d, (c[0], c[1], mx, c[3]), 3); panel_leaf(d, (mx, c[1], c[2], c[3]), 3)
    # W4 pintu pagar (half-height swing doors) in front of dark doorway
    c = frame(cells[4]); mx = (c[0] + c[2]) // 2
    d.rectangle(c, fill=(30, 26, 22))
    # far main door leaves open inward (lighter strips at sides)
    d.rectangle((c[0], c[1], c[0] + 26, c[3]), fill=(120, 90, 60))
    d.rectangle((c[2] - 26, c[1], c[2], c[3]), fill=(120, 90, 60))
    ph0 = c[1] + int((c[3] - c[1]) * 0.35)
    ph1 = c[1] + int((c[3] - c[1]) * 0.88)
    for (a, b) in ((c[0] + 6, mx - 2), (mx + 2, c[2] - 6)):
        shade_rect(d, (a, ph0, b, ph1), FRAME)
        # carved top (fretwork) + lower panel
        for k in range(5):
            xx = a + 10 + k * (b - a - 20) / 4
            d.line([(xx, ph0 + 10), (xx, ph0 + 90)], fill=FRAME_DK, width=5)
        d.arc((a + 8, ph0 - 30, b - 8, ph0 + 60), 200, 340, fill=FRAME_DK, width=5)
        shade_rect(d, (a + 12, ph0 + 110, b - 12, ph1 - 14), (206, 202, 190), 1.15, 0.7, 4)
    # W5 blackout: glazed window with dark cloth pinned over
    c = frame(cells[5]); mx = (c[0] + c[2]) // 2
    glazed_leaf(d, (c[0], c[1], mx, c[3]), True, 2, 5); glazed_leaf(d, (mx, c[1], c[2], c[3]), True, 2, 5)
    cl = (c[0] + 18, c[1] + 14, c[2] - 18, c[3] - 60)
    d.rectangle(cl, fill=(28, 30, 34))
    for k in range(9):
        xx = cl[0] + k * (cl[2] - cl[0]) / 8
        d.line([(xx, cl[1]), (xx + random.uniform(-6, 6), cl[3])], fill=(40, 42, 48), width=4)
    d.polygon([(cl[0], cl[3]), (cl[2], cl[3]), (cl[2] - 20, cl[3] + 30), (cl[0] + 30, cl[3] + 18)], fill=(34, 36, 40))
    # W6 panelled main double door, closed, with a door knocker ring
    c = frame(cells[6]); mx = (c[0] + c[2]) // 2
    panel_leaf(d, (c[0], c[1], mx, c[3]), 4); panel_leaf(d, (mx, c[1], c[2], c[3]), 4)
    for xx in (mx - 18, mx + 18):
        d.ellipse((xx - 9, c[1] + 230, xx + 9, c[1] + 248), outline=(60, 50, 30), width=3)
    # W7 open dark doorway / shop interior hint
    c = frame(cells[7])
    d.rectangle(c, fill=(26, 22, 18))
    d.rectangle((c[0] + 20, c[1] + 330, c[2] - 20, c[1] + 420), fill=(52, 40, 28))  # counter
    d.rectangle((c[0] + 20, c[1] + 80, c[2] - 20, c[1] + 90), fill=(46, 36, 26))
    d.rectangle((c[0] + 20, c[1] + 170, c[2] - 20, c[1] + 180), fill=(46, 36, 26))
    for k in range(10):
        xx = c[0] + 30 + k * 18
        d.rectangle((xx, c[1] + 50, xx + 12, c[1] + 80), fill=(70, 60, 44))
        d.rectangle((xx, c[1] + 140, xx + 12, c[1] + 170), fill=(64, 56, 40))
    return img


def details_atlas():
    img = Image.new("RGB", (N, N), (200, 196, 186))
    d = ImageDraw.Draw(img)
    s = 256

    def cell(i):
        return ((i % 4) * s, (i // 4) * s, (i % 4 + 1) * s, (i // 4 + 1) * s)

    # 0 fanlight: semicircle, radial glazing bars, taped
    x0, y0, x1, y1 = cell(0)
    d.rectangle((x0, y0, x1, y1), fill=FRAME)
    d.pieslice((x0 + 8, y0 + 8, x1 - 8, y1 + s - 8), 180, 360, fill=GLASS)
    cx, cy = (x0 + x1) / 2, y1 - 4
    for k in range(7):
        a = math.pi + k * math.pi / 6
        d.line([(cx, cy), (cx + math.cos(a) * 124, cy + math.sin(a) * 124)], fill=FRAME, width=7)
    d.arc((x0 + 8, y0 + 8, x1 - 8, y1 + s - 8), 180, 360, fill=FRAME, width=10)
    d.arc((x0 + 60, y0 + 60, x1 - 60, y1 + s - 60), 180, 360, fill=FRAME, width=6)
    d.line([(x0 + 40, y0 + 120), (x1 - 40, y1 - 20)], fill=TAPE, width=5)
    d.line([(x1 - 40, y0 + 120), (x0 + 40, y1 - 20)], fill=TAPE, width=5)
    # 1 ground-floor casement with iron bars, taped glass
    x0, y0, x1, y1 = cell(1)
    glazed_leaf(d, (x0, y0, (x0 + x1) // 2, y1), True, 1, 3)
    glazed_leaf(d, ((x0 + x1) // 2, y0, x1, y1), True, 1, 3)
    for k in range(7):
        xx = x0 + 18 + k * 37
        d.rectangle((xx, y0, xx + 6, y1), fill=(40, 40, 42))
    # 2 decorative tile panel (muted majolica-like, original pattern)
    x0, y0, x1, y1 = cell(2)
    t = 64
    pal = [(150, 170, 150), (196, 176, 120), (120, 140, 160), (180, 120, 100)]
    for i in range(4):
        for j in range(4):
            tx, ty = x0 + i * t, y0 + j * t
            d.rectangle((tx, ty, tx + t, ty + t), fill=(214, 206, 186))
            d.ellipse((tx + 10, ty + 10, tx + t - 10, ty + t - 10), outline=pal[(i + j) % 2], width=6)
            d.polygon([(tx + t / 2, ty + 18), (tx + t - 18, ty + t / 2), (tx + t / 2, ty + t - 18), (tx + 18, ty + t / 2)], fill=pal[2 + (i * j) % 2])
            for (qx, qy) in ((tx, ty), (tx + t, ty), (tx, ty + t), (tx + t, ty + t)):
                d.pieslice((qx - 14, qy - 14, qx + 14, qy + 14), 0, 360, fill=pal[1])
            d.rectangle((tx, ty, tx + t, ty + t), outline=(170, 162, 146), width=2)
    # 3 marble
    x0, y0, x1, y1 = cell(3)
    mb = pnoise(s, 2.6, 81)
    mb2 = pnoise(s, 2.2, 82)
    v = 0.90 - np.exp(-np.abs(mb - 0.5) * 60) * 0.32 - np.exp(-np.abs(mb2 - 0.45) * 90) * 0.18
    v += (pnoise(s, 1.0, 83) - 0.5) * 0.05
    m = to_img(rgb(v, v * 0.99, v * 0.97))
    img.paste(m, (x0, y0))
    # 4 timber plank shopfront (removable planks, numbered)
    x0, y0, x1, y1 = cell(4)
    f = font(FONT_TC, 22)
    nums = "一二三四五六七八"
    pw = s / 8
    for k in range(8):
        px = x0 + k * pw
        shade_rect(d, (px, y0, px + pw, y1), (196, 186, 170), 0.6, 1.1, 3)
        d.text((px + pw / 2 - 11, y0 + 40), nums[k], font=f, fill=(150, 40, 30))
    d.rectangle((x0, y0 + 110, x1, y0 + 122), fill=(90, 80, 70))  # iron bar across
    # 5 rattan / bamboo chick blind
    x0, y0, x1, y1 = cell(5)
    d.rectangle((x0, y0, x1, y1), fill=(40, 34, 26))
    for yy in range(y0, y1, 6):
        c = random.randint(170, 200)
        d.rectangle((x0, yy, x1, yy + 4), fill=(c, int(c * 0.86), int(c * 0.6)))
    for xx in (x0 + 40, x0 + 128, x1 - 40):
        d.line([(xx, y0), (xx, y1)], fill=(110, 80, 50), width=3)
    # 6 vent grille (geometric / bat-like motif)
    x0, y0, x1, y1 = cell(6)
    d.rectangle((x0, y0, x1, y1), fill=FRAME)
    d.rectangle((x0 + 20, y0 + 60, x1 - 20, y1 - 60), fill=(40, 36, 32))
    for k in range(5):
        cx = x0 + 44 + k * 42
        d.polygon([(cx - 18, y0 + 128), (cx, y0 + 80), (cx + 18, y0 + 128), (cx, y0 + 176)], fill=FRAME)
    # 7 medicine drawer cabinet (百子櫃)
    x0, y0, x1, y1 = cell(7)
    d.rectangle((x0, y0, x1, y1), fill=(92, 54, 34))
    fs = font(FONT_TC, 12)
    herbs = "當歸黨參枸杞川芎白朮甘草熟地黃芪茯苓陳皮桂枝杏仁"
    k = 0
    for j in range(7):
        for i in range(8):
            bx, by = x0 + 6 + i * 31, y0 + 6 + j * 35
            shade_rect(d, (bx, by, bx + 28, by + 32), (128, 78, 46), 0.7, 1.2, 2)
            d.rectangle((bx + 8, by + 4, bx + 20, by + 16), fill=(220, 206, 170))
            d.text((bx + 8, by + 3), herbs[k % len(herbs)], font=fs, fill=(30, 20, 10))
            d.ellipse((bx + 11, by + 22, bx + 17, by + 28), fill=(200, 170, 80))
            k += 1
    # 8 cloth bolts shelf (tailor)
    x0, y0, x1, y1 = cell(8)
    d.rectangle((x0, y0, x1, y1), fill=(60, 44, 30))
    cols = [(60, 60, 70), (170, 160, 140), (90, 70, 50), (120, 120, 110), (40, 44, 60), (200, 196, 180), (110, 60, 50)]
    for j in range(4):
        d.rectangle((x0, y0 + j * 64 + 58, x1, y0 + j * 64 + 64), fill=(96, 72, 48))
        for i in range(8):
            c = random.choice(cols)
            d.rectangle((x0 + 4 + i * 31, y0 + j * 64 + 8, x0 + 32 + i * 31, y0 + j * 64 + 58), fill=c)
            d.line([(x0 + 4 + i * 31, y0 + j * 64 + 30), (x0 + 32 + i * 31, y0 + j * 64 + 30)], fill=tuple(int(q * 0.8) for q in c), width=2)
    # 9 provision shelves (tins, jars, sacks)
    x0, y0, x1, y1 = cell(9)
    d.rectangle((x0, y0, x1, y1), fill=(58, 44, 30))
    for j in range(4):
        d.rectangle((x0, y0 + j * 64 + 58, x1, y0 + j * 64 + 64), fill=(100, 76, 50))
        i = 0
        x = x0 + 4
        while x < x1 - 20:
            wdt = random.randint(14, 30)
            kind = random.random()
            if kind < 0.5:
                c = random.choice([(170, 40, 30), (200, 170, 60), (60, 90, 130), (190, 190, 180)])
                d.rectangle((x, y0 + j * 64 + 26, x + wdt, y0 + j * 64 + 58), fill=c)
                d.rectangle((x, y0 + j * 64 + 36, x + wdt, y0 + j * 64 + 46), fill=(230, 220, 190))
            else:
                d.rectangle((x, y0 + j * 64 + 16, x + wdt, y0 + j * 64 + 58), fill=(120, 130, 120))
                d.rectangle((x + 2, y0 + j * 64 + 26, x + wdt - 2, y0 + j * 64 + 56), fill=(170, 120, 60))
            x += wdt + 4
    # 10 crate side with stencil (hoarded tins)
    x0, y0, x1, y1 = cell(10)
    for k in range(4):
        shade_rect(d, (x0, y0 + k * 64, x1, y0 + (k + 1) * 64), (178, 150, 110), 0.7, 1.1, 3)
    fo = font(FONT_ROCK, 40)
    d.text((x0 + 20, y0 + 70), "SARDINES", font=fo, fill=(50, 40, 30))
    d.text((x0 + 60, y0 + 130), "48 TINS", font=font(FONT_ROCK, 28), fill=(50, 40, 30))
    # 11 checked cloth bundle (buntil / kain)
    x0, y0, x1, y1 = cell(11)
    for i in range(16):
        for j in range(16):
            c = (150, 40, 40) if (i + j) % 2 == 0 else (220, 200, 160)
            if i % 4 == 0 or j % 4 == 0:
                c = (40, 60, 110)
            d.rectangle((x0 + i * 16, y0 + j * 16, x0 + i * 16 + 16, y0 + j * 16 + 16), fill=c)
    # 12 suitcase / rattan trunk
    x0, y0, x1, y1 = cell(12)
    d.rectangle((x0, y0, x1, y1), fill=(112, 70, 42))
    for k in range(0, 256, 8):
        d.line([(x0, y0 + k), (x1, y0 + k)], fill=(96, 60, 36), width=1)
    d.rectangle((x0, y0 + 60, x1, y0 + 74), fill=(70, 44, 26))
    d.rectangle((x0, y0 + 180, x1, y0 + 194), fill=(70, 44, 26))
    for xx in (x0 + 50, x1 - 70):
        d.rectangle((xx, y0 + 110, xx + 20, y0 + 140), fill=(190, 170, 110))
    # 13 kopitiam price board (black board, gold text)
    x0, y0, x1, y1 = cell(13)
    d.rectangle((x0, y0, x1, y1), fill=(24, 22, 20))
    d.rectangle((x0 + 6, y0 + 6, x1 - 6, y1 - 6), outline=(180, 150, 70), width=4)
    fb = font(FONT_TC, 30)
    fs2 = font(FONT_GILL, 16)
    items = [("咖啡", "KOPI  4 CTS"), ("咖啡烏", "KOPI-O  3 CTS"), ("紅茶", "TEH  4 CTS"), ("麵包", "ROTI  5 CTS")]
    for k, (zh, en) in enumerate(items):
        d.text((x0 + 18, y0 + 18 + k * 58), zh, font=fb, fill=(210, 180, 90))
        d.text((x0 + 120, y0 + 28 + k * 58), en, font=fs2, fill=(200, 196, 180))
    # 14 wall clock (left) + calendar (right)
    x0, y0, x1, y1 = cell(14)
    d.rectangle((x0, y0, x1, y1), fill=(210, 204, 190))
    d.rectangle((x0 + 4, y0 + 4, x0 + 124, y1 - 4), fill=(92, 58, 32))
    d.ellipse((x0 + 14, y0 + 20, x0 + 114, y0 + 120), fill=(236, 230, 210), outline=(40, 30, 20), width=3)
    for h in range(12):
        a = h / 12 * math.tau
        d.line([(x0 + 64 + math.sin(a) * 40, y0 + 70 - math.cos(a) * 40), (x0 + 64 + math.sin(a) * 46, y0 + 70 - math.cos(a) * 46)], fill=(20, 20, 20), width=3)
    d.line([(x0 + 64, y0 + 70), (x0 + 64, y0 + 36)], fill=(20, 20, 20), width=3)
    d.line([(x0 + 64, y0 + 70), (x0 + 88, y0 + 84)], fill=(20, 20, 20), width=4)
    d.rectangle((x0 + 50, y0 + 140, x0 + 78, y0 + 230), fill=(60, 40, 22))  # pendulum case
    d.ellipse((x0 + 54, y0 + 200, x0 + 74, y0 + 220), fill=(200, 170, 80))
    # calendar: red header, grid
    d.rectangle((x0 + 136, y0 + 10, x1 - 8, y1 - 10), fill=(236, 228, 206))
    d.rectangle((x0 + 136, y0 + 10, x1 - 8, y0 + 70), fill=(170, 40, 34))
    d.text((x0 + 150, y0 + 20), "壬午年", font=font(FONT_TC, 28), fill=(240, 210, 120))
    d.text((x0 + 150, y0 + 80), "FEB 1942", font=font(FONT_GILL, 18), fill=(30, 30, 30))
    for r in range(5):
        for c in range(5):
            d.rectangle((x0 + 146 + c * 20, y0 + 108 + r * 24, x0 + 160 + c * 20, y0 + 124 + r * 24), fill=(70, 70, 70) if (r * 5 + c) != 13 else (180, 30, 30))
    # 15 carved panel door / screen (pawnshop 當 screen)
    x0, y0, x1, y1 = cell(15)
    d.rectangle((x0, y0, x1, y1), fill=(40, 60, 50))
    d.rectangle((x0 + 12, y0 + 12, x1 - 12, y1 - 12), outline=(190, 160, 80), width=5)
    fbig = font(FONT_TC, 170)
    d.text((x0 + 42, y0 + 20), "當", font=fbig, fill=(200, 170, 80))
    return img


def fit_text(d, box, text, spec, fill, max_size=200, vertical=False, pad=0.08):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    if vertical:
        n = len(text)
        size = int(min(w * (1 - 2 * pad), h * (1 - 2 * pad) / max(n, 1)))
        size = min(size, max_size)
        f = font(spec, size)
        total = n * size
        yy = y0 + (h - total) / 2
        for ch in text:
            bb = d.textbbox((0, 0), ch, font=f)
            cw = bb[2] - bb[0]
            d.text((x0 + (w - cw) / 2 - bb[0], yy - bb[1] + (size - (bb[3] - bb[1])) / 2), ch, font=f, fill=fill)
            yy += size
        return
    size = max_size
    while size > 6:
        f = font(spec, size)
        bb = d.textbbox((0, 0), text, font=f)
        if bb[2] - bb[0] <= w * (1 - 2 * pad) and bb[3] - bb[1] <= h * (1 - 2 * pad):
            break
        size -= 2
    bb = d.textbbox((0, 0), text, font=f)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    d.text((x0 + (w - tw) / 2 - bb[0], y0 + (h - th) / 2 - bb[1]), text, font=f, fill=fill)


# ---- shop signage: shared with the build script (index -> meaning) ----
PLAQUES = [
    # (chinese, romanised, bg, fg)
    ("福記咖啡店", "HOCK KEE  KEDAI KOPI", (22, 20, 18), (214, 178, 84)),        # 0 kopitiam (Ah Ma)
    ("濟生堂藥材", "CHOP CHEE SENG TONG  MEDICAL HALL", (20, 22, 20), (210, 176, 80)),  # 1 medical hall (DROP_1)
    ("美華洋服", "MEI HUA TAILOR  TUKANG JAHIT", (120, 26, 22), (224, 190, 96)),  # 2 tailor (DROP_2)
    ("南豐號", "CHOP NAM HONG  PROVISIONS  KEDAI RUNCIT", (24, 22, 20), (216, 182, 90)),  # 3 provision (DROP_3)
    ("金寶金莊", "KIM POH GOLDSMITH", (130, 24, 20), (230, 196, 100)),            # 4 goldsmith
    ("光華影相館", "KONG HWA PHOTO STUDIO", (28, 36, 30), (220, 206, 170)),       # 5 photo studio
    ("大信當", "TAI SIN PAWNSHOP", (22, 20, 18), (206, 170, 76)),                 # 6 pawnshop
    ("三陽茶莊", "SAM YEONG TEA MERCHANT", (196, 162, 76), (30, 24, 18)),         # 7 tea
    ("順發米行", "SOON HUAT RICE DEALER", (24, 22, 20), (210, 176, 84)),          # 8 rice
    ("和利木屐", "WOH LEE CLOGS & RATTAN", (110, 30, 24), (226, 192, 100)),       # 9 clogs
    ("聯興客棧", "LIAN HENG LODGING HOUSE", (24, 30, 40), (210, 190, 140)),       # 10 lodging
    ("義安單車", "GEE AN BICYCLES", (22, 20, 18), (214, 180, 86)),                # 11 bicycles
]
VBOARDS = [
    ("咖啡茶點", (22, 20, 18), (214, 178, 84)),      # 0 kopitiam
    ("參茸藥材", (20, 22, 20), (210, 176, 80)),      # 1 medical
    ("丸散膏丹", (20, 22, 20), (210, 176, 80)),      # 2 medical
    ("中西洋服", (120, 26, 22), (224, 190, 96)),     # 3 tailor
    ("精工裁剪", (120, 26, 22), (224, 190, 96)),     # 4 tailor
    ("油糖米糧", (24, 22, 20), (216, 182, 90)),      # 5 provision
    ("南北貨品", (24, 22, 20), (216, 182, 90)),      # 6 provision
    ("金銀首飾", (130, 24, 20), (230, 196, 100)),    # 7 gold
    ("專影人像", (28, 36, 30), (220, 206, 170)),     # 8 photo
    ("當", (22, 20, 18), (206, 170, 76)),            # 9 pawn
    ("名茶", (196, 162, 76), (30, 24, 18)),          # 10 tea
    ("新春大吉", (178, 34, 30), (30, 24, 20)),       # 11 CNY couplet
    ("萬事如意", (178, 34, 30), (30, 24, 20)),       # 12 CNY couplet
    ("出入平安", (178, 34, 30), (30, 24, 20)),       # 13 CNY couplet (poignant)
    ("國泰民安", (178, 34, 30), (30, 24, 20)),       # 14 CNY couplet
    ("客棧", (24, 30, 40), (210, 190, 140)),         # 15 lodging
]
SIGN_PLAQUE_RECT = lambda i: ((i % 2) * 512, (i // 2) * 112, (i % 2) * 512 + 512, (i // 2) * 112 + 112)
SIGN_VBOARD_RECT = lambda i: (i * 64, 672, i * 64 + 64, 960)
SIGN_SMALL = {
    "arp": (0, 960, 256, 1024),
    "shelter": (256, 960, 576, 1024),
    "date1936": (576, 960, 704, 1024),
    "date1938": (704, 960, 832, 1024),
    "fu": (832, 960, 896, 1024),
    "houseno": (896, 960, 1024, 1024),
}


def signs_atlas():
    img = Image.new("RGB", (N, N), (30, 28, 26))
    d = ImageDraw.Draw(img)
    for i, (zh, en, bg, fg) in enumerate(PLAQUES):
        x0, y0, x1, y1 = SIGN_PLAQUE_RECT(i)
        d.rectangle((x0, y0, x1 - 1, y1 - 1), fill=bg)
        # carved border + weathering
        d.rectangle((x0 + 5, y0 + 5, x1 - 6, y1 - 6), outline=fg, width=3)
        d.rectangle((x0 + 11, y0 + 11, x1 - 12, y1 - 12), outline=tuple(int(c * 0.7) for c in fg), width=1)
        fit_text(d, (x0 + 14, y0 + 8, x1 - 14, y0 + 84), zh, FONT_TC, fg, max_size=74, pad=0.03)
        fit_text(d, (x0 + 30, y0 + 82, x1 - 30, y1 - 10), en, FONT_COPPER, fg, max_size=18, pad=0.02)
    for i, (zh, bg, fg) in enumerate(VBOARDS):
        x0, y0, x1, y1 = SIGN_VBOARD_RECT(i)
        d.rectangle((x0 + 1, y0, x1 - 2, y1 - 1), fill=bg)
        d.rectangle((x0 + 4, y0 + 4, x1 - 5, y1 - 5), outline=fg, width=2)
        fit_text(d, (x0 + 4, y0 + 8, x1 - 4, y1 - 8), zh, FONT_TC, fg, max_size=56, vertical=True, pad=0.06)
    # small signs
    x0, y0, x1, y1 = SIGN_SMALL["arp"]
    d.rectangle((x0, y0, x1 - 1, y1 - 1), fill=(236, 232, 220))
    d.rectangle((x0 + 3, y0 + 3, x1 - 4, y1 - 4), outline=(20, 20, 20), width=3)
    fit_text(d, (x0 + 8, y0 + 4, x1 - 8, y0 + 42), "A.R.P. WARDENS' POST", FONT_GILL, (20, 20, 20), 34, pad=0.02)
    fit_text(d, (x0 + 8, y0 + 40, x1 - 8, y1 - 4), "No. 14   防空站", FONT_TC, (170, 30, 26), 20, pad=0.02)
    x0, y0, x1, y1 = SIGN_SMALL["shelter"]
    d.rectangle((x0, y0, x1 - 1, y1 - 1), fill=(20, 20, 20))
    fit_text(d, (x0 + 8, y0 + 2, x1 - 8, y0 + 40), "AIR RAID SHELTER", FONT_GILL, (236, 232, 220), 36, pad=0.02)
    fit_text(d, (x0 + 8, y0 + 38, x1 - 8, y1 - 2), "防空壕  TEMPAT BERLINDONG  60 PERSONS", FONT_TC, (236, 210, 90), 18, pad=0.02)
    for key, txt in (("date1936", "1936"), ("date1938", "1938")):
        x0, y0, x1, y1 = SIGN_SMALL[key]
        d.rectangle((x0, y0, x1 - 1, y1 - 1), fill=(214, 208, 192))
        d.rectangle((x0 + 4, y0 + 4, x1 - 5, y1 - 5), outline=(160, 150, 130), width=3)
        fit_text(d, (x0 + 6, y0 + 6, x1 - 6, y1 - 6), txt, FONT_FUT, (120, 112, 96), 44)
    x0, y0, x1, y1 = SIGN_SMALL["fu"]
    d.rectangle((x0, y0, x1 - 1, y1 - 1), fill=(20, 20, 20))
    d.polygon([(x0 + 32, y0 + 2), (x1 - 2, y0 + 32), (x0 + 32, y1 - 2), (x0 + 2, y0 + 32)], fill=(180, 36, 30))
    fit_text(d, (x0 + 12, y0 + 12, x1 - 12, y1 - 12), "福", FONT_TC, (30, 20, 16), 40, pad=0.0)
    x0, y0, x1, y1 = SIGN_SMALL["houseno"]
    d.rectangle((x0, y0, x1 - 1, y1 - 1), fill=(30, 50, 90))
    d.rectangle((x0 + 3, y0 + 3, x1 - 4, y1 - 4), outline=(230, 230, 230), width=2)
    fit_text(d, (x0 + 6, y0 + 6, x1 - 6, y1 - 6), "No. 27", FONT_GILL, (236, 236, 236), 36)
    return img


POSTER_RECT = {
    "p_arp": (0, 0, 256, 384),
    "p_siren": (256, 0, 512, 384),
    "p_talk": (512, 0, 768, 384),
    "p_savings": (768, 0, 1024, 384),
    "banner": (0, 384, 1024, 512),
    "flag": (0, 512, 192, 640),
    "flag2": (192, 512, 384, 640),
    "ration": (384, 512, 768, 768),
    "occ_notice": (0, 640, 384, 1024),
    "news": (768, 512, 1024, 896),
    "torn": (384, 768, 768, 1024),
    "sentry": (768, 896, 1024, 1024),
}


def aged(img, box, amount=0.25, seed=0):
    """Yellow + blotch an area to look like weathered paper."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    region = np.asarray(img.crop(box)).astype(np.float32) / 255.0
    n = pnoise(max(w, h), 2.2, seed)[:h, :w]
    y = np.array([0.93, 0.86, 0.68])
    region = region * (1 - amount * n[..., None]) + y * amount * n[..., None] * 0.6
    img.paste(to_img(region), (x0, y0))


def posters_atlas():
    img = Image.new("RGB", (N, N), (200, 190, 170))
    d = ImageDraw.Draw(img)
    # --- British/colonial war posters (original compositions, period lettering) ---
    x0, y0, x1, y1 = POSTER_RECT["p_arp"]
    d.rectangle((x0, y0, x1 - 1, y1 - 1), fill=(222, 200, 150))
    d.rectangle((x0 + 8, y0 + 8, x1 - 9, y1 - 9), outline=(30, 40, 70), width=4)
    d.polygon([(x0 + 128, y0 + 70), (x0 + 200, y0 + 150), (x0 + 128, y0 + 230), (x0 + 56, y0 + 150)], fill=(30, 40, 70))
    fit_text(d, (x0 + 70, y0 + 120, x0 + 186, y0 + 180), "A.R.P.", FONT_FUT, (222, 200, 150), 40)
    fit_text(d, (x0 + 14, y0 + 14, x1 - 14, y0 + 64), "JOIN THE", FONT_GILL, (30, 40, 70), 40)
    fit_text(d, (x0 + 14, y0 + 240, x1 - 14, y0 + 300), "PASSIVE DEFENCE", FONT_GILL, (170, 34, 30), 40)
    fit_text(d, (x0 + 14, y0 + 296, x1 - 14, y0 + 340), "SERVICES", FONT_GILL, (170, 34, 30), 34)
    fit_text(d, (x0 + 14, y0 + 336, x1 - 14, y1 - 14), "參加民防  SERTAI", FONT_TC, (30, 40, 70), 24)
    aged(img, POSTER_RECT["p_arp"], 0.35, 201)
    x0, y0, x1, y1 = POSTER_RECT["p_siren"]
    d.rectangle((x0, y0, x1 - 1, y1 - 1), fill=(160, 36, 30))
    fit_text(d, (x0 + 12, y0 + 14, x1 - 12, y0 + 70), "WHEN THE SIREN", FONT_ROCK, (240, 230, 200), 36)
    fit_text(d, (x0 + 12, y0 + 64, x1 - 12, y0 + 110), "SOUNDS", FONT_ROCK, (240, 230, 200), 40)
    d.rectangle((x0 + 20, y0 + 120, x1 - 20, y0 + 250), fill=(240, 230, 200))
    fit_text(d, (x0 + 24, y0 + 124, x1 - 24, y0 + 250), "TAKE COVER", FONT_ROCK, (30, 26, 24), 50)
    fit_text(d, (x0 + 12, y0 + 260, x1 - 12, y0 + 320), "警報響時 立即躲避", FONT_TC, (240, 230, 200), 30)
    fit_text(d, (x0 + 12, y0 + 318, x1 - 12, y1 - 16), "BERLINDONG-LAH", FONT_GILL, (240, 230, 200), 28)
    aged(img, POSTER_RECT["p_siren"], 0.3, 202)
    x0, y0, x1, y1 = POSTER_RECT["p_talk"]
    d.rectangle((x0, y0, x1 - 1, y1 - 1), fill=(236, 226, 196))
    d.ellipse((x0 + 58, y0 + 90, x0 + 198, y0 + 230), fill=(40, 40, 40))
    d.polygon([(x0 + 120, y0 + 200), (x0 + 150, y0 + 250), (x0 + 170, y0 + 196)], fill=(40, 40, 40))
    d.rectangle((x0 + 96, y0 + 146, x0 + 160, y0 + 160), fill=(236, 226, 196))
    fit_text(d, (x0 + 12, y0 + 16, x1 - 12, y0 + 80), "CARELESS TALK", FONT_GILL, (170, 34, 30), 40)
    fit_text(d, (x0 + 12, y0 + 250, x1 - 12, y0 + 310), "COSTS LIVES", FONT_GILL, (170, 34, 30), 44)
    fit_text(d, (x0 + 12, y0 + 310, x1 - 12, y1 - 16), "慎言  JAGA MULUT", FONT_TC, (40, 40, 40), 28)
    aged(img, POSTER_RECT["p_talk"], 0.35, 203)
    x0, y0, x1, y1 = POSTER_RECT["p_savings"]
    d.rectangle((x0, y0, x1 - 1, y1 - 1), fill=(34, 70, 60))
    fit_text(d, (x0 + 12, y0 + 16, x1 - 12, y0 + 70), "MALAYA", FONT_FUT, (230, 200, 110), 46)
    fit_text(d, (x0 + 12, y0 + 70, x1 - 12, y0 + 110), "DOES HER BIT", FONT_FUT, (240, 236, 220), 30)
    for k in range(3):
        d.rectangle((x0 + 50 + k * 56, y0 + 130 + k * 10, x0 + 90 + k * 56, y0 + 250), fill=(230, 200, 110))
    fit_text(d, (x0 + 12, y0 + 260, x1 - 12, y0 + 310), "BUY WAR SAVINGS", FONT_FUT, (240, 236, 220), 30)
    fit_text(d, (x0 + 12, y0 + 306, x1 - 12, y0 + 346), "CERTIFICATES", FONT_FUT, (240, 236, 220), 30)
    fit_text(d, (x0 + 12, y0 + 344, x1 - 12, y1 - 12), "購買戰時儲蓄券", FONT_TC, (230, 200, 110), 26)
    aged(img, POSTER_RECT["p_savings"], 0.3, 204)
    # --- Occupation: Syonan banner (white cloth, black brush lettering) ---
    x0, y0, x1, y1 = POSTER_RECT["banner"]
    d.rectangle((x0, y0, x1 - 1, y1 - 1), fill=(236, 232, 222))
    d.ellipse((x0 + 20, y0 + 14, x0 + 120, y0 + 114), fill=(196, 30, 36))
    d.ellipse((x1 - 120, y0 + 14, x1 - 20, y0 + 114), fill=(196, 30, 36))
    fit_text(d, (x0 + 140, y0 + 6, x0 + 560, y1 - 6), "昭南島", FONT_JP, (20, 20, 20), 110)
    fit_text(d, (x0 + 560, y0 + 10, x1 - 140, y0 + 70), "ショウナントウ", FONT_JP, (20, 20, 20), 46)
    fit_text(d, (x0 + 560, y0 + 68, x1 - 140, y1 - 8), "SYONAN-TO", FONT_GILL, (20, 20, 20), 44)
    # --- Hinomaru flags ---
    for key, crease in (("flag", 0), ("flag2", 1)):
        x0, y0, x1, y1 = POSTER_RECT[key]
        d.rectangle((x0, y0, x1 - 1, y1 - 1), fill=(238, 236, 230))
        cx, cy, r = (x0 + x1) / 2, (y0 + y1) / 2, (y1 - y0) * 0.3
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(196, 28, 36))
        if crease:
            for k in range(4):
                xx = x0 + 30 + k * 44
                d.line([(xx, y0), (xx + 10, y1)], fill=(200, 196, 190), width=3)
    # --- Ration notice board ---
    x0, y0, x1, y1 = POSTER_RECT["ration"]
    d.rectangle((x0, y0, x1 - 1, y1 - 1), fill=(96, 70, 44))
    d.rectangle((x0 + 12, y0 + 12, x1 - 13, y1 - 13), fill=(226, 218, 196))
    fit_text(d, (x0 + 20, y0 + 16, x1 - 20, y0 + 90), "米 配給所", FONT_JP, (20, 20, 20), 64)
    fit_text(d, (x0 + 20, y0 + 90, x1 - 20, y0 + 130), "HAIKYU-SHO  RICE RATION", FONT_GILL, (20, 20, 20), 26)
    fit_text(d, (x0 + 20, y0 + 128, x1 - 20, y0 + 166), "TEMPAT CATUAN BERAS", FONT_GILL, (20, 20, 20), 24)
    fit_text(d, (x0 + 20, y0 + 166, x1 - 20, y0 + 206), "大人每月 八斤  小童減半", FONT_TC, (150, 30, 26), 24)
    fit_text(d, (x0 + 20, y0 + 206, x1 - 20, y1 - 18), "BRING RATION CARD", FONT_GILL, (60, 60, 60), 22)
    # --- Occupation proclamation (generic notice; multilingual) ---
    x0, y0, x1, y1 = POSTER_RECT["occ_notice"]
    d.rectangle((x0, y0, x1 - 1, y1 - 1), fill=(232, 226, 206))
    d.ellipse((x0 + 152, y0 + 16, x0 + 232, y0 + 96), fill=(196, 28, 36))
    fit_text(d, (x0 + 16, y0 + 104, x1 - 16, y0 + 170), "布告", FONT_JP, (20, 20, 20), 60)
    for k in range(6):
        d.line([(x0 + 30, y0 + 190 + k * 26), (x1 - 30 - random.randint(0, 60), y0 + 190 + k * 26)], fill=(60, 60, 60), width=6)
    fit_text(d, (x0 + 16, y0 + 350, x1 - 16, y1 - 12), "NOTICE  PEMBERITAHUAN", FONT_GILL, (20, 20, 20), 22)
    aged(img, POSTER_RECT["occ_notice"], 0.2, 205)
    # --- Newspaper front page (fictional paper) ---
    x0, y0, x1, y1 = POSTER_RECT["news"]
    d.rectangle((x0, y0, x1 - 1, y1 - 1), fill=(222, 214, 192))
    fit_text(d, (x0 + 8, y0 + 6, x1 - 8, y0 + 46), "THE MALAYAN DAILY", FONT_COPPER, (20, 20, 20), 30)
    d.line([(x0 + 8, y0 + 50), (x1 - 8, y0 + 50)], fill=(20, 20, 20), width=2)
    fit_text(d, (x0 + 8, y0 + 56, x1 - 8, y0 + 110), "SINGAPORE", FONT_ROCK, (20, 20, 20), 48)
    fit_text(d, (x0 + 8, y0 + 108, x1 - 8, y0 + 160), "WILL STAND", FONT_ROCK, (20, 20, 20), 48)
    fit_text(d, (x0 + 8, y0 + 160, x1 - 8, y0 + 186), "FEBRUARY 1942 — PRICE 5 CENTS", FONT_GILL, (40, 40, 40), 16)
    for c in range(3):
        for k in range(22):
            xx = x0 + 10 + c * 80
            d.line([(xx, y0 + 196 + k * 8), (xx + 70 - random.randint(0, 16), y0 + 196 + k * 8)], fill=(90, 90, 86), width=3)
    aged(img, POSTER_RECT["news"], 0.25, 206)
    # --- torn / ripped poster remnants (for walls in the damaged / later state) ---
    x0, y0, x1, y1 = POSTER_RECT["torn"]
    d.rectangle((x0, y0, x1 - 1, y1 - 1), fill=(190, 180, 160))
    for k in range(5):
        px, py = x0 + random.randint(0, 300), y0 + random.randint(0, 180)
        pts = [(px + random.randint(-10, 90), py + random.randint(-10, 80)) for _ in range(7)]
        d.polygon(pts, fill=random.choice([(222, 200, 150), (160, 40, 30), (236, 226, 196), (34, 70, 60)]))
    aged(img, POSTER_RECT["torn"], 0.4, 207)
    # --- sentry post board ---
    x0, y0, x1, y1 = POSTER_RECT["sentry"]
    d.rectangle((x0, y0, x1 - 1, y1 - 1), fill=(236, 232, 222))
    fit_text(d, (x0 + 8, y0 + 6, x1 - 8, y0 + 70), "歩哨", FONT_JP, (20, 20, 20), 56)
    fit_text(d, (x0 + 8, y0 + 70, x1 - 8, y1 - 8), "HALT", FONT_GILL, (170, 30, 26), 40)
    return img


NOW_SIGNS = [
    ("NINE TILES", "九瓦咖啡 · coffee & toast", (32, 36, 38), (236, 230, 214), FONT_FUT),
    ("KERB & KAYA", "small plates · natural wine", (236, 228, 210), (40, 44, 40), FONT_GILL),
    ("studio jalousie", "百葉設計室 · architecture", (250, 250, 248), (30, 30, 30), FONT_FUT),
    ("AIRWELL", "天井酒廊 · cocktails upstairs", (22, 40, 44), (214, 184, 120), FONT_COPPER),
    ("LIME & LOUVRE", "bakery · 烘焙坊", (182, 70, 48), (246, 236, 218), FONT_ROCK),
    ("FIVE-FOOT BOOKS", "五腳基書店 · new & rare", (40, 58, 44), (236, 226, 196), FONT_GILL),
]


def mixed_text(d, box, text, fill, size):
    """Draw a line that mixes CJK and Latin: CJK runs in Songti TC, the rest in Gill Sans."""
    x0, y0, x1, y1 = box
    runs, cur, cjk = [], "", None
    for ch in text:
        c = ord(ch) > 0x2E80
        if cjk is None or c == cjk:
            cur += ch
        else:
            runs.append((cur, cjk)); cur = ch
        cjk = c
    runs.append((cur, cjk))
    while size > 8:
        fl, fc = font(FONT_GILL, size), font(FONT_TC, int(size * 0.95))
        w = sum(d.textbbox((0, 0), t, font=(fc if c else fl))[2] for t, c in runs)
        if w <= (x1 - x0):
            break
        size -= 1
    x = x0 + ((x1 - x0) - w) / 2
    for t, c in runs:
        f = fc if c else fl
        bb = d.textbbox((0, 0), t, font=f)
        d.text((x, y0 + ((y1 - y0) - (bb[3] - bb[1])) / 2 - bb[1]), t, font=f, fill=fill)
        x += bb[2]


def now_atlas():
    """Present-day dressing: modern signboards (invented names), umbrella fabric, AC grille,
    A-board menu, heritage marker text and a mural."""
    img = Image.new("RGB", (N, N), (200, 200, 200))
    d = ImageDraw.Draw(img)
    for i, (name, sub, bg, fg, fnt) in enumerate(NOW_SIGNS):
        x0, y0 = (i % 2) * 512, (i // 2) * 128
        d.rectangle((x0, y0, x0 + 511, y0 + 127), fill=bg)
        fit_text(d, (x0 + 20, y0 + 10, x0 + 492, y0 + 86), name, fnt, fg, 70, pad=0.02)
        mixed_text(d, (x0 + 50, y0 + 86, x0 + 462, y0 + 122), sub, fg, 26)
    # umbrella fabric: cream / terracotta panels
    x0, y0 = 0, 384
    for k in range(8):
        d.rectangle((x0 + k * 32, y0, x0 + k * 32 + 31, y0 + 255), fill=(236, 226, 204) if k % 2 else (176, 84, 58))
    # AC condenser front: grey casing, round fan grille
    x0, y0 = 256, 384
    d.rectangle((x0, y0, x0 + 255, y0 + 255), fill=(214, 214, 210))
    d.ellipse((x0 + 20, y0 + 30, x0 + 196, y0 + 206), fill=(90, 92, 94))
    for r in range(10, 90, 12):
        d.ellipse((x0 + 108 - r, y0 + 118 - r, x0 + 108 + r, y0 + 118 + r), outline=(170, 170, 168), width=3)
    for k in range(6):
        d.line([(x0 + 212, y0 + 40 + k * 28), (x0 + 244, y0 + 40 + k * 28)], fill=(150, 150, 148), width=5)
    # A-board menu
    x0, y0 = 512, 384
    d.rectangle((x0, y0, x0 + 255, y0 + 255), fill=(34, 36, 34))
    fit_text(d, (x0 + 14, y0 + 10, x0 + 242, y0 + 60), "TODAY", FONT_FUT, (240, 236, 222), 40)
    for k, t in enumerate(("kopi-o  $1.60", "kaya toast  $3", "flat white  $6", "laksa  $9")):
        fit_text(d, (x0 + 14, y0 + 70 + k * 44, x0 + 242, y0 + 108 + k * 44), t, FONT_GILL, (226, 220, 200), 30, pad=0.02)
    # heritage marker (original wording)
    x0, y0 = 768, 384
    d.rectangle((x0, y0, x0 + 255, y0 + 255), fill=(116, 32, 30))
    d.rectangle((x0 + 6, y0 + 6, x0 + 249, y0 + 249), outline=(230, 206, 150), width=3)
    fit_text(d, (x0 + 16, y0 + 14, x0 + 240, y0 + 60), "HERITAGE MARKER", FONT_GILL, (240, 222, 170), 26)
    lines = ["On this lot stood a brick", "and sandbag air-raid", "shelter used by the people", "of this street during the", "bombing of February 1942."]
    for k, t in enumerate(lines):
        fit_text(d, (x0 + 14, y0 + 70 + k * 34, x0 + 242, y0 + 102 + k * 34), t, FONT_GILL, (246, 238, 220), 22, pad=0.01)
    # mural (naive style: shophouse row, a kopitiam cup, birds)
    x0, y0 = 0, 640
    d.rectangle((x0, y0, x0 + 767, y0 + 383), fill=(236, 214, 170))
    d.rectangle((x0, y0 + 250, x0 + 767, y0 + 383), fill=(196, 120, 86))
    cols = [(120, 170, 160), (230, 170, 90), (200, 110, 100), (140, 150, 200), (240, 220, 150)]
    for k in range(7):
        hx = x0 + 10 + k * 108
        d.rectangle((hx, y0 + 110 + (k % 3) * 12, hx + 100, y0 + 250), fill=cols[k % 5])
        d.polygon([(hx - 6, y0 + 110 + (k % 3) * 12), (hx + 50, y0 + 70 + (k % 3) * 12), (hx + 106, y0 + 110 + (k % 3) * 12)], fill=(170, 80, 60))
        for w in range(2):
            d.rectangle((hx + 18 + w * 42, y0 + 140, hx + 40 + w * 42, y0 + 190), fill=(60, 80, 70))
    d.ellipse((x0 + 600, y0 + 190, x0 + 740, y0 + 330), fill=(250, 246, 236), outline=(60, 50, 40), width=5)
    d.rectangle((x0 + 640, y0 + 150, x0 + 700, y0 + 200), fill=(250, 246, 236))
    for k in range(4):
        bx, by = x0 + 100 + k * 150, y0 + 30 + (k % 2) * 20
        d.arc((bx, by, bx + 40, by + 24), 200, 340, fill=(40, 40, 40), width=4)
        d.arc((bx + 36, by, bx + 76, by + 24), 200, 340, fill=(40, 40, 40), width=4)
    # traffic signs (generic designs)
    x0, y0 = 768, 640            # pedestrian crossing: blue square, white triangle, walker
    d.rectangle((x0, y0, x0 + 127, y0 + 127), fill=(20, 70, 160))
    d.polygon([(x0 + 64, y0 + 14), (x0 + 116, y0 + 110), (x0 + 12, y0 + 110)], fill=(250, 250, 250))
    d.ellipse((x0 + 58, y0 + 44, x0 + 70, y0 + 56), fill=(20, 20, 20))
    d.line([(x0 + 64, y0 + 58), (x0 + 60, y0 + 82), (x0 + 50, y0 + 100)], fill=(20, 20, 20), width=6)
    d.line([(x0 + 60, y0 + 82), (x0 + 74, y0 + 100)], fill=(20, 20, 20), width=6)
    x0, y0 = 896, 640            # no entry
    d.rectangle((x0, y0, x0 + 127, y0 + 127), fill=(200, 200, 200))
    d.ellipse((x0 + 4, y0 + 4, x0 + 123, y0 + 123), fill=(200, 20, 30))
    d.rectangle((x0 + 22, y0 + 54, x0 + 105, y0 + 74), fill=(250, 250, 250))
    x0, y0 = 768, 768            # bus-stop style sign
    d.rectangle((x0, y0, x0 + 255, y0 + 127), fill=(250, 250, 250))
    d.rectangle((x0, y0, x0 + 255, y0 + 40), fill=(90, 40, 120))
    fit_text(d, (x0 + 8, y0 + 4, x0 + 248, y0 + 38), "BUS STOP  03129", FONT_GILL, (250, 250, 250), 26)
    for k, t in enumerate(("80   145   608", "Telok Ayer Stn")):
        fit_text(d, (x0 + 8, y0 + 46 + k * 40, x0 + 248, y0 + 84 + k * 40), t, FONT_GILL, (30, 30, 30), 26)
    x0, y0 = 768, 896            # street name sign (white on blue-green, bilingual)
    d.rectangle((x0, y0, x0 + 255, y0 + 127), fill=(20, 90, 110))
    d.rectangle((x0 + 5, y0 + 5, x0 + 250, y0 + 122), outline=(250, 250, 250), width=3)
    fit_text(d, (x0 + 12, y0 + 12, x0 + 244, y0 + 66), "Telok Ayer St", FONT_GILL, (250, 250, 250), 40)
    fit_text(d, (x0 + 12, y0 + 66, x0 + 244, y0 + 116), "直落亚逸街", FONT_TC, (250, 250, 250), 36)
    # plain dark frame patch (for board edges / backs): a corner pixel block
    d.rectangle((1016, 1016, 1023, 1023), fill=(28, 28, 28))
    return img


def tex_glass():
    """Curtain wall (tileable): 6 panels x 4 floors; sky reflection, mullions, spandrels."""
    X, Y = np.meshgrid(np.arange(N), np.arange(N))
    ref = pnoise(N, 3.2, 91, aniso=(0.25, 1.0))
    v = 0.46 + (ref - 0.5) * 0.3
    r = np.random.default_rng(3)
    pid = (X * 6 // N) + (Y * 4 // N) * 6
    tone = r.uniform(0.88, 1.14, size=24)[pid]
    R, G, B = v * 0.70 * tone, v * 0.84 * tone, v * 0.97 * tone
    px = (X * 6) % N // 6
    fy = Y % (N // 4)
    mull = (px < 6) | (px > N // 6 - 6)
    spand = fy > (N // 4) * 0.82
    R = np.where(spand, 0.30, np.where(mull, 0.22, R))
    G = np.where(spand, 0.33, np.where(mull, 0.24, G))
    B = np.where(spand, 0.36, np.where(mull, 0.27, B))
    return to_img(rgb(R, G, B))


def nowshop_atlas():
    """Present-day glass shopfronts (warm interior light) + upper-window variants (emissive map)."""
    img = Image.new("RGB", (N, N), (20, 20, 20))
    d = ImageDraw.Draw(img)
    warm = [(250, 205, 140), (240, 190, 120), (250, 222, 170), (235, 235, 230)]
    for i in range(4):
        x0, y0 = (i % 2) * 512, (i // 2) * 384
        for yy in range(384):
            t = yy / 383
            k = 0.55 + 0.45 * (1 - abs(t - 0.45) * 1.6)
            d.line([(x0, y0 + yy), (x0 + 511, y0 + yy)], fill=tuple(int(q * max(0.25, k)) for q in warm[i]))
        dark = (70, 50, 36) if i < 3 else (150, 150, 148)
        if i == 0:
            for k in range(3):
                tx = x0 + 70 + k * 150
                d.ellipse((tx, y0 + 250, tx + 70, y0 + 262), fill=dark)
                d.rectangle((tx + 32, y0 + 262, tx + 38, y0 + 330), fill=dark)
        elif i == 1:
            for k in range(3):
                d.rectangle((x0 + 40, y0 + 90 + k * 60, x0 + 470, y0 + 96 + k * 60), fill=dark)
                for j in range(12):
                    d.ellipse((x0 + 50 + j * 35, y0 + 60 + k * 60, x0 + 76 + j * 35, y0 + 90 + k * 60), fill=(200, 150, 90))
            d.rectangle((x0 + 60, y0 + 260, x0 + 450, y0 + 330), fill=dark)
        elif i == 2:
            for k in range(2):
                d.rectangle((x0 + 30, y0 + 110 + k * 70, x0 + 480, y0 + 114 + k * 70), fill=(90, 60, 40))
                for j in range(22):
                    d.rectangle((x0 + 36 + j * 20, y0 + 70 + k * 70, x0 + 46 + j * 20, y0 + 110 + k * 70), fill=(120 + (j * 37) % 100, 80, 50))
            d.rectangle((x0 + 30, y0 + 250, x0 + 480, y0 + 330), fill=dark)
        else:
            for k in range(2):
                d.rectangle((x0 + 60 + k * 220, y0 + 230, x0 + 230 + k * 220, y0 + 240), fill=(90, 90, 90))
                d.rectangle((x0 + 80 + k * 220, y0 + 150, x0 + 180 + k * 220, y0 + 225), fill=(40, 40, 44))
        for k in range(4):
            lx = x0 + 70 + k * 120
            d.line([(lx, y0), (lx, y0 + 60)], fill=(30, 30, 30), width=2)
            d.ellipse((lx - 14, y0 + 56, lx + 14, y0 + 76), fill=(255, 240, 200))
        f = (24, 24, 24)
        d.rectangle((x0, y0, x0 + 511, y0 + 383), outline=f, width=10)
        d.rectangle((x0, y0 + 40, x0 + 511, y0 + 48), fill=f)
        for mx in (x0 + 170, x0 + 340):
            d.rectangle((mx - 4, y0, mx + 4, y0 + 383), fill=f)
        d.rectangle((x0 + 196, y0 + 60, x0 + 314, y0 + 383), outline=f, width=6)
        d.rectangle((x0 + 300, y0 + 210, x0 + 306, y0 + 260), fill=(200, 200, 200))
        d.line([(x0 + 20, y0 + 370), (x0 + 150, y0 + 60)], fill=(255, 255, 255), width=3)
    for i in range(4):
        x0, y0 = i * 256, 768
        d.rectangle((x0, y0, x0 + 255, y0 + 255), fill=(30, 30, 30))
        inner = [(240, 200, 150), (200, 220, 190), (220, 230, 240), (60, 60, 64)][i]
        d.rectangle((x0 + 40, y0 + 10, x0 + 215, y0 + 245), fill=inner)
        for sx in (x0 + 4, x0 + 216):
            d.rectangle((sx, y0 + 10, sx + 36, y0 + 245), fill=(60, 90, 70))
            for yy in range(y0 + 16, y0 + 240, 10):
                d.line([(sx, yy), (sx + 36, yy)], fill=(40, 60, 48), width=3)
        if i == 0:
            d.polygon([(x0 + 40, y0 + 10), (x0 + 110, y0 + 10), (x0 + 70, y0 + 245), (x0 + 40, y0 + 245)], fill=(250, 240, 220))
        if i == 1:
            for k in range(4):
                d.ellipse((x0 + 50 + k * 40, y0 + 190, x0 + 95 + k * 40, y0 + 240), fill=(60, 110, 60))
        d.rectangle((x0 + 124, y0 + 10, x0 + 131, y0 + 245), fill=(30, 30, 30))
    return img


def weather(img, strength=0.25, seed=0):
    """Multiply an atlas by grime noise + vertical streaks so nothing looks factory-new."""
    a = np.asarray(img).astype(np.float32) / 255.0
    n = pnoise(N, 2.4, 300 + seed)
    st = pnoise(N, 2.4, 400 + seed, aniso=(1.0, 0.1))
    f = 1 - strength * (0.6 * np.clip(n - 0.4, 0, 1) + 0.8 * np.clip(st - 0.55, 0, 1))
    f *= 1 - strength * 0.25 * (pnoise(N, 0.6, 500 + seed) - 0.5)
    return to_img(a * f[..., None])


def main():
    os.makedirs(OUT, exist_ok=True)
    jobs = {
        "plaster": tex_plaster, "roof": tex_roof, "timber": tex_timber, "floor": tex_floor,
        "road": tex_road, "sandbag": tex_sandbag, "brick": tex_brick, "cloth": tex_cloth,
        "windows": window_atlas, "details": details_atlas, "signs": signs_atlas, "posters": posters_atlas,
        "now": now_atlas, "glass": tex_glass, "nowshop": nowshop_atlas,
    }
    for res in (1024, 512):
        os.makedirs(os.path.join(OUT, str(res)), exist_ok=True)
    for name, fn in jobs.items():
        random.seed(sum(map(ord, name)))
        img = fn().convert("RGB")
        if name in ("windows", "details"):
            img = weather(img, 0.45, len(name))
        elif name in ("signs",):
            img = weather(img, 0.25, 3)
        img.save(os.path.join(OUT, "1024", name + ".png"))
        small = img.resize((512, 512), Image.LANCZOS)
        small.save(os.path.join(OUT, "512", name + ".png"))
        print("tex", name)


if __name__ == "__main__":
    main()
