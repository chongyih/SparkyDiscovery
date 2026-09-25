# Audio

All files are mono MP3 (LAME CBR, with a Xing/LAME header), built by `tools/build_audio.py`
(Python standard library + ffmpeg, deterministic). Total: about 2.5 MB.

The recordings are modern and illustrate the scene. None of them is archival sound from Singapore in 1942.

## Looping

`loops.json` lists every file with its duration, sample rate and bitrate. For loops it also gives
`loopStart`, `loopEnd` and `loopLength` in seconds.

MP3 encoders add about 1105 samples of silence at the start and pad the last frame. Some decoders
remove this padding and some do not, so looping a plain MP3 with `loop = true` can click or leave a
gap. To avoid this, every loop file is **wrap-padded**: it holds the last 0.25 s of the loop, then
the loop, then the first 0.25 s of the loop. Play it with Web Audio like this:

```js
src.buffer = buffer;
src.loop = true;
src.loopStart = info.loopStart;   // 0.25 s (0.249977 s at 22.05 kHz)
src.loopEnd = info.loopEnd;
src.start(0, info.loopStart);
```

The padding is real loop audio, so the seam stays smooth whether or not the decoder removed the
encoder delay. Any offset up to 0.25 s is absorbed. `loopEnd - loopStart` is always exactly one
loop period. Don't loop these files with `<audio loop>`.

I chose this over AAC/M4A. Browsers are not consistent about gapless AAC either, and MP3 is the
format the design doc specifies. When ffmpeg decodes these files, it removes the delay exactly.
The build prints a seam check for every loop: there is no level dip beyond the normal variation
of the material, and no click.

| File | Dur. (s) | Loop (start–end s) | Rate / kbps |
| --- | --- | --- | --- |
| `siren.mp3` | 25.23 | 0.249977–24.983764 (24.73 s) | 22.05k / 64 |
| `street.mp3` | 60.50 | 0.249977–60.249977 (60 s) | 22.05k / 48 |
| `murmur.mp3` | 45.50 | 0.249977–45.249977 (45 s) | 22.05k / 48 |
| `cicadas.mp3` | 45.97 | 0.249977–45.721043 (45.47 s) | 22.05k / 48 |
| `rumble.mp3` | 12.85 | 0.249977–12.600000 (12.35 s) | 22.05k / 48 |
| `radio-static.mp3` | 8.50 | 0.249977–8.249977 (8 s) | 22.05k / 48 |
| `shelter-room.mp3` | 20.50 | 0.249977–20.249977 (20 s) | 22.05k / 48 |
| `theme-1942.mp3` | 72.50 | 0.25–72.25 (72 s) | 32k / 64 |
| `fire-crackle.mp3` | 12.50 | 0.249977–12.249977 (12 s) | 22.05k / 48 |
| `night-ambience.mp3` | 30.50 | 0.249977–30.249977 (30 s) | 22.05k / 48 |
| `heartbeat.mp3` | 6.50 | 0.249977–6.249977 (6 s = 8 beats at 80 bpm) | 22.05k / 48 |
| `aircraft.mp3` | 12.00 | one-shot | 22.05k / 64 |
| `impact.mp3` | 4.00 | one-shot | 22.05k / 64 |
| `distant-explosion.mp3` | 4.50 | one-shot | 22.05k / 64 |
| `door.mp3` | 1.00 | one-shot | 22.05k / 64 |
| `shutter.mp3` | 0.80 | one-shot | 22.05k / 64 |
| `camera-shutter.mp3` | 1.25 | one-shot | 44.1k / 64 |
| `paper.mp3` | 1.15 | one-shot | 44.1k / 64 |
| `whistle.mp3` | 1.45 | one-shot | 44.1k / 64 |
| `pickup-chime.mp3` | 1.70 | one-shot | 44.1k / 64 |
| `ui-click.mp3` | 0.06 | one-shot | 44.1k / 64 |
| `shell-whistle.mp3` | 1.80 | one-shot. It stops dead by design, so play `impact` or `distant-explosion` right after. | 44.1k / 64 |
| `ear-ring.mp3` | 3.20 | one-shot, fades out. Deliberately quiet (−12 dBFS peak). | 44.1k / 64 |
| `paper-piece.mp3` | 0.60 | one-shot | 44.1k / 64 |
| `myna.mp3`, `koel-short.mp3` | 5.20, 4.30 | one-shot | 44.1k / 64 |
| `footstep-1…5.mp3` | ~0.11 each | one-shot | 44.1k / 64 |

One-shots keep the usual short MP3 start delay (≈25 ms at 44.1 kHz, ≈50 ms at 22.05 kHz) if the
decoder doesn't remove it. That is why the UI, camera and footstep sounds are 44.1 kHz.

## Sources and licences

