extends SceneTree
## Validate the real imported wardrobe, including prop/animation state changes.
const Wardrobe = preload("res://game/sparky_outfit.gd")

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	var visual := Wardrobe.new()
	root.add_child(visual)
	var report := {}
	for id in ["original", "ww2", "ns"]:
		visual.set_outfit(id)
		var skeletons := visual.model.find_children("*", "Skeleton3D", true, false)
		assert(skeletons.size() == 1)
		var skeleton := skeletons[0] as Skeleton3D
		assert(skeleton.get_bone_count() == 7)
		assert(visual.rifle_meshes.size() == (9 if id == "ns" else 0))
		for mesh in visual.rifle_meshes:
			assert(not mesh.visible, "Rifle must begin hidden")
		var clips: Array[String] = ["Idle", "Walk", "Wave"]
		if id == "ns":
			clips.append_array(["CarryIdle", "CarryWalk"])
		for clip in clips:
			assert(visual.animator.has_animation(clip), id + ": missing " + clip)
			visual.animator.play(clip, 0.0)
			var animation := visual.animator.get_animation(clip)
			for step in range(9):
				visual.animator.seek(animation.length * step / 8.0, true)
				await process_frame
				for bone in range(7):
					var pose := skeleton.get_bone_global_pose(bone)
					assert(pose.is_finite(), id + ": invalid pose")
					assert(pose.origin.length() < 3.0, id + ": invalid bounds")
		visual.set_rifle(true)
		assert(visual.rifle_visible == (id == "ns"))
		if id == "ns":
			assert(visual.animator.current_animation == "CarryIdle")
			for mesh in visual.rifle_meshes:
				assert(mesh.visible)
			visual.play_clip("Walk")
			assert(visual.animator.current_animation == "CarryWalk")
			visual.animator.advance(.4)
			visual.set_rifle(false)
			assert(visual.animator.current_animation == "Walk")
			for side in ["arm.L", "arm.R"]:
				assert(skeleton.get_bone_pose_scale(skeleton.find_bone(side)).is_equal_approx(Vector3.ONE))
			visual.set_rifle(true)
			visual.play_clip("Wave", 0.0)
			assert(not visual.rifle_visible)
			for mesh in visual.rifle_meshes:
				assert(not mesh.visible)
			visual.set_rifle(true)
			assert(visual.animator.current_animation == "CarryIdle")
		report[id] = {"bones": 7, "clips": clips, "rifle_meshes": visual.rifle_meshes.size()}
	visual.set_outfit("ww2")
	assert(not visual.rifle_visible and visual.rifle_meshes.is_empty())
	visual.queue_free()
	await process_frame
	# Exercise the actual studio selectors and pause button's current player.
	var studio = load("res://scenes/character_studio.tscn").instantiate()
	root.add_child(studio)
	for index in [2, 1, 0, 2]:
		studio.select_outfit(index)
		studio.play_clip("Walk")
		assert(studio.player == studio.wardrobe.animator)
	studio.rifle_button.button_pressed = true
	assert(studio.player.current_animation == "CarryWalk")
	studio.play_clip("Wave")
	assert(not studio.rifle_button.button_pressed)
	studio.queue_free()
	await process_frame
	var file := FileAccess.open("res://assets/sparky/outfits/godot-validation.json", FileAccess.WRITE)
	file.store_string(JSON.stringify({"result": "passed", "engine": Engine.get_version_info().string, "outfits": report}, "  "))
	print("SPARKY_OUTFITS_VALIDATION passed: 3 outfits, 11 clips, prop and studio transitions")
	quit()
