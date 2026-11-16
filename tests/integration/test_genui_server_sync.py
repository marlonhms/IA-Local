"""
Suite de Testes Automatizada: Sincronizacao Bidirecional & Memoria do Agente (Fase 5: P1)
(ActionExecuteRequest, ActionVoucher, POST /actions/execute, Idempotencia Estrita,
 Injecao de role tool no SQLite, Consistencia Contextual Multiturn, Node.js e Zero Regressao)

Validacoes Obrigatorias:
1. Contratos Pydantic de Acao Transacional e Voucher (core/schemas/genui.py):
   - ActionExecuteRequest: validacao de tool_call_id, action_id RFC 4122 v4, rejeicao de identificadores invalidos.
   - ActionVoucher: validacao de voucher_id, tool_call_id, action_id, status APPROVED/EXECUTED.
   - Assinatura auditavel HMAC-SHA256 (generate_action_voucher_signature e verify_action_voucher_signature).
2. Endpoint de Execucao Transacional (core/aura_api.py - POST /api/v1/aura/actions/execute):
   - Requisicao valida de pedido de combustivel e emissao de ActionVoucher.
   - Rejeicao de payloads invalidos (HTTP 422).
3. Idempotencia Estrita:
   - Duplo envio com o mesmo action_id retorna o mesmo voucher sem reexecucao de rotina e sem duplicacao de registros.
4. Injecao Direta de role 'tool' em AuraSessionMemory e Preservacao no SQLite:
   - Armazenamento com tool_call_id e name no SQLite.
   - Recuperacao cronologica via get_history e get_history_as_messages para IA de nuvem.
5. Consistencia Contextual Subsequente (Prevencao de Amnesia Contextual):
   - format_history_for_prompt formata acoes confirmadas adequadamente.
   - Pergunta seguinte ("Qual o status daquele pedido de combustivel?") reconhece o voucher e confirma o pedido.
6. Validacao de Integracao no Cliente (Node.js Headless):
   - AuraApiClient.executeAction despachando requisicao com session_id e payload.
   - AuraStateManager travando widget, aplicando estado otimista e finalizando com sucesso.
   - Renderizacao do badge de conclusao auditado no DOM.
7. Validacao de Regressao Zero nas Suites Homologadas Anteriores.
"""

import sys
import json
import uuid
import hmac
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

# Protege stdout no terminal Windows contra problemas de codificacao
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from pydantic import ValidationError
from fastapi.testclient import TestClient

from core.schemas.genui import (
    ActionExecuteRequest,
    ActionVoucher,
    generate_action_voucher_signature,
    verify_action_voucher_signature,
    WidgetStateRecord,
    WidgetActionExecution,
    GenUIEnvelope,
)
from core.schemas.idempotency import (
    generate_tool_call_id,
    generate_action_id,
    generate_uuid4,
    validate_tool_call_id,
    validate_action_id,
)
from core.aura_engine import AuraEngine, AuraSessionMemory
from core.aura_api import create_aura_app, set_aura_engine


# =============================================================================
# ETAPA 1: CONTRATOS PYDANTIC E ASSINATURA AUDITAVEL (F5-01)
# =============================================================================

