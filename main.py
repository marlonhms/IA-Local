"""
Ponto de Entrada Principal (Main CLI) do Agente Inteligente AURA.
(Autonomous Unified Retail Assistant - Postos de Combustíveis & PDV)

Arquitetura Headless (Fase 1):
- Motor Cognitivo: AuraEngine (core/aura_engine.py)
- Roteador Vetorial: SemanticRouter (pgvector HNSW + heurísticas de baixa latência)
- RAG Híbrido: HybridRAGEngine (GIN FTS + pgvector HNSW + RRF Boost + Cache Semântico)
- 11 Ferramentas Especializadas: PostoTools (ERP PostgreSQL porta 5433)
- Blindagem e Privacidade: CentralLogSanitizer (LGPD & OWASP)
- Memória de Sessão: AuraSessionMemory (SQLite persistente)
- LLM: Google Gemini com Streaming de Resposta em Tempo Real
"""

import os
import sys
import time
import json
import re
import uuid
import asyncio
from typing import Tuple, Optional, Any, Dict

# Garante saída em UTF-8 no terminal Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Adiciona o diretório raiz ao path para importações absolutas
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import (
    GEMINI_API_KEY,
    DB_ERP_CONFIG,
    FALLBACK_MODELS,
    BASE_DIR,
)
from core.aura_engine import (
    AuraEngine,
    AuraChunk,
    AuraChunkType,
    AuraSessionMemory,
    classificar_intencao,
    extrair_combustivel,
    extrair_data_turno,
    extrair_frentista,
    extrair_bico,
    extrair_produto_cesta,
    extrair_grupo,
    limpar_termo_produto,
)
from core.tools import get_erp_connection
from core.semantic_router import SemanticRouter, classificar_intencao_heuristica
import google.generativeai as genai


# =============================================================================
# COMPATIBILIDADE RETROATIVA (LEGACY WRAPPERS)
# =============================================================================

def responder_com_streaming(prompt_sistema: str):
    """Gera resposta do Gemini com Streaming de tokens em tempo real (compatibilidade legada)."""
    t0 = time.perf_counter()
    ttft_ms = None
    primeiro_chunk = True
    texto_completo = []

    for m_name in FALLBACK_MODELS:
        try:
            model = genai.GenerativeModel(m_name)
            response = model.generate_content(
                prompt_sistema,
                stream=True,
                request_options={"timeout": 10}
            )

            for chunk in response:
                try:
                    texto = chunk.text
                except Exception:
                    continue

                if not texto:
                    continue

                if primeiro_chunk:
                    ttft_ms = (time.perf_counter() - t0) * 1000
                    primeiro_chunk = False

                sys.stdout.write(texto)
                sys.stdout.flush()
                texto_completo.append(texto)

            if texto_completo:
                total_llm_ms = (time.perf_counter() - t0) * 1000
                if ttft_ms is None:
                    ttft_ms = total_llm_ms
                return "".join(texto_completo), ttft_ms, total_llm_ms
        except Exception:
            continue

    msg_erro = "Não foi possível obter resposta dos modelos do Gemini no momento."
    print(msg_erro)
    return msg_erro, 0.0, (time.perf_counter() - t0) * 1000


# =============================================================================
# CLI INTERATIVO CONSUMINDO O MOTOR HEADLESS AURA
# =============================================================================

