// Torn-newspaper puzzle: a front page drawn on a canvas, cut into jagged pieces the player
// drags (mouse or touch) back into place. Pieces snap when close. Resolves when complete.

function wrapLines(g, text, maxW) {
  const words = text.split(' ');
  const lines = [];
  let line = '';
  for (const w of words) {
    const t = line ? `${line} ${w}` : w;
    if (g.measureText(t).width > maxW && line) { lines.push(line); line = w; } else line = t;
  }
  if (line) lines.push(line);
  return lines;
}

/** Draw a period-style broadsheet front page (layout only; body text is illegible filler). */
export function drawFrontPage({ masthead = 'THE STRAITS TIMES', date = 'SUNDAY, FEBRUARY 15, 1942', headline, size = 900 }) {
  const W = size, H = Math.round(size * 1.25);
  const c = document.createElement('canvas');
  c.width = W; c.height = H;
  const g = c.getContext('2d');
  g.fillStyle = '#e9dfc6';
  g.fillRect(0, 0, W, H);
  // Paper grain + foxing.
  const img = g.getImageData(0, 0, W, H);
  for (let i = 0; i < img.data.length; i += 4) {
    const n = (Math.random() - 0.5) * 14;
    img.data[i] += n; img.data[i + 1] += n; img.data[i + 2] += n * 0.8;
  }
  g.putImageData(img, 0, 0);
  for (let i = 0; i < 18; i++) {
    const x = Math.random() * W, y = Math.random() * H, r = 10 + Math.random() * 60;
    const grd = g.createRadialGradient(x, y, 0, x, y, r);
    grd.addColorStop(0, 'rgba(150,110,60,0.12)'); grd.addColorStop(1, 'rgba(150,110,60,0)');
    g.fillStyle = grd; g.fillRect(x - r, y - r, r * 2, r * 2);
  }
  const ink = '#1c1814';
  g.fillStyle = ink;
  g.textAlign = 'center';
  g.font = `bold ${Math.round(W * 0.085)}px "Gelasio", Georgia, serif`;
  g.fillText(masthead, W / 2, H * 0.085);
  g.fillRect(W * 0.05, H * 0.1, W * 0.9, 3);
  g.font = `${Math.round(W * 0.022)}px "Gelasio", Georgia, serif`;
  g.fillText(`${date}   ·   SINGAPORE   ·   PRICE 5 CENTS`, W / 2, H * 0.125);
  g.fillRect(W * 0.05, H * 0.135, W * 0.9, 1.5);
  // Headline, wrapped, heavy.
  g.font = `900 ${Math.round(W * 0.078)}px "Gelasio", Georgia, serif`;
  const lines = wrapLines(g, headline.toUpperCase(), W * 0.88);
  lines.forEach((l, i) => g.fillText(l, W / 2, H * 0.215 + i * W * 0.088));
  const bodyTop = H * 0.215 + lines.length * W * 0.088 + 10;
  g.fillRect(W * 0.05, bodyTop - 6, W * 0.9, 1.5);
  // Columns of filler "text" (grey bars) and a photo box.
  const cols = 4, gap = W * 0.02, colW = (W * 0.9 - gap * (cols - 1)) / cols;
  for (let cI = 0; cI < cols; cI++) {
    const x0 = W * 0.05 + cI * (colW + gap);
    let y = bodyTop + 10;
    if (cI === 1) { g.fillStyle = '#6b6258'; g.fillRect(x0, y, colW * 2 + gap, H * 0.2); g.fillStyle = ink; y += H * 0.21; }
    if (cI === 2 && y < bodyTop + H * 0.2) y = bodyTop + 10 + H * 0.21;
    g.font = `bold ${Math.round(W * 0.02)}px Georgia, serif`;
    g.textAlign = 'left';
    while (y < H * 0.96) {
      const w = colW * (0.7 + Math.random() * 0.3);
      g.fillStyle = 'rgba(28,24,20,0.55)';
      g.fillRect(x0, y, w, W * 0.007);
      y += W * 0.016;
      if (Math.random() < 0.06) y += W * 0.02;
    }
    g.fillStyle = ink;
    g.textAlign = 'center';
  }
  return c;
}

/**
 * Show the puzzle overlay. `pieces` = grid (cols×rows) cut with jagged edges.
 * Returns a promise resolved when all pieces are placed.
 */
