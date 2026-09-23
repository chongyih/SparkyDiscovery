extends CanvasLayer

const TouchControls = preload("res://game/touch_controls.gd")
const History = preload("res://game/history.gd")

const PAPER := Color("f5efdf")
const INK := Color("203e42")
const TEAL := Color("285b58")
const MUTED := Color("637572")
const GOLD := Color("e3ae54")
const LINE := Color("ded6c1")
const PAGE := Color("fbf7ec")
const COVER := Color("1f4744")
const STEPS := ["Uncle Tan", "The antenna", "The signal", "Independence"]
var root: Control
var hud: Control
var overlay: Control
var objective: Label
var progress: Label
var navigation: Label
var prompt: PanelContainer
var prompt_label: Label
var progress_bar: HBoxContainer
var main_font: Font
var heading_font: FontVariation
var archive_player: VideoStreamPlayer
var archive_caption: Label
var caption_panel: PanelContainer
var archive_clock: Label
var archive_pause_button: Button
var archive_progress: ProgressBar
var archive_views := {}
## The journal remembers its open spread, like a bookmark.
var journal_spread := 0
var journal_pages: Array = []
var journal_data := {}
var captions: Array = []
const ARCHIVE_PATH := "res://assets/video/lky-1965-excerpt.ogv"
## Browsers decode Theora in WebAssembly on the main thread, and the 640×480 / 25 fps clip took
## over a second of CPU per second of footage. The web copy is 320×240 / 12 fps.
const ARCHIVE_WEB_PATH := "res://assets/video/lky-1965-excerpt-web.ogv"
## The archive speech measures about -29 LUFS; this lifts it to the -18 LUFS dialogue level (peaks stay near -3 dBFS).
const ARCHIVE_VOLUME_DB := 11.0
## Kelvin takes are normalized to -21 LUFS; playback stays about 6 dB under the broadcast.
const VOICE_VOLUME_DB := -3.6

func _ready() -> void:
	# Bundled so browsers, which cannot reach system fonts, show the same type as desktop.
	main_font = load("res://assets/fonts/Inter.ttf")
	heading_font = FontVariation.new()
	heading_font.base_font = load("res://assets/fonts/Gelasio.ttf")
	# Gelasio has no check mark; Inter supplies it.
	heading_font.fallbacks = [main_font]
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
	# Switched-on toggles (Captions, Mute) otherwise hover with Godot's empty style and white text.
	theme.set_stylebox("hover_pressed", "Button", style(INK.lightened(0.12), 10, 0, INK))
	theme.set_stylebox("focus", "Button", style(Color.TRANSPARENT, 10, 3, GOLD))
	theme.set_stylebox("disabled", "Button", style(Color("c1c5b8"), 10, 0, INK))
	for state in ["font_color", "font_hover_color", "font_pressed_color", "font_hover_pressed_color", "font_focus_color"]:
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
		set_secondary(b, true)
	b.pressed.connect(action)
	parent.add_child(b)
	return b

func set_secondary(b: Button, on: bool) -> void:
	for state in ["normal", "hover", "pressed", "hover_pressed", "focus"]:
		b.remove_theme_stylebox_override(state)
	for state in ["font_color", "font_hover_color", "font_focus_color"]:
		b.remove_theme_color_override(state)
	if not on:
		return
	b.add_theme_stylebox_override("normal", style(Color("e6e5d6"), 10))
	b.add_theme_stylebox_override("hover", style(Color("d9ddcf"), 10))
	for state in ["font_color", "font_hover_color", "font_focus_color"]:
		b.add_theme_color_override(state, INK)

## Compact buttons for secondary controls, so they don't compete with the main action.
func small_button(parent: Node, text: String, action: Callable) -> Button:
	var b := button(parent, text, action, true)
	b.custom_minimum_size.y = 42
	b.add_theme_font_size_override("font_size", 15)
	shrink(b)
	return b

func shrink(b: Button) -> void:
	for state in ["normal", "hover", "pressed", "hover_pressed", "focus"]:
		var s := (b.get_theme_stylebox(state) as StyleBoxFlat).duplicate() as StyleBoxFlat
		s.content_margin_left = 14
		s.content_margin_right = 14
		s.content_margin_top = 8
		s.content_margin_bottom = 8
		b.add_theme_stylebox_override(state, s)

## Borderless text button for page turns, contents and links in the journal.
func text_button(parent: Node, text: String, action: Callable, color := TEAL, size := 16) -> Button:
	var b := Button.new()
	b.text = text
	b.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	b.alignment = HORIZONTAL_ALIGNMENT_LEFT
	b.add_theme_font_size_override("font_size", size)
	for state in ["normal", "pressed", "disabled"]:
		b.add_theme_stylebox_override(state, compact(Color.TRANSPARENT))
	for state in ["hover", "hover_pressed"]:
		b.add_theme_stylebox_override(state, compact(Color(TEAL, 0.09)))
	var focus := compact(Color.TRANSPARENT)
	focus.set_border_width_all(2)
	focus.border_color = GOLD
	b.add_theme_stylebox_override("focus", focus)
	for state in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color", "font_hover_pressed_color"]:
		b.add_theme_color_override(state, color)
	b.add_theme_color_override("font_disabled_color", Color(MUTED, 0.35))
	b.pressed.connect(action)
	parent.add_child(b)
	return b

