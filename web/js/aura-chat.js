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
      <div class="prose-aura">
        <p>Olá, gestor! Sou a <strong>AURA</strong>, sua <strong>Assistente de Prontidão e Gerente Supervisora do Posto & PDV</strong>.</p>
        <p>Tirou o celular do bolso e precisa tomar uma decisão rápida na pista ou na loja? Pergunte sobre tanques, fechamento de turno, furo de caixa, conformidade fiscal ANP ou vendas cruzadas na conveniência:</p>
      </div>
      <div class="mt-3 pt-2 border-t border-purple-900/30">
        <div class="text-[11px] font-mono text-slate-400 mb-2 font-semibold flex items-center gap-1.5">
          <span>⚡</span> <span>Decisões Rápidas de 1 Toque:</span>
        </div>
        <div class="flex flex-wrap gap-2">
          <button onclick="window.auraChat.sendUserPrompt('Como fechou o turno da manhã?')" class="quick-prompt-chip">
            💰 Como fechou o turno da manhã?
          </button>
          <button onclick="window.auraChat.sendUserPrompt('Qual a autonomia da gasolina comum?')" class="quick-prompt-chip">
            ⛽ Qual a autonomia da gasolina comum?
          </button>
          <button onclick="window.auraChat.sendUserPrompt('Teve furo no caixa?')" class="quick-prompt-chip">
            🚨 Teve furo no caixa?
          </button>
          <button onclick="window.auraChat.sendUserPrompt('Combos para vender mais Heineken?')" class="quick-prompt-chip">
            🛒 Combos para vender mais Heineken?
          </button>
          <button onclick="window.auraChat.sendUserPrompt('Qual o status do LMC da ANP de hoje?')" class="quick-prompt-chip">
            📋 LMC ANP de hoje
          </button>
          <button onclick="window.auraChat.sendUserPrompt('Há algum bico lento na pista?')" class="quick-prompt-chip">
            ⚠️ Algum bico lento na pista?
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
    const input = document.getElementById('chat-input-text');
    if (input) input.value = text;
    const splitInput = document.getElementById('split-chat-input-text');
    if (splitInput) splitInput.value = text;
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
            this.updateToolStartStatus(messageContainerId, chunk.data?.tool_name || chunk.tool_name);
          } 
          else if (type === 'tool_result') {
            currentToolResult = chunk.data?.result || chunk.data || {};
            this.updateToolResultCard(messageContainerId, chunk.data?.tool_name || 'ferramenta', currentToolResult);
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
              <span class="font-bold font-mono text-xs text-purple-300">AURA COGNITIVE</span>
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

          <!-- Telemetria SRE da Resposta -->
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
            <span class="font-bold font-mono text-xs text-purple-300">AURA COGNITIVE</span>
            ${opts.isWelcome ? '<span class="px-1.5 py-0.2 rounded text-[10px] font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">PRONTA</span>' : ''}
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

  updateToolStartStatus(containerId, toolName) {
    const ids = [containerId + '-tool-chip', containerId + '-split-tool-chip'];
    ids.forEach(id => {
      const chip = document.getElementById(id);
      if (chip) {
        chip.innerHTML = `⚡ Executando ${toolName}...`;
        chip.classList.remove('hidden');
      }
    });
  }

  updateToolResultCard(containerId, toolName, resultData) {
    const cardIds = [containerId + '-tool-card', containerId + '-split-tool-card'];
    const chipIds = [containerId + '-tool-chip', containerId + '-split-tool-chip'];

    chipIds.forEach(id => {
      const chip = document.getElementById(id);
      if (chip) {
        chip.innerHTML = `✓ ${toolName} concluído`;
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

    // 1. Previsão de Tanques & Autonomia (Run-Out Forecast)
    if (toolName === 'previsao_tanques' || toolName === 'run_out' || Array.isArray(data.tanques)) {
      return this.renderTankAutonomyWidget(data);
    }

    // 2. Livro de Movimentação de Combustíveis (LMC Oficial ANP Portaria 26/1992)
    if (toolName === 'lmc_anp' || Array.isArray(data.demonstrativo_por_combustivel)) {
      return this.renderLmcAnpWidget(data);
    }

    // 3. Conciliação de Fechamento de Turno & Furo de Caixa
    if (toolName === 'auditoria_turno' || toolName === 'conciliacao_turno' || data.triangulacao_volumes || data.fechamento_caixa) {
      return this.renderTurnoWidget(data);
    }

    // 4. Vendas Cruzadas & Combos de Conveniência (Market Basket Analysis)
    if (toolName === 'conveniencia_vendas_cruzadas' || Array.isArray(data.top_combos_oportunidades)) {
      return this.renderCombosWidget(data);
    }

    // 5. Performance de Pista, Frentistas & Vazão de Bicos
    if (toolName === 'desempenho_pista_frentistas' || Array.isArray(data.ranking_frentistas)) {
      return this.renderDesempenhoPistaWidget(data);
    }

    // Fallback genérico executivo
    return this.renderGenericToolWidget(toolName, data);
  }

  /**
   * Widget 1: Mini-Barras Visuais de Nível de Tanques e Autonomia Restante
   */
  renderTankAutonomyWidget(data) {
    const resumo = data.resumo_executivo || {};
    const tanques = data.tanques || [];
    const statusGeral = resumo.status_geral || 'ESTÁVEL';
    const menorAutonomia = resumo.menor_autonomia_horas;

    let badgeStatus = '<span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">✓ ESTÁVEL</span>';
    if (statusGeral === 'CRÍTICO') {
      badgeStatus = '<span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-500/20 text-rose-300 border border-rose-500/40 animate-pulse">🚨 CRÍTICO</span>';
    } else if (statusGeral === 'ATENÇÃO') {
      badgeStatus = '<span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">⚠️ ATENÇÃO</span>';
    }

    let tanksHtml = '';
    tanques.forEach(t => {
      const pct = Math.min(100, Math.max(0, parseFloat(t.ocupacao_percentual || 0)));
      const vol = parseFloat(t.volume_atual_litros || 0).toLocaleString('pt-BR', { maximumFractionDigits: 0 });
      const cap = parseFloat(t.capacidade_litros || 0).toLocaleString('pt-BR', { maximumFractionDigits: 0 });
      const horas = t.autonomia_horas ? `${parseFloat(t.autonomia_horas).toFixed(1)}h restantes` : 'N/A';
      const ullage = t.espaco_livre_descarga_litros ? parseFloat(t.espaco_livre_descarga_litros).toLocaleString('pt-BR', { maximumFractionDigits: 0 }) : 'N/A';

      let fillClass = 'normal';
      let statusIcon = '🟢';
      if (pct < 15 || t.status_nivel === 'CRÍTICO') {
        fillClass = 'critical';
        statusIcon = '🚨';
      } else if (pct < 30 || t.status_nivel === 'ATENÇÃO') {
        fillClass = 'warning';
        statusIcon = '🟡';
      }

      tanksHtml += `
        <div class="widget-tank-card">
          <div class="flex items-center justify-between text-xs font-mono">
            <span class="font-bold text-white flex items-center gap-1.5">
              <span>${statusIcon}</span>
              <span>TQ ${t.tanque} • ${this.escapeHtml(t.combustivel)}</span>
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
            <button class="widget-action-btn emerald" onclick="window.auraChat.sendUserPrompt('Qual a melhor sugestão de pedido de carreta para o Tanque ${t.tanque}?')">
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
            ${menorAutonomia ? `<span class="text-[11px] font-mono text-cyan-300 font-bold">Mín: ${parseFloat(menorAutonomia).toFixed(1)}h</span>` : ''}
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
    const combs = data.demonstrativo_por_combustivel || [];
    const statusGeral = resumo.status_geral_anp || 'CONFORME_ANP';
    const isConforme = statusGeral === 'CONFORME_ANP' || statusGeral === 'CONFORME';

    const statusBadge = isConforme
      ? '<span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">✓ CONFORME ANP</span>'
      : '<span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-500/20 text-rose-300 border border-rose-500/40 animate-pulse">🚨 FORA DA TOLERÂNCIA</span>';

    // Determina o desvio de maior magnitude para a régua
    let maxVarPct = 0;
    if (combs.length > 0) {
      maxVarPct = combs.reduce((max, c) => {
        const v = Math.abs(parseFloat(c.variacao_percentual || 0));
        return v > Math.abs(max) ? parseFloat(c.variacao_percentual) : max;
      }, parseFloat(combs[0].variacao_percentual || 0));
    }

    // Escala [-0.8% a +0.8%] na régua com margem
    const minScale = -0.8;
    const maxScale = 0.8;
    const clampedPct = Math.max(minScale, Math.min(maxScale, maxVarPct));
    let needleLeft = ((clampedPct - minScale) / (maxScale - minScale)) * 100;
    needleLeft = Math.max(4, Math.min(96, needleLeft));

    const needleColor = Math.abs(maxVarPct) <= 0.6 ? '#10b981' : '#f43f5e';
    const needleText = `${maxVarPct > 0 ? '+' : ''}${maxVarPct.toFixed(2)}%`;

    let rowsHtml = '';
    combs.forEach(c => {
      const vL = parseFloat(c.variacao_litros || 0);
      const vP = parseFloat(c.variacao_percentual || 0);
      const cConf = Math.abs(vP) <= 0.6;
      const tagConf = cConf
        ? '<span class="text-emerald-400 font-bold">Conforme</span>'
        : '<span class="text-rose-400 font-bold">Alerta ANP</span>';

      rowsHtml += `
        <div class="p-2 rounded bg-slate-900/60 border border-slate-800 text-xs font-mono flex items-center justify-between gap-2">
          <div>
            <div class="font-bold text-slate-200">${this.escapeHtml(c.combustivel)}</div>
            <div class="text-[10px] text-slate-400">Escriturado: ${(c.estoque_escriturado_litros || 0).toLocaleString('pt-BR')} L | Físico: ${(c.estoque_fisico_litros || 0).toLocaleString('pt-BR')} L</div>
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

        <div class="space-y-1 mt-2">${rowsHtml}</div>

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
    const tri = data.triangulacao_volumes || {};
    const caixa = data.fechamento_caixa || {};
    const status = resumo.status_conciliacao || 'CONCILIADO';
    const score = resumo.score_conformidade_percentual || 100;

    const diffReais = parseFloat(caixa.diferenca_reais || 0);
    let diffBadge = '<span class="text-emerald-300 font-bold">✓ Caixa Zerado</span>';
    if (diffReais < 0) {
      diffBadge = `<span class="text-rose-400 font-bold">🚨 Furo de R$ ${Math.abs(diffReais).toFixed(2)}</span>`;
    } else if (diffReais > 0) {
      diffBadge = `<span class="text-emerald-400 font-bold">🟢 Sobra de R$ ${diffReais.toFixed(2)}</span>`;
    }

    const modal = caixa.modalidades || {};
    const din = parseFloat(modal.dinheiro || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    const carCred = parseFloat(modal.cartao_credito || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    const carDeb = parseFloat(modal.cartao_debito || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    const pix = parseFloat(modal.pix || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

    const faturado = parseFloat(caixa.total_combustivel_faturado_reais || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    const declarado = parseFloat(caixa.total_declarado_operador_reais || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

    const encLitros = parseFloat(tri.encerrantes_litros || 0).toLocaleString('pt-BR');
    const cbcLitros = parseFloat(tri.abastecimentos_cbc04_litros || 0).toLocaleString('pt-BR');
    const divPista = parseFloat(tri.divergencia_litros || 0);

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
              <strong class="${divPista === 0 ? 'text-emerald-300' : 'text-rose-400'}">${divPista > 0 ? '+' : ''}${divPista.toFixed(1)} L</strong>
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
    const combos = data.top_combos_oportunidades || [];
    const maxLift = resumo.max_lift ? `${parseFloat(resumo.max_lift).toFixed(2)}x` : '2.85x';

    let cardsHtml = '';
    combos.slice(0, 3).forEach(c => {
      const lift = parseFloat(c.lift || 1.5).toFixed(2);
      const conf = parseFloat(c.confianca_percentual || 50).toFixed(0);
      const prodDest = c.produto_recomendado || '';
      const prodDestShort = prodDest.split(' ').slice(0, 2).join(' ');

      cardsHtml += `
        <div class="widget-combo-card">
          <div class="flex items-center justify-between text-xs font-mono mb-1">
            <span class="font-bold text-white">${this.escapeHtml(c.produto_origem)}</span>
            <span class="text-purple-400">➔</span>
            <span class="font-bold text-auraCyan-light">${this.escapeHtml(c.produto_recomendado)}</span>
          </div>

          <div class="flex items-center gap-2 font-mono text-[10px] text-slate-400 my-1">
            <span class="px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 font-bold border border-purple-500/30">⚡ Lift ${lift}x</span>
            <span class="px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">🎯 Confiança ${conf}%</span>
            <span>📦 ${c.frequencia_conjunta_cupons || 10} cupons</span>
          </div>

          <div class="widget-combo-script-box">
            <strong>🗣 Script no Balcão:</strong> "${this.escapeHtml(c.script_sugestao_pdv || 'Ofereça o combo ao registrar o item.')}"
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
    const bicos = data.vazao_bicos || [];
    const lider = data.resumo_executivo?.lider_faturamento || (frents[0]?.frentista || 'N/A');

    let frentsHtml = '';
    frents.slice(0, 3).forEach((f, idx) => {
      const medals = ['🥇', '🥈', '🥉'];
      const med = medals[idx] || '👤';
      const fat = parseFloat(f.faturamento_reais || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
      const adit = parseFloat(f.percentual_aditivada || 0).toFixed(1);
      const isMeta = parseFloat(f.percentual_aditivada || 0) >= 25.0;

      frentsHtml += `
        <div class="flex items-center justify-between p-1.5 rounded bg-slate-900/50 border border-slate-800 text-xs font-mono">
          <div class="flex items-center gap-1.5 font-bold text-white">
            <span>${med}</span>
            <span>${this.escapeHtml(f.frentista)}</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-slate-300">${fat}</span>
            <span class="${isMeta ? 'text-emerald-400' : 'text-amber-400'} font-semibold">Adit: ${adit}%</span>
          </div>
        </div>
      `;
    });

    let bicosAlertHtml = '';
    const bicosAlerta = bicos.filter(b => b.alerta_vazao || parseFloat(b.vazao_media_litros_minuto || 35) < 25.0);
    if (bicosAlerta.length > 0) {
      bicosAlertHtml = `
        <div class="mt-2 p-2 rounded bg-amber-950/30 border border-amber-500/30 text-amber-300 text-xs font-mono space-y-1">
          <strong class="text-[10px] uppercase tracking-wider text-amber-400">⚠️ Alerta de Vazão Lenta nos Bicos:</strong>
          ${bicosAlerta.map(b => `<div>Bico ${b.bico} (${this.escapeHtml(b.combustivel)}): <strong>${parseFloat(b.vazao_media_litros_minuto).toFixed(1)} L/min</strong> (Filtro/Bomba requer checagem)</div>`).join('')}
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
    return `
      <div class="widget-inline-container border-l-4 border-l-slate-600">
        <div class="widget-inline-header">
          <div class="flex items-center gap-2">
            <span class="text-sm">📊</span>
            <strong class="text-xs font-mono text-white uppercase tracking-wider">Diagnóstico: ${this.escapeHtml(toolName)}</strong>
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
    const ttft = t.ttft_ms ? `${t.ttft_ms.toFixed(0)}ms` : null;
    const e2e = t.total_e2e_ms ? `${t.total_e2e_ms.toFixed(0)}ms` : null;
    const model = t.llm_model || 'Gemini 3.1 Flash';
    const lgpd = t.lgpd_sanitized_count || 0;

    const html = `
      <div class="flex flex-wrap items-center gap-3">
        ${ttft ? `<span>TTFT: <strong class="text-cyan-300">${ttft}</strong></span>` : ''}
        ${e2e ? `<span>E2E: <strong class="text-emerald-300">${e2e}</strong></span>` : ''}
        <span>Modelo: <strong class="text-purple-300">${model}</strong></span>
        <span>LGPD Blindagem: <strong class="text-slate-300">${lgpd} ofuscados</strong></span>
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
