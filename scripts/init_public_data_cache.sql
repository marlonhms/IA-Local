-- =============================================================================
-- DDL DECLARATIVO E IDEMPOTENTE: CACHE RELACIONAL DE DADOS PUBLICOS DA AURA
-- Schema: aura_core (posto_ai:5433) com views de compatibilidade em public
-- Fontes: ANP (Precos Semanais), CONFAZ (PMPF COTEPE) e BACEN (Series SGS)
-- Zero travessoes em todo o arquivo.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS aura_core;

-- 1. Precos Semanais de Combustiveis ANP
CREATE TABLE IF NOT EXISTS aura_core.anp_precos_semanais (
    id BIGSERIAL PRIMARY KEY,
    regiao VARCHAR(20),
    estado_sigla VARCHAR(2) NOT NULL,
    municipio VARCHAR(100) NOT NULL,
    revenda VARCHAR(255),
    cnpj_revenda VARCHAR(20),
    produto VARCHAR(60) NOT NULL,
    data_coleta DATE NOT NULL,
    valor_venda NUMERIC(10, 3) NOT NULL,
    unidade_medida VARCHAR(20) DEFAULT 'R$ / litro',
    bandeira VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_anp_precos_cnpj_prod_data UNIQUE (cnpj_revenda, produto, data_coleta)
);

CREATE INDEX IF NOT EXISTS idx_anp_precos_mun_prod
ON aura_core.anp_precos_semanais (municipio, produto, data_coleta DESC);

CREATE INDEX IF NOT EXISTS idx_anp_precos_uf
ON aura_core.anp_precos_semanais (estado_sigla);

-- 2. Pautas Fiscais COTEPE PMPF do CONFAZ (ICMS-ST)
CREATE TABLE IF NOT EXISTS aura_core.confaz_pmpf (
    id SERIAL PRIMARY KEY,
    uf VARCHAR(2) NOT NULL,
    produto VARCHAR(60) NOT NULL,
    valor_pauta NUMERIC(10, 4) NOT NULL,
    vigencia_inicio DATE NOT NULL,
    vigencia_fim DATE,
    ato_cotepe_num VARCHAR(50),
    data_publicacao_dou DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_confaz_pmpf_uf_prod_vig UNIQUE (uf, produto, vigencia_inicio)
);

CREATE INDEX IF NOT EXISTS idx_confaz_pmpf_uf_prod
ON aura_core.confaz_pmpf (uf, produto, vigencia_inicio DESC);

-- 3. Series Historicas Macroeconomicas do BACEN SGS
CREATE TABLE IF NOT EXISTS aura_core.bacen_series_historicas (
    id SERIAL PRIMARY KEY,
    codigo_serie INT NOT NULL,
    nome_serie VARCHAR(100) NOT NULL,
    data_referencia DATE NOT NULL,
    valor NUMERIC(14, 6) NOT NULL,
    unidade VARCHAR(30),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_bacen_series_cod_data UNIQUE (codigo_serie, data_referencia)
);

CREATE INDEX IF NOT EXISTS idx_bacen_serie_data
ON aura_core.bacen_series_historicas (codigo_serie, data_referencia DESC);

-- 4. Auditoria e Telemetria de Sincronizacao em Segundo Plano
CREATE TABLE IF NOT EXISTS aura_core.public_sync_telemetry (
    id SERIAL PRIMARY KEY,
    fonte VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    registros_processados INT NOT NULL DEFAULT 0,
    registros_inseridos INT NOT NULL DEFAULT 0,
    duracao_ms NUMERIC(10, 2) NOT NULL,
    mensagem_erro TEXT,
    executado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Views e Sinonimos em public para consulta transparente
CREATE OR REPLACE VIEW public.anp_precos_semanais AS
SELECT * FROM aura_core.anp_precos_semanais;

CREATE OR REPLACE VIEW public.confaz_pmpf AS
SELECT * FROM aura_core.confaz_pmpf;

CREATE OR REPLACE VIEW public.bacen_series_historicas AS
SELECT * FROM aura_core.bacen_series_historicas;

CREATE OR REPLACE VIEW public.public_sync_telemetry AS
SELECT * FROM aura_core.public_sync_telemetry;
