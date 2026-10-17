"""
Modulo de Mensageria Resiliente com Transactional Outbox (SQLite WAL) - Fase 5 (Roadmap Sentinel-AURA).

Implementa o padrao Transactional Outbox para garantir entrega confiavel (at-least-once)
de relatorios de fechamento de turno, alertas criticos de tanques e sangrias para
WhatsApp (Evolution API) e webhooks n8n em postos de combustiveis com internet instavel.

Principios Arquiteturais:
1. Persist-Before-Send: Toda mensagem e gravada atomicamente no SQLite local em modo WAL
   com status PENDING antes de qualquer tentativa de envio por rede.
2. Deduplicacao Estrita: Suporte a idempotency_key (UNIQUE) evitando disparos duplicados
   em retentativas de regras ou reinicializacoes de servico.
3. Exponential Backoff com Jitter: Retentativas progressivas (FAILED_RETRY) ate max_attempts,
   movendo para fila Dead Letter (DEAD_LETTER / DLQ) quando esgotadas.
4. Crash Recovery: Recuperacao automatica de mensagens orfas presas em PROCESSING
   caso o processo ou computador reinicie durante uma requisicao HTTP.
5. Armazenamento Compartilhado: Banco padrao em %ProgramData%\\Aura\\data\\aura_outbox.db
   com suporte a override via AURA_OUTBOX_DB_PATH, AURA_DATA_DIR ou db_path no construtor.
Zero travessoes em todo o arquivo.
"""
# ruff: noqa: BLE001, S110

from __future__ import annotations

import inspect
import json
import logging
import os
import random
import sqlite3
import threading
import time
import uuid
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger("aura.outbox")

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_BASE_DELAY_SEC: float = 2.0
DEFAULT_MAX_DELAY_SEC: float = 300.0
DEFAULT_MAX_ATTEMPTS: int = 5
DEFAULT_STALE_PROCESSING_SEC: float = 120.0
DEFAULT_POLL_INTERVAL_SEC: float = 5.0
DEFAULT_HTTP_TIMEOUT_SEC: float = 8.0


class OutboxStatus(str, Enum):
    """Estados do ciclo de vida de uma mensagem na Transactional Outbox."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    DELIVERED = "DELIVERED"
    FAILED_RETRY = "FAILED_RETRY"
    DEAD_LETTER = "DEAD_LETTER"


@dataclass
class OutboxMessage:
    """Representa um registro persistido na tabela aura_outbox_messages."""

    message_id: str
    idempotency_key: str | None
    event_type: str
    destination_url: str
    payload_json: str
    headers_json: str = "{}"
    status: str = OutboxStatus.PENDING.value
    attempt_count: int = 0
    max_attempts: int = DEFAULT_MAX_ATTEMPTS
    next_retry_at: float = 0.0
    last_error: str | None = None
    created_at: str = ""
    updated_at: str = ""
    delivered_at: str | None = None

    @property
    def payload(self) -> dict[str, Any]:
        """Retorna o payload desserializado como dicionario."""
        try:
            data = json.loads(self.payload_json) if self.payload_json else {}
            return data if isinstance(data, dict) else {"raw": data}
        except Exception:
            return {"raw": self.payload_json}

    @property
    def headers(self) -> dict[str, str]:
        """Retorna os cabecalhos HTTP desserializados."""
        try:
            data = json.loads(self.headers_json) if self.headers_json else {}
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
            return {}
        except Exception:
            return {}

    def to_dict(self) -> dict[str, Any]:
        """Converte a mensagem para dicionario serializavel em JSON."""
        data = asdict(self)
        data["payload"] = self.payload
        data["headers"] = self.headers
        return data

    @classmethod
    def from_row(cls, row: sqlite3.Row | dict[str, Any]) -> OutboxMessage:
        """Constroi OutboxMessage a partir de uma linha do SQLite."""
        return cls(
            message_id=str(row["message_id"]),
            idempotency_key=row["idempotency_key"],
            event_type=str(row["event_type"]),
            destination_url=str(row["destination_url"]),
            payload_json=str(row["payload_json"]),
            headers_json=str(row["headers_json"] or "{}"),
            status=str(row["status"]),
            attempt_count=int(row["attempt_count"] or 0),
            max_attempts=int(row["max_attempts"] or DEFAULT_MAX_ATTEMPTS),
            next_retry_at=float(row["next_retry_at"] or 0.0),
            last_error=row["last_error"],
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            delivered_at=row["delivered_at"],
        )


@dataclass
class OutboxBatchResult:
    """Resumo estruturado do processamento em lote da Outbox."""

    processed: int = 0
    delivered: int = 0
    failed_retry: int = 0
    dead_letter: int = 0
    recovered_stale: int = 0
    messages: list[dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Converte o resumo do lote para dicionario serializavel."""
        return asdict(self)


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


