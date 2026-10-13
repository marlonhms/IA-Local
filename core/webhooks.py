"""
Esteira de Webhooks Assincronos para Notificacoes e WhatsApp (P1-7).
Integra o motor cognitivo AURA com n8n e Evolution API para envio automatico
de relatorios executivos de turno, alertas de ruptura de tanques e pedidos de combustivel.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import BaseModel, Field

from config.settings import (
    EVOLUTION_API_KEY,
    EVOLUTION_API_URL,
    EVOLUTION_INSTANCE,
    N8N_WEBHOOK_URL,
    WHATSAPP_MANAGER_PHONE,
)
from core.logger import logger

# =============================================================================
# CONTRATOS PYDANTIC DE PAYLOAD DE WEBHOOKS
# =============================================================================

class WebhookDispatchResult(BaseModel):
    """Resultado do envio de webhook."""
    success: bool
    service: str
    target_url: str
    status_code: int | None = None
    response_body: str | None = None
    error: str | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class TurnoResumoPayload(BaseModel):
    """Payload estruturado do resumo executivo de fechamento de turno."""
    turno_id: str = Field(..., description="Identificador do turno ou data/horario")
    filial_id: str = Field(default="posto_01", description="Identificador da filial do posto")
    data: str = Field(default_factory=lambda: datetime.now(UTC).strftime("%Y-%m-%d"))
    faturamento_total: float = Field(..., description="Faturamento total consolidado em R$")
    litros_vendidos: float = Field(..., description="Volume total vendido em litros")
    quebra_caixa: float = Field(default=0.0, description="Divergencia ou quebra de caixa em R$")
    status_conciliacao: str = Field(default="CONCILIADO", description="Status da auditoria (CONCILIADO, ALERTA)")
    bicos_analisados: int = Field(default=0, description="Quantidade de bicos conferidos")
    observacoes: str | None = None


class AlertaTanquePayload(BaseModel):
    """Payload estruturado para alerta urgente de ruptura de combustivel."""
    tanque_id: str
    combustivel: str
    filial_id: str = "posto_01"
    volume_atual_litros: float
    capacidade_total_litros: float
    autonomia_horas: float
    previsao_esgotamento: str
    urgencia: str = "ALTA"  # BAIXA, MEDIA, ALTA, CRITICA


class PedidoCombustivelPayload(BaseModel):
    """Payload estruturado para pedido de combustivel / carreta."""
    voucher_id: str
    combustivel: str
    litros: float
    fornecedor: str
    filial_id: str = "posto_01"
    data_programada: str
    executado_por: str


# =============================================================================
# DESPACHADORES HTTP ASSINCRONOS
# =============================================================================

async def dispatch_n8n_webhook(
    event_type: str,
    payload: dict[str, Any],
    webhook_url: str | None = None,
    timeout_seconds: float = 8.0,
) -> WebhookDispatchResult:
    """
    Envia payload padronizado via HTTP POST para o endpoint do n8n.
    """
    url = webhook_url or N8N_WEBHOOK_URL
    if not url:
        logger.warning(
            "N8N_WEBHOOK_URL nao configurada. Disparo cancelado.",
            extra={"event_type": event_type},
        )
        return WebhookDispatchResult(
            success=False,
            service="n8n",
            target_url="",
            error="N8N_WEBHOOK_URL nao definida no ambiente",
        )

    body = {
        "event": event_type,
        "timestamp": datetime.now(UTC).isoformat(),
        "data": payload,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            resp = await client.post(url, json=body)
            success = 200 <= resp.status_code < 300
            if not success:
                logger.error(
                    f"Falha no webhook n8n ({resp.status_code}): {resp.text}",
                    extra={"event_type": event_type, "status_code": resp.status_code},
                )
            return WebhookDispatchResult(
                success=success,
                service="n8n",
                target_url=url,
                status_code=resp.status_code,
                response_body=resp.text[:500],
            )
    except Exception as exc:
        logger.error(
            f"Excecao no disparo de webhook n8n: {exc}",
            extra={"event_type": event_type, "error": str(exc)},
        )
        return WebhookDispatchResult(
            success=False,
            service="n8n",
            target_url=url,
            error=str(exc),
        )


async def dispatch_evolution_message(
    phone: str,
    message_text: str,
    api_url: str | None = None,
    api_key: str | None = None,
    instance: str | None = None,
    timeout_seconds: float = 8.0,
) -> WebhookDispatchResult:
    """
    Envia mensagem de texto via Evolution API para WhatsApp corporativo.
    """
    base_url = (api_url or EVOLUTION_API_URL).rstrip("/")
    token = api_key or EVOLUTION_API_KEY
    inst = instance or EVOLUTION_INSTANCE

    if not base_url or not token:
        logger.warning("Evolution API nao configurada. Disparo cancelado.")
        return WebhookDispatchResult(
            success=False,
            service="evolution_api",
            target_url="",
            error="EVOLUTION_API_URL ou EVOLUTION_API_KEY nao definida no ambiente",
        )

    endpoint = f"{base_url}/message/sendText/{inst}"
    headers = {
        "apikey": token,
        "Content-Type": "application/json",
    }
    body = {
        "number": phone.replace("+", "").replace("-", "").replace(" ", "").strip(),
        "text": message_text,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            resp = await client.post(endpoint, json=body, headers=headers)
            success = 200 <= resp.status_code < 300
            if not success:
                logger.error(
                    f"Falha na Evolution API ({resp.status_code}): {resp.text}",
                    extra={"phone": phone, "status_code": resp.status_code},
                )
            return WebhookDispatchResult(
                success=success,
                service="evolution_api",
                target_url=endpoint,
                status_code=resp.status_code,
                response_body=resp.text[:500],
            )
    except Exception as exc:
        logger.error(
            f"Excecao na Evolution API: {exc}",
            extra={"phone": phone, "error": str(exc)},
        )
        return WebhookDispatchResult(
            success=False,
            service="evolution_api",
            target_url=endpoint,
            error=str(exc),
        )


# =============================================================================
# FORMATADORES DE MENSAGENS EXECUTIVAS WHATSAPP
# =============================================================================

def _format_brl(val: float) -> str:
    s = f"{val:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _format_litros(val: float) -> str:
    s = f"{val:,.1f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def format_turno_whatsapp_message(payload: TurnoResumoPayload) -> str:
    """Formata card executivo em texto para envio via WhatsApp."""
    status_icon = "✅" if payload.status_conciliacao == "CONCILIADO" else "⚠️"
    msg = (
        f"{status_icon} *AURA // FECHAMENTO DE TURNO EXECUTIVO*\n"
        f"📅 Data: {payload.data} | Turno: {payload.turno_id}\n"
        f"⛽ Filial: {payload.filial_id}\n"
        f"----------------------------------------\n"
        f"💰 Faturamento: R$ {_format_brl(payload.faturamento_total)}\n"
        f"📊 Litros Vendidos: {_format_litros(payload.litros_vendidos)} L\n"
        f"⚖️ Quebra/Divergência: R$ {_format_brl(payload.quebra_caixa)}\n"
        f"🎯 Status: {payload.status_conciliacao}\n"
        f"🔌 Bicos Auditados: {payload.bicos_analisados}\n"
    )
    if payload.observacoes:
        msg += f"\n📝 Obs: {payload.observacoes}"
    return msg


def format_alerta_tanque_whatsapp_message(payload: AlertaTanquePayload) -> str:
    """Formata alerta de risco de esgotamento de combustível."""
    urg_icon = "🚨" if payload.urgencia in ("ALTA", "CRITICA") else "⚠️"
    return (
        f"{urg_icon} *AURA // ALERTA DE RUPTURA DE COMBUSTÍVEL*\n"
        f"⛽ Combustível: {payload.combustivel}\n"
        f"🏷️ Tanque: {payload.tanque_id} (Filial {payload.filial_id})\n"
        f"----------------------------------------\n"
        f"📦 Nível Atual: {payload.volume_atual_litros:,.0f} L / {payload.capacidade_total_litros:,.0f} L\n"
        f"⏳ Autonomia Estimada: {payload.autonomia_horas:.1f} horas\n"
        f"⏰ Esgotamento Previsto: {payload.previsao_esgotamento}\n"
        f"🚨 Prioridade: {payload.urgencia}\n"
        f"\n💡 Ação sugerida: Autorizar pedido de carreta no painel da AURA."
    )


# =============================================================================
# FUNCOES DE ALTO NIVEL PARA NOTIFICACOES INTEGRADAS
# =============================================================================

async def notify_fechamento_turno(
    payload: TurnoResumoPayload,
    phone: str | None = None,
    webhook_url: str | None = None,
) -> dict[str, Any]:
    """
    Despacha resumo de turno para n8n e Evolution API simultaneamente.
    """
    results = {}
    # 1. Envio para n8n
    n8n_res = await dispatch_n8n_webhook(
        event_type="turno_fechamento",
        payload=payload.model_dump(),
        webhook_url=webhook_url,
    )
    results["n8n"] = n8n_res.model_dump()

    # 2. Envio direto para WhatsApp via Evolution API se telefone configurado
    target_phone = phone or WHATSAPP_MANAGER_PHONE
    if target_phone:
        msg_text = format_turno_whatsapp_message(payload)
        evo_res = await dispatch_evolution_message(
            phone=target_phone,
            message_text=msg_text,
        )
        results["evolution"] = evo_res.model_dump()

    return results


async def notify_alerta_tanque(
    payload: AlertaTanquePayload,
    phone: str | None = None,
    webhook_url: str | None = None,
) -> dict[str, Any]:
    """
    Despacha alerta de autonomia critica para n8n e Evolution API.
    """
    results = {}
    n8n_res = await dispatch_n8n_webhook(
        event_type="alerta_tanque_critico",
        payload=payload.model_dump(),
        webhook_url=webhook_url,
    )
    results["n8n"] = n8n_res.model_dump()

    target_phone = phone or WHATSAPP_MANAGER_PHONE
    if target_phone:
        msg_text = format_alerta_tanque_whatsapp_message(payload)
        evo_res = await dispatch_evolution_message(
            phone=target_phone,
            message_text=msg_text,
        )
        results["evolution"] = evo_res.model_dump()

    return results
