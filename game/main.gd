extends Node3D

const History = preload("res://game/history.gd")
const World = preload("res://game/world.gd")
const Player = preload("res://game/player.gd")
const Interface = preload("res://game/interface.gd")
const FollowCamera = preload("res://game/follow_camera.gd")
const TouchControls = preload("res://game/touch_controls.gd")
const JourneyProgress = preload("res://game/journey_progress.gd")
const WAR_SAVE_PATH := "user://wartime_progress.cfg"
const SAVE_PATH := "user://independence_progress.cfg"
const INTERACT_DISTANCE := 2.3

var chapter: Dictionary = History.chapter()
var world: Node3D
var player: CharacterBody3D
var camera: Camera3D
var menu_camera: Camera3D
var follow_camera: Node3D
var ui: CanvasLayer
var task_index := 0
var mode := "menu"
var journal_return := "menu"
var checkpoint := 0
var has_save := false
var persistence_enabled := true
var save_path := SAVE_PATH
var conversation_poses: Array = []
var nod_delay: Tween
var dialogue_action: Callable
var dialogue_pages: Array = []
var dialogue_page := 0
var dialogue_context := {}
var voice_pages: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://assets/voice/pages.json"))
var dialogue_voice := AudioStreamPlayer.new()
var carried_aerial: Node3D
var aerial_fitted := false
var watch_camera: Camera3D
var broadcast_view := "community"
var watch_tween: Tween
var staging: Node
var soundscape: Node3D
var reflection_topics: Dictionary = {}
var closing_conversation := false
## What the touch Interact button would do right now; empty when nothing is in reach.
var interact_verb := ""

func _ready() -> void:
	# Tests and screenshots never overwrite the player's real progress.
	persistence_enabled = not OS.get_cmdline_user_args().has("--test")
	configure_input()
	dialogue_voice.name = "DialogueVoice"
	dialogue_voice.volume_db = Interface.VOICE_VOLUME_DB
	add_child(dialogue_voice)
	setup_lighting()
	configure_web_resolution()
	world = World.new()
	add_child(world)
	world.build(chapter)
	world.set_active(-1)
	player = Player.new()
	add_child(player)
	player.position = Vector3(0, 0.15, 3.8)
	if not sun_shadows():
		player.add_blob_shadow()
	carried_aerial = world.aerial(player.visual, Vector3(0.55, 0.9, 0.3))
	carried_aerial.scale = Vector3.ONE * 0.7
	carried_aerial.visible = false
	menu_camera = Camera3D.new()
	add_child(menu_camera)
	menu_camera.fov = 55
	menu_camera.position = Vector3(15, 9, 22)
	menu_camera.look_at(Vector3(0, 1.0, -1))
	menu_camera.current = true
	follow_camera = FollowCamera.new()
	add_child(follow_camera)
	follow_camera.target = player
	follow_camera.arm.add_excluded_object(player.get_rid())
	follow_camera.reset()
	camera = follow_camera.camera
	player.camera = camera
	watch_camera = Camera3D.new()
	add_child(watch_camera)
	ui = Interface.new()
	add_child(ui)
	staging = preload("res://game/chapter_staging.gd").new()
	staging.game = self
	add_child(staging)
	soundscape = preload("res://game/soundscape.gd").new()
	add_child(soundscape)
	soundscape.setup(player)
	var touch_controls := TouchControls.new()
	touch_controls.game = self
	add_child(touch_controls)
	read_save()
	show_menu()
	if get_tree().has_meta("enter_1965"):
		get_tree().remove_meta("enter_1965")
		chapter = chapter.duplicate(true)
		chapter.intro += "\n\nTwenty-three years after the shelter, Uncle Tan is still bringing his neighbours together."
		start_new()

func configure_input() -> void:
	var actions := {
		"move_left": [KEY_A, KEY_LEFT], "move_right": [KEY_D, KEY_RIGHT],
		"move_up": [KEY_W, KEY_UP], "move_down": [KEY_S, KEY_DOWN],
		"interact": [KEY_E], "journal": [KEY_J], "pause_game": [KEY_ESCAPE],
	}
	for action in actions:
		if not InputMap.has_action(action):
			InputMap.add_action(action)
		for key in actions[action]:
			var event := InputEventKey.new()
			event.physical_keycode = key
			if not InputMap.action_has_event(action, event):
				InputMap.action_add_event(action, event)