| File | Source | Licence | Changes |
| --- | --- | --- | --- |
| `siren.mp3` | [Civil-defense-siren-waver.ogg](https://commons.wikimedia.org/wiki/File:Civil-defense-siren-waver.ogg), Techtonic, recorded in St. Paul, Minnesota, 5 Nov 2008, via Wikimedia Commons | Public domain (released by the author) | From 8.00 s: a 24.73 s loop chosen to match the waver's pitch, a 1.5 s equal-power crossfade, level matched to the Godot project's gameplay siren. A modern US siren, not a 1942 Singapore one. |
| `street.mp3` | [Village, City Center #1](https://bigsoundbank.com/village-city-center-1-s1346.html), Joseph Sardin, BigSoundBank (via the Godot project's `street.ogg`) | CC0 | 0:00–1:02 of the processed file, re-looped to 60 s with a 2 s crossfade |
| `murmur.mp3` | [Small Restaurant Conversations](https://bigsoundbank.com/small-restaurant-conversations-s3542.html), Joseph Sardin, BigSoundBank (via `neighbours.ogg`) | CC0 | Low-passed murmur, re-looped to 45 s with a 2 s crossfade |
| `cicadas.mp3` | [Cicadas](https://bigsoundbank.com/cicadas-s3002.html), Joseph Sardin, BigSoundBank (via `cicadas.ogg`) | CC0 | Format conversion only (already looped) |
| `koel-short.mp3` | [Asian koel 1.flac](https://commons.wikimedia.org/wiki/File:Asian_koel_1.flac), Yosef Ben Melamed, via Wikimedia Commons | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) | 0:06.6–0:10.9, band-passed, faded (Godot project), then converted. The adapted clip stays CC BY-SA 4.0. |
| `myna.mp3` | [Common Myna XC509296](https://commons.wikimedia.org/wiki/File:Acridotheres_tristis_-_Common_Myna_XC509296.mp3), James Ray (xeno-canto), via Wikimedia Commons | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) | 0:12.2–0:17.4, band-passed, soft-saturated, faded, then converted. The adapted clip stays CC BY-SA 4.0. |
| `footstep-1…5.mp3` | [Impact Sounds](https://kenney.nl/assets/impact-sounds), Kenney (`footstep_concrete_000–004`) | CC0 | Mono, converted |
| `aircraft.mp3`, `impact.mp3`, `door.mp3`, `shutter.mp3`, `rumble.mp3` | Godot project's `tools/build_ww2_audio.py`: original synthetic effects | Original (game's own) | Converted. `rumble` is looped from 0.15–13.7 s with a 1.2 s crossfade. |
| `camera-shutter.mp3`, `radio-static.mp3`, `paper.mp3`, `whistle.mp3`, `shelter-room.mp3`, `distant-explosion.mp3`, `ui-click.mp3`, `pickup-chime.mp3`, `shell-whistle.mp3`, `ear-ring.mp3`, `fire-crackle.mp3`, `night-ambience.mp3`, `heartbeat.mp3`, `paper-piece.mp3` | `tools/build_audio.py`: synthesised from noise, filters and sine partials | Original (game's own) | — |
| `theme-1942.mp3` | `tools/build_audio.py`: original composition (music box and soft felt piano; A minor pentatonic, lifting to C major in the middle; 80 bpm, 24 bars) | Original (game's own) | Circular render + circular convolution reverb, so the loop is seamless |

The koel and myna recordists should be credited in the album credits (`credits.audio` in
`src/chapters/ww2-text.js`). The CC BY-SA licence of those two clips doesn't change the licence of
any other game file.

## Captions

Every sound has an accessibility caption in `src/chapters/ww2-text.js` → `captions`, keyed by the
file name (footsteps share `footstep`).

## Rebuild

```sh
python3 tools/build_audio.py                 # everything
python3 tools/build_audio.py --only theme-1942 whistle
```

## Chapter 2 (1965) additions

| File | Source | Licence |
| --- | --- | --- |
| `ceiling-fan.mp3` | [Electric fan #2](https://bigsoundbank.com/electric-fan-2-s0079.html), Joseph Sardin, BigSoundBank (via the Godot project's `ceiling-fan.ogg`) | CC0 |
| `tv-static.mp3` | Generated white noise with a slight shimmer (Godot project's `tv-static.ogg`) | Original |
| `kopi-pour.mp3`, `cup-clink.mp3`, `spoon-stir.mp3`, `firecrackers.mp3` | Synthesised by `tools/build_audio.py` | Original |
| `radio-song.mp3` | Original tune in the style of 1960s Malay pop (joget), synthesised and radio-filtered by `tools/build_audio.py` | Original |

The TV's press-conference audio is part of the archival video: see `public/assets/video/ATTRIBUTION.md`.

## Chapter 3 sounds (`tools/build_audio_ns.py`)

- The drill has no cue sound: commands are shown on screen and the section's boots answer them.
- `band-march.mp3` (loop): an original synthesised march, 116 bpm.
- `truck-engine.mp3` (loop): a synthesised lorry idle.
