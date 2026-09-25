# Sparky Discovery (Three.js) — Design & Asset Contract

Browser game (Vite + Three.js r186), must run at 60fps on mid-range phones (landscape).
Three chapters, ~10 minutes total. Chapter 1 (WW2) is built first.

## Audience & presentation
Aimed at kids/teens (≈10–16), also played by adults, and **presented to a panel of judges**. So:
polish and first impressions over feature count; a strong title screen and opening minute; clear
onboarding (controls shown in context, never a wall of text); no dead ends or soft-locks; historically
careful, respectful tone (hardship acknowledged without graphic content); visible sources, a
"what's real vs imagined" page and credits in the album; accessibility (subtitles for all audio,
readable font sizes, reduced-motion/shake option, volume controls, pause anywhere).

**Tone (user direction):** keep the impact. WW2 must convey the severity, fear and uncertainty of
February 1942 — dread under the calm morning, a genuinely frightening raid (a shophouse on the route
is hit, fire, dust, people fleeing), a claustrophobic shelter, and an epilogue that carries real
weight (Sook Ching through implication and absence, hunger, fear). Age-appropriate = no gore, not
softened. A short content note appears before the chapter.

## Agreed plan (brainstorm with the user, 24 Sep 2026)
Brief: open / creative. Balance: **balanced** gameplay and story (tighten walk-and-read sections).

### Framing — Mr. Boon's roll of film + Then & Now
- **Prologue (present day, ~30 s):** a Queenstown HDB void deck. 91-year-old **Mr. Boon** shows Sparky
  his old Brownie box camera. The roll inside holds three photos he has never had developed: "three days
  I could never forget". (Like the letter in Ch3, he has never opened it, because for him opening things
  brings bad news. Sparky takes the 1942 frame; Boon takes the 1965 and 1968 frames.)
- **Then & Now (each chapter, ~20 s):** Sparky stands in the *real place today* and raises the
  Brownie. A ghostly sepia overlay of Mr. Boon's old photo appears in the viewfinder; the player lines
  it up (position, turn, tilt). When it locks, colour drains, and Sparky steps into the past. This also
  teaches the camera controls.
  - 1942: Telok Ayer's conserved shophouses today (cafés, lanterns, tourists) → same street, 12 Feb 1942.
    (A `NOW_` dressing variant of the same street geometry.)
  - 1965: Queenstown today → the early block and kopitiam, 9 Aug 1965.
  - 1967: Taman Jurong Greens park today (the former camp site, 2017 heritage marker) → the camp's
    passing-out parade, 2 Mar 1968.
- **Ending (~50 s, then credits):** see "Ending — the void deck, 2026" below. (NS60 is in 2027.)

### Signature mechanics (all three chapters, kept light)
1. **Viewfinder "Look closer".** Raise the camera any time. Hotspots reveal hidden history; the game
   recognises framed "moments" (target in frame and unobstructed) → album shows memories captured N/M.
2. **Community resilience.** Small optional kindnesses (share water, tie a family's bundles, calm a
   child) are remembered: helped characters reappear later (e.g. at the 1965 TV, the 1967 send-off).
3. **Heirlooms & choices.** One key choice per chapter, no wrong answer. 1942: *"There's room for two
   things in the shelter"*: family photo / rice / Siti's newspaper / Papa's tiffin carrier. Each pays off
   later (photo on the 1965 kopitiam wall; Siti still carries the newspaper in 1965; rice feeds the
   shelter and neighbours remember; tiffin carrier returns in 1967). Unchosen items get a lighter
   fallback so no later scene breaks. 1965: *"Something for the wall"* (newspaper / flag / four-language
   sign / calendar page), paying off in 1967.

### Chapter 1 — "The Fortress Falls" (12–15 Feb 1942, then March) ~4.5 min, trim every beat
0. Prologue 30 s → 1. Then & Now 20 s → 2. Morning papers **2 deliveries** + Look-closer hotspots 45 s →
3. Air raid escort + shophouse hit 60 s → 4. **Shelter choice** (room for two things) 15 s →
5. Blackout search 60 s → 6. Rumours **3 fragments** + newspaper puzzle 40 s → 7. Syonan-to 40 s.

### Chapter 2 — "A Nation Is Born" (Mon 9 Aug 1965) ~2.5 min — agreed with the user, 24 Sep 2026
**Tone: anxiety → resolve.** Independence was unwanted: shock and worry all day (water, jobs,
Konfrontasi still on, family across the Causeway, fear of the 1964 riots returning), turning to quiet
determination at the TV. Not a celebration.

**Siti's arc:** in 1942 she read "It SHALL stand" to the street and was wrong. Now 35 (a teacher on the
afternoon session, so home in the morning), she's asked to explain the news again and is afraid to
promise anything: "Last time I read the news out, I told everyone we'd be safe." She explains anyway,
carefully: "I don't know. But we'll find out together."

**Set (compact):** Boon's kopitiam, a ground-floor shop unit in an early Queenstown block: counter +
kopi urn, ~6 marble tables, Rediffusion/radio, the block's only TV on a high shelf, and **the wall**
(Ah Ma's portrait already hangs there). Plus a short shop-corridor exterior for one errand. (No void
decks yet in 1965.)

