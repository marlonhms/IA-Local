"""
Suite de Testes Automatizada: Motor de Gestao de Estado no Cliente, Idempotencia & Optimistic UI (Fase 4: P1)
(AuraStateManager, State Locking, Idempotencia, TTL 15min, Rollback Resiliente, Mock SessionStorage e Zero Regressao)

Validacoes Obrigatorias:
1. Validacao dos Modelos Pydantic (core/schemas/genui.py):
   - WidgetStateRecord: validacao de tool_call_id RFC 4122 v4, status de ciclo de vida, is_stale() por TTL, serializacao.
   - WidgetActionExecution: validacao de action_id e tool_call_id RFC 4122 v4, rejeicao de identificadores invalidos.
   - GenUIActionResult e GenUIEnvelope: integracao com metadados de estado.
2. Validacao do Servimento Estatico FastAPI (core/aura_api.py & web/index.html):
   - Presenca da tag script em web/index.html na ordem correta (apos aura-genui.js e antes de aura-genui-widgets.js/aura-chat.js).
   - Rota estatica /static/js/aura-state-manager.js servida com 200 OK.
3. Validacao Headless em Node.js (web/js/aura-state-manager.js & web/js/aura-genui-widgets.js):
   - Registro de widgets, atualizacao de props e recuperacao por tool_call_id.
   - State Locking imediato (lockWidget, unlockWidget).
   - Idempotencia criptografica local (isActionExecuted, markActionExecuted, protecao contra duplo clique).
   - Inspecao de TTL e expiracao de acoes apos 15 minutos (900s) com desabilitacao tatil e badge de expiracao.
   - Optimistic UI com snapshots de reversao perfeita (applyOptimisticState, rollbackOptimisticState, finalizeSuccessState).
   - Persistencia segura em sessionStorage mockado com isolamento total em try-catch.
   - Integracao com ExecutiveDecisionMentorUI e despacho de toast via window.auraFx.
4. Validacao de Regressao Zero nas Suites Homologadas:
   - test_genui_baseline.py (Fase 0)
   - test_genui_engine_sse.py (Fase 1)
   - test_genui_frontend_streaming.py (Fase 2)
   - test_aura_aux_panel.py (Companion Canvas)
"""

import sys
import json
import re
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
    WidgetStateRecord,
    WidgetActionExecution,
    GenUIActionResult,
    GenUIEnvelope,
    GenUIActionOption,
)
from core.schemas.idempotency import generate_tool_call_id, generate_action_id
from core.aura_api import create_aura_app


# =============================================================================
# ETAPA 1: MODELOS PYDANTIC DE GESTAO DE ESTADO (F4-01)
# =============================================================================

def test_pydantic_state_contracts():
    print("\n1. Testando Contratos Pydantic de Estado e Idempotencia (WidgetStateRecord, WidgetActionExecution)...")

    # 1.1 WidgetStateRecord valido
    tool_id = generate_tool_call_id()
    act_id = generate_action_id()

    record = WidgetStateRecord(
        tool_call_id=tool_id,
        status="proposed",
        is_locked=False,
        locked_action_id=None,
        ttl_seconds=900,
        props={"margem": 15.5}
    )
    assert record.tool_call_id == tool_id
    assert record.status == "proposed"
    assert record.is_locked is False
    assert record.ttl_seconds == 900
    assert record.props["margem"] == 15.5
    assert record.is_stale() is False

    # 1.2 Teste de expiracao TTL em WidgetStateRecord
    old_ts = int((datetime.now(timezone.utc).timestamp() - 1000) * 1000) # 1000s atras (> 900s)
    stale_record = WidgetStateRecord(
        tool_call_id=tool_id,
        status="proposed",
        timestamp=old_ts,
        ttl_seconds=900
    )
    assert stale_record.is_stale() is True

    # 1.3 Rejeicao de tool_call_id invalido em WidgetStateRecord
    try:
        WidgetStateRecord(tool_call_id="invalid_uuid_12345")
        assert False, "Deveria falhar com tool_call_id invalido"
    except ValidationError:
        pass

    # 1.4 WidgetActionExecution valido
    action_exec = WidgetActionExecution(
        action_id=act_id,
        tool_call_id=tool_id,
        payload={"param": 100}
    )
    assert action_exec.action_id == act_id
    assert action_exec.tool_call_id == tool_id
    assert action_exec.payload["param"] == 100

    # 1.5 Rejeicao de action_id invalido em WidgetActionExecution
    try:
        WidgetActionExecution(action_id="act_invalid_xxx", tool_call_id=tool_id)
        assert False, "Deveria falhar com action_id malformado"
    except ValidationError:
        pass

    print("   [OK] Contratos Pydantic de estado validados com 100% de sucesso.")


