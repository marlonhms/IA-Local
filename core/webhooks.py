"""
Esteira de Webhooks Assincronos para Notificacoes e WhatsApp (P1-7 / Fase 5 Outbox).
Integra o motor cognitivo AURA com n8n, Evolution API e a Transactional Outbox (SQLite WAL)
para envio resiliente de relatorios executivos de turno, alertas de ruptura de tanques
e alertas de sangria mesmo durante quedas de internet no posto.
Zero travessoes em todo o arquivo.
"""
# ruff: noqa: BLE001, S110

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
from core.outbox import (
    AuraTransactionalOutbox,
    OutboxStatus,
    get_transactional_outbox,
)

# =============================================================================
# CONTRATOS PYDANTIC DE PAYLOAD DE WEBHOOKS
# =============================================================================


class WebhookDispatchResult(BaseModel):
    """Resultado do envio de webhook integrado com a Transactional Outbox."""

    success: bool
    service: str
    target_url: str
    status_code: int | None = None
    response_body: str | None = None
    error: str | None = None
    outbox_message_id: str | None = None
    outbox_status: str | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    def __await__(self):
        async def _coro() -> WebhookDispatchResult:
            return self

        return _coro().__await__()


class TurnoResumoPayload(BaseModel):
    """Payload estruturado do resumo executivo de fechamento de turno."""

    turno_id: str = Field(..., description="Identificador do turno ou data/horario")
    filial_id: str = Field(default="posto_01", description="Identificador da filial do posto")
    data: str = Field(default_factory=lambda: datetime.now(UTC).strftime("%Y-%m-%d"))
    faturamento_total: float = Field(..., description="Faturamento total consolidado em R$")
    litros_vendidos: float = Field(..., description="Volume total vendido em litros")
    quebra_caixa: float = Field(default=0.0, description="Divergencia ou quebra de caixa em R$")
    status_conciliacao: str = Field(
        default="CONCILIADO",
        description="Status da auditoria (CONCILIADO, ALERTA)",
    )
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
    compartimentos_5k: int | None = None
    volume_sugerido_litros: float | None = None


class AlertaSangriaPayload(BaseModel):
    """Payload estruturado para alerta de retencao excessiva de caixa ou sangria pendente."""

    caixa_id: str
    filial_id: str = "posto_01"
    saldo_dinheiro: float
    teto_seguro: float
    excesso_dinheiro: float
    minutos_sem_sangria: int
    urgencia: str = "ALTA"  # BAIXA, MEDIA, ALTA, CRITICA
    operador_id: str | None = None


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
# DESPACHADORES HTTP ASSINCRONOS COM PERSIST-BEFORE-SEND (OUTBOX)
# =============================================================================


async def dispatch_n8n_webhook(
    event_type: str,
    payload: dict[str, Any],
    webhook_url: str | None = None,
    timeout_seconds: float = 8.0,
    outbox: AuraTransactionalOutbox | None = None,
    idempotency_key: str | None = None,
    max_attempts: int = 5,
) -> WebhookDispatchResult:
    """
    Persiste primeiramente na Transactional Outbox (SQLite WAL) e envia payload
    padronizado via HTTP POST para o endpoint do n8n.
    Se a rede falhar, mantem na Outbox como FAILED_RETRY com backoff exponencial.
    """
    url = (webhook_url or N8N_WEBHOOK_URL or "").strip()
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
        "data": payload.model_dump() if hasattr(payload, "model_dump") else payload,
    }
    headers = {"Content-Type": "application/json"}

    active_outbox = outbox if outbox is not None else get_transactional_outbox()
    msg = active_outbox.enqueue(
        event_type=event_type,
        destination_url=url,
        payload=body,
        headers=headers,
        idempotency_key=idempotency_key,
        max_attempts=max_attempts,
    )

    if msg.status == OutboxStatus.DELIVERED.value:
        return WebhookDispatchResult(
            success=True,
            service="n8n",
            target_url=url,
            status_code=200,
            response_body="Mensagem ja entregue anteriormente (idempotency_key)",
            outbox_message_id=msg.message_id,
            outbox_status=msg.status,
        )

    if msg.status == OutboxStatus.DEAD_LETTER.value:
        return WebhookDispatchResult(
            success=False,
            service="n8n",
            target_url=url,
            error=msg.last_error or "Mensagem em DEAD_LETTER (max_attempts esgotado)",
            outbox_message_id=msg.message_id,
            outbox_status=msg.status,
        )

    processing_msg = active_outbox.mark_processing(msg.message_id)
    if processing_msg is None:
        current = active_outbox.get_message(msg.message_id) or msg
        if current.status == OutboxStatus.DELIVERED.value:
            return WebhookDispatchResult(
                success=True,
                service="n8n",
                target_url=url,
                status_code=200,
                response_body="Mensagem ja entregue anteriormente (idempotency_key)",
                outbox_message_id=current.message_id,
                outbox_status=current.status,
            )
        return WebhookDispatchResult(
            success=False,
            service="n8n",
            target_url=url,
            error=current.last_error or "Mensagem ja em processamento concorrente na Outbox",
            outbox_message_id=current.message_id,
            outbox_status=current.status,
        )

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            resp = await client.post(url, json=body)
            success = 200 <= resp.status_code < 300
            if success:
                updated = active_outbox.mark_delivered(msg.message_id)
                return WebhookDispatchResult(
                    success=True,
                    service="n8n",
                    target_url=url,
                    status_code=resp.status_code,
                    response_body=resp.text[:500],
                    outbox_message_id=msg.message_id,
                    outbox_status=updated.status if updated else OutboxStatus.DELIVERED.value,
                )

            err_text = f"HTTP {resp.status_code}: {resp.text[:300]}"
            logger.error(
                f"Falha no webhook n8n ({resp.status_code}): {resp.text}",
                extra={"event_type": event_type, "status_code": resp.status_code},
            )
            updated = active_outbox.mark_failed_attempt(msg.message_id, error=err_text)
            return WebhookDispatchResult(
                success=False,
                service="n8n",
                target_url=url,
                status_code=resp.status_code,
                response_body=resp.text[:500],
                error=err_text,
                outbox_message_id=msg.message_id,
                outbox_status=updated.status if updated else OutboxStatus.FAILED_RETRY.value,
            )
    except Exception as exc:
        logger.error(
            f"Excecao no disparo de webhook n8n: {exc}",
            extra={"event_type": event_type, "error": str(exc)},
        )
        updated = active_outbox.mark_failed_attempt(msg.message_id, error=str(exc))
        return WebhookDispatchResult(
            success=False,
            service="n8n",
            target_url=url,
            error=str(exc),
            outbox_message_id=msg.message_id,
            outbox_status=updated.status if updated else OutboxStatus.FAILED_RETRY.value,
        )


