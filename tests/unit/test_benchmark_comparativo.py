"""
Testes Unitarios - Benchmark Comparativo de Postos, Turnos e Concorrencia.
Valida o motor analitico deterministico de comparacao de precos de combustiveis,
ticket medio e conversao de aditivada no ERP frente a medias de mercado e metas da rede,
aderencia aos contratos Pydantic (BenchmarkComparisonProps), roteamento semantico e sintese GenUI.
"""

import json
from unittest.mock import MagicMock

import pytest

from core.aura_engine import AuraEngine
from core.schemas.genui import BenchmarkComparisonProps
from core.semantic_router import SemanticRouter
from core.tools import PostoTools


@pytest.fixture
def posto_tools():
    return PostoTools(rag_engine=MagicMock())


@pytest.fixture
def mock_router():
    return SemanticRouter(rag_engine=MagicMock())


def test_comparar_benchmark_concorrencia_defaults(posto_tools):
    """Valida a execucao padrao do benchmark comparativo contra concorrentes locais."""
    resultado = posto_tools.comparar_benchmark_concorrencia()

    assert resultado["status"] == "ok"
    assert resultado["intent"] == "benchmark_comparativo"
    assert resultado["component_name"] == "render_BenchmarkComparisonUI"
    assert resultado["client_component"] == "BenchmarkComparisonUI"

    # Validacao estrita do contrato Pydantic canônico
    props = BenchmarkComparisonProps(**resultado["props"])
    assert props.confidence_score >= 0.85
    assert 0.0 <= props.competitiveness_score <= 100.0
    assert len(props.entity_name) > 0
    assert len(props.benchmark_group) > 0
    assert props.market_position is not None
    assert len(props.comparison_items) == 7
    assert len(props.suggested_actions) >= 3
    assert len(props.limitations) >= 2

    # Verifica integridade dos indicadores confrontados
    kpi_names = [it.kpi_name for it in props.comparison_items]
    assert "Preco Gasolina Comum" in kpi_names
    assert "Preco Gasolina Aditivada" in kpi_names
    assert "Preco Etanol Hidratado" in kpi_names
    assert "Preco Diesel S10" in kpi_names
    assert "Conversao de Aditivada" in kpi_names
    assert "Ticket Medio da Pista" in kpi_names
    assert "Tempo Medio de Atendimento" in kpi_names

    for it in props.comparison_items:
        assert it.status in ("success", "warning", "danger", "neutral")
        assert it.filial_value is not None
        assert it.benchmark_value is not None
        assert it.gap_value is not None
        assert it.observation is not None


def test_comparar_benchmark_concorrencia_custom_overrides(posto_tools):
    """Valida passagem de benchmarks customizados (ex: rede de postos parceiros)."""
    custom = {
        "preco_gasolina_comum": 7.50,
        "preco_gasolina_aditivada": 7.80,
        "preco_etanol": 5.00,
        "preco_diesel_s10": 6.80,
        "conversao_aditivada_pct": 30.0,
        "ticket_medio_reais": 95.00,
        "tempo_atendimento_segundos": 180.0,
    }
    resultado = posto_tools.comparar_benchmark_concorrencia(
        grupo_benchmark="Rede Rodoviaria Sul",
        custom_benchmarks=custom,
        filial_nome="Posto Modelo Sul",
    )

    assert resultado["status"] == "ok"
    props = BenchmarkComparisonProps(**resultado["props"])
    assert props.entity_name == "Posto Modelo Sul"
    assert props.benchmark_group == "Rede Rodoviaria Sul"

    # Gasolina Comum com filial em ~7.19 (ou fallback 5.89) vs benchmark customizado de 7.50 deve ser success (mais barato)
    item_gc = next(it for it in props.comparison_items if it.kpi_name == "Preco Gasolina Comum")
    assert "7,50" in str(item_gc.benchmark_value)
    assert item_gc.status == "success"

    # Conversao em ~24.8% vs benchmark 30.0% (-5.2 pp) deve ser warning
    item_adit = next(it for it in props.comparison_items if it.kpi_name == "Conversao de Aditivada")
    assert "30.0%" in str(item_adit.benchmark_value)
    assert item_adit.status in ("warning", "danger")


def test_gerar_diagnostico_mentoria_executiva_benchmark(posto_tools):
    """Garante que a rota no mentor de decisoes executivo invoca o motor real sem mock estatico."""
    resultado = posto_tools.gerar_diagnostico_mentoria_executiva(tipo="benchmark_comparativo")

    assert resultado["status"] == "ok"
    assert resultado["intent"] == "benchmark_comparativo"
    assert resultado["component_name"] == "render_BenchmarkComparisonUI"
    assert "props" in resultado

    props = BenchmarkComparisonProps(**resultado["props"])
    assert len(props.comparison_items) == 7
    assert props.competitiveness_score > 0.0


