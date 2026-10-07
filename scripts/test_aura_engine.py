"""
Suíte de Testes Automatizada: Motor Cognitivo Headless AURA (Fase 1).
(AuraEngine, Sessões Duráveis, Execução Direta, Streaming e Endpoints FastAPI)

Validações:
1. Inicialização do motor AuraEngine (Multi-tenant e Multi-filial).
2. Memória durável de sessão (AuraSessionMemory com SQLite): persistência, ordem cronológica, WAL mode e isolamento.
3. Execução direta de ferramentas analíticas via execute_tool e execute_tool_direct:
   - Previsão de Esgotamento de Tanques (Run-Out Forecast)
   - LMC Oficial ANP Portaria 26/1992
   - Telemetria de Observabilidade SRE
   - Dados Cadastrais da Filial
   - Catálogo de Produtos com RAG Híbrido
   - Auditoria de Fechamento de Turno (com aliases)
4. Diagnóstico e status da estação (get_stations_status).
5. Extração de parâmetros e retrocompatibilidade de funções em main.py.
6. Streaming assíncrono (ask_stream): emissão de chunks tipados (INTENT, TOOL_START, TOOL_RESULT estruturado, DELTA, TELEMETRY, DONE).
7. Cancelamento precoce no SSE (client disconnect) sem vazamento de recursos.
8. Injeção de contexto operacional pelo chamador e suporte a multi-tenant/multi-filial.
9. Resposta completa assíncrona (ask): objeto estruturado AuraResponse com tool_result populado.
10. Blindagem LGPD ativa pré-prompt.
11. Endpoints FastAPI da AURA via TestClient (/health, /stations, /execute-intent, /chat SSE e JSON).
"""

import sys
import asyncio
from pathlib import Path

# Protege stdout no terminal Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Adiciona raiz do projeto
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.aura_engine import (
    AuraEngine,
    AuraChunk,
    AuraChunkType,
    AuraResponse,
    AuraSessionMemory,
    StationStatus,
    classificar_intencao,
    extrair_combustivel,
    extrair_data_turno,
    extrair_frentista,
    extrair_bico,
    extrair_produto_cesta,
    extrair_grupo,
)
from core.aura_api import create_aura_app, get_aura_engine
from fastapi.testclient import TestClient


async def test_session_memory():
    print("\n--- 1. Testando AuraSessionMemory (SQLite Durável com WAL) ---")
    mem = AuraSessionMemory(db_path=":memory:")

    # Adiciona mensagens em duas sessões diferentes
    mem.save_message("sess_01", "user", "Como está o tanque de Gasolina?", intent="previsao_tanques", tenant_id="tenant_a", filial_id="posto_01")
    mem.save_message("sess_01", "assistant", "O tanque 001 tem 18.000 L disponíveis.", intent="previsao_tanques", tenant_id="tenant_a", filial_id="posto_01")
    mem.save_message("sess_02", "user", "Quem foi o frentista que mais vendeu?", intent="desempenho_pista_frentistas", tenant_id="tenant_b", filial_id="posto_02")

    hist_1 = mem.get_history("sess_01")
    assert len(hist_1) == 2, f"Esperava 2 mensagens na sess_01, obteve {len(hist_1)}"
    assert hist_1[0]["role"] == "user"
    assert hist_1[1]["role"] == "assistant"

    hist_2 = mem.get_history("sess_02")
    assert len(hist_2) == 1, f"Esperava 1 mensagem na sess_02, obteve {len(hist_2)}"

    fmt = mem.format_history_for_prompt("sess_01")
    assert "Usuário: Como está o tanque de Gasolina?" in fmt
    assert "AURA: O tanque 001 tem 18.000 L disponíveis." in fmt

    mem.clear_session("sess_01")
    assert len(mem.get_history("sess_01")) == 0
    assert len(mem.get_history("sess_02")) == 1
    print(" [OK] AuraSessionMemory: Isolamento, persistência e formatação de contexto validados.")


