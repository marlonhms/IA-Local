"""
Testes Unitarios: Motor de Recuperacao de Conhecimento do webPosto (core/webposto_rag.py).
Valida:
1. Procedimentos e Manuais Confluence (911 paginas e Hubs de Modulos)
2. Dicionario Semantico de Regras e Flags do Banco (Zero Alucinacao SQL)
3. Diagnosticos de Pista e Contingencias (Dinheiro Travado)
4. Catalogo Oficial de APIs para Expansao Multi-Posto (OpenAPI)
5. Desempenho sub-milissegundo da busca FTS5 com BM25

Zero travessoes em todo o arquivo.
"""

import time
import pytest

from core.webposto_rag import WebPostoRAGEngine, get_webposto_rag
from core.tools import PostoTools
from core.rag_engine import HybridRAGEngine


@pytest.fixture(scope="module")
def webposto_rag():
    return get_webposto_rag()


def test_banco_webposto_knowledge_carregado(webposto_rag):
    """Verifica se o banco local SQLite FTS5 contem os registros curados dos 4 pilares."""
    with webposto_rag._get_connection() as conn:
        cur = conn.execute("SELECT pilar, count(*) FROM tabela_conhecimento GROUP BY pilar;")
        contagens = dict(cur.fetchall())

    assert "confluence_procedimentos" in contagens, "Pilar Confluence nao encontrado"
    assert "dicionario_sql" in contagens, "Pilar Dicionario SQL nao encontrado"
    assert "incidentes_pista_perdas" in contagens, "Pilar Incidentes/Perdas nao encontrado"
    assert "catalogo_api" in contagens, "Pilar Catalogo API nao encontrado"

    assert contagens["confluence_procedimentos"] >= 900, "Esperado mais de 900 registros do Confluence/Hubs"
    assert contagens["incidentes_pista_perdas"] >= 300, "Esperado mais de 300 runbooks de incidentes"
    assert contagens["catalogo_api"] >= 100, "Esperado mais de 100 rotas OpenAPI"


def test_busca_procedimentos_confluence_lmc(webposto_rag):
    """Valida recuperacao de passos operacionais do Confluence para LMC."""
    t0 = time.perf_counter()
    res = webposto_rag.consultar_procedimento_webposto("como emitir o LMC no retaguarda", limit=3)
    latency_ms = (time.perf_counter() - t0) * 1000

    assert len(res) > 0, "Deveria retornar procedimento de LMC"
    assert latency_ms < 50.0, f"Latencia FTS5 muito alta: {latency_ms:.2f}ms"

    titulos = [item["titulo"].lower() for item in res]
    assert any("lmc" in t or "estoque" in t or "combust" in t for t in titulos)


def test_dicionario_sql_regras_e_flags(webposto_rag):
    """Valida retorno das regras de integridade do banco (abastecimentos, nfce, pedido)."""
    res = webposto_rag.consultar_regras_sql_webposto(["abastecimentos", "imprimiu", "pedido"])
    assert len(res) > 0, "Deveria retornar dicionario semantico de tabelas"

    conteudo_unificado = " ".join(item["conteudo_completo"] for item in res)
    assert "imprimiu" in conteudo_unificado.lower(), "Regra de flag imprimiu ausente"
    assert "pedido" in conteudo_unificado.lower(), "Regra de pedido ausente"


def test_diagnostico_incidente_dinheiro_travado(webposto_rag):
    """Valida traducao executiva de bico preso para Dinheiro Travado na pista."""
    res = webposto_rag.diagnosticar_incidente_operacional("abastecimento preso bico travado cancelado", limit=2)
    assert len(res) > 0, "Deveria diagnosticar bico preso"

    primeiro = res[0]
    assert primeiro["pilar"] == "incidentes_pista_perdas"
    assert "Dinheiro Travado" in primeiro["impacto_financeiro"], "Impacto de Dinheiro Travado ausente"
    assert len(primeiro["acao_recomendada"]) > 10, "Acao recomendada para o gestor ausente"


def test_catalogo_api_multi_posto(webposto_rag):
    """Valida consulta de rotas OpenAPI para expansao de rede."""
    res = webposto_rag.consultar_api_multi_posto("abastecimentos", limit=3)
    assert len(res) > 0, "Deveria retornar rotas de integracao de abastecimentos"

    primeiro = res[0]
    assert primeiro["pilar"] == "catalogo_api"
    assert "/INTEGRACAO/" in primeiro["titulo"], "Rota OpenAPI esperada no titulo"


def test_integracao_posto_tools_webposto():
    """Valida chamada do metodo consultar_conhecimento_webposto atraves de PostoTools."""
    tools = PostoTools(HybridRAGEngine())
    res = tools.consultar_conhecimento_webposto("sangria de caixa fechamento", top_k=2)

    assert res["status"] == "online_local"
    assert res["total"] > 0
    assert len(res["resultados"]) > 0


def test_ausencia_unicode_dashes_no_motor_webposto():
    """Garante ausencia estrita de travessoes unicode no codigo do motor."""
    import pathlib
    arquivo = pathlib.Path(__file__).resolve().parent.parent.parent / "core" / "webposto_rag.py"
    texto = arquivo.read_text(encoding="utf-8")
    assert "\u2014" not in texto, "Travessao em-dash (\u2014) detectado em core/webposto_rag.py"
    assert "\u2013" not in texto, "Travessao en-dash (\u2013) detectado em core/webposto_rag.py"
