// Chapter 3 — "The First Intake" (September 1967 to Saturday 2 March 1968) and the 2026 ending.
// All in-game text for Chapter 3. Script: docs/ch3-script.md. Research and citations: docs/research/1967-history.md.
//
// A line is { who, text } or { who: 'Sparky', react } (Sparky has no voice; `react` names an emote).
// Speakers: OldBoon, Boon, Siti, Farid, AhHock, Ravi, Leo, Osman, Rajan, AhHockMa, Neighbour, Rohani, AhPek, Letchumi,
//   PA (the Minister's speech over the loudspeakers), Farid77, Irfan, Narrator, Card.
// Glosses: {word|meaning} on the FIRST appearance of a non-English word. Lines ≤ 120 characters (glosses not counted).
// Everything spoken by a character is fiction, except the Minister's words (sourced, see credits).
// NATIVE REVIEW: every Malay and Hokkien phrase is flagged "review" in a trailing comment until a native speaker (and, for
// the drill words, an SAF reviewer) has checked it. No 1967 source confirms the exact drill wording (research §2).
//
// Voices (1967–68):
//   Boon (32): runs the kopitiam; jokes less now. Scared for Farid, so he's cross. Won't open letters.
//   Siti (37): teacher, Farid's big sister. Calm, dry. Reads the news for everyone.
//   Farid (18): grown up since 1965, wants to be the "somebody". Bossy when nervous. Calls Boon "Abang".
//   Ah Hock (18): hawker's son, Hokkien only. Big, stubborn, homesick. Short sentences.
//   Ravi (18): Mr. Rajan's son. Nearly silent. Watches, counts, remembers.
//   Leo Pereira (18): Eurasian, English-educated, talks nonstop, has seen every war film.
//   Sergeant Osman: a Malay regular from before NS. Deadpan; every joke is one sentence long. Secretly kind.

