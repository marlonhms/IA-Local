/**
 * AURA Core Engine API Client & Unified Transport (v3.0 - Carbon P0 Auth & SSE)
 * Centraliza todas as requisicoes HTTP e Server-Sent Events (SSE) sob AuraHttpTransport:
 * - credentials: "include" obrigatorio em 100% das chamadas (HttpOnly; SameSite=Strict P0.1)
 * - Normalizacao same-origin para loopback (evita quebra cross-site localhost vs 127.0.0.1)
 * - Bootstrap silencioso de sessao (GET /) com replay unico em 401 local
 * - Modal de pareamento X-API-Key (AuraLanAuthModal) para terminais na LAN
 * - Streaming SSE via fetch + ReadableStream (fim do EventSource nativo) com suporte a stream_reset
 * Zero travessoes em todo o arquivo.
 */

const AURA_LAN_SESSION_KEY = 'aura_lan_api_key';
const AURA_LAN_PERSIST_KEY = 'aura_api_key';
const AURA_LOOPBACK_HOSTS = new Set(['127.0.0.1', 'localhost', '::1', '[::1]']);

function isBrowserEnv() {
  return typeof window !== 'undefined' && typeof document !== 'undefined';
}

function isLoopbackHostname(hostname) {
  if (!hostname) return false;
  return AURA_LOOPBACK_HOSTS.has(String(hostname).toLowerCase());
}

/**
 * Modal Glassmorphism de Pareamento de Terminal LAN (X-API-Key)
 * Acionado automaticamente apenas quando um terminal nao-loopback recebe HTTP 401.
 */
class AuraLanAuthModal {
  constructor() {
    this._pendingPromise = null;
    this._modalId = 'aura-lan-auth-modal';
  }