## The Compatibility renderer (used for web) washes sunlit surfaces out to white
## when a light casts shadows (godotengine/godot#90259), so it gets a blob shadow instead.
func sun_shadows() -> bool:
	return RenderingServer.get_current_rendering_method() != "gl_compatibility"

## Browsers size the canvas by device pixel ratio, so a 3x phone renders 3D at nine times the
## pixels of a plain screen. Render 3D at about 1.5x CSS pixels there; the UI stays sharp.
func configure_web_resolution() -> void:
	if OS.has_feature("web"):
		get_viewport().scaling_3d_scale = clampf(1.5 / DisplayServer.screen_get_scale(), 0.5, 1.0)

func setup_lighting() -> void:
	var environment := WorldEnvironment.new()
	var settings := Environment.new()
	settings.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	var sky_material := ProceduralSkyMaterial.new()
	sky_material.sky_top_color = Color("689dad")
	sky_material.sky_horizon_color = Color("dce4d9")
	sky_material.ground_horizon_color = Color("dce4d9")
	sky_material.ground_bottom_color = Color("8a9e91")
	sky.sky_material = sky_material
	settings.sky = sky
	settings.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	settings.ambient_light_color = Color("c9dedb")
	settings.ambient_light_energy = 0.55
	settings.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	settings.fog_enabled = true
	settings.fog_light_color = Color("c3d6cb")
	settings.fog_density = 0.003
	environment.environment = settings
	add_child(environment)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-52, -28, 0)
	sun.light_color = Color("fff0cf")
	sun.light_energy = 1.1
	sun.shadow_enabled = sun_shadows()
	sun.directional_shadow_max_distance = 60
	add_child(sun)
	var fill := DirectionalLight3D.new()
	fill.rotation_degrees = Vector3(-25, 135, 0)
	fill.light_color = Color("c1dedf")
	fill.light_energy = 0.35
	add_child(fill)

func set_mode(value: String) -> void:
	if value not in ["dialogue", "reflection"]:
		for pose in conversation_poses:
			if is_instance_valid(pose.actor):
				pose.actor.rotation = pose.rotation
		conversation_poses.clear()
		if is_instance_valid(player) and player.seated:
			player.apply_seat_pose(1.0)
	if value != "dialogue":
		cancel_dialogue_nod()
		dialogue_voice.stop()
	mode = value
	if is_instance_valid(soundscape):
		soundscape.set_scene_mode(value)
	var can_walk := mode == "play" or (mode == "video" and broadcast_view == "walk")
	if can_walk and player.seated:
		player.set_seated(false)
		player.position = Vector3(0.6, 0.15, -1.4)
	player.enabled = can_walk
	follow_camera.enabled = can_walk
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED if can_walk and not TouchControls.available() else Input.MOUSE_MODE_VISIBLE
	if not can_walk:
		player.velocity.x = 0
		player.velocity.z = 0
	ui.set_prompt("")

func frame_scene(menu_view: bool) -> void:
	if watch_tween:
		watch_tween.kill()
	if menu_view:
		menu_camera.make_current()
	else:
		camera.make_current()

func show_menu() -> void:
	staging.cancel()
	if watch_tween: watch_tween.kill()
	set_mode("menu")
	player.set_seated(false)
	world.set_active(-1)
	player.position = Vector3(10, 0.15, 8)
	player.visual.rotation.y = 0.35
	frame_scene(true)
	var finished := JourneyProgress.finished(save_path, WAR_SAVE_PATH) if persistence_enabled else has_save and checkpoint == 3
	ui.show_menu(start_new, show_journal, continue_saved, has_save, start_journey, continue_wartime, persistence_enabled and not JourneyProgress.read(WAR_SAVE_PATH, 4).is_empty(), continue_journey, finished)

func start_new() -> void:
	task_index = 0
	checkpoint = 0
	aerial_fitted = false
	world.community.set_broadcast(false)
	world.stations[0].visible = true
	world.tv_screen.material_override = world.material(Color("718a83"))
	prepare_chapter()
	write_save()
	set_mode("intro")
	ui.show_intro(chapter, resume_play)

