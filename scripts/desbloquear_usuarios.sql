-- Desbloqueio e renovacao de senhas de producao para o PDV e AURA
-- PostgreSQL 16 (Porta 5433 / Banco posto)
-- Zero travessoes

-- 1. Desbloqueia e renova o usuario superuser postgres
ALTER ROLE postgres WITH LOGIN PASSWORD '123456' VALID UNTIL 'infinity';
GRANT CONNECT ON DATABASE posto TO postgres;

-- 2. Desbloqueia e renova o usuario do PDV (suporte) eliminando expiracao de senha
ALTER ROLE suporte WITH LOGIN PASSWORD '123456' VALID UNTIL 'infinity';
GRANT CONNECT ON DATABASE posto TO suporte;
GRANT USAGE ON SCHEMA public TO suporte;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO suporte;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO suporte;

-- 3. Provisiona e desbloqueia a role de servico da AURA
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'aura_service_ro') THEN
        CREATE ROLE aura_service_ro WITH LOGIN PASSWORD '123456' CONNECTION LIMIT -1 VALID UNTIL 'infinity';
    ELSE
        ALTER ROLE aura_service_ro WITH LOGIN PASSWORD '123456' CONNECTION LIMIT -1 VALID UNTIL 'infinity';
    END IF;
END
$$;

-- Permissoes na base 'posto' para aura_service_ro
GRANT CONNECT ON DATABASE posto TO aura_service_ro;
GRANT USAGE ON SCHEMA public TO aura_service_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO aura_service_ro;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO aura_service_ro;

-- Permissoes condicionais em bases auxiliares
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_database WHERE datname = 'posto_ai') THEN
        EXECUTE 'GRANT CONNECT ON DATABASE posto_ai TO postgres';
        EXECUTE 'GRANT CONNECT ON DATABASE posto_ai TO aura_service_ro';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_database WHERE datname = 'postgres') THEN
        EXECUTE 'GRANT CONNECT ON DATABASE postgres TO postgres';
        EXECUTE 'GRANT CONNECT ON DATABASE postgres TO aura_service_ro';
    END IF;
END
$$;