func compact(bg: Color, radius := 8) -> StyleBoxFlat:
	var s := style(bg, radius)
	s.content_margin_left = 10
	s.content_margin_right = 10
	s.content_margin_top = 5
	s.content_margin_bottom = 5
	return s

func rule(parent: Node, color := LINE) -> void:
	var line := ColorRect.new()
	line.color = color
	line.custom_minimum_size.y = 1
	line.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(line)

func fill(parent: Node) -> Control:
	var c := Control.new()
	c.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	c.size_flags_vertical = Control.SIZE_EXPAND_FILL
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(c)
	return c

## A small keyboard key, drawn as a raised cap.
func key_cap(parent: Node, key: String, size := 14, bg := Color.WHITE) -> PanelContainer:
	var cap := PanelContainer.new()
	var s := style(bg, 6, 1, Color(INK, 0.3))
	s.border_width_bottom = 3
	s.content_margin_left = 9
	s.content_margin_right = 9
	s.content_margin_top = 2
	s.content_margin_bottom = 2
	cap.add_theme_stylebox_override("panel", s)
	cap.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	cap.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	parent.add_child(cap)
	label(cap, key, size, INK).horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	return cap

## Round Journal and Pause buttons match the touch versions. Mouse capture keeps them
## out of reach while walking, so each shows its key.
func round_button(parent: Node, icon: String, key: String, tip: String, action: Callable) -> Button:
	var b := Button.new()
	b.name = icon.capitalize() + "Button"
	b.custom_minimum_size = Vector2(60, 60)
	b.tooltip_text = tip
	b.focus_mode = Control.FOCUS_NONE
	b.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	b.add_theme_stylebox_override("normal", style(Color(PAPER, 0.95), 30, 2, Color(INK, 0.16)))
	b.add_theme_stylebox_override("hover", style(Color.WHITE, 30, 2, Color(INK, 0.3)))
	b.add_theme_stylebox_override("pressed", style(Color("e6e5d6"), 30, 2, Color(INK, 0.3)))
	b.draw.connect(func(): draw_icon(b, icon, key))
	b.pressed.connect(action)
	parent.add_child(b)
	return b

func draw_icon(b: Control, icon: String, key: String) -> void:
	var c := b.size / 2.0
	if icon == "journal":
		# An open book: two pages meeting at the spine.
		for side in [-1, 1]:
			b.draw_colored_polygon(PackedVector2Array([
				c + Vector2(0, -8), c + Vector2(13 * side, -11),
				c + Vector2(13 * side, 9), c + Vector2(0, 12),
			]), INK)
			b.draw_line(c + Vector2(4 * side, -3), c + Vector2(10 * side, -4.5), PAPER, 1.5)
			b.draw_line(c + Vector2(4 * side, 2.5), c + Vector2(10 * side, 1), PAPER, 1.5)
	else:
		for x in [-6, 6]:
			b.draw_rect(Rect2(c + Vector2(x - 3, -10), Vector2(6, 20)), INK)
	var width := main_font.get_string_size(key, HORIZONTAL_ALIGNMENT_LEFT, -1, 11).x + 12
	var badge := Rect2(Vector2(b.size.x - width + 6, b.size.y - 14), Vector2(width, 19))
	b.draw_style_box(style(GOLD, 9, 2, PAPER), badge)
	b.draw_string(main_font, badge.position + Vector2(6, 14), key, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, INK)

func gap(parent: Node, height := 12) -> void:
	var c := Control.new()
	c.custom_minimum_size.y = height
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(c)

func clear_overlay() -> void:
	if is_instance_valid(archive_player):
		archive_player.stop()
	archive_player = null
	journal_pages = []
	if is_instance_valid(overlay):
		root.remove_child(overlay)
		overlay.queue_free()
	overlay = null

