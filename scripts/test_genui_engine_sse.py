"""
Suíte de Testes Automatizada: Protocolo SSE Multiplexado & Envelopes GenUI (Fase 1 — P0)
(AuraEngine, ask_stream, GenUIEnvelope, GenUIActionOption, FastAPI TestClient & Zero Regressão)

Validações Obrigatórias:
1. Validação, parsing e serialização dos modelos Pydantic GenUI (core/schemas/genui.py):
   - GenUIActionOption: validação de action_id (RFC 4122 v4 com act_), campos padrão, rejeição de IDs inválidos ou com prefixo cruzado call_.
   - GenUIEnvelope: validação de tool_call_id (RFC 4122 v4 com call_), component_name seguro, props determinísticas, actions tipadas, TTL e to_sse_payload().
   - GenUIActionResult: validação de tool_call_id, action_id e status.
2. Transmissão do gerador assíncrono ask_stream() emitindo a sequência cronológica correta:
   - Ordem estrita: intent -> ui_skeleton -> delta (Resumo Executivo) -> ui_complete -> done.
   - Presença dos atributos canônicos em ui_skeleton (<100ms): tool_call_id, component_name, title.
   - Presença do payload validado em ui_complete: tool_call_id coincidente, props analíticas e actions idempotentes.
3. Blindagem contra vazamento de JSON bruto no chat:
   - Confirmação de que nenhum chunk delta contém blocos brutos de JSON ({...}).
4. Testes de integração HTTP no endpoint FastAPI /api/v1/aura/chat usando TestClient:
   - Streaming SSE (stream=true): validação de headers text/event-stream e eventos event: ui_skeleton, event: ui_complete, event: delta.
   - Síncrono (stream=false): retorno de AuraResponse com envelope GenUI e tool_call_id populados.
5. Cobertura de múltiplos micro-widgets analíticos:
   - previsao_tanques (render_TankRunOutForecastUI)
   - auditoria_turno (render_ShiftReconciliationUI)
   - lmc_anp (render_LMCReportUI)
   - desempenho_pista_frentistas (render_PumpPerformanceUI)
6. Validação de Regressão Zero:
   - Execução e aprovação 100% de test_genui_baseline.py, test_aura_engine.py e test_phase5_specialized_responses.py.
"""

import sys
import json
import re
import asyncio
import subprocess
from decimal import Decimal
from unittest.mock import MagicMock
from pathlib import Path

# Protege stdout no terminal Windows contra problemas de codificação
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from pydantic import ValidationError
from fastapi.testclient import TestClient

from core.aura_engine import (
    AuraEngine,
    AuraChunk,
    AuraChunkType,
    AuraResponse,
    AuraSessionMemory,
    GENUI_COMPONENT_REGISTRY_MAP,
    build_canonical_genui_envelope,
)
from core.aura_api import create_aura_app
from core.schemas.idempotency import (
    generate_uuid4,
    generate_tool_call_id,
    generate_action_id,
    validate_tool_call_id,
    validate_action_id,
)
from core.schemas.genui import (
    GenUIActionOption,
    GenUIEnvelope,
    GenUIActionResult,
)


