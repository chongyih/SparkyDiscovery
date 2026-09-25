#!/usr/bin/env python3
"""Build Chapter 3's extra sounds into public/assets/audio/ and add them to loops.json.

    python3 tools/build_audio_ns.py [--ffmpeg /opt/homebrew/bin/ffmpeg] [--only band truck]

* The drill has no sound cue of its own: the commands are shown on screen, and the boots answer.
* band-march   An original, generic military-band march (brass, bass drum, snare), 116 bpm, looped.
* truck-engine A lorry idling, looped.

Standard library + ffmpeg, deterministic. Loops are wrap-padded like
tools/build_audio.py (see public/assets/audio/README.md).
"""
import argparse, array, json, math, random, subprocess, tempfile, wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'public/assets/audio'
PAD = 0.25
ap = argparse.ArgumentParser()
ap.add_argument('--ffmpeg', default='/opt/homebrew/bin/ffmpeg')
ap.add_argument('--only', nargs='*', default=['band', 'truck'])
args = ap.parse_args()
FF = args.ffmpeg
TMP = Path(tempfile.mkdtemp(prefix='sparky-audio-ns-'))
MANIFEST_PATH = OUT / 'loops.json'
MANIFEST = json.loads(MANIFEST_PATH.read_text()) if MANIFEST_PATH.exists() else {}
TAU = 2 * math.pi


def write_wav(path, x, rate):
    a = array.array('h', (max(-32767, min(32767, int(v * 32767))) for v in x))
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(a.tobytes())


def encode(src, name, rate, kbps, info=None, note='', filters=None):
    mp3 = OUT / f'{name}.mp3'
    cmd = [FF, '-v', 'error', '-y', '-i', str(src)]
    if filters:
        cmd += ['-af', filters]
    cmd += ['-ac', '1', '-ar', str(rate), '-codec:a', 'libmp3lame', '-b:a', f'{kbps}k', '-write_xing', '1', str(mp3)]
    subprocess.run(cmd, check=True)
    dur = float(subprocess.run([FF.replace('ffmpeg', 'ffprobe'), '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(mp3)],
                               capture_output=True, text=True).stdout.strip() or 0)
    info = dict(info or {})
    info.update({'file': mp3.name, 'duration': round(dur, 3), 'rate': rate, 'kbps': kbps, 'bytes': mp3.stat().st_size})
    if note:
        info['note'] = note
    MANIFEST[name] = info
    print(f'{mp3.name:24s} {dur:6.2f}s {info["bytes"] / 1024:6.1f} KB' + ('  loop' if info.get('loop') else ''))


def emit_loop(name, x, rate, kbps, note=''):
    p = int(PAD * rate)
    body = x[-p:] + x + x[:p]
    wav = TMP / f'{name}.wav'
    write_wav(wav, body, rate)
    encode(wav, name, rate, kbps, {'loop': True, 'loopStart': round(p / rate, 6), 'loopEnd': round((p + len(x)) / rate, 6),
                                   'loopLength': round(len(x) / rate, 6)}, note)


# ---------------------------------------------------------------- band march (original)
def build_band():
    rate = 22050
    bpm = 116
    beat = 60 / bpm
    bars = 16
    n = int(rate * beat * 4 * bars)
    x = [0.0] * n
    rng = random.Random(1967)
    # Melody (scale degrees in C major, one per half-beat; 0 = rest). Original, generic march shape.
    A = [5, 0, 5, 6, 5, 3, 1, 0, 2, 0, 2, 3, 2, 7, 5, 0]
    B = [8, 0, 8, 7, 6, 5, 6, 0, 5, 0, 3, 2, 1, 2, 3, 0]
    C = [5, 0, 5, 6, 5, 3, 1, 0, 2, 3, 4, 2, 1, 0, 1, 0]
    melody = (A + B + A + C) * 2
    scale = [0, 0, 2, 4, 5, 7, 9, 11, 12]
    bass_notes = [0, 7, 5, 7] * (bars)

    def midi_hz(m): return 440 * 2 ** ((m - 69) / 12)

    def add_note(t0, dur, hz, amp, bright=0.6):
        i0 = int(t0 * rate); L = int(dur * rate)
        ph = 0.0
        for j in range(L):
            if i0 + j >= n: break
            t = j / rate
            env = min(1, t / 0.02) * math.exp(-t * 1.6) * (1 - max(0, (j - L + 400) / 400))
            ph += hz / rate
            s = 2 * (ph % 1) - 1                      # saw
            s = s * bright + math.sin(TAU * ph) * (1 - bright)
            x[i0 + j] += s * amp * env

    half = beat / 2
    for k, deg in enumerate(melody):
        if not deg: continue
        m = 72 + scale[deg]
        add_note(k * half, half * 1.8, midi_hz(m), 0.16, 0.55)
        add_note(k * half, half * 1.8, midi_hz(m - 12), 0.08, 0.35)   # horns an octave down
    for k, deg in enumerate(bass_notes):
        add_note(k * beat, beat * 0.9, midi_hz(36 + deg), 0.22, 0.3)
    # Drums: bass drum on 1 and 3, snare roll figure on 4.
    def drum(t0, kind):
        i0 = int(t0 * rate)
        L = int(0.25 * rate)
        for j in range(L):
            if i0 + j >= n: break
            t = j / rate
            if kind == 'bass':
                v = math.sin(TAU * (55 - 25 * t) * t) * math.exp(-t * 14) * 0.5
            else:
                v = (rng.random() * 2 - 1) * math.exp(-t * 28) * 0.22 + math.sin(TAU * 190 * t) * math.exp(-t * 40) * 0.08
            x[i0 + j] += v
    for b in range(bars * 4):
        if b % 2 == 0: drum(b * beat, 'bass')
        drum(b * beat + half, 'snare') if b % 4 == 3 else None
        drum(b * beat, 'snare') if b % 2 == 1 else None
    peak = max(abs(v) for v in x) or 1
    x = [v / peak * 0.8 for v in x]
    emit_loop('band-march', x, rate, 64, note='Original synthesised march, 116 bpm, 16 bars (tools/build_audio_ns.py).')


# ---------------------------------------------------------------- lorry idling
def build_truck():
    rate = 22050
    L = rate * 6
    rng = random.Random(3)
    x = [0.0] * L
    lp = 0.0
    for i in range(L):
        t = i / rate
        f0 = 27.5  # an exact number of cycles per loop
        firing = sum(math.sin(TAU * f0 * h * t + h) / h for h in (1, 2, 3, 4, 6))
        wob = 1 + 0.12 * math.sin(TAU * t / 1.5)
        lp += 0.08 * ((rng.random() * 2 - 1) - lp)
        x[i] = (firing * 0.32 * wob + lp * 0.9)
    peak = max(abs(v) for v in x) or 1
    x = [v / peak * 0.7 for v in x]
    emit_loop('truck-engine', x, rate, 48, note='Synthesised lorry idle (tools/build_audio_ns.py).')


if 'band' in args.only: build_band()
if 'truck' in args.only: build_truck()
MANIFEST_PATH.write_text(json.dumps(dict(sorted(MANIFEST.items())), indent=2) + '\n')
print('loops.json updated')
