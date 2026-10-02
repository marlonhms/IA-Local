"""
Script de Indexação Vetorial e Lexical de Produtos (PostgreSQL 16 + pgvector)
- Lê os produtos do banco ERP local (Porta 5433 - posto)
- Enriquece com gírias/sinônimos comerciais via Gemini
- Gera embeddings usando a API do Google Gemini (gemini-embedding-001)
- Salva os vetores no banco Docker pgvector (Porta 5434 - posto_ai)
- Mantém coluna tsvector e índices HNSW e GIN otimizados
"""

import os
import sys
import time
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values
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
    BASE_DIR,
)


def inicializar_banco_vetorial(conn_vec):
    """Garante que a tabela, tsvector e índices HNSW/GIN existam no posto_ai."""
    with conn_vec.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS produtos_vetores (
                codpro VARCHAR(10) PRIMARY KEY,
                nompro VARCHAR(120) NOT NULL,
                grupo VARCHAR(50),
                codbar VARCHAR(20),
                unidade VARCHAR(10),
                preco NUMERIC(15, 2),
                texto_busca TEXT NOT NULL,
                embedding halfvec(768),
                atualizado_em TIMESTAMP DEFAULT NOW()
            );
        """)

        cur.execute("""
            ALTER TABLE produtos_vetores 
            ADD COLUMN IF NOT EXISTS tsv tsvector 
            GENERATED ALWAYS AS (
                to_tsvector('portuguese', 
                    coalesce(nompro, '') || ' ' || 
                    coalesce(grupo, '') || ' ' || 
                    coalesce(codbar, '') || ' ' || 
                    coalesce(codpro, '') || ' ' ||
                    coalesce(unidade, '')
                )
            ) STORED;
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_produtos_vetores_hnsw 
            ON produtos_vetores USING hnsw (embedding halfvec_cosine_ops)
            WITH (m = 16, ef_construction = 64);
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_produtos_vetores_tsv_gin 
            ON produtos_vetores USING gin (tsv);
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS perguntas_cache (
                id SERIAL PRIMARY KEY,
                pergunta TEXT NOT NULL,
                pergunta_vetor halfvec(768) NOT NULL,
                resposta_llm TEXT NOT NULL,
                json_produtos JSONB NOT NULL,
                criado_em TIMESTAMP DEFAULT NOW()
            );
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_perguntas_cache_hnsw 
            ON perguntas_cache USING hnsw (pergunta_vetor halfvec_cosine_ops)
            WITH (m = 16, ef_construction = 64);
        """)

        conn_vec.commit()
    print("   [OK] Tabela 'produtos_vetores' e índices HNSW + GIN verificados.")


def buscar_produtos_erp(conn_erp):
    """Busca os produtos e seus grupos no banco do ERP."""
    query = """
        SELECT 
            TRIM(p.codpro) as codpro,
            TRIM(p.nompro) as nompro,
            COALESCE(TRIM(g.grupo), 'GERAL') as grupo,
            COALESCE(TRIM(p.codbar), '') as codbar,
            COALESCE(TRIM(p.uni), 'UN') as unidade,
            COALESCE(p.valvenda, 0) as preco
        FROM public.produtos p
        LEFT JOIN public.grupos g ON g.codi = p.codgru
        WHERE p.nompro IS NOT NULL AND TRIM(p.nompro) <> ''
        ORDER BY p.codpro;
    """
    with conn_erp.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
    return rows


import argparse


def main():
    parser = argparse.ArgumentParser(description="Indexador Híbrido de Produtos (Gemini + pgvector)")
    parser.add_argument("--limit", type=int, default=None, help="Limite máximo de produtos a indexar")
    parser.add_argument("--non-interactive", action="store_true", help="Não bloqueia solicitando input interativo")
    args = parser.parse_args()

    print("=" * 65)
    print("  INDEXADOR HÍBRIDO DE PRODUTOS (GEMINI + PGVECTOR + FTS GIN)")
    print("=" * 65)

    if not GEMINI_API_KEY:
        print("\n[ERRO] Por favor, informe sua chave do Gemini no arquivo .env!")
        return

    print("\n1. Conectando aos bancos de dados...")
    senha_arquivo = BASE_DIR / "backups" / "erp_password.txt"
    if senha_arquivo.exists():
        try:
            with open(senha_arquivo, "r", encoding="utf-8-sig") as f:
                DB_ERP_CONFIG["password"] = f.read().strip("\ufeff \r\n\t")
        except Exception:
            pass

    while True:
        try:
            conn_erp = psycopg2.connect(**DB_ERP_CONFIG)
            print(f"   [OK] Conectado ao banco ERP ({DB_ERP_CONFIG.get('dbname')} na porta {DB_ERP_CONFIG.get('port')})")
            senha_arquivo.parent.mkdir(parents=True, exist_ok=True)
            with open(senha_arquivo, "w", encoding="utf-8") as f:
                f.write(DB_ERP_CONFIG["password"])
            break
        except Exception as e:
            if "utf-8" in str(e).lower() or "password" in str(e).lower() or "autenticação" in str(e).lower():
                print("\n   [AVISO ERP] Senha inválida ou expirada.")
                if args.non_interactive:
                    print("   [ERRO] Modo não-interativo ativo. Abortando solicitação de senha.")
                    conn_erp = None
                    break
                nova_senha = input("   Digite a senha do ERP de hoje: ").strip()
                DB_ERP_CONFIG["password"] = nova_senha
            else:
                print(f"   [ERRO FATAL ERP] Banco ERP ({DB_ERP_CONFIG.get('port')}) não conectado: {e}")
                conn_erp = None
                break

    try:
        conn_vec = psycopg2.connect(**DB_VECTOR_CONFIG)
        print("   [OK] Conectado ao banco Vetorial (posto_ai no Docker porta 5434)")
    except Exception as e:
        print(f"   [FALHA] Não foi possível conectar ao banco Docker (5434): {e}")
        if conn_erp:
            conn_erp.close()
        return

    inicializar_banco_vetorial(conn_vec)

    if not conn_erp:
        print("\n[INFO] O banco ERP não está acessível no momento para nova sincronização.")
        conn_vec.close()
        return

    print("\n2. Carregando produtos do ERP e verificando banco vetorial...")
    todos_produtos = buscar_produtos_erp(conn_erp)

    with conn_vec.cursor() as cur:
        cur.execute("SELECT codpro FROM produtos_vetores WHERE embedding IS NOT NULL;")
        ja_indexados = {row[0] for row in cur.fetchall()}

    produtos = [p for p in todos_produtos if p[0] not in ja_indexados]
    total_pendentes = len(produtos)
    if args.limit and args.limit > 0:
        produtos = produtos[:args.limit]
    total = len(produtos)
    print(f"   Total no ERP: {len(todos_produtos)} | Já indexados: {len(ja_indexados)} | Pendentes: {total_pendentes} | Indexando agora: {total}")

    if total == 0:
        print("   [OK] Todos os produtos selecionados já estão indexados no banco vetorial!")
        conn_erp.close()
        conn_vec.close()
        return

    print(f"\n3. Gerando Embeddings para os {total} produtos pendentes...")
    sucessos = 0
    erros = 0
    batch_size = 30

    upsert_sql = """
        INSERT INTO produtos_vetores 
            (codpro, nompro, grupo, codbar, unidade, preco, texto_busca, embedding, atualizado_em)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (codpro) DO UPDATE SET
            nompro = EXCLUDED.nompro,
            grupo = EXCLUDED.grupo,
            codbar = EXCLUDED.codbar,
            unidade = EXCLUDED.unidade,
            preco = EXCLUDED.preco,
            texto_busca = EXCLUDED.texto_busca,
            embedding = EXCLUDED.embedding,
            atualizado_em = NOW();
    """

    with conn_vec.cursor() as cur:
        for i in range(0, total, batch_size):
            lote = produtos[i:i + batch_size]
            textos_lote = []
            dados_lote = []

            prompt_sinonimos = "Gere 2 a 3 gírias curtas, apelidos comerciais ou termos de busca coloquiais para cada produto abaixo. Responda apenas com as gírias separadas por vírgula, uma linha por produto (na exata mesma ordem):\n"
            for p in lote:
                prompt_sinonimos += f"- {p[1]} (Categoria: {p[2]})\n"

            sinonimos_lote = [""] * len(lote)
            try:
                model = genai.GenerativeModel("models/gemini-3.5-flash-lite")
                res = model.generate_content(prompt_sinonimos, request_options={"timeout": 10})
                linhas = [l.strip(" -*") for l in res.text.strip().split("\n") if l.strip()]
                if len(linhas) == len(lote):
                    sinonimos_lote = linhas
            except Exception:
                pass

            for (codpro, nompro, grupo, codbar, unidade, preco), sinonimos in zip(lote, sinonimos_lote):
                texto_busca = f"Produto: {nompro} | Grupo: {grupo} | Unidade: {unidade} | Preço: R$ {preco:.2f}"
                if sinonimos:
                    texto_busca += f" | Tags Populares: {sinonimos}"
                if codbar:
                    texto_busca += f" | Cód. Barras: {codbar}"
                textos_lote.append(texto_busca)
                dados_lote.append((codpro, nompro, grupo, codbar, unidade, preco, texto_busca))

            vetores = None
            for tentativa in range(3):
                try:
                    res = genai.embed_content(
                        model=DEFAULT_EMBEDDING_MODEL,
                        content=textos_lote,
                        output_dimensionality=768,
                        task_type="retrieval_document",
                    )
                    vetores = res["embedding"]
                    break
                except Exception as e:
                    print(f"   [Pausa para cota da API] Aguardando 10s... ({e})")
                    time.sleep(10)

            if vetores:
                for item_dado, vetor in zip(dados_lote, vetores):
                    codpro, nompro, grupo, codbar, unidade, preco, texto_busca = item_dado
                    try:
                        cur.execute(
                            upsert_sql,
                            (codpro, nompro, grupo, codbar, unidade, preco, texto_busca, str(vetor))
                        )
                        sucessos += 1
                    except Exception:
                        erros += 1
                conn_vec.commit()
                fim_lote = min(i + batch_size, total)
                print(f"   [OK] Lote {i // batch_size + 1} salvo: {fim_lote}/{total} produtos indexados...")
            else:
                erros += len(lote)
                print(f"   [ERRO] Falha ao processar lote de {len(lote)} produtos.")

            time.sleep(1)

    conn_erp.close()
    conn_vec.close()

    print("\n" + "=" * 65)
    print(f"  SINCRONIZAÇÃO CONCLUÍDA: {sucessos} produtos salvos | {erros} falhas")
    print("=" * 65)


if __name__ == "__main__":
    main()