async def _processar_pergunta_cli(engine: AuraEngine, pergunta: str, session_id: str):
    """Processa a pergunta via stream assíncrono do AuraEngine exibindo saída em tempo real."""
    ttft_exibido = False
    telemetria_recebida = None
    cache_atingido = False

    async for chunk in engine.ask_stream(pergunta, session_id=session_id):
        if chunk.chunk_type == AuraChunkType.INTENT and chunk.data:
            intencao = chunk.data.get("intent", "").upper()
            conf = chunk.data.get("confidence", 0.0) * 100
            rota_info = chunk.data.get("routing_telemetry", {})
            metodo = rota_info.get("method", "heuristica")
            metodo_label = "pgvector (halfvec 768d)" if metodo == "vector_pgvector" else metodo
            pg_lat = rota_info.get("pgvector_latency_ms", 0.0)
            print(f"\n🔀 [ROTEADOR SEMÂNTICO] Intenção: {intencao} (Confiança: {conf:.1f}% | Rota: {metodo_label} | Latência pgvector: {pg_lat:.2f}ms)")

        elif chunk.chunk_type == AuraChunkType.TOOL_START:
            intencao_raw = chunk.data.get("intent", "") if chunk.data else ""
            if intencao_raw == "auditoria_turno":
                print(f"🔀 [ROTEADOR] Intenção detectada: Auditoria de Pista & Conciliação de Turnos (ERP Tool)...")
            elif intencao_raw == "previsao_tanques":
                print(f"🔮 [ROTEADOR] Intenção detectada: Previsão de Esgotamento & Sugestão de Pedidos (Run-Out Forecast)...")
            elif intencao_raw == "desempenho_pista_frentistas":
                print(f"⛽ [ROTEADOR] Intenção detectada: Auditoria Operacional de Pista & Desempenho de Frentistas (ERP Tool)...")
            elif intencao_raw == "lmc_anp":
                print(f"📋 [ROTEADOR] Intenção detectada: Livro de Movimentação de Combustíveis (LMC Oficial ANP)...")
            elif intencao_raw == "vendas_analitico":
                print(f"🔀 [ROTEADOR] Intenção detectada: Análise de Vendas (ERP Tool)...")
            elif intencao_raw == "conveniencia_vendas_cruzadas":
                print(f"🛒 [ROTEADOR] Intenção detectada: Inteligência de Conveniência (Market Basket Analysis & Vendas Cruzadas)...")
            elif intencao_raw == "sre_metricas":
                print(f"🔀 [ROTEADOR] Intenção detectada: Telemetria SRE (PostgreSQL & Semantic Router Tool)...")
            elif intencao_raw == "dados_filial":
                print(f"🔀 [ROTEADOR] Intenção detectada: Cadastro da Filial...")
            elif intencao_raw == "estoque_posicao":
                print(f"🔀 [ROTEADOR] Intenção detectada: Consulta de Estoque e Tanques (ERP Tool)...")
            elif intencao_raw == "clientes_ranking":
                print(f"🔀 [ROTEADOR] Intenção detectada: Análise de Clientes e Faturamento (ERP Tool)...")
            else:
                print(f"⚙️  [ROTEADOR] Intenção detectada: Catálogo (Busca Híbrida RRF)...")

        elif chunk.chunk_type == AuraChunkType.CACHE_HIT:
            cache_atingido = True
            sim = chunk.data.get("similarity", 1.0) if chunk.data else 1.0
            print(f"⚡ [CACHE SEMÂNTICO] Hit de cache semântico (Similaridade: {sim:.4f})")
            print("\n🤖 AURA (Cache):\n")

        elif chunk.chunk_type == AuraChunkType.DELTA:
            if not ttft_exibido and not cache_atingido:
                print("\n🤖 AURA (Streaming):\n")
                ttft_exibido = True
            if chunk.text:
                sys.stdout.write(chunk.text)
                sys.stdout.flush()

        elif chunk.chunk_type == AuraChunkType.TELEMETRY:
            telemetria_recebida = chunk.data or {}

        elif chunk.chunk_type == AuraChunkType.DONE:
            print("\n")
            if telemetria_recebida:
                print("-" * 75)
                print("📊 [TELEMETRIA SRE DA REQUISIÇÃO]")
                print(f"  • Rota / Ferramenta:   {telemetria_recebida.get('intent', '').upper()}")
                if telemetria_recebida.get('cache_hit'):
                    print(f"  • ⚡ Hit Cache Semântico: SIM (Custo Zero)")
                print(f"  • Latência Ferramenta: {telemetria_recebida.get('tool_latency_ms', 0.0)} ms")
                if telemetria_recebida.get('lgpd_redacted_count', 0) > 0:
                    print(f"  • 🛡️ LGPD Protegido:    {telemetria_recebida['lgpd_redacted_count']} dado(s) sensível(is) mascarado(s)")
                retrieval = telemetria_recebida.get("retrieval")
                if retrieval:
                    print(f"    - Embedding Gemini:  {retrieval.get('embedding_latency_ms', 0)} ms")
                    print(f"    - PostgreSQL RRF:    {retrieval.get('db_rrf_latency_ms', 0)} ms (HNSW ef={retrieval.get('hnsw_ef_search', 100)})")
                if telemetria_recebida.get('ttft_ms'):
                    print(f"  • ⚡ Time-To-First-Token: {telemetria_recebida.get('ttft_ms', 0.0)} ms (Início da Resposta)")
                if telemetria_recebida.get('llm_total_ms'):
                    print(f"  • ⏳ Duração Total LLM:   {telemetria_recebida.get('llm_total_ms', 0.0)} ms")
                print(f"  • 🏁 Latência Total E2E:  {telemetria_recebida.get('total_e2e_ms', 0.0)} ms")
                print("-" * 75)


