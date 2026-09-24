// Persistent player settings + graphics tier presets.

const KEY = 'sparky.settings.v1';

export const TIERS = {
  low: { pixelRatio: 1.25, shadows: false, shadowSize: 0, post: false, bloom: false, particles: 0.45, assetVariant: 'mobile', maxLights: 2 },
  medium: { pixelRatio: 1.5, shadows: true, shadowSize: 1024, post: true, bloom: false, particles: 0.7, assetVariant: 'mobile', maxLights: 4 },
  high: { pixelRatio: 1.5, shadows: true, shadowSize: 2048, post: true, bloom: true, particles: 1, assetVariant: 'desktop', maxLights: 6 },
};

export const isTouch = (() => {
  try { return matchMedia('(pointer: coarse)').matches || 'ontouchstart' in window; } catch { return false; }
})();

function detectTier() {
  if (isTouch) {
    const big = Math.min(screen.width, screen.height) >= 700; // tablets
    return big ? 'medium' : 'low';
  }
  return 'high';
}

const defaults = () => ({
  quality: detectTier(),
  volume: 0.9,
  music: 0.6,
  subtitles: true,
  reduceMotion: false,
  invertY: false,
});

function load() {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return { ...defaults(), ...JSON.parse(raw) };
  } catch { /* storage unavailable */ }
  return defaults();
}

export const settings = load();
const listeners = new Set();

export function saveSettings(patch) {
  Object.assign(settings, patch);
  try { localStorage.setItem(KEY, JSON.stringify(settings)); } catch { /* ignore */ }
  listeners.forEach((fn) => fn(settings, patch));
}

export function onSettings(fn) { listeners.add(fn); return () => listeners.delete(fn); }

export const tier = () => TIERS[settings.quality] || TIERS.medium;
