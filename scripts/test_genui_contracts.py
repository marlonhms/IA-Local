"""
Suite de Testes Automatizada: Validacao de Contratos GenUI e Schemas Pydantic v2 (Fase 8: F8-01)
Valida a serializacao, tipagem estrita, imutabilidade, idempotencia e robustez de todos os contratos:
- GenUIActionOption, GenUIEnvelope, GenUIActionResult, IdempotencyKey.
- ExecutiveDecisionProps, MarginAnalysisProps, PredictiveScenarioProps,
  BenchmarkComparisonProps, FinancialLeakAuditProps, BasketUpsellStrategyProps.
- ActionExecuteRequest, ActionVoucher e verificacao HMAC-SHA256.
- Rejeicao de IDs invalidos, coercao de tipos, aliases e to_sse_payload().
- Zero travessoes nos textos e logs.
"""

from __future__ import annotations

import sys
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List

# Protege stdout no terminal Windows contra problemas de codificacao
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from pydantic import ValidationError

from core.schemas.idempotency import (
    generate_uuid4,
    generate_tool_call_id,
    generate_action_id,
    is_valid_uuid4,
    validate_tool_call_id,
    validate_action_id,
    IdempotencyKey,
)
from core.schemas.genui import (
    GenUIActionOption,
    GenUIEnvelope,
    GenUIActionResult,
    WidgetStateRecord,
    WidgetActionExecution,
    ActionExecuteRequest,
    ActionVoucher,
    ActionAuditLogRecord,
    generate_action_voucher_signature,
    verify_action_voucher_signature,
    ExecutiveMetric,
    ExecutiveImpactProjection,
    ExecutiveEvidenceItem,
    ExecutiveDecisionProps,
    FuelMarginItem,
    PaymentFeeImpactItem,
    MarginAnalysisProps,
    ScenarioPoint,
    PredictiveScenarioProps,
    BenchmarkComparisonItem,
    BenchmarkComparisonProps,
    FinancialLeakItem,
    FinancialLeakAuditProps,
    UpsellComboItem,
    BasketUpsellStrategyProps,
)


def test_idempotency_contracts():
    print("\n1. Testando Contratos de Idempotencia e Validadores RFC 4122 v4...")

    u = generate_uuid4()
    assert is_valid_uuid4(u, allow_prefix=False)

    # Prefixos validos para tool_call
    tool_id = generate_tool_call_id()
    assert tool_id.startswith("call_")
    assert validate_tool_call_id(tool_id)
    assert validate_tool_call_id(f"tool_call_{u}")
    assert validate_tool_call_id(f"tool_{u}")
    assert validate_tool_call_id(u, require_prefix=False)

    # Prefixos validos para action
    act_id = generate_action_id()
    assert act_id.startswith("act_")
    assert validate_action_id(act_id)
    assert validate_action_id(f"action_{u}")
    assert validate_action_id(u, require_prefix=False)

    # Rejeicao de prefixos cruzados
    assert not validate_tool_call_id(act_id)
    assert not validate_action_id(tool_id)

    # Rejeicao de IDs adulterados ou com payloads maliciosos
    invalid_ids = [
        "call_<script>alert(1)</script>",
        "act_' OR '1'='1",
        "invalid-uuid-value",
        "call_12345",
        "act_12345678-1234-1234-1234-123456789abc", # version 1, not version 4
        "",
        "   ",
        None,
    ]
    for inv in invalid_ids:
        assert not validate_tool_call_id(inv)
        assert not validate_action_id(inv)

    # IdempotencyKey Model
    key = IdempotencyKey(tool_call_id=tool_id, action_id=act_id)
    assert key.tool_call_id == tool_id
    assert key.action_id == act_id

    # Teste de IdempotencyKey sem action_id
    key_no_act = IdempotencyKey(tool_call_id=tool_id)
    assert key_no_act.tool_call_id == tool_id
    assert key_no_act.action_id is None

    # Rejeicao de IDs invalidos no IdempotencyKey
    try:
        IdempotencyKey(tool_call_id="invalid_prefix_uuid", action_id=act_id)
        assert False, "IdempotencyKey deveria rejeitar tool_call_id invalido"
    except ValidationError:
        pass

    try:
        IdempotencyKey(tool_call_id=tool_id, action_id="invalid_act_id")
        assert False, "IdempotencyKey deveria rejeitar action_id invalido"
    except ValidationError:
        pass

    print("   [OK] IdempotencyKey e validadores RFC 4122 v4 aprovados.")


