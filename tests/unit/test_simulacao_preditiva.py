"""
Testes Unitarios - Simulacao Preditiva What-If e Precificacao Dinamica no Core Cognitivo AURA.
Valida o calculo de elasticidade-preco, paridade energetica 70% Etanol vs Gasolina,
impacto financeiro projetado e aderencia aos contratos Pydantic (PredictiveScenarioProps).
"""

from unittest.mock import MagicMock

import pytest

from core.aura_engine import AuraEngine, extrair_parametros_simulacao
from core.schemas.genui import PredictiveScenarioProps, ScenarioPoint
from core.tools import PostoTools


@pytest.fixture
def posto_tools():
    return PostoTools(rag_engine=MagicMock())


def test_simular_cenario_gasolina_comum(posto_tools):
    """Valida a simulacao de aumento de R$ 0,10 na Gasolina Comum com elasticidade -0.65."""
    resultado = posto_tools.simular_cenario_precificacao(
        produto="GASOLINA COMUM",
        delta_preco=0.10,
        periodo_dias=30,
    )

    assert resultado["status"] == "ok"
    assert resultado["intent"] == "cenario_preditivo"
    assert resultado["component_name"] == "render_PredictiveScenarioUI"
    assert "GASOLINA COMUM" in resultado["produto"].upper()
    assert resultado["delta_preco"] == 0.10
    assert resultado["periodo_dias"] == 30
    assert resultado["elasticidade"] == -0.65

    # Aumento de preco com elasticidade negativa deve reduzir volume
    assert resultado["delta_volume_pct"] < 0.0
    assert resultado["delta_volume_litros"] < 0.0

    # Margem de contribuicao deve expandir
    assert resultado["delta_margem_pct"] > 0.0

    # Lucro liquido para +0.10 na Gasolina Comum e positivo
    assert resultado["delta_lucro"] > 0.0

    # Validacao do contrato Pydantic
    props = PredictiveScenarioProps(**resultado["props"])
    assert isinstance(props.base_scenario, ScenarioPoint)
    assert isinstance(props.simulated_scenario, ScenarioPoint)
    assert props.elasticity_coefficient == -0.65
    assert len(props.suggested_actions) >= 2


def test_simular_cenario_etanol_paridade_70(posto_tools):
    """Valida a simulacao de reajuste no Etanol com efeito de paridade energetica frente a Gasolina."""
    resultado = posto_tools.simular_cenario_precificacao(
        produto="ETANOL",
        delta_preco=0.50,
        periodo_dias=30,
    )

    assert resultado["status"] == "ok"
    assert "ETANOL" in resultado["produto"].upper()
    assert resultado["elasticidade"] == -1.25

    # Etanol tem elasticidade alta (-1.25), entao reajuste forte gera grande perda de volume
    assert resultado["delta_volume_pct"] < -5.0

    # Diagnostico deve mencionar a paridade
    assert "Paridade Etanol/Gasolina" in resultado["diagnosis"] or "paridade" in resultado["diagnosis"].lower()

    # Contrato Pydantic
    props = PredictiveScenarioProps(**resultado["props"])
    assert props.confidence_score >= 0.85


def test_simular_cenario_diesel_s10(posto_tools):
    """Valida a simulacao no Diesel S10 com demanda inelastica (-0.45)."""
    resultado = posto_tools.simular_cenario_precificacao(
        produto="DIESEL S10",
        delta_preco=0.10,
        periodo_dias=30,
    )

    assert resultado["status"] == "ok"
    assert "DIESEL" in resultado["produto"].upper()
    assert resultado["elasticidade"] == -0.45

    # Demanda inelastica gera perda volumetrica moderada
    assert -3.0 < resultado["delta_volume_pct"] < 0.0
    assert resultado["delta_lucro"] > 0.0


def test_simular_cenario_reducao_promocional(posto_tools):
    """Valida reducao promocional de preco (-R$ 0,05) estimulando volume."""
    resultado = posto_tools.simular_cenario_precificacao(
        produto="GASOLINA COMUM",
        delta_preco=-0.05,
        periodo_dias=15,
    )

    assert resultado["status"] == "ok"
    assert resultado["delta_preco"] == -0.05
    assert resultado["periodo_dias"] == 15

    # Reducao de preco aumenta o volume de litros
    assert resultado["delta_volume_pct"] > 0.0
    assert resultado["delta_volume_litros"] > 0.0

    # Margem unitaria contrai levemente
    assert resultado["delta_margem_pct"] < 0.0


def test_simular_cenario_repasse_novo_custo(posto_tools):
    """Valida simulacao de what-if com novo custo de reposicao (aumento da distribuidora)."""
    # Simulando distribuidora aumentando custo de reposicao para R$ 6.15
    resultado = posto_tools.simular_cenario_precificacao(
        produto="GASOLINA COMUM",
        delta_preco=0.15,
        periodo_dias=30,
        custo_novo=6.15,
    )

    assert resultado["status"] == "ok"
    assert resultado["custo_simulado"] == 6.15
    assert resultado["props"]["base_scenario"]["preco_medio"] < resultado["props"]["simulated_scenario"]["preco_medio"]


def test_extrair_parametros_simulacao_nlp():
    """Valida extracao semantica de parametros de perguntas em linguagem natural."""
    p1 = "o que acontece se eu subir a gasolina comum em 10 centavos?"
    r1 = extrair_parametros_simulacao(p1)
    assert r1["produto"] == "GASOLINA COMUM"
    assert r1["delta_preco"] == 0.10
    assert r1["periodo_dias"] == 30

    p2 = "e se eu baixar o preco do etanol em 15 centavos por 15 dias?"
    r2 = extrair_parametros_simulacao(p2)
    assert r2["produto"] == "ETANOL"
    assert r2["delta_preco"] == -0.15
    assert r2["periodo_dias"] == 15

    p3 = "simular aumento de 20 centavos no diesel s10"
    r3 = extrair_parametros_simulacao(p3)
    assert r3["produto"] == "DIESEL S10"
    assert r3["delta_preco"] == 0.20

    p4 = "se o custo for para 6.20 e eu subir 0.15 na gasolina aditivada"
    r4 = extrair_parametros_simulacao(p4)
    assert r4["produto"] == "GASOLINA ADITIVADA"
    assert r4["delta_preco"] == 0.15
    assert r4["custo_novo"] == 6.20


@pytest.mark.asyncio
async def test_execute_tool_cenario_preditivo():
    """Valida execucao direta de cenario_preditivo via AuraEngine sem intermediacao de LLM."""
    engine = AuraEngine()
    res = await engine.execute_tool(
        "cenario_preditivo",
        {"produto": "GASOLINA COMUM", "delta_preco": 0.10, "periodo_dias": 30}
    )

    assert res["status"] == "success"
    assert res["tool_name"] == "cenario_preditivo"
    assert res["data"]["status"] == "ok"
    assert "GASOLINA COMUM" in res["data"]["produto"]
    assert res["latency_ms"] < 250
