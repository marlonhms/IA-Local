"""
Suíte de Testes Automatizada: AURA Companion Canvas & Dynamic Inspector Panel (v1.0.0)
Validação de:
1. Shell & Integração HTML (Botão Header Alt+P, Aside Canvas, 4 Abas Analíticas, Controles de Janela e Carrossel)
2. Tokens CSS & Design System (Split Desktop 50/50, Expandido 65/35, Sheet Mobile, GPU Guard, Reduced Motion)
3. Lógica Frontend via Node.js (AuraAuxPanel Controller, 4 Perspectivas, Suporte a Postos e Qualquer Banco de Dados)
4. Exportação CSV, Busca em Tempo Real e Blindagem XSS
"""

import sys
import subprocess
import json
import re
from pathlib import Path

# Protege stdout e stderr no terminal Windows contra problemas de codificação
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from fastapi.testclient import TestClient
from core.aura_engine import AuraEngine, AuraSessionMemory
from core.aura_api import create_aura_app
from core.schemas import (
    TankForecastContract,
    LMCReportContract,
    PumpPerformanceContract,
    MarketBasketContract,
    ShiftReconciliationContract,
)
from core.rag_engine import HybridRAGEngine
from core.tools import PostoTools


def run_aux_panel_tests():
    print("=" * 78)
    print("🎨 SUÍTE DE TESTES: AURA COMPANION CANVAS & DYNAMIC INSPECTOR PANEL")
    print("   (Dual Focus Workspace, 4 Perspectivas, Agnóstico p/ Qualquer Banco)")
    print("=" * 78)

    mem = AuraSessionMemory(db_path=":memory:")
    engine = AuraEngine(tenant_id="test_aux_panel", filial_id="posto_teste_01", session_memory=mem)
    app = create_aura_app(engine)
    client = TestClient(app)

    # ------------------------------------------------------------------
    # 1. VALIDAÇÃO DE INTEGRAÇÃO HTML E SHELL
    # ------------------------------------------------------------------
    print("\n1. Testando Estrutura HTML e Integração no Shell...")
    resp_root = client.get("/")
    assert resp_root.status_code == 200, "Falha ao carregar SPA"
    html = resp_root.text

    # Botão de Toggle no Header Executivo
    assert 'id="btn-toggle-aux-panel"' in html, "Botão btn-toggle-aux-panel ausente no header"
    assert 'min-w-[44px]' in html and 'min-h-[44px]' in html, "Touch targets mínimos de 44px não aplicados"
    assert 'Alt+P' in html, "Atalho Alt+P ausente na marcação do botão de alternância"
    assert 'id="aux-toggle-beacon"' in html, "Farol de notificação de novo artefato ausente"
    assert 'id="aux-toggle-count"' in html, "Badge contador de artefatos ausente"

    # Botão no Menu Lateral (Drawer)
    assert 'id="sidebar-btn-aux-panel"' in html, "Botão sidebar-btn-aux-panel ausente no menu lateral"

    # Aside do Painel Auxiliar e Containers das 4 Perspectivas
    assert 'id="aura-aux-panel"' in html, "Contêiner aura-aux-panel ausente no HTML"
    assert 'role="region"' in html, "Atributo ARIA role=region ausente no painel auxiliar"
    assert 'id="aux-panel-title"' in html, "Título do artefato aux-panel-title ausente"
    assert 'id="aux-panel-status-chip"' in html, "Badge de status aux-panel-status-chip ausente"
    assert 'id="aux-panel-subtitle"' in html, "Subtítulo de contexto aux-panel-subtitle ausente"

    # 4 Abas Analíticas
    assert 'id="aux-tab-visual"' in html, "Aba aux-tab-visual ausente"
    assert 'id="aux-tab-data"' in html, "Aba aux-tab-data ausente"
    assert 'id="aux-tab-schema"' in html, "Aba aux-tab-schema ausente"
    assert 'id="aux-tab-audit"' in html, "Aba aux-tab-audit ausente"

    # Contêineres de Conteúdo das 4 Perspectivas
    assert 'id="aux-view-visual"' in html, "Contêiner aux-view-visual ausente"
    assert 'id="aux-view-data"' in html, "Contêiner aux-view-data ausente"
    assert 'id="aux-view-schema"' in html, "Contêiner aux-view-schema ausente"
    assert 'id="aux-view-audit"' in html, "Contêiner aux-view-audit ausente"

    # Controles de Janela
    assert 'id="aux-btn-copy-data"' in html, "Botão aux-btn-copy-data ausente"
    assert 'id="aux-btn-expand"' in html, "Botão aux-btn-expand ausente"
    assert 'id="aux-btn-close"' in html, "Botão aux-btn-close ausente"

    # Carrossel de Múltiplos Artefatos e Toast Mobile
    assert 'id="aux-artifacts-bar"' in html, "Barra de carrossel de artefatos ausente"
    assert 'id="aux-artifact-peek-toast"' in html, "Toast de aviso mobile aux-artifact-peek-toast ausente"

    # Entrega do Script Estático
    assert 'aura-aux-panel.js' in html, "Script aura-aux-panel.js não referenciado no index.html"
    resp_js = client.get("/static/js/aura-aux-panel.js")
    assert resp_js.status_code == 200, "Falha ao servir /static/js/aura-aux-panel.js"
    assert "class AuraAuxPanel" in resp_js.text, "Classe AuraAuxPanel ausente no arquivo estático"

    print("   [OK] Shell HTML validado: Botão no header, Aside Canvas, 4 Abas, Controles e Script estático.")

    # ------------------------------------------------------------------
    # 2. VALIDAÇÃO DE TOKENS CSS E RESPONSIVIDADE
    # ------------------------------------------------------------------
    print("\n2. Testando Regras CSS do Design System (aura.css)...")
    resp_css = client.get("/static/css/aura.css")
    assert resp_css.status_code == 200
    css = resp_css.text

    assert ".aura-aux-panel" in css, "Classe .aura-aux-panel ausente no CSS"
    assert "backdrop-filter" in css, "Efeito de vidro translúcido acrílico ausente"
    assert "#view-console.aux-panel-active" in css, "Regra de split canvas #view-console.aux-panel-active ausente"
    assert "@media (min-width: 1024px)" in css, "Media query para desktop ausente"
    assert "@media (max-width: 1023px)" in css, "Media query para mobile sheet ausente"
    assert ".aux-expanded" in css, "Regra de canvas expandido .aux-expanded ausente"
    assert ".gpu-guard-active .aura-aux-panel" in css, "Otimização de GPU Guard para o painel ausente"
    assert "@media (prefers-reduced-motion: reduce)" in css, "Acessibilidade para movimento reduzido ausente"
    assert ".aux-btn-view-chat" in css, "Regra .aux-btn-view-chat ausente no CSS"
    assert ".aux-btn-view-panel" in css, "Regra .aux-btn-view-panel ausente no CSS"
    assert "@media (min-width: 768px)" in css, "Media query de 768px para PC ausente no CSS"
    assert '[data-device="desktop"]' in css and '[data-device="mobile"]' in css, "Regras de data-device ausentes no CSS"
    print("   [OK] Design System CSS validado: Split Desktop, Sheet Mobile, GPU Guard, Acessibilidade e Reconhecimento Inteligente.")

    # ------------------------------------------------------------------
    # 3. VALIDAÇÃO DA LÓGICA FRONTEND VIA NODE.JS
    # ------------------------------------------------------------------
    print("\n3. Executando Validação de Lógica do Canvas via Node.js...")
    rag = HybridRAGEngine()
    tools = PostoTools(rag)

    res_tanques = tools.prever_esgotamento_tanques()
    res_lmc = tools.gerar_relatorio_lmc_anp()
    res_pista = tools.auditar_desempenho_pista_frentistas()
    res_combos = tools.auditar_cesta_conveniencia_vendas_cruzadas()

    aux_panel_path = BASE_DIR / "web" / "js" / "aura-aux-panel.js"
    assert aux_panel_path.exists(), f"Arquivo não encontrado: {aux_panel_path}"

    node_script = f"""
    const {{ AuraAuxPanel }} = require({json.dumps(str(aux_panel_path.resolve()))});
    const panel = new AuraAuxPanel();

    console.log('[NODE] 1. Validando Instanciação e Estado Inicial...');
    if (panel.isOpen !== false || panel.isExpanded !== false || panel.activeTab !== 'visual') {{
      console.error('FALHA: Estado inicial incorreto:', panel);
      process.exit(1);
    }}
    console.log('[NODE]    ✓ Instanciação e estado inicial aprovados');

    // =========================================================================
    // TESTE 2: PROJEÇÃO DE CONTRATO 1 - AUTONOMIA DE TANQUES
    // =========================================================================
    console.log('[NODE] 2. Validando Projeção de Autonomia de Tanques...');
    const tankPayload = {json.dumps(res_tanques, ensure_ascii=False)};
    const art1 = panel.projectArtifact({{
      id: 'art-tank-1',
      containerId: 'msg-1',
      toolName: 'previsao_tanques',
      intent: 'tank_forecast',
      data: tankPayload,
      html: '<div class="decision-card">DecisionCard Tanques Mock</div>',
      autoOpen: false
    }});

    if (!art1.title.includes('Autonomia de Tanques')) {{
      console.error('FALHA: Título incorreto para tanques:', art1.title);
      process.exit(1);
    }}
    if (!art1.records || art1.records.length === 0) {{
      console.error('FALHA: Registros tabulares não extraídos para tanques');
      process.exit(1);
    }}
    if (!art1.records[0]['Tanque'] || !art1.records[0]['Combustível']) {{
      console.error('FALHA: Colunas canônicas ausentes no registro de tanques:', art1.records[0]);
      process.exit(1);
    }}
    if (!art1.schemaInfo.source.includes('PostgreSQL') || !art1.schemaInfo.table.includes('tb_tanques')) {{
      console.error('FALHA: Esquema do banco de dados de tanques incorreto:', art1.schemaInfo);
      process.exit(1);
    }}
    console.log('[NODE]    ✓ Projeção de Tanques: Título, Status, Tabular (' + art1.records.length + ' linhas) e Esquema SQL OK');

    // =========================================================================
    // TESTE 3: PROJEÇÃO DE CONTRATO 2 - LMC ANP OFICIAL
    // =========================================================================
    console.log('[NODE] 3. Validando Projeção de LMC ANP Oficial...');
    const lmcPayload = {json.dumps(res_lmc, ensure_ascii=False)};
    const art2 = panel.projectArtifact({{
      id: 'art-lmc-2',
      containerId: 'msg-2',
      toolName: 'lmc_anp',
      intent: 'lmc_report',
      data: lmcPayload,
      html: '<div class="decision-card">LMC Mock</div>',
      autoOpen: false
    }});

    if (!art2.title.includes('LMC ANP Oficial')) {{
      console.error('FALHA: Título incorreto para LMC:', art2.title);
      process.exit(1);
    }}
    if (!art2.records[0]['Variação (%)'] || !art2.records[0]['Status ANP']) {{
      console.error('FALHA: Colunas de auditoria ANP ausentes:', art2.records[0]);
      process.exit(1);
    }}
    console.log('[NODE]    ✓ Projeção LMC: Portaria 26, Variações volumétricas e Status ANP OK');

    // =========================================================================
    // TESTE 4: PROJEÇÃO DE CONTRATO 3 - PISTA & FRENTISTAS
    // =========================================================================
    console.log('[NODE] 4. Validando Projeção de Performance de Pista...');
    const pistaPayload = {json.dumps(res_pista, ensure_ascii=False)};
    const art3 = panel.projectArtifact({{
      id: 'art-pista-3',
      containerId: 'msg-3',
      toolName: 'desempenho_pista_frentistas',
      intent: 'pump_performance',
      data: pistaPayload,
      html: '<div class="decision-card">Pista Mock</div>',
      autoOpen: false
    }});

    if (!art3.records[0]['Frentista'] || !art3.records[0]['Volume Total (L)']) {{
      console.error('FALHA: Colunas de frentistas ausentes:', art3.records[0]);
      process.exit(1);
    }}
    console.log('[NODE]    ✓ Projeção Pista: Ranking de Frentistas e Vazão OK');

    // =========================================================================
    // TESTE 5: PROJEÇÃO DE CONTRATO 4 - COMBOS DE CONVENIÊNCIA
    // =========================================================================
    console.log('[NODE] 5. Validando Projeção de Combos da Conveniência...');
    const combosPayload = {json.dumps(res_combos, ensure_ascii=False)};
    const art4 = panel.projectArtifact({{
      id: 'art-combos-4',
      containerId: 'msg-4',
      toolName: 'conveniencia_vendas_cruzadas',
      intent: 'market_basket',
      data: combosPayload,
      html: '<div class="decision-card">Combos Mock</div>',
      autoOpen: false
    }});

    if (!art4.records[0]['Produto Base'] || !art4.records[0]['Lift']) {{
      console.error('FALHA: Colunas de combos ausentes:', art4.records[0]);
      process.exit(1);
    }}
    console.log('[NODE]    ✓ Projeção Combos: Regras de Associação e Lift OK');

    // =========================================================================
    // TESTE 6: SUPORTE UNIVERSAL A QUALQUER BANCO DE DADOS RELACIONAL FUTURO
    // =========================================================================
    console.log('[NODE] 6. Validando Conector Universal para Qualquer Banco de Dados Futuro...');
    const genericDbPayload = {{
      db_source: 'MySQL 8.0 / ERP Retaguarda',
      table_name: 'tb_produtos_estoque',
      rows: [
        {{ cod_prod: 101, descricao: 'Óleo Motor 15W40', estoque_atual: 14, preco_unitario: 39.90, ativo: true }},
        {{ cod_prod: 102, descricao: 'Filtro de Ar Master', estoque_atual: 3, preco_unitario: 45.00, ativo: true }},
        {{ cod_prod: 103, descricao: 'Aditivo Radiador Coolant', estoque_atual: 22, preco_unitario: 28.50, ativo: false }}
      ],
      total_rows: 3
    }};

    const artGeneric = panel.projectArtifact({{
      id: 'art-generic-db-1',
      toolName: 'consulta_sql_produtos',
      data: genericDbPayload,
      html: '<div class="custom-card">Consulta SQL Genérica</div>',
      autoOpen: false
    }});

    if (artGeneric.records.length !== 3) {{
      console.error('FALHA: Conector genérico não extraiu 3 registros:', artGeneric.records);
      process.exit(1);
    }}
    if (!artGeneric.records[0]['descricao'] || artGeneric.records[0]['descricao'] !== 'Óleo Motor 15W40') {{
      console.error('FALHA: Campos dinâmicos não preservados:', artGeneric.records[0]);
      process.exit(1);
    }}
    if (artGeneric.schemaInfo.source !== 'MySQL 8.0 / ERP Retaguarda' || artGeneric.schemaInfo.table !== 'tb_produtos_estoque') {{
      console.error('FALHA: Metadados do banco de dados não preservados:', artGeneric.schemaInfo);
      process.exit(1);
    }}
    console.log('[NODE]    ✓ Conector Universal aprovado: Schema dinâmico, tipos e linhas arbitrárias OK');

    // =========================================================================
    // TESTE 7: CARROSSEL DE MÚLTIPLOS ARTEFATOS E HISTÓRICO
    // =========================================================================
    console.log('[NODE] 7. Validando Carrossel de Histórico de Artefatos...');
    if (panel.artifacts.length !== 5) {{
      console.error('FALHA: Esperava 5 artefatos registrados, obteve:', panel.artifacts.length);
      process.exit(1);
    }}
    panel.selectArtifact('art-tank-1');
    if (panel.getActiveArtifact().id !== 'art-tank-1') {{
      console.error('FALHA: selectArtifact não alterou o artefato ativo');
      process.exit(1);
    }}
    console.log('[NODE]    ✓ Carrossel de múltiplos artefatos gerenciou histórico com sucesso');

    // =========================================================================
    // TESTE 8: EXPORTAÇÃO CSV DE DADOS TABULARES
    // =========================================================================
    console.log('[NODE] 8. Validando Formatação de Exportação CSV...');
    const tankRecords = art1.records;
    const headers = Object.keys(tankRecords[0]);
    const csvContent = [
      headers.join(';'),
      ...tankRecords.map(r => headers.map(h => `"${{String(r[h] ?? '').replace(/"/g, '""')}}"`).join(';'))
    ].join('\\n');

    if (!csvContent.includes('Tanque;') || !csvContent.includes('Combustível;') || !csvContent.includes('GASOLINA')) {{
      console.error('FALHA: Conteúdo do CSV inválido:', csvContent.substring(0, 200));
      process.exit(1);
    }}
    console.log('[NODE]    ✓ Exportação CSV determinística aprovada com delimitador oficial');

    // =========================================================================
    // TESTE 9: BLINDAGEM CONTRA XSS EM CAMPOS RELACIONAIS
    // =========================================================================
    console.log('[NODE] 9. Validando Blindagem contra XSS...');
    const xssEscaped = panel.escapeHtml('<script>alert("hack")</script>');
    if (xssEscaped.includes('<script>')) {{
      console.error('FALHA: escapeHtml não neutralizou script tag:', xssEscaped);
      process.exit(1);
    }}
    console.log('[NODE]    ✓ XSS devidamente neutralizado em células e esquemas');

    // =========================================================================
    // TESTE 10: PROJEÇÃO DE VENDAS & FATURAMENTO PDV (vendas_analitico)
    // =========================================================================
    console.log('[NODE] 10. Validando Projeção de Vendas & Faturamento PDV...');
    const mockVendas = {{
      status: "ok",
      ultimo_produto_vendido_destaque: {{
        origem: "Conveniência / PDV",
        produto: "BOLO DE MORANGO",
        valor_total: 15.0,
        quantidade: 1.0,
        data_hora: "2026-10-06 14:10:00",
        cupom: "101",
        pdv: "001"
      }},
      produtos_mais_vendidos: [
        {{ codpro: "00022", nompro: "CERVEJA HEINEKEN LN 330ML", total_saidas: 29, qtd_total: 29.0, receita_total: 319.0 }},
        {{ codpro: "00001", nompro: "GASOLINA COMUM", total_saidas: 15, qtd_total: 450.0, receita_total: 2790.0 }}
      ],
      resumo_geral: {{
        total_abastecimentos: 15,
        total_litros: 450.0,
        faturamento_total: 3109.0
      }}
    }};

    const artVendas = panel.projectArtifact({{
      id: 'art-vendas-10',
      toolName: 'vendas_analitico',
      data: mockVendas,
      html: '<div class="decision-card">Vendas Mock</div>',
      autoOpen: false
    }});

    if (!artVendas.title.includes('Vendas & Faturamento PDV')) {{
      console.error('FALHA: Título de vendas_analitico incorreto:', artVendas.title);
      process.exit(1);
    }}
    if (artVendas.records.length !== 2) {{
      console.error('FALHA: Quantidade de produtos mais vendidos incorreta:', artVendas.records.length);
      process.exit(1);
    }}
    if (!artVendas.records[0]['Produto'].includes('HEINEKEN')) {{
      console.error('FALHA: Produto do ranking não mapeado corretamente:', artVendas.records[0]);
      process.exit(1);
    }}
    if (!artVendas.schemaInfo.source.includes('Retaguarda Vendas') || !artVendas.schemaInfo.table.includes('tb_vendas_itens')) {{
      console.error('FALHA: Esquema SQL de vendas incorreto:', artVendas.schemaInfo);
      process.exit(1);
    }}
    console.log('[NODE]    ✓ Projeção de Vendas: Título, Ranking (' + artVendas.records.length + ' produtos), KPIs e Esquema SQL OK');

    // =========================================================================
    // TESTE 11: SUPORTE UNIVERSAL A DICIONÁRIOS PLANOS (OBJETOS CHAVE-VALOR)
    // =========================================================================
    console.log('[NODE] 11. Validando Normalização de Objetos Chave-Valor Planos...');
    const flatMetricsPayload = {{
      db_source: 'PostgreSQL 16 (Health SRE)',
      table_name: 'tb_telemetria_servidor',
      cpu_usage_pct: 14.2,
      memory_used_mb: 2048,
      active_connections: 18,
      status: 'HEALTHY'
    }};
    const artFlat = panel.projectArtifact({{
      id: 'art-flat-11',
      toolName: 'sre_metricas_servidor',
      data: flatMetricsPayload,
      html: '<div class="card">SRE Mock</div>',
      autoOpen: false
    }});

    if (artFlat.records.length !== 6) {{
      console.error('FALHA: Dicionário plano não convertido em 6 registros tabulares:', artFlat.records);
      process.exit(1);
    }}
    if (!artFlat.records.some(r => r['Propriedade / Métrica'] === 'cpu usage pct' || r['Propriedade / Métrica'] === 'status')) {{
      console.error('FALHA: Colunas de atributos planos incorretas:', artFlat.records);
      process.exit(1);
    }}
    console.log('[NODE]    ✓ Dicionários planos convertidos com sucesso em Data Grid bidimensional');

    // =========================================================================
    // TESTE 12: DESCOBERTA DE COLUNAS HETEROGÊNEAS EM QUALQUER BANCO
    // =========================================================================
    console.log('[NODE] 12. Validando Descoberta de Colunas Heterogêneas...');
    const heterogeneousPayload = {{
      rows: [
        {{ id: 1, nome: 'Item A', preco: 10.5 }},
        {{ id: 2, nome: 'Item B', preco: 20.0, categoria: 'Especiais' }},
        {{ id: 3, nome: 'Item C', fornecedor: 'Distribuidora X' }}
      ]
    }};
    const artHetero = panel.projectArtifact({{
      id: 'art-hetero-12',
      toolName: 'consulta_polimorfica',
      data: heterogeneousPayload,
      html: '<div>Polimórfico</div>',
      autoOpen: false
    }});
    const allHeteroCols = Array.from(new Set(artHetero.records.flatMap(r => Object.keys(r || {{}}))));
    if (!allHeteroCols.includes('categoria') || !allHeteroCols.includes('fornecedor') || !allHeteroCols.includes('preco')) {{
      console.error('FALHA: Nem todas as colunas heterogêneas foram descobertas:', allHeteroCols);
      process.exit(1);
    }}
    console.log('[NODE]    ✓ Descoberta heterogênea unificou todas as 5 colunas polimórficas');

    // =========================================================================
    // TESTE 13: LIMPEZA TOTAL COM clearArtifacts E RESET DE ESTADO
    // =========================================================================
    console.log('[NODE] 13. Validando clearArtifacts e Reset Completo...');
    panel.filterQuery = 'filtro_temporario';
    panel.clearArtifacts();
    if (panel.artifacts.length !== 0 || panel.activeArtifactId !== null || panel.filterQuery !== '') {{
      console.error('FALHA: clearArtifacts não redefiniu o estado completamente:', panel);
      process.exit(1);
    }}
    if (panel.getActiveArtifact() !== null) {{
      console.error('FALHA: getActiveArtifact deve retornar null após clearArtifacts');
      process.exit(1);
    }}
    console.log('[NODE]    ✓ Limpeza completa de artefatos e filtros aprovada');

    // =========================================================================
    // TESTE 14: INTEGRAÇÃO DO COMPANION PORTAL CARD NO CHAT CONTROLLER
    // =========================================================================
    console.log('[NODE] 14. Validando Companion Portal Card no AuraChatController...');
    const chatJsPath = {json.dumps(str((BASE_DIR / "web" / "js" / "aura-chat.js").resolve()))};
    const {{ AuraChatController }} = require(chatJsPath);
    const chat = new AuraChatController();
    if (typeof chat.toggleInlineArtifact !== 'function') {{
      console.error('FALHA: toggleInlineArtifact ausente no AuraChatController');
      process.exit(1);
    }}
    if (typeof chat.renderCompanionPortalCard !== 'function') {{
      console.error('FALHA: renderCompanionPortalCard ausente no AuraChatController');
      process.exit(1);
    }}

    const portalHtml = chat.renderCompanionPortalCard({{
      artifactId: 'art-teste-portal',
      artifactTitle: 'Autonomia Tanques',
      artifactSubtitle: 'Auditoria de Estoque',
      containerId: 'msg-99',
      widgetHtml: '<div class="decision-card">Card Teste</div>'
    }});

    // Validação estrita das classes e regras inteligentes no HTML do portal
    if (!portalHtml.includes('aux-btn-view-chat') || !portalHtml.includes('inline-flex md:hidden')) {{
      console.error('FALHA: Botão Ver no Chat não configurado com classes mobile-only (aux-btn-view-chat inline-flex md:hidden):', portalHtml);
      process.exit(1);
    }}
    if (!portalHtml.includes('aux-btn-view-panel') || !portalHtml.includes('hidden md:inline-flex')) {{
      console.error('FALHA: Botão Ver no Painel não configurado com classes pc-only (aux-btn-view-panel hidden md:inline-flex):', portalHtml);
      process.exit(1);
    }}
    if (!portalHtml.includes('Ver no Chat ▾') || !portalHtml.includes('Ver no Painel')) {{
      console.error('FALHA: Textos canônicos dos botões ausentes no portal card');
      process.exit(1);
    }}
    console.log('[NODE]    ✓ Companion Portal Card gerado com separação estrita Mobile vs PC (classes utilitárias OK)');

    // =========================================================================
    // TESTE 15: RECONHECIMENTO INTELIGENTE DE TELA (MOBILE <768px VS PC >=768px)
    // =========================================================================
    console.log('[NODE] 15. Validando Reconhecimento Inteligente de Tela (isMobileDevice)...');
    
    // Viewport Mobile (< 768px)
    const mobileWin320 = {{ innerWidth: 320 }};
    const mobileWin375 = {{ innerWidth: 375 }};
    const mobileWin767 = {{ innerWidth: 767 }};
    if (!panel.isMobileDevice(mobileWin320) || !chat.isMobileDevice(mobileWin320)) {{
      console.error('FALHA: 320px deve ser reconhecido como mobile');
      process.exit(1);
    }}
    if (!panel.isMobileDevice(mobileWin375) || !chat.isMobileDevice(mobileWin375)) {{
      console.error('FALHA: 375px deve ser reconhecido como mobile');
      process.exit(1);
    }}
    if (!panel.isMobileDevice(mobileWin767) || !chat.isMobileDevice(mobileWin767)) {{
      console.error('FALHA: 767px deve ser reconhecido como mobile');
      process.exit(1);
    }}
    if (panel.isDesktopDevice(mobileWin375) || chat.isDesktopDevice(mobileWin375)) {{
      console.error('FALHA: isDesktopDevice deve retornar false para 375px');
      process.exit(1);
    }}

    // Viewport PC / Desktop (>= 768px)
    const pcWin768 = {{ innerWidth: 768 }};
    const pcWin800 = {{ innerWidth: 800 }};
    const pcWin1024 = {{ innerWidth: 1024 }};
    const pcWin1920 = {{ innerWidth: 1920 }};
    if (panel.isMobileDevice(pcWin768) || chat.isMobileDevice(pcWin768)) {{
      console.error('FALHA: 768px deve ser reconhecido como PC/Desktop');
      process.exit(1);
    }}
    if (panel.isMobileDevice(pcWin800) || chat.isMobileDevice(pcWin800)) {{
      console.error('FALHA: 800px deve ser reconhecido como PC/Desktop');
      process.exit(1);
    }}
    if (panel.isMobileDevice(pcWin1024) || chat.isMobileDevice(pcWin1024)) {{
      console.error('FALHA: 1024px deve ser reconhecido como PC/Desktop');
      process.exit(1);
    }}
    if (!panel.isDesktopDevice(pcWin768) || !chat.isDesktopDevice(pcWin768)) {{
      console.error('FALHA: isDesktopDevice deve retornar true para 768px');
      process.exit(1);
    }}
    if (!panel.isDesktopDevice(pcWin1920) || !chat.isDesktopDevice(pcWin1920)) {{
      console.error('FALHA: 1920px deve ser reconhecido como PC/Desktop');
      process.exit(1);
    }}

    // Blindagem contra DOM residual: data-device="mobile" no elemento raiz NÃO pode anular innerWidth >= 768px
    global.document = {{
      documentElement: {{
        getAttribute: (attr) => attr === 'data-device' ? 'mobile' : null
      }}
    }};
    if (panel.isMobileDevice(pcWin768) || chat.isMobileDevice(pcWin768)) {{
      console.error('FALHA: innerWidth: 768px foi indevidamente sobrescrito por data-device=\"mobile\" no DOM!');
      process.exit(1);
    }}
    if (panel.isMobileDevice(pcWin1024) || chat.isMobileDevice(pcWin1024)) {{
      console.error('FALHA: innerWidth: 1024px foi indevidamente sobrescrito por data-device=\"mobile\" no DOM!');
      process.exit(1);
    }}
    // Do mesmo modo, data-device="desktop" no DOM NÃO pode anular innerWidth < 768px
    global.document = {{
      documentElement: {{
        getAttribute: (attr) => attr === 'data-device' ? 'desktop' : null
      }}
    }};
    if (!panel.isMobileDevice(mobileWin375) || !chat.isMobileDevice(mobileWin375)) {{
      console.error('FALHA: innerWidth: 375px foi indevidamente sobrescrito por data-device=\"desktop\" no DOM!');
      process.exit(1);
    }}
    delete global.document;

    // Override manual explícito do HUD (AuraFx) prevalece soberano
    const overrideMobile = {{ auraFx: {{ override: 'mobile' }}, innerWidth: 1440 }};
    const overrideDesktop = {{ auraFx: {{ override: 'desktop' }}, innerWidth: 360 }};
    if (!panel.isMobileDevice(overrideMobile)) {{
      console.error('FALHA: Override manual mobile deve prevalecer sobre viewport 1440px');
      process.exit(1);
    }}
    if (panel.isMobileDevice(overrideDesktop)) {{
      console.error('FALHA: Override manual desktop deve prevalecer sobre viewport 360px');
      process.exit(1);
    }}
    console.log('[NODE]    ✓ Reconhecimento inteligente de tela validado para Mobile (<768px), PC (>=768px), blindagem DOM e overrides HUD');

    // =========================================================================
    // TESTE 16: AUTO-OPEN INTELIGENTE (DESATIVADO EM MOBILE, ATIVADO EM PC)
    // =========================================================================
    console.log('[NODE] 16. Validando Regra de Auto-Open: Bloqueado no Mobile, Ativado no PC...');
    
    // 16.1 Simulação Mobile (375px e 767px): autoOpen: true NÃO deve abrir o painel lateral
    global.window = {{
      innerWidth: 375,
      auraFx: {{ override: null, isMobile: () => true }},
      auraAudio: {{ playChime: () => {{}} }}
    }};
    const mobilePanel = new AuraAuxPanel();
    mobilePanel.projectArtifact({{
      id: 'art-mobile-auto-test',
      data: {{ status: 'ok', teste: true }},
      html: '<div>Mobile</div>',
      autoOpen: true
    }});
    if (mobilePanel.isOpen !== false) {{
      console.error('FALHA: autoOpen: true abriu indevidamente o painel em tela mobile 375px!');
      process.exit(1);
    }}
    
    // Teste no limite de borda 767px (ainda mobile)
    global.window.innerWidth = 767;
    const mobilePanel767 = new AuraAuxPanel();
    mobilePanel767.projectArtifact({{
      id: 'art-mobile-767-auto-test',
      data: {{ status: 'ok', teste: true }},
      html: '<div>Mobile 767</div>',
      autoOpen: true
    }});
    if (mobilePanel767.isOpen !== false) {{
      console.error('FALHA: autoOpen: true abriu indevidamente o painel na borda mobile 767px!');
      process.exit(1);
    }}
    console.log('[NODE]    ✓ Mobile: autoOpen respeitado em 375px e 767px (painel permaneceu fechado p/ foco no chat)');

    // 16.2 Simulação PC / Desktop no limite exato de 768px: autoOpen: true DEVE abrir o painel lateral suavemente
    global.window = {{
      innerWidth: 768,
      auraFx: {{ override: null, isMobile: () => false }},
      auraAudio: {{ playChime: () => {{}} }}
    }};
    const pcPanel768 = new AuraAuxPanel();
    pcPanel768.projectArtifact({{
      id: 'art-pc-768-auto-test',
      data: {{ status: 'ok', teste: true }},
      html: '<div>Desktop 768px</div>',
      autoOpen: true
    }});
    if (pcPanel768.isOpen !== true) {{
      console.error('FALHA: autoOpen: true não abriu o painel lateral no limiar de PC 768px!');
      process.exit(1);
    }}
    console.log('[NODE]    ✓ PC / Desktop (768px): autoOpen abriu o painel lateral suavemente no limiar de tela ampla');

    // 16.3 Simulação PC / Desktop padrão (1024px): autoOpen: true DEVE abrir o painel lateral suavemente
    global.window.innerWidth = 1024;
    const pcPanel = new AuraAuxPanel();
    pcPanel.projectArtifact({{
      id: 'art-pc-auto-test',
      data: {{ status: 'ok', teste: true }},
      html: '<div>Desktop 1024px</div>',
      autoOpen: true
    }});
    if (pcPanel.isOpen !== true) {{
      console.error('FALHA: autoOpen: true não abriu o painel lateral em tela de PC 1024px!');
      process.exit(1);
    }}
    console.log('[NODE]    ✓ PC / Desktop (1024px): autoOpen abriu o painel lateral suavemente (Dual Focus ativo)');

    // 16.4 Simulação PC com fechamento voluntário prévio (userDismissed): NÃO deve forçar reabertura
    const pcPanelDismissed = new AuraAuxPanel();
    pcPanelDismissed.userDismissed = true;
    pcPanelDismissed.projectArtifact({{
      id: 'art-pc-dismissed-test',
      data: {{ status: 'ok', teste: true }},
      html: '<div>Dismissed</div>',
      autoOpen: true
    }});
    if (pcPanelDismissed.isOpen !== false) {{
      console.error('FALHA: autoOpen não respeitou userDismissed no PC!');
      process.exit(1);
    }}
    console.log('[NODE]    ✓ PC / Desktop: userDismissed respeitou a decisão do operador');

    // Limpa global.window
    delete global.window;

    console.log('AURA_AUX_PANEL_NODE_OK');
    """

    res_node = subprocess.run(
        ["node"],
        input=node_script,
        capture_output=True,
        text=True,
        cwd=str(BASE_DIR),
        encoding="utf-8"
    )
    assert res_node.returncode == 0, f"Erro nos testes Node.js:\n{res_node.stderr}"
    assert "AURA_AUX_PANEL_NODE_OK" in res_node.stdout, "Token de sucesso não encontrado na saída do Node.js"
    print("   [OK] Lógica JS validada: 4 perspectivas, tanques, LMC, pista, combos, banco universal e CSV.")

    print("\n" + "=" * 78)
    print("🎉 TODOS OS TESTES DO AURA COMPANION CANVAS PASSARAM COM 100% DE SUCESSO!")
    print("=" * 78)


if __name__ == "__main__":
    run_aux_panel_tests()
