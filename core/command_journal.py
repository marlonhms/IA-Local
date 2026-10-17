"""
Modulo de Journal de Comandos Persist-First & Idempotencia Transacional (SQLite WAL) - Fase 6 (Roadmap Sentinel-AURA).

Implementa o padrao Persist-First Command Journal para blindar a execucao de Action Vouchers
(pedidos de combustivel, sangrias, ajustes de preco e conciliacoes de turno) contra:
1. Duplo clique ou retentativa concorrente de rede (TOCTOU / Race Condition).
2. Reexecucao acidental de comandos ja concluidos (Idempotent Replay).
3. Queda de energia ou reinicializacao abrupta do PDV no meio da transacao (Crash Recovery).

Principios Arquiteturais:
1. Persist-First Atomic Claim (begin_command): Antes de qualquer efeito colateral no ERP
   ou emissao de voucher, o comando e gravado atomicamente no SQLite WAL com status RUNNING
   usando transacao imediata (BEGIN IMMEDIATE).
2. Replay Idempotente: Se command_key ja estiver COMPLETED, retorna o recibo original
   (acquired=False, already_completed=True, replayed=True) sem reexecutar a acao.
3. Bloqueio de Concorrencia: Se command_key ja estiver RUNNING em outra thread/processo,
   bloqueia a chamada concorrente (acquired=False, already_running=True).
4. Crash Recovery Forense: Comandos orfaos em RUNNING apos queda de energia ou reinicio
   sao transicionados para INTERRUPTED_BY_CRASH via recover_interrupted_commands().
5. Armazenamento Padrao: %ProgramData%\\Aura\\data\\aura_command_journal.db com suporte a
   override via AURA_COMMAND_JOURNAL_DB_PATH, AURA_DATA_DIR ou db_path no construtor.
Zero travessoes em todo o arquivo.
"""
# ruff: noqa: BLE001, S110

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
import uuid
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger("aura.command_journal")

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_STALE_RUNNING_SEC: float = 0.0


class CommandJournalError(ValueError, KeyError, RuntimeError):
    """Excecao de dominio para violacoes de estado ou chave inexistente no Command Journal."""

    def __str__(self) -> str:
        return Exception.__str__(self)


class CommandJournalStatus(str, Enum):
    """Estados do ciclo de vida de um comando transacional no Persist-First Journal."""

    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"
    INTERRUPTED_BY_CRASH = "INTERRUPTED_BY_CRASH"


def _parse_iso_to_epoch(ts_str: str | None) -> float | None:
    """Converte string ISO-8601 ou timestamp SQLite para epoch em segundos."""
    if not ts_str:
        return None
    raw = str(ts_str).strip()
    try:
        return float(raw)
    except ValueError:
        pass
    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.timestamp()
    except ValueError:
        try:
            dt = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
            return dt.timestamp()
        except ValueError:
            return None


@dataclass
class CommandJournalEntry:
    """Representa um registro persistido na tabela aura_command_journal."""

    journal_id: str
    command_key: str
    action_id: str
    action_type: str
    actor: str
    status: str = CommandJournalStatus.RUNNING.value
    request_payload_json: str = "{}"
    result_payload_json: str | None = None
    error_message: str | None = None
    attempt_count: int = 1
    started_at: str = ""
    updated_at: str = ""
    completed_at: str | None = None

    @property
    def request_payload(self) -> dict[str, Any]:
        """Retorna o request_payload desserializado como dicionario."""
        try:
            data = json.loads(self.request_payload_json) if self.request_payload_json else {}
            return data if isinstance(data, dict) else {"raw": data}
        except Exception:
            return {"raw": self.request_payload_json}

    @property
    def result_payload(self) -> dict[str, Any] | None:
        """Retorna o result_payload desserializado como dicionario (ou None se ausente)."""
        if self.result_payload_json is None:
            return None
        try:
            data = json.loads(self.result_payload_json)
            return data if isinstance(data, dict) else {"result": data}
        except Exception:
            return {"raw": self.result_payload_json}

    def to_dict(self) -> dict[str, Any]:
        """Converte a entrada do journal para dicionario serializavel em JSON."""
        data = asdict(self)
        data["request_payload"] = self.request_payload
        data["result_payload"] = self.result_payload
        return data

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.to_dict().get(key, default)

    @classmethod
    def from_row(cls, row: sqlite3.Row | dict[str, Any]) -> CommandJournalEntry:
        """Constroi CommandJournalEntry a partir de uma linha do SQLite."""
        return cls(
            journal_id=str(row["journal_id"]),
            command_key=str(row["command_key"]),
            action_id=str(row["action_id"]),
            action_type=str(row["action_type"]),
            actor=str(row["actor"]),
            status=str(row["status"]),
            request_payload_json=str(row["request_payload_json"] or "{}"),
            result_payload_json=row["result_payload_json"],
            error_message=row["error_message"],
            attempt_count=int(row["attempt_count"] or 1),
            started_at=str(row["started_at"]),
            updated_at=str(row["updated_at"]),
            completed_at=row["completed_at"],
        )


