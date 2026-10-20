"""
Suite Unificada de Testes - Ferramentas Cognitivas Publicas (Fase 4 / Pilar 5)

Testa a integracao cognitiva de dados publicos da ANP, BACEN e CONFAZ:
1. Enriquecimento de PostoTools.comparar_benchmark_concorrencia com estatisticas ANP e quartis
2. Auditoria volumetrica PostoTools.auditar_conformidade_lmc_anp (Portaria ANP 26/1992)
3. Analise macroeconomica PostoTools.analisar_custo_estoque_macroeconomico (BACEN Selic, PTAX e PMPF CONFAZ)
4. Despacho direto via AuraEngine.execute_tool_direct
5. Envelopes canonicos GenUI (render_LMCComplianceReportUI e render_MacroeconomicInventoryCostUI)
6. Sintese executiva de contingencia deterministica
7. Classificacao semantica e heuristica em SemanticRouter
8. Auditoria estrita de zero em-dash e en-dash
"""

from unittest.mock import MagicMock, patch

import pytest

from core.aura_engine import (
    GENUI_COMPONENT_REGISTRY_MAP,
    AuraEngine,
    build_canonical_genui_envelope,
)
from core.integrations.public_data.repository import PublicDataRepository
from core.schemas.genui import (
    BenchmarkComparisonProps,
    GenUIEnvelope,
    LMCComplianceProps,
    MacroeconomicInventoryCostProps,
)
from core.schemas.idempotency import generate_tool_call_id
from core.semantic_router import INTENT_EXEMPLARS, classificar_intencao_heuristica
from core.tools import PostoTools

# =============================================================================
# 1. TESTES DE BENCHMARK COM ESTATISTICAS ANP & QUARTIS
# =============================================================================

def test_comparar_benchmark_concorrencia_com_cache_anp():
    """Valida calculo de quartis e indicadores ANP quando ha registros em cache."""
    mock_repo = MagicMock(spec=PublicDataRepository)
    mock_repo.get_preco_benchmark_anp.return_value = {
        "preco_medio": 5.85,
        "preco_minimo": 5.69,
        "preco_maximo": 6.09,
        "preco_mediana": 5.84,
        "quartil_1": 5.75,
        "quartil_3": 5.95,
        "total_amostras": 12,
        "postos_amostrados": 12,
        "data_ultima_coleta": "2026-10-15",
    }

    tools = PostoTools(rag_engine=None, public_data_repo=mock_repo)
    resultado = tools.comparar_benchmark_concorrencia(
        filial_nome="Posto Modelo Campinas",
    )

    assert resultado["status"] == "ok"
    assert resultado["component_name"] == "render_BenchmarkComparisonUI"
    assert resultado["client_component"] == "BenchmarkComparisonUI"
    assert resultado["fonte_dados"] == "ANP_CACHE_LOCAL"
    assert "anp_stats" in resultado

    anp_stats = resultado["anp_stats"]
    assert "gasolina_comum" in anp_stats
    gc_stats = anp_stats["gasolina_comum"]
    assert gc_stats["preco_medio"] == 5.85
    assert gc_stats["preco_minimo"] == 5.69
    assert gc_stats["preco_maximo"] == 6.09
    assert gc_stats["preco_mediana"] == 5.84
    assert gc_stats["quartil_1"] == 5.75
    assert gc_stats["quartil_3"] == 5.95
    assert gc_stats["postos_amostrados"] == 12

    # Verifica validacao do schema Pydantic BenchmarkComparisonProps
    props = resultado["props"]
    props_obj = BenchmarkComparisonProps(**props)
    assert props_obj.competitiveness_score >= 0.0
    assert "ANP" in props_obj.benchmark_group or "Média" in props_obj.benchmark_group


def test_comparar_benchmark_concorrencia_fallback_sem_anp():
    """Valida resiliencia quando repositorio publico nao possui dados ANP da regiao."""
    mock_repo = MagicMock(spec=PublicDataRepository)
    mock_repo.get_preco_benchmark_anp.return_value = {}

    tools = PostoTools(rag_engine=None, public_data_repo=mock_repo)
    resultado = tools.comparar_benchmark_concorrencia()

    assert resultado["status"] == "ok"
    assert resultado["component_name"] == "render_BenchmarkComparisonUI"
    assert "props" in resultado
    assert len(resultado["props"]["comparison_items"]) > 0


