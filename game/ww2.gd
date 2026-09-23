extends "res://game/main.gd"
## Shared movement/dialogue/touch controls; WWII owns its scene, tasks and save file.
const WAR_SAVE := "user://wartime_progress.cfg"
const WAR_CHAPTER := {
	"year": "1942", "date": "12 FEBRUARY 1942", "title": "Before the streets fell silent",
	"place": "An imagined Singapore shophouse street",
	"intro": "Fighting has reached the island. Uncle Tan and his neighbour Mei are preparing a shelter. Help them bring water inside.",
	"tasks": [
		{"name": "Speak to Uncle Tan", "label": "UNCLE TAN", "at": Vector3(0, 0, 7.5)},
		{"name": "Help Mei prepare the shelter", "label": "MEI", "at": Vector3(-1.8, 0, -1.7)},
		{"name": "Collect water from the courtyard", "label": "WATER", "at": Vector3(7.3, 0, 1)},
		{"name": "Bring the pail to the water station", "label": "WATER STATION", "at": Vector3(-2.6, 0, -8.7)},
	]
}
var carried_water: Node3D
var war_audio: AudioStreamPlayer
var blast_audio: AudioStreamPlayer
var blast_time := 0.0
var blast_hit := false
var reduced_effects := false
var audio_enabled := true
var paused_mode := "play"
var journal_page := 0
var lines: Array = []
var lines_done: Callable
var original_visual_position := Vector3.ZERO
var war_mix: Node
var body_pose: SkeletonModifier3D
var stage_kind := ""
var stage_clock := 0.0
var stage_duration := 0.0
var prop_start := Vector3.ZERO
var stage_target := Vector3.ZERO
var stage_sound_played := false
var blast_caption: Label

func _ready() -> void:
	persistence_enabled = not OS.get_cmdline_user_args().has("--test")
	save_path = WAR_SAVE
	chapter = WAR_CHAPTER.duplicate(true)
	configure_input()
	add_child(dialogue_voice)
	setup_lighting()
	configure_web_resolution()
	for child in get_children():
		if child is WorldEnvironment:
			child.environment.fog_light_color = Color("9b9180")
			child.environment.fog_density = 0.004
			child.environment.ambient_light_energy = 0.35
		if child is DirectionalLight3D:
			child.light_energy *= 0.75
	world = preload("res://game/ww2_world.gd").new()
	add_child(world)
	world.build(chapter)
	player = Player.new()
	player.model_path = "res://assets/sparky/outfits/sparky-ww2-civilian.glb"
	add_child(player)
	player.add_blob_shadow()
	carried_water = world.make_pail(player.visual)
	carried_water.position = Vector3(-0.62, 0.04, 0.23)
	carried_water.scale = Vector3.ONE * 0.65
	carried_water.visible = false
	body_pose = preload("res://game/ww2_pose.gd").new()
	player.skeleton.add_child(body_pose)
	body_pose.prop = carried_water
	player.animator.advance(0)
	body_pose.carry_rotation = player.skeleton.get_bone_pose_rotation(player.skeleton.find_bone("arm.R"))
	war_mix = preload("res://game/ww2_sound.gd").new()
	add_child(war_mix)
	war_mix.setup(player)
	follow_camera = FollowCamera.new()
	add_child(follow_camera)
	follow_camera.target = player
	follow_camera.arm.add_excluded_object(player.get_rid())
	camera = follow_camera.camera
	player.camera = camera
	watch_camera = Camera3D.new()
	add_child(watch_camera)
	ui = Interface.new()
	add_child(ui)
	var touch := TouchControls.new()
	touch.game = self
	add_child(touch)
	war_audio = AudioStreamPlayer.new()
	war_audio.stream = load("res://assets/audio/ww2-rumble.wav")
	war_audio.volume_db = -27
	add_child(war_audio)
	war_audio.finished.connect(func():
		if audio_enabled and mode in ["play", "dialogue", "blast"]: war_audio.play()
	)
	blast_audio = AudioStreamPlayer.new()
	blast_audio.volume_db = -14
	add_child(blast_audio)
	read_save()
	if get_tree().has_meta("restart_1942"):
		get_tree().remove_meta("restart_1942")
		checkpoint = 0
	prepare_chapter()
	write_save()
	if checkpoint == 4:
		show_complete()
	elif checkpoint > 0:
		resume_play()
	else:
		set_mode("intro")
		ui.show_intro(chapter, resume_play)

