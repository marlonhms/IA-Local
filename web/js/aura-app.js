/**
 * AURA Application Coordinator
 * Orquestra as visualizações do painel, alternância de abas, layout split,
 * áudio tático via Web Audio API, ícones com fallback offline e auto-refresh.
 */

class AuraAudio {
  constructor() {
    this.ctx = null;
    this.muted = true; // Mutado por padrão para discrição
  }

  ensureContext() {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) this.ctx = new AudioCtx();
    }
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  toggleMute() {
    this.muted = !this.muted;
    if (!this.muted) {
      this.ensureContext();
      this.playChime(660, 0.08);
    }
    return this.muted;
  }

  playChime(freq = 520, duration = 0.06) {
    if (this.muted) return;
    try {
      this.ensureContext();
      if (!this.ctx) return;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq, this.ctx.currentTime);
      gain.gain.setValueAtTime(0.04, this.ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.0001, this.ctx.currentTime + duration);
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start();
      osc.stop(this.ctx.currentTime + duration);
    } catch (_) {}
  }
}

window.auraAudio = new AuraAudio();

function applyIconsFallback() {
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
    return;
  }

  const svgMap = {
    'fuel': '<svg class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 22V5a2 2 0 012-2h8a2 2 0 012 2v17M15 11l4-4 2 2v13M3 11h12"/></svg>',
    'gauge': '<svg class="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke-width="2"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6l4 2"/></svg>',
    'zap': '<svg class="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><polygon stroke-width="2" points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
    'terminal': '<svg class="w-4 h-4 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><polyline stroke-width="2" points="4 17 10 11 4 5"/><line stroke-width="2" x1="12" y1="19" x2="20" y2="19"/></svg>',
    'layout-grid': '<svg class="w-4 h-4 text-sky-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" stroke-width="2"/><rect x="14" y="3" width="7" height="7" stroke-width="2"/><rect x="14" y="14" width="7" height="7" stroke-width="2"/><rect x="3" y="14" width="7" height="7" stroke-width="2"/></svg>',
    'refresh-cw': '<svg class="w-4 h-4 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/></svg>',
    'volume-2': '<svg class="w-4 h-4 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><polygon stroke-width="2" points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.07 4.93a10 10 0 010 14.14M15.54 8.46a5 5 0 010 7.07"/></svg>',
    'volume-x': '<svg class="w-4 h-4 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><polygon stroke-width="2" points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><line stroke-width="2" x1="23" y1="9" x2="17" y2="15"/><line stroke-width="2" x1="17" y1="9" x2="23" y2="15"/></svg>',
    'send': '<svg class="w-4 h-4 text-slate-900" fill="none" stroke="currentColor" viewBox="0 0 24 24"><line stroke-width="2" x1="22" y1="2" x2="11" y2="13"/><polygon stroke-width="2" points="22 2 15 22 11 13 2 9 22 2"/></svg>',
    'trash-2': '<svg class="w-3.5 h-3.5 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><polyline stroke-width="2" points="3 6 5 6 21 6"/><path stroke-width="2" d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>',
    'shield-check': '<svg class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10zM9 12l2 2 4-4"/></svg>',
    'layers': '<svg class="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><polygon stroke-width="2" points="12 2 2 7 12 12 22 7 12 2"/><polyline stroke-width="2" points="2 17 12 22 22 17"/><polyline stroke-width="2" points="2 12 12 17 22 12"/></svg>',
    'users': '<svg class="w-4 h-4 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-width="2" d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4" stroke-width="2"/><path stroke-width="2" d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/></svg>',
    'shield-alert': '<svg class="w-4 h-4 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-width="2" d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10zM12 8v4M12 16h.01"/></svg>',
    'receipt': '<svg class="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-width="2" d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1-2-1zM8 7h8M8 11h8M8 15h5"/></svg>',
    'book-check': '<svg class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-width="2" d="M4 19.5A2.5 2.5 0 016.5 17H20M4 4.5A2.5 2.5 0 016.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15zM9 10l2 2 4-4"/></svg>',
    'shopping-bag': '<svg class="w-4 h-4 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-width="2" d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4zM3 6h18M16 10a4 4 0 01-8 0"/></svg>',
    'sparkles': '<svg class="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-width="2" d="M12 3l1.5 5.5L19 10l-5.5 1.5L12 17l-1.5-5.5L5 10l5.5-1.5L12 3z"/></svg>',
    'square': '<svg class="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16" rx="2"/></svg>',
  };

  document.querySelectorAll('i[data-lucide]').forEach(el => {
    const iconName = el.getAttribute('data-lucide');
    if (svgMap[iconName]) {
      el.outerHTML = svgMap[iconName];
    }
  });
}

