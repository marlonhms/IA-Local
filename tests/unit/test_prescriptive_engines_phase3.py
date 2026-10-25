"""
Suíte de Testes Unitários dos 4 Novos Motores Cognitivos Prescritivos (Fase 3).
Cobre:
1. Motor 1: Auditor de Erosão Financeira, Taxas TEF/Pagamentos e Arbitragem Selic (auditar_erosao_financeira_e_recebiveis)
2. Motor 2: Caçador de Capital Morto (Selic) e Ruptura Invisível de Gôndola (diagnosticar_capital_morto_e_ruptura_invisivel)
3. Motor 3: Raio-X de Sangria de Margem - Decomposição Causal Waterfall (diagnosticar_variacao_margem_causal)
4. Motor 4: Simulador de Elasticidade Dinâmica e Otimizador de Lote de Compra (simular_elasticidade_e_lote_compra)
5. Integração com AuraEngine (execute_tool_direct e síntese de contingência)
6. Validação estrita de ausência de travessões Unicode (\\u2014, \\u2013).
"""
import pytest

from core.tools import PostoTools
from core.schemas.genui import (
    FinancialErosionProps,
    DeadCapitalOpportunityProps,
    MarginWaterfallProps,
    ElasticityBatchSimulatorProps,
)


@pytest.fixture
def tools():
    """Instância do PostoTools com mock de dependências externas para testes herméticos."""
    t = PostoTools()
    return t


# =============================================================================
# MOTOR 1: AUDITOR DE EROSÃO FINANCEIRA & ARBITRAGEM SELIC
# =============================================================================

def test_auditar_erosao_financeira_e_recebiveis_padrao(tools):
    """Testa execução padrão do Motor 1 validando contratos, VPL e divergência de taxas."""
    res = tools.auditar_erosao_financeira_e_recebiveis()
    assert res["status"] == "ok"
    assert res["client_component"] == "FinancialErosionUI"
    assert res["total_vendas_reais"] > 0
    assert res["total_divergencia_taxas_reais"] >= 0
    assert res["total_custo_carregamento_selic_reais"] >= 0
    assert res["taxa_selic_anual_pct"] > 0
    assert len(res["modalidades"]) == 6

    # Validação do contrato Pydantic v2
    props = FinancialErosionProps(**res["props"])
    assert props.confidence_score >= 0.90
    assert len(props.suggested_actions) == 3
    assert props.necessidade_caixa_72h_reais > 0


def test_auditar_erosao_financeira_custom_params(tools):
    """Testa o Motor 1 com taxas contratadas personalizadas e necessidade de caixa específica."""
    custom_rates = {"pix": 0.0, "debito": 1.0, "credito_vista": 2.0}
    custom_prazos = {"pix": 0, "debito": 1, "credito_vista": 15}
    res = tools.auditar_erosao_financeira_e_recebiveis(
        taxas_contratadas_custom=custom_rates,
        prazo_liquidacao_dias_custom=custom_prazos,
        necessidade_caixa_72h=120000.0,
        taxa_antecipacao_mensal_custom=2.5,
    )
    assert res["status"] == "ok"
    assert res["necessidade_caixa_72h_reais"] == 120000.0
    assert "PIX" in res["estrategia_cobertura_otima"]
    assert len(res["acoes_prescritivas"]) >= 2


# =============================================================================
# MOTOR 2: CAÇADOR DE CAPITAL MORTO & RUPTURA INVISÍVEL DE GÔNDOLA
# =============================================================================

def test_diagnosticar_capital_morto_e_ruptura_invisivel_padrao(tools):
    """Testa execução do Motor 2 verificando corrosão Selic de capital morto e itens em ruptura fantasma."""
    res = tools.diagnosticar_capital_morto_e_ruptura_invisivel(dias_sem_giro_corte=30)
    assert res["status"] == "ok"
    assert res["client_component"] == "DeadCapitalOpportunityUI"
    assert res["total_capital_morto_imobilizado_reais"] > 0
    assert res["total_custo_selic_acumulado_reais"] > 0
    assert len(res["itens_capital_morto"]) >= 1
    assert len(res["itens_ruptura_fantasma"]) >= 1

    # Verifica pareamento Apriori com Lift >= 2.0
    for it in res["itens_capital_morto"]:
        if it.get("combo_apriori_sugerido"):
            assert it["combo_apriori_sugerido"]["apriori_lift"] >= 2.0
            assert it["combo_apriori_sugerido"]["desconto_sugerido_pct"] > 0

    # Validação do contrato Pydantic v2
    props = DeadCapitalOpportunityProps(**res["props"])
    assert props.confidence_score >= 0.90
    assert len(props.suggested_actions) == 3


