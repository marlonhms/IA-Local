"""
Testes Unitarios do Bloco 4 (Etapa 4.4): Migracao de Pista e Desempenho de Bombas / Frentistas.
Valida o desacoplamento de PostoTools para consumo exclusivo do ERP Adapter e AUPS.
Assegura que nenhuma query SQL direta de abastecimentos ou bombas permaneca no PostoTools.
Regra inegociavel: ZERO travessoes em todo o arquivo.
"""

from __future__ import annotations

import inspect
from datetime import datetime

import pytest

from core.adapters.erp import MockERPAdapter
from core.aura_engine import AuraEngine
from core.domain.pumps import UniversalDispenserLog, UniversalPump
from core.schemas.pump_performance import PumpPerformanceContract
from core.tools import PostoTools


@pytest.fixture
def custom_pumps_mock_adapter():
    """Adaptador ERP Mock com massa deterministica calibrada para pista e frentistas."""
    adapter = MockERPAdapter()
    adapter.reset()

    # Bicos cadastrados no catalogo fisico
    p1 = UniversalPump(
        identificador_bomba="1",
        identificador_bico="1",
        identificador_tanque="1",
        codigo_combustivel="COMB_01",
        descricao_combustivel="Gasolina Comum",
        bomba_fisica="BOMBA 01",
        ativo=True,
        manual_permitido=False,
    )
    p2 = UniversalPump(
        identificador_bomba="1",
        identificador_bico="2",
        identificador_tanque="2",
        codigo_combustivel="COMB_02",
        descricao_combustivel="Gasolina Aditivada",
        bomba_fisica="BOMBA 01",
        ativo=True,
        manual_permitido=False,
    )
    p3 = UniversalPump(
        identificador_bomba="2",
        identificador_bico="3",
        identificador_tanque="4",
        codigo_combustivel="COMB_04",
        descricao_combustivel="Diesel S10",
        bomba_fisica="BOMBA 02",
        ativo=True,
        manual_permitido=False,
    )
    p4 = UniversalPump(
        identificador_bomba="2",
        identificador_bico="4",
        identificador_tanque="3",
        codigo_combustivel="COMB_03",
        descricao_combustivel="Etanol Hidratado",
        bomba_fisica="BOMBA 02",
        ativo=True,
        manual_permitido=False,
    )

    adapter._pumps_catalog = [p1, p2, p3, p4]

    # Abastecimentos detalhados na data 2026-10-15
    d1 = UniversalDispenserLog(
        controle="1001",
        identificador_bomba="1",
        identificador_bico="1",
        identificador_tanque="1",
        codigo_combustivel="COMB_01",
        descricao_combustivel="Gasolina Comum",
        turno_descricao="1º Turno",
        pdv="1",
        timestamp_registro=datetime(2026, 10, 15, 8, 30, 0),
        encerrante_inicial_litros=1000.0,
        encerrante_final_litros=1040.0,
        volume_litros=40.0,
        preco_unitario_reais=5.89,
        total_faturado_reais=235.60,
        operador_id="00010",
        operador_nome="JOAO CARLOS",
        duracao_segundos=60.0,
        tempo_descricao="00:01:00",
        venda_cancelada=False,
    )

    d2 = UniversalDispenserLog(
        controle="1002",
        identificador_bomba="1",
        identificador_bico="2",
        identificador_tanque="2",
        codigo_combustivel="COMB_02",
        descricao_combustivel="Gasolina Aditivada",
        turno_descricao="1º Turno",
        pdv="1",
        timestamp_registro=datetime(2026, 10, 15, 9, 15, 0),
        encerrante_inicial_litros=500.0,
        encerrante_final_litros=520.0,
        volume_litros=20.0,
        preco_unitario_reais=6.19,
        total_faturado_reais=123.80,
        operador_id="00010",
        operador_nome="JOAO CARLOS",
        duracao_segundos=30.0,
        tempo_descricao="00:00:30",
        venda_cancelada=False,
    )

    d3 = UniversalDispenserLog(
        controle="1003",
        identificador_bomba="2",
        identificador_bico="3",
        identificador_tanque="4",
        codigo_combustivel="COMB_04",
        descricao_combustivel="Diesel S10",
        turno_descricao="2º Turno",
        pdv="2",
        timestamp_registro=datetime(2026, 10, 15, 14, 0, 0),
        encerrante_inicial_litros=2000.0,
        encerrante_final_litros=2100.0,
        volume_litros=100.0,
        preco_unitario_reais=6.15,
        total_faturado_reais=615.00,
        operador_id="00012",
        operador_nome="MARCOS SOUZA",
        duracao_segundos=150.0,
        tempo_descricao="00:02:30",
        venda_cancelada=False,
    )

    # Anomalia 1: Micro-abastecimento (< 1.0 L)
    d4_micro = UniversalDispenserLog(
        controle="1004",
        identificador_bomba="1",
        identificador_bico="1",
        identificador_tanque="1",
        codigo_combustivel="COMB_01",
        descricao_combustivel="Gasolina Comum",
        turno_descricao="2º Turno",
        pdv="1",
        timestamp_registro=datetime(2026, 10, 15, 14, 30, 0),
        encerrante_inicial_litros=1040.0,
        encerrante_final_litros=1040.5,
        volume_litros=0.5,
        preco_unitario_reais=5.89,
        total_faturado_reais=2.95,
        operador_id="00012",
        operador_nome="MARCOS SOUZA",
        duracao_segundos=5.0,
        tempo_descricao="00:00:05",
        venda_cancelada=False,
    )

    # Anomalia 2: Abastecimento Manual
    d5_manual = UniversalDispenserLog(
        controle="1005",
        identificador_bomba="2",
        identificador_bico="4",
        identificador_tanque="3",
        codigo_combustivel="COMB_03",
        descricao_combustivel="Etanol Hidratado",
        turno_descricao="2º Turno",
        pdv="2",
        timestamp_registro=datetime(2026, 10, 15, 15, 0, 0),
        encerrante_inicial_litros=3000.0,
        encerrante_final_litros=3050.0,
        volume_litros=50.0,
        preco_unitario_reais=3.99,
        total_faturado_reais=199.50,
        operador_id="00012",
        operador_nome="MARCOS SOUZA",
        duracao_segundos=80.0,
        tempo_descricao="00:01:20",
        venda_cancelada=False,
        string_full="DIGITADO MANUAL NO PDV",
    )

    # Anomalia 3: Venda Cancelada
    d6_canc = UniversalDispenserLog(
        controle="1006",
        identificador_bomba="1",
        identificador_bico="1",
        identificador_tanque="1",
        codigo_combustivel="COMB_01",
        descricao_combustivel="Gasolina Comum",
        turno_descricao="2º Turno",
        pdv="1",
        timestamp_registro=datetime(2026, 10, 15, 15, 10, 0),
        encerrante_inicial_litros=1040.5,
        encerrante_final_litros=1055.5,
        volume_litros=15.0,
        preco_unitario_reais=5.89,
        total_faturado_reais=88.35,
        operador_id="00012",
        operador_nome="MARCOS SOUZA",
        duracao_segundos=25.0,
        tempo_descricao="00:00:25",
        venda_cancelada=True,
    )

    adapter._pumps = [d1, d2, d3, d4_micro, d5_manual, d6_canc]
    return adapter


