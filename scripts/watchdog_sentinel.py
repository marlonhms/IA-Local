"""
CLI do Sentinela de Resiliencia e Auto-Healing AURA (Fase P3-5).
Executa monitoramento autonomo no Windows da porta 8000 e servico AURA.
Uso:
    python scripts/watchdog_sentinel.py --once
    python scripts/watchdog_sentinel.py --interval 30 --port 8000
    python scripts/watchdog_sentinel.py --status
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import argparse
import io
import json
import signal
import sys
import time
from pathlib import Path
from typing import Any

# Protege terminal UTF-8 no Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, io.UnsupportedOperation, OSError):
        pass

# Garante inclusao da raiz do projeto no PYTHONPATH
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.watchdog import AuraWatchdogSentinel, WatchdogHealthResult


def print_banner() -> None:
    """Exibe cabecalho textual no console."""
    print("=" * 70)
    print("   AURA: SENTINELA DE RESILIENCIA & AUTO-HEALING LOCAL (P3-5)")
    print("=" * 70)


def format_health_line(res: WatchdogHealthResult) -> str:
    """Formata linha de sumario de verificacao de saude."""
    status_tag = "[OK]" if res.healthy else "[FALHA]"
    pid_str = f"PID: {res.pid}" if res.pid else "PID: N/A"
    return (
        f"{status_tag} {res.timestamp} | Porta: {res.port} | {pid_str} | "
        f"HTTP: {res.status_code or 'ERR'} ({res.response_time_ms:.1f}ms) | "
        f"{res.error or 'Saudavel'}"
    )


def main() -> int:
    """Ponto de entrada da CLI do sentinela."""
    parser = argparse.ArgumentParser(
        description="AURA Watchdog Sentinel: monitoramento e auto-healing da porta 8000 no Windows."
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host do servidor local (padrao: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Porta TCP monitorada (padrao: 8000)")
    parser.add_argument(
        "--endpoint",
        default="/api/v1/aura/telemetry/metrics",
        help="Endpoint HTTP de telemetria/health (padrao: /api/v1/aura/telemetry/metrics)",
    )
    parser.add_argument("--service", default="AuraBackendService", help="Nome do servico Windows")
    parser.add_argument(
        "--interval",
        type=float,
        default=30.0,
        help="Intervalo em segundos entre verificacoes (padrao: 30)",
    )
    parser.add_argument("--once", action="store_true", help="Executa uma unica verificacao e encerra")
    parser.add_argument(
        "--no-heal",
        action="store_true",
        help="Desativa auto-healing automatico (modo somente monitoramento)",
    )
    parser.add_argument("--status", action="store_true", help="Exibe diagnostico de status e ultimos incidentes")
    parser.add_argument("--json", action="store_true", help="Formata a saida em JSON estruturado")

    args = parser.parse_args()

    sentinel = AuraWatchdogSentinel(
        host=args.host,
        port=args.port,
        health_endpoint=args.endpoint,
        service_name=args.service,
        check_interval_seconds=args.interval,
        enable_auto_healing=not args.no_heal,
    )

    if args.status:
        st = sentinel.get_status()
        events = sentinel.get_recent_events(limit=10)
        if args.json:
            print(json.dumps({"status": st, "recent_events": events}, indent=2, ensure_ascii=False))
        else:
            print_banner()
            print(f"Status Atual          : {st['status'].upper()}")
            print(f"Porta Monitorada      : {st['port']}")
            print(f"Servico Windows       : {st['service_name']}")
            print(f"Auto-Healing Ativo    : {st['auto_healing_enabled']}")
            print(f"Flapping Detectado    : {st['is_flapping']}")
            print(f"Reinicios Recentes    : {st['recent_healing_attempts']}/{st['max_restart_attempts']}")
            if st.get("contingency_reason"):
                print(f"Alerta Contingencia   : {st['contingency_reason']}")
            print("-" * 70)
            print("Ultimos Incidentes Registrados:")
            if not events:
                print("  Nenhum incidente registrado.")
            for ev in events:
                print(
                    f"  [{ev.get('timestamp')}] {ev.get('event_type')}: "
                    f"{ev.get('reason')} (Sucesso: {ev.get('success')})"
                )
            print("=" * 70)
        return 0

    if args.once:
        res = sentinel.check_health()
        if args.json:
            print(json.dumps(res.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(format_health_line(res))

        if not res.healthy and not args.no_heal:
            print("(!) Anomalia detectada. Disparando rotina de Auto-Healing...")
            healed = sentinel.heal_process(pid=res.pid, reason=res.error or "Falha em --once")
            print(f"(!) Resultado do Auto-Healing: {'SUCESSO' if healed else 'FALHA'}")
            return 0 if healed else 1
        return 0 if res.healthy else 1

    # Modo Daemon: Loop Continuo
    if not args.json:
        print_banner()
        print(f"Monitorando http://{args.host}:{args.port}{args.endpoint}")
        print(f"Intervalo: {args.interval}s | Auto-Healing: {'ATIVO' if not args.no_heal else 'DESATIVADO'}")
        print("Pressione Ctrl+C para encerrar o sentinela.")
        print("-" * 70)

    running = True

    def _sig_handler(sig: int, frame: Any) -> None:
        nonlocal running
        running = False
        if not args.json:
            print("\n[!] Encerrando Sentinela AURA graciosamente...")

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    while running:
        res = sentinel.check_health()
        if args.json:
            print(json.dumps(res.to_dict(), ensure_ascii=False))
        else:
            print(format_health_line(res))

        if not res.healthy and not args.no_heal:
            if not args.json:
                print("  --> Disparando auto-healing defensivo...")
            healed = sentinel.heal_process(pid=res.pid, reason=res.error or "Loop health check failure")
            if not args.json:
                print(f"  --> Resultado da recuperacao: {'SUCESSO' if healed else 'FALHA'}")

        deadline = time.time() + args.interval
        while running and time.time() < deadline:
            time.sleep(0.5)

    return 0


if __name__ == "__main__":
    sys.exit(main())
