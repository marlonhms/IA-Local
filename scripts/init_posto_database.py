"""
Script de Inicializacao e Migracao do Banco Vetorial da AURA (Fase 2.5).
Provisiona o banco 'posto_ai', instala a extensao 'vector' (pgvector)
e inicializa os esquemas de intencoes, produtos e conhecimento local.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Garante path absoluto
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Configuracoes padrao do banco vetorial
DEFAULT_HOST = os.getenv("VECTOR_DB_HOST", "localhost")
DEFAULT_PORT = int(os.getenv("VECTOR_DB_PORT", "5434"))
DEFAULT_USER = os.getenv("VECTOR_DB_USER", "postgres")
DEFAULT_PASS = os.getenv("VECTOR_DB_PASSWORD", "aura_vector_secret_2026")
DEFAULT_DBNAME = os.getenv("VECTOR_DB_NAME", "posto_ai")


def parse_args():
    parser = argparse.ArgumentParser(description="Inicializa o banco vetorial pgvector da AURA")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host do banco vetorial")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Porta do banco vetorial")
    parser.add_argument("--user", default=DEFAULT_USER, help="Usuario PostgreSQL")
    parser.add_argument("--password", default=DEFAULT_PASS, help="Senha PostgreSQL")
    parser.add_argument("--dbname", default=DEFAULT_DBNAME, help="Nome do banco de dados")
    parser.add_argument("--max-retries", type=int, default=15, help="Tentativas maximas de conexao")
    parser.add_argument("--retry-delay", type=float, default=2.0, help="Intervalo entre tentativas em segundos")
    parser.add_argument("--check-only", action="store_true", help="Apenas verifica a saude do banco sem migrar")
    return parser.parse_args()


def wait_for_postgres(host: str, port: int, user: str, password: str, max_retries: int, delay: float) -> bool:
    """Aguarda o servico PostgreSQL ficar pronto para aceitar conexoes."""
    print(f"[*] Aguardando PostgreSQL em {host}:{port} ficar disponivel...")
    for attempt in range(1, max_retries + 1):
        try:
            conn = psycopg2.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                dbname="postgres",
                connect_timeout=3,
            )
            conn.close()
            print(f"[OK] PostgreSQL pronto e respondendo na porta {port} (tentativa {attempt}/{max_retries}).")
            return True
        except psycopg2.OperationalError as exc:
            print(f"    Tentativa {attempt}/{max_retries} falhou ({exc!s}). Aguardando {delay}s...")
            time.sleep(delay)
    return False


def ensure_database_exists(host: str, port: int, user: str, password: str, dbname: str) -> None:
    """Cria o banco de dados se ele ainda nao existir."""
    conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname="postgres",
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    try:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (dbname,))
        if not cur.fetchone():
            print(f"[*] Criando banco de dados '{dbname}'...")
            cur.execute(f'CREATE DATABASE "{dbname}";')
            print(f"[OK] Banco de dados '{dbname}' criado com sucesso.")
        else:
            print(f"[OK] Banco de dados '{dbname}' ja existe.")
    finally:
        cur.close()
        conn.close()


def apply_schema_migrations(host: str, port: int, user: str, password: str, dbname: str) -> None:
    """Aplica as extensoes e esquemas de tabelas vetoriais necessarios."""
    conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=dbname,
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    try:
        # 1. Extensao vector
        print("[*] Instalando/Verificando extensao pgvector...")
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        print("[OK] Extensao pgvector ativa.")

        # 2. Tabela intencoes_vetores (Semantic Router)
        print("[*] Configurando tabela 'intencoes_vetores'...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS public.intencoes_vetores (
                id SERIAL PRIMARY KEY,
                intencao VARCHAR(50) NOT NULL,
                descricao TEXT NOT NULL,
                exemplo_frase TEXT NOT NULL,
                embedding halfvec(768),
                criado_em TIMESTAMP DEFAULT NOW()
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_intencoes_vetores_hnsw
            ON public.intencoes_vetores
            USING hnsw (embedding halfvec_cosine_ops)
            WITH (m = 32, ef_construction = 256);
        """)

        # 3. Tabela produtos_vetores (RAG Catalogo & Produtos)
        print("[*] Configurando tabela 'produtos_vetores'...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS public.produtos_vetores (
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
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_produtos_vetores_hnsw
            ON public.produtos_vetores
            USING hnsw (embedding halfvec_cosine_ops)
            WITH (m = 24, ef_construction = 128);
        """)

        # 4. Tabela perguntas_cache
        print("[*] Configurando tabela 'perguntas_cache'...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS public.perguntas_cache (
                id SERIAL PRIMARY KEY,
                pergunta TEXT NOT NULL,
                pergunta_vetor halfvec(768) NOT NULL,
                resposta_llm TEXT NOT NULL,
                json_produtos JSONB NOT NULL,
                criado_em TIMESTAMP DEFAULT NOW()
            );
        """)

        # 5. Tabela aura_conhecimento_vetores (Meta-RAG)
        print("[*] Configurando tabela 'aura_conhecimento_vetores'...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS public.aura_conhecimento_vetores (
                id SERIAL PRIMARY KEY,
                modulo VARCHAR(50) NOT NULL,
                topico VARCHAR(100) NOT NULL,
                titulo VARCHAR(150) NOT NULL,
                subtitulo VARCHAR(255),
                conteudo TEXT NOT NULL,
                elementos_ui JSONB,
                ui_action JSONB,
                tags TEXT[],
                embedding halfvec(768),
                criado_em TIMESTAMP DEFAULT NOW()
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_conhecimento_vetores_hnsw
            ON public.aura_conhecimento_vetores
            USING hnsw (embedding halfvec_cosine_ops)
            WITH (m = 24, ef_construction = 128);
        """)

        print("[OK] Todos os esquemas e indices vetoriais foram aplicados com sucesso.")

        # 6. Semeia intencoes canônicas se vazia
        cur.execute("SELECT COUNT(*) FROM public.intencoes_vetores;")
        count_intencoes = cur.fetchone()[0]
        if count_intencoes == 0:
            print("[*] Base de intencoes vazia. Inicializando intencoes canonicas...")
            try:
                from core.semantic_router import SemanticRouter
                router = SemanticRouter(host=host, port=port, dbname=dbname, user=user, password=password)
                router.seed_default_intents()
                print("[OK] Intencoes canonicas semeadas com sucesso.")
            except Exception as e:
                print(f"[WARN] Nao foi possivel semear intencoes automaticamente: {e}")
        else:
            print(f"[OK] Base de intencoes ja possui {count_intencoes} registros.")

    finally:
        cur.close()
        conn.close()


def main():
    args = parse_args()

    print("=" * 70)
    print("AURA Core Engine: Inicializacao do Banco Vetorial (Fase 2.5)")
    print("=" * 70)
    print(f"Host: {args.host}")
    print(f"Porta: {args.port}")
    print(f"Usuario: {args.user}")
    print(f"Banco: {args.dbname}")
    print("=" * 70)

    # Passo 1: Aguarda servico
    if not wait_for_postgres(args.host, args.port, args.user, args.password, args.max_retries, args.retry_delay):
        print(f"[!] ERRO CRITICO: Nao foi possivel conectar ao PostgreSQL em {args.host}:{args.port}.")
        sys.exit(1)

    if args.check_only:
        print("[OK] Verificacao de saude concluida com sucesso. Banco ativo.")
        sys.exit(0)

    # Passo 2: Garante existencia do banco
    ensure_database_exists(args.host, args.port, args.user, args.password, args.dbname)

    # Passo 3: Aplica extensoes e tabelas
    apply_schema_migrations(args.host, args.port, args.user, args.password, args.dbname)

    print("=" * 70)
    print("[OK] SUCESSO: Banco vetorial inicializado e pronto para operacao!")
    print("=" * 70)


if __name__ == "__main__":
    main()
