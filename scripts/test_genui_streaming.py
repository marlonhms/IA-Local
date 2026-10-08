"""
Suite de Testes Automatizada: Streaming e Bufferizacao GenUI Multiplexada (Fase 8: F8-02)
Valida a transmissao SSE em chunks fracionados, bufferizacao e resiliencia de conexao:
1. Emissao multiplexada no backend (intent -> ui_skeleton -> delta -> ui_complete -> done).
2. Bufferizacao no cliente simulado sem vazamento de blocos JSON no texto conversacional.
3. Resiliencia do parser contra interrupcao prematura, cancelamento e desconexao do cliente.
4. Parsing SSE resiliente com fragmentacao arbitraria de pacotes TCP (16, 32, 64 bytes).
5. Zero travessoes em textos e mensagens de teste.
"""

from __future__ import annotations

import sys
import json
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

# Protege stdout no terminal Windows contra problemas de codificacao
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from core.aura_engine import (
    AuraEngine,
    AuraChunk,
    AuraChunkType,
    GENUI_COMPONENT_REGISTRY_MAP,
    build_canonical_genui_envelope,
)
from core.aura_api import create_aura_app
from core.schemas.idempotency import validate_tool_call_id, generate_tool_call_id
from core.semantic_router import SemanticRouter
from core.rag_engine import HybridRAGEngine


class MockGeminiStream:
    """Simulador de stream assincrono do modelo de IA para teste rapido sem latencia WAN."""
    def __init__(self, texts: List[str]):
        self.texts = texts

    def __aiter__(self):
        self._iter = iter(self.texts)
        return self

    async def __anext__(self):
        try:
            val = next(self._iter)
            mock_chunk = MagicMock()
            mock_chunk.text = val
            return mock_chunk
        except StopIteration:
            raise StopAsyncIteration


async def mock_gemini_generate_content_async(prompt, stream=True, **kwargs):
    """Gera tokens conversacionais sinteticos sem blocos de JSON cru."""
    tokens = [
        "Diagnostico executivo apurado. ",
        "Margem operacional sob controle no periodo, ",
        "indicadores estaveis e em conformidade."
    ]
    return MockGeminiStream(tokens)


def fast_no_pgvector_conn(self, *args, **kwargs):
    """Previne delay de timeout TCP em testes automatizados locais sem banco Postgres."""
    raise ConnectionRefusedError("Modo de teste rapido local (pgvector offline)")


# =============================================================================
# ETAPA 1: EMISSAO MULTIPLEXADA NO BACKEND (ask_stream)
# =============================================================================

