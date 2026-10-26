"""
Testes Unitarios do AURA Partner API Gateway (Opcao A).

Valida:
1. Autenticacao de parceiro via Header (X-Partner-Key ou Authorization: Bearer) e X-Station-ID.
2. Ingestao de dados brutos (raw-sync) com armazenamento em staging isolado.
3. Mapeamento de tabelas brutas para entidades canonicas AUPS via YAMLDataMapperERPAdapter com generic_postgres.yaml.
4. Chat conversacional em modo texto puro com streaming SSE filtrado (apenas delta e done).
5. Isolamento estrito entre diferentes estacoes de postos.
6. Ausencia de travessoes (zero em-dash e en-dash).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from core.adapters.erp import YAMLDataMapperERPAdapter
from core.aura_api import create_aura_app
from core.aura_engine import (
    AuraChunk,
    AuraChunkType,
    AuraEngine,
    AuraResponse,
    AuraSessionMemory,
)
from core.domain.cashier import UniversalCashierShift
from core.domain.pumps import UniversalDispenserLog
from core.domain.sales import UniversalSaleReceipt
from core.domain.tanks import UniversalTankReading
from core.partner_api import (
    PartnerStagingStore,
    get_partner_erp_adapter,
    get_partner_staging_store,
    set_partner_staging_store,
    compute_station_roi_diagnostic,
    StationROIDiagnosticResponse,
    PartnerSemanticResponseCache,
    get_partner_semantic_cache,
    set_partner_semantic_cache,
)


PARTNER_TEST_KEY = "teste-parceiro-chave-secreta-2026"


@pytest.fixture
def isolated_staging_store(tmp_path: Path):
    """Cria instancia isolada de PartnerStagingStore em diretorio temporario."""
    store = PartnerStagingStore(staging_dir=tmp_path / "staging")
    set_partner_staging_store(store)
    yield store
    set_partner_staging_store(None)


@pytest.fixture
def mock_engine():
    """Motor AURA configurado para testes com memoria isolada."""
    mem = AuraSessionMemory(db_path=":memory:")
    return AuraEngine(session_memory=mem)


@pytest.fixture
def client(mock_engine, isolated_staging_store, monkeypatch):
    """TestClient configurado com chave de parceiro de teste e cache semantico limpo."""
    monkeypatch.setenv("AURA_PARTNER_API_KEY", PARTNER_TEST_KEY)
    cache = PartnerSemanticResponseCache()
    set_partner_semantic_cache(cache)
    app = create_aura_app(engine=mock_engine)
    yield TestClient(app)
    set_partner_semantic_cache(None)


# =============================================================================
# 1. TESTES DE AUTENTICACAO
# =============================================================================

@pytest.mark.unit
def test_partner_auth_missing_header(client):
    """Garante que requisicao sem cabecalho de chave de parceiro retorna 401."""
    resp = client.post("/api/v1/partner/stations/posto_01/raw-sync", json={"tanques": []})
    assert resp.status_code == 401
    assert "Autenticacao de parceiro necessaria" in resp.json()["detail"]


@pytest.mark.unit
def test_partner_auth_invalid_key(client):
    """Garante que chave incorreta retorna 401."""
    resp = client.post(
        "/api/v1/partner/stations/posto_01/raw-sync",
        headers={"X-Partner-Key": "chave_totalmente_errada"},
        json={"tanques": []},
    )
    assert resp.status_code == 401
    assert "Autenticacao de parceiro invalida" in resp.json()["detail"]


@pytest.mark.unit
def test_partner_auth_valid_x_partner_key(client):
    """Garante autenticacao bem sucedida via header X-Partner-Key."""
    resp = client.get(
        "/api/v1/partner/stations/posto_01/status",
        headers={"X-Partner-Key": PARTNER_TEST_KEY},
    )
    assert resp.status_code == 200
    assert resp.json()["station_id"] == "posto_01"


@pytest.mark.unit
def test_partner_auth_valid_bearer_token(client):
    """Garante autenticacao bem sucedida via Authorization: Bearer <key>."""
    resp = client.get(
        "/api/v1/partner/stations/posto_01/status",
        headers={"Authorization": f"Bearer {PARTNER_TEST_KEY}"},
    )
    assert resp.status_code == 200
    assert resp.json()["station_id"] == "posto_01"


@pytest.mark.unit
def test_partner_auth_station_conflict(client):
    """Garante que conflito entre X-Station-ID e station_id da rota retorna 400."""
    resp = client.post(
        "/api/v1/partner/stations/posto_01/raw-sync",
        headers={
            "X-Partner-Key": PARTNER_TEST_KEY,
            "X-Station-ID": "posto_02",
        },
        json={"tanques": []},
    )
    assert resp.status_code == 400
    assert "Conflito de estacao" in resp.json()["detail"]


@pytest.mark.unit
def test_partner_auth_station_match(client):
    """Garante sucesso quando X-Station-ID e station_id da rota coincidem."""
    resp = client.get(
        "/api/v1/partner/stations/posto_01/status",
        headers={
            "X-Partner-Key": PARTNER_TEST_KEY,
            "X-Station-ID": "posto_01",
        },
    )
    assert resp.status_code == 200


# =============================================================================
# 2. TESTES DE INGESTAO RAW-SYNC
# =============================================================================

@pytest.fixture
def sample_webposto_payload() -> dict[str, Any]:
    """Payload de exemplo de tabelas cruas do WebPosto."""
    return {
        "tanques": [
            {
                "codtan": "1",
                "prl_ds_produto_lmc": "Gasolina Comum",
                "codlmc": "1001",
                "ultima_leitura": "2026-10-25T10:00:00",
                "volume": 12500.0,
                "volume_agua": 0.0,
                "temperatura": 24.5,
                "capacidade": 15000.0,
                "iniciodia": 13000.0,
                "tan_vl_quantidade_fim": 12500.0,
            },
            {
                "codtan": "2",
                "prl_ds_produto_lmc": "Etanol Hidratado",
                "codlmc": "1002",
                "ultima_leitura": "2026-10-25T10:00:00",
                "volume": 8200.0,
                "volume_agua": 2.0,
                "temperatura": 25.0,
                "capacidade": 10000.0,
                "iniciodia": 9000.0,
                "tan_vl_quantidade_fim": 8200.0,
            },
        ],
        "fechabomba": [
            {
                "ilha": "1",
                "codbom": "1",
                "codtan": "1",
                "codpro": "GAS_COMUM",
                "turno": "1",
                "codpdv": "1",
                "dtmov": "2026-10-25T10:00:00",
                "encltsa": 1000.0,
                "enclts": 1500.0,
                "qtdeaf": 0.0,
                "preco": 5.89,
                "encdinh": 2945.0,
            }
        ],
        "fechacaixa": [
            {
                "cai_cd_caixa": "1",
                "codpdv": "1",
                "fechado": "S",
                "matricula": "OPERADOR_101",
                "turno": "1",
                "dtmov": "2026-10-25T10:00:00",
                "cai_ts_abertura": "2026-10-25T06:00:00",
            }
        ],
        "pedido": [
            {
                "codi": "PED1001",
                "pdv": "1",
                "dtem": "2026-10-25T09:30:00",
                "valortotal": 150.0,
                "situ": "A",
                "vendedor": "OPERADOR_101",
                "ven_tx_motivo_cancelamento": None,
                "formapg": "1",
            }
        ],
        "itemped": [
            {
                "controle": "1",
                "pedido": "PED1001",
                "codpec": "GAS_COMUM",
                "valunit": 5.0,
                "quant": 30.0,
                "valitem": 150.0,
            }
        ],
    }


@pytest.mark.unit
def test_raw_sync_nested_tables(client, sample_webposto_payload):
    """Garante ingestao com formato nested {'tables': {...}}."""
    body = {"station_id": "posto_01", "tables": sample_webposto_payload}
    resp = client.post(
        "/api/v1/partner/stations/posto_01/raw-sync",
        headers={"X-Partner-Key": PARTNER_TEST_KEY},
        json=body,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["station_id"] == "posto_01"
    assert "tanques" in data["tables_stored"]
    assert data["record_counts"]["tanques"] == 2
    assert data["record_counts"]["fechabomba"] == 1


@pytest.mark.unit
def test_raw_sync_flat_tables(client, sample_webposto_payload):
    """Garante ingestao com tabelas diretamente no corpo raiz do JSON."""
    resp = client.post(
        "/api/v1/partner/stations/posto_01/raw-sync",
        headers={"X-Partner-Key": PARTNER_TEST_KEY},
        json=sample_webposto_payload,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["record_counts"]["tanques"] == 2


@pytest.mark.unit
def test_raw_sync_empty_tables_rejected(client):
    """Garante que envio sem nenhuma tabela valida retorna erro 422."""
    resp = client.post(
        "/api/v1/partner/stations/posto_01/raw-sync",
        headers={"X-Partner-Key": PARTNER_TEST_KEY},
        json={"tables": {}},
    )
    assert resp.status_code == 422


@pytest.mark.unit
def test_raw_sync_invalid_station_id(client):
    """Garante bloqueio de station_id malicioso ou com tentativa de path traversal."""
    resp = client.post(
        "/api/v1/partner/stations/..%2F..%2Fhack/raw-sync",
        headers={"X-Partner-Key": PARTNER_TEST_KEY},
        json={"tanques": []},
    )
    assert resp.status_code in (400, 404)


@pytest.mark.unit
def test_staging_disk_persistence_and_reload(isolated_staging_store, sample_webposto_payload):
    """Valida que os dados sao gravados em disco e recarregados apos esvaziamento de cache."""
    isolated_staging_store.save_raw_data("posto_alpha", sample_webposto_payload)

    # Invalida o cache em memoria simulando restart do servico
    isolated_staging_store._cache.clear()

    # Leitura deve recuperar do arquivo JSON persistido em disco
    tanks = isolated_staging_store.get_table_rows("posto_alpha", "tanques")
    assert len(tanks) == 2
    assert tanks[0]["codtan"] == "1"


# =============================================================================
# 3. TESTES DE MAPEAMENTO AUPS VIA YAMLDataMapper COM generic_postgres.yaml
# =============================================================================

@pytest.mark.unit
def test_aups_mapping_tanks(isolated_staging_store, sample_webposto_payload):
    """Valida mapeamento de tanques crus para UniversalTankReading."""
    isolated_staging_store.save_raw_data("posto_01", sample_webposto_payload)

    adapter = get_partner_erp_adapter("posto_01", staging_store=isolated_staging_store)
    tanks = adapter.get_tank_inventory()

    assert len(tanks) == 2
    tanks_by_id = {t.identificador_tanque: t for t in tanks}
    assert "1" in tanks_by_id
    assert "2" in tanks_by_id
    t1 = tanks_by_id["1"]
    assert isinstance(t1, UniversalTankReading)
    assert t1.identificador_tanque == "1"
    assert t1.combustivel == "Gasolina Comum"
    assert t1.volume_atual_litros == 12500.0
    assert t1.capacidade_nominal_litros == 15000.0
    assert t1.percentual_capacidade > 80.0


@pytest.mark.unit
def test_aups_mapping_pumps(isolated_staging_store, sample_webposto_payload):
    """Valida mapeamento de fechabomba cru para UniversalDispenserLog."""
    isolated_staging_store.save_raw_data("posto_01", sample_webposto_payload)

    adapter = get_partner_erp_adapter("posto_01", staging_store=isolated_staging_store)
    pumps = adapter.get_pump_dispenses()

    assert len(pumps) == 1
    p1 = pumps[0]
    assert isinstance(p1, UniversalDispenserLog)
    assert p1.identificador_bico == "1"
    assert p1.identificador_tanque == "1"
    assert p1.delta_leitura == 500.0


@pytest.mark.unit
def test_aups_mapping_cashier(isolated_staging_store, sample_webposto_payload):
    """Valida mapeamento de fechacaixa cru para UniversalCashierShift."""
    isolated_staging_store.save_raw_data("posto_01", sample_webposto_payload)

    adapter = get_partner_erp_adapter("posto_01", staging_store=isolated_staging_store)
    shifts = adapter.get_cashier_shifts()

    assert len(shifts) == 1
    s1 = shifts[0]
    assert isinstance(s1, UniversalCashierShift)
    assert s1.caixa_id == "1"
    assert s1.operador_id == "OPERADOR_101"
    assert s1.fechado is True


@pytest.mark.unit
def test_aups_mapping_sales_and_items(isolated_staging_store, sample_webposto_payload):
    """Valida mapeamento de pedido e itemped crus para UniversalSaleReceipt."""
    isolated_staging_store.save_raw_data("posto_01", sample_webposto_payload)

    adapter = get_partner_erp_adapter("posto_01", staging_store=isolated_staging_store)
    sales = adapter.get_recent_sales(limit=10)

    assert len(sales) == 1
    sale = sales[0]
    assert isinstance(sale, UniversalSaleReceipt)
    assert sale.cupom_id == "PED1001"
    assert sale.total_reais == 150.0
    assert len(sale.itens) == 1
    assert sale.itens[0].sku == "GAS_COMUM"
    assert sale.itens[0].quantidade == 30.0


@pytest.mark.unit
def test_partner_get_tanks_api_endpoint(client, sample_webposto_payload):
    """Valida endpoint GET /api/v1/partner/stations/{station_id}/tanks."""
    client.post(
        "/api/v1/partner/stations/posto_01/raw-sync",
        headers={"X-Partner-Key": PARTNER_TEST_KEY},
        json=sample_webposto_payload,
    )
    resp = client.get(
        "/api/v1/partner/stations/posto_01/tanks",
        headers={"X-Partner-Key": PARTNER_TEST_KEY},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2
    tank_ids = {t["identificador_tanque"] for t in data["tanks"]}
    assert "1" in tank_ids
    assert "2" in tank_ids


# =============================================================================
# 4. TESTES DE CHAT CONVERSACIONAL FILTRADO (SSE E PURE TEXT)
# =============================================================================

@pytest.mark.unit
def test_partner_chat_streaming_sse_filtered(client, mock_engine, monkeypatch):
    """
    Garante que o streaming SSE de parceiros:
    1. Descarta chunks internos (intent, tool_start, tool_result, telemetry).
    2. Transmite exclusivamente chunks dos tipos delta e done.
    3. Desativa GenUI (sem cartoes ou vouchers).
    """
    async def mock_ask_stream(query, **kwargs):
        # Garante que GenUI esta estritamente desativado
        assert kwargs.get("enable_genui") is False

        # Emite chunks internos de calculo
        yield AuraChunk(chunk_type=AuraChunkType.INTENT, text="run_out")
        yield AuraChunk(chunk_type=AuraChunkType.TOOL_START, text="Iniciando calculo")
        yield AuraChunk(chunk_type=AuraChunkType.TOOL_RESULT, data={"dias": 3.5})

        # Emite tokens textuais
        yield AuraChunk(chunk_type=AuraChunkType.DELTA, text="O tanque 1 ")
        yield AuraChunk(chunk_type=AuraChunkType.DELTA, text="possui autonomia de 3 dias.")

        # Emite telemetria interna
        yield AuraChunk(chunk_type=AuraChunkType.TELEMETRY, data={"latency_ms": 12.0})

        # Emite chunk de finalizacao
        yield AuraChunk(chunk_type=AuraChunkType.DONE, text="")

    monkeypatch.setattr(mock_engine, "ask_stream", mock_ask_stream)

    resp = client.post(
        "/api/v1/partner/chat",
        headers={
            "X-Partner-Key": PARTNER_TEST_KEY,
            "X-Station-ID": "posto_01",
        },
        json={
            "query": "Como esta a autonomia dos tanques?",
            "stream": True,
        },
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    assert resp.headers.get("X-GenUI-Enabled") == "0"

    sse_text = resp.text
    # Garante que chunks internos foram descartados
    assert "event: intent" not in sse_text
    assert "event: tool_start" not in sse_text
    assert "event: tool_result" not in sse_text
    assert "event: telemetry" not in sse_text
    assert "event: ui_skeleton" not in sse_text
    assert "event: ui_complete" not in sse_text

    # Garante que apenas delta e done foram transmitidos
    assert "event: delta" in sse_text
    assert "event: done" in sse_text
    assert "O tanque 1" in sse_text
    assert "possui autonomia de 3 dias" in sse_text


@pytest.mark.unit
def test_partner_chat_sync_pure_text(client, mock_engine, monkeypatch):
    """Garante resposta síncrona JSON limpa quando stream=False."""
    async def mock_ask(query, **kwargs):
        assert kwargs.get("enable_genui") is False
        return AuraResponse(
            session_id="sess_partner_123",
            query=query,
            response_text="Estoque de combustivel estavel em 12.500 litros.",
            intent="tanques",
            confidence=0.98,
            routing_method="heuristica",
        )

    monkeypatch.setattr(mock_engine, "ask", mock_ask)

    resp = client.post(
        "/api/v1/partner/chat",
        headers={
            "X-Partner-Key": PARTNER_TEST_KEY,
            "X-Station-ID": "posto_01",
        },
        json={
            "query": "Resumo dos tanques",
            "stream": False,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "sess_partner_123"
    assert data["response_text"] == "Estoque de combustivel estavel em 12.500 litros."
    assert "envelope" not in data
    assert "action_voucher" not in data


# =============================================================================
# 5. TESTES DE ISOLAMENTO DE STAGING ENTRE ESTACOES
# =============================================================================

@pytest.mark.unit
def test_station_staging_isolation(client, isolated_staging_store):
    """Garante que os dados da estacao A nao vazam para a estacao B."""
    payload_a = {
        "tanques": [{"codtan": "A1", "prl_ds_produto_lmc": "Diesel S10", "volume": 5000.0, "capacidade": 10000.0}]
    }
    payload_b = {
        "tanques": [{"codtan": "B1", "prl_ds_produto_lmc": "Gasolina Podium", "volume": 2000.0, "capacidade": 5000.0}]
    }

    client.post(
        "/api/v1/partner/stations/posto_A/raw-sync",
        headers={"X-Partner-Key": PARTNER_TEST_KEY},
        json=payload_a,
    )
    client.post(
        "/api/v1/partner/stations/posto_B/raw-sync",
        headers={"X-Partner-Key": PARTNER_TEST_KEY},
        json=payload_b,
    )

    resp_a = client.get(
        "/api/v1/partner/stations/posto_A/tanks",
        headers={"X-Partner-Key": PARTNER_TEST_KEY},
    )
    resp_b = client.get(
        "/api/v1/partner/stations/posto_B/tanks",
        headers={"X-Partner-Key": PARTNER_TEST_KEY},
    )

    tanks_a = resp_a.json()["tanks"]
    tanks_b = resp_b.json()["tanks"]

    assert len(tanks_a) == 1
    assert tanks_a[0]["identificador_tanque"] == "A1"
    assert tanks_a[0]["combustivel"] == "Diesel S10"

    assert len(tanks_b) == 1
    assert tanks_b[0]["identificador_tanque"] == "B1"
    assert tanks_b[0]["combustivel"] == "Gasolina Podium"

    # Limpeza de posto_A nao deve afetar posto_B
    isolated_staging_store.clear_station("posto_A")
    assert isolated_staging_store.get_table_rows("posto_A", "tanques") == []
    assert len(isolated_staging_store.get_table_rows("posto_B", "tanques")) == 1


@pytest.mark.unit
def test_aura_core_routes_unaffected(client):
    """Garante que as rotas padrao da AURA continuam intactas."""
    resp = client.get("/api/v1/aura/health")
    assert resp.status_code == 200
    assert resp.json().get("status") == "healthy"


@pytest.mark.unit
def test_partner_chat_empty_query_rejected(client):
    """Garante rejeicao com 422 quando a query do chat esta vazia."""
    resp = client.post(
        "/api/v1/partner/chat",
        headers={"X-Partner-Key": PARTNER_TEST_KEY},
        json={"query": ""},
    )
    assert resp.status_code == 422


@pytest.mark.unit
def test_raw_sync_station_id_length_limit(client):
    """Garante que station_id com mais de 64 caracteres eh rejeitado com 400."""
    long_id = "posto_" + "x" * 60
    resp = client.post(
        f"/api/v1/partner/stations/{long_id}/raw-sync",
        headers={"X-Partner-Key": PARTNER_TEST_KEY},
        json={"tanques": []},
    )
    assert resp.status_code == 400
    assert "excessivamente longo" in resp.json()["detail"]


@pytest.mark.unit
def test_raw_sync_partial_tables_graceful_empty(client):
    """Garante que consultar tabelas nao enviadas no sync retorna lista vazia sem erro."""
    client.post(
        "/api/v1/partner/stations/posto_parcial/raw-sync",
        headers={"X-Partner-Key": PARTNER_TEST_KEY},
        json={"tanques": [{"codtan": "1", "volume": 1000.0, "capacidade": 5000.0}]},
    )
    resp = client.get(
        "/api/v1/partner/stations/posto_parcial/sales",
        headers={"X-Partner-Key": PARTNER_TEST_KEY},
    )
    assert resp.status_code == 200
    assert resp.json()["count"] == 0
    assert resp.json()["sales"] == []


@pytest.mark.unit
def test_partner_chat_streaming_error_handling(client, mock_engine, monkeypatch):
    """Garante que excecao no ask_stream emite chunk de erro gracioso sem quebrar o stream SSE."""
    async def failing_ask_stream(query, **kwargs):
        raise RuntimeError("Falha critica simulada de conexao LLM")
        yield AuraChunk(chunk_type=AuraChunkType.DELTA, text="")

    monkeypatch.setattr(mock_engine, "ask_stream", failing_ask_stream)

    resp = client.post(
        "/api/v1/partner/chat",
        headers={"X-Partner-Key": PARTNER_TEST_KEY},
        json={"query": "Pergunta com falha", "stream": True},
    )
    assert resp.status_code == 200
    assert "event: delta" in resp.text
    assert "Erro interno no processamento" in resp.text
    assert "event: done" in resp.text


@pytest.mark.unit
def test_partner_health_endpoint(client):
    """Garante que endpoint /api/v1/partner/health responde 200 com status online."""
    resp = client.get("/api/v1/partner/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "online"
    assert "AURA Partner Gateway" in data["service"]


@pytest.mark.unit
def test_partner_erp_adapter_check_health_record_counts(isolated_staging_store, sample_webposto_payload):
    """Garante que check_health calcula COUNT(*) real de registros no staging."""
    isolated_staging_store.save_raw_data("posto_01", sample_webposto_payload)
    adapter = get_partner_erp_adapter("posto_01", staging_store=isolated_staging_store)
    h = adapter.check_health()

    assert h["status"] == "healthy"
    assert h["connected"] is True
    assert h["record_counts"]["tanks"] == 2
    assert h["record_counts"]["pumps"] == 1
    assert h["record_counts"]["cashier"] == 1
    assert h["record_counts"]["sales"] == 1
    assert h["record_counts"]["sales_items"] == 1


@pytest.mark.unit
def test_partner_erp_adapter_date_filtering(isolated_staging_store):
    """Garante filtragem por start_date e end_date em consultas de vendas."""
    payload = {
        "pedido": [
            {"codi": "PED1", "valortotal": 50.0, "situ": "A", "dtem": "2026-10-20T10:00:00"},
            {"codi": "PED2", "valortotal": 60.0, "situ": "A", "dtem": "2026-10-22T10:00:00"},
            {"codi": "PED3", "valortotal": 70.0, "situ": "A", "dtem": "2026-10-25T10:00:00"},
            {"codi": "PED4", "valortotal": 80.0, "situ": "A", "dtem": "2026-10-25T12:00:00"},
        ]
    }
    isolated_staging_store.save_raw_data("posto_datas", payload)
    adapter = get_partner_erp_adapter("posto_datas", staging_store=isolated_staging_store)

    # Vendas a partir de 24/10
    after = adapter.get_recent_sales(start_date="2026-10-24T00:00:00")
    assert [s.cupom_id for s in after] == ["PED4", "PED3"]

    # Vendas ate 21/10
    before = adapter.get_recent_sales(end_date="2026-10-21T00:00:00")
    assert [s.cupom_id for s in before] == ["PED1"]


@pytest.mark.unit
def test_partner_erp_adapter_order_by_and_limit(isolated_staging_store):
    """Garante que ORDER BY dtem DESC e LIMIT retornam as vendas mais recentes primeiro."""
    payload = {
        "pedido": [
            {"codi": "PED_ANTIGO", "valortotal": 50.0, "situ": "A", "dtem": "2026-10-20T10:00:00"},
            {"codi": "PED_RECENTE_1", "valortotal": 70.0, "situ": "A", "dtem": "2026-10-25T10:00:00"},
            {"codi": "PED_RECENTE_2", "valortotal": 80.0, "situ": "A", "dtem": "2026-10-25T14:00:00"},
        ]
    }
    isolated_staging_store.save_raw_data("posto_ordenacao", payload)
    adapter = get_partner_erp_adapter("posto_ordenacao", staging_store=isolated_staging_store)

    top2 = adapter.get_recent_sales(limit=2)
    assert len(top2) == 2
    assert [s.cupom_id for s in top2] == ["PED_RECENTE_2", "PED_RECENTE_1"]


@pytest.mark.unit
def test_partner_raw_sync_brazilian_number_formats(client, isolated_staging_store):
    """Garante que formatos numericos brasileiros legados (milhar ponto e decimal virgula) sao sanitizados."""
    payload_br = {
        "tanques": [
            {
                "codtan": "T_BR",
                "prl_ds_produto_lmc": "Gasolina Aditivada",
                "volume": "14.250,75",
                "capacidade": "20.000,00",
            }
        ],
        "pedido": [
            {
                "codi": "PED_BR",
                "valortotal": "1.345,60",
                "dtem": "2026-10-25T10:00:00",
                "situ": "A",
            }
        ],
        "itemped": [
            {
                "controle": "1",
                "pedido": "PED_BR",
                "codpec": "GAS_ADIT",
                "valunit": "6,19",
                "quant": "217,38",
                "valitem": "1.345,60",
            }
        ],
    }

    resp = client.post(
        "/api/v1/partner/stations/posto_br/raw-sync",
        headers={"X-Partner-Key": PARTNER_TEST_KEY},
        json=payload_br,
    )
    assert resp.status_code == 200

    adapter = get_partner_erp_adapter("posto_br", staging_store=isolated_staging_store)
    tanks = adapter.get_tank_inventory()
    assert len(tanks) == 1
    assert tanks[0].volume_atual_litros == 14250.75
    assert tanks[0].capacidade_nominal_litros == 20000.0

    sales = adapter.get_recent_sales()
    assert len(sales) == 1
    assert sales[0].total_reais == 1345.60
    assert sales[0].itens[0].preco_unitario_reais == 6.19
    assert sales[0].itens[0].total_item_reais == 1345.60


@pytest.mark.unit
def test_partner_chat_station_conflict_between_header_and_body(client):
    """Garante 400 quando X-Station-ID difere do station_id informado no corpo do chat."""
    resp = client.post(
        "/api/v1/partner/chat",
        headers={
            "X-Partner-Key": PARTNER_TEST_KEY,
            "X-Station-ID": "posto_01",
        },
        json={
            "query": "Como esta o estoque?",
            "station_id": "posto_02",
        },
    )
    assert resp.status_code == 400
    assert "Conflito de estacao" in resp.json()["detail"]



# =============================================================================
# 7. TESTES DO MODULO 1: CALCULADORA EXECUTIVA E DIAGNOSTICO RETROATIVO DE ROI
# =============================================================================

@pytest.mark.unit
def test_roi_diagnostic_requires_authentication(client):
    """Garante 401 ao requisitar /roi-diagnostic sem autenticacao valida."""
    # Sem header de chave
    resp = client.get("/api/v1/partner/stations/posto_01/roi-diagnostic")
    assert resp.status_code == 401
    assert "Autenticacao de parceiro necessaria" in resp.json()["detail"]

    # Com chave incorreta
    resp_invalid = client.get(
        "/api/v1/partner/stations/posto_01/roi-diagnostic",
        headers={"X-Partner-Key": "chave-invalida-123"},
    )
    assert resp_invalid.status_code == 401
    assert "Autenticacao de parceiro invalida" in resp_invalid.json()["detail"]


@pytest.mark.unit
def test_roi_diagnostic_baseline_when_no_data_in_staging(client, isolated_staging_store):
    """Valida diagnostico com valores auditados de baseline quando nao ha dados no staging."""
    resp = client.get(
        "/api/v1/partner/stations/posto_novo/roi-diagnostic",
        headers={"X-Partner-Key": PARTNER_TEST_KEY},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["station_id"] == "posto_novo"
    assert data["data_version_hash"] == "0000000000000000"
    assert "generated_at" in data

    # Quebra de perdas mensais (baseline auditado)
    breakdown = data["breakdown_brl"]
    assert breakdown["lmc_and_tank_shrinkage"] == 4520.00
    assert breakdown["convenience_and_pos_cancellations"] == 3100.00
    assert breakdown["cashier_shift_discrepancies"] == 1850.00
    assert breakdown["pricing_and_carreta_arbitrage"] == 6200.00
    assert breakdown["working_capital_selic_cost"] == 1400.00

    # Consolidacao executiva
    summary = data["summary"]
    assert summary["total_monthly_leakage_brl"] == 17070.00
    assert summary["estimated_monthly_recovery_brl"] == 13206.00
    assert summary["roi_90_days_net_brl"] == 28903.80
    assert summary["roi_multiple"] == 20.7
    assert summary["guarantee_3x_met"] is True

    # Blindagem regulatoria
    shield = data["regulatory_shield"]
    assert shield["anp_law_9847_min_fine_brl"] == 20000.00
    assert shield["anp_lmc_tolerance_pct"] == 0.60
    assert shield["clt_art_462_compliance_active"] is True


@pytest.mark.unit
def test_roi_diagnostic_custom_monthly_fee(client, isolated_staging_store):
    """Valida calculo de ROI liquido em 90 dias com mensalidade customizada."""
    resp = client.get(
        "/api/v1/partner/stations/posto_custom_fee/roi-diagnostic?monthly_fee=1200.0",
        headers={"X-Partner-Key": PARTNER_TEST_KEY},
    )
    assert resp.status_code == 200
    summary = resp.json()["summary"]

    # Custo de 3 mensalidades = 3 * 1200 = 3600.00
    # Recuperacao em 90 dias com adocao (2.3) = 13206.00 * 2.3 = 30373.80
    # Retorno liquido = 30373.80 - 3600.00 = 26773.80
    assert summary["roi_90_days_net_brl"] == 26773.80
    assert summary["roi_multiple"] == 8.4
    assert summary["guarantee_3x_met"] is True


@pytest.mark.unit
def test_roi_diagnostic_with_populated_staging_data(client, isolated_staging_store):
    """Valida diagnostico deterministico com dados reais sincronizados no staging."""
    station = "posto_auditado"
    payload = {
        "fechabomba": [
            {
                "enclts": "12000.00",
                "encltsa": "8000.00",
                "qtdeaf": "0.00",
                "preco": "5.90",
                "encdinh": "18000.00",
            }
        ],
        "tanques": [
            {
                "tanque": "1",
                "iniciodia": "15000.00",
                "volume": "10500.00",
            }
        ],
        "fechacaixa": [
            {
                "fechamento": "1",
                "valtot": "17800.00",
                "valrefcai": "0.00",
            }
        ],
        "pedido": [
            {
                "pedido": "P101",
                "situ": "C",
                "total": "150.00",
            }
        ],
    }

    sync_resp = client.post(
        f"/api/v1/partner/stations/{station}/raw-sync",
        headers={"X-Partner-Key": PARTNER_TEST_KEY},
        json=payload,
    )
    assert sync_resp.status_code == 200
    sync_hash = sync_resp.json().get("data_version_hash")
    assert sync_hash is not None
    assert len(sync_hash) == 16

    diag_resp = client.get(
        f"/api/v1/partner/stations/{station}/roi-diagnostic",
        headers={"X-Partner-Key": PARTNER_TEST_KEY},
    )
    assert diag_resp.status_code == 200
    diag = diag_resp.json()

    assert diag["station_id"] == station
    assert diag["data_version_hash"] == sync_hash

    b = diag["breakdown_brl"]
    assert b["lmc_and_tank_shrinkage"] == 88500.00
    assert b["convenience_and_pos_cancellations"] == 4500.00
    assert b["cashier_shift_discrepancies"] == 6000.00
    assert b["pricing_and_carreta_arbitrage"] == 4200.00
    assert b["working_capital_selic_cost"] == 526.58

    s = diag["summary"]
    assert s["total_monthly_leakage_brl"] == 103726.58
    assert s["estimated_monthly_recovery_brl"] == 81488.29
    assert s["roi_90_days_net_brl"] == 185953.07
    assert s["roi_multiple"] == 127.5
    assert s["guarantee_3x_met"] is True


@pytest.mark.unit
def test_roi_diagnostic_header_station_mismatch(client):
    """Garante 400 quando X-Station-ID difere da URL do diagnostico."""
    resp = client.get(
        "/api/v1/partner/stations/posto_01/roi-diagnostic",
        headers={
            "X-Partner-Key": PARTNER_TEST_KEY,
            "X-Station-ID": "posto_99",
        },
    )
    assert resp.status_code == 400
    assert "Conflito de estacao" in resp.json()["detail"]


@pytest.mark.unit
def test_compute_station_roi_diagnostic_direct_function(isolated_staging_store):
    """Valida chamada direta da funcao compute_station_roi_diagnostic sem HTTP."""
    res = compute_station_roi_diagnostic(
        "posto_unit_direct",
        staging_store=isolated_staging_store,
        monthly_subscription_brl=490.0,
    )
    assert res["station_id"] == "posto_unit_direct"
    assert res["data_version_hash"] == "0000000000000000"
    assert res["summary"]["guarantee_3x_met"] is True
    assert res["summary"]["roi_multiple"] >= 3.0



# =============================================================================
# 8. TESTES DO MODULO 2: CACHE SEMANTICO SINCRONIZADO AO DATA_VERSION_HASH
# =============================================================================

@pytest.mark.unit
def test_semantic_cache_query_normalization():
    """Valida normalizacao semantica de queries: acentos, espacos e pontuacao."""
    norm = PartnerSemanticResponseCache.normalize_query
    assert norm("Como estao os tanques agora?") == "como estao os tanques agora"
    assert norm("COMO ESTAO OS TANQUES AGORA???") == "como estao os tanques agora"
    assert norm("  Qual o   resumo de caixa!  ") == "qual o resumo de caixa"
    assert norm("Preco da Gasolina Comum R$ 5,80") == "preco da gasolina comum r 5 80"
    assert norm("") == ""
    assert norm("   ") == ""


@pytest.mark.unit
def test_semantic_cache_get_set_lru_and_invalidation():
    """Valida operacoes get/set com chave composta, politica LRU e invalidacao por estacao."""
    cache = PartnerSemanticResponseCache(max_entries_per_station=2)
    station = "posto_teste_cache"
    hash_v1 = "1111222233334444"
    hash_v2 = "5555666677778888"

    # Set entrada 1
    cache.set(station, hash_v1, "Como estao os tanques?", {"response_text": "Tanques estaveis"})
    # Get com variacao de pontuacao/caixa alta -> Cache Hit
    hit = cache.get(station, hash_v1, "como estao os tanques")
    assert hit is not None
    assert hit["response_text"] == "Tanques estaveis"

    # Get com data_version_hash diferente -> Cache Miss
    miss_hash = cache.get(station, hash_v2, "como estao os tanques")
    assert miss_hash is None

    # Get com query diferente -> Cache Miss
    miss_query = cache.get(station, hash_v1, "qual o faturamento")
    assert miss_query is None

    # Adiciona mais 2 entradas para testar LRU (limite = 2)
    cache.set(station, hash_v1, "Pergunta B", {"response_text": "B"})
    cache.set(station, hash_v1, "Pergunta C", {"response_text": "C"})

    # Primeira entrada ("Como estao os tanques?") foi evictada pelo LRU
    assert cache.get(station, hash_v1, "Como estao os tanques?") is None
    assert cache.get(station, hash_v1, "Pergunta B") is not None
    assert cache.get(station, hash_v1, "Pergunta C") is not None

    # Invalidacao da estacao
    cache.invalidate_station(station)
    assert cache.get(station, hash_v1, "Pergunta B") is None
    assert cache.get(station, hash_v1, "Pergunta C") is None


@pytest.mark.unit
def test_partner_chat_semantic_cache_miss_then_hit_non_stream(client, mock_engine, monkeypatch):
    """Garante economia de tokens: primeira chamada gera Cache Miss, segunda chamada gera Cache Hit com custo zero de LLM."""
    call_counter = {"count": 0}

    async def mock_ask(query, **kwargs):
        call_counter["count"] += 1
        return AuraResponse(
            session_id="sess_cache_test",
            query=query,
            response_text=f"Resposta gerada pelo motor LLM (chamada {call_counter['count']})",
            intent="tanques",
            confidence=0.97,
            routing_method="deep_research",
        )

    monkeypatch.setattr(mock_engine, "ask", mock_ask)

    # 1. Primeira requisicao: Cache Miss
    resp1 = client.post(
        "/api/v1/partner/chat",
        headers={
            "X-Partner-Key": PARTNER_TEST_KEY,
            "X-Station-ID": "posto_cache_01",
        },
        json={
            "query": "Como estao os estoques dos tanques?",
            "stream": False,
        },
    )
    assert resp1.status_code == 200
    assert resp1.headers.get("X-Aura-Cache") == "MISS"
    data1 = resp1.json()
    assert data1["cache_hit"] is False
    assert "chamada 1" in data1["response_text"]
    assert call_counter["count"] == 1

    # 2. Segunda requisicao (mesma query com variacao de pontuacao): Cache Hit
    resp2 = client.post(
        "/api/v1/partner/chat",
        headers={
            "X-Partner-Key": PARTNER_TEST_KEY,
            "X-Station-ID": "posto_cache_01",
        },
        json={
            "query": "como estao os estoques dos tanques",
            "stream": False,
        },
    )
    assert resp2.status_code == 200
    assert resp2.headers.get("X-Aura-Cache") == "HIT"
    data2 = resp2.json()
    assert data2["cache_hit"] is True
    assert "chamada 1" in data2["response_text"]
    # Garante que o motor NAO foi invocado novamente
    assert call_counter["count"] == 1


@pytest.mark.unit
def test_partner_chat_semantic_cache_stream_hit(client, mock_engine, monkeypatch):
    """Valida que Cache Hit no modo stream=True emite SSE imediato com headers X-Aura-Cache: HIT."""
    async def mock_ask_stream(query, **kwargs):
        yield AuraChunk(chunk_type=AuraChunkType.DELTA, text="Chunk inicial.")
        yield AuraChunk(chunk_type=AuraChunkType.DONE, text="")

    monkeypatch.setattr(mock_engine, "ask_stream", mock_ask_stream)

    # 1. Primeira chamada stream: Miss (armazena no cache)
    resp1 = client.post(
        "/api/v1/partner/chat",
        headers={
            "X-Partner-Key": PARTNER_TEST_KEY,
            "X-Station-ID": "posto_stream_cache",
        },
        json={
            "query": "Status das bombas",
            "stream": True,
        },
    )
    assert resp1.status_code == 200
    assert resp1.headers.get("X-Aura-Cache") == "MISS"
    body1 = resp1.text
    assert "event: delta" in body1
    assert "Chunk inicial." in body1

    # 2. Segunda chamada stream: Hit
    resp2 = client.post(
        "/api/v1/partner/chat",
        headers={
            "X-Partner-Key": PARTNER_TEST_KEY,
            "X-Station-ID": "posto_stream_cache",
        },
        json={
            "query": "status das bombas",
            "stream": True,
        },
    )
    assert resp2.status_code == 200
    assert resp2.headers.get("X-Aura-Cache") == "HIT"
    body2 = resp2.text
    assert "event: delta" in body2
    assert "Chunk inicial." in body2
    assert "event: done" in body2


@pytest.mark.unit
def test_semantic_cache_invalidation_on_raw_sync(client, mock_engine, monkeypatch, isolated_staging_store):
    """Garante que novo raw-sync altera o data_version_hash e invalida automaticamente o cache semantico."""
    station = "posto_sync_inval"
    call_counter = {"count": 0}

    async def mock_ask(query, **kwargs):
        call_counter["count"] += 1
        return AuraResponse(
            session_id="sess_sync_test",
            query=query,
            response_text=f"Resposta sincronizada versao {call_counter['count']}",
            intent="fechamento",
            confidence=0.99,
            routing_method="direct",
        )

    monkeypatch.setattr(mock_engine, "ask", mock_ask)

    # 1. Ingestao inicial de dados
    sync1 = client.post(
        f"/api/v1/partner/stations/{station}/raw-sync",
        headers={"X-Partner-Key": PARTNER_TEST_KEY},
        json={"tanques": [{"tanque": "1", "volume": "5000"}]},
    )
    assert sync1.status_code == 200
    hash1 = sync1.json()["data_version_hash"]

    # 2. Primeira consulta: Cache Miss
    chat1 = client.post(
        "/api/v1/partner/chat",
        headers={"X-Partner-Key": PARTNER_TEST_KEY, "X-Station-ID": station},
        json={"query": "Resumo dos tanques", "stream": False},
    )
    assert chat1.status_code == 200
    assert chat1.headers.get("X-Aura-Cache") == "MISS"
    assert chat1.headers.get("X-Data-Version") == hash1
    assert call_counter["count"] == 1

    # 3. Segunda consulta: Cache Hit
    chat2 = client.post(
        "/api/v1/partner/chat",
        headers={"X-Partner-Key": PARTNER_TEST_KEY, "X-Station-ID": station},
        json={"query": "resumo dos tanques", "stream": False},
    )
    assert chat2.status_code == 200
    assert chat2.headers.get("X-Aura-Cache") == "HIT"
    assert chat2.headers.get("X-Data-Version") == hash1
    assert call_counter["count"] == 1

    # 4. Novo raw-sync com dados alterados (novo volume)
    sync2 = client.post(
        f"/api/v1/partner/stations/{station}/raw-sync",
        headers={"X-Partner-Key": PARTNER_TEST_KEY},
        json={"tanques": [{"tanque": "1", "volume": "8000"}]},
    )
    assert sync2.status_code == 200
    hash2 = sync2.json()["data_version_hash"]
    assert hash2 != hash1

    # 5. Terceira consulta com nova versao de dados: Cache Miss automatico!
    chat3 = client.post(
        "/api/v1/partner/chat",
        headers={"X-Partner-Key": PARTNER_TEST_KEY, "X-Station-ID": station},
        json={"query": "Resumo dos tanques", "stream": False},
    )
    assert chat3.status_code == 200
    assert chat3.headers.get("X-Aura-Cache") == "MISS"
    assert chat3.headers.get("X-Data-Version") == hash2
    assert call_counter["count"] == 2


@pytest.mark.unit
def test_station_status_contains_data_version_hash(client, isolated_staging_store):
    """Valida que o endpoint GET /stations/{station_id}/status informa data_version_hash."""
    resp_empty = client.get(
        "/api/v1/partner/stations/posto_teste_meta/status",
        headers={"X-Partner-Key": PARTNER_TEST_KEY},
    )
    assert resp_empty.status_code == 200
    assert "data_version_hash" in resp_empty.json() or resp_empty.json()["status"] == "empty"

    # Sincroniza dados e valida status ready com hash
    client.post(
        "/api/v1/partner/stations/posto_teste_meta/raw-sync",
        headers={"X-Partner-Key": PARTNER_TEST_KEY},
        json={"tanques": [{"tanque": "1", "volume": "1000"}]},
    )

    resp_ready = client.get(
        "/api/v1/partner/stations/posto_teste_meta/status",
        headers={"X-Partner-Key": PARTNER_TEST_KEY},
    )
    assert resp_ready.status_code == 200
    data = resp_ready.json()
    assert data["status"] == "ready"
    assert len(data.get("data_version_hash", "")) == 16

# =============================================================================
# 6. CONFORMIDADE: ZERO TRAVESSOES
# =============================================================================

@pytest.mark.unit
def test_zero_travessoes_in_all_partner_files():
    """Garante ausencia estrita de travessoes (U+2014 e U+2013) em todos os novos artefatos."""
    files_to_check = [
        Path("core") / "partner_api.py",
        Path("Dockerfile.partner"),
        Path("docker-compose.partner.yml"),
        Path("tests") / "unit" / "test_partner_api.py",
    ]
    for path in files_to_check:
        assert path.exists(), f"Arquivo nao encontrado: {path}"
        content = path.read_text(encoding="utf-8")
        assert "\u2014" not in content, f"Em-dash encontrado em {path}"
        assert "\u2013" not in content, f"En-dash encontrado em {path}"
