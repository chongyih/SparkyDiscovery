extends SceneTree
## Focused desktop and phone-aspect screenshots of the interactive antenna.
func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	var viewport := SubViewport.new()
	viewport.size = Vector2i(1440, 900)
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(viewport)
	var game = load("res://scenes/main.tscn").instantiate()
	viewport.add_child(game)
	await process_frame
	game.checkpoint = 2
	game.continue_saved()
	game.player.position = Vector3(0, 0.1, -4.3)
	game.aerial_fitted = true
	game.world.tv_aerial.visible = true
	game.show_tuning()
	await create_timer(1.2).timeout
	viewport.get_texture().get_image().save_png("res://artifacts/tuning.png")
	# Canvas stretch maps a landscape phone to a wider logical viewport.
	viewport.size = Vector2i(1950, 900)
	await create_timer(0.3).timeout
	viewport.get_texture().get_image().save_png("res://artifacts/tuning-mobile.png")
	var tuner = game.ui.overlay.find_child("AntennaTuner", true, false)
	tuner.adjust(45)
	await create_timer(0.9).timeout
	viewport.get_texture().get_image().save_png("res://artifacts/tuning-locked.png")
	game.resume_play()
	await create_timer(1.3).timeout
	if game.mode != "play":
		push_error("Cancelled tuning still started the broadcast")
		quit(1)
		return
	print("PASS: Leaving tuning cancels the pending transition")
	viewport.queue_free()
	await process_frame
	quit()
