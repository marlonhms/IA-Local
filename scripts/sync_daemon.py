"""
Daemon de Sincronização Contínua (ERP -> pgvector) com Delta Hashing (CDC).
Monitora periodicamente alterações de produtos, preços ou novos cadastros no ERP
e atualiza os vetores no PostgreSQL pgvector automaticamente somente quando o hash_md5 diferir.
"""

import os
import sys
import time
import hashlib
import argparse
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
import google.generativeai as genai

# Garante saída em UTF-8 no terminal Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Adiciona o diretório raiz ao path para importações absolutas
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    GEMINI_API_KEY,
    DB_ERP_CONFIG,
    DB_VECTOR_CONFIG,
    DEFAULT_EMBEDDING_MODEL,
)


def calcular_hash_produto(nompro: str, grupo: str, codbar: str, preco: float, unidade: str) -> str:
    """Calcula hash MD5 determinístico para Change Data Capture (CDC)."""
    nompro_c = (nompro or "").strip().upper()
    grupo_c = (grupo or "GERAL").strip().upper()
    codbar_c = (codbar or "").strip()
    unidade_c = (unidade or "UN").strip().upper()
    try:
        preco_c = f"{float(preco):.2f}"
    except (ValueError, TypeError):
        preco_c = "0.00"
    payload = f"{nompro_c}|{grupo_c}|{codbar_c}|{preco_c}|{unidade_c}"
    return hashlib.md5(payload.encode("utf-8")).hexdigest()


def sync_cycle(conn_erp, conn_vec) -> int:
    """Executa um ciclo único de verificação e sincronização CDC."""
    # 1. Buscar produtos atuais no ERP
    with conn_erp.cursor(cursor_factory=RealDictCursor) as cur_erp:
        cur_erp.execute("""
            SELECT TRIM(p.codpro) as codpro, TRIM(p.nompro) as nompro, 
                   COALESCE(TRIM(g.grupo), 'GERAL') as grupo, COALESCE(TRIM(p.codbar), '') as codbar, 
                   COALESCE(TRIM(p.uni), 'UN') as unidade, COALESCE(p.valvenda, 0) as preco
            FROM public.produtos p
            LEFT JOIN public.grupos g ON g.codi = p.codgru
            WHERE p.nompro IS NOT NULL AND TRIM(p.nompro) <> '';
        """)
        produtos_erp = cur_erp.fetchall()

    # 2. Buscar produtos indexados no pgvector com hash_md5
    with conn_vec.cursor(cursor_factory=RealDictCursor) as cur_vec:
        cur_vec.execute("SELECT codpro, hash_md5 FROM produtos_vetores WHERE embedding IS NOT NULL;")
        produtos_vec = {r['codpro']: r['hash_md5'] for r in cur_vec.fetchall()}

    # 3. Detectar alterações via Delta Hashing (CDC)
    a_atualizar = []
    for p_erp in produtos_erp:
        cod = p_erp['codpro']
        h = calcular_hash_produto(
            p_erp['nompro'], p_erp['grupo'], p_erp['codbar'], p_erp['preco'], p_erp['unidade']
        )
        if cod not in produtos_vec or produtos_vec[cod] != h:
            a_atualizar.append((p_erp, h))

    if a_atualizar:
        print(f"[{time.strftime('%H:%M:%S')}] CDC: Detectados {len(a_atualizar)} produtos alterados/novos de {len(produtos_erp)} totais. Sincronizando...")

        with conn_vec.cursor() as cur_vec:
            for p, h in a_atualizar:
                texto_busca = f"Produto: {p['nompro']} | Grupo: {p['grupo']} | Unidade: {p['unidade']} | Preço: R$ {p['preco']:.2f}"
                if p['codbar']:
                    texto_busca += f" | Cód. Barras: {p['codbar']}"

                res = genai.embed_content(
                    model=DEFAULT_EMBEDDING_MODEL,
                    content=texto_busca,
                    output_dimensionality=768,
                    task_type="retrieval_document"
                )
                vetor = res["embedding"]

                cur_vec.execute("""
                    INSERT INTO produtos_vetores (codpro, nompro, grupo, codbar, unidade, preco, texto_busca, embedding, hash_md5, atualizado_em)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::halfvec, %s, NOW())
                    ON CONFLICT (codpro) DO UPDATE SET
                        nompro = EXCLUDED.nompro, grupo = EXCLUDED.grupo, codbar = EXCLUDED.codbar,
                        unidade = EXCLUDED.unidade, preco = EXCLUDED.preco, texto_busca = EXCLUDED.texto_busca,
                        embedding = EXCLUDED.embedding, hash_md5 = EXCLUDED.hash_md5, atualizado_em = NOW();
                """, (p['codpro'], p['nompro'], p['grupo'], p['codbar'], p['unidade'], p['preco'], texto_busca, str(vetor), h))

            conn_vec.commit()
        print(f"[{time.strftime('%H:%M:%S')}] Sincronização CDC concluída com sucesso ({len(a_atualizar)} atualizados).")
    else:
        economia_pct = 100.0 if produtos_erp else 0.0
        print(f"[{time.strftime('%H:%M:%S')}] CDC Hit: Todos os {len(produtos_erp)} produtos idênticos ({economia_pct:.1f}% economia API).")

    return len(a_atualizar)


def sync_loop(interval_seconds: int = 300, run_once: bool = False):
    print("=" * 65)
    print("  DAEMON DE SINCRONIZAÇÃO CONTÍNUA COM CDC (ERP -> PGVECTOR)")
    print("=" * 65)

    if not GEMINI_API_KEY:
        print("[ERRO] Chave GEMINI_API_KEY não configurada no .env!")
        return

    while True:
        try:
            conn_erp = psycopg2.connect(**DB_ERP_CONFIG)
            conn_vec = psycopg2.connect(**DB_VECTOR_CONFIG)

            sync_cycle(conn_erp, conn_vec)

            conn_erp.close()
            conn_vec.close()

        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] Erro no sync daemon: {e}")

        if run_once:
            break

        print(f"[{time.strftime('%H:%M:%S')}] Aguardando próximo ciclo ({interval_seconds}s)...")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Daemon de Sincronização Contínua com CDC Delta Hash")
    parser.add_argument("--once", action="store_true", help="Executa apenas um ciclo de sincronização e finaliza")
    parser.add_argument("--interval", type=int, default=300, help="Intervalo em segundos entre ciclos")
    args = parser.parse_args()

    sync_loop(interval_seconds=args.interval, run_once=args.once)
