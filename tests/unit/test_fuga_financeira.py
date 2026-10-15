"""
Testes Unitarios: Auditoria de Fuga Financeira & Conciliacao TEF (Micro-Widget FinancialLeakAuditUI).
Valida o motor analitico deterministico de deteccao de furos de gaveta,
sangrias anomalas retidas no caixa, divergencias de conciliacao de cartoes TEF
e cancelamentos suspeitos de alto valor, contratos Pydantic (FinancialLeakAuditProps,
FinancialLeakItem), integracao ao SemanticRouter, AuraEngine e gerador de sintese.
Zero travessoes em todo o arquivo.
"""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from core.aura_engine import AuraEngine
from core.domain.cashier import UniversalCashierShift
from core.domain.sales import UniversalPaymentMethod, UniversalSaleReceipt
from core.schemas.genui import FinancialLeakAuditProps, FinancialLeakItem
from core.semantic_router import classificar_intencao_heuristica
from core.tools import PostoTools


@pytest.fixture
def posto_tools():
    return PostoTools(rag_engine=MagicMock())


@pytest.fixture
def aura_engine(posto_tools):
    mock_rag = MagicMock()
    mock_router = MagicMock()
    return AuraEngine(rag_engine=mock_rag, router=mock_router, tools=posto_tools)


def test_auditar_fuga_financeira_fallback_offline(posto_tools):
    """Valida a execucao do motor deterministico em cenario offline/fallback calibrado."""
    with patch.object(posto_tools.erp_adapter, "get_cashier_shifts", side_effect=Exception("DB Offline")):
        resultado = posto_tools.auditar_fuga_financeira()

    assert resultado["status"] == "ok"
    assert resultado["intent"] == "auditoria_fuga_financeira"
    assert resultado["component_name"] == "render_FinancialLeakAuditUI"
    assert resultado["client_component"] == "FinancialLeakAuditUI"
    assert resultado["fonte_dados"] == "AUDITORIA_CALIBRADA"

    # Validacao estrita do contrato Pydantic canonico
    props = FinancialLeakAuditProps(**resultado["props"])
    assert props.confidence_score >= 0.85
    assert props.confidence_score <= 1.0
    assert props.severity in ("normal", "attention", "critical")
    assert props.risk_level in ("baixo", "medio", "critico")
    assert props.total_leak_value >= 0.0
    assert props.total_divergence_reais >= 0.0
    assert props.total_leak_value == props.total_divergence_reais
    assert props.cash_break_value >= 0.0
    assert props.pending_bleed_value >= 0.0
    assert props.tef_divergence_value >= 0.0
    assert len(props.diagnosis) > 0
    assert len(props.leak_items) >= 4
    assert len(props.suggested_actions) >= 3
    assert len(props.limitations) >= 2

    # Verifica presenca de todos os vetores de fuga auditados
    categories = [it.category for it in props.leak_items]
    assert "Quebra de Caixa" in categories
    assert "Sangria Pendente" in categories
    assert "TEF Cartao" in categories
    assert "Cancelamento Suspeito" in categories

    # Verifica integridade individual de cada item
    for it in props.leak_items:
        assert it.amount >= 0.0
        assert it.status in ("critical", "warning", "resolved", "investigating")
        assert it.leak_type == it.category
        assert it.amount_reais == it.amount
        assert it.source == it.pdv_or_terminal
        assert len(it.description) > 0
        assert len(it.mitigation_action) > 0


def test_auditar_fuga_financeira_real_db_divergence(posto_tools):
    """Valida deteccao real de quebra de caixa e divergencia TEF com dados do ERP."""
    # Data 2026-09-02 possui quebra de caixa real registrada
    resultado = posto_tools.auditar_fuga_financeira(data="2026-09-02")
    assert resultado["status"] == "ok"
    assert resultado["fonte_dados"] in ("ERP_POSTGRESQL", "AUDITORIA_CALIBRADA")
    props = FinancialLeakAuditProps(**resultado["props"])
    assert props.total_leak_value > 0.0
    assert props.audited_shift is not None
    assert len(props.suggested_actions) >= 2