# =============================================================================
# 2. TESTES DE AUDITORIA DE CONFORMIDADE LMC ANP (PORTARIA 26/1992)
# =============================================================================

def test_auditar_conformidade_lmc_anp_conforme():
    """Valida auditoria quando variacao volumetrica esta dentro de +-0.60%."""
    tools = PostoTools(rag_engine=None)
    resultado = tools.auditar_conformidade_lmc_anp(data="2026-09-02")

    assert resultado["status"] == "ok"
    assert resultado["component_name"] == "render_LMCComplianceReportUI"
    assert resultado["client_component"] == "LMCComplianceReportUI"
    assert resultado["tolerancia_legal_pct"] == 0.60
    assert "status_conformidade" in resultado
    assert "props" in resultado

    props = resultado["props"]
    # Valida conformidade estrita contra schema Pydantic LMCComplianceProps
    props_obj = LMCComplianceProps(**props)
    assert props_obj.tolerancia_legal_pct == 0.60
    assert len(props_obj.suggested_actions) == 3

    # Verifica acoes interativas HITL
    action_types = [a.action_type for a in props_obj.suggested_actions]
    assert "inspection" in action_types
    assert "mutation" in action_types


def test_auditar_conformidade_lmc_anp_critico():
    """Valida diagnostico de tanque critico violando limite de +-0.60%."""
    tools = PostoTools(rag_engine=None)
    mock_lmc = {
        "status": "ok",
        "periodo_analisado": {"data_lmc": "2026-10-15"},
        "resumo_executivo": {
            "total_vendas_litros": 5000.0,
            "total_recebimentos_litros": 8000.0,
            "total_estoque_escriturado_litros": 15000.0,
            "total_estoque_fisico_litros": 14920.0,
        },
        "tanques": [
            {
                "tanque": "001",
                "combustivel": "GASOLINA COMUM",
                "capacidade_litros": 30000.0,
                "estoque_abertura": 12000.0,
                "recebimento": 8000.0,
                "vendas": 5000.0,
                "estoque_escriturado": 15000.0,
                "estoque_fisico": 14920.0,  # -80L em 5000L = -1.60%
            }
        ],
    }

    with patch.object(tools, "gerar_relatorio_lmc_anp", return_value=mock_lmc):
        resultado = tools.auditar_conformidade_lmc_anp(data="2026-10-15")

    assert resultado["status"] == "ok"
    assert resultado["status_conformidade"] == "CRITICO"
    assert len(resultado["tanques_criticos"]) >= 1

    critico = resultado["tanques_criticos"][0]
    assert critico["tanque"] == "001"
    assert critico["variacao_pct"] == -1.60
    assert "excede o limite" in critico["diagnostico"].lower()


# =============================================================================
# 3. TESTES DE ANALISE MACROECONOMICA DE CUSTO DE ESTOQUE (BACEN & CONFAZ)
# =============================================================================