func prepare_chapter() -> void:
	task_index = checkpoint
	ui.build_hud(chapter, show_journal, pause_game)
	player.position = Vector3(-2, 0.1, 3.5) if checkpoint == 0 else Vector3(6, 0.1, 2)
	player.velocity = Vector3.ZERO
	player.visual.rotation.y = 0
	follow_camera.reset(2.65 if checkpoint == 0 else 0.6)
	camera.make_current()
	world.pail.visible = checkpoint < 3
	carried_water.visible = checkpoint == 3
	body_pose.carry = 1.0 if checkpoint == 3 else 0.0
	if checkpoint >= 3:
		world.aftermath()
	if checkpoint == 4:
		world.close_shelter()
		world.finish_relief()
		body_pose.quiet = 1
		war_mix.enter_shelter()
		world.pail.visible = true
		world.pail.position = world.WATER_SPOT
		war_audio.volume_db = -42 if audio_enabled else -80
		player.position = Vector3(-1.05, 0.1, -8.55)
	refresh_objective()

func start_new() -> void:
	get_tree().set_meta("restart_1942", true)
	get_tree().reload_current_scene()

func show_menu() -> void:
	get_tree().change_scene_to_file("res://scenes/main.tscn")

func frame_scene(_menu_view: bool) -> void:
	camera.make_current()

func resume_play() -> void:
	ui.clear_overlay()
	ui.hud.visible = true
	set_mode("play")
	camera.make_current()
	if audio_enabled and not war_audio.playing:
		war_audio.play()
	war_audio.stream_paused = false
	refresh_objective()

func refresh_objective() -> void:
	world.set_active(task_index if task_index < 4 else -1)
	ui.set_objective(chapter.tasks[task_index].name if task_index < 4 else "Together in the shelter", task_index, 4)

