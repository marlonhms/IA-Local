/**
 * Cliente HTTP e SSE Fortemente Tipado para o Motor Cognitivo AURA (P0-UI1/P0-UI2/P0-UI3).
 * Centraliza 100% das chamadas no AuraHttpTransport com credentials: "include",
 * bootstrap silencioso de sessao local em 401, suporte a X-API-Key na LAN,
 * streaming SSE via fetch (zero EventSource nativo) e tratamento de stream_reset.
 * Zero travessoes em todo o arquivo.
 */

import type {
  ActionExecuteRequest,
  ActionVoucher,
  ActionableDirectivePayload,
  ComplianceVerificationResult,
  ExecutiveExceptionCard,
  GenUIEnvelope,
  GenUIEvent,
  LiveSecurityTelemetry,
  TelemetrySLISnapshot,
} from "../types/aura-contracts";

export interface AuraTransportConfig {
  baseUrl?: string;
  apiKey?: string;
  operatorRole?: "frentista" | "caixa" | "gerente" | "administrador";
  onLanAuthRequired?: (reason?: string) => Promise<string | null>;
}

export interface AuraClientConfig extends AuraTransportConfig {
  operatorId?: string;
}

export interface AuraStreamHandle {
  close: () => void;
  abort: () => void;
  done: Promise<void>;
}

export interface AuraStreamChatOptions {
  signal?: AbortSignal;
  onStreamReset?: (event: GenUIEvent) => void;
  useLegacyGetEndpoint?: boolean;
}

const LOOPBACK_HOSTS = new Set(["127.0.0.1", "localhost", "::1", "[::1]"]);
const API_KEY_STORAGE_KEY = "aura_lan_api_key";

export function isValidGenUIEnvelope(payload: unknown): payload is GenUIEnvelope {
  if (typeof payload !== "object" || payload === null) {
    return false;
  }
  const obj = payload as Record<string, unknown>;
  return (
    typeof obj.tool_call_id === "string" &&
    typeof obj.component_name === "string" &&
    typeof obj.executive_summary === "string" &&
    typeof obj.props === "object" &&
    obj.props !== null &&
    Array.isArray(obj.actions)
  );
}

export function isValidActionVoucher(payload: unknown): payload is ActionVoucher {
  if (typeof payload !== "object" || payload === null) {
    return false;
  }
  const obj = payload as Record<string, unknown>;
  return (
    typeof obj.voucher_id === "string" &&
    typeof obj.action_id === "string" &&
    typeof obj.tool_call_id === "string" &&
    (obj.status === "APPROVED" || obj.status === "EXECUTED") &&
    typeof obj.signature === "string"
  );
}

export class AuraHttpTransport {
  private readonly baseUrl: string;
  private apiKey?: string;
  private readonly operatorRole: "frentista" | "caixa" | "gerente" | "administrador";
  private readonly onLanAuthRequired?: (reason?: string) => Promise<string | null>;
  private bootstrapPromise: Promise<boolean> | null = null;

  constructor(config: AuraTransportConfig = {}) {
    this.baseUrl = this.normalizeBaseUrl(config.baseUrl ?? "");
    this.apiKey = config.apiKey;
    this.operatorRole = config.operatorRole ?? "gerente";
    this.onLanAuthRequired = config.onLanAuthRequired;
  }

  private normalizeBaseUrl(rawBaseUrl: string): string {
    const trimmed = rawBaseUrl.replace(/\/+$/, "");
    if (!trimmed) {
      return "";
    }
    if (typeof window !== "undefined" && window.location && window.location.hostname) {
      try {
        const parsed = new URL(trimmed);
        if (LOOPBACK_HOSTS.has(parsed.hostname) && LOOPBACK_HOSTS.has(window.location.hostname)) {
          if (parsed.port === window.location.port || !parsed.port) {
            return "";
          }
        }
      } catch {
        return trimmed;
      }
    }
    return trimmed;
  }