func new_overlay(dim := true, darkness := 0.42) -> Control:
	clear_overlay()
	overlay = Control.new()
	overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.add_child(overlay)
	if dim:
		var veil := ColorRect.new()
		veil.color = Color(0.05, 0.13, 0.15, darkness)
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
	panel.add_theme_stylebox_override("panel", card_style())
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
	label(v, "Left thumb  Move    Right thumb  Look    Gold button  Interact  ·  Play in landscape" if TouchControls.available() else "WASD  Move    Mouse  Look    E  Interact", 14, MUTED)
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
	# One card holds the chapter, how far along Sparky is and what to do next.
	var quest := PanelContainer.new()
	quest.position = Vector2(28, 24)
	quest.custom_minimum_size.x = 400
	var quest_style := style(Color(PAPER, 0.96), 16)
	quest_style.content_margin_top = 18
	quest_style.content_margin_bottom = 18
	quest.add_theme_stylebox_override("panel", quest_style)
	hud.add_child(quest)
	var qv := VBoxContainer.new()
	qv.add_theme_constant_override("separation", 8)
	quest.add_child(qv)
	var top := HBoxContainer.new()
	qv.add_child(top)
	label(top, "%s  ·  %s" % [chapter.year, chapter.title.to_upper()], 12, TEAL).size_flags_horizontal = Control.SIZE_EXPAND_FILL
	progress = label(top, "", 12, MUTED)
	progress_bar = HBoxContainer.new()
	progress_bar.add_theme_constant_override("separation", 5)
	qv.add_child(progress_bar)
	for i in STEPS.size():
		var segment := Panel.new()
		segment.custom_minimum_size.y = 5
		segment.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		progress_bar.add_child(segment)
	gap(qv, 2)
	objective = paragraph(qv, "", 21)
	objective.custom_minimum_size.x = 356
	navigation = label(qv, "Follow the gold marker", 15, TEAL)
	if not TouchControls.available():
		# Touch builds draw their own round buttons in the same corner.
		var menu := HBoxContainer.new()
		menu.set_anchors_and_offsets_preset(Control.PRESET_TOP_RIGHT)
		menu.grow_horizontal = Control.GROW_DIRECTION_BEGIN
		menu.offset_left = -28
		menu.offset_right = -28
		menu.offset_top = 24
		menu.add_theme_constant_override("separation", 14)
		hud.add_child(menu)
		round_button(menu, "journal", "J", "Journal (J)", on_journal)
		round_button(menu, "pause", "Esc", "Pause (Esc)", on_pause)
	# Controls fade once the player has had time to read them; the journal keeps the full list.
	var hint := PanelContainer.new()
	hint.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	hint.grow_horizontal = Control.GROW_DIRECTION_BOTH
	hint.grow_vertical = Control.GROW_DIRECTION_BEGIN
	hint.offset_top = -22
	hint.offset_bottom = -22
	var hint_style := style(Color(INK, 0.7), 10)
	hint_style.content_margin_top = 7
	hint_style.content_margin_bottom = 7
	hint_style.content_margin_left = 16
	hint_style.content_margin_right = 16
	hint.add_theme_stylebox_override("panel", hint_style)
	hud.add_child(hint)
	label(hint, "Left thumb  Walk      Right thumb  Look      Double-tap  Centre camera" if TouchControls.available() else "WASD  Walk      Mouse  Look      Scroll  Zoom      R  Centre camera      E  Interact", 14, PAPER)
	var fade := hint.create_tween()
	fade.tween_interval(18.0)
	fade.tween_property(hint, "modulate:a", 0.0, 1.5)
	prompt = PanelContainer.new()
	prompt.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	prompt.grow_horizontal = Control.GROW_DIRECTION_BOTH
	prompt.grow_vertical = Control.GROW_DIRECTION_BEGIN
	prompt.offset_top = -82
	prompt.offset_bottom = -82
	var prompt_style := style(Color(INK, 0.94), 14)
	prompt_style.content_margin_top = 11
	prompt_style.content_margin_bottom = 11
	prompt_style.content_margin_left = 14
	prompt.add_theme_stylebox_override("panel", prompt_style)
	hud.add_child(prompt)
	var prompt_row := HBoxContainer.new()
	prompt_row.add_theme_constant_override("separation", 12)
	prompt.add_child(prompt_row)
	if not TouchControls.available():
		key_cap(prompt_row, "E", 16, GOLD)
	prompt_label = label(prompt_row, "", 18, PAPER)
	prompt.visible = false

func set_objective(text: String, done: int, _total: int) -> void:
	objective.text = text
	progress.text = "STEP %d OF %d" % [mini(done, STEPS.size() - 1) + 1, STEPS.size()]
	for i in progress_bar.get_child_count():
		var segment := StyleBoxFlat.new()
		segment.set_corner_radius_all(3)
		segment.bg_color = TEAL if i < done else (GOLD if i == done else Color("dcd9c8"))
		progress_bar.get_child(i).add_theme_stylebox_override("panel", segment)

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
	label(v, "Left thumb to walk · Right thumb to look · Follow the gold marker · Tap the gold button" if TouchControls.available() else "WASD to walk · Mouse to look · Follow the gold marker · E to interact", 16, MUTED)
	button(v, "Step into %s   →" % chapter.year, begin).grab_focus()

## Darkens the bottom of the screen so text cards stand out from the bright scene.
func bottom_shade() -> void:
	var gradient := Gradient.new()
	gradient.set_color(0, Color(0.03, 0.08, 0.09, 0.0))
	gradient.set_color(1, Color(0.03, 0.08, 0.09, 0.45))
	var texture := GradientTexture2D.new()
	texture.gradient = gradient
	texture.fill_to = Vector2(0, 1)
	texture.width = 4
	texture.height = 128
	var shade := TextureRect.new()
	shade.texture = texture
	shade.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	shade.stretch_mode = TextureRect.STRETCH_SCALE
	shade.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	shade.offset_top = -380
	shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	overlay.add_child(shade)

