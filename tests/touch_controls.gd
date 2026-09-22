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
	var up: Vector2 = controls.buttons[0].position + Vector2(45, 45)
	var before: Vector3 = game.player.position
	touch(0, up, true)
	await frames(30)
	check(Input.is_action_pressed("move_up"), "A held touch presses the movement action")
	check(game.player.position.distance_to(before) > 0.5, "Touch movement moves the player")
	var look := Vector2(700, 450)
	touch(1, look, true)
	var yaw: float = game.follow_camera.yaw
	var drag := InputEventScreenDrag.new()
	drag.index = 1
	drag.position = look + Vector2(80, 0)
	drag.relative = Vector2(80, 0)
	root.push_input(drag, true)
	await frames(2)
	check(game.follow_camera.yaw != yaw, "Second finger orbits while movement is held")
	touch(1, drag.position, false)
	game.pause_game()
	await frames(3)
	check(not controls.controls.visible, "Pause hides gameplay touch controls")
	check(not Input.is_action_pressed("move_up"), "Pause releases held movement")
	touch(0, up, false)
	game.resume_play()
	await frames(3)
	game.player.position = game.chapter.tasks[0].at + Vector3(0, 0.1, 1.4)
	var interact: Vector2 = controls.buttons[4].position + Vector2(45, 45)
	touch(0, interact, true)
	touch(0, interact, false)
	await frames(3)
	check(game.mode == "dialogue", "Interact touch opens nearby dialogue")
	game.queue_free()
	await frames(3)
	quit(1 if failures else 0)