  public isLocalOrigin(): boolean {
    if (typeof window === "undefined" || !window.location) {
      return true;
    }
    return LOOPBACK_HOSTS.has(window.location.hostname);
  }

  public getApiKey(): string {
    if (this.apiKey) {
      return this.apiKey;
    }
    if (typeof window !== "undefined") {
      try {
        const fromSession = window.sessionStorage?.getItem(API_KEY_STORAGE_KEY);
        if (fromSession) return fromSession;
        const fromLocal = window.localStorage?.getItem(API_KEY_STORAGE_KEY);
        if (fromLocal) return fromLocal;
      } catch {
        // Ignora ambientes sem storage
      }
    }
    return "";
  }

  public setApiKey(key: string): void {
    this.apiKey = key.trim();
  }

  public resolveUrl(path: string): string {
    if (/^https?:\/\//i.test(path)) {
      return path;
    }
    const normalizedPath = path.startsWith("/") ? path : `/${path}`;
    return `${this.baseUrl}${normalizedPath}`;
  }

  public buildHeaders(extra: Record<string, string> = {}, includeJsonContentType = true): Record<string, string> {
    const headers: Record<string, string> = {
      "X-Operator-Role": this.operatorRole,
      ...extra,
    };
    if (includeJsonContentType && !headers["Content-Type"] && !headers["content-type"]) {
      headers["Content-Type"] = "application/json";
    }
    const key = this.getApiKey();
    if (key && !headers["X-API-Key"]) {
      headers["X-API-Key"] = key;
    }
    return headers;
  }

  public async ensureLocalSessionBootstrap(): Promise<boolean> {
    if (this.bootstrapPromise) {
      return this.bootstrapPromise;
    }
    this.bootstrapPromise = (async () => {
      try {
        const resp = await fetch(this.resolveUrl("/"), {
          method: "GET",
          credentials: "include",
          cache: "no-store",
        });
        return resp.ok;
      } catch {
        return false;
      } finally {
        this.bootstrapPromise = null;
      }
    })();
    return this.bootstrapPromise;
  }

  public async request(
    path: string,
    init: RequestInit = {},
    options: { includeJsonContentType?: boolean; retryOn401?: boolean } = {},
  ): Promise<Response> {
    const includeJson = options.includeJsonContentType ?? true;
    const retryOn401 = options.retryOn401 ?? true;

    const executeFetch = async (): Promise<Response> => {
      const extraHeaders = (init.headers && !(init.headers instanceof Headers) && !Array.isArray(init.headers))
        ? (init.headers as Record<string, string>)
        : {};
      const headers = this.buildHeaders(extraHeaders, includeJson);
      return fetch(this.resolveUrl(path), {
        ...init,
        headers,
        credentials: "include",
      });
    };

    let response = await executeFetch();

    if (response.status === 401 && retryOn401) {
      if (this.isLocalOrigin()) {
        const ok = await this.ensureLocalSessionBootstrap();
        if (ok) {
          response = await executeFetch();
        }
      } else if (this.onLanAuthRequired) {
        const newKey = await this.onLanAuthRequired("Sessao nao autorizada na rede local.");
        if (newKey) {
          this.setApiKey(newKey);
          response = await executeFetch();
        }
      }
    }

    return response;
  }

