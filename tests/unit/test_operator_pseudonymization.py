"""
Testes Unitarios: Pseudonimizacao Reversivel de Operadores Internos ([OP_XX]) e
Blindagem de Titulos/Rotulos Estruturais GenUI no Core da AURA.
"""

from __future__ import annotations

import asyncio

import pytest

from core.semantic_router import classificar_intencao_heuristica
from core.sanitizer import (
    REDACTED_CPF,
    REDACTED_PERSON,
    CentralLogSanitizer,
    StreamingOutputSanitizerGuard,
    operator_pseudonym_scope,
    sanitize_dict,
    sanitize_text,
)


@pytest.mark.unit
def test_genui_executive_titles_and_buttons_never_redacted_as_person() -> None:
    """Titulos executivos e botoes PT-BR de GenUI nunca podem virar [REDACTED:PERSON]."""
    payload = {
        "component_name": "ExecutiveDecisionCard",
        "title": "Mentor de Decisões Executivo",
        "subtitle": "Diagnóstico Operacional de Fechamento de Turno",
        "badge_label": "AURA INTELIGÊNCIA",
        "metrics": [
            {"label": "Autonomia Mínima", "current_value": "153.0h"},
        ],
        "evidence_items": [
            {"title": "Telemetria Volumétrica", "detail": "Autonomia do Tanque 005"},
        ],
        "actions": [
            {"action_id": "act_rev_margem", "label": "Aprovar Revisão de Margem"},
            {"action_id": "act_aplicar", "label": "⚡ Aplicar Recomendações Prioritárias"},
            {"action_id": "act_metas", "label": "🎯 Ajustar Metas do Turno"},
        ],
    }

    cleaned, _ = sanitize_dict(payload)

    assert cleaned["title"] == "Mentor de Decisões Executivo"
    assert cleaned["subtitle"] == "Diagnóstico Operacional de Fechamento de Turno"
    assert cleaned["metrics"][0]["label"] == "Autonomia Mínima"
    assert cleaned["evidence_items"][0]["title"] == "Telemetria Volumétrica"
    assert cleaned["actions"][0]["label"] == "Aprovar Revisão de Margem"
    assert cleaned["actions"][1]["label"] == "⚡ Aplicar Recomendações Prioritárias"
    assert cleaned["actions"][2]["label"] == "🎯 Ajustar Metas do Turno"
    assert REDACTED_PERSON not in str(cleaned)
    assert sanitize_text("Aprovar Revisão de Margem") == "Aprovar Revisão de Margem"
    assert sanitize_text("⚡ Aplicar Recomendações Prioritárias") == "⚡ Aplicar Recomendações Prioritárias"
    assert sanitize_text("Autonomia Mínima") == "Autonomia Mínima"
    assert sanitize_text("Telemetria Volumétrica") == "Telemetria Volumétrica"


@pytest.mark.unit
def test_staff_collection_names_pseudonymized_while_customer_names_redacted() -> None:
    """Rankings de frentistas/vendedores recebem [OP_XX], clientes permanecem [REDACTED:PERSON]."""
    sanitizer = CentralLogSanitizer()

    with operator_pseudonym_scope() as vault:
        payload = {
            "melhor_frentista_nome": "Italo Bezerra X",
            "ranking_vendedores_pdv": [
                {"matricula": "00014", "nome": "Limitado", "faturamento_reais": 1772.21},
                {"matricula": "00007", "nome": "Marlon Henrique", "faturamento_reais": 146.87},
            ],
            "clientes": [
                {"codigo": "C01", "nome": "Maria Fernanda Souza"},
            ],
        }
        for_llm, _ = sanitizer.sanitize_payload(payload)

        assert for_llm["melhor_frentista_nome"] == "[OP_01]"
        assert for_llm["ranking_vendedores_pdv"][0]["nome"] == "[OP_02]"
        assert for_llm["ranking_vendedores_pdv"][1]["nome"] == "[OP_03]"
        assert for_llm["clientes"][0]["nome"] == REDACTED_PERSON

        for_manager = vault.rehydrate_data(for_llm)
        assert for_manager["melhor_frentista_nome"] == "Italo Bezerra X"
        assert for_manager["ranking_vendedores_pdv"][0]["nome"] == "Limitado"
        assert for_manager["ranking_vendedores_pdv"][1]["nome"] == "Marlon Henrique"
        assert for_manager["clientes"][0]["nome"] == REDACTED_PERSON