def test_genui_action_option_contract():
    print("\n2. Testando GenUIActionOption (Camada 3: Action Sheets)...")

    act_id = generate_action_id()
    opt = GenUIActionOption(
        action_id=act_id,
        label="Homologar Pedido de Combustivel",
        action_type="mutation",
        variant="primary",
        is_destructive=False,
        requires_confirmation=True,
        payload={"litros": 15000, "combustivel": "Gasolina Comum"}
    )
    assert opt.action_id == act_id
    assert opt.label == "Homologar Pedido de Combustivel"
    assert opt.action_type == "mutation"
    assert opt.variant == "primary"
    assert opt.is_destructive is False
    assert opt.requires_confirmation is True
    assert opt.payload["litros"] == 15000

    # Imutabilidade (frozen=True)
    try:
        opt.label = "Outro Label"  # type: ignore
        assert False, "GenUIActionOption deveria ser imutavel (frozen)"
    except (TypeError, ValidationError):
        pass

    # Rejeicao de action_id invalido (prefixo call_)
    try:
        GenUIActionOption(
            action_id=generate_tool_call_id(),
            label="Acao Invalida"
        )
        assert False, "GenUIActionOption deveria rejeitar prefixo call_"
    except ValidationError:
        pass

    # Rejeicao de label vazio ou espacos
    try:
        GenUIActionOption(action_id=act_id, label="   ")
        assert False, "GenUIActionOption deveria rejeitar label vazio"
    except ValidationError:
        pass

    # Rejeicao de action_type invalido
    try:
        GenUIActionOption(action_id=act_id, label="Teste", action_type="invalid_type")  # type: ignore
        assert False, "GenUIActionOption deveria rejeitar action_type desconhecido"
    except ValidationError:
        pass

    # Rejeicao de variant invalido
    try:
        GenUIActionOption(action_id=act_id, label="Teste", variant="neon_glow")  # type: ignore
        assert False, "GenUIActionOption deveria rejeitar variant desconhecido"
    except ValidationError:
        pass

    print("   [OK] GenUIActionOption validado com imutabilidade e rejeicao estrita.")