func card_style(bg := PAPER) -> StyleBoxFlat:
	var s := style(bg, 18)
	s.content_margin_left = 32
	s.content_margin_right = 32
	s.content_margin_top = 24
	s.content_margin_bottom = 22
	s.shadow_color = Color(0, 0, 0, 0.18)
	s.shadow_size = 18
	s.shadow_offset = Vector2(0, 6)
	return s

## A card centred at the bottom of the screen, at a comfortable reading width.
func bottom_card(width := 840.0) -> VBoxContainer:
	var holder := VBoxContainer.new()
	holder.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	holder.offset_bottom = -32
	holder.alignment = BoxContainer.ALIGNMENT_END
	holder.mouse_filter = Control.MOUSE_FILTER_IGNORE
	overlay.add_child(holder)
	var panel := PanelContainer.new()
	panel.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	panel.custom_minimum_size.x = width
	panel.add_theme_stylebox_override("panel", card_style())
	holder.add_child(panel)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 14)
	panel.add_child(v)
	return v

func name_tag(parent: Node, speaker: String) -> void:
	var tag := PanelContainer.new()
	tag.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	var s := style(TEAL, 8)
	s.content_margin_left = 12
	s.content_margin_right = 12
	s.content_margin_top = 3
	s.content_margin_bottom = 5
	tag.add_theme_stylebox_override("panel", s)
	parent.add_child(tag)
	label(tag, speaker, 18, PAPER, true)

## A sourced fact, set apart from fictional dialogue with a gold rule.
func note_card(parent: Node, note: Dictionary) -> void:
	var card := PanelContainer.new()
	var s := style(Color("ede5d0"), 10)
	s.border_width_left = 4
	s.border_color = GOLD
	s.content_margin_left = 18
	s.content_margin_right = 18
	s.content_margin_top = 12
	s.content_margin_bottom = 12
	card.add_theme_stylebox_override("panel", s)
	parent.add_child(card)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 4)
	card.add_child(v)
	label(v, note.tag.to_upper(), 12, TEAL)
	paragraph(v, note.note, 17)
	if note.has("source"):
		label(v, "Source: %s  ·  links in the journal" % note.source, 13, MUTED)

func show_dialogue(speaker: String, text: String, next: Callable, voice: AudioStreamPlayer = null, note: Dictionary = {}, narration := false) -> void:
	new_overlay(false)
	if is_instance_valid(hud):
		hud.visible = false
	bottom_shade()
	var v := bottom_card()
	if narration:
		label(v, speaker.to_upper(), 13, TEAL)
	else:
		name_tag(v, speaker)
	var body := VBoxContainer.new()
	body.add_theme_constant_override("separation", 10)
	v.add_child(body)
	for part in text.split("\n\n"):
		var line := paragraph(body, part, 21)
		if narration:
			line.add_theme_font_override("font", heading_font)
	if not note.is_empty():
		note_card(v, note)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	v.add_child(row)
	if voice:
		var replay := small_button(row, "Replay voice", func(): voice.play())
		replay.name = "ReplayVoice"
		var mute := small_button(row, "Unmute voice" if is_zero_approx(voice.volume_linear) else "Mute voice", func(): pass)
		mute.name = "MuteVoice"
		mute.pressed.connect(func():
			if is_zero_approx(voice.volume_linear):
				voice.volume_db = VOICE_VOLUME_DB
			else:
				voice.volume_linear = 0.0
			mute.text = "Unmute voice" if is_zero_approx(voice.volume_linear) else "Mute voice"
		)
	fill(row)
	if not TouchControls.available():
		key_cap(row, "E")
		gap(row, 0)
	button(row, "Continue  →", next).grab_focus()

func show_sequence(title: String, text: String, skip: Callable, skip_label: String) -> void:
	new_overlay(false)
	hud.visible = false
	bottom_shade()
	var v := bottom_card(760)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 25)
	v.add_child(row)
	var words := VBoxContainer.new()
	words.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	words.add_theme_constant_override("separation", 4)
	row.add_child(words)
	label(words, title, 26, INK, true)
	paragraph(words, text, 18, MUTED)
	var skip_button := button(row, skip_label + "  →", skip, true)
	skip_button.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	skip_button.grab_focus()

func show_reflection(topics: Dictionary, asked: Dictionary, choose: Callable, finish: Callable) -> void:
	new_overlay(false)
	hud.visible = false
	bottom_shade()
	var panel := PanelContainer.new()
	panel.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT)
	panel.grow_vertical = Control.GROW_DIRECTION_BEGIN
	panel.offset_left = 32
	panel.offset_top = -32
	panel.offset_bottom = -32
	panel.custom_minimum_size.x = 560
	panel.add_theme_stylebox_override("panel", card_style())
	overlay.add_child(panel)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 10)
	panel.add_child(v)
	name_tag(v, "Uncle Tan")
	label(v, "What’s on Sparky’s mind?", 30, INK, true)
	paragraph(v, "Ask as many as you like, then thank him.", 16, MUTED)
	gap(v, 2)
	for id in topics:
		var choice := small_button(v, "“%s”" % topics[id].question, func(): choose.call(id))
		choice.name = "Topic_" + id
		choice.alignment = HORIZONTAL_ALIGNMENT_LEFT
		choice.custom_minimum_size.y = 48
		choice.add_theme_font_size_override("font_size", 17)
		if asked.has(id):
			choice.text += "   ✓"
			for state in ["font_color", "font_hover_color", "font_focus_color"]:
				choice.add_theme_color_override(state, MUTED)
	gap(v, 4)
	button(v, "Thank you, Uncle Tan  →", finish).grab_focus()

