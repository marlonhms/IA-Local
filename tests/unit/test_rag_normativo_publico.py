"""
Testes Unitarios: RAG Normativo e Legislacao Tecnica Local (ANP, INMETRO e CONFAZ).
Valida a ingestao no pgvector (schema aura_core.aura_conhecimento_vetores),
enriquecimento de metadados, embeddings deterministicos, busca hibrida RRF sub-segundo,
tolerancia INMETRO (Â±100 ml em 20L), variacao LMC ANP (Â±0,60%) e regras da Resolucao ANP 894/2022.
"""

import time
from unittest.mock import patch

from core.rag_engine import HybridRAGEngine
from scripts.seed_aura_conhecimento import (
    CONHECIMENTO_SEEDS,
    calcular_hash_conhecimento,
    gerar_embedding_deterministico,
)


def test_conhecimento_seeds_estrutura_e_campos_obrigatorios():
    """Valida se todas as sementes normativas possuem os campos canonicos obrigatorios."""
    assert len(CONHECIMENTO_SEEDS) >= 26, f"Esperado ao menos 26 chunks oficiais, encontrado {len(CONHECIMENTO_SEEDS)}"

    campos_obrigatorios = [
        "modulo",
        "topico",
        "titulo",
        "subtitulo",
        "conteudo",
        "metadados",
        "elementos_ui",
        "ui_action",
        "tags",
    ]

    modulos_encontrados = set()
    topicos_vistos = set()

    for idx, seed in enumerate(CONHECIMENTO_SEEDS):
        for campo in campos_obrigatorios:
            assert campo in seed, f"Chunk #{idx} ({seed.get('topico', 'sem_topico')}) nao possui campo '{campo}'"

        modulo = seed["modulo"]
        topico = seed["topico"]
        chave_unica = f"{modulo}|{topico}"
        assert chave_unica not in topicos_vistos, f"Chave duplicada detectada: {chave_unica}"
        topicos_vistos.add(chave_unica)
        modulos_encontrados.add(modulo)

        assert isinstance(seed["metadados"], dict), f"metadados de {chave_unica} deve ser dict"
        assert isinstance(seed["elementos_ui"], dict), f"elementos_ui de {chave_unica} deve ser dict"
        assert isinstance(seed["ui_action"], dict), f"ui_action de {chave_unica} deve ser dict"
        assert isinstance(seed["tags"], list), f"tags de {chave_unica} deve ser list"
        assert len(seed["conteudo"]) > 50, f"Conteudo de {chave_unica} muito curto"

    modulos_esperados = {
        "compliance_anp",
        "metrologia_inmetro",
        "tributario_combustiveis",
        "macroeconomia_bacen",
    }
    assert modulos_esperados.issubset(modulos_encontrados), (
        f"Modulos normativos faltando: {modulos_esperados - modulos_encontrados}"
    )


def test_geracao_embedding_deterministico_qualidade_e_dimensoes():
    """Valida geracao deterministica de vetores unitarios para 768d e 1536d."""
    texto_amostra = "Portaria INMETRO 559/2016 tolerancia volumetrica de bicos 100ml em 20L"

    # Teste de dimensao 768 (padrao nativo pgvector halfvec AURA)
    vec768 = gerar_embedding_deterministico(texto_amostra, dim=768)
    assert len(vec768) == 768
    norma768 = sum(x * x for x in vec768)
    assert 0.98 <= norma768 <= 1.02, f"Vetor nao normalizado: norma={norma768}"

    # Teste de dimensao 1536 (especificada nos requisitos de compatibilidade)
    vec1536 = gerar_embedding_deterministico(texto_amostra, dim=1536)
    assert len(vec1536) == 1536
    norma1536 = sum(x * x for x in vec1536)
    assert 0.98 <= norma1536 <= 1.02, f"Vetor nao normalizado: norma={norma1536}"

    # Teste de determinismo estrito
    vec768_clone = gerar_embedding_deterministico(texto_amostra, dim=768)
    assert vec768 == vec768_clone, "Gerador deterministico deve produzir saidas identicas para o mesmo texto"

    # Teste de sensibilidade a variacao do texto
    texto_outro = "Resolucao ANP 894/2022 direitos do consumidor e teste de proveta"
    vec_outro = gerar_embedding_deterministico(texto_outro, dim=768)
    assert vec768 != vec_outro, "Textos distintos devem gerar vetores diferentes"


