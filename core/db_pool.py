"""
Gerenciador Centralizado de Connection Pools para PostgreSQL (ERP e pgvector).
Implementa psycopg2.pool.ThreadedConnectionPool com recuperacao automatica,
isolamento por thread e devolucao garantida via context managers e proxies gerenciados.
Zero travessoes em todo o modulo.
"""

import logging
import threading
import time
from contextlib import contextmanager
from typing import Dict, Any, Optional
import psycopg2
from psycopg2 import pool

from config.settings import (
    DB_ERP_CONFIG,
    DB_VECTOR_CONFIG,
    get_erp_password,
)

logger = logging.getLogger("AuraDBPool")

# Lock global para instanciacao singleton thread-safe dos pools
_pool_lock = threading.Lock()

_erp_pool: Optional[pool.ThreadedConnectionPool] = None
_vector_pool: Optional[pool.ThreadedConnectionPool] = None
_last_working_erp_port: Optional[int] = None


class PooledConnectionWrapper:
    """
    Proxy em torno de uma conexao psycopg2 emprestada de um ThreadedConnectionPool.
    Permite uso tanto como conexao direta (com .close() que devolve ao pool)
    quanto como context manager (devolvendo ao pool ao sair do bloco 'with').
    """

    def __init__(self, real_conn, pool_instance: pool.ThreadedConnectionPool):
        self._real_conn = real_conn
        self._pool = pool_instance
        self._returned = False
        self._lock = threading.Lock()

    def close(self):
        """Devolve a conexao de volta ao pool de forma idempotente."""
        with self._lock:
            if not self._returned:
                self._returned = True
                try:
                    if self._real_conn.closed:
                        self._pool.putconn(self._real_conn, close=True)
                    else:
                        try:
                            self._real_conn.rollback()
                        except Exception:
                            pass
                        self._pool.putconn(self._real_conn)
                except Exception:
                    pass

    @property
    def closed(self) -> bool:
        return self._returned or bool(self._real_conn.closed)

    def __getattr__(self, item):
        return getattr(self._real_conn, item)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            try:
                self._real_conn.rollback()
            except Exception:
                pass
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


def _create_erp_pool(
    minconn: int = 2,
    maxconn: int = 10,
    timeout: int = 5,
) -> pool.ThreadedConnectionPool:
    """
    Cria pool gerenciado para o banco ERP com deteccao automatica da porta funcional.
    Tenta primeiramente a porta configurada (5433) com fallback para portas alternativas (5435).
    """
    global _last_working_erp_port
    config = dict(DB_ERP_CONFIG)
    config["password"] = get_erp_password()
    configured_port = int(config.get("port", 5433))

    ports_to_try = []
    if _last_working_erp_port:
        ports_to_try.append(_last_working_erp_port)
    if configured_port not in ports_to_try:
        ports_to_try.append(configured_port)
    for alt in (5435, 5433):
        if alt not in ports_to_try:
            ports_to_try.append(alt)

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
        except Exception as exc:
            last_exc = exc
            continue

    raise psycopg2.OperationalError(
        f"Falha ao inicializar ERP ThreadedConnectionPool em todas as portas testadas {ports_to_try}: {last_exc}"
    )


def _create_vector_pool(
    minconn: int = 2,
    maxconn: int = 8,
    timeout: int = 5,
) -> pool.ThreadedConnectionPool:
    """
    Cria pool gerenciado para o banco vetorial posto_ai (porta 5433).
    """
    config = dict(DB_VECTOR_CONFIG)
    config["connect_timeout"] = timeout
    p = pool.ThreadedConnectionPool(
        minconn=minconn,
        maxconn=maxconn,
        **config,
    )
    logger.info(f"Vector ThreadedConnectionPool inicializado no posto_ai (min={minconn}, max={maxconn}).")
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


def get_erp_connection(timeout: Optional[int] = None) -> PooledConnectionWrapper:
    """
    Obtem conexao do pool ERP envolvida em PooledConnectionWrapper.
    Ao chamar .close() ou sair de bloco 'with', a conexao retorna ao pool.
    """
    p = get_erp_pool()
    conn = p.getconn()
    if conn.closed:
        p.putconn(conn, close=True)
        conn = p.getconn()
    try:
        conn.set_client_encoding('UTF8')
    except Exception:
        pass
    return PooledConnectionWrapper(conn, p)


def get_vector_connection() -> PooledConnectionWrapper:
    """
    Obtem conexao do pool pgvector envolvida em PooledConnectionWrapper.
    Ao chamar .close() ou sair de bloco 'with', a conexao retorna ao pool.
    """
    p = get_vector_pool()
    conn = p.getconn()
    if conn.closed:
        p.putconn(conn, close=True)
        conn = p.getconn()
    try:
        conn.set_client_encoding('UTF8')
    except Exception:
        pass
    return PooledConnectionWrapper(conn, p)


@contextmanager
def get_erp_db_connection(timeout: Optional[int] = None):
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
def get_vector_db_connection():
    """
    Context manager thread-safe para obtencao de conexao com o banco vetorial pgvector a partir do pool.
    Garante devolucao automatica ao pool no bloco finally.
    """
    wrapper = get_vector_connection()
    try:
        yield wrapper
    finally:
        wrapper.close()


def close_all_pools():
    """Encerra todas as conexoes ativas em ambos os pools de conexao."""
    global _erp_pool, _vector_pool
    with _pool_lock:
        if _erp_pool is not None:
            try:
                _erp_pool.closeall()
            except Exception:
                pass
            _erp_pool = None

        if _vector_pool is not None:
            try:
                _vector_pool.closeall()
            except Exception:
                pass
            _vector_pool = None


def get_pool_status() -> Dict[str, Any]:
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