func show_chapter_end(chapter: Dictionary, replay: Callable, journal: Callable) -> void:
	var v := modal(760)
	label(v, "CHAPTER ONE COMPLETE  ·  NEW JOURNAL ENTRY", 13, TEAL)
	label(v, chapter.year + " · " + chapter.short, 40, INK, true)
	paragraph(v, chapter.fact, 21)
	gap(v, 4)
	rule(v)
	gap(v, 4)
	label(v, "INDEPENDENCE WAS A BEGINNING", 12, TEAL)
	paragraph(v, chapter.bridge, 18, MUTED)
	gap(v)
	button(v, "Open Sparky’s journal", journal).grab_focus()
	button(v, "Return to title", replay, true)

func show_tuner(done: Callable, cancel: Callable, tuned: Callable = Callable()) -> void:
	new_overlay(false)
	hud.visible = false
	var gesture := preload("res://game/antenna_tuner.gd").new()
	gesture.name = "AntennaTuner"
	gesture.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	overlay.add_child(gesture)
	if tuned.is_valid():
		gesture.adjusted.connect(tuned)
	gesture.settled.connect(done)
	var touch := TouchControls.available()
	var v := bottom_card(1160 if touch else 940)
	v.add_theme_constant_override("separation", 8)
	label(v, "Find a clear picture", 32 if touch else 28, INK, true)
	gesture.hint = label(v, "Move the antenna until the snow clears.", 26 if touch else 19, TEAL)
	label(v, "Swipe across the TV view, or tap the arrows." if touch else "Drag across the TV view, tap the arrows, or use ← →.", 24 if touch else 16, MUTED)
	gesture.progress = ProgressBar.new()
	gesture.progress.custom_minimum_size.y = 8
	gesture.progress.show_percentage = false
	gesture.progress.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.add_child(gesture.progress)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 14)
	v.add_child(row)
	for direction in [-1, 1]:
		var b := button(row, "←  Left" if direction == -1 else "Right  →", func(): gesture.adjust(direction * 8.0))
		b.custom_minimum_size = Vector2(230, 104) if touch else Vector2(180, 64)
		b.add_theme_font_size_override("font_size", 28 if touch else 18)
		b.focus_mode = Control.FOCUS_NONE
	fill(row)
	var back := button(row, "Back to the street", cancel, true)
	back.add_theme_font_size_override("font_size", 26 if touch else 18)
	gesture.adjust(0)
	gesture.grab_focus()

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
	archive_player.stream = load(ARCHIVE_WEB_PATH if OS.has_feature("web") else ARCHIVE_PATH) as VideoStream
	archive_player.volume_db = -80 if OS.get_cmdline_user_args().has("--test") else ARCHIVE_VOLUME_DB
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
	if not TouchControls.available():
		label(titles, "Space  Pause      V  Change view      Esc  Release mouse", 12, TEAL)
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
	archive_pause_button = small_button(row, "Pause", toggle_video_pause)
	archive_pause_button.custom_minimum_size.x = 96
	archive_clock = label(row, "00:00 / 01:58", 15, MUTED)
	archive_clock.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	archive_clock.size_flags_vertical = Control.SIZE_FILL
	archive_progress = ProgressBar.new()
	archive_progress.show_percentage = false
	archive_progress.max_value = 118.0
	archive_progress.custom_minimum_size = Vector2(120, 6)
	archive_progress.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	archive_progress.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	archive_progress.mouse_filter = Control.MOUSE_FILTER_IGNORE
	for part in [["background", Color("dcd9c8")], ["fill", TEAL]]:
		var bar := StyleBoxFlat.new()
		bar.bg_color = part[1]
		bar.set_corner_radius_all(3)
		archive_progress.add_theme_stylebox_override(part[0], bar)
	row.add_child(archive_progress)
	gap(row, 0)
	# The camera views act as one segmented choice; the current one is filled.
	archive_views.clear()
	var views := HBoxContainer.new()
	views.add_theme_constant_override("separation", 4)
	row.add_child(views)
	for view in [["community", "Community view"], ["television", "TV view"], ["walk", "Walk around"]]:
		archive_views[view[0]] = small_button(views, view[1], func(): change_view.call(view[0]))
	set_archive_view("community")
	gap(row, 0)
	var cc := small_button(row, "Captions on", func(): pass)
	cc.pressed.connect(func():
		archive_caption.visible = not archive_caption.visible
		cc.text = "Captions on" if archive_caption.visible else "Captions off"
	)
	var sound := small_button(row, "Sound off" if OS.get_cmdline_user_args().has("--test") else "Sound on", func(): pass)
	sound.pressed.connect(func():
		var silence := archive_player.volume_db > -1.0
		archive_player.volume_db = -80 if silence else ARCHIVE_VOLUME_DB
		sound.text = "Sound off" if silence else "Sound on"
	)
	small_button(row, "Skip  →", done)
	archive_player.finished.connect(done)
	archive_player.play()
	archive_pause_button.grab_focus()
	return archive_player

