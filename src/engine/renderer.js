import * as THREE from 'three';
import {
  EffectComposer, RenderPass, EffectPass, Effect, BloomEffect, ToneMappingEffect, ToneMappingMode, FXAAEffect,
} from 'postprocessing';
import { tier, settings, onSettings } from './settings.js';

// One merged colour-grade effect: saturation, sepia, contrast, tint, vignette, grain, white flash.
// On the low tier (no post-processing) the same values drive a CSS filter on the canvas instead.
class GradeEffect extends Effect {
  constructor() {
    super('GradeEffect', /* glsl */`
      uniform float saturation, sepia, contrast, vignette, grain, flash;
      uniform vec3 tint;
      float gHash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
      void mainImage(const in vec4 inputColor, const in vec2 uv, out vec4 outputColor) {
        vec3 col = inputColor.rgb;
        float l = dot(col, vec3(0.2126, 0.7152, 0.0722));
        col = mix(vec3(l), col, saturation);
        vec3 sep = vec3(dot(col, vec3(0.393, 0.769, 0.189)), dot(col, vec3(0.349, 0.686, 0.168)), dot(col, vec3(0.272, 0.534, 0.131)));
        col = mix(col, sep, sepia);
        col = max((col - 0.18) * contrast + 0.18, 0.0);
        col *= tint;
        vec2 d = uv - 0.5;
        col *= 1.0 - vignette * smoothstep(0.2, 0.9, dot(d, d) * 2.4);
        col += (gHash(uv * 997.0 + time) - 0.5) * grain * (0.3 + l);
        col = mix(col, vec3(1.0), flash);
        outputColor = vec4(col, inputColor.a);
      }`, {
      uniforms: new Map([
        ['saturation', new THREE.Uniform(1)], ['sepia', new THREE.Uniform(0)], ['contrast', new THREE.Uniform(1.04)],
        ['vignette', new THREE.Uniform(0.35)], ['grain', new THREE.Uniform(0.03)], ['flash', new THREE.Uniform(0)],
        ['tint', new THREE.Uniform(new THREE.Color(1, 1, 1))],
      ]),
    });
  }
}

export class Renderer {
  constructor(canvas) {
    this.canvas = canvas;
    // Live grade values — chapters tween these (e.g. sepia intro, desaturated occupation).
    this.grade = { saturation: 1, sepia: 0, contrast: 1.04, vignette: 0.35, grain: 0.03, flash: 0, tint: new THREE.Color(1, 1, 1) };
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: false, powerPreference: 'high-performance', stencil: false, depth: true });
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.shadowMap.type = THREE.PCFShadowMap;
    this.scene = null;
    this.camera = null;
    this.composer = null;
    this.applyTier();
    onSettings((s, patch) => { if ('quality' in patch) this.applyTier(); });
    addEventListener('resize', () => this.resize());
  }

  get info() { return this.renderer.info; }

  applyTier() {
    const t = tier();
    const shadowChanged = this.tier && this.tier.shadows !== t.shadows;
    this.tier = t;
    this.renderer.shadowMap.enabled = t.shadows;
    this.canvas.style.filter = '';
    this._lastFilter = '';
    this.buildComposer();
    this.resize();
    if (shadowChanged) this.scene?.traverse((o) => { if (o.material) [].concat(o.material).forEach((m) => { m.needsUpdate = true; }); });
    this.onTierChange?.(t);
  }

  setScene(scene, camera) {
    this.scene = scene;
    this.camera = camera;
    this.renderer.shadowMap.needsUpdate = true;
    this.buildComposer();
    this.resize();
  }

  buildComposer() {
    if (this.composer) { this.composer.dispose(); this.composer = null; }
    const t = this.tier;
    // Without post-processing, three's own tone mapping + MSAA-free canvas is cheapest.
    this.renderer.toneMapping = t.post ? THREE.NoToneMapping : THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.0;
    if (!t.post || !this.scene || !this.camera) return;
    const composer = new EffectComposer(this.renderer, { frameBufferType: THREE.HalfFloatType, multisampling: t.bloom ? 4 : 0 });
    composer.addPass(new RenderPass(this.scene, this.camera));
    const effects = [];
    if (t.bloom) effects.push(new BloomEffect({ intensity: 0.9, luminanceThreshold: 0.82, luminanceSmoothing: 0.25, mipmapBlur: true, radius: 0.6 }));
    effects.push(new ToneMappingEffect({ mode: ToneMappingMode.ACES_FILMIC }));
    this.gradeEffect = new GradeEffect();
    effects.push(this.gradeEffect);
    composer.addPass(new EffectPass(this.camera, ...effects));
    if (!t.bloom) composer.addPass(new EffectPass(this.camera, new FXAAEffect()));
    this.composer = composer;
  }

  /** Dynamic resolution: call once per frame with the real frame time (seconds). */
  adapt(frameDt) {
    const a = (this._adapt ||= { acc: 0, n: 0, scale: 1, cool: 0 });
    a.acc += frameDt; a.n++;
    a.cool -= frameDt;
    if (a.acc < 1.5) return;
    const avg = a.acc / a.n;
    a.acc = 0; a.n = 0;
    if (a.cool > 0) return;
    const maxPr = Math.min(devicePixelRatio || 1, this.tier.pixelRatio);
    let next = a.scale;
    if (avg > 1 / 45 && maxPr * a.scale > 0.75) next = Math.max(0.5, a.scale - 0.15);
    else if (avg < 1 / 58 && a.scale < 1) next = Math.min(1, a.scale + 0.1);
    if (next !== a.scale) { a.scale = next; a.cool = 3; this.resize(); }
  }

  resize() {
    const w = innerWidth, h = innerHeight;
    const pr = Math.max(0.5, Math.min(devicePixelRatio || 1, this.tier.pixelRatio) * (this._adapt?.scale ?? 1));
    this.renderer.setPixelRatio(pr);
    this.renderer.setSize(w, h, false);
    this.composer?.setSize(w, h, false);
    if (this.camera) { this.camera.aspect = w / h; this.camera.updateProjectionMatrix(); }
  }

  render(dt) {
    if (!this.scene || !this.camera) return;
    const g = this.grade;
    const flash = settings.reduceMotion ? g.flash * 0.25 : g.flash;
    if (this.composer) {
      const u = this.gradeEffect.uniforms;
      u.get('saturation').value = g.saturation; u.get('sepia').value = g.sepia; u.get('contrast').value = g.contrast;
      u.get('vignette').value = g.vignette; u.get('grain').value = g.grain; u.get('flash').value = flash;
      u.get('tint').value.copy(g.tint);
      this.composer.render(dt);
    } else {
      const plain = Math.abs(g.saturation - 1) < 0.01 && g.sepia < 0.01 && flash < 0.01;
      const f = plain ? '' : `saturate(${g.saturation.toFixed(2)}) sepia(${g.sepia.toFixed(2)}) brightness(${(1 + flash * 2).toFixed(2)})`;
      if (this._lastFilter !== f) { this.canvas.style.filter = f; this._lastFilter = f; }
      this.renderer.render(this.scene, this.camera);
    }
  }
}
