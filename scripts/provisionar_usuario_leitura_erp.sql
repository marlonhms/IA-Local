-- ==============================================================================
-- PROVISIONAMENTO DE USUARIO TECNICO SOMENTE-LEITURA (READ-ONLY) PARA AURA
-- Role: aura_service_ro
-- Finalidade: Blindagem estrita contra escritas e exclusoes acidentais no ERP
-- ==============================================================================

-- 1. Criacao ou atualizacao da role com senha parametrizada
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'aura_service_ro') THEN
        CREATE ROLE aura_service_ro WITH LOGIN PASSWORD 'AuraReadOnly2026!Secure';
        RAISE NOTICE 'Role aura_service_ro criada com sucesso.';
    ELSE
        ALTER ROLE aura_service_ro WITH LOGIN;
        RAISE NOTICE 'Role aura_service_ro ja existe. Privilegios serao atualizados.';
    END IF;
END
$$;

-- 2. Concessao de permissao de conexao no banco posto
GRANT CONNECT ON DATABASE posto TO aura_service_ro;

-- 3. Concessao de uso no esquema public
GRANT USAGE ON SCHEMA public TO aura_service_ro;

-- 4. Concessao de leitura em todas as tabelas e views existentes
GRANT SELECT ON ALL TABLES IN SCHEMA public TO aura_service_ro;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO aura_service_ro;

-- 5. Concessao automatica para futuras tabelas criadas no esquema public
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO aura_service_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON SEQUENCES TO aura_service_ro;

-- 6. Revogacao estrita de qualquer privilegio de mutacao de dados ou esquema
REVOKE CREATE ON SCHEMA public FROM aura_service_ro;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA public FROM aura_service_ro;

-- 7. Confirmacao de seguranca
COMMENT ON ROLE aura_service_ro IS 'Role de servico de leitura da AURA. Acesso estritamente somente-leitura (SELECT).';
