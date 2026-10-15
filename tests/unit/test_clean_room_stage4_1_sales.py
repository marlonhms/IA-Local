"""
Testes Unitarios do Bloco 4 (Etapa 4.1): Migracao de Vendas e Loja de Conveniencia.
Valida o desacoplamento de PostoTools para consumo exclusivo do ERP Adapter e AUPS.
Assegura que nenhuma query SQL direta de vendas permaneca no PostoTools.
Regra inegociavel: ZERO travessoes em todo o arquivo.
"""

import inspect
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from core.adapters.erp import MockERPAdapter, PostgresLocalERPAdapter
from core.aura_engine import AuraEngine
from core.domain.sales import (
    UniversalPaymentMethod,
    UniversalSaleItem,
    UniversalSaleReceipt,
)
from core.schemas.genui import BasketUpsellStrategyProps
from core.tools import PostoTools


@pytest.fixture
def mock_erp_adapter():
    """Adaptador ERP Mock com massa de testes deterministica em memoria."""
    sales = [
        UniversalSaleReceipt(
            cupom_id="CUPOM_001",
            data_hora=datetime(2026, 10, 15, 10, 30, 0),
            pdv="1",
            total_reais=25.0,
            status="CONCLUIDA",
            operador="FRENTISTA_01",
            itens=[
                UniversalSaleItem(
                    sku="00010",
                    descricao_produto="Cafe Expresso",
                    grupo_comercial="Conveniencia",
                    preco_unitario_reais=5.50,
                    quantidade=1.0,
                    total_item_reais=5.50,
                ),
                UniversalSaleItem(
                    sku="00011",
                    descricao_produto="Pao de Queijo",
                    grupo_comercial="Conveniencia",
                    preco_unitario_reais=7.50,
                    quantidade=1.0,
                    total_item_reais=7.50,
                ),
            ],
            pagamentos=[
                UniversalPaymentMethod(
                    codigo_forma_pagamento="1",
                    descricao_forma="DINHEIRO",
                    tipo="dinheiro",
                    valor_reais=25.0,
                )
            ],
        ),
        UniversalSaleReceipt(
            cupom_id="CUPOM_002",
            data_hora=datetime(2026, 10, 15, 11, 0, 0),
            pdv="1",
            total_reais=13.0,
            status="CONCLUIDA",
            operador="FRENTISTA_01",
            itens=[
                UniversalSaleItem(
                    sku="00010",
                    descricao_produto="Cafe Expresso",
                    grupo_comercial="Conveniencia",
                    preco_unitario_reais=5.50,
                    quantidade=1.0,
                    total_item_reais=5.50,
                ),
                UniversalSaleItem(
                    sku="00011",
                    descricao_produto="Pao de Queijo",
                    grupo_comercial="Conveniencia",
                    preco_unitario_reais=7.50,
                    quantidade=1.0,
                    total_item_reais=7.50,
                ),
            ],
            pagamentos=[
                UniversalPaymentMethod(
                    codigo_forma_pagamento="2",
                    descricao_forma="CARTAO DE DEBITO",
                    tipo="debito",
                    valor_reais=13.0,
                )
            ],
        ),
        UniversalSaleReceipt(
            cupom_id="CUPOM_003",
            data_hora=datetime(2026, 10, 15, 11, 45, 0),
            pdv="2",
            total_reais=50.0,
            status="CONCLUIDA",
            operador="OPERADOR_02",
            itens=[
                UniversalSaleItem(
                    sku="00020",
                    descricao_produto="Cerveja 6-pack",
                    grupo_comercial="Bebidas",
                    preco_unitario_reais=35.0,
                    quantidade=1.0,
                    total_item_reais=35.0,
                ),
                UniversalSaleItem(
                    sku="00021",
                    descricao_produto="Gelo Filtrado 5kg",
                    grupo_comercial="Gelo",
                    preco_unitario_reais=15.0,
                    quantidade=1.0,
                    total_item_reais=15.0,
                ),
            ],
        ),
    ]
    return MockERPAdapter(sales=sales, is_connected=True)


@pytest.fixture
def tools_with_mock(mock_erp_adapter):
    """Instancia de PostoTools acoplada ao MockERPAdapter sem banco de dados."""
    return PostoTools(rag_engine=MagicMock(), erp_adapter=mock_erp_adapter)


