"""
Testes Unitarios da Fase 6 (Roadmap Sentinel-AURA):
Journal de Comandos Persist-First & Idempotencia Transacional (SQLite WAL).

Valida:
1. Inicializacao SQLite WAL (PRAGMA journal_mode=WAL, synchronous=NORMAL, busy_timeout=5000),
   resolucao de caminhos (AURA_COMMAND_JOURNAL_DB_PATH, AURA_DATA_DIR, %ProgramData%) e
   garantia Persist-First (durante a execucao da callback o status no banco SQLite em disco
   ja e RUNNING).
2. Idempotencia e bloqueio de reexecucao duplicada (execute_idempotent e begin_command).
3. Concorrencia multi-thread (5 threads disparando o mesmo comando simultaneamente ->
   exatamente 1 executa a rotina de negocio e 4 sao bloqueadas como already_running ou replay).
4. Falha de execucao (RUNNING -> FAILED) e retentativa controlada (allow_retry=True e False).
5. Crash recovery (recover_interrupted_commands transitando RUNNING -> INTERRUPTED_BY_CRASH)
   e retomada segura apos recuperacao.
6. Ciclo completo nos endpoints FastAPI (/actions/execute, /actions/rollback,
   /actions/journal, /actions/journal/recover) e compatibilidade com Action Vouchers.
7. Exportacoes lazy loading PEP 562 em core/__init__.py e ausencia total de travessoes.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import core
from core.aura_api import (
    create_aura_app,
    set_command_journal,
)
from core.aura_engine import AuraEngine, AuraSessionMemory
from core.command_journal import (
    AuraCommandJournal,
    CommandAcquisitionResult,
    CommandJournalEntry,
    CommandJournalError,
    CommandJournalStatus,
    get_command_journal,
    reset_command_journal,
)
from core.schemas.idempotency import generate_action_id, generate_tool_call_id

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture(autouse=True)
def _clean_journal_singleton(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    """Isola o singleton global e garante banco SQLite temporario limpo entre cada teste."""
    default_test_db = tmp_path / "isolated_default_journal.db"
    monkeypatch.setenv("AURA_COMMAND_JOURNAL_DB_PATH", str(default_test_db))
    reset_command_journal()
    set_command_journal(None)
    yield
    reset_command_journal()
    set_command_journal(None)


# =============================================================================
# 1. SQLITE WAL, RESOLUCAO DE CAMINHOS E GARANTIA PERSIST-FIRST EM DISCO
# =============================================================================


class TestSQLiteWALAndPersistFirstGuarantee:
    """Valida modo SQLite WAL, pragmas e persistencia previa do estado RUNNING em disco."""

    def test_sqlite_wal_mode_and_pragmas_on_disk(self, tmp_path: Path) -> None:
        """Verifica que o banco em disco ativa journal_mode=WAL, synchronous=NORMAL e busy_timeout=5000."""
        db_file = tmp_path / "aura_command_journal.db"
        journal = AuraCommandJournal(db_path=db_file)

        assert db_file.exists()
        assert journal.get_journal_mode() == "wal"

        pragmas = journal.get_pragma_info()
        assert pragmas["journal_mode"] == "wal"
        assert pragmas["synchronous"] == 1  # 1 = NORMAL no SQLite
        assert pragmas["busy_timeout"] == 5000
        journal.close()

    def test_resolve_default_db_path_precedence(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verifica a hierarquia de resolucao de caminho do banco SQLite."""
        # 1. Override explicito via AURA_COMMAND_JOURNAL_DB_PATH
        explicit_db = tmp_path / "custom" / "journal_explicit.db"
        monkeypatch.setenv("AURA_COMMAND_JOURNAL_DB_PATH", str(explicit_db))
        assert AuraCommandJournal.resolve_default_db_path() == str(explicit_db)

        # 2. Override via AURA_DATA_DIR
        monkeypatch.delenv("AURA_COMMAND_JOURNAL_DB_PATH", raising=False)
        data_dir = tmp_path / "aura_data"
        monkeypatch.setenv("AURA_DATA_DIR", str(data_dir))
        assert AuraCommandJournal.resolve_default_db_path() == str(
            data_dir / "aura_command_journal.db"
        )

        # 3. Fallback padrao (%ProgramData%\Aura\data\aura_command_journal.db no Windows)
        monkeypatch.delenv("AURA_DATA_DIR", raising=False)
        monkeypatch.setenv("PROGRAMDATA", str(tmp_path / "ProgramData"))
        resolved = AuraCommandJournal.resolve_default_db_path()
        assert resolved.endswith("aura_command_journal.db")

    def test_persist_first_status_is_running_on_disk_during_callback(
        self, tmp_path: Path
    ) -> None:
        """
        Prova o protocolo Persist-First: enquanto a funcao de negocio esta executando,
        uma leitura independente diretamente no arquivo SQLite em disco ja enxerga
        o registro com status == 'RUNNING'.
        """
        db_file = tmp_path / "persist_first_proof.db"
        journal = AuraCommandJournal(db_path=db_file)
        cmd_key = "voucher:act_persist_01:execute"

        observed_on_disk_during_execution: dict[str, Any] = {}

        def _business_callback() -> dict[str, Any]:
            # Abre uma conexao SQLite totalmente separada para inspecionar o disco
            with sqlite3.connect(str(db_file), timeout=5.0) as external_conn:
                external_conn.row_factory = sqlite3.Row
                row = external_conn.execute(
                    "SELECT * FROM aura_command_journal WHERE command_key = ?",
                    (cmd_key,),
                ).fetchone()
                assert row is not None, "Registro deveria existir em disco ANTES do fim da callback!"
                observed_on_disk_during_execution["status"] = row["status"]
                observed_on_disk_during_execution["attempt_count"] = row["attempt_count"]
                observed_on_disk_during_execution["actor"] = row["actor"]
                observed_on_disk_during_execution["completed_at"] = row["completed_at"]
            return {"confirmacao_erp": "PED-998877", "litros": 15000}

        res = journal.execute_idempotent(
            command_key=cmd_key,
            fn=_business_callback,
            action_id="act_persist_01",
            action_type="mutation",
            actor="gerente_pista",
            request_payload={"litros": 15000, "combustivel": "DIESEL S10"},
        )

        # Verifica o que foi observado no disco DURANTE a execucao da callback
        assert observed_on_disk_during_execution["status"] == CommandJournalStatus.RUNNING.value
        assert observed_on_disk_during_execution["attempt_count"] == 1
        assert observed_on_disk_during_execution["actor"] == "gerente_pista"
        assert observed_on_disk_during_execution["completed_at"] is None

        # Verifica o estado final apos o retorno da callback
        assert res.acquired is True
        assert res.executed is True
        assert res.status == CommandJournalStatus.COMPLETED.value
        assert res.result_payload == {"confirmacao_erp": "PED-998877", "litros": 15000}

        final_entry = journal.get_entry(cmd_key)
        assert final_entry is not None
        assert final_entry.status == CommandJournalStatus.COMPLETED.value
        assert final_entry.completed_at is not None
        journal.close()


