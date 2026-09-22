extends CanvasLayer

const PAPER := Color("f5efdf")
const INK := Color("203e42")
const TEAL := Color("285b58")
const MUTED := Color("637572")
const GOLD := Color("e3ae54")
var root: Control
var hud: Control
var overlay: Control
var objective: Label
var progress: Label
var navigation: Label
var prompt: PanelContainer
var prompt_label: Label
var timeline: HBoxContainer
var main_font: SystemFont
var heading_font: SystemFont
var archive_player: VideoStreamPlayer
var archive_caption: Label
var caption_panel: PanelContainer
var archive_clock: Label
var archive_pause_button: Button
var captions: Array = []
const ARCHIVE_PATH := "res://assets/video/lky-1965-excerpt.ogv"

func _ready() -> void:
	main_font = SystemFont.new()
	main_font.font_names = PackedStringArray(["Helvetica Neue", "Arial", "Noto Sans"])
	main_font.font_weight = 400
	heading_font = SystemFont.new()
	heading_font.font_names = PackedStringArray(["Georgia", "Noto Serif", "serif"])
	root = Control.new()
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)
	var theme := Theme.new()
	theme.default_font = main_font
	theme.default_font_size = 18
	theme.set_color("font_color", "Label", INK)
	theme.set_stylebox("normal", "Button", style(TEAL, 10, 0, TEAL))
	theme.set_stylebox("hover", "Button", style(TEAL.lightened(0.12), 10, 0, TEAL))
	theme.set_stylebox("pressed", "Button", style(INK, 10, 0, INK))
	theme.set_stylebox("focus", "Button", style(Color.TRANSPARENT, 10, 3, GOLD))
	theme.set_stylebox("disabled", "Button", style(Color("c1c5b8"), 10, 0, INK))
	for state in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color"]:
		theme.set_color(state, "Button", PAPER)
	theme.set_color("font_disabled_color", "Button", Color("65726b"))
	theme.set_constant("outline_size", "Button", 0)
	root.theme = theme

func style(bg: Color, radius := 14, border := 0, stroke := INK) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = bg
	s.set_corner_radius_all(radius)
	s.set_border_width_all(border)
	s.border_color = stroke
	s.content_margin_left = 22
	s.content_margin_right = 22
	s.content_margin_top = 16
	s.content_margin_bottom = 16
	return s

func label(parent: Node, text: String, size := 18, color := INK, serif := false) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.add_theme_font_override("font", heading_font if serif else main_font)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(l)
	return l

func paragraph(parent: Node, text: String, size := 20, color := INK) -> Label:
	var l := label(parent, text, size, color)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.add_theme_constant_override("line_spacing", 5)
	return l

func button(parent: Node, text: String, action: Callable, secondary := false) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size.y = 50
	b.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	if secondary:
		b.add_theme_stylebox_override("normal", style(Color("e6e5d6"), 10))
		b.add_theme_stylebox_override("hover", style(Color("d9ddcf"), 10))
		b.add_theme_color_override("font_color", INK)
		b.add_theme_color_override("font_hover_color", INK)
		b.add_theme_color_override("font_focus_color", INK)
	b.pressed.connect(action)
	parent.add_child(b)
	return b

func gap(parent: Node, height := 12) -> void:
	var c := Control.new()
	c.custom_minimum_size.y = height
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(c)

func clear_overlay() -> void:
	if is_instance_valid(archive_player):
		archive_player.stop()
	archive_player = null
	if is_instance_valid(overlay):
		root.remove_child(overlay)
		overlay.queue_free()
	overlay = null

func new_overlay(dim := true) -> Control:
	clear_overlay()
	overlay = Control.new()
	overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.add_child(overlay)
	if dim:
		var veil := ColorRect.new()
		veil.color = Color(0.05, 0.13, 0.15, 0.42)
		veil.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		overlay.add_child(veil)
	return overlay

func modal(width := 790.0) -> VBoxContainer:
	new_overlay()
	var center := CenterContainer.new()
	center.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	overlay.add_child(center)
	var panel := PanelContainer.new()
	panel.custom_minimum_size.x = width
	panel.add_theme_stylebox_override("panel", style(PAPER, 18))
	center.add_child(panel)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 9)
	panel.add_child(v)
	return v

