"""
Suíte de Testes Automatizada: Micro-Widget Piloto ExecutiveDecisionMentorUI (Fase 3 — P0)
(ExecutiveDecisionProps, ExecutiveDecisionMentorUI, 3 Camadas Concêntricas, Companion Canvas & Zero Regressão)

Validações Obrigatórias:
1. Validação dos Modelos Pydantic (core/schemas/genui.py):
   - ExecutiveMetric: validação de rótulo, status ('success', 'warning', 'danger', 'neutral'), tendência ('up', 'down', 'neutral') e benchmark.
   - ExecutiveImpactProjection: resumo, valor financeiro estimado em R$, horizonte temporal e confiança.
   - ExecutiveEvidenceItem: título, detalhamento técnico, valor e tabela/sensor de origem.
   - ExecutiveDecisionProps: diagnóstico, score de confiança (0.0 a 1.0 com rejeição de limites inválidos), normalização de limitações e integração com GenUIActionOption.
   - GenUIEnvelope: empacotamento com props tipadas como ExecutiveDecisionProps ou dict, validação de tool_call_id, TTL e to_sse_payload().
2. Validação da Ferramenta de Backend (PostoTools & AuraEngine):
   - PostoTools.gerar_diagnostico_mentoria_executiva(): apuração determinística de margem real, faturamento, quebra de caixa e autonomia de tanques.
   - SemanticRouter: classificação heurística das perguntas de diagnóstico e mentoria executiva para 'mentoria_decisao'.
   - build_canonical_genui_envelope: geração do envelope para 'render_ExecutiveDecisionMentorUI' com 3 ações executivas táteis.
   - AuraEngine.ask_stream(): cronologia estrita (intent -> ui_skeleton -> delta -> ui_complete -> done) e zero vazamento de JSON em delta.
   - FastAPI /api/v1/aura/chat: streaming SSE multiplexado e resposta síncrona retornando envelope do mentor de decisões.
3. Validação Headless em Node.js (web/js/aura-genui-widgets.js):
   - Registro seguro no SecureComponentRegistry ('render_ExecutiveDecisionMentorUI', 'render_ExecutiveBriefingUI', 'ExecutiveDecisionMentorUI').
   - Montagem DOM (mount()) e renderização perfeita das 3 camadas concêntricas (AURA Precision Glass Deluxe):
     * Camada 1: Resumo Executivo e Diagnóstico de Alto Nível (score badge, status, texto direto).
     * Camada 2: Visualização Comparativa e Projeção de Impacto (métricas tabulares, tendências visuais, aviso de limitações do dado).
     * Camada 3: Ação Recomendada de 1 Toque e Acoplamento com Companion Canvas (botões táteis, optimistic UI, state locking e rollback).
   - Sanitização rigorosa contra Prompt Injection & XSS (OWASP LLM01): neutralização de tags <script>, <img onerror>, etc.
   - Acoplamento com Companion Canvas (projectToCanvas() invocando window.auraAuxPanel.projectArtifact).
   - Integração com AuraChatController (handleUIComplete substituindo esqueleto por ExecutiveDecisionMentorUI sem layout jank).
4. Validação de Regressão Zero:
   - Execução das 5 suítes homologadas do projeto AURA:
     * test_genui_baseline.py (Fase 0)
     * test_genui_engine_sse.py (Fase 1)
     * test_genui_frontend_streaming.py (Fase 2)
     * test_aura_aux_panel.py (Companion Canvas)
     * test_phase6_quality_resilience.py (Resiliência & WCAG)
"""

import sys
import json
import re
import asyncio
import subprocess
from pathlib import Path
from decimal import Decimal
from typing import Dict, Any, List

# Protege stdout no terminal Windows contra problemas de codificação
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
    ExecutiveMetric,
    ExecutiveImpactProjection,
    ExecutiveEvidenceItem,
    ExecutiveDecisionProps,
    GenUIActionOption,
    GenUIEnvelope,
    GenUIActionResult,
)
from core.schemas.idempotency import generate_tool_call_id, generate_action_id
from core.tools import PostoTools
from core.semantic_router import classificar_intencao_heuristica
from core.aura_engine import (
    AuraEngine,
    AuraChunk,
    AuraChunkType,
    AuraResponse,
    GENUI_COMPONENT_REGISTRY_MAP,
    build_canonical_genui_envelope,
)
from core.aura_api import create_aura_app


# =============================================================================
# ETAPA 1: MODELOS PYDANTIC E CONTRATOS DO MICRO-WIDGET (F3-01)
# =============================================================================

