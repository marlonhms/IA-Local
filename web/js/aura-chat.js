/**
 * AURA Console Cognitivo Controller
 * Gerencia a conversa em tempo real com streaming SSE token-a-token,
 * renderização de blocos tipados (Intent, Tool Start, Tool Result, Telemetry),
 * Markdown rico com GitHub Flavored Markdown e breaks,
 * espelhamento em tempo real com a Visão Split e memória de sessão durável.
 */

class AuraChatController {
  constructor() {
    this.sessionId = this.generateSessionId();
    this.isStreaming = false;
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
    };
  }

  generateSessionId() {
    return 'aura_ui_' + Math.random().toString(36).substring(2, 10);
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
    this.addWelcomeMessage();
  }

  bindEvents() {
    const input = document.getElementById('chat-input-text');
    const sendBtn = document.getElementById('btn-chat-send');
    const stopBtn = document.getElementById('btn-chat-stop');
    const clearBtn = document.getElementById('btn-chat-clear');
    const newChatBtn = document.getElementById('btn-new-chat');

    const splitInput = document.getElementById('split-chat-input-text');
    const splitSendBtn = document.getElementById('btn-split-chat-send');

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

    if (splitInput) {
      splitInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          this.handleSendMessage();
        }
      });
    }

    if (sendBtn) sendBtn.addEventListener('click', () => this.handleSendMessage());
    if (splitSendBtn) splitSendBtn.addEventListener('click', () => this.handleSendMessage());
    if (stopBtn) stopBtn.addEventListener('click', () => this.abortStreaming());
    if (clearBtn) clearBtn.addEventListener('click', () => this.clearSession());

    // F4-12 & F4-13: Detecção de rolagem e botão flutuante de mensagens recentes
    const chatFeed = document.getElementById('chat-feed-container');
    const splitFeed = document.getElementById('split-chat-feed-container');
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

    if (splitFeed) {
      splitFeed.addEventListener('scroll', () => {
        const threshold = 80;
        const isAtBottom = (splitFeed.scrollHeight - splitFeed.scrollTop - splitFeed.clientHeight) <= threshold;
        this.userScrolledUp = !isAtBottom;
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
      const evDrawer = document.getElementById('aura-evidence-drawer');
      const isDrawerOpen = evDrawer && evDrawer.classList.contains('open');

      if (e.key === 'Escape' && isDrawerOpen) {
        this.closeEvidence();
      }

      // Acessibilidade: Focus Trap dentro do Drawer aberto
      if (e.key === 'Tab' && isDrawerOpen) {
        const focusableEls = evDrawer.querySelectorAll('button:not([disabled]), [tabindex]:not([tabindex="-1"]), [href], input, select, textarea');
        if (focusableEls.length > 0) {
          const firstEl = focusableEls[0];
          const lastEl = focusableEls[focusableEls.length - 1];
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

    document.querySelectorAll('.evidence-tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const tab = btn.getAttribute('data-ev-tab');
        this.switchEvidenceTab(tab);
      });
    });
  }

  renderSessionId() {
    const el = document.getElementById('chat-session-badge');
    if (el) el.textContent = `Sessão: ${this.sessionId}`;
  }

  addWelcomeMessage() {
    const welcomeHtml = `
      <div class="decision-card !p-5 border-cyan-500/25 bg-gradient-to-b from-slate-900/95 via-slate-900/80 to-slate-950/95 space-y-4 shadow-2xl">
        <!-- Cabeçalho Executivo Precision Glass -->
        <div class="flex items-start justify-between gap-3 pb-3 border-b border-white/10">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-2xl bg-gradient-to-tr from-cyan-500/20 via-sky-500/15 to-purple-500/20 border border-cyan-400/30 flex items-center justify-center text-cyan-300 shadow-inner">
              <i data-lucide="sparkles" class="w-5 h-5 text-cyan-300"></i>
            </div>
            <div>
              <div class="flex items-center gap-2">
                <h3 class="text-white font-bold text-base tracking-wide">AURA // Decisão & Supervisão</h3>
                <span class="px-2 py-0.5 rounded-full text-[9px] font-sans font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                  Precision Glass
                </span>
              </div>
              <p class="text-slate-400 text-xs">Assistente Executiva de Prontidão • Posto & PDV</p>
            </div>
          </div>
          <span class="px-2.5 py-1 rounded-full text-[10px] font-mono font-semibold bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 hidden sm:inline-flex items-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse"></span> Sob Demanda
          </span>
        </div>

        <p class="text-slate-200 text-sm leading-relaxed">
          Estou de prontidão para iluminar tomadas de decisão rápidas na pista e no PDV com <strong>diagnósticos estruturados, cálculos contábeis oficiais e evidências verificáveis</strong>.
        </p>

        <!-- Grade de Consultas Executivas em 1-Toque (Acionam os DecisionCards Reais) -->
        <div class="space-y-2 pt-1">
          <div class="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
            <i data-lucide="compass" class="w-3.5 h-3.5 text-cyan-400"></i>
            <span>Diagnósticos Especializados (Toque para auditar agora):</span>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 w-full">
            <button onclick="window.auraChat.sendUserPrompt('Qual a situação e autonomia de cada tanque agora?')" class="group p-3 rounded-xl bg-slate-900/90 hover:bg-slate-800/90 border border-white/10 hover:border-emerald-500/50 text-left transition-all shadow-sm active:scale-[0.98]">
              <div class="flex items-center justify-between mb-1.5">
                <div class="flex items-center gap-2">
                  <span class="text-base">⛽</span>
                  <span class="text-white font-semibold text-xs group-hover:text-emerald-300 transition-colors">Autonomia de Tanques</span>
                </div>
                <span class="text-[9px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Run-Out</span>
              </div>
              <p class="text-[11px] text-slate-400 group-hover:text-slate-300 leading-snug">Previsão em horas/dias, reserva de 15% e espaço de carreta (5.000L).</p>
            </button>

            <button onclick="window.auraChat.sendUserPrompt('Como fechou o último turno? Teve furo de caixa?')" class="group p-3 rounded-xl bg-slate-900/90 hover:bg-slate-800/90 border border-white/10 hover:border-cyan-500/50 text-left transition-all shadow-sm active:scale-[0.98]">
              <div class="flex items-center justify-between mb-1.5">
                <div class="flex items-center gap-2">
                  <span class="text-base">💰</span>
                  <span class="text-white font-semibold text-xs group-hover:text-cyan-300 transition-colors">Conciliação de Turno</span>
                </div>
                <span class="text-[9px] font-mono px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">CBC04 vs PDV</span>
              </div>
              <p class="text-[11px] text-slate-400 group-hover:text-slate-300 leading-snug">Triangulação de encerrantes físicos, sobras/quebras e faturamento.</p>
            </button>

            <button onclick="window.auraChat.sendUserPrompt('O LMC de ontem fechou dentro da tolerância oficial da ANP?')" class="group p-3 rounded-xl bg-slate-900/90 hover:bg-slate-800/90 border border-white/10 hover:border-purple-500/50 text-left transition-all shadow-sm active:scale-[0.98]">
              <div class="flex items-center justify-between mb-1.5">
                <div class="flex items-center gap-2">
                  <span class="text-base">📋</span>
                  <span class="text-white font-semibold text-xs group-hover:text-purple-300 transition-colors">LMC Oficial ANP</span>
                </div>
                <span class="text-[9px] font-mono px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20">±0.6%</span>
              </div>
              <p class="text-[11px] text-slate-400 group-hover:text-slate-300 leading-snug">Auditoria diária pela Portaria 26 com régua visual de conformidade legal.</p>
            </button>

            <button onclick="window.auraChat.sendUserPrompt('Há algum bico com vazão lenta ou alerta na pista?')" class="group p-3 rounded-xl bg-slate-900/90 hover:bg-slate-800/90 border border-white/10 hover:border-amber-500/50 text-left transition-all shadow-sm active:scale-[0.98]">
              <div class="flex items-center justify-between mb-1.5">
                <div class="flex items-center gap-2">
                  <span class="text-base">⚡</span>
                  <span class="text-white font-semibold text-xs group-hover:text-amber-300 transition-colors">Vazão & Frentistas</span>
                </div>
                <span class="text-[9px] font-mono px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">&lt;30 L/min</span>
              </div>
              <p class="text-[11px] text-slate-400 group-hover:text-slate-300 leading-snug">Detecção preventiva de filtro sujo, produtividade e conversão de aditivada.</p>
            </button>

            <button onclick="window.auraChat.sendUserPrompt('Quais os combos de vendas cruzadas com maior Lift na conveniência?')" class="group p-3 rounded-xl bg-slate-900/90 hover:bg-slate-800/90 border border-white/10 hover:border-sky-500/50 text-left transition-all shadow-sm active:scale-[0.98]">
              <div class="flex items-center justify-between mb-1.5">
                <div class="flex items-center gap-2">
                  <span class="text-base">🛒</span>
                  <span class="text-white font-semibold text-xs group-hover:text-sky-300 transition-colors">Combos da Loja</span>
                </div>
                <span class="text-[9px] font-mono px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/20">Lift ≥ 2.0x</span>
              </div>
              <p class="text-[11px] text-slate-400 group-hover:text-slate-300 leading-snug">Market Basket Analysis da conveniência com scripts práticos para balcão.</p>
            </button>

            <button onclick="window.auraChat.sendUserPrompt('Quem são os maiores clientes e frotistas da revenda?')" class="group p-3 rounded-xl bg-slate-900/90 hover:bg-slate-800/90 border border-white/10 hover:border-rose-500/50 text-left transition-all shadow-sm active:scale-[0.98]">
              <div class="flex items-center justify-between mb-1.5">
                <div class="flex items-center gap-2">
                  <span class="text-base">🏆</span>
                  <span class="text-white font-semibold text-xs group-hover:text-rose-300 transition-colors">Clientes & Frotas</span>
                </div>
                <span class="text-[9px] font-mono px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">Ranking</span>
              </div>
              <p class="text-[11px] text-slate-400 group-hover:text-slate-300 leading-snug">Faturamento acumulado por cliente, frotistas e volume de vendas.</p>
            </button>
          </div>
        </div>

        <div class="p-2.5 rounded-xl bg-cyan-500/5 border border-cyan-500/15 flex items-center justify-between text-xs text-slate-400">
          <span class="flex items-center gap-1.5 text-cyan-300">
            <i data-lucide="info" class="w-3.5 h-3.5"></i>
            <span>Dica: Ao receber qualquer resposta, clique em <strong>"Ver Evidências"</strong> para abrir o painel com as fontes oficiais.</span>
          </span>
          <kbd class="hidden sm:inline-block px-1.5 py-0.5 rounded bg-slate-800 text-[10px] text-slate-400 font-mono">Esc fecha gaveta</kbd>
        </div>
      </div>
    `;
    this.appendAuraMessage(welcomeHtml, { isWelcome: true });
  }

  /**
   * Dispara prompt vindo de atalhos rápidos ou outros módulos
   */
  sendUserPrompt(text) {
    const input = document.getElementById('chat-input-text');
    if (input) input.value = '';
    const splitInput = document.getElementById('split-chat-input-text');
    if (splitInput) splitInput.value = '';
    this.handleSendMessage(text);
  }

  /**
   * Envia a mensagem do usuário e inicia a conexão SSE
   */
  async handleSendMessage(promptText = null) {
    let query = promptText;
    const input = document.getElementById('chat-input-text');
    const splitInput = document.getElementById('split-chat-input-text');

    if (!query) {
      if (input && input.value.trim()) {
        query = input.value.trim();
      } else if (splitInput && splitInput.value.trim()) {
        query = splitInput.value.trim();
      }
    }

    if (!query || this.isStreaming) return;

    if (input) {
      input.value = '';
      input.style.height = 'auto';
    }
    if (splitInput) {
      splitInput.value = '';
    }

    this.userScrolledUp = false;
    const scrollBtn = document.getElementById('btn-scroll-bottom');
    if (scrollBtn) scrollBtn.classList.add('hidden');

    this.setStreamingState(true);

    // 1. Adiciona a mensagem do usuário na tela (Console e Split)
    this.appendUserMessage(query);

    // 2. Prepara contêiner para a resposta da AURA
    const messageContainerId = 'aura-msg-' + Date.now();
    this.createAuraMessageBubble(messageContainerId);

    // Força rolagem para o início da nova resposta
    this.scrollToBottom(true);

    // Contexto de streaming
    let fullResponseText = '';
    let currentIntent = null;
    let currentToolResult = null;
    let telemetryData = null;

    this.abortController = new AbortController();

    try {
      await window.auraApi.chatStream({
        query: query,
        sessionId: this.sessionId,
        signal: this.abortController.signal,
        onChunk: (chunk) => {
          const type = chunk.chunk_type || chunk.eventType || 'delta';

          if (type === 'intent') {
            currentIntent = chunk.data || { intent: chunk.intent };
            this.updateIntentChip(messageContainerId, currentIntent);
          } 
          else if (type === 'tool_start') {
            const toolName = chunk.data?.tool_name || chunk.data?.intent || chunk.tool_name || chunk.intent || 'ferramenta';
            this.updateToolStartStatus(messageContainerId, toolName);
          } 
          else if (type === 'tool_result') {
            const toolName = chunk.data?.tool_name || chunk.data?.intent || chunk.tool_name || chunk.intent || 'ferramenta';
            currentToolResult = chunk.data?.result || chunk.data || {};
            this.updateToolResultCard(messageContainerId, toolName, currentToolResult);
          } 
          else if (type === 'delta') {
            const token = chunk.text || chunk.data?.text || '';
            fullResponseText += token;
            this.updateAuraText(messageContainerId, fullResponseText, true);
          } 
          else if (type === 'telemetry') {
            telemetryData = chunk.data || {};
            this.updateTelemetryBadge(messageContainerId, telemetryData);
          }
          else if (type === 'error') {
            const errorMsg = chunk.data?.error || chunk.text || 'Erro no processamento da solicitação';
            this.renderStreamError(messageContainerId, errorMsg);
            this.setStreamingState(false);
          }
          else if (type === 'done') {
            this.updateAuraText(messageContainerId, fullResponseText, false);
            this.setStreamingState(false);
          }
        },
        onDone: () => {
          this.updateAuraText(messageContainerId, fullResponseText, false);
          this.setStreamingState(false);
          this.scrollToBottom(false);
        },
        onError: (err) => {
          console.error('[AuraChat] Erro no stream:', err);
          this.renderStreamError(messageContainerId, err.message);
          this.setStreamingState(false);
        },
      });
    } catch (err) {
      console.error('[AuraChat] Erro fatal no chat:', err);
      this.renderStreamError(messageContainerId, err.message);
      this.setStreamingState(false);
    }
  }

  abortStreaming() {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
    this.setStreamingState(false);
  }

  clearSession() {
    this.abortStreaming();
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
    const splitFeed = document.getElementById('split-chat-feed-container');
    if (splitFeed) splitFeed.innerHTML = '';
    this.addWelcomeMessage();
  }

  setStreamingState(isStreaming) {
    this.isStreaming = isStreaming;
    const sendBtn = document.getElementById('btn-chat-send');
    const stopBtn = document.getElementById('btn-chat-stop');
    const input = document.getElementById('chat-input-text');

    const splitSendBtn = document.getElementById('btn-split-chat-send');
    const splitInput = document.getElementById('split-chat-input-text');

    if (sendBtn && stopBtn) {
      if (isStreaming) {
        sendBtn.classList.add('hidden');
        stopBtn.classList.remove('hidden');
      } else {
        sendBtn.classList.remove('hidden');
        stopBtn.classList.add('hidden');
      }
    }

    if (splitSendBtn) {
      splitSendBtn.disabled = isStreaming;
      splitSendBtn.textContent = isStreaming ? 'Gerando...' : 'Enviar';
    }

    if (input) {
      input.disabled = isStreaming;
      if (!isStreaming && typeof window !== 'undefined' && window.innerWidth >= 768 && typeof input.focus === 'function') {
        input.focus({ preventScroll: true });
      }
    }

    if (splitInput) {
      splitInput.disabled = isStreaming;
    }
  }

  appendUserMessage(text) {
    const feeds = [
      document.getElementById('chat-feed-container'),
      document.getElementById('split-chat-feed-container')
    ].filter(Boolean);

    feeds.forEach(feed => {
      const div = document.createElement('div');
      div.className = 'flex justify-end w-full animate-fade-in';
      div.innerHTML = `
        <div class="chat-bubble-user max-w-[85%] md:max-w-[70%] lg:max-w-[60%] ml-auto p-3.5 text-slate-100 text-sm">
          <div class="flex items-center justify-between text-[11px] font-mono text-slate-400 mb-1">
            <span class="font-bold text-cyan-400">OPERADOR</span>
            <span>${new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</span>
          </div>
          <div class="leading-relaxed whitespace-pre-wrap">${this.escapeHtml(text)}</div>
        </div>
      `;
      feed.appendChild(div);
    });

    this.scrollToBottom();
  }

  createAuraMessageBubble(containerId) {
    const feeds = [
      { el: document.getElementById('chat-feed-container'), suffix: '' },
      { el: document.getElementById('split-chat-feed-container'), suffix: '-split' }
    ].filter(item => Boolean(item.el));

    feeds.forEach(({ el, suffix }) => {
      const div = document.createElement('div');
      div.id = containerId + suffix;
      div.className = 'flex justify-start w-full animate-fade-in';
      div.innerHTML = `
        <div class="chat-bubble-aura w-full max-w-full p-4.5 text-slate-100 text-sm space-y-3">
          <!-- Header da Resposta com Núcleo e Tags -->
          <div class="flex flex-wrap items-center justify-between gap-2 border-b border-purple-900/40 pb-2">
            <div class="flex items-center gap-2">
              <div class="w-5 h-5 rounded-full bg-gradient-to-tr from-emerald-500 via-cyan-500 to-purple-600 flex items-center justify-center text-[10px] font-bold text-white shadow-sm">
                A
              </div>
              <span class="font-bold font-sans text-xs text-purple-200">AURA</span>
            </div>

            <div id="${containerId + suffix}-meta" class="flex flex-wrap items-center gap-1.5 font-mono text-[10px]">
              <span id="${containerId + suffix}-intent-chip" class="hidden chip-intent"></span>
              <span id="${containerId + suffix}-tool-chip" class="hidden chip-tool-status"></span>
            </div>
          </div>

          <!-- Card de Resultado da Ferramenta Estruturada (se houver) -->
          <div id="${containerId + suffix}-tool-card" class="hidden w-full"></div>

          <!-- Texto em Streaming -->
          <div id="${containerId + suffix}-text" class="prose-aura typing-cursor">
            <span class="text-slate-400 text-xs font-mono">Processando consulta analítica...</span>
          </div>

          <!-- Métricas e Confirmação da Resposta -->
          <div id="${containerId + suffix}-telemetry" class="hidden pt-2 border-t border-slate-800/80 text-[10px] font-mono text-slate-400">
          </div>
        </div>
      `;
      el.appendChild(div);
    });

    this.scrollToBottom();
    return document.getElementById(containerId);
  }

  appendAuraMessage(htmlContent, opts = {}) {
    const feeds = [
      document.getElementById('chat-feed-container'),
      document.getElementById('split-chat-feed-container')
    ].filter(Boolean);

    feeds.forEach(feed => {
      const div = document.createElement('div');
      div.className = 'flex justify-start w-full animate-fade-in';
      div.innerHTML = `
        <div class="chat-bubble-aura w-full max-w-full p-4.5 text-slate-100 text-sm space-y-3">
          <div class="flex items-center gap-2 border-b border-purple-900/40 pb-2">
            <div class="w-5 h-5 rounded-full bg-gradient-to-tr from-emerald-500 via-cyan-500 to-purple-600 flex items-center justify-center text-[10px] font-bold text-white shadow-sm">
              A
            </div>
            <span class="font-bold font-sans text-xs text-purple-200">AURA</span>
            ${opts.isWelcome ? '<span class="px-2 py-0.5 rounded-full text-[10px] font-sans font-medium bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">Pronta para Atendimento</span>' : ''}
          </div>
          <div class="w-full">${htmlContent}</div>
        </div>
      `;
      feed.appendChild(div);
    });

    this.scrollToBottom();
  }

  updateIntentChip(containerId, intentData) {
    const ids = [containerId + '-intent-chip', containerId + '-split-intent-chip'];
    const name = intentData.intent || intentData.name || 'desconhecido';
    const conf = intentData.confidence ? ` ${(intentData.confidence * 100).toFixed(0)}%` : '';

    ids.forEach(id => {
      const chip = document.getElementById(id);
      if (chip) {
        chip.innerHTML = `🎯 ${name}${conf}`;
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

  updateToolStartStatus(containerId, toolName) {
    const ids = [containerId + '-tool-chip', containerId + '-split-tool-chip'];
    const displayName = this.formatToolDisplayName(toolName);
    ids.forEach(id => {
      const chip = document.getElementById(id);
      if (chip) {
        chip.innerHTML = `⚡ Consultando ${this.escapeHtml(displayName)}...`;
        chip.classList.remove('hidden');
      }
    });
  }

  updateToolResultCard(containerId, toolName, resultData) {
    const cardIds = [containerId + '-tool-card', containerId + '-split-tool-card'];
    const chipIds = [containerId + '-tool-chip', containerId + '-split-tool-chip'];
    const displayName = this.formatToolDisplayName(toolName);

    chipIds.forEach(id => {
      const chip = document.getElementById(id);
      if (chip) {
        chip.innerHTML = `✓ ${this.escapeHtml(displayName)} apurado`;
        chip.className = 'chip-intent text-emerald-300 border-emerald-500/30 bg-emerald-500/10';
      }
    });

    const widgetHtml = this.renderToolInlineWidget(toolName, resultData);

    if (widgetHtml) {
      cardIds.forEach(id => {
        const cardEl = document.getElementById(id);
        if (cardEl) {
          cardEl.innerHTML = widgetHtml;
          cardEl.classList.remove('hidden');
        }
      });
      this.scrollToBottom();
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

    // 4. Fallback genérico executivo
    return this.renderGenericToolWidget(toolName, data);
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
            <span>⚠️</span>
            <span>Schema Desconhecido</span>
          </span>
        </div>
        <div class="p-3.5 rounded-xl bg-slate-900/80 border border-amber-500/30 text-amber-200/90 font-mono text-xs space-y-1.5">
          <div>⚠️ <strong>Aviso de Conformidade e Governança:</strong></div>
          <p class="text-[11px] text-slate-300">
            O payload analítico recebido para <strong>${this.escapeHtml(moduleName)}</strong> utiliza a versão <code>${this.escapeHtml(version)}</code>, incompatível com o renderizador atual. A exibição executiva foi suspensa para evitar inferências incorretas.
          </p>
        </div>
      </div>
    `;
  }

  /**
   * Widget de Auto-Conhecimento e Atalho Interativo da UI
   */
  renderAjudaSistemaWidget(data) {
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
            <span class="text-sm">🚀</span>
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
            <span class="text-sm">📂</span>
            <span>${this.escapeHtml(label)}</span>
          </button>
        `;
      } else if (action.action === 'open_command_palette') {
        actionButtonHtml = `
          <button 
            type="button"
            onclick="const btn = document.getElementById('btn-open-palette'); if (btn) btn.click();" 
            class="group inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-gradient-to-r from-cyan-500/25 to-purple-600/25 hover:from-cyan-500/40 hover:to-purple-600/40 border border-cyan-400/40 hover:border-cyan-300 text-cyan-200 hover:text-white font-semibold text-xs transition-all shadow-md active:scale-95 cursor-pointer">
            <span class="text-sm">⌨️</span>
            <span>${this.escapeHtml(label)}</span>
          </button>
        `;
      } else if (action.action === 'toggle_audio') {
        actionButtonHtml = `
          <button 
            type="button"
            onclick="const btn = document.getElementById('sidebar-btn-toggle-sfx') || document.getElementById('btn-toggle-sfx'); if (btn) { btn.click(); } else if (window.auraAudio) { const m = window.auraAudio.toggleMute(); if (window.auraApp) window.auraApp.syncSfxButtons(m); }" 
            class="group inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-gradient-to-r from-cyan-500/25 to-purple-600/25 hover:from-cyan-500/40 hover:to-purple-600/40 border border-cyan-400/40 hover:border-cyan-300 text-cyan-200 hover:text-white font-semibold text-xs transition-all shadow-md active:scale-95 cursor-pointer">
            <span class="text-sm">🔊</span>
            <span>${this.escapeHtml(label)}</span>
          </button>
        `;
      } else {
        actionButtonHtml = `
          <button 
            type="button"
            onclick="if (window.auraApp) window.auraApp.switchTab('cockpit');" 
            class="group inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-gradient-to-r from-cyan-500/25 to-purple-600/25 hover:from-cyan-500/40 hover:to-purple-600/40 border border-cyan-400/40 hover:border-cyan-300 text-cyan-200 hover:text-white font-semibold text-xs transition-all shadow-md active:scale-95 cursor-pointer">
            <span class="text-sm">⚡</span>
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
        return `<span class="px-2 py-0.5 rounded-lg bg-slate-800/80 text-cyan-300/90 text-[10px] font-mono border border-slate-700/60 inline-flex items-center gap-1">📌 [${this.escapeHtml(mod)}] ${this.escapeHtml(tit)}</span>`;
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
              <span class="text-sm">💡</span>
            </div>
            <div>
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 uppercase tracking-wider">${this.escapeHtml(modulo)}</span>
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

    const isNoMovement = assessment.status_code === 'SEM_MOVIMENTACAO' || assessment.status_code === 'SEM_REGISTROS' || data.status === 'sem_movimento' || tanksList.length === 0;
    const isUnavailable = assessment.status_code === 'INDISPONIVEL' || data.status === 'indisponivel';

    const evId = 'ev_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7);
    if (typeof window !== 'undefined') {
      if (!window.__auraEvidenceStore) window.__auraEvidenceStore = {};
      window.__auraEvidenceStore[evId] = data;
    }

    // Status Badges Semânticos com Ícone (F5-09)
    let badgeClass = 'status-validated';
    let badgeIcon = '✓';
    let badgeText = assessment.badge_label || 'Estoque Estável';
    const severity = assessment.severity || (resumo.status_geral?.includes('CRITICO') ? 'critical' : (resumo.status_geral?.includes('ATENCAO') ? 'attention' : 'normal'));

    if (isNoMovement) {
      badgeClass = 'status-neutral';
      badgeIcon = '⏸️';
      badgeText = assessment.badge_label || 'Sem Registros';
    } else if (isUnavailable) {
      badgeClass = 'status-divergent';
      badgeIcon = '⚠️';
      badgeText = 'Fonte Indisponível';
    } else if (severity === 'critical') {
      badgeClass = 'status-divergent';
      badgeIcon = '🚨';
      badgeText = assessment.badge_label || 'Estoque Crítico (< 12h)';
    } else if (severity === 'attention') {
      badgeClass = 'status-partial';
      badgeIcon = '⚠️';
      badgeText = assessment.badge_label || 'Atenção Estoque';
    } else {
      badgeClass = 'status-validated';
      badgeIcon = '✓';
      badgeText = assessment.badge_label || 'Estoque Confortável';
    }

    // Métrica Hero: Menor Autonomia até Reserva 15% (distinguindo esgotamento 0% - F5-04)
    const menorAutonomiaReserva = assessment.horizonte_critico_horas ?? metrics.autonomia_critica_horas ?? metrics.menor_autonomia_runout_horas ?? assessment.menor_autonomia_horas ?? resumo.tanque_mais_critico?.autonomia_critica_horas;
    const menorAutonomiaEsgot = assessment.horizonte_runout_horas ?? metrics.autonomia_runout_horas ?? metrics.menor_autonomia_esgotamento_horas ?? assessment.menor_autonomia_esgotamento_horas ?? resumo.tanque_mais_critico?.autonomia_runout_horas;
    const codCritico = assessment.tanque_mais_critico_cod ?? resumo.tanque_mais_critico?.codtan ?? resumo.tanque_mais_critico?.tanque ?? (tanksList.length > 0 ? (tanksList[0]?.codtan || tanksList[0]?.tanque) : 'N/D');

    let heroValFormatted = '—';
    let heroColorClass = 'text-emerald';
    if (tanksList.length === 0 || isNoMovement) {
      heroValFormatted = '—';
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
    if (tanksList.length === 0 || isNoMovement) {
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

    // Bloco de Limitação (F5-02)
    let limitationHtml = '';
    const limText = assessment.limitation || resumo.limitation;
    if (limText && !isNoMovement && !isUnavailable) {
      limitationHtml = `
        <div class="decision-limitation-callout">
          <span class="text-sm">⚠️</span>
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
      let statusIcon = '🟢';
      const statusOp = String(t.status_operacional || '').toUpperCase();
      if (pct < 15 || statusOp.includes('CRÍTICO') || (hReserva !== null && hReserva < 12)) {
        fillClass = 'critical';
        statusIcon = '🚨';
      } else if (pct < 30 || statusOp.includes('ATENÇÃO') || (hReserva !== null && hReserva < 24)) {
        fillClass = 'warning';
        statusIcon = '🟡';
      }

      tanksBarsHtml += `
        <div class="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1.5 font-mono text-xs">
          <div class="flex items-center justify-between">
            <span class="font-bold text-slate-100 flex items-center gap-1.5">
              <span>${statusIcon}</span>
              <span>TQ ${this.escapeHtml(cod)} • ${this.escapeHtml(comb)}</span>
            </span>
            <span class="text-slate-300 font-semibold tabular-nums">${pct.toFixed(1)}% <span class="text-slate-500 font-normal">(${vol} / ${cap} L)</span></span>
          </div>

          <div class="widget-tank-track" style="margin: 4px 0;">
            <div class="widget-tank-fill ${fillClass}" style="width: ${pct}%"></div>
          </div>

          <div class="flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-400">
            <div class="flex items-center gap-1.5 flex-wrap">
              <span class="text-cyan-300 font-semibold tabular-nums">⏱ ${hReservaStr}${hEsgotStr}</span>
              <span class="text-slate-600">|</span>
              <span class="text-slate-300 tabular-nums">📦 Ullage: ${ullageL} L (${carretasTq}x 5k)</span>
            </div>
            <button type="button" class="widget-action-btn emerald" onclick="if (window.auraChat) window.auraChat.sendUserPrompt('Qual a melhor sugestão de pedido de carreta para o Tanque ${cod}?');">
              🚚 Pedir Carreta
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
            <span class="text-amber-400 font-bold">⏳</span>
            <span class="font-semibold text-slate-200">${this.escapeHtml(p.label)}</span>
          </div>
          <span class="text-[10px] text-slate-400 font-mono flex items-center gap-1">
            <span>Tanque</span>
            <span>↗</span>
          </span>
        </div>
      `).join('');

      pendingHtml = `
        <div class="space-y-1.5">
          <span class="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold">Alertas de Reposição:</span>
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
              <span>📅 ${this.escapeHtml(dataConsulta)}</span>
              <span>•</span>
              <span>⛽ ${tanksList.length} Tanques Monitorados</span>
              <span>•</span>
              <span>🏢 ${this.escapeHtml(c.context?.unit_id || 'Posto')}</span>
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
            <span class="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">Tanque ${codCritico}</span>
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
          ${tanksBarsHtml || '<div class="text-xs font-mono text-slate-400">Nenhum tanque retornado.</div>'}
        </div>

        ${pendingHtml}

        <!-- Ações Permitidas -->
        <div class="decision-actions">
          <button 
            type="button" 
            class="decision-btn-primary" 
            onclick="if (window.auraChat) window.auraChat.sendUserPrompt('Qual a melhor sugestão de pedido de carreta para o Tanque ${codCritico}?');"
            title="Sugerir compra imediata com base no Ullage">
            <span class="text-xs">🚚</span>
            <span>${this.escapeHtml(recLabel)}</span>
          </button>

          <button 
            type="button" 
            class="decision-btn-secondary" 
            onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'formula');"
            title="Ver fórmulas matemáticas de consumo médio e run-out">
            <span class="text-xs">📐</span>
            <span>Como foi calculado</span>
          </button>

          <button 
            type="button" 
            class="decision-btn-secondary" 
            onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'tanques');"
            title="Ver detalhamento completo dos tanques">
            <span class="text-xs">⛽</span>
            <span>Ver Tanques & Detalhes</span>
          </button>

          <button 
            type="button" 
            class="decision-btn-secondary" 
            onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'resumo');"
            title="Ver fontes de telemetria e diagnóstico">
            <span class="text-xs">📋</span>
            <span>Resumo & Fontes</span>
          </button>
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

    const isNoMovement = assessment.status_code === 'SEM_MOVIMENTACAO' || data.status === 'sem_movimento';
    const isUnavailable = assessment.status_code === 'INDISPONIVEL' || data.status === 'indisponivel';

    const evId = 'ev_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7);
    if (typeof window !== 'undefined') {
      if (!window.__auraEvidenceStore) window.__auraEvidenceStore = {};
      window.__auraEvidenceStore[evId] = data;
    }

    // Status Geral ANP
    const statusGeral = assessment.status_code || resumo.status_geral_anp || 'CONFORME_ANP';
    const isConforme = statusGeral === 'CONFORME_ANP' || statusGeral === 'CONFORME';

    let badgeClass = isConforme ? 'status-validated' : 'status-divergent';
    let badgeIcon = isConforme ? '✓' : '🚨';
    let badgeText = assessment.badge_label || (isConforme ? '✓ CONFORME ANP (±0.6%)' : '🚨 FORA DA TOLERÂNCIA ANP');

    if (isNoMovement) {
      badgeClass = 'status-neutral';
      badgeIcon = '⏸️';
      badgeText = 'Sem Movimentação';
    } else if (isUnavailable) {
      badgeClass = 'status-divergent';
      badgeIcon = '⚠️';
      badgeText = 'Fonte Indisponível';
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
    const heroVal = isNoMovement || isUnavailable ? '—' : needleText;
    const heroColorClass = isNoMovement || isUnavailable ? 'text-slate-400' : (dentroTolerancia ? 'text-emerald' : 'text-rose');
    const tanquesConformes = metrics.total_tanques_conformes ?? metrics.tanques_conformes_count ?? items.filter(it => Math.abs(parseFloat(it.variacao_pct ?? it.auditoria_anp?.variacao_pct ?? 0)) <= 0.6).length;
    const heroSub = `Portaria ANP 26/1992 • Tolerância legal: ±0.60% • ${tanquesConformes} de ${items.length} tanques em conformidade estrita.`;

    // Valores do Comparativo
    const escTotal = Number(metrics.total_estoque_escriturado_litros ?? metrics.estoque_escriturado_total_litros ?? resumo.estoque_escriturado_total_litros ?? 0);
    const fisTotal = Number(metrics.total_estoque_fisico_litros ?? metrics.estoque_fisico_total_litros ?? resumo.estoque_fisico_total_litros ?? 0);
    const varTotalL = Number(metrics.variacao_volumetrica_total_litros ?? resumo.variacao_volumetrica_total_litros ?? (fisTotal - escTotal));

    // Bloco de Limitação (F5-02)
    let limitationHtml = '';
    const limText = assessment.limitation || resumo.limitation;
    if (limText && !isNoMovement && !isUnavailable) {
      limitationHtml = `
        <div class="decision-limitation-callout">
          <span class="text-sm">⚠️</span>
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
        ? '<span class="text-emerald-400 font-bold">✓ Conforme</span>'
        : '<span class="text-rose-400 font-bold">🚨 Alerta ANP</span>';

      const escLitros = parseFloat(cItem.estoque_escriturado_litros ?? cItem.movimentacao?.estoque_escriturado_litros ?? 0).toLocaleString('pt-BR', { maximumFractionDigits: 1 });
      const fisLitros = parseFloat(cItem.estoque_fisico_medido_litros ?? cItem.estoque_fisico_litros ?? cItem.movimentacao?.estoque_fisico_medido_litros ?? 0).toLocaleString('pt-BR', { maximumFractionDigits: 1 });
      const nome = cItem.combustivel || (cItem.tanque ? `Tanque ${cItem.tanque}` : 'Combustível');
      const codTan = cItem.tanque || '00';

      rowsHtml += `
        <div class="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800 text-xs font-mono flex items-center justify-between gap-2">
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
            <span class="text-rose-400 font-bold">🚨</span>
            <span class="font-semibold text-slate-200">${this.escapeHtml(p.label)}</span>
          </div>
          <span class="text-[10px] text-slate-400 font-mono flex items-center gap-1">
            <span>LMC</span>
            <span>↗</span>
          </span>
        </div>
      `).join('');

      pendingHtml = `
        <div class="space-y-1.5">
          <span class="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold">Pendências Regulatórias:</span>
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
              <span>📅 ${this.escapeHtml(dataConsulta)}</span>
              <span>•</span>
              <span>📋 Portaria ANP 26/1992</span>
              <span>•</span>
              <span>🏢 ${this.escapeHtml(c.context?.unit_id || 'Posto')}</span>
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
            <span class="px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${dentroTolerancia ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30' : 'bg-rose-500/15 text-rose-300 border border-rose-500/30'}">
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
          <div class="flex justify-between text-[10px] font-mono text-slate-400 px-1">
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

          <div class="text-center font-mono text-xs mt-1">
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
          ${rowsHtml || '<div class="text-xs font-mono text-slate-400">Nenhum tanque retornado no relatório.</div>'}
        </div>

        ${pendingHtml}

        <!-- Ações Permitidas -->
        <div class="decision-actions">
          <button 
            type="button" 
            class="decision-btn-primary" 
            onclick="if (window.auraChat) window.auraChat.sendUserPrompt('Como auditar a divergência física no tanque de combustíveis?');"
            title="Abrir procedimento de conferência de sonda e régua">
            <span class="text-xs">🔍</span>
            <span>${this.escapeHtml(recLabel)}</span>
          </button>

          <button 
            type="button" 
            class="decision-btn-secondary" 
            onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'formula');"
            title="Ver definição regulatória da Portaria 26 da ANP">
            <span class="text-xs">📐</span>
            <span>Como foi calculado</span>
          </button>

          <button 
            type="button" 
            class="decision-btn-secondary" 
            onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'tanques');"
            title="Ver balanço físico-contábil completo dos tanques">
            <span class="text-xs">⛽</span>
            <span>Ver Tanques & ANP</span>
          </button>

          <button 
            type="button" 
            class="decision-btn-secondary" 
            onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'resumo');"
            title="Ver fontes fiscais e telemetria">
            <span class="text-xs">📋</span>
            <span>Resumo & Fontes</span>
          </button>
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
   * 4. Comparativo compacto entre Automação CBC04, Caixas PDV e Encerrantes Físicos.
   * 5. Limitações e pendências verificáveis transparentes.
   * 6. Acesso em 1 clique ao Drawer Lateral de Evidências e Fórmulas.
   */
  renderTurnoWidget(data) {
    if (!data || typeof data !== 'object') {
      return `<div class="decision-card"><p class="text-xs text-slate-400">Dados de conciliação indisponíveis ou payload inválido.</p></div>`;
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
              <span>⚠️</span>
              <span>Schema Desconhecido</span>
            </span>
          </div>
          <div class="p-3.5 rounded-xl bg-slate-900/80 border border-amber-500/30 text-amber-200/90 font-mono text-xs space-y-1.5">
            <div>⚠️ <strong>Aviso de Conformidade Contábil:</strong></div>
            <p class="text-[11px] text-slate-300">
              O payload analítico recebido utiliza a versão <code>${this.escapeHtml(c.schema_version)}</code>, incompatível com o renderizador atual. Por governança e segurança financeira, a exibição de decisão foi suspensa.
            </p>
          </div>
        </div>
      `;
    }

    // Validação mínima de payload válido
    if (!data.contrato && !data.assessment && !data.metrics && !data.resumo_executivo) {
      return `
        <div class="decision-card">
          <div class="decision-header">
            <span class="decision-context-title">Auditoria Indisponível</span>
            <span class="decision-status-badge status-neutral">Sem Dados</span>
          </div>
          <p class="text-xs text-slate-400 font-mono">Payload de conciliação vazio ou estrutura não reconhecida.</p>
        </div>
      `;
    }

    const assessment = c.assessment || {};
    const metrics = c.metrics || {};
    const pendingItems = c.pending_items || [];
    const action = c.recommended_action || {};
    const resumo = data.resumo_executivo || {};
    const tri = data.triangulacao_pista || {};

    const finality = assessment.finality || (resumo.status_conciliacao?.includes('ANDAMENTO') ? 'partial' : 'final');
    const isPartial = finality === 'partial';
    const isNoMovement = finality === 'no_movement' || data.status === 'sem_movimento';
    const isUnavailable = finality === 'unavailable' || data.status === 'indisponivel';

    // Armazena payload na memória global de evidências
    const evId = 'ev_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7);
    if (typeof window !== 'undefined') {
      if (!window.__auraEvidenceStore) window.__auraEvidenceStore = {};
      window.__auraEvidenceStore[evId] = data;
    }

    // Badges de Status Semânticos
    let badgeClass = 'status-neutral';
    let badgeIcon = '📋';
    let badgeText = assessment.badge_label || resumo.status_conciliacao || 'Turno';

    if (isPartial) {
      badgeClass = 'status-partial';
      badgeIcon = '⏳';
      badgeText = assessment.badge_label || 'Análise parcial (provisória)';
    } else if (isNoMovement) {
      badgeClass = 'status-neutral';
      badgeIcon = '⏸️';
      badgeText = 'Sem movimentação';
    } else if (isUnavailable) {
      badgeClass = 'status-divergent';
      badgeIcon = '⚠️';
      badgeText = 'Fonte indisponível';
    } else if (assessment.severity === 'critical' || resumo.status_conciliacao?.includes('FURO') || resumo.status_conciliacao?.includes('DIVERGENCIA')) {
      badgeClass = 'status-divergent';
      badgeIcon = '🚨';
      badgeText = assessment.badge_label || 'Divergência confirmada';
    } else {
      badgeClass = 'status-validated';
      badgeIcon = '✓';
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
      heroBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/30">Caixas em Aberto</span>`;
    } else if (isNoMovement || isUnavailable) {
      diffColorClass = 'text-slate-400';
      heroLabel = 'Situação';
    } else if (Math.abs(diffVal) < 0.01) {
      diffColorClass = 'text-emerald';
      heroLabel = 'Caixa Conciliado';
      heroBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">100% Batido</span>`;
    } else if (diffVal < 0) {
      diffColorClass = 'text-rose';
      heroLabel = 'Falta Apurada';
      heroBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-rose-500/15 text-rose-300 border border-rose-500/30">Furo de Caixa</span>`;
    } else {
      diffColorClass = 'text-emerald';
      heroLabel = 'Sobra Apurada';
      heroBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">Sobra de Caixa</span>`;
    }

    const diffFormatted = (isNoMovement || isUnavailable)
      ? '—'
      : this.formatSignedBRL(diffVal);

    // Valores do Comparativo
    const autRev = Number(metrics.automation_revenue ?? resumo.faturamento_pista_total ?? 0);
    const autVol = Number(metrics.automation_volume_liters ?? tri.total_litros_automacao ?? 0);
    const posRev = Number(metrics.pos_revenue ?? resumo.faturamento_caixa_total ?? 0);

    const encState = metrics.physical_volume_state || (tri.total_litros_faturados_encerrante === 0 && autVol > 0 ? 'not_reported' : 'measured');
    const encVol = metrics.physical_volume_liters ?? (encState === 'not_reported' ? null : Number(tri.total_litros_faturados_encerrante || 0));

    // Bloco de Limitação
    let limitationHtml = '';
    const limText = assessment.limitation || (isPartial ? 'Caixas abertos no PDV e encerrantes pendentes no ERP' : null);
    if (limText && !isNoMovement && !isUnavailable) {
      limitationHtml = `
        <div class="decision-limitation-callout">
          <span class="text-sm">⚠️</span>
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
              <span class="text-amber-400 font-bold">⏳</span>
              <span class="font-semibold text-slate-200">${this.escapeHtml(p.label)}</span>
            </div>
            <span class="text-[10px] text-slate-400 font-mono flex items-center gap-1">
              <span>${badgeTag}</span>
              <span>↗</span>
            </span>
          </div>
        `;
      }).join('');

      pendingHtml = `
        <div class="space-y-1.5">
          <span class="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold">Pendências Operacionais:</span>
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
              <span>📅 ${this.escapeHtml(dataAuditada)}</span>
              <span>•</span>
              <span>⏰ ${this.escapeHtml(turnoAuditado)}</span>
              <span>•</span>
              <span>⛽ CBC04 + PDV</span>
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
              <span class="decision-comp-label">Automação CBC04</span>
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
                ${encState === 'not_reported' ? 'Pendente' : (encVol !== null ? this.formatLiters(encVol, 1) : '—')}
              </strong>
              <span class="decision-comp-sub">${encState === 'not_reported' ? 'Não digitado no ERP' : 'Lançado no fechabomba'}</span>
            </div>
          </div>
        ` : ''}

        ${pendingHtml}

        <!-- Ações Permitidas (Uma primária + botões de evidência) -->
        <div class="decision-actions">
          <button 
            type="button" 
            class="decision-btn-primary" 
            onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'resumo');"
            title="Abrir painel lateral com proveniência e detalhamento">
            <span class="text-xs">📋</span>
            <span>${this.escapeHtml(recLabel)} ↗</span>
          </button>

          <button 
            type="button" 
            class="decision-btn-secondary" 
            onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'formula');"
            title="Ver fórmula matemática e definição do cálculo">
            <span class="text-xs">📐</span>
            <span>Como foi calculado</span>
          </button>

          ${pendingItems.length > 0 ? `
            <button 
              type="button" 
              class="decision-btn-secondary" 
              onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'resumo');"
              title="Ver lista de pendências impeditivas">
              <span class="text-xs">⏳</span>
              <span>Ver pendências (${pendingItems.length})</span>
            </button>
          ` : ''}

          <button 
            type="button" 
            class="decision-btn-secondary" 
            onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'bicos');"
            title="Ver todos os bicos da pista e encerrantes">
            <span class="text-xs">⛽</span>
            <span>Ver Bicos & Caixas</span>
          </button>
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

    const drawer = document.getElementById('aura-evidence-drawer');
    const overlay = document.getElementById('aura-evidence-drawer-overlay');
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
      'shift_reconciliation': `Evidências: ${dataAuditada} (${turnoAuditado})`
    };

    if (titleEl) titleEl.textContent = titleMap[intent] || `Evidências: ${dataAuditada}`;
    if (chipEl) {
      chipEl.textContent = assessment.badge_label || (assessment.finality === 'partial' ? 'Provisório' : 'Validado');
      const isCrit = assessment.severity === 'critical';
      const isAttn = assessment.severity === 'attention' || assessment.finality === 'partial';
      chipEl.className = `px-2 py-0.5 rounded-full text-[10px] font-sans font-semibold ${isCrit ? 'bg-rose-500/15 text-rose-300 border border-rose-500/30' : (isAttn ? 'bg-amber-500/15 text-amber-300 border border-amber-500/30' : 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30')}`;
    }
    if (subEl) {
      const subMap = {
        'tank_forecast': `Unidade: ${c.context?.unit_id || 'Posto'} • Tanques & Previsão de Run-Out • ERP Leitura`,
        'pump_performance': `Unidade: ${c.context?.unit_id || 'Posto'} • Telemetria CBC04 Companytec & PDV`,
        'lmc_report': `Unidade: ${c.context?.unit_id || 'Posto'} • Portaria ANP 26/1992 • Tolerância ±0.60%`,
        'market_basket': `Unidade: ${c.context?.unit_id || 'Loja'} • Market Basket PDV (pedido + itemped)`,
        'shift_reconciliation': `Unidade: ${c.context?.unit_id || 'Posto'} • Data: ${dataAuditada} • Turno: ${turnoAuditado}`
      };
      subEl.textContent = subMap[intent] || `Unidade: ${c.context?.unit_id || 'Posto'}`;
    }

    this.switchEvidenceTab(activeTab);

    overlay.classList.add('open');
    drawer.classList.add('open');

    const closeBtn = document.getElementById('btn-close-evidence-drawer');
    if (closeBtn) closeBtn.focus();
    if (typeof window !== 'undefined' && window.lucide) window.lucide.createIcons();
  }

  /**
   * Fecha o Drawer Lateral de Evidências e devolve o foco ao botão chamador
   */
  closeEvidence() {
    if (typeof document === 'undefined') return;
    const drawer = document.getElementById('aura-evidence-drawer');
    const overlay = document.getElementById('aura-evidence-drawer-overlay');
    if (drawer) drawer.classList.remove('open');
    if (overlay) overlay.classList.remove('open');

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
    if (!data || (typeof data !== 'object') || (!data.contrato && !data.resumo_executivo && !data.assessment && !data.metrics)) {
      return `<div class="p-6 text-center text-slate-400 font-mono text-xs">Dados de evidência indisponíveis para este item.</div>`;
    }

    const c = data.contrato || data;
    const assessment = c.assessment || {};
    const metrics = c.metrics || {};
    const sources = c.sources || [];
    const intent = c.intent || data.intent || 'shift_reconciliation';
    const dataAuditada = data.data_auditada || c.context?.data_auditada || (c.context?.queried_at ? new Date(c.context.queried_at).toLocaleDateString('pt-BR') : 'Data Recente');

    // =========================================================================
    // ABA: COMO FOI CALCULADO (FÓRMULAS & DEFINIÇÕES CANÔNICAS)
    // =========================================================================
    if (tab === 'formula') {
      if (intent === 'tank_forecast') {
        const menorRes = assessment.horizonte_critico_horas ?? metrics.autonomia_critica_horas ?? metrics.menor_autonomia_runout_horas ?? assessment.menor_autonomia_horas ?? 'N/A';
        const menorEsg = assessment.horizonte_runout_horas ?? metrics.autonomia_runout_horas ?? metrics.menor_autonomia_esgotamento_horas ?? assessment.menor_autonomia_esgotamento_horas ?? 'N/A';
        return `
          <div class="space-y-4">
            <div class="evidence-section-card">
              <h4 class="font-bold text-slate-100 flex items-center gap-2">
                <span>📐</span><span>Fórmula de Autonomia até Reserva de Segurança (15%)</span>
              </h4>
              <div class="p-3 rounded-lg bg-slate-900 border border-slate-800 font-mono text-xs space-y-2">
                <div class="text-cyan-400 font-bold">Autonomia_15h = (Volume_Atual - Reserva_Tecnica_15%) / Consumo_Medio_Horario</div>
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
                <span>⏱</span><span>Fórmula de Esgotamento Total (0 L) vs Espaço Livre (Ullage)</span>
              </h4>
              <div class="p-3 rounded-lg bg-slate-900 border border-slate-800 font-mono text-xs space-y-2">
                <div class="text-cyan-400 font-bold">Autonomia_0h = Volume_Atual / Consumo_Medio_Horario</div>
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
                <span>📐</span><span>Fórmula de Vazão Operacional de Bicos (L/min)</span>
              </h4>
              <div class="p-3 rounded-lg bg-slate-900 border border-slate-800 font-mono text-xs space-y-2">
                <div class="text-cyan-400 font-bold">Vazão (L/min) = Volume Abastecido (L) / Duração do Abastecimento (min)</div>
                <div class="text-slate-300">
                  Telemetria automatizada recebida via concentrador CBC04 Companytec.
                </div>
                <div class="text-amber-400 font-bold pt-1 border-t border-slate-800">
                  Threshold Operacional: Vazão &lt; 30.0 L/min indica saturação precoce de elemento filtrante ou perda de sucção da bomba mecânica.
                </div>
              </div>
            </div>

            <div class="evidence-section-card">
              <h4 class="font-bold text-slate-100 flex items-center gap-2">
                <span>⛽</span><span>Fórmula de Conversão em Gasolina Aditivada (%)</span>
              </h4>
              <div class="p-3 rounded-lg bg-slate-900 border border-slate-800 font-mono text-xs space-y-2">
                <div class="text-cyan-400 font-bold">Conversão Aditivada (%) = (Volume Aditivada / Volume Total do Colaborador) × 100</div>
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
                <span>📐</span><span>Fórmula Legal da Portaria ANP nº 26/1992</span>
              </h4>
              <div class="p-3 rounded-lg bg-slate-900 border border-slate-800 font-mono text-xs space-y-2">
                <div class="text-cyan-400 font-bold">Estoque Escriturado = Estoque Inicial + Entradas Fiscais (NFe) - Saídas dos Bicos</div>
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
                <span>📐</span><span>Fórmulas de Mineração de Regras de Associação</span>
              </h4>
              <div class="p-3 rounded-lg bg-slate-900 border border-slate-800 font-mono text-xs space-y-2">
                <div class="text-cyan-400 font-bold">Suporte(A ∪ B) = Cupons(A e B) / Total de Cupons (N)</div>
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

      // Default: shift_reconciliation
      if (assessment.finality === 'no_movement' || data.status === 'sem_movimento') {
        return `
          <div class="evidence-section-card">
            <h4 class="font-bold text-slate-100 flex items-center gap-2">
              <span>⏸️</span><span>Sem Movimentação Registrada</span>
            </h4>
            <p class="text-slate-300 text-xs leading-relaxed p-3 rounded-lg bg-slate-900 border border-slate-800 font-mono">
              Não foram encontrados lançamentos de bicos, cupons fiscais ou movimentação de caixas para a data consultada (${this.escapeHtml(dataAuditada)}). Por isso, nenhuma diferença contábil ou volumétrica foi apurada.
            </p>
          </div>
        `;
      }

      if (assessment.finality === 'unavailable' || data.status === 'indisponivel') {
        return `
          <div class="evidence-section-card">
            <h4 class="font-bold text-slate-100 flex items-center gap-2">
              <span>⚠️</span><span>Fonte Indisponível</span>
            </h4>
            <p class="text-slate-300 text-xs leading-relaxed p-3 rounded-lg bg-slate-900 border border-slate-800 font-mono">
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
          <div class="p-3 rounded-lg bg-slate-900 border border-slate-800 font-mono text-xs space-y-2">
            <div class="text-cyan-400 font-bold">Triangulação Volumétrica: Pendência de Leitura Física</div>
            <div class="text-slate-300 space-y-1">
              <div>Automação CBC04: <strong class="text-cyan-300">${this.formatLiters(autVol, 3)}</strong></div>
              <div>Encerrantes Físicos: <strong class="text-amber-400">Pendente / Não digitado no módulo fechabomba</strong></div>
              <div class="pt-1 border-t border-slate-800 text-slate-400">Divergência Pista: <strong class="text-amber-300">Diferença provisória (aguardando leitura dos bicos)</strong></div>
            </div>
          </div>
          <p class="text-slate-400 text-xs leading-relaxed">
            ⚠️ <strong>Dado ausente:</strong> A ausência de digitação de encerrantes mecânicos <em>não representa 0 L medidos</em>. O fechamento físico permanece provisório até a conferência pelo chefe de pista.
          </p>
        `;
      } else if (encState === 'zero_registered') {
        volumetricContent = `
          <div class="p-3 rounded-lg bg-slate-900 border border-slate-800 font-mono text-xs space-y-2">
            <div class="text-cyan-400 font-bold">Divergência Pista = Volume Automação - Encerrantes Faturados</div>
            <div class="text-slate-300">
              ${this.formatLiters(autVol, 3)} (CBC04) - ${this.formatLiters(0, 3)} (fechabomba) = 
              <strong class="text-emerald-400">${this.formatLiters(0, 3)}</strong>
            </div>
          </div>
          <p class="text-slate-400 text-xs leading-relaxed">
            ✓ Zero efetivamente registrado: Turno confirmado sem saídas nos bicos.
          </p>
        `;
      } else {
        const diffVol = autVol - (encVol || 0);
        volumetricContent = `
          <div class="p-3 rounded-lg bg-slate-900 border border-slate-800 font-mono text-xs space-y-2">
            <div class="text-cyan-400 font-bold">Divergência Pista = Volume Automação - Encerrantes Faturados</div>
            <div class="text-slate-300">
              ${this.formatLiters(autVol, 3)} (CBC04) - ${this.formatLiters(encVol, 3)} (fechabomba) = 
              <strong class="${Math.abs(diffVol) < 0.01 ? 'text-emerald-400' : 'text-amber-400'}">${diffVol > 0 ? '+' : ''}${this.formatLiters(diffVol, 3)}</strong>
            </div>
          </div>
          <p class="text-slate-400 text-xs leading-relaxed">
            ${Math.abs(diffVol) < 0.01 ? '✓ Encerrantes físicos 100% batidos com a telemetria CBC04.' : '⚠️ Diferença apurada entre medição mecânica e telemetria CBC04.'}
          </p>
        `;
      }

      return `
        <div class="space-y-4">
          <div class="evidence-section-card">
            <h4 class="font-bold text-slate-100 flex items-center gap-2">
              <span>📐</span><span>Fórmula da Conciliação Financeira</span>
            </h4>
            <div class="p-3 rounded-lg bg-slate-900 border border-slate-800 font-mono text-xs space-y-2">
              <div class="text-cyan-400 font-bold">Diferença = Faturamento PDV - Automação CBC04</div>
              <div class="text-slate-300">
                ${this.formatBRL(posRev)} (PDV) - ${this.formatBRL(autRev)} (CBC04) = 
                <strong class="${diff < 0 ? 'text-amber-400' : 'text-emerald-400'}">${this.formatSignedBRL(diff)}</strong>
              </div>
            </div>
            <p class="text-slate-400 text-xs leading-relaxed">
              ${assessment.finality === 'partial' ? '⚠️ <strong>Diferença Provisória:</strong> Como os operadores ainda possuem caixa aberto no PDV e/ou encerrantes mecânicos pendentes, esta diferença não representa uma quebra confirmada.' : '✓ <strong>Diferença Definitiva:</strong> Fechamento apurado após o encerramento formal de todos os caixas.'}
            </p>
          </div>

          <div class="evidence-section-card">
            <h4 class="font-bold text-slate-100 flex items-center gap-2">
              <span>⛽</span><span>Triangulação Volumétrica da Pista</span>
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
      const nozzlesList = c.nozzles || data.auditoria_vazao_bicos || data.vazao_bicos || data.triangulacao_pista?.detalhamento_bicos || [];
      if (nozzlesList.length === 0) {
        return `<div class="p-4 text-center text-slate-500 font-mono text-xs">Sem dados detalhados de bicos para esta consulta.</div>`;
      }

      const rows = nozzlesList.map(b => {
        const vazao = b.vazao_media_l_min ?? b.vazao_litros_minuto ?? b.vazao_media_litros_minuto;
        const isLenta = b.alerta_filtro_lento || b.alerta_vazao_lenta || b.alerta_filtro || (vazao !== undefined && parseFloat(vazao) < 30.0);
        const vazaoText = vazao !== undefined ? `${parseFloat(vazao).toFixed(1)} L/min` : 'N/A';
        const volText = this.formatLiters(Number(b.volume_total_litros ?? b.volume_automacao_litros ?? 0), 1);
        const prod = b.combustivel || b.produto_nome || 'Combustível';

        return `
          <tr class="border-b border-slate-800/80 text-[11px] font-mono">
            <td class="py-2.5 font-bold text-slate-200">Bico ${this.escapeHtml(b.bico)}</td>
            <td class="py-2.5 text-slate-300">${this.escapeHtml(prod)}</td>
            <td class="py-2.5 text-right ${isLenta ? 'text-rose-400 font-bold' : 'text-emerald-300'} tabular-nums">${vazaoText}</td>
            <td class="py-2.5 text-right text-cyan-300 tabular-nums">${volText}</td>
            <td class="py-2.5 text-right">
              <span class="px-1.5 py-0.5 rounded text-[10px] ${isLenta ? 'bg-rose-500/15 text-rose-300 border border-rose-500/30' : 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'}">
                ${isLenta ? '⚠️ Filtro Lento' : '✓ Normal'}
              </span>
            </td>
          </tr>
        `;
      }).join('');

      return `
        <div class="space-y-3">
          <div class="flex items-center justify-between text-xs font-mono text-slate-400">
            <span>Total de Bicos Monitorados: <strong>${nozzlesList.length}</strong></span>
            <span>Automação: CBC04 Companytec</span>
          </div>
          <div class="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/60 p-1">
            <table class="w-full text-left font-mono">
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
      if (intent === 'market_basket') {
        const rulesList = c.detailed_rules || c.top_combos || data.regras_associacao_detalhadas || [];
        if (rulesList.length === 0) {
          return `<div class="p-4 text-center text-slate-500 font-mono text-xs">Nenhuma regra minerada para esta consulta.</div>`;
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
            <tr class="border-b border-slate-800/80 text-[11px] font-mono">
              <td class="py-2.5 font-bold text-slate-200">${this.escapeHtml(regraStr)}</td>
              <td class="py-2.5 text-right text-slate-300 tabular-nums">${supVal}%</td>
              <td class="py-2.5 text-right text-cyan-300 tabular-nums">${confVal}%</td>
              <td class="py-2.5 text-right ${isForte ? 'text-purple-300 font-bold' : 'text-slate-200'} tabular-nums">${liftVal}x</td>
              <td class="py-2.5 text-right">
                <span class="px-1.5 py-0.5 rounded text-[10px] ${isForte ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30' : 'bg-slate-800 text-slate-400'}">
                  ${isForte ? '⚡ Forte Sinergia' : '✓ Positiva'}
                </span>
              </td>
            </tr>
          `;
        }).join('');

        return `
          <div class="space-y-3">
            <div class="flex items-center justify-between text-xs font-mono text-slate-400">
              <span>Total de Regras Mineradas: <strong>${rulesList.length}</strong></span>
              <span>Algoritmo: Market Basket PDV</span>
            </div>
            <div class="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/60 p-1">
              <table class="w-full text-left font-mono">
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
        return `<div class="p-4 text-center text-slate-500 font-mono text-xs">Sem caixas registrados na data auditada.</div>`;
      }

      const rows = caixasList.map(cItem => {
        let opName = String(cItem.operador || 'Operador não informado').trim();
        return `
          <div class="p-3 rounded-xl border border-slate-800 bg-slate-900/60 space-y-2 font-mono text-xs">
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

      return `<div class="space-y-3">${rows}</div>`;
    }

    // =========================================================================
    // ABA: TANQUES & ANP
    // =========================================================================
    if (tab === 'tanques') {
      if (intent === 'tank_forecast') {
        const tanksList = c.tanks || data.detalhamento_tanques || data.tanques || [];
        if (tanksList.length === 0) {
          return `<div class="p-4 text-center text-slate-500 font-mono text-xs">Sem tanques auditados neste relatório.</div>`;
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
            <div class="p-3 rounded-xl border border-slate-800 bg-slate-900/60 space-y-2 font-mono text-xs">
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

        return `<div class="space-y-3">${rows}</div>`;
      }

      if (intent === 'lmc_report') {
        const tanksList = c.tanks || data.demonstrativo_por_combustivel || data.tanques || [];
        if (tanksList.length === 0) {
          return `<div class="p-4 text-center text-slate-500 font-mono text-xs">Sem tanques auditados no LMC.</div>`;
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
            <div class="p-3 rounded-xl border border-slate-800 bg-slate-900/60 space-y-2 font-mono text-xs">
              <div class="flex items-center justify-between">
                <span class="font-bold text-slate-100">TQ-${this.escapeHtml(cod)} • ${this.escapeHtml(comb)}</span>
                <span class="px-2 py-0.5 rounded text-[10px] font-semibold ${isConf ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30' : 'bg-rose-500/15 text-rose-300 border border-rose-500/30'}">
                  ${isConf ? '✓ Conforme ANP (±0.6%)' : '🚨 Alerta ANP'}
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

        return `<div class="space-y-3">${rows}</div>`;
      }

      // Default: Balanço de tanques turno
      const tanquesList = data.balanco_tanques?.detalhamento_tanques || [];
      if (tanquesList.length === 0) {
        return `<div class="p-4 text-center text-slate-500 font-mono text-xs">Sem tanques auditados neste fechamento.</div>`;
      }

      const rows = tanquesList.map(t => {
        const isConf = t.status_anp?.includes('CONFORME');
        return `
          <div class="p-3 rounded-xl border border-slate-800 bg-slate-900/60 space-y-2 font-mono text-xs">
            <div class="flex items-center justify-between">
              <span class="font-bold text-slate-100">TQ-${this.escapeHtml(t.codtan ?? 'N/D')} • ${this.escapeHtml(t.combustivel ?? 'N/D')}</span>
              <span class="px-2 py-0.5 rounded text-[10px] font-semibold ${isConf ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30' : 'bg-rose-500/15 text-rose-300 border border-rose-500/30'}">
                ${isConf ? '✓ Conforme ANP' : '⚠️ Alerta ANP'}
              </span>
            </div>
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] text-slate-300 pt-1 border-t border-slate-800">
              <div><span class="text-slate-400">Capacidade:</span> ${this.formatLiters(t.capacidade_litros, 0)}</div>
              <div><span class="text-slate-400">Saldo Inicial:</span> ${this.formatLiters(t.saldo_inicial, 0)}</div>
              <div><span class="text-slate-400">Saldo Final:</span> ${this.formatLiters(t.saldo_final, 0)}</div>
              <div><span class="text-slate-400">Saída Bicos:</span> ${this.formatLiters(t.saida_bicos_litros, 1)}</div>
            </div>
          </div>
        `;
      }).join('');

      return `<div class="space-y-3">${rows}</div>`;
    }

    // =========================================================================
    // ABA PADRÃO: RESUMO & FONTES DE DADOS
    // =========================================================================
    const sourcesList = sources.map(s => {
      let stBadge = '<span class="text-emerald-400 font-semibold">✓ Disponível</span>';
      if (s.availability === 'missing') stBadge = '<span class="text-amber-400 font-semibold">⏳ Pendente / Não lançado</span>';
      if (s.availability === 'unavailable') stBadge = '<span class="text-rose-400 font-semibold">⚠️ Indisponível</span>';

      return `
        <div class="p-3 rounded-xl border border-slate-800 bg-slate-900/60 flex items-center justify-between font-mono text-xs">
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
      <div class="space-y-4">
        <div class="evidence-section-card">
          <h4 class="font-bold text-slate-100 flex items-center gap-2">
            <span>📡</span><span>Proveniência e Disponibilidade das Fontes</span>
          </h4>
          <div class="space-y-2">${sourcesList || '<div class="text-slate-500">Fontes padrão do ERP (Somente Leitura)</div>'}</div>
        </div>

        <div class="evidence-section-card">
          <h4 class="font-bold text-slate-100 flex items-center gap-2">
            <span>📝</span><span>Diagnóstico Executivo</span>
          </h4>
          <p class="text-slate-300 leading-relaxed text-xs p-3 rounded-lg bg-slate-900 border border-slate-800">
            ${this.escapeHtml(explanationText)}
          </p>
        </div>

        ${limText ? `
          <div class="evidence-section-card">
            <h4 class="font-bold text-slate-100 flex items-center gap-2">
              <span>⚠️</span><span>Limitações e Premissas da Consulta</span>
            </h4>
            <p class="text-amber-200/90 leading-relaxed text-xs p-3 rounded-lg bg-amber-950/20 border border-amber-500/20 font-mono">
              ${this.escapeHtml(limText)}
            </p>
          </div>
        ` : ''}

        <div class="p-3 rounded-xl bg-slate-900/40 border border-slate-800/60 text-[10px] font-mono text-slate-500 flex items-center justify-between">
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
      return `<div class="decision-card"><p class="text-xs text-slate-400">Dados de Market Basket indisponíveis.</p></div>`;
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

    const isNoMovement = assessment.status_code === 'SEM_REGISTROS' || data.status === 'sem_movimento';
    const isUnavailable = assessment.status_code === 'INDISPONIVEL' || data.status === 'indisponivel';

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
    let badgeIcon = '⚡';
    let badgeText = assessment.badge_label || `⚡ Max Lift: ${parseFloat(maxLiftVal).toFixed(2)}x`;

    if (isNoMovement) {
      badgeClass = 'status-neutral';
      badgeIcon = '⏸️';
      badgeText = 'Sem Cupons';
    } else if (isUnavailable) {
      badgeClass = 'status-divergent';
      badgeIcon = '⚠️';
      badgeText = 'Fonte Indisponível';
    } else if (countForteSinergia > 0) {
      badgeClass = 'status-validated';
      badgeIcon = '⚡';
      badgeText = assessment.badge_label || `⚡ Max Lift: ${parseFloat(maxLiftVal).toFixed(2)}x`;
    } else if (totalMultiplas === 0) {
      badgeClass = 'status-partial';
      badgeIcon = '⚠️';
      badgeText = 'Cestas sem Multiplicidade';
    } else {
      badgeClass = 'status-neutral';
      badgeIcon = '✓';
      badgeText = 'Regras Mineradas';
    }

    // Hero Metric: Maior Lift
    const heroLabel = 'Maior Multiplicador de Sinergia (Lift)';
    const heroVal = isNoMovement || isUnavailable ? '—' : `${parseFloat(maxLiftVal).toFixed(2)}x`;
    const heroColorClass = isNoMovement || isUnavailable ? 'text-slate-400' : (parseFloat(maxLiftVal) >= 2.0 ? 'text-purple-300' : 'text-emerald');
    const heroSub = `${countForteSinergia} combo(s) com forte sinergia (Lift ≥ 2.0x) • ${totalTransacoes} cupons analisados (${parseFloat(pctMultiplas).toFixed(1)}% cestas múltiplas).`;

    // Bloco de Limitação (F5-02 & F5-08)
    let limitationHtml = '';
    const limText = assessment.limitation || resumo.limitation;
    if (limText && !isNoMovement && !isUnavailable) {
      limitationHtml = `
        <div class="decision-limitation-callout">
          <span class="text-sm">⚠️</span>
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
        <div class="widget-combo-card">
          <div class="flex items-center justify-between text-xs font-mono mb-1">
            <span class="font-bold text-white flex items-center gap-1.5">
              <span>${isForte ? '⚡' : '🛒'}</span>
              <span>${this.escapeHtml(prodOrig)}</span>
            </span>
            <span class="text-purple-400 font-bold">➔</span>
            <span class="font-bold text-auraCyan-light">${this.escapeHtml(prodDest)}</span>
          </div>

          <div class="flex flex-wrap items-center gap-2 font-mono text-[10px] text-slate-400 my-1">
            <span class="px-1.5 py-0.5 rounded ${isForte ? 'bg-purple-500/25 text-purple-200 border-purple-500/40' : 'bg-slate-800 text-slate-300 border-slate-700'} font-bold border tabular-nums">
              ⚡ Lift ${lift}x
            </span>
            <span class="px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 tabular-nums">
              🎯 Confiança ${conf}%
            </span>
            <span class="tabular-nums">📦 ${cupons} cupons</span>
            ${pRecVal > 0 ? `<span class="text-emerald-400 font-semibold tabular-nums">+${this.formatBRL(pRecVal)}${incrPct ? ` (+${incrPct}%)` : ''}</span>` : ''}
          </div>

          <div class="widget-combo-script-box">
            <strong>🗣 Script no Balcão:</strong> "${this.escapeHtml(script)}"
          </div>

          <div class="flex justify-end mt-2">
            <button type="button" class="widget-action-btn purple" onclick="if (window.auraChat) window.auraChat.sendUserPrompt('Qual o estoque atual de ${this.escapeHtml(prodDest)}?');">
              📦 Checar Estoque (${this.escapeHtml(prodDestShort)})
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
            <span class="text-purple-400 font-bold">💡</span>
            <span class="font-semibold text-slate-200">${this.escapeHtml(p.label)}</span>
          </div>
          <span class="text-[10px] text-slate-400 font-mono flex items-center gap-1">
            <span>Combos</span>
            <span>↗</span>
          </span>
        </div>
      `).join('');

      pendingHtml = `
        <div class="space-y-1.5">
          <span class="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold">Oportunidades de Venda Cruzada:</span>
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
              <span>📅 ${this.escapeHtml(dataConsulta)}</span>
              <span>•</span>
              <span>🛒 PDV / Cestas de Compras</span>
              <span>•</span>
              <span>🏢 ${this.escapeHtml(c.context?.unit_id || 'Loja')}</span>
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
            <span class="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-purple-500/15 text-purple-300 border border-purple-500/30">
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
          ${cardsHtml || '<div class="text-xs font-mono text-slate-400">Nenhum combo com o filtro solicitado retornado.</div>'}
        </div>

        ${pendingHtml}

        <!-- Ações Permitidas -->
        <div class="decision-actions">
          <button 
            type="button" 
            class="decision-btn-primary" 
            onclick="if (window.auraChat) window.auraChat.sendUserPrompt('Quais os scripts de balcão recomendados para a equipe do caixa?');"
            title="Capacitar operadores com roteiro persuasivo no PDV">
            <span class="text-xs">🛒</span>
            <span>${this.escapeHtml(recLabel)}</span>
          </button>

          <button 
            type="button" 
            class="decision-btn-secondary" 
            onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'formula');"
            title="Ver definições matemáticas de Suporte, Confiança e Lift">
            <span class="text-xs">📐</span>
            <span>Como foi calculado</span>
          </button>

          <button 
            type="button" 
            class="decision-btn-secondary" 
            onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'caixas');"
            title="Ver tabela detalhada de todas as regras mineradas">
            <span class="text-xs">📊</span>
            <span>Ver Regras Detalhadas</span>
          </button>

          <button 
            type="button" 
            class="decision-btn-secondary" 
            onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'resumo');"
            title="Ver fontes de dados e diagnósticos">
            <span class="text-xs">📋</span>
            <span>Resumo & Fontes</span>
          </button>
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

    const isNoMovement = assessment.status_code === 'SEM_MOVIMENTACAO' || data.status === 'sem_movimento';
    const isUnavailable = assessment.status_code === 'INDISPONIVEL' || data.status === 'indisponivel';

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
    let badgeIcon = '✓';
    let badgeText = assessment.badge_label || (bicosLentosCount > 0 ? `⚠️ ${bicosLentosCount} Bicos Lentos (<30 L/min)` : '✓ Pista Operando Conforme');

    if (isNoMovement) {
      badgeClass = 'status-neutral';
      badgeIcon = '⏸️';
      badgeText = assessment.badge_label || 'Sem Movimentação';
    } else if (isUnavailable) {
      badgeClass = 'status-divergent';
      badgeIcon = '⚠️';
      badgeText = 'Fonte Indisponível';
    } else if (bicosLentosCount > 0) {
      badgeClass = 'status-partial';
      badgeIcon = '⚠️';
      badgeText = assessment.badge_label || `⚠️ ${bicosLentosCount} Bicos Lentos (<30 L/min)`;
    } else {
      badgeClass = 'status-validated';
      badgeIcon = '✓';
      badgeText = assessment.badge_label || '✓ Pista Operando Conforme';
    }

    // Hero Metric: Faturamento da Pista
    const fatPista = Number(metrics.faturamento_total ?? metrics.faturamento_total_pista ?? resumo.faturamento_pista_total ?? 0);
    const liderNome = assessment.melhor_frentista_nome ?? resumo.campeao_faturamento?.nome ?? resumo.lider_faturamento ?? (ranking[0]?.nome || ranking[0]?.frentista || 'Colaborador');
    const liderObj = ranking[0] || {};
    const liderFat = Number(liderObj.faturamento_reais ?? 0);
    const liderAdit = parseFloat(liderObj.conversao_aditivada_pct ?? liderObj.percentual_aditivada ?? 0).toFixed(1);

    const heroLabel = 'Faturamento Total da Pista';
    const heroVal = isNoMovement || isUnavailable ? '—' : this.formatBRL(fatPista);
    const heroColorClass = isNoMovement || isUnavailable ? 'text-slate-400' : 'text-emerald';
    const heroSub = ranking.length > 0
      ? `Líder: ${liderNome} (${this.formatBRL(liderFat)}, Aditivada: ${liderAdit}%) • Ticket Médio da Pista: ${this.formatBRL(metrics.ticket_medio ?? metrics.ticket_medio_pista ?? resumo.ticket_medio_pista ?? 0)}.`
      : 'Sem abastecimentos registrados no período.';

    // Comparativo Compacto
    const volPista = Number(metrics.total_litros ?? metrics.volume_total_litros ?? resumo.volume_total_litros ?? 0);
    const txAditGlobal = parseFloat(metrics.taxa_conversao_aditivada_geral_pct ?? metrics.taxa_conversao_aditivada_global_pct ?? resumo.conversao_aditivada_geral_pct ?? 0).toFixed(1);
    const vazaoMedia = parseFloat(metrics.vazao_media_l_min ?? metrics.vazao_media_geral_litros_minuto ?? resumo.vazao_media_pista_litros_minuto ?? 34.5).toFixed(1);

    // Bloco de Limitação (F5-02 & F5-05)
    let limitationHtml = '';
    const limText = assessment.limitation || resumo.limitation;
    if (limText && !isNoMovement && !isUnavailable) {
      limitationHtml = `
        <div class="decision-limitation-callout">
          <span class="text-sm">⚠️</span>
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
      const medals = ['🥇', '🥈', '🥉'];
      const med = medals[idx] || '👤';
      const nomeFrent = f.nome || f.frentista || 'Colaborador';
      const fat = this.formatBRL(f.faturamento_reais || 0);
      const aditVal = parseFloat(f.conversao_aditivada_pct ?? f.percentual_aditivada ?? 0);
      const isMeta = aditVal >= 25.0;
      const atends = f.total_abastecimentos ?? f.atendimentos_count ?? 0;

      frentsHtml += `
        <div class="flex items-center justify-between p-2 rounded-xl bg-slate-900/60 border border-slate-800 text-xs font-mono">
          <div class="flex items-center gap-2 font-bold text-white">
            <span class="text-sm">${med}</span>
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
        <div class="p-3 rounded-xl bg-amber-950/25 border border-amber-500/30 text-amber-300 text-xs font-mono space-y-1.5">
          <div class="flex items-center gap-2 font-bold text-amber-400">
            <span>⚠️</span>
            <span class="uppercase tracking-wider text-[11px]">Bicos com Alerta de Vazão Lenta (&lt; 30 L/min):</span>
          </div>
          <p class="text-[10px] text-slate-300">
            Vazão reduzida prejudica a produtividade da pista e aponta necessidade de troca de elemento filtrante ou ajuste na unidade de sucção:
          </p>
          <div class="space-y-1 pt-1">
            ${bicosAlerta.map(b => {
              const vazao = parseFloat(b.vazao_media_l_min ?? b.vazao_litros_minuto ?? b.vazao_media_litros_minuto ?? 0).toFixed(1);
              const prod = b.combustivel || b.produto_nome || 'Combustível';
              return `<div class="flex items-center justify-between text-[11px] p-1 rounded bg-slate-900/60 border border-amber-500/20">
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
            <span class="text-amber-400 font-bold">🔧</span>
            <span class="font-semibold text-slate-200">${this.escapeHtml(p.label)}</span>
          </div>
          <span class="text-[10px] text-slate-400 font-mono flex items-center gap-1">
            <span>Bicos</span>
            <span>↗</span>
          </span>
        </div>
      `).join('');

      pendingHtml = `
        <div class="space-y-1.5">
          <span class="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold">Pendências Operacionais:</span>
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
              <span>📅 ${this.escapeHtml(dataConsulta)}</span>
              <span>•</span>
              <span>⛽ ${nozzles.length} Bicos Monitorados</span>
              <span>•</span>
              <span>🏢 ${this.escapeHtml(c.context?.unit_id || 'Posto')}</span>
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
            <span class="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
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
        <div class="space-y-1.5 mt-1">
          <span class="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold">Podium de Performance da Pista:</span>
          ${frentsHtml || '<div class="text-xs font-mono text-slate-400">Nenhum frentista retornado.</div>'}
        </div>

        ${bicosAlertHtml}
        ${pendingHtml}

        <!-- Ações Permitidas -->
        <div class="decision-actions">
          <button 
            type="button" 
            class="decision-btn-primary" 
            onclick="if (window.auraChat) window.auraChat.sendUserPrompt('Como programar a manutenção preventiva dos filtros de bicos de combustíveis?');"
            title="Abrir diretrizes de manutenção de bicos e bombas">
            <span class="text-xs">🔧</span>
            <span>${this.escapeHtml(recLabel)}</span>
          </button>

          <button 
            type="button" 
            class="decision-btn-secondary" 
            onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'formula');"
            title="Ver fórmulas de vazão e conversão de aditivada">
            <span class="text-xs">📐</span>
            <span>Como foi calculado</span>
          </button>

          <button 
            type="button" 
            class="decision-btn-secondary" 
            onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'bicos');"
            title="Ver detalhamento de todos os bicos da pista">
            <span class="text-xs">⛽</span>
            <span>Ver Bicos & Pista</span>
          </button>

          <button 
            type="button" 
            class="decision-btn-secondary" 
            onclick="if (window.auraChat) window.auraChat.openEvidence('${evId}', 'resumo');"
            title="Ver fontes de dados e diagnósticos">
            <span class="text-xs">📋</span>
            <span>Resumo & Fontes</span>
          </button>
        </div>
      </div>
    `;
  }

  /**
   * Widget Genérico para outras ferramentas analíticas
   */
  renderGenericToolWidget(toolName, data) {
    if (!data.resumo_executivo && !data.status) return '';
    const r = data.resumo_executivo || data;
    const displayName = this.formatToolDisplayName(toolName);
    return `
      <div class="widget-inline-container border-l-4 border-l-slate-600">
        <div class="widget-inline-header">
          <div class="flex items-center gap-2">
            <span class="text-sm">📊</span>
            <strong class="text-xs font-mono text-white uppercase tracking-wider">Diagnóstico: ${this.escapeHtml(displayName)}</strong>
          </div>
          <span class="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700">OK</span>
        </div>
        <div class="text-xs font-mono text-slate-300">
          ${this.escapeHtml(r.status || r.mensagem || 'Dados processados com sucesso.')}
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
        ${e2e ? `<span class="flex items-center gap-1"><span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> Resposta em <strong class="text-emerald-300 font-mono">${e2e}</strong></span>` : ''}
        <span class="text-slate-500">•</span>
        <span>Motor: <strong class="text-purple-300">${model}</strong></span>
        ${lgpd > 0 ? `<span class="text-slate-500">•</span><span class="text-emerald-400/90 font-medium">🛡️ LGPD: ${lgpd} dados protegidos</span>` : ''}
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
    const textIds = [containerId + '-text', containerId + '-split-text'];
    const html = `
      <div class="p-3 rounded bg-rose-950/20 border border-rose-500/40 text-rose-300 text-xs font-mono">
        <strong>⚠️ Falha de Conexão ou Resposta:</strong> ${this.escapeHtml(errorMsg)}
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
    const feeds = [
      document.getElementById('chat-feed-container'),
      document.getElementById('split-chat-feed-container')
    ];

    feeds.forEach(feed => {
      if (feed && (force || !this.userScrolledUp)) {
        feed.scrollTop = feed.scrollHeight;
      }
    });
  }

  formatBRL(val) {
    if (val === null || val === undefined || isNaN(Number(val))) return '—';
    const num = Number(val);
    return 'R$ ' + num.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  formatSignedBRL(val) {
    if (val === null || val === undefined || isNaN(Number(val))) return '—';
    const num = Number(val);
    if (Math.abs(num) < 0.005) {
      return 'R$ 0,00';
    }
    const prefix = num < 0 ? '-' : '+';
    return `${prefix}R$ ${Math.abs(num).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }

  formatLiters(val, decimals = 1) {
    if (val === null || val === undefined || isNaN(Number(val))) return '—';
    const num = Number(val);
    return `${num.toLocaleString('pt-BR', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })} L`;
  }

  formatNumber(val, decimals = 0) {
    if (val === null || val === undefined || isNaN(Number(val))) return '—';
    const num = Number(val);
    return num.toLocaleString('pt-BR', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  }

  formatPercent(val, decimals = 1) {
    if (val === null || val === undefined || isNaN(Number(val))) return '—';
    const num = Number(val);
    return `${num.toLocaleString('pt-BR', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}%`;
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