func _process(delta: float) -> void:
	interact_verb = ""
	if not is_instance_valid(ui): return
	war_mix.update(delta, mode)
	if mode == "staging":
		update_stage(delta)
		return
	if mode == "blast":
		blast_time += delta
		if blast_time >= 2.4 and not blast_hit:
			blast_hit = true
			world.aftermath()
			world.dust.visible = not reduced_effects
			world.dust.restart()
			world.dust.emitting = not reduced_effects
			play_effect("ww2-impact")
			war_mix.duck_siren()
			war_mix.aircraft.stop()
			war_mix.effect("shutter")
			blast_caption.text = "[A nearby blast. A shutter crashes.]"
			war_audio.volume_db = -45 if audio_enabled else -80
			world.tan.pose = "flinch"
			world.mei.pose = "flinch"
		if blast_hit:
			var strength := maxf(0, 1 - (blast_time - 2.4) / 1.3)
			world.flash.light_energy = 0 if reduced_effects else strength * 3
			player.visual.position.y = -0.25 * strength
			player.visual.rotation.x = 0.15 * strength
			body_pose.crouch = strength
			world.tan.rotation.z = -0.22 * strength
			world.mei.rotation.x = 0.12 * strength
			watch_camera.h_offset = 0 if reduced_effects else sin(blast_time * 47) * strength * 0.055
			if blast_time > 3.7:
				world.tan.pose = "listen"
				world.mei.pose = "beckon"
			if blast_time > 4.5:
				var shelter_direction: Vector3 = Vector3(0, 0, -3) - player.position
				player.visual.rotation.y = lerp_angle(player.visual.rotation.y, atan2(shelter_direction.x, shelter_direction.z), minf(delta * 3, 1))
				var tan_direction: Vector3 = Vector3(0, 0, -3) - world.tan.position
				world.tan.rotation.y = lerp_angle(world.tan.rotation.y, atan2(tan_direction.x, tan_direction.z), minf(delta * 3, 1))
		if blast_time > 6.2:
			finish_blast()
		return
	if mode != "play" or task_index >= 4: return
	if task_index == 2 or task_index == 3:
		var destination: Vector3 = player.position + Vector3(-1.4, 0, 1)
		if task_index == 2 and player.position.z > 0:
			destination.z = maxf(destination.z, 1)
		if player.position.z < -2 and world.tan.position.z > -3:
			destination = Vector3(0, 0, -3.5)
		world.tan.position = world.tan.position.move_toward(destination, delta * 2.9)
		world.tan.rotation.y = atan2(player.position.x - world.tan.position.x, player.position.z - world.tan.position.z)
	var target: Vector3 = chapter.tasks[task_index].at
	var distance := Vector2(player.position.x - target.x, player.position.z - target.z).length()
	if distance <= INTERACT_DISTANCE:
		interact_verb = ["Talk", "Talk", "Carry water", "Set down pail"][task_index]
	var relative: Vector3 = camera.global_basis.inverse() * (target - player.position)
	var direction := "Ahead" if relative.z < 0 else "Behind you"
	if absf(relative.x) > absf(relative.z):
		direction = "To your left" if relative.x < 0 else "To your right"
	ui.set_navigation("%s · %d m" % [direction, int(distance)] if interact_verb.is_empty() else ("Tap the gold button" if TouchControls.available() else "Press E"))
	ui.set_prompt(chapter.tasks[task_index].name if not interact_verb.is_empty() else "")

func interact() -> bool:
	if mode != "play" or task_index >= 4: return false
	var target: Vector3 = chapter.tasks[task_index].at
	if Vector2(player.position.x - target.x, player.position.z - target.z).length() > INTERACT_DISTANCE: return false
	match task_index:
		0:
			conversation([
				["Uncle Tan", "Sparky, give us a hand. Mei is getting everyone into the shelter. We need water inside."],
				["Sparky", "Is the fighting close?"],
				["Uncle Tan", "They came down through Malaya. Now they've crossed from Johor. There's fighting on the island."],
			], complete_task)
		1:
			world.shutters_closing = true
			war_mix.effect("shutter")
			conversation([
				["Mei", "The water pail is by the courtyard barrel. Bring it here. I'll make room for the next family."],
				["Uncle Tan", "I'll come with you, Sparky. Stay close. We'll be inside soon."],
			], complete_task)
		2:
			begin_stage("pickup", 1.9)
		3:
			begin_stage("setdown", 2.2)
	return true

func conversation(script: Array, after: Callable) -> void:
	set_mode("dialogue")
	world.set_active(-1)
	lines = script.duplicate()
	lines_done = after
	next_line()

func next_line() -> void:
	if lines.is_empty():
		lines_done.call()
		return
	var line: Array = lines.pop_front()
	frame_wartime_conversation(line[0])
	if task_index == 3:
		world.tan.pose = "speak" if line[0] == "Uncle Tan" else "listen"
		world.mei.pose = "speak" if line[0] == "Mei" else "listen"
	else:
		world.tan.pose = "speak" if line[0] == "Uncle Tan" else "listen"
		world.mei.pose = "beckon" if task_index == 2 else ("speak" if line[0] == "Mei" else "listen")
	show_dialogue(line[0], line[1], next_line)

func complete_task() -> void:
	task_index += 1
	checkpoint = task_index
	write_save()
	if task_index == 4: show_complete()
	else: resume_play()

func start_blast() -> void:
	set_mode("blast")
	blast_time = 0
	blast_hit = false
	world.set_active(-1)
	frame_wartime_conversation("Uncle Tan")
	war_mix.start_siren()
	blast_overlay()

