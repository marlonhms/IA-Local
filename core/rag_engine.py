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

import math
import os
import re
import sys
import time
import json
import logging
from typing import List, Dict, Any, Optional, Union
import psycopg2
from psycopg2.extras import RealDictCursor
from core.llm_client import CompatGenAIShim, embed_content as llm_embed_content

genai = CompatGenAIShim()

from config.settings import (
    DB_VECTOR_CONFIG,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_LLM_MODEL,
    GEMINI_API_KEY,
)
from core.db_pool import (
    get_vector_connection,
    get_vector_db_connection,
)
from core.migrations import ensure_semantic_cache_partition_schema
from core.tenancy import (
    TenantContext,
    inject_rls_filial_context,
    inject_rls_tenant_context,
    validate_filial_id,
    validate_tenant_id,
)

logger = logging.getLogger("HybridRAG")

# TTLs padrao para particionamento do cache semantico (Carbon Core P0.2)
DEFAULT_CACHE_TTL_CATALOG_SECONDS = 900
DEFAULT_CACHE_TTL_STATIC_SECONDS = 86400
DEFAULT_MIN_COSINE_EVIDENCE = 0.62
DEFAULT_MIN_FTS_EVIDENCE = 0.05


def _validate_positive_int(value: Any, name: str, min_val: int = 1, max_val: int = 10000) -> int:
    """Valida estritamente inteiro numerico para parametros de consulta SQL/HNSW."""
    if isinstance(value, bool):
        raise ValueError(f"Parametro '{name}' nao pode ser booleano.")
    iv = int(value)
    if iv < min_val or iv > max_val:
        raise ValueError(f"Parametro '{name}' fora dos limites [{min_val}, {max_val}]: {iv}")
    return iv


