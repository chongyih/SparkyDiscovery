extends TextureRect
## A photographic plush cutout with a small local paw motion; the face and body stay still.
var greeting_time := 0.0

func _ready() -> void:
	texture = load("res://assets/menu/sparky-plush.png")
	expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	var wave := ShaderMaterial.new()
	wave.shader = preload("res://game/launch_wave.gdshader")
	material = wave
	visibility_changed.connect(update_visibility)

func _process(delta: float) -> void:
	greeting_time = fmod(greeting_time + delta, 7.0)
	material.set_shader_parameter("greeting_time", greeting_time)

func update_visibility() -> void:
	set_process(is_visible_in_tree())
	if is_visible_in_tree():
		greeting_time = 0.0
