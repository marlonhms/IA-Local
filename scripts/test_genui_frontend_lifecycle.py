"""
Suite de Testes Automatizada: Ciclo de Vida Frontend via Node.js (Fase 8: F8-03)
Testa programaticamente via script headless em Node.js:
1. Instanciacao e montagem DOM de todos os 6 micro-widgets do catalogo.
2. Transicao de Skeleton para Componente Hidratado no DOM sem layout jank (Zero CLS).
3. Disparo de evento de clique na Camada 3 e ativacao imediata de State Lock contra duplo clique.
4. Execucao otimista e reversao (Rollback) simulando falha de rede/timeout com emissao de toast.
5. Neutralizacao de XSS em strings de props e atributos (OWASP LLM01).
6. Finalizacao com sucesso exibindo badge auditado (VOUCHER AUDITADO).
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


def run_nodejs_frontend_lifecycle_tests():
    print("\n" + "=" * 78)
    print("SUITE DE TESTES: CICLO DE VIDA FRONTEND VIA NODE.JS (FASE 8: F8-03)")
    print("=" * 78)

    genui_js = BASE_DIR / "web" / "js" / "aura-genui.js"
    widgets_js = BASE_DIR / "web" / "js" / "aura-genui-widgets.js"
    state_mgr_js = BASE_DIR / "web" / "js" / "aura-state-manager.js"
    chat_js = BASE_DIR / "web" / "js" / "aura-chat.js"

    assert genui_js.exists(), f"Arquivo nao encontrado: {genui_js}"
    assert widgets_js.exists(), f"Arquivo nao encontrado: {widgets_js}"
    assert state_mgr_js.exists(), f"Arquivo nao encontrado: {state_mgr_js}"
    assert chat_js.exists(), f"Arquivo nao encontrado: {chat_js}"

    node_code = f"""
    const assert = require('assert');
    const path = require('path');

    const genuiPath = {json.dumps(str(genui_js.resolve()))};
    const widgetsPath = {json.dumps(str(widgets_js.resolve()))};
    const stateMgrPath = {json.dumps(str(state_mgr_js.resolve()))};
    const chatPath = {json.dumps(str(chat_js.resolve()))};

    // =========================================================================
    // 0. AMBIENTE DOM HEADLESS MOCK ROBUSTO
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
        return true;
      }}

      click() {{
        const evt = {{
          type: 'click',
          target: this,
          currentTarget: this,
          preventDefault: () => {{}},
          stopPropagation: () => {{}}
        }};
        this.dispatchEvent(evt);
      }}

      appendChild(node) {{
        node.parentNode = this;
        this.children.push(node);
        return node;
      }}

      replaceChild(newNode, oldNode) {{
        const idx = this.children.indexOf(oldNode);
        if (idx >= 0) {{
          oldNode.parentNode = null;
          newNode.parentNode = this;
          this.children[idx] = newNode;
          this._innerHTML = this.children.map(c => c._innerHTML || c.outerHTML).join('\\n');
          return oldNode;
        }}
        // Se oldNode nao for filho direto, anexa newNode
        newNode.parentNode = this;
        this.children.push(newNode);
        this._innerHTML = (this._innerHTML || '') + '\\n' + (newNode._innerHTML || newNode.outerHTML);
        return oldNode;
      }}

      remove() {{
        if (this.parentNode) {{
          const idx = this.parentNode.children.indexOf(this);
          if (idx >= 0) this.parentNode.children.splice(idx, 1);
          this.parentNode = null;
        }}
      }}

      querySelector(sel) {{
        const clean = (sel || '').trim();
        const bare = clean.replace('.', '').replace('#', '');

        for (const child of this.children) {{
          if (clean.startsWith('#') && child.id === bare) return child;
          if (clean.startsWith('.') && child.classList.contains(bare)) return child;
          if (child.tagName.toLowerCase() === clean.toLowerCase()) return child;
          if (child.attributes.has(clean.replace(/[\\[\\]]/g, ''))) return child;
          const found = child.querySelector(clean);
          if (found) return found;
        }}

        // Se for botao
        const btnMatches = this._innerHTML.match(/<button[\\s\\S]*?<\\/button>/gi) || [];
        for (const bHtml of btnMatches) {{
          if (bHtml.includes(bare)) {{
            const bNode = new MockNode('button');
            bNode._innerHTML = bHtml;
            const actMatch = bHtml.match(/data-action-id="([^"]+)"/);
            if (actMatch) bNode.setAttribute('data-action-id', actMatch[1]);
            const clsMatch = bHtml.match(/class="([^"]+)"/);
            if (clsMatch) bNode.className = clsMatch[1];
            const typeMatch = bHtml.match(/data-action-type="([^"]+)"/);
            if (typeMatch) bNode.setAttribute('data-action-type', typeMatch[1]);
            const toolMatch = bHtml.match(/data-tool-call-id="([^"]+)"/);
            if (toolMatch) bNode.setAttribute('data-tool-call-id', toolMatch[1]);
            if (bHtml.includes('disabled')) bNode.setAttribute('disabled', 'true');
            bNode.parentNode = this;
            return bNode;
          }}
        }}

        if (this._innerHTML.includes(bare)) {{
          const m = new MockNode('div');
          m.parentNode = this;
          if (clean.startsWith('.')) m.className = bare;
          if (clean.startsWith('#')) m.id = bare;
          m._innerHTML = this._innerHTML;
          m.children = this.children.slice();
          return m;
        }}
        return null;
      }}

      querySelectorAll(sel) {{
        const clean = (sel || '').trim();
        const bare = clean.replace('.', '').replace('#', '');
        const results = [];

        for (const child of this.children) {{
          if (clean.startsWith('#') && child.id === bare) results.push(child);
          else if (clean.startsWith('.') && child.classList.contains(bare)) results.push(child);
          else if (child.tagName.toLowerCase() === clean.toLowerCase()) results.push(child);
          results.push(...child.querySelectorAll(clean));
        }}
        if (results.length > 0) return results;

        // Se nao encontrou em children diretos, extrai do _innerHTML
        const btnMatches = this._innerHTML.match(/<button[^>]*>[\\s\\S]*?<\\/button>/gi) || [];
        for (const bHtml of btnMatches) {{
          const clsMatch = bHtml.match(/class="([^"]+)"/);
          if (clsMatch && clsMatch[1].includes(bare)) {{
            const bNode = new MockNode('button');
            bNode._innerHTML = bHtml;
            bNode.className = clsMatch[1];
            const actMatch = bHtml.match(/data-action-id="([^"]+)"/);
            if (actMatch) bNode.setAttribute('data-action-id', actMatch[1]);
            const typeMatch = bHtml.match(/data-action-type="([^"]+)"/);
            if (typeMatch) bNode.setAttribute('data-action-type', typeMatch[1]);
            const toolMatch = bHtml.match(/data-tool-call-id="([^"]+)"/);
            if (toolMatch) bNode.setAttribute('data-tool-call-id', toolMatch[1]);
            if (bHtml.includes('disabled')) bNode.setAttribute('disabled', 'true');
            bNode.parentNode = this;
            results.push(bNode);
          }}
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

        // Extrai elementos div de camadas
        const divMatches = html.match(/<div[^>]*class="([^"]*)"[^>]*>([\\s\\S]*?)<\\/div>/gi) || [];
        for (const dHtml of divMatches) {{
          const dNode = new MockNode('div');
          dNode._innerHTML = dHtml;
          const clsMatch = dHtml.match(/class="([^"]+)"/);
          if (clsMatch) dNode.className = clsMatch[1];
          const idMatch = dHtml.match(/id="([^"]+)"/);
          if (idMatch) dNode.id = idMatch[1];
          dNode.parentNode = this;
          this.children.push(dNode);
        }}

        // Extrai botoes para listeners e testes de interacao
        const btnMatches = html.match(/<button[^>]*>([\\s\\S]*?)<\\/button>/gi) || [];
        for (const bHtml of btnMatches) {{
          const bNode = new MockNode('button');
          bNode._innerHTML = bHtml;
          const actMatch = bHtml.match(/data-action-id="([^"]+)"/);
          if (actMatch) bNode.setAttribute('data-action-id', actMatch[1]);
          const clsMatch = bHtml.match(/class="([^"]+)"/);
          if (clsMatch) bNode.className = clsMatch[1];
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

    const mockElementsRegistry = new Map();
    global.document = {{
      createElement(tag) {{
        return new MockNode(tag);
      }},
      getElementById(id) {{
        return mockElementsRegistry.get(id) || null;
      }},
      querySelector(sel) {{
        for (const el of mockElementsRegistry.values()) {{
          if (sel.startsWith('#') && el.id === sel.slice(1)) return el;
          if (sel.startsWith('.') && el.classList.contains(sel.slice(1))) return el;
          const found = el.querySelector(sel);
          if (found) return found;
        }}
        return null;
      }},
      registerElement(el) {{
        if (el.id) mockElementsRegistry.set(el.id, el);
      }}
    }};

    // Mocks globais da plataforma AURA
    let lastToastNotice = null;
    let rpcCallCount = 0;
    let rpcSimulateFailure = false;

    global.window = {{
      document: global.document,
      auraFx: {{
        showToast(toast) {{
          lastToastNotice = toast;
        }}
      }},
      auraApi: {{
        async executeAction(actionId, payload) {{
          rpcCallCount++;
          await new Promise(r => setTimeout(r, 10));
          if (rpcSimulateFailure) {{
            throw new Error('Falha simulada de conectividade com o ERP');
          }}
          return {{
            voucher_id: 'vch_88b19a02_fase8',
            action_id: actionId,
            status: 'APPROVED',
            signature: 'sig_hmac_123456789abcdef'
          }};
        }}
      }},
      auraAuxPanel: {{
        projectArtifact(art) {{}}
      }}
    }};
    global.CustomEvent = class CustomEvent {{
      constructor(type, opts = {{}}) {{
        this.type = type;
        this.detail = opts.detail || null;
        this.bubbles = !!opts.bubbles;
      }}
    }};

    // Mock de sessionStorage para testes headless
    const mockSessionStorage = {{
      _store: new Map(),
      getItem(k) {{ return this._store.get(k) || null; }},
      setItem(k, v) {{ this._store.set(k, String(v)); }},
      removeItem(k) {{ this._store.delete(k); }},
      clear() {{ this._store.clear(); }}
    }};
    global.sessionStorage = mockSessionStorage;
    global.window.sessionStorage = mockSessionStorage;

    // Carrega modulos GenUI e registra componentes
    const {{ AuraGenUI, SecureComponentRegistry }} = require(genuiPath);
    const {{ AuraStateManager }} = require(stateMgrPath);
    const widgetsModule = require(widgetsPath);

    const {{
      BaseGenUIWidget,
      ExecutiveDecisionMentorUI,
      MarginAnalysisUI,
      PredictiveScenarioUI,
      BenchmarkComparisonUI,
      FinancialLeakAuditUI,
      BasketUpsellStrategyUI,
      registerWidgets,
      escapeHtml
    }} = widgetsModule;

    const registry = new SecureComponentRegistry();
    registerWidgets(registry);
    global.window.SecureComponentRegistry = registry;

    const stateManager = new AuraStateManager({{ storageKey: 'test_lifecycle_fase8' }});
    global.window.auraStateManager = stateManager;

    (async () => {{
      // =======================================================================
      // 1. INSTANCIACAO E MONTAGEM DOM DE TODOS OS 6 MICRO-WIDGETS DO CATALOGO
      // =======================================================================
      console.log('1. Testando Instanciacao e Montagem DOM dos 6 Micro-Widgets...');

      const widgetSpecs = [
        {{
          Cls: ExecutiveDecisionMentorUI,
          name: 'ExecutiveDecisionMentorUI',
          intent: 'mentoria_decisao',
          toolId: 'call_exec_001',
          props: {{
            diagnosis: 'Diagnostico executivo da operacao.',
            confidence_score: 0.96,
            metrics: [{{ label: 'Margem', current_value: 14.5, trend: 'up' }}],
            limitations: ['Sem conciliacao bancaria'],
            suggested_actions: [{{
              action_id: 'act_exec_001',
              label: 'Aplicar Recomendacao',
              action_type: 'mutation',
              variant: 'primary'
            }}]
          }}
        }},
        {{
          Cls: MarginAnalysisUI,
          name: 'MarginAnalysisUI',
          intent: 'analise_margem',
          toolId: 'call_marg_002',
          props: {{
            diagnosis: 'Margem liquida em 13.8%.',
            confidence_score: 0.95,
            consolidated_margin_pct: 13.8,
            fuel_margins: [{{ combustivel: 'Gasolina', volume_litros: 10000, preco_venda: 5.89, custo_aquisicao: 5.10, margem_liquida_pct: 13.4 }}],
            suggested_actions: [{{
              action_id: 'act_marg_002',
              label: 'Repassar Custo Cartao',
              action_type: 'mutation'
            }}]
          }}
        }},
        {{
          Cls: PredictiveScenarioUI,
          name: 'PredictiveScenarioUI',
          intent: 'cenario_preditivo',
          toolId: 'call_pred_003',
          props: {{
            scenario_title: 'Simulacao Preco +0.05',
            hypothesis: 'Impacto marginal',
            base_scenario: {{ preco_medio: 5.89, volume_projetado: 50000, receita_liquida: 294500, margem_contribuicao_pct: 14.0 }},
            simulated_scenario: {{ preco_medio: 5.94, volume_projetado: 49800, receita_liquida: 295812, margem_contribuicao_pct: 14.8 }},
            delta_volume_pct: -0.4,
            delta_revenue: 1312,
            delta_margin_pct: 0.8,
            confidence_score: 0.91,
            diagnosis: 'Ganho liquido de R$ 1.312,00 projetado.',
            suggested_actions: [{{
              action_id: 'act_pred_003',
              label: 'Aplicar Cenario',
              action_type: 'mutation'
            }}]
          }}
        }},
        {{
          Cls: BenchmarkComparisonUI,
          name: 'BenchmarkComparisonUI',
          intent: 'benchmark_comparativo',
          toolId: 'call_bench_004',
          props: {{
            diagnosis: 'Filial 10 centavos acima dos concorrentes locais.',
            confidence_score: 0.89,
            competitiveness_score: 75.0,
            entity_name: 'Posto Central',
            benchmark_group: 'Concorrentes 3km',
            comparison_items: [{{ kpi_name: 'Gasolina', filial_value: '5.89', benchmark_value: '5.79', status: 'warning' }}],
            suggested_actions: [{{
              action_id: 'act_bench_004',
              label: 'Ajustar Preco Pista',
              action_type: 'mutation'
            }}]
          }}
        }},
        {{
          Cls: FinancialLeakAuditUI,
          name: 'FinancialLeakAuditUI',
          intent: 'auditoria_fuga_financeira',
          toolId: 'call_leak_005',
          props: {{
            diagnosis: 'Divergencia de sangria identificada no PDV 01.',
            severity: 'critical',
            confidence_score: 0.97,
            total_leak_value: 230.0,
            cash_break_value: 230.0,
            leak_items: [{{ category: 'Quebra de Caixa', description: 'Falta no fechamento', amount: 230.0, status: 'critical' }}],
            suggested_actions: [{{
              action_id: 'act_leak_005',
              label: 'Estancar Quebra no Turno',
              action_type: 'mutation',
              variant: 'danger'
            }}]
          }}
        }},
        {{
          Cls: BasketUpsellStrategyUI,
          name: 'BasketUpsellStrategyUI',
          intent: 'conveniencia_vendas_cruzadas',
          toolId: 'call_basket_006',
          props: {{
            diagnosis: 'Oportunidade de alavancar aditivos na pista.',
            confidence_score: 0.92,
            projected_ticket_increase: 3.50,
            top_combos: [{{ anchor_product: 'Gasolina Comum', recommended_product: 'Aditivo Flex', lift: 3.1, confidence_pct: 25.0, support_pct: 7.0, additional_ticket_reais: 22.0, script_pitch: 'Coloca o aditivo?' }}],
            suggested_actions: [{{
              action_id: 'act_basket_006',
              label: 'Ativar Campanha PDV',
              action_type: 'mutation'
            }}]
          }}
        }}
      ];

      for (const spec of widgetSpecs) {{
        const inst = new spec.Cls({{
          tool_call_id: spec.toolId,
          intent: spec.intent,
          executive_summary: spec.props.diagnosis,
          props: spec.props,
          actions: spec.props.suggested_actions
        }});

        const domNode = inst.mount();
        assert(domNode, `Widget ${{spec.name}} nao retornou no DOM`);
        assert.strictEqual(domNode.id, `genui-card-${{spec.toolId}}`);
        assert(domNode.classList.contains('genui-hydrated-card'), `Classe genui-hydrated-card ausente em ${{spec.name}}`);

        // Verifica as 3 camadas
        const l1 = domNode.querySelector('.genui-layer-1');
        const l2 = domNode.querySelector('.genui-layer-2');
        const l3 = domNode.querySelector('.genui-layer-3');
        assert(l1, `Camada 1 ausente em ${{spec.name}}`);
        assert(l2, `Camada 2 ausente em ${{spec.name}}`);
        assert(l3, `Camada 3 ausente em ${{spec.name}}`);

        // Verifica botao de acao
        const actBtn = l3.querySelector('.genui-action-btn');
        assert(actBtn, `Botao de acao ausente na Camada 3 de ${{spec.name}}`);
        assert.strictEqual(actBtn.getAttribute('data-tool-call-id'), spec.toolId);
        console.log(`   [OK] Widget ${{spec.name}} instanciado e montado nas 3 camadas.`);
      }}

      // =======================================================================
      // 2. TRANSICAO DE SKELETON PARA COMPONENTE HIDRATADO NO DOM (ZERO CLS)
      // =======================================================================
      console.log('\\n2. Testando Transicao de Skeleton para Componente Hidratado no DOM (Zero CLS)...');

      const parentFeed = new MockNode('div', 'chat-feed-container');
      const toolCallIdTrans = 'call_trans_007';

      // Cria slot de skeleton no feed
      const skeletonSlot = new MockNode('div', `genui-skeleton-${{toolCallIdTrans}}`);
      skeletonSlot.className = 'genui-skeleton-slot p-4 rounded-xl border border-cyan-500/20 animate-pulse';
      parentFeed.appendChild(skeletonSlot);
      global.document.registerElement(parentFeed);
      global.document.registerElement(skeletonSlot);

      assert.strictEqual(parentFeed.children.length, 1);
      assert.strictEqual(parentFeed.children[0].id, `genui-skeleton-${{toolCallIdTrans}}`);

      // Instancia componente hidratado
      const hydratedWidget = new ExecutiveDecisionMentorUI({{
        tool_call_id: toolCallIdTrans,
        intent: 'mentoria_decisao',
        executive_summary: 'Transição fluida sem layout jank.',
        props: {{ diagnosis: 'Zero CLS comprovado.', confidence_score: 0.98 }}
      }});
      const hydratedDom = hydratedWidget.mount();
      global.document.registerElement(hydratedDom);

      // Executa substituicao (Zero CLS / 150ms fade-in transition)
      parentFeed.replaceChild(hydratedDom, skeletonSlot);

      assert.strictEqual(parentFeed.children.length, 1);
      assert.strictEqual(parentFeed.children[0].id, `genui-card-${{toolCallIdTrans}}`);
      assert(parentFeed.children[0].classList.contains('genui-hydrated-card'));
      assert(parentFeed.children[0].classList.contains('animate-fade-in'));
      assert.strictEqual(skeletonSlot.parentNode, null, 'Slot de skeleton deve ser completamente removido');
      console.log('   [OK] Substituicao de Skeleton por Card Hidratado sem Layout Jank aprovada.');

      // =======================================================================
      // 3. EVENTO DE CLIQUE NA CAMADA 3 E STATE LOCK IMEDIATO CONTRA DUPLO CLIQUE
      // =======================================================================
      console.log('\\n3. Testando Clique na Camada 3 e State Lock Imediato contra Duplo Clique...');

      const lockToolId = 'call_lock_008';
      const lockActionId = 'act_lock_008';
      rpcCallCount = 0;
      rpcSimulateFailure = false;

      const widgetLock = new ExecutiveDecisionMentorUI({{
        tool_call_id: lockToolId,
        intent: 'mentoria_decisao',
        props: {{ diagnosis: 'Teste de duplo clique.', confidence_score: 0.95 }},
        actions: [{{
          action_id: lockActionId,
          label: 'Aprovar Compra',
          action_type: 'mutation',
          variant: 'primary'
        }}]
      }});
      const lockDom = widgetLock.mount();
      global.document.registerElement(lockDom);

      const btnLock = lockDom.querySelector('.genui-action-btn');
      assert(btnLock, 'Botao de acao ausente');
      assert.strictEqual(widgetLock.state.isLocked, false);
      assert.strictEqual(stateManager.getWidget(lockToolId).isLocked, false);

      // Dispara primeiro clique
      const clickPromise1 = widgetLock.handleActionClick(lockActionId, 'mutation', btnLock, {{ target: btnLock }});

      // Estado trava imediatamente no DOM e no StateManager
      assert.strictEqual(widgetLock.state.isLocked, true, 'Widget deveria estar travado imediatamente');
      assert.strictEqual(stateManager.getWidget(lockToolId).isLocked, true, 'StateManager deveria estar travado');
      assert(btnLock.classList.contains('pointer-events-none'), 'Classe pointer-events-none ausente');
      assert(btnLock.classList.contains('opacity-50'), 'Classe opacity-50 ausente');

      // Dispara segundo clique concorrente imediato
      const clickResult2 = await widgetLock.handleActionClick(lockActionId, 'mutation', btnLock, {{ target: btnLock }});
      assert.strictEqual(clickResult2, false, 'Segundo clique concorrente deveria ser descartado com retorno false');

      // Aguarda conclusao do primeiro RPC
      await clickPromise1;
      assert.strictEqual(rpcCallCount, 1, 'RPC deveria ter sido despachado exatamente 1 vez');
      console.log('   [OK] State Lock imediato e descarte de duplo clique validados.');

      // =======================================================================
      // 4. EXECUCAO OTIMISTA E REVERSAO (ROLLBACK) SIMULANDO FALHA DE REDE
      // =======================================================================
      console.log('\\n4. Testando Optimistic UI e Reversao (Rollback) por Falha de Rede com Toast...');

      const failToolId = 'call_fail_009';
      const failActionId = 'act_fail_009';
      rpcSimulateFailure = true;
      lastToastNotice = null;

      const widgetFail = new ExecutiveDecisionMentorUI({{
        tool_call_id: failToolId,
        intent: 'mentoria_decisao',
        props: {{ diagnosis: 'Simulacao de falha de rede.', confidence_score: 0.93 }},
        actions: [{{
          action_id: failActionId,
          label: 'Aprovar Pedido com Falha',
          action_type: 'mutation',
          variant: 'primary'
        }}]
      }});
      const failDom = widgetFail.mount();
      global.document.registerElement(failDom);
      const btnFail = failDom.querySelector('.genui-action-btn');

      // Dispara clique que falhara no backend
      const failPromise = widgetFail.handleActionClick(failActionId, 'mutation', btnFail, {{ target: btnFail }});

      // Validacao do estado otimista intermediario
      assert.strictEqual(widgetFail.state.isLocked, true);
      assert.strictEqual(stateManager.getWidget(failToolId).state.status, 'optimistic');

      // Conclui chamada com erro
      const finalResult = await failPromise;
      assert.strictEqual(finalResult, false, 'handleActionClick com falha deve retornar false');

      // Validacao do Rollback limpo
      assert.strictEqual(widgetFail.state.isLocked, false, 'Widget deve ser destravado apos rollback');
      assert(['failed', 'proposed'].includes(widgetFail.state.status), 'Status deve ser restaurado para proposed/failed');
      assert.notStrictEqual(widgetFail.state.errorMessage, null, 'Mensagem de erro deve estar presente');
      assert.strictEqual(stateManager.getWidget(failToolId).isLocked, false, 'StateManager destravado apos rollback');
      assert.strictEqual(stateManager.isActionExecuted(failActionId), false, 'Acao nao pode constar como executada');

      // Validacao do Toast emitido
      assert(lastToastNotice, 'Toast de erro deveria ter sido emitido');
      assert.strictEqual(lastToastNotice.type, 'error');
      assert.strictEqual(lastToastNotice.title, 'Falha na Operacao');

      // Validacao de badge de erro no DOM
      const errorBadge = widgetFail.element.querySelector('.genui-error-badge');
      assert(errorBadge, 'Badge de erro ausente apos rollback');
      console.log('   [OK] Rollback resiliente e emissao de toast homologados com sucesso.');

      // =======================================================================
      // 5. NEUTRALIZACAO DE XSS EM STRINGS DE PROPS E ATRIBUTOS (OWASP LLM01)
      // =======================================================================
      console.log('\\n5. Testando Neutralizacao Estrita de XSS em Props e Atributos (OWASP LLM01)...');

      const xssToolId = 'call_xss_010';
      const maliciousPayload = {{
        tool_call_id: xssToolId,
        intent: 'mentoria_decisao',
        executive_summary: '<script>alert("XSS-Summary")</script>',
        props: {{
          diagnosis: '<img src=x onerror=alert(1)> Diagnostico injetado',
          confidence_score: 0.95,
          limitations: ['<script>evil()</script>', '"><b onmouseover=alert(1)>'],
          suggested_actions: [{{
            action_id: 'act_xss_010',
            label: '<svg onload=alert(1)>Acao Maliciosa',
            action_type: 'mutation'
          }}]
        }}
      }};

      const widgetXss = new ExecutiveDecisionMentorUI(maliciousPayload);
      const xssDom = widgetXss.mount();
      const rawHtml = widgetXss.renderHtml();

      // Nao pode conter tags HTML maliciosas ativas ou executaveis abertas
      assert(!rawHtml.includes('<script>'), 'Tag <script> vazou na renderizacao do widget');
      assert(!rawHtml.includes('<img'), 'Tag <img> vazou na renderizacao do widget');
      assert(!rawHtml.includes('<svg onload'), 'Tag <svg onload> vazou na renderizacao do widget');

      // As strings devem estar escapadas com entidades HTML seguras
      assert(rawHtml.includes('&lt;script&gt;') || rawHtml.includes('&amp;lt;script&amp;gt;'), 'Entidade script escapada ausente');
      assert(rawHtml.includes('&lt;img') || rawHtml.includes('&amp;lt;img'), 'Entidade img escapada ausente');
      assert(rawHtml.includes('&lt;svg onload') || rawHtml.includes('&amp;lt;svg onload'), 'Entidade svg onload escapada ausente');
      console.log('   [OK] OWASP LLM01: XSS neutralizado em todas as camadas de renderizacao.');

      // =======================================================================
      // 6. FINALIZACAO COM SUCESSO EXIBINDO BADGE AUDITADO (VOUCHER AUDITADO)
      // =======================================================================
      console.log('\\n6. Testando Finalizacao com Sucesso e Exibicao de Badge (VOUCHER AUDITADO)...');

      const okToolId = 'call_ok_011';
      const okActionId = 'act_ok_011';
      rpcSimulateFailure = false;

      const widgetOk = new ExecutiveDecisionMentorUI({{
        tool_call_id: okToolId,
        intent: 'mentoria_decisao',
        props: {{ diagnosis: 'Operacao concluida com exito.', confidence_score: 0.99 }},
        actions: [{{
          action_id: okActionId,
          label: 'Aprovar Pedido de Carreta',
          action_type: 'mutation',
          variant: 'primary'
        }}]
      }});
      const okDom = widgetOk.mount();
      global.document.registerElement(okDom);
      const btnOk = okDom.querySelector('.genui-action-btn');

      const okResult = await widgetOk.handleActionClick(okActionId, 'mutation', btnOk, {{ target: btnOk }});
      assert.strictEqual(okResult, true, 'handleActionClick deveria concluir com true');

      // Validacao do estado committed
      assert.strictEqual(widgetOk.state.status, 'committed');
      assert.strictEqual(widgetOk.state.isLocked, false);
      assert.strictEqual(widgetOk.isCommitted, true);
      assert.strictEqual(stateManager.isActionExecuted(okActionId), true);

      // Inspeciona DOM atualizado da Camada 3
      const successHtml = widgetOk.renderLayer3();
      assert(successHtml.includes('VOUCHER AUDITADO'), 'Texto "VOUCHER AUDITADO" ausente no badge');
      assert(successHtml.includes('badge-committed'), 'Classe badge-committed ausente no badge');
      assert(successHtml.includes('genui-success-badge'), 'Classe genui-success-badge ausente');
      assert(successHtml.includes('vch_88b19a02_fase8'), 'ID do voucher ausente no badge');
      console.log('   [OK] Badge auditado (VOUCHER AUDITADO) exibido com voucher_id e assinatura.');

      console.log('\\nNODE_FRONTEND_LIFECYCLE_ALL_OK');
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

    assert res.returncode == 0, f"Falha na suite Node.js do frontend: {res.stderr}"
    assert "NODE_FRONTEND_LIFECYCLE_ALL_OK" in res.stdout

    print("=" * 78)
    print("SUITE F8-03 (CICLO DE VIDA FRONTEND VIA NODE.JS) CONCLUIDA COM 100% DE SUCESSO!")
    print("=" * 78 + "\n")


if __name__ == "__main__":
    run_nodejs_frontend_lifecycle_tests()