**Core mechanic: kopi orders (the "language bridge").** Build a drink in 3 taps: kopi / teh ·
milk (default condensed, **O** none, **C** evaporated) · sugar (normal, *kosong*, *siew dai*,
*ga dai*) · *peng* (iced). A chalk order board teaches the lingo. Kopitiam lingo mixes Hokkien, Malay
and English: proof people already shared a language before they were a nation. Sparky walks drinks to
tables with the normal third-person controls; dialogue happens while serving. **What orders mean
changes each rush:** routine → orders carrying worries → customers ordering *for each other*.

**Beats (~160 s):**
0. Void deck bridge 10 s. Mr. Boon: "1965. I had my own kopitiam by then. And the only television on
   the block!"
1. Then & Now 20 s. Queenstown today → the block, 9 Aug 1965. The block with ground-floor shops is invented;
   the research found no shops in the Stirling Road blocks, so no real block is named.
2. Morning rush 25 s: **1 order** (tutorial), then a moment to chat with the regulars. Everyday 1965 chatter (prices, Konfrontasi, Malaysian
   dollars). Customers sit apart by community.
3. 10 a.m. 15 s: the counter radio (on Radio Singapura's Malay service, for Makcik Rohani's songs) breaks in
   with the Proclamation. It's the real Malay recording, the only 1965 one known to survive. Makcik understands first. Cups stop mid-sip. Boon freezes:
   "Every time the news changes, someone disappears." (His papa, 1942.)
4. Errand 15 s: Boon sends Sparky along the shop corridor to fetch Siti. On the way, ambient rumours
   echo Ch1 ("No more water from tomorrow!", "The army from KL is coming!"). Siti hesitates, then comes.
5. Worries 30 s: Sparky **listens to three worries** (one half-heard in Tamil, translated by Ravi). Siti answers the
   water and bases questions aloud and admits she can't answer the riots one. Boon pours Makcik Rohani's teh-C and Sparky carries
   it over with that honest answer; Auntie Letchumi pats the stool beside her and Makcik smiles back (in the evening they share a table).
   Fact cards: water (the Separation Agreement kept the water deals), the British bases, the riots/jobs.
6. Evening + TV 30 s: the whole block crowds in. One quick **cross-order** (a Hokkien uncle orders
   teh-O ga dai for the Tamil auntie; Boon pours, Sparky delivers). Only the morning order uses the
   counter (playtest: more felt repetitive). Then the press conference: the "moment of anguish" and "This is not a
   Malay nation, this is not a Chinese nation, this is not an Indian nation." Hold on faces.