# =============================================================================
# 2. IDEMPOTENCIA E BLOQUEIO DE REEXECUCAO DUPLICADA
# =============================================================================


class TestIdempotencyAndReplayProtection:
    """Valida replay idempotente e prevencao de efeitos colaterais duplicados."""

    def test_begin_command_and_complete_prevent_reexecution(self, tmp_path: Path) -> None:
        """Verifica o ciclo manual begin_command -> complete_command -> replay idempotente."""
        journal = AuraCommandJournal(db_path=tmp_path / "manual_cycle.db")
        cmd_key = "voucher:act_100:execute"

        # 1. Primeira reivindicacao: adquire lock atomico como RUNNING
        acq1 = journal.begin_command(
            command_key=cmd_key,
            action_id="act_100",
            action_type="mutation",
            actor="gerente_01",
            request_payload={"valor": 500.0},
        )
        assert acq1.acquired is True
        assert acq1.already_running is False
        assert acq1.already_completed is False
        assert acq1.entry.status == CommandJournalStatus.RUNNING.value

        # 2. Tentativa concorrente enquanto RUNNING: bloqueada imediatamente
        acq_running = journal.begin_command(
            command_key=cmd_key,
            action_id="act_100",
            action_type="mutation",
            actor="gerente_01",
        )
        assert acq_running.acquired is False
        assert acq_running.already_running is True
        assert acq_running.already_completed is False

        # 3. Conclusao do comando com recibo
        completed = journal.complete_command(
            command_key=cmd_key,
            result_payload={"voucher_id": "vch_abc", "status": "APPROVED"},
        )
        assert completed.status == CommandJournalStatus.COMPLETED.value
        assert completed.result_payload == {"voucher_id": "vch_abc", "status": "APPROVED"}

        # 4. Nova chamada apos COMPLETED: retorna replay idempotente sem adquirir execucao
        acq_replay = journal.begin_command(
            command_key=cmd_key,
            action_id="act_100",
            action_type="mutation",
            actor="gerente_01",
            request_payload={"valor": 99999.0},
        )
        assert acq_replay.acquired is False
        assert acq_replay.already_completed is True
        assert acq_replay.replayed is True
        assert acq_replay.already_running is False
        assert acq_replay.result_payload == {"voucher_id": "vch_abc", "status": "APPROVED"}
        assert acq_replay.entry.attempt_count == 1
        journal.close()

    def test_execute_idempotent_calls_side_effect_only_once(self, tmp_path: Path) -> None:
        """Garante que execute_idempotent executa a callback apenas 1 vez em multiplas chamadas."""
        journal = AuraCommandJournal(db_path=tmp_path / "exec_idem.db")
        cmd_key = "voucher:act_200:execute"
        execution_counter = 0

        def _side_effect() -> dict[str, Any]:
            nonlocal execution_counter
            execution_counter += 1
            return {"exec_num": execution_counter, "protocolo": "ERP-200"}

        res1 = journal.execute_idempotent(
            command_key=cmd_key,
            fn=_side_effect,
            action_id="act_200",
            actor="operador_01",
        )
        res2 = journal.execute_idempotent(
            command_key=cmd_key,
            fn=_side_effect,
            action_id="act_200",
            actor="operador_01",
        )
        res3 = journal.execute_idempotent(
            command_key=cmd_key,
            fn=_side_effect,
            action_id="act_200",
            actor="operador_01",
        )

        assert execution_counter == 1
        assert res1.acquired is True
        assert res1.executed is True
        assert res1.replayed is False

        assert res2.acquired is False
        assert res2.executed is False
        assert res2.already_completed is True
        assert res2.replayed is True
        assert res2.result_payload == {"exec_num": 1, "protocolo": "ERP-200"}

        assert res3.already_completed is True
        assert res3.result_payload == res1.result_payload
        journal.close()


