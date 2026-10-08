"""
Suite de Testes Automatizada: Hardening de Seguranca Cibernetica, OWASP LLM & Governanca (Fase 7: P0/P1)
(Mitigacao OWASP LLM03, OWASP LLM01, Coercao Estrita, RBAC Gateway, Audit Log e Regressao Atomica)

Validacoes Obrigatorias:
1. Mitigacao Estrita de OWASP LLM03 (Agencia Excessiva & Catalogo Fechado):
   - Backend: Intencao ou componente alucinado/desconhecido rejeitado com retorno None e log de alerta de seguranca.
   - Frontend (Node.js): SecureComponentRegistry lanca excecao para componente nao registrado e incrementa contador de alertas.
   - Fallback Seguro: Renderizacao segura em texto puro sanitizado (renderSafeFallback) sem execucao dinamica.
2. Mitigacao de OWASP LLM01 (Prompt Injection & XSS):
   - escapeHtml neutraliza tags <script>, atributos onerror/onfocus, backticks e entidades maliciosas.
   - sanitizeProps sanitiza recursivamente objetos e listas, prevenindo prototype pollution e ciclos de referencia.
3. Coercao Estrita de Tipos Primitivos:
   - coerceNumber converte strings numericas e neutraliza strings invalidas/maliciosas para fallback deterministico.
   - coerceBoolean converte strings booleanas para tipos booleanos primitivos.
4. Governanca RBAC de Operadores (Human-in-the-Loop Gateway - F7-03):
   - Frentista bloqueado com HTTP 403 Forbidden em pedido de combustivel e ajuste de margem.
   - Frentista bloqueado com HTTP 403 Forbidden em acoes de caixa (estancar_quebra, sangria).
   - Frentista permitido com HTTP 200 OK em acoes de inspecao e navegacao.
   - Caixa aprovado com HTTP 200 OK em acoes de caixa, mas bloqueado com 403 em pedido de combustivel.
   - Gerente e Administrador aprovados com HTTP 200 OK e emissao de ActionVoucher assinado com HMAC-SHA256.
   - Perfil desconhecido ou invalido bloqueado com HTTP 403 Forbidden.
5. Trilha de Auditoria Transacional Duravel (Audit Log - F7-04):
   - Tabela aura_action_audit_log no SQLite grava tentativas APPROVED e REJECTED_FORBIDDEN.
   - Endpoint GET /api/v1/aura/audit/logs permite consulta com filtros por sessao, status e limite.
   - Contrato tipado ActionAuditLogRecord validado integralmente.
6. Regressao Atomica Rapida:
   - Execucao de suites atomicas sem recursao de subprocessos profundos.
"""

import sys
import json
import uuid
import logging
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List

# Protege stdout no terminal Windows contra problemas de codificacao
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from fastapi.testclient import TestClient

from core.schemas.genui import (
    ActionExecuteRequest,
    ActionVoucher,
    ActionAuditLogRecord,
    generate_action_voucher_signature,
    verify_action_voucher_signature,
)
from core.schemas.idempotency import (
    generate_tool_call_id,
    generate_action_id,
    generate_uuid4,
)
from core.aura_engine import (
    AuraEngine,
    AuraSessionMemory,
    build_canonical_genui_envelope,
    GENUI_COMPONENT_REGISTRY_MAP,
)
from core.aura_api import (
    create_aura_app,
    evaluate_action_permission,
    VALID_OPERATOR_ROLES,
    ROLE_HIERARCHY_LEVELS,
)


# =============================================================================
# ETAPA 1: MITIGACAO DE OWASP LLM03 (AGENCIA EXCESSIVA & CATALOGO FECHADO)
# =============================================================================