def test_delta_hashing_cdc_calculation():
    """Valida calculo deterministico de hash MD5 para Change Data Capture."""
    h1 = calcular_hash_conhecimento(
        modulo="compliance_anp",
        topico="lmc_teste",
        titulo="Titulo Teste",
        subtitulo="Subtitulo Teste",
        conteudo="Conteudo regulatorio de teste",
        elementos_ui={"tipo": "card"},
        ui_action={"action": "open"},
        tags=["anp", "lmc"],
        metadados={"norma": "26/1992"},
    )
    assert isinstance(h1, str)
    assert len(h1) == 32

    # Mesmos parametros devem gerar o mesmo hash
    h2 = calcular_hash_conhecimento(
        modulo="compliance_anp",
        topico="lmc_teste",
        titulo="Titulo Teste",
        subtitulo="Subtitulo Teste",
        conteudo="Conteudo regulatorio de teste",
        elementos_ui={"tipo": "card"},
        ui_action={"action": "open"},
        tags=["anp", "lmc"],
        metadados={"norma": "26/1992"},
    )
    assert h1 == h2

    # Alteracao em metadados deve alterar o hash
    h3 = calcular_hash_conhecimento(
        modulo="compliance_anp",
        topico="lmc_teste",
        titulo="Titulo Teste",
        subtitulo="Subtitulo Teste",
        conteudo="Conteudo regulatorio de teste",
        elementos_ui={"tipo": "card"},
        ui_action={"action": "open"},
        tags=["anp", "lmc"],
        metadados={"norma": "894/2022"},
    )
    assert h1 != h3


def test_recuperacao_hibrida_tolerancia_inmetro_bicos():
    """Valida recuperacao hibrida da tolerancia metrologica INMETRO (Â±100 ml em 20L)."""
    engine = HybridRAGEngine()
    consulta = "tolerancia metrologica bico bomba inmetro 100ml em 20 litros"

    t0 = time.perf_counter()
    res = engine.search_hybrid_conhecimento(consulta, top_k=2)
    latencia_s = time.perf_counter() - t0

    assert res["telemetry"]["db_rrf_latency_ms"] < 500, f"Tempo de busca no banco excedeu sub-segundo: {res['telemetry']['db_rrf_latency_ms']}ms"
    assert latencia_s < 2.5, f"Tempo total excedeu limite de resiliencia: {latencia_s:.3f}s"
    assert "results" in res
    assert len(res["results"]) > 0

    top1 = res["results"][0]
    assert top1["modulo"] == "metrologia_inmetro"
    assert top1["topico"] == "inmetro_559_tolerancia_bombas_100ml"

    # Validacao do conteudo normativo
    conteudo = top1["conteudo"]
    assert "100 ml" in conteudo or "100ml" in conteudo
    assert "20 litros" in conteudo

    # Validacao do enriquecimento de metadados
    meta = top1.get("metadados") or {}
    assert meta.get("erro_maximo_admissivel_ml") == 100
    assert meta.get("volume_padrao_litros") == 20
    assert meta.get("tolerancia_percentual") == 0.50
    assert "Portaria INMETRO" in meta.get("norma", "")


def test_recuperacao_hibrida_variacao_maxima_lmc_anp():
    """Valida recuperacao da regra de variacao maxima do LMC (Â±0,60% Portaria ANP 26/1992)."""
    engine = HybridRAGEngine()
    consulta = "variacao volumetrica maxima perdas sobras LMC ANP 0.60%"

    t0 = time.perf_counter()
    res = engine.search_hybrid_conhecimento(consulta, top_k=2)
    latencia_s = time.perf_counter() - t0

    assert res["telemetry"]["db_rrf_latency_ms"] < 500, f"Tempo de busca no banco excedeu sub-segundo: {res['telemetry']['db_rrf_latency_ms']}ms"
    assert latencia_s < 2.5, f"Tempo total excedeu limite de resiliencia: {latencia_s:.3f}s"
    assert len(res["results"]) > 0

    top1 = res["results"][0]
    assert top1["modulo"] == "compliance_anp"
    assert top1["topico"] == "lmc_tolerancia_variacao_perdas_sobras"

    conteudo = top1["conteudo"]
    assert "0,60%" in conteudo or "0.60%" in conteudo
    assert "Portaria ANP" in conteudo and "26/1992" in conteudo

    meta = top1.get("metadados") or {}
    assert meta.get("tolerancia_maxima_percentual") == 0.60
    assert meta.get("prazo_guarda_anos") == 5
    assert meta.get("tipo_livro") == "LMC"


