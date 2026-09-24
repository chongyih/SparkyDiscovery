const KEY = 'sparky.album.v1';
const $ = (id) => document.getElementById(id);

/** Capture the centre of the canvas (the viewfinder frame) as a sepia-toned square photo. */
export function capturePhoto(canvas, { size = 512, tone = 'sepia' } = {}) {
  const W = canvas.width, H = canvas.height;
  // Must match .vf-frame CSS: side = min(66vh, 62vw), centred at 50% x / 46% y.
  const cssSide = Math.min(innerHeight * 0.66, innerWidth * 0.62);
  const sx = W / innerWidth, sy = H / innerHeight;
  const side = cssSide * sx;
  const cx = W / 2, cy = innerHeight * 0.46 * sy;
  const out = document.createElement('canvas');
  out.width = out.height = size;
  const g = out.getContext('2d');
  g.drawImage(canvas, cx - side / 2, cy - (cssSide * sy) / 2, side, cssSide * sy, 0, 0, size, size);
  const img = g.getImageData(0, 0, size, size);
  const d = img.data;
  let seed = 1234;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const i = (y * size + x) * 4;
      let r = d[i], gg = d[i + 1], b = d[i + 2];
      if (tone === 'sepia') {
        const l = 0.3 * r + 0.59 * gg + 0.11 * b;
        r = l * 1.07 + 18; gg = l * 0.9 + 8; b = l * 0.7;
      }
      const dx = x / size - 0.5, dy = y / size - 0.5;
      const v = 1 - Math.min(1, (dx * dx + dy * dy) * 1.9) * 0.6;
      const n = (rnd() - 0.5) * 16;
      d[i] = Math.min(255, r * v + n); d[i + 1] = Math.min(255, gg * v + n); d[i + 2] = Math.min(255, b * v + n);
    }
  }
  g.putImageData(img, 0, 0);
  return out.toDataURL('image/jpeg', 0.84);
}

/** The photo album: persisted photos + reference pages (real vs imagined, sources, credits). */
export class Album {
  constructor() {
    this.photos = {};
    this.slots = []; // [{ id, chapter, title, year }]
    this.pages = { facts: '', sources: '' };
    try { this.photos = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch { this.photos = {}; }
    this.el = $('album');
    $('btn-album-close').onclick = () => this.close();
    this.el.querySelectorAll('.album-tabs button').forEach((b) => {
      b.onclick = () => this.tab(b.dataset.tab);
    });
  }

  get isOpen() { return !this.el.classList.contains('hidden'); }

  setSlots(slots) { this.slots = slots; }

  setPages({ realVsImagined = [], sources = [], credits = [] }) {
    const li = (s) => `<li>${s}</li>`;
    this.pages.facts = `<h3>What's real, and what's imagined</h3><ul>${realVsImagined.map(li).join('')}</ul>`;
    const src = sources.map((s) => (typeof s === 'string' ? li(s) : li(`<a href="${s.url}" target="_blank" rel="noopener">${s.title}</a>${s.note ? ` — ${s.note}` : ''}`))).join('');
    const cr = credits.map((c) => li(typeof c === 'string' ? c : `${c.what}: ${c.who}${c.licence ? ` (${c.licence})` : ''}`)).join('');
    this.pages.sources = `<h3>Sources</h3><ul>${src}</ul><h3>Credits</h3><ul>${cr}</ul>`;
  }

  add(photo) {
    this.photos[photo.id] = photo;
    // Keep only the latest few free photos (each is a ~40 KB JPEG in local storage).
    const free = Object.values(this.photos).filter((p) => p.free && p.chapter === photo.chapter);
    free.slice(0, Math.max(0, free.length - 4)).forEach((p) => { delete this.photos[p.id]; });
    try { localStorage.setItem(KEY, JSON.stringify(this.photos)); } catch { /* storage full — keep in memory */ }
    document.getElementById('btn-album').classList.add('badge');
  }

  has(id) { return !!this.photos[id]; }

  clearChapter(chapter) {
    for (const [id, p] of Object.entries(this.photos)) if (p.chapter === chapter) delete this.photos[id];
    try { localStorage.setItem(KEY, JSON.stringify(this.photos)); } catch { /* ignore */ }
  }

  render() {
    const grid = this.slots.map((s) => {
      const p = this.photos[s.id];
      if (!p) return `<div class="album-photo"><div class="empty">?</div><div class="yr">${s.year || ''}</div><h4>Not yet taken</h4><p>${s.hint || ''}</p></div>`;
      return `<div class="album-photo"><img src="${p.image}" alt="${p.title}"/><div class="yr">${p.year || ''}</div><h4>${p.title}</h4><p>${p.text}</p></div>`;
    }).join('');
    const taken = this.slots.filter((s) => this.photos[s.id]).length;
    const own = Object.values(this.photos).filter((p) => p.free).slice(-6);
    const ownHTML = own.length ? `<h3>Sparky’s own photos</h3><div class="album-grid">${own.map((p) => `<div class="album-photo"><img src="${p.image}" alt="Sparky’s photo"/><div class="yr">${p.year}</div><p>${p.text}</p></div>`).join('')}</div>` : '';
    $('album-photos').innerHTML = `<p class="album-count">Memories captured: <b>${taken} / ${this.slots.length}</b> — raise your camera (C, right-click or the camera button) to look closer.</p><div class="album-grid">${grid}</div>${ownHTML}`;
    $('album-facts').innerHTML = this.pages.facts;
    $('album-sources').innerHTML = this.pages.sources;
  }

  tab(name) {
    this.el.querySelectorAll('.album-tabs button').forEach((b) => b.classList.toggle('active', b.dataset.tab === name));
    ['photos', 'facts', 'sources'].forEach((t) => $(`album-${t}`).classList.toggle('hidden', t !== name));
  }

  open() {
    this.render();
    this.el.classList.remove('hidden');
    document.getElementById('btn-album').classList.remove('badge');
    this.onToggle?.(true);
  }

  close() {
    this.el.classList.add('hidden');
    this.onToggle?.(false);
  }
}
