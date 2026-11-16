"""
Fixtures compartilhadas para a suite de testes no diretorio scripts/ (P1-2).
Fornece fixture engine para AuraEngine desacoplado em testes pytest.
Zero travessoes em todo o arquivo.
"""

import pytest
from core.aura_engine import AuraEngine, AuraSessionMemory


@pytest.fixture
def engine():
    """Instancia de teste de AuraEngine com memoria em SQLite in-memory isolada."""
    mem = AuraSessionMemory(db_path=":memory:")
    return AuraEngine(
        tenant_id="test_suite_tenant",
        filial_id="posto_teste_01",
        session_memory=mem,
    )
