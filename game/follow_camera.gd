extends Node3D
## Third-person orbit camera. The spring arm keeps the camera outside buildings.
var target: CharacterBody3D
var camera: Camera3D
var arm: SpringArm3D
var enabled := false
var yaw := 0.0
var pitch := -0.23
var distance := 5.5
const SENSITIVITY := 0.003

func _ready() -> void:
	arm = SpringArm3D.new()
	arm.spring_length = distance
	arm.margin = 0.2
	var shape := SphereShape3D.new()
	shape.radius = 0.18
	arm.shape = shape
	add_child(arm)
	camera = Camera3D.new()
	camera.fov = 65
	camera.near = 0.1
	camera.far = 180
	arm.add_child(camera)

func reset() -> void:
	yaw = 0
	pitch = -0.23
	distance = 5.5
	position = target.position + Vector3(0, 1.5, 0)
	rotation = Vector3(0, yaw, 0)
	arm.rotation.x = pitch
	arm.spring_length = distance

func _process(delta: float) -> void:
	if not target:
		return
	position = position.lerp(target.position + Vector3(0, 1.5, 0), 1.0 - exp(-14.0 * delta))
	rotation.y = yaw
	arm.rotation.x = pitch
	arm.spring_length = lerpf(arm.spring_length, distance, 1.0 - exp(-12.0 * delta))

func _unhandled_input(event: InputEvent) -> void:
	if not enabled:
		return
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		yaw -= event.relative.x * SENSITIVITY
		pitch = clampf(pitch - event.relative.y * SENSITIVITY, -0.85, 0.22)
		get_viewport().set_input_as_handled()
	elif event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP:
			distance = maxf(3.0, distance - 0.5)
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			distance = minf(8.0, distance + 0.5)
	elif event is InputEventKey and event.pressed and event.physical_keycode == KEY_R:
		yaw = target.visual.rotation.y - PI
		pitch = -0.23
