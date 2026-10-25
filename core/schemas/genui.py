"""
Módulo de Envelopes Canônicos GenUI / SDUI da AURA.
Define contratos Pydantic v2 para micro-widgets de 3 camadas:
- Camada 1: Resumo Executivo (executive_summary)
- Camada 2: Visualização Rica (props determinísticas)
- Camada 3: Action Sheets Transacionais (actions tipadas com idempotência)
"""
# ruff: noqa: UP006, UP007, UP012, UP017, UP035, UP045, I001, B009, F401

from __future__ import annotations

import math
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator, AliasChoices

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
    idempotency_key: Optional[str] = Field(default=None, description="Chave deterministica opcional de idempotencia no Command Journal")

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
    status: Literal["APPROVED", "EXECUTED", "ROLLED_BACK"] = Field(
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
    status: Literal["APPROVED", "REJECTED_FORBIDDEN", "FAILED", "ROLLED_BACK"] = Field(
        default="APPROVED",
        description="Status oficial da auditoria"
    )
    details: Dict[str, Any] = Field(default_factory=dict, description="Detalhes complementares ou justificativa")
    client_ip: Optional[str] = Field(default=None, description="Endereco IP do cliente")


AURA_VOUCHER_SECRET = os.getenv("AURA_VOUCHER_SECRET", "aura_voucher_hmac_secret_v1")


def generate_action_voucher_signature(
    voucher_id: str,
    action_id: str,
    tool_call_id: str,
    status: str,
    timestamp: str,
    secret: Optional[str] = None,
) -> str:
    """Gera assinatura HMAC-SHA256 para integridade auditavel do Action Voucher."""
    import hmac
    import hashlib
    effective_secret = secret if secret is not None else os.getenv("AURA_VOUCHER_SECRET", AURA_VOUCHER_SECRET)
    raw = f"{voucher_id}:{action_id}:{tool_call_id}:{status}:{timestamp}".encode("utf-8")
    return hmac.new(effective_secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()


def verify_action_voucher_signature(
    voucher: ActionVoucher,
    secret: Optional[str] = None,
) -> bool:
    """Verifica a integridade criptografica da assinatura de um Action Voucher."""
    import hmac
    effective_secret = secret if secret is not None else os.getenv("AURA_VOUCHER_SECRET", AURA_VOUCHER_SECRET)
    expected = generate_action_voucher_signature(
        voucher_id=voucher.voucher_id,
        action_id=voucher.action_id,
        tool_call_id=voucher.tool_call_id,
        status=voucher.status,
        timestamp=voucher.timestamp,
        secret=effective_secret,
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
    ranking_postos_anp: Optional[Dict[str, Any]] = Field(default=None, description="Ranking dos postos mais baratos da ANP")

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
    """Registro individual de fuga financeira ou divergencia auditada."""
    model_config = ConfigDict(frozen=True, extra="ignore", populate_by_name=True)

    category: str = Field(..., description="Categoria da perda (Quebra de Caixa, Sangria Pendente, TEF Cartao, Cancelamento Suspeito)")
    description: str = Field(..., description="Descricao detalhada do fato gerador")
    amount: float = Field(..., ge=0.0, description="Valor monetario apurado em R$")
    status: Literal["critical", "warning", "resolved", "investigating"] = Field(
        default="warning",
        description="Gravidade ou status da auditoria"
    )
    pdv_or_terminal: Optional[str] = Field(default=None, description="Identificacao do PDV, POS ou turno envolvido")
    leak_type: Optional[str] = Field(default=None, description="Alias canonico para category")
    amount_reais: Optional[float] = Field(default=None, ge=0.0, description="Alias canonico para amount")
    severity: Optional[str] = Field(default=None, description="Alias canonico para status")
    source: Optional[str] = Field(default=None, description="Alias canonico para pdv_or_terminal")
    mitigation_action: Optional[str] = Field(default=None, description="Acao recomendada de contencao")

    @model_validator(mode="before")
    @classmethod
    def normalize_leak_item_aliases(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        d = dict(data)
        if "leak_type" in d and not d.get("category"):
            d["category"] = d["leak_type"]
        elif "category" in d and not d.get("leak_type"):
            d["leak_type"] = d["category"]

        if "amount_reais" in d and d.get("amount") is None:
            d["amount"] = d["amount_reais"]
        elif "amount" in d and d.get("amount_reais") is None:
            d["amount_reais"] = d["amount"]

        if "source" in d and not d.get("pdv_or_terminal"):
            d["pdv_or_terminal"] = d["source"]
        elif "pdv_or_terminal" in d and not d.get("source"):
            d["source"] = d["pdv_or_terminal"]

        if "severity" in d and not d.get("status"):
            sev = str(d["severity"]).lower().strip()
            if sev in ("critical", "critico", "danger"):
                d["status"] = "critical"
            elif sev in ("warning", "attention", "medio", "alerta"):
                d["status"] = "warning"
            elif sev in ("resolved", "normal", "baixo", "conforme"):
                d["status"] = "resolved"
            else:
                d["status"] = "investigating"
        elif "status" in d and not d.get("severity"):
            d["severity"] = d["status"]
        return d


class FinancialLeakAuditProps(BaseModel):
    """Propriedades do Micro-Widget FinancialLeakAuditUI (Fase 6: F6-01)."""
    model_config = ConfigDict(frozen=True, extra="ignore", populate_by_name=True)

    diagnosis: str = Field(..., description="Diagnostico de prevencao de perdas e quebras financeiras")
    severity: Literal["normal", "attention", "critical"] = Field(default="attention", description="Nivel de severidade do alerta")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confianca na conciliacao contabil (0.0 a 1.0)")
    total_leak_value: float = Field(..., ge=0.0, description="Perda total identificada em R$")
    cash_break_value: float = Field(default=0.0, ge=0.0, description="Quebra de caixa apurada em R$")
    pending_bleed_value: float = Field(default=0.0, ge=0.0, description="Volume de sangrias em atraso/gaveta em R$")
    tef_divergence_value: float = Field(default=0.0, ge=0.0, description="Divergencia de conciliacao TEF/cartoes em R$")
    total_divergence_reais: Optional[float] = Field(default=None, ge=0.0, description="Alias canonico para total_leak_value")
    risk_level: Optional[str] = Field(default=None, description="Nivel de risco: baixo, medio ou critico")
    audited_shift: Optional[Union[str, int]] = Field(default=None, description="Turno auditado")
    cashier_name: Optional[str] = Field(default=None, description="Operador ou responsavel pelo caixa")
    leak_items: List[FinancialLeakItem] = Field(default_factory=list, description="Itens detalhados de vazamentos")
    limitations: List[str] = Field(default_factory=list, description="Limitacoes da apuracao bancaria e fiscal")
    suggested_actions: List[GenUIActionOption] = Field(default_factory=list, description="Acoes de contencao de perdas")

    @model_validator(mode="before")
    @classmethod
    def normalize_leak_props_aliases(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        d = dict(data)
        if "total_divergence_reais" in d and d.get("total_leak_value") is None:
            d["total_leak_value"] = d["total_divergence_reais"]
        elif "total_leak_value" in d and d.get("total_divergence_reais") is None:
            d["total_divergence_reais"] = d["total_leak_value"]

        if "risk_level" in d and not d.get("severity"):
            rl = str(d["risk_level"]).lower().strip()
            if rl in ("critico", "critical"):
                d["severity"] = "critical"
            elif rl in ("medio", "attention", "warning"):
                d["severity"] = "attention"
            else:
                d["severity"] = "normal"
        elif "severity" in d and not d.get("risk_level"):
            s = str(d["severity"]).lower().strip()
            if s == "critical":
                d["risk_level"] = "critico"
            elif s == "attention":
                d["risk_level"] = "medio"
            else:
                d["risk_level"] = "baixo"
        return d

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
    """Sugestao acionavel de combo ou venda combinada com Lift."""
    model_config = ConfigDict(frozen=True, extra="ignore", populate_by_name=True, from_attributes=True)

    anchor_product: str = Field(..., validation_alias=AliasChoices("anchor_product", "produto_origem", "origem"), description="Produto ancora comprado (Pista ou Conveniencia)")
    recommended_product: str = Field(..., validation_alias=AliasChoices("recommended_product", "produto_recomendado", "recomendado"), description="Produto complementar sugerido")
    lift: float = Field(default=1.0, ge=0.0, description="Multiplicador de Lift da associacao")
    confidence_pct: float = Field(..., ge=0.0, le=100.0, validation_alias=AliasChoices("confidence_pct", "confianca_pct", "confidence"), description="Confianca estatistica da regra (%)")
    support_pct: float = Field(..., ge=0.0, le=100.0, validation_alias=AliasChoices("support_pct", "suporte_conjunto_pct", "suporte_pct", "support"), description="Suporte amostral nos cupons (%)")
    additional_ticket_reais: float = Field(default=0.0, ge=0.0, validation_alias=AliasChoices("additional_ticket_reais", "ticket_recomendado_reais", "ticket_adicional_reais", "additional_ticket"), description="Ticket adicional gerado pela conversao em R$")
    script_pitch: str = Field(..., validation_alias=AliasChoices("script_pitch", "script_sugerido_caixa", "script"), description="Script pratico e direto para o frentista ou operador de caixa")
    category: Optional[str] = Field(default=None, validation_alias=AliasChoices("category", "categoria"), description="Categoria do combo (ex: Pista + Aditivo, Balcao PDV)")

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if hasattr(data, "model_dump"):
            data = data.model_dump()
        elif hasattr(data, "__dict__") and not isinstance(data, dict):
            data = dict(data.__dict__)

        if isinstance(data, dict):
            data = dict(data)

            # 1. Normaliza produto_origem se for dict ou string
            if "anchor_product" not in data:
                p_orig = data.get("produto_origem") or data.get("origem")
                if isinstance(p_orig, dict):
                    data["anchor_product"] = p_orig.get("nompro") or p_orig.get("nome") or p_orig.get("produto") or str(p_orig.get("codpro", ""))
                elif p_orig is not None:
                    data["anchor_product"] = str(p_orig)
            elif isinstance(data.get("anchor_product"), dict):
                p_orig = data["anchor_product"]
                data["anchor_product"] = p_orig.get("nompro") or p_orig.get("nome") or str(p_orig.get("codpro", ""))

            # 2. Normaliza produto_recomendado se for dict ou string
            if "recommended_product" not in data:
                p_rec = data.get("produto_recomendado") or data.get("recomendado")
                if isinstance(p_rec, dict):
                    data["recommended_product"] = p_rec.get("nompro") or p_rec.get("nome") or p_rec.get("produto") or str(p_rec.get("codpro", ""))
                elif p_rec is not None:
                    data["recommended_product"] = str(p_rec)
            elif isinstance(data.get("recommended_product"), dict):
                p_rec = data["recommended_product"]
                data["recommended_product"] = p_rec.get("nompro") or p_rec.get("nome") or str(p_rec.get("codpro", ""))

            # 3. Normaliza lift (direto ou de metricas)
            if "lift" not in data or data["lift"] is None:
                if "metricas" in data and isinstance(data["metricas"], dict):
                    data["lift"] = data["metricas"].get("lift", 1.0)
                else:
                    data["lift"] = 1.0

            # 4. Normaliza confianca_pct (direto ou de metricas)
            if "confidence_pct" not in data or data["confidence_pct"] is None:
                conf = data.get("confianca_pct") or data.get("confidence")
                if conf is None and "metricas" in data and isinstance(data["metricas"], dict):
                    c_val = data["metricas"].get("confianca", 0.0)
                    conf = float(c_val) * 100.0 if float(c_val) <= 1.0 else float(c_val)
                data["confidence_pct"] = float(conf if conf is not None else 0.0)

            # 5. Normaliza suporte_conjunto_pct (direto ou de metricas)
            if "support_pct" not in data or data["support_pct"] is None:
                sup = data.get("suporte_conjunto_pct") or data.get("suporte_pct") or data.get("support")
                if sup is None and "metricas" in data and isinstance(data["metricas"], dict):
                    s_val = data["metricas"].get("suporte", 0.0)
                    sup = float(s_val) * 100.0 if float(s_val) <= 1.0 else float(s_val)
                data["support_pct"] = float(sup if sup is not None else 0.0)

            # 6. Normaliza ticket adicional (direto ou de impacto_financeiro)
            if "additional_ticket_reais" not in data or data["additional_ticket_reais"] is None:
                ticket = (
                    data.get("ticket_recomendado_reais")
                    or data.get("ticket_adicional_reais")
                    or data.get("additional_ticket")
                    or (data.get("impacto_financeiro", {}).get("preco_recomendado") if isinstance(data.get("impacto_financeiro"), dict) else None)
                    or (data.get("impacto_financeiro", {}).get("incremento_ticket_reais") if isinstance(data.get("impacto_financeiro"), dict) else None)
                    or 0.0
                )
                data["additional_ticket_reais"] = float(ticket or 0.0)

            # 7. Normaliza categoria
            if "category" not in data or not data["category"]:
                data["category"] = data.get("categoria") or "Balcao PDV"

            # 8. Normaliza script
            if "script_pitch" not in data or not data["script_pitch"]:
                pitch = data.get("script_sugerido_caixa") or data.get("script")
                if not pitch:
                    orig = data.get("anchor_product") or "o produto principal"
                    rec = data.get("recommended_product") or "o produto complementar"
                    pitch = f"Ao vender {orig}, ofereca {rec} no caixa."
                data["script_pitch"] = pitch
        return data


class BasketUpsellStrategyProps(BaseModel):
    """Propriedades do Micro-Widget BasketUpsellStrategyUI (Fase 6: F6-01)."""
    model_config = ConfigDict(frozen=True, extra="ignore", populate_by_name=True, from_attributes=True)

    diagnosis: str = Field(..., validation_alias=AliasChoices("diagnosis", "diagnostico", "diagnostico_estrategico"), description="Diagnostico executivo de oportunidades de ticket medio")
    confidence_score: float = Field(default=0.92, ge=0.0, le=1.0, validation_alias=AliasChoices("confidence_score", "confianca", "score"), description="Confianca na mineracao de cupons (0.0 a 1.0)")
    projected_ticket_increase: float = Field(default=0.0, ge=0.0, validation_alias=AliasChoices("projected_ticket_increase", "incremento_ticket_medio", "ticket_increase"), description="Aumento potencial no ticket medio por cupom em R$")
    projected_monthly_revenue_lift: Optional[float] = Field(default=None, ge=0.0, description="Ganho financeiro mensal estimado em R$")
    category_focus: Optional[str] = Field(default=None, description="Foco estrategico (ex: Pista x Conveniencia)")
    top_combos: List[UpsellComboItem] = Field(default_factory=list, validation_alias=AliasChoices("top_combos", "combos", "top_combos_cross_selling"), description="Lista dos combos com maior Lift e viabilidade")
    limitations: List[str] = Field(default_factory=list, description="Limitacoes da amostra de cupons analisada")
    suggested_actions: List[GenUIActionOption] = Field(default_factory=list, description="Acoes para ativacao imediata de campanhas")
    total_transacoes: Optional[int] = Field(default=None, description="Total de transacoes analisadas no periodo")
    pct_multiplos_itens: Optional[float] = Field(default=None, description="Percentual de compras com multiplos itens (%)")
    maior_lift: Optional[float] = Field(default=None, description="Maior Lift encontrado nas regras")
    regras_forte_sinergia_count: Optional[int] = Field(default=None, description="Total de regras com Lift >= 2.0x")

    @field_validator("diagnosis", mode="before")
    @classmethod
    def check_diagnosis(cls, v: Any) -> str:
        if isinstance(v, dict):
            v = v.get("text") or v.get("summary") or v.get("diagnostico") or v.get("diagnostico_estrategico") or str(v)
        elif hasattr(v, "text"):
            v = getattr(v, "text")
        v = str(v or "").strip()
        if not v:
            raise ValueError("diagnosis nao pode ser vazio")
        return v

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

    @field_validator("top_combos", mode="before")
    @classmethod
    def normalize_top_combos(cls, v: Any) -> List[Any]:
        if not v:
            return []
        if not isinstance(v, (list, tuple)):
            v = [v]
        normalized = []
        for item in v:
            if isinstance(item, UpsellComboItem):
                normalized.append(item)
            else:
                normalized.append(UpsellComboItem.model_validate(item))
        return normalized


class CompliancePillarItem(BaseModel):
    """Item explicativo de um dos pilares legais e tecnicos de conformidade."""
    model_config = ConfigDict(frozen=True, extra="ignore", populate_by_name=True)

    title: str = Field(..., description="Titulo do pilar legal ou tecnico")
    norma: str = Field(..., description="Referencia legislativa ou arquitetural")
    status: str = Field(default="conforme", description="Status do pilar: conforme, ativo, seguro")
    description: str = Field(..., description="Explicacao de seguranca juridica e operacional")


class ComplianceStatusProps(BaseModel):
    """Propriedades do Micro-Widget ComplianceStatusUI (Conformidade Legal & Interoperabilidade)."""
    model_config = ConfigDict(frozen=True, extra="ignore", populate_by_name=True, from_attributes=True)

    loja_cnpj: str = Field(..., validation_alias=AliasChoices("loja_cnpj", "cnpj"), description="CNPJ do estabelecimento")
    razao_social: Optional[str] = Field(default=None, description="Razao Social do estabelecimento controlador")
    compliant: bool = Field(default=True, validation_alias=AliasChoices("compliant", "conforme"), description="Se esta 100% conforme")
    status: str = Field(default="active", description="Status do opt-in: active, accepted, pending")
    versao_termo: str = Field(default="1.1", description="Versao do termo juridico formal")
    assinado_por: Optional[str] = Field(default=None, description="Representante legal que formalizou o opt-in")
    aceite_interoperabilidade_em: Optional[str] = Field(default=None, description="Data e hora do aceite formal")
    hash_termo: Optional[str] = Field(default=None, description="Digest SHA-256 no momento do aceite")
    hash_atual_termo: str = Field(default="", description="Digest SHA-256 do arquivo fisico atual do termo")
    hash_confere: bool = Field(default=True, description="Se o hash assinado confere com o termo atual")
    garantia_leitura_exclusiva: bool = Field(default=True, description="Garantia de transacoes READ ONLY estritas")
    isolamento_aups: bool = Field(default=True, description="Garantia de isolamento canonico AUPS Clean Room")
    driver_level_protection: bool = Field(default=True, description="Garantia de timeouts em nivel de driver")
    statement_timeout_ms: int = Field(default=4000, description="Timeout maximo de query para nao onerar o ERP (ms)")
    lock_timeout_ms: int = Field(default=1000, description="Timeout maximo de espera por lock (ms)")
    role_banco: str = Field(default="aura_service_ro", description="Role de leitura especializada somente-leitura")
    mensagem: str = Field(default="Conformidade legal e tecnica ativa.", description="Mensagem executiva do status")
    pilares_legais: List[CompliancePillarItem] = Field(default_factory=list, description="Pilares legais e tecnicos da protecao")
    suggested_actions: List[GenUIActionOption] = Field(default_factory=list, description="Acoes HITL executivas")


class LMCTankComplianceItem(BaseModel):
    """Fechamento e auditoria volumetrica por tanque no LMC (Portaria ANP 26/1992)."""
    model_config = ConfigDict(frozen=True, extra="ignore", populate_by_name=True)

    tanque: str = Field(..., description="Identificador do tanque")
    combustivel: str = Field(..., description="Nome do combustivel")
    capacidade_litros: float = Field(default=0.0, description="Capacidade maxima nominal em litros")
    estoque_abertura_litros: float = Field(default=0.0, description="Estoque de abertura em litros")
    recebimentos_descargas_litros: float = Field(default=0.0, description="Volume recebido via DFE/DANFE em litros")
    vendas_bicos_litros: float = Field(default=0.0, description="Volume vendido registrado nos bicos em litros")
    estoque_contabil_litros: float = Field(default=0.0, description="Estoque escriturado/contabil apurado em litros")
    estoque_fisico_medido_litros: float = Field(default=0.0, description="Estoque fisico apurado em regua ou sonda em litros")
    variacao_litros: float = Field(default=0.0, description="Variacao volumetrica liquida (fisico - contabil) em litros")
    variacao_pct: float = Field(default=0.0, description="Variacao volumetrica percentual sobre as vendas (%)")
    tolerancia_max_pct: float = Field(default=0.60, description="Tolerancia legal maxima da ANP (+-0.60%)")
    tolerancia_max_litros: float = Field(default=0.0, description="Volume maximo tolerado em litros")
    status: str = Field(default="CONFORME", description="CONFORME ou CRITICO")
    diagnostico: str = Field(default="", description="Parecer operacional e regulatorio do tanque")


class LMCComplianceProps(BaseModel):
    """Propriedades do Micro-Widget LMCComplianceReportUI (Portaria ANP 26/1992 e Resolucao ANP 894/2022)."""
    model_config = ConfigDict(frozen=True, extra="ignore", populate_by_name=True)

    diagnosis: str = Field(..., description="Diagnostico regulatorio consolidado do LMC")
    status: str = Field(default="CONFORME", description="Status geral: CONFORME ou CRITICO")
    confidence_score: float = Field(default=0.98, ge=0.0, le=1.0, description="Confianca na auditoria volumetrica")
    data_analise: str = Field(..., description="Data de referencia analisada (YYYY-MM-DD)")
    variacao_geral_pct: float = Field(default=0.0, description="Variacao percentual consolidada sobre o total de vendas (%)")
    tolerancia_legal_pct: float = Field(default=0.60, description="Tolerancia regulamentar maxima da ANP (0.60%)")
    total_vendas_litros: float = Field(default=0.0, description="Volume total vendido atraves dos bicos (L)")
    total_recebimentos_litros: float = Field(default=0.0, description="Volume total recebido de descargas (L)")
    total_estoque_contabil_litros: float = Field(default=0.0, description="Estoque contabil escriturado total (L)")
    total_estoque_fisico_litros: float = Field(default=0.0, description="Estoque fisico total medido em regua/telemetria (L)")
    total_variacao_litros: float = Field(default=0.0, description="Variacao volumetrica liquida consolidada (L)")
    tanques: List[LMCTankComplianceItem] = Field(default_factory=list, description="Detalhamento individualizado por tanque")
    tanques_criticos: List[Dict[str, Any]] = Field(default_factory=list, description="Lista de tanques com variacao fora de +-0.60%")
    parecer_regulatorio: str = Field(..., description="Parecer juridico-regulatorio fundamentado na Portaria ANP 26/1992")
    suggested_actions: List[GenUIActionOption] = Field(default_factory=list, description="Acoes HITL interativas recomendadas")


class MacroeconomicInventoryCostProps(BaseModel):
    """Propriedades do Micro-Widget MacroeconomicInventoryCostUI (BACEN Selic, PTAX e PMPF CONFAZ)."""
    model_config = ConfigDict(frozen=True, extra="ignore", populate_by_name=True)

    diagnosis: str = Field(..., description="Diagnostico executivo de custo de oportunidade de estoque e pauta fiscal")
    confidence_score: float = Field(default=0.95, ge=0.0, le=1.0, description="Confianca estatistica dos indicadores")
    volume_total_litros: float = Field(..., description="Volume total estocado nos tanques em litros")
    custo_medio_litro: float = Field(..., description="Custo medio de aquisicao por litro em R$")
    capital_imobilizado_reais: float = Field(..., description="Total de capital financeiro imobilizado nos tanques em R$")
    taxa_selic_anual_pct: float = Field(..., description="Taxa Selic anualizada oficial do BACEN (Serie 11 SGS)")
    taxa_cambio_ptax: float = Field(default=0.0, description="Taxa de cambio PTAX Dolar comercial de venda do BACEN")
    custo_diario_carregamento_reais: float = Field(..., description="Custo financeiro diario de carregamento (Selic/252)")
    custo_mensal_carregamento_reais: float = Field(..., description="Custo financeiro mensal de carregamento (21 dias uteis)")
    uf_referencia: str = Field(default="SP", description="UF de referencia da tributacao")
    produto_referencia: str = Field(default="GASOLINA COMUM", description="Produto analisado na pauta fiscal")
    pmpf_vigente_reais: Optional[float] = Field(default=None, description="Preco Medio Ponderado a Consumidor Final (PMPF) CONFAZ")
    spread_pmpf_reais: Optional[float] = Field(default=None, description="Spread em R$/L entre o custo do posto e a pauta PMPF")
    spread_pmpf_pct: Optional[float] = Field(default=None, description="Spread percentual frente ao custo do posto (%)")
    ato_cotepe: Optional[str] = Field(default=None, description="Ato COTEPE publicador da pauta PMPF")
    vigencia_pmpf: Optional[str] = Field(default=None, description="Data de vigencia inicial da pauta PMPF")
    recomendacao_compra: str = Field(..., description="Orientacao executiva para compra fracionada vs carreta fechada")
    suggested_actions: List[GenUIActionOption] = Field(default_factory=list, description="Acoes HITL estrategicas recomendadas")


# =============================================================================
# BLOCOS MODULARES GENERATIVOS (LEGO BLOCKS UI - FASE 7+)
# =============================================================================

class LegoKpiItem(BaseModel):
    """Item individual de indicador/metrica para grid modular."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    label: str = Field(..., description="Nome do indicador (ex: Faturamento, Volume, Margem)")
    value: str = Field(..., description="Valor formatado (ex: R$ 42.500,00, 15.200 L, +18.5%)")
    delta: Optional[str] = Field(default=None, description="Variacao frente ao periodo anterior ou meta (ex: +5.2%)")
    trend: Optional[str] = Field(default="neutral", description="Tendencia: up, down ou neutral")
    status: str = Field(default="neutral", description="Status semantico: success, warning, danger, neutral")
    subtext: Optional[str] = Field(default=None, description="Texto complementar de contexto (ex: Meta: R$ 40k)")


class LegoComparisonRow(BaseModel):
    """Linha de confronto comparativo entre entidades (ex: Filial vs Mercado ou Turno A vs Turno B)."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    name: str = Field(..., description="Nome do item ou parametro comparado")
    primary_value: str = Field(..., description="Valor principal (ex: Filial)")
    secondary_value: str = Field(..., description="Valor de referencia (ex: Mercado ou Meta)")
    gap: Optional[str] = Field(default=None, description="Diferenca apurada (ex: +R$ 0,15, -2,1 pp)")
    status: str = Field(default="neutral", description="Status semantico: success, warning, danger, neutral")
    observation: Optional[str] = Field(default=None, description="Observacao executiva da linha")


class LegoRankingItem(BaseModel):
    """Item ranqueado com posicao e medalha (ex: Top Postos, Ranking de Bicos ou Frentistas)."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    rank: int = Field(..., ge=1, description="Posicao no ranking (1, 2, 3...)")
    title: str = Field(..., description="Titulo ou nome da entidade (ex: Posto Alpha, Bico 03)")
    subtitle: Optional[str] = Field(default=None, description="Subtitulo ou bandeira (ex: Shell, Pista Central)")
    value: str = Field(..., description="Valor principal em destaque (ex: R$ 5,39, 4.250 L)")
    tag: Optional[str] = Field(default=None, description="Tag ou classificacao (ex: 1º Quartil, Lider)")
    status: str = Field(default="neutral", description="Status: success, warning, danger, neutral")


class LegoTimelineEvent(BaseModel):
    """Evento em linha do tempo (ex: marcos do turno, afericoes, alertas historicos)."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    timestamp: str = Field(..., description="Horario ou data do evento (ex: 14:32 ou 2026-10-18)")
    title: str = Field(..., description="Titulo do evento")
    description: Optional[str] = Field(default=None, description="Descricao detalhada")
    badge: Optional[str] = Field(default=None, description="Badge descritivo")
    status: str = Field(default="neutral", description="Status: success, warning, danger, neutral")


class LegoAlertItem(BaseModel):
    """Callout de alerta ou diagnostico critico."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    title: str = Field(..., description="Titulo do alerta")
    message: str = Field(..., description="Mensagem analitica do alerta")
    severity: str = Field(default="info", description="Severidade: info, warning, critical, success")
    action_label: Optional[str] = Field(default=None, description="Rotulo de acao rapida opcional")


class LegoBlock(BaseModel):
    """Bloco modular generativo empilhavel."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    block_id: str = Field(..., description="Identificador unico do bloco")
    block_type: str = Field(..., description="Tipo do bloco: kpi_grid, comparison_table, ranking_list, timeline_feed, alert_callout, custom_content")
    title: Optional[str] = Field(default=None, description="Titulo do bloco")
    subtitle: Optional[str] = Field(default=None, description="Subtitulo explicativo")
    kpis: List[LegoKpiItem] = Field(default_factory=list, description="Lista de KPIs (para block_type=kpi_grid)")
    comparison_rows: List[LegoComparisonRow] = Field(default_factory=list, description="Linhas de confronto (para block_type=comparison_table)")
    ranking_items: List[LegoRankingItem] = Field(default_factory=list, description="Itens de ranking (para block_type=ranking_list)")
    timeline_events: List[LegoTimelineEvent] = Field(default_factory=list, description="Eventos de timeline (para block_type=timeline_feed)")
    alert: Optional[LegoAlertItem] = Field(default=None, description="Item de alerta (para block_type=alert_callout)")
    custom_content: Optional[str] = Field(default=None, description="Conteudo textual ou markdown customizado")


class GenerativeModularProps(BaseModel):
    """Propriedades do Micro-Widget GenerativeModularCardUI (Blocos Lego Generativos)."""
    model_config = ConfigDict(frozen=True, extra="ignore", populate_by_name=True)

    title: str = Field(..., description="Titulo executivo do card generativo")
    subtitle: Optional[str] = Field(default=None, description="Subtitulo de contexto")
    diagnosis: str = Field(..., description="Diagnostico executivo consolidado")
    confidence_score: float = Field(default=0.95, ge=0.0, le=1.0, description="Confianca estatistica (0.0 a 1.0)")
    blocks: List[LegoBlock] = Field(default_factory=list, description="Lista ordenada de blocos modulares lego a renderizar")
    limitations: List[str] = Field(default_factory=list, description="Limitacoes ou avisos amostrais")
    suggested_actions: List[GenUIActionOption] = Field(default_factory=list, description="Acoes transacionais HITL")


# =============================================================================
# LOOP FECHADO DE ACAO (ACTIONABLE DIRECTIVE PAYLOAD - FASE 4)
# =============================================================================

class ActionableDirectivePayload(BaseModel):
    """
    Envelope canonico de Diretiva de Acao em 1-Clique (Loop Fechado de Acao - Fase 4).
    Padroniza acoes executivas acionaveis com roteiro de voz, instrucao tatica de pista
    e campanha segmentada de recuperacao para despacho via outbox local.
    """
    model_config = ConfigDict(frozen=True, extra="ignore", populate_by_name=True)

    directive_id: str = Field(
        default_factory=lambda: f"dir_{uuid.uuid4().hex[:12]}",
        description="UUID unico da diretiva de acao executiva",
    )
    card_id: Optional[str] = Field(
        default=None,
        description="Identificador do card de excecao de origem (se aplicavel)",
    )
    title: str = Field(..., description="Titulo executivo conciso da acao prescrita")
    category: str = Field(
        default="operacao",
        description="Categoria: caixa_sangria, runout_estoque, margem_conversao, market_basket_combo, anomalia_operacional",
    )
    financial_impact_brl: float = Field(
        default=0.0,
        description="Impacto financeiro apurado ou projetado em Reais (R$)",
    )
    roteiro_voz_consultor: str = Field(
        ...,
        description="Texto natural humanizado pronto para sintese de voz (TTS / Briefing Executivo)",
    )
    treinamento_equipe_15s: str = Field(
        ...,
        description="Instrucao tatica direta para o gerente/equipe de pista em 15 segundos",
    )
    campanha_clientes_whatsapp: str = Field(
        default="",
        description="Mensagem persuasiva segmentada para clientes ou recuperacao operacional",
    )
    status: Literal["pending", "queued", "dispatched", "executed", "cancelled"] = Field(
        default="pending",
        description="Status do ciclo de vida da diretiva acionavel",
    )
    canal_despacho: Literal["outbox_webhook", "in_app_cockpit", "notificador_desktop"] = Field(
        default="in_app_cockpit",
        description="Canal de despacho primario da acao",
    )
    idempotency_key: Optional[str] = Field(
        default=None,
        description="Chave de idempotencia para persistencia e despacho seguro",
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Timestamp ISO-8601 de criacao",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadados contextuais adicionais",
    )

    @field_validator("title")
    @classmethod
    def check_title(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("title nao pode ser vazio")
        return v.strip()

    @field_validator("roteiro_voz_consultor")
    @classmethod
    def check_roteiro(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("roteiro_voz_consultor nao pode ser vazio")
        return v.strip()


# =============================================================================
# FEED EXECUTIVO ZERO-CLICK (O ANTI-DASHBOARD ESTATICO - FASE 2)
# =============================================================================

class ExecutiveExceptionCard(BaseModel):
    """
    Contrato Pydantic v2 para Cards de Excecao e Oportunidade do Feed Zero-Click (Fase 2).
    Apresenta diagnostico direto, prova matematica deterministica, impacto financeiro em R$
    e acao HITL em 1-clique para decisao imediata.
    """
    model_config = ConfigDict(frozen=True, extra="ignore", populate_by_name=True)

    card_id: str = Field(..., description="Identificador unico deterministico do card (ex: card_runout_01)")
    title: str = Field(..., description="Titulo executivo conciso do alerta ou oportunidade")
    category: str = Field(
        ...,
        description="Categoria: caixa_sangria, runout_estoque, margem_conversao, market_basket_combo, anomalia_operacional",
    )
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"] = Field(
        default="HIGH",
        description="Nivel de severidade do impacto",
    )
    financial_impact_brl: float = Field(
        ...,
        description="Impacto financeiro apurado ou projetado em Reais (R$)",
    )
    diagnostico_direto: str = Field(
        ...,
        description="1 linha executiva com severidade clara sem ruido gerativo",
    )
    prova_matematica: Union[str, Dict[str, Any]] = Field(
        ...,
        description="Memoria de calculo deterministica, impacto em R$ e comparativo percentual",
    )
    acao_recomendada_hitl: Union[GenUIActionOption, Dict[str, Any]] = Field(
        ...,
        description="Payload estruturado para decisao e execucao imediata em 1-clique",
    )
    urgency_timeframe: Optional[str] = Field(
        default=None,
        description="Janela temporal de urgencia (ex: 48h, imediato, turno_atual)",
    )
    directive: Optional[ActionableDirectivePayload] = Field(
        default=None,
        description="Diretiva acionavel de loop fechado estruturada para execucao em 1-clique (Fase 4)",
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Timestamp ISO-8601 da geracao",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadados operacionais complementares (filial_id, tenant_id, etc.)",
    )

    @field_validator("title")
    @classmethod
    def check_title(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("title nao pode ser vazio")
        return v.strip()

    @field_validator("diagnostico_direto")
    @classmethod
    def check_diagnostico(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("diagnostico_direto nao pode ser vazio")
        return v.strip()

    @field_validator("financial_impact_brl")
    @classmethod
    def check_financial_impact(cls, v: float) -> float:
        if math.isnan(v) or math.isinf(v):
            raise ValueError("financial_impact_brl deve ser um numero finito valido")
        if v < 0:
            raise ValueError("financial_impact_brl deve ser maior ou igual a zero")
        return round(float(v), 2)


# =============================================================================
# MOTORES COGNITIVOS PRESCRITIVOS (FASE 3: SUPERANDO O BI DESCRITIVO)
# =============================================================================

class ErosionModalityItem(BaseModel):
    """Item analitico por modalidade de pagamento na auditoria de erosao financeira."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    modalidade: str = Field(..., description="Nome da modalidade (ex: PIX, Dinheiro, Cartao Debito, Credito Vista, Credito Parcelado, Voucher Frota)")
    volume_reais: float = Field(..., ge=0.0, description="Volume bruto vendido na modalidade em R$")
    taxa_contratada_pct: float = Field(..., ge=0.0, description="Taxa MDR contratada com a adquirente (%)")
    taxa_efetiva_descontada_pct: float = Field(..., ge=0.0, description="Taxa media real descontada na liquidacao (%)")
    divergencia_taxa_pct: float = Field(default=0.0, description="Divergencia entre taxa real e contratada (pp)")
    perda_divergencia_reais: float = Field(default=0.0, ge=0.0, description="Prejuizo direto por cobranca a maior em R$")
    prazo_liquidacao_dias: int = Field(default=0, ge=0, description="Prazo medio de recebimento em dias corridos/uteis")
    vpl_recebimento_reais: float = Field(..., description="Valor Presente Liquido (VPL) descontado pela Selic diaria")
    custo_carregamento_selic_reais: float = Field(default=0.0, ge=0.0, description="Custo de oportunidade Selic ate a liquidacao em R$")


class FinancialErosionProps(BaseModel):
    """Propriedades do Micro-Widget FinancialErosionUI (Motor 1: Erosao Financeira e Arbitragem Selic)."""
    model_config = ConfigDict(frozen=True, extra="ignore", populate_by_name=True)

    diagnosis: str = Field(..., description="Diagnostico executivo da erosao financeira e taxas TEF")
    confidence_score: float = Field(default=0.96, ge=0.0, le=1.0, description="Score de confianca estatistica (0.0 a 1.0)")
    total_vendas_reais: float = Field(..., ge=0.0, description="Faturamento total auditado no periodo em R$")
    total_taxas_contratadas_reais: float = Field(default=0.0, ge=0.0, description="Total de taxas orcadas pelo contrato em R$")
    total_taxas_reais_descontadas: float = Field(default=0.0, ge=0.0, description="Total de taxas efetivamente descontadas em R$")
    total_divergencia_taxas_reais: float = Field(..., ge=0.0, description="Perda total por cobrancas a maior das adquirentes em R$")
    total_custo_carregamento_selic_reais: float = Field(default=0.0, ge=0.0, description="Custo financeiro de espera ate a liquidacao em R$")
    taxa_selic_anual_pct: float = Field(..., description="Taxa Selic anualizada oficial (BACEN SGS Serie 11)")
    taxa_selic_diaria_pct: float = Field(..., description="Taxa Selic diaria util equivalente (%)")
    necessidade_caixa_72h_reais: float = Field(default=0.0, ge=0.0, description="Compromissos e boletos a liquidar em 72h em R$")
    estrategia_cobertura_otima: str = Field(..., description="Estrategia prescritiva de menor custo financeiro para cobrir o caixa")
    economia_estimada_reais: float = Field(default=0.0, ge=0.0, description="Economia projetada ao aplicar a prescricao em R$")
    modalidades: List[ErosionModalityItem] = Field(default_factory=list, description="Detalhamento individual por meio de pagamento")
    acoes_prescritivas: List[str] = Field(default_factory=list, description="Diretrizes operacionais acionaveis")
    suggested_actions: List[GenUIActionOption] = Field(default_factory=list, description="Acoes transacionais HITL")


class DeadCapitalItem(BaseModel):
    """Item com capital financeiro imobilizado sem giro (Capital Morto)."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    produto_sku: str = Field(..., description="Codigo ou SKU do produto")
    produto_nome: str = Field(..., description="Descricao do produto")
    categoria: str = Field(default="conveniencia", description="Categoria do produto")
    saldo_estoque: float = Field(..., ge=0.0, description="Quantidade estocada parada")
    custo_unitario_reais: float = Field(..., ge=0.0, description="Custo unitario de aquisicao em R$")
    capital_imobilizado_reais: float = Field(..., ge=0.0, description="Capital financeiro parado em R$")
    dias_sem_giro: int = Field(..., ge=0, description="Dias consecutivos sem nenhuma venda")
    custo_oportunidade_selic_reais: float = Field(..., ge=0.0, description="Corrosao Selic acumulada do capital imobilizado")
    combo_apriori_sugerido: Optional[Dict[str, Any]] = Field(default=None, description="Pareamento estrategico Apriori (produto parceiro, lift, sugestao de desconto)")


class GhostStockoutItem(BaseModel):
    """Item de Curva A em ruptura fantasma (saldo positivo no ERP mas zero vendas no pico)."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    produto_sku: str = Field(..., description="Codigo ou SKU do produto")
    produto_nome: str = Field(..., description="Descricao do produto")
    categoria: str = Field(default="curva_a", description="Classificacao de curva do produto")
    saldo_erp: float = Field(..., ge=0.0, description="Saldo positivo registrado no ERP")
    velocidade_historica_hora: float = Field(..., ge=0.0, description="Velocidade media de vendas por hora em horario de pico")
    horas_sem_venda_pico: int = Field(..., ge=1, description="Horas consecutivas com zero vendas durante pico")
    perda_faturamento_estimada_reais: float = Field(..., ge=0.0, description="Estimativa de vendas perdidas por gondola vazia em R$")
    alerta_gondola: str = Field(..., description="Orientacao de reposicao fisica imediata")


class DeadCapitalOpportunityProps(BaseModel):
    """Propriedades do Micro-Widget DeadCapitalOpportunityUI (Motor 2: Capital Morto e Ruptura Fantasma)."""
    model_config = ConfigDict(frozen=True, extra="ignore", populate_by_name=True)

    diagnosis: str = Field(..., description="Diagnostico executivo de capital imobilizado e rupturas invisiveis")
    confidence_score: float = Field(default=0.95, ge=0.0, le=1.0, description="Score de confianca estatistica (0.0 a 1.0)")
    total_capital_morto_imobilizado_reais: float = Field(..., ge=0.0, description="Total de capital financeiro parado em itens sem giro em R$")
    total_custo_selic_acumulado_reais: float = Field(..., ge=0.0, description="Custo de oportunidade Selic total acumulado no estoque parado em R$")
    taxa_selic_anual_pct: float = Field(..., description="Taxa Selic anual utilizada no calculo")
    itens_capital_morto: List[DeadCapitalItem] = Field(default_factory=list, description="Lista de itens encalhados com oportunidade de liquidacao")
    itens_ruptura_fantasma: List[GhostStockoutItem] = Field(default_factory=list, description="Lista de itens de Curva A com provavel gondola vazia")
    plano_acao_desova: str = Field(..., description="Plano de desova estrategica pareada com produtos de alto giro")
    suggested_actions: List[GenUIActionOption] = Field(default_factory=list, description="Acoes transacionais HITL")


class WaterfallStepItem(BaseModel):
    """Etapa individual do grafico causal Waterfall de margem."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    step_name: str = Field(..., description="Nome da etapa (ex: Margem Anterior, Efeito Reposicao, Margem Atual)")
    category: Literal["start", "effect", "end"] = Field(..., description="Categoria da etapa")
    impact_reais: float = Field(..., description="Impacto em R$ (+ ganho, - reducao, ou valor total)")
    cumulative_reais: float = Field(..., description="Valor acumulado resultante da margem em R$")
    description: str = Field(..., description="Explicacao causal do fator de impacto")


class MarginWaterfallProps(BaseModel):
    """Propriedades do Micro-Widget MarginWaterfallUI (Motor 3: Decomposicao Causal Waterfall de Margem)."""
    model_config = ConfigDict(frozen=True, extra="ignore", populate_by_name=True)

    diagnosis: str = Field(..., description="Diagnostico causal da variacao de margem e lucro bruto")
    confidence_score: float = Field(default=0.97, ge=0.0, le=1.0, description="Score de confianca do modelo causal (0.0 a 1.0)")
    periodo_atual: str = Field(..., description="Periodo de referencia atual analisado")
    periodo_anterior: str = Field(..., description="Periodo anterior de confronto")
    margem_inicial_reais: float = Field(..., description="Margem bruta/liquida do periodo anterior em R$")
    margem_final_reais: float = Field(..., description="Margem bruta/liquida do periodo atual em R$")
    delta_margem_total_reais: float = Field(..., description="Variacao liquida total apurada em R$")
    delta_margem_pct: float = Field(..., description="Variacao percentual da margem (%)")
    efeito_custo_reposicao_reais: float = Field(..., description="Efeito Custo de Reposicao / CMV nao repassado no PDV em R$")
    efeito_mix_conversao_reais: float = Field(..., description="Efeito Mix de Produtos e Conversao de Aditivadas em R$")
    efeito_volume_puro_reais: float = Field(..., description="Efeito Volume Puro de Clientes e Fluxo em R$")
    efeito_perdas_descontos_reais: float = Field(..., description="Efeito Perdas Fisicas, Descontos de Caixa e Afericoes em R$")
    horas_defasagem_preco_medio: float = Field(default=0.0, ge=0.0, description="Tempo medio em horas que o posto demorou para repassar o novo CMV")
    steps: List[WaterfallStepItem] = Field(default_factory=list, description="Lista ordenada de degraus da cascata Waterfall")
    suggested_actions: List[GenUIActionOption] = Field(default_factory=list, description="Acoes transacionais HITL")


class BatchSimulationScenario(BaseModel):
    """Cenario simulado de elasticidade de demanda para lote de compra."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    nome: str = Field(..., description="Nome do cenario (ex: Cenario Base, Micro-Promocao R$ 0,05, Campanha WhatsApp R$ 0,08)")
    reducao_preco_reais: float = Field(..., ge=0.0, description="Reducao no preco de venda por litro em R$")
    preco_promocional_reais: float = Field(..., ge=0.0, description="Preco resultante na bomba em R$")
    aceleracao_vendas_pct: float = Field(..., description="Aumento percentual estimado na queima horaria (%)")
    horas_para_abrir_espaco: float = Field(..., ge=0.0, description="Horas estimadas para abrir o espaco do lote minimo")
    custo_promocao_reais: float = Field(..., ge=0.0, description="Custo financeiro da reducao de margem no volume promocional em R$")
    ganho_desconto_fornecedor_reais: float = Field(..., ge=0.0, description="Ganho financeiro bruto obtido pelo desconto de lote fechado em R$")
    resultado_liquido_reais: float = Field(..., description="Lucro liquido incremental gerado pela operacao em R$")
    viavel: bool = Field(..., description="Indica se a operacao gera resultado positivo antes do lote")


class ElasticityBatchSimulatorProps(BaseModel):
    """Propriedades do Micro-Widget ElasticityBatchSimulatorUI (Motor 4: Elasticidade e Otimizador de Lote)."""
    model_config = ConfigDict(frozen=True, extra="ignore", populate_by_name=True)

    diagnosis: str = Field(..., description="Diagnostico executivo da simulacao de lote e espaco de tanque")
    confidence_score: float = Field(default=0.95, ge=0.0, le=1.0, description="Score de confianca estatistica (0.0 a 1.0)")
    produto: str = Field(..., description="Combustivel ou produto analisado")
    municipio: str = Field(..., description="Municipio de referencia para benchmark da ANP")
    tanque_capacidade_litros: float = Field(..., ge=0.0, description="Capacidade nominal do tanque em litros")
    estoque_atual_litros: float = Field(..., ge=0.0, description="Estoque fisico atual no tanque em litros")
    espaco_livre_ullage_litros: float = Field(..., ge=0.0, description="Espaco fisico disponivel no tanque (Ullage) em litros")
    lote_minimo_compra_litros: float = Field(..., ge=0.0, description="Lote minimo exigido pelo fornecedor (ex: 5.000L compartimento)")
    capacidade_recebimento_imediata: bool = Field(..., description="True se Ullage >= Lote Minimo, False se faltar espaco")
    litros_faltantes_para_lote: float = Field(default=0.0, ge=0.0, description="Litros que faltam ser consumidos para caber o lote")
    desconto_lote_reais_litro: float = Field(..., ge=0.0, description="Desconto logistico oferecido pela distribuidora por litro em R$")
    economia_potencial_lote_reais: float = Field(..., ge=0.0, description="Economia bruta total ao comprar o lote fechado em R$")
    preco_venda_atual_reais: float = Field(..., ge=0.0, description="Preco de venda atual praticado no posto em R$")
    benchmark_anp_municipio: Dict[str, Any] = Field(default_factory=dict, description="Estatisticas de preco da ANP no municipio (media, q1, q2, q3)")
    elasticidade_preco_estimada: float = Field(default=-1.8, description="Coeficiente de elasticidade preco da demanda adotado")
    cenarios: List[BatchSimulationScenario] = Field(default_factory=list, description="Lista de cenarios simulados de aceleracao de demanda")
    cenario_recomendado: str = Field(..., description="Parecer e cenario ideal recomendado para maximizar o ganho liquido")
    suggested_actions: List[GenUIActionOption] = Field(default_factory=list, description="Acoes transacionais HITL")


class PaymentMethodBreakdownItem(BaseModel):
    """Item consolidado de forma de pagamento no fechamento do dia."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    modalidade: str = Field(..., description="Nome da forma de pagamento (Dinheiro, Cartao de Debito, PIX, etc.)")
    codigo_forma: str = Field(default="", description="Codigo interno da forma de pagamento no ERP")
    total_reais: float = Field(..., description="Valor total faturado nesta modalidade em R$")
    total_transacoes: int = Field(default=0, description="Quantidade de transacoes/cupons")
    percentual: float = Field(default=0.0, description="Percentual sobre o faturamento total (%)")
    ticket_medio: float = Field(default=0.0, description="Ticket medio em R$")


class CashierOperatorPaymentItem(BaseModel):
    """Detalhamento financeiro por caixa (terminal PDV) e operador responsavel."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    caixa: str = Field(..., description="Identificacao do caixa ou terminal PDV (ex: Caixa 007)")
    caixa_raw: str = Field(default="", description="Codigo bruto do PDV")
    operador_matricula: str = Field(default="", description="Matricula do operador no ERP")
    operador_nome: str = Field(..., description="Nome do operador ou funcionario responsavel")
    turno: str = Field(default="1º TURNO", description="Turno de trabalho do operador")
    dinheiro_reais: float = Field(default=0.0, description="Total em Dinheiro (R$)")
    cartao_debito_reais: float = Field(default=0.0, description="Total em Cartao de Debito (R$)")
    cartao_credito_reais: float = Field(default=0.0, description="Total em Cartao de Credito (R$)")
    cartao_total_reais: float = Field(default=0.0, description="Total consolidado em Cartoes (R$)")
    pix_reais: float = Field(default=0.0, description="Total em PIX (R$)")
    prazo_convenio_reais: float = Field(default=0.0, description="Total em Prazo/Convenio (R$)")
    outros_reais: float = Field(default=0.0, description="Outros meios de pagamento em R$")
    total_caixa_reais: float = Field(..., description="Total geral apurado no caixa em R$")
    total_cupons: int = Field(default=0, description="Quantidade de cupons emitidos")


class PaymentMethodsBreakdownProps(BaseModel):
    """Propriedades do Micro-Widget PaymentMethodsBreakdownUI (Formas de Pagamento por Caixa e Operador)."""
    model_config = ConfigDict(frozen=True, extra="ignore", populate_by_name=True)

    title: str = Field(default="Formas de Pagamento & Caixas", description="Titulo executivo do card")
    subtitle: str = Field(default="Detalhamento por Terminal PDV, Operador & Modalidade", description="Subtitulo descritivo")
    data_referencia: str = Field(..., description="Data de referencia analisada (DD/MM/AAAA)")
    aviso_data: Optional[str] = Field(default=None, description="Aviso caso tenha sido selecionada a ultima data com movimento")
    total_geral_reais: float = Field(..., description="Faturamento total consolidado em R$")
    total_transacoes: int = Field(default=0, description="Total de transacoes apuradas")
    ticket_medio_geral: float = Field(default=0.0, description="Ticket medio geral em R$")
    total_caixas_ativos: int = Field(default=0, description="Quantidade de caixas com movimento")
    total_operadores_ativos: int = Field(default=0, description="Quantidade de operadores com movimento")
    maior_modalidade: Optional[str] = Field(default=None, description="Modalidade com maior representatividade")
    modalidades: List[PaymentMethodBreakdownItem] = Field(default_factory=list, description="Lista de formas de pagamento")
    caixas_operadores: List[CashierOperatorPaymentItem] = Field(default_factory=list, description="Detalhamento por caixa e operador")
    diagnosis: str = Field(default="", description="Diagnostico executivo conciso")
    suggested_actions: List[GenUIActionOption] = Field(default_factory=list, description="Acoes transacionais HITL")



