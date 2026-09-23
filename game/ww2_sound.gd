extends Node
## Independent chapter mix: mute/pause affects every layer, with a private siren filter bus removed on exit.
var enabled := true
var suspended := false
var indoors := false
var phase := 0.0
var stride := 0.0
var previous := Vector3.ZERO
var player: CharacterBody3D
var aircraft: AudioStreamPlayer
var footsteps: AudioStreamPlayer
var detail: AudioStreamPlayer
var hush: AudioStreamPlayer
var siren: AudioStreamPlayer
var siren_filter: AudioEffectLowPassFilter
var siren_bus: StringName
var siren_level := -20.0
var siren_target := -20.0
var siren_duck := 0.0
var siren_fade := -1.0
var foot_index := 0
var steps: Array[AudioStream] = []

func source(path: String, volume: float) -> AudioStreamPlayer:
	var audio := AudioStreamPlayer.new()
	audio.stream = load(path)
	audio.volume_db = volume
	add_child(audio)
	return audio

func setup(target: CharacterBody3D) -> void:
	player = target
	previous = target.position
	aircraft = source("res://assets/audio/ww2-aircraft.wav", -30)
	footsteps = source("res://assets/audio/footstep-1.ogg", -22)
	detail = source("res://assets/audio/ww2-shutter.wav", -21)
	hush = source("res://assets/audio/neighbours.ogg", -41)
	hush.stream = hush.stream.duplicate()
	hush.stream.loop = true
	siren = source("res://assets/audio/ww2-siren-recorded-loop.wav", -20)
	siren.stream = siren.stream.duplicate()
	siren.stream.loop_mode = AudioStreamWAV.LOOP_FORWARD
	siren.stream.loop_begin = 0
	siren.stream.loop_end = int(siren.stream.get_length() * siren.stream.mix_rate)
	siren_bus = StringName("WartimeSiren_%d" % get_instance_id())
	AudioServer.add_bus()
	var bus := AudioServer.bus_count - 1
	AudioServer.set_bus_name(bus, siren_bus)
	siren_filter = AudioEffectLowPassFilter.new()
	siren_filter.cutoff_hz = 12000
	AudioServer.add_bus_effect(bus, siren_filter)
	siren.bus = siren_bus
	for i in range(1, 6): steps.append(load("res://assets/audio/footstep-%d.ogg" % i))

func update(delta: float, mode: String) -> void:
	if suspended: return
	siren_duck = maxf(0, siren_duck - delta)
	var level_target := -40.0 if siren_duck > 0 else siren_target
	if siren_fade >= 0:
		siren_fade += delta
		level_target = lerpf(-39, -80, clampf(siren_fade / 6.5, 0, 1))
		if siren_fade >= 6.5: siren.stop()
	siren_level = lerpf(siren_level, level_target, 1 - exp(-delta * 5))
	siren.volume_db = siren_level if enabled else -80
	siren_filter.cutoff_hz = lerpf(siren_filter.cutoff_hz, 550.0 if indoors else 12000.0, 1 - exp(-delta * 4))
	phase += delta
	if enabled and not indoors and mode == "play" and phase > 11 and not aircraft.playing:
		aircraft.play()
		phase = -8
	var distance := player.position.distance_to(previous)
	previous = player.position
	if mode != "play":
		stride = 0
		return
	if distance < 0.6: stride += distance
	if stride > 0.85 and enabled:
		stride = 0
		footsteps.stream = steps[foot_index % steps.size()]
		foot_index += 1
		footsteps.play()

func effect(name: String) -> void:
	detail.stream = load("res://assets/audio/ww2-%s.wav" % name)
	if enabled: detail.play()

func enter_shelter() -> void:
	indoors = true
	siren_target = -39
	aircraft.stop()
	footsteps.stop()
	if enabled: hush.play()
	effect("door")

func pause_audio(value: bool) -> void:
	suspended = value
	for audio in [aircraft, footsteps, detail, hush, siren]: audio.stream_paused = value

func mute(value: bool) -> void:
	enabled = not value
	for audio in [aircraft, footsteps, detail, hush, siren]: audio.volume_db = -80 if value else {aircraft: -30, footsteps: -22, detail: -21, hush: -41, siren: siren_level}[audio]

func start_siren() -> void:
	siren_fade = -1
	siren_level = -20
	siren_target = -20
	siren.volume_db = siren_level if enabled else -80
	siren.play()

func duck_siren() -> void:
	siren_duck = 0.75
	siren_target = -29
	siren_level = -40
	siren.volume_db = siren_level if enabled else -80

func fade_siren() -> void:
	siren_fade = 0

func _exit_tree() -> void:
	var bus := AudioServer.get_bus_index(siren_bus)
	if bus > 0: AudioServer.remove_bus(bus)
