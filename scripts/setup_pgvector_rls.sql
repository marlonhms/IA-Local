-- ============================================================================
-- SCRIPT DE MIGRACAO: ROW-LEVEL SECURITY (RLS) MULTI-TENANT PGVECTOR (FASE 8)
-- Roadmap: docs/roadmap_apendice_conhecimento_multicamada_rag.md (Secao 5.4 e Fase 8)
--
-- Ativa isolamento matematico de conexao por tenant_id em tabelas compartilhadas
-- do banco vetorial central na VPS ou ambiente centralizado.
-- Utiliza current_setting('aura.tenant_id', true) injetado via SET SESSION / SET LOCAL.
--
-- Regra inegociavel: Zero travessoes Unicode (U+2014 e U+2013) neste arquivo.
-- ============================================================================

-- 1. Habilita e forca RLS em aura_core.aura_conhecimento_chunks
ALTER TABLE aura_core.aura_conhecimento_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE aura_core.aura_conhecimento_chunks FORCE ROW LEVEL SECURITY;

-- 1.1 Politica de Leitura Segura:
-- Permite leitura de camadas publicas (core, vertical, erp) OU apenas chunks do tenant ativo
DROP POLICY IF EXISTS escopo_leitura ON aura_core.aura_conhecimento_chunks;
CREATE POLICY escopo_leitura ON aura_core.aura_conhecimento_chunks
    FOR SELECT USING (
        camada IN ('core', 'vertical', 'erp')
        OR tenant_id = current_setting('aura.tenant_id', true)
    );

-- 1.2 Politica de Insercao Restrita:
-- Impede que um posto grave chunks fingindo pertencer a outro tenant
DROP POLICY IF EXISTS escopo_escrita_tenant ON aura_core.aura_conhecimento_chunks;
CREATE POLICY escopo_escrita_tenant ON aura_core.aura_conhecimento_chunks
    FOR INSERT WITH CHECK (
        camada <> 'tenant' OR tenant_id = current_setting('aura.tenant_id', true)
    );

-- 1.3 Politica de Atualizacao:
-- Permite atualizacao apenas de chunks pertencentes ao tenant ativo
DROP POLICY IF EXISTS escopo_update_tenant ON aura_core.aura_conhecimento_chunks;
CREATE POLICY escopo_update_tenant ON aura_core.aura_conhecimento_chunks
    FOR UPDATE USING (
        tenant_id = current_setting('aura.tenant_id', true)
    );

-- 1.4 Politica de Remocao:
DROP POLICY IF EXISTS escopo_delete_tenant ON aura_core.aura_conhecimento_chunks;
CREATE POLICY escopo_delete_tenant ON aura_core.aura_conhecimento_chunks
    FOR DELETE USING (
        tenant_id = current_setting('aura.tenant_id', true)
    );


-- 2. Habilita e forca RLS em aura_core.aura_conhecimento_vetores (tabela historica)
ALTER TABLE aura_core.aura_conhecimento_vetores ENABLE ROW LEVEL SECURITY;
ALTER TABLE aura_core.aura_conhecimento_vetores FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS escopo_leitura_vetores ON aura_core.aura_conhecimento_vetores;
CREATE POLICY escopo_leitura_vetores ON aura_core.aura_conhecimento_vetores
    FOR SELECT USING (
        camada IN ('core', 'vertical', 'erp')
        OR tenant_id = current_setting('aura.tenant_id', true)
    );

DROP POLICY IF EXISTS escopo_escrita_vetores ON aura_core.aura_conhecimento_vetores;
CREATE POLICY escopo_escrita_vetores ON aura_core.aura_conhecimento_vetores
    FOR INSERT WITH CHECK (
        camada <> 'tenant' OR tenant_id = current_setting('aura.tenant_id', true)
    );


-- 3. Configuracao de Roles da VPS
-- Cria a role aura_app_vps sem capacidade de bypass de RLS (NOBYPASSRLS)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'aura_app_vps') THEN
        CREATE ROLE aura_app_vps WITH LOGIN NOBYPASSRLS;
    ELSE
        ALTER ROLE aura_app_vps NOBYPASSRLS;
    END IF;
END
$$;

GRANT USAGE ON SCHEMA aura_core TO aura_app_vps;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA aura_core TO aura_app_vps;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA aura_core TO aura_app_vps;
