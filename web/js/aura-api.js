/**
 * AURA Core Engine API Client (v2.0 - GenUI Streaming Multiplexed Protocol)
 * Comunicacao direta com a API FastAPI local (/api/v1/aura)
 * Suporte a Server-Sent Events (SSE) multiplexados via POST stream,
 * bufferizacao volatil de deltas JSON, execucao de intencoes e suporte analitico sob demanda.
 */

class AuraApiClient {
  constructor(baseUrlOrOptions = '') {
    const raw = (typeof baseUrlOrOptions === 'object' && baseUrlOrOptions !== null)
      ? (baseUrlOrOptions.baseUrl || '')
      : (baseUrlOrOptions || '');
    this.baseUrl = String(raw).replace(/\/$/, '');
  }

  /**
   * Health check operacional
   */
  async getHealth() {
    const res = await fetch(`${this.baseUrl}/api/v1/aura/health`);
    if (!res.ok) throw new Error(`Health check falhou: ${res.status}`);
    return await res.json();
  }

  /**
   * Obtém identificação e status da estação
   */
  async getStationStatus() {
    const res = await fetch(`${this.baseUrl}/api/v1/aura/stations`);
    if (!res.ok) throw new Error(`Falha ao obter status da estação: ${res.status}`);
    const data = await res.json();
    return Array.isArray(data) && data.length > 0 ? data[0] : null;
  }

