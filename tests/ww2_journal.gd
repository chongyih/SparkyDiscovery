extends SceneTree
var failures := 0
func _initialize() -> void: call_deferred("run")
func check(value: bool, description: String) -> void:
	print(("PASS: " if value else "FAIL: ") + description)
	if not value: failures += 1
func run() -> void:
	var ui = load("res://game/interface.gd").new()
	root.add_child(ui)
	var chapter: Dictionary = load("res://game/ww2.gd").WAR_CHAPTER
	for size in [Vector2i(1440, 900), Vector2i(844, 390), Vector2i(390, 844)]:
		root.size = size
		for progress in [0, 4]:
			ui.show_journal(chapter, progress, load("res://game/ww2_journal.gd").SOURCES, func(): pass)
			await process_frame
			await process_frame
			check(ui.journal_page_count == (2 if size.x == 1440 else 1), "Journal adapts to %s" % size)
			for key in ui.JOURNAL_PAGES:
				ui.open_page(key)
				for toggle in ui.overlay.find_children("HistoryDetails*", "Button", true, false): toggle.button_pressed = true
				await process_frame
				await process_frame
				var close: Control = ui.overlay.find_child("CloseJournal", true, false)
				var transform := root.get_final_transform() * close.get_global_transform_with_canvas()
				var bounds := Rect2(transform.origin, close.size * transform.get_scale())
				check(bounds.end.y <= size.y + 1 and bounds.end.x <= size.x + 1, "%s keeps close visible at %s" % [key, size])
				var text := ""
				for label in ui.overlay.find_children("*", "Label", true, false): text += label.text
				check(not "broadcast" in text.to_lower(), "%s contains only wartime content" % key)
				if key == "credits":
					check("Kelvin" in text and "Lilian" in text, "Credits name both wartime voices")
	ui.queue_free()
	await process_frame
	print("JOURNAL FAILURES: ", failures)
	quit(1 if failures else 0)