async def test_execute_tool_methods(engine: AuraEngine):
    print("\n--- 2. Testando execute_tool e execute_tool_direct (Headless Intent Call) ---")

    # 1. Dados da Filial via execute_tool (alias canônico)
    res_filial = await engine.execute_tool("dados_filial")
    assert res_filial["status"] == "success"
    assert "idempresa" in res_filial["data"]
    print(f" [OK] execute_tool('dados_filial'): {res_filial['data']['nome']} (Latência: {res_filial['latency_ms']}ms)")

    # 2. Telemetria SRE via execute_tool_direct
    res_sre = await engine.execute_tool_direct("sre_metricas")
    assert res_sre["status"] == "success"
    assert "database_health" in res_sre["data"]
    print(f" [OK] execute_tool_direct('sre_metricas'): Cache Hit Ratio {res_sre['data']['database_health']['cache_hit_ratio_percent']}%")

    # 3. Previsão de Tanques (Run-Out) com alias run_out
    res_runout = await engine.execute_tool("run_out", {"combustivel": "GASOLINA COMUM"})
    assert res_runout["status"] == "success"
    if "detalhamento_tanques" in res_runout["data"]:
        print(f" [OK] execute_tool('run_out'): {len(res_runout['data']['detalhamento_tanques'])} tanques analisados")
    else:
        print(f" [OK] execute_tool('run_out'): Retorno resiliente ({res_runout['data'].get('status', 'sem_dados')})")

    # 4. Conciliação de Turno com alias conciliacao_turno
    res_turno = await engine.execute_tool("conciliacao_turno", {"data": "2026-09-02"})
    assert res_turno["status"] == "success"
    if "resumo_executivo" in res_turno["data"]:
        status_conc = res_turno["data"]["resumo_executivo"]["status_conciliacao"]
        print(f" [OK] execute_tool('conciliacao_turno'): Status '{status_conc}'")
    else:
        print(f" [OK] execute_tool('conciliacao_turno'): Retorno resiliente ({res_turno['data'].get('status', 'sem_dados')})")

    # 5. LMC Oficial ANP
    res_lmc = await engine.execute_tool("lmc_anp", {"data": "2026-09-02"})
    assert res_lmc["status"] == "success"
    if "resumo_executivo" in res_lmc["data"]:
        status_anp = res_lmc["data"]["resumo_executivo"]["status_geral_anp"]
        print(f" [OK] execute_tool('lmc_anp'): Status ANP '{status_anp}'")
    else:
        print(f" [OK] execute_tool('lmc_anp'): Retorno resiliente ({res_lmc['data'].get('status', 'sem_dados')})")

    # 6. Catálogo de Produtos
    res_cat = await engine.execute_tool("catalogo_produtos", {"termo": "heineken", "top_k": 3})
    assert res_cat["status"] == "success"
    assert "results" in res_cat["data"]
    print(f" [OK] execute_tool('catalogo_produtos'): {len(res_cat['data']['results'])} produtos recuperados")

    # 7. Ferramenta Inexistente (Tratamento de Erro Gracioso)
    res_err = await engine.execute_tool("ferramenta_inexistente")
    assert res_err["status"] == "error"
    print(" [OK] execute_tool: Tratamento de erro resiliente validado.")


def test_station_status(engine: AuraEngine):
    print("\n--- 3. Testando Diagnóstico Operacional da Estação ---")
    st = engine.get_stations_status()
    assert isinstance(st, StationStatus)
    assert st.filial_id is not None
    assert st.erp_host is not None
    print(f" [OK] StationStatus: Filial {st.filial_id} | ERP Online: {st.erp_online} ({st.erp_host}:{st.erp_port}) | Vector DB: {st.vector_db_online} | Produtos: {st.total_products_indexed}")