func prepare_chapter() -> void:
	staging.cancel()
	if watch_tween: watch_tween.kill()
	closing_conversation = false
	reflection_topics.clear()
	world.stations[0].position = chapter.tasks[0].at
	world.stations[0].visible = true
	world.neighbour_visual.rotation.y = PI
	world.community.set_broadcast(false)
	aerial_fitted = false
	player.set_seated(false)
	player.position = Vector3(0, 0.2, 14)
	player.velocity = Vector3.ZERO
	player.visual.rotation.y = 1.85 + PI
	follow_camera.reset(1.85)
	frame_scene(false)
	ui.build_hud(chapter, show_journal, pause_game)
	refresh_objective()

func continue_saved() -> void:
	task_index = checkpoint
	prepare_chapter()
	write_save()
	if checkpoint >= chapter.tasks.size():
		show_complete()
	else:
		resume_play()

func continue_journey() -> void:
	if persistence_enabled and JourneyProgress.latest(save_path, WAR_SAVE_PATH) == "1942":
		continue_wartime()
	else:
		continue_saved()

func resume_play() -> void:
	ui.clear_overlay()
	ui.hud.visible = true
	set_mode("play")
	frame_scene(false)
	refresh_objective()

func refresh_objective() -> void:
	world.set_active(task_index if task_index < chapter.tasks.size() else -1)
	world.spare_aerial.visible = task_index < 2
	world.tv_aerial.visible = aerial_fitted or task_index == 3
	carried_aerial.visible = task_index == 2 and not aerial_fitted
	if task_index < chapter.tasks.size():
		ui.set_objective(chapter.tasks[task_index].name, task_index, 3)
	else:
		ui.set_objective("Independence · 9 August 1965", 3, 3)

func _process(_delta: float) -> void:
	if mode == "video" and is_instance_valid(ui.archive_player):
		world.community.playback_time = ui.archive_player.stream_position
		world.community.reaction_paused = ui.archive_player.paused
		soundscape.set_frozen(ui.archive_player.paused)
		player.react_to_broadcast(ui.archive_player.stream_position)
	interact_verb = ""
	if mode != "play" or task_index >= chapter.tasks.size():
		return
	var task: Dictionary = chapter.tasks[task_index]
	var target: Vector3 = task.at
	var distance := Vector2(player.position.x - target.x, player.position.z - target.z).length()
	var relative := camera.global_basis.inverse() * (target - player.position)
	var direction := "Ahead"
	if relative.z > 1:
		direction = "Behind you"
	elif relative.x < -2:
		direction = "To your left"
	elif relative.x > 2:
		direction = "To your right"
	if distance <= INTERACT_DISTANCE:
		interact_verb = {"person": "Talk", "aerial": "Pick up"}.get(task.kind, "Tune" if aerial_fitted else "Fit antenna")
	var interact_hint := "Tap the gold button" if TouchControls.available() else "Press E"
	ui.set_navigation("%s  ·  %d m" % [direction, int(distance)] if distance > INTERACT_DISTANCE else "You’re here  ·  " + interact_hint)
	ui.set_prompt(interact_verb if distance <= INTERACT_DISTANCE else "")

func _input(event: InputEvent) -> void:
	if mode != "video" or not event is InputEventKey or not event.pressed or event.echo:
		return
	if event.physical_keycode == KEY_SPACE:
		ui.toggle_video_pause()
		get_viewport().set_input_as_handled()
	elif event.physical_keycode == KEY_V:
		set_broadcast_view("community" if broadcast_view == "television" else "television")
		get_viewport().set_input_as_handled()

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("pause_game"):
		if mode == "play":
			pause_game()
		elif mode == "pause" or mode == "puzzle":
			resume_play()
		elif mode == "journal":
			close_journal()
		elif mode == "video":
			if broadcast_view == "walk":
				set_broadcast_view("community")
			ui.toggle_video_pause()
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("journal"):
		if mode in ["play", "complete"]:
			show_journal()
		elif mode == "journal":
			close_journal()
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("interact"):
		if mode == "play":
			interact()
		elif mode == "dialogue":
			advance_dialogue()
		get_viewport().set_input_as_handled()

