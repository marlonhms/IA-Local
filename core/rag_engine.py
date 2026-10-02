"""
Motor de Busca Vetorial e RAG Híbrido (HNSW + Full-Text Search + RRF)
com Telemetria para Observabilidade SRE.

Tecnologias:
- PostgreSQL 16 + pgvector (0.8.6+)
- HNSW (Hierarchical Navigable Small World) com vector_cosine_ops e tuning ef_search
- GIN Index com tsvector (Full-Text Search em Português)
- Reciprocal Rank Fusion (RRF) nativo em SQL via CTEs
- Google Gemini Embedding API (gemini-embedding-001)
"""

import os
import re
import sys
import time
import json
import logging
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import google.generativeai as genai

from config.settings import (
    DB_VECTOR_CONFIG,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_LLM_MODEL,
    GEMINI_API_KEY,
)

logger = logging.getLogger("HybridRAG")


def formatar_tsquery_portugues(texto: str) -> str:
    """
    Limpa caracteres especiais e formata a query para full-text search flexível com operador OR (|).
    """
    termos = re.findall(r"[\w]+", texto.lower())
    termos_uteis = [t for t in termos if len(t) > 1 and not t.isdigit()]
    numeros = [t for t in termos if t.isdigit() or any(c.isdigit() for c in t)]
    todos = list(dict.fromkeys(termos_uteis + numeros))
    if not todos:
        return ""
    return " | ".join(todos)


