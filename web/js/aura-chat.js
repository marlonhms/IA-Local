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
  }

  generateSessionId() {
    return 'aura_ui_' + Math.random().toString(36).substring(2, 10);
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

    const splitInput = document.getElementById('split-chat-input-text');
    const splitSendBtn = document.getElementById('btn-split-chat-send');

    if (input) {
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          this.handleSendMessage();
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

          <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5">
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
    if (!query) {
      const input = document.getElementById('chat-input-text');
      const splitInput = document.getElementById('split-chat-input-text');
      if (input && input.value.trim()) {
        query = input.value.trim();
        input.value = '';
      } else if (splitInput && splitInput.value.trim()) {
        query = splitInput.value.trim();
        splitInput.value = '';
      }
    } else {
      const input = document.getElementById('chat-input-text');
      if (input) input.value = '';
      const splitInput = document.getElementById('split-chat-input-text');
      if (splitInput) splitInput.value = '';
    }

    if (!query || this.isStreaming) return;

    this.setStreamingState(true);

    // 1. Adiciona a mensagem do usuário na tela (Console e Split)
    this.appendUserMessage(query);

    // 2. Prepara contêiner para a resposta da AURA
    const messageContainerId = 'aura-msg-' + Date.now();
    this.createAuraMessageBubble(messageContainerId);

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
          else if (type === 'done') {
            this.updateAuraText(messageContainerId, fullResponseText, false);
            this.setStreamingState(false);
          }
        },
        onDone: () => {
          this.updateAuraText(messageContainerId, fullResponseText, false);
          this.setStreamingState(false);
          this.scrollToBottom();
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
      if (!isStreaming) input.focus();
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
      div.className = 'flex justify-end animate-fade-in';
      div.innerHTML = `
        <div class="chat-bubble-user max-w-[85%] md:max-w-[70%] p-3.5 text-slate-100 text-sm">
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
      div.className = 'flex justify-start animate-fade-in';
      div.innerHTML = `
        <div class="chat-bubble-aura max-w-[95%] md:max-w-[85%] p-4 text-slate-100 text-sm space-y-3">
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
          <div id="${containerId + suffix}-tool-card" class="hidden"></div>

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
      div.className = 'flex justify-start animate-fade-in';
      div.innerHTML = `
        <div class="chat-bubble-aura max-w-[95%] md:max-w-[85%] p-4 text-slate-100 text-sm space-y-3">
          <div class="flex items-center gap-2 border-b border-purple-900/40 pb-2">
            <div class="w-5 h-5 rounded-full bg-gradient-to-tr from-emerald-500 via-cyan-500 to-purple-600 flex items-center justify-center text-[10px] font-bold text-white shadow-sm">
              A
            </div>
            <span class="font-bold font-sans text-xs text-purple-200">AURA</span>
            ${opts.isWelcome ? '<span class="px-2 py-0.5 rounded-full text-[10px] font-sans font-medium bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">Pronta para Atendimento</span>' : ''}
          </div>
          <div>${htmlContent}</div>
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
      data.resumo_executivo?.status_geral_anp ||
      Array.isArray(data.demonstrativo_por_combustivel) ||
      (Array.isArray(data.tanques) && data.tanques[0]?.auditoria_anp)
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
   * Widget 3: Mini-Tabela de Furos/Quebras de Caixa e Conciliação de Pista
   */
  renderTurnoWidget(data) {
    const resumo = data.resumo_executivo || {};
    const tri = data.triangulacao_pista || data.triangulacao_volumes || {};
    const caixa = data.triangulacao_caixa || data.fechamento_caixa || {};
    const status = resumo.status_conciliacao || 'CONCILIADO';
    const score = resumo.score_conformidade_pct ?? resumo.score_conformidade_percentual ?? 100;

    const diffReais = parseFloat(resumo.diferenca_financeira_caixa ?? caixa.diferenca_reais ?? 0);
    let diffBadge = '<span class="text-emerald-300 font-bold">✓ Caixa Zerado</span>';
    if (diffReais < -0.01) {
      diffBadge = `<span class="text-rose-400 font-bold">🚨 Furo de R$ ${Math.abs(diffReais).toFixed(2)}</span>`;
    } else if (diffReais > 0.01) {
      diffBadge = `<span class="text-emerald-400 font-bold">🟢 Sobra de R$ ${diffReais.toFixed(2)}</span>`;
    }

    const modal = caixa.totais_caixa || caixa.modalidades || {};
    const din = parseFloat(modal.dinheiro || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    const carCred = parseFloat(modal.cartao_credito || modal.cartao || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    const carDeb = parseFloat(modal.cartao_debito || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    const pix = parseFloat(modal.pix || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

    const faturadoVal = resumo.faturamento_pista_total ?? caixa.total_combustivel_faturado_reais ?? 0;
    const faturado = parseFloat(faturadoVal).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    const declaradoVal = modal.total_declarado ?? caixa.total_declarado_operador_reais ?? 0;
    const declarado = parseFloat(declaradoVal).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

    const encLitros = parseFloat(tri.total_litros_encerrante ?? tri.encerrantes_litros ?? 0).toLocaleString('pt-BR');
    const cbcLitros = parseFloat(tri.total_litros_automacao ?? tri.abastecimentos_cbc04_litros ?? 0).toLocaleString('pt-BR');
    const divPista = parseFloat(tri.diferenca_litros_pista ?? tri.divergencia_litros ?? 0);

    return `
      <div class="widget-inline-container border-l-4 border-l-auraCyan">
        <div class="widget-inline-header">
          <div class="flex items-center gap-2">
            <span class="text-sm">💰</span>
            <strong class="text-xs font-mono text-white uppercase tracking-wider">Conciliação de Turno & Caixa</strong>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-[11px] font-mono text-cyan-300 font-bold">Score: ${score}%</span>
            <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-800 text-slate-200 border border-slate-700">
              ${this.escapeHtml(status)}
            </span>
          </div>
        </div>

        <!-- Grid de Triangulação -->
        <div class="widget-turno-grid">
          <!-- Coluna 1: Pista -->
          <div class="widget-turno-cell space-y-1">
            <div class="text-[10px] font-mono text-slate-400 font-bold uppercase">⛽ Pista (Encerrantes vs CBC04)</div>
            <div class="text-xs font-mono flex justify-between">
              <span class="text-slate-400">Encerrantes:</span>
              <strong class="text-white">${encLitros} L</strong>
            </div>
            <div class="text-xs font-mono flex justify-between">
              <span class="text-slate-400">CBC04:</span>
              <strong class="text-cyan-300">${cbcLitros} L</strong>
            </div>
            <div class="text-xs font-mono flex justify-between pt-1 border-t border-slate-800">
              <span class="text-slate-400">Divergência Pista:</span>
              <strong class="${Math.abs(divPista) < 0.01 ? 'text-emerald-300' : 'text-rose-400'}">${divPista > 0 ? '+' : ''}${divPista.toFixed(1)} L</strong>
            </div>
          </div>

          <!-- Coluna 2: Caixa -->
          <div class="widget-turno-cell space-y-1">
            <div class="text-[10px] font-mono text-slate-400 font-bold uppercase">💵 Fechamento de Caixa</div>
            <div class="text-xs font-mono flex justify-between">
              <span class="text-slate-400">Faturado ERP:</span>
              <strong class="text-white">${faturado}</strong>
            </div>
            <div class="text-xs font-mono flex justify-between">
              <span class="text-slate-400">Declarado Operador:</span>
              <strong class="text-slate-200">${declarado}</strong>
            </div>
            <div class="text-xs font-mono flex justify-between pt-1 border-t border-slate-800">
              <span class="text-slate-400">Diferença Caixa:</span>
              ${diffBadge}
            </div>
          </div>
        </div>

        <!-- Breakdown Modalidades -->
        <div class="mt-2 p-2 rounded bg-slate-900/50 border border-slate-800 text-[11px] font-mono flex flex-wrap items-center justify-between gap-2">
          <span>Dinheiro: <strong class="text-slate-200">${din}</strong></span>
          <span>Cartões: <strong class="text-slate-200">${carCred} / ${carDeb}</strong></span>
          <span>PIX: <strong class="text-slate-200">${pix}</strong></span>
        </div>

        <div class="mt-2 pt-2 border-t border-slate-800/80 flex items-center justify-between">
          <button class="widget-action-btn emerald" onclick="window.auraChat.sendUserPrompt('Teve furo no caixa por operador?')">
            👥 Identificar Operador
          </button>
          <button class="widget-action-btn purple" onclick="window.auraChat.sendUserPrompt('Como fechou o turno da manhã?')">
            🔄 Fechamento Detalhado
          </button>
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

  updateAuraText(containerId, fullMarkdown, isStillStreaming) {
    const textIds = [containerId + '-text', containerId + '-split-text'];
    const html = window.marked 
      ? window.marked.parse(fullMarkdown) 
      : `<p>${this.escapeHtml(fullMarkdown).replace(/\n/g, '<br>')}</p>`;

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

  scrollToBottom() {
    const feeds = [
      document.getElementById('chat-feed-container'),
      document.getElementById('split-chat-feed-container')
    ];

    feeds.forEach(feed => {
      if (feed) feed.scrollTop = feed.scrollHeight;
    });
  }

  escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
}

// Instância singleton global
window.auraChat = new AuraChatController();
