"""
Suíte de Testes Automatizada: Streaming Parser, Bufferização JSON & Skeleton UI (Fase 2 — P0)
(AuraApiClient, AuraChatController, GenUIFragmentBuffer, Ciclo de Vida DOM e Zero Regressão)

Validações Obrigatórias:
1. Validação estática de contratos e arquivos do frontend:
   - Exportação CommonJS e Singleton de AuraApiClient em web/js/aura-api.js.
   - Presença de streamChat e chatStream suportando onDelta, onSkeleton, onUIDelta, onUIComplete, onActionFeedback, onChunk, onDone, onError.
   - Presença e exportação de GenUIFragmentBuffer em web/js/aura-genui.js.
   - Métodos de ciclo de vida GenUI em web/js/aura-chat.js (handleUISkeleton, handleUIDelta, handleUIComplete, handleUIActionFeedback, cleanupSkeletonSlots).
   - Classes CSS Precision Glass em web/css/aura.css (.genui-skeleton-slot, .genui-hydrated-card, .genui-fade-in, genuiFadeIn 150ms).
2. Validação Headless em Node.js (F2-01 & F2-02):
   - Buffer de fragmentos JSON volátil: parsing tolerante com silent try/catch e montagem de estruturas complexas.
   - Parser de streaming SSE multiplexado em streamChat: despacho de onSkeleton, onDelta, onUIDelta, onUIComplete, onActionFeedback, onDone.
   - Garantia de que tokens de texto fluem limpos e em tempo real via onDelta sem atrasos.
3. Validação do Ciclo de Vida no DOM (F2-03 & F2-04):
   - Injeção do SkeletonPulse (genui-skeleton-[tool_call_id]) com micro-copy contextual da etapa e classes AURA Precision Glass.
   - Hidratação instantânea (Zero CLS) substituindo o esqueleto por componente registrado via SecureComponentRegistry (ou fallback gracioso).
   - Remoção graciosa de esqueletos órfãos em caso de término (done) ou erro sem emissão de ui_complete.
4. Validação de Regressão Zero:
   - Execução das 4 suítes analíticas homologadas:
     * test_genui_baseline.py (Fase 0)
     * test_genui_engine_sse.py (Fase 1)
     * test_aura_aux_panel.py (Companion Canvas)
     * test_phase6_quality_resilience.py (Resiliência & WCAG)
"""

import sys
import json
import re
import subprocess
from pathlib import Path

# Protege stdout no terminal Windows contra problemas de codificação
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent


def test_static_contracts_and_exports():
    print("\n1. Verificando Asserções Estáticas de Contratos e Módulos do Frontend...")

    api_js_path = BASE_DIR / "web" / "js" / "aura-api.js"
    genui_js_path = BASE_DIR / "web" / "js" / "aura-genui.js"
    chat_js_path = BASE_DIR / "web" / "js" / "aura-chat.js"
    css_path = BASE_DIR / "web" / "css" / "aura.css"

    assert api_js_path.exists(), f"Arquivo não encontrado: {api_js_path}"
    assert genui_js_path.exists(), f"Arquivo não encontrado: {genui_js_path}"
    assert chat_js_path.exists(), f"Arquivo não encontrado: {chat_js_path}"
    assert css_path.exists(), f"Arquivo não encontrado: {css_path}"

    api_js = api_js_path.read_text(encoding="utf-8")
    genui_js = genui_js_path.read_text(encoding="utf-8")
    chat_js = chat_js_path.read_text(encoding="utf-8")
    css = css_path.read_text(encoding="utf-8")

    # 1.1 aura-api.js
    assert "class AuraApiClient" in api_js, "AuraApiClient não encontrado em aura-api.js"
    assert "async streamChat" in api_js, "Método streamChat não encontrado em aura-api.js"
    assert "async chatStream" in api_js, "Método chatStream não encontrado em aura-api.js"
    assert "onSkeleton" in api_js, "Callback onSkeleton não suportado em streamChat"
    assert "onUIDelta" in api_js, "Callback onUIDelta não suportado em streamChat"
    assert "onUIComplete" in api_js, "Callback onUIComplete não suportado em streamChat"
    assert "onActionFeedback" in api_js, "Callback onActionFeedback não suportado em streamChat"
    assert "onDelta" in api_js, "Callback onDelta não suportado em streamChat"
    assert "fragmentBuffer" in api_js or "GenUIFragmentBuffer" in api_js or "jsonBuffers" in api_js, "Buffer de deltas ausente em aura-api.js"
    assert "module.exports" in api_js, "Exportação CommonJS ausente em aura-api.js"

    # 1.2 aura-genui.js
    assert "class GenUIFragmentBuffer" in genui_js, "GenUIFragmentBuffer ausente em aura-genui.js"
    assert "GenUIFragmentBuffer" in genui_js, "GenUIFragmentBuffer não exportado em AuraGenUI"

    # 1.3 aura-chat.js
    assert "handleUISkeleton" in chat_js, "handleUISkeleton ausente em aura-chat.js"
    assert "handleUIDelta" in chat_js, "handleUIDelta ausente em aura-chat.js"
    assert "handleUIComplete" in chat_js, "handleUIComplete ausente em aura-chat.js"
    assert "cleanupSkeletonSlots" in chat_js, "cleanupSkeletonSlots ausente em aura-chat.js"
    assert "renderCanonicalFallbackCard" in chat_js, "renderCanonicalFallbackCard ausente em aura-chat.js"
    assert "genui-skeleton-slot" in chat_js, "Classe genui-skeleton-slot ausente em aura-chat.js"
    assert "genui-hydrated-card" in chat_js, "Classe genui-hydrated-card ausente em aura-chat.js"

    # 1.4 aura.css
    assert ".genui-skeleton-slot" in css, "Classe .genui-skeleton-slot ausente em aura.css"
    assert ".genui-hydrated-card" in css, "Classe .genui-hydrated-card ausente em aura.css"
    assert ".genui-fade-in" in css or "genuiFadeIn" in css, "Animação genuiFadeIn ausente em aura.css"
    assert "150ms" in css, "Transição suave de 150ms ausente em aura.css"
    assert "prefers-reduced-motion" in css, "Suporte a movimento reduzido (WCAG 2.1 AA) ausente em aura.css"

    print("   [OK] Contratos estáticos, classes de suporte e exportações validadas com sucesso.")


