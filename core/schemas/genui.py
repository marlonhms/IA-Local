"""
Módulo de Envelopes Canônicos GenUI / SDUI da AURA.
Define contratos Pydantic v2 para micro-widgets de 3 camadas:
- Camada 1: Resumo Executivo (executive_summary)
- Camada 2: Visualização Rica (props determinísticas)
- Camada 3: Action Sheets Transacionais (actions tipadas com idempotência)
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator, AliasChoices

from core.schemas.idempotency import (
    validate_tool_call_id,
    validate_action_id,
    generate_tool_call_id,
    generate_action_id,
)

# Regex para nomes seguros de componentes no SecureComponentRegistry
# Permite PascalCase, camelCase, snake_case ou kebab-case iniciando com letra (3 a 128 chars)
SAFE_COMPONENT_NAME_REGEX = re.compile(r"^[a-zA-Z][a-zA-Z0-9_\-]{2,127}$")


class GenUIActionOption(BaseModel):
    """Opção de ação transacional na Camada 3 de um micro-widget GenUI."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    action_id: str = Field(..., description="UUID único da ação transacional (RFC 4122 v4 com prefixo act_)")
    label: str = Field(..., description="Rótulo visual do botão de ação")
    action_type: Literal["mutation", "inspection", "navigation"] = Field(
        default="mutation",
        description="Tipo da ação: mutação transacional, inspeção em painel ou navegação"
    )
    variant: Literal["primary", "secondary", "danger", "ghost"] = Field(
        default="primary",
        description="Variante visual de destaque do botão"
    )
    is_destructive: bool = Field(
        default=False,
        description="Indica se a ação é irreversível ou de alto impacto financeiro"
    )
    requires_confirmation: bool = Field(
        default=True,
        description="Indica se a ação exige modal ou confirmação prévia do operador"
    )
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Carga útil imutável para despacho no Human-in-the-Loop Gateway"
    )

    @field_validator("action_id")
    @classmethod
    def check_action_id(cls, v: str) -> str:
        if not validate_action_id(v):
            raise ValueError(f"action_id inválido: '{v}' não é um UUID v4 válido ou possui prefixo incompatível")
        return v

    @field_validator("label")
    @classmethod
    def check_label(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("label não pode ser vazio")
        return v.strip()


class ExecutiveMetric(BaseModel):
    """Métrica executiva analítica individual com benchmark e tendência."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    label: str = Field(..., description="Rótulo da métrica (ex: Margem Líquida Real)")
    current_value: Any = Field(..., description="Valor atual apurado")
    benchmark_value: Optional[Any] = Field(default=None, description="Valor de benchmark ou meta histórica")
    trend: Literal["up", "down", "neutral"] = Field(
        default="neutral",
        description="Tendência do indicador: up, down ou neutral"
    )
    status: Literal["success", "warning", "danger", "neutral"] = Field(
        default="neutral",
        description="Classificação semântica de status"
    )
    unit: Optional[str] = Field(default=None, description="Unidade de medida (%, R$, L, etc.)")
    delta_percent: Optional[float] = Field(default=None, description="Variação percentual calculada")

    @field_validator("label")
    @classmethod
    def check_label(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("label não pode ser vazio")
        return v.strip()


class ExecutiveImpactProjection(BaseModel):
    """Projeção de impacto financeiro ou operacional estimado."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    summary: str = Field(..., description="Resumo descritivo da projeção")
    estimated_financial_impact: Optional[float] = Field(
        default=None,
        description="Impacto financeiro estimado em R$ (positivo = ganho, negativo = perda)"
    )
    timeframe: Optional[str] = Field(default=None, description="Janela temporal estimada (ex: 24h, 7 dias, mensal)")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Confiança na projeção (0.0 a 1.0)")


class ExecutiveEvidenceItem(BaseModel):
    """Item de evidência analítica para aprofundamento no Companion Canvas."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    title: str = Field(..., description="Título da evidência ou fonte")
    detail: str = Field(..., description="Detalhamento técnico ou contábil")
    value: Optional[Any] = Field(default=None, description="Valor apurado")
    source: Optional[str] = Field(default=None, description="Tabela ou sensor de origem")


class ExecutiveDecisionProps(BaseModel):
    """Propriedades determinísticas do Micro-Widget Piloto ExecutiveDecisionMentorUI (Camada 2)."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    diagnosis: str = Field(..., description="Diagnóstico conciso e direto sem ruído gerativo")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Score de confiança na recomendação (0.0 a 1.0)")
    metrics: List[ExecutiveMetric] = Field(default_factory=list, description="Lista de métricas executivas comparativas")
    limitations: List[str] = Field(
        default_factory=list,
        description="Avisos sobre limitações dos dados (ex: dados sem conciliação bancária)"
    )
    impact_projection: Optional[Union[str, Dict[str, Any], ExecutiveImpactProjection]] = Field(
        default=None,
        description="Texto ou estrutura com projeção financeira ou operacional estimada"
    )
    evidence_items: List[Union[str, Dict[str, Any], ExecutiveEvidenceItem]] = Field(
        default_factory=list,
        description="Lista de evidências para aprofundamento analítico"
    )
    suggested_actions: List[GenUIActionOption] = Field(
        default_factory=list,
        description="Opções de ação imediata em 1 toque na interface"
    )

    @field_validator("diagnosis")
    @classmethod
    def check_diagnosis(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("diagnosis não pode ser vazio")
        return v.strip()

    @field_validator("limitations", mode="before")
    @classmethod
    def normalize_limitations(cls, v: Any) -> List[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v.strip()] if v.strip() else []
        if isinstance(v, (list, tuple)):
            res = []
            for item in v:
                if isinstance(item, str) and item.strip():
                    res.append(item.strip())
                elif item is not None:
                    res.append(str(item).strip())
            return res
        return [str(v)]


class GenUIEnvelope(BaseModel):
    """Envelope canônico universal para componentes Server-Driven UI no AURA IntelligentUI."""
    model_config = ConfigDict(frozen=True, extra="ignore", populate_by_name=True)

    schema_version: str = Field(
        default="1.0",
        validation_alias=AliasChoices("schema_version", "envelope_version"),
        description="Versão do schema do envelope GenUI"
    )
    tool_call_id: str = Field(..., description="UUID da invocação gerada pelo backend (RFC 4122 v4)")
    component_name: str = Field(..., description="Nome do componente registrado no SecureComponentRegistry")
    client_component: Optional[str] = Field(default=None, description="Nome da classe construtora no frontend")
    intent: str = Field(
        default="",
        validation_alias=AliasChoices("intent", "component_name"),
        description="Intenção canônica classificada (ex: previsao_tanques)"
    )
    executive_summary: str = Field(
        ...,
        validation_alias=AliasChoices("executive_summary", "summary_text"),
        description="Camada 1: Resumo Executivo em texto puro"
    )
    props: Dict[str, Any] = Field(..., description="Camada 2: Propriedades puras do widget calculadas pelo Python")
    actions: List[GenUIActionOption] = Field(default_factory=list, description="Camada 3: Action Sheets com botões de ação")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        validation_alias=AliasChoices("created_at", "timestamp"),
        description="Timestamp ISO da criação do envelope"
    )
    ttl_seconds: int = Field(default=900, description="Tempo de vida útil (TTL) da proposta de ação na interface")

    @field_validator("tool_call_id")
    @classmethod
    def check_tool_call_id(cls, v: str) -> str:
        if not validate_tool_call_id(v):
            raise ValueError(f"tool_call_id inválido: '{v}' não é um UUID v4 válido ou possui prefixo incompatível")
        return v

    @field_validator("component_name")
    @classmethod
    def check_component_name(cls, v: str) -> str:
        if not isinstance(v, str) or not SAFE_COMPONENT_NAME_REGEX.match(v.strip()):
            raise ValueError(f"component_name inválido ou inseguro: '{v}'")
        return v.strip()

    @field_validator("intent", mode="before")
    @classmethod
    def check_intent(cls, v: Any) -> str:
        if v is None:
            return ""
        if isinstance(v, str):
            return v.strip()
        return str(v).strip()

    @field_validator("props", mode="before")
    @classmethod
    def check_props(cls, v: Any) -> Dict[str, Any]:
        if isinstance(v, BaseModel):
            return v.model_dump(mode="json")
        if isinstance(v, dict):
            return v
        raise ValueError("props deve ser um dicionário ou modelo Pydantic")

    @field_validator("ttl_seconds")
    @classmethod
    def check_ttl(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("ttl_seconds deve ser maior que zero")
        return v

    def to_sse_payload(self) -> Dict[str, Any]:
        """Gera payload compatível com a especificação formal de streaming SSE."""
        data = self.model_dump(mode="json")
        # Aliases para compatibilidade integral com docs/protocolo_streaming_genui.md
        data["envelope_version"] = self.schema_version
        data["summary_text"] = self.executive_summary
        data["timestamp"] = self.created_at
        return data

    def to_json(self) -> str:
        """Serializa o envelope para string JSON segura."""
        return self.model_dump_json()


class GenUIActionResult(BaseModel):
    """Envelope de retorno de execução de ações transacionais da Camada 3."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    tool_call_id: str = Field(..., description="UUID da invocação original da ferramenta")
    action_id: str = Field(..., description="UUID da ação transacional executada")
    status: Literal["COMMITTED", "FAILED", "PENDING"] = Field(
        default="COMMITTED",
        description="Status oficial da execução transacional"
    )
    voucher_id: Optional[str] = Field(default=None, description="Identificador único do Action Voucher gerado")
    signature: Optional[str] = Field(default=None, description="Assinatura criptográfica HMAC-SHA256")
    feedback_message: Optional[str] = Field(default=None, description="Mensagem de retorno executivo")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Timestamp ISO da confirmação"
    )

    @field_validator("tool_call_id")
    @classmethod
    def check_tool_call_id(cls, v: str) -> str:
        if not validate_tool_call_id(v):
            raise ValueError(f"tool_call_id inválido: '{v}'")
        return v

    @field_validator("action_id")
    @classmethod
    def check_action_id(cls, v: str) -> str:
        if not validate_action_id(v):
            raise ValueError(f"action_id inválido: '{v}'")
        return v


class WidgetStateRecord(BaseModel):
    """Modelo Pydantic que valida o contrato de estado do cliente (AuraStateManager)."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    tool_call_id: str = Field(..., description="UUID da invocação RFC 4122 v4")
    status: Literal["proposed", "locked", "optimistic", "committed", "failed", "expired"] = Field(
        default="proposed",
        description="Estado do ciclo de vida do micro-widget"
    )
    is_locked: bool = Field(default=False, description="Indicador de bloqueio contra duplo clique")
    locked_action_id: Optional[str] = Field(default=None, description="ID da ação atualmente em execução")
    timestamp: int = Field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000), description="Timestamp em milissegundos")
    ttl_seconds: int = Field(default=900, description="Tempo de vida útil em segundos")
    props: Dict[str, Any] = Field(default_factory=dict, description="Propriedades do widget")
    optimistic_data: Optional[Dict[str, Any]] = Field(default=None, description="Dados da mutação otimista")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Resultado da execução da ação")

    @field_validator("tool_call_id")
    @classmethod
    def check_tool_call_id(cls, v: str) -> str:
        if not validate_tool_call_id(v):
            raise ValueError(f"tool_call_id inválido: '{v}'")
        return v

    def is_stale(self, current_ts_ms: Optional[int] = None) -> bool:
        """Verifica se o estado está expirado pelo TTL."""
        now_ms = current_ts_ms if current_ts_ms is not None else int(datetime.now(timezone.utc).timestamp() * 1000)
        return (now_ms - self.timestamp) > (self.ttl_seconds * 1000)


