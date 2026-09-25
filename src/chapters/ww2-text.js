// Chapter 1 — "The Fortress Falls" (Singapore, February 1942)
// All in-game text for the prologue and Chapter 1. Research notes and citations:
// docs/research/ww2-history.md.
//
// A line is { who, text } or { who: 'Sparky', react } (Sparky has no voice; `react` names an emote).
// Speakers: Narrator, OldBoon, Siti, Rajan, AhMa, Boon, Hassan, Shopkeeper, Neighbour, Soldier, Card.
// Glosses: write {word|meaning} to show a small translation above a word (e.g. {adik|little one}).
//   Use them on the FIRST appearance of a non-English word or name kids may not know.
// Lines are ≤ 120 characters (glosses not counted) so they fit a phone speech bubble (checked by tools/check_text.mjs).
// Everything spoken by a character is fiction. Facts, snaps, the epilogue and cards follow the sources below.
//
// Voices — keep them distinct and conversational (short, spoken sentences; people react to each other):
//   Siti (12): chatty, a bit bossy, reads everything, braver than she feels.
//   Mr. Rajan (ARP warden): calm, dry, dutiful. Speaks in short instructions.
//   Ah Ma: brisk, practical, scolds with love. "Aiyoh".
//   Ah Boon (7): questions, literal, excitable, scared.
//   Pak Hassan: warm joker, grandfatherly, laughs at his own bad ankle.
//   Old Mr. Boon (91): gentle, slow, a little wry.

