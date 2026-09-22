extends CanvasLayer
## Touch movement and orbit controls for phone browsers. Menus use normal taps.

var game: Node3D
var controls := Node2D.new()
var look_finger := -1
var was_walking := false
var touch_enabled := false
var buttons: Array[TouchScreenButton] = []
const MOVE_ACTIONS := ["move_left", "move_right", "move_up", "move_down"]

static func available() -> bool:
	return DisplayServer.is_touchscreen_available() or OS.has_feature("web_android") or OS.has_feature("web_ios") or OS.get_cmdline_user_args().has("--touch")

func _ready() -> void:
	layer = 20
	touch_enabled = available()
	add_child(controls)
	controls.visible = false
	if not touch_enabled:
		return
	add_button("move_up", "↑", Vector2(130, -380))
	add_button("move_left", "←", Vector2(35, -285))
	add_button("move_down", "↓", Vector2(130, -190))
	add_button("move_right", "→", Vector2(225, -285))
	add_button("interact", "Interact", Vector2(-155, -195))
	add_button("pause_game", "Pause", Vector2(-155, -300))
	add_button("journal", "Journal", Vector2(-260, -195))

func add_button(action: String, caption: String, offset: Vector2) -> void:
	var button := TouchScreenButton.new()
	button.action = action
	button.set_meta("offset", offset)
	var gradient := Gradient.new()
	gradient.set_color(0, Color(0.13, 0.24, 0.25, 0.82))
	gradient.set_color(1, Color(0.13, 0.24, 0.25, 0.82))
	var texture := GradientTexture2D.new()
	texture.gradient = gradient
	texture.width = 90
	texture.height = 90
	button.texture_normal = texture
	var shape := RectangleShape2D.new()
	shape.size = Vector2(90, 90)
	button.shape = shape
	var text := Label.new()
	text.text = caption
	text.size = Vector2(90, 90)
	text.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	text.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	text.add_theme_font_size_override("font_size", 21)
	text.mouse_filter = Control.MOUSE_FILTER_IGNORE
	button.add_child(text)
	controls.add_child(button)
	buttons.append(button)

func _process(_delta: float) -> void:
	if not touch_enabled:
		return
	var walking: bool = game.player.enabled
	if was_walking and not walking:
		release_controls()
	was_walking = walking
	controls.visible = walking
	var size := get_viewport().get_visible_rect().size
	for button in buttons:
		var offset: Vector2 = button.get_meta("offset")
		button.position = Vector2(size.x + offset.x if offset.x < 0 else offset.x, size.y + offset.y)

func release_controls() -> void:
	look_finger = -1
	for action in MOVE_ACTIONS:
		Input.action_release(action)

func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		release_controls()

func _unhandled_input(event: InputEvent) -> void:
	if not touch_enabled or not game.player.enabled:
		return
	if event is InputEventScreenTouch:
		# TouchScreenButton emits actions but does not consume the original touch.
		# A movement finger must not also become the camera's orbit finger.
		if event.pressed:
			for button in buttons:
				if Rect2(button.position, Vector2(90, 90)).has_point(event.position):
					return
		if event.pressed and look_finger == -1:
			look_finger = event.index
		elif not event.pressed and event.index == look_finger:
			look_finger = -1
	elif event is InputEventScreenDrag and event.index == look_finger:
		game.follow_camera.yaw -= event.relative.x * 0.005
		game.follow_camera.pitch = clampf(game.follow_camera.pitch - event.relative.y * 0.005, -0.85, 0.22)
		get_viewport().set_input_as_handled()