class WidgetActionExecution(BaseModel):
    """Modelo para requisição e validação de ações transacionais."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    action_id: str = Field(..., description="UUID da ação RFC 4122 v4")
    tool_call_id: str = Field(..., description="UUID da invocação do widget")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Payload de execução")

    @field_validator("action_id")
    @classmethod
    def check_action_id(cls, v: str) -> str:
        if not validate_action_id(v):
            raise ValueError(f"action_id inválido: '{v}'")
        return v

    @field_validator("tool_call_id")
    @classmethod
    def check_tool_call_id(cls, v: str) -> str:
        if not validate_tool_call_id(v):
            raise ValueError(f"tool_call_id inválido: '{v}'")
        return v


class ActionExecuteRequest(BaseModel):
    """Modelo de requisicao para execucao de acoes transacionais (F5-01 / F7-03)."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    session_id: str = Field(default="", description="Identificador da sessao conversacional")
    tool_call_id: str = Field(..., description="UUID v4 da invocacao da ferramenta")
    action_id: str = Field(..., description="UUID v4 da acao transacional a executar")
    action_name: str = Field(default="", description="Nome ou rotulo da acao transacional")
    action_type: Literal["mutation", "inspection", "navigation"] = Field(
        default="mutation",
        description="Tipo da acao transacional"
    )
    payload: Dict[str, Any] = Field(default_factory=dict, description="Carga util da acao transacional")
    operator_id: Optional[str] = Field(default="operador_01", description="Identificador do operador humano")
    operator_role: Optional[str] = Field(default="gerente", description="Perfil ou permissao do operador (frentista, caixa, gerente, administrador)")

    @field_validator("tool_call_id")
    @classmethod
    def check_tool_call_id(cls, v: str) -> str:
        if not validate_tool_call_id(v):
            raise ValueError(f"tool_call_id invalido: '{v}'")
        return v

    @field_validator("action_id")
    @classmethod
    def check_action_id(cls, v: str) -> str:
        if not validate_action_id(v):
            raise ValueError(f"action_id invalido: '{v}'")
        return v

    @field_validator("action_name", mode="before")
    @classmethod
    def check_action_name(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v).strip()

    @field_validator("action_type", mode="before")
    @classmethod
    def check_action_type(cls, v: Any) -> str:
        if v is None:
            return "mutation"
        return str(v).strip().lower()

    @field_validator("operator_role", mode="before")
    @classmethod
    def check_operator_role(cls, v: Any) -> str:
        if v is None:
            return "gerente"
        val = str(v).strip().lower()
        return val if val else "gerente"


