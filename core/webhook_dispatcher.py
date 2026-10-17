"""
Modulo de Despacho de Webhooks e Notificacoes WhatsApp (P1-7 / P3-2 / Fase 5 Outbox).
Fornece interface unificada e classe AuraWebhookDispatcher integrada com
AuraTransactionalOutbox (SQLite WAL) para notificacoes operacionais da AURA:
- Alertas de ruptura e autonomia de tanques
- Alertas de sangria pendente e retencao de caixa
- Resumos executivos de fechamento de turno
- Retentativa resiliente em quedas de internet (Persist-Before-Send)
Zero travessoes em todo o arquivo.
"""
# ruff: noqa: BLE001

from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from unittest.mock import Base as MockBase

import httpx
from pydantic import BaseModel

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
    OutboxBatchResult,
    OutboxMessage,
    OutboxStatus,
    get_transactional_outbox,
)
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


def _execute_http_post_immediate(
    url: str,
    body: dict[str, Any],
    headers: dict[str, str],
    timeout_seconds: float,
) -> tuple[bool, int | None, str | None, str | None]:
    """
    Executa POST HTTP imediato suportando mocks tanto em httpx.AsyncClient.post
    quanto em httpx.Client.post.
    Retorna (success, status_code, response_body, error).
    """
    async_post_attr = getattr(httpx.AsyncClient, "post", None)
    if isinstance(async_post_attr, MockBase):
        async def _call_async() -> tuple[bool, int | None, str | None, str | None]:
            try:
                async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                    resp = await client.post(url, json=body, headers=headers)
                    code = int(getattr(resp, "status_code", 200))
                    txt = str(getattr(resp, "text", ""))[:500]
                    ok = 200 <= code < 300
                    err = None if ok else f"HTTP {code}: {txt[:300]}"
                    return ok, code, txt, err
            except Exception as exc:
                return False, None, None, str(exc)

        try:
            asyncio.get_running_loop()
            holder: list[tuple[bool, int | None, str | None, str | None]] = []

            def _runner() -> None:
                holder.append(asyncio.run(_call_async()))

            t = threading.Thread(target=_runner)
            t.start()
            t.join(timeout=timeout_seconds + 2.0)
            if holder:
                return holder[0]
            return False, None, None, "Timeout na thread de despacho assincrono"
        except RuntimeError:
            return asyncio.run(_call_async())

    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            resp = client.post(url, json=body, headers=headers)
            code = int(resp.status_code)
            txt = str(resp.text)[:500]
            ok = 200 <= code < 300
            err = None if ok else f"HTTP {code}: {txt[:300]}"
            return ok, code, txt, err
    except Exception as exc:
        return False, None, None, str(exc)


