"""
Módulo de Idempotência Criptográfica e Rastreabilidade da AURA (GenUI / SDUI).
Padronização de UUID v4 para tool_call_id e action_id.
Mitigação de Agência Excessiva (OWASP LLM03) e Duplo Envio.
"""

from __future__ import annotations

import re
import uuid
from typing import Any, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator

# Regex oficial RFC 4122 para UUID v4 (8-4-4-4-12 hexadecimais com versão 4 e variante 8, 9, a ou b)
UUID4_PATTERN = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
UUID4_REGEX = re.compile(UUID4_PATTERN)

# Padrão estrito para detecção e extração de prefixos seguros (ex: call, act, tool_call)
# Requer identificador alfanumérico iniciando com letra, de 1 a 32 caracteres
SAFE_PREFIX_PATTERN = r"^[a-zA-Z][a-zA-Z0-9_]{0,31}$"
SAFE_PREFIX_REGEX = re.compile(SAFE_PREFIX_PATTERN)

# Prefixos canônicos autorizados para chamadas de ferramentas e ações transacionais
VALID_TOOL_CALL_PREFIXES = ("call", "tool_call", "tool")
VALID_ACTION_PREFIXES = ("act", "action")


def generate_uuid4() -> str:
    """Gera um UUID v4 canônico criptograficamente seguro no padrão RFC 4122."""
    return str(uuid.uuid4())


def generate_tool_call_id(prefix: str = "call_") -> str:
    """Gera um tool_call_id canônico no formato [prefixo]UUID_v4."""
    return f"{prefix}{generate_uuid4()}"


def generate_action_id(prefix: str = "act_") -> str:
    """Gera um action_id canônico no formato [prefixo]UUID_v4."""
    return f"{prefix}{generate_uuid4()}"


def is_valid_uuid4(val: Any, allow_prefix: bool = True) -> bool:
    """
    Valida se o valor fornecido é uma string contendo um UUID v4 válido RFC 4122.
    Se allow_prefix=True, tolera prefixos seguros validados contra SAFE_PREFIX_REGEX.
    Rejeita injeções arbitrárias, caracteres de controle ou formatações adulteradas.
    """
    if not isinstance(val, str) or not val.strip():
        return False

    raw_val = val.strip()
    if "_" in raw_val:
        if not allow_prefix:
            return False
        prefix, _, uuid_candidate = raw_val.rpartition("_")
        if not SAFE_PREFIX_REGEX.match(prefix):
            return False
        raw_val = uuid_candidate

    if not UUID4_REGEX.match(raw_val):
        return False

    try:
        parsed = uuid.UUID(raw_val, version=4)
        return parsed.version == 4
    except (ValueError, AttributeError):
        return False


def validate_tool_call_id(val: Any, require_prefix: bool = False) -> bool:
    """
    Valida se o identificador de chamada de ferramenta atende ao padrão UUID v4.
    Requer que, se prefixado, utilize um prefixo de ferramenta canônico ('call_', 'tool_call_', 'tool_').
    Rejeita explicitamente prefixos de ação ('act_') ou injeções arbitrárias.
    """
    if not isinstance(val, str) or not val.strip():
        return False

    raw_val = val.strip()
    if "_" in raw_val:
        prefix, _, uuid_candidate = raw_val.rpartition("_")
        if prefix not in VALID_TOOL_CALL_PREFIXES:
            return False
        return is_valid_uuid4(uuid_candidate, allow_prefix=False)

    if require_prefix:
        return False
    return is_valid_uuid4(raw_val, allow_prefix=False)


def validate_action_id(val: Any, require_prefix: bool = False) -> bool:
    """
    Valida se o identificador de ação transacional atende ao padrão UUID v4.
    Requer que, se prefixado, utilize um prefixo de ação canônico ('act_', 'action_').
    Rejeita explicitamente prefixos de ferramenta ('call_') ou injeções arbitrárias.
    """
    if not isinstance(val, str) or not val.strip():
        return False

    raw_val = val.strip()
    if "_" in raw_val:
        prefix, _, uuid_candidate = raw_val.rpartition("_")
        if prefix not in VALID_ACTION_PREFIXES:
            return False
        return is_valid_uuid4(uuid_candidate, allow_prefix=False)

    if require_prefix:
        return False
    return is_valid_uuid4(raw_val, allow_prefix=False)


class IdempotencyKey(BaseModel):
    """Envelope de rastreabilidade e idempotência transacional para GenUI."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    tool_call_id: str = Field(..., description="UUID v4 da invocação da ferramenta (ex: call_<uuid4>)")
    action_id: Optional[str] = Field(default=None, description="UUID v4 da ação transacional específica (ex: act_<uuid4>)")

    @field_validator("tool_call_id")
    @classmethod
    def check_tool_call_id(cls, v: str) -> str:
        if not validate_tool_call_id(v):
            raise ValueError(f"tool_call_id inválido: '{v}' não é um UUID v4 válido ou possui prefixo incompatível")
        return v

    @field_validator("action_id")
    @classmethod
    def check_action_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not validate_action_id(v):
            raise ValueError(f"action_id inválido: '{v}' não é um UUID v4 válido ou possui prefixo incompatível")
        return v