class ActionVoucher(BaseModel):
    """Comprovante auditavel de acao transacional homologada no ERP (F5-01)."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    voucher_id: str = Field(..., description="UUID v4 do voucher gerado")
    action_id: str = Field(..., description="UUID v4 da acao transacional executada")
    tool_call_id: str = Field(..., description="UUID v4 da invocacao original")
    status: Literal["APPROVED", "EXECUTED"] = Field(
        default="APPROVED",
        description="Status oficial da transacao homologada"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Timestamp ISO UTC da homologacao"
    )
    action_name: str = Field(..., description="Nome da acao executada")
    details: Dict[str, Any] = Field(default_factory=dict, description="Detalhes e parametros confirmados")
    signature: str = Field(..., description="Assinatura HMAC-SHA256 auditavel")

    @field_validator("action_id")
    @classmethod
    def check_action_id(cls, v: str) -> str:
        if not validate_action_id(v):
            raise ValueError(f"action_id invalido: '{v}'")
        return v

    @field_validator("tool_call_id")
    @classmethod
    def check_tool_call_id(cls, v: str) -> str:
        if not validate_tool_call_id(v):
            raise ValueError(f"tool_call_id invalido: '{v}'")
        return v


class ActionAuditLogRecord(BaseModel):
    """Registro duravel da trilha de auditoria transacional no SQLite (F7-04)."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    audit_id: str = Field(..., description="UUID v4 unico do registro de auditoria")
    timestamp: str = Field(..., description="Timestamp ISO UTC do evento")
    session_id: Optional[str] = Field(default=None, description="Sessao conversacional")
    tool_call_id: str = Field(..., description="UUID v4 da invocacao da ferramenta")
    action_id: str = Field(..., description="UUID v4 da acao transacional")
    action_name: str = Field(..., description="Nome da acao executada ou tentada")
    action_type: str = Field(default="mutation", description="Tipo da acao transacional")
    operator_id: Optional[str] = Field(default="operador_01", description="Identificador do operador humano")
    operator_role: Optional[str] = Field(default="gerente", description="Perfil ou role do operador")
    authorized: bool = Field(default=True, description="Indicador se a acao foi autorizada pelo RBAC")
    status: Literal["APPROVED", "REJECTED_FORBIDDEN", "FAILED"] = Field(
        default="APPROVED",
        description="Status oficial da auditoria"
    )
    details: Dict[str, Any] = Field(default_factory=dict, description="Detalhes complementares ou justificativa")
    client_ip: Optional[str] = Field(default=None, description="Endereco IP do cliente")


