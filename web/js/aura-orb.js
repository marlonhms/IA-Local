/**
 * AURA Orb: Living Cosmic Presence & Audio-Reactive Neural Core
 * Parity 1:1 with mobile AuraOrb.kt (Compose Canvas Engine).
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
    root.AuraFloatingOrb = mod.AuraFloatingOrb;
    root.AuraOrbManager = mod.AuraOrbManager;
    root.auraOrbManager = mod.manager;
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // Estados Emocionais da AURA (1:1 com AuraOrbEmotion do Kotlin)
  const AuraOrbEmotion = Object.freeze({
    NEUTRAL: 'NEUTRAL',
    CALM: 'CALM',
    THINKING: 'THINKING',
    LISTENING: 'LISTENING',
    WORRIED: 'WORRIED',
    AGITATED: 'AGITATED',
    SUCCESS: 'SUCCESS'
  });

  // Paleta de Cores Cosmica AURA (Slate-950 Alinhada)
  const PALETTE = Object.freeze({
    cyan: '#22d3ee',
    cyanLight: '#67e8f9',
    violet: '#7c3aed',
    violetLight: '#a78bfa',
    emerald: '#10b981',
    emeraldLight: '#34d399',
    amber: '#f59e0b',
    red: '#ef4444',
    gold: '#d4af37',
    slateMuted: '#64748b'
  });

  // Configuracoes Dinamicas por Emocao
  const EMOTION_CONFIG = Object.freeze({
    NEUTRAL: {
      primary: 'rgba(34, 211, 238, 0.8)',
      secondary: 'rgba(100, 116, 139, 0.9)',
      halo: 'rgba(34, 211, 238, 0.35)',
      breathingDuration: 2800,
      glowDuration: 2200,
      rotationDuration: 12000,
      scaleMin: 0.93,
      scaleMax: 1.07,
      glowMin: 0.35,
      glowMax: 0.75,
      hasCounterRing: false,
      tooltip: 'AURA em repouso'
    },
    CALM: {
      primary: 'rgba(34, 211, 238, 1.0)',
      secondary: 'rgba(16, 185, 129, 1.0)',
      halo: 'rgba(34, 211, 238, 0.50)',
      breathingDuration: 2800,
      glowDuration: 2200,
      rotationDuration: 12000,
      scaleMin: 0.93,
      scaleMax: 1.07,
      glowMin: 0.35,
      glowMax: 0.75,
      hasCounterRing: false,
      tooltip: 'AURA Pronta'
    },
    THINKING: {
      primary: 'rgba(34, 211, 238, 1.0)',
      secondary: 'rgba(124, 58, 237, 1.0)',
      halo: 'rgba(124, 58, 237, 0.65)',
      breathingDuration: 1200,
      glowDuration: 1000,
      rotationDuration: 2400,
      scaleMin: 0.90,
      scaleMax: 1.10,
      glowMin: 0.50,
      glowMax: 0.95,
      hasCounterRing: true,
      tooltip: 'Raciocinando...'
    },
    LISTENING: {
      primary: 'rgba(103, 232, 249, 1.0)',
      secondary: 'rgba(34, 211, 238, 1.0)',
      halo: 'rgba(34, 211, 238, 0.60)',
      breathingDuration: 900,
      glowDuration: 800,
      rotationDuration: 3000,
      scaleMin: 0.93,
      scaleMax: 1.08,
      glowMin: 0.40,
      glowMax: 0.85,
      hasCounterRing: true,
      tooltip: 'Ouvindo comando de pista...'
    },
    WORRIED: {
      primary: 'rgba(245, 158, 11, 1.0)',
      secondary: 'rgba(124, 58, 237, 1.0)',
      halo: 'rgba(245, 158, 11, 0.50)',
      breathingDuration: 2200,
      glowDuration: 1800,
      rotationDuration: 8000,
      scaleMin: 0.92,
      scaleMax: 1.08,
      glowMin: 0.40,
      glowMax: 0.80,
      hasCounterRing: false,
      tooltip: 'Atencao operacional'
    },
    AGITATED: {
      primary: 'rgba(239, 68, 68, 1.0)',
      secondary: 'rgba(245, 158, 11, 1.0)',
      halo: 'rgba(239, 68, 68, 0.65)',
      breathingDuration: 1500,
      glowDuration: 1400,
      rotationDuration: 5000,
      scaleMin: 0.90,
      scaleMax: 1.12,
      glowMin: 0.50,
      glowMax: 0.90,
      hasCounterRing: true,
      tooltip: 'Alerta critico SEFAZ'
    },
    SUCCESS: {
      primary: 'rgba(16, 185, 129, 1.0)',
      secondary: 'rgba(212, 175, 55, 1.0)',
      halo: 'rgba(212, 175, 55, 0.60)',
      breathingDuration: 2000,
      glowDuration: 1600,
      rotationDuration: 6000,
      scaleMin: 0.94,
      scaleMax: 1.08,
      glowMin: 0.45,
      glowMax: 0.85,
      hasCounterRing: false,
      tooltip: 'Concluido com sucesso'
    }
  });

  // Modulo de Rastreamento de Audio em Tempo Real (Web Audio API)
  class AuraOrbAudioTracker {
    constructor() {
      this.audioCtx = null;
      this.analyser = null;
      this.mediaStreamSource = null;
      this.stream = null;
      this.dataArray = null;
      this.currentLevel = 0.0;
      this.targetLevel = 0.0;
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
          this.analyser.smoothingTimeConstant = 0.5;
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
      this.targetLevel = 0.0;
      this.currentLevel = 0.0;
    }

    sampleAudioLevel(isListeningMode) {
      if (this.isTracking && this.analyser && this.dataArray) {
        try {
          this.analyser.getByteFrequencyData(this.dataArray);
          let sum = 0;
          const count = this.dataArray.length;
          for (let i = 0; i < count; i++) {
            sum += this.dataArray[i];
          }
          const rawAvg = count > 0 ? sum / count : 0;
          this.targetLevel = Math.min(1.0, (rawAvg / 128.0) * 1.5);
        } catch (_) {
          this.targetLevel = 0.0;
        }
      } else if (isListeningMode) {
        // Sintese organica de cadencia vocal caso stream bruto nao esteja linkado
        this.syntheticTime += 0.08;
        const base = Math.sin(this.syntheticTime * 2.2) * 0.35 + 0.45;
        const jitter = Math.sin(this.syntheticTime * 5.7) * 0.2;
        this.targetLevel = Math.max(0.0, Math.min(1.0, base + jitter));
      } else {
        this.targetLevel = 0.0;
      }

      // Suavizacao ataque e decaimento (Attack / Decay Envelope)
      const factor = this.targetLevel > this.currentLevel ? 0.35 : 0.12;
      this.currentLevel += (this.targetLevel - this.currentLevel) * factor;
      return this.currentLevel;
    }
  }

  const globalAudioTracker = new AuraOrbAudioTracker();

  // Singleton de pre-carregamento do logo oficial
  let sharedLogoImage = null;
  let isLogoLoaded = false;
  function getSharedLogoImage() {
    if (!sharedLogoImage && typeof Image !== 'undefined') {
      sharedLogoImage = new Image();
      sharedLogoImage.crossOrigin = 'anonymous';
      sharedLogoImage.onload = () => { isLogoLoaded = true; };
      sharedLogoImage.src = '/static/img/ic_aura_logo.png';
    }
    return sharedLogoImage;
  }

  // Componente AuraOrb Canvas de Alta Fidelidade
  class AuraOrb {
    constructor(options = {}) {
      this.container = typeof options.container === 'string' ? document.querySelector(options.container) : options.container;
      this.size = Number(options.size) || 48; // Diametro nominal do logo central em px
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
      this.canvas.setAttribute('aria-label', 'AURA Orb');
      if (this.isInteractive) {
        this.canvas.tabIndex = 0;
      }

      this.ctx = this.canvas.getContext('2d', { alpha: true });
      this.container.appendChild(this.canvas);

      this.updateDimensions();

      if (this.isInteractive) {
        this.bindInteractions();
      }

      getSharedLogoImage();
    }

    updateDimensions() {
      if (!this.canvas || !this.container) return;
      const dpr = window.devicePixelRatio || 1;
      // O canvas se expande em 2.2x para acomodar o backglow amplo e ondas cosmicas
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

      // Audio responsiveness sampling
      const isListening = this.emotion === AuraOrbEmotion.LISTENING;
      const audioLevel = globalAudioTracker.sampleAudioLevel(isListening);

      // Micro-interacao elastica de clique
      const targetPressScale = this.isPressed ? 0.88 : 1.0;
      this.pressScale += (targetPressScale - this.pressScale) * 0.35;

      const elapsed = now - this.startTime;

      // 1. Pulso de Escala (Breathing)
      const breathingHalf = cfg.breathingDuration / 2;
      const breathProgress = (elapsed % cfg.breathingDuration) / breathingHalf;
      // Interpolacao cossenoidal suave (FastOutSlowIn approximation)
      const breathCos = (1 - Math.cos(breathProgress * Math.PI)) / 2;
      const baseScale = cfg.scaleMin + (cfg.scaleMax - cfg.scaleMin) * breathCos;
      // Amplificacao dinamica com audio de voz
      const audioScaleBoost = isListening ? audioLevel * 0.12 : 0;
      const currentScale = (baseScale + audioScaleBoost) * this.pressScale;

      const logoRadius = (this.size * dpr / 2) * currentScale;

      // 2. Pulso de Brilho (Glow Pulse)
      const glowHalf = cfg.glowDuration / 2;
      const glowProgress = (elapsed % cfg.glowDuration) / glowHalf;
      const glowCos = (1 - Math.cos(glowProgress * Math.PI)) / 2;
      const baseGlow = cfg.glowMin + (cfg.glowMax - cfg.glowMin) * glowCos;
      const audioGlowBoost = isListening ? audioLevel * 0.30 : 0;
      const glowPulse = Math.min(1.0, baseGlow + audioGlowBoost);

      // 3. Fases das Ondas Concentricas de Aura (Ripples)
      const waveDuration = cfg.breathingDuration * 1.3;
      const wavePhase1 = (elapsed % waveDuration) / waveDuration;
      const wavePhase2 = (wavePhase1 + 0.5) % 1.0;

      // 4. Angulos Orbitais
      // O audio acelera a rotacao orbital suavemente na fala
      const rotDuration = isListening ? Math.max(1200, cfg.rotationDuration - audioLevel * 1400) : cfg.rotationDuration;
      const rotAngle = ((elapsed % rotDuration) / rotDuration) * (Math.PI * 2);
      const counterRotDuration = rotDuration * 1.5;
      const counterRotAngle = -(((elapsed % counterRotDuration) / counterRotDuration) * (Math.PI * 2));

      // ----------------------------------------------------------------------
      // CAMADA A: Nebulosa Atmosferica Ampla de Fundo (Backglow)
      // ----------------------------------------------------------------------
      const nebulaRadius = logoRadius * (1.85 + audioLevel * 0.25);
      const backglow = ctx.createRadialGradient(center, center, 0, center, center, nebulaRadius);
      const haloAlpha = glowPulse * (this.isPressed ? 0.85 : 0.55);
      backglow.addColorStop(0, this.applyAlpha(cfg.halo, haloAlpha));
      backglow.addColorStop(0.5, this.applyAlpha(cfg.secondary, glowPulse * 0.22));
      backglow.addColorStop(1, 'rgba(0, 0, 0, 0)');

      ctx.beginPath();
      ctx.arc(center, center, nebulaRadius, 0, Math.PI * 2);
      ctx.fillStyle = backglow;
      ctx.fill();

      // ----------------------------------------------------------------------
      // CAMADA B: Ondas Continuas de Energia (Dual Concentric Ripples)
      // ----------------------------------------------------------------------
      this.drawRipple(ctx, center, logoRadius, wavePhase1, glowPulse, cfg.primary, cfg.secondary, audioLevel);
      this.drawRipple(ctx, center, logoRadius, wavePhase2, glowPulse, cfg.secondary, cfg.halo, audioLevel);

      // ----------------------------------------------------------------------
      // CAMADA C: Anel Orbital Primario Rotativo (Sweep Conic Ring)
      // ----------------------------------------------------------------------
      this.drawOrbitalRing(ctx, center, logoRadius * 1.10, rotAngle, cfg.primary, cfg.secondary, PALETTE.cyanLight, cfg.hasCounterRing ? 2.4 : 1.8);

      // ----------------------------------------------------------------------
      // CAMADA D: Anel Secundario em Contra-rotacao (Ativo em THINKING, LISTENING, AGITATED)
      // ----------------------------------------------------------------------
      if (cfg.hasCounterRing) {
        this.drawOrbitalRing(ctx, center, logoRadius * 1.25, counterRotAngle, PALETTE.violet, 'rgba(0,0,0,0)', PALETTE.cyanLight, 1.4);
      }

      // ----------------------------------------------------------------------
      // CAMADA E: Brilho Emocional Sutil no Centro da Aura
      // ----------------------------------------------------------------------
      if (this.emotion !== AuraOrbEmotion.CALM && this.emotion !== AuraOrbEmotion.NEUTRAL) {
        const coreGlowRadius = logoRadius * 0.85;
        const coreGlow = ctx.createRadialGradient(center, center, 0, center, center, coreGlowRadius);
        const centerAlpha = this.emotion === AuraOrbEmotion.THINKING ? 0.45 : (0.28 + audioLevel * 0.25);
        coreGlow.addColorStop(0, this.applyAlpha(cfg.primary, centerAlpha));
        coreGlow.addColorStop(0.6, this.applyAlpha(cfg.secondary, 0.15));
        coreGlow.addColorStop(1, 'rgba(0, 0, 0, 0)');

        ctx.beginPath();
        ctx.arc(center, center, coreGlowRadius, 0, Math.PI * 2);
        ctx.fillStyle = coreGlow;
        ctx.fill();
      }

      // ----------------------------------------------------------------------
      // CAMADA F: Logo Oficial da AURA (ic_aura_logo.png ou Fallback Vetorial)
      // ----------------------------------------------------------------------
      this.drawOfficialLogo(ctx, center, logoRadius);
    }

    drawRipple(ctx, center, logoRadius, wavePhase, glowPulse, colPrimary, colSecondary, audioLevel) {
      const audioExpansion = audioLevel * 0.35;
      const r = logoRadius * (0.95 + wavePhase * 0.70 + audioExpansion);
      const a = Math.max(0, Math.min(1.0, (1.0 - wavePhase) * 0.60 * glowPulse));
      if (a <= 0.01) return;

      const ripGrad = ctx.createRadialGradient(center, center, 0, center, center, r);
      ripGrad.addColorStop(0, this.applyAlpha(colPrimary, a * 0.45));
      ripGrad.addColorStop(0.7, this.applyAlpha(colSecondary, a * 0.20));
      ripGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');

      ctx.beginPath();
      ctx.arc(center, center, r, 0, Math.PI * 2);
      ctx.fillStyle = ripGrad;
      ctx.fill();

      // Contorno suave da onda
      ctx.beginPath();
      ctx.arc(center, center, r, 0, Math.PI * 2);
      ctx.strokeStyle = this.applyAlpha(colPrimary, a * 0.85);
      ctx.lineWidth = Math.max(0.7, (2.2 * (1.0 - wavePhase)));
      ctx.stroke();
    }

    drawOrbitalRing(ctx, center, radius, angle, col1, col2, col3, lineWidth) {
      ctx.save();
      ctx.translate(center, center);
      ctx.rotate(angle);

      // Usar conicGradient nativo se disponivel no browser moderno
      if (typeof ctx.createConicGradient === 'function') {
        const conic = ctx.createConicGradient(0, 0, 0);
        conic.addColorStop(0, this.applyAlpha(col1, 0.95));
        conic.addColorStop(0.33, this.applyAlpha(col2, 0.40));
        conic.addColorStop(0.66, this.applyAlpha(col3, 0.95));
        conic.addColorStop(1, this.applyAlpha(col1, 0.95));
        ctx.strokeStyle = conic;
      } else {
        ctx.strokeStyle = this.applyAlpha(col1, 0.85);
      }

      ctx.lineWidth = lineWidth;
      ctx.beginPath();
      ctx.arc(0, 0, radius, 0, Math.PI * 2);
      ctx.stroke();

      ctx.restore();
    }

    drawOfficialLogo(ctx, center, logoRadius) {
      const logoImg = getSharedLogoImage();
      const drawSize = logoRadius * 2;

      if (isLogoLoaded && logoImg && logoImg.naturalWidth > 0) {
        ctx.drawImage(logoImg, center - drawSize / 2, center - drawSize / 2, drawSize, drawSize);
      } else {
        // Fallback vetorial imediato do nucleo de diamante AURA (enquanto imagem carrega)
        ctx.save();
        ctx.translate(center, center);

        ctx.beginPath();
        ctx.moveTo(0, -logoRadius * 0.7);
        ctx.lineTo(logoRadius * 0.7, 0);
        ctx.lineTo(0, logoRadius * 0.7);
        ctx.lineTo(-logoRadius * 0.7, 0);
        ctx.closePath();

        const grad = ctx.createLinearGradient(-logoRadius, -logoRadius, logoRadius, logoRadius);
        grad.addColorStop(0, PALETTE.cyan);
        grad.addColorStop(0.5, PALETTE.emerald);
        grad.addColorStop(1, PALETTE.violet);

        ctx.fillStyle = grad;
        ctx.fill();

        ctx.strokeStyle = 'rgba(255, 255, 255, 0.85)';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        ctx.restore();
      }
    }

    applyAlpha(colorStr, alpha) {
      if (!colorStr) return `rgba(34, 211, 238, ${alpha})`;
      if (colorStr.startsWith('#')) {
        let hex = colorStr.slice(1);
        if (hex.length === 3) hex = hex.split('').map(c => c + c).join('');
        const num = parseInt(hex, 16);
        const r = (num >> 16) & 255;
        const g = (num >> 8) & 255;
        const b = num & 255;
        return `rgba(${r}, ${g}, ${b}, ${alpha.toFixed(3)})`;
      }
      if (colorStr.startsWith('rgba')) {
        return colorStr.replace(/rgba?\(([^)]+)\)/, (match, vals) => {
          const parts = vals.split(',').map(s => s.trim());
          return `rgba(${parts[0]}, ${parts[1]}, ${parts[2]}, ${alpha.toFixed(3)})`;
        });
      }
      return colorStr;
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

  // Componente de Orb Flutuante HUD (Floating Interactive Aura Orb)
  class AuraFloatingOrb {
    constructor() {
      this.container = null;
      this.orb = null;
      this.badge = null;
      this.badgeText = null;
      this.init();
    }

    init() {
      if (typeof document === 'undefined') return;

      // Criar container flutuante se ainda nao existir
      let host = document.getElementById('aura-floating-orb-container');
      if (!host) {
        host = document.createElement('div');
        host.id = 'aura-floating-orb-container';
        host.className = 'aura-floating-orb-container';
        document.body.appendChild(host);
      }

      host.innerHTML = `
        <div id="aura-floating-orb-badge" class="aura-floating-orb-badge" aria-live="polite">
          <span class="aura-badge-dot"></span>
          <span id="aura-floating-orb-text" class="aura-badge-text">AURA</span>
        </div>
        <div id="aura-floating-orb-canvas-wrapper" class="aura-floating-orb-canvas-wrapper"></div>
      `;

      this.container = host;
      this.badge = document.getElementById('aura-floating-orb-badge');
      this.badgeText = document.getElementById('aura-floating-orb-text');

      const wrapper = document.getElementById('aura-floating-orb-canvas-wrapper');

      this.orb = new AuraOrb({
        container: wrapper,
        size: 52, // Diametro confortavel para toque e clique flutuante
        emotion: AuraOrbEmotion.CALM,
        isInteractive: true,
        onClick: () => {
          this.handleClick();
        }
      });

      this.bindStateEvents();
    }

    handleClick() {
      // Dispara o controlador de voz se disponivel, ou foca o input de chat
      if (window.auraVoice && typeof window.auraVoice.toggleVoice === 'function') {
        window.auraVoice.toggleVoice();
      } else {
        const chatInput = document.getElementById('chat-input-text');
        if (chatInput) {
          chatInput.focus();
        }
      }
    }

    setEmotion(emotion) {
      if (!this.orb) return;
      this.orb.setEmotion(emotion);

      const cfg = EMOTION_CONFIG[emotion];
      if (this.badgeText && cfg) {
        this.badgeText.textContent = cfg.tooltip;
      }
      if (this.container) {
        this.container.setAttribute('data-emotion', emotion);
      }
      if (this.badge) {
        if (emotion !== AuraOrbEmotion.CALM && emotion !== AuraOrbEmotion.NEUTRAL) {
          this.badge.classList.add('badge-visible');
        } else {
          this.badge.classList.remove('badge-visible');
        }
      }
    }

    bindStateEvents() {
      // Sincroniza com mudancas de estado no app
      if (this.container) {
        this.container.addEventListener('mouseenter', () => {
          if (this.badge) this.badge.classList.add('badge-visible');
        });
        this.container.addEventListener('mouseleave', () => {
          if (this.orb && (this.orb.emotion === AuraOrbEmotion.CALM || this.orb.emotion === AuraOrbEmotion.NEUTRAL)) {
            if (this.badge) this.badge.classList.remove('badge-visible');
          }
        });
      }
    }
  }

  // Gerenciador Central de Orbes AURA
  class AuraOrbManager {
    constructor() {
      this.instances = new Map();
      this.floatingOrb = null;
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
          size: 32,
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
          size: 28,
          emotion: AuraOrbEmotion.CALM,
          isInteractive: false
        });
        this.instances.set('drawer', orb);
      }

      // 3. Instanciar Floating Action Orb
      this.floatingOrb = new AuraFloatingOrb();

      // 4. Observar classes legadas (retrocompatibilidade perfeita com .reasoning-active)
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

    setEmotion(emotion) {
      if (!EMOTION_CONFIG[emotion]) return;
      this.currentEmotion = emotion;

      for (const orb of this.instances.values()) {
        orb.setEmotion(emotion);
      }

      if (this.floatingOrb) {
        this.floatingOrb.setEmotion(emotion);
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
    AuraFloatingOrb,
    AuraOrbManager,
    manager,
    audioTracker: globalAudioTracker
  };
});
