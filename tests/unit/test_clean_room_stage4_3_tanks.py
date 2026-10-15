"""
Testes Unitarios do Bloco 4 (Etapa 4.3): Migracao de Tanques e Relatorio LMC Oficial ANP.
Valida o desacoplamento de PostoTools para consumo exclusivo do ERP Adapter e AUPS.
Assegura que nenhuma query SQL direta de tanques, bombas ou abastecimentos permaneca no PostoTools.
Regra inegociavel: ZERO travessoes em todo o arquivo.
"""

import inspect
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from core.adapters.erp import MockERPAdapter
from core.aura_engine import AuraEngine
from core.domain.pumps import UniversalDispenserLog
from core.domain.tanks import UniversalTankReading
from core.schemas.lmc_report import LMCReportContract
from core.schemas.tank_forecast import TankForecastContract
from core.tools import PostoTools


@pytest.fixture
def custom_tank_mock_adapter():
    """Adaptador ERP Mock com massa deterministica calibrada para previsao e LMC."""
    adapter = MockERPAdapter()
    adapter.reset()

    # Leitura calibrada dos 4 tanques
    t1 = UniversalTankReading(
        identificador_tanque="1",
        combustivel="Gasolina Comum",
        codigo_lmc="420101001",
        bicos_conectados=["1", "2"],
        timestamp_leitura=datetime(2026, 10, 15, 18, 0, 0),
        volume_atual_litros=5000.0,
        volume_agua_mm=0.0,
        temperatura_celsius=24.5,
        percentual_capacidade=25.0,
        capacidade_nominal_litros=20000.0,
        saldo_inicial_litros=6500.0,
        saldo_final_litros=5000.0,
        tem_medicao_fisica=True,
    )
    t2 = UniversalTankReading(
        identificador_tanque="2",
        combustivel="Gasolina Aditivada",
        codigo_lmc="420101002",
        bicos_conectados=["3"],
        timestamp_leitura=datetime(2026, 10, 15, 18, 0, 0),
        volume_atual_litros=2000.0,
        volume_agua_mm=0.0,
        temperatura_celsius=24.8,
        percentual_capacidade=13.33,
        capacidade_nominal_litros=15000.0,
        saldo_inicial_litros=2800.0,
        saldo_final_litros=2000.0,
        tem_medicao_fisica=True,
    )
    t3 = UniversalTankReading(
        identificador_tanque="3",
        combustivel="Etanol Hidratado",
        codigo_lmc="420102001",
        bicos_conectados=["4"],
        timestamp_leitura=datetime(2026, 10, 15, 18, 0, 0),
        volume_atual_litros=8000.0,
        volume_agua_mm=1.0,
        temperatura_celsius=23.9,
        percentual_capacidade=53.33,
        capacidade_nominal_litros=15000.0,
        saldo_inicial_litros=8650.0,
        saldo_final_litros=8000.0,
        tem_medicao_fisica=True,
    )
    t4 = UniversalTankReading(
        identificador_tanque="4",
        combustivel="Diesel S10",
        codigo_lmc="420103001",
        bicos_conectados=["5"],
        timestamp_leitura=datetime(2026, 10, 15, 18, 0, 0),
        volume_atual_litros=18000.0,
        volume_agua_mm=0.0,
        temperatura_celsius=25.1,
        percentual_capacidade=60.0,
        capacidade_nominal_litros=30000.0,
        saldo_inicial_litros=20500.0,
        saldo_final_litros=18000.0,
        tem_medicao_fisica=True,
    )

    # Dispensas sincronizadas para a data 2026-10-15
    d1 = UniversalDispenserLog(
        identificador_bomba="1",
        identificador_bico="1",
        identificador_tanque="1",
        codigo_combustivel="COMB_01",
        descricao_combustivel="Gasolina Comum",
        turno_descricao="MANHA",
        pdv="1",
        timestamp_registro=datetime(2026, 10, 15, 14, 0, 0),
        encerrante_inicial_litros=100000.0,
        encerrante_final_litros=101500.0,
        volume_aferido_litros=0.0,
        preco_unitario_reais=5.89,
        total_faturado_reais=8835.0,
        qtd_abastecimentos=35,
        volume_automacao_litros=1500.0,
        total_automacao_reais=8835.0,
    )
    d2 = UniversalDispenserLog(
        identificador_bomba="1",
        identificador_bico="3",
        identificador_tanque="2",
        codigo_combustivel="COMB_02",
        descricao_combustivel="Gasolina Aditivada",
        turno_descricao="MANHA",
        pdv="1",
        timestamp_registro=datetime(2026, 10, 15, 14, 0, 0),
        encerrante_inicial_litros=50000.0,
        encerrante_final_litros=50800.0,
        volume_aferido_litros=0.0,
        preco_unitario_reais=6.19,
        total_faturado_reais=4952.0,
        qtd_abastecimentos=20,
        volume_automacao_litros=800.0,
        total_automacao_reais=4952.0,
    )
    d3 = UniversalDispenserLog(
        identificador_bomba="2",
        identificador_bico="4",
        identificador_tanque="3",
        codigo_combustivel="COMB_03",
        descricao_combustivel="Etanol Hidratado",
        turno_descricao="MANHA",
        pdv="2",
        timestamp_registro=datetime(2026, 10, 15, 14, 0, 0),
        encerrante_inicial_litros=30000.0,
        encerrante_final_litros=30650.0,
        volume_aferido_litros=0.0,
        preco_unitario_reais=3.99,
        total_faturado_reais=2593.5,
        qtd_abastecimentos=18,
        volume_automacao_litros=650.0,
        total_automacao_reais=2593.5,
    )
    d4 = UniversalDispenserLog(
        identificador_bomba="2",
        identificador_bico="5",
        identificador_tanque="4",
        codigo_combustivel="COMB_04",
        descricao_combustivel="Diesel S10",
        turno_descricao="MANHA",
        pdv="2",
        timestamp_registro=datetime(2026, 10, 15, 14, 0, 0),
        encerrante_inicial_litros=150000.0,
        encerrante_final_litros=152500.0,
        volume_aferido_litros=0.0,
        preco_unitario_reais=6.15,
        total_faturado_reais=15375.0,
        qtd_abastecimentos=30,
        volume_automacao_litros=2500.0,
        total_automacao_reais=15375.0,
    )

    adapter._tanks = [t1, t2, t3, t4]
    adapter._pumps = [d1, d2, d3, d4]

    return adapter


