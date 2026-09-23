"""Rebuild short dialogue clips from the existing normalized takes.

Boundaries in pages.json fall inside detected pauses; no spoken text is changed.
Run from the repository root. Requires ffmpeg. Listening review should accompany
any timing changes, especially for local expressions and pauses.
"""
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / 'assets/voice/pages.json').read_text())
originals = {Path(line['file']).stem: line['text'] for line in json.loads(
    (root / 'assets/voice/lines.json').read_text())['lines']}
for name, pages in manifest.items():
    assert ' '.join(originals[name].split()) == ' '.join(' '.join(p['text'] for p in pages).split()), name
    previous = 0
    for page in pages:
        assert page['start'] == previous and page['end'] > page['start'], name
        previous = page['end']
        target = root / page['audio'].removeprefix('res://')
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i',
                        str(root / 'assets/voice' / (name + '.mp3')),
                        '-ss', str(page['start']), '-t', str(page['end'] - page['start']),
                        '-codec:a', 'libmp3lame', '-q:a', '3', str(target)], check=True)
print('Built dialogue pages; original words and contiguous timing validated.')
