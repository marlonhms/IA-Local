"""Pacote de Cartuchos Verticais e Registro Agnostico de Tools (Carbon Core P1.1).

Expoe DomainToolRegistry no nucleo agnostico e cartuchos verticais isolados
(ex: core/packs/fuel_convenience/) mantendo PostoTools como fachada retrocompativel.
Zero travessoes em todo o modulo.
"""

from core.packs.registry import (
    DomainToolRegistry,
    ToolExecutionContext,
    ToolExecutionResult,
    create_default_tool_registry,
)

__all__ = [
    "DomainToolRegistry",
    "ToolExecutionContext",
    "ToolExecutionResult",
    "create_default_tool_registry",
]
