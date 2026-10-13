"""
Modulo de conveniencia para reexportacao do logging estruturado AURA (P1-6).
Zero travessoes em todo o arquivo.
"""

from core.logging_config import (
    StructuredJsonFormatter,
    current_client_ip,
    current_request_id,
    get_structured_logger,
    setup_logging,
)

logger = get_structured_logger("aura")

__all__ = [
    "StructuredJsonFormatter",
    "current_client_ip",
    "current_request_id",
    "get_structured_logger",
    "logger",
    "setup_logging",
]