def test_genui_envelope_contract():
    print("\n3. Testando GenUIEnvelope (Envelope Canonico Universal)...")

    tool_id = generate_tool_call_id()
    act_id = generate_action_id()
    action = GenUIActionOption(action_id=act_id, label="Acao Primaria")

    props_data = {
        "diagnosis": "Diagnostico operacional sob controle",
        "confidence_score": 0.98,
        "metrics": [{"label": "Margem", "current_value": 14.5}]
    }

    env = GenUIEnvelope(
        schema_version="1.0",
        tool_call_id=tool_id,
        component_name="render_ExecutiveDecisionMentorUI",
        client_component="ExecutiveDecisionMentorUI",
        intent="mentoria_decisao",
        executive_summary="Resumo executivo emitido via streaming.",
        props=props_data,
        actions=[action],
        ttl_seconds=900
    )

    assert env.tool_call_id == tool_id
    assert env.component_name == "render_ExecutiveDecisionMentorUI"
    assert env.intent == "mentoria_decisao"
    assert env.executive_summary == "Resumo executivo emitido via streaming."
    assert env.props["confidence_score"] == 0.98
    assert len(env.actions) == 1
    assert env.ttl_seconds == 900
    assert env.created_at is not None

    # Teste de Aliases (envelope_version, summary_text, timestamp)
    env_from_aliases = GenUIEnvelope(
        envelope_version="1.0",
        tool_call_id=tool_id,
        component_name="render_ExecutiveDecisionMentorUI",
        intent="mentoria_decisao",
        summary_text="Resumo por alias",
        props=props_data,
        timestamp="2026-10-08T18:00:00Z"
    )
    assert env_from_aliases.schema_version == "1.0"
    assert env_from_aliases.executive_summary == "Resumo por alias"
    assert env_from_aliases.created_at == "2026-10-08T18:00:00Z"

    # to_sse_payload()
    sse_payload = env.to_sse_payload()
    assert sse_payload["envelope_version"] == "1.0"
    assert sse_payload["summary_text"] == env.executive_summary
    assert sse_payload["timestamp"] == env.created_at
    assert sse_payload["tool_call_id"] == tool_id
    assert sse_payload["props"]["confidence_score"] == 0.98

    # to_json()
    json_str = env.to_json()
    parsed_json = json.loads(json_str)
    assert parsed_json["tool_call_id"] == tool_id

    # JSON Schema para Guided Decoding (vLLM)
    schema_dict = GenUIEnvelope.model_json_schema()
    assert "properties" in schema_dict
    assert "tool_call_id" in schema_dict["properties"]
    assert "executive_summary" in schema_dict["properties"]
    assert "props" in schema_dict["properties"]

    # Rejeicao de component_name inseguro / injection
    bad_component_names = [
        "<script>alert(1)</script>",
        "drop table postos;",
        "a", # menos de 3 chars
        "123_invalid_start",
        "component with spaces",
    ]
    for b_comp in bad_component_names:
        try:
            GenUIEnvelope(
                tool_call_id=tool_id,
                component_name=b_comp,
                executive_summary="Resumo",
                props=props_data
            )
            assert False, f"GenUIEnvelope deveria rejeitar component_name: {b_comp}"
        except ValidationError:
            pass

    # Rejeicao de ttl_seconds <= 0
    try:
        GenUIEnvelope(
            tool_call_id=tool_id,
            component_name="render_ExecutiveDecisionMentorUI",
            executive_summary="Resumo",
            props=props_data,
            ttl_seconds=0
        )
        assert False, "GenUIEnvelope deveria rejeitar ttl_seconds <= 0"
    except ValidationError:
        pass

    # Imutabilidade
    try:
        env.executive_summary = "Outro resumo"  # type: ignore
        assert False, "GenUIEnvelope deveria ser imutavel"
    except (TypeError, ValidationError):
        pass

    print("   [OK] GenUIEnvelope, aliases, to_sse_payload() e schema json validados com sucesso.")


