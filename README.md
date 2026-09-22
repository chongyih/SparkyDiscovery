# Sparky Discovery — playable prototype

The game currently contains **one chapter: 9 August 1965**. It is a small, explorable third-person neighbourhood. Other chapters are on hold until this one has been reviewed.

## Play

1. Open this folder's `project.godot` in Godot 4.7.2.
2. Press **F5**, then choose **Step into 1965**.
3. Follow the gold marker: speak to Uncle Tan on the shophouse pavement, collect the spare aerial, then tune the television.

The **Mobile renderer** is configured and tested on desktop with Metal. This does not mean the prototype currently has touchscreen controls. Browser export is not configured.

| Control | Action |
| --- | --- |
| WASD / arrows | Move relative to the camera |
| Mouse | Orbit the third-person camera |
| Scroll wheel | Zoom |
| R | Centre the camera behind Sparky |
| E | Interact nearby / continue dialogue |
| J | Historical journal |
| Esc | Pause / release the mouse |
| Tab / Enter | Navigate / activate menu controls |
| Space (during broadcast) | Pause / resume the footage |
| V (during broadcast) | Switch between community and close television views |

Progress saves locally after each encounter. Pause offers restart and return-to-title controls. The journal includes historical sources and identifies fictional dialogue and scenery. The television plays a 1 minute 58 second excerpt of the actual Lee Kuan Yew press conference, with original audio, optional English captions, pause, mute and skip controls. The source and rights designation are recorded in `assets/video/ATTRIBUTION.md`. Uncle Tan now speaks a short Singlish audition generated with ElevenLabs, with matching subtitles and replay/mute controls. Continuing stops the voice. Generation details are in `assets/voice/README.md`; other dialogue is text-only.

The broadcast plays directly on the wooden television in the open ground floor of a residential block, with flats and common corridors above. The shops face it from across the road. All four slatted benches angle inward towards the TV, with seated characters aligned to their benches. Seven neighbours gather with cups, a thermos and a slowly turning ceiling fan nearby. On the foreground-left bench, one neighbour raises a handkerchief to dab her eyes while her companion turns towards her and pats her shoulder. The eye-wiping happens briefly three times across the clip, with long quiet rests. Sparky sits on an angled left-hand bench beside a neighbour; the community camera shows his face, the reacting pair and the television together. **Walk around** returns him to the aisle; choosing a viewing camera seats him again. These reactions are fictional interpretations. Use **Community view**, **TV view**, or **Walk around** to choose how Sparky watches; press **Esc** to release the mouse and pause while walking.

## Current review scope

This first chapter is intended for a short playtest of movement, camera, exploration, interactions and storytelling. NPCs and environment meshes are placeholders. The streets and block are illustrative rather than a reconstruction of a named Singapore neighbourhood. NHB’s [history of void decks](https://www.nhb.gov.sg/~/media/nhb/files/resources/publications/ebooks/nhb_ebook_void_decks.pdf) records an early example at Jalan Klinik in 1963, while noting that widespread provision and the term came later. The block is an imagined early example, not a claim that open ground floors were standard in 1965. Upper-floor flats are scenery; the playable area remains at ground level. The full game's 5–10 minute duration is not a claim about this single chapter.

## Development

- `game/main.gd`: chapter state, interaction gates and checkpoints.
- `game/player.gd`: Sparky's movement and imported animations.
- `game/follow_camera.gd`: mouse orbit, zoom and camera collision.
- `game/world.gd`: the neighbourhood and interactable props.
- `game/community.gd`: communal seating, neighbours and broadcast reactions.
- `game/interface.gd`: title, HUD, dialogue, tuner, journal and pause UI.
- `game/history.gd`: the 1965 story and historical references.
- `tests/playthrough.gd`: gameplay, collision, puzzle and persistence checks.
- `tests/render_preview.gd`: actual-renderer screenshots in `artifacts/`.

On macOS:

```sh
/Applications/Godot.app/Contents/MacOS/Godot --headless --path . --script res://tests/playthrough.gd -- --test
/Applications/Godot.app/Contents/MacOS/Godot --path . --script res://tests/render_preview.gd -- --test
```

`--test` isolates the tests from real player progress. The playthrough test takes about two minutes because it checks the real archival clip through to its end. Screenshots require graphics access. The supplied Blender source remains intact; direct Blender import is disabled because the game uses the exported GLB.

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