class HybridRAGEngine:
    """Motor de recuperação híbrida (Dense + Sparse) com RRF e métricas SRE."""

    def __init__(
        self,
        db_config: Optional[Dict[str, Any]] = None,
        gemini_api_key: Optional[str] = None,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        llm_model: str = DEFAULT_LLM_MODEL,
        ef_search: int = 100,
        rrf_k: int = 60,
    ):
        self.db_config = db_config or DB_VECTOR_CONFIG
        self.api_key = gemini_api_key or GEMINI_API_KEY
        self.embedding_model = embedding_model
        self.llm_model = llm_model
        self.ef_search = ef_search
        self.rrf_k = rrf_k

        if self.api_key:
            genai.configure(api_key=self.api_key)

    def _get_connection(self):
        """Abre conexão com o PostgreSQL do pgvector."""
        return psycopg2.connect(**self.db_config)

    def gerar_embedding(self, texto: str, task_type: str = "retrieval_query") -> List[float]:
        """Gera embedding de 768 dimensões com o Gemini."""
        res = genai.embed_content(
            model=self.embedding_model,
            content=texto,
            output_dimensionality=768,
            task_type=task_type,
        )
        return res["embedding"]

    def check_semantic_cache(self, query_text: str, similarity_threshold: float = 0.96) -> Optional[Dict[str, Any]]:
        """Verifica se há resposta idêntica ou equivalente já armazenada em cache."""
        query_vector = self.gerar_embedding(query_text, task_type="retrieval_query")
        sql = """
        SELECT resposta_llm, json_produtos, 
               1 - (pergunta_vetor <=> %s::halfvec) AS cosine_similarity
        FROM perguntas_cache
        ORDER BY pergunta_vetor <=> %s::halfvec
        LIMIT 1;
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    vec_str = str(query_vector)
                    cur.execute(sql, (vec_str, vec_str))
                    row = cur.fetchone()

            if row and row['cosine_similarity'] >= similarity_threshold:
                return {
                    "resposta_llm": row["resposta_llm"],
                    "json_produtos": row["json_produtos"],
                    "cosine_similarity": row["cosine_similarity"],
                    "query_vector": query_vector
                }
        except Exception as e:
            logger.error(f"Erro no cache semântico: {e}")
        return {"query_vector": query_vector}

    def save_semantic_cache(self, query_text: str, query_vector: List[float], resposta_llm: str, json_produtos: Any):
        """Salva a resposta do catálogo no cache semântico evitando erros ou respostas vazias."""
        frases_bloqueio = ["não há registros", "erro", "indisponível", "não foi possível", "não encontrei"]
        if any(fb in resposta_llm.lower() for fb in frases_bloqueio):
            return

        sql = """
        INSERT INTO perguntas_cache (pergunta, pergunta_vetor, resposta_llm, json_produtos)
        VALUES (%s, %s::halfvec, %s, %s);
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (query_text, str(query_vector), resposta_llm, json.dumps(json_produtos, default=str)))
                conn.commit()
        except Exception as e:
            logger.error(f"Erro ao salvar no cache semântico: {e}")

    def search_hybrid(
        self,
        query_text: str,
        top_k: int = 5,
        dense_weight: float = 0.5,
        sparse_weight: float = 0.5,
        ef_search: Optional[int] = None,
        query_vector: Optional[List[float]] = None,
        grupo_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Busca híbrida usando Reciprocal Rank Fusion (RRF) em SQL nativo."""
        ef = ef_search or self.ef_search
        t0 = time.perf_counter()

        t_emb_start = time.perf_counter()
        if not query_vector:
            query_vector = self.gerar_embedding(query_text, task_type="retrieval_query")
        emb_latency_ms = (time.perf_counter() - t_emb_start) * 1000

        tsquery_str = formatar_tsquery_portugues(query_text)
        like_term = f"%{query_text.strip()}%"

        grupo_condition = ""
        if grupo_filter:
            grupo_condition = "AND grupo ILIKE %s"

        sql_rrf = f"""
        SET LOCAL hnsw.ef_search = {ef};

        WITH dense_search AS (
            SELECT 
                codpro, nompro, grupo, codbar, unidade, preco, texto_busca,
                1 - (embedding <=> %s::halfvec) AS cosine_similarity,
                ROW_NUMBER() OVER (ORDER BY embedding <=> %s::halfvec) AS dense_rank
            FROM produtos_vetores
            WHERE embedding IS NOT NULL {grupo_condition}
            ORDER BY embedding <=> %s::halfvec
            LIMIT %s
        ),
        sparse_search AS (
            SELECT 
                codpro, nompro, grupo, codbar, unidade, preco, texto_busca,
                CASE 
                    WHEN %s <> '' AND to_tsquery('portuguese', %s) IS NOT NULL THEN
                        ts_rank_cd(tsv, to_tsquery('portuguese', %s))
                    ELSE 0.0
                END AS fts_score,
                ROW_NUMBER() OVER (
                    ORDER BY 
                        (CASE WHEN %s <> '' THEN ts_rank_cd(tsv, to_tsquery('portuguese', %s)) ELSE 0.0 END) DESC,
                        (nompro ILIKE %s) DESC,
                        nompro ASC
                ) AS sparse_rank
            FROM produtos_vetores
            WHERE ((%s <> '' AND tsv @@ to_tsquery('portuguese', %s))
               OR nompro ILIKE %s
               OR codbar ILIKE %s
               OR codpro ILIKE %s) {grupo_condition}
            ORDER BY fts_score DESC
            LIMIT %s
        )
        SELECT 
            COALESCE(d.codpro, s.codpro) AS codpro,
            COALESCE(d.nompro, s.nompro) AS nompro,
            COALESCE(d.grupo, s.grupo) AS grupo,
            COALESCE(d.codbar, s.codbar) AS codbar,
            COALESCE(d.unidade, s.unidade) AS unidade,
            COALESCE(d.preco, s.preco) AS preco,
            COALESCE(d.texto_busca, s.texto_busca) AS texto_busca,
            COALESCE(d.cosine_similarity, 0.0) AS cosine_similarity,
            COALESCE(s.fts_score, 0.0) AS fts_score,
            d.dense_rank,
            s.sparse_rank,
            (
                {dense_weight} * COALESCE(1.0 / ({self.rrf_k} + d.dense_rank), 0.0) +
                {sparse_weight} * COALESCE(1.0 / ({self.rrf_k} + s.sparse_rank), 0.0)
            ) AS rrf_score
        FROM dense_search d
        FULL OUTER JOIN sparse_search s ON d.codpro = s.codpro
        ORDER BY rrf_score DESC
        LIMIT %s;
        """

        t_db_start = time.perf_counter()
        fetch_limit = top_k * 3
        vec_str = str(query_vector)

        params = [vec_str, vec_str, vec_str]
        if grupo_filter:
            params.append(grupo_filter)
        params.append(fetch_limit)

        params.extend([
            tsquery_str, tsquery_str, tsquery_str,
            tsquery_str, tsquery_str, like_term,
            tsquery_str, tsquery_str,
            like_term, like_term, like_term
        ])
        if grupo_filter:
            params.append(grupo_filter)
        params.extend([fetch_limit, top_k])

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql_rrf, tuple(params))
                results = cur.fetchall()

        db_latency_ms = (time.perf_counter() - t_db_start) * 1000
        total_latency_ms = (time.perf_counter() - t0) * 1000

        telemetry = {
            "query": query_text,
            "tsquery_used": tsquery_str,
            "embedding_latency_ms": round(emb_latency_ms, 2),
            "db_rrf_latency_ms": round(db_latency_ms, 2),
            "total_retrieval_latency_ms": round(total_latency_ms, 2),
            "hnsw_ef_search": ef,
            "rrf_k": self.rrf_k,
            "dense_weight": dense_weight,
            "sparse_weight": sparse_weight,
            "results_count": len(results),
        }

        return {
            "results": [dict(r) for r in results],
            "telemetry": telemetry,
        }

    def search_dense_only(self, query_text: str, top_k: int = 5, ef_search: Optional[int] = None) -> Dict[str, Any]:
        """Busca puramente semântica (HNSW)."""
        ef = ef_search or self.ef_search
        t0 = time.perf_counter()
        query_vector = self.gerar_embedding(query_text, task_type="retrieval_query")
        emb_ms = (time.perf_counter() - t0) * 1000

        sql = f"""
        SET LOCAL hnsw.ef_search = {ef};
        SELECT 
            codpro, nompro, grupo, codbar, unidade, preco, texto_busca,
            1 - (embedding <=> %s::halfvec) AS cosine_similarity
        FROM produtos_vetores
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %s::halfvec
        LIMIT %s;
        """
        t_db = time.perf_counter()
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                vec_str = str(query_vector)
                cur.execute(sql, (vec_str, vec_str, top_k))
                results = cur.fetchall()
        db_ms = (time.perf_counter() - t_db) * 1000

        return {
            "results": [dict(r) for r in results],
            "telemetry": {
                "type": "dense_hnsw",
                "embedding_latency_ms": round(emb_ms, 2),
                "db_latency_ms": round(db_ms, 2),
                "total_latency_ms": round(emb_ms + db_ms, 2),
            }
        }

    def search_sparse_only(self, query_text: str, top_k: int = 5) -> Dict[str, Any]:
        """Busca puramente lexical (GIN Full-Text Search)."""
        t0 = time.perf_counter()
        tsquery_str = formatar_tsquery_portugues(query_text)
        like_term = f"%{query_text.strip()}%"

        sql = """
        SELECT 
            codpro, nompro, grupo, codbar, unidade, preco, texto_busca,
            CASE 
                WHEN %s <> '' AND to_tsquery('portuguese', %s) IS NOT NULL THEN
                    ts_rank_cd(tsv, to_tsquery('portuguese', %s))
                ELSE 0.0
            END AS fts_score
        FROM produtos_vetores
        WHERE (%s <> '' AND tsv @@ to_tsquery('portuguese', %s))
           OR nompro ILIKE %s
           OR codbar ILIKE %s
           OR codpro ILIKE %s
        ORDER BY fts_score DESC, nompro ASC
        LIMIT %s;
        """
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    sql,
                    (
                        tsquery_str, tsquery_str, tsquery_str,
                        tsquery_str, tsquery_str,
                        like_term, like_term, like_term,
                        top_k
                    )
                )
                results = cur.fetchall()
        db_ms = (time.perf_counter() - t0) * 1000

        return {
            "results": [dict(r) for r in results],
            "telemetry": {
                "type": "sparse_fts",
                "tsquery_used": tsquery_str,
                "db_latency_ms": round(db_ms, 2),
                "total_latency_ms": round(db_ms, 2),
            }
        }

    def get_sre_metrics(self) -> Dict[str, Any]:
        """Coleta métricas detalhadas do PostgreSQL para o Painel SRE."""
        metrics = {}
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        count(*) AS total_rows,
                        pg_size_pretty(pg_total_relation_size('produtos_vetores')) AS total_size,
                        pg_size_pretty(pg_relation_size('produtos_vetores')) AS table_size,
                        pg_size_pretty(pg_indexes_size('produtos_vetores')) AS indexes_size
                    FROM produtos_vetores;
                """)
                metrics["table_stats"] = cur.fetchone()

                cur.execute("""
                    SELECT 
                        i.relname AS index_name,
                        am.amname AS index_type,
                        pg_size_pretty(pg_relation_size(i.oid)) AS index_size,
                        COALESCE(stat.idx_scan, 0) AS index_scans,
                        COALESCE(stat.idx_tup_read, 0) AS tuples_read,
                        COALESCE(stat.idx_tup_fetch, 0) AS tuples_fetched
                    FROM pg_class i
                    JOIN pg_am am ON am.oid = i.relam
                    LEFT JOIN pg_stat_user_indexes stat ON stat.indexrelid = i.oid
                    WHERE i.relname IN ('idx_produtos_vetores_hnsw', 'idx_produtos_vetores_tsv_gin', 'produtos_vetores_pkey')
                    ORDER BY pg_relation_size(i.oid) DESC;
                """)
                metrics["index_stats"] = cur.fetchall()

                cur.execute("""
                    SELECT 
                        datname,
                        numbackends AS active_connections,
                        xact_commit,
                        xact_rollback,
                        blks_read,
                        blks_hit,
                        ROUND(
                            100.0 * blks_hit / NULLIF(blks_hit + blks_read, 0), 2
                        ) AS cache_hit_ratio_percent
                    FROM pg_stat_database 
                    WHERE datname = current_database();
                """)
                metrics["database_health"] = cur.fetchone()

                cur.execute("SELECT extname, extversion FROM pg_extension;")
                metrics["extensions"] = cur.fetchall()

        return metrics
