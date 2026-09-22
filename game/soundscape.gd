extends Node3D
## Field-recorded ambience (assets/audio/README.md). Dialogue and the broadcast play at about
## -18 LUFS; the beds together sit about 20 dB below that while walking, lower while listening.
const TREES := [Vector3(-16, 3.4, -3.5), Vector3(-16, 3.4, 1.5), Vector3(16, 3.4, -3.5), Vector3(16, 3.4, 1.5), Vector3(-21, 3.4, -2), Vector3(20, 3.4, -1), Vector3(-20, 3.4, 12.8), Vector3(20, 3.4, 12.8)]
const BIRDS := ["koel-long", "koel-short", "koel-long", "myna"]
## Web builds default to Web Audio samples, which decode a whole file to 32-bit PCM up front:
## the 130 s street bed alone needed a 50 MB buffer, and phone browsers ran out of memory.
## Long loops stream instead; short one-shots keep the low-latency default.
const LONG_LOOP_PLAYBACK := AudioServer.PLAYBACK_TYPE_STREAM
var enabled := true
var mode := "menu"
var player: CharacterBody3D
var fan: AudioStreamPlayer3D
var street: AudioStreamPlayer3D
var murmur: AudioStreamPlayer3D
var cicadas: Array[AudioStreamPlayer3D] = []
var bird: AudioStreamPlayer3D
var footsteps: AudioStreamPlayer3D
var click: AudioStreamPlayer3D
var tv_static: AudioStreamPlayer
var steps: Array[AudioStream] = []
var bird_calls: Array[AudioStream] = []
var previous_position := Vector3.ZERO
var stride := 0.0
var bird_wait := 8.0
var mix_tween: Tween
var static_tween: Tween
var frozen := false

func setup(target: CharacterBody3D) -> void:
	player = target
	previous_position = player.global_position
	fan = make_source("ceiling-fan", Vector3(0, 3.5, -1.3), true, 14)
	street = make_source("street", Vector3(0, 1.0, 9), true, 60)
	murmur = make_source("neighbours", Vector3(0, 1.3, -1), true, 22)
	# Two trees on opposite sides, offset in time, so the insects never pulse in unison.
	cicadas = [make_source("cicadas", TREES[0], true, 40), make_source("cicadas", TREES[7], true, 40)]
	cicadas[1].play(20.0)
	bird = make_source("koel-long", TREES[0], false, 45)
	bird.unit_size = 8
	for name in BIRDS:
		bird_calls.append(load("res://assets/audio/%s.ogg" % name))
	for i in range(1, 6):
		steps.append(load("res://assets/audio/footstep-%d.ogg" % i))
	footsteps = make_source("footstep-1", player.position, false, 12)
	footsteps.volume_db = -18
	click = make_source("aerial-click", Vector3(0, 2.5, -5.7), false, 12)
	click.volume_db = -14
	tv_static = AudioStreamPlayer.new()
	tv_static.stream = load("res://assets/audio/tv-static.ogg").duplicate()
	tv_static.stream.loop = true
	tv_static.playback_type = LONG_LOOP_PLAYBACK
	tv_static.volume_db = -80
	add_child(tv_static)
	set_scene_mode("menu")

func make_source(file: String, at: Vector3, looping: bool, radius: float) -> AudioStreamPlayer3D:
	var source := AudioStreamPlayer3D.new()
	var stream := load("res://assets/audio/" + file + ".ogg").duplicate() as AudioStreamOggVorbis
	stream.loop = looping
	source.stream = stream
	if looping:
		source.playback_type = LONG_LOOP_PLAYBACK
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

func audible() -> bool:
	return enabled and mode not in ["menu", "intro", "complete"] and not OS.get_cmdline_user_args().has("--test")

func watching() -> bool:
	return mode in ["video", "reflection", "dialogue", "returning"]

func set_scene_mode(value: String) -> void:
	mode = value
	if not is_instance_valid(fan):
		return
	if mix_tween:
		mix_tween.kill()
	var on := audible()
	var hushed := watching() or mode == "puzzle"
	mix_tween = create_tween().set_parallel(true)
	mix_tween.tween_property(fan, "volume_db", (-27.0 if hushed else -20.0) if on else -80.0, 1.3)
	mix_tween.tween_property(street, "volume_db", (-30.0 if hushed else -19.0) if on else -80.0, 1.3)
	# The neighbours fall quiet once the press conference begins.
	mix_tween.tween_property(murmur, "volume_db", (-26.0 if mode == "puzzle" else -21.0) if on and mode in ["play", "puzzle", "arrival", "fitting"] else -80.0, 1.3)
	for source in cicadas:
		mix_tween.tween_property(source, "volume_db", (-34.0 if hushed else -25.0) if on else -80.0, 1.3)
	if not on:
		bird.stop()
	if mode != "puzzle" and tv_static.playing:
		static_tween = create_tween()
		static_tween.tween_property(tv_static, "volume_db", -80.0, 0.25)
		static_tween.tween_callback(tv_static.stop)
	set_frozen(mode in ["pause", "journal"])

func set_frozen(value: bool) -> void:
	frozen = value
	for source in [fan, street, murmur, bird, footsteps] + cicadas:
		if is_instance_valid(source):
			source.stream_paused = value

func aerial_click() -> void:
	if enabled and not OS.get_cmdline_user_args().has("--test"):
		click.play()

## Snow on the untuned set: loudest far from the station, gone once the picture locks.
## Feedback for the puzzle rather than ambience, so the ambient toggle leaves it on.
func tune(_dial: float, strength: float, clear: bool) -> void:
	if OS.get_cmdline_user_args().has("--test"):
		return
	if static_tween:
		static_tween.kill()
	if not tv_static.playing:
		tv_static.play()
	tv_static.volume_db = -80.0 if clear else linear_to_db(lerpf(0.12, 1.0, 1.0 - strength / 100.0)) - 5.0

## An occasional koel or myna from a random tree, never over the broadcast.
func call_bird(delta: float) -> void:
	if frozen or not audible() or watching():
		return
	bird_wait -= delta
	if bird_wait > 0 or bird.playing:
		return
	bird_wait = randf_range(14.0, 32.0)
	bird.stream = bird_calls.pick_random()
	bird.position = TREES.pick_random()
	bird.volume_db = randf_range(-11.0, -6.0)
	bird.pitch_scale = randf_range(0.97, 1.03)
	bird.play()

func _process(delta: float) -> void:
	if not is_instance_valid(player):
		return
	call_bird(delta)
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
			footsteps.stream = steps.pick_random()
			footsteps.pitch_scale = randf_range(0.94, 1.06)
			footsteps.play()
