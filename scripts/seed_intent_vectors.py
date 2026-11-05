"""
Semeador e Reindexador de Vetores de Intencao (Fase 2 do Roadmap de Verdade Minima).
Garante a indexacao de alta precisao de todas as 30 intencoes operacionais da AURA
na tabela aura_core.intencoes_vetores via pgvector halfvec(768).
Regra inegociavel: ZERO travessoes em todo o arquivo.
"""

import argparse
import logging
import os
import sys
import time
from typing import Any, Dict, List, Set, Tuple

import google.generativeai as genai
import psycopg2
from psycopg2.extras import RealDictCursor

# Ajuste do path para execucao direta do script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.settings import (
    DB_VECTOR_CONFIG,
    DEFAULT_EMBEDDING_MODEL,
    GEMINI_API_KEY,
)
from core.semantic_router import INTENT_EXEMPLARS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("SeedIntentVectors")


def parse_args() -> argparse.Namespace:
    """Configura argumentos de linha de comando."""
    parser = argparse.ArgumentParser(
        description="Semeia vetores de intencoes operacionais no PostgreSQL 16 (pgvector)."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reindexa todas as frases do catalogo do zero (TRUNCATE ou DELETE das intencoes).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas lista intencoes e frases ausentes sem gerar embeddings ou gravar no banco.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=20,
        help="Tamanho do lote para envio a API de embeddings do Gemini (padrao: 20).",
    )
    parser.add_argument(
        "--intent",
        type=str,
        default=None,
        help="Semeia apenas uma intencao especifica (ex: auditoria_fiscal_sefaz).",
    )
    return parser.parse_args()


def get_db_connection() -> psycopg2.extensions.connection:
    """Abre conexao direta com o banco vetorial posto_ai."""
    return psycopg2.connect(**DB_VECTOR_CONFIG)