def test_auditar_desempenho_pista_frentistas_mock(custom_pumps_mock_adapter):
    """Valida a auditoria completa de pista e frentistas com MockERPAdapter."""
    tools = PostoTools(erp_adapter=custom_pumps_mock_adapter)
    resultado = tools.auditar_desempenho_pista_frentistas(data="2026-10-15")

    assert resultado["status"] == "ok"
    assert "metrics" in resultado
    assert "ranking" in resultado
    assert "nozzles" in resultado
    assert "anomalies" in resultado
    assert "contrato" in resultado

    # Validacao do contrato Pydantic oficial
    contrato = PumpPerformanceContract.model_validate(resultado["contrato"])
    assert contrato.intent == "pump_performance"
    assert contrato.metrics.total_abastecimentos == 6
    assert contrato.metrics.total_litros > 0
    assert contrato.metrics.faturamento_total > 0

    # Ranking de frentistas
    ranking = resultado["ranking_frentistas"]
    assert len(ranking) >= 2
    nomes_ranking = [f["nome"] for f in ranking]
    assert "JOAO CARLOS" in nomes_ranking
    assert "MARCOS SOUZA" in nomes_ranking

    # Joao Carlos vendeu 40L Comum + 20L Aditivada -> Conversao de 33.33%
    joao = next(f for f in ranking if f["nome"] == "JOAO CARLOS")
    assert joao["conversao_aditivada_pct"] == pytest.approx(33.33, rel=1e-2)
    assert joao["litros_gasolina_aditivada"] == 20.0


