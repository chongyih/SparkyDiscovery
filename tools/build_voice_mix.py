"""Normalize downloaded Kelvin takes; retain originals under artifacts/voice-originals.
Run from the repository root after adding/updating recordings in assets/voice.
To replace a take, replace its original in artifacts/voice-originals before rerunning.
"""
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ORIGINALS = ROOT / 'artifacts/voice-originals'
ORIGINALS.mkdir(parents=True, exist_ok=True)
report = {}
for name in ('neighbour_01', 'after_broadcast', 'homes', 'jobs', 'future', 'farewell', 'signal_found', 'come_sit'):
    destination = ROOT / 'assets/voice' / (name + '.mp3')
    original = ORIGINALS / destination.name
    if not original.exists():
        shutil.copy2(destination, original)
    base = ['ffmpeg', '-hide_banner', '-nostats', '-i', str(original)]
    scan = subprocess.run(base + ['-af', 'loudnorm=I=-21:TP=-2:LRA=7:print_format=json', '-f', 'null', '-'], capture_output=True, text=True, check=True)
    stats = json.loads(scan.stderr[scan.stderr.rfind('{'):scan.stderr.rfind('}') + 1])
    effect = ('loudnorm=I=-21:TP=-2:LRA=7:linear=true:measured_I={input_i}:'
              'measured_TP={input_tp}:measured_LRA={input_lra}:measured_thresh={input_thresh}:'
              'offset={target_offset}').format(**stats)
    subprocess.run(base + ['-af', effect, '-ar', '44100', '-ac', '1', '-b:a', '128k', '-y', str(destination)], capture_output=True, check=True)
    report[name] = stats
    print('Mixed:', name)
(ORIGINALS / 'mix-report.json').write_text(json.dumps(report, indent=2) + '\n')
