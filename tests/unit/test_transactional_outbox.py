"""
Testes Unitarios da Fase 5 (Roadmap Sentinel-AURA):
Mensageria Resiliente com Transactional Outbox (SQLite WAL).

Valida:
1. Criacao do banco SQLite em modo WAL (PRAGMA journal_mode=WAL, synchronous=NORMAL, busy_timeout=5000)
   e protocolo Persist-Before-Send (enqueue).
2. Deduplicacao estrita e thread-safe por idempotency_key.
3. Ciclo completo de entrega com sucesso (PENDING -> PROCESSING -> DELIVERED).
4. Falha de rede transiente (FAILED_RETRY com Exponential Backoff + Jitter) seguida de
   entrega bem-sucedida quando a conectividade retorna.
5. Transicao para DEAD_LETTER (DLQ) apos esgotar max_attempts e reabilitacao via requeue_dead_letters().
6. Crash recovery de mensagens orfas presas em PROCESSING (recover_stale_processing).
7. Integracao com AuraWebhookDispatcher (retencao offline na Outbox e entrega online).
8. Endpoints FastAPI (/api/v1/aura/outbox/stats, /messages, /flush, /requeue-dlq).
9. Ausencia estrita de travessoes (\\u2014, \\u2013) em todo o codigo e documentacao da Fase 5.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import sqlite3
import sys
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from core.aura_api import create_aura_app, set_transactional_outbox
from core.aura_engine import AuraEngine, AuraSessionMemory
from core.outbox import (
    AuraTransactionalOutbox,
    OutboxBatchResult,
    OutboxMessage,
    OutboxStatus,
    compute_next_backoff,
    get_transactional_outbox,
    reset_transactional_outbox,
)
from core.webhook_dispatcher import (
    AlertaTanquePayload,
    AuraWebhookDispatcher,
    TurnoResumoPayload,
    notify_alerta_tanque,
    notify_fechamento_turno,
)


@pytest.fixture(autouse=True)
def _clean_outbox_singleton(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    """Isola o singleton global e garante banco temporario limpo entre cada teste."""
    default_test_db = tmp_path / "isolated_default_outbox.db"
    monkeypatch.setenv("AURA_OUTBOX_DB_PATH", str(default_test_db))
    reset_transactional_outbox()
    set_transactional_outbox(None)
    yield
    reset_transactional_outbox()
    set_transactional_outbox(None)


# =============================================================================
# 1. SQLITE WAL, RESOLUCAO DE CAMINHO E PERSIST-BEFORE-SEND (ENQUEUE)
# =============================================================================


class TestSQLiteWALAndPersistBeforeSend:
    """Valida modo SQLite WAL, pragmas de resiliencia e gravacao previa (enqueue)."""

    def test_sqlite_wal_mode_and_pragmas_on_file_db(self, tmp_path: Path) -> None:
        """Verifica que o banco em disco ativa journal_mode=WAL, synchronous=NORMAL e busy_timeout=5000."""
        db_file = tmp_path / "aura_outbox_wal.db"
        outbox = AuraTransactionalOutbox(db_path=db_file)

        assert db_file.exists()
        assert outbox.get_journal_mode() == "wal"

        pragmas = outbox.get_pragma_info()
        assert pragmas["journal_mode"] == "wal"
        assert pragmas["synchronous"] == 1  # 1 = NORMAL no SQLite
        assert pragmas["busy_timeout"] == 5000
        assert pragmas["wal_autocheckpoint"] == 1000
        assert pragmas["journal_size_limit"] == 67108864
        outbox.close()

    def test_enqueue_persists_pending_message_before_network(self, tmp_path: Path) -> None:
        """Garante que enqueue grava a mensagem em disco com status PENDING e metadados completos."""
        db_file = tmp_path / "outbox_enqueue.db"
        outbox = AuraTransactionalOutbox(db_path=db_file)

        payload = {"turno_id": "T-01", "faturamento_total": 42500.50}
        headers = {"X-Station-Id": "posto_01", "Authorization": "Bearer secret"}

        msg = outbox.enqueue(
            event_type="fechamento_turno",
            destination_url="https://n8n.posto.local/webhook/turno",
            payload=payload,
            headers=headers,
            idempotency_key="turno:posto_01:T-01",
            max_attempts=5,
        )

        assert isinstance(msg, OutboxMessage)
        assert msg.message_id
        assert msg.idempotency_key == "turno:posto_01:T-01"
        assert msg.event_type == "fechamento_turno"
        assert msg.destination_url == "https://n8n.posto.local/webhook/turno"
        assert msg.status == OutboxStatus.PENDING.value
        assert msg.attempt_count == 0
        assert msg.max_attempts == 5
        assert msg.payload == payload
        assert msg.headers == headers
        assert msg.created_at
        assert msg.updated_at
        assert msg.delivered_at is None
        assert msg.last_error is None

        # Verifica leitura direta do arquivo SQLite
        loaded = outbox.get_message(msg.message_id)
        assert loaded is not None
        assert loaded.message_id == msg.message_id
        assert loaded.status == "PENDING"
        assert loaded.payload["faturamento_total"] == 42500.50

        stats = outbox.get_stats()
        assert stats["pending"] == 1
        assert stats["total"] == 1
        outbox.close()

    def test_default_path_resolution_and_env_overrides(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Testa resolucao de caminho via AURA_OUTBOX_DB_PATH, AURA_DATA_DIR e padrao ProgramData."""
        # 1. AURA_OUTBOX_DB_PATH explicito
        custom_db = tmp_path / "custom" / "my_outbox.db"
        monkeypatch.setenv("AURA_OUTBOX_DB_PATH", str(custom_db))
        assert AuraTransactionalOutbox.resolve_default_db_path() == str(custom_db)

        # 2. AURA_DATA_DIR quando AURA_OUTBOX_DB_PATH nao esta definido
        monkeypatch.delenv("AURA_OUTBOX_DB_PATH", raising=False)
        data_dir = tmp_path / "aura_data"
        monkeypatch.setenv("AURA_DATA_DIR", str(data_dir))
        assert AuraTransactionalOutbox.resolve_default_db_path() == str(
            data_dir / "aura_outbox.db"
        )

        # 3. Padrao %ProgramData%\Aura\data\aura_outbox.db no Windows ou fallback no POSIX
        monkeypatch.delenv("AURA_DATA_DIR", raising=False)
        fake_progdata = tmp_path / "ProgramData"
        monkeypatch.setenv("PROGRAMDATA", str(fake_progdata))
        import core.outbox as outbox_mod

        if sys.platform == "win32":
            resolved_win = AuraTransactionalOutbox.resolve_default_db_path()
            assert resolved_win == str(fake_progdata / "Aura" / "data" / "aura_outbox.db")
        else:
            resolved_posix = AuraTransactionalOutbox.resolve_default_db_path()
            assert resolved_posix == str(outbox_mod.PROJECT_ROOT / "data" / "aura_outbox.db")

    def test_enqueue_rejects_empty_destination_url(self) -> None:
        """Nao deve permitir enfileirar mensagem sem destination_url."""
        outbox = AuraTransactionalOutbox(db_path=":memory:")
        with pytest.raises(ValueError, match="destination_url"):
            outbox.enqueue(
                event_type="alerta_tanque",
                destination_url="   ",
                payload={"tanque": "01"},
            )
        outbox.close()