def test_analisar_custo_estoque_macroeconomico_calculo_selic_e_pmpf():
    """Valida calculo exato do custo de oportunidade com Selic 252 d.u. e spread PMPF."""
    mock_repo = MagicMock(spec=PublicDataRepository)
    mock_repo.get_indicadores_economicos_recentes.return_value = {
        "selic_diaria_aa": 11.25,
        "data_referencia_selic": "2026-10-15",
        "ptax_dolar_venda": 5.60,
        "data_referencia_ptax": "2026-10-15",
    }
    mock_repo.get_pmpf_atual.return_value = {
        "valor_pauta": 6.20,
        "ato_cotepe_num": "Ato COTEPE/PMPF nº 20/2026",
        "vigencia_inicio": "2026-10-01",
    }

    tools = PostoTools(rag_engine=None, public_data_repo=mock_repo)
    resultado = tools.analisar_custo_estoque_macroeconomico(
        produto="GASOLINA COMUM",
        uf="SP",
        volume_total_litros=40000.0,
        custo_medio_litro=5.20,
    )

    assert resultado["status"] == "ok"
    assert resultado["component_name"] == "render_MacroeconomicInventoryCostUI"
    assert resultado["client_component"] == "MacroeconomicInventoryCostUI"

    props = resultado["props"]
    # Capital imobilizado = 40.000L * R$ 5,20 = R$ 208.000,00
    assert props["capital_imobilizado_reais"] == 208000.0
    assert props["taxa_selic_anual_pct"] == 11.25
    assert props["taxa_cambio_ptax"] == 5.60

    # Custo diario = 208.000 * (0.1125 / 252) = 92.86
    custo_dia_esperado = round(208000.0 * (0.1125 / 252.0), 2)
    assert props["custo_diario_carregamento_reais"] == custo_dia_esperado

    # Custo mensal = custo_dia * 21 dias uteis = 1950.06
    custo_mes_esperado = round(custo_dia_esperado * 21.0, 2)
    assert props["custo_mensal_carregamento_reais"] == custo_mes_esperado

    # Spread PMPF = 6.20 - 5.20 = 1.00
    assert props["pmpf_vigente_reais"] == 6.20
    assert props["spread_pmpf_reais"] == 1.00
    assert props["spread_pmpf_pct"] == round((1.00 / 5.20) * 100, 2)
    assert props["ato_cotepe"] == "Ato COTEPE/PMPF nº 20/2026"

    # Valida schema Pydantic MacroeconomicInventoryCostProps
    props_obj = MacroeconomicInventoryCostProps(**props)
    assert len(props_obj.suggested_actions) == 3


# =============================================================================
# 4. TESTES DE DESPACHO DIRETO VIA AURA ENGINE (execute_tool_direct)
# =============================================================================

@pytest.mark.asyncio
async def test_aura_engine_execute_tool_direct_novas_ferramentas():
    """Valida que execute_tool_direct executa e retorna status success para as novas ferramentas."""
    mock_tools = MagicMock()
    mock_tools.auditar_conformidade_lmc_anp.return_value = {
        "status": "ok",
        "status_conformidade": "CONFORME",
        "component_name": "render_LMCComplianceReportUI",
    }
    mock_tools.analisar_custo_estoque_macroeconomico.return_value = {
        "status": "ok",
        "component_name": "render_MacroeconomicInventoryCostUI",
    }

    engine = AuraEngine(tools=mock_tools)

    res_lmc = await engine.execute_tool_direct("auditar_conformidade_lmc_anp", {"data": "2026-09-02"})
    assert res_lmc["status"] == "success"
    assert res_lmc["tool_name"] == "auditar_conformidade_lmc_anp"
    assert res_lmc["data"]["component_name"] == "render_LMCComplianceReportUI"

    res_macro = await engine.execute_tool_direct("analisar_custo_estoque_macroeconomico", {"produto": "GASOLINA COMUM"})
    assert res_macro["status"] == "success"
    assert res_macro["tool_name"] == "analisar_custo_estoque_macroeconomico"
    assert res_macro["data"]["component_name"] == "render_MacroeconomicInventoryCostUI"


@pytest.mark.asyncio
async def test_aura_engine_execute_tool_direct_real_posto_tools():
    """Valida que execute_tool_direct com PostoTools real não falha com TypeError por argumentos incompativeis."""
    real_tools = PostoTools(rag_engine=None)
    engine = AuraEngine(tools=real_tools)

    res = await engine.execute_tool_direct(
        "auditar_conformidade_lmc_anp",
        {"data": "2026-09-02", "combustivel": "GASOLINA COMUM", "tanque": "001"}
    )
    assert res["status"] == "success"
    assert res["data"]["status"] == "ok"
    assert res["data"]["component_name"] == "render_LMCComplianceReportUI"


# =============================================================================
# 5. TESTES DE CONSTRUCAO DO ENVELOPE CANONICO GENUI
# =============================================================================