async def dispatch_evolution_message(
    phone: str,
    message_text: str,
    api_url: str | None = None,
    api_key: str | None = None,
    instance: str | None = None,
    timeout_seconds: float = 8.0,
    outbox: AuraTransactionalOutbox | None = None,
    idempotency_key: str | None = None,
    event_type: str = "whatsapp_evolution",
    max_attempts: int = 5,
) -> WebhookDispatchResult:
    """
    Persiste primeiramente na Transactional Outbox (SQLite WAL) e envia mensagem
    de texto via Evolution API para WhatsApp corporativo.
    """
    base_url = (api_url or EVOLUTION_API_URL or "").rstrip("/")
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

    active_outbox = outbox if outbox is not None else get_transactional_outbox()
    msg = active_outbox.enqueue(
        event_type=event_type,
        destination_url=endpoint,
        payload=body,
        headers=headers,
        idempotency_key=idempotency_key,
        max_attempts=max_attempts,
    )

    if msg.status == OutboxStatus.DELIVERED.value:
        return WebhookDispatchResult(
            success=True,
            service="evolution_api",
            target_url=endpoint,
            status_code=200,
            response_body="Mensagem ja entregue anteriormente (idempotency_key)",
            outbox_message_id=msg.message_id,
            outbox_status=msg.status,
        )

    if msg.status == OutboxStatus.DEAD_LETTER.value:
        return WebhookDispatchResult(
            success=False,
            service="evolution_api",
            target_url=endpoint,
            error=msg.last_error or "Mensagem em DEAD_LETTER (max_attempts esgotado)",
            outbox_message_id=msg.message_id,
            outbox_status=msg.status,
        )

    processing_msg = active_outbox.mark_processing(msg.message_id)
    if processing_msg is None:
        current = active_outbox.get_message(msg.message_id) or msg
        if current.status == OutboxStatus.DELIVERED.value:
            return WebhookDispatchResult(
                success=True,
                service="evolution_api",
                target_url=endpoint,
                status_code=200,
                response_body="Mensagem ja entregue anteriormente (idempotency_key)",
                outbox_message_id=current.message_id,
                outbox_status=current.status,
            )
        return WebhookDispatchResult(
            success=False,
            service="evolution_api",
            target_url=endpoint,
            error=current.last_error or "Mensagem ja em processamento concorrente na Outbox",
            outbox_message_id=current.message_id,
            outbox_status=current.status,
        )

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            resp = await client.post(endpoint, json=body, headers=headers)
            success = 200 <= resp.status_code < 300
            if success:
                updated = active_outbox.mark_delivered(msg.message_id)
                return WebhookDispatchResult(
                    success=True,
                    service="evolution_api",
                    target_url=endpoint,
                    status_code=resp.status_code,
                    response_body=resp.text[:500],
                    outbox_message_id=msg.message_id,
                    outbox_status=updated.status if updated else OutboxStatus.DELIVERED.value,
                )

            err_text = f"HTTP {resp.status_code}: {resp.text[:300]}"
            logger.error(
                f"Falha na Evolution API ({resp.status_code}): {resp.text}",
                extra={"phone": phone, "status_code": resp.status_code},
            )
            updated = active_outbox.mark_failed_attempt(msg.message_id, error=err_text)
            return WebhookDispatchResult(
                success=False,
                service="evolution_api",
                target_url=endpoint,
                status_code=resp.status_code,
                response_body=resp.text[:500],
                error=err_text,
                outbox_message_id=msg.message_id,
                outbox_status=updated.status if updated else OutboxStatus.FAILED_RETRY.value,
            )
    except Exception as exc:
        logger.error(
            f"Excecao na Evolution API: {exc}",
            extra={"phone": phone, "error": str(exc)},
        )
        updated = active_outbox.mark_failed_attempt(msg.message_id, error=str(exc))
        return WebhookDispatchResult(
            success=False,
            service="evolution_api",
            target_url=endpoint,
            error=str(exc),
            outbox_message_id=msg.message_id,
            outbox_status=updated.status if updated else OutboxStatus.FAILED_RETRY.value,
        )


