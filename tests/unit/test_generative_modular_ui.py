"""
Testes unitarios do Componente Modular Generativo (Blocos Lego UI - Fase 7+).
Valida contratos Pydantic, composicao em PostoTools, empacotamento no AuraEngine,
roteador semantico, contingencia inteligente e ausencia estrita de travessoes.
"""

import pytest

from core.aura_engine import AuraEngine, build_canonical_genui_envelope
from core.schemas.genui import (
    GenerativeModularProps,
    GenUIActionOption,
    GenUIEnvelope,
    LegoAlertItem,
    LegoBlock,
    LegoComparisonRow,
    LegoKpiItem,
    LegoRankingItem,
    LegoTimelineEvent,
)
from core.schemas.idempotency import generate_action_id, generate_tool_call_id
from core.semantic_router import classificar_intencao_heuristica
from core.tools import PostoTools


def test_lego_pydantic_schemas_validation():
    """Valida schemas Pydantic de todos os blocos Lego individuais e do props consolidado."""
    kpi = LegoKpiItem(
        label="Margem Bruta",
        value="16.4%",
        delta="+1.2 pp",
        trend="up",
        status="success",
        subtext="Meta: 15.0%",
    )
    assert kpi.label == "Margem Bruta"
    assert kpi.status == "success"

    comp_row = LegoComparisonRow(
        name="Gasolina Aditivada",
        primary_value="R$ 6,19",
        secondary_value="R$ 6,05",
        gap="+R$ 0,14",
        status="warning",
        observation="Acima da media",
    )
    assert comp_row.name == "Gasolina Aditivada"

    rank_item = LegoRankingItem(
        rank=1,
        title="Posto Matriz",
        subtitle="Bandeira Shell",
        value="R$ 15.800,00",
        tag="Lider da Cidade",
        status="success",
    )
    assert rank_item.rank == 1

    event = LegoTimelineEvent(
        timestamp="10:00",
        title="Sangria Efetuada",
        description="R$ 2.000,00 recolhidos para o cofre.",
        badge="Auditado",
        status="success",
    )
    assert event.timestamp == "10:00"

    alert = LegoAlertItem(
        severity="critical",
        title="Estoque Baixo",
        message="Tanque 02 abaixo do ponto de ressuprimento.",
        action_label="Pedir Carreta",
    )
    assert alert.severity == "critical"

    # Monta LegoBlock com cada tipo
    block_kpi = LegoBlock(
        block_id="b1",
        block_type="kpi_grid",
        title="Grid de KPIs",
        kpis=[kpi],
    )
    block_table = LegoBlock(
        block_id="b2",
        block_type="comparison_table",
        title="Tabela de Confronto",
        comparison_rows=[comp_row],
    )
    block_rank = LegoBlock(
        block_id="b3",
        block_type="ranking_list",
        title="Ranking de Unidades",
        ranking_items=[rank_item],
    )
    block_feed = LegoBlock(
        block_id="b4",
        block_type="timeline_feed",
        title="Linha do Tempo",
        timeline_events=[event],
    )
    block_alert = LegoBlock(
        block_id="b5",
        block_type="alert_callout",
        title="Alerta Urgente",
        alert=alert,
    )
    block_custom = LegoBlock(
        block_id="b6",
        block_type="custom_content",
        title="Nota do Especialista",
        custom_content="Analise ad-hoc cruzando vendas de conveniencia e picos de fluxo.",
    )

    props = GenerativeModularProps(
        title="Cockpit Executivo Generativo",
        subtitle="Composicao sob demanda",
        diagnosis="Operacao apresentando forte performance de vendas e atencao no tanque 02.",
        confidence_score=0.98,
        blocks=[block_kpi, block_table, block_rank, block_feed, block_alert, block_custom],
        limitations=["Dados parciais do turno da manha."],
        suggested_actions=[
            GenUIActionOption(
                action_id=generate_action_id(),
                label="Confirmar Pedido de Combustivel",
                action_type="mutation",
                variant="primary",
            )
        ],
    )
    assert len(props.blocks) == 6
    assert props.confidence_score == 0.98
    dumped = props.model_dump(mode="json")
    assert dumped["title"] == "Cockpit Executivo Generativo"
    assert len(dumped["blocks"]) == 6


def test_tools_compor_diagnostico_modular_defaults():
    """Valida geracao default de blocos lego quando nenhum bloco especifico e informado."""
    tools = PostoTools()
    res = tools.compor_diagnostico_modular()
    assert res.get("status") == "ok"
    assert res.get("intent") == "diagnostico_modular"
    assert res.get("component_name") == "render_GenerativeModularCardUI"
    assert res.get("client_component") == "GenerativeModularCardUI"
    assert "props" in res
    props = res["props"]
    assert "title" in props
    assert "diagnosis" in props
    assert len(props["blocks"]) == 5

    block_types = [b["block_type"] for b in props["blocks"]]
    assert "kpi_grid" in block_types
    assert "alert_callout" in block_types
    assert "comparison_table" in block_types
    assert "ranking_list" in block_types
    assert "timeline_feed" in block_types

    assert len(res.get("suggested_actions", [])) >= 2