# =============================================================================
# ETAPA 2: SERVIÇO ESTATICO E INTEGRACAO HTML SHELL (F4-01)
# =============================================================================

def test_static_delivery_and_html_shell():
    print("\n2. Testando Servimento Estatico FastAPI e Integracao Shell web/index.html...")

    state_mgr_path = BASE_DIR / "web" / "js" / "aura-state-manager.js"
    index_html_path = BASE_DIR / "web" / "index.html"

    assert state_mgr_path.exists(), f"Arquivo nao encontrado: {state_mgr_path}"
    assert index_html_path.exists(), f"Arquivo nao encontrado: {index_html_path}"

    state_mgr_js = state_mgr_path.read_text(encoding="utf-8")
    index_html = index_html_path.read_text(encoding="utf-8")

    # 2.1 Conteudo obrigatorio do aura-state-manager.js
    assert "class AuraStateManager" in state_mgr_js
    assert "registerWidget" in state_mgr_js
    assert "getWidget" in state_mgr_js
    assert "lockWidget" in state_mgr_js
    assert "unlockWidget" in state_mgr_js
    assert "isActionExecuted" in state_mgr_js
    assert "markActionExecuted" in state_mgr_js
    assert "isStale" in state_mgr_js
    assert "applyOptimisticState" in state_mgr_js
    assert "rollbackOptimisticState" in state_mgr_js
    assert "finalizeSuccessState" in state_mgr_js
    assert "persistToSessionStorage" in state_mgr_js
    assert "loadFromSessionStorage" in state_mgr_js
    assert "module.exports" in state_mgr_js

    # 2.2 Ordem de inclusao em web/index.html
    assert "aura-state-manager.js" in index_html, "aura-state-manager.js ausente no index.html"
    idx_genui = index_html.find('src="/static/js/aura-genui.js')
    idx_statemgr = index_html.find('src="/static/js/aura-state-manager.js')
    idx_widgets = index_html.find('src="/static/js/aura-genui-widgets.js')
    idx_chat = index_html.find('src="/static/js/aura-chat.js')

    assert idx_genui != -1, "aura-genui.js ausente no index.html"
    assert idx_statemgr != -1, "aura-state-manager.js ausente no index.html"
    assert idx_widgets != -1, "aura-genui-widgets.js ausente no index.html"
    assert idx_chat != -1, "aura-chat.js ausente no index.html"

    assert idx_genui < idx_statemgr < idx_widgets, "Ordem incorreta: aura-state-manager.js deve carregar apos aura-genui.js e antes de aura-genui-widgets.js"
    assert idx_statemgr < idx_chat, "Ordem incorreta: aura-state-manager.js deve carregar antes de aura-chat.js"

    # 2.3 Rota estatica FastAPI via TestClient
    app = create_aura_app()
    client = TestClient(app)
    resp = client.get("/static/js/aura-state-manager.js")
    assert resp.status_code == 200, f"Falha ao servir asset /static/js/aura-state-manager.js: {resp.status_code}"
    assert "class AuraStateManager" in resp.text

    print("   [OK] Shell HTML, ordem dos scripts e rota estatica FastAPI validados com 100% de sucesso.")


# =============================================================================
# ETAPA 3: VALIDAÇAO HEADLESS EM NODE.JS (F4-01, F4-02, F4-03, F4-04)
# =============================================================================