def test_nodejs_headless_streaming_and_dom():
    print("\n2. Executando Validações Headless em Node.js (Parser SSE, Buffer & Ciclo de Vida)...")

    genui_js_path = BASE_DIR / "web" / "js" / "aura-genui.js"
    api_js_path = BASE_DIR / "web" / "js" / "aura-api.js"
    chat_js_path = BASE_DIR / "web" / "js" / "aura-chat.js"

    node_script = f"""
    const path = require('path');
    const assert = require('assert');

    const genuiPath = {json.dumps(str(genui_js_path.resolve()))};
    const apiPath = {json.dumps(str(api_js_path.resolve()))};
    const chatPath = {json.dumps(str(chat_js_path.resolve()))};

    const {{ AuraGenUI, SecureComponentRegistry, GenUIFragmentBuffer }} = require(genuiPath);
    const {{ AuraApiClient }} = require(apiPath);
    const {{ AuraChatController }} = require(chatPath);

    (async () => {{
      // =========================================================================
      // ETAPA 1: TESTE UNITÁRIO DE GENUI FRAGMENT BUFFER (F2-02)
      // =========================================================================
      console.log('[NODE] 1. Testando GenUIFragmentBuffer (Bufferização & Fallback Silencioso)...');
      const buf = new GenUIFragmentBuffer();

      // 1.1 Append inválido
      assert.strictEqual(buf.append(null, '{{}}'), null, 'Append com toolCallId nulo deve retornar null');

      // 1.2 Chunk parcial incompleto (silent try/catch)
      const chunk1 = buf.append('call_abc', '{{"tanque": "01",');
      assert.strictEqual(chunk1.tool_call_id, 'call_abc');
      assert.strictEqual(chunk1.parsed, null, 'JSON incompleto deve resultar em parsed === null');
      assert.strictEqual(chunk1.isComplete, false, 'isComplete deve ser false para fragmento parcial');
      assert.strictEqual(buf.get('call_abc'), '{{"tanque": "01",');

      // 1.3 Segundo chunk completando a estrutura
      const chunk2 = buf.append('call_abc', ' "litros": 4200}}');
      assert.notStrictEqual(chunk2.parsed, null, 'JSON completo deve ser desserializado com sucesso');
      assert.strictEqual(chunk2.isComplete, true);
      assert.strictEqual(chunk2.parsed.tanque, '01');
      assert.strictEqual(chunk2.parsed.litros, 4200);

      // 1.4 Isolamento de múltiplos tool_call_id
      buf.append('call_xyz', '{{"status": "ok"}}');
      assert.strictEqual(buf.getParsed('call_xyz').status, 'ok');
      assert.strictEqual(buf.getParsed('call_abc').tanque, '01');

      // 1.5 Limpeza específica e total
      buf.clear('call_abc');
      assert.strictEqual(buf.get('call_abc'), '');
      assert.strictEqual(buf.getParsed('call_xyz').status, 'ok');
      buf.clear();
      assert.strictEqual(buf.get('call_xyz'), '');
      console.log('[NODE]    ✓ GenUIFragmentBuffer aprovado com tolerância e isolamento estrito.');

      // =========================================================================
      // ETAPA 2: TESTE DO PARSER SSE MULTIPLEXADO EM AuraApiClient (F2-01)
      // =========================================================================
      console.log('[NODE] 2. Testando Parser SSE Multiplexado em AuraApiClient.streamChat()...');

      async function testStreamParser() {{
      const client = new AuraApiClient('http://localhost:8000');

      // Monta stream SSE sintético simulando a sequência formal
      const sseChunks = [
        'event: intent\\ndata: {{"chunk_type": "intent", "intent": "previsao_tanques"}}\\n\\n',
        'event: ui_skeleton\\ndata: {{"chunk_type": "ui_skeleton", "tool_call_id": "call_mock_1", "component_name": "render_TankRunOutForecastUI", "title": "Analisando Autonomia de Tanques..."}}\\n\\n',
        'event: delta\\ndata: {{"chunk_type": "delta", "text": "Tanque 01 "}}\\n\\n',
        'event: delta\\ndata: {{"chunk_type": "delta", "text": "com autonomia crítica."}}\\n\\n',
        'event: ui_delta\\ndata: {{"chunk_type": "ui_delta", "tool_call_id": "call_mock_1", "delta_json": "{{\\\\"tanque\\\\": \\\\"01\\\\","}}\\n\\n',
        'event: ui_delta\\ndata: {{"chunk_type": "ui_delta", "tool_call_id": "call_mock_1", "delta_json": " \\\\"saldo\\\\": 4200}}"}}' + '\\n\\n',
        'event: ui_complete\\ndata: {{"chunk_type": "ui_complete", "tool_call_id": "call_mock_1", "component_name": "render_TankRunOutForecastUI", "envelope": {{"schema_version": "1.0", "tool_call_id": "call_mock_1", "component_name": "render_TankRunOutForecastUI", "intent": "tank_forecast", "executive_summary": "Tanque 01 com autonomia crítica.", "props": {{"tanque": "01", "saldo": 4200}}, "actions": [{{"action_id": "act_mock_1", "label": "Pedir Carreta"}}]}}}}\\n\\n',
        'event: ui_action_feedback\\ndata: {{"chunk_type": "ui_action_feedback", "tool_call_id": "call_mock_1", "action_id": "act_mock_1", "status": "COMMITTED", "voucher_id": "vch_12345"}}\\n\\n',
        'event: done\\ndata: [DONE]\\n\\n'
      ];

      // Mock de global fetch com ReadableStream nativo do Node 18+
      const encoder = new TextEncoder();
      const mockStream = new ReadableStream({{
        start(controller) {{
          for (const c of sseChunks) {{
            controller.enqueue(encoder.encode(c));
          }}
          controller.close();
        }}
      }});

      global.fetch = async () => ({{
        ok: true,
        status: 200,
        body: mockStream
      }});

      let deltaTextAccum = '';
      let receivedSkeleton = null;
      let uiDeltaCount = 0;
      let finalUIDeltaParsed = null;
      let receivedComplete = null;
      let receivedFeedback = null;
      let doneFired = false;
      const allChunks = [];

      await client.streamChat({{
        query: 'Como estão os tanques?',
        sessionId: 'sess_test_node',
        onDelta: (text) => {{
          deltaTextAccum += text;
        }},
        onSkeleton: (skel) => {{
          receivedSkeleton = skel;
        }},
        onUIDelta: (delta) => {{
          uiDeltaCount++;
          if (delta.parsed) {{
            finalUIDeltaParsed = delta.parsed;
          }}
        }},
        onUIComplete: (env) => {{
          receivedComplete = env;
        }},
        onActionFeedback: (fb) => {{
          receivedFeedback = fb;
        }},
        onChunk: (chunk) => {{
          allChunks.push(chunk);
        }},
        onDone: () => {{
          doneFired = true;
        }}
      }});

      assert.strictEqual(doneFired, true, 'onDone deve ser disparado');
      assert.strictEqual(deltaTextAccum, 'Tanque 01 com autonomia crítica.', 'Tokens delta concatenados corretamente');
      assert.notStrictEqual(receivedSkeleton, null, 'onSkeleton deve ser acionado');
      assert.strictEqual(receivedSkeleton.tool_call_id, 'call_mock_1');
      assert.strictEqual(receivedSkeleton.component_name, 'render_TankRunOutForecastUI');

      assert.strictEqual(uiDeltaCount, 2, 'Dois chunks de ui_delta devem ser recebidos');
      assert.notStrictEqual(finalUIDeltaParsed, null, 'Buffer de ui_delta deve ter parseado com sucesso ao final');
      assert.strictEqual(finalUIDeltaParsed.tanque, '01');
      assert.strictEqual(finalUIDeltaParsed.saldo, 4200);

      assert.notStrictEqual(receivedComplete, null, 'onUIComplete deve receber o envelope consolidado');
      assert.strictEqual(receivedComplete.tool_call_id, 'call_mock_1');
      assert.strictEqual(receivedComplete.props.saldo, 4200);

      assert.notStrictEqual(receivedFeedback, null, 'onActionFeedback deve ser processado');
      assert.strictEqual(receivedFeedback.status, 'COMMITTED');
      assert.strictEqual(receivedFeedback.voucher_id, 'vch_12345');

      assert.strictEqual(allChunks.length, 8, 'Todos os 8 chunks SSE multiplexados devem ter sido notificados');
    }}

    await testStreamParser();
    console.log('[NODE]    ✓ streamChat() multiplexado validado com sucesso total.');

    // 2.2 Teste de Fragmentação TCP entre 'event:' e 'data:'
    async function testStreamFragmentation() {{
      const client = new AuraApiClient('http://localhost:8000');
      const encoder = new TextEncoder();
      const fragChunks = [
        'event: ui_skeleton\\n',
        'data: {{"chunk_type": "ui_skeleton", "tool_call_id": "call_frag_1", "component_name": "TankWidget"}}\\n\\n',
        'data: [DONE]\\n\\n'
      ];
      global.fetch = async () => ({{
        ok: true,
        status: 200,
        body: new ReadableStream({{
          start(c) {{
            for (const ch of fragChunks) c.enqueue(encoder.encode(ch));
            c.close();
          }}
        }})
      }});

      let fragSkeleton = null;
      let fragDelta = null;
      await client.streamChat({{
        query: 'teste frag',
        onSkeleton: (skel) => {{ fragSkeleton = skel; }},
        onDelta: (text, chunk) => {{ fragDelta = {{ text, chunk }}; }}
      }});

      assert.notStrictEqual(fragSkeleton, null, 'Skeleton deve ser recebido mesmo com quebra de pacote TCP entre event e data');
      assert.strictEqual(fragSkeleton.tool_call_id, 'call_frag_1');
      assert.strictEqual(fragDelta, null, 'Skeleton fragmentado não pode vazar como token de texto delta');
    }}
    await testStreamFragmentation();
    console.log('[NODE]    ✓ Parser SSE resiliente a fragmentação de pacotes TCP aprovado.');

    // 2.3 Teste de SSE com apenas 'data:' (sem header 'event:')
    async function testStreamNoEventHeader() {{
      const client = new AuraApiClient('http://localhost:8000');
      const encoder = new TextEncoder();
      const noEventChunks = [
        'data: {{"chunk_type": "ui_skeleton", "tool_call_id": "call_no_evt", "component_name": "TankWidget"}}\\n\\n',
        'data: [DONE]\\n\\n'
      ];
      global.fetch = async () => ({{
        ok: true,
        status: 200,
        body: new ReadableStream({{
          start(c) {{
            for (const ch of noEventChunks) c.enqueue(encoder.encode(ch));
            c.close();
          }}
        }})
      }});

      let noEvtSkeleton = null;
      let noEvtDelta = null;
      await client.streamChat({{
        query: 'teste sem event',
        onSkeleton: (skel) => {{ noEvtSkeleton = skel; }},
        onDelta: (text, chunk) => {{ noEvtDelta = {{ text, chunk }}; }}
      }});

      assert.notStrictEqual(noEvtSkeleton, null, 'chunk_type no payload JSON deve prevalecer mesmo sem header event');
      assert.strictEqual(noEvtSkeleton.tool_call_id, 'call_no_evt');
      assert.strictEqual(noEvtDelta, null, 'Skeleton sem event header não pode ser tratado como texto delta');
    }}
    await testStreamNoEventHeader();
    console.log('[NODE]    ✓ Parser SSE com resolução canônica por chunk_type aprovado.');

    // =========================================================================
    // ETAPA 3: TESTE DE CICLO DE VIDA DO DOM (SKELETON, HYDRATE & CLEANUP)
    // =========================================================================
    console.log('[NODE] 3. Testando Ciclo de Vida no DOM em AuraChatController (F2-03 & F2-04)...');

    class MockClassList {{
      constructor(el) {{
        this._el = el;
        this._classes = new Set();
      }}
      add(...classes) {{
        for (const c of classes) {{
          if (c) this._classes.add(c);
        }}
        this._el._className = Array.from(this._classes).join(' ');
      }}
      remove(...classes) {{
        for (const c of classes) {{
          this._classes.delete(c);
        }}
        this._el._className = Array.from(this._classes).join(' ');
      }}
      contains(cls) {{
        return this._classes.has(cls);
      }}
    }}

    class MockElement {{
      constructor(tagName, id = '') {{
        this.tagName = (tagName || 'div').toUpperCase();
        this.id = id;
        this._className = '';
        this.classList = new MockClassList(this);
        this.children = [];
        this.parentNode = null;
        this._innerHTML = '';
        this.style = {{}};
        this.attributes = new Map();
      }}

      get className() {{
        return this._className;
      }}

      set className(val) {{
        this._className = val || '';
        this.classList._classes = new Set(this._className.split(/\\s+/).filter(Boolean));
      }}

      get innerHTML() {{
        return this._innerHTML;
      }}

      set innerHTML(val) {{
        this._innerHTML = val || '';
        this.children = [];
        if (typeof val === 'string') {{
          const matchId = val.match(/id="([^"]+)"/);
          const childId = matchId ? matchId[1] : '';
          const matchClass = val.match(/class="([^"]+)"/);
          const childClass = matchClass ? matchClass[1] : '';
          if (childId || childClass) {{
            const child = new MockElement('div', childId);
            child.className = childClass;
            child._innerHTML = val;
            this.appendChild(child);
          }}
        }}
      }}

      get outerHTML() {{
        const clsAttr = this.className ? ` class="${{this.className}}"` : '';
        const idAttr = this.id ? ` id="${{this.id}}"` : '';
        return `<${{this.tagName.toLowerCase()}}${{idAttr}}${{clsAttr}}>${{this._innerHTML}}</${{this.tagName.toLowerCase()}}>`;
      }}

      appendChild(node) {{
        node.parentNode = this;
        this.children.push(node);
        if (node.id) mockElementsById.set(node.id, node);
        return node;
      }}

      replaceChild(newNode, oldNode) {{
        const idx = this.children.indexOf(oldNode);
        if (idx !== -1) {{
          newNode.parentNode = this;
          oldNode.parentNode = null;
          this.children[idx] = newNode;
          if (newNode.id) mockElementsById.set(newNode.id, newNode);
          if (oldNode.id) mockElementsById.delete(oldNode.id);
          this._innerHTML = this.children.map(c => c.outerHTML).join('');
          return oldNode;
        }}
        return null;
      }}

      remove() {{
        if (this.parentNode) {{
          const idx = this.parentNode.children.indexOf(this);
          if (idx !== -1) {{
            this.parentNode.children.splice(idx, 1);
          }}
          if (this.id) mockElementsById.delete(this.id);
          this.parentNode = null;
        }}
      }}

      querySelector(sel) {{
        for (const c of this.children) {{
          if (sel.startsWith('#') && c.id === sel.slice(1)) return c;
          if (sel.startsWith('.') && c.classList.contains(sel.slice(1))) return c;
          if (sel.includes('.genui-skeleton-slot') && c.classList.contains('genui-skeleton-slot')) return c;
          const found = c.querySelector(sel);
          if (found) return found;
        }}
        return null;
      }}

      querySelectorAll(sel) {{
        const res = [];
        for (const c of this.children) {{
          if (sel.startsWith('.') && c.classList.contains(sel.slice(1))) res.push(c);
          res.push(...c.querySelectorAll(sel));
        }}
        return res;
      }}

      setAttribute(k, v) {{
        this.attributes.set(k, String(v));
      }}

      getAttribute(k) {{
        return this.attributes.get(k) || null;
      }}
    }}

    const mockElementsById = new Map();

    const mockDocument = {{
      createElement(tag) {{
        return new MockElement(tag);
      }},
      getElementById(id) {{
        return mockElementsById.get(id) || null;
      }},
      querySelector(sel) {{
        if (sel.startsWith('#')) {{
          const cleanId = sel.slice(1).split(' ')[0].split('.')[0].split('#')[0];
          const el = mockElementsById.get(cleanId);
          if (el) {{
            const rest = sel.slice(cleanId.length + 1).trim();
            if (!rest) return el;
            return el.querySelector(rest);
          }}
        }}
        for (const el of mockElementsById.values()) {{
          const found = el.querySelector(sel);
          if (found) return found;
        }}
        return null;
      }},
      querySelectorAll(sel) {{
        const found = [];
        for (const el of mockElementsById.values()) {{
          if (sel.includes('.genui-skeleton-slot')) {{
            if (el.className && el.className.includes('genui-skeleton-slot')) found.push(el);
          }}
          found.push(...el.querySelectorAll(sel));
        }}
        return Array.from(new Set(found));
      }}
    }};

    global.document = mockDocument;
    global.HTMLElement = MockElement;
    global.window = {{
      document: mockDocument,
      SecureComponentRegistry: new SecureComponentRegistry(),
      AuraGenUI: AuraGenUI,
      auraApi: new AuraApiClient('http://localhost:8000'),
    }};

    const chatCtrl = new AuraChatController();

    // 3.1 Criação do container de mensagem da AURA
    const containerId = 'aura-msg-12345';
    const msgBox = new MockElement('div', containerId);
    const toolCard = new MockElement('div', containerId + '-tool-card');
    toolCard.classList.add('hidden');
    msgBox.appendChild(toolCard);

    mockElementsById.set(containerId, msgBox);
    mockElementsById.set(containerId + '-tool-card', toolCard);

    // 3.2 Injeção de Skeleton UI Reativo (F2-03)
    chatCtrl.handleUISkeleton(containerId, {{
      tool_call_id: 'call_test_skel',
      component_name: 'render_TankRunOutForecastUI',
      title: 'Consultando volumetria dos tanques...'
    }});

    const skelSlot = mockDocument.getElementById('genui-skeleton-call_test_skel') ||
                     toolCard.querySelector('.genui-skeleton-slot');
    assert.notStrictEqual(skelSlot, null, 'Slot de esqueleto deve ser inserido no tool-card');
    assert.strictEqual(toolCard.classList.contains('hidden'), false, 'tool-card deve ficar visível ao receber skeleton');
    assert.strictEqual(toolCard.innerHTML.includes('AURA Engine: Consultando volumetria dos tanques...'), true, 'Micro-copy contextual deve ser renderizada');
    assert.strictEqual(toolCard.innerHTML.includes('animate-pulse'), true, 'Placeholder deve possuir animação animate-pulse');
    console.log('[NODE]    ✓ handleUISkeleton alocou esqueleto e micro-copy com precisão.');

    // 3.3 Hidratação Instantânea sem Layout Jank com Componente Registrado (F2-04)
    const testRegistry = window.SecureComponentRegistry;
    testRegistry.registerComponent('render_TankRunOutForecastUI', class MockTankWidget {{
      constructor(payload) {{
        this.payload = payload;
      }}
      mount() {{
        const card = new MockElement('div', 'genui-hydrated-card-1');
        card.className = 'genui-hydrated-card p-4 rounded-xl border border-cyan-500';
        card.innerHTML = `<div class="gauge">Saldo: ${{this.payload.props.saldo}}L</div>`;
        return card;
      }}
    }});

    chatCtrl.handleUIComplete(containerId, {{
      tool_call_id: 'call_test_skel',
      component_name: 'render_TankRunOutForecastUI',
      props: {{ saldo: 4200 }},
      actions: []
    }});

    assert.strictEqual(toolCard.innerHTML.includes('genui-hydrated-card'), true, 'Esqueleto deve ser substituído pelo card hidratado');
    console.log('[NODE]    ✓ handleUIComplete hidratou componente registrado sem layout jank.');

    // 3.4 Fallback gracioso quando componente não está registrado (Fase 2 -> Fase 3)
    const containerId2 = 'aura-msg-fallback';
    const msgBox2 = new MockElement('div', containerId2);
    const toolCard2 = new MockElement('div', containerId2 + '-tool-card');
    toolCard2.classList.add('hidden');
    msgBox2.appendChild(toolCard2);
    mockElementsById.set(containerId2, msgBox2);
    mockElementsById.set(containerId2 + '-tool-card', toolCard2);

    chatCtrl.handleUISkeleton(containerId2, {{
      tool_call_id: 'call_unregistered_1',
      component_name: 'render_UnregisteredFutureWidget',
      title: 'Calculando análise preditiva futura...'
    }});

    chatCtrl.handleUIComplete(containerId2, {{
      tool_call_id: 'call_unregistered_1',
      component_name: 'render_UnregisteredFutureWidget',
      executive_summary: 'Diagnóstico futuro sem quebra.',
      props: {{ kpi: 'alto_impacto' }},
      actions: [{{ action_id: 'act_1', label: 'Simular Cenário' }}]
    }});

    assert.strictEqual(toolCard2.innerHTML.includes('render_UnregisteredFutureWidget'), true, 'Fallback canônico deve exibir título do widget');
    assert.strictEqual(toolCard2.innerHTML.includes('Diagnóstico futuro sem quebra.'), true, 'Fallback canônico deve exibir resumo');
    console.log('[NODE]    ✓ Fallback gracioso para componente futuro validado com sucesso.');

    // 3.5 Limpeza graciosa de esqueleto órfão em erro ou encerramento (F2-04)
    const containerId3 = 'aura-msg-orphan';
    const msgBox3 = new MockElement('div', containerId3);
    const toolCard3 = new MockElement('div', containerId3 + '-tool-card');
    toolCard3.classList.add('hidden');
    msgBox3.appendChild(toolCard3);
    mockElementsById.set(containerId3, msgBox3);
    mockElementsById.set(containerId3 + '-tool-card', toolCard3);

    chatCtrl.handleUISkeleton(containerId3, {{
      tool_call_id: 'call_orphan_1',
      component_name: 'render_TankRunOutForecastUI',
      title: 'Consultando...'
    }});

    assert.strictEqual(toolCard3.classList.contains('hidden'), false);

    // Simula erro ou término antes de ui_complete
    chatCtrl.cleanupSkeletonSlots(containerId3);
    assert.strictEqual(toolCard3.classList.contains('hidden'), true, 'toolCard3 deve voltar a hidden se esqueleto for removido');
    assert.strictEqual(toolCard3.children.length, 0, 'Nenhum nó de esqueleto órfão deve permanecer no DOM');
    console.log('[NODE]    ✓ cleanupSkeletonSlots removeu esqueleto órfão sem deixar caixas vazias.');

    // 3.6 Teste de Ciclo de Vida Completo em AuraChatController.handleSendMessage()
    console.log('[NODE] 4. Testando handleSendMessage() end-to-end (Zero Duplicação & Companion Canvas)...');
    let auxProjectCount = 0;
    window.auraAuxPanel = {{
      projectArtifact: () => {{
        auxProjectCount++;
      }}
    }};

    const feedContainer = new MockElement('div', 'chat-feed-container');
    const inputEl = new MockElement('input', 'chat-input-text');
    mockElementsById.set('chat-feed-container', feedContainer);
    mockElementsById.set('chat-input-text', inputEl);

    const e2eChatCtrl = new AuraChatController();
    let e2eSkeletonCalls = 0;
    let e2eCompleteCalls = 0;

    const origSkel = e2eChatCtrl.handleUISkeleton.bind(e2eChatCtrl);
    const origComp = e2eChatCtrl.handleUIComplete.bind(e2eChatCtrl);

    e2eChatCtrl.handleUISkeleton = (cid, data) => {{
      e2eSkeletonCalls++;
      return origSkel(cid, data);
    }};
    e2eChatCtrl.handleUIComplete = (cid, data) => {{
      e2eCompleteCalls++;
      return origComp(cid, data);
    }};

    const e2eSseChunks = [
      'event: intent\\ndata: {{"chunk_type": "intent", "intent": "previsao_tanques"}}\\n\\n',
      'event: tool_start\\ndata: {{"chunk_type": "tool_start", "intent": "previsao_tanques"}}\\n\\n',
      'event: ui_skeleton\\ndata: {{"chunk_type": "ui_skeleton", "tool_call_id": "call_e2e_1", "component_name": "render_TankRunOutForecastUI", "title": "Analisando..."}}\\n\\n',
      'event: tool_result\\ndata: {{"chunk_type": "tool_result", "intent": "previsao_tanques", "result": {{"tanque": 1}}}}\\n\\n',
      'event: delta\\ndata: {{"chunk_type": "delta", "text": "Resumo executivo do tanque."}}\\n\\n',
      'event: ui_complete\\ndata: {{"chunk_type": "ui_complete", "tool_call_id": "call_e2e_1", "component_name": "render_TankRunOutForecastUI", "props": {{"saldo": 5000}}}}\\n\\n',
      'event: telemetry\\ndata: {{"chunk_type": "telemetry", "data": {{"latency_ms": 30}}}}\\n\\n',
      'event: done\\ndata: [DONE]\\n\\n'
    ];

    const enc = new TextEncoder();
    global.fetch = async () => ({{
      ok: true,
      status: 200,
      body: new ReadableStream({{
        start(c) {{
          for (const ch of e2eSseChunks) c.enqueue(enc.encode(ch));
          c.close();
        }}
      }})
    }});

    await e2eChatCtrl.handleSendMessage('Qual o nível dos tanques?');

    assert.strictEqual(e2eSkeletonCalls, 1, 'handleUISkeleton deve ser chamado exatamente uma vez');
    assert.strictEqual(e2eCompleteCalls, 1, 'handleUIComplete deve ser chamado exatamente uma vez');
    assert.strictEqual(auxProjectCount, 1, 'projectArtifact no Companion Canvas deve ser acionado exatamente uma vez');
    console.log('[NODE]    ✓ Zero dispatch duplicado e projeção única no Companion Canvas validados.');

    // 3.7 Teste de Fallback Gracioso quando ui_complete é omitido
    console.log('[NODE] 5. Testando Fallback Gracioso quando ui_complete é omitido...');
    let fallbackToolRenderCalls = 0;
    const fallbackChatCtrl = new AuraChatController();
    const origUpdateTool = fallbackChatCtrl.updateToolResultCard.bind(fallbackChatCtrl);
    fallbackChatCtrl.updateToolResultCard = (cid, tName, rData, force) => {{
      fallbackToolRenderCalls++;
      return origUpdateTool(cid, tName, rData, force);
    }};

    const fallbackSseChunks = [
      'event: intent\\ndata: {{"chunk_type": "intent", "intent": "previsao_tanques"}}\\n\\n',
      'event: ui_skeleton\\ndata: {{"chunk_type": "ui_skeleton", "tool_call_id": "call_fb_1", "title": "Calculando..."}}\\n\\n',
      'event: tool_result\\ndata: {{"chunk_type": "tool_result", "intent": "previsao_tanques", "result": {{"saldo": 9999}}}}\\n\\n',
      'event: delta\\ndata: {{"chunk_type": "delta", "text": "Texto final sem GenUI."}}\\n\\n',
      'event: done\\ndata: [DONE]\\n\\n'
    ];

    global.fetch = async () => ({{
      ok: true,
      status: 200,
      body: new ReadableStream({{
        start(c) {{
          for (const ch of fallbackSseChunks) c.enqueue(enc.encode(ch));
          c.close();
        }}
      }})
    }});

    await fallbackChatCtrl.handleSendMessage('Consulta fallback');
    assert.strictEqual(fallbackToolRenderCalls, 2, 'Fallback deve forçar renderização da ferramenta no encerramento');
    console.log('[NODE]    ✓ Fallback com preservação de tool_result validado com sucesso.');

    console.log('NODE_GENUI_FRONTEND_STREAMING_OK');
    }})().catch(err => {{
      console.error('[ERRO FATAL NODE]', err);
      process.exit(1);
    }});
    """

    res = subprocess.run(
        ["node", "-e", node_script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(BASE_DIR),
    )

    if res.returncode != 0:
        print("[ERRO] Execução Node.js falhou:")
        print(res.stdout)
        print(res.stderr)
        sys.exit(1)

    print(res.stdout)
    assert "NODE_GENUI_FRONTEND_STREAMING_OK" in res.stdout, "Asserção final do Node.js não encontrada"
    print("   [OK] Testes headless em Node.js finalizados com 100% de sucesso.")


def run_zero_regression_suites():
    print("\n3. Executando Validação de Regressão Zero nas Suítes Existentes...")

    suites = [
        ("test_genui_baseline.py (Fase 0 — Baseline & Governança)", "scripts/test_genui_baseline.py"),
        ("test_genui_engine_sse.py (Fase 1 — Backend SSE Multiplexado)", "scripts/test_genui_engine_sse.py"),
        ("test_aura_aux_panel.py (Companion Canvas & Split View)", "scripts/test_aura_aux_panel.py"),
        ("test_phase6_quality_resilience.py (Resiliência & Qualidade)", "scripts/test_phase6_quality_resilience.py"),
    ]

    for label, script_rel in suites:
        print(f"   ► Executando {label}...")
        script_path = BASE_DIR / script_rel
        assert script_path.exists(), f"Script de teste não encontrado: {script_path}"
        res = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(BASE_DIR),
        )
        if res.returncode != 0:
            print(f"[FALHA] {label} falhou:")
            print(res.stdout)
            print(res.stderr)
            sys.exit(1)
        print(f"     [OK] {script_rel} aprovado com 100% de sucesso.")


def main():
    print("=" * 78)
    print("🚀 SUÍTE DE TESTES: STREAMING PARSER, BUFFER & SKELETON UI (FASE 2 — P0)")
    print("   (AuraApiClient, AuraChatController, GenUIFragmentBuffer & Zero Regressão)")
    print("=" * 78)

    test_static_contracts_and_exports();
    test_nodejs_headless_streaming_and_dom();
    run_zero_regression_suites();

    print("\n" + "=" * 78)
    print("🎉 STREAMING PARSER & SKELETON UI (FASE 2) HOMOLOGADOS COM 100% DE SUCESSO!")
    print("   Eventos multiplexados, buffer volátil tolerante, zero layout jank.")
    print("=" * 78)


if __name__ == "__main__":
    main()
