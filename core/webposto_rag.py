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
