"""
Testes Unitarios: Carbon Core P0.2 - Particionamento Multi-Tenant + TTL no Cache Semantico,
Busca HNSW Pura e Correcao Matematica de evidencia_insuficiente no HybridRAGEngine.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from core.migrations import ensure_semantic_cache_partition_schema
from core.rag_engine import HybridRAGEngine


class _InMemoryPartitionedCacheCursor:
    """Simula perguntas_cache particionada com TTL e cosseno deterministico."""

    def __init__(self, rows: list[dict[str, Any]], executed_sql: list[tuple[str, Any]]) -> None:
        self._rows = rows
        self._executed_sql = executed_sql
        self._result: Any = None

    def execute(self, sql: str, params: Any = None) -> None:
        self._executed_sql.append((sql, params))
        sql_up = sql.strip().upper()
        if sql_up.startswith("INSERT INTO PERGUNTAS_CACHE"):
            pergunta, vec_str, resposta, json_prod, tenant_id, filial_id, pack_id = params
            self._rows.append(
                {
                    "pergunta": pergunta,
                    "pergunta_vetor": vec_str,
                    "resposta_llm": resposta,
                    "json_produtos": json_prod,
                    "tenant_id": tenant_id,
                    "filial_id": filial_id,
                    "pack_id": pack_id,
                    "created_at": datetime.now(UTC),
                }
            )
            self._result = None
        elif "FROM PERGUNTAS_CACHE" in sql_up:
            _vec1, tenant_id, filial_id, pack_id, ttl_seconds, _vec2 = params
            cutoff = datetime.now(UTC) - timedelta(seconds=int(ttl_seconds))
            matched = [
                r
                for r in self._rows
                if r["tenant_id"] == tenant_id
                and r["filial_id"] == filial_id
                and r["pack_id"] == pack_id
                and r["created_at"] >= cutoff
            ]
            if matched:
                top = dict(matched[-1])
                top["cosine_similarity"] = 0.99
                self._result = top
            else:
                self._result = None

    def fetchone(self) -> Any:
        return self._result

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None


class _FakeConn:
    def __init__(self, cursor_factory_fn) -> None:
        self._cursor_factory_fn = cursor_factory_fn
        self.committed = False

    def cursor(self, *args, **kwargs):
        return self._cursor_factory_fn()

    def commit(self) -> None:
        self.committed = True

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None


@pytest.mark.unit
def test_semantic_cache_migration_is_idempotent_sqlite() -> None:
    """Garante que a migracao de particionamento e TTL em perguntas_cache e idempotente."""
    conn = sqlite3.connect(":memory:")
    try:
        res1 = ensure_semantic_cache_partition_schema(conn, dialect="sqlite")
        res2 = ensure_semantic_cache_partition_schema(conn, dialect="sqlite")
        assert res1["status"] == "ok"
        assert res2["status"] == "ok"

        cur = conn.cursor()
        cur.execute("PRAGMA table_info(perguntas_cache);")
        cols = {row[1] for row in cur.fetchall()}
        assert {"tenant_id", "filial_id", "pack_id", "created_at"}.issubset(cols)
    finally:
        conn.close()


@pytest.mark.unit
def test_semantic_cache_isolates_tenants_and_enforces_ttl(monkeypatch) -> None:
    """
    Valida P0.2:
    1. Cache gravado por tenant_a nunca e retornado para tenant_b.
    2. Cache gravado para pack_id='fuel_convenience' nunca vaza para 'pharmacy_health'.
    3. Entradas expiradas por TTL sao ignoradas.
    """
    rows: list[dict[str, Any]] = []
    executed_sql: list[tuple[str, Any]] = []

    rag = HybridRAGEngine(gemini_api_key="dummy")
    rag._cache_schema_ready = True
    monkeypatch.setattr(
        rag,
        "_get_connection",
        lambda tenant_id=None, filial_id=None: _FakeConn(
            lambda: _InMemoryPartitionedCacheCursor(rows, executed_sql)
        ),
    )

    vec = [0.1, 0.2, 0.3]
    rag.save_semantic_cache(
        query_text="preco gasolina aditivada",
        query_vector=vec,
        resposta_llm="Gasolina Aditivada custa R$ 6,19.",
        json_produtos=[{"codpro": "1", "preco": 6.19}],
        tenant_id="tenant_a",
        filial_id="1",
        pack_id="fuel_convenience",
    )

    # Mesmo tenant + filial + pack dentro do TTL -> HIT
    hit_a = rag.check_semantic_cache(
        "preco gasolina aditivada",
        query_vector=vec,
        tenant_id="tenant_a",
        filial_id="1",
        pack_id="fuel_convenience",
        ttl_seconds=900,
    )
    assert hit_a is not None
    assert hit_a.get("resposta_llm") == "Gasolina Aditivada custa R$ 6,19."

    # Outro tenant (tenant_b) -> MISS estrito
    miss_b = rag.check_semantic_cache(
        "preco gasolina aditivada",
        query_vector=vec,
        tenant_id="tenant_b",
        filial_id="1",
        pack_id="fuel_convenience",
        ttl_seconds=900,
    )
    assert miss_b is not None
    assert "resposta_llm" not in miss_b

    # Outro pack_id -> MISS estrito
    miss_pack = rag.check_semantic_cache(
        "preco gasolina aditivada",
        query_vector=vec,
        tenant_id="tenant_a",
        filial_id="1",
        pack_id="pharmacy_health",
        ttl_seconds=900,
    )
    assert "resposta_llm" not in miss_pack

    # Entrada expirada por TTL -> MISS estrito
    rows[0]["created_at"] = datetime.now(UTC) - timedelta(seconds=3600)
    miss_expired = rag.check_semantic_cache(
        "preco gasolina aditivada",
        query_vector=vec,
        tenant_id="tenant_a",
        filial_id="1",
        pack_id="fuel_convenience",
        ttl_seconds=900,
    )
    assert "resposta_llm" not in miss_expired

    # Valida que a SQL de consulta usa filtro parametrizado de particao e TTL
    select_queries = [q for q, _ in executed_sql if "FROM perguntas_cache" in q]
    assert select_queries
    assert "tenant_id = %s" in select_queries[0]
    assert "filial_id = %s" in select_queries[0]
    assert "pack_id = %s" in select_queries[0]
    assert "INTERVAL '1 second'" in select_queries[0]


@pytest.mark.unit
def test_evidencia_insuficiente_triggers_on_low_cosine_and_pure_hnsw_sql(monkeypatch) -> None:
    """
    Valida P0.2:
    - Resultados com cosine_similarity=0.25 e fts_score=0.0 disparam evidencia_insuficiente=True
      (corrigindo a falha matematica do limiar RRF morto < 0.008).
    - A query dense_candidates executa ORDER BY embedding <=> %s::halfvec ASC LIMIT 50 puro
      (compativel com Index Scan HNSW) e aplica boost de breadcrumb apenas no RRF externo.
    """
    captured_sql: list[str] = []

    class _WeakMatchCursor:
        def execute(self, sql: str, params: Any = None) -> None:
            captured_sql.append(sql)

        def fetchall(self) -> list[dict[str, Any]]:
            return [
                {
                    "id": 1,
                    "doc_id": "DOC-WEAK",
                    "doc_titulo": "Manual Irrelevante",
                    "doc_url": "",
                    "doc_versao": 1,
                    "breadcrumb": "Geral",
                    "secao": "Outros",
                    "chunk_idx": 0,
                    "chunk_total": 1,
                    "conteudo": "Texto sem relacao real com a consulta.",
                    "n_tokens": 10,
                    "cosine_similarity": 0.25,
                    "fts_score": 0.0,
                    "dense_rank": 1,
                    "sparse_rank": None,
                    "rrf_score": 0.008197,
                }
            ]

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    rag = HybridRAGEngine(gemini_api_key="dummy")
    monkeypatch.setattr(
        rag,
        "_get_connection",
        lambda tenant_id=None, filial_id=None: _FakeConn(lambda: _WeakMatchCursor()),
    )

    res = rag.search_hybrid_procedimentos(
        "como configurar algo totalmente inexistente no pdv",
        query_vector=[0.01] * 8,
        tenant_id="tenant_a",
    )

    assert res["evidencia_insuficiente"] is True
    assert res["telemetry"]["max_cosine_similarity"] == 0.25
    assert res["telemetry"]["max_fts_score"] == 0.0

    # Verifica que a query SQL executou busca HNSW pura em dense_candidates e set_config parametrizado
    main_sql = next(q for q in captured_sql if "WITH dense_candidates" in q)
    dense_block = main_sql.split("dense_search AS")[0]
    assert "ORDER BY embedding <=> %s::halfvec ASC" in dense_block
    assert "LIMIT 50" in dense_block
    assert "ILIKE '%%pdv%%'" not in dense_block
    assert "WHERE cosine_similarity >= %s" in main_sql
    assert any("set_config('hnsw.ef_search', %s, true)" in q for q in captured_sql)


@pytest.mark.unit
def test_get_connection_never_bypasses_rls_on_pool_failure(monkeypatch) -> None:
    """Garante que _get_connection nao faz fallback silencioso para psycopg2.connect sem RLS."""
    import core.rag_engine as rag_mod

    def _fail_pool(*_args, **_kwargs):
        raise RuntimeError("pool_indisponivel")

    connect_called = False

    def _forbidden_connect(*_args, **_kwargs):
        nonlocal connect_called
        connect_called = True
        raise AssertionError("psycopg2.connect sem RLS nao pode ser chamado para DB_VECTOR_CONFIG")

    monkeypatch.setattr(rag_mod, "get_vector_connection", _fail_pool)
    monkeypatch.setattr(rag_mod.psycopg2, "connect", _forbidden_connect)

    rag = HybridRAGEngine(gemini_api_key="dummy")
    with pytest.raises(RuntimeError, match="pool_indisponivel"):
        rag._get_connection(tenant_id="tenant_a", filial_id=1)

    assert connect_called is False
