"""
Testes Unitarios e Avaliacao Golden Set para o RAG Procedural de Manuais do ERP e Roteador Semantico.
Roadmap: roadmap_apendice_conhecimento_multicamada_rag.md (Secoes 8, 9 e 10)

Zero travessoes em todo o arquivo.
"""

import json
import sqlite3
import time
from pathlib import Path

import pytest

from core.rag_engine import HybridRAGEngine
from core.semantic_router import SemanticRouter
from core.tools import PostoTools
from core.webposto_rag import get_webposto_rag

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
GOLDEN_PATH = PROJECT_ROOT / "tests" / "rag" / "golden_procedimentos.json"


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
    """Valida recuperacao de chunks estruturais (pgvector ou contingencia local de 2.343 chunks)."""
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


def test_resolver_url_manual_e_porte_extenso():
    """Valida resolucao de URL oficial do Confluence e deteccao de documento extenso."""
    from core.aura_engine import AuraEngine

    # 1. URL explicita preservada
    c1 = {"doc_url": "https://qualityautomacao.atlassian.net/wiki/spaces/seu ERP/pages/9999"}
    assert AuraEngine._resolver_url_manual(c1) == "https://qualityautomacao.atlassian.net/wiki/spaces/seu ERP/pages/9999"

    # 2. Derivacao automatica a partir de CONF-id
    c2 = {"doc_id": "CONF-65699937"}
    assert AuraEngine._resolver_url_manual(c2) == "https://qualityautomacao.atlassian.net/wiki/spaces/webposto/pages/65699937"

    # 3. Fallback sem url
    c3 = {"doc_id": "OUTRO-123"}
    assert AuraEngine._resolver_url_manual(c3) == ""


def test_prompt_procedimento_erp_dual_pacing():
    """Valida que o prompt de procedimentos contem as diretrizes de Dual-Pacing e links."""
    from core.prompts.system_prompts import build_procedimento_erp_prompt

    prompt = build_procedimento_erp_prompt(
        pergunta_sanitizada="como fazer fechamento de caixa",
        contexto_sanitizado="Trecho de manual",
        historico_formatado="",
    )
    assert "Dual-Pacing" in prompt
    assert "EXTENSO" in prompt
    assert "DIRETO" in prompt
    assert "Manual Completo no Confluence" in prompt


def test_golden_set_30_procedimentos_accuracy_and_latency():
    """
    Executa a avaliacao obrigatoria da Secao 10 do roadmap_apendice_conhecimento_multicamada_rag.md:
    - 30 perguntas reais de operacao em tests/rag/golden_procedimentos.json
    - Acerto Top-3 >= 85%
    - Acerto Top-1 >= 65%
    - Latencia p95 < 300 ms
    """
    assert GOLDEN_PATH.exists(), f"Golden Set nao encontrado em {GOLDEN_PATH}"
    golden_items = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    assert len(golden_items) >= 30, "O Golden Set deve conter pelo menos 30 casos reais de operacao"

    rag_local = get_webposto_rag()
    top1_hits = 0
    top3_hits = 0
    latencies_ms = []

    for item in golden_items:
        q = item["pergunta"]
        expected_doc = item["doc_id_esperado"]
        t0 = time.perf_counter()
        results = rag_local.buscar_chunks_procedimentos(q, top_k=5) if "top_k" in rag_local.buscar_chunks_procedimentos.__code__.co_varnames else rag_local.buscar_chunks_procedimentos(q, limit=5)
        dt_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(dt_ms)

        doc_ids = []
        for r in results:
            if r["doc_id"] not in doc_ids:
                doc_ids.append(r["doc_id"])

        if doc_ids and doc_ids[0] == expected_doc:
            top1_hits += 1
        if expected_doc in doc_ids[:3]:
            top3_hits += 1

    total = len(golden_items)
    top1_rate = (top1_hits / total) * 100.0
    top3_rate = (top3_hits / total) * 100.0
    latencies_sorted = sorted(latencies_ms)
    p95_ms = latencies_sorted[int(len(latencies_sorted) * 0.95) - 1]

    assert top1_rate >= 65.0, f"Acerto Top-1 ({top1_rate:.1f}%) abaixo da meta de 65%"
    assert top3_rate >= 85.0, f"Acerto Top-3 ({top3_rate:.1f}%) abaixo da meta de 85%"
    assert p95_ms < 300.0, f"Latencia p95 ({p95_ms:.1f} ms) acima do limite de 300 ms"


