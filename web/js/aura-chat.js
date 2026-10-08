/**
 * AURA Console Cognitivo Controller
 * Gerencia a conversa em tempo real com streaming SSE token-a-token,
 * renderização de blocos tipados (Intent, Tool Start, Tool Result, Telemetry),
 * Markdown rico com GitHub Flavored Markdown e breaks,
 * espelhamento em tempo real com a Visão Split e memória de sessão durável.
 */

const CHAT_ICONS = {
  truck: '<svg class="w-3.5 h-3.5 inline mr-1 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor"><rect x="1" y="4" width="14" height="12" rx="1.5" stroke-width="1.75"/><path d="M15 8h4.5l2.5 3.5V16h-7V8z" stroke-width="1.75" stroke-linejoin="round"/><circle cx="5.5" cy="18.5" r="2.5" stroke-width="1.75"/><circle cx="18.5" cy="18.5" r="2.5" stroke-width="1.75"/></svg>',
  formula: '<svg class="w-3.5 h-3.5 inline mr-1 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M21 3L3 21h18V3z" stroke-width="1.75" stroke-linejoin="round"/><line x1="9" y1="21" x2="9" y2="17" stroke-width="1.5"/><line x1="13" y1="21" x2="13" y2="15" stroke-width="1.5"/><line x1="17" y1="21" x2="17" y2="13" stroke-width="1.5"/></svg>',
  tank: '<svg class="w-3.5 h-3.5 inline mr-1 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor"><rect x="3" y="3" width="11" height="18" rx="2" stroke-width="1.75"/><line x1="2" y1="21" x2="15" y2="21" stroke-width="1.75"/><path d="M14 8h2.5a2 2 0 0 1 2 2v6.5a1.5 1.5 0 0 0 3 0V9l-2-2" stroke-width="1.5"/></svg>',
  audit: '<svg class="w-3.5 h-3.5 inline mr-1 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" stroke-width="1.75"/><rect x="8" y="2" width="8" height="4" rx="1" stroke-width="1.75"/></svg>',
  search: '<svg class="w-3.5 h-3.5 inline mr-1 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="11" cy="11" r="8" stroke-width="1.75"/><line x1="21" y1="21" x2="16.65" y2="16.65" stroke-width="1.75"/></svg>',
  store: '<svg class="w-3.5 h-3.5 inline mr-1 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z" stroke-width="1.75"/><line x1="3" y1="6" x2="21" y2="6" stroke-width="1.75"/></svg>',
  nozzle: '<svg class="w-3.5 h-3.5 inline mr-1 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" stroke-width="1.75"/></svg>',
  chart: '<svg class="w-3.5 h-3.5 inline mr-1 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor"><line x1="18" y1="20" x2="18" y2="10" stroke-width="2"/><line x1="12" y1="20" x2="12" y2="4" stroke-width="2"/><line x1="6" y1="20" x2="6" y2="14" stroke-width="2"/></svg>',
  calendar: '<svg class="w-3 h-3 inline mr-1 flex-shrink-0 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor"><rect x="3" y="4" width="18" height="18" rx="2" stroke-width="2"/><line x1="16" y1="2" x2="16" y2="6" stroke-width="2"/><line x1="8" y1="2" x2="8" y2="6" stroke-width="2"/><line x1="3" y1="10" x2="21" y2="10" stroke-width="2"/></svg>',
  unit: '<svg class="w-3 h-3 inline mr-1 flex-shrink-0 text-cyan-400" viewBox="0 0 24 24" fill="none" stroke="currentColor"><rect x="4" y="2" width="16" height="20" rx="2" stroke-width="2"/><line x1="9" y1="22" x2="9" y2="12" stroke-width="2"/><line x1="15" y1="22" x2="15" y2="12" stroke-width="2"/></svg>',
  check: '<svg class="w-3.5 h-3.5 inline mr-1 flex-shrink-0 text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor"><polyline points="20 6 9 17 4 12" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  alert: '<svg class="w-3.5 h-3.5 inline mr-1 flex-shrink-0 text-amber-400" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" stroke-width="1.75" stroke-linejoin="round"/><line x1="12" y1="9" x2="12" y2="13" stroke-width="1.75" stroke-linecap="round"/><circle cx="12" cy="17" r="1" fill="currentColor"/></svg>',
  pulse: '<svg class="w-3.5 h-3.5 inline mr-1 flex-shrink-0 text-cyan-400" viewBox="0 0 24 24" fill="none" stroke="currentColor"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  target: '<svg class="w-3.5 h-3.5 inline mr-1 flex-shrink-0 text-cyan-400" viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="12" cy="12" r="10" stroke-width="2"/><circle cx="12" cy="12" r="6" stroke-width="2"/><circle cx="12" cy="12" r="2" fill="currentColor"/></svg>',
  box: '<svg class="w-3.5 h-3.5 inline mr-1 flex-shrink-0 text-purple-300" viewBox="0 0 24 24" fill="none" stroke="currentColor"><rect x="3" y="3" width="18" height="18" rx="2" stroke-width="1.75"/><line x1="3" y1="9" x2="21" y2="9" stroke-width="1.5"/></svg>',
  dialog: '<svg class="w-3.5 h-3.5 inline mr-1 flex-shrink-0 text-purple-400" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  wrench: '<svg class="w-3.5 h-3.5 inline mr-1 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" stroke-width="1.75"/></svg>',
  pause: '<svg class="w-3.5 h-3.5 inline mr-1 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor"><rect x="6" y="4" width="4" height="16" rx="1" stroke-width="1.75"/><rect x="14" y="4" width="4" height="16" rx="1" stroke-width="1.75"/></svg>',
  core: '<svg class="w-3.5 h-3.5 inline mr-1 flex-shrink-0" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><polygon points="12 2 20.66 7 20.66 17 12 22 3.34 17 3.34 7" stroke="currentColor" stroke-width="1.75" stroke-linejoin="round"/><circle cx="12" cy="12" r="2.2" fill="currentColor"/></svg>',
  sparkles: '<svg class="w-3.5 h-3.5 inline mr-1 flex-shrink-0" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><polygon points="12 2 20.66 7 20.66 17 12 22 3.34 17 3.34 7" stroke="currentColor" stroke-width="1.75" stroke-linejoin="round"/><circle cx="12" cy="12" r="2.2" fill="currentColor"/></svg>',
  telemetry: '<svg class="w-3.5 h-3.5 inline mr-1 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="12" cy="12" r="9" stroke-width="1.75"/><path d="M12 7v5l3.5 2" stroke-width="2" stroke-linecap="round"/><circle cx="12" cy="12" r="2" fill="currentColor"/><path d="M7 16a6 6 0 0 1 10 0" stroke-width="1.5" stroke-dasharray="2 2"/></svg>',
  shield: '<svg class="w-3.5 h-3.5 inline mr-1 flex-shrink-0 text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" stroke-width="1.75"/><path d="M9 12l2 2 4-4" stroke-width="1.75"/></svg>',
  clock: '<svg class="w-3.5 h-3.5 inline mr-1 flex-shrink-0 text-amber-400" viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="12" cy="12" r="9" stroke-width="1.75"/><polyline points="12 6 12 12 15 15" stroke-width="1.75"/></svg>',
  bulb: '<svg class="w-3.5 h-3.5 inline mr-1 flex-shrink-0 text-cyan-400" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M9 18h6m-4 4h2a8 8 0 1 0-8-8c0 2.2 1 4.2 2.5 5.5.6.5 1 1.5 1.5 2.5z" stroke-width="1.75"/></svg>',
  terminal: '<svg class="w-3.5 h-3.5 inline mr-1 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor"><polyline points="4 17 10 11 4 5" stroke-width="2"/><line x1="12" y1="19" x2="20" y2="19" stroke-width="2"/></svg>',
  volume: '<svg class="w-3.5 h-3.5 inline mr-1 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" stroke-width="1.75"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07" stroke-width="1.75"/></svg>',
  folder: '<svg class="w-3.5 h-3.5 inline mr-1 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" stroke-width="1.75"/></svg>',
  rocket: '<svg class="w-3.5 h-3.5 inline mr-1 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09zM12 15l-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z" stroke-width="1.75"/></svg>',
  refresh: '<svg class="w-3.5 h-3.5 inline mr-1 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor"><polyline points="23 4 23 10 17 10" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/><polyline points="1 20 1 14 7 14" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/></svg>'
};

class AuraChatController {
  constructor() {
    this.sessionId = this.generateSessionId();
    this.isStreaming = false;
    this.isSubmitting = false;
    this.abortController = null;
    this.messages = [];
    this.userScrolledUp = false;

    // F5-01: Registro Modular Centralizado de Renderizadores Especializados por Intent / Ferramenta
    this.responseRenderers = {
      'shift_reconciliation': this.renderTurnoWidget.bind(this),
      'conciliacao_turno': this.renderTurnoWidget.bind(this),
      'auditoria_turno': this.renderTurnoWidget.bind(this),
      'auditar_fechamento_turno': this.renderTurnoWidget.bind(this),

      'tank_forecast': this.renderTankAutonomyWidget.bind(this),
      'previsao_tanques': this.renderTankAutonomyWidget.bind(this),
      'run_out': this.renderTankAutonomyWidget.bind(this),
      'prever_esgotamento_tanques': this.renderTankAutonomyWidget.bind(this),

      'pump_performance': this.renderDesempenhoPistaWidget.bind(this),
      'desempenho_pista_frentistas': this.renderDesempenhoPistaWidget.bind(this),
      'auditar_desempenho_pista_frentistas': this.renderDesempenhoPistaWidget.bind(this),

      'lmc_report': this.renderLmcAnpWidget.bind(this),
      'lmc_anp': this.renderLmcAnpWidget.bind(this),
      'gerar_relatorio_lmc_anp': this.renderLmcAnpWidget.bind(this),

      'market_basket': this.renderCombosWidget.bind(this),
      'conveniencia_vendas_cruzadas': this.renderCombosWidget.bind(this),
      'auditar_cesta_conveniencia_vendas_cruzadas': this.renderCombosWidget.bind(this),

      'ajuda_sistema': this.renderAjudaSistemaWidget.bind(this),
      'conhecimento_aura': this.renderAjudaSistemaWidget.bind(this),
      'ajuda': this.renderAjudaSistemaWidget.bind(this),

      'vendas_analitico': this.renderVendasAnaliticoWidget.bind(this),
      'consultar_analise_vendas_erp': this.renderVendasAnaliticoWidget.bind(this),
      'analise_vendas': this.renderVendasAnaliticoWidget.bind(this),
      'vendas': this.renderVendasAnaliticoWidget.bind(this),
    };
  }

  generateSessionId() {
    return 'aura_ui_' + Math.random().toString(36).substring(2, 10);
  }

  /**
   * F6-03 & F6-04: Anunciador Acessível para Leitores de Tela (WCAG 2.1 AA)
   * Emite anúncios estáveis apenas em eventos-chave (início, ferramenta, término, erro),
   * evitando poluição sonora a cada token do streaming.
   */
  announceToScreenReader(message) {
    if (typeof document === 'undefined') return;
    const el = document.getElementById('aura-sr-announcer');
    if (el) {
      el.textContent = '';
      setTimeout(() => { el.textContent = message; }, 50);
    }
  }

  autoResizeInput(textarea) {
    if (!textarea) return;
    textarea.style.height = 'auto';
    const newHeight = Math.min(Math.max(textarea.scrollHeight, 44), 160);
    textarea.style.height = `${newHeight}px`;
  }

  init() {
    if (window.marked && typeof window.marked.setOptions === 'function') {
      try {
        window.marked.setOptions({
          gfm: true,
          breaks: true,
        });
      } catch (_) {}
    }
    this.bindEvents();
    this.renderSessionId();
    const feed = document.getElementById('chat-feed-container');
    if (!feed || !feed.firstElementChild) {
      this.addWelcomeMessage();
    }
    this.expireStaleWidgets();
    if (typeof window !== 'undefined' && typeof window.setInterval === 'function') {
      try {
        window.setInterval(() => this.expireStaleWidgets(), 60000);
      } catch (_) {}
    }
  }

