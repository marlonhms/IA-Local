"""
Modulo de GraphRAG Causal Leve em SQLite WAL (Fase 4 - Roadmap Next-Gen).
Conecta entidades operacionais (Fornecedor -> NFe/XML -> Tanque/Produto -> Turno
-> Operador -> Anomalia) e executa travessia BFS ponderada com decaimento temporal
para Root Cause Analysis (RCA) multi-salto em < 30ms sem Neo4j nem GPU.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from collections import deque
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR
from core.logger import logger

DEFAULT_GRAPH_DB_PATH = BASE_DIR / "data" / "aura_causal_graph.db"
VALID_NODE_TYPES = {
    "SUPPLIER",
    "NFE",
    "PRODUCT",
    "TANK",
    "SHIFT",
    "OPERATOR",
    "ANOMALY",
}


def _parse_iso_dt(ts: str | None) -> datetime:
    """Converte string ISO-8601 em datetime UTC aware com fallback para agora."""
    if not ts:
        return datetime.now(UTC)
    dt = datetime.fromisoformat(ts)
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def compute_edge_id(
    tenant_id: str,
    source_id: str,
    relation_type: str,
    target_id: str,
    occurred_at: str,
) -> str:
    """Calcula hash SHA-256 deterministico garantindo ingestao 100% idempotente."""
    bucket_date = str(occurred_at or "")[:10]
    raw = f"{tenant_id}|{source_id}|{relation_type}|{target_id}|{bucket_date}"
    return f"edge_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]}"


class AuraCausalGraph:
    """
    Grafo Causal Operacional leve persistido em SQLite WAL (CPU-only).
    Suporta isolamento estrito por tenant_id e travessia BFS reversa/bidirecional.
    """

    def __init__(self, db_path: Path | str = DEFAULT_GRAPH_DB_PATH) -> None:
        self.db_path_str = str(db_path)
        self._lock = threading.Lock()
        self._mem_conn: sqlite3.Connection | None = None

        if self.db_path_str != ":memory:":
            Path(self.db_path_str).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        """Retorna conexao SQLite persistente protegida por lock para leitura sub-5ms."""
        if self._mem_conn is None:
            self._mem_conn = sqlite3.connect(
                self.db_path_str, timeout=5.0, check_same_thread=False
            )
            self._mem_conn.row_factory = sqlite3.Row
        return self._mem_conn

    def _close_conn(self, conn: sqlite3.Connection) -> None:
        """Mantem conexao persistente reutilizavel (fechada explicitamente em close())."""
        return

    def close(self) -> None:
        """Fecha a conexao SQLite persistente de forma segura."""
        with self._lock:
            if self._mem_conn is not None:
                self._mem_conn.close()
                self._mem_conn = None

    def _init_db(self) -> None:
        """Cria tabelas aura_graph_nodes, aura_graph_edges, WAL e indices."""
        with self._lock:
            conn = self._connect()
            try:
                if self.db_path_str != ":memory:":
                    conn.execute("PRAGMA journal_mode=WAL;")
                    conn.execute("PRAGMA synchronous=NORMAL;")
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS aura_graph_nodes (
                        node_id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        node_type TEXT NOT NULL,
                        label TEXT NOT NULL,
                        metrics_json TEXT NOT NULL DEFAULT '{}',
                        updated_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS aura_graph_edges (
                        edge_id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        source_id TEXT NOT NULL,
                        target_id TEXT NOT NULL,
                        relation_type TEXT NOT NULL,
                        weight REAL NOT NULL DEFAULT 1.0,
                        occurred_at TEXT NOT NULL,
                        evidence_json TEXT NOT NULL DEFAULT '{}',
                        FOREIGN KEY (source_id) REFERENCES aura_graph_nodes(node_id),
                        FOREIGN KEY (target_id) REFERENCES aura_graph_nodes(node_id)
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_edges_target
                    ON aura_graph_edges(tenant_id, target_id)
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_edges_source
                    ON aura_graph_edges(tenant_id, source_id)
                    """
                )
                conn.commit()
            finally:
                self._close_conn(conn)

    def _upsert_node_conn(
        self,
        conn: sqlite3.Connection,
        tenant_id: str,
        node_id: str,
        node_type: str,
        label: str,
        metrics: dict[str, Any] | None = None,
        updated_at: str | None = None,
    ) -> str:
        """Executa upsert de no dentro de uma conexao/transacao existente."""
        clean_type = str(node_type or "ANOMALY").strip().upper()
        if clean_type not in VALID_NODE_TYPES:
            raise ValueError(f"node_type invalido: '{node_type}'.")

        ts = updated_at or datetime.now(UTC).isoformat()
        metrics_str = json.dumps(metrics or {}, ensure_ascii=False)
        conn.execute(
            """
            INSERT INTO aura_graph_nodes (
                node_id, tenant_id, node_type, label, metrics_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(node_id) DO UPDATE SET
                tenant_id = excluded.tenant_id,
                node_type = excluded.node_type,
                label = excluded.label,
                metrics_json = excluded.metrics_json,
                updated_at = excluded.updated_at
            """,
            (node_id, tenant_id, clean_type, label, metrics_str, ts),
        )
        return node_id

    def _upsert_edge_conn(
        self,
        conn: sqlite3.Connection,
        tenant_id: str,
        source_id: str,
        target_id: str,
        relation_type: str,
        weight: float = 1.0,
        occurred_at: str | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> str:
        """Executa upsert de aresta dentro de uma conexao/transacao existente."""
        ts = occurred_at or datetime.now(UTC).isoformat()
        clamped_w = max(0.05, min(1.0, float(weight)))
        edge_id = compute_edge_id(tenant_id, source_id, relation_type, target_id, ts)
        ev_str = json.dumps(evidence or {}, ensure_ascii=False)
        conn.execute(
            """
            INSERT INTO aura_graph_edges (
                edge_id, tenant_id, source_id, target_id,
                relation_type, weight, occurred_at, evidence_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(edge_id) DO UPDATE SET
                weight = excluded.weight,
                occurred_at = excluded.occurred_at,
                evidence_json = excluded.evidence_json
            """,
            (edge_id, tenant_id, source_id, target_id, relation_type, clamped_w, ts, ev_str),
        )
        return edge_id

    def upsert_node(
        self,
        tenant_id: str,
        node_id: str,
        node_type: str,
        label: str,
        metrics: dict[str, Any] | None = None,
        updated_at: str | None = None,
    ) -> str:
        """Insere ou atualiza um no operacional de forma idempotente."""
        with self._lock:
            conn = self._connect()
            try:
                self._upsert_node_conn(conn, tenant_id, node_id, node_type, label, metrics, updated_at)
                conn.commit()
            finally:
                self._close_conn(conn)
        return node_id

    def upsert_edge(
        self,
        tenant_id: str,
        source_id: str,
        target_id: str,
        relation_type: str,
        weight: float = 1.0,
        occurred_at: str | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> str:
        """Insere ou atualiza uma aresta causal deterministica sem duplicar."""
        with self._lock:
            conn = self._connect()
            try:
                edge_id = self._upsert_edge_conn(
                    conn, tenant_id, source_id, target_id, relation_type, weight, occurred_at, evidence
                )
                conn.commit()
            finally:
                self._close_conn(conn)
        return edge_id

    def sync_causal_graph_window(
        self,
        tenant_id: str,
        records: list[dict[str, Any]] | None = None,
        window_days: int = 30,
    ) -> dict[str, int]:
        """
        Materializa nos e arestas em lote numa unica transacao atomica
        (NFe/descarga, turno, operador, anomalia) de forma idempotente.
        """
        cutoff = datetime.now(UTC) - timedelta(days=max(1, int(window_days)))
        nodes_count = 0
        edges_count = 0

        with self._lock:
            conn = self._connect()
            try:
                for rec in records or []:
                    occurred_at = str(rec.get("occurred_at") or datetime.now(UTC).isoformat())
                    if _parse_iso_dt(occurred_at) < cutoff:
                        continue

                    for node in rec.get("nodes", []):
                        self._upsert_node_conn(
                            conn,
                            tenant_id=tenant_id,
                            node_id=node["node_id"],
                            node_type=node["node_type"],
                            label=node["label"],
                            metrics=node.get("metrics"),
                            updated_at=occurred_at,
                        )
                        nodes_count += 1

                    for edge in rec.get("edges", []):
                        self._upsert_edge_conn(
                            conn,
                            tenant_id=tenant_id,
                            source_id=edge["source_id"],
                            target_id=edge["target_id"],
                            relation_type=edge["relation_type"],
                            weight=float(edge.get("weight", 1.0)),
                            occurred_at=occurred_at,
                            evidence=edge.get("evidence"),
                        )
                        edges_count += 1
                conn.commit()
            finally:
                self._close_conn(conn)

        return {"nodes_upserted": nodes_count, "edges_upserted": edges_count}

    def get_counts(self, tenant_id: str | None = None) -> dict[str, int]:
        """Retorna contagem de nos e arestas persistidos (opcionalmente por tenant)."""
        with self._lock:
            conn = self._connect()
            try:
                if tenant_id:
                    n = conn.execute(
                        "SELECT COUNT(*) FROM aura_graph_nodes WHERE tenant_id = ?", (tenant_id,)
                    ).fetchone()[0]
                    e = conn.execute(
                        "SELECT COUNT(*) FROM aura_graph_edges WHERE tenant_id = ?", (tenant_id,)
                    ).fetchone()[0]
                else:
                    n = conn.execute("SELECT COUNT(*) FROM aura_graph_nodes").fetchone()[0]
                    e = conn.execute("SELECT COUNT(*) FROM aura_graph_edges").fetchone()[0]
                return {"nodes": int(n), "edges": int(e)}
            finally:
                self._close_conn(conn)

    def trace_root_cause(
        self,
        tenant_id: str,
        anomaly_node_id: str,
        max_hops: int = 4,
        time_window_hours: int = 72,
        top_k_paths: int = 3,
        reference_time: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Executa BFS ponderada a partir de anomaly_node_id ate max_hops,
        filtrando arestas fora de time_window_hours e aplicando decaimento temporal.
        """
        t0 = time.perf_counter()
        with self._lock:
            conn = self._connect()
            try:
                node_rows = conn.execute(
                    "SELECT node_id, node_type, label, updated_at FROM aura_graph_nodes WHERE tenant_id = ?",
                    (tenant_id,),
                ).fetchall()
                edge_rows = conn.execute(
                    "SELECT source_id, target_id, relation_type, weight, occurred_at FROM aura_graph_edges WHERE tenant_id = ?",
                    (tenant_id,),
                ).fetchall()
            finally:
                self._close_conn(conn)

        nodes_by_id: dict[str, dict[str, Any]] = {
            nr["node_id"]: {
                "node_id": nr["node_id"],
                "node_type": nr["node_type"],
                "label": nr["label"],
                "updated_at": nr["updated_at"],
            }
            for nr in node_rows
        }

        start_node = nodes_by_id.get(anomaly_node_id)
        if start_node is None:
            return {
                "anomaly_node_id": anomaly_node_id,
                "tenant_id": tenant_id,
                "causal_paths": [],
                "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            }

        ref_dt = reference_time or _parse_iso_dt(start_node["updated_at"])
        adjacency: dict[str, list[dict[str, Any]]] = {}
        for er in edge_rows:
            edge_dt = _parse_iso_dt(er["occurred_at"])
            hours_diff = abs((ref_dt - edge_dt).total_seconds()) / 3600.0
            if hours_diff > float(time_window_hours):
                continue
            decay = max(0.2, 1.0 - (hours_diff / max(1.0, float(time_window_hours))))
            eff_weight = round(float(er["weight"]) * decay, 4)

            item_out = {
                "neighbor_id": er["target_id"],
                "relation_type": er["relation_type"],
                "raw_weight": float(er["weight"]),
                "effective_weight": eff_weight,
                "occurred_at": er["occurred_at"],
            }
            item_in = {
                "neighbor_id": er["source_id"],
                "relation_type": er["relation_type"],
                "raw_weight": float(er["weight"]),
                "effective_weight": eff_weight,
                "occurred_at": er["occurred_at"],
            }
            adjacency.setdefault(er["source_id"], []).append(item_out)
            adjacency.setdefault(er["target_id"], []).append(item_in)

        # BFS multi-salto preservando caminhos candidatos completos
        completed_paths: list[dict[str, Any]] = []
        queue: deque[tuple[str, list[str], list[dict[str, Any]], float]] = deque()
        queue.append((anomaly_node_id, [anomaly_node_id], [], 1.0))

        while queue:
            curr_id, path_ids, edge_steps, acc_score = queue.popleft()
            depth = len(edge_steps)
            neighbors = adjacency.get(curr_id, [])

            next_candidates = [n for n in neighbors if n["neighbor_id"] not in path_ids]
            if depth >= max_hops or (depth > 0 and not next_candidates):
                if depth > 0:
                    completed_paths.append(
                        self._format_path(path_ids, edge_steps, acc_score, nodes_by_id)
                    )
                continue

            if depth > 0 and len(next_candidates) > 1:
                # Registra tambem subcaminhos relevantes caso ramifique
                pass

            extended = False
            for edge in next_candidates:
                nxt = edge["neighbor_id"]
                if nxt not in nodes_by_id:
                    continue
                extended = True
                new_score = round(acc_score * edge["effective_weight"], 4)
                queue.append((nxt, [*path_ids, nxt], [*edge_steps, edge], new_score))

            if not extended and depth > 0:
                completed_paths.append(
                    self._format_path(path_ids, edge_steps, acc_score, nodes_by_id)
                )

        completed_paths.sort(key=lambda p: (p["path_score"], p["hops"]), reverse=True)
        top_paths = completed_paths[: max(1, int(top_k_paths))]
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)

        return {
            "anomaly_node_id": anomaly_node_id,
            "tenant_id": tenant_id,
            "causal_paths": top_paths,
            "latency_ms": elapsed_ms,
        }

    @staticmethod
    def _format_path(
        path_ids: list[str],
        edge_steps: list[dict[str, Any]],
        score: float,
        nodes_by_id: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Formata caminho causal em trilha legivel e lista de evidencias auditaveis."""
        start = nodes_by_id[path_ids[0]]
        chain = [f"{start['node_id']} ({start['label']})"]
        for idx, step in enumerate(edge_steps):
            nxt_node = nodes_by_id[path_ids[idx + 1]]
            chain.append(
                f"--[{step['relation_type']} w={step['raw_weight']:.2f}]--> "
                f"{nxt_node['node_id']} ({nxt_node['label']})"
            )
        return {
            "path_score": round(score, 4),
            "hops": len(edge_steps),
            "chain": chain,
            "evidence_ids": path_ids[1:],
        }

    @staticmethod
    def format_for_rag_context(trace_result: dict[str, Any]) -> str:
        """Renderiza o resultado da travessia causal em bloco textual limpo para o RAG."""
        paths = trace_result.get("causal_paths") or []
        if not paths:
            return ""
        lines = [
            f"Cadeias Causais Rastreadas para {trace_result.get('anomaly_node_id')}:"
        ]
        for idx, p in enumerate(paths, start=1):
            lines.append(f"{idx}. [Score {p['path_score']:.2f} | {p['hops']} saltos] " + " ".join(p["chain"]))
        return "\n".join(lines)


_graph_lock = threading.Lock()
_graph_singleton: AuraCausalGraph | None = None


def get_causal_graph() -> AuraCausalGraph:
    """Retorna singleton thread-safe do AuraCausalGraph."""
    global _graph_singleton
    with _graph_lock:
        if _graph_singleton is None:
            _graph_singleton = AuraCausalGraph()
            logger.info("AuraCausalGraph inicializado em %s", _graph_singleton.db_path_str)
        return _graph_singleton


def set_causal_graph(graph: AuraCausalGraph | None) -> None:
    """Permite injetar instancia isolada de AuraCausalGraph em testes."""
    global _graph_singleton
    with _graph_lock:
        _graph_singleton = graph


def reset_causal_graph() -> None:
    """Reseta singleton do AuraCausalGraph."""
    set_causal_graph(None)