  promptForKey(reason = '') {
    if (!isBrowserEnv() || !document.body) {
      return Promise.resolve(null);
    }
    if (this._pendingPromise) {
      return this._pendingPromise;
    }

    this._pendingPromise = new Promise((resolve) => {
      const existing = document.getElementById(this._modalId);
      if (existing) existing.remove();

      const backdrop = document.createElement('div');
      backdrop.id = this._modalId;
      backdrop.className = 'fixed inset-0 z-[120] flex items-center justify-center p-4 bg-slate-950/85 backdrop-blur-xl';
      backdrop.setAttribute('role', 'dialog');
      backdrop.setAttribute('aria-modal', 'true');
      backdrop.setAttribute('aria-labelledby', 'aura-lan-auth-title');

      const safeReason = String(reason || '').replace(/[<>&"']/g, '');
      const reasonBlock = safeReason
        ? `<p class="text-[11px] font-mono text-amber-300 bg-amber-500/10 border border-amber-500/25 rounded-lg px-3 py-2">${safeReason}</p>`
        : '';

      backdrop.innerHTML = `
        <div class="w-full max-w-md rounded-2xl border border-white/10 bg-[#0c111c]/95 shadow-2xl p-6 space-y-4 font-sans text-slate-200">
          <div class="flex items-start justify-between gap-3 border-b border-white/10 pb-3">
            <div>
              <div class="flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-cyan-400"></span>
                <h3 id="aura-lan-auth-title" class="text-sm font-bold text-white tracking-wide">Pareamento de Terminal LAN</h3>
              </div>
              <p class="text-xs text-slate-400 mt-1">
                Este acesso ocorre pela rede local (LAN). Informe a chave de API do servidor AURA para autenticar esta sessao.
              </p>
            </div>
            <button type="button" data-lan-action="cancel" class="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white text-xs" aria-label="Fechar">✕</button>
          </div>
          ${reasonBlock}
          <form id="aura-lan-auth-form" class="space-y-3">
            <div>
              <label for="aura-lan-api-key-input" class="block text-[11px] font-medium text-slate-300 mb-1">Chave de Acesso (X-API-Key)</label>
              <div class="relative">
                <input id="aura-lan-api-key-input" type="password" autocomplete="off" spellcheck="false" placeholder="Cole a AURA_API_KEY do servidor..." class="w-full px-3 py-2.5 pr-16 rounded-xl bg-[#07090e] border border-white/15 focus:border-cyan-400 focus:outline-none text-xs font-mono text-white placeholder-slate-500" required />
                <button type="button" id="aura-lan-toggle-vis" class="absolute right-2 top-1/2 -translate-y-1/2 px-2 py-1 rounded-md text-[10px] font-mono text-slate-400 hover:text-cyan-300">Ver</button>
              </div>
            </div>
            <label class="flex items-center gap-2 text-xs text-slate-400 cursor-pointer select-none">
              <input id="aura-lan-remember-check" type="checkbox" class="rounded border-white/20 bg-slate-900 text-cyan-400 focus:ring-cyan-400" />
              <span>Lembrar neste terminal confiavel (localStorage)</span>
            </label>
            <div class="flex items-center justify-end gap-2 pt-2 border-t border-white/10">
              <button type="button" data-lan-action="cancel" class="px-3.5 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 text-xs font-medium border border-white/10">Cancelar</button>
              <button type="submit" class="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs transition-colors">Autenticar Terminal</button>
            </div>
          </form>
        </div>
      `;

      const cleanup = (result) => {
        document.removeEventListener('keydown', onKeyDown);
        backdrop.remove();
        this._pendingPromise = null;
        resolve(result);
      };

      const onKeyDown = (e) => {
        if (e.key === 'Escape') {
          e.preventDefault();
          cleanup(null);
        }
      };

      document.addEventListener('keydown', onKeyDown);
      backdrop.addEventListener('click', (e) => {
        if (e.target === backdrop) cleanup(null);
      });

      backdrop.querySelectorAll('[data-lan-action="cancel"]').forEach((btn) => {
        btn.addEventListener('click', () => cleanup(null));
      });

      const toggleBtn = backdrop.querySelector('#aura-lan-toggle-vis');
      const inputEl = backdrop.querySelector('#aura-lan-api-key-input');
      const rememberEl = backdrop.querySelector('#aura-lan-remember-check');
      const formEl = backdrop.querySelector('#aura-lan-auth-form');

      if (toggleBtn && inputEl) {
        toggleBtn.addEventListener('click', () => {
          const isPwd = inputEl.type === 'password';
          inputEl.type = isPwd ? 'text' : 'password';
          toggleBtn.textContent = isPwd ? 'Ocultar' : 'Ver';
        });
      }

      if (formEl && inputEl) {
        formEl.addEventListener('submit', (e) => {
          e.preventDefault();
          const key = String(inputEl.value || '').trim();
          if (!key) return;
          cleanup({ key, persist: Boolean(rememberEl && rememberEl.checked) });
        });
      }

      document.body.appendChild(backdrop);
      if (inputEl) {
        setTimeout(() => inputEl.focus(), 30);
      }
    });

    return this._pendingPromise;
  }
}

/**
 * Transporte Unificado HTTP + SSE da AURA (P0-UI1)
 * Garante credentials: "include", protecao same-origin, bootstrap 401 local e pareamento LAN.
 */
class AuraHttpTransport {
  constructor(options = {}) {
    const rawBase = typeof options === 'string'
      ? options
      : (options && options.baseUrl ? options.baseUrl : '');
    this.baseUrl = this._normalizeBaseUrl(rawBase);
    this.explicitApiKey = (options && typeof options === 'object' && options.apiKey) ? String(options.apiKey) : '';
    this.lanAuthModal = new AuraLanAuthModal();
    this._bootstrapPromise = null;
  }

  _normalizeBaseUrl(rawBase) {
    const cleaned = String(rawBase || '').trim().replace(/\/+$/, '');
    if (!cleaned) return '';

    // Em navegador HTTP/HTTPS loopback, forca URLs relativas para evitar
    // divergencia cross-site (localhost vs 127.0.0.1) em cookies SameSite=Strict.
    if (isBrowserEnv() && window.location && (window.location.protocol === 'http:' || window.location.protocol === 'https:')) {
      try {
        const parsed = new URL(cleaned, window.location.origin);
        if (parsed.origin === window.location.origin) {
          return '';
        }
        if (
          isLoopbackHostname(window.location.hostname) &&
          isLoopbackHostname(parsed.hostname) &&
          parsed.port === window.location.port
        ) {
          return '';
        }
      } catch (_) {}
    }

    return cleaned;
  }

  isLocalhostRuntime() {
    if (!isBrowserEnv() || !window.location) return false;
    const proto = window.location.protocol;
    if (proto !== 'http:' && proto !== 'https:') return false;
    return isLoopbackHostname(window.location.hostname);
  }

  isLanRuntime() {
    if (!isBrowserEnv() || !window.location) return false;
    const proto = window.location.protocol;
    if (proto !== 'http:' && proto !== 'https:') return false;
    return !isLoopbackHostname(window.location.hostname);
  }

  resolveUrl(path) {
    if (!path) return this.baseUrl || '/';
    if (/^https?:\/\//i.test(path)) return path;
    const normalizedPath = path.startsWith('/') ? path : `/${path}`;
    return `${this.baseUrl}${normalizedPath}`;
  }

  getApiKey() {
    if (this.explicitApiKey) return this.explicitApiKey;
    if (typeof window !== 'undefined') {
      if (window.AURA_API_KEY) return String(window.AURA_API_KEY);
      try {
        const sessionKey = window.sessionStorage && window.sessionStorage.getItem(AURA_LAN_SESSION_KEY);
        if (sessionKey) return sessionKey;
      } catch (_) {}
      try {
        const persistedKey = window.localStorage && window.localStorage.getItem(AURA_LAN_PERSIST_KEY);
        if (persistedKey) return persistedKey;
      } catch (_) {}
    }
    return '';
  }

  setApiKey(key, persist = false) {
    const clean = String(key || '').trim();
    if (!clean) return;
    this.explicitApiKey = clean;
    if (typeof window !== 'undefined') {
      try {
        if (window.sessionStorage) window.sessionStorage.setItem(AURA_LAN_SESSION_KEY, clean);
      } catch (_) {}
      if (persist) {
        try {
          if (window.localStorage) window.localStorage.setItem(AURA_LAN_PERSIST_KEY, clean);
        } catch (_) {}
      }
    }
  }

  clearApiKey() {
    this.explicitApiKey = '';
    if (typeof window !== 'undefined') {
      try {
        if (window.sessionStorage) window.sessionStorage.removeItem(AURA_LAN_SESSION_KEY);
      } catch (_) {}
      try {
        if (window.localStorage) window.localStorage.removeItem(AURA_LAN_PERSIST_KEY);
      } catch (_) {}
    }
  }

  buildHeaders(extraHeaders = {}) {
    const headers = Object.assign({}, extraHeaders || {});
    const apiKey = this.getApiKey();
    if (apiKey && !headers['X-API-Key'] && !headers['x-api-key'] && !headers['Authorization']) {
      headers['X-API-Key'] = apiKey;
    }
    return headers;
  }

  /**
   * Renova silenciosamente o cookie HttpOnly (aura_local_session) via GET /
   * usando promessa deduplicada para evitar thundering herd em chamadas paralelas.
   */
  async ensureLocalSessionBootstrap() {
    if (this._bootstrapPromise) {
      return this._bootstrapPromise;
    }
    const bootstrapUrl = this.resolveUrl('/');
    this._bootstrapPromise = (async () => {
      try {
        const resp = await fetch(bootstrapUrl, {
          method: 'GET',
          credentials: 'include',
          cache: 'no-store',
          headers: { Accept: 'text/html' },
        });
        return resp && resp.ok;
      } catch (err) {
        console.warn('[AuraHttpTransport] Falha no bootstrap silencioso de sessao local:', err);
        return false;
      } finally {
        this._bootstrapPromise = null;
      }
    })();
    return this._bootstrapPromise;
  }

  /**
   * Executa qualquer requisicao HTTP com credentials: "include", cabecalhos de auth
   * e recuperacao automatica de 401 (bootstrap em localhost / modal em LAN).
   */
  async request(path, options = {}) {
    const url = this.resolveUrl(path);
    const isRetry = Boolean(options._isRetry);
    const skipAuthRecovery = Boolean(options._skipAuthRecovery);

    const fetchOptions = {
      method: options.method || 'GET',
      credentials: options.credentials || 'include',
      headers: this.buildHeaders(options.headers),
    };

    if (options.body !== undefined) fetchOptions.body = options.body;
    if (options.signal) fetchOptions.signal = options.signal;
    if (options.keepalive !== undefined) fetchOptions.keepalive = options.keepalive;
    if (options.cache) fetchOptions.cache = options.cache;

    const response = await fetch(url, fetchOptions);

    if (response && response.status === 401 && !isRetry && !skipAuthRecovery) {
      if (this.isLocalhostRuntime()) {
        const bootstrapped = await this.ensureLocalSessionBootstrap();
        if (bootstrapped) {
          return this.request(path, Object.assign({}, options, { _isRetry: true }));
        }
      } else if (this.isLanRuntime()) {
        const authResult = await this.lanAuthModal.promptForKey(
          'Autenticacao necessaria (HTTP 401). Informe a X-API-Key do servidor AURA.'
        );
        if (authResult && authResult.key) {
          this.setApiKey(authResult.key, authResult.persist);
          return this.request(path, Object.assign({}, options, { _isRetry: true }));
        }
      }
    }

    return response;
  }

  /**
   * Leitor unificado de Server-Sent Events (SSE) sobre fetch + ReadableStream.
   * Suporta GET e POST, credentials: "include", X-API-Key na LAN e fragmentacao TCP.
   */
  async streamSse(path, options = {}) {
    const onEvent = typeof options.onEvent === 'function' ? options.onEvent : () => {};
    const onOpen = typeof options.onOpen === 'function' ? options.onOpen : () => {};

    const headers = Object.assign(
      { Accept: 'text/event-stream' },
      options.headers || {}
    );

    const response = await this.request(path, {
      method: options.method || 'GET',
      headers: headers,
      body: options.body,
      signal: options.signal,
      _skipAuthRecovery: Boolean(options._skipAuthRecovery),
    });

    if (!response.ok) {
      const err = new Error(`Falha na conexao SSE: HTTP ${response.status}`);
      err.status = response.status;
      throw err;
    }

    onOpen(response);

    if (!response.body || typeof response.body.getReader !== 'function') {
      throw new Error('ReadableStream indisponivel na resposta SSE.');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';
    let currentEvent = null;

    const processLine = (line) => {
      const trimmed = line.trim();
      if (!trimmed) {
        currentEvent = null;
        return;
      }
      if (trimmed.startsWith(':')) {
        return;
      }
      if (trimmed.startsWith('event:')) {
        currentEvent = trimmed.slice(6).trim();
      } else if (trimmed.startsWith('data:')) {
        const dataStr = trimmed.startsWith('data: ') ? trimmed.slice(6) : trimmed.slice(5);
        onEvent(currentEvent, dataStr);
      }
    };

    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          buffer += decoder.decode();
          if (buffer.trim()) {
            const remainingLines = buffer.split('\n');
            for (const line of remainingLines) {
              processLine(line);
            }
          }
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          processLine(line);
        }
      }
    } finally {
      try {
        reader.releaseLock();
      } catch (_) {}
    }

    return response;
  }

  /**
   * Envio nao-bloqueante de telemetria respeitando sessao P0.1:
   * usa sendBeacon apenas em loopback sem chave customizada; na LAN usa fetch keepalive autenticado.
   */
  async sendTelemetryBeacon(path, payloadStr) {
    const url = this.resolveUrl(path);
    const hasCustomKey = Boolean(this.getApiKey());

    if (
      !hasCustomKey &&
      !this.isLanRuntime() &&
      typeof navigator !== 'undefined' &&
      typeof navigator.sendBeacon === 'function'
    ) {
      try {
        const blob = new Blob([payloadStr], { type: 'application/json' });
        const queued = navigator.sendBeacon(url, blob);
        if (queued) return { status: 'queued_beacon' };
      } catch (_) {}
    }

    try {
      const resp = await this.request(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: payloadStr,
        keepalive: true,
        _skipAuthRecovery: true,
      });
      if (!resp.ok) {
        return { status: 'fallback_http_error', httpStatus: resp.status };
      }
      return await resp.json();
    } catch (err) {
      return { status: 'fallback_error', error: err && err.message };
    }
  }
}