# =============================================================================
# 3. CONCORRENCIA MULTI-THREAD (RACE CONDITION / TOCTOU PROTECTION)
# =============================================================================


class TestMultiThreadConcurrency:
    """Valida protecao contra condicao de corrida quando multiplas threads disparam juntas."""

    def test_five_concurrent_threads_only_one_executes(self, tmp_path: Path) -> None:
        """
        Dispara 5 threads simultaneamente para o mesmo command_key:
        - Exatamente 1 thread adquire e executa a funcao de negocio.
        - As outras 4 threads sao bloqueadas como already_running (ou recebem replay).
        """
        db_file = tmp_path / "concurrent_race.db"
        journal = AuraCommandJournal(db_path=db_file)
        cmd_key = "voucher:act_race_5:execute"

        barrier = threading.Barrier(5)
        call_count = 0
        call_lock = threading.Lock()

        def _slow_erp_mutation() -> dict[str, Any]:
            nonlocal call_count
            with call_lock:
                call_count += 1
            # Mantem o estado RUNNING ativo tempo suficiente para as outras threads colidirem
            time.sleep(0.08)
            return {"status": "APPROVED", "confirmacao": "ERP-SINGLE-EXEC"}

        def _worker(idx: int) -> CommandAcquisitionResult:
            barrier.wait(timeout=5.0)
            return journal.execute_idempotent(
                command_key=cmd_key,
                fn=_slow_erp_mutation,
                action_id="act_race_5",
                action_type="mutation",
                actor=f"thread_{idx}",
            )

        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = [pool.submit(_worker, i) for i in range(5)]
            results = [f.result(timeout=10.0) for f in futures]

        assert call_count == 1, f"A rotina de negocio deveria executar 1 unica vez, executou {call_count}"

        executed_results = [r for r in results if r.acquired and r.executed]
        blocked_or_replayed = [
            r for r in results if (not r.acquired) and (r.already_running or r.already_completed)
        ]

        assert len(executed_results) == 1
        assert len(blocked_or_replayed) == 4

        entry = journal.get_entry(cmd_key)
        assert entry is not None
        assert entry.status == CommandJournalStatus.COMPLETED.value
        assert entry.attempt_count == 1
        journal.close()