def generate_action_voucher_signature(
    voucher_id: str,
    action_id: str,
    tool_call_id: str,
    status: str,
    timestamp: str,
    secret: str = "aura_voucher_hmac_secret_v1"
) -> str:
    """Gera assinatura HMAC-SHA256 para integridade auditavel do Action Voucher."""
    import hmac
    import hashlib
    raw = f"{voucher_id}:{action_id}:{tool_call_id}:{status}:{timestamp}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()


def verify_action_voucher_signature(
    voucher: ActionVoucher,
    secret: str = "aura_voucher_hmac_secret_v1"
) -> bool:
    """Verifica a integridade criptografica da assinatura de um Action Voucher."""
    import hmac
    expected = generate_action_voucher_signature(
        voucher_id=voucher.voucher_id,
        action_id=voucher.action_id,
        tool_call_id=voucher.tool_call_id,
        status=voucher.status,
        timestamp=voucher.timestamp,
        secret=secret,
    )
    return hmac.compare_digest(voucher.signature, expected)


# =============================================================================
# MODELOS DE PROPRIEDADES DA FASE 6: EXPANSAO DO CATALOGO DE MICRO-WIDGETS
# =============================================================================

class FuelMarginItem(BaseModel):
    """Item analítico de margem por combustível ou bico."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    combustivel: str = Field(..., description="Nome do combustível ou identificador do bico")
    volume_litros: float = Field(default=0.0, ge=0.0, description="Volume apurado em litros")
    preco_venda: float = Field(..., ge=0.0, description="Preço de venda unitário em R$")
    custo_aquisicao: float = Field(..., ge=0.0, description="Custo de aquisição unitário em R$")
    margem_liquida_pct: float = Field(..., description="Margem líquida apurada em percentual")
    margem_alvo_pct: Optional[float] = Field(default=None, description="Margem alvo estipulada")
    benchmark_mercado: Optional[float] = Field(default=None, description="Preço médio de mercado na região")
    elasticidade: Optional[str] = Field(default=None, description="Classificação da elasticidade de demanda")


class PaymentFeeImpactItem(BaseModel):
    """Impacto de taxas por modalidade de pagamento na margem real."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    modalidade: str = Field(..., description="Modalidade (Cartão Crédito, Débito, Voucher Frota, PIX, Dinheiro)")
    taxa_media_pct: float = Field(..., ge=0.0, description="Taxa média cobrada pela adquirente (%)")
    volume_financeiro: float = Field(..., ge=0.0, description="Volume financeiro transacionado (R$)")
    desconto_taxas_reais: float = Field(..., ge=0.0, description="Valor total descontado em taxas (R$)")
    impacto_margem_pct: float = Field(default=0.0, description="Impacto na redução da margem líquida (pp)")