  /**
   * Invoca diretamente uma das 11 ferramentas analíticas (sub-100ms, sem custo LLM)
   * @param {string} toolName - Nome ou alias da ferramenta
   * @param {object} params - Parâmetros específicos
   */
  async executeIntent(toolName, params = {}) {
    const t0 = performance.now();
    const res = await fetch(`${this.baseUrl}/api/v1/aura/execute-intent`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        tool_name: toolName,
        params: params,
      }),
    });

    const clientLatencyMs = Math.round(performance.now() - t0);
    if (!res.ok) {
      let errDetail = {};
      try { errDetail = await res.json(); } catch (_) {}
      throw new Error(errDetail.detail?.error || `Erro HTTP ${res.status} ao executar ${toolName}`);
    }

    const payload = await res.json();
    payload.clientLatencyMs = clientLatencyMs;
    return payload;
  }

  /**
   * Streaming conversacional com a AURA via Server-Sent Events (SSE) multiplexados (F2-01)
   * Despacha eventos multiplexados sem atraso para renderização de tokens:
   * - onDelta: tokens textuais em tempo real (Resumo Executivo Camada 1)
   * - onSkeleton: placeholder visual do micro-widget (<100ms)
   * - onUIDelta: bufferização volátil de fragmentos parciais de JSON
   * - onUIComplete: envelope canônico GenUIEnvelope (Camada 2 & 3)
   * - onActionFeedback: retorno/confirmação de ações transacionais com voucher
   * - onChunk: observador universal para retrocompatibilidade
   * - onDone: finalização do stream
   * - onError: tratamento de erros e abortos
   */
  async streamChat(optionsOrQuery = {}, legacyOptions = {}) {
    const opts = (typeof optionsOrQuery === 'string')
      ? { query: optionsOrQuery, ...(legacyOptions && typeof legacyOptions === 'object' ? legacyOptions : {}) }
      : ((optionsOrQuery && typeof optionsOrQuery === 'object')
          ? { ...optionsOrQuery, ...(legacyOptions && typeof legacyOptions === 'object' ? legacyOptions : {}) }
          : {});
    const options = opts;

    const activeQuery = opts.query !== undefined
      ? opts.query
      : (opts.prompt !== undefined ? opts.prompt : (opts.message !== undefined ? opts.message : ''));
    const activeSessionId = (opts.sessionId !== undefined && opts.sessionId !== null)
      ? opts.sessionId
      : (opts.session_id !== undefined ? opts.session_id : null);
    const activeContext = opts.context || null;
    const activeTenantId = (opts.tenantId !== undefined && opts.tenantId !== null)
      ? opts.tenantId
      : (opts.tenant_id !== undefined ? opts.tenant_id : null);
    const activeFilialId = (opts.filialId !== undefined && opts.filialId !== null)
      ? opts.filialId
      : (opts.filial_id !== undefined ? opts.filial_id : null);
    const genuiFlag = opts.genui !== undefined ? opts.genui : opts.enable_genui;

    const onDelta = typeof opts.onDelta === 'function' ? opts.onDelta : () => {};
    const onSkeleton = typeof opts.onSkeleton === 'function' ? opts.onSkeleton : () => {};
    const onUIDelta = typeof opts.onUIDelta === 'function' ? opts.onUIDelta : () => {};
    const onUIComplete = typeof opts.onUIComplete === 'function' ? opts.onUIComplete : () => {};
    const onActionFeedback = typeof opts.onActionFeedback === 'function' ? opts.onActionFeedback : () => {};
    const onChunk = typeof opts.onChunk === 'function' ? opts.onChunk : () => {};
    const onDone = typeof opts.onDone === 'function' ? opts.onDone : () => {};
    const onError = typeof opts.onError === 'function' ? opts.onError : () => {};
    const signal = opts.signal || null;

    // F2-02: Buffer volátil de fragmentos JSON indexado por tool_call_id
    let fragmentBuffer = null;
    const FragmentBufferClass = (typeof AuraGenUI !== 'undefined' && AuraGenUI.GenUIFragmentBuffer) ||
      (typeof window !== 'undefined' && window.AuraGenUI && window.AuraGenUI.GenUIFragmentBuffer) ||
      (typeof GenUIFragmentBuffer !== 'undefined' ? GenUIFragmentBuffer : null);

    if (FragmentBufferClass) {
      fragmentBuffer = new FragmentBufferClass();
    } else {
      class LocalFragmentBuffer {
        constructor() { this._buffers = new Map(); }
        append(id, chunk) {
          if (!id) return null;
          const prev = this._buffers.get(id) || '';
          const str = (typeof chunk === 'object' && chunk !== null) ? JSON.stringify(chunk) : String(chunk || '');
          const acc = prev + str;
          this._buffers.set(id, acc);
          let parsed = null;
          try {
            const candidate = JSON.parse(acc);
            if (typeof candidate === 'object' && candidate !== null) parsed = candidate;
          } catch (_) { parsed = null; }
          return { tool_call_id: id, delta: str, accumulated: acc, parsed, isComplete: parsed !== null };
        }
        get(id) { return this._buffers.get(id) || ''; }
        getParsed(id) {
          const raw = this._buffers.get(id);
          if (!raw) return null;
          try { return JSON.parse(raw); } catch (_) { return null; }
        }
        clear(id) { if (id) this._buffers.delete(id); else this._buffers.clear(); }
      }
      fragmentBuffer = new LocalFragmentBuffer();
    }

    try {
      // Resolucao de Feature Flag GenUI (F9-01)
      let genuiParam = genuiFlag !== undefined ? genuiFlag : options.genui;
      if (genuiParam === undefined && typeof window !== 'undefined' && window.AuraGenUI && typeof window.AuraGenUI.isEnabled === 'function') {
        genuiParam = window.AuraGenUI.isEnabled();
      }

      let chatUrl = `${this.baseUrl}/api/v1/aura/chat`;
      const reqHeaders = {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      };

      if (genuiParam !== undefined) {
        const flagVal = (genuiParam === false || genuiParam === 0 || genuiParam === '0') ? '0' : '1';
        chatUrl += `?genui=${flagVal}`;
        reqHeaders['X-GenUI-Enabled'] = flagVal;
      }

      const response = await fetch(chatUrl, {
        method: 'POST',
        headers: reqHeaders,
        body: JSON.stringify({
          query: activeQuery,
          session_id: activeSessionId,
          stream: true,
          context: activeContext,
          tenant_id: activeTenantId,
          filial_id: activeFilialId,
          genui: genuiParam !== undefined ? (genuiParam !== false && genuiParam !== 0 && genuiParam !== '0') : undefined,
        }),
        signal: signal,
      });

      if (!response.ok) {
        throw new Error(`Falha na conexão de chat: HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let doneNotified = false;
      let currentEvent = null; // Preservado através das iterações de pacotes TCP

      const triggerDone = () => {
        if (!doneNotified) {
          doneNotified = true;
          if (fragmentBuffer) fragmentBuffer.clear();
          try {
            onDone();
          } catch (e) {
            console.error('[AuraAPI] Erro ao executar callback onDone:', e);
          }
        }
      };

      /**
       * Despacha um chunk individual para seus respectivos callbacks de ciclo de vida
       */
      const dispatchChunk = (eventCategory, rawDataStr) => {
        if (rawDataStr === '[DONE]') {
          triggerDone();
          return;
        }

        let chunkData;
        try {
          chunkData = JSON.parse(rawDataStr);
        } catch (err) {
          console.warn('[AuraAPI] Falha ao decodificar chunk JSON:', rawDataStr, err);
          return;
        }

        // Prioridade canônica do tipo de evento:
        // 1. chunk_type explícito no payload JSON (sempre canônico na AURA)
        // 2. eventCategory recebido da linha 'event:' do SSE
        // 3. 'delta' como fallback para texto comum
        const effectiveEvent = (chunkData && chunkData.chunk_type) || eventCategory || 'delta';

        if (effectiveEvent === 'done' || chunkData.chunk_type === 'done') {
          triggerDone();
          return;
        }

        // 1. Chunks de Texto (Resumo Executivo / Camada 1) - Não bloqueante, latência mínima
        if (effectiveEvent === 'delta' || chunkData.chunk_type === 'delta') {
          const deltaText = chunkData.text || '';
          if (onDelta) {
            onDelta(deltaText, chunkData);
          }
        }

        // 2. Chunks de Skeleton UI Precursor (<100ms)
        else if (effectiveEvent === 'ui_skeleton' || chunkData.chunk_type === 'ui_skeleton') {
          const skeletonData = chunkData.data || chunkData;
          if (onSkeleton) {
            onSkeleton(skeletonData, chunkData);
          }
        }

        // 3. Chunks de Fragmentos JSON (F2-02: Bufferização com Fallback Gracioso)
        else if (effectiveEvent === 'ui_delta' || chunkData.chunk_type === 'ui_delta') {
          const toolCallId = chunkData.tool_call_id || (chunkData.data && chunkData.data.tool_call_id) || 'default';
          const fragment = (chunkData.delta_json !== undefined ? chunkData.delta_json : (chunkData.data && chunkData.data.delta_json)) || chunkData.text || '';

          const bufferResult = fragmentBuffer ? fragmentBuffer.append(toolCallId, fragment) : {
            tool_call_id: toolCallId,
            delta: fragment,
            accumulated: fragment,
            parsed: null,
            isComplete: false,
          };

          const deltaPayload = {
            ...bufferResult,
            ...chunkData,
          };

          if (onUIDelta) {
            onUIDelta(deltaPayload, chunkData);
          }
        }

        // 4. Chunks de Envelope GenUI Completo (Hidratação Camada 2 & 3)
        else if (effectiveEvent === 'ui_complete' || chunkData.chunk_type === 'ui_complete') {
          const envelopeData = chunkData.envelope || chunkData.data || chunkData;
          const toolCallId = chunkData.tool_call_id || (envelopeData && envelopeData.tool_call_id);

          if (toolCallId && fragmentBuffer) {
            fragmentBuffer.clear(toolCallId);
          }

          if (onUIComplete) {
            onUIComplete(envelopeData, chunkData);
          }
        }

        // 5. Chunks de Feedback / Voucher de Ações Transacionais
        else if (
          effectiveEvent === 'ui_action_feedback' ||
          effectiveEvent === 'ui_action_result' ||
          chunkData.chunk_type === 'ui_action_feedback' ||
          chunkData.chunk_type === 'ui_action_result'
        ) {
          const feedbackData = chunkData.data || chunkData;
          if (onActionFeedback) {
            onActionFeedback(feedbackData, chunkData);
          }
        }

        // Despacho universal para observadores gerais / retrocompatibilidade
        if (onChunk) {
          onChunk({
            eventType: effectiveEvent,
            ...chunkData,
          });
        }
      };

      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          buffer += decoder.decode(); // Flush final do decodificador
          if (buffer.trim()) {
            const remainingLines = buffer.split('\n');
            for (const line of remainingLines) {
              const trimmed = line.trim();
              if (!trimmed) {
                currentEvent = null;
                continue;
              }
              if (trimmed.startsWith('event:')) {
                currentEvent = trimmed.slice(6).trim();
              } else if (trimmed.startsWith('data:')) {
                const dataStr = trimmed.startsWith('data: ') ? trimmed.slice(6) : trimmed.slice(5);
                dispatchChunk(currentEvent, dataStr);
              }
            }
          }
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // Mantém fragmento que estiver incompleto

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) {
            currentEvent = null; // Fim do bloco SSE
            continue;
          }

          if (trimmed.startsWith('event:')) {
            currentEvent = trimmed.slice(6).trim();
          } else if (trimmed.startsWith('data:')) {
            const dataStr = trimmed.startsWith('data: ') ? trimmed.slice(6) : trimmed.slice(5);
            dispatchChunk(currentEvent, dataStr);
          }
        }
      }

      triggerDone();
    } catch (err) {
      if (fragmentBuffer) fragmentBuffer.clear();
      if (err && err.name === 'AbortError') {
        console.log('[AuraAPI] Streaming abortado pelo usuário.');
      } else {
        console.error('[AuraAPI] Erro no stream SSE:', err);
      }
      try {
        onError(err);
      } catch (e) {
        console.error('[AuraAPI] Erro ao executar callback onError:', e);
      }
    }
  }

  /**
   * Alias canônico para retrocompatibilidade com chamadas chatStream()
   */
  async chatStream(optionsOrQuery = {}, legacyOptions = {}) {
    return this.streamChat(optionsOrQuery, legacyOptions);
  }

  /**
   * Executa uma acao transacional Human-in-the-Loop na rota /api/v1/aura/actions/execute (F5-01 / F5-04)
   * @param {string} actionId - Identificador RFC 4122 v4 da acao
   * @param {Object} [options={}] - Objeto contendo tool_call_id, session_id, action_name, action_type, payload e timeoutMs
   * @returns {Promise<Object>} Resposta contendo Action Voucher homologado
   */
  async executeAction(actionId, options = {}) {
    const toolCallId = options.tool_call_id || options.toolCallId || '';
    const sessionId = options.session_id || options.sessionId || '';
    const actionName = options.action_name || options.actionName || options.label || options.name || '';
    const actionType = options.action_type || options.actionType || 'mutation';
    const operatorId = options.operator_id || options.operatorId || 'operador_01';
    const operatorRole = options.operator_role || options.operatorRole || options.role || 'gerente';
    const payload = options.payload || options.props || {};
    const timeoutMs = Number(options.timeoutMs || 15000);

    const controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
    const timeoutTimer = controller ? setTimeout(() => controller.abort(), timeoutMs) : null;

    try {
      let wireActionId = actionId;
      const uuidRegex = /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$/;
      let isUuidValid = false;
      if (wireActionId && typeof wireActionId === 'string') {
        const lastUnderscore = wireActionId.lastIndexOf('_');
        const candidate = lastUnderscore !== -1 ? wireActionId.slice(lastUnderscore + 1) : wireActionId;
        isUuidValid = uuidRegex.test(candidate);
      }
      if (!isUuidValid) {
        if (!this._actionUuidMap) this._actionUuidMap = new Map();
        if (!this._actionUuidMap.has(actionId)) {
          const genUuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
            const r = Math.random() * 16 | 0;
            return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
          });
          this._actionUuidMap.set(actionId, 'act_' + genUuid);
        }
        wireActionId = this._actionUuidMap.get(actionId);
      }

      const fetchOpts = {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          tool_call_id: toolCallId,
          action_id: wireActionId,
          action_name: actionName,
          action_type: actionType,
          payload: payload,
          operator_id: operatorId,
          operator_role: operatorRole,
        }),
      };
      if (controller) {
        fetchOpts.signal = controller.signal;
      }

      const res = await fetch(`${this.baseUrl}/api/v1/aura/actions/execute`, fetchOpts);

      if (!res.ok) {
        let errDetail = {};
        try { errDetail = await res.json(); } catch (_) {}
        const errorMsg = (typeof errDetail.detail === 'string' ? errDetail.detail : errDetail.detail?.error) || errDetail.error || `Erro HTTP ${res.status} ao executar acao ${actionId}`;
        throw new Error(errorMsg);
      }

      const data = await res.json();
      if (data && typeof data === 'object') {
        data.action_id = actionId;
      }
      return data;
    } catch (err) {
      if (err && (err.name === 'AbortError' || String(err.message || '').toLowerCase().includes('abort'))) {
        throw new Error(`Timeout de conexao (${timeoutMs}ms) ao executar acao ${actionId}`);
      }
      throw err;
    } finally {
      if (timeoutTimer) clearTimeout(timeoutTimer);
    }
  }

  /**
   * Consulta a trilha duravel de auditoria transacional (F7-04)
   * @param {Object} [filters={}] - Filtros opcionais (session_id, action_id, operator_id, status, limit)
   * @returns {Promise<Array<Object>>} Registros da trilha de auditoria
   */
  async getAuditLogs(filters = {}) {
    const params = new URLSearchParams();
    if (filters.session_id) params.append('session_id', filters.session_id);
    if (filters.action_id) params.append('action_id', filters.action_id);
    if (filters.operator_id) params.append('operator_id', filters.operator_id);
    if (filters.status) params.append('status', filters.status);
    if (filters.limit) params.append('limit', String(filters.limit));

    const qs = params.toString() ? `?${params.toString()}` : '';
    const res = await fetch(`${this.baseUrl}/api/v1/aura/audit/logs${qs}`);
    if (!res.ok) {
      throw new Error(`Erro HTTP ${res.status} ao consultar logs de auditoria`);
    }
    return await res.json();
  }

  /**
   * Reporta metricas de telemetria e UX (hidratacao, ttft, rollback) de forma assincrona e nao-bloqueante (F9-02).
   * @param {Object} reportData
   * @returns {Promise<Object>}
   */
  async reportTelemetry(reportData) {
    if (!reportData || typeof reportData !== 'object') return { status: 'ignored' };
    const payload = JSON.stringify(reportData);
    const url = `${this.baseUrl}/api/v1/aura/telemetry/report`;

    // 1. Tenta navigator.sendBeacon se disponivel no browser (zero overhead)
    if (typeof navigator !== 'undefined' && typeof navigator.sendBeacon === 'function') {
      try {
        const blob = new Blob([payload], { type: 'application/json' });
        const queued = navigator.sendBeacon(url, blob);
        if (queued) return { status: 'queued_beacon' };
      } catch (_) {}
    }

    // 2. Fallback resiliente com fetch keepalive
    try {
      const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: payload,
        keepalive: true,
      });
      return await resp.json();
    } catch (err) {
      return { status: 'fallback_error', error: err && err.message };
    }
  }

  /**
   * Consulta os SLIs de observabilidade SRE da AURA (F9-02).
   * @returns {Promise<Object>}
   */
  async getTelemetryMetrics() {
    const resp = await fetch(`${this.baseUrl}/api/v1/aura/telemetry/metrics`);
    if (!resp.ok) {
      throw new Error(`Falha ao obter telemetria: HTTP ${resp.status}`);
    }
    return await resp.json();
  }

  /**
   * Consulta as feature flags ativas no backend (F9-03).
   * @returns {Promise<Object>}
   */
  async getFeatureFlags() {
    const resp = await fetch(`${this.baseUrl}/api/v1/aura/admin/feature-flags`);
    if (!resp.ok) {
      throw new Error(`Falha ao consultar feature flags: HTTP ${resp.status}`);
    }
    return await resp.json();
  }

  /**
   * Atualiza feature flags no backend em tempo de execucao a quente (F9-03).
   * @param {Object} flags
   * @returns {Promise<Object>}
   */
  async updateFeatureFlags(flags) {
    const resp = await fetch(`${this.baseUrl}/api/v1/aura/admin/feature-flags`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(flags),
    });
    if (!resp.ok) {
      throw new Error(`Falha ao atualizar feature flags: HTTP ${resp.status}`);
    }
    return await resp.json();
  }
}

// 1. Exportação Global no Navegador (Window)
if (typeof window !== 'undefined') {
  window.AuraApiClient = AuraApiClient;
  window.auraApi = new AuraApiClient();
}

// 2. Exportação CommonJS para testes headless e automação (Node.js)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    AuraApiClient,
    AuraApi: AuraApiClient,
  };
}