# =============================================================================
# 4. FALHA DE EXECUCAO (RUNNING -> FAILED) E RETENTATIVA CONTROLADA
# =============================================================================


class TestExecutionFailureAndControlledRetry:
    """Valida transicao RUNNING -> FAILED em excecao e retentativa com allow_retry."""

    def test_failure_transitions_to_failed_and_controlled_retry_succeeds(
        self, tmp_path: Path
    ) -> None:
        """
        Verifica que:
        1. Uma falha na funcao marca o comando como FAILED e persiste error_message.
        2. Com allow_retry=False, o comando nao e reexecutado.
        3. Com allow_retry=True, attempt_count incrementa para 2 e transita para COMPLETED.
        """
        journal = AuraCommandJournal(db_path=tmp_path / "failure_retry.db")
        cmd_key = "voucher:act_fail_retry:execute"
        attempts = 0

        def _flaky_operation() -> dict[str, Any]:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise RuntimeError("Timeout de conexao com concentrador de bombas")
            return {"status": "APPROVED", "attempt_succeeded": attempts}

        # 1. Primeira tentativa falha e propaga excecao
        with pytest.raises(RuntimeError, match="Timeout de conexao"):
            journal.execute_idempotent(
                command_key=cmd_key,
                fn=_flaky_operation,
                action_id="act_fail_retry",
                actor="gerente_01",
            )

        failed_entry = journal.get_entry(cmd_key)
        assert failed_entry is not None
        assert failed_entry.status == CommandJournalStatus.FAILED.value
        assert "Timeout de conexao" in (failed_entry.error_message or "")
        assert failed_entry.attempt_count == 1

        # 2. Tentativa com allow_retry=False nao deve executar a callback
        no_retry_res = journal.execute_idempotent(
            command_key=cmd_key,
            fn=_flaky_operation,
            action_id="act_fail_retry",
            actor="gerente_01",
            allow_retry=False,
        )
        assert no_retry_res.acquired is False
        assert no_retry_res.executed is False
        assert attempts == 1

        # 3. Tentativa com allow_retry=True reexecuta, incrementa attempt_count=2 e conclui
        retry_res = journal.execute_idempotent(
            command_key=cmd_key,
            fn=_flaky_operation,
            action_id="act_fail_retry",
            actor="gerente_01",
            allow_retry=True,
        )
        assert retry_res.acquired is True
        assert retry_res.executed is True
        assert retry_res.status == CommandJournalStatus.COMPLETED.value
        assert retry_res.entry.attempt_count == 2
        assert retry_res.result_payload == {"status": "APPROVED", "attempt_succeeded": 2}
        assert retry_res.entry.error_message is None
        journal.close()


# =============================================================================
# 5. CRASH RECOVERY (RUNNING -> INTERRUPTED_BY_CRASH)
# =============================================================================


