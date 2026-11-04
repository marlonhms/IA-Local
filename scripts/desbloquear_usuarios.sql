-- Provisionamento soberano e nao-invasivo da role de leitura da AURA (aura_service_ro)
-- Preserva 100% intocadas as senhas nativas de 'postgres' e 'suporte' do ERP
-- PostgreSQL 16 (Porta 5433 / Bancos posto e posto_ai)
-- Zero travessoes

-- 1. Preserva a senha nativa do superuser postgres (evita disparo de auto-reparo do ERP)
ALTER ROLE postgres WITH LOGIN VALID UNTIL 'infinity';
GRANT CONNECT ON DATABASE posto TO postgres;

-- 2. Preserva a senha atual do usuario suporte, apenas removendo a trava de expiracao diaria
ALTER ROLE suporte WITH LOGIN VALID UNTIL 'infinity';
GRANT CONNECT ON DATABASE posto TO suporte;
GRANT USAGE ON SCHEMA public TO suporte;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO suporte;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO suporte;

-- 3. Provisiona e desbloqueia a role de servico dedicada da AURA (somente-leitura permanente)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'aura_service_ro') THEN
        CREATE ROLE aura_service_ro WITH LOGIN PASSWORD '364768' CONNECTION LIMIT -1 VALID UNTIL 'infinity';
    ELSE
        ALTER ROLE aura_service_ro WITH LOGIN PASSWORD '364768' CONNECTION LIMIT -1 VALID UNTIL 'infinity';
    END IF;
END
$$;

-- 4. Permissoes estritamente somente-leitura na base 'posto' para aura_service_ro
GRANT CONNECT ON DATABASE posto TO aura_service_ro;
GRANT USAGE ON SCHEMA public TO aura_service_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO aura_service_ro;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO aura_service_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO aura_service_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON SEQUENCES TO aura_service_ro;
REVOKE CREATE ON SCHEMA public FROM aura_service_ro;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA public FROM aura_service_ro;

-- 5. Permissoes condicionais na base vetorial 'posto_ai' e base 'postgres'
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_database WHERE datname = 'posto_ai') THEN
        EXECUTE 'GRANT CONNECT ON DATABASE posto_ai TO postgres';
        EXECUTE 'GRANT CONNECT ON DATABASE posto_ai TO suporte';
        EXECUTE 'GRANT CONNECT ON DATABASE posto_ai TO aura_service_ro';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_database WHERE datname = 'postgres') THEN
        EXECUTE 'GRANT CONNECT ON DATABASE postgres TO postgres';
        EXECUTE 'GRANT CONNECT ON DATABASE postgres TO aura_service_ro';
    END IF;
END
$$;
