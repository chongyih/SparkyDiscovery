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
const REFLECTIONS = {
	"homes": {
		"question": "Will everyone have a home?",
		"answer": "People still need a safe place to live, Sparky. HDB has been building flats for several years already. Becoming independent doesn't finish that work.\n\nA home means a lot. Somewhere to rest, bring up children, and get to know your neighbours.",
		"note": "HISTORY NOTE · HDB was formed in 1960. Public-housing construction was already underway before independence. Source: National Library Board; links in the journal.",
	},
	"jobs": {
		"question": "Where will people find work?",
		"answer": "A home needs a livelihood too. Factories are opening in Jurong, but finding enough work is still a big worry.\n\nPeople need a chance to earn a living. We have to keep working at that, together.",
		"note": "HISTORY NOTE · Development of Jurong Industrial Estate began in 1961, before independence. Source: National Library Board; links in the journal.",
	},
	"future": {
		"question": "What happens to Singapore now?",
		"answer": "We're a country on our own now. We need friends abroad, and we need to look after one another here.\n\nI can't tell you how everything will turn out. We start with today, lah.",
		"note": "WHAT FOLLOWED · Singapore established its Ministry of Foreign Affairs in August 1965 and joined the United Nations on 21 September 1965. Source: MFA; links in the journal.",
	},
}

static func chapter() -> Dictionary:
	return {
		"year": "1965", "date": "9 AUGUST 1965", "title": "A nation of our own",
		"place": "A neighbourhood television corner", "short": "Independence",
		"intro": "On 9 August 1965, Singapore separated from Malaysia and became a sovereign, independent nation.\n\nAfter political and economic tensions and negotiations between leaders, the future had changed. Help neighbours gather around a television to learn what has happened.",
		"fact": "Singapore became a sovereign, independent nation on 9 August 1965. Independence brought urgent questions about the economy, defence and relations with other countries.",
		"bridge": "Independence is the beginning of a new task. Singapore must build its economy, establish international relationships and strengthen its defence. Homes and industrial development, already underway before 1965, remain priorities.",
		"tasks": [
			{"id": "neighbour", "name": "Speak to Uncle Tan", "kind": "person", "at": Vector3(-5, 0, 15.5), "speaker": "Uncle Tan", "voice": "res://assets/voice/neighbour_01.mp3", "text": "Eh, Sparky! Got important news today. Everyone coming to watch, but the TV cannot receive properly.\n\nCan help me bring the spare aerial from the table? We all want to hear the announcement together. Aiyoh... so much happening today. Don't know what comes next."},
			{"id": "aerial", "name": "Collect the spare television aerial", "kind": "aerial", "at": Vector3(11.5, 0, 1.9), "speaker": "Getting a clear picture", "text": "Sparky picks up the spare aerial. Televisions could bring neighbours together to follow major events.\n\nTake it to the television corner and adjust the signal. The neighbours are waiting to learn what this day will mean for their home."},
			{"id": "television", "name": "Tune the television for the announcement", "kind": "tv", "at": Vector3(0, 0, -5.7), "speaker": "9 August 1965 · Independence", "text": "Singapore has separated from Malaysia and is now a sovereign, independent nation. Prime Minister Lee Kuan Yew speaks emotionally about the separation at a televised press conference.\n\nThe neighbours listen. There is hope, but also uncertainty: how will this small country provide jobs, defend itself and find its place in the world?"},
		],
	}
