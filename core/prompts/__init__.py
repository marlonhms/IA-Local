"""Pacote de Prompts Especializados e Diretrizes Cognitivas da AURA (Clean Room Bloco 5).

Centraliza prompts de sistema, personas e orientacoes de linguagem natural.
Garante blindagem juridica absoluta: nenhum schema, tabela ou coluna fisica do ERP e exposta a LLM.
Regra inegociavel: ZERO travessoes em todo o modulo.
"""

from core.prompts.system_prompts import (
    build_help_prompt,
    build_system_prompt,
)

__all__ = [
    "build_help_prompt",
    "build_system_prompt",
]