  public async streamSse(
    path: string,
    init: RequestInit,
    onEvent: (event: GenUIEvent) => void,
    options: { onStreamReset?: (event: GenUIEvent) => void } = {},
  ): Promise<void> {
    const extraHeaders = (init.headers && !(init.headers instanceof Headers) && !Array.isArray(init.headers))
      ? (init.headers as Record<string, string>)
      : {};

    const response = await this.request(
      path,
      {
        ...init,
        headers: {
          Accept: "text/event-stream",
          ...extraHeaders,
        },
      },
      { includeJsonContentType: init.method === "POST", retryOn401: true },
    );

    if (!response.ok) {
      const errorText = await response.text().catch(() => "");
      throw new Error(`Falha na conexao SSE (${response.status}): ${errorText}`);
    }

    if (!response.body) {
      throw new Error("Stream SSE sem corpo legivel (ReadableStream ausente).");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    const dispatchBlock = (rawBlock: string): void => {
      const lines = rawBlock.split(/\r?\n/);
      let eventType = "";
      const dataLines: string[] = [];

      for (const line of lines) {
        if (!line || line.startsWith(":")) {
          continue;
        }
        if (line.startsWith("event:")) {
          eventType = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          dataLines.push(line.slice(5).trimStart());
        }
      }

      if (dataLines.length === 0) {
        return;
      }

      const dataStr = dataLines.join("\n").trim();
      if (!dataStr || dataStr === "[DONE]") {
        return;
      }

      let parsed: GenUIEvent;
      try {
        parsed = JSON.parse(dataStr) as GenUIEvent;
      } catch {
        parsed = {
          chunk_type: (eventType as GenUIEvent["chunk_type"]) || "delta",
          text: dataStr,
        };
      }

      if (eventType && !parsed.chunk_type) {
        parsed.chunk_type = eventType as GenUIEvent["chunk_type"];
      }

      if (parsed.chunk_type === "stream_reset" && options.onStreamReset) {
        options.onStreamReset(parsed);
      }

      onEvent(parsed);
    };

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          break;
        }
        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split(/\r?\n\r?\n/);
        buffer = blocks.pop() ?? "";
        for (const block of blocks) {
          if (block.trim()) {
            dispatchBlock(block);
          }
        }
      }

      buffer += decoder.decode();
      if (buffer.trim()) {
        dispatchBlock(buffer);
      }
    } finally {
      reader.releaseLock();
    }
  }
}

export class AuraApiClient {
  public readonly transport: AuraHttpTransport;
  private readonly operatorId: string;
  private readonly operatorRole: "frentista" | "caixa" | "gerente" | "administrador";

  constructor(config: AuraClientConfig = {}) {
    this.operatorId = config.operatorId ?? "operador_01";
    this.operatorRole = config.operatorRole ?? "gerente";
    this.transport = new AuraHttpTransport({
      baseUrl: config.baseUrl,
      apiKey: config.apiKey,
      operatorRole: this.operatorRole,
      onLanAuthRequired: config.onLanAuthRequired,
    });
  }

