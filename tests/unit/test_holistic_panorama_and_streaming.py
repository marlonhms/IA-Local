"""
Suite de testes unitarios para o Roadmap Apendice:
Desenviesamento Holistico de Panorama, Higienizacao de Telemetria Fantasma (Tanque 000)
e Resiliencia Atomica de Streaming (v2.3.0).

Regra estrita: ZERO travessoes Unicode em todo o arquivo.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.aura_engine import AuraChunkType, AuraEngine
from core.prompts.micro_sops import resolve_micro_agent_spec
from core.prompts.system_prompts import build_system_prompt
from core.tools import PostoTools


def test_tanque_000_inativo_excluded_from_critical_autonomy() -> None:
    """Garante que registros virtuais/inativos (como Tanque 000) nao zerem a autonomia do posto."""
    tools = PostoTools()
    res = tools.prever_esgotamento_tanques()

    assert "metrics" in res
    assert "tanks" in res or "detalhamento_tanques" in res

    metrics = res["metrics"]
    tanks = res.get("tanks") or res.get("detalhamento_tanques") or []

    # Se o Tanque 000 existir na base, deve ser marcado como INATIVO
    t000_list = [t for t in tanks if str(t.get("codtan")) in ("000", "0", "00")]
    for t0 in t000_list:
        assert t0.get("status_operacional") == "INATIVO", "Tanque 000 deve ser classificado como INATIVO"

    # Tanques operacionais com saldo devem vir no topo
    t_ativos = [t for t in tanks if t.get("status_operacional") != "INATIVO" and float(t.get("saldo_atual_litros") or 0) > 0]
    if t_ativos:
        primeiro_tanque = tanks[0]
        assert primeiro_tanque.get("status_operacional") != "INATIVO", "O primeiro tanque da lista de retorno deve ser ativo e operacional"
        # Autonomia de esgotamento total (runout) apurada nas metricas gerais nao pode ser 0.0h se houver tanques com saldo
        assert metrics.get("autonomia_runout_horas", 0.0) > 0.0, "Autonomia runout nao pode ser zerada por tanques inativos"


def test_mentoria_executiva_leads_with_holistic_panorama() -> None:
    """Valida que a mentoria executiva lidera com Faturamento, Margem e Caixa (4 pilares) e nao com Tanque 000."""
    tools = PostoTools()
    diagnostico_dict = tools.gerar_diagnostico_mentoria_executiva()

    diagnosis = diagnostico_dict.get("diagnosis", "")
    assert diagnosis, "Diagnostico executivo nao pode ser vazio"

    # 1. Proibicao absoluta do Tanque 000
    assert "Tanque 000" not in diagnosis, "Diagnostico executivo jamais pode citar o Tanque 000 inativo"
    assert "0,0h" not in diagnosis and "0.0h" not in diagnosis, "Diagnostico nao pode alegar falso esgotamento de 0.0h"

    # 2. Abertura Holistica do Panorama
    assert diagnosis.startswith("Panorama do dia:"), f"Diagnostico deve abrir com 'Panorama do dia:', recebido: {diagnosis}"
    assert "Faturamento" in diagnosis, "Diagnostico deve incluir Faturamento do dia"
    assert "margem" in diagnosis.lower(), "Diagnostico deve incluir Margem consolidada"
    assert "caixa" in diagnosis.lower(), "Diagnostico deve incluir Conciliacao de caixa"


def test_system_prompt_neutral_bluf_no_tank_anchoring() -> None:
    """Valida que o prompt principal possui a regra anti-vies e nao induz o modelo a falar de tanques."""
    prompt = build_system_prompt(
        pergunta_sanitizada="Como estamos hoje?",
        contexto_sanitizado="Contexto de teste",
        historico_formatado="",
        intencao="mentoria_decisao",
        genui_active=True,
    )

    # 1. Deve conter a regra explicita de equilibrio holistico
    assert "REGRA DE EQUILIBRIO HOLISTICO E PROIBICAO DE VIES EM TANQUES" in prompt
    assert "NUNCA resuma um check-in geral a um unico tanque" in prompt
    assert "JAMAIS mencione tanques inativos" in prompt

    # 2. Nao pode usar Tanque 1 critico como primeiro exemplo de BLUF
    assert 'ex: "Tanque 1 (Gasolina Comum) critico' not in prompt
    assert 'ex: "Panorama com faturamento' in prompt


def test_micro_sops_executive_mentor_role() -> None:
    """Valida o mapeamento e catalogo do micro-agente executive_mentor_bot."""
    spec = resolve_micro_agent_spec("mentoria_decisao")
    assert spec.agent_role == "executive_mentor_bot"
    assert "Panorama estrategico holistico" in spec.sop_template or "panorama estrategico holistico" in spec.sop_template.lower()
    assert "Equilibrio dos 4 Pilares" in spec.sop_template
    assert "NUNCA mencione tanques inativos" in spec.sop_template


@pytest.mark.asyncio
async def test_aura_engine_streaming_resilience_on_truncation() -> None:
    """Garante que interrupcao da API da LLM (erro 503) no meio da frase aciona a sintese deterministica completa."""
    engine = AuraEngine()

    mock_chunk1 = MagicMock()
    mock_chunk1.text = "Tanque operacional em andamento e faturamento di"

    class MockAsyncStream:
        def __init__(self):
            self.yielded = False

        def __aiter__(self):
            return self

        async def __anext__(self):
            if not self.yielded:
                self.yielded = True
                return mock_chunk1
            raise RuntimeError("503 This model is currently experiencing high demand.")

    with patch("google.generativeai.GenerativeModel") as mock_model_cls:
        mock_instance = MagicMock()
        mock_instance.generate_content_async = AsyncMock(return_value=MockAsyncStream())
        mock_model_cls.return_value = mock_instance

        chunks = []
        async for c in engine.ask_stream(
            query="Como estamos hoje?",
            session_id="test_resilience_session",
            enable_genui=True,
        ):
            chunks.append(c)

        # Deve haver chunk DONE
        done_chunks = [c for c in chunks if c.chunk_type == AuraChunkType.DONE]
        assert len(done_chunks) == 1, "Deve emitir exatamente um chunk DONE"

        done_text = done_chunks[0].text
        # O texto final entregue nao pode terminar na metade da palavra 'di'
        assert not done_text.endswith("faturamento di"), "O texto final reconciliado nao pode estar truncado na metade da palavra"
        assert done_text.endswith((".", "!", "?", ")", '"', "'", ":", "]")), "O texto final deve encerrar com pontuacao valida"
        assert "Mentor Executivo de Decisoes" in done_text or "Panorama do dia:" in done_text or "faturamento" in done_text.lower()
