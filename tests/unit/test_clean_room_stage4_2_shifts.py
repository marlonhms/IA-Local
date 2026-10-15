"""
Testes Unitarios do Bloco 4 (Etapa 4.2): Migracao de Fechamento de Turno e Fuga Financeira.
Valida o desacoplamento de PostoTools para consumo exclusivo do ERP Adapter e AUPS.
Assegura que nenhuma query SQL direta de caixas, bombas ou abastecimentos permaneca no PostoTools.
Regra inegociavel: ZERO travessoes em todo o arquivo.
"""

import inspect
from datetime import date, datetime
from unittest.mock import MagicMock

import pytest

from core.adapters.erp import MockERPAdapter
from core.aura_engine import AuraEngine
from core.domain.cashier import UniversalCashierShift
from core.domain.pumps import UniversalDispenserLog
from core.domain.sales import (
    UniversalPaymentMethod,
    UniversalSaleItem,
    UniversalSaleReceipt,
)
from core.domain.tanks import UniversalTankReading
from core.schemas.genui import FinancialLeakAuditProps
from core.schemas.reconciliation import ShiftReconciliationContract
from core.tools import PostoTools


@pytest.fixture
def custom_mock_adapter():
    """Adaptador ERP Mock com massa de dados deterministica para testes de turno e vazamentos."""
    adapter = MockERPAdapter()

    # Turno com quebra de caixa e retencao controlada
    shift_pdv1 = UniversalCashierShift(
        operador_id="001",
        operador_nome="JOAO OPERADOR",
        turno_descricao="Turno 1",
        data_movimento=date(2026, 10, 15),
        timestamp_abertura=datetime(2026, 10, 15, 6, 0, 0),
        timestamp_fechamento=datetime(2026, 10, 15, 14, 0, 0),
        fundo_troco_reais=150.0,
        total_declarado_reais=850.0,
        total_sistema_reais=900.0,
        quebra_sobra_reais=-50.0,
        pdv="1",
        caixa_id="101",
        fechado=True,
        dinheiro_declarado_reais=250.0,
        cartao_declarado_reais=500.0,
        prazo_declarado_reais=100.0,
        convenio_cheque_reais=0.0,
        venda_combustivel_reais=700.0,
        venda_produtos_reais=200.0,
        litros_declarados=120.0,
    )

    # Medicao de bico de pista
    dispense_bico1 = UniversalDispenserLog(
        identificador_bomba="1",
        identificador_bico="1",
        timestamp_registro=datetime(2026, 10, 15, 14, 0, 0),
        encerrante_inicial_litros=10000.0,
        encerrante_final_litros=10100.0,
        volume_aferido_litros=0.0,
        total_faturado_reais=589.0,
        codigo_combustivel="01",
        descricao_combustivel="Gasolina Comum",
        identificador_tanque="1",
        preco_unitario_reais=5.89,
        turno_descricao="Turno 1",
        pdv="1",
        qtd_abastecimentos=8,
        volume_automacao_litros=100.0,
        total_automacao_reais=589.0,
    )

    # Tanque correspondente
    tank_1 = UniversalTankReading(
        identificador_tanque="1",
        combustivel="Gasolina Comum",
        timestamp_leitura=datetime(2026, 10, 15, 14, 0, 0),
        volume_atual_litros=14900.0,
        volume_agua_mm=0.0,
        temperatura_celsius=23.0,
        percentual_capacidade=74.5,
        capacidade_nominal_litros=20000.0,
        saldo_inicial_litros=15000.0,
        saldo_final_litros=14900.0,
        tem_medicao_fisica=True,
    )

    # Venda PDV correspondente
    sale_1 = UniversalSaleReceipt(
        cupom_id="CUPOM_TURNO_01",
        data_hora=datetime(2026, 10, 15, 10, 0, 0),
        pdv="1",
        total_reais=589.0,
        status="CONCLUIDA",
        operador="JOAO OPERADOR",
        itens=[
            UniversalSaleItem(
                sku="01",
                descricao_produto="Gasolina Comum",
                grupo_comercial="Combustiveis",
                preco_unitario_reais=5.89,
                quantidade=100.0,
                total_item_reais=589.0,
            )
        ],
        pagamentos=[
            UniversalPaymentMethod(
                codigo_forma_pagamento="1",
                descricao_forma="DINHEIRO",
                tipo="dinheiro",
                valor_reais=200.0,
            ),
            UniversalPaymentMethod(
                codigo_forma_pagamento="2",
                descricao_forma="CARTAO DE DEBITO",
                tipo="debito",
                valor_reais=389.0,
            ),
        ],
    )

    adapter.reset()
    adapter.add_cashier_shift(shift_pdv1)
    adapter.add_pump_dispense(dispense_bico1)
    adapter.add_tank_reading(tank_1)
    adapter.add_sale(sale_1)

    return adapter


