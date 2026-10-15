"""Camada de adaptadores de infraestrutura e integracao externa.

AURA Universal Posto Schema (AUPS): Arquitetura Hexagonal (Ports e Adapters).
Isola comunicacoes de rede, banco de dados e sistemas legados de ERP.
"""

from core.adapters import erp

__all__ = ["erp"]