def test_pydantic_contracts_and_signatures():
    print("\n1. Testando Contratos Pydantic de Acao Transacional e Voucher (ActionExecuteRequest, ActionVoucher)...")

    tool_id = generate_tool_call_id()
    act_id = generate_action_id()
    sess_id = f"sess_{uuid.uuid4()}"

    # 1.1 ActionExecuteRequest valido
    req = ActionExecuteRequest(
        session_id=sess_id,
        tool_call_id=tool_id,
        action_id=act_id,
        action_name="pedido_combustivel",
        action_type="mutation",
        payload={"litros": 15000, "combustivel": "GASOLINA COMUM"},
        operator_id="operador_01"
    )
    assert req.session_id == sess_id
    assert req.tool_call_id == tool_id
    assert req.action_id == act_id
    assert req.action_name == "pedido_combustivel"
    assert req.action_type == "mutation"
    assert req.payload["litros"] == 15000
    assert req.operator_id == "operador_01"

    # 1.2 Rejeicao de IDs invalidos em ActionExecuteRequest
    try:
        ActionExecuteRequest(
            tool_call_id="invalid_call_id",
            action_id=act_id
        )
        assert False, "Deveria rejeitar tool_call_id malformado"
    except ValidationError:
        pass

    try:
        ActionExecuteRequest(
            tool_call_id=tool_id,
            action_id="invalid_action_id"
        )
        assert False, "Deveria rejeitar action_id malformado"
    except ValidationError:
        pass

    # 1.3 ActionVoucher valido e assinatura HMAC-SHA256
    voucher_id = generate_uuid4()
    ts = datetime.now(timezone.utc).isoformat()
    sig = generate_action_voucher_signature(
        voucher_id=voucher_id,
        action_id=act_id,
        tool_call_id=tool_id,
        status="APPROVED",
        timestamp=ts,
    )

    voucher = ActionVoucher(
        voucher_id=voucher_id,
        action_id=act_id,
        tool_call_id=tool_id,
        status="APPROVED",
        timestamp=ts,
        action_name="pedido_combustivel",
        details={"litros": 15000, "fornecedor": "Distribuidora Oficial"},
        signature=sig,
    )
    assert voucher.voucher_id == voucher_id
    assert voucher.status == "APPROVED"
    assert verify_action_voucher_signature(voucher) is True

    # 1.4 Deteccao de assinatura adulterada
    tampered_voucher = ActionVoucher(
        voucher_id=voucher_id,
        action_id=act_id,
        tool_call_id=tool_id,
        status="APPROVED",
        timestamp=ts,
        action_name="pedido_combustivel",
        details={"litros": 99999}, # alterado
        signature="signature_forjada_1234567890abcdef",
    )
    assert verify_action_voucher_signature(tampered_voucher) is False

    print("   [OK] Contratos tipados e assinatura criptografica validados com sucesso.")


# =============================================================================
# ETAPA 2: ENDPOINT DE EXECUCAO TRANSACIONAL & FORMATO DO VOUCHER (F5-01)
# =============================================================================

def test_execute_action_endpoint():
    print("\n2. Testando Endpoint POST /api/v1/aura/actions/execute com TestClient FastAPI...")

    mem = AuraSessionMemory(db_path=":memory:")
    engine = AuraEngine(session_memory=mem)
    app = create_aura_app(engine=engine)
    client = TestClient(app)

    tool_id = generate_tool_call_id()
    act_id = generate_action_id()
    sess_id = f"sess_{uuid.uuid4()}"

    # 2.1 Execucao com sucesso de pedido de combustivel
    payload = {
        "session_id": sess_id,
        "tool_call_id": tool_id,
        "action_id": act_id,
        "action_name": "pedido_combustivel",
        "action_type": "mutation",
        "payload": {
            "litros": 15000,
            "combustivel": "GASOLINA COMUM",
            "fornecedor": "Distribuidora Oficial"
        },
        "operator_id": "gerente_01"
    }

    resp = client.post("/api/v1/aura/actions/execute", json=payload)
    assert resp.status_code == 200, f"Falha na rota: {resp.status_code} - {resp.text}"
    data = resp.json()

    assert data["status"] == "APPROVED"
    assert data["action_id"] == act_id
    assert data["tool_call_id"] == tool_id
    assert "voucher_id" in data
    assert "signature" in data
    assert data["details"]["litros"] == 15000
    assert data["details"]["combustivel"] == "GASOLINA COMUM"
    assert data["details"]["executado_por"] == "gerente_01"
    assert "confirmacao_erp" in data["details"]

    # Valida assinatura do voucher retornado
    ret_voucher = ActionVoucher(**data)
    assert verify_action_voucher_signature(ret_voucher) is True

    # 2.2 Rejeicao de payload com IDs invalidos (HTTP 422)
    bad_payload = {
        "session_id": sess_id,
        "tool_call_id": "not-a-valid-uuid",
        "action_id": act_id,
    }
    resp_bad = client.post("/api/v1/aura/actions/execute", json=bad_payload)
    assert resp_bad.status_code == 422, f"Deveria retornar 422, retornou {resp_bad.status_code}"

    print("   [OK] Endpoint de execucao transacional e formato do voucher homologados.")