def main():
    print("=" * 75)
    print("  AURA - Autonomous Unified Retail Assistant")
    print("  Agente Cognitivo do Posto & PDV (Híbrido HNSW + pgvector + Gemini)")
    print("=" * 75)

    if not GEMINI_API_KEY:
        print("\n[ERRO] Chave GEMINI_API_KEY não configurada no arquivo .env!")
        return

    # Inicializa o Motor Central Headless
    engine = AuraEngine()

    print(f"\n0. Autenticando no Banco ERP ({DB_ERP_CONFIG['host']}:{DB_ERP_CONFIG['port']})...")
    senha_arquivo = BASE_DIR / "backups" / "erp_password.txt"
    if senha_arquivo.exists():
        try:
            with open(senha_arquivo, "r", encoding="utf-8-sig") as f:
                DB_ERP_CONFIG["password"] = f.read().strip("\ufeff \r\n\t")
        except Exception:
            pass

    while True:
        try:
            conn = get_erp_connection()
            conn.close()
            print("   [OK] Conectado ao ERP com sucesso.")
            senha_arquivo.parent.mkdir(parents=True, exist_ok=True)
            with open(senha_arquivo, "w", encoding="utf-8") as f:
                f.write(DB_ERP_CONFIG["password"])
            break
        except Exception as e:
            if "utf-8" in str(e).lower() or "password" in str(e).lower() or "autenticação" in str(e).lower():
                print("\n   [AVISO] Senha do ERP inválida (ou expirada).")
                nova_senha = input("   Digite a senha do ERP de hoje: ").strip()
                DB_ERP_CONFIG["password"] = nova_senha
            else:
                print(f"   [ERRO] Falha ao conectar no ERP: {e}")
                break

    print("\n1. Verificando métricas de saúde operacional da estação (SRE)...")
    try:
        status_estacao = engine.get_stations_status()
        print(f"   [OK] ERP Online: {status_estacao.erp_online} ({status_estacao.erp_host}:{status_estacao.erp_port})")
        print(f"   [OK] Base Vetorial: {status_estacao.total_products_indexed or 0} produtos indexados")
        print(f"   [OK] Cache Hit Ratio: {status_estacao.cache_hit_ratio_percent or 0}% | Conexões: {status_estacao.active_connections or 0}")
    except Exception as e:
        print(f"   [AVISO] Telemetria inicial: {e}")

    print("\n2. Carregando dados cadastrais da filial...")
    dados_filial = engine.get_dados_filial()
    print(f"   [OK] Filial Conectada: {dados_filial.get('idempresa')} - {dados_filial.get('nome')} (PDV {dados_filial.get('pdv')})")

    cli_session_id = f"cli_{uuid.uuid4().hex[:8]}"
    print(f"   [OK] Sessão de Memória Iniciada: {cli_session_id}")

    print("\n" + "-" * 75)
    print("AURA pronta! Digite sua pergunta (ex: vendas, estoque, catálogo) ou 'sair':")
    print("-" * 75)

    while True:
        try:
            pergunta = input("\nVocê > ").strip()
            if not pergunta:
                continue
            if pergunta.lower() in ["sair", "exit", "quit"]:
                print("Encerrando sessão AURA. Até logo!")
                break

            asyncio.run(_processar_pergunta_cli(engine, pergunta, cli_session_id))

        except KeyboardInterrupt:
            print("\nEncerrado.")
            break
        except Exception as e:
            print(f"\n[Erro na consulta]: {e}")


if __name__ == "__main__":
    main()