class MarginAnalysisProps(BaseModel):
    """Propriedades do Micro-Widget MarginAnalysisUI (Fase 6: F6-01)."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    diagnosis: str = Field(..., description="Diagnóstico executivo de margem e rentabilidade")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Score de confiança na apuração (0.0 a 1.0)")
    consolidated_margin_pct: float = Field(..., description="Margem líquida consolidada real apurada (%)")
    target_margin_pct: Optional[float] = Field(default=None, description="Meta de margem da diretoria (%)")
    gross_revenue: Optional[float] = Field(default=None, description="Faturamento bruto apurado em R$")
    net_profit: Optional[float] = Field(default=None, description="Lucro líquido estimado em R$")
    fuel_margins: List[FuelMarginItem] = Field(default_factory=list, description="Detalhamento por combustível")
    payment_fee_impact: List[PaymentFeeImpactItem] = Field(default_factory=list, description="Impacto de taxas financeiras")
    elasticity_projection: Optional[Union[str, Dict[str, Any], ExecutiveImpactProjection]] = Field(
        default=None,
        description="Projeção de impacto ou elasticidade de repasse"
    )
    limitations: List[str] = Field(default_factory=list, description="Avisos sobre limitações dos dados contábeis")
    suggested_actions: List[GenUIActionOption] = Field(default_factory=list, description="Ações transacionais de 1 toque")

    @field_validator("diagnosis")
    @classmethod
    def check_diagnosis(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("diagnosis não pode ser vazio")
        return v.strip()

    @field_validator("limitations", mode="before")
    @classmethod
    def normalize_limitations(cls, v: Any) -> List[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v.strip()] if v.strip() else []
        if isinstance(v, (list, tuple)):
            res = []
            for item in v:
                if isinstance(item, str) and item.strip():
                    res.append(item.strip())
                elif item is not None:
                    res.append(str(item).strip())
            return res
        return [str(v)]


class ScenarioPoint(BaseModel):
    """Ponto de métricas financeiras de um cenário preditivo."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    preco_medio: float = Field(..., ge=0.0, description="Preço médio praticado em R$")
    volume_projetado: float = Field(..., ge=0.0, description="Volume projetado em litros")
    receita_liquida: float = Field(..., description="Receita líquida projetada em R$")
    margem_contribuicao_pct: float = Field(..., description="Margem de contribuição percentual (%)")


