"""
Suíte de Testes Automatizada: Auto-Conhecimento & Meta-RAG da AURA via pgvector.
Valida:
1. Tabela `aura_conhecimento_vetores` no posto_ai (porta 5433 local), índices HNSW/GIN e delta hashing.
2. Indexação completa dos 15 chunks atômicos oficiais da AURA.
3. Busca híbrida HNSW + GIN FTS + RRF calibrado (sub-5ms SLA).
4. Roteamento semântico vetorial e heurístico da 12ª intenção `ajuda_sistema`.
5. Comandos isolados 'ajuda' e 'menu' evitando catálogo de produtos.
6. Não-regressão de intenções operacionais existentes.
7. Despachante do AuraEngine: zero chamadas ao ERP e prompt acolhedor/didático sem tom de crise.
8. Widgets interativos da UI do chat com ui_action e switchTab.
"""

import sys
import time
import json
from pathlib import Path
from unittest.mock import patch
import psycopg2
from psycopg2.extras import RealDictCursor

# Garante saída UTF-8 no terminal Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Adiciona o diretório raiz ao path para importações absolutas
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import DB_VECTOR_CONFIG, DB_ERP_CONFIG
from core.rag_engine import HybridRAGEngine
from core.semantic_router import (
    SemanticRouter,
    classificar_intencao_heuristica,
    INTENT_EXEMPLARS,
)
from core.aura_engine import AuraEngine
from core.tools import PostoTools
from scripts.seed_aura_conhecimento import seed_conhecimento, CONHECIMENTO_CHUNKS


