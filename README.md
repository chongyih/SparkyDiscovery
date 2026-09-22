# Sparky Discovery — playable prototype

The game currently contains **one chapter: 9 August 1965**. It is a small, explorable third-person neighbourhood. Other chapters are on hold until this one has been reviewed.

## Play

1. Open this folder's `project.godot` in Godot 4.7.2.
2. Press **F5**, then choose **Step into 1965**.
3. Follow the gold marker: speak to Uncle Tan on the shophouse pavement, collect and fit the spare aerial, then tune the television.

Desktop builds use the **Mobile renderer**. Browser builds use **Compatibility** rendering and a single-threaded Web export. Phone browsers get a floating thumbstick (touch anywhere on the left half and slide), drag-to-look on the right half (double-tap there to centre the camera), a round Interact button that turns gold and names the action near the marker, and Journal and Pause buttons at the top right. Play in landscape. Phone performance and browser compatibility still need real-device playtesting.

## Publishing to itch.io

Pushing to `main` runs [Publish to itch.io](.github/workflows/publish-itch.yml): import with Godot 4.7.2, run the gameplay checks, export browser/Windows/Linux/macOS builds, save a GitHub Actions artifact, then upload each build using Butler. You can also run it manually from GitHub's Actions tab on `main`.

One-time setup:

1. Create an itch.io game page and set **Kind of project** to **HTML**. A draft page works for initial testing.
2. In GitHub **Settings → Secrets and variables → Actions → Variables**, add `ITCH_PROJECT` as `username/game-slug` (for example, `your-name/sparky-discovery`). Use the username and slug from the itch.io URL, not the game title.
3. Generate an [itch.io API key](https://itch.io/user/settings/api-keys) and save it under **Secrets** as `BUTLER_API_KEY`. Never commit it or paste it into chat.
4. Push to `main` or manually run the workflow. After the first upload, edit the itch.io page and mark the `html5` upload **This file will be played in the browser**. Enable fullscreen and mobile-friendly play, with landscape orientation. Save the page. See [Butler's browser-upload instructions](https://itch.io/docs/butler/pushing.html#html-playable-in-browser-games).

Uploads use the `html5`, `windows`, `linux` and `macos` channels. Later pushes update those same uploads. Windows and Linux are x86-64; macOS includes Apple Silicon and Intel. Desktop builds are not signed with a publisher certificate or notarized; macOS uses ad-hoc signing, so normal OS download protections may require additional user steps.

If the itch.io settings are missing, the workflow still builds and saves its artifact, then fails with a setup message before uploading. Artifacts are kept for seven days. Native Android/iOS builds are not part of this workflow. Android APKs can be offered as separate itch.io downloads later; mobile browser play needs no app-store installation.

For local exports, install the **4.7.2** export templates in Godot, create the output directories, then run:

```sh
mkdir -p build/{web,windows,linux,macos}
touch build/.gdignore
godot --headless --editor --import
godot --headless --export-release "Web" build/web/index.html
godot --headless --export-release "Windows Desktop" build/windows/SparkyDiscovery.exe
godot --headless --export-release "Linux" build/linux/SparkyDiscovery.x86_64
godot --headless --export-release "macOS" build/macos/SparkyDiscovery.zip
```

Use your Godot executable's full path if `godot` is not on your PATH. Serve `build/web` over HTTP to test it; opening `index.html` as a local file will not work. Export presets include runtime caption JSON and attribution files and exclude development previews. Generated builds are ignored by Git.

| Control | Action |
| --- | --- |
| WASD / arrows | Move relative to the camera |
| Mouse | Orbit the third-person camera |
| Scroll wheel | Zoom |
| R | Centre the camera behind Sparky |
| E | Interact nearby / continue dialogue |
| J | Sparky's journal |
| ← / → (in the journal) | Turn pages |
| Esc | Pause / release the mouse |
| Tab / Enter | Navigate / activate menu controls |
| Space (during broadcast) | Pause / resume the footage |
| V (during broadcast) | Switch between community and close television views |

Progress saves locally after each encounter. Pause offers restart and return-to-title controls. The journal is an open book: a contents page, a log of the chapter that fills in as Sparky completes each step, a merger-to-separation timeline, notes on what came next, sources, a page separating real from imagined content, controls and credits. The television plays a 1 minute 58 second excerpt of the actual Lee Kuan Yew press conference, with original audio, optional English captions, pause, mute and skip controls. The source and rights designation are recorded in `assets/video/ATTRIBUTION.md`. Uncle Tan now speaks a short Singlish audition generated with ElevenLabs, with matching subtitles and replay/mute controls. Continuing stops the voice. Generation details are in `assets/voice/README.md`; other dialogue is text-only.

The broadcast plays directly on the wooden television in the open ground floor of a residential block, with flats and common corridors above. The shops face it from across the road. All four slatted benches angle inward towards the TV, with seated characters aligned to their benches. Seven neighbours gather with cups, a thermos and a slowly turning ceiling fan nearby. On the foreground-left bench, one neighbour raises a handkerchief to dab her eyes while her companion turns towards her and pats her shoulder. The eye-wiping happens briefly three times across the clip, with long quiet rests. Sparky sits on an angled left-hand bench beside a neighbour; the community camera shows his face, the reacting pair and the television together. **Walk around** returns him to the aisle; choosing a viewing camera seats him again. These reactions are fictional interpretations. Use **Community view**, **TV view**, or **Walk around** to choose how Sparky watches; press **Esc** to release the mouse and pause while walking.

## Current review scope

Sparky now visibly fits the aerial before tuning. After tuning, Uncle Tan walks over from the pavement while Sparky approaches the bench and settles into his seat; both sequences can be skipped. During the broadcast, Sparky briefly lowers his head and glances towards the reacting couple. Afterwards, an optional conversation with Uncle Tan explores homes, jobs and Singapore's future. These new lines are text-only, with fictional dialogue separated from sourced historical notes.

Ambience from free field recordings (CC0, plus CC BY-SA 4.0 bird calls credited in the journal) adds a daytime street, cicadas, occasional koel and myna calls from the trees, a ceiling fan, varied footsteps and indistinct neighbours' conversation that fades during the footage. Untuned TV static follows the tuning dial. Uncle Tan's voice sits a little under the broadcast, with ambience well below both. Pause includes an **Ambient sound** toggle. The build script, sources and licences are in `tools/build_soundscape.py` and `assets/audio/README.md`. The opening camera faces along the pavement towards Uncle Tan; shop signs and awnings also block the orbit camera.

This first chapter is intended for a short playtest of movement, camera, exploration, interactions and storytelling. NPCs and environment meshes are placeholders. The streets and block are illustrative rather than a reconstruction of a named Singapore neighbourhood. NHB’s [history of void decks](https://www.nhb.gov.sg/~/media/nhb/files/resources/publications/ebooks/nhb_ebook_void_decks.pdf) records an early example at Jalan Klinik in 1963, while noting that widespread provision and the term came later. The block is an imagined early example, not a claim that open ground floors were standard in 1965. Upper-floor flats are scenery; the playable area remains at ground level. The full game's 5–10 minute duration is not a claim about this single chapter.

## Development

- `game/main.gd`: chapter state, interaction gates and checkpoints.
- `game/player.gd`: Sparky's movement and imported animations.
- `game/follow_camera.gd`: mouse orbit, zoom and camera collision.
- `game/world.gd`: the neighbourhood and interactable props.
- `game/community.gd`: communal seating, neighbours and broadcast reactions.
- `game/chapter_staging.gd`: interruptible aerial fitting and walk-to-seat sequences.
- `game/soundscape.gd`: positional ambience, footsteps and broadcast audio transitions.
- `game/interface.gd`: title, HUD, dialogue, tuner, journal and pause UI.
- `game/history.gd`: the 1965 story and historical references.
- `tests/playthrough.gd`: gameplay, collision, puzzle and persistence checks.
- `tests/render_preview.gd`: actual-renderer screenshots in `artifacts/`.

On macOS:

```sh
/Applications/Godot.app/Contents/MacOS/Godot --headless --path . --script res://tests/playthrough.gd -- --test
/Applications/Godot.app/Contents/MacOS/Godot --path . --script res://tests/render_preview.gd -- --test
```

`--test` isolates the tests from real player progress. The playthrough test takes about 20 seconds. It seeks through the archival clip rather than playing all of it, but still lets the final seconds play so the real end-of-file signal is checked. Screenshots require graphics access. The supplied Blender source remains intact; direct Blender import is disabled because the game uses the exported GLB.

---

# Sparky — refined 3D character

A stylised interpretation of your bear photograph, with a navy hoodie, DSTA chest lettering, hood, pocket, cream paws, and button eyes. This refinement makes Sparky stockier, shortens his legs, slightly reduces his head, adds broad fabric folds, softens the rounded muzzle, and gives his walk a gentle sway with delayed arm/head movement and planted-foot height correction. The continuous hood shell and fitted chest lettering preserve the side-profile fixes. The back is an interpretation because the reference only shows the front.

The original version is preserved in `assets/sparky/v1`. The version immediately before this refinement is in `assets/sparky/before-refinement`.

## Easiest way to see him move: Godot

1. Open this folder's `project.godot` in Godot.
2. Open `scenes/character_studio.tscn` from the FileSystem panel.
3. Press **F6** (Run Current Scene). F5 continues to run the main game.
4. Click **Idle**, **Walk**, or **Wave**. Drag the background to rotate the view; scroll to zoom. There is also a pause/resume button.

This is a character viewer, not the historical adventure game. It uses the final GLB directly, with studio lighting and animation controls. Its fur avoids tiny per-fibre cast shadows, and the floor uses a soft contact-shadow graphic. Those are preview scene choices rather than baked changes to the character.

## Open your model

1. Start Blender.
2. Choose **File → Open** and open `assets/sparky/sparky.blend` in this folder.
3. The file opens with a camera view of Sparky. Press **Space** with the pointer over the timeline to play the gentle idle animation; press it again to stop.
4. Use **Render → Render Image** for a lit preview. The PNG previews are already available in the same folder.

The model is already built. You do not need to run any Python scripts.

## Files

- `assets/sparky/sparky.blend` — editable Blender source with lights and a camera.
- `assets/sparky/sparky.glb` — exported character for Godot, containing materials, a seven-bone skeleton, and Idle, Walk, and Wave animations. Studio lights and floor are excluded.
- `assets/sparky/sparky-preview.png` — three-quarter preview.
- `assets/sparky/sparky-walk.gif` — looping preview of the exported walk.
- `assets/sparky/sparky-front.png`, `sparky-back.png`, and `sparky-side.png` — additional views.
- `tools/build_sparky.py` — reproducible creation script, last run with Blender 5.2.2.
- `assets/sparky/validation.json` — Blender round-trip validation result.
- `assets/sparky/godot-validation.json` — Godot import and animation checks.

## Later: use in Godot 4

1. Copy **only `sparky.glb`** into your Godot project's asset folder. Keep the Blender source outside that folder to avoid importing the studio scene too.
2. Drag the GLB from Godot's FileSystem panel into a 3D scene.
3. The exported animations are named `Idle`, `Walk`, and `Wave`. Configure Idle and Walk to loop in Godot's animation import settings.
4. For a controllable character, place the model under a `CharacterBody3D`, add a capsule `CollisionShape3D`, and add movement and animation logic. These gameplay pieces are not part of this model deliverable.

The model is about 2.1 units tall. It faces Blender -Y, which becomes glTF/Godot +Z. Orient the visual child to match your controller's forward direction (often a 180-degree Y rotation).

## Scope and checks

This is a prototype character with a seven-bone rig and blended weights at the shoulders and upper legs. Other parts follow individual bones. It has simple plush movement, rather than a full anatomical rig or cloth simulation. The hands have no individual fingers. Walk is in place, with no root travel.

Short tapered mesh fibres create the fur, supported by packed surface-normal textures. Cotton has a separate woven normal texture. These are exported in the GLB; they do not rely on Blender-only particle hair or procedural shaders. The materials need no external texture files. Use Material Preview or Rendered shading in Blender to see the textures; Solid mode does not display them.

The refined model has **73,854 triangles and a 7.94 MB GLB**, down from 398,546 triangles and 28.36 MB. The reduction comes from a simpler head, fewer hood and clothing subdivisions, single-triangle fibres, and removal of hidden fur. Its packed textures and all three animations remain included.

The exported character was reimported and rendered in Blender 5.2.2, including the full walk loop. It was also imported and rendered in Godot 4.7.2; automated checks verify the seven-bone skeleton and finite bone transforms at nine sample times in each animation. This is functional/visual validation, not a mobile performance benchmark. Exported walk and wave pose renders are included as `sparky-export-walk.png` and `sparky-export-wave.png`.

The Blender file opens with Idle active and Material Preview enabled. To inspect another action, select `Sparky_Rig`, change a panel to **Dope Sheet → Action Editor**, and select Walk or Wave from the action dropdown. Set the timeline end to 33 for Walk, 73 for Wave, or 97 for Idle. Saved NLA tracks are muted to prevent animations playing over each other.
