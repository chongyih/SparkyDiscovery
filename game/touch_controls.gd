extends CanvasLayer
## Touch controls for phone browsers: a floating thumbstick on the left half,
## drag-to-look on the right, and round action buttons. Menus use normal taps.

const PAPER := Color("f5efdf")
const INK := Color("203e42")
const GOLD := Color("e3ae54")
const MOVE_ACTIONS := ["move_left", "move_right", "move_up", "move_down"]
const STICK_RADIUS := 100.0
const KNOB_RADIUS := 44.0
const INTERACT_RADIUS := 78.0
const MENU_RADIUS := 42.0
## Fraction of the screen width that starts the thumbstick instead of looking.
const STICK_ZONE := 0.45
const LOOK_SPEED := 0.005
const DOUBLE_TAP_TIME := 0.35

var game: Node3D
var controls := Node2D.new()
var touch_enabled := false
var was_walking := false
var look_finger := -1
var look_start := Vector2.ZERO
var look_last := Vector2.ZERO
var look_start_time := 0.0
var last_tap_time := -10.0
var last_tap_position := Vector2.ZERO
var stick_finger := -1
var stick_center := Vector2.ZERO
var stick_knob := Vector2.ZERO
var interact_button: TouchScreenButton
var pause_button: TouchScreenButton
var journal_button: TouchScreenButton
var buttons: Array[TouchScreenButton] = []
var font: Font = ThemeDB.fallback_font

static func available() -> bool:
	return DisplayServer.is_touchscreen_available() or OS.has_feature("web_android") or OS.has_feature("web_ios") or OS.get_cmdline_user_args().has("--touch")

func _ready() -> void:
	layer = 20
	touch_enabled = available()
	add_child(controls)
	controls.visible = false
	controls.draw.connect(draw_controls)
	if not touch_enabled:
		return
	interact_button = add_button("interact", INTERACT_RADIUS)
	pause_button = add_button("pause_game", MENU_RADIUS)
	journal_button = add_button("journal", MENU_RADIUS)

## TouchScreenButton handles multi-touch and emits the action; drawing happens in draw_controls.
func add_button(action: String, radius: float) -> TouchScreenButton:
	var button := TouchScreenButton.new()
	button.action = action
	button.shape_centered = false
	var shape := CircleShape2D.new()
	shape.radius = radius
	button.shape = shape
	button.set_meta("radius", radius)
	controls.add_child(button)
	buttons.append(button)
	return button

func stick_rest() -> Vector2:
	# Above the chapter progress strip, clear of the bottom-left corner.
	return Vector2(190, get_viewport().get_visible_rect().size.y - 240)

func _process(_delta: float) -> void:
	if not touch_enabled:
		return
	var walking: bool = game.player.enabled
	if was_walking and not walking:
		release_controls()
	was_walking = walking
	controls.visible = walking
	if not walking:
		return
	var size := get_viewport().get_visible_rect().size
	var in_play: bool = game.mode == "play"
	interact_button.visible = in_play
	pause_button.visible = in_play
	journal_button.visible = in_play
	interact_button.position = Vector2(size.x - 190, size.y - 240)
	pause_button.position = Vector2(size.x - 28 - MENU_RADIUS, 24 + MENU_RADIUS)
	journal_button.position = pause_button.position - Vector2(MENU_RADIUS * 2 + 14, 0)
	if stick_finger == -1:
		stick_center = stick_rest()
	controls.queue_redraw()

func release_controls() -> void:
	look_finger = -1
	stick_finger = -1
	stick_knob = Vector2.ZERO
	for action in MOVE_ACTIONS:
		Input.action_release(action)

func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		release_controls()

func on_button(point: Vector2) -> bool:
	for button in buttons:
		if button.is_visible_in_tree() and point.distance_to(button.position) <= button.get_meta("radius"):
			return true
	return false

func _unhandled_input(event: InputEvent) -> void:
	if not touch_enabled or not game.player.enabled:
		return
	if event is InputEventScreenTouch:
		if event.pressed:
			# TouchScreenButton emits actions but does not consume the original touch.
			if on_button(event.position):
				return
			if stick_finger == -1 and event.position.x < get_viewport().get_visible_rect().size.x * STICK_ZONE:
				stick_finger = event.index
				stick_center = event.position
				stick_knob = Vector2.ZERO
				get_viewport().set_input_as_handled()
			elif look_finger == -1:
				look_finger = event.index
				look_start = event.position
				look_last = event.position
				look_start_time = now()
		elif event.index == stick_finger:
			stick_finger = -1
			stick_knob = Vector2.ZERO
			apply_stick()
		elif event.index == look_finger:
			look_finger = -1
			check_double_tap(event.position)
	elif event is InputEventScreenDrag:
		if event.index == stick_finger:
			var offset: Vector2 = event.position - stick_center
			# Drag the base along behind the thumb rather than capping the reach.
			if offset.length() > STICK_RADIUS:
				stick_center += offset.normalized() * (offset.length() - STICK_RADIUS)
				offset = offset.limit_length(STICK_RADIUS)
			stick_knob = offset
			apply_stick()
			get_viewport().set_input_as_handled()
		elif event.index == look_finger:
			# Web builds measure `relative` against whichever finger last used the same event slot
			# (godot platform/web touch_callback), so with the stick held it can jump by the
			# distance between thumbs. Track this finger's own previous position instead.
			var moved: Vector2 = event.position - look_last
			look_last = event.position
			game.follow_camera.yaw -= moved.x * LOOK_SPEED
			game.follow_camera.pitch = clampf(game.follow_camera.pitch - moved.y * LOOK_SPEED, -0.85, 0.22)
			get_viewport().set_input_as_handled()

