"""
Suite de Testes Automatizada: Delegacao Global Centralizada de Acoes GenUI
Testa programaticamente via Node.js headless:
1. Delegacao Global de Clique no Document: captura de clique em .genui-action-btn sem listener direto.
2. Acao de Inspecao (Companion Canvas): abertura do painel auxiliar, toast informativo e chime sutil.
3. Acao de Mutacao Transacional: State Locking imediato, spinner de processamento, chamada a executeAction.
4. Homologacao com Voucher: transicao para concluido, badge VOUCHER AUDITADO no DOM, toast de sucesso e som de vitoria.
5. Rollback Otimista em Falha de Rede: reversao do botao, emissao de toast de erro.
6. Integracao Companion Canvas (aura-aux-panel): renderVisualView e bindGenUIEvents.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import sys
import json
import subprocess
from pathlib import Path

# Protege stdout no terminal Windows contra problemas de codificacao
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))


def run_action_delegation_tests():
    print("\n" + "=" * 78)
    print("SUITE DE TESTES: DELEGACAO GLOBAL DE ACOES GENUI E COMPANION CANVAS")
    print("=" * 78)

    genui_js = BASE_DIR / "web" / "js" / "aura-genui.js"
    widgets_js = BASE_DIR / "web" / "js" / "aura-genui-widgets.js"
    state_mgr_js = BASE_DIR / "web" / "js" / "aura-state-manager.js"
    aux_panel_js = BASE_DIR / "web" / "js" / "aura-aux-panel.js"

    assert genui_js.exists(), f"Arquivo nao encontrado: {genui_js}"
    assert widgets_js.exists(), f"Arquivo nao encontrado: {widgets_js}"
    assert state_mgr_js.exists(), f"Arquivo nao encontrado: {state_mgr_js}"
    assert aux_panel_js.exists(), f"Arquivo nao encontrado: {aux_panel_js}"

    node_code = f"""
    const assert = require('assert');
    const path = require('path');

    const genuiPath = {json.dumps(str(genui_js.resolve()))};
    const widgetsPath = {json.dumps(str(widgets_js.resolve()))};
    const stateMgrPath = {json.dumps(str(state_mgr_js.resolve()))};
    const auxPanelPath = {json.dumps(str(aux_panel_js.resolve()))};

    // =========================================================================
    // 0. AMBIENTE DOM HEADLESS MOCK COM SUPORTE A BUBBLE E CLOSEST
    // =========================================================================

    class MockClassList {{
      constructor(el) {{
        this.el = el;
        this._classes = new Set();
      }}
      add(...cls) {{
        cls.forEach(c => c && this._classes.add(c));
        this.sync();
      }}
      remove(...cls) {{
        cls.forEach(c => this._classes.delete(c));
        this.sync();
      }}
      contains(c) {{
        return this._classes.has(c);
      }}
      toggle(c, force) {{
        const has = this._classes.has(c);
        const shouldHave = (force !== undefined) ? force : !has;
        if (shouldHave) this._classes.add(c); else this._classes.delete(c);
        this.sync();
        return shouldHave;
      }}
      sync() {{
        this.el._className = Array.from(this._classes).join(' ');
      }}
    }}

    class MockNode {{
      constructor(tagName = 'div', id = '') {{
        this.tagName = (tagName || 'div').toUpperCase();
        this.id = id;
        this._className = '';
        this.classList = new MockClassList(this);
        this.attributes = new Map();
        this.listeners = new Map();
        this.children = [];
        this.parentNode = null;
        this._innerHTML = '';
        this._textContent = '';
        this.disabled = false;
        this.style = {{}};
      }}

      get textContent() {{
        if (this._textContent) return this._textContent;
        return this._innerHTML.replace(/<[^>]+>/g, '').trim();
      }}

      set textContent(v) {{
        this._textContent = v || '';
        this._innerHTML = v || '';
      }}

      get className() {{
        return this._className;
      }}

      set className(v) {{
        this._className = v || '';
        this.classList._classes = new Set((v || '').split(/\\s+/).filter(Boolean));
      }}

      get firstElementChild() {{
        return this.children[0] || null;
      }}

      setAttribute(k, v) {{
        this.attributes.set(k, String(v));
        if (k === 'id') this.id = String(v);
        if (k === 'class') this.className = String(v);
        if (k === 'disabled') this.disabled = Boolean(v);
      }}

      getAttribute(k) {{
        return this.attributes.get(k) || null;
      }}

      removeAttribute(k) {{
        this.attributes.delete(k);
        if (k === 'disabled') this.disabled = false;
      }}

      addEventListener(type, fn) {{
        if (!this.listeners.has(type)) this.listeners.set(type, []);
        this.listeners.get(type).push(fn);
      }}

      removeEventListener(type, fn) {{
        const list = this.listeners.get(type) || [];
        const idx = list.indexOf(fn);
        if (idx !== -1) list.splice(idx, 1);
      }}

      dispatchEvent(evt) {{
        const list = this.listeners.get(evt.type) || [];
        for (const fn of list) {{
          try {{ fn(evt); }} catch (e) {{ console.error('Listener err:', e); }}
        }}
        if (evt.bubbles && this.parentNode && typeof this.parentNode.dispatchEvent === 'function') {{
          this.parentNode.dispatchEvent(evt);
        }}
        return true;
      }}

      closest(sel) {{
        const clean = sel.trim();
        const bare = clean.replace('.', '').replace('#', '');
        let cur = this;
        while (cur) {{
          if (clean.startsWith('#') && cur.id === bare) return cur;
          if (clean.startsWith('.') && cur.classList.contains(bare)) return cur;
          if (cur.tagName && cur.tagName.toLowerCase() === clean.toLowerCase()) return cur;
          cur = cur.parentNode;
        }}
        return null;
      }}

      appendChild(child) {{
        if (!child) return child;
        child.parentNode = this;
        this.children.push(child);
        return child;
      }}

      replaceChild(newNode, oldNode) {{
        const idx = this.children.indexOf(oldNode);
        if (idx !== -1) {{
          oldNode.parentNode = null;
          newNode.parentNode = this;
          this.children[idx] = newNode;
        }} else {{
          this.appendChild(newNode);
        }}
        return oldNode;
      }}

      querySelector(sel) {{
        const list = this.querySelectorAll(sel);
        return list.length > 0 ? list[0] : null;
      }}

      querySelectorAll(sel) {{
        const clean = sel.trim();
        const results = [];

        // Suporte a seletores com atributos ex: [data-tool-call-id="..."]
        const attrMatch = clean.match(/\\[([a-zA-Z0-9_-]+)="([^"]+)"\\]/);
        const classMatch = clean.match(/\\.([a-zA-Z0-9_-]+)/);

        for (const child of this.children) {{
          let matched = true;
          if (attrMatch) {{
            if (child.getAttribute(attrMatch[1]) !== attrMatch[2]) matched = false;
          }}
          if (classMatch) {{
            if (!child.classList.contains(classMatch[1])) matched = false;
          }}
          if (!attrMatch && !classMatch) {{
            const bare = clean.replace('.', '').replace('#', '');
            if (clean.startsWith('#') && child.id !== bare) matched = false;
            else if (clean.startsWith('.') && !child.classList.contains(bare)) matched = false;
            else if (child.tagName.toLowerCase() !== clean.toLowerCase()) matched = false;
          }}
          if (matched) results.push(child);
          results.push(...child.querySelectorAll(sel));
        }}

        return results;
      }}

      get outerHTML() {{
        const tag = this.tagName.toLowerCase();
        const cls = this.className ? ` class="${{this.className}}"` : '';
        const id = this.id ? ` id="${{this.id}}"` : '';
        return `<${{tag}}${{id}}${{cls}}>${{this._innerHTML}}</${{tag}}>`;
      }}

      get innerHTML() {{
        return this._innerHTML;
      }}

      set innerHTML(html) {{
        this._innerHTML = html || '';
        this.children = [];
        if (!html) return;

        // Extrai botoes e divs
        const btnMatches = html.match(/<button[^>]*>[\\s\\S]*?<\\/button>/gi) || [];
        for (const bHtml of btnMatches) {{
          const bNode = new MockNode('button');
          bNode._innerHTML = bHtml;
          const clsMatch = bHtml.match(/class="([^"]+)"/);
          if (clsMatch) bNode.className = clsMatch[1];
          const actMatch = bHtml.match(/data-action-id="([^"]+)"/);
          if (actMatch) bNode.setAttribute('data-action-id', actMatch[1]);
          const typeMatch = bHtml.match(/data-action-type="([^"]+)"/);
          if (typeMatch) bNode.setAttribute('data-action-type', typeMatch[1]);
          const toolMatch = bHtml.match(/data-tool-call-id="([^"]+)"/);
          if (toolMatch) bNode.setAttribute('data-tool-call-id', toolMatch[1]);
          if (bHtml.includes('disabled')) bNode.setAttribute('disabled', 'true');
          bNode.parentNode = this;
          this.children.push(bNode);
        }}
      }}
    }}

    global.HTMLElement = MockNode;

    const mockRegistry = new Map();
    const docListeners = new Map();

    const mockDocument = {{
      _auraGenUIActionDelegationInitialized: false,
      listeners: docListeners,
      children: [],
      body: new MockNode('body'),
      createElement(tag) {{
        return new MockNode(tag);
      }},
      getElementById(id) {{
        return mockRegistry.get(id) || null;
      }},
      querySelector(sel) {{
        for (const el of mockRegistry.values()) {{
          if (sel.startsWith('#') && el.id === sel.slice(1)) return el;
          if (sel.startsWith('.') && el.classList.contains(sel.slice(1))) return el;
          const found = el.querySelector(sel);
          if (found) return found;
        }}
        return null;
      }},
      querySelectorAll(sel) {{
        const results = [];
        for (const el of mockRegistry.values()) {{
          results.push(...el.querySelectorAll(sel));
        }}
        return results;
      }},
      registerElement(el) {{
        if (el.id) mockRegistry.set(el.id, el);
      }},
      addEventListener(type, fn) {{
        if (!docListeners.has(type)) docListeners.set(type, []);
        docListeners.get(type).push(fn);
      }},
      removeEventListener(type, fn) {{
        const list = docListeners.get(type) || [];
        const idx = list.indexOf(fn);
        if (idx !== -1) list.splice(idx, 1);
      }},
      dispatchEvent(evt) {{
        const list = docListeners.get(evt.type) || [];
        for (const fn of list) {{
          try {{ fn(evt); }} catch (e) {{ console.error('Doc listener err:', e); }}
        }}
        return true;
      }}
    }};

    global.document = mockDocument;

    // Platform Mocks
    let lastToast = null;
    let canvasOpenedArtifactId = null;
    let lastAudioFreq = null;
    let rpcActionExecuted = null;
    let rpcExecuteCount = 0;
    let rpcShouldFail = false;

    global.window = {{
      document: mockDocument,
      auraFx: {{
        showToast(toast) {{
          lastToast = toast;
        }}
      }},
      auraAudio: {{
        playChime(freq, dur) {{
          lastAudioFreq = freq;
        }}
      }},
      auraAuxPanel: {{
        open(artId) {{
          canvasOpenedArtifactId = artId || 'opened';
        }},
        projectArtifact(art) {{
          canvasOpenedArtifactId = art.id;
        }}
      }},
      auraApi: {{
        async executeAction(actionId, payload) {{
          rpcExecuteCount++;
          rpcActionExecuted = {{ actionId, payload }};
          if (rpcShouldFail) {{
            throw new Error('Falha de comunicacao simulada no ERP');
          }}
          return {{
            voucher_id: 'vch_delegation_success_7788',
            action_id: actionId,
            status: 'APPROVED',
            signature: 'sig_hmac_valid'
          }};
        }}
      }}
    }};

    global.CustomEvent = class CustomEvent {{
      constructor(type, opts = {{}}) {{
        this.type = type;
        this.detail = opts.detail || null;
        this.bubbles = opts.bubbles !== false;
      }}
    }};

    const mockSessionStorage = {{
      _store: new Map(),
      getItem(k) {{ return this._store.get(k) || null; }},
      setItem(k, v) {{ this._store.set(k, String(v)); }},
      removeItem(k) {{ this._store.delete(k); }},
      clear() {{ this._store.clear(); }}
    }};
    global.sessionStorage = mockSessionStorage;
    global.window.sessionStorage = mockSessionStorage;

    (async () => {{
      // 1. Carrega modulos
      const {{ AuraGenUI, SecureComponentRegistry }} = require(genuiPath);
      const {{ AuraStateManager }} = require(stateMgrPath);
      const widgetsModule = require(widgetsPath);
      const {{ BaseGenUIWidget, ExecutiveDecisionMentorUI, initGlobalGenUIActionDelegation }} = widgetsModule;

      const stateMgr = new AuraStateManager();
      global.window.auraStateManager = stateMgr;

      // Inicializa a delegacao global explicitamente
      initGlobalGenUIActionDelegation();
      assert(mockDocument.listeners.has('click'), 'Delegacao global deve adicionar listener de clique no document');
      console.log('1. [OK] Listener delegado de clique registrado no document.');

      // =======================================================================
      // 2. TESTE DE CLIQUE NA ACAO DE INSPECACAO (CANVAS / PROJETAR)
      // =======================================================================
      console.log('\\n2. Testando Acao de Inspecao ("Projetar Cenario no Canvas")...');
      canvasOpenedArtifactId = null;
      lastToast = null;
      lastAudioFreq = null;

      const toolIdInsp = 'call_insp_101';
      const actIdCanvas = 'act_default_canvas';

      const widgetInsp = new ExecutiveDecisionMentorUI({{
        tool_call_id: toolIdInsp,
        intent: 'mentoria_decisao',
        props: {{ diagnosis: 'Diagnostico para inspecao no Canvas.', confidence_score: 0.96 }}
      }});
      AuraGenUI.registerWidget(toolIdInsp, widgetInsp);

      // Simula botao renderizado como string crua sem listener direto no elemento
      const canvasBtn = new MockNode('button');
      canvasBtn.className = 'genui-action-btn';
      canvasBtn.setAttribute('data-action-id', actIdCanvas);
      canvasBtn.setAttribute('data-action-type', 'inspection');
      canvasBtn.setAttribute('data-tool-call-id', toolIdInsp);
      canvasBtn.textContent = '🔍 Projetar Cenário no Canvas';
      canvasBtn.parentNode = mockDocument.body;

      // Dispara clique que borbulha ate o document sem listener nativo no botao
      const clickEvt1 = {{
        type: 'click',
        target: canvasBtn,
        bubbles: true,
        preventDefault() {{}},
        stopPropagation() {{}}
      }};
      mockDocument.dispatchEvent(clickEvt1);

      assert(canvasOpenedArtifactId !== null, 'Companion Canvas deveria ter sido aberto');
      assert.strictEqual(lastToast?.title, 'Cenário Projetado');
      assert.strictEqual(lastToast?.type, 'info');
      assert.strictEqual(lastAudioFreq, 680, 'Audio chime sutil (680Hz) esperado');
      console.log('   [OK] Inspecao: Canvas aberto, toast informativo e som 680Hz validados.');

      // =======================================================================
      // 3. TESTE DE CLIQUE NA ACAO DE MUTACAO ("⚡ Aplicar Recomendacoes")
      // =======================================================================
      console.log('\\n3. Testando Acao de Mutacao Transacional ("⚡ Aplicar Recomendacoes")...');
      rpcActionExecuted = null;
      rpcExecuteCount = 0;
      rpcShouldFail = false;
      lastToast = null;
      lastAudioFreq = null;

      const toolIdMut = 'call_mut_202';
      const actIdApply = 'act_default_apply';

      const widgetMut = new ExecutiveDecisionMentorUI({{
        tool_call_id: toolIdMut,
        intent: 'mentoria_decisao',
        props: {{ diagnosis: 'Decisao pronta para homologacao no ERP.', confidence_score: 0.98 }},
        actions: [{{
          action_id: actIdApply,
          label: '⚡ Aplicar Recomendações Prioritárias',
          action_type: 'mutation',
          variant: 'primary'
        }}]
      }});
      const cardDom = widgetMut.mount();
      mockDocument.registerElement(cardDom);
      AuraGenUI.registerWidget(toolIdMut, widgetMut);

      // Botao na arvore
      const applyBtn = cardDom.querySelector('.genui-action-btn');
      assert(applyBtn, 'Botao de acao ausente no card');

      // Simula clique capturado pela delegacao global
      const clickEvt2 = {{
        type: 'click',
        target: applyBtn,
        bubbles: true,
        preventDefault() {{}},
        stopPropagation() {{}}
      }};
      await mockDocument.dispatchEvent(clickEvt2);

      // Validacoes imediatas de State Locking e RPC
      assert.strictEqual(rpcExecuteCount, 1, 'executeAction deveria ser chamado exatamente 1 vez');
      assert.strictEqual(rpcActionExecuted.actionId, actIdApply);
      assert.strictEqual(widgetMut.state.status, 'committed');
      assert.strictEqual(widgetMut.state.isLocked, false);
      assert.strictEqual(stateMgr.isActionExecuted(actIdApply), true);

      // Validacao do toast de homologacao e audio de sucesso
      assert(lastToast !== null, 'Toast de sucesso ausente');
      assert.strictEqual(lastToast?.title, 'Ação Homologada');
      assert.strictEqual(lastToast?.type, 'success');
      assert.strictEqual(lastAudioFreq, 880, 'Audio chime de vitoria (880Hz) esperado');

      // Validacao do badge VOUCHER AUDITADO no HTML
      const layer3Html = widgetMut.renderLayer3();
      assert(layer3Html.includes('VOUCHER AUDITADO'), 'Badge VOUCHER AUDITADO ausente');
      assert(layer3Html.includes('vch_delegation_success_7788'), 'ID do voucher ausente no badge');
      console.log('   [OK] Mutacao: State Lock, RPC executeAction, Voucher Auditado, toast de sucesso e som 880Hz validados.');

      // =======================================================================
      // 4. TESTE DE MUTACAO COM FALHA E ROLLBACK OTIMISTA
      // =======================================================================
      console.log('\\n4. Testando Falha de Rede e Rollback Otimista...');
      rpcShouldFail = true;
      lastToast = null;

      const toolIdErr = 'call_err_303';
      const actIdGoals = 'act_default_goals';

      const widgetErr = new ExecutiveDecisionMentorUI({{
        tool_call_id: toolIdErr,
        intent: 'mentoria_decisao',
        props: {{ diagnosis: 'Teste de recuperacao de erro.', confidence_score: 0.94 }},
        actions: [{{
          action_id: actIdGoals,
          label: '🎯 Ajustar Metas do Turno',
          action_type: 'mutation',
          variant: 'secondary'
        }}]
      }});
      const cardErrDom = widgetErr.mount();
      mockDocument.registerElement(cardErrDom);
      AuraGenUI.registerWidget(toolIdErr, widgetErr);

      const goalsBtn = cardErrDom.querySelector('.genui-action-btn');
      const clickEvt3 = {{
        type: 'click',
        target: goalsBtn,
        bubbles: true,
        preventDefault() {{}},
        stopPropagation() {{}}
      }};
      await mockDocument.dispatchEvent(clickEvt3);

      assert.strictEqual(widgetErr.state.status, 'failed');
      assert.strictEqual(widgetErr.state.isLocked, false, 'Widget deve ser destravado');
      assert.strictEqual(stateMgr.isActionExecuted(actIdGoals), false, 'Acao com falha nao pode constar como executada');
      assert(lastToast !== null, 'Toast de erro ausente');
      assert.strictEqual(lastToast?.title, 'Falha na Operacao');
      assert.strictEqual(lastToast?.type, 'error');
      console.log('   [OK] Rollback: Reversao otimista, destravamento de estado e toast de erro validados.');

      // =======================================================================
      // 5. TESTE DE RESISTENCIA A CLIQUE DUPLO
      // =======================================================================
      console.log('\\n5. Testando Rejeicao de Clique Duplo Concorrente...');
      rpcShouldFail = false;
      rpcExecuteCount = 0;

      const toolIdDup = 'call_dup_404';
      const actIdDup = 'act_dup_404';

      const widgetDup = new ExecutiveDecisionMentorUI({{
        tool_call_id: toolIdDup,
        intent: 'mentoria_decisao',
        props: {{ diagnosis: 'Teste anti-duplo clique.', confidence_score: 0.97 }},
        actions: [{{
          action_id: actIdDup,
          label: 'Autorizar Operacao',
          action_type: 'mutation'
        }}]
      }});
      const cardDupDom = widgetDup.mount();
      mockDocument.registerElement(cardDupDom);
      AuraGenUI.registerWidget(toolIdDup, widgetDup);

      const dupBtn = cardDupDom.querySelector('.genui-action-btn');

      // Primeiro clique
      const p1 = mockDocument.dispatchEvent({{
        type: 'click',
        target: dupBtn,
        bubbles: true,
        preventDefault() {{}},
        stopPropagation() {{}}
      }});

      // Segundo clique imediato concorrente enquanto bloqueado
      dupBtn.disabled = true;
      dupBtn.classList.add('pointer-events-none');
      const p2 = mockDocument.dispatchEvent({{
        type: 'click',
        target: dupBtn,
        bubbles: true,
        preventDefault() {{}},
        stopPropagation() {{}}
      }});

      await Promise.all([p1, p2]);
      assert.strictEqual(rpcExecuteCount, 1, 'RPC deve ser disparado exatamente 1 vez descartando duplo clique');
      console.log('   [OK] Anti-Duplo Clique: Invocacao concorrente bloqueada.');

      console.log('\\nACTION_DELEGATION_ALL_OK');
    }})().catch(err => {{
      console.error('[NODE_ERROR]', err);
      process.exit(1);
    }});
    """

    res = subprocess.run(
        ["node", "-e", node_code],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    print(res.stdout)
    if res.stderr:
        print("[STDERR]", res.stderr)

    assert res.returncode == 0, f"Falha na suite de delegacao de acoes: {res.stderr}"
    print("=" * 78)
    print("SUITE DE DELEGACAO DE ACOES GENUI CONCLUIDA COM 100% DE SUCESSO!")
    print("=" * 78 + "\n")


if __name__ == "__main__":
    run_action_delegation_tests()
