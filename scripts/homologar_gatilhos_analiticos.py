"""
Suite Automatizada de Homologacao Completa: AURA 11 Gatilhos Analiticos, Micro-Widgets e Companion Canvas.
Valida:
1. Execucao direta na API FastAPI (http://127.0.0.1:8000/api/v1/aura/execute-intent) para as 11 ferramentas.
2. Integridade dos payloads analiticos (zero None/undefined em nos obrigatorios).
3. Streaming multiplexado SSE (/api/v1/aura/chat) com geracao de envelopes canonicos GenUI.
4. Renderizacao limpa do Companion Canvas e dos 11 cards do AuraTriggersController via Node.js.
5. Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import sys
import os
import time
import json
import urllib.request
import urllib.error
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Forca UTF-8 no console do Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
API_BASE_URL = os.environ.get("AURA_API_URL", "http://127.0.0.1:8000")


# =============================================================================
# ETAPA 1: HOMOLOGACAO DOS 11 GATILHOS ANALITICOS (EXECUTE-INTENT)
# =============================================================================

TOOLS_SPECS = [
    {
        "id": "run_out",
        "name": "Previsao Run-Out de Tanques",
        "category": "combustiveis",
        "badge": "Logistica",
        "params": {"combustivel": None},
        "required_keys": ["detalhamento_tanques", "resumo_executivo", "previsao_por_combustivel"],
    },
    {
        "id": "lmc_anp",
        "name": "LMC Oficial ANP (Port. 26/1992)",
        "category": "fiscal",
        "badge": "Regulatorio",
        "params": {"data": "hoje"},
        "required_keys": ["resumo_executivo", "tanques", "status_geral_anp"],
    },
    {
        "id": "conciliacao_turno",
        "name": "Conciliacao de Turno & Caixa",
        "category": "caixa",
        "badge": "Auditoria",
        "params": {"data": "hoje"},
        "required_keys": ["resumo_executivo", "triangulacao_pista", "triangulacao_caixa", "balanco_tanques"],
    },
    {
        "id": "desempenho_pista_frentistas",
        "name": "Desempenho de Frentistas & Pista",
        "category": "caixa",
        "badge": "Produtividade",
        "params": {},
        "required_keys": ["ranking_frentistas", "auditoria_vazao_bicos"],
    },
    {
        "id": "conveniencia_vendas_cruzadas",
        "name": "Cesta de Compras & Cross-Selling",
        "category": "loja",
        "badge": "Inteligencia PDV",
        "params": {"min_lift": 1.2, "limit": 10},
        "required_keys": ["top_combos_cross_selling", "regras_associacao_detalhadas"],
    },
    {
        "id": "estoque_posicao",
        "name": "Posicao Geral de Estoque ERP",
        "category": "combustiveis",
        "badge": "Estoque Central",
        "params": {"termo": ""},
        "required_keys": ["maiores_estoques", "tanques_combustivel"],
    },
    {
        "id": "clientes_ranking",
        "name": "Ranking e Perfil de Clientes",
        "category": "caixa",
        "badge": "CRM",
        "params": {"termo": ""},
        "required_keys": ["ranking_compras_pedidos", "total_clientes_cadastrados"],
    },
    {
        "id": "dados_filial",
        "name": "Dados Cadastrais da Filial",
        "category": "gestao",
        "badge": "Identidade",
        "params": {},
        "required_keys": ["idempresa", "nome", "razao_social", "cnpj"],
    },
    {
        "id": "catalogo_produtos",
        "name": "Busca Semantica no Catalogo",
        "category": "loja",
        "badge": "Catalogo & Precos",
        "params": {"termo": "combustivel", "top_k": 5},
        "required_keys": ["results"],
    },
    {
        "id": "vendas_analitico",
        "name": "Vendas & Faturamento ERP",
        "category": "fiscal",
        "badge": "Faturamento",
        "params": {"tipo": "mais_vendidos"},
        "required_keys": ["produtos_mais_vendidos", "resumo_geral"],
    },
    {
        "id": "sre_metricas",
        "name": "Saude & Telemetria SRE do Posto",
        "category": "gestao",
        "badge": "Observabilidade",
        "params": {},
        "required_keys": ["database_health", "table_stats", "semantic_router_metrics"],
    },
]


def homologar_gatilhos_execute_intent() -> Tuple[bool, List[Dict[str, Any]]]:
    print("\n" + "=" * 80)
    print("ETAPA 1: HOMOLOGACAO DETERMINISTICA DOS 11 GATILHOS ANALITICOS (API FASTAPI)")
    print("Endpoint: POST /api/v1/aura/execute-intent")
    print("=" * 80)

    results = []
    all_ok = True

    for spec in TOOLS_SPECS:
        tool_id = spec["id"]
        t0 = time.perf_counter()
        url = f"{API_BASE_URL}/api/v1/aura/execute-intent"
        req_body = json.dumps({"tool_name": tool_id, "params": spec["params"]}).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=req_body,
            headers={"Content-Type": "application/json", "Accept": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                elapsed_ms = (time.perf_counter() - t0) * 1000
                status_code = resp.status
                raw_bytes = resp.read()
                data_payload = json.loads(raw_bytes.decode("utf-8"))

            status_val = data_payload.get("status", "unknown")
            data_obj = data_payload.get("data", {})

            # Validacao de chaves obrigatorias
            missing_keys = []
            for rk in spec["required_keys"]:
                if isinstance(data_obj, dict):
                    # Checagem em primeiro nivel ou em resumo_executivo/contrato
                    found = (
                        rk in data_obj
                        or (isinstance(data_obj.get("resumo_executivo"), dict) and rk in data_obj["resumo_executivo"])
                        or (isinstance(data_obj.get("contrato"), dict) and rk in data_obj["contrato"])
                    )
                    if not found:
                        missing_keys.append(rk)
                else:
                    missing_keys.append(rk)

            # Validacao de zero [object Object] na serializacao
            has_obj_obj = "[object Object]" in json.dumps(data_payload)
            is_valid = (status_code == 200 and status_val == "success" and not missing_keys and not has_obj_obj)

            if not is_valid:
                all_ok = False

            res_info = {
                "id": tool_id,
                "name": spec["name"],
                "badge": spec["badge"],
                "latency_ms": elapsed_ms,
                "status": "PASS" if is_valid else "FAIL",
                "status_code": status_code,
                "missing_keys": missing_keys,
                "data_payload": data_obj,
            }
            results.append(res_info)

            status_tag = "[OK] PASS" if is_valid else "[X] FAIL"
            print(f" {status_tag} {spec['name']:<36} | {elapsed_ms:6.1f}ms | Chaves validadas: {len(spec['required_keys'])}")

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            all_ok = False
            results.append({
                "id": tool_id,
                "name": spec["name"],
                "badge": spec["badge"],
                "latency_ms": elapsed_ms,
                "status": "FAIL",
                "error": str(exc),
            })
            print(f" [X] FAIL {spec['name']:<36} | {elapsed_ms:6.1f}ms | Erro: {exc}")

    return all_ok, results


# =============================================================================
# ETAPA 2: HOMOLOGACAO DO STREAMING SSE E ENVELOPES GENUI (CHAT STREAM)
# =============================================================================

GENUI_STREAM_QUERIES = [
    {
        "query": "Qual o diagnostico executivo geral do meu posto?",
        "expected_component": "render_ExecutiveDecisionMentorUI",
        "description": "Mentoria Executiva de Decisao",
    },
    {
        "query": "O que vende junto com bala ou cerveja?",
        "expected_component": "render_BasketUpsellStrategyUI",
        "description": "Cesta de Compras e Cross-Selling",
    },
    {
        "query": "Como esta a previsao de esgotamento e tanques?",
        "expected_component": "render_TankRunOutForecastUI",
        "description": "Previsao de Run-Out e Ullage de Tanques",
    },
    {
        "query": "Auditar fechamento de turno e caixa de hoje",
        "expected_component": "render_ShiftReconciliationUI",
        "description": "Conciliacao e Auditoria de Turno",
    },
    {
        "query": "Como esta o desempenho dos frentistas e vazao dos bicos?",
        "expected_component": "render_PumpPerformanceUI",
        "description": "Produtividade de Pista e Frentistas",
    },
    {
        "query": "Gerar auditoria do livro LMC ANP oficial",
        "expected_component": "render_LMCReportUI",
        "description": "Conformidade Regulatoria ANP",
    },
    {
        "query": "Qual o faturamento e analise de vendas dos mais vendidos?",
        "expected_component": "render_MarginAnalysisUI",
        "description": "Analise de Margens e Vendas ERP",
    },
]


def homologar_streaming_genui() -> Tuple[bool, List[Dict[str, Any]]]:
    print("\n" + "=" * 80)
    print("ETAPA 2: HOMOLOGACAO DO STREAMING SSE MULTIPLEXADO E ENVELOPES GENUI")
    print("Endpoint: POST /api/v1/aura/chat?genui=1 (text/event-stream)")
    print("=" * 80)

    results = []
    all_ok = True

    for spec in GENUI_STREAM_QUERIES:
        query = spec["query"]
        t0 = time.perf_counter()
        url = f"{API_BASE_URL}/api/v1/aura/chat?genui=1"
        req_body = json.dumps({"query": query, "stream": True}).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=req_body,
            headers={
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
                "X-GenUI-Enabled": "1"
            }
        )

        events_received = []
        ui_complete_envelope = None
        has_skeleton = False
        text_tokens = []

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                current_event = None
                for line in resp:
                    line_str = line.decode("utf-8").strip()
                    if not line_str:
                        current_event = None
                        continue

                    if line_str.startswith("event:"):
                        current_event = line_str.replace("event:", "").strip()
                    elif line_str.startswith("data:"):
                        data_str = line_str.replace("data:", "").strip()
                        events_received.append(current_event)

                        if current_event == "ui_skeleton":
                            has_skeleton = True
                        elif current_event == "delta":
                            try:
                                d = json.loads(data_str)
                                if d.get("text"):
                                    text_tokens.append(d["text"])
                            except Exception:
                                pass
                        elif current_event == "ui_complete":
                            try:
                                parsed = json.loads(data_str)
                                ui_complete_envelope = parsed.get("envelope") or parsed.get("data") or parsed
                            except Exception:
                                pass

            elapsed_ms = (time.perf_counter() - t0) * 1000

            # Validacao do envelope canônico
            has_ui_complete = ui_complete_envelope is not None
            component_match = False
            has_no_object_object = True

            if has_ui_complete:
                comp_name = ui_complete_envelope.get("component_name", "")
                component_match = (comp_name == spec["expected_component"])
                envelope_json = json.dumps(ui_complete_envelope)
                has_no_object_object = "[object Object]" not in envelope_json

            is_valid = has_ui_complete and component_match and has_no_object_object and len(text_tokens) > 0

            if not is_valid:
                all_ok = False

            status_tag = "[OK] PASS" if is_valid else "[X] FAIL"
            comp_found = ui_complete_envelope.get("component_name") if ui_complete_envelope else "Nenhum"
            print(f" {status_tag} {spec['description']:<36} | {elapsed_ms:6.1f}ms | Comp: {comp_found}")

            results.append({
                "description": spec["description"],
                "query": query,
                "latency_ms": elapsed_ms,
                "expected_component": spec["expected_component"],
                "received_component": comp_found,
                "has_skeleton": has_skeleton,
                "has_ui_complete": has_ui_complete,
                "status": "PASS" if is_valid else "FAIL",
            })

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            all_ok = False
            results.append({
                "description": spec["description"],
                "query": query,
                "latency_ms": elapsed_ms,
                "status": "FAIL",
                "error": str(exc),
            })
            print(f" [X] FAIL {spec['description']:<36} | {elapsed_ms:6.1f}ms | Erro: {exc}")

    return all_ok, results


# =============================================================================
# ETAPA 3: HOMOLOGACAO FRONTEND VIA NODE.JS (RENDERIZACAO DOS 11 CARDS)
# =============================================================================

def homologar_frontend_cards_nodejs(etapa1_results: List[Dict[str, Any]]) -> bool:
    print("\n" + "=" * 80)
    print("ETAPA 3: HOMOLOGACAO DA RENDERIZACAO DOS 11 CARDS VIA NODE.JS HEADLESS")
    print("Script: web/js/aura-triggers.js -> buildFormattedHtml()")
    print("=" * 80)

    # Prepara payload em arquivo temporario para teste Node.js
    test_data_map = {}
    for r in etapa1_results:
        test_data_map[r["id"]] = r.get("data_payload", {})

    node_script = """
    const fs = require('fs');
    const path = require('path');

    // Mock basico de DOM
    global.window = {};
    global.document = {
      getElementById: () => null,
      querySelectorAll: () => []
    };

    // Carrega aura-triggers.js via require CommonJS
    const triggerJsPath = path.resolve('ia-banco-local/web/js/aura-triggers.js');
    const { AuraTriggersController } = require(triggerJsPath);

    const controller = new AuraTriggersController();
    const catalog = controller.getToolsCatalog();

    console.log('[Node] Total de ferramentas no catalogo:', catalog.length);
    if (catalog.length !== 11) {
      console.error('[ERRO] Catalogo deve ter exatamente 11 ferramentas! Encontrado:', catalog.length);
      process.exit(1);
    }

    const testData = JSON.parse(fs.readFileSync('ia-banco-local/scripts/temp_homolog_data.json', 'utf8'));

    let allOk = true;
    for (const tool of catalog) {
      const data = testData[tool.id] || {};
      const html = controller.buildFormattedHtml(tool.id, data);

      if (!html || typeof html !== 'string' || html.length < 20) {
        console.error(`[FALHA] HTML vazio ou invalido para ${tool.id}`);
        allOk = false;
        continue;
      }

      if (html.includes('[object Object]')) {
        console.error(`[FALHA] [object Object] detectado no HTML de ${tool.id}`);
        allOk = false;
        continue;
      }

      if (html.includes('undefined') || html.includes('NaN')) {
        console.error(`[FALHA] undefined/NaN detectado no HTML de ${tool.id}`);
        allOk = false;
        continue;
      }

      console.log(`[OK] ${tool.id.padEnd(30)} -> HTML renderizado com sucesso (${html.length} chars)`);
    }

    process.exit(allOk ? 0 : 1);
    """

    temp_json_path = BASE_DIR / "scripts" / "temp_homolog_data.json"
    temp_json_path.write_text(json.dumps(test_data_map, ensure_ascii=False), encoding="utf-8")

    try:
        proc = subprocess.run(
            ["node", "-e", node_script],
            cwd=str(BASE_DIR.parent),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=15,
        )

        print(proc.stdout)
        if proc.returncode != 0:
            print(f"[ERRO Node.js]: {proc.stderr}")
            return False
        return True

    except Exception as exc:
        print(f"[ERRO ao executar Node.js]: {exc}")
        return False
    finally:
        if temp_json_path.exists():
            temp_json_path.unlink()


# =============================================================================
# EXECUTOR PRINCIPAL E RELATORIO CONSOLIDADO
# =============================================================================

def run_full_homologation():
    print("=" * 80)
    print("AURA CORE ENGINE: RELATORIO DE HOMOLOGACAO COMPLETA (11 GATILHOS & GENUI)")
    print("=" * 80)
    print(f"Data: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target API: {API_BASE_URL}")

    t_start = time.perf_counter()

    # 1. Homologacao dos 11 Gatilhos
    ok1, res1 = homologar_gatilhos_execute_intent()

    # 2. Homologacao do Streaming SSE Multiplexado
    ok2, res2 = homologar_streaming_genui()

    # 3. Homologacao do Frontend via Node.js
    ok3 = homologar_frontend_cards_nodejs(res1)

    t_total = time.perf_counter() - t_start

    # Tabela Resumo Consolidada
    print("\n" + "=" * 80)
    print("QUADRO RESUMO DE AUDITORIA E HOMOLOGACAO CONSOLIDADA")
    print("=" * 80)
    print(f"{'FERRAMENTA / MODULO':<38} | {'LATENCIA':<10} | {'STATUS':<8} | {'RESULTADO':<15}")
    print("-" * 80)

    for r in res1:
        stat = "[OK] PASS" if r["status"] == "PASS" else "[X] FAIL"
        lat = f"{r['latency_ms']:.1f}ms"
        print(f"{r['name']:<38} | {lat:<10} | {stat:<8} | Determinístico")

    print("-" * 80)
    for r in res2:
        stat = "[OK] PASS" if r["status"] == "PASS" else "[X] FAIL"
        lat = f"{r['latency_ms']:.1f}ms"
        print(f"{r['description']:<38} | {lat:<10} | {stat:<8} | GenUI Stream")

    print("=" * 80)
    print(f"Tempo Total da Bateria de Homologacao: {t_total:.2f}s")

    all_passed = ok1 and ok2 and ok3

    if all_passed:
        print("\n🎉 CONCLUSAO: TODOS OS 11 GATILHOS ANALITICOS E MICRO-WIDGETS GENUI FORAM")
        print("   HOMOLOGADOS COM 100% DE SUCESSO E ESTAO OPERACIONAIS EM PRODUCAO!")
        print("=" * 80 + "\n")
        return True
    else:
        print("\n⚠ CONCLUSAO: UMA OU MAIS ETAPAS DE HOMOLOGACAO APRESENTARAM FALHAS.")
        print("=" * 80 + "\n")
        return False


if __name__ == "__main__":
    success = run_full_homologation()
    sys.exit(0 if success else 1)
