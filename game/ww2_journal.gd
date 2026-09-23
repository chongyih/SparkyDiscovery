extends RefCounted
## Chapter-specific content; layout, navigation and focus are shared with 1965.
const SOURCES := [
	["NHB · World War Two", "https://www.roots.gov.sg/stories-landing/stories/world-war-ii/story"],
	["National Museum · Fall of Singapore", "https://www.nhb.gov.sg/nationalmuseum/-/media/nms2024/documents/media-releases/220128-dislocations-memory-meaning-fall-of-singapore.pdf"],
]

static func render(ui, page: VBoxContainer, key: String) -> void:
	var progress: int = ui.journal_data.progress
	match key:
		"title":
			ui.page_heading(page, "SPARKY’S JOURNAL", "A place together")
			ui.label(page, "Singapore · 12 February 1942", 18, ui.TEAL)
			ui.gap(page, 14)
			ui.label(page, "What’s next?" if progress < 4 else "Inside at last", 26, ui.INK, true)
			ui.paragraph(page, ui.journal_data.chapter.tasks[progress].name if progress < 4 else "Mei shared the water. Uncle Tan stayed beside me.", 24)
			ui.paragraph(page, "Follow the gold marker." if progress < 4 else "My hands were still shaking. I wasn’t alone.", 18, ui.MUTED)
			ui.gap(page, 18)
			ui.rule(page)
			ui.label(page, "Curious?", 22, ui.INK, true)
			ui.text_button(page, "How did the fighting reach Singapore? →", func(): ui.open_page("before"))
			ui.text_button(page, "What happened next? →", func(): ui.open_page("after"))
			ui.fill(page)
			ui.text_button(page, "About the history →", func(): ui.open_page("real"))
			ui.text_button(page, "How to play & credits →", func(): ui.open_page("controls"))
		"day":
			ui.page_heading(page, "MY MEMORIES", "People who helped")
			if progress == 0:
				ui.label(page, "A new page…", 26, ui.INK, true)
				ui.paragraph(page, "Find Uncle Tan to begin.", 21)
			var entries := [
				["Uncle Tan", "He was getting a shelter ready."],
				["Mei’s request", "The neighbours needed drinking water."],
				["The siren", "We heard a blast. Mei called us inside."],
				["Together", "Mei helped a neighbour. Uncle Tan put a hand on my shoulder."],
			]
			for i in mini(progress, 4):
				ui.gap(page, 8)
				var words = ui.illustrated_row(page, "uncle-tan" if i == 0 or i == 3 else "homes", 54)
				ui.label(words, entries[i][0], 22, ui.INK, true)
				ui.paragraph(words, entries[i][1], 19)
			ui.fill(page)
			ui.paragraph(page, "Sparky’s memories are part of our imagined story.", 15, ui.MUTED)
		"before":
			ui.page_heading(page, "FEBRUARY 1942", "Fighting reaches the island")
			ui.paragraph(page, "Japanese forces advanced down Malaya and crossed the Johor Strait.", 22)
			ui.optional_note(page, "Where did they land?", {"tag": "8 February", "note": "The main landings on Singapore’s northwest coast began on 8 February 1942."})
			ui.optional_note(page, "Were the guns pointing the wrong way?", {"tag": "A closer look", "note": "Some coastal guns could fire inland and did so. The defeat cannot be explained simply by saying the guns pointed the wrong way."})
			ui.fill(page)
			ui.text_button(page, "Read the sources →", func(): ui.open_page("sources"))
		"after":
			ui.page_heading(page, "1942–1945", "The Occupation")
			ui.paragraph(page, "British-led forces surrendered on 15 February 1942. The Japanese Occupation followed, lasting until 1945.", 22)
			ui.optional_note(page, "Everyday life", {"tag": "Shortages", "note": "Civilians faced shortages and fear. People grew food, found substitutes and helped neighbours survive."})
			ui.optional_note(page, "Persecution and loss", {"tag": "Remembering", "note": "Japanese forces carried out persecution and mass killings. During Sook Ching, many Chinese civilians were taken away and killed. These losses remain part of Singapore’s wartime memory."})
			ui.optional_note(page, "After 1945", {"tag": "Recovery", "note": "The Occupation ended in 1945. Recovery took time."})
		"sources":
			ui.page_sources(page)
		"real":
			ui.page_heading(page, "REAL AND IMAGINED", "What is real here?")
			ui.label(page, "THE HISTORY", 12, ui.TEAL)
			ui.paragraph(page, "The invasion, surrender and Occupation follow the sources in this journal.", 20)
			ui.label(page, "OUR STORY", 12, ui.TEAL)
			ui.paragraph(page, "Sparky, Uncle Tan, Mei, their dialogue and this street are fictional. The nearby blast is not a reconstruction of a particular raid. Sparky’s outfit is stylised.", 20)
		"controls":
			ui.page_controls(page)
			ui.optional_note(page, "Sound and effects", {"tag": "Your settings", "note": "Sound and reduced blast effects are in Pause during exploration. Scripted sequences play through without skip or pause controls."})
		"credits":
			ui.page_heading(page, "CREDITS", "Thank you")
			ui.paragraph(page, "Sparky uses the supplied Blender model. Built with Godot Engine (MIT licence).", 18)
			ui.optional_note(page, "Sound credits", {"tag": "Modern recordings", "note": "Siren: Techtonic, Civil-defense-siren-waver (2008), public domain. Trimmed, volume-adjusted and filtered. Footsteps: Kenney (CC0). Neighbours: Joseph Sardin / BigSoundBank (CC0). Other wartime effects are original synthesis. These are not wartime archival recordings."})
			ui.text_button(page, "Siren source & licence →", func(): OS.shell_open("https://commons.wikimedia.org/wiki/File:Civil-defense-siren-waver.ogg"))
			ui.paragraph(page, "AI voices from ElevenLabs: Uncle Tan — Kelvin; Mei — Lilian (Warm, Calm and Captivating). Other dialogue is presented as text.", 17, ui.MUTED)