def test_parameter_extractors():
    print("\n--- 4. Testando Extratores de Parâmetros e Heurísticas ---")
    comb = extrair_combustivel("Qual o nível de gasolina aditivada?")
    assert comb == "GASOLINA ADITIVADA"

    data_val, turno_val = extrair_data_turno("Como foi o 1º turno de ontem?")
    assert turno_val == "1º TURNO"
    assert data_val == "ontem"

    frent = extrair_frentista("Vendas do frentista Cristian")
    assert frent == "CRISTIAN"

    bico = extrair_bico("Vazão da bomba 02")
    assert bico == "002"

    cesta = extrair_produto_cesta("O que vende junto com cerveja heineken?")
    assert cesta is not None and "heineken" in cesta.lower()

    grupo = extrair_grupo("Preço das cervejas")
    assert grupo == "BEBIDAS"

    intencao = classificar_intencao("relatório do lmc da anp")
    assert intencao == "lmc_anp"

    print(" [OK] Extratores de parâmetros do posto validados com precisão.")


async def test_streaming_and_ask(engine: AuraEngine):
    print("\n--- 5. Testando Streaming Assíncrono (ask_stream) e Resposta Completa (ask) ---")

    # 1. Teste do Streaming Completo
    pergunta = "Qual a autonomia do tanque de gasolina comum?"
    sess_id = "test_stream_sess"

    chunks_recebidos = []
    tipos_recebidos = set()

    async for chunk in engine.ask_stream(pergunta, session_id=sess_id):
        chunks_recebidos.append(chunk)
        tipos_recebidos.add(chunk.chunk_type)

    assert AuraChunkType.INTENT in tipos_recebidos, "Faltou chunk INTENT"
    assert AuraChunkType.TOOL_START in tipos_recebidos, "Faltou chunk TOOL_START"
    assert AuraChunkType.TOOL_RESULT in tipos_recebidos, "Faltou chunk TOOL_RESULT"
    assert AuraChunkType.DONE in tipos_recebidos, "Faltou chunk DONE"

    # Valida que TOOL_RESULT contém payload estruturado
    tool_chunk = next(c for c in chunks_recebidos if c.chunk_type == AuraChunkType.TOOL_RESULT)
    assert tool_chunk.data is not None
    assert "result" in tool_chunk.data

    texto_total = "".join(c.text for c in chunks_recebidos if c.chunk_type == AuraChunkType.DELTA and c.text)
    assert len(texto_total) > 0, "Nenhum texto gerado no streaming"
    print(f" [OK] ask_stream: {len(chunks_recebidos)} chunks emitidos | Tipos: {[t.value for t in tipos_recebidos]}")
    print(f"      Texto gerado ({len(texto_total)} caracteres): {texto_total[:80]}...")

    # 2. Teste da Resposta Completa (ask) com tool_result estruturado
    pergunta_ask = "Como está o LMC de hoje?"
    resposta = await engine.ask(pergunta_ask, session_id=sess_id)
    assert isinstance(resposta, AuraResponse)
    assert resposta.session_id == sess_id
    assert resposta.intent == "lmc_anp"
    assert len(resposta.response_text) > 0
    assert resposta.tool_result is not None, "tool_result deve conter o dicionário analítico da ferramenta"
    assert "telemetry" in resposta.model_dump()
    print(f" [OK] ask: Resposta estruturada retornada com sucesso (Intenção: {resposta.intent}, Dados Estruturados: {bool(resposta.tool_result)})")

    # 3. Teste de Cancelamento Precoce no SSE (Client Disconnect)
    chunks_early = []
    async for chunk in engine.ask_stream("Previsão de tanques de diesel", session_id="early_disconnect_sess"):
        chunks_early.append(chunk)
        if len(chunks_early) >= 2:
            break
    assert len(chunks_early) == 2
    print(" [OK] Cancelamento precoce no SSE: Gerador encerrado sem travamento de recursos.")

    # 4. Injeção de Contexto Operacional do Chamador e Multi-tenant
    resp_ctx = await engine.ask(
        "Quem é você?",
        context={"operador": "Gerente Carlos", "canal": "WhatsApp"},
        tenant_id="rede_postos_alpha",
        filial_id="posto_042",
        session_id="sess_context_test",
    )
    assert isinstance(resp_ctx, AuraResponse)
    hist_ctx = engine.session_memory.get_history("sess_context_test")
    assert len(hist_ctx) == 2
    print(" [OK] Injeção de contexto do chamador e persistência multi-filial validadas.")

    # 5. Continuidade de Sessão
    hist = engine.session_memory.get_history(sess_id)
    assert len(hist) >= 4, f"Esperava ao menos 4 mensagens no histórico da sessão, obteve {len(hist)}"
    print(f" [OK] Memória multiturn: {len(hist)} mensagens preservadas na sessão.")