class TestCrashRecovery:
    """Valida deteccao e recuperacao forense de comandos orfaos em RUNNING."""

    def test_recover_interrupted_commands_boot_and_stale_threshold(
        self, tmp_path: Path
    ) -> None:
        """
        Verifica que recover_interrupted_commands transita comandos orfaos em RUNNING
        para INTERRUPTED_BY_CRASH (respeitando stale_after_sec) e permite retry posterior.
        """
        db_file = tmp_path / "crash_recovery.db"
        journal = AuraCommandJournal(db_path=db_file)

        # Cria 2 comandos em RUNNING
        acq_old = journal.begin_command(
            command_key="voucher:act_orphan_old:execute",
            action_id="act_orphan_old",
            action_type="mutation",
            actor="gerente_01",
        )
        acq_fresh = journal.begin_command(
            command_key="voucher:act_fresh:execute",
            action_id="act_fresh",
            action_type="mutation",
            actor="gerente_01",
        )
        assert acq_old.acquired is True
        assert acq_fresh.acquired is True

        # Retrocede o timestamp de act_orphan_old em 300 segundos para simular processo morto
        old_iso = (datetime.now(UTC) - timedelta(seconds=300)).isoformat()
        with sqlite3.connect(str(db_file)) as conn:
            conn.execute(
                "UPDATE aura_command_journal SET started_at = ?, updated_at = ? WHERE command_key = ?",
                (old_iso, old_iso, "voucher:act_orphan_old:execute"),
            )
            conn.commit()

        # 1. Recuperacao com stale_after_sec=60.0 deve recuperar apenas o comando antigo
        recovered_partial = journal.recover_interrupted_commands(stale_after_sec=60.0)
        assert recovered_partial == 1

        entry_old = journal.get_entry("voucher:act_orphan_old:execute")
        entry_fresh = journal.get_entry("voucher:act_fresh:execute")
        assert entry_old is not None
        assert entry_old.status == CommandJournalStatus.INTERRUPTED_BY_CRASH.value
        assert entry_old.error_message is not None

        assert entry_fresh is not None
        assert entry_fresh.status == CommandJournalStatus.RUNNING.value

        # 2. Recuperacao de boot (stale_after_sec=0.0 / default) recupera todos os RUNNING restantes
        recovered_boot = journal.recover_interrupted_commands()
        assert recovered_boot == 1

        entry_fresh_after = journal.get_entry("voucher:act_fresh:execute")
        assert entry_fresh_after is not None
        assert entry_fresh_after.status == CommandJournalStatus.INTERRUPTED_BY_CRASH.value

        # 3. Comando em INTERRUPTED_BY_CRASH pode ser retentado de forma controlada (attempt_count=2)
        retried = journal.execute_idempotent(
            command_key="voucher:act_orphan_old:execute",
            fn=lambda: {"recovered": True, "voucher_id": "vch_rec_01"},
            action_id="act_orphan_old",
            actor="gerente_01",
            allow_retry=True,
        )
        assert retried.acquired is True
        assert retried.status == CommandJournalStatus.COMPLETED.value
        assert retried.entry.attempt_count == 2
        journal.close()


# =============================================================================
# 6. INTEGRACAO FASTAPI (/actions/execute, /actions/rollback, /actions/journal)
# =============================================================================