def test_posto_tools_adapter_injection():
    """Valida que PostoTools aceita injecao explicita de erp_adapter e possui fallback padrao."""
    # 1. Com fallback padrao
    tools_default = PostoTools(rag_engine=MagicMock())
    assert isinstance(tools_default.erp_adapter, PostgresLocalERPAdapter)

    # 2. Com injecao de MockERPAdapter
    mock_adapter = MockERPAdapter()
    tools_mock = PostoTools(rag_engine=MagicMock(), erp_adapter=mock_adapter)
    assert tools_mock.erp_adapter is mock_adapter


def test_consultar_analise_vendas_erp_with_adapter(tools_with_mock):
    """Valida execucao de consultar_analise_vendas_erp consumindo puramente o adapter."""
    resultado = tools_with_mock.consultar_analise_vendas_erp()

    assert resultado["status"] == "ok"
    assert "ultimo_produto_vendido_destaque" in resultado
    assert "ultimos_produtos_conveniencia" in resultado
    assert "produtos_mais_vendidos" in resultado
    assert "resumo_hoje" in resultado
    assert "resumo_geral" in resultado

    # Verifica integridade dos produtos mais vendidos
    mais_vendidos = resultado["produtos_mais_vendidos"]
    assert len(mais_vendidos) > 0
    skus = [p["codpro"] for p in mais_vendidos]
    assert "00010" in skus or "00011" in skus or "00020" in skus

    # Verifica resumo de hoje
    resumo_hoje = resultado["resumo_hoje"]
    assert resumo_hoje["pedidos_conveniencia_hoje"] >= 0
    assert resumo_hoje["faturamento_conveniencia_hoje"] >= 0.0


def test_auditar_cesta_conveniencia_with_adapter(tools_with_mock):
    """Valida mineracao Apriori em auditar_cesta_conveniencia_vendas_cruzadas via adapter."""
    resultado = tools_with_mock.auditar_cesta_conveniencia_vendas_cruzadas(
        min_lift=1.0,
        min_suporte=0.01,
        min_confianca=0.1,
    )

    assert resultado["status"] == "ok"
    assert resultado["component_name"] == "render_BasketUpsellStrategyUI"
    assert resultado["client_component"] == "BasketUpsellStrategyUI"

    props = BasketUpsellStrategyProps(**resultado["props"])
    assert props.confidence_score >= 0.85
    assert props.total_transacoes == 3
    assert len(props.top_combos) > 0

    # Verifica combo esperado entre Cafe e Pao de Queijo
    combos_str = [
        f"{c.anchor_product} + {c.recommended_product}" for c in props.top_combos
    ]
    assert any("Cafe Expresso" in c and "Pao de Queijo" in c for c in combos_str)


def test_no_raw_sql_in_migrated_sales_tools():
    """Valida estritamente que nenhum comando SQL direto permanece nos metodos migrados de vendas."""
    src_vendas = inspect.getsource(PostoTools.consultar_analise_vendas_erp)
    src_cesta = inspect.getsource(PostoTools.auditar_cesta_conveniencia_vendas_cruzadas)

    prohibited_sql_tokens = [
        "SELECT ",
        "FROM pedido",
        "JOIN itemped",
        "WHERE p.situ",
        "cur.execute",
        "cursor_factory",
    ]

    for token in prohibited_sql_tokens:
        assert token.lower() not in src_vendas.lower(), (
            f"Token SQL proibido '{token}' encontrado em consultar_analise_vendas_erp"
        )
        assert token.lower() not in src_cesta.lower(), (
            f"Token SQL proibido '{token}' encontrado em auditar_cesta_conveniencia_vendas_cruzadas"
        )


@pytest.mark.asyncio
async def test_aura_engine_integration_with_adapter(mock_erp_adapter):
    """Valida que AuraEngine aceita erp_adapter injetado e executa vendas_analitico."""
    engine = AuraEngine(erp_adapter=mock_erp_adapter)
    res = await engine.execute_tool_direct("vendas_analitico", {})

    assert res["status"] == "success"
    assert res["tool_name"] == "vendas_analitico"
    assert "data" in res
    assert res["data"]["status"] == "ok"


def test_clean_room_sales_zero_dashes():
    """Garante ausencia estrita de em-dash e en-dash neste arquivo de testes."""
    with open(__file__, "r", encoding="utf-8") as f:
        content = f.read()
    assert "\u2014" not in content, "Em-dash proibido encontrado no arquivo de testes"
    assert "\u2013" not in content, "En-dash proibido encontrado no arquivo de testes"
