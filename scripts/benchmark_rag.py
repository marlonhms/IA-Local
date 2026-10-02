"""
Script de Benchmark e Validação de Busca:
Compara Dense (HNSW), Sparse (GIN FTS) e Hybrid (RRF)
com exibição de telemetria SRE.
"""

import os
import sys
from pathlib import Path

# Garante saída em UTF-8 no terminal Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.rag_engine import HybridRAGEngine


def run_benchmarks():
    print("=" * 70)
    print("  BENCHMARK & VALIDAÇÃO: RAG HNSW HÍBRIDO (POSTGRESQL 16 + PGVECTOR)")
    print("=" * 70)

    engine = HybridRAGEngine()

    # 1. Obter métricas SRE do PostgreSQL
    print("\n📊 [SRE Metrics] Estado Atual do Banco e Índices:")
    metrics = engine.get_sre_metrics()

    t_stats = metrics.get("table_stats", {})
    db_stats = metrics.get("database_health", {})

    print(f"  • Total de Registros: {t_stats.get('total_rows')}")
    print(f"  • Tamanho da Tabela: {t_stats.get('table_size')} | Índices: {t_stats.get('indexes_size')} (Total: {t_stats.get('total_size')})")
    print(f"  • Cache Hit Ratio: {db_stats.get('cache_hit_ratio_percent')}%")
    print(f"  • Conexões Ativas: {db_stats.get('active_connections')}")

    print("\n  [Índices em Operação]:")
    for idx in metrics.get("index_stats", []):
        print(f"    - {idx['index_name']} ({idx['index_type']}): Tamanho {idx['index_size']} | Scans: {idx['index_scans']}")

    # 2. Consultas de teste para comparar os motores
    queries = [
        ("Semântica / Aplicação", "óleo sintético para motor flex alta performance"),
        ("Código Exato / SKU", "007"),
        ("Marca / Termo Específico", "coca cola zero lata"),
        ("Conveniência / Genérico", "algo doce para comer ou chocolate"),
    ]

    print("\n" + "=" * 70)
    print("  TESTES COMPARATIVOS DE RECUPERAÇÃO (Dense vs Sparse vs Hybrid RRF)")
    print("=" * 70)

    for tipo, query in queries:
        print(f"\n🔍 [Cenário: {tipo}] Query: \"{query}\"")
        print("-" * 70)

        # 1. Híbrido RRF
        res_hybrid = engine.search_hybrid(query, top_k=3)
        t_hyb = res_hybrid["telemetry"]
        print(f"⚡ [Híbrido RRF] Retornou {len(res_hybrid['results'])} itens em {t_hyb['total_retrieval_latency_ms']} ms (DB: {t_hyb['db_rrf_latency_ms']}ms | Emb: {t_hyb['embedding_latency_ms']}ms)")
        for i, p in enumerate(res_hybrid["results"][:2], 1):
            print(f"    {i}. [{p['codpro']}] {p['nompro']} (RRF: {p['rrf_score']:.4f} | Cosine: {p['cosine_similarity']:.2f} | FTS: {p['fts_score']:.2f})")

        # 2. Denso Puro (HNSW)
        res_dense = engine.search_dense_only(query, top_k=3)
        t_den = res_dense["telemetry"]
        print(f"🧠 [Denso HNSW]  Retornou {len(res_dense['results'])} itens em {t_den['total_latency_ms']} ms")
        for i, p in enumerate(res_dense["results"][:2], 1):
            print(f"    {i}. [{p['codpro']}] {p['nompro']} (Cosine: {p['cosine_similarity']:.2f})")

        # 3. Esparso Puro (GIN FTS)
        res_sparse = engine.search_sparse_only(query, top_k=3)
        t_spa = res_sparse["telemetry"]
        print(f"🔎 [Esparso GIN] Retornou {len(res_sparse['results'])} itens em {t_spa['total_latency_ms']} ms")
        for i, p in enumerate(res_sparse["results"][:2], 1):
            print(f"    {i}. [{p['codpro']}] {p['nompro']} (FTS Score: {p['fts_score']:.2f})")


if __name__ == "__main__":
    run_benchmarks()