def test_semantic_router_benchmark_queries(mock_router):
    """Valida o roteamento semantico heuristico e vetorial para a intencao benchmark_comparativo."""
    consultas_teste = [
        "Como estão nossos preços frente à concorrência?",
        "Benchmark comparativo com concorrentes",
        "Ranking de competitividade do posto",
        "Comparar preços de combustíveis com o mercado",
        "Preço da concorrência na gasolina comum",
        "Preços dos concorrentes no raio",
        "Posicionamento competitivo da filial",
        "Benchmark de preços e conversão de aditivada",
        "Comparar com a concorrência no raio de 3km",
        "Comparativo regional de postos",
        "Como estamos posicionados no mercado local?",
    ]

    for q in consultas_teste:
        intencao, confianca, _telemetria = mock_router.route(q)
        assert intencao == "benchmark_comparativo", (
            f"Query '{q}' deveria rotear para benchmark_comparativo, mas retornou '{intencao}'"
        )
        assert confianca >= 0.50


@pytest.mark.asyncio
async def test_aura_engine_execute_tool_benchmark(posto_tools):
    """Valida a execucao direta (headless intent call) de benchmark_comparativo no AuraEngine."""
    engine = AuraEngine(tools=posto_tools)
    res = await engine.execute_tool_direct("benchmark_comparativo")

    assert res["status"] == "success"
    assert res["tool_name"] == "benchmark_comparativo"
    assert "data" in res
    assert res["data"]["intent"] == "benchmark_comparativo"
    assert "props" in res["data"]
    props = BenchmarkComparisonProps(**res["data"]["props"])
    assert props.competitiveness_score >= 0.0


def test_aura_engine_sintese_contingencia_benchmark(posto_tools):
    """Valida a formatacao executiva de contingencia deterministica no AuraEngine."""
    engine = AuraEngine(tools=posto_tools)
    resultado_bruto = posto_tools.comparar_benchmark_concorrencia()

    sintese = engine._gerar_sintese_contingencia_ferramenta(
        intencao="benchmark_comparativo",
        resultado_bruto=resultado_bruto,
        pergunta="Como estão nossos preços frente à concorrência?",
    )

    assert sintese is not None
    assert "Benchmark Comparativo de Postos & Concorrência" in sintese
    assert "Score de Competitividade" in sintese
    assert "Preco Gasolina Comum" in sintese
    assert "Decisões Disponíveis" in sintese or "Ações Recomendadas" in sintese


def test_no_em_dash_or_en_dash_in_benchmark_artifacts(posto_tools):
    """Regra inegociavel: ZERO travoes em todos os payloads e textos gerados."""
    resultado = posto_tools.comparar_benchmark_concorrencia()
    json_str = json.dumps(resultado, ensure_ascii=False)

    assert "\u2014" not in json_str, "Payload contem travessao em-dash proibido!"
    assert "\u2013" not in json_str, "Payload contem travessao en-dash proibido!"

    engine = AuraEngine(tools=posto_tools)
    sintese = engine._gerar_sintese_contingencia_ferramenta(
        intencao="benchmark_comparativo",
        resultado_bruto=resultado,
        pergunta="Como estamos frente aos concorrentes?",
    )

    assert sintese is not None
    assert "\u2014" not in sintese, "Sintese contem travessao em-dash proibido!"
    assert "\u2013" not in sintese, "Sintese contem travessao en-dash proibido!"


@pytest.mark.asyncio
async def test_aura_engine_query_and_build_response_text(posto_tools):
    """Valida os metodos query() e _build_response_text() do AuraEngine para benchmark."""
    engine = AuraEngine(tools=posto_tools)
    resultado = posto_tools.comparar_benchmark_concorrencia()

    # Valida _build_response_text para benchmark_comparativo e comparativo_turnos
    resp_text_bench = engine._build_response_text("benchmark_comparativo", resultado)
    assert resp_text_bench is not None
    assert "Benchmark Comparativo de Postos & Concorrência" in resp_text_bench
    assert "Score de Competitividade" in resp_text_bench

    resp_text_turnos = engine._build_response_text("comparativo_turnos", resultado)
    assert resp_text_turnos is not None
    assert "Benchmark Comparativo de Postos & Concorrência" in resp_text_turnos

    # Valida query assincrona direta
    resp = await engine.query("Como estão nossos preços frente à concorrência?")
    assert resp.intent == "benchmark_comparativo"
    assert resp.response_text is not None and len(resp.response_text) > 0
    resp_lower = resp.response_text.lower()
    assert any(term in resp_lower for term in ("competitividade", "gasolina", "preço", "preco", "ranking", "posto", "concorrência", "concorrencia"))


def test_canonical_product_precedence_and_limitations(posto_tools):
    """Valida precedencia do produto canonico 00001 sobre produtos clone e nota de limitacoes."""
    resultado = posto_tools.comparar_benchmark_concorrencia()
    precos = resultado.get("precos_filial", {})
    # Produto canonico 00001 no banco e 7.19, nao deve ser sobrescrito pelo clone 00134 (5.95)
    assert precos.get("gasolina_comum") != 5.95
    assert len(resultado["limitations"]) >= 2
