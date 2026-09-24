# Archival footage: 9 August 1965 (Chapter 2)

Boon's television plays a continuous excerpt of the actual press conference given by Prime Minister
Lee Kuan Yew on 9 August 1965. It is not a recreation or a synthetic voice.

- Source file: [Lee Kuan Yew's press conference on 9 Aug 1965.webm](https://commons.wikimedia.org/wiki/File:Lee_Kuan_Yew%27s_press_conference_on_9_Aug_1965.webm), Wikimedia Commons.
- File-page attribution: Singapore Broadcasting Corporation (the archive attribution supplied by the uploader).
- File-page rights designation: public domain (PD-SG-broadcast, PD-1996). This records the source's designation.
- Excerpt: source 02:08–04:06, 118 s, continuous. Original audio and pauses kept; no speech rearranged or regenerated.
  The archive's burned-in timecode and a black band were cropped (the picture is scaled back to 4:3).
- `lky-1965.mp4`: 640×480, 25 fps, H.264 (Main), AAC mono 80 kb/s, loudness-normalised to −18 LUFS, `+faststart`
  (plays in iOS Safari). Converted from the copy kept in the Godot project (`../SparkyDiscovery/artifacts/lky-1965-source.webm`).
- Corroboration: [National Archives of Singapore transcript, lky19650809b](https://www.nas.gov.sg/archivesonline/data/pdfdoc/lky19650809b.pdf).
  The National Archives also holds the recording ("Prime Minister Meets The Press", accession 1997002660), credited there
  "Courtesy of Mediacorp Pte Ltd". Check reuse terms with Mediacorp before any commercial release.

## Captions

`lky-1965-en.json` is adapted from [Wikimedia Commons English TimedText contributors](https://commons.wikimedia.org/wiki/TimedText:Lee_Kuan_Yew%27s_press_conference_on_9_Aug_1965.webm.en.srt)
under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) (cues offset to the excerpt, one long cue split,
punctuation lightly adjusted; long silences have no invented captions). This does not change the licence of other game files.

## Reproduce

```sh
ffmpeg -ss 128 -i lky-1965-source.webm -t 118 \
  -vf "crop=iw*0.85:ih*0.85:iw*0.075:ih*0.055,scale=640:480:flags=lanczos,fps=25" \
  -c:v libx264 -profile:v main -pix_fmt yuv420p -crf 30 -preset slow -tune film -g 50 \
  -af "loudnorm=I=-18:TP=-2:LRA=11" -ac 1 -ar 44100 -c:a aac -b:a 80k -movflags +faststart lky-1965.mp4
```
