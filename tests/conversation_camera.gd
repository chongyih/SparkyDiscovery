extends SceneTree
var game: Node
var failures := 0
func _initialize() -> void:
	call_deferred("run")
func check(value: bool, message: String) -> void:
	print(("PASS: " if value else "FAIL: ") + message)
	if not value: failures += 1
func capture(file_name: String) -> void:
	await create_timer(0.3).timeout
	RenderingServer.force_draw(false)
	root.get_texture().get_image().save_png("res://artifacts/" + file_name + ".png")
func inspect(seated: bool) -> void:
	var uncle: Node3D = game.world.community.residents[5].root if seated else game.world.neighbour_visual
	for actor in [game.player.visual, uncle]:
		var partner: Node3D = uncle if actor == game.player.visual else game.player.visual
		var toward_partner: Vector3 = partner.global_position - actor.global_position
		toward_partner.y = 0
		if seated:
			var seat: Transform3D = game.world.community.sparky_seat() if actor == game.player.visual else game.world.community.seat_transform(0, 0.8)
			check(actor.global_basis.z.normalized().dot(seat.basis.z) > 0.99, "Seated body stays aligned with the bench")
		else:
			check(actor.global_basis.z.normalized().dot(toward_partner.normalized()) > 0.99, "Characters face each other")
		var head: Vector3 = actor.global_position + Vector3(0, 1.5, 0)
		var ray := PhysicsRayQueryParameters3D.create(game.watch_camera.global_position, head)
		ray.exclude = [game.player.get_rid()]
		check(game.get_world_3d().direct_space_state.intersect_ray(ray).is_empty(), "Scenery does not block the face")
		var screen: Vector2 = game.watch_camera.unproject_position(head) / root.get_visible_rect().size
		check(screen.x > 0.08 and screen.x < 0.92 and screen.y > 0.03 and screen.y < 0.5, "Both heads fit above the dialogue")
func run() -> void:
	root.size = Vector2i(1440, 900)
	game = load("res://scenes/main.tscn").instantiate()
	root.add_child(game)
	await process_frame
	for approach in [Vector3(0, 0.1, -1.4), Vector3(0, 0.1, 1.4), Vector3(1.4, 0.1, 0), Vector3(-1.4, 0.1, 0)]:
		game.start_new()
		game.resume_play()
		game.player.position = game.chapter.tasks[0].at + approach
		game.interact()
		await process_frame
		await process_frame
		check(game.watch_tween.is_running(), "Conversation camera eases in")
		var beginning: Transform3D = game.watch_camera.global_transform
		await create_timer(0.35).timeout
		check(not game.watch_camera.global_transform.is_equal_approx(beginning) and game.watch_tween.is_running(), "Camera moves through an intermediate view")
		await create_timer(0.4).timeout
		check(not game.watch_tween.is_running(), "Camera settles after the transition")
		inspect(false)
		if OS.get_cmdline_user_args().has("--capture"):
			await capture("conversation-opening-%d" % int(approach.x * 10 + approach.z))
	game.start_new()
	game.resume_play()
	game.task_index = 2
	game.checkpoint = 2
	game.start_broadcast()
	if OS.get_cmdline_user_args().has("--capture"):
		await create_timer(1.2).timeout
		await capture("tv-toolbar-simple")
	game.finish_archive()
	await create_timer(0.8).timeout
	inspect(true)
	check(game.player.global_position.is_equal_approx(game.world.community.sparky_seat().origin), "Conversation preserves backrest clearance")
	if OS.get_cmdline_user_args().has("--capture"):
		await capture("conversation-closing")
	game.frame_conversation()
	check(game.watch_tween.is_running(), "Exit test interrupts an active transition")
	game.show_menu()
	await process_frame
	check(game.menu_camera.current and not game.watch_tween.is_running(), "Leaving cancels the transition without reclaiming the camera")
	check(game.conversation_poses.is_empty(), "Leaving a conversation restores actor poses")
	game.queue_free()
	await process_frame
	quit(1 if failures else 0)