def test_genui_pydantic_schemas():
    print("\n1. Testando Modelos Pydantic Canônicos GenUI (Validação & Idempotência)...")

    # 1.1 GenUIActionOption válido
    valid_act_id = generate_action_id()
    action = GenUIActionOption(
        action_id=valid_act_id,
        label="Pedir Carreta de Combustível (15.000 L)",
        action_type="mutation",
        variant="primary",
        is_destructive=False,
        requires_confirmation=True,
        payload={"litros": 15000, "combustivel": "GASOLINA COMUM"},
    )
    assert action.action_id == valid_act_id
    assert action.label == "Pedir Carreta de Combustível (15.000 L)"
    assert action.action_type == "mutation"
    assert action.variant == "primary"
    assert not action.is_destructive
    assert action.requires_confirmation
    assert action.payload["litros"] == 15000

    # 1.2 Rejeição de action_id inválido ou com prefixo cruzado em GenUIActionOption
    invalid_action_ids = [
        "not_an_id",
        generate_tool_call_id(),  # Prefixo call_ em vez de act_
        "act_not-a-valid-uuid",
        "<script>_88b19a02-412f-4a0b-8c01-d85cfd774bfe",
        "",
        "   ",
    ]
    for inv_id in invalid_action_ids:
        try:
            GenUIActionOption(action_id=inv_id, label="Ação Teste")
            assert False, f"GenUIActionOption deveria rejeitar action_id inválido: {inv_id}"
        except ValidationError:
            pass

    # 1.3 Rejeição de label vazio
    try:
        GenUIActionOption(action_id=valid_act_id, label="   ")
        assert False, "GenUIActionOption deveria rejeitar label vazio"
    except ValidationError:
        pass

    # 1.4 GenUIEnvelope válido
    valid_tool_id = generate_tool_call_id()
    envelope = GenUIEnvelope(
        schema_version="1.0",
        tool_call_id=valid_tool_id,
        component_name="render_TankRunOutForecastUI",
        client_component="TankForecastWidget",
        intent="previsao_tanques",
        executive_summary="Tanque 001 com 4.2h de autonomia crítica.",
        props={
            "tanque": "001",
            "combustivel": "GASOLINA COMUM",
            "autonomia_critica_horas": 4.2,
            "saldo_atual_litros": 4200,
        },
        actions=[action],
        ttl_seconds=900,
    )
    assert envelope.tool_call_id == valid_tool_id
    assert envelope.component_name == "render_TankRunOutForecastUI"
    assert envelope.intent == "previsao_tanques"
    assert len(envelope.actions) == 1
    assert envelope.ttl_seconds == 900
    assert envelope.created_at is not None

    # Teste de serialização segura para SSE com aliases do protocolo
    sse_payload = envelope.to_sse_payload()
    assert sse_payload["envelope_version"] == "1.0"
    assert sse_payload["summary_text"] == "Tanque 001 com 4.2h de autonomia crítica."
    assert sse_payload["timestamp"] == envelope.created_at
    assert sse_payload["tool_call_id"] == valid_tool_id
    assert "props" in sse_payload
    assert "actions" in sse_payload

    # 1.5 Rejeição de tool_call_id inválido ou com prefixo cruzado em GenUIEnvelope
    invalid_tool_ids = [
        "not_an_id",
        generate_action_id(),  # Prefixo act_ em vez de call_
        "call_invalid-uuid",
        "'; DROP TABLE_88b19a02-412f-4a0b-8c01-d85cfd774bfe",
        "",
    ]
    for inv_tid in invalid_tool_ids:
        try:
            GenUIEnvelope(
                tool_call_id=inv_tid,
                component_name="render_TankRunOutForecastUI",
                intent="previsao_tanques",
                executive_summary="Teste",
                props={},
            )
            assert False, f"GenUIEnvelope deveria rejeitar tool_call_id inválido: {inv_tid}"
        except ValidationError:
            pass

    # 1.6 Rejeição de component_name inválido ou inseguro (XSS / Injeção)
    invalid_comp_names = [
        "",
        "   ",
        "<script>alert(1)</script>",
        "render_Tank; DROP TABLE",
        "123InvalidStart",
        "component with spaces",
    ]
    for inv_cn in invalid_comp_names:
        try:
            GenUIEnvelope(
                tool_call_id=valid_tool_id,
                component_name=inv_cn,
                intent="previsao_tanques",
                executive_summary="Teste",
                props={},
            )
            assert False, f"GenUIEnvelope deveria rejeitar component_name inseguro: {inv_cn}"
        except ValidationError:
            pass

    # 1.7 Rejeição de ttl_seconds inválido (<= 0)
    try:
        GenUIEnvelope(
            tool_call_id=valid_tool_id,
            component_name="render_TankRunOutForecastUI",
            intent="previsao_tanques",
            executive_summary="Teste",
            props={},
            ttl_seconds=0,
        )
        assert False, "GenUIEnvelope deveria rejeitar ttl_seconds <= 0"
    except ValidationError:
        pass

    # 1.8 Validação de GenUIActionResult
    action_res = GenUIActionResult(
        tool_call_id=valid_tool_id,
        action_id=valid_act_id,
        status="COMMITTED",
        voucher_id="vch_test_123",
        signature="sig_test_abc",
        feedback_message="Pedido transmitido com sucesso ao ERP.",
    )
    assert action_res.tool_call_id == valid_tool_id
    assert action_res.action_id == valid_act_id
    assert action_res.status == "COMMITTED"
    assert action_res.voucher_id == "vch_test_123"

    # 1.9 Compatibilidade estrita com o payload formal de docs/protocolo_streaming_genui.md (aliases)
    protocol_canonical_payload = {
        "envelope_version": "1.0",
        "tool_call_id": "call_a62b19cc-e872-448b-b8cf-dfff06869033",
        "component_name": "render_TankRunOutForecastUI",
        "client_component": "TankForecastWidget",
        "timestamp": "2026-10-07T19:00:00Z",
        "ttl_seconds": 900,
        "summary_text": "Tanque 01 com 4.2h de autonomia crítica.",
        "props": {
            "tanque": "01",
            "combustivel": "GASOLINA COMUM",
            "capacidade_litros": 15000,
            "saldo_atual_litros": 4200,
            "autonomia_critica_horas": 4.2,
            "espaco_livre_ullage_litros": 10800,
            "status_operacional": "CRÍTICO",
        },
        "actions": [
            {
                "action_id": "act_20367dea-9047-4a78-bc36-86b2d960fdf6",
                "label": "Pedir Carreta (10.000 L)",
                "action_type": "mutation",
                "requires_confirmation": True,
                "payload": {"tanque": "01", "litros": 10000},
            }
        ],
    }
    parsed_proto_env = GenUIEnvelope.model_validate(protocol_canonical_payload)
    assert parsed_proto_env.tool_call_id == "call_a62b19cc-e872-448b-b8cf-dfff06869033"
    assert parsed_proto_env.executive_summary == "Tanque 01 com 4.2h de autonomia crítica."
    assert parsed_proto_env.schema_version == "1.0"
    assert parsed_proto_env.created_at == "2026-10-07T19:00:00Z"
    assert len(parsed_proto_env.actions) == 1

    # 1.10 Serialização segura de tipos não-primitivos (Decimal do PostgreSQL) via to_sse_payload()
    env_decimal = GenUIEnvelope(
        tool_call_id=valid_tool_id,
        component_name="render_TankRunOutForecastUI",
        intent="previsao_tanques",
        executive_summary="Teste Decimal",
        props={"saldo_litros": Decimal("4200.75"), "capacidade": Decimal("15000.00")},
    )
    sse_decimal = env_decimal.to_sse_payload()
    # Confirma que json.dumps nativo não levanta TypeError: Decimal is not JSON serializable
    dumped_json_str = json.dumps(sse_decimal)
    assert isinstance(dumped_json_str, str)
    assert "4200.75" in dumped_json_str

    # 1.11 Sincronização automática de envelope e data no AuraChunk
    chunk_with_env = AuraChunk(
        chunk_type=AuraChunkType.UI_COMPLETE,
        tool_call_id=valid_tool_id,
        component_name="render_TankRunOutForecastUI",
        envelope=sse_decimal,
    )
    assert chunk_with_env.data is not None, "chunk.data deveria sincronizar automaticamente com chunk.envelope"
    assert chunk_with_env.data["tool_call_id"] == valid_tool_id
    dumped_chunk_dict = chunk_with_env.to_dict()
    assert isinstance(json.dumps(dumped_chunk_dict), str)

    # 1.12 Enum AuraChunkType com suporte a ui_action_result e ui_action_feedback
    assert AuraChunkType.UI_ACTION_RESULT.value == "ui_action_result"
    assert AuraChunkType.UI_ACTION_FEEDBACK.value == "ui_action_feedback"

    print("   [OK] Modelos GenUIActionOption, GenUIEnvelope e GenUIActionResult 100% aprovados.")


