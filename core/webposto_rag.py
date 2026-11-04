"""
Motor de Recuperacao de Conhecimento do webPosto (core/webposto_rag.py).
Fornece busca full-text instantanea (sub-milissegundo com SQLite FTS5 e BM25)
sobre o acervo curado do webPosto da AURA:
1. Procedimentos e Manuais Confluence (911 paginas e Hubs)
2. Dicionario Semantico de Regras e Flags do Banco (Zero Alucinacao SQL)
3. Diagnosticos de Pista e Contingencias (Dinheiro Travado)
4. Catalogo Oficial de APIs para Expansao Multi-Posto (OpenAPI)

100% local, sem Docker, sem nuvem, sem latencia externa.
Regra inegociavel: ZERO travessoes em todo o arquivo.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import time
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional
from core.sanitizer import sanitize_erp_brand_names

logger = logging.getLogger("aura.webposto_rag")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "webposto_knowledge.db"


class WebPostoRAGEngine:
    """Motor de consulta ultrarrapido para o conhecimento estruturado do webPosto."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH

    def _get_connection(self) -> sqlite3.Connection:
        if not self.db_path.exists():
            raise FileNotFoundError(f"Banco de conhecimento do webPosto nao localizado em: {self.db_path}")
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn

    def buscar_geral(
        self,
        termo: str,
        pilar: Optional[str] = None,
        modulo: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Executa busca por relevancia BM25 no indice FTS5 em portugues.
        Retorna registros rankeados com resumo executivo e acao recomendada.
        """
        termo_limpo = (termo or "").strip()
        if not termo_limpo:
            return []

        # Sanitizacao basica de caracteres especiais do SQLite FTS5
        palavras = [re.sub(r"[^\wáéíóúâêîôûãõçÁÉÍÓÚÂÊÎÔÛÃÕÇ]", "", p) for p in termo_limpo.split()]
        palavras_validas = [p for p in palavras if len(p) >= 2]
        if not palavras_validas:
            return []

        # Query FTS com operador prefixo (*) para tolerar flexoes e plurais
        query_fts = " OR ".join(f'"{p}"*' for p in palavras_validas)

        sql = """
            SELECT 
                t.id,
                t.pilar,
                t.codigo_ref,
                t.modulo,
                t.titulo,
                t.subtitulo,
                t.resumo_executivo,
                t.conteudo_completo,
                t.tabelas_banco,
                t.impacto_financeiro,
                t.acao_recomendada,
                t.tags_busca,
                bm25(conhecimento_fts) AS bm25_rank
            FROM conhecimento_fts f
            JOIN tabela_conhecimento t ON f.rowid = t.id
            WHERE conhecimento_fts MATCH ?
        """
        params: List[Any] = [query_fts]

        if pilar:
            sql += " AND t.pilar = ?"
            params.append(pilar)

        if modulo:
            sql += " AND t.modulo LIKE ?"
            params.append(f"%{modulo}%")

        sql += " ORDER BY bm25_rank ASC LIMIT ?"
        params.append(limit)

        resultados = []
        try:
            with self._get_connection() as conn:
                cur = conn.execute(sql, params)
                for row in cur.fetchall():
                    resultados.append({
                        "id": row["id"],
                        "pilar": row["pilar"],
                        "codigo_ref": sanitize_erp_brand_names(row["codigo_ref"]),
                        "modulo": sanitize_erp_brand_names(row["modulo"]),
                        "titulo": sanitize_erp_brand_names(row["titulo"]),
                        "subtitulo": sanitize_erp_brand_names(row["subtitulo"]),
                        "resumo_executivo": sanitize_erp_brand_names(row["resumo_executivo"]),
                        "conteudo_completo": sanitize_erp_brand_names(row["conteudo_completo"]),
                        "tabelas_banco": row["tabelas_banco"],
                        "impacto_financeiro": sanitize_erp_brand_names(row["impacto_financeiro"]),
                        "acao_recomendada": sanitize_erp_brand_names(row["acao_recomendada"]),
                        "tags_busca": sanitize_erp_brand_names(row["tags_busca"]),
                        "score_bm25": round(float(row["bm25_rank"]), 4) if row["bm25_rank"] is not None else 0.0,
                    })
        except Exception as e:
            logger.warning("Falha na consulta FTS5 webPosto: %s", e)

        return resultados


    @staticmethod
    def _norm_ascii(s: str) -> str:
        n = unicodedata.normalize("NFD", s or "")
        return "".join(c for c in n if unicodedata.category(c) != "Mn").lower()

    def buscar_chunks_procedimentos(
        self,
        query: str,
        tenant_id: str = "posto_local",
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Busca de alta precisao sobre a tabela estrutural aura_conhecimento_chunks e chunks_fts (2.343 chunks).
        Aplica filtragem de escopo multicamada (core, vertical, erp, tenant), consciencia de ambiente
        (PDV vs Retaguarda), penalizacao de relatorios/notas de versao quando nao solicitados e guarda
        estrita contra consultas fora do escopo operacional.
        """
        q_norm = self._norm_ascii(query)
        if not q_norm.strip():
            return []

        stopwords = {
            "como", "faco", "fazer", "posso", "consigo", "onde", "fica", "qual", "quais",
            "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas", "para", "pra",
            "um", "uma", "uns", "umas", "o", "a", "os", "as", "que", "se", "por", "com", "ou",
            "passo", "etapa", "tutorial", "explicar", "ensinar", "rotina", "dar", "lancar", "emitir",
            "realizar", "efetuar", "configurar", "alterar", "definir", "usar", "verificar", "acompanhar"
        }
        broad_terms = {"pdv", "erp", "sistema", "modulo", "webposto", "posto", "retaguarda", "novo", "nova", "arquivo"}

        wants_report = bool(re.search(r"\b(relatorio|relatorios)\b", q_norm))
        wants_release = bool(re.search(r"\b(versao|atualizacao|novidades)\b", q_norm))
        is_pdv = bool(re.search(r"\b(pdv|ponto de venda|frente|pista|caixa da pista)\b", q_norm))
        is_retaguarda = bool(re.search(r"\b(retaguarda|administrativo|gerencial|escritorio)\b", q_norm))

        raw_tokens = [re.sub(r"[^a-z0-9]", "", t) for t in q_norm.split()]
        uteis = [t for t in raw_tokens if len(t) >= 2 and t not in stopwords]
        core_terms = [t for t in uteis if t not in broad_terms] or uteis
        if not core_terms:
            return []

        fts_terms = list(core_terms)
        for ct in core_terms:
            if len(ct) >= 6:
                fts_terms.append(ct[:5])
        if "nota" in core_terms or "fiscal" in core_terms:
            fts_terms.append("nfe")
        if "nfe" in core_terms:
            fts_terms.extend(["nota", "entradas"])
        if "cupom" in core_terms:
            fts_terms.append("nfce")
        if "caixa" in core_terms and is_pdv:
            fts_terms.append("turno")
        fts_terms = list(dict.fromkeys(fts_terms))

        fts_or = " OR ".join(f'"{t}"*' for t in fts_terms)

        try:
            with self._get_connection() as conn:
                cur = conn.execute(
                    """
                    SELECT c.*, bm25(chunks_fts, 0.0, 10.0, 5.0, 3.0, 1.0) AS raw_bm25
                    FROM chunks_fts f
                    JOIN aura_conhecimento_chunks c ON f.rowid = c.id
                    WHERE chunks_fts MATCH ?
                      AND c.status = 'ativo'
                      AND (c.camada IN ('core', 'vertical', 'erp') OR (c.camada = 'tenant' AND c.tenant_id = ?))
                    ORDER BY raw_bm25 ASC
                    LIMIT 100
                    """,
                    (fts_or, tenant_id),
                )
                candidates = cur.fetchall()
        except Exception as e:
            logger.warning("Tabela chunks_fts indisponivel ou erro na busca de chunks: %s", e)
            return []

        if not candidates:
            return []

        scored = []
        for row in candidates:
            title_n = self._norm_ascii(row["doc_titulo"])
            bread_n = self._norm_ascii(row["breadcrumb"] or "")
            secao_n = self._norm_ascii(row["secao"] or "")
            body_n = self._norm_ascii(row["conteudo"] or "")
            full_n = f"{title_n} {bread_n} {secao_n} {body_n}"

            matched_core = 0
            title_hits = 0
            for ct in core_terms:
                stem = ct[:5] if len(ct) >= 6 else ct
                syn_hit = False
                if ct in ("nota", "fiscal") and ("nfe" in full_n or "nota" in full_n):
                    syn_hit = True
                if ct == "nfe" and ("nfe" in full_n or "nota fiscal" in full_n or "entradas" in title_n):
                    syn_hit = True
                if ct == "caixa" and is_pdv and ("caixa" in full_n or "turno" in full_n):
                    syn_hit = True
                if stem in full_n or syn_hit:
                    matched_core += 1
                if (
                    stem in title_n
                    or stem in bread_n
                    or (ct in ("nota", "fiscal", "nfe") and ("nfe" in title_n or "nota" in title_n))
                    or (ct == "caixa" and is_pdv and ("caixa" in title_n or "turno" in title_n))
                ):
                    title_hits += 1

            coverage_ratio = matched_core / len(core_terms)
            if coverage_ratio < 0.60 or title_hits == 0:
                continue

            bm25_pos = abs(float(row["raw_bm25"] or 0.0))
            score = (coverage_ratio * 25.0) + (title_hits * 10.0) + min(bm25_pos, 30.0)

            if not wants_report and ("relatorio" in title_n or "relatorios" in bread_n):
                score -= 14.0
            if not wants_release and ("notas de versao" in title_n or "notas de versao" in bread_n):
                score -= 18.0
            if "mobile" in title_n and "mobile" not in q_norm:
                score -= 8.0

            if is_pdv:
                if "pdv" in title_n or "pdv" in bread_n:
                    score += 10.0
                elif "retaguarda" in bread_n:
                    score -= 4.0
            elif is_retaguarda:
                if "retaguarda" in title_n or "retaguarda" in bread_n:
                    score += 10.0
                elif "pdv" in bread_n:
                    score -= 4.0

            if title_n.strip() in ("seu erp", "webposto"):
                score -= 15.0

            if score < 25.0:
                continue

            scored.append((score, dict(row)))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        doc_counts: Dict[str, int] = {}
        for sc, r in scored:
            did = r["doc_id"]
            if doc_counts.get(did, 0) < 2:
                results.append({
                    "id": r["id"],
                    "doc_id": r["doc_id"],
                    "doc_titulo": sanitize_erp_brand_names(r["doc_titulo"]),
                    "secao": sanitize_erp_brand_names(r.get("secao") or "Geral"),
                    "breadcrumb": sanitize_erp_brand_names(r.get("breadcrumb") or ""),
                    "chunk_idx": r.get("chunk_idx", 0),
                    "chunk_total": r.get("chunk_total", 1),
                    "conteudo": sanitize_erp_brand_names(r["conteudo"]),
                    "doc_url": r.get("doc_url") or "",
                    "n_tokens": r.get("n_tokens") or (len(r["conteudo"]) // 4),
                    "rrf_score": round(sc / 100.0, 5),
                })
                doc_counts[did] = doc_counts.get(did, 0) + 1
            if len(results) >= limit:
                break
        return results

    def consultar_procedimento_webposto(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Recupera guias funcionais e passos de operacao nas telas do Confluence."""
        return self.buscar_geral(query, pilar="confluence_procedimentos", limit=limit)

    def consultar_regras_sql_webposto(self, tabelas: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Retorna o dicionario semantico de tabelas, campos e flags do banco local.
        Evita que consultas Text-to-SQL alucinem filtros ou calculos fiscais.
        """
        if not tabelas:
            termo = "abastecimentos pedido nfce produtos tanque lmc"
        else:
            termo = " ".join(tabelas)
        return self.buscar_geral(termo, pilar="dicionario_sql", limit=10)

    def diagnosticar_incidente_operacional(self, sintoma_ou_erro: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Diagnostica problemas de bicos, cancelamentos ou TEF com traducao para 'Dinheiro Travado'.
        Retorna a causa raiz e a acao sugerida para o gestor destravar a operacao.
        """
        return self.buscar_geral(sintoma_ou_erro, pilar="incidentes_pista_perdas", limit=limit)

    def consultar_api_multi_posto(self, entidade_ou_rota: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retorna rotas da API oficial do webPosto para integracao de matriz/filiais."""
        return self.buscar_geral(entidade_ou_rota, pilar="catalogo_api", limit=limit)


# Instancia singleton para uso global
_webposto_rag_singleton: Optional[WebPostoRAGEngine] = None


def get_webposto_rag() -> WebPostoRAGEngine:
    global _webposto_rag_singleton
    if _webposto_rag_singleton is None:
        _webposto_rag_singleton = WebPostoRAGEngine()
    return _webposto_rag_singleton