@dataclass
class CommandAcquisitionResult:
    """Resultado da reivindicacao atomica Persist-First (begin_command / execute_idempotent)."""

    acquired: bool
    entry: CommandJournalEntry
    already_completed: bool = False
    already_running: bool = False
    already_rolled_back: bool = False
    replayed: bool = False
    executed: bool = False
    reason: str = ""

    @property
    def result_payload(self) -> dict[str, Any] | None:
        """Retorna o payload de resultado da entrada associada."""
        return self.entry.result_payload

    @property
    def status(self) -> str:
        """Retorna o status atual da entrada no journal."""
        return self.entry.status

    @property
    def command_key(self) -> str:
        """Retorna a chave deterministica do comando."""
        return self.entry.command_key

    @property
    def journal_id(self) -> str:
        """Retorna o identificador unico do registro no journal."""
        return self.entry.journal_id

    def to_dict(self) -> dict[str, Any]:
        """Converte o resultado de aquisicao para dicionario serializavel."""
        return {
            "acquired": self.acquired,
            "already_completed": self.already_completed,
            "already_running": self.already_running,
            "already_rolled_back": self.already_rolled_back,
            "replayed": self.replayed,
            "executed": self.executed,
            "reason": self.reason,
            "status": self.status,
            "command_key": self.command_key,
            "journal_id": self.journal_id,
            "result_payload": self.result_payload,
            "entry": self.entry.to_dict(),
        }

    def __getitem__(self, key: str) -> Any:
        d = self.to_dict()
        if key in d:
            return d[key]
        if self.result_payload and key in self.result_payload:
            return self.result_payload[key]
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key: str) -> bool:
        d = self.to_dict()
        if key in d:
            return True
        return bool(self.result_payload and key in self.result_payload)