def test_auditar_fuga_financeira_conformidade_sem_divergencias(posto_tools):
    """Valida diagnostico de conformidade quando nao ha quebras de caixa ou descompasso TEF."""
    mock_shift = UniversalCashierShift(
        caixa_id="1",
        pdv="001",
        turno_descricao="1",
        operador_id="0001",
        operador_nome="OPERADOR TESTE",
        fechado=True,
        dinheiro_declarado_reais=100.0,
        cartao_declarado_reais=200.0,
        prazo_declarado_reais=0.0,
        convenio_cheque_reais=0.0,
        total_declarado_reais=300.0,
        venda_combustivel_reais=300.0,
        venda_produtos_reais=0.0,
        litros_declarados=50.0,
    )
    mock_sales = [
        UniversalSaleReceipt(
            cupom_id="1",
            pdv="001",
            total_reais=100.0,
            status="CONCLUIDA",
            pagamentos=[
                UniversalPaymentMethod(
                    codigo_forma_pagamento="1",
                    descricao_forma="DINHEIRO",
                    tipo="dinheiro",
                    valor_reais=100.0,
                )
            ],
        ),
        UniversalSaleReceipt(
            cupom_id="2",
            pdv="001",
            total_reais=200.0,
            status="CONCLUIDA",
            pagamentos=[
                UniversalPaymentMethod(
                    codigo_forma_pagamento="2",
                    descricao_forma="CARTAO_PIX",
                    tipo="credito",
                    valor_reais=200.0,
                )
            ],
        ),
    ]

    with patch.object(posto_tools.erp_adapter, "get_cashier_shifts", return_value=[mock_shift]), \
         patch.object(posto_tools.erp_adapter, "get_recent_sales", return_value=mock_sales):
        resultado = posto_tools.auditar_fuga_financeira(data="2026-10-14")
        assert resultado["status"] == "ok"
        assert resultado["fonte_dados"] == "ERP_POSTGRESQL"
        assert resultado["total_divergence_reais"] == 0.0
        assert resultado["risk_level"] == "baixo"
        assert "conformidade" in resultado["diagnosis"].lower()
        props = FinancialLeakAuditProps(**resultado["props"])
        assert props.severity == "normal"
        assert len(props.leak_items) == 0


def test_auditar_fuga_financeira_custom_tolerance(posto_tools):
    """Valida customizacao de tolerancia de quebra de caixa e teto de gaveta."""
    with patch.object(posto_tools.erp_adapter, "get_cashier_shifts", side_effect=Exception("DB Offline")):
        resultado = posto_tools.auditar_fuga_financeira(
            cash_tolerance_reais=100.0,
            max_safe_cash_drawer=1000.0,
            data="2026-09-02",
            turno="1",
            pdv="01",
        )

    assert resultado["status"] == "ok"
    props = FinancialLeakAuditProps(**resultado["props"])
    assert props.total_leak_value > 0.0
    assert props.audited_shift is not None


def test_financial_leak_item_aliases_and_validation():
    """Valida bidirecionalidade de aliases e validacoes de FinancialLeakItem."""
    # Instanciacao via campos canonicos do prompt
    item = FinancialLeakItem(
        leak_type="Quebra de Caixa",
        amount_reais=150.75,
        severity="critical",
        source="PDV 03",
        description="Furo constatado na conferencia fisica da gaveta",
        mitigation_action="Bloquear operador e acionar supervisor",
    )
    assert item.category == "Quebra de Caixa"
    assert item.amount == 150.75
    assert item.status == "critical"
    assert item.pdv_or_terminal == "PDV 03"
    assert item.leak_type == "Quebra de Caixa"
    assert item.amount_reais == 150.75
    assert item.severity == "critical"
    assert item.source == "PDV 03"

    # Rejeicao de valor negativo
    with pytest.raises(ValidationError):
        FinancialLeakItem(
            category="Quebra de Caixa",
            description="Valor invalido",
            amount=-10.0,
        )


def test_financial_leak_props_aliases_and_validation():
    """Valida bidirecionalidade de aliases e validacoes de FinancialLeakAuditProps."""
    item = FinancialLeakItem(
        category="TEF Cartao",
        description="Transacao TEF descompassada",
        amount=45.0,
        status="warning",
        pdv_or_terminal="POS 02",
    )
    props = FinancialLeakAuditProps(
        diagnosis="Divergencia identificada no lote TEF",
        risk_level="critico",
        confidence_score=0.96,
        total_divergence_reais=45.0,
        cash_break_value=0.0,
        pending_bleed_value=0.0,
        tef_divergence_value=45.0,
        leak_items=[item],
    )
    assert props.severity == "critical"
    assert props.risk_level == "critico"
    assert props.total_leak_value == 45.0
    assert props.total_divergence_reais == 45.0

    # Rejeicao de diagnosis vazio
    with pytest.raises(ValidationError):
        FinancialLeakAuditProps(
            diagnosis="",
            confidence_score=0.95,
            total_leak_value=10.0,
        )


