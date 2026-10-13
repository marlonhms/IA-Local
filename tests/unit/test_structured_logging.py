"""
Testes Unitarios: Logging Estruturado em Formato JSON Padronizado (P1-6).
Valida geracao de linhas JSON compativeis com ferramentas de observabilidade,
extracao de campos obrigatorios e propagacao do middleware X-Request-ID.
Zero travessoes em todo o arquivo.
"""

import json
import logging

import pytest
from fastapi.testclient import TestClient

from core.aura_api import create_aura_app
from core.aura_engine import AuraEngine, AuraSessionMemory
from core.logging_config import (
    StructuredJsonFormatter,
)


@pytest.mark.unit
def test_structured_json_formatter_fields():
    """Valida presenca dos campos padronizados no JSON emitido pelo formatador."""
    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="aura.test",
        level=logging.INFO,
        pathname="test_file.py",
        lineno=42,
        msg="Teste de mensagem estruturada de pista",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-12345678-abcd"
    record.client_ip = "192.168.1.100"
    record.elapsed_ms = 45.67

    formatted_str = formatter.format(record)
    parsed = json.loads(formatted_str)

    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "aura.test"
    assert parsed["message"] == "Teste de mensagem estruturada de pista"
    assert parsed["request_id"] == "req-12345678-abcd"
    assert parsed["client_ip"] == "192.168.1.100"
    assert parsed["elapsed_ms"] == 45.67
    assert "timestamp" in parsed


@pytest.mark.unit
def test_request_id_middleware_propagation():
    """Valida injecao e retorno do cabecalho X-Request-ID no ciclo FastAPI."""
    mem = AuraSessionMemory(db_path=":memory:")
    engine = AuraEngine(session_memory=mem)
    app = create_aura_app(engine=engine)
    client = TestClient(app)

    # 1. Requisicao sem X-Request-ID previo -> API deve gerar novo UUIDv4
    resp = client.get("/api/v1/aura/health")
    assert resp.status_code == 200
    assert "X-Request-ID" in resp.headers
    generated_req_id = resp.headers["X-Request-ID"]
    assert len(generated_req_id) > 10

    # 2. Requisicao com X-Request-ID explicitamente fornecido -> API deve preservar o mesmo
    custom_id = "custom-trace-id-post-999"
    resp2 = client.get("/api/v1/aura/health", headers={"X-Request-ID": custom_id})
    assert resp2.status_code == 200
    assert resp2.headers["X-Request-ID"] == custom_id