class AuraCommandJournal:
    """
    Implementacao do padrao Persist-First Command Journal & Idempotencia Transacional
    sobre SQLite em modo WAL.
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
        stale_after_sec: float = DEFAULT_STALE_RUNNING_SEC,
    ) -> None:
        self.stale_after_sec = max(0.0, float(stale_after_sec))
        self._lock = threading.RLock()
        self._shared_conn: sqlite3.Connection | None = None

        if db_path is not None:
            raw_path = str(db_path).strip()
            if raw_path == ":memory:":
                self.db_path = ":memory:"
            else:
                resolved = Path(raw_path)
                resolved.parent.mkdir(parents=True, exist_ok=True)
                self.db_path = str(resolved)
        else:
            self.db_path = self.resolve_default_db_path()

        if self.db_path == ":memory:":
            self._shared_conn = sqlite3.connect(
                ":memory:",
                check_same_thread=False,
                isolation_level=None,
            )
            self._shared_conn.row_factory = sqlite3.Row

        self._init_db()

    @staticmethod
    def resolve_default_db_path() -> str:
        """
        Resolve o caminho padrao do banco SQLite do Command Journal.
        Prioridade:
        1. Variavel de ambiente AURA_COMMAND_JOURNAL_DB_PATH
        2. Variavel de ambiente AURA_DATA_DIR / aura_command_journal.db
        3. %ProgramData%\\Aura\\data\\aura_command_journal.db (no Windows)
        4. Fallback para <PROJECT_ROOT>/data/aura_command_journal.db
        """
        env_path = os.getenv("AURA_COMMAND_JOURNAL_DB_PATH")
        if env_path and env_path.strip():
            cleaned = env_path.strip()
            if cleaned == ":memory:":
                return ":memory:"
            p = Path(cleaned)
            p.parent.mkdir(parents=True, exist_ok=True)
            return str(p)

        data_dir_override = os.getenv("AURA_DATA_DIR")
        if data_dir_override and data_dir_override.strip():
            p = Path(data_dir_override.strip()) / "aura_command_journal.db"
            p.parent.mkdir(parents=True, exist_ok=True)
            return str(p)

        if os.name == "nt":
            prog_data = os.getenv("PROGRAMDATA") or r"C:\ProgramData"
            p = Path(prog_data) / "Aura" / "data" / "aura_command_journal.db"
            try:
                p.parent.mkdir(parents=True, exist_ok=True)
                return str(p)
            except Exception:
                pass

        fallback = PROJECT_ROOT / "data" / "aura_command_journal.db"
        fallback.parent.mkdir(parents=True, exist_ok=True)
        return str(fallback)

    @staticmethod
    def _apply_pragmas(conn: sqlite3.Connection) -> None:
        """Aplica as diretivas de resiliencia SQLite WAL e concorrencia."""
        try:
            conn.execute("PRAGMA busy_timeout=5000;")
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except sqlite3.OperationalError:
            pass

    @contextmanager
    def _connection(self, immediate: bool = False):
        """
        Gerenciador de contexto thread-safe com pragmas WAL e suporte a BEGIN IMMEDIATE.
        Quando immediate=True, inicia uma transacao de escrita imediata no SQLite.
        """
        with self._lock:
            if self._shared_conn is not None:
                conn = self._shared_conn
                self._apply_pragmas(conn)
                if immediate:
                    conn.execute("BEGIN IMMEDIATE;")
                try:
                    yield conn
                    if conn.in_transaction:
                        conn.execute("COMMIT;")
                except Exception:
                    if conn.in_transaction:
                        try:
                            conn.execute("ROLLBACK;")
                        except Exception:
                            pass
                    raise
            else:
                conn = sqlite3.connect(
                    self.db_path,
                    timeout=10.0,
                    isolation_level=None,
                )
                conn.row_factory = sqlite3.Row
                try:
                    self._apply_pragmas(conn)
                    if immediate:
                        conn.execute("BEGIN IMMEDIATE;")
                    try:
                        yield conn
                        if conn.in_transaction:
                            conn.execute("COMMIT;")
                    except Exception:
                        if conn.in_transaction:
                            try:
                                conn.execute("ROLLBACK;")
                            except Exception:
                                pass
                        raise
                finally:
                    conn.close()

    def _init_db(self) -> None:
        """Inicializa o schema e os indices da tabela aura_command_journal."""
        with self._connection(immediate=True) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS aura_command_journal (
                    journal_id TEXT PRIMARY KEY,
                    command_key TEXT NOT NULL UNIQUE,
                    action_id TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    status TEXT NOT NULL,
                    request_payload_json TEXT NOT NULL DEFAULT '{}',
                    result_payload_json TEXT,
                    error_message TEXT,
                    attempt_count INTEGER NOT NULL DEFAULT 1,
                    started_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT
                );
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_cmd_journal_action_id
                ON aura_command_journal(action_id);
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_cmd_journal_status
                ON aura_command_journal(status, updated_at);
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_cmd_journal_started_at
                ON aura_command_journal(started_at);
                """
            )

    def get_journal_mode(self) -> str:
        """Retorna o journal_mode ativo no banco SQLite (ex: 'wal' em disco, 'memory' em RAM)."""
        with self._connection(immediate=False) as conn:
            row = conn.execute("PRAGMA journal_mode;").fetchone()
            return str(row[0]).lower() if row else "unknown"

    def get_pragma_info(self) -> dict[str, Any]:
        """Inspeciona os pragmas ativos do SQLite para auditoria e testes."""
        with self._connection(immediate=False) as conn:
            jm = conn.execute("PRAGMA journal_mode;").fetchone()
            sync = conn.execute("PRAGMA synchronous;").fetchone()
            bt = conn.execute("PRAGMA busy_timeout;").fetchone()
            return {
                "journal_mode": str(jm[0]).lower() if jm else "unknown",
                "synchronous": int(sync[0]) if sync else -1,
                "busy_timeout": int(bt[0]) if bt else 0,
            }

    @staticmethod
    def _serialize_payload(payload: Any, allow_none: bool = False) -> str | None:
        """Serializa dicionario, modelo Pydantic ou valor arbitrario em JSON."""
        if payload is None:
            return None if allow_none else "{}"
        if hasattr(payload, "model_dump"):
            return json.dumps(payload.model_dump(mode="json"), ensure_ascii=False, default=str)
        if hasattr(payload, "to_dict"):
            return json.dumps(payload.to_dict(), ensure_ascii=False, default=str)
        if isinstance(payload, dict):
            return json.dumps(payload, ensure_ascii=False, default=str)
        if isinstance(payload, str):
            stripped = payload.strip()
            if not stripped:
                return "{}"
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, dict):
                    return stripped
            except Exception:
                pass
            return json.dumps({"value": payload}, ensure_ascii=False, default=str)
        return json.dumps({"result": payload}, ensure_ascii=False, default=str)

    # =========================================================================
    # 1. PERSIST-FIRST ATOMIC CLAIM (BEGIN_COMMAND)
    # =========================================================================

    def begin_command(
        self,
        command_key: str,
        action_id: str = "",
        action_type: str = "mutation",
        actor: str = "system",
        request_payload: dict[str, Any] | Any | None = None,
        allow_retry: bool = True,
    ) -> CommandAcquisitionResult:
        """
        Reivindica atomicamente o comando no SQLite WAL com status RUNNING (BEGIN IMMEDIATE)
        antes de iniciar qualquer efeito colateral ou mutacao.

        Comportamento:
        - Se nao existir: insere como RUNNING (attempt_count=1) e retorna acquired=True.
        - Se ja existir com status == COMPLETED: retorna replay idempotente
          (acquired=False, already_completed=True, replayed=True) com o result_payload original.
        - Se ja existir com status == RUNNING: bloqueia execucao concorrente duplicada
          (acquired=False, already_running=True).
        - Se ja existir com status in (FAILED, INTERRUPTED_BY_CRASH) e allow_retry=True:
          incrementa attempt_count, volta status para RUNNING e retorna acquired=True.
        - Se ja existir com status == ROLLED_BACK: bloqueia reexecucao
          (acquired=False, already_rolled_back=True).
        """
        norm_key = str(command_key or "").strip()
        if not norm_key:
            raise ValueError("command_key nao pode ser vazio no AuraCommandJournal.")

        norm_action_id = str(action_id or norm_key).strip()
        norm_action_type = str(action_type or "mutation").strip()
        norm_actor = str(actor or "system").strip()
        req_json = self._serialize_payload(request_payload, allow_none=False) or "{}"
        now_iso = datetime.now(UTC).isoformat()

        with self._connection(immediate=True) as conn:
            existing_row = conn.execute(
                "SELECT * FROM aura_command_journal WHERE command_key = ?",
                (norm_key,),
            ).fetchone()

            if existing_row is None:
                journal_id = str(uuid.uuid4())
                conn.execute(
                    """
                    INSERT INTO aura_command_journal (
                        journal_id,
                        command_key,
                        action_id,
                        action_type,
                        actor,
                        status,
                        request_payload_json,
                        result_payload_json,
                        error_message,
                        attempt_count,
                        started_at,
                        updated_at,
                        completed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        journal_id,
                        norm_key,
                        norm_action_id,
                        norm_action_type,
                        norm_actor,
                        CommandJournalStatus.RUNNING.value,
                        req_json,
                        None,
                        None,
                        1,
                        now_iso,
                        now_iso,
                        None,
                    ),
                )
                inserted = conn.execute(
                    "SELECT * FROM aura_command_journal WHERE journal_id = ?",
                    (journal_id,),
                ).fetchone()
                entry = CommandJournalEntry.from_row(inserted)
                return CommandAcquisitionResult(
                    acquired=True,
                    entry=entry,
                    already_completed=False,
                    already_running=False,
                    already_rolled_back=False,
                    replayed=False,
                    executed=False,
                    reason="ACQUIRED_NEW",
                )

            existing_entry = CommandJournalEntry.from_row(existing_row)
            current_status = existing_entry.status.upper()

            if current_status == CommandJournalStatus.COMPLETED.value:
                return CommandAcquisitionResult(
                    acquired=False,
                    entry=existing_entry,
                    already_completed=True,
                    already_running=False,
                    already_rolled_back=False,
                    replayed=True,
                    executed=False,
                    reason="ALREADY_COMPLETED",
                )

            if current_status == CommandJournalStatus.RUNNING.value:
                return CommandAcquisitionResult(
                    acquired=False,
                    entry=existing_entry,
                    already_completed=False,
                    already_running=True,
                    already_rolled_back=False,
                    replayed=False,
                    executed=False,
                    reason="ALREADY_RUNNING",
                )

            if current_status == CommandJournalStatus.ROLLED_BACK.value:
                return CommandAcquisitionResult(
                    acquired=False,
                    entry=existing_entry,
                    already_completed=False,
                    already_running=False,
                    already_rolled_back=True,
                    replayed=False,
                    executed=False,
                    reason="ALREADY_ROLLED_BACK",
                )

            if current_status in (
                CommandJournalStatus.FAILED.value,
                CommandJournalStatus.INTERRUPTED_BY_CRASH.value,
            ):
                if allow_retry:
                    new_attempt = int(existing_entry.attempt_count or 1) + 1
                    eff_req_json = (
                        req_json
                        if request_payload is not None
                        else existing_entry.request_payload_json
                    )
                    eff_actor = norm_actor if actor != "system" else existing_entry.actor
                    conn.execute(
                        """
                        UPDATE aura_command_journal
                        SET status = ?,
                            attempt_count = ?,
                            actor = ?,
                            request_payload_json = ?,
                            error_message = NULL,
                            started_at = ?,
                            updated_at = ?,
                            completed_at = NULL
                        WHERE command_key = ?
                        """,
                        (
                            CommandJournalStatus.RUNNING.value,
                            new_attempt,
                            eff_actor,
                            eff_req_json,
                            now_iso,
                            now_iso,
                            norm_key,
                        ),
                    )
                    updated_row = conn.execute(
                        "SELECT * FROM aura_command_journal WHERE command_key = ?",
                        (norm_key,),
                    ).fetchone()
                    updated_entry = CommandJournalEntry.from_row(updated_row)
                    return CommandAcquisitionResult(
                        acquired=True,
                        entry=updated_entry,
                        already_completed=False,
                        already_running=False,
                        already_rolled_back=False,
                        replayed=False,
                        executed=False,
                        reason="ACQUIRED_RETRY",
                    )

                return CommandAcquisitionResult(
                    acquired=False,
                    entry=existing_entry,
                    already_completed=False,
                    already_running=False,
                    already_rolled_back=False,
                    replayed=False,
                    executed=False,
                    reason=f"RETRY_DISABLED_{current_status}",
                )

            return CommandAcquisitionResult(
                acquired=False,
                entry=existing_entry,
                reason=f"UNHANDLED_STATUS_{current_status}",
            )

    # =========================================================================
    # 2. TRANSICOES DE CICLO DE VIDA (COMPLETE, FAIL, ROLLBACK)
    # =========================================================================

    def complete_command(
        self,
        command_key: str,
        result_payload: dict[str, Any] | Any | None = None,
    ) -> CommandJournalEntry:
        """
        Transita atomicamente o comando de RUNNING para COMPLETED e persiste o recibo.
        """
        norm_key = str(command_key or "").strip()
        if not norm_key:
            raise CommandJournalError("command_key nao pode ser vazio em complete_command.")

        res_json = self._serialize_payload(result_payload, allow_none=False) or "{}"
        now_iso = datetime.now(UTC).isoformat()

        with self._connection(immediate=True) as conn:
            row = conn.execute(
                "SELECT * FROM aura_command_journal WHERE command_key = ?",
                (norm_key,),
            ).fetchone()
            if row is None:
                raise CommandJournalError(
                    f"Comando '{norm_key}' nao encontrado no journal para complete_command."
                )

            current_status = str(row["status"]).upper()
            if current_status == CommandJournalStatus.COMPLETED.value:
                return CommandJournalEntry.from_row(row)

            if current_status != CommandJournalStatus.RUNNING.value:
                raise CommandJournalError(
                    f"Transicao invalida para COMPLETED a partir do status '{current_status}' (esperado RUNNING)."
                )

            conn.execute(
                """
                UPDATE aura_command_journal
                SET status = ?,
                    result_payload_json = ?,
                    error_message = NULL,
                    updated_at = ?,
                    completed_at = ?
                WHERE command_key = ?
                """,
                (
                    CommandJournalStatus.COMPLETED.value,
                    res_json,
                    now_iso,
                    now_iso,
                    norm_key,
                ),
            )
            updated = conn.execute(
                "SELECT * FROM aura_command_journal WHERE command_key = ?",
                (norm_key,),
            ).fetchone()
            return CommandJournalEntry.from_row(updated)

    def fail_command(
        self,
        command_key: str,
        error_message: str,
        result_payload: dict[str, Any] | Any | None = None,
    ) -> CommandJournalEntry:
        """
        Transita atomicamente o comando de RUNNING para FAILED e registra o erro.
        """
        norm_key = str(command_key or "").strip()
        if not norm_key:
            raise CommandJournalError("command_key nao pode ser vazio em fail_command.")

        err_str = str(error_message or "Falha na execucao do comando")[:2000]
        res_json = self._serialize_payload(result_payload, allow_none=True)
        now_iso = datetime.now(UTC).isoformat()

        with self._connection(immediate=True) as conn:
            row = conn.execute(
                "SELECT * FROM aura_command_journal WHERE command_key = ?",
                (norm_key,),
            ).fetchone()
            if row is None:
                raise CommandJournalError(
                    f"Comando '{norm_key}' nao encontrado no journal para fail_command."
                )

            eff_res_json = res_json if res_json is not None else row["result_payload_json"]
            conn.execute(
                """
                UPDATE aura_command_journal
                SET status = ?,
                    error_message = ?,
                    result_payload_json = ?,
                    updated_at = ?,
                    completed_at = ?
                WHERE command_key = ?
                """,
                (
                    CommandJournalStatus.FAILED.value,
                    err_str,
                    eff_res_json,
                    now_iso,
                    now_iso,
                    norm_key,
                ),
            )
            updated = conn.execute(
                "SELECT * FROM aura_command_journal WHERE command_key = ?",
                (norm_key,),
            ).fetchone()
            return CommandJournalEntry.from_row(updated)

    def mark_rolled_back(
        self,
        command_key: str,
        rollback_payload: dict[str, Any] | Any | None = None,
    ) -> CommandJournalEntry:
        """
        Transita atomicamente um comando COMPLETED para ROLLED_BACK e persiste os metadados de estorno.
        Aceita command_key exata ou action_id como fallback de busca.
        """
        norm_key = str(command_key or "").strip()
        if not norm_key:
            raise CommandJournalError("command_key nao pode ser vazio em mark_rolled_back.")

        now_iso = datetime.now(UTC).isoformat()

        with self._connection(immediate=True) as conn:
            row = conn.execute(
                "SELECT * FROM aura_command_journal WHERE command_key = ?",
                (norm_key,),
            ).fetchone()
            if row is None:
                row = conn.execute(
                    """
                    SELECT * FROM aura_command_journal
                    WHERE action_id = ?
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    (norm_key,),
                ).fetchone()

            if row is None:
                raise CommandJournalError(
                    f"Comando '{norm_key}' nao encontrado no journal para rollback."
                )

            existing_entry = CommandJournalEntry.from_row(row)
            current_status = existing_entry.status.upper()

            if current_status == CommandJournalStatus.ROLLED_BACK.value and rollback_payload is None:
                return existing_entry

            if current_status not in (
                CommandJournalStatus.COMPLETED.value,
                CommandJournalStatus.ROLLED_BACK.value,
            ):
                raise CommandJournalError(
                    f"Nao e possivel realizar rollback de comando no status '{current_status}' (esperado COMPLETED)."
                )

            merged_result: dict[str, Any] = {}
            if isinstance(existing_entry.result_payload, dict):
                merged_result.update(existing_entry.result_payload)

            if rollback_payload is not None:
                if isinstance(rollback_payload, dict):
                    merged_result.update(rollback_payload)
                    merged_result["rollback"] = rollback_payload
                else:
                    merged_result["rollback"] = rollback_payload

            merged_result["status"] = CommandJournalStatus.ROLLED_BACK.value
            merged_result["rolled_back_at"] = now_iso

            res_json = self._serialize_payload(merged_result, allow_none=False) or "{}"
            rb_reason = None
            if isinstance(rollback_payload, dict):
                rb_reason = rollback_payload.get("reason") or rollback_payload.get("motivo")

            conn.execute(
                """
                UPDATE aura_command_journal
                SET status = ?,
                    result_payload_json = ?,
                    error_message = COALESCE(?, error_message),
                    updated_at = ?
                WHERE journal_id = ?
                """,
                (
                    CommandJournalStatus.ROLLED_BACK.value,
                    res_json,
                    str(rb_reason) if rb_reason else None,
                    now_iso,
                    existing_entry.journal_id,
                ),
            )
            updated = conn.execute(
                "SELECT * FROM aura_command_journal WHERE journal_id = ?",
                (existing_entry.journal_id,),
            ).fetchone()
            return CommandJournalEntry.from_row(updated)

    # =========================================================================
    # 3. CRASH RECOVERY DE COMANDOS ORFAOS EM RUNNING
    # =========================================================================

    def recover_interrupted_commands(
        self,
        stale_after_sec: float | None = None,
        error_message: str | None = None,
    ) -> int:
        """
        Identifica comandos que ficaram orfaos em RUNNING (acima de stale_after_sec ou no boot)
        e marca como INTERRUPTED_BY_CRASH, registrando auditoria forense de queda de energia/processo.
        Retorna a quantidade de comandos recuperados.
        """
        threshold = (
            self.stale_after_sec
            if stale_after_sec is None
            else max(0.0, float(stale_after_sec))
        )
        now_epoch = time.time()
        now_iso = datetime.now(UTC).isoformat()
        forensic_msg = (
            str(error_message).strip()
            if (error_message and str(error_message).strip())
            else "Comando interrompido por queda de energia ou reinicio abrupto do processo (crash recovery)"
        )

        with self._connection(immediate=True) as conn:
            rows = conn.execute(
                "SELECT * FROM aura_command_journal WHERE status = ?",
                (CommandJournalStatus.RUNNING.value,),
            ).fetchall()

            stale_journal_ids: list[str] = []
            for row in rows:
                if threshold <= 0.0:
                    stale_journal_ids.append(str(row["journal_id"]))
                    continue

                ts_epoch = _parse_iso_to_epoch(row["updated_at"] or row["started_at"])
                if ts_epoch is not None:
                    is_stale = (now_epoch - ts_epoch) >= threshold
                else:
                    is_stale = True

                if is_stale:
                    stale_journal_ids.append(str(row["journal_id"]))

            recovered_count = 0
            for j_id in stale_journal_ids:
                cur = conn.execute(
                    """
                    UPDATE aura_command_journal
                    SET status = ?,
                        error_message = COALESCE(error_message, ?),
                        updated_at = ?,
                        completed_at = ?
                    WHERE journal_id = ? AND status = ?
                    """,
                    (
                        CommandJournalStatus.INTERRUPTED_BY_CRASH.value,
                        forensic_msg,
                        now_iso,
                        now_iso,
                        j_id,
                        CommandJournalStatus.RUNNING.value,
                    ),
                )
                recovered_count += int(cur.rowcount or 0)

            return recovered_count

    # =========================================================================
    # 4. EXECUTOR IDEMPOTENTE (EXECUTE_IDEMPOTENT)
    # =========================================================================

    def execute_idempotent(
        self,
        command_key: str,
        fn: Callable[[], Any] | None = None,
        *,
        action_id: str = "",
        action_type: str = "mutation",
        actor: str = "system",
        request_payload: dict[str, Any] | Any | None = None,
        allow_retry: bool = True,
        func: Callable[[], Any] | None = None,
        callback: Callable[[], Any] | None = None,
    ) -> CommandAcquisitionResult:
        """
        Executa uma funcao sob o protocolo Persist-First:
        1. Reivindica o comando com begin_command() gravando RUNNING no SQLite WAL.
        2. Se ja estiver COMPLETED, retorna replay imediato sem invocar a funcao.
        3. Se ja estiver RUNNING em outra thread, retorna resultado bloqueado (already_running=True)
           sem invocar a funcao.
        4. Se adquirido (acquired=True), executa a funcao fora do lock do banco:
           - Em caso de sucesso: invoca complete_command() e retorna o resultado.
           - Em caso de excecao: invoca fail_command() e propaga a excecao.
        """
        target_fn = fn or func or callback
        if target_fn is None or not callable(target_fn):
            raise ValueError("Uma funcao executavel (fn) deve ser fornecida para execute_idempotent.")

        acq = self.begin_command(
            command_key=command_key,
            action_id=action_id,
            action_type=action_type,
            actor=actor,
            request_payload=request_payload,
            allow_retry=allow_retry,
        )

        if not acq.acquired:
            return acq

        try:
            raw_result = target_fn()
        except Exception as exc:
            self.fail_command(
                command_key=command_key,
                error_message=str(exc),
            )
            raise

        completed_entry = self.complete_command(
            command_key=command_key,
            result_payload=raw_result,
        )
        return CommandAcquisitionResult(
            acquired=True,
            entry=completed_entry,
            already_completed=False,
            already_running=False,
            already_rolled_back=False,
            replayed=False,
            executed=True,
            reason="COMPLETED",
        )

    # =========================================================================
    # 5. CONSULTA E ESTATISTICAS
    # =========================================================================

    def get_entry(self, command_key: str) -> CommandJournalEntry | None:
        """Busca uma entrada no journal pela command_key (ou journal_id como fallback)."""
        norm_key = str(command_key or "").strip()
        if not norm_key:
            return None
        with self._connection(immediate=False) as conn:
            row = conn.execute(
                "SELECT * FROM aura_command_journal WHERE command_key = ?",
                (norm_key,),
            ).fetchone()
            if row is None:
                row = conn.execute(
                    "SELECT * FROM aura_command_journal WHERE journal_id = ?",
                    (norm_key,),
                ).fetchone()
            return CommandJournalEntry.from_row(row) if row is not None else None

    def get_entry_by_action_id(self, action_id: str) -> CommandJournalEntry | None:
        """Busca a entrada mais recente associada a um action_id."""
        norm_act = str(action_id or "").strip()
        if not norm_act:
            return None
        with self._connection(immediate=False) as conn:
            row = conn.execute(
                """
                SELECT * FROM aura_command_journal
                WHERE action_id = ?
                ORDER BY updated_at DESC, started_at DESC
                LIMIT 1
                """,
                (norm_act,),
            ).fetchone()
            return CommandJournalEntry.from_row(row) if row is not None else None

    def list_entries(
        self,
        action_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Lista entradas do Command Journal com filtros opcionais por action_id e status."""
        safe_limit = max(1, min(int(limit), 500))
        query = "SELECT * FROM aura_command_journal WHERE 1=1"
        params: list[Any] = []

        if action_id and str(action_id).strip():
            query += " AND action_id = ?"
            params.append(str(action_id).strip())

        if status and str(status).strip():
            query += " AND UPPER(status) = ?"
            params.append(str(status).strip().upper())

        query += " ORDER BY updated_at DESC, started_at DESC LIMIT ?"
        params.append(safe_limit)

        with self._connection(immediate=False) as conn:
            rows = conn.execute(query, tuple(params)).fetchall()

        return [CommandJournalEntry.from_row(r).to_dict() for r in rows]

    def get_stats(self) -> dict[str, int]:
        """
        Retorna estatisticas consolidadas por status do Command Journal:
        running, completed, failed, rolled_back, interrupted_by_crash, total.
        """
        stats = {
            "running": 0,
            "completed": 0,
            "failed": 0,
            "rolled_back": 0,
            "interrupted_by_crash": 0,
            "total": 0,
        }
        status_map = {
            CommandJournalStatus.RUNNING.value: "running",
            CommandJournalStatus.COMPLETED.value: "completed",
            CommandJournalStatus.FAILED.value: "failed",
            CommandJournalStatus.ROLLED_BACK.value: "rolled_back",
            CommandJournalStatus.INTERRUPTED_BY_CRASH.value: "interrupted_by_crash",
        }
        with self._connection(immediate=False) as conn:
            rows = conn.execute(
                """
                SELECT status, COUNT(*) AS cnt
                FROM aura_command_journal
                GROUP BY status
                """
            ).fetchall()
            for row in rows:
                st = str(row["status"] or "").upper()
                cnt = int(row["cnt"] or 0)
                key = status_map.get(st)
                if key:
                    stats[key] += cnt
                stats["total"] += cnt
        return stats

    def close(self) -> None:
        """Fecha conexoes persistentes em memoria."""
        with self._lock:
            if self._shared_conn is not None:
                try:
                    self._shared_conn.close()
                except Exception:
                    pass
                self._shared_conn = None


# =============================================================================
# SINGLETON GLOBAL E PROVIDERS
# =============================================================================

_GLOBAL_JOURNAL: AuraCommandJournal | None = None
_GLOBAL_JOURNAL_EXPLICIT: bool = False
_GLOBAL_JOURNAL_LOCK = threading.RLock()


def get_command_journal() -> AuraCommandJournal:
    """Retorna a instancia singleton ativa do AuraCommandJournal."""
    global _GLOBAL_JOURNAL, _GLOBAL_JOURNAL_EXPLICIT
    with _GLOBAL_JOURNAL_LOCK:
        env_path = os.getenv("AURA_COMMAND_JOURNAL_DB_PATH")
        if (
            _GLOBAL_JOURNAL is not None
            and not _GLOBAL_JOURNAL_EXPLICIT
            and env_path
            and env_path.strip()
            and _GLOBAL_JOURNAL.db_path != env_path.strip()
        ):
            _GLOBAL_JOURNAL.close()
            _GLOBAL_JOURNAL = None

        if _GLOBAL_JOURNAL is None:
            _GLOBAL_JOURNAL = AuraCommandJournal()
            _GLOBAL_JOURNAL_EXPLICIT = False
        return _GLOBAL_JOURNAL


def set_command_journal(journal: AuraCommandJournal | None) -> None:
    """Permite injetar ou substituir a instancia global do AuraCommandJournal."""
    global _GLOBAL_JOURNAL, _GLOBAL_JOURNAL_EXPLICIT
    with _GLOBAL_JOURNAL_LOCK:
        _GLOBAL_JOURNAL = journal
        _GLOBAL_JOURNAL_EXPLICIT = journal is not None


def reset_command_journal() -> None:
    """Reseta o singleton global do Command Journal (utilitario para isolamento de testes)."""
    global _GLOBAL_JOURNAL, _GLOBAL_JOURNAL_EXPLICIT
    with _GLOBAL_JOURNAL_LOCK:
        if _GLOBAL_JOURNAL is not None:
            _GLOBAL_JOURNAL.close()
        _GLOBAL_JOURNAL = None
        _GLOBAL_JOURNAL_EXPLICIT = False


__all__ = [
    "AuraCommandJournal",
    "CommandAcquisitionResult",
    "CommandJournalEntry",
    "CommandJournalError",
    "CommandJournalStatus",
    "get_command_journal",
    "reset_command_journal",
    "set_command_journal",
]
