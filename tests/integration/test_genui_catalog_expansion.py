"""
Suite de Testes Automatizada: Expansao do Catalogo de Micro-Widgets do Mentor de Decisoes (Fase 6 - P2)
Valida contratos Pydantic v2, Backend Engine SSE, Node.js Headless DOM/XSS, State Locking e Regressao Zero.
"""

import sys
import json
import re
import asyncio
import subprocess
from pathlib import Path
from decimal import Decimal
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

from pydantic import ValidationError
from fastapi.testclient import TestClient

from core.schemas.genui import (
    FuelMarginItem,
    PaymentFeeImpactItem,
    MarginAnalysisProps,
    ScenarioPoint,
    PredictiveScenarioProps,
    BenchmarkComparisonItem,
    BenchmarkComparisonProps,
    FinancialLeakItem,
    FinancialLeakAuditProps,
    UpsellComboItem,
    BasketUpsellStrategyProps,
    ExecutiveMetric,
    ExecutiveImpactProjection,
    ExecutiveEvidenceItem,
    ExecutiveDecisionProps,
    GenUIActionOption,
    GenUIEnvelope,
    ActionExecuteRequest,
    ActionVoucher,
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
from core.aura_api import create_aura_app, _dispatch_business_action


# =============================================================================
# ETAPA 1: VALIDACAO DOS MODELOS PYDANTIC V2 DA FASE 6 (F6-01)
# =============================================================================

def test_pydantic_catalog_contracts():
    print("\n1. Testando Contratos Pydantic v2 dos 5 Novos Micro-Widgets da Fase 6...")

    # 1.1 MarginAnalysisProps
    f1 = FuelMarginItem(
        combustivel="Gasolina Comum",
        volume_litros=14500.0,
        preco_venda=5.89,
        custo_aquisicao=5.10,
        margem_liquida_pct=13.41,
        margem_alvo_pct=15.0,
        benchmark_mercado=5.92,
        elasticidade="Media"
    )
    p1 = PaymentFeeImpactItem(
        modalidade="Cartao Credito",
        taxa_media_pct=2.45,
        volume_financeiro=62400.0,
        desconto_taxas_reais=1528.80,
        impacto_margem_pct=1.52
    )
    margin_props = MarginAnalysisProps(
        diagnosis="Margem liquida real consolidada em 13.8%.",
        confidence_score=0.95,
        consolidated_margin_pct=13.8,
        fuel_margins=[f1],
        payment_fee_impact=[p1],
        limitations=["Taxas estimadas via lote TEF"],
        suggested_actions=[
            GenUIActionOption(
                action_id=generate_action_id(),
                label="Simular Repasse",
                action_type="mutation",
                variant="primary",
                payload={"operacao": "repassar_custo"}
            )
        ]
    )
    assert margin_props.consolidated_margin_pct == 13.8
    assert len(margin_props.fuel_margins) == 1
    assert len(margin_props.payment_fee_impact) == 1

    # Validacao de diagnosis vazio em MarginAnalysisProps
    try:
        MarginAnalysisProps(
            diagnosis="   ",
            confidence_score=0.95,
            consolidated_margin_pct=13.8
        )
        assert False, "Deveria falhar com diagnosis vazio em MarginAnalysisProps"
    except ValidationError:
        pass

    # 1.2 PredictiveScenarioProps
    sp_base = ScenarioPoint(
        preco_medio=5.89,
        volume_projetado=120000.0,
        receita_liquida=706800.0,
        margem_contribuicao_pct=14.2
    )
    sp_sim = ScenarioPoint(
        preco_medio=5.99,
        volume_projetado=118680.0,
        receita_liquida=710893.2,
        margem_contribuicao_pct=14.9
    )
    scen_props = PredictiveScenarioProps(
        scenario_title="Simulacao de Frete +3%",
        hypothesis="Repasse de R$ 0,10 na gasolina comum",
        base_scenario=sp_base,
        simulated_scenario=sp_sim,
        delta_volume_pct=-1.1,
        delta_revenue=4093.20,
        delta_margin_pct=0.7,
        confidence_score=0.93,
        diagnosis="Repasse viabiliza ganho financeiro liquido projetado.",
        elasticity_coefficient=-0.65,
        assumptions=["Concorrentes estaveis"],
        limitations=["Sem guerra de precos"],
        suggested_actions=[]
    )
    assert scen_props.delta_margin_pct == 0.7
    assert scen_props.base_scenario.preco_medio == 5.89

    # 1.3 BenchmarkComparisonProps
    b_item = BenchmarkComparisonItem(
        kpi_name="Preco Gasolina Comum",
        filial_value="R$ 5,89",
        benchmark_value="R$ 5,94",
        gap_value="-R$ 0,05",
        status="success",
        observation="Preco mais agressivo"
    )
    bench_props = BenchmarkComparisonProps(
        diagnosis="Filial competitiva na regiao central.",
        confidence_score=0.94,
        competitiveness_score=86.0,
        entity_name="Filial 01 Centro",
        benchmark_group="Raio 3km",
        comparison_items=[b_item],
        limitations=[],
        suggested_actions=[]
    )
    assert bench_props.competitiveness_score == 86.0
    assert bench_props.comparison_items[0].status == "success"

    # 1.4 FinancialLeakAuditProps
    leak_item = FinancialLeakItem(
        category="Quebra de Caixa",
        description="Falta de dinheiro fisico na gaveta",
        amount=85.00,
        status="critical",
        pdv_or_terminal="PDV 01"
    )
    leak_props = FinancialLeakAuditProps(
        diagnosis="Alerta de fuga financeira apurado no fechamento.",
        severity="attention",
        confidence_score=0.98,
        total_leak_value=385.50,
        cash_break_value=85.00,
        pending_bleed_value=250.00,
        tef_divergence_value=50.50,
        leak_items=[leak_item],
        limitations=[],
        suggested_actions=[]
    )
    assert leak_props.total_leak_value == 385.50
    assert leak_props.severity == "attention"

    # 1.5 BasketUpsellStrategyProps
    combo_item = UpsellComboItem(
        anchor_product="Gasolina Aditivada",
        recommended_product="Aditivo STP",
        lift=3.45,
        confidence_pct=42.0,
        support_pct=15.8,
        additional_ticket_reais=29.90,
        script_pitch="Ofereca o aditivo na promocao",
        category="Pista"
    )
    basket_props = BasketUpsellStrategyProps(
        diagnosis="Potencial de aumento de ticket medio via cross-selling.",
        confidence_score=0.94,
        projected_ticket_increase=14.80,
        projected_monthly_revenue_lift=8920.00,
        top_combos=[combo_item],
        limitations=[],
        suggested_actions=[]
    )
    assert basket_props.projected_ticket_increase == 14.80
    assert basket_props.top_combos[0].lift == 3.45

    # 1.6 Envelope canônico com to_sse_payload()
    for comp_name, props_obj in [
        ("render_MarginAnalysisUI", margin_props),
        ("render_PredictiveScenarioUI", scen_props),
        ("render_BenchmarkComparisonUI", bench_props),
        ("render_FinancialLeakAuditUI", leak_props),
        ("render_BasketUpsellStrategyUI", basket_props),
    ]:
        env = GenUIEnvelope(
            schema_version="1.0",
            tool_call_id=generate_tool_call_id(),
            component_name=comp_name,
            executive_summary="Resumo executivo do micro-widget.",
            props=props_obj
        )
        assert env.schema_version == "1.0"
        sse_p = env.to_sse_payload()
        assert sse_p["envelope_version"] == "1.0"
        assert sse_p["summary_text"] == "Resumo executivo do micro-widget."
        assert "props" in sse_p

    print("   [OK] Todos os 5 contratos Pydantic v2 e envelopes validados com sucesso.")


# =============================================================================
# ETAPA 2: VALIDACAO BACKEND (TOOLS, ROUTER, ENVELOPE E FASTAPI ACTIONS)
# =============================================================================

def test_backend_catalog_integration():
    print("\n2. Testando Integracao Backend: Tools, Heuristic Router, Envelopes e Actions Gateway...")

    tools = PostoTools(rag_engine=None)

    # 2.1 PostoTools.gerar_diagnostico_mentoria_executiva() para todos os tipos
    tipos_esperados = {
        "analise_margem": "MarginAnalysisUI",
        "cenario_preditivo": "PredictiveScenarioUI",
        "benchmark_comparativo": "BenchmarkComparisonUI",
        "auditoria_fuga_financeira": "FinancialLeakAuditUI",
        "conveniencia_vendas_cruzadas": "BasketUpsellStrategyUI",
        "geral": "ExecutiveDecisionMentorUI",
    }
    for tipo, comp_esperado in tipos_esperados.items():
        res = tools.gerar_diagnostico_mentoria_executiva(tipo=tipo)
        assert res["status"] == "ok"
        assert res["client_component"] == comp_esperado
        assert "props" in res

    # 2.2 SemanticRouter heuristico
    perguntas_rotas = [
        ("análise de margem e taxas de cartão", "analise_margem"),
        ("cenário preditivo what-if de preço", "cenario_preditivo"),
        ("benchmark comparativo de concorrentes", "benchmark_comparativo"),
        ("auditoria de fuga financeira no caixa", "auditoria_fuga_financeira"),
        ("quais os combos mais vendidos da conveniência", "conveniencia_vendas_cruzadas"),
        ("onde estou perdendo margem", "mentoria_decisao"),
    ]
    for pergunta, intencao_esperada in perguntas_rotas:
        int_res = classificar_intencao_heuristica(pergunta)
        assert int_res == intencao_esperada, f"Pergunta '{pergunta}' roteou para '{int_res}', esperava '{intencao_esperada}'"

    # 2.3 build_canonical_genui_envelope
    for intencao, comp_esperado in [
        ("analise_margem", "render_MarginAnalysisUI"),
        ("cenario_preditivo", "render_PredictiveScenarioUI"),
        ("benchmark_comparativo", "render_BenchmarkComparisonUI"),
        ("auditoria_fuga_financeira", "render_FinancialLeakAuditUI"),
        ("conveniencia_vendas_cruzadas", "render_BasketUpsellStrategyUI"),
    ]:
        raw_data = tools.gerar_diagnostico_mentoria_executiva(tipo=intencao)
        tid = generate_tool_call_id()
        env = build_canonical_genui_envelope(
            intencao=intencao,
            tool_call_id=tid,
            resultado_bruto=raw_data,
            executive_summary=f"Sintese executiva de {intencao}"
        )
        assert env.component_name == comp_esperado
        assert len(env.actions) >= 3

    # 2.4 _dispatch_business_action
    acoes_teste = [
        ("repassar_custo", {"operacao": "repassar_custo"}, "REPASSE_CUSTO"),
        ("absorver_margem", {"operacao": "absorver_margem"}, "ABSORCAO_MARGEM"),
        ("revisar_estrategia", {"operacao": "revisar_estrategia"}, "REVISAO_ESTRATEGIA"),
        ("auditar_concorrencia", {"operacao": "auditar_concorrencia"}, "AUDITORIA_CONCORRENCIA"),
        ("abrir_chamado_tef", {"operacao": "abrir_chamado_tef"}, "CHAMADO_TEF"),
        ("lancar_campanha_frentistas", {"operacao": "lancar_campanha_frentistas"}, "CAMPANHA_FRENTISTAS"),
        ("ativar_combo_pdv", {"operacao": "ativar_combo_pdv"}, "ATIVACAO_COMBO_PDV"),
    ]
    for act_name, payload, tipo_esperado in acoes_teste:
        res_act = _dispatch_business_action(act_name, "mutation", payload, "operador_fase6")
        assert res_act["status"] == "APPROVED"
        assert res_act["tipo"] == tipo_esperado
        assert "confirmacao_erp" in res_act

    # 2.5 Endpoint FastAPI /api/v1/aura/actions/execute com Idempotencia e Voucher
    engine = AuraEngine()
    app = create_aura_app(engine=engine)
    client = TestClient(app)

    aid = generate_action_id()
    tid = generate_tool_call_id()
    req_payload = {
        "action_id": aid,
        "tool_call_id": tid,
        "action_name": "repassar_custo",
        "action_type": "mutation",
        "operator_id": "operador_01",
        "session_id": "test_sess_catalog",
        "payload": {"operacao": "repassar_custo", "produto": "Gasolina Comum", "delta_preco": 0.10}
    }
    resp1 = client.post("/api/v1/aura/actions/execute", json=req_payload)
    assert resp1.status_code == 200, f"Falha na primeira chamada de acao: {resp1.text}"
    v1 = resp1.json()
    assert v1["status"] == "APPROVED"
    assert v1["action_id"] == aid
    assert v1["signature"] != ""

    # Teste de idempotencia: reenvio com mesmo action_id
    resp2 = client.post("/api/v1/aura/actions/execute", json=req_payload)
    assert resp2.status_code == 200
    v2 = resp2.json()
    assert v2["voucher_id"] == v1["voucher_id"], "Idempotencia violada: gerou novo voucher_id"
    assert v2["signature"] == v1["signature"]

    print("   [OK] Integracao backend, PostoTools, rotas e gateway de acoes aprovados.")


# =============================================================================
# ETAPA 3: VALIDACAO DE STREAMING SSE NO MOTOR AURAENGINE
# =============================================================================

def test_aura_engine_streaming_catalog():
    print("\n3. Testando Streaming Multiplexado SSE com os Novos Micro-Widgets...")

    engine = AuraEngine()

    async def stream_query(query: str):
        chunks = []
        async for chunk in engine.ask_stream(query, session_id="test_stream_catalog"):
            chunks.append(chunk)
        return chunks

    test_queries = [
        ("Simulação preditiva what-if de preço", "render_PredictiveScenarioUI"),
        ("Auditoria de fuga financeira no caixa", "render_FinancialLeakAuditUI"),
    ]

    for q, comp_esperado in test_queries:
        chunks = asyncio.run(stream_query(q))
        types = [c.chunk_type.value for c in chunks]

        assert "intent" in types, f"Faltou INTENT para '{q}'"
        assert "ui_skeleton" in types, f"Faltou UI_SKELETON para '{q}'"
        assert "delta" in types, f"Faltou DELTA para '{q}'"
        assert "ui_complete" in types, f"Faltou UI_COMPLETE para '{q}'"
        assert "done" in types, f"Faltou DONE para '{q}'"

        # Ordem cronológica estrita
        idx_skel = types.index("ui_skeleton")
        idx_delta = types.index("delta")
        idx_comp = types.index("ui_complete")
        idx_done = types.index("done")
        assert idx_skel < idx_delta < idx_comp < idx_done

        # Conteúdo do UI_SKELETON e UI_COMPLETE
        skel = next(c for c in chunks if c.chunk_type == AuraChunkType.UI_SKELETON)
        assert skel.data.get("component_name") == comp_esperado

        comp = next(c for c in chunks if c.chunk_type == AuraChunkType.UI_COMPLETE)
        assert comp.data.get("component_name") == comp_esperado
        assert "props" in comp.data
        assert comp.data["props"].get("confidence_score") is not None

        # Zero vazamento de JSON em DELTA
        deltas = [c.text for c in chunks if c.chunk_type == AuraChunkType.DELTA and c.text]
        full_text = "".join(deltas)
        assert not full_text.strip().startswith("{")
        assert "```json" not in full_text

    print("   [OK] Cronologia SSE e envelopes multiplexados validados no AuraEngine.")


# =============================================================================
# ETAPA 4: TESTES HEADLESS NO NODE.JS (WIDGETS, 3 CAMADAS, STATE LOCK E DOM)
# =============================================================================

def test_nodejs_headless_catalog_widgets():
    print("\n4. Testando Micro-Widgets no Node.js Headless (Montagem DOM, 3 Camadas, State Lock, XSS)...")

    widgets_js = BASE_DIR / "web" / "js" / "aura-genui-widgets.js"
    genui_js = BASE_DIR / "web" / "js" / "aura-genui.js"
    assert widgets_js.exists(), f"Arquivo {widgets_js} nao encontrado"
    assert genui_js.exists(), f"Arquivo {genui_js} nao encontrado"

    node_script = f"""
    const assert = require('assert');
    const path = require('path');

    const widgetsPath = {json.dumps(str(widgets_js.resolve()))};
    const genuiPath = {json.dumps(str(genui_js.resolve()))};

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
        if (idx >= 0) {{
          oldNode.parentNode = null;
          newNode.parentNode = this;
          this.children[idx] = newNode;
        }}
      }}
      querySelector(sel) {{
        if (this._innerHTML.includes(sel.replace('.', ''))) {{
          const m = new MockNode('div');
          m.parentNode = this;
          return m;
        }}
        return null;
      }}
      querySelectorAll(sel) {{
        return [];
      }}
      get innerHTML() {{ return this._innerHTML; }}
      set innerHTML(html) {{
        this._innerHTML = html;
        this.children = [];
        const btnMatches = html.match(/<button[^>]*>([\\s\\S]*?)<\\/button>/gi) || [];
        for (let bHtml of btnMatches) {{
          const bNode = new MockNode('button');
          bNode._innerHTML = bHtml;
          const actMatch = bHtml.match(/data-action-id="([^"]+)"/);
          if (actMatch) bNode.setAttribute('data-action-id', actMatch[1]);
          const clsMatch = bHtml.match(/class="([^"]+)"/);
          if (clsMatch) bNode.className = clsMatch[1];
          this.appendChild(bNode);
        }}
      }}
    }}

    global.document = {{
      createElement(tag) {{ return new MockNode(tag); }},
      getElementById(id) {{ return null; }}
    }};

    // Mock das APIs de apoio globais da AURA
    let lastProjectedArtifact = null;
    let lastToast = null;
    global.window = {{
      document: global.document,
      auraAuxPanel: {{
        projectArtifact(art) {{ lastProjectedArtifact = art; }}
      }},
      auraFx: {{
        showToast(msg, type) {{
          if (typeof msg === 'object' && msg !== null) {{
            lastToast = msg;
          }} else {{
            lastToast = {{ msg, type: type || 'info' }};
          }}
        }}
      }},
      auraApi: {{
        async executeAction(actionId, props) {{
          await new Promise(r => setTimeout(r, 25));
          if (actionId.includes('fail')) throw new Error('Falha simulada de rede');
          return {{
            voucher_id: 'vouch-999',
            action_id: actionId,
            status: 'APPROVED',
            signature: 'sig-abc'
          }};
        }}
      }}
    }};

    const {{ SecureComponentRegistry }} = require(genuiPath);
    const widgets = require(widgetsPath);
    const {{
      BaseGenUIWidget,
      MarginAnalysisUI,
      PredictiveScenarioUI,
      BenchmarkComparisonUI,
      FinancialLeakAuditUI,
      BasketUpsellStrategyUI,
      ExecutiveDecisionMentorUI,
      registerWidgets,
      escapeHtml
    }} = widgets;

    // 1. Validacao de Registro de Todos os Componentes
    const registry = new SecureComponentRegistry();
    registerWidgets(registry);
    const compList = registry.listComponents();
    const compNames = compList.map(c => c.name);

    assert(compNames.includes('render_MarginAnalysisUI'), 'MarginAnalysisUI ausente do registry');
    assert(compNames.includes('render_PredictiveScenarioUI'), 'PredictiveScenarioUI ausente do registry');
    assert(compNames.includes('render_BenchmarkComparisonUI'), 'BenchmarkComparisonUI ausente do registry');
    assert(compNames.includes('render_FinancialLeakAuditUI'), 'FinancialLeakAuditUI ausente do registry');
    assert(compNames.includes('render_BasketUpsellStrategyUI'), 'BasketUpsellStrategyUI ausente do registry');
    assert(compNames.includes('render_ExecutiveDecisionMentorUI'), 'ExecutiveDecisionMentorUI ausente do registry');

    // 2. Montagem e Validacao das 3 Camadas Concêntricas para cada Widget
    const testCases = [
      {{
        Class: MarginAnalysisUI,
        name: 'MarginAnalysisUI',
        envelope: {{
          tool_call_id: 'tool-marg-123',
          props: {{
            diagnosis: 'Margem liquida em 13.8% com pressao de taxas TEF.',
            confidence_score: 0.95,
            consolidated_margin_pct: 13.8,
            fuel_margins: [
              {{ combustivel: 'Gasolina Comum', volume_litros: 14500, preco_venda: 5.89, custo_aquisicao: 5.10, margem_liquida_pct: 13.41 }}
            ],
            payment_fee_impact: [
              {{ modalidade: 'Cartao Credito', taxa_media_pct: 2.45, volume_financeiro: 62400, desconto_taxas_reais: 1528.80 }}
            ],
            suggested_actions: [
              {{ action_id: 'act-marg-1', label: 'Simular Repasse', variant: 'primary' }}
            ]
          }}
        }}
      }},
      {{
        Class: PredictiveScenarioUI,
        name: 'PredictiveScenarioUI',
        envelope: {{
          tool_call_id: 'tool-scen-123',
          props: {{
            scenario_title: 'Simulacao de Frete e Demanda',
            hypothesis: 'Repasse de R$ 0,10 no litro',
            base_scenario: {{ preco_medio: 5.89, volume_projetado: 120000, receita_liquida: 706800, margem_contribuicao_pct: 14.2 }},
            simulated_scenario: {{ preco_medio: 5.99, volume_projetado: 118680, receita_liquida: 710893, margem_contribuicao_pct: 14.9 }},
            delta_volume_pct: -1.1,
            delta_revenue: 4093.20,
            delta_margin_pct: 0.7,
            confidence_score: 0.93,
            diagnosis: 'Repasse eleva margem com retencao de volume.',
            suggested_actions: [
              {{ action_id: 'act-scen-1', label: 'Repassar Custo', variant: 'primary' }}
            ]
          }}
        }}
      }},
      {{
        Class: BenchmarkComparisonUI,
        name: 'BenchmarkComparisonUI',
        envelope: {{
          tool_call_id: 'tool-bench-123',
          props: {{
            diagnosis: 'Filial lider em conversao no raio central.',
            confidence_score: 0.94,
            competitiveness_score: 86.0,
            entity_name: 'Filial 01',
            benchmark_group: 'Raio 3km',
            comparison_items: [
              {{ kpi_name: 'Preco Gasolina', filial_value: 'R$ 5,89', benchmark_value: 'R$ 5,94', gap_value: '-R$ 0,05', status: 'success' }}
            ],
            suggested_actions: [
              {{ action_id: 'act-bench-1', label: 'Revisar Estrategia', variant: 'primary' }}
            ]
          }}
        }}
      }},
      {{
        Class: FinancialLeakAuditUI,
        name: 'FinancialLeakAuditUI',
        envelope: {{
          tool_call_id: 'tool-leak-123',
          props: {{
            diagnosis: 'Alerta de Fuga Financeira: R$ 385,50 apurados.',
            severity: 'attention',
            confidence_score: 0.98,
            total_leak_value: 385.50,
            cash_break_value: 85.00,
            pending_bleed_value: 250.00,
            tef_divergence_value: 50.50,
            leak_items: [
              {{ category: 'Quebra de Caixa', description: 'Gaveta divergente', amount: 85.00, status: 'critical' }}
            ],
            suggested_actions: [
              {{ action_id: 'act-leak-1', label: 'Estancar Quebra', variant: 'danger' }}
            ]
          }}
        }}
      }},
      {{
        Class: BasketUpsellStrategyUI,
        name: 'BasketUpsellStrategyUI',
        envelope: {{
          tool_call_id: 'tool-upsell-123',
          props: {{
            diagnosis: 'Oportunidades de vendas cruzadas com alto Lift.',
            confidence_score: 0.94,
            projected_ticket_increase: 14.80,
            projected_monthly_revenue_lift: 8920.00,
            top_combos: [
              {{ anchor_product: 'Gasolina', recommended_product: 'Aditivo', lift: 3.45, confidence_pct: 42, additional_ticket_reais: 29.90, script_pitch: 'Ofereca aditivo' }}
            ],
            suggested_actions: [
              {{ action_id: 'act-upsell-1', label: 'Ativar Combo', variant: 'primary' }}
            ]
          }}
        }}
      }}
    ];

    for (let tc of testCases) {{
      const inst = new tc.Class(tc.envelope);
      const root = inst.mount();
      assert(root !== null, `Mount falhou para ${{tc.name}}`);
      const html = inst.element.innerHTML;

      // 3 Camadas presentes
      assert(html.includes('genui-layer-1'), `genui-layer-1 ausente em ${{tc.name}}`);
      assert(html.includes('genui-layer-2'), `genui-layer-2 ausente em ${{tc.name}}`);
      assert(html.includes('genui-layer-3'), `genui-layer-3 ausente em ${{tc.name}}`);

      // Projecao no Companion Canvas
      inst.projectToCanvas();
      assert(lastProjectedArtifact !== null, `Canvas nao acionado para ${{tc.name}}`);
      assert(lastProjectedArtifact.id && lastProjectedArtifact.id.length > 0);
      assert(lastProjectedArtifact.toolName && lastProjectedArtifact.toolName.length > 0);
    }}

    // 3. Teste de State Locking e Idempotencia no Clique
    async function testStateLock() {{
      const inst = new MarginAnalysisUI({{
        tool_call_id: 'tool-lock-test',
        props: {{
          diagnosis: 'Diagnostico de teste de bloqueio.',
          confidence_score: 0.95,
          consolidated_margin_pct: 14.0,
          suggested_actions: [
            {{ action_id: 'act-lock-primary', label: 'Executar Repasse', variant: 'primary' }}
          ]
        }}
      }});
      inst.mount();
      const btn = inst.element.children.find(c => c.getAttribute('data-action-id') === 'act-lock-primary');
      assert(btn, 'Botao de acao nao encontrado no DOM');

      // Primeiro clique
      const promiseClick = inst.handleActionClick('act-lock-primary', 'mutation', btn);
      assert(inst.isLocked === true, 'isLocked deveria ser true apos o clique');

      // Segundo clique imediato concorrente (deve ser ignorado)
      const resConcurrent = await inst.handleActionClick('act-lock-primary', 'mutation', btn);
      assert(resConcurrent === false, 'Segundo clique nao foi descartado de forma idempotente');

      await promiseClick;
      assert(inst.isCommitted === true, 'isCommitted deveria ser true apos confirmacao');
      assert(inst.renderLayer3().includes('VOUCHER AUDITADO') || inst.element.innerHTML.includes('VOUCHER AUDITADO'), 'Badge de voucher auditado ausente');
    }}

    // 4. Teste de Rollback Otimista em Falha de Rede
    async function testRollback() {{
      const inst = new PredictiveScenarioUI({{
        tool_call_id: 'tool-fail-test',
        props: {{
          diagnosis: 'Cenario com falha simulada.',
          confidence_score: 0.90,
          base_scenario: {{ preco_medio: 5.89, volume_projetado: 100000, receita_liquida: 589000, margem_contribuicao_pct: 14 }},
          simulated_scenario: {{ preco_medio: 5.99, volume_projetado: 99000, receita_liquida: 593010, margem_contribuicao_pct: 14.5 }},
          delta_volume_pct: -1,
          delta_revenue: 4010,
          delta_margin_pct: 0.5,
          suggested_actions: [
            {{ action_id: 'act-fail-network', label: 'Acao com Falha', variant: 'primary' }}
          ]
        }}
      }});
      inst.mount();
      const btn = inst.element.children.find(c => c.getAttribute('data-action-id') === 'act-fail-network');
      assert(btn, 'Botao de falha nao encontrado');

      await inst.handleActionClick('act-fail-network', 'mutation', btn);
      assert(inst.isLocked === false, 'isLocked deveria retornar a false apos rollback');
      assert(inst.isCommitted === false, 'isCommitted nao deveria ser true em erro');
      assert(lastToast !== null && lastToast.type === 'error', 'Toast de erro nao disparado no rollback');
    }}

    // 5. Sanitizacao Rigorosa contra XSS e Prompt Injection (OWASP LLM01)
    function testXSSSanitization() {{
      const xssDiagnosis = '<script>alert("XSS")</script><img src=x onerror=alert(1)> Perigo';
      const safe = escapeHtml(xssDiagnosis);
      assert(!safe.includes('<script>'), 'Tag script vazada');
      assert(!safe.includes('<img'), 'Tag img vazada');
      assert(safe.includes('&lt;script&gt;'), 'Script nao foi escapado');
      assert(safe.includes('&lt;img'), 'Img nao foi escapada');

      const inst = new FinancialLeakAuditUI({{
        tool_call_id: 'tool-xss-test',
        props: {{
          diagnosis: xssDiagnosis,
          severity: 'attention',
          confidence_score: 0.99,
          total_leak_value: 100,
          leak_items: [
            {{ category: '<script>evil()</script>', description: '<b onmouseover=evil()>Desc</b>', amount: 50, status: 'warning' }}
          ]
        }}
      }});
      inst.mount();
      assert(!inst.element.innerHTML.includes('<script>evil()</script>'), 'XSS vazou nos itens de vazamento');
      assert(inst.element.innerHTML.includes('&lt;script&gt;'), 'Tags script nao foram sanitizadas');
    }}

    (async () => {{
      await testStateLock();
      await testRollback();
      testXSSSanitization();
      console.log('NODE_GENUI_CATALOG_EXPANSION_OK');
    }})();
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
        raise RuntimeError(f"Validacoes Headless em Node.js falharam com codigo {res.returncode}")

    assert "NODE_GENUI_CATALOG_EXPANSION_OK" in res.stdout, "Assercao final Node.js nao encontrada no stdout"
    print("   [OK] Testes headless em Node.js finalizados com 100% de sucesso.")


# =============================================================================
# ETAPA 5: VALIDACAO DE REGRESSAO ZERO NAS SUITES ANTERIORES
# =============================================================================

def test_zero_regression():
    print("\n5. Executando Validacao de Regressao Zero nas Suites Homologadas Anteriores...")

    suites = [
        ("test_genui_baseline.py", "Fase 0: Linha de Base GenUI, Registry & OWASP LLM03"),
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

    print("\n   [OK] Regressao zero garantida em todas as suites atomicas anteriores.")


# =============================================================================
# RUNNER PRINCIPAL
# =============================================================================

def main():
    print("=" * 78)
    print("🚀 SUITE DE TESTES: EXPANSAO DO CATALOGO DE MICRO-WIDGETS GENUI (FASE 6 - P2)")
    print("   (MarginAnalysis, PredictiveScenario, Benchmark, FinancialLeak, BasketUpsell)")
    print("=" * 78)

    try:
        test_pydantic_catalog_contracts()
        test_backend_catalog_integration()
        test_aura_engine_streaming_catalog()
        test_nodejs_headless_catalog_widgets()
        test_zero_regression()

        print("\n" + "=" * 78)
        print("🎉 FASE 6: CATALOGO DE MICRO-WIDGETS HOMOLOGADO COM 100% DE SUCESSO!")
        print("   Contratos Pydantic v2, 3 Camadas Deluxe, DOM, Streaming & Zero Regressao.")
        print("=" * 78)
        return 0

    except Exception as e:
        print(f"\n❌ ERRO NA EXECUCAO DA SUITE FASE 6: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