def test_prever_esgotamento_tanques_with_mock_adapter(custom_tank_mock_adapter):
    """Valida prever_esgotamento_tanques consumindo exclusivamente o ERP Adapter."""
    tools = PostoTools(rag_engine=MagicMock(), erp_adapter=custom_tank_mock_adapter)
    resultado = tools.prever_esgotamento_tanques()

    assert resultado["status"] == "ok"
    assert resultado["intent"] == "tank_forecast"
    assert "contrato" in resultado

    contrato = TankForecastContract(**resultado["contrato"])
    assert len(contrato.tanks) == 4
    assert len(contrato.fuel_summary) >= 4
    assert contrato.metrics.saldo_total_litros == 33000.0
    assert contrato.metrics.capacidade_total_litros == 80000.0

    # Verifica tanque mais critico (Tanque 2 esta em nivel critico < 15%)
    resumo = resultado["resumo_executivo"]
    assert resumo["status_geral"] == "ALERTA_ESTOQUE_CRITICO"
    tanque_crit = resumo["tanque_mais_critico"]
    assert tanque_crit["codtan"] == "2"
    assert tanque_crit["urgencia"] == "CRÍTICA / IMEDIATA"


def test_prever_esgotamento_tanques_filtro_combustivel(custom_tank_mock_adapter):
    """Valida aplicacao de filtro por combustivel na previsao de esgotamento."""
    tools = PostoTools(rag_engine=MagicMock(), erp_adapter=custom_tank_mock_adapter)
    resultado = tools.prever_esgotamento_tanques(filtro_combustivel="Diesel S10")

    assert resultado["status"] == "ok"
    assert resultado["filtro_aplicado"] == "Diesel S10"
    tanques = resultado["tanks"]
    assert len(tanques) == 1
    assert tanques[0]["combustivel"] == "Diesel S10"
    assert tanques[0]["capacidade_litros"] == 30000.0


