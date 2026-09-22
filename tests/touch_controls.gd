extends SceneTree
## Run with -- --test --touch to exercise real multi-touch input dispatch.
var failures := 0
var game: Node

func _initialize() -> void:
	call_deferred("run")

func check(condition: bool, description: String) -> void:
	print(("PASS: " if condition else "FAIL: ") + description)
	if not condition:
		failures += 1

func frames(count: int) -> void:
	for i in count:
		await physics_frame

func touch(index: int, position: Vector2, pressed: bool) -> void:
	var event := InputEventScreenTouch.new()
	event.index = index
	event.position = position
	event.pressed = pressed
	root.push_input(event, true)

func drag(index: int, position: Vector2, relative: Vector2) -> void:
	var event := InputEventScreenDrag.new()
	event.index = index
	event.position = position
	event.relative = relative
	root.push_input(event, true)

func run() -> void:
	game = load("res://scenes/main.tscn").instantiate()
	root.add_child(game)
	await frames(4)
	game.start_new()
	game.resume_play()
	await frames(4)
	var controls: Node
	for child in game.get_children():
		if child.get_script() == load("res://game/touch_controls.gd"):
			controls = child
	check(controls != null and controls.controls.visible, "Touch controls appear while walking")
	check(Input.mouse_mode == Input.MOUSE_MODE_VISIBLE, "Touch mode does not capture a mouse")
	var stick := Vector2(260, 600)
	var before: Vector3 = game.player.position
	touch(0, stick, true)
	drag(0, stick + Vector2(0, -40), Vector2(0, -40))
	await frames(2)
	var gentle := Input.get_action_strength("move_up")
	check(gentle > 0.2 and gentle < 0.6, "A short thumbstick push gives partial strength")
	drag(0, stick + Vector2(0, -300), Vector2(0, -260))
	await frames(30)
	check(is_equal_approx(Input.get_action_strength("move_up"), 1.0), "A full thumbstick push walks at full speed")
	check(controls.stick_center.distance_to(stick) > 100, "The thumbstick base follows a long drag")
	check(game.player.position.distance_to(before) > 0.5, "Thumbstick movement moves the player")
	var look := Vector2(1100, 450)
	touch(1, look, true)
	var yaw: float = game.follow_camera.yaw
	drag(1, look + Vector2(80, 0), Vector2(80, 0))
	await frames(2)
	check(game.follow_camera.yaw != yaw, "Second finger orbits while moving")
	check(Input.is_action_pressed("move_up"), "Looking does not interrupt the thumbstick")
	touch(1, look + Vector2(80, 0), false)
	touch(0, stick, false)
	await frames(2)
	check(not Input.is_action_pressed("move_up"), "Lifting the thumb stops movement")
	game.follow_camera.yaw = game.player.visual.rotation.y + 1.2
	for i in 2:
		touch(1, look, true)
		touch(1, look, false)
	await frames(2)
	check(is_equal_approx(game.follow_camera.yaw, game.player.visual.rotation.y - PI), "Double-tapping the look side centres the camera")
	touch(0, stick, true)
	drag(0, stick + Vector2(100, 0), Vector2(100, 0))
	game.pause_game()
	await frames(3)
	check(not controls.controls.visible, "Pause hides gameplay touch controls")
	check(not Input.is_action_pressed("move_right"), "Pause releases held movement")
	touch(0, stick, false)
	game.resume_play()
	await frames(3)
	check(game.interact_verb.is_empty(), "Interact is inactive away from the marker")
	game.player.position = game.chapter.tasks[0].at + Vector3(0, 0.1, 1.4)
	await frames(3)
	check(game.interact_verb == "Talk", "Interact names the nearby action")
	var journal: Vector2 = controls.journal_button.position
	touch(0, journal, true)
	touch(0, journal, false)
	await frames(3)
	check(game.mode == "journal", "The journal touch button opens the journal")
	game.close_journal()
	await frames(3)
	var interact: Vector2 = controls.interact_button.position
	touch(0, interact, true)
	touch(0, interact, false)
	await frames(3)
	check(game.mode == "dialogue", "Interact touch opens nearby dialogue")
	game.queue_free()
	await frames(3)
	quit(1 if failures else 0)