func blast_overlay() -> void:
	ui.new_overlay(false)
	var panel := sequence_panel()
	blast_caption = ui.label(panel, "[A nearby blast. A shutter crashes.]" if blast_hit else "[An air-raid siren rises.]", 20, Interface.PAPER)
	ui.label(panel, "Mei: Sparky! Tan! Get inside!", 22, Interface.PAPER)

func finish_blast() -> void:
	if mode != "blast" or blast_time < 6.2: return
	world.flash.light_energy = 0
	camera.h_offset = 0
	player.visual.position = original_visual_position
	player.visual.rotation.x = 0
	body_pose.crouch = 0
	watch_camera.h_offset = 0
	world.tan.pose = "listen"
	world.mei.pose = "beckon"
	world.tan.rotation.z = 0
	world.mei.rotation.x = 0
	world.aftermath()
	blast_audio.stop()
	world.dust.emitting = false
	world.dust.visible = false
	conversation([
		["Uncle Tan", "Wait—the shop—"],
		["Mei", "Leave it, Tan. Come inside!"],
	], complete_task)

func play_effect(effect: String) -> void:
	blast_audio.stream = load("res://assets/audio/%s.wav" % effect)
	if audio_enabled: blast_audio.play()

func pause_game() -> void:
	if mode != "play": return
	paused_mode = mode
	set_mode("pause")
	war_audio.stream_paused = true
	blast_audio.stream_paused = true
	world.dust.speed_scale = 0
	var v: VBoxContainer = ui.modal()
	ui.label(v, "A moment to pause", 32, Interface.INK)
	ui.button(v, "Continue", resume_pause).grab_focus()
	ui.button(v, "Restart 1942", start_new, true)
	ui.button(v, "Return to title", show_menu, true)
	var quiet := CheckButton.new()
	quiet.text = "Sound"
	quiet.button_pressed = audio_enabled
	quiet.toggled.connect(func(value: bool):
		audio_enabled = value
		war_audio.volume_db = (-45 if war_mix.indoors else -27) if value else -80
		blast_audio.volume_db = -14 if value else -80
		war_mix.mute(not value)
	)
	v.add_child(quiet)
	var reduced := CheckButton.new()
	reduced.text = "Reduce blast motion and light"
	reduced.button_pressed = reduced_effects
	reduced.toggled.connect(func(value: bool):
		reduced_effects = value
		if value:
			camera.h_offset = 0
			watch_camera.h_offset = 0
			world.flash.light_energy = 0
			world.dust.emitting = false
	)
	v.add_child(reduced)

func resume_pause() -> void:
	world.dust.speed_scale = 1
	war_audio.stream_paused = false
	blast_audio.stream_paused = false
	if paused_mode == "blast":
		set_mode("blast")
		blast_overlay()
	elif paused_mode == "staging":
		set_mode("staging")
		stage_overlay()
	else: resume_play()

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("pause_game") and mode in ["blast", "staging", "pause"]:
		if mode == "pause": resume_pause()
		else: pause_game()
		get_viewport().set_input_as_handled()
	else: super._unhandled_input(event)

func show_complete() -> void:
	set_mode("complete")
	world.set_active(-1)
	ui.hud.visible = false
	var v: VBoxContainer = ui.modal()
	ui.label(v, "1942 · A MOMENT OF SHELTER", 15, Interface.TEAL)
	ui.label(v, "What came next", 36, Interface.INK)
	ui.paragraph(v, "On 15 February 1942, British-led forces surrendered Singapore to Japan. The Japanese Occupation followed, lasting until 1945. Civilians endured shortages, persecution and violence.", 22)
	ui.paragraph(v, "The shelter was a moment of safety at the beginning of a much longer ordeal.", 19, Interface.MUTED)
	ui.button(v, "Continue to 1965   →", enter_1965).grab_focus()
	ui.button(v, "Journal · What happened next?", show_journal, true)
	ui.button(v, "Return to title", show_menu, true)