func show_menu(start: Callable, journal: Callable, resume: Callable, can_resume: bool) -> void:
	if is_instance_valid(hud):
		hud.visible = false
	new_overlay(false)
	var panel := PanelContainer.new()
	panel.set_anchors_and_offsets_preset(Control.PRESET_LEFT_WIDE)
	panel.offset_right = 500
	var s := style(PAPER, 0)
	s.content_margin_left = 48
	s.content_margin_right = 40
	s.content_margin_top = 36
	s.content_margin_bottom = 30
	panel.add_theme_stylebox_override("panel", s)
	overlay.add_child(panel)
	var v := VBoxContainer.new()
	panel.add_child(v)
	label(v, "S P A R K Y   D I S C O V E R Y", 15, TEAL)
	gap(v, 34)
	label(v, "Small bear.\nBig moment.", 53, INK, true)
	gap(v, 15)
	paragraph(v, "A nation of our own", 28, TEAL)
	gap(v, 16)
	paragraph(v, "Step into a Singapore neighbourhood on the day everything changed. Help Sparky bring the neighbours together for the news.", 19, MUTED)
	gap(v, 19)
	label(v, "9 AUGUST 1965   /   SINGAPORE", 14, TEAL)
	gap(v, 22)
	if can_resume:
		button(v, "Continue journey   →", resume).grab_focus()
		button(v, "Restart the chapter", start, true)
	else:
		button(v, "Step into 1965   →", start).grab_focus()
	gap(v, 2)
	button(v, "Historical notes & controls", journal, true)
	var spacer := Control.new()
	spacer.size_flags_vertical = Control.SIZE_EXPAND_FILL
	spacer.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.add_child(spacer)
	label(v, "WASD  Move    Mouse  Look    E  Interact", 14, MUTED)
	label(v, "The road to independence · First chapter prototype", 13, MUTED)
	var tag := label(overlay, "SINGAPORE  /  01° N, 103° E", 14, PAPER)
	tag.set_anchors_and_offsets_preset(Control.PRESET_TOP_RIGHT)
	tag.position = Vector2(-300, 34)
	var caption := label(overlay, "Meet Sparky. Your companion through time.", 18, INK)
	caption.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_RIGHT)
	caption.position = Vector2(-540, -56)

func build_hud(chapter: Dictionary, on_journal: Callable, on_pause: Callable) -> void:
	if is_instance_valid(hud):
		root.remove_child(hud)
		hud.queue_free()
	hud = Control.new()
	hud.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	hud.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(hud)
	# Keep modal overlays above the HUD.
	if is_instance_valid(overlay):
		root.move_child(overlay, -1)
	var header := PanelContainer.new()
	header.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	header.offset_left = 28
	header.offset_right = -28
	header.offset_top = 24
	header.offset_bottom = 108
	header.add_theme_stylebox_override("panel", style(PAPER, 14))
	hud.add_child(header)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 26)
	header.add_child(row)
	label(row, chapter.year, 38, TEAL, true)
	var titles := VBoxContainer.new()
	titles.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(titles)
	label(titles, "THE ROAD TO INDEPENDENCE  /  %s" % chapter.date, 12, MUTED)
	label(titles, chapter.title, 25, INK, true)
	button(row, "Journal  ·  J", on_journal, true)
	button(row, "Pause  ·  Esc", on_pause, true)
	var quest := PanelContainer.new()
	quest.position = Vector2(28, 132)
	quest.custom_minimum_size = Vector2(340, 110)
	quest.add_theme_stylebox_override("panel", style(PAPER, 12))
	hud.add_child(quest)
	var qv := VBoxContainer.new()
	qv.add_theme_constant_override("separation", 8)
	quest.add_child(qv)
	progress = label(qv, "YOUR NEXT STEP", 12, TEAL)
	objective = paragraph(qv, "", 20)
	objective.custom_minimum_size.x = 296
	navigation = label(qv, "Follow the gold marker", 15, TEAL)
	var footer := VBoxContainer.new()
	footer.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	footer.offset_left = 28
	footer.offset_right = -28
	footer.offset_top = -78
	footer.offset_bottom = -18
	hud.add_child(footer)
	timeline = HBoxContainer.new()
	timeline.add_theme_constant_override("separation", 8)
	footer.add_child(timeline)
	var steps := ["01   UNCLE TAN", "02   THE AERIAL", "03   THE SIGNAL", "04   INDEPENDENCE"]
	for i in steps.size():
		var chip := PanelContainer.new()
		chip.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		var chip_style := style(Color("e3e4d5"), 6)
		chip_style.content_margin_top = 8
		chip_style.content_margin_bottom = 8
		chip.add_theme_stylebox_override("panel", chip_style)
		timeline.add_child(chip)
		label(chip, steps[i], 13, MUTED)
	label(footer, "WASD  Move    Mouse  Look    Scroll  Zoom    R  Centre camera    E  Interact    J  Journal    Esc  Pause / release mouse", 13, INK)
	prompt = PanelContainer.new()
	prompt.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	prompt.offset_left = -255
	prompt.offset_right = 255
	prompt.offset_top = -153
	prompt.offset_bottom = -95
	prompt.add_theme_stylebox_override("panel", style(INK, 12))
	hud.add_child(prompt)
	prompt_label = label(prompt, "", 18, PAPER)
	prompt_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	prompt.visible = false

