"""
Configuracoes e Feature Flags da AURA IntelligentUI & Core Engine.
Fornece suporte a Feature Flag ENABLE_GENUI, alternancia a quente no runtime
e resolucao de precedencia de flags por requisicao (Query Param, Header, Body e Global).
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import os
from typing import Dict, Any, Optional

# =============================================================================
# FEATURE FLAGS GLOBAIS
# =============================================================================

# Leitura inicial a partir da variavel de ambiente ENABLE_GENUI (padrao: True)
_RAW_GENUI_ENV = os.getenv("ENABLE_GENUI", "true").strip().lower()
ENABLE_GENUI: bool = _RAW_GENUI_ENV in ("1", "true", "yes", "on", "t")

# Estado mutavel em tempo de execucao (Runtime Feature Flags)
# Permite acionamento imediato de Circuit Breaker sem reiniciar o servidor
_RUNTIME_FEATURE_FLAGS: Dict[str, Any] = {
    "ENABLE_GENUI": ENABLE_GENUI,
}


def is_genui_enabled() -> bool:
    """
    Retorna o status ativo da feature flag ENABLE_GENUI no runtime.
    """
    return bool(_RUNTIME_FEATURE_FLAGS.get("ENABLE_GENUI", True))


def set_genui_enabled(enabled: bool) -> bool:
    """
    Comuta a quente o valor de ENABLE_GENUI em tempo de execucao.
    """
    global ENABLE_GENUI
    ENABLE_GENUI = bool(enabled)
    _RUNTIME_FEATURE_FLAGS["ENABLE_GENUI"] = ENABLE_GENUI
    return _RUNTIME_FEATURE_FLAGS["ENABLE_GENUI"]


def get_feature_flags() -> Dict[str, Any]:
    """
    Retorna copia do dicionario de feature flags ativas no runtime.
    """
    return dict(_RUNTIME_FEATURE_FLAGS)


def update_feature_flags(flags: Dict[str, Any]) -> Dict[str, Any]:
    """
    Atualiza multiplas feature flags no runtime de forma segura.
    """
    global ENABLE_GENUI
    if not isinstance(flags, dict):
        return dict(_RUNTIME_FEATURE_FLAGS)

    for k, v in flags.items():
        k_upper = str(k).strip().upper()
        if k_upper in ("ENABLE_GENUI", "GENUI"):
            ENABLE_GENUI = bool(v)
            _RUNTIME_FEATURE_FLAGS["ENABLE_GENUI"] = ENABLE_GENUI
        else:
            _RUNTIME_FEATURE_FLAGS[k_upper] = v

    return dict(_RUNTIME_FEATURE_FLAGS)


def resolve_genui_flag(
    query_param: Optional[Any] = None,
    header_val: Optional[str] = None,
    body_val: Optional[bool] = None,
) -> bool:
    """
    Resolve a precedencia estrita para habilitacao da experiencia GenUI:
    1. Query param '?genui=1' (ativa) ou '?genui=0' (desativa)
    2. Header 'X-GenUI-Enabled: 1' ou '0'
    3. Campo no body do request (se fornecido)
    4. Valor global do runtime (is_genui_enabled())
    """
    # 1. Precedencia: Query Param
    if query_param is not None:
        if isinstance(query_param, bool):
            return query_param
        val_str = str(query_param).strip().lower()
        if val_str in ("1", "true", "yes", "on", "t"):
            return True
        if val_str in ("0", "false", "no", "off", "f"):
            return False

    # 2. Precedencia: Header HTTP
    if header_val is not None:
        val_str = str(header_val).strip().lower()
        if val_str in ("1", "true", "yes", "on", "t"):
            return True
        if val_str in ("0", "false", "no", "off", "f"):
            return False

    # 3. Precedencia: Body do Request
    if body_val is not None:
        return bool(body_val)

    # 4. Fallback: Estado global da flag no runtime
    return is_genui_enabled()
