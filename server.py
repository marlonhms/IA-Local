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

import io
import json
import os
import socket
import sys
import threading
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

# Protege terminal UTF-8 no Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, io.UnsupportedOperation):
        pass

# Garante path absoluto da raiz
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

import uvicorn

from core.aura_api import create_aura_app

app = create_aura_app()


def check_aura_service_active(port: int, timeout: float = 1.0) -> bool:
    """Verifica se o backend da AURA ja esta ativo e respondendo na porta."""
    url = f"http://127.0.0.1:{port}/api/v1/aura/health"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "AuraHealthChecker/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                payload = json.loads(response.read().decode("utf-8"))
                return payload.get("status") == "healthy" or "AURA" in str(payload.get("service", ""))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return False
    return False


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Testa se a porta TCP especificada ja esta ocupada."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def main():
    host = os.getenv("AURA_HOST", "0.0.0.0")
    port = int(os.getenv("AURA_PORT", "8000"))
    auto_open = os.getenv("AURA_AUTO_OPEN", "1").lower() not in ("0", "false", "no")

    local_access_url = f"http://127.0.0.1:{port}"
    network_host_str = "Rede Local / Tailscale" if host == "0.0.0.0" else host

    # 1. Se a porta ja estiver escutando, verifica se o servico da AURA ja esta em execucao
    if is_port_in_use(port):
        if check_aura_service_active(port):
            print("=" * 75)
            print("✨ AURA // SERVIÇO EM SEGUNDO PLANO JÁ ATIVO E OPERACIONAL")
            print(f"   O backend da AURA já está em execução no Windows (porta {port}).")
            print(f"   Acesso Local:       {local_access_url}")
            print(f"   Documentação API:   {local_access_url}/docs")
            print("   Prontidão:          Supervisão Ativa de Pista, Tanques e Fechamento")
            print("=" * 75)
            if auto_open:
                try:
                    webbrowser.open(local_access_url)
                except (webbrowser.Error, OSError):
                    pass
            print(f"\n[OK] Cockpit Operacional disponível no navegador em {local_access_url}.")
            print("     O serviço da AURA já está ativo e operando em segundo plano (AuraBackendService).")
            return
        else:
            # Porta ocupada por outro processo
            print(f"[!] A porta {port} esta ocupada por outro processo.")
            alternative_port = port + 1
            while is_port_in_use(alternative_port) and alternative_port < port + 20:
                alternative_port += 1
            print(f"[*] Redirecionando automaticamente para a porta {alternative_port}...")
            port = alternative_port
            local_access_url = f"http://127.0.0.1:{port}"

    print("=" * 75)
    print("✨ AURA // ASSISTENTE EXECUTIVA DE PRONTIDÃO (POSTO & PDV)")
    print(f"   Acesso Local:       {local_access_url}")
    print(f"   Escuta em Rede:     http://{host}:{port} ({network_host_str})")
    print(f"   Documentação API:   {local_access_url}/docs")
    print("   Prontidão:          Supervisão Ativa de Pista, Tanques e Fechamento")
    print("=" * 75)

    if auto_open:
        def _open_browser():
            import time
            time.sleep(1.2)
            try:
                webbrowser.open(local_access_url)
            except (webbrowser.Error, OSError):
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
