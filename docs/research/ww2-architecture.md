# Research notes — Chinatown shophouse street, Singapore, February 1942

Reference notes for the Chapter 1 level (`public/assets/models/ww2-street.glb`, built by
`tools/build_ww2_street.py`). Every modelling decision below is tagged **[src]** when it comes
straight from a cited source, and **[inf]** when it is an artistic inference from general
knowledge of the period (to be listed on the game's "what's real vs imagined" page).

A note on method: the sources were read as text (NLB Infopedia / BiblioAsia articles, URA
conservation pages, Roots.gov.sg, Wikipedia, Wikimedia Commons catalogue captions). No
photographs were downloaded or embedded. Where a "photo" is described below, the description
comes from its catalogue caption or from the article text around it. Everything in the game is
modelled and textured procedurally from these notes.

---

## 1. Shophouse architecture present by 1942

### 1.1 Styles (URA's classification)
URA sorts shophouses built 1840–1960 into six styles: Early, First Transitional, Late, Second
Transitional, Art Deco and Modern. By February 1942 the first five were all standing side by side
in Chinatown. Modern (1950–60) did **not** exist yet and is left out. [src: URA, Roots]

| Style | Dates | What identifies it | How it appears in the level |
|---|---|---|---|
| **Early** | 1840s–1900s | Squat, usually 2 storeys, very little ornament, **two** plain timber-shuttered windows upstairs, locally made clay roof tiles; five-foot-way floor often red cement screed scored into a grid [src: Roots, URA guidelines via thesgshophouse] | 2 storeys, eave at 7.2–7.6 m, 2 windows, timber eave fascia, red scored cement five-foot way |
| **First Transitional** | early 1900s | Taller (a third storey was often added), still restrained, timber windows with small glass panels, some plasterwork and tiles [src: Roots, SG Shop House] | 3 storeys, 2 windows per floor, arched fanlights, a simple cornice |
| **Late** ("Chinese Baroque") | 1900–1940 | The most ornate: **three** windows upstairs with pilasters/columns framing them, full-length French windows, dense plasterwork, Peranakan tile panels, Malay-style timber eaves, bat-motif vents [src: Roots, Insight Guides, SG Shop House] | 2–3 storeys, 3 windows between pilasters, tile panels under the sills, a heavy cornice. Colours are kept muted (see 1.4) |
| **Second Transitional** | late 1930s | A plainer version of Late: muted colours, simpler geometric forms, French windows with timber louvres [src: Roots, SG Shop House] | 2–3 storeys, 2–3 windows, flat pilasters, little ornament |
| **Art Deco** | 1930–1960 | Geometric patterns, stepped parapets, streamlined capitals, clean arches and keystones, a **date plaque** in the pediment, fair-faced brick in some [src: Roots] | Flat stepped parapet with a date plaque ("1936"/"1938"), vertical fins, horizontal hood mouldings |

URA's advice to look at "structure, window proportions, decoration and roofline together" guided
the variety: no two neighbouring houses share a style, height and colour at once. [src: littlebigreddot field guide]

### 1.2 Proportions and elements
- **Plot and frontage:** long, narrow plots on shared party walls, built in continuous terraces
  [src: URA, Wikipedia *Shophouse*]. Wikipedia's worked example gives frontages of 4–5 m on 12 m
  plots. Real Chinatown frontages run about 4.5–6.5 m (≈15–21 ft) [inf]. The level uses
  4.5–6.5 m frontages, 12 m of modelled depth, and backs of other terraces beyond.
- **Storeys:** 2–3 storeys [src: URA]. Ground floor about 3.6–4 m and upper floors about
  3.3–3.5 m [inf, typical of load-bearing brick and timber floors]. The level uses 3.8 m ground
  floors, 3.4 m upper floors and a 0.6–1.2 m cornice/parapet.
- **Five-foot way:** Raffles' 1822 Town Plan required a "verandah of a certain depth, open at all
  times as a continued and covered passage" [src: Wikipedia *Five-foot way*]. Required depths grew
  over time: at least 6 ft in the 1840s, 7 ft (2.1 m) from 1887, and 8 ft (2.4 m) on major streets
  from 1929 [src: BiblioAsia "Give Me Shelter"]. The level uses **2.6 m** overall (2.2 m clear
  behind the columns), which fits the 1929 rule and leaves room for a third-person camera.
  Floor finishes were cement screed, terracotta or clay tiles, terrazzo, mosaic or granite slabs,
  with **granite edging running along the roadside drain** [src: URA guidelines via thesgshophouse].
  The five-foot way sits one step (~0.2–0.3 m) above the road [inf].
- **Five-foot-way life:** hawkers (satay, laksa, noodles), barbers with mirrors hung on the walls,
  letter-writers, cobblers, parrot astrologers and flower sellers worked there. People also sat
  out at dusk and slept there on hot nights [src: BiblioAsia "Give Me Shelter"]. The level shows
  this as stools, baskets, a letter-writer's table and a hawker pushcart.
- **Columns and arches:** the upper storeys rest on columns along the five-foot way, round or
  square depending on style [src: PLB Insights]. The level has square piers at the party walls,
  segmental arches on the Late and Transitional houses, and flat beams on the Early and Deco ones.
- **Windows:** upstairs, full-height French windows that open outward in two leaves, sometimes
  with transoms or **fanlights** and timber or cast-iron balustrades. Downstairs, inward-opening
  casements with iron security bars. Upstairs windows are evenly spaced [src: URA guidelines].
  Frames are painted darker than the walls [src: PLB Insights]. Many have **jalousie / louvred**
  timber shutters [src: Roots, SG Shop House]. The texture atlas has louvred shutters (open and
  closed), panelled shutters, French windows with fanlights, barred casements and pintu pagar.
- **Pintu pagar:** half-height swing doors in front of the main door that let in air while
  keeping privacy [src: Roots, PLB Insights]. They are used on the house-type frontages.
- **Roof:** pitched roofs on timber purlins that rest on the party walls, covered in "overlapping
  V-profile or flat natural colour unglazed clay tiles" (the Canton tile), with timber fascias and
  galvanised-iron gutters [src: URA guidelines]. Some houses have a raised **jack roof** over the
  ridge for ventilation [inf, common on many shophouses]. Party walls rise above the roof as fire
  walls with capped ends [inf].
- **Air wells:** an open courtyard in the middle of the plot brought in light and air [src:
  Wikipedia, PLB Insights]. It cannot be seen from the street, so it is not modelled. The jack
  roofs hint at it.
- **Finishes:** lime plaster over brick, painted with lime wash [src: NUS News "Heritage
  conservation with lime"]. Late-style houses also carry ceramic tile panels, and some have
  Shanghai plaster (cement, sand and crushed marble) [src: PLB Insights]. Art Deco houses may
  have terrazzo five-foot ways [src: URA guidelines].

### 1.3 Signboards and shop types
- Carved or painted wooden **signboards** hang above the doors of businesses, clan associations
  and homes. The calligraphy is carved or painted, typically **gold on black** (and red) [src:
  Roots ICH "Making of Chinese Signboards", SCMP]. Signboard makers clustered on Pekin Street
  [src: Roots ICH]. Characters are also carved on the pillars beside the entrance [src:
  mustsharenews/Starbucks Smith St restoration].
- The level uses two sign types: a **horizontal plaque** on the frieze above the five-foot way
  with the shop's name, and **vertical boards** on the piers with trade phrases in the traditional
  manner (e.g. 參茸藥材 "ginseng, antler and medicinal herbs" for a medical hall). All text is in
  Traditional characters, as used in 1942. Romanised names use the "Chop ..." firm convention and
  period Malay trade words (*Kedai Kopi*, *Kedai Runcit*, *Tukang Jahit*) [inf].
- Shop types (all made up, none copying a real firm): 福記咖啡店 Hock Kee Coffee Shop (Ah Ma's
  kopitiam), 濟生堂 medical hall (DROP_1), 美華洋服 Mei Hua tailor (DROP_2), 南豐號 Nam Hong
  provision shop (DROP_3), 金寶金莊 goldsmith, 光華影相館 Kong Hwa photo studio (a hook for young
  Boon's "one day I'll have a camera"), 大信當 pawnshop, 茶莊 tea merchant, 米行 rice dealer and a
  clog/rattan shop. Medical halls in Chinatown are documented by Thye Shan and Teck Soon medical
  halls [src: thyeshan.com, lionheartlanders].
- **Kopitiam:** the classic furniture is a timber table with a **marble top** (round, square or
  hexagonal) and wooden chairs [src: Roots collection "Kopitiam table with marble top"; that
  object is dated 1950s–80s, so its use in 1942 is a mild inference, though marble-topped tables
  were already common in pre-war coffee shops]. A black-and-gold carved signboard is typical
  [src: johorkaki on Heap Seng Leong]. The level adds a charcoal-fired kopi boiler with a
  cloth-sock strainer, glass biscuit jars, an abacus and cash drawer, a wall clock, a calendar
  poster and red CNY couplets. It is a place Boon will want to run in 1965 [inf].

### 1.4 Colours — why the level is not pastel
Lime wash comes from a small range of earth pigments: yellow ochre, iron-oxide reds and browns,
and some ultramarine. One conservation dig on a shophouse found rust-brown and ultramarine under
later paint, and traditional colours included yellow ochres [src: lionheartlanders / NUS News].
Today's bright candy pastels are late-20th-century repaints. So the level uses **off-white, cream,
buff, pale ochre, faded Venetian red, dull celadon and faded blue-grey**, tinted per house by
vertex colour. Walls are streaked with rain, darker at the base (splash-back), mould-stained under
the sills, with shutters in dark green, brown, oxblood and blue-grey [inf].

---

## 2. Street elements, c. 1930–1942
- **Road:** Chinatown's main roads were metalled and tarred by the 1930s. Trams ran on South
  Bridge Road 1905–1927, then **trolley buses from 1929** [src: Infopedia *South Bridge Road*].
  The level has a patched, dusty tar surface. The cross street at the east end, standing in for
  South Bridge Road, has twin trolleybus wires on span wires.
- **Drains and kerbs:** an open, stone-lined monsoon drain runs between the road and the
  five-foot way, with granite edging on the five-foot-way side [src: URA guidelines]. Small slab
  bridges cross it at doorways [inf].
- **Street lighting:** gas lamps lit most streets; the last one went in 1956, and about 530 were
  still in use in 1954. Electric street lighting spread from 1906 in the centre, and modern
  mercury lamps arrived on Clemenceau Avenue in 1939 [src: BiblioAsia "Let There Be Light",
  Remember Singapore]. The level has cast-iron gas-lantern posts with **blackout hoods** [inf, see
  3.2], plus timber utility poles carrying wires.
- **Transport:** hand-pulled rickshaws were still everywhere. The central depot was the
  **Jinrikisha Station**, bombed on 3 Feb 1942 [src: Wikipedia *Bombing of Singapore*]. Trishaws
  first appeared in 1914 as "pedal rickshaws", spread in the 1930s and became dominant after the
  war. Rickshaws were banned in 1947 [src: Infopedia *Trishaw*]. The level has Pak Hassan's
  rickshaw (one wheel off), one trishaw, bicycles, handcarts, a hawker pushcart with a carrying
  pole, and an unhitched bullock cart. The cart nods to 牛車水 *Gu Chia Chui*, "bullock-cart water",
  Chinatown's Chinese name [inf, well-known toponym].
- **Laundry poles:** bamboo poles pushed out of upper windows with washing hanging on them [inf,
  a ubiquitous sight in pre-war photographs]. **Rattan/bamboo chick blinds** hang in the
  five-foot-way openings, some rolled up and some down [inf].
- **Chinese New Year:** 15 Feb 1942 was the first day of CNY (in the design doc). A few faded red
  couplets and lanterns suggest a festival nobody is celebrating [inf].

---

## 3. Wartime, Dec 1941 – Feb 1942
### 3.1 Timeline facts used in dialogue and set dressing
- ARP (Air Raid Precautions) was set up in 1938 and had about 3,500 wardens by Nov 1939 [src:
  NAS Former Ford Factory collection]. Wardens made residents take cover and switch off lights,
  and made vehicles pull over with their lamps off [src: BiblioAsia "In Their Own Voices"].
- 8 Dec 1941: the first raid, by 17 bombers at 04:30. The streets were **still brightly lit**
  because the man with the key to the power-station switch could not be found. 61 people were
  killed [src: Wikipedia *Bombing of Singapore*]. After that, the blackout was enforced.
- 10 Feb 1942: Japanese artillery set the **Normanton oil depot** on fire. The **Pulau Bukom**
  tanks were also burning and were shelled from Fort Siloso to deny them to the enemy. By
  15 Feb the city was ringed by smoke and flames [src: fortsiloso.com, NLB *Pulau Bukom*]. A
  well-known photo is captioned "A column of smoke from burning oil tanks rising above the
  deserted streets of Singapore, Feb 1942" [src: ww2db image 4609]. Hence **three SMOKE_ columns
  to the south-west and west, 180–300 m out**, and an overcast, smoky sky.

### 3.2 Shelters, sandbags, blackout
- The government said Singapore's low, waterlogged ground made underground shelters
  "impossible" and blamed the "narrow streets". Residents were told to "make for" the nearest
  open space [src: BiblioAsia "In Their Own Voices"]. That is why the level's shelter is a
  **surface shelter on an open lot**, built of brick with a slab roof and banked sandbags.
- Civilian shelters were improvised: a brick underground shelter in a compound, a semicircular
  pit about 8 ft deep and 5–6 ft wide roofed with **planks and sandbags**, or simply the space
  under a staircase and a table [src: BiblioAsia]. So Boon hiding under a kopitiam table is
  historically grounded.
- The Tiong Bahru SIT shelter (1939–41, 1,600 people) is the only surviving pre-war civilian
  shelter. Its entrances were **in front of a coffee shop**. Inside it was dark and
  unventilated, and people waited about 20 minutes for the all-clear [src: Roots online
  exhibition, Wikipedia]. The level's shelter interior matches this: dark, brick, benches, one oil
  lamp and candles, a crate with a wireless set.
- **Criss-cross paper tape** on glass against blast, **sandbagged doorways**, fire buckets, sand
  buckets and stirrup pumps at ARP posts, and blackout cloth or paint on windows and lamp heads.
  These were standard British-Empire civil-defence practice and appear in IWM "Siege of
  Singapore 1942" photographs of civil-defence crews fighting fires in city streets [src: IWM
  collection listings. Specific Singapore captions for taped panes were not found in text, so
  the tape is an **inference** from Empire-wide ARP practice].
- **Posters** (PRE_): the game uses original text in period style, not copies of real artwork:
  "JOIN THE PASSIVE DEFENCE SERVICES", "WHEN THE SIREN SOUNDS — TAKE COVER" (English/Chinese),
  "CARELESS TALK COSTS LIVES" (a real 1940 UK Ministry of Information slogan; the words are a
  public-domain phrase, the layout is new) and "BUY WAR SAVINGS CERTIFICATES" (war-savings drives
  are documented in 1941 Malayan papers) [src: BiblioAsia salvage/war-effort notes; inf layout].
- Signs of fear and haste: hoarded tinned food (people lived on tinned sardines for 2–3 weeks
  before the surrender) [src: BiblioAsia], bundles and suitcases on the five-foot way, a
  half-loaded handcart, a shuttered shop, a lost slipper [inf].
- **Bomb damage** (DMG_ state): one shophouse loses its upper facade and roof, with exposed timber
  joists, fallen shutters, and rubble on the five-foot way and road [inf; bombing of the city in
  Dec 1941 – Feb 1942 is documented, e.g. the Jinrikisha Station raid on 3 Feb].

---

## 4. Syonan-to epilogue (OCC_ nodes)
- Singapore was renamed **Syonan-to** 昭南島 ("Light of the South"). Rising-sun (Hinomaru) flags
  were hung on buildings and **propaganda banners and posters went up everywhere** [src: Military
  Wiki / lionheartlanders *Japanese Occupation*].
- **Rationing:** ration cards, 4.8 kg of rice a month per adult and 2.4 kg per child, later cut.
  A "Peace Living Certificate" was needed to get cards, and people **queued in the sun** [src:
  BiblioAsia "Wartime Victuals", Mothership]. Hence the ration notice board (配給 / *haikyu* /
  *beras*) and the EPI_Queue markers outside the provision shop.
- **"Banana money":** the occupation currency, named for its banana-tree motif, soon made
  worthless by inflation [src: same].
- **Sentry posts:** civilians had to bow to Japanese sentries at checkpoints [inf, widely
  documented in oral histories]. OCC_Sentry is a small hut and barrier at the east end. The
  game may add the figure.

---

## 5. Landmarks on the skyline
- **Sri Mariamman Temple gopuram** (South Bridge Road). The present **six-tiered** gopuram dates
  from **1925**. It was restored in the 1960s with many more sculptures, and the pre-1960s tower
  was "less richly embellished" [src: Wikipedia *Sri Mariamman Temple*]. Pagoda Street and
  Temple Street run into South Bridge Road at the temple, so a Chinatown side street really can
  end on this view. **Built:** at the east end, across the cross street, centred on the street's
  axis. About 15 m high [inf; no height found in sources], six diminishing tiers and a
  barrel-vault crown, in muted lime-wash colours with faint polychrome to match the pre-1960s,
  less decorated state.
- **Jamae (Chulia) Mosque**, 218 South Bridge Road (built 1830–35): a pair of **octagonal
  minarets with seven levels of double arch-shaped niches**, joined by a miniature palace facade
  above the gateway [src: Roots, Wikipedia]. **Built:** a little south along the cross street,
  showing above the lower corner house.
- **Cathay Building** (cinema 1939, flats 1940, 83.5 m, then Singapore's tallest), requisitioned
  in early 1942 for the Malaya Broadcasting Corporation [src: Wikipedia]. It is roughly 1.5 km
  away, so it is only a faint far-skyline silhouette.
- Thian Hock Keng (Telok Ayer Street) was considered, with its curved swallowtail roofs and
  dragons [src: Wikipedia]. It was left out because it faces Telok Ayer Street, not a
  South Bridge Road junction, and one temple terminus reads more clearly.

---

## Sources
- URA — Understanding the Shophouse: https://www.ura.gov.sg/conservation/conservation-resources/understanding-the-shophouse/
- Roots.gov.sg — The Singapore Shophouses: https://www.roots.gov.sg/stories-landing/stories/singapore-shophouses/story
- Six Singapore Shophouse Styles field guide: https://littlebigreddot.com/singapore-shophouse-styles-field-guide/
- SG Shop House — URA shophouse guidelines: https://www.thesgshophouse.com/ura-shophouse-guidelines-in-singapore/
- SG Shop House — History of shophouses: https://www.thesgshophouse.com/history-of-shophouses-in-singapore/
- PLB Insights — 10 archetypal features: https://plbinsights.com/10-archetypal-features-shophouses-in-singapore/
- Insight Guides — Singapore shophouses: https://www.insightguides.com/destinations/asia-pacific/singapore/cultural-features/singapore-shophouses
- Our Grandfather Story — Shophouse types: http://ourgrandfatherstory.com/shophouse-history-design-types/
- Wikipedia — Shophouse: https://en.wikipedia.org/wiki/Shophouse
- Wikipedia — Five-foot way: https://en.wikipedia.org/wiki/Five-foot_way
- BiblioAsia — Give Me Shelter: The Five-footway Story: https://biblioasia.nlb.gov.sg/all-sections/vol-15-issue-3-oct-dec-2019-five-foot-way/
- NUS News — Heritage conservation with lime: https://news.nus.edu.sg/heritage-conservation-with-lime/
- Lionheartlanders — Evolution of shophouses: https://www.lionheartlanders.com/post/the-fascinating-evolution-of-singapore-shophouses-history
- Roots ICH — Making of Chinese Signboards: https://www.roots.gov.sg/ich-landing/ich/making-of-chinese-signboards
- SCMP — Chinese signboard making in Singapore: https://www.scmp.com/lifestyle/travel-leisure/article/3205098/inside-dying-art-chinese-signboard-making-meet-two-men-keeping-traditional-craft-alive-singapore
- Roots collection — Kopitiam table with marble top: https://www.roots.gov.sg/Collection-Landing/listing/1336384?taigerlist=collections
- Heap Seng Leong kopitiam: https://johorkaki.blogspot.com/2020/08/heap-seng-leong-kopitiam-singapores.html
- Thye Shan Medical Hall: https://thyeshan.com/our-story/
- Infopedia — South Bridge Road: https://eresources.nlb.gov.sg/infopedia/articles/SIP_911_2005-01-19.html
- Infopedia — Trishaw: https://eresources.nlb.gov.sg/infopedia/articles/SIP_932_2005-01-24.html
- BiblioAsia — Let There Be Light (street lighting): https://biblioasia.nlb.gov.sg/vol-16/issue-4/jan-mar-2021/light/
- Remember Singapore — Street lighting history: https://remembersingapore.org/2021/09/24/singapore-street-lighting-history/
- BiblioAsia — In Their Own Voices: Preparing for War in Singapore: https://biblioasia.nlb.gov.sg/vol-18/issue-4/jan-mar-2023/preparing-war-singapore/
- Wikipedia — Bombing of Singapore (1941): https://en.wikipedia.org/wiki/Bombing_of_Singapore_(1941)
- NAS — Former Ford Factory collection highlights: https://corporate.nas.gov.sg/former-ford-factory/collection/
- Roots — Tiong Bahru Air Raid Shelter: https://www.roots.gov.sg/resources-landing/online-exhibitions/tiong-bahru-air-raid-shelter
- Wikipedia — Tiong Bahru Air Raid Shelter: https://en.wikipedia.org/wiki/Tiong_Bahru_Air_Raid_Shelter
- Fort Siloso — History 1942: https://fortsiloso.com/history/1942/1942.htm
- NLB — Pulau Bukom: https://www.nlb.gov.sg/main/article-detail?cmsuuid=93a29125-66aa-46c6-8ca3-9b9b0f65ab8d
- WW2DB — smoke from burning oil tanks, Feb 1942: https://ww2db.com/image.php?image_id=4609
- IWM — The Siege of Singapore, 1942: https://www.iwm.org.uk/collections/item/object/205050130
- Wikimedia Commons — Category: Battle of Singapore: https://commons.wikimedia.org/wiki/Category:Battle_of_Singapore
- BiblioAsia — Wartime Victuals: https://biblioasia.nlb.gov.sg/all-sections/vol-15-issue-1-apr-jun-2019-wartime-victuals/
- Japanese occupation of Singapore (Military Wiki): https://military-history.fandom.com/wiki/Japanese_occupation_of_Singapore
- Wikipedia — Sri Mariamman Temple: https://en.wikipedia.org/wiki/Sri_Mariamman_Temple,_Singapore
- Wikipedia — Masjid Jamae: https://en.wikipedia.org/wiki/Masjid_Jamae
- Roots — Jamae Mosque: https://www.roots.gov.sg/places/places-landing/Places/national-monuments/jamae-mosque
- Wikipedia — Cathay Building: https://en.wikipedia.org/wiki/Cathay_Building
- Wikipedia — Thian Hock Keng: https://en.wikipedia.org/wiki/Thian_Hock_Keng