def compute_next_backoff(
    attempt: int,
    base_delay: float = DEFAULT_BASE_DELAY_SEC,
    max_delay: float = DEFAULT_MAX_DELAY_SEC,
    jitter_ratio: float = 0.15,
) -> float:
    """
    Calcula o tempo de espera (em segundos) com Exponential Backoff e Jitter.
    Formula base: min(max_delay, base_delay * (2 ** max(0, attempt - 1))) + jitter.
    """
    safe_base = max(0.0, float(base_delay))
    safe_max = max(safe_base, float(max_delay))
    if safe_base == 0.0:
        return 0.0

    exponent = max(0, int(attempt) - 1)
    exp_delay = min(safe_max, safe_base * (2**exponent))
    max_jitter = exp_delay * max(0.0, float(jitter_ratio))
    jitter = random.uniform(0.0, max_jitter) if max_jitter > 0.0 else 0.0
    return round(min(safe_max, exp_delay + jitter), 4)


class AuraTransactionalOutbox:
    """
    Implementacao do padrao Transactional Outbox sobre SQLite em modo WAL.
    Garante persistencia local previa ao envio (Persist-Before-Send), deduplicacao
    por idempotency_key, retentativa com backoff exponencial, crash recovery e DLQ.
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
        base_delay_sec: float = DEFAULT_BASE_DELAY_SEC,
        max_delay_sec: float = DEFAULT_MAX_DELAY_SEC,
        default_max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        stale_processing_timeout_sec: float = DEFAULT_STALE_PROCESSING_SEC,
        poll_interval_sec: float = DEFAULT_POLL_INTERVAL_SEC,
        http_timeout_sec: float = DEFAULT_HTTP_TIMEOUT_SEC,
        sender_fn: Callable[..., Any] | None = None,
    ) -> None:
        self.base_delay_sec = max(0.0, float(base_delay_sec))
        self.max_delay_sec = max(self.base_delay_sec, float(max_delay_sec))
        self.default_max_attempts = max(1, int(default_max_attempts))
        self.stale_processing_timeout_sec = max(0.0, float(stale_processing_timeout_sec))
        self.poll_interval_sec = max(0.05, float(poll_interval_sec))
        self.http_timeout_sec = max(0.5, float(http_timeout_sec))
        self.sender_fn = sender_fn

        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._worker_thread: threading.Thread | None = None
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
            self._shared_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._shared_conn.row_factory = sqlite3.Row

        self._init_db()

    @staticmethod
    def resolve_default_db_path() -> str:
        """
        Resolve o caminho padrao do banco SQLite da Outbox.
        Prioridade:
        1. Variavel de ambiente AURA_OUTBOX_DB_PATH
        2. Variavel de ambiente AURA_DATA_DIR / aura_outbox.db
        3. %ProgramData%\\Aura\\data\\aura_outbox.db (no Windows)
        4. Fallback para <PROJECT_ROOT>/data/aura_outbox.db
        """
        env_path = os.getenv("AURA_OUTBOX_DB_PATH")
        if env_path and env_path.strip():
            cleaned = env_path.strip()
            if cleaned == ":memory:":
                return ":memory:"
            p = Path(cleaned)
            p.parent.mkdir(parents=True, exist_ok=True)
            return str(p)

        data_dir_override = os.getenv("AURA_DATA_DIR")
        if data_dir_override and data_dir_override.strip():
            p = Path(data_dir_override.strip()) / "aura_outbox.db"
            p.parent.mkdir(parents=True, exist_ok=True)
            return str(p)

        if os.name == "nt":
            prog_data = os.getenv("PROGRAMDATA") or r"C:\ProgramData"
            p = Path(prog_data) / "Aura" / "data" / "aura_outbox.db"
            try:
                p.parent.mkdir(parents=True, exist_ok=True)
                return str(p)
            except Exception:
                pass

        fallback = PROJECT_ROOT / "data" / "aura_outbox.db"
        fallback.parent.mkdir(parents=True, exist_ok=True)
        return str(fallback)

    @staticmethod
    def compute_next_backoff(
        attempt: int,
        base_delay: float = DEFAULT_BASE_DELAY_SEC,
        max_delay: float = DEFAULT_MAX_DELAY_SEC,
    ) -> float:
        """Calcula o atraso de retentativa exponencial com jitter."""
        return compute_next_backoff(attempt=attempt, base_delay=base_delay, max_delay=max_delay)

    @contextmanager
    def _connection(self):
        """Gerenciador de contexto thread-safe com pragmas WAL e busy_timeout."""
        with self._lock:
            if self._shared_conn is not None:
                self._apply_pragmas(self._shared_conn)
                with self._shared_conn:
                    yield self._shared_conn
            else:
                conn = sqlite3.connect(self.db_path, timeout=10.0)
                conn.row_factory = sqlite3.Row
                try:
                    self._apply_pragmas(conn)
                    with conn:
                        yield conn
                finally:
                    conn.close()

    @staticmethod
    def _apply_pragmas(conn: sqlite3.Connection) -> None:
        """Aplica as diretivas de resiliencia SQLite WAL e concorrencia."""
        try:
            conn.execute("PRAGMA busy_timeout=5000;")
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except sqlite3.OperationalError:
            pass

    def _init_db(self) -> None:
        """Inicializa o schema e os indices da tabela aura_outbox_messages."""
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS aura_outbox_messages (
                    message_id TEXT PRIMARY KEY,
                    idempotency_key TEXT UNIQUE,
                    event_type TEXT NOT NULL,
                    destination_url TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    headers_json TEXT NOT NULL DEFAULT '{}',
                    status TEXT NOT NULL,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 5,
                    next_retry_at REAL NOT NULL,
                    last_error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    delivered_at TEXT
                );
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_outbox_status_retry
                ON aura_outbox_messages(status, next_retry_at);
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_outbox_event_type
                ON aura_outbox_messages(event_type);
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_outbox_created_at
                ON aura_outbox_messages(created_at);
                """
            )

    def get_journal_mode(self) -> str:
        """Retorna o journal_mode ativo no banco SQLite (ex: 'wal' em disco, 'memory' em RAM)."""
        with self._connection() as conn:
            row = conn.execute("PRAGMA journal_mode;").fetchone()
            return str(row[0]).lower() if row else "unknown"

    def get_pragma_info(self) -> dict[str, Any]:
        """Inspeciona os pragmas ativos do SQLite para auditoria e testes."""
        with self._connection() as conn:
            jm = conn.execute("PRAGMA journal_mode;").fetchone()
            sync = conn.execute("PRAGMA synchronous;").fetchone()
            bt = conn.execute("PRAGMA busy_timeout;").fetchone()
            return {
                "journal_mode": str(jm[0]).lower() if jm else "unknown",
                "synchronous": int(sync[0]) if sync else -1,
                "busy_timeout": int(bt[0]) if bt else 0,
            }

    @staticmethod
    def _serialize_payload(payload: Any) -> str:
        """Serializa dicionario, modelo Pydantic ou string em JSON."""
        if hasattr(payload, "model_dump"):
            return json.dumps(payload.model_dump(), ensure_ascii=False, default=str)
        if isinstance(payload, dict):
            return json.dumps(payload, ensure_ascii=False, default=str)
        if isinstance(payload, str):
            stripped = payload.strip()
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, dict):
                    return stripped
            except Exception:
                pass
            return json.dumps({"text": payload}, ensure_ascii=False, default=str)
        return json.dumps({"data": str(payload)}, ensure_ascii=False, default=str)

    @staticmethod
    def _serialize_headers(headers: dict[str, str] | None) -> str:
        """Serializa cabecalhos HTTP em JSON."""
        if not headers:
            return "{}"
        clean = {str(k): str(v) for k, v in headers.items()}
        return json.dumps(clean, ensure_ascii=False)

    # =========================================================================
    # 1. PERSIST-BEFORE-SEND (ENQUEUE & DEDUPLICACAO)
    # =========================================================================

    def enqueue(
        self,
        event_type: str,
        destination_url: str,
        payload: Any,
        headers: dict[str, str] | None = None,
        idempotency_key: str | None = None,
        max_attempts: int | None = None,
    ) -> OutboxMessage:
        """
        Grava a mensagem no disco com status PENDING antes de qualquer tentativa de rede.
        Se idempotency_key ja existir no banco, retorna a mensagem existente sem duplicar.
        """
        norm_event = str(event_type or "generic_event").strip()
        norm_url = str(destination_url or "").strip()
        if not norm_url:
            raise ValueError("destination_url nao pode ser vazio ao enfileirar na Outbox.")

        norm_idem = idempotency_key.strip() if (idempotency_key and idempotency_key.strip()) else None
        effective_max = max(1, int(max_attempts if max_attempts is not None else self.default_max_attempts))
        payload_str = self._serialize_payload(payload)
        headers_str = self._serialize_headers(headers)

        now_epoch = time.time()
        now_iso = datetime.now(UTC).isoformat()
        msg_id = str(uuid.uuid4())

        with self._connection() as conn:
            if norm_idem is not None:
                existing_row = conn.execute(
                    "SELECT * FROM aura_outbox_messages WHERE idempotency_key = ?",
                    (norm_idem,),
                ).fetchone()
                if existing_row is not None:
                    return OutboxMessage.from_row(existing_row)

            try:
                conn.execute(
                    """
                    INSERT INTO aura_outbox_messages (
                        message_id,
                        idempotency_key,
                        event_type,
                        destination_url,
                        payload_json,
                        headers_json,
                        status,
                        attempt_count,
                        max_attempts,
                        next_retry_at,
                        last_error,
                        created_at,
                        updated_at,
                        delivered_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        msg_id,
                        norm_idem,
                        norm_event,
                        norm_url,
                        payload_str,
                        headers_str,
                        OutboxStatus.PENDING.value,
                        0,
                        effective_max,
                        now_epoch,
                        None,
                        now_iso,
                        now_iso,
                        None,
                    ),
                )
            except sqlite3.IntegrityError:
                if norm_idem is not None:
                    existing_row = conn.execute(
                        "SELECT * FROM aura_outbox_messages WHERE idempotency_key = ?",
                        (norm_idem,),
                    ).fetchone()
                    if existing_row is not None:
                        return OutboxMessage.from_row(existing_row)
                raise

            inserted_row = conn.execute(
                "SELECT * FROM aura_outbox_messages WHERE message_id = ?",
                (msg_id,),
            ).fetchone()
            return OutboxMessage.from_row(inserted_row)

    def get_message(self, message_id: str) -> OutboxMessage | None:
        """Busca uma mensagem pelo message_id."""
        with self._connection() as conn:
            row = conn.execute(
                "SELECT * FROM aura_outbox_messages WHERE message_id = ?",
                (str(message_id).strip(),),
            ).fetchone()
            return OutboxMessage.from_row(row) if row is not None else None

    def get_message_by_idempotency_key(self, idempotency_key: str) -> OutboxMessage | None:
        """Busca uma mensagem pela chave de idempotencia."""
        with self._connection() as conn:
            row = conn.execute(
                "SELECT * FROM aura_outbox_messages WHERE idempotency_key = ?",
                (str(idempotency_key).strip(),),
            ).fetchone()
            return OutboxMessage.from_row(row) if row is not None else None

    # =========================================================================
    # 2. TRANSICOES DE ESTADO ATOMICAS (PROCESSING, DELIVERED, FAILED, DLQ)
    # =========================================================================

    def mark_processing(
        self,
        message_id: str,
        *,
        respect_backoff: bool = False,
        now: float | None = None,
    ) -> OutboxMessage | None:
        """
        Reivindica atomicamente (Compare-And-Swap) a mensagem como PROCESSING
        apenas se ela estiver em PENDING ou FAILED_RETRY.
        Retorna None se a mensagem nao existir ou ja tiver sido reivindicada/entregue
        por outra thread ou processo concorrente.
        """
        now_iso = datetime.now(UTC).isoformat()
        effective_now = float(now) if now is not None else time.time()
        with self._connection() as conn:
            if respect_backoff:
                cur = conn.execute(
                    """
                    UPDATE aura_outbox_messages
                    SET status = ?, updated_at = ?
                    WHERE message_id = ?
                      AND status IN (?, ?)
                      AND next_retry_at <= ?
                    """,
                    (
                        OutboxStatus.PROCESSING.value,
                        now_iso,
                        message_id,
                        OutboxStatus.PENDING.value,
                        OutboxStatus.FAILED_RETRY.value,
                        effective_now,
                    ),
                )
            else:
                cur = conn.execute(
                    """
                    UPDATE aura_outbox_messages
                    SET status = ?, updated_at = ?
                    WHERE message_id = ?
                      AND status IN (?, ?)
                    """,
                    (
                        OutboxStatus.PROCESSING.value,
                        now_iso,
                        message_id,
                        OutboxStatus.PENDING.value,
                        OutboxStatus.FAILED_RETRY.value,
                    ),
                )
            if (cur.rowcount or 0) == 0:
                return None
            row = conn.execute(
                "SELECT * FROM aura_outbox_messages WHERE message_id = ?",
                (message_id,),
            ).fetchone()
            return OutboxMessage.from_row(row) if row is not None else None

    def mark_delivered(
        self,
        message_id: str,
        delivered_at: str | None = None,
    ) -> OutboxMessage | None:
        """Marca a mensagem como DELIVERED apos confirmacao de sucesso HTTP."""
        now_iso = delivered_at or datetime.now(UTC).isoformat()
        with self._connection() as conn:
            row = conn.execute(
                "SELECT attempt_count FROM aura_outbox_messages WHERE message_id = ?",
                (message_id,),
            ).fetchone()
            if row is None:
                return None
            new_attempts = int(row["attempt_count"] or 0) + 1
            conn.execute(
                """
                UPDATE aura_outbox_messages
                SET status = ?,
                    attempt_count = ?,
                    last_error = NULL,
                    updated_at = ?,
                    delivered_at = ?
                WHERE message_id = ?
                """,
                (
                    OutboxStatus.DELIVERED.value,
                    new_attempts,
                    now_iso,
                    now_iso,
                    message_id,
                ),
            )
            updated_row = conn.execute(
                "SELECT * FROM aura_outbox_messages WHERE message_id = ?",
                (message_id,),
            ).fetchone()
            return OutboxMessage.from_row(updated_row) if updated_row is not None else None

    def mark_failed_attempt(
        self,
        message_id: str,
        error: str,
        base_delay: float | None = None,
        max_delay: float | None = None,
    ) -> OutboxMessage | None:
        """
        Registra uma falha de entrega na Outbox.
        - Se attempt_count + 1 >= max_attempts: move para DEAD_LETTER.
        - Caso contrario: move para FAILED_RETRY e agenda next_retry_at com backoff exponencial.
        """
        now_epoch = time.time()
        now_iso = datetime.now(UTC).isoformat()
        b_delay = self.base_delay_sec if base_delay is None else float(base_delay)
        m_delay = self.max_delay_sec if max_delay is None else float(max_delay)

        with self._connection() as conn:
            row = conn.execute(
                "SELECT attempt_count, max_attempts FROM aura_outbox_messages WHERE message_id = ?",
                (message_id,),
            ).fetchone()
            if row is None:
                return None

            new_attempt = int(row["attempt_count"] or 0) + 1
            max_att = int(row["max_attempts"] or self.default_max_attempts)

            if new_attempt >= max_att:
                next_status = OutboxStatus.DEAD_LETTER.value
                next_retry = now_epoch
            else:
                next_status = OutboxStatus.FAILED_RETRY.value
                backoff = self.compute_next_backoff(
                    attempt=new_attempt,
                    base_delay=b_delay,
                    max_delay=m_delay,
                )
                next_retry = now_epoch + backoff

            conn.execute(
                """
                UPDATE aura_outbox_messages
                SET status = ?,
                    attempt_count = ?,
                    next_retry_at = ?,
                    last_error = ?,
                    updated_at = ?
                WHERE message_id = ?
                """,
                (
                    next_status,
                    new_attempt,
                    next_retry,
                    str(error)[:1000],
                    now_iso,
                    message_id,
                ),
            )
            updated_row = conn.execute(
                "SELECT * FROM aura_outbox_messages WHERE message_id = ?",
                (message_id,),
            ).fetchone()
            return OutboxMessage.from_row(updated_row) if updated_row is not None else None

    # =========================================================================
    # 3. CRASH RECOVERY DE MENSAGENS ORFAS EM PROCESSING
    # =========================================================================

    def recover_stale_processing(
        self,
        stale_after_sec: float = DEFAULT_STALE_PROCESSING_SEC,
    ) -> int:
        """
        Recupera mensagens que ficaram presas com status PROCESSING caso o processo
        tenha caido ou reiniciado durante o envio HTTP.
        """
        now_epoch = time.time()
        now_iso = datetime.now(UTC).isoformat()
        threshold = max(0.0, float(stale_after_sec))

        with self._connection() as conn:
            rows = conn.execute(
                "SELECT * FROM aura_outbox_messages WHERE status = ?",
                (OutboxStatus.PROCESSING.value,),
            ).fetchall()

            stale_ids: list[str] = []
            for row in rows:
                if threshold <= 0.0:
                    stale_ids.append(str(row["message_id"]))
                    continue

                updated_epoch = _parse_iso_to_epoch(row["updated_at"])
                if updated_epoch is not None:
                    is_stale = (now_epoch - updated_epoch) >= threshold
                else:
                    # Se updated_at estiver corrompido/invalido, trata como orfao
                    is_stale = True

                if is_stale:
                    stale_ids.append(str(row["message_id"]))

            recovered_count = 0
            for msg_id in stale_ids:
                cur = conn.execute(
                    """
                    UPDATE aura_outbox_messages
                    SET status = ?,
                        next_retry_at = ?,
                        last_error = COALESCE(last_error, 'Recuperado de PROCESSING orfao (crash recovery)'),
                        updated_at = ?
                    WHERE message_id = ? AND status = ?
                    """,
                    (
                        OutboxStatus.PENDING.value,
                        now_epoch,
                        now_iso,
                        msg_id,
                        OutboxStatus.PROCESSING.value,
                    ),
                )
                recovered_count += int(cur.rowcount or 0)

            return recovered_count

    # =========================================================================
    # 4. DRENAGEM EM LOTE E RETENTATIVA (PROCESS_PENDING_BATCH)
    # =========================================================================

    def _default_http_sender(self, msg: OutboxMessage) -> tuple[bool, str | None]:
        """Executa o POST HTTP padrao para destination_url com payload e headers da mensagem."""
        headers = {"Content-Type": "application/json"}
        headers.update(msg.headers)
        try:
            with httpx.Client(timeout=self.http_timeout_sec) as client:
                resp = client.post(
                    msg.destination_url,
                    content=msg.payload_json.encode("utf-8"),
                    headers=headers,
                )
                if 200 <= resp.status_code < 300:
                    return True, None
                return False, f"HTTP {resp.status_code}: {resp.text[:300]}"
        except Exception as exc:
            return False, str(exc)

    def _invoke_sender(
        self,
        msg: OutboxMessage,
        sender_fn: Callable[..., Any] | None = None,
    ) -> tuple[bool, str | None]:
        """Invoca o sender_fn customizado ou o cliente HTTP padrao e normaliza o retorno."""
        effective_sender = sender_fn or self.sender_fn or self._default_http_sender
        try:
            sig = inspect.signature(effective_sender)
            params = [
                p
                for p in sig.parameters.values()
                if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
            ]
            has_varargs = any(
                p.kind == inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values()
            )
            if len(params) >= 3 and not has_varargs:
                raw_res = effective_sender(msg.destination_url, msg.payload, msg.headers)
            else:
                raw_res = effective_sender(msg)

            if inspect.isawaitable(raw_res):
                import asyncio

                try:
                    asyncio.get_running_loop()
                    # Executa a corrotina em thread isolada se ja houver loop ativo
                    res_holder: list[Any] = []
                    err_holder: list[BaseException] = []

                    def _run_coro() -> None:
                        try:
                            res_holder.append(asyncio.run(raw_res))
                        except BaseException as e:
                            err_holder.append(e)

                    t = threading.Thread(target=_run_coro)
                    t.start()
                    t.join(timeout=self.http_timeout_sec + 2.0)
                    if err_holder:
                        raise err_holder[0]
                    raw_res = res_holder[0] if res_holder else False
                except RuntimeError:
                    raw_res = asyncio.run(raw_res)

            if isinstance(raw_res, tuple) and len(raw_res) == 2:
                ok = bool(raw_res[0])
                err = str(raw_res[1]) if (raw_res[1] is not None and not ok) else None
                return ok, err
            if isinstance(raw_res, bool):
                return raw_res, (None if raw_res else "Sender retornou False")
            if isinstance(raw_res, dict):
                ok = bool(raw_res.get("success", False))
                err = str(raw_res.get("error") or "Falha no envio") if not ok else None
                return ok, err
            if hasattr(raw_res, "success"):
                ok = bool(raw_res.success)
                err = str(getattr(raw_res, "error", None) or "Falha no envio") if not ok else None
                return ok, err
            return bool(raw_res), (None if raw_res else "Sender retornou resultado falso")
        except Exception as exc:
            return False, str(exc)

    def process_pending_batch(
        self,
        limit: int = 20,
        sender_fn: Callable[..., Any] | None = None,
        *,
        force: bool = False,
        now: float | None = None,
    ) -> OutboxBatchResult:
        """
        Processa em lote mensagens PENDING ou FAILED_RETRY prontas para envio:
        1. Recupera mensagens orfas presas em PROCESSING acima do timeout.
        2. Seleciona ate `limit` mensagens com next_retry_at <= now (ou todas se force=True).
        3. Reivindica atomicamente como PROCESSING, executa o envio e atualiza para DELIVERED,
           FAILED_RETRY (com backoff exponencial) ou DEAD_LETTER (ao atingir max_attempts).
        """
        batch_limit = max(1, min(int(limit), 500))
        effective_now = float(now) if now is not None else time.time()

        recovered = self.recover_stale_processing(self.stale_processing_timeout_sec)
        result = OutboxBatchResult(recovered_stale=recovered)

        with self._connection() as conn:
            if force:
                rows = conn.execute(
                    """
                    SELECT * FROM aura_outbox_messages
                    WHERE status IN (?, ?)
                    ORDER BY next_retry_at ASC, created_at ASC
                    LIMIT ?
                    """,
                    (
                        OutboxStatus.PENDING.value,
                        OutboxStatus.FAILED_RETRY.value,
                        batch_limit,
                    ),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM aura_outbox_messages
                    WHERE status IN (?, ?) AND next_retry_at <= ?
                    ORDER BY next_retry_at ASC, created_at ASC
                    LIMIT ?
                    """,
                    (
                        OutboxStatus.PENDING.value,
                        OutboxStatus.FAILED_RETRY.value,
                        effective_now,
                        batch_limit,
                    ),
                ).fetchall()

        candidates = [OutboxMessage.from_row(r) for r in rows]

        for candidate in candidates:
            processing_msg = self.mark_processing(
                candidate.message_id,
                respect_backoff=not force,
                now=effective_now,
            )
            if processing_msg is None:
                continue

            ok, err_msg = self._invoke_sender(processing_msg, sender_fn=sender_fn)
            if ok:
                updated = self.mark_delivered(processing_msg.message_id)
                result.delivered += 1
            else:
                updated = self.mark_failed_attempt(
                    processing_msg.message_id,
                    error=err_msg or "Falha de rede durante process_pending_batch",
                )
                if updated is not None and updated.status == OutboxStatus.DEAD_LETTER.value:
                    result.dead_letter += 1
                else:
                    result.failed_retry += 1

            result.processed += 1
            if updated is not None:
                result.messages.append(updated.to_dict())

        return result

    # =========================================================================
    # 5. GESTAO DE DLQ, OBSERVABILIDADE E EXPURGO
    # =========================================================================

    def requeue_dead_letters(self, limit: int = 50) -> int:
        """
        Reabilita mensagens da fila DEAD_LETTER de volta para PENDING com attempt_count=0
        para que sejam reprocessadas imediatamente.
        """
        batch_limit = max(1, min(int(limit), 500))
        now_epoch = time.time()
        now_iso = datetime.now(UTC).isoformat()

        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT message_id FROM aura_outbox_messages
                WHERE status = ?
                ORDER BY updated_at ASC
                LIMIT ?
                """,
                (OutboxStatus.DEAD_LETTER.value, batch_limit),
            ).fetchall()

            ids = [str(r["message_id"]) for r in rows]
            requeued_count = 0
            for msg_id in ids:
                cur = conn.execute(
                    """
                    UPDATE aura_outbox_messages
                    SET status = ?,
                        attempt_count = 0,
                        next_retry_at = ?,
                        last_error = NULL,
                        updated_at = ?
                    WHERE message_id = ? AND status = ?
                    """,
                    (
                        OutboxStatus.PENDING.value,
                        now_epoch,
                        now_iso,
                        msg_id,
                        OutboxStatus.DEAD_LETTER.value,
                    ),
                )
                requeued_count += int(cur.rowcount or 0)
            return requeued_count

    def list_messages(
        self,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Lista mensagens da Outbox com filtro opcional por status."""
        safe_limit = max(1, min(int(limit), 500))
        with self._connection() as conn:
            if status and status.strip():
                norm_status = status.strip().upper()
                rows = conn.execute(
                    """
                    SELECT * FROM aura_outbox_messages
                    WHERE UPPER(status) = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (norm_status, safe_limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM aura_outbox_messages
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (safe_limit,),
                ).fetchall()

        return [OutboxMessage.from_row(r).to_dict() for r in rows]

    def get_stats(self) -> dict[str, int]:
        """Retorna estatisticas consolidadas por status da fila Outbox."""
        stats = {
            "pending": 0,
            "processing": 0,
            "delivered": 0,
            "failed_retry": 0,
            "dead_letter": 0,
            "total": 0,
        }
        status_map = {
            OutboxStatus.PENDING.value: "pending",
            OutboxStatus.PROCESSING.value: "processing",
            OutboxStatus.DELIVERED.value: "delivered",
            OutboxStatus.FAILED_RETRY.value: "failed_retry",
            OutboxStatus.DEAD_LETTER.value: "dead_letter",
        }
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT status, COUNT(*) AS cnt
                FROM aura_outbox_messages
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

    def purge_delivered(self, older_than_sec: float = 86400 * 7) -> int:
        """Remove mensagens ja entregues (DELIVERED) mais antigas que older_than_sec."""
        threshold = float(older_than_sec)
        now_epoch = time.time()

        with self._connection() as conn:
            if threshold <= 0.0:
                cur = conn.execute(
                    "DELETE FROM aura_outbox_messages WHERE status = ?",
                    (OutboxStatus.DELIVERED.value,),
                )
                return int(cur.rowcount or 0)

            rows = conn.execute(
                """
                SELECT message_id, delivered_at, updated_at
                FROM aura_outbox_messages
                WHERE status = ?
                """,
                (OutboxStatus.DELIVERED.value,),
            ).fetchall()

            to_delete: list[str] = []
            for row in rows:
                ts_epoch = _parse_iso_to_epoch(row["delivered_at"] or row["updated_at"])
                if ts_epoch is not None and (now_epoch - ts_epoch) >= threshold:
                    to_delete.append(str(row["message_id"]))

            for msg_id in to_delete:
                conn.execute(
                    "DELETE FROM aura_outbox_messages WHERE message_id = ?",
                    (msg_id,),
                )
            return len(to_delete)

    # =========================================================================
    # 6. WORKER EM BACKGROUND THREAD-SAFE
    # =========================================================================

    @property
    def is_worker_running(self) -> bool:
        """Indica se a thread de drenagem em background esta ativa."""
        with self._lock:
            return self._worker_thread is not None and self._worker_thread.is_alive()

    def start_worker(
        self,
        poll_interval_sec: float | None = None,
        sender_fn: Callable[..., Any] | None = None,
    ) -> bool:
        """Inicia o worker de drenagem periodica da Outbox em background."""
        with self._lock:
            if self._worker_thread is not None and self._worker_thread.is_alive():
                return True
            if poll_interval_sec is not None:
                self.poll_interval_sec = max(0.05, float(poll_interval_sec))
            if sender_fn is not None:
                self.sender_fn = sender_fn

            self._stop_event.clear()
            self._worker_thread = threading.Thread(
                target=self._worker_loop,
                name="AuraTransactionalOutboxWorker",
                daemon=True,
            )
            self._worker_thread.start()
            return True

    def stop_worker(self, timeout_sec: float = 5.0) -> bool:
        """Para graciosamente o worker em background."""
        thread_to_join: threading.Thread | None = None
        with self._lock:
            self._stop_event.set()
            if self._worker_thread is not None and self._worker_thread.is_alive():
                thread_to_join = self._worker_thread
            self._worker_thread = None

        if thread_to_join is not None:
            thread_to_join.join(timeout=max(0.1, float(timeout_sec)))
            return not thread_to_join.is_alive()
        return True

    def _worker_loop(self) -> None:
        """Loop continuo do worker em background."""
        while not self._stop_event.is_set():
            try:
                self.process_pending_batch()
            except Exception as exc:
                logger.warning("Erro no ciclo do worker da Transactional Outbox: %s", exc)
            self._stop_event.wait(timeout=self.poll_interval_sec)

    def close(self) -> None:
        """Encerra o worker e fecha conexoes persistentes em memoria."""
        self.stop_worker()
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

_GLOBAL_OUTBOX: AuraTransactionalOutbox | None = None
_GLOBAL_OUTBOX_EXPLICIT: bool = False
_GLOBAL_OUTBOX_LOCK = threading.RLock()


def get_transactional_outbox() -> AuraTransactionalOutbox:
    """Retorna a instancia singleton ativa da AuraTransactionalOutbox."""
    global _GLOBAL_OUTBOX, _GLOBAL_OUTBOX_EXPLICIT
    with _GLOBAL_OUTBOX_LOCK:
        env_path = os.getenv("AURA_OUTBOX_DB_PATH")
        if (
            _GLOBAL_OUTBOX is not None
            and not _GLOBAL_OUTBOX_EXPLICIT
            and env_path
            and env_path.strip()
            and _GLOBAL_OUTBOX.db_path != env_path.strip()
        ):
            _GLOBAL_OUTBOX.close()
            _GLOBAL_OUTBOX = None

        if _GLOBAL_OUTBOX is None:
            _GLOBAL_OUTBOX = AuraTransactionalOutbox()
            _GLOBAL_OUTBOX_EXPLICIT = False
        return _GLOBAL_OUTBOX


def set_transactional_outbox(outbox: AuraTransactionalOutbox | None) -> None:
    """Permite injetar ou substituir a instancia global da AuraTransactionalOutbox."""
    global _GLOBAL_OUTBOX, _GLOBAL_OUTBOX_EXPLICIT
    with _GLOBAL_OUTBOX_LOCK:
        _GLOBAL_OUTBOX = outbox
        _GLOBAL_OUTBOX_EXPLICIT = outbox is not None


def reset_transactional_outbox() -> None:
    """Reseta o singleton global da Outbox (utilitario para isolamento de testes)."""
    global _GLOBAL_OUTBOX, _GLOBAL_OUTBOX_EXPLICIT
    with _GLOBAL_OUTBOX_LOCK:
        if _GLOBAL_OUTBOX is not None:
            _GLOBAL_OUTBOX.close()
        _GLOBAL_OUTBOX = None
        _GLOBAL_OUTBOX_EXPLICIT = False


__all__ = [
    "AuraTransactionalOutbox",
    "OutboxBatchResult",
    "OutboxMessage",
    "OutboxStatus",
    "compute_next_backoff",
    "get_transactional_outbox",
    "reset_transactional_outbox",
    "set_transactional_outbox",
]
