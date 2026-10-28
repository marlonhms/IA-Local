"""
Script de Carga Estrutural de Chunks Lexicos (scripts/populate_unembedded_chunks.py)
Roadmap Apendice: roadmap_apendice_conhecimento_multicamada_rag.md (Secao 7 / Fase 3)

Garante 100% de cobertura dos documentos procedimentais no PostgreSQL:
1. Identifica chunks ainda nao presentes no pgvector.
2. Grava os chunks com embedding = NULL para indexacao imediata no indice GIN (tsvector em portugues).
3. Preserva 100% dos chunks que ja possuem embeddings vetoriais do Gemini.
4. Permite busca hibrida instantanea (lexica agora + vetorial para os 977 ja embeddados).
5. Quando a cota de API resetar, o script ingest_confluence_pgvector.py --mode delta preenche os vetores.

Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import sys
import os
import time
import sqlite3
from pathlib import Path
from typing import List, Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import psycopg2
from psycopg2.extras import execute_batch
from config.settings import DB_VECTOR_CONFIG
from core.confluence_chunker import ConfluenceChunker, ConfluenceChunk

def run_populate():
    t0 = time.perf_counter()
    print("=== INICIANDO CARGA ESTRUTURAL DE CHUNKS NO POSTGRESQL (100% COBERTURA) ===")
    
    sqlite_path = PROJECT_ROOT / "data" / "webposto_knowledge.db"
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite nao encontrado em {sqlite_path}")

    # 1. Leitura de todos os docs do SQLite
    conn_sq = sqlite3.connect(str(sqlite_path))
    cur_sq = conn_sq.cursor()
    cur_sq.execute("""
        SELECT codigo_ref, modulo, titulo, subtitulo, resumo_executivo, 
               conteudo_completo, metadados_json
        FROM tabela_conhecimento
        WHERE pilar = 'confluence_procedimentos' AND codigo_ref LIKE 'CONF-%'
        ORDER BY codigo_ref ASC;
    """)
    rows = cur_sq.fetchall()
    conn_sq.close()
    print(f"Total de documentos procedimentais lidos: {len(rows)}")

    # 2. Conexao PostgreSQL e levantamento dos hashes existentes
    conn_pg = psycopg2.connect(**DB_VECTOR_CONFIG)
    cur_pg = conn_pg.cursor()

    cur_pg.execute("SELECT doc_id, chunk_idx FROM aura_core.aura_conhecimento_chunks WHERE status = 'ativo';")
    existing_set = set(cur_pg.fetchall())
    print(f"Total de chunks ja existentes no PostgreSQL: {len(existing_set)}")

    chunker = ConfluenceChunker()
    sql_insert = """
        INSERT INTO aura_core.aura_conhecimento_chunks (
            camada, vertical, erp, tenant_id, status, fonte,
            doc_id, doc_titulo, doc_url, doc_versao, breadcrumb, secao,
            chunk_idx, chunk_total, conteudo, conteudo_embed, n_tokens,
            hash_md5, embedding
        ) VALUES (
            %(camada)s, %(vertical)s, %(erp)s, %(tenant_id)s, %(status)s, %(fonte)s,
            %(doc_id)s, %(doc_titulo)s, %(doc_url)s, %(doc_versao)s, %(breadcrumb)s, %(secao)s,
            %(chunk_idx)s, %(chunk_total)s, %(conteudo)s, %(conteudo_embed)s, %(n_tokens)s,
            %(hash_md5)s, NULL
        ) ON CONFLICT (camada, erp, tenant_id, doc_id, chunk_idx) DO UPDATE SET
            doc_titulo = EXCLUDED.doc_titulo,
            breadcrumb = EXCLUDED.breadcrumb,
            secao = EXCLUDED.secao,
            conteudo = EXCLUDED.conteudo,
            conteudo_embed = EXCLUDED.conteudo_embed,
            n_tokens = EXCLUDED.n_tokens,
            hash_md5 = EXCLUDED.hash_md5,
            status = 'ativo',
            atualizado_em = now();
    """

    records_to_insert = []
    total_chunks_evaluated = 0
    skipped_count = 0

    for r in rows:
        doc_data = {
            "codigo_ref": r[0],
            "modulo": r[1],
            "titulo": r[2],
            "subtitulo": r[3],
            "resumo_executivo": r[4],
            "conteudo_completo": r[5],
            "metadados_json": r[6]
        }
        chunks = chunker.chunk_document(doc_data)
        total_chunks_evaluated += len(chunks)

        for c in chunks:
            if (c.doc_id, c.chunk_idx) in existing_set:
                skipped_count += 1
            else:
                records_to_insert.append({
                    "camada": c.camada,
                    "vertical": c.vertical,
                    "erp": c.erp,
                    "tenant_id": c.tenant_id,
                    "status": "ativo",
                    "fonte": c.fonte,
                    "doc_id": c.doc_id,
                    "doc_titulo": c.doc_titulo,
                    "doc_url": c.doc_url,
                    "doc_versao": c.doc_versao,
                    "breadcrumb": c.breadcrumb,
                    "secao": c.secao,
                    "chunk_idx": c.chunk_idx,
                    "chunk_total": c.chunk_total,
                    "conteudo": c.conteudo,
                    "conteudo_embed": c.conteudo_embed,
                    "n_tokens": c.n_tokens,
                    "hash_md5": c.hash_md5,
                })

    print(f"Chunks avaliados: {total_chunks_evaluated}")
    print(f"Chunks ja persistidos (preservados com embedding intacto): {skipped_count}")
    print(f"Chunks novos a inserir para indice GIN: {len(records_to_insert)}")

    if records_to_insert:
        batch_size = 200
        for i in range(0, len(records_to_insert), batch_size):
            batch = records_to_insert[i:i + batch_size]
            execute_batch(cur_pg, sql_insert, batch, page_size=len(batch))
            conn_pg.commit()
            print(f"  Gravados {min(i + batch_size, len(records_to_insert))}/{len(records_to_insert)} chunks...")

    print("Atualizando estatisticas do planejador (ANALYZE)...")
    cur_pg.execute("ANALYZE aura_core.aura_conhecimento_chunks;")
    conn_pg.commit()

    cur_pg.execute("SELECT count(*), count(DISTINCT doc_id), count(embedding) FROM aura_core.aura_conhecimento_chunks WHERE status = 'ativo';")
    tot, docs, with_emb = cur_pg.fetchone()
    conn_pg.close()

    elapsed = time.perf_counter() - t0
    print("\n=== RESUMO DA CARGA ESTRUTURAL ===")
    print(f"Total de Chunks Ativos no PostgreSQL: {tot}")
    print(f"Documentos Unicos Cobertos: {docs} (de 970)")
    print(f"Chunks com Embedding Vetorial (Gemini): {with_emb}")
    print(f"Chunks com Indice GIN Lexico: {tot} (100%)")
    print(f"Tempo total: {elapsed:.2f}s")

if __name__ == "__main__":
    run_populate()