func toggle_video_pause() -> void:
	if not is_instance_valid(archive_player):
		return
	archive_player.paused = not archive_player.paused
	archive_pause_button.text = "Resume" if archive_player.paused else "Pause"

func set_archive_view(view: String) -> void:
	for id in archive_views:
		var b: Button = archive_views[id]
		if is_instance_valid(b):
			set_secondary(b, id != view)
			shrink(b)

func _process(_delta: float) -> void:
	if not is_instance_valid(archive_player):
		return
	var seconds := archive_player.stream_position
	archive_clock.text = "%02d:%02d / 01:58" % [int(seconds) / 60, int(seconds) % 60]
	archive_progress.value = seconds
	var text := ""
	for caption in captions:
		if seconds >= caption.start and seconds < caption.end:
			text = caption.text
			break
	archive_caption.text = text
	caption_panel.visible = not text.is_empty() and archive_caption.visible

func show_pause(resume: Callable, restart: Callable, menu: Callable, ambience: Callable = Callable(), ambient_enabled := true) -> void:
	var v := modal(570)
	label(v, "TAKE A BREATHER", 14, TEAL)
	label(v, "Journey paused", 38, INK, true)
	paragraph(v, "Your place is saved automatically after each encounter.", 19, MUTED)
	gap(v)
	button(v, "Resume", resume).grab_focus()
	button(v, "Restart this chapter", restart, true)
	button(v, "Return to title", menu, true)
	if ambience.is_valid():
		var toggle := CheckButton.new()
		toggle.text = "Ambient sound"
		toggle.button_pressed = ambient_enabled
		toggle.toggled.connect(ambience)
		v.add_child(toggle)

## Sparky's journal is an open book: two pages per spread, turned with the page buttons or ← →.
const JOURNAL_PAGES := ["title", "day", "before", "after", "sources", "real", "controls", "credits"]
const CONTENTS := [
	["9 August 1965", "day"], ["How we got here", "before"], ["What came next", "after"],
	["Read the history", "sources"], ["What is real here?", "real"], ["How to play", "controls"], ["Credits", "credits"],
]

func show_journal(chapter: Dictionary, progress: int, sources: Array, close: Callable) -> void:
	new_overlay(true, 0.6)
	journal_data = {"chapter": chapter, "progress": progress, "sources": sources}
	var center := CenterContainer.new()
	center.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	overlay.add_child(center)
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 16)
	center.add_child(column)
	var cover := PanelContainer.new()
	var cover_style := style(COVER, 20)
	cover_style.set_content_margin_all(14)
	cover_style.shadow_color = Color(0, 0, 0, 0.35)
	cover_style.shadow_size = 30
	cover_style.shadow_offset = Vector2(0, 12)
	cover.add_theme_stylebox_override("panel", cover_style)
	column.add_child(cover)
	var spread := HBoxContainer.new()
	spread.add_theme_constant_override("separation", 0)
	cover.add_child(spread)
	for side in 2:
		if side == 1:
			spread.add_child(gutter())
		var page := PanelContainer.new()
		page.custom_minimum_size = Vector2(560, 680)
		var page_style := style(PAGE, 0)
		page_style.corner_radius_top_left = 10 if side == 0 else 0
		page_style.corner_radius_bottom_left = 10 if side == 0 else 0
		page_style.corner_radius_top_right = 10 if side == 1 else 0
		page_style.corner_radius_bottom_right = 10 if side == 1 else 0
		page_style.content_margin_left = 50 if side == 0 else 40
		page_style.content_margin_right = 40 if side == 0 else 50
		page_style.content_margin_top = 42
		page_style.content_margin_bottom = 24
		page.add_theme_stylebox_override("panel", page_style)
		spread.add_child(page)
		var content := VBoxContainer.new()
		content.add_theme_constant_override("separation", 10)
		page.add_child(content)
		journal_pages.append(content)
	var actions := HBoxContainer.new()
	actions.alignment = BoxContainer.ALIGNMENT_CENTER
	actions.add_theme_constant_override("separation", 18)
	column.add_child(actions)
	var back := button(actions, "Back to the journey", close)
	back.name = "CloseJournal"
	back.custom_minimum_size.x = 260
	if not TouchControls.available():
		label(actions, "←  →  Turn pages      J  Close", 14, PAPER).vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	render_spread()
	back.grab_focus()

## Pages darken towards the spine, with a crease down the middle.
func gutter() -> TextureRect:
	var gradient := Gradient.new()
	gradient.offsets = PackedFloat32Array([0.0, 0.47, 0.5, 0.53, 1.0])
	gradient.colors = PackedColorArray([PAGE, Color("ddd2b6"), Color("b9ad8f"), Color("ddd2b6"), PAGE])
	var texture := GradientTexture2D.new()
	texture.gradient = gradient
	texture.width = 64
	texture.height = 4
	var crease := TextureRect.new()
	crease.texture = texture
	crease.custom_minimum_size.x = 30
	crease.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	crease.stretch_mode = TextureRect.STRETCH_SCALE
	crease.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return crease

