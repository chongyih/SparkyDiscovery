"""Original, deterministic ambience and foley; no recordings or speech samples."""
from pathlib import Path
import array, math, random, wave
RATE = 22050
OUT = Path(__file__).resolve().parents[1] / 'assets/audio'
OUT.mkdir(exist_ok=True)
rng = random.Random(1965)
def write(name, data):
    peak = max(abs(x) for x in data) or 1
    gain = min(1, .65 / peak)
    pcm = array.array('h', (int(max(-1,min(1,x*gain))*32767) for x in data))
    with wave.open(str(OUT / (name + '.wav')), 'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(RATE); f.writeframes(pcm.tobytes())
    print(name, len(data)/RATE, 'seconds; peak', round(peak*gain,3))
def noise(n, smoothing):
    state=0; out=[]
    for _ in range(n):
        state=state*smoothing+rng.uniform(-1,1)*(1-smoothing)
        out.append(state)
    return out
# Soft periodic fan motor with air, all periodic tones meet at the loop boundary.
n=RATE*12; air=noise(n,.86)
write('ceiling-fan', [(air[i]*.45 + .08*math.sin(2*math.pi*50*i/RATE) + .025*math.sin(2*math.pi*100*i/RATE))*(.78+.22*math.cos(2*math.pi*2*i/RATE)) for i in range(n)])
# Distant rolling street bed, no modern sirens, horns or conspicuous machinery.
n=RATE*24; street=noise(n,.975)
write('street', [street[i]*(.9+.35*math.sin(2*math.pi*i/n)) + .018*math.sin(2*math.pi*45*i/RATE)*(.5+.5*math.cos(2*math.pi*i/n)) for i in range(n)])
# Indistinct, low-level vocal murmur: formant-like harmonics, never actual words.
n=RATE*20; crowd=[0.0]*n
for voice in range(5):
    base=95+voice*27
    for phrase in range(5):
        start=rng.uniform(.2,17.2); duration=rng.uniform(.8,2.0)
        a=int(start*RATE); b=min(n,int((start+duration)*RATE))
        for i in range(a,b):
            t=(i-a)/RATE; env=math.sin(math.pi*t/duration)**2
            syllable=(.5+.5*math.sin(2*math.pi*3.1*t+voice))**2
            tone=sum(math.sin(2*math.pi*(base*k)*t)*math.exp(-((base*k-550)/400)**2)/k for k in range(1,9))
            crowd[i]+=.055*env*syllable*tone
write('quiet-murmur',crowd)
for name,length in [('footstep',.18),('aerial-click',.10)]:
    n=int(RATE*length); dust=noise(n,.35)
    write(name, [(dust[i]*.24+.28*math.sin(2*math.pi*85*i/RATE))*math.exp(-i/(RATE*.033))*min(1,i/60) for i in range(n)])