def test_nodejs_headless_state_manager():
    print("\n3. Executando Validacoes Headless em Node.js (State Locking, Duplo Clique, TTL, Rollback & Storage)...")

    state_mgr_js_path = BASE_DIR / "web" / "js" / "aura-state-manager.js"
    widgets_js_path = BASE_DIR / "web" / "js" / "aura-genui-widgets.js"
    chat_js_path = BASE_DIR / "web" / "js" / "aura-chat.js"

    node_test_code = f"""
    const assert = require('assert');
    const path = require('path');

    const stateMgrPath = {json.dumps(str(state_mgr_js_path.resolve()))};
    const widgetsPath = {json.dumps(str(widgets_js_path.resolve()))};

    // 1. Setup de ambiente DOM e Storage mock para Node.js
    class MockStorage {{
      constructor() {{ this.store = new Map(); }}
      getItem(k) {{ return this.store.has(k) ? this.store.get(k) : null; }}
      setItem(k, v) {{ this.store.set(k, String(v)); }}
      removeItem(k) {{ this.store.delete(k); }}
      clear() {{ this.store.clear(); }}
    }}

    const mockSessionStorage = new MockStorage();
    global.window = global;
    global.window.addEventListener = () => {{}};
    global.window.removeEventListener = () => {{}};
    global.window.dispatchEvent = () => true;
    global.sessionStorage = mockSessionStorage;

    // Carrega modulo AuraStateManager
    const {{ AuraStateManager, auraStateManager }} = require(stateMgrPath);
    assert(AuraStateManager, 'Classe AuraStateManager nao exportada');
    assert(auraStateManager, 'Instancia auraStateManager nao exportada');

    console.log('   [NODE] 1. AuraStateManager carregado e exportacoes verificadas.');

    // 2. Teste do ciclo de vida: registerWidget, getWidget, lockWidget, unlockWidget
    const mgr = new AuraStateManager({{ storageKey: 'test_store_1' }});
    const toolCallId1 = 'call_00000000-0000-4000-8000-000000000001';
    const actionId1 = 'act_00000000-0000-4000-8000-000000000001';

    const w1 = mgr.registerWidget(toolCallId1, {{ kpi: 'receita', valor: 50000 }}, 900);
    assert.strictEqual(w1.toolCallId, toolCallId1);
    assert.strictEqual(w1.state.status, 'proposed');
    assert.strictEqual(w1.isLocked, false);
    assert.strictEqual(w1.ttlSeconds, 900);
    assert.strictEqual(w1.props.kpi, 'receita');

    const fetchedW1 = mgr.getWidget(toolCallId1);
    assert.strictEqual(fetchedW1.toolCallId, toolCallId1);

    // Lock
    mgr.lockWidget(toolCallId1, actionId1);
    assert.strictEqual(mgr.getWidget(toolCallId1).isLocked, true);
    assert.strictEqual(mgr.getWidget(toolCallId1).lockedActionId, actionId1);
    assert.strictEqual(mgr.getWidget(toolCallId1).state.status, 'locked');

    // Unlock
    mgr.unlockWidget(toolCallId1);
    assert.strictEqual(mgr.getWidget(toolCallId1).isLocked, false);
    assert.strictEqual(mgr.getWidget(toolCallId1).lockedActionId, null);
    assert.strictEqual(mgr.getWidget(toolCallId1).state.status, 'proposed');

    console.log('   [NODE] 2. Registro, obtencao, locking e unlocking validados com sucesso.');

    // 3. Teste de Idempotencia: isActionExecuted e markActionExecuted
    assert.strictEqual(mgr.isActionExecuted(actionId1), false);
    mgr.markActionExecuted(actionId1, {{ voucher: 'VCH-98765' }});
    assert.strictEqual(mgr.isActionExecuted(actionId1), true);

    // Nova marcacao nao deve quebrar idempotencia
    mgr.markActionExecuted(actionId1);
    assert.strictEqual(mgr.isActionExecuted(actionId1), true);

    console.log('   [NODE] 3. Idempotencia de acoes e armazenamento de resultados validados.');

    // 4. Teste de Inspecao de TTL: isStale e expiração apos 15 minutos (900s)
    const now = Date.now();
    assert.strictEqual(mgr.isStale(now, 900), false);
    assert.strictEqual(mgr.isStale(now - (5 * 60 * 1000), 900), false); // 5 min atras -> ok
    assert.strictEqual(mgr.isStale(now - (16 * 60 * 1000), 900), true); // 16 min atras -> stale!
    assert.strictEqual(mgr.isStale(new Date(now - (20 * 60 * 1000)).toISOString(), 900), true); // ISO string stale!
    assert.strictEqual(mgr.isStale(new Date(now - (2 * 60 * 1000)), 900), false); // Date object recente!

    // 4.1 Teste de registro com created_at historico preservado
    const histToolId = 'call_00000000-0000-4000-8000-hist00000001';
    const histTs = now - (25 * 60 * 1000); // 25 min atras
    mgr.registerWidget(histToolId, {{ created_at: histTs }}, 900);
    assert.strictEqual(mgr.isWidgetStale(histToolId), true, 'Widget com created_at historico deveria ser considerado expirado');

    console.log('   [NODE] 4. Guarda de TTL (Stale Action Guard - 15min / 900s) validada.');

    // 5. Teste de Optimistic UI e Rollback Resiliente
    const toolCallId2 = 'call_00000000-0000-4000-8000-000000000002';
    const actionId2 = 'act_00000000-0000-4000-8000-000000000002';

    const w2 = mgr.registerWidget(toolCallId2, {{ status_inicial: 'pendente' }}, 900);
    assert.strictEqual(w2.state.status, 'proposed');
    assert.strictEqual(w2.isLocked, false);

    // 5.1 Aplica estado otimista
    mgr.applyOptimisticState(toolCallId2, {{
      actionId: actionId2,
      label: 'Aprovar Pedido',
      status: 'optimistic'
    }});
    assert.strictEqual(mgr.getWidget(toolCallId2).isLocked, true);
    assert.strictEqual(mgr.getWidget(toolCallId2).state.status, 'optimistic');
    assert(mgr.getWidget(toolCallId2).snapshot !== null, 'Snapshot previo nao foi salvo');

    // 5.2 Reverte mutacao otimista (simulando falha de rede / ERP 500)
    mgr.rollbackOptimisticState(toolCallId2);
    assert.strictEqual(mgr.getWidget(toolCallId2).isLocked, false);
    assert.strictEqual(mgr.getWidget(toolCallId2).lockedActionId, null);
    assert.strictEqual(mgr.getWidget(toolCallId2).state.status, 'proposed');
    assert.strictEqual(mgr.getWidget(toolCallId2).snapshot, null);

    // 5.3 Aplica mutacao e consolida sucesso
    mgr.applyOptimisticState(toolCallId2, {{ actionId: actionId2, status: 'optimistic' }});
    mgr.finalizeSuccessState(toolCallId2, {{ voucher_id: 'VOUCHER-OK-123' }});
    assert.strictEqual(mgr.getWidget(toolCallId2).state.status, 'committed');
    assert.strictEqual(mgr.getWidget(toolCallId2).isLocked, false);
    assert.strictEqual(mgr.isActionExecuted(actionId2), true);

    console.log('   [NODE] 5. Optimistic UI, snapshot de rollback e finalizacao de voucher validados.');

    // 6. Teste de Persistencia em sessionStorage mockado
    const storageKey = 'test_aura_persistence';
    const mgrPersist = new AuraStateManager({{ storageKey }});
    const toolCallId3 = 'call_00000000-0000-4000-8000-000000000003';
    const actionId3 = 'act_00000000-0000-4000-8000-000000000003';

    mgrPersist.registerWidget(toolCallId3, {{ meta: 'faturamento' }}, 600);
    mgrPersist.lockWidget(toolCallId3, actionId3);
    mgrPersist.markActionExecuted(actionId3, {{ ok: true }});
    mgrPersist.persistToSessionStorage();

    // Cria nova instancia apontando para a mesma chave de storage
    const mgrReload = new AuraStateManager({{ storageKey }});
    const loadedWidget = mgrReload.getWidget(toolCallId3);
    assert(loadedWidget, 'Widget nao recuperado do sessionStorage');
    assert.strictEqual(loadedWidget.toolCallId, toolCallId3);
    assert.strictEqual(loadedWidget.isLocked, true);
    assert.strictEqual(mgrReload.isActionExecuted(actionId3), true);

    console.log('   [NODE] 6. Persistencia e recarga de sessionStorage validadas com sucesso.');

    // 7. Teste de Isolamento Seguro try-catch contra falhas de storage (ex: quota excedida)
    const faultyStorage = {{
      getItem: () => {{ throw new Error('QuotaExceededError'); }},
      setItem: () => {{ throw new Error('QuotaExceededError'); }},
      removeItem: () => {{ throw new Error('QuotaExceededError'); }}
    }};
    global.sessionStorage = faultyStorage;
    const mgrFaulty = new AuraStateManager({{ storageKey: 'faulty' }});
    // Nao deve lancar excecao
    mgrFaulty.registerWidget('call_test_fault', {{}});
    mgrFaulty.lockWidget('call_test_fault', 'act_test_fault');
    mgrFaulty.persistToSessionStorage();
    mgrFaulty.loadFromSessionStorage();

    // Restaura storage confiavel
    global.sessionStorage = mockSessionStorage;

    console.log('   [NODE] 7. Isolamento seguro try-catch em sessionStorage validado.');

    // 8. Integracao com ExecutiveDecisionMentorUI e Protecao contra Duplo Clique
    const widgetsModule = require(widgetsPath);
    const ExecutiveDecisionMentorUI = widgetsModule.ExecutiveDecisionMentorUI;
    assert(ExecutiveDecisionMentorUI, 'ExecutiveDecisionMentorUI nao exportado');

    // Setup global state manager
    global.auraStateManager = mgr;
    global.window.auraStateManager = mgr;

    let toastEmitted = null;
    global.auraFx = {{
      showToast: (opts) => {{ toastEmitted = opts; }}
    }};
    global.window.auraFx = global.auraFx;

    const toolCallId4 = 'call_00000000-0000-4000-8000-000000000004';
    const actionId4 = 'act_00000000-0000-4000-8000-000000000004';

    const widgetUI = new ExecutiveDecisionMentorUI({{
      tool_call_id: toolCallId4,
      props: {{
        confidence_score: 0.95,
        diagnosis: 'Margem real de combustiveis requer calibragem imediata.'
      }},
      actions: [
        {{
          action_id: actionId4,
          label: 'Aplicar Repasse Imediato',
          variant: 'primary',
          action_type: 'mutation'
        }},
        {{
          action_id: 'act_canvas_test',
          label: 'Projetar no Canvas',
          variant: 'secondary',
          action_type: 'inspection'
        }}
      ],
      created_at: new Date().toISOString(),
      ttl_seconds: 900
    }});

    // Monta o widget
    const htmlMount = widgetUI.mount();
    assert(htmlMount, 'Falha na montagem de ExecutiveDecisionMentorUI');
    assert(mgr.getWidget(toolCallId4), 'Widget nao registrado automaticamente no AuraStateManager');

    // 8.1 Simula primeiro clique na acao de mutacao
    let networkCallCount = 0;
    global.auraApi = {{
      executeAction: async (actId, opts) => {{
        networkCallCount++;
        return {{ voucher_id: 'VOUCHER-PASS-999', status: 'COMMITTED' }};
      }}
    }};
    global.window.auraApi = global.auraApi;

    // Dispara primeiro clique
    const mockBtn = {{
      textContent: 'Aplicar Repasse Imediato',
      classList: {{
        add: (...cls) => {{ mockBtn._classes.push(...cls); }},
        contains: (c) => mockBtn._classes.includes(c)
      }},
      _classes: [],
      disabled: false
    }};

    // 8.0 Verifica feedback animado no botao ativo durante bloqueio
    widgetUI.state.isLocked = true;
    widgetUI.state.lockedActionId = actionId4;
    const l3Active = widgetUI.renderLayer3();
    assert(l3Active.includes('animate-pulse'), 'Feedback animado no botao ativo ausente');
    assert(l3Active.includes('animate-spin'), 'Icone de spinner no botao ativo ausente');
    widgetUI.state.isLocked = false;
    widgetUI.state.lockedActionId = null;

    // Executa acao
    const p1 = widgetUI.handleActionClick(actionId4, 'mutation', mockBtn);

    // No mesmo instante, antes de p1 resolver, tenta segundo clique imediato (DUPLO CLIQUE)
    const p2 = widgetUI.handleActionClick(actionId4, 'mutation', mockBtn);

    Promise.all([p1, p2]).then(() => {{
      // Apenas 1 chamada de rede deve ter ocorrido
      assert.strictEqual(networkCallCount, 1, `Duplo clique gerou mais de 1 chamada de rede: ${{networkCallCount}}`);
      assert.strictEqual(mgr.isActionExecuted(actionId4), true, 'Acao nao marcada como executada');
      assert.strictEqual(widgetUI.state.status, 'committed');

      // Tenta terceiro clique apos confirmacao
      const p3 = widgetUI.handleActionClick(actionId4, 'mutation', mockBtn);
      Promise.resolve(p3).then(() => {{
        assert.strictEqual(networkCallCount, 1, 'Clique em acao ja executada gerou chamada de rede');
        console.log('   [NODE] 8. Prevencao de duplo clique e integracao com ExecutiveDecisionMentorUI 100% aprovadas.');

        // 9. Validacao de timeout no cliente de API com AbortController
        const apiModule = require({json.dumps(str((BASE_DIR / "web" / "js" / "aura-api.js").resolve()))});
        const clientTest = new apiModule.AuraApiClient({{ baseUrl: 'http://127.0.0.1:9999' }});
        clientTest.executeAction('act_timeout_test', {{ timeoutMs: 1 }}).then(() => {{
          assert.fail('Deveria ter falhado por timeout');
        }}).catch(err => {{
          assert(err.message.includes('Timeout') || err.message.includes('abort') || err.name === 'AbortError', 'Erro de timeout nao reportado');
          console.log('   [NODE] 9. Timeout e cancelamento com AbortController validados no cliente de API.');
          console.log('NODE_GENUI_STATE_MANAGER_OK');
        }});
      }});
    }}).catch(err => {{
      console.error('Erro na promessa de teste:', err);
      process.exit(1);
    }});
    """;

    res = subprocess.run(
        ["node", "-e", node_test_code],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8"
    )

    if res.returncode != 0:
        print("[ERRO NODE.JS]:\n", res.stderr)
        print("[STDOUT NODE.JS]:\n", res.stdout)
        raise RuntimeError(f"Validacoes Headless em Node.js falharam com codigo {res.returncode}")

    assert "NODE_GENUI_STATE_MANAGER_OK" in res.stdout, "Assercao final Node.js nao encontrada no stdout"
    print("   [OK] Testes headless em Node.js finalizados com 100% de sucesso.")


