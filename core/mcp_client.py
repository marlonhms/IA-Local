"""
Cliente MCP (Model Context Protocol) com Governanca HITL (Fase 5B - Roadmap Next-Gen).
Conecta a servidores MCP externos configurados em config/mcp_servers.json,
permite execucao direta de tools read-only e exige confirmacao HITL em 1-clique
(GenUIEnvelope + AuraCommandJournal) para qualquer tool externa de escrita/mutacao.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from config.settings import BASE_DIR
from core.logger import logger
from core.sanitizer import central_log_sanitizer, sanitize_dict
from core.schemas.genui import GenUIActionOption, GenUIEnvelope

DEFAULT_MCP_CONFIG_PATH = BASE_DIR / "config" / "mcp_servers.json"

WRITE_TOOL_PATTERN = re.compile(
    r"(?:^|_|-)(?:create|update|delete|write|send|post|put|patch|remove|exec|drop|alter|insert|send_email|append)(?:$|_|-)",
    re.IGNORECASE,
)


class McpServerEntry(BaseModel):
    """Configuracao tipada de um servidor MCP externo."""

    name: str
    transport: str = "stdio"
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    url: str | None = None
    read_only: bool = True
    require_hitl_for_writes: bool = True
    enabled: bool = True


def is_write_tool(tool_name: str, tool_metadata: dict[str, Any] | None = None) -> bool:
    """Determina se uma tool MCP externa possui efeito colateral / escrita."""
    meta = tool_metadata or {}
    annotations = meta.get("annotations") if isinstance(meta.get("annotations"), dict) else meta
    if isinstance(annotations, dict) and annotations.get("readOnlyHint") is False:
        return True
    if meta.get("mutating") is True:
        return True
    return bool(WRITE_TOOL_PATTERN.search(str(tool_name or "")))


class AuraMcpClient:
    """
    Gerenciador de conexoes e politica de seguranca para servidores MCP externos.
    """

    def __init__(
        self,
        config_path: Path | str = DEFAULT_MCP_CONFIG_PATH,
        tool_invoker: Callable[[McpServerEntry, str, dict[str, Any]], Awaitable[Any]] | None = None,
    ) -> None:
        self.config_path = Path(config_path)
        self._tool_invoker = tool_invoker

    def load_servers(self) -> list[McpServerEntry]:
        """Carrega configuracao de servidores MCP de config/mcp_servers.json."""
        if not self.config_path.is_file():
            return []
        raw = json.loads(self.config_path.read_text(encoding="utf-8"))
        entries = raw.get("servers", []) if isinstance(raw, dict) else []
        return [McpServerEntry(**item) for item in entries]

    def get_server(self, server_name: str) -> McpServerEntry:
        """Busca servidor configurado por nome."""
        for srv in self.load_servers():
            if srv.name == server_name:
                return srv
        raise KeyError(f"Servidor MCP '{server_name}' nao encontrado em {self.config_path}.")

    async def _invoke_stdio(
        self, server: McpServerEntry, tool_name: str, arguments: dict[str, Any]
    ) -> Any:
        """Executa chamada MCP real via transporte stdio oficial do SDK mcp."""
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        if not server.command:
            raise ValueError(f"Servidor stdio '{server.name}' sem 'command' definido.")

        params = StdioServerParameters(command=server.command, args=server.args)
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            return await session.call_tool(tool_name, arguments)

    async def call_external_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        tool_metadata: dict[str, Any] | None = None,
        hitl_approved: bool = False,
        actor: str = "gestor",
    ) -> dict[str, Any]:
        """
        Executa uma tool MCP externa aplicando politica HITL para operacoes de escrita
        e sanitizando todo retorno contra vazamento de PII.
        """
        server = self.get_server(server_name)
        args = arguments or {}
        mutating = is_write_tool(tool_name, tool_metadata)

        if (mutating or not server.read_only) and server.require_hitl_for_writes and not hitl_approved:
            action_id = str(uuid.uuid4())
            try:
                from core.command_journal import get_command_journal

                get_command_journal().begin_command(
                    command_key=f"mcp_hitl:{server.name}:{tool_name}:{action_id}",
                    action_id=action_id,
                    action_type="MCP_EXTERNAL_WRITE_PENDING",
                    actor=actor,
                    request_payload={
                        "server_name": server.name,
                        "tool_name": tool_name,
                        "arguments": args,
                    },
                )
            except (ImportError, OSError, sqlite3.Error, ValueError) as exc:
                logger.debug("Registro HITL MCP no journal ignorado: %s", exc)

            envelope = GenUIEnvelope(
                tool_call_id=str(uuid.uuid4()),
                component_name="McpActionConfirmationUI",
                intent="mcp_external_write_confirmation",
                executive_summary=(
                    f"Confirmacao HITL obrigatoria para executar '{tool_name}' "
                    f"no servidor MCP externo '{server.name}'."
                ),
                props={
                    "server_name": server.name,
                    "tool_name": tool_name,
                    "arguments": args,
                    "mutating": True,
                },
                actions=[
                    GenUIActionOption(
                        action_id=action_id,
                        label=f"Autorizar {tool_name}",
                        intent="confirm_mcp_write",
                        style="danger",
                        requires_confirmation=True,
                        params={
                            "server_name": server.name,
                            "tool_name": tool_name,
                            "arguments": args,
                            "hitl_approved": True,
                        },
                    )
                ],
            )
            logger.info("MCP Client bloqueou escrita '%s.%s' aguardando HITL.", server.name, tool_name)
            return {
                "executed": False,
                "requires_hitl": True,
                "server_name": server.name,
                "tool_name": tool_name,
                "genui_envelope": envelope.model_dump(mode="json"),
            }

        if self._tool_invoker is not None:
            raw_res = await self._tool_invoker(server, tool_name, args)
        else:
            raw_res = await self._invoke_stdio(server, tool_name, args)

        if isinstance(raw_res, dict):
            sanitized, _ = sanitize_dict(raw_res)
        elif isinstance(raw_res, str):
            sanitized, _ = central_log_sanitizer.sanitize_text(raw_res)
        else:
            sanitized, _ = central_log_sanitizer.sanitize_text(str(raw_res))

        return {
            "executed": True,
            "requires_hitl": False,
            "server_name": server.name,
            "tool_name": tool_name,
            "result": sanitized,
        }