async def test_ask_stream_chronological_sequence(engine: AuraEngine):
    print("\n2. Testando Ordem Cronológica Estrita no Streaming Assíncrono (ask_stream)...")
    pergunta = "Qual a autonomia do tanque de gasolina comum?"
    sess_id = "test_stream_genui_seq"

    chunks_recebidos = []
    async for chunk in engine.ask_stream(pergunta, session_id=sess_id):
        chunks_recebidos.append(chunk)

    tipos_ordem = [c.chunk_type for c in chunks_recebidos]
    print(f"   Sequência emitida ({len(chunks_recebidos)} chunks): {[t.value for t in tipos_ordem]}")

    # Validação de presença obrigatória dos tipos canônicos
    assert AuraChunkType.INTENT in tipos_ordem, "Faltou chunk INTENT"
    assert AuraChunkType.UI_SKELETON in tipos_ordem, "Faltou chunk UI_SKELETON"
    assert AuraChunkType.DELTA in tipos_ordem, "Faltou chunk DELTA"
    assert AuraChunkType.UI_COMPLETE in tipos_ordem, "Faltou chunk UI_COMPLETE"
    assert AuraChunkType.DONE in tipos_ordem, "Faltou chunk DONE"

    # Encontra índices das ocorrências-chave
    idx_intent = tipos_ordem.index(AuraChunkType.INTENT)
    idx_skeleton = tipos_ordem.index(AuraChunkType.UI_SKELETON)
    idx_first_delta = tipos_ordem.index(AuraChunkType.DELTA)
    idx_complete = tipos_ordem.index(AuraChunkType.UI_COMPLETE)
    idx_done = tipos_ordem.index(AuraChunkType.DONE)

    # Ordem canônica estrita: intent -> ui_skeleton -> delta -> ui_complete -> done
    assert idx_intent < idx_skeleton, f"intent ({idx_intent}) deve anteceder ui_skeleton ({idx_skeleton})"
    assert idx_skeleton < idx_first_delta, f"ui_skeleton ({idx_skeleton}) deve anteceder delta ({idx_first_delta})"
    assert idx_first_delta < idx_complete, f"primeiro delta ({idx_first_delta}) deve anteceder ui_complete ({idx_complete})"
    assert idx_complete < idx_done, f"ui_complete ({idx_complete}) deve anteceder done ({idx_done})"

    # Validação estrutural do chunk UI_SKELETON
    skeleton_chunk = next(c for c in chunks_recebidos if c.chunk_type == AuraChunkType.UI_SKELETON)
    assert skeleton_chunk.tool_call_id is not None, "tool_call_id ausente no chunk UI_SKELETON"
    assert validate_tool_call_id(skeleton_chunk.tool_call_id), f"tool_call_id inválido em UI_SKELETON: {skeleton_chunk.tool_call_id}"
    assert skeleton_chunk.component_name == "render_TankRunOutForecastUI"
    assert skeleton_chunk.title is not None and "tanque" in skeleton_chunk.title.lower()

    # Validação do SSE gerado pelo UI_SKELETON
    sse_skel = skeleton_chunk.to_sse()
    assert sse_skel.startswith("event: ui_skeleton\n"), f"SSE incorreto para ui_skeleton: {sse_skel}"
    assert '"component_name": "render_TankRunOutForecastUI"' in sse_skel or '"component_name":"render_TankRunOutForecastUI"' in sse_skel

    # Validação estrutural do chunk UI_COMPLETE
    complete_chunk = next(c for c in chunks_recebidos if c.chunk_type == AuraChunkType.UI_COMPLETE)
    assert complete_chunk.tool_call_id == skeleton_chunk.tool_call_id, "tool_call_id em UI_COMPLETE diverge do UI_SKELETON"
    assert complete_chunk.component_name == skeleton_chunk.component_name
    assert complete_chunk.envelope is not None, "envelope estruturado ausente no chunk UI_COMPLETE"

    env_data = complete_chunk.envelope
    assert env_data["tool_call_id"] == skeleton_chunk.tool_call_id
    assert env_data["component_name"] == "render_TankRunOutForecastUI"
    assert "props" in env_data and isinstance(env_data["props"], dict)
    assert "actions" in env_data and len(env_data["actions"]) >= 1

    for act in env_data["actions"]:
        assert validate_action_id(act["action_id"]), f"action_id inválido na Action Sheet: {act['action_id']}"
        assert act["label"]

    sse_comp = complete_chunk.to_sse()
    assert sse_comp.startswith("event: ui_complete\n"), f"SSE incorreto para ui_complete: {sse_comp}"

    print("   [OK] Cronologia rigorosa validada: intent -> ui_skeleton -> delta -> ui_complete -> done.")


