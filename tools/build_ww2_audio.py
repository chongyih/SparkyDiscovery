"""Deterministic, original synthetic theatrical effects. No external samples."""
from pathlib import Path
import math
import random
import struct
import wave

ROOT = Path(__file__).resolve().parents[1] / 'assets/audio'
RATE = 22050
rng = random.Random(1942)
for name, duration in [('rumble', 14), ('siren', 7), ('impact', 4), ('aircraft', 12), ('shutter', 0.8), ('door', 1.0), ('water', 2.4)]:
    samples = bytearray()
    phase = low = 0.0
    for i in range(int(RATE * duration)):
        t = i / RATE
        noise = rng.uniform(-1, 1)
        low = 0.96 * low + 0.04 * noise
        edge = min(1, t / 0.1, (duration - t) / 0.25)
        if name == 'siren':
            phase += 2 * math.pi * (380 + 150 * math.sin(t * 1.3 - 1)) / RATE
            value = (math.sin(phase) + 0.18 * math.sin(phase * 3)) * 0.35 * edge
        elif name == 'impact':
            value = (low * 3 + noise * 0.15 + math.sin(t * 2 * math.pi * 48) * 0.35) * math.exp(-t * 1.5) * min(1, t / 0.015) * 0.7
        elif name == 'aircraft':
            envelope = math.sin(math.pi * t / duration) ** 2
            frequency = 82 - t * 1.1
            phase += 2 * math.pi * frequency / RATE
            value = (math.sin(phase) * 0.2 + math.sin(phase * 2.03) * 0.13 + low) * envelope * (0.8 + 0.2 * math.sin(t * 38))
        elif name in ('shutter', 'door'):
            decay = math.exp(-t * (9 if name == 'shutter' else 6))
            value = (low * 2 + math.sin(t * 2 * math.pi * 113) * 0.25 + noise * 0.2) * decay * min(1, t / 0.008)
        elif name == 'water':
            value = (noise * 0.07 + low * 0.4 + math.sin(t * 2000 + math.sin(t * 19) * 4) * 0.04) * edge
        else:
            value = (low * 1.5 + math.sin(t * 2 * math.pi * 53) * 0.1) * (0.4 + 0.2 * math.sin(t * 0.7)) * edge
        samples.extend(struct.pack('<h', int(max(-0.95, min(0.95, value)) * 32767)))
    with wave.open(str(ROOT / f'ww2-{name}.wav'), 'wb') as out:
        out.setparams((1, 2, RATE, 0, 'NONE', 'not compressed'))
        out.writeframes(samples)
