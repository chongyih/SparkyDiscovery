// Turns src/chapters/ww2-text.js into a readable screenplay (docs/ch1-script.md) for review.
import { writeFileSync } from 'node:fs';
import T from '../src/chapters/ww2-text.js';

const N = { OldBoon: 'MR. BOON (91)', AhMa: 'AH MA', Boon: 'AH BOON (7)', Hassan: 'PAK HASSAN', Rajan: 'MR. RAJAN', Siti: 'SITI (12)', Shopkeeper: 'SHOPKEEPER', Soldier: 'SOLDIER', Neighbour: 'NEIGHBOUR', Narrator: 'NARRATOR' };
const out = [];
const gl = (t) => (t || '').replace(/\{([^|}]+)\|([^}]*)\}/g, '$1 [$2]');
const line = (l) => {
  if (!l) return;
  if (l.who === 'Card') out.push(`> **[Title card]** ${l.text}`);
  else if (l.who === 'Sparky') out.push(`*(Sparky ${({ nod: 'nods eagerly', startle: 'jumps at the siren', peer: 'peers into the viewfinder', hug: 'gives a hug' })[l.react] || l.react})*`);
  else out.push(`**${N[l.who] || l.who}:** ${l.requires ? `*(if Ah Ma is with you)* ` : ''}${gl(l.text)}`);
  out.push('');
};
const lines = (a) => (a || []).forEach(line);
const note = (t) => { out.push(`*${t}*`, ''); };
const h = (t) => out.push(`## ${t}`, '');

out.push('# Chapter 1 — The Fortress Falls', '', `_${T.meta.dates}. Content note: ${T.contentNote}_`, '');
h('0 · Prologue — a Queenstown void deck, today'); lines(T.prologue);
h('1 · Then & Now — Telok Ayer today'); line(T.thenNow.card); lines(T.thenNow.before); note(`Objective: ${T.thenNow.hint}`); lines(T.thenNow.locked);
h('2 · Morning papers — Thursday, 12 February 1942'); lines(T.intro); lines(T.papers.start); note(`Objective: ${T.papers.hint}`);
T.drops.forEach((d) => { note(`Deliver to the ${d.shop.toLowerCase()} (${d.paper}):`); lines(d.handoff); note(`Fact card — ${d.factTitle}: ${d.fact}`); });
out.push('**Optional chats** (walk up to anyone):', '');
for (const [who, a] of Object.entries(T.papers.barks)) { out.push(`- **${N[who]}**`); a.forEach((l) => out.push(`  - ${l.text}`)); }
out.push('');
out.push('**Optional kindnesses** (remembered in later chapters):', '');
T.kindness.forEach((k) => { out.push(`- *${k.label}* — ${k.ask.map((l) => `${N[l.who]}: “${l.text}”`).join(' ')} → ${k.thanks.map((l) => `“${l.text}”`).join(' ')}`); });
out.push('', '**Look closer** (camera hotspots):', '');
for (const [k, t] of Object.entries(T.lookCloser)) out.push(`- *${k}:* ${t} — photo card: **${T.snaps[k].title}** — ${T.snaps[k].text}`);
out.push('');
lines(T.papers.done);
h('3 · Air raid'); lines(T.raid.start); note(`Objective: ${T.raid.hint}`);
note('Finding Ah Ma:'); lines(T.raid.found.AhMa); note('Finding Ah Boon (under a kopitiam table):'); lines(T.raid.found.Boon); note('Finding Pak Hassan (by his broken satay cart):'); lines(T.raid.found.Hassan);
note(`While they follow you (random): ${T.raid.follow.map((l) => `${N[l.who]}: “${l.text}”`).join(' · ')}`);
note('A shophouse on the route is hit:'); lines(T.raid.hit); note('At the shelter:'); lines(T.raid.arrive);
h('4 · Room for two things'); lines(T.shelterChoice.lines); note(`Choice: ${T.shelterChoice.prompt}`);
T.shelterChoice.options.forEach((o) => { out.push(`- **${o.label}** → ${o.react.map((l) => `${N[l.who]}: “${l.text}”`).join(' ')}`); }); out.push('');
note('Inside the shelter:'); lines(T.shelterTransition.before); note('(The candle goes out.)'); line(T.shelterTransition.card); lines(T.shelterTransition.after);
h('5 · Blackout search — night of 14 February'); lines(T.blackout.start); note(`Objective: ${T.blackout.hint} — Tip: ${T.blackout.coverHint}`);
note(`If caught in the open: ${T.blackout.knockedDown.join(' / ')}`);
T.blackout.clues.forEach((c, i) => { note(`Clue ${i + 1} — ${c.title}: ${c.text}`); lines(c.lines); });
note('Finding Boon (behind a tipped handcart):'); lines(T.blackout.found); note('Back at the shelter:'); lines(T.blackout.return);
h('6 · Rumours in the silence — 15 February'); line(T.rumours.card); lines(T.rumours.start); note(`Objective: ${T.rumours.hint}`);
T.rumours.fragments.forEach((f) => lines(f.lines));
note(`Puzzle — ${T.rumours.puzzle.title}: the torn front page reads “${T.rumours.headline.text}” (${T.rumours.headline.source})`);
lines(T.rumours.reveal); note(`Photo card: **${T.snaps.Headline.title}** — ${T.snaps.Headline.text}`);
h('7 · Syonan-to — March 1942'); line(T.epilogue.card); lines(T.epilogue.street); lines(T.epilogue.absence); lines(T.epilogue.bananaGift);
note(`Photo card: **${T.snaps.Banana.title}** — ${T.snaps.Banana.text}`);
out.push(`**NARRATOR:** ${T.epilogue.narration}`, '');
h('Back at the void deck'); lines(T.epilogue.oldBoon);
writeFileSync(new URL('../docs/ch1-script.md', import.meta.url), out.join('\n'));
console.log('wrote docs/ch1-script.md', out.length, 'lines');