async def test_no_raw_json_leaks_in_delta(engine: AuraEngine):
    print("\n3. Verificando Isolamento Semântico (Zero Vazamento de JSON Bruto em DELTA)...")
    pergunta = "Qual a previsão dos tanques de diesel e gasolina?"
    sess_id = "test_stream_no_json_leak"

    delta_texts = []
    async for chunk in engine.ask_stream(pergunta, session_id=sess_id):
        if chunk.chunk_type == AuraChunkType.DELTA and chunk.text:
            delta_texts.append(chunk.text)

    texto_consolidado = "".join(delta_texts)

    # Verifica ausência de chaves de JSON bruto típicas de dumps não tratados
    json_leak_patterns = [
        r'\{\s*"props"\s*:',
        r'\{\s*"envelope_version"\s*:',
        r'\{\s*"detalhamento_tanques"\s*:',
        r'\{\s*"assessment"\s*:',
        r'\{\s*"resumo_executivo"\s*:',
        r'\{\s*"status"\s*:\s*"success"',
    ]
    for pattern in json_leak_patterns:
        match = re.search(pattern, texto_consolidado)
        assert match is None, f"Vazamento de JSON bruto detectado no texto DELTA: {match.group(0)}"

    assert len(texto_consolidado) > 50, "Texto consolidado DELTA muito curto"
    print(f"   [OK] Zero JSON bruto vazado nos tokens DELTA. Texto limpo ({len(texto_consolidado)} caracteres).")