def test_micro_widgets_props_contracts():
    print("\n4. Testando Contratos de Props dos 6 Micro-Widgets do Catalogo...")

    act_id = generate_action_id()
    action = GenUIActionOption(action_id=act_id, label="Acao de Teste")

    # 4.1 ExecutiveDecisionProps (Piloto)
    m1 = ExecutiveMetric(
        label="Margem Liquida Real",
        current_value=13.8,
        benchmark_value=14.0,
        trend="down",
        status="warning",
        unit="%",
        delta_percent=-1.43
    )
    imp = ExecutiveImpactProjection(
        summary="Impacto projetado de R$ 3.500 no fechamento mensal",
        estimated_financial_impact=-3500.0,
        timeframe="mensal",
        confidence=0.92
    )
    evi = ExecutiveEvidenceItem(
        title="Lote TEF Cartoes",
        detail="Taxa media cobrada de 2.45% no debito/credito",
        value="2.45%",
        source="adquirente_local"
    )
    exec_props = ExecutiveDecisionProps(
        diagnosis="Margem liquida em queda devido a taxas de cartao.",
        confidence_score=0.94,
        metrics=[m1],
        limitations="Dados sem conciliacao bancaria final", # Teste de coercao de string simples para lista
        impact_projection=imp,
        evidence_items=[evi],
        suggested_actions=[action]
    )
    assert exec_props.confidence_score == 0.94
    assert isinstance(exec_props.limitations, list)
    assert len(exec_props.limitations) == 1
    assert exec_props.limitations[0] == "Dados sem conciliacao bancaria final"
    assert len(exec_props.metrics) == 1

    # Rejeicao de confidence_score fora do intervalo [0.0, 1.0]
    try:
        ExecutiveDecisionProps(
            diagnosis="Diagnostico",
            confidence_score=1.5
        )
        assert False, "ExecutiveDecisionProps deveria rejeitar confidence_score > 1.0"
    except ValidationError:
        pass

    # 4.2 MarginAnalysisProps (F6-01)
    fm = FuelMarginItem(
        combustivel="Diesel S10",
        volume_litros=25000.0,
        preco_venda=6.19,
        custo_aquisicao=5.40,
        margem_liquida_pct=12.76,
        margem_alvo_pct=14.0,
        benchmark_mercado=6.15,
        elasticidade="Baixa"
    )
    fee = PaymentFeeImpactItem(
        modalidade="Voucher Frota",
        taxa_media_pct=3.80,
        volume_financeiro=45000.0,
        desconto_taxas_reais=1710.0,
        impacto_margem_pct=2.10
    )
    margin_props = MarginAnalysisProps(
        diagnosis="Margem liquida real consolidada em 12.8%.",
        confidence_score=0.96,
        consolidated_margin_pct=12.8,
        target_margin_pct=14.5,
        gross_revenue=350000.0,
        net_profit=44800.0,
        fuel_margins=[fm],
        payment_fee_impact=[fee],
        limitations=["Conciliacao parcial de notas"],
        suggested_actions=[action]
    )
    assert margin_props.consolidated_margin_pct == 12.8
    assert len(margin_props.fuel_margins) == 1
    assert len(margin_props.payment_fee_impact) == 1

    # 4.3 PredictiveScenarioProps (F6-02)
    sp_base = ScenarioPoint(
        preco_medio=5.89,
        volume_projetado=80000.0,
        receita_liquida=471200.0,
        margem_contribuicao_pct=14.2
    )
    sp_sim = ScenarioPoint(
        preco_medio=5.99,
        volume_projetado=79200.0,
        receita_liquida=474408.0,
        margem_contribuicao_pct=15.1
    )
    pred_props = PredictiveScenarioProps(
        scenario_title="Simulacao de Repasse de R$ 0,10 no Preco",
        hypothesis="Aumento de R$ 0,10 compensa perda marginal de 1% no volume",
        base_scenario=sp_base,
        simulated_scenario=sp_sim,
        delta_volume_pct=-1.0,
        delta_revenue=3208.0,
        delta_margin_pct=0.9,
        confidence_score=0.91,
        diagnosis="Repasse de R$ 0,10 resulta em ganho liquido de R$ 3.208,00.",
        elasticity_coefficient=-0.59,
        assumptions=["Concorrentes no raio de 3km nao baixam precos"],
        limitations=["Cenario valido para ate 14 dias"],
        suggested_actions=[action]
    )
    assert pred_props.delta_volume_pct == -1.0
    assert pred_props.base_scenario.preco_medio == 5.89

    # 4.4 BenchmarkComparisonProps (F6-03)
    b_item = BenchmarkComparisonItem(
        kpi_name="Preco Gasolina Comum",
        filial_value="R$ 5,89",
        benchmark_value="R$ 5,79",
        gap_value="+R$ 0,10",
        status="warning",
        observation="Filial 10 centavos acima da media regional"
    )
    bench_props = BenchmarkComparisonProps(
        diagnosis="Filial posicionada no quartil superior de preco com leve perda de giro.",
        confidence_score=0.88,
        competitiveness_score=78.5,
        entity_name="Posto Central - Filial 01",
        benchmark_group="Concorrentes Raio 3km",
        market_position="3º de 9 postos",
        comparison_items=[b_item],
        limitations=["Pesquisa de precos manual de 24h atras"],
        suggested_actions=[action]
    )
    assert bench_props.competitiveness_score == 78.5
    assert len(bench_props.comparison_items) == 1

    # Rejeicao de competitiveness_score > 100
    try:
        BenchmarkComparisonProps(
            diagnosis="Diagnostico",
            confidence_score=0.9,
            competitiveness_score=150.0,
            entity_name="Posto",
            benchmark_group="Grupo"
        )
        assert False, "BenchmarkComparisonProps deveria rejeitar competitiveness_score > 100"
    except ValidationError:
        pass

    # 4.5 FinancialLeakAuditProps (F6-04)
    leak_item = FinancialLeakItem(
        category="Quebra de Caixa",
        description="Diferenca entre sangrias e soma das vendas fiscais no PDV 02",
        amount=142.50,
        status="critical",
        pdv_or_terminal="PDV-02"
    )
    leak_props = FinancialLeakAuditProps(
        diagnosis="Identificada quebra de caixa anomala de R$ 142,50 no Turno B.",
        severity="critical",
        confidence_score=0.97,
        total_leak_value=142.50,
        cash_break_value=142.50,
        pending_bleed_value=0.0,
        tef_divergence_value=0.0,
        audited_shift="Turno 2",
        cashier_name="Operador Joao",
        leak_items=[leak_item],
        limitations=["Conferencia final pendente de supervisor"],
        suggested_actions=[action]
    )
    assert leak_props.severity == "critical"
    assert leak_props.total_leak_value == 142.50
    assert len(leak_props.leak_items) == 1

    # 4.6 BasketUpsellStrategyProps (F6-05)
    combo = UpsellComboItem(
        anchor_product="Gasolina Aditivada",
        recommended_product="Aditivo Flex Concentrado",
        lift=3.42,
        confidence_pct=28.5,
        support_pct=8.4,
        additional_ticket_reais=24.90,
        script_pitch="Doutor, ja colocou o aditivo de protecao do motor hoje?",
        category="Pista + Aditivos"
    )
    basket_props = BasketUpsellStrategyProps(
        diagnosis="Oportunidade de alavancar ticket medio em R$ 4,20 por abastecimento.",
        confidence_score=0.92,
        projected_ticket_increase=4.20,
        projected_monthly_revenue_lift=12600.0,
        category_focus="Pista x Aditivos",
        top_combos=[combo],
        limitations=["Base de cupons dos ultimos 30 dias"],
        suggested_actions=[action]
    )
    assert basket_props.projected_ticket_increase == 4.20
    assert len(basket_props.top_combos) == 1
    assert basket_props.top_combos[0].lift == 3.42

    print("   [OK] Todos os 6 Props Models de micro-widgets validados com integridade tipada.")


