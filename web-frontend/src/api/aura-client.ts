/**
 * Cliente HTTP e SSE Fortemente Tipado para o Motor Cognitivo AURA (P2-6).
 * Implementa validacao de contratos em runtime e integracao com rotas REST/SSE.
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

export interface AuraClientConfig {
  baseUrl?: string;
  apiKey?: string;
  operatorId?: string;
  operatorRole?: "frentista" | "caixa" | "gerente" | "administrador";
}

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

export class AuraApiClient {
  private readonly baseUrl: string;
  private readonly apiKey?: string;
  private readonly operatorId: string;
  private readonly operatorRole: "frentista" | "caixa" | "gerente" | "administrador";

  constructor(config: AuraClientConfig = {}) {
    this.baseUrl = (config.baseUrl ?? "").replace(/\/+$/, "");
    this.apiKey = config.apiKey;
    this.operatorId = config.operatorId ?? "operador_01";
    this.operatorRole = config.operatorRole ?? "gerente";
  }

  private buildHeaders(extra: Record<string, string> = {}): Record<string, string> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "X-Operator-Role": this.operatorRole,
      ...extra,
    };
    if (this.apiKey) {
      headers["X-API-Key"] = this.apiKey;
    }
    return headers;
  }

  public async executeAction(request: ActionExecuteRequest): Promise<ActionVoucher> {
    const payload: ActionExecuteRequest = {
      ...request,
      operator_id: request.operator_id ?? this.operatorId,
      operator_role: request.operator_role ?? this.operatorRole,
    };

    const response = await fetch(`${this.baseUrl}/api/v1/aura/actions/execute`, {
      method: "POST",
      headers: this.buildHeaders(),
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
    const response = await fetch(`${this.baseUrl}/api/v1/aura/compliance/status${query}`, {
      method: "GET",
      headers: this.buildHeaders(),
    });

    if (!response.ok) {
      throw new Error(`Falha ao consultar conformidade (${response.status})`);
    }
    return (await response.json()) as ComplianceVerificationResult;
  }

  public async getTelemetryMetrics(): Promise<TelemetrySLISnapshot> {
    const response = await fetch(`${this.baseUrl}/api/v1/aura/telemetry/metrics`, {
      method: "GET",
      headers: this.buildHeaders(),
    });

    if (!response.ok) {
      throw new Error(`Falha ao consultar telemetria SRE (${response.status})`);
    }
    return (await response.json()) as TelemetrySLISnapshot;
  }

  public async getPrometheusMetrics(): Promise<string> {
    const response = await fetch(`${this.baseUrl}/metrics`, {
      method: "GET",
    });

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
  ): EventSource {
    const params = new URLSearchParams({
      query,
      session_id: sessionId,
      genui: "1",
    });
    const url = `${this.baseUrl}/api/v1/aura/chat/stream?${params.toString()}`;
    const source = new EventSource(url);

    source.onmessage = (msg: MessageEvent<string>) => {
      try {
        const parsed = JSON.parse(msg.data) as GenUIEvent;
        onEvent(parsed);
      } catch (err) {
        if (onError) {
          onError(err instanceof Error ? err : new Error(String(err)));
        }
      }
    };

    source.onerror = () => {
      if (onError) {
        onError(new Error("Erro na conexao de streaming SSE com a AURA"));
      }
    };

    return source;
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
    const response = await fetch(`${this.baseUrl}/api/v1/cockpit/zero-click-feed?${params.toString()}`, {
      method: "GET",
      headers: this.buildHeaders(),
    });

    if (!response.ok) {
      throw new Error(`Falha ao consultar Feed Zero-Click (${response.status})`);
    }
    const data = (await response.json()) as { cards?: ExecutiveExceptionCard[] };
    return data.cards ?? [];
  }

  public async getLiveSecurityTelemetry(): Promise<LiveSecurityTelemetry> {
    const response = await fetch(`${this.baseUrl}/api/v1/aura/security/telemetry`, {
      method: "GET",
      headers: this.buildHeaders(),
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
    const response = await fetch(`${this.baseUrl}/api/v1/aura/directives/dispatch`, {
      method: "POST",
      headers: this.buildHeaders(),
      body: JSON.stringify({
        ...directive,
        destination_url: destinationUrl,
        operator_id: this.config.operatorId ?? "gerente_01",
      }),
    });

    if (!response.ok) {
      throw new Error(`Falha ao despachar diretiva de acao na outbox (${response.status})`);
    }
    return (await response.json()) as { success: boolean; directive_id: string; outbox_message_id: string; status: string };
  }

  public async getRecentDirectives(limit = 20): Promise<ActionableDirectivePayload[]> {
    const response = await fetch(`${this.baseUrl}/api/v1/aura/directives/recent?limit=${limit}`, {
      method: "GET",
      headers: this.buildHeaders(),
    });

    if (!response.ok) {
      throw new Error(`Falha ao listar diretivas recentes (${response.status})`);
    }
    const data = (await response.json()) as { directives?: ActionableDirectivePayload[] };
    return data.directives ?? [];
  }
}