func interact() -> bool:
	if mode != "play" or task_index >= chapter.tasks.size():
		return false
	var task: Dictionary = chapter.tasks[task_index]
	var target: Vector3 = task.at
	if Vector2(player.position.x - target.x, player.position.z - target.z).length() > INTERACT_DISTANCE:
		return false
	player.visual.rotation.y = atan2(target.x - player.position.x, target.z - player.position.z)
	if task.kind == "tv":
		if aerial_fitted:
			show_tuning()
		else:
			staging.fit_aerial()
	else:
		show_dialogue(task.speaker, task.text, complete_task, task.get("voice", ""), {}, task.kind != "person")
	return true

func show_tuning() -> void:
	set_mode("puzzle")
	world.set_active(-1)
	frame_watch(Vector3(2.8, 3.2, -1.0), Vector3(0, 1.65, -5.7), 48)
	var screen_material := ShaderMaterial.new()
	screen_material.shader = preload("res://game/tuning_screen.gdshader")
	world.tv_screen.material_override = screen_material
	ui.show_tuner(finish_tuning, resume_play, func(value: float, strength: float, clear: bool):
		for rod in world.tv_aerial.get_children():
			if rod.position.y > 0.1:
				# The locked signal (65) is the antenna's centred resting pose.
				rod.rotation.z = (-0.65 if rod.position.x < 0 else 0.65) + deg_to_rad((value - 65.0) * -0.65)
		screen_material.set_shader_parameter("clarity", 1.0 if clear else strength / 120.0)
		soundscape.tune(value, strength, clear)
	)

	var tuner = ui.overlay.find_child("AntennaTuner", true, false)
	var cue := load("res://assets/voice/signal_found.mp3") as AudioStream
	tuner.celebration_duration = maxf(1.1, cue.get_length() + 0.2)
	tuner.signal_locked.connect(func(): play_voice_cue(cue))

func play_voice_cue(stream: AudioStream) -> void:
	dialogue_voice.stop()
	dialogue_voice.stream = stream
	dialogue_voice.play()

func show_dialogue(speaker: String, text: String, after: Callable, voice_path: String = "", note: Dictionary = {}, narration := false) -> void:
	dialogue_voice.stop()
	set_mode("dialogue")
	dialogue_action = after
	dialogue_context = {"speaker": speaker, "note": note, "narration": narration}
	dialogue_pages = voice_pages.get(voice_path.get_file().get_basename(), []).duplicate(true)
	if dialogue_pages.is_empty():
		for part in text.split("\n\n"):
			dialogue_pages.append({"text": part, "audio": ""})
	dialogue_page = 0
	render_dialogue_page()
	if speaker == "Uncle Tan":
		frame_conversation.call_deferred()

## Elevated diagonal two-shot; both characters keep looking at each other.
func frame_conversation() -> void:
	if mode not in ["dialogue", "reflection"]:
		return
	var uncle: Node3D = world.community.residents[5].root if player.seated else world.neighbour_visual
	var uncle_head: Node3D = world.community.residents[5].head if player.seated else null
	if conversation_poses.is_empty():
		for actor in [player.visual, uncle]:
			conversation_poses.append({"actor": actor, "rotation": actor.rotation})
		if uncle_head:
			conversation_poses.append({"actor": uncle_head, "rotation": uncle_head.rotation})
	var sparky_at := player.global_position
	var uncle_at := uncle.global_position
	var middle := (sparky_at + uncle_at) * 0.5
	var across := uncle_at - sparky_at
	across.y = 0
	if across.length() < 0.2:
		across = Vector3.RIGHT
	# Prefer Uncle Tan on the left, with a little depth between the two faces.
	var side: Vector3 = world.community.sparky_seat().basis.z if player.seated else -across.normalized().cross(Vector3.UP)
	var distance := maxf(5.5, across.length() * 1.1)
	var offset := side * 3.8 - across.normalized() * 2.5 if player.seated else (side + across.normalized() * 0.22).normalized() * distance
	var at := middle + offset + Vector3(0, 2.8, 0)
	# The reverse side can be inside the shops or behind the residential block.
	# Use the open side when scenery would obscure either conversation partner.
	for actor_at in [sparky_at, uncle_at]:
		var ray := PhysicsRayQueryParameters3D.create(at, actor_at + Vector3(0, 1.5, 0))
		ray.exclude = [player.get_rid()]
		ray.hit_from_inside = true
		if not get_world_3d().direct_space_state.intersect_ray(ray).is_empty():
			offset = side * 3.0 - across.normalized() * 3.0 if player.seated else (-side + across.normalized() * 0.22).normalized() * distance
			at = middle + offset + Vector3(0, 2.8, 0)
			break
	# Leave the lower part of the shot clear for the dialogue panel.
	var aim := middle + Vector3(0, 0.45, 0)
	frame_watch(at, aim, 50, 0.7)
	for actor in [player.visual, uncle]:
		var other: Vector3 = uncle_at if actor == player.visual else sparky_at
		var toward_partner: Vector3 = other - actor.global_position
		toward_partner.y = 0
		var facing: Vector3 = toward_partner.normalized()
		if not player.seated:
			actor.global_rotation.y = atan2(facing.x, facing.z)
	if uncle_head:
		# Keep both seated bodies aligned with their benches; only turn their heads.
		player.look_at_conversation(uncle_at)
		var local_direction := uncle.global_basis.inverse() * (sparky_at - uncle_at)
		uncle_head.rotation = Vector3(0, clampf(atan2(local_direction.x, local_direction.z), -0.95, 0.95), 0)

