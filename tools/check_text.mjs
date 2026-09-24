// Checks src/chapters/ww2-text.js against the phone-bubble and card limits in docs/design.md.
// Run: node tools/check_text.mjs
import text from '../src/chapters/ww2-text.js';

const problems = [];
const plain = (s) => s.replace(/\{([^|}]+)\|[^}]*\}/g, '$1');
const words = (s) => plain(s).trim().split(/\s+/).length;
const sentences = (s) => (s.match(/[.!?](\s|$)/g) || []).length;

(function walk(node, path) {
  if (Array.isArray(node)) return node.forEach((n, i) => walk(n, `${path}[${i}]`));
  if (node && typeof node === 'object') {
    if (typeof node.who === 'string' && typeof node.text === 'string' && plain(node.text).length > 120)
      problems.push(`${path}: ${plain(node.text).length} chars`);
    for (const [k, v] of Object.entries(node)) walk(v, `${path}.${k}`);
  }
})(text, 'text');

text.drops.forEach((d, i) => sentences(d.fact) > 2 && problems.push(`drops[${i}].fact: ${sentences(d.fact)} sentences`));
for (const [k, c] of Object.entries(text.snaps)) words(c.text) > 40 && problems.push(`snaps.${k}: ${words(c.text)} words`);
words(text.epilogue.narration) > 70 && problems.push(`epilogue.narration: ${words(text.epilogue.narration)} words`);

console.log(problems.length ? problems.join('\n') : 'ww2-text.js OK');
console.log('snap words:', Object.fromEntries(Object.entries(text.snaps).map(([k, c]) => [k, words(c.text)])),
  'narration words:', words(text.epilogue.narration));
process.exit(problems.length ? 1 : 0);
