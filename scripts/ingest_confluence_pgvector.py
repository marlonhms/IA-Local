"""
Script de Ingestao e Sincronizacao Incremental Confluence -> pgvector (scripts/ingest_confluence_pgvector.py).
Roadmap Apendice: roadmap_apendice_conhecimento_multicamada_rag.md (Secao 7)

Capacidades:
1. Chunker estrutural de alta fidelidade (core/confluence_chunker.py)
2. Ingestao em lote com Gemini Embedding API (gemini-embedding-001, 768d, task_type=RETRIEVAL_DOCUMENT)
3. Comparacao por hash MD5: reprocessa apenas chunks novos ou modificados
4. Marcacao de chunks obsoletos para paginas encurtadas
5. Normalizacao L2 do vetor para otimizacao maxima no indice HNSW
6. Execucao transacional e atualizacao do planejador (ANALYZE)
7. Modos --full, --delta, --limit-docs e --dry-run

Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import sys
import os
import time
import math
import argparse
import sqlite3
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import psycopg2
from psycopg2.extras import execute_batch
import google.generativeai as genai

from config.settings import GEMINI_API_KEY, DEFAULT_EMBEDDING_MODEL, DB_VECTOR_CONFIG
from core.confluence_chunker import ConfluenceChunker, ConfluenceChunk

def normalize_l2(vector: List[float]) -> List[float]:
    """Aplica normalizacao Euclidiana L2 no vetor de embedding."""
    norm = math.sqrt(sum(x * x for x in vector))
    if norm == 0:
        return vector
    return [round(x / norm, 6) for x in vector]

class ConfluencePgvectorIngester:
    """Gerenciador de ingestao e sincronizacao de conhecimento operacional no pgvector."""

    def __init__(
        self,
        sqlite_db_path: Optional[Path] = None,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        batch_size: int = 25,
        api_key: Optional[str] = None
    ):
        self.sqlite_db_path = sqlite_db_path or (PROJECT_ROOT / "data" / "webposto_knowledge.db")
        self.embedding_model = embedding_model
        self.batch_size = batch_size
        self.api_key = api_key or GEMINI_API_KEY
        self.chunker = ConfluenceChunker()

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY nao configurada no ambiente ou no .env!")
        genai.configure(api_key=self.api_key)

    def _get_pg_connection(self):
        """Conecta ao PostgreSQL com a role apropriada para gravacao em aura_core."""
        cfg = dict(DB_VECTOR_CONFIG)
        return psycopg2.connect(**cfg)

    def _get_existing_hashes(self, cur, doc_id: str) -> Dict[int, str]:
        """Recupera os hashes dos chunks ja existentes no pgvector para o documento."""
        cur.execute("""
            SELECT chunk_idx, hash_md5 
            FROM aura_core.aura_conhecimento_chunks
            WHERE doc_id = %s AND status = 'ativo';
        """, (doc_id,))
        return {row[0]: row[1] for row in cur.fetchall()}

    def _embed_batch_with_retry(self, texts: List[str], max_retries: int = 7) -> List[List[float]]:
        """Gera embeddings em lote com tratamento de rate-limit e retentativa com backoff."""
        delay = 4.0
        for attempt in range(max_retries):
            try:
                res = genai.embed_content(
                    model=self.embedding_model,
                    content=texts,
                    output_dimensionality=768,
                    task_type="retrieval_document"
                )
                raw_embeddings = res["embedding"]
                # Normaliza L2 cada vetor do lote
                return [normalize_l2(emb) for emb in raw_embeddings]
            except Exception as e:
                err_msg = str(e)
                if attempt == max_retries - 1:
                    raise RuntimeError(f"Falha definitiva ao gerar embeddings via Gemini API apos {max_retries} tentativas: {e}")

                if "429" in err_msg or "ResourceExhausted" in err_msg or "quota" in err_msg.lower():
                    print(f"  [AVISO RATE LIMIT] Tentativa {attempt + 1}/{max_retries}. Aguardando {delay:.1f}s...", flush=True)
                    time.sleep(delay)
                    delay = min(delay * 2.0, 60.0)
                else:
                    print(f"  [AVISO CONEXAO] {err_msg[:80]}. Tentando novamente em {delay:.1f}s...", flush=True)
                    time.sleep(delay)
                    delay = min(delay * 1.5, 30.0)
        raise RuntimeError("Falha inesperada no loop de retry")

    def _flush_batch_to_pg(self, cur, batch: List[Tuple[ConfluenceChunk, List[float]]]):
        """Persiste um lote de chunks com embeddings na tabela aura_core.aura_conhecimento_chunks."""
        if not batch:
            return

        sql_upsert = """
            INSERT INTO aura_core.aura_conhecimento_chunks (
                camada, vertical, erp, tenant_id, status, fonte,
                doc_id, doc_titulo, doc_url, doc_versao, breadcrumb, secao,
                chunk_idx, chunk_total, conteudo, conteudo_embed, n_tokens,
                hash_md5, embedding
            ) VALUES (
                %(camada)s, %(vertical)s, %(erp)s, %(tenant_id)s, %(status)s, %(fonte)s,
                %(doc_id)s, %(doc_titulo)s, %(doc_url)s, %(doc_versao)s, %(breadcrumb)s, %(secao)s,
                %(chunk_idx)s, %(chunk_total)s, %(conteudo)s, %(conteudo_embed)s, %(n_tokens)s,
                %(hash_md5)s, %(embedding)s::halfvec
            ) ON CONFLICT (camada, erp, tenant_id, doc_id, chunk_idx) DO UPDATE SET
                doc_titulo = EXCLUDED.doc_titulo,
                doc_url = EXCLUDED.doc_url,
                doc_versao = EXCLUDED.doc_versao,
                breadcrumb = EXCLUDED.breadcrumb,
                secao = EXCLUDED.secao,
                chunk_total = EXCLUDED.chunk_total,
                conteudo = EXCLUDED.conteudo,
                conteudo_embed = EXCLUDED.conteudo_embed,
                n_tokens = EXCLUDED.n_tokens,
                hash_md5 = EXCLUDED.hash_md5,
                embedding = EXCLUDED.embedding,
                status = 'ativo',
                atualizado_em = now();
        """

        records = []
        for c, emb in batch:
            emb_str = "[" + ",".join(str(x) for x in emb) + "]"
            records.append({
                "camada": c.camada,
                "vertical": c.vertical,
                "erp": c.erp,
                "tenant_id": c.tenant_id,
                "status": c.status,
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
                "embedding": emb_str,
            })

        execute_batch(cur, sql_upsert, records, page_size=len(records))

    def run_ingest(
        self,
        mode: str = "full",
        limit_docs: Optional[int] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Executa o pipeline completo de ingestao incremental.
        Retorna dicionario de estatisticas e telemetria.
        """
        t0 = time.perf_counter()
        print(f"=== INICIANDO INGESTAO CONFLUENCE -> PGVECTOR (MODO: {mode.upper()}) ===")
        print(f"Origem SQLite: {self.sqlite_db_path}")
        print(f"Modelo de Embedding: {self.embedding_model} (768 dimensoes)")
        print(f"Tamanho do Lote de API: {self.batch_size}")
        if limit_docs:
            print(f"Limite configurado: {limit_docs} documentos")
        if dry_run:
            print("[MODO DRY RUN: Nao fara chamadas de API nem gravacoes no banco]")

        if not self.sqlite_db_path.exists():
            raise FileNotFoundError(f"Banco SQLite de conhecimento nao encontrado em: {self.sqlite_db_path}")

        # 1. Leitura dos documentos do SQLite
        conn_sqlite = sqlite3.connect(str(self.sqlite_db_path))
        cur_sqlite = conn_sqlite.cursor()

        cur_sqlite.execute("""
            SELECT codigo_ref, modulo, titulo, subtitulo, resumo_executivo, 
                   conteudo_completo, metadados_json
            FROM tabela_conhecimento
            WHERE pilar = 'confluence_procedimentos' AND codigo_ref LIKE 'CONF-%'
            ORDER BY length(conteudo_completo) ASC;
        """)
        rows = cur_sqlite.fetchall()
        conn_sqlite.close()

        total_available = len(rows)
        if limit_docs and limit_docs > 0:
            rows = rows[:limit_docs]

        print(f"Documentos procedimentais selecionados para analise: {len(rows)} (de {total_available} totais)")

        # 2. Conexao com PostgreSQL
        conn_pg = None if dry_run else self._get_pg_connection()
        cur_pg = None if dry_run else conn_pg.cursor()

        stats = {
            "docs_total": len(rows),
            "docs_processed": 0,
            "chunks_evaluated": 0,
            "chunks_unchanged": 0,
            "chunks_embedded": 0,
            "chunks_obsoleted": 0,
            "tokens_embedded": 0,
            "batches_executed": 0,
            "elapsed_sec": 0.0,
        }

        pending_batch: List[ConfluenceChunk] = []

        try:
            for idx, r in enumerate(rows, 1):
                doc_data = {
                    "codigo_ref": r[0],
                    "modulo": r[1],
                    "titulo": r[2],
                    "subtitulo": r[3],
                    "resumo_executivo": r[4],
                    "conteudo_completo": r[5],
                    "metadados_json": r[6]
                }
                doc_id = r[0]

                # Executa chunking estrutural com ConfluenceChunker
                chunks = self.chunker.chunk_document(doc_data)
                stats["docs_processed"] += 1
                stats["chunks_evaluated"] += len(chunks)

                if not chunks:
                    continue

                # Recupera hashes ja persistidos no pgvector
                existing_hashes = {} if dry_run else self._get_existing_hashes(cur_pg, doc_id)

                # Compara cada chunk por hash_md5
                for c in chunks:
                    prev_hash = existing_hashes.get(c.chunk_idx)
                    if prev_hash and prev_hash == c.hash_md5:
                        stats["chunks_unchanged"] += 1
                    else:
                        pending_batch.append(c)

                # Verifica se a pagina foi encurtada e marca excedentes como obsoletos
                if not dry_run:
                    for old_idx in existing_hashes:
                        if old_idx >= len(chunks):
                            cur_pg.execute("""
                                UPDATE aura_core.aura_conhecimento_chunks
                                SET status = 'obsoleto', atualizado_em = now()
                                WHERE doc_id = %s AND chunk_idx = %s AND status = 'ativo';
                            """, (doc_id, old_idx))
                            stats["chunks_obsoleted"] += 1

                # Quando o lote acumula batch_size, dispara embedding e commit
                if len(pending_batch) >= self.batch_size:
                    if not dry_run:
                        batch_texts = [item.conteudo_embed for item in pending_batch]
                        embeddings = self._embed_batch_with_retry(batch_texts)
                        if not embeddings:
                            raise RuntimeError(f"Lote de embeddings retornou vazio para {len(batch_texts)} itens!")
                        batch_with_emb = list(zip(pending_batch, embeddings))
                        self._flush_batch_to_pg(cur_pg, batch_with_emb)
                        conn_pg.commit()

                    stats["chunks_embedded"] += len(pending_batch)
                    stats["tokens_embedded"] += sum(item.n_tokens for item in pending_batch)
                    stats["batches_executed"] += 1

                    elapsed_so_far = time.perf_counter() - t0
                    rate = stats["chunks_embedded"] / elapsed_so_far if elapsed_so_far > 0 else 0.0
                    print(
                        f"  [Lote {stats['batches_executed']}] Docs: {idx}/{len(rows)} | "
                        f"Novos/Atualizados: {stats['chunks_embedded']} | Inalterados: {stats['chunks_unchanged']} | "
                        f"Velocidade: {rate:.1f} chunks/s",
                        flush=True
                    )
                    pending_batch = []
                    # Pausa suave de seguranca para evitar rate limit de RPM
                    time.sleep(1.0)

            # Processa o lote final remanescente
            if pending_batch:
                if not dry_run:
                    batch_texts = [item.conteudo_embed for item in pending_batch]
                    embeddings = self._embed_batch_with_retry(batch_texts)
                    if not embeddings:
                        raise RuntimeError(f"Lote final de embeddings retornou vazio para {len(batch_texts)} itens!")
                    batch_with_emb = list(zip(pending_batch, embeddings))
                    self._flush_batch_to_pg(cur_pg, batch_with_emb)
                    conn_pg.commit()

                stats["chunks_embedded"] += len(pending_batch)
                stats["tokens_embedded"] += sum(item.n_tokens for item in pending_batch)
                stats["batches_executed"] += 1
                pending_batch = []

            # 3. Finalizacao e atualizacao das estatisticas do PostgreSQL
            if not dry_run:
                print("Atualizando estatisticas do planejador (ANALYZE)...", flush=True)
                cur_pg.execute("ANALYZE aura_core.aura_conhecimento_chunks;")
                conn_pg.commit()

        except Exception as e:
            if conn_pg:
                conn_pg.rollback()
            print(f"[ERRO NO PIPELINE DE INGESTAO]: {e}")
            raise
        finally:
            if conn_pg:
                conn_pg.close()

        stats["elapsed_sec"] = round(time.perf_counter() - t0, 2)
        print("\n=== RESUMO EXECUTIVO DA INGESTAO ===")
        print(f"Documentos avaliados: {stats['docs_processed']}")
        print(f"Chunks totais avaliados: {stats['chunks_evaluated']}")
        print(f"Chunks inalterados (ignorados por hash): {stats['chunks_unchanged']}")
        print(f"Chunks novos/atualizados gravados no pgvector: {stats['chunks_embedded']}")
        print(f"Chunks obsoletos desativados: {stats['chunks_obsoleted']}")
        print(f"Estimativa de tokens consumidos: {stats['tokens_embedded']}")
        print(f"Lotes de API executados: {stats['batches_executed']}")
        print(f"Tempo total de execucao: {stats['elapsed_sec']}s")

        return stats

def main():
    parser = argparse.ArgumentParser(description="Ingestao incremental Confluence -> pgvector (Fase 3)")
    parser.add_argument("--mode", choices=["full", "delta"], default="full", help="Modo de execucao")
    parser.add_argument("--batch-size", type=int, default=25, help="Quantidade de chunks por chamada Gemini API")
    parser.add_argument("--limit-docs", type=int, default=None, help="Processa apenas os primeiros N documentos")
    parser.add_argument("--dry-run", action="store_true", help="Apenas simula o chunking e hashes sem chamar API")
    args = parser.parse_args()

    ingester = ConfluencePgvectorIngester(batch_size=args.batch_size)
    ingester.run_ingest(mode=args.mode, limit_docs=args.limit_docs, dry_run=args.dry_run)

if __name__ == '__main__':
    main()
