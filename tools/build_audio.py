#!/usr/bin/env python3
"""Build public/assets/audio/*.mp3 for the Three.js game.

* Converts the credited sounds from the Godot project (../SparkyDiscovery/assets/audio) to mono MP3.
* Synthesises the extra effects and the music theme (deterministic, no samples, no licence issues).
* Writes loops.json with the loopStart/loopEnd (seconds) for every loop.

Only the Python standard library and ffmpeg are needed:
    python3 tools/build_audio.py [--src ../SparkyDiscovery/assets/audio] [--ffmpeg /opt/homebrew/bin/ffmpeg]

Loops and MP3 padding
---------------------
An MP3 encoder adds silence at the start (encoder delay, ~1105 samples with LAME) and pads the last
frame. Some decoders trim it (using the LAME/Xing header), some do not, so `loop = true` on a plain MP3
clicks or gaps. Every loop is therefore written "wrap-padded": [last PAD s of loop] + loop + [first PAD s].
Play it with Web Audio:
    src.loop = true; src.loopStart = loopStart; src.loopEnd = loopEnd; src.start(0, loopStart)
Because the padding is real loop audio, the seam stays seamless whether or not the decoder trimmed the
encoder delay (any offset up to PAD is absorbed). loopEnd - loopStart is exactly the loop length.
"""
import argparse
import array
import json
import math
import os
import random
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'public/assets/audio'
PAD = 0.25  # seconds of wrap padding on each side of a loop

ap = argparse.ArgumentParser()
ap.add_argument('--src', default=str(ROOT.parent / 'SparkyDiscovery/assets/audio'))
ap.add_argument('--ffmpeg', default='/opt/homebrew/bin/ffmpeg')
ap.add_argument('--only', nargs='*', help='build only these output names (without .mp3)')
args = ap.parse_args()
SRC = Path(args.src)
FF = args.ffmpeg
TMP = Path(tempfile.mkdtemp(prefix='sparky-audio-'))
TAU = 2 * math.pi


# ---------------------------------------------------------------- I/O helpers
def ff_read(path, rate):
    """Decode any file to mono float samples at `rate`."""
    raw = subprocess.run([FF, '-v', 'error', '-i', str(path), '-ac', '1', '-ar', str(rate), '-f', 's16le', '-'],
                         check=True, capture_output=True).stdout
    a = array.array('h'); a.frombytes(raw)
    return [v / 32768 for v in a]


def write_wav(path, x, rate):
    a = array.array('h', (int(max(-1.0, min(1.0, v)) * 32767) for v in x))
    with wave.open(str(path), 'wb') as w:
        w.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
        w.writeframes(a.tobytes())


def peak(x):
    return max(abs(v) for v in x) or 1.0


def rms(x):
    return math.sqrt(sum(v * v for v in x) / len(x)) or 1e-9


def gain(x, g):
    return [v * g for v in x]


def norm_peak(x, db):
    return gain(x, 10 ** (db / 20) / peak(x))


def norm_rms(x, db):
    y = gain(x, 10 ** (db / 20) / rms(x))
    p = peak(y)
    return gain(y, 0.97 / p) if p > 0.97 else y


MANIFEST = {}


def emit(name, x, rate, kbps, loop=None, note=''):
    """Encode x to OUT/name.mp3. loop=True wrap-pads x (x is exactly one loop period)."""
    if args.only and name not in args.only:
        return
    body = x
    info = {}
    if loop:
        p = int(PAD * rate)
        body = x[-p:] + x + x[:p]
        info = {'loop': True, 'loopStart': round(p / rate, 6), 'loopEnd': round((p + len(x)) / rate, 6),
                'loopLength': round(len(x) / rate, 6)}
    wav = TMP / f'{name}.wav'
    write_wav(wav, body, rate)
    mp3 = OUT / f'{name}.mp3'
    subprocess.run([FF, '-v', 'error', '-y', '-i', str(wav), '-ac', '1', '-ar', str(rate), '-codec:a', 'libmp3lame',
                    '-b:a', f'{kbps}k', '-write_xing', '1', str(mp3)], check=True)
    info.update({'file': mp3.name, 'duration': round(len(body) / rate, 3), 'rate': rate, 'kbps': kbps,
                 'bytes': mp3.stat().st_size})
    if note:
        info['note'] = note
    MANIFEST[name] = info
    print(f'{mp3.name:24s} {info["duration"]:7.2f}s {info["bytes"] / 1024:7.1f} KB' + ('  loop' if loop else ''))


# ---------------------------------------------------------------- DSP helpers
def biquad(x, kind, f, q, rate, db=0.0):
    """RBJ cookbook biquad: kind in lp, hp, bp, peak."""
    w = TAU * f / rate
    cw, sw = math.cos(w), math.sin(w)
    al = sw / (2 * q)
    if kind == 'lp':
        b0, b1, b2 = (1 - cw) / 2, 1 - cw, (1 - cw) / 2; a0, a1, a2 = 1 + al, -2 * cw, 1 - al
    elif kind == 'hp':
        b0, b1, b2 = (1 + cw) / 2, -(1 + cw), (1 + cw) / 2; a0, a1, a2 = 1 + al, -2 * cw, 1 - al
    elif kind == 'bp':
        b0, b1, b2 = al, 0.0, -al; a0, a1, a2 = 1 + al, -2 * cw, 1 - al
    else:  # peaking EQ
        A = 10 ** (db / 40)
        b0, b1, b2 = 1 + al * A, -2 * cw, 1 - al * A; a0, a1, a2 = 1 + al / A, -2 * cw, 1 - al / A
    b0, b1, b2, a1, a2 = b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0
    y = [0.0] * len(x)
    x1 = x2 = y1 = y2 = 0.0
    for i, v in enumerate(x):
        o = b0 * v + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1, y2, y1 = x1, v, y1, o
        y[i] = o
    return y


def noise(n, rng):
    r = rng.random
    return [2 * r() - 1 for _ in range(n)]


