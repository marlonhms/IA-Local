"""
Servidor MCP (Model Context Protocol) da AURA (Fase 5A - Roadmap Next-Gen).
Expoe ferramentas estritamente read-only e sanitizadas contra PII via protocolo MCP
(stdio para uso local e JSON-RPC sobre HTTP autenticado por X-Partner-Key).
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import json
from contextlib import suppress
from datetime import UTC, datetime
from typing import Any

from core.sanitizer import central_log_sanitizer, sanitize_dict

try:
    from mcp.server.mcpserver import MCPServer
except ImportError:  # Compatibilidade com SDK mcp 1.x
    from mcp.server.fastmcp import FastMCP as MCPServer

try:
    mcp = MCPServer("AURA-Intelligence")
except TypeError:
    mcp = MCPServer("AURA-Intelligence", json_response=True)


def _sanitize_payload(data: Any) -> Any:
    """Aplica sanitizacao LGPD/PII em qualquer dicionario ou string retornada via MCP."""
    if isinstance(data, dict):
        cleaned, _ = sanitize_dict(data)
        return cleaned
    if isinstance(data, list):
        return [_sanitize_payload(item) for item in data]
    if isinstance(data, str):
        cleaned_text, _ = central_log_sanitizer.sanitize_text(data)
        return cleaned_text
    return data


@mcp.tool()
def aura_get_executive_snapshot(station_id: str = "posto_01") -> dict[str, Any]:
    """Retorna snapshot executivo read-only da operacao (sanitizado contra PII)."""
    from core.partner_api import (
        compute_station_roi_diagnostic,
        generate_morning_briefing_payload,
        get_partner_staging_store,
    )

    staging = get_partner_staging_store()
    clean_station = staging.sanitize_station_id(station_id)
    briefing = generate_morning_briefing_payload(clean_station, staging_store=staging)
    roi = compute_station_roi_diagnostic(clean_station, staging_store=staging)
    raw = {
        "stationCode": clean_station,
        "briefing": briefing,
        "roi_diagnostic": roi,
    }
    return _sanitize_payload(raw)


@mcp.tool()
def aura_query_erp_metric(domain: str = "vendas", period_days: int = 1) -> dict[str, Any]:
    """Consulta metricas operacionais agregadas read-only do ERP (vendas, estoque, tanques)."""
    from core.tools import PostoTools

    tools = PostoTools()
    norm = str(domain or "vendas").strip().lower()
    if norm in ("tanques", "runout"):
        res = tools.prever_esgotamento_tanques()
    elif norm in ("estoque", "inventory"):
        res = tools.consultar_estoque_erp()
    else:
        res = tools.consultar_analise_vendas_erp()
    if isinstance(res, dict):
        res = {**res, "period_days": int(period_days)}
    return _sanitize_payload(res)


@mcp.tool()
def aura_run_whatif_simulation(
    product_name: str,
    current_price: float,
    unit_cost: float,
    daily_volume: float,
    price_delta: float,
    horizon_days: int = 30,
) -> dict[str, Any]:
    """Executa simulacao deterministica What-If de preco e ponto de equilibrio."""
    from core.whatif_simulator import simulate_price_change

    res = simulate_price_change(
        product_name=product_name,
        current_price=current_price,
        unit_cost=unit_cost,
        daily_volume=daily_volume,
        price_delta=price_delta,
        horizon_days=horizon_days,
    )
    return _sanitize_payload(res)


@mcp.tool()
def aura_trace_causal_rca(
    anomaly_node_id: str,
    tenant_id: str = "posto_01",
    max_hops: int = 4,
) -> dict[str, Any]:
    """Rastreia cadeias causais multi-salto no grafo leve SQLite WAL."""
    from core.causal_graph import get_causal_graph

    trace = get_causal_graph().trace_root_cause(
        tenant_id=tenant_id,
        anomaly_node_id=anomaly_node_id,
        max_hops=max_hops,
    )
    return _sanitize_payload(trace)


@mcp.tool()
def aura_search_fiscal_rag(query: str, top_k: int = 3) -> dict[str, Any]:
    """Busca orientacoes fiscais/operacionais somente leitura na base de conhecimento local."""
    from core.tools import PostoTools

    tools = PostoTools()
    res = tools.consultar_conhecimento_webposto(termo=query, top_k=top_k)
    return _sanitize_payload(res)


@mcp.tool()
def aura_get_realized_roi(
    period_days: int = 30,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """Retorna o scorecard de ROI realmente salvo pela AURA no periodo."""
    from core.outcome_tracker import get_outcome_tracker

    scorecard = get_outcome_tracker().get_realized_roi_scorecard(
        period_days=period_days,
        tenant_id=tenant_id,
    )
    return _sanitize_payload(scorecard.model_dump())


@mcp.resource("aura://telemetry/health")
def get_telemetry_health() -> str:
    """Retorna telemetria resumida de saude do motor local e self-healing."""
    from core.self_healing import get_self_healer

    status = get_self_healer().get_status(limit=5)
    return json.dumps(_sanitize_payload(status), ensure_ascii=False)


@mcp.resource("aura://memory/facts/{tenant_id}")
def get_tenant_memory_facts(tenant_id: str) -> str:
    """Retorna memorias operacionais ativas da filial (sanitizadas contra PII)."""
    from core.tenant_memory import TenantMemoryManager

    facts = TenantMemoryManager().list_facts(tenant_id=tenant_id, status="ativo")
    payload = [f.to_dict() for f in facts]
    return json.dumps(_sanitize_payload(payload), ensure_ascii=False)


@mcp.resource("aura://compliance/status")
def get_compliance_status() -> str:
    """Retorna status read-only e conformidade fiscal/LGPD da instancia."""
    payload = {
        "mode": "READ_ONLY_CLEAN_ROOM",
        "lgpd_sanitizer": "active",
        "sql_mutations_blocked": True,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    return json.dumps(_sanitize_payload(payload), ensure_ascii=False)


def _serialize_call_result(raw_result: Any) -> dict[str, Any]:
    """Normaliza retorno de call_tool do SDK mcp (v1 tuple/list e v2 CallToolResult) e sanitiza."""
    is_error = bool(getattr(raw_result, "is_error", getattr(raw_result, "isError", False)))
    items = getattr(raw_result, "content", None)

    if items is None:
        if isinstance(raw_result, tuple) and raw_result and isinstance(raw_result[0], (list, tuple)):
            # SDK mcp 1.x retorna (list[ContentBlock], structured_dict)
            items = list(raw_result[0])
        elif isinstance(raw_result, (list, tuple)):
            items = list(raw_result)
        elif isinstance(raw_result, dict):
            return {
                "content": [{"type": "text", "text": json.dumps(_sanitize_payload(raw_result), ensure_ascii=False)}],
                "isError": is_error,
            }

    serialized_content: list[dict[str, Any]] = []
    for item in items or []:
        text = getattr(item, "text", None)
        if text is None and isinstance(item, dict):
            if "text" in item:
                text = item["text"]
            else:
                serialized_content.append(
                    {"type": "text", "text": json.dumps(_sanitize_payload(item), ensure_ascii=False)}
                )
                continue
        if text is not None:
            clean_text = _sanitize_payload(str(text))
            serialized_content.append({"type": "text", "text": clean_text})
        else:
            serialized_content.append({"type": "text", "text": _sanitize_payload(str(item))})
    return {
        "content": serialized_content,
        "isError": is_error,
    }


async def handle_mcp_jsonrpc(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Despacha chamadas JSON-RPC 2.0 do protocolo MCP (initialize, tools/list,
    tools/call, resources/list, resources/read) diretamente para o MCPServer.
    """
    req_id = payload.get("id")
    method = str(payload.get("method") or "").strip()
    params = payload.get("params") or {}

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "AURA-Intelligence", "version": "1.0.0"},
                "capabilities": {"tools": {}, "resources": {}},
            },
        }

    if method == "tools/list":
        tools = await mcp.list_tools()
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": t.name,
                        "description": t.description or "",
                        "inputSchema": getattr(t, "inputSchema", None) or getattr(t, "parameters", {}),
                    }
                    for t in tools
                ]
            },
        }

    if method == "tools/call":
        tool_name = str(params.get("name") or "")
        arguments = params.get("arguments") or {}
        raw_res = await mcp.call_tool(tool_name, arguments)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": _serialize_call_result(raw_res),
        }

    if method == "resources/list":
        resources = await mcp.list_resources()
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "resources": [
                    {
                        "uri": str(r.uri),
                        "name": r.name or str(r.uri),
                        "description": r.description or "",
                    }
                    for r in resources
                ]
            },
        }

    if method == "resources/read":
        uri = str(params.get("uri") or "")
        contents = await mcp.read_resource(uri)
        formatted = []
        for c in contents:
            raw_c = getattr(c, "content", str(c))
            with suppress(TypeError):
                raw_c = _sanitize_payload(raw_c)
            formatted.append({"uri": uri, "mimeType": getattr(c, "mime_type", "text/plain"), "text": str(raw_c)})
        return {"jsonrpc": "2.0", "id": req_id, "result": {"contents": formatted}}

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Metodo MCP desconhecido: '{method}'"},
    }
