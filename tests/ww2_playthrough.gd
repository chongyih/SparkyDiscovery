extends SceneTree
var failures := 0
var game: Node
var test_save := "/tmp/sparky-ww2-%d.cfg" % OS.get_process_id()

func _initialize() -> void:
	call_deferred("run")

func check(value: bool, description: String) -> void:
	print(("PASS: " if value else "FAIL: ") + description)
	if not value: failures += 1

func frames(count: int) -> void:
	for i in count: await process_frame

func finish_dialogue() -> void:
	var limit := 20
	while game.mode == "dialogue" and limit > 0:
		if game.task_index == 3 and game.dialogue_context.get("speaker") == "Sparky":
			var toward_tan: Vector3 = game.world.tan.position - game.player.position
			toward_tan.y = 0
			check(game.player.visual.basis.z.normalized().dot(toward_tan.normalized()) > 0.98, "Sparky faces Tan during his shelter questions")
		game.advance_dialogue()
		limit -= 1
	check(limit > 0, "Dialogue advances without a loop")

func capture(name: String) -> void:
	if not OS.get_cmdline_user_args().has("--render"): return
	await create_timer(0.7).timeout
	RenderingServer.force_draw(false)
	root.get_texture().get_image().save_png("res://artifacts/ww2-" + name + ".png")