def test_auditar_desempenho_pista_frentistas_filters(custom_pumps_mock_adapter):
    """Testa filtros especificos por bico, frentista e turno."""
    tools = PostoTools(erp_adapter=custom_pumps_mock_adapter)

    # Filtro por bico 1
    res_bico = tools.auditar_desempenho_pista_frentistas(data="2026-10-15", bico="1")
    assert res_bico["status"] == "ok"
    assert res_bico["periodo_analisado"]["bico_filtro"] == "1"

    # Filtro por frentista Joao
    res_frent = tools.auditar_desempenho_pista_frentistas(data="2026-10-15", frentista="JOAO")
    assert res_frent["status"] == "ok"

    # Filtro por turno
    res_turno = tools.auditar_desempenho_pista_frentistas(data="2026-10-15", turno="1º Turno")
    assert res_turno["status"] == "ok"


def test_nozzle_flow_speed_and_filter_alert(custom_pumps_mock_adapter):
    """Valida deteccao de bicos com vazao lenta e alerta de filtro obstruido."""
    tools = PostoTools(erp_adapter=custom_pumps_mock_adapter)

    # Fornecer medicao de vazao customizada simulando filtro entupido no bico 1 (22 L/min)
    res_lento = tools.auditar_desempenho_pista_frentistas(
        data="2026-10-15",
        vazao_bicos_custom={"1": 22.0}
    )
    assert res_lento["status"] == "ok"
    bicos = res_lento["auditoria_vazao_bicos"]
    bico1 = next(b for b in bicos if b["bico"] == "1")
    assert bico1["vazao_media_l_min"] == 22.0
    assert bico1["alerta_filtro_lento"] is True
    assert "Filtro Obstruído" in bico1["status_vazao"] or "Lento" in bico1["status_vazao"] or "CRÍTICO" in bico1["status_vazao"]


def test_piste_anomalies_detection(custom_pumps_mock_adapter):
    """Valida deteccao deterministica de anomalias de pista."""
    tools = PostoTools(erp_adapter=custom_pumps_mock_adapter)
    resultado = tools.auditar_desempenho_pista_frentistas(data="2026-10-15")

    anomalias = resultado["anomalias_detectadas"]
    tipos_anomalias = [a["tipo"] for a in anomalias]

    assert "MICRO_ABASTECIMENTO" in tipos_anomalias
    assert "ABASTECIMENTO_MANUAL" in tipos_anomalias
    assert "VENDA_CANCELADA" in tipos_anomalias


def test_clean_room_ast_inspection_no_sql():
    """Garante via inspecao de AST que nenhuma query SQL direta permaneca no PostoTools."""
    tools_source = inspect.getsource(PostoTools.auditar_desempenho_pista_frentistas)

    forbidden_patterns = [
        "SELECT ",
        "FROM abastecimentos",
        "FROM bombas",
        "LEFT JOIN funcionarios",
        "get_erp_connection()",
        "cursor(",
    ]

    for pattern in forbidden_patterns:
        assert pattern not in tools_source, f"Padrao SQL proibido encontrado em auditar_desempenho_pista_frentistas: '{pattern}'"

    # Confirma consumo exclusivo da porta universal do ERP
    assert "self.erp_adapter.get_pump_dispenses" in tools_source
    assert "self.erp_adapter.get_pumps_catalog" in tools_source


@pytest.mark.asyncio
async def test_aura_engine_execute_tool_direct_pumps(custom_pumps_mock_adapter):
    """Valida a integracao assincrona ponta a ponta atraves do AuraEngine."""
    engine = AuraEngine(erp_adapter=custom_pumps_mock_adapter)

    # Execucao direta da ferramenta
    res = await engine.execute_tool_direct(
        "auditar_desempenho_pista_frentistas",
        {"data": "2026-10-15"},
    )

    assert res["status"] == "success"
    assert res["tool_name"] == "auditar_desempenho_pista_frentistas"
    data = res["data"]
    assert data["status"] == "ok"
    assert "metrics" in data
    assert "ranking" in data
    assert data["metrics"]["total_abastecimentos"] == 6


def test_zero_travessoes_stage4_4():
    """Garante estrita conformidade com a regra de ZERO travessoes."""
    import pathlib

    test_file = pathlib.Path(__file__)
    content_test = test_file.read_text(encoding="utf-8")
    assert "\u2014" not in content_test, "Em-dash proibido encontrado no arquivo de testes!"
    assert "\u2013" not in content_test, "En-dash proibido encontrado no arquivo de testes!"

    pumps_domain = pathlib.Path("core/domain/pumps.py")
    content_pumps = pumps_domain.read_text(encoding="utf-8")
    assert "\u2014" not in content_pumps, "Em-dash proibido encontrado em core/domain/pumps.py!"
    assert "\u2013" not in content_pumps, "En-dash proibido encontrado em core/domain/pumps.py!"