func turn_page(delta: int) -> void:
	var last := (JOURNAL_PAGES.size() - 1) / 2
	var target := clampi(journal_spread + delta, 0, last)
	if target != journal_spread:
		journal_spread = target
		render_spread(0 if delta < 0 else 1)

func open_page(page: String) -> void:
	journal_spread = JOURNAL_PAGES.find(page) / 2
	render_spread()

func render_spread(focus_side := -1) -> void:
	var last := (JOURNAL_PAGES.size() - 1) / 2
	journal_spread = clampi(journal_spread, 0, last)
	for side in 2:
		var content: VBoxContainer = journal_pages[side]
		for child in content.get_children():
			content.remove_child(child)
			child.queue_free()
		var index := journal_spread * 2 + side
		var body := VBoxContainer.new()
		body.size_flags_vertical = Control.SIZE_EXPAND_FILL
		body.add_theme_constant_override("separation", 10)
		content.add_child(body)
		call("page_" + JOURNAL_PAGES[index], body)
		var footer := HBoxContainer.new()
		content.add_child(footer)
		var number := label(footer, str(index + 1), 14, MUTED)
		number.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		var turn: Button
		if side == 0:
			turn = text_button(footer, "←  Previous", func(): turn_page(-1))
			turn.disabled = journal_spread == 0
			footer.move_child(turn, 0)
			fill(footer)
			footer.move_child(number, -1)
		else:
			fill(footer)
			turn = text_button(footer, "Next  →", func(): turn_page(1))
			turn.disabled = journal_spread == last
		turn.name = "PreviousPage" if side == 0 else "NextPage"
		if side == focus_side:
			var target: Control = turn if not turn.disabled else overlay.find_child("CloseJournal", true, false)
			target.grab_focus.call_deferred()
		content.modulate.a = 0.0
		content.create_tween().tween_property(content, "modulate:a", 1.0, 0.2)

func _input(event: InputEvent) -> void:
	if journal_pages.is_empty() or not is_instance_valid(journal_pages[0]):
		return
	if event is InputEventKey and event.pressed and not event.echo:
		match event.physical_keycode:
			KEY_LEFT, KEY_PAGEUP:
				turn_page(-1)
			KEY_RIGHT, KEY_PAGEDOWN:
				turn_page(1)
			_:
				return
		get_viewport().set_input_as_handled()

func page_heading(page: Node, eyebrow: String, title: String) -> void:
	label(page, eyebrow, 12, TEAL)
	label(page, title, 32, INK, true)
	gap(page, 2)

func page_title(page: VBoxContainer) -> void:
	gap(page, 8)
	label(page, "SPARKY’S JOURNAL", 13, TEAL)
	label(page, "The road to\nindependence", 42, INK, true)
	paragraph(page, "Notes kept by a small bear on a big journey.", 17, MUTED)
	gap(page, 16)
	rule(page)
	gap(page, 2)
	label(page, "CONTENTS", 12, TEAL)
	for entry in CONTENTS:
		var row := HBoxContainer.new()
		page.add_child(row)
		var link := text_button(row, entry[0], func(): open_page(entry[1]), INK, 17)
		link.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		var number := label(row, str(JOURNAL_PAGES.find(entry[1]) + 1), 15, MUTED)
		number.vertical_alignment = VERTICAL_ALIGNMENT_CENTER

func page_day(page: VBoxContainer) -> void:
	var chapter: Dictionary = journal_data.chapter
	var progress: int = journal_data.progress
	page_heading(page, "CHAPTER ONE  ·  9 AUGUST 1965", chapter.title)
	# Tuning and watching both finish with the broadcast, the chapter's last checkpoint.
	var done := [progress >= 1, progress >= 2, progress >= 3, progress >= 3]
	for i in History.JOURNEY.size():
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 14)
		page.add_child(row)
		var mark := PanelContainer.new()
		mark.custom_minimum_size = Vector2(28, 28)
		mark.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
		var mark_style := style(TEAL if done[i] else Color.TRANSPARENT, 14, 0 if done[i] else 2, Color(MUTED, 0.45))
		mark_style.set_content_margin_all(0)
		mark.add_theme_stylebox_override("panel", mark_style)
		row.add_child(mark)
		var tick := label(mark, "✓" if done[i] else str(i + 1), 14, PAPER if done[i] else MUTED)
		tick.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		tick.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		var words := VBoxContainer.new()
		words.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		words.add_theme_constant_override("separation", 1)
		row.add_child(words)
		label(words, History.JOURNEY[i][0], 18, INK if done[i] else MUTED)
		paragraph(words, History.JOURNEY[i][1] if done[i] else "Not written yet.", 15, MUTED)
	gap(page, 4)
	if progress >= 3:
		note_card(page, {"tag": "Entry complete", "note": chapter.fact})
	else:
		paragraph(page, "Keep going, Sparky. The rest of this page is still blank.", 15, MUTED)

