// Checks src/chapters/ind-text.js (Chapter 2) against the phone-bubble and card limits in docs/design.md:
// spoken lines ≤ 120 characters (glosses not counted), album cards ≤ 40 words, fact toasts ≤ 45 words.
// Run: node tools/check_text_ind.mjs
import text from '../src/chapters/ind-text.js';

const problems = [];
const plain = (s) => s.replace(/\{([^|}]+)\|[^}]*\}/g, '$1');
const words = (s) => plain(s).trim().split(/\s+/).length;

(function walk(node, path) {
  if (Array.isArray(node)) return node.forEach((n, i) => walk(n, `${path}[${i}]`));
  if (node && typeof node === 'object') {
    if (typeof node.who === 'string' && typeof node.text === 'string' && plain(node.text).length > 120)
      problems.push(`${path}: ${plain(node.text).length} chars`);
    for (const [k, v] of Object.entries(node)) walk(v, `${path}.${k}`);
  }
})(text, 'text');

for (const [k, c] of Object.entries(text.snaps)) words(c.text) > 40 && problems.push(`snaps.${k}: ${words(c.text)} words`);
text.worries.list.forEach((w) => words(w.fact.text) > 45 && problems.push(`worries.${w.id}.fact: ${words(w.fact.text)} words`));

console.log(problems.length ? problems.join('\n') : 'ind-text.js OK');
console.log('snap words:', Object.fromEntries(Object.entries(text.snaps).map(([k, c]) => [k, words(c.text)])));
process.exit(problems.length ? 1 : 0);
