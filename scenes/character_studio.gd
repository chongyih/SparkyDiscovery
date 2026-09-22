extends Node3D
## Standalone character review scene. Open this scene and press F6.

var character: Node3D
var player: AnimationPlayer
var camera: Camera3D
var dragging := false
var angle := 0.35
var distance := 5.4
var caption: Label

func _ready() -> void:
	character = (load("res://assets/sparky/sparky.glb") as PackedScene).instantiate()
	add_child(character)
	for item in character.find_children("*", "MeshInstance3D", true, false):
		if "Short" in item.name:
			item.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		for index in range(item.mesh.get_surface_count()):
			var source_material: Material = item.mesh.surface_get_material(index)
			if source_material is StandardMaterial3D:
				var adjusted := source_material.duplicate() as StandardMaterial3D
				if "plush" in adjusted.resource_name.to_lower():
					adjusted.normal_scale *= 0.35
				item.set_surface_override_material(index, adjusted)
	for item in character.find_children("*", "AnimationPlayer", true, false):
		player = item
	assert(player != null, "Missing animations")
	for clip in ["Idle", "Walk"]:
		assert(player.has_animation(clip), "Missing " + clip)
		player.get_animation(clip).loop_mode = Animation.LOOP_LINEAR
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color("202d37")
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color("d9e4f0")
	env.environment.ambient_light_energy = 0.3
	env.environment.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	add_child(env)
	for spec in [[Vector3(-3, 5, 4), 0.65], [Vector3(4, 3, -2), 0.25]]:
		var light := DirectionalLight3D.new()
		add_child(light)
		light.position = spec[0]
		light.look_at(Vector3(0, 1, 0))
		light.light_energy = spec[1]
	var floor_mesh := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(200, 200)
	floor_mesh.mesh = plane
	var material := StandardMaterial3D.new()
	material.albedo_color = Color("283b43")
	material.roughness = 1.0
	floor_mesh.material_override = material
	floor_mesh.position.y = -0.015
	add_child(floor_mesh)
	add_contact_shadow()
	camera = Camera3D.new()
	add_child(camera)
	camera.fov = 32
	update_camera()
	build_controls()
	play_clip("Walk")
	if "--validate-sparky" in OS.get_cmdline_user_args():
		await validate_model()

func add_contact_shadow() -> void:
	var shadow := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(1.6, 1.1)
	shadow.mesh = plane
	shadow.position.y = -0.013
	shadow.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var gradient := Gradient.new()
	gradient.offsets = PackedFloat32Array([0.0, 0.3, 1.0])
	gradient.colors = PackedColorArray([Color(0, 0, 0, 0.3), Color(0, 0, 0, 0.18), Color(0, 0, 0, 0)])
	var texture := GradientTexture2D.new()
	texture.gradient = gradient
	texture.width = 128
	texture.height = 128
	texture.fill = GradientTexture2D.FILL_RADIAL
	texture.fill_from = Vector2(0.5, 0.5)
	texture.fill_to = Vector2(1, 0.5)
	var material := StandardMaterial3D.new()
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.albedo_texture = texture
	shadow.material_override = material
	add_child(shadow)

func update_camera() -> void:
	camera.position = Vector3(sin(angle) * distance, 2.1, cos(angle) * distance)
	camera.look_at(Vector3(0, 1.02, 0))

func play_clip(clip: String) -> void:
	player.play(clip, 0.2)
	caption.text = clip + "   ·   Drag to rotate   ·   Scroll to zoom"

func build_controls() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	var margin := MarginContainer.new()
	margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	for edge in ["left", "top", "right", "bottom"]:
		margin.add_theme_constant_override("margin_" + edge, 24)
	margin.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(margin)
	var column := VBoxContainer.new()
	column.mouse_filter = Control.MOUSE_FILTER_IGNORE
	margin.add_child(column)
	var title := Label.new()
	title.text = "Sparky"
	title.add_theme_font_size_override("font_size", 34)
	column.add_child(title)
	var subtitle := Label.new()
	subtitle.text = "CHARACTER STUDIO"
	subtitle.modulate = Color("a9c8c5")
	column.add_child(subtitle)
	var spacer := Control.new()
	spacer.size_flags_vertical = Control.SIZE_EXPAND_FILL
	spacer.mouse_filter = Control.MOUSE_FILTER_IGNORE
	column.add_child(spacer)
	caption = Label.new()
	caption.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	column.add_child(caption)
	var row := HBoxContainer.new()
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	row.add_theme_constant_override("separation", 12)
	column.add_child(row)
	for clip in ["Idle", "Walk", "Wave"]:
		var button := Button.new()
		button.text = clip
		button.custom_minimum_size = Vector2(110, 42)
		button.pressed.connect(play_clip.bind(clip))
		row.add_child(button)
	var pause_button := Button.new()
	pause_button.text = "Pause / resume"
	pause_button.custom_minimum_size = Vector2(150, 42)
	pause_button.pressed.connect(func():
		if player.is_playing(): player.pause()
		else: player.play())
	row.add_child(pause_button)

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT:
			dragging = event.pressed
		if event.pressed and event.button_index == MOUSE_BUTTON_WHEEL_UP:
			distance = maxf(3.4, distance - 0.25)
		if event.pressed and event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			distance = minf(8.0, distance + 0.25)
		update_camera()
	if event is InputEventMouseMotion and dragging:
		angle -= event.relative.x * 0.008
		update_camera()

func validate_model() -> void:
	var skeletons := character.find_children("*", "Skeleton3D", true, false)
	assert(skeletons.size() == 1, "Expected one skeleton")
	var skeleton := skeletons[0] as Skeleton3D
	assert(skeleton.get_bone_count() == 7, "Expected seven bones")
	var clips := {}
	for clip in ["Idle", "Walk", "Wave"]:
		assert(player.has_animation(clip), "Missing " + clip)
		var animation := player.get_animation(clip)
		player.play(clip)
		for step in range(9):
			player.seek(animation.length * step / 8.0, true)
			await get_tree().process_frame
			for bone in range(skeleton.get_bone_count()):
				assert(skeleton.get_bone_global_pose(bone).is_finite(), "Invalid bone transform")
		clips[clip] = {"seconds": animation.length, "tracks": animation.get_track_count()}
	var report := {"result": "passed", "engine": Engine.get_version_info().string, "bones": 7, "clips": clips}
	var file := FileAccess.open("res://assets/sparky/godot-validation.json", FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "  "))
	print("SPARKY_GODOT_VALIDATION " + JSON.stringify(report))
	get_tree().quit()