def test_pydantic_contracts_executive_decision():
    print("\n1. Testando Contratos Pydantic do Micro-Widget Piloto (ExecutiveDecisionProps)...")

    # 1.1 ExecutiveMetric
    m1 = ExecutiveMetric(
        label="Margem Líquida Real",
        current_value="14.2%",
        benchmark_value="15.0%",
        trend="down",
        status="warning",
        unit="%",
        delta_percent=-0.8
    )
    assert m1.label == "Margem Líquida Real"
    assert m1.current_value == "14.2%"
    assert m1.trend == "down"
    assert m1.status == "warning"
    assert m1.delta_percent == -0.8

    # Rejeição de rótulo vazio
    try:
        ExecutiveMetric(label="   ", current_value="10%")
        assert False, "Deveria falhar com label vazio"
    except ValidationError:
        pass

    # Rejeição de trend inválido
    try:
        ExecutiveMetric(label="Métrica", current_value="10", trend="invalid_trend")
        assert False, "Deveria falhar com trend inválido"
    except ValidationError:
        pass

    # Rejeição de status inválido
    try:
        ExecutiveMetric(label="Métrica", current_value="10", status="invalid_status")
        assert False, "Deveria falhar com status inválido"
    except ValidationError:
        pass

    # 1.2 ExecutiveImpactProjection
    proj = ExecutiveImpactProjection(
        summary="Ajuste na abordagem de pista pode recuperar R$ 420,00/dia",
        estimated_financial_impact=420.0,
        timeframe="24h a 7 dias",
        confidence=0.92
    )
    assert proj.estimated_financial_impact == 420.0
    assert proj.timeframe == "24h a 7 dias"
    assert proj.confidence == 0.92

    # Rejeição de confiança fora do range [0.0, 1.0]
    try:
        ExecutiveImpactProjection(summary="Teste", confidence=1.5)
        assert False, "Deveria falhar com confiança > 1.0"
    except ValidationError:
        pass

    # 1.3 ExecutiveEvidenceItem
    ev = ExecutiveEvidenceItem(
        title="Auditoria de Vendas",
        detail="Confronto de cupons fiscais e receitas",
        value="R$ 14.850,00",
        source="tb_vendas_itens"
    )
    assert ev.title == "Auditoria de Vendas"
    assert ev.source == "tb_vendas_itens"

    # 1.4 ExecutiveDecisionProps
    act1 = GenUIActionOption(
        action_id=generate_action_id(),
        label="⚡ Aplicar Recomendações Prioritárias",
        action_type="mutation",
        variant="primary",
        requires_confirmation=True,
        payload={"operacao": "aplicar"}
    )

    props = ExecutiveDecisionProps(
        diagnosis="Operação estável com margem consolidada em 14.2% e atenção ao 1º Turno.",
        confidence_score=0.96,
        metrics=[m1],
        limitations="Dados bancários pendentes de conciliação de lote TEF.",  # Testa normalização str -> list
        impact_projection=proj,
        evidence_items=[ev],
        suggested_actions=[act1]
    )
    assert props.diagnosis.startswith("Operação estável")
    assert props.confidence_score == 0.96
    assert len(props.metrics) == 1
    assert isinstance(props.limitations, list) and len(props.limitations) == 1
    assert props.limitations[0] == "Dados bancários pendentes de conciliação de lote TEF."
    assert len(props.suggested_actions) == 1

    # Rejeição de score de confiança inválido (<0 ou >1)
    try:
        ExecutiveDecisionProps(diagnosis="Ok", confidence_score=-0.1)
        assert False, "Deveria falhar com confidence_score < 0"
    except ValidationError:
        pass
    try:
        ExecutiveDecisionProps(diagnosis="Ok", confidence_score=1.05)
        assert False, "Deveria falhar com confidence_score > 1"
    except ValidationError:
        pass

    # Rejeição de diagnóstico vazio
    try:
        ExecutiveDecisionProps(diagnosis="   ", confidence_score=0.9)
        assert False, "Deveria falhar com diagnosis vazio"
    except ValidationError:
        pass

    # 1.5 GenUIEnvelope integrando ExecutiveDecisionProps
    tool_call_id = generate_tool_call_id()
    envelope = GenUIEnvelope(
        schema_version="1.0",
        tool_call_id=tool_call_id,
        component_name="render_ExecutiveDecisionMentorUI",
        client_component="ExecutiveDecisionMentorUI",
        intent="mentoria_decisao",
        executive_summary="Diagnóstico executivo de alta precisão apurado pela AURA.",
        props=props,  # Testa coerção automática de BaseModel para Dict
        actions=[act1],
        ttl_seconds=900
    )
    assert envelope.tool_call_id == tool_call_id
    assert envelope.component_name == "render_ExecutiveDecisionMentorUI"
    assert envelope.props["confidence_score"] == 0.96
    assert isinstance(envelope.props["metrics"], list)

    sse_payload = envelope.to_sse_payload()
    assert sse_payload["component_name"] == "render_ExecutiveDecisionMentorUI"
    assert sse_payload["summary_text"] == "Diagnóstico executivo de alta precisão apurado pela AURA."
    assert sse_payload["envelope_version"] == "1.0"

    print("   [OK] Modelos Pydantic, restrições e integração com GenUIEnvelope validados com 100% de sucesso.")


# =============================================================================
# ETAPA 2: BACKEND, TOOLS E INTEGRAÇÃO SSE MULTIPLEXADA (F3-03)
# =============================================================================

