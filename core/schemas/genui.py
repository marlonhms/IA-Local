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
from typing import Any, Dict, List, Literal, Optional
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
