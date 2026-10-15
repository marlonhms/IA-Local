-- =============================================================================
-- Script de Configuracao de Multi-Tenancy e Row-Level Security (RLS) - P2-5
-- Banco de Dados Alvo: posto_ai (PostgreSQL 16 + pgvector)
-- Tabelas Isoladas: intencoes_vetores, produtos_vetores, conhecimento_operacional
-- Regra de Ouro: ZERO travessoes em comentarios ou definicoes SQL.
-- =============================================================================

BEGIN;

-- 1. Garantir existencia da coluna codfilial com valor padrao seguro (Filial 1)
ALTER TABLE IF EXISTS intencoes_vetores
    ADD COLUMN IF NOT EXISTS codfilial INT NOT NULL DEFAULT 1;

ALTER TABLE IF EXISTS produtos_vetores
    ADD COLUMN IF NOT EXISTS codfilial INT NOT NULL DEFAULT 1;

ALTER TABLE IF EXISTS conhecimento_operacional
    ADD COLUMN IF NOT EXISTS codfilial INT NOT NULL DEFAULT 1;

-- 2. Criar indices compostos por filial para preservar performance sub-5ms
CREATE INDEX IF NOT EXISTS idx_intencoes_vetores_codfilial
    ON intencoes_vetores (codfilial);

CREATE INDEX IF NOT EXISTS idx_produtos_vetores_codfilial
    ON produtos_vetores (codfilial);

CREATE INDEX IF NOT EXISTS idx_conhecimento_operacional_codfilial
    ON conhecimento_operacional (codfilial);

-- 3. Ativar e forcar Row-Level Security (RLS) em todas as tabelas vetoriais
ALTER TABLE intencoes_vetores ENABLE ROW LEVEL SECURITY;
ALTER TABLE intencoes_vetores FORCE ROW LEVEL SECURITY;

ALTER TABLE produtos_vetores ENABLE ROW LEVEL SECURITY;
ALTER TABLE produtos_vetores FORCE ROW LEVEL SECURITY;

ALTER TABLE conhecimento_operacional ENABLE ROW LEVEL SECURITY;
ALTER TABLE conhecimento_operacional FORCE ROW LEVEL SECURITY;

-- 4. Remover politicas anteriores de forma idempotente antes de recriar
DROP POLICY IF EXISTS filial_isolation_policy ON intencoes_vetores;
DROP POLICY IF EXISTS filial_isolation_policy ON produtos_vetores;
DROP POLICY IF EXISTS filial_isolation_policy ON conhecimento_operacional;

-- 5. Criar politicas estritas de isolamento por filial baseadas na GUC de sessao
-- A sessao deve definir: SET SESSION app.current_filial = '1' (ou SET LOCAL)
CREATE POLICY filial_isolation_policy ON intencoes_vetores
    FOR ALL
    USING (codfilial = current_setting('app.current_filial', true)::int)
    WITH CHECK (codfilial = current_setting('app.current_filial', true)::int);

CREATE POLICY filial_isolation_policy ON produtos_vetores
    FOR ALL
    USING (codfilial = current_setting('app.current_filial', true)::int)
    WITH CHECK (codfilial = current_setting('app.current_filial', true)::int);

CREATE POLICY filial_isolation_policy ON conhecimento_operacional
    FOR ALL
    USING (codfilial = current_setting('app.current_filial', true)::int)
    WITH CHECK (codfilial = current_setting('app.current_filial', true)::int);

COMMIT;