def test_build_canonical_genui_envelope_lmc_compliance():
    """Valida envelope canônico para render_LMCComplianceReportUI."""
    dados_lmc = {
        "status": "ok",
        "diagnosis": "LMC auditado e conforme margem legal da ANP.",
        "status_conformidade": "CONFORME",
        "variacao_volumetrica_pct": 0.15,
        "tolerancia_legal_pct": 0.60,
        "total_vendas_litros": 18000.0,
        "total_recebimentos_litros": 15000.0,
        "total_estoque_contabil_litros": 22000.0,
        "total_estoque_fisico_litros": 22027.0,
        "total_variacao_litros": 27.0,
        "parecer_regulatorio": "Tanques operando dentro da variacao regulamentar.",
    }

    envelope = build_canonical_genui_envelope(
        intencao="auditar_conformidade_lmc_anp",
        tool_call_id=generate_tool_call_id(),
        resultado_bruto=dados_lmc,
        executive_summary="Resumo de conformidade volumetrica LMC.",
    )

    assert envelope is not None
    assert isinstance(envelope, GenUIEnvelope)
    assert envelope.component_name == "render_LMCComplianceReportUI"
    assert envelope.client_component == "LMCComplianceReportUI"
    assert envelope.intent == "auditar_conformidade_lmc_anp"
    assert len(envelope.actions) >= 1
    assert envelope.props["tolerancia_legal_pct"] == 0.60


def test_build_canonical_genui_envelope_macroeconomic_inventory():
    """Valida envelope canônico para render_MacroeconomicInventoryCostUI."""
    dados_macro = {
        "status": "ok",
        "diagnosis": "Custo de carregamento calculado com taxa Selic oficial.",
        "volume_total_litros": 35000.0,
        "custo_medio_litro": 5.15,
        "capital_imobilizado_reais": 180250.0,
        "taxa_selic_anual_pct": 11.25,
        "taxa_cambio_ptax": 5.58,
        "custo_diario_carregamento_reais": 80.47,
        "custo_mensal_carregamento_reais": 1689.87,
        "uf_referencia": "SP",
        "produto_referencia": "GASOLINA COMUM",
        "pmpf_vigente_reais": 6.15,
        "spread_pmpf_reais": 1.00,
        "spread_pmpf_pct": 19.42,
        "recomendacao_compra": "Giro acelerado: priorizar carreta fechada.",
    }

    envelope = build_canonical_genui_envelope(
        intencao="custo_estoque_macro",
        tool_call_id=generate_tool_call_id(),
        resultado_bruto=dados_macro,
        executive_summary="Resumo executivo de custo macroeconomico.",
    )

    assert envelope is not None
    assert isinstance(envelope, GenUIEnvelope)
    assert envelope.component_name == "render_MacroeconomicInventoryCostUI"
    assert envelope.client_component == "MacroeconomicInventoryCostUI"
    assert envelope.intent == "custo_estoque_macro"
    assert len(envelope.actions) >= 1
    assert envelope.props["capital_imobilizado_reais"] == 180250.0


# =============================================================================
# 6. TESTES DE SINTESE EXECUTIVA DE CONTINGENCIA (FALLBACK DETERMINISTICO)
# =============================================================================

def test_sintese_contingencia_ferramenta_lmc_e_macro():
    """Valida que sintese de contingencia produz texto rico sem dependencia do LLM."""
    engine = AuraEngine()

    lmc_data = {
        "status": "ok",
        "status_conformidade": "CONFORME",
        "diagnosis": "Conformidade volumetrica verificada.",
        "total_vendas_litros": 20000.0,
        "total_variacao_litros": 35.0,
        "variacao_volumetrica_pct": 0.175,
        "parecer_regulatorio": "Tanques operando normalmente.",
    }
    sintese_lmc = engine._gerar_sintese_contingencia_ferramenta(
        intencao="auditar_conformidade_lmc_anp",
        resultado_bruto=lmc_data,
        pergunta="auditar conformidade do lmc",
    )
    assert sintese_lmc is not None
    assert "Auditoria de Conformidade LMC ANP" in sintese_lmc
    assert "CONFORME ANP" in sintese_lmc
    assert "+-0.60%" in sintese_lmc

    macro_data = {
        "status": "ok",
        "diagnosis": "Custo de carregamento projetado.",
        "volume_total_litros": 40000.0,
        "custo_medio_litro": 5.25,
        "capital_imobilizado_reais": 210000.0,
        "taxa_selic_anual_pct": 11.25,
        "taxa_cambio_ptax": 5.62,
        "custo_diario_carregamento_reais": 93.75,
        "custo_mensal_carregamento_reais": 1968.75,
        "pmpf_vigente_reais": 6.18,
        "spread_pmpf_reais": 0.93,
        "spread_pmpf_pct": 17.7,
        "recomendacao_compra": "Manter programacao regular de carretas.",
    }
    sintese_macro = engine._gerar_sintese_contingencia_ferramenta(
        intencao="custo_estoque_macro",
        resultado_bruto=macro_data,
        pergunta="custo de carregamento do estoque",
    )
    assert sintese_macro is not None
    assert "Analise Macroeconomica de Custo de Estoque" in sintese_macro
    assert "R$ 210.000,00" in sintese_macro
    assert "11.25% a.a." in sintese_macro


