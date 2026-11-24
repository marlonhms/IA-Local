"""
Testes Unitarios: Carbon Core P0.4 - Isolamento de DomainPack via ContextVar,
Desbloqueio Async do SemanticRouter (db_pool + asyncio.to_thread) e Transacionalidade
de Streaming com emissao de STREAM_RESET em falha de FALLBACK_MODELS.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace
from typing import Any

import pytest

import core.aura_engine as ae
from core.aura_engine import AuraChunkType, AuraEngine, AuraSessionMemory
from core.domain.domain_pack_loader import (
    DomainPackContext,
    get_active_domain_pack,
    reset_active_domain_pack,
)
from core.semantic_router import SemanticRouter


@pytest.mark.unit
def test_domain_pack_contextvar_concurrent_isolation_20_tasks() -> None:
    """
    Executa 20 coroutines concorrentes via asyncio.gather misturando pharmacy_health
    e fuel_convenience, provando zero cross-talk no ContextVar de DomainPack.
    """

    async def _worker(idx: int) -> tuple[int, str, str]:
        target_pack = "pharmacy_health" if idx % 2 == 0 else "fuel_convenience"
        async with DomainPackContext(target_pack) as entered:
            # Cede controle varias vezes para forcar intercalacao de coroutines
            await asyncio.sleep(0.005)
            observed = get_active_domain_pack().pack_id
            await asyncio.sleep(0.005)
            observed_after = get_active_domain_pack().pack_id
            assert entered.pack_id == target_pack
            return idx, observed, observed_after

    async def _run_all():
        return await asyncio.gather(*(_worker(i) for i in range(20)))

    try:
        results = asyncio.run(_run_all())
        assert len(results) == 20
        for idx, obs1, obs2 in results:
            expected = "pharmacy_health" if idx % 2 == 0 else "fuel_convenience"
            assert obs1 == expected, f"Cross-talk detectado na task {idx}: {obs1} != {expected}"
            assert obs2 == expected, f"Cross-talk detectado apos await na task {idx}: {obs2} != {expected}"
    finally:
        reset_active_domain_pack()


@pytest.mark.unit
def test_semantic_router_uses_db_pool_vector_connection(monkeypatch) -> None:
    """Valida que SemanticRouter._get_connection delega ao pool gerenciado get_vector_connection."""
    import core.db_pool as db_pool_mod

    sentinel_conn = object()
    called = {"count": 0}

    def _fake_get_vector_conn(*_args, **_kwargs):
        called["count"] += 1
        return sentinel_conn

    monkeypatch.setattr(db_pool_mod, "get_vector_connection", _fake_get_vector_conn)
    router = SemanticRouter()
    conn = router._get_connection()

    assert conn is sentinel_conn
    assert called["count"] == 1


@pytest.mark.unit
def test_ask_stream_event_loop_stays_responsive_during_slow_routing(monkeypatch) -> None:
    """
    Garante que router.route sincrono lento (500ms simulando embedding HTTP) roda em
    asyncio.to_thread sem congelar o event loop durante o roteamento.
    """

    class _SlowRouter:
        def route(self, query_text: str):
            time.sleep(0.5)
            return ("dados_filial", 0.95, {"method": "mock_slow_vector", "query_vector": None})

    class _FastModel:
        def __init__(self, _name: str) -> None:
            pass

        async def generate_content_async(self, _prompt: str, **_kwargs):
            async def _gen():
                yield SimpleNamespace(
                    text="Unidade operacional validada com sucesso e cadastro integralmente conciliado.",
                    usage_metadata=SimpleNamespace(prompt_token_count=30, candidates_token_count=12),
                )

            return _gen()

    monkeypatch.setattr(ae.genai, "GenerativeModel", _FastModel)

    mem = AuraSessionMemory(db_path=":memory:")
    engine = AuraEngine(session_memory=mem, router=_SlowRouter())
    engine._dados_filial = {
        "idempresa": "00001",
        "nome": "POSTO PILOTO MODELO",
        "razao_social": "POSTO PILOTO MODELO LTDA",
        "cnpj": "00.000.000/0001-00",
    }
    monkeypatch.setattr(
        engine,
        "_resolver_contexto_ferramenta",
        lambda *_a, **_kw: ("Dados da filial OK.", {"idempresa": "00001"}, None, False, 1.0),
    )

    async def _measure():
        max_routing_gap_ms = 0.0
        routing_ticks = 0
        routing_done = False

        async def _heartbeat():
            nonlocal max_routing_gap_ms, routing_ticks
            while not routing_done:
                t0 = time.perf_counter()
                await asyncio.sleep(0.01)
                gap_ms = (time.perf_counter() - t0 - 0.01) * 1000.0
                routing_ticks += 1
                if gap_ms > max_routing_gap_ms:
                    max_routing_gap_ms = gap_ms

        hb = asyncio.create_task(_heartbeat())
        chunks = []
        try:
            async for c in engine.ask_stream("qual o cnpj da filial?", enable_genui=False):
                chunks.append(c)
                if c.chunk_type == AuraChunkType.INTENT:
                    routing_done = True
        finally:
            routing_done = True
            await hb

        return max_routing_gap_ms, routing_ticks, chunks

    max_routing_gap_ms, routing_ticks, chunks = asyncio.run(_measure())
    assert any(c.chunk_type == AuraChunkType.DONE for c in chunks)
    # Durante 500ms de roteamento sincrono em thread, o event loop deve continuar pulsando
    assert routing_ticks >= 15, f"Poucos ticks no event loop durante roteamento lento: {routing_ticks}"
    assert max_routing_gap_ms < 50.0, (
        f"Event loop bloqueado durante roteamento lento (500ms): max_gap={max_routing_gap_ms:.1f}ms"
    )


@pytest.mark.unit
def test_stream_reset_emitted_and_no_duplication_on_fallback_timeout(monkeypatch) -> None:
    """
    Valida P0.4:
    Quando FALLBACK_MODELS[0] emite > 50 chars e lanca asyncio.TimeoutError no meio da stream,
    ask_stream DEVE emitir AuraChunkType.STREAM_RESET antes de transmitir a resposta limpa
    de FALLBACK_MODELS[1], garantindo zero texto duplicado em ask_stream e ask().
    """
    monkeypatch.setattr(ae, "FALLBACK_MODELS", ["models/primary-fail", "models/secondary-ok"])

    partial_primary_text = (
        "Texto parcial corrompido do modelo primario que sera descartado apos cinquenta caracteres "
    )
    clean_fallback_text = (
        "Panorama consolidado: faturamento de R$ 15.200,00 com margem liquida de 14,5% "
        "e caixa totalmente conciliado sem divergencias operacionais na unidade."
    )

    class _MockGenerativeModel:
        def __init__(self, model_name: str) -> None:
            self.model_name = model_name

        async def generate_content_async(self, _prompt: str, **_kwargs):
            if self.model_name == "models/primary-fail":

                async def _failing_gen():
                    yield SimpleNamespace(text=partial_primary_text)
                    raise asyncio.TimeoutError("simulated_mid_stream_timeout")

                return _failing_gen()

            async def _ok_gen():
                yield SimpleNamespace(
                    text=clean_fallback_text,
                    usage_metadata=SimpleNamespace(prompt_token_count=45, candidates_token_count=28),
                )

            return _ok_gen()

    class _FixedRouter:
        def route(self, _q: str):
            return ("vendas_analitico", 0.96, {"method": "mock_vector", "query_vector": None})

    monkeypatch.setattr(ae.genai, "GenerativeModel", _MockGenerativeModel)

    mem = AuraSessionMemory(db_path=":memory:")
    engine = AuraEngine(session_memory=mem, router=_FixedRouter())
    tool_payload = {"faturamento_total": 15200.0, "margem_pct": 14.5}
    monkeypatch.setattr(
        engine,
        "_resolver_contexto_ferramenta",
        lambda *_a, **_kw: ("Faturamento R$ 15.200,00 | Margem 14,5%.", tool_payload, None, False, 2.0),
    )

    async def _collect():
        stream_chunks = [c async for c in engine.ask_stream("qual o faturamento de hoje?", enable_genui=False)]
        ask_resp = await engine.ask("qual o faturamento de hoje?", enable_genui=False)
        return stream_chunks, ask_resp

    chunks, resp = asyncio.run(_collect())

    # 1. Evento explicito STREAM_RESET foi emitido com formato SSE valido
    reset_chunks = [c for c in chunks if c.chunk_type == AuraChunkType.STREAM_RESET]
    assert len(reset_chunks) == 1
    assert reset_chunks[0].to_sse().startswith("event: stream_reset\n")
    assert reset_chunks[0].data["failed_model"] == "models/primary-fail"

    # 2. Deltas apos STREAM_RESET contem apenas a resposta limpa do fallback (zero duplicacao)
    reset_idx = chunks.index(reset_chunks[0])
    post_reset_text = "".join(
        c.text for c in chunks[reset_idx + 1 :] if c.chunk_type == AuraChunkType.DELTA and c.text
    )
    assert "Texto parcial corrompido" not in post_reset_text
    assert "R$ 15.200,00" in post_reset_text

    # 3. ask() consolida respeitando STREAM_RESET -> zero texto parcial do modelo abortado
    assert "Texto parcial corrompido" not in resp.response_text
    assert "R$ 15.200,00" in resp.response_text

    # 4. Telemetria contem auditoria deterministica de fidelidade numerica e contagem de stream_reset
    telem_chunks = [c for c in chunks if c.chunk_type == AuraChunkType.TELEMETRY]
    assert telem_chunks
    telem = telem_chunks[-1].data
    assert telem["stream_reset_count"] == 1
    assert "numeric_fidelity" in telem
    assert telem["numeric_fidelity"]["passed"] is True
