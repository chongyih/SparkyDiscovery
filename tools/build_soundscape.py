"""Builds the chapter ambience from free field recordings (see assets/audio/README.md).

Requires numpy, scipy and soundfile. Sources download once into ignored artifacts/.
"""
from pathlib import Path
import io, urllib.request, zipfile
import numpy as np, soundfile as sf
from scipy.signal import butter, resample_poly, sosfiltfilt

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'artifacts/audio-sources'
OUT = ROOT / 'assets/audio'
BSB = 'https://bigsoundbank.com/UPLOAD/ogg/'
COMMONS = 'https://upload.wikimedia.org/wikipedia/commons/'
KENNEY = 'https://kenney.nl/media/pages/assets/impact-sounds/87b4ddecda-1677589768/kenney_impact-sounds.zip'
SOURCES = {
    'village.ogg': BSB + '1346.ogg',
    'restaurant.ogg': BSB + '3542.ogg',
    'fan.ogg': BSB + '0079.ogg',
    'cicadas.ogg': BSB + '3002.ogg',
    'koel.flac': COMMONS + '1/19/Asian_koel_1.flac',
    'myna.mp3': COMMONS + '7/7b/Acridotheres_tristis_-_Common_Myna_XC509296.mp3',
}

def fetch(name, url):
    path = CACHE / name
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(url, headers={'User-Agent': 'SparkyDiscovery soundscape build'})
        path.write_bytes(urllib.request.urlopen(request).read())
    return path

def load(name, start=0.0, end=None, rate=22050):
    data, sr = sf.read(fetch(name, SOURCES[name]), always_2d=True)
    data = data.mean(1)[int(start * sr):None if end is None else int(end * sr)]
    return resample_poly(data, rate, sr), rate

def band(x, rate, low=None, high=None):
    if low:
        x = sosfiltfilt(butter(4, low, 'highpass', fs=rate, output='sos'), x)
    if high:
        x = sosfiltfilt(butter(4, high, 'lowpass', fs=rate, output='sos'), x)
    return x

def seamless(x, rate, fade):
    """Equal-power crossfade of the tail into the head, so the loop has no seam."""
    n = int(fade * rate)
    t = np.linspace(0, np.pi / 2, n)
    body = x[:-n].copy()
    body[:n] = body[:n] * np.sin(t) + x[-n:] * np.cos(t)
    return body

def edges(x, rate, fade=0.05):
    n = int(fade * rate)
    x = x.copy()
    x[:n] *= np.linspace(0, 1, n)
    x[-n:] *= np.linspace(1, 0, n)
    return x

def even(x, rate, window=0.4, ratio=0.6):
    """Slow compressor: pulls laughs and clatter towards the room's average level."""
    n = int(window * rate)
    envelope = np.sqrt(np.convolve(x ** 2, np.ones(n) / n, 'same')) + 1e-6
    return x * (np.sqrt(np.mean(x ** 2)) / envelope) ** ratio

def write(name, x, rate, rms_db=None, peak_db=-1.0):
    """Matches beds by RMS, one-shots by peak, and never lets either clip."""
    gain = 10 ** (rms_db / 20) / np.sqrt(np.mean(x ** 2)) if rms_db is not None else np.inf
    gain = min(gain, 10 ** (peak_db / 20) / np.abs(x).max())
    sf.write(OUT / (name + '.ogg'), x * gain, rate, format='OGG', subtype='VORBIS', compression_level=0.55)
    print(f'{name}: {len(x) / rate:.1f}s, {(OUT / (name + ".ogg")).stat().st_size // 1024} KB')

# Daytime village square: birds and the occasional distant vehicle. Stops before a close car at 2:15.
x, r = load('village.ogg', 0, 133)
write('street', seamless(band(x, r, 60, 8000), r, 3), r, -22)
# Neighbours chatting. Low-passed until the conversation is indistinct and no language is recognisable.
x, r = load('restaurant.ogg', 4, 96)
write('neighbours', seamless(even(band(x, r, 140, 950), r), r, 3), r, -22)
# Electric fan softened into a slow ceiling fan: duller air, gentle three-blade swish at 0.5 rev/s.
x, r = load('fan.ogg', 0.2, 9.8)
x = seamless(band(x, r, 90, 1600), r, 0.6)
swish = 1 + 0.18 * np.sin(2 * np.pi * round(1.5 * len(x) / r) * np.arange(len(x)) / len(x))
write('ceiling-fan', x * swish, r, -22)
# Tropical afternoon heat, kept well under everything else in game.
x, r = load('cicadas.ogg', 0, None)
write('cicadas', seamless(band(x, r, 1500), r, 3), r, -24)
# Occasional one-shot bird calls from the trees. The koel's rising "ko-el" is a familiar Singapore call.
x, r = load('koel.flac', 13.9, 26.3, 44100)
write('koel-long', edges(band(x, r, 700, 9000), r), r, -24)
x, r = load('koel.flac', 6.6, 10.9, 44100)
write('koel-short', edges(band(x, r, 700, 9000), r), r, -24)
x, r = load('myna.mp3', 12.2, 17.4, 44100)
x = band(x, r, 500, 10000)
# The calls are sharp clicks; soft saturation lifts them to roughly the koel's loudness.
write('myna', edges(np.tanh(4 * x / np.abs(x).max()), r), r, peak_db=-3)
# Kenney CC0 foley: five concrete footsteps and a light metal knock for the aerial.
kenney = zipfile.ZipFile(io.BytesIO(fetch('kenney_impact-sounds.zip', KENNEY).read_bytes()))
for i in range(5):
    x, r = sf.read(io.BytesIO(kenney.read(f'Audio/footstep_concrete_00{i}.ogg')), always_2d=True)
    write(f'footstep-{i + 1}', x.mean(1), r, peak_db=-3)
x, r = sf.read(io.BytesIO(kenney.read('Audio/impactMetal_light_000.ogg')), always_2d=True)
write('aerial-click', x.mean(1), r, peak_db=-3)
# Untuned analogue TV: the bright, full-band "shhh" of snow, which is itself white noise.
# A slight, slow shimmer keeps the 4-second loop from sounding mechanical.
r = 44100
t = np.arange(4 * r) / r
rng = np.random.default_rng(1965)
shimmer = 1 + 0.06 * np.sin(2 * np.pi * 0.5 * t) + 0.03 * np.sin(2 * np.pi * 1.75 * t)
write('tv-static', band(rng.standard_normal(len(t)), r, 120, 16000) * shimmer, r, -20)