def test_tools_compor_diagnostico_modular_custom_blocks():
    """Valida composicao com blocos customizados sob medida."""
    tools = PostoTools()
    custom_kpi = LegoBlock(
        block_id="b_custom_1",
        block_type="kpi_grid",
        title="Metricas de Conveniencia",
        kpis=[
            LegoKpiItem(label="Ticket Medio", value="R$ 38,50", trend="up", status="success")
        ],
    )
    res = tools.compor_diagnostico_modular(
        titulo="Analise de Cross-Selling",
        subtitulo="PDV e Cafeteria",
        diagnostico="Sinergia observada entre expressos e pao de queijo.",
        confidence_score=0.92,
        blocos=[custom_kpi],
    )
    assert res.get("status") == "ok"
    props = res["props"]
    assert props["title"] == "Analise de Cross-Selling"
    assert len(props["blocks"]) == 1
    assert props["blocks"][0]["block_id"] == "b_custom_1"


def test_build_canonical_genui_envelope_generative_modular():
    """Valida criacao do envelope canonico GenUI para render_GenerativeModularCardUI."""
    tools = PostoTools()
    raw = tools.compor_diagnostico_modular()
    tool_call_id = generate_tool_call_id()

    envelope = build_canonical_genui_envelope(
        intencao="diagnostico_modular",
        tool_call_id=tool_call_id,
        resultado_bruto=raw,
        executive_summary="Resumo de briefing generativo",
    )
    assert envelope is not None
    assert isinstance(envelope, GenUIEnvelope)
    assert envelope.component_name == "render_GenerativeModularCardUI"
    assert envelope.client_component == "GenerativeModularCardUI"
    assert len(envelope.props["blocks"]) == 5
    assert len(envelope.actions) >= 2


def test_semantic_router_heuristics_modular():
    """Valida classificacao heuristica das intencoes de diagnostico modular e blocos lego."""
    queries = [
        "monte um diagnostico modular para a diretoria",
        "preciso de um card modular de lego",
        "visao modular dos indicadores de pista",
        "gere um componente generativo modular",
        "diagnostico_modular",
        "blocos lego",
    ]
    for q in queries:
        assert classificar_intencao_heuristica(q) == "diagnostico_modular"


def test_engine_sintese_contingencia_genui_active_and_inactive():
    """Valida a diretriz Intelligent UI: briefing executivo conciso com Canvas ativo vs detalhado no chat."""
    tools = PostoTools()
    raw = tools.compor_diagnostico_modular(
        titulo="Painel de Desempenho",
        diagnostico="Vendas acima da meta com atencao no caixa.",
    )
    engine = AuraEngine()

    # Com Canvas ativo (genui_active=True): briefing executivo sem duplicar densidade
    sintese_on = engine._gerar_sintese_contingencia_ferramenta(
        intencao="diagnostico_modular",
        resultado_bruto=raw,
        pergunta="mostrar diagnostico modular",
        genui_active=True,
    )
    assert "painel interativo ao lado" in sintese_on
    assert "Composicao Modular:" in sintese_on
    assert "Blocos Modulares Ativos:" not in sintese_on

    # Sem Canvas (genui_active=False): saida rica com resumo de blocos
    sintese_off = engine._gerar_sintese_contingencia_ferramenta(
        intencao="diagnostico_modular",
        resultado_bruto=raw,
        pergunta="mostrar diagnostico modular",
        genui_active=False,
    )
    assert "Blocos Modulares Ativos" in sintese_off


@pytest.mark.asyncio
async def test_engine_execute_tool_direct_modular():
    """Valida execucao direta assincrona via execute_tool_direct."""
    engine = AuraEngine()
    res = await engine.execute_tool_direct("diagnostico_modular", {
        "titulo": "Painel Assincrono",
        "diagnostico": "Teste de chamada assincrona direta.",
    })
    assert res.get("status") == "success"
    assert res.get("tool_name") == "diagnostico_modular"
    data = res.get("data", {})
    assert data.get("component_name") == "render_GenerativeModularCardUI"
    assert data.get("props", {}).get("title") == "Painel Assincrono"


def test_ausencia_travessoes_modular():
    """Garante ausencia estrita de travessoes Unicode (\\u2014, \\u2013) em todos os arquivos tocados."""
    arquivos_validar = [
        "core/schemas/genui.py",
        "core/tools.py",
        "core/aura_engine.py",
        "core/semantic_router.py",
        "web/js/aura-genui-widgets.js",
        "web-frontend/src/types/aura-contracts.ts",
        "tests/unit/test_generative_modular_ui.py",
    ]
    for rel_path in arquivos_validar:
        with open(rel_path, "r", encoding="utf-8") as f:
            content = f.read()
        for idx, char in enumerate(content):
            if char in ("\u2014", "\u2013"):
                line_no = content[:idx].count("\n") + 1
                pytest.fail(f"Travessao proibido '\\u{ord(char):04x}' encontrado em {rel_path}:{line_no}")