export function newspaperPuzzle({ canvas, cols = 2, rows = 2, title = 'Piece the newspaper together', hint = 'Drag the pieces into place', onPlace, bindAssist }) {
  return new Promise((resolve) => {
    const root = document.createElement('div');
    root.className = 'puzzle';
    root.innerHTML = `<div class="puzzle-head"><h3>${title}</h3><p>${hint}</p></div><div class="puzzle-board"></div><button class="btn small puzzle-assist">Place a piece for me <kbd>E</kbd></button>`;
    document.body.appendChild(root);
    const board = root.querySelector('.puzzle-board');
    const bw = Math.min(innerHeight * 0.62 / 1.25, innerWidth * 0.34);
    const bh = bw * 1.25;
    board.style.width = `${bw}px`;
    board.style.height = `${bh}px`;
    const pw = bw / cols, ph = bh / rows;
    let placed = 0;
    const total = cols * rows;
    const url = canvas.toDataURL('image/jpeg', 0.85);
    const placers = [];
    // Keyboard / gamepad / accessibility: place the next piece automatically.
    const assist = () => { placers.find((p) => !p.piece.classList.contains('placed'))?.place(); };
    root.querySelector('.puzzle-assist').onclick = assist;
    bindAssist?.(assist);
    // Jagged tear offsets shared between neighbours so edges match.
    const jag = (n) => Array.from({ length: n }, () => (Math.random() - 0.5) * 0.08);
    const vEdges = Array.from({ length: cols - 1 }, () => jag(9));
    const hEdges = Array.from({ length: rows - 1 }, () => jag(9));
    for (let r = 0; r < rows; r++) {
      for (let cI = 0; cI < cols; cI++) {
        const piece = document.createElement('div');
        piece.className = 'puzzle-piece';
        const pts = [];
        const top = r === 0 ? null : hEdges[r - 1];
        const bot = r === rows - 1 ? null : hEdges[r];
        const left = cI === 0 ? null : vEdges[cI - 1];
        const right = cI === cols - 1 ? null : vEdges[cI];
        // Polygon in board-relative percentages, then clipped.
        const X = (u) => ((cI + u) / cols) * 100, Y = (v) => ((r + v) / rows) * 100;
        const n = 9;
        for (let i = 0; i <= n; i++) pts.push([X(i / n), Y(top ? top[Math.min(i, n - 1)] : 0)]);
        for (let i = 0; i <= n; i++) pts.push([X(1 + (right ? right[Math.min(i, n - 1)] : 0)), Y(i / n)]);
        for (let i = n; i >= 0; i--) pts.push([X(i / n), Y(1 + (bot ? bot[Math.min(i, n - 1)] : 0))]);
        for (let i = n; i >= 0; i--) pts.push([X(left ? left[Math.min(i, n - 1)] : 0), Y(i / n)]);
        piece.style.cssText = `width:${bw}px;height:${bh}px;background-image:url(${url});background-size:${bw}px ${bh}px;clip-path:polygon(${pts.map(([a, b]) => `${a}% ${b}%`).join(',')})`;
        // Scatter around the board.
        // Scatter each piece into the side margins, keeping its visible cell fully on screen.
        const side = (r * cols + cI) % 2 ? 1 : -1;
        const boardLeft = (innerWidth - bw) / 2;
        const margin = Math.max(pw * 0.6, boardLeft);
        const lo = pw / 2 + 8, hi = Math.max(lo, margin - pw * 0.15);
        const cellX = lo + Math.random() * (hi - lo);
        const targetX = side < 0 ? cellX : innerWidth - cellX;
        let ox = targetX - (boardLeft + (cI + 0.5) * pw);
        let oy = (Math.random() - 0.5) * bh * 0.5;
        let rot = (Math.random() - 0.5) * 30;
        const apply = () => { piece.style.transform = `translate(${ox}px, ${oy}px) rotate(${rot}deg)`; };
        apply();
        board.appendChild(piece);
        let drag = null;
        // clip-path also clips hit-testing, so each full-size layer only receives events on its own shape.
        piece.addEventListener('pointerdown', (e) => {
          if (piece.classList.contains('placed')) return;
          e.preventDefault();
          drag = { x: e.clientX, y: e.clientY, ox, oy };
          piece.setPointerCapture?.(e.pointerId);
          piece.classList.add('dragging');
          rot *= 0.4; apply();
        });
        piece.addEventListener('pointermove', (e) => {
          if (!drag) return;
          ox = drag.ox + (e.clientX - drag.x);
          oy = drag.oy + (e.clientY - drag.y);
          apply();
        });
        const end = () => {
          if (!drag) return;
          drag = null;
          piece.classList.remove('dragging');
          if (Math.hypot(ox, oy) < Math.max(40, pw * 0.3)) {
            ox = 0; oy = 0; rot = 0; apply();
            piece.classList.add('placed');
            placed++;
            onPlace?.(placed, total);
            if (placed === total) {
              root.classList.add('done');
              setTimeout(() => { resolve(); }, 900);
              setTimeout(() => root.remove(), 1400);
            }
          }
        };
        const autoPlace = () => {
          if (piece.classList.contains('placed')) return;
          drag = { x: 0, y: 0, ox: 0, oy: 0 }; ox = 0; oy = 0;
          end();
        };
        placers.push({ place: autoPlace, piece });
        piece.addEventListener('pointerup', end);
        piece.addEventListener('pointercancel', end);
      }
    }
  });
}
