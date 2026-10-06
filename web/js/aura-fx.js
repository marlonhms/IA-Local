/**
 * AURA FX & DESKTOP COGNITIVE ENGINE
 * ============================================================================
 * 1. Detecção e Adaptação Inteligente de Dispositivo (Desktop vs Mobile)
 * 2. Monitoramento de Taxa de Atualização do Monitor (60Hz, 120Hz, 144Hz, 240Hz)
 * 3. Simulação Fluida de Aurora Boreal (Cores AURA: Esmeralda, Ciano e Roxo Gameplay)
 * 4. Efeitos Glance (Specular Mouse Lighting, Glance Bar e Quick Peek)
 * 5. Command Palette Executiva para Desktop (Ctrl+K / Cmd+K)
 * ============================================================================
 */

(function () {
  'use strict';

  // ==========================================================================
  // 1. GERENCIADOR DE DISPOSITIVOS (DESKTOP VS MOBILE AUTO-DETECTION)
  // ==========================================================================
  class AuraDeviceManager {
    constructor() {
      this.mode = 'desktop'; // 'desktop' | 'mobile'
      this.override = null;  // permite teste manual
      this.listeners = [];
    }

    init() {
      this.detect();
      window.addEventListener('resize', () => this.detect(), { passive: true });
      if (window.matchMedia) {
        window.matchMedia('(pointer: coarse)').addEventListener('change', () => this.detect());
        window.matchMedia('(max-width: 1024px)').addEventListener('change', () => this.detect());
      }
      this.bindHudControls();
    }

    detect() {
      if (this.override) {
        this.applyMode(this.override);
        return;
      }

      const hasCoarsePointer = window.matchMedia && window.matchMedia('(pointer: coarse)').matches;
      const isNarrow = window.innerWidth < 1024;
      const isMobileUA = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);

      const detected = (hasCoarsePointer || isNarrow || isMobileUA) ? 'mobile' : 'desktop';
      this.applyMode(detected);
    }

    applyMode(mode) {
      if (this.mode !== mode) {
        this.mode = mode;
        this.notifyListeners();
      }

      const root = document.documentElement;
      root.setAttribute('data-device', mode);
      root.setAttribute('data-pointer', mode === 'desktop' ? 'fine' : 'coarse');

      // Atualiza badge no HUD
      const badge = document.getElementById('hud-device-badge');
      const label = document.getElementById('hud-device-label');
      const icon = document.getElementById('hud-device-icon');

      if (label) {
        label.textContent = mode === 'desktop' ? 'DESKTOP' : 'MOBILE';
      }
      if (icon) {
        icon.setAttribute('class', mode === 'desktop' ? 'w-3 h-3 text-auraCyan' : 'w-3 h-3 text-auraEmerald');
      }
      if (badge) {
        badge.title = `Modo Atual: ${mode.toUpperCase()} (Clique para alternar visão)`;
      }

      // Alterna visibilidade da Glance Bar do Desktop
      const desktopGlanceBar = document.getElementById('desktop-glance-bar');
      if (desktopGlanceBar) {
        if (mode === 'desktop') {
          desktopGlanceBar.classList.remove('hidden');
        } else {
          desktopGlanceBar.classList.add('hidden');
        }
      }
    }

    toggleOverride() {
      if (this.override === 'desktop') {
        this.override = 'mobile';
      } else if (this.override === 'mobile') {
        this.override = null; // volta para auto
      } else {
        this.override = this.mode === 'desktop' ? 'mobile' : 'desktop';
      }
      this.detect();
      if (window.auraAudio) window.auraAudio.playChime(640, 0.05);
    }

    bindHudControls() {
      const badge = document.getElementById('hud-device-badge');
      if (badge) {
        badge.addEventListener('click', () => this.toggleOverride());
      }
    }

    onDeviceChange(fn) {
      this.listeners.push(fn);
    }

    notifyListeners() {
      this.listeners.forEach(fn => {
        try { fn(this.mode); } catch (_) {}
      });
    }

    isDesktop() {
      return this.mode === 'desktop';
    }

    isMobile() {
      return this.mode === 'mobile';
    }
  }

  // ==========================================================================
  // 2. MONITOR DE TAXA DE ATUALIZAÇÃO (HERTZ DO MONITOR & FLUIDEZ ADAPTATIVA)
  // ==========================================================================
  class AuraRefreshRateMonitor {
    constructor() {
      this.detectedHz = 60;
      this.tier = 'Standard 60Hz';
      this.frameTimes = [];
      this.maxSamples = 50;
      this.isRunning = false;
      this.calibrated = false;
    }

    init() {
      this.startCalibration();
      // Recalibra ao mudar de aba ou focar (caso o usuário troque de monitor externo)
      window.addEventListener('focus', () => this.startCalibration(), { passive: true });
    }

    startCalibration() {
      this.frameTimes = [];
      this.calibrated = false;
      let lastTime = performance.now();

      const sample = (now) => {
        const delta = now - lastTime;
        lastTime = now;

        // Ignora saltos anômalos (ex: minimizou aba)
        if (delta > 2 && delta < 100) {
          this.frameTimes.push(delta);
        }

        if (this.frameTimes.length < this.maxSamples) {
          requestAnimationFrame(sample);
        } else {
          this.computeHz();
        }
      };

      requestAnimationFrame(sample);
    }

    computeHz() {
      if (this.frameTimes.length === 0) return;

      // Mediana / Média descartando outliers
      const sorted = [...this.frameTimes].sort((a, b) => a - b);
      const trimmed = sorted.slice(5, -5);
      const avgDelta = trimmed.reduce((sum, d) => sum + d, 0) / trimmed.length;
      const rawFps = 1000 / avgDelta;

      // Categorização em faixas padrão de hardware
      let snappedHz = 60;
      let tierName = '60 Hz';

      if (rawFps >= 220) {
        snappedHz = 240;
        tierName = '240 Hz Hyper';
      } else if (rawFps >= 155) {
        snappedHz = 165;
        tierName = '165 Hz Esports';
      } else if (rawFps >= 135) {
        snappedHz = 144;
        tierName = '144 Hz Ultra';
      } else if (rawFps >= 110) {
        snappedHz = 120;
        tierName = '120 Hz ProMotion';
      } else if (rawFps >= 80) {
        snappedHz = 90;
        tierName = '90 Hz Smooth+';
      } else if (rawFps >= 68) {
        snappedHz = 75;
        tierName = '75 Hz Smooth';
      } else {
        snappedHz = 60;
        tierName = '60 Hz Fluid';
      }

      this.detectedHz = snappedHz;
      this.tier = tierName;
      this.calibrated = true;

      // Injeta no CSS variables
      document.documentElement.style.setProperty('--display-hz', snappedHz);
      document.documentElement.style.setProperty('--frame-time-ms', `${avgDelta.toFixed(2)}ms`);
      document.documentElement.setAttribute('data-hz', snappedHz);

      // Atualiza badge de telemetria no HUD
      const badge = document.getElementById('hud-hz-badge');
      const val = document.getElementById('hud-hz-value');
      if (val) {
        val.textContent = tierName;
      }
      if (badge) {
        badge.title = `Taxa de Atualização do Monitor Sincronizada: ${rawFps.toFixed(1)} FPS (${snappedHz}Hz nativo)`;
      }

      // Ajusta passo do motor de aurora boreal
      if (window.auraBorealis) {
        window.auraBorealis.setFrameStep(snappedHz);
      }
    }
  }

  // ==========================================================================
  // 3. MOTOR DE AURORA BOREAL (AMBIÊNCIA FLUÍDA NAS CORES DA AURA)
  // Cores: Esmeralda (#10b981), Azul Ciano (#06b6d4), Roxo Gameplay (#7c3aed)
  // Fundo: Obsidian profundo (#07090e)
  // ==========================================================================
  class AuraBorealisEngine {
    constructor() {
      this.canvas = null;
      this.ctx = null;
      this.width = 0;
      this.height = 0;
      this.time = 0;
      this.speed = 0.0006;
      this.mouseX = 0.5;
      this.mouseY = 0.5;
      this.targetMouseX = 0.5;
      this.targetMouseY = 0.5;
      this.isRunning = false;
      this.hzMultiplier = 1.0;
      this.reducedMotion = false;
    }

    init() {
      this.reducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      if (window.matchMedia) {
        window.matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', (e) => {
          this.reducedMotion = e.matches;
        });
      }
      this.createCanvas();
      this.bindEvents();
      this.start();
    }

    createCanvas() {
      let canvas = document.getElementById('aura-borealis-canvas');
      if (!canvas) {
        canvas = document.createElement('canvas');
        canvas.id = 'aura-borealis-canvas';
        canvas.className = 'aura-borealis-layer';
        document.body.prepend(canvas);
      }
      this.canvas = canvas;
      this.ctx = canvas.getContext('2d', { alpha: true });
      this.resize();
    }

    resize() {
      if (!this.canvas) return;
      // Resolução leve (escala 0.5) com interpolação e blur suave de hardware
      const scale = window.innerWidth > 1440 ? 0.6 : 0.5;
      this.width = Math.max(320, Math.floor(window.innerWidth * scale));
      this.height = Math.max(240, Math.floor(window.innerHeight * scale));
      this.canvas.width = this.width;
      this.canvas.height = this.height;
    }

    bindEvents() {
      window.addEventListener('resize', () => this.resize(), { passive: true });

      // Parallax sutil ao mover o cursor no Desktop
      window.addEventListener('mousemove', (e) => {
        this.targetMouseX = e.clientX / window.innerWidth;
        this.targetMouseY = e.clientY / window.innerHeight;
      }, { passive: true });

      // Pausa quando a aba fica invisível para 0 consumo de CPU
      document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
          this.isRunning = false;
        } else {
          this.isRunning = true;
          this.loop();
        }
      });
    }

    setFrameStep(hz) {
      // Ajusta velocidade para que 60Hz, 120Hz, 144Hz ou 240Hz mantenham o mesmo ritmo biológico calmo
      this.hzMultiplier = 60 / Math.max(30, hz);
    }

    start() {
      this.isRunning = true;
      this.loop();
    }

    loop() {
      if (!this.isRunning) return;

      const isGpuGuard = typeof document !== 'undefined' && document.documentElement.classList.contains('gpu-guard-active');
      if (isGpuGuard || this.reducedMotion) {
        if (this.ctx) this.ctx.clearRect(0, 0, this.width, this.height);
        setTimeout(() => {
          if (this.isRunning) requestAnimationFrame(() => this.loop());
        }, 300);
        return;
      }

      this.updatePhysics();
      this.render();

      requestAnimationFrame(() => this.loop());
    }

    updatePhysics() {
      if (this.reducedMotion) return;

      // Pacing calmo e orgânico sincronizado com os Hertz
      this.time += this.speed * this.hzMultiplier;

      // Amortecimento lerp do mouse
      this.mouseX += (this.targetMouseX - this.mouseX) * 0.04;
      this.mouseY += (this.targetMouseY - this.mouseY) * 0.04;
    }

    render() {
      if (!this.ctx) return;
      const ctx = this.ctx;
      const w = this.width;
      const h = this.height;

      // Limpa com transparência
      ctx.clearRect(0, 0, w, h);

      // Deslocamento orgânico induzido pelo mouse
      const mouseShiftX = (this.mouseX - 0.5) * (w * 0.15);
      const mouseShiftY = (this.mouseY - 0.5) * (h * 0.10);

      // --- CAMADA 1: ONDA ESMERALDA (#10b981) - Estabilidade e Operação ---
      this.drawAuroraRibbon(ctx, {
        yBase: h * 0.25 + mouseShiftY * 0.5,
        amplitude: h * 0.18,
        wavelength: w * 0.65,
        speedFactor: 1.0,
        colorStart: 'rgba(16, 185, 129, 0.16)', // Verde Esmeralda AURA
        colorMid: 'rgba(5, 150, 105, 0.08)',
        colorEnd: 'rgba(7, 9, 14, 0.0)',
        shiftX: mouseShiftX * 0.8,
        harmonic: 2.2
      });

      // --- CAMADA 2: ONDA AZUL CIANO (#06b6d4) - Telemetria e Inteligência ---
      this.drawAuroraRibbon(ctx, {
        yBase: h * 0.40 + mouseShiftY * 0.8,
        amplitude: h * 0.22,
        wavelength: w * 0.55,
        speedFactor: 1.35,
        colorStart: 'rgba(6, 182, 212, 0.14)', // Azul Ciano AURA
        colorMid: 'rgba(8, 145, 178, 0.07)',
        colorEnd: 'rgba(7, 9, 14, 0.0)',
        shiftX: -mouseShiftX * 0.9,
        harmonic: 1.8
      });

      // --- CAMADA 3: ONDA ROXO GAMEPLAY (#7c3aed) - Núcleo Cognitivo Executivo ---
      this.drawAuroraRibbon(ctx, {
        yBase: h * 0.60 + mouseShiftY * 0.6,
        amplitude: h * 0.20,
        wavelength: w * 0.75,
        speedFactor: 0.8,
        colorStart: 'rgba(124, 58, 237, 0.15)', // Roxo Gameplay AURA
        colorMid: 'rgba(109, 40, 217, 0.06)',
        colorEnd: 'rgba(7, 9, 14, 0.0)',
        shiftX: mouseShiftX * 0.6,
        harmonic: 2.5
      });
    }

    drawAuroraRibbon(ctx, config) {
      const w = this.width;
      const h = this.height;
      const t = this.time * config.speedFactor;

      ctx.save();
      ctx.beginPath();
      ctx.moveTo(0, h);

      // Traçado ondulatório composto
      const points = 24;
      const step = w / points;

      for (let i = 0; i <= points; i++) {
        const x = i * step;
        const normX = x / config.wavelength;
        
        // Superposição harmônica de senos
        const wave1 = Math.sin(normX * Math.PI * 2 + t) * config.amplitude;
        const wave2 = Math.cos(normX * Math.PI * config.harmonic - t * 0.7) * (config.amplitude * 0.45);
        const wave3 = Math.sin(normX * Math.PI * 0.5 + t * 1.4) * (config.amplitude * 0.25);

        const y = config.yBase + wave1 + wave2 + wave3;

        if (i === 0) {
          ctx.lineTo(x, y);
        } else {
          const prevX = (i - 1) * step;
          const cpX = (prevX + x) / 2;
          ctx.quadraticCurveTo(prevX, y, x, y);
        }
      }

      ctx.lineTo(w, h);
      ctx.closePath();

      // Gradiente vertical simulando cortina de aurora boreal
      const grad = ctx.createLinearGradient(0, config.yBase - config.amplitude, 0, h);
      grad.addColorStop(0, config.colorStart);
      grad.addColorStop(0.35, config.colorMid);
      grad.addColorStop(0.85, config.colorEnd);
      grad.addColorStop(1, 'transparent');

      ctx.fillStyle = grad;
      ctx.fill();
      ctx.restore();
    }
  }

  // ==========================================================================
  // 4. EFEITOS GLANCE & SPECULAR LIGHTING (MICRO-INTERAÇÕES DESKTOP)
  // ==========================================================================
  class AuraGlanceEngine {
    constructor() {
      this.activeCard = null;
    }

    init() {
      this.bindSpecularMouseHighlight();
      this.bindGlanceHoverCards();
      this.bindCommandPalette();
    }

    bindSpecularMouseHighlight() {
      // Efeito glance de brilho de borda e superfície interativa
      document.addEventListener('mousemove', (e) => {
        if (!window.auraDevice || !window.auraDevice.isDesktop()) return;

        const target = e.target.closest('.glass-panel, .glance-card, .tank-card-interactive');
        if (!target) return;

        const rect = target.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        target.style.setProperty('--mouse-x', `${x}px`);
        target.style.setProperty('--mouse-y', `${y}px`);
      }, { passive: true });
    }

    bindGlanceHoverCards() {
      // Delegado para glance rápido
      document.addEventListener('mouseover', (e) => {
        if (!window.auraDevice || !window.auraDevice.isDesktop()) return;

        const trigger = e.target.closest('[data-glance-tip]');
        if (!trigger) return;

        const text = trigger.getAttribute('data-glance-tip');
        if (!text) return;

        // Feedback sonoro tático ultra discreto (se áudio ligado)
        if (window.auraAudio && Math.random() < 0.2) {
          window.auraAudio.playChime(880, 0.02);
        }
      });
    }

    bindCommandPalette() {
      // Atalho de Teclado Global Executivo: Ctrl+K ou Cmd+K
      window.addEventListener('keydown', (e) => {
        const modal = document.getElementById('aura-command-palette-modal');
        const isPaletteOpen = modal && !modal.classList.contains('hidden');

        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
          e.preventDefault();
          this.toggleCommandPalette();
          return;
        }

        // Tecla ESC fecha a paleta
        if (e.key === 'Escape' && isPaletteOpen) {
          e.preventDefault();
          e.stopPropagation();
          this.closeCommandPalette();
          return;
        }

        // Acessibilidade WCAG 2.1 AA: Focus Trap dentro da Command Palette aberta
        if (e.key === 'Tab' && isPaletteOpen) {
          const focusables = modal.querySelectorAll('button:not([disabled]), [tabindex]:not([tabindex="-1"]), a[href], input:not([disabled])');
          if (focusables.length > 0) {
            const first = focusables[0];
            const last = focusables[focusables.length - 1];
            if (!modal.contains(document.activeElement)) {
              e.preventDefault();
              first.focus();
              return;
            }
            if (e.shiftKey && document.activeElement === first) {
              e.preventDefault();
              last.focus();
            } else if (!e.shiftKey && document.activeElement === last) {
              e.preventDefault();
              first.focus();
            }
          }
        }

        // Tecla "/" foca no input de chat no Desktop quando não estiver digitando
        if (e.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
          e.preventDefault();
          const input = document.getElementById('chat-input-text');
          if (input) input.focus();
        }

        // Atalhos 1, 2, 3, 4 para alternar abas no Desktop
        if (document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
          if (e.key === '1') window.auraApp && window.auraApp.switchTab('console');
          if (e.key === '2') window.auraApp && window.auraApp.switchTab('cockpit');
          if (e.key === '3') window.auraApp && window.auraApp.switchTab('triggers');
          if (e.key === '4') window.auraApp && window.auraApp.switchTab('split');
        }
      });

      // Botão disparador da Command Palette no header
      const btnPalette = document.getElementById('btn-open-palette');
      if (btnPalette) {
        btnPalette.addEventListener('click', () => this.toggleCommandPalette());
      }

      // Clique no backdrop fora do container fecha a modal (F6-03)
      const modalEl = document.getElementById('aura-command-palette-modal');
      if (modalEl) {
        modalEl.addEventListener('click', (e) => {
          if (e.target === modalEl) {
            this.closeCommandPalette();
          }
        });
      }

      // Input de busca dentro da Command Palette
      const paletteInput = document.getElementById('palette-search-input');
      if (paletteInput) {
        paletteInput.addEventListener('input', (e) => this.filterPalette(e.target.value));
      }
    }

    openCommandPalette() {
      const modal = document.getElementById('aura-command-palette-modal');
      if (modal && modal.classList.contains('hidden')) {
        this.toggleCommandPalette();
      }
    }

    toggleCommandPalette() {
      const modal = document.getElementById('aura-command-palette-modal');
      if (!modal) return;

      const isHidden = modal.classList.contains('hidden');
      if (isHidden) {
        this.previousActiveElement = document.activeElement;
        modal.classList.remove('hidden');
        if (window.auraAudio) window.auraAudio.playChime(720, 0.05);
        const input = document.getElementById('palette-search-input');
        if (input) {
          input.value = '';
          input.focus();
          this.filterPalette('');
        }
      } else {
        this.closeCommandPalette();
      }
    }

    closeCommandPalette() {
      const modal = document.getElementById('aura-command-palette-modal');
      if (modal) modal.classList.add('hidden');
      if (this.previousActiveElement && typeof this.previousActiveElement.focus === 'function') {
        try {
          this.previousActiveElement.focus();
        } catch (_) {}
      }
    }

    filterPalette(query) {
      const q = query.trim().toLowerCase();
      const items = document.querySelectorAll('.palette-item');
      items.forEach(item => {
        const text = item.textContent.toLowerCase();
        if (!q || text.includes(q)) {
          item.classList.remove('hidden');
        } else {
          item.classList.add('hidden');
        }
      });
    }

    executePaletteAction(promptText) {
      this.closeCommandPalette();
      if (window.auraChat) {
        window.auraApp && window.auraApp.switchTab('console');
        window.auraChat.sendUserPrompt(promptText);
      }
    }
  }

  // ==========================================================================
  // INICIALIZAÇÃO GLOBAL DOS SUBSISTEMAS FX
  // ==========================================================================
  window.auraDevice = new AuraDeviceManager();
  window.auraHz = new AuraRefreshRateMonitor();
  window.auraBorealis = new AuraBorealisEngine();
  window.auraGlance = new AuraGlanceEngine();

  document.addEventListener('DOMContentLoaded', () => {
    window.auraDevice.init();
    window.auraHz.init();
    window.auraBorealis.init();
    window.auraGlance.init();
  });

})();
