extends SceneTree
## Title/chapter navigation, saved-game actions and responsive keyboard access.
const Interface = preload("res://game/interface.gd")
var failures := 0
var selected := ""

func _initialize() -> void:
	call_deferred("run")

func check(value: bool, description: String) -> void:
	print(("PASS: " if value else "FAIL: ") + description)
	if not value:
		failures += 1

func find_button(ui: CanvasLayer, prefix: String) -> Button:
	for node in ui.overlay.find_children("*", "Button", true, false):
		if node.text.begins_with(prefix):
			return node
	return null

func settle() -> void:
	for i in 8:
		await process_frame

func run() -> void:
	check_save_order()
	var viewport := SubViewport.new()
	viewport.size = Vector2i(1440, 900)
	root.add_child(viewport)
	var ui := Interface.new()
	viewport.add_child(ui)
	for saved in [false, true]:
		ui.show_menu(func(): selected = "start", func(): selected = "journal", func(): selected = "resume", saved, func(): selected = "journey", func(): selected = "wartime", saved, func(): selected = "latest")
		await settle()
		var launch = ui.overlay.find_child("LaunchMenu", true, false)
		check(launch.home.visible and not launch.browser.visible, "Title opens before chapter browser")
		check(launch.mascot.texture != null, "Sparky plush portrait is loaded")
		for control in [launch.chapter_button, launch.find_child("LaunchJournal", true, false)]:
			for state in ["normal", "hover", "pressed"]:
				check(is_equal_approx(control.get_theme_stylebox(state).bg_color.a, 1.0), "%s stays opaque in %s state" % [control.text, state])
		check(launch.mascot.is_processing(), "Welcome motion is active on the title")
		launch.primary.pressed.emit()
		check(not launch.browser.visible and selected == ("latest" if saved else "journey"), "Primary action starts or resumes directly without chapter selection")
		launch.show_chapters()
		check(not launch.mascot.is_processing(), "Chapter browser suspends welcome motion")
		var first := find_button(ui, "Continue 1942" if saved else "Begin in 1942")
		var second := find_button(ui, "Continue 1965" if saved else "Step into 1965")
		check(first != null and second != null, "Both chapters available (saved=%s)" % saved)
		first.pressed.emit()
		check(selected == ("wartime" if saved else "journey"), "1942 action uses correct callback")
		second.pressed.emit()
		check(selected == ("resume" if saved else "start"), "1965 action uses correct callback")
		if saved:
			find_button(ui, "Restart 1942").pressed.emit()
			check(selected == "journey", "1942 restart stays available")
			find_button(ui, "Restart 1965").pressed.emit()
			check(selected == "start", "1965 restart stays available")
		for dimensions in [Vector2i(1440, 900), Vector2i(1024, 768), Vector2i(844, 390), Vector2i(390, 844)]:
			viewport.size = dimensions
			launch.show_home()
			await settle()
			check(absf(launch.actions.get_global_rect().get_center().x - dimensions.x / 2.0) < 1 and absf(launch.actions.get_global_rect().get_center().y - dimensions.y / 2.0) < 1, "Main controls are centred at %s" % dimensions)
			check(not launch.actions.get_global_rect().intersects(launch.mascot.get_global_rect()), "Sparky stays clear of the main controls at %s" % dimensions)
			check(launch.primary.get_global_rect().end.y < dimensions.y and launch.primary.get_global_rect().position.x >= 0, "Primary action fits at %s" % dimensions)
			check(launch.title_stack.get_global_rect().end.y <= launch.actions.position.y, "Title and actions do not overlap at %s" % dimensions)
			check(launch.actions.get_global_rect().end.y <= launch.art_note.position.y, "Actions do not overlap footer at %s" % dimensions)
			launch.show_chapters()
			await settle()
			var scroll: ScrollContainer = launch.chapter_scroll
			check(scroll.get_h_scroll_bar().max_value <= scroll.size.x, "No chapter browser horizontal overflow at %s" % dimensions)
			for target in [first, second, find_button(ui, "Back")]:
				if target == null: target = ui.overlay.find_child("BackToTitle", true, false)
				target.grab_focus()
				await settle()
				check(target.get_global_rect().position.y >= 0 and target.get_global_rect().end.y <= dimensions.y, "Keyboard focus reveals %s at %s" % [target.text, dimensions])
		launch.show_home()
		check(launch.home.visible and not launch.browser.visible, "Back returns to title")
		check(launch.mascot.is_processing(), "Returning to the title resumes the welcome")
		find_button(ui, "Journal").pressed.emit()
		check(selected == "journal", "Journal action remains available")

	for state in [{"wartime": true, "independence": false, "expected": "wartime"}, {"wartime": false, "independence": true, "expected": "resume"}]:
		ui.show_menu(func(): selected = "start", func(): selected = "journal", func(): selected = "resume", state.independence, func(): selected = "journey", func(): selected = "wartime", state.wartime)
		var launch = ui.overlay.find_child("LaunchMenu", true, false)
		launch.primary.pressed.emit()
		check(selected == state.expected, "A single save resumes its chapter directly")
	ui.show_menu(func(): selected = "start", func(): selected = "journal", func(): selected = "resume", true, func(): selected = "journey", func(): selected = "wartime", true, func(): selected = "latest", true)
	var completed_menu = ui.overlay.find_child("LaunchMenu", true, false)
	check(completed_menu.primary.text.begins_with("Begin journey"), "Finished journey offers a new beginning")
	completed_menu.primary.pressed.emit()
	check(selected == "journey", "Finished journey starts fresh in 1942")
	completed_menu.show_chapters()
	check(find_button(ui, "Continue 1965") != null, "Chapter selection retains completed chapter access")
	ui.queue_free()
	await process_frame
	print("LAUNCH UI: %d failures" % failures)
	quit(1 if failures else 0)

