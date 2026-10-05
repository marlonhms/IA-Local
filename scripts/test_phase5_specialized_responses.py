"""
Suíte de Testes Automatizada: Fase 5 — Respostas Especializadas (AURA Precision Glass)
Validação ponta-a-ponta dos 4 módulos canônicos:
1. Autonomia de Tanques (TankForecastContract / prever_esgotamento_tanques)
2. Vazão de Bicos & Frentistas (PumpPerformanceContract / auditar_desempenho_pista_frentistas)
3. Conciliação Físico-Contábil LMC ANP (LMCReportContract / gerar_relatorio_lmc_anp)
4. Combos & Associação da Conveniência (MarketBasketContract / auditar_cesta_conveniencia_vendas_cruzadas)

Abrange:
- Validação estrita de contratos Pydantic v1.0 e serialização/deserialização
- Preservação de compatibilidade regressiva de chaves de dicionário legadas
- Roteamento modular centralizado por intent (F5-01)
- Cards de decisão AURA Precision Glass (DecisionCard, Hero Metric, Limitation Callout, Ação em 1 Clique)
- Evidence Drawer modular dinâmico (Fórmulas matemáticas, Bicos, Caixas, Tanques, Resumo)
- Acessibilidade e Design System (pt-BR, tabular-nums, badges com ícone, alternativas textuais para gráficos)
- Robustez: Fallback de versão de schema desconhecida, payload vazio, XSS e estados operacionais
"""

import sys
import subprocess
import json
import os
from pathlib import Path
from datetime import datetime

# Protege stdout no terminal Windows contra problemas de codificação
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.schemas import (
    TankForecastContract,
    PumpPerformanceContract,
    LMCReportContract,
    MarketBasketContract,
    ShiftReconciliationContract,
)
from core.rag_engine import HybridRAGEngine
from core.tools import PostoTools


