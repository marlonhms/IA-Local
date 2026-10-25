# -*- coding: utf-8 -*-
"""
Benchmark de velocidade da busca de informacoes da AURA.
Mede o tempo gasto em cada camada:
1. Roteamento semantico (Router)
2. Recuperacao de dados (Tools / Database / Cache)
3. Latencia total de recuperacao
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.aura_api import get_aura_engine

def run_benchmark():
    print("Iniciando motor AURA para amostragem de latencia...")
    engine = get_aura_engine()

    test_queries = [
        "fazer auditoria de fuga financeira",
        "Como estao nossos precos frente a concorrencia?",
        "Audite a conformidade do LMC dos tanques de combustivel",
        "Qual o faturamento de hoje e formas de pagamento?",
        "Quais os produtos mais vendidos na conveniencia?"
    ]

    print("\n=======================================================")
    print("   RELATORIO DE AUDITORIA DE VELOCIDADE (LATENCIA)")
    print("=======================================================\n")

    for q in test_queries:
        t0 = time.perf_counter()

        # 1. Router
        t_r0 = time.perf_counter()
        intencao, conf, tel = engine.router.route(q)
        t_route_ms = (time.perf_counter() - t_r0) * 1000

        # 2. Tool / Data Retrieval
        t_t0 = time.perf_counter()
        query_vec = tel.get("query_vector")
        ctx, res, ret_tel, cache_hit, tool_lat = engine._resolver_contexto_ferramenta(q, intencao, query_vec)
        t_tool_ms = (time.perf_counter() - t_t0) * 1000

        t_total_ms = (time.perf_counter() - t0) * 1000
        print(f"Pergunta: '{q}'")
        print(f"  [1] Classificacao de Rota: {intencao} -> {t_route_ms:.2f} ms")
        print(f"  [2] Execucao da Ferramenta / SQL: {tool_lat:.2f} ms (Wrap: {t_tool_ms:.2f} ms)")
        print(f"  [3] Cache Hit Semantico: {cache_hit}")
        print(f"  --> TEMPO TOTAL DE BUSCA DE DADOS: {t_total_ms:.2f} ms")
        print("-------------------------------------------------------")

if __name__ == "__main__":
    run_benchmark()
