extends Control
## Relative gestures work anywhere on the view, without grabbing the antenna.
signal adjusted(value: float, strength: float, clear: bool)
signal signal_locked
signal settled
var value := 20.0
var locked := false
var settling := 0.0
var celebration := 0.0
var celebration_duration := 1.1
var pointer := -1
var dragging := false
var hint: Label
var progress: ProgressBar

func _ready() -> void:
	focus_mode = Control.FOCUS_ALL
	mouse_default_cursor_shape = Control.CURSOR_DRAG
	gui_input.connect(handle_input)

func adjust(amount: float) -> void:
	if locked: return
	value = clampf(value + amount, 0.0, 100.0)
	var distance := absf(value - 65.0)
	var clear := distance <= 10.0
	if not clear: settling = 0.0
	adjusted.emit(value, clampf(100.0 - distance * 1.8, 0.0, 100.0), clear)
	if hint:
		hint.text = 'Picture found — let it settle…' if clear else ('Getting clearer… a little more.' if distance < 25 else 'Move the antenna until the snow clears.')

func handle_input(event: InputEvent) -> void:
	if event is InputEventScreenTouch:
		if event.pressed and pointer == -1:
			pointer = event.index
		elif not event.pressed and pointer == event.index:
			pointer = -1
	elif event is InputEventScreenDrag and event.index == pointer:
		adjust(event.relative.x / maxf(size.x, 1.0) * 150.0)
	elif event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and event.device != InputEvent.DEVICE_ID_EMULATION:
		dragging = event.pressed
	elif event is InputEventMouseMotion and dragging and event.device != InputEvent.DEVICE_ID_EMULATION:
		if event.button_mask & MOUSE_BUTTON_MASK_LEFT:
			adjust(event.relative.x / maxf(size.x, 1.0) * 150.0)
		else:
			dragging = false
	elif event is InputEventKey and event.keycode in [KEY_LEFT, KEY_RIGHT]:
		if event.pressed: adjust(-5.0 if event.keycode == KEY_LEFT else 5.0)
		accept_event()

func _process(delta: float) -> void:
	if locked:
		celebration += delta
		if celebration >= celebration_duration:
			set_process(false)
			settled.emit()
		return
	if absf(value - 65.0) <= 10.0:
		settling += delta
		if settling >= 0.8:
			locked = true
			value = 65.0
			adjusted.emit(value, 100.0, true)
			hint.text = 'Uncle Tan: “There, that’s it!”'
			signal_locked.emit()
	if progress: progress.value = settling / 0.8 * 100.0
