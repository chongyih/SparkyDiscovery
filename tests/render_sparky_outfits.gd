extends SceneTree
## Render the imported assets and carrying gait with the real game renderer.
var viewport: SubViewport

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	DirAccess.make_dir_recursive_absolute("res://artifacts")
	var container := SubViewportContainer.new()
	root.add_child(container)
	viewport = SubViewport.new()
	viewport.size = Vector2i(1440, 1000)
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	container.add_child(viewport)
	var studio = load("res://scenes/character_studio.tscn").instantiate()
	viewport.add_child(studio)
	for index in [1, 2]:
		studio.select_outfit(index)
		studio.play_clip("Idle")
		await capture("outfit-" + str(index))
	studio.wardrobe.set_rifle(true)
	studio.update_caption()
	await capture("outfit-rifle-idle")
	studio.play_clip("Walk")
	studio.player.seek(.34, true)
	studio.player.pause()
	await capture("outfit-rifle-walk")
	studio.angle = 1.3
	studio.update_camera()
	await capture("outfit-rifle-side")
	quit()

func capture(name: String) -> void:
	await create_timer(.5).timeout
	RenderingServer.force_draw(false)
	viewport.get_texture().get_image().save_png("res://artifacts/" + name + ".png")
	print("CAPTURE " + name)
	await process_frame
