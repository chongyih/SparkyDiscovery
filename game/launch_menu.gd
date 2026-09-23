extends Control
## The title and chapter browser share one old-and-new Singapore stage, independent of the 3D camera.
const NIGHT := Color("202925")
const CREAM := Color("f5ecd9")
const AMBER := Color("e5c795")
const SOFT := Color("d9d6cb")
const RED := Color("9e382c")
var mascot: TextureRect
var art_note: Label
var ui: CanvasLayer
var home: Control
var browser: Control
var primary: Button
var chapter_button: Button
var first_chapter: Button
var title: Label
var subtitle: Label
var discovery: Label
var title_gap: Control
var title_stack: VBoxContainer
var actions: VBoxContainer
var credits: Label
var chapter_scroll: ScrollContainer
var chapter_margin: MarginContainer
var chapter_row: BoxContainer
var chapter_heading: Label

func setup(interface: CanvasLayer, start: Callable, journal: Callable, resume: Callable, can_resume: bool, journey: Callable, wartime: Callable, has_wartime: bool, continue_journey: Callable = Callable(), journey_finished := false) -> void:
	ui = interface
	name = "LaunchMenu"
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var art := TextureRect.new()
	art.name = "TitleArtwork"
	art.texture = load("res://assets/menu/singapore-old-new-torn.png")
	art.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	art.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	art.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	art.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(art)
	var gradient := Gradient.new()
	gradient.set_color(0, Color(NIGHT, 0.46))
	gradient.add_point(0.48, Color(NIGHT, 0.08))
	gradient.set_color(gradient.get_point_count() - 1, Color(NIGHT, 0.86))
	var shade_texture := GradientTexture2D.new()
	shade_texture.gradient = gradient
	shade_texture.fill_from = Vector2(0, 0)
	shade_texture.fill_to = Vector2(0, 1)
	var shade := TextureRect.new()
	shade.texture = shade_texture
	shade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(shade)

	home = Control.new()
	home.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(home)
	mascot = preload("res://game/launch_sparky.gd").new()
	mascot.name = "SparkyPortrait"
	home.add_child(mascot)
	title_stack = VBoxContainer.new()
	title_stack.add_theme_constant_override("separation", 0)
	home.add_child(title_stack)
	title = words(title_stack, "Sparky", 108, CREAM, true)
	title.add_theme_color_override("font_shadow_color", Color(NIGHT, 0.6))
	title.add_theme_constant_override("shadow_offset_y", 4)
	discovery = words(title_stack, "D I S C O V E R Y", 27, CREAM)
	ui.gap(title_stack, 18)
	title_gap = title_stack.get_child(title_stack.get_child_count() - 1)
	subtitle = words(title_stack, "A small bear in a changing Singapore.", 18, CREAM)
	subtitle.add_theme_constant_override("line_spacing", 5)

	actions = VBoxContainer.new()
	actions.add_theme_constant_override("separation", 10)
	home.add_child(actions)
	var continue_action := journey if journey.is_valid() else start
	var can_continue := (has_wartime or can_resume) and not journey_finished
	if can_continue and continue_journey.is_valid():
		continue_action = continue_journey
	elif can_continue and can_resume:
		continue_action = resume
	elif can_continue and has_wartime:
		continue_action = wartime
	primary = menu_button(actions, "Continue journey   →" if can_continue else "Begin journey   →", continue_action, true)
	primary.name = "BeginJourney"
	var links := HBoxContainer.new()
	links.alignment = BoxContainer.ALIGNMENT_CENTER
	links.add_theme_constant_override("separation", 12)
	actions.add_child(links)
	chapter_button = menu_button(links, "Chapters", show_chapters)
	chapter_button.name = "ChooseChapters"
	menu_button(links, "Journal", journal).name = "LaunchJournal"
	credits = words(home, "EXPLORE THE PAST. MEET ITS PEOPLE.", 11, SOFT)
	art_note = words(home, "SINGAPORE, THEN & NOW", 11, SOFT)

	browser = Control.new()
	browser.name = "ChapterBrowser"
	browser.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(browser)
	var dim := ColorRect.new()
	dim.color = Color(NIGHT, 0.89)
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	browser.add_child(dim)
	chapter_scroll = ScrollContainer.new()
	chapter_scroll.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	chapter_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	chapter_scroll.follow_focus = true
	browser.add_child(chapter_scroll)
	chapter_margin = MarginContainer.new()
	chapter_margin.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	chapter_scroll.add_child(chapter_margin)
	var contents := VBoxContainer.new()
	contents.add_theme_constant_override("separation", 18)
	chapter_margin.add_child(contents)
	var back := menu_button(contents, "←  Back to title", show_home)
	back.name = "BackToTitle"
	back.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	words(contents, "THE JOURNEY", 12, AMBER)
	chapter_heading = words(contents, "Choose a moment in time", 42, CREAM, true)
	words(contents, "Start at the beginning, or step into either chapter.", 16, SOFT).autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	chapter_row = BoxContainer.new()
	chapter_row.add_theme_constant_override("separation", 24)
	contents.add_child(chapter_row)
	if journey.is_valid():
		first_chapter = chapter("01", "1942", "A place of shelter", "FEBRUARY 1942", "On a wartime street, help Uncle Tan and Mei bring water to the shelter.", "Continue 1942" if has_wartime else "Begin in 1942", wartime if has_wartime else journey, journey if has_wartime else Callable(), RED)
	var second := chapter("02", "1965", "A moment together", "9 AUGUST 1965", "An antenna, a television, and neighbours gathering for news of independence.", "Continue 1965" if can_resume else "Step into 1965", resume if can_resume else start, start if can_resume else Callable(), Color("45695f"))
	if not is_instance_valid(first_chapter):
		first_chapter = second
	words(contents, "Your progress is saved after each encounter.", 12, SOFT)
	browser.hide()
	resized.connect(layout)
	layout()
	primary.grab_focus()

