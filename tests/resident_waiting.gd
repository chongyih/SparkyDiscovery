extends SceneTree
var failures := 0
func _initialize() -> void:
	call_deferred("run")
func check(value: bool, message: String) -> void:
	print(("PASS: " if value else "FAIL: ") + message)
	if not value: failures += 1
func run() -> void:
	var game = load("res://scenes/main.tscn").instantiate()
	root.add_child(game)
	await process_frame
	game.start_new()
	game.resume_play()
	var community = game.world.community
	community.set_process(false)
	community.update_waiting(2.5)
	for pair in community.WAITING_PAIRS:
		for member in 2:
			var person: Dictionary = community.residents[pair[member]]
			var partner: Node3D = community.residents[pair[1 - member]].root
			var local_partner: Vector3 = person.root.to_local(partner.global_position)
			check(signf(person.head.rotation.y) == signf(local_partner.x), "Neighbour looks toward their actual bench partner")
	var first = community.residents[0]
	var head: Vector3 = first.head.rotation
	var hand: Vector3 = first.arms[1].hand.position
	check(hand.y > 0.8, "Speaking neighbour makes a small hand gesture")
	check(absf(community.residents[2].arms[1].hand.position.y - hand.y) > 0.05, "Pairs do not move in unison")
	if OS.get_cmdline_user_args().has("--capture"):
		game.ui.hud.visible = false
		game.frame_community()
		await create_timer(1.2).timeout
		RenderingServer.force_draw(false)
		root.get_texture().get_image().save_png("res://artifacts/neighbours-waiting.png")
	community.set_broadcast(true)
	check(first.head.rotation.is_equal_approx(head), "Starting the broadcast preserves gaze for a smooth turn")
	check(first.arms[1].hand.position.is_equal_approx(hand), "Starting the broadcast preserves the hand pose")
	community.attention = 1.0
	community.update_reactions()
	check(is_zero_approx(first.head.rotation.y), "Neighbours turn toward the TV")
	check(first.arms[1].hand.position.is_equal_approx(Vector3(0.21, 0.72, 0.38)), "Conversation gesture settles back into the lap")
	community.reaction_paused = true
	var paused: Vector3 = first.head.rotation
	community._process(1.0)
	check(first.head.rotation.is_equal_approx(paused), "Pausing the footage freezes reactions")
	community.set_broadcast(false)
	community.update_waiting(7.0)
	check(absf(first.head.rotation.y) > 0.5, "Restart restores waiting conversations")
	game.queue_free()
	await process_frame
	quit(1 if failures else 0)
