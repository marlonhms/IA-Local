"""
Script de Migracao da Fase 1: Esquema Multicamada e Tabela de Chunks
Roadmap Apendice: roadmap_apendice_conhecimento_multicamada_rag.md (Secoes 5.2 e 5.3)

Aplica de forma transacional e reversivel:
1. Evolucao de aura_core.aura_conhecimento_vetores com colunas de escopo (camada, vertical, erp, tenant_id, status)
2. Classificacao das 26 sementes cognitivas em 'core' e 'vertical' (com tenant_id = 'posto_local')
3. View de retrocompatibilidade public.aura_conhecimento_vetores apontando para aura_core
4. Criacao da tabela canônica de alta performance aura_core.aura_conhecimento_chunks
5. Indices HNSW (halfvec_cosine_ops), GIN (tsvector em portugues) e B-Tree de escopo relacional
6. Concessao de privilegios para suporte e aura_service_ro

Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import sys
import os
from pathlib import Path
import psycopg2

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.db_pool import DB_VECTOR_CONFIG

def get_admin_connection():
    # Usa usuario postgres para operacoes de DDL e troca de schema
    cfg = dict(DB_VECTOR_CONFIG)
    cfg["user"] = "postgres"
    return psycopg2.connect(**cfg)

def apply_phase1():
    print("=== INICIANDO APLICACAO DA FASE 1: RAG MULTICAMADA ===")
    conn = get_admin_connection()
    try:
        with conn.cursor() as cur:
            # 1. Garante extensao vector e schema aura_core
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute("CREATE SCHEMA IF NOT EXISTS aura_core;")
            
            # 2. Adiciona colunas de escopo em aura_core.aura_conhecimento_vetores
            print("[1/5] Adicionando colunas de escopo em aura_core.aura_conhecimento_vetores...")
            cur.execute("""
                ALTER TABLE aura_core.aura_conhecimento_vetores
                    ADD COLUMN IF NOT EXISTS camada TEXT NOT NULL DEFAULT 'core',
                    ADD COLUMN IF NOT EXISTS vertical TEXT,
                    ADD COLUMN IF NOT EXISTS erp TEXT,
                    ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'posto_local',
                    ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'ativo';
            """)
            
            # Adiciona constraints se nao existirem
            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'chk_aura_vetores_camada'
                    ) THEN
                        ALTER TABLE aura_core.aura_conhecimento_vetores
                            ADD CONSTRAINT chk_aura_vetores_camada 
                            CHECK (camada IN ('core', 'vertical', 'erp', 'tenant'));
                    END IF;
                    
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'chk_aura_vetores_status'
                    ) THEN
                        ALTER TABLE aura_core.aura_conhecimento_vetores
                            ADD CONSTRAINT chk_aura_vetores_status 
                            CHECK (status IN ('ativo', 'pendente', 'obsoleto'));
                    END IF;
                END
                $$;
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_aura_core_vetores_escopo
                ON aura_core.aura_conhecimento_vetores (camada, vertical, erp, tenant_id, status);
            """)
            
            # 3. Classificacao das 26 sementes
            print("[2/5] Classificando as 26 sementes cognitivas existentes...")
            cur.execute("""
                UPDATE aura_core.aura_conhecimento_vetores 
                SET camada = 'core',
                    vertical = NULL,
                    erp = NULL,
                    tenant_id = 'posto_local',
                    status = 'ativo'
                WHERE modulo IN (
                    'compliance_anp', 'macroeconomia_bacen', 'metrologia_inmetro',
                    'tributario_combustiveis', 'fiscal', 'navegacao', 'console'
                );
            """)
            
            cur.execute("""
                UPDATE aura_core.aura_conhecimento_vetores 
                SET camada = 'vertical',
                    vertical = 'posto',
                    erp = NULL,
                    tenant_id = 'posto_local',
                    status = 'ativo'
                WHERE modulo IN (
                    'cockpit', 'conciliacao', 'triggers', 'split', 'conveniencia'
                );
            """)
            
            # 4. View de retrocompatibilidade em public
            print("[3/5] Configurando view retrocompativel em public.aura_conhecimento_vetores...")
            # Verifica se public.aura_conhecimento_vetores e tabela física ou view
            cur.execute("""
                SELECT table_type FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'aura_conhecimento_vetores';
            """)
            row = cur.fetchone()
            if row and row[0] == 'BASE TABLE':
                cur.execute("DROP TABLE public.aura_conhecimento_vetores CASCADE;")
            
            cur.execute("""
                CREATE OR REPLACE VIEW public.aura_conhecimento_vetores AS 
                SELECT * FROM aura_core.aura_conhecimento_vetores;
            """)
            
            # 5. Criacao da tabela aura_core.aura_conhecimento_chunks
            print("[4/5] Criando tabela de alta performance aura_core.aura_conhecimento_chunks...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS aura_core.aura_conhecimento_chunks (
                    id              BIGSERIAL PRIMARY KEY,
                    camada          TEXT NOT NULL CHECK (camada IN ('core','vertical','erp','tenant')),
                    vertical        TEXT,
                    erp             TEXT,
                    tenant_id       TEXT NOT NULL DEFAULT 'posto_local',
                    status          TEXT NOT NULL DEFAULT 'ativo' CHECK (status IN ('ativo','pendente','obsoleto')),

                    -- Origem e rastreabilidade
                    fonte           TEXT NOT NULL,
                    doc_id          TEXT NOT NULL,
                    doc_titulo      TEXT NOT NULL,
                    doc_url         TEXT,
                    doc_versao      INTEGER,
                    breadcrumb      TEXT,
                    secao           TEXT,
                    chunk_idx       INTEGER NOT NULL,
                    chunk_total     INTEGER NOT NULL,

                    -- Conteudo
                    conteudo        TEXT NOT NULL,
                    conteudo_embed  TEXT NOT NULL,
                    n_tokens        INTEGER,
                    hash_md5        TEXT NOT NULL,
                    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT now(),

                    embedding       halfvec(768),
                    tsv             tsvector GENERATED ALWAYS AS (
                                        setweight(to_tsvector('portuguese', coalesce(doc_titulo,'')), 'A') ||
                                        setweight(to_tsvector('portuguese', coalesce(breadcrumb,'')), 'B') ||
                                        setweight(to_tsvector('portuguese', coalesce(conteudo,'')),   'C')
                                    ) STORED,

                    UNIQUE (camada, erp, tenant_id, doc_id, chunk_idx)
                );
            """)
            
            # Indices da tabela de chunks
            print("     Criando indices HNSW, GIN e Escopo relacional...")
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunks_hnsw
                ON aura_core.aura_conhecimento_chunks
                USING hnsw (embedding halfvec_cosine_ops) WITH (m = 24, ef_construction = 128);
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunks_tsv 
                ON aura_core.aura_conhecimento_chunks USING gin (tsv);
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunks_escopo
                ON aura_core.aura_conhecimento_chunks (camada, vertical, erp, tenant_id, status);
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunks_doc
                ON aura_core.aura_conhecimento_chunks (doc_id, doc_versao);
            """)
            
            # View retrocompativel em public para chunks
            cur.execute("""
                CREATE OR REPLACE VIEW public.aura_conhecimento_chunks AS 
                SELECT * FROM aura_core.aura_conhecimento_chunks;
            """)
            
            # 6. Concessao de privilegios para suporte e aura_service_ro
            print("[5/5] Concedendo privilegios a suporte e aura_service_ro...")
            for usr in ('suporte', 'aura_service_ro'):
                cur.execute(f"GRANT USAGE ON SCHEMA aura_core TO {usr};")
                cur.execute(f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA aura_core TO {usr};")
                cur.execute(f"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA aura_core TO {usr};")
                cur.execute(f"GRANT SELECT ON public.aura_conhecimento_vetores TO {usr};")
                cur.execute(f"GRANT SELECT ON public.aura_conhecimento_chunks TO {usr};")
                
        conn.commit()
        print("[SUCESSO] MIGRACAO DA FASE 1 APLICADA COM EXITO!")
    except Exception as e:
        conn.rollback()
        print(f"[ERRO FATAL NA MIGRACAO]: {e}")
        raise
    finally:
        conn.close()

def rollback_phase1():
    print("=== EXECUTANDO ROLLBACK DA FASE 1 ===")
    conn = get_admin_connection()
    try:
        with conn.cursor() as cur:
            # 1. Drop das tabelas e views de chunks
            cur.execute("DROP VIEW IF EXISTS public.aura_conhecimento_chunks CASCADE;")
            cur.execute("DROP TABLE IF EXISTS aura_core.aura_conhecimento_chunks CASCADE;")
            
            # 2. Remove constraints e colunas adicionadas
            cur.execute("""
                ALTER TABLE aura_core.aura_conhecimento_vetores
                    DROP CONSTRAINT IF EXISTS chk_aura_vetores_camada,
                    DROP CONSTRAINT IF EXISTS chk_aura_vetores_status,
                    DROP COLUMN IF EXISTS camada,
                    DROP COLUMN IF EXISTS vertical,
                    DROP COLUMN IF EXISTS erp,
                    DROP COLUMN IF EXISTS tenant_id,
                    DROP COLUMN IF EXISTS status;
            """)
            
        conn.commit()
        print("[SUCESSO] ROLLBACK DA FASE 1 CONCLUIDO!")
    except Exception as e:
        conn.rollback()
        print(f"[ERRO NO ROLLBACK]: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else "apply"
    if mode == "apply":
        apply_phase1()
    elif mode == "rollback":
        rollback_phase1()
    else:
        print(f"Modo desconhecido: {mode}. Use 'apply' ou 'rollback'.")