class AuraApiClient {
  constructor(baseUrlOrOptions = '') {
    const opts = (typeof baseUrlOrOptions === 'object' && baseUrlOrOptions !== null)
      ? baseUrlOrOptions
      : { baseUrl: baseUrlOrOptions || '' };
    this.transport = new AuraHttpTransport(opts);
    this.baseUrl = this.transport.baseUrl;
  }

  async request(path, options = {}) {
    return this.transport.request(path, options);
  }

  /**
   * Health check operacional
   */
  async getHealth() {
    const res = await this.transport.request('/api/v1/aura/health');
    if (!res.ok) throw new Error(`Health check falhou: ${res.status}`);
    return await res.json();
  }

  /**
   * Obtem identificacao e status da estacao
   */
  async getStationStatus() {
    const res = await this.transport.request('/api/v1/aura/stations');
    if (!res.ok) throw new Error(`Falha ao obter status da estacao: ${res.status}`);
    const data = await res.json();
    return Array.isArray(data) && data.length > 0 ? data[0] : null;
  }

  /**
   * Retorna lista completa de estacoes (utilizado pela telemetria SRE)
   */
  async getStations() {
    const res = await this.transport.request('/api/v1/aura/stations');
    if (!res.ok) throw new Error(`Falha ao obter estacoes: ${res.status}`);
    return await res.json();
  }