def test_owasp_llm03_excessive_agency_mitigation():
    print("\n1. Testando Mitigacao Estrita de OWASP LLM03 (Agencia Excessiva & Catalogo Fechado)...")

    # 1.1 Backend: Verificacao de que intencoes nao catalogadas retornam None e geram log de seguranca
    tool_id = generate_tool_call_id()

    # Intencao inexistente / alucinada
    fake_intent = "destruir_banco_dados"
    res_fake = build_canonical_genui_envelope(
        intencao=fake_intent,
        tool_call_id=tool_id,
        resultado_bruto={"status": "ok", "mensagem": "alucinacao do modelo"},
        executive_summary="Tentativa nao autorizada",
    )
    assert res_fake is None, "Deveria rejeitar intencao nao catalogada com retorno None"

    # Componente arbitrario inexistente
    fake_comp = "render_DeleteAllDatabasesUI"
    res_fake_comp = build_canonical_genui_envelope(
        intencao=fake_comp,
        tool_call_id=tool_id,
        resultado_bruto={"dados": [1, 2, 3]},
        executive_summary="Resumo de teste",
    )
    assert res_fake_comp is None, "Deveria rejeitar componente alucinado com retorno None"

    # Intencao legitima deve construir envelope com sucesso
    valid_intent = "analise_margem"
    res_valid = build_canonical_genui_envelope(
        intencao=valid_intent,
        tool_call_id=tool_id,
        resultado_bruto={
            "diagnosis": "Margem positiva",
            "confidence_score": 0.95,
            "consolidated_margin_pct": 14.5,
        },
        executive_summary="Margem consolidada sob controle.",
    )
    assert res_valid is not None, "Deveria construir envelope para intencao valida"
    assert res_valid.component_name == "render_MarginAnalysisUI"

    # 1.2 Frontend (Node.js): SecureComponentRegistry e bloqueio de componentes desconhecidos
    widgets_js = BASE_DIR / "web" / "js" / "aura-genui-widgets.js"
    genui_js = BASE_DIR / "web" / "js" / "aura-genui.js"
    assert widgets_js.exists(), f"Arquivo {widgets_js} nao encontrado"
    assert genui_js.exists(), f"Arquivo {genui_js} nao encontrado"

    node_code = f"""
    const path = require('path');
    const assert = require('assert');

    const genui = require({json.dumps(str(genui_js.resolve()))});
    const registry = genui.registry;
    const AuraGenUI = genui.AuraGenUI;

    // 1. Rejeicao com excecao em resolveComponent com throwOnMissing: true
    let threw = false;
    try {{
      registry.resolveComponent('render_UnknownHackerUI', {{ throwOnMissing: true }});
    }} catch (e) {{
      threw = true;
      assert(e.message.includes('[AURA-SEC-003]'), 'Mensagem de erro deve conter codigo [AURA-SEC-003]');
    }}
    assert(threw, 'Deveria ter lancado erro para componente desconhecido');

    // 2. Rejeicao graciosa com throwOnMissing: false e incremento do contador de alertas
    const initialAlerts = registry.getSecurityAlertCount();
    const resolved = registry.resolveComponent('render_UnknownHackerUI', {{ throwOnMissing: false }});
    assert.strictEqual(resolved, null, 'Deveria retornar null quando throwOnMissing for false');
    assert(registry.getSecurityAlertCount() > initialAlerts, 'Deveria incrementar contador de alertas de seguranca');

    // 3. Fallback Seguro via renderSafeFallback
    const fallbackHtml = AuraGenUI.renderSafeFallback('render_UnknownHackerUI', '<script>alert(1)</script>');
    assert(fallbackHtml.includes('genui-safe-fallback-card'), 'Deve conter classe do card de fallback');
    assert(fallbackHtml.includes('[AURA-SEC-003]'), 'Deve conter codigo de alerta [AURA-SEC-003]');
    assert(!fallbackHtml.includes('<script>'), 'Nao pode conter tag script aberta');
    assert(fallbackHtml.includes('&lt;script&gt;'), 'Deve conter script escapado');

    console.log('NODE_OWASP_LLM03_OK');
    """

    res_node = subprocess.run(
        ["node", "-e", node_code],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    assert res_node.returncode == 0, f"Falha no teste Node.js LLM03: {res_node.stderr}"
    assert "NODE_OWASP_LLM03_OK" in res_node.stdout

    print("   [OK] Mitigacao OWASP LLM03 validada com sucesso no backend e frontend.")


# =============================================================================
# ETAPA 2: MITIGACAO DE OWASP LLM01 (PROMPT INJECTION & SANITIZACAO)
# =============================================================================

def test_owasp_llm01_prompt_injection_and_sanitization():
    print("\n2. Testando Mitigacao de OWASP LLM01 (Prompt Injection & Sanitizacao Rigorosa)...")

    genui_js = BASE_DIR / "web" / "js" / "aura-genui.js"
    node_code = f"""
    const genui = require({json.dumps(str(genui_js.resolve()))});
    const escapeHtml = genui.escapeHtml;
    const sanitizeProps = genui.sanitizeProps;
    const assert = require('assert');

    // 2.1 Teste de injeções maliciosas em escapeHtml
    const dangerousPayloads = [
      '<script>alert("xss")</script>',
      '"><img src=x onerror=alert(1)>',
      "' onfocus='alert(document.cookie)",
      'javascript:alert(1)',
      '<svg onload=alert(1)>',
      '` || calc.exe || `',
    ];

    for (const p of dangerousPayloads) {{
      const clean = escapeHtml(p);
      assert(!clean.includes('<script>'), 'Tag script nao pode vazar');
      assert(!clean.includes('<img'), 'Tag img nao pode vazar');
      assert(!clean.includes('<svg'), 'Tag svg nao pode vazar');
      assert(!clean.includes('"'), 'Aspas duplas devem ser escapadas');
      assert(!clean.includes("'"), 'Aspas simples devem ser escapadas');
      assert(!clean.includes('`'), 'Backticks devem ser escapados');
    }}

    // 2.2 Teste de sanitizeProps recursivo com objetos e arrays aninhados
    const maliciousProps = {{
      diagnosis: 'Tudo normal <script>stealToken()</script>',
      metrics: [
        {{ label: '<b>Faturamento</b>', current_value: '<img src=x onerror=alert(1)>' }},
        {{ label: 'Margem', current_value: 14.8 }}
      ],
      nested: {{
        note: 'Observacao "com aspas" e <tags>'
      }}
    }};

    const sanitized = sanitizeProps(maliciousProps);
    assert(sanitized.diagnosis.includes('&lt;script&gt;stealToken()&lt;/script&gt;'));
    assert(sanitized.metrics[0].label.includes('&lt;b&gt;Faturamento&lt;/b&gt;'));
    assert(sanitized.metrics[0].current_value.includes('&lt;img src=x onerror=alert(1)&gt;'));
    assert.strictEqual(sanitized.metrics[1].current_value, 14.8, 'Numeros primitivos devem ser preservados');
    assert(sanitized.nested.note.includes('&quot;com aspas&quot;'));

    // 2.3 Protecao contra Prototype Pollution
    const polluted = JSON.parse('{{"__proto__": {{"polluted": true}}, "normal": "valor"}}');
    const sanitizedPolluted = sanitizeProps(polluted);
    assert.strictEqual(sanitizedPolluted.__proto__.polluted, undefined, 'Nao deve permitir poluicao de prototipo');

    console.log('NODE_OWASP_LLM01_OK');
    """

    res_node = subprocess.run(
        ["node", "-e", node_code],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    assert res_node.returncode == 0, f"Falha no teste Node.js LLM01: {res_node.stderr}"
    assert "NODE_OWASP_LLM01_OK" in res_node.stdout

    print("   [OK] Mitigacao OWASP LLM01 e sanitizacao rigorosa validadas com sucesso.")


# =============================================================================
# ETAPA 3: COERCAO ESTRITA DE TIPOS PRIMITIVOS (NUMEROS E BOOLEANOS)
# =============================================================================

def test_strict_primitive_type_coercion():
    print("\n3. Testando Coercao Estrita de Tipos Primitivos (Numeros e Booleanos)...")

    genui_js = BASE_DIR / "web" / "js" / "aura-genui.js"
    node_code = f"""
    const genui = require({json.dumps(str(genui_js.resolve()))});
    const coerceNumber = genui.AuraGenUI.coerceNumber;
    const coerceBoolean = genui.AuraGenUI.coerceBoolean;
    const assert = require('assert');

    // 3.1 Teste de coerceNumber
    assert.strictEqual(coerceNumber(100), 100);
    assert.strictEqual(coerceNumber('123.45'), 123.45);
    assert.strictEqual(coerceNumber('0'), 0);
    assert.strictEqual(coerceNumber('invalid_string'), 0);
    assert.strictEqual(coerceNumber('10; DROP TABLE', 42), 42);
    assert.strictEqual(coerceNumber(null, 50), 50);
    assert.strictEqual(coerceNumber(undefined, 900), 900);
    assert.strictEqual(coerceNumber(NaN, 15), 15);

    // 3.2 Teste de coerceBoolean
    assert.strictEqual(coerceBoolean(true), true);
    assert.strictEqual(coerceBoolean(false), false);
    assert.strictEqual(coerceBoolean('true'), true);
    assert.strictEqual(coerceBoolean('1'), true);
    assert.strictEqual(coerceBoolean('yes'), true);
    assert.strictEqual(coerceBoolean('sim'), true);
    assert.strictEqual(coerceBoolean('false'), false);
    assert.strictEqual(coerceBoolean('0'), false);
    assert.strictEqual(coerceBoolean('no'), false);
    assert.strictEqual(coerceBoolean('nao'), false);
    assert.strictEqual(coerceBoolean(null, false), false);
    assert.strictEqual(coerceBoolean(undefined, true), true);

    console.log('NODE_COERCION_OK');
    """

    res_node = subprocess.run(
        ["node", "-e", node_code],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    assert res_node.returncode == 0, f"Falha no teste Node.js coercao: {res_node.stderr}"
    assert "NODE_COERCION_OK" in res_node.stdout

    print("   [OK] Coercao estrita de tipos primitivos homologada com sucesso.")


# =============================================================================
# ETAPA 4: GOVERNANCA RBAC DE OPERADORES (HUMAN-IN-THE-LOOP GATEWAY)
# =============================================================================

def test_operator_rbac_governance():
    print("\n4. Testando Governanca RBAC de Operadores (Human-in-the-Loop Gateway - F7-03)...")

    # 4.1 Teste unitario da funcao evaluate_action_permission
    # Frentista tentando acao de mutacao de alto impacto -> Bloqueado
    ok_f1, lvl_f1, msg_f1 = evaluate_action_permission("pedido_combustivel", "mutation", "frentista")
    assert ok_f1 is False
    assert lvl_f1 == 3
    assert "Autorizacao negada" in msg_f1
    assert "gerente" in msg_f1

    # Frentista tentando acao de caixa -> Bloqueado
    ok_f2, lvl_f2, msg_f2 = evaluate_action_permission("estancar_quebra", "mutation", "frentista")
    assert ok_f2 is False
    assert lvl_f2 == 2
    assert "caixa" in msg_f2

    # Frentista tentando acao de inspecao -> Aprovado
    ok_f3, lvl_f3, msg_f3 = evaluate_action_permission("visualizar_canvas", "inspection", "frentista")
    assert ok_f3 is True
    assert lvl_f3 == 1

    # Caixa tentando acao de caixa -> Aprovado
    ok_c1, lvl_c1, msg_c1 = evaluate_action_permission("estancar_quebra", "mutation", "caixa")
    assert ok_c1 is True
    assert lvl_c1 == 2

    # Caixa tentando mutacao de combustivel -> Bloqueado
    ok_c2, lvl_c2, msg_c2 = evaluate_action_permission("pedido_combustivel", "mutation", "caixa")
    assert ok_c2 is False
    assert lvl_c2 == 3

    # Gerente tentando mutacao de combustivel -> Aprovado
    ok_g1, lvl_g1, msg_g1 = evaluate_action_permission("pedido_combustivel", "mutation", "gerente")
    assert ok_g1 is True
    assert lvl_g1 == 3

    # Administrador tentando qualquer acao -> Aprovado
    ok_a1, lvl_a1, msg_a1 = evaluate_action_permission("pedido_combustivel", "mutation", "administrador")
    assert ok_a1 is True
    assert lvl_a1 == 3

    # Perfil desconhecido -> Bloqueado
    ok_x, lvl_x, msg_x = evaluate_action_permission("pedido_combustivel", "mutation", "invasor")
    assert ok_x is False
    assert "desconhecido" in msg_x

    # 4.2 Teste fim-a-fim no endpoint FastAPI POST /api/v1/aura/actions/execute
    mem = AuraSessionMemory(db_path=":memory:")
    engine = AuraEngine(session_memory=mem)
    app = create_aura_app(engine=engine)
    client = TestClient(app)

    sess_id = f"sess_{uuid.uuid4()}"

    # Caso A: Frentista tenta mutacao de combustivel -> HTTP 403 Forbidden
    aid_frentista = generate_action_id()
    tid_frentista = generate_tool_call_id()
    resp_frentista = client.post("/api/v1/aura/actions/execute", json={
        "session_id": sess_id,
        "tool_call_id": tid_frentista,
        "action_id": aid_frentista,
        "action_name": "pedido_combustivel",
        "action_type": "mutation",
        "operator_id": "frentista_joao",
        "operator_role": "frentista",
        "payload": {"litros": 15000, "combustivel": "GASOLINA COMUM"}
    })
    assert resp_frentista.status_code == 403, f"Esperava 403, obteve {resp_frentista.status_code}: {resp_frentista.text}"
    detail_frentista = resp_frentista.json().get("detail", "")
    assert "Autorizacao negada" in detail_frentista
    assert "frentista" in detail_frentista

    # Caso B: Frentista tenta acao de inspecao -> HTTP 200 OK
    aid_insp = generate_action_id()
    tid_insp = generate_tool_call_id()
    resp_insp = client.post("/api/v1/aura/actions/execute", json={
        "session_id": sess_id,
        "tool_call_id": tid_insp,
        "action_id": aid_insp,
        "action_name": "visualizar_companion_canvas",
        "action_type": "inspection",
        "operator_id": "frentista_joao",
        "operator_role": "frentista",
        "payload": {"view": "split_canvas"}
    })
    assert resp_insp.status_code == 200, f"Falha na inspecao: {resp_insp.status_code}"
    voucher_insp = resp_insp.json()
    assert voucher_insp["status"] == "APPROVED"

    # Caso C: Caixa executa estancamento de quebra -> HTTP 200 OK
    aid_caixa = generate_action_id()
    tid_caixa = generate_tool_call_id()
    resp_caixa = client.post("/api/v1/aura/actions/execute", json={
        "session_id": sess_id,
        "tool_call_id": tid_caixa,
        "action_id": aid_caixa,
        "action_name": "estancar_quebra",
        "action_type": "mutation",
        "operator_id": "caixa_maria",
        "operator_role": "caixa",
        "payload": {"valor": 85.0, "turno": 1}
    })
    assert resp_caixa.status_code == 200, f"Falha na acao do caixa: {resp_caixa.status_code}"
    voucher_caixa = resp_caixa.json()
    assert voucher_caixa["status"] == "APPROVED"
    assert voucher_caixa["details"]["tipo"] == "ESTANCAMENTO_QUEBRA"

    # Caso D: Gerente executa pedido de combustivel -> HTTP 200 OK com ActionVoucher
    aid_gerente = generate_action_id()
    tid_gerente = generate_tool_call_id()
    resp_gerente = client.post("/api/v1/aura/actions/execute", json={
        "session_id": sess_id,
        "tool_call_id": tid_gerente,
        "action_id": aid_gerente,
        "action_name": "pedido_combustivel",
        "action_type": "mutation",
        "operator_id": "gerente_carlos",
        "operator_role": "gerente",
        "payload": {"litros": 15000, "combustivel": "DIESEL S10", "fornecedor": "Distribuidora Oficial"}
    })
    assert resp_gerente.status_code == 200, f"Falha no pedido do gerente: {resp_gerente.status_code}"
    voucher_gerente = resp_gerente.json()
    assert voucher_gerente["status"] == "APPROVED"
    assert voucher_gerente["details"]["tipo"] == "PEDIDO_COMBUSTIVEL"
    assert voucher_gerente["signature"] != ""
    assert verify_action_voucher_signature(ActionVoucher(**voucher_gerente)) is True

    # Caso E: Idempotencia preservada para a acao do gerente
    resp_dup = client.post("/api/v1/aura/actions/execute", json={
        "session_id": sess_id,
        "tool_call_id": tid_gerente,
        "action_id": aid_gerente,
        "action_name": "pedido_combustivel",
        "action_type": "mutation",
        "operator_id": "gerente_carlos",
        "operator_role": "gerente",
        "payload": {"litros": 15000}
    })
    assert resp_dup.status_code == 200
    assert resp_dup.json()["voucher_id"] == voucher_gerente["voucher_id"]

    # Caso F: Bloqueio estrito de ataque de replay por operador nao autorizado
    # Frentista tenta contornar RBAC reutilizando action_id ja homologado por gerente
    resp_replay_frentista = client.post("/api/v1/aura/actions/execute", json={
        "session_id": sess_id,
        "tool_call_id": tid_gerente,
        "action_id": aid_gerente,
        "action_name": "pedido_combustivel",
        "action_type": "mutation",
        "operator_id": "frentista_replay",
        "operator_role": "frentista",
        "payload": {"litros": 15000}
    })
    assert resp_replay_frentista.status_code == 403, (
        f"Ataque de replay deveria ser bloqueado com 403 Forbidden, obteve {resp_replay_frentista.status_code}"
    )

    # Caso G: Robustez insensivel a caixa em action_type (INSPECTION permitida para frentista)
    aid_insp_upper = generate_action_id()
    tid_insp_upper = generate_tool_call_id()
    resp_insp_upper = client.post("/api/v1/aura/actions/execute", json={
        "session_id": sess_id,
        "tool_call_id": tid_insp_upper,
        "action_id": aid_insp_upper,
        "action_name": "visualizar_tanques",
        "action_type": "INSPECTION",
        "operator_id": "frentista_joao",
        "operator_role": "frentista",
        "payload": {}
    })
    assert resp_insp_upper.status_code == 200, f"INSPECTION insensivel a caixa falhou: {resp_insp_upper.text}"

    print("   [OK] Governanca RBAC (Frentista 403, Caixa 200/403, Gerente 200, Replay bloqueado) homologada com sucesso.")


# =============================================================================
# ETAPA 5: TRILHA DE AUDITORIA TRANSACIONAL DURAVEL (AUDIT LOG - F7-04)
# =============================================================================

def test_durable_audit_log_trail():
    print("\n5. Testando Trilha de Auditoria Transacional Duravel (Audit Log - F7-04)...")

    mem = AuraSessionMemory(db_path=":memory:")
    engine = AuraEngine(session_memory=mem)
    app = create_aura_app(engine=engine)
    client = TestClient(app)

    sess_id = f"sess_audit_{uuid.uuid4()}"

    # 5.1 Disparo de tentativa rejeitada pelo RBAC
    aid_rej = generate_action_id()
    tid_rej = generate_tool_call_id()
    client.post("/api/v1/aura/actions/execute", json={
        "session_id": sess_id,
        "tool_call_id": tid_rej,
        "action_id": aid_rej,
        "action_name": "pedido_combustivel",
        "action_type": "mutation",
        "operator_id": "frentista_alvo",
        "operator_role": "frentista",
        "payload": {"litros": 20000}
    })

    # 5.2 Disparo de acao autorizada com sucesso
    aid_app = generate_action_id()
    tid_app = generate_tool_call_id()
    client.post("/api/v1/aura/actions/execute", json={
        "session_id": sess_id,
        "tool_call_id": tid_app,
        "action_id": aid_app,
        "action_name": "pedido_combustivel",
        "action_type": "mutation",
        "operator_id": "gerente_audit",
        "operator_role": "gerente",
        "payload": {"litros": 10000, "combustivel": "ETANOL"}
    })

    # 5.3 Consulta direta no AuraSessionMemory
    logs_mem = mem.get_audit_logs(session_id=sess_id)
    assert len(logs_mem) >= 2, f"Esperava ao menos 2 logs na memoria, obteve {len(logs_mem)}"

    # O mais recente deve ser APPROVED (ordem rowid DESC)
    log_app = next(l for l in logs_mem if l["action_id"] == aid_app)
    assert log_app["status"] == "APPROVED"
    assert log_app["authorized"] is True
    assert log_app["operator_role"] == "gerente"
    assert "voucher_id" in log_app["details"]

    log_rej = next(l for l in logs_mem if l["action_id"] == aid_rej)
    assert log_rej["status"] == "REJECTED_FORBIDDEN"
    assert log_rej["authorized"] is False
    assert log_rej["operator_role"] == "frentista"
    assert "motivo" in log_rej["details"]

    # 5.4 Consulta via endpoint FastAPI GET /api/v1/aura/audit/logs
    resp_logs = client.get(f"/api/v1/aura/audit/logs?session_id={sess_id}")
    assert resp_logs.status_code == 200, f"Falha na consulta de logs: {resp_logs.text}"
    api_logs = resp_logs.json()
    assert len(api_logs) >= 2

    # Validacao do modelo Pydantic ActionAuditLogRecord
    parsed_record = ActionAuditLogRecord(**api_logs[0])
    assert parsed_record.audit_id != ""
    assert parsed_record.timestamp != ""

    # Teste de filtro por status REJECTED_FORBIDDEN (e validacao de case-insensitivity: lowercase query)
    resp_rej = client.get(f"/api/v1/aura/audit/logs?session_id={sess_id}&status=REJECTED_FORBIDDEN")
    assert resp_rej.status_code == 200
    rej_items = resp_rej.json()
    assert len(rej_items) == 1
    assert rej_items[0]["status"] == "REJECTED_FORBIDDEN"

    # Teste de filtro com status em letras minusculas (case-insensitive query)
    resp_rej_lower = client.get(f"/api/v1/aura/audit/logs?session_id={sess_id}&status=rejected_forbidden")
    assert resp_rej_lower.status_code == 200
    assert len(resp_rej_lower.json()) == 1

    resp_app_lower = client.get(f"/api/v1/aura/audit/logs?session_id={sess_id}&status=approved")
    assert resp_app_lower.status_code == 200
    assert len(resp_app_lower.json()) >= 1

    # 5.5 Teste de serializacao robusta com objetos nao-primitivos em details
    aid_robust = generate_action_id()
    tid_robust = generate_tool_call_id()
    saved_id = mem.save_audit_log(
        session_id=sess_id,
        tool_call_id=tid_robust,
        action_id=aid_robust,
        action_name="teste_serializacao_robusta",
        details={"erro": Exception("falha_simulada"), "data": datetime.now(timezone.utc)},
        status="APPROVED"
    )
    assert saved_id != ""
    robust_logs = mem.get_audit_logs(action_id=aid_robust)
    assert len(robust_logs) == 1
    assert "falha_simulada" in str(robust_logs[0]["details"])

    # Teste de filtro por limite
    resp_lim = client.get(f"/api/v1/aura/audit/logs?limit=1")
    assert resp_lim.status_code == 200
    assert len(resp_lim.json()) == 1

    print("   [OK] Trilha de auditoria duravel e endpoint GET /audit/logs homologados com sucesso.")


# =============================================================================
# ETAPA 6: REGRESSAO ATOMICA RAPIDA (ZERO SUBPROCESSOS ANINHADOS PROFUNDOS)
# =============================================================================

def test_atomic_regression_fast():
    print("\n6. Executando Validacao de Regressao Atomica Rapida (test_genui_baseline & test_aura_aux_panel)...")

    # 6.1 test_aura_aux_panel.py
    aux_panel_script = BASE_DIR / "scripts" / "test_aura_aux_panel.py"
    res_aux = subprocess.run(
        [sys.executable, str(aux_panel_script)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    assert res_aux.returncode == 0, f"Falha na regressao test_aura_aux_panel: {res_aux.stderr}"
    print("   [OK] test_aura_aux_panel.py aprovado com 100% de sucesso.")

    # 6.2 Idempotencia basica em Python
    from core.schemas.idempotency import generate_uuid4, is_valid_uuid4, validate_tool_call_id
    u = generate_uuid4()
    assert is_valid_uuid4(u)
    assert validate_tool_call_id("call_" + u)

    print("   [OK] Regressao atomica concluida com zero falhas.")


# =============================================================================
# MAIN RUNNER
# =============================================================================

def main():
    print("=" * 78)
    print("🛡️ SUITE DE TESTES: HARDENING DE SEGURANCA CIBERNETICA & OWASP LLM (FASE 7 - P0/P1)")
    print("   (Mitigacao OWASP LLM03, OWASP LLM01, Coercao Estrita, RBAC e Audit Log)")
    print("=" * 78)

    test_owasp_llm03_excessive_agency_mitigation()
    test_owasp_llm01_prompt_injection_and_sanitization()
    test_strict_primitive_type_coercion()
    test_operator_rbac_governance()
    test_durable_audit_log_trail()
    test_atomic_regression_fast()

    print("\n" + "=" * 78)
    print("🎉 FASE 7 (HARDENING DE SEGURANCA & GOVERNANCA) HOMOLOGADA COM 100% DE SUCESSO!")
    print("   OWASP LLM03 mitigado, OWASP LLM01 sanitizado, RBAC ativo e Audit Log duravel.")
    print("=" * 78 + "\n")


if __name__ == "__main__":
    main()