def test_backend_tool_and_router():
    print("\n2. Testando Roteamento Semântico e Ferramenta de Mentoria Executiva no Backend...")

    engine = AuraEngine()
    tools = engine.tools
    diag_data = tools.gerar_diagnostico_mentoria_executiva(tipo="geral")
    assert diag_data["status"] == "ok"
    assert diag_data["intent"] == "mentoria_decisao"
    assert diag_data["component_name"] == "render_ExecutiveDecisionMentorUI"
    assert "diagnosis" in diag_data
    assert "confidence_score" in diag_data and diag_data["confidence_score"] >= 0.9
    assert isinstance(diag_data["metrics"], list) and len(diag_data["metrics"]) >= 3
    assert isinstance(diag_data["limitations"], list) and len(diag_data["limitations"]) >= 1
    assert isinstance(diag_data["suggested_actions"], list) and len(diag_data["suggested_actions"]) >= 2
    assert "props" in diag_data and isinstance(diag_data["props"], dict)

    # Classificação Heurística do SemanticRouter
    perguntas_mentoria = [
        "Qual o diagnóstico do meu negócio hoje?",
        "Onde estou perdendo margem no posto?",
        "Briefing executivo do dia",
        "Como está a saúde da minha operação?",
        "O que o mentor de decisões recomenda hoje?",
    ]
    for q in perguntas_mentoria:
        intent = classificar_intencao_heuristica(q)
        assert intent == "mentoria_decisao", f"Falha ao classificar '{q}': obteve '{intent}'"

    # Mapeamento canônico no GENUI_COMPONENT_REGISTRY_MAP
    assert "mentoria_decisao" in GENUI_COMPONENT_REGISTRY_MAP
    mapping = GENUI_COMPONENT_REGISTRY_MAP["mentoria_decisao"]
    assert mapping["component_name"] == "render_ExecutiveDecisionMentorUI"
    assert mapping["client_component"] == "ExecutiveDecisionMentorUI"

    # Builder canônico do envelope
    tool_id = generate_tool_call_id()
    envelope = build_canonical_genui_envelope(
        intencao="mentoria_decisao",
        tool_call_id=tool_id,
        resultado_bruto=diag_data,
        executive_summary="Resumo executivo do diagnóstico do dia."
    )
    assert envelope is not None
    assert envelope.tool_call_id == tool_id
    assert envelope.component_name == "render_ExecutiveDecisionMentorUI"
    assert len(envelope.actions) >= 3
    labels = [a.label for a in envelope.actions]
    assert any("Aplicar Recomendações" in l for l in labels)
    assert any("Ajustar Metas" in l for l in labels)
    assert any("Companion Canvas" in l or "Canvas" in l for l in labels)

    print("   [OK] Roteamento, PostoTools e build_canonical_genui_envelope aprovados.")


def test_engine_streaming_and_fastapi_sse():
    print("\n3. Testando Streaming Multiplexado SSE com ExecutiveDecisionMentorUI...")

    engine = AuraEngine()

    async def run_stream():
        chunks = []
        async for chunk in engine.ask_stream("Qual o diagnóstico do meu negócio hoje?", session_id="test_mentor_session"):
            chunks.append(chunk)
        return chunks

    chunks = asyncio.run(run_stream())
    types = [c.chunk_type.value for c in chunks]

    assert "intent" in types, "Faltou chunk INTENT"
    assert "ui_skeleton" in types, "Faltou chunk UI_SKELETON"
    assert "delta" in types, "Faltou chunk DELTA"
    assert "ui_complete" in types, "Faltou chunk UI_COMPLETE"
    assert "done" in types, "Faltou chunk DONE"

    # Validação da ordem cronológica
    idx_intent = types.index("intent")
    idx_skel = types.index("ui_skeleton")
    idx_delta = types.index("delta")
    idx_comp = types.index("ui_complete")
    idx_done = types.index("done")

    assert idx_intent < idx_skel < idx_delta < idx_comp < idx_done, f"Ordem cronológica violada: {types}"

    # Validação do conteúdo do UI_SKELETON
    skel_chunk = next(c for c in chunks if c.chunk_type == AuraChunkType.UI_SKELETON)
    assert skel_chunk.data.get("component_name") == "render_ExecutiveDecisionMentorUI"

    # Validação do conteúdo do UI_COMPLETE
    comp_chunk = next(c for c in chunks if c.chunk_type == AuraChunkType.UI_COMPLETE)
    comp_data = comp_chunk.data
    assert comp_data.get("component_name") == "render_ExecutiveDecisionMentorUI"
    assert "props" in comp_data
    assert comp_data["props"].get("confidence_score") is not None
    assert len(comp_data.get("actions", [])) >= 2

    # Isolamento semântico: zero vazamento de JSON em DELTA
    deltas = [c.text for c in chunks if c.chunk_type == AuraChunkType.DELTA and c.text]
    full_text = "".join(deltas)
    assert not full_text.strip().startswith("{"), "Vazamento de JSON detectado no início de DELTA"
    assert "```json" not in full_text, "Bloco json cru vazado em DELTA"

    # Teste de integração HTTP no FastAPI com TestClient
    app = create_aura_app(engine=engine)
    client = TestClient(app)

    # 1. Chat SSE streaming
    resp_sse = client.post(
        "/api/v1/aura/chat",
        json={"query": "Onde estou perdendo margem no posto?", "stream": True, "session_id": "test_http_sse"}
    )
    assert resp_sse.status_code == 200
    assert "text/event-stream" in resp_sse.headers["content-type"]
    sse_body = resp_sse.text
    assert "event: ui_skeleton" in sse_body
    assert "render_ExecutiveDecisionMentorUI" in sse_body
    assert "event: ui_complete" in sse_body
    assert "event: done" in sse_body

    # 2. Chat síncrono
    resp_sync = client.post(
        "/api/v1/aura/chat",
        json={"query": "Qual o diagnóstico do meu negócio hoje?", "stream": False, "session_id": "test_http_sync"}
    )
    assert resp_sync.status_code == 200
    sync_data = resp_sync.json()
    assert sync_data.get("intent") == "mentoria_decisao"
    envelope = sync_data.get("envelope") or sync_data.get("genui_envelope")
    assert envelope is not None
    assert envelope["component_name"] == "render_ExecutiveDecisionMentorUI"

    print("   [OK] Gerador ask_stream multiplexado e rotas FastAPI SSE validados com 100% de sucesso.")