# =============================================================================
# ETAPA 3: IDEMPOTENCIA ESTRITA (F5-01)
# =============================================================================

def test_strict_idempotency():
    print("\n3. Testando Idempotencia Estrita (Duplo Envio do Mesmo action_id)...")

    mem = AuraSessionMemory(db_path=":memory:")
    engine = AuraEngine(session_memory=mem)
    app = create_aura_app(engine=engine)
    client = TestClient(app)

    tool_id = generate_tool_call_id()
    act_id = generate_action_id()
    sess_id = f"sess_{uuid.uuid4()}"

    payload = {
        "session_id": sess_id,
        "tool_call_id": tool_id,
        "action_id": act_id,
        "action_name": "estancar_quebra",
        "action_type": "mutation",
        "payload": {"valor": 85.0, "turno": 1},
        "operator_id": "fiscal_caixa"
    }

    # Primeiro envio
    resp1 = client.post("/api/v1/aura/actions/execute", json=payload)
    assert resp1.status_code == 200
    voucher1 = resp1.json()

    # Segundo envio imediato com o mesmo action_id
    resp2 = client.post("/api/v1/aura/actions/execute", json=payload)
    assert resp2.status_code == 200
    voucher2 = resp2.json()

    # Devem ser exatamente identicos
    assert voucher1["voucher_id"] == voucher2["voucher_id"]
    assert voucher1["signature"] == voucher2["signature"]
    assert voucher1["timestamp"] == voucher2["timestamp"]
    assert voucher1["details"] == voucher2["details"]

    # Terceiro envio com payload diferente mas mesmo action_id
    payload_alterado = dict(payload)
    payload_alterado["payload"] = {"valor": 9999.0}
    resp3 = client.post("/api/v1/aura/actions/execute", json=payload_alterado)
    assert resp3.status_code == 200
    voucher3 = resp3.json()

    # Deve retornar o voucher original imutavel
    assert voucher3["voucher_id"] == voucher1["voucher_id"]
    assert voucher3["details"]["valor"] == 85.0

    # Verifica integridade na tabela do SQLite: deve ter exatamente 1 voucher e 1 tool message
    with mem._connection() as conn:
        cur = conn.execute("SELECT COUNT(*) AS c FROM aura_action_vouchers WHERE action_id = ?;", (act_id,))
        count_vouchers = cur.fetchone()["c"]
        assert count_vouchers == 1, f"Duplicacao na tabela de vouchers: {count_vouchers}"

        cur2 = conn.execute("SELECT COUNT(*) AS c FROM aura_messages WHERE session_id = ? AND role = 'tool';", (sess_id,))
        count_tool_msgs = cur2.fetchone()["c"]
        assert count_tool_msgs == 1, f"Duplicacao de mensagens de ferramenta: {count_tool_msgs}"

    print("   [OK] Idempotencia estrita comprovada: duplo envio reutiliza voucher e evita duplicacao.")


# =============================================================================
# ETAPA 4: INJECAO DE role 'tool' EM AuraSessionMemory E SQLITE (F5-02)
# =============================================================================