export default {
  meta: {
    chapter: 3,
    title: 'The First Intake',
    place: 'Taman Jurong Camp, Singapore',
    dates: 'September 1967 – 2 March 1968',
  },

  contentNote: 'This chapter is about Singapore’s first national servicemen. There is no fighting in it.',

  // Present day: the void deck. Mr. Boon introduces the last photo.
  bridge: [
    { who: 'OldBoon', text: 'Farid was eighteen. One of the first boys ever called up to be a soldier. The very first batch.' },
    { who: 'OldBoon', text: 'And I told him not to go. I shouted at him, even.' },
    { who: 'OldBoon', text: 'Go on, Sparky. Last one. Look through it.' },
  ],

  thenNow: {
    card: { who: 'Card', text: 'Taman Jurong Greens. Today.' },
    before: [
      { who: 'OldBoon', text: 'It’s a park now. The camp’s buildings are all gone.' },
      { who: 'OldBoon', text: 'But the field is the same field. That’s where they marched.' },
    ],
    hint: 'Raise the camera. Line up the old view with the field.',
    close: 'Almost… turn a little more.',
    locked: [
      { who: 'OldBoon', text: 'There. I stood right there. Behind a little X.' },
    ],
  },

  // Beat 2: the kopitiam on the morning of the send-off.
  sendoffMorning: {
    card: { who: 'Card', text: 'Queenstown, Singapore. September 1967.' },
    lines: [
      { who: 'Boon', text: 'Sparky? Two years, and here you are again. You only turn up when something big happens.' },
      { who: 'Farid', text: '{Abang|big brother}, stop wiping. It’s clean already.' },
      { who: 'Farid', text: 'I signed the papers at Kallang last month. It’s done. Nine hundred of us, full-time. The first ever.' },
      { who: 'Boon', text: '(not looking up) Good iron isn’t made into nails. Good men don’t become soldiers. Everybody knows that.' },
      { who: 'Farid', text: 'Nobody says that anymore.' },
      { who: 'Boon', text: 'I say it. So don’t go.' },
      { who: 'Farid', text: 'Mr. Rajan said somebody has to defend this place. I want it to be somebody like us.' },
      { who: 'Farid', text: 'Sparky’s coming too. Right, Sparky?' },
      { who: 'Sparky', react: 'nod' },
      { who: 'Boon', text: 'Aiyoh. Not you also.' },
      { who: 'Boon', text: '(turning away) The kopitiam can’t close. I’m not coming to the community centre. Go.' },
    ],
    // Boon has gone into the back; something is on the counter.
    tiffin: [{ who: 'Farid', text: 'This is… his papa’s {tiffin carrier|stacked lunch tins}. He never lets anyone touch it.' }],
    tiffinFallback: [{ who: 'Farid', text: 'He packed lunch. He’s angry, and he packed lunch.' }],
    // Ch2 wall payoff, one line, by the Chapter 2 choice.
    wall: {
      newspaper: [{ who: 'Siti', text: '(reading Farid’s call-up letter aloud) “…to report for full-time National Service.” This time the news is true.' }],
      flag: [{ who: 'Farid', text: '(touching the flag on the way out) This time I know the song. All the words.' }],
      sign: [{ who: 'Siti', text: 'Look. He painted your name on the sign last night. Small, at the bottom. Don’t tell him you saw.' }],
      calendar: [{ who: 'Siti', text: 'He tore off today’s calendar page and pinned it beside 9 August. So he’ll remember.' }],
    },
    objective: 'Take the tiffin carrier and go with Farid.',
  },

  // Beat 3: the send-off at the community centre.
  sendoff: {
    // Enlistment day: shown as a card (day / event / place), then a fact.
    card: { day: 'Sunday, 3 September 1967', title: 'Enlistment Day', place: 'Queenstown Community Centre' },
    fact: { title: 'Enlistment day', text: 'On Sunday 3 September 1967, the first full-time national servicemen gathered at community centres across Singapore with their families, then left for camp in army lorries.' },
    lines: [
      { who: 'Rajan', text: 'Ravi. Eat properly. Write to your mother.' },
      { who: 'Siti', text: '(to Farid) He’ll come round. He’s Boon. He needs time to be wrong first.' },
    ],
    neighbour: [{ who: 'Neighbour', text: 'The rope bear! Now you’re going to be a soldier? Aiyoh. Eat well, ah.' }],
    // Optional kindness: Ah Hock's grandmother won't go near the truck.
    ahMa: [{ who: 'AhHockMa', text: '(in Hokkien) Good iron isn’t made into nails…' }], // review (Hokkien)
    ahMaThanks: [{ who: 'AhHockMa', text: '(in Hokkien) Tell him to eat them. All of them.' }], // review (Hokkien)
    ahMaPrompt: 'Take the oranges to the truck',
    truckPrompt: 'Climb into the truck',
    objective: 'Say goodbye, then climb into the truck.',
    fact: { title: 'Fifty dinners', text: 'Many families were worried about their sons becoming soldiers. Community leaders held about fifty send-off dinners for the first batch, and at some of them each young man got a medal.' },
  },

  // Beat 4a: the lorry arrives at Taman Jurong Camp; Sergeant Osman meets his section.
  arrival: {
    card: { who: 'Card', text: 'Taman Jurong Camp. September 1967.' },
    fallIn: [
      { who: 'Osman', text: 'Down! Down from the lorry! Line up. One line. Here.' },
    ],
    lines: [
      { who: 'Osman', text: 'I am Sergeant Osman. For six months I am your mother, your father and your alarm clock.' },
      { who: 'Osman', text: 'Names. Short. You.' },
      { who: 'Leo', text: 'Leonard Pereira, Sergeant! Leo. From Katong. I’ve seen every war film at the Capitol, so—' },
      { who: 'Osman', text: 'Short, I said. Next.' },
      { who: 'Farid', text: 'Farid, Sergeant. Queenstown.' },
      { who: 'AhHock', text: '(in Hokkien) …Ah Hock.' }, // review (Hokkien)
      { who: 'Osman', text: 'No English? No Malay? Hm. You will learn. Next.' },
      { who: 'Ravi', text: '(quietly) Ravi.' },
      { who: 'Osman', text: '(looking down at Sparky) And you… are very short. Never mind.' },
      { who: 'Osman', text: 'Four boys who can’t talk to each other, and a bear. My section.' },
    ],
  },

  // Beat 4b: day one — the first drill.
  dayOne: {
    card: { who: 'Card', text: 'The next morning.' },
    drillIntro: [
      { who: 'Osman', text: 'Listen. I say two words. The first word is a warning. The second word, you move. Not before.' },
      { who: 'Osman', text: 'In this army we drill in Malay. Chinese, Malay, Indian, Eurasian, everybody learns the same words.' },
      { who: 'Leo', text: 'Yes, Sergeant! Completely, Sergeant!' },
      { who: 'Osman', text: 'You don’t. But you will.' },
    ],
    drillHint: 'Wait for the second word. Then move.',
    noPictures: 'Now. No more pictures.',
    end: [
      { who: 'Osman', text: 'Four boys, four directions.' },
      { who: 'Osman', text: '(to Sparky) And you. Tomorrow, stand on a box.' },
    ],
  },

  // Lines the drill shows in its own caption (the dialogue box would cover the buttons).
  drill: {
    assist: 'Do it for me',
    again: 'Again!',
    early: 'I said wait.',
    wrong: 'Wrong way!',
    late: 'Too slow!',
    good: ['Hm. Not bad.', 'Better.', 'Again like that.'],
    bump: 'Two boys, one mistake. Very efficient.',
    leo: 'Pereira. This is not a race. Nobody is chasing you.',
    whisper: { // Farid, after two misses on the same command
      kanan: '(whispering) Kanan is right!',
      kiri: '(whispering) Kiri is left!',
      belakang: '(whispering) Belakang, all the way round!',
      sedia: '(whispering) Sedia! Stand up straight!',
    },
    dismissed: [{ who: 'Osman', text: 'Seksyen… BERSURAI! (Dismissed!)' }], // review (Malay)
    nudge: { early: '(an elbow: wait for it)', wrong: '(an elbow: other way)', late: '(an elbow: now!)' },
    forgive: 'Close enough. Next.',
  },

  // Beat 5: rifles, some weeks later.
  rifles: {
    card: { who: 'Card', text: 'Some weeks later. Weapons training.' },
    issue: [
      { who: 'Osman', text: 'This is the M16. From today it goes where you go.' },
      { who: 'Osman', text: 'You will know it better than your mother’s face. Take one. Gently.' },
    ],
    take: 'Take a rifle from the rack',
    after: [
      { who: 'Leo', text: 'It’s lighter than in the films.' },
      { who: 'Osman', text: 'Pereira. Everything is lighter than in the films.' },
    ],
    slingHint: 'Sling your rifle on the word.',
    done: [{ who: 'Osman', text: 'Good. Now it goes where you go. Even to the parade.' }],
    fact: { title: 'The M16', text: 'In the late 1960s the Singapore Armed Forces adopted the American M16 rifle. Singapore later made its own under licence, as the M16S1. In this game the rifles are only for drill.' },
  },

  // Beat 5b: the letter round in the barracks.
  letter: {
    card: { who: 'Card', text: 'The barracks. February 1968.' },
    dinner: [
      { who: 'AhHock', text: '(in Hokkien, eating from the tiffin carrier) Wah. Who made this?' }, // review (Hokkien)
      { who: 'Farid', text: 'Abang Boon. He’s angry with me. He still cooks like this when he’s angry.' },
      { who: 'Farid', text: 'He hasn’t written. Not once.' },
    ],
    start: [
      { who: 'Farid', text: 'How do I tell Abang Boon I’m okay, when he won’t believe it?' },
      { who: 'Farid', text: 'Sparky. You start. What do I say first?' },
    ],
    choiceTitle: 'How should Farid start the letter?',
    openings: [
      { id: 'honest', label: 'Honest', text: 'The first night, I didn’t sleep at all. I was scared, Abang. Like you said.' },
      { id: 'brave', label: 'Brave', text: 'Don’t worry about me. I’m fine. Really.' },
      { id: 'funny', label: 'Funny', text: 'Good news: I can turn left now. Bad news: Leo still can’t.' },
    ],
    heading: 'Taman Jurong Camp, February 1968',
    greeting: 'Abang Boon,',
    body: [
      'We are four boys who don’t talk the same. Ah Hock only speaks Hokkien. Ravi hardly speaks. Leo never stops.',
      'But when the sergeant shouts, we turn together now.',
      'Your tiffin fed five of us. Even Ravi had seconds, and Ravi never says anything.',
      'The passing-out parade is on Saturday, 2 March. Families can come. Please come, Abang. Bring the camera.',
    ],
    sign: 'Farid',
    takeRound: [{ who: 'Farid', text: 'Take it round, Sparky. Everyone should add something. So he knows I’m not alone here.' }],
    objective: 'Take the letter to the section.',
    ps: {
      AhHock: {
        prompt: 'Ask Ah Hock for a P.S.',
        lines: [{ who: 'AhHock', text: '(in Hokkien, to Farid) You write. I say.' }], // review (Hokkien)
        text: 'P.S. Boon-hiaⁿ, lí m̄-bián kiaⁿ. Guá ē chiàu-kòo i.', // review (Hokkien: "Brother Boon, don't be scared. I'll look after him.")
        gloss: '“Brother Boon, don’t be scared. I’ll look after him.”',
      },
      Ravi: {
        prompt: 'Ask Ravi for a P.S.',
        lines: [{ who: 'Card', text: 'Ravi says nothing. He draws a little map of the parade square and marks an X.' }],
        text: 'Stand here. Best view.',
        map: true,
      },
      Leo: {
        prompt: 'Ask Leo for a P.S.',
        lines: [{ who: 'Leo', text: 'A P.S.? Oh, I’m good at those. Give it here.' }],
        text: 'P.P.S. Army food is terrible. Please send more of whatever was in the tiffin. — Leo (the handsome one)',
      },
    },
    paw: { prompt: 'Add Sparky’s paw print', text: '🐾' },
    ravisMap: [{ who: 'Card', text: 'Ravi gets up and hands you his map anyway.' }],
    enough: [{ who: 'Farid', text: 'It’s enough. He’ll get it.' }],
    backToFarid: 'Bring the letter back to Farid.',
  },

  // Beat 5c: the reading, a few days later.
  reading: {
    card: { who: 'Card', text: 'Queenstown. A few days later.' },
    start: [
      { who: 'Siti', text: 'Three days, Boon. It’s been sitting there three days.' },
      { who: 'Boon', text: 'Letters bring bad news. I know what’s in it.' },
      { who: 'Siti', text: 'You don’t. That’s the problem.' },
    ],
    react: {
      honest: [{ who: 'Boon', text: '(quietly) …Me too.' }],
      brave: [{ who: 'Boon', text: 'He’s lying. He always says “really” when he lies.' }],
      funny: [{ who: 'Boon', text: '(laughing for the first time in weeks) Which one is Leo?' }],
    },
    ahHock: [
      { who: 'Siti', text: '(trying, badly) “Boon… hee-ah… lee… mm-bee-an…” Aiyoh, what language is this?' },
      { who: 'Boon', text: '(laughing) Aiyoh, your Hokkien!' },
      { who: 'Boon', text: '(then quietly) He says don’t be scared. He says he’ll look after him.' },
    ],
    ravi: [{ who: 'Siti', text: 'And a map. “Stand here. Best view.” That must be Mr. Rajan’s boy.' }],
    leo: [
      { who: 'Siti', text: '“Please send more of whatever was in the tiffin.”' },
      { who: 'Boon', text: 'Cheeky.' },
    ],
    paw: [
      { who: 'Siti', text: 'And at the bottom… a paw print?' },
      { who: 'Boon', text: 'That bear.' },
    ],
    end: [{ who: 'Siti', text: 'So use it.' }],
  },

  // Beat 6: the passing-out parade.
  parade: {
    card: { day: 'Saturday, 2 March 1968', title: 'The Passing-Out Parade', place: 'Taman Jurong Camp' },
    fact: { title: 'The first passing-out parade', text: 'After about 25 weeks of training, Singapore’s first full-time national servicemen passed out at Taman Jurong Camp. Defence Minister Lim Kim San took the salute, and their families watched from the stands.' },
    banner: 'PASSING-OUT PARADE · FIRST INTAKE OF NATIONAL SERVICEMEN',
    start: [
      { who: 'Farid', text: '(barely moving his lips) He’s not coming.' },
      { who: 'AhHock', text: '(in Hokkien) Wait for the word.' }, // review (Hokkien)
    ],
    hint: 'No pictures now. Wait for the word, then move.',
    lookHint: 'Eyes right. Look to the stands.',
    stands: {
      neighbour: { who: 'Neighbour', text: 'That’s the rope bear! Front row!' },
      ahMa: { who: 'AhHockMa', text: '(in Hokkien, to Siti, proud) That one is my grandson.' }, // review (Hokkien)
      always: [{ who: 'Rohani', text: '(dabbing her eyes) Look how straight they walk.' }, { who: 'AhPek', text: 'Hmph. Not bad.' }],
    },
    reveal: { who: 'Farid', text: '(a whisper) Abang.' },
    minister: { who: 'PA', text: '“You are the pioneers in a new field and pioneers in a most honourable way of serving the country.”' },
    after: [
      { who: 'Farid', text: 'It came back, Abang. I came back.' },
      { who: 'Boon', text: '(taking it, then handing him a full one) Leo’s P.S. said the food was terrible.' },
      { who: 'Boon', text: 'All of you. Stand together. Sparky, you too. In the middle.' },
      { who: 'Boon', text: '(to himself) Look at them. All of them, together.' },
    ],
  },

  oldBoon: [
    { who: 'OldBoon', text: 'I almost didn’t go. I stood at the bus stop for half an hour.' },
    { who: 'OldBoon', text: 'Then I thought: if I don’t go, who takes his photo? So I ran all the way.' },
    { who: 'Farid77', text: '(walking up with his grandson) Still telling that story, Abang?' },
  ],

  // The 2026 ending at the void deck.
  ending: {
    arrive: [
      { who: 'OldBoon', text: 'He’s late. Always late for everything, except parades.' },
      { who: 'Farid77', text: '(setting down the tiffin carrier) Your turn to fill it, Abang. Fifty-eight years and you still owe me.' },
      { who: 'OldBoon', text: 'Irfan! Look at you. Another one. Aiyoh.' },
      { who: 'Irfan', text: '{Atuk|grandpa} says you cried at his parade.' },
      { who: 'OldBoon', text: 'Your Atuk talks too much.' },
    ],
    envelope: [
      { who: 'Farid77', text: 'You gave me your roll to take to the photo shop. Then you phoned and said don’t.' },
      { who: 'Farid77', text: 'I did anyway. (He puts an envelope on the table.)' },
      { who: 'Farid77', text: 'Eighty-four years, Abang. Open it.' },
    ],
    envelopePrompt: 'Open the envelope',
    photos: {
      ww2: [
        { who: 'OldBoon', text: 'Ah Ma. And the street. I was under that table.' },
        { who: 'Farid77', text: 'You were so small.' },
      ],
      ind: [
        { who: 'OldBoon', text: 'My kopitiam. The night we became a country.' },
        { who: 'Farid77', text: 'Look, Kak Siti. She’s reading, of course.' },
      ],
      ns: [
        { who: 'Farid77', text: 'Look at us. Four boys who couldn’t talk to each other.' },
        { who: 'OldBoon', text: 'And a bear.' },
      ],
    },
    reunion: [{ who: 'Farid77', text: 'Ah Hock phoned last week. Leo too. He still talks too much. Ravi sent a map to the reunion. With an X.' }],
    selfie: [{ who: 'Irfan', text: 'Atuk, Uncle Boon, Sparky. Squeeze in.' }],
    last: [
      { who: 'OldBoon', text: '(pushing the Brownie across the table) Keep it, Sparky. Somebody has to remember.' },
      { who: 'OldBoon', text: 'Now it’s you.' },
    ],
    nextTime: [
      { who: 'Card', text: 'Irfan opens the old camera case. Inside is a second roll of film. The label is too worn to read.' },
      { who: 'Farid77', text: 'Whose is that?' },
      { who: 'OldBoon', text: '(smiling) Next time.' },
    ],
  },

  lookCloser: {
    MoneyTin: 'New notes in Boon’s money tin.',
    Mexicans: 'Two advisers in straw hats, taking notes.',
    Marker: 'A heritage marker in the grass.',
  },

  // Photo-album cards.
  snaps: {
    MoneyTin: {
      title: 'Our own dollar',
      year: '1967',
      text: 'Singapore’s own money came out on 12 June 1967. The new $1 note showed Queenstown’s flats, so Boon’s customers paid with a picture of their own neighbourhood.',
    },
    Uniform: {
      title: 'Temasek green',
      year: '1967',
      text: 'The first national servicemen wore a green cotton uniform called the No. 4. They starched it so stiff that it could stand up by itself.',
    },
    Mexicans: {
      title: 'The “Mexicans”',
      year: '1967',
      text: 'Israeli military advisers helped train Singapore’s first soldiers. To keep it secret, people called them “Mexicans”. Some wore straw hats.',
    },
    Marker: {
      title: 'The first NS camp',
      year: '1967',
      text: 'Taman Jurong Camp was Singapore’s first camp for full-time national servicemen. Blocks of one-room flats were turned into barracks in a hurry. A heritage marker was put up here in 2017.',
    },
    Letter: {
      title: 'A letter home',
      year: 'Feb 1968',
      text: 'Farid’s letter, with a P.S. from the section. Many of the first recruits spoke no language in common. They learned to understand each other anyway.',
    },
    Parade: {
      title: '2 March 1968',
      year: '2 Mar 1968',
      text: 'Singapore’s first full-time national servicemen passed out at Taman Jurong Camp. About 9,000 young men had registered; 900 were chosen for full-time training. In August 1968 they marched at the National Day Parade in the pouring rain.',
    },
    Phone: {
      title: 'Today',
      year: '2026',
      text: 'Two old friends and a bear, at a void deck in Queenstown. National Service has carried on, one intake after another, since 1967.',
    },
  },

  heritageMarker: ['FORMER TAMAN JURONG CAMP', 'Singapore’s first national service camp, 1967'], // generic, not the real marker's text
  ccSign: ['COMMUNITY CENTRE', '民众联络所', 'PUSAT MASYARAKAT'], // review (Chinese, Malay)
  banner: 'GOOD LUCK, OUR NATIONAL SERVICEMEN!',

  captions: {
    'band-march': '[A military band plays a march]',
    'truck-engine': '[An army lorry’s engine rumbles]',
    'night-ambience': '[Frogs and insects in the dark]',
    cicadas: '[Cicadas buzz]',
    murmur: '[A crowd chatting]',
    footstep: '[Boots on the square]',
    'camera-shutter': '[Camera clicks and winds on]',
    'pickup-chime': '',
    'ui-click': '',
    paper: '[Paper rustles]',
    'theme-1942': '[Gentle music-box melody]',
  },

  realVsImagined: [
    'Imagined: Farid, Ah Hock, Ravi, Leo Pereira, Sergeant Osman, Ah Hock’s Ah Ma, Irfan, and Boon’s kopitiam.',
    'Real: in 1967 about 9,000 young men born in the first half of 1949 registered for National Service. About 900 were chosen for full-time service in two new battalions, 3 SIR and 4 SIR, at Taman Jurong Camp. They enlisted at the Central Manpower Base in Kallang in August 1967.',
    'Real: their passing-out parade was at Taman Jurong Camp on Saturday, 2 March 1968. Minister Lim Kim San took the salute. His words in this chapter are quoted from a 2017 speech by DPM Tharman Shanmugaratnam, who repeated them.',
    'Real: many families were unhappy about sons becoming soldiers. A Chinese saying goes “good iron isn’t made into nails, good men don’t become soldiers”. Community leaders held send-off dinners and ceremonies to win families over.',
    'Real: the recruits spoke many languages. One first-batch recruit remembered a buddy who spoke neither English nor Malay, so they used sign language.',
    'Likely, not certain: drill commands were given in Malay, as they are today. No 1967 record we found says so.',
    'Real: Israeli advisers helped train the first soldiers, and people called them “Mexicans” to keep it secret.',
    'Real: the Temasek green uniform, starched stiff enough to stand up by itself.',
    'Partly known: the SAF adopted the M16 rifle in the late 1960s. Which rifles the very first intake carried at their passing-out parade is not confirmed; the game shows M16s, carried slung for drill.',
    'Not known: whether any Malay Singaporeans were among the first 900. In the early years of National Service many Malay Singaporeans were not called up. Today every fit young man is called up, whatever his race or religion. Farid is an imagined character.',
    'Real: the camp site is now Taman Jurong Greens, a park, with a heritage marker put up in 2017. The marker in the game is a stand-in, not a copy.',
  ],

  credits: {
    audio: [
      'Band march, boots and lorry: synthesised for this game (original).',
    ],
  },

  sources: [
    { title: 'DPM Tharman Shanmugaratnam at the placing of the heritage marker at the first NS camp, Taman Jurong (6 Aug 2017)', publisher: 'Prime Minister’s Office', url: 'https://www.pmo.gov.sg/newsroom/dpm-tharman-shanmugaratnam-placing-heritage-marker-first-ns-camp-singapore-and-taman/' },
    { title: 'Implementation of National Service', publisher: 'Roots.gov.sg, National Heritage Board', url: 'https://www.roots.gov.sg/stories-landing/stories/implementation-of-national-service/story' },
    { title: 'Former Taman Jurong Camp (Jurong Heritage Trail)', publisher: 'Roots.gov.sg, National Heritage Board', url: 'https://www.roots.gov.sg/places/places-landing/Places/landmarks/jurong-heritage-trail/former-taman-jurong-camp' },
    { title: 'Early years of National Service', publisher: 'National Library Board, Infopedia', url: 'https://www.nlb.gov.sg/main/article-detail?cmsuuid=00a6d12b-9d71-491a-936e-1f09c7b23653' },
    { title: 'Compulsory National Service', publisher: 'National Library Board, Infopedia', url: 'https://www.nlb.gov.sg/main/article-detail?cmsuuid=debf50d7-d81a-4b31-9c0d-65dd932aab8c' },
    { title: '50 years of National Service', publisher: 'BiblioAsia, National Library Board', url: 'https://biblioasia.nlb.gov.sg/vol-13/issue-2/jul-sep-2017/50years-of-ns/' },
    { title: 'Passing out parade of national servicemen at Taman Jurong Camp, 2 March 1968 (photographs)', publisher: 'National Archives of Singapore', url: 'https://www.nas.gov.sg/archivesonline/photographs/record-details/cd2ab198-1161-11e3-83d5-0050568939ad' },
    { title: 'Oral history interview: Albel Singh (OH 004356)', publisher: 'National Archives of Singapore', url: 'https://www.nas.gov.sg/archivesonline/oral_history_interviews/record-details/601a4641-a3bc-11e9-9972-001a4a5ba61b' },
    { title: 'Oral history interview (OH 004508): the early days of SAFTI', publisher: 'National Archives of Singapore', url: 'https://www.nas.gov.sg/archivesonline/oral_history_interviews/record-details/321f690a-435d-11ea-a865-001a4a5ba61b' },
    { title: 'Senior Minister Lee Kuan Yew’s dialogue with AMP and Majlis Pusat (2 Mar 2001)', publisher: 'National Archives of Singapore', url: 'https://www.nas.gov.sg/archivesonline/data/pdfdoc/2001030204.htm' },
    { title: 'Our history', publisher: 'Ministry of Defence', url: 'https://www.mindef.gov.sg/about-us/history/' },
    { title: 'A March in August', publisher: 'Roots.gov.sg, National Heritage Board', url: 'https://www.roots.gov.sg/stories-landing/stories/A-March-in-August' },
    { title: 'Ranks and drill commands', publisher: 'Central Manpower Base', url: 'https://www.cmpb.gov.sg/life-in-ns/saf/ranks-and-drill-commands/' },
  ],
};