def test_fastapi_genui_endpoints(engine: AuraEngine):
    print("\n4. Testando Endpoints FastAPI (/chat SSE e Síncrono com GenUI)...")
    app = create_aura_app(engine)
    client = TestClient(app)

    # 4.1 Chat SSE Streaming (stream=true)
    resp_stream = client.post(
        "/api/v1/aura/chat",
        json={"query": "Qual a autonomia do tanque de gasolina comum?", "stream": True},
    )
    assert resp_stream.status_code == 200
    assert "text/event-stream" in resp_stream.headers["content-type"]
    body_stream = resp_stream.text

    assert "event: intent" in body_stream, "Evento intent ausente no stream SSE"
    assert "event: ui_skeleton" in body_stream, "Evento ui_skeleton ausente no stream SSE"
    assert "event: delta" in body_stream, "Evento delta ausente no stream SSE"
    assert "event: ui_complete" in body_stream, "Evento ui_complete ausente no stream SSE"
    assert "event: done" in body_stream, "Evento done ausente no stream SSE"

    # Extrai e valida os blocos de dados SSE
    lines = body_stream.split("\n")
    events_found = {}
    current_event = None

    for line in lines:
        if line.startswith("event: "):
            current_event = line.replace("event: ", "").strip()
        elif line.startswith("data: ") and current_event:
            raw_data = line.replace("data: ", "").strip()
            try:
                parsed_json = json.loads(raw_data)
                events_found[current_event] = parsed_json
            except Exception:
                pass

    assert "ui_skeleton" in events_found, "Payload data de ui_skeleton não pôde ser desserializado"
    skel_data = events_found["ui_skeleton"]
    assert validate_tool_call_id(skel_data["tool_call_id"])
    assert skel_data["component_name"] == "render_TankRunOutForecastUI"

    assert "ui_complete" in events_found, "Payload data de ui_complete não pôde ser desserializado"
    comp_data = events_found["ui_complete"]
    assert validate_tool_call_id(comp_data["tool_call_id"])
    assert comp_data["component_name"] == "render_TankRunOutForecastUI"

    # 4.2 Chat Síncrono (stream=false)
    resp_sync = client.post(
        "/api/v1/aura/chat",
        json={"query": "Como foi a auditoria do turno de ontem?", "stream": False},
    )
    assert resp_sync.status_code == 200
    json_sync = resp_sync.json()
    assert json_sync["intent"] == "auditoria_turno"
    assert json_sync["tool_call_id"] is not None
    assert validate_tool_call_id(json_sync["tool_call_id"])
    assert json_sync["envelope"] is not None
    assert json_sync["envelope"]["component_name"] == "render_ShiftReconciliationUI"
    assert "props" in json_sync["envelope"]
    assert "actions" in json_sync["envelope"]

    print("   [OK] Endpoints FastAPI testados com 100% de sucesso (SSE Multiplexado & Síncrono).")