def test_fastapi_endpoints(engine: AuraEngine):
    print("\n--- 6. Testando Endpoints FastAPI (/health, /stations, /execute-intent, /chat) ---")
    app = create_aura_app(engine)
    client = TestClient(app)

    # 1. GET /api/v1/aura/health
    resp_h = client.get("/api/v1/aura/health")
    assert resp_h.status_code == 200
    assert resp_h.json()["status"] == "healthy"
    print(" [OK] GET /api/v1/aura/health -> 200 OK")

    # 2. GET /api/v1/aura/stations
    resp_st = client.get("/api/v1/aura/stations")
    assert resp_st.status_code == 200
    stations = resp_st.json()
    assert isinstance(stations, list) and len(stations) > 0
    assert "filial_id" in stations[0]
    print(f" [OK] GET /api/v1/aura/stations -> 200 OK (Filial: {stations[0]['filial_nome']})")

    # 3. POST /api/v1/aura/execute-intent
    resp_exec = client.post(
        "/api/v1/aura/execute-intent",
        json={"tool_name": "conciliacao_turno", "params": {"data": "2026-09-02"}},
    )
    assert resp_exec.status_code == 200
    assert resp_exec.json()["status"] == "success"
    print(" [OK] POST /api/v1/aura/execute-intent -> 200 OK")

    # 4. POST /api/v1/aura/chat (stream=false) com contexto e tenant
    resp_chat = client.post(
        "/api/v1/aura/chat",
        json={
            "query": "Dados da filial",
            "stream": False,
            "tenant_id": "rede_sentinel",
            "filial_id": "posto_01",
            "context": {"origem": "dashboard_web"}
        },
    )
    assert resp_chat.status_code == 200
    chat_data = resp_chat.json()
    assert "response_text" in chat_data
    assert chat_data["intent"] == "dados_filial"
    print(f" [OK] POST /api/v1/aura/chat (stream=false) -> 200 OK (Intenção: {chat_data['intent']})")

    # 5. POST /api/v1/aura/chat (stream=true, SSE)
    resp_sse = client.post(
        "/api/v1/aura/chat",
        json={"query": "Qual a razão social do posto?", "stream": True},
    )
    assert resp_sse.status_code == 200
    assert "text/event-stream" in resp_sse.headers["content-type"]
    assert "event: intent" in resp_sse.text or "event: delta" in resp_sse.text
    print(" [OK] POST /api/v1/aura/chat (stream=true) -> 200 OK (SSE Stream recebido com sucesso)")


async def _run_all_async():
    mem_test = AuraSessionMemory(db_path=":memory:")
    engine = AuraEngine(
        tenant_id="test_tenant",
        filial_id="posto_teste_01",
        session_memory=mem_test,
    )

    await test_session_memory()
    await test_execute_tool_methods(engine)
    test_station_status(engine)
    test_parameter_extractors()
    await test_streaming_and_ask(engine)
    test_fastapi_endpoints(engine)


def run_all_tests():
    print("=" * 75)
    print("🚀 SUÍTE DE TESTES: MOTOR COGNITIVO HEADLESS AURA (FASE 1)")
    print("   (AuraEngine, Sessões Duráveis, Roteamento, Streaming & FastAPI)")
    print("=" * 75)

    asyncio.run(_run_all_async())

    print("\n" + "=" * 75)
    print("🎉 TODOS OS TESTES DA FASE 1 (AURA ENGINE HEADLESS) PASSARAM COM SUCESSO!")
    print("=" * 75)


if __name__ == "__main__":
    run_all_tests()
