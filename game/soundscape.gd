extends Node3D
## Original synthesized ambience, kept below the historical recording.
var enabled := true
var mode := "menu"
var player: CharacterBody3D
var fan: AudioStreamPlayer3D
var street: AudioStreamPlayer3D
var murmur: AudioStreamPlayer3D
var footsteps: AudioStreamPlayer3D
var click: AudioStreamPlayer3D
var previous_position := Vector3.ZERO
var stride := 0.0
var mix_tween: Tween
var frozen := false

func setup(target: CharacterBody3D) -> void:
	player = target
	previous_position = player.global_position
	fan = make_source("ceiling-fan", Vector3(0, 3.5, -1.3), true, 22)
	street = make_source("street", Vector3(0, 1.0, 7.5), true, 50)
	murmur = make_source("quiet-murmur", Vector3(0, 1.3, -2), true, 20)
	footsteps = make_source("footstep", player.position, false, 12)
	footsteps.volume_db = -20
	click = make_source("aerial-click", Vector3(0, 2.5, -5.7), false, 12)
	click.volume_db = -15
	set_scene_mode("menu")

func make_source(file: String, at: Vector3, looping: bool, radius: float) -> AudioStreamPlayer3D:
	var source := AudioStreamPlayer3D.new()
	var stream := load("res://assets/audio/" + file + ".wav").duplicate() as AudioStreamWAV
	if looping:
		stream.loop_mode = AudioStreamWAV.LOOP_FORWARD
		stream.loop_end = int(stream.get_length() * stream.mix_rate)
	source.stream = stream
	source.position = at
	source.max_distance = radius
	source.unit_size = 5
	source.volume_db = -80
	add_child(source)
	if looping:
		source.play()
	return source

func set_enabled(value: bool) -> void:
	enabled = value
	set_scene_mode(mode)

func set_scene_mode(value: String) -> void:
	mode = value
	if not is_instance_valid(fan):
		return
	if mix_tween:
		mix_tween.kill()
	var audible := enabled and mode not in ["menu", "intro", "complete"] and not OS.get_cmdline_user_args().has("--test")
	var watching := mode in ["video", "reflection", "dialogue", "returning"]
	mix_tween = create_tween().set_parallel(true)
	mix_tween.tween_property(fan, "volume_db", (-32.0 if watching else -24.0) if audible else -80.0, 1.3)
	mix_tween.tween_property(street, "volume_db", (-34.0 if watching else -23.0) if audible else -80.0, 1.3)
	mix_tween.tween_property(murmur, "volume_db", -21.0 if audible and mode in ["play", "puzzle", "arrival", "fitting"] else -80.0, 1.3)
	set_frozen(mode in ["pause", "journal"])

func set_frozen(value: bool) -> void:
	frozen = value
	for source in [fan, street, murmur, footsteps]:
		if is_instance_valid(source):
			source.stream_paused = value

func aerial_click() -> void:
	if enabled and not OS.get_cmdline_user_args().has("--test"):
		click.play()

func _process(_delta: float) -> void:
	if not is_instance_valid(player):
		return
	var travelled := player.global_position.distance_to(previous_position)
	previous_position = player.global_position
	footsteps.global_position = player.global_position
	if travelled > 1.0 or player.seated or frozen or not enabled or mode not in ["play", "video", "arrival", "fitting", "returning"]:
		stride = 0
		return
	stride += travelled
	if stride > 0.7:
		stride = 0
		if not OS.get_cmdline_user_args().has("--test"):
			footsteps.pitch_scale = randf_range(0.94, 1.06)
			footsteps.play()
