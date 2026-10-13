"""
Fixtures centralizadas para a suite de testes pytest (P1-2).
Zero travessoes em todo o arquivo.
"""

import pytest
from fastapi.testclient import TestClient

from core.aura_api import create_aura_app
from core.aura_engine import AuraEngine, AuraSessionMemory


@pytest.fixture
def mock_session_memory():
    """Fornece memoria isolada SQLite em memoria para cada teste."""
    return AuraSessionMemory(db_path=":memory:")


@pytest.fixture
def engine(mock_session_memory):
    """Instancia de teste do motor cognitivo AURA."""
    return AuraEngine(
        tenant_id="test_corp_tenant",
        filial_id="posto_unit_01",
        session_memory=mock_session_memory,
    )


@pytest.fixture
def app(engine):
    """Aplicacao FastAPI configurada para testes."""
    return create_aura_app(engine=engine)


@pytest.fixture
def client(app):
    """TestClient síncrono para testes de endpoints HTTP."""
    return TestClient(app)