func run() -> void:
	DirAccess.make_dir_recursive_absolute("res://artifacts")
	game = load("res://scenes/ww2.tscn").instantiate()
	root.add_child(game)
	current_scene = game
	await frames(5)
	check(game.mode == "intro", "WWII intro opens")
	check(not game.world.dust.visible and not game.world.dust.emitting, "Blast dust is hidden on chapter load")
	check("ww2-civilian" in game.player.model_path, "Civilian model is used")
	game.resume_play()
	await capture("street")
	check(not game.interact(), "Tasks require proximity")
	game.pause_game()
	check(not game.player.enabled, "Pause disables movement")
	game.resume_pause()
	game.show_journal()
	check(game.mode == "journal", "Journal opens during play")
	await capture("journal")
	game.close_journal()
	check(game.mode == "play", "Journal restores gameplay")
	for i in 3:
		game.player.position = game.chapter.tasks[i].at + Vector3(0, 0.1, 1)
		check(game.interact(), "Interaction " + str(i))
		if i == 0:
			check(game.dialogue_voice.playing, "Tan's opening voice plays")
			check(game.dialogue_voice.stream.resource_path.ends_with("ww2/opening.mp3"), "Tan uses selected WWII opening")
			await capture("tan-conversation")
		if i == 1:
			check(game.dialogue_voice.playing, "Mei's selected voice plays")
			check(game.dialogue_voice.stream.resource_path.ends_with("ww2/mei_pail.mp3"), "Mei uses her own selected take")
			var clear_lane := true
			for route in game.world.resident_routes:
				for waypoint in range(route.size() - 1):
					var a: Vector3 = route[waypoint]
					var b: Vector3 = route[waypoint + 1]
					var nearest := Geometry2D.get_closest_point_to_segment(Vector2(game.player.position.x, game.player.position.z), Vector2(a.x, a.z), Vector2(b.x, b.z))
					if nearest.distance_to(Vector2(game.player.position.x, game.player.position.z)) < 1.1: clear_lane = false
			check(clear_lane, "Sparky's doorway conversation leaves resident routes clear")
			await capture("mei-conversation")
		if i == 2:
			check(game.mode == "staging" and game.stage_kind == "pickup", "Pickup is visibly staged")
			check(game.player.position.distance_to(game.world.pail.position) < 1.5, "Pickup keeps Sparky beside the pail after repositioning")
			game.pause_game()
			check(game.mode == "staging", "Pickup plays through without pausing")
			check(game.ui.overlay.find_children("*", "Button", true, false).is_empty(), "Scripted scene has no skip or pause buttons")
			await capture("pickup")
			game.update_stage(game.stage_duration)
		finish_dialogue()
	check(game.mode == "blast", "Water collection starts siren sequence")
	check(game.dialogue_voice.playing and game.dialogue_voice.stream.resource_path.ends_with("ww2/mei_get_inside.mp3"), "Mei calls everyone inside during the siren")
	var facing: Vector3 = (game.world.tan.position - game.player.position).normalized()
	check(game.player.visual.basis.z.normalized().dot(facing) > 0.98 and game.world.tan.basis.z.normalized().dot(-facing) > 0.98, "Sparky and Tan face each other before the blast")
	var skip_found := false
	for button in game.ui.overlay.find_children("*", "Button", true, false):
		if "Skip" in button.text or "Pause" in button.text: skip_found = true
	check(not skip_found, "Blast overlay has no skip or pause control")
	game.pause_game()
	check(game.mode == "blast", "Blast plays through without pausing")
	game._process(2.6)
	check(game.blast_hit and game.world.keys.visible, "Impact changes the street")
	check(game.world.dust.visible, "Dust appears during the blast")
	check(game.war_mix.siren.playing and game.war_mix.siren_level <= -39, "Impact ducks the independent siren without stopping it")
	await capture("blast")
	await capture("blast-dispersing")
	await capture("blast-clearing")
	game.finish_blast()
	check(game.mode == "blast", "Blast cannot be skipped before its duration")
	game._process(4.0)
	check(not game.world.dust.visible, "Dust is hidden when the blast ends")
	check(game.war_mix.siren.playing, "Siren continues after the blast")
	finish_dialogue()
	# SkeletonModifier3D temporarily changes bone poses, then restores the base animation.
	# Sample its signal, while the actual rendered pose is available.
	var attachment_samples := [0, 0.0]
	var sample_attachment := func():
		var rig: Skeleton3D = game.player.skeleton
		var arm := rig.find_bone("arm.R")
		var palm := rig.get_bone_global_rest(arm).affine_inverse() * Vector3(-0.93, 0.85, 0.006)
		var hand := rig.global_transform * (rig.get_bone_global_pose(arm) * palm)
		attachment_samples[0] += 1
		attachment_samples[1] = maxf(attachment_samples[1], (game.carried_water.global_position + Vector3.UP * 0.52).distance_to(hand))
	game.body_pose.modification_processed.connect(sample_attachment)
	await frames(3)
	game.body_pose.modification_processed.disconnect(sample_attachment)
	check(attachment_samples[0] > 0 and attachment_samples[1] < 0.06, "Carried pail stays attached to the animated mitten")
	check(game.checkpoint == 3 and game.carried_water.visible, "Timed blast commits return-to-shelter checkpoint")
	check(game.camera.h_offset == 0 and game.world.flash.light_energy == 0, "Blast ending clears transient camera and light effects")
	game.persistence_enabled = true
	game.save_path = test_save
	game.write_save()
	game.checkpoint = 0
	game.read_save()
	check(game.checkpoint == 3, "WWII save round trip")
	game.prepare_chapter()
	game.resume_play()
	check(game.carried_water.visible and not game.world.pail.visible, "Resume restores carried water")
	# The shelter entrance is physically traversable, not a teleport-only objective.
	game.player.position = Vector3(0, 0.1, 0)
	game.follow_camera.reset(0)
	Input.action_press("move_up")
	for i in 100: await physics_frame
	Input.action_release("move_up")
	check(game.player.position.z < -4, "Player walks through shelter doorway")
	game.player.position = game.chapter.tasks[3].at + Vector3(1, 0.1, 1)
	check(game.interact(), "Shelter interaction completes return")
	check(game.stage_kind == "setdown" and game.war_mix.indoors, "Shelter entry starts set-down and interior mix")
	game.war_mix.update(1.0, "staging")
	check(game.war_mix.siren_filter.cutoff_hz < 1000 and game.war_mix.siren_target == -39, "Shelter muffles and lowers the siren")
	game.update_stage(2.3)
	var toward_mei: Vector3 = game.world.mei.position - game.player.position
	toward_mei.y = 0
	check(game.player.visual.basis.z.normalized().dot(toward_mei.normalized()) > 0.98, "Sparky faces Mei from the first shelter line")
	var toward_sparky: Vector3 = game.player.position - game.world.mei.position
	toward_sparky.y = 0
	check(game.world.mei.basis.z.normalized().dot(toward_sparky.normalized()) > 0.98, "Mei faces Sparky from the first shelter line")
	await capture("shelter")
	finish_dialogue()
	check(game.mode == "staging" and game.stage_kind == "quiet", "Ending shows water being taken to a neighbour")
	game.world.update_relief(3.8)
	game.update_stage(0.01)
	var toward_comfort: Vector3 = game.world.tan.position - game.player.position
	toward_comfort.y = 0
	check(game.player.visual.basis.z.normalized().dot(toward_comfort.normalized()) > 0.98, "Sparky keeps facing Tan after their conversation")
	await capture("handoff")
	game.world.update_relief(1.0)
	await capture("relief")
	check(game.world.water_delivered and game.world.evacuees[0].seat_activity == "drink", "Water reaches a seated neighbour")
	check(game.world.pail.position.is_equal_approx(game.world.WATER_SPOT), "Pail is on the water table")
	game.war_mix.update(7.0, "staging")
	check(not game.war_mix.siren.playing, "Siren fades out during water handoff")
	game.update_stage(game.stage_duration)
	check(not game.player.scripted_motion and not game.world.water_stream.visible, "Completing quiet beat clears transient state")
	check(game.checkpoint == 4 and game.mode == "complete", "Chapter ends with historical epilogue")
	await capture("epilogue")
	game.show_journal()
	game.ui.open_page("after")
	await capture("occupation")
	game.close_journal()
	check(game.mode == "complete", "Journal returns to epilogue")
	game.checkpoint = 4
	game.prepare_chapter()
	game.show_complete()
	check(game.mode == "complete", "Completed checkpoint is resumable")
	# Also exercise the timed end (without the skip button), including reduced effects.
	game.task_index = 2
	game.begin_stage("pickup", 1.9)
	game.update_stage(2.0)
	check(game.mode == "dialogue" and game.carried_water.visible, "Timed pickup completes without skip")
	game.reduced_effects = true
	game.start_blast()
	game._process(2.5)
	check(game.world.flash.light_energy == 0 and game.camera.h_offset == 0 and game.watch_camera.h_offset == 0, "Reduced effects suppress flash and shake")
	game._process(4.0)
	check(not game.world.dust.visible, "Dust is hidden when the blast ends")
	finish_dialogue()
	check(game.mode == "play" and game.checkpoint == 3, "Timed blast completion restores play")
	game.persistence_enabled = false
	game.enter_1965()
	await frames(10)
	game = current_scene
	check(game.chapter.year == "1965" and game.mode == "intro", "Continue opens 1965 intro")
	check("Twenty-three years" in game.chapter.intro, "1965 introduction remembers the shelter")
	check(not has_meta("enter_1965"), "Transition flag is consumed")
	game.show_menu()
	await capture("title")
	DirAccess.remove_absolute(test_save)
	game.queue_free()
	await frames(3)
	print("WWII failures: ", failures)
	quit(1 if failures else 0)
