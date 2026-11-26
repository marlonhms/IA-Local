"""
Testes unitarios da arquitetura de Cerebro Autonomo e Otimizador de Contexto
para LLMs leves/locais e motores de fronteira (core/migrations.py + core/brain_optimizer.py).
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import json
import sqlite3

from core.brain_optimizer import (
    AutonomousBrainStore,
    LLMTier,
    distill_tool_context,
    resolve_llm_context_profile,
)
from core.migrations import ensure_autonomous_brain_schema


def test_ensure_autonomous_brain_schema_idempotent_sqlite() -> None:
    """Garante migracao idempotente de perguntas_cache, intencoes_vetores e aura_learned_knowledge."""
    conn = sqlite3.connect(":memory:")
    try:
        r1 = ensure_autonomous_brain_schema(conn, dialect="sqlite")
        r2 = ensure_autonomous_brain_schema(conn, dialect="sqlite")
        assert r1["status"] == "ok"
        assert r2["status"] == "ok"
        assert set(r1["tables"]) == {"perguntas_cache", "intencoes_vetores", "aura_learned_knowledge"}

        cur = conn.cursor()
        cur.execute("PRAGMA table_info(intencoes_vetores);")
        int_cols = {row[1] for row in cur.fetchall()}
        assert "pack_id" in int_cols

        cur.execute("PRAGMA table_info(aura_learned_knowledge);")
        lk_cols = {row[1] for row in cur.fetchall()}
        assert {"tenant_id", "filial_id", "pack_id", "topic_key", "summary_compact", "status"}.issubset(lk_cols)
    finally:
        conn.close()


def test_resolve_llm_context_profile_tiers(monkeypatch) -> None:
    """Classifica corretamente LLMs leves/locais, balanceados e de fronteira com override via env."""
    monkeypatch.delenv("AURA_LLM_TIER", raising=False)

    light_flash = resolve_llm_context_profile("models/gemini-3.5-flash-lite")
    light_local = resolve_llm_context_profile("ollama/gemma3:4b")
    balanced = resolve_llm_context_profile("models/gemini-flash-latest")
    frontier = resolve_llm_context_profile("models/gemini-2.5-pro")

    assert light_flash.tier == LLMTier.EDGE_LIGHT
    assert light_local.tier == LLMTier.EDGE_LIGHT
    assert balanced.tier == LLMTier.BALANCED
    assert frontier.tier == LLMTier.FRONTIER
    assert light_flash.max_context_chars < balanced.max_context_chars < frontier.max_context_chars
    assert light_flash.compact_json is True
    assert frontier.compact_json is False

    monkeypatch.setenv("AURA_LLM_TIER", "frontier")
    forced = resolve_llm_context_profile("ollama/gemma3:4b")
    assert forced.tier == LLMTier.FRONTIER


def test_distill_tool_context_compresses_for_light_llm_preserving_numbers() -> None:
    """Reduz drasticamente tokens em LLMs leves mantendo todos os numeros reais intactos."""
    raw_payload = {
        "status": "OK",
        "faturamento_total": 2174.68,
        "preco_gasolina_comum": 7.50,
        "media_anp": 5.52,
        "embedding": [0.123456] * 128,
        "raw_sql": "SELECT * FROM produtos WHERE ativo = 'S'",
        "campo_vazio": None,
        "debug": {"internal": "verbose"},
        "itens": [
            {"sku": f"SKU{i:03d}", "nome": f"Produto {i}", "preco": round(10.0 + i, 2), "obs": None}
            for i in range(25)
        ],
    }

    verbose = json.dumps(raw_payload, ensure_ascii=False, indent=2)
    distilled_light = distill_tool_context(
        raw_payload,
        header="KPIs ERP Real:",
        model_name="models/gemini-3.5-flash-lite",
    )
    distilled_frontier = distill_tool_context(
        raw_payload,
        header="KPIs ERP Real:",
        model_name="models/gemini-2.5-pro",
    )

    assert len(distilled_light) < len(verbose) * 0.4
    assert len(distilled_light) < len(distilled_frontier)
    assert "embedding" not in distilled_light
    assert "raw_sql" not in distilled_light
    assert "2174.68" in distilled_light
    assert "7.5" in distilled_light
    assert "5.52" in distilled_light
    assert "_omitted_items" in distilled_light


def test_autonomous_brain_store_learn_and_recall_isolated_by_scope() -> None:
    """Valida auto-especializacao com upsert idempotente e isolamento por tenant/filial/pack."""
    conn = sqlite3.connect(":memory:")
    try:
        store = AutonomousBrainStore(connection=conn, dialect="sqlite")
        res1 = store.learn_fact(
            tenant_id="rede_es",
            filial_id="59050",
            pack_id="fuel_convenience",
            topic_key="regra_margem_gasolina",
            summary_compact="Margem minima autorizada para Gasolina Comum e 12.5% sobre custo CIF.",
            structured_data={"min_margin_pct": 12.5},
        )
        assert res1["status"] == "learned"

        # Upsert atualiza o mesmo topic_key sem duplicar
        store.learn_fact(
            tenant_id="rede_es",
            filial_id="59050",
            pack_id="fuel_convenience",
            topic_key="regra_margem_gasolina",
            summary_compact="Margem minima revisada para Gasolina Comum: 13.0% sobre custo CIF.",
            structured_data={"min_margin_pct": 13.0},
        )

        # Fato de outro tenant/pack nao pode vazar no recall
        store.learn_fact(
            tenant_id="rede_sp",
            filial_id="99999",
            pack_id="pharmacy_health",
            topic_key="regra_sngpc",
            summary_compact="Conferencia SNGPC obrigatoria toda sexta-feira.",
        )

        recalled = store.recall_compact_knowledge(
            query="qual a margem minima de gasolina comum?",
            tenant_id="rede_es",
            filial_id="59050",
            pack_id="fuel_convenience",
            model_name="ollama/llama-3.2-3b",
        )
        assert len(recalled) == 1
        assert recalled[0]["topic_key"] == "regra_margem_gasolina"
        assert "13.0%" in recalled[0]["summary_compact"]

        block = AutonomousBrainStore.format_recalled_knowledge_block(
            recalled,
            model_name="ollama/llama-3.2-3b",
        )
        assert "regra_margem_gasolina" in block
        assert len(block) <= 650
    finally:
        conn.close()


def test_build_system_prompt_genui_complementary_without_redundancy() -> None:
    """Garante que genui_active=True instrui texto complementar sem repetir blocos do card."""
    from core.prompts.system_prompts import build_system_prompt

    prompt_gui = build_system_prompt(
        pergunta_sanitizada="simule aumento de 3% no frete",
        contexto_sanitizado="{}",
        historico_formatado="",
        intencao="simulacao_preditiva",
        genui_active=True,
    )
    prompt_text = build_system_prompt(
        pergunta_sanitizada="simule aumento de 3% no frete",
        contexto_sanitizado="{}",
        historico_formatado="",
        intencao="simulacao_preditiva",
        genui_active=False,
    )

    assert "Complementaridade Real" in prompt_gui
    assert "VEREDITO ESTRATEGICO" in prompt_gui
    assert "NUMEROS E CALCULOS COMPROVADOS" not in prompt_gui
    assert "14.850,00" not in prompt_gui
    assert "NUMEROS E CALCULOS COMPROVADOS" in prompt_text