# =============================================================================
# ETAPA 3: VALIDAÇÃO HEADLESS EM NODE.JS (F3-02 & F3-04)
# =============================================================================

def test_nodejs_headless_decision_mentor():
    print("\n4. Executando Validações Headless em Node.js (DOM, 3 Camadas, Sanitização & Canvas)...")

    widgets_js_path = BASE_DIR / "web" / "js" / "aura-genui-widgets.js"
    genui_js_path = BASE_DIR / "web" / "js" / "aura-genui.js"
    api_js_path = BASE_DIR / "web" / "js" / "aura-api.js"
    chat_js_path = BASE_DIR / "web" / "js" / "aura-chat.js"
    aux_panel_js_path = BASE_DIR / "web" / "js" / "aura-aux-panel.js"
    index_html_path = BASE_DIR / "web" / "index.html"
    css_path = BASE_DIR / "web" / "css" / "aura.css"

    assert widgets_js_path.exists(), f"Arquivo ausente: {widgets_js_path}"
    assert genui_js_path.exists(), f"Arquivo ausente: {genui_js_path}"
    assert api_js_path.exists(), f"Arquivo ausente: {api_js_path}"
    assert chat_js_path.exists(), f"Arquivo ausente: {chat_js_path}"
    assert aux_panel_js_path.exists(), f"Arquivo ausente: {aux_panel_js_path}"
    assert index_html_path.exists(), f"Arquivo ausente: {index_html_path}"
    assert css_path.exists(), f"Arquivo ausente: {css_path}"

    index_html = index_html_path.read_text(encoding="utf-8")
    assert "aura-genui-widgets.js" in index_html, "aura-genui-widgets.js não incluído em index.html"

    css_content = css_path.read_text(encoding="utf-8")
    assert ".genui-decision-mentor-card" in css_content, ".genui-decision-mentor-card ausente em aura.css"

    node_script = f"""
    const assert = require('assert');
    const path = require('path');

    const widgetsPath = {json.dumps(str(widgets_js_path.resolve()))};
    const genuiPath = {json.dumps(str(genui_js_path.resolve()))};
    const chatPath = {json.dumps(str(chat_js_path.resolve()))};
    const auxPath = {json.dumps(str(aux_panel_js_path.resolve()))};

    // Setup do ambiente DOM mock para testes reais de montagem no Node.js
    class MockClassList {{
      constructor(el) {{ this.el = el; this._classes = new Set(); }}
      add(...cls) {{ cls.forEach(c => this._classes.add(c)); this.sync(); }}
      remove(...cls) {{ cls.forEach(c => this._classes.delete(c)); this.sync(); }}
      contains(c) {{ return this._classes.has(c); }}
      toggle(c, force) {{
        const has = this._classes.has(c);
        const shouldHave = (force !== undefined) ? force : !has;
        if (shouldHave) this._classes.add(c); else this._classes.delete(c);
        this.sync();
        return shouldHave;
      }}
      sync() {{ this.el._className = Array.from(this._classes).join(' '); }}
    }}

    class MockNode {{
      constructor(tagName = 'div') {{
        this.tagName = (tagName || 'div').toUpperCase();
        this.id = '';
        this._className = '';
        this.classList = new MockClassList(this);
        this.attributes = new Map();
        this.listeners = new Map();
        this.children = [];
        this.parentNode = null;
        this._innerHTML = '';
        this._textContent = '';
      }}
      get firstElementChild() {{ return this.children[0] || null; }}
      get textContent() {{ return this._textContent || this._innerHTML.replace(/<[^>]+>/g, '').trim(); }}
      set textContent(v) {{ this._textContent = v; }}
      get className() {{ return this._className; }}
      set className(v) {{ this._className = v || ''; this.classList._classes = new Set((v || '').split(/\\s+/).filter(Boolean)); }}
      setAttribute(k, v) {{ this.attributes.set(k, String(v)); if (k === 'id') this.id = v; if (k === 'class') this.className = v; }}
      getAttribute(k) {{ return this.attributes.get(k) || null; }}
      addEventListener(type, fn) {{
        if (!this.listeners.has(type)) this.listeners.set(type, []);
        this.listeners.get(type).push(fn);
      }}
      click() {{
        const fns = this.listeners.get('click') || [];
        for (const fn of fns) fn({{ target: this, preventDefault: () => {{}} }});
      }}
      appendChild(node) {{
        node.parentNode = this;
        this.children.push(node);
        return node;
      }}
      replaceChild(newNode, oldNode) {{
        const idx = this.children.indexOf(oldNode);
        if (idx !== -1) {{
          newNode.parentNode = this;
          oldNode.parentNode = null;
          this.children[idx] = newNode;
          return oldNode;
        }}
        return null;
      }}
      querySelector(selector) {{
        for (const child of this.children) {{
          if (child.matches(selector)) return child;
          const found = child.querySelector(selector);
          if (found) return found;
        }}
        return null;
      }}
      querySelectorAll(selector) {{
        const res = [];
        for (const child of this.children) {{
          if (child.matches(selector)) res.push(child);
          res.push(...child.querySelectorAll(selector));
        }}
        return res;
      }}
      matches(selector) {{
        if (selector.startsWith('.')) return this.classList.contains(selector.slice(1));
        if (selector.startsWith('#')) return this.id === selector.slice(1);
        return false;
      }}
      set innerHTML(html) {{
        this._innerHTML = html;
        this.children = [];
        const layer1 = new MockNode('div'); layer1.className = 'genui-layer genui-layer-1'; this.appendChild(layer1);
        const layer2 = new MockNode('div'); layer2.className = 'genui-layer genui-layer-2'; this.appendChild(layer2);
        const layer3 = new MockNode('div'); layer3.className = 'genui-layer genui-layer-3'; this.appendChild(layer3);

        const toggleBtn = new MockNode('button');
        toggleBtn.className = 'genui-toggle-evidence';
        toggleBtn.textContent = '▼ Memória de Cálculo & Evidências';
        layer2.appendChild(toggleBtn);

        const evidenceList = new MockNode('div');
        evidenceList.className = 'genui-evidence-list space-y-1 hidden';
        layer2.appendChild(evidenceList);

        const dismissBtn = new MockNode('button');
        dismissBtn.className = 'genui-dismiss-error';
        layer3.appendChild(dismissBtn);

        const btnRegex = /<button[^>]*class="[^"]*genui-action-btn[^"]*"[^>]*data-action-id="([^"]+)"[^>]*data-action-type="([^"]+)"[^>]*>([\\s\\S]*?)<\\/button>/g;
        let match;
        while ((match = btnRegex.exec(html)) !== null) {{
          const btn = new MockNode('button');
          btn.className = 'genui-action-btn';
          btn.setAttribute('data-action-id', match[1]);
          btn.setAttribute('data-action-type', match[2]);
          btn.textContent = match[3].replace(/<[^>]+>/g, '').trim();
          layer3.appendChild(btn);
        }}
      }}
      get innerHTML() {{ return this._innerHTML; }}
    }}

    global.document = {{
      createElement: (tag) => new MockNode(tag),
      querySelector: () => null,
      querySelectorAll: () => []
    }};
    global.HTMLElement = MockNode;

    const {{ ExecutiveDecisionMentorUI, ExecutiveBriefingWidget }} = require(widgetsPath);
    const {{ AuraGenUI, SecureComponentRegistry, registry }} = require(genuiPath);
    const {{ AuraChatController }} = require(chatPath);
    const {{ AuraAuxPanel }} = require(auxPath);

    // =========================================================================
    // 1. VERIFICAÇÃO DO REGISTRO NO SecureComponentRegistry (OWASP LLM03)
    // =========================================================================
    console.log('[NODE] 1. Verificando Registro no SecureComponentRegistry...');
    assert(registry.hasComponent('render_ExecutiveDecisionMentorUI'), 'render_ExecutiveDecisionMentorUI não registrado');
    assert(registry.hasComponent('render_ExecutiveBriefingUI'), 'render_ExecutiveBriefingUI não registrado');
    assert(registry.hasComponent('ExecutiveDecisionMentorUI'), 'ExecutiveDecisionMentorUI não registrado');

    const ResolvedClass = registry.resolveComponent('render_ExecutiveDecisionMentorUI');
    assert.strictEqual(ResolvedClass, ExecutiveDecisionMentorUI, 'Classe resolvida diferente de ExecutiveDecisionMentorUI');

    // =========================================================================
    // 2. MONTAGEM DAS 3 CAMADAS CONCÊNTRICAS E DADOS TABULARES
    // =========================================================================
    console.log('[NODE] 2. Testando Montagem das 3 Camadas Concêntricas...');

    const samplePayload = {{
      tool_call_id: 'call_99b19a02-412f-4a0b-8c01-d85cfd774bfe',
      component_name: 'render_ExecutiveDecisionMentorUI',
      intent: 'mentoria_decisao',
      executive_summary: 'Diagnóstico operacional consolidado: margem saudável em 14.2% com oportunidade no 2º turno.',
      props: {{
        diagnosis: 'Margem líquida estável em 14.2%, porém com gap de R$ 180,00 no 1º turno e Tanque 01 demandando pedido.',
        confidence_score: 0.96,
        metrics: [
          {{ label: 'Margem Real', current_value: '14.2%', benchmark_value: '15.0%', trend: 'down', status: 'warning' }},
          {{ label: 'Faturamento', current_value: 'R$ 14.850,00', benchmark_value: 'R$ 15.000,00', trend: 'up', status: 'success' }},
          {{ label: 'Quebra de Caixa', current_value: '-R$ 180,00', benchmark_value: 'R$ 0,00', trend: 'down', status: 'danger' }},
          {{ label: 'Autonomia Mínima', current_value: '8.5h', benchmark_value: '24.0h', trend: 'down', status: 'danger' }}
        ],
        impact_projection: {{
          summary: 'Ajuste de abordagem e contenção de perdas projetam recuperação de R$ 520,00/dia.',
          estimated_financial_impact: 520.0,
          timeframe: '24h a 7 dias'
        }},
        limitations: [
          'Dados de cartões de crédito consolidados via TEF local sem fechamento bancário.'
        ],
        evidence_items: [
          {{ title: 'Conferência de Caixa', detail: 'Furo apurado no 1º turno', source: 'tb_caixa_fechamento' }},
          {{ title: 'Telemetria de Tanques', detail: 'Sonda automática Tanque 01', source: 'tb_tanque_medicao' }}
        ]
      }},
      actions: [
        {{
          action_id: 'act_10101010-412f-4a0b-8c01-d85cfd774bfe',
          label: '⚡ Aplicar Recomendações Prioritárias',
          action_type: 'mutation',
          variant: 'primary'
        }},
        {{
          action_id: 'act_20202020-412f-4a0b-8c01-d85cfd774bfe',
          label: '🎯 Ajustar Metas do Turno',
          action_type: 'mutation',
          variant: 'secondary'
        }},
        {{
          action_id: 'act_30303030-412f-4a0b-8c01-d85cfd774bfe',
          label: '🔍 Projetar no Companion Canvas',
          action_type: 'inspection',
          variant: 'ghost'
        }}
      ]
    }};

    const widget = new ExecutiveDecisionMentorUI(samplePayload);
    const mountedHtml = widget.renderHtml();

    // Validações da Camada 1
    assert(mountedHtml.includes('96% Confiança'), 'Camada 1: Badge de confiança ausente');
    assert(mountedHtml.includes('Margem líquida estável em 14.2%'), 'Camada 1: Diagnóstico ausente');

    // Validações da Camada 2
    assert(mountedHtml.includes('Margem Real'), 'Camada 2: Rótulo de métrica ausente');
    assert(mountedHtml.includes('R$ 14.850,00'), 'Camada 2: Faturamento ausente');
    assert(mountedHtml.includes('-R$ 180,00'), 'Camada 2: Quebra de caixa ausente');
    assert(mountedHtml.includes('Projeção de Impacto'), 'Camada 2: Projeção ausente');
    assert(mountedHtml.includes('+R$ 520,00'), 'Camada 2: Valor do impacto ausente');
    assert(mountedHtml.includes('Limitações do Dado Apurado'), 'Camada 2: Aviso de limitações ausente');
    assert(mountedHtml.includes('Dados de cartões de crédito consolidados'), 'Camada 2: Detalhe de limitações ausente');
    assert(mountedHtml.includes('genui-evidence-list space-y-1 hidden'), 'Camada 2: Evidências devem iniciar colapsadas com classe hidden');

    // Teste de Impacto Negativo e Benchmark Zero
    const negPayload = {{
      tool_call_id: 'call_neg_test',
      component_name: 'render_ExecutiveDecisionMentorUI',
      props: {{
        diagnosis: 'Risco de desabastecimento iminente',
        confidence_score: 0.91,
        metrics: [{{ label: 'Desvio de Caixa', current_value: '-R$ 350,00', benchmark_value: 0 }}],
        impact_projection: {{
          summary: 'Prejuízo estimado com parada da operação',
          estimated_financial_impact: -480.0,
          timeframe: '12h'
        }}
      }}
    }};
    const negWidget = new ExecutiveDecisionMentorUI(negPayload);
    const negHtml = negWidget.renderHtml();
    assert(negHtml.includes('-R$ 480,00'), 'Camada 2: Impacto negativo deve exibir sinal de menos');
    assert(negHtml.includes('text-rose-400'), 'Camada 2: Impacto negativo deve ter classe rose de atenção');
    assert(!negHtml.includes('+R$ -480,00'), 'Camada 2: Erro de sinal duplo +R$ -480,00 não pode ocorrer');
    assert(negHtml.includes('Meta: 0'), 'Camada 2: Benchmark zero deve ser exibido sem ser descartado');

    // Validações da Camada 3
    assert(mountedHtml.includes('⚡ Aplicar Recomendações Prioritárias'), 'Camada 3: Botão primário ausente');
    assert(mountedHtml.includes('🎯 Ajustar Metas do Turno'), 'Camada 3: Botão secundário ausente');
    assert(mountedHtml.includes('🔍 Projetar no Companion Canvas'), 'Camada 3: Botão de Canvas ausente');
    assert(mountedHtml.includes('data-action-id="act_10101010-412f-4a0b-8c01-d85cfd774bfe"'), 'Camada 3: ID de ação incorreto');

    // =========================================================================
    // 3. SANITIZAÇÃO CONTRA XSS E PROMPT INJECTION (OWASP LLM01)
    // =========================================================================
    console.log('[NODE] 3. Testando Sanitização Contra XSS e Injeções Maliciosas (OWASP LLM01)...');

    const maliciousPayload = {{
      tool_call_id: 'call_xss_test_123',
      component_name: 'render_ExecutiveDecisionMentorUI',
      props: {{
        diagnosis: '<script>alert("xss")</script>Diagnóstico com injeção',
        confidence_score: 0.90,
        metrics: [
          {{ label: '<img src=x onerror=alert(1)>Rótulo', current_value: '<b>10%</b>' }}
        ],
        limitations: [
          '<iframe src="evil.com"></iframe>Limitação hostil'
        ]
      }},
      actions: [
        {{
          action_id: 'act_xss_1',
          label: '<script>evil()</script>Clique Aqui',
          action_type: 'mutation'
        }}
      ]
    }};

    const maliciousWidget = new ExecutiveDecisionMentorUI(maliciousPayload);
    const sanitizedHtml = maliciousWidget.renderHtml();

    assert(!sanitizedHtml.includes('<script>'), 'Falha grave: tag <script> não foi escapada!');
    assert(sanitizedHtml.includes('&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;'), 'String do script não foi escapada para entidades HTML');
    assert(!sanitizedHtml.includes('<img src=x onerror'), 'Falha grave: tag <img> maliciosa não foi escapada!');
    assert(!sanitizedHtml.includes('<iframe'), 'Falha grave: tag <iframe> maliciosa não foi escapada!');

    // =========================================================================
    // 4. GESTÃO DE ESTADO OTIMISTA & ROLLBACK RESILIENTE
    // =========================================================================
    console.log('[NODE] 4. Testando State Locking, Optimistic UI e Rollback...');

    assert.strictEqual(widget.state.isLocked, false);
    widget.applyOptimisticState('act_10101010-412f-4a0b-8c01-d85cfd774bfe', 'Autorizando no ERP...');
    assert.strictEqual(widget.state.isLocked, true);
    assert.strictEqual(widget.state.lockedActionId, 'act_10101010-412f-4a0b-8c01-d85cfd774bfe');
    assert.strictEqual(widget.state.optimisticFeedback, 'Autorizando no ERP...');

    const lockedHtml = widget.renderLayer3();
    assert(lockedHtml.includes('disabled'), 'Botões deveriam estar desabilitados no estado locked');
    assert(lockedHtml.includes('Autorizando no ERP...'), 'Badge otimista ausente no estado locked');

    // Rollback
    widget.rollbackOptimisticState('Erro 500 no ERP');
    assert.strictEqual(widget.state.isLocked, false);
    assert.strictEqual(widget.state.lockedActionId, null);
    assert.strictEqual(widget.state.errorMessage, 'Erro 500 no ERP');

    const rollbackHtml = widget.renderLayer3();
    assert(rollbackHtml.includes('Erro 500 no ERP'), 'Mensagem de erro não exibida após rollback');
    assert(!rollbackHtml.includes('disabled'), 'Botões deveriam voltar a ser habilitados após rollback');

    // =========================================================================
    // 5. ACOPLAMENTO COM COMPANION CANVAS (AuraAuxPanel.projectArtifact)
    // =========================================================================
    console.log('[NODE] 5. Testando Acoplamento com Companion Canvas...');

    const auxPanel = new AuraAuxPanel();
    let projectedArtifact = null;

    // Simula window.auraAuxPanel
    global.window = {{
      auraAuxPanel: {{
        projectArtifact: (art) => {{
          projectedArtifact = art;
          return art;
        }}
      }}
    }};

    widget.projectToCanvas();
    assert(projectedArtifact !== null, 'projectToCanvas() não invocou window.auraAuxPanel.projectArtifact');
    assert(projectedArtifact.toolName === 'render_ExecutiveDecisionMentorUI', 'toolName incorreto na projeção');
    assert(projectedArtifact.intent === 'mentoria_decisao', 'intent incorreta na projeção');
    assert(projectedArtifact.autoOpen === true, 'autoOpen deveria ser true');

    // Testa normalização no AuraAuxPanel nativo
    const normalized = auxPanel.normalizeArtifactData(
      'render_ExecutiveDecisionMentorUI',
      'mentoria_decisao',
      samplePayload.props,
      mountedHtml
    );
    assert(normalized.title.includes('Mentor de Decisões Executivo'), 'Título normalizado do Canvas incorreto');
    assert(normalized.statusChip.label.includes('96% Confiança'), 'Status chip normalizado do Canvas incorreto');
    assert(normalized.records.length >= 4, 'Records tabulares do Canvas não extraídos');
    assert(normalized.auditRules.length >= 1, 'Regras de auditoria do Canvas não configuradas');

    // =========================================================================
    // 6. IDEMPOTÊNCIA DE EVENT LISTENERS & CICLO DE VIDA DOM
    // =========================================================================
    console.log('[NODE] 6. Testando Idempotência de Listeners e Ciclo de Vida DOM...');

    const domEl = widget.mount();
    const toggleEvidenceBtn = domEl.querySelector('.genui-toggle-evidence');
    const evidenceListEl = domEl.querySelector('.genui-evidence-list');
    assert(evidenceListEl.classList.contains('hidden'), 'Lista de evidências deve iniciar oculta no DOM');
    toggleEvidenceBtn.click();
    assert(!evidenceListEl.classList.contains('hidden'), 'Primeiro clique deve exibir evidências');
    // Invoca refreshLayer3 (que re-executa bindEvents no rootElement)
    widget.refreshLayer3();
    toggleEvidenceBtn.click();
    assert(evidenceListEl.classList.contains('hidden'), 'Segundo clique deve ocultar evidências sem conflito de listeners');

    console.log('NODE_GENUI_DECISION_MENTOR_OK');
    process.exit(0);
    """

    res = subprocess.run(
        ["node", "-e", node_script],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8"
    )

    if res.returncode != 0:
        print("[ERRO NODE.JS]:\n", res.stderr)
        print("[STDOUT NODE.JS]:\n", res.stdout)
        raise RuntimeError(f"Validações Headless em Node.js falharam com código {res.returncode}")

    assert "NODE_GENUI_DECISION_MENTOR_OK" in res.stdout, "Asserção final Node.js não encontrada no stdout"
    print("   [OK] Testes headless em Node.js finalizados com 100% de sucesso.")