def test_tool_message_injection_and_sqlite_persistence():
    print("\n4. Testando Injecao Direta de role 'tool' em AuraSessionMemory e SQLite...")

    mem = AuraSessionMemory(db_path=":memory:")
    sess_id = f"sess_{uuid.uuid4()}"
    tool_id = generate_tool_call_id()
    act_id = generate_action_id()
    v_id = generate_uuid4()

    # Salva turno conversacional tipico
    mem.save_message(sess_id, "user", "Como estao os estoques dos tanques?")
    mem.save_message(sess_id, "assistant", "Tanque 1 com autonomia de 14h. Decisao: emitir pedido de 15.000 L.")

    # Injeta mensagem canonica de acao executada (role: tool)
    tool_payload = {
        "status": "APPROVED",
        "action_id": act_id,
        "voucher_id": v_id,
        "details": {
            "litros": 15000,
            "combustivel": "GASOLINA COMUM",
            "executado_por": "operador_01"
        }
    }
    mem.save_message(
        session_id=sess_id,
        role="tool",
        content=json.dumps(tool_payload, ensure_ascii=False),
        intent="pedido_combustivel",
        tool_call_id=tool_id,
        name="pedido_combustivel",
        metadata={"voucher_id": v_id, "signature": "hmac_hash_sample"}
    )

    # Recupera historico
    hist = mem.get_history(sess_id, limit=10)
    assert len(hist) == 3
    assert hist[0]["role"] == "user"
    assert hist[1]["role"] == "assistant"
    assert hist[2]["role"] == "tool"

    # Valida campos da mensagem tool
    tool_msg = hist[2]
    assert tool_msg["tool_call_id"] == tool_id
    assert tool_msg["name"] == "pedido_combustivel"
    parsed_content = json.loads(tool_msg["content"])
    assert parsed_content["status"] == "APPROVED"
    assert parsed_content["voucher_id"] == v_id
    assert parsed_content["details"]["litros"] == 15000

    # Valida exportacao canônica para APIs de nuvem (OpenAI / Anthropic / Gemini)
    cloud_messages = mem.get_history_as_messages(sess_id, limit=10)
    assert len(cloud_messages) == 3
    assert cloud_messages[2]["role"] == "tool"
    assert cloud_messages[2]["tool_call_id"] == tool_id
    assert cloud_messages[2]["name"] == "pedido_combustivel"

    print("   [OK] Injecao de role 'tool', preservacao no SQLite e adaptadores de nuvem validados.")


# =============================================================================
# ETAPA 5: CONSISTENCIA CONTEXTUAL SUBSEQUENTE (F5-03)
# =============================================================================

def test_multiturn_contextual_consistency():
    print("\n5. Testando Consistencia Contextual Subsequente (Prevencao de Amnesia Contextual)...")

    mem = AuraSessionMemory(db_path=":memory:")
    engine = AuraEngine(session_memory=mem)
    app = create_aura_app(engine=engine)
    client = TestClient(app)

    sess_id = f"sess_{uuid.uuid4()}"
    tool_id = generate_tool_call_id()
    act_id = generate_action_id()

    # 1. Simula primeiro turno: usuario pergunta sobre tanques
    mem.save_message(sess_id, "user", "Como estao os tanques hoje?")
    mem.save_message(
        sess_id,
        "assistant",
        "Tanque 1 (Gasolina Comum) critico com 14h de autonomia. Decisao recomendada: Emitir pedido de 15.000 L."
    )

    # 2. Operador clica e executa a acao no endpoint
    exec_resp = client.post("/api/v1/aura/actions/execute", json={
        "session_id": sess_id,
        "tool_call_id": tool_id,
        "action_id": act_id,
        "action_name": "pedido_combustivel",
        "action_type": "mutation",
        "payload": {"litros": 15000, "combustivel": "GASOLINA COMUM"},
        "operator_id": "gerente_turno"
    })
    assert exec_resp.status_code == 200
    voucher_data = exec_resp.json()
    voucher_id = voucher_data["voucher_id"]

    # 3. Formata historico para o prompt do LLM
    prompt_hist = mem.format_history_for_prompt(sess_id, limit=10)
    assert "Ação Confirmada [pedido_combustivel]" in prompt_hist
    assert voucher_id in prompt_hist
    assert "15000" in prompt_hist

    # 4. Turno seguinte: usuario pergunta o status daquele pedido
    sintese = engine._gerar_sintese_contingencia_ferramenta(
        intencao="previsao_tanques",
        resultado_bruto={"assessment": {"status": "ok"}},
        pergunta="Qual o status daquele pedido de combustível?",
        session_id=sess_id
    )

    assert sintese is not None
    assert "Pedido Confirmado no ERP" in sintese
    assert voucher_id in sintese
    assert "15.000 L" in sintese or "15000" in sintese
    assert "Não há necessidade de recalcular" in sintese or "já foi submetido" in sintese

    print("   [OK] Consistencia contextual comprovada: motor cognitivo reconhece a acao aprovada.")


# =============================================================================
# ETAPA 6: VALIDACAO HEADLESS NO CLIENTE EM NODE.JS (F5-04)
# =============================================================================