class PredictiveScenarioProps(BaseModel):
    """Propriedades do Micro-Widget PredictiveScenarioUI (Fase 6: F6-01)."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    scenario_title: str = Field(..., description="Título do estudo ou cenário simulado")
    hypothesis: str = Field(..., description="Hipótese testada (ex: Aumento de 3% no frete da distribuidora)")
    base_scenario: ScenarioPoint = Field(..., description="Cenário base atual da operação")
    simulated_scenario: ScenarioPoint = Field(..., description="Cenário projetado com a hipótese aplicada")
    delta_volume_pct: float = Field(..., description="Variação esperada no volume (%)")
    delta_revenue: float = Field(..., description="Impacto projetado na receita líquida em R$")
    delta_margin_pct: float = Field(..., description="Variação na margem percentual (pp)")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Score de confiança do modelo estatístico (0.0 a 1.0)")
    diagnosis: str = Field(..., description="Diagnóstico preditivo e recomendação do mentor")
    elasticity_coefficient: Optional[float] = Field(default=None, description="Coeficiente de elasticidade de preço da demanda")
    assumptions: List[str] = Field(default_factory=list, description="Premissas adotadas na simulação")
    limitations: List[str] = Field(default_factory=list, description="Limitações da projeção preditiva")
    suggested_actions: List[GenUIActionOption] = Field(default_factory=list, description="Ações executivas recomendadas")

    @field_validator("scenario_title", "hypothesis", "diagnosis")
    @classmethod
    def check_non_empty(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("Campo textual obrigatório não pode ser vazio")
        return v.strip()

    @field_validator("limitations", "assumptions", mode="before")
    @classmethod
    def normalize_str_lists(cls, v: Any) -> List[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v.strip()] if v.strip() else []
        if isinstance(v, (list, tuple)):
            res = []
            for item in v:
                if isinstance(item, str) and item.strip():
                    res.append(item.strip())
                elif item is not None:
                    res.append(str(item).strip())
            return res
        return [str(v)]


class BenchmarkComparisonItem(BaseModel):
    """Métrica comparativa individual entre a filial e a concorrência/rede."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    kpi_name: str = Field(..., description="Nome do indicador (ex: Preço Gasolina Comum, Conversão Aditivada)")
    filial_value: Any = Field(..., description="Valor apurado na filial")
    benchmark_value: Any = Field(..., description="Valor de referência do concorrente ou média da rede")
    gap_value: Optional[str] = Field(default=None, description="Diferença ou delta formatado")
    status: Literal["success", "warning", "danger", "neutral"] = Field(
        default="neutral",
        description="Classificação da competitividade da filial"
    )
    observation: Optional[str] = Field(default=None, description="Comentário analítico sobre a métrica")


