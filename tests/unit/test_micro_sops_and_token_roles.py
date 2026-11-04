"""Testes Unitarios para Micro-SOPs e Governanca de Orcamento por Agent Role (AURA).

Valida:
1. Reducao de tokens >= 45% com build_scoped_micro_prompt frente ao prompt monolitico.
2. Adaptacao dinamica de vocabulario por Domain Pack (Supermercados, Farmacias, Postos, etc.).
3. Registro e agregacao por agent_role, intent_category e vertical_pack no TokenBudgetManager.
4. Roteamento economico e downgrade automatico de modelos via recommend_model_for_role.
5. Snapshot YAML conciso de estado (<= 150 tokens estimados) via build_compact_retail_state_yaml.
Regra estrita: Zero travessoes Unicode em todo o arquivo.
"""

from __future__ import annotations

import sqlite3
from typing import Any

import pytest

from core.domain.domain_pack_loader import load_domain_pack
from core.prompts.micro_sops import (
    INTENT_TO_AGENT_ROLE,
    RETAIL_MICRO_AGENT_SOPS,
    build_compact_retail_state_yaml,
    build_scoped_micro_prompt,
    resolve_micro_agent_spec,
)
from core.prompts.system_prompts import build_system_prompt
from core.token_budget import TokenBudgetManager


def test_scoped_micro_prompt_token_reduction():
    """Comprova que o Micro-SOP reduz em pelo menos 45% o tamanho do prompt frente ao monolitico."""
    pergunta = "Como fechar o turno e auditar quebras de caixa?"
    contexto = "Tabela de fechamento de caixa: operador Maria com sobra de R$ 5,00."
    historico = "Usuario: Bom dia\nAURA: Ola gestor, em prontidao."
    filial = {"idempresa": "00001", "nome": "SUPERMERCADO MODELO"}

    # Prompt monolitico tradicional
    monolithic_prompt = build_system_prompt(
        pergunta_sanitizada=pergunta,
        contexto_sanitizado=contexto,
        historico_formatado=historico,
        dados_filial=filial,
    )

    pack = load_domain_pack("retail_supermarket")
    scoped_prompt, spec = build_scoped_micro_prompt(
        intent="auditoria_turno_caixa",
        pergunta_sanitizada=pergunta,
        tool_output_yaml="caixa: fechado\nsobra_brl: 5.0",
        pack=pack,
        dados_filial=filial,
    )

    len_monolithic = len(monolithic_prompt)
    len_scoped = len(scoped_prompt)
    reduction_pct = (len_monolithic - len_scoped) / len_monolithic * 100.0

    assert reduction_pct >= 45.0, (
        f"Reducao de {reduction_pct:.1f}% foi inferior a meta minima de 45% "
        f"(monolitico: {len_monolithic} chars, scoped: {len_scoped} chars)"
    )
    assert spec.agent_role == "checkout_auditor_bot"
    assert "gondola" in scoped_prompt or "checkout" in scoped_prompt


def test_vocabulary_adaptation_across_domain_packs():
    """Comprova que o vocabulario do prompt muda dinamicamente conforme o DomainPack ativo."""
    supermarket_pack = load_domain_pack("retail_supermarket")
    pharmacy_pack = load_domain_pack("pharmacy_health")
    fuel_pack = load_domain_pack("fuel_convenience")

    # Supermercado: deve falar de checkout / operador de caixa / gondola
    prompt_super, _ = build_scoped_micro_prompt(
        intent="auditoria_turno_caixa",
        pergunta_sanitizada="como esta o caixa?",
        tool_output_yaml="saldo: 0.0",
        pack=supermarket_pack,
    )
    assert "checkout" in prompt_super
    assert "operador_caixa" in prompt_super or "operador de caixa" in prompt_super

    # Farmacia: deve citar balcao_dispensacao ou farmaceutico ou SNGPC
    prompt_pharm, spec_pharm = build_scoped_micro_prompt(
        intent="previsao_runout_estoque",
        pergunta_sanitizada="produtos perto de vencer?",
        tool_output_yaml="lotes_vencendo: 3",
        pack=pharmacy_pack,
    )
    assert "prateleira_gaveteiro" in prompt_pharm or "vencimento_fefo_lote" in prompt_pharm
    assert spec_pharm.agent_role == "inventory_rupture_bot"

    # Posto de combustivel: deve citar tanque ou bomba ou LMC
    prompt_fuel, spec_fuel = build_scoped_micro_prompt(
        intent="lmc_anp",
        pergunta_sanitizada="como esta o lmc?",
        tool_output_yaml="desvio_lmc_pct: 0.2",
        pack=fuel_pack,
    )
    assert "LMC ANP" in prompt_fuel
    assert spec_fuel.agent_role == "regulatory_shrinkage_bot"