def test_diagnosticar_capital_morto_filtro_dias_estrito(tools):
    """Testa filtro de corte temporal para capital morto (ex: apenas itens sem giro >= 50 dias)."""
    res = tools.diagnosticar_capital_morto_e_ruptura_invisivel(dias_sem_giro_corte=50)
    assert res["status"] == "ok"
    # Apenas itens com dias >= 50 devem constar
    for it in res["itens_capital_morto"]:
        assert it["dias_sem_giro"] >= 50


# =============================================================================
# MOTOR 3: RAIO-X DE SANGRIA DE MARGEM (WATERFALL CAUSAL)
# =============================================================================

def test_diagnosticar_variacao_margem_causal_padrao(tools):
    """Testa a prova matemática determinística da decomposição causal Waterfall."""
    res = tools.diagnosticar_variacao_margem_causal()
    assert res["status"] == "ok"
    assert res["client_component"] == "MarginWaterfallUI"

    m_ini = res["margem_inicial_reais"]
    m_fim = res["margem_final_reais"]
    d_tot = res["delta_margem_total_reais"]
    ef_rep = res["efeito_custo_reposicao_reais"]
    ef_mix = res["efeito_mix_conversao_reais"]
    ef_vol = res["efeito_volume_puro_reais"]
    ef_perd = res["efeito_perdas_descontos_reais"]

    # Prova matemática exata da decomposição
    assert round(ef_rep + ef_mix + ef_vol + ef_perd, 2) == d_tot
    assert round(m_ini + d_tot, 2) == m_fim

    # Validação das etapas da cascata
    steps = res["steps"]
    assert len(steps) == 6
    assert steps[0]["category"] == "start"
    assert steps[-1]["category"] == "end"

    # Validação do contrato Pydantic v2
    props = MarginWaterfallProps(**res["props"])
    assert props.confidence_score >= 0.90
    assert len(props.suggested_actions) == 3


def test_diagnosticar_variacao_margem_causal_custom_dados(tools):
    """Testa o Motor 3 com dados customizados e valida o fechamento exato dos efeitos."""
    dados_custom = {
        "margem_inicial_reais": 100000.0,
        "efeito_custo_reposicao_reais": -5000.0,
        "efeito_mix_conversao_reais": -2000.0,
        "efeito_volume_puro_reais": 1500.0,
        "efeito_perdas_descontos_reais": -500.0,
        "horas_defasagem_preco_medio": 24.0,
    }
    res = tools.diagnosticar_variacao_margem_causal(dados_custom=dados_custom)
    assert res["status"] == "ok"
    assert res["delta_margem_total_reais"] == -6000.0
    assert res["margem_final_reais"] == 94000.0


# =============================================================================
# MOTOR 4: SIMULADOR DE ELASTICIDADE DINÂMICA & OTIMIZADOR DE LOTE
# =============================================================================

def test_simular_elasticidade_e_lote_compra_padrao(tools):
    """Testa simulação de elasticidade com Ullage insuficiente para lote de carreta."""
    res = tools.simular_elasticidade_e_lote_compra(
        produto="GASOLINA COMUM",
        municipio="CAMPINAS",
        tanque_capacidade_litros=20000.0,
        estoque_atual_litros=16800.0,
        lote_minimo_litros=5000.0,
        desconto_lote_reais_litro=0.08,
    )
    assert res["status"] == "ok"
    assert res["client_component"] == "ElasticityBatchSimulatorUI"
    assert res["espaco_livre_ullage_litros"] == 3200.0
    assert res["capacidade_recebimento_imediata"] is False
    assert res["litros_faltantes_para_lote"] == 1800.0
    assert res["economia_potencial_lote_reais"] == 400.0

    # Validação dos cenários simulados
    cenarios = res["cenarios"]
    assert len(cenarios) == 3
    # O cenário WhatsApp deve ser o recomendado por viabilizar o lote antes do fim de semana
    assert cenarios[2]["viavel"] is True
    assert cenarios[2]["resultado_liquido_reais"] > 0

    # Validação do contrato Pydantic v2
    props = ElasticityBatchSimulatorProps(**res["props"])
    assert props.confidence_score >= 0.90
    assert len(props.suggested_actions) == 3