# =============================================================================
# 2. DEDUPLICACAO ESTRITA POR IDEMPOTENCY_KEY
# =============================================================================


class TestIdempotencyDeduplication:
    """Valida que idempotency_key impede duplicatas sequenciais e concorrentes."""

    def test_duplicate_idempotency_key_returns_existing_message(self) -> None:
        """Enfileirar duas vezes com a mesma idempotency_key retorna o mesmo registro sem duplicar."""
        outbox = AuraTransactionalOutbox(db_path=":memory:")

        m1 = outbox.enqueue(
            event_type="alerta_tanque",
            destination_url="http://n8n.local/webhook",
            payload={"tanque_id": "TQ-01", "volume": 1500},
            idempotency_key="alerta:posto_01:TQ-01:20261017",
        )
        m2 = outbox.enqueue(
            event_type="alerta_tanque",
            destination_url="http://n8n.local/webhook",
            payload={"tanque_id": "TQ-01", "volume": 1400},
            idempotency_key="alerta:posto_01:TQ-01:20261017",
        )

        assert m1.message_id == m2.message_id
        assert m2.payload["volume"] == 1500
        assert outbox.get_stats()["total"] == 1
        outbox.close()

    def test_concurrent_enqueue_with_same_idempotency_key_is_thread_safe(
        self, tmp_path: Path
    ) -> None:
        """Multiplas threads disparando o mesmo idempotency_key simultaneamente criam apenas 1 registro."""
        outbox = AuraTransactionalOutbox(db_path=tmp_path / "conc_idem.db")
        barrier = threading.Barrier(6)
        results: list[OutboxMessage] = []
        lock = threading.Lock()

        def _worker(idx: int) -> None:
            barrier.wait()
            msg = outbox.enqueue(
                event_type="fechamento_turno",
                destination_url="http://n8n.local/webhook",
                payload={"worker": idx},
                idempotency_key="CONCURRENT_SHIFT_KEY_01",
            )
            with lock:
                results.append(msg)

        threads = [threading.Thread(target=_worker, args=(i,)) for i in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 6
        unique_ids = {m.message_id for m in results}
        assert len(unique_ids) == 1
        assert outbox.get_stats()["total"] == 1
        outbox.close()


# =============================================================================
# 3. CICLO COMPLETO DE SUCESSO E FALHA TRANSIENTE COM BACKOFF EXPONENCIAL
# =============================================================================


class TestBatchDeliveryAndTransientFailure:
    """Testa PENDING -> DELIVERED e FAILED_RETRY com backoff exponencial + recuperacao."""

    def test_successful_delivery_lifecycle(self) -> None:
        """Mensagem PENDING processada com sucesso transita para DELIVERED com delivered_at."""
        outbox = AuraTransactionalOutbox(db_path=":memory:")
        msg = outbox.enqueue(
            event_type="whatsapp_evolution",
            destination_url="http://evolution.local/message/sendText/posto",
            payload={"number": "5511999999999", "text": "Resumo do turno"},
        )

        delivered_calls: list[OutboxMessage] = []

        def _ok_sender(m: OutboxMessage) -> tuple[bool, str | None]:
            delivered_calls.append(m)
            # No momento do envio, o status no banco deve ser PROCESSING
            in_flight = outbox.get_message(m.message_id)
            assert in_flight is not None
            assert in_flight.status == OutboxStatus.PROCESSING.value
            return True, None

        batch = outbox.process_pending_batch(limit=10, sender_fn=_ok_sender)
        assert isinstance(batch, OutboxBatchResult)
        assert batch.processed == 1
        assert batch.delivered == 1
        assert batch.failed_retry == 0
        assert batch.dead_letter == 0
        assert len(delivered_calls) == 1

        updated = outbox.get_message(msg.message_id)
        assert updated is not None
        assert updated.status == OutboxStatus.DELIVERED.value
        assert updated.attempt_count == 1
        assert updated.delivered_at is not None
        assert updated.last_error is None

        stats = outbox.get_stats()
        assert stats == {
            "pending": 0,
            "processing": 0,
            "delivered": 1,
            "failed_retry": 0,
            "dead_letter": 0,
            "total": 1,
        }
        outbox.close()

    def test_exponential_backoff_calculation_and_bounds(self) -> None:
        """Verifica crescimento exponencial, jitter positivo e teto max_delay."""
        b1 = compute_next_backoff(attempt=1, base_delay=2.0, max_delay=300.0, jitter_ratio=0.0)
        b2 = compute_next_backoff(attempt=2, base_delay=2.0, max_delay=300.0, jitter_ratio=0.0)
        b3 = compute_next_backoff(attempt=3, base_delay=2.0, max_delay=300.0, jitter_ratio=0.0)
        b4 = compute_next_backoff(attempt=4, base_delay=2.0, max_delay=300.0, jitter_ratio=0.0)
        b10 = compute_next_backoff(attempt=10, base_delay=2.0, max_delay=300.0, jitter_ratio=0.15)

        assert b1 == 2.0
        assert b2 == 4.0
        assert b3 == 8.0
        assert b4 == 16.0
        assert b10 <= 300.0

        # Com jitter padrao, deve estar entre exp_delay e exp_delay * 1.15
        for _ in range(20):
            bj = AuraTransactionalOutbox.compute_next_backoff(
                attempt=3, base_delay=2.0, max_delay=300.0
            )
            assert 8.0 <= bj <= 8.0 * 1.15

    def test_transient_network_failure_schedules_failed_retry_and_delivers_when_online(
        self,
    ) -> None:
        """
        Simula queda de internet no posto:
        1. 1a tentativa falha -> status FAILED_RETRY, attempt_count=1, next_retry_at > now.
        2. Chamada imediata (antes de next_retry_at) nao reprocessa prematuramente.
        3. Quando o tempo de backoff expira e a internet volta -> entrega e marca DELIVERED.
        """
        outbox = AuraTransactionalOutbox(
            db_path=":memory:",
            base_delay_sec=10.0,
            max_delay_sec=300.0,
            default_max_attempts=5,
        )
        msg = outbox.enqueue(
            event_type="fechamento_turno",
            destination_url="http://n8n.local/webhook/turno",
            payload={"turno": 1, "total": 18500.0},
        )

        network_online = False

        def _flaky_sender(m: OutboxMessage) -> tuple[bool, str | None]:
            if not network_online:
                raise ConnectionError("Internet do posto indisponivel (DNS / Gateway timeout)")
            return True, None

        t_before = time.time()
        res_fail = outbox.process_pending_batch(sender_fn=_flaky_sender)
        assert res_fail.processed == 1
        assert res_fail.delivered == 0
        assert res_fail.failed_retry == 1

        after_fail = outbox.get_message(msg.message_id)
        assert after_fail is not None
        assert after_fail.status == OutboxStatus.FAILED_RETRY.value
        assert after_fail.attempt_count == 1
        assert "Internet do posto indisponivel" in (after_fail.last_error or "")
        assert after_fail.next_retry_at >= t_before + 10.0

        # Tentativa antes do horario agendado (sem force) nao deve selecionar a mensagem
        res_early = outbox.process_pending_batch(sender_fn=_flaky_sender, now=t_before + 2.0)
        assert res_early.processed == 0

        # Internet volta e horario de retry chega
        network_online = True
        res_ok = outbox.process_pending_batch(
            sender_fn=_flaky_sender,
            now=after_fail.next_retry_at + 1.0,
        )
        assert res_ok.processed == 1
        assert res_ok.delivered == 1

        final_msg = outbox.get_message(msg.message_id)
        assert final_msg is not None
        assert final_msg.status == OutboxStatus.DELIVERED.value
        assert final_msg.attempt_count == 2
        assert final_msg.delivered_at is not None
        assert final_msg.last_error is None
        outbox.close()


# =============================================================================
# 4. DEAD LETTER QUEUE (DLQ) E REABILITACAO (REQUEUE_DEAD_LETTERS)
# =============================================================================


class TestDeadLetterQueueAndRequeue:
    """Testa exaustao de max_attempts para DEAD_LETTER e reabilitacao via requeue_dead_letters."""

    def test_exhausted_attempts_moves_to_dead_letter_and_requeue_restores_pending(self) -> None:
        """
        Com max_attempts=3:
        - Tentativa 1 falha -> FAILED_RETRY (attempt_count=1)
        - Tentativa 2 falha -> FAILED_RETRY (attempt_count=2)
        - Tentativa 3 falha -> DEAD_LETTER (attempt_count=3)
        - requeue_dead_letters() -> volta para PENDING (attempt_count=0) e entrega quando online.
        """
        outbox = AuraTransactionalOutbox(
            db_path=":memory:",
            base_delay_sec=0.0,
            default_max_attempts=3,
        )
        msg = outbox.enqueue(
            event_type="alerta_tanque",
            destination_url="http://evolution.local/send",
            payload={"tanque": "TQ-02", "nivel_pct": 6.5},
            max_attempts=3,
        )

        def _always_fail(_m: OutboxMessage) -> tuple[bool, str | None]:
            return False, "HTTP 502 Bad Gateway"

        # Tentativa 1 -> FAILED_RETRY
        r1 = outbox.process_pending_batch(sender_fn=_always_fail)
        assert r1.failed_retry == 1
        assert outbox.get_message(msg.message_id).status == OutboxStatus.FAILED_RETRY.value

        # Tentativa 2 -> FAILED_RETRY
        r2 = outbox.process_pending_batch(sender_fn=_always_fail)
        assert r2.failed_retry == 1
        assert outbox.get_message(msg.message_id).status == OutboxStatus.FAILED_RETRY.value

        # Tentativa 3 -> DEAD_LETTER
        r3 = outbox.process_pending_batch(sender_fn=_always_fail)
        assert r3.dead_letter == 1
        dlq_msg = outbox.get_message(msg.message_id)
        assert dlq_msg is not None
        assert dlq_msg.status == OutboxStatus.DEAD_LETTER.value
        assert dlq_msg.attempt_count == 3
        assert "502 Bad Gateway" in (dlq_msg.last_error or "")

        # Mensagem em DEAD_LETTER nao e processada em novos lotes normais
        r4 = outbox.process_pending_batch(sender_fn=lambda _m: (True, None))
        assert r4.processed == 0

        # Reabilita via requeue_dead_letters()
        requeued_count = outbox.requeue_dead_letters(limit=10)
        assert requeued_count == 1

        requeued_msg = outbox.get_message(msg.message_id)
        assert requeued_msg is not None
        assert requeued_msg.status == OutboxStatus.PENDING.value
        assert requeued_msg.attempt_count == 0
        assert requeued_msg.last_error is None

        # Agora entrega com sucesso
        r5 = outbox.process_pending_batch(sender_fn=lambda _m: (True, None))
        assert r5.delivered == 1
        assert outbox.get_message(msg.message_id).status == OutboxStatus.DELIVERED.value
        outbox.close()


# =============================================================================
# 5. CRASH RECOVERY DE MENSAGENS ORFAS EM PROCESSING
# =============================================================================


class TestStaleProcessingCrashRecovery:
    """Testa recuperacao de mensagens presas em PROCESSING apos queda abrupta do processo."""

    def test_recover_stale_processing_restores_orphaned_messages(self, tmp_path: Path) -> None:
        """Mensagens em PROCESSING com updated_at antigo devem voltar para PENDING e ser entregues."""
        db_file = tmp_path / "crash_recovery.db"
        outbox = AuraTransactionalOutbox(db_path=db_file, stale_processing_timeout_sec=120.0)

        msg_stale = outbox.enqueue(
            event_type="fechamento_turno",
            destination_url="http://n8n.local/webhook",
            payload={"turno": "orfao_1"},
        )
        msg_fresh = outbox.enqueue(
            event_type="fechamento_turno",
            destination_url="http://n8n.local/webhook",
            payload={"turno": "em_andamento_recente"},
        )

        outbox.mark_processing(msg_stale.message_id)
        outbox.mark_processing(msg_fresh.message_id)

        # Retroage updated_at e next_retry_at apenas de msg_stale para 5 minutos atras
        old_iso = (datetime.now(UTC) - timedelta(seconds=300)).isoformat()
        old_epoch = time.time() - 300.0
        with sqlite3.connect(db_file) as conn:
            conn.execute(
                "UPDATE aura_outbox_messages SET updated_at = ?, next_retry_at = ? WHERE message_id = ?",
                (old_iso, old_epoch, msg_stale.message_id),
            )

        recovered = outbox.recover_stale_processing(stale_after_sec=120.0)
        assert recovered == 1

        # msg_stale voltou para PENDING, msg_fresh continua em PROCESSING
        assert outbox.get_message(msg_stale.message_id).status == OutboxStatus.PENDING.value
        assert outbox.get_message(msg_fresh.message_id).status == OutboxStatus.PROCESSING.value

        # process_pending_batch entrega a mensagem recuperada
        batch = outbox.process_pending_batch(sender_fn=lambda _m: (True, None))
        assert batch.delivered == 1
        assert outbox.get_message(msg_stale.message_id).status == OutboxStatus.DELIVERED.value
        outbox.close()

    def test_purge_delivered_and_background_worker(self) -> None:
        """Valida expurgo de mensagens antigas entregues e execucao do worker em background."""
        outbox = AuraTransactionalOutbox(
            db_path=":memory:",
            poll_interval_sec=0.05,
            sender_fn=lambda _m: (True, None),
        )
        m1 = outbox.enqueue("alerta_tanque", "http://n8n.local/1", {"id": 1})
        m2 = outbox.enqueue("alerta_tanque", "http://n8n.local/2", {"id": 2})

        assert outbox.start_worker(poll_interval_sec=0.05) is True
        assert outbox.is_worker_running is True

        # Aguarda o worker drenar as mensagens
        deadline = time.time() + 3.0
        while time.time() < deadline:
            if outbox.get_stats()["delivered"] == 2:
                break
            time.sleep(0.05)

        assert outbox.stop_worker() is True
        assert outbox.is_worker_running is False
        assert outbox.get_stats()["delivered"] == 2

        # Expurga mensagens entregues
        purged = outbox.purge_delivered(older_than_sec=0.0)
        assert purged == 2
        assert outbox.get_stats()["total"] == 0
        assert outbox.get_message(m1.message_id) is None
        assert outbox.get_message(m2.message_id) is None
        outbox.close()

    def test_core_lazy_exports_pep562(self) -> None:
        """Verifica exportacoes PEP 562 exigidas no pacote core."""
        import core

        assert core.AuraTransactionalOutbox is AuraTransactionalOutbox
        assert core.OutboxMessage is OutboxMessage
        assert core.OutboxStatus is OutboxStatus
        assert core.OutboxBatchResult is OutboxBatchResult
        assert core.get_transactional_outbox is get_transactional_outbox


# =============================================================================
# 6. INTEGRACAO COM AuraWebhookDispatcher (OFFLINE -> OUTBOX -> ONLINE)
# =============================================================================


class TestAuraWebhookDispatcherOutboxIntegration:
    """Testa integracao entre AuraWebhookDispatcher e AuraTransactionalOutbox."""

    def test_dispatcher_retains_in_outbox_when_offline_and_delivers_when_online(
        self, tmp_path: Path
    ) -> None:
        """
        Quando a internet do posto cai:
        - dispatch_n8n e dispatch_whatsapp persistem na Outbox (enqueue) antes do envio.
        - Apos falha de rede, os registros permanecem no SQLite com status FAILED_RETRY.
        - Quando a internet volta, dispatcher.flush() entrega todas as mensagens (DELIVERED).
        """
        outbox = AuraTransactionalOutbox(
            db_path=tmp_path / "dispatcher_outbox.db",
            base_delay_sec=30.0,
            default_max_attempts=5,
        )
        internet_up = False
        sent_urls: list[str] = []

        def _simulated_network(msg: OutboxMessage) -> tuple[bool, str | None]:
            if not internet_up:
                raise httpx.ConnectError("Cabo de rede desconectado no posto")
            sent_urls.append(msg.destination_url)
            return True, None

        dispatcher = AuraWebhookDispatcher(
            outbox=outbox,
            sender_fn=_simulated_network,
            n8n_webhook_url="http://n8n.posto.local/webhook/eventos",
            evolution_api_url="http://evolution.posto.local:8080",
            evolution_api_key="evo_secret_key",
            evolution_instance="posto_matriz",
        )

        # 1. Disparo com internet OFFLINE
        res_n8n = dispatcher.dispatch_n8n(
            event_type="fechamento_turno",
            payload={"turno_id": "T-NOITE", "faturamento_total": 31200.0},
            idempotency_key="turno:T-NOITE:n8n",
        )
        assert res_n8n.success is False
        assert res_n8n.outbox_message_id is not None
        assert res_n8n.outbox_status == OutboxStatus.FAILED_RETRY.value

        res_wpp = dispatcher.dispatch_whatsapp(
            phone="5511988887777",
            message_text="*AURA* Fechamento de turno T-NOITE: R$ 31.200,00",
            idempotency_key="turno:T-NOITE:wpp",
        )
        assert res_wpp.success is False
        assert res_wpp.outbox_message_id is not None
        assert res_wpp.outbox_status == OutboxStatus.FAILED_RETRY.value

        # Verifica que ambas as mensagens estao salvas e seguras no SQLite
        stats_offline = outbox.get_stats()
        assert stats_offline["failed_retry"] == 2
        assert stats_offline["delivered"] == 0
        assert stats_offline["total"] == 2

        # 2. Internet do posto volta a ficar ONLINE
        internet_up = True
        flush_result = dispatcher.flush(limit=20, force=True)
        assert flush_result.processed == 2
        assert flush_result.delivered == 2
        assert flush_result.failed_retry == 0
        assert len(sent_urls) == 2

        stats_online = outbox.get_stats()
        assert stats_online["delivered"] == 2
        assert stats_online["failed_retry"] == 0
        outbox.close()

    @pytest.mark.asyncio
    async def test_dispatcher_immediate_online_and_idempotency_deduplication(
        self, tmp_path: Path
    ) -> None:
        """Quando online, marca DELIVERED imediatamente e nao reenvia mesma idempotency_key."""
        outbox = AuraTransactionalOutbox(db_path=tmp_path / "online_outbox.db")
        call_count = 0

        def _counting_sender(_msg: OutboxMessage) -> tuple[bool, str | None]:
            nonlocal call_count
            call_count += 1
            return True, None

        dispatcher = AuraWebhookDispatcher(
            outbox=outbox,
            sender_fn=_counting_sender,
            n8n_webhook_url="http://n8n.local/webhook",
        )

        # 1o envio (tambem valida await no retorno de dispatch_n8n)
        r1 = await dispatcher.dispatch_n8n(
            event_type="alerta_tanque",
            payload={"tanque_id": "TQ-01"},
            idempotency_key="idem_tq_01",
        )
        assert r1.success is True
        assert r1.outbox_status == OutboxStatus.DELIVERED.value
        assert call_count == 1

        # 2o envio com mesma idempotency_key: deduplicado sem chamar rede novamente
        r2 = await dispatcher.dispatch_n8n(
            event_type="alerta_tanque",
            payload={"tanque_id": "TQ-01"},
            idempotency_key="idem_tq_01",
        )
        assert r2.success is True
        assert r2.outbox_message_id == r1.outbox_message_id
        assert r2.outbox_status == OutboxStatus.DELIVERED.value
        assert call_count == 1
        outbox.close()

    @pytest.mark.asyncio
    async def test_legacy_notify_functions_persist_in_outbox_on_network_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Garante 100% de retrocompatibilidade das funcoes notify_fechamento_turno e
        notify_alerta_tanque salvando na Outbox quando httpx falha.
        """
        outbox = AuraTransactionalOutbox(db_path=tmp_path / "legacy_funcs.db")
        set_transactional_outbox(outbox)

        monkeypatch.setattr("core.webhooks.N8N_WEBHOOK_URL", "http://n8n.local/webhook")
        monkeypatch.setattr("core.webhooks.EVOLUTION_API_URL", "http://evo.local:8080")
        monkeypatch.setattr("core.webhooks.EVOLUTION_API_KEY", "evo_key")
        monkeypatch.setattr("core.webhooks.WHATSAPP_MANAGER_PHONE", "5511977776666")

        with patch(
            "httpx.AsyncClient.post",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("Sem rota para o host"),
        ):
            turno_payload = TurnoResumoPayload(
                turno_id="TURNO-01",
                filial_id="posto_01",
                faturamento_total=25000.0,
                litros_vendidos=4200.0,
            )
            res = await notify_fechamento_turno(payload=turno_payload)
            assert res["n8n"]["success"] is False
            assert res["n8n"]["outbox_status"] == "FAILED_RETRY"
            assert res["evolution"]["success"] is False
            assert res["evolution"]["outbox_status"] == "FAILED_RETRY"

            tanque_payload = AlertaTanquePayload(
                tanque_id="TQ-01",
                combustivel="DIESEL S10",
                volume_atual_litros=1200.0,
                capacidade_total_litros=15000.0,
                autonomia_horas=4.0,
                previsao_esgotamento="Hoje 19h",
            )
            res_tq = await notify_alerta_tanque(payload=tanque_payload)
            assert res_tq["n8n"]["outbox_status"] == "FAILED_RETRY"

        stats = outbox.get_stats()
        assert stats["failed_retry"] == 4
        assert stats["total"] == 4
        outbox.close()


# =============================================================================
# 7. ENDPOINTS FASTAPI (/outbox/stats, /messages, /flush, /requeue-dlq)
# =============================================================================


class TestFastAPIOutboxEndpoints:
    """Valida os endpoints HTTP de observabilidade e operacao da Outbox em core/aura_api.py."""

    def test_outbox_stats_messages_flush_and_requeue_dlq_endpoints(
        self, tmp_path: Path
    ) -> None:
        """Testa o fluxo completo de gerenciamento da Outbox via FastAPI TestClient."""
        network_ok = False

        def _controllable_sender(_msg: OutboxMessage) -> tuple[bool, str | None]:
            if not network_ok:
                return False, "Simulated offline state"
            return True, None

        outbox = AuraTransactionalOutbox(
            db_path=tmp_path / "api_outbox.db",
            base_delay_sec=60.0,
            default_max_attempts=2,
            sender_fn=_controllable_sender,
        )

        # Enfileira 2 mensagens: uma com max_attempts=1 (vai para DLQ na 1a falha) e outra com max_attempts=3
        m_dlq = outbox.enqueue(
            event_type="alerta_tanque",
            destination_url="http://n8n.local/dlq_test",
            payload={"tanque": "TQ-DLQ"},
            max_attempts=1,
        )
        m_retry = outbox.enqueue(
            event_type="fechamento_turno",
            destination_url="http://n8n.local/retry_test",
            payload={"turno": "T-RETRY"},
            max_attempts=3,
        )

        mem = AuraSessionMemory(db_path=":memory:")
        engine = AuraEngine(session_memory=mem)
        app = create_aura_app(engine=engine, outbox=outbox)
        client = TestClient(app)

        # 1. GET /api/v1/aura/outbox/stats (inicial: 2 pending)
        r_stats_1 = client.get("/api/v1/aura/outbox/stats")
        assert r_stats_1.status_code == 200
        s1 = r_stats_1.json()
        assert s1["pending"] == 2
        assert s1["total"] == 2

        # 2. POST /api/v1/aura/outbox/flush com rede OFFLINE
        # m_dlq vai para DEAD_LETTER (max_attempts=1), m_retry vai para FAILED_RETRY
        r_flush_fail = client.post("/api/v1/aura/outbox/flush", json={"limit": 10})
        assert r_flush_fail.status_code == 200
        ff_data = r_flush_fail.json()
        assert ff_data["processed"] == 2
        assert ff_data["delivered"] == 0
        assert ff_data["failed_retry"] == 1
        assert ff_data["dead_letter"] == 1

        # 3. GET /api/v1/aura/outbox/messages com filtro status=DEAD_LETTER
        r_msgs_dlq = client.get("/api/v1/aura/outbox/messages?status=DEAD_LETTER&limit=10")
        assert r_msgs_dlq.status_code == 200
        dlq_list = r_msgs_dlq.json()["messages"]
        assert len(dlq_list) == 1
        assert dlq_list[0]["message_id"] == m_dlq.message_id
        assert dlq_list[0]["status"] == "DEAD_LETTER"

        # 4. POST /api/v1/aura/outbox/requeue-dlq -> move m_dlq de DEAD_LETTER para PENDING
        r_requeue = client.post("/api/v1/aura/outbox/requeue-dlq", json={"limit": 50})
        assert r_requeue.status_code == 200
        assert r_requeue.json()["requeued_count"] == 1

        # 5. Rede volta a ficar ONLINE -> POST /api/v1/aura/outbox/flush entrega ambas!
        network_ok = True
        r_flush_ok = client.post("/api/v1/aura/outbox/flush", json={"limit": 10, "force": True})
        assert r_flush_ok.status_code == 200
        f_ok = r_flush_ok.json()
        assert f_ok["processed"] == 2
        assert f_ok["delivered"] == 2

        # 6. GET /api/v1/aura/outbox/stats confirma 2 entregues e 0 pendentes/DLQ
        r_stats_final = client.get("/api/v1/aura/outbox/stats")
        assert r_stats_final.status_code == 200
        sf = r_stats_final.json()
        assert sf["delivered"] == 2
        assert sf["pending"] == 0
        assert sf["failed_retry"] == 0
        assert sf["dead_letter"] == 0
        assert sf["total"] == 2
        assert outbox.get_message(m_retry.message_id).status == "DELIVERED"
        outbox.close()

    def test_outbox_flush_endpoint_respects_force_false_in_body_and_query(
        self, tmp_path: Path
    ) -> None:
        """
        Verifica que POST /api/v1/aura/outbox/flush com force=False (via body ou query param)
        nao processa prematuramente mensagens em FAILED_RETRY cujo next_retry_at esta no futuro.
        """
        should_succeed = False

        def _sender(_msg: OutboxMessage) -> tuple[bool, str | None]:
            return (True, None) if should_succeed else (False, "Offline")

        outbox = AuraTransactionalOutbox(
            db_path=tmp_path / "flush_force_false.db",
            base_delay_sec=120.0,
            default_max_attempts=5,
            sender_fn=_sender,
        )
        msg = outbox.enqueue(
            event_type="fechamento_turno",
            destination_url="http://n8n.local/flush_test",
            payload={"turno": "T-FUTURE"},
        )

        # 1a tentativa falha -> vai para FAILED_RETRY com next_retry_at ~ +120s no futuro
        first_batch = outbox.process_pending_batch()
        assert first_batch.failed_retry == 1
        assert outbox.get_message(msg.message_id).status == OutboxStatus.FAILED_RETRY.value

        should_succeed = True
        mem = AuraSessionMemory(db_path=":memory:")
        engine = AuraEngine(session_memory=mem)
        app = create_aura_app(engine=engine, outbox=outbox)
        client = TestClient(app)

        # 1. Flush com force=False no JSON body -> nao deve processar (next_retry_at no futuro)
        r_body_false = client.post(
            "/api/v1/aura/outbox/flush",
            json={"limit": 10, "force": False},
        )
        assert r_body_false.status_code == 200
        assert r_body_false.json()["processed"] == 0
        assert outbox.get_message(msg.message_id).status == OutboxStatus.FAILED_RETRY.value

        # 2. Flush com ?force=false na query string e body omitindo force -> nao deve processar
        r_query_false = client.post(
            "/api/v1/aura/outbox/flush?force=false",
            json={"limit": 10},
        )
        assert r_query_false.status_code == 200
        assert r_query_false.json()["processed"] == 0
        assert outbox.get_message(msg.message_id).status == OutboxStatus.FAILED_RETRY.value

        # 3. Flush com force=True -> processa e entrega imediatamente
        r_force_true = client.post(
            "/api/v1/aura/outbox/flush",
            json={"limit": 10, "force": True},
        )
        assert r_force_true.status_code == 200
        assert r_force_true.json()["delivered"] == 1
        assert outbox.get_message(msg.message_id).status == OutboxStatus.DELIVERED.value
        outbox.close()


# =============================================================================
# 8. CONCORRENCIA MULTI-INSTANCIA E CASOS DE BORDA DE CRASH RECOVERY
# =============================================================================


class TestConcurrencyAndEdgeCases:
    """Valida atomicidade CAS sob concorrencia, crash recovery com datas invalidas/timezones e tipos complexos."""

    def test_concurrent_process_pending_batch_across_instances_never_double_sends(
        self, tmp_path: Path
    ) -> None:
        """
        Duas instancias independentes de AuraTransactionalOutbox (e multiplas threads)
        chamando process_pending_batch() simultaneamente sobre o mesmo banco SQLite em disco
        nunca enviam a mesma mensagem PENDING mais de uma vez (atomicidade CAS em mark_processing).
        """
        db_file = tmp_path / "concurrent_batch.db"
        seeder = AuraTransactionalOutbox(db_path=db_file)
        enqueued_ids = []
        for i in range(6):
            m = seeder.enqueue(
                event_type="fechamento_turno",
                destination_url=f"http://n8n.local/webhook/{i}",
                payload={"index": i},
            )
            enqueued_ids.append(m.message_id)
        seeder.close()

        sent_lock = threading.Lock()
        sent_message_ids: list[str] = []

        def _slow_sender(msg: OutboxMessage) -> tuple[bool, str | None]:
            time.sleep(0.02)
            with sent_lock:
                sent_message_ids.append(msg.message_id)
            return True, None

        instances = [
            AuraTransactionalOutbox(db_path=db_file, sender_fn=_slow_sender)
            for _ in range(4)
        ]
        barrier = threading.Barrier(4)
        batch_results: list[OutboxBatchResult] = []

        def _runner(inst: AuraTransactionalOutbox) -> None:
            barrier.wait()
            res = inst.process_pending_batch(limit=10)
            with sent_lock:
                batch_results.append(res)

        threads = [threading.Thread(target=_runner, args=(inst,)) for inst in instances]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        for inst in instances:
            inst.close()

        # Cada uma das 6 mensagens deve ter sido enviada exatamente 1 unica vez!
        assert len(sent_message_ids) == 6
        assert sorted(sent_message_ids) == sorted(enqueued_ids)
        assert sum(r.delivered for r in batch_results) == 6

    def test_recover_stale_processing_edge_cases_old_retry_invalid_dates_and_timezones(
        self, tmp_path: Path
    ) -> None:
        """
        Verifica que recover_stale_processing:
        1. NAO recupera prematuramente uma mensagem recem-entrada em PROCESSING (updated_at recente)
           mesmo que seu next_retry_at original seja muito antigo.
        2. Recupera mensagem em PROCESSING cujo updated_at contem formato de data invalido/corrompido.
        3. Calcula corretamente o delta para updated_at com fuso horario explicito (-03:00).
        """
        from datetime import timezone

        db_file = tmp_path / "stale_edge_cases.db"
        outbox = AuraTransactionalOutbox(db_path=db_file, stale_processing_timeout_sec=120.0)

        # Caso 1: Mensagem com next_retry_at antigo (500s atras), mas que acabou de entrar em PROCESSING (updated_at = agora)
        m_fresh_in_flight = outbox.enqueue(
            event_type="fechamento_turno",
            destination_url="http://n8n.local/1",
            payload={"case": "fresh_in_flight_old_retry"},
        )
        outbox.mark_processing(m_fresh_in_flight.message_id)
        with sqlite3.connect(db_file) as conn:
            conn.execute(
                "UPDATE aura_outbox_messages SET next_retry_at = ? WHERE message_id = ?",
                (time.time() - 500.0, m_fresh_in_flight.message_id),
            )

        # Caso 2: Mensagem em PROCESSING com updated_at corrompido/invalido e next_retry_at recente
        m_corrupt_ts = outbox.enqueue(
            event_type="alerta_tanque",
            destination_url="http://n8n.local/2",
            payload={"case": "corrupt_updated_at"},
        )
        outbox.mark_processing(m_corrupt_ts.message_id)
        with sqlite3.connect(db_file) as conn:
            conn.execute(
                "UPDATE aura_outbox_messages SET updated_at = ?, next_retry_at = ? WHERE message_id = ?",
                ("DATA_INVALIDA_CORROMPIDA", time.time(), m_corrupt_ts.message_id),
            )

        # Caso 3: Mensagem em PROCESSING com fuso -03:00 recente (10s atras) -> NAO deve ser recuperada
        tz_brt = timezone(timedelta(hours=-3))
        recent_brt_iso = (datetime.now(tz_brt) - timedelta(seconds=10)).isoformat()
        m_tz_fresh = outbox.enqueue(
            event_type="alerta_tanque",
            destination_url="http://n8n.local/3",
            payload={"case": "tz_fresh"},
        )
        outbox.mark_processing(m_tz_fresh.message_id)
        with sqlite3.connect(db_file) as conn:
            conn.execute(
                "UPDATE aura_outbox_messages SET updated_at = ? WHERE message_id = ?",
                (recent_brt_iso, m_tz_fresh.message_id),
            )

        # Caso 4: Mensagem em PROCESSING com fuso -03:00 antiga (300s atras) -> DEVE ser recuperada
        old_brt_iso = (datetime.now(tz_brt) - timedelta(seconds=300)).isoformat()
        m_tz_stale = outbox.enqueue(
            event_type="alerta_tanque",
            destination_url="http://n8n.local/4",
            payload={"case": "tz_stale"},
        )
        outbox.mark_processing(m_tz_stale.message_id)
        with sqlite3.connect(db_file) as conn:
            conn.execute(
                "UPDATE aura_outbox_messages SET updated_at = ? WHERE message_id = ?",
                (old_brt_iso, m_tz_stale.message_id),
            )

        recovered = outbox.recover_stale_processing(stale_after_sec=120.0)
        assert recovered == 2  # Apenas m_corrupt_ts e m_tz_stale devem ser recuperadas!

        assert outbox.get_message(m_fresh_in_flight.message_id).status == OutboxStatus.PROCESSING.value
        assert outbox.get_message(m_tz_fresh.message_id).status == OutboxStatus.PROCESSING.value
        assert outbox.get_message(m_corrupt_ts.message_id).status == OutboxStatus.PENDING.value
        assert outbox.get_message(m_tz_stale.message_id).status == OutboxStatus.PENDING.value
        outbox.close()

    def test_concurrent_dispatcher_same_idempotency_key_and_dlq_protection(
        self, tmp_path: Path
    ) -> None:
        """
        Verifica que:
        1. Chamadas concorrentes ao AuraWebhookDispatcher com a mesma idempotency_key
           executam apenas 1 envio HTTP real.
        2. Uma mensagem em DEAD_LETTER nao e reenviada por novas chamadas de dispatch_n8n
           com a mesma idempotency_key ate ser reabilitada via requeue_dead_letters().
        """
        outbox = AuraTransactionalOutbox(db_path=tmp_path / "conc_disp.db")
        send_calls = 0
        send_lock = threading.Lock()

        def _slow_ok_sender(_msg: OutboxMessage) -> tuple[bool, str | None]:
            nonlocal send_calls
            time.sleep(0.03)
            with send_lock:
                send_calls += 1
            return True, None

        dispatcher = AuraWebhookDispatcher(
            outbox=outbox,
            sender_fn=_slow_ok_sender,
            n8n_webhook_url="http://n8n.local/webhook",
        )

        barrier = threading.Barrier(4)
        for_threads = []

        def _call_disp() -> None:
            barrier.wait()
            dispatcher.dispatch_n8n(
                event_type="fechamento_turno",
                payload={"turno": "T-CONC"},
                idempotency_key="IDEM_CONC_DISPATCH_01",
            )

        for _ in range(4):
            t = threading.Thread(target=_call_disp)
            for_threads.append(t)
            t.start()
        for t in for_threads:
            t.join()

        assert send_calls == 1
        assert outbox.get_message_by_idempotency_key("IDEM_CONC_DISPATCH_01").status == "DELIVERED"

        # Agora testa protecao de DEAD_LETTER (max_attempts=1 com falha)
        fail_calls = 0

        def _failing_sender(_msg: OutboxMessage) -> tuple[bool, str | None]:
            nonlocal fail_calls
            fail_calls += 1
            return False, "HTTP 500 Internal Error"

        dispatcher_fail = AuraWebhookDispatcher(
            outbox=outbox,
            sender_fn=_failing_sender,
            n8n_webhook_url="http://n8n.local/webhook",
            max_attempts=1,
        )
        r_dlq_1 = dispatcher_fail.dispatch_n8n(
            event_type="alerta_tanque",
            payload={"tanque": "TQ-99"},
            idempotency_key="IDEM_DLQ_LOCK_01",
            max_attempts=1,
        )
        assert r_dlq_1.success is False
        assert r_dlq_1.outbox_status == OutboxStatus.DEAD_LETTER.value
        assert fail_calls == 1

        # Segunda chamada com mesma idempotency_key em DEAD_LETTER nao deve disparar rede novamente
        r_dlq_2 = dispatcher_fail.dispatch_n8n(
            event_type="alerta_tanque",
            payload={"tanque": "TQ-99"},
            idempotency_key="IDEM_DLQ_LOCK_01",
            max_attempts=1,
        )
        assert r_dlq_2.success is False
        assert r_dlq_2.outbox_status == OutboxStatus.DEAD_LETTER.value
        assert fail_calls == 1
        outbox.close()

    def test_enqueue_serializes_decimal_datetime_and_uuid_payloads(self) -> None:
        """Verifica que payloads com Decimal, datetime e UUID sao serializados sem TypeError."""
        import uuid
        from decimal import Decimal

        outbox = AuraTransactionalOutbox(db_path=":memory:")
        uid = uuid.uuid4()
        now_dt = datetime.now(UTC)
        msg = outbox.enqueue(
            event_type="fechamento_turno",
            destination_url="http://n8n.local/webhook",
            payload={
                "faturamento": Decimal("48950.75"),
                "horario": now_dt,
                "voucher_uuid": uid,
            },
        )
        assert msg.payload["faturamento"] == "48950.75"
        assert msg.payload["voucher_uuid"] == str(uid)
        outbox.close()


# =============================================================================
# 9. VERIFICACAO DE ZERO TRAVESSOES NA FASE 5
# =============================================================================


class TestPhase5ZeroDashes:
    """Valida ausencia estrita de travessoes proibidos (\\u2014, \\u2013) nos arquivos da Fase 5."""

    def test_zero_prohibited_dashes_in_phase_5_files(self) -> None:
        base_dir = Path(__file__).resolve().parent.parent.parent
        phase5_files = [
            base_dir / "core" / "outbox.py",
            base_dir / "core" / "webhook_dispatcher.py",
            base_dir / "core" / "webhooks.py",
            base_dir / "core" / "aura_api.py",
            base_dir / "core" / "__init__.py",
            base_dir / "ROADMAP_SENTINEL_AURA.md",
            base_dir / "docs" / "archive" / "roadmaps" / "ROADMAP_SENTINEL_AURA.md",
            base_dir / "tests" / "unit" / "test_transactional_outbox.py",
        ]

        prohibited_bytes = [b"\xe2\x80\x94", b"\xe2\x80\x93"]

        for file_path in phase5_files:
            assert file_path.exists(), f"Arquivo esperado nao encontrado: {file_path}"
            content = file_path.read_bytes()
            for bad in prohibited_bytes:
                assert bad not in content, (
                    f"Arquivo {file_path.name} contem travessao proibido ({bad!r})!"
                )