def test_compact_retail_state_yaml_token_budget():
    """Comprova que build_compact_retail_state_yaml gera estado enxuto (<= 150 tokens / 600 chars)."""
    kpis = {
        "faturamento_dia_brl": 15420.50,
        "taxa_quebra_pct": 0.42,
        "ruptura_gondola_itens": 3,
        "operadores_ativos": 4,
        "ticket_medio_brl": 86.40,
    }
    recent_turns = [
        {"intent": "auditoria_turno_caixa", "target": "checkout_02", "verdict": "sobra_r$12"},
        {"intent": "ruptura_invisivel_gondola", "target": "leite_integral", "verdict": "alerta_reposicao"},
    ]

    state_yaml = build_compact_retail_state_yaml(
        filial_id="loja_central",
        vertical="supermarket_retail",
        kpi_snapshot=kpis,
        recent_turns=recent_turns,
    )

    # 150 tokens equivalem tipicamente a ~600 caracteres em portugues
    assert len(state_yaml) <= 600, f"Estado muito longo: {len(state_yaml)} caracteres"
    assert "filial_id: loja_central" in state_yaml
    assert "faturamento_dia_brl: 15420.50" in state_yaml
    assert "intent: ruptura_invisivel_gondola" in state_yaml
    assert "\u2014" not in state_yaml and "\u2013" not in state_yaml


def test_token_budget_agent_role_ledger():
    """Valida registro e consulta agregada por agent_role, intent_category e vertical_pack."""
    manager = TokenBudgetManager(db_path=":memory:")

    # Registra consumo de tres micro-agentes diferentes
    manager.record_usage(
        session_id="s1",
        filial_id="posto_sp",
        model_name="gemini-2.5-flash",
        prompt_tokens=400,
        completion_tokens=150,
        agent_role="checkout_auditor_bot",
        intent_category="checkout",
        vertical_pack="fuel_convenience",
    )
    manager.record_usage(
        session_id="s2",
        filial_id="posto_sp",
        model_name="gemini-2.5-flash",
        prompt_tokens=300,
        completion_tokens=100,
        agent_role="erp_sop_triage_bot",
        intent_category="triage",
        vertical_pack="fuel_convenience",
    )
    manager.record_usage(
        session_id="s3",
        filial_id="posto_sp",
        model_name="gemini-2.5-flash",
        prompt_tokens=800,
        completion_tokens=250,
        agent_role="margin_causal_bot",
        intent_category="executive_margin",
        vertical_pack="fuel_convenience",
    )

    usage = manager.get_usage_by_agent_role(filial_id="posto_sp", days=7)
    assert len(usage) == 3

    roles = {u["agent_role"] for u in usage}
    assert "checkout_auditor_bot" in roles
    assert "erp_sop_triage_bot" in roles
    assert "margin_causal_bot" in roles

    # Verifica se percentual relativo foi calculado
    total_pct = sum(u["cost_pct"] for u in usage)
    assert 99.0 <= total_pct <= 101.0


def test_recommend_model_for_role_and_downgrade():
    """Valida fixacao de modelo economico para triagem e downgrade preventivo no limite orcamentario."""
    manager = TokenBudgetManager(db_path=":memory:")

    # 1. Triagem operacional deve ser fixada em flash
    rec = manager.recommend_model_for_role(
        filial_id="f1",
        agent_role="erp_sop_triage_bot",
        requested_model="gemini-2.5-pro",
    )
    assert rec["recommended_model"] == "gemini-2.5-flash"

    # 2. Quando orcamento esta normal, modelo pro para margin_causal_bot e aceito
    rec_pro = manager.recommend_model_for_role(
        filial_id="f1",
        agent_role="margin_causal_bot",
        requested_model="gemini-2.5-pro",
    )
    assert rec_pro["recommended_model"] == "gemini-2.5-pro"
    assert rec_pro["downgrade_applied"] is False

    # 3. Simula consumo alto atingindo teto de alerta
    manager.update_budget_policy(filial_id="f1", monthly_budget_brl=1.00, alert_threshold_pct=50.0)
    manager.record_usage(
        session_id="s_heavy",
        filial_id="f1",
        model_name="gemini-2.5-pro",
        prompt_tokens=500000,
        completion_tokens=100000,
    )

    # Agora a filial esta em alerta ou estourada -> downgrade automatico
    rec_downgrade = manager.recommend_model_for_role(
        filial_id="f1",
        agent_role="margin_causal_bot",
        requested_model="gemini-2.5-pro",
    )
    assert rec_downgrade["recommended_model"] == "gemini-2.5-flash"
    assert rec_downgrade["downgrade_applied"] is True