func check_save_order() -> void:
	var progress = preload("res://game/journey_progress.gd")
	var prefix := "/tmp/sparky-save-order-%s" % Time.get_ticks_usec()
	var independence := prefix + "-1965.cfg"
	var wartime := prefix + "-1942.cfg"
	check(progress.latest(independence, wartime).is_empty(), "No saves offers a new journey")
	var config := ConfigFile.new()
	config.set_value("progress", "task", 2)
	config.set_value("progress", "last_played", 100.0)
	config.save(independence)
	check(progress.latest(independence, wartime) == "1965", "A sole 1965 save is selected")
	config.set_value("progress", "last_played", 200.0)
	config.save(wartime)
	check(progress.latest(independence, wartime) == "1942", "Latest activity selects 1942 when both saves exist")
	config.set_value("progress", "last_played", 300.0)
	config.set_value("progress", "task", 3)
	config.save(independence)
	check(progress.finished(independence, wartime), "Finishing the final chapter completes the journey")
	config.set_value("progress", "task", 0)
	config.set_value("progress", "last_played", 400.0)
	config.save(wartime)
	check(not progress.finished(independence, wartime), "Starting again in 1942 makes the new journey resumable")
	config.set_value("progress", "task", 4)
	config.save(wartime)
	check(not progress.finished(independence, wartime), "Finishing 1942 alone still offers continuation into 1965")
	config.set_value("progress", "task", 99)
	config.save(wartime)
	check(progress.latest(independence, wartime) == "1965", "Invalid checkpoints are not offered for continuation")
	config.set_value("progress", "task", 1)
	config.erase_section_key("progress", "last_played")
	config.save(wartime)
	check(progress.read(wartime, 4).last_played == float(FileAccess.get_modified_time(wartime)), "Legacy saves fall back to file modification time")
	DirAccess.remove_absolute(independence)
	DirAccess.remove_absolute(wartime)
