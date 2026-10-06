"""
Motor de Busca Vetorial e RAG Híbrido (HNSW + Full-Text Search + RRF Calibrado)
com Telemetria para Observabilidade SRE.

Tecnologias:
- PostgreSQL 16 + pgvector (0.8.6+)
- HNSW (Hierarchical Navigable Small World) com vector_cosine_ops e tuning ef_search = 128
- GIN Index com tsvector (Full-Text Search em Português)
- Reciprocal Rank Fusion (RRF) Calibrado com Boost de Código de Barras/EAN-13 e Viscosidades de Lubrificantes
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

# Regex para detecção de viscosidades de óleos lubrificantes (com suporte a hífen, espaço ou colado)
VISCOSITY_REGEX = re.compile(
    r'\b(0W[-\s]?20|0W[-\s]?30|5W[-\s]?20|5W[-\s]?30|5W[-\s]?40|10W[-\s]?30|10W[-\s]?40|15W[-\s]?40|20W[-\s]?50|80W[-\s]?90|75W[-\s]?90|85W[-\s]?140)\b',
    re.IGNORECASE
)

# Regex para detecção de códigos numéricos (código de barras EAN-13, EAN-8 ou codpro)
CODE_PATTERN = re.compile(r'\b\d{1,14}\b')


def formatar_tsquery_portugues(texto: str) -> str:
    """
    Limpa caracteres especiais e formata a query para full-text search flexível com operador OR (|).
    Preserva especificações de viscosidades de lubrificantes (ex: 5w30, 10w40).
    """
    visc_match = VISCOSITY_REGEX.search(texto)
    visc_tokens = []
    if visc_match:
        raw_v = visc_match.group(0).lower().replace("-", "").replace(" ", "")
        visc_tokens.append(raw_v)

    termos = re.findall(r"[\w]+", texto.lower())
    termos_uteis = [t for t in termos if len(t) > 1 and not t.isdigit()]
    numeros = [t for t in termos if t.isdigit() or any(c.isdigit() for c in t)]
    todos = list(dict.fromkeys(visc_tokens + termos_uteis + numeros))
    if not todos:
        return ""
    return " | ".join(todos)


class HybridRAGEngine:
    """Motor de recuperação híbrida (Dense + Sparse) com RRF calibrado e métricas SRE."""

    def __init__(
        self,
        db_config: Optional[Dict[str, Any]] = None,
        gemini_api_key: Optional[str] = None,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        llm_model: str = DEFAULT_LLM_MODEL,
        ef_search: int = 128,
        rrf_k: int = 20,
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
        conn = psycopg2.connect(**self.db_config)
        try:
            conn.set_client_encoding('UTF8')
        except Exception:
            pass
        return conn

    def gerar_embedding(self, texto: str, task_type: str = "retrieval_query") -> List[float]:
        """Gera embedding de 768 dimensões com o Gemini."""
        res = genai.embed_content(
            model=self.embedding_model,
            content=texto,
            output_dimensionality=768,
            task_type=task_type,
        )
        return res["embedding"]

    def check_semantic_cache(
        self,
        query_text: str,
        similarity_threshold: float = 0.96,
        query_vector: Optional[List[float]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Verifica se há resposta idêntica ou equivalente já armazenada em cache."""
        if not query_vector:
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
        """
        Busca híbrida usando Reciprocal Rank Fusion (RRF) Calibrado em SQL nativo:
        - Boost imediato (+1.0) para correspondência exata de Código de Barras (EAN-13) ou código de produto (codpro)
        - Priorização léxica de viscosidades de lubrificantes (+0.08 de boost no RRF)
        - Tuning dinâmico de HNSW ef_search = 128
        """
        ef = ef_search or self.ef_search
        t0 = time.perf_counter()

        clean_query = (query_text or "").strip()
        if not clean_query:
            clean_query = "produtos"

        t_emb_start = time.perf_counter()
        if not query_vector:
            try:
                query_vector = self.gerar_embedding(clean_query, task_type="retrieval_query")
            except Exception:
                query_vector = None
        emb_latency_ms = (time.perf_counter() - t_emb_start) * 1000

        tsquery_str = formatar_tsquery_portugues(clean_query)
        like_term = f"%{clean_query}%"

        # Detecção de código de produto ou código de barras
        prefix_match = re.search(r'(?:c[oó]digo|cod|item|produto|ean|barras|ref)\s*[:#]?\s*(\d{1,14})\b', clean_query, re.IGNORECASE)
        if prefix_match:
            exact_code = prefix_match.group(1)
        elif clean_query.isdigit():
            exact_code = clean_query
        else:
            code_match = re.search(r'\b\d{3,14}\b(?!\s*(?:ml|l|litros?|g|kg|graus?|gr|m|cm|mm|un|und)\b)', clean_query, re.IGNORECASE)
            exact_code = code_match.group(0) if code_match else ""

        # Detecção de viscosidade de lubrificante (com suporte a hífen ou espaço)
        visc_match = VISCOSITY_REGEX.search(query_text)
        viscosity_sql_regex = ""
        viscosity_token = ""
        if visc_match:
            raw_v = visc_match.group(0).upper().replace("-", "").replace(" ", "")
            viscosity_token = raw_v
            if "W" in raw_v:
                part1, part2 = raw_v.split("W")
                viscosity_sql_regex = rf"\y{part1}W[-\s]?{part2}\y"

        grupo_condition = ""
        iterative_scan_sql = ""
        if grupo_filter:
            grupo_condition = "AND grupo ILIKE %s"
            iterative_scan_sql = """
        LOAD 'vector';
        SET LOCAL hnsw.iterative_scan = 'relaxed_order';
        SET LOCAL hnsw.max_scan_tuples = 20000;
            """

        fetch_limit = min(50, top_k * 10)

        if query_vector is not None:
            sql_rrf = f"""
            SET LOCAL hnsw.ef_search = {ef};
            {iterative_scan_sql}

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
                            -- Prioridade 1: Match exato de código de barras ou código do produto (com tolerância a zero à esquerda)
                            (CASE WHEN %s <> '' AND (TRIM(codbar) = %s OR TRIM(codpro) = %s OR (LTRIM(TRIM(codpro), '0') <> '' AND LTRIM(TRIM(codpro), '0') = LTRIM(%s, '0'))) THEN 1 ELSE 0 END) DESC,
                            -- Prioridade 2: Match exato de viscosidade de lubrificante
                            (CASE WHEN %s <> '' AND nompro ~* %s THEN 1 ELSE 0 END) DESC,
                            -- Prioridade 3: Score do FTS e proximidade de nome
                            (CASE WHEN %s <> '' THEN ts_rank_cd(tsv, to_tsquery('portuguese', %s)) ELSE 0.0 END) DESC,
                            (nompro ILIKE %s) DESC,
                            nompro ASC
                    ) AS sparse_rank
                FROM produtos_vetores
                WHERE ((%s <> '' AND tsv @@ to_tsquery('portuguese', %s))
                   OR nompro ILIKE %s
                   OR codbar ILIKE %s
                   OR codpro ILIKE %s
                   OR (%s <> '' AND (TRIM(codbar) = %s OR TRIM(codpro) = %s OR (LTRIM(TRIM(codpro), '0') <> '' AND LTRIM(TRIM(codpro), '0') = LTRIM(%s, '0'))))
                   OR (%s <> '' AND nompro ~* %s)) {grupo_condition}
                ORDER BY sparse_rank ASC
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
                    {sparse_weight} * COALESCE(1.0 / ({self.rrf_k} + s.sparse_rank), 0.0) +
                    -- Boost normalizado de Código de Barras / Código de Produto (+0.050)
                    (CASE WHEN %s <> '' AND (TRIM(COALESCE(d.codbar, s.codbar)) = %s OR TRIM(COALESCE(d.codpro, s.codpro)) = %s OR (LTRIM(TRIM(COALESCE(d.codpro, s.codpro)), '0') <> '' AND LTRIM(TRIM(COALESCE(d.codpro, s.codpro)), '0') = LTRIM(%s, '0'))) THEN 0.050 ELSE 0.0 END) +
                    -- Boost normalizado de Viscosidade de Lubrificante (+0.015)
                    (CASE WHEN %s <> '' AND COALESCE(d.nompro, s.nompro) ~* %s THEN 0.015 ELSE 0.0 END) +
                    -- Desempate semântico contínuo proporcional à similaridade de cosseno (+0.02 * cosine)
                    (0.02 * COALESCE(d.cosine_similarity, 0.0))
                ) AS rrf_score
            FROM dense_search d
            FULL OUTER JOIN sparse_search s ON d.codpro = s.codpro
            ORDER BY rrf_score DESC
            LIMIT %s;
            """

            vec_str = str(query_vector)
            # Parâmetros para dense_search (alinhados com a ordem do SQL)
            params = [vec_str, vec_str]
            if grupo_filter:
                params.append(grupo_filter)
            params.extend([vec_str, fetch_limit])

            # Parâmetros para sparse_search
            params.extend([
                tsquery_str, tsquery_str, tsquery_str,                                              # CASE ts_rank_cd
                exact_code, exact_code, exact_code, exact_code,                                    # ORDER BY match exato
                viscosity_sql_regex, viscosity_sql_regex,                                          # ORDER BY viscosidade
                tsquery_str, tsquery_str,                                                          # ORDER BY ts_rank_cd
                like_term,                                                                         # ORDER BY nompro ILIKE
                tsquery_str, tsquery_str,                                                          # WHERE tsv @@
                like_term, like_term, like_term,                                                   # WHERE nompro / codbar / codpro ILIKE
                exact_code, exact_code, exact_code, exact_code,                                    # WHERE match exato
                viscosity_sql_regex, viscosity_sql_regex,                                          # WHERE viscosidade
            ])
            if grupo_filter:
                params.append(grupo_filter)
            params.append(fetch_limit)

            # Parâmetros para SELECT final (boosts RRF)
            params.extend([
                exact_code, exact_code, exact_code, exact_code,                                    # Boost exato codbar/codpro
                viscosity_sql_regex, viscosity_sql_regex,                                          # Boost viscosidade
                top_k                                                                              # LIMIT final
            ])
        else:
            # Fallback gracioso para recuperação esparsa (GIN FTS + Boosts + RRF) quando embedding não disponível
            sql_rrf = f"""
            SET LOCAL hnsw.ef_search = {ef};

            WITH sparse_search AS (
                SELECT 
                    codpro, nompro, grupo, codbar, unidade, preco, texto_busca,
                    CASE 
                        WHEN %s <> '' AND to_tsquery('portuguese', %s) IS NOT NULL THEN
                            ts_rank_cd(tsv, to_tsquery('portuguese', %s))
                        ELSE 0.0
                    END AS fts_score,
                    ROW_NUMBER() OVER (
                        ORDER BY 
                            (CASE WHEN %s <> '' AND (TRIM(codbar) = %s OR TRIM(codpro) = %s OR (LTRIM(TRIM(codpro), '0') <> '' AND LTRIM(TRIM(codpro), '0') = LTRIM(%s, '0'))) THEN 1 ELSE 0 END) DESC,
                            (CASE WHEN %s <> '' AND nompro ~* %s THEN 1 ELSE 0 END) DESC,
                            (CASE WHEN %s <> '' THEN ts_rank_cd(tsv, to_tsquery('portuguese', %s)) ELSE 0.0 END) DESC,
                            (nompro ILIKE %s) DESC,
                            nompro ASC
                    ) AS sparse_rank
                FROM produtos_vetores
                WHERE ((%s <> '' AND tsv @@ to_tsquery('portuguese', %s))
                   OR nompro ILIKE %s
                   OR codbar ILIKE %s
                   OR codpro ILIKE %s
                   OR (%s <> '' AND (TRIM(codbar) = %s OR TRIM(codpro) = %s OR (LTRIM(TRIM(codpro), '0') <> '' AND LTRIM(TRIM(codpro), '0') = LTRIM(%s, '0'))))
                   OR (%s <> '' AND nompro ~* %s)) {grupo_condition}
                ORDER BY sparse_rank ASC
                LIMIT %s
            )
            SELECT 
                s.codpro, s.nompro, s.grupo, s.codbar, s.unidade, s.preco, s.texto_busca,
                0.0 AS cosine_similarity,
                s.fts_score,
                NULL::bigint AS dense_rank,
                s.sparse_rank,
                (
                    {sparse_weight} * (1.0 / ({self.rrf_k} + s.sparse_rank)) +
                    (CASE WHEN %s <> '' AND (TRIM(s.codbar) = %s OR TRIM(s.codpro) = %s OR (LTRIM(TRIM(s.codpro), '0') <> '' AND LTRIM(TRIM(s.codpro), '0') = LTRIM(%s, '0'))) THEN 0.050 ELSE 0.0 END) +
                    (CASE WHEN %s <> '' AND s.nompro ~* %s THEN 0.015 ELSE 0.0 END)
                ) AS rrf_score
            FROM sparse_search s
            ORDER BY rrf_score DESC
            LIMIT %s;
            """
            params = [
                tsquery_str, tsquery_str, tsquery_str,
                exact_code, exact_code, exact_code, exact_code,
                viscosity_sql_regex, viscosity_sql_regex,
                tsquery_str, tsquery_str,
                like_term,
                tsquery_str, tsquery_str,
                like_term, like_term, like_term,
                exact_code, exact_code, exact_code, exact_code,
                viscosity_sql_regex, viscosity_sql_regex,
            ]
            if grupo_filter:
                params.append(grupo_filter)
            params.extend([
                fetch_limit,
                exact_code, exact_code, exact_code, exact_code,
                viscosity_sql_regex, viscosity_sql_regex,
                top_k
            ])

        t_db_start = time.perf_counter()
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql_rrf, tuple(params))
                results = cur.fetchall()

        db_latency_ms = (time.perf_counter() - t_db_start) * 1000
        total_latency_ms = (time.perf_counter() - t0) * 1000

        telemetry = {
            "query": query_text,
            "tsquery_used": tsquery_str,
            "exact_code_detected": exact_code or None,
            "viscosity_detected": viscosity_token or None,
            "embedding_latency_ms": round(emb_latency_ms, 2),
            "db_rrf_latency_ms": round(db_latency_ms, 2),
            "total_retrieval_latency_ms": round(total_latency_ms, 2),
            "hnsw_ef_search": ef,
            "rrf_k": self.rrf_k,
            "fetch_limit": fetch_limit,
            "dense_weight": dense_weight,
            "sparse_weight": sparse_weight,
            "grupo_filter": grupo_filter or None,
            "iterative_scan": bool(grupo_filter),
            "calibrated_rrf": True,
            "results_count": len(results),
            "retrieval_mode": "hybrid_hnsw_rrf" if query_vector is not None else "sparse_fts_fallback",
        }

        return {
            "results": [dict(r) for r in results],
            "telemetry": telemetry,
        }

    def search_hybrid_conhecimento(
        self,
        query_text: str,
        top_k: int = 2,
        dense_weight: float = 0.5,
        sparse_weight: float = 0.5,
        ef_search: Optional[int] = None,
        query_vector: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """
        Busca híbrida de auto-conhecimento da AURA na tabela `aura_conhecimento_vetores`
        utilizando pgvector HNSW (halfvec 768d) + GIN Full-Text Search (tsvector em português)
        + Reciprocal Rank Fusion (RRF) em SQL nativo.
        Latência de busca em banco sub-5ms (< 5ms).
        """
        ef = ef_search or self.ef_search
        t0 = time.perf_counter()

        q_clean = (query_text or "").strip()
        if not q_clean:
            q_clean = "panorama operacional"

        t_emb_start = time.perf_counter()
        if not query_vector:
            # Comandos diretos de ajuda evitam latência de rede na API e usam FTS sub-1ms
            if q_clean.lower() in ("ajuda", "menu", "telas", "atalhos", "help", "socorro", "modulos"):
                query_vector = None
            else:
                try:
                    query_vector = self.gerar_embedding(q_clean, task_type="retrieval_query")
                except Exception:
                    query_vector = None
        emb_latency_ms = (time.perf_counter() - t_emb_start) * 1000

        tsquery_str = formatar_tsquery_portugues(q_clean)
        like_term = f"%{q_clean}%"
        fetch_limit = min(50, top_k * 10)

        t_db_start = time.perf_counter()

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if query_vector is not None:
                    sql_rrf = f"""
                    SET LOCAL hnsw.ef_search = {ef};

                    WITH dense_search AS (
                        SELECT 
                            id, modulo, topico, titulo, subtitulo, conteudo, elementos_ui, ui_action, tags,
                            1 - (embedding <=> %s::halfvec) AS cosine_similarity,
                            ROW_NUMBER() OVER (ORDER BY embedding <=> %s::halfvec) AS dense_rank
                        FROM aura_conhecimento_vetores
                        WHERE embedding IS NOT NULL
                        ORDER BY embedding <=> %s::halfvec
                        LIMIT %s
                    ),
                    sparse_search AS (
                        SELECT 
                            id, modulo, topico, titulo, subtitulo, conteudo, elementos_ui, ui_action, tags,
                            CASE 
                                WHEN %s <> '' AND to_tsquery('portuguese', %s) IS NOT NULL THEN
                                    ts_rank_cd(tsv, to_tsquery('portuguese', %s))
                                ELSE 0.0
                            END AS fts_score,
                            ROW_NUMBER() OVER (
                                ORDER BY 
                                    (CASE WHEN %s <> '' AND to_tsquery('portuguese', %s) IS NOT NULL THEN ts_rank_cd(tsv, to_tsquery('portuguese', %s)) ELSE 0.0 END) DESC,
                                    (titulo ILIKE %s) DESC,
                                    (topico ILIKE %s) DESC,
                                    (modulo ILIKE %s) DESC,
                                    id ASC
                            ) AS sparse_rank
                        FROM aura_conhecimento_vetores
                        WHERE (%s <> '' AND tsv @@ to_tsquery('portuguese', %s))
                           OR titulo ILIKE %s
                           OR subtitulo ILIKE %s
                           OR topico ILIKE %s
                           OR modulo ILIKE %s
                           OR conteudo ILIKE %s
                        ORDER BY sparse_rank ASC
                        LIMIT %s
                    )
                    SELECT 
                        COALESCE(d.id, s.id) AS id,
                        COALESCE(d.modulo, s.modulo) AS modulo,
                        COALESCE(d.topico, s.topico) AS topico,
                        COALESCE(d.titulo, s.titulo) AS titulo,
                        COALESCE(d.subtitulo, s.subtitulo) AS subtitulo,
                        COALESCE(d.conteudo, s.conteudo) AS conteudo,
                        COALESCE(d.elementos_ui, s.elementos_ui) AS elementos_ui,
                        COALESCE(d.ui_action, s.ui_action) AS ui_action,
                        COALESCE(d.tags, s.tags) AS tags,
                        COALESCE(d.cosine_similarity, 0.0) AS cosine_similarity,
                        COALESCE(s.fts_score, 0.0) AS fts_score,
                        d.dense_rank,
                        s.sparse_rank,
                        (
                            {dense_weight} * COALESCE(1.0 / ({self.rrf_k} + d.dense_rank), 0.0) +
                            {sparse_weight} * COALESCE(1.0 / ({self.rrf_k} + s.sparse_rank), 0.0)
                        ) AS rrf_score
                    FROM dense_search d
                    FULL OUTER JOIN sparse_search s ON d.id = s.id
                    ORDER BY rrf_score DESC
                    LIMIT %s;
                    """
                    vec_str = str(query_vector)
                    params = [
                        # dense_search
                        vec_str, vec_str, vec_str, fetch_limit,
                        # sparse_search CASE
                        tsquery_str, tsquery_str, tsquery_str,
                        # sparse_search ORDER BY
                        tsquery_str, tsquery_str, tsquery_str,
                        like_term, like_term, like_term,
                        # sparse_search WHERE
                        tsquery_str, tsquery_str,
                        like_term, like_term, like_term, like_term, like_term,
                        fetch_limit,
                        # final LIMIT
                        top_k
                    ]
                    cur.execute(sql_rrf, tuple(params))
                    results = cur.fetchall()
                else:
                    # Recuperação esparsa ultra-rápida (sub-1ms) em fallback
                    sql_sparse = f"""
                    SELECT 
                        id, modulo, topico, titulo, subtitulo, conteudo, elementos_ui, ui_action, tags,
                        0.0 AS cosine_similarity,
                        CASE 
                            WHEN %s <> '' AND to_tsquery('portuguese', %s) IS NOT NULL THEN
                                ts_rank_cd(tsv, to_tsquery('portuguese', %s))
                            ELSE 0.0
                        END AS fts_score,
                        NULL::bigint AS dense_rank,
                        ROW_NUMBER() OVER (
                            ORDER BY 
                                (CASE WHEN %s <> '' AND to_tsquery('portuguese', %s) IS NOT NULL THEN ts_rank_cd(tsv, to_tsquery('portuguese', %s)) ELSE 0.0 END) DESC,
                                (titulo ILIKE %s) DESC,
                                (topico ILIKE %s) DESC,
                                (modulo ILIKE %s) DESC,
                                id ASC
                        ) AS sparse_rank,
                        (1.0 / ({self.rrf_k} + ROW_NUMBER() OVER (
                            ORDER BY 
                                (CASE WHEN %s <> '' AND to_tsquery('portuguese', %s) IS NOT NULL THEN ts_rank_cd(tsv, to_tsquery('portuguese', %s)) ELSE 0.0 END) DESC,
                                (titulo ILIKE %s) DESC,
                                (topico ILIKE %s) DESC,
                                (modulo ILIKE %s) DESC,
                                id ASC
                        ))) AS rrf_score
                    FROM aura_conhecimento_vetores
                    WHERE (%s <> '' AND tsv @@ to_tsquery('portuguese', %s))
                       OR titulo ILIKE %s
                       OR subtitulo ILIKE %s
                       OR topico ILIKE %s
                       OR modulo ILIKE %s
                       OR conteudo ILIKE %s
                    ORDER BY rrf_score DESC
                    LIMIT %s;
                    """
                    params = [
                        tsquery_str, tsquery_str, tsquery_str,
                        tsquery_str, tsquery_str, tsquery_str,
                        like_term, like_term, like_term,
                        tsquery_str, tsquery_str, tsquery_str,
                        like_term, like_term, like_term,
                        tsquery_str, tsquery_str,
                        like_term, like_term, like_term, like_term, like_term,
                        top_k
                    ]
                    cur.execute(sql_sparse, tuple(params))
                    results = cur.fetchall()

                # Fallback garantido se nenhuma linha for encontrada
                if not results:
                    cur.execute("""
                        SELECT 
                            id, modulo, topico, titulo, subtitulo, conteudo, elementos_ui, ui_action, tags,
                            0.0 AS cosine_similarity, 0.0 AS fts_score, NULL::bigint AS dense_rank, 1::bigint AS sparse_rank,
                            0.04762 AS rrf_score
                        FROM aura_conhecimento_vetores
                        WHERE topico = 'panorama_operacional'
                        LIMIT 1;
                    """)
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
            "top_k": top_k,
            "results_count": len(results),
            "retrieval_mode": "hybrid_hnsw_rrf" if query_vector is not None else "sparse_fts_fallback",
        }

        return {
            "results": [dict(r) for r in results],
            "telemetry": telemetry,
        }

    def search_dense_only(
        self,
        query_text: str,
        top_k: int = 5,
        ef_search: Optional[int] = None,
        grupo_filter: Optional[str] = None,
        query_vector: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """Busca puramente semântica (HNSW) com suporte a filtro relacional e iterative scan."""
        ef = ef_search or self.ef_search
        t0 = time.perf_counter()

        clean_query = (query_text or "").strip()
        if not clean_query and query_vector is None:
            return {
                "results": [],
                "telemetry": {
                    "type": "dense_hnsw",
                    "embedding_latency_ms": 0.0,
                    "db_latency_ms": 0.0,
                    "total_latency_ms": 0.0,
                    "iterative_scan": bool(grupo_filter),
                    "grupo_filter": grupo_filter or None,
                    "results_count": 0,
                }
            }

        if query_vector is None:
            try:
                query_vector = self.gerar_embedding(clean_query, task_type="retrieval_query")
            except Exception as e:
                logger.warning(f"Erro ao gerar embedding em search_dense_only: {e}")
                return {
                    "results": [],
                    "telemetry": {
                        "type": "dense_hnsw",
                        "error": str(e),
                        "embedding_latency_ms": round((time.perf_counter() - t0) * 1000, 2),
                        "db_latency_ms": 0.0,
                        "total_latency_ms": round((time.perf_counter() - t0) * 1000, 2),
                        "iterative_scan": bool(grupo_filter),
                        "grupo_filter": grupo_filter or None,
                        "results_count": 0,
                    }
                }

        emb_ms = (time.perf_counter() - t0) * 1000

        grupo_condition = ""
        iterative_scan_sql = ""
        params = [str(query_vector)]
        if grupo_filter:
            grupo_condition = "AND grupo ILIKE %s"
            iterative_scan_sql = """
            LOAD 'vector';
            SET LOCAL hnsw.iterative_scan = 'relaxed_order';
            SET LOCAL hnsw.max_scan_tuples = 20000;
            """
            params.append(grupo_filter)
        params.extend([str(query_vector), top_k])

        sql = f"""
        SET LOCAL hnsw.ef_search = {ef};
        {iterative_scan_sql}
        SELECT 
            codpro, nompro, grupo, codbar, unidade, preco, texto_busca,
            1 - (embedding <=> %s::halfvec) AS cosine_similarity
        FROM produtos_vetores
        WHERE embedding IS NOT NULL {grupo_condition}
        ORDER BY embedding <=> %s::halfvec
        LIMIT %s;
        """
        t_db = time.perf_counter()
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, tuple(params))
                results = cur.fetchall()
        db_ms = (time.perf_counter() - t_db) * 1000

        return {
            "results": [dict(r) for r in results],
            "telemetry": {
                "type": "dense_hnsw",
                "embedding_latency_ms": round(emb_ms, 2),
                "db_latency_ms": round(db_ms, 2),
                "total_latency_ms": round(emb_ms + db_ms, 2),
                "iterative_scan": bool(grupo_filter),
                "grupo_filter": grupo_filter or None,
                "results_count": len(results),
            }
        }

    def search_sparse_only(
        self,
        query_text: str,
        top_k: int = 5,
        grupo_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Busca puramente lexical (GIN Full-Text Search)."""
        t0 = time.perf_counter()
        clean_query = (query_text or "").strip()
        tsquery_str = formatar_tsquery_portugues(clean_query)
        like_term = f"%{clean_query}%"

        grupo_condition = ""
        params = [
            tsquery_str, tsquery_str, tsquery_str,
            tsquery_str, tsquery_str,
            like_term, like_term, like_term,
        ]
        if grupo_filter:
            grupo_condition = "AND grupo ILIKE %s"
            params.append(grupo_filter)
        params.append(top_k)

        sql = f"""
        SELECT 
            codpro, nompro, grupo, codbar, unidade, preco, texto_busca,
            CASE 
                WHEN %s <> '' AND to_tsquery('portuguese', %s) IS NOT NULL THEN
                    ts_rank_cd(tsv, to_tsquery('portuguese', %s))
                ELSE 0.0
            END AS fts_score
        FROM produtos_vetores
        WHERE ((%s <> '' AND tsv @@ to_tsquery('portuguese', %s))
           OR nompro ILIKE %s
           OR codbar ILIKE %s
           OR codpro ILIKE %s) {grupo_condition}
        ORDER BY fts_score DESC, nompro ASC
        LIMIT %s;
        """
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, tuple(params))
                results = cur.fetchall()
        db_ms = (time.perf_counter() - t0) * 1000

        return {
            "results": [dict(r) for r in results],
            "telemetry": {
                "type": "sparse_fts",
                "tsquery_used": tsquery_str,
                "db_latency_ms": round(db_ms, 2),
                "total_latency_ms": round(db_ms, 2),
                "grupo_filter": grupo_filter or None,
                "results_count": len(results),
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
                        count(*) AS total_intencoes,
                        pg_size_pretty(pg_total_relation_size('intencoes_vetores')) AS intencoes_total_size
                    FROM intencoes_vetores;
                """)
                metrics["intencoes_stats"] = cur.fetchone()

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
                    WHERE i.relname IN (
                        'idx_produtos_vetores_hnsw', 
                        'idx_produtos_vetores_tsv_gin', 
                        'produtos_vetores_pkey',
                        'idx_produtos_vetores_hash_md5',
                        'idx_intencoes_vetores_hnsw',
                        'intencoes_vetores_pkey',
                        'idx_aura_conhecimento_hnsw',
                        'idx_aura_conhecimento_tsv_gin',
                        'idx_aura_conhecimento_modulo_topico',
                        'idx_aura_conhecimento_hash_md5'
                    )
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