class BenchmarkComparisonProps(BaseModel):
    """Propriedades do Micro-Widget BenchmarkComparisonUI (Fase 6: F6-01)."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    diagnosis: str = Field(..., description="Diagnóstico comparativo de posicionamento competitivo")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confiança na amostragem (0.0 a 1.0)")
    competitiveness_score: float = Field(..., ge=0.0, le=100.0, description="Score de competitividade global (0 a 100)")
    entity_name: str = Field(..., description="Nome da filial sob análise")
    benchmark_group: str = Field(..., description="Grupo de comparação (ex: Concorrentes Raio 3km, Média da Rede)")
    market_position: Optional[str] = Field(default=None, description="Posicionamento no ranking (ex: 2º de 8 postos)")
    comparison_items: List[BenchmarkComparisonItem] = Field(default_factory=list, description="Lista de indicadores comparados")
    limitations: List[str] = Field(default_factory=list, description="Limitações da coleta de dados de concorrentes")
    suggested_actions: List[GenUIActionOption] = Field(default_factory=list, description="Ações táticas de ajuste")

    @field_validator("diagnosis", "entity_name", "benchmark_group")
    @classmethod
    def check_non_empty(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("Campo textual não pode ser vazio")
        return v.strip()

    @field_validator("limitations", mode="before")
    @classmethod
    def normalize_limitations(cls, v: Any) -> List[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v.strip()] if v.strip() else []
        if isinstance(v, (list, tuple)):
            res = []
            for item in v:
                if isinstance(item, str) and item.strip():
                    res.append(item.strip())
                elif item is not None:
                    res.append(str(item).strip())
            return res
        return [str(v)]


class FinancialLeakItem(BaseModel):
    """Registro individual de fuga financeira ou divergência auditada."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    category: str = Field(..., description="Categoria da perda (Quebra de Caixa, Sangria Pendente, TEF Cartão)")
    description: str = Field(..., description="Descrição detalhada do fato gerador")
    amount: float = Field(..., ge=0.0, description="Valor monetário apurado em R$")
    status: Literal["critical", "warning", "resolved", "investigating"] = Field(
        default="warning",
        description="Gravidade ou status da auditoria"
    )
    pdv_or_terminal: Optional[str] = Field(default=None, description="Identificação do PDV, POS ou turno envolvido")