## Analogue strengths let a small push walk slowly; get_vector applies the dead zone.
func apply_stick() -> void:
	var axis := stick_knob / STICK_RADIUS
	var strengths := {
		"move_left": maxf(-axis.x, 0), "move_right": maxf(axis.x, 0),
		"move_up": maxf(-axis.y, 0), "move_down": maxf(axis.y, 0),
	}
	for action in strengths:
		if strengths[action] > 0.0:
			Input.action_press(action, strengths[action])
		else:
			Input.action_release(action)

func now() -> float:
	return Time.get_ticks_msec() / 1000.0

## A quick double tap on the look side centres the camera behind Sparky.
func check_double_tap(point: Vector2) -> void:
	if now() - look_start_time > 0.25 or point.distance_to(look_start) > 24:
		return
	if now() - last_tap_time < DOUBLE_TAP_TIME and point.distance_to(last_tap_position) < 90:
		game.follow_camera.recentre()
		last_tap_time = -10.0
		return
	last_tap_time = now()
	last_tap_position = point

func draw_controls() -> void:
	var active := stick_finger != -1
	controls.draw_circle(stick_center, STICK_RADIUS, Color(INK, 0.28 if active else 0.16))
	controls.draw_arc(stick_center, STICK_RADIUS, 0, TAU, 64, Color(PAPER, 0.75 if active else 0.4), 3, true)
	controls.draw_circle(stick_center + stick_knob, KNOB_RADIUS, Color(PAPER, 0.92 if active else 0.55))
	controls.draw_arc(stick_center + stick_knob, KNOB_RADIUS, 0, TAU, 48, Color(INK, 0.35), 2, true)
	if interact_button.visible:
		draw_interact()
	if pause_button.visible:
		draw_menu_button(pause_button, false)
		draw_menu_button(journal_button, true)

func draw_interact() -> void:
	var verb: String = game.interact_verb
	var center := interact_button.position
	var radius := INTERACT_RADIUS * (0.92 if interact_button.is_pressed() else 1.0)
	if verb.is_empty():
		controls.draw_circle(center, radius, Color(INK, 0.3))
		controls.draw_arc(center, radius, 0, TAU, 64, Color(PAPER, 0.35), 3, true)
		draw_centered("Interact", center, 22, Color(PAPER, 0.55))
		return
	# A slow pulse draws the eye when something nearby can be used.
	var pulse := fmod(now(), 1.4) / 1.4
	controls.draw_arc(center, radius + 6 + 22 * pulse, 0, TAU, 64, Color(GOLD, 0.7 * (1.0 - pulse)), 4, true)
	controls.draw_circle(center, radius, GOLD)
	controls.draw_arc(center, radius, 0, TAU, 64, Color(PAPER, 0.9), 3, true)
	draw_centered(verb, center, 26, INK)

func draw_menu_button(button: TouchScreenButton, journal: bool) -> void:
	var center := button.position
	controls.draw_circle(center, MENU_RADIUS * (0.92 if button.is_pressed() else 1.0), Color(PAPER, 0.94))
	controls.draw_arc(center, MENU_RADIUS, 0, TAU, 48, Color(INK, 0.25), 2, true)
	if journal:
		# An open book: two pages meeting at the spine.
		for side in [-1, 1]:
			var page := PackedVector2Array([
				center + Vector2(0, -10), center + Vector2(17 * side, -14),
				center + Vector2(17 * side, 12), center + Vector2(0, 16),
			])
			controls.draw_colored_polygon(page, INK)
			controls.draw_line(center + Vector2(5 * side, -4), center + Vector2(13 * side, -6), PAPER, 2)
			controls.draw_line(center + Vector2(5 * side, 3), center + Vector2(13 * side, 1), PAPER, 2)
	else:
		for x in [-8, 8]:
			controls.draw_rect(Rect2(center + Vector2(x - 4, -14), Vector2(8, 28)), INK)

func draw_centered(text: String, center: Vector2, size: int, color: Color) -> void:
	var width := font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x
	var baseline := center.y + (font.get_ascent(size) - font.get_descent(size)) / 2.0
	controls.draw_string(font, Vector2(center.x - width / 2.0, baseline), text, HORIZONTAL_ALIGNMENT_LEFT, -1, size, color)
