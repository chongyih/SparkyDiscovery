extends Node3D
## Reusable character visual for chapter scenes. Existing 1965 gameplay uses its original visual.
## Call set_outfit("ww2") / set_outfit("ns"), play_clip("Walk"), set_rifle(true).

const OUTFITS := {
	"original": "res://assets/sparky/sparky.glb",
	"ww2": "res://assets/sparky/outfits/sparky-ww2-civilian.glb",
	"ns": "res://assets/sparky/outfits/sparky-ns-1967.glb",
}

var outfit_id := "original"
var model: Node3D
var animator: AnimationPlayer
var rifle_visible := false
var current_clip := "Idle"
var rifle_meshes: Array[MeshInstance3D] = []

func set_outfit(id: String) -> void:
	assert(OUTFITS.has(id), "Unknown Sparky outfit: " + id)
	if model:
		remove_child(model)
		model.queue_free()
	outfit_id = id
	rifle_visible = false
	rifle_meshes.clear()
	model = (load(OUTFITS[id]) as PackedScene).instantiate()
	add_child(model)
	for item in model.find_children("*", "MeshInstance3D", true, false):
		if item.name.begins_with("Rifle"):
			rifle_meshes.append(item)
			item.visible = false
		if "Short" in item.name:
			item.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		for index in range(item.mesh.get_surface_count()):
			var source: Material = item.mesh.surface_get_material(index)
			if source is StandardMaterial3D and "plush" in source.resource_name.to_lower():
				var adjusted := source.duplicate() as StandardMaterial3D
				adjusted.normal_scale *= 0.35
				item.set_surface_override_material(index, adjusted)
	animator = model.find_children("*", "AnimationPlayer", true, false)[0] as AnimationPlayer
	for clip in ["Idle", "Walk", "CarryIdle", "CarryWalk"]:
		if animator.has_animation(clip):
			animator.get_animation(clip).loop_mode = Animation.LOOP_LINEAR
	play_clip(current_clip, 0.0)

func set_rifle(active: bool) -> void:
	rifle_visible = active and outfit_id == "ns"
	for mesh in rifle_meshes:
		mesh.visible = rifle_visible
	if rifle_visible and current_clip == "Wave":
		current_clip = "Idle"
	# Snap when equipping: the prop and both paws enter the authored pose together.
	play_clip(current_clip, 0.0)

func play_clip(clip: String, blend := 0.2) -> void:
	assert(clip in ["Idle", "Walk", "Wave"], "Unknown character movement: " + clip)
	current_clip = clip
	if clip == "Wave" and rifle_visible:
		rifle_visible = false
		for mesh in rifle_meshes:
			mesh.visible = false
	var animation := "Carry" + clip if rifle_visible else clip
	assert(animator.has_animation(animation), "Missing " + animation)
	animator.play(animation, blend)
	animator.advance(0.0)
