extends RefCounted
## Historical milestones are factual; Sparky, neighbours and their dialogue are fiction.
## Only the 1965 chapter is implemented while its gameplay is under review.

const SOURCES = [
	["Original press-conference footage · Wikimedia Commons", "https://commons.wikimedia.org/wiki/File:Lee_Kuan_Yew%27s_press_conference_on_9_Aug_1965.webm"],
	["English caption contributors · Wikimedia Commons", "https://commons.wikimedia.org/wiki/TimedText:Lee_Kuan_Yew%27s_press_conference_on_9_Aug_1965.webm.en.srt"],
	["Independence · Parliament of Singapore", "https://www.parliament.gov.sg/history/historical-development"],
	["Merger and separation · National Library Board", "https://biblioasia.nlb.gov.sg/all-sections/vol-12-issue-3-oct-dec-2016-law-of-the-land/"],
	["The Albatross File · National Library", "https://exhibitions.nlb.gov.sg/thealbatrossfile/about/"],
	["Early public housing · National Heritage Board", "https://www.roots.gov.sg/places/places-landing/Places/landmarks/my-queenstown-heritage-trail/the-first-hdb-blocks-the-hdb-terraces"],
	["History of void decks · National Heritage Board", "https://www.nhb.gov.sg/~/media/nhb/files/resources/publications/ebooks/nhb_ebook_void_decks.pdf"],
	["Housing in the early years · National Library Board", "https://biblioasia.nlb.gov.sg/all-sections/vol-12-issue-3-oct-dec-2016-public-housing-private-lives/"],
	["Jurong industrial development · National Library Board", "https://curiocity.nlb.gov.sg/digital-stories/jurong/jurong-industrial-estate-development/"],
	["Foreign relations milestones · Ministry of Foreign Affairs", "https://www.mfa.gov.sg/about-mfa/histories-and-milestones/"],
]

# Fictional present-day dialogue in August 1965; later events belong in the notes.
# Uncle Tan speaks everyday Singapore English with a little Hokkien and Malay, kept readable for learners.
const REFLECTIONS = {
	"homes": {
		"voice": "res://assets/voice/homes.mp3",
		"question": "Will everyone have a home?",
		"answer": "My cousin still staying in an attap house in the kampong. One fire, everything gone, you know.\n\nNow HDB building flats, one block after another. Independent or not, people still need a roof over their heads.",
		"tag": "History note",
		"note": "HDB was formed in 1960 and was already building flats before independence.",
		"source": "National Library Board",
	},
	"jobs": {
		"voice": "res://assets/voice/jobs.mp3",
		"question": "Where will people find work?",
		"answer": "They clearing the swamp at Jurong to build factories. But so many young people finishing school... where got enough jobs for everybody?\n\nMy son also still looking. Everybody needs a rice bowl.",
		"tag": "History note",
		"note": "Work on Jurong Industrial Estate began in 1961, before independence.",
		"source": "National Library Board",
	},
	"future": {
		"voice": "res://assets/voice/future.mp3",
		"question": "What happens to Singapore now?",
		"answer": "Such a small island. Even our water comes from Johor. People keep asking, how to survive?\n\nI also don't know, Sparky. But Chinese, Malay, Indian, everybody here is in the same boat. Must jaga each other.",
		"tag": "What followed",
		"note": "Singapore set up its Ministry of Foreign Affairs in August 1965 and joined the United Nations on 21 September 1965.",
		"source": "Ministry of Foreign Affairs",
	},
}

## After the footage, before the questions.
const AFTER_BROADCAST := "Wah... even Mr Lee also cannot hold back. You saw or not?\n\nSo that's it. From today, Singapore is on our own. What's on your mind, Sparky?"
## After Sparky thanks him; completes the chapter.
const FAREWELL := "Okay lah, cannot think so much in one day. Come, have some kopi first.\n\nThank you ah, Sparky. Because of you, the whole block could watch together."

## The road to 9 August, for the journal.
const TIMELINE = [
	["16 Sep 1963", "Singapore joins the new Federation of Malaysia."],
	["Jul & Sep 1964", "Racial riots break out, deepening tensions."],
	["9 Aug 1965", "Separation. Singapore becomes an independent nation."],
]

## What Sparky writes in the journal once each step is done, in order.
const JOURNEY = [
	["Met Uncle Tan outside the shops", "The TV under the block could not get a clear picture."],
	["Found the spare antenna", "Few families had their own television, so neighbours often watched together."],
	["Fixed and tuned the TV", "Snow, then a picture, then the whole block crowding onto the benches."],
	["Watched the announcement", "Mr Lee Kuan Yew spoke about the separation. Some neighbours cried."],
]

static func chapter() -> Dictionary:
	return {
		"year": "1965", "date": "9 AUGUST 1965", "title": "A nation of our own",
		"place": "Under the block, in a neighbourhood like many others", "short": "Independence",
		"intro": "Singapore has just become independent.\n\nHelp Sparky fix the neighbours’ TV so everyone can watch the news together.",
		"fact": "Singapore became a sovereign, independent nation on 9 August 1965. Independence brought urgent questions about jobs, defence and relations with other countries.",
		"background": "Singapore joined Malaysia in 1963. Political and economic disagreements strained relations, and racial riots in 1964 deepened tensions. Negotiations among leaders led to separation in 1965; the outcome cannot be reduced to a single disagreement.",
		"bridge": "Independence was the start of a new task. Singapore had to build its economy, make friends abroad and strengthen its defence. Homes and industry, already underway before 1965, stayed priorities.",
		"tasks": [
			# Keep recorded dialogue and subtitles in sync; settings are in assets/voice/README.md.
			{"id": "neighbour", "name": "Talk to Uncle Tan", "kind": "person", "at": Vector3(-5, 0, 15.5), "speaker": "Uncle Tan", "voice": "res://assets/voice/neighbour_01.mp3", "text": "Eh, Sparky! Got important news today. Everyone coming to watch, but the TV cannot receive properly.\n\nCan help me bring the spare antenna from the table? We all want to hear the announcement together. Aiyoh... so much happening today. Don't know what comes next."},
			{"id": "aerial", "name": "Get the antenna", "kind": "aerial", "at": Vector3(11.5, 0, 1.9), "speaker": "The spare antenna", "text": "Found it! Bring the antenna to the TV. Everyone is waiting."},
			{"id": "television", "name": "Fix the TV", "kind": "tv", "at": Vector3(0, 0, -5.7), "speaker": "Television"},
		],
	}