  public async executeAction(request: ActionExecuteRequest): Promise<ActionVoucher> {
    const payload: ActionExecuteRequest = {
      ...request,
      operator_id: request.operator_id ?? this.operatorId,
      operator_role: request.operator_role ?? this.operatorRole,
    };

    const response = await this.transport.request("/api/v1/aura/actions/execute", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Falha ao executar acao (${response.status}): ${errorText}`);
    }

    const data: unknown = await response.json();
    if (!isValidActionVoucher(data)) {
      throw new Error("Contrato invalido: resposta nao corresponde a ActionVoucher");
    }
    return data;
  }

  public async getComplianceStatus(cnpj?: string): Promise<ComplianceVerificationResult> {
    const query = cnpj ? `?cnpj=${encodeURIComponent(cnpj)}` : "";
    const response = await this.transport.request(`/api/v1/aura/compliance/status${query}`, {
      method: "GET",
    });

    if (!response.ok) {
      throw new Error(`Falha ao consultar conformidade (${response.status})`);
    }
    return (await response.json()) as ComplianceVerificationResult;
  }

  public async getTelemetryMetrics(): Promise<TelemetrySLISnapshot> {
    const response = await this.transport.request("/api/v1/aura/telemetry/metrics", {
      method: "GET",
    });

    if (!response.ok) {
      throw new Error(`Falha ao consultar telemetria SRE (${response.status})`);
    }
    return (await response.json()) as TelemetrySLISnapshot;
  }

  public async getPrometheusMetrics(): Promise<string> {
    const response = await this.transport.request(
      "/metrics",
      { method: "GET" },
      { includeJsonContentType: false },
    );

    if (!response.ok) {
      throw new Error(`Falha ao consultar /metrics Prometheus (${response.status})`);
    }
    return await response.text();
  }

  public streamChat(
    query: string,
    sessionId: string,
    onEvent: (event: GenUIEvent) => void,
    onError?: (err: Error) => void,
    options: AuraStreamChatOptions = {},
  ): AuraStreamHandle {
    const controller = new AbortController();

    if (options.signal) {
      if (options.signal.aborted) {
        controller.abort();
      } else {
        options.signal.addEventListener("abort", () => controller.abort(), { once: true });
      }
    }

    let path: string;
    let init: RequestInit;

    if (options.useLegacyGetEndpoint) {
      const params = new URLSearchParams({
        query,
        session_id: sessionId,
        genui: "1",
      });
      path = `/api/v1/aura/chat/stream?${params.toString()}`;
      init = {
        method: "GET",
        signal: controller.signal,
      };
    } else {
      path = "/api/v1/aura/chat";
      init = {
        method: "POST",
        signal: controller.signal,
        body: JSON.stringify({
          query,
          session_id: sessionId,
          stream: true,
        }),
      };
    }

    const done = this.transport
      .streamSse(path, init, onEvent, { onStreamReset: options.onStreamReset })
      .catch((err: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        if (onError) {
          onError(err instanceof Error ? err : new Error(String(err)));
        }
      });

    return {
      close: () => controller.abort(),
      abort: () => controller.abort(),
      done,
    };
  }

  public async getZeroClickFeed(
    tenantId = "default",
    limit = 5,
    forceRefresh = false,
  ): Promise<ExecutiveExceptionCard[]> {
    const params = new URLSearchParams({
      tenant_id: tenantId,
      limit: String(limit),
      force_refresh: forceRefresh ? "true" : "false",
    });
    const response = await this.transport.request(
      `/api/v1/cockpit/zero-click-feed?${params.toString()}`,
      { method: "GET" },
    );

    if (!response.ok) {
      throw new Error(`Falha ao consultar Feed Zero-Click (${response.status})`);
    }
    const data = (await response.json()) as { cards?: ExecutiveExceptionCard[] };
    return data.cards ?? [];
  }

  public async getLiveSecurityTelemetry(): Promise<LiveSecurityTelemetry> {
    const response = await this.transport.request("/api/v1/aura/security/telemetry", {
      method: "GET",
    });

    if (!response.ok) {
      throw new Error(`Falha ao consultar telemetria de seguranca (${response.status})`);
    }
    return (await response.json()) as LiveSecurityTelemetry;
  }

  public async dispatchActionableDirective(
    directive: ActionableDirectivePayload,
    destinationUrl?: string,
  ): Promise<{ success: boolean; directive_id: string; outbox_message_id: string; status: string }> {
    const response = await this.transport.request("/api/v1/aura/directives/dispatch", {
      method: "POST",
      body: JSON.stringify({
        ...directive,
        destination_url: destinationUrl,
        operator_id: this.operatorId ?? "gerente_01",
      }),
    });

    if (!response.ok) {
      throw new Error(`Falha ao despachar diretiva de acao na outbox (${response.status})`);
    }
    return (await response.json()) as {
      success: boolean;
      directive_id: string;
      outbox_message_id: string;
      status: string;
    };
  }

  public async getRecentDirectives(limit = 20): Promise<ActionableDirectivePayload[]> {
    const response = await this.transport.request(`/api/v1/aura/directives/recent?limit=${limit}`, {
      method: "GET",
    });

    if (!response.ok) {
      throw new Error(`Falha ao listar diretivas recentes (${response.status})`);
    }
    const data = (await response.json()) as { directives?: ActionableDirectivePayload[] };
    return data.directives ?? [];
  }
}