@pytest.mark.unit
def test_heuristic_routing_shift_executive_and_top_selling_employee() -> None:
    """Consultas executivas de turno, caixa aberto e vendas por funcionario roteiam corretamente."""
    assert classificar_intencao_heuristica("consulta executiva de turno") == "auditoria_turno"
    assert classificar_intencao_heuristica("diagnostico executivo do turno") in ("auditoria_turno", "mentoria_decisao")
    assert classificar_intencao_heuristica("movimentação do turno atual") == "auditoria_turno"
    assert classificar_intencao_heuristica("como está o caixa aberto agora") == "auditoria_turno"
    assert classificar_intencao_heuristica("qual funcionario que mais vendeu no erp") == "desempenho_pista_frentistas"
    assert classificar_intencao_heuristica("ranking de vendas por funcionario") == "desempenho_pista_frentistas"


@pytest.mark.unit
def test_operator_pseudonymization_for_llm_and_rehydration_for_manager() -> None:
    """
    Operadores internos viram [OP_01]/[OP_02] antes do LLM e sao re-hidratados
    no retorno autenticado, enquanto PII de cliente permanece irreversivelmente redatada.
    """
    sanitizer = CentralLogSanitizer()

    with operator_pseudonym_scope() as vault:
        tool_payload = {
            "turno": "Manha",
            "operador_nome": "CARLOS_OLIVEIRA",
            "frentista": "Ana Pereira",
            "observacao": (
                "Operador Carlos Oliveira fechou o caixa com divergencia. "
                "Cliente Joao Mendes (CPF 529.982.247-25) pediu nota fiscal."
            ),
        }

        sanitized_for_llm, counts = sanitizer.sanitize_payload(tool_payload)

        # Para o LLM externo: zero nome real de operador, zero nome/CPF de cliente
        assert sanitized_for_llm["operador_nome"] == "[OP_01]"
        assert sanitized_for_llm["frentista"] == "[OP_02]"
        assert "[OP_01]" in sanitized_for_llm["observacao"]
        assert "Carlos Oliveira" not in str(sanitized_for_llm)
        assert "Ana Pereira" not in str(sanitized_for_llm)
        assert "Joao Mendes" not in str(sanitized_for_llm)
        assert "529.982.247-25" not in str(sanitized_for_llm)
        assert REDACTED_PERSON in sanitized_for_llm["observacao"]
        assert REDACTED_CPF in sanitized_for_llm["observacao"]
        assert counts.get("operator_pseudonym", 0) >= 2

        # Streaming de resposta da LLM citando [OP_01] e [OP_02] (mesmo fatiado entre chunks)
        guard = StreamingOutputSanitizerGuard(window_size=24, sanitizer=sanitizer)
        llm_chunks = [
            "O turno da manha operado por [OP_",
            "01] apresentou divergencia no caixa, enquanto [OP_02] fechou conforme.",
        ]
        out_parts = [guard.push(c) for c in llm_chunks]
        out_parts.append(guard.flush())
        manager_output = "".join(out_parts)

        assert "Carlos Oliveira" in manager_output
        assert "Ana Pereira" in manager_output
        assert "[OP_01]" not in manager_output
        assert "[OP_02]" not in manager_output

        # Re-hidratacao de envelope GenUI estruturado
        rehydrated_card = vault.rehydrate_data(
            {"title": "Fechamento de Turno", "operador_nome": "[OP_01]", "frentista": "[OP_02]"}
        )
        assert rehydrated_card["operador_nome"] == "Carlos Oliveira"
        assert rehydrated_card["frentista"] == "Ana Pereira"


@pytest.mark.unit
def test_operator_pseudonym_vault_isolated_across_concurrent_async_requests() -> None:
    """Garante isolamento total via ContextVar entre requisicoes concorrentes (inclusive com to_thread)."""
    sanitizer = CentralLogSanitizer()

    async def _run_request(op_name: str, delay: float) -> tuple[str, str]:
        with operator_pseudonym_scope() as vault:
            sanitized, _ = await asyncio.to_thread(
                sanitizer.sanitize_payload, {"operador_nome": op_name}
            )
            await asyncio.sleep(delay)
            rehydrated = vault.rehydrate_text(f"Responsavel: {sanitized['operador_nome']}")
            return sanitized["operador_nome"], rehydrated

    async def _main():
        res_a, res_b = await asyncio.gather(
            _run_request("Marcos Antonio", 0.03),
            _run_request("Fernanda Lima", 0.01),
        )
        return res_a, res_b

    (tok_a, text_a), (tok_b, text_b) = asyncio.run(_main())
    assert tok_a == "[OP_01]"
    assert tok_b == "[OP_01]"
    assert text_a == "Responsavel: Marcos Antonio"
    assert text_b == "Responsavel: Fernanda Lima"
