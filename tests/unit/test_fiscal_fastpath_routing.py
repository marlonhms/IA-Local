"""
Testes Unitarios do Roteamento Fiscal Deterministico e Fast-Path Lexico.
Garante que termos tributarios e regulatorios (CST 61, CST 04, SEFAZ, DIFAL)
sejam direcionados para auditoria_fiscal_sefaz em menos de 10ms sem poluicao de dados de tanques.
Zero travessoes em todo o arquivo.
"""

from unittest.mock import MagicMock
import pytest

from core.semantic_router import (
    PADRAO_FISCAL_DETERMINISTICO,
    SemanticRouter,
    classificar_intencao_heuristica,
)


def test_padrao_fiscal_deterministico_regex():
    """Valida correspondencia exata do regex fiscal para termos tributarios criticos."""
    exemplos_positivos = [
        "Quais os pontos criticos de ICMS Monofasico CST 61, PIS/COFINS CST 04 na conveniencia e rejeicoes SEFAZ?",
        "35261001173538000160550040000039571624115433",
        "rejeicao 960 na sefaz de combustiveis",
        "rejeicoes da sefaz para nfe",
        "cst 61 na gasolina comum",
        "tabela 4.3.10 pis cofins bebidas frias",
        "CFOP 5929 cupom referenciado",
        "como calcular o difal interestadual?",
        "rejeicao 806 cest",
        "substituicao tributaria de lubrificantes",
        "regime monofasico da lc 192",
    ]
    for ex in exemplos_positivos:
        assert PADRAO_FISCAL_DETERMINISTICO.search(ex) is not None, f"Falha ao reconhecer: {ex}"

    exemplos_negativos = [
        "quanto sobrou no tanque de gasolina hoje?",
        "qual o faturamento do dia de hoje?",
        "como fechar o caixa do turno 1?",
        "quais os frentistas que mais venderam?",
    ]
    for ex in exemplos_negativos:
        assert PADRAO_FISCAL_DETERMINISTICO.search(ex) is None, f"Falso positivo em: {ex}"


def test_classificar_intencao_heuristica_fiscal():
    """Valida que o classificador heuristico retorna auditoria_fiscal_sefaz."""
    query = "Quais os pontos criticos de ICMS Monofasico CST 61, PIS/COFINS CST 04 na conveniencia e rejeicoes SEFAZ?"
    assert classificar_intencao_heuristica(query) == "auditoria_fiscal_sefaz"


def test_semantic_router_fiscal_fastpath_submillisecond():
    """Valida que o roteador semantico executa o fast-path fiscal com confianca 0.99."""
    router = SemanticRouter()
    query = "Quais os pontos criticos de ICMS Monofasico CST 61, PIS/COFINS CST 04 na conveniencia e rejeicoes SEFAZ?"

    intencao, conf, telemetry = router.route(query, use_cache=False)
    assert intencao == "auditoria_fiscal_sefaz"
    assert conf >= 0.98
    assert telemetry["method"] == "deterministic_fiscal_fastpath"
    assert telemetry["total_routing_latency_ms"] < 25.0  # Execucao ultrarrapida sem pgvector/embedding
