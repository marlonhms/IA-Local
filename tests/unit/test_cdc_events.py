"""
Testes unitarios para o Change Data Capture (CDC) Orientado a Eventos (P2-2).
Valida scripts/cdc_triggers.sql, parsing de notificacoes pg_notify, fila de
deduplicacao, despertar instantaneo (< 500ms) com mock de conn.notifies,
fallback gracioso para polling de 4 horas (14400s) e ausencia de travessoes.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from config.settings import BASE_DIR
from core.cdc_listener import (
    DEFAULT_CDC_CHANNEL,
    FALLBACK_POLLING_INTERVAL_SECONDS,
    AuraCDCListener,
    parse_cdc_payload,
)


@dataclass
class FakeNotify:
    """Simula objeto psycopg2.extensions.Notify retornado em conn.notifies."""

    channel: str
    payload: str
    pid: int = 1234


class FakeCursor:
    """Cursor simulado para testes de LISTEN e consulta de triggers."""

    def __init__(self, conn: FakePGConnection) -> None:
        self.conn = conn
        self._last_row: tuple[Any, ...] | None = None

    def execute(self, sql: str, params: Any = None) -> None:
        if self.conn.fail_on_listen and "LISTEN" in sql.upper():
            raise RuntimeError("permission denied or connection read-only restriction")
        self.conn.executed_sql.append(sql.strip())
        if "pg_trigger" in sql:
            self._last_row = (1,) if self.conn.trigger_installed else None

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._last_row

    def close(self) -> None:
        pass


class FakePGConnection:
    """Conexao PostgreSQL simulada compativel com LISTEN/NOTIFY do psycopg2."""

    def __init__(
        self,
        queued_payloads: list[str] | None = None,
        fail_on_listen: bool = False,
        fail_on_poll: bool = False,
        trigger_installed: bool = True,
    ) -> None:
        self.notifies: list[FakeNotify] = []
        self._queued_payloads = list(queued_payloads or [])
        self.fail_on_listen = fail_on_listen
        self.fail_on_poll = fail_on_poll
        self.trigger_installed = trigger_installed
        self.executed_sql: list[str] = []
        self.isolation_level: int | None = None
        self.poll_calls: int = 0

    def set_isolation_level(self, level: int) -> None:
        self.isolation_level = level

    def cursor(self) -> FakeCursor:
        return FakeCursor(self)

    def poll(self) -> None:
        self.poll_calls += 1
        if self.fail_on_poll:
            raise OSError("Database socket closed unexpectedly")
        while self._queued_payloads:
            raw = self._queued_payloads.pop(0)
            self.notifies.append(FakeNotify(channel=DEFAULT_CDC_CHANNEL, payload=raw))


@pytest.mark.unit
def test_cdc_triggers_sql_script_structure() -> None:
    """Verifica que scripts/cdc_triggers.sql contem a funcao pg_notify e aviso Clean Room."""
    sql_path = BASE_DIR / "scripts" / "cdc_triggers.sql"
    assert sql_path.exists(), "scripts/cdc_triggers.sql deve existir"

    content = sql_path.read_text(encoding="utf-8")
    assert "notify_aura_cdc_change" in content
    assert "pg_notify('aura_cdc_channel'" in content
    assert "trg_aura_cdc_produtos" in content
    assert "CLEAN ROOM" in content.upper()
    assert "OPT-IN" in content.upper()


@pytest.mark.unit
def test_parse_cdc_payload_variants() -> None:
    """Valida o parsing defensivo de JSON, bytes, dict e strings brutas."""
    raw_json = json.dumps(
        {
            "channel": "aura_cdc_channel",
            "table": "produtos",
            "operation": "UPDATE",
            "codpro": "000105",
            "nompro": "GASOLINA ADITIVADA GRID",
            "preco": 6.19,
            "timestamp": "2026-10-15T12:00:00Z",
        }
    )
    event = parse_cdc_payload(raw_json)
    assert event.table == "produtos"
    assert event.operation == "UPDATE"
    assert event.codpro == "000105"
    assert event.nompro == "GASOLINA ADITIVADA GRID"
    assert event.preco == pytest.approx(6.19)
    assert event.dedup_key == "produtos:000105"

    # Bytes JSON
    event_bytes = parse_cdc_payload(raw_json.encode("utf-8"))
    assert event_bytes.codpro == "000105"

    # String simples (fallback nao-JSON)
    event_plain = parse_cdc_payload("000200")
    assert event_plain.table == "produtos"
    assert event_plain.codpro == "000200"
    assert event_plain.dedup_key == "produtos:000200"


@pytest.mark.unit
def test_cdc_listener_deduplication_queue() -> None:
    """Garante que mutacoes repetidas no mesmo produto sejam coalescidas na fila."""
    listener = AuraCDCListener()

    ev1 = parse_cdc_payload({"table": "produtos", "codpro": "001", "preco": 5.50})
    ev2 = parse_cdc_payload({"table": "produtos", "codpro": "001", "preco": 5.79})
    ev3 = parse_cdc_payload({"table": "produtos", "codpro": "002", "preco": 4.19})

    assert listener.enqueue_event(ev1) is True
    assert listener.enqueue_event(ev2) is False  # Deduplicado (mesma chave produtos:001)
    assert listener.enqueue_event(ev3) is True

    assert listener.pending_count() == 2
    assert listener.total_events_deduplicated == 1

    drained = listener.drain_events()
    assert len(drained) == 2
    assert listener.pending_count() == 0

    by_cod = {e.codpro: e for e in drained}
    assert by_cod["001"].preco == pytest.approx(5.79)
    assert by_cod["002"].preco == pytest.approx(4.19)


@pytest.mark.unit
def test_cdc_listener_instant_wakeup_under_500ms() -> None:
    """
    Valida que o AuraCDCListener desperta em sub-segundo (< 500ms) ao receber
    notificacoes via conn.poll() e conn.notifies.
    """
    payload_1 = json.dumps({"table": "produtos", "operation": "UPDATE", "codpro": "10", "preco": 5.99})
    payload_2 = json.dumps({"table": "produtos", "operation": "UPDATE", "codpro": "10", "preco": 6.09})
    payload_3 = json.dumps({"table": "produtos", "operation": "INSERT", "codpro": "20", "preco": 12.50})

    conn = FakePGConnection(queued_payloads=[payload_1, payload_2, payload_3])
    listener = AuraCDCListener()

    assert listener.setup_listen(conn) is True
    assert listener.mode == "event"
    assert conn.isolation_level == 0
    assert any("LISTEN aura_cdc_channel" in s for s in conn.executed_sql)

    t0 = time.perf_counter()
    should_sync, events = listener.wait_for_change_or_timeout(
        conn,
        timeout_seconds=5.0,
        select_fn=lambda r, w, x, t: (r, [], []),
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert elapsed_ms < 500.0, f"Wakeup CDC excedeu 500ms: {elapsed_ms:.2f}ms"
    assert should_sync is True
    assert len(events) == 2  # codpro 10 (deduplicado) + codpro 20
    assert listener.total_notifications_received == 3
    assert listener.total_events_deduplicated == 1


@pytest.mark.unit
def test_cdc_listener_graceful_fallback_to_long_polling() -> None:
    """
    Garante fallback automatico para modo polling (14400s / 4 horas) quando:
    1. O banco recusa LISTEN ou nao possui triggers no modo Clean Room Read-Only.
    2. Ocorre falha de socket durante poll_notifications.
    """
    assert FALLBACK_POLLING_INTERVAL_SECONDS == 14400

    # Caso 1: Trigger ausente quando require_trigger_installed=True
    conn_no_trigger = FakePGConnection(trigger_installed=False)
    listener_ro = AuraCDCListener(require_trigger_installed=True)
    assert listener_ro.setup_listen(conn_no_trigger) is False
    assert listener_ro.mode == "polling_fallback"
    assert "Clean Room" in (listener_ro.fallback_reason or "")

    slept_intervals: list[float] = []
    should_sync, events = listener_ro.wait_for_change_or_timeout(
        conn_no_trigger,
        sleep_fn=lambda s: slept_intervals.append(s),
    )
    assert should_sync is True
    assert events == []
    assert slept_intervals == [14400.0]

    # Caso 2: Erro na conexao durante poll()
    conn_broken = FakePGConnection(fail_on_poll=True)
    listener_err = AuraCDCListener()
    assert listener_err.setup_listen(conn_broken) is True
    events_err = listener_err.poll_notifications(
        conn_broken,
        timeout_seconds=0.01,
        select_fn=lambda r, w, x, t: (r, [], []),
    )
    assert events_err == []
    assert listener_err.mode == "polling_fallback"


@pytest.mark.unit
def test_zero_em_dashes_in_cdc_files() -> None:
    """Verifica ausencia total de travessoes em todos os arquivos do escopo P2-2."""
    files_to_check = [
        BASE_DIR / "scripts" / "cdc_triggers.sql",
        BASE_DIR / "core" / "cdc_listener.py",
        BASE_DIR / "scripts" / "sync_daemon.py",
        Path(__file__),
    ]
    for path in files_to_check:
        content = path.read_text(encoding="utf-8")
        assert "\u2014" not in content, f"Travessao (em-dash) encontrado em {path}"
        assert "\u2013" not in content, f"Meia-risca (en-dash) encontrada em {path}"
