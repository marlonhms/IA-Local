"""
Daemon de Sincronização Contínua (ERP -> pgvector).
Monitora periodicamente alterações de produtos, preços ou novos cadastros no ERP
e atualiza os vetores no PostgreSQL pgvector automaticamente.
"""

import os
import sys
import time
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


def sync_loop():
    print("=" * 65)
    print("  DAEMON DE SINCRONIZAÇÃO CONTÍNUA (ERP -> PGVECTOR)")
    print("=" * 65)

    if not GEMINI_API_KEY:
        print("[ERRO] Chave GEMINI_API_KEY não configurada no .env!")
        return

    while True:
        try:
            conn_erp = psycopg2.connect(**DB_ERP_CONFIG)
            conn_vec = psycopg2.connect(**DB_VECTOR_CONFIG)

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

            # 2. Buscar produtos indexados no pgvector
            with conn_vec.cursor(cursor_factory=RealDictCursor) as cur_vec:
                cur_vec.execute("SELECT codpro, nompro, grupo, codbar, unidade, preco FROM produtos_vetores;")
                produtos_vec = {r['codpro']: r for r in cur_vec.fetchall()}

            # 3. Detectar alterações
            a_atualizar = []
            for p_erp in produtos_erp:
                cod = p_erp['codpro']
                p_vec = produtos_vec.get(cod)

                if (not p_vec or 
                    float(p_vec['preco']) != float(p_erp['preco']) or 
                    p_vec['nompro'] != p_erp['nompro'] or 
                    p_vec['grupo'] != p_erp['grupo']):
                    a_atualizar.append(p_erp)

            if a_atualizar:
                print(f"[{time.strftime('%H:%M:%S')}] Detectados {len(a_atualizar)} produtos alterados/novos. Sincronizando...")

                with conn_vec.cursor() as cur_vec:
                    for p in a_atualizar:
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
                            INSERT INTO produtos_vetores (codpro, nompro, grupo, codbar, unidade, preco, texto_busca, embedding, atualizado_em)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s::halfvec, NOW())
                            ON CONFLICT (codpro) DO UPDATE SET
                                nompro = EXCLUDED.nompro, grupo = EXCLUDED.grupo, codbar = EXCLUDED.codbar,
                                unidade = EXCLUDED.unidade, preco = EXCLUDED.preco, texto_busca = EXCLUDED.texto_busca,
                                embedding = EXCLUDED.embedding, atualizado_em = NOW();
                        """, (p['codpro'], p['nompro'], p['grupo'], p['codbar'], p['unidade'], p['preco'], texto_busca, str(vetor)))

                    conn_vec.commit()
                print(f"[{time.strftime('%H:%M:%S')}] Sincronização concluída com sucesso.")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] Tudo atualizado. Aguardando próximo ciclo (5 minutos)...")

            conn_erp.close()
            conn_vec.close()

        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] Erro no sync daemon: {e}")

        time.sleep(300)


if __name__ == "__main__":
    sync_loop()