func set_objective(text: String, done: int, total: int) -> void:
	objective.text = text
	progress.text = "YOUR NEXT STEP   ·   %d / %d" % [done, total]
	for i in timeline.get_child_count():
		var chip := timeline.get_child(i) as PanelContainer
		var chip_style := style(TEAL if i == done else Color("e3e4d5"), 6)
		chip_style.content_margin_top = 8
		chip_style.content_margin_bottom = 8
		chip.add_theme_stylebox_override("panel", chip_style)
		chip.get_child(0).add_theme_color_override("font_color", PAPER if i == done else MUTED)

func set_prompt(text: String) -> void:
	if not is_instance_valid(prompt):
		return
	prompt.visible = not text.is_empty()
	prompt_label.text = text

func set_navigation(text: String) -> void:
	navigation.text = text

func show_intro(chapter: Dictionary, begin: Callable) -> void:
	var v := modal()
	label(v, "SINGAPORE    /    %s" % chapter.date, 14, TEAL)
	label(v, chapter.title, 40, INK, true)
	label(v, chapter.place, 17, MUTED)
	gap(v)
	paragraph(v, chapter.intro, 21)
	gap(v)
	label(v, "WASD to walk · Mouse to look · Follow the gold marker · E to interact", 16, MUTED)
	button(v, "Step into %s   →" % chapter.year, begin).grab_focus()

func show_dialogue(speaker: String, text: String, next: Callable, voice: AudioStreamPlayer = null) -> void:
	new_overlay(false)
	var frame := MarginContainer.new()
	frame.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	frame.offset_left = 250
	frame.offset_right = -250
	frame.offset_bottom = -112
	frame.mouse_filter = Control.MOUSE_FILTER_IGNORE
	overlay.add_child(frame)
	var panel := PanelContainer.new()
	panel.size_flags_vertical = Control.SIZE_SHRINK_END
	panel.add_theme_stylebox_override("panel", style(PAPER, 16, 2, Color("ded6c1")))
	frame.add_child(panel)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 12)
	panel.add_child(v)
	label(v, speaker.to_upper(), 14, TEAL)
	paragraph(v, text, 20)
	var row := HBoxContainer.new()
	v.add_child(row)
	var hint := label(row, "E or Enter to continue", 14, MUTED)
	hint.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	if voice:
		var replay := button(row, "Replay voice", func(): voice.play())
		replay.name = "ReplayVoice"
		var mute := button(row, "Unmute voice" if is_zero_approx(voice.volume_linear) else "Mute voice", func(): pass)
		mute.name = "MuteVoice"
		mute.pressed.connect(func():
			voice.volume_linear = 1.0 if is_zero_approx(voice.volume_linear) else 0.0
			mute.text = "Unmute voice" if is_zero_approx(voice.volume_linear) else "Mute voice"
		)
	button(row, "Continue  →", next).grab_focus()

func show_chapter_end(chapter: Dictionary, replay: Callable, journal: Callable) -> void:
	var v := modal()
	label(v, "HISTORY JOURNAL   /   ENTRY ADDED", 14, TEAL)
	label(v, chapter.year + " · " + chapter.short, 38, INK, true)
	paragraph(v, chapter.fact, 22)
	gap(v)
	label(v, "INDEPENDENCE WAS A BEGINNING", 13, TEAL)
	paragraph(v, chapter.bridge, 19, MUTED)
	gap(v)
	button(v, "Explore the historical notes", journal).grab_focus()
	button(v, "Return to title", replay, true)

