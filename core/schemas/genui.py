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