func words(parent: Node, text: String, size: int, color: Color, serif := false) -> Label:
	var result: Label = ui.label(parent, text, size, color, serif)
	result.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	return result

func menu_button(parent: Node, text: String, action: Callable, filled := false) -> Button:
	var b: Button = ui.button(parent, text, action)
	b.custom_minimum_size.y = 58 if filled else 46
	b.add_theme_font_size_override("font_size", 18 if filled else 15)
	for state in ["normal", "hover", "pressed", "focus"]:
		var bg := RED if filled else NIGHT
		if state == "hover": bg = RED.lightened(0.16) if filled else Color("405449")
		if state == "pressed": bg = RED.darkened(0.16) if filled else Color("15221c")
		if state == "focus": bg = Color.TRANSPARENT
		var border := 2 if state == "focus" else (0 if filled else 1)
		var box: StyleBoxFlat = ui.style(bg, 3, border, AMBER if state == "focus" else Color(CREAM, 0.23))
		box.content_margin_top = 10
		box.content_margin_bottom = 10
		b.add_theme_stylebox_override(state, box)
	for state in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color"]:
		b.add_theme_color_override(state, CREAM)
	return b

func chapter(number: String, year: String, heading: String, date: String, description: String, action_text: String, action: Callable, restart: Callable, accent: Color) -> Button:
	var card := PanelContainer.new()
	card.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var box: StyleBoxFlat = ui.style(CREAM, 3, 1, Color(accent, 0.4))
	box.border_width_top = 3
	box.content_margin_left = 30
	box.content_margin_right = 30
	box.content_margin_top = 24
	box.content_margin_bottom = 24
	card.add_theme_stylebox_override("panel", box)
	chapter_row.add_child(card)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 10)
	card.add_child(v)
	ui.label(v, "CHAPTER " + number, 11, accent)
	ui.label(v, year, 64, accent, true)
	ui.label(v, heading, 26, NIGHT, true).autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	ui.label(v, date, 11, NIGHT)
	ui.paragraph(v, description, 16, Color("526057"))
	ui.fill(v)
	var b := menu_button(v, action_text + "  →", action, true)
	if restart.is_valid():
		ui.text_button(v, "Restart " + year, restart, NIGHT, 14)
	return b

func layout() -> void:
	if not is_instance_valid(home): return
	var compact := size.y < 600
	var narrow := size.x < 600
	title.add_theme_font_size_override("font_size", 56 if compact or narrow else 96)
	discovery.add_theme_font_size_override("font_size", 17 if compact or narrow else 27)
	subtitle.visible = not compact
	title_gap.visible = not compact
	title_stack.position = Vector2(20, size.y * (0.035 if compact else 0.07))
	title_stack.set_deferred("size", Vector2(size.x - 40, 0))
	var action_width := minf(310, size.x - 48)
	actions.size = Vector2(action_width, 0)
	actions.position = Vector2((size.x - action_width) / 2, (size.y - actions.get_combined_minimum_size().y) / 2)
	var mascot_height := minf(size.y * 0.60, size.x * 0.38)
	if narrow: mascot_height = minf(size.y * 0.32, size.x * 0.85)
	mascot_height *= 0.85
	mascot.size = Vector2(mascot_height * 2.0 / 3.0, mascot_height)
	mascot.position = Vector2(size.x - mascot.size.x - 20, size.y - mascot_height - (48 if compact else 60))
	if narrow: mascot.position.x = (size.x - mascot.size.x) / 2

	credits.visible = not compact
	credits.position = Vector2(12, size.y - 62)
	credits.size.x = size.x - 24
	credits.add_theme_font_size_override("font_size", 9 if narrow else 11)
	art_note.position = Vector2(12, size.y - 34)
	art_note.size = Vector2(size.x - 24, 22)
	chapter_row.vertical = size.x < 700
	chapter_heading.add_theme_font_size_override("font_size", 28 if compact or narrow else 42)
	var side := int(maxf(20, (size.x - 940) / 2))
	for edge in ["left", "right"]:
		chapter_margin.add_theme_constant_override("margin_" + edge, side)
	for edge in ["top", "bottom"]:
		chapter_margin.add_theme_constant_override("margin_" + edge, 18 if compact else 40)

func show_chapters() -> void:
	home.hide()
	browser.show()
	first_chapter.grab_focus()

func show_home() -> void:
	browser.hide()
	home.show()
	chapter_button.grab_focus()

func _input(event: InputEvent) -> void:
	if is_instance_valid(browser) and browser.visible and event.is_action_pressed("ui_cancel"):
		show_home()
		get_viewport().set_input_as_handled()
