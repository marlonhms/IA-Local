"""
Testes unitarios da integracao MCP Server & Client (Fase 5 - Roadmap Next-Gen).
Valida tools/list, tools/call, resources/list, resources/read, bloqueio HTTP 401
sem X-Partner-Key, sanitizacao PII obrigatoria e trava HITL para escritas externas.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from core.mcp_client import AuraMcpClient, is_write_tool
from core.mcp_server import (
    _sanitize_payload,
    _serialize_call_result,
    handle_mcp_jsonrpc,
)
from core.schemas.genui import GenUIEnvelope


async def test_mcp_server_list_call_and_resources() -> None:
    """Valida listagem de tools/resources, leitura de compliance e simulacao What-If via MCP."""
    init_res = await handle_mcp_jsonrpc({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert init_res["result"]["serverInfo"]["name"] == "AURA-Intelligence"

    tools_res = await handle_mcp_jsonrpc({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    tool_names = {t["name"] for t in tools_res["result"]["tools"]}
    assert {
        "aura_get_executive_snapshot",
        "aura_query_erp_metric",
        "aura_run_whatif_simulation",
        "aura_trace_causal_rca",
        "aura_search_fiscal_rag",
        "aura_get_realized_roi",
    }.issubset(tool_names)

    res_list = await handle_mcp_jsonrpc({"jsonrpc": "2.0", "id": 3, "method": "resources/list"})
    uris = {r["uri"] for r in res_list["result"]["resources"]}
    assert "aura://telemetry/health" in uris
    assert "aura://compliance/status" in uris

    res_read = await handle_mcp_jsonrpc(
        {"jsonrpc": "2.0", "id": 4, "method": "resources/read", "params": {"uri": "aura://compliance/status"}}
    )
    compliance_text = res_read["result"]["contents"][0]["text"]
    assert "READ_ONLY_CLEAN_ROOM" in compliance_text

    whatif_call = await handle_mcp_jsonrpc(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "aura_run_whatif_simulation",
                "arguments": {
                    "product_name": "Gasolina Comum",
                    "current_price": 6.19,
                    "unit_cost": 5.75,
                    "daily_volume": 18450.0,
                    "price_delta": -0.08,
                    "horizon_days": 30,
                },
            },
        }
    )
    payload_text = whatif_call["result"]["content"][0]["text"]
    parsed = json.loads(payload_text)
    assert parsed["break_even_daily_volume"] == 22550.0


async def test_mcp_server_sanitizes_pii() -> None:
    """Garante mascaramento obrigatorio de CPF/email/telefone antes da resposta MCP."""
    leaky = {
        "cliente": "Joao Silva",
        "cpf": "529.982.247-25",
        "email": "gestor@postovip.com.br",
        "telefone": "(27) 98886-3635",
    }
    cleaned = _sanitize_payload(leaky)
    serialized = json.dumps(cleaned)
    assert "529.982.247-25" not in serialized
    assert "gestor@postovip.com.br" not in serialized

    with (
        patch(
            "core.partner_api.generate_morning_briefing_payload",
            return_value={"station_id": "posto_01", "notes": "Contato 529.982.247-25 joao@posto.com"},
        ),
        patch(
            "core.partner_api.compute_station_roi_diagnostic",
            return_value={"station_id": "posto_01", "summary": {"total_monthly_leakage_brl": 1200.0}},
        ),
    ):
        call_res = await handle_mcp_jsonrpc(
            {
                "jsonrpc": "2.0",
                "id": 6,
                "method": "tools/call",
                "params": {"name": "aura_get_executive_snapshot", "arguments": {"station_id": "posto_01"}},
            }
        )
    text_out = call_res["result"]["content"][0]["text"]
    assert "529.982.247-25" not in text_out
    assert "joao@posto.com" not in text_out


def test_mcp_http_gateway_auth_401_and_200(client) -> None:
    """Bloqueia chamadas MCP HTTP sem X-Partner-Key (401) e autoriza com chave valida (200)."""
    rpc_req = {"jsonrpc": "2.0", "id": 10, "method": "tools/list"}

    resp_unauth = client.post("/mcp", json=rpc_req)
    assert resp_unauth.status_code == 401

    resp_bad = client.post("/mcp", json=rpc_req, headers={"X-Partner-Key": "chave-errada"})
    assert resp_bad.status_code == 401

    resp_ok = client.post(
        "/mcp",
        json=rpc_req,
        headers={"X-Partner-Key": "whsec_partner_fuel_bi_2026"},
    )
    assert resp_ok.status_code == 200
    tools = {t["name"] for t in resp_ok.json()["result"]["tools"]}
    assert "aura_run_whatif_simulation" in tools


async def test_mcp_client_hitl_governance_on_writes(tmp_path: Path) -> None:
    """Tools read-only executam direto; tools de escrita exigem confirmacao HITL GenUI."""
    cfg_path = tmp_path / "mcp_servers.json"
    cfg_path.write_text(
        json.dumps(
            {
                "servers": [
                    {
                        "name": "erp_nuvem",
                        "transport": "stdio",
                        "command": "echo",
                        "args": [],
                        "read_only": True,
                        "require_hitl_for_writes": True,
                        "enabled": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    called: list[str] = []

    async def fake_invoker(_srv, tool_name: str, _args: dict):
        called.append(tool_name)
        return {"ok": True, "cpf_leak": "529.982.247-25"}

    mcp_client = AuraMcpClient(config_path=cfg_path, tool_invoker=fake_invoker)

    assert is_write_tool("create_invoice") is True
    assert is_write_tool("list_sheets", {"annotations": {"readOnlyHint": False}}) is True
    assert is_write_tool("list_sheets", {"annotations": {"readOnlyHint": True}}) is False

    # Leitura executa direto e sanitiza retorno
    ro_res = await mcp_client.call_external_tool("erp_nuvem", "list_sheets", {"page": 1})
    assert ro_res["executed"] is True
    assert ro_res["requires_hitl"] is False
    assert "529.982.247-25" not in json.dumps(ro_res["result"])
    assert called == ["list_sheets"]

    # Escrita sem aprovacao HITL e bloqueada e gera GenUIEnvelope
    wr_blocked = await mcp_client.call_external_tool(
        "erp_nuvem", "create_invoice", {"total": 500.0}
    )
    assert wr_blocked["executed"] is False
    assert wr_blocked["requires_hitl"] is True
    env = GenUIEnvelope(**wr_blocked["genui_envelope"])
    assert env.component_name == "McpActionConfirmationUI"
    assert called == ["list_sheets"]

    # Apos aprovacao HITL executa normalmente
    wr_ok = await mcp_client.call_external_tool(
        "erp_nuvem", "create_invoice", {"total": 500.0}, hitl_approved=True
    )
    assert wr_ok["executed"] is True
    assert called == ["list_sheets", "create_invoice"]


def test_serialize_call_result_supports_mcp_v1_and_v2_shapes() -> None:
    """Garante compatibilidade com tuple (mcp 1.x) e CallToolResult.content (mcp 2.x)."""
    from types import SimpleNamespace

    v1_tuple = ([SimpleNamespace(text='{"break_even_daily_volume": 22550.0}')], {"break_even_daily_volume": 22550.0})
    out_v1 = _serialize_call_result(v1_tuple)
    assert out_v1["isError"] is False
    assert json.loads(out_v1["content"][0]["text"])["break_even_daily_volume"] == 22550.0

    v2_obj = SimpleNamespace(content=[SimpleNamespace(text='{"ok": true}')], is_error=False)
    out_v2 = _serialize_call_result(v2_obj)
    assert json.loads(out_v2["content"][0]["text"])["ok"] is True


def test_zero_unicode_dashes_in_phase5_files() -> None:
    """Garante ausencia absoluta de travessoes Unicode nos arquivos da Fase 5."""
    root = Path(__file__).resolve().parent.parent.parent
    for path in (
        root / "core" / "mcp_server.py",
        root / "core" / "mcp_client.py",
        root / "scripts" / "run_mcp_server.py",
        root / "config" / "mcp_servers.json",
        Path(__file__),
    ):
        text = path.read_text(encoding="utf-8")
        assert "\u2014" not in text
        assert "\u2013" not in text