func show_tuner(done: Callable, cancel: Callable) -> void:
	var v := modal(690)
	label(v, "9 AUGUST 1965  /  TELEVISION CORNER", 14, TEAL)
	label(v, "Find a clear signal", 36, INK, true)
	paragraph(v, "The aerial is fitted. Adjust the tuning dial until the picture clears.", 20)
	gap(v)
	var screen := PanelContainer.new()
	screen.custom_minimum_size.y = 130
	screen.add_theme_stylebox_override("panel", style(INK, 12))
	v.add_child(screen)
	var signal_label := label(screen, "░ ▒ ░ ▓ ▒ ░ ▓ ░\nNO SIGNAL", 26, PAPER)
	signal_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	signal_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	var slider := HSlider.new()
	slider.name = "TuningDial"
	slider.min_value = 0
	slider.max_value = 100
	slider.value = 20
	slider.step = 1
	slider.custom_minimum_size.y = 44
	v.add_child(slider)
	var strength := label(v, "Signal strength: 10%", 16, TEAL)
	label(v, "Drag the dial, or focus it and use ← / →.", 15, MUTED)
	var watch := button(v, "Watch the announcement   →", done)
	watch.disabled = true
	slider.value_changed.connect(func(value: float):
		var clear := absf(value - 65) <= 4
		strength.text = "Signal strength: %d%%" % int(clampf(100 - absf(value - 65) * 2, 0, 100))
		signal_label.text = "SINGAPORE\n9 AUGUST 1965" if clear else "░ ▒ ░ ▓ ▒ ░ ▓ ░\nTUNING…"
		watch.disabled = not clear
	)
	button(v, "Back to the street", cancel, true)
	slider.grab_focus()

func show_archive(done: Callable, change_view: Callable) -> VideoStreamPlayer:
	# Only the 3D television displays the decoded texture. No popup video surface.
	new_overlay(false)
	overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hud.visible = false
	archive_player = VideoStreamPlayer.new()
	archive_player.name = "ArchivalVideo"
	archive_player.expand = true
	archive_player.size = Vector2.ONE
	archive_player.self_modulate.a = 0.0
	archive_player.mouse_filter = Control.MOUSE_FILTER_IGNORE
	archive_player.stream = load(ARCHIVE_PATH) as VideoStream
	archive_player.volume_db = -80 if OS.get_cmdline_user_args().has("--test") else 8
	overlay.add_child(archive_player)
	var title_panel := PanelContainer.new()
	title_panel.position = Vector2(28, 24)
	title_panel.add_theme_stylebox_override("panel", style(Color(0.96, 0.94, 0.88, 0.93), 12))
	overlay.add_child(title_panel)
	var titles := VBoxContainer.new()
	title_panel.add_child(titles)
	label(titles, "9 AUGUST 1965  /  THE NEIGHBOURHOOD", 12, TEAL)
	label(titles, "Watching together", 27, INK, true)
	label(titles, "Original press-conference footage · via Wikimedia Commons", 12, MUTED)
	label(titles, "Space  Pause     V  Change view     Esc  Release mouse / pause", 12, TEAL)
	caption_panel = PanelContainer.new()
	caption_panel.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	caption_panel.offset_left = 310
	caption_panel.offset_right = -310
	caption_panel.offset_top = -184
	caption_panel.offset_bottom = -104
	caption_panel.add_theme_stylebox_override("panel", style(Color(0.04, 0.09, 0.08, 0.86), 8))
	overlay.add_child(caption_panel)
	archive_caption = paragraph(caption_panel, "", 21, Color.WHITE)
	archive_caption.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	archive_caption.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	caption_panel.visible = false
	captions = JSON.parse_string(FileAccess.get_file_as_string("res://assets/video/lky-1965-en.json"))
	var controls := PanelContainer.new()
	controls.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	controls.offset_left = 28
	controls.offset_right = -28
	controls.offset_top = -88
	controls.offset_bottom = -18
	controls.add_theme_stylebox_override("panel", style(Color(0.96, 0.94, 0.88, 0.95), 12))
	overlay.add_child(controls)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 10)
	controls.add_child(row)
	archive_pause_button = button(row, "Pause", toggle_video_pause, true)
	archive_clock = label(row, "00:00 / 01:58", 15, MUTED)
	archive_clock.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	button(row, "Community view", func(): change_view.call("community"), true)
	button(row, "TV view", func(): change_view.call("television"), true)
	button(row, "Walk around", func(): change_view.call("walk"), true)
	var cc := CheckButton.new()
	cc.text = "Captions"
	cc.button_pressed = true
	cc.toggled.connect(func(on: bool): archive_caption.visible = on)
	row.add_child(cc)
	var mute := CheckButton.new()
	mute.text = "Mute"
	mute.button_pressed = OS.get_cmdline_user_args().has("--test")
	mute.toggled.connect(func(on: bool): archive_player.volume_db = -80 if on else 8)
	row.add_child(mute)
	button(row, "Skip  →", done, true)
	archive_player.finished.connect(done)
	archive_player.play()
	archive_pause_button.grab_focus()
	return archive_player

