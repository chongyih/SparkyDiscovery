// Checks src/chapters/ns-text.js (Chapter 3 + the ending) against the phone-bubble and card limits in docs/design.md:
// spoken lines ≤ 120 characters (glosses not counted), album cards ≤ 40 words, fact toasts ≤ 45 words.
// Run: node tools/check_text_ns.mjs
import text from '../src/chapters/ns-text.js';

const problems = [];
const plain = (s) => s.replace(/\{([^|}]+)\|[^}]*\}/g, '$1');
const words = (s) => plain(s).trim().split(/\s+/).length;

(function walk(node, path) {
  if (Array.isArray(node)) return node.forEach((n, i) => walk(n, `${path}[${i}]`));
  if (node && typeof node === 'object') {
    if (typeof node.who === 'string' && typeof node.text === 'string' && node.who !== 'Card' && plain(node.text).length > 120)
      problems.push(`${path}: ${plain(node.text).length} chars`);
    for (const [k, v] of Object.entries(node)) walk(v, `${path}.${k}`);
  }
})(text, 'text');

for (const [k, c] of Object.entries(text.snaps)) words(c.text) > 40 && problems.push(`snaps.${k}: ${words(c.text)} words`);
words(text.sendoff.fact.text) > 45 && problems.push(`sendoff.fact: ${words(text.sendoff.fact.text)} words`);

console.log(problems.length ? problems.join('\n') : 'ns-text.js OK');
console.log('snap words:', Object.fromEntries(Object.entries(text.snaps).map(([k, c]) => [k, words(c.text)])));
process.exit(problems.length ? 1 : 0);
