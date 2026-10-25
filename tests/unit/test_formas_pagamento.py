"""
Testes Unitarios - Formas de Pagamento e Detalhamento por Caixa/Operador.
Valida o motor de analise de pagamentos por modalidade, PDV (caixa) e operador,
roteamento semantico de intencoes financeiras, validacao Pydantic v2 do
PaymentMethodsBreakdownProps e integracao com AuraEngine e GenUI.
"""

from unittest.mock import MagicMock

import pytest

from core.aura_engine import AuraEngine
from core.schemas.genui import (
    CashierOperatorPaymentItem,
    PaymentMethodBreakdownItem,
    PaymentMethodsBreakdownProps,
)
from core.semantic_router import SemanticRouter, classificar_intencao_heuristica
from core.tools import PostoTools


@pytest.fixture
def posto_tools():
    return PostoTools(rag_engine=MagicMock())


@pytest.fixture
def mock_router():
    return SemanticRouter(rag_engine=MagicMock())


def test_semantic_router_formas_pagamento(mock_router):
    """Valida se perguntas sobre formas de pagamento e caixas roteiam para formas_pagamento."""
    queries = [
        "quais foram as formas de pagamento do dia?",
        "qual foi a forma de pagamento de hoje?",
        "como foram as formas de pagamento?",
        "como foram os pagamentos por caixa hoje?",
        "quanto entrou em dinheiro e cartao?",
        "detalhe os pagamentos dos operadores por caixa",
        "me mostra as formas de pagamento e os caixas",
        "pagamentos do dia por operador",
    ]
    for q in queries:
        intent = classificar_intencao_heuristica(q)
        assert intent == "formas_pagamento", f"Query '{q}' deveria rotear para formas_pagamento, mas foi para {intent}"
        # Testa tambem via metodo route() com fallback
        routed_intent, _, _ = mock_router.route(q, use_cache=False)
        assert routed_intent == "formas_pagamento"


def test_consultar_formas_pagamento_detalhado_schema(posto_tools):
    """Valida a estrutura de retorno de consultar_formas_pagamento_detalhado e aderencia ao schema Pydantic."""
    resultado = posto_tools.consultar_formas_pagamento_detalhado()

    assert resultado["status"] == "ok"
    assert resultado["intent"] == "formas_pagamento"
    assert resultado["component_name"] == "render_PaymentMethodsBreakdownUI"
    assert resultado["client_component"] == "PaymentMethodsBreakdownUI"

    # Validacao estrita com Pydantic v2
    props = PaymentMethodsBreakdownProps(**resultado["props"])
    assert props.title == "Formas de Pagamento & Caixas"
    assert props.total_geral_reais >= 0
    assert props.total_transacoes >= 0
    assert len(props.suggested_actions) >= 3

    # Verifica lista de modalidades
    assert isinstance(props.modalidades, list)
    for mod in props.modalidades:
        assert isinstance(mod, PaymentMethodBreakdownItem)
        assert mod.modalidade != ""
        assert mod.total_reais >= 0
        assert 0 <= mod.percentual <= 100

    # Verifica lista de caixas e operadores
    assert isinstance(props.caixas_operadores, list)
    for c in props.caixas_operadores:
        assert isinstance(c, CashierOperatorPaymentItem)
        assert c.caixa != ""
        assert c.operador_nome != ""
        assert c.operador_matricula != ""
        assert c.total_caixa_reais >= 0

    # Verifica resumo executivo limpo
    resumo = resultado["resumo_executivo"]
    assert len(resumo) > 10
    assert "span class=" not in resumo
    assert "\u2014" not in resumo
    assert "\u2013" not in resumo


@pytest.mark.asyncio
async def test_engine_execute_tool_formas_pagamento():
    """Valida a execucao da ferramenta pelo AuraEngine."""
    engine = AuraEngine()
    resultado = await engine.execute_tool_direct("formas_pagamento")

    assert resultado.get("status") == "success"
    assert resultado.get("tool_name") == "formas_pagamento"
    data = resultado.get("data", {})
    assert data.get("component_name") == "render_PaymentMethodsBreakdownUI"
    assert "props" in data
    assert data["props"]["title"] == "Formas de Pagamento & Caixas"


def test_schemas_pydantic_validations():
    """Valida a criacao direta e regras dos modelos Pydantic."""
    item = PaymentMethodBreakdownItem(
        modalidade="Cartao de Credito",
        total_reais=150.50,
        percentual=60.0,
        transacoes=5,
        ticket_medio_reais=30.10,
    )
    assert item.modalidade == "Cartao de Credito"
    assert item.total_reais == 150.50

    caixa_item = CashierOperatorPaymentItem(
        caixa="Caixa 001",
        caixa_raw="001",
        operador_nome="JOAO DA SILVA",
        operador_matricula="00010",
        turno="1o TURNO",
        total_caixa_reais=500.00,
        total_cupons=12,
        dinheiro_reais=200.00,
        cartao_debito_reais=150.00,
        cartao_credito_reais=100.00,
        cartao_total_reais=250.00,
        pix_reais=50.00,
    )
    assert caixa_item.caixa == "Caixa 001"
    assert caixa_item.dinheiro_reais == 200.00
    assert caixa_item.cartao_total_reais == 250.00

    props = PaymentMethodsBreakdownProps(
        title="Formas de Pagamento & Caixas",
        data_referencia="2026-10-22",
        total_geral_reais=500.00,
        total_transacoes=12,
        ticket_medio_geral=41.67,
        modalidades=[item],
        caixas_operadores=[caixa_item],
    )
    assert props.total_geral_reais == 500.00
    assert len(props.caixas_operadores) == 1


def test_zero_travessoes_formas_pagamento():
    """Garante que nao existem travessoes proibidos (\u2014 ou \u2013) no modulo de testes."""
    with open(__file__, "r", encoding="utf-8") as f:
        content = f.read()
    assert "\u2014" not in content, "Travessao em-dash detectado em test_formas_pagamento.py"
    assert "\u2013" not in content, "Travessao en-dash detectado em test_formas_pagamento.py"