class TestFastAPIActionsJournalIntegration:
    """Valida o ciclo completo nos endpoints FastAPI e compatibilidade com Action Vouchers."""

    def test_fastapi_execute_idempotency_rollback_and_journal_audit(
        self, tmp_path: Path
    ) -> None:
        """Testa /actions/execute, /actions/rollback, /actions/journal e /actions/journal/recover."""
        mem = AuraSessionMemory(db_path=tmp_path / "api_sessions.db")
        journal = AuraCommandJournal(db_path=tmp_path / "api_journal.db")
        engine = AuraEngine(session_memory=mem)
        app = create_aura_app(engine=engine, command_journal=journal)
        client = TestClient(app)

        act_id = generate_action_id()
        tool_id = generate_tool_call_id()
        sess_id = "sess_fase6_api"

        req_body = {
            "session_id": sess_id,
            "tool_call_id": tool_id,
            "action_id": act_id,
            "action_name": "pedido_combustivel",
            "action_type": "mutation",
            "operator_id": "gerente_pista",
            "operator_role": "gerente",
            "idempotency_key": f"voucher:{act_id}:execute",
            "payload": {"litros": 20000, "combustivel": "GASOLINA COMUM"},
        }

        # 1. Execucao inicial -> HTTP 200 e COMPLETED no journal
        r1 = client.post("/api/v1/aura/actions/execute", json=req_body)
        assert r1.status_code == 200
        v1 = r1.json()
        assert v1["action_id"] == act_id
        assert v1["status"] == "APPROVED"

        # 2. Replay idempotente -> HTTP 200 com o mesmo voucher_id e signature
        r2 = client.post("/api/v1/aura/actions/execute", json=req_body)
        assert r2.status_code == 200
        v2 = r2.json()
        assert v2["voucher_id"] == v1["voucher_id"]
        assert v2["signature"] == v1["signature"]

        # 3. Auditoria do journal via GET /api/v1/aura/actions/journal
        j_resp = client.get(f"/api/v1/aura/actions/journal?action_id={act_id}")
        assert j_resp.status_code == 200
        j_data = j_resp.json()
        assert j_data["completed"] == 1
        assert j_data["total"] == 1
        assert len(j_data["entries"]) == 1
        assert j_data["entries"][0]["command_key"] == f"voucher:{act_id}:execute"
        assert j_data["entries"][0]["status"] == CommandJournalStatus.COMPLETED.value

        # 4. Rollback via POST /api/v1/aura/actions/rollback
        rb_resp = client.post(
            "/api/v1/aura/actions/rollback",
            json={
                "action_id": act_id,
                "session_id": sess_id,
                "tool_call_id": tool_id,
                "operator_id": "gerente_pista",
                "operator_role": "gerente",
                "reason": "Pedido substituido por carreta compartilhada",
            },
        )
        assert rb_resp.status_code == 200
        rb_data = rb_resp.json()
        assert rb_data["status"] == "ROLLED_BACK"
        assert rb_data["journal_status"] == CommandJournalStatus.ROLLED_BACK.value

        # 5. Tentativa de reexecutar voucher ja estornado -> HTTP 409 Conflict
        r_after_rb = client.post("/api/v1/aura/actions/execute", json=req_body)
        assert r_after_rb.status_code == 409

        # 6. Simula comando orfao em RUNNING e aciona POST /api/v1/aura/actions/journal/recover
        orphan_act_id = generate_action_id()
        journal.begin_command(
            command_key=f"voucher:{orphan_act_id}:execute",
            action_id=orphan_act_id,
            action_type="mutation",
            actor="gerente_pista",
        )
        rec_resp = client.post(
            "/api/v1/aura/actions/journal/recover",
            json={"stale_after_sec": 0.0},
        )
        assert rec_resp.status_code == 200
        rec_data = rec_resp.json()
        assert rec_data["recovered_count"] == 1
        assert rec_data["stats"]["interrupted_by_crash"] == 1
        assert rec_data["stats"]["rolled_back"] == 1
        assert rec_data["stats"]["total"] == 2
        journal.close()

    def test_fastapi_execute_returns_409_when_command_already_running(
        self, tmp_path: Path
    ) -> None:
        """Verifica que POST /api/v1/aura/actions/execute retorna HTTP 409 se o comando ja estiver RUNNING."""
        mem = AuraSessionMemory(db_path=tmp_path / "conflict_sessions.db")
        journal = AuraCommandJournal(db_path=tmp_path / "conflict_journal.db")
        engine = AuraEngine(session_memory=mem)
        app = create_aura_app(engine=engine, command_journal=journal)
        client = TestClient(app)

        act_id = generate_action_id()
        tool_id = generate_tool_call_id()
        cmd_key = f"voucher:{act_id}:execute"

        # Pre-reivindica o comando como RUNNING simulando outra thread em execucao
        journal.begin_command(
            command_key=cmd_key,
            action_id=act_id,
            action_type="mutation",
            actor="gerente_01",
        )

        resp = client.post(
            "/api/v1/aura/actions/execute",
            json={
                "session_id": "sess_conflict",
                "tool_call_id": tool_id,
                "action_id": act_id,
                "action_name": "pedido_combustivel",
                "action_type": "mutation",
                "operator_id": "gerente_01",
                "operator_role": "gerente",
                "payload": {"litros": 10000},
            },
        )
        assert resp.status_code == 409
        assert "RUNNING" in resp.json()["detail"]
        journal.close()

    def test_fastapi_execute_marks_journal_failed_on_business_exception(
        self, tmp_path: Path
    ) -> None:
        """Verifica que excecao em _dispatch_business_action transita o journal para FAILED e retorna HTTP 500."""
        mem = AuraSessionMemory(db_path=tmp_path / "err_sessions.db")
        journal = AuraCommandJournal(db_path=tmp_path / "err_journal.db")
        engine = AuraEngine(session_memory=mem)
        app = create_aura_app(engine=engine, command_journal=journal)
        client = TestClient(app)

        act_id = generate_action_id()
        tool_id = generate_tool_call_id()

        with patch(
            "core.aura_api._dispatch_business_action",
            side_effect=RuntimeError("Erro fatal no ERP local"),
        ):
            resp = client.post(
                "/api/v1/aura/actions/execute",
                json={
                    "session_id": "sess_err",
                    "tool_call_id": tool_id,
                    "action_id": act_id,
                    "action_name": "pedido_combustivel",
                    "action_type": "mutation",
                    "operator_id": "gerente_01",
                    "operator_role": "gerente",
                    "payload": {"litros": 10000},
                },
            )
            assert resp.status_code == 500

        entry = journal.get_entry(f"voucher:{act_id}:execute")
        assert entry is not None
        assert entry.status == CommandJournalStatus.FAILED.value
        assert "Erro fatal no ERP local" in (entry.error_message or "")
        journal.close()