func cancel_dialogue_nod() -> void:
	if nod_delay:
		nod_delay.kill()
		nod_delay = null
	if is_instance_valid(player):
		player.cancel_nod()

func render_dialogue_page() -> void:
	cancel_dialogue_nod()
	dialogue_voice.stop()
	var page: Dictionary = dialogue_pages[dialogue_page]
	dialogue_voice.stream = load(page.audio) if not page.audio.is_empty() else null
	if dialogue_voice.stream:
		dialogue_voice.play()
	var last := dialogue_page == dialogue_pages.size() - 1
	ui.show_dialogue(dialogue_context.speaker, page.text, advance_dialogue,
		dialogue_voice if dialogue_voice.stream else null,
		dialogue_context.note if last else {}, dialogue_context.narration,
		dialogue_page + 1, dialogue_pages.size(), previous_dialogue_page)
	if task_index == 0 and page.text.begins_with("Can help me bring the spare antenna"):
		# The request ends 2.44 seconds into this clip; acknowledge it in its pause.
		nod_delay = create_tween()
		nod_delay.tween_interval(2.55)
		nod_delay.tween_callback(player.nod)

func previous_dialogue_page() -> void:
	if mode == "dialogue" and dialogue_page > 0:
		dialogue_page -= 1
		render_dialogue_page()

func advance_dialogue() -> void:
	if mode != "dialogue":
		return
	cancel_dialogue_nod()
	dialogue_voice.stop()
	if dialogue_page + 1 < dialogue_pages.size():
		dialogue_page += 1
		render_dialogue_page()
		return
	var action := dialogue_action
	dialogue_action = Callable()
	if action.is_valid():
		action.call()

func finish_tuning() -> void:
	if mode != "puzzle":
		return
	# Only a settled signal can start the seating sequence.
	var tuner = ui.overlay.find_child("AntennaTuner", true, false)
	if not tuner or not tuner.locked:
		return
	world.set_active(-1)
	ui.set_objective("Watch the original press conference", 3, 3)
	staging.arrive()

func start_broadcast() -> void:
	broadcast_view = "community"
	set_mode("video")
	world.community.set_broadcast(true)
	world.stations[0].visible = false
	var video: VideoStreamPlayer = ui.show_archive(finish_archive, set_broadcast_view)
	var screen_material := StandardMaterial3D.new()
	screen_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	screen_material.albedo_texture = video.get_video_texture()
	world.tv_screen.material_override = screen_material
	set_broadcast_view("community")

func set_broadcast_view(value: String) -> void:
	if mode != "video":
		return
	broadcast_view = value
	ui.set_archive_view(value)
	if value != "walk":
		var seat: Transform3D = world.community.global_transform * world.community.sparky_seat()
		player.global_position = seat.origin
		player.visual.global_rotation.y = seat.basis.get_euler().y
		player.set_seated(true)
	set_mode("video")
	if watch_tween and watch_tween.is_running():
		watch_tween.kill()
	if value == "walk":
		follow_camera.reset()
		camera.make_current()
		return
	if value == "community":
		frame_community()
	else:
		frame_watch(Vector3(-0.15, 2.05, -2.9), Vector3(-0.15, 1.84, -5.275), 48)

