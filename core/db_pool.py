"""
Gerenciador Centralizado de Connection Pools para PostgreSQL (ERP e pgvector).
Implementa psycopg2.pool.ThreadedConnectionPool com recuperacao automatica,
isolamento por thread e devolucao garantida via context managers e proxies gerenciados.
Zero travessoes em todo o modulo.
"""

import logging
import threading
from contextlib import contextmanager, suppress
from typing import Any

import psycopg2
from psycopg2 import pool

from config.settings import (
    DB_ERP_CONFIG,
    DB_VECTOR_CONFIG,
    get_erp_password,
)
from core.tenancy import (
    TenantContext,
    inject_rls_filial_context,
    validate_filial_id,
)

logger = logging.getLogger("AuraDBPool")

# Lock global para instanciacao singleton thread-safe dos pools
_pool_lock = threading.Lock()

_erp_pool: pool.ThreadedConnectionPool | None = None
_vector_pool: pool.ThreadedConnectionPool | None = None
_last_working_erp_port: int | None = None


class PooledConnectionWrapper:
    """
    Proxy em torno de uma conexao psycopg2 emprestada de um ThreadedConnectionPool.
    Permite uso tanto como conexao direta (com .close() que devolve ao pool)
    quanto como context manager (devolvendo ao pool ao sair do bloco 'with').
    """

    def __init__(
        self,
        real_conn,
        pool_instance: pool.ThreadedConnectionPool,
        rls_filial_id: int | None = None,
    ):
        self._real_conn = real_conn
        self._pool = pool_instance
        self._rls_filial_id = rls_filial_id
        self._returned = False
        self._lock = threading.Lock()

    @property
    def rls_filial_id(self) -> int | None:
        """Retorna o identificador de filial RLS injetado nesta sessao, se houver."""
        return self._rls_filial_id

    def close(self):
        """Devolve a conexao de volta ao pool de forma idempotente."""
        with self._lock:
            if not self._returned:
                self._returned = True
                with suppress(Exception):
                    if self._real_conn.closed:
                        self._pool.putconn(self._real_conn, close=True)
                    else:
                        with suppress(Exception):
                            self._real_conn.rollback()
                        self._pool.putconn(self._real_conn)

    @property
    def closed(self) -> bool:
        return self._returned or bool(self._real_conn.closed)

    def __getattr__(self, item):
        return getattr(self._real_conn, item)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            with suppress(Exception):
                self._real_conn.rollback()
        self.close()

    def __del__(self):
        with suppress(Exception):
            self.close()


def _create_erp_pool(
    minconn: int = 2,
    maxconn: int = 10,
    timeout: int = 2,
) -> pool.ThreadedConnectionPool:
    """
    Cria pool gerenciado para o banco ERP com deteccao automatica da porta funcional.
    Tenta primeiramente a porta configurada (5433).
    """
    global _last_working_erp_port
    config = dict(DB_ERP_CONFIG)
    config["password"] = get_erp_password()
    configured_port = int(config.get("port", 5433))

    ports_to_try = [configured_port]
    if _last_working_erp_port and _last_working_erp_port not in ports_to_try:
        ports_to_try.insert(0, _last_working_erp_port)

    last_exc = None
    for port in ports_to_try:
        try_config = dict(config)
        try_config["port"] = port
        try_config["connect_timeout"] = timeout
        try:
            p = pool.ThreadedConnectionPool(
                minconn=minconn,
                maxconn=maxconn,
                **try_config,
            )
            _last_working_erp_port = port
            logger.info(f"ERP ThreadedConnectionPool inicializado na porta {port} (min={minconn}, max={maxconn}).")
            return p
        except (psycopg2.Error, OSError, RuntimeError, UnicodeDecodeError) as exc:
            try:
                last_exc = str(exc)
            except Exception:
                last_exc = repr(exc)
            continue

    raise psycopg2.OperationalError(
        f"Falha ao inicializar ERP ThreadedConnectionPool em todas as portas testadas {ports_to_try}: {last_exc}"
    )


def _create_vector_pool(
    minconn: int = 2,
    maxconn: int = 8,
    timeout: int = 2,
) -> pool.ThreadedConnectionPool:
    """
    Cria pool gerenciado para o banco vetorial posto_ai (porta 5433).
    Aplica search_path=aura_core,public e isolamento de schemas com o Sentinel (n3_sre).
    """
    config = dict(DB_VECTOR_CONFIG)
    config["connect_timeout"] = timeout
    p = pool.ThreadedConnectionPool(
        minconn=minconn,
        maxconn=maxconn,
        **config,
    )
    port = config.get("port", 5433)
    logger.info(
        f"Vector ThreadedConnectionPool inicializado no posto_ai:{port} com schema aura_core (min={minconn}, max={maxconn})."
    )
    return p