def run_tests():
    print("=" * 78)
    print("💎 SUÍTE DE TESTES: FASE 5 — RESPOSTAS ESPECIALIZADAS (AURA PRECISION GLASS)")
    print("=" * 78)

    rag = HybridRAGEngine()
    tools = PostoTools(rag)

    # ------------------------------------------------------------------
    # 1. MÓDULO 1: AUTONOMIA DE TANQUES & RUN-OUT (F5-03 & F5-04)
    # ------------------------------------------------------------------
    print("\n1. Testando Módulo 1: Autonomia de Tanques (TankForecastContract)...")
    res_tanques = tools.prever_esgotamento_tanques()
    assert res_tanques["status"] == "ok", f"Erro em prever_esgotamento_tanques: {res_tanques}"
    assert res_tanques["intent"] == "tank_forecast", f"Intent incorreta: {res_tanques.get('intent')}"
    assert "contrato" in res_tanques, "Chave 'contrato' ausente"

    # Validação Pydantic estrita
    contrato_tanques = TankForecastContract.model_validate(res_tanques["contrato"])
    assert contrato_tanques.schema_version == "1.0"
    assert contrato_tanques.intent == "tank_forecast"
    assert len(contrato_tanques.tanks) > 0, "Nenhum tanque retornado no contrato"
    assert contrato_tanques.assessment.title is not None
    assert contrato_tanques.assessment.badge_label is not None
    assert contrato_tanques.assessment.limitation is not None
    assert contrato_tanques.metrics.capacidade_total_litros > 0
    assert contrato_tanques.metrics.saldo_total_litros > 0
    assert contrato_tanques.metrics.espaco_livre_ullage_total_litros >= 0
    # Valida distinção de run-out 15% vs esgotamento 0% (F5-04)
    tq1 = contrato_tanques.tanks[0]
    assert tq1.autonomia_critica_horas is not None or tq1.autonomia_runout_horas is not None
    if tq1.autonomia_critica_horas is not None and tq1.autonomia_runout_horas is not None:
        assert tq1.autonomia_runout_horas >= tq1.autonomia_critica_horas, (
            "Autonomia até 0% deve ser >= autonomia até reserva técnica de 15%"
        )
    # Compatibilidade regressiva
    assert "resumo_executivo" in res_tanques and "detalhamento_tanques" in res_tanques
    print(f"   [OK] Contrato TankForecast validado: {len(contrato_tanques.tanks)} tanques auditados | "
          f"Menor autonomia 15%: {contrato_tanques.assessment.horizonte_critico_horas}h | "
          f"Ullage total: {contrato_tanques.metrics.espaco_livre_ullage_total_litros:,.0f} L")

    # ------------------------------------------------------------------
    # 2. MÓDULO 2: VAZÃO DE BICOS & FRENTISTAS (F5-05)
    # ------------------------------------------------------------------
    print("\n2. Testando Módulo 2: Vazão de Bicos & Frentistas (PumpPerformanceContract)...")
    res_pista = tools.auditar_desempenho_pista_frentistas()
    assert res_pista["status"] == "ok", f"Erro em auditar_desempenho_pista_frentistas: {res_pista}"
    assert res_pista["intent"] == "pump_performance", f"Intent incorreta: {res_pista.get('intent')}"
    assert "contrato" in res_pista, "Chave 'contrato' ausente"

    # Validação Pydantic estrita
    contrato_pista = PumpPerformanceContract.model_validate(res_pista["contrato"])
    assert contrato_pista.schema_version == "1.0"
    assert contrato_pista.intent == "pump_performance"
    assert len(contrato_pista.ranking) > 0, "Ranking de frentistas vazio"
    assert len(contrato_pista.nozzles) > 0, "Lista de bicos vazia"
    assert contrato_pista.assessment.limitation is not None
    assert contrato_pista.metrics.faturamento_total > 0
    assert contrato_pista.metrics.total_litros > 0
    assert contrato_pista.metrics.vazao_media_l_min > 0
    # Compatibilidade regressiva
    assert "ranking_frentistas" in res_pista and "auditoria_vazao_bicos" in res_pista
    print(f"   [OK] Contrato PumpPerformance validado: {len(contrato_pista.ranking)} frentistas | "
          f"{len(contrato_pista.nozzles)} bicos auditados | "
          f"Vazão média geral: {contrato_pista.metrics.vazao_media_l_min:.1f} L/min | "
          f"Bicos lentos (<30 L/min): {contrato_pista.assessment.total_bicos_lentos}")

    # ------------------------------------------------------------------
    # 3. MÓDULO 3: CONCILIAÇÃO FÍSICO-CONTÁBIL LMC ANP (F5-06 & F5-07)
    # ------------------------------------------------------------------
    print("\n3. Testando Módulo 3: LMC ANP Oficial (LMCReportContract)...")
    res_lmc = tools.gerar_relatorio_lmc_anp(data="2026-09-02")
    assert res_lmc["status"] == "ok", f"Erro em gerar_relatorio_lmc_anp: {res_lmc}"
    assert res_lmc["intent"] == "lmc_report", f"Intent incorreta: {res_lmc.get('intent')}"
    assert "contrato" in res_lmc, "Chave 'contrato' ausente"

    # Validação Pydantic estrita
    contrato_lmc = LMCReportContract.model_validate(res_lmc["contrato"])
    assert contrato_lmc.schema_version == "1.0"
    assert contrato_lmc.intent == "lmc_report"
    assert len(contrato_lmc.tanks) > 0, "Nenhum tanque retornado no LMC"
    assert contrato_lmc.assessment.limitation is not None
    assert contrato_lmc.metrics.tolerancia_oficial_pct == 0.60, "Tolerância ANP deve ser 0.60%"
    assert contrato_lmc.metrics.total_tanques_analisados == len(contrato_lmc.tanks)
    # Compatibilidade regressiva
    assert "resumo_executivo" in res_lmc and "tanques" in res_lmc
    print(f"   [OK] Contrato LMCReport validado: {len(contrato_lmc.tanks)} tanques | "
          f"Variação geral: {contrato_lmc.metrics.variacao_volumetrica_geral_pct:.2f}% | "
          f"Status Geral: {contrato_lmc.assessment.status_geral_anp}")

    # ------------------------------------------------------------------
    # 4. MÓDULO 4: COMBOS & CONVENIÊNCIA (F5-08)
    # ------------------------------------------------------------------
    print("\n4. Testando Módulo 4: Market Basket & Combos (MarketBasketContract)...")
    res_combos = tools.auditar_cesta_conveniencia_vendas_cruzadas(min_lift=1.2, limit=10)
    assert res_combos["status"] == "ok", f"Erro em auditar_cesta_conveniencia_vendas_cruzadas: {res_combos}"
    assert res_combos["intent"] == "market_basket", f"Intent incorreta: {res_combos.get('intent')}"
    assert "contrato" in res_combos, "Chave 'contrato' ausente"

    # Validação Pydantic estrita
    contrato_combos = MarketBasketContract.model_validate(res_combos["contrato"])
    assert contrato_combos.schema_version == "1.0"
    assert contrato_combos.intent == "market_basket"
    assert len(contrato_combos.top_combos) > 0, "Lista top_combos vazia"
    assert contrato_combos.assessment.limitation is not None
    assert contrato_combos.metrics.total_transacoes_analisadas > 0
    assert contrato_combos.metrics.maior_lift >= 1.2
    # Valida presença de script prático do caixa (F5-08)
    c1 = contrato_combos.top_combos[0]
    assert len(c1.script_sugerido_caixa) > 10, "Script do caixa ausente ou curto"
    # Compatibilidade regressiva
    assert "resumo_executivo" in res_combos and "top_combos_cross_selling" in res_combos
    print(f"   [OK] Contrato MarketBasket validado: {contrato_combos.metrics.total_transacoes_analisadas} cupons | "
          f"{len(contrato_combos.top_combos)} combos | Max Lift: {contrato_combos.metrics.maior_lift:.2f}x | "
          f"Combos fortes (>=2.0x): {contrato_combos.assessment.regras_com_forte_sinergia_lift_2}")

    # ------------------------------------------------------------------
    # 5. ROBUSTEZ: TRATAMENTO GRACIOSO DE DADOS AUSENTES OU PARCIAIS (F5-10)
    # ------------------------------------------------------------------
    print("\n5. Testando Tratamento Gracioso de Dados Ausentes ou Parciais...")

    # Tanques com filtro sem correspondência
    res_tanques_vazio = tools.prever_esgotamento_tanques(filtro_combustivel="COMBUSTIVEL_INEXISTENTE_XYZ")
    assert res_tanques_vazio["status"] == "ok"
    c_tk_vazio = TankForecastContract.model_validate(res_tanques_vazio["contrato"])
    assert len(c_tk_vazio.tanks) == 0
    assert c_tk_vazio.assessment.status_code == "SEM_REGISTROS"
    print("   [OK] Tanques: Filtro inexistente tratado graciosamente (status: SEM_REGISTROS)")

    # Pista em data sem movimento
    res_pista_vazia = tools.auditar_desempenho_pista_frentistas(data="1990-01-01")
    assert res_pista_vazia["status"] == "ok"
    c_pista_vazia = PumpPerformanceContract.model_validate(res_pista_vazia["contrato"])
    assert c_pista_vazia.assessment.status_code == "SEM_MOVIMENTACAO"
    print("   [OK] Pista: Data sem movimento tratada graciosamente (status: SEM_MOVIMENTACAO)")

    # LMC em data sem movimentação de vendas
    res_lmc_vazio = tools.gerar_relatorio_lmc_anp(data="1990-01-01")
    assert res_lmc_vazio["status"] == "ok"
    c_lmc_vazio = LMCReportContract.model_validate(res_lmc_vazio["contrato"])
    assert c_lmc_vazio.metrics.total_vendas_litros == 0.0
    print("   [OK] LMC ANP: Data sem movimento tratada graciosamente (vendas zeradas com integridade contábil)")

    # Market Basket com limiar alto de Lift
    res_mb_vazio = tools.auditar_cesta_conveniencia_vendas_cruzadas(min_lift=99.0)
    assert res_mb_vazio["status"] == "ok"
    c_mb_vazio = MarketBasketContract.model_validate(res_mb_vazio["contrato"])
    assert len(c_mb_vazio.top_combos) == 0
    print("   [OK] Market Basket: Filtro extremo tratado graciosamente (0 combos sem quebra de schema)")

    # ------------------------------------------------------------------
    # 6. TESTES FRONTEND HEADLESS (NODE.JS) - REGISTRY, DECISIONCARDS & DRAWER
    # ------------------------------------------------------------------
    print("\n6. Executando Validação de Renderização Frontend via Node.js...")
    aura_chat_path = BASE_DIR / "web" / "js" / "aura-chat.js"
    assert aura_chat_path.exists(), f"Arquivo aura-chat.js não encontrado em {aura_chat_path}"

    node_script = f"""
    const {{ AuraChatController }} = require({json.dumps(str(aura_chat_path.resolve()))});
    const chat = new AuraChatController();

    // =========================================================================
    // TESTE 1: REGISTRO CENTRALIZADO DE RENDERIZADORES MODULARES (F5-01)
    // =========================================================================
    console.log('[NODE] 1. Validando Registro Centralizado de Renderizadores...');
    const expectedIntents = [
      'shift_reconciliation',
      'tank_forecast',
      'pump_performance',
      'lmc_report',
      'market_basket',
      'ajuda_sistema'
    ];
    for (const key of expectedIntents) {{
      if (typeof chat.responseRenderers[key] !== 'function') {{
        console.error('FALHA: Renderizador não registrado para intent:', key);
        process.exit(1);
      }}
    }}
    console.log('[NODE]    ✓ Todos os renderizadores canônicos registrados no construtor');

    // =========================================================================
    // TESTE 2: DECISIONCARD MÓDULO 1 - AUTONOMIA DE TANQUES (F5-03 & F5-04)
    // =========================================================================
    console.log('[NODE] 2. Validando DecisionCard de Autonomia de Tanques...');
    const tankPayload = {json.dumps(res_tanques, ensure_ascii=False)};
    const tankCardHtml = chat.renderToolInlineWidget('previsao_tanques', tankPayload);

    if (!tankCardHtml.includes('class="decision-card"')) {{
      console.error('FALHA: Tanques não renderizou .decision-card');
      process.exit(1);
    }}
    if (!tankCardHtml.includes('Menor Autonomia de Pista')) {{
      console.error('FALHA: Hero metric de menor autonomia ausente');
      process.exit(1);
    }}
    if (!tankCardHtml.includes('Reserva técnica (15%)') || !tankCardHtml.includes('Esgotamento total (0%)')) {{
      console.error('FALHA: Distinção entre reserva 15% e esgotamento 0% ausente no hero do card');
      process.exit(1);
    }}
    if (!tankCardHtml.includes('decision-limitation-callout')) {{
      console.error('FALHA: Callout de limitação ausente no card de tanques');
      process.exit(1);
    }}
    if (!tankCardHtml.includes('Pedir Carreta')) {{
      console.error('FALHA: Botão de ação rápida Pedir Carreta ausente');
      process.exit(1);
    }}
    if (!tankCardHtml.includes('tabular-nums')) {{
      console.error('FALHA: Classe tabular-nums ausente nas métricas de tanques');
      process.exit(1);
    }}

    // Valida distinção de 15% vs 0% e Ullage nas linhas individuais dos tanques
    const pureTankContract = {{
      contrato: {{
        schema_version: '1.0',
        intent: 'tank_forecast',
        assessment: {{
          status_code: 'ALERTA_ESTOQUE_CRITICO',
          severity: 'attention',
          title: 'Atenção aos Tanques',
          badge_label: '⚠️ Nível de Reserva',
          horizonte_critico_horas: 14.5,
          horizonte_runout_horas: 48.0,
          tanque_mais_critico_cod: '02'
        }},
        metrics: {{
          saldo_total_litros: 8500,
          capacidade_total_litros: 30000,
          ocupacao_geral_pct: 28.3,
          autonomia_critica_horas: 14.5,
          autonomia_critica_dias: 0.6,
          autonomia_runout_horas: 48.0,
          autonomia_runout_dias: 2.0,
          espaco_livre_ullage_total_litros: 21500,
          compartimentos_5k_total: 4,
          volume_sugerido_total_litros: 20000
        }},
        tanks: [{{
          codtan: '02',
          combustivel: 'GASOLINA COMUM',
          categoria: 'GASOLINA COMUM',
          capacidade_litros: 15000,
          saldo_atual_litros: 4200,
          ocupacao_pct: 28.0,
          estoque_critico_15pct_litros: 2250,
          saldo_util_critico_litros: 1950,
          consumo_diario_litros: 2100,
          consumo_horario_litros: 87.5,
          autonomia_critica_horas: 14.5,
          autonomia_critica_dias: 0.6,
          autonomia_runout_horas: 48.0,
          autonomia_runout_dias: 2.0,
          espaco_livre_ullage_litros: 10800,
          compartimentos_5k: 2,
          volume_sugerido_litros: 10000,
          alerta_critico: false,
          status_operacional: 'ATENÇÃO',
          urgencia_pedido: 'MÉDIA',
          prazo_ideal_compra: 'Emitir pedido em até 48 horas',
          data_hora_critico: '2026-10-06 08:00',
          data_hora_runout: '2026-10-07 18:00'
        }}]
      }}
    }};
    const pureTankHtml = chat.renderTankAutonomyWidget(pureTankContract);
    if (!pureTankHtml.includes('14.5h até 15%') || !pureTankHtml.includes('48.0h até 0%')) {{
      console.error('FALHA: Distinção 14.5h até 15% e 48.0h até 0% falhou na linha do tanque:', pureTankHtml);
      process.exit(1);
    }}
    if (!pureTankHtml.includes('10.800 L (2x 5k)')) {{
      console.error('FALHA: Ullage 10.800 L (2x 5k) não formatado corretamente:', pureTankHtml);
      process.exit(1);
    }}
    console.log('[NODE]    ✓ DecisionCard Tanques: Hero, Barras volumétricas, 15% vs 0%, Ullage e Ação OK');

    // =========================================================================
    // TESTE 3: DECISIONCARD MÓDULO 2 - VAZÃO DE BICOS & FRENTISTAS (F5-05)
    // =========================================================================
    console.log('[NODE] 3. Validando DecisionCard de Performance da Pista & Frentistas...');
    const pumpPayload = {json.dumps(res_pista, ensure_ascii=False)};
    const pumpCardHtml = chat.renderToolInlineWidget('desempenho_pista_frentistas', pumpPayload);

    if (!pumpCardHtml.includes('class="decision-card"')) {{
      console.error('FALHA: Performance de pista não renderizou .decision-card');
      process.exit(1);
    }}
    if (!pumpCardHtml.includes('Faturamento Total da Pista')) {{
      console.error('FALHA: Hero metric de faturamento da pista ausente');
      process.exit(1);
    }}
    if (!pumpCardHtml.includes('Podium de Performance da Pista')) {{
      console.error('FALHA: Podium de frentistas ausente');
      process.exit(1);
    }}
    if (!pumpCardHtml.includes('decision-limitation-callout')) {{
      console.error('FALHA: Callout de limitação de telemetria ausente');
      process.exit(1);
    }}

    // Valida detecção de bico lento (< 30 L/min) e métricas a partir do contrato puro
    const purePumpContract = {{
      contrato: {{
        schema_version: '1.0',
        intent: 'pump_performance',
        assessment: {{
          status_code: 'ALERTA_PISTA',
          severity: 'attention',
          title: 'Auditoria de Pista: Alertas Preventivos',
          badge_label: '⚠️ 1 Bicos Lentos (<30 L/min)',
          total_bicos_lentos: 1,
          total_anomalias: 0,
          melhor_frentista_nome: 'Carlos Silva'
        }},
        metrics: {{
          total_abastecimentos: 150,
          total_litros: 4200.5,
          faturamento_total: 24500.80,
          faturamento_total_cents: 2450080,
          ticket_medio: 163.34,
          volume_medio: 28.0,
          taxa_conversao_aditivada_geral_pct: 29.5,
          classificacao_conversao_aditivada: 'BOM',
          vazao_media_l_min: 33.2,
          bicos_com_alerta_filtro: 1,
          total_anomalias_detectadas: 0
        }},
        ranking: [{{
          matricula: 'F01',
          nome: 'Carlos Silva',
          total_abastecimentos: 80,
          total_litros: 2300.0,
          faturamento_reais: 13500.0,
          ticket_medio_reais: 168.75,
          volume_medio_litros: 28.75,
          conversao_aditivada_pct: 32.0,
          classificacao_conversao: 'EXCELENTE',
          taxa_diesel_s10_pct: 0.0,
          identificado: true
        }}],
        nozzles: [{{
          bico: '03',
          bomba_fisica: 'B01',
          tanque: '01',
          combustivel: 'GASOLINA COMUM',
          categoria: 'GASOLINA COMUM',
          total_abastecimentos: 45,
          volume_total_litros: 1200.0,
          vazao_media_l_min: 24.5,
          status_vazao: 'ALERTA_FILTRO_LENTO',
          alerta_filtro_lento: true,
          recomendacao: 'Trocar filtro',
          origem_vazao: 'cbc04'
        }}]
      }}
    }};
    const purePumpHtml = chat.renderDesempenhoPistaWidget(purePumpContract);
    if (!purePumpHtml.includes('R$ 24.500,80')) {{
      console.error('FALHA: Faturamento da pista não formatado a partir de pure contract:', purePumpHtml);
      process.exit(1);
    }}
    if (!purePumpHtml.includes('24.5 L/min')) {{
      console.error('FALHA: Alerta de bico lento 24.5 L/min não renderizado no pure contract:', purePumpHtml);
      process.exit(1);
    }}
    if (!purePumpHtml.includes('⚠️ 1 Bicos Lentos (<30 L/min)') && !purePumpHtml.includes('⚠️ 1 Bicos Lentos (&lt;30 L/min)')) {{
      console.error('FALHA: Badge semântico de bico lento ausente:', purePumpHtml);
      process.exit(1);
    }}
    console.log('[NODE]    ✓ DecisionCard Pista: Hero, Frentistas, Vazão e Alerta < 30 L/min OK');

    // =========================================================================
    // TESTE 4: DECISIONCARD MÓDULO 3 - LMC ANP OFICIAL (F5-06 & F5-07)
    // =========================================================================
    console.log('[NODE] 4. Validando DecisionCard de LMC ANP Oficial...');
    const lmcPayload = {json.dumps(res_lmc, ensure_ascii=False)};
    const lmcCardHtml = chat.renderToolInlineWidget('lmc_anp', lmcPayload);

    if (!lmcCardHtml.includes('class="decision-card"')) {{
      console.error('FALHA: LMC ANP não renderizou .decision-card');
      process.exit(1);
    }}
    if (!lmcCardHtml.includes('Maior Desvio Volumétrico ANP')) {{
      console.error('FALHA: Hero metric de desvio ANP ausente');
      process.exit(1);
    }}
    if (!lmcCardHtml.includes('widget-anp-track') || !lmcCardHtml.includes('widget-anp-needle')) {{
      console.error('FALHA: Régua visual regulatória da ANP ausente');
      process.exit(1);
    }}
    if (!lmcCardHtml.includes('role="figure"') || !lmcCardHtml.includes('aria-label=')) {{
      console.error('FALHA: Alternativa textual acessível para a régua ANP ausente (F5-09)');
      process.exit(1);
    }}
    if (!lmcCardHtml.includes('Portaria ANP 26/1992')) {{
      console.error('FALHA: Citação regulatória Portaria 26 ausente');
      process.exit(1);
    }}

    // Valida exibição correta do estoque físico medido em régua (não pode virar 0 L)
    const pureLmcContract = {{
      contrato: {{
        schema_version: '1.0',
        intent: 'lmc_report',
        assessment: {{
          status_geral_anp: 'CONFORME_ANP',
          severity: 'normal',
          title: 'LMC Oficial ANP: Conformidade Regulamentar Aprovada',
          badge_label: '✓ Conforme ANP (±0,6%)',
          dentro_tolerancia_geral: true,
          variacao_geral_pct: -0.20,
          total_tanques_alerta: 0
        }},
        metrics: {{
          total_tanques_analisados: 1,
          total_tanques_conformes: 1,
          total_tanques_alerta: 0,
          total_vendas_litros: 5000.0,
          total_recebimentos_litros: 0.0,
          total_estoque_escriturado_litros: 5000.0,
          total_estoque_fisico_litros: 4990.0,
          variacao_volumetrica_total_litros: -10.0,
          variacao_volumetrica_geral_pct: -0.20,
          tolerancia_oficial_pct: 0.60
        }},
        tanks: [{{
          tanque: '01',
          combustivel: 'GASOLINA COMUM',
          categoria_combustivel: 'GASOLINA COMUM',
          codlmc_anp: '210101001',
          capacidade_litros: 15000.0,
          estoque_abertura_litros: 10000.0,
          recebimentos_descargas_litros: 0.0,
          vendas_bicos_litros: 5000.0,
          estoque_escriturado_litros: 5000.0,
          estoque_fisico_medido_litros: 4990.0,
          variacao_litros: -10.0,
          variacao_pct: -0.20,
          tolerancia_pct: 0.60,
          tolerancia_max_litros: 30.0,
          dentro_tolerancia: true,
          status_anp: 'CONFORME_ANP',
          tipo_variacao: 'PERDA',
          nome_variacao: 'Quebra Normal',
          descricao_status: 'Conforme',
          diagnostico: 'Operação dentro da margem legal'
        }}]
      }}
    }};
    const pureLmcHtml = chat.renderLmcAnpWidget(pureLmcContract);
    if (!pureLmcHtml.includes('Físico: 4.990 L') && !pureLmcHtml.includes('Físico: 4.990,0 L')) {{
      console.error('FALHA: Estoque físico medido 4.990 L ausente no pure contract (virou 0 L):', pureLmcHtml);
      process.exit(1);
    }}
    console.log('[NODE]    ✓ DecisionCard LMC: Hero, Régua visual [-0.6% a +0.6%], Acessibilidade e Portaria 26 OK');

    // =========================================================================
    // TESTE 5: DECISIONCARD MÓDULO 4 - COMBOS & MARKET BASKET (F5-08)
    // =========================================================================
    console.log('[NODE] 5. Validando DecisionCard de Combos & Conveniência...');
    const combosPayload = {json.dumps(res_combos, ensure_ascii=False)};
    const combosCardHtml = chat.renderToolInlineWidget('conveniencia_vendas_cruzadas', combosPayload);

    if (!combosCardHtml.includes('class="decision-card"')) {{
      console.error('FALHA: Combos não renderizou .decision-card');
      process.exit(1);
    }}
    if (!combosCardHtml.includes('Maior Multiplicador de Sinergia (Lift)')) {{
      console.error('FALHA: Hero metric de maior lift ausente');
      process.exit(1);
    }}
    if (!combosCardHtml.includes('Script no Balcão:')) {{
      console.error('FALHA: Script de abordagem para o operador de caixa ausente');
      process.exit(1);
    }}
    if (!combosCardHtml.includes('decision-limitation-callout')) {{
      console.error('FALHA: Callout de limitação estatística ausente');
      process.exit(1);
    }}
    if (!combosCardHtml.includes('Checar Estoque')) {{
      console.error('FALHA: Botão de checagem rápida de estoque ausente');
      process.exit(1);
    }}
    console.log('[NODE]    ✓ DecisionCard Combos: Hero, Lift >= 2.0x, Script de Balcão e Ações OK');

    // =========================================================================
    // TESTE 6: EVIDENCE DRAWER DINÂMICO PARA TODOS OS MÓDULOS
    // =========================================================================
    console.log('[NODE] 6. Validando Abas do Evidence Drawer Dinâmico...');

    // Aba formula para cada módulo com verificação de valores reais (sem 'N/A')
    const formulaTank = chat.renderEvidenceTabContent(pureTankContract, 'formula');
    if (!formulaTank.includes('14.5h') || !formulaTank.includes('48.0h')) {{
      console.error('FALHA: Drawer formula para tanques exibiu N/A em vez das horas reais:', formulaTank);
      process.exit(1);
    }}

    const formulaPista = chat.renderEvidenceTabContent(pumpPayload, 'formula');
    if (!formulaPista.includes('30.0 L/min') || !formulaPista.includes('25.0%')) {{
      console.error('FALHA: Drawer formula para pista não explicou limiar de 30 L/min ou meta 25%');
      process.exit(1);
    }}

    const formulaLmc = chat.renderEvidenceTabContent(lmcPayload, 'formula');
    if (!formulaLmc.includes('Portaria ANP nº 26/1992') || !formulaLmc.includes('0.6%')) {{
      console.error('FALHA: Drawer formula para LMC não explicou Portaria 26');
      process.exit(1);
    }}

    const formulaCombos = chat.renderEvidenceTabContent(combosPayload, 'formula');
    if (!formulaCombos.includes('Lift(A → B)') || !formulaCombos.includes('Suporte')) {{
      console.error('FALHA: Drawer formula para combos não explicou Lift');
      process.exit(1);
    }}

    // Abas de dados específicas com contratos estritos
    const bicosPistaTab = chat.renderEvidenceTabContent(purePumpContract, 'bicos');
    if (!bicosPistaTab.includes('24.5 L/min') || !bicosPistaTab.includes('Filtro Lento')) {{
      console.error('FALHA: Aba bicos exibiu N/A ou não identificou Filtro Lento no bico 03:', bicosPistaTab);
      process.exit(1);
    }}

    const pureRulesMbContract = {{
      contrato: {{
        schema_version: '1.0',
        intent: 'market_basket',
        detailed_rules: [{{
          regra: 'CERVEJA HEINEKEN ➔ BATATA PRINGLES',
          suporte: 0.052,
          confianca: 0.625,
          lift: 3.45,
          frequencia_conjunta: 12,
          forte_sinergia: true
        }}]
      }}
    }};
    const caixasCombosTab = chat.renderEvidenceTabContent(pureRulesMbContract, 'caixas');
    if (!caixasCombosTab.includes('5.2%') || !caixasCombosTab.includes('62.5%')) {{
      console.error('FALHA: Aba caixas para market basket não escalonou suporte e confiança para percentuais reais:', caixasCombosTab);
      process.exit(1);
    }}

    const tanquesTab = chat.renderEvidenceTabContent(pureTankContract, 'tanques');
    if (!tanquesTab.includes('14.5h') || !tanquesTab.includes('48.0h')) {{
      console.error('FALHA: Aba tanques exibiu N/A para autonomia 15% ou esgotamento:', tanquesTab);
      process.exit(1);
    }}

    const tanquesLmcTab = chat.renderEvidenceTabContent(pureLmcContract, 'tanques');
    if (!tanquesLmcTab.includes('4.990,0 L')) {{
      console.error('FALHA: Aba tanques do LMC exibiu estoque físico zerado:', tanquesLmcTab);
      process.exit(1);
    }}

    console.log('[NODE]    ✓ Todas as abas do Evidence Drawer dinâmico renderizadas com precisão e valores oficiais');

    // =========================================================================
    // TESTE 7: FALLBACK SEGURO PARA VERSÃO DE SCHEMA DESCONHECIDA (F1-08 / F5-01)
    // =========================================================================
    console.log('[NODE] 7. Validando Fallback Seguro para Schema Desconhecido...');
    const fakeSchemaTank = JSON.parse(JSON.stringify(tankPayload));
    fakeSchemaTank.contrato.schema_version = '2.0';
    const fakeCardHtml = chat.renderTankAutonomyWidget(fakeSchemaTank);
    if (!fakeCardHtml.includes('Versão de Contrato Não Suportada (v2.0)') || !fakeCardHtml.includes('Schema Desconhecido')) {{
      console.error('FALHA: Schema versão 2.0 não ativou fallback seguro:', fakeCardHtml);
      process.exit(1);
    }}
    if (fakeCardHtml.includes('Menor Autonomia de Pista')) {{
      console.error('FALHA: Fallback seguro permitiu exibição de métricas hero falsamente');
      process.exit(1);
    }}
    console.log('[NODE]    ✓ Fallback de governança bloqueou interpretação indevida para v2.0');

    // =========================================================================
    // TESTE 8: PROTEÇÃO CONTRA INJEÇÃO XSS EM LABELS E SCRIPTS
    // =========================================================================
    console.log('[NODE] 8. Validando Blindagem contra XSS...');
    const xssPayload = JSON.parse(JSON.stringify(combosPayload));
    xssPayload.contrato.top_combos[0].produto_origem = '<script>alert("xss")</script>';
    xssPayload.contrato.top_combos[0].script_sugerido_caixa = '<img src=x onerror=alert(1)>';
    const xssCardHtml = chat.renderCombosWidget(xssPayload);
    if (xssCardHtml.includes('<script>') || xssCardHtml.includes('<img src=x')) {{
      console.error('FALHA: Injeção XSS detectada no DecisionCard:', xssCardHtml);
      process.exit(1);
    }}
    console.log('[NODE]    ✓ XSS neutralizado com sucesso via escapeHtml');

    console.log('NODE_PHASE5_TESTS_OK');
    """

    res_node = subprocess.run(
        ["node"],
        input=node_script,
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8"
    )

    if res_node.returncode != 0:
        print("\n❌ ERRO NA EXECUÇÃO DOS TESTES NODE.JS:")
        print(res_node.stderr)
        print(res_node.stdout)
        raise AssertionError("Falha nos testes de renderização frontend (Node.js)")

    print(res_node.stdout)
    print("\n" + "=" * 78)
    print("🎉 TODOS OS TESTES DA FASE 5 (RESPOSTAS ESPECIALIZADAS) PASSARAM COM SUCESSO!")
    print("=" * 78)


if __name__ == "__main__":
    run_tests()
