// Chapter 2 — "A Nation Is Born" (Queenstown, Monday 9 August 1965)
// All in-game text for Chapter 2. Script: docs/ch2-script.md. Research and citations:
// docs/research/1965-history.md.
//
// A line is { who, text } or { who: 'Sparky', react } (Sparky has no voice; `react` names an emote).
// Speakers: OldBoon, Boon, Siti, Farid, Ravi, Rajan, AhPek, Rohani, Letchumi, Neighbour, Radio, Narrator, Card,
//   and the corridor voices Barber, Schoolboy, Hawker, Girl, Schoolboy2.
// Glosses: {word|meaning} on the FIRST appearance of a non-English word. Lines ≤ 120 characters (glosses not counted).
// Everything spoken by a character is fiction. Facts, cards, the Proclamation and the press conference follow the sources.
// NATIVE REVIEW: every Malay, Hokkien and Tamil phrase is flagged "review" in a trailing comment until a native speaker
// has checked it. Tamil sentences are shown in English with "(in Tamil)" rather than guessed at.
//
// Voices (1965):
//   Boon (30): loud and quick like Ah Ma ("Aiyoh"), jokes to hide that he's scared of big news.
//   Siti (35): a teacher; still reads everything, but careful now. Never promises what she doesn't know.
//   Farid (16): Siti's little brother; cheeky, full of questions, wants the day to be exciting.
//   Mr. Rajan (63): calm, dry, short sentences. Grassroots leader at the community centre.
//   Ravi (16): Mr. Rajan's son. Quiet, watches everything.
//   Ah Pek Tan: old Hokkien uncle, grumbles, thirty years of the same order.
//   Makcik Rohani: Malay auntie, a seamstress upstairs. Warm, worried, sharp.
//   Auntie Letchumi: elderly Tamil auntie, polite and proud; speaks mostly Tamil.