def test_gerar_relatorio_lmc_anp_with_mock_adapter(custom_tank_mock_adapter):
    """Valida gerar_relatorio_lmc_anp consumindo exclusivamente o ERP Adapter."""
    tools = PostoTools(rag_engine=MagicMock(), erp_adapter=custom_tank_mock_adapter)
    resultado = tools.gerar_relatorio_lmc_anp(data="2026-10-15")

    assert resultado["status"] == "ok"
    assert resultado["intent"] == "lmc_report"
    assert "contrato" in resultado

    contrato = LMCReportContract(**resultado["contrato"])
    assert contrato.context.data_lmc == "2026-10-15"
    assert len(contrato.tanks) == 4
    assert contrato.metrics.total_tanques_analisados == 4
    assert contrato.metrics.tolerancia_oficial_pct == 0.6

    # Verifica se os 4 tanques estao conformes com a margem legal da Portaria ANP 26/1992
    assert contrato.assessment.status_geral_anp == "CONFORME_ANP"
    assert contrato.assessment.dentro_tolerancia_geral is True
    for item in contrato.tanks:
        assert item.dentro_tolerancia is True
        assert item.codlmc_anp != "N/D"


def test_gerar_relatorio_lmc_anp_filtro_tanque(custom_tank_mock_adapter):
    """Valida filtro por codigo de tanque no Relatorio Oficial LMC."""
    tools = PostoTools(rag_engine=MagicMock(), erp_adapter=custom_tank_mock_adapter)
    resultado = tools.gerar_relatorio_lmc_anp(data="2026-10-15", tanque="4")

    assert resultado["status"] == "ok"
    tanques = resultado["tanques"]
    assert len(tanques) == 1
    assert tanques[0]["tanque"] == "4"
    assert tanques[0]["combustivel"] == "Diesel S10"
    assert tanques[0]["movimentacao"]["vendas_bicos_litros"] == 2500.0


def test_no_raw_sql_in_migrated_tank_and_lmc_tools():
    """Valida via AST inspection que nenhum comando SQL direto permanece nas ferramentas migradas."""
    src_tanks = inspect.getsource(PostoTools.prever_esgotamento_tanques)
    src_lmc = inspect.getsource(PostoTools.gerar_relatorio_lmc_anp)

    prohibited_sql_tokens = [
        "SELECT ",
        "FROM tanques",
        "FROM bombas",
        "FROM abastecimentos",
        "FROM fechabomba",
        "cur.execute",
        "cursor_factory",
        "get_erp_connection",
    ]

    for token in prohibited_sql_tokens:
        assert token.lower() not in src_tanks.lower(), (
            f"Token SQL proibido '{token}' encontrado em prever_esgotamento_tanques"
        )
        assert token.lower() not in src_lmc.lower(), (
            f"Token SQL proibido '{token}' encontrado em gerar_relatorio_lmc_anp"
        )

    # Garante presenca explicita do adaptador ERP desacoplado
    assert "self.erp_adapter.get_tank_inventory()" in src_tanks
    assert "self.erp_adapter.get_pump_dispenses" in src_tanks
    assert "self.erp_adapter.get_tank_inventory()" in src_lmc
    assert "self.erp_adapter.get_pump_dispenses" in src_lmc


@pytest.mark.asyncio
async def test_aura_engine_integration_tanks_and_lmc(custom_tank_mock_adapter):
    """Valida que AuraEngine executa previsao de tanques e LMC ANP com erp_adapter injetado."""
    engine = AuraEngine(erp_adapter=custom_tank_mock_adapter)

    # 1. Previsao de Esgotamento de Tanques
    res_tanks = await engine.execute_tool_direct("prever_esgotamento_tanques", {})
    assert res_tanks["status"] == "success"
    assert res_tanks["tool_name"] == "prever_esgotamento_tanques"
    assert res_tanks["data"]["status"] == "ok"
    assert len(res_tanks["data"]["tanks"]) == 4

    # 2. Relatorio Oficial LMC ANP
    res_lmc = await engine.execute_tool_direct("gerar_relatorio_lmc_anp", {"data": "2026-10-15"})
    assert res_lmc["status"] == "success"
    assert res_lmc["tool_name"] == "gerar_relatorio_lmc_anp"
    assert res_lmc["data"]["status"] == "ok"
    assert len(res_lmc["data"]["tanques"]) == 4


def test_clean_room_stage4_3_zero_dashes():
    """Garante ausencia estrita de em-dash e en-dash neste arquivo de testes."""
    with open(__file__, "r", encoding="utf-8") as f:
        content = f.read()
    assert "\u2014" not in content, "Em-dash proibido encontrado no arquivo de testes"
    assert "\u2013" not in content, "En-dash proibido encontrado no arquivo de testes"