class FinancialLeakAuditProps(BaseModel):
    """Propriedades do Micro-Widget FinancialLeakAuditUI (Fase 6: F6-01)."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    diagnosis: str = Field(..., description="Diagnóstico de prevenção de perdas e quebras financeiras")
    severity: Literal["normal", "attention", "critical"] = Field(default="attention", description="Nível de severidade do alerta")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confiança na conciliação contábil (0.0 a 1.0)")
    total_leak_value: float = Field(..., ge=0.0, description="Perda total identificada em R$")
    cash_break_value: float = Field(default=0.0, ge=0.0, description="Quebra de caixa apurada em R$")
    pending_bleed_value: float = Field(default=0.0, ge=0.0, description="Volume de sangrias em atraso/gaveta em R$")
    tef_divergence_value: float = Field(default=0.0, ge=0.0, description="Divergência de conciliação TEF/cartões em R$")
    audited_shift: Optional[Union[str, int]] = Field(default=None, description="Turno auditado")
    cashier_name: Optional[str] = Field(default=None, description="Operador ou responsável pelo caixa")
    leak_items: List[FinancialLeakItem] = Field(default_factory=list, description="Itens detalhados de vazamentos")
    limitations: List[str] = Field(default_factory=list, description="Limitações da apuração bancária e fiscal")
    suggested_actions: List[GenUIActionOption] = Field(default_factory=list, description="Ações de contenção de perdas")

    @field_validator("diagnosis")
    @classmethod
    def check_diagnosis(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("diagnosis não pode ser vazio")
        return v.strip()

    @field_validator("limitations", mode="before")
    @classmethod
    def normalize_limitations(cls, v: Any) -> List[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v.strip()] if v.strip() else []
        if isinstance(v, (list, tuple)):
            res = []
            for item in v:
                if isinstance(item, str) and item.strip():
                    res.append(item.strip())
                elif item is not None:
                    res.append(str(item).strip())
            return res
        return [str(v)]


class UpsellComboItem(BaseModel):
    """Sugestão acionável de combo ou venda combinada com Lift."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    anchor_product: str = Field(..., description="Produto âncora comprado (Pista ou Conveniência)")
    recommended_product: str = Field(..., description="Produto complementar sugerido")
    lift: float = Field(..., ge=0.0, description="Multiplicador de Lift da associação")
    confidence_pct: float = Field(..., ge=0.0, le=100.0, description="Confiança estatística da regra (%)")
    support_pct: float = Field(..., ge=0.0, le=100.0, description="Suporte amostral nos cupons (%)")
    additional_ticket_reais: float = Field(..., ge=0.0, description="Ticket adicional gerado pela conversão em R$")
    script_pitch: str = Field(..., description="Script prático e direto para o frentista ou operador de caixa")
    category: Optional[str] = Field(default=None, description="Categoria do combo (ex: Pista + Aditivo, Balcão PDV)")


class BasketUpsellStrategyProps(BaseModel):
    """Propriedades do Micro-Widget BasketUpsellStrategyUI (Fase 6: F6-01)."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    diagnosis: str = Field(..., description="Diagnóstico executivo de oportunidades de ticket médio")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confiança na mineração de cupons (0.0 a 1.0)")
    projected_ticket_increase: float = Field(..., ge=0.0, description="Aumento potencial no ticket médio por cupom em R$")
    projected_monthly_revenue_lift: Optional[float] = Field(default=None, ge=0.0, description="Ganho financeiro mensal estimado em R$")
    category_focus: Optional[str] = Field(default=None, description="Foco estratégico (ex: Pista x Conveniência)")
    top_combos: List[UpsellComboItem] = Field(default_factory=list, description="Lista dos combos com maior Lift e viabilidade")
    limitations: List[str] = Field(default_factory=list, description="Limitações da amostra de cupons analisada")
    suggested_actions: List[GenUIActionOption] = Field(default_factory=list, description="Ações para ativação imediata de campanhas")

    @field_validator("diagnosis")
    @classmethod
    def check_diagnosis(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("diagnosis não pode ser vazio")
        return v.strip()

    @field_validator("limitations", mode="before")
    @classmethod
    def normalize_limitations(cls, v: Any) -> List[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v.strip()] if v.strip() else []
        if isinstance(v, (list, tuple)):
            res = []
            for item in v:
                if isinstance(item, str) and item.strip():
                    res.append(item.strip())
                elif item is not None:
                    res.append(str(item).strip())
            return res
        return [str(v)]



