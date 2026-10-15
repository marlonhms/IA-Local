"""
Modulo de Change Data Capture (CDC) Orientado a Eventos via PostgreSQL LISTEN/NOTIFY (P2-2).
Implementa escuta assincrona/reativa no canal 'aura_cdc_channel' com:
- Parsing seguro de payloads JSON emitidos por pg_notify (CDCEvent)
- Fila de eventos com deduplicacao em memoria por chave (tabela + codpro)
- Despertar sub-segundo via select.select + conn.poll() + conn.notifies
- Fallback gracioso automatico para polling de intervalo longo (14400s / 4 horas)
  quando o banco opera em modo estrito Read-Only (aura_service_ro) ou sem triggers.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import json
import select
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from core.logger import logger

DEFAULT_CDC_CHANNEL = "aura_cdc_channel"
FALLBACK_POLLING_INTERVAL_SECONDS = 14400  # 4 horas


@dataclass(frozen=True)
class CDCEvent:
    """Representa um evento estruturado de mutacao capturado via pg_notify."""

    table: str = "produtos"
    operation: str = "UPDATE"
    codpro: str | None = None
    nompro: str | None = None
    preco: float | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    raw_payload: dict[str, Any] = field(default_factory=dict)

    @property
    def dedup_key(self) -> str:
        """Chave deterministica para coalescencia de mutacoes repetidas no mesmo item."""
        target_id = (self.codpro or "*").strip().upper()
        return f"{self.table.strip().lower()}:{target_id}"


def parse_cdc_payload(raw_payload: str | bytes | dict[str, Any] | None) -> CDCEvent:
    """
    Realiza o parsing defensivo do payload recebido via pg_notify.
    Aceita JSON valido, dicionario ja deserializado ou string simples (codpro).
    """
    if raw_payload is None:
        return CDCEvent()

    if isinstance(raw_payload, bytes):
        raw_str = raw_payload.decode("utf-8", errors="replace").strip()
    elif isinstance(raw_payload, dict):
        data = dict(raw_payload)
        return _build_event_from_dict(data)
    else:
        raw_str = str(raw_payload).strip()

    if not raw_str:
        return CDCEvent()

    try:
        parsed = json.loads(raw_str)
        if isinstance(parsed, dict):
            return _build_event_from_dict(parsed)
    except (json.JSONDecodeError, TypeError, ValueError):
        pass

    return CDCEvent(
        table="produtos",
        operation="UPDATE",
        codpro=raw_str,
        raw_payload={"raw": raw_str},
    )


def _build_event_from_dict(data: dict[str, Any]) -> CDCEvent:
    """Constroi instancia tipada de CDCEvent a partir de um dicionario JSON."""
    table = str(data.get("table") or "produtos").strip()
    operation = str(data.get("operation") or data.get("op") or "UPDATE").strip().upper()
    raw_cod = data.get("codpro")
    codpro = str(raw_cod).strip() if raw_cod not in (None, "") else None
    raw_nom = data.get("nompro")
    nompro = str(raw_nom).strip() if raw_nom not in (None, "") else None

    preco_val: float | None = None
    if data.get("preco") is not None:
        try:
            preco_val = float(data["preco"])
        except (TypeError, ValueError):
            preco_val = None

    ts = str(data.get("timestamp") or datetime.now(UTC).isoformat())
    return CDCEvent(
        table=table,
        operation=operation,
        codpro=codpro,
        nompro=nompro,
        preco=preco_val,
        timestamp=ts,
        raw_payload=data,
    )


class AuraCDCListener:
    """
    Escutador reativo de Change Data Capture (CDC) via PostgreSQL LISTEN/NOTIFY.
    Comuta automaticamente para modo de polling longo (4 horas) se o banco
    recusar LISTEN, nao possuir triggers instalados ou perder suporte a eventos.
    """

    def __init__(
        self,
        channel: str = DEFAULT_CDC_CHANNEL,
        fallback_interval_seconds: int = FALLBACK_POLLING_INTERVAL_SECONDS,
        require_trigger_installed: bool = False,
    ) -> None:
        self.channel = channel
        self.fallback_interval_seconds = max(1, int(fallback_interval_seconds))
        self.require_trigger_installed = require_trigger_installed
        self.mode: str = "event"
        self.fallback_reason: str | None = None
        self._dedup_queue: dict[str, CDCEvent] = {}
        self.total_notifications_received: int = 0
        self.total_events_deduplicated: int = 0

    def enqueue_event(self, event: CDCEvent) -> bool:
        """
        Enfileira um evento CDC com deduplicacao por (tabela, codpro).
        Retorna True se for uma nova chave na fila ou False se substituiu evento existente.
        """
        key = event.dedup_key
        is_new = key not in self._dedup_queue
        if not is_new:
            self.total_events_deduplicated += 1
        self._dedup_queue[key] = event
        return is_new

    def pending_count(self) -> int:
        """Retorna a quantidade de eventos unicos aguardando processamento."""
        return len(self._dedup_queue)

    def drain_events(self) -> list[CDCEvent]:
        """Retorna todos os eventos deduplicados da fila e limpa o buffer interno."""
        events = list(self._dedup_queue.values())
        self._dedup_queue.clear()
        return events

    def activate_polling_fallback(self, reason: str) -> None:
        """Ativa o modo de fallback gracioso para polling de intervalo longo."""
        self.mode = "polling_fallback"
        self.fallback_reason = reason
        logger.warning(
            f"CDC Listener em modo fallback de polling ({self.fallback_interval_seconds}s): {reason}"
        )

    def check_trigger_installed(self, conn: Any) -> bool:
        """Verifica no catalogo pg_trigger se o gatilho opcional da AURA esta ativo."""
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT 1
                FROM pg_catalog.pg_trigger
                WHERE tgname IN ('trg_aura_cdc_produtos', 'trg_aura_cdc_grupos')
                  AND NOT tgisinternal
                LIMIT 1;
                """
            )
            row = cur.fetchone()
            return bool(row)
        except (AttributeError, OSError, RuntimeError, ValueError):
            return False
        finally:
            cur.close()

    def setup_listen(self, conn: Any) -> bool:
        """
        Configura a conexao PostgreSQL em autocommit e registra LISTEN no canal CDC.
        Em caso de restricao Read-Only estrita, falha de driver ou ausencia de trigger
        (quando exigido), aciona fallback gracioso para polling de 4 horas.
        """
        if conn is None:
            self.activate_polling_fallback("Conexao de banco nula ou indisponivel")
            return False

        try:
            if hasattr(conn, "set_isolation_level"):
                conn.set_isolation_level(0)
            elif hasattr(conn, "autocommit"):
                conn.autocommit = True

            if self.require_trigger_installed and not self.check_trigger_installed(conn):
                self.activate_polling_fallback(
                    "Triggers opcionais CDC ausentes no ERP (modo Clean Room Read-Only)"
                )
                return False

            cur = conn.cursor()
            try:
                cur.execute(f"LISTEN {self.channel};")
            finally:
                cur.close()

            self.mode = "event"
            self.fallback_reason = None
            return True
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as exc:
            self.activate_polling_fallback(f"Falha ao registrar LISTEN {self.channel}: {exc}")
            return False

    def poll_notifications(
        self,
        conn: Any,
        timeout_seconds: float = 1.0,
        select_fn: Callable[..., Any] | None = None,
    ) -> list[CDCEvent]:
        """
        Aguarda notificacoes no socket PostgreSQL ate timeout_seconds, executa conn.poll(),
        extrai conn.notifies com deduplicacao e retorna os eventos prontos para sincronizacao.
        """
        if conn is None or self.mode != "event":
            return []

        wait_fn = select_fn or select.select
        try:
            if getattr(conn, "notifies", None):
                pass
            else:
                try:
                    wait_fn([conn], [], [], max(0.0, float(timeout_seconds)))
                except (TypeError, ValueError, OSError):
                    if timeout_seconds > 0:
                        time.sleep(min(float(timeout_seconds), 0.05))

            if hasattr(conn, "poll"):
                conn.poll()

            notifies = getattr(conn, "notifies", None)
            if notifies is not None:
                while notifies:
                    notify = notifies.pop(0)
                    raw_payload = getattr(notify, "payload", notify)
                    event = parse_cdc_payload(raw_payload)
                    self.total_notifications_received += 1
                    self.enqueue_event(event)
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as exc:
            self.activate_polling_fallback(f"Erro durante poll de notificacoes CDC: {exc}")
            return []

        return self.drain_events()

    def wait_for_change_or_timeout(
        self,
        conn: Any,
        timeout_seconds: float | None = None,
        select_fn: Callable[..., Any] | None = None,
        sleep_fn: Callable[[float], None] | None = None,
    ) -> tuple[bool, list[CDCEvent]]:
        """
        Bloqueia eficientemente ate que um evento LISTEN/NOTIFY chegue ou o timeout expire.
        Se estiver em modo 'polling_fallback', aguarda o intervalo longo (ex: 4h) e sinaliza
        execucao periodica do sync_cycle.
        """
        sleeper = sleep_fn or time.sleep
        if self.mode == "polling_fallback":
            wait_time = (
                float(timeout_seconds)
                if timeout_seconds is not None
                else float(self.fallback_interval_seconds)
            )
            if wait_time > 0:
                sleeper(wait_time)
            return True, []

        effective_timeout = (
            float(timeout_seconds)
            if timeout_seconds is not None
            else float(self.fallback_interval_seconds)
        )
        events = self.poll_notifications(
            conn=conn,
            timeout_seconds=effective_timeout,
            select_fn=select_fn,
        )
        if events:
            return True, events
        if self.mode == "polling_fallback":
            return True, []
        return False, []