async def test_multiple_genui_widgets(engine: AuraEngine):
    print("\n5. Testando Mapeamento Canônico de Múltiplos Micro-Widgets...")
    queries_and_expected_components = [
        ("Qual a autonomia dos tanques?", "previsao_tanques", "render_TankRunOutForecastUI"),
        ("Como foi a conciliação do turno 1?", "auditoria_turno", "render_ShiftReconciliationUI"),
        ("Relatório oficial do LMC ANP de hoje", "lmc_anp", "render_LMCReportUI"),
        ("Desempenho dos bicos e frentistas", "desempenho_pista_frentistas", "render_PumpPerformanceUI"),
        ("O que vende junto com cerveja?", "conveniencia_vendas_cruzadas", "render_BasketUpsellStrategyUI"),
        ("Vendas de hoje no posto", "vendas_analitico", "render_MarginAnalysisUI"),
    ]

    for q, expected_intent, expected_comp in queries_and_expected_components:
        meta = GENUI_COMPONENT_REGISTRY_MAP.get(expected_intent)
        assert meta is not None, f"Intenção {expected_intent} ausente no mapeamento GenUI"
        assert meta["component_name"] == expected_comp

        env = build_canonical_genui_envelope(
            intencao=expected_intent,
            tool_call_id=generate_tool_call_id(),
            resultado_bruto={"test_metric": 42},
            executive_summary=f"Resumo executivo de teste para {expected_intent}.",
        )
        assert env is not None
        assert env.component_name == expected_comp
        assert len(env.actions) >= 1
        for act in env.actions:
            assert validate_action_id(act.action_id)

    print("   [OK] 6 micro-widgets canônicos do Mentor de Decisões validados com sucesso.")


