"""
Modulo de Despacho de Webhooks e Notificacoes WhatsApp (P1-7 / P3-2).
Fornece interface unificada para notificacoes operacionais da AURA:
- Alertas de ruptura e autonomia de tanques
- Alertas de sangria pendente e retencao de caixa
- Resumos executivos de fechamento de turno
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

from core.webhooks import (
    AlertaSangriaPayload,
    AlertaTanquePayload,
    PedidoCombustivelPayload,
    TurnoResumoPayload,
    WebhookDispatchResult,
    dispatch_evolution_message,
    dispatch_n8n_webhook,
    format_alerta_sangria_whatsapp_message,
    format_alerta_tanque_whatsapp_message,
    format_turno_whatsapp_message,
    notify_alerta_sangria,
    notify_alerta_tanque,
    notify_fechamento_turno,
)

__all__ = [
    "AlertaSangriaPayload",
    "AlertaTanquePayload",
    "PedidoCombustivelPayload",
    "TurnoResumoPayload",
    "WebhookDispatchResult",
    "dispatch_evolution_message",
    "dispatch_n8n_webhook",
    "format_alerta_sangria_whatsapp_message",
    "format_alerta_tanque_whatsapp_message",
    "format_turno_whatsapp_message",
    "notify_alerta_sangria",
    "notify_alerta_tanque",
    "notify_fechamento_turno",
]