export default {
  meta: {
    chapter: 1,
    title: 'The Fortress Falls',
    place: 'Chinatown, Singapore',
    dates: '12–15 February 1942 (epilogue: March 1942)',
  },

  contentNote:
    'This chapter shows wartime air raids, fear and loss. Nothing graphic is shown.',

  // Present day, a Queenstown void deck. Old Mr. Boon (91) shows Sparky the Brownie camera.
  // (Code: first two lines play on the wide shot, the rest on the close-up.)
  prologue: [
    { who: 'OldBoon', text: 'Careful, Sparky! That’s my old Brownie camera. It’s even older than me. And I’m ninety-one!' },
    { who: 'OldBoon', text: 'There are still three photos left on this roll. I never took them. Three days I could never forget.' },
    { who: 'OldBoon', text: 'The first one is 1942. I was seven years old, hiding under a table in my {Ah Ma|grandma}’s {kopitiam|coffee shop}.' },
    { who: 'OldBoon', text: 'Go on, Sparky. Look through it. Maybe you’ll see what I saw.' },
    { who: 'Sparky', react: 'peer' },
  ],

  // Then & Now: present-day Telok Ayer. Line up Mr. Boon's old photo with today's street.
  thenNow: {
    card: { who: 'Card', text: 'Telok Ayer, Chinatown. Today.' },
    before: [
      { who: 'OldBoon', text: 'It’s all cafés and tourists now. But back then, this street was my whole world.' },
    ],
    hint: 'Raise the camera. Line up the old photo with the street.',
    close: 'Almost… turn a little more.',
    locked: [
      { who: 'OldBoon', text: 'There. That’s it. That’s exactly how it looked.' },
    ],
  },

  intro: [
    { who: 'Card', text: 'Chinatown, Singapore. Thursday, 12 February 1942.' },
    { who: 'Narrator', text: 'Four days ago, Japanese soldiers crossed over from Johor and landed on Singapore island.' },
    { who: 'Narrator', text: 'The newspapers still say “Fortress Singapore”. But look at the sky. That isn’t rain cloud. It’s smoke.' },
  ],

  // Beat 2: Siti gives Sparky two newspapers to deliver (DROP markers in `drops`).
  papers: {
    start: [
      { who: 'Siti', text: 'Eh, you! You look lost. What’s that on your bag… S-P-A-R-K-Y. Sparky! Is that your name?' },
      { who: 'Sparky', react: 'nod' },
      { who: 'Siti', text: 'I’m Siti. Want to help me, Sparky? My {bapak|dad}’s paper stand is crazy busy today.' },
      { who: 'Siti', text: '{Bagus|Great}! Take these two. One Chinese paper for the medical hall, one Malay paper for the provision shop.' },
      { who: 'Siti', text: 'Front page says “Singapore will stand!” I read it out to the whole street this morning.' },
      { who: 'Siti', text: 'But if we’re so safe… why is everyone packing?' },
    ],
    hint: 'Deliver the two newspapers.',
    snapHint: 'Tip: look for “Take a photo”. Some things are worth remembering.',
    // Optional chats. Each carries a little of the dread under the calm.
    barks: {
      Siti: [
        { who: 'Siti', text: 'People say the Japanese are already at Bukit Timah. Funny, the paper doesn’t say that.' },
        { who: 'Siti', text: '{Mak|Mum} says one day I might get a little brother. I’ll teach him to read. First thing!' },
        { who: 'Siti', text: 'Every morning I read the headlines out loud. Somebody has to tell the street what’s going on.' },
      ],
      Rajan: [
        { who: 'Rajan', text: 'Morning, Sparky. See the tape on the windows? If a bomb falls, the glass won’t fly everywhere.' },
        { who: 'Rajan', text: 'I’m the {ARP|Air Raid Precautions} warden here. No pay. Just this helmet and a whistle. But it’s my street.' },
        { who: 'Rajan', text: 'Lots of rumours today. Don’t believe everything you hear. Stay calm. Stay near the shelter.' },
      ],
      AhMa: [
        { who: 'AhMa', text: 'Rice, salt, candles. Buy them today. Tomorrow? Who knows.' },
        { who: 'AhMa', text: 'Aiyoh, Boon! Come out from under that table and wipe the cups!' },
        { who: 'AhMa', text: 'The tap water is getting weaker every day. Fill every pot you can find, Sparky.' },
      ],
      Boon: [
        { who: 'Boon', text: 'Is that a real camera? Wah! One day I’m going to have one just like it.' },
        { who: 'Boon', text: 'When I grow up, I’m going to make kopi even better than Ah Ma’s. Shh, don’t tell her.' },
        { who: 'Boon', text: 'My papa’s helping at the docks. He promised he’ll be home for Chinese New Year.' },
      ],
      Hassan: [
        { who: 'Hassan', text: 'Hear that? Boom… boom. Big guns, near Bukit Timah. Louder than yesterday.' },
        { who: 'Hassan', text: 'No satay today, {adik|little one}. My ankle’s useless! So Siti brings me the news instead. Clever girl, that one.' },
        { who: 'Hassan', text: 'The family next door left last night, everything on a cart. But go where? We’re on an island.' },
      ],
    },
    done: [
      { who: 'Siti', text: 'Done already? {Terima kasih|Thank you}! You’re even faster than my—' },
      { who: 'Sparky', react: 'startle' },
    ],
  },

  // Two deliveries (trimmed from three). `fact` shows as a card after the hand-over.
  drops: [
    {
      marker: 'DROP_1',
      shop: 'Medical hall',
      paper: 'the Chinese newspaper',
      handoff: [{ who: 'Shopkeeper', text: 'Ah, the {Nanyang Siang Pau|Chinese newspaper}! Thank you. Might be the last one for a while.' }],
      factTitle: 'Nanyang Siang Pau — “South Seas Business News”',
      fact: 'One of Singapore’s big Chinese newspapers. Like the others, it stopped printing just before Singapore fell, and only came back in September 1945.',
    },
    {
      marker: 'DROP_3',
      shop: 'Provision shop',
      paper: 'the Malay newspaper',
      handoff: [{ who: 'Shopkeeper', text: '{Utusan Melayu|Malay newspaper}! Good. The rice sacks are almost empty, but at least the news still comes.' }],
      factTitle: 'Utusan Melayu — “The Malay Messenger”',
      fact: 'The first Malay newspaper owned and run by Malays, started here in 1939. One of its founders, Yusof Ishak, later became Singapore’s first President.',
    },
  ],

  // Small optional kindnesses (community resilience). The people you help come back in later chapters.
  kindness: [
    {
      id: 'bundles', who: 'Neighbour', label: 'Help tie the bundles',
      ask: [{ who: 'Neighbour', text: 'Adik, can you hold this rope? My hands are shaking too much to tie it.' }],
      thanks: [{ who: 'Neighbour', text: 'Thank you. We’re going to my sister’s in Geylang. At least we’ll be together.' }],
    },
    {
      id: 'water', who: 'Hassan', label: 'Bring Pak Hassan some water',
      ask: [{ who: 'Hassan', text: 'Adik, the tap by the kopitiam still works. Could you bring an old man a cup? My ankle, you see.' }],
      thanks: [{ who: 'Hassan', text: 'Ahh. Better than satay. Well… almost. Thank you, adik.' }],
    },
  ],

  // Look closer: short notes when a hotspot is framed in the viewfinder.
  lookCloser: {
    Poster: 'A war poster: “Fortress Singapore”. Behind it, black smoke is rising.',
    Bicycle: 'An ordinary bicycle. Japanese soldiers rode bikes just like this all the way down Malaya.',
    Smoke: 'Black smoke from burning oil tanks, miles away. It has hung over the city for days.',
  },

  // Beat 3: the siren. Rajan sends Sparky to bring Ah Ma, Ah Boon and Pak Hassan to the shelter.
  raid: {
    start: [
      { who: 'Rajan', text: 'Air raid! Air raid! Everybody off the street, now!' },
      { who: 'Rajan', text: 'Sparky! Ah Ma, Ah Boon and Pak Hassan are still out here. Get them to the shelter. Quick!' },
      { who: 'Rajan', text: 'Stay close to the walls. And don’t stop to look up!' },
    ],
    hint: 'Find Ah Ma, Ah Boon and Pak Hassan. Bring them to the shelter.',
    // A line with `requires: 'X'` plays only if X is already following Sparky.
    found: {
      AhMa: [
        { who: 'AhMa', text: 'My shop… my money tin… Aiyoh, forget it! Where’s Boon? Have you seen Boon?' },
        { who: 'AhMa', text: 'Okay, okay. You lead, Sparky. I’m right behind you.' },
      ],
      Boon: [
        { who: 'Boon', text: 'No! I’m not coming out! The planes are too loud!' },
        { who: 'Boon', text: 'I want Papa! Papa’s at the docks!' },
        { who: 'AhMa', requires: 'AhMa', text: 'Boon. Look at me. Papa knows how to take cover. Now hold my hand. Tight.' },
        { who: 'Boon', text: 'Okay… but you go first, Sparky.' },
      ],
      Hassan: [
        { who: 'Hassan', text: 'Go on without me, adik. I’m too slow—' },
        { who: 'Hassan', text: 'What, you won’t leave me? {Aiyah|Oh dear}. Okay, okay. Slowly, ya?' },
      ],
    },
    follow: [
      { who: 'Boon', text: 'Don’t let go! Don’t let go!' },
      { who: 'AhMa', text: 'Don’t look up, Boon. Just watch Sparky.' },
      { who: 'Hassan', text: 'Keep going! I’m still here!' },
      { who: 'Rajan', text: 'This way! Past the lamp post! Keep coming!' },
    ],
    // A shophouse on the route is hit (scripted; nobody in the party is hurt).
    hit: [
      { who: 'Rajan', text: 'Get down!' },
      { who: 'Boon', text: 'That’s Uncle Lim’s shop! Is he inside? Ah Ma, is he inside?' },
      { who: 'Rajan', text: 'The fire team’s coming. We can’t help him by standing here. Move!' },
      { who: 'AhMa', text: 'Don’t look back, Boon. Don’t look back.' },
    ],
    arrive: [
      { who: 'Rajan', text: 'In, in, in! Heads down. One, two, three… and Sparky. That’s everyone.' },
      { who: 'Rajan', text: 'Good job, Sparky. Now we wait.' },
    ],
  },

  // Heirloom choice at the shelter door: room for two things. No wrong answer; each pays off later.
  shelterChoice: {
    lines: [
      { who: 'Rajan', text: 'No bags! There’s no room in there. Two things per family, that’s all.' },
      { who: 'AhMa', text: 'Two? Aiyoh. Sparky, help me choose. Quickly!' },
    ],
    prompt: 'There’s room for two things. What will you bring into the shelter?',
    pick: 2,
    options: [
      { id: 'photo', label: 'The family photo', react: [{ who: 'AhMa', text: 'Boon’s papa is in that photo. Good. We keep him close.' }] },
      { id: 'rice', label: 'The sack of rice', react: [{ who: 'AhMa', text: 'Rice. Smart boy, Sparky. Nobody can be brave on an empty stomach.' }] },
      { id: 'newspaper', label: 'Siti’s newspaper', react: [{ who: 'Siti', text: 'You’re keeping it? Then I’ll read it to everyone in there.' }] },
      { id: 'tiffin', label: 'Papa’s tiffin carrier (lunch tins)', react: [{ who: 'Boon', text: 'That’s Papa’s {tiffin carrier|stacked lunch tins}! He’ll need it when he comes back.' }] },
    ],
  },

  // 12 Feb: blasts, candle out. Card. 14 Feb: Boon has slipped out to find his papa; Sparky goes after him.
  shelterTransition: {
    before: [
      { who: 'Rajan', text: 'Stay on the bench! Heads down, hands over your heads!' },
      { who: 'Boon', text: 'Ah Ma, the walls are shaking! Make it stop!' },
      { who: 'Hassan', text: 'The candle! Somebody hold on to the matches—' },
    ],
    card: { who: 'Card', text: 'Two nights later. Saturday, 14 February 1942.' },
    // Late at night, everyone is asleep. Sparky sees Boon get up and tiptoe to the door.
    boonLeaves: [
      { who: 'Boon', text: '(whispering) Sparky? You’re awake too? I can’t sleep. Papa hasn’t come.' },
      { who: 'Boon', text: '(whispering) The fire post is just on Neil Road. I’ll bring him his dinner and come right back.' },
      { who: 'Boon', text: '(whispering) Shh! Don’t wake Ah Ma. I’ll be quick. Promise.' },
    ],
    // A shell lands close; everyone wakes up.
    after: [
      { who: 'AhMa', text: 'What was that?! Boon? Boon! His mat is empty. Where’s my Boon?' },
      { who: 'Siti', text: 'He kept asking about his papa. The fire post on Neil Road… Sparky, did he go out there?' },
      { who: 'Rajan', text: 'Out there? In this?!' },
      { who: 'Rajan', text: 'I can’t leave everyone here. Sparky, you’re small and fast. Find him. Stay under the five-foot ways.' },
    ],
    objective: 'Find Ah Boon and bring him back.',
  },

  // Night of 14 Feb 1942. The city is being shelled; Sparky searches the dark, burning street.
  blackout: {
    start: [
      { who: 'Narrator', text: 'Blackout. Every light in the city is off. Except the fires.' },
    ],
    hint: 'Follow Boon’s trail. Stay under the five-foot ways.',
    coverHint: 'Hear a whistle? A shell is coming. Get under cover, fast!',
    knockedDown: [
      'Too close! Your ears are ringing. Get back under cover.',
      'The blast knocks you flat. Up you get. Stay covered this time.',
      'Dust everywhere. Find a five-foot way!',
    ],
    clues: [
      { title: 'A wooden clog', text: 'One of Boon’s clogs, in the middle of the road. He didn’t even stop to pick it up.', lines: [] },
      { title: 'Papa’s tiffin carrier', text: 'Papa’s tiffin carrier, still warm. Boon was bringing his papa dinner.', lines: [] },
      { title: 'A small voice', text: 'Someone is calling, somewhere ahead…', lines: [{ who: 'Boon', text: '(far away) Papa? Papa, where are you?' }] },
    ],
    found: [
      { who: 'Boon', text: 'Sparky? Sparky! You came!' },
      { who: 'Boon', text: 'Papa wasn’t at the fire post. They said he went to another fire. But everything is on fire!' },
      { who: 'Boon', text: 'I brought his photo. So I could ask people if they’ve seen him.' },
      { who: 'Sparky', react: 'hug' },
      { who: 'Boon', text: 'Can we go back now? Hold my hand. Don’t let go, okay?' },
    ],
    return: [
      { who: 'AhMa', text: 'Boon! You silly, silly boy. Never do that again, you hear me? Never.' },
      { who: 'AhMa', text: 'Thank you, Sparky. Come. Both of you. Sit close to me.' },
    ],
  },

  // Sunday 15 Feb 1942, first day of Chinese New Year. Around 8.30 pm the guns stop. Nobody knows why.
  // Each fragment is a rumour (some true, some false) plus a torn piece of that morning's newspaper.
  rumours: {
    card: { who: 'Card', text: 'Sunday, 15 February 1942. The first day of Chinese New Year.' },
    start: [
      { who: 'Hassan', text: 'Listen. The guns… they’ve stopped.' },
      { who: 'Siti', text: 'Is it over? Did we win?' },
      { who: 'AhMa', text: 'Nobody knows anything. Go and ask around, Sparky. And grab that newspaper. It’s blowing everywhere.' },
    ],
    hint: 'Ask the neighbours what they’ve heard. Collect the torn newspaper.',
    fragments: [
      {
        who: 'Hassan',
        lines: [
          { who: 'Hassan', text: 'Someone said American ships are coming to save us. Maybe that’s why it’s so quiet?' },
          { who: 'Hassan', text: 'Here. A bit of this morning’s paper. It blew right onto my foot.' },
        ],
      },
      {
        who: 'Soldier',
        lines: [
          { who: 'Soldier', text: 'I saw our officers driving up Bukit Timah Road. One of them was holding a white flag.' },
          { who: 'Soldier', text: 'Take this. I… I don’t even know where my unit is any more.' },
        ],
      },
      {
        who: 'Siti',
        lines: [
          { who: 'Siti', text: 'The goldsmith’s radio picked up a faraway station. It said the fighting is still going on. Hours ago.' },
          { who: 'Siti', text: 'I found this bit by his door. I think it’s the headline!' },
        ],
      },
    ],
    puzzle: { title: 'The last newspaper', hint: 'Drag the torn pieces together.' },
    // Real headline (Governor Sir Shenton Thomas's message), The Straits Times, 15 Feb 1942.
    headline: {
      text: 'Singapore Must Stand; It SHALL Stand',
      source: 'The Straits Times, 15 February 1942. A message from the Governor, Sir Shenton Thomas (NewspaperSG).',
    },
    reveal: [
      { who: 'Siti', text: '“Singapore must stand. It SHALL stand.” That’s what it says. This morning’s paper.' },
      { who: 'Rajan', text: 'Siti. Put the paper down. I’ve just come from the police post.' },
      { who: 'Rajan', text: 'The British have surrendered. This evening, at the Ford Factory in Bukit Timah. That’s why the guns stopped.' },
      { who: 'Hassan', text: 'Surrendered? The great fortress? Just like that?' },
      { who: 'Siti', text: 'I read that headline to everyone. I told them we’d be okay.' },
      { who: 'Boon', text: 'Ah Ma, the bombs stopped. That’s good, right?' },
      { who: 'AhMa', text: 'Quiet doesn’t always mean safe, Boon.' },
      { who: 'Rajan', text: 'I don’t know what happens next. But we face it together. Nobody on this street is alone.' },
    ],
    snapHint: 'Take a photo of this moment.',
  },

  // The same street under occupation, desaturated. Ration queue. Ah Ma gives Sparky banana money.
  epilogue: {
    card: { who: 'Card', text: 'Syonan-to. March 1942.' },
    street: [
      { who: 'Siti', text: 'They even changed our name. We’re not Singapore any more. Now it’s “{Syonan-to|Light of the South Island}”.' },
      { who: 'Hassan', text: 'See the sentry at the corner? Always bow when you pass. People who forget get slapped. Or worse.' },
      { who: 'Siti', text: 'Bapak’s papers are banned. Only the Japanese newspaper is allowed now.' },
      { who: 'Rajan', text: 'My warden days are over. Now I queue for rice like everyone else. Head down, mouth shut.' },
    ],
    // Sook Ching, shown through absence. Chinese men aged 18–50 were ordered to report for "screening";
    // Hong Lim Green in Chinatown was a screening centre. Many never returned.
    absence: [
      { who: 'AhMa', text: 'After the surrender, all the Chinese men had to go to {Hong Lim Green|a park nearby} to be “screened”.' },
      { who: 'AhMa', text: 'Boon’s papa went, like they told him. That was four weeks ago.' },
      { who: 'AhMa', text: 'Every morning I pour his {kopi|coffee}. Every night, I pour it away.' },
      { who: 'Boon', text: 'Ah Ma says Papa’s coming back. He is, right, Sparky?' },
      { who: 'Sparky', react: 'hug' },
    ],
    bananaGift: [
      { who: 'AhMa', text: 'Here, Sparky. “Banana money”. Their money. Every week it buys less and less rice.' },
      { who: 'AhMa', text: 'Keep it. One day this will be just paper. I hope that day comes soon.' },
    ],
    snapHint: 'Take one last photo.',
    // ≤ 70 words. Read over the final photograph as it develops.
    narration:
      'The Japanese Occupation lasted three years and seven months. People went hungry and lived in fear. In the Sook Ching, thousands of Chinese men were taken away and killed. Many families, like Boon’s, never found out what happened. On 12 September 1945, Japan formally surrendered in Singapore. The people who lived through it never forgot, so that we would remember too.',
    oldBoon: [
      { who: 'OldBoon', text: 'Papa never came home. Ah Ma kept the kopitiam going, and I grew up behind that counter.' },
      { who: 'OldBoon', text: 'That’s why I kept this camera, Sparky. Somebody has to remember.' },
    ],
  },

  // Photo-album fact cards, keyed by snap target.
  snaps: {
    Poster: {
      title: '“Fortress Singapore”',
      year: '1942',
      text: 'People called Singapore the “Gibraltar of the East”. Its big coastal guns could turn to face land, but they mostly had shells made for sinking ships, not stopping soldiers.',
    },
    Bicycle: {
      title: 'The bicycle blitzkrieg',
      year: '1941–42',
      text: 'Japanese soldiers rode bicycles, many taken from locals, all the way down Malaya. They moved faster than the British could retreat. Malaya fell in 55 days; the Causeway was blown up on 31 January 1942.',
    },
    Smoke: {
      title: 'A sky of black smoke',
      year: '1942',
      text: 'As the Japanese got closer, oil tanks were set on fire so the enemy couldn’t use the fuel. Thick black smoke hung over the city for days.',
    },
    Headline: {
      title: '“It SHALL Stand”',
      year: '15 Feb 1942',
      text: 'That morning, The Straits Times printed the Governor’s message: “Singapore Must Stand; It SHALL Stand.” That evening, the British surrendered. Most people heard the news by word of mouth.',
    },
    Banana: {
      title: '“Banana money”',
      year: '1942–45',
      text: 'The Japanese printed their own money. The $10 note had banana trees on it. They printed so much that prices shot up. By 1945, the notes were worthless.',
    },
  },

  // Accessibility: a caption for every sound. Keys match audio file names in public/assets/audio/.
  captions: {
    siren: '[Air-raid siren wails]',
    aircraft: '[Aircraft engines drone overhead]',
    impact: '[A bomb explodes nearby]',
    'distant-explosion': '[A distant explosion]',
    rumble: '[Distant guns rumble]',
    door: '[A heavy door bangs shut]',
    shutter: '[A shop shutter rattles]',
    street: '[Street sounds: voices, carts, footsteps]',
    murmur: '[People murmur quietly]',
    cicadas: '[Cicadas buzz]',
    myna: '[A myna bird calls]',
    'koel-short': '[A koel bird calls]',
    footstep: '[Footsteps]',
    'camera-shutter': '[Camera clicks and winds on]',
    'radio-static': '[Radio crackles and hisses]',
    paper: '[Newspaper rustles]',
    whistle: '[Warden’s whistle blows]',
    'shelter-room': '[Candle flickers; people breathing in a small room]',
    'pickup-chime': '',
    'ui-click': '',
    'theme-1942': '[Gentle music-box melody]',
    'shell-whistle': '[A shell whistles in, getting closer]',
    'ear-ring': '[Ears ringing]',
    'fire-crackle': '[Fire crackles]',
    'night-ambience': '[Distant fires and far-off guns]',
    heartbeat: '[Heartbeat]',
    'paper-piece': '[Paper tears]',
  },

  // For the album's "What's real vs imagined" page.
  realVsImagined: [
    'Imagined: Siti, Mr. Rajan, Ah Ma, Ah Boon, his papa, Pak Hassan, Uncle Lim and the shopkeepers are invented, and so is our street.',
    'Real: Chinatown was bombed and shelled in February 1942. Its streets were home to Chinese, Indian and Malay people.',
    'Real: ARP (Air Raid Precautions) wardens were volunteers from every community. They sounded warnings and guided people to shelter.',
    'Real: the Japanese landed on 8 February 1942. Oil tanks were burning, and by 14 February the water supply was failing.',
    'Real: Singapore surrendered at the Ford Factory, Bukit Timah, on 15 February 1942, the first day of Chinese New Year.',
    'Imagined: the words on the radio. Singapore’s own radio station was off the air by then, and news spread by word of mouth.',
    'Real: in the last days, Japanese guns shelled the city at night and many streets burned. Imagined: Boon’s search for his papa.',
    'Real: rumours flew that night. Some were true (officers did carry a white flag to the Japanese lines); some were false (no American ships were coming).',
    'Real: The Straits Times of 15 February 1942 carried the Governor’s message “Singapore Must Stand; It SHALL Stand”. Singapore surrendered that evening.',
    'Real: Singapore was renamed Syonan-to. People had to bow to Japanese sentries, food was rationed and “banana money” lost its value.',
    'Real: in the Sook Ching, Chinese men aged 18–50 were ordered to screening centres. Hong Lim Green in Chinatown was one. Thousands never returned.',
    'Real: the Japanese formally surrendered at the Municipal Building (now part of National Gallery Singapore) on 12 September 1945.',
    'Imagined: Boon’s story stands for many real families who never learned what happened to someone they loved.',
  ],

  credits: {
    audio: [
      'Air-raid siren: “Civil-defense-siren-waver.ogg” by Techtonic, public domain, via Wikimedia Commons (a modern US siren recording).',
      'Street, neighbours’ murmur and cicadas: recordings by Joseph Sardin, BigSoundBank.com, CC0.',
      'Asian koel: “Asian koel 1.flac” by Yosef Ben Melamed, via Wikimedia Commons, CC BY-SA 4.0 (trimmed and filtered).',
      'Common myna: XC509296 by James Ray (xeno-canto), via Wikimedia Commons, CC BY-SA 4.0 (trimmed and filtered).',
      'Footsteps: “Impact Sounds” by Kenney (kenney.nl), CC0.',
      'Music theme and all other sound effects: synthesised for this game.',
    ],
  },

  sources: [
    { title: 'Battle of Singapore', publisher: 'National Library Board, Infopedia', url: 'https://www.nlb.gov.sg/main/article-detail?cmsuuid=1afe9a7e-f0bd-4b11-9fe3-bb3aab31c3e8' },
    { title: 'Malayan Campaign', publisher: 'National Library Board, Infopedia', url: 'https://www.nlb.gov.sg/main/article-detail?cmsuuid=f2e9428f-c2cc-4c21-8a33-6ba79d03d77e' },
    { title: 'The Fall of Singapore: Sequence of Events (media release annex)', publisher: 'National Archives of Singapore', url: 'https://www.nas.gov.sg/archivesonline/data/pdfdoc/20120209002/annex_b_media_release_-_battle_for_singapore_(timeline).pdf' },
    { title: 'Former Ford Factory', publisher: 'Roots.gov.sg, National Heritage Board', url: 'https://www.roots.gov.sg/places/places-landing/Places/landmarks/Bukit-Timah-Heritage-Trail-WWII-Legacy-Trail/Former-Ford-Factory' },
    { title: 'Singapore Fell on 15 Feb 1942', publisher: 'SG101', url: 'https://www.sg101.gov.sg/resources/archives/onthisday-singapore-fell/' },
    { title: 'Johore Battery', publisher: 'National Library Board, Infopedia', url: 'https://www.nlb.gov.sg/main/article-detail?cmsuuid=d34fd0ae-8bd2-4082-a9d1-fb9c26e3a3e9' },
    { title: 'Churchill and the Guns of Singapore, 1941–42: Facing the Wrong Way?', publisher: 'The Churchill Project, Hillsdale College', url: 'https://winstonchurchill.hillsdale.edu/singapore-guns/' },
    { title: 'In Their Own Voices: Preparing for War in Singapore', publisher: 'BiblioAsia, National Library Board', url: 'https://biblioasia.nlb.gov.sg/vol-18/issue-4/jan-mar-2023/preparing-war-singapore/' },
    { title: 'Water shortages and rationing in Singapore', publisher: 'National Library Board, Infopedia', url: 'https://eresources.nlb.gov.sg/infopedia/articles/SIP_2020-02-20_192848.html' },
    { title: 'The Straits Times, 15 February 1942', publisher: 'NewspaperSG, National Library Board', url: 'https://eresources.nlb.gov.sg/newspapers/digitised/issue/straitstimes19420215-1' },
    { title: 'Nanyang Siang Pau', publisher: 'National Library Board, Infopedia', url: 'https://eresources.nlb.gov.sg/infopedia/articles/SIP_2017-01-10_095946.html' },
    { title: 'Utusan Melayu', publisher: 'National Library Board, Infopedia', url: 'https://eresources.nlb.gov.sg/infopedia/articles/SIP_1088_2007-06-12.html' },
    { title: 'Telok Ayer & Amoy Streets', publisher: 'Harmony in Diversity Gallery', url: 'https://www.harmonyindiversitygallery.gov.sg/streets-of-harmony/telok-ayer-amoy-streets/' },
    { title: 'Operation Sook Ching', publisher: 'National Library Board, Infopedia', url: 'https://www.nlb.gov.sg/main/article-detail?cmsuuid=cc4da337-3bcd-4f96-bdc6-5210646bdd90' },
    { title: 'The Sook Ching', publisher: 'BiblioAsia, National Library Board', url: 'https://biblioasia.nlb.gov.sg/vol-12/issue-4/jan-mar-2017/the-sook-ching/' },
    { title: 'Becoming Syonan', publisher: 'National Archives of Singapore (Former Ford Factory)', url: 'https://corporate.nas.gov.sg/former-ford-factory/whatson/exhibition-syonan/' },
    { title: 'Wartime Victuals: Surviving the Japanese Occupation', publisher: 'BiblioAsia, National Library Board', url: 'https://biblioasia.nlb.gov.sg/all-sections/vol-15-issue-1-apr-jun-2019-wartime-victuals/' },
    { title: 'Surviving the Japanese Occupation: War and its Legacies', publisher: 'BiblioAsia, National Library Board', url: 'https://biblioasia.nlb.gov.sg/vol-12/issue-4/jan-mar-2017/surviving-jpnese-occu/' },
    { title: 'Fall of Singapore 1942', publisher: 'Anzac Portal, Australian Department of Veterans’ Affairs', url: 'https://anzacportal.dva.gov.au/wars-and-missions/ww2/where/asia/singapore-1942' },
    { title: 'Leadership in the Malayan Campaign', publisher: 'The Cove, Australian Army', url: 'https://cove.army.gov.au/article/leadership-malayan-campaign' },
    { title: 'Japan’s surrender day at Singapore, 12 September 1945 (photograph)', publisher: 'Imperial War Museums', url: 'https://www.iwm.org.uk/collections/item/object/205161612' },
    { title: 'The Japanese formally surrender', publisher: 'National Library Board, Singapore History', url: 'https://www.nlb.gov.sg/main/article-detail?cmsuuid=90e0c9be-ec65-4bd1-9b71-28d6062acc38' },
  ],
};