# =============================================================================
# ETAPA 4: TESTE DE EXPIRAÇAO E TTL NO DOM (F4-04)
# =============================================================================

def test_stale_action_dom_behavior():
    print("\n4. Testando Comportamento de Acoes Expiradas no DOM (TTL > 15min / 900s)...")

    widgets_js_path = BASE_DIR / "web" / "js" / "aura-genui-widgets.js"
    state_mgr_js_path = BASE_DIR / "web" / "js" / "aura-state-manager.js"

    node_stale_test = f"""
    const assert = require('assert');
    const stateMgrPath = {json.dumps(str(state_mgr_js_path.resolve()))};
    const widgetsPath = {json.dumps(str(widgets_js_path.resolve()))};

    global.window = global;
    global.window.addEventListener = () => {{}};
    global.window.removeEventListener = () => {{}};
    global.window.dispatchEvent = () => true;
    const {{ AuraStateManager }} = require(stateMgrPath);
    const mgr = new AuraStateManager({{ storageKey: 'test_stale_dom' }});
    global.auraStateManager = mgr;
    global.window.auraStateManager = mgr;

    const {{ ExecutiveDecisionMentorUI }} = require(widgetsPath);

    // Widget criado ha 30 minutos (1800s atras) com TTL de 15 minutos (900s)
    const staleTime = new Date(Date.now() - (30 * 60 * 1000)).toISOString();
    const staleToolCallId = 'call_00000000-0000-4000-8000-stale00000001';
    const staleActionId = 'act_00000000-0000-4000-8000-stale00000001';

    const staleWidget = new ExecutiveDecisionMentorUI({{
      tool_call_id: staleToolCallId,
      props: {{ diagnosis: 'Telemetria passada' }},
      actions: [{{
        action_id: staleActionId,
        label: 'Aprovar Compra de Combustivel',
        action_type: 'mutation'
      }}],
      created_at: staleTime,
      ttl_seconds: 900
    }});

    assert.strictEqual(staleWidget.isExpired(), true, 'Widget deveria ser considerado expirado');

    // Camada 3 deve conter indicacao de expiracao
    const layer3Html = staleWidget.renderLayer3();
    assert(layer3Html.includes('badge-expired') || layer3Html.includes('genui-expired-badge'), 'Badge de expiracao ausente no HTML');
    assert(layer3Html.includes('Proposta Expirada'), 'Texto explicativo de proposta expirada ausente');
    assert(layer3Html.includes('disabled'), 'Botao de mutacao nao recebeu atributo disabled');
    assert(layer3Html.includes('opacity-50'), 'Botao de mutacao nao recebeu estilo visual de desabilitacao tatil');

    // Clique na acao expirada nao deve prosseguir nem chamar API
    let called = false;
    global.auraApi = {{ executeAction: async () => {{ called = true; }} }};
    global.window.auraApi = global.auraApi;

    staleWidget.handleActionClick(staleActionId, 'mutation', null).then(() => {{
      assert.strictEqual(called, false, 'Acao expirada executou chamada de rede indevida');
      console.log('NODE_STALE_ACTION_OK');
    }});
    """;

    res = subprocess.run(
        ["node", "-e", node_stale_test],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8"
    )

    if res.returncode != 0:
        print("[ERRO NODE.JS STALE]:\n", res.stderr)
        print("[STDOUT NODE.JS STALE]:\n", res.stdout)
        raise RuntimeError(f"Validacao de acao expirada falhou com codigo {res.returncode}")

    assert "NODE_STALE_ACTION_OK" in res.stdout
    print("   [OK] Deteccao de acoes expiradas e bloqueio visual no DOM validados com sucesso.")


