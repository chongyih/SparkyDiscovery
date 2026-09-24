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
  his old Brownie box camera: three frames left on the roll, "three days I never forgot".
- **Then & Now (each chapter, ~20 s):** Sparky stands in the *real place today* and raises the
  Brownie. A ghostly sepia overlay of Mr. Boon's old photo appears in the viewfinder; the player lines
  it up (position, turn, tilt). When it locks, colour drains, and Sparky steps into the past. This also
  teaches the camera controls.
  - 1942: Telok Ayer's conserved shophouses today (cafés, lanterns, tourists) → same street, 12 Feb 1942.
    (A `NOW_` dressing variant of the same street geometry.)
  - 1965: Queenstown today → the early block and kopitiam, 9 Aug 1965.
  - 1967: a present-day scene tied to the first intake → 17 Aug 1967 (exact "now" scene TBD).
- **Ending (~30 s):** the photos develop. Farid (now 77, one of the first NSmen) visits Mr. Boon at the
  void deck. Album complete; credits over the photographs. (NS60 is in 2027.)

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
2. Morning rush 25 s: **2 orders** (tutorial). Everyday 1965 chatter (prices, Konfrontasi, Malaysian
   dollars). Customers sit apart by community.
3. 10 a.m. 15 s: the counter radio (on Radio Singapura's Malay service, for Makcik Rohani's songs) breaks in
   with the Proclamation. It's the real Malay recording, the only 1965 one known to survive. Makcik understands first. Cups stop mid-sip. Boon freezes:
   "Every time the news changes, someone disappears." (His papa, 1942.)
4. Errand 15 s: Boon sends Sparky along the shop corridor to fetch Siti. On the way, ambient rumours
   echo Ch1 ("No more water from tomorrow!", "The army from KL is coming!"). Siti hesitates, then comes.
5. Worries rush 30 s: **3 orders, each with a worry** half-heard in another language. Siti answers
   from her corner table; Sparky delivers drink + answer; chairs start turning towards each other.
   Fact cards: water (the Separation Agreement kept the water deals), the British bases, the riots/jobs.
6. Evening + TV 30 s: the whole block crowds in. One quick **cross-order** (a Hokkien uncle orders
   teh-C for the Tamil auntie). Then the press conference: the "moment of anguish" and "This is not a
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

**Ch3 seeds:** only **Farid (16, helps at the counter)** and **Ravi (Mr. Rajan's son)** are planted:
separate tables all day, side by side on the bench at the TV, not speaking. Ah Hock and the Eurasian
boy are introduced fresh in Ch3.

**LKY footage: use the real clip (user decision; internal, non-profit build).** Source: NAS "Prime
Minister Meets The Press" (accession 1997002660), with subtitles verbatim from transcript lky19650809b.
Credit on screen while it plays and in the album: "Courtesy of Mediacorp Pte Ltd / National Archives of
Singapore". NAS says reuse needs Mediacorp's written permission, so ask them before any public
release (itch.io, competition pages).

**Research:** done, in `docs/research/1965-history.md` (press conference recorded at noon and shown
on TV the same day; ST 10 Aug headline "Singapore is out"; firecrackers in Chinatown confirmed).
Script: `docs/ch2-script.md`. **Still open:** the Tamil lines (placeholders) and a native-speaker
review of all Hokkien, Malay and Tamil; the exact time the press conference aired on TV; clip
timecodes.

### Chapter 3 — "The First Intake" (17 Aug 1967) ~2.5 min — family story + section of strangers
- **Family frame ("good iron isn't made into nails", 好铁不打钉，好男不当兵):** many families were uneasy
  about sons becoming soldiers. Farid (18, Siti's brother, born 1949) is enlisting; Boon (32), like an
  uncle to him, begs him not to go: "My papa went out in a war and never came home." Ends at the
  passing-out parade, where Boon comes after all and takes the photo, resolving his 1942 wound.
- **Section of strangers (gameplay):** Sparky's section: Farid (Malay), Ah Hock (Chinese hawker's son,
  Hokkien only), **Ravi (Mr. Rajan's son)**, and a Eurasian boy. No shared language, little trust.
  Co-op mechanics: a marching rhythm game where the whole section must stay in step; an obstacle
  course where you help each buddy past their weak spot; a night navigation exercise where each
  holds one piece of the puzzle. Pays off 1965's "multiracial nation" with a multiracial army.
- Setting: first intake, 900 men into 3 SIR & 4 SIR, Taman Jurong Camp (converted five-storey
  JTC flat blocks as barracks), Temasek green uniforms. (Chapter 3 does *not* mirror Chapter 1's beats.)

### Cast across time
| | 1942 | 1965 | 1967 | 2026 |
|---|---|---|---|---|
| Boon | 7 | 30, runs the kopitiam | 32, resists → proud | 91, narrator |
| Siti | 12, helps at Bapak's paper stand | 35, teacher | 37 | — |
| Farid | — (born 1949) | 16 | 18, enlists with Sparky | 77, first-intake NSman |
| Mr. Rajan | ARP warden | grassroots leader | father of Ravi | — |
| Ravi | — | teen | 18, in Sparky's section | — |
| Ah Ma | kopitiam owner | photo on the wall | — | — |

## Scale & coordinates
- Metres. Sparky ≈ 1.0 m tall. Children 1.1–1.35 m, adults 1.55–1.7 m (stylised, larger heads).
- glTF convention: Blender (X, Y, Z) exports to three.js (X, Z, −Y). Characters face Blender −Y
  (= three.js +Z) in their rest pose.

## Asset outputs (all under `public/assets/`)
- `models/sparky-ww2.glb`, `models/sparky-ns.glb`, `models/sparky.glb` — optimised Sparky.
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
  `seat_centre_offset` 0.17); `PRO_SeatTop_Boon` / `PRO_SeatTop_Sparky` (seat-top centres).
- `PRO_Camera_Wide`, `PRO_Camera_Close` (their −Y already aims at the table, same targets as
  `present-day.js`); `PRO_Sun` (100 m out along the sun direction, 13° elevation);
  `PRO_Lamp_1..15` (fluorescent battens, sorted nearest-to-table first; 9 = lift lobby).
- Open side is three +Z (Blender −Y): sunlit verge, playground, neighbour block;
  lift lobby & letterboxes at three z ≈ −6..−9. No colliders (cutscene set).