def test_action_execute_request_and_voucher_contracts():
    print("\n5. Testando ActionExecuteRequest, ActionVoucher e Assinatura Criptografica HMAC...")

    tool_id = generate_tool_call_id()
    act_id = generate_action_id()
    voucher_id = f"vch_{uuid.uuid4()}"
    sess_id = f"sess_{uuid.uuid4()}"

    # 5.1 ActionExecuteRequest
    req = ActionExecuteRequest(
        session_id=sess_id,
        tool_call_id=tool_id,
        action_id=act_id,
        action_name="pedido_combustivel",
        action_type="mutation",
        payload={"litros": 15000, "combustivel": "Diesel S10"},
        operator_id="gerente_carlos",
        operator_role="gerente"
    )
    assert req.tool_call_id == tool_id
    assert req.action_id == act_id
    assert req.action_name == "pedido_combustivel"
    assert req.operator_role == "gerente"

    # Rejeicao de tool_call_id invalido em ActionExecuteRequest
    try:
        ActionExecuteRequest(
            tool_call_id="invalid_call_id",
            action_id=act_id
        )
        assert False, "ActionExecuteRequest deveria rejeitar tool_call_id invalido"
    except ValidationError:
        pass

    # Rejeicao de action_id invalido em ActionExecuteRequest
    try:
        ActionExecuteRequest(
            tool_call_id=tool_id,
            action_id="invalid_action_id"
        )
        assert False, "ActionExecuteRequest deveria rejeitar action_id invalido"
    except ValidationError:
        pass

    # 5.2 ActionVoucher e Assinatura HMAC-SHA256
    ts = datetime.now(timezone.utc).isoformat()
    sig = generate_action_voucher_signature(
        voucher_id=voucher_id,
        action_id=act_id,
        tool_call_id=tool_id,
        status="APPROVED",
        timestamp=ts,
        secret="aura_voucher_hmac_secret_v1"
    )
    assert len(sig) == 64 # SHA256 hex string tem 64 caracteres

    voucher = ActionVoucher(
        voucher_id=voucher_id,
        action_id=act_id,
        tool_call_id=tool_id,
        status="APPROVED",
        timestamp=ts,
        action_name="pedido_combustivel",
        details={"litros": 15000, "combustivel": "Diesel S10"},
        signature=sig
    )
    assert voucher.voucher_id == voucher_id
    assert voucher.status == "APPROVED"
    assert verify_action_voucher_signature(voucher, secret="aura_voucher_hmac_secret_v1")

    # Deteccao de Adulteracao (Tamper Resistance)
    tampered_voucher = ActionVoucher(
        voucher_id=voucher_id,
        action_id=act_id,
        tool_call_id=tool_id,
        status="EXECUTED", # Alterado de APPROVED para EXECUTED sem recalcular assinatura
        timestamp=ts,
        action_name="pedido_combustivel",
        details={"litros": 15000},
        signature=sig
    )
    assert not verify_action_voucher_signature(tampered_voucher, secret="aura_voucher_hmac_secret_v1")

    # Deteccao de chave secreta incorreta
    assert not verify_action_voucher_signature(voucher, secret="wrong_secret_key")

    # 5.3 GenUIActionResult
    res = GenUIActionResult(
        tool_call_id=tool_id,
        action_id=act_id,
        status="COMMITTED",
        voucher_id=voucher_id,
        signature=sig,
        feedback_message="Transacao autorizada e despachada ao ERP."
    )
    assert res.status == "COMMITTED"
    assert res.voucher_id == voucher_id

    # 5.4 WidgetStateRecord e WidgetActionExecution
    wsr = WidgetStateRecord(
        tool_call_id=tool_id,
        status="committed",
        is_locked=True,
        locked_action_id=act_id,
        ttl_seconds=900,
        result={"voucher_id": voucher_id}
    )
    assert wsr.status == "committed"
    assert wsr.is_locked is True
    assert not wsr.is_stale()

    wae = WidgetActionExecution(
        action_id=act_id,
        tool_call_id=tool_id,
        payload={"opcao": 1}
    )
    assert wae.action_id == act_id

    print("   [OK] ActionExecuteRequest, ActionVoucher, HMAC e GenUIActionResult validados com sucesso.")


def run_all_contract_tests():
    print("=" * 78)
    print("SUITE DE TESTES: CONTRATOS GENUI & SCHEMAS PYDANTIC V2 (FASE 8: F8-01)")
    print("=" * 78)

    test_idempotency_contracts()
    test_genui_action_option_contract()
    test_genui_envelope_contract()
    test_micro_widgets_props_contracts()
    test_action_execute_request_and_voucher_contracts()

    print("\n" + "=" * 78)
    print("SUITE F8-01 (CONTRATOS GENUI) CONCLUIDA COM 100% DE SUCESSO!")
    print("=" * 78 + "\n")


if __name__ == "__main__":
    run_all_contract_tests()
