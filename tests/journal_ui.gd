extends SceneTree
## Focused journal navigation and optional-history checks. Add -- --capture for PNGs.
const Interface = preload("res://game/interface.gd")
const History = preload("res://game/history.gd")
var failures := 0

func _initialize() -> void:
	call_deferred("run")

func check(value: bool, description: String) -> void:
	print(("PASS: " if value else "FAIL: ") + description)
	if not value:
		failures += 1

func run() -> void:
	root.size = Vector2i(1440, 900)
	var ui := Interface.new()
	root.add_child(ui)
	for progress in 4:
		ui.show_journal(History.chapter(), progress, History.SOURCES, func(): pass)
		await process_frame
		await process_frame
		check(ui.journal_spread == 0, "Journal opens on adventure at checkpoint %d" % progress)
		check(ui.overlay.find_child("CloseJournal", true, false) != null, "Journal has a close action")
		if progress >= 2:
			var toggle: Button = ui.overlay.find_child("HistoryDetails", true, false)
			var details := toggle.get_parent().get_child(toggle.get_index() + 1)
			check(not details.visible, "Extra history starts collapsed")
			toggle.button_pressed = true
			check(details.visible, "Extra history opens on request")
			await process_frame
			await process_frame
			check(ui.overlay.find_child("CloseJournal", true, false).get_global_rect().end.y <= 900, "Expanded memories fit on screen")
			toggle.button_pressed = false
		if OS.get_cmdline_user_args().has("--capture"):
			await create_timer(0.3).timeout
			RenderingServer.force_draw(false)
			root.get_texture().get_image().save_png("/tmp/sparky-journal-%d.png" % progress)
		ui.open_page("before")
		await process_frame
		await process_frame
		var toggles := ui.overlay.find_children("HistoryDetails*", "Button", true, false)
		check(toggles.size() == (4 if progress == 3 else 1), "Topics unlock only after the broadcast")
		for toggle in toggles:
			toggle.button_pressed = true
			var detail := toggle.get_parent().get_child(toggle.get_index() + 1)
			check(detail.visible, "Historical details expand")
		await process_frame
		await process_frame
		check(ui.overlay.find_child("CloseJournal", true, false).get_global_rect().end.y <= 900, "All expanded topics keep close action visible")
		check(ui.journal_pages[1].size.x <= 480, "Topic details do not widen the book")
		if OS.get_cmdline_user_args().has("--capture"):
			await create_timer(0.3).timeout
			RenderingServer.force_draw(false)
			root.get_texture().get_image().save_png("/tmp/sparky-history-expanded-%d.png" % progress)
		for toggle in toggles:
			toggle.button_pressed = false
		if OS.get_cmdline_user_args().has("--capture"):
			await create_timer(0.3).timeout
			RenderingServer.force_draw(false)
			root.get_texture().get_image().save_png("/tmp/sparky-history-%d.png" % progress)
		ui.open_page("real")
		check(ui.journal_spread == 2, "History and sources remain accessible")
		ui.open_page("controls")
		check(ui.journal_spread == 3, "Controls and credits remain accessible")
	for window_size in [Vector2i(390, 844), Vector2i(844, 390), Vector2i(768, 1024)]:
		root.size = window_size
		await process_frame
		await process_frame
		ui.show_journal(History.chapter(), 3, History.SOURCES, func(): pass)
		check(ui.journal_page_count == 1, "Small screens show one page")
		for page_id in ui.JOURNAL_PAGES:
			ui.open_page(page_id)
			await process_frame
			await process_frame
			check(ui.journal_spread == ui.JOURNAL_PAGES.find(page_id), "Single-page links reach " + page_id)
			var close: Control = ui.overlay.find_child("CloseJournal", true, false)
			var screen_transform := root.get_final_transform() * close.get_global_transform_with_canvas()
			var bounds := Rect2(screen_transform.origin, close.size * screen_transform.get_scale())
			check(bounds.end.x <= root.size.x + 1 and bounds.end.y <= root.size.y + 1, "Close stays on screen: " + page_id)
			if OS.get_cmdline_user_args().has("--capture") and page_id in ["day", "after"]:
				await create_timer(0.3).timeout
				RenderingServer.force_draw(false)
				root.get_texture().get_image().save_png("/tmp/sparky-mobile-%s-%d.png" % [page_id, window_size.x])
		ui.turn_page(1)
		check(ui.journal_spread == 7, "Last single page clamps next")
		ui.open_page("title")
		ui.turn_page(-1)
		check(ui.journal_spread == 0, "First single page clamps previous")
		var voice := AudioStreamPlayer.new()
		root.add_child(voice)
		voice.stream = load("res://assets/voice/pages/neighbour_01/03.mp3")
		ui.show_dialogue("Uncle Tan", "Can help me bring the spare antenna from the table? We all want to hear the announcement together.", func(): pass, voice, {}, false, 3, 4, func(): pass)
		await process_frame
		await process_frame
		for button_name in ["PreviousDialogue", "NextDialogue", "DialoguePageCount"]:
			var control: Control = ui.overlay.find_child(button_name, true, false)
			var transform := root.get_final_transform() * control.get_global_transform_with_canvas()
			var bounds := Rect2(transform.origin, control.size * transform.get_scale())
			check(bounds.position.x >= 0 and bounds.position.y >= 0 and bounds.end.x <= root.size.x + 1 and bounds.end.y <= root.size.y + 1, "Dialogue action fits: " + button_name)
		if OS.get_cmdline_user_args().has("--capture"):
			await create_timer(0.3).timeout
			RenderingServer.force_draw(false)
			root.get_texture().get_image().save_png("/tmp/sparky-dialogue-%d.png" % window_size.x)
		voice.queue_free()
		ui.show_journal(History.chapter(), 3, History.SOURCES, func(): pass)
	ui.open_page("after")
	root.size = Vector2i(1440, 900)
	await process_frame
	await process_frame
	check(ui.journal_page_count == 2 and ui.journal_spread == 1, "Resize preserves the open topic spread")
	ui.show_dialogue("Uncle Tan", History.REFLECTIONS.homes.answer, func(): pass, null, History.REFLECTIONS.homes)
	check(ui.overlay.find_child("HistoryDetails", true, false) != null, "Dialogue offers optional historical context")
	var focused := root.gui_get_focus_owner()
	ui.show_memory_notice(2)
	check(root.gui_get_focus_owner() == focused, "Memory notice does not steal focus")
	await create_timer(4.6).timeout
	check(not is_instance_valid(ui.memory_notice), "Memory notice disappears on its own")
	ui.show_memory_notice(1)
	ui.clear_overlay()
	check(ui.memory_notice == null, "Changing screens cancels a memory notice")
	ui.queue_free()
	await process_frame
	quit(1 if failures else 0)