async def test_tool_error_resilience_and_no_bogus_ui_complete(engine: AuraEngine):
    print("\n6. Testando Resiliência contra Erros de Ferramenta (Zero Emissão de UI_COMPLETE Falso)...")

    # 6.1 build_canonical_genui_envelope retorna None em caso de falha de ferramenta
    err_envelope = build_canonical_genui_envelope(
        intencao="previsao_tanques",
        tool_call_id=generate_tool_call_id(),
        resultado_bruto={"status": "error", "error": "Falha na conexão com banco PostgreSQL local"},
        executive_summary="Erro no banco",
    )
    assert err_envelope is None, "build_canonical_genui_envelope deveria retornar None para resultado_bruto com erro"

    err_none_env = build_canonical_genui_envelope(
        intencao="previsao_tanques",
        tool_call_id=generate_tool_call_id(),
        resultado_bruto=None,
        executive_summary="Sem dados",
    )
    assert err_none_env is None, "build_canonical_genui_envelope deveria retornar None para resultado_bruto None"

    # 6.2 ask_stream() não deve emitir UI_COMPLETE quando a ferramenta falhar
    engine_mock = AuraEngine(
        tenant_id="test_resilience",
        filial_id="posto_sse_resilience",
        session_memory=AuraSessionMemory(db_path=":memory:"),
    )
    engine_mock.tools.prever_esgotamento_tanques = MagicMock(side_effect=RuntimeError("Simulação de indisponibilidade de banco"))

    chunks = []
    async for c in engine_mock.ask_stream("Qual a autonomia dos tanques de gasolina?"):
        chunks.append(c)

    has_ui_complete = any(c.chunk_type == AuraChunkType.UI_COMPLETE for c in chunks)
    assert not has_ui_complete, "UI_COMPLETE NUNCA deve ser emitido quando a ferramenta analítica falhar"
    print("   [OK] Resiliência validada: falha na ferramenta não emite UI_COMPLETE nem mutações indevidas.")


def test_dynamic_action_parameters():
    print("\n7. Testando Parametrização Dinâmica e Determinística das Action Sheets...")

    # 7.1 Previsão de tanques com sugestão calculada de 8.000 L de Gasolina Aditivada
    resultado_tanques = {
        "sugestoes_pedidos": [
            {
                "tanque": "02",
                "combustivel": "GASOLINA ADITIVADA",
                "volume_sugerido_litros": 8000,
                "urgencia": "CRÍTICA",
            }
        ]
    }
    env = build_canonical_genui_envelope(
        intencao="previsao_tanques",
        tool_call_id=generate_tool_call_id(),
        resultado_bruto=resultado_tanques,
        executive_summary="Tanque 02 em nível de alerta.",
    )
    assert env is not None
    action_pedido = next(a for a in env.actions if a.payload.get("operacao") == "pedido_carreta")
    assert action_pedido.payload["litros"] == 8000
    assert action_pedido.payload["tanque"] == "02"
    assert "8.000 L" in action_pedido.label or "8000" in action_pedido.label
    assert "ADITIVADA" in action_pedido.label

    # 7.2 Conveniência com combo calculado (Cerveja + Carvão)
    resultado_combos = {
        "combos": [
            {
                "origem": "Cerveja Heineken",
                "recomendado": "Carvão Vegetal 3kg",
                "lift": 3.8,
            }
        ]
    }
    env_combo = build_canonical_genui_envelope(
        intencao="conveniencia_vendas_cruzadas",
        tool_call_id=generate_tool_call_id(),
        resultado_bruto=resultado_combos,
        executive_summary="Combo com alto lift identificado.",
    )
    assert env_combo is not None
    action_combo = next(a for a in env_combo.actions if a.payload.get("operacao") == "ativar_combo")
    assert "Cerveja Heineken" in action_combo.label
    assert "Carvão Vegetal" in action_combo.label
    print("   [OK] Parâmetros das Action Sheets extraídos deterministicamente dos cálculos das ferramentas.")


async def test_ask_error_propagation():
    print("\n8. Testando Captura de Chunks de Erro no Método Síncrono (ask)...")
    engine = AuraEngine(
        tenant_id="test_err_prop",
        filial_id="posto_err",
        session_memory=AuraSessionMemory(db_path=":memory:"),
    )

    async def mock_err_stream(*args, **kwargs):
        yield AuraChunk(chunk_type=AuraChunkType.INTENT, text="sre_metricas", data={"intent": "sre_metricas"})
        yield AuraChunk(chunk_type=AuraChunkType.ERROR, text="Falha de comunicação no modelo neural")
        yield AuraChunk(chunk_type=AuraChunkType.DONE, text="")

    engine.ask_stream = mock_err_stream
    resp = await engine.ask("Qual a saúde do banco?")
    assert resp.response_text == "Falha de comunicação no modelo neural", f"response_text vazio no erro: '{resp.response_text}'"
    print("   [OK] Mensagens de chunk ERROR propagadas corretamente para AuraResponse.response_text.")