def test_gerar_diagnostico_mentoria_executiva_delegation(posto_tools):
    """Valida delegacao de mentoria executiva para auditar_fuga_financeira."""
    aliases = [
        "auditoria_fuga_financeira",
        "fuga_financeira",
        "fugas_financeiras",
        "auditoria_quebras",
        "fugas",
    ]
    with patch.object(posto_tools.erp_adapter, "get_cashier_shifts", side_effect=Exception("DB Offline")):
        for alias in aliases:
            res = posto_tools.gerar_diagnostico_mentoria_executiva(tipo=alias)
            assert res["status"] == "ok"
            assert res["intent"] == "auditoria_fuga_financeira"
            assert res["client_component"] == "FinancialLeakAuditUI"
            assert "props" in res
            assert "total_divergence_reais" in res
            assert res["total_divergence_reais"] > 0.0


def test_semantic_router_fuga_financeira():
    """Valida roteamento semantico heuristico para termos de fuga financeira."""
    frases_teste = [
        "auditoria de fuga financeira no caixa",
        "auditar quebras de caixa do turno da manha",
        "tem sangria anomala retida no pdv?",
        "sangria anômala identificada",
        "houve sangria suspeita hoje?",
        "alerta de sangrias pendentes",
        "verificar divergência tef na pista",
        "divergencia tef entre maquinetas e fechamento",
        "apurar desvio de caixa",
        "furo de gaveta no pdv 01",
        "conferir furos de caixa",
        "bloquear terminal suspeito",
    ]
    for frase in frases_teste:
        intencao = classificar_intencao_heuristica(frase)
        assert intencao == "auditoria_fuga_financeira", f"Frase '{frase}' roteou para '{intencao}'"


@pytest.mark.asyncio
async def test_aura_engine_execute_tool_direct_and_contingency(posto_tools):
    """Valida execucao direta de ferramenta e sintese de contingencia rica no AuraEngine."""
    with patch.object(posto_tools.erp_adapter, "get_cashier_shifts", side_effect=Exception("DB Offline")):
        engine = AuraEngine(tools=posto_tools)

        # 1. Execucao direta no AuraEngine
        res = await engine.execute_tool_direct(
            tool_name="auditoria_fuga_financeira",
            params={"cash_tolerance_reais": 40.0},
        )
        assert res["status"] == "success"
        assert res["tool_name"] == "auditoria_fuga_financeira"
        assert "data" in res
        data_res = res["data"]
        assert data_res["client_component"] == "FinancialLeakAuditUI"
        assert data_res["total_divergence_reais"] > 0.0

        # 2. Aliases em execute_tool_direct
        for alias in ["fuga_financeira", "furo_caixa", "auditoria_quebras"]:
            res_alias = await engine.execute_tool_direct(
                tool_name=alias,
                params={},
            )
            assert res_alias["status"] == "success"

        # 3. Sintese executiva de contingencia rica
        sintese = engine._gerar_sintese_contingencia_ferramenta(
            intencao="auditoria_fuga_financeira",
            resultado_bruto=data_res,
            pergunta="auditoria de fuga financeira",
        )
        assert sintese is not None
        assert "Auditoria de Fuga Financeira & Conciliação TEF" in sintese
        assert "Quebra de Caixa" in sintese
        assert "Sangrias Pendentes" in sintese
        assert "Divergência de Conciliação TEF" in sintese
        assert "R$" in sintese
        assert "Ações Recomendadas (HITL)" in sintese

        # Inegociavel: Zero travessoes (verificado via escape unicode sem conter os caracteres literais no arquivo)
        assert "\u2014" not in sintese, "Sintese nao pode conter em-dash"
        assert "\u2013" not in sintese, "Sintese nao pode conter en-dash"


def test_erp_read_only_access_in_tools_file():
    """Garante que a ferramenta auditar_fuga_financeira executa exclusivamente atraves do ERP Adapter."""
    import inspect
    source = inspect.getsource(PostoTools.auditar_fuga_financeira)

    # Verifica ausencia de operacoes de escrita
    prohibited_keywords = ["INSERT ", "UPDATE ", "DELETE ", "DROP ", "ALTER ", "TRUNCATE "]
    for kw in prohibited_keywords:
        assert kw not in source.upper(), f"Palavra proibida de mutacao encontrada: {kw}"

    # Verifica desacoplamento clean-room: consumo do erp_adapter sem SQL direto
    assert "erp_adapter" in source.lower(), "Metodo deve delegar para o erp_adapter"
    assert "get_erp_connection" not in source, "Metodo nao deve abrir conexao SQL direta"
    assert "SELECT " not in source.upper(), "Metodo nao deve conter queries SQL brutas"
