-- =============================================================================
-- AURA - Change Data Capture (CDC) Orientado a Eventos via LISTEN / NOTIFY (P2-2)
-- =============================================================================
-- AVISO DE GOVERNANCA E CLEAN ROOM (OPT-IN ESTRITO):
-- 1. Por padrao, a AURA opera em regime 100% Read-Only no ERP usando a role
--    tecnica 'aura_service_ro' (zero escrita, zero triggers, zero objetos DDL).
-- 2. Este script e ESTRITAMENTE OPCIONAL (Opt-In) e destina-se apenas a
--    ambientes autorizados pelo administrador do banco ou em bases espelho/replica
--    onde deseja-se substituir o polling de 4 horas por notificacoes sub-segundo.
-- 3. Caso este script NAO seja aplicado no banco, o daemon 'scripts/sync_daemon.py'
--    opera automaticamente em modo fallback de polling seguro sem erros.
-- Zero travessoes em todo o arquivo.
-- =============================================================================

CREATE OR REPLACE FUNCTION public.notify_aura_cdc_change()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_record RECORD;
    v_codpro TEXT := '';
    v_nompro TEXT := '';
    v_preco NUMERIC := 0;
    v_payload JSONB;
BEGIN
    IF (TG_OP = 'DELETE') THEN
        v_record := OLD;
    ELSE
        v_record := NEW;
    END IF;

    IF (TG_TABLE_NAME = 'produtos') THEN
        v_codpro := COALESCE(TRIM(v_record.codpro::text), '');
        v_nompro := COALESCE(TRIM(v_record.nompro::text), '');
        v_preco := COALESCE(v_record.valvenda, 0);
    ELSIF (TG_TABLE_NAME = 'grupos') THEN
        v_codpro := COALESCE(TRIM(v_record.codi::text), '');
        v_nompro := COALESCE(TRIM(v_record.grupo::text), '');
    END IF;

    v_payload := jsonb_build_object(
        'channel', 'aura_cdc_channel',
        'table', TG_TABLE_NAME,
        'operation', TG_OP,
        'codpro', v_codpro,
        'nompro', v_nompro,
        'preco', v_preco,
        'timestamp', to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
    );

    PERFORM pg_notify('aura_cdc_channel', v_payload::text);
    RETURN v_record;
END;
$$;

-- Criacao idempotente do trigger opcional na tabela public.produtos
DROP TRIGGER IF EXISTS trg_aura_cdc_produtos ON public.produtos;
CREATE TRIGGER trg_aura_cdc_produtos
AFTER INSERT OR UPDATE OR DELETE ON public.produtos
FOR EACH ROW
EXECUTE FUNCTION public.notify_aura_cdc_change();

-- Criacao idempotente do trigger opcional na tabela public.grupos
DROP TRIGGER IF EXISTS trg_aura_cdc_grupos ON public.grupos;
CREATE TRIGGER trg_aura_cdc_grupos
AFTER INSERT OR UPDATE OR DELETE ON public.grupos
FOR EACH ROW
EXECUTE FUNCTION public.notify_aura_cdc_change();

-- =============================================================================
-- REVERSAO (ROLLBACK LIMPO):
-- Para remover os triggers opcionais e retornar ao modo 100% Read-Only puro:
-- DROP TRIGGER IF EXISTS trg_aura_cdc_produtos ON public.produtos;
-- DROP TRIGGER IF EXISTS trg_aura_cdc_grupos ON public.grupos;
-- DROP FUNCTION IF EXISTS public.notify_aura_cdc_change();
-- =============================================================================