def test_out_of_scope_refusal_and_data_routing_and_tenant_isolation():
    """
    Valida metas de seguranca da Secao 10:
    1. Perguntas fora do acervo recusadas (>= 90%)
    2. Perguntas de dados do posto roteadas para ferramentas do ERP (100%, nunca para procedimento_erp)
    3. Isolamento entre tenants (0 vazamento de chunks da camada 'tenant' de outro posto)
    """
    rag_local = get_webposto_rag()
    router = SemanticRouter()

    # 1. Perguntas fora do acervo devem retornar vazio (evidencia_insuficiente)
    out_of_scope_queries = [
        "como fazer receita de bolo de cenoura com cobertura de chocolate?",
        "qual a escalacao da selecao brasileira na copa do mundo de 1994?",
        "como declarar imposto de renda pessoa fisica no carne leao?",
        "como configurar roteador wifi tp-link residencial?",
        "qual a previsao do tempo para amanha em curitiba?",
        "como trocar o pneu furado de uma bicicleta na trilha?",
        "como plantar tomates organicos em apartamento?",
        "como reservar passagem aerea internacional com milhas?",
        "qual a capital da australia e sua populacao?",
        "como afinar um violao acustico de seis cordas?",
    ]
    refused = 0
    for q_oos in out_of_scope_queries:
        res = rag_local.buscar_chunks_procedimentos(q_oos, limit=3)
        if len(res) == 0:
            refused += 1
    refusal_rate = (refused / len(out_of_scope_queries)) * 100.0
    assert refusal_rate >= 90.0, f"Taxa de recusa fora do escopo ({refusal_rate:.1f}%) abaixo de 90%"

    # 2. Perguntas de dados operacionais devem ir 100% para ferramentas do ERP (nunca procedimento_erp)
    erp_data_queries = [
        "qual o volume atual dos tanques de combustivel?",
        "como fechou o turno de ontem na pista?",
        "quais foram os produtos mais vendidos hoje na conveniencia?",
        "qual a margem liquida da gasolina comum neste mes?",
        "existem fugas financeiras ou quebras de caixa hoje?",
    ]
    for q_data in erp_data_queries:
        intent, _, _ = router.route(q_data)
        assert intent != "procedimento_erp", f"Pergunta de dados '{q_data}' roteou indevidamente para procedimento_erp"

    # 3. Isolamento estrito de tenant na camada 'tenant'
    db_path = rag_local.db_path
    with sqlite3.connect(str(db_path)) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT OR REPLACE INTO aura_conhecimento_chunks (
                camada, vertical, erp, tenant_id, status, fonte,
                doc_id, doc_titulo, doc_url, doc_versao, breadcrumb, secao,
                chunk_idx, chunk_total, conteudo, conteudo_embed, n_tokens, hash_md5
            ) VALUES (
                'tenant', 'posto', 'webposto', 'posto_secreto_alpha', 'ativo', 'tenant_memory',
                'TENANT-SECRET-999', 'Procedimento Exclusivo Cofre Alpha', '', 1, 'Memoria > Cofre Alpha', 'Regra Secreta',
                0, 1, 'O cofre exclusivo alpha usa protocolo biometrico safira.', 'Cofre Alpha safira', 15, 'hash_secret_alpha'
            );
            """
        )
        cur.execute("SELECT id FROM aura_conhecimento_chunks WHERE doc_id = 'TENANT-SECRET-999';")
        sec_id = cur.fetchone()[0]
        cur.execute(
            """
            INSERT INTO chunks_fts(rowid, doc_id, doc_titulo, breadcrumb, secao, conteudo)
            VALUES (?, 'TENANT-SECRET-999', 'Procedimento Exclusivo Cofre Alpha', 'Memoria > Cofre Alpha', 'Regra Secreta', 'O cofre exclusivo alpha usa protocolo biometrico safira.');
            """,
            (sec_id,),
        )
        conn.commit()

    try:
        # Consulta por outro tenant ('posto_beta') NAO pode ver o chunk de 'posto_secreto_alpha'
        res_other = rag_local.buscar_chunks_procedimentos(
            "como funciona o protocolo biometrico safira no cofre exclusivo alpha?",
            tenant_id="posto_beta",
            limit=5,
        )
        leaked_ids = [r["doc_id"] for r in res_other if r["doc_id"] == "TENANT-SECRET-999"]
        assert len(leaked_ids) == 0, f"Vazamento de tenant detectado para posto_beta: {leaked_ids}"

        # Consulta pelo proprio tenant ('posto_secreto_alpha') DEVE encontrar seu chunk
        res_own = rag_local.buscar_chunks_procedimentos(
            "como funciona o protocolo biometrico safira no cofre exclusivo alpha?",
            tenant_id="posto_secreto_alpha",
            limit=5,
        )
        own_ids = [r["doc_id"] for r in res_own if r["doc_id"] == "TENANT-SECRET-999"]
        assert len(own_ids) == 1, "O proprio tenant deveria recuperar sua memoria ativa"
    finally:
        with sqlite3.connect(str(db_path)) as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM aura_conhecimento_chunks WHERE doc_id = 'TENANT-SECRET-999';")
            cur.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild');")
            cur.execute("INSERT INTO chunks_fts(chunks_fts, rank) VALUES('rank', 'bm25(0.0, 10.0, 5.0, 3.0, 1.0)');")
            conn.commit()


def test_zero_unicode_dashes_in_test():
    """Garante ausencia de travessoes proibidos neste arquivo de teste e no golden set."""
    for p in (Path(__file__), GOLDEN_PATH):
        text = p.read_text(encoding="utf-8")
        assert chr(8212) not in text, f"Em-dash encontrado em {p.name}"
        assert chr(8211) not in text, f"En-dash encontrado em {p.name}"
