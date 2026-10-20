"""
Hub de Conectores de Dados Abertos Governamentais da AURA.
Exporta adaptadores para ANP, CONFAZ, BACEN SGS, Circuit Breaker e Cache Relacional Local.
Zero travessoes em todo o modulo.
"""

from core.integrations.public_data.anp_connector import AnpPublicDataConnector
from core.integrations.public_data.bacen_connector import BacenSgsConnector
from core.integrations.public_data.base import (
    BasePublicDataConnector,
    CircuitState,
    ConnectorFetchResult,
    PublicDataCircuitBreaker,
)
from core.integrations.public_data.confaz_connector import ConfazPmpfConnector
from core.integrations.public_data.repository import (
    PublicDataRepository,
    get_public_data_repository,
)

__all__ = [
    "AnpPublicDataConnector",
    "BacenSgsConnector",
    "BasePublicDataConnector",
    "CircuitState",
    "ConfazPmpfConnector",
    "ConnectorFetchResult",
    "PublicDataCircuitBreaker",
    "PublicDataRepository",
    "get_public_data_repository",
]