# =============================================================================
# 7. TESTES DE CLASSIFICACAO SEMANTICA E HEURISTICA (SemanticRouter)
# =============================================================================

def test_classificacao_heuristica_novas_intencoes():
    """Valida roteamento correto das novas intencoes e retrocompatibilidade com lmc_anp."""
    # Novas intencoes de compliance volumetrico
    assert classificar_intencao_heuristica("auditar conformidade do lmc") == "auditar_conformidade_lmc_anp"
    assert classificar_intencao_heuristica("auditoria de conformidade lmc") == "auditar_conformidade_lmc_anp"
    assert classificar_intencao_heuristica("auditar conformidade anp") == "auditar_conformidade_lmc_anp"
    assert classificar_intencao_heuristica("lmc compliance") == "auditar_conformidade_lmc_anp"

    # Novas intencoes macroeconomicas
    assert classificar_intencao_heuristica("qual o custo de carregamento do estoque?") == "custo_estoque_macro"
    assert classificar_intencao_heuristica("quanto custa manter o estoque parado com a taxa selic?") == "custo_estoque_macro"
    assert classificar_intencao_heuristica("capital imobilizado nos tanques") == "custo_estoque_macro"
    assert classificar_intencao_heuristica("pauta fiscal pmpf do confaz") == "custo_estoque_macro"
    assert classificar_intencao_heuristica("custo financeiro do estoque") == "custo_estoque_macro"

    # Retrocompatibilidade com intencoes canonicas existentes
    assert classificar_intencao_heuristica("gerar relatorio do lmc da anp") == "lmc_anp"
    assert classificar_intencao_heuristica("como esta o lmc de hoje?") == "lmc_anp"
    assert classificar_intencao_heuristica("relatorio do livro de movimentacao de combustiveis") == "lmc_anp"


def test_catalogo_exemplars_contem_custo_estoque_macro():
    """Valida registro formal da nova intencao em INTENT_EXEMPLARS."""
    assert "custo_estoque_macro" in INTENT_EXEMPLARS
    exemplos = INTENT_EXEMPLARS["custo_estoque_macro"]["exemplos"]
    assert len(exemplos) >= 10
    assert any("selic" in e.lower() for e in exemplos)
    assert any("pmpf" in e.lower() for e in exemplos)


def test_catalogo_exemplars_contem_auditar_conformidade_lmc_anp():
    """Valida registro formal de auditar_conformidade_lmc_anp em INTENT_EXEMPLARS."""
    assert "auditar_conformidade_lmc_anp" in INTENT_EXEMPLARS
    exemplos = INTENT_EXEMPLARS["auditar_conformidade_lmc_anp"]["exemplos"]
    assert len(exemplos) >= 10
    assert any("lmc" in e.lower() for e in exemplos)
    assert any("tolerância" in e.lower() or "tolerancia" in e.lower() or "0.6" in e for e in exemplos)


