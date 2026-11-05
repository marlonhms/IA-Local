"""
Testes Unitarios do Catalogo Canonico de Fichas Fiscais (Micro-SOPs) e Grounding.
Valida integridade estrutural das fichas de CST 61, CST 04, Rejeicoes SEFAZ e DIFAL.
Regra inegociavel: ZERO travessoes em todo o modulo.
"""

import pytest

from core.prompts.fiscal_knowledge_cards import (
    FISCAL_KNOWLEDGE_CARDS,
    formatar_fichas_para_prompt,
    obter_card_fiscal,
    obter_todos_cards_relevantes,
)
from core.prompts.micro_sops import resolve_micro_agent_spec


def test_cards_estruturais_essenciais():
    """Valida presenca e campos obrigatorios dos cartoes fiscais criticos."""
    chaves_obrigatorias = [
        "cst_61_icms_monofasico",
        "cst_04_pis_cofins_conveniencia",
        "rejeicoes_sefaz_criticas_posto",
        "difal_combustiveis",
        "reforma_tributaria_combustiveis",
    ]
    for chave in chaves_obrigatorias:
        card = obter_card_fiscal(chave)
        assert card is not None, f"Cartao ausente: {chave}"
        assert "titulo" in card
        assert "base_legal" in card
        assert "pontos_criticos" in card
        assert len(card["pontos_criticos"]) >= 2


def test_cst_61_regras_combustiveis():
    """Valida regras fiscais de CST 61 e LC 192/2022."""
    card = obter_card_fiscal("cst_61_icms_monofasico")
    assert "LC 192" in card["base_legal"] or "192/2022" in card["base_legal"]
    assert "5656" in card["cfop_padrao"]
    assert "5102" in card["cfops_proibidos"]
    pontos_str = " ".join(card["pontos_criticos"])
    assert "960" in pontos_str
    assert "958" in pontos_str
    assert "qBCMonoRet" in pontos_str


def test_cst_04_regras_conveniencia():
    """Valida regras de PIS/COFINS monofasico na loja de conveniencia."""
    card = obter_card_fiscal("cst_04_pis_cofins_conveniencia")
    assert "13.097" in card["base_legal"] or "13097" in card["base_legal"]
    assert "4.3.10" in card["base_legal"]
    pontos_str = " ".join(card["pontos_criticos"])
    assert "Bitributacao" in pontos_str or "bitributacao" in pontos_str.lower()
    assert "806" in pontos_str
    assert "CEST" in pontos_str


def test_obter_todos_cards_relevantes_query_mista():
    """Valida que uma pergunta complexa com CST 61 e CST 04 recupera ambos os cartoes."""
    query = "Quais os pontos criticos de ICMS Monofasico CST 61, PIS/COFINS CST 04 na conveniencia e rejeicoes SEFAZ?"
    cards = obter_todos_cards_relevantes(query)
    assert len(cards) >= 2
    ids_encontrados = [c["id"] for c in cards]
    assert "cst_61_icms_monofasico" in ids_encontrados
    assert "cst_04_pis_cofins_conveniencia" in ids_encontrados


def test_formatar_fichas_para_prompt():
    """Valida a formatacao em markdown para injecao no prompt da LLM."""
    query = "Quais os pontos criticos de ICMS Monofasico CST 61, PIS/COFINS CST 04 na conveniencia e rejeicoes SEFAZ?"
    prompt_bloco = formatar_fichas_para_prompt(query)
    assert "GROUNDING FISCAL DETERMINISTICO" in prompt_bloco
    assert "ICMS Monofasico sobre Combustiveis (CST 61)" in prompt_bloco
    assert "PIS/COFINS Monofasico na Loja de Conveniencia (CST 04)" in prompt_bloco
    assert "NUNCA mencione tanques de combustivel" in prompt_bloco


def test_micro_sops_resolucao_fiscal_compliance_bot():
    """Valida que a intencao auditoria_fiscal_sefaz resolve para fiscal_compliance_bot."""
    spec = resolve_micro_agent_spec("auditoria_fiscal_sefaz")
    assert spec.agent_role == "fiscal_compliance_bot"
    assert spec.universal_intent == "auditoria_fiscal_sefaz"
    assert "Micro-Agente de Auditoria Fiscal" in spec.sop_template