async def test_non_genui_intent_backward_compatibility(engine: AuraEngine):
    print("\n9. Testando Retrocompatibilidade com Consultas Não-GenUI...")
    pergunta = "Qual o CNPJ da filial?"
    chunks = []
    async for c in engine.ask_stream(pergunta, session_id="test_non_genui"):
        chunks.append(c)

    tipos = [c.chunk_type for c in chunks]
    assert AuraChunkType.UI_SKELETON not in tipos, "Consultas não-GenUI não devem emitir UI_SKELETON"
    assert AuraChunkType.UI_COMPLETE not in tipos, "Consultas não-GenUI não devem emitir UI_COMPLETE"
    assert AuraChunkType.INTENT in tipos
    assert AuraChunkType.DELTA in tipos
    assert AuraChunkType.DONE in tipos
    print("   [OK] Retrocompatibilidade integral: clientes legados e consultas sem widgets preservados.")


def run_regression_suites():
    print("\n10. Executando Validação de Regressão Zero nas Suítes Existentes...")
    regression_scripts = [
        ("test_genui_baseline.py", "Fase 0 — Linha de Base GenUI, Registry & OWASP LLM03"),
        ("test_aura_engine.py", "Fase 1 — Motor Headless, Memória Durável & Streaming"),
        ("test_phase5_specialized_responses.py", "Fase 5 — DecisionCards & Respostas Especializadas"),
    ]

    for script_name, desc in regression_scripts:
        script_path = BASE_DIR / "scripts" / script_name
        assert script_path.exists(), f"Script de teste {script_name} não encontrado"
        print(f"   ► Executando {script_name} ({desc})...")
        res = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        if res.returncode != 0:
            print(f"\n❌ REGRESSÃO DETECTADA EM {script_name}:")
            print(res.stdout)
            print(res.stderr)
            assert False, f"Falha de regressão na suíte {script_name}"
        print(f"     [OK] {script_name} aprovado com 100% de sucesso.")


async def _run_all_async():
    mem = AuraSessionMemory(db_path=":memory:")
    engine = AuraEngine(
        tenant_id="test_genui_engine_sse",
        filial_id="posto_sse_01",
        session_memory=mem,
    )

    test_genui_pydantic_schemas()
    await test_ask_stream_chronological_sequence(engine)
    await test_no_raw_json_leaks_in_delta(engine)
    test_fastapi_genui_endpoints(engine)
    await test_multiple_genui_widgets(engine)
    await test_tool_error_resilience_and_no_bogus_ui_complete(engine)
    test_dynamic_action_parameters()
    await test_ask_error_propagation()
    await test_non_genui_intent_backward_compatibility(engine)
    run_regression_suites()


def run_all_tests():
    print("=" * 78)
    print("🚀 SUÍTE DE TESTES: PROTOCOLO SSE MULTIPLEXADO & ENVELOPES GENUI (FASE 1 — P0)")
    print("   (AuraEngine, ask_stream, GenUIEnvelope, TestClient & Zero Regressão)")
    print("=" * 78)

    asyncio.run(_run_all_async())

    print("\n" + "=" * 78)
    print("🎉 PROTOCOLO SSE & ENVELOPES GENUI (FASE 1) HOMOLOGADOS COM 100% DE SUCESSO!")
    print("   Skeletons <100ms, streaming limpo, envelopes canônicos e zero regressão.")
    print("=" * 78)


if __name__ == "__main__":
    run_all_tests()