def _validate_finite_float(value: Any, name: str, min_val: float = 0.0, max_val: float = 10.0) -> float:
    """Valida estritamente numero real finito para pesos RRF e limiares de corte."""
    if isinstance(value, bool):
        raise ValueError(f"Parametro '{name}' nao pode ser booleano.")
    fv = float(value)
    if not math.isfinite(fv) or fv < min_val or fv > max_val:
        raise ValueError(f"Parametro '{name}' invalido ou fora dos limites [{min_val}, {max_val}]: {fv}")
    return fv

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
        self.ef_search = _validate_positive_int(ef_search, "ef_search", min_val=1, max_val=2000)
        self.rrf_k = _validate_positive_int(rrf_k, "rrf_k", min_val=1, max_val=1000)
        self._cache_schema_ready = False
        self._cache_schema_partitioned: Optional[bool] = None

    def _ensure_cache_partition_columns(self, conn) -> bool:
        """
        Verifica se perguntas_cache possui as colunas de particionamento
        (tenant_id, filial_id, pack_id, created_at). Executa rollback seguro caso
        a role de servico nao seja proprietaria da tabela para evitar transacao abortada.
        """
        if self._cache_schema_ready and self._cache_schema_partitioned is not None:
            return self._cache_schema_partitioned

        required = {"tenant_id", "filial_id", "pack_id", "created_at"}
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'perguntas_cache'
                      AND table_schema = ANY(current_schemas(false));
                    """
                )
                present = {row[0] for row in cur.fetchall() if row}
            if required.issubset(present):
                self._cache_schema_ready = True
                self._cache_schema_partitioned = True
                return True
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass

        try:
            ensure_semantic_cache_partition_schema(conn)
            self._cache_schema_ready = True
            self._cache_schema_partitioned = True
            return True
        except Exception as exc:
            try:
                conn.rollback()
            except Exception:
                pass
            if isinstance(exc, psycopg2.Error):
                logger.warning(
                    "Cache semantico particionado indisponivel nesta base (aguardando migracao DDL): %s",
                    exc,
                )
                self._cache_schema_ready = True
                self._cache_schema_partitioned = False
                return False
            self._cache_schema_ready = True
            self._cache_schema_partitioned = True
            return True

    def _resolve_cache_partition(
        self,
        tenant_id: Optional[str] = None,
        filial_id: Optional[Union[str, int]] = None,
        pack_id: Optional[str] = None,
    ) -> tuple[str, str, str]:
        """Resolve a tupla (tenant_id, filial_id, pack_id) ativa para particionamento do cache."""
        eff_tenant = (tenant_id or "").strip()
        if not eff_tenant:
            eff_tenant = TenantContext.get_tenant_id() if TenantContext.get_current() is not None else "default"
        eff_tenant = validate_tenant_id(eff_tenant)

        if filial_id is not None and str(filial_id).strip():
            eff_filial = str(filial_id).strip()
        else:
            ctx_filial = TenantContext.get_filial_id()
            eff_filial = str(ctx_filial) if ctx_filial is not None else "1"

        eff_pack = (pack_id or "").strip()
        if not eff_pack:
            try:
                from core.domain.domain_pack_loader import get_active_domain_pack

                eff_pack = get_active_domain_pack().pack_id
            except Exception:
                eff_pack = "fuel_convenience"

        return eff_tenant, eff_filial, eff_pack

    def _get_connection(self, tenant_id: str | None = None, filial_id: int | None = None):
        """
        Abre conexao com o PostgreSQL do pgvector com isolamento RLS obrigatorio (Carbon Core P0.2).
        Para DB_VECTOR_CONFIG padrao, usa estritamente o pool gerenciado (sem bypass RLS).
        Para db_config customizado, injeta explicitamente o contexto RLS na conexao.
        """
        if self.db_config == DB_VECTOR_CONFIG:
            return get_vector_connection(filial_id=filial_id, tenant_id=tenant_id)

        eff_filial = filial_id if filial_id is not None else TenantContext.get_filial_id()
        if eff_filial is not None:
            eff_filial = validate_filial_id(eff_filial)
        eff_tenant = (
            tenant_id
            if tenant_id is not None
            else (TenantContext.get_tenant_id() if TenantContext.get_current() is not None else None)
        )
        if eff_tenant is not None:
            eff_tenant = validate_tenant_id(eff_tenant)

        conn = psycopg2.connect(**self.db_config)
        try:
            conn.set_client_encoding("UTF8")
        except Exception:
            pass
        if eff_filial is not None:
            inject_rls_filial_context(conn, eff_filial, session_scope=True)
        if eff_tenant is not None:
            inject_rls_tenant_context(conn, eff_tenant, session_scope=True)
        return conn

    def ensure_semantic_cache_schema(self, conn: Any = None) -> None:
        """Executa migracao idempotente de particionamento/TTL em perguntas_cache."""
        if conn is not None:
            ensure_semantic_cache_partition_schema(conn)
            self._cache_schema_ready = True
            return
        if self._cache_schema_ready:
            return
        with self._get_connection() as managed_conn:
            ensure_semantic_cache_partition_schema(managed_conn)
            self._cache_schema_ready = True

    def gerar_embedding(self, texto: str, task_type: str = "retrieval_query", timeout_sec: float = 2.5) -> List[float]:
        """Gera embedding de 768 dimensoes com o cliente unificado google-genai Keep-Alive."""
        vec = llm_embed_content(
            model=self.embedding_model,
            content=texto,
            output_dimensionality=768,
            task_type=task_type,
            timeout_sec=timeout_sec,
            api_key=self.api_key,
        )
        return list(vec) if isinstance(vec, list) else []

    def check_semantic_cache(
        self,
        query_text: str,
        similarity_threshold: float = 0.96,
        query_vector: Optional[List[float]] = None,
        tenant_id: Optional[str] = None,
        filial_id: Optional[Union[str, int]] = None,
        pack_id: Optional[str] = None,
        ttl_seconds: int = DEFAULT_CACHE_TTL_CATALOG_SECONDS,
    ) -> Optional[Dict[str, Any]]:
        """
        Verifica se ha resposta identica ou equivalente valida no cache semantico,
        particionada estritamente por (tenant_id, filial_id, pack_id) e TTL (Carbon Core P0.2).
        """
        if not query_vector:
            query_vector = self.gerar_embedding(query_text, task_type="retrieval_query")

        eff_tenant, eff_filial, eff_pack = self._resolve_cache_partition(
            tenant_id=tenant_id,
            filial_id=filial_id,
            pack_id=pack_id,
        )
        eff_ttl = _validate_positive_int(ttl_seconds, "ttl_seconds", min_val=1, max_val=86400 * 30)
        eff_threshold = _validate_finite_float(similarity_threshold, "similarity_threshold", min_val=0.0, max_val=1.0)

        sql = """
        SELECT resposta_llm, json_produtos,
               1 - (pergunta_vetor <=> %s::halfvec) AS cosine_similarity,
               tenant_id, filial_id, pack_id, created_at
        FROM perguntas_cache
        WHERE tenant_id = %s
          AND filial_id = %s
          AND pack_id = %s
          AND created_at >= NOW() - (%s * INTERVAL '1 second')
        ORDER BY pergunta_vetor <=> %s::halfvec
        LIMIT 1;
        """
        try:
            rls_filial_int = int(re.sub(r"\D", "", eff_filial) or 1)
            with self._get_connection(tenant_id=eff_tenant, filial_id=rls_filial_int) as conn:
                if not self._ensure_cache_partition_columns(conn):
                    return {"query_vector": query_vector}
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    vec_str = str(query_vector)
                    cur.execute(sql, (vec_str, eff_tenant, eff_filial, eff_pack, eff_ttl, vec_str))
                    row = cur.fetchone()

            if row and float(row["cosine_similarity"]) >= eff_threshold:
                return {
                    "resposta_llm": row["resposta_llm"],
                    "json_produtos": row["json_produtos"],
                    "cosine_similarity": float(row["cosine_similarity"]),
                    "tenant_id": eff_tenant,
                    "filial_id": eff_filial,
                    "pack_id": eff_pack,
                    "query_vector": query_vector,
                }
        except Exception as e:
            logger.error(f"Erro no cache semântico: {e}")
        return {"query_vector": query_vector}

    def save_semantic_cache(
        self,
        query_text: str,
        query_vector: List[float],
        resposta_llm: str,
        json_produtos: Any,
        tenant_id: Optional[str] = None,
        filial_id: Optional[Union[str, int]] = None,
        pack_id: Optional[str] = None,
    ):
        """
        Salva a resposta no cache semantico particionado por (tenant_id, filial_id, pack_id)
        com timestamp created_at para expiracao deterministica por TTL.
        """
        frases_bloqueio = ["não há registros", "erro", "indisponível", "não foi possível", "não encontrei"]
        if any(fb in resposta_llm.lower() for fb in frases_bloqueio):
            return

        eff_tenant, eff_filial, eff_pack = self._resolve_cache_partition(
            tenant_id=tenant_id,
            filial_id=filial_id,
            pack_id=pack_id,
        )

        sql = """
        INSERT INTO perguntas_cache (
            pergunta, pergunta_vetor, resposta_llm, json_produtos,
            tenant_id, filial_id, pack_id, created_at
        )
        VALUES (%s, %s::halfvec, %s, %s, %s, %s, %s, NOW());
        """
        try:
            rls_filial_int = int(re.sub(r"\D", "", eff_filial) or 1)
            with self._get_connection(tenant_id=eff_tenant, filial_id=rls_filial_int) as conn:
                if not self._ensure_cache_partition_columns(conn):
                    return
                with conn.cursor() as cur:
                    cur.execute(
                        sql,
                        (
                            query_text,
                            str(query_vector),
                            resposta_llm,
                            json.dumps(json_produtos, default=str),
                            eff_tenant,
                            eff_filial,
                            eff_pack,
                        ),
                    )
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
        ef = _validate_positive_int(ef_search or self.ef_search, "ef_search", min_val=1, max_val=2000)
        eff_dense_weight = _validate_finite_float(dense_weight, "dense_weight", min_val=0.0, max_val=10.0)
        eff_sparse_weight = _validate_finite_float(sparse_weight, "sparse_weight", min_val=0.0, max_val=10.0)
        eff_rrf_k = _validate_positive_int(self.rrf_k, "rrf_k", min_val=1, max_val=1000)
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
        SET LOCAL hnsw.iterative_scan = 'relaxed_order';
        SET LOCAL hnsw.max_scan_tuples = 20000;
            """

        fetch_limit = min(50, top_k * 10)

        if query_vector is not None:
            sql_rrf = f"""
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
                    %s * COALESCE(1.0 / (%s + d.dense_rank), 0.0) +
                    %s * COALESCE(1.0 / (%s + s.sparse_rank), 0.0) +
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

            # Parâmetros para SELECT final (pesos e boosts RRF parametrizados)
            params.extend([
                eff_dense_weight, eff_rrf_k,
                eff_sparse_weight, eff_rrf_k,
                exact_code, exact_code, exact_code, exact_code,                                    # Boost exato codbar/codpro
                viscosity_sql_regex, viscosity_sql_regex,                                          # Boost viscosidade
                top_k                                                                              # LIMIT final
            ])
        else:
            # Fallback gracioso para recuperação esparsa (GIN FTS + Boosts + RRF) quando embedding não disponível
            sql_rrf = f"""
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
                    %s * (1.0 / (%s + s.sparse_rank)) +
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
                eff_sparse_weight, eff_rrf_k,
                exact_code, exact_code, exact_code, exact_code,
                viscosity_sql_regex, viscosity_sql_regex,
                top_k
            ])

        t_db_start = time.perf_counter()
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT set_config('hnsw.ef_search', %s, true);", (str(ef),))
                if grupo_filter and query_vector is not None:
                    cur.execute("SELECT set_config('hnsw.iterative_scan', 'relaxed_order', true);")
                    cur.execute("SELECT set_config('hnsw.max_scan_tuples', '20000', true);")
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
        tenant_id: str = "posto_local",
    ) -> Dict[str, Any]:
        """
        Busca híbrida de auto-conhecimento da AURA na tabela `aura_conhecimento_vetores`
        utilizando pgvector HNSW (halfvec 768d) + GIN Full-Text Search (tsvector em português)
        + Reciprocal Rank Fusion (RRF) em SQL nativo.
        Latência de busca em banco sub-5ms (< 5ms).
        """
        ef = _validate_positive_int(ef_search or self.ef_search, "ef_search", min_val=1, max_val=2000)
        eff_dense_weight = _validate_finite_float(dense_weight, "dense_weight", min_val=0.0, max_val=10.0)
        eff_sparse_weight = _validate_finite_float(sparse_weight, "sparse_weight", min_val=0.0, max_val=10.0)
        eff_rrf_k = _validate_positive_int(self.rrf_k, "rrf_k", min_val=1, max_val=1000)
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
        retrieval_mode = "hybrid_hnsw_rrf" if query_vector is not None else "sparse_fts_fallback"
        results = []

        try:
            with self._get_connection(tenant_id=tenant_id) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
                if query_vector is not None:
                    sql_rrf = f"""
                    SET LOCAL hnsw.ef_search = {ef};

                    WITH dense_search AS (
                        SELECT 
                            id, modulo, topico, titulo, subtitulo, conteudo, metadados, elementos_ui, ui_action, tags,
                            1 - (embedding <=> %s::halfvec) AS cosine_similarity,
                            ROW_NUMBER() OVER (ORDER BY embedding <=> %s::halfvec) AS dense_rank
                        FROM aura_conhecimento_vetores
                        WHERE embedding IS NOT NULL
                        ORDER BY embedding <=> %s::halfvec
                        LIMIT %s
                    ),
                    sparse_search AS (
                        SELECT 
                            id, modulo, topico, titulo, subtitulo, conteudo, metadados, elementos_ui, ui_action, tags,
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
                        COALESCE(d.metadados, s.metadados) AS metadados,
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
                        id, modulo, topico, titulo, subtitulo, conteudo, metadados, elementos_ui, ui_action, tags,
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
                            id, modulo, topico, titulo, subtitulo, conteudo, metadados, elementos_ui, ui_action, tags,
                            0.0 AS cosine_similarity, 0.0 AS fts_score, NULL::bigint AS dense_rank, 1::bigint AS sparse_rank,
                            0.04762 AS rrf_score
                        FROM aura_conhecimento_vetores
                        WHERE topico = 'panorama_operacional'
                        LIMIT 1;
                    """)
                    results = cur.fetchall()
        except Exception as e:  # noqa: BLE001
            logger.warning("Falha ao consultar banco vetorial: %s. Ativando fallback em memoria.", e)
            retrieval_mode = "offline_memory_fallback"
            try:
                # 1. Consulta sementes operacionais e normativas oficiais da AURA (ANP, INMETRO, Cockpit)
                from scripts.seed_aura_conhecimento import CONHECIMENTO_SEEDS
                q_words = [w for w in re.findall(r"[\w]+", q_clean.lower()) if len(w) > 2]
                scored = []
                for seed in CONHECIMENTO_SEEDS:
                    text_blob = f"{seed['titulo']} {seed.get('subtitulo', '')} {seed['topico']} {seed['modulo']} {seed['conteudo']} {' '.join(seed.get('tags', []))}".lower()
                    score = sum(1 for w in q_words if w in text_blob)
                    if score > 0:
                        scored.append((score, seed))
                scored.sort(key=lambda x: x[0], reverse=True)
                if scored:
                    for s in scored[:top_k]:
                        item = dict(s[1])
                        item.setdefault("id", None)
                        item.setdefault("cosine_similarity", 0.0)
                        item.setdefault("fts_score", 0.0)
                        item.setdefault("dense_rank", None)
                        item.setdefault("sparse_rank", 1)
                        item.setdefault("rrf_score", 0.04762)
                        results.append(item)

                # 2. Complementa com o acervo operacional curado do webPosto (Confluence, Dicionario SQL, Incidentes, APIs)
                from core.webposto_rag import get_webposto_rag
                wp_limit = top_k if not results else top_k
                wp_items = get_webposto_rag().buscar_geral(q_clean, limit=wp_limit)
                for wp in wp_items:
                    results.append({
                        "id": f"wp_{wp['id']}",
                        "modulo": f"ERP / {wp['modulo']}",
                        "topico": wp["codigo_ref"],
                        "titulo": wp["titulo"],
                        "subtitulo": wp.get("subtitulo") or wp["resumo_executivo"],
                        "conteudo": wp["conteudo_completo"],
                        "metadados": {
                            "pilar": wp["pilar"],
                            "impacto_financeiro": wp.get("impacto_financeiro"),
                            "acao_recomendada": wp.get("acao_recomendada"),
                            "tabelas_banco": wp.get("tabelas_banco"),
                        },
                        "elementos_ui": {},
                        "ui_action": {},
                        "tags": [t.strip() for t in wp.get("tags_busca", "").split(",") if t.strip()],
                        "cosine_similarity": 0.0,
                        "fts_score": wp.get("score_bm25", 0.0),
                        "dense_rank": None,
                        "sparse_rank": 1,
                        "rrf_score": 0.04,
                    })

                if not results:
                    item = dict(CONHECIMENTO_SEEDS[0])
                    item.setdefault("id", None)
                    item.setdefault("cosine_similarity", 0.0)
                    item.setdefault("fts_score", 0.0)
                    item.setdefault("dense_rank", None)
                    item.setdefault("sparse_rank", 1)
                    item.setdefault("rrf_score", 0.04762)
                    results.append(item)
            except Exception:  # noqa: BLE001
                results = []

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
            "retrieval_mode": retrieval_mode,
        }

        return {
            "results": [dict(r) for r in results],
            "telemetry": telemetry,
        }

    def search_hybrid_procedimentos(
        self,
        query_text: str,
        top_k: int = 5,
        tenant_id: str = "posto_local",
        erp: str = "webposto",
        dense_weight: float = 0.5,
        sparse_weight: float = 0.5,
        ef_search: int = 100,
        query_vector: list = None,
        vertical_pack: Optional[str] = None,
        min_cosine_threshold: float = DEFAULT_MIN_COSINE_EVIDENCE,
        min_fts_threshold: float = DEFAULT_MIN_FTS_EVIDENCE,
    ) -> dict:
        """
        Busca hibrida multicamada de procedimentos operacionais e manuais do ERP (Carbon Core P0.2).
        Executa busca em aura_core.aura_conhecimento_chunks:
        - Ramo denso: HNSW puro (ORDER BY embedding <=> %s::halfvec ASC LIMIT 50) + corte cosine >= 0.62
        - Ramo esparso: GIN tsvector em portugues com ts_rank_cd e fallback relaxado
        - Fusao: Reciprocal Rank Fusion (RRF, k=60) com boost de breadcrumb apenas no score externo
        - Trava matematica real de evidencia_insuficiente: max_cosine < 0.62 AND max_fts_score < 0.05
        """
        ef = _validate_positive_int(ef_search or 100, "ef_search", min_val=1, max_val=2000)
        eff_dense_weight = _validate_finite_float(dense_weight, "dense_weight", min_val=0.0, max_val=10.0)
        eff_sparse_weight = _validate_finite_float(sparse_weight, "sparse_weight", min_val=0.0, max_val=10.0)
        eff_min_cosine = _validate_finite_float(min_cosine_threshold, "min_cosine_threshold", min_val=0.0, max_val=1.0)
        eff_min_fts = _validate_finite_float(min_fts_threshold, "min_fts_threshold", min_val=0.0, max_val=10.0)
        eff_vertical = (vertical_pack or "").strip()
        t0 = time.perf_counter()

        q_clean = (query_text or "").strip()
        if not q_clean:
            return {
                "results": [],
                "evidencia_insuficiente": True,
                "telemetry": {"query": "", "results_count": 0, "total_ms": 0.0}
            }

        t_emb_start = time.perf_counter()
        if not query_vector:
            try:
                query_vector = self.gerar_embedding(q_clean, task_type="retrieval_query")
            except Exception:
                query_vector = None
        emb_latency_ms = (time.perf_counter() - t_emb_start) * 1000

        # Deteccao de ambiente operacional alvo (PDV vs Retaguarda)
        q_lower = q_clean.lower()
        is_pdv = bool(re.search(r'\b(pdv|ponto de venda|frente|pista|caixa da pista|caixa do posto)\b', q_lower))
        is_retaguarda = bool(re.search(r'\b(retaguarda|administrativo|gerencial|escritorio)\b', q_lower))

        # Limpeza de stopwords procedimentais e termos genericos do dominio ERP
        stopwords = {
            "como", "faco", "faço", "fazer", "posso", "consigo", "onde", "qual", "quais",
            "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas", "para", "pra",
            "um", "uma", "uns", "umas", "o", "a", "os", "as", "que", "se", "por", "com",
            "passo", "etapa", "tutorial", "explicar", "ensinar"
        }
        broad_terms = {"pdv", "erp", "sistema", "modulo", "webposto", "posto", "retaguarda"}
        termos = re.findall(r"[\w]+", q_clean.lower())
        uteis = [t for t in termos if len(t) > 1 and t not in stopwords]
        uteis_core = [t for t in uteis if t not in broad_terms]
        active_terms = uteis_core if uteis_core else uteis

        # Expansao de sinonimos operacionais no tsquery
        expanded = []
        for t in active_terms:
            if t == "caixa" and is_pdv:
                expanded.append("(caixa | turno)")
            elif t == "turno":
                expanded.append("(turno | caixa)")
            else:
                expanded.append(t)

        tsquery_and = " & ".join(expanded) if expanded else q_clean
        tsquery_or = " | ".join(expanded) if expanded else q_clean
        like_main = f"%{active_terms[0]}%" if active_terms else f"%{q_clean}%"

        t_db_start = time.perf_counter()
        retrieval_mode = "hybrid_chunks_rrf" if query_vector is not None else "sparse_chunks_fts"
        results = []

        try:
            with self._get_connection(tenant_id=tenant_id) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
                if query_vector is not None:
                    cur.execute("SELECT set_config('hnsw.ef_search', %s, true);", (str(ef),))
                    cur.execute("SELECT set_config('hnsw.iterative_scan', 'relaxed_order', true);")

                    sql_rrf = """
                    WITH dense_candidates AS (
                        SELECT
                            id, doc_id, doc_titulo, doc_url, doc_versao, breadcrumb, secao,
                            chunk_idx, chunk_total, conteudo, n_tokens,
                            1 - (embedding <=> %s::halfvec) AS cosine_similarity
                        FROM aura_core.aura_conhecimento_chunks
                        WHERE embedding IS NOT NULL
                          AND status = 'ativo'
                          AND (camada IN ('core', 'vertical', 'erp') OR (camada = 'tenant' AND tenant_id = %s))
                          AND (%s = '' OR vertical IS NULL OR vertical = '' OR vertical = %s)
                        ORDER BY embedding <=> %s::halfvec ASC
                        LIMIT 50
                    ),
                    dense_search AS (
                        SELECT
                            id, doc_id, doc_titulo, doc_url, doc_versao, breadcrumb, secao,
                            chunk_idx, chunk_total, conteudo, n_tokens,
                            cosine_similarity,
                            ROW_NUMBER() OVER (ORDER BY cosine_similarity DESC, id ASC) AS dense_rank
                        FROM dense_candidates
                        WHERE cosine_similarity >= %s
                    ),
                    sparse_search AS (
                        SELECT 
                            id, doc_id, doc_titulo, doc_url, doc_versao, breadcrumb, secao,
                            chunk_idx, chunk_total, conteudo, n_tokens,
                            ts_rank_cd(tsv, to_tsquery('portuguese', %s)) AS fts_score,
                            ROW_NUMBER() OVER (
                                ORDER BY 
                                    (CASE WHEN tsv @@ to_tsquery('portuguese', %s) THEN 1 ELSE 0 END) DESC,
                                    (CASE WHEN doc_titulo ILIKE %s THEN 1 ELSE 0 END) DESC,
                                    ts_rank_cd(tsv, to_tsquery('portuguese', %s)) DESC,
                                    id ASC
                            ) AS sparse_rank
                        FROM aura_core.aura_conhecimento_chunks
                        WHERE (tsv @@ to_tsquery('portuguese', %s)
                               OR tsv @@ to_tsquery('portuguese', %s)
                               OR doc_titulo ILIKE %s
                               OR breadcrumb ILIKE %s)
                          AND status = 'ativo'
                          AND (camada IN ('core', 'vertical', 'erp') OR (camada = 'tenant' AND tenant_id = %s))
                          AND (%s = '' OR vertical IS NULL OR vertical = '' OR vertical = %s)
                        ORDER BY sparse_rank ASC
                        LIMIT 30
                    )
                    SELECT 
                        COALESCE(d.id, s.id) AS id,
                        COALESCE(d.doc_id, s.doc_id) AS doc_id,
                        COALESCE(d.doc_titulo, s.doc_titulo) AS doc_titulo,
                        COALESCE(d.doc_url, s.doc_url) AS doc_url,
                        COALESCE(d.doc_versao, s.doc_versao) AS doc_versao,
                        COALESCE(d.breadcrumb, s.breadcrumb) AS breadcrumb,
                        COALESCE(d.secao, s.secao) AS secao,
                        COALESCE(d.chunk_idx, s.chunk_idx) AS chunk_idx,
                        COALESCE(d.chunk_total, s.chunk_total) AS chunk_total,
                        COALESCE(d.conteudo, s.conteudo) AS conteudo,
                        COALESCE(d.n_tokens, s.n_tokens) AS n_tokens,
                        COALESCE(d.cosine_similarity, 0.0) AS cosine_similarity,
                        COALESCE(s.fts_score, 0.0) AS fts_score,
                        d.dense_rank,
                        s.sparse_rank,
                        (
                            %s * COALESCE(1.0 / (60 + d.dense_rank), 0.0) +
                            %s * COALESCE(1.0 / (60 + s.sparse_rank), 0.0) +
                            (CASE
                                WHEN %s AND (COALESCE(d.breadcrumb, s.breadcrumb) ILIKE '%%pdv%%' OR COALESCE(d.doc_titulo, s.doc_titulo) ILIKE '%%pdv%%') THEN 0.005
                                WHEN %s AND (COALESCE(d.breadcrumb, s.breadcrumb) ILIKE '%%retaguarda%%' OR COALESCE(d.doc_titulo, s.doc_titulo) ILIKE '%%retaguarda%%') THEN 0.005
                                WHEN %s AND COALESCE(d.breadcrumb, s.breadcrumb) ILIKE '%%retaguarda%%' THEN -0.003
                                WHEN %s AND COALESCE(d.breadcrumb, s.breadcrumb) ILIKE '%%pdv%%' THEN -0.003
                                ELSE 0.0
                            END)
                        ) AS rrf_score
                    FROM dense_search d
                    FULL OUTER JOIN sparse_search s ON d.id = s.id
                    ORDER BY rrf_score DESC
                    LIMIT 30;
                    """
                    vec_str = str(query_vector)
                    params = (
                        vec_str,
                        tenant_id,
                        eff_vertical, eff_vertical,
                        vec_str,
                        eff_min_cosine,
                        tsquery_and,
                        tsquery_and, like_main, tsquery_and,
                        tsquery_and, tsquery_or, like_main, like_main,
                        tenant_id,
                        eff_vertical, eff_vertical,
                        eff_dense_weight,
                        eff_sparse_weight,
                        is_pdv, is_retaguarda, is_pdv, is_retaguarda,
                    )
                    cur.execute(sql_rrf, params)
                    raw_rows = cur.fetchall()
                else:
                    sql_sparse = """
                    SELECT 
                        id, doc_id, doc_titulo, doc_url, doc_versao, breadcrumb, secao,
                        chunk_idx, chunk_total, conteudo, n_tokens,
                        0.0 AS cosine_similarity,
                        ts_rank_cd(tsv, to_tsquery('portuguese', %s)) AS fts_score,
                        NULL::bigint AS dense_rank,
                        ROW_NUMBER() OVER (
                            ORDER BY 
                                (CASE 
                                    WHEN %s AND (breadcrumb ILIKE '%%pdv%%' OR doc_titulo ILIKE '%%pdv%%') THEN 10
                                    WHEN %s AND (breadcrumb ILIKE '%%retaguarda%%' OR doc_titulo ILIKE '%%retaguarda%%') THEN 10
                                    WHEN %s AND breadcrumb ILIKE '%%retaguarda%%' THEN -5
                                    WHEN %s AND breadcrumb ILIKE '%%pdv%%' THEN -5
                                    ELSE 0
                                END) DESC,
                                (CASE WHEN tsv @@ to_tsquery('portuguese', %s) THEN 1 ELSE 0 END) DESC,
                                (CASE WHEN doc_titulo ILIKE %s THEN 1 ELSE 0 END) DESC,
                                ts_rank_cd(tsv, to_tsquery('portuguese', %s)) DESC,
                                id ASC
                        ) AS sparse_rank,
                        (1.0 / (60 + ROW_NUMBER() OVER (
                            ORDER BY 
                                (CASE 
                                    WHEN %s AND (breadcrumb ILIKE '%%pdv%%' OR doc_titulo ILIKE '%%pdv%%') THEN 10
                                    WHEN %s AND (breadcrumb ILIKE '%%retaguarda%%' OR doc_titulo ILIKE '%%retaguarda%%') THEN 10
                                    WHEN %s AND breadcrumb ILIKE '%%retaguarda%%' THEN -5
                                    WHEN %s AND breadcrumb ILIKE '%%pdv%%' THEN -5
                                    ELSE 0
                                END) DESC,
                                (CASE WHEN tsv @@ to_tsquery('portuguese', %s) THEN 1 ELSE 0 END) DESC,
                                (CASE WHEN doc_titulo ILIKE %s THEN 1 ELSE 0 END) DESC,
                                ts_rank_cd(tsv, to_tsquery('portuguese', %s)) DESC,
                                id ASC
                        ))) AS rrf_score
                    FROM aura_core.aura_conhecimento_chunks
                    WHERE (tsv @@ to_tsquery('portuguese', %s)
                           OR tsv @@ to_tsquery('portuguese', %s)
                           OR doc_titulo ILIKE %s
                           OR breadcrumb ILIKE %s)
                      AND status = 'ativo'
                      AND (camada IN ('core', 'vertical', 'erp') OR (camada = 'tenant' AND tenant_id = %s))
                    ORDER BY rrf_score DESC
                    LIMIT 30;
                    """
                    params = (
                        tsquery_and,
                        is_pdv, is_retaguarda, is_pdv, is_retaguarda,
                        tsquery_and, like_main, tsquery_and,
                        is_pdv, is_retaguarda, is_pdv, is_retaguarda,
                        tsquery_and, like_main, tsquery_and,
                        tsquery_and, tsquery_or, like_main, like_main, tenant_id
                    )
                    cur.execute(sql_sparse, params)
                    raw_rows = cur.fetchall()

                # Deduplicacao com limite de 2 chunks por pagina
                doc_counts = {}
                for r in raw_rows:
                    d_id = r["doc_id"]
                    cnt = doc_counts.get(d_id, 0)
                    if cnt < 2:
                        results.append(dict(r))
                        doc_counts[d_id] = cnt + 1
                    if len(results) >= top_k:
                        break

        except Exception as e:
            logger.warning("Falha na busca de procedimentos em chunks: %s", e)
            retrieval_mode = "error_fallback"

        # Fallback de contingencia local FTS5 SQLite sobre os 2.343 chunks estruturais se pgvector estiver offline
        if not results and retrieval_mode == "error_fallback":
            try:
                from core.webposto_rag import get_webposto_rag
                rag_local = get_webposto_rag()
                chunk_hits = rag_local.buscar_chunks_procedimentos(
                    query_text,
                    tenant_id=tenant_id,
                    limit=top_k,
                )
                if chunk_hits:
                    for hit in chunk_hits:
                        hit.setdefault("cosine_similarity", 0.0)
                        hit.setdefault("fts_score", float(hit.get("rrf_score", 0.0)))
                    results.extend(chunk_hits)
                    retrieval_mode = "local_chunks_fts5"
            except Exception as e_ch:
                logger.warning("Falha na busca local de chunks FTS5: %s", e_ch)

        db_latency_ms = (time.perf_counter() - t_db_start) * 1000
        total_latency_ms = (time.perf_counter() - t0) * 1000

        # Trava matematica real de evidencia minima (Carbon Core P0.2):
        # Evita o limiar RRF morto (< 0.008) que jamais disparava quando dense_weight=0.5 e k=60
        max_score = max((float(r.get("rrf_score") or 0.0) for r in results), default=0.0)
        max_cosine = max((float(r.get("cosine_similarity") or 0.0) for r in results), default=0.0)
        max_fts_score = max((float(r.get("fts_score") or 0.0) for r in results), default=0.0)
        evidencia_insuficiente = bool(
            not results or (max_cosine < eff_min_cosine and max_fts_score < eff_min_fts)
        )

        telemetry = {
            "query": query_text,
            "tsquery_used": tsquery_or,
            "embedding_latency_ms": round(emb_latency_ms, 2),
            "db_rrf_latency_ms": round(db_latency_ms, 2),
            "total_retrieval_latency_ms": round(total_latency_ms, 2),
            "hnsw_ef_search": ef,
            "top_k": top_k,
            "results_count": len(results),
            "max_rrf_score": round(max_score, 5),
            "max_cosine_similarity": round(max_cosine, 5),
            "max_fts_score": round(max_fts_score, 5),
            "evidencia_insuficiente": evidencia_insuficiente,
            "retrieval_mode": retrieval_mode,
        }

        return {
            "results": results,
            "evidencia_insuficiente": evidencia_insuficiente,
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
        ef = _validate_positive_int(ef_search or self.ef_search, "ef_search", min_val=1, max_val=2000)
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

    def search_causal_rca_context(
        self,
        tenant_id: str,
        anomaly_node_id: str,
        max_hops: int = 4,
        time_window_hours: int = 72,
        top_k_paths: int = 3,
    ) -> Dict[str, Any]:
        """
        Consulta o grafo causal leve (GraphRAG Fase 4) para retornar cadeias de
        causa-raiz multi-salto e bloco textual auditavel para injecao no prompt.
        """
        from core.causal_graph import get_causal_graph

        graph = get_causal_graph()
        trace = graph.trace_root_cause(
            tenant_id=tenant_id,
            anomaly_node_id=anomaly_node_id,
            max_hops=max_hops,
            time_window_hours=time_window_hours,
            top_k_paths=top_k_paths,
        )
        return {
            "trace": trace,
            "causal_context_text": graph.format_for_rag_context(trace),
        }
