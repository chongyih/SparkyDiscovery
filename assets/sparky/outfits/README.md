# Sparky's chapter wardrobe — first review pass

Open `scenes/character_studio.tscn` in Godot and press **F6**. Choose **WW2 · Civilian** or **1967 · NS recruit**. Idle, Walk and Wave work for each outfit. The NS outfit also has **Carry rifle**: Idle and Walk use two additional carrying animations. Wave puts the rifle away; changing outfits also removes it.

These are editable, rigged 3D variants of the existing Sparky, not concept-image replacements. His face, plush proportions, seven-bone skeleton and original animations are retained. The 1965 chapter still uses the original navy hoodie. The WWII chapter now uses the civilian GLB through the player controller and includes it in exports. The unused NS outfit, Blender sources and review renders remain excluded.

## Designs and historical boundaries

**Singapore civilian, 1942–1945.** Faded blue-grey cotton, a short button placket, plain trousers and cloth shoes, a repaired patch, and a canvas shoulder bag. No DSTA lettering or modern drawstrings. The hood is intentionally retained at the user's request as Sparky's recognizable silhouette. This is a fictional civilian costume inspired by material restraint; it is **not a reconstruction of typical Singapore civilian dress**. Singapore had diverse civilian clothing traditions. The colour, patch, bag and fastenings are artistic choices and do not identify a specific community or occupation.

**First full-time NS intake, 1967.** Plain green shirt and trousers, collar, breast pockets, web belt, black boots and a small field-cap interpretation that leaves the ears visible. The hood is removed at the user's request. The historical anchor is Temasek Green cotton drill; the cut, proportions, cap and details are adapted for a plush bear and have not been certified as an exact 1967 uniform. No modern camouflage, body armour, national-flag patch, rank or DSTA branding is added.

**Rifle scenes.** An early M16-inspired visual prop has a fixed stock, carry-handle silhouette and straight magazine. Army News dates the M16's replacement of the SLR to 1967; that does not establish which weapon a particular unit held on a particular day. Confirm the unit, scene date and archival image before calling any equipment a precise first-batch reconstruction. The prop is interchangeable at the mesh level and has no firing mechanics. The same nine `Rifle*` meshes are weighted to the body bone and appear only when the wardrobe component enables them. The raw GLB includes these meshes; use the component to apply visibility and animation state together.

## Files and scene integration

- `sparky-ww2-civilian.blend` / `.glb`: civilian source and runtime asset.
- `sparky-ns-1967.blend` / `.glb`: recruit source and runtime asset, including optional rifle meshes.
- `*-preview.png`, `*-back.png`, `*-rifle.png`: Blender review renders.
- `godot-validation.json`: imported asset and state-transition checks.
- `../../../tools/build_sparky_outfits.py`: reproducible builder (repository path: `tools/build_sparky_outfits.py`). It opens the existing `assets/sparky/sparky.blend` afresh for each outfit and does not overwrite it.

Use `game/sparky_outfit.gd` on a visual child of a future chapter's player:

```gdscript
var visual = preload("res://game/sparky_outfit.gd").new()
add_child(visual)
visual.set_outfit("ns") # "original", "ww2", "ns"
visual.set_rifle(true)  # only enabled for "ns"
visual.play_clip("Walk") # selects CarryWalk while the rifle is visible
```

The existing controller is not migrated as part of this model preparation. The model still faces Godot +Z and is about 2.1 units tall. The seven-bone plush rig has no elbows, wrists or articulated fingers. CarryIdle and CarryWalk use fixed mitten contacts and modest arm scaling; they are a stylized carry, not realistic drill, aiming, reloading or a full weapon animation system. Equipping snaps to the carrying pose to keep the prop and paws together.

In Blender, the source opens unarmed with Idle active. To inspect the rifle, reveal the nine `Rifle*` objects in the Outliner, enable their render visibility, select `Sparky_Rig` and choose CarryIdle or CarryWalk in the Action Editor. Muted NLA strips preserve all clips without stacking them.

Rebuild with Blender 5.2.2:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --python tools/build_sparky_outfits.py
/Applications/Godot.app/Contents/MacOS/Godot --headless --path . --editor --import
/Applications/Godot.app/Contents/MacOS/Godot --headless --path . --script res://tests/sparky_outfits.gd
/Applications/Godot.app/Contents/MacOS/Godot --path . --script res://tests/render_sparky_outfits.gd
```

The last command writes actual Godot captures to ignored `artifacts/`. The tests cover all three outfits, eleven clips, finite bone poses, rifle visibility, return to unarmed arm scale, outfit changes and studio controls. Preview renders should still be reviewed for garment intersections at future scene-specific poses.

## Reference trail

Consulted 23 September 2026. No archival imagery is embedded in these assets.

- [NHB / Roots: Implementation of National Service](https://www.roots.gov.sg/stories-landing/stories/implementation-of-national-service/story): pioneer NS and Temasek Green cotton drill.
- [MINDEF: History](https://www.mindef.gov.sg/about-us/history/): first full-time enlistments from 17 August 1967.
- [Singapore Army, Army News 245/2017](https://isomer-user-content.by.gov.sg/128/43836d2c-a0f9-42fa-ba00-0b3b066ba54d/pub-245-2017.pdf), “Reminiscing National Service”: uniform and rifle chronology, including M16 introduction in 1967.
- [NHB: Wartime Kitchen](https://www.nhb.gov.sg/nationalmuseum/about-us/publications/wartime-kitchen): context of wartime shortages and adaptation, not evidence for a hooded outfit.
- [NLB: Memories of the Japanese Occupation](https://www.nlb.gov.sg/main/article-detail?cmsuuid=A-cfde1fac-4512-4f7f-9388-5b1ca3c31719): an individual clothing recollection, not a universal civilian costume reference.