def test_auditar_fechamento_turno_with_mock_adapter(custom_mock_adapter):
    """Valida auditar_fechamento_turno consumindo exclusivamente o ERP Adapter."""
    tools = PostoTools(rag_engine=MagicMock(), erp_adapter=custom_mock_adapter)
    resultado = tools.auditar_fechamento_turno(data="2026-10-15", turno="Turno 1")

    assert resultado["status"] == "ok"
    assert resultado["intent"] == "shift_reconciliation"
    assert "contrato" in resultado

    contrato = ShiftReconciliationContract(**resultado["contrato"])
    assert contrato.context.data_auditada == "2026-10-15"
    assert contrato.assessment.finality in ("final", "partial")
    assert contrato.metrics.automation_volume_liters == 100.0
    assert len(contrato.sources) >= 4

    # Verifica triangulacao de pista e caixa
    assert "triangulacao_pista" in resultado
    pista = resultado["triangulacao_pista"]
    assert pista["total_bicos_auditados"] >= 1
    assert pista["total_litros_automacao"] == 100.0

    assert "triangulacao_caixa" in resultado
    caixas = resultado["triangulacao_caixa"]["caixas"]
    assert len(caixas) >= 1
    assert caixas[0]["matricula"] == "001"
    assert caixas[0]["total_declarado"] == 850.0


def test_auditar_fechamento_turno_sem_movimento(custom_mock_adapter):
    """Valida diagnostico deterministico quando nao ha movimentacao na data consultada."""
    tools = PostoTools(rag_engine=MagicMock(), erp_adapter=custom_mock_adapter)
    resultado = tools.auditar_fechamento_turno(data="2020-01-01")

    assert resultado["status"] == "sem_movimento"
    assert resultado["intent"] == "shift_reconciliation"
    contrato = ShiftReconciliationContract(**resultado["contrato"])
    assert contrato.assessment.finality == "no_movement"
    assert contrato.metrics.automation_volume_liters == 0.0


def test_auditar_fuga_financeira_with_mock_adapter(custom_mock_adapter):
    """Valida auditar_fuga_financeira consumindo dados canônicos do ERP Adapter."""
    tools = PostoTools(rag_engine=MagicMock(), erp_adapter=custom_mock_adapter)
    resultado = tools.auditar_fuga_financeira(data="2026-10-15", turno="Turno 1", pdv="1")

    assert resultado["status"] == "ok"
    assert resultado["intent"] == "auditoria_fuga_financeira"
    assert resultado["component_name"] == "render_FinancialLeakAuditUI"

    props = FinancialLeakAuditProps(**resultado["props"])
    assert props.confidence_score >= 0.85
    assert len(props.suggested_actions) >= 2
    assert props.audited_shift is not None


def test_no_raw_sql_in_migrated_shift_tools():
    """Valida estritamente que nenhum comando SQL direto permanece em auditar_fechamento_turno e auditar_fuga_financeira."""
    src_turno = inspect.getsource(PostoTools.auditar_fechamento_turno)
    src_fuga = inspect.getsource(PostoTools.auditar_fuga_financeira)

    prohibited_sql_tokens = [
        "SELECT ",
        "FROM fechacaixa",
        "FROM fechabomba",
        "FROM abastecimentos",
        "FROM pedido",
        "FROM tanques",
        "cur.execute",
        "cursor_factory",
        "get_erp_connection",
    ]

    for token in prohibited_sql_tokens:
        assert token.lower() not in src_turno.lower(), (
            f"Token SQL proibido '{token}' encontrado em auditar_fechamento_turno"
        )
        assert token.lower() not in src_fuga.lower(), (
            f"Token SQL proibido '{token}' encontrado em auditar_fuga_financeira"
        )


@pytest.mark.asyncio
async def test_aura_engine_integration_with_adapter(custom_mock_adapter):
    """Valida que AuraEngine executa conciliacao de turno e fuga financeira com erp_adapter injetado."""
    engine = AuraEngine(erp_adapter=custom_mock_adapter)

    # 1. Conciliacao de Turno
    res_turno = await engine.execute_tool_direct("conciliacao_turno", {"data": "2026-10-15"})
    assert res_turno["status"] == "success"
    assert res_turno["tool_name"] == "conciliacao_turno"
    assert res_turno["data"]["status"] == "ok"

    # 2. Auditoria de Fuga Financeira
    res_fuga = await engine.execute_tool_direct("auditoria_fuga_financeira", {"data": "2026-10-15"})
    assert res_fuga["status"] == "success"
    assert res_fuga["tool_name"] == "auditoria_fuga_financeira"
    assert res_fuga["data"]["status"] == "ok"


def test_clean_room_shifts_zero_dashes():
    """Garante ausencia estrita de em-dash e en-dash neste arquivo de testes."""
    with open(__file__, "r", encoding="utf-8") as f:
        content = f.read()
    assert "\u2014" not in content, "Em-dash proibido encontrado no arquivo de testes"
    assert "\u2013" not in content, "En-dash proibido encontrado no arquivo de testes"