def test_recuperacao_hibrida_resolucao_anp_894():
    """Valida recuperacao das regras da Resolucao ANP 894/2022 (bandeira e testes de pista)."""
    engine = HybridRAGEngine()
    consulta = "Resolucao ANP 894/2022 fidelidade bandeira teste proveta qualidade"

    t0 = time.perf_counter()
    res = engine.search_hybrid_conhecimento(consulta, top_k=2)
    latencia_s = time.perf_counter() - t0

    assert res["telemetry"]["db_rrf_latency_ms"] < 500, f"Tempo de busca no banco excedeu sub-segundo: {res['telemetry']['db_rrf_latency_ms']}ms"
    assert latencia_s < 2.5, f"Tempo total excedeu limite de resiliencia: {latencia_s:.3f}s"
    assert len(res["results"]) > 0

    top1 = res["results"][0]
    assert top1["modulo"] == "compliance_anp"
    assert top1["topico"] in (
        "anp_894_fidelidade_bandeira_identificacao_precos",
        "anp_894_testes_qualidade_amostra_testemunha",
    )

    meta = top1.get("metadados") or {}
    assert "894" in meta.get("norma", "")
    assert meta.get("orgao") == "ANP"


def test_recuperacao_hibrida_seguranca_pista_descarte_sao():
    """Valida recuperacao da Portaria ANP 858/2021 sobre seguranca e caixa separadora SAO."""
    engine = HybridRAGEngine()
    consulta = "Portaria ANP 858/2021 seguranca pista descarte caixa separadora sao"

    t0 = time.perf_counter()
    res = engine.search_hybrid_conhecimento(consulta, top_k=2)
    latencia_s = time.perf_counter() - t0

    assert res["telemetry"]["db_rrf_latency_ms"] < 500, f"Tempo de busca no banco excedeu sub-segundo: {res['telemetry']['db_rrf_latency_ms']}ms"
    assert latencia_s < 2.5, f"Tempo total excedeu limite de resiliencia: {latencia_s:.3f}s"
    assert len(res["results"]) > 0

    top1 = res["results"][0]
    assert top1["modulo"] == "compliance_anp"
    assert top1["topico"] == "anp_858_seguranca_pista_descarte_sao"
    assert "SAO" in top1["conteudo"]
    assert "INMETRO" in top1["conteudo"]


def test_recuperacao_hibrida_icms_monofasico_e_st_pmpf():
    """Valida distincao entre ICMS Monofasico (LC 192/2022) e ICMS-ST PMPF CONFAZ."""
    engine = HybridRAGEngine()
    consulta = "ICMS monofasico diesel LC 192/2022 ad rem vs ICMS-ST PMPF CONFAZ"

    t0 = time.perf_counter()
    res = engine.search_hybrid_conhecimento(consulta, top_k=2)
    latencia_s = time.perf_counter() - t0

    assert res["telemetry"]["db_rrf_latency_ms"] < 500, f"Tempo de busca no banco excedeu sub-segundo: {res['telemetry']['db_rrf_latency_ms']}ms"
    assert latencia_s < 2.5, f"Tempo total excedeu limite de resiliencia: {latencia_s:.3f}s"
    assert len(res["results"]) > 0

    top1 = res["results"][0]
    assert top1["modulo"] == "tributario_combustiveis"
    assert top1["topico"] in (
        "tributario_icms_monofasico_vs_st_pmpf",
        "tributario_restituicao_icms_st_tema_201_stf",
    )


