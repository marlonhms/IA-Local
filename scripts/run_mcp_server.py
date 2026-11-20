"""
CLI de execucao standalone do Servidor MCP da AURA (Fase 5A).
Suporta transporte stdio (agentes locais como Claude/Cursor) ou streamable-http.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.mcp_server import mcp


def main() -> int:
    parser = argparse.ArgumentParser(description="Inicia o Servidor MCP da AURA.")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http", "sse"],
        default="stdio",
    )
    args = parser.parse_args()
    mcp.run(transport=args.transport)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
