"""
Servidor Web Oficial do Painel Operacional & API da AURA.
(Autonomous Unified Retail Assistant - Postos de Combustíveis & PDV)

Inicia o servidor Uvicorn servindo a SPA local e todas as rotas da API:
- Painel Operacional Web: http://127.0.0.1:8000
- Documentação OpenAPI:   http://127.0.0.1:8000/docs
- Chat SSE Stream:        POST http://127.0.0.1:8000/api/v1/aura/chat
- Gatilhos 1-Clique:      POST http://127.0.0.1:8000/api/v1/aura/execute-intent
- Diagnóstico Estações:   GET  http://127.0.0.1:8000/api/v1/aura/stations
- Health Check:           GET  http://127.0.0.1:8000/api/v1/aura/health
"""

import sys
import os
from pathlib import Path

# Protege terminal UTF-8 no Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Garante path absoluto da raiz
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

import uvicorn
import threading
import webbrowser
from core.aura_api import create_aura_app

app = create_aura_app()


def main():
    host = os.getenv("AURA_HOST", "0.0.0.0")
    port = int(os.getenv("AURA_PORT", "8000"))
    auto_open = os.getenv("AURA_AUTO_OPEN", "1").lower() not in ("0", "false", "no")

    local_access_url = f"http://127.0.0.1:{port}"
    network_host_str = "Rede Local / Tailscale" if host == "0.0.0.0" else host

    print("=" * 75)
    print("✨ AURA // ASSISTENTE EXECUTIVA DE PRONTIDÃO (POSTO & PDV)")
    print(f"   Acesso Local:       {local_access_url}")
    print(f"   Escuta em Rede:     http://{host}:{port} ({network_host_str})")
    print(f"   Documentação API:   {local_access_url}/docs")
    print(f"   Prontidão:          Supervisão Ativa de Pista, Tanques e Fechamento")
    print("=" * 75)

    if auto_open:
        def _open_browser():
            import time
            time.sleep(1.2)
            try:
                webbrowser.open(local_access_url)
            except Exception:
                pass
        threading.Thread(target=_open_browser, daemon=True).start()

    uvicorn.run(
        "server:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