func frame_community() -> void:
	frame_watch(Vector3(5.2, 2.9, 2.4), Vector3(-0.5, 1.3, -2.5), 58)

func frame_watch(at: Vector3, aim: Vector3, fov: float, duration := 1.0) -> void:
	if watch_tween: watch_tween.kill()
	var previous_camera: Camera3D = get_viewport().get_camera_3d()
	watch_camera.global_transform = previous_camera.global_transform
	watch_camera.fov = previous_camera.fov
	watch_camera.make_current()
	var destination := Transform3D(Basis.IDENTITY, at).looking_at(aim)
	watch_tween = create_tween().set_parallel(true)
	watch_tween.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN_OUT)
	watch_tween.tween_property(watch_camera, "global_transform", destination, duration)
	watch_tween.tween_property(watch_camera, "fov", fov, duration)

func finish_archive() -> void:
	if mode != "video":
		return
	# A player who explored during the footage rejoins the seated conversation.
	if broadcast_view == "walk":
		set_broadcast_view("community")
	world.community.reaction_paused = true
	world.community.conversing = true
	world.community.update_reactions()
	closing_conversation = true
	world.tv_screen.material_override = world.material(Color("d7e9da"), true)
	show_dialogue("Uncle Tan", History.AFTER_BROADCAST, show_reflection, "res://assets/voice/after_broadcast.mp3")

func show_reflection() -> void:
	if not closing_conversation: return
	set_mode("reflection")
	ui.show_reflection(History.REFLECTIONS, reflection_topics, ask_reflection, finish_reflection)

func ask_reflection(topic_id: String) -> void:
	if mode != "reflection" or not History.REFLECTIONS.has(topic_id): return
	var topic: Dictionary = History.REFLECTIONS[topic_id]
	reflection_topics[topic_id] = true
	show_dialogue("Uncle Tan", topic.answer, show_reflection, topic.voice, topic)

func finish_reflection() -> void:
	if mode != "reflection" or not closing_conversation: return
	closing_conversation = false
	show_dialogue("Uncle Tan", History.FAREWELL, complete_task, "res://assets/voice/farewell.mp3")

func complete_task() -> void:
	task_index += 1
	checkpoint = task_index
	write_save()
	if task_index >= chapter.tasks.size():
		show_complete()
	else:
		resume_play()
	ui.show_memory_notice(checkpoint)

func show_complete() -> void:
	set_mode("complete")
	refresh_objective()
	ui.show_chapter_end(chapter, show_menu, show_journal)

func pause_game() -> void:
	if mode != "play":
		return
	set_mode("pause")
	ui.show_pause(resume_play, start_new, show_menu, soundscape.set_enabled, soundscape.enabled)

func show_journal() -> void:
	if mode not in ["play", "menu", "complete"]:
		return
	journal_return = mode
	set_mode("journal")
	ui.show_journal(chapter, checkpoint, History.SOURCES, close_journal)

func close_journal() -> void:
	match journal_return:
		"menu": show_menu()
		"complete": show_complete()
		_: resume_play()

func read_save() -> void:
	if not persistence_enabled:
		return
	var config := ConfigFile.new()
	if config.load(save_path) == OK:
		var saved: Variant = config.get_value("progress", "task", 0)
		if saved is int and saved >= 0 and saved <= 3:
			checkpoint = saved
			has_save = true

func write_save() -> void:
	has_save = true
	if not persistence_enabled:
		return
	var config := ConfigFile.new()
	config.set_value("progress", "task", checkpoint)
	config.set_value("progress", "last_played", Time.get_unix_time_from_system())
	var result := config.save(save_path)
	if result != OK:
		push_warning("Could not save progress: %s" % error_string(result))

func start_journey() -> void:
	get_tree().set_meta("restart_1942", true)
	get_tree().change_scene_to_file("res://scenes/ww2.tscn")

func continue_wartime() -> void:
	get_tree().change_scene_to_file("res://scenes/ww2.tscn")
