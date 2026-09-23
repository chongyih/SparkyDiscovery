extends SceneTree
## Run with a rendering display and -- --test; writes actual game viewport captures.
var game: Node
var capture_viewport: SubViewport

func _initialize() -> void:
	call_deferred("run")

func capture(file_name: String) -> void:
	await create_timer(0.9).timeout
	RenderingServer.force_draw(false)
	var snapshot := capture_viewport.get_texture().get_image()
	snapshot.save_png("res://artifacts/" + file_name + ".png")
	print("CAPTURE: " + file_name)
	# Leave the render callback before changing mouse capture or scene state.
	await process_frame

func finish_dialogue() -> void:
	# Explicitly advance every short page, stopping when its conversation ends.
	for i in 12:
		if game.mode != "dialogue":
			return
		game.advance_dialogue()

func run() -> void:
	# Render continuously even if the user is testing another Godot window.
	var container := SubViewportContainer.new()
	container.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.add_child(container)
	capture_viewport = SubViewport.new()
	capture_viewport.size = Vector2i(1440, 900)
	capture_viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	container.add_child(capture_viewport)
	game = load("res://scenes/main.tscn").instantiate()
	capture_viewport.add_child(game)
	await capture("title")
	game.start_new()
	await capture("introduction")
	game.resume_play()
	await capture("street")
	capture_viewport.size = Vector2i(2048, 780)
	await capture("opening-wide")
	capture_viewport.size = Vector2i(1440, 900)
	game.menu_camera.position = Vector3(16, 11, 16)
	game.menu_camera.look_at(Vector3(0, 6, -2))
	game.menu_camera.make_current()
	await capture("residential-block")
	game.menu_camera.position = Vector3(12, 4, 8)
	game.menu_camera.look_at(Vector3(8, 1.5, 14))
	await capture("bus-stop")
	game.menu_camera.position = Vector3(10, 4, 7)
	game.menu_camera.look_at(Vector3(14.5, 0.7, -0.3))
	await capture("park-seating")
	game.menu_camera.position = Vector3(9, 3.2, 6)
	game.menu_camera.look_at(Vector3(7.6, 2.5, 2.4))
	await capture("block-number")
	game.menu_camera.position = Vector3(-3.7, 1.8, 13)
	game.menu_camera.look_at(Vector3(-5, 1.3, 15.5))
	await capture("uncle-tan")
	game.camera.make_current()
	game.player.position = game.chapter.tasks[0].at + Vector3(0, 0.1, -1.4)
	game.interact()
	await capture("neighbour")
	finish_dialogue()
	game.player.position = game.chapter.tasks[1].at + Vector3(0, 0.1, 1.4)
	game.interact()
	finish_dialogue()
	game.player.position = game.chapter.tasks[2].at + Vector3(0, 0.1, 1.4)
	game.interact()
	await capture("fitting-aerial")
	while game.mode == "fitting":
		await process_frame
	await capture("tuning")
	var dial = game.ui.overlay.find_child("AntennaTuner", true, false)
	dial.adjust(45)
	await create_timer(0.9).timeout
	game.finish_tuning()
	await create_timer(1.3).timeout
	await capture("taking-seats")
	while game.mode == "arrival":
		await process_frame
	await create_timer(2.0).timeout
	await capture("archive-video")
	game.set_broadcast_view("television")
	await capture("television-close")
	game.set_broadcast_view("community")
	await create_timer(24.0).timeout
	await capture("community-reactions")
	# Inspect the face/hand animation from within the same 3D set.
	game.watch_camera.position = Vector3(-0.8, 2.0, -1.7)
	game.watch_camera.look_at(Vector3(-2.8, 1.3, 0))
	await capture("neighbour-reaction-detail")
	game.watch_camera.position = Vector3(-0.2, 1.8, -2.0)
	game.watch_camera.look_at(Vector3(-2.35, 1.15, -2.7))
	await capture("sparky-seated-detail")
	game.finish_archive()
	await capture("announcement")
	finish_dialogue()
	await capture("closing-choices")
	game.ask_reflection("homes")
	await capture("closing-homes")
	finish_dialogue()
	game.finish_reflection()
	await capture("closing-thanks")
	finish_dialogue()
	await capture("complete")
	game.show_journal()
	await capture("journal")
	for spread in 3:
		game.ui.turn_page(1)
		await capture("journal-%d" % (spread + 2))
	game.queue_free()
	await process_frame
	quit()
