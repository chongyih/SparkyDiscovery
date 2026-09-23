extends SceneTree
## Exercise gameplay state, keyboard motion, proximity, puzzle gating and completion.
var failures := 0
var game: Node

func _initialize() -> void:
	call_deferred("run")

func check(condition: bool, description: String) -> void:
	if condition:
		print("PASS: " + description)
	else:
		push_error("FAIL: " + description)
		failures += 1

func frames(count: int) -> void:
	for i in count:
		await physics_frame

func wait_mode(expected: String, timeout: float) -> void:
	var deadline := Time.get_ticks_msec() + int(timeout * 1000)
	while game.mode != expected and Time.get_ticks_msec() < deadline:
		await process_frame
	check(game.mode == expected, "Sequence reaches " + expected)

func run() -> void:
	game = load("res://scenes/main.tscn").instantiate()
	root.add_child(game)
	await frames(4)
	check(game.mode == "menu", "Title screen opens")
	check(game.player.animator != null, "Supplied Sparky animation player imported")
	game.start_new()
	check(game.mode == "intro" and not game.player.enabled, "Introduction locks movement")
	game.resume_play()
	check(game.mode == "play" and game.task_index == 0, "New chapter starts at first objective")
	check(game.camera.projection == Camera3D.PROJECTION_PERSPECTIVE, "Gameplay uses a third-person perspective camera")
	check(game.follow_camera.enabled and game.camera.current, "Follow camera is active during gameplay")
	await frames(4)
	var sight := PhysicsRayQueryParameters3D.create(game.camera.global_position, game.player.global_position + Vector3(0, 1.5, 0))
	sight.exclude = [game.player.get_rid()]
	check(game.get_world_3d().direct_space_state.intersect_ray(sight).is_empty(), "Initial camera has a clear view of Sparky")
	check(not game.interact(), "Cannot interact from across the street")
	var before: Vector3 = game.player.position
	Input.action_press("move_right")
	await frames(30)
	Input.action_release("move_right")
	check(game.player.position.distance_to(before) > 0.5, "Keyboard movement moves Sparky")
	game.player.position = Vector3(0, 0.2, 14)
	game.follow_camera.reset()
	await frames(5)
	check(game.follow_camera.arm.get_hit_length() < 4.0, "The camera retracts before the shop banner and awning")
	# Walk into the solid shopfront, then into the visible boundary wall.
	game.player.position = Vector3(0, 0.1, 16)
	game.follow_camera.reset()
	Input.action_press("move_down")
	await frames(65)
	Input.action_release("move_down")
	check(game.player.position.z < 18.55, "Shopfront collision prevents walking through buildings")
	game.player.position = Vector3(22, 0.1, 6)
	game.player.velocity = Vector3.ZERO
	Input.action_press("move_right")
	await frames(65)
	Input.action_release("move_right")
	check(game.player.position.x < 24, "Visible boundary wall contains the explorable neighbourhood")
	# Put a shop behind the orbit camera; the spring arm must shorten.
	game.player.position = Vector3(0, 0.1, 16)
	game.follow_camera.reset()
	game.follow_camera.yaw = 0
	await frames(20)
	check(game.follow_camera.arm.get_hit_length() < game.follow_camera.distance - 0.5, "Camera retracts when a building blocks its view")
	game.follow_camera.reset()
	game.pause_game()
	await frames(20)
	before = game.player.position
	Input.action_press("move_left")
	await frames(20)
	Input.action_release("move_left")
	check(game.player.position.distance_to(before) < 0.05, "Pause blocks movement")
	game.resume_play()
	game.player.position = game.chapter.tasks[2].at + Vector3(0, 0.1, 1.4)
	check(not game.interact(), "Television cannot skip neighbour and aerial objectives")
	for i in 2:
		game.player.position = game.chapter.tasks[i].at + Vector3(0, 0.1, 1.4)
		if i == 0:
			var interact_key := InputEventAction.new()
			interact_key.action = "interact"
			interact_key.pressed = true
			game._unhandled_input(interact_key)
			check(game.mode == "dialogue", "E input opens nearby neighbour dialogue")
		else:
			check(game.interact(), "Objective %d accepts nearby interaction" % i)
		check(game.mode == "dialogue" and game.task_index == i, "Reading has not yet completed objective %d" % i)
		if i == 0:
			check(game.dialogue_voice.playing and game.dialogue_voice.stream.get_length() > 10, "Kelvin opening voice plays")
			var mute: Button = game.ui.overlay.find_child("MuteVoice", true, false)
			mute.pressed.emit()
			check(is_zero_approx(game.dialogue_voice.volume_linear), "Dialogue can be muted")
			mute.pressed.emit()
			game.dialogue_voice.stop()
			game.ui.overlay.find_child("ReplayVoice", true, false).pressed.emit()
			check(game.dialogue_voice.playing and game.task_index == 0, "Replay does not advance the conversation")
		else:
			check(game.dialogue_voice.stream == null, "Narration remains text-only")
		game.advance_dialogue()
		check(not game.dialogue_voice.playing, "Continuing stops dialogue voice %d" % i)
		check(game.task_index == i + 1 and game.checkpoint == i + 1, "Objective %d advances checkpoint" % i)
	check(not game.world.spare_aerial.visible and game.carried_aerial.visible, "Collecting the aerial moves it from the table to Sparky")
	game.save_path = "res://artifacts/test-progress.cfg"
	game.persistence_enabled = true
	game.write_save()
	game.checkpoint = 0
	game.read_save()
	check(game.checkpoint == 2, "Checkpoint survives a disk save and reload")
	DirAccess.remove_absolute(game.save_path)
	game.persistence_enabled = false
	game.show_menu()
	game.continue_saved()
	check(game.task_index == 2 and game.mode == "play", "Continue restores checkpoint")
	game.show_journal()
	check(game.mode == "journal" and not game.player.enabled, "Journal suspends gameplay")
	game.close_journal()
	check(game.mode == "play", "Journal returns to gameplay")
	game.player.position = game.chapter.tasks[2].at + Vector3(0, 0.1, 1.4)
	game.interact()
	check(game.mode == "fitting" and not game.aerial_fitted, "The aerial is visibly fitted before tuning")
	await wait_mode("puzzle", 8)
	check(game.aerial_fitted and game.world.tv_aerial.visible and not game.carried_aerial.visible, "Fitting transfers the aerial onto the television")
	game.finish_tuning()
	check(game.mode == "puzzle", "Poor signal cannot reveal announcement")
	var dial = game.ui.overlay.find_child("AntennaTuner", true, false)
	var touch := InputEventScreenTouch.new()
	touch.index = 0
	touch.pressed = true
	dial.handle_input(touch)
	var swipe := InputEventScreenDrag.new()
	swipe.index = 1
	swipe.relative = Vector2(dial.size.x * 0.3, 0)
	dial.handle_input(swipe)
	check(is_equal_approx(dial.value, 20.0), "A second finger cannot hijack the antenna gesture")
	swipe.index = 0
	dial.handle_input(swipe)
	check(absf(dial.value - 65.0) < 0.1, "A broad touch swipe adjusts the antenna")
	game.finish_tuning()
	check(game.mode == "puzzle", "A fleeting clear signal does not skip settling")
	dial.adjust(-30)
	await create_timer(0.9).timeout
	check(not dial.locked, "Leaving the clear region resets settling")
	dial.adjust(30)
	await create_timer(0.9).timeout
	check(dial.locked, "A stable picture locks without precision holding")
	dial.adjust(-100)
	check(is_equal_approx(dial.value, 65.0), "A locked signal resists accidental swipes")
	await wait_mode("arrival", 3)
	check(game.mode == "arrival" and not game.player.seated, "Clear signal starts the walk-to-seat sequence")
	var uncle_before: Vector3 = game.world.stations[0].position
	await frames(45)
	check(game.world.stations[0].position.distance_to(uncle_before) > 0.5, "Uncle Tan walks over from the pavement")
	await wait_mode("video", 15)
	check(game.ui.archive_player.stream is VideoStreamTheora, "Archival clip loads as native Godot video")
	check(game.ui.archive_player.self_modulate.a == 0.0, "Video decoder has no onscreen popup surface")
	check(game.world.tv_screen.material_override.albedo_texture == game.ui.archive_player.get_video_texture(), "Actual video texture is bound to the 3D television")
	check(game.world.community.residents.size() == 7, "Neighbours gather on shared benches")
	check(game.player.seated, "Sparky sits with the neighbours during the broadcast")
	var seated_at: Vector3 = game.player.position
	await frames(12)
	check(game.player.position.is_equal_approx(seated_at), "Seated Sparky stays on the bench instead of falling or sliding")
	check(not game.world.stations[0].visible and game.world.community.residents[5].root.visible, "The waiting neighbour joins the seated gathering")
	game.set_broadcast_view("walk")
	check(game.player.enabled and game.camera.current, "Sparky can walk around while the television plays")
	check(not game.player.seated and game.player.position.x < 1.0, "Walking restores the standing pose in the clear aisle")
	game.set_broadcast_view("television")
	check(not game.player.enabled and game.watch_camera.current, "Closer TV view keeps playback in the world")
	check(game.player.seated, "Returning to a viewing camera reseats Sparky")
	game.set_broadcast_view("community")
	await frames(90)
	check(game.ui.archive_player.stream_position > 0.5, "Archival footage advances during playback")
	game.ui.toggle_video_pause()
	var paused_at: float = game.ui.archive_player.stream_position
	await frames(20)
	check(absf(game.ui.archive_player.stream_position - paused_at) < 0.08, "Pausing preserves video position")
	game.ui.toggle_video_pause()
	# Seek instead of watching the whole clip; captions and reactions follow the footage clock.
	check(is_equal_approx(game.ui.archive_player.get_stream_length(), 118.0), "Archival clip matches the 01:58 excerpt shown in the player")
	game.ui.archive_player.stream_position = 64.0
	await frames(6)
	check(game.ui.archive_caption.text == "You see, the whole of my adult life…", "Captions follow a seek in the footage")
	check(game.ui.archive_clock.text == "01:04 / 01:58", "Player clock follows a seek in the footage")
	# The final 1.5 seconds still play for real, so the decoder's own end-of-file signal is exercised.
	game.ui.archive_player.stream_position = game.ui.archive_player.get_stream_length() - 1.5
	await wait_mode("dialogue", 8)
	check(game.mode == "dialogue", "Actual end-of-file returns automatically to the historical reflection")
	check(game.dialogue_voice.playing and game.dialogue_voice.stream.resource_path.ends_with("after_broadcast.mp3"), "Post-broadcast reply plays its matching voice")
	check(game.world.community.residents[0].tear.visible, "Emotional reactions develop during the actual broadcast")
	game.advance_dialogue()
	check(game.mode == "reflection" and game.checkpoint == 2, "The closing conversation comes before chapter completion")
	for topic in ["homes", "jobs", "future"]:
		game.ask_reflection(topic)
		check(game.mode == "dialogue" and game.reflection_topics.has(topic), "Uncle Tan answers about " + topic)
		check(game.dialogue_voice.playing and game.dialogue_voice.stream.resource_path.ends_with(topic + ".mp3"), "Matching optional reply voice: " + topic)
		game.advance_dialogue()
		check(not game.dialogue_voice.playing, "Reply stops when returning to choices")
		check(game.mode == "reflection", "Answers return to the optional conversation choices")
	game.finish_reflection()
	check(game.dialogue_voice.playing and game.dialogue_voice.stream.resource_path.ends_with("farewell.mp3"), "Farewell is voiced")
	game.advance_dialogue()
	check(game.mode == "complete" and game.task_index == 3, "Chapter reaches completion")
	game.show_journal()
	game.close_journal()
	check(game.mode == "complete", "Completed journal returns to chapter summary")
	game.start_new()
	check(game.task_index == 0 and game.checkpoint == 0, "Restart resets all objectives")
	check(not game.player.seated, "Restart clears Sparky's seated pose")
	check(not game.world.community.residents[0].tear.visible, "Restart resets the neighbours' reactions")
	game.checkpoint = 2
	game.continue_saved()
	game.player.position = game.chapter.tasks[2].at + Vector3(0, 0.1, 1.4)
	game.interact()
	game.show_menu()
	await frames(60)
	check(game.mode == "menu" and not game.aerial_fitted, "Leaving a sequence cancels pending changes")
	game.continue_saved()
	game.player.position = game.chapter.tasks[2].at + Vector3(0, 0.1, 1.4)
	game.interact()
	game.staging.finish_fitting(game.staging.serial)
	dial = game.ui.overlay.find_child("AntennaTuner", true, false)
	dial.adjust(45)
	await create_timer(0.9).timeout
	game.finish_tuning()
	game.staging.finish_arrival()
	game.finish_archive()
	check(game.mode == "dialogue", "Skipping footage also reaches the reflection")
	game.advance_dialogue()
	game.finish_reflection()
	check(game.dialogue_voice.playing and game.dialogue_voice.stream.resource_path.ends_with("farewell.mp3"), "Farewell is voiced")
	game.advance_dialogue()
	check(game.mode == "complete", "Players can finish without choosing a reflection topic")
	game.queue_free()
	await process_frame
	print("RESULT: %d failures" % failures)
	quit(1 if failures else 0)