def get_existing_intents_and_phrases(conn) -> Tuple[Set[str], Set[Tuple[str, str]]]:
    """Retorna conjunto de intencoes existentes e conjunto de tuplas (intencao, frase)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT intencao FROM aura_core.intencoes_vetores WHERE embedding IS NOT NULL;"
        )
        intents = {r[0] for r in cur.fetchall()}

        cur.execute(
            "SELECT intencao, exemplo_frase FROM aura_core.intencoes_vetores WHERE embedding IS NOT NULL;"
        )
        phrases = {(r[0], r[1].strip().lower()) for r in cur.fetchall()}

    return intents, phrases


def seed_intent_vectors(
    force: bool = False,
    dry_run: bool = False,
    batch_size: int = 20,
    target_intent: str = None,
) -> Dict[str, Any]:
    """
    Executa a calibracao e o semeio de vetores no PostgreSQL 16.
    Retorna dicionario com metricas de execucao.
    """
    t0 = time.perf_counter()
    logger.info("Iniciando processo de auditoria e semeio de intencoes vetoriais...")

    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY nao encontrada nas configuracoes de ambiente.")

    genai.configure(api_key=GEMINI_API_KEY)

    conn = get_db_connection()
    try:
        existing_intents, existing_phrases = get_existing_intents_and_phrases(conn)
        logger.info(
            f"Banco atual: {len(existing_phrases)} frases indexadas cobrindo {len(existing_intents)} intencoes."
        )

        catalog_intents = INTENT_EXEMPLARS
        if target_intent:
            if target_intent not in catalog_intents:
                raise ValueError(
                    f"Intencao '{target_intent}' nao encontrada em INTENT_EXEMPLARS. "
                    f"Disponiveis: {list(catalog_intents.keys())}"
                )
            catalog_intents = {target_intent: catalog_intents[target_intent]}

        # Identifica o que precisa ser semeado
        itens_para_semear: List[Tuple[str, str, str]] = []

        if force:
            logger.warning("[MODO FORCE] Todas as frases do catalogo serao reenviadas.")
            for intencao, dados in catalog_intents.items():
                desc = dados["descricao"]
                for frase in dados["exemplos"]:
                    itens_para_semear.append((intencao, desc, frase))
        else:
            for intencao, dados in catalog_intents.items():
                desc = dados["descricao"]
                for frase in dados["exemplos"]:
                    frase_norm = frase.strip().lower()
                    if (intencao, frase_norm) not in existing_phrases:
                        itens_para_semear.append((intencao, desc, frase))

        total_itens = len(itens_para_semear)
        intencoes_afetadas = sorted(list({item[0] for item in itens_para_semear}))

        logger.info(
            f"Itens pendentes de insercao: {total_itens} frases distribuidas em {len(intencoes_afetadas)} intencoes."
        )
        if intencoes_afetadas:
            logger.info(f"Intencoes a sincronizar: {intencoes_afetadas}")

        if dry_run:
            logger.info("[DRY RUN] Execucao simulada concluida. Nenhuma alteracao gravada no banco.")
            return {
                "dry_run": True,
                "pending_items": total_itens,
                "affected_intents": intencoes_afetadas,
                "duration_sec": round(time.perf_counter() - t0, 3),
            }

        if total_itens == 0:
            logger.info("[OK] Todas as intencoes e frases do catalogo ja estao 100% indexadas no banco.")
            return {
                "inserted": 0,
                "affected_intents": [],
                "duration_sec": round(time.perf_counter() - t0, 3),
            }

        # Modo FORCE: limpa antes de reinserir
        if force:
            with conn.cursor() as cur:
                if target_intent:
                    cur.execute(
                        "DELETE FROM aura_core.intencoes_vetores WHERE intencao = %s;",
                        (target_intent,),
                    )
                else:
                    cur.execute("TRUNCATE TABLE aura_core.intencoes_vetores RESTART IDENTITY;")
            conn.commit()
            logger.info("Tabela limpa com sucesso antes do reseeding.")

        # Geracao de embeddings e insercao em lotes
        total_inseridos = 0
        total_batches = (total_itens + batch_size - 1) // batch_size

        for b_idx in range(0, total_itens, batch_size):
            batch = itens_para_semear[b_idx : b_idx + batch_size]
            current_batch_num = (b_idx // batch_size) + 1
            logger.info(
                f"Processando lote {current_batch_num}/{total_batches} ({len(batch)} frases)..."
            )

            textos_para_embedding = [
                f"Intencao: {item[0]} | Pergunta Tipica: {item[2]}" for item in batch
            ]

            # Geracao de embeddings com retry resiliente para rate limit
            max_retries = 4
            emb_list = None
            for attempt in range(1, max_retries + 1):
                try:
                    t_emb = time.perf_counter()
                    res = genai.embed_content(
                        model=DEFAULT_EMBEDDING_MODEL,
                        content=textos_para_embedding,
                        output_dimensionality=768,
                        task_type="retrieval_document",
                    )
                    emb_list = res["embedding"]
                    emb_lat = (time.perf_counter() - t_emb) * 1000
                    logger.info(f"Embeddings do lote {current_batch_num} gerados em {emb_lat:.1f}ms.")
                    break
                except Exception as exc:
                    if "429" in str(exc) or "ResourceExhausted" in str(exc) or "quota" in str(exc).lower():
                        wait_sec = 16.0
                        logger.warning(
                            f"Rate limit (429) detectado. Aguardando {wait_sec}s (tentativa {attempt}/{max_retries})..."
                        )
                        time.sleep(wait_sec)
                    else:
                        raise exc

            if emb_list is None:
                raise RuntimeError(f"Falha ao gerar embeddings do lote {current_batch_num} apos {max_retries} tentativas.")

            with conn.cursor() as cur:
                for (intencao, desc, frase), emb in zip(batch, emb_list):
                    cur.execute(
                        """
                        INSERT INTO aura_core.intencoes_vetores (intencao, descricao, exemplo_frase, embedding)
                        VALUES (%s, %s, %s, %s::halfvec);
                        """,
                        (intencao, desc, frase, str(emb)),
                    )
                    total_inseridos += 1
            conn.commit()
            time.sleep(1.0)

        # Tentativa de reindexacao do grafo HNSW
        reindex_status = "skipped"
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "REINDEX INDEX aura_core.idx_aura_core_intencoes_vetores_hnsw;"
                )
            conn.commit()
            reindex_status = "success"
            logger.info("[OK] Indice HNSW aura_core.idx_aura_core_intencoes_vetores_hnsw reindexado com sucesso.")
        except Exception as e:
            conn.rollback()
            reindex_status = f"notice: {e}"
            logger.info(
                f"[INFO] Manutencao de indice HNSW automatica (grafo atualizado incrementalmente a cada INSERT). Detalhe: {e}"
            )

        duration = round(time.perf_counter() - t0, 3)
        logger.info(
            f"[SUCESSO] {total_inseridos} novos vetores inseridos em {duration}s. Todas as intencoes calibradas."
        )

        # Metricas finais de confirmacao
        final_intents, final_phrases = get_existing_intents_and_phrases(conn)

        return {
            "inserted": total_inseridos,
            "affected_intents": intencoes_afetadas,
            "total_phrases_in_db": len(final_phrases),
            "total_distinct_intents_in_db": len(final_intents),
            "reindex_status": reindex_status,
            "duration_sec": duration,
        }

    finally:
        conn.close()


def main():
    """Ponto de entrada do script CLI."""
    args = parse_args()
    try:
        metrics = seed_intent_vectors(
            force=args.force,
            dry_run=args.dry_run,
            batch_size=args.batch_size,
            target_intent=args.intent,
        )
        print("\n" + "=" * 70)
        print("RESUMO DA EXECUCAO DO SEMEADOR DE VETORES (ETAPA 2)")
        print("=" * 70)
        for k, v in metrics.items():
            print(f"  - {k}: {v}")
        print("=" * 70)
    except Exception as exc:
        logger.error(f"Falha na execucao do semeador: {exc}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