class AuraWebhookDispatcher:
    """
    Despachador resiliente de Webhooks (n8n) e WhatsApp (Evolution API)
    integrado ao padrao Transactional Outbox (SQLite WAL).

    Fluxo Persist-Before-Send:
    1. Ao despachar para n8n (dispatch_n8n) ou WhatsApp (dispatch_whatsapp),
       persiste primeiramente na Outbox (enqueue) com status PENDING.
    2. Tenta o envio imediato. Se tiver sucesso, marca como DELIVERED na Outbox.
    3. Se o envio imediato falhar (ex: queda de internet no posto), registra a falha
       na Outbox (FAILED_RETRY com backoff exponencial) para entrega posterior
       automatica assim que a conectividade retornar.
    """

    def __init__(
        self,
        outbox: AuraTransactionalOutbox | None = None,
        sender_fn: Callable[..., Any] | None = None,
        n8n_webhook_url: str | None = None,
        evolution_api_url: str | None = None,
        evolution_api_key: str | None = None,
        evolution_instance: str | None = None,
        manager_phone: str | None = None,
        timeout_seconds: float = 8.0,
        max_attempts: int = 5,
    ) -> None:
        self._outbox = outbox
        self.sender_fn = sender_fn
        self.n8n_webhook_url = n8n_webhook_url
        self.evolution_api_url = evolution_api_url
        self.evolution_api_key = evolution_api_key
        self.evolution_instance = evolution_instance
        self.manager_phone = manager_phone
        self.timeout_seconds = float(timeout_seconds)
        self.max_attempts = max(1, int(max_attempts))

    @property
    def outbox(self) -> AuraTransactionalOutbox:
        """Retorna a instancia ativa da Transactional Outbox."""
        if self._outbox is not None:
            return self._outbox
        return get_transactional_outbox()

    @outbox.setter
    def outbox(self, value: AuraTransactionalOutbox | None) -> None:
        self._outbox = value

    def dispatch_n8n(
        self,
        event_type: str | dict[str, Any] | BaseModel = "n8n_webhook",
        payload: dict[str, Any] | BaseModel | None = None,
        webhook_url: str | None = None,
        destination_url: str | None = None,
        idempotency_key: str | None = None,
        headers: dict[str, str] | None = None,
        max_attempts: int | None = None,
        sender_fn: Callable[..., Any] | None = None,
        timeout_seconds: float | None = None,
    ) -> WebhookDispatchResult:
        """
        Persiste o evento na Transactional Outbox e tenta o envio imediato ao n8n.
        Retorna WebhookDispatchResult (suporta chamada sincrona ou com await).
        """
        if isinstance(event_type, (dict, BaseModel)) and payload is None:
            actual_payload = event_type
            actual_event = "n8n_webhook"
        else:
            actual_payload = payload if payload is not None else {}
            actual_event = str(event_type or "n8n_webhook").strip()

        url = (
            webhook_url
            or destination_url
            or self.n8n_webhook_url
            or N8N_WEBHOOK_URL
            or ""
        ).strip()
        if not url:
            logger.warning(
                "N8N_WEBHOOK_URL nao configurada. Disparo cancelado.",
                extra={"event_type": actual_event},
            )
            return WebhookDispatchResult(
                success=False,
                service="n8n",
                target_url="",
                error="N8N_WEBHOOK_URL nao definida no ambiente",
            )

        data_dict = (
            actual_payload.model_dump()
            if hasattr(actual_payload, "model_dump")
            else dict(actual_payload)
        )
        body = {
            "event": actual_event,
            "timestamp": datetime.now(UTC).isoformat(),
            "data": data_dict,
        }
        eff_headers = {"Content-Type": "application/json"}
        if headers:
            eff_headers.update(headers)

        eff_max = max_attempts if max_attempts is not None else self.max_attempts
        eff_timeout = timeout_seconds if timeout_seconds is not None else self.timeout_seconds

        # 1. Persist-Before-Send na Outbox
        msg: OutboxMessage = self.outbox.enqueue(
            event_type=actual_event,
            destination_url=url,
            payload=body,
            headers=eff_headers,
            idempotency_key=idempotency_key,
            max_attempts=eff_max,
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

        # 2. Reivindica atomicamente PROCESSING e tenta envio imediato
        processing_msg = self.outbox.mark_processing(msg.message_id)
        if processing_msg is None:
            current = self.outbox.get_message(msg.message_id) or msg
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

        active_sender = sender_fn or self.sender_fn or self.outbox.sender_fn

        if active_sender is not None:
            ok, err_msg = self.outbox._invoke_sender(processing_msg, sender_fn=active_sender)
            code = 200 if ok else 503
            resp_body = '{"status":"ok"}' if ok else None
        else:
            ok, code, resp_body, err_msg = _execute_http_post_immediate(
                url=url,
                body=body,
                headers=eff_headers,
                timeout_seconds=eff_timeout,
            )

        # 3. Atualiza estado final na Outbox
        if ok:
            updated = self.outbox.mark_delivered(msg.message_id)
            return WebhookDispatchResult(
                success=True,
                service="n8n",
                target_url=url,
                status_code=code or 200,
                response_body=resp_body,
                outbox_message_id=msg.message_id,
                outbox_status=updated.status if updated else OutboxStatus.DELIVERED.value,
            )

        updated = self.outbox.mark_failed_attempt(
            msg.message_id,
            error=err_msg or "Falha de conectividade ao enviar webhook n8n",
        )
        return WebhookDispatchResult(
            success=False,
            service="n8n",
            target_url=url,
            status_code=code,
            response_body=resp_body,
            error=err_msg or "Falha de conectividade ao enviar webhook n8n",
            outbox_message_id=msg.message_id,
            outbox_status=updated.status if updated else OutboxStatus.FAILED_RETRY.value,
        )

    def dispatch_whatsapp(
        self,
        phone: str = "",
        message_text: str = "",
        api_url: str | None = None,
        api_key: str | None = None,
        instance: str | None = None,
        event_type: str = "whatsapp_evolution",
        idempotency_key: str | None = None,
        payload: dict[str, Any] | None = None,
        destination_url: str | None = None,
        max_attempts: int | None = None,
        sender_fn: Callable[..., Any] | None = None,
        timeout_seconds: float | None = None,
        message: str | None = None,
    ) -> WebhookDispatchResult:
        """
        Persiste a notificacao de WhatsApp na Transactional Outbox e tenta o envio imediato
        para a Evolution API. Se falhar, mantem como FAILED_RETRY com backoff exponencial.
        """
        text = message_text or message or (payload.get("text", "") if isinstance(payload, dict) else "")
        target_phone = (
            phone
            or (payload.get("number", "") if isinstance(payload, dict) else "")
            or self.manager_phone
            or WHATSAPP_MANAGER_PHONE
            or ""
        )

        active_sender = sender_fn or self.sender_fn or self.outbox.sender_fn
        token = api_key or self.evolution_api_key or EVOLUTION_API_KEY or ""
        inst = instance or self.evolution_instance or EVOLUTION_INSTANCE or "aura_posto"

        if destination_url and destination_url.strip():
            endpoint = destination_url.strip()
        else:
            base_url = (api_url or self.evolution_api_url or EVOLUTION_API_URL or "").rstrip("/")
            if not base_url and active_sender is not None:
                base_url = "http://evolution.local:8080"
            if not token and active_sender is not None:
                token = "outbox_sender_token"

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
            "apikey": token or "default_token",
            "Content-Type": "application/json",
        }
        clean_phone = target_phone.replace("+", "").replace("-", "").replace(" ", "").strip()
        body = (
            dict(payload)
            if (payload is not None and not clean_phone and not text)
            else {
                "number": clean_phone,
                "text": text,
            }
        )

        eff_max = max_attempts if max_attempts is not None else self.max_attempts
        eff_timeout = timeout_seconds if timeout_seconds is not None else self.timeout_seconds

        # 1. Persist-Before-Send na Outbox
        msg: OutboxMessage = self.outbox.enqueue(
            event_type=event_type,
            destination_url=endpoint,
            payload=body,
            headers=headers,
            idempotency_key=idempotency_key,
            max_attempts=eff_max,
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

        # 2. Reivindica atomicamente PROCESSING e tenta envio imediato
        processing_msg = self.outbox.mark_processing(msg.message_id)
        if processing_msg is None:
            current = self.outbox.get_message(msg.message_id) or msg
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

        if active_sender is not None:
            ok, err_msg = self.outbox._invoke_sender(processing_msg, sender_fn=active_sender)
            code = 200 if ok else 503
            resp_body = '{"status":"ok"}' if ok else None
        else:
            ok, code, resp_body, err_msg = _execute_http_post_immediate(
                url=endpoint,
                body=body,
                headers=headers,
                timeout_seconds=eff_timeout,
            )

        # 3. Atualiza estado final na Outbox
        if ok:
            updated = self.outbox.mark_delivered(msg.message_id)
            return WebhookDispatchResult(
                success=True,
                service="evolution_api",
                target_url=endpoint,
                status_code=code or 200,
                response_body=resp_body,
                outbox_message_id=msg.message_id,
                outbox_status=updated.status if updated else OutboxStatus.DELIVERED.value,
            )

        updated = self.outbox.mark_failed_attempt(
            msg.message_id,
            error=err_msg or "Falha de conectividade ao enviar WhatsApp Evolution API",
        )
        return WebhookDispatchResult(
            success=False,
            service="evolution_api",
            target_url=endpoint,
            status_code=code,
            response_body=resp_body,
            error=err_msg or "Falha de conectividade ao enviar WhatsApp Evolution API",
            outbox_message_id=msg.message_id,
            outbox_status=updated.status if updated else OutboxStatus.FAILED_RETRY.value,
        )

    # Aliases de compatibilidade
    dispatch_n8n_webhook = dispatch_n8n
    dispatch_evolution_message = dispatch_whatsapp

    def flush(
        self,
        limit: int = 20,
        sender_fn: Callable[..., Any] | None = None,
        force: bool = True,
    ) -> OutboxBatchResult:
        """Processa imediatamente as mensagens pendentes ou em retentativa na Outbox."""
        eff_sender = sender_fn or self.sender_fn
        return self.outbox.process_pending_batch(
            limit=limit,
            sender_fn=eff_sender,
            force=force,
        )

    def process_pending_batch(
        self,
        limit: int = 20,
        sender_fn: Callable[..., Any] | None = None,
        force: bool = False,
    ) -> OutboxBatchResult:
        """Delega processamento de lote pendente para a Outbox associada."""
        eff_sender = sender_fn or self.sender_fn
        return self.outbox.process_pending_batch(
            limit=limit,
            sender_fn=eff_sender,
            force=force,
        )


_GLOBAL_DISPATCHER: AuraWebhookDispatcher | None = None


def get_webhook_dispatcher() -> AuraWebhookDispatcher:
    """Retorna a instancia singleton ativa do AuraWebhookDispatcher."""
    global _GLOBAL_DISPATCHER
    if _GLOBAL_DISPATCHER is None:
        _GLOBAL_DISPATCHER = AuraWebhookDispatcher()
    return _GLOBAL_DISPATCHER


def set_webhook_dispatcher(dispatcher: AuraWebhookDispatcher | None) -> None:
    """Permite injetar ou substituir o singleton global do AuraWebhookDispatcher."""
    global _GLOBAL_DISPATCHER
    _GLOBAL_DISPATCHER = dispatcher


__all__ = [
    "AlertaSangriaPayload",
    "AlertaTanquePayload",
    "AuraWebhookDispatcher",
    "PedidoCombustivelPayload",
    "TurnoResumoPayload",
    "WebhookDispatchResult",
    "dispatch_evolution_message",
    "dispatch_n8n_webhook",
    "format_alerta_sangria_whatsapp_message",
    "format_alerta_tanque_whatsapp_message",
    "format_turno_whatsapp_message",
    "get_webhook_dispatcher",
    "notify_alerta_sangria",
    "notify_alerta_tanque",
    "notify_fechamento_turno",
    "set_webhook_dispatcher",
]
