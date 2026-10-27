/**
 * AURA Orb: Living Liquid Plasma Consciousness & Audio-Reactive Voice Core
 * Parity 1:1 with Aura Assistance Android (AuraLivingOrb in AuraComponents.kt).
 * Zero Unicode dashes policy strictly enforced.
 */

(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define([], factory);
  } else if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    const mod = factory();
    root.AuraOrbEmotion = mod.AuraOrbEmotion;
    root.AuraOrb = mod.AuraOrb;
    root.AuraOrbManager = mod.AuraOrbManager;
    root.auraOrbManager = mod.manager;
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // Estados Emocionais da AURA
  const AuraOrbEmotion = Object.freeze({
    NEUTRAL: 'NEUTRAL',
    CALM: 'CALM',
    THINKING: 'THINKING',
    LISTENING: 'LISTENING',
    WORRIED: 'WORRIED',
    AGITATED: 'AGITATED',
    SUCCESS: 'SUCCESS'
  });

  // Paleta de Cores Oficial (Aura Assistance Android Theme.kt & Color.kt)
  const PALETTE = Object.freeze({
    auraCyan: '#22d3ee',         // Clarity Cyan
    auraEmerald: '#10b981',      // Emerald
    auraPurple: '#8b5cf6',       // Aura Purple
    auraBrandBlue: '#38bdf8',    // Azul celeste vibrante
    auraBrandPetroleum: '#0d9488', // Verde Petroleo
    auraBrandPurple: '#a855f7',  // Roxo elegante
    obsidianBase: '#07090e',     // Superficie AMOLED Obsidian
    obsidianDeep: '#030407',
    textPrimary: '#f1f5f9',
    textMuted: '#64748b',
    statusWarning: '#f59e0b',
    statusDanger: '#ef4444'
  });

  // Configuracoes Dinamicas por Emocao
  const EMOTION_CONFIG = Object.freeze({
    NEUTRAL: {
      colors: ['#22d3ee', '#64748b', '#0d9488', '#22d3ee'],
      halo: 'rgba(34, 211, 238, 0.30)',
      timeDuration: 4200,
      breathDuration: 2600,
      tooltip: 'AURA em repouso'
    },
    CALM: {
      colors: ['#22d3ee', '#10b981', '#8b5cf6', '#22d3ee'],
      halo: 'rgba(34, 211, 238, 0.40)',
      timeDuration: 3800,
      breathDuration: 2200,
      tooltip: 'AURA Pronta'
    },
    THINKING: {
      colors: ['#38bdf8', '#8b5cf6', '#a855f7', '#22d3ee'],
      halo: 'rgba(139, 92, 246, 0.60)',
      timeDuration: 1400,
      breathDuration: 1200,
      tooltip: 'Raciocinando...'
    },
    LISTENING: {
      colors: ['#67e8f9', '#22d3ee', '#10b981', '#67e8f9'],
      halo: 'rgba(34, 211, 238, 0.65)',
      timeDuration: 1800,
      breathDuration: 1000,
      tooltip: 'Ouvindo comando de pista...'
    },
    WORRIED: {
      colors: ['#f59e0b', '#8b5cf6', '#f59e0b', '#a855f7'],
      halo: 'rgba(245, 158, 11, 0.50)',
      timeDuration: 2600,
      breathDuration: 1800,
      tooltip: 'Atencao operacional'
    },
    AGITATED: {
      colors: ['#ef4444', '#f59e0b', '#ef4444', '#f59e0b'],
      halo: 'rgba(239, 68, 68, 0.65)',
      timeDuration: 1600,
      breathDuration: 1400,
      tooltip: 'Alerta critico SEFAZ'
    },
    SUCCESS: {
      colors: ['#10b981', '#38bdf8', '#d4af37', '#10b981'],
      halo: 'rgba(16, 185, 129, 0.55)',
      timeDuration: 2400,
      breathDuration: 1800,
      tooltip: 'Concluido com sucesso'
    }
  });

  // Modulo de Rastreamento de Audio em Tempo Real (AuraVoiceManager Parity)
  class AuraOrbAudioTracker {
    constructor() {
      this.audioCtx = null;
      this.analyser = null;
      this.mediaStreamSource = null;
      this.stream = null;
      this.dataArray = null;
      this.currentLevel = 0.05;
      this.targetLevel = 0.05;
      this.isTracking = false;
      this.syntheticTime = 0;
    }

    startTracking(stream) {
      try {
        if (!this.audioCtx) {
          const AudioContextClass = window.AudioContext || window.webkitAudioContext;
          if (AudioContextClass) {
            this.audioCtx = new AudioContextClass();
          }
        }
        if (this.audioCtx && this.audioCtx.state === 'suspended') {
          this.audioCtx.resume();
        }
        if (stream && this.audioCtx) {
          this.stream = stream;
          this.mediaStreamSource = this.audioCtx.createMediaStreamSource(stream);
          this.analyser = this.audioCtx.createAnalyser();
          this.analyser.fftSize = 256;
          this.analyser.smoothingTimeConstant = 0.6;
          this.mediaStreamSource.connect(this.analyser);
          this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
          this.isTracking = true;
        }
      } catch (err) {
        console.warn('[AuraOrbAudioTracker] Inicializacao de stream audio:', err);
      }
    }

    stopTracking() {
      this.isTracking = false;
      if (this.mediaStreamSource) {
        try {
          this.mediaStreamSource.disconnect();
        } catch (_) {}
        this.mediaStreamSource = null;
      }
      this.stream = null;
      this.analyser = null;
      this.targetLevel = 0.05;
      this.currentLevel = 0.05;
    }

    sampleVoiceRms(isListeningMode) {
      if (this.isTracking && this.analyser && this.dataArray) {
        try {
          this.analyser.getByteFrequencyData(this.dataArray);
          let sum = 0;
          const count = this.dataArray.length;
          for (let i = 0; i < count; i++) {
            sum += this.dataArray[i];
          }
          const rawAvg = count > 0 ? sum / count : 0;
          // Normalizacao identica ao onRmsChanged do AuraVoiceManager
          this.targetLevel = Math.max(0.05, Math.min(1.0, (rawAvg / 128.0) * 1.4));
        } catch (_) {
          this.targetLevel = 0.05;
        }
      } else if (isListeningMode) {
        // Sintese organica suave caso o stream bruto de microfone nao esteja conectado
        this.syntheticTime += 0.06;
        const base = Math.sin(this.syntheticTime * 2.4) * 0.32 + 0.42;
        const jitter = Math.sin(this.syntheticTime * 6.1) * 0.18;
        this.targetLevel = Math.max(0.05, Math.min(1.0, base + jitter));
      } else {
        this.targetLevel = 0.05;
      }

      // Amortecimento suave por mola (spring damping)
      const factor = this.targetLevel > this.currentLevel ? 0.35 : 0.14;
      this.currentLevel += (this.targetLevel - this.currentLevel) * factor;
      return this.currentLevel;
    }
  }

  const globalAudioTracker = new AuraOrbAudioTracker();

  // Componente AuraLivingOrb Puro (Compose Canvas 1:1)
  class AuraOrb {
    constructor(options = {}) {
      this.container = typeof options.container === 'string' ? document.querySelector(options.container) : options.container;
      this.size = Number(options.size) || 40; // Diametro nominal do orbe em px
      this.emotion = options.emotion && EMOTION_CONFIG[options.emotion] ? options.emotion : AuraOrbEmotion.CALM;
      this.onClick = typeof options.onClick === 'function' ? options.onClick : null;
      this.isInteractive = Boolean(options.isInteractive !== false);

      this.canvas = null;
      this.ctx = null;
      this.animationFrameId = null;
      this.startTime = performance.now();
      this.isPressed = false;
      this.pressScale = 1.0;
      this.isDestroyed = false;

      this.initDOM();
      this.startRenderLoop();
    }

    initDOM() {
      if (!this.container) return;

      this.container.classList.add('aura-orb-host');
      this.container.innerHTML = '';

      this.canvas = document.createElement('canvas');
      this.canvas.className = 'aura-orb-canvas';
      this.canvas.setAttribute('role', this.isInteractive ? 'button' : 'img');
      this.canvas.setAttribute('aria-label', 'AURA Consciencia Viva');
      if (this.isInteractive) {
        this.canvas.tabIndex = 0;
      }

      this.ctx = this.canvas.getContext('2d', { alpha: true });
      this.container.appendChild(this.canvas);

      this.updateDimensions();

      if (this.isInteractive) {
        this.bindInteractions();
      }
    }

    updateDimensions() {
      if (!this.canvas || !this.container) return;
      const dpr = window.devicePixelRatio || 1;
      // 2.2x para expansao fluida do halo atmosferico e ondas senoidais polares
      const canvasDim = Math.round(this.size * 2.2);

      this.canvas.width = Math.round(canvasDim * dpr);
      this.canvas.height = Math.round(canvasDim * dpr);
      this.canvas.style.width = `${canvasDim}px`;
      this.canvas.style.height = `${canvasDim}px`;
      this.canvasDim = canvasDim;
      this.dpr = dpr;
    }

    bindInteractions() {
      if (!this.canvas) return;

      const triggerPress = () => {
        this.isPressed = true;
      };

      const releasePress = () => {
        this.isPressed = false;
      };

      this.canvas.addEventListener('mousedown', triggerPress);
      window.addEventListener('mouseup', releasePress);

      this.canvas.addEventListener('touchstart', triggerPress, { passive: true });
      window.addEventListener('touchend', releasePress, { passive: true });
      window.addEventListener('touchcancel', releasePress, { passive: true });

      this.canvas.addEventListener('click', (e) => {
        if (window.auraAudio && typeof window.auraAudio.playChime === 'function') {
          window.auraAudio.playChime(720, 0.05);
        }
        if (this.onClick) {
          this.onClick(e);
        }
      });

      this.canvas.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          this.canvas.click();
        }
      });
    }

    setEmotion(nextEmotion) {
      if (EMOTION_CONFIG[nextEmotion] && this.emotion !== nextEmotion) {
        this.emotion = nextEmotion;
      }
    }

    startRenderLoop() {
      const render = (now) => {
        if (this.isDestroyed) return;
        this.draw(now);
        this.animationFrameId = requestAnimationFrame(render);
      };
      this.animationFrameId = requestAnimationFrame(render);
    }

    draw(now) {
      if (!this.ctx || !this.canvas) return;

      const ctx = this.ctx;
      const dpr = this.dpr || 1;
      const totalSize = this.canvasDim * dpr;
      const center = totalSize / 2;
      const cfg = EMOTION_CONFIG[this.emotion] || EMOTION_CONFIG.CALM;

      ctx.clearRect(0, 0, totalSize, totalSize);

      const elapsed = now - this.startTime;

      // 1. Amostragem do RMS de voz (AuraVoiceManager)
      const isListening = this.emotion === AuraOrbEmotion.LISTENING;
      const voiceRms = globalAudioTracker.sampleVoiceRms(isListening);

      // Micro-interacao elastica de clique
      const targetPressScale = this.isPressed ? 0.88 : 1.0;
      this.pressScale += (targetPressScale - this.pressScale) * 0.35;

      // 2. Tempo continuo para fluxo liquido das ondas (60fps)
      const timePhase = ((elapsed % cfg.timeDuration) / cfg.timeDuration) * (Math.PI * 2);

      // 3. Respiracao organica lenta (FastOutSlowInEasing)
      const breathProgress = (elapsed % cfg.breathDuration) / (cfg.breathDuration / 2);
      const breathCos = (1 - Math.cos(breathProgress * Math.PI)) / 2;
      const idleBreath = 0.92 + 0.16 * breathCos;

      // Raio base calibrado
      const baseRadius = ((this.size * dpr) / 2.6) * idleBreath * this.pressScale;

      // ----------------------------------------------------------------------
      // CAMADA A: Halo Difuso Atmosferico (AuraComponents.kt L1109-L1123)
      // ----------------------------------------------------------------------
      const haloRadius = baseRadius * (1.6 + (voiceRms * 0.70));
      const haloGradient = ctx.createRadialGradient(center, center, 0, center, center, haloRadius);
      const haloAlphaMult = 0.5 + voiceRms * 0.5;
      haloGradient.addColorStop(0, `rgba(34, 211, 238, ${(0.40 * haloAlphaMult).toFixed(3)})`);
      haloGradient.addColorStop(0.5, `rgba(139, 92, 246, ${(0.25 * haloAlphaMult).toFixed(3)})`);
      haloGradient.addColorStop(1, 'rgba(0, 0, 0, 0)');

      ctx.beginPath();
      ctx.arc(center, center, haloRadius, 0, Math.PI * 2);
      ctx.fillStyle = haloGradient;
      ctx.fill();

      // ----------------------------------------------------------------------
      // CAMADA B: Manto Liquido Externo (Polar Harmonic Liquid Waves L1164-L1190)
      // ----------------------------------------------------------------------
      const outerRMultiplier = 1.0 + (voiceRms * 0.25);
      this.buildLiquidPath(ctx, center, baseRadius, 0, outerRMultiplier, voiceRms, timePhase);

      // Preenchimento com Sweep / Conic Gradient
      if (typeof ctx.createConicGradient === 'function') {
        const conic = ctx.createConicGradient(timePhase * 0.5, center, center);
        conic.addColorStop(0, cfg.colors[0]);
        conic.addColorStop(0.33, cfg.colors[1]);
        conic.addColorStop(0.66, cfg.colors[2]);
        conic.addColorStop(1, cfg.colors[3]);
        ctx.fillStyle = conic;
      } else {
        const lin = ctx.createLinearGradient(center - baseRadius, center - baseRadius, center + baseRadius, center + baseRadius);
        lin.addColorStop(0, cfg.colors[0]);
        lin.addColorStop(0.5, cfg.colors[1]);
        lin.addColorStop(1, cfg.colors[2]);
        ctx.fillStyle = lin;
      }
      ctx.fill();

      // Borda iridescente fina de vidro liquido contornando a onda (L1179-L1190)
      const borderLin = ctx.createLinearGradient(center - baseRadius, center - baseRadius, center + baseRadius, center + baseRadius);
      borderLin.addColorStop(0, 'rgba(255, 255, 255, 0.85)');
      borderLin.addColorStop(0.5, 'rgba(34, 211, 238, 0.40)');
      borderLin.addColorStop(1, 'rgba(255, 255, 255, 0.75)');
      ctx.strokeStyle = borderLin;
      ctx.lineWidth = Math.max(1.0, 1.4 * dpr);
      ctx.stroke();

      // ----------------------------------------------------------------------
      // CAMADA C: Nucleo Secundario Contra-Rotativo (Efeito Moire Cosmico L1192-L1205)
      // ----------------------------------------------------------------------
      this.buildLiquidPath(ctx, center, baseRadius, 2.1, 0.78, voiceRms * 0.8, -timePhase * 1.2);
      const innerRadial = ctx.createRadialGradient(center, center, 0, center, center, baseRadius * 0.95);
      innerRadial.addColorStop(0, 'rgba(139, 92, 246, 0.70)');
      innerRadial.addColorStop(0.6, 'rgba(34, 211, 238, 0.85)');
      innerRadial.addColorStop(1, 'rgba(0, 0, 0, 0)');
      ctx.fillStyle = innerRadial;
      ctx.fill();

      // ----------------------------------------------------------------------
      // CAMADA D: Nucleo Incandescente de Plasma Branco/Ciano (L1207-L1222)
      // ----------------------------------------------------------------------
      const coreR = baseRadius * 0.38 * (1.0 + voiceRms * 0.30);
      const coreRadial = ctx.createRadialGradient(center, center, 0, center, center, coreR);
      coreRadial.addColorStop(0, '#ffffff');
      coreRadial.addColorStop(0.4, 'rgba(255, 255, 255, 0.92)');
      coreRadial.addColorStop(0.8, 'rgba(34, 211, 238, 0.85)');
      coreRadial.addColorStop(1, 'rgba(0, 0, 0, 0)');

      ctx.beginPath();
      ctx.arc(center, center, coreR, 0, Math.PI * 2);
      ctx.fillStyle = coreRadial;
      ctx.fill();

      // ----------------------------------------------------------------------
      // CAMADA E: Centelha Diamante no Centro da Consciencia (L1224-L1229)
      // ----------------------------------------------------------------------
      ctx.beginPath();
      ctx.arc(center, center, baseRadius * 0.12, 0, Math.PI * 2);
      ctx.fillStyle = '#ffffff';
      ctx.fill();
    }

    /**
     * Gerador de Contorno Organico Liquido (Polar Harmonic Spline)
     * Paridade exata com buildLiquidPath de AuraComponents.kt L1130-L1162
     */
    buildLiquidPath(ctx, center, baseRadius, phaseOffset, rMultiplier, waveAmp, timePhase) {
      const steps = 36;
      const stepAngle = (2 * Math.PI) / steps;
      const points = [];

      for (let i = 0; i < steps; i++) {
        const angle = i * stepAngle;
        // Modulacao harmonica com 3 frequencias (octaves) senoidais
        const harm1 = Math.sin(3 * angle + timePhase + phaseOffset) * (0.09 + waveAmp * 0.22);
        const harm2 = Math.cos(2 * angle - (timePhase * 1.3) + phaseOffset) * (0.07 + waveAmp * 0.18);
        const harm3 = Math.sin(4 * angle + (timePhase * 0.8)) * (0.05 + waveAmp * 0.12);

        const r = baseRadius * rMultiplier * (1.0 + harm1 + harm2 + harm3);
        const x = center + r * Math.cos(angle);
        const y = center + r * Math.sin(angle);
        points.push({ x, y });
      }

      ctx.beginPath();
      // Interpolacao Bezier quadratica suave entre os pontos medios
      const firstMid = {
        x: (points[0].x + points[steps - 1].x) / 2,
        y: (points[0].y + points[steps - 1].y) / 2
      };
      ctx.moveTo(firstMid.x, firstMid.y);

      for (let i = 0; i < steps; i++) {
        const current = points[i];
        const next = points[(i + 1) % steps];
        const mid = {
          x: (current.x + next.x) / 2,
          y: (current.y + next.y) / 2
        };
        ctx.quadraticCurveTo(current.x, current.y, mid.x, mid.y);
      }
      ctx.closePath();
    }

    destroy() {
      this.isDestroyed = true;
      if (this.animationFrameId) {
        cancelAnimationFrame(this.animationFrameId);
        this.animationFrameId = null;
      }
      if (this.canvas && this.canvas.parentNode) {
        this.canvas.parentNode.removeChild(this.canvas);
      }
      this.canvas = null;
      this.ctx = null;
    }
  }

  // Gerenciador Central de Orbes AURA
  class AuraOrbManager {
    constructor() {
      this.instances = new Map();
      this.currentEmotion = AuraOrbEmotion.CALM;
      this.isInitialized = false;
    }

    init() {
      if (this.isInitialized || typeof document === 'undefined') return;

      // 1. Instanciar Header Orb
      const headerEl = document.getElementById('header-neural-core-orb');
      if (headerEl) {
        const orb = new AuraOrb({
          container: headerEl,
          size: 34,
          emotion: AuraOrbEmotion.CALM,
          isInteractive: true,
          onClick: () => {
            if (window.auraVoice && typeof window.auraVoice.toggleVoice === 'function') {
              window.auraVoice.toggleVoice();
            }
          }
        });
        this.instances.set('header', orb);
      }

      // 2. Instanciar Drawer Orb se presente
      const drawerOrbEl = document.getElementById('drawer-neural-core-orb');
      if (drawerOrbEl) {
        const orb = new AuraOrb({
          container: drawerOrbEl,
          size: 30,
          emotion: AuraOrbEmotion.CALM,
          isInteractive: false
        });
        this.instances.set('drawer', orb);
      }

      // 3. Observar classes legadas (retrocompatibilidade com .reasoning-active)
      this.setupLegacyObserver();

      this.isInitialized = true;
    }

    setupLegacyObserver() {
      const headerEl = document.getElementById('header-neural-core-orb');
      if (!headerEl || typeof MutationObserver === 'undefined') return;

      const observer = new MutationObserver((mutations) => {
        for (const m of mutations) {
          if (m.attributeName === 'class') {
            const hasReasoning = headerEl.classList.contains('reasoning-active');
            if (hasReasoning) {
              this.setEmotion(AuraOrbEmotion.THINKING);
            } else if (this.currentEmotion === AuraOrbEmotion.THINKING) {
              this.setEmotion(AuraOrbEmotion.SUCCESS);
              setTimeout(() => {
                if (this.currentEmotion === AuraOrbEmotion.SUCCESS) {
                  this.setEmotion(AuraOrbEmotion.CALM);
                }
              }, 1800);
            }
          }
        }
      });

      observer.observe(headerEl, { attributes: true });
    }

    registerOrb(key, orbInstance) {
      this.instances.set(key, orbInstance);
    }

    unregisterOrb(key) {
      const orb = this.instances.get(key);
      if (orb) {
        orb.destroy();
        this.instances.delete(key);
      }
    }

    setEmotion(emotion) {
      if (!EMOTION_CONFIG[emotion]) return;
      this.currentEmotion = emotion;

      for (const orb of this.instances.values()) {
        orb.setEmotion(emotion);
      }
    }

    getEmotion() {
      return this.currentEmotion;
    }

    attachAudioStream(stream) {
      globalAudioTracker.startTracking(stream);
      this.setEmotion(AuraOrbEmotion.LISTENING);
    }

    detachAudioStream() {
      globalAudioTracker.stopTracking();
      if (this.currentEmotion === AuraOrbEmotion.LISTENING) {
        this.setEmotion(AuraOrbEmotion.CALM);
      }
    }
  }

  const manager = new AuraOrbManager();

  if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => manager.init());
    } else {
      manager.init();
    }
  }

  return {
    AuraOrbEmotion,
    AuraOrb,
    AuraOrbManager,
    manager,
    audioTracker: globalAudioTracker
  };
});