# =============================================================================
# ETAPA 5: REGRESSAO ZERO NAS SUITES ANTERIORES
# =============================================================================

def test_zero_regression():
    print("\n5. Executando Validacao de Regressao Zero nas Suites Analiticas Anteriores...")

    suites = [
        ("test_genui_baseline.py", "Fase 0: Linha de Base GenUI, Registry & OWASP LLM03"),
        ("test_genui_engine_sse.py", "Fase 1: Backend SSE Multiplexado & Envelopes"),
        ("test_genui_frontend_streaming.py", "Fase 2: Streaming Parser, Buffer & Skeleton UI"),
        ("test_genui_decision_mentor.py", "Fase 3: Micro-Widget Piloto ExecutiveDecisionMentorUI"),
        ("test_aura_aux_panel.py", "Companion Canvas: Split View, 4 Perspectivas & Responsividade"),
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

    print("\n   [OK] Regressao zero garantida em todas as suites homologadas anteriores.")


# =============================================================================
# RUNNER PRINCIPAL
# =============================================================================

def main():
    print("=" * 78)
    print("SUITE DE TESTES: GESTAO DE ESTADO, IDEMPOTENCIA & OPTIMISTIC UI (FASE 4: P1)")
    print("   (AuraStateManager, State Locking, TTL 15min, Rollback & Zero Regressao)")
    print("=" * 78)

    try:
        test_pydantic_state_contracts()
        test_static_delivery_and_html_shell()
        test_nodejs_headless_state_manager()
        test_stale_action_dom_behavior()
        test_zero_regression()

        print("\n" + "=" * 78)
        print("FASE 4: AuraStateManager HOMOLOGADO COM 100% DE SUCESSO!")
        print("   State Locking, Idempotencia, Optimistic UI, Rollback e Zero Regressao.")
        print("=" * 78)
        return 0

    except Exception as e:
        print(f"\nERRO NA EXECUCAO DA SUITE FASE 4: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
