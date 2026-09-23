extends Node
## Short, interruptible sequences on authored paths through the open aisles.
## Just behind the community camera on the aisle from the street.
const UNCLE_ENTRY := Vector3(0.2, 0, 6.0)
var game: Node
var tweens: Array[Tween] = []
var serial := 0
var pending := 0
var fitting_aerial: Node3D

func cancel() -> void:
	serial += 1
	for tween in tweens:
		if tween and tween.is_valid():
			tween.kill()
	tweens.clear()
	if is_instance_valid(fitting_aerial):
		fitting_aerial.queue_free()
	fitting_aerial = null
	game.player.scripted_motion = false
	game.world.neighbour_walking = false

func sequence() -> Tween:
	var tween := create_tween()
	tweens.append(tween)
	return tween

func walk(tween: Tween, actor: Node3D, facing: Node3D, points: Array, speed: float) -> void:
	var previous := actor.global_position
	for point in points:
		var destination: Vector3 = point
		var direction := destination - previous
		var duration := maxf(0.08, direction.length() / speed)
		var yaw := atan2(direction.x, direction.z)
		tween.tween_callback(func():
			facing.rotation.y = lerp_angle(facing.rotation.y, yaw, 1.0)
		)
		tween.tween_property(actor, "global_position", destination, duration)
		previous = destination

func fit_aerial() -> void:
	cancel()
	var token := serial
	game.set_mode("fitting")
	game.world.set_active(-1)
	game.ui.show_sequence("Up it goes", "Sparky fixes the spare antenna on top of the TV set.", func(): finish_fitting(token), "Skip")
	game.frame_watch(Vector3(3.2, 2.8, -1.6), Vector3(0, 1.8, -5.1), 52)
	game.player.scripted_motion = true
	game.player.play_animation("Walk")
	var tween := sequence()
	var points: Array = []
	if game.player.position.z < -5.0:
		var side := -2.0 if game.player.position.x < 0 else 2.0
		points.append(Vector3(side, 0.1, game.player.position.z))
		points.append(Vector3(side, 0.1, -4.1))
	points.append(Vector3(0, 0.1, -4.1))
	walk(tween, game.player, game.player.visual, points, 2.2)
	tween.tween_property(game.player.visual, "rotation:y", PI, 0.3)
	tween.tween_callback(func():
		if token != serial: return
		game.player.prepare_reach()
		fitting_aerial = game.carried_aerial.duplicate()
		game.world.add_child(fitting_aerial)
		fitting_aerial.global_transform = game.carried_aerial.global_transform
		fitting_aerial.visible = true
		game.carried_aerial.visible = false
	)
	tween.tween_property(game.player, "reach_blend", 1.0, 0.6)
	tween.tween_callback(func():
		if token != serial: return
		var fitting := sequence()
		fitting.tween_property(fitting_aerial, "global_position", Vector3(0, 3.2, -4.8), 0.6).set_trans(Tween.TRANS_SINE)
		fitting.tween_property(fitting_aerial, "global_transform", game.world.tv_aerial.global_transform, 0.65).set_trans(Tween.TRANS_SINE)
		fitting.tween_callback(func(): finish_fitting(token))
	)

func finish_fitting(token: int) -> void:
	if token != serial or game.mode != "fitting": return
	cancel()
	game.player.reach_blend = 0
	game.player.resume_idle()
	game.aerial_fitted = true
	game.world.tv_aerial.visible = true
	game.carried_aerial.visible = false
	game.soundscape.aerial_click()
	game.show_tuning()

func arrive() -> void:
	cancel()
	var token := serial
	pending = 2
	game.set_mode("arrival")
	game.play_voice_cue(load("res://assets/voice/come_sit.mp3"))
	game.ui.show_sequence("Come, come, sit!", "The neighbours shift up to make space. Sparky squeezes onto the bench.", finish_arrival, "Skip")
	game.frame_community()
	var seat: Transform3D = game.world.community.sparky_seat()
	var approach := seat.origin + seat.basis.z * 0.85
	approach.y = 0.1
	game.player.scripted_motion = true
	game.player.play_animation("Walk")
	var sparky := sequence()
	walk(sparky, game.player, game.player.visual, [Vector3(-0.3, 0.1, -3.7), approach], 1.9)
	sparky.tween_property(game.player.visual, "rotation:y", seat.basis.get_euler().y, 0.45)
	sparky.tween_callback(func():
		game.player.set_seated(true)
		game.player.sit_blend = 0
	)
	sparky.tween_property(game.player, "global_position", seat.origin, 0.9).set_trans(Tween.TRANS_SINE)
	sparky.parallel().tween_property(game.player, "sit_blend", 1.0, 0.9).set_trans(Tween.TRANS_SINE)
	sparky.tween_callback(func(): actor_ready(token))
	var uncle := sequence()
	var uncle_seat: Transform3D = game.world.community.seat_transform(0, 0.8)
	var uncle_approach := uncle_seat.origin + uncle_seat.basis.z * 0.85
	# The community shot faces away from the street, so the walk from the shops happened off
	# camera for about five seconds. Start him just outside the frame on the same route instead.
	game.world.stations[0].global_position = UNCLE_ENTRY
	game.world.neighbour_walking = true
	walk(uncle, game.world.stations[0], game.world.neighbour_visual, [Vector3(0.2, 0, 2.2), Vector3(0.2, 0, -4.6), uncle_approach], 3.0)
	uncle.tween_callback(func(): game.world.neighbour_walking = false)
	uncle.tween_property(game.world.neighbour_visual, "rotation:y", uncle_seat.basis.get_euler().y, 0.4)
	uncle.tween_property(game.world.stations[0], "position", uncle_seat.origin, 0.65).set_trans(Tween.TRANS_SINE)
	uncle.tween_callback(func():
		if token != serial: return
		game.world.stations[0].visible = false
		game.world.community.residents[5].root.visible = true
		actor_ready(token)
	)

func actor_ready(token: int) -> void:
	if token != serial or game.mode != "arrival": return
	pending -= 1
	if pending == 0:
		finish_arrival()

func finish_arrival() -> void:
	if game.mode != "arrival": return
	cancel()
	game.world.stations[0].visible = false
	game.start_broadcast()