func enter_1965() -> void:
	get_tree().set_meta("enter_1965", true)
	get_tree().change_scene_to_file("res://scenes/main.tscn")

func show_journal() -> void:
	if mode not in ["play", "complete", "journal"]: return
	if mode != "journal": journal_return = mode
	set_mode("journal")
	war_audio.stream_paused = true
	var v: VBoxContainer = ui.modal(850)
	ui.label(v, "SPARKY'S JOURNAL · 1942–1945", 16, Interface.TEAL)
	var pages := [
		["A street under threat", "Japanese forces advanced down Malaya and crossed the Johor Strait. The main landings on Singapore's northwest coast began on 8 February 1942. British-led forces surrendered on 15 February.\n\nSome coastal guns could fire inland and did so. The defeat cannot be explained simply by saying the guns pointed the wrong way."],
		["What happened next", "During the Japanese Occupation, food shortages and fear changed everyday life. People grew food, found substitutes and helped neighbours survive.\n\nJapanese forces also carried out persecution and mass killings. During Sook Ching, many Chinese civilians were taken away and killed. These losses remain part of Singapore's wartime memory.\n\nThe Occupation ended in 1945. Recovery took time."],
		["Our imagined encounter", "Sparky, Uncle Tan, Mei, their dialogue, this street and the nearby blast are fictional. This is not a reconstruction of a particular raid or shelter. Sparky's hooded civilian outfit is a stylised costume.\n\n" + ("We brought water into the shelter. Mei shared it, and Uncle Tan stayed with the neighbours." if checkpoint >= 4 else "Our task: help Uncle Tan and Mei bring water into the shelter.") + "\n\nWASD / left thumb: move. Mouse / right thumb: look. E / gold button: interact. J: journal. Escape: pause. The blast plays through; reduced motion/light and sound controls are in Pause. Sound effects combine original synthesis and a modern siren recording, not wartime archival audio."],
	]
	ui.label(v, pages[journal_page][0], 32, Interface.INK)
	ui.paragraph(v, pages[journal_page][1], 19)
	ui.button(v, "Historical source · NHB: World War Two", func(): OS.shell_open("https://www.roots.gov.sg/stories-landing/stories/world-war-ii/story"), true)
	ui.button(v, "Historical source · National Museum: coastal guns", func(): OS.shell_open("https://www.nhb.gov.sg/nationalmuseum/-/media/nms2024/documents/media-releases/220128-dislocations-memory-meaning-fall-of-singapore.pdf"), true)
	var row := HBoxContainer.new()
	v.add_child(row)
	ui.button(row, "Previous", func(): journal_page = posmod(journal_page - 1, 3); show_journal(), true)
	ui.label(row, "  %d / 3  " % (journal_page + 1), 18, Interface.MUTED)
	ui.button(row, "Next", func(): journal_page = (journal_page + 1) % 3; show_journal(), true)
	ui.button(v, "Close journal", close_journal).grab_focus()

func read_save() -> void:
	if not persistence_enabled: return
	var config := ConfigFile.new()
	if config.load(save_path) == OK:
		var saved: Variant = config.get_value("progress", "task", 0)
		if saved is int and saved >= 0 and saved <= 4:
			checkpoint = saved
			has_save = true

func set_mode(value: String) -> void:
	super.set_mode(value)
	var freeze := value in ["intro", "menu", "pause", "journal", "complete"]
	if is_instance_valid(world): world.animations_paused = freeze
	if is_instance_valid(war_mix): war_mix.pause_audio(freeze)
	if is_instance_valid(player) and is_instance_valid(player.animator):
		player.animator.speed_scale = 0 if freeze else 1