async def test_backend_multiplexed_streaming(engine: AuraEngine):
    print("\n1. Testando Emissao Multiplexada no Backend (intent -> ui_skeleton -> delta -> ui_complete -> done)...")

    test_cases = [
        ("Qual o diagnostico do meu negocio hoje?", "mentoria_decisao", "render_ExecutiveDecisionMentorUI"),
        ("O que vende junto com cerveja?", "conveniencia_vendas_cruzadas", "render_BasketUpsellStrategyUI"),
    ]

    for query, expected_intent, expected_comp in test_cases:
        print(f"   ► Validando consulta: '{query}'")
        sess_id = f"test_stream_{expected_intent}"
        chunks: List[AuraChunk] = []

        async for chunk in engine.ask_stream(query, session_id=sess_id):
            chunks.append(chunk)

        tipos = [c.chunk_type for c in chunks]
        print(f"     Sequencia recebida ({len(chunks)} chunks): {[t.value for t in tipos]}")

        # 1. Presenca obrigatoria de todos os tipos canônicos
        assert AuraChunkType.INTENT in tipos, f"Chunk INTENT ausente para {query}"
        assert AuraChunkType.UI_SKELETON in tipos, f"Chunk UI_SKELETON ausente para {query}"
        assert AuraChunkType.DELTA in tipos, f"Chunk DELTA ausente para {query}"
        assert AuraChunkType.UI_COMPLETE in tipos, f"Chunk UI_COMPLETE ausente para {query}"
        assert AuraChunkType.DONE in tipos, f"Chunk DONE ausente para {query}"

        # 2. Ordem cronologica estrita: intent < ui_skeleton < delta < ui_complete < done
        idx_intent = tipos.index(AuraChunkType.INTENT)
        idx_skeleton = tipos.index(AuraChunkType.UI_SKELETON)
        idx_first_delta = tipos.index(AuraChunkType.DELTA)
        idx_complete = tipos.index(AuraChunkType.UI_COMPLETE)
        idx_done = tipos.index(AuraChunkType.DONE)

        assert idx_intent < idx_skeleton, f"intent ({idx_intent}) deve anteceder ui_skeleton ({idx_skeleton})"
        assert idx_skeleton < idx_first_delta, f"ui_skeleton ({idx_skeleton}) deve anteceder primeiro delta ({idx_first_delta})"
        assert idx_first_delta < idx_complete, f"delta ({idx_first_delta}) deve anteceder ui_complete ({idx_complete})"
        assert idx_complete < idx_done, f"ui_complete ({idx_complete}) deve anteceder done ({idx_done})"

        # 3. Metadados de ui_skeleton
        skel = next(c for c in chunks if c.chunk_type == AuraChunkType.UI_SKELETON)
        assert skel.tool_call_id is not None
        assert validate_tool_call_id(skel.tool_call_id)
        assert skel.data.get("component_name") == expected_comp

        # 4. Metadados de ui_complete coincidem com ui_skeleton
        comp = next(c for c in chunks if c.chunk_type == AuraChunkType.UI_COMPLETE)
        assert comp.tool_call_id == skel.tool_call_id, "tool_call_id de ui_complete deve coincidir com ui_skeleton"
        assert comp.data.get("component_name") == expected_comp
        assert "props" in comp.data
        assert "actions" in comp.data
        assert isinstance(comp.data["actions"], list)
        assert len(comp.data["actions"]) >= 1

    print("   [OK] Cronologia multiplexada e metadados validados com 100% de sucesso.")


# =============================================================================
# ETAPA 2: ZERO VAZAMENTO DE JSON & BUFFERIZACAO NO CLIENTE SIMULADO
# =============================================================================