def test_simular_elasticidade_com_ullage_suficiente(tools):
    """Testa caso em que o tanque já tem espaço livre suficiente (Ullage >= Lote Mínimo)."""
    res = tools.simular_elasticidade_e_lote_compra(
        produto="DIESEL S10",
        tanque_capacidade_litros=30000.0,
        estoque_atual_litros=12000.0, # Ullage = 18.000 L >= 5.000 L
        lote_minimo_litros=5000.0,
    )
    assert res["status"] == "ok"
    assert res["capacidade_recebimento_imediata"] is True
    assert res["litros_faltantes_para_lote"] == 0.0


# =============================================================================
# INTEGRAÇÃO COM AURA ENGINE
# =============================================================================

@pytest.mark.asyncio
async def test_aura_engine_execute_tool_direct_fase3():
    """Testa o despacho de todas as 4 novas ferramentas via AuraEngine.execute_tool_direct."""
    from core.aura_engine import AuraEngine

    engine = AuraEngine()

    ferramentas_teste = [
        ("auditar_erosao_financeira_e_recebiveis", {}),
        ("diagnosticar_capital_morto_e_ruptura_invisivel", {}),
        ("diagnosticar_variacao_margem_causal", {}),
        ("simular_elasticidade_e_lote_compra", {"produto": "GASOLINA COMUM"}),
    ]

    for tool_name, params in ferramentas_teste:
        res = await engine.execute_tool_direct(tool_name, params)
        assert res["status"] == "success", f"Falha ao executar ferramenta {tool_name}: {res}"
        assert res["data"]["status"] == "ok"
        assert "props" in res["data"]


def test_aura_engine_contingency_synthesis_fase3():
    """Testa a geração de síntese determinística de contingência para os 4 novos motores."""
    from core.aura_engine import AuraEngine

    engine = AuraEngine()
    tools = PostoTools()

    # 1. Erosão
    r1 = tools.auditar_erosao_financeira_e_recebiveis()
    s1 = engine._gerar_sintese_contingencia_ferramenta("auditar_erosao_financeira_e_recebiveis", r1, "erosao")
    assert s1 is not None
    assert "Auditoria de Erosao Financeira" in s1

    # 2. Capital Morto
    r2 = tools.diagnosticar_capital_morto_e_ruptura_invisivel()
    s2 = engine._gerar_sintese_contingencia_ferramenta("diagnosticar_capital_morto_e_ruptura_invisivel", r2, "capital morto")
    assert s2 is not None
    assert "Cacador de Capital Morto" in s2

    # 3. Waterfall Margem
    r3 = tools.diagnosticar_variacao_margem_causal()
    s3 = engine._gerar_sintese_contingencia_ferramenta("diagnosticar_variacao_margem_causal", r3, "margem")
    assert s3 is not None
    assert "Raio-X de Sangria de Margem" in s3

    # 4. Elasticidade Lote
    r4 = tools.simular_elasticidade_e_lote_compra()
    s4 = engine._gerar_sintese_contingencia_ferramenta("simular_elasticidade_e_lote_compra", r4, "lote")
    assert s4 is not None
    assert "Simulador de Elasticidade" in s4


# =============================================================================
# BLINDAGEM DE TRAVESSÕES
# =============================================================================

def test_ausencia_travessoes_motores_fase3():
    """Garante que nenhum travessão Unicode (\\u2014, \\u2013) foi introduzido nos arquivos da Fase 3."""
    import pathlib

    arquivos = [
        pathlib.Path("core/tools.py"),
        pathlib.Path("core/schemas/genui.py"),
        pathlib.Path("core/aura_engine.py"),
        pathlib.Path(__file__),
    ]

    for arq in arquivos:
        texto = arq.read_text(encoding="utf-8")
        assert "\u2014" not in texto, f"Travessao em-dash (\\u2014) detectado em {arq.name}"
        assert "\u2013" not in texto, f"Travessao en-dash (\\u2013) detectado em {arq.name}"