func cut_camera(at: Vector3, aim: Vector3, lens := 58.0) -> void:
	# Mask authored position changes with a brief editorial fade, only on a new shot.
	if not watch_camera.current or watch_camera.position.distance_to(at) > 0.2:
		var transition := CanvasLayer.new()
		transition.layer = 100
		add_child(transition)
		var shade := ColorRect.new()
		shade.color = Color(0.06, 0.055, 0.045, 1)
		shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
		shade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		transition.add_child(shade)
		var fade := create_tween()
		fade.tween_property(shade, "color:a", 0.0, 0.22)
		fade.tween_callback(transition.queue_free)
	if watch_tween: watch_tween.kill()
	watch_camera.position = at
	watch_camera.look_at(aim)
	watch_camera.fov = lens
	watch_camera.make_current()

func frame_wartime_conversation(speaker: String) -> void:
	match task_index:
		0:
			player.position = Vector3(-1.2, 0.1, 6.2)
			face_tan()
			cut_camera(Vector3(3, 2.5, 3.6), Vector3(-0.3, 1.1, 6.8))
		1:
			player.position = Vector3(2.2, 0.1, 0.2)
			player.visual.rotation.y = atan2(world.mei.position.x - player.position.x, world.mei.position.z - player.position.z)
			world.mei.rotation.y = 0.8
			world.tan.position = Vector3(1.6, 0, 1.5)
			world.tan.rotation.y = -1.5
			cut_camera(Vector3(-5, 2.5, 3.3), Vector3(-1, 1.1, -0.3), 62)
		2:
			if carried_water.visible and not blast_hit:
				face_tan()
			if speaker == "Mei":
				cut_camera(Vector3(3, 2.4, 2), Vector3(-1.2, 1.2, -1.6), 56)
			else:
				cut_camera(Vector3(9.8, 2.5, 4.5), Vector3(6.4, 1.0, 1.6), 62)
		3:
			if mode == "dialogue":
				var focus: Vector3 = world.tan.position if speaker == "Uncle Tan" else world.mei.position
				if speaker == "Neighbour": focus = world.evacuees[0].position
				var toward := focus - player.position
				player.visual.rotation.y = atan2(toward.x, toward.z)
				var tan_focus: Vector3 = world.mei.position if speaker == "Mei" else player.position
				var mei_focus: Vector3 = world.tan.position if speaker == "Uncle Tan" else player.position
				world.tan.rotation.y = atan2(tan_focus.x - world.tan.position.x, tan_focus.z - world.tan.position.z)
				world.mei.rotation.y = atan2(mei_focus.x - world.mei.position.x, mei_focus.z - world.mei.position.z)
			cut_camera(Vector3(-1.0, 2.55, -5.1), Vector3(-1.2, 1.0, -8.3), 70)

func stage_overlay() -> void:
	ui.new_overlay(false)
	ui.hud.visible = false
	var panel := sequence_panel()
	var captions := {"pickup": "Sparky lifts the water pail.", "setdown": "[The door closes. Outside sounds fade.]", "quiet": "Mei brings water to a neighbour. Uncle Tan rests a hand on Sparky’s shoulder."}
	ui.label(panel, captions[stage_kind], 19, Interface.PAPER)

func begin_stage(kind: String, duration: float) -> void:
	stage_kind = kind
	stage_clock = 0
	stage_duration = duration
	stage_sound_played = false
	set_mode("staging")
	world.set_active(-1)
	player.scripted_motion = true
	player.velocity = Vector3.ZERO
	player.play_animation("Idle")
	var palm_offset: Vector3 = player.visual.to_local(body_pose.carry_hand_world())
	if kind == "pickup":
		player.visual.rotation.y = PI / 2
		player.position = world.pail.position - player.visual.basis * palm_offset
		player.position.y = 0.1
		body_pose.carry = 1
		world.tan.position = Vector3(4.9, 0, 1.9)
		world.tan.rotation.y = 1.7
		prop_start = world.pail.global_position
		stage_target = player.visual.to_global(palm_offset) - Vector3.UP * 0.52
		frame_wartime_conversation("Sparky")
	elif kind == "setdown":
		player.position = Vector3(-1.05, 0.1, -8.55)
		player.visual.rotation.y = -2.2
		world.close_shelter()
		war_mix.enter_shelter()
		war_audio.volume_db = -45 if audio_enabled else -80
		blast_audio.stop()
		prop_start = player.visual.to_global(palm_offset) - Vector3.UP * 0.52
		stage_target = world.WATER_SPOT
		carried_water.visible = false
		world.pail.visible = true
		world.pail.global_position = prop_start
		body_pose.carry = 0
		frame_wartime_conversation("Mei")
	else:
		cut_camera(Vector3(0, 2.7, -3.5), Vector3(0, 1, -7.8), 78)
		var neighbour_direction: Vector3 = world.evacuees[0].position - player.position
		player.visual.rotation.y = atan2(neighbour_direction.x, neighbour_direction.z)
		world.comfort_target = player.position + Vector3(0.45, 1.05, 0.05)
		world.begin_pour()
		war_mix.fade_siren()
		war_mix.effect("water")
	stage_overlay()