def test_recuperacao_esparsa_fallback_sem_api():
    """Valida busca esparsa pura FTS quando API nao esta disponivel (modo 100% offline)."""
    engine = HybridRAGEngine()
    with patch.object(engine, "gerar_embedding", return_value=None):
        res = engine.search_hybrid_conhecimento(
            query_text="inmetro bombas 100ml",
            top_k=2,
        )
    assert len(res["results"]) > 0
    assert res["telemetry"]["retrieval_mode"] in ("sparse_fts_fallback", "offline_memory_fallback")
    assert res["results"][0]["modulo"] == "metrologia_inmetro"


def test_resiliencia_com_mock_fallback_banco_indisponivel():
    """Garante resiliencia contra falhas de conexao ativando fallback gracioso em memoria."""
    engine = HybridRAGEngine()

    with patch.object(engine, "_get_connection", side_effect=RuntimeError("Conexao com PostgreSQL posto_ai:5433 interrompida")):
        res = engine.search_hybrid_conhecimento("tolerancia bico 100ml", top_k=2)

    assert "results" in res
    assert len(res["results"]) > 0
    assert res["telemetry"]["retrieval_mode"] == "offline_memory_fallback"
    top1 = res["results"][0]
    assert top1["modulo"] == "metrologia_inmetro"
    assert "100" in top1["conteudo"]


def test_recuperacao_hibrida_recusa_combustivel_fora_especificacao():
    """Valida recuperacao do procedimento obrigatorio de recusa de combustivel fora de especificacao."""
    engine = HybridRAGEngine()
    consulta = "procedimento recusa combustivel fora de especificacao caminhao tanque descarregamento ANP 894"

    t0 = time.perf_counter()
    res = engine.search_hybrid_conhecimento(consulta, top_k=2)
    latencia_s = time.perf_counter() - t0

    assert res["telemetry"]["db_rrf_latency_ms"] < 500, f"Tempo de busca no banco excedeu sub-segundo: {res['telemetry']['db_rrf_latency_ms']}ms"
    assert latencia_s < 2.5, f"Tempo total excedeu limite de resiliencia: {latencia_s:.3f}s"
    assert len(res["results"]) > 0

    top1 = res["results"][0]
    assert top1["modulo"] == "compliance_anp"
    assert top1["topico"] == "anp_894_testes_qualidade_amostra_testemunha"

    conteudo = top1["conteudo"]
    assert "recusa" in conteudo.lower()
    assert "descarregamento" in conteudo.lower()
    assert "dacte" in conteudo.lower() or "danfe" in conteudo.lower()

    meta = top1.get("metadados") or {}
    assert "procedimento_recusa_combustivel" in meta
    assert "impedir" in meta["procedimento_recusa_combustivel"].lower()


def test_recuperacao_esparsa_fallback_garantido_sem_match():
    """Garante que a busca esparsa sem match textual retorne o chunk de fallback com metadados."""
    engine = HybridRAGEngine()
    with patch.object(engine, "gerar_embedding", return_value=None):
        res = engine.search_hybrid_conhecimento(
            query_text="xyz999termoinexistentecompletamentealeatorio",
            top_k=2,
        )
    assert len(res["results"]) > 0
    top1 = res["results"][0]
    assert top1["topico"] == "panorama_operacional"
    assert "metadados" in top1
    assert isinstance(top1["metadados"], dict)


def test_no_em_dash_or_en_dash_in_normative_corpus_and_code():
    """Regra inegociavel: ZERO travoes (em-dash / en-dash) em todo o acervo normativo."""
    for chunk in CONHECIMENTO_SEEDS:
        titulo = chunk["titulo"]
        subtitulo = chunk.get("subtitulo", "")
        conteudo = chunk["conteudo"]
        tags = chunk.get("tags", [])
        metadados = chunk.get("metadados", {})

        texto_completo = f"{titulo} {subtitulo} {conteudo} {' '.join(tags)} {metadados!s}"

        assert "\u2014" not in texto_completo, (
            f"Travessao em-dash proibido encontrado no chunk '{chunk['modulo']}/{chunk['topico']}'"
        )
        assert "\u2013" not in texto_completo, (
            f"Travessao en-dash proibido encontrado no chunk '{chunk['modulo']}/{chunk['topico']}'"
        )
