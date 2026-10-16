"""Modulo de Adaptadores de ERP (Open Posto Architecture).

AURA Universal Posto Schema (AUPS): Bloco 2 e Bloco 4.
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
from core.adapters.erp.postgres_local_adapter import PostgresLocalERPAdapter
from core.adapters.erp.yaml_data_mapper import (
    ColumnMappingConfig,
    ERPMappingConfig,
    FilterConfig,
    JoinConfig,
    TableMappingConfig,
    YAMLDataMapperERPAdapter,
    create_yaml_erp_adapter,
)

__all__ = [
    "BaseERPAdapter",
    "ColumnMappingConfig",
    "ERPAdapterError",
    "ERPConnectionError",
    "ERPMappingConfig",
    "ERPQueryError",
    "FilterConfig",
    "JoinConfig",
    "MockERPAdapter",
    "PostgresLocalERPAdapter",
    "TableMappingConfig",
    "YAMLDataMapperERPAdapter",
    "create_yaml_erp_adapter",
    "normalize_date_filter",
]