  /**
   * Invoca diretamente uma das ferramentas analiticas (sub-100ms, sem custo LLM)
   */
  async executeIntent(toolName, params = {}) {
    const t0 = performance.now();
    const res = await this.transport.request('/api/v1/aura/execute-intent', {
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
   * Streaming conversacional com a AURA via Server-Sent Events (SSE) multiplexados (P0)
   * Suporta credentials: "include", X-API-Key na LAN e evento transacional stream_reset (P0.4).
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
    const onStreamReset = typeof opts.onStreamReset === 'function' ? opts.onStreamReset : () => {};
    const onChunk = typeof opts.onChunk === 'function' ? opts.onChunk : () => {};
    const onDone = typeof opts.onDone === 'function' ? opts.onDone : () => {};
    const onError = typeof opts.onError === 'function' ? opts.onError : () => {};
    const signal = opts.signal || null;

    // Buffer volatil de fragmentos JSON indexado por tool_call_id
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
      let genuiParam = genuiFlag !== undefined ? genuiFlag : options.genui;
      if (genuiParam === undefined && typeof window !== 'undefined' && window.AuraGenUI && typeof window.AuraGenUI.isEnabled === 'function') {
        genuiParam = window.AuraGenUI.isEnabled();
      }

      let chatUrl = '/api/v1/aura/chat';
      const reqHeaders = {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      };

      if (genuiParam !== undefined) {
        const flagVal = (genuiParam === false || genuiParam === 0 || genuiParam === '0') ? '0' : '1';
        chatUrl += `?genui=${flagVal}`;
        reqHeaders['X-GenUI-Enabled'] = flagVal;
      }

      let doneNotified = false;
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

        const effectiveEvent = (chunkData && chunkData.chunk_type) || eventCategory || 'delta';

        if (effectiveEvent === 'done' || chunkData.chunk_type === 'done') {
          triggerDone();
          return;
        }

        // 0. Reset Transacional de Stream em fallback de modelo (P0.4)
        if (effectiveEvent === 'stream_reset' || chunkData.chunk_type === 'stream_reset') {
          if (fragmentBuffer) fragmentBuffer.clear();
          if (onStreamReset) {
            onStreamReset(chunkData);
          }
        }
        // 1. Chunks de Texto (Resumo Executivo)
        else if (effectiveEvent === 'delta' || chunkData.chunk_type === 'delta') {
          const deltaText = chunkData.text || '';
          if (onDelta) {
            onDelta(deltaText, chunkData);
          }
        }
        // 2. Chunks de Skeleton UI Precursor
        else if (effectiveEvent === 'ui_skeleton' || chunkData.chunk_type === 'ui_skeleton') {
          const skeletonData = chunkData.data || chunkData;
          if (onSkeleton) {
            onSkeleton(skeletonData, chunkData);
          }
        }
        // 3. Chunks de Fragmentos JSON (ui_delta)
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
        // 4. Chunks de Envelope GenUI Completo (ui_complete)
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
        // 5. Chunks de Feedback / Voucher de Acoes Transacionais
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
        // 6. Chunks de Alerta Proativo In-App da AURA
        else if (effectiveEvent === 'proactive_alert' || chunkData.chunk_type === 'proactive_alert') {
          const alertData = chunkData.data || chunkData;
          if (typeof opts.onProactiveAlert === 'function') {
            opts.onProactiveAlert(alertData, chunkData);
          }
          if (typeof window !== 'undefined' && window.auraChat && typeof window.auraChat.handleProactiveAlert === 'function') {
            window.auraChat.handleProactiveAlert(alertData);
          }
        }

        if (onChunk) {
          onChunk({
            eventType: effectiveEvent,
            ...chunkData,
          });
        }
      };

      await this.transport.streamSse(chatUrl, {
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
        onEvent: dispatchChunk,
      });

      triggerDone();
    } catch (err) {
      if (fragmentBuffer) fragmentBuffer.clear();
      if (err && err.name === 'AbortError') {
        console.log('[AuraAPI] Streaming abortado pelo usuario.');
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
   * Alias canonico para retrocompatibilidade com chamadas chatStream()
   */
  async chatStream(optionsOrQuery = {}, legacyOptions = {}) {
    return this.streamChat(optionsOrQuery, legacyOptions);
  }

  /**
   * Executa uma acao transacional Human-in-the-Loop na rota /api/v1/aura/actions/execute
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

      const res = await this.transport.request('/api/v1/aura/actions/execute', fetchOpts);

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
   * Consulta a trilha duravel de auditoria transacional
   */
  async getAuditLogs(filters = {}) {
    const params = new URLSearchParams();
    if (filters.session_id) params.append('session_id', filters.session_id);
    if (filters.action_id) params.append('action_id', filters.action_id);
    if (filters.operator_id) params.append('operator_id', filters.operator_id);
    if (filters.status) params.append('status', filters.status);
    if (filters.limit) params.append('limit', String(filters.limit));

    const qs = params.toString() ? `?${params.toString()}` : '';
    const res = await this.transport.request(`/api/v1/aura/audit/logs${qs}`);
    if (!res.ok) {
      throw new Error(`Erro HTTP ${res.status} ao consultar logs de auditoria`);
    }
    return await res.json();
  }

  /**
   * Reporta metricas de telemetria e UX de forma assincrona e nao-bloqueante
   */
  async reportTelemetry(reportData) {
    if (!reportData || typeof reportData !== 'object') return { status: 'ignored' };
    return this.transport.sendTelemetryBeacon('/api/v1/aura/telemetry/report', JSON.stringify(reportData));
  }

  /**
   * Consulta os SLIs de observabilidade SRE da AURA
   */
  async getTelemetryMetrics() {
    const resp = await this.transport.request('/api/v1/aura/telemetry/metrics');
    if (!resp.ok) {
      throw new Error(`Falha ao obter telemetria: HTTP ${resp.status}`);
    }
    return await resp.json();
  }

  /**
   * Consulta o orcamento de tokens (FiscalLLM)
   */
  async getTokenBudget() {
    const resp = await this.transport.request('/api/v1/aura/telemetry/token-budget');
    if (!resp.ok) {
      throw new Error(`Falha ao consultar orcamento de tokens: HTTP ${resp.status}`);
    }
    return await resp.json();
  }

  /**
   * Atualiza a politica orcamentaria de tokens (FiscalLLM)
   */
  async updateTokenBudgetPolicy(policy) {
    const resp = await this.transport.request('/api/v1/aura/telemetry/token-budget/policy', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(policy || {}),
    });
    if (!resp.ok) {
      throw new Error(`Falha ao atualizar politica orcamentaria: HTTP ${resp.status}`);
    }
    return await resp.json();
  }

  /**
   * CRUD de Memoria Operacional do Tenant (Camada Tenant)
   */
  async listTenantMemories() {
    const resp = await this.transport.request('/api/v1/aura/memory/tenant');
    if (!resp.ok) {
      throw new Error(`Falha ao listar memoria do tenant: HTTP ${resp.status}`);
    }
    return await resp.json();
  }

  async createTenantMemory(payload) {
    const resp = await this.transport.request('/api/v1/aura/memory/tenant', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload || {}),
    });
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`);
    }
    return await resp.json();
  }

  async approveTenantMemory(factId, approvedBy = 'gestor_painel') {
    const resp = await this.transport.request(`/api/v1/aura/memory/tenant/${encodeURIComponent(factId)}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ approved_by: approvedBy }),
    });
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`);
    }
    return await resp.json();
  }

  async rejectTenantMemory(factId, reason = 'Rejeitado pelo gestor no painel') {
    const resp = await this.transport.request(`/api/v1/aura/memory/tenant/${encodeURIComponent(factId)}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason }),
    });
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`);
    }
    return await resp.json();
  }

  async deleteTenantMemory(factId) {
    const resp = await this.transport.request(`/api/v1/aura/memory/tenant/${encodeURIComponent(factId)}`, {
      method: 'DELETE',
    });
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`);
    }
    return await resp.json();
  }

  /**
   * Consulta as feature flags ativas no backend
   */
  async getFeatureFlags() {
    const resp = await this.transport.request('/api/v1/aura/admin/feature-flags');
    if (!resp.ok) {
      throw new Error(`Falha ao consultar feature flags: HTTP ${resp.status}`);
    }
    return await resp.json();
  }

  /**
   * Atualiza feature flags no backend em tempo de execucao a quente
   */
  async updateFeatureFlags(flags) {
    const resp = await this.transport.request('/api/v1/aura/admin/feature-flags', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(flags),
    });
    if (!resp.ok) {
      throw new Error(`Falha ao atualizar feature flags: HTTP ${resp.status}`);
    }
    return await resp.json();
  }

  /**
   * Consulta as configuracoes e toggles da Central de Automacoes da AURA
   */
  async getAutomationSettings() {
    const resp = await this.transport.request('/api/v1/aura/admin/automation-settings');
    if (!resp.ok) {
      throw new Error(`Falha ao consultar configuracoes de automacao: HTTP ${resp.status}`);
    }
    return await resp.json();
  }

  /**
   * Atualiza as configuracoes e regras da Central de Automacoes
   */
  async updateAutomationSettings(settings) {
    const resp = await this.transport.request('/api/v1/aura/admin/automation-settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
    });
    if (!resp.ok) {
      let errDetail = {};
      try { errDetail = await resp.json(); } catch (_) {}
      throw new Error(errDetail.detail?.error || `Falha ao atualizar configuracoes de automacao: HTTP ${resp.status}`);
    }
    return await resp.json();
  }

  /**
   * Consulta o status de conformidade juridica e opt-in do lojista
   */
  async getComplianceStatus(cnpj = null) {
    const query = cnpj ? `?cnpj=${encodeURIComponent(cnpj)}` : '';
    const resp = await this.transport.request(`/api/v1/aura/compliance/status${query}`);
    if (!resp.ok) {
      throw new Error(`Falha ao consultar status de conformidade: HTTP ${resp.status}`);
    }
    return await resp.json();
  }

  /**
   * Obtem o conteudo integral do termo de interoperabilidade v1.1 e hash SHA-256
   */
  async getComplianceTerm() {
    const resp = await this.transport.request('/api/v1/aura/compliance/term');
    if (!resp.ok) {
      throw new Error(`Falha ao obter termo de conformidade: HTTP ${resp.status}`);
    }
    return await resp.json();
  }

  /**
   * Registra duravelmente o opt-in de interoperabilidade do lojista
   */
  async registerComplianceOptIn(payload) {
    const resp = await this.transport.request('/api/v1/aura/compliance/opt-in', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      let errDetail = {};
      try { errDetail = await resp.json(); } catch (_) {}
      throw new Error(errDetail.detail?.error || `Falha ao registrar opt-in: HTTP ${resp.status}`);
    }
    return await resp.json();
  }

  /**
   * Historico duravel de sessoes de conversa no backend
   */
  async getSessionHistory(sessionId) {
    const resp = await this.transport.request(`/api/v1/aura/sessions/${encodeURIComponent(sessionId)}`);
    if (!resp.ok) {
      throw new Error(`Falha ao carregar historico da sessao: HTTP ${resp.status}`);
    }
    return await resp.json();
  }

  async listSessions(limit = 100) {
    const resp = await this.transport.request(`/api/v1/aura/sessions?limit=${encodeURIComponent(String(limit))}`);
    if (!resp.ok) {
      throw new Error(`Falha ao listar sessoes: HTTP ${resp.status}`);
    }
    return await resp.json();
  }

  async deleteSession(sessionId) {
    const resp = await this.transport.request(`/api/v1/aura/sessions/${encodeURIComponent(sessionId)}`, {
      method: 'DELETE',
    });
    if (!resp.ok) {
      throw new Error(`Falha ao excluir sessao: HTTP ${resp.status}`);
    }
    return await resp.json().catch(() => ({ status: 'ok' }));
  }

  async clearAllSessions() {
    const resp = await this.transport.request('/api/v1/aura/sessions', {
      method: 'DELETE',
    });
    if (!resp.ok) {
      throw new Error(`Falha ao limpar sessoes: HTTP ${resp.status}`);
    }
    return await resp.json().catch(() => ({ status: 'ok' }));
  }

  /**
   * Feed Executivo Zero-Click e Despacho de Diretivas (Cockpit)
   */
  async getZeroClickFeed(forceRefresh = false) {
    const qs = `?force_refresh=${forceRefresh ? 'true' : 'false'}`;
    let res = await this.transport.request(`/api/v1/cockpit/zero-click-feed${qs}`);
    if (!res.ok) {
      res = await this.transport.request(`/api/v1/aura/cockpit/zero-click-feed${qs}`);
    }
    if (!res.ok) {
      throw new Error(`Falha ao consultar Feed Zero-Click: HTTP ${res.status}`);
    }
    return await res.json();
  }

  async dispatchDirective(payload) {
    const res = await this.transport.request('/api/v1/aura/directives/dispatch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload || {}),
    });
    if (!res.ok) {
      throw new Error(`Falha ao despachar diretiva: HTTP ${res.status}`);
    }
    return await res.json();
  }

  /**
   * Telemetria ao vivo de Arquitetura de Seguranca Clean Room
   */
  async getSecurityTelemetry() {
    let res = await this.transport.request('/api/v1/aura/security/telemetry');
    if (!res.ok) {
      res = await this.transport.request('/api/v1/aura/compliance/security/telemetry');
    }
    if (!res.ok) {
      throw new Error(`Falha ao consultar telemetria de seguranca: HTTP ${res.status}`);
    }
    return await res.json();
  }

  /**
   * Transcricao de comando de voz via Groq Whisper local gateway
   */
  async transcribeVoice(audioBlob, mimeType = 'audio/webm') {
    const res = await this.transport.request('/api/v1/aura/voice/transcribe', {
      method: 'POST',
      headers: { 'Content-Type': mimeType || 'audio/webm' },
      body: audioBlob,
    });
    const data = await res.json().catch(() => ({}));
    return { ok: res.ok, status: res.status, data };
  }

  /**
   * Simulador deterministico What-If (POST /api/v1/aura/what-if/simulate)
   */
  async simulateWhatIf(payload) {
    const res = await this.transport.request('/api/v1/aura/what-if/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload || {}),
    });
    if (!res.ok) {
      throw new Error(`Falha ao simular cenario What-If: HTTP ${res.status}`);
    }
    return await res.json();
  }

  /**
   * Recalculo interativo Zero-LLM What-If (POST /api/v1/simulate/recompute)
   */
  async recomputeWhatIf(payload, options = {}) {
    const res = await this.transport.request('/api/v1/simulate/recompute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: options.signal,
      body: JSON.stringify(payload || {}),
    });
    if (!res.ok) {
      const errText = await res.text().catch(() => '');
      throw new Error(`Falha ao recalcular simulacao What-If: HTTP ${res.status} ${errText}`);
    }
    return await res.json();
  }

  /**
   * Feed consolidado HiC: regras candidate + simulacoes sugeridas (GET /api/v1/memory/suggestions)
   */
  async getMemoryGovernanceFeed(packId = 'fuel_convenience', tenantId = 'default') {
    const params = new URLSearchParams({
      pack_id: packId,
      tenant_id: tenantId,
    });
    const res = await this.transport.request(`/api/v1/memory/suggestions?${params.toString()}`, {
      method: 'GET',
    });
    if (!res.ok) {
      throw new Error(`Falha ao consultar feed de governanca HiC: HTTP ${res.status}`);
    }
    return await res.json();
  }

  /**
   * Decisao explicita HiC sobre regra candidate (POST /api/v1/memory/rules/{rule_id}/decision)
   */
  async decideMemoryRule(ruleId, payload) {
    const res = await this.transport.request(
      `/api/v1/memory/rules/${encodeURIComponent(ruleId)}/decision`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload || {}),
      },
    );
    if (!res.ok) {
      const errText = await res.text().catch(() => '');
      throw new Error(`Falha ao registrar decisao HiC: HTTP ${res.status} ${errText}`);
    }
    return await res.json();
  }

  /**
   * Execucao deterministica de backtesting 30/60/90d (POST /api/v1/simulate/backtest/run)
   */
  async runSimulationBacktest(payload) {
    const res = await this.transport.request('/api/v1/simulate/backtest/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload || {}),
    });
    if (!res.ok) {
      throw new Error(`Falha ao executar backtesting: HTTP ${res.status}`);
    }
    return await res.json();
  }

  /**
   * Scorecard Previsto vs. Realizado (GET /api/v1/simulate/backtest/scorecard)
   */
  async getBacktestScorecard(packId = 'fuel_convenience', tenantId = 'default', limit = 20) {
    const params = new URLSearchParams({
      pack_id: packId,
      tenant_id: tenantId,
      limit: String(limit),
    });
    const res = await this.transport.request(
      `/api/v1/simulate/backtest/scorecard?${params.toString()}`,
      { method: 'GET' },
    );
    if (!res.ok) {
      throw new Error(`Falha ao consultar scorecard de backtesting: HTTP ${res.status}`);
    }
    return await res.json();
  }

  /**
   * Alertas proativos in-app
   */
  async getProactiveAlerts(params = {}) {
    const searchParams = new URLSearchParams();
    if (params.limit) searchParams.set('limit', String(params.limit));
    if (params.offset) searchParams.set('offset', String(params.offset));
    if (params.alert_type) searchParams.set('alert_type', String(params.alert_type));
    if (params.severity) searchParams.set('severity', String(params.severity));
    if (params.filial_id) searchParams.set('filial_id', String(params.filial_id));
    if (params.unread_only) searchParams.set('unread_only', 'true');
    const queryStr = searchParams.toString();
    const url = `/api/v1/aura/proactive/alerts${queryStr ? '?' + queryStr : ''}`;
    const res = await this.transport.request(url);
    if (!res.ok) throw new Error(`Falha ao obter alertas proativos: HTTP ${res.status}`);
    return await res.json();
  }

  async getProactiveStatus() {
    const res = await this.transport.request('/api/v1/aura/proactive/status');
    if (!res.ok) throw new Error(`Falha ao consultar status proativo: HTTP ${res.status}`);
    return await res.json();
  }

  async ackProactiveAlert(alertId = null) {
    const res = await this.transport.request('/api/v1/aura/proactive/alerts/ack', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ alert_id: alertId || null }),
    });
    if (!res.ok) throw new Error(`Falha ao confirmar alerta proativo: HTTP ${res.status}`);
    return await res.json();
  }

  /**
   * Assina o canal SSE de alertas proativos via fetch + ReadableStream (sem EventSource nativo).
   * Compativel com cookies HttpOnly/SameSite=Strict em localhost e X-API-Key na LAN.
   * Retorna handle compativel com .close() / .abort().
   */
  subscribeProactiveStream(onAlertCallback, filialId = null) {
    const query = filialId ? `?filial_id=${encodeURIComponent(filialId)}` : '';
    const path = `/api/v1/aura/proactive/stream${query}`;

    let closed = false;
    let activeController = null;
    let reconnectTimer = null;
    let attempt = 0;
    const backoffDelays = [1000, 2000, 5000, 15000];

    const handle = {
      readyState: 0, // 0=CONNECTING, 1=OPEN, 2=CLOSED
      close() {
        closed = true;
        this.readyState = 2;
        if (reconnectTimer) {
          clearTimeout(reconnectTimer);
          reconnectTimer = null;
        }
        if (activeController) {
          try { activeController.abort(); } catch (_) {}
          activeController = null;
        }
      },
      abort() {
        this.close();
      },
    };

    const scheduleReconnect = () => {
      if (closed) return;
      const delay = backoffDelays[Math.min(attempt, backoffDelays.length - 1)];
      attempt += 1;
      reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        if (closed) return;
        if (typeof document !== 'undefined' && document.hidden) {
          scheduleReconnect();
          return;
        }
        connect();
      }, delay);
    };

    const connect = async () => {
      if (closed) return;
      handle.readyState = 0;
      activeController = typeof AbortController !== 'undefined' ? new AbortController() : null;

      try {
        await this.transport.streamSse(path, {
          method: 'GET',
          signal: activeController ? activeController.signal : undefined,
          _skipAuthRecovery: false,
          onOpen: () => {
            attempt = 0;
            handle.readyState = 1;
          },
          onEvent: (eventCategory, rawDataStr) => {
            if (!rawDataStr || rawDataStr === '[DONE]') return;
            try {
              const payload = JSON.parse(rawDataStr);
              const isProactive =
                eventCategory === 'proactive_alert' ||
                (payload && (payload.chunk_type === 'proactive_alert' || payload.event === 'proactive_alert'));
              if (isProactive) {
                const alertData = (payload && payload.data) || payload;
                if (typeof onAlertCallback === 'function') {
                  onAlertCallback(alertData, payload);
                }
                if (typeof window !== 'undefined' && window.auraChat && typeof window.auraChat.handleProactiveAlert === 'function') {
                  window.auraChat.handleProactiveAlert(alertData);
                }
              }
            } catch (_) {
              // Ignora heartbeats ou payloads nao JSON
            }
          },
        });
        if (!closed) {
          scheduleReconnect();
        }
      } catch (err) {
        if (closed || (err && err.name === 'AbortError')) return;
        if (err && err.status === 401) {
          // Nao entra em loop infinito de 401 se o usuario cancelou o pareamento LAN
          handle.readyState = 2;
          return;
        }
        scheduleReconnect();
      }
    };

    connect();
    return handle;
  }
}

// 1. Exportacao Global no Navegador (Window)
if (typeof window !== 'undefined') {
  window.AuraLanAuthModal = AuraLanAuthModal;
  window.AuraHttpTransport = AuraHttpTransport;
  window.AuraApiClient = AuraApiClient;
  window.auraApi = new AuraApiClient();
  window.auraTransport = window.auraApi.transport;
}

// 2. Exportacao CommonJS para testes headless e automacao (Node.js)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    AuraApiClient,
    AuraApi: AuraApiClient,
    AuraHttpTransport,
    AuraLanAuthModal,
  };
}
