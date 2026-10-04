/**
 * AURA Core Engine API Client
 * Comunicação direta com a API FastAPI local (/api/v1/aura)
 * Suporte a Server-Sent Events (SSE) via POST stream, execução de intenções e suporte analítico sob demanda.
 */

class AuraApiClient {
  constructor(baseUrl = '') {
    this.baseUrl = baseUrl.replace(/\/$/, '');
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
   * Streaming conversacional com a AURA via Server-Sent Events (SSE)
   * Processa chunks em tempo real: delta, intent, tool_start, tool_result, telemetry, done
   */
  async chatStream({
    query,
    sessionId = null,
    context = null,
    tenantId = null,
    filialId = null,
    onChunk = () => {},
    onDone = () => {},
    onError = () => {},
    signal = null,
  }) {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/aura/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify({
          query: query,
          session_id: sessionId,
          stream: true,
          context: context,
          tenant_id: tenantId,
          filial_id: filialId,
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

      const triggerDone = () => {
        if (!doneNotified) {
          doneNotified = true;
          onDone();
        }
      };

      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          if (buffer.trim()) {
            const remainingLines = buffer.split('\n');
            for (const line of remainingLines) {
              const trimmed = line.trim();
              if (trimmed.startsWith('data:')) {
                const dataStr = trimmed.replace('data:', '').trim();
                if (dataStr === '[DONE]') {
                  triggerDone();
                } else {
                  try {
                    const chunkData = JSON.parse(dataStr);
                    if (chunkData.chunk_type === 'done') {
                      triggerDone();
                    } else {
                      onChunk({ eventType: 'delta', ...chunkData });
                    }
                  } catch (_) {}
                }
              }
            }
          }
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // Mantém o que estiver incompleto

        let currentEvent = 'delta';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) {
            currentEvent = 'delta';
            continue;
          }

          if (trimmed.startsWith('event:')) {
            currentEvent = trimmed.replace('event:', '').trim();
          } else if (trimmed.startsWith('data:')) {
            const dataStr = trimmed.replace('data:', '').trim();
            if (dataStr === '[DONE]') {
              triggerDone();
              continue;
            }

            try {
              const chunkData = JSON.parse(dataStr);
              if (chunkData.chunk_type === 'done' || currentEvent === 'done') {
                triggerDone();
              } else {
                onChunk({
                  eventType: currentEvent,
                  ...chunkData,
                });
              }
            } catch (err) {
              console.warn('[AuraAPI] Falha ao decodificar chunk JSON:', dataStr, err);
            }
          }
        }
      }

      triggerDone();
    } catch (err) {
      if (err.name === 'AbortError') {
        console.log('[AuraAPI] Streaming abortado pelo usuário.');
      } else {
        onError(err);
      }
    }
  }
}

// Instância singleton global
window.auraApi = new AuraApiClient();