def smooth_noise(n, rate, hz, rng):
    """Slow random wobble in -1..1 (linear interpolation of random points)."""
    step = max(1, int(rate / hz))
    pts = [2 * rng.random() - 1 for _ in range(n // step + 2)]
    return [pts[i // step] + (pts[i // step + 1] - pts[i // step]) * (i % step) / step for i in range(n)]


def add(buf, x, at, g=1.0, wrap=False):
    n = len(buf)
    for i, v in enumerate(x):
        j = at + i
        if wrap:
            j %= n
        elif j >= n:
            break
        buf[j] += v * g


def loopify(y, L, X):
    """Equal-power crossfade loop of length L samples from y (needs len(y) >= L + X)."""
    assert len(y) >= L + X, (len(y), L, X)
    out = y[:L]
    for j in range(X):
        a = math.sin(0.5 * math.pi * j / X)
        b = math.cos(0.5 * math.pi * j / X)
        out[j] = y[j] * a + y[L + j] * b
    return out


def fade(x, rate, fin=0.005, fout=0.02):
    n = len(x); a = max(1, int(fin * rate)); b = max(1, int(fout * rate))
    y = list(x)
    for i in range(min(a, n)):
        y[i] *= i / a
    for i in range(min(b, n)):
        y[n - 1 - i] *= i / b
    return y


def convolve_loop(dry, ir, rate):
    """Circular convolution (reverb) of a loop with ffmpeg afir: tile 3x, convolve, keep the middle."""
    n = len(dry)
    write_wav(TMP / 'tile.wav', dry * 3, rate)
    return _afir(TMP / 'tile.wav', ir, rate)[n:2 * n]


def convolve(dry, ir, rate):
    write_wav(TMP / 'dry.wav', dry + [0.0] * len(ir), rate)
    return _afir(TMP / 'dry.wav', ir, rate)


def _afir(wav, ir, rate):
    write_wav(TMP / 'ir.wav', ir, rate)
    raw = subprocess.run([FF, '-v', 'error', '-i', str(wav), '-i', str(TMP / 'ir.wav'), '-filter_complex',
                          'afir=dry=0:wet=1:gtype=none:irnorm=-1', '-ac', '1', '-ar', str(rate), '-f', 's16le', '-'],
                         check=True, capture_output=True).stdout
    a = array.array('h'); a.frombytes(raw)
    return [v / 32768 for v in a]


def room_ir(rate, seconds, rt60, rng, bright=4000.0, predelay=0.012):
    """Exponentially decaying noise impulse response (small room / soft hall), peak ~0.5."""
    n = int(seconds * rate)
    k = math.log(1000) / rt60
    x = noise(n, rng)
    x = biquad(x, 'lp', bright, 0.7, rate)
    p = int(predelay * rate)
    ir = [0.0] * p + [v * math.exp(-k * i / rate) for i, v in enumerate(x)]
    return gain(ir[:n], 0.5 / peak(ir))


# ---------------------------------------------------------------- 1. conversions
def convert(src, name, rate, kbps, loop=False):
    x = ff_read(SRC / src, rate)
    emit(name, x, rate, kbps, loop=loop)


def build_conversions():
    # One-shots, kept at their existing levels.
    convert('ww2-aircraft.wav', 'aircraft', 22050, 64)
    convert('ww2-impact.wav', 'impact', 22050, 64)
    convert('ww2-door.wav', 'door', 22050, 64)
    convert('ww2-shutter.wav', 'shutter', 22050, 64)
    convert('myna.ogg', 'myna', 44100, 64)
    convert('koel-short.ogg', 'koel-short', 44100, 64)
    for i in range(1, 6):
        convert(f'footstep-{i}.ogg', f'footstep-{i}', 44100, 64)

    # Cicadas: already a seamless loop in the Godot project; keep the whole period.
    convert('cicadas.ogg', 'cicadas', 22050, 48, loop=True)

    # Street and murmur: shortened to 60 s / 45 s with a fresh 2 s crossfade (keeps the total under 3 MB).
    r = 22050
    st = ff_read(SRC / 'street.ogg', r)
    emit('street', loopify(st, 60 * r, 2 * r), r, 48, loop=True,
         note='street.ogg 0:00-1:02, re-looped to 60 s with a 2 s equal-power crossfade')
    mu = ff_read(SRC / 'neighbours.ogg', r)
    emit('murmur', loopify(mu, 45 * r, 2 * r), r, 48, loop=True,
         note='neighbours.ogg 0:00-0:47, re-looped to 45 s with a 2 s crossfade')

    # Rumble: the synthetic file has edge fades; loop its steady middle with a 1.2 s crossfade.
    ru = ff_read(SRC / 'ww2-rumble.wav', r)
    ru = ru[int(0.15 * r):int(13.7 * r)]
    X = int(1.2 * r)
    emit('rumble', loopify(ru, len(ru) - X, X), r, 48, loop=True, note='ww2-rumble.wav 0.15-13.7 s, 1.2 s crossfade')

    # Siren: rebuilt from the public-domain recording (the old 24 s loop had edge fades = a dip at the seam).
    # Choose the loop length near 24 s whose pitch contour best matches the start, then crossfade 1.5 s.
    rec = ff_read(SRC / 'ww2-siren-recording.ogg', r)
    start = 8 * r
    X = int(1.5 * r)
    hop = r // 100
    def zcr(a, b):  # zero-crossing rate per 10 ms (pitch proxy)
        return [sum(1 for k in range(i, i + hop - 1) if (rec[k] >= 0) != (rec[k + 1] >= 0)) for i in range(a, b, hop)]
    ref = zcr(start, start + X)
    best = None
    for L10 in range(2200, 2601, 1):  # 22.00 .. 26.00 s in 10 ms steps
        L = L10 * hop
        cand = zcr(start + L, start + L + X)
        err = sum((p - q) ** 2 for p, q in zip(ref, cand))
        if best is None or err < best[0]:
            best = (err, L)
    L = best[1]
    seg = rec[start:start + L + X]
    old = ff_read(SRC / 'ww2-siren-recorded-loop.wav', r)
    sir = loopify(seg, L, X)
    sir = gain(sir, rms(old) / rms(sir))
    emit('siren', sir, r, 64, loop=True,
         note=f'ww2-siren-recording.ogg from 8.00 s, loop {L / r:.2f} s (pitch-matched), 1.5 s crossfade')


# ---------------------------------------------------------------- 2. synthesis
def synth_camera_shutter():
    r = 44100; rng = random.Random(101)
    n = int(1.25 * r); buf = [0.0] * n

    def click(at, amp, f1, f2, dec):
        m = int(0.06 * r)
        nz = biquad(noise(m, rng), 'hp', 1500, 0.7, r)
        c = [(nz[i] * 0.6 + 0.5 * math.sin(TAU * f1 * i / r) + 0.3 * math.sin(TAU * f2 * i / r))
             * math.exp(-dec * i / r) * min(1, i / (0.0004 * r)) for i in range(m)]
        add(buf, c, int(at * r), amp)
    # Box-camera rotary shutter: a dry "tick-clack" (sprung blade out and back).
    click(0.000, 0.9, 2300, 4100, 140)
    click(0.045, 0.6, 1700, 3300, 110)
    # Low body thump of the wooden/cardboard box.
    m = int(0.08 * r)
    add(buf, [math.sin(TAU * 180 * i / r) * math.exp(-60 * i / r) for i in range(m)], 0, 0.35)
    # Winding knob: ratchet clicks over gentle friction noise.
    t = 0.38
    while t < 1.05:
        click(t, 0.28 + 0.1 * rng.random(), 2900 + 400 * rng.random(), 5200, 260)
        t += 0.07 + 0.03 * rng.random()
    fr = biquad(noise(int(0.7 * r), rng), 'bp', 900, 1.2, r)
    add(buf, [v * math.sin(math.pi * i / len(fr)) for i, v in enumerate(fr)], int(0.37 * r), 0.08)
    emit('camera-shutter', norm_peak(fade(buf, r, 0.0005, 0.05), -2), r, 64)


def synth_radio_static():
    r = 22050; rng = random.Random(202)
    L, X = 8 * r, 1 * r
    n = L + X
    hiss = biquad(noise(n, rng), 'bp', 1700, 0.45, r)
    hiss = biquad(hiss, 'lp', 5000, 0.7, r)
    wob = smooth_noise(n, r, 0.8, rng)
    fad = smooth_noise(n, r, 6, rng)
    buf = [h * 0.35 * (0.75 + 0.2 * w + 0.08 * f) for h, w, f in zip(hiss, wob, fad)]
    # Mains hum through an old valve set.
    for i in range(n):
        buf[i] += 0.018 * math.sin(TAU * 100 * i / r) + 0.008 * math.sin(TAU * 200 * i / r)
    # A faint heterodyne whistle drifting between stations.
    ph = 0.0
    drift = smooth_noise(n, r, 0.3, rng)
    for i in range(n):
        ph += TAU * (950 + 180 * drift[i]) / r
        buf[i] += 0.012 * math.sin(ph) * (0.5 + 0.5 * wob[i])
    # Crackle: sparse pops, sometimes in little clusters.
    t = 0
    while t < n:
        t += int(r * rng.expovariate(14))
        cnt = 1 if rng.random() < 0.8 else rng.randint(3, 8)
        for k in range(cnt):
            at = t + k * rng.randint(30, 300)
            m = rng.randint(20, 90)
            amp = (0.15 + 0.6 * rng.random() ** 2) * (1 if rng.random() < 0.5 else -1)
            add(buf, [amp * math.exp(-i / (m / 4)) * (1 - 2 * (i % 2) * 0.3) for i in range(m)], at)
    emit('radio-static', norm_rms(loopify(buf, L, X), -20), r, 48, loop=True)


def synth_paper():
    r = 44100; rng = random.Random(303)
    n = int(1.15 * r); buf = [0.0] * n
    t = 0.02
    while t < 0.75:
        m = int((0.04 + 0.11 * rng.random()) * r)
        f = 1800 + 4200 * rng.random()
        g = biquad(noise(m, rng), 'bp', f, 0.9, r)
        env = [min(1, i / (0.004 * r)) * math.exp(-5 * i / m) * (0.6 + 0.4 * rng.random()) for i in range(m)]
        add(buf, [a * b for a, b in zip(g, env)], int(t * r), 0.5 + 0.5 * rng.random())
        t += 0.03 + 0.09 * rng.random()
    # The hand-over: a soft flap and a crisp snap as the paper is taken.
    m = int(0.12 * r)
    flap = biquad(noise(m, rng), 'lp', 450, 0.8, r)
    add(buf, [v * math.exp(-25 * i / r) for i, v in enumerate(flap)], int(0.82 * r), 1.6)
    m = int(0.03 * r)
    snap = biquad(noise(m, rng), 'hp', 2500, 0.7, r)
    add(buf, [v * math.exp(-150 * i / r) for i, v in enumerate(snap)], int(0.86 * r), 0.9)
    emit('paper', norm_peak(fade(buf, r, 0.002, 0.08), -3), r, 64)


def synth_whistle():
    r = 44100; rng = random.Random(404)
    n = int(1.45 * r); buf = [0.0] * n
    breath = biquad(noise(n, rng), 'bp', 3000, 1.5, r)
    jit = smooth_noise(n, r, 40, rng)
    for s, e in ((0.02, 0.30), (0.42, 1.32)):  # short-long, like a warden's warning
        a, b = int(s * r), int(e * r)
        ph = 0.0
        for i in range(a, b):
            t = (i - a) / r; d = (b - i) / r
            env = min(1, t / 0.015) * min(1, d / 0.04)
            trill = math.sin(TAU * (31 + 4 * jit[i]) * t)  # the pea rattling in the chamber
            f = 2950 + 70 * trill - (80 * (0.04 - d) / 0.04 if d < 0.04 else 0)
            ph += TAU * f / r
            amp = env * (0.72 + 0.28 * trill)
            buf[i] += amp * (math.sin(ph) + 0.12 * math.sin(2 * ph)) + env * 0.12 * breath[i]
    emit('whistle', norm_peak(buf, -3), r, 64)


def synth_shelter_room():
    r = 22050; rng = random.Random(505)
    L, X = 20 * r, 2 * r
    n = L + X
    low = biquad(biquad(noise(n, rng), 'lp', 220, 0.7, r), 'lp', 220, 0.7, r)
    swell = smooth_noise(n, r, 0.15, rng)
    buf = [v * (0.8 + 0.2 * s) for v, s in zip(low, swell)]
    buf = gain(buf, 1 / rms(buf) * 0.02)
    # Candle flame: very soft breathy flutter.
    fl = biquad(noise(n, rng), 'bp', 700, 0.6, r)
    flut = smooth_noise(n, r, 3, rng)
    for i in range(n):
        buf[i] += fl[i] * 0.004 * (1 + flut[i])
    # Wick crackles, rare and quiet.
    t = 0
    while t < n:
        t += int(r * rng.expovariate(0.7))
        m = rng.randint(40, 160)
        add(buf, biquad([rng.uniform(-1, 1) * math.exp(-i / (m / 5)) for i in range(m)], 'bp', 2500, 1, r), t, 0.05)
    emit('shelter-room', norm_rms(loopify(buf, L, X), -32), r, 48, loop=True)


def synth_distant_explosion():
    r = 22050; rng = random.Random(606)
    n = int(4.5 * r)
    boom = biquad(biquad(noise(n, rng), 'lp', 110, 0.8, r), 'lp', 140, 0.7, r)
    tail = biquad(noise(n, rng), 'lp', 320, 0.7, r)
    deb = biquad(noise(n, rng), 'bp', 900, 0.8, r)
    buf = []
    for i in range(n):
        t = i / r
        att = min(1, t / 0.04)
        buf.append(att * (boom[i] * 6 * math.exp(-1.6 * t) + tail[i] * 0.9 * math.exp(-0.85 * t)
                          + deb[i] * 0.12 * math.exp(-3 * t) * (t > 0.25))
                   + math.sin(TAU * 36 * t) * 0.35 * math.exp(-3.5 * t) * att)
    emit('distant-explosion', norm_peak(fade(buf, r, 0.001, 0.6), -4), r, 64)


def synth_ui_click():
    r = 44100; rng = random.Random(707)
    n = int(0.06 * r)
    nz = noise(n, rng)
    buf = [(math.sin(TAU * 1900 * i / r) * math.exp(-320 * i / r) + 0.4 * math.sin(TAU * 3700 * i / r)
            * math.exp(-600 * i / r) + 0.15 * nz[i] * math.exp(-900 * i / r)) * min(1, i / 8) for i in range(n)]
    emit('ui-click', norm_peak(buf, -6), r, 64)


def bell(f, dur, r, parts=((1, 1, 2.6), (2.0, 0.22, 5), (2.76, 0.32, 6), (5.4, 0.08, 11))):
    n = int(dur * r)
    out = [0.0] * n
    for ratio, amp, dec in parts:
        fr = f * ratio
        if fr > r * 0.45:
            continue
        w = TAU * fr / r
        for i in range(n):
            out[i] += amp * math.sin(w * i) * math.exp(-dec * i / r)
    a = int(0.003 * r)
    for i in range(a):
        out[i] *= i / a
    return out


def synth_pickup_chime():
    r = 44100; rng = random.Random(808)
    n = int(1.7 * r); buf = [0.0] * n
    add(buf, bell(1318.5, 1.5, r), 0, 0.5)          # E6
    add(buf, bell(1975.5, 1.4, r), int(0.11 * r), 0.42)  # B6
    add(buf, bell(659.25, 1.5, r, ((1, 1, 3), (2, 0.2, 6))), 0, 0.18)  # soft E5 underneath
    wet = convolve(buf, room_ir(r, 1.2, 0.9, rng, 6000), r)[:n]
    emit('pickup-chime', norm_peak(fade([d + 0.18 * w for d, w in zip(buf, wet)], r, 0.001, 0.3), -4), r, 64)


# ---------------------------------------------------------------- night search / rumours beats
def synth_shell_whistle():
    """Incoming shell: a descending, growing whistle that stops dead (the impact is a separate sound)."""
    r = 44100; rng = random.Random(909)
    n = int(1.8 * r)
    air = biquad(noise(n, rng), 'bp', 1200, 2.0, r)
    wob = smooth_noise(n, r, 9, rng)
    buf = [0.0] * n
    ph = 0.0
    for i in range(n):
        u = i / n
        f = 1450 * (1 - u) ** 0.6 + 420 * u + 12 * wob[i]   # falls ~1450 -> ~420 Hz
        ph += TAU * f / r
        env = min(1, i / (0.25 * r)) * (0.15 + 0.85 * u ** 1.6)
        buf[i] = env * (math.sin(ph) * 0.8 + 0.18 * math.sin(2 * ph) + air[i] * 0.5 * (0.3 + u))
    emit('shell-whistle', norm_peak(fade(buf, r, 0.01, 0.004), -3), r, 64,
         note='ends abruptly by design; play impact/distant-explosion right after')


def synth_ear_ring():
    """Tinnitus after a near blast: a thin high ring with slow beating over a muffled rumble, fading out."""
    r = 44100; rng = random.Random(910)
    n = int(3.2 * r)
    low = biquad(biquad(noise(n, rng), 'lp', 180, 0.7, r), 'lp', 180, 0.7, r)
    low = gain(low, 0.25 / peak(low))
    buf = []
    for i in range(n):
        t = i / r
        env = min(1, t / 0.04) * math.exp(-1.1 * t) * min(1, (3.2 - t) / 0.4)
        ring = math.sin(TAU * 3800 * t) + math.sin(TAU * 3806.5 * t) * 0.7 + 0.12 * math.sin(TAU * 7603 * t)
        buf.append(env * ring * 0.5 + low[i] * math.exp(-1.5 * t))
    emit('ear-ring', norm_peak(buf, -12), r, 64, note='kept quiet (-12 dBFS peak) on purpose')


def synth_fire_crackle():
    r = 22050; rng = random.Random(911)
    L, X = 12 * r, 1 * r
    n = L + X
    roar = biquad(biquad(noise(n, rng), 'lp', 380, 0.7, r), 'hp', 60, 0.7, r)
    swell = smooth_noise(n, r, 0.7, rng); flick = smooth_noise(n, r, 7, rng)
    buf = [v * (0.7 + 0.25 * s + 0.1 * f) for v, s, f in zip(roar, swell, flick)]
    buf = gain(buf, 0.08 / rms(buf))
    t = 0
    while t < n:  # crackles and the odd bigger snap of burning timber
        t += int(r * rng.expovariate(22))
        big = rng.random() < 0.06
        m = rng.randint(30, 120) * (3 if big else 1)
        pop = biquad([rng.uniform(-1, 1) * math.exp(-i / (m / 5)) for i in range(m)], 'bp',
                     rng.uniform(900, 4000), 0.9, r)
        add(buf, pop, t, (0.5 if big else 0.12 + 0.2 * rng.random()))
    emit('fire-crackle', norm_rms(loopify(buf, L, X), -22), r, 48, loop=True)


def synth_night_ambience():
    """Very sparse: low night air, a far-off fire roar and a few distant thuds of guns."""
    r = 22050; rng = random.Random(912)
    L, X = 30 * r, 2 * r
    n = L + X
    wind = biquad(biquad(noise(n, rng), 'lp', 260, 0.7, r), 'hp', 40, 0.7, r)
    sw = smooth_noise(n, r, 0.12, rng)
    far = biquad(noise(n, rng), 'bp', 700, 0.7, r)
    buf = [w * (0.8 + 0.2 * s) + 0.08 * f * (0.6 + 0.4 * s) for w, s, f in zip(wind, sw, far)]
    buf = loopify(gain(buf, 0.02 / rms(buf)), L, X)
    for at in (3.1, 11.8, 13.4, 22.6):  # far guns; placed circularly so the loop stays seamless
        m = int(2.5 * r)
        th = biquad(biquad(noise(m, rng), 'lp', 90, 0.8, r), 'lp', 120, 0.7, r)
        th = [v * min(1, i / (0.05 * r)) * math.exp(-2.2 * i / r) for i, v in enumerate(th)]
        add(buf, gain(th, 1 / peak(th)), int(at * r), 0.12 + 0.08 * rng.random(), wrap=True)
    emit('night-ambience', norm_rms(buf, -30), r, 48, loop=True)


def synth_heartbeat():
    """Soft 'lub-dub' at 80 bpm; 8 beats = exactly 6.0 s, rendered circularly."""
    r = 22050; rng = random.Random(913)
    period = 0.75
    L = int(8 * period * r)
    buf = [0.0] * L

    def thump(f, dur, dec):
        m = int(dur * r)
        return [math.sin(TAU * f * i / r * (1 - 0.25 * i / m)) * min(1, i / (0.006 * r)) * math.exp(-dec * i / r)
                for i in range(m)]
    lub, dub = thump(58, 0.16, 30), thump(72, 0.13, 38)
    for k in range(8):
        t0 = k * period + rng.uniform(-0.004, 0.004)
        add(buf, lub, int(t0 * r), 1.0, wrap=True)
        add(buf, dub, int((t0 + 0.27) * r), 0.6, wrap=True)
    buf = biquad(buf * 2, 'lp', 160, 0.7, r)[L:]  # filter a doubled copy so the seam is steady-state
    emit('heartbeat', norm_peak(buf, -6), r, 48, loop=True, note='80 bpm, 8 beats')


def synth_paper_piece():
    """A short tear, then the torn piece laid down."""
    r = 44100; rng = random.Random(914)
    n = int(0.6 * r); buf = [0.0] * n
    t = 0.0
    while t < 0.28:  # tear: dense fibre ticks that speed up
        m = int(0.004 * r)
        tick = biquad(noise(m, rng), 'bp', rng.uniform(2500, 6000), 1.2, r)
        add(buf, [v * math.exp(-i / (m / 4)) for i, v in enumerate(tick)], int(t * r), 0.4 + 0.6 * rng.random())
        t += 0.012 * (1 - t / 0.35) + 0.002
    m = int(0.25 * r)
    rip = biquad(noise(m, rng), 'bp', 3500, 0.8, r)
    add(buf, [v * math.sin(math.pi * i / m) for i, v in enumerate(rip)], 0, 0.35)
    m = int(0.09 * r)
    tap = biquad(noise(m, rng), 'lp', 600, 0.8, r)
    add(buf, [v * math.exp(-40 * i / r) for i, v in enumerate(tap)], int(0.42 * r), 1.4)
    emit('paper-piece', norm_peak(fade(buf, r, 0.001, 0.05), -4), r, 64)


# ---------------------------------------------------------------- music theme
NOTE = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def midi(name):
    return 12 * (int(name[-1]) + 1) + NOTE[name[0]]


def hz(m):
    return 440 * 2 ** ((m - 69) / 12)


# 24 bars of 4/4 at 80 bpm = 72 s. Melody in A minor pentatonic (A C D E G), lifting to C major for bars 9-16.
MELODY = """
A4 1 C5 1 E5 2 | D5 1 C5 .5 A4 .5 G4 2 | A4 1 C5 1 D5 1 E5 1 | D5 3 - 1 |
E5 1 G5 1 E5 1 D5 1 | C5 1 D5 .5 C5 .5 A4 2 | G4 1 A4 1 C5 1 D5 1 | A4 3 - 1 |
C5 1 E5 1 G5 2 | A5 1 G5 1 E5 2 | D5 1 E5 1 G5 1 A5 1 | G5 3 - 1 |
A5 1 C6 1 A5 1 G5 1 | E5 1 G5 .5 E5 .5 D5 2 | C5 1 D5 1 E5 1 G5 1 | E5 3 - 1 |
A4 1 C5 1 E5 2 | D5 1 E5 .5 G5 .5 A5 2 | G5 1 E5 1 D5 1 C5 1 | D5 3 - 1 |
E5 1 D5 1 C5 1 A4 1 | C5 1 D5 1 E5 2 | D5 1 C5 1 G4 1 C5 1 | A4 3 - 1 |
"""
# (bass root, chord tone on beat 3) per bar
HARMONY = ('A2 E4 F2 C4 C3 G4 G2 D4 C3 E4 A2 C4 G2 D4 A2 E4 '
           'C3 G4 A2 E4 F2 A4 G2 D4 F2 C4 C3 G4 G2 D4 C3 E4 '
           'A2 E4 F2 A4 C3 G4 G2 D4 A2 E4 F2 C4 G2 B3 A2 E4').split()


def musicbox(f, r, dur=3.2):
    return bell(f, dur, r, ((1, 1, 1.1), (3.01, 0.13, 5), (5.93, 0.05, 12), (2.0, 0.06, 3)))


def felt_piano(f, r, dur=3.4):
    n = int(dur * r)
    out = [0.0] * n
    for ratio, amp, dec in ((1, 1, 0.9), (2, 0.35, 1.6), (3, 0.12, 2.6), (4, 0.05, 3.5)):
        w = TAU * f * ratio / r
        for i in range(n):
            out[i] += amp * math.sin(w * i) * math.exp(-dec * i / r)
    a = int(0.012 * r)
    for i in range(a):
        out[i] *= i / a
    b = int(0.4 * r)
    for i in range(b):
        out[n - 1 - i] *= i / b
    return out


def synth_theme():
    r = 32000; rng = random.Random(1942)
    beat = 60 / 80
    L = int(24 * 4 * beat * r)
    buf = [0.0] * L
    cache = {}

    def tone(kind, m):
        k = (kind, m)
        if k not in cache:
            cache[k] = musicbox(hz(m), r) if kind == 'box' else felt_piano(hz(m), r)
        return cache[k]

    t = 0.0
    toks = MELODY.replace('|', ' ').split()
    for name, length in zip(toks[::2], toks[1::2]):
        if name != '-':
            jitter = rng.uniform(-0.008, 0.008)
            vel = 0.8 + 0.2 * rng.random()
            add(buf, tone('box', midi(name) + 12), int((t + jitter) * r), 0.42 * vel, wrap=True)
        t += float(length) * beat
    assert abs(t - 24 * 4 * beat) < 1e-6, t
    for bar in range(24):
        root, chord = HARMONY[2 * bar], HARMONY[2 * bar + 1]
        t0 = bar * 4 * beat
        add(buf, tone('piano', midi(root)), int(t0 * r), 0.30, wrap=True)
        add(buf, tone('piano', midi(root) + 7), int((t0 + 0.02) * r), 0.10, wrap=True)
        add(buf, tone('box', midi(chord)), int((t0 + 2 * beat) * r), 0.16, wrap=True)
        if bar % 4 == 3:  # a soft pick-up note at the end of each phrase
            add(buf, tone('box', midi(chord) + 12), int((t0 + 3.5 * beat) * r), 0.08, wrap=True)
    wet = convolve_loop(buf, room_ir(r, 2.6, 2.2, rng, 5000, 0.02), r)
    mix = [d + 0.22 * w for d, w in zip(buf, wet)]
    emit('theme-1942', norm_peak(mix, -6), r, 64, loop=True,
         note='original music-box theme, A minor pentatonic, 80 bpm, 24 bars')


# ---------------------------------------------------------------- Chapter 2 (1965 kopitiam)
def build_conversions_1965():
    # Both are already seamless loops in the Godot project (tools/build_soundscape.py there).
    convert('ceiling-fan.ogg', 'ceiling-fan', 22050, 48, loop=True)
    convert('tv-static.ogg', 'tv-static', 22050, 48, loop=True)


def tv_peak(x, fn, q, db, rate, step=32):
    """Peaking EQ whose centre frequency fn(t in 0..1) glides, keeping filter state (no clicks)."""
    y = [0.0] * len(x)
    x1 = x2 = y1 = y2 = 0.0
    n = len(x)
    A = 10 ** (db / 40)
    for s0 in range(0, n, step):
        w = TAU * fn(s0 / n) / rate
        cw, sw = math.cos(w), math.sin(w)
        al = sw / (2 * q)
        a0 = 1 + al / A
        b0, b1, b2 = (1 + al * A) / a0, -2 * cw / a0, (1 - al * A) / a0
        a1, a2 = -2 * cw / a0, (1 - al / A) / a0
        for i in range(s0, min(n, s0 + step)):
            v = x[i]
            o = b0 * v + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
            x2, x1, y2, y1 = x1, v, y1, o
            y[i] = o
    return y


def bubble(r_mm, rate, rng):
    """One air bubble in liquid: a damped sine at the Minnaert frequency, chirping upwards as it rises."""
    f0 = 3260.0 / r_mm                       # Minnaert: ~3.26 m·Hz / radius
    d = 0.043 * f0 + 0.0014 * f0 ** 1.5      # damping (van den Doel)
    rise = 0.1 * f0 * rng.uniform(1.0, 3.0)  # Hz per second of upward glide
    m = int(min(0.08, 6.0 / d) * rate)
    ph = 0.0
    out = []
    for i in range(m):
        t = i / rate
        ph += TAU * (f0 + rise * t * 40) / rate
        out.append(math.sin(ph) * math.exp(-d * t))
    return out


def synth_kopi_pour():
    """Kopi poured from a long-spouted pot into a thick cup: a stream full of little bubbles, the cup's
    ring rising as it fills, the stream thinning to a few last drips."""
    r = 44100; rng = random.Random(1965)
    dur, stream = 1.75, 1.4                   # total length, time the stream runs
    n = int(dur * r)
    buf = [0.0] * n

    def density(t):                            # bubbles per second: fast attack, thins at the end
        if t < 0.05:
            return 520 * t / 0.05
        if t < stream - 0.25:
            return 520
        return max(0.0, 520 * (stream - t) / 0.25)
    # 1) bubbles (a Poisson stream; smaller bubbles are more common and quieter)
    t = 0.0
    while t < stream:
        t += rng.expovariate(520)               # constant-rate stream, thinned by density()
        if t >= stream or rng.random() > density(t) / 520:
            continue
        r_mm = math.exp(rng.uniform(math.log(0.9), math.log(4.5)))
        add(buf, bubble(r_mm, r, rng), int(t * r), 0.12 * (r_mm / 2.5) ** 0.8)
    # 2) the stream itself: splashy broadband noise that flutters
    fl = smooth_noise(n, r, 45, rng)
    sp = biquad(biquad(noise(n, rng), 'hp', 500, 0.7, r), 'lp', 3200, 0.7, r)
    for i in range(n):
        tt = i / r
        env = min(1.0, tt / 0.04) * (1.0 if tt < stream - 0.2 else max(0.0, (stream - tt) / 0.2))
        buf[i] += sp[i] * env * (0.05 + 0.03 * fl[i])
    # 3) the cup: its air column shortens as it fills, so the ring rises (~500 Hz -> ~1.7 kHz)
    buf = tv_peak(buf, lambda u: 500 + 1200 * min(1.0, u * dur / stream) ** 1.3, 4.0, 12.0, r)
    buf = biquad(buf, 'hp', 180, 0.7, r)
    # 4) a first splash as the stream hits the empty cup, then the last drips
    m = int(0.06 * r)
    splash = biquad(noise(m, rng), 'bp', 1800, 0.9, r)
    add(buf, [v * math.exp(-60 * i / r) for i, v in enumerate(splash)], 0, 0.35)
    for k, at in enumerate((stream + 0.07, stream + 0.2, stream + 0.29)):
        add(buf, bubble(rng.uniform(1.4, 2.2), r, rng), int(at * r), 0.16 - 0.03 * k)
    # a touch of room (the kopitiam's tiled walls)
    wet = convolve(buf, room_ir(r, 0.35, 0.3, rng, bright=5000), r)[:n]
    out = [d + 0.18 * w for d, w in zip(buf, wet)]
    emit('kopi-pour', norm_peak(fade(out, r, 0.004, 0.08), -4), r, 80)


def synth_cup_clink():
    """Thick porcelain kopi cup set down on its saucer on a marble table."""
    r = 44100; rng = random.Random(1966)
    n = int(0.7 * r); buf = [0.0] * n
    add(buf, bell(2240, 0.6, r, ((1, 1, 26), (2.31, 0.5, 38), (3.9, 0.25, 55), (6.2, 0.1, 80))), 0, 0.55)
    add(buf, bell(1580, 0.5, r, ((1, 1, 30), (2.6, 0.3, 45))), int(0.018 * r), 0.3)   # small rattle back
    m = int(0.05 * r)
    thunk = biquad(noise(m, rng), 'lp', 600, 0.8, r)
    add(buf, [v * math.exp(-90 * i / r) for i, v in enumerate(thunk)], 0, 0.9)
    emit('cup-clink', norm_peak(fade(buf, r, 0.0005, 0.1), -4), r, 64)


def synth_spoon_stir():
    """A teaspoon stirring kopi: soft liquid swish with small metallic tinks against the rim."""
    r = 44100; rng = random.Random(1967)
    n = int(1.3 * r); buf = [0.0] * n
    sw = biquad(noise(n, rng), 'bp', 700, 1.2, r)
    for i in range(n):
        buf[i] += sw[i] * 0.08 * (0.5 + 0.5 * math.sin(TAU * 3.2 * i / r)) ** 2
    t = 0.05
    while t < 1.15:
        f = 3300 + 900 * rng.random()
        add(buf, bell(f, 0.2, r, ((1, 1, 45), (2.4, 0.4, 70), (4.1, 0.15, 90))), int(t * r), 0.25 + 0.2 * rng.random())
        t += 0.28 + 0.06 * rng.random()
    emit('spoon-stir', norm_peak(fade(buf, r, 0.01, 0.12), -6), r, 64)


def synth_firecrackers():
    """A string of firecrackers going off a few streets away (heard through the kopitiam door)."""
    r = 22050; rng = random.Random(1968)
    n = int(4.5 * r); buf = [0.0] * n
    t = 0.1
    while t < 3.8:
        m = int(0.06 * r)
        pop = biquad(noise(m, rng), 'bp', 900 + 1400 * rng.random(), 0.9, r)
        amp = 0.4 + 0.6 * rng.random()
        add(buf, [v * math.exp(-70 * i / r) * min(1, i / 20) for i, v in enumerate(pop)], int(t * r), amp)
        t += rng.expovariate(18) + 0.012
    far = biquad(biquad(buf, 'lp', 2600, 0.7, r), 'hp', 180, 0.7, r)
    wet = convolve(far, room_ir(r, 1.4, 1.1, rng, 3000, 0.03), r)[:n]
    mix = [d + 0.5 * w for d, w in zip(far, wet)]
    emit('firecrackers', norm_peak(fade(mix, r, 0.005, 0.8), -8), r, 64)


def pluck(f, dur, r, rng, bright=0.5):
    """Karplus-Strong plucked string (guitar / gambus-ish)."""
    n = int(dur * r)
    p = max(2, int(r / f))
    ring = [rng.uniform(-1, 1) for _ in range(p)]
    out = [0.0] * n
    for i in range(n):
        a = ring[i % p]
        b = ring[(i + 1) % p]
        v = (bright * a + (1 - bright) * b) * 0.996
        ring[i % p] = v
        out[i] = a
    return fade(out, r, 0.001, 0.05)


# Original tune in the style of 1960s Malay pop (joget rhythm, D major), 16 bars of 4/4 at 126 bpm.
RADIO_MELODY = """
A4 .5 B4 .5 D5 1 D5 .5 E5 .5 F#5 1 | E5 .5 D5 .5 B4 1 A4 2 | B4 .5 D5 .5 E5 1 E5 .5 F#5 .5 A5 1 | F#5 3 - 1 |
A5 .5 F#5 .5 E5 1 D5 .5 E5 .5 F#5 1 | E5 .5 D5 .5 B4 1 D5 2 | B4 .5 A4 .5 F#4 1 A4 .5 B4 .5 D5 1 | E5 3 - 1 |
D5 .5 E5 .5 F#5 1 A5 .5 F#5 .5 E5 1 | D5 .5 B4 .5 A4 1 B4 2 | D5 .5 E5 .5 F#5 1 E5 .5 D5 .5 B4 1 | A4 3 - 1 |
B4 .5 D5 .5 E5 1 F#5 .5 E5 .5 D5 1 | B4 .5 A4 .5 F#4 1 A4 2 | B4 .5 D5 .5 E5 1 D5 .5 C#5 .5 E5 1 | D5 3 - 1 |
"""
RADIO_CHORDS = ('D G D A D G D A '
                'D Bm G A D Bm G A '
                'D G D A G D Em A '
                'G D Bm A G D A D').split()   # two chords per bar
CHORD_TONES = {'D': ('D3', 'F#3', 'A3'), 'G': ('G2', 'B2', 'D3'), 'A': ('A2', 'C#3', 'E3'),
               'Bm': ('B2', 'D3', 'F#3'), 'Em': ('E3', 'G3', 'B3')}


def note_midi(name):
    base = NOTE[name[0]]
    acc = 1 if '#' in name else 0
    return 12 * (int(name[-1]) + 1) + base + acc


def synth_radio_song():
    """An original lo-fi pop tune as heard through a 1960s valve radio (band-limited, slightly driven)."""
    r = 22050; rng = random.Random(1969)
    beat = 60 / 126
    L = int(16 * 4 * beat * r)
    buf = [0.0] * L
    t = 0.0
    toks = RADIO_MELODY.replace('|', ' ').split()
    for name, length in zip(toks[::2], toks[1::2]):
        dur = float(length) * beat
        if name != '-':
            f = hz(note_midi(name))
            m = int(min(dur * 1.1, 1.8) * r)
            vib = [math.sin(TAU * 5.5 * i / r) for i in range(m)]
            ph = 0.0
            tone = []
            for i in range(m):
                ph += TAU * f * (1 + 0.006 * vib[i] * min(1, i / (0.25 * r))) / r
                env = min(1, i / (0.03 * r)) * math.exp(-0.9 * i / r) * min(1, (m - i) / (0.05 * r))
                tone.append(env * (math.sin(ph) + 0.35 * math.sin(2 * ph) + 0.12 * math.sin(3 * ph)))  # violin-ish
            add(buf, tone, int(t * r), 0.22, wrap=True)
        t += dur
    assert abs(t - 16 * 4 * beat) < 1e-6, t
    # Rhythm guitar (off-beat strums) + bass (joget: dotted, pushing feel) + tambourine / hand drum.
    cache = {}
    def pl(nm, dur, bright=0.5):
        k = (nm, dur, bright)
        if k not in cache:
            cache[k] = pluck(hz(note_midi(nm)), dur, r, rng, bright)
        return cache[k]
    for half, ch in enumerate(RADIO_CHORDS):
        t0 = half * 2 * beat
        tones = CHORD_TONES[ch]
        add(buf, pl(tones[0], 0.5, 0.6), int(t0 * r), 0.45, wrap=True)                       # bass on 1
        add(buf, pl(tones[0], 0.35, 0.6), int((t0 + 1.5 * beat) * r), 0.3, wrap=True)        # push on 2-and
        for k, off in enumerate((0.5, 1.0)):                                                 # off-beat strums
            for j, nm in enumerate(tones):
                up = note_midi(nm) + 12
                add(buf, pluck(hz(up), 0.3, r, rng, 0.8), int((t0 + off * beat + j * 0.008) * r), 0.10, wrap=True)
        for k in range(4):                                                                   # tambourine 8ths
            m = int(0.07 * r)
            jing = biquad(noise(m, rng), 'hp', 6000, 0.7, r)
            add(buf, [v * math.exp(-60 * i / r) for i, v in enumerate(jing)], int((t0 + k * 0.5 * beat) * r), 0.10 if k % 2 else 0.05, wrap=True)
        m = int(0.12 * r)                                                                    # hand drum on 1
        add(buf, [math.sin(TAU * (140 - 60 * i / m) * i / r) * math.exp(-30 * i / r) for i in range(m)], int(t0 * r), 0.35, wrap=True)
    # Through the radio: band-pass, gentle valve saturation, a little hiss and hum.
    y = biquad(biquad(buf, 'hp', 320, 0.7, r), 'lp', 3200, 0.7, r)
    y = biquad(y, 'peak', 1400, 0.9, r, 4)
    y = norm_peak(y, -3)
    y = [math.tanh(1.8 * v) / math.tanh(1.8) for v in y]
    hiss = biquad(noise(L, rng), 'bp', 2500, 0.5, r)
    y = [v + 0.015 * h + 0.006 * math.sin(TAU * 100 * i / r) for i, (v, h) in enumerate(zip(y, hiss))]
    emit('radio-song', norm_rms(y, -20), r, 48, loop=True,
         note='original tune in the style of 1960s Malay pop (joget), D major, 126 bpm, 16 bars; radio-filtered')


# ---------------------------------------------------------------- main
def verify_loops():
    """Decode each loop, splice [loopEnd-50ms .. loopEnd] + [loopStart .. +50ms] as Web Audio would play it,
    and check the join for a level dip (gap) or a click, compared with the rest of the file."""
    print('\nloop seam check (ffmpeg decode; dip = quietest 5 ms window vs median, click = join step vs p99.9 step):')
    for name, info in MANIFEST.items():
        if not info.get('loop'):
            continue
        r = info['rate']
        x = ff_read(OUT / info['file'], r)
        a, b = int(round(info['loopStart'] * r)), int(round(info['loopEnd'] * r))
        w = int(0.05 * r); h = int(0.005 * r)
        seam = x[b - w:b] + x[a:a + w]
        wins = [rms(seam[i:i + h]) for i in range(0, len(seam) - h, h // 2)]
        body = x[a:b]
        bw = sorted(rms(body[i:i + h]) for i in range(0, len(body) - h, h))
        med = bw[len(bw) // 2] or 1e-9
        steps = sorted(abs(body[i + 1] - body[i]) for i in range(0, len(body) - 1, 3))
        p999 = steps[int(len(steps) * 0.999)] or 1e-9
        join = abs(x[a] - x[b - 1])
        info['decodedSamples'] = len(x)
        info['seamDipDb'] = round(20 * math.log10(min(wins) / med + 1e-9), 1)
        print(f'  {name:14s} decoded {len(x) / r:8.3f}s ({len(x)} samples)  dip {info["seamDipDb"]:6.1f} dB'
              f'  click {join / p999:4.2f}')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if not SRC.exists():
        sys.exit(f'source folder not found: {SRC}')
    build_conversions()
    build_conversions_1965()
    for fn in (synth_camera_shutter, synth_radio_static, synth_paper, synth_whistle, synth_shelter_room,
               synth_distant_explosion, synth_ui_click, synth_pickup_chime, synth_theme,
               synth_shell_whistle, synth_ear_ring, synth_fire_crackle, synth_night_ambience, synth_heartbeat,
               synth_paper_piece, synth_kopi_pour, synth_cup_clink, synth_spoon_stir, synth_firecrackers,
               synth_radio_song):
        fn()
    verify_loops()
    old = {}
    mf = OUT / 'loops.json'
    if args.only and mf.exists():
        old = json.loads(mf.read_text())
    old.update(MANIFEST)
    mf.write_text(json.dumps(dict(sorted(old.items())), indent=2) + '\n')
    total = sum(p.stat().st_size for p in OUT.glob('*.mp3'))
    print(f'\ntotal mp3: {total / 1024 / 1024:.2f} MB ({total} bytes)')


main()
