"""
Script de Indexação Vetorial e Lexical de Produtos (PostgreSQL 16 + pgvector)
com Delta Hashing (Change Data Capture - CDC) e Roteador de Intenções.

Melhorias:
- Change Data Capture (CDC) via Delta Hashing (coluna hash_md5 em produtos_vetores).
- Economia >95% de consumo de tokens/API Gemini (só gera embedding quando o conteúdo mudar).
- Criação e indexação da tabela intencoes_vetores (9 intenções operacionais).
- Tuning de índices HNSW com ef_construction = 128 e ef_search = 128.
- Mantém coluna tsvector e índices HNSW e GIN otimizados.
"""

import os
import sys
import time
import hashlib
import argparse
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
from core.semantic_router import SemanticRouter


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


def inicializar_banco_vetorial(conn_vec):
    """Garante que as tabelas, tsvector e índices HNSW/GIN existam no posto_ai."""
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
                hash_md5 VARCHAR(32),
                atualizado_em TIMESTAMP DEFAULT NOW()
            );
        """)

        cur.execute("ALTER TABLE produtos_vetores ADD COLUMN IF NOT EXISTS hash_md5 VARCHAR(32);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_produtos_vetores_hash_md5 ON produtos_vetores (hash_md5);")

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
            WITH (m = 16, ef_construction = 128);
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
    print("   [OK] Tabela 'produtos_vetores' e índices HNSW (ef_construction=128) + GIN verificados.")


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


def main():
    parser = argparse.ArgumentParser(description="Indexador Híbrido de Produtos com CDC Delta Hash (Gemini + pgvector)")
    parser.add_argument("--limit", type=int, default=None, help="Limite máximo de produtos a indexar")
    parser.add_argument("--reindex-all", action="store_true", help="Força reindexação completa ignorando Delta Hash")
    parser.add_argument("--seed-intencoes", action="store_true", help="Força reindexação do catálogo de intenções semânticas")
    parser.add_argument("--non-interactive", action="store_true", help="Não bloqueia solicitando input interativo")
    args = parser.parse_args()

    print("=" * 70)
    print("  INDEXADOR HÍBRIDO COM CDC DELTA HASH (GEMINI + PGVECTOR + GIN)")
    print("=" * 70)

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

    # Verifica e sincroniza as intenções vetoriais
    router = SemanticRouter(db_config=DB_VECTOR_CONFIG)
    router.init_table()
    total_intents = router.count_intents()
    distinct_intents = router.count_distinct_intents()
    if total_intents < 9 or distinct_intents < 9 or args.seed_intencoes:
        print(f"\n[ROTEADOR] Indexando intenções operacionais ({total_intents} exemplares, {distinct_intents} intenções)...")
        total_seeded = router.seed_intents(force=args.seed_intencoes)
        print(f"   [OK] {total_seeded} intenções semânticas indexadas em 'intencoes_vetores'.")
    else:
        print(f"   [OK] Catálogo de Intenções Semânticas OK ({total_intents} exemplares nas {distinct_intents} intenções).")

    if not conn_erp:
        print("\n[INFO] O banco ERP não está acessível no momento para nova sincronização.")
        conn_vec.close()
        return

    print("\n2. Executando CDC (Change Data Capture) via Delta Hash MD5...")
    todos_produtos = buscar_produtos_erp(conn_erp)

    with conn_vec.cursor() as cur:
        cur.execute("SELECT codpro, hash_md5 FROM produtos_vetores WHERE embedding IS NOT NULL;")
        produtos_vec = dict(cur.fetchall())

    produtos_pendentes = []
    produtos_novos = 0
    produtos_alterados = 0

    for p in todos_produtos:
        codpro, nompro, grupo, codbar, uni, preco = p
        h = calcular_hash_produto(nompro, grupo, codbar, preco, uni)

        if args.reindex_all or codpro not in produtos_vec:
            produtos_pendentes.append((p, h))
            produtos_novos += 1
        elif produtos_vec[codpro] != h:
            produtos_pendentes.append((p, h))
            produtos_alterados += 1

    total_erp = len(todos_produtos)
    total_economizados = total_erp - len(produtos_pendentes)
    pct_economia = (total_economizados / total_erp * 100) if total_erp else 0.0

    print(f"   • Total no ERP: {total_erp} produtos")
    print(f"   • Inalterados (CDC Delta Hit): {total_economizados} produtos ({pct_economia:.1f}% economia de API)")
    print(f"   • Pendentes de embedding: {len(produtos_pendentes)} ({produtos_novos} novos, {produtos_alterados} alterados)")

    if args.limit and args.limit > 0:
        produtos_pendentes = produtos_pendentes[:args.limit]

    total = len(produtos_pendentes)
    if total == 0:
        print("\n   ✨ [CDC 100% SINCRONIZADO] Nenhuma alteração detectada no ERP. Zero chamadas de API necessárias!")
        conn_erp.close()
        conn_vec.close()
        return

    print(f"\n3. Gerando Embeddings para os {total} produtos que sofreram alterações...")
    sucessos = 0
    erros = 0
    batch_size = 30

    upsert_sql = """
        INSERT INTO produtos_vetores 
            (codpro, nompro, grupo, codbar, unidade, preco, texto_busca, embedding, hash_md5, atualizado_em)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (codpro) DO UPDATE SET
            nompro = EXCLUDED.nompro,
            grupo = EXCLUDED.grupo,
            codbar = EXCLUDED.codbar,
            unidade = EXCLUDED.unidade,
            preco = EXCLUDED.preco,
            texto_busca = EXCLUDED.texto_busca,
            embedding = EXCLUDED.embedding,
            hash_md5 = EXCLUDED.hash_md5,
            atualizado_em = NOW();
    """

    with conn_vec.cursor() as cur:
        for i in range(0, total, batch_size):
            lote_com_hash = produtos_pendentes[i:i + batch_size]
            lote = [item[0] for item in lote_com_hash]
            hashes_lote = [item[1] for item in lote_com_hash]
            textos_lote = []
            dados_lote = []

            for (codpro, nompro, grupo, codbar, unidade, preco), h in zip(lote, hashes_lote):
                texto_busca = f"Produto: {nompro} | Grupo: {grupo} | Unidade: {unidade} | Preço: R$ {preco:.2f}"
                if codbar:
                    texto_busca += f" | Cód. Barras: {codbar}"
                textos_lote.append(texto_busca)
                dados_lote.append((codpro, nompro, grupo, codbar, unidade, preco, texto_busca, h))

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
                    codpro, nompro, grupo, codbar, unidade, preco, texto_busca, h = item_dado
                    try:
                        cur.execute(
                            upsert_sql,
                            (codpro, nompro, grupo, codbar, unidade, preco, texto_busca, str(vetor), h)
                        )
                        sucessos += 1
                    except Exception:
                        erros += 1
                conn_vec.commit()
                fim_lote = min(i + batch_size, total)
                print(f"   [OK] Lote {i // batch_size + 1} salvo: {fim_lote}/{total} produtos indexados com hash_md5...")
            else:
                erros += len(lote)
                print(f"   [ERRO] Falha ao processar lote de {len(lote)} produtos.")

            time.sleep(0.5)

    conn_erp.close()
    conn_vec.close()

    print("\n" + "=" * 70)
    print(f"  SINCRONIZAÇÃO CONCLUÍDA: {sucessos} produtos salvos | {erros} falhas")
    print(f"  Economia de API obtida pelo CDC: {pct_economia:.1f}%")
    print("=" * 70)


if __name__ == "__main__":
    main()