export default {
  meta: {
    chapter: 2,
    title: 'A Nation Is Born',
    place: 'Queenstown, Singapore',
    dates: 'Monday, 9 August 1965',
  },

  contentNote: 'This chapter mentions the 1964 race riots. Nothing graphic is shown.',

  // Present day: the void deck. Mr. Boon introduces the second photo.
  bridge: [
    { who: 'OldBoon', text: 'The second photo. 1965. I was thirty by then, with my own {kopitiam|coffee shop} in Queenstown.' },
    { who: 'OldBoon', text: 'And the only television on the whole block! Everybody came to my shop to watch.' },
    { who: 'OldBoon', text: 'That was the day we woke up in one country… and went to bed in another.' },
  ],

  thenNow: {
    card: { who: 'Card', text: 'Queenstown. Today.' },
    before: [
      { who: 'OldBoon', text: 'My old shop is a minimart now. Same corner, same pillars. Everything else changed.' },
    ],
    hint: 'Raise the camera. Line up the old photo with the shops.',
    close: 'Almost… turn a little more.',
    locked: [
      { who: 'OldBoon', text: 'Ah, there. My kopitiam. Right next to the bookshop.' },
    ],
  },

  intro: [
    { who: 'Card', text: 'Queenstown, Singapore. Monday, 9 August 1965.' },
  ],

  // Boon recognises Sparky.
  morning: {
    greet: [
      { who: 'Boon', text: 'Eh… Sparky? No. Can’t be.' },
      { who: 'Boon', text: 'Twenty-three years, and you haven’t changed one bit! {Ah Ma|grandma} always said the bear would come back.' },
      { who: 'Boon', text: 'Come, come. I said I’d make kopi better than Ah Ma’s, right? Now you can help me prove it.' },
      { who: 'Sparky', react: 'nod' },
      { who: 'Farid', text: '{Abang|big brother} Boon, who’s this?' },
      { who: 'Boon', text: 'Old friend. Farid, show him the board. Sparky, two orders waiting. Go!' },
    ],
    board: [
      { who: 'Farid', text: 'Easy one. Kopi is coffee, teh is tea. Both come with sweet condensed milk, unless they say.' },
      { who: 'Farid', text: '“O” means no milk. “C” means evaporated milk. {Kosong|“zero” in Malay} means no sugar.' },
      { who: 'Farid', text: '{Siew dai|less sweet} is less sugar, {ga dai|more sweet} is more. {Peng|ice} means ice. Got it?' },
    ],
    hint: 'Make the drinks. Check the order board if you forget.',
  },

  // Kopi orders. order: { drink: 'kopi'|'teh', milk: 'condensed'|'O'|'C', sugar: 'normal'|'kosong'|'siew dai'|'ga dai', ice }
  orders: {
    ahpek1: {
      who: 'AhPek', seat: 'AhPek',
      order: { drink: 'kopi', milk: 'O', sugar: 'kosong', ice: false },
      ask: [{ who: 'AhPek', text: '{Kopi-O kosong|black coffee, no sugar}! Like always. Thirty years, same order!' }],
      correct: [{ who: 'AhPek', text: 'Hmm. Not bad. Not as good as your Ah Ma’s. Not bad.' }],
      wrong: [{ who: 'AhPek', text: '{Aiyoh|oh dear}, wrong one lah, bear. O means black. Kosong means no sugar. Again.' }],
    },
    rohani1: {
      who: 'Rohani', seat: 'Rohani',
      order: { drink: 'teh', milk: 'C', sugar: 'siew dai', ice: false },
      ask: [
        { who: 'Rohani', text: '{Teh-C|tea with evaporated milk}, {kurang manis|less sweet}, ya?' }, // review (Malay)
        { who: 'Farid', text: 'Kurang manis is Malay. Here we say siew dai. Same thing, different word!' },
      ],
      correct: [{ who: 'Rohani', text: '{Terima kasih|thank you}, {adik|little one}. You learn faster than Boon did.' }],
      wrong: [{ who: 'Rohani', text: 'Adik, that’s not what I asked. Teh-C, less sweet. You want my teeth to fall out?' }],
    },
  },

  // Optional morning chats (walk up to anyone).
  barks: {
    AhPek: [
      { who: 'AhPek', text: 'Indonesia still sending bombs. Remember {MacDonald House|a bank building bombed in March 1965}? Orchard Road!' },
      { who: 'AhPek', text: 'KL say one thing, Singapore say another. Every day in the paper, quarrel, quarrel.' },
    ],
    Rohani: [
      { who: 'Rohani', text: 'My husband says KL and Singapore are always quarrelling now. Like a married couple, he says.' },
      { who: 'Rohani', text: 'Last year, during the riots, I didn’t go downstairs for a week. I can still hear the shouting.' },
    ],
    Letchumi: [
      { who: 'Letchumi', text: '{Vanakkam|hello, in Tamil}. (She pats the stool beside her. Nobody sits there.)' }, // review (Tamil)
      { who: 'Letchumi', text: '(in Tamil) My son works at the naval base. Very good job. Very proud.' },
    ],
    Farid: [
      { who: 'Farid', text: '{Kak|big sister} Siti taught me to read before I could even walk properly. She never lets me forget.' },
      { who: 'Farid', text: 'Afternoon session, so mornings I work here. Abang Boon pays me in {kaya|coconut jam} toast.' },
    ],
    Ravi: [
      { who: 'Ravi', text: '…Hm? Oh. My father’s at the community centre. He said wait here.' },
      { who: 'Ravi', text: '(He goes back to his comic. He is watching everyone over the top of it.)' },
    ],
    Boon: [
      { who: 'Boon', text: 'That television cost me more than the shop makes in three months. Worth it. Everybody comes!' },
      { who: 'Boon', text: 'Every morning I pour one cup for Papa first. Ah Ma did it. So I do it.' },
    ],
  },

  lookCloser: {
    Rediffusion: 'A wooden box on the wall. It plays stories and songs all day.',
    TV: 'Boon’s pride and joy. Most families don’t own one yet.',
    MoneyTin: 'The coins in Boon’s money tin.',
  },

  // 10 a.m.: the radio (tuned to Radio Singapura's Malay service for Makcik Rohani).
  tenOClock: {
    radio: [
      // The real broadcast went out in Malay on Radio Singapura at 10 a.m. We show the English key sentence
      // (from the signed Proclamation) rather than invent a Malay translation.
      { who: 'Radio', text: '(in Malay) This is Radio Singapura. We interrupt this programme for a proclamation…' },
      { who: 'Radio', text: '(in Malay) “…Singapore shall be forever a sovereign democratic and independent nation…”' },
    ],
    react: [
      { who: 'Rohani', text: '{Singapura… keluar dari Malaysia?|Singapore… out of Malaysia?}' }, // review (Malay)
      { who: 'Farid', text: 'We’re out of Malaysia. He said independent. That means we’re our own country?' },
      { who: 'AhPek', text: 'Ah? What he say? {To̍k-li̍p|independent}? Who independent?' }, // review (Hokkien)
      { who: 'Boon', text: '(very quietly) Every time the news changes, somebody disappears.' },
      { who: 'Boon', text: 'Sparky. Go and get Siti. She’s down the corridor at the bookshop. She’ll know what it means.' },
    ],
  },

  errand: {
    hint: 'Find Siti at the bookshop down the corridor.',
    rumours: [
      { who: 'Barber', text: 'No more water from tomorrow! Johor will turn off the pipe, you wait!' },
      { who: 'Schoolboy', text: 'My brother says the army from KL is coming to take over!' },
      { who: 'Hawker', text: 'Independent? Then who’s going to buy my noodles? The British?' },
      { who: 'Girl', text: 'Does it mean no school tomorrow?' },
      { who: 'Schoolboy2', text: 'My cousin says they’re letting off firecrackers in Chinatown! Firecrackers, for what?' },
    ],
    siti: [
      { who: 'Siti', text: 'Sparky? (She stares, then laughs.) You look exactly the same. Exactly!' },
      { who: 'Siti', text: 'You heard? This morning’s paper doesn’t say a word about it. First time the paper’s behind.' },
      { who: 'Siti', text: 'Boon wants me to explain it to everyone? Sparky… no.' },
      { who: 'Siti', text: 'Last time I read the news out, I told the whole street we’d be safe. Remember?' },
    ],
    sitiNewspaper: [
      { who: 'Siti', text: '(She takes a folded, yellowed front page from her bag.) I still carry this. “It SHALL stand.”' },
      { who: 'Siti', text: 'It reminds me to read carefully. And never promise what I don’t know.' },
    ],
    sitiNoNewspaper: [
      { who: 'Siti', text: 'I think about that headline every time I open a newspaper.' },
    ],
    sitiGo: [
      { who: 'Sparky', react: 'nod' },
      { who: 'Siti', text: 'Okay. Okay! No promises. I’ll just tell them the truth.' },
    ],
  },

  worries: {
    start: [
      { who: 'Boon', text: 'Siti! Good. Sparky, keep the drinks coming. Everyone’s asking. Nobody’s ordering properly.' },
    ],
    hint: 'Take each order, ask Siti, then bring the drink and her answer.',
    askSiti: 'Ask Siti',
    list: [
      {
        id: 'water', who: 'AhPek', seat: 'AhPek',
        order: { drink: 'kopi', milk: 'condensed', sugar: 'normal', ice: true },
        ask: [{ who: 'AhPek', text: 'Kopi peng! More ice. Drink ice now, tomorrow maybe no water!' }],
        siti: [{ who: 'Siti', text: 'Tell him: the water agreements with Johor stay. It’s written into the separation deal.' }],
        after: [{ who: 'AhPek', text: 'Written down, ah? Hm. Okay. Ice still very nice.' }],
        fact: {
          title: 'Water from across the Causeway',
          text: 'Much of Singapore’s water came from Johor. The Separation Agreement promised that the 1961 and 1962 water deals would carry on. Even so, Singapore spent decades learning to make more of its own water.',
        },
      },
      {
        id: 'riots', who: 'Rohani', seat: 'Rohani',
        order: { drink: 'teh', milk: 'C', sugar: 'siew dai', ice: false },
        ask: [{ who: 'Rohani', text: 'Teh-C siew dai. (She says the Hokkien words carefully.) Ask Siti: will the riots come back?' }],
        siti: [
          { who: 'Siti', text: 'I don’t know. I won’t pretend I do. Last year I was scared of people I’d known all my life.' },
          { who: 'Siti', text: 'But look who’s making her tea. A bear, for a Malay makcik, in a Chinese kopitiam. Tell her that.' },
        ],
        after: [{ who: 'Rohani', text: '(She looks at Ah Pek, then at Sparky, and laughs a little.) A bear. Okay. A bear I can trust.' }],
        fact: {
          title: 'The 1964 riots',
          text: 'In July and September 1964, fights broke out between Chinese and Malay people in Singapore. 36 people were killed and hundreds were hurt. Families had to stay indoors during curfews. A year later, many still feared it could happen again.',
        },
      },
      {
        id: 'jobs', who: 'Letchumi', seat: 'Letchumi',
        order: { drink: 'teh', milk: 'O', sugar: 'normal', ice: false },
        ask: [
          { who: 'Letchumi', text: 'Teh-O. (in Tamil) And the naval base? My son works there. What happens to his job?' },
          { who: 'Ravi', text: '(looking up from his comic) She’s asking about the naval base. Her son works there. Is his job gone?' },
        ],
        siti: [{ who: 'Siti', text: 'The British bases are still here. Nothing closes today. Tell her: nothing closes today.' }],
        after: [
          { who: 'Ravi', text: '(in Tamil) {Amma|a respectful way to address a woman}, nothing closes today. The base is still there.' }, // review (Tamil)
          { who: 'Letchumi', text: '{Nandri|thank you, in Tamil}. (She pats the stool beside her again. This time, Makcik Rohani sits down.)' }, // review
        ],
        fact: {
          title: 'The British bases',
          text: 'Thousands of Singaporeans worked at the British military bases. The bases stayed after 1965. In 1968 Britain announced it would leave, and its forces were gone by the end of 1971.',
        },
      },
    ],
    done: [
      { who: 'Siti', text: '(quietly) That wasn’t so bad. No promises. Just the truth.' },
    ],
  },

  evening: {
    card: { who: 'Card', text: 'Later that day.' },
    rajan: [
      { who: 'Rajan', text: 'Evening, Boon. Evening… Sparky? (A pause.) Of course it’s Sparky. Why not. Today anything can happen.' },
    ],
    rajanRice: [
      { who: 'Rajan', text: 'Boon. Your Ah Ma’s rice kept us alive in that shelter. I never paid her back. Tonight’s kopi is on me.' },
    ],
    rajanNoRice: [
      { who: 'Rajan', text: 'Busy night, Boon. Your Ah Ma would be proud.' },
    ],
    photo: [
      { who: 'Boon', text: 'Papa always gets the best seat. Right up there, next to Ah Ma.' },
    ],
    bundles: [
      { who: 'Neighbour', text: 'You’re the bear who held my rope! In ’42! My hands were shaking so badly. Remember?' },
    ],
    water: [
      { who: 'Siti', text: 'Pak Hassan used to talk about you. “That bear brought me water. Better than satay.” He’d have loved tonight.' },
    ],
    crossOrder: {
      who: 'AhPek', seat: 'Letchumi',
      order: { drink: 'teh', milk: 'C', sugar: 'siew dai', ice: false },
      ask: [
        { who: 'AhPek', text: 'Bear! Teh-C for the Tamil auntie. Siew dai. I asked her already. (He waves at Auntie Letchumi.)' },
        { who: 'Letchumi', text: '(nodding, smiling) Siew dai!' },
      ],
      correct: [{ who: 'Boon', text: 'Wah. Now even Ah Pek is taking orders. Maybe I should pay him in kaya toast too.' }],
      wrong: [{ who: 'AhPek', text: 'No lah! Teh-C, siew dai. I asked her properly, you know.' }],
    },
    hint: 'One last order before the news.',
    tvCall: [
      { who: 'Boon', text: 'Quiet, everybody! It’s starting! Farid, turn it up!' },
    ],
  },

  // The TV: the real 9 August 1965 press conference (118 s excerpt, captions in public/assets/video/lky-1965-en.json).
  tv: {
    label: 'Prime Minister Lee Kuan Yew · press conference, 9 August 1965',
    credit: 'Original footage: Lee Kuan Yew’s press conference, 9 Aug 1965 (Singapore Broadcasting Corporation archive), via Wikimedia Commons, public domain.',
    skip: 'Hold to skip',
    reactions: [
      // Played during the long silences, while the footage keeps rolling.
      { at: 30, who: 'Farid', text: '(whispering) He’s crying. The Prime Minister is crying.' },
      { at: 48, who: 'Siti', text: '(quietly) He really didn’t want this.' },
    ],
    // After the clip: the words he said later in the same press conference (NAS transcript lky19650809b).
    after: [
      { who: 'Narrator', text: 'Later in the same press conference, he said:' },
      { who: 'Narrator', text: '“We are going to have a multi-racial nation in Singapore. We will set the example.”' },
      { who: 'Narrator', text: '“This is not a Malay nation; this is not a Chinese nation; this is not an Indian nation.”' },
      { who: 'Narrator', text: '“Everybody will have his place: equal; language, culture, religion.”' },
    ],
    snapHint: 'Take a photo of this moment.',
  },

  wallChoice: {
    lines: [
      { who: 'Boon', text: 'Ah Ma put up a picture every time something big happened. Good or bad. So we never forget.' },
      { who: 'Boon', text: 'Today needs to go on the wall, Sparky. You choose.' },
    ],
    prompt: 'Something for the wall. What will you put up?',
    options: [
      { id: 'newspaper', label: 'Tomorrow’s newspaper', react: [{ who: 'Siti', text: '“Singapore is out.” This time the headline is true. And we’ll read what comes next together.' }] },
      { id: 'flag', label: 'The state flag', react: [
        { who: 'Farid', text: 'Wait, we already had a flag? And a song? Since 1959? Kak, why didn’t you tell me?' },
        { who: 'Siti', text: 'I did. You weren’t listening.' },
      ] },
      { id: 'sign', label: 'A new sign in four languages', react: [{ who: 'Boon', text: 'English, Chinese, Malay, Tamil. Makcik will check the Malay. Auntie Letchumi, the Tamil. Everyone’s kopitiam.' }] },
      { id: 'calendar', label: 'The calendar page: 9 August', react: [{ who: 'Boon', text: 'Just the date. When I’m old, I’ll look at it and remember exactly how today felt.' }] },
    ],
  },

  coda: [
    { who: 'Rajan', text: '(at the doorway, putting on his shoes) No water of our own. No army. Two battalions, that’s all.' },
    { who: 'Rajan', text: 'Somebody’s going to have to defend this place, Boon.' },
    { who: 'Farid', text: '(to Sparky, quietly) Somebody, huh?' },
  ],

  oldBoon: [
    { who: 'OldBoon', text: 'We didn’t ask to be a country, Sparky. Nobody was ready.' },
    { who: 'OldBoon', text: 'But everyone in my shop that night decided the same thing. We’ll make it work. Together.' },
    { who: 'OldBoon', text: 'One photo left. 1967. That one… that one I almost didn’t take.' },
  ],

  // Photo-album cards, keyed by snap target.
  snaps: {
    Rediffusion: {
      title: 'Rediffusion',
      year: '1949–',
      text: 'Wired radio. For $5 a month, a cable brought music and famous Chinese dialect storytellers into homes and coffee shops.',
    },
    TV: {
      title: 'Television Singapura',
      year: '1963',
      text: 'Singapore’s TV service began on 15 February 1963. Only about 1 in 12 homes had a set, so people gathered at community centres and coffee shops to watch.',
    },
    MoneyTin: {
      title: 'Whose dollar?',
      year: '1965',
      text: 'In 1965 Singapore still used the Malaya and British Borneo dollar. Its own money came in June 1967. The new $1 note showed Queenstown flats!',
    },
    Anguish: {
      title: '9 August 1965',
      year: '9 Aug 1965',
      text: 'Singapore left Malaysia and became an independent country. At a press conference shown on TV, Prime Minister Lee Kuan Yew broke down. He had believed all his adult life that Singapore belonged with Malaysia.',
    },
    Wall_newspaper: {
      title: '“Singapore is out”',
      year: '10 Aug 1965',
      text: 'The Straits Times front page the next morning. Siti’s newspapers now tell two stories: a promise that failed in 1942, and a truth everyone had to face together in 1965.',
    },
    Wall_flag: {
      title: 'Majulah Singapura',
      year: '1959',
      text: 'Singapore’s state flag, coat of arms and anthem, “Majulah Singapura” (“Onward, Singapore”), were unveiled on 3 December 1959, six years before independence.',
    },
    Wall_sign: {
      title: 'Everyone’s kopitiam',
      year: '1965',
      text: 'English, Chinese, Malay and Tamil. Kopitiams were already places where every community met, and kopitiam lingo mixed Hokkien, Malay and English long before 1965.',
    },
    Wall_calendar: {
      title: '9 August',
      year: '1965',
      text: 'The day Singapore became independent. It has been celebrated as National Day every year since.',
    },
  },

  // Chalk order board (drawn on a canvas at runtime).
  orderBoard: {
    title: '文记咖啡店',
    rows: [['咖啡', 'KOPI', '10¢'], ['咖啡乌', 'KOPI-O', '10¢'], ['红茶', 'TEH', '10¢'], ['冰', '+ PENG', '5¢'], ['面包', 'ROTI KAYA', '15¢']],
    legend: 'O = no milk · C = evaporated milk · kosong = no sugar · siew dai = less sweet · ga dai = more sweet',
  },

  shopSign: { zh: '文记咖啡店', en: 'BOON KEE COFFEE SHOP' },
  nowSign: 'CORNER MINIMART',
  neighbourSigns: { Tailor: ['裁缝', 'TAILOR'], Provision: ['杂货', 'PROVISIONS'], Bookshop: ['书局', 'BOOKSHOP'], Barber: ['理发', 'BARBER'] },
  newSign: ['BOON KEE COFFEE SHOP', '文记咖啡店', 'KEDAI KOPI BOON KEE', 'பூன் கீ காப்பிக் கடை'], // review (Malay, Tamil)
  notice: ['NO SPITTING', '请勿随地吐痰', 'DILARANG MELUDAH'], // review (Malay)

  captions: {
    'ceiling-fan': '[A ceiling fan whirs]',
    'tv-static': '[TV static hisses]',
    'kopi-pour': '[Kopi pours into a cup]',
    'cup-clink': '[A cup clinks on a saucer]',
    'spoon-stir': '[A spoon stirs a cup]',
    firecrackers: '[Firecrackers go off a few streets away]',
    'radio-song': '[A Malay pop song plays on the radio]',
    'radio-static': '[Radio crackles and hisses]',
    murmur: '[Customers chatting]',
    street: '[Voices and footsteps in the corridor]',
    cicadas: '[Cicadas buzz]',
    myna: '[A myna bird calls]',
    footstep: '[Footsteps]',
    'camera-shutter': '[Camera clicks and winds on]',
    'pickup-chime': '',
    'ui-click': '',
    paper: '[Newspaper rustles]',
    'theme-1942': '[Gentle music-box melody]',
  },

  realVsImagined: [
    'Imagined: Boon’s kopitiam, its block, Siti, Farid, Ravi, Mr. Rajan, Ah Pek Tan, Makcik Rohani and Auntie Letchumi.',
    'Real: on 9 August 1965 Singapore separated from Malaysia. The Proclamation went out on Radio Singapura at 10 a.m. The only 1965 recording known to survive is the Malay reading. In the game you read the words.',
    'Real: Lee Kuan Yew’s press conference was recorded at noon at Broadcasting House and shown on TV the same day. The footage and his words are real.',
    'Real: some people let off firecrackers in Chinatown that morning. Others were shocked and afraid. Reactions were mixed.',
    'Real: the worries in the kopitiam: water from Johor, the 1964 riots, jobs at the British bases, Indonesia’s Confrontation.',
    'Real: kopitiam lingo mixes Hokkien, Malay and English, and people of every community ordered in it.',
    'Real: The Straits Times on 10 August 1965 ran the headline “Singapore is out”.',
    'Real: Singapore had just two infantry battalions in 1965. Many of its soldiers were on their way to Sabah that week.',
    'Imagined: the rumours in the corridor stand for the many that spread that day.',
  ],

  credits: {
    audio: [
      'Press conference footage: “Lee Kuan Yew’s press conference on 9 Aug 1965” (Singapore Broadcasting Corporation archive), via Wikimedia Commons, public domain (PD-SG-broadcast). 118 s excerpt, archive timecode cropped.',
      'Press conference captions: adapted from Wikimedia Commons English TimedText contributors, CC BY-SA 4.0.',
      'Ceiling fan, customers’ murmur, corridor and cicadas: recordings by Joseph Sardin, BigSoundBank.com, CC0.',
      'Radio song, kopi, cups, firecrackers and TV static: synthesised for this game (original).',
      'Common myna: XC509296 by James Ray (xeno-canto), via Wikimedia Commons, CC BY-SA 4.0 (trimmed and filtered).',
    ],
  },

  sources: [
    { title: 'Transcript of a press conference given by the Prime Minister, Mr. Lee Kuan Yew, 9 August 1965 (lky19650809b)', publisher: 'National Archives of Singapore', url: 'https://www.nas.gov.sg/archivesonline/data/pdfdoc/lky19650809b.pdf' },
    { title: 'Lee Kuan Yew’s press conference on 9 Aug 1965 (video)', publisher: 'Wikimedia Commons', url: 'https://commons.wikimedia.org/wiki/File:Lee_Kuan_Yew%27s_press_conference_on_9_Aug_1965.webm' },
    { title: 'Singapore separates from Malaysia and becomes independent', publisher: 'National Library Board, Infopedia', url: 'https://www.nlb.gov.sg/main/article-detail?cmsuuid=dc1efe7a-8159-40b2-9244-cdb078755013' },
    { title: 'Proclamation of Singapore', publisher: 'National Archives of Singapore', url: 'https://www.nas.gov.sg/archivesonline/speeches/record-details/740ab5e6-115d-11e3-83d5-0050568939ad' },
    { title: 'The Straits Times, 10 August 1965', publisher: 'NewspaperSG, National Library Board', url: 'https://eresources.nlb.gov.sg/newspapers/digitised/issue/straitstimes19650810-1' },
    { title: 'Communal riots of 1964', publisher: 'National Library Board, Infopedia', url: 'https://www.nlb.gov.sg/main/article-detail?cmsuuid=3cb72867-1eec-4caa-96b2-365e1301cbb1' },
    { title: 'Water agreements', publisher: 'Ministry of Foreign Affairs, Singapore', url: 'https://www.mfa.gov.sg/about-mfa/key-issues/water-agreements/' },
    { title: 'Withdrawal of the British Far East Command from Singapore', publisher: 'SG101', url: 'https://www.sg101.gov.sg/resources/archives/onthisday-withdrawal-of-british-far-east-command-from-singapore-british-far-east-withdrew-from-singapore/' },
    { title: 'Rediffusion', publisher: 'National Library Board, Infopedia', url: 'https://www.nlb.gov.sg/main/article-detail?cmsuuid=9d4b7199-fa91-417d-832d-b4160c7c9d59' },
    { title: 'Singapore TV', publisher: 'BiblioAsia, National Library Board', url: 'https://biblioasia.nlb.gov.sg/vol-12/issue-1/apr-jun-2016/singapore-tv/' },
    { title: 'History of currency in Singapore', publisher: 'Monetary Authority of Singapore', url: 'https://www.mas.gov.sg/currency/history-of-currency-in-singapore' },
    { title: 'National identity and symbols', publisher: 'Ministry of Culture, Community and Youth', url: 'https://www.mccy.gov.sg/sectors/resilience-and-engagement/national-identity-and-symbols/' },
    { title: 'Makan place: coffee shops', publisher: 'BiblioAsia, National Library Board', url: 'https://biblioasia.nlb.gov.sg/vol-14/issue-3/oct-dec-2018/makan-place-coffee-s/' },
  ],
};
