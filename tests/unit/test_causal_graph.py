"""
Testes unitarios do GraphRAG Causal Leve em SQLite WAL (Fase 4 - Roadmap Next-Gen).
Valida ingestao idempotente, travessia multi-salto (3-4 hops), janela temporal,
isolamento multi-tenant, latencia < 30ms em grafo de 500 nos, RAG e endpoint REST.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from core.causal_graph import (
    AuraCausalGraph,
    reset_causal_graph,
    set_causal_graph,
)
from core.rag_engine import HybridRAGEngine


def test_idempotent_ingestion_and_multihop_trace(tmp_path: Path) -> None:
    """Ingestao repetida nao duplica nos/arestas e encontra cadeia causal de 3-4 saltos."""
    graph = AuraCausalGraph(db_path=tmp_path / "causal.db")
    now = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)

    records = [
        {
            "occurred_at": (now - timedelta(hours=2)).isoformat(),
            "nodes": [
                {"node_id": "ANOMALY:lmc_tank1", "node_type": "ANOMALY", "label": "Perda LMC -0.78%"},
                {"node_id": "TANK:1", "node_type": "TANK", "label": "Tanque 1 Gasolina Comum"},
                {"node_id": "NFE:45891", "node_type": "NFE", "label": "Descarga 15.000 L"},
                {"node_id": "SUPPLIER:dist_x", "node_type": "SUPPLIER", "label": "Distribuidora X"},
            ],
            "edges": [
                {
                    "source_id": "ANOMALY:lmc_tank1",
                    "target_id": "TANK:1",
                    "relation_type": "OCCURRED_IN",
                    "weight": 0.95,
                },
                {
                    "source_id": "NFE:45891",
                    "target_id": "TANK:1",
                    "relation_type": "DELIVERED_TO",
                    "weight": 0.92,
                },
                {
                    "source_id": "NFE:45891",
                    "target_id": "SUPPLIER:dist_x",
                    "relation_type": "SUPPLIED_BY",
                    "weight": 0.96,
                },
            ],
        }
    ]

    graph.sync_causal_graph_window("posto_01", records=records)
    counts_1 = graph.get_counts("posto_01")
    # Reexecutar sincronizacao deve ser 100% idempotente
    graph.sync_causal_graph_window("posto_01", records=records)
    counts_2 = graph.get_counts("posto_01")
    assert counts_1 == {"nodes": 4, "edges": 3}
    assert counts_2 == counts_1

    trace = graph.trace_root_cause(
        tenant_id="posto_01",
        anomaly_node_id="ANOMALY:lmc_tank1",
        max_hops=4,
        time_window_hours=72,
        reference_time=now,
    )
    assert len(trace["causal_paths"]) >= 1
    top = trace["causal_paths"][0]
    assert top["hops"] == 3
    assert top["evidence_ids"] == ["TANK:1", "NFE:45891", "SUPPLIER:dist_x"]
    assert top["path_score"] > 0.7
    graph.close()


def test_time_window_filtering_and_tenant_isolation() -> None:
    """Arestas fora da janela temporal e de outros tenants ficam isoladas."""
    graph = AuraCausalGraph(db_path=":memory:")
    now = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)

    graph.upsert_node("tenant_a", "ANOMALY:a1", "ANOMALY", "Quebra Turno", updated_at=now.isoformat())
    graph.upsert_node("tenant_a", "SHIFT:recent", "SHIFT", "Turno Recente")
    graph.upsert_node("tenant_a", "SHIFT:old", "SHIFT", "Turno Antigo 100h")
    graph.upsert_edge(
        "tenant_a",
        "ANOMALY:a1",
        "SHIFT:recent",
        "OCCURRED_IN",
        weight=0.9,
        occurred_at=(now - timedelta(hours=10)).isoformat(),
    )
    graph.upsert_edge(
        "tenant_a",
        "ANOMALY:a1",
        "SHIFT:old",
        "OCCURRED_IN",
        weight=0.9,
        occurred_at=(now - timedelta(hours=100)).isoformat(),
    )

    # Outro tenant nao pode ver dados de tenant_a
    graph.upsert_node("tenant_b", "SHIFT:b1", "SHIFT", "Turno B")
    trace_b = graph.trace_root_cause("tenant_b", "ANOMALY:a1", reference_time=now)
    assert trace_b["causal_paths"] == []

    trace_a = graph.trace_root_cause(
        "tenant_a", "ANOMALY:a1", time_window_hours=72, reference_time=now
    )
    ev_ids = [eid for p in trace_a["causal_paths"] for eid in p["evidence_ids"]]
    assert "SHIFT:recent" in ev_ids
    assert "SHIFT:old" not in ev_ids


def test_performance_500_nodes_under_30ms(tmp_path: Path) -> None:
    """Travessia RCA em grafo com 500 nos executa abaixo de 30ms em CPU comum."""
    graph = AuraCausalGraph(db_path=tmp_path / "perf500.db")
    now = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)
    ts = now.isoformat()

    nodes = [
        {"node_id": f"PRODUCT:{i}", "node_type": "PRODUCT", "label": f"Item {i}"}
        for i in range(499)
    ]
    nodes.append({"node_id": "ANOMALY:margin_drop", "node_type": "ANOMALY", "label": "Queda Margem"})

    edges = [
        {
            "source_id": "ANOMALY:margin_drop",
            "target_id": f"PRODUCT:{i}",
            "relation_type": "COINCIDED_WITH",
            "weight": 0.5 + (i % 5) * 0.1,
        }
        for i in range(25)
    ]
    for i in range(25, 498):
        edges.append(
            {
                "source_id": f"PRODUCT:{i - 25}",
                "target_id": f"PRODUCT:{i}",
                "relation_type": "SUPPLIED_BY",
                "weight": 0.8,
            }
        )

    graph.sync_causal_graph_window("posto_perf", records=[{"occurred_at": ts, "nodes": nodes, "edges": edges}])
    assert graph.get_counts("posto_perf")["nodes"] == 500

    trace = graph.trace_root_cause(
        tenant_id="posto_perf",
        anomaly_node_id="ANOMALY:margin_drop",
        max_hops=4,
        time_window_hours=72,
        top_k_paths=3,
        reference_time=now,
    )
    assert len(trace["causal_paths"]) == 3
    assert trace["latency_ms"] < 30.0
    graph.close()


def test_rag_integration_and_rest_endpoint(client, tmp_path: Path) -> None:
    """Valida integracao em HybridRAGEngine e endpoint POST /api/v1/aura/causal-graph/trace."""
    graph = AuraCausalGraph(db_path=tmp_path / "api_graph.db")
    now = datetime.now(UTC).isoformat()
    graph.upsert_node("posto_01", "ANOMALY:caixa_01", "ANOMALY", "Divergencia Turno 1", updated_at=now)
    graph.upsert_node("posto_01", "OPERATOR:op_12", "OPERATOR", "Operador Turno 1")
    graph.upsert_edge("posto_01", "ANOMALY:caixa_01", "OPERATOR:op_12", "OPERATED_BY", 0.9, occurred_at=now)

    set_causal_graph(graph)
    try:
        rag = HybridRAGEngine.__new__(HybridRAGEngine)
        rag_res = rag.search_causal_rca_context(tenant_id="posto_01", anomaly_node_id="ANOMALY:caixa_01")
        assert "OPERATOR:op_12" in rag_res["causal_context_text"]

        resp = client.post(
            "/api/v1/aura/causal-graph/trace",
            json={"tenant_id": "posto_01", "anomaly_node_id": "ANOMALY:caixa_01"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["causal_paths"][0]["evidence_ids"] == ["OPERATOR:op_12"]
        assert "Cadeias Causais Rastreadas" in body["causal_context_text"]
    finally:
        reset_causal_graph()
        graph.close()


def test_zero_unicode_dashes_in_phase4_files() -> None:
    """Garante ausencia absoluta de travessoes Unicode nos arquivos da Fase 4."""
    root = Path(__file__).resolve().parent.parent.parent
    for path in (root / "core" / "causal_graph.py", Path(__file__)):
        text = path.read_text(encoding="utf-8")
        assert "\u2014" not in text
        assert "\u2013" not in text
