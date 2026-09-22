"""Round-trip check of the deliverable, run in Blender."""
import bpy, os, json
from mathutils import Vector
root=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out=os.path.join(root,'assets','sparky')
bpy.ops.wm.open_mainfile(filepath=os.path.join(out,'sparky.blend'))
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.context.scene.objects:
    if not o.name.startswith('STUDIO'): o.select_set(True)
bpy.ops.object.delete(use_global=False)
for action in list(bpy.data.actions): bpy.data.actions.remove(action)
bpy.ops.import_scene.gltf(filepath=os.path.join(out,'sparky.glb'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
actions={a.name:a for a in bpy.data.actions}
assert {'Idle','Walk','Wave'} <= set(actions), list(actions)
assert len(rig.data.bones)==7
for track in rig.animation_data.nla_tracks: track.mute=True
rig.animation_data.action=actions['Walk']
scene=bpy.context.scene; scene.frame_set(7)
deps=bpy.context.evaluated_depsgraph_get()
points=[]
for o in scene.objects:
    if o.type=='MESH' and not o.name.startswith('STUDIO'):
        ev=o.evaluated_get(deps)
        points.extend(ev.matrix_world @ Vector(c) for c in ev.bound_box)
assert all(abs(c)<5 for p in points for c in p), 'Invalid bounds'
report={'round_trip':'passed','animations':sorted(actions),'bones':len(rig.data.bones),'mesh_objects':sum(o.type=='MESH' and not o.name.startswith('STUDIO') for o in scene.objects),'walk_frame_checked':7,'note':'Blender GLB reimport validated. Godot validation is recorded in assets/sparky/godot-validation.json.'}
with open(os.path.join(out,'validation.json'),'w') as f: json.dump(report,f,indent=2)
print(report)
scene.render.resolution_x=700; scene.render.resolution_y=700
for name,frame in [('Walk',7),('Wave',31)]:
    rig.animation_data.action=actions[name]
    scene.frame_set(frame)
    scene.render.filepath=os.path.join(out,'sparky-export-'+name.lower()+'.png')
    bpy.ops.render.render(write_still=True)

# Check that the arm travels fore/aft rather than twisting in place.
rig.animation_data.action=actions['Walk']; scene.frame_set(9)
camera=scene.camera; original_location=camera.location.copy(); original_rotation=camera.rotation_euler.copy()
camera.location=(7,-.5,2.0)
camera.rotation_euler=(Vector((0,0,1.04))-camera.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=os.path.join(out,'sparky-walk-side.png')
bpy.ops.render.render(write_still=True)
camera.location=original_location; camera.rotation_euler=original_rotation

# A compact, looping animation preview for people unfamiliar with Blender.
rig.animation_data.action=actions['Walk']
scene.render.resolution_x=420; scene.render.resolution_y=420
scene.cycles.samples=12
os.makedirs(os.path.join(out,'walk-loop'),exist_ok=True)
for frame in range(1,33,2):
    scene.frame_set(frame)
    scene.render.filepath=os.path.join(out,'walk-loop',f'{frame:03}.png')
    bpy.ops.render.render(write_still=True)
