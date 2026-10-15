"""Modulo de Adaptadores de ERP (Open Posto Architecture).

AURA Universal Posto Schema (AUPS): Bloco 2.
Exporta interfaces abstratas, adaptadores e utilitarios de comunicacao com ERPs.
"""

from core.adapters.erp.base import (
    BaseERPAdapter,
    ERPAdapterError,
    ERPConnectionError,
    ERPQueryError,
    normalize_date_filter,
)
from core.adapters.erp.mock_adapter import MockERPAdapter

__all__ = [
    "BaseERPAdapter",
    "ERPAdapterError",
    "ERPConnectionError",
    "ERPQueryError",
    "MockERPAdapter",
    "normalize_date_filter",
]
