"""
Suite de Validacao Fim-a-Fim Consolidada GenUI (Fase 8: F8-04)
Runner mestre unificado que orquestra as tres suites centrais de qualidade:
- F8-01: Contratos GenUI e Schemas Pydantic v2 (scripts/test_genui_contracts.py)
- F8-02: Streaming e Bufferizacao GenUI Multiplexada (scripts/test_genui_streaming.py)
- F8-03: Ciclo de Vida Frontend via Node.js (scripts/test_genui_frontend_lifecycle.py)

Garante medicao individual de latencia de cada suite, relatorio estruturado consolidado,
execucao rapida (< 60s) e regressao zero sem chamadas recursivas encadeadas.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import List, Dict, Any

# Garante suporte seguro a UTF-8 no console do Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Importa os executores diretos das suites da Fase 8
from scripts.test_genui_contracts import run_all_contract_tests
from scripts.test_genui_streaming import run_all_streaming_tests
from scripts.test_genui_frontend_lifecycle import run_nodejs_frontend_lifecycle_tests


def run_consolidated_e2e_quality_suite() -> bool:
    print("=" * 80)
    print("AURA GENUI: SUITE INTEGRADA DE QUALIDADE E VALIDACAO FIM-A-FIM (FASE 8)")
    print("=" * 80)
    print("Ambiente: Python 3.12 + Node.js (Headless) + FastAPI SSE + Pydantic v2")
    print("Objetivo: Homologacao dos contratos, streaming resiliente e ciclo de vida DOM\n")

    suites = [
        {
            "id": "F8-01",
            "name": "Contratos GenUI e Schemas Pydantic v2",
            "runner": run_all_contract_tests,
            "description": "Schemas Pydantic v2, imutabilidade, idempotencia RFC 4122 v4 e HMAC-SHA256"
        },
        {
            "id": "F8-02",
            "name": "Streaming e Bufferizacao GenUI",
            "runner": run_all_streaming_tests,
            "description": "Emissao multiplexada SSE, zero vazamento JSON, fragmentacao TCP (16-128B)"
        },
        {
            "id": "F8-03",
            "name": "Ciclo de Vida Frontend via Node.js",
            "runner": run_nodejs_frontend_lifecycle_tests,
            "description": "Montagem DOM dos 6 micro-widgets, Zero CLS, State Lock, Rollback e XSS"
        }
    ]

    results: List[Dict[str, Any]] = []
    total_start_time = time.perf_counter()
    all_passed = True

    for suite in suites:
        print("\n" + "-" * 80)
        print(f"Executando {suite['id']}: {suite['name']}...")
        print(f"Descricao: {suite['description']}")
        print("-" * 80)

        suite_start = time.perf_counter()
        suite_status = "PASS"
        suite_error = None

        try:
            suite["runner"]()
        except Exception as exc:
            suite_status = "FAIL"
            suite_error = str(exc)
            all_passed = False
            print(f"[ERRO] Falha na execucao da suite {suite['id']}: {exc}")
        finally:
            elapsed = time.perf_counter() - suite_start
            results.append({
                "id": suite["id"],
                "name": suite["name"],
                "status": suite_status,
                "elapsed": elapsed,
                "error": suite_error
            })

    total_elapsed = time.perf_counter() - total_start_time

    # =========================================================================
    # RELATORIO CONSOLIDADO DE METRICAS E QUALIDADE
    # =========================================================================
    print("\n" + "=" * 80)
    print("RELATORIO CONSOLIDADO DE QUALIDADE GENUI (FASE 8)")
    print("=" * 80)
    print(f"{'SUITE':<8} | {'NOME':<42} | {'TEMPO (s)':<10} | {'STATUS':<8}")
    print("-" * 80)

    for res in results:
        status_display = f"[OK] {res['status']}" if res["status"] == "PASS" else f"[FALHA] {res['status']}"
        print(f"{res['id']:<8} | {res['name']:<42} | {res['elapsed']:<10.3f} | {status_display:<8}")

    print("-" * 80)
    print(f"Tempo Total Consolidado: {total_elapsed:.3f}s (Limite: < 60.000s)")

    if total_elapsed < 60.0:
        print("[OK] Meta de desempenho cumprida com sucesso (< 60s).")
    else:
        print("[ALERTA] Tempo consolidado excedeu a meta esperada de 60s.")

    print("=" * 80)

    if all_passed:
        print("CONCLUSAO: TODAS AS 3 SUITES DA FASE 8 FORAM HOMOLOGADAS COM 100% DE SUCESSO!")
        print("=" * 80 + "\n")
        return True
    else:
        print("CONCLUSAO: UMA OU MAIS SUITES APRESENTARAM FALHAS.")
        print("=" * 80 + "\n")
        return False


if __name__ == "__main__":
    success = run_consolidated_e2e_quality_suite()
    sys.exit(0 if success else 1)
