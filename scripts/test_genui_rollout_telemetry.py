"""
Suite de Testes Automatizada da Fase 9: Rollout Gradual, Feature Flags e Observabilidade SRE (F9-04)
Cobre de forma rapida e deterministica (< 15 segundos):
1. Precedencia de Feature Flags (Query Param ?genui=0/1, Header HTTP, Body e Runtime Global)
2. Endpoints Administrativos GET e POST /api/v1/aura/admin/feature-flags (Circuit Breaker a quente)
3. Comutacao a quente de contingencia e supressao de envelopes GenUI no streaming SSE
4. Coleta e consolidacao de telemetria SRE (TTFT, hidratacao, acoes aprovadas, rollbacks, seguranca)
5. Integracao de telemetria no gateway transacional (RBAC blocks e voucher approvals)
6. Verificacao do cliente frontend Zero-Bundler em Node.js (isEnabled, setEnabled, reportTelemetry)

Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import sys
import time
import json
import subprocess
from pathlib import Path

# Protecao estrita de encoding UTF-8 no Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from unittest.mock import MagicMock
import google.generativeai as genai
from fastapi.testclient import TestClient

from core.config import (
    ENABLE_GENUI,
    is_genui_enabled,
    set_genui_enabled,
    get_feature_flags,
    update_feature_flags,
    resolve_genui_flag,
)
from core.telemetry import AuraSRETelemetry
from core.aura_engine import (
    AuraEngine,
    AuraSessionMemory,
    AuraChunkType,
)
from core.aura_api import create_aura_app, set_aura_engine
from core.rag_engine import HybridRAGEngine
from core.schemas.idempotency import generate_action_id, generate_tool_call_id


class MockGeminiStream:
    """Simulador de stream de tokens para testes ultrarrapidos sem latencia de rede."""
    def __init__(self, texts):
        self.texts = texts

    def __aiter__(self):
        self._iter = iter(self.texts)
        return self

    async def __anext__(self):
        try:
            val = next(self._iter)
            mock_chunk = MagicMock()
            mock_chunk.text = val
            return mock_chunk
        except StopIteration:
            raise StopAsyncIteration


async def mock_gemini_generate_content_async(prompt, stream=True, **kwargs):
    return MockGeminiStream(["Autonomia estimada dos tanques sob controle no periodo."])


def fast_no_pgvector_conn(self, *args, **kwargs):
    raise ConnectionRefusedError("Modo de teste rapido local (pgvector offline)")


def run_all_rollout_telemetry_tests():
    # Instala mocks de alta performance para execucao direta em segundos
    from core.semantic_router import SemanticRouter
    SemanticRouter._conectar_pgvector = fast_no_pgvector_conn
    HybridRAGEngine._conectar_pgvector = fast_no_pgvector_conn
    genai.GenerativeModel.generate_content_async = mock_gemini_generate_content_async

    print("=" * 80)
    print("SUITE DE TESTES: ROLLOUT GRADUAL, FEATURE FLAGS & SRE (FASE 9: F9-04)")
    print("=" * 80)
    t_start = time.perf_counter()

    # 1. TESTE DE PRECEDENCIA DE FEATURE FLAGS E FUNCOES DE CONFIG
    print("\n1. Testando Resolucao de Precedencia da Feature Flag ENABLE_GENUI...")
    set_genui_enabled(True)
    assert is_genui_enabled() is True, "ENABLE_GENUI deveria iniciar como True"

    # Precedencia 1: Query param sobrescreve tudo
    assert resolve_genui_flag(query_param="0", header_val="1", body_val=True) is False
    assert resolve_genui_flag(query_param="1", header_val="0", body_val=False) is True
    assert resolve_genui_flag(query_param=False, header_val="1") is False

    # Precedencia 2: Header HTTP sobrescreve body e global
    assert resolve_genui_flag(query_param=None, header_val="0", body_val=True) is False
    assert resolve_genui_flag(query_param=None, header_val="1", body_val=False) is True

    # Precedencia 3: Body do request
    assert resolve_genui_flag(query_param=None, header_val=None, body_val=False) is False
    assert resolve_genui_flag(query_param=None, header_val=None, body_val=True) is True

    # Precedencia 4: Global runtime
    set_genui_enabled(False)
    assert resolve_genui_flag(query_param=None, header_val=None, body_val=None) is False
    set_genui_enabled(True)
    assert resolve_genui_flag(query_param=None, header_val=None, body_val=None) is True
    print("   [OK] Precedencia de flags (Query > Header > Body > Global) 100% validada.")

    # 2. TESTE DOS ENDPOINTS ADMINISTRATIVOS (CIRCUIT BREAKER - F9-03)
    print("\n2. Testando Endpoints Administrativos GET/POST /api/v1/aura/admin/feature-flags...")
    mem = AuraSessionMemory(db_path=":memory:")
    engine = AuraEngine(session_memory=mem)
    telemetry = AuraSRETelemetry(session_memory=mem)
    telemetry.reset()
    engine._telemetry = telemetry
    app = create_aura_app(engine)
    client = TestClient(app)

    # Inspecao inicial
    resp_get = client.get("/api/v1/aura/admin/feature-flags")
    assert resp_get.status_code == 200, f"Status invalido: {resp_get.status_code}"
    data_get = resp_get.json()
    assert data_get["status"] == "ok"
    assert data_get["ENABLE_GENUI"] is True

    # Alteracao a quente: Desativar GenUI (Circuit Breaker)
    resp_post = client.post(
        "/api/v1/aura/admin/feature-flags",
        json={"ENABLE_GENUI": False}
    )
    assert resp_post.status_code == 200
    data_post = resp_post.json()
    assert data_post["status"] == "updated"
    assert data_post["ENABLE_GENUI"] is False
    assert is_genui_enabled() is False

    # Confirmacao via GET
    resp_get2 = client.get("/api/v1/aura/admin/feature-flags")
    assert resp_get2.json()["ENABLE_GENUI"] is False

    # Reativacao via update_feature_flags
    resp_post2 = client.post(
        "/api/v1/aura/admin/feature-flags",
        json={"flags": {"ENABLE_GENUI": True}}
    )
    assert resp_post2.status_code == 200
    assert resp_post2.json()["ENABLE_GENUI"] is True
    assert is_genui_enabled() is True
    print("   [OK] Endpoints administrativos de Feature Flags e Circuit Breaker 100% validados.")

    # 3. TESTE DE COMUTACAO A QUENTE E SUPRESSAO DE ENVELOPES NO STREAMING SSE
    print("\n3. Testando Streaming SSE com Feature Flag e Contingencia a Quente...")
    # 3.1 Com GenUI Ativo: deve emitir ui_skeleton e ui_complete
    set_genui_enabled(True)
    resp_stream_on = client.post(
        "/api/v1/aura/chat",
        json={"query": "Como estao os tanques hoje?", "stream": True}
    )
    assert resp_stream_on.status_code == 200
    body_on = resp_stream_on.text
    assert "event: ui_skeleton" in body_on, "Deveria conter ui_skeleton quando GenUI ativo"
    assert "event: ui_complete" in body_on, "Deveria conter ui_complete quando GenUI ativo"
    assert resp_stream_on.headers.get("x-genui-enabled") == "1"

    # 3.2 Override via query param ?genui=0 no request: deve suprimir ui_skeleton e ui_complete
    resp_stream_override_off = client.post(
        "/api/v1/aura/chat?genui=0",
        json={"query": "Como estao os tanques hoje?", "stream": True}
    )
    assert resp_stream_override_off.status_code == 200
    body_off = resp_stream_override_off.text
    assert "event: ui_skeleton" not in body_off, "Nao deve conter ui_skeleton quando desativado via query param"
    assert "event: ui_complete" not in body_off, "Nao deve conter ui_complete quando desativado via query param"
    assert "event: tool_result" in body_off, "Deve manter dados brutos da ferramenta para DecisionCards legados"
    assert resp_stream_override_off.headers.get("x-genui-enabled") == "0"

    # 3.3 Alias de streaming /api/v1/aura/chat/stream com header X-GenUI-Enabled: 0
    resp_alias_off = client.post(
        "/api/v1/aura/chat/stream",
        headers={"X-GenUI-Enabled": "0"},
        json={"query": "Como estao os tanques hoje?", "stream": True}
    )
    assert resp_alias_off.status_code == 200
    body_alias = resp_alias_off.text
    assert "event: ui_skeleton" not in body_alias
    assert "event: ui_complete" not in body_alias

    # 3.4 Comutacao a quente (Circuit Breaker global): desativar globalmente e testar chat sem override
    set_genui_enabled(False)
    resp_stream_global_off = client.post(
        "/api/v1/aura/chat",
        json={"query": "Como estao os tanques hoje?", "stream": True}
    )
    assert resp_stream_global_off.status_code == 200
    body_glob_off = resp_stream_global_off.text
    assert "event: ui_skeleton" not in body_glob_off
    assert "event: ui_complete" not in body_glob_off
    assert resp_stream_global_off.headers.get("x-genui-enabled") == "0"

    # 3.5 Sobrescrita com query param ?genui=1 mesmo com global desativado
    resp_stream_override_on = client.post(
        "/api/v1/aura/chat?genui=1",
        json={"query": "Como estao os tanques hoje?", "stream": True}
    )
    assert resp_stream_override_on.status_code == 200
    body_ov_on = resp_stream_override_on.text
    assert "event: ui_skeleton" in body_ov_on
    assert "event: ui_complete" in body_ov_on
    assert resp_stream_override_on.headers.get("x-genui-enabled") == "1"

    # Restaura flag global para True
    set_genui_enabled(True)
    print("   [OK] Comutacao a quente e supressao seletiva de envelopes SSE 100% validadas.")

    # 4. TESTE DE COLETA E CONSOLIDACAO DE TELEMETRIA SRE (F9-02)
    print("\n4. Testando Coleta e Consolidacao de Telemetria SRE (Metrics & Report)...")
    telemetry.reset()

    # Inspecao inicial das metricas
    resp_metrics1 = client.get("/api/v1/aura/telemetry/metrics")
    assert resp_metrics1.status_code == 200
    m_data1 = resp_metrics1.json()
    assert m_data1["status"] == "ok"
    assert m_data1["total_actions_requested"] == 0
    assert m_data1["total_actions_approved"] == 0
    assert m_data1["total_actions_rolled_back"] == 0
    assert m_data1["security_blocks"] == 0

    # Reporte de hidratacao pelo cliente
    resp_rep1 = client.post(
        "/api/v1/aura/telemetry/report",
        json={
            "metric_type": "hydration",
            "hydration_ms": 38.5,
            "session_id": "sess_test_1",
            "tool_call_id": "call_test_1"
        }
    )
    assert resp_rep1.status_code == 200
    assert resp_rep1.json()["status"] == "ok"

    # Reporte de rollback pelo cliente
    resp_rep2 = client.post(
        "/api/v1/aura/telemetry/report",
        json={
            "is_rollback": True,
            "action_status": "rolled_back",
            "action_id": "act_roll_1",
            "reason": "Timeout de rede no posto"
        }
    )
    assert resp_rep2.status_code == 200

    # Inspecao das metricas consolidadas apos reportes
    resp_metrics2 = client.get("/api/v1/aura/telemetry/metrics")
    assert resp_metrics2.status_code == 200
    m_data2 = resp_metrics2.json()
    assert m_data2["hydration_ms"]["count"] >= 1
    assert m_data2["hydration_ms"]["avg"] == 38.5
    assert m_data2["total_actions_rolled_back"] == 1
    print("   [OK] Endpoints /telemetry/metrics e /telemetry/report 100% homologados.")

    # 5. TESTE DE INTEGRACAO TRANSACIONAL COM SLIs SRE (RBAC BLOCKS E APROVACOES)
    print("\n5. Testando Integracao de Telemetria no Gateway Transacional...")
    # 5.1 Bloqueio de Seguranca RBAC: operador frentista tentando mutacao de alto impacto
    aid_block = generate_action_id()
    tid_block = generate_tool_call_id()
    resp_act_block = client.post(
        "/api/v1/aura/actions/execute",
        json={
            "session_id": "sess_sre_1",
            "tool_call_id": tid_block,
            "action_id": aid_block,
            "action_name": "pedido_combustivel",
            "action_type": "mutation",
            "operator_id": "frentista_01",
            "operator_role": "frentista",
            "payload": {"litros": 15000}
        }
    )
    assert resp_act_block.status_code == 403, "Deveria bloquear com HTTP 403 Forbidden"

    # 5.2 Acao autorizada: operador gerente executando a mesma acao
    aid_ok = generate_action_id()
    tid_ok = generate_tool_call_id()
    resp_act_ok = client.post(
        "/api/v1/aura/actions/execute",
        json={
            "session_id": "sess_sre_1",
            "tool_call_id": tid_ok,
            "action_id": aid_ok,
            "action_name": "pedido_combustivel",
            "action_type": "mutation",
            "operator_id": "gerente_01",
            "operator_role": "gerente",
            "payload": {"litros": 15000}
        }
    )
    assert resp_act_ok.status_code == 200, "Deveria aprovar com HTTP 200 OK"
    voucher = resp_act_ok.json()
    assert voucher["status"] == "APPROVED"
    assert voucher["action_id"] == aid_ok

    # 5.3 Validacao dos contadores consolidados na telemetria
    resp_metrics3 = client.get("/api/v1/aura/telemetry/metrics")
    m_data3 = resp_metrics3.json()
    assert m_data3["total_actions_requested"] >= 2, "Deveria ter registrado ao menos 2 acoes solicitadas"
    assert m_data3["total_actions_approved"] >= 1, "Deveria ter registrado 1 acao aprovada"
    assert m_data3["security_blocks"] >= 1, "Deveria ter registrado 1 bloqueio de seguranca"
    assert m_data3["action_success_rate_pct"] > 0, "Taxa de sucesso deve ser positiva"
    print("   [OK] SLIs de acoes solicitadas, bloqueios de seguranca e aprovacoes validados.")

    # 6. TESTE DE CICLO DE VIDA DO CLIENTE FRONTEND VIA NODE.JS HEADLESS
    print("\n6. Testando Modulos do Frontend Zero-Bundler via Node.js Headless...")
    js_code = """
    const genui = require('./web/js/aura-genui');
    const apiModule = require('./web/js/aura-api');
    const assert = require('assert');

    // 1. Validacao de Feature Flag no AuraGenUI
    assert.strictEqual(typeof genui.AuraGenUI.isEnabled, 'function', 'isEnabled deve ser funcao');
    assert.strictEqual(typeof genui.AuraGenUI.setEnabled, 'function', 'setEnabled deve ser funcao');

    assert.strictEqual(genui.AuraGenUI.isEnabled(), true, 'Deveria iniciar como true');
    genui.AuraGenUI.setEnabled(false);
    assert.strictEqual(genui.AuraGenUI.isEnabled(), false, 'Deveria refletir false');
    genui.AuraGenUI.setEnabled(true);
    assert.strictEqual(genui.AuraGenUI.isEnabled(), true, 'Deveria refletir true');

    // 2. Validacao dos novos metodos no AuraApiClient
    const client = new apiModule.AuraApiClient({ baseUrl: 'http://127.0.0.1:8000' });
    assert.strictEqual(typeof client.reportTelemetry, 'function', 'reportTelemetry deve ser funcao');
    assert.strictEqual(typeof client.getTelemetryMetrics, 'function', 'getTelemetryMetrics deve ser funcao');
    assert.strictEqual(typeof client.getFeatureFlags, 'function', 'getFeatureFlags deve ser funcao');
    assert.strictEqual(typeof client.updateFeatureFlags, 'function', 'updateFeatureFlags deve ser funcao');

    console.log('NODE_GENUI_ROLLOUT_TELEMETRY_OK');
    """

    res = subprocess.run(
        ["node", "-e", js_code],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    assert res.returncode == 0, f"Falha no Node.js: {res.stderr}"
    assert "NODE_GENUI_ROLLOUT_TELEMETRY_OK" in res.stdout
    print("   [OK] Modulos de feature flags e telemetria no frontend validados via Node.js.")

    elapsed = time.perf_counter() - t_start
    print("\n" + "=" * 80)
    print(f"SUITE DA FASE 9 CONCLUIDA COM 100% DE SUCESSO EM {elapsed:.3f}s (LIMITE: < 15.0s)!")
    print("=" * 80)
    return True


if __name__ == "__main__":
    run_all_rollout_telemetry_tests()