# =============================================================================
# ETAPA 4: VALIDAÇÃO DE REGRESSÃO ZERO NAS 5 SUÍTES ANTERIORES
# =============================================================================

def test_zero_regression():
    print("\n5. Executando Validação de Regressão Zero nas 5 Suítes Analíticas Anteriores...")

    suites = [
        ("test_genui_baseline.py", "Fase 0 — Linha de Base GenUI, Registry & OWASP LLM03"),
        ("test_genui_engine_sse.py", "Fase 1 — Backend SSE Multiplexado & Envelopes"),
        ("test_genui_frontend_streaming.py", "Fase 2 — Streaming Parser, Buffer & Skeleton UI"),
        ("test_aura_aux_panel.py", "Companion Canvas — Split View, 4 Perspectivas & Responsividade"),
        ("test_phase6_quality_resilience.py", "Resiliência Operacional, WCAG 2.1 AA & Qualidade"),
    ]

    for script_name, desc in suites:
        script_path = BASE_DIR / "scripts" / script_name
        print(f"   ► Executando {script_name} ({desc})...")
        res = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        if res.returncode != 0:
            print(f"[FALHA EM {script_name}]:")
            print(res.stderr or res.stdout)
            raise RuntimeError(f"Regressão detectada em {script_name}! Código de saída: {res.returncode}")
        print(f"     [OK] {script_name} aprovado com 100% de sucesso.")

    print("\n   [OK] Regressão zero garantida em todas as 5 suítes analíticas anteriores.")


# =============================================================================
# RUNNER PRINCIPAL
# =============================================================================

def main():
    print("=" * 78)
    print("🚀 SUÍTE DE TESTES: MICRO-WIDGET PILOTO ExecutiveDecisionMentorUI (FASE 3 — P0)")
    print("   (Contratos Pydantic, 3 Camadas Deluxe, DOM, Streaming & Zero Regressão)")
    print("=" * 78)

    try:
        test_pydantic_contracts_executive_decision()
        test_backend_tool_and_router()
        test_engine_streaming_and_fastapi_sse()
        test_nodejs_headless_decision_mentor()
        test_zero_regression()

        print("\n" + "=" * 78)
        print("🎉 FASE 3: ExecutiveDecisionMentorUI HOMOLOGADO COM 100% DE SUCESSO!")
        print("   3 Camadas Concêntricas, Contratos Pydantic, Zero CLS e Zero Regressão.")
        print("=" * 78)
        return 0

    except Exception as e:
        print(f"\n❌ ERRO NA EXECUÇÃO DA SUÍTE FASE 3: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