7. **Choice: something for the wall** 10 s. Boon: "Today needs to go on the wall, bear."
   - the next day's newspaper (Siti's newspaper thread; ST 10 Aug 1965 headline "Singapore is out", confirmed)
   - the state flag (Farid's thread; fact: flag and *Majulah Singapura* already existed since 1959)
   - a new shop sign in four languages (Boon's gesture)
   - the 9 August calendar page, torn off and kept
   Each pays off in 1967 (details in the Ch3 brainstorm).
8. Coda 5 s. Mr. Rajan: "No water of our own. No army. Two battalions." Farid is listening → Ch3.

**Payoffs from Ch1.** Heirlooms: *family photo* → Papa's photo hangs beside Ah Ma's (fallback: Ah Ma's
alone). *Newspaper* → Siti keeps the 1942 front page in her book bag and shows it when she hesitates
(fallback: she mentions it). *Rice* → the Geylang family insists Boon's kopi is on them today
(fallback: a warm nod). *Tiffin carrier* → on Boon's shelf, saved for 1967. Kindnesses: helped
characters appear in the evening crowd with a line.

**Built (branch `ch2-independence`):** set `tools/build_kopitiam.py` → `kopitiam.glb`; cast `tools/build_1965_npcs.py`;
code `src/chapters/ind*.js`. If no family photo was saved in 1942, a red 福 diamond hangs in Papa's frame.
Sparky wears a 1965 kopitiam-helper outfit (`tools/build_sparky_1965.py` → `sparky-ind.glb`): pale-blue cotton shirt,
pencil in the pocket, khaki shorts, canvas shoes, a striped face towel over the shoulder, no hood. Boon's TV is a
1960s walnut table set (curved screen behind a gold mask, speaker grille, rabbit ears) with a CRT shader on the picture.
The Then & Now opens on present-day Queenstown (research §14): the repainted block, parked cars, Dawson-style towers and
an East-West Line train, then the player pans back to the shops.

**Ch3 seeds:** only **Farid (16, helps at the counter)** and **Ravi (Mr. Rajan's son)** are planted:
separate tables all day, side by side on the bench at the TV, not speaking. Ah Hock and the Eurasian
boy are introduced fresh in Ch3.

**LKY footage: the real clip (built).** The 118 s "moment of anguish" excerpt from Wikimedia Commons
("Lee Kuan Yew's press conference on 9 Aug 1965", Singapore Broadcasting Corporation archive, public domain),
converted to H.264 with the archive timecode cropped; Commons captions (CC BY-SA 4.0). Credited on screen while
it plays and in the album; details in `public/assets/video/ATTRIBUTION.md`. The "not a Malay nation…" words follow
as narration from the NAS transcript (they aren't in the excerpt).

**Research:** done, in `docs/research/1965-history.md` (press conference recorded at noon and shown
on TV the same day; ST 10 Aug headline "Singapore is out"; firecrackers in Chinatown confirmed).
Script: `docs/ch2-script.md`. **Still open:** the Tamil lines (placeholders) and a native-speaker
review of all Hokkien, Malay and Tamil; the exact time the press conference aired on TV; clip
timecodes.

### Chapter 3 — "The First Intake" (Aug 1967 → Sat 2 Mar 1968) ~2.5 min — agreed with the user, 25 Sep 2026
**Tone: reluctance → trust.** Lighter than Ch1/Ch2 (drill chaos, starched uniforms, Leo's P.S. are
funny), with Boon's grief underneath. The chapter spans about seven months: enlistment (17–25 Aug 1967
at CMPB Kallang; formal training from 11 Sep, about 25 weeks) to the **passing-out parade on Saturday
2 March 1968 at Taman Jurong Camp**, where Defence Minister Lim Kim San took the salute (confirmed,
NAS photos). The album photo is dated 2 March 1968.

- **Family frame ("good iron isn't made into nails", 好铁不打钉，好男不当兵):** many families were uneasy
  about sons becoming soldiers. Farid (18, Siti's brother, born 1949) is enlisting; Boon (32), like an
  uncle to him, begs him not to go: "My papa went out in a war and never came home." He skips the
  send-off (the "almost" in "that one I almost didn't take"), is turned by Farid's letter, and comes to
  the parade with the Brownie, resolving his 1942 wound. **Sparky is in the photo.**
- **Core mechanic: drill commands (the "command bridge").** SAF foot drill is shouted in Malay
  (*Sedia!*, *Ke kanan… pusing!*, *Dari kiri, cepat jalan!*). For 1967 this is **likely, not proven**
  (no 1967 primary source), so the script uses a few core commands and never claims exact 1967
  wording; exact forms need **[native review]**. A language
  nobody in the section fully shares, which everyone on the square must learn. A direct sequel to
  Ch2's kopi lingo (Farid learned kopi words in 1965; now he teaches Ah Hock the commands).
  **"Wait for the word":** every command is a drawn-out cautionary word (*"Kanaaan…"*) then a sharp
  executive word (*"PUSING!"*); you move only on the executive word. The skill is holding still, then
  moving together. Timing is measured from the executive word, not a metronome: window ≈ ±300 ms
  (also absorbs Bluetooth latency), a closing ring is the main visual cue, and pressing during the
  cautionary word = "jumped the gun". Marching steps are automatic ("kiri… kiri…" sets the cadence; no
  step-tapping). Inputs: *Sedia* = Space; *Kanan / Kiri / Belakang pusing* = → ← ↓ (or D A S);
  *Cepat jalan* = ↑, *Berhenti* = Space; *Pandang kanan* = mouse/drag look. Touch: four big on-screen
  buttons labelled with the Malay words (kiri / belakang / kanan / sedia). Gamepad: d-pad + A.
  No fail state, no score (like the kopi orders); a "Relaxed timing" option and a do-it-for-me assist
  (as in the newspaper puzzle). Album gets a **"Drill words"** glossary card, like the kopi board.
  Played twice:
  - **Day one (~25 s): Ah Hock copies you.** He can't follow the Malay, so he watches Sparky's feet.
    (Real: a 3 SIR recruit's oral history describes a buddy who "could not speak English and Malay";
    they used sign language.)
    Right → he's right; wrong → he turns wrong with you (comedy), sergeant: "Again!" First four commands
    show a direction icon; then "Now without pictures": words only. After two misses Farid whispers the
    meaning and the icon returns. Leo is scripted to jump the gun once.
  - **Passing out (~30 s): you copy Ah Hock.** Words only, band playing, families in the stands, no
    "Again!". If you slip, Ah Hock nudges you back into line and the parade carries on: the trust has
    flipped. The last command, ***Pandang kanan!* (eyes right)**, is the only drill use of the look
    control: the player turns to the reviewing stand and finds Boon there with the Brownie.
  Prototype of the timing and the Ah Hock copy/nudge logic was play-tested in the brainstorm (25 Sep 2026).
  **Bed carry (15 s): the drill rule, taught before the drill.** Recruits carried their own bed and
  cupboard up the barrack stairs (one secondary source, so keep it light). Ah Hock, at the other end of
  the bed frame, counts in Hokkien, *"Tsi̍t… nn̄g… saⁿ!"* **[native review]**, and you heave on *saⁿ!*,
  with the same input (↑ / big touch button), window and ring as the drill. Early or late: the bed bangs
  the wall, Ah Hock grumbles, try again (no fail). It teaches "wait for the word" in a language Sparky
  doesn't speak, from the boy who'll need Sparky's help with Malay; the parade flips it. On the stairs:
  Leo passes, talking nonstop and carrying nothing; Ravi silently carries his own cupboard; Farid bosses
  traffic from the landing ("Left! No, your other left!"). After two heaves Ah Hock gives up waiting,
  lifts the bed alone with Sparky still sitting on it, and carries both up. Card: *"Four floors later."*
  Only one flight of stairs needs building. Night navigation is cut down to a story beat; the obstacle
  course is dropped.
- **The sergeant: Sergeant Osman (placeholder name).** A Malay regular from 1 or 2 SIR, in the army
  since before NS (the first intake was trained by regulars, and Malay Singaporeans served as regulars,
  per the research). Deadpan shouter, secretly kind, every joke one sentence long: "Four boys, four
  directions." To Sparky: "You. Stand on a box." At the parade he gives Sparky one tiny nod, his only
  approval all chapter. In the background of the day-one drill, the Israeli advisers stand in straw hats
  (optional "Mexicans" camera hotspot and fact card).
- **Section of strangers** (Sparky is the fifth member, in `sparky-ns`, and nobody remarks on a bear,
  though the sergeant can joke about his height once):
  - **Farid (Malay):** grown up since Rajan's "Somebody"; wants to lead. Flaw: bosses people.
    Turn: teaches Ah Hock the commands. **Accuracy (decided 25 Sep 2026):** no Malay recruit is
    documented among the first 900, and Lee Kuan Yew said in 2001 that "many Malay Singaporeans were
    not called up" in the early years, though there was "no blanket ban". Farid stays in the section
    as an imagined individual, and dialogue never states a policy reason. The album's real-vs-imagined page
    says it plainly: it isn't known whether any Malay Singaporeans were among the first 900; in the
    early years many were not called up; today every fit man serves, whatever his race or religion.
  - **Ah Hock (Chinese, hawker's son, Hokkien only):** strong, stubborn, homesick. Flaw: can't follow
    the commands and turns the wrong way. Turn: carries the bed alone; his Hokkien P.S. promises Boon he'll look after Farid.
  - **Ravi (Mr. Rajan's son):** still near-silent. Flaw: won't call out the step. Turn: on the night
    exercise he's the only one who can read the map. His first real line in the game.
  - **Leonard "Leo" Pereira (Eurasian):** English-educated, talks nonstop, has seen too
    many war films. Flaw: turns confidently, early, and wrong. Comic relief.
- **Beats (~190 s, about 3 min; the letter scene cost the kopi lesson and 5 s of send-off). To get
  closer to 3 min, trim the day-one drill to 20 s:**
  0. Void deck bridge 10 s: "That one I almost didn't take."
  1. Then & Now 20 s: Taman Jurong Greens park today (the former camp site; 2017 heritage marker)
     → the camp in 1967. **[needs a reference photo of the marker; the research couldn't find one]**
  2. Send-off morning, kopitiam (reuses the Ch2 set) 25 s: Farid has already enlisted at CMPB Kallang
     (papers, one line). Boon refuses, quotes the proverb and his papa, then silently packs **Papa's
     tiffin carrier** and leaves it on the counter for Farid. Ch2 wall payoff (one line).
  3. Send-off 10 s: the community centre. A band, the MP's gift or medal, families at the gate, recruits
     climbing into a military truck (NAS photos, 3 Sep 1967; which intake they show isn't known, so
     it's presented as typical, not as a record). Ch1/Ch2 kindness characters in the crowd. Boon's spot
     is empty.
  4. Day one at Taman Jurong 40 s: the bed carry (15 s), then the first, chaotic drill (25 s) with
     Sergeant Osman. No head-shaving scene.
  5. Night exercise 10 s: Ravi reads the map (his first real line); the section shares the tiffin
     carrier's food.
  5b. **Farid's letter, the P.S. round** 25 s (barrack block at night, normal walking controls). Farid
     is stuck: "How do I tell Abang Boon I'm okay, when he won't believe it?" The player picks his
     opening (no wrong answer; each changes Boon's reaction): *honest* "The first night, I didn't sleep
     at all. I was scared, Abang. Like you said." (Boon: "…Me too.") / *brave* "Don't worry about me.
     I'm fine. Really." (Boon: "He's lying. He always says 'really' when he lies.") / *funny* "Good news:
     I can turn left now. Bad news: Leo still can't." (Boon's first laugh of the chapter). Fixed body:
     four boys who don't talk the same but turn together now; the tiffin carrier fed five on the night
     exercise and Ravi found the way; "The passing-out parade is on Saturday, 2 March. Families can come.
     Please come, Abang. Bring the camera." Sparky then carries the letter down the corridor for a
     P.S. from each buddy (any order), each setting up a parade payoff:
     - **Ah Hock:** Hokkien spelled out by Farid, roughly "Don't be scared, Uncle. I'll look after him."
       **[native review]** → Ah Hock's nudge at the parade.
     - **Ravi:** no words, a small map of the parade square with an X: "Stand here. Best view." → on
       *Pandang kanan!* Boon is standing on the X.
     - **Leo:** "P.P.S. Army food is terrible. Please send more of whatever was in the tiffin. — Leo
       (the handsome one)" → Boon brings the tiffin carrier to the parade, full.
     - **Sparky:** a paw print.
     Optional hotspot: a starched Temasek green uniform standing up by itself (fact card). If the
     player skips buddies, the letter goes with the P.S.s it has; Ravi hands over his map anyway, so
     the parade payoffs never break.
  5c. **The reading** 20 s (kopitiam). The letter has sat unopened on Boon's shelf for three days; for
     him, letters bring bad news. Siti opens it and reads it aloud (voice-over; handwriting appears line
     by line). Her thread ends: wrong news in 1942, careful news in 1965, true, good, personal news in
     1968. She mangles Ah Hock's Hokkien; Boon laughs ("Aiyoh, your Hokkien!"), then, quietly: "He says
     he'll look after him." Only Boon understands it: the language bridge in reverse. The paw print:
     SITI: "And… a paw print?" BOON: "That bear." Boon says nothing more; he takes the Brownie off the
     shelf, winds on the film and looks at the frame counter. SITI: "So use it." Cut to the parade.
  6. Passing-out parade (2 Mar 1968) 30 s: the drill, ending on "Pandang kanan!" as the player finds
     Boon. The Minister takes the salute (Lim Kim San, in the background only). In the stands: Mr. Rajan
     and Siti, and the kindness characters with a line each (families attending is likely: NAS
     captions say "spectators" and "guests"). Boon takes the photo. Farid gives
     back the tiffin carrier, washed: "It came back, Abang. I came back."
  7. Ending: Farid (77) visits Mr. Boon at the void deck, bringing the tiffin carrier.
- **Payoffs.** Ch1 *tiffin carrier* as above (fallback: Boon packs his own new tiffin; same lines).
  Ch2 wall: *newspaper* → Siti reads Farid's call-up letter aloud (the news is true this time);
  *flag* → Farid: "This time I know the song."; *four-language sign* → Boon has painted Farid's name
  on it; *calendar* → Boon tears off the send-off day's page and pins it beside 9 Aug 1965.
- **Fact cards:** about 9,000 registered and 900 went full-time; the Israeli advisers were nicknamed
  "Mexicans" to keep them secret (two NAS oral histories); Temasek green uniforms starched stiff enough
  to stand up; community leaders held about fifty send-off dinners, some with a medal for each recruit.
- **Sets:** one new set: a camp barrack block (stairwell) + parade square, day and night lighting.
  Kopitiam and community-centre road reuse Ch2.
- Setting: first intake, 900 men into 3 SIR & 4 SIR, Taman Jurong Camp (five-storey one-room flat
  blocks converted into barracks; don't call them "JTC flats", since JTC was only set up in 1968), Temasek
  green uniforms. (Chapter 3 does *not* mirror Chapter 1's beats.)
  Research: [docs/research/1967-history.md](research/1967-history.md). Script: [docs/ch3-script.md](ch3-script.md).

**Revised after playtest (user, 25 Sep 2026):**
- **Arrival scene (new, before the bed carry):** the lorry drives into Taman Jurong Camp; Sergeant Osman lines up the section in
  front of it and takes their names (Leo rambles, Ah Hock answers in Hokkien, Ravi barely speaks), so the section is introduced
  before the bed carry. The bed carry now ends with Ah Hock carrying the bed, with Sparky still sitting on it, up the stairs in view.
- **Drill made forgiving and simpler:** every command shows its icon and meaning; the right button counts from just before the
  executive word until 1.8 s after it (3 s with Relaxed drill timing); pressing well before the word is still "jumped the gun";
  after two tries on day one the sergeant lets it go ("Close enough."). Day one has 4 commands (Sedia, Ke kanan, Ke kiri,
  Ke belakang); the parade has 6 (Sedia, Ke kanan, Dari kiri cepat jalan, Pandang kanan, Pandang depan, Berhenti).
  **No voice and no cue sound** (the TTS voice and the drum cue were both removed): the words are on screen; the boots answer.
- **Night exercise removed.** Replaced by **Rifles**: Osman issues M16s from a rack on the square (the player takes one), Ravi's
  first real line (counting rifle parts, as his father counted doors in the blackout), then one command, *Sandang… senjata!*
  (sling arms) **[native/SAF review]**. The tiffin-carrier dinner moves to the barracks, before the letter.
- **Rifles at the passing-out parade:** the section carries M16s upright at the right shoulder (right arm held still, left arm
  swinging). History: the SAF adopted the M16 in the late 1960s (secondary sources); which rifles the first intake carried at
  their parade is not confirmed; the album's real-vs-imagined page says so. No firing anywhere in the game.
- **Ending:** Farid (77) and Irfan are already walking in as the void-deck scene opens.
- **Second playtest (same day):** the bed carry is cut (the section goes from the arrival straight to the next morning's drill);
  the lorry drives off after the arrival; Ravi's rifle-stripping lines are cut; Boon's lines about his papa disappearing are
  cut (the Ch1 tiffin-carrier heirloom stays); in the barracks everyone stands (no floating Sit poses) and Ah Hock stays in
  Farid's room; the starched "standing uniform" prop is removed (it read as a headless man); the parade ends on
  *Seksyen… bersurai!* (dismissed) so the section breaks ranks before Farid steps out to meet Boon. Drill fix: the others now
  always move on the word, even if the player answers a moment early (they used to be left behind).

**Built (branch `ch3-first-intake`, worktree `SparkyDiscovery_ThreeJS-ch3`):** set `tools/build_camp.py` → `camp.glb`
(four areas; `src/chapters/ns-fallback.js` stands in if it's missing); cast `tools/build_1967_npcs.py`; drill + chapter code
`src/chapters/ns*.js`; sounds `tools/build_audio_ns.py` (band march and lorry; the drill has no sound cue).
Debug: `?chapter=ns&beat=morning|sendoff|arrival|stairs|drill|rifles|letter|reading|parade|ending`.

### Ending — the void deck, 2026 (~50 s, then credits) — agreed with the user, 25 Sep 2026
Reuses the prologue set (`voiddeck.glb`) and its playground kids. **Theme:** Boon finally opens the roll
he has never developed, just as Siti opened Farid's letter for him in 1968.
1. **Farid arrives (10 s).** MR. BOON: "He's late. Always late for everything, except parades." Farid
   (77) walks up with the tiffin carrier, full. Since 1968 it has gone back and forth between them:
   "Your turn to fill it." (Fallback if the Ch1 tiffin carrier wasn't chosen: Boon's own 1967 tiffin.)
   With him is his **grandson Irfan (18)**, home on his first book-out in today's
   uniform: NS carrying on, shown and not said.
2. **The envelope (15 s).** FARID: "You asked me to take your roll to the photo shop. Then you phoned
   and said don't. I did anyway." He sets down an envelope of prints. Mr. Boon won't touch it. The
   player opens it: Sparky, the same as Siti with the letter.
3. **Three photos (20 s).** Each fills the screen and develops (reuse `developPhoto`), with one line
   from each old man. The photos show the player's choices (heirloom, the item on the wall, the P.S.s
   collected). Over 1968, FARID: "Look at us. Four boys who couldn't talk to each other." MR. BOON: "And
   a bear."
4. **The fourth photo (5 s).** The grandson takes a phone photo of the two old men and Sparky at the
   table: the album's last page, the only one in colour, which takes the album from the Brownie to a phone.
5. **Last line.** Mr. Boon gives Sparky the Brownie: "Keep it, Sparky. Somebody has to remember. Now it's
   you." (Closes Ch1's "Somebody has to remember.")
6. **Room for more chapters (5 s).** The grandson finds a **second undeveloped roll** in the camera case,
   its label too worn to read. FARID: "Whose is that?" MR. BOON (smiling): "Next time." The album ends
   with an empty page, "Roll 2: not yet developed". A future chapter decides whose roll it is and which
   days are on it; with no sequel it still reads as "there are always more stories".
7. **Credits** over all four photos; the album's real-vs-imagined page (including the Ch3 note on Malay
   recruits in the first intake).

### Cast across time
| | 1942 | 1965 | 1967 | 2026 |
|---|---|---|---|---|
| Boon | 7 | 30, runs the kopitiam | 32, resists → proud | 91, narrator |
| Siti | 12, helps at Bapak's paper stand | 35, teacher | 37 | — |
| Farid | — (born 1949) | 16 | 18, enlists with Sparky | 77, first-intake NSman; brings the prints |
| Sgt Osman (name TBC) | — | — | regular, drill sergeant | — |
| Irfan | — | — | — | 18, Farid's grandson, on book-out |
| Mr. Rajan | ARP warden | grassroots leader | father of Ravi | — |
| Ravi | — | teen | 18, in Sparky's section | — |
| Ah Hock | — | — | 18, in Sparky's section | — |
| Leo Pereira | — | — | 18, in Sparky's section | — |
| Ah Ma | kopitiam owner | photo on the wall | — | — |

## Scale & coordinates
- Metres. Sparky ≈ 1.0 m tall. Children 1.1–1.35 m, adults 1.55–1.7 m (stylised, larger heads).
- glTF convention: Blender (X, Y, Z) exports to three.js (X, Z, −Y). Characters face Blender −Y
  (= three.js +Z) in their rest pose.

## Asset outputs (all under `public/assets/`)
- `models/sparky-ww2.glb`, `models/sparky-ind.glb`, `models/sparky-ns.glb`, `models/sparky.glb` — optimised Sparky.
- `models/ww2-street.glb` — the level, with named marker empties and colliders (see level contract).
- `models/npc-*.glb` — NPCs.
- `audio/*.mp3` — audio (mp3 for iOS Safari compatibility).

### Quality tiers (the game must look and play like a real desktop game AND run on phones)
- **Desktop / high tier:** keyboard+mouse (WASD, mouse-look with pointer lock, E/Space, Esc), gamepad
  optional; full device pixel ratio (cap 2), real-time shadow map from the sun on nearby geometry,
  post-processing (SMAA/FXAA, subtle bloom, vignette/colour grade, optional SSAO), 1024² textures,
  denser particles/smoke, higher-detail Sparky.
- **Mobile / low tier:** touch joystick + drag-look + big context button, pixel ratio ≤ 1.5,
  blob shadows only, minimal post (colour grade via tone mapping only), 512² textures.
- Auto-detect tier (touch + GPU/screen heuristics), with a Settings toggle (Low / Medium / High).
- Asset variants: each GLB may ship as `name.glb` (desktop, higher texture res / detail) and
  `name-mobile.glb` (512² textures, lighter geometry). If only one file exists, the game uses it
  for both tiers.

Mobile budgets: whole level ≤ 150k triangles, ≤ 40 draw calls (merge by material), textures ≤ 1024²
(most 512²), total chapter download ≤ 15 MB. Characters ≤ 15k tris (Sparky), ≤ 4k tris (NPC),
≤ 3 materials each. Use meshopt/Draco-free plain glTF or `EXT_meshopt_compression` (three supports it).

## Level contract (`ww2-street.glb`) — node names the game code reads
- `SPAWN_Sparky`
- `NPC_Siti`, `NPC_Rajan`, `NPC_AhMa`, `NPC_Boon`, `NPC_Hassan` (start positions; empty −Y = facing)
- `DROP_1`, `DROP_2`, `DROP_3` (shop doors for newspaper delivery)
- `SNAP_Poster`, `SNAP_Bicycle`, `SNAP_Smoke` (photo targets)
- `SHELTER_Entrance`
- `INT_Spawn`, `INT_Radio`, `INT_Seat_1..5`, `INT_Camera` (shelter interior, a separate small room
  placed away from the street, e.g. at X=200)
- `EPI_Spawn`, `EPI_Queue_1..4` (epilogue positions)
- `PRE_*` nodes: visible before occupation only (e.g. British posters). `OCC_*` nodes: hidden until
  the epilogue (Hinomaru flags, "Syonan" banners, ration notice).
- `COL_*` meshes: invisible box colliders (walls, pillars, props). Code hides them & builds collision.
- `SMOKE_*` empties: base positions of distant oil-smoke columns (code renders them as particles).

## Present-day set contract (`voiddeck.glb` / `voiddeck-mobile.glb`)
Queenstown HDB void deck, 2026, late afternoon (built by `tools/build_voiddeck.py`; research in
`docs/research/voiddeck.md`). One mesh `VoidDeck`, one primitive per material (13 draw calls), AO +
warm bounce baked into COLOR_0 (multiply with the base colour map), meshopt-compressed.
- `PRO_Table` (top surface centre, three (0, 0.75, 0)); `PRO_Stool_Boon` / `PRO_Stool_Sparky`
  (floor, under the seat's front edge, facing the table; extras `seat_height` 0.45 and
  `seat_centre_offset` 0.17); `PRO_SeatTop_Boon` / `PRO_SeatTop_Sparky` (seat-top centres);
  `PRO_Kopi` (on the chessboard: Mr. Boon's bag of kopi, built at runtime in `present-kopi.js`).
- `PRO_Camera_Wide`, `PRO_Camera_Close` (their −Y already aims at the table, same targets as
  `present-day.js`); `PRO_Sun` (100 m out along the sun direction, 13° elevation);
  `PRO_Lamp_1..15` (fluorescent battens, sorted nearest-to-table first; 9 = lift lobby).
- Open side is three +Z (Blender −Y): sunlit verge, playground, neighbour block;
  lift lobby & letterboxes at three z ≈ −6..−9. No colliders (cutscene set).

## Chapter 3 set contract (`camp.glb` / `camp-mobile.glb`, built by `tools/build_camp.py`)
Four areas in one GLB, each under its own root node so code can show one at a time (`AREA_Parade`,
`AREA_Barracks`, `AREA_Night`, `AREA_CC`). All coordinates below are **three.js** (x, y up, z); markers face
their Blender −Y (three.js +Z at yaw 0), as in the kopitiam. Colliders are `COL_*` boxes (hidden by code).
Mobile tier: ≤ 150k triangles and ≤ 40 draw calls for the whole file, since only one area is visible at a time.

**AREA_Parade: Taman Jurong Camp, 1967–68, around the origin.**
- Parade square: laterite/tarmac, x −30..30, z −20..20 (`THEN_Square`). Three long five-storey slab blocks of
  one-room flats (open corridors facing the square, 1960s) along the north edge at z ≈ −32..−45 (`THEN_Blocks`).
  The nearest block has an **open stairwell** at its east end facing the square: one real flight from the ground to
  the first landing (9 steps × ~0.165 m) plus the start of the next flight, walkable, with colliders.
- A pile of iron bed frames by the stair foot (`THEN_BedPile`). A separate carryable bed frame node `PROP_Bed`
  (~1.9 × 0.8 m, origin at its centre, built along its local ±Y) that code parents between two carriers.
- Reviewing dais on the south edge, centred at x ≈ 8, z ≈ 24, with an awning and flagpole (`THEN_Dais`).
  Spectator stands (tiered benches under awnings) either side of the dais along z ≈ 24..30, facing north (−z)
  (`THEN_Stands`). Trees and a low fence round the edge; a far treeline and sky.
- **Present-day state (Then & Now):** `NOW_Lawn` (park grass covering the square), `NOW_Path` (jogging path loop),
  `NOW_Marker` (low heritage-marker plinth near the path at about x 4, z 16, with a runtime-textured quad
  `DECAL_Marker`, UV 0..1, ~0.9 × 0.6 m), `NOW_Blocks` (modern HDB blocks at the far edge), `NOW_Trees`.
  Everything else in AREA_Parade is `THEN_*` (hidden in the present-day view). No real marker text is copied.
- Markers:
  - `SPAWN_Sparky` (stair foot, facing up the stair); `STAIR_Bottom`, `STAIR_Landing`, `STAIR_Top` (first landing)
  - `BED_Start` (carried bed's centre at the stair foot, facing up the stair), `BED_Landing`
  - `NPC_Osman_Stair`, `NPC_Leo_Stair` (halfway up, walking down), `NPC_Ravi_Stair`, `NPC_Farid_Landing`
  - `DRILL_1..5` day-one line on the square (1.0 m apart along x at z ≈ 0, facing north −z); order Leo, Farid,
    Sparky, Ah Hock, Ravi. `NPC_Osman_Drill` 4 m in front of the line, facing it.
  - `NPC_Adviser_1`, `NPC_Adviser_2` (edge of the square, west side); `SNAP_Mexicans` (between them, ~1.6 m up).
  - `PARADE_1..5` passing-out start line (1.0 m apart along x at z ≈ 12, x ≈ −14..−10, facing north). After
    *Ke kanan pusing* they face east (+x) and march in file along z = 12. `PARADE_Halt` at x ≈ 22, z = 12.
    The dais is on their right (+z) as they pass x ≈ 8.
  - `STAND_X` (Boon's spot, in front of the stands at x ≈ 12, z ≈ 19.5, facing the square); `STAND_Seat_1..16`
    (seated spectators, facing north); `NPC_Minister` (on the dais); `NPC_Siti_Stand`, `NPC_Rajan_Stand`,
    `NPC_Rohani_Stand`, `NPC_AhPek_Stand`, `NPC_Letchumi_Stand`, `NPC_Neighbour_Stand`, `NPC_AhMa_Stand`.
  - `CAM_Title`, `CAM_DrillDay` (3/4 front view of the day-one line), `CAM_Parade` (low 3/4 view of the start line).
  - `THEN_NOW_Camera` (at the south-west edge, ~1.45 m up, looking north-east across the square/lawn).
  - `SNAP_Marker` (above `DECAL_Marker`).

**AREA_Barracks: a barrack floor at night, centred at x = 200.** An open corridor (~20 m) along three converted
one-room flats with doorways. Iron single beds (one double-decker for Leo), lockers, a single bulb per room, louvred
windows, starched uniforms on hooks. Markers: `BAR_Spawn`, `BAR_Farid` (sitting on his bed), `BAR_AhHock` (sitting
on the bed he carried), `BAR_Ravi` (lying in bed, torch), `BAR_Leo` (top bunk), `BAR_Uniform` + `SNAP_Uniform`
(a uniform standing up on its own by a bed), `LAMP_Bar_1..3`, `CAM_Barracks`. Colliders for walls, beds, lockers.

**AREA_Night: scrub and a stream at night, centred at x = −200.** A clearing ~24 × 24 m: shrubs, lalang, a big
tree, a shallow stream strip across one side. Markers: `NIGHT_Spawn`, `NIGHT_Group_1..5` (crouched under the big
tree), `NIGHT_Stream`, `NIGHT_Rest_1..5` (sitting by the stream), `CAM_Night`.

**AREA_CC: community-centre send-off, Queenstown, 1967, centred at z = 200.** A single-storey 1960s community
centre front with a sign quad (`DECAL_CCSign`), low fence and gate, a canvas-topped army three-tonner with the
tailboard down (`PROP_Truck`), a banner quad between two poles (`DECAL_Banner`), a spot for a small band. Markers:
`CC_Spawn`, `CC_Truck_Tail`, `CC_Gate`, `CC_Boon_Spot` (where Boon would stand; left empty), `CC_Band_1..4`,
`CC_Family_1..10`, `NPC_Rajan_CC`, `NPC_Ravi_CC`, `NPC_Siti_CC`, `NPC_Farid_CC`, `NPC_AhMa_CC` (Ah Hock's Ah Ma,
apart from the truck), `NPC_Neighbour_CC`, `NPC_MP_CC`, `CAM_CC`.

## Chapter 3 cast contract (`tools/build_1967_npcs.py`, same bones and clips as every NPC)
New clips appended after the existing ones (so older clips are unchanged): `Attention` (heels together, arms straight
at the sides, chin up), `March` (stiff drill march: arms swing to shoulder height, loop, one stride per beat at the
character's walk period), `Carry` (arms forward at waist height as if holding a bed frame, walking).
Uniforms: the **Temasek green No. 4**: long-sleeved green cotton-drill shirt with two chest pockets, green trousers,
black boots, starched-looking (crisp, few folds). No headwear (no source yet for 1967 recruit headdress).
| file | who | notes |
|---|---|---|
| `npc-farid-ns` | Farid, 18, recruit | Farid's face DNA (build_1965_npcs `farid`), uniform |
| `npc-ahhock-ns` | Ah Hock, 18, recruit | big and broad (height ~1.74), crew cut, uniform |
| `npc-ravi-ns` | Ravi, 18, recruit | Ravi's face DNA, slim, uniform |
| `npc-leo-ns` | Leo Pereira, 18, recruit | Eurasian, wavy hair, uniform |
| `npc-osman` | Sergeant Osman, ~35, regular | uniform with three sleeve chevrons, pace stick (cane prop), moustache |
| `npc-adviser` | Israeli adviser | khaki shirt and trousers, straw hat, clipboard-ish |
| `npc-ahhockma` | Ah Hock's Ah Ma, ~70 | Hokkien grandmother: dark samfu, grey bun, paper bag |
| `npc-minister` | the Minister (background only) | white long-sleeved shirt, dark trousers, glasses; not a likeness |
| `npc-farid77` | Farid, 77 (2026) | Farid's face DNA aged: white hair, glasses, batik shirt, trousers, sandals |
| `npc-irfan` | Irfan, 18 (2026) | today's No. 4 uniform (pixel camouflage), short hair |
Reused as is: `npc-boon65` (Boon 32), `npc-siti65` (Siti 37), `npc-rajan65`, `npc-farid` (Farid in civvies),
`npc-ravi` (Ravi in civvies), `npc-rohani`, `npc-ahpek`, `npc-letchumi`, `npc-oldboon`, Ch1 crowd NPCs, `sparky-ns`
(its own "Rifle" prop mesh is hidden; the game uses the procedural M16 from `ns-props.js` for everyone).
