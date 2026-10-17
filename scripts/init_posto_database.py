"""
Script de Inicializacao e Migracao do Banco Vetorial Convergente (Fase 7).
Provisiona o banco 'posto_ai' na porta 5433 com extensao 'vector' (pgvector)
e schemas isolados:
- 'aura_core': inteligencia comercial e operacional da AURA (produtos, intencoes, conhecimento);
- 'n3_sre': telemetria, fingerprints de incidentes e runbooks operacionais do Sentinel.
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
DEFAULT_PORT = int(os.getenv("VECTOR_DB_PORT", "5433"))
DEFAULT_USER = os.getenv("VECTOR_DB_USER", "postgres")
DEFAULT_PASS = os.getenv("VECTOR_DB_PASSWORD", "123456")
DEFAULT_DBNAME = os.getenv("VECTOR_DB_NAME", "posto_ai")
DEFAULT_SCHEMA = os.getenv("VECTOR_TARGET_SCHEMA", "all")

# DDL Declarativo do Schema aura_core (AURA Cognitive & Retail Engine)
DDL_AURA_CORE = """
CREATE SCHEMA IF NOT EXISTS aura_core;

-- 1. Tabela intencoes_vetores (Semantic Router)
CREATE TABLE IF NOT EXISTS aura_core.intencoes_vetores (
    id SERIAL PRIMARY KEY,
    intencao VARCHAR(50) NOT NULL,
    descricao TEXT NOT NULL,
    exemplo_frase TEXT NOT NULL,
    embedding halfvec(768),
    criado_em TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_aura_core_intencoes_vetores_hnsw
ON aura_core.intencoes_vetores
USING hnsw (embedding halfvec_cosine_ops)
WITH (m = 32, ef_construction = 256);

-- 2. Tabela produtos_vetores (RAG Catalogo & Produtos)
CREATE TABLE IF NOT EXISTS aura_core.produtos_vetores (
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

CREATE INDEX IF NOT EXISTS idx_aura_core_produtos_vetores_hnsw
ON aura_core.produtos_vetores
USING hnsw (embedding halfvec_cosine_ops)
WITH (m = 24, ef_construction = 128);

-- 3. Tabela perguntas_cache
CREATE TABLE IF NOT EXISTS aura_core.perguntas_cache (
    id SERIAL PRIMARY KEY,
    pergunta TEXT NOT NULL,
    pergunta_vetor halfvec(768) NOT NULL,
    resposta_llm TEXT NOT NULL,
    json_produtos JSONB NOT NULL,
    criado_em TIMESTAMP DEFAULT NOW()
);

-- 4. Tabela aura_conhecimento_vetores (Meta-RAG)
CREATE TABLE IF NOT EXISTS aura_core.aura_conhecimento_vetores (
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

CREATE INDEX IF NOT EXISTS idx_aura_core_conhecimento_vetores_hnsw
ON aura_core.aura_conhecimento_vetores
USING hnsw (embedding halfvec_cosine_ops)
WITH (m = 24, ef_construction = 128);
"""

# DDL Declarativo do Schema n3_sre (Sentinel SRE & Infrastructure Engine)
DDL_N3_SRE = """
CREATE SCHEMA IF NOT EXISTS n3_sre;

-- 1. Base de conhecimento SRE de concentradores, bicos e TEF
CREATE TABLE IF NOT EXISTS n3_sre.knowledge_base (
    id SERIAL PRIMARY KEY,
    remote_id INTEGER UNIQUE,
    tenant_id VARCHAR(64) NOT NULL DEFAULT 'default',
    doc_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    embedding vector(768),
    synced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_n3_edge_kb_hnsw 
ON n3_sre.knowledge_base USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_n3_edge_kb_fts 
ON n3_sre.knowledge_base USING gin (to_tsvector('portuguese', content));

-- 2. Deteccao anti-storm e fingerprints de incidentes
CREATE TABLE IF NOT EXISTS n3_sre.incident_fingerprints (
    error_hash VARCHAR(64) PRIMARY KEY,
    error_signature TEXT NOT NULL,
    first_seen TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    occurrence_count INTEGER DEFAULT 1
);

-- 3. Runbooks operacionais locais para recuperacao autônoma
CREATE TABLE IF NOT EXISTS n3_sre.sre_runbooks (
    id SERIAL PRIMARY KEY,
    componente VARCHAR(64) NOT NULL,
    falha_sintoma TEXT NOT NULL,
    acao_recuperacao TEXT NOT NULL,
    severidade VARCHAR(20) NOT NULL DEFAULT 'warning',
    embedding halfvec(768),
    atualizado_em TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_n3_sre_runbooks_hnsw
ON n3_sre.sre_runbooks
USING hnsw (embedding halfvec_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 4. Log local de eventos de telemetria do Sentinel
CREATE TABLE IF NOT EXISTS n3_sre.sre_telemetry_events (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
"""


def get_convergence_ddl(target_schema: str = "all") -> str:
    """Retorna o script SQL completo para convergencia declarativa dos schemas."""
    statements = ["CREATE EXTENSION IF NOT EXISTS vector;"]
    if target_schema in ("all", "aura_core"):
        statements.append(DDL_AURA_CORE.strip())
    if target_schema in ("all", "n3_sre"):
        statements.append(DDL_N3_SRE.strip())
    return "\n\n".join(statements)


def parse_args():
    parser = argparse.ArgumentParser(description="Inicializa o banco vetorial pgvector convergente (AURA + Sentinel)")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host do banco vetorial")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Porta do banco vetorial (padrao 5433)")
    parser.add_argument("--user", default=DEFAULT_USER, help="Usuario PostgreSQL")
    parser.add_argument("--password", default=DEFAULT_PASS, help="Senha PostgreSQL")
    parser.add_argument("--dbname", default=DEFAULT_DBNAME, help="Nome do banco de dados (padrao posto_ai)")
    parser.add_argument(
        "--schema",
        choices=["all", "aura_core", "n3_sre"],
        default=DEFAULT_SCHEMA,
        help="Schemas a provisionar: all, aura_core ou n3_sre",
    )
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
        except (psycopg2.OperationalError, UnicodeDecodeError, OSError) as exc:
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


def ensure_backwards_compatibility_views(cur) -> None:
    """
    Garante retrocompatibilidade: se tabelas em public nao existirem como tabelas fisicas,
    cria views apontando para aura_core para garantir funcionamento de queries legadas.
    """
    compat_tables = [
        "intencoes_vetores",
        "produtos_vetores",
        "perguntas_cache",
        "aura_conhecimento_vetores",
    ]
    for tbl in compat_tables:
        cur.execute(
            """
            SELECT table_type FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = %s;
            """,
            (tbl,),
        )
        row = cur.fetchone()
        if not row:
            try:
                cur.execute(f"CREATE OR REPLACE VIEW public.{tbl} AS SELECT * FROM aura_core.{tbl};")
                print(f"[OK] View retrocompativel public.{tbl} criada -> aura_core.{tbl}.")
            except Exception as e:
                print(f"[WARN] Nao foi possivel criar view public.{tbl}: {e}")
        elif row[0] == "VIEW":
            print(f"[OK] View public.{tbl} ja configurada.")
        else:
            print(f"[OK] Tabela fisica public.{tbl} mantida em coexistencia.")


def apply_schema_migrations(
    host: str,
    port: int,
    user: str,
    password: str,
    dbname: str,
    target_schema: str = "all",
) -> None:
    """Aplica as extensoes e esquemas de tabelas vetoriais necessarios para AURA e Sentinel."""
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

        # 2. Schema aura_core (AURA Cognitive & Retail)
        if target_schema in ("all", "aura_core"):
            print("[*] Provisionando schema 'aura_core'...")
            cur.execute(DDL_AURA_CORE)
            print("[OK] Schema 'aura_core' e indices HNSW aplicados.")
            ensure_backwards_compatibility_views(cur)

            # Semeia intencoes se tabela estiver vazia
            cur.execute("SELECT COUNT(*) FROM aura_core.intencoes_vetores;")
            count_intencoes = cur.fetchone()[0]
            if count_intencoes == 0:
                print("[*] Base de intencoes aura_core vazia. Semeando intencoes canonicas...")
                try:
                    from core.semantic_router import SemanticRouter

                    router = SemanticRouter(
                        db_config={
                            "host": host,
                            "port": port,
                            "dbname": dbname,
                            "user": user,
                            "password": password,
                            "options": "-c search_path=aura_core,public",
                        }
                    )
                    router.seed_intents()
                    print("[OK] Intencoes canonicas semeadas em aura_core com sucesso.")
                except Exception as e:
                    print(f"[WARN] Semeio automatico de intencoes adiado: {e}")
            else:
                print(f"[OK] Base aura_core.intencoes_vetores ja possui {count_intencoes} registros.")

        # 3. Schema n3_sre (Sentinel SRE & Infrastructure)
        if target_schema in ("all", "n3_sre"):
            print("[*] Provisionando schema 'n3_sre' do Sentinel...")
            cur.execute(DDL_N3_SRE)
            print("[OK] Schema 'n3_sre' e indices HNSW/GIN do Sentinel aplicados.")

        print(f"[OK] Migracao de schemas ({target_schema}) concluida com sucesso!")

    finally:
        cur.close()
        conn.close()


def main():
    args = parse_args()

    print("=" * 70)
    print("AURA + Sentinel: Inicializacao do Banco Vetorial Convergente (Fase 7)")
    print("=" * 70)
    print(f"Host: {args.host}")
    print(f"Porta: {args.port} (PostgreSQL 16 pgvector compartilhado)")
    print(f"Usuario: {args.user}")
    print(f"Banco: {args.dbname}")
    print(f"Schemas Alvo: {args.schema}")
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
    apply_schema_migrations(
        args.host,
        args.port,
        args.user,
        args.password,
        args.dbname,
        target_schema=args.schema,
    )

    print("=" * 70)
    print("[OK] SUCESSO: Banco vetorial convergente inicializado e pronto para operacao!")
    print("=" * 70)


if __name__ == "__main__":
    main()