  bindEvents() {
    const input = document.getElementById('chat-input-text');
    const sendBtn = document.getElementById('btn-chat-send');
    const stopBtn = document.getElementById('btn-chat-stop');
    const clearBtn = document.getElementById('btn-chat-clear');
    const newChatBtn = document.getElementById('btn-new-chat');

    if (input) {
      input.addEventListener('input', () => {
        this.autoResizeInput(input);
      });

      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          this.handleSendMessage();
        } else if (e.key === 'Enter' && e.shiftKey) {
          setTimeout(() => this.autoResizeInput(input), 0);
        }
      });
    }

    if (sendBtn) sendBtn.addEventListener('click', () => this.handleSendMessage());
    if (stopBtn) stopBtn.addEventListener('click', () => this.abortStreaming());
    if (clearBtn) clearBtn.addEventListener('click', () => this.clearSession());

    // F4-12 & F4-13: Detecção de rolagem e botão flutuante de mensagens recentes
    const chatFeed = document.getElementById('chat-feed-container');
    const scrollBtn = document.getElementById('btn-scroll-bottom');

    if (chatFeed) {
      chatFeed.addEventListener('scroll', () => {
        const threshold = 80;
        const isAtBottom = (chatFeed.scrollHeight - chatFeed.scrollTop - chatFeed.clientHeight) <= threshold;
        this.userScrolledUp = !isAtBottom;
        if (scrollBtn) {
          if (this.userScrolledUp) {
            scrollBtn.classList.remove('hidden');
          } else {
            scrollBtn.classList.add('hidden');
          }
        }
      }, { passive: true });
    }

    if (scrollBtn) {
      scrollBtn.addEventListener('click', () => {
        this.userScrolledUp = false;
        if (chatFeed) {
          chatFeed.scrollTo({ top: chatFeed.scrollHeight, behavior: 'smooth' });
        }
        scrollBtn.classList.add('hidden');
      });
    }

    // Eventos do Drawer de Evidências (Marco 1)
    const closeEvBtn = document.getElementById('btn-close-evidence-drawer');
    const evOverlay = document.getElementById('aura-evidence-drawer-overlay');
    if (closeEvBtn) closeEvBtn.addEventListener('click', () => this.closeEvidence());
    if (evOverlay) evOverlay.addEventListener('click', () => this.closeEvidence());

    document.addEventListener('keydown', (e) => {
      const evDrawer = document.getElementById('aura-evidence-drawer') || document.getElementById('evidence-drawer');
      const isDrawerOpen = evDrawer && (
        evDrawer.classList.contains('open') ||
        evDrawer.getAttribute('aria-hidden') === 'false'
      );

      if (e.key === 'Escape' && isDrawerOpen) {
        e.preventDefault();
        e.stopPropagation();
        this.closeEvidence();
        return;
      }

      // Acessibilidade: Focus Trap dentro do Drawer aberto
      if (e.key === 'Tab' && isDrawerOpen) {
        const focusableEls = evDrawer.querySelectorAll('button:not([disabled]), [tabindex]:not([tabindex="-1"]), [href], input, select, textarea');
        if (focusableEls.length > 0) {
          const firstEl = focusableEls[0];
          const lastEl = focusableEls[focusableEls.length - 1];
          if (!evDrawer.contains(document.activeElement)) {
            e.preventDefault();
            firstEl.focus();
            return;
          }
          if (e.shiftKey) {
            if (document.activeElement === firstEl) {
              e.preventDefault();
              lastEl.focus();
            }
          } else {
            if (document.activeElement === lastEl) {
              e.preventDefault();
              firstEl.focus();
            }
          }
        }
      }
    });

    const tabBtns = Array.from(document.querySelectorAll('.evidence-tab-btn'));
    tabBtns.forEach((btn, idx) => {
      btn.addEventListener('click', () => {
        const tab = btn.getAttribute('data-ev-tab');
        this.switchEvidenceTab(tab);
      });
      // Suporte a navegação por setas (WCAG 2.1 AA - Design Pattern Tablist)
      btn.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
          e.preventDefault();
          const nextBtn = tabBtns[(idx + 1) % tabBtns.length];
          if (nextBtn) {
            nextBtn.focus();
            nextBtn.click();
          }
        } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
          e.preventDefault();
          const prevBtn = tabBtns[(idx - 1 + tabBtns.length) % tabBtns.length];
          if (prevBtn) {
            prevBtn.focus();
            prevBtn.click();
          }
        }
      });
    });
  }

  renderSessionId() {
    const el = document.getElementById('chat-session-badge');
    if (el) el.textContent = `Sessão: ${this.sessionId}`;
  }

  addWelcomeMessage() {
    const welcomeHtml = `
      <div class="space-y-3 font-sans text-slate-200 leading-relaxed text-sm">
        <p>
          Olá! Sou a <strong>AURA</strong>, sua assistente executiva para operações de pista, conveniência e gestão do posto.
        </p>
        <p class="text-slate-300 text-xs sm:text-sm">
          Estou conectada e pronta para apoiar suas decisões. Você pode me perguntar sobre a autonomia dos combustíveis, auditar o fechamento de turno e caixa, verificar a conformidade do LMC com a ANP ou analisar as vendas da loja.
        </p>
      </div>
      <!-- Rodapé do Card de Boas-Vindas: Sugestões Executivas Ancoradas na Base -->
      <div id="welcome-suggestions-container" class="welcome-card-footer mt-auto !mt-auto pt-4 border-t border-white/10 space-y-2.5">
        <span class="text-xs font-medium text-slate-400 flex items-center gap-1.5">
          <svg class="w-3.5 h-3.5 text-cyan-400 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M12 2L20.5 7.2V16.8L12 22L3.5 16.8V7.2L12 2Z" stroke-width="1.75" stroke-linejoin="round"/><circle cx="12" cy="12" r="2" fill="currentColor"/></svg>
          Sugestões executivas para iniciar:
        </span>
        <div class="welcome-suggestions-grid grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
          <button onclick="window.auraChat.sendUserPrompt('Qual o diagnóstico executivo do meu negócio hoje?')" class="quick-prompt-chip !border-cyan-500/40 text-cyan-200 hover:text-white" aria-label="Consultar Mentor de Decisões Executivo">
            <svg class="w-3.5 h-3.5 text-cyan-400 mr-1 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M12 2L20.5 7.2V16.8L12 22L3.5 16.8V7.2L12 2Z" stroke-width="1.75" stroke-linejoin="round"/><circle cx="12" cy="12" r="2" fill="currentColor"/></svg> <span>Mentor de Decisões</span>
          </button>
          <button onclick="window.auraChat.sendUserPrompt('Como fechou o último turno? Teve furo de caixa?')" class="quick-prompt-chip" aria-label="Consultar Fechamento de Turno e Caixa">
            <svg class="w-3.5 h-3.5 text-cyan-400 mr-1 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor"><rect x="2" y="6" width="20" height="12" rx="2" stroke-width="1.75"/><circle cx="12" cy="12" r="3" stroke-width="1.75"/><path d="M6 12h.01M18 12h.01" stroke-width="2"/></svg> <span>Fechamento & Caixa</span>
          </button>
          <button onclick="window.auraChat.sendUserPrompt('Qual a situação e autonomia de cada tanque agora?')" class="quick-prompt-chip" aria-label="Consultar Autonomia de Tanques">
            <svg class="w-3.5 h-3.5 text-emerald-400 mr-1 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor"><rect x="3" y="3" width="11" height="18" rx="2" stroke-width="1.75"/><line x1="2" y1="21" x2="15" y2="21" stroke-width="1.75"/><path d="M14 8h2.5a2 2 0 0 1 2 2v6.5a1.5 1.5 0 0 0 3 0V9l-2-2" stroke-width="1.5"/></svg> <span>Autonomia dos Tanques</span>
          </button>
          <button onclick="window.auraGlance ? window.auraGlance.openCommandPalette() : document.getElementById('btn-open-palette').click()" class="quick-prompt-chip !border-purple-500/30 text-purple-300 hover:text-purple-200" aria-label="Abrir mais consultas rápidas">
            <svg class="w-3.5 h-3.5 text-purple-400 mr-1 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M12 2L20.5 7.2V16.8L12 22L3.5 16.8V7.2L12 2Z" stroke-width="1.75" stroke-linejoin="round"/><polygon points="12,6.5 16.5,9.5 16.5,14.5 12,17.5 7.5,14.5 7.5,9.5" stroke-width="1.25" fill="rgba(168,85,247,0.25)"/><circle cx="12" cy="12" r="2" fill="currentColor"/></svg> <span>Mais consultas (Ctrl+K)</span>
          </button>
        </div>
      </div>
    `;
    this.appendAuraMessage(welcomeHtml, { isWelcome: true });
  }

  /**
   * Dispara prompt vindo de atalhos rápidos ou outros módulos
   */
  sendUserPrompt(text) {
    if (this.isSubmitting || this.isStreaming) return;
    const input = document.getElementById('chat-input-text');
    if (input) input.value = '';
    this.handleSendMessage(text);
  }

  /**
   * Envia a mensagem do usuário e inicia a conexão SSE
   */
  async handleSendMessage(promptText = null) {
    if (this.isSubmitting || this.isStreaming) return;
    this.isSubmitting = true;

    let query = promptText;
    const input = document.getElementById('chat-input-text');

    if (!query) {
      if (input && input.value.trim()) {
        query = input.value.trim();
      }
    }

    if (!query) {
      this.isSubmitting = false;
      return;
    }

    this.announceToScreenReader('Consulta enviada para AURA. Aguardando processamento analítico.');

    // F4-07 & Clean UX: Remove as sugestões de boas-vindas para manter o layout ultra-clean após iniciar a conversa
    const welcomeSuggestions = typeof document !== 'undefined' ? document.getElementById('welcome-suggestions-container') : null;
    if (welcomeSuggestions) {
      welcomeSuggestions.remove();
    }

    // Adapta o card de boas-vindas para altura natural após iniciar a conversa
    const feed = typeof document !== 'undefined' ? document.getElementById('chat-feed-container') : null;
    const welcomeBubble = typeof document !== 'undefined' ? (document.getElementById('welcome-message-bubble') || (feed && feed.children && feed.children[0])) : null;
    if (welcomeBubble && welcomeBubble.classList) {
      welcomeBubble.classList.add('welcome-message-collapsed');
      ['h-full', 'min-h-full', 'flex-1', 'welcome-message-wrapper'].forEach(c => welcomeBubble.classList.remove(c));
      const innerBubble = welcomeBubble.querySelector ? welcomeBubble.querySelector('.chat-bubble-aura') : null;
      if (innerBubble && innerBubble.classList) {
        innerBubble.classList.add('welcome-message-collapsed');
        ['h-full', 'min-h-full', 'flex-1', 'chat-bubble-welcome'].forEach(c => innerBubble.classList.remove(c));
      }
      const innerBody = welcomeBubble.querySelector ? welcomeBubble.querySelector('.welcome-content-body') : null;
      if (innerBody && innerBody.classList) {
        innerBody.classList.add('welcome-message-collapsed');
        ['flex-1', 'justify-between'].forEach(c => innerBody.classList.remove(c));
      }
    }

    if (input) {
      input.value = '';
      input.style.height = 'auto';
    }

    this.userScrolledUp = false;
    const scrollBtn = document.getElementById('btn-scroll-bottom');
    if (scrollBtn) scrollBtn.classList.add('hidden');

    this.setStreamingState(true);

    // 1. Adiciona a mensagem do usuário na tela
    this.appendUserMessage(query);

    // 2. Prepara contêiner para a resposta da AURA
    const messageContainerId = 'aura-msg-' + Date.now();
    this.currentMessageContainerId = messageContainerId;
    this.createAuraMessageBubble(messageContainerId);

    // Ativa pulso do Cognitive Reasoning Orb no header e define primeira etapa cognitiva
    const headerOrb = typeof document !== 'undefined' ? (document.getElementById('header-neural-core-orb') || document.querySelector('header .neural-core-orb')) : null;
    if (headerOrb) headerOrb.classList.add('reasoning-active');
    this.updateCognitiveStep(messageContainerId, 'Consultando automação da pista...', 'cyan');

    // Força rolagem para o início da nova resposta
    this.scrollToBottom(true);

    // Contexto de streaming
    let fullResponseText = '';
    let currentIntent = null;
    let currentToolResult = null;
    let currentToolName = null;
    let uiCompleteReceived = false;
    let telemetryData = null;
    let hasStreamError = false;

    this.abortController = new AbortController();

    const handleDoneReconciliation = () => {
      if (hasStreamError) return;
      if (!uiCompleteReceived && currentToolResult) {
        // Fallback gracioso: o backend executou a ferramenta mas não emitiu GenUIEnvelope.
        // Remove o slot de esqueleto e renderiza o card legado de ferramenta para não perder os dados.
        this.cleanupSkeletonSlots(messageContainerId);
        this.updateToolResultCard(messageContainerId, currentToolName || 'ferramenta', currentToolResult, true /* force */);
      } else {
        this.cleanupSkeletonSlots(messageContainerId);
      }
      this.updateAuraText(messageContainerId, fullResponseText, false);
      this.finalizeCognitiveStep(messageContainerId, true);
      this.setStreamingState(false);
      this.scrollToBottom(false);
      this.expireStaleWidgets();
    };

    try {
      await window.auraApi.streamChat({
        query: query,
        sessionId: this.sessionId,
        signal: this.abortController.signal,
        onDelta: (token) => {
          if (!fullResponseText && token.trim()) {
            this.updateCognitiveStep(messageContainerId, 'Gerando diagnóstico executivo...', 'purple');
          }
          fullResponseText += token;
          this.updateAuraText(messageContainerId, fullResponseText, true);
        },
        onSkeleton: (skeletonData) => {
          this.handleUISkeleton(messageContainerId, skeletonData);
        },
        onUIDelta: (deltaData) => {
          this.handleUIDelta(messageContainerId, deltaData);
        },
        onUIComplete: (envelopeData) => {
          if (typeof window !== 'undefined' && window.AuraGenUI && typeof window.AuraGenUI.isEnabled === 'function') {
            if (!window.AuraGenUI.isEnabled()) {
              // GenUI desativado no cliente: fallback transparente para DecisionCards legados
              if (currentToolResult) {
                this.updateToolResultCard(messageContainerId, currentToolName || envelopeData.component_name || 'ferramenta', currentToolResult, true);
              }
              return;
            }
          }
          uiCompleteReceived = true;
          this.handleUIComplete(messageContainerId, envelopeData);
        },
        onActionFeedback: (feedbackData) => {
          this.handleUIActionFeedback(messageContainerId, feedbackData);
        },
        onChunk: (chunk) => {
          const type = chunk.chunk_type || chunk.eventType || 'delta';

          if (type === 'intent') {
            currentIntent = chunk.data || { intent: chunk.intent };
            this.updateIntentChip(messageContainerId, currentIntent);

            const intentKey = (currentIntent.intent || currentIntent.name || '').toLowerCase();
            if (intentKey.includes('turno') || intentKey.includes('fechamento')) {
              this.updateCognitiveStep(messageContainerId, 'Confrontando caixas PDV & encerrantes...', 'cyan');
            } else if (intentKey.includes('tanque') || intentKey.includes('run_out') || intentKey.includes('previsao')) {
              this.updateCognitiveStep(messageContainerId, 'Consultando volumetria & autonomia dos tanques...', 'cyan');
            } else if (intentKey.includes('lmc')) {
              this.updateCognitiveStep(messageContainerId, 'Auditando conformidade fiscal Portaria ANP 26...', 'cyan');
            } else if (intentKey.includes('pista') || intentKey.includes('frentista') || intentKey.includes('pump')) {
              this.updateCognitiveStep(messageContainerId, 'Auditando vazão de bicos & frentistas...', 'cyan');
            } else if (intentKey.includes('cesta') || intentKey.includes('conveniencia') || intentKey.includes('combo')) {
              this.updateCognitiveStep(messageContainerId, 'Processando regras de associação da loja...', 'cyan');
            } else if (intentKey.includes('venda') || intentKey.includes('faturamento')) {
              this.updateCognitiveStep(messageContainerId, 'Consultando histórico de vendas & faturamento...', 'cyan');
            } else {
              this.updateCognitiveStep(messageContainerId, 'Processando raciocínio cognitivo...', 'cyan');
            }
          } 
          else if (type === 'tool_start') {
            const toolName = chunk.data?.tool_name || chunk.data?.intent || chunk.tool_name || chunk.intent || 'ferramenta';
            this.updateToolStartStatus(messageContainerId, toolName);
          } 
          else if (type === 'tool_result') {
            const toolName = chunk.data?.tool_name || chunk.data?.intent || chunk.tool_name || chunk.intent || 'ferramenta';
            currentToolName = toolName;
            currentToolResult = chunk.data?.result || chunk.data || {};
            this.updateToolResultCard(messageContainerId, toolName, currentToolResult);
            this.updateCognitiveStep(messageContainerId, 'Confrontando dados e regras de negócio...', 'purple');
          } 
          else if (
            type === 'ui_skeleton' ||
            type === 'ui_delta' ||
            type === 'ui_complete' ||
            type === 'ui_action_feedback' ||
            type === 'ui_action_result'
          ) {
            // Já despachados pelos callbacks dedicados de ciclo de vida (onSkeleton, onUIDelta, onUIComplete, onActionFeedback)
            // Não reprocessa para evitar chamadas duplicadas, jank de layout e duplo registro no Companion Canvas.
            return;
          }
          else if (type === 'delta') {
            if (!fullResponseText && (chunk.text || '').trim()) {
              this.updateCognitiveStep(messageContainerId, 'Gerando diagnóstico executivo...', 'purple');
            }
          } 
          else if (type === 'telemetry') {
            telemetryData = chunk.data || {};
            this.updateTelemetryBadge(messageContainerId, telemetryData);
          }
          else if (type === 'error') {
            hasStreamError = true;
            const errorMsg = chunk.data?.error || chunk.text || 'Erro no processamento da solicitação';
            this.cleanupSkeletonSlots(messageContainerId);
            this.hideToolCardSkeleton(messageContainerId);
            this.renderStreamError(messageContainerId, errorMsg);
            this.finalizeCognitiveStep(messageContainerId, false);
            this.setStreamingState(false);
          }
          else if (type === 'done') {
            if (hasStreamError) return;
            if (chunk.data?.error || chunk.data?.success === false) {
              hasStreamError = true;
              this.cleanupSkeletonSlots(messageContainerId);
              this.finalizeCognitiveStep(messageContainerId, false);
              this.setStreamingState(false);
              return;
            }
            handleDoneReconciliation();
          }
        },
        onDone: () => {
          handleDoneReconciliation();
        },
        onError: (err) => {
          hasStreamError = true;
          this.cleanupSkeletonSlots(messageContainerId);
          if (err && (err.name === 'AbortError' || String(err.message || '').toLowerCase().includes('abort'))) {
            this.finalizeCognitiveStep(messageContainerId, false);
            this.hideToolCardSkeleton(messageContainerId);
          } else {
            console.error('[AuraChat] Erro no stream:', err);
            this.hideToolCardSkeleton(messageContainerId);
            this.renderStreamError(messageContainerId, err.message);
            this.finalizeCognitiveStep(messageContainerId, false);
          }
          this.setStreamingState(false);
        },
      });
    } catch (err) {
      hasStreamError = true;
      this.cleanupSkeletonSlots(messageContainerId);
      if (err && (err.name === 'AbortError' || String(err.message || '').toLowerCase().includes('abort'))) {
        this.finalizeCognitiveStep(messageContainerId, false);
        this.hideToolCardSkeleton(messageContainerId);
      } else {
        console.error('[AuraChat] Erro fatal no chat:', err);
        this.hideToolCardSkeleton(messageContainerId);
        this.renderStreamError(messageContainerId, err.message);
        this.finalizeCognitiveStep(messageContainerId, false);
      }
      this.setStreamingState(false);
    }
  }

  /**
   * F2-03: Injeção de Skeleton UI Reativo (SkeletonPulse) no container da mensagem
   * Aloca no DOM o slot genui-skeleton-slot com identificador genui-skeleton-[tool_call_id],
   * micro-copy contextual da etapa e classes AURA Precision Glass.
   */
  handleUISkeleton(containerId, skeletonData) {
    if (!skeletonData || typeof document === 'undefined') return;

    // Feature Flag F9-01: Se GenUI desativado no cliente, ignora skeleton e faz fallback para cards legados
    if (typeof window !== 'undefined' && window.AuraGenUI && typeof window.AuraGenUI.isEnabled === 'function') {
      if (!window.AuraGenUI.isEnabled()) return;
    }

    const toolCallId = skeletonData.tool_call_id || ('call_' + Date.now());

    // Telemetria SRE (F9-02): Medir inicio da hidratacao (skeleton) com performance.now()
    this._skeletonTimers = this._skeletonTimers || {};
    this._skeletonTimers[toolCallId] = (typeof performance !== 'undefined' && typeof performance.now === 'function')
      ? performance.now()
      : Date.now();

    const componentName = skeletonData.component_name || 'GenericGenUIWidget';
    const rawTitle = skeletonData.title || 'Analisando indicadores executivos...';
    
    // Micro-copy contextual informando a etapa em execução
    const microCopy = rawTitle.toLowerCase().startsWith('aura engine')
      ? rawTitle
      : `AURA Engine: ${rawTitle}`;

    // Atualiza chip cognitivo no header da mensagem
    this.updateCognitiveStep(containerId, rawTitle, 'cyan');

    // Se já existir slot para este toolCallId, não duplica
    const existingSlot = (typeof document.getElementById === 'function')
      ? document.getElementById('genui-skeleton-' + toolCallId)
      : null;
    if (existingSlot) return;

    let toolCard = (typeof document.getElementById === 'function')
      ? document.getElementById(containerId + '-tool-card')
      : null;
    if (!toolCard && typeof document.getElementById === 'function') {
      toolCard = document.getElementById(containerId);
    }
    if (!toolCard) return;

    // Constrói o HTML do SkeletonPulse no padrão AURA Precision Glass
    const skeletonHtml = `
      <div id="genui-skeleton-${this.escapeHtml(toolCallId)}" 
           class="genui-skeleton-slot p-4 rounded-xl border border-cyan-500/20 bg-slate-900/60 backdrop-blur-md animate-fade-in my-2"
           data-tool-call-id="${this.escapeHtml(toolCallId)}"
           data-component="${this.escapeHtml(componentName)}">
        <div class="flex items-center gap-3">
          <div class="w-3 h-3 rounded-full bg-cyan-400 animate-ping flex-shrink-0"></div>
          <span class="text-xs font-mono text-cyan-300 tracking-wide uppercase font-semibold">
            ${this.escapeHtml(microCopy)}
          </span>
        </div>
        <div class="mt-3 space-y-2">
          <div class="h-4 bg-slate-800/80 rounded w-3/4 animate-pulse"></div>
          <div class="h-8 bg-slate-800/60 rounded w-full animate-pulse"></div>
        </div>
      </div>
    `;

    toolCard.innerHTML = skeletonHtml;
    toolCard.classList.remove('hidden');

    const splitCard = (typeof document.getElementById === 'function')
      ? document.getElementById(containerId + '-split-tool-card')
      : null;
    if (splitCard) {
      splitCard.innerHTML = skeletonHtml.replace(`id="genui-skeleton-${toolCallId}"`, `id="genui-skeleton-${toolCallId}-split"`);
      splitCard.classList.remove('hidden');
    }

    this.scrollToBottom();
  }

  /**
   * F2-02: Recepção de fragmento ui_delta com buffer volátil em memória
   */
  handleUIDelta(containerId, deltaData) {
    if (!deltaData || typeof document === 'undefined') return;
    const toolCallId = deltaData.tool_call_id;
    const title = (deltaData.parsed && deltaData.parsed.title) || deltaData.title;
    if (title) {
      let slot = (toolCallId && typeof document.getElementById === 'function')
        ? document.getElementById('genui-skeleton-' + toolCallId)
        : null;
      if (!slot && containerId && typeof document.querySelector === 'function') {
        slot = document.querySelector(`#${containerId} .genui-skeleton-slot, #${containerId}-tool-card .genui-skeleton-slot`);
      }
      if (slot) {
        const titleEl = (typeof slot.querySelector === 'function')
          ? slot.querySelector('span.text-cyan-300')
          : null;
        if (titleEl) {
          titleEl.textContent = `AURA Engine: ${title}`;
        }
      }
      this.updateCognitiveStep(containerId, title, 'cyan');
    }
  }

  /**
   * F2-04: Hidratação Instantânea sem Layout Jank (Zero CLS)
   * Substitui o slot genui-skeleton-[tool_call_id] pelo componente hidratado via
   * SecureComponentRegistry com transição suave de 150ms fade-in.
   */
  handleUIComplete(containerId, envelopeData) {
    if (!envelopeData || typeof document === 'undefined') return;

    // Feature Flag F9-01: Se GenUI desativado no cliente, ignora envelope
    if (typeof window !== 'undefined' && window.AuraGenUI && typeof window.AuraGenUI.isEnabled === 'function') {
      if (!window.AuraGenUI.isEnabled()) return;
    }

    const toolCallId = envelopeData.tool_call_id;

    // Idempotência: Se o card para este toolCallId já foi hidratado no DOM, não remonta
    if (toolCallId && typeof document.getElementById === 'function') {
      const alreadyMounted = document.getElementById('genui-card-' + toolCallId);
      if (alreadyMounted) return;
    }

    // Registra o widget no AuraStateManager para gestao de estado e idempotencia
    const stateMgr = (typeof window !== 'undefined' && window.auraStateManager) ||
                     (typeof globalThis !== 'undefined' && globalThis.auraStateManager) ||
                     null;
    if (stateMgr && toolCallId && typeof stateMgr.registerWidget === 'function') {
      const createdAt = envelopeData.created_at || envelopeData.timestamp || Date.now();
      const ttl = envelopeData.ttl_seconds || 900;
      stateMgr.registerWidget(
        toolCallId,
        Object.assign({ created_at: createdAt, timestamp: createdAt }, envelopeData.props || {}),
        ttl,
        createdAt
      );
    }

    let skeletonSlot = (toolCallId && typeof document.getElementById === 'function')
      ? document.getElementById('genui-skeleton-' + toolCallId)
      : null;
    if (!skeletonSlot && containerId && typeof document.querySelector === 'function') {
      skeletonSlot = document.querySelector(`#${containerId} .genui-skeleton-slot, #${containerId}-tool-card .genui-skeleton-slot`);
    }

    // 1. Resolve o componente no SecureComponentRegistry
    const registry = (typeof window !== 'undefined' && window.SecureComponentRegistry) ||
                     (typeof AuraGenUI !== 'undefined' && AuraGenUI.registry);
    let ComponentDef = null;
    if (registry && typeof registry.resolveComponent === 'function') {
      try {
        ComponentDef = registry.resolveComponent(envelopeData.component_name, { throwOnMissing: false });
      } catch (_) {
        ComponentDef = null;
      }
    }

    let hydratedHtml = '';
    let hydratedNode = null;

    if (ComponentDef) {
      if (typeof ComponentDef === 'function') {
        try {
          const enrichedData = Object.assign({ session_id: this.sessionId }, envelopeData);
          const instance = new ComponentDef(enrichedData);
          if (instance && typeof instance.mount === 'function') {
            const mounted = instance.mount();
            if (typeof HTMLElement !== 'undefined' && mounted instanceof HTMLElement) {
              hydratedNode = mounted;
            } else if (typeof mounted === 'string') {
              hydratedHtml = mounted;
            }
          } else if (typeof HTMLElement !== 'undefined' && instance instanceof HTMLElement) {
            hydratedNode = instance;
          }
        } catch (e) {
          console.warn('[GenUI] Erro ao instanciar componente registrado:', e);
        }
      } else if (typeof ComponentDef.render === 'function') {
        try {
          const rendered = ComponentDef.render(envelopeData);
          if (typeof HTMLElement !== 'undefined' && rendered instanceof HTMLElement) {
            hydratedNode = rendered;
          } else if (typeof rendered === 'string') {
            hydratedHtml = rendered;
          }
        } catch (e) {
          console.warn('[GenUI] Erro ao renderizar componente registrado:', e);
        }
      }
    }

    // 2. Fallback seguro caso nao haja componente registrado no catalogo fechado (OWASP LLM03 - F7-01)
    if (!hydratedNode && !hydratedHtml) {
      if (typeof AuraGenUI !== 'undefined' && typeof AuraGenUI.renderSafeFallback === 'function') {
        hydratedHtml = AuraGenUI.renderSafeFallback(
          envelopeData.component_name || envelopeData.intent,
          envelopeData.props || envelopeData.raw_output || envelopeData.data || envelopeData.executive_summary
        );
      } else {
        const inlineWidget = this.renderToolInlineWidget(
          envelopeData.intent || envelopeData.component_name,
          envelopeData.props || envelopeData.data || envelopeData
        );

        if (inlineWidget) {
          hydratedHtml = `
            <div id="genui-card-${this.escapeHtml(toolCallId || 'default')}" 
                 class="genui-hydrated-card animate-fade-in my-2"
                 data-tool-call-id="${this.escapeHtml(toolCallId || '')}"
                 data-component="${this.escapeHtml(envelopeData.component_name || '')}">
              ${inlineWidget}
            </div>
          `;
        } else {
          hydratedHtml = this.renderCanonicalFallbackCard(envelopeData);
        }
      }
    }

    if (!hydratedNode && hydratedHtml) {
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = hydratedHtml.trim();
      hydratedNode = tempDiv.firstElementChild || tempDiv;
    }

    if (hydratedNode || hydratedHtml) {
      const widgetContentHtml = hydratedHtml || (hydratedNode ? (hydratedNode.outerHTML || '') : '');
      const artifactId = 'art_genui_' + (toolCallId || Date.now());
      const artifactTitle = this.formatToolDisplayName(envelopeData.component_name || envelopeData.intent);
      const artifactSubtitle = envelopeData.executive_summary || 'Resultado estruturado e auditável gerado pela AURA';

      // No Desktop, o widget inline no chat inicia recolhido para não duplicar com o Companion Canvas aberto.
      // No Mobile, inicia expandido para leitura natural no feed sem depender de split canvas.
      const isMobile = this.isMobileDevice();
      const startExpanded = isMobile;

      // 1. Projeta no Companion Canvas se habilitado (abre no Desktop, não abre no mobile)
      if (typeof window !== 'undefined' && window.auraAuxPanel && typeof window.auraAuxPanel.projectArtifact === 'function') {
        try {
          window.auraAuxPanel.projectArtifact({
            id: artifactId,
            containerId: containerId,
            toolName: envelopeData.component_name,
            intent: envelopeData.intent,
            data: envelopeData.props,
            html: widgetContentHtml,
            autoOpen: !isMobile
          });
        } catch (_) {}
      }

      // 2. Renderiza o portal card com banner e contêiner desdobrável / recolhível
      const portalBannerHtml = this.renderCompanionPortalCard({
        artifactId,
        artifactTitle,
        artifactSubtitle,
        containerId,
        widgetHtml: widgetContentHtml,
        startExpanded: startExpanded
      });

      const toolCard = (containerId && typeof document.getElementById === 'function')
        ? (document.getElementById(containerId + '-tool-card') || document.getElementById(containerId))
        : null;

      if (toolCard) {
        toolCard.innerHTML = portalBannerHtml;
        toolCard.classList.remove('hidden');
      } else if (skeletonSlot && skeletonSlot.parentNode) {
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = portalBannerHtml.trim();
        const portalNode = tempDiv.firstElementChild || tempDiv;
        portalNode.classList.add('genui-fade-in');
        skeletonSlot.parentNode.replaceChild(portalNode, skeletonSlot);
      }

      const splitCard = (containerId && typeof document.getElementById === 'function')
        ? document.getElementById(containerId + '-split-tool-card')
        : null;
      if (splitCard) {
        splitCard.innerHTML = portalBannerHtml;
        splitCard.classList.remove('hidden');
      }

      // Telemetria SRE (F9-02): Medir tempo real de hidratacao e reportar assincronamente ao backend
      if (this._skeletonTimers && toolCallId && this._skeletonTimers[toolCallId]) {
        const endTime = (typeof performance !== 'undefined' && typeof performance.now === 'function')
          ? performance.now()
          : Date.now();
        const hydrationMs = Math.max(0, endTime - this._skeletonTimers[toolCallId]);
        delete this._skeletonTimers[toolCallId];

        if (typeof window !== 'undefined' && window.auraApi && typeof window.auraApi.reportTelemetry === 'function') {
          window.auraApi.reportTelemetry({
            hydration_ms: hydrationMs,
            tool_call_id: toolCallId,
            session_id: this.sessionId,
            details: { component_name: envelopeData.component_name }
          }).catch(() => {});
        }
      }

      this.scrollToBottom();
    }
  }

  /**
   * Renderiza card canônico Precision Glass para fallback seguro (F2-04)
   */
  renderCanonicalFallbackCard(envelopeData) {
    const toolCallId = envelopeData.tool_call_id || '';
    const componentName = envelopeData.component_name || 'Componente GenUI';
    const schemaVersion = envelopeData.schema_version || '1.0';
    const summary = envelopeData.executive_summary || '';
    const props = envelopeData.props || {};
    const actions = envelopeData.actions || [];

    const stateMgr = (typeof window !== 'undefined' && window.auraStateManager) ||
                     (typeof globalThis !== 'undefined' && globalThis.auraStateManager) ||
                     null;
    const createdAt = envelopeData.created_at || envelopeData.timestamp || Date.now();
    const ttlSeconds = envelopeData.ttl_seconds || 900;
    const isExpired = stateMgr && typeof stateMgr.isStale === 'function'
      ? stateMgr.isStale(createdAt, ttlSeconds)
      : false;

    const propKeys = Object.keys(props).slice(0, 6);
    const propsHtml = propKeys.map(k => {
      const val = props[k];
      const displayVal = (typeof val === 'object' && val !== null) ? JSON.stringify(val) : String(val);
      return `
        <div class="p-2.5 rounded-lg bg-white/[0.03] border border-white/5 space-y-0.5">
          <div class="text-[10px] font-mono text-slate-400 uppercase tracking-wider">${this.escapeHtml(k)}</div>
          <div class="text-xs font-semibold text-slate-100 truncate" title="${this.escapeHtml(displayVal)}">${this.escapeHtml(displayVal)}</div>
        </div>
      `;
    }).join('');

    const actionsHtml = actions.map(act => {
      const isActionDone = stateMgr && typeof stateMgr.isActionExecuted === 'function' && stateMgr.isActionExecuted(act.action_id);
      const shouldDisable = isActionDone || isExpired;
      const displayLabel = isActionDone ? `✔ ${act.label || 'Ação'}` : (act.label || 'Ação');
      const disabledClass = shouldDisable ? 'opacity-50 pointer-events-none cursor-not-allowed ' : '';

      const variantClass = act.variant === 'danger'
        ? 'bg-rose-500/20 text-rose-300 border-rose-500/40 hover:bg-rose-500/30'
        : act.variant === 'secondary'
        ? 'bg-slate-800 text-slate-200 border-white/10 hover:bg-slate-700'
        : 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40 hover:bg-cyan-500/30';
      return `
        <button type="button" 
                data-action-id="${this.escapeHtml(act.action_id || '')}"
                data-tool-call-id="${this.escapeHtml(toolCallId || '')}"
                class="genui-action-btn px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${variantClass} ${disabledClass}"
                ${shouldDisable ? 'disabled' : ''}>
          ${this.escapeHtml(displayLabel)}
        </button>
      `;
    }).join('');

    const expiredBadgeHtml = isExpired ? `
      <div class="genui-expired-badge p-2 mb-2 rounded-xl bg-slate-950/70 border border-slate-700/60 text-slate-400 text-xs flex items-center justify-between gap-2">
        <span class="text-slate-300">Proposta Expirada (Dados desatualizados)</span>
        <span class="badge-expired text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-700">Expirado</span>
      </div>
    ` : '';

    return `
      <div id="genui-card-${this.escapeHtml(toolCallId || 'default')}" 
           class="genui-hydrated-card p-4 sm:p-5 space-y-3.5 rounded-2xl border border-cyan-500/30 bg-slate-900/80 backdrop-blur-xl animate-fade-in my-2"
           data-tool-call-id="${this.escapeHtml(toolCallId)}"
           data-component="${this.escapeHtml(componentName)}">
        <div class="flex items-center justify-between border-b border-white/10 pb-3">
          <div class="flex items-center gap-2.5">
            <div class="w-2.5 h-2.5 rounded-full bg-emerald-400"></div>
            <span class="text-xs font-mono font-bold text-cyan-300 uppercase tracking-wide">
              ${this.escapeHtml(componentName)}
            </span>
          </div>
          <span class="px-2 py-0.5 rounded text-[10px] font-sans font-semibold bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
            GenUI v${this.escapeHtml(schemaVersion)}
          </span>
        </div>

        ${summary ? `<div class="text-xs text-slate-200 leading-relaxed font-sans">${this.escapeHtml(summary)}</div>` : ''}

        ${propKeys.length > 0 ? `
          <div class="grid grid-cols-2 sm:grid-cols-3 gap-2 pt-1">
            ${propsHtml}
          </div>
        ` : ''}

        ${expiredBadgeHtml}

        ${actions.length > 0 ? `
          <div class="flex flex-wrap items-center gap-2 pt-2 border-t border-white/5">
            ${actionsHtml}
          </div>
        ` : ''}
      </div>
    `;
  }

  /**
   * F4-04: Escaneia o DOM do feed e desativa acoes de widgets cujo TTL foi excedido (> 15 min / 900s)
   */
  expireStaleWidgets() {
    if (typeof document === 'undefined') return;
    const stateMgr = (typeof window !== 'undefined' && window.auraStateManager) ||
                     (typeof globalThis !== 'undefined' && globalThis.auraStateManager) ||
                     null;
    if (!stateMgr || typeof stateMgr.isStale !== 'function') return;

    if (typeof document.querySelectorAll === 'function') {
      const cards = document.querySelectorAll('.genui-hydrated-card[data-tool-call-id]');
      cards.forEach(card => {
        const toolCallId = card.getAttribute('data-tool-call-id');
        const widget = stateMgr.getWidget(toolCallId);
        if (widget && stateMgr.isStale(widget.timestamp, widget.ttlSeconds)) {
          widget.state.status = 'expired';
          const btns = card.querySelectorAll('.genui-action-btn:not([data-action-type="inspection"])');
          btns.forEach(btn => {
            btn.classList.add('opacity-50', 'pointer-events-none', 'cursor-not-allowed');
            btn.setAttribute('disabled', 'true');
          });
          if (!card.querySelector('.genui-expired-badge') && !card.querySelector('.badge-expired')) {
            const targetContainer = card.querySelector('.genui-layer-3') || card.querySelector('.border-t') || card;
            if (targetContainer) {
              const badge = document.createElement('div');
              badge.className = 'genui-expired-badge p-2.5 mb-2.5 rounded-xl bg-slate-950/70 border border-slate-700/60 text-slate-400 text-xs flex items-center justify-between gap-2';
              badge.innerHTML = '<div class="flex items-center gap-2"><span class="w-2 h-2 rounded-full bg-slate-500"></span><span class="font-medium text-slate-300">Proposta Expirada (Dados de telemetria desatualizados)</span></div><span class="badge-expired text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-700">Expirado</span>';
              targetContainer.insertBefore(badge, targetContainer.firstChild);
            }
          }
        }
      });
    }
  }

  /**
   * F2-04: Remove graciosamente slots de esqueleto orfaos em caso de erro, done ou fallback
   * Garante que nenhuma caixa vazia permaneca no DOM se ui_complete nao for emitido.
   */
  cleanupSkeletonSlots(containerId = null) {
    if (typeof document === 'undefined') return;

    const selector = containerId
      ? `#${containerId} .genui-skeleton-slot, #${containerId}-tool-card .genui-skeleton-slot`
      : '.genui-skeleton-slot';

    if (typeof document.querySelectorAll === 'function') {
      const skeletons = document.querySelectorAll(selector);
      skeletons.forEach(skel => {
        const parent = skel.parentNode;
        skel.remove();
        if (parent && parent.children && parent.children.length === 0 && parent.classList) {
          parent.classList.add('hidden');
        }
      });
    }

    if (containerId && typeof document.getElementById === 'function') {
      const toolCard = document.getElementById(containerId + '-tool-card');
      if (toolCard && (!toolCard.firstElementChild || (typeof toolCard.querySelector === 'function' && toolCard.querySelector('.genui-skeleton-slot')))) {
        toolCard.innerHTML = '';
        if (toolCard.classList) toolCard.classList.add('hidden');
      }
      const splitCard = document.getElementById(containerId + '-split-tool-card');
      if (splitCard && (!splitCard.firstElementChild || (typeof splitCard.querySelector === 'function' && splitCard.querySelector('.genui-skeleton-slot')))) {
        splitCard.innerHTML = '';
        if (splitCard.classList) splitCard.classList.add('hidden');
      }
    }
  }

  /**
   * Processa eventos de confirmacao / voucher de acoes transacionais (ui_action_feedback)
   */
  handleUIActionFeedback(containerId, feedbackData) {
    if (!feedbackData || typeof document === 'undefined') return;
    const actionId = feedbackData.action_id;
    const status = feedbackData.status;
    const voucherId = feedbackData.voucher_id;

    const stateMgr = (typeof window !== 'undefined' && window.auraStateManager) ||
                     (typeof globalThis !== 'undefined' && globalThis.auraStateManager) ||
                     null;

    if (actionId && typeof document.querySelector === 'function') {
      const btn = document.querySelector(`button[data-action-id="${actionId}"]`);
      if (btn) {
        if (status === 'COMMITTED') {
          btn.disabled = true;
          btn.className = 'px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 opacity-90 cursor-default';
          btn.innerHTML = `✔ Confirmado (${this.escapeHtml(voucherId || 'Voucher emitido')})`;
        } else if (status === 'FAILED') {
          btn.disabled = false;
          btn.className = 'px-3 py-1.5 rounded-lg text-xs font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/40 hover:bg-rose-500/30';
          btn.innerHTML = `✖ Falha ao executar (Tentar Novamente)`;
        }
      }

      if (stateMgr) {
        if (status === 'COMMITTED') {
          stateMgr.markActionExecuted(actionId, feedbackData);
          const toolCallId = feedbackData.tool_call_id || (btn ? btn.getAttribute('data-tool-call-id') : null);
          if (toolCallId) {
            stateMgr.finalizeSuccessState(toolCallId, feedbackData);
          }
        } else if (status === 'FAILED') {
          const toolCallId = feedbackData.tool_call_id || (btn ? btn.getAttribute('data-tool-call-id') : null);
          if (toolCallId) {
            stateMgr.rollbackOptimisticState(toolCallId);
          }
          if (typeof window !== 'undefined' && window.auraApi && typeof window.auraApi.reportTelemetry === 'function') {
            window.auraApi.reportTelemetry({
              is_rollback: true,
              action_status: 'rolled_back',
              action_id: actionId,
              tool_call_id: toolCallId,
              session_id: this.sessionId,
            }).catch(() => {});
          }
        }
      }
    }
  }

  hideToolCardSkeleton(containerId) {
    this.cleanupSkeletonSlots(containerId);
    const cardIds = [containerId + '-tool-card', containerId + '-split-tool-card'];
    cardIds.forEach(id => {
      const cardEl = typeof document !== 'undefined' ? document.getElementById(id) : null;
      if (cardEl && cardEl.querySelector('.skeleton-glass')) {
        cardEl.innerHTML = '';
        cardEl.classList.add('hidden');
      }
    });
  }

  abortStreaming() {
    if (this.currentMessageContainerId) {
      this.finalizeCognitiveStep(this.currentMessageContainerId, false);
      this.cleanupSkeletonSlots(this.currentMessageContainerId);
      this.hideToolCardSkeleton(this.currentMessageContainerId);
    }
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
    this.setStreamingState(false);
  }

  clearSession() {
    this.abortStreaming();
    this.cleanupSkeletonSlots();
    this.userScrolledUp = false;
    const scrollBtn = document.getElementById('btn-scroll-bottom');
    if (scrollBtn) scrollBtn.classList.add('hidden');
    const input = document.getElementById('chat-input-text');
    if (input) {
      input.value = '';
      input.style.height = 'auto';
    }
    this.sessionId = this.generateSessionId();
    this.renderSessionId();
    const feed = document.getElementById('chat-feed-container');
    if (feed) feed.innerHTML = '';
    if (typeof window !== 'undefined' && window.auraAuxPanel && typeof window.auraAuxPanel.clearArtifacts === 'function') {
      try { window.auraAuxPanel.clearArtifacts(); } catch (_) {}
    }
    this.addWelcomeMessage();
  }

  setStreamingState(isStreaming) {
    this.isStreaming = isStreaming;
    if (!isStreaming) {
      this.isSubmitting = false;
    }
    const sendBtn = document.getElementById('btn-chat-send');
    const stopBtn = document.getElementById('btn-chat-stop');
    const input = document.getElementById('chat-input-text');

    if (sendBtn && stopBtn) {
      if (isStreaming) {
        sendBtn.classList.add('hidden');
        stopBtn.classList.remove('hidden');
      } else {
        sendBtn.classList.remove('hidden');
        stopBtn.classList.add('hidden');
      }
    }

    if (input) {
      input.disabled = isStreaming;
      if (!isStreaming && typeof window !== 'undefined' && window.innerWidth >= 768 && typeof input.focus === 'function') {
        input.focus({ preventScroll: true });
      }
    }

    // Gerencia estado visual do Cognitive Reasoning Orb no header e nas bolhas
    if (!isStreaming && typeof document !== 'undefined') {
      const headerOrb = document.getElementById('header-neural-core-orb') || document.querySelector('header .neural-core-orb');
      if (headerOrb) headerOrb.classList.remove('reasoning-active');
      document.querySelectorAll('.chat-bubble-aura .neural-core-orb.reasoning-active').forEach(orb => {
        orb.classList.remove('reasoning-active');
      });
    }
  }

  appendUserMessage(text) {
    const feed = document.getElementById('chat-feed-container');
    if (!feed) return;

    const div = document.createElement('div');
    div.className = 'flex justify-end w-full animate-fade-in';
    div.innerHTML = `
      <div class="chat-bubble-user max-w-[85%] md:max-w-[70%] lg:max-w-[65%] ml-auto p-4 text-slate-100 text-sm">
        <div class="flex items-center justify-between text-[11px] font-sans font-medium text-slate-400 mb-1.5 pb-1 border-b border-white/5">
          <span class="font-bold text-cyan-400 flex items-center gap-1.5">
            <span class="w-1.5 h-1.5 rounded-full bg-cyan-400"></span>
            <span>OPERADOR</span>
          </span>
          <span class="text-slate-400 tabular-nums">${new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</span>
        </div>
        <div class="leading-relaxed whitespace-pre-wrap">${this.escapeHtml(text)}</div>
      </div>
    `;
    feed.appendChild(div);
    this.scrollToBottom();
  }

  createAuraMessageBubble(containerId) {
    const feed = document.getElementById('chat-feed-container');
    if (!feed) return null;

    const div = document.createElement('div');
    div.id = containerId;
    div.className = 'flex justify-start w-full animate-fade-in';
    div.innerHTML = `
      <div class="chat-bubble-aura w-full max-w-full p-4 sm:p-5 text-slate-100 text-sm space-y-3">
        <!-- Header da Resposta com Núcleo e Tags -->
        <div class="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 pb-2">
          <div class="flex items-center gap-2">
            <div id="${containerId}-orb" class="neural-core-orb !w-6 !h-6 reasoning-active text-[10px] font-bold text-white flex items-center justify-center">
              <span class="relative z-10">A</span>
            </div>
            <span class="font-bold font-sans text-xs text-white">AURA</span>
            <span class="px-1.5 py-0.5 rounded text-[9px] font-sans font-semibold bg-purple-500/10 text-purple-300 border border-purple-500/20">AI</span>
          </div>

          <div id="${containerId}-meta" class="flex flex-wrap items-center gap-1.5 font-sans text-[10px]">
            <span id="${containerId}-cognitive-chip" class="chip-cognitive-step px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 flex items-center gap-1.5 transition-all">
              <span class="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping"></span>
              <span class="cognitive-step-label">Consultando automação da pista...</span>
            </span>
            <span id="${containerId}-intent-chip" class="hidden chip-intent"></span>
            <span id="${containerId}-tool-chip" class="hidden chip-tool-status"></span>
          </div>
        </div>

        <!-- Card de Resultado da Ferramenta Estruturada (se houver) -->
        <div id="${containerId}-tool-card" class="hidden w-full"></div>

        <!-- Texto em Streaming -->
        <div id="${containerId}-text" class="prose-aura typing-cursor">
          <span class="text-slate-400 text-xs font-sans">Processando consulta analítica...</span>
        </div>

        <!-- Métricas e Confirmação da Resposta -->
        <div id="${containerId}-telemetry" class="hidden pt-2 border-t border-slate-800/80 text-[10px] font-sans text-slate-400">
        </div>
      </div>
    `;
    feed.appendChild(div);

    this.scrollToBottom();
    return document.getElementById(containerId);
  }

  appendAuraMessage(htmlContent, opts = {}) {
    const feed = document.getElementById('chat-feed-container');
    if (!feed) return;

    const div = document.createElement('div');
    if (opts.isWelcome) {
      div.id = 'welcome-message-bubble';
      div.className = 'flex justify-start w-full h-full min-h-full flex-1 animate-fade-in welcome-message-wrapper';
    } else {
      div.className = 'flex justify-start w-full animate-fade-in';
    }
    div.innerHTML = `
      <div class="chat-bubble-aura ${opts.isWelcome ? 'chat-bubble-welcome w-full max-w-full h-full min-h-full flex-1 flex flex-col justify-between p-4 sm:p-5 text-slate-100 text-sm space-y-3' : 'w-full max-w-full p-4 sm:p-5 text-slate-100 text-sm space-y-3'}">
        <div class="flex items-center justify-between border-b border-white/10 pb-2 ${opts.isWelcome ? 'flex-shrink-0' : ''}">
          <div class="flex items-center gap-2">
            <div class="neural-core-orb !w-6 !h-6 text-[10px] font-bold text-white flex items-center justify-center shadow-sm">
              <span class="relative z-10">A</span>
            </div>
            <span class="font-bold font-sans text-xs text-white">AURA</span>
            <span class="px-1.5 py-0.5 rounded text-[9px] font-sans font-semibold bg-purple-500/10 text-purple-300 border border-purple-500/20">AI</span>
          </div>
          ${opts.isWelcome ? '<span class="px-2 py-0.5 rounded-full text-[10px] font-sans font-medium bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">Pronta para Atendimento</span>' : ''}
        </div>
        <div class="${opts.isWelcome ? 'welcome-content-body w-full flex flex-col justify-between flex-1' : 'w-full'}">${htmlContent}</div>
      </div>
    `;
    feed.appendChild(div);

    this.scrollToBottom();
  }

  updateIntentChip(containerId, intentData) {
    const ids = [containerId + '-intent-chip', containerId + '-split-intent-chip'];
    const name = intentData.intent || intentData.name || 'desconhecido';
    const conf = intentData.confidence ? ` ${(intentData.confidence * 100).toFixed(0)}%` : '';

    ids.forEach(id => {
      const chip = document.getElementById(id);
      if (chip) {
        chip.innerHTML = `${CHAT_ICONS.target} ${name}${conf}`;
        chip.classList.remove('hidden');
      }
    });
  }

  formatToolDisplayName(toolName) {
    const map = {
      'previsao_tanques': 'Tanques & Autonomia',
      'run_out': 'Tanques & Autonomia',
      'lmc_anp': 'LMC ANP Oficial',
      'auditoria_turno': 'Conciliação de Turno & Caixa',
      'conciliacao_turno': 'Conciliação de Turno & Caixa',
      'conveniencia_vendas_cruzadas': 'Combos & Cross-Selling',
      'desempenho_pista_frentistas': 'Performance da Pista',
      'catalogo_produtos': 'Catálogo de Produtos',
      'vendas_analitico': 'Histórico de Vendas',
      'estoque_posicao': 'Posição de Estoque',
      'clientes_ranking': 'Ranking de Clientes',
      'dados_filial': 'Dados da Filial',
      'sre_metricas': 'Diagnóstico Operacional',
      'ajuda_sistema': 'Guia & Auto-Conhecimento',
      'conhecimento_aura': 'Guia & Auto-Conhecimento',
    };
    return map[toolName] || toolName;
  }

  /**
   * Renderiza um card de skeleton dinâmico simulando a estrutura do futuro DecisionCard
   * com brilho de vidro translúcido suave (.skeleton-glass) enquanto a IA calcula os dados.
   */
  renderDecisionCardSkeleton(toolName) {
    const displayName = this.formatToolDisplayName(toolName);
    return `
      <div class="decision-card skeleton-glass p-4 sm:p-5 space-y-4 rounded-2xl border border-white/10 backdrop-blur-xl animate-fade-in my-2">
        <!-- Topo do Card de Decisão: Título & Badge de Status -->
        <div class="flex items-center justify-between border-b border-white/10 pb-3">
          <div class="flex items-center gap-2.5">
            <div class="w-8 h-8 rounded-xl skeleton-shimmer flex items-center justify-center text-cyan-400">
              <span class="animate-pulse text-sm inline-flex">${CHAT_ICONS.pulse}</span>
            </div>
            <div>
              <div class="skeleton-shimmer h-4 w-40 mb-1.5"></div>
              <div class="text-[11px] text-cyan-400/80 font-sans flex items-center gap-1.5">
                <span class="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse"></span>
                <span>Calculando ${this.escapeHtml(displayName)}...</span>
              </div>
            </div>
          </div>
          <div class="skeleton-shimmer h-6 w-24 rounded-full"></div>
        </div>

        <!-- Hero Metric em Destaque -->
        <div class="p-3.5 rounded-xl bg-white/[0.02] border border-white/5 flex items-center justify-between">
          <div class="space-y-1.5">
            <div class="skeleton-shimmer h-3 w-28"></div>
            <div class="skeleton-shimmer h-7 w-36"></div>
          </div>
          <div class="skeleton-shimmer h-8 w-20 rounded-lg"></div>
        </div>

        <!-- Grade de Métricas Simulada -->
        <div class="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
          <div class="p-2.5 rounded-lg bg-white/[0.02] border border-white/5 space-y-1">
            <div class="skeleton-shimmer h-3 w-16"></div>
            <div class="skeleton-shimmer h-4 w-24"></div>
          </div>
          <div class="p-2.5 rounded-lg bg-white/[0.02] border border-white/5 space-y-1">
            <div class="skeleton-shimmer h-3 w-20"></div>
            <div class="skeleton-shimmer h-4 w-20"></div>
          </div>
          <div class="p-2.5 rounded-lg bg-white/[0.02] border border-white/5 space-y-1 col-span-2 sm:col-span-1">
            <div class="skeleton-shimmer h-3 w-14"></div>
            <div class="skeleton-shimmer h-4 w-28"></div>
          </div>
        </div>

        <!-- Rodapé do Card: Ações e Evidências -->
        <div class="flex items-center justify-between pt-2 border-t border-white/5">
          <div class="skeleton-shimmer h-7 w-28 rounded-lg"></div>
          <div class="skeleton-shimmer h-7 w-32 rounded-lg"></div>
        </div>
      </div>
    `;
  }

  updateCognitiveStep(containerId, stepLabel, mode = 'cyan') {
    const ids = [containerId + '-cognitive-chip', containerId + '-split-cognitive-chip'];
    ids.forEach(id => {
      const chip = typeof document !== 'undefined' ? document.getElementById(id) : null;
      if (chip) {
        const colorClass = mode === 'purple' 
          ? 'bg-purple-500/10 text-purple-300 border-purple-500/30'
          : mode === 'emerald'
          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
          : 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30';
        const pingClass = mode === 'purple' ? 'bg-purple-400' : mode === 'emerald' ? 'bg-emerald-400' : 'bg-cyan-400';

        chip.className = `chip-cognitive-step px-2 py-0.5 rounded-full ${colorClass} border flex items-center gap-1.5 transition-all`;
        chip.innerHTML = `
          <span class="w-1.5 h-1.5 rounded-full ${pingClass} ${mode === 'emerald' ? '' : 'animate-ping'}"></span>
          <span class="cognitive-step-label">${this.escapeHtml(stepLabel)}</span>
        `;
        chip.classList.remove('hidden');
      }
    });
  }

  finalizeCognitiveStep(containerId, success = true) {
    const ids = [containerId + '-cognitive-chip', containerId + '-split-cognitive-chip'];
    ids.forEach(id => {
      const chip = typeof document !== 'undefined' ? document.getElementById(id) : null;
      if (chip) {
        if (success) {
          chip.className = 'chip-cognitive-step px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1.5 transition-all';
          chip.innerHTML = `
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            <span class="cognitive-step-label">Diagnóstico executivo concluído</span>
          `;
        } else {
          chip.className = 'chip-cognitive-step px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 flex items-center gap-1.5 transition-all';
          chip.innerHTML = `
            <span class="w-1.5 h-1.5 rounded-full bg-rose-400"></span>
            <span class="cognitive-step-label">Processamento interrompido</span>
          `;
        }
      }
    });
  }

  updateToolStartStatus(containerId, toolName) {
    const ids = [containerId + '-tool-chip', containerId + '-split-tool-chip'];
    const cardIds = [containerId + '-tool-card', containerId + '-split-tool-card'];
    const displayName = this.formatToolDisplayName(toolName);

    ids.forEach(id => {
      const chip = typeof document !== 'undefined' ? document.getElementById(id) : null;
      if (chip) {
        chip.innerHTML = `${CHAT_ICONS.pulse} Consultando ${this.escapeHtml(displayName)}...`;
        chip.classList.remove('hidden');
      }
    });

    this.updateCognitiveStep(containerId, `Consultando telemetria de ${displayName}...`, 'cyan');

    // Renderiza card de skeleton dinâmico simulando a estrutura do DecisionCard
    const skeletonHtml = this.renderDecisionCardSkeleton(toolName);
    cardIds.forEach(id => {
      const cardEl = typeof document !== 'undefined' ? document.getElementById(id) : null;
      if (cardEl) {
        cardEl.innerHTML = skeletonHtml;
        cardEl.classList.remove('hidden');
      }
    });
  }

  updateToolResultCard(containerId, toolName, resultData, force = false) {
    const cardIds = [containerId + '-tool-card', containerId + '-split-tool-card'];
    const chipIds = [containerId + '-tool-chip', containerId + '-split-tool-chip'];
    const displayName = this.formatToolDisplayName(toolName);
    const isUnavail = this.isSourceUnavailable(resultData);

    chipIds.forEach(id => {
      const chip = document.getElementById(id);
      if (chip) {
        if (isUnavail) {
          chip.innerHTML = `${CHAT_ICONS.alert} ${this.escapeHtml(displayName)} indisponível`;
          chip.className = 'chip-intent text-rose-300 border-rose-500/30 bg-rose-500/10';
        } else {
          chip.innerHTML = `${CHAT_ICONS.check} ${this.escapeHtml(displayName)} apurado`;
          chip.className = 'chip-intent text-emerald-300 border-emerald-500/30 bg-emerald-500/10';
        }
      }
    });

    // Se houver um slot de GenUI Skeleton ativo e não for renderização forçada de fallback,
    // preserva o skeleton pulsando até ui_complete!
    if (!force) {
      const activeGenUISkeleton = (typeof document !== 'undefined') && (
        (typeof document.querySelector === 'function' && (
          document.querySelector('#' + containerId + ' .genui-skeleton-slot') ||
          document.querySelector('#' + containerId + '-tool-card .genui-skeleton-slot')
        )) ||
        (typeof document.getElementById === 'function' && document.getElementById('genui-skeleton-' + (resultData?.tool_call_id || '')))
      );
      if (activeGenUISkeleton) {
        return;
      }
    }

    const widgetHtml = this.renderToolInlineWidget(toolName, resultData);

    if (widgetHtml) {
      let artifactId = 'art_' + Date.now() + '_' + Math.random().toString(36).substring(2, 6);
      let artifactTitle = this.formatToolDisplayName(toolName);
      let artifactSubtitle = 'Resultado estruturado e auditável gerado pela AURA';

      if (typeof window !== 'undefined' && window.auraAuxPanel && typeof window.auraAuxPanel.projectArtifact === 'function') {
        try {
          const art = window.auraAuxPanel.projectArtifact({
            id: artifactId,
            containerId: containerId,
            toolName: toolName,
            intent: resultData?.contrato?.intent || resultData?.intent,
            data: resultData,
            html: widgetHtml,
            autoOpen: true
          });
          if (art && art.id) {
            artifactId = art.id;
            if (art.title) artifactTitle = art.title;
            if (art.subtitle) artifactSubtitle = art.subtitle;
          }
        } catch (_) {}
      }

      const portalBannerHtml = this.renderCompanionPortalCard({
        artifactId,
        artifactTitle,
        artifactSubtitle,
        containerId,
        widgetHtml
      });

      cardIds.forEach(id => {
        const cardEl = document.getElementById(id);
        if (cardEl) {
          cardEl.innerHTML = portalBannerHtml;
          cardEl.classList.remove('hidden');
        }
      });
      this.scrollToBottom();
    } else {
      cardIds.forEach(id => {
        const cardEl = document.getElementById(id);
        if (cardEl) {
          cardEl.innerHTML = '';
          cardEl.classList.add('hidden');
        }
      });
    }
  }

  /**
   * Reconhecimento inteligente de tela (Mobile <768px vs PC >=768px)
   */
  isMobileDevice(win = (typeof window !== 'undefined' ? window : null)) {
    if (!win) return false;
    // 1. Override manual do HUD de dispositivo (prioridade máxima para comutação e testes)
    if (win.auraFx && typeof win.auraFx.override === 'string') {
      if (win.auraFx.override === 'mobile') return true;
      if (win.auraFx.override === 'desktop') return false;
    }
    // 2. Viewport width padrão da janela informada (< 768px Mobile, >= 768px Desktop/PC)
    if (typeof win.innerWidth === 'number') {
      return win.innerWidth < 768;
    }
    // 3. Media query reativa
    if (win.matchMedia && typeof win.matchMedia === 'function') {
      return win.matchMedia('(max-width: 767px)').matches;
    }
    // 4. Atributo data-device no DOM (fallback se innerWidth não estiver disponível)
    if (typeof document !== 'undefined' && document.documentElement) {
      const dev = document.documentElement.getAttribute('data-device');
      if (dev === 'mobile') return true;
      if (dev === 'desktop') return false;
    }
    // 5. Fallback para helpers de dispositivo
    if (win.auraFx && typeof win.auraFx.isMobileDevice === 'function') {
      return win.auraFx.isMobileDevice();
    }
    if (win.auraFx && typeof win.auraFx.isMobile === 'function') {
      return win.auraFx.isMobile();
    }
    return false;
  }

  isDesktopDevice(win = (typeof window !== 'undefined' ? window : null)) {
    return !this.isMobileDevice(win);
  }

  /**
   * Renderiza o Card Portal do AURA Companion Canvas acoplado ao chat
   * Regra Inteligente:
   * - Mobile (<768px): Exibe SOMENTE "Ver no Chat ▾" (card desdobra inline no chat)
   * - PC / Desktop (>=768px): Exibe SOMENTE "Ver no Painel" (destaca o canvas lateral)
   */
  renderCompanionPortalCard({ artifactId, artifactTitle, artifactSubtitle, containerId, widgetHtml, startExpanded = false }) {
    const isHiddenClass = startExpanded ? '' : 'hidden';
    const labelText = startExpanded ? 'Esconder Widget ▴' : 'Ver no Chat ▾';
    const ariaExpanded = startExpanded ? 'true' : 'false';

    return `
      <div class="aux-companion-portal-banner aux-artifact-portal-card mb-3 p-3.5 rounded-2xl bg-slate-900/90 border border-cyan-500/30 flex flex-col gap-2.5 shadow-lg backdrop-blur-md">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
          <div class="flex items-center gap-3 min-w-0">
            <div class="w-8 h-8 rounded-xl bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-400 flex-shrink-0 shadow-inner">
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <rect x="2" y="3" width="20" height="18" rx="2.5" stroke-width="1.75"/>
                <line x1="13" y1="3" x2="13" y2="21" stroke-width="1.75"/>
                <circle cx="7.5" cy="12" r="2" fill="currentColor"/>
              </svg>
            </div>
            <div class="min-w-0">
              <div class="text-xs font-bold text-white flex items-center gap-1.5 truncate font-sans">
                <span>${this.escapeHtml(artifactTitle)}</span>
                <span class="px-1.5 py-0.2 rounded text-[9px] font-sans font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">Canvas</span>
              </div>
              <p class="text-[11px] text-slate-400 font-sans truncate">${this.escapeHtml(artifactSubtitle)}</p>
            </div>
          </div>

          <!-- Ações Inteligentes: Alternar no Chat e Ver no Painel (PC >=768px) -->
          <div class="flex items-center gap-2 self-end sm:self-auto flex-shrink-0 font-sans">
            <!-- Mobile: Somente Ver/Esconder no Chat inline -->
            <button type="button" onclick="window.auraChat && window.auraChat.toggleInlineArtifact('${containerId}')" id="${containerId}-btn-toggle-inline" aria-expanded="${ariaExpanded}" aria-controls="${containerId}-inline-widget" class="aux-btn-view-chat inline-flex md:hidden px-2.5 py-1.5 min-h-[36px] rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white border border-white/10 text-xs font-medium transition-all items-center gap-1 active:scale-95 cursor-pointer" title="Alternar visualização deste card no chat">
              <span id="${containerId}-btn-toggle-label">${labelText}</span>
            </button>
            <!-- PC / Desktop: Botão de alternar/esconder no Chat para total controle sem duplicar tela -->
            <button type="button" onclick="window.auraChat && window.auraChat.toggleInlineArtifact('${containerId}')" id="${containerId}-btn-toggle-pc" aria-expanded="${ariaExpanded}" aria-controls="${containerId}-inline-widget" class="aux-btn-toggle-pc hidden md:inline-flex px-2.5 py-1.5 min-h-[36px] rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white border border-white/10 text-xs font-medium transition-all items-center gap-1 active:scale-95 cursor-pointer" title="Mostrar ou esconder este card no feed de mensagens">
              <span id="${containerId}-btn-toggle-pc-label">${labelText}</span>
            </button>
            <!-- PC / Desktop: Somente Ver no Painel lateral -->
            <button type="button" onclick="window.auraAuxPanel && window.auraAuxPanel.open('${artifactId}')" id="${containerId}-btn-open-panel" class="aux-btn-view-panel hidden md:inline-flex px-3 py-1.5 min-h-[36px] rounded-xl bg-gradient-to-r from-cyan-500/20 to-purple-500/20 hover:from-cyan-500/30 hover:to-purple-500/30 text-cyan-200 hover:text-white border border-cyan-500/40 text-xs font-semibold items-center gap-1.5 transition-all active:scale-95 shadow-sm cursor-pointer" title="Abrir no Painel Auxiliar">
              <span>Ver no Painel</span>
              <svg class="w-3.5 h-3.5 text-cyan-400" viewBox="0 0 24 24" fill="none" stroke="currentColor"><polyline points="9 18 15 12 9 6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </button>
          </div>
        </div>

        <!-- Contêiner do Widget Inline Desdobrável (fica recolhido para não poluir o feed quando o painel auxiliar estiver ativo) -->
        <div id="${containerId}-inline-widget" class="${isHiddenClass} pt-2 border-t border-white/10 animate-fade-in space-y-2">
          ${widgetHtml}
          <!-- Barra rápida para esconder o widget no chat -->
          <div class="flex justify-end pt-1">
            <button type="button" 
                    onclick="window.auraChat && window.auraChat.toggleInlineArtifact('${containerId}')" 
                    class="text-[11px] text-slate-400 hover:text-cyan-300 transition-colors flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-800/60 hover:bg-slate-800 border border-white/10 cursor-pointer"
                    title="Recolher visualização deste card no chat">
              <span>Esconder este widget ▴</span>
            </button>
          </div>
        </div>
      </div>
    `;
  }

  toggleInlineArtifact(containerId) {
    if (typeof document === 'undefined') return;
    const widgetEl = document.getElementById(containerId + '-inline-widget');
    const labelEl = document.getElementById(containerId + '-btn-toggle-label');
    const labelPcEl = document.getElementById(containerId + '-btn-toggle-pc-label');
    const toggleBtn = document.getElementById(containerId + '-btn-toggle-inline');
    const togglePcBtn = document.getElementById(containerId + '-btn-toggle-pc');
    if (!widgetEl) return;

    const isHidden = widgetEl.classList.contains('hidden');
    if (isHidden) {
      widgetEl.classList.remove('hidden');
      if (labelEl) labelEl.textContent = 'Esconder Widget ▴';
      if (labelPcEl) labelPcEl.textContent = 'Esconder Widget ▴';
      if (toggleBtn) {
        toggleBtn.setAttribute('aria-expanded', 'true');
        toggleBtn.classList.add('bg-white/15', 'text-white', 'border-white/20');
      }
      if (togglePcBtn) {
        togglePcBtn.setAttribute('aria-expanded', 'true');
        togglePcBtn.classList.add('bg-white/15', 'text-white', 'border-white/20');
      }
      if (typeof this.scrollToBottom === 'function') {
        setTimeout(() => this.scrollToBottom(), 50);
      }
    } else {
      widgetEl.classList.add('hidden');
      if (labelEl) labelEl.textContent = 'Ver no Chat ▾';
      if (labelPcEl) labelPcEl.textContent = 'Ver no Chat ▾';
      if (toggleBtn) {
        toggleBtn.setAttribute('aria-expanded', 'false');
        toggleBtn.classList.remove('bg-white/15', 'text-white', 'border-white/20');
      }
      if (togglePcBtn) {
        togglePcBtn.setAttribute('aria-expanded', 'false');
        togglePcBtn.classList.remove('bg-white/15', 'text-white', 'border-white/20');
      }
    }
  }

  /**
   * F5-01: Roteador Centralizado de Renderização de Respostas Especializadas
   * Despacha para renderizadores canônicos registrados por intent ou toolName.
   */
  renderToolInlineWidget(toolName, data) {
    if (!data || typeof data !== 'object') return '';

    // 1. Despacho Canônico por Intent Estruturado do Contrato (F5-01)
    const intent = data.contrato?.intent || data.intent;
    if (intent && this.responseRenderers && typeof this.responseRenderers[intent] === 'function') {
      return this.responseRenderers[intent](data);
    }

    // 2. Despacho por toolName registrado
    if (toolName && this.responseRenderers && typeof this.responseRenderers[toolName] === 'function') {
      return this.responseRenderers[toolName](data);
    }

    // 3. Roteamento por Assinatura Estrutural dos Dados (Fallback Seguro)
    if (
      data.ui_action ||
      (Array.isArray(data.artigos) && data.artigos.length > 0 && data.artigos[0]?.modulo)
    ) {
      return this.renderAjudaSistemaWidget(data);
    }
    if (
      data.resumo_executivo?.status_geral_anp ||
      data.assessment?.status_code === 'CONFORME_ANP' ||
      data.assessment?.status_code === 'ALERTA_VARIACAO_EXCESSIVA' ||
      Array.isArray(data.demonstrativo_por_combustivel) ||
      (Array.isArray(data.tanques) && data.tanques[0]?.auditoria_anp) ||
      (Array.isArray(data.tanques) && data.tanques[0]?.status_anp)
    ) {
      return this.renderLmcAnpWidget(data);
    }
    if (
      data.triangulacao_pista ||
      data.triangulacao_caixa ||
      data.triangulacao_volumes ||
      data.fechamento_caixa
    ) {
      return this.renderTurnoWidget(data);
    }
    if (
      Array.isArray(data.top_combos_cross_selling) ||
      Array.isArray(data.top_combos_oportunidades) ||
      Array.isArray(data.regras_associacao_detalhadas) ||
      Array.isArray(data.top_combos)
    ) {
      return this.renderCombosWidget(data);
    }
    if (
      Array.isArray(data.ranking_frentistas) ||
      Array.isArray(data.auditoria_vazao_bicos) ||
      Array.isArray(data.ranking) ||
      Array.isArray(data.nozzles)
    ) {
      return this.renderDesempenhoPistaWidget(data);
    }
    if (
      Array.isArray(data.detalhamento_tanques) ||
      data.previsao_por_combustivel ||
      Array.isArray(data.tanks) ||
      Array.isArray(data.tanques)
    ) {
      return this.renderTankAutonomyWidget(data);
    }
    if (
      data.ultimo_produto_vendido_destaque ||
      data.produtos_mais_vendidos ||
      data.resumo_hoje ||
      Array.isArray(data.ultimos_produtos_conveniencia) ||
      Array.isArray(data.ultimos_abastecimentos_pista)
    ) {
      return this.renderVendasAnaliticoWidget(data);
    }

    // 4. Fallback genérico executivo
    return this.renderGenericToolWidget(toolName, data);
  }

  /**
   * Avalia com precisão se a fonte de dados (ERP/Banco/Automação) está offline, em timeout ou inacessível.
   */
  isSourceUnavailable(data, assessment = null) {
    if (!data || typeof data !== 'object') return false;
    const c = data.contrato || data;
    const a = assessment || c.assessment || {};
    return Boolean(
      a.finality === 'unavailable' ||
      a.status_code === 'INDISPONIVEL' ||
      a.status_code === 'FONTE_INDISPONIVEL' ||
      data.status === 'indisponivel' ||
      data.status === 'unavailable' ||
      data.status === 'timeout' ||
      data.status === 'error' ||
      data.status === 'erro' ||
      data.status_code === 'INDISPONIVEL' ||
      data.status_code === 'FONTE_INDISPONIVEL' ||
      data.error ||
      c.error
    );
  }

  /**
   * F6-06 / F1-08: Card de Contingência Executiva para Fontes Indisponíveis / Timeout / Erro
   * Apresenta diagnóstico semântico honesto, limitação explícita e ação de contingência manual/reiteração.
   */
  renderContingencyCard(moduleName, data, retryPrompt = null) {
    const c = data?.contrato || data;
    const motivo = data?.motivo || data?.mensagem || data?.error || c?.error || data?.context?.error || c?.assessment?.limitation || 'Acesso à fonte de dados (ERP/Banco/Automação) temporariamente indisponível.';
    const evId = 'ev_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7);
    if (typeof window !== 'undefined') {
      if (!window.__auraEvidenceStore) window.__auraEvidenceStore = {};
      window.__auraEvidenceStore[evId] = data;
    }

    const defaultPrompts = {
      'Conciliação de Turno & Caixa': 'Qual a conciliação do turno de hoje?',
      'Autonomia de Tanques & Run-Out': 'Qual a previsão de esgotamento e a autonomia estimada dos tanques?',
      'Performance da Pista & Frentistas': 'Qual o desempenho da pista e vazão de bicos hoje?',
      'Conciliação Físico-Contábil do LMC ANP': 'O LMC de ontem fechou dentro da tolerância oficial da ANP?',
      'Combos & Vendas Cruzadas na Conveniência': 'Quais os combos de conveniência com maior afinidade?',
    };
    const promptToRetry = retryPrompt || defaultPrompts[moduleName] || 'Repetir a consulta anterior';
    const escapedPrompt = this.escapeHtml(String(promptToRetry).replace(/'/g, "\\'"));

    return `
      <div class="decision-card decision-contingency-card" data-evidence-id="${evId}">
        <div class="decision-header">
          <div class="decision-context">
            <span class="decision-context-title">${this.escapeHtml(moduleName)}</span>
            <span class="decision-context-sub">
              <span>${CHAT_ICONS.alert} Análise Suspensa</span>
              <span>•</span>
              <span>${CHAT_ICONS.unit} ${this.escapeHtml(c?.context?.unit_id || 'Posto')}</span>
            </span>
          </div>
          <span class="decision-status-badge status-divergent">
            <span>${CHAT_ICONS.alert}</span>
            <span>${this.escapeHtml(c?.assessment?.badge_label || 'Fonte Indisponível')}</span>
          </span>
        </div>

        <div class="decision-hero">
          <div class="decision-hero-header">
            <span class="decision-hero-label">Status da Conexão</span>
            <span class="px-2 py-0.5 rounded text-[10px] font-sans font-semibold bg-rose-500/15 text-rose-300 border border-rose-500/30">Indisponibilidade Temporária</span>
          </div>
          <div class="decision-hero-value text-slate-400">
            -
          </div>
          <div class="decision-hero-sub text-rose-300/90">
            Não foi possível calcular indicadores oficiais. Fonte primária não respondeu dentro do tempo limite.
          </div>
        </div>

        <div class="decision-limitation-callout border-rose-500/30 bg-rose-950/20 text-rose-200/90">
          <span class="inline-flex text-rose-400">${CHAT_ICONS.alert}</span>
          <div>
            <strong class="font-semibold text-rose-300">Contingência Operacional:</strong>
            <span class="text-rose-200/90">${this.escapeHtml(motivo)}</span>
          </div>
        </div>

        <div class="decision-actions">
          <button 
            type="button" 
            class="decision-btn-primary" 
            onclick="if (window.auraChat) window.auraChat.sendUserPrompt('${escapedPrompt}');"
            title="Tentar executar a consulta novamente">
            <span>${CHAT_ICONS.refresh}</span>
            <span>Tentar Novamente</span>
          </button>

          <button 
            type="button" 
            class="decision-btn-secondary" 
            onclick="if (window.auraChat) window.auraChat.sendUserPrompt('Como verificar a integridade da conexão do ERP e banco local?');"
            title="Verificar status e procedimento manual de contingência">
            <span>${CHAT_ICONS.wrench}</span>
            <span>Procedimento de Contingência</span>
          </button>
        </div>
      </div>
    `;
  }

  /**
   * F1-08 / F5-01: Card de Fallback Seguro para Versão Desconhecida de Schema
   * Não inventa interpretação financeira ou operacional quando o schema não for suportado.
   */
  renderUnsupportedSchemaCard(version, moduleName) {
    return `
      <div class="decision-card">
        <div class="decision-header">
          <div class="decision-context">
            <span class="decision-context-title">Versão de Contrato Não Suportada (v${this.escapeHtml(version)})</span>
            <span class="decision-context-sub">Contrato AURA Precision Glass v1.0 esperado • ${this.escapeHtml(moduleName)}</span>
          </div>
          <span class="decision-status-badge status-neutral">
            <span>${CHAT_ICONS.alert}</span>
            <span>Schema Desconhecido</span>
          </span>
        </div>
        <div class="p-3.5 rounded-xl bg-slate-900/80 border border-amber-500/30 text-amber-200/90 font-sans text-xs space-y-1.5">
          <div class="flex items-center gap-1.5"><span class="inline-flex text-amber-400">${CHAT_ICONS.alert}</span> <strong>Aviso de Conformidade e Governança:</strong></div>
          <p class="text-[11px] text-slate-300">
            A estrutura de dados analíticos recebida para <strong>${this.escapeHtml(moduleName)}</strong> utiliza a versão <code>${this.escapeHtml(version)}</code>, incompatível com o renderizador atual. A exibição executiva foi suspensa para evitar inferências incorretas.
          </p>
        </div>
      </div>
    `;
  }

  /**
   * Widget de Auto-Conhecimento e Atalho Interativo da UI
   */
  renderAjudaSistemaWidget(data) {
    if (!data || typeof data !== 'object') return '';
    const action = data.ui_action || (data.artigos && data.artigos[0]?.ui_action) || null;
    const artigos = data.artigos || [];
    const topArtigo = artigos.length > 0 ? artigos[0] : null;
    const modulo = topArtigo?.modulo ? topArtigo.modulo.toUpperCase() : 'SISTEMA';
    const titulo = topArtigo?.titulo || 'Auto-Conhecimento da AURA';
    const subtitulo = topArtigo?.subtitulo || 'Guia de operação e atalhos rápidos da plataforma.';

    let actionButtonHtml = '';
    if (action) {
      const label = action.label || 'Acessar Funcionalidade';
      if (action.action === 'switch_tab' && action.target) {
        actionButtonHtml = `
          <button 
            type="button"
            onclick="if (window.auraAudio) window.auraAudio.playChime(650, 0.05); if (window.auraApp) window.auraApp.switchTab('${this.escapeHtml(action.target)}');" 
            class="group inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-gradient-to-r from-cyan-500/25 to-purple-600/25 hover:from-cyan-500/40 hover:to-purple-600/40 border border-cyan-400/40 hover:border-cyan-300 text-cyan-200 hover:text-white font-semibold text-xs transition-all shadow-md active:scale-95 cursor-pointer">
            <span class="inline-flex">${CHAT_ICONS.rocket}</span>
            <span>${this.escapeHtml(label)}</span>
            <svg class="w-3.5 h-3.5 text-cyan-300 group-hover:translate-x-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/>
            </svg>
          </button>
        `;
      } else if (action.action === 'open_sidebar') {
        actionButtonHtml = `
          <button 
            type="button"
            onclick="if (window.auraApp) window.auraApp.openSidebar();" 
            class="group inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-gradient-to-r from-cyan-500/25 to-purple-600/25 hover:from-cyan-500/40 hover:to-purple-600/40 border border-cyan-400/40 hover:border-cyan-300 text-cyan-200 hover:text-white font-semibold text-xs transition-all shadow-md active:scale-95 cursor-pointer">
            <span class="inline-flex">${CHAT_ICONS.folder}</span>
            <span>${this.escapeHtml(label)}</span>
          </button>
        `;
      } else if (action.action === 'open_command_palette') {
        actionButtonHtml = `
          <button 
            type="button"
            onclick="const btn = document.getElementById('btn-open-palette'); if (btn) btn.click();" 
            class="group inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-gradient-to-r from-cyan-500/25 to-purple-600/25 hover:from-cyan-500/40 hover:to-purple-600/40 border border-cyan-400/40 hover:border-cyan-300 text-cyan-200 hover:text-white font-semibold text-xs transition-all shadow-md active:scale-95 cursor-pointer">
            <span class="inline-flex">${CHAT_ICONS.terminal}</span>
            <span>${this.escapeHtml(label)}</span>
          </button>
        `;
      } else if (action.action === 'toggle_audio') {
        actionButtonHtml = `
          <button 
            type="button"
            onclick="const btn = document.getElementById('sidebar-btn-toggle-sfx') || document.getElementById('btn-toggle-sfx'); if (btn) { btn.click(); } else if (window.auraAudio) { const m = window.auraAudio.toggleMute(); if (window.auraApp) window.auraApp.syncSfxButtons(m); }" 
            class="group inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-gradient-to-r from-cyan-500/25 to-purple-600/25 hover:from-cyan-500/40 hover:to-purple-600/40 border border-cyan-400/40 hover:border-cyan-300 text-cyan-200 hover:text-white font-semibold text-xs transition-all shadow-md active:scale-95 cursor-pointer">
            <span class="inline-flex">${CHAT_ICONS.volume}</span>
            <span>${this.escapeHtml(label)}</span>
          </button>
        `;
      } else {
        actionButtonHtml = `
          <button 
            type="button"
            onclick="if (window.auraApp) window.auraApp.switchTab('cockpit');" 
            class="group inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-gradient-to-r from-cyan-500/25 to-purple-600/25 hover:from-cyan-500/40 hover:to-purple-600/40 border border-cyan-400/40 hover:border-cyan-300 text-cyan-200 hover:text-white font-semibold text-xs transition-all shadow-md active:scale-95 cursor-pointer">
            <span class="inline-flex">${CHAT_ICONS.pulse}</span>
            <span>${this.escapeHtml(label)}</span>
          </button>
        `;
      }
    }

    let relatedHtml = '';
    if (artigos.length > 1) {
      const relBadges = artigos.slice(1, 3).map(art => {
        const mod = art.modulo ? art.modulo.toUpperCase() : 'GUIA';
        const tit = art.titulo || art.topico;
        return `<span class="px-2 py-0.5 rounded-lg bg-slate-800/80 text-cyan-300/90 text-[10px] font-sans font-medium border border-slate-700/60 inline-flex items-center gap-1">${CHAT_ICONS.target} [${this.escapeHtml(mod)}] ${this.escapeHtml(tit)}</span>`;
      }).join(' ');
      relatedHtml = `
        <div class="pt-2 border-t border-cyan-500/10 flex flex-wrap items-center gap-1.5">
          <span class="text-[10px] text-slate-400">Tópicos complementares:</span>
          ${relBadges}
        </div>
      `;
    }

    return `
      <div class="rounded-2xl border border-cyan-500/30 bg-slate-900/90 backdrop-blur-md p-4 text-slate-100 shadow-lg space-y-3 animate-fade-in">
        <div class="flex items-center justify-between border-b border-cyan-500/20 pb-2.5">
          <div class="flex items-center gap-2.5">
            <div class="w-8 h-8 rounded-xl bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center text-cyan-300 shadow-inner">
              <span class="inline-flex">${CHAT_ICONS.bulb}</span>
            </div>
            <div>
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded text-[10px] font-sans font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 uppercase tracking-wider">${this.escapeHtml(modulo)}</span>
                <span class="text-white font-bold text-xs">${this.escapeHtml(titulo)}</span>
              </div>
              <p class="text-[11px] text-slate-400 leading-snug mt-0.5">${this.escapeHtml(subtitulo)}</p>
            </div>
          </div>
        </div>

        ${actionButtonHtml ? `
        <div class="pt-1 flex items-center justify-between gap-3">
          <span class="text-[11px] text-slate-400">Atalho de ação rápida no sistema:</span>
          ${actionButtonHtml}
        </div>
        ` : ''}

        ${relatedHtml}
      </div>
    `;
  }

  /**
   * Widget 1: Card de Decisão Executiva para Autonomia de Tanques & Previsão de Run-Out
   * Implementação AURA Precision Glass v1.0 (F5-03 & F5-04).
   * Garante:
   * 1. Superfície única DecisionCard sem aninhamentos desnecessários.
   * 2. Distinção explícita entre autonomia até reserva crítica (15%) e esgotamento total (0%) (F5-04).
   * 3. Barras volumétricas com código de cores semântico e espaço livre (Ullage em carretas de 5k).
   * 4. Limitações de histórico e consumo médio explícitas (F5-02).
   * 5. Ação recomendada em 1 clique e gatilho de evidências detalhadas.
   */
  renderTankAutonomyWidget(data) {
    if (!data || typeof data !== 'object') {
      return `<div class="decision-card"><p class="text-xs text-slate-400">Dados de autonomia de tanques indisponíveis.</p></div>`;
    }

    const c = data.contrato || data;

    // F1-08 / F5-01: Versão desconhecida de contrato tratada com segurança
    if (c.schema_version && c.schema_version !== '1.0') {
      return this.renderUnsupportedSchemaCard(c.schema_version, 'Autonomia de Tanques');
    }

    const assessment = c.assessment || {};
    const metrics = c.metrics || {};
    const pendingItems = c.pending_items || [];
    const action = c.recommended_action || {};
    const resumo = data.resumo_executivo || {};
    const tanksList = c.tanks || data.detalhamento_tanques || data.tanques || [];

    const isUnavailable = this.isSourceUnavailable(data, assessment);
    const isNoMovement = !isUnavailable && (assessment.status_code === 'SEM_MOVIMENTACAO' || assessment.status_code === 'SEM_REGISTROS' || data.status === 'sem_movimento' || (!data.error && tanksList.length === 0));

    if (isUnavailable) {
      return this.renderContingencyCard('Autonomia de Tanques & Run-Out', data, 'Qual a previsão de esgotamento e a autonomia estimada dos tanques?');
    }

    const evId = 'ev_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7);
    if (typeof window !== 'undefined') {
      if (!window.__auraEvidenceStore) window.__auraEvidenceStore = {};
      window.__auraEvidenceStore[evId] = data;
    }

    // Status Badges Semânticos com Ícone (F5-09)
    let badgeClass = 'status-validated';
    let badgeIcon = CHAT_ICONS.check;
    let badgeText = assessment.badge_label || 'Estoque Estável';
    const severity = assessment.severity || (resumo.status_geral?.includes('CRITICO') ? 'critical' : (resumo.status_geral?.includes('ATENCAO') ? 'attention' : 'normal'));

    if (isUnavailable) {
      badgeClass = 'status-divergent';
      badgeIcon = CHAT_ICONS.alert;
      badgeText = 'Fonte Indisponível';
    } else if (isNoMovement) {
      badgeClass = 'status-neutral';
      badgeIcon = CHAT_ICONS.pause;
      badgeText = assessment.badge_label || 'Sem Registros';
    } else if (severity === 'critical') {
      badgeClass = 'status-divergent';
      badgeIcon = CHAT_ICONS.alert;
      badgeText = assessment.badge_label || 'Estoque Crítico (< 12h)';
    } else if (severity === 'attention') {
      badgeClass = 'status-partial';
      badgeIcon = CHAT_ICONS.alert;
      badgeText = assessment.badge_label || 'Atenção Estoque';
    } else {
      badgeClass = 'status-validated';
      badgeIcon = CHAT_ICONS.check;
      badgeText = assessment.badge_label || 'Estoque Confortável';
    }

    // Métrica Hero: Menor Autonomia até Reserva 15% (distinguindo esgotamento 0% - F5-04)
    const menorAutonomiaReserva = assessment.horizonte_critico_horas ?? metrics.autonomia_critica_horas ?? metrics.menor_autonomia_runout_horas ?? assessment.menor_autonomia_horas ?? resumo.tanque_mais_critico?.autonomia_critica_horas;
    const menorAutonomiaEsgot = assessment.horizonte_runout_horas ?? metrics.autonomia_runout_horas ?? metrics.menor_autonomia_esgotamento_horas ?? assessment.menor_autonomia_esgotamento_horas ?? resumo.tanque_mais_critico?.autonomia_runout_horas;
    const codCritico = assessment.tanque_mais_critico_cod ?? resumo.tanque_mais_critico?.codtan ?? resumo.tanque_mais_critico?.tanque ?? (tanksList.length > 0 ? (tanksList[0]?.codtan || tanksList[0]?.tanque) : 'N/D');

    let heroValFormatted = '-';
    let heroColorClass = 'text-emerald';
    if (isUnavailable || tanksList.length === 0 || isNoMovement) {
      heroValFormatted = '-';
      heroColorClass = 'text-slate-400';
    } else if (menorAutonomiaReserva !== null && menorAutonomiaReserva !== undefined && !isNaN(Number(menorAutonomiaReserva))) {
      const hVal = Number(menorAutonomiaReserva);
      heroValFormatted = `${hVal.toFixed(1)}h`;
      if (hVal < 12) heroColorClass = 'text-rose';
      else if (hVal < 24) heroColorClass = 'text-amber';
      else heroColorClass = 'text-emerald';
    }

    const heroLabel = 'Menor Autonomia de Pista';
    let heroSub = 'Tempo estimado até atingir a reserva crítica de segurança (15%).';
    if (isUnavailable) {
      heroSub = 'Telemetria de tanques e volumetria temporariamente indisponíveis no concentrador/ERP.';
    } else if (tanksList.length === 0 || isNoMovement) {
      heroSub = 'Nenhum tanque localizado para os critérios informados.';
    } else if (menorAutonomiaEsgot !== null && menorAutonomiaEsgot !== undefined && !isNaN(Number(menorAutonomiaEsgot))) {
      heroSub = `Tanque ${codCritico} • Reserva técnica (15%) em ${heroValFormatted} • Esgotamento total (0%) em ${Number(menorAutonomiaEsgot).toFixed(1)}h.`;
    }

    // Comparativo Compacto (Volume Total, Capacidade Total, Ullage Total)
    const volTotal = Number(metrics.saldo_total_litros ?? metrics.volume_total_estoque_litros ?? resumo.volume_total_estoque_litros ?? 0);
    const capTotal = Number(metrics.capacidade_total_litros ?? resumo.capacidade_total_litros ?? 0);
    const ullageTotal = Number(metrics.espaco_livre_ullage_total_litros ?? metrics.espaco_livre_total_ullage_litros ?? resumo.espaco_livre_total_ullage_litros ?? 0);
    const carretas5k = metrics.compartimentos_5k_total ?? metrics.carretas_capacidade_5k_sugeridas ?? resumo.carretas_capacidade_5k_sugeridas ?? Math.floor(ullageTotal / 5000);
    const pctGlobal = metrics.ocupacao_geral_pct !== undefined ? Number(metrics.ocupacao_geral_pct).toFixed(1) : (capTotal > 0 ? ((volTotal / capTotal) * 100).toFixed(1) : '0.0');

    // Bloco de Limitação (F5-02 / F6-01)
    let limitationHtml = '';
    const limText = assessment.limitation || resumo.limitation;
    if (isUnavailable) {
      limitationHtml = `
        <div class="decision-limitation-callout border-rose-500/30 bg-rose-950/20 text-rose-200/90">
          <span class="inline-flex text-rose-400">${CHAT_ICONS.alert}</span>
          <div>
            <strong class="font-semibold text-rose-300">Contingência Operacional:</strong>
            <span class="text-rose-200/90">${this.escapeHtml(limText || data.motivo || 'Telemetria de tanques temporariamente indisponível no concentrador/ERP.')}</span>
          </div>
        </div>
      `;
    } else if (limText && !isNoMovement) {
      limitationHtml = `
        <div class="decision-limitation-callout">
          <span class="inline-flex text-amber-400">${CHAT_ICONS.alert}</span>
          <div>
            <strong class="font-semibold">Premissa e Limitação:</strong>
            <span class="text-amber-200/90">${this.escapeHtml(limText)}</span>
          </div>
        </div>
      `;
    }

    // Barras Volumétricas por Tanque com Ullage e Ação Rápida
    let tanksBarsHtml = '';
    tanksList.forEach(t => {
      const cod = t.codtan || t.tanque || '00';
      const comb = t.combustivel || 'Combustível';
      const pct = Math.min(100, Math.max(0, parseFloat(t.ocupacao_pct ?? t.ocupacao_percentual ?? 0)));
      const vol = parseFloat(t.saldo_atual_litros ?? t.volume_atual_litros ?? 0).toLocaleString('pt-BR', { maximumFractionDigits: 0 });
      const cap = parseFloat(t.capacidade_litros ?? 0).toLocaleString('pt-BR', { maximumFractionDigits: 0 });

      const hReserva = t.autonomia_critica_horas ?? t.autonomia_reserva_horas ?? t.autonomia_horas;
      const hEsgot = t.autonomia_runout_horas ?? t.autonomia_esgotamento_horas;
      const hReservaStr = (hReserva !== null && hReserva !== undefined && !isNaN(hReserva)) ? `${parseFloat(hReserva).toFixed(1)}h até 15%` : 'N/A';
      const hEsgotStr = (hEsgot !== null && hEsgot !== undefined && !isNaN(hEsgot)) ? ` | ${parseFloat(hEsgot).toFixed(1)}h até 0%` : '';

      const ullageL = parseFloat(t.espaco_livre_ullage_litros ?? t.espaco_livre_descarga_litros ?? 0).toLocaleString('pt-BR', { maximumFractionDigits: 0 });
      const carretasTq = t.compartimentos_5k ?? t.sugestao_carreta_5k ?? Math.floor((t.espaco_livre_ullage_litros || 0) / 5000);

      let fillClass = 'normal';
      let statusIcon = '<span class="w-2 h-2 rounded-full bg-emerald-400 inline-block"></span>';
      const statusOp = String(t.status_operacional || '').toUpperCase();
      if (pct < 15 || statusOp.includes('CRÍTICO') || (hReserva !== null && hReserva < 12)) {
        fillClass = 'critical';
        statusIcon = '<span class="w-2 h-2 rounded-full bg-rose-400 inline-block animate-pulse"></span>';
      } else if (pct < 30 || statusOp.includes('ATENÇÃO') || (hReserva !== null && hReserva < 24)) {
        fillClass = 'warning';
        statusIcon = '<span class="w-2 h-2 rounded-full bg-amber-400 inline-block"></span>';
      }

      tanksBarsHtml += `
        <div class="p-3 rounded-xl glass-subcard border border-white/5 space-y-2 font-sans text-xs transition-all duration-200">
          <div class="flex items-center justify-between">
            <span class="font-medium text-slate-100 flex items-center gap-1.5">
              <span>${statusIcon}</span>
              <span class="px-1.5 py-0.5 rounded bg-white/5 border border-white/10 text-slate-300 font-semibold">TQ ${this.escapeHtml(cod)}</span>
              <span class="text-slate-200 font-semibold">${this.escapeHtml(comb)}</span>
            </span>
            <span class="text-slate-200 font-bold tabular-nums">${pct.toFixed(1)}% <span class="text-slate-400 font-normal text-[11px]">(${vol} / ${cap} L)</span></span>
          </div>

          <div class="widget-tank-track" style="margin: 4px 0;">
            <div class="widget-tank-fill ${fillClass}" style="width: ${pct}%"></div>
          </div>

          <div class="flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-400">
            <div class="flex items-center gap-1.5 flex-wrap">
              <span class="text-cyan-300 font-semibold tabular-nums">${CHAT_ICONS.calendar}${hReservaStr}${hEsgotStr}</span>
              <span class="text-slate-600">•</span>
              <span class="text-slate-300 tabular-nums">${CHAT_ICONS.tank}Ullage: <strong class="text-cyan-300 font-semibold">${ullageL} L</strong> (${carretasTq}x 5k)</span>
            </div>
            <button type="button" class="widget-action-btn emerald flex items-center gap-1" onclick="if (window.auraChat) window.auraChat.sendUserPrompt('Qual a melhor sugestão de pedido de carreta para o Tanque ${cod}?');">
              ${CHAT_ICONS.truck}<span>Pedir Carreta</span>
            </button>
          </div>
        </div>
      `;
    });

    // Bloco de Pendências (F5-02)
    let pendingHtml = '';
    if (pendingItems.length > 0) {
      const itemsList = pendingItems.map(p => `
        <div class="decision-pending-item cursor-pointer hover:bg-amber-500/10 transition-colors" onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'tanques');" title="Ver detalhes nas evidências">
          <div class="flex items-center gap-2">
            <span class="text-amber-400 font-bold">${CHAT_ICONS.alert}</span>
            <span class="font-semibold text-slate-200">${this.escapeHtml(p.label)}</span>
          </div>
          <span class="text-[10px] text-slate-400 font-sans flex items-center gap-1">
            <span>Tanque</span>
            <span>↗</span>
          </span>
        </div>
      `).join('');

      pendingHtml = `
        <div class="space-y-1.5">
          <span class="text-[10px] font-sans uppercase tracking-wider text-slate-400 font-semibold">Alertas de Reposição:</span>
          <div class="decision-pending-list">${itemsList}</div>
        </div>
      `;
    }

    const recLabel = action.label || `Pedir Carreta para TQ ${codCritico}`;
    const dataConsulta = c.context?.queried_at ? new Date(c.context.queried_at).toLocaleDateString('pt-BR') : 'Data Recente';

    return `
      <div class="decision-card" data-evidence-id="${evId}">
        <!-- Context Header -->
        <div class="decision-header">
          <div class="decision-context">
            <span class="decision-context-title">${this.escapeHtml(assessment.title || 'Autonomia de Tanques & Previsão de Run-Out')}</span>
            <span class="decision-context-sub">
              <span>${CHAT_ICONS.calendar} ${this.escapeHtml(dataConsulta)}</span>
              <span>•</span>
              <span>${CHAT_ICONS.tank} ${tanksList.length} Tanques Monitorados</span>
              <span>•</span>
              <span>${CHAT_ICONS.unit} ${this.escapeHtml(c.context?.unit_id || 'Posto')}</span>
            </span>
          </div>
          <span class="decision-status-badge ${badgeClass}">
            <span>${badgeIcon}</span>
            <span>${this.escapeHtml(badgeText)}</span>
          </span>
        </div>

        <!-- Hero Metric -->
        <div class="decision-hero">
          <div class="decision-hero-header">
            <span class="decision-hero-label">${this.escapeHtml(heroLabel)}</span>
            <span class="px-2 py-0.5 rounded text-[10px] font-sans font-semibold bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">Tanque ${codCritico}</span>
          </div>
          <div class="decision-hero-value ${heroColorClass}">
            ${heroValFormatted}
          </div>
          <div class="decision-hero-sub">
            ${this.escapeHtml(heroSub)}
          </div>
        </div>

        ${limitationHtml}

        <!-- Comparativo Compacto -->
        ${(!isNoMovement && !isUnavailable) ? `
          <div class="decision-comparison-grid">
            <div class="decision-comp-item">
              <span class="decision-comp-label">Volume Total</span>
              <strong class="decision-comp-val text-cyan-300 tabular-nums">${this.formatLiters(volTotal, 0)}</strong>
              <span class="decision-comp-sub tabular-nums">${pctGlobal}% ocupação global</span>
            </div>
            <div class="decision-comp-item">
              <span class="decision-comp-label">Capacidade Nominal</span>
              <strong class="decision-comp-val text-slate-100 tabular-nums">${this.formatLiters(capTotal, 0)}</strong>
              <span class="decision-comp-sub">${tanksList.length} tanques físicos</span>
            </div>
            <div class="decision-comp-item">
              <span class="decision-comp-label">Ullage Livre</span>
              <strong class="decision-comp-val text-amber-300 tabular-nums">${this.formatLiters(ullageTotal, 0)}</strong>
              <span class="decision-comp-sub tabular-nums">Até ${carretas5k} carretas de 5k L</span>
            </div>
          </div>
        ` : ''}

        <!-- Barras de Tanques -->
        <div class="space-y-2 mt-1">
          ${isUnavailable ? '<div class="p-3 rounded-xl bg-slate-900/60 border border-rose-500/20 text-rose-300 text-xs font-sans">Leitura individual dos tanques suspensa por indisponibilidade da fonte.</div>' : (tanksBarsHtml || '<div class="text-xs font-sans text-slate-400">Nenhum tanque retornado.</div>')}
        </div>

        ${pendingHtml}

        <!-- Ações Permitidas -->
        <div class="decision-actions">
          ${isUnavailable ? `
            <button 
              type="button" 
              class="decision-btn-primary" 
              onclick="if (window.auraChat) window.auraChat.sendUserPrompt('Qual a previsão de esgotamento e a autonomia estimada dos tanques?');"
              title="Tentar executar a consulta novamente">
              <span>${CHAT_ICONS.refresh}</span>
              <span>Tentar Novamente</span>
            </button>
            <button 
              type="button" 
              class="decision-btn-secondary" 
              onclick="if (window.auraChat) window.auraChat.sendUserPrompt('Como auditar estoque de combustível sem telemetria eletrônica?');"
              title="Procedimento de contingência">
              <span>${CHAT_ICONS.wrench}</span>
              <span>Procedimento de Contingência</span>
            </button>
          ` : `
            <button 
              type="button" 
              class="decision-btn-primary" 
              onclick="if (window.auraChat) window.auraChat.sendUserPrompt('Qual a melhor sugestão de pedido de carreta para o Tanque ${codCritico}?');"
              title="Sugerir compra imediata com base no Ullage">
              ${CHAT_ICONS.truck}
              <span>${this.escapeHtml(recLabel)}</span>
            </button>

            <button 
              type="button" 
              class="decision-btn-secondary" 
              onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'formula');"
              title="Ver fórmulas matemáticas de consumo médio e run-out">
              ${CHAT_ICONS.formula}
              <span>Como foi calculado</span>
            </button>

            <button 
              type="button" 
              class="decision-btn-secondary" 
              onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'tanques');"
              title="Ver detalhamento completo dos tanques">
              ${CHAT_ICONS.tank}
              <span>Ver Tanques & Detalhes</span>
            </button>

            <button 
              type="button" 
              class="decision-btn-secondary" 
              onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'resumo');"
              title="Ver fontes de telemetria e diagnóstico">
              ${CHAT_ICONS.audit}
              <span>Resumo & Fontes</span>
            </button>
          `}
        </div>
      </div>
    `;
  }

  /**
   * Widget 2: Card de Decisão Executiva para Conciliação Físico-Contábil do LMC ANP
   * Implementação AURA Precision Glass v1.0 (F5-06 & F5-07).
   * Garante:
   * 1. Superfície única DecisionCard sem aninhamentos desnecessários.
   * 2. Régua visual regulatória [-0.6% a +0.6%] com marcação de safezone e agulha precisa.
   * 3. Alternativa textual acessível para leitores de tela e reflow (F5-09).
   * 4. Comparativo entre Escriturado e Físico Medido com desvios em Litros e %.
   * 5. Limitações legais e de calibragem transparentes.
   */
  renderLmcAnpWidget(data) {
    if (!data || typeof data !== 'object') {
      return `<div class="decision-card"><p class="text-xs text-slate-400">Dados do LMC ANP indisponíveis.</p></div>`;
    }

    const c = data.contrato || data;

    // F1-08 / F5-01: Versão desconhecida de contrato tratada com segurança
    if (c.schema_version && c.schema_version !== '1.0') {
      return this.renderUnsupportedSchemaCard(c.schema_version, 'LMC ANP Oficial');
    }

    const assessment = c.assessment || {};
    const metrics = c.metrics || {};
    const pendingItems = c.pending_items || [];
    const action = c.recommended_action || {};
    const resumo = data.resumo_executivo || {};
    const items = c.tanks || data.demonstrativo_por_combustivel || data.tanques || [];
    const isUnavailable = this.isSourceUnavailable(data, assessment);
    const isNoMovement = !isUnavailable && (assessment.status_code === 'SEM_MOVIMENTACAO' || data.status === 'sem_movimento');

    if (isUnavailable) {
      return this.renderContingencyCard('Conciliação Físico-Contábil do LMC ANP', data, 'O LMC de ontem fechou dentro da tolerância oficial da ANP?');
    }

    const evId = 'ev_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7);
    if (typeof window !== 'undefined') {
      if (!window.__auraEvidenceStore) window.__auraEvidenceStore = {};
      window.__auraEvidenceStore[evId] = data;
    }

    // Status Geral ANP
    const statusGeral = assessment.status_code || resumo.status_geral_anp || 'CONFORME_ANP';
    const isConforme = statusGeral === 'CONFORME_ANP' || statusGeral === 'CONFORME';

    let badgeClass = isConforme ? 'status-validated' : 'status-divergent';
    let badgeIcon = isConforme ? CHAT_ICONS.check : CHAT_ICONS.alert;
    let badgeText = assessment.badge_label || (isConforme ? 'CONFORME ANP (±0.6%)' : 'FORA DA TOLERÂNCIA ANP');

    if (isUnavailable) {
      badgeClass = 'status-divergent';
      badgeIcon = CHAT_ICONS.alert;
      badgeText = 'Fonte Indisponível';
    } else if (isNoMovement) {
      badgeClass = 'status-neutral';
      badgeIcon = CHAT_ICONS.pause;
      badgeText = 'Sem Movimentação';
    }

    // Determina o desvio de maior magnitude para a régua regulatória [-1.2% a +1.2%]
    let maxVarPct = metrics.variacao_volumetrica_geral_pct !== undefined ? Number(metrics.variacao_volumetrica_geral_pct) : (metrics.maior_desvio_pct !== undefined ? Number(metrics.maior_desvio_pct) : (resumo.variacao_volumetrica_geral_pct !== undefined ? parseFloat(resumo.variacao_volumetrica_geral_pct) : 0));
    if (items.length > 0) {
      items.forEach(item => {
        const vPct = parseFloat(item.variacao_pct ?? item.auditoria_anp?.variacao_pct ?? item.variacao_percentual ?? 0);
        if (Math.abs(vPct) > Math.abs(maxVarPct)) {
          maxVarPct = vPct;
        }
      });
    }

    // Escala [-1.2% a +1.2%] na régua (25% a 75% = ±0.6% tolerância da Portaria ANP 26)
    const minScale = -1.2;
    const maxScale = 1.2;
    const clampedPct = Math.max(minScale, Math.min(maxScale, maxVarPct));
    let needleLeft = ((clampedPct - minScale) / (maxScale - minScale)) * 100;
    needleLeft = Math.max(4, Math.min(96, needleLeft));

    const dentroTolerancia = Math.abs(maxVarPct) <= 0.60;
    const needleColor = dentroTolerancia ? '#10b981' : '#f43f5e';
    const needleText = `${maxVarPct > 0 ? '+' : ''}${maxVarPct.toFixed(2)}%`;

    // Métrica Hero: Maior Desvio Volumétrico ANP
    const heroLabel = 'Maior Desvio Volumétrico ANP';
    const heroVal = isNoMovement || isUnavailable ? '-' : needleText;
    const heroColorClass = isNoMovement || isUnavailable ? 'text-slate-400' : (dentroTolerancia ? 'text-emerald' : 'text-rose');
    const tanquesConformes = metrics.total_tanques_conformes ?? metrics.tanques_conformes_count ?? items.filter(it => Math.abs(parseFloat(it.variacao_pct ?? it.auditoria_anp?.variacao_pct ?? 0)) <= 0.6).length;
    let heroSub = `Portaria ANP 26/1992 • Tolerância legal: ±0.60% • ${tanquesConformes} de ${items.length} tanques em conformidade estrita.`;
    if (isUnavailable) {
      heroSub = 'Não foi possível apurar o balanço fiscal do LMC por indisponibilidade na fonte de dados.';
    } else if (isNoMovement) {
      heroSub = 'Nenhuma movimentação de combustíveis registrada no período.';
    }

    // Valores do Comparativo
    const escTotal = Number(metrics.total_estoque_escriturado_litros ?? metrics.estoque_escriturado_total_litros ?? resumo.estoque_escriturado_total_litros ?? 0);
    const fisTotal = Number(metrics.total_estoque_fisico_litros ?? metrics.estoque_fisico_total_litros ?? resumo.estoque_fisico_total_litros ?? 0);
    const varTotalL = Number(metrics.variacao_volumetrica_total_litros ?? resumo.variacao_volumetrica_total_litros ?? (fisTotal - escTotal));

    // Bloco de Limitação (F5-02 / F6-01)
    let limitationHtml = '';
    const limText = assessment.limitation || resumo.limitation;
    if (isUnavailable) {
      limitationHtml = `
        <div class="decision-limitation-callout border-rose-500/30 bg-rose-950/20 text-rose-200/90">
          <span class="inline-flex text-rose-400">${CHAT_ICONS.alert}</span>
          <div>
            <strong class="font-semibold text-rose-300">Contingência Operacional:</strong>
            <span class="text-rose-200/90">${this.escapeHtml(limText || data.motivo || 'Livro de Movimentação de Combustíveis (LMC) indisponível no ERP fiscal.')}</span>
          </div>
        </div>
      `;
    } else if (limText && !isNoMovement) {
      limitationHtml = `
        <div class="decision-limitation-callout">
          <span class="inline-flex text-amber-400">${CHAT_ICONS.alert}</span>
          <div>
            <strong class="font-semibold">Marco Regulatório & Premissa:</strong>
            <span class="text-amber-200/90">${this.escapeHtml(limText)}</span>
          </div>
        </div>
      `;
    }

    // Lista de Tanques Auditados no LMC
    let rowsHtml = '';
    items.forEach(cItem => {
      const vL = parseFloat(cItem.variacao_litros ?? cItem.auditoria_anp?.variacao_litros ?? 0);
      const vP = parseFloat(cItem.variacao_pct ?? cItem.auditoria_anp?.variacao_pct ?? cItem.variacao_percentual ?? 0);
      const cConf = Math.abs(vP) <= 0.60;
      const tagConf = cConf
        ? `<span class="text-emerald-400 font-bold inline-flex items-center gap-1">${CHAT_ICONS.check} Conforme</span>`
        : `<span class="text-rose-400 font-bold inline-flex items-center gap-1">${CHAT_ICONS.alert} Alerta ANP</span>`;

      const escLitros = parseFloat(cItem.estoque_escriturado_litros ?? cItem.movimentacao?.estoque_escriturado_litros ?? 0).toLocaleString('pt-BR', { maximumFractionDigits: 1 });
      const fisLitros = parseFloat(cItem.estoque_fisico_medido_litros ?? cItem.estoque_fisico_litros ?? cItem.movimentacao?.estoque_fisico_medido_litros ?? 0).toLocaleString('pt-BR', { maximumFractionDigits: 1 });
      const nome = cItem.combustivel || (cItem.tanque ? `Tanque ${cItem.tanque}` : 'Combustível');
      const codTan = cItem.tanque || '00';

      rowsHtml += `
        <div class="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800 text-xs font-sans flex items-center justify-between gap-2">
          <div>
            <div class="font-bold text-slate-200">TQ ${this.escapeHtml(codTan)} • ${this.escapeHtml(nome)}</div>
            <div class="text-[10px] text-slate-400 tabular-nums">Escriturado: ${escLitros} L | Físico: ${fisLitros} L</div>
          </div>
          <div class="text-right">
            <div class="${cConf ? 'text-emerald-300' : 'text-rose-400'} font-bold tabular-nums">
              Δ ${vL > 0 ? '+' : ''}${vL.toFixed(1)} L (${vP > 0 ? '+' : ''}${vP.toFixed(2)}%)
            </div>
            <div class="text-[10px]">${tagConf}</div>
          </div>
        </div>
      `;
    });

    // Bloco de Pendências
    let pendingHtml = '';
    if (pendingItems.length > 0) {
      const itemsList = pendingItems.map(p => `
        <div class="decision-pending-item cursor-pointer hover:bg-rose-500/10 transition-colors" onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'tanques');" title="Ver detalhes nas evidências">
          <div class="flex items-center gap-2">
            <span class="text-rose-400 font-bold">${CHAT_ICONS.alert}</span>
            <span class="font-semibold text-slate-200">${this.escapeHtml(p.label)}</span>
          </div>
          <span class="text-[10px] text-slate-400 font-sans flex items-center gap-1">
            <span>LMC</span>
            <span>↗</span>
          </span>
        </div>
      `).join('');

      pendingHtml = `
        <div class="space-y-1.5">
          <span class="text-[10px] font-sans uppercase tracking-wider text-slate-400 font-semibold">Pendências Regulatórias:</span>
          <div class="decision-pending-list">${itemsList}</div>
        </div>
      `;
    }

    const recLabel = action.label || 'Auditar Medição Física nos Tanques';
    const dataConsulta = c.context?.data_auditada || (c.context?.queried_at ? new Date(c.context.queried_at).toLocaleDateString('pt-BR') : 'Data Recente');

    return `
      <div class="decision-card" data-evidence-id="${evId}">
        <!-- Context Header -->
        <div class="decision-header">
          <div class="decision-context">
            <span class="decision-context-title">${this.escapeHtml(assessment.title || 'Conciliação Físico-Contábil do LMC ANP')}</span>
            <span class="decision-context-sub">
              <span>${CHAT_ICONS.calendar} ${this.escapeHtml(dataConsulta)}</span>
              <span>•</span>
              <span>${CHAT_ICONS.audit} Portaria ANP 26/1992</span>
              <span>•</span>
              <span>${CHAT_ICONS.unit} ${this.escapeHtml(c.context?.unit_id || 'Posto')}</span>
            </span>
          </div>
          <span class="decision-status-badge ${badgeClass}">
            <span>${badgeIcon}</span>
            <span>${this.escapeHtml(badgeText)}</span>
          </span>
        </div>

        <!-- Hero Metric -->
        <div class="decision-hero">
          <div class="decision-hero-header">
            <span class="decision-hero-label">${this.escapeHtml(heroLabel)}</span>
            <span class="px-2 py-0.5 rounded text-[10px] font-sans font-semibold ${dentroTolerancia ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30' : 'bg-rose-500/15 text-rose-300 border border-rose-500/30'}">
              ${dentroTolerancia ? 'Dentro da Tolerância' : 'Fora do Limite Legal'}
            </span>
          </div>
          <div class="decision-hero-value ${heroColorClass}">
            ${heroVal}
          </div>
          <div class="decision-hero-sub">
            ${this.escapeHtml(heroSub)}
          </div>
        </div>

        <!-- Régua Visual da ANP [-0.6% a +0.6%] com Alternativa Textual Acessível (F5-09) -->
        <div class="widget-anp-ruler-container" role="figure" aria-label="Régua de Variação Volumétrica ANP: ${needleText} (tolerância permitida entre -0.6% e +0.6%)">
          <div class="flex justify-between text-[10px] font-sans font-medium text-slate-400 px-1">
            <span class="text-rose-400 font-bold">-0.6% (Limite)</span>
            <span class="text-emerald-400 font-bold">0.0% (Equilíbrio)</span>
            <span class="text-rose-400 font-bold">+0.6% (Limite)</span>
          </div>

          <div class="widget-anp-track" aria-hidden="true">
            <div class="widget-anp-safezone-mark"></div>
            <div class="widget-anp-needle" style="left: ${needleLeft}%; color: ${needleColor};">
              <div class="widget-anp-needle-pin"></div>
              <div class="widget-anp-needle-line"></div>
            </div>
          </div>

          <div class="text-center font-sans text-xs mt-1">
            <span class="text-slate-400">Desvio Regulatório: </span>
            <strong style="color: ${needleColor};" class="tabular-nums">${needleText}</strong>
            <span class="text-[10px] text-slate-500 ml-1">(${dentroTolerancia ? 'Dentro da tolerância legal de ±0.60%' : 'Inconformidade: requer verificação física'})</span>
          </div>
        </div>

        ${limitationHtml}

        <!-- Comparativo Compacto -->
        ${(!isNoMovement && !isUnavailable) ? `
          <div class="decision-comparison-grid">
            <div class="decision-comp-item">
              <span class="decision-comp-label">Estoque Escriturado</span>
              <strong class="decision-comp-val text-cyan-300 tabular-nums">${this.formatLiters(escTotal, 1)}</strong>
              <span class="decision-comp-sub">Saldo contábil ERP</span>
            </div>
            <div class="decision-comp-item">
              <span class="decision-comp-label">Estoque Físico Medido</span>
              <strong class="decision-comp-val text-slate-100 tabular-nums">${this.formatLiters(fisTotal, 1)}</strong>
              <span class="decision-comp-sub">Medição na régua/sonda</span>
            </div>
            <div class="decision-comp-item">
              <span class="decision-comp-label">Variação Total</span>
              <strong class="decision-comp-val ${dentroTolerancia ? 'text-emerald-300' : 'text-rose-400'} tabular-nums">
                ${varTotalL > 0 ? '+' : ''}${this.formatLiters(varTotalL, 1)}
              </strong>
              <span class="decision-comp-sub tabular-nums">${needleText} global</span>
            </div>
          </div>
        ` : ''}

        <!-- Lista de Tanques -->
        <div class="space-y-1.5 mt-1">
          ${isUnavailable ? '<div class="p-3 rounded-xl bg-slate-900/60 border border-rose-500/20 text-rose-300 text-xs font-sans">Demonstrativo por combustível suspenso por indisponibilidade da fonte fiscal.</div>' : (rowsHtml || '<div class="text-xs font-sans text-slate-400">Nenhum tanque retornado no relatório.</div>')}
        </div>

        ${pendingHtml}

        <!-- Ações Permitidas -->
        <div class="decision-actions">
          ${isUnavailable ? `
            <button 
              type="button" 
              class="decision-btn-primary" 
              onclick="if (window.auraChat) window.auraChat.sendUserPrompt('O LMC de ontem fechou dentro da tolerância oficial da ANP?');"
              title="Tentar executar a consulta novamente">
              <span>${CHAT_ICONS.refresh}</span>
              <span>Tentar Novamente</span>
            </button>
            <button 
              type="button" 
              class="decision-btn-secondary" 
              onclick="if (window.auraChat) window.auraChat.sendUserPrompt('Como preencher o LMC em contingência sem sistema ERP?');"
              title="Procedimento de contingência">
              <span>${CHAT_ICONS.wrench}</span>
              <span>Procedimento de Contingência</span>
            </button>
          ` : `
            <button 
              type="button" 
              class="decision-btn-primary" 
              onclick="if (window.auraChat) window.auraChat.sendUserPrompt('Como auditar a divergência física no tanque de combustíveis?');"
              title="Abrir procedimento de conferência de sonda e régua">
              ${CHAT_ICONS.search}
              <span>${this.escapeHtml(recLabel)}</span>
            </button>

            <button 
              type="button" 
              class="decision-btn-secondary" 
              onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'formula');"
              title="Ver definição regulatória da Portaria 26 da ANP">
              ${CHAT_ICONS.formula}
              <span>Como foi calculado</span>
            </button>

            <button 
              type="button" 
              class="decision-btn-secondary" 
              onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'tanques');"
              title="Ver balanço físico-contábil completo dos tanques">
              ${CHAT_ICONS.tank}
              <span>Ver Tanques & ANP</span>
            </button>

            <button 
              type="button" 
              class="decision-btn-secondary" 
              onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'resumo');"
              title="Ver fontes fiscais e telemetria">
              ${CHAT_ICONS.audit}
              <span>Resumo & Fontes</span>
            </button>
          `}
        </div>
      </div>
    `;
  }

  /**
   * Widget 3: Card de Decisão Executiva para Conciliação de Turno & Caixa
   * Implementação AURA Precision Glass v1.0 (Marco 1 / Fases 1 a 3).
   * Garante:
   * 1. Superfície única estável, sem cards aninhados.
   * 2. Semântica estrita: Análise parcial nunca é exibida como quebra definitiva.
   * 3. Métrica hero em destaque com números tabulares e formatação pt-BR.
   * 4. Comparativo compacto entre Automação da Pista, Caixas PDV e Encerrantes Físicos.
   * 5. Limitações e pendências verificáveis transparentes.
   * 6. Acesso em 1 clique ao Drawer Lateral de Evidências e Fórmulas.
   */
  renderTurnoWidget(data) {
    if (!data || typeof data !== 'object') {
      return `<div class="decision-card"><p class="text-xs text-slate-400 font-sans">Dados de conciliação indisponíveis ou formato não reconhecido.</p></div>`;
    }

    const c = data.contrato || data;

    // F1-08: Tratar versões de contrato desconhecidas com fallback seguro (sem aparentar validação financeira)
    if (c.schema_version && c.schema_version !== '1.0') {
      return `
        <div class="decision-card">
          <div class="decision-header">
            <div class="decision-context">
              <span class="decision-context-title">Versão de Contrato Não Suportada (v${this.escapeHtml(c.schema_version)})</span>
              <span class="decision-context-sub">Contrato AURA Precision Glass v1.0 esperado</span>
            </div>
            <span class="decision-status-badge status-neutral">
              <span>${CHAT_ICONS.alert}</span>
              <span>Schema Desconhecido</span>
            </div>
          </div>
          <div class="p-3.5 rounded-xl bg-slate-900/80 border border-amber-500/30 text-amber-200/90 font-sans text-xs space-y-1.5">
            <div class="flex items-center gap-1.5"><span class="inline-flex text-amber-400">${CHAT_ICONS.alert}</span> <strong>Aviso de Conformidade Contábil:</strong></div>
            <p class="text-[11px] text-slate-300">
              A estrutura analítica de dados recebida utiliza a versão <code>${this.escapeHtml(c.schema_version)}</code>, incompatível com o renderizador atual. Por governança e segurança financeira, a exibição de decisão foi suspensa.
            </p>
          </div>
        </div>
      `;
    }

    // Validação mínima de payload válido
    if (!data.contrato && !data.assessment && !data.metrics && !data.resumo_executivo) {
      if (this.isSourceUnavailable(data)) {
        return this.renderContingencyCard('Conciliação de Turno & Caixa', data, 'Qual a conciliação do turno de hoje?');
      }
      return `
        <div class="decision-card">
          <div class="decision-header">
            <span class="decision-context-title">Auditoria Indisponível</span>
            <span class="decision-status-badge status-neutral">Sem Dados</span>
          </div>
          <p class="text-xs text-slate-400 font-sans">Dados de conciliação vazios ou estrutura não reconhecida.</p>
        </div>
      `;
    }

    const assessment = c.assessment || {};
    const metrics = c.metrics || {};
    const pendingItems = c.pending_items || [];
    const action = c.recommended_action || {};
    const resumo = data.resumo_executivo || {};
    const tri = data.triangulacao_pista || {};

    const isUnavailable = this.isSourceUnavailable(data, assessment);
    const isNoMovement = !isUnavailable && (assessment.finality === 'no_movement' || data.status === 'sem_movimento' || assessment.status_code === 'SEM_MOVIMENTACAO');
    const isPartial = !isUnavailable && !isNoMovement && (assessment.finality === 'partial' || resumo.status_conciliacao?.includes('ANDAMENTO'));

    if (isUnavailable) {
      return this.renderContingencyCard('Conciliação de Turno & Caixa', data, 'Qual a conciliação do turno de hoje?');
    }

    // Armazena payload na memória global de evidências
    const evId = 'ev_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7);
    if (typeof window !== 'undefined') {
      if (!window.__auraEvidenceStore) window.__auraEvidenceStore = {};
      window.__auraEvidenceStore[evId] = data;
    }

    // Badges de Status Semânticos
    let badgeClass = 'status-neutral';
    let badgeIcon = CHAT_ICONS.audit;
    let badgeText = assessment.badge_label || resumo.status_conciliacao || 'Turno';

    if (isUnavailable) {
      badgeClass = 'status-divergent';
      badgeIcon = CHAT_ICONS.alert;
      badgeText = assessment.badge_label || 'Fonte Indisponível';
    } else if (isPartial) {
      badgeClass = 'status-partial';
      badgeIcon = CHAT_ICONS.clock;
      badgeText = assessment.badge_label || 'Análise parcial (provisória)';
    } else if (isNoMovement) {
      badgeClass = 'status-neutral';
      badgeIcon = CHAT_ICONS.pause;
      badgeText = 'Sem movimentação';
    } else if (assessment.severity === 'critical' || resumo.status_conciliacao?.includes('FURO') || resumo.status_conciliacao?.includes('DIVERGENCIA')) {
      badgeClass = 'status-divergent';
      badgeIcon = CHAT_ICONS.alert;
      badgeText = assessment.badge_label || 'Divergência confirmada';
    } else {
      badgeClass = 'status-validated';
      badgeIcon = CHAT_ICONS.check;
      badgeText = assessment.badge_label || 'Conciliação validada';
    }

    // Contexto
    const dataAuditada = data.data_auditada || c.context?.data_auditada || 'Data Recente';
    const rawTurno = data.turno_auditado ?? c.context?.shift_id ?? 'Todos os Turnos';
    let turnoAuditado = rawTurno;
    if (rawTurno === 1 || rawTurno === '1') turnoAuditado = '1º Turno';
    else if (rawTurno === 2 || rawTurno === '2') turnoAuditado = '2º Turno';
    else if (rawTurno === 3 || rawTurno === '3') turnoAuditado = '3º Turno';
    const title = assessment.title || (isPartial ? 'Conciliação parcial do turno' : 'Conciliação do Turno & Caixa');

    // Métrica Hero: Diferença Financeira
    const diffVal = Number(metrics.difference ?? resumo.diferenca_financeira_caixa ?? 0);
    let diffColorClass = 'text-emerald';
    let heroLabel = 'Diferença Contábil';
    let heroBadge = '';

    if (isPartial) {
      diffColorClass = diffVal < 0 ? 'text-amber' : 'text-emerald';
      heroLabel = 'Diferença Provisória';
      heroBadge = `<span class="px-2.5 py-0.5 rounded text-[10px] font-sans font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/30">Caixas em Aberto</span>`;
    } else if (isNoMovement || isUnavailable) {
      diffColorClass = 'text-slate-400';
      heroLabel = 'Situação';
    } else if (Math.abs(diffVal) < 0.01) {
      diffColorClass = 'text-emerald';
      heroLabel = 'Caixa Conciliado';
      heroBadge = `<span class="px-2.5 py-0.5 rounded text-[10px] font-sans font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">100% Batido</span>`;
    } else if (diffVal < 0) {
      diffColorClass = 'text-rose';
      heroLabel = 'Falta Apurada';
      heroBadge = `<span class="px-2.5 py-0.5 rounded text-[10px] font-sans font-semibold bg-rose-500/15 text-rose-300 border border-rose-500/30">Furo de Caixa</span>`;
    } else {
      diffColorClass = 'text-emerald';
      heroLabel = 'Sobra Apurada';
      heroBadge = `<span class="px-2.5 py-0.5 rounded text-[10px] font-sans font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">Sobra de Caixa</span>`;
    }

    const diffFormatted = (isNoMovement || isUnavailable)
      ? '-'
      : this.formatSignedBRL(diffVal);

    // Valores do Comparativo
    const autRev = Number(metrics.automation_revenue ?? resumo.faturamento_pista_total ?? 0);
    const autVol = Number(metrics.automation_volume_liters ?? tri.total_litros_automacao ?? 0);
    const posRev = Number(metrics.pos_revenue ?? resumo.faturamento_caixa_total ?? 0);

    const encState = metrics.physical_volume_state || (tri.total_litros_faturados_encerrante === 0 && autVol > 0 ? 'not_reported' : 'measured');
    const encVol = metrics.physical_volume_liters ?? (encState === 'not_reported' ? null : Number(tri.total_litros_faturados_encerrante || 0));

    // Bloco de Limitação (F1-03 / F6-01)
    let limitationHtml = '';
    const limText = assessment.limitation || (isPartial ? 'Caixas abertos no PDV e encerrantes pendentes no ERP' : null);
    if (isUnavailable) {
      limitationHtml = `
        <div class="decision-limitation-callout border-rose-500/30 bg-rose-950/20 text-rose-200/90">
          <span class="inline-flex text-rose-400">${CHAT_ICONS.alert}</span>
          <div>
            <strong class="font-semibold text-rose-300">Contingência Operacional:</strong>
            <span class="text-rose-200/90">${this.escapeHtml(limText || data.motivo || 'Fonte de dados do ERP ou banco local indisponível para conciliação.')}</span>
          </div>
        </div>
      `;
    } else if (limText && !isNoMovement) {
      limitationHtml = `
        <div class="decision-limitation-callout">
          <span class="inline-flex text-amber-400">${CHAT_ICONS.alert}</span>
          <div>
            <strong class="font-semibold">Limitação da Análise:</strong>
            <span class="text-amber-200/90">${this.escapeHtml(limText)}</span>
          </div>
        </div>
      `;
    }

    // Bloco de Pendências com atalhos para abas
    let pendingHtml = '';
    if (pendingItems.length > 0) {
      const itemsList = pendingItems.map(p => {
        const targetTab = p.code === 'physical_readings_missing' ? 'bicos' : (p.code === 'tanks_anp_alert' ? 'tanques' : 'caixas');
        const badgeTag = p.code === 'physical_readings_missing' ? 'Encerrante' : (p.code === 'tanks_anp_alert' ? 'Tanque' : 'PDV');
        return `
          <div class="decision-pending-item cursor-pointer hover:bg-amber-500/10 transition-colors" onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', '${targetTab}');" title="Ver detalhes desta pendência nas evidências">
            <div class="flex items-center gap-2">
              <span class="text-amber-400 font-bold">${CHAT_ICONS.alert}</span>
              <span class="font-semibold text-slate-200">${this.escapeHtml(p.label)}</span>
            </div>
            <span class="text-[10px] text-slate-400 font-sans flex items-center gap-1">
              <span>${badgeTag}</span>
              <span>↗</span>
            </span>
          </div>
        `;
      }).join('');

      pendingHtml = `
        <div class="space-y-1.5">
          <span class="text-[10px] font-sans uppercase tracking-wider text-slate-400 font-semibold">Pendências Operacionais:</span>
          <div class="decision-pending-list">${itemsList}</div>
        </div>
      `;
    }

    // Ação recomendada (Somente leitura segura)
    const recLabel = action.label || (isPartial ? 'Conferir encerrantes e fechamento no ERP' : 'Conferir no ERP');

    return `
      <div class="decision-card" data-evidence-id="${evId}">
        <!-- Topo: Contexto da Consulta & Status Badge -->
        <div class="decision-header">
          <div class="decision-context">
            <span class="decision-context-title">${this.escapeHtml(title)}</span>
            <span class="decision-context-sub">
              <span>${CHAT_ICONS.calendar} ${this.escapeHtml(dataAuditada)}</span>
              <span>•</span>
              <span>${CHAT_ICONS.pulse} ${this.escapeHtml(turnoAuditado)}</span>
              <span>•</span>
              <span>${CHAT_ICONS.telemetry} Pista + PDV</span>
            </span>
          </div>
          <span class="decision-status-badge ${badgeClass}">
            <span>${badgeIcon}</span>
            <span>${this.escapeHtml(badgeText)}</span>
          </span>
        </div>

        <!-- Métrica Hero Executiva -->
        <div class="decision-hero">
          <div class="decision-hero-header">
            <span class="decision-hero-label">${this.escapeHtml(heroLabel)}</span>
            ${heroBadge}
          </div>
          <div class="decision-hero-value ${diffColorClass}">
            ${diffFormatted}
          </div>
          <div class="decision-hero-sub">
            ${isPartial ? 'A diferença definitiva será apurada após o encerramento formal dos caixas e lançamento de encerrantes.' : (isNoMovement ? 'Nenhum lançamento encontrado para a data informada.' : (isUnavailable ? 'Não foi possível consultar os dados da auditoria.' : 'Comparativo entre vendas faturadas no PDV e saídas registradas na pista.'))}
          </div>
        </div>

        ${limitationHtml}

        <!-- Comparativo Compacto (Automação vs PDV vs Encerrante) -->
        ${(!isNoMovement && !isUnavailable) ? `
          <div class="decision-comparison-grid">
            <div class="decision-comp-item">
              <span class="decision-comp-label">Automação da Pista</span>
              <strong class="decision-comp-val text-cyan-300">${this.formatBRL(autRev)}</strong>
              <span class="decision-comp-sub">${this.formatLiters(autVol, 1)} medidos</span>
            </div>
            <div class="decision-comp-item">
              <span class="decision-comp-label">Cupons / PDV</span>
              <strong class="decision-comp-val text-slate-100">${this.formatBRL(posRev)}</strong>
              <span class="decision-comp-sub">${isPartial ? 'Caixa em andamento' : 'Caixa fechado'}</span>
            </div>
            <div class="decision-comp-item">
              <span class="decision-comp-label">Encerrantes Físicos</span>
              <strong class="decision-comp-val ${encState === 'not_reported' ? 'text-amber-400' : 'text-slate-100'}">
                ${encState === 'not_reported' ? 'Pendente' : (encVol !== null ? this.formatLiters(encVol, 1) : '-')}
              </strong>
              <span class="decision-comp-sub">${encState === 'not_reported' ? 'Não digitado no ERP' : 'Lançado no fechabomba'}</span>
            </div>
          </div>
        ` : ''}

        ${pendingHtml}

        <!-- Ações Permitidas (Uma primária + botões de evidência) -->
        <div class="decision-actions">
          ${isUnavailable ? `
            <button 
              type="button" 
              class="decision-btn-primary" 
              onclick="if (window.auraChat) window.auraChat.sendUserPrompt('Qual a conciliação do turno de hoje?');"
              title="Tentar executar a consulta novamente">
              <span>${CHAT_ICONS.refresh}</span>
              <span>Tentar Novamente</span>
            </button>
            <button 
              type="button" 
              class="decision-btn-secondary" 
              onclick="if (window.auraChat) window.auraChat.sendUserPrompt('Como auditar fechamento de turno em contingência sem ERP?');"
              title="Procedimento de contingência">
              <span>${CHAT_ICONS.wrench}</span>
              <span>Procedimento de Contingência</span>
            </button>
          ` : `
            <button 
              type="button" 
              class="decision-btn-primary" 
              onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'resumo');"
              title="Abrir painel lateral com proveniência e detalhamento">
              ${CHAT_ICONS.audit}
              <span>${this.escapeHtml(recLabel)} ↗</span>
            </button>

            <button 
              type="button" 
              class="decision-btn-secondary" 
              onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'formula');"
              title="Ver fórmula matemática e definição do cálculo">
              ${CHAT_ICONS.formula}
              <span>Como foi calculado</span>
            </button>

            ${pendingItems.length > 0 ? `
              <button 
                type="button" 
                class="decision-btn-secondary" 
                onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'resumo');"
                title="Ver lista de pendências impeditivas">
                ${CHAT_ICONS.alert}
                <span>Ver pendências (${pendingItems.length})</span>
              </button>
            ` : ''}

            <button 
              type="button" 
              class="decision-btn-secondary" 
              onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'bicos');"
              title="Ver todos os bicos da pista e encerrantes">
              ${CHAT_ICONS.nozzle}
              <span>Ver Bicos & Caixas</span>
            </button>
          `}
        </div>
      </div>
    `;
  }

  /**
   * Abre o Drawer Lateral de Evidências com foco acessível
   */
  openEvidence(evId, activeTab = 'resumo') {
    if (typeof document === 'undefined') return;
    this.lastFocusedElement = document.activeElement;
    this.currentEvidenceId = evId;

    const store = (typeof window !== 'undefined' && window.__auraEvidenceStore) || {};
    const data = store[evId] || {};

    const drawer = document.getElementById('aura-evidence-drawer') || document.getElementById('evidence-drawer');
    const overlay = document.getElementById('aura-evidence-drawer-overlay') || document.getElementById('evidence-drawer-overlay');
    const titleEl = document.getElementById('evidence-drawer-title');
    const chipEl = document.getElementById('evidence-drawer-status-chip');
    const subEl = document.getElementById('evidence-drawer-subtitle');

    if (!drawer || !overlay) return;

    const c = data.contrato || data;
    const assessment = c.assessment || {};
    const intent = c.intent || data.intent || 'shift_reconciliation';
    const dataAuditada = data.data_auditada || c.context?.data_auditada || (c.context?.queried_at ? new Date(c.context.queried_at).toLocaleDateString('pt-BR') : 'Data Recente');
    const turnoAuditado = data.turno_auditado || c.context?.shift_id || 'Turno';

    const titleMap = {
      'tank_forecast': `Evidências: Autonomia de Tanques (${dataAuditada})`,
      'pump_performance': `Evidências: Performance da Pista (${dataAuditada})`,
      'lmc_report': `Evidências: Conciliação LMC ANP (${dataAuditada})`,
      'market_basket': `Evidências: Combos & Conveniência (${dataAuditada})`,
      'vendas_analitico': `Evidências: Vendas & Faturamento (${dataAuditada})`,
      'consultar_analise_vendas_erp': `Evidências: Vendas & Faturamento (${dataAuditada})`,
      'shift_reconciliation': `Evidências: ${dataAuditada} (${turnoAuditado})`
    };

    if (titleEl) titleEl.textContent = titleMap[intent] || `Evidências: ${dataAuditada}`;
    const isUnavail = this.isSourceUnavailable(data, assessment);
    if (chipEl) {
      chipEl.textContent = assessment.badge_label || (isUnavail ? 'Fonte Indisponível' : (assessment.finality === 'partial' ? 'Provisório' : 'Validado'));
      const isCrit = assessment.severity === 'critical' || isUnavail;
      const isAttn = !isUnavail && (assessment.severity === 'attention' || assessment.finality === 'partial');
      chipEl.className = `px-2 py-0.5 rounded-full text-[10px] font-sans font-semibold ${isCrit ? 'bg-rose-500/15 text-rose-300 border border-rose-500/30' : (isAttn ? 'bg-amber-500/15 text-amber-300 border border-amber-500/30' : 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30')}`;
    }
    if (subEl) {
      const subMap = {
        'tank_forecast': `Unidade: ${c.context?.unit_id || 'Posto'} • Tanques & Previsão de Run-Out • ERP Leitura`,
        'pump_performance': `Unidade: ${c.context?.unit_id || 'Posto'} • Automação da Pista & PDV`,
        'lmc_report': `Unidade: ${c.context?.unit_id || 'Posto'} • Portaria ANP 26/1992 • Tolerância ±0.60%`,
        'market_basket': `Unidade: ${c.context?.unit_id || 'Loja'} • Cesta de Compras & Combos PDV`,
        'vendas_analitico': `Unidade: ${c.context?.unit_id || 'Posto 01'} • Histórico de Vendas & PDV • ERP`,
        'consultar_analise_vendas_erp': `Unidade: ${c.context?.unit_id || 'Posto 01'} • Histórico de Vendas & PDV • ERP`,
        'shift_reconciliation': `Unidade: ${c.context?.unit_id || 'Posto'} • Data: ${dataAuditada} • Turno: ${turnoAuditado}`
      };
      subEl.textContent = subMap[intent] || `Unidade: ${c.context?.unit_id || 'Posto'}`;
    }

    this.switchEvidenceTab(activeTab);

    overlay.classList.add('open');
    drawer.classList.add('open');
    drawer.setAttribute('aria-hidden', 'false');
    overlay.setAttribute('aria-hidden', 'false');

    const closeBtn = document.getElementById('btn-close-evidence-drawer');
    if (closeBtn) closeBtn.focus();
    if (typeof window !== 'undefined' && window.lucide) window.lucide.createIcons();
  }

  /**
   * Fecha o Drawer Lateral de Evidências e devolve o foco ao botão chamador
   */
  closeEvidence() {
    if (typeof document === 'undefined') return;
    const drawer = document.getElementById('aura-evidence-drawer') || document.getElementById('evidence-drawer');
    const overlay = document.getElementById('aura-evidence-drawer-overlay') || document.getElementById('evidence-drawer-overlay');
    if (drawer) {
      drawer.classList.remove('open');
      drawer.setAttribute('aria-hidden', 'true');
    }
    if (overlay) {
      overlay.classList.remove('open');
      overlay.setAttribute('aria-hidden', 'true');
    }

    if (this.lastFocusedElement && typeof this.lastFocusedElement.focus === 'function') {
      try {
        this.lastFocusedElement.focus();
      } catch (_) {}
    }
  }

  /**
   * Alterna a aba ativa no Drawer de Evidências
   */
  switchEvidenceTab(tabName) {
    if (typeof document === 'undefined') return;
    this.currentEvidenceTab = tabName;

    document.querySelectorAll('.evidence-tab-btn').forEach(btn => {
      const t = btn.getAttribute('data-ev-tab');
      const isSelected = (t === tabName);
      btn.setAttribute('aria-selected', isSelected ? 'true' : 'false');
      btn.setAttribute('tabindex', isSelected ? '0' : '-1');
      if (isSelected) {
        btn.className = 'evidence-tab-btn active px-3 py-1.5 rounded-lg bg-slate-800 text-white font-semibold border border-slate-700';
      } else {
        btn.className = 'evidence-tab-btn px-3 py-1.5 rounded-lg text-slate-400 hover:text-white border border-transparent';
      }
    });

    const store = (typeof window !== 'undefined' && window.__auraEvidenceStore) || {};
    const data = store[this.currentEvidenceId] || {};
    const contentEl = document.getElementById('evidence-drawer-content');
    if (contentEl) {
      contentEl.setAttribute('aria-labelledby', `evidence-tab-${tabName}`);
      contentEl.innerHTML = this.renderEvidenceTabContent(data, tabName);
      if (typeof window !== 'undefined' && window.lucide) window.lucide.createIcons();
    }
  }

  /**
   * Renderiza o conteúdo da aba selecionada no Drawer de Evidências
   * Adaptado modularmente para suportar os 5 contratos canônicos da Fase 5:
   * 1. shift_reconciliation
   * 2. tank_forecast
   * 3. pump_performance
   * 4. lmc_report
   * 5. market_basket
   */
  renderEvidenceTabContent(data, tab) {
    if (!data || (typeof data !== 'object') || (!data.contrato && !data.resumo_executivo && !data.assessment && !data.metrics && !this.isSourceUnavailable(data))) {
      return `<div class="p-6 text-center text-slate-400 font-sans text-xs">Dados de evidência indisponíveis para este item.</div>`;
    }

    const c = data.contrato || data;
    const assessment = c.assessment || {};
    const metrics = c.metrics || {};
    const sources = c.sources || [];
    const intent = c.intent || data.intent || 'shift_reconciliation';
    const dataAuditada = data.data_auditada || c.context?.data_auditada || (c.context?.queried_at ? new Date(c.context.queried_at).toLocaleDateString('pt-BR') : 'Data Recente');
    const isUnavailable = this.isSourceUnavailable(data, assessment);

    // =========================================================================
    // ABA: COMO FOI CALCULADO (FÓRMULAS & DEFINIÇÕES CANÔNICAS)
    // =========================================================================
    if (tab === 'formula') {
      if (isUnavailable) {
        return `
          <div class="evidence-section-card">
            <h4 class="font-bold text-slate-100 flex items-center gap-2">
              <span class="inline-flex text-rose-400">${CHAT_ICONS.alert}</span><span>Fonte Indisponível</span>
            </h4>
            <p class="text-slate-300 text-xs leading-relaxed p-3.5 rounded-xl glass-subcard border border-rose-500/20 font-sans">
              A conexão com o banco de dados ERP não pôde ser estabelecida no momento da consulta. O cálculo de fórmulas analíticas foi suspenso para preservar a integridade das métricas.
            </p>
          </div>
        `;
      }

      if (intent === 'tank_forecast') {
        const menorRes = assessment.horizonte_critico_horas ?? metrics.autonomia_critica_horas ?? metrics.menor_autonomia_runout_horas ?? assessment.menor_autonomia_horas ?? 'N/A';
        const menorEsg = assessment.horizonte_runout_horas ?? metrics.autonomia_runout_horas ?? metrics.menor_autonomia_esgotamento_horas ?? assessment.menor_autonomia_esgotamento_horas ?? 'N/A';
        return `
          <div class="space-y-4">
            <div class="evidence-section-card">
              <h4 class="font-bold text-slate-100 flex items-center gap-2">
                <span class="inline-flex text-cyan-400">${CHAT_ICONS.formula}</span><span>Fórmula de Autonomia até Reserva de Segurança (15%)</span>
              </h4>
              <div class="p-3 rounded-xl glass-subcard border border-white/5 font-sans text-xs space-y-2">
                <div class="text-cyan-400 font-bold font-mono">Autonomia_15h = (Volume_Atual - Reserva_Tecnica_15%) / Consumo_Medio_Horario</div>
                <div class="text-slate-300">
                  Reserva Crítica = Capacidade Nominal × 15% (Proteção contra sucção de sedimentos e cavitação da bomba).
                </div>
                <div class="text-emerald-400 font-bold pt-1 border-t border-slate-800">
                  Menor Autonomia até Reserva: ${menorRes !== 'N/A' ? `${Number(menorRes).toFixed(1)}h` : 'N/A'}
                </div>
              </div>
              <p class="text-slate-400 text-xs leading-relaxed">
                A autonomia de run-out técnico aponta o momento limite para descarga da carreta sem interrupção nas bombas de abastecimento.
              </p>
            </div>

            <div class="evidence-section-card">
              <h4 class="font-bold text-slate-100 flex items-center gap-2">
                <span class="inline-flex text-cyan-400">${CHAT_ICONS.pulse}</span><span>Fórmula de Esgotamento Total (0 L) vs Espaço Livre (Ullage)</span>
              </h4>
              <div class="p-3 rounded-xl glass-subcard border border-white/5 font-sans text-xs space-y-2">
                <div class="text-cyan-400 font-bold font-mono">Autonomia_0h = Volume_Atual / Consumo_Medio_Horario</div>
                <div class="text-amber-300">
                  Esgotamento Zero: ${menorEsg !== 'N/A' ? `${Number(menorEsg).toFixed(1)}h` : 'N/A'} (Zerar o tanque acarreta contaminação e perda de escorva).
                </div>
                <div class="pt-1 border-t border-slate-800 text-slate-300">
                  Ullage Livre (L) = Capacidade Nominal - Volume Atual
                </div>
                <div class="text-slate-400">
                  Sugestão Carretas 5k = floor(Ullage Livre / 5.000 L) (compartimentos padrão das distribuidoras).
                </div>
              </div>
            </div>
          </div>
        `;
      }

      if (intent === 'pump_performance') {
        return `
          <div class="space-y-4">
            <div class="evidence-section-card">
              <h4 class="font-bold text-slate-100 flex items-center gap-2">
                <span class="inline-flex text-cyan-400">${CHAT_ICONS.formula}</span><span>Fórmula de Vazão Operacional de Bicos (L/min)</span>
              </h4>
              <div class="p-3 rounded-xl glass-subcard border border-white/5 font-sans text-xs space-y-2">
                <div class="text-cyan-400 font-bold font-mono">Vazão (L/min) = Volume Abastecido (L) / Duração do Abastecimento (min)</div>
                <div class="text-slate-300">
                  Telemetria automatizada recebida via concentrador de automação da pista.
                </div>
                <div class="text-amber-400 font-bold pt-1 border-t border-slate-800">
                  Threshold Operacional: Vazão &lt; 30.0 L/min indica saturação precoce de elemento filtrante ou perda de sucção da bomba mecânica.
                </div>
              </div>
            </div>

            <div class="evidence-section-card">
              <h4 class="font-bold text-slate-100 flex items-center gap-2">
                <span class="inline-flex text-cyan-400">${CHAT_ICONS.nozzle}</span><span>Fórmula de Conversão em Gasolina Aditivada (%)</span>
              </h4>
              <div class="p-3 rounded-xl glass-subcard border border-white/5 font-sans text-xs space-y-2">
                <div class="text-cyan-400 font-bold font-mono">Conversão Aditivada (%) = (Volume Aditivada / Volume Total do Colaborador) × 100</div>
                <div class="text-emerald-400">
                  Meta da Pista: ≥ 25.0% de conversão sobre o volume total abastecido pelo frentista.
                </div>
              </div>
            </div>
          </div>
        `;
      }

      if (intent === 'lmc_report') {
        const limTol = metrics.tolerancia_oficial_pct ?? metrics.limite_tolerancia_anp_pct ?? 0.60;
        return `
          <div class="space-y-4">
            <div class="evidence-section-card">
              <h4 class="font-bold text-slate-100 flex items-center gap-2">
                <span class="inline-flex text-cyan-400">${CHAT_ICONS.formula}</span><span>Fórmula Legal da Portaria ANP nº 26/1992</span>
              </h4>
              <div class="p-3 rounded-xl glass-subcard border border-white/5 font-sans text-xs space-y-2">
                <div class="text-cyan-400 font-bold font-mono">Estoque Escriturado = Estoque Inicial + Entradas Fiscais (NFe) - Saídas dos Bicos</div>
                <div class="text-slate-300">
                  Variação Volumétrica (L) = Estoque Físico Medido (Régua/Sonda) - Estoque Escriturado (L)
                </div>
                <div class="text-emerald-400 font-bold pt-1 border-t border-slate-800">
                  Variação Percentual (Δ%) = (Variação L / Estoque Escriturado L) × 100
                </div>
              </div>
              <p class="text-slate-400 text-xs leading-relaxed">
                Tolerância regulamentar legal: <strong>±${limTol}%</strong>. Variações absolutas superiores a 0.60% devem ser investigadas e justificadas tecnicamente no LMC oficial.
              </p>
            </div>
          </div>
        `;
      }

      if (intent === 'market_basket') {
        return `
          <div class="space-y-4">
            <div class="evidence-section-card">
              <h4 class="font-bold text-slate-100 flex items-center gap-2">
                <span class="inline-flex text-cyan-400">${CHAT_ICONS.formula}</span><span>Fórmulas de Mineração de Regras de Associação</span>
              </h4>
              <div class="p-3 rounded-xl glass-subcard border border-white/5 font-sans text-xs space-y-2">
                <div class="text-cyan-400 font-bold font-mono">Suporte(A ∪ B) = Cupons(A e B) / Total de Cupons (N)</div>
                <div class="text-slate-300">
                  Confiança(A → B) = P(B | A) = Cupons(A e B) / Cupons(A)
                </div>
                <div class="text-purple-300 font-bold pt-1 border-t border-slate-800">
                  Lift(A → B) = Confiança(A → B) / Suporte(B) = P(A ∩ B) / (P(A) × P(B))
                </div>
              </div>
              <p class="text-slate-400 text-xs leading-relaxed">
                <strong>Interpretação do Lift:</strong> Lift = 1.0 indica independência estatística; Lift &gt; 1.0 indica associação positiva; Lift ≥ 2.0x representa forte afinidade comprovada no comportamento de compra.
              </p>
            </div>
          </div>
        `;
      }

      if (intent === 'vendas_analitico' || intent === 'consultar_analise_vendas_erp') {
        return `
          <div class="space-y-4">
            <div class="evidence-section-card">
              <h4 class="font-bold text-slate-100 flex items-center gap-2">
                <span class="inline-flex text-cyan-400">${CHAT_ICONS.formula}</span><span>Fórmula de Faturamento Consolidado do Posto</span>
              </h4>
              <div class="p-3 rounded-xl glass-subcard border border-white/5 font-sans text-xs space-y-2">
                <div class="text-cyan-400 font-bold font-mono">Faturamento Total = Faturamento Pista + Faturamento Loja</div>
                <div class="text-slate-300">
                  Pista de Combustíveis: Total apurado no concentrador (volume medido em litros × preço unitário).
                </div>
                <div class="text-emerald-400 font-bold pt-1 border-t border-slate-800">
                  Loja de Conveniência: Total dos cupons fiscais emitidos no PDV (pedido + itemped).
                </div>
              </div>
              <p class="text-slate-400 text-xs leading-relaxed">
                Dados integrados diretamente do ERP (PostgreSQL 16) com triangulação de abastecimentos.
              </p>
            </div>
          </div>
        `;
      }

      // Default: shift_reconciliation
      if (assessment.finality === 'no_movement' || data.status === 'sem_movimento') {
        return `
          <div class="evidence-section-card">
            <h4 class="font-bold text-slate-100 flex items-center gap-2">
              <span class="inline-flex text-slate-400">${CHAT_ICONS.pause}</span><span>Sem Movimentação Registrada</span>
            </h4>
            <p class="text-slate-300 text-xs leading-relaxed p-3.5 rounded-xl glass-subcard border border-white/5 font-sans">
              Não foram encontrados lançamentos de bicos, cupons fiscais ou movimentação de caixas para a data consultada (${this.escapeHtml(dataAuditada)}). Por isso, nenhuma diferença contábil ou volumétrica foi apurada.
            </p>
          </div>
        `;
      }

      if (assessment.finality === 'unavailable' || data.status === 'indisponivel') {
        return `
          <div class="evidence-section-card">
            <h4 class="font-bold text-slate-100 flex items-center gap-2">
              <span class="inline-flex text-amber-400">${CHAT_ICONS.alert}</span><span>Fonte Indisponível</span>
            </h4>
            <p class="text-slate-300 text-xs leading-relaxed p-3.5 rounded-xl glass-subcard border border-white/5 font-sans">
              A conexão com o banco de dados ERP não pôde ser estabelecida no momento da consulta. Não foi possível apurar fórmulas contábeis ou volumétricas.
            </p>
          </div>
        `;
      }

      const tri = data.triangulacao_pista || {};
      const autRev = Number(metrics.automation_revenue ?? data.resumo_executivo?.faturamento_pista_total ?? 0);
      const posRev = Number(metrics.pos_revenue ?? data.resumo_executivo?.faturamento_caixa_total ?? 0);
      const diff = Number(metrics.difference ?? data.resumo_executivo?.diferenca_financeira_caixa ?? 0);
      const autVol = Number(metrics.automation_volume_liters ?? tri.total_litros_automacao ?? 0);
      const encState = metrics.physical_volume_state || (tri.total_litros_faturados_encerrante === 0 && autVol > 0 ? 'not_reported' : 'measured');
      const encVol = metrics.physical_volume_liters ?? (encState === 'not_reported' ? null : Number(tri.total_litros_faturados_encerrante || 0));

      let volumetricContent = '';
      if (encState === 'not_reported') {
        volumetricContent = `
          <div class="p-3 rounded-xl glass-subcard border border-white/5 font-sans text-xs space-y-2">
            <div class="text-cyan-400 font-bold font-mono">Triangulação Volumétrica: Pendência de Leitura Física</div>
            <div class="text-slate-300 space-y-1">
              <div>Automação da Pista: <strong class="text-cyan-300 tabular-nums">${this.formatLiters(autVol, 3)}</strong></div>
              <div>Encerrantes Físicos: <strong class="text-amber-400">Pendente / Não digitado no módulo fechabomba</strong></div>
              <div class="pt-1 border-t border-slate-800 text-slate-400">Divergência Pista: <strong class="text-amber-300">Diferença provisória (aguardando leitura dos bicos)</strong></div>
            </div>
          </div>
          <p class="text-slate-400 text-xs leading-relaxed">
            <span class="inline-flex text-amber-400 mr-1">${CHAT_ICONS.alert}</span><strong>Dado ausente:</strong> A ausência de digitação de encerrantes mecânicos <em>não representa 0 L medidos</em>. O fechamento físico permanece provisório até a conferência pelo chefe de pista.
          </p>
        `;
      } else if (encState === 'zero_registered') {
        volumetricContent = `
          <div class="p-3 rounded-xl glass-subcard border border-white/5 font-sans text-xs space-y-2">
            <div class="text-cyan-400 font-bold font-mono">Divergência Pista = Volume Automação - Encerrantes Faturados</div>
            <div class="text-slate-300">
              ${this.formatLiters(autVol, 3)} (Pista) - ${this.formatLiters(0, 3)} (fechabomba) = 
              <strong class="text-emerald-400 tabular-nums">${this.formatLiters(0, 3)}</strong>
            </div>
          </div>
          <p class="text-slate-400 text-xs leading-relaxed">
            ${CHAT_ICONS.check} Zero efetivamente registrado: Turno confirmado sem saídas nos bicos.
          </p>
        `;
      } else {
        const diffVol = autVol - (encVol || 0);
        volumetricContent = `
          <div class="p-3 rounded-xl glass-subcard border border-white/5 font-sans text-xs space-y-2">
            <div class="text-cyan-400 font-bold font-mono">Divergência Pista = Volume Automação - Encerrantes Faturados</div>
            <div class="text-slate-300">
              ${this.formatLiters(autVol, 3)} (Pista) - ${this.formatLiters(encVol, 3)} (fechabomba) = 
              <strong class="${Math.abs(diffVol) < 0.01 ? 'text-emerald-400' : 'text-amber-400'} tabular-nums">${diffVol > 0 ? '+' : ''}${this.formatLiters(diffVol, 3)}</strong>
            </div>
          </div>
          <p class="text-slate-400 text-xs leading-relaxed">
            ${Math.abs(diffVol) < 0.01 ? `${CHAT_ICONS.check} Encerrantes físicos 100% batidos com a automação da pista.` : `<span class="inline-flex text-amber-400 mr-1">${CHAT_ICONS.alert}</span> Diferença apurada entre medição mecânica e automação da pista.`}
          </p>
        `;
      }

      return `
        <div class="space-y-4 font-sans text-xs">
          <div class="evidence-section-card">
            <h4 class="font-bold text-slate-100 flex items-center gap-2">
              <span class="inline-flex text-cyan-400">${CHAT_ICONS.formula}</span><span>Fórmula da Conciliação Financeira</span>
            </h4>
            <div class="p-3 rounded-xl glass-subcard border border-white/5 font-sans text-xs space-y-2">
              <div class="text-cyan-400 font-bold font-mono">Diferença = Faturamento PDV - Automação da Pista</div>
              <div class="text-slate-300">
                ${this.formatBRL(posRev)} (PDV) - ${this.formatBRL(autRev)} (Pista) = 
                <strong class="${diff < 0 ? 'text-amber-400' : 'text-emerald-400'} tabular-nums">${this.formatSignedBRL(diff)}</strong>
              </div>
            </div>
            <p class="text-slate-400 text-xs leading-relaxed">
              ${assessment.finality === 'partial' ? `<span class="inline-flex text-amber-400 mr-1">${CHAT_ICONS.alert}</span><strong>Diferença Provisória:</strong> Como os operadores ainda possuem caixa aberto no PDV e/ou encerrantes mecânicos pendentes, esta diferença não representa uma quebra confirmada.` : `${CHAT_ICONS.check} <strong>Diferença Definitiva:</strong> Fechamento apurado após o encerramento formal de todos os caixas.`}
            </p>
          </div>

          <div class="evidence-section-card">
            <h4 class="font-bold text-slate-100 flex items-center gap-2">
              <span class="inline-flex text-cyan-400">${CHAT_ICONS.nozzle}</span><span>Triangulação Volumétrica da Pista</span>
            </h4>
            ${volumetricContent}
          </div>
        </div>
      `;
    }

    // =========================================================================
    // ABA: BICOS & PISTA
    // =========================================================================
    if (tab === 'bicos') {
      if (intent === 'vendas_analitico' || intent === 'consultar_analise_vendas_erp') {
        const abastList = data.ultimos_abastecimentos_pista || [];
        if (abastList.length === 0) {
          return `<div class="p-4 text-center text-slate-500 font-sans text-xs">Sem abastecimentos recentes registrados no concentrador.</div>`;
        }
        const rows = abastList.map(a => `
          <tr class="border-b border-slate-800/80 text-[11px] font-sans">
            <td class="py-2.5 font-bold text-slate-200">Bomba ${this.escapeHtml(a.bomba)}</td>
            <td class="py-2.5 text-slate-300">${this.escapeHtml(a.nompro)}</td>
            <td class="py-2.5 text-right text-cyan-300 tabular-nums">${this.formatLiters(a.litros, 3)}</td>
            <td class="py-2.5 text-right text-emerald-300 font-semibold tabular-nums">${this.formatBRL(a.total)}</td>
            <td class="py-2.5 text-right text-slate-400 tabular-nums">${this.escapeHtml(a.hora)}</td>
          </tr>
        `).join('');
        return `
          <div class="space-y-3 font-sans">
            <div class="flex items-center justify-between text-xs text-slate-400">
              <span>Últimos Abastecimentos na Pista: <strong>${abastList.length}</strong></span>
              <span>Concentrador Companytec CBC04</span>
            </div>
            <div class="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/60 p-1">
              <table class="w-full text-left font-sans text-xs">
                <thead>
                  <tr class="border-b border-slate-800 text-slate-400 text-[10px] uppercase">
                    <th class="p-2">Bomba</th>
                    <th class="p-2">Combustível</th>
                    <th class="p-2 text-right">Litros</th>
                    <th class="p-2 text-right">Total</th>
                    <th class="p-2 text-right">Hora</th>
                  </tr>
                </thead>
                <tbody>${rows}</tbody>
              </table>
            </div>
          </div>
        `;
      }

      const nozzlesList = c.nozzles || data.auditoria_vazao_bicos || data.vazao_bicos || data.triangulacao_pista?.detalhamento_bicos || [];
      if (nozzlesList.length === 0) {
        return `<div class="p-4 text-center ${isUnavailable ? 'text-rose-300' : 'text-slate-500'} font-sans text-xs">${isUnavailable ? 'Leitura de bicos indisponível por falha na fonte primária.' : 'Sem dados detalhados de bicos para esta consulta.'}</div>`;
      }

      const rows = nozzlesList.map(b => {
        const vazao = b.vazao_media_l_min ?? b.vazao_litros_minuto ?? b.vazao_media_litros_minuto;
        const isLenta = b.alerta_filtro_lento || b.alerta_vazao_lenta || b.alerta_filtro || (vazao !== undefined && parseFloat(vazao) < 30.0);
        const vazaoText = vazao !== undefined ? `${parseFloat(vazao).toFixed(1)} L/min` : 'N/A';
        const volText = this.formatLiters(Number(b.volume_total_litros ?? b.volume_automacao_litros ?? 0), 1);
        const prod = b.combustivel || b.produto_nome || 'Combustível';

        return `
          <tr class="border-b border-slate-800/80 text-[11px] font-sans">
            <td class="py-2.5 font-bold text-slate-200">Bico ${this.escapeHtml(b.bico)}</td>
            <td class="py-2.5 text-slate-300">${this.escapeHtml(prod)}</td>
            <td class="py-2.5 text-right ${isLenta ? 'text-rose-400 font-bold' : 'text-emerald-300'} tabular-nums">${vazaoText}</td>
            <td class="py-2.5 text-right text-cyan-300 tabular-nums">${volText}</td>
            <td class="py-2.5 text-right">
              <span class="px-1.5 py-0.5 rounded text-[10px] inline-flex items-center gap-1 ${isLenta ? 'bg-rose-500/15 text-rose-300 border border-rose-500/30' : 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'}">
                ${isLenta ? `${CHAT_ICONS.alert} Filtro Lento` : `${CHAT_ICONS.check} Normal`}
              </span>
            </td>
          </tr>
        `;
      }).join('');

      return `
        <div class="space-y-3 font-sans">
          <div class="flex items-center justify-between text-xs text-slate-400">
            <span>Total de Bicos Monitorados: <strong>${nozzlesList.length}</strong></span>
            <span>Automação: Concentrador de Pista</span>
          </div>
          <div class="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/60 p-1">
            <table class="w-full text-left font-sans text-xs">
              <thead>
                <tr class="border-b border-slate-800 text-slate-400 text-[10px] uppercase">
                  <th class="p-2">Bico</th>
                  <th class="p-2">Combustível</th>
                  <th class="p-2 text-right">Vazão</th>
                  <th class="p-2 text-right">Volume</th>
                  <th class="p-2 text-right">Diagnóstico</th>
                </tr>
              </thead>
              <tbody>${rows}</tbody>
            </table>
          </div>
        </div>
      `;
    }

    // =========================================================================
    // ABA: CAIXAS & PDV (OU REGRAS DE CONVENIÊNCIA)
    // =========================================================================
    if (tab === 'caixas') {
      if (intent === 'vendas_analitico' || intent === 'consultar_analise_vendas_erp') {
        const prodsConv = data.ultimos_produtos_conveniencia || [];
        if (prodsConv.length === 0) {
          return `<div class="p-4 text-center text-slate-500 font-sans text-xs">Sem cupons recentes faturados na conveniência.</div>`;
        }
        const rows = prodsConv.map(p => `
          <tr class="border-b border-slate-800/80 text-[11px] font-sans">
            <td class="py-2.5 font-bold text-slate-200">Cupom #${this.escapeHtml(p.cupom || p.pedido)} (PDV ${this.escapeHtml(p.pdv)})</td>
            <td class="py-2.5 text-slate-300">${this.escapeHtml(p.nompro)}</td>
            <td class="py-2.5 text-right text-slate-300 tabular-nums">${p.quantidade} un</td>
            <td class="py-2.5 text-right text-emerald-300 font-semibold tabular-nums">${this.formatBRL(p.total_item || p.total_pedido)}</td>
          </tr>
        `).join('');
        return `
          <div class="space-y-3 font-sans">
            <div class="flex items-center justify-between text-xs text-slate-400">
              <span>Últimos Itens Faturados na Conveniência: <strong>${prodsConv.length}</strong></span>
              <span>Módulo PDV / Caixa</span>
            </div>
            <div class="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/60 p-1">
              <table class="w-full text-left font-sans text-xs">
                <thead>
                  <tr class="border-b border-slate-800 text-slate-400 text-[10px] uppercase">
                    <th class="p-2">Cupom / PDV</th>
                    <th class="p-2">Produto</th>
                    <th class="p-2 text-right">Qtd</th>
                    <th class="p-2 text-right">Total</th>
                  </tr>
                </thead>
                <tbody>${rows}</tbody>
              </table>
            </div>
          </div>
        `;
      }

      if (intent === 'market_basket') {
        const rulesList = c.detailed_rules || c.top_combos || data.regras_associacao_detalhadas || [];
        if (rulesList.length === 0) {
          return `<div class="p-4 text-center ${isUnavailable ? 'text-rose-300' : 'text-slate-500'} font-sans text-xs">${isUnavailable ? 'Mineração de regras indisponível por falha na base do PDV.' : 'Nenhuma regra minerada para esta consulta.'}</div>`;
        }

        const rows = rulesList.map(r => {
          const regraStr = r.regra || (r.produto_origem ? `${typeof r.produto_origem === 'object' ? r.produto_origem.nompro : r.produto_origem} ➔ ${typeof r.produto_recomendado === 'object' ? r.produto_recomendado.nompro : r.produto_recomendado}` : 'Regra');
          const liftVal = parseFloat(r.lift ?? r.metricas?.lift ?? 0).toFixed(2);
          let confRaw = r.confianca_pct ?? r.confianca ?? (r.metricas?.confianca ? r.metricas.confianca * 100 : 0);
          if (confRaw <= 1.0 && confRaw > 0) confRaw = confRaw * 100;
          const confVal = parseFloat(confRaw).toFixed(1);

          let supRaw = r.suporte_conjunto_pct ?? r.suporte ?? (r.metricas?.suporte ? r.metricas.suporte * 100 : 0);
          if (supRaw <= 1.0 && supRaw > 0) supRaw = supRaw * 100;
          const supVal = parseFloat(supRaw).toFixed(1);
          const isForte = Boolean(r.forte_sinergia ?? (parseFloat(liftVal) >= 2.0));

          return `
            <tr class="border-b border-slate-800/80 text-[11px] font-sans">
              <td class="py-2.5 font-bold text-slate-200">${this.escapeHtml(regraStr)}</td>
              <td class="py-2.5 text-right text-slate-300 tabular-nums">${supVal}%</td>
              <td class="py-2.5 text-right text-cyan-300 tabular-nums">${confVal}%</td>
              <td class="py-2.5 text-right ${isForte ? 'text-purple-300 font-bold' : 'text-slate-200'} tabular-nums">${liftVal}x</td>
              <td class="py-2.5 text-right">
                <span class="px-1.5 py-0.5 rounded text-[10px] inline-flex items-center gap-1 ${isForte ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30' : 'bg-slate-800 text-slate-400'}">
                  ${isForte ? `${CHAT_ICONS.pulse} Forte Sinergia` : `${CHAT_ICONS.check} Positiva`}
                </span>
              </td>
            </tr>
          `;
        }).join('');

        return `
          <div class="space-y-3 font-sans">
            <div class="flex items-center justify-between text-xs text-slate-400">
              <span>Total de Regras Mineradas: <strong>${rulesList.length}</strong></span>
              <span>Padrão de Compra: Combos PDV</span>
            </div>
            <div class="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/60 p-1">
              <table class="w-full text-left font-sans text-xs">
                <thead>
                  <tr class="border-b border-slate-800 text-slate-400 text-[10px] uppercase">
                    <th class="p-2">Regra de Associação</th>
                    <th class="p-2 text-right">Suporte</th>
                    <th class="p-2 text-right">Confiança</th>
                    <th class="p-2 text-right">Lift</th>
                    <th class="p-2 text-right">Classificação</th>
                  </tr>
                </thead>
                <tbody>${rows}</tbody>
              </table>
            </div>
          </div>
        `;
      }

      // Default: Conciliação de turno caixas
      const caixasList = data.triangulacao_caixa?.caixas || [];
      if (caixasList.length === 0) {
        return `<div class="p-4 text-center ${isUnavailable ? 'text-rose-300' : 'text-slate-500'} font-sans text-xs">${isUnavailable ? 'Leitura de caixas e operadores suspensa por indisponibilidade da fonte ERP.' : 'Sem caixas registrados na data auditada.'}</div>`;
      }

      const rows = caixasList.map(cItem => {
        let opName = String(cItem.operador || 'Operador não informado').trim();
        return `
          <div class="p-3.5 rounded-xl glass-subcard border border-white/5 space-y-2 font-sans text-xs">
            <div class="flex items-center justify-between">
              <span class="font-bold text-slate-100">Sessão #${this.escapeHtml(cItem.caixa_id ?? 'N/D')} • Terminal PDV ${this.escapeHtml(cItem.pdv ?? 'N/D')}</span>
              <span class="text-slate-400 text-[11px]">${this.escapeHtml(opName)}</span>
            </div>
            <div class="flex items-center justify-between pt-1 border-t border-slate-800/60 text-xs">
              <span class="text-slate-400">Total Declarado:</span>
              <strong class="text-cyan-300 tabular-nums">${this.formatBRL(cItem.total_declarado)}</strong>
            </div>
          </div>
        `;
      }).join('');

      return `<div class="space-y-3 font-sans">${rows}</div>`;
    }

    // =========================================================================
    // ABA: TANQUES & ANP
    // =========================================================================
    if (tab === 'tanques') {
      if (intent === 'vendas_analitico' || intent === 'consultar_analise_vendas_erp') {
        const prodsRank = data.produtos_mais_vendidos || [];
        const rowsP = prodsRank.map((p, idx) => `
          <div class="p-3 rounded-xl glass-subcard border border-white/5 flex items-center justify-between text-xs font-sans">
            <div class="flex items-center gap-2.5">
              <span class="w-5 h-5 rounded-full bg-cyan-500/10 text-cyan-400 text-xs flex items-center justify-center font-bold">${idx + 1}</span>
              <div>
                <strong class="text-slate-100">${this.escapeHtml(p.nompro)}</strong>
                <span class="text-[10px] text-slate-400 block">${p.total_saidas || 0} saídas faturadas</span>
              </div>
            </div>
            <div class="text-right">
              <strong class="text-emerald-300 tabular-nums">${this.formatBRL(p.receita_total)}</strong>
              <span class="text-[10px] text-slate-400 block tabular-nums">${p.qtd_total} un/L</span>
            </div>
          </div>
        `).join('');
        return `
          <div class="space-y-3 font-sans">
            <div class="flex items-center justify-between text-xs text-slate-400">
              <span>Ranking Geral dos Mais Vendidos</span>
              <span>Histórico Consolidado ERP</span>
            </div>
            <div class="space-y-2">${rowsP || '<div class="text-slate-500 text-center py-4">Sem dados no ranking.</div>'}</div>
          </div>
        `;
      }

      if (intent === 'tank_forecast') {
        const tanksList = c.tanks || data.detalhamento_tanques || data.tanques || [];
        if (tanksList.length === 0) {
          return `<div class="p-4 text-center ${isUnavailable ? 'text-rose-300' : 'text-slate-500'} font-sans text-xs">${isUnavailable ? 'Telemetria de tanques e saldo volumétrico indisponíveis no momento.' : 'Sem tanques auditados neste relatório.'}</div>`;
        }

        const rows = tanksList.map(t => {
          const cod = t.codtan || t.tanque || '00';
          const comb = t.combustivel || 'Combustível';
          const saldo = this.formatLiters(t.saldo_atual_litros ?? t.volume_atual_litros ?? 0, 0);
          const cap = this.formatLiters(t.capacidade_litros ?? 0, 0);
          const pct = parseFloat(t.ocupacao_pct ?? t.ocupacao_percentual ?? 0).toFixed(1);
          const hResVal = t.autonomia_critica_horas ?? t.autonomia_reserva_horas;
          const hRes = (hResVal !== undefined && hResVal !== null) ? `${parseFloat(hResVal).toFixed(1)}h` : 'N/A';
          const hEsgVal = t.autonomia_runout_horas ?? t.autonomia_esgotamento_horas;
          const hEsg = (hEsgVal !== undefined && hEsgVal !== null) ? `${parseFloat(hEsgVal).toFixed(1)}h` : 'N/A';
          const ullage = this.formatLiters(t.espaco_livre_ullage_litros ?? t.espaco_livre_descarga_litros ?? 0, 0);

          return `
            <div class="p-3.5 rounded-xl glass-subcard border border-white/5 space-y-2 font-sans text-xs">
              <div class="flex items-center justify-between">
                <span class="font-bold text-slate-100">TQ-${this.escapeHtml(cod)} • ${this.escapeHtml(comb)}</span>
                <span class="text-slate-300 font-semibold tabular-nums">${pct}% (${saldo} / ${cap})</span>
              </div>
              <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] text-slate-300 pt-1 border-t border-slate-800">
                <div><span class="text-slate-400">Autonomia 15%:</span> <strong class="text-cyan-300 tabular-nums">${hRes}</strong></div>
                <div><span class="text-slate-400">Esgotamento:</span> <strong class="text-amber-300 tabular-nums">${hEsg}</strong></div>
                <div><span class="text-slate-400">Ullage Livre:</span> <strong class="text-slate-200 tabular-nums">${ullage}</strong></div>
                <div><span class="text-slate-400">Prazo Compra:</span> <strong class="text-slate-200">${this.escapeHtml(t.prazo_ideal_compra || 'Normal')}</strong></div>
              </div>
            </div>
          `;
        }).join('');

        return `<div class="space-y-3 font-sans">${rows}</div>`;
      }

      if (intent === 'lmc_report') {
        const tanksList = c.tanks || data.demonstrativo_por_combustivel || data.tanques || [];
        if (tanksList.length === 0) {
          return `<div class="p-4 text-center ${isUnavailable ? 'text-rose-300' : 'text-slate-500'} font-sans text-xs">${isUnavailable ? 'Registros do LMC e escrituração de tanques indisponíveis no momento.' : 'Sem tanques auditados no LMC.'}</div>`;
        }

        const rows = tanksList.map(t => {
          const cod = t.tanque || t.codtan || '00';
          const comb = t.combustivel || 'Combustível';
          const vP = parseFloat(t.variacao_pct ?? t.auditoria_anp?.variacao_pct ?? 0);
          const vL = parseFloat(t.variacao_litros ?? t.auditoria_anp?.variacao_litros ?? 0);
          const isConf = Math.abs(vP) <= 0.60;
          const escLitros = this.formatLiters(t.estoque_escriturado_litros ?? t.movimentacao?.estoque_escriturado_litros ?? 0, 1);
          const fisLitros = this.formatLiters(t.estoque_fisico_medido_litros ?? t.estoque_fisico_litros ?? t.movimentacao?.estoque_fisico_medido_litros ?? 0, 1);

          return `
            <div class="p-3.5 rounded-xl glass-subcard border border-white/5 space-y-2 font-sans text-xs">
              <div class="flex items-center justify-between">
                <span class="font-bold text-slate-100">TQ-${this.escapeHtml(cod)} • ${this.escapeHtml(comb)}</span>
                <span class="px-2.5 py-0.5 rounded text-[10px] font-semibold inline-flex items-center gap-1 ${isConf ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30' : 'bg-rose-500/15 text-rose-300 border border-rose-500/30'}">
                  ${isConf ? `${CHAT_ICONS.check} Conforme ANP (±0.6%)` : `${CHAT_ICONS.alert} Alerta ANP`}
                </span>
              </div>
              <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] text-slate-300 pt-1 border-t border-slate-800">
                <div><span class="text-slate-400">Escriturado:</span> <span class="tabular-nums">${escLitros}</span></div>
                <div><span class="text-slate-400">Físico:</span> <span class="tabular-nums">${fisLitros}</span></div>
                <div><span class="text-slate-400">Variação L:</span> <strong class="${isConf ? 'text-emerald-300' : 'text-rose-400'} tabular-nums">${vL > 0 ? '+' : ''}${vL.toFixed(1)} L</strong></div>
                <div><span class="text-slate-400">Desvio %:</span> <strong class="${isConf ? 'text-emerald-300' : 'text-rose-400'} tabular-nums">${vP > 0 ? '+' : ''}${vP.toFixed(2)}%</strong></div>
              </div>
            </div>
          `;
        }).join('');

        return `<div class="space-y-3 font-sans">${rows}</div>`;
      }

      // Default: Balanço de tanques turno
      const tanquesList = data.balanco_tanques?.detalhamento_tanques || [];
      if (tanquesList.length === 0) {
        return `<div class="p-4 text-center ${isUnavailable ? 'text-rose-300' : 'text-slate-500'} font-sans text-xs">${isUnavailable ? 'Leitura de estoque e tanques indisponível por falha na fonte primária.' : 'Sem tanques auditados neste fechamento.'}</div>`;
      }

      const rows = tanquesList.map(t => {
        const isConf = t.status_anp?.includes('CONFORME');
        return `
          <div class="p-3.5 rounded-xl glass-subcard border border-white/5 space-y-2 font-sans text-xs">
            <div class="flex items-center justify-between">
              <span class="font-bold text-slate-100">TQ-${this.escapeHtml(t.codtan ?? 'N/D')} • ${this.escapeHtml(t.combustivel ?? 'N/D')}</span>
              <span class="px-2.5 py-0.5 rounded text-[10px] font-semibold inline-flex items-center gap-1 ${isConf ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30' : 'bg-rose-500/15 text-rose-300 border border-rose-500/30'}">
                ${isConf ? `${CHAT_ICONS.check} Conforme ANP` : `${CHAT_ICONS.alert} Alerta ANP`}
              </span>
            </div>
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] text-slate-300 pt-1 border-t border-slate-800">
              <div><span class="text-slate-400">Capacidade:</span> <span class="tabular-nums">${this.formatLiters(t.capacidade_litros, 0)}</span></div>
              <div><span class="text-slate-400">Saldo Inicial:</span> <span class="tabular-nums">${this.formatLiters(t.saldo_inicial, 0)}</span></div>
              <div><span class="text-slate-400">Saldo Final:</span> <span class="tabular-nums">${this.formatLiters(t.saldo_final, 0)}</span></div>
              <div><span class="text-slate-400">Saída Bicos:</span> <span class="tabular-nums">${this.formatLiters(t.saida_bicos_litros, 1)}</span></div>
            </div>
          </div>
        `;
      }).join('');

      return `<div class="space-y-3 font-sans">${rows}</div>`;
    }

    // =========================================================================
    // ABA PADRÃO: RESUMO & FONTES DE DADOS
    // =========================================================================
    if (intent === 'vendas_analitico' || intent === 'consultar_analise_vendas_erp') {
      const rHoje = data.resumo_hoje || {};
      const ult = data.ultimo_produto_vendido_destaque || {};
      const fatHoje = Number(rHoje.faturamento_conveniencia_hoje || 0) + Number(rHoje.faturamento_combustivel_hoje || 0);
      return `
        <div class="space-y-4 font-sans text-xs">
          <div class="evidence-section-card">
            <h4 class="font-bold text-slate-100 flex items-center gap-2">
              <span class="inline-flex text-cyan-400">${CHAT_ICONS.chart}</span><span>Resumo da Operação Hoje (${this.escapeHtml(rHoje.data || 'Hoje')})</span>
            </h4>
            <div class="grid grid-cols-2 gap-2.5 pt-2">
              <div class="p-3 rounded-xl glass-subcard border border-white/5">
                <span class="text-slate-400 text-[11px] block">Faturamento Hoje:</span>
                <strong class="text-emerald-400 text-sm tabular-nums">${this.formatBRL(fatHoje)}</strong>
              </div>
              <div class="p-3 rounded-xl glass-subcard border border-white/5">
                <span class="text-slate-400 text-[11px] block">Conveniência:</span>
                <strong class="text-cyan-300 text-sm tabular-nums">${this.formatBRL(rHoje.faturamento_conveniencia_hoje || 0)}</strong>
                <span class="text-[10px] text-slate-400 block">${rHoje.pedidos_conveniencia_hoje || 0} pedidos</span>
              </div>
              <div class="p-3 rounded-xl glass-subcard border border-white/5">
                <span class="text-slate-400 text-[11px] block">Pista / Litros:</span>
                <strong class="text-slate-100 text-sm tabular-nums">${this.formatLiters(rHoje.litros_hoje || 0, 1)}</strong>
                <span class="text-[10px] text-slate-400 block">${rHoje.abastecimentos_hoje || 0} abastecimentos</span>
              </div>
              <div class="p-3 rounded-xl glass-subcard border border-white/5">
                <span class="text-slate-400 text-[11px] block">Receita Pista:</span>
                <strong class="text-cyan-300 text-sm tabular-nums">${this.formatBRL(rHoje.faturamento_combustivel_hoje || 0)}</strong>
              </div>
            </div>
          </div>

          ${ult.produto ? `
            <div class="evidence-section-card">
              <h4 class="font-bold text-slate-100 flex items-center gap-2">
                <span class="inline-flex text-purple-400">${CHAT_ICONS.store}</span><span>Última Venda Registrada (${this.escapeHtml(ult.origem || 'PDV')})</span>
              </h4>
              <div class="p-3 rounded-xl glass-subcard border border-white/5 space-y-1">
                <div class="flex items-center justify-between">
                  <strong class="text-slate-100">${this.escapeHtml(ult.produto)} (SKU: ${this.escapeHtml(ult.codigo_sku)})</strong>
                  <strong class="text-emerald-300 tabular-nums">${this.formatBRL(ult.valor_total)}</strong>
                </div>
                <div class="text-slate-400 text-[11px]">Horário: ${this.escapeHtml(ult.data_hora)} • Cupom: ${this.escapeHtml(ult.cupom)} (PDV ${this.escapeHtml(ult.pdv)})</div>
              </div>
            </div>
          ` : ''}

          <div class="p-3.5 rounded-xl glass-subcard border border-white/5 text-[10px] text-slate-500 flex items-center justify-between">
            <span>Fonte: ERP Posto 01 (PostgreSQL 16) • Automação CBC04</span>
            <span>Status: Sincronizado</span>
          </div>
        </div>
      `;
    }

    const sourcesList = sources.map(s => {
      let stBadge = `<span class="text-emerald-400 font-semibold inline-flex items-center gap-1">${CHAT_ICONS.check} Disponível</span>`;
      if (s.availability === 'missing') stBadge = `<span class="text-amber-400 font-semibold inline-flex items-center gap-1">${CHAT_ICONS.clock} Pendente / Não lançado</span>`;
      if (s.availability === 'unavailable') stBadge = `<span class="text-rose-400 font-semibold inline-flex items-center gap-1">${CHAT_ICONS.alert} Indisponível</span>`;

      return `
        <div class="p-3.5 rounded-xl glass-subcard border border-white/5 flex items-center justify-between font-sans text-xs">
          <div>
            <div class="font-bold text-slate-200">${this.escapeHtml(s.label)}</div>
            <div class="text-[10px] text-slate-400">Atualização: ${s.data_as_of ? this.escapeHtml(s.data_as_of) : 'Tempo real'}</div>
          </div>
          <div>${stBadge}</div>
        </div>
      `;
    }).join('');

    const explanationText = c.explanation?.text || data.resumo_executivo?.diagnostico || data.resumo_executivo?.diagnostico_caixa || 'Auditoria executada conforme regras vigentes.';
    const limText = assessment.limitation || data.resumo_executivo?.limitation || null;

    return `
      <div class="space-y-4 font-sans text-xs">
        <div class="evidence-section-card">
          <h4 class="font-bold text-slate-100 flex items-center gap-2">
            <span class="inline-flex text-cyan-400">${CHAT_ICONS.pulse}</span><span>Proveniência e Disponibilidade das Fontes</span>
          </h4>
          <div class="space-y-2">${sourcesList || '<div class="text-slate-500 font-sans">Fontes padrão do ERP (Somente Leitura)</div>'}</div>
        </div>

        <div class="evidence-section-card">
          <h4 class="font-bold text-slate-100 flex items-center gap-2">
            <span class="inline-flex text-cyan-400">${CHAT_ICONS.audit}</span><span>Diagnóstico Executivo</span>
          </h4>
          <p class="text-slate-300 leading-relaxed text-xs p-3.5 rounded-xl glass-subcard border border-white/5 font-sans">
            ${this.escapeHtml(explanationText)}
          </p>
        </div>

        ${limText ? `
          <div class="evidence-section-card">
            <h4 class="font-bold text-slate-100 flex items-center gap-2">
              <span class="inline-flex text-amber-400">${CHAT_ICONS.alert}</span><span>Limitações e Premissas da Consulta</span>
            </h4>
            <p class="text-amber-200/90 leading-relaxed text-xs p-3.5 rounded-xl bg-amber-950/20 border border-amber-500/20 font-sans">
              ${this.escapeHtml(limText)}
            </p>
          </div>
        ` : ''}

        <div class="p-3.5 rounded-xl glass-subcard border border-white/5 text-[10px] font-sans text-slate-500 flex items-center justify-between">
          <span>Contrato: ${this.escapeHtml(c.schema_version || '1.0')} (${this.escapeHtml(intent)})</span>
          <span>ID: ${this.escapeHtml(c.response_id || 'N/A')}</span>
        </div>
      </div>
    `;
  }

  /**
   * Widget 4: Card de Decisão Executiva para Combos & Vendas Cruzadas (Market Basket)
   * Implementação AURA Precision Glass v1.0 (F5-08).
   * Garante:
   * 1. Superfície única DecisionCard sem aninhamentos desnecessários.
   * 2. Destaque para regras com forte sinergia (Lift >= 2.0x) e confiança comprovada.
   * 3. Scripts práticos de balcão para o operador de caixa sem falsas promessas de ganho garantido (F5-08).
   * 4. Limitações de cupons analisados e premissas estatísticas transparentes.
   * 5. Ação de ativação do combo em 1 clique e drawer de regras completas.
   */
  renderCombosWidget(data) {
    if (!data || typeof data !== 'object') {
      return `<div class="decision-card"><p class="text-xs text-slate-400">Dados de combos e vendas cruzadas indisponíveis.</p></div>`;
    }

    const c = data.contrato || data;

    // F1-08 / F5-01: Versão desconhecida de contrato tratada com segurança
    if (c.schema_version && c.schema_version !== '1.0') {
      return this.renderUnsupportedSchemaCard(c.schema_version, 'Combos & Conveniência');
    }

    const assessment = c.assessment || {};
    const metrics = c.metrics || {};
    const pendingItems = c.pending_items || [];
    const action = c.recommended_action || {};
    const resumo = data.resumo_executivo || {};
    const combos = c.top_combos || data.top_combos_cross_selling || data.top_combos_oportunidades || data.regras_associacao_detalhadas || [];
    const isUnavailable = this.isSourceUnavailable(data, assessment);
    const isNoMovement = !isUnavailable && (assessment.status_code === 'SEM_REGISTROS' || data.status === 'sem_movimento' || assessment.status_code === 'SEM_MOVIMENTACAO');

    if (isUnavailable) {
      return this.renderContingencyCard('Combos & Vendas Cruzadas na Conveniência', data, 'Quais os combos de conveniência com maior afinidade?');
    }

    const evId = 'ev_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7);
    if (typeof window !== 'undefined') {
      if (!window.__auraEvidenceStore) window.__auraEvidenceStore = {};
      window.__auraEvidenceStore[evId] = data;
    }

    // Métricas Canônicas
    const maxLiftVal = assessment.maior_lift ?? metrics.maior_lift ?? resumo.maior_lift_encontrado ?? (combos[0]?.lift ?? combos[0]?.metricas?.lift ?? 0.0);
    const countForteSinergia = assessment.regras_com_forte_sinergia_lift_2 ?? metrics.regras_forte_sinergia_count ?? resumo.regras_com_forte_sinergia_lift_2 ?? 0;
    const totalTransacoes = metrics.total_transacoes_analisadas ?? resumo.total_transacoes_analisadas ?? 0;
    const totalMultiplas = metrics.total_transacoes_multiplos_itens ?? resumo.total_transacoes_multiplos_itens ?? 0;
    const pctMultiplas = metrics.pct_cestas_multiplos_itens ?? resumo.pct_cestas_multiplos_itens ?? 0.0;
    const ticketMedioLoja = metrics.ticket_medio_reais ?? resumo.ticket_medio_conveniencia ?? 0.0;
    const totalSkus = metrics.total_itens_distintos ?? resumo.total_itens_distintos_conveniencia ?? 0;
    const totalRegras = metrics.total_regras_geradas ?? resumo.total_regras_geradas ?? combos.length;

    // Badges Semânticos
    let badgeClass = 'status-validated';
    let badgeIcon = CHAT_ICONS.pulse;
    let badgeText = assessment.badge_label || `Max Lift: ${parseFloat(maxLiftVal).toFixed(2)}x`;

    if (isUnavailable) {
      badgeClass = 'status-divergent';
      badgeIcon = CHAT_ICONS.alert;
      badgeText = 'Fonte Indisponível';
    } else if (isNoMovement) {
      badgeClass = 'status-neutral';
      badgeIcon = CHAT_ICONS.pause;
      badgeText = 'Sem Cupons';
    } else if (countForteSinergia > 0) {
      badgeClass = 'status-validated';
      badgeIcon = CHAT_ICONS.pulse;
      badgeText = assessment.badge_label || `Max Lift: ${parseFloat(maxLiftVal).toFixed(2)}x`;
    } else if (totalMultiplas === 0) {
      badgeClass = 'status-partial';
      badgeIcon = CHAT_ICONS.alert;
      badgeText = 'Cestas sem Multiplicidade';
    } else {
      badgeClass = 'status-neutral';
      badgeIcon = CHAT_ICONS.check;
      badgeText = 'Regras Mineradas';
    }

    // Hero Metric: Maior Lift
    const heroLabel = 'Maior Multiplicador de Sinergia (Lift)';
    const heroVal = isNoMovement || isUnavailable ? '-' : `${parseFloat(maxLiftVal).toFixed(2)}x`;
    const heroColorClass = isNoMovement || isUnavailable ? 'text-slate-400' : (parseFloat(maxLiftVal) >= 2.0 ? 'text-purple-300' : 'text-emerald');
    let heroSub = `${countForteSinergia} combo(s) com forte sinergia (Lift ≥ 2.0x) • ${totalTransacoes} cupons analisados (${parseFloat(pctMultiplas).toFixed(1)}% cestas múltiplas).`;
    if (isUnavailable) {
      heroSub = 'Dados de cupons e cestas de conveniência temporariamente indisponíveis no PDV.';
    }

    // Bloco de Limitação (F5-02 & F5-08 / F6-01)
    let limitationHtml = '';
    const limText = assessment.limitation || resumo.limitation;
    if (isUnavailable) {
      limitationHtml = `
        <div class="decision-limitation-callout border-rose-500/30 bg-rose-950/20 text-rose-200/90">
          <span class="inline-flex text-rose-400">${CHAT_ICONS.alert}</span>
          <div>
            <strong class="font-semibold text-rose-300">Contingência Operacional:</strong>
            <span class="text-rose-200/90">${this.escapeHtml(limText || data.motivo || 'Vendas da loja de conveniência indisponíveis para mineração de regras.')}</span>
          </div>
        </div>
      `;
    } else if (limText && !isNoMovement) {
      limitationHtml = `
        <div class="decision-limitation-callout">
          <span class="inline-flex text-amber-400">${CHAT_ICONS.alert}</span>
          <div>
            <strong class="font-semibold">Premissa Estatística & Limitação:</strong>
            <span class="text-amber-200/90">${this.escapeHtml(limText)}</span>
          </div>
        </div>
      `;
    }

    // Top Combos Acionáveis
    let cardsHtml = '';
    combos.slice(0, 3).forEach(cItem => {
      const lift = parseFloat(cItem.lift ?? cItem.metricas?.lift ?? 1.5).toFixed(2);
      const conf = parseFloat(cItem.confianca_pct ?? (cItem.metricas?.confianca ? cItem.metricas.confianca * 100 : cItem.confianca_percentual) ?? 50).toFixed(0);
      const cupons = cItem.cupons_conjuntos ?? cItem.metricas?.frequencia_conjunta ?? cItem.frequencia_conjunta_cupons ?? 0;
      const isForte = Boolean(cItem.forte_sinergia ?? (parseFloat(lift) >= 2.0));

      const prodOrig = typeof cItem.produto_origem === 'object' ? (cItem.produto_origem?.nompro || 'Item Origem') : (cItem.produto_origem || 'Item Origem');
      const prodDest = typeof cItem.produto_recomendado === 'object' ? (cItem.produto_recomendado?.nompro || 'Item Recomendado') : (cItem.produto_recomendado || 'Item Recomendado');
      const prodDestShort = String(prodDest).split(' ').slice(0, 2).join(' ');
      const script = cItem.script_sugerido_caixa || cItem.script_sugestao_pdv || 'Ofereça o combo ao registrar o item no caixa.';

      const pOrigVal = Number(cItem.ticket_origem_reais ?? cItem.impacto_financeiro?.preco_origem ?? 0);
      const pRecVal = Number(cItem.ticket_recomendado_reais ?? cItem.impacto_financeiro?.preco_recomendado ?? 0);
      const incrPct = pOrigVal > 0 ? ((pRecVal / pOrigVal) * 100).toFixed(1) : null;

      cardsHtml += `
        <div class="widget-combo-card font-sans">
          <div class="flex items-center justify-between text-xs mb-1">
            <span class="font-bold text-white flex items-center gap-1.5">
              <span>${isForte ? CHAT_ICONS.pulse : CHAT_ICONS.store}</span>
              <span>${this.escapeHtml(prodOrig)}</span>
            </span>
            <span class="text-purple-400 font-bold">➔</span>
            <span class="font-bold text-auraCyan-light">${this.escapeHtml(prodDest)}</span>
          </div>

          <div class="flex flex-wrap items-center gap-2 text-[10px] text-slate-400 my-1">
            <span class="px-2 py-0.5 rounded ${isForte ? 'bg-purple-500/25 text-purple-200 border-purple-500/40' : 'bg-slate-800 text-slate-300 border-slate-700'} font-bold border tabular-nums flex items-center gap-1">
              ${CHAT_ICONS.pulse}<span>Lift ${lift}x</span>
            </span>
            <span class="px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 tabular-nums flex items-center gap-1 font-semibold">
              ${CHAT_ICONS.target}<span>Confiança ${conf}%</span>
            </span>
            <span class="tabular-nums flex items-center gap-1">${CHAT_ICONS.box}<span>${cupons} cupons</span></span>
            ${pRecVal > 0 ? `<span class="text-emerald-400 font-semibold tabular-nums">+${this.formatBRL(pRecVal)}${incrPct ? ` (+${incrPct}%)` : ''}</span>` : ''}
          </div>

          <div class="widget-combo-script-box">
            <strong>${CHAT_ICONS.dialog}Script no Balcão:</strong> "${this.escapeHtml(script)}"
          </div>

          <div class="flex justify-end mt-2">
            <button type="button" class="widget-action-btn purple flex items-center gap-1" onclick="if (window.auraChat) window.auraChat.sendUserPrompt('Qual o estoque atual de ${this.escapeHtml(prodDest)}?');">
              ${CHAT_ICONS.box}<span>Checar Estoque</span> <span>(${this.escapeHtml(prodDestShort)})</span>
            </button>
          </div>
        </div>
      `;
    });

    // Bloco de Pendências
    let pendingHtml = '';
    if (pendingItems.length > 0) {
      const itemsList = pendingItems.map(p => `
        <div class="decision-pending-item cursor-pointer hover:bg-purple-500/10 transition-colors" onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'caixas');" title="Ver detalhes nas evidências">
          <div class="flex items-center gap-2">
            <span class="text-purple-400 font-bold">${CHAT_ICONS.alert}</span>
            <span class="font-semibold text-slate-200">${this.escapeHtml(p.label)}</span>
          </div>
          <span class="text-[10px] text-slate-400 font-sans flex items-center gap-1">
            <span>Combos</span>
            <span>↗</span>
          </span>
        </div>
      `).join('');

      pendingHtml = `
        <div class="space-y-1.5">
          <span class="text-[10px] font-sans uppercase tracking-wider text-slate-400 font-semibold">Oportunidades de Venda Cruzada:</span>
          <div class="decision-pending-list">${itemsList}</div>
        </div>
      `;
    }

    const recLabel = action.label || 'Ativar Combos Recomendados no Balcão';
    const dataConsulta = c.context?.queried_at ? new Date(c.context.queried_at).toLocaleDateString('pt-BR') : 'Data Recente';

    return `
      <div class="decision-card" data-evidence-id="${evId}">
        <!-- Context Header -->
        <div class="decision-header">
          <div class="decision-context">
            <span class="decision-context-title">${this.escapeHtml(assessment.title || 'Combos & Vendas Cruzadas (Conveniência)')}</span>
            <span class="decision-context-sub">
              <span>${CHAT_ICONS.calendar} ${this.escapeHtml(dataConsulta)}</span>
              <span>•</span>
              <span>${CHAT_ICONS.store} PDV / Cestas de Compras</span>
              <span>•</span>
              <span>${CHAT_ICONS.unit} ${this.escapeHtml(c.context?.unit_id || 'Loja')}</span>
            </span>
          </div>
          <span class="decision-status-badge ${badgeClass}">
            <span>${badgeIcon}</span>
            <span>${this.escapeHtml(badgeText)}</span>
          </span>
        </div>

        <!-- Hero Metric -->
        <div class="decision-hero">
          <div class="decision-hero-header">
            <span class="decision-hero-label">${this.escapeHtml(heroLabel)}</span>
            <span class="px-2.5 py-0.5 rounded text-[10px] font-sans font-semibold bg-purple-500/15 text-purple-300 border border-purple-500/30">
              ${countForteSinergia} Combos Fortes
            </span>
          </div>
          <div class="decision-hero-value ${heroColorClass} tabular-nums">
            ${heroVal}
          </div>
          <div class="decision-hero-sub">
            ${this.escapeHtml(heroSub)}
          </div>
        </div>

        ${limitationHtml}

        <!-- Comparativo Compacto -->
        ${(!isNoMovement && !isUnavailable) ? `
          <div class="decision-comparison-grid">
            <div class="decision-comp-item">
              <span class="decision-comp-label">Cestas Múltiplas</span>
              <strong class="decision-comp-val text-cyan-300 tabular-nums">${totalMultiplas} cupons</strong>
              <span class="decision-comp-sub tabular-nums">${parseFloat(pctMultiplas).toFixed(1)}% do total</span>
            </div>
            <div class="decision-comp-item">
              <span class="decision-comp-label">Ticket Médio Loja</span>
              <strong class="decision-comp-val text-slate-100 tabular-nums">${this.formatBRL(ticketMedioLoja)}</strong>
              <span class="decision-comp-sub tabular-nums">${totalSkus} SKUs minerados</span>
            </div>
            <div class="decision-comp-item">
              <span class="decision-comp-label">Regras Geradas</span>
              <strong class="decision-comp-val text-purple-300 tabular-nums">${totalRegras} regras</strong>
              <span class="decision-comp-sub tabular-nums">${countForteSinergia} com Lift ≥ 2.0x</span>
            </div>
          </div>
        ` : ''}

        <!-- Lista de Combos Destaque -->
        <div class="space-y-2 mt-1">
          ${isUnavailable ? '<div class="p-3 rounded-xl bg-slate-900/60 border border-rose-500/20 text-rose-300 text-xs font-sans">Mineração de combos suspensa por indisponibilidade da fonte.</div>' : (cardsHtml || '<div class="text-xs font-sans text-slate-400">Nenhum combo com o filtro solicitado retornado.</div>')}
        </div>

        ${pendingHtml}

        <!-- Ações Permitidas -->
        <div class="decision-actions">
          ${isUnavailable ? `
            <button 
              type="button" 
              class="decision-btn-primary" 
              onclick="if (window.auraChat) window.auraChat.sendUserPrompt('Quais os combos de conveniência com maior afinidade?');"
              title="Tentar executar a consulta novamente">
              <span>${CHAT_ICONS.refresh}</span>
              <span>Tentar Novamente</span>
            </button>
            <button 
              type="button" 
              class="decision-btn-secondary" 
              onclick="if (window.auraChat) window.auraChat.sendUserPrompt('Como auditar vendas de conveniência em contingência?');"
              title="Procedimento de contingência">
              <span>${CHAT_ICONS.wrench}</span>
              <span>Procedimento de Contingência</span>
            </button>
          ` : `
            <button 
              type="button" 
              class="decision-btn-primary" 
              onclick="if (window.auraChat) window.auraChat.sendUserPrompt('Quais os scripts de balcão recomendados para a equipe do caixa?');"
              title="Capacitar operadores com roteiro persuasivo no PDV">
              ${CHAT_ICONS.store}
              <span>${this.escapeHtml(recLabel)}</span>
            </button>

            <button 
              type="button" 
              class="decision-btn-secondary" 
              onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'formula');"
              title="Ver definições matemáticas de Suporte, Confiança e Lift">
              ${CHAT_ICONS.formula}
              <span>Como foi calculado</span>
            </button>

            <button 
              type="button" 
              class="decision-btn-secondary" 
              onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'caixas');"
              title="Ver tabela detalhada de todas as regras mineradas">
              ${CHAT_ICONS.chart}
              <span>Ver Regras Detalhadas</span>
            </button>

            <button 
              type="button" 
              class="decision-btn-secondary" 
              onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'resumo');"
              title="Ver fontes de dados e diagnósticos">
              ${CHAT_ICONS.audit}
              <span>Resumo & Fontes</span>
            </button>
          `}
        </div>
      </div>
    `;
  }

  /**
   * Widget 5: Card de Decisão Executiva para Performance da Pista, Vazão de Bicos & Frentistas
   * Implementação AURA Precision Glass v1.0 (F5-05).
   * Garante:
   * 1. Superfície única DecisionCard sem aninhamentos desnecessários.
   * 2. Destaque para bicos com vazão lenta (< 30 L/min indicando manutenção preventiva).
   * 3. Ranking de frentistas com meta de conversão em aditivada (≥ 25%) e faturamento.
   * 4. Limitações operacionais de telemetria transparentes.
   * 5. Ação de agendamento de manutenção em 1 clique e drawer de evidências.
   */
  renderDesempenhoPistaWidget(data) {
    if (!data || typeof data !== 'object') {
      return `<div class="decision-card"><p class="text-xs text-slate-400">Dados de performance da pista indisponíveis.</p></div>`;
    }

    const c = data.contrato || data;

    // F1-08 / F5-01: Versão desconhecida de contrato tratada com segurança
    if (c.schema_version && c.schema_version !== '1.0') {
      return this.renderUnsupportedSchemaCard(c.schema_version, 'Performance da Pista');
    }

    const assessment = c.assessment || {};
    const metrics = c.metrics || {};
    const pendingItems = c.pending_items || [];
    const action = c.recommended_action || {};
    const resumo = data.resumo_executivo || {};
    const ranking = c.ranking || data.ranking_frentistas || [];
    const nozzles = c.nozzles || data.auditoria_vazao_bicos || data.vazao_bicos || [];

    const isUnavailable = this.isSourceUnavailable(data, assessment);
    const isNoMovement = !isUnavailable && (assessment.status_code === 'SEM_MOVIMENTACAO' || data.status === 'sem_movimento');

    if (isUnavailable) {
      return this.renderContingencyCard('Performance da Pista & Frentistas', data, 'Qual o desempenho da pista e vazão de bicos hoje?');
    }

    const evId = 'ev_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7);
    if (typeof window !== 'undefined') {
      if (!window.__auraEvidenceStore) window.__auraEvidenceStore = {};
      window.__auraEvidenceStore[evId] = data;
    }

    // Identificação de Bicos Lentos (< 30 L/min)
    const bicosAlerta = nozzles.filter(b => b.alerta_filtro_lento || b.alerta_vazao_lenta || b.alerta_filtro || b.alerta_vazao || parseFloat(b.vazao_media_l_min ?? b.vazao_litros_minuto ?? b.vazao_media_litros_minuto ?? 35) < 30.0);
    const bicosLentosCount = assessment.total_bicos_lentos ?? assessment.bicos_lentos_count ?? metrics.bicos_com_alerta_filtro ?? metrics.bicos_com_alerta_vazao_count ?? bicosAlerta.length;

    // Badges Semânticos com Ícone (F5-09)
    let badgeClass = 'status-validated';
    let badgeIcon = CHAT_ICONS.check;
    let badgeText = assessment.badge_label || (bicosLentosCount > 0 ? `${bicosLentosCount} Bicos Lentos (<30 L/min)` : 'Pista Operando Conforme');

    if (isUnavailable) {
      badgeClass = 'status-divergent';
      badgeIcon = CHAT_ICONS.alert;
      badgeText = 'Fonte Indisponível';
    } else if (isNoMovement) {
      badgeClass = 'status-neutral';
      badgeIcon = CHAT_ICONS.pause;
      badgeText = assessment.badge_label || 'Sem Movimentação';
    } else if (bicosLentosCount > 0) {
      badgeClass = 'status-partial';
      badgeIcon = CHAT_ICONS.alert;
      badgeText = assessment.badge_label || `${bicosLentosCount} Bicos Lentos (<30 L/min)`;
    } else {
      badgeClass = 'status-validated';
      badgeIcon = CHAT_ICONS.check;
      badgeText = assessment.badge_label || 'Pista Operando Conforme';
    }

    // Hero Metric: Faturamento da Pista
    const fatPista = Number(metrics.faturamento_total ?? metrics.faturamento_total_pista ?? resumo.faturamento_pista_total ?? 0);
    const liderNome = assessment.melhor_frentista_nome ?? resumo.campeao_faturamento?.nome ?? resumo.lider_faturamento ?? (ranking[0]?.nome || ranking[0]?.frentista || 'Colaborador');
    const liderObj = ranking[0] || {};
    const liderFat = Number(liderObj.faturamento_reais ?? 0);
    const liderAdit = parseFloat(liderObj.conversao_aditivada_pct ?? liderObj.percentual_aditivada ?? 0).toFixed(1);

    const heroLabel = 'Faturamento Total da Pista';
    const heroVal = isNoMovement || isUnavailable ? '-' : this.formatBRL(fatPista);
    const heroColorClass = isNoMovement || isUnavailable ? 'text-slate-400' : 'text-emerald';
    let heroSub = ranking.length > 0
      ? `Líder: ${liderNome} (${this.formatBRL(liderFat)}, Aditivada: ${liderAdit}%) • Ticket Médio da Pista: ${this.formatBRL(metrics.ticket_medio ?? metrics.ticket_medio_pista ?? resumo.ticket_medio_pista ?? 0)}.`
      : 'Sem abastecimentos registrados no período.';
    if (isUnavailable) {
      heroSub = 'Telemetria da pista e bicos temporariamente indisponível no concentrador.';
    }

    // Comparativo Compacto
    const volPista = Number(metrics.total_litros ?? metrics.volume_total_litros ?? resumo.volume_total_litros ?? 0);
    const txAditGlobal = parseFloat(metrics.taxa_conversao_aditivada_geral_pct ?? metrics.taxa_conversao_aditivada_global_pct ?? resumo.conversao_aditivada_geral_pct ?? 0).toFixed(1);
    const vazaoMedia = parseFloat(metrics.vazao_media_l_min ?? metrics.vazao_media_geral_litros_minuto ?? resumo.vazao_media_pista_litros_minuto ?? 34.5).toFixed(1);

    // Bloco de Limitação (F5-02 & F5-05 / F6-01)
    let limitationHtml = '';
    const limText = assessment.limitation || resumo.limitation;
    if (isUnavailable) {
      limitationHtml = `
        <div class="decision-limitation-callout border-rose-500/30 bg-rose-950/20 text-rose-200/90">
          <span class="inline-flex text-rose-400">${CHAT_ICONS.alert}</span>
          <div>
            <strong class="font-semibold text-rose-300">Contingência Operacional:</strong>
            <span class="text-rose-200/90">${this.escapeHtml(limText || data.motivo || 'Telemetria de pista e concentrador de bicos temporariamente indisponíveis.')}</span>
          </div>
        </div>
      `;
    } else if (limText && !isNoMovement) {
      limitationHtml = `
        <div class="decision-limitation-callout">
          <span class="inline-flex text-amber-400">${CHAT_ICONS.alert}</span>
          <div>
            <strong class="font-semibold">Premissa Operacional & Telemetria:</strong>
            <span class="text-amber-200/90">${this.escapeHtml(limText)}</span>
          </div>
        </div>
      `;
    }

    // Ranking de Frentistas (Top 3)
    let frentsHtml = '';
    ranking.slice(0, 3).forEach((f, idx) => {
      const rankBadge = idx === 0
        ? '<span class="inline-flex items-center justify-center w-5 h-5 rounded-md text-[10px] font-bold bg-amber-400/20 text-amber-300 border border-amber-400/40">#1</span>'
        : idx === 1
          ? '<span class="inline-flex items-center justify-center w-5 h-5 rounded-md text-[10px] font-bold bg-slate-300/20 text-slate-200 border border-slate-300/40">#2</span>'
          : '<span class="inline-flex items-center justify-center w-5 h-5 rounded-md text-[10px] font-bold bg-amber-700/20 text-amber-500 border border-amber-600/40">#3</span>';
      const nomeFrent = f.nome || f.frentista || 'Colaborador';
      const fat = this.formatBRL(f.faturamento_reais || 0);
      const aditVal = parseFloat(f.conversao_aditivada_pct ?? f.percentual_aditivada ?? 0);
      const isMeta = aditVal >= 25.0;
      const atends = f.total_abastecimentos ?? f.atendimentos_count ?? 0;

      frentsHtml += `
        <div class="flex items-center justify-between p-2 rounded-xl bg-slate-900/60 border border-slate-800 text-xs font-sans">
          <div class="flex items-center gap-2 font-bold text-white">
            ${rankBadge}
            <span>${this.escapeHtml(nomeFrent)}</span>
            ${atends > 0 ? `<span class="text-[10px] text-slate-500 font-normal">(${atends} atends)</span>` : ''}
          </div>
          <div class="flex items-center gap-3">
            <span class="text-slate-200 font-semibold tabular-nums">${fat}</span>
            <span class="px-1.5 py-0.5 rounded text-[10px] font-semibold tabular-nums ${isMeta ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30' : 'bg-amber-500/15 text-amber-300 border border-amber-500/30'}">
              Adit: ${aditVal.toFixed(1)}%
            </span>
          </div>
        </div>
      `;
    });

    // Alerta de Vazão Lenta nos Bicos (< 30 L/min)
    let bicosAlertHtml = '';
    if (bicosAlerta.length > 0) {
      bicosAlertHtml = `
        <div class="p-3 rounded-xl bg-amber-950/25 border border-amber-500/30 text-amber-300 text-xs font-sans space-y-1.5">
          <div class="flex items-center gap-2 font-bold text-amber-400">
            <span class="inline-flex">${CHAT_ICONS.alert}</span>
            <span class="uppercase tracking-wider text-[11px]">Bicos com Alerta de Vazão Lenta (&lt; 30 L/min):</span>
          </div>
          <p class="text-[10px] text-slate-300">
            Vazão reduzida prejudica a produtividade da pista e aponta necessidade de troca de elemento filtrante ou ajuste na unidade de sucção:
          </p>
          <div class="space-y-1 pt-1">
            ${bicosAlerta.map(b => {
              const vazao = parseFloat(b.vazao_media_l_min ?? b.vazao_litros_minuto ?? b.vazao_media_litros_minuto ?? 0).toFixed(1);
              const prod = b.combustivel || b.produto_nome || 'Combustível';
              return `<div class="flex items-center justify-between text-[11px] p-1 rounded bg-slate-900/60 border border-amber-500/20 font-sans">
                <span>Bico <strong>${b.bico}</strong> (${this.escapeHtml(prod)})</span>
                <strong class="text-rose-400 tabular-nums">${vazao} L/min</strong>
              </div>`;
            }).join('')}
          </div>
        </div>
      `;
    }

    // Bloco de Pendências
    let pendingHtml = '';
    if (pendingItems.length > 0) {
      const itemsList = pendingItems.map(p => `
        <div class="decision-pending-item cursor-pointer hover:bg-amber-500/10 transition-colors" onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'bicos');" title="Ver detalhes nas evidências">
          <div class="flex items-center gap-2">
            <span class="text-amber-400 font-bold inline-flex">${CHAT_ICONS.wrench}</span>
            <span class="font-semibold text-slate-200">${this.escapeHtml(p.label)}</span>
          </div>
          <span class="text-[10px] text-slate-400 font-sans flex items-center gap-1">
            <span>Bicos</span>
            <span>↗</span>
          </span>
        </div>
      `).join('');

      pendingHtml = `
        <div class="space-y-1.5">
          <span class="text-[10px] font-sans uppercase tracking-wider text-slate-400 font-semibold">Pendências Operacionais:</span>
          <div class="decision-pending-list">${itemsList}</div>
        </div>
      `;
    }

    const recLabel = action.label || (bicosLentosCount > 0 ? 'Agendar Manutenção de Filtro nos Bicos Lentos' : 'Incentivar Conversão em Aditivada');
    const dataConsulta = c.context?.data_auditada || (c.context?.queried_at ? new Date(c.context.queried_at).toLocaleDateString('pt-BR') : 'Data Recente');

    return `
      <div class="decision-card" data-evidence-id="${evId}">
        <!-- Context Header -->
        <div class="decision-header">
          <div class="decision-context">
            <span class="decision-context-title">${this.escapeHtml(assessment.title || 'Performance da Pista & Frentistas')}</span>
            <span class="decision-context-sub">
              <span>${CHAT_ICONS.calendar} ${this.escapeHtml(dataConsulta)}</span>
              <span>•</span>
              <span>${CHAT_ICONS.nozzle} ${nozzles.length} Bicos Monitorados</span>
              <span>•</span>
              <span>${CHAT_ICONS.unit} ${this.escapeHtml(c.context?.unit_id || 'Posto')}</span>
            </span>
          </div>
          <span class="decision-status-badge ${badgeClass}">
            <span>${badgeIcon}</span>
            <span>${this.escapeHtml(badgeText)}</span>
          </span>
        </div>

        <!-- Hero Metric -->
        <div class="decision-hero">
          <div class="decision-hero-header">
            <span class="decision-hero-label">${this.escapeHtml(heroLabel)}</span>
            <span class="px-2.5 py-0.5 rounded text-[10px] font-sans font-semibold bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
              Líder: ${this.escapeHtml(liderNome)}
            </span>
          </div>
          <div class="decision-hero-value ${heroColorClass} tabular-nums">
            ${heroVal}
          </div>
          <div class="decision-hero-sub">
            ${this.escapeHtml(heroSub)}
          </div>
        </div>

        ${limitationHtml}

        <!-- Comparativo Compacto -->
        ${(!isNoMovement && !isUnavailable) ? `
          <div class="decision-comparison-grid">
            <div class="decision-comp-item">
              <span class="decision-comp-label">Volume Total</span>
              <strong class="decision-comp-val text-cyan-300 tabular-nums">${this.formatLiters(volPista, 1)}</strong>
              <span class="decision-comp-sub tabular-nums">${ranking.length} frentistas ativos</span>
            </div>
            <div class="decision-comp-item">
              <span class="decision-comp-label">Conversão Aditivada</span>
              <strong class="decision-comp-val ${parseFloat(txAditGlobal) >= 25.0 ? 'text-emerald-400' : 'text-amber-300'} tabular-nums">
                ${txAditGlobal}%
              </strong>
              <span class="decision-comp-sub">Meta da pista: ≥ 25.0%</span>
            </div>
            <div class="decision-comp-item">
              <span class="decision-comp-label">Vazão Média Geral</span>
              <strong class="decision-comp-val ${parseFloat(vazaoMedia) >= 30.0 ? 'text-slate-100' : 'text-rose-400'} tabular-nums">
                ${vazaoMedia} L/min
              </strong>
              <span class="decision-comp-sub tabular-nums">${bicosLentosCount > 0 ? `${bicosLentosCount} em alerta` : 'Todos conforme'}</span>
            </div>
          </div>
        ` : ''}

        <!-- Ranking de Frentistas -->
        <div class="space-y-1.5 mt-1 font-sans">
          <span class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">Podium de Performance da Pista:</span>
          ${isUnavailable ? '<div class="p-3 rounded-xl bg-slate-900/60 border border-rose-500/20 text-rose-300 text-xs font-sans">Leitura individual de frentistas suspensa por indisponibilidade da fonte.</div>' : (frentsHtml || '<div class="text-xs text-slate-400">Nenhum frentista retornado.</div>')}
        </div>

        ${bicosAlertHtml}
        ${pendingHtml}

        <!-- Ações Permitidas -->
        <div class="decision-actions">
          ${isUnavailable ? `
            <button 
              type="button" 
              class="decision-btn-primary" 
              onclick="if (window.auraChat) window.auraChat.sendUserPrompt('Qual o desempenho da pista e vazão de bicos hoje?');"
              title="Tentar executar a consulta novamente">
              <span>${CHAT_ICONS.refresh}</span>
              <span>Tentar Novamente</span>
            </button>
            <button 
              type="button" 
              class="decision-btn-secondary" 
              onclick="if (window.auraChat) window.auraChat.sendUserPrompt('Como auditar vazão de bicos manualmente em contingência?');"
              title="Procedimento de contingência">
              <span>${CHAT_ICONS.wrench}</span>
              <span>Procedimento de Contingência</span>
            </button>
          ` : `
            <button 
              type="button" 
              class="decision-btn-primary" 
              onclick="if (window.auraChat) window.auraChat.sendUserPrompt('Como programar a manutenção preventiva dos filtros de bicos de combustíveis?');"
              title="Abrir diretrizes de manutenção de bicos e bombas">
              <span class="text-xs inline-flex">${CHAT_ICONS.wrench}</span>
              <span>${this.escapeHtml(recLabel)}</span>
            </button>

            <button 
              type="button" 
              class="decision-btn-secondary" 
              onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'formula');"
              title="Ver fórmulas de vazão e conversão de aditivada">
              <span class="text-xs inline-flex">${CHAT_ICONS.formula}</span>
              <span>Como foi calculado</span>
            </button>

            <button 
              type="button" 
              class="decision-btn-secondary" 
              onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'bicos');"
              title="Ver detalhamento de todos os bicos da pista">
              <span class="text-xs inline-flex">${CHAT_ICONS.nozzle}</span>
              <span>Ver Bicos & Pista</span>
            </button>

            <button 
              type="button" 
              class="decision-btn-secondary" 
              onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'resumo');"
              title="Ver fontes de dados e diagnósticos">
              <span class="text-xs inline-flex">${CHAT_ICONS.audit}</span>
              <span>Resumo & Fontes</span>
            </button>
          `}
        </div>
      </div>
    `;
  }

  /**
   * Renderizador Especializado: Histórico de Vendas, PDV e Pista (AURA Precision Glass)
   * Renderiza DecisionCard executivo com métricas de hoje, último produto vendido,
   * top 5 mais vendidos e integração com EvidenceDrawer.
   */
  renderVendasAnaliticoWidget(data) {
    if (!data || typeof data !== 'object') return '';
    if (this.isSourceUnavailable(data)) {
      return this.renderContingencyCard('Histórico & Projeção de Vendas', data, 'Qual a análise de vendas e faturamento de hoje?');
    }

    const c = data.contrato || data;
    const resumoHoje = data.resumo_hoje || {};
    const ultimoProd = data.ultimo_produto_vendido_destaque || {};
    const topProds = data.produtos_mais_vendidos || [];
    const resumoGeral = data.resumo_geral || {};

    const dataHoje = resumoHoje.data || new Date().toISOString().split('T')[0];
    const dataFormatada = this.formatDateBR(dataHoje);

    const abastHoje = Number(resumoHoje.abastecimentos_hoje || 0);
    const litrosHoje = Number(resumoHoje.litros_hoje || 0);
    const fatCombHoje = Number(resumoHoje.faturamento_combustivel_hoje || 0);

    const pedConvHoje = Number(resumoHoje.pedidos_conveniencia_hoje || 0);
    const fatConvHoje = Number(resumoHoje.faturamento_conveniencia_hoje || 0);

    const fatTotalHoje = fatCombHoje + fatConvHoje;
    const temMovimentoHoje = (fatTotalHoje > 0 || abastHoje > 0 || pedConvHoje > 0);

    const heroValor = temMovimentoHoje ? fatTotalHoje : Number(resumoGeral.faturamento_total || 0);
    const heroLabel = temMovimentoHoje ? 'Faturamento Consolidado Hoje' : 'Faturamento Histórico Acumulado';
    const heroSub = temMovimentoHoje
      ? `${pedConvHoje} pedidos na loja • ${abastHoje} abastecimentos na pista`
      : `${resumoGeral.total_abastecimentos || 0} abastecimentos históricos registrados`;

    const statusBadge = temMovimentoHoje
      ? `<span class="decision-status-badge status-adherent"><span>${CHAT_ICONS.check}</span><span>Operação Ativa</span></span>`
      : `<span class="decision-status-badge status-neutral"><span>${CHAT_ICONS.telemetry}</span><span>Dados Apurados</span></span>`;

    // Evidências
    const evId = 'ev_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7);
    if (typeof window !== 'undefined') {
      if (!window.__auraEvidenceStore) window.__auraEvidenceStore = {};
      window.__auraEvidenceStore[evId] = {
        ...data,
        intent: 'vendas_analitico',
        context: { unit_id: 'posto_01', data_auditada: dataHoje }
      };
    }

    // Top produtos list
    let topProdsHtml = '';
    if (topProds && topProds.length > 0) {
      const items = topProds.slice(0, 3).map((p, idx) => {
        const nome = p.nompro || 'Produto';
        const qtd = Number(p.qtd_total || 0);
        const rec = Number(p.receita_total || 0);
        return `
          <div class="p-2 rounded-lg bg-white/[0.02] border border-white/5 flex items-center justify-between text-xs font-sans">
            <div class="flex items-center gap-2 truncate">
              <span class="w-4 h-4 rounded-full bg-cyan-500/10 text-cyan-400 text-[10px] flex items-center justify-center font-bold font-mono">${idx + 1}</span>
              <span class="text-slate-200 truncate font-medium">${this.escapeHtml(nome)}</span>
            </div>
            <div class="text-right flex-shrink-0 ml-2">
              <span class="text-emerald-300 font-semibold tabular-nums">${this.formatBRL(rec)}</span>
              <span class="text-[10px] text-slate-400 block tabular-nums">${qtd} un/L</span>
            </div>
          </div>
        `;
      }).join('');

      topProdsHtml = `
        <div class="space-y-1.5 pt-1">
          <div class="flex items-center justify-between text-[11px] font-sans text-slate-400 font-semibold uppercase tracking-wider">
            <span>Mais Vendidos (Líderes)</span>
            <span class="text-[10px] text-cyan-400 cursor-pointer hover:underline" onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'tanques');">Ver ranking completo ↗</span>
          </div>
          <div class="space-y-1">${items}</div>
        </div>
      `;
    }

    // Último produto destaque
    let ultimoProdHtml = '';
    if (ultimoProd && ultimoProd.produto) {
      const pNome = ultimoProd.produto;
      const pOrigem = ultimoProd.origem || 'PDV';
      const pHora = ultimoProd.data_hora ? String(ultimoProd.data_hora).split(' ')[1] || ultimoProd.data_hora : '';
      const pTotal = Number(ultimoProd.valor_total || 0);

      ultimoProdHtml = `
        <div class="p-2.5 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-between text-xs font-sans">
          <div class="flex items-center gap-2">
            <span class="p-1 rounded-lg bg-purple-500/20 text-purple-300">${CHAT_ICONS.store}</span>
            <div>
              <div class="text-[10px] text-purple-300 font-semibold uppercase">Última Venda • ${this.escapeHtml(pOrigem)}</div>
              <div class="text-slate-100 font-bold truncate max-w-[200px] sm:max-w-xs">${this.escapeHtml(pNome)}</div>
            </div>
          </div>
          <div class="text-right">
            <div class="text-emerald-300 font-bold tabular-nums">${this.formatBRL(pTotal)}</div>
            <div class="text-[10px] text-slate-400">${this.escapeHtml(pHora)}</div>
          </div>
        </div>
      `;
    }

    return `
      <div class="decision-card" data-evidence-id="${evId}">
        <!-- Topo do Card -->
        <div class="decision-header">
          <div class="decision-context">
            <span class="decision-context-title">Diagnóstico de Vendas & Faturamento</span>
            <span class="decision-context-sub">
              <span>${CHAT_ICONS.calendar} ${this.escapeHtml(dataFormatada)}</span>
              <span>•</span>
              <span>${CHAT_ICONS.unit} Posto 01</span>
              <span>•</span>
              <span>${CHAT_ICONS.telemetry} Pista + PDV</span>
            </span>
          </div>
          ${statusBadge}
        </div>

        <!-- Hero Metric -->
        <div class="decision-hero">
          <div class="decision-hero-header">
            <span class="decision-hero-label">${this.escapeHtml(heroLabel)}</span>
            <span class="px-2 py-0.5 rounded text-[10px] font-sans font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">Receita Operacional</span>
          </div>
          <div class="decision-hero-value text-emerald-400 tabular-nums">
            ${this.formatBRL(heroValor)}
          </div>
          <div class="decision-hero-sub text-slate-300">
            ${this.escapeHtml(heroSub)}
          </div>
        </div>

        <!-- Grade de Comparativo Pista vs Loja -->
        <div class="decision-comparison-grid">
          <div class="decision-comp-item">
            <span class="decision-comp-label">Loja de Conveniência</span>
            <strong class="decision-comp-val text-emerald-300 tabular-nums">${this.formatBRL(fatConvHoje)}</strong>
            <span class="decision-comp-sub">${pedConvHoje} pedidos hoje</span>
          </div>
          <div class="decision-comp-item">
            <span class="decision-comp-label">Pista de Combustíveis</span>
            <strong class="decision-comp-val text-cyan-300 tabular-nums">${this.formatBRL(fatCombHoje)}</strong>
            <span class="decision-comp-sub">${this.formatLiters(litrosHoje, 1)} hoje</span>
          </div>
          <div class="decision-comp-item">
            <span class="decision-comp-label">Volume de Pista</span>
            <strong class="decision-comp-val text-slate-100 tabular-nums">${abastHoje}</strong>
            <span class="decision-comp-sub">abastecimentos</span>
          </div>
        </div>

        ${ultimoProdHtml}
        ${topProdsHtml}

        <!-- Ações do Card -->
        <div class="decision-actions">
          <button 
            type="button" 
            class="decision-btn-primary" 
            onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'resumo');"
            title="Abrir extrato analítico com cupons e histórico">
            ${CHAT_ICONS.audit}
            <span>Extrato Completo de Vendas ↗</span>
          </button>

          <button 
            type="button" 
            class="decision-btn-secondary" 
            onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'caixas');"
            title="Ver cupons fiscais da conveniência">
            ${CHAT_ICONS.store}
            <span>Cupons da Loja</span>
          </button>

          <button 
            type="button" 
            class="decision-btn-secondary" 
            onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'bicos');"
            title="Ver histórico de abastecimentos da pista">
            ${CHAT_ICONS.nozzle}
            <span>Abastecimentos Pista</span>
          </button>
        </div>
      </div>
    `;
  }

  /**
   * Widget Genérico para outras ferramentas analíticas
   */
  renderGenericToolWidget(toolName, data) {
    if (!data || typeof data !== 'object') return '';
    if (this.isSourceUnavailable(data)) {
      return this.renderContingencyCard(this.formatToolDisplayName(toolName), data);
    }
    if (!data.resumo_executivo && !data.status) return '';
    const r = data.resumo_executivo || data;
    const displayName = this.formatToolDisplayName(toolName);
    const rawMsg = String(r.mensagem || r.descricao || '').trim();
    const isTechStatus = !rawMsg || ['ok', 'success', 'true', 'done', 'ready'].includes(rawMsg.toLowerCase());
    const displayMsg = isTechStatus ? 'Dados operacionais apurados com sucesso junto ao ERP.' : rawMsg;
    return `
      <div class="widget-inline-container border-l-4 border-l-cyan-600">
        <div class="widget-inline-header">
          <div class="flex items-center gap-2">
            <span class="inline-flex">${CHAT_ICONS.chart}</span>
            <strong class="text-xs font-sans text-white uppercase tracking-wider font-semibold">Diagnóstico: ${this.escapeHtml(displayName)}</strong>
          </div>
          <span class="px-2 py-0.5 rounded text-[10px] font-sans font-medium bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">Apurado</span>
        </div>
        <div class="text-xs font-sans text-slate-300">
          ${this.escapeHtml(displayMsg)}
        </div>
      </div>
    `;
  }

  /**
   * Extrai e protege blocos de código (``` e `) com tokens neutros
   * para evitar corrupção durante transformações de BBCode, sublinhado e sanitização.
   */
  extractCodeBlocks(text) {
    const codeSnippets = [];
    const protectedText = text.replace(/(```[\s\S]*?```|`[^`\r\n]+`)/g, (match) => {
      const placeholder = `XAURACODE${codeSnippets.length}END`;
      codeSnippets.push(match);
      return placeholder;
    });
    return { protectedText, codeSnippets };
  }

  /**
   * Restaura os blocos de código originais após processamento de Markdown e estilos.
   */
  restoreCodeBlocks(text, codeSnippets) {
    if (!codeSnippets || codeSnippets.length === 0) return text;
    return text.replace(/XAURACODE(\d+)END/g, (match, idx) => {
      const code = codeSnippets[Number(idx)];
      return code !== undefined ? code : match;
    });
  }

  /**
   * Balanceia tags abertas e marcadores em streaming para evitar quebras de layout
   * ou vazamento de estilos durante a digitação token-a-token.
   * Utiliza pilha unificada LIFO para garantir aninhamento sem cruzamento de tags.
   */
  balanceStreamingText(text) {
    if (!text) return '';
    let balanced = text;

    // Remove tags incompletas que estejam sendo ativamente digitadas no final da string.
    // Preserva operadores matemáticos como "< 15" e citações numéricas como "[1]".
    balanced = balanced.replace(/\[(\/?(?:badge-)?[a-zA-Z][a-zA-Z0-9_\-]*)$/, '');
    balanced = balanced.replace(/<(\/?[a-zA-Z]{1,6}(?:\s+[^>]*)?)$/, '');

    // Se houver bloco de código (```) não fechado, fecha temporariamente
    const codeBlockCount = (balanced.match(/```/g) || []).length;
    if (codeBlockCount % 2 !== 0) {
      balanced += '\n```';
    }

    // Se houver inline code (`) não fechado, fecha temporariamente
    const inlineTickMatches = (balanced.replace(/```[\s\S]*?```/g, '').match(/`/g) || []).length;
    if (inlineTickMatches % 2 !== 0) {
      balanced += '`';
    }

    // Pilha unificada LIFO para garantir aninhamento perfeito
    const stack = [];
    const tokenRegex = /(\*\*|__(?!\w)|(?<!\*)\*(?!\*)|\[(\/?)([a-zA-Z0-9_\-]+)\]|<(\/?)([a-zA-Z0-9]+)(?:\s+[^>]*)?>)/g;
    const bbTags = new Set([
      'verde', 'emerald', 'green', 'amarelo', 'amber', 'yellow', 'vermelho', 'rose', 'red', 'ciano', 'cyan', 'roxo', 'purple',
      'badge-verde', 'badge-emerald', 'badge-green', 'badge-amarelo', 'badge-amber', 'badge-yellow',
      'badge-vermelho', 'badge-rose', 'badge-red', 'badge-ciano', 'badge-cyan', 'badge-roxo', 'badge-purple', 'u'
    ]);
    const htmlTags = new Set(['span', 'u', 'strong', 'em', 'b', 'i', 'mark']);

    let match;
    while ((match = tokenRegex.exec(balanced)) !== null) {
      const full = match[0];

      if (full === '**') {
        const idx = stack.map(s => s.close).lastIndexOf('**');
        if (idx !== -1) stack.splice(idx, 1);
        else stack.push({ type: 'bold', close: '**' });
      } else if (full.startsWith('__')) {
        const idx = stack.map(s => s.close).lastIndexOf('__');
        if (idx !== -1) stack.splice(idx, 1);
        else stack.push({ type: 'underline', close: '__' });
      } else if (full === '*') {
        const idx = stack.map(s => s.close).lastIndexOf('*');
        if (idx !== -1) stack.splice(idx, 1);
        else stack.push({ type: 'italic', close: '*' });
      } else if (match[3]) {
        // BBCode
        const isClosing = match[2] === '/';
        const tag = match[3].toLowerCase();
        if (bbTags.has(tag)) {
          if (!isClosing) {
            stack.push({ type: 'bb', tag, close: `[/${tag}]` });
          } else {
            const idx = stack.map(s => s.tag).lastIndexOf(tag);
            if (idx !== -1) stack.splice(idx, 1);
          }
        }
      } else if (match[5]) {
        // HTML
        const isClosing = match[4] === '/';
        const tag = match[5].toLowerCase();
        if (htmlTags.has(tag)) {
          if (!isClosing) {
            stack.push({ type: 'html', tag, close: `</${tag}>` });
          } else {
            const idx = stack.map(s => s.tag).lastIndexOf(tag);
            if (idx !== -1) stack.splice(idx, 1);
          }
        }
      }
    }

    // Fecha tags na ordem inversa de abertura
    while (stack.length > 0) {
      balanced += stack.pop().close;
    }

    return balanced;
  }

  /**
   * Sanitiza HTML perigoso contra XSS e converte BBCode e marcadores semânticos
   * em tags HTML estilizadas com as classes do Design System AURA.
   */
  sanitizeAndTransformTags(input) {
    if (!input) return '';

    const allowedClasses = /^(?:text-(?:emerald|amber|rose|cyan|purple|red|yellow|green)|badge-(?:emerald|amber|rose|cyan|purple|red|yellow|green)|aura-(?:hl|badge|text)-(?:emerald|amber|rose|cyan|purple|red)|aura-underline|\s)+$/i;

    // 1. Escapa comentários HTML e declarações <! ... >
    let text = input.replace(/<![\s\S]*?>/g, (match) => {
      return '&lt;' + match.slice(1, -1) + '&gt;';
    });

    // 2. Escapa operadores matemáticos '<' seguidos de espaço, dígito ou símbolo (ex: < 15%, <15, <= 10)
    text = text.replace(/<(?![a-zA-Z\/])/g, '&lt;');

    // 3. Sanitiza e filtra TODAS as tags HTML
    text = text.replace(/<(\/?[a-zA-Z][a-zA-Z0-9]*)([^>]*)>/g, (fullMatch, rawTagName, rawAttrs) => {
      const isClosing = rawTagName.startsWith('/');
      const tagName = (isClosing ? rawTagName.slice(1) : rawTagName).toLowerCase();
      const attrs = (rawAttrs || '').trim();

      // Expurgar handlers de eventos perigosos (on*) e schemes de script
      const cleanedAttrs = attrs
        .replace(/\bon\w+\s*=\s*(?:'[^']*'|"[^"]*"|[^\s>]+)/gi, '')
        .replace(/javascript:[^\s"'>]*/gi, '')
        .trim();

      const escapeTag = (name, a) => {
        const inside = (name + (a ? ' ' + a : '')).trim();
        return '&lt;' + inside.replace(/"/g, '&quot;').replace(/'/g, '&#039;') + '&gt;';
      };

      const safeVoidOrSimpleTags = new Set(['b', 'i', 'strong', 'em', 'p', 'br', 'hr', 'code', 'pre', 'blockquote', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'ul', 'ol', 'li']);

      if (isClosing) {
        if (['span', 'mark', 'u', ...safeVoidOrSimpleTags].includes(tagName)) {
          return `</${tagName}>`;
        }
        return '&lt;/' + tagName + '&gt;';
      }

      // Abertura de span ou mark: EXCLUSIVAMENTE atributo class com classes permitidas
      if (tagName === 'span' || tagName === 'mark') {
        const classMatch = attrs.match(/^class\s*=\s*(["'])([^"']*)\1$/i);
        if (classMatch) {
          const cls = classMatch[2].trim();
          if (allowedClasses.test(cls)) {
            return `<span class="${cls}">`;
          }
        }
        return escapeTag(rawTagName, cleanedAttrs);
      }

      // Abertura de u: sem atributos ou com class="aura-underline"
      if (tagName === 'u') {
        if (!attrs || /^class\s*=\s*(["'])aura-underline\1$/i.test(attrs)) {
          return '<u class="aura-underline">';
        }
        return escapeTag(rawTagName, cleanedAttrs);
      }

      // Tags simples sem atributos
      if (safeVoidOrSimpleTags.has(tagName)) {
        if (!attrs || attrs === '/') {
          return `<${tagName}>`;
        }
        return escapeTag(rawTagName, cleanedAttrs);
      }

      // Qualquer outra tag não autorizada é escapada
      return escapeTag(rawTagName, cleanedAttrs);
    });

    // 4. Dicionário de cores e badges semânticos AURA
    const colorMap = {
      'verde': { hl: 'text-emerald aura-hl-emerald', badge: 'badge-emerald aura-badge-emerald' },
      'emerald': { hl: 'text-emerald aura-hl-emerald', badge: 'badge-emerald aura-badge-emerald' },
      'green': { hl: 'text-emerald aura-hl-emerald', badge: 'badge-emerald aura-badge-emerald' },

      'amarelo': { hl: 'text-amber aura-hl-amber', badge: 'badge-amber aura-badge-amber' },
      'amber': { hl: 'text-amber aura-hl-amber', badge: 'badge-amber aura-badge-amber' },
      'yellow': { hl: 'text-amber aura-hl-amber', badge: 'badge-amber aura-badge-amber' },

      'vermelho': { hl: 'text-rose aura-hl-rose', badge: 'badge-rose aura-badge-rose' },
      'rose': { hl: 'text-rose aura-hl-rose', badge: 'badge-rose aura-badge-rose' },
      'red': { hl: 'text-rose aura-hl-rose', badge: 'badge-rose aura-badge-rose' },

      'ciano': { hl: 'text-cyan aura-hl-cyan', badge: 'badge-cyan aura-badge-cyan' },
      'cyan': { hl: 'text-cyan aura-hl-cyan', badge: 'badge-cyan aura-badge-cyan' },

      'roxo': { hl: 'text-purple aura-hl-purple', badge: 'badge-purple aura-badge-purple' },
      'purple': { hl: 'text-purple aura-hl-purple', badge: 'badge-purple aura-badge-purple' },
    };

    // Transforma BBCode de badges: [badge-cor]...[/badge-cor]
    Object.keys(colorMap).forEach(key => {
      const badgeRegex = new RegExp('\\[badge-' + key + '\\]([\\s\\S]*?)\\[\\/badge-' + key + '\\]', 'gi');
      text = text.replace(badgeRegex, `<span class="${colorMap[key].badge}">$1</span>`);
    });

    // Transforma BBCode de realces coloridos: [cor]...[/cor]
    Object.keys(colorMap).forEach(key => {
      const hlRegex = new RegExp('\\[' + key + '\\]([\\s\\S]*?)\\[\\/' + key + '\\]', 'gi');
      text = text.replace(hlRegex, `<span class="${colorMap[key].hl}">$1</span>`);
    });

    // Transforma BBCode de sublinhado: [u]...[/u]
    text = text.replace(/\[u\]([\s\S]*?)\[\/u\]/gi, '<u class="aura-underline">$1</u>');

    // Transforma Markdown de sublinhado: __texto__ (permite underlines no meio de palavras compostas)
    text = text.replace(/(^|[^\w])__(?!_)([^\r\n]+?)(?<!_)__([^\w]|$)/g, '$1<u class="aura-underline">$2</u>$3');

    return text;
  }

  /**
   * Renderizador autônomo e rico de Markdown para funcionamento 100% offline
   * sem dependência externa do Marked.js.
   * Suporta cabeçalhos, listas (ordenadas e não ordenadas), blockquotes,
   * tabelas, blocos de código com linguagem, inline code, negrito, itálico e links.
   */
  renderFallbackMarkdown(text) {
    if (!text) return '';

    const lines = text.split('\n');
    const output = [];
    let inCodeBlock = false;
    let codeBlockLang = '';
    let codeBlockLines = [];
    let listType = null;
    let inBlockquote = false;
    let blockquoteLines = [];
    let inTable = false;
    let tableLines = [];

    function flushList() {
      if (listType) {
        output.push(`</${listType}>`);
        listType = null;
      }
    }

    function flushBlockquote() {
      if (inBlockquote) {
        output.push(`<blockquote><p>${blockquoteLines.join('<br>')}</p></blockquote>`);
        inBlockquote = false;
        blockquoteLines = [];
      }
    }

    function flushTable() {
      if (inTable && tableLines.length > 0) {
        let tableHtml = '<div class="overflow-x-auto my-3"><table class="w-full text-xs text-left border-collapse border border-slate-800">';
        let isHeader = true;
        for (let r = 0; r < tableLines.length; r++) {
          const row = tableLines[r].trim();
          if (/^\|?[\s\-:|]+\|?$/.test(row)) {
            isHeader = false;
            continue;
          }
          const cells = row.replace(/^\|/, '').replace(/\|$/, '').split('|').map(c => c.trim());
          tableHtml += '<tr>';
          cells.forEach(c => {
            if (isHeader) {
              tableHtml += `<th class="px-2.5 py-1.5 font-bold bg-slate-900 border border-slate-800 text-slate-200">${c}</th>`;
            } else {
              tableHtml += `<td class="px-2.5 py-1.5 border border-slate-800 text-slate-300">${c}</td>`;
            }
          });
          tableHtml += '</tr>';
        }
        tableHtml += '</table></div>';
        output.push(tableHtml);
        inTable = false;
        tableLines = [];
      }
    }

    for (let i = 0; i < lines.length; i++) {
      const rawLine = lines[i];

      // 1. Fenced Code Blocks (```)
      const codeMatch = rawLine.match(/^```([a-zA-Z0-9_\-]*)/);
      if (codeMatch) {
        if (!inCodeBlock) {
          flushList();
          flushBlockquote();
          flushTable();
          inCodeBlock = true;
          codeBlockLang = codeMatch[1] || '';
          codeBlockLines = [];
        } else {
          inCodeBlock = false;
          const codeContent = codeBlockLines.join('\n')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
          const langAttr = codeBlockLang ? ` class="language-${codeBlockLang}"` : '';
          output.push(`<pre class="bg-slate-900 border border-slate-800 p-3 rounded-lg overflow-x-auto text-xs font-mono text-cyan-300"><code${langAttr}>${codeContent}</code></pre>`);
          codeBlockLang = '';
          codeBlockLines = [];
        }
        continue;
      }

      if (inCodeBlock) {
        codeBlockLines.push(rawLine);
        continue;
      }

      // 2. Tabelas Markdown (| col1 | col2 |)
      if (rawLine.trim().startsWith('|') && rawLine.trim().endsWith('|')) {
        flushList();
        flushBlockquote();
        inTable = true;
        tableLines.push(rawLine);
        continue;
      } else if (inTable) {
        flushTable();
      }

      // 3. Blockquotes (> texto)
      const bqMatch = rawLine.match(/^>\s*(.+)$/);
      if (bqMatch) {
        flushList();
        flushTable();
        inBlockquote = true;
        blockquoteLines.push(bqMatch[1]);
        continue;
      } else if (inBlockquote) {
        flushBlockquote();
      }

      // 4. Cabeçalhos Markdown
      const h4 = rawLine.match(/^####\s+(.+)$/);
      if (h4) { flushList(); output.push(`<h4>${h4[1]}</h4>`); continue; }
      const h3 = rawLine.match(/^###\s+(.+)$/);
      if (h3) { flushList(); output.push(`<h3>${h3[1]}</h3>`); continue; }
      const h2 = rawLine.match(/^##\s+(.+)$/);
      if (h2) { flushList(); output.push(`<h2>${h2[1]}</h2>`); continue; }
      const h1 = rawLine.match(/^#\s+(.+)$/);
      if (h1) { flushList(); output.push(`<h1>${h1[1]}</h1>`); continue; }

      // 5. Linhas horizontais (--- ou ***)
      if (/^(?:---|\*\*\*|___)\s*$/.test(rawLine.trim())) {
        flushList();
        output.push('<hr class="my-3 border-slate-800">');
        continue;
      }

      // 6. Listas ordenadas (1. item)
      const olMatch = rawLine.match(/^\s*(\d+)\.\s+(.+)$/);
      if (olMatch) {
        if (listType !== 'ol') {
          flushList();
          listType = 'ol';
          output.push('<ol class="list-decimal pl-5 space-y-1">');
        }
        output.push(`<li>${olMatch[2]}</li>`);
        continue;
      }

      // 7. Listas não ordenadas (- item ou * item)
      const ulMatch = rawLine.match(/^\s*[-*]\s+(.+)$/);
      if (ulMatch) {
        if (listType !== 'ul') {
          flushList();
          listType = 'ul';
          output.push('<ul class="list-disc pl-5 space-y-1">');
        }
        output.push(`<li>${ulMatch[1]}</li>`);
        continue;
      }

      flushList();

      // 8. Linhas vazias
      if (rawLine.trim() === '') {
        continue;
      }

      // 9. Parágrafos comuns
      output.push(`<p>${rawLine}</p>`);
    }

    if (inCodeBlock) {
      const codeContent = codeBlockLines.join('\n')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
      output.push(`<pre class="bg-slate-900 border border-slate-800 p-3 rounded-lg overflow-x-auto text-xs font-mono text-cyan-300"><code>${codeContent}</code></pre>`);
    }
    flushList();
    flushBlockquote();
    flushTable();

    let html = output.join('\n');

    // Negrito (**texto**)
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // Itálico (*texto*)
    html = html.replace(/(?<!\*)\*([^*\n]+?)\*(?!\*)/g, '<em>$1</em>');
    // Inline code (`código`)
    html = html.replace(/`([^`\n]+)`/g, '<code class="px-1.5 py-0.5 rounded bg-slate-800 text-cyan-300 font-mono text-xs">$1</code>');

    return html;
  }

  /**
   * Formata texto em Markdown rico, seguro e semântico para a AURA.
   * Suporta negrito (**texto**), itálico (*texto*), sublinhado (<u>texto</u>, [u]texto[/u] ou __texto__),
   * destaques coloridos ([verde], [amarelo], [vermelho], [ciano], [roxo]), badges e tags seguras.
   * Garante renderização suave no streaming token-a-token e sanitização estrita contra XSS.
   */
  formatMarkdown(rawMarkdown, isStillStreaming = false) {
    if (!rawMarkdown || typeof rawMarkdown !== 'string') return '';

    // 1. Em streaming ativo, balanceia tags abertas temporariamente
    let preparedText = isStillStreaming
      ? this.balanceStreamingText(rawMarkdown)
      : rawMarkdown;

    // 2. Protege blocos de código e inline code antes de transformar BBCode e tags
    const { protectedText, codeSnippets } = this.extractCodeBlocks(preparedText);

    // 3. Sanitiza HTML malicioso e transforma BBCode e sublinhado em tags seguras
    let transformedText = this.sanitizeAndTransformTags(protectedText);

    // 4. Restaura blocos de código intactos
    let finalText = this.restoreCodeBlocks(transformedText, codeSnippets);

    // 5. Renderização via Marked.js com breaks e GFM ou fallback offline
    let html = '';
    if (typeof window !== 'undefined' && window.marked && typeof window.marked.parse === 'function') {
      try {
        html = window.marked.parse(finalText);
      } catch (err) {
        console.warn('[AuraChat] Falha no marked.parse, acionando fallback nativo:', err);
        html = this.renderFallbackMarkdown(finalText);
      }
    } else {
      html = this.renderFallbackMarkdown(finalText);
    }

    return html;
  }

  updateAuraText(containerId, fullMarkdown, isStillStreaming) {
    const textIds = [containerId + '-text', containerId + '-split-text'];
    const html = this.formatMarkdown(fullMarkdown, isStillStreaming);

    textIds.forEach(id => {
      const textEl = document.getElementById(id);
      if (textEl) {
        if (isStillStreaming) {
          textEl.classList.add('typing-cursor');
        } else {
          textEl.classList.remove('typing-cursor');
        }
        textEl.innerHTML = html;
      }
    });

    this.scrollToBottom();
  }

  updateTelemetryBadge(containerId, t) {
    const ids = [containerId + '-telemetry', containerId + '-split-telemetry'];
    const e2e = t.total_e2e_ms ? `${t.total_e2e_ms.toFixed(0)}ms` : null;
    const model = t.llm_model || 'Gemini 3.1 Flash';
    const lgpd = t.lgpd_sanitized_count || 0;

    const html = `
      <div class="flex flex-wrap items-center gap-3">
        ${e2e ? `<span class="flex items-center gap-1"><span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> Resposta em <strong class="text-emerald-300 font-sans tabular-nums font-semibold">${e2e}</strong></span>` : ''}
        <span class="text-slate-500">•</span>
        <span>Motor: <strong class="text-purple-300">${model}</strong></span>
        ${lgpd > 0 ? `<span class="text-slate-500">•</span><span class="text-emerald-400/90 font-medium inline-flex items-center gap-1">${CHAT_ICONS.shield} LGPD: ${lgpd} dados protegidos</span>` : ''}
      </div>
    `;

    ids.forEach(id => {
      const el = document.getElementById(id);
      if (el) {
        el.innerHTML = html;
        el.classList.remove('hidden');
      }
    });

    this.scrollToBottom();
  }

  renderStreamError(containerId, errorMsg) {
    this.hideToolCardSkeleton(containerId);
    const textIds = [containerId + '-text', containerId + '-split-text'];
    const html = `
      <div class="p-3.5 rounded-xl bg-rose-950/20 border border-rose-500/40 text-rose-300 text-xs font-sans">
        <strong class="inline-flex items-center gap-1">${CHAT_ICONS.alert} Falha de Conexão ou Resposta:</strong> ${this.escapeHtml(errorMsg)}
      </div>
    `;

    textIds.forEach(id => {
      const textEl = document.getElementById(id);
      if (textEl) {
        textEl.classList.remove('typing-cursor');
        textEl.innerHTML = html;
      }
    });

    this.scrollToBottom();
  }

  scrollToBottom(force = false) {
    const feed = document.getElementById('chat-feed-container');
    if (feed && (force || !this.userScrolledUp)) {
      feed.scrollTop = feed.scrollHeight;
    }
  }

  formatBRL(val) {
    if (val === null || val === undefined || isNaN(Number(val))) return '-';
    const num = Number(val);
    return 'R$ ' + num.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  formatSignedBRL(val) {
    if (val === null || val === undefined || isNaN(Number(val))) return '-';
    const num = Number(val);
    if (Math.abs(num) < 0.005) {
      return 'R$ 0,00';
    }
    const prefix = num < 0 ? '-' : '+';
    return `${prefix}R$ ${Math.abs(num).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }

  formatLiters(val, decimals = 1) {
    if (val === null || val === undefined || isNaN(Number(val))) return '-';
    const num = Number(val);
    return `${num.toLocaleString('pt-BR', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })} L`;
  }

  formatNumber(val, decimals = 0) {
    if (val === null || val === undefined || isNaN(Number(val))) return '-';
    const num = Number(val);
    return num.toLocaleString('pt-BR', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  }

  formatPercent(val, decimals = 1) {
    if (val === null || val === undefined || isNaN(Number(val))) return '-';
    const num = Number(val);
    return `${num.toLocaleString('pt-BR', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}%`;
  }

  formatDateBR(val) {
    if (!val) return 'Hoje';
    try {
      const parts = String(val).split('T')[0].split('-');
      if (parts.length === 3) {
        return `${parts[2]}/${parts[1]}/${parts[0]}`;
      }
      return String(val);
    } catch (e) {
      return String(val);
    }
  }

  escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
}

// Instância singleton global e export para ambientes Node/Testes
if (typeof window !== 'undefined') {
  window.auraChat = new AuraChatController();
}
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { AuraChatController };
}