class AuraApp {
  constructor() {
    this.currentTab = 'console';
    this.autoRefreshInterval = 30; // segundos
    this.refreshTimer = null;
    this.countdownSeconds = 30;
  }

  init() {
    this.bindNavigationTabs();
    this.startClock();
    this.setupAutoRefresh();

    // Inicializa subsistemas
    window.auraCockpit.init();
    window.auraTriggers.renderGrid();
    window.auraChat.init();

    // Inicia diretamente no Console Cognitivo (Mobile-First Workspace)
    this.switchTab('console');

    applyIconsFallback();
  }

  bindNavigationTabs() {
    const tabs = document.querySelectorAll('.nav-tab-btn');
    tabs.forEach(btn => {
      btn.addEventListener('click', () => {
        const target = btn.getAttribute('data-tab');
        if (target) {
          window.auraAudio.playChime(600, 0.05);
          this.switchTab(target);
        }
      });
    });

    // Filtros de gatilhos 1-clique
    const filterBtns = document.querySelectorAll('.trigger-filter-btn');
    filterBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const filter = btn.getAttribute('data-filter');
        if (filter) {
          window.auraAudio.playChime(500, 0.04);
          window.auraTriggers.setFilter(filter);
          applyIconsFallback();
        }
      });
    });

    // Botão de refresh manual do cockpit
    const btnRefresh = document.getElementById('btn-refresh-cockpit');
    if (btnRefresh) {
      btnRefresh.addEventListener('click', () => {
        window.auraAudio.playChime(700, 0.06);
        window.auraCockpit.refreshAllData();
        this.resetCountdown();
      });
    }

    // Botão SFX Audio
    const btnToggleSfx = document.getElementById('btn-toggle-sfx');
    if (btnToggleSfx) {
      btnToggleSfx.addEventListener('click', () => {
        const isMuted = window.auraAudio.toggleMute();
        btnToggleSfx.title = isMuted ? 'Áudio Mudo (Clique para Ativar SFX)' : 'Áudio Ativo (Clique para Mutar)';
        btnToggleSfx.className = isMuted 
          ? 'p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white border border-slate-700 transition-colors'
          : 'p-1.5 rounded-lg bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 transition-colors';
      });
    }

    // Botão copiar JSON
    const btnCopyJson = document.getElementById('btn-copy-json');
    if (btnCopyJson) {
      btnCopyJson.addEventListener('click', () => {
        window.auraAudio.playChime(800, 0.05);
        window.auraTriggers.copyJson();
      });
    }

    // Botão enviar resultado para a AURA
    const btnSendToAura = document.getElementById('btn-send-to-aura');
    if (btnSendToAura) {
      btnSendToAura.addEventListener('click', () => {
        window.auraAudio.playChime(750, 0.07);
        window.auraTriggers.sendResultToAura();
      });
    }

    // Abas internas do Inspetor de Gatilhos (Formatado vs JSON)
    const tabInspectorFormatted = document.getElementById('tab-inspector-formatted');
    const tabInspectorJson = document.getElementById('tab-inspector-json');
    const contentFormatted = document.getElementById('inspector-content-formatted');
    const contentJson = document.getElementById('inspector-content-json');

    if (tabInspectorFormatted && tabInspectorJson && contentFormatted && contentJson) {
      tabInspectorFormatted.addEventListener('click', () => {
        window.auraAudio.playChime(540, 0.04);
        tabInspectorFormatted.classList.add('bg-slate-800', 'text-white');
        tabInspectorFormatted.classList.remove('text-slate-400');
        tabInspectorJson.classList.remove('bg-slate-800', 'text-white');
        tabInspectorJson.classList.add('text-slate-400');
        contentFormatted.classList.remove('hidden');
        contentJson.classList.add('hidden');
      });

      tabInspectorJson.addEventListener('click', () => {
        window.auraAudio.playChime(540, 0.04);
        tabInspectorJson.classList.add('bg-slate-800', 'text-white');
        tabInspectorJson.classList.remove('text-slate-400');
        tabInspectorFormatted.classList.remove('bg-slate-800', 'text-white');
        tabInspectorFormatted.classList.add('text-slate-400');
        contentJson.classList.remove('hidden');
        contentFormatted.classList.add('hidden');
      });
    }
  }

  /**
   * Alterna a visualização ativa
   */
  switchTab(tabName) {
    this.currentTab = tabName;

    document.querySelectorAll('.nav-tab-btn').forEach(btn => {
      const isTarget = btn.getAttribute('data-tab') === tabName;
      if (isTarget) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    const viewCockpit = document.getElementById('view-cockpit');
    const viewTriggers = document.getElementById('view-triggers');
    const viewConsole = document.getElementById('view-console');
    const viewSplit = document.getElementById('view-split');

    [viewCockpit, viewTriggers, viewConsole, viewSplit].forEach(v => {
      if (v) v.classList.add('hidden');
    });

    if (tabName === 'cockpit') {
      if (viewCockpit) viewCockpit.classList.remove('hidden');
    } else if (tabName === 'triggers') {
      if (viewTriggers) viewTriggers.classList.remove('hidden');
    } else if (tabName === 'console') {
      if (viewConsole) viewConsole.classList.remove('hidden');
      const input = document.getElementById('chat-input-text');
      if (input) input.focus();
    } else if (tabName === 'split') {
      if (viewSplit) viewSplit.classList.remove('hidden');
      const splitInput = document.getElementById('split-chat-input-text');
      if (splitInput) splitInput.focus();
      // Assegura tanques renderizados
      if (window.auraCockpit && window.auraCockpit.tanksData) {
        window.auraCockpit.renderSplitTanks(window.auraCockpit.tanksData);
      }
    }

    applyIconsFallback();
  }

  /**
   * Atalho acionado a partir de um card de tanque
   */
  askAboutTank(codtan, combustivel) {
    const prompt = `Qual a previsão de esgotamento e a autonomia estimada para o tanque ${codtan} (${combustivel})? Devemos emitir pedido de carreta para hoje?`;
    if (this.currentTab === 'split') {
      window.auraChat.sendUserPrompt(prompt);
    } else {
      this.switchTab('console');
      window.auraChat.sendUserPrompt(prompt);
    }
  }

  startClock() {
    const clockEl = document.getElementById('hud-live-clock');
    const clockMobile = document.getElementById('hud-live-clock-mobile');

    const update = () => {
      const now = new Date();
      const timeStr = now.toLocaleTimeString('pt-BR');
      if (clockEl) clockEl.textContent = timeStr;
      if (clockMobile) clockMobile.textContent = timeStr;
    };
    update();
    setInterval(update, 1000);
  }

  setupAutoRefresh() {
    this.countdownSeconds = this.autoRefreshInterval;
    const countdownEl = document.getElementById('hud-refresh-countdown');

    setInterval(() => {
      if (this.currentTab === 'cockpit' || this.currentTab === 'split') {
        this.countdownSeconds--;
        if (countdownEl) countdownEl.textContent = `${this.countdownSeconds}s`;

        if (this.countdownSeconds <= 0) {
          window.auraCockpit.refreshAllData();
          this.resetCountdown();
        }
      }
    }, 1000);
  }

  resetCountdown() {
    this.countdownSeconds = this.autoRefreshInterval;
    const countdownEl = document.getElementById('hud-refresh-countdown');
    if (countdownEl) countdownEl.textContent = `${this.countdownSeconds}s`;
  }
}

// Instanciação e boot
window.auraApp = new AuraApp();
document.addEventListener('DOMContentLoaded', () => {
  window.auraApp.init();
});