def test_classificacao_heuristica_edge_cases():
    """Valida que frases comuns de pista e gestao financeira roteiam com precisao."""
    # Edge cases LMC / tolerancia regulamentar
    assert classificar_intencao_heuristica("perda de 0.60% nos tanques") == "auditar_conformidade_lmc_anp"
    assert classificar_intencao_heuristica("tolerância de 0,60%") == "auditar_conformidade_lmc_anp"
    assert classificar_intencao_heuristica("tolerancia anp") == "auditar_conformidade_lmc_anp"
    assert classificar_intencao_heuristica("auditoria lmc") == "auditar_conformidade_lmc_anp"
    assert classificar_intencao_heuristica("perda 060") == "auditar_conformidade_lmc_anp"

    # Edge cases Macro / CONFAZ / BACEN
    assert classificar_intencao_heuristica("pauta confaz da gasolina") == "custo_estoque_macro"
    assert classificar_intencao_heuristica("indicadores macro do posto") == "custo_estoque_macro"
    assert classificar_intencao_heuristica("pauta icms-st de sp") == "custo_estoque_macro"
    assert classificar_intencao_heuristica("pmpf confaz do diesel") == "custo_estoque_macro"
    assert classificar_intencao_heuristica("custo estoque selic") == "custo_estoque_macro"


def test_genui_component_registry_map_lmc_anp_mapping():
    """Garante mapeamento de lmc_anp, auditar_conformidade_lmc_anp e custo_estoque_macro no catalogo GenUI."""
    assert "lmc_anp" in GENUI_COMPONENT_REGISTRY_MAP
    assert GENUI_COMPONENT_REGISTRY_MAP["lmc_anp"]["component_name"] == "render_LMCComplianceReportUI"
    assert GENUI_COMPONENT_REGISTRY_MAP["lmc_anp"]["client_component"] == "LMCComplianceReportUI"

    assert "auditar_conformidade_lmc_anp" in GENUI_COMPONENT_REGISTRY_MAP
    assert GENUI_COMPONENT_REGISTRY_MAP["auditar_conformidade_lmc_anp"]["component_name"] == "render_LMCComplianceReportUI"

    assert "custo_estoque_macro" in GENUI_COMPONENT_REGISTRY_MAP
    assert GENUI_COMPONENT_REGISTRY_MAP["custo_estoque_macro"]["component_name"] == "render_MacroeconomicInventoryCostUI"


def test_comparar_benchmark_concorrencia_produto_priorizado():
    """Valida que o parametro produto e priorizado na consulta de benchmark da ANP."""
    mock_repo = MagicMock(spec=PublicDataRepository)
    mock_repo.get_preco_benchmark_anp.return_value = {
        "preco_medio": 3.90,
        "preco_minimo": 3.75,
        "preco_maximo": 4.10,
        "preco_mediana": 3.88,
        "quartil_1": 3.80,
        "quartil_3": 3.98,
        "total_amostras": 8,
        "postos_amostrados": 8,
        "data_ultima_coleta": "2026-10-15",
    }

    tools = PostoTools(rag_engine=None, public_data_repo=mock_repo)
    resultado = tools.comparar_benchmark_concorrencia(
        filial_nome="Posto Modelo Campinas",
        municipio="CAMPINAS",
        produto="ETANOL",
    )
    assert resultado["status"] == "ok"
    assert resultado["component_name"] == "render_BenchmarkComparisonUI"
    # Repo deve ter sido chamado com ETANOL
    mock_repo.get_preco_benchmark_anp.assert_any_call("CAMPINAS", "ETANOL")


# =============================================================================
# 8. AUDITORIA ESTRITA DE ZERO UNICODE DASHES (EM-DASH E EN-DASH)
# =============================================================================

def test_zero_unicode_dashes_enforcement():
    """Garante que nenhum arquivo tocado contem em-dash (\u2014) ou en-dash (\u2013)."""
    from pathlib import Path

    base_dir = Path(__file__).resolve().parent.parent.parent
    arquivos_auditados = [
        base_dir / "core" / "tools.py",
        base_dir / "core" / "aura_engine.py",
        base_dir / "core" / "semantic_router.py",
        base_dir / "core" / "schemas" / "genui.py",
        Path(__file__),
    ]

    for arq in arquivos_auditados:
        if not arq.exists():
            continue
        conteudo = arq.read_text(encoding="utf-8")
        assert "\u2014" not in conteudo, f"Em-dash (\\u2014) encontrado no arquivo: {arq.name}"
        assert "\u2013" not in conteudo, f"En-dash (\\u2013) encontrado no arquivo: {arq.name}"