func page_before(page: VBoxContainer) -> void:
	page_heading(page, "BEFORE 9 AUGUST 1965", "How we got here")
	for item in History.TIMELINE:
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 16)
		page.add_child(row)
		var when := label(row, item[0], 17, TEAL, true)
		when.custom_minimum_size.x = 130
		when.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
		paragraph(row, item[1], 17).size_flags_horizontal = Control.SIZE_EXPAND_FILL
	gap(page, 6)
	rule(page)
	gap(page, 2)
	paragraph(page, journal_data.chapter.background, 16, MUTED)

func page_after(page: VBoxContainer) -> void:
	var unlocked: bool = journal_data.progress >= 3
	page_heading(page, "UNCLE TAN’S WORRIES", "What came next")
	paragraph(page, journal_data.chapter.bridge, 16, MUTED)
	for id in History.REFLECTIONS:
		var topic: Dictionary = History.REFLECTIONS[id]
		gap(page, 2)
		label(page, topic.question, 18, INK, true)
		if unlocked:
			paragraph(page, topic.note + "  (" + topic.source + ")", 15)
		else:
			paragraph(page, "Ask Uncle Tan after the broadcast to fill this in.", 15, MUTED)

func page_sources(page: VBoxContainer) -> void:
	page_heading(page, "SOURCES", "Read the history")
	paragraph(page, "Dates and milestones in this chapter follow these sources.", 15, MUTED)
	for source in journal_data.sources:
		var parts: PackedStringArray = source[0].split(" · ")
		var row := HBoxContainer.new()
		page.add_child(row)
		var link := text_button(row, parts[0] + "  →", func(): OS.shell_open(source[1]), TEAL, 15)
		link.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		link.tooltip_text = source[1]
		if parts.size() > 1:
			label(row, parts[1], 13, MUTED).vertical_alignment = VERTICAL_ALIGNMENT_CENTER

func page_real(page: VBoxContainer) -> void:
	page_heading(page, "REAL AND IMAGINED", "What is real here?")
	for part in [
		["REAL", "The date and milestones, from the sources on the previous page. The television plays actual footage of Lee Kuan Yew’s press conference on 9 August 1965, with its original audio and pauses."],
		["IMAGINED", "Sparky, Uncle Tan, the neighbours and everything they say. The streets and block are illustrative, not a particular neighbourhood. The neighbours’ tears are imagined, not eyewitness accounts."],
		["THE FOOTAGE", "A 1 minute 58 second excerpt (02:08–04:06) of the Wikimedia Commons recording, which its file page marks as public domain. English captions are adapted from the Commons TimedText contributors under CC BY-SA 4.0."],
	]:
		gap(page, 2)
		label(page, part[0], 12, TEAL)
		paragraph(page, part[1], 16, INK if part[0] != "THE FOOTAGE" else MUTED)

func page_controls(page: VBoxContainer) -> void:
	page_heading(page, "HOW TO PLAY", "Getting around")
	var rows := [
		["Left thumb", "Touch and slide to walk; push further to go faster"],
		["Right thumb", "Drag to look around"],
		["Double-tap", "Centre the camera behind Sparky"],
		["Gold button", "Talk, pick up and use things"],
		["Top right", "Journal and pause"],
	] if TouchControls.available() else [
		["WASD", "Walk (arrow keys work too)"], ["Mouse", "Look around"], ["Scroll", "Zoom"],
		["R", "Centre the camera"], ["E", "Talk, pick up, continue"], ["J", "Open or close this journal"],
		["Esc", "Pause and release the mouse"], ["Space", "Pause the broadcast"], ["V", "Change view during the broadcast"],
	]
	for item in rows:
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 14)
		page.add_child(row)
		var cell := HBoxContainer.new()
		cell.custom_minimum_size.x = 120
		row.add_child(cell)
		key_cap(cell, item[0])
		paragraph(row, item[1], 16).size_flags_horizontal = Control.SIZE_EXPAND_FILL
	gap(page, 4)
	paragraph(page, "Follow the gold marker. Progress saves after each step.", 15, MUTED)

func page_credits(page: VBoxContainer) -> void:
	page_heading(page, "CREDITS", "Thank you")
	for part in [
		["CHARACTER", "Sparky, from the supplied Blender model."],
		["VOICE", "Uncle Tan’s dialogue uses the AI-generated Kelvin voice from ElevenLabs."],
		["SOUND", "Field recordings by Joseph Sardin (BigSoundBank.com, CC0) and footsteps by Kenney (CC0). Asian koel by Yosef Ben Melamed and common myna by James Ray (xeno-canto XC509296), via Wikimedia Commons under CC BY-SA 4.0; trimmed and filtered. These are modern recordings, not archival sound from 1965."],
		["ENGINE", "Built with Godot Engine (MIT licence). godotengine.org/license"],
	]:
		gap(page, 2)
		label(page, part[0], 12, TEAL)
		paragraph(page, part[1], 15, MUTED)
