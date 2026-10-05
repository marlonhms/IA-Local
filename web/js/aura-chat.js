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
      <div class="space-y-4">
        <div class="flex items-center gap-3 pb-2 border-b border-purple-500/20">
          <div class="w-10 h-10 rounded-2xl bg-gradient-to-tr from-emerald-500/20 via-cyan-500/20 to-purple-500/20 border border-cyan-500/30 flex items-center justify-center text-cyan-300 shadow-inner">
            <i data-lucide="sparkles" class="w-5 h-5 text-cyan-300"></i>
          </div>
          <div>
            <h3 class="text-white font-bold text-base">Olá! Seja bem-vindo à AURA</h3>
            <p class="text-slate-400 text-xs">Sua Assistente Executiva e Supervisora do Posto & PDV</p>
          </div>
        </div>

        <p class="text-slate-200 text-sm leading-relaxed">
          Estou de prontidão para apoiar sua gestão com foco total em assistência ágil, acolhedora e precisa. 
          Todas as consultas ao banco de dados ocorrem <strong>100% sob sua demanda</strong>, sem processos em segundo plano.
        </p>

        <div class="pt-2">
          <div class="text-xs font-medium text-slate-300 mb-3 flex items-center gap-1.5">
            <i data-lucide="compass" class="w-4 h-4 text-emerald-400"></i>
            <span>Por onde deseja começar? Escolha uma sugestão ou pergunte diretamente:</span>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 w-full">
            <button onclick="window.auraChat.sendUserPrompt('Qual a situação e autonomia de cada tanque agora?')" class="group p-3 rounded-xl bg-slate-900/80 hover:bg-slate-800/90 border border-slate-800 hover:border-emerald-500/40 text-left transition-all shadow-sm">
              <div class="flex items-center gap-2 mb-1">
                <span class="text-base">⛽</span>
                <span class="text-white font-semibold text-xs group-hover:text-emerald-300 transition-colors">Autonomia de Tanques</span>
              </div>
              <p class="text-[11px] text-slate-400 group-hover:text-slate-300 leading-snug">Previsão de esgotamento e pedido de carreta.</p>
            </button>

            <button onclick="window.auraChat.sendUserPrompt('Como fechou o último turno? Teve furo de caixa?')" class="group p-3 rounded-xl bg-slate-900/80 hover:bg-slate-800/90 border border-slate-800 hover:border-purple-500/40 text-left transition-all shadow-sm">
              <div class="flex items-center gap-2 mb-1">
                <span class="text-base">💰</span>
                <span class="text-white font-semibold text-xs group-hover:text-purple-300 transition-colors">Fechamento de Caixa</span>
              </div>
              <p class="text-[11px] text-slate-400 group-hover:text-slate-300 leading-snug">Triangulação de encerrantes e turno.</p>
            </button>

            <button onclick="window.auraChat.sendUserPrompt('O LMC de ontem fechou dentro da tolerância oficial da ANP?')" class="group p-3 rounded-xl bg-slate-900/80 hover:bg-slate-800/90 border border-slate-800 hover:border-cyan-500/40 text-left transition-all shadow-sm">
              <div class="flex items-center gap-2 mb-1">
                <span class="text-base">📋</span>
                <span class="text-white font-semibold text-xs group-hover:text-cyan-300 transition-colors">LMC Fiscal ANP</span>
              </div>
              <p class="text-[11px] text-slate-400 group-hover:text-slate-300 leading-snug">Auditoria Portaria 26 (margem ±0.6%).</p>
            </button>

            <button onclick="window.auraChat.sendUserPrompt('Quais os combos de vendas cruzadas com maior Lift na conveniência?')" class="group p-3 rounded-xl bg-slate-900/80 hover:bg-slate-800/90 border border-slate-800 hover:border-amber-500/40 text-left transition-all shadow-sm">
              <div class="flex items-center gap-2 mb-1">
                <span class="text-base">🛒</span>
                <span class="text-white font-semibold text-xs group-hover:text-amber-300 transition-colors">Vendas da Loja</span>
              </div>
              <p class="text-[11px] text-slate-400 group-hover:text-slate-300 leading-snug">Cross-selling e combos no caixa.</p>
            </button>

            <button onclick="window.auraChat.sendUserPrompt('Há algum bico com vazão lenta ou alerta na pista?')" class="group p-3 rounded-xl bg-slate-900/80 hover:bg-slate-800/90 border border-slate-800 hover:border-rose-500/40 text-left transition-all shadow-sm">
              <div class="flex items-center gap-2 mb-1">
                <span class="text-base">⚠️</span>
                <span class="text-white font-semibold text-xs group-hover:text-rose-300 transition-colors">Vazão dos Bicos</span>
              </div>
              <p class="text-[11px] text-slate-400 group-hover:text-slate-300 leading-snug">Alerta preventivo (&lt;30 L/min).</p>
            </button>

            <button onclick="window.auraChat.sendUserPrompt('Quem são os maiores clientes e frotistas da revenda?')" class="group p-3 rounded-xl bg-slate-900/80 hover:bg-slate-800/90 border border-slate-800 hover:border-sky-500/40 text-left transition-all shadow-sm">
              <div class="flex items-center gap-2 mb-1">
                <span class="text-base">🏆</span>
                <span class="text-white font-semibold text-xs group-hover:text-sky-300 transition-colors">Clientes VIP & Frotas</span>
              </div>
              <p class="text-[11px] text-slate-400 group-hover:text-slate-300 leading-snug">Ranking de clientes de maior volume.</p>
            </button>
          </div>
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
   * Roteador de Renderização de Widgets Inline Interativos no Chat
   */
  renderToolInlineWidget(toolName, data) {
    if (!data || typeof data !== 'object') return '';

    // 1. Roteamento prioritário por toolName canônico
    if (toolName === 'ajuda_sistema' || toolName === 'conhecimento_aura' || toolName === 'ajuda') {
      return this.renderAjudaSistemaWidget(data);
    }
    if (toolName === 'lmc_anp' || toolName === 'gerar_relatorio_lmc_anp') {
      return this.renderLmcAnpWidget(data);
    }
    if (toolName === 'previsao_tanques' || toolName === 'run_out' || toolName === 'prever_esgotamento_tanques') {
      return this.renderTankAutonomyWidget(data);
    }
    if (toolName === 'auditoria_turno' || toolName === 'conciliacao_turno' || toolName === 'auditar_fechamento_turno') {
      return this.renderTurnoWidget(data);
    }
    if (toolName === 'conveniencia_vendas_cruzadas' || toolName === 'auditar_cesta_conveniencia_vendas_cruzadas') {
      return this.renderCombosWidget(data);
    }
    if (toolName === 'desempenho_pista_frentistas' || toolName === 'auditar_desempenho_pista_frentistas') {
      return this.renderDesempenhoPistaWidget(data);
    }

    // 2. Roteamento por assinatura estrutural dos dados (fallback inteligente)
    if (
      data.ui_action ||
      (Array.isArray(data.artigos) && data.artigos.length > 0 && data.artigos[0]?.modulo)
    ) {
      return this.renderAjudaSistemaWidget(data);
    }
    if (
      data.resumo_executivo?.status_geral_anp ||
      Array.isArray(data.demonstrativo_por_combustivel) ||
      (Array.isArray(data.tanques) && data.tanques[0]?.auditoria_anp)
    ) {
      return this.renderLmcAnpWidget(data);
    }
    if (
      data.contrato?.intent === 'shift_reconciliation' ||
      data.intent === 'shift_reconciliation' ||
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
      Array.isArray(data.regras_associacao_detalhadas)
    ) {
      return this.renderCombosWidget(data);
    }
    if (
      Array.isArray(data.ranking_frentistas) ||
      Array.isArray(data.auditoria_vazao_bicos)
    ) {
      return this.renderDesempenhoPistaWidget(data);
    }
    if (
      Array.isArray(data.detalhamento_tanques) ||
      data.previsao_por_combustivel ||
      Array.isArray(data.tanques)
    ) {
      return this.renderTankAutonomyWidget(data);
    }

    // 3. Fallback genérico executivo
    return this.renderGenericToolWidget(toolName, data);
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
   * Widget 1: Mini-Barras Visuais de Nível de Tanques e Autonomia Restante
   */
  renderTankAutonomyWidget(data) {
    const resumo = data.resumo_executivo || {};
    const tanques = data.detalhamento_tanques || data.tanques || [];
    const statusGeral = resumo.status_geral || 'ESTÁVEL';
    const menorAutonomia = resumo.tanque_mais_critico?.autonomia_runout_horas ?? resumo.menor_autonomia_horas;

    let badgeStatus = '<span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">✓ ESTÁVEL</span>';
    if (statusGeral === 'ALERTA_ESTOQUE_CRITICO' || statusGeral === 'CRÍTICO') {
      badgeStatus = '<span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-500/20 text-rose-300 border border-rose-500/40 animate-pulse">🚨 CRÍTICO</span>';
    } else if (String(statusGeral).includes('ATENÇÃO')) {
      badgeStatus = '<span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">⚠️ ATENÇÃO</span>';
    }

    let tanksHtml = '';
    tanques.forEach(t => {
      const cod = t.codtan || t.tanque || '000';
      const comb = t.combustivel || 'Combustível';
      const pct = Math.min(100, Math.max(0, parseFloat(t.ocupacao_pct ?? t.ocupacao_percentual ?? 0)));
      const vol = parseFloat(t.saldo_atual_litros ?? t.volume_atual_litros ?? 0).toLocaleString('pt-BR', { maximumFractionDigits: 0 });
      const cap = parseFloat(t.capacidade_litros ?? 0).toLocaleString('pt-BR', { maximumFractionDigits: 0 });
      const horasVal = t.autonomia_runout_horas ?? t.autonomia_horas;
      const horas = (horasVal !== undefined && horasVal !== null && !isNaN(horasVal)) ? `${parseFloat(horasVal).toFixed(1)}h restantes` : 'N/A';
      const ullageVal = t.espaco_livre_ullage_litros ?? t.espaco_livre_descarga_litros;
      const ullage = (ullageVal !== undefined && ullageVal !== null) ? parseFloat(ullageVal).toLocaleString('pt-BR', { maximumFractionDigits: 0 }) : 'N/A';

      let fillClass = 'normal';
      let statusIcon = '🟢';
      const statusOp = String(t.status_operacional || t.status_nivel || '').toUpperCase();
      if (pct < 15 || statusOp.includes('CRÍTICO')) {
        fillClass = 'critical';
        statusIcon = '🚨';
      } else if (pct < 30 || statusOp.includes('ATENÇÃO')) {
        fillClass = 'warning';
        statusIcon = '🟡';
      }

      tanksHtml += `
        <div class="widget-tank-card">
          <div class="flex items-center justify-between text-xs font-mono">
            <span class="font-bold text-white flex items-center gap-1.5">
              <span>${statusIcon}</span>
              <span>TQ ${cod} • ${this.escapeHtml(comb)}</span>
            </span>
            <span class="text-slate-300 font-semibold">${pct.toFixed(1)}% <span class="text-slate-500 font-normal">(${vol} / ${cap} L)</span></span>
          </div>

          <div class="widget-tank-track">
            <div class="widget-tank-fill ${fillClass}" style="width: ${pct}%"></div>
          </div>

          <div class="flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono text-slate-400 mt-1">
            <div class="flex items-center gap-2">
              <span class="text-cyan-300 font-semibold">⏱ ${horas}</span>
              <span class="text-slate-600">|</span>
              <span class="text-slate-300">📦 Ullage livre: ${ullage} L</span>
            </div>
            <button class="widget-action-btn emerald" onclick="window.auraChat.sendUserPrompt('Qual a melhor sugestão de pedido de carreta para o Tanque ${cod}?')">
              🚚 Pedir Carreta
            </button>
          </div>
        </div>
      `;
    });

    return `
      <div class="widget-inline-container border-l-4 border-l-auraEmerald">
        <div class="widget-inline-header">
          <div class="flex items-center gap-2">
            <span class="text-sm">⛽</span>
            <strong class="text-xs font-mono text-white uppercase tracking-wider">Tanques Volumétricos & Previsão de Run-Out</strong>
          </div>
          <div class="flex items-center gap-2">
            ${menorAutonomia !== undefined && menorAutonomia !== null ? `<span class="text-[11px] font-mono text-cyan-300 font-bold">Mín: ${parseFloat(menorAutonomia).toFixed(1)}h</span>` : ''}
            ${badgeStatus}
          </div>
        </div>
        <div class="space-y-1">${tanksHtml || '<div class="text-xs font-mono text-slate-400">Nenhum tanque retornado.</div>'}</div>
      </div>
    `;
  }

  /**
   * Widget 2: Régua Visual da ANP [-0.6% a +0.6%] e Balanço Volumétrico
   */
  renderLmcAnpWidget(data) {
    const resumo = data.resumo_executivo || {};
    const items = data.demonstrativo_por_combustivel || data.tanques || [];
    const statusGeral = resumo.status_geral_anp || 'CONFORME_ANP';
    const isConforme = statusGeral === 'CONFORME_ANP' || statusGeral === 'CONFORME';

    const statusBadge = isConforme
      ? '<span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">✓ CONFORME ANP</span>'
      : '<span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-500/20 text-rose-300 border border-rose-500/40 animate-pulse">🚨 FORA DA TOLERÂNCIA</span>';

    // Determina o desvio de maior magnitude para a régua
    let maxVarPct = resumo.variacao_volumetrica_geral_pct !== undefined ? parseFloat(resumo.variacao_volumetrica_geral_pct) : 0;
    if (items.length > 0) {
      items.forEach(c => {
        const vPct = parseFloat(c.auditoria_anp?.variacao_pct ?? c.variacao_percentual ?? c.variacao_pct ?? 0);
        if (Math.abs(vPct) > Math.abs(maxVarPct)) {
          maxVarPct = vPct;
        }
      });
    }

    // Escala [-1.2% a +1.2%] na régua para alinhar com a safezone CSS (25% a 75% = ±0.6%)
    const minScale = -1.2;
    const maxScale = 1.2;
    const clampedPct = Math.max(minScale, Math.min(maxScale, maxVarPct));
    let needleLeft = ((clampedPct - minScale) / (maxScale - minScale)) * 100;
    needleLeft = Math.max(4, Math.min(96, needleLeft));

    const needleColor = Math.abs(maxVarPct) <= 0.6 ? '#10b981' : '#f43f5e';
    const needleText = `${maxVarPct > 0 ? '+' : ''}${maxVarPct.toFixed(2)}%`;

    let rowsHtml = '';
    items.forEach(c => {
      const vL = parseFloat(c.auditoria_anp?.variacao_litros ?? c.variacao_litros ?? 0);
      const vP = parseFloat(c.auditoria_anp?.variacao_pct ?? c.variacao_percentual ?? c.variacao_pct ?? 0);
      const cConf = Math.abs(vP) <= 0.6;
      const tagConf = cConf
        ? '<span class="text-emerald-400 font-bold">Conforme</span>'
        : '<span class="text-rose-400 font-bold">Alerta ANP</span>';

      const escLitros = parseFloat(c.movimentacao?.estoque_escriturado_litros ?? c.estoque_escriturado_litros ?? 0).toLocaleString('pt-BR');
      const fisLitros = parseFloat(c.movimentacao?.estoque_fisico_medido_litros ?? c.estoque_fisico_litros ?? 0).toLocaleString('pt-BR');
      const nome = c.combustivel || (c.tanque ? `Tanque ${c.tanque}` : 'Combustível');

      rowsHtml += `
        <div class="p-2 rounded bg-slate-900/60 border border-slate-800 text-xs font-mono flex items-center justify-between gap-2">
          <div>
            <div class="font-bold text-slate-200">${this.escapeHtml(nome)}</div>
            <div class="text-[10px] text-slate-400">Escriturado: ${escLitros} L | Físico: ${fisLitros} L</div>
          </div>
          <div class="text-right">
            <div class="${cConf ? 'text-emerald-300' : 'text-rose-400'} font-bold">
              Δ ${vL > 0 ? '+' : ''}${vL.toFixed(1)} L (${vP > 0 ? '+' : ''}${vP.toFixed(2)}%)
            </div>
            <div class="text-[10px]">${tagConf}</div>
          </div>
        </div>
      `;
    });

    return `
      <div class="widget-inline-container border-l-4 border-l-auraCyan">
        <div class="widget-inline-header">
          <div class="flex items-center gap-2">
            <span class="text-sm">📋</span>
            <strong class="text-xs font-mono text-white uppercase tracking-wider">LMC Oficial ANP (Portaria 26/1992)</strong>
          </div>
          <div>${statusBadge}</div>
        </div>

        <!-- Régua Visual da ANP [-0.6% a +0.6%] -->
        <div class="widget-anp-ruler-container">
          <div class="flex justify-between text-[10px] font-mono text-slate-400 px-1">
            <span class="text-rose-400 font-bold">-0.6% (Limite)</span>
            <span class="text-emerald-400 font-bold">0.0% (Equilíbrio)</span>
            <span class="text-rose-400 font-bold">+0.6% (Limite)</span>
          </div>

          <div class="widget-anp-track">
            <div class="widget-anp-safezone-mark"></div>
            <div class="widget-anp-needle" style="left: ${needleLeft}%; color: ${needleColor};">
              <div class="widget-anp-needle-pin"></div>
              <div class="widget-anp-needle-line"></div>
            </div>
          </div>

          <div class="text-center font-mono text-xs mt-1">
            <span class="text-slate-400">Desvio Regulatório: </span>
            <strong style="color: ${needleColor};">${needleText}</strong>
            <span class="text-[10px] text-slate-500 ml-1">(${Math.abs(maxVarPct) <= 0.6 ? 'Dentro da tolerância regulamentar' : 'Fora da tolerância legal'})</span>
          </div>
        </div>

        <div class="space-y-1 mt-2">${rowsHtml || '<div class="text-xs font-mono text-slate-400">Nenhum tanque auditado no LMC.</div>'}</div>

        <div class="mt-2 pt-2 border-t border-slate-800/80 flex items-center justify-between">
          <span class="text-[10px] font-mono text-slate-400">Tolerância Portaria 26: ±0.6%</span>
          <button class="widget-action-btn purple" onclick="window.auraChat.sendUserPrompt('Como auditar a divergência física no tanque de combustíveis?')">
            🔍 Auditar Medição Física
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
    const dataAuditada = data.data_auditada || c.context?.data_auditada || 'Data Recente';
    const turnoAuditado = data.turno_auditado || c.context?.shift_id || 'Turno';

    if (titleEl) titleEl.textContent = `Evidências: ${dataAuditada} (${turnoAuditado})`;
    if (chipEl) {
      chipEl.textContent = assessment.badge_label || (assessment.finality === 'partial' ? 'Provisório' : 'Validado');
      chipEl.className = `px-2 py-0.5 rounded-full text-[10px] font-sans font-semibold ${assessment.finality === 'partial' ? 'bg-amber-500/15 text-amber-300 border border-amber-500/30' : 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'}`;
    }
    if (subEl) subEl.textContent = `Unidade: ${c.context?.unit_id || 'Posto'} • Data: ${dataAuditada} • Turno: ${turnoAuditado}`;

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
   */
  renderEvidenceTabContent(data, tab) {
    if (!data || (typeof data !== 'object') || (!data.contrato && !data.resumo_executivo && !data.assessment && !data.metrics)) {
      return `<div class="p-6 text-center text-slate-400 font-mono text-xs">Dados de evidência indisponíveis para este item.</div>`;
    }

    const c = data.contrato || data;
    const assessment = c.assessment || {};
    const metrics = c.metrics || {};
    const sources = c.sources || [];
    const tri = data.triangulacao_pista || {};
    const caixa = data.triangulacao_caixa || {};
    const tanques = data.balanco_tanques || {};
    const bicosList = tri.detalhamento_bicos || [];
    const caixasList = caixa.caixas || [];
    const tanquesList = tanques.detalhamento_tanques || [];
    const dataAuditada = data.data_auditada || c.context?.data_auditada || 'Data Recente';

    if (tab === 'formula') {
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

    if (tab === 'bicos') {
      if (bicosList.length === 0) {
        return `<div class="p-4 text-center text-slate-500 font-mono text-xs">Sem dados detalhados de bicos para este turno.</div>`;
      }

      const rows = bicosList.map(b => {
        const isPend = b.status_bico?.includes('PENDENTE_ENCERRANTE');
        const encText = isPend ? 'Pendente' : this.formatLiters(Number(b.volume_faturado_encerrante || 0), 1);
        return `
          <tr class="border-b border-slate-800/80 text-[11px] font-mono">
            <td class="py-2.5 font-bold text-slate-200">${this.escapeHtml(b.bico)}</td>
            <td class="py-2.5 text-slate-300">${this.escapeHtml(b.combustivel)}</td>
            <td class="py-2.5 text-right text-cyan-300">${this.formatLiters(Number(b.volume_automacao_litros || 0), 1)}</td>
            <td class="py-2.5 text-right ${isPend ? 'text-amber-400 font-semibold' : 'text-slate-200'}">
              ${encText}
            </td>
            <td class="py-2.5 text-right text-slate-100">${this.formatBRL(Number(b.total_reais_automacao || 0))}</td>
            <td class="py-2.5 text-right">
              <span class="px-1.5 py-0.5 rounded text-[10px] ${b.status_bico?.includes('CONCILIADO') ? 'bg-emerald-500/15 text-emerald-300' : 'bg-amber-500/15 text-amber-300'}">
                ${isPend ? 'Encerrante Pendente' : (b.status_bico?.includes('CONCILIADO') ? 'OK' : 'Divergência')}
              </span>
            </td>
          </tr>
        `;
      }).join('');

      return `
        <div class="space-y-3">
          <div class="flex items-center justify-between text-xs font-mono text-slate-400">
            <span>Total de Bicos Auditados: <strong>${bicosList.length}</strong></span>
            <span>Automação: CBC04 Companytec</span>
          </div>
          <div class="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/60 p-1">
            <table class="w-full text-left font-mono">
              <thead>
                <tr class="border-b border-slate-800 text-slate-400 text-[10px] uppercase">
                  <th class="p-2">Bico</th>
                  <th class="p-2">Combustível</th>
                  <th class="p-2 text-right">CBC04</th>
                  <th class="p-2 text-right">Encerrante</th>
                  <th class="p-2 text-right">Total R$</th>
                  <th class="p-2 text-right">Status</th>
                </tr>
              </thead>
              <tbody>${rows}</tbody>
            </table>
          </div>
        </div>
      `;
    }

    if (tab === 'caixas') {
      if (caixasList.length === 0) {
        return `<div class="p-4 text-center text-slate-500 font-mono text-xs">Sem caixas registrados na data auditada.</div>`;
      }

      const rows = caixasList.map(cItem => {
        let opName = String(cItem.operador || 'Operador não informado').trim();
        if (opName.includes('NO') || opName.toUpperCase().includes('NAO INFORMADO') || opName.toUpperCase().includes('NÃO INFORMADO')) {
          opName = 'Operador não informado';
        }

        return `
        <div class="p-3 rounded-xl border border-slate-800 bg-slate-900/60 space-y-2 font-mono text-xs">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="font-bold text-slate-100">Sessão #${this.escapeHtml(cItem.caixa_id ?? 'N/D')} • Terminal PDV ${this.escapeHtml(cItem.pdv ?? 'N/D')}</span>
              <span class="px-2 py-0.5 rounded text-[10px] font-semibold ${cItem.status === 'FECHADO' ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30' : 'bg-amber-500/15 text-amber-300 border border-amber-500/30'}">
                ${this.escapeHtml(cItem.status ?? 'EM ABERTO')}
              </span>
            </div>
            <span class="text-slate-400 text-[11px]">${this.escapeHtml(opName)}</span>
          </div>

          <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 border-t border-slate-800 text-[11px]">
            <div><span class="text-slate-400">Dinheiro:</span> <strong class="text-slate-200">${this.formatBRL(cItem.dinheiro)}</strong></div>
            <div><span class="text-slate-400">Cartões:</span> <strong class="text-slate-200">${this.formatBRL(cItem.cartao)}</strong></div>
            <div><span class="text-slate-400">Prazo:</span> <strong class="text-slate-200">${this.formatBRL(cItem.prazo)}</strong></div>
            <div><span class="text-slate-400">Convênio:</span> <strong class="text-slate-200">${this.formatBRL(cItem.convenio_cheque)}</strong></div>
          </div>

          <div class="flex items-center justify-between pt-1 border-t border-slate-800/60 text-xs">
            <span class="text-slate-400">Total Declarado:</span>
            <strong class="text-cyan-300">${this.formatBRL(cItem.total_declarado)}</strong>
          </div>
        </div>
      `;
      }).join('');

      return `<div class="space-y-3">${rows}</div>`;
    }

    if (tab === 'tanques') {
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
                ${isConf ? '✓ Conforme ANP (±0.6%)' : '⚠️ Alerta ANP'}
              </span>
            </div>
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] text-slate-300">
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

    // Default: 'resumo'
    const sourcesList = sources.map(s => {
      let stBadge = '<span class="text-emerald-400 font-semibold">✓ Disponível</span>';
      if (s.availability === 'missing') stBadge = '<span class="text-amber-400 font-semibold">⏳ Pendente / Não lançado</span>';
      if (s.availability === 'unavailable') stBadge = '<span class="text-rose-400 font-semibold">⚠️ Indisponível</span>';

      return `
        <div class="p-3 rounded-xl border border-slate-800 bg-slate-900/60 flex items-center justify-between font-mono text-xs">
          <div>
            <div class="font-bold text-slate-200">${this.escapeHtml(s.label)}</div>
            <div class="text-[10px] text-slate-400">Data de atualização: ${s.data_as_of ? this.escapeHtml(s.data_as_of) : 'Não informada'}</div>
          </div>
          <div>${stBadge}</div>
        </div>
      `;
    }).join('');

    const explanationText = c.explanation?.text || data.resumo_executivo?.diagnostico_caixa || 'Auditoria executada conforme regras vigentes.';

    return `
      <div class="space-y-4">
        <div class="evidence-section-card">
          <h4 class="font-bold text-slate-100 flex items-center gap-2">
            <span>📡</span><span>Proveniência e Disponibilidade das Fontes</span>
          </h4>
          <div class="space-y-2">${sourcesList || '<div class="text-slate-500">Fontes padrão do ERP</div>'}</div>
        </div>

        <div class="evidence-section-card">
          <h4 class="font-bold text-slate-100 flex items-center gap-2">
            <span>📝</span><span>Diagnóstico Operacional</span>
          </h4>
          <p class="text-slate-300 leading-relaxed text-xs p-3 rounded-lg bg-slate-900 border border-slate-800">
            ${this.escapeHtml(explanationText)}
          </p>
        </div>
      </div>
    `;
  }

  /**
   * Widget 4: Cards de Combos de Conveniência com Scripts de Balcão e Ações
   */
  renderCombosWidget(data) {
    const resumo = data.resumo_executivo || {};
    const combos = data.top_combos_cross_selling || data.top_combos_oportunidades || data.regras_associacao_detalhadas || [];
    const maxLiftVal = resumo.maior_lift_encontrado ?? resumo.max_lift ?? (combos[0]?.metricas?.lift ?? combos[0]?.lift ?? 2.85);
    const maxLift = `${parseFloat(maxLiftVal).toFixed(2)}x`;

    let cardsHtml = '';
    combos.slice(0, 3).forEach(c => {
      const lift = parseFloat(c.metricas?.lift ?? c.lift ?? 1.5).toFixed(2);
      const conf = parseFloat((c.metricas?.confianca ? c.metricas.confianca * 100 : c.confianca_percentual) ?? 50).toFixed(0);
      const cupons = c.metricas?.frequencia_conjunta ?? c.frequencia_conjunta_cupons ?? 10;

      const prodOrig = typeof c.produto_origem === 'object' ? (c.produto_origem?.nompro || 'Item Origem') : (c.produto_origem || 'Item Origem');
      const prodDest = typeof c.produto_recomendado === 'object' ? (c.produto_recomendado?.nompro || 'Item Recomendado') : (c.produto_recomendado || 'Item Recomendado');
      const prodDestShort = String(prodDest).split(' ').slice(0, 2).join(' ');
      const script = c.script_sugerido_caixa || c.script_sugestao_pdv || 'Ofereça o combo ao registrar o item.';

      cardsHtml += `
        <div class="widget-combo-card">
          <div class="flex items-center justify-between text-xs font-mono mb-1">
            <span class="font-bold text-white">${this.escapeHtml(prodOrig)}</span>
            <span class="text-purple-400">➔</span>
            <span class="font-bold text-auraCyan-light">${this.escapeHtml(prodDest)}</span>
          </div>

          <div class="flex items-center gap-2 font-mono text-[10px] text-slate-400 my-1">
            <span class="px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 font-bold border border-purple-500/30">⚡ Lift ${lift}x</span>
            <span class="px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">🎯 Confiança ${conf}%</span>
            <span>📦 ${cupons} cupons</span>
          </div>

          <div class="widget-combo-script-box">
            <strong>🗣 Script no Balcão:</strong> "${this.escapeHtml(script)}"
          </div>

          <div class="flex justify-end mt-2">
            <button class="widget-action-btn purple" onclick="window.auraChat.sendUserPrompt('Qual o estoque atual de ${this.escapeHtml(prodDest)}?')">
              📦 Checar Estoque (${this.escapeHtml(prodDestShort)})
            </button>
          </div>
        </div>
      `;
    });

    return `
      <div class="widget-inline-container border-l-4 border-l-auraPurple">
        <div class="widget-inline-header">
          <div class="flex items-center gap-2">
            <span class="text-sm">🛒</span>
            <strong class="text-xs font-mono text-white uppercase tracking-wider">Combos & Vendas Cruzadas (Conveniência)</strong>
          </div>
          <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">
            ⚡ Max Lift: ${maxLift}
          </span>
        </div>
        <div class="space-y-2">${cardsHtml || '<div class="text-xs font-mono text-slate-400">Nenhum combo com lift mínimo identificado.</div>'}</div>
      </div>
    `;
  }

  /**
   * Widget 5: Performance de Pista, Ranking e Alertas de Vazão de Bicos
   */
  renderDesempenhoPistaWidget(data) {
    const frents = data.ranking_frentistas || [];
    const bicos = data.auditoria_vazao_bicos || data.vazao_bicos || [];
    const lider = data.resumo_executivo?.campeao_faturamento?.nome || data.resumo_executivo?.lider_faturamento || (frents[0]?.nome || frents[0]?.frentista || 'N/A');

    let frentsHtml = '';
    frents.slice(0, 3).forEach((f, idx) => {
      const medals = ['🥇', '🥈', '🥉'];
      const med = medals[idx] || '👤';
      const nomeFrent = f.nome || f.frentista || 'Colaborador';
      const fat = parseFloat(f.faturamento_reais || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
      const adit = parseFloat(f.conversao_aditivada_pct ?? f.percentual_aditivada ?? 0).toFixed(1);
      const isMeta = parseFloat(adit) >= 25.0;

      frentsHtml += `
        <div class="flex items-center justify-between p-1.5 rounded bg-slate-900/50 border border-slate-800 text-xs font-mono">
          <div class="flex items-center gap-1.5 font-bold text-white">
            <span>${med}</span>
            <span>${this.escapeHtml(nomeFrent)}</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-slate-300">${fat}</span>
            <span class="${isMeta ? 'text-emerald-400' : 'text-amber-400'} font-semibold">Adit: ${adit}%</span>
          </div>
        </div>
      `;
    });

    let bicosAlertHtml = '';
    const bicosAlerta = bicos.filter(b => b.alerta_filtro || b.alerta_vazao || parseFloat(b.vazao_litros_minuto ?? b.vazao_media_litros_minuto ?? 35) < 25.0);
    if (bicosAlerta.length > 0) {
      bicosAlertHtml = `
        <div class="mt-2 p-2 rounded bg-amber-950/30 border border-amber-500/30 text-amber-300 text-xs font-mono space-y-1">
          <strong class="text-[10px] uppercase tracking-wider text-amber-400">⚠️ Alerta de Vazão Lenta nos Bicos:</strong>
          ${bicosAlerta.map(b => {
            const vazao = parseFloat(b.vazao_litros_minuto ?? b.vazao_media_litros_minuto ?? 0).toFixed(1);
            const prod = b.produto_nome || b.combustivel || 'Combustível';
            return `<div>Bico ${b.bico} (${this.escapeHtml(prod)}): <strong>${vazao} L/min</strong> (Filtro/Bomba requer checagem)</div>`;
          }).join('')}
        </div>
      `;
    }

    return `
      <div class="widget-inline-container border-l-4 border-l-auraPurple">
        <div class="widget-inline-header">
          <div class="flex items-center gap-2">
            <span class="text-sm">🏆</span>
            <strong class="text-xs font-mono text-white uppercase tracking-wider">Performance da Pista & Frentistas</strong>
          </div>
          <span class="text-[10px] font-mono text-cyan-300 font-bold">Líder: ${this.escapeHtml(lider)}</span>
        </div>
        <div class="space-y-1">${frentsHtml}</div>
        ${bicosAlertHtml}
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