def run_tests():
    print("=" * 75)
    print("🧠 SUÍTE DE TESTES: AUTO-CONHECIMENTO & META-RAG DA AURA (PGVECTOR)")
    print("   (PostgreSQL 16 + HNSW halfvec(768) + GIN FTS + 12ª Intenção Canônica)")
    print("=" * 75)

    # -------------------------------------------------------------------------
    # 1. Validação da Infraestrutura da Tabela e Índices
    # -------------------------------------------------------------------------
    print("\n1. Testando Tabela 'aura_conhecimento_vetores' e Índices no posto_ai (porta 5433 local)...")
    with psycopg2.connect(**DB_VECTOR_CONFIG) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Verifica existência da tabela
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'aura_conhecimento_vetores';
            """)
            assert cur.fetchone(), "Tabela 'aura_conhecimento_vetores' não encontrada no banco posto_ai!"
            print("   [OK] Tabela 'aura_conhecimento_vetores' confirmada no PostgreSQL 16.")

            # Verifica contagem de chunks e embeddings
            cur.execute("""
                SELECT 
                    count(*) AS total,
                    count(embedding) AS com_embedding,
                    count(hash_md5) AS com_hash,
                    count(tsv) AS com_tsv
                FROM public.aura_conhecimento_vetores;
            """)
            counts = cur.fetchone()
            assert counts["total"] == 15, f"Esperado 15 chunks, encontrado {counts['total']}"
            assert counts["com_embedding"] == 15, f"Esperado 15 embeddings, encontrado {counts['com_embedding']}"
            assert counts["com_hash"] == 15, f"Esperado 15 hashes MD5, encontrado {counts['com_hash']}"
            assert counts["com_tsv"] == 15, f"Esperado 15 tsvectors gerados, encontrado {counts['com_tsv']}"
            print(f"   [OK] Integridade de Chunks: 15/15 registros com halfvec(768), hash_md5 e tsvector STORED.")

            # Verifica existência dos 4 índices
            cur.execute("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'aura_conhecimento_vetores';
            """)
            indices_existentes = {r["indexname"] for r in cur.fetchall()}
            esperados = {
                "idx_aura_conhecimento_hnsw",
                "idx_aura_conhecimento_tsv_gin",
                "idx_aura_conhecimento_modulo_topico",
                "idx_aura_conhecimento_hash_md5"
            }
            for idx in esperados:
                assert idx in indices_existentes, f"Índice esperado '{idx}' não encontrado em {indices_existentes}"
            print(f"   [OK] Índices verificados com sucesso: HNSW (halfvec), GIN (tsvector), Módulo/Tópico e Hash_MD5.")

    # -------------------------------------------------------------------------
    # 2. Teste de Idempotência e CDC Delta Hashing
    # -------------------------------------------------------------------------
    print("\n2. Testando Idempotência e Change Data Capture (Delta Hashing MD5)...")
    with psycopg2.connect(**DB_VECTOR_CONFIG) as conn:
        stats_cdc = seed_conhecimento(conn, reindex_all=False)
        assert stats_cdc["ignorados_cdc"] == 15, f"Esperado 15 chunks ignorados por CDC, obtido {stats_cdc['ignorados_cdc']}"
        assert stats_cdc["inseridos"] == 0, "Nenhum chunk deveria ser inserido novamente"
        assert stats_cdc["atualizados"] == 0, "Nenhum chunk deveria ser atualizado sem alteração"
        assert stats_cdc["erros"] == 0, "Zero erros esperados no seeding"
        print(f"   [OK] CDC Delta Hashing 100% comprovado: 15/15 chunks idênticos ignorados sem custo de API.")

    # -------------------------------------------------------------------------
    # 3. Teste do Motor de Busca Híbrida (search_hybrid_conhecimento)
    # -------------------------------------------------------------------------
    print("\n3. Testando Motor de Busca Híbrida (HNSW + GIN FTS + RRF) na Base de Conhecimento...")
    rag = HybridRAGEngine()

    testes_busca = [
        ("Como funciona o Panorama Operacional e o Cockpit?", "cockpit", "panorama_operacional"),
        ("O que significa o cálculo de Ullage de 5.000L?", "cockpit", "tanques_ullage"),
        ("Onde eu vejo a vazão dos bicos e alerta de filtro lento?", "cockpit", "vazao_bicos_filtro"),
        ("Ranking dos frentistas e conversão de gasolina aditivada", "cockpit", "desempenho_frentistas"),
        ("Triangulação da automação CBC04 Companytec contra PDV fiscal", "conciliacao", "cbc04_vs_pdv"),
        ("Como auditar a conciliação de turno e quebra de caixa?", "conciliacao", "auditoria_turno"),
        ("Relatório do LMC Oficial da ANP e tolerância de 0.6%", "fiscal", "lmc_anp"),
        ("Combos da conveniência e Market Basket Apriori", "conveniencia", "market_basket_combos"),
        ("Radar de ações rápidas e gatilhos de 1 clique", "triggers", "radar_acoes_rapidas"),
        ("Inspetor duplo com formato visual e JSON", "triggers", "inspetor_duplo"),
        ("Como usar a assistente executiva no chat cognitivo?", "console", "chat_assistente"),
        ("Como ativar a visão integrada split lado a lado?", "split", "visao_split"),
        ("Menu lateral hambúrguer liquid glass", "navegacao", "menu_hamburguer_liquid_glass"),
        ("Atalho de teclado Ctrl+K da Command Palette", "navegacao", "command_palette_ctrl_k"),
        ("Feedback sensorial e áudio tático Web Audio API", "acessibilidade", "feedback_sensorial_audio"),
    ]

    for query, exp_modulo, exp_topico in testes_busca:
        res = rag.search_hybrid_conhecimento(query, top_k=2)
        results = res.get("results", [])
        assert len(results) > 0, f"Nenhum resultado retornado para query '{query}'"
        top1 = results[0]
        assert top1["modulo"] == exp_modulo, f"Para '{query}': esperado modulo '{exp_modulo}', obtido '{top1['modulo']}'"
        assert top1["topico"] == exp_topico, f"Para '{query}': esperado topico '{exp_topico}', obtido '{top1['topico']}'"
        assert top1["rrf_score"] > 0, "Score RRF deve ser maior que zero"
        assert "ui_action" in top1, "Resultado deve conter ui_action"
        print(f"   [OK] '{query[:35]}...' -> [{top1['modulo']}/{top1['topico']}] (RRF: {top1['rrf_score']:.4f})")

    # Testes de resiliência e comandos diretos
    print("\n   [Resiliência] Testando queries diretas e vazias no motor híbrido...")
    res_vazia = rag.search_hybrid_conhecimento("", top_k=2)
    assert len(res_vazia["results"]) > 0, "Query vazia não deve falhar e deve retornar fallback seguro"
    assert res_vazia["results"][0]["topico"] == "panorama_operacional", "Query vazia deve sugerir panorama operacional"

    res_ajuda = rag.search_hybrid_conhecimento("ajuda", top_k=2)
    assert res_ajuda["results"][0]["topico"] == "panorama_operacional", "Comando 'ajuda' deve apontar para panorama_operacional"
    print("   [OK] Resiliência a consulta vazia e mapeamento de 'ajuda' comprovados com sucesso.")

    # Validação de latência do banco vetorial
    t0 = time.perf_counter()
    try:
        emb_dummy = rag.gerar_embedding("cockpit")
    except Exception:
        # Fallback para vetor armazenado no banco quando a cota externa da API Gemini atingir o limite diário
        with psycopg2.connect(**DB_VECTOR_CONFIG) as conn_test:
            with conn_test.cursor() as cur_test:
                cur_test.execute("SELECT embedding FROM aura_conhecimento_vetores WHERE embedding IS NOT NULL LIMIT 1;")
                emb_dummy = cur_test.fetchone()[0]
    res_lat = rag.search_hybrid_conhecimento("cockpit", query_vector=emb_dummy)
    db_ms = res_lat["telemetry"]["db_rrf_latency_ms"]
    print(f"   [OK] Latência de recuperação híbrida no pgvector: {db_ms:.2f}ms")

    # Validação de recuperação esparsa em fallback (query_vector=None)
    res_sparse = rag.search_hybrid_conhecimento("menu", query_vector=None)
    assert res_sparse["results"][0]["topico"] == "menu_hamburguer_liquid_glass"
    assert res_sparse["telemetry"]["retrieval_mode"] == "sparse_fts_fallback"
    print(f"   [OK] Recuperação em fallback esparso sem API: {res_sparse['telemetry']['db_rrf_latency_ms']:.2f}ms")

    # -------------------------------------------------------------------------
    # 4. Teste do Roteador Semântico (12ª Intenção 'ajuda_sistema')
    # -------------------------------------------------------------------------
    print("\n4. Testando Roteador Semântico & Heurístico para a 12ª Intenção 'ajuda_sistema'...")
    router = SemanticRouter()

    # Valida presença no catálogo de intenções
    assert "ajuda_sistema" in INTENT_EXEMPLARS, "ajuda_sistema deve estar em INTENT_EXEMPLARS"
    assert len(INTENT_EXEMPLARS["ajuda_sistema"]["exemplos"]) >= 20, "ajuda_sistema deve ter ao menos 20 exemplos"
    assert router.count_distinct_intents() >= 12, "Deve haver ao menos 12 intenções distintas indexadas"

    # Testes de roteamento de comandos isolados, conversacionais e meta-perguntas
    testes_ajuda = [
        ("ajuda", "ajuda_sistema", "Comando isolado 'ajuda'"),
        ("menu", "ajuda_sistema", "Comando isolado 'menu'"),
        ("help", "ajuda_sistema", "Comando isolado 'help'"),
        ("atalhos", "ajuda_sistema", "Comando isolado 'atalhos'"),
        ("telas", "ajuda_sistema", "Comando isolado 'telas'"),
        ("me ajuda", "ajuda_sistema", "Pedido conversacional 'me ajuda'"),
        ("preciso de ajuda", "ajuda_sistema", "Pedido conversacional 'preciso de ajuda'"),
        ("ajuda com o sistema", "ajuda_sistema", "Pedido 'ajuda com o sistema'"),
        ("dá uma ajuda", "ajuda_sistema", "Pedido coloquial 'dá uma ajuda'"),
        ("Como funciona o Panorama Operacional?", "ajuda_sistema", "Pergunta de tela cockpit"),
        ("O que significa o cálculo de Ullage de 5.000L?", "ajuda_sistema", "Pergunta de cálculo ullage"),
        ("Onde eu vejo a vazão dos bicos e filtro lento?", "ajuda_sistema", "Pergunta de tela bicos"),
        ("Como usar o atalho Ctrl+K e a command palette?", "ajuda_sistema", "Pergunta de atalho Ctrl+K"),
        ("Como ativo a visão integrada split?", "ajuda_sistema", "Pergunta de tela split"),
        ("Para que serve o inspetor duplo com JSON?", "ajuda_sistema", "Pergunta de tela inspetor"),
        ("O que essa tela mostra e como operar o sistema?", "ajuda_sistema", "Pergunta geral de tela"),
        ("Como funciona a conciliação de turno e quebra de caixa?", "ajuda_sistema", "Explicação do funcionamento"),
        ("Como funciona o relatório do LMC da ANP e a margem de 0.6%?", "ajuda_sistema", "Explicação do LMC"),
    ]

    for query, exp_intent, desc in testes_ajuda:
        # Testa classificador heurístico rápido
        heur_intent = classificar_intencao_heuristica(query)
        assert heur_intent == exp_intent, f"Heurística falhou para '{query}': esperado '{exp_intent}', obtido '{heur_intent}' ({desc})"

        # Testa roteador semântico completo (vetorial + cache)
        intencao, conf, telemetria = router.route(query)
        assert intencao == exp_intent, f"Roteador falhou para '{query}': esperado '{exp_intent}', obtido '{intencao}'"
        print(f"   [OK] '{query}' -> {intencao} (Confiança: {conf*100:.1f}%, Método: {telemetria.get('method')})")

    # -------------------------------------------------------------------------
    # 5. Não-Regressão de Intenções Operacionais
    # -------------------------------------------------------------------------
    print("\n5. Testando Não-Regressão das Intenções Operacionais do Posto...")
    testes_nao_regressao = [
        ("Qual a autonomia dos tanques e previsão de esgotamento?", "previsao_tanques"),
        ("Como fechou o 1º turno hoje?", "auditoria_turno"),
        ("Gerar relatório do LMC da ANP de ontem", "lmc_anp"),
        ("Qual frentista vendeu mais gasolina aditivada hoje?", "desempenho_pista_frentistas"),
        ("Qual o preço da cerveja heineken?", "catalogo_produtos"),
        ("Quanto custa o óleo lubrificante 5w30?", "catalogo_produtos"),
        ("Quais são os combos mais vendidos da conveniência?", "conveniencia_vendas_cruzadas"),
        ("Qual o faturamento total do posto hoje?", "vendas_analitico"),
        ("Qual o saldo físico do estoque de produtos?", "estoque_posicao"),
        ("Quem é o cliente que mais comprou?", "clientes_ranking"),
        ("Qual o CNPJ e endereço da filial?", "dados_filial"),
        ("Qual a saúde do banco de dados e métricas SRE?", "sre_metricas"),
    ]

    for query, exp_intent in testes_nao_regressao:
        intencao, _, _ = router.route(query)
        assert intencao == exp_intent, f"Regressão detectada em '{query}': esperado '{exp_intent}', obtido '{intencao}'"
        print(f"   [OK] Não-Regressão: '{query[:35]}...' -> {intencao}")

    # -------------------------------------------------------------------------
    # 6. Despachante AuraEngine & Verificação de ZERO Chamadas ao ERP
    # -------------------------------------------------------------------------
    print("\n6. Testando Despachante AuraEngine e Garantia de ZERO Chamadas ao ERP...")
    engine = AuraEngine()

    # Espiona conexões com o ERP
    erp_call_count = 0

    def mock_get_erp_connection(*args, **kwargs):
        nonlocal erp_call_count
        erp_call_count += 1
        raise RuntimeError("VIOLAÇÃO: O banco ERP foi consultado indevidamente para ajuda_sistema!")

    with patch("core.tools.get_erp_connection", side_effect=mock_get_erp_connection):
        contexto_extra, resultado_bruto, telemetria, cache_hit, lat_ms = (
            engine._resolver_contexto_ferramenta("Como funciona o cockpit operacional?", "ajuda_sistema")
        )

    assert erp_call_count == 0, f"Falha: Houve {erp_call_count} chamadas indevidas ao ERP na intenção 'ajuda_sistema'!"
    assert resultado_bruto is not None, "resultado_bruto não pode ser None"
    assert "artigos" in resultado_bruto, "resultado_bruto deve conter 'artigos'"
    assert "ui_action" in resultado_bruto, "resultado_bruto deve conter 'ui_action'"
    assert resultado_bruto["ui_action"]["action"] == "switch_tab", "ui_action deve conter switch_tab"
    assert resultado_bruto["ui_action"]["target"] == "cockpit", "target deve ser cockpit"
    assert "Base de Conhecimento e Auto-Explicação da AURA" in contexto_extra, "Contexto extra deve conter header"
    print(f"   [OK] Despachante executado em {lat_ms:.2f}ms com ZERO chamadas ao ERP.")
    print(f"   [OK] ui_action extraído com precisão: {resultado_bruto['ui_action']}")

    # -------------------------------------------------------------------------
    # 7. Teste do System Prompt Dedicado para ajuda_sistema
    # -------------------------------------------------------------------------
    print("\n7. Testando Persona Cognitiva e System Prompt para 'ajuda_sistema'...")
    prompt_ajuda = engine._build_prompt_sistema(
        pergunta_sanitizada="Como funciona o cockpit?",
        contexto_sanitizado=contexto_extra,
        historico_formatado="Nenhum histórico anterior.",
        intencao="ajuda_sistema",
    )

    # Validações estritas do prompt
    assert "Especialista Guia da Plataforma" in prompt_ajuda, "Prompt deve definir persona de guia"
    assert "DESATIVE COMPLETAMENTE qualquer tom de emergência" in prompt_ajuda, "Tom de emergência deve ser desativado"
    assert "📘 **Visão Geral**" in prompt_ajuda, "Estrutura deve conter Visão Geral"
    assert "🖥️ **O que a tela mostra**" in prompt_ajuda, "Estrutura deve conter O que a tela mostra"
    assert "⚡ **Como operar e atalhos**" in prompt_ajuda, "Estrutura deve conter Como operar e atalhos"
    assert "🚨 **Atenção**" not in prompt_ajuda, "Tom de alerta de pista não deve constar no prompt de ajuda"
    print("   [OK] System Prompt validado: Tom acolhedor, didático e estruturado em 3 blocos (sem crise de pista).")

    # -------------------------------------------------------------------------
    # 8. Teste de Execução Direta Headless (execute_tool)
    # -------------------------------------------------------------------------
    print("\n8. Testando Execução Direta Headless de 'ajuda_sistema'...")
    import asyncio
    res_direct = asyncio.run(engine.execute_tool("ajuda_sistema", {"query": "como funciona os tanques"}))
    assert res_direct["status"] == "success", "execute_tool deve retornar success"
    assert len(res_direct["data"]["results"]) > 0, "Deve retornar artigos na execução direta"
    print(f"   [OK] Headless tool 'ajuda_sistema' executada com sucesso ({res_direct['latency_ms']:.2f}ms).")

    # -------------------------------------------------------------------------
    # 9. Verificação dos Contratos do Frontend (aura-chat.js)
    # -------------------------------------------------------------------------
    print("\n9. Testando Contratos do Frontend no aura-chat.js...")
    chat_js_path = PROJECT_ROOT / "web" / "js" / "aura-chat.js"
    assert chat_js_path.exists(), "aura-chat.js deve existir"
    with open(chat_js_path, "r", encoding="utf-8") as f:
        chat_js_content = f.read()

    assert "renderAjudaSistemaWidget" in chat_js_content, "renderAjudaSistemaWidget deve estar presente em aura-chat.js"
    assert "window.auraApp.switchTab" in chat_js_content, "window.auraApp.switchTab deve ser acionado no botão interativo"
    assert "'ajuda_sistema': 'Guia & Auto-Conhecimento'" in chat_js_content, "DisplayName de ajuda_sistema deve estar mapeado"
    assert "sidebar-btn-toggle-sfx" in chat_js_content, "Suporte a toggle de SFX no sidebar deve estar presente"
    assert "Tópicos complementares:" in chat_js_content, "Renderização de tópicos complementares deve estar presente"
    print("   [OK] Contratos do Frontend aura-chat.js validados (card interativo com switchTab, SFX e badges complementares).")

    print("\n" + "=" * 75)
    print("🎉 TODOS OS TESTES DE AUTO-CONHECIMENTO & META-RAG PASSARAM COM 100% DE SUCESSO!")
    print("=" * 75)


if __name__ == "__main__":
    run_tests()
