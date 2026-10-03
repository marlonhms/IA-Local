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
        <p>Olá! Sou a <strong>AURA</strong>, sua Assistente Cognitiva de Operações do Posto & PDV.</p>
        <p>Estou conectada ao ERP local (porta 5433) e ao banco vetorial pgvector (porta 5434). Posso auditar estoques, projetar esgotamento de tanques (Run-Out), emitir LMC da ANP, conciliar fechamentos de turno e identificar regras de vendas cruzadas na conveniência.</p>
        <p class="text-xs text-slate-400">Clique em qualquer sugestão tática abaixo ou digite sua dúvida operacional:</p>
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

    let previewHtml = '';
    if (resultData.resumo_executivo) {
      const r = resultData.resumo_executivo;
      previewHtml = `
        <div class="p-2.5 rounded bg-slate-900/90 border border-purple-500/30 font-mono text-xs space-y-1">
          <div class="text-[10px] text-purple-300 font-bold uppercase tracking-wider">Dados Analíticos Extraídos:</div>
          <div class="text-slate-200">
            ${r.status_conciliacao || r.status_geral_anp || r.status || 'Dados consolidados com sucesso'}
          </div>
        </div>
      `;
    }

    if (previewHtml) {
      cardIds.forEach(id => {
        const cardEl = document.getElementById(id);
        if (cardEl) {
          cardEl.innerHTML = previewHtml;
          cardEl.classList.remove('hidden');
        }
      });
    }
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