# =============================================================================
# FORMATADORES DE MENSAGENS EXECUTIVAS WHATSAPP
# =============================================================================


def _format_brl(val: float) -> str:
    s = f"{val:,.2f}"
    # Injeta zero-width space (\u200b) apos o ponto de milhar para neutralizar
    # o detector de links do WhatsApp que quebrava numeros como 18.450 em links azuis.
    return s.replace(",", "X").replace(".", ",").replace("X", ".\u200b")


def _format_litros(val: float) -> str:
    s = f"{val:,.1f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".\u200b")


def _format_date(d_str: str) -> str:
    if not d_str:
        return ""
    try:
        parts = d_str.strip().split("-")
        if len(parts) == 3 and len(parts[0]) == 4:
            return f"{parts[2]}/{parts[1]}/{parts[0]}"
    except Exception:
        pass
    return d_str


def format_turno_whatsapp_message(payload: TurnoResumoPayload) -> str:
    """Formata card executivo em texto profissional e limpo para envio via WhatsApp."""
    data_br = _format_date(payload.data)
    quebra_str = _format_brl(payload.quebra_caixa)
    diff_prefix = "+" if payload.quebra_caixa > 0 else ""

    lines = [
        "*AURA | FECHAMENTO DE TURNO*",
        f"{payload.filial_id} • {payload.turno_id}",
        f"Data: {data_br}",
        "",
        f"• Faturamento Total: R$ {_format_brl(payload.faturamento_total)}",
        f"• Volume Vendido: {_format_litros(payload.litros_vendidos)} L",
        f"• Quebra / Diferença Caixa: {diff_prefix}R$ {quebra_str}",
        f"• Bicos Auditados: {payload.bicos_analisados}",
        f"• Status da Conciliação: {payload.status_conciliacao}",
    ]
    if payload.observacoes:
        lines.append(f"\nObservação: {payload.observacoes.strip()}")
    return "\n".join(lines)


def format_alerta_tanque_whatsapp_message(payload: AlertaTanquePayload) -> str:
    """Formata alerta operacional de tanques em texto limpo e executivo."""
    pct = (
        (payload.volume_atual_litros / payload.capacidade_total_litros * 100)
        if payload.capacidade_total_litros > 0
        else 0.0
    )
    if payload.compartimentos_5k is not None and payload.compartimentos_5k > 0:
        vol_sug = payload.volume_sugerido_litros or (payload.compartimentos_5k * 5000.0)
        acao = (
            f"Ação Recomendada: Autorizar pedido fracionado de "
            f"{payload.compartimentos_5k} compartimento(s) de 5.000 L ({_format_litros(vol_sug)} L)."
        )
    else:
        acao = "Ação Recomendada: Autorizar pedido de carreta no painel de controle."
    lines = [
        "*AURA | ALERTA OPERACIONAL DE TANQUES*",
        f"Filial: {payload.filial_id} • Tanque: {payload.tanque_id}",
        "",
        f"• Combustível: {payload.combustivel}",
        f"• Saldo Atual: {_format_litros(payload.volume_atual_litros)} L / {_format_litros(payload.capacidade_total_litros)} L ({pct:.1f}%)",
        f"• Autonomia Estimada: {payload.autonomia_horas:.1f} horas",
        f"• Previsão de Esgotamento: {payload.previsao_esgotamento}",
        f"• Urgência: {payload.urgencia}",
        "",
        acao,
    ]
    return "\n".join(lines)