def get_erp_pool() -> pool.ThreadedConnectionPool:
    """Retorna o pool singleton do banco ERP de forma thread-safe."""
    global _erp_pool
    if _erp_pool is None:
        with _pool_lock:
            if _erp_pool is None:
                _erp_pool = _create_erp_pool()
    return _erp_pool


def get_vector_pool() -> pool.ThreadedConnectionPool:
    """Retorna o pool singleton do banco vetorial pgvector de forma thread-safe."""
    global _vector_pool
    if _vector_pool is None:
        with _pool_lock:
            if _vector_pool is None:
                _vector_pool = _create_vector_pool()
    return _vector_pool


def get_erp_connection(timeout: int | None = None) -> PooledConnectionWrapper:
    """
    Obtem conexao do pool ERP envolvida em PooledConnectionWrapper.
    Ao chamar .close() ou sair de bloco 'with', a conexao retorna ao pool.
    """
    p = get_erp_pool()
    conn = p.getconn()
    if conn.closed:
        p.putconn(conn, close=True)
        conn = p.getconn()
    with suppress(Exception):
        conn.set_client_encoding('UTF8')
    return PooledConnectionWrapper(conn, p)


def get_vector_connection(filial_id: int | None = None) -> PooledConnectionWrapper:
    """
    Obtem conexao do pool pgvector envolvida em PooledConnectionWrapper.
    Quando filial_id e informado (ou esta ativo no TenantContext), injeta
    automaticamente 'SET SESSION app.current_filial = ...' para isolamento RLS.
    Ao chamar .close() ou sair de bloco 'with', a conexao retorna ao pool.
    """
    effective_filial = filial_id if filial_id is not None else TenantContext.get_filial_id()
    if effective_filial is not None:
        effective_filial = validate_filial_id(effective_filial)

    p = get_vector_pool()
    conn = p.getconn()
    if conn.closed:
        p.putconn(conn, close=True)
        conn = p.getconn()
    with suppress(Exception):
        conn.set_client_encoding('UTF8')

    if effective_filial is not None:
        try:
            inject_rls_filial_context(conn, effective_filial, session_scope=True)
        except Exception:
            with suppress(Exception):
                p.putconn(conn)
            raise

    return PooledConnectionWrapper(conn, p, rls_filial_id=effective_filial)


@contextmanager
def get_erp_db_connection(timeout: int | None = None):
    """
    Context manager thread-safe para obtencao de conexao com o banco ERP a partir do pool.
    Garante devolucao automatica ao pool no bloco finally.
    """
    wrapper = get_erp_connection(timeout=timeout)
    try:
        yield wrapper
    finally:
        wrapper.close()


@contextmanager
def get_vector_db_connection(filial_id: int | None = None):
    """
    Context manager thread-safe para obtencao de conexao com o banco vetorial pgvector a partir do pool.
    Garante devolucao automatica ao pool no bloco finally.
    """
    wrapper = get_vector_connection(filial_id=filial_id)
    try:
        yield wrapper
    finally:
        wrapper.close()


def close_all_pools():
    """Encerra todas as conexoes ativas em ambos os pools de conexao."""
    global _erp_pool, _vector_pool
    with _pool_lock:
        if _erp_pool is not None:
            with suppress(Exception):
                _erp_pool.closeall()
            _erp_pool = None

        if _vector_pool is not None:
            with suppress(Exception):
                _vector_pool.closeall()
            _vector_pool = None


def get_pool_status() -> dict[str, Any]:
    """Retorna estado e telemetria dos connection pools."""
    status = {
        "erp_pool": {"active": False},
        "vector_pool": {"active": False},
    }
    with _pool_lock:
        if _erp_pool is not None:
            status["erp_pool"] = {
                "active": True,
                "closed": _erp_pool.closed,
                "minconn": _erp_pool.minconn,
                "maxconn": _erp_pool.maxconn,
            }
        if _vector_pool is not None:
            status["vector_pool"] = {
                "active": True,
                "closed": _vector_pool.closed,
                "minconn": _vector_pool.minconn,
                "maxconn": _vector_pool.maxconn,
            }
    return status