func update_stage(delta: float) -> void:
	stage_clock += delta
	var t := clampf(stage_clock / stage_duration, 0, 1)
	if stage_kind != "quiet":
		var reach := sin(t * PI)
		if stage_kind == "pickup":
			var lowering := smoothstep(0, 0.5, t) if t < 0.5 else 1 - smoothstep(0.5, 1, t)
			player.visual.position.y = -(stage_target.y - prop_start.y) * lowering
			player.visual.rotation.x = 0
			world.pail.global_position = prop_start.lerp(stage_target, smoothstep(0.5, 1, t))
		else:
			player.visual.position.y = -0.2 * reach
			player.visual.rotation.x = 0.24 * reach
			world.pail.global_position = prop_start.lerp(stage_target, smoothstep(0.2, 0.85, t))
		body_pose.quiet = 0.8 * reach
		if t > 0.35 and not stage_sound_played:
			stage_sound_played = true
			war_mix.effect("water")
	if t >= 1: finish_stage()

func finish_stage() -> void:
	if mode != "staging" or stage_clock < stage_duration: return
	player.scripted_motion = false
	player.visual.position = original_visual_position
	player.visual.rotation.x = 0
	if stage_kind == "pickup":
		world.pail.visible = false
		carried_water.visible = true
		body_pose.carry = 1
		conversation([
			["Sparky", "Can the defences hold?"],
			["Uncle Tan", "They said Singapore was a fortress."],
		], start_blast)
	elif stage_kind == "setdown":
		world.pail.position = stage_target
		body_pose.quiet = 1
		conversation([
			["Mei", "On the table, beside the cups. Thank you, Sparky."],
			["Neighbour", "Is anyone still outside?"],
			["Uncle Tan", "I couldn't see anyone. Stay close, Sparky."],
			["Mei", "Have a little water. You can rest here."],
			["Sparky", "Uncle Tan... I'm still shaking."],
			["Uncle Tan", "Come here, Sparky. I'm here."],
			["Sparky", "Will you stay?"],
			["Uncle Tan", "Of course. Right here beside you."],
		], func(): begin_stage("quiet", 7.6))
	else:
		world.finish_relief()
		complete_task()

func sequence_panel() -> VBoxContainer:
	var backing := PanelContainer.new()
	backing.position = Vector2(30, 36)
	backing.add_theme_stylebox_override("panel", ui.style(Color(0.08, 0.12, 0.11, 0.88), 12))
	ui.overlay.add_child(backing)
	var content := VBoxContainer.new()
	content.add_theme_constant_override("separation", 8)
	backing.add_child(content)
	return content

func face_tan() -> void:
	var towards: Vector3 = world.tan.global_position - player.global_position
	player.visual.rotation.y = atan2(towards.x, towards.z)
	world.tan.rotation.y = atan2(-towards.x, -towards.z)

func frame_conversation() -> void:
	# The 1965 base class requests its own camera after Tan's dialogue.
	# Wartime conversations are already framed by next_line before rendering.
	pass