async def test_zero_json_leakage_and_fragment_buffer(engine: AuraEngine):
    print("\n2. Testando Blindagem contra Vazamento de JSON no Texto Conversacional e FragmentBuffer...")

    query = "Qual a previsao dos tanques de diesel?"
    chunks: List[AuraChunk] = []
    async for chunk in engine.ask_stream(query, session_id="test_no_leak_sess"):
        chunks.append(chunk)

    # 2.1 Verifica que nenhum chunk DELTA vaza JSON
    deltas = [c.text for c in chunks if c.chunk_type == AuraChunkType.DELTA and c.text]
    full_delta_text = "".join(deltas).strip()

    assert not full_delta_text.startswith("{"), "Texto de delta iniciou com chave JSON {"
    assert not full_delta_text.endswith("}"), "Texto de delta finalizou com chave JSON }"
    assert "```json" not in full_delta_text, "Bloco ```json encontrado no texto do delta"
    assert '"tool_call_id":' not in full_delta_text, 'Propriedade "tool_call_id" vazou no texto do delta'
    assert '"component_name":' not in full_delta_text, 'Propriedade "component_name" vazou no texto do delta'

    # 2.2 Teste do GenUIFragmentBuffer via Node.js
    genui_js = BASE_DIR / "web" / "js" / "aura-genui.js"
    assert genui_js.exists(), f"{genui_js} nao encontrado"

    node_buffer_test = f"""
    const assert = require('assert');
    const {{ GenUIFragmentBuffer }} = require({json.dumps(str(genui_js.resolve()))});

    const buf = new GenUIFragmentBuffer();
    const tid = 'call_test_fragment_123';

    // Fragmento 1: JSON incompleto
    let r1 = buf.append(tid, '{{"diagnosis": "Margem sob controle",');
    assert.strictEqual(r1.isComplete, false, 'Fragmento parcial 1 nao deve ser completo');
    assert.strictEqual(r1.parsed, null);

    // Fragmento 2: mais um pedaco incompleto
    let r2 = buf.append(tid, ' "confidence_score": 0.95, "items": [1, 2,');
    assert.strictEqual(r2.isComplete, false, 'Fragmento parcial 2 nao deve ser completo');
    assert.strictEqual(r2.parsed, null);

    // Fragmento 3: fechamento do JSON
    let r3 = buf.append(tid, ' 3]}}');
    assert.strictEqual(r3.isComplete, true, 'JSON finalizado deve ser completo');
    assert.notStrictEqual(r3.parsed, null);
    assert.strictEqual(r3.parsed.diagnosis, 'Margem sob controle');
    assert.strictEqual(r3.parsed.confidence_score, 0.95);
    assert.deepStrictEqual(r3.parsed.items, [1, 2, 3]);

    // getParsed direto
    const parsedDirect = buf.getParsed(tid);
    assert.strictEqual(parsedDirect.diagnosis, 'Margem sob controle');

    // Limpeza
    buf.clear(tid);
    assert.strictEqual(buf.get(tid), '');
    assert.strictEqual(buf.getParsed(tid), null);

    console.log('NODE_FRAGMENT_BUFFER_OK');
    """

    res_node = subprocess.run(
        ["node", "-e", node_buffer_test],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    assert res_node.returncode == 0, f"Falha no teste do fragment buffer Node.js: {res_node.stderr}"
    assert "NODE_FRAGMENT_BUFFER_OK" in res_node.stdout

    print("   [OK] Zero vazamento de JSON em deltas e GenUIFragmentBuffer validado com sucesso.")


# =============================================================================
# ETAPA 3: RESILIENCIA CONTRA INTERRUPCAO PREMATURA E DESCONEXAO DO CLIENTE
# =============================================================================

async def test_early_disconnect_and_error_resilience(engine: AuraEngine):
    print("\n3. Testando Resiliencia contra Interrupcao Prematura, Aborto e Falhas...")

    # 3.1 Interrupcao precoce do cliente (AbortController / early break)
    # Simula cliente fechando a conexao logo apos o evento ui_skeleton
    received_before_abort = []
    async for chunk in engine.ask_stream("Qual a previsao de tanques?", session_id="test_abort_early"):
        received_before_abort.append(chunk)
        if chunk.chunk_type == AuraChunkType.UI_SKELETON:
            # Cliente cancela iteracao / aborta stream
            break

    assert len(received_before_abort) >= 2
    types_before_abort = [c.chunk_type for c in received_before_abort]
    assert AuraChunkType.INTENT in types_before_abort
    assert AuraChunkType.UI_SKELETON in types_before_abort
    assert AuraChunkType.DONE not in types_before_abort

    # Prova que o gerador nao deixou estado inconsistente: proxima consulta na mesma engine roda normalmente
    chunks_after = []
    async for chunk in engine.ask_stream("Como esta a operacao?", session_id="test_after_abort"):
        chunks_after.append(chunk)
    assert any(c.chunk_type == AuraChunkType.DONE for c in chunks_after)

    # 3.2 Resiliencia quando o input e vazio
    empty_chunks = []
    async for chunk in engine.ask_stream("", session_id="test_empty_query"):
        empty_chunks.append(chunk)
    empty_types = [c.chunk_type for c in empty_chunks]
    assert AuraChunkType.DELTA in empty_types
    assert AuraChunkType.DONE in empty_types
    assert AuraChunkType.UI_COMPLETE not in empty_types

    # 3.3 Resiliencia contra intencao inexistente / desconhecida
    fake_tool_id = generate_tool_call_id()
    env_fake = build_canonical_genui_envelope(
        intencao="intencao_inexistente_alucinada",
        tool_call_id=fake_tool_id,
        resultado_bruto={"status": "teste"},
        executive_summary="Resumo de teste",
    )
    assert env_fake is None, "Intencao inexistente deve retornar None sem levantar excecao nao tratada"

    print("   [OK] Interrupcao prematura e resiliencia a falhas validadas com sucesso.")


# =============================================================================
# ETAPA 4: TESTE HTTP REAL FASTAPI SSE COM FRAGMENTACAO DE PACOTES TCP
# =============================================================================

def test_fastapi_sse_stream_with_tcp_fragmentation(engine: AuraEngine):
    print("\n4. Testando Endpoint FastAPI SSE com Fragmentacao Arbitraria de Pacotes TCP (16, 32, 64 bytes)...")

    app = create_aura_app(engine)
    client = TestClient(app)

    # 4.1 Requisicao SSE via POST /api/v1/aura/chat com stream=true
    response = client.post(
        "/api/v1/aura/chat",
        json={
            "query": "Qual o diagnostico do meu negocio hoje?",
            "stream": True,
            "session_id": "test_tcp_fragmentation"
        }
    )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")

    raw_sse_bytes = response.content
    assert len(raw_sse_bytes) > 0, "Corpo da resposta SSE veio vazio"

    # 4.2 Simula transmissao TCP fragmentada com buffers pequenos
    # e valida se um parser SSE acumula e reconstroi perfeitamente os eventos
    for chunk_size in [16, 32, 64, 128]:
        parser_buffer = ""
        events_reconstructed = []
        current_event_type = None

        # Fatiamento arbitrario da resposta em pacotes de tamanho fixo
        offset = 0
        while offset < len(raw_sse_bytes):
            packet = raw_sse_bytes[offset:offset + chunk_size].decode("utf-8", errors="replace")
            offset += chunk_size
            parser_buffer += packet

            # Processa linhas completas
            while "\n\n" in parser_buffer:
                event_block, parser_buffer = parser_buffer.split("\n\n", 1)
                lines = event_block.strip().split("\n")
                ev_type = None
                ev_data = None
                for line in lines:
                    if line.startswith("event: "):
                        ev_type = line.replace("event: ", "").strip()
                    elif line.startswith("data: "):
                        data_str = line.replace("data: ", "").strip()
                        try:
                            ev_data = json.loads(data_str)
                        except Exception:
                            ev_data = data_str

                if ev_type:
                    events_reconstructed.append({"type": ev_type, "data": ev_data})

        reconstructed_types = [e["type"] for e in events_reconstructed]
        assert "intent" in reconstructed_types, f"intent ausente no chunk_size {chunk_size}"
        assert "ui_skeleton" in reconstructed_types, f"ui_skeleton ausente no chunk_size {chunk_size}"
        assert "delta" in reconstructed_types, f"delta ausente no chunk_size {chunk_size}"
        assert "ui_complete" in reconstructed_types, f"ui_complete ausente no chunk_size {chunk_size}"
        assert "done" in reconstructed_types, f"done ausente no chunk_size {chunk_size}"

        # Valida que ui_complete foi parseado como objeto JSON valido em todos os cenarios de fragmentacao
        ui_comp_ev = next(e for e in events_reconstructed if e["type"] == "ui_complete")
        assert isinstance(ui_comp_ev["data"], dict)
        assert ui_comp_ev["data"].get("component_name") == "render_ExecutiveDecisionMentorUI"

    print("   [OK] Parsing SSE sob fragmentacao de pacotes TCP (16-128 bytes) reconstruiu 100% dos eventos.")


# =============================================================================
# MAIN RUNNER
# =============================================================================

def run_all_streaming_tests():
    print("=" * 78)
    print("SUITE DE TESTES: STREAMING E BUFFERIZACAO GENUI (FASE 8: F8-02)")
    print("=" * 78)

    with patch.object(SemanticRouter, "_get_connection", fast_no_pgvector_conn), \
         patch.object(HybridRAGEngine, "_get_connection", fast_no_pgvector_conn), \
         patch("google.generativeai.GenerativeModel.generate_content_async", side_effect=mock_gemini_generate_content_async):

        engine = AuraEngine()

        asyncio.run(test_backend_multiplexed_streaming(engine))
        asyncio.run(test_zero_json_leakage_and_fragment_buffer(engine))
        asyncio.run(test_early_disconnect_and_error_resilience(engine))
        test_fastapi_sse_stream_with_tcp_fragmentation(engine)

    print("\n" + "=" * 78)
    print("SUITE F8-02 (STREAMING E BUFFERIZACAO) CONCLUIDA COM 100% DE SUCESSO!")
    print("=" * 78 + "\n")


if __name__ == "__main__":
    run_all_streaming_tests()
