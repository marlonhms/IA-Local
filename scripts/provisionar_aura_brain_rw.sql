-- Provisionamento da Role Soberana do Cerebro Cognitivo da AURA (aura_brain_rw)
-- Escopo ESTRITO: dona exclusiva do banco vetorial 'posto_ai' e schemas 'aura_core' / 'n3_sre'
-- Isolamento Clean Room: ZERO acesso ao banco transacional 'posto' do PDV
-- Uso: definir SET aura.brain_rw_password = '...' antes de executar em posto_ai
-- Zero travessoes

SET lock_timeout = '1500ms';
SET statement_timeout = '5000ms';

DO $$
DECLARE
    v_pass TEXT := current_setting('aura.brain_rw_password', true);
    r_obj RECORD;
BEGIN
    IF v_pass IS NULL OR length(trim(v_pass)) < 12 THEN
        RAISE EXCEPTION 'Defina aura.brain_rw_password (minimo 12 caracteres) antes de provisionar aura_brain_rw.';
    END IF;

    -- 1. Cria ou atualiza role exclusiva do cerebro cognitivo (sem superuser, sem acesso ao ERP)
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'aura_brain_rw') THEN
        EXECUTE format(
            'CREATE ROLE aura_brain_rw WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD %L CONNECTION LIMIT -1 VALID UNTIL %L',
            v_pass,
            'infinity'
        );
    ELSE
        EXECUTE format(
            'ALTER ROLE aura_brain_rw WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD %L CONNECTION LIMIT -1 VALID UNTIL %L',
            v_pass,
            'infinity'
        );
    END IF;

    -- 2. Blindagem Clean Room: garante revogacao explicita no banco transacional 'posto' do PDV
    IF EXISTS (SELECT 1 FROM pg_database WHERE datname = 'posto') THEN
        EXECUTE 'REVOKE ALL ON DATABASE posto FROM aura_brain_rw';
    END IF;

    -- 3. Propriedade plena do banco posto_ai e schemas cognitivos da AURA
    EXECUTE 'GRANT ALL PRIVILEGES ON DATABASE posto_ai TO aura_brain_rw';
    EXECUTE 'CREATE SCHEMA IF NOT EXISTS aura_core AUTHORIZATION aura_brain_rw';
    EXECUTE 'CREATE SCHEMA IF NOT EXISTS n3_sre AUTHORIZATION aura_brain_rw';
    EXECUTE 'ALTER SCHEMA aura_core OWNER TO aura_brain_rw';
    EXECUTE 'ALTER SCHEMA n3_sre OWNER TO aura_brain_rw';
    EXECUTE 'GRANT USAGE, CREATE ON SCHEMA public TO aura_brain_rw';

    -- 4. Transfere ownership de todas as tabelas, sequencias e views em aura_core e n3_sre
    FOR r_obj IN
        SELECT schemaname, tablename
        FROM pg_tables
        WHERE schemaname IN ('aura_core', 'n3_sre')
    LOOP
        EXECUTE format('ALTER TABLE %I.%I OWNER TO aura_brain_rw', r_obj.schemaname, r_obj.tablename);
    END LOOP;

    FOR r_obj IN
        SELECT sequence_schema, sequence_name
        FROM information_schema.sequences
        WHERE sequence_schema IN ('aura_core', 'n3_sre')
    LOOP
        EXECUTE format('ALTER SEQUENCE %I.%I OWNER TO aura_brain_rw', r_obj.sequence_schema, r_obj.sequence_name);
    END LOOP;

    FOR r_obj IN
        SELECT schemaname, viewname
        FROM pg_views
        WHERE schemaname IN ('aura_core', 'n3_sre')
    LOOP
        EXECUTE format('ALTER VIEW %I.%I OWNER TO aura_brain_rw', r_obj.schemaname, r_obj.viewname);
    END LOOP;

    -- 5. Privilegios de leitura preservados para aura_service_ro no posto_ai (compatibilidade)
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'aura_service_ro') THEN
        EXECUTE 'GRANT CONNECT ON DATABASE posto_ai TO aura_service_ro';
        EXECUTE 'GRANT USAGE ON SCHEMA aura_core TO aura_service_ro';
        EXECUTE 'GRANT SELECT ON ALL TABLES IN SCHEMA aura_core TO aura_service_ro';
    END IF;
END
$$;

COMMENT ON ROLE aura_brain_rw IS 'Role proprietaria do cerebro cognitivo AURA (posto_ai / aura_core / n3_sre). Sem acesso ao ERP posto.';

SELECT 'AURA_BRAIN_PROVISIONED' AS status;