func toggle_video_pause() -> void:
	if not is_instance_valid(archive_player):
		return
	archive_player.paused = not archive_player.paused
	archive_pause_button.text = "Resume" if archive_player.paused else "Pause"

func _process(_delta: float) -> void:
	if not is_instance_valid(archive_player):
		return
	var seconds := archive_player.stream_position
	archive_clock.text = "%02d:%02d / 01:58" % [int(seconds) / 60, int(seconds) % 60]
	var text := ""
	for caption in captions:
		if seconds >= caption.start and seconds < caption.end:
			text = caption.text
			break
	archive_caption.text = text
	caption_panel.visible = not text.is_empty() and archive_caption.visible

func show_pause(resume: Callable, restart: Callable, menu: Callable) -> void:
	var v := modal(570)
	label(v, "TAKE A BREATHER", 14, TEAL)
	label(v, "Journey paused", 38, INK, true)
	paragraph(v, "Your place is saved automatically after each encounter.", 19, MUTED)
	gap(v)
	button(v, "Resume", resume).grab_focus()
	button(v, "Restart this chapter", restart, true)
	button(v, "Return to title", menu, true)

func show_journal(chapter: Dictionary, completed: bool, sources: Array, close: Callable) -> void:
	var v := modal(880)
	label(v, "SPARKY’S FIELD NOTES", 14, TEAL)
	label(v, "A small guide to big events", 34, INK, true)
	var scroll := ScrollContainer.new()
	scroll.custom_minimum_size.y = 380
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	v.add_child(scroll)
	var pages := VBoxContainer.new()
	pages.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	pages.add_theme_constant_override("separation", 12)
	scroll.add_child(pages)
	paragraph(pages, "Move with WASD or the arrow keys. Move the mouse to look around; scroll to zoom. R centres the camera behind Sparky. Follow the gold marker and press E nearby. J opens this journal; Esc pauses and releases the mouse. Menus also support Tab and Enter. Progress saves locally after each encounter.", 17, MUTED)
	paragraph(pages, "Sparky, the neighbours, their dialogue and the streets are fictional. Dates and milestones follow the sources below. The scenes are illustrative, not exact reconstructions. The neighbours’ emotional reactions are imagined rather than documented eyewitness accounts. The television plays actual footage of Lee Kuan Yew’s 9 August 1965 press conference, with the original audio and pauses preserved.", 17, MUTED)
	paragraph(pages, "The video is a 1 minute 58 second excerpt (02:08–04:06) from the Wikimedia Commons recording. Its file page marks the recording public domain. English captions are adapted from the Commons TimedText contributors, under CC BY-SA 4.0. The source and contributor links are below.", 15, MUTED)
	label(pages, "1965  ·  Independence" + ("  ✓" if completed else ""), 23, TEAL, true)
	paragraph(pages, chapter.fact, 18)
	paragraph(pages, "Singapore joined Malaysia in 1963. Political and economic disagreements strained relations, and racial riots in 1964 deepened tensions. Negotiations among leaders led to separation in 1965; the outcome cannot be reduced to a single disagreement.", 18)
	label(pages, "READ THE HISTORY", 13, TEAL)
	for source in sources:
		var link := LinkButton.new()
		link.text = source[0] + "  ↗"
		link.add_theme_color_override("font_color", TEAL)
		link.pressed.connect(func(): OS.shell_open(source[1]))
		pages.add_child(link)
	gap(pages)
	paragraph(pages, "Character: Sparky, from the supplied Blender model. Built with Godot Engine (MIT licence). Engine notices: godotengine.org/license", 15, MUTED)
	button(v, "Back to the journey", close).grab_focus()
