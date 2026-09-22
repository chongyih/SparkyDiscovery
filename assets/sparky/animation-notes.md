# Sparky animation update

The walking arms now hang closer to the torso and swing forward/backward from the shoulders, opposite the legs. The earlier wide arm pose made the same rotation look like sleeve twisting or paddling.

- Idle and Walk share a relaxed arm position.
- Walk uses a clearly visible shoulder swing (about 28 degrees each way), opposite the legs, with a slight delay.
- Steps lift about 8.5 cm, with a stronger stride, up to 4 cm of body bounce, and a gentle side-to-side weight shift. Planted-foot height correction remains enabled.
- Wave starts and ends in the same relaxed pose.
- The model's mesh, fur, materials, proportions, and seven-bone skeleton are unchanged by this animation update.

The updated animation is embedded in both `sparky.blend` and `sparky.glb`. Reopen the Blender file, or stop and restart the Godot scene after import, to see it. In Godot, open `scenes/character_studio.tscn` and press F6 to inspect the character independently of the game.