def format_alerta_sangria_whatsapp_message(payload: AlertaSangriaPayload) -> str:
    """Formata alerta operacional de sangria de caixa em texto executivo."""
    lines = [
        "*AURA | ALERTA OPERACIONAL DE CAIXA*",
        f"Filial: {payload.filial_id} • Caixa: {payload.caixa_id}",
        "",
        f"• Saldo em Espécie: R$ {_format_brl(payload.saldo_dinheiro)}",
        f"• Teto Seguro de Gaveta: R$ {_format_brl(payload.teto_seguro)}",
        f"• Excesso Retido: R$ {_format_brl(payload.excesso_dinheiro)}",
        f"• Tempo sem Sangria: {payload.minutos_sem_sangria} minutos",
        f"• Urgência: {payload.urgencia}",
        "",
        "Ação Recomendada: Recolher sangria imediata para o cofre seguro de retaguarda.",
    ]
    return "\n".join(lines)


# =============================================================================
# FUNCOES DE ALTO NIVEL PARA NOTIFICACOES INTEGRADAS
# =============================================================================


async def notify_fechamento_turno(
    payload: TurnoResumoPayload,
    phone: str | None = None,
    webhook_url: str | None = None,
    outbox: AuraTransactionalOutbox | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """
    Despacha resumo de turno para n8n e Evolution API simultaneamente com Outbox.
    """
    results: dict[str, Any] = {}
    idem_n8n = f"{idempotency_key}:n8n" if idempotency_key else None
    idem_evo = f"{idempotency_key}:whatsapp" if idempotency_key else None

    # 1. Envio para n8n
    n8n_res = await dispatch_n8n_webhook(
        event_type="turno_fechamento",
        payload=payload.model_dump(),
        webhook_url=webhook_url,
        outbox=outbox,
        idempotency_key=idem_n8n,
    )
    results["n8n"] = n8n_res.model_dump()

    # 2. Envio direto para WhatsApp via Evolution API se telefone configurado
    target_phone = phone or WHATSAPP_MANAGER_PHONE
    if target_phone:
        msg_text = format_turno_whatsapp_message(payload)
        evo_res = await dispatch_evolution_message(
            phone=target_phone,
            message_text=msg_text,
            outbox=outbox,
            idempotency_key=idem_evo,
            event_type="fechamento_turno",
        )
        results["evolution"] = evo_res.model_dump()

    return results


async def notify_alerta_tanque(
    payload: AlertaTanquePayload,
    phone: str | None = None,
    webhook_url: str | None = None,
    outbox: AuraTransactionalOutbox | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """
    Despacha alerta de autonomia critica para n8n e Evolution API com Outbox.
    """
    results: dict[str, Any] = {}
    idem_n8n = f"{idempotency_key}:n8n" if idempotency_key else None
    idem_evo = f"{idempotency_key}:whatsapp" if idempotency_key else None

    n8n_res = await dispatch_n8n_webhook(
        event_type="alerta_tanque_critico",
        payload=payload.model_dump(),
        webhook_url=webhook_url,
        outbox=outbox,
        idempotency_key=idem_n8n,
    )
    results["n8n"] = n8n_res.model_dump()

    target_phone = phone or WHATSAPP_MANAGER_PHONE
    if target_phone:
        msg_text = format_alerta_tanque_whatsapp_message(payload)
        evo_res = await dispatch_evolution_message(
            phone=target_phone,
            message_text=msg_text,
            outbox=outbox,
            idempotency_key=idem_evo,
            event_type="alerta_tanque",
        )
        results["evolution"] = evo_res.model_dump()

    return results


async def notify_alerta_sangria(
    payload: AlertaSangriaPayload,
    phone: str | None = None,
    webhook_url: str | None = None,
    outbox: AuraTransactionalOutbox | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """
    Despacha alerta de retencao excessiva de numerario para n8n e Evolution API com Outbox.
    """
    results: dict[str, Any] = {}
    idem_n8n = f"{idempotency_key}:n8n" if idempotency_key else None
    idem_evo = f"{idempotency_key}:whatsapp" if idempotency_key else None

    n8n_res = await dispatch_n8n_webhook(
        event_type="alerta_sangria_pendente",
        payload=payload.model_dump(),
        webhook_url=webhook_url,
        outbox=outbox,
        idempotency_key=idem_n8n,
    )
    results["n8n"] = n8n_res.model_dump()

    target_phone = phone or WHATSAPP_MANAGER_PHONE
    if target_phone:
        msg_text = format_alerta_sangria_whatsapp_message(payload)
        evo_res = await dispatch_evolution_message(
            phone=target_phone,
            message_text=msg_text,
            outbox=outbox,
            idempotency_key=idem_evo,
            event_type="alerta_sangria",
        )
        results["evolution"] = evo_res.model_dump()

    return results