# =============================================================================
# 7. EXPORTACOES PEP 562 E AUSENCIA ESTRITA DE TRAVESSOES
# =============================================================================


class TestExportsAndCodeHygiene:
    """Valida exportacoes no pacote core e ausencia total de travessoes."""

    def test_core_lazy_exports_for_command_journal(self) -> None:
        """Verifica se todos os simbolos da Fase 6 estao exportados em core/__init__.py."""
        assert core.AuraCommandJournal is AuraCommandJournal
        assert core.CommandJournalEntry is CommandJournalEntry
        assert core.CommandJournalStatus is CommandJournalStatus
        assert core.CommandAcquisitionResult is CommandAcquisitionResult
        assert core.get_command_journal is get_command_journal
        assert callable(core.set_command_journal)
        assert callable(core.reset_command_journal)

        # Valida erro para transicoes invalidas
        j = AuraCommandJournal(db_path=":memory:")
        with pytest.raises(CommandJournalError):
            j.complete_command("inexistente")
        with pytest.raises(CommandJournalError):
            j.fail_command("inexistente", "erro")
        with pytest.raises(CommandJournalError):
            j.mark_rolled_back("inexistente")
        j.close()

    def test_zero_travessoes_in_phase6_files(self) -> None:
        """Garante ausencia total de travessoes (\\u2014 e \\u2013) nos arquivos da Fase 6."""
        target_files = [
            PROJECT_ROOT / "core" / "command_journal.py",
            PROJECT_ROOT / "core" / "__init__.py",
            PROJECT_ROOT / "core" / "aura_api.py",
            PROJECT_ROOT / "tests" / "unit" / "test_command_journal_idempotency.py",
            PROJECT_ROOT / "tests" / "unit" / "test_action_vouchers.py",
            PROJECT_ROOT / "ROADMAP_SENTINEL_AURA.md",
            PROJECT_ROOT / "docs" / "ROADMAP_SENTINEL_AURA.md",
        ]
        for file_path in target_files:
            assert file_path.exists(), f"Arquivo esperado nao encontrado: {file_path}"
            content = file_path.read_text(encoding="utf-8")
            assert "\u2014" not in content, f"Travessao (em-dash) detectado em {file_path.name}"
            assert "\u2013" not in content, f"Travessao (en-dash) detectado em {file_path.name}"