def test_nodejs_client_integration():
    print("\n6. Executando Validacao Headless no Cliente via Node.js (executeAction e DOM Badge)...")

    api_js_path = BASE_DIR / "web" / "js" / "aura-api.js"
    state_mgr_js_path = BASE_DIR / "web" / "js" / "aura-state-manager.js"
    widgets_js_path = BASE_DIR / "web" / "js" / "aura-genui-widgets.js"

    node_script = f"""
    const assert = require('assert');

    // 1. Mock de ambiente de navegador (DOM e storage)
    class MockStorage {{
      constructor() {{ this.store = new Map(); }}
      getItem(k) {{ return this.store.get(k) || null; }}
      setItem(k, v) {{ this.store.set(k, String(v)); }}
      removeItem(k) {{ this.store.delete(k); }}
      clear() {{ this.store.clear(); }}
    }}

    global.window = global;
    global.window.sessionStorage = new MockStorage();
    global.window.addEventListener = () => {{}};

    // Mock simples de elementos do DOM
    class MockElement {{
      constructor(tagName = 'div') {{
        this.tagName = tagName;
        this.className = '';
        this.innerHTML = '';
        this.children = [];
        this.attributes = {{}};
      }}
      setAttribute(k, v) {{ this.attributes[k] = String(v); }}
      getAttribute(k) {{ return this.attributes[k] || null; }}
      querySelector(sel) {{ return new MockElement('div'); }}
      querySelectorAll(sel) {{ return []; }}
    }}

    global.document = {{
      createElement: (t) => new MockElement(t),
      getElementById: () => null,
      querySelector: () => null,
      querySelectorAll: () => []
    }};

    // Carrega modulos Zero-Bundler
    const {{ AuraApiClient }} = require({json.dumps(str(api_js_path.resolve()))});
    const {{ AuraStateManager }} = require({json.dumps(str(state_mgr_js_path.resolve()))});
    const {{ ExecutiveDecisionMentorUI }} = require({json.dumps(str(widgets_js_path.resolve()))});

    const stateMgr = new AuraStateManager();
    global.window.auraStateManager = stateMgr;

    // 2. Mock do fetch na rota /api/v1/aura/actions/execute
    const toolCallId = 'call_99998888-7777-4444-8888-111122223333';
    const actionId = 'act_11112222-3333-4444-8888-99990000aaaa';
    const fakeVoucher = {{
      voucher_id: 'vch_00001111-2222-4333-8444-555566667777',
      action_id: actionId,
      tool_call_id: toolCallId,
      status: 'APPROVED',
      timestamp: new Date().toISOString(),
      action_name: 'pedido_combustivel',
      details: {{ litros: 15000, combustivel: 'GASOLINA COMUM' }},
      signature: 'mock_signature_hmac_123'
    }};

    global.fetch = async (url, opts) => {{
      assert(url.includes('/api/v1/aura/actions/execute'), 'URL incorreta: ' + url);
      const reqBody = JSON.parse(opts.body);
      assert.strictEqual(reqBody.action_id, actionId);
      assert.strictEqual(reqBody.tool_call_id, toolCallId);
      return {{
        ok: true,
        status: 200,
        json: async () => fakeVoucher
      }};
    }};

    const apiClient = new AuraApiClient({{ baseUrl: 'http://127.0.0.1:8000' }});
    global.window.auraApi = apiClient;

    (async () => {{
      // 3. Testa invocacao de apiClient.executeAction
      const voucher = await apiClient.executeAction(actionId, {{
        tool_call_id: toolCallId,
        session_id: 'sess_node_test_1',
        action_name: 'pedido_combustivel',
        action_type: 'mutation',
        payload: {{ litros: 15000 }}
      }});

      assert.strictEqual(voucher.status, 'APPROVED');
      assert.strictEqual(voucher.voucher_id, fakeVoucher.voucher_id);

      // 4. Testa mutacao no AuraStateManager
      stateMgr.registerWidget(toolCallId, {{ litros: 15000 }}, 900);
      stateMgr.lockWidget(toolCallId, actionId);
      assert.strictEqual(stateMgr.getWidget(toolCallId).isLocked, true);

      stateMgr.markActionExecuted(actionId, voucher);
      stateMgr.finalizeSuccessState(toolCallId, voucher);

      assert.strictEqual(stateMgr.isActionExecuted(actionId), true);
      assert.strictEqual(stateMgr.getWidget(toolCallId).status, 'committed');

      // 5. Testa componente ExecutiveDecisionMentorUI e renderizacao do badge de conclusao
      const widget = new ExecutiveDecisionMentorUI({{
        tool_call_id: toolCallId,
        session_id: 'sess_node_test_1',
        actions: [
          {{ action_id: actionId, label: 'Emitir Pedido 15.000 L', variant: 'primary' }}
        ]
      }});

      widget.finalizeSuccessState(voucher);
      assert.strictEqual(widget.state.status, 'committed');
      assert.strictEqual(widget.state.voucher.voucher_id, fakeVoucher.voucher_id);

      const htmlL3 = widget.renderLayer3();
      assert(htmlL3.includes('genui-success-badge') || htmlL3.includes('badge-committed'), 'HTML nao contem badge de conclusao');
      assert(htmlL3.includes('VOUCHER AUDITADO'), 'HTML nao contem texto VOUCHER AUDITADO');

      console.log('NODE_GENUI_SERVER_SYNC_OK');
    }})();
    """

    res = subprocess.run(
        ["node", "-e", node_script],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    if res.returncode != 0:
        print("[ERRO NODE.JS]:\n", res.stderr)
        print("[STDOUT NODE.JS]:\n", res.stdout)
        raise RuntimeError(f"Validacao Node.js headless falhou com codigo {res.returncode}")

    assert "NODE_GENUI_SERVER_SYNC_OK" in res.stdout
    print("   [OK] Integracao cliente em Node.js (executeAction, stateMgr e badge de voucher) validada.")


# =============================================================================
# ETAPA 7: REGRESSAO ZERO NAS SUITES ANTERIORES
# =============================================================================

def test_zero_regression():
    print("\n7. Executando Validacao de Regressao Zero nas Suites Anteriores...")

    suites = [
        ("test_genui_baseline.py", "Fase 0: Linha de Base GenUI, Registry & OWASP LLM03"),
        ("test_genui_engine_sse.py", "Fase 1: Backend SSE Multiplexado & Envelopes"),
        ("test_genui_frontend_streaming.py", "Fase 2: Streaming Parser, Buffer & Skeleton UI"),
        ("test_genui_decision_mentor.py", "Fase 3: Micro-Widget Piloto ExecutiveDecisionMentorUI"),
        ("test_genui_state_manager.py", "Fase 4: AuraStateManager, State Locking & Idempotencia Local"),
    ]

    for script_name, desc in suites:
        script_path = BASE_DIR / "scripts" / script_name
        print(f"   ► Executando {script_name} ({desc})...")
        res = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        if res.returncode != 0:
            print(f"[FALHA EM {script_name}]:")
            print(res.stderr or res.stdout)
            raise RuntimeError(f"Regressao detectada em {script_name}! Codigo de saida: {res.returncode}")
        print(f"     [OK] {script_name} aprovado com 100% de sucesso.")

    print("\n   [OK] Regressao zero garantida em todas as 5 suites homologadas anteriores.")


# =============================================================================
# RUNNER PRINCIPAL
# =============================================================================

def main():
    print("=" * 78)
    print("SUITE DE TESTES: SINCRONIZACAO SERVIDOR-CLIENTE & MEMORIA (FASE 5: P1)")
    print("   (ActionExecuteRequest, ActionVoucher, POST /actions/execute, Idempotencia,")
    print("    Injecao de role tool, Consistencia Contextual Multiturn & Zero Regressao)")
    print("=" * 78)

    try:
        test_pydantic_contracts_and_signatures()
        test_execute_action_endpoint()
        test_strict_idempotency()
        test_tool_message_injection_and_sqlite_persistence()
        test_multiturn_contextual_consistency()
        test_nodejs_client_integration()
        test_zero_regression()

        print("\n" + "=" * 78)
        print("FASE 5: SINCRONIZACAO BIDIRECIONAL & MEMORIA HOMOLOGADA COM 100% DE SUCESSO!")
        print("   Idempotencia estrita, Action Voucher auditado e zero amnesia contextual.")
        print("=" * 78)
        return 0

    except Exception as e:
        print(f"\nERRO NA EXECUCAO DA SUITE FASE 5: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
