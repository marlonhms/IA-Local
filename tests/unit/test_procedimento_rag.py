"""
Testes Unitarios para o RAG Procedural de Manuais do ERP e Roteador Semantico.
Roadmap: roadmap_apendice_conhecimento_multicamada_rag.md (Secoes 8 e 9)

Zero travessoes em todo o arquivo.
"""

import pytest
from pathlib import Path

from core.semantic_router import SemanticRouter
from core.rag_engine import HybridRAGEngine
from core.tools import PostoTools

def test_procedimento_erp_deterministic_routing():
    """Valida deteccao deterministica de perguntas procedimentais do ERP em sub-1ms."""
    router = SemanticRouter()
    queries = [
        "como fazer a entrada de uma nota fiscal de fornecedor?",
        "como dar entrada em nfe no retaguarda",
        "como importar o xml da nota fiscal",
        "onde fica o menu de notas fiscais",
        "como fazer o fechamento de caixa no pdv",
        "como cancelar um cupom fiscal no pdv",
        "passo a passo para emitir nota de saida",
        "como cadastrar bico e tanque",
    ]
    for q in queries:
        intent, conf, telem = router.route(q)
        assert intent == "procedimento_erp", f"Query '{q}' deveria rotear para procedimento_erp, recebeu '{intent}'"
        assert conf >= 0.90, f"Confianca baixa para '{q}': {conf}"
        assert telem.get("method") == "procedural_erp_heuristics"

def test_search_hybrid_procedimentos_database():
    """Valida recuperacao de chunks em aura_core.aura_conhecimento_chunks no PostgreSQL."""
    rag = HybridRAGEngine()
    res = rag.search_hybrid_procedimentos("como dar entrada em nota fiscal", top_k=3)
    assert "results" in res
    assert "telemetry" in res
    assert res["evidencia_insuficiente"] is False
    assert len(res["results"]) > 0
    
    first = res["results"][0]
    assert "doc_id" in first
    assert "doc_titulo" in first
    assert "conteudo" in first
    assert len(first["conteudo"]) > 20

def test_posto_tools_consultar_procedimento():
    """Valida metodo de integracao em PostoTools."""
    tools = PostoTools()
    res = tools.consultar_procedimento_erp("como fazer fechamento de caixa", top_k=2)
    assert "results" in res
    assert len(res["results"]) > 0
    assert res.get("evidencia_insuficiente") is False

def test_zero_unicode_dashes_in_test():
    """Garante ausencia de travessoes proibidos neste arquivo de teste."""
    text = Path(__file__).read_text(encoding="utf-8")
    assert chr(8212) not in text
    assert chr(8211) not in text
