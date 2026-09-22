# Archival footage: 9 August 1965

The game plays a continuous excerpt of the actual Lee Kuan Yew press conference, not a recreation or synthetic voice.

- Source file: [Lee Kuan Yew's press conference on 9 Aug 1965.webm](https://commons.wikimedia.org/wiki/File:Lee_Kuan_Yew%27s_press_conference_on_9_Aug_1965.webm).
- Source page revision: [1256918464](https://commons.wikimedia.org/w/index.php?title=File:Lee_Kuan_Yew%27s_press_conference_on_9_Aug_1965.webm&oldid=1256918464).
- File-page attribution: Singapore Broadcasting Corporation. The recording dates to 9 August 1965; the named corporation is the archive attribution supplied by the uploader, not a claim about the broadcaster's name in 1965.
- File-page rights designation: public domain, under the PD-SG-broadcast and PD-1996 tags. This records the source's designation.
- Retrieved: 22 September 2026.
- Included excerpt: source 02:08–04:06, continuously trimmed, 118 seconds. Original audio and pauses are retained. No speech is rearranged or regenerated.
- Conversion: 960×720 WebM to 640×480 Ogg Theora / Vorbis for native Godot playback. The source is kept only in ignored `artifacts/`; the game ships the converted excerpt.

## Captions

Adapted from [Wikimedia Commons English TimedText contributors](https://commons.wikimedia.org/wiki/TimedText:Lee_Kuan_Yew%27s_press_conference_on_9_Aug_1965.webm.en.srt), [revision 1164450134](https://commons.wikimedia.org/w/index.php?title=TimedText:Lee_Kuan_Yew%27s_press_conference_on_9_Aug_1965.webm.en.srt&oldid=1164450134), under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).

Changes: selected the excerpt's cues, offset timestamps by 128 seconds, split one long cue, and lightly adjusted punctuation. `lky-1965-en.json` remains available under CC BY-SA 4.0; this does not change the licence of other game files. Long silent pauses deliberately have no invented captions.

## Reproduce the conversion

```sh
ffmpeg -ss 128 -i lky-1965-source.webm -t 118 -vf scale=640:480 \
  -c:v libtheora -q:v 7 -g 64 -c:a libvorbis -q:a 5 -ac 2 \
  lky-1965-excerpt.ogv
```

### Web copy

Browsers decode Theora in WebAssembly on the main thread, where the 640×480 / 25 fps excerpt needed more than a second of CPU per second of footage. Web exports therefore ship `lky-1965-excerpt-web.ogv` instead: the same 118-second cut at 320×240 / 12 fps (3.2 MB), with the original audio. Desktop exports keep the full excerpt. Each preset excludes the file its platform does not use.

The Homebrew ffmpeg build has no Theora encoder, so frames and audio were extracted with ffmpeg and re-encoded by Godot 4.7's Movie Maker (Theora/Vorbis, video quality 0.8, audio quality 0.5, keyframe interval 64, 44.1 kHz). The replay script showed frame *n* on frame *n* and started the audio on the first frame.

```sh
ffmpeg -ss 128 -i lky-1965-source.webm -t 118 -vf "scale=320:240:flags=lanczos,fps=12" frames/%05d.png
ffmpeg -ss 128 -i lky-1965-source.webm -t 118 -vn -ac 2 -ar 44100 -c:a pcm_s16le audio.wav
godot --path <replay project> --script record.gd --write-movie lky-1965-excerpt-web.ogv --fixed-fps 12
```

With a Theora-enabled ffmpeg, `-vf scale=320:240 -r 12` on the command above gives an equivalent file.

Historical corroboration: [National Archives press-conference transcript](https://www.nas.gov.sg/archivesonline/data/pdfdoc/lky19650809b.pdf) and [National Museum gallery guide](https://www.nhb.gov.sg/nationalmuseum/-/media/nms2017/documents/senior-programmes/nms-easy-publications-shg-seniors-online.pdf).
