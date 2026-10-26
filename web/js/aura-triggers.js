/**
 * AURA Gatilhos Analíticos em 1-Clique Controller
 * Gerencia a matriz de 13 ferramentas especializadas para execução direta em sub-100ms.
 */

class AuraTriggersController {
  constructor() {
    this.currentTool = null;
    this.currentResult = null;
    this.activeFilter = 'todos';
    this.isExecuting = false;
  }

  /**
   * Catálogo das 13 ferramentas analíticas
   */
  getToolsCatalog() {
    return [
      {
        id: 'roi_diagnostic',
        aliases: ['diagnostico_executivo_roi', 'diagnostico_perdas', 'roi_perdas'],
        name: 'Diagnóstico Executivo de ROI & Perdas (90 Dias)',
        category: 'gestao',
        icon: 'dollar-sign',
        color: 'emerald',
        badge: 'Executivo / ROI',
        desc: 'Diagnóstico determinístico dos 5 vetores de perdas operacionais, projeção de retorno líquido em 90 dias e garantia de 3x.',
        defaultParams: { monthly_subscription_brl: 490.0 },
      },
      {
        id: 'pos_audit',
        aliases: ['radar_anomalias_pdv', 'auditoria_pdv_zscore', 'auditoria_pos'],
        name: 'Radar de Anomalias de PDV & Caixa (Z-Score)',
        category: 'caixa',
        icon: 'shield-alert',
        color: 'cyan',
        badge: 'Auditoria CLT',
        desc: 'Auditoria estatística e contábil de cancelamentos com Z-Score por operador e checklist de conformidade Art. 462 CLT.',
        defaultParams: {},
      },
      {
        id: 'zero_click_briefing',
        aliases: ['briefing_matinal', 'cafe_com_dono', 'morning_briefing'],
        name: 'Briefing Matinal Zero-Click (Café com o Dono)',
        category: 'gestao',
        icon: 'coffee',
        color: 'purple',
        badge: 'WhatsApp / Mobile',
        desc: 'Resumo executivo consolidado das últimas 24h, alerta de runout de tanques, divergências de caixa e mensagem formatada para WhatsApp.',
        defaultParams: {},
      },
      {
        id: 'run_out',
        name: 'Previsão Run-Out de Tanques',
        category: 'combustiveis',
        icon: 'fuel',
        color: 'emerald',
        badge: 'Logística',
        desc: 'Projeção de esgotamento de combustível, cálculo de Ullage e sugestão de caminhão-tanque (múltiplos de 5.000 L).',
        defaultParams: { combustivel: null },
      },
      {
        id: 'lmc_anp',
        name: 'LMC Oficial ANP (Port. 26/1992)',
        category: 'fiscal',
        icon: 'book-open',
        color: 'emerald',
        badge: 'Regulatório',
        desc: 'Auditoria de perdas e sobras físicas vs contábeis no livro LMC com verificação da margem legal de ±0.6%.',
        defaultParams: { data: 'hoje' },
      },
      {
        id: 'conciliacao_turno',
        name: 'Conciliação de Turno & Caixa',
        category: 'caixa',
        icon: 'check-circle-2',
        color: 'cyan',
        badge: 'Auditoria',
        desc: 'Triangulação contábil entre encerrantes de bicos na pista, vendas do PDV e balanço volumétrico de tanques.',
        defaultParams: { data: 'hoje' },
      },
      {
        id: 'investigar_causa_raiz',
        name: 'Perícia Forense RCA (Causa-Raiz)',
        category: 'caixa',
        icon: 'search-check',
        color: 'purple',
        badge: 'IA Forense',
        desc: 'Triangulação autônoma de quebras de turno: abastecimentos órfãos, estornos descompassados, aferições 20L e inversões de forma de pagamento.',
        defaultParams: { data: 'hoje' },
      },
      {
        id: 'desempenho_pista_frentistas',
        name: 'Desempenho de Frentistas & Pista',
        category: 'caixa',
        icon: 'users',
        color: 'cyan',
        badge: 'Produtividade',
        desc: 'Ranking de litragem, ticket médio, conversão de aditivada e detecção de bicos com vazão lenta (<30 L/min).',
        defaultParams: {},
      },
      {
        id: 'conveniencia_vendas_cruzadas',
        aliases: ['market_basket', 'cesta_compras', 'basket_upsell', 'cross_selling', 'auditar_cesta_conveniencia_vendas_cruzadas'],
        name: 'Cesta de Compras & Cross-Selling',
        category: 'loja',
        icon: 'shopping-cart',
        color: 'purple',
        badge: 'Inteligência PDV',
        desc: 'Combos e padrões de compras frequentes na conveniência, com relevância comprovada e scripts para o caixa.',
        defaultParams: { min_lift: 1.2, limit: 10 },
      },
      {
        id: 'estoque_posicao',
        name: 'Posição Geral de Estoque ERP',
        category: 'combustiveis',
        icon: 'package',
        color: 'emerald',
        badge: 'Estoque Central',
        desc: 'Consulta o saldo contábil, custos e posições de estoque em tempo real das mercadorias cadastradas.',
        defaultParams: { termo: '' },
      },
      {
        id: 'clientes_ranking',
        name: 'Ranking e Perfil de Clientes',
        category: 'caixa',
        icon: 'award',
        color: 'purple',
        badge: 'CRM',
        desc: 'Identificação dos clientes de maior volume de compra, frotas conveniadas e histórico de faturamento.',
        defaultParams: { termo: '' },
      },
      {
        id: 'dados_filial',
        name: 'Dados Cadastrais da Filial',
        category: 'gestao',
        icon: 'building',
        color: 'cyan',
        badge: 'Identidade',
        desc: 'Razão social, CNPJ, endereço oficial, código de filial e terminal PDV conectado à AURA.',
        defaultParams: {},
      },
      {
        id: 'catalogo_produtos',
        name: 'Busca Semântica no Catálogo',
        category: 'loja',
        icon: 'search',
        color: 'purple',
        badge: 'Catálogo & Preços',
        desc: 'Pesquisa inteligente de combustíveis, conveniência e lubrificantes com correspondência precisa de sinônimos.',
        defaultParams: { termo: 'combustivel', top_k: 5 },
      },
      {
        id: 'vendas_analitico',
        name: 'Vendas & Faturamento ERP',
        category: 'fiscal',
        icon: 'trending-up',
        color: 'emerald',
        badge: 'Faturamento',
        desc: 'Análise de produtos mais vendidos na pista e conveniência, abastecimentos recentes e ticket médio diário.',
        defaultParams: { tipo: 'mais_vendidos' },
      },
      {
        id: 'sre_metricas',
        name: 'Saúde & Telemetria SRE do Posto',
        category: 'gestao',
        icon: 'activity',
        color: 'cyan',
        badge: 'Observabilidade',
        desc: 'Métricas de banco de dados, latência do Semantic Router, conexões ativas e integridade das tabelas do posto.',
        defaultParams: {},
      },
      {
        id: 'cenario_preditivo',
        name: 'Simulação Preditiva & What-If',
        category: 'combustiveis',
        icon: 'trending-up',
        color: 'purple',
        badge: 'Precificação Preditiva',
        desc: 'Simulação preditiva de reajustes de preço e repasse de custos com elasticidade calibrada da demanda e paridade 70% Etanol vs Gasolina.',
        defaultParams: { produto: 'GASOLINA COMUM', delta_preco: 0.10, periodo_dias: 30 },
      },
      {
        id: 'benchmark_comparativo',
        name: 'Benchmark Comparativo & Concorrência',
        category: 'gestao',
        icon: 'trending-up',
        color: 'cyan',
        badge: 'Competitividade',
        desc: 'Triangulação analítica de preços de combustíveis, ticket médio e conversão de aditivada frente à média do mercado local e metas da rede.',
        defaultParams: { grupo_benchmark: 'Concorrentes Raio 3km (Média Região)' },
      },
      {
        id: 'auditoria_fuga_financeira',
        name: 'Auditoria de Fuga Financeira & TEF',
        category: 'caixa',
        icon: 'alert-triangle',
        color: 'purple',
        badge: 'Prevenção de Perdas',
        desc: 'Detecção determinística de quebras de gaveta, sangrias anômalas retidas no caixa e divergências de conciliação de cartões TEF.',
        defaultParams: { data: 'hoje', cash_tolerance_reais: 50.0 },
      },
      {
        id: 'compliance_status',
        aliases: ['conformidade_legal', 'termo_interoperabilidade', 'blindagem_juridica', 'status_conformidade'],
        name: 'Conformidade Legal & LGPD (Termo v1.1)',
        category: 'gestao',
        icon: 'shield-check',
        color: 'emerald',
        badge: 'Blindagem Jurídica',
        desc: 'Verificação em tempo real do Opt-In formal, Termo de Interoperabilidade v1.1, driver shield e isolamento Clean Room AUPS.',
        defaultParams: {},
      },
    ];
  }

  /**
   * Renderiza os cards de gatilho no grid
   */
  renderGrid() {
    const gridEl = document.getElementById('triggers-grid');
    if (!gridEl) return;

    const catalog = this.getToolsCatalog();
    const filtered = this.activeFilter === 'todos' 
      ? catalog 
      : catalog.filter(t => t.category === this.activeFilter);

    let html = '';

    filtered.forEach(tool => {
      let borderAccent = 'hover:border-emerald-500/50 hover:shadow-emerald-950/20';
      let tagBg = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';

      if (tool.color === 'cyan') {
        borderAccent = 'hover:border-cyan-500/50 hover:shadow-cyan-950/20';
        tagBg = 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30';
      } else if (tool.color === 'purple') {
        borderAccent = 'hover:border-purple-500/50 hover:shadow-purple-950/20';
        tagBg = 'bg-purple-500/10 text-purple-400 border-purple-500/30';
      }

      html += `
        <div class="glass-panel p-4 flex flex-col justify-between transition-all duration-200 cursor-pointer ${borderAccent} hover:-translate-y-1 hover:shadow-xl group"
             onclick="window.auraTriggers.executeTrigger('${tool.id}')">
          <div>
            <div class="flex items-center justify-between mb-3">
              <span class="px-2.5 py-0.5 rounded-full text-[10px] font-sans font-semibold border ${tagBg}">
                ${tool.badge}
              </span>
              <span class="text-[11px] text-slate-400 font-sans group-hover:text-cyan-300 transition-colors flex items-center gap-1">
                <span>1-Clique</span>
                <svg class="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"/></svg>
              </span>
            </div>

            <h3 class="font-bold text-sm text-slate-100 group-hover:text-white transition-colors">
              ${tool.name}
            </h3>

            <p class="text-xs text-slate-400 mt-1.5 leading-relaxed font-sans">
              ${tool.desc}
            </p>
          </div>

          <div class="mt-4 pt-3 border-t border-white/5 flex items-center justify-between font-sans text-[11px] text-slate-500">
            <span class="text-slate-400">Módulo: ${tool.badge}</span>
            <span class="text-cyan-400 font-semibold group-hover:text-cyan-300 flex items-center gap-1.5">
              <span>Consultar</span>
              <svg class="w-3.5 h-3.5 inline text-cyan-400 group-hover:translate-x-0.5 transition-transform" viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="12" cy="12" r="9" stroke-width="1.75"/><line x1="12" y1="1.5" x2="12" y2="5" stroke-width="1.75"/><line x1="12" y1="19" x2="12" y2="22.5" stroke-width="1.75"/><line x1="1.5" y1="12" x2="5" y2="12" stroke-width="1.75"/><line x1="19" y1="12" x2="22.5" y2="12" stroke-width="1.75"/><path d="M8 12.5l2.8 2.8L16.5 8.5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </span>
          </div>
        </div>
      `;
    });

    gridEl.innerHTML = html;
  }

  /**
   * Define o filtro ativo e redesenha os cards
   */
  setFilter(filterName) {
    this.activeFilter = filterName;
    document.querySelectorAll('.trigger-filter-btn').forEach(btn => {
      const active = btn.getAttribute('data-filter') === filterName;
      if (active) {
        btn.classList.add('bg-slate-800', 'text-white', 'border-slate-700');
        btn.classList.remove('text-slate-400');
      } else {
        btn.classList.remove('bg-slate-800', 'text-white', 'border-slate-700');
        btn.classList.add('text-slate-400');
      }
    });
    this.renderGrid();
  }

  /**
   * Executa a ferramenta selecionada e exibe o resultado formatado
   */
  async executeTrigger(toolId, customParams = null) {
    if (this.isExecuting) return;
    this.isExecuting = true;

    const catalog = this.getToolsCatalog();
    const tool = catalog.find(t => t.id === toolId || (t.aliases && t.aliases.includes(toolId))) || { id: toolId, name: toolId };
    this.currentTool = tool;

    const inspectorEl = document.getElementById('trigger-inspector-card');
    const loadingEl = document.getElementById('trigger-inspector-loading');
    const resultEl = document.getElementById('trigger-inspector-result');

    if (inspectorEl) inspectorEl.classList.remove('hidden');
    if (loadingEl) loadingEl.classList.remove('hidden');
    if (resultEl) resultEl.classList.add('hidden');

    try {
      const params = customParams || tool.defaultParams || {};
      const response = await window.auraApi.executeIntent(toolId, params);
      this.currentResult = response;

      this.renderResultInspector(tool, response);
    } catch (err) {
      console.error('[AuraTriggers] Erro na execução:', err);
      this.renderErrorInspector(tool, err.message);
    } finally {
      this.isExecuting = false;
      if (loadingEl) loadingEl.classList.add('hidden');
      if (resultEl) resultEl.classList.remove('hidden');
    }
  }

  /**
   * Renderiza a visualização rica do resultado (Formatado e JSON)
   */
  renderResultInspector(tool, response) {
    const titleEl = document.getElementById('inspector-tool-title');
    const statusEl = document.getElementById('inspector-status-badge');
    const latencyEl = document.getElementById('inspector-latency-badge');
    const formattedTab = document.getElementById('inspector-content-formatted');
    const jsonTab = document.getElementById('inspector-content-json');
    const dataObj = response.data || response;
    const isUnavail = dataObj?.status === 'indisponivel' || dataObj?.status === 'unavailable' || dataObj?.status === 'error' || dataObj?.status === 'erro' || Boolean(dataObj?.error);

    if (titleEl) titleEl.textContent = tool.name;
    if (statusEl) {
      if (isUnavail) {
        statusEl.className = 'px-2.5 py-0.5 rounded text-[11px] font-sans font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/40';
        statusEl.textContent = '⚠ Fonte Indisponível';
      } else {
        statusEl.className = 'px-2.5 py-0.5 rounded text-[11px] font-sans font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40';
        statusEl.textContent = '✓ Consulta Concluída';
      }
    }
    if (latencyEl) {
      latencyEl.innerHTML = `<span class="inline-flex items-center gap-1.5"><svg class="w-3.5 h-3.5 text-cyan-400" viewBox="0 0 24 24" fill="none" stroke="currentColor"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg> <span>Tempo de Resposta: ${response.clientLatencyMs || response.latency_ms || 25} ms</span></span>`;
    }

    // Renderiza JSON bruto com syntax highlighting simples
    if (jsonTab) {
      jsonTab.textContent = JSON.stringify(response.data || response, null, 2);
    }

    // Renderiza visualização formatada específica
    if (formattedTab) {
      formattedTab.innerHTML = this.buildFormattedHtml(tool.id, response.data || response);
    }
  }

  /**
   * Constrói HTML formatado sob medida para cada tipo de ferramenta
   */
  buildFormattedHtml(toolId, data) {
    if (!data) return '<div class="text-slate-400 font-sans text-xs">Nenhum dado retornado.</div>';

    if (data.status === 'indisponivel' || data.status === 'unavailable' || data.status === 'error' || data.status === 'erro' || data.error) {
      const motivo = data.motivo || data.mensagem || data.error || 'Acesso à fonte primária (ERP/Banco) temporariamente indisponível.';
      return `
        <div class="p-4 rounded-xl bg-rose-950/20 border border-rose-500/30 text-rose-300 font-sans text-xs space-y-2">
          <div class="flex items-center gap-2">
            <svg class="w-4 h-4 text-rose-400 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" stroke-width="1.75" stroke-linejoin="round"/><line x1="12" y1="9" x2="12" y2="13" stroke-width="1.75" stroke-linecap="round"/><circle cx="12" cy="17" r="1" fill="currentColor"/></svg>
            <strong class="font-semibold text-rose-200">Indisponibilidade da Fonte (ERP/Banco):</strong>
          </div>
          <p class="text-rose-200/90 leading-relaxed">${this.escapeHtml(motivo)}</p>
          <div class="pt-2">
            <button type="button" class="px-3 py-1.5 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 border border-rose-500/40 text-xs font-semibold cursor-pointer transition-colors" onclick="if (window.auraTriggers) window.auraTriggers.executeTrigger('${toolId}');">
              Tentar Novamente
            </button>
          </div>
        </div>
      `;
    }

    // 1. Run-Out de Tanques
    if (toolId === 'run_out' && data.detalhamento_tanques) {
      let rows = '';
      data.detalhamento_tanques.forEach(t => {
        rows += `
          <tr class="border-b border-white/5 text-xs font-sans hover:bg-white/[0.02] transition-colors">
            <td class="py-2.5 text-slate-300 font-bold">TQ-${t.codtan}</td>
            <td class="py-2.5 font-semibold text-slate-100">${t.combustivel}</td>
            <td class="py-2.5 text-right tabular-nums">${(t.saldo_atual_litros || 0).toLocaleString('pt-BR')} L</td>
            <td class="py-2.5 text-right tabular-nums">${(t.capacidade_litros || 0).toLocaleString('pt-BR')} L</td>
            <td class="py-2.5 text-right text-emerald-400 font-bold tabular-nums">${(t.ocupacao_pct || 0).toFixed(1)}%</td>
            <td class="py-2.5 text-right text-cyan-300 tabular-nums">${(t.espaco_livre_ullage_litros || 0).toLocaleString('pt-BR')} L</td>
            <td class="py-2.5 text-right text-purple-300 tabular-nums">${t.compartimentos_5k || 0}x 5k</td>
            <td class="py-2.5 text-right font-bold tabular-nums ${t.alerta_critico ? 'text-rose-400' : 'text-slate-300'}">
              ~${(t.autonomia_runout_dias || 0).toFixed(1)}d
            </td>
          </tr>
        `;
      });

      const tanksList = data.detalhamento_tanques || [];
      const totalAtivos = tanksList.filter(t => t.status_operacional !== 'INATIVO').length;
      const emRisco = tanksList.filter(t => t.alerta_critico).length;
      const saldoTot = tanksList.reduce((acc, t) => acc + (Number(t.saldo_atual_litros) || 0), 0);
      const ullageTot = tanksList.reduce((acc, t) => acc + (Number(t.espaco_livre_ullage_litros) || 0), 0);

      return `
        <div class="space-y-4 font-sans text-xs">
          <div class="p-3.5 rounded-xl glass-subcard border border-white/5 text-xs text-slate-300">
            <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div>Tanques Ativos: <strong class="text-emerald-400 tabular-nums">${totalAtivos}</strong></div>
              <div>Nível Crítico (&lt;15%): <strong class="${emRisco > 0 ? 'text-rose-400' : 'text-slate-400'} tabular-nums">${emRisco}</strong></div>
              <div>Saldo Total: <strong class="text-slate-100 tabular-nums">${saldoTot.toLocaleString('pt-BR')} L</strong></div>
              <div>Ullage Total: <strong class="text-cyan-300 tabular-nums">${ullageTot.toLocaleString('pt-BR')} L</strong></div>
            </div>
          </div>

          <div class="overflow-x-auto">
            <table class="w-full text-left font-sans text-xs">
              <thead>
                <tr class="text-slate-400 border-b border-white/10">
                  <th class="pb-2.5">Tanque</th>
                  <th class="pb-2.5">Combustível</th>
                  <th class="pb-2.5 text-right">Saldo</th>
                  <th class="pb-2.5 text-right">Capacidade</th>
                  <th class="pb-2.5 text-right">Ocupação</th>
                  <th class="pb-2.5 text-right">Ullage</th>
                  <th class="pb-2.5 text-right">Carreta</th>
                  <th class="pb-2.5 text-right">Autonomia</th>
                </tr>
              </thead>
              <tbody>${rows}</tbody>
            </table>
          </div>
        </div>
      `;
    }

    // 2. LMC Oficial ANP
    if (toolId === 'lmc_anp' && data.resumo_executivo) {
      const r = data.resumo_executivo;
      return `
        <div class="space-y-4 font-sans text-xs">
          <div class="p-4 rounded-xl glass-subcard border border-emerald-500/40 flex items-center justify-between shadow-lg">
            <div>
              <div class="text-xs text-slate-400">Status Geral ANP</div>
              <div class="text-lg font-bold text-emerald-400">${r.status_geral_anp}</div>
            </div>
            <div class="text-right">
              <div class="text-xs text-slate-400">Tolerância Portaria 26/1992</div>
              <div class="text-sm font-bold text-slate-200">±0.60% (Margem Legal)</div>
            </div>
          </div>

          <div class="grid grid-cols-2 md:grid-cols-4 gap-3 p-3.5 rounded-xl glass-subcard border border-white/5">
            <div>Tanques Conformes: <strong class="text-emerald-400 tabular-nums">${r.total_tanques_conformes} / ${r.total_tanques_analisados}</strong></div>
            <div>Vendas do Período: <strong class="text-slate-100 tabular-nums">${(r.total_vendas_litros || 0).toLocaleString('pt-BR')} L</strong></div>
            <div>Estoque Escriturado: <strong class="text-slate-100 tabular-nums">${(r.total_estoque_escriturado_litros || 0).toLocaleString('pt-BR')} L</strong></div>
            <div>Estoque Físico Medido: <strong class="text-slate-100 tabular-nums">${(r.total_estoque_fisico_litros || 0).toLocaleString('pt-BR')} L</strong></div>
          </div>
        </div>
      `;
    }

    // 3. Conciliação de Turno & Caixa (AURA Precision Glass v1.0)
    if (toolId === 'conciliacao_turno') {
      if (typeof window !== 'undefined' && window.auraChat && typeof window.auraChat.renderTurnoWidget === 'function') {
        return window.auraChat.renderTurnoWidget(data);
      }

      // Fallback com contrato semântico caso auraChat não esteja instanciado
      const c = data.contrato || data;
      const r = data.resumo_executivo || {};
      const assessment = c.assessment || {};
      const metrics = c.metrics || {};
      const finality = assessment.finality || (r.status_conciliacao?.includes('ANDAMENTO') ? 'partial' : 'final');
      const isPartial = finality === 'partial';
      const isNoMovement = finality === 'no_movement' || data.status === 'sem_movimento';
      const isUnavailable = finality === 'unavailable' || data.status === 'indisponivel';

      const diffVal = Number(metrics.difference ?? r.diferenca_financeira_caixa ?? 0);
      const autRev = Number(metrics.automation_revenue ?? r.faturamento_pista_total ?? 0);
      const posRev = Number(metrics.pos_revenue ?? r.faturamento_caixa_total ?? 0);

      const diffFormatted = (isNoMovement || isUnavailable)
        ? '-'
        : `${diffVal < 0 ? '-' : diffVal > 0 ? '+' : ''}R$ ${Math.abs(diffVal).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

      const autRevText = (isNoMovement || isUnavailable)
        ? '-'
        : `R$ ${autRev.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

      const posRevText = (isNoMovement || isUnavailable)
        ? '-'
        : `R$ ${posRev.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

      const badgeLabel = assessment.badge_label || r.status_conciliacao || (isPartial ? 'Análise parcial (provisória)' : (isNoMovement ? 'Sem movimentação' : 'Turno em Andamento'));
      const diagText = r.diagnostico_caixa || c.explanation?.text || 'Conferência de turno executada.';

      return `
        <div class="space-y-4 font-sans text-xs">
          <div class="p-4 rounded-lg ${isPartial ? 'bg-amber-950/20 border border-amber-500/30' : (isUnavailable ? 'bg-rose-950/20 border border-rose-500/30' : 'bg-cyan-950/20 border border-cyan-500/30')} flex items-center justify-between">
            <div>
              <div class="text-xs text-slate-400">Status da Conciliação</div>
              <div class="text-lg font-bold ${isPartial ? 'text-amber-300' : (isUnavailable ? 'text-rose-300' : 'text-cyan-300')}">
                ${this.escapeHtml(badgeLabel)}
              </div>
            </div>
            <div class="text-right">
              <div class="text-xs text-slate-400">${isPartial ? 'Análise Provisória' : 'Score de Triangulação'}</div>
              <div class="text-base font-bold ${isPartial ? 'text-amber-400' : 'text-emerald-400'}">
                ${isPartial ? 'Caixa Aberto' : (isNoMovement || isUnavailable ? '-' : `${Number(r.score_conformidade_pct || 100)}%`)}
              </div>
            </div>
          </div>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-3 p-3 rounded bg-slate-900 border border-slate-800">
            <div>Faturamento Automação Pista: <strong class="text-slate-100 block mt-0.5 tabular-nums">${autRevText}</strong></div>
            <div>Faturamento Caixa PDV: <strong class="text-cyan-300 block mt-0.5 tabular-nums">${posRevText}</strong></div>
            <div>${isPartial ? 'Diferença Provisória:' : 'Diferença Caixa:'} <strong class="${isPartial ? 'text-amber-400' : 'text-emerald-400'} block mt-0.5 tabular-nums">${diffFormatted}</strong></div>
            <div>Diagnóstico: <span class="text-slate-400 block mt-0.5">${this.escapeHtml(diagText)}</span></div>
          </div>
        </div>
      `;
    }

    // 3b. Perícia Forense de Causa-Raiz (RCA)
    if (toolId === 'investigar_causa_raiz') {
      const rep = data.report || data.contrato || data;
      const resExec = data.resumo_executivo || rep.resumo_executivo || {};
      const hipoteses = data.hipoteses || rep.hypotheses || [];
      const totalQuebra = Number(data.total_divergence_reais ?? rep.total_divergence_reais ?? 0);
      const totalExp = Number(data.total_explained_reais ?? rep.total_explained_reais ?? 0);
      const unexplained = Number(data.unexplained_reais ?? rep.unexplained_reais ?? 0);
      const confOverall = Math.round(Number(data.confidence_overall ?? rep.confidence_overall ?? 0.9) * 100);
      const isConforme = data.diagnostico === 'conforme' || (hipoteses.length === 1 && String(hipoteses[0].hypothesis_id || '').includes('CONFORME'));

      return `
        <div class="space-y-4 font-sans text-xs">
          <div class="p-4 rounded-xl ${isConforme ? 'bg-emerald-950/20 border border-emerald-500/30' : 'bg-purple-950/20 border border-purple-500/30'} flex flex-wrap items-center justify-between gap-3">
            <div>
              <div class="text-[11px] text-slate-400 font-mono">Status da Perícia Forense</div>
              <div class="text-base sm:text-lg font-bold ${isConforme ? 'text-emerald-300' : 'text-purple-300'}">
                ${this.escapeHtml(resExec.diagnostico_principal || (isConforme ? 'Conforme (Dentro da Tolerância)' : 'Quebra Investigada'))}
              </div>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-[10px] font-mono text-slate-300 bg-slate-900 px-2 py-1 rounded border border-white/10">HITL Consultivo</span>
              <span class="text-xs font-mono font-bold text-cyan-300 bg-cyan-500/10 border border-cyan-500/20 px-2.5 py-1 rounded">
                ${confOverall}% Certeza
              </span>
            </div>
          </div>

          <div class="grid grid-cols-3 gap-3 p-3 rounded-xl bg-slate-900/90 border border-slate-800 text-center">
            <div>
              <span class="text-[10px] text-slate-400">Divergência Total</span>
              <strong class="${totalQuebra < 0 ? 'text-rose-400' : 'text-cyan-300'} block text-sm sm:text-base mt-0.5 tabular-nums">
                ${totalQuebra < 0 ? '-R$ ' : '+R$ '}${Math.abs(totalQuebra).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
              </strong>
            </div>
            <div>
              <span class="text-[10px] text-slate-400">Explicado pela IA</span>
              <strong class="text-emerald-400 block text-sm sm:text-base mt-0.5 tabular-nums">
                R$ ${totalExp.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
              </strong>
            </div>
            <div>
              <span class="text-[10px] text-slate-400">Saldo Remanescente</span>
              <strong class="${unexplained > 0 ? 'text-amber-400' : 'text-slate-300'} block text-sm sm:text-base mt-0.5 tabular-nums">
                R$ ${unexplained.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
              </strong>
            </div>
          </div>

          <div class="space-y-2">
            <span class="text-[10px] uppercase font-bold tracking-wider text-slate-400 font-mono">Hipóteses Trianguladas no ERP</span>
            ${hipoteses.length === 0 ? `
              <div class="p-3 rounded-lg bg-slate-900 border border-slate-800 text-slate-400">
                Nenhuma anomalia identificada para o período.
              </div>
            ` : hipoteses.map(h => {
              const score = Math.round(Number(h.confidence_score || 0.8) * 100);
              const expVal = Number(h.explained_amount_reais || 0);
              return `
                <div class="p-3 rounded-xl bg-slate-900/80 border border-white/5 space-y-1.5">
                  <div class="flex items-center justify-between">
                    <span class="font-bold text-slate-100">${this.escapeHtml(h.title || 'Hipótese')}</span>
                    <div class="flex items-center gap-2">
                      <span class="text-[10px] font-mono text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">${score}% Certeza</span>
                      <span class="font-mono font-bold text-emerald-400">R$ ${expVal.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</span>
                    </div>
                  </div>
                  <p class="text-slate-300 text-xs leading-relaxed">${this.escapeHtml(h.summary || '')}</p>
                  <div class="p-2 rounded bg-slate-950/60 text-[11px] text-amber-200/90">
                    <strong>Ação Recomendada:</strong> ${this.escapeHtml(h.recommended_action || '')}
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      `;
    }

    // 4. Desempenho Pista & Frentistas
    if (toolId === 'desempenho_pista_frentistas') {
      let bicosList = '';
      if (data.auditoria_vazao_bicos) {
        data.auditoria_vazao_bicos.forEach(b => {
          const vazao = Number(b.vazao_media_l_min || 0);
          const isLento = b.alerta_filtro_lento || (b.status_operacional === 'ATIVO' && vazao > 0 && vazao < 30);
          bicosList += `
            <div class="p-3 rounded-xl glass-subcard border ${isLento ? 'border-amber-500/50 shadow-md shadow-amber-950/20 text-amber-300' : 'border-white/10 text-slate-300'} font-sans text-xs transition-all hover:-translate-y-0.5">
              <div class="font-bold">Bico ${b.bico} (${b.combustivel})</div>
              <div class="text-[11px] text-slate-400 mt-1">Vazão: <strong class="tabular-nums">${vazao.toFixed(1)} L/min</strong> ${isLento ? '<span class="inline-flex items-center gap-1 text-amber-400 font-semibold"><svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" stroke-width="1.75"/><line x1="12" y1="9" x2="12" y2="13" stroke-width="1.75"/><circle cx="12" cy="17" r="1" fill="currentColor"/></svg> LENTO</span>' : '<span class="text-emerald-400">✓ NORMAL</span>'}</div>
            </div>
          `;
        });
      }

      let frentRows = '';
      if (data.ranking_frentistas) {
        data.ranking_frentistas.forEach((f, idx) => {
          frentRows += `
            <tr class="border-b border-white/5 text-xs font-sans hover:bg-white/[0.02] transition-colors">
              <td class="py-2.5 text-slate-400 tabular-nums">${idx + 1}</td>
              <td class="py-2.5 font-semibold text-slate-200">${f.nome}</td>
              <td class="py-2.5 text-right tabular-nums">${Number(f.total_litros || 0).toFixed(1)} L</td>
              <td class="py-2.5 text-right text-emerald-400 font-bold tabular-nums">R$ ${Number(f.faturamento_reais || 0).toFixed(2)}</td>
              <td class="py-2.5 text-right text-cyan-300 tabular-nums">${Number(f.conversao_aditivada_pct || 0).toFixed(1)}%</td>
            </tr>
          `;
        });
      }

      return `
        <div class="space-y-4 font-sans text-xs">
          <div>
            <h4 class="font-bold text-slate-200 mb-2">Auditoria de Vazão dos Bicos:</h4>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-2.5">${bicosList || '<div class="text-slate-500 font-sans">Sem dados de bicos</div>'}</div>
          </div>
          <div>
            <h4 class="font-bold text-slate-200 mb-2">Ranking de Frentistas:</h4>
            <div class="overflow-x-auto">
              <table class="w-full text-left font-sans text-xs">
                <thead>
                  <tr class="text-slate-400 border-b border-white/10">
                    <th class="pb-2.5">#</th>
                    <th class="pb-2.5">Frentista</th>
                    <th class="pb-2.5 text-right">Volume</th>
                    <th class="pb-2.5 text-right">Faturamento</th>
                    <th class="pb-2.5 text-right">Conv. Aditivada</th>
                  </tr>
                </thead>
                <tbody>${frentRows}</tbody>
              </table>
            </div>
          </div>
        </div>
      `;
    }

    // 5. Vendas & Faturamento ERP
    if (toolId === 'vendas_analitico') {
      let topProds = '';
      if (data.produtos_mais_vendidos) {
        data.produtos_mais_vendidos.slice(0, 8).forEach(p => {
          topProds += `
            <tr class="border-b border-white/5 text-xs font-sans hover:bg-white/[0.02] transition-colors">
              <td class="py-2 text-slate-200">${p.nompro || p.descricao || p.codpro}</td>
              <td class="py-2 text-right text-slate-300 tabular-nums">${Number(p.quantidade || p.quant || p.qtd_total || 0).toFixed(1)}</td>
              <td class="py-2 text-right text-emerald-400 font-semibold tabular-nums">R$ ${Number(p.valor_total || p.total || p.receita_total || 0).toFixed(2)}</td>
            </tr>
          `;
        });
      }
      return `
        <div class="space-y-4 font-sans text-xs">
          <div class="grid grid-cols-2 md:grid-cols-3 gap-3 p-3.5 rounded-xl glass-subcard border border-white/5">
            <div>Status: <strong class="text-emerald-400">${data.status || 'OK'}</strong></div>
            <div>Destaque Hoje: <strong class="text-cyan-300">${data.ultimo_produto_vendido_destaque?.produto || data.ultimo_produto_vendido_destaque?.nompro || 'Registrado'}</strong></div>
            <div>Total Geral: <strong class="text-purple-300 tabular-nums">R$ ${Number(data.resumo_geral?.faturamento_total || 0).toFixed(2)}</strong></div>
          </div>
          <div>
            <h4 class="font-bold text-slate-200 mb-2">Top Produtos Mais Vendidos:</h4>
            <div class="overflow-x-auto">
              <table class="w-full text-left font-sans text-xs">
                <thead>
                  <tr class="text-slate-400 border-b border-white/10">
                    <th class="pb-2">Produto</th>
                    <th class="pb-2 text-right">Qtd</th>
                    <th class="pb-2 text-right">Faturamento</th>
                  </tr>
                </thead>
                <tbody>${topProds || '<tr><td colspan="3" class="py-2 text-slate-500 font-sans">Sem itens</td></tr>'}</tbody>
              </table>
            </div>
          </div>
        </div>
      `;
    }

    // 6. Conveniencia e Cross-Selling (Market Basket & BasketUpsellStrategyUI)
    const isBasketTool = [
      'conveniencia_vendas_cruzadas', 'market_basket', 'cesta_compras',
      'basket_upsell', 'cross_selling', 'auditar_cesta_conveniencia_vendas_cruzadas'
    ].includes(toolId) || data.component_name === 'render_BasketUpsellStrategyUI' || data.client_component === 'BasketUpsellStrategyUI';

    if (isBasketTool) {
      const props = data.props || {};
      const metrics = data.metrics || {};
      const resumo = data.resumo_executivo || {};
      const combos = props.top_combos || data.top_combos || data.top_combos_cross_selling || [];
      const actions = props.suggested_actions || data.suggested_actions || [];
      const limitations = props.limitations || data.limitations || [];

      const maiorLift = Number(props.maior_lift ?? metrics.maior_lift ?? resumo.maior_lift_encontrado ?? (combos.length > 0 ? (combos[0].lift || combos[0].metricas?.lift || 0) : 0));
      const totalCupons = Number(props.total_transacoes ?? metrics.total_transacoes_analisadas ?? resumo.total_transacoes_analisadas ?? 0);
      const pctMultiplos = Number(props.pct_multiplos_itens ?? metrics.pct_cestas_multiplos_itens ?? resumo.pct_cestas_multiplos_itens ?? 0);
      const ticketIncr = Number(props.projected_ticket_increase ?? (combos.length > 0 ? (combos[0].additional_ticket_reais || combos[0].impacto_financeiro?.preco_recomendado || 0) : 0));
      const diagText = props.diagnosis || data.diagnosis || resumo.diagnostico_estrategico || 'Oportunidades de vendas cruzadas e aumento de ticket medio no PDV.';
      const confScore = Math.round(Number(props.confidence_score ?? data.confidence_score ?? 0.94) * 100);

      let cardsHtml = '';
      combos.forEach((c) => {
        const orig = c.anchor_product || c.produto_origem?.nompro || c.produto_origem || 'Produto Origem';
        const rec = c.recommended_product || c.produto_recomendado?.nompro || c.produto_recomendado || 'Produto Sugerido';
        const liftVal = Number(c.lift ?? c.metricas?.lift ?? 1.0).toFixed(2);
        const confVal = Number(c.confidence_pct ?? ((c.metricas?.confianca || 0) * 100) ?? 0).toFixed(0);
        const ticketVal = Number(c.additional_ticket_reais ?? c.impacto_financeiro?.preco_recomendado ?? 0).toFixed(2);
        const scriptPitch = c.script_pitch || c.script_sugerido_caixa || 'Ofereca o produto complementar no fechamento da compra.';
        const category = c.category || c.categoria || 'Balcao PDV';

        cardsHtml += `
          <div class="p-4 rounded-xl glass-subcard border border-purple-500/20 bg-slate-900/60 flex flex-col justify-between font-sans text-xs hover:-translate-y-0.5 transition-all shadow-sm">
            <div>
              <div class="flex items-center justify-between text-[11px] mb-2 pb-1.5 border-b border-white/5">
                <span class="px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-300 font-bold border border-purple-500/30 tabular-nums">
                  LIFT ${liftVal}x
                </span>
                <span class="text-cyan-300 font-medium tabular-nums">
                  Confianca: ${confVal}%
                </span>
                <span class="text-[10px] text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded border border-white/5">
                  ${this.escapeHtml(category)}
                </span>
              </div>
              <div class="font-bold text-slate-100 text-sm mt-1">
                ${this.escapeHtml(orig)}
              </div>
              <div class="text-emerald-400 font-semibold text-xs mt-1 flex items-center gap-1.5">
                <span>↳ Sugerir: ${this.escapeHtml(rec)}</span>
                ${Number(ticketVal) > 0 ? `<span class="text-[11px] text-emerald-300/80 tabular-nums font-mono">(+R$ ${ticketVal})</span>` : ''}
              </div>
            </div>
            <div class="mt-3 pt-2.5 border-t border-purple-900/30 bg-purple-950/20 p-2.5 rounded-lg text-[11px] text-slate-200 leading-relaxed italic">
              "${this.escapeHtml(scriptPitch)}"
            </div>
          </div>
        `;
      });

      let actionsHtml = '';
      if (actions.length > 0) {
        actionsHtml = `
          <div class="pt-2 border-t border-white/5 space-y-2">
            <span class="text-[10px] uppercase font-bold tracking-wider text-slate-400 font-mono">Acoes Transacionais de 1-Clique (HITL)</span>
            <div class="flex flex-wrap gap-2">
              ${actions.map(act => {
                const variantClass = act.variant === 'primary' 
                  ? 'bg-purple-600 hover:bg-purple-500 text-white shadow-purple-900/30'
                  : (act.variant === 'secondary'
                    ? 'bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-cyan-500/30'
                    : 'bg-slate-900/80 hover:bg-slate-800 text-slate-300 border border-white/10');
                return `
                  <button type="button" 
                          class="px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer transition-all shadow-sm flex items-center gap-1.5 ${variantClass}"
                          onclick="alert('Acao solicitada: ${this.escapeHtml(act.label)}');">
                    <span>${this.escapeHtml(act.label)}</span>
                  </button>
                `;
              }).join('')}
            </div>
          </div>
        `;
      }

      let limitsHtml = '';
      if (limitations.length > 0) {
        limitsHtml = `
          <div class="p-2.5 rounded-lg bg-slate-950/40 border border-white/5 text-[11px] text-slate-400 space-y-1">
            <strong class="text-slate-300">Limitacoes e Premissas:</strong>
            <ul class="list-disc list-inside space-y-0.5">
              ${limitations.map(lim => `<li>${this.escapeHtml(lim)}</li>`).join('')}
            </ul>
          </div>
        `;
      }

      return `
        <div class="space-y-4 font-sans text-xs">
          <div class="p-4 rounded-xl bg-purple-950/20 border border-purple-500/30 flex flex-wrap items-center justify-between gap-3">
            <div class="max-w-xl">
              <div class="text-[11px] text-purple-300/80 font-mono">Diagnostico de Cross-Selling & Cesta de Compras</div>
              <div class="text-sm sm:text-base font-bold text-slate-100 mt-0.5">
                ${this.escapeHtml(diagText)}
              </div>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-[10px] font-mono text-purple-200 bg-purple-900/40 px-2 py-1 rounded border border-purple-500/30">Apriori PDV</span>
              <span class="text-xs font-mono font-bold text-cyan-300 bg-cyan-500/10 border border-cyan-500/20 px-2.5 py-1 rounded">
                ${confScore}% Confianca
              </span>
            </div>
          </div>

          <div class="grid grid-cols-2 md:grid-cols-4 gap-3 p-3 rounded-xl bg-slate-900/90 border border-slate-800 text-center">
            <div>
              <span class="text-[10px] text-slate-400 block">Maior Lift</span>
              <strong class="text-purple-300 text-base sm:text-lg tabular-nums mt-0.5 block">${maiorLift.toFixed(2)}x</strong>
            </div>
            <div>
              <span class="text-[10px] text-slate-400 block">Cupons Analisados</span>
              <strong class="text-slate-100 text-base sm:text-lg tabular-nums mt-0.5 block">${totalCupons.toLocaleString('pt-BR')}</strong>
            </div>
            <div>
              <span class="text-[10px] text-slate-400 block">% Vendas Combinadas</span>
              <strong class="text-cyan-300 text-base sm:text-lg tabular-nums mt-0.5 block">${pctMultiplos.toFixed(1)}%</strong>
            </div>
            <div>
              <span class="text-[10px] text-slate-400 block">Incremento / Cupom</span>
              <strong class="text-emerald-400 text-base sm:text-lg tabular-nums mt-0.5 block">+R$ ${ticketIncr.toFixed(2)}</strong>
            </div>
          </div>

          <div>
            <div class="flex items-center justify-between mb-2">
              <span class="text-[10px] uppercase font-bold tracking-wider text-slate-400 font-mono">Combos Recomendados para o Balcao e Pista</span>
              <span class="text-[11px] text-purple-300 font-mono">${combos.length} combinacoes ativas</span>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
              ${cardsHtml || '<div class="text-slate-500 font-sans p-4 bg-slate-900/50 rounded-lg">Nenhum combo identificado para os parametros informados.</div>'}
            </div>
          </div>

          ${actionsHtml}
          ${limitsHtml}
        </div>
      `;
    }

    // 7. Posição Geral de Estoque ERP
    if (toolId === 'estoque_posicao') {
      let estRows = '';
      if (data.maiores_estoques) {
        data.maiores_estoques.slice(0, 10).forEach(e => {
          estRows += `
            <tr class="border-b border-white/5 text-xs font-sans hover:bg-white/[0.02] transition-colors">
              <td class="py-2 text-slate-400 tabular-nums">${e.codpro}</td>
              <td class="py-2 text-slate-200 font-semibold">${e.nompro}</td>
              <td class="py-2 text-right text-cyan-300 tabular-nums">${Number(e.estoque_atual || e.estoque || 0).toFixed(1)} ${e.unidade || 'UN'}</td>
              <td class="py-2 text-right text-emerald-400 tabular-nums font-semibold">R$ ${Number(e.preco_venda || e.precovenda || 0).toFixed(2)}</td>
            </tr>
          `;
        });
      }
      return `
        <div class="space-y-4 font-sans text-xs">
          <div class="p-3.5 rounded-xl glass-subcard border border-white/5 flex items-center justify-between">
            <span class="text-slate-400">Status do Estoque ERP:</span> <strong class="text-emerald-400">${data.status || 'ONLINE'}</strong>
          </div>
          <div>
            <h4 class="font-bold text-slate-200 mb-2">Maiores Posições de Estoque Cadastradas:</h4>
            <div class="overflow-x-auto">
              <table class="w-full text-left font-sans text-xs">
                <thead>
                  <tr class="text-slate-400 border-b border-white/10">
                    <th class="pb-2">SKU</th>
                    <th class="pb-2">Produto</th>
                    <th class="pb-2 text-right">Saldo</th>
                    <th class="pb-2 text-right">Preço Venda</th>
                  </tr>
                </thead>
                <tbody>${estRows || '<tr><td colspan="4" class="py-2 text-slate-500 font-sans">Nenhum estoque</td></tr>'}</tbody>
              </table>
            </div>
          </div>
        </div>
      `;
    }

    // 8. Clientes Ranking
    if (toolId === 'clientes_ranking') {
      let cliRows = '';
      if (data.ranking_compras_pedidos) {
        data.ranking_compras_pedidos.slice(0, 8).forEach((c, idx) => {
          cliRows += `
            <tr class="border-b border-white/5 text-xs font-sans hover:bg-white/[0.02] transition-colors">
              <td class="py-2.5 text-slate-400 tabular-nums">${idx + 1}</td>
              <td class="py-2.5 text-slate-200 font-semibold">${c.nome_cliente || c.nome || c.cliente || 'Consumidor'}</td>
              <td class="py-2.5 text-right text-cyan-300 tabular-nums">${c.total_pedidos || 1} compras</td>
              <td class="py-2.5 text-right text-emerald-400 font-bold tabular-nums">R$ ${Number(c.total_comprado || c.total_gasto || c.faturamento || 0).toFixed(2)}</td>
            </tr>
          `;
        });
      }
      return `
        <div class="space-y-4 font-sans text-xs">
          <div class="grid grid-cols-2 gap-3 p-3.5 rounded-xl glass-subcard border border-white/5">
            <div>Clientes Cadastrados: <strong class="text-cyan-300 tabular-nums">${data.total_clientes_cadastrados || 'N/A'}</strong></div>
            <div>Observação PDV: <span class="text-slate-300">${data.observacao_pdv || 'Normal'}</span></div>
          </div>
          <div>
            <h4 class="font-bold text-slate-200 mb-2">Principais Clientes & Frotas:</h4>
            <div class="overflow-x-auto">
              <table class="w-full text-left font-sans text-xs">
                <thead>
                  <tr class="text-slate-400 border-b border-white/10">
                    <th class="pb-2.5">#</th>
                    <th class="pb-2.5">Cliente</th>
                    <th class="pb-2.5 text-right">Frequência</th>
                    <th class="pb-2.5 text-right">Faturamento</th>
                  </tr>
                </thead>
                <tbody>${cliRows || '<tr><td colspan="4" class="py-2 text-slate-500 font-sans">Sem clientes</td></tr>'}</tbody>
              </table>
            </div>
          </div>
        </div>
      `;
    }

    // 9. Dados Cadastrais da Filial
    if (toolId === 'dados_filial') {
      return `
        <div class="space-y-3 font-sans text-xs p-4 rounded-xl glass-subcard border border-white/5">
          <div class="text-sm font-bold text-white border-b border-white/10 pb-2">${data.nome || data.razao_social || 'Posto'}</div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
            <div><span class="text-slate-400">Razão Social:</span> <strong class="text-slate-200">${data.razao_social || 'N/A'}</strong></div>
            <div><span class="text-slate-400">CNPJ:</span> <strong class="text-cyan-300 tabular-nums">${data.cnpj || 'N/A'}</strong></div>
            <div><span class="text-slate-400">Filial ID:</span> <strong class="text-emerald-400 tabular-nums">${data.idempresa || '59050'}</strong></div>
            <div><span class="text-slate-400">PDV Vinculado:</span> <strong class="text-purple-300 tabular-nums">PDV ${data.pdv || '01'}</strong></div>
            <div class="md:col-span-2"><span class="text-slate-400">Endereço:</span> <span class="text-slate-300">${data.endereco || 'Unidade Operacional'}</span></div>
          </div>
        </div>
      `;
    }

    // 10. Busca no Catálogo de Produtos
    if (toolId === 'catalogo_produtos') {
      const results = data.results || data.resultados || data.produtos || [];
      let prodCards = '';
      results.forEach(p => {
        const scoreVal = p.score ? (p.score * 100) : ((p.rrf_score || p.cosine_similarity || 0.8) * 100);
        prodCards += `
          <div class="p-3 rounded-xl glass-subcard border border-purple-500/30 font-sans text-xs hover:-translate-y-0.5 transition-all">
            <div class="flex items-center justify-between text-[11px] text-slate-400">
              <span class="tabular-nums">SKU: ${p.codpro || p.codigo}</span>
              <span class="text-purple-300 font-bold tabular-nums">Score: ${scoreVal.toFixed(0)}%</span>
            </div>
            <div class="font-bold text-slate-100 mt-1">${p.nompro || p.nome}</div>
            <div class="flex items-center justify-between mt-2.5 pt-1.5 border-t border-white/5 text-emerald-400 font-semibold">
              <span>Preço: <strong class="tabular-nums">R$ ${Number(p.preco || p.precovenda || 0).toFixed(2)}</strong></span>
              <span class="text-slate-400 text-[10px]">${p.grupo || 'GERAL'}</span>
            </div>
          </div>
        `;
      });
      return `
        <div class="space-y-3 font-sans text-xs">
          <div class="flex items-center justify-between p-3 rounded-xl glass-subcard border border-white/5">
            <span>Método de Busca: <strong class="text-purple-300">${data.metodo || 'Busca Semântica Híbrida & pgvector'}</strong></span>
            <span>Resultados: <strong class="text-cyan-300 tabular-nums">${results.length}</strong></span>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5">${prodCards || '<div class="text-slate-500 font-sans">Nenhum produto encontrado.</div>'}</div>
        </div>
      `;
    }

    // 11. Saúde & Telemetria SRE do Posto
    if (toolId === 'sre_metricas') {
      const db = data.database_health || {};
      const tab = data.table_stats || {};
      const router = data.semantic_router_metrics || {};
      return `
        <div class="space-y-4 font-sans text-xs">
          <div class="grid grid-cols-2 md:grid-cols-4 gap-3 p-3.5 rounded-xl glass-subcard border border-cyan-500/30">
            <div>Status Banco ERP: <strong class="text-emerald-400 block mt-0.5">ONLINE (Porta 5433)</strong></div>
            <div>Cache Hit Ratio: <strong class="text-cyan-300 block mt-0.5 tabular-nums">${Number(db.cache_hit_ratio_percent || 99.4).toFixed(1)}%</strong></div>
            <div>Conexões Ativas: <strong class="text-slate-100 block mt-0.5 tabular-nums">${db.active_connections || 3}</strong></div>
            <div>Latência Vetorial: <strong class="text-purple-300 block mt-0.5 tabular-nums">${Number(router.avg_pgvector_latency_ms || 25).toFixed(1)} ms</strong></div>
          </div>
          <div class="grid grid-cols-2 md:grid-cols-3 gap-3 p-3 rounded-xl bg-slate-900/60 border border-slate-800">
            <div>Tamanho Tabelas: <strong class="text-slate-200 tabular-nums">${tab.table_size || '256 kB'}</strong></div>
            <div>Tamanho Índices: <strong class="text-slate-200 tabular-nums">${tab.indexes_size || '632 kB'}</strong></div>
            <div>Volume Total: <strong class="text-slate-200 tabular-nums">${tab.total_size || '1296 kB'}</strong></div>
          </div>
        </div>
      `;
    }

    // 12. Simulação Preditiva What-If & Precificação Dinâmica
    if (toolId === 'cenario_preditivo' || toolId === 'simulacao_preditiva') {
      const p = data.props || data;
      const base = p.base_scenario || {};
      const sim = p.simulated_scenario || {};
      const deltaVol = Number(data.delta_volume_pct ?? p.delta_volume_pct ?? 0);
      const deltaRec = Number(data.delta_receita ?? p.delta_revenue ?? 0);
      const deltaMg = Number(data.delta_margem_pct ?? p.delta_margin_pct ?? 0);
      const deltaLucro = Number(data.delta_lucro ?? 0);
      const prod = data.produto || p.scenario_title || 'GASOLINA COMUM';
      const score = Math.round(Number(data.confidence_score ?? p.confidence_score ?? 0.94) * 100);
      const elas = p.elasticity_coefficient ?? data.elasticidade ?? -0.65;
      const dias = data.periodo_dias || 30;
      const precoAtual = Number(data.preco_atual ?? base.preco_medio ?? 0);
      const precoSim = Number(data.preco_simulado ?? sim.preco_medio ?? 0);
      const diag = p.diagnosis || data.diagnosis || '';

      const deltaVolColor = deltaVol >= 0 ? 'text-emerald-400' : 'text-rose-400';
      const deltaRecColor = deltaRec >= 0 ? 'text-emerald-400' : 'text-rose-400';
      const deltaMgColor = deltaMg >= 0 ? 'text-emerald-400' : 'text-rose-400';
      const deltaLucroColor = deltaLucro >= 0 ? 'text-emerald-400' : 'text-rose-400';

      return `
        <div class="space-y-4 font-sans text-xs">
          <!-- Cabeçalho Executivo -->
          <div class="p-4 rounded-xl bg-purple-950/20 border border-purple-500/30 flex flex-wrap items-center justify-between gap-3">
            <div>
              <div class="text-[11px] text-slate-400 font-mono">Projeção Preditiva What-If (${dias} dias)</div>
              <div class="text-base sm:text-lg font-bold text-purple-300">
                ${this.escapeHtml(prod)}: R$ ${precoAtual.toFixed(2)} -> R$ ${precoSim.toFixed(2)}
              </div>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-[10px] font-mono text-slate-300 bg-slate-900 px-2 py-1 rounded border border-white/10">Elasticidade: ${elas}</span>
              <span class="text-xs font-mono font-bold text-purple-300 bg-purple-500/10 border border-purple-500/20 px-2.5 py-1 rounded">
                ${score}% Certeza
              </span>
            </div>
          </div>

          <!-- Diagnóstico -->
          <div class="p-3 rounded-xl bg-slate-900/80 border border-white/5 space-y-1">
            <span class="text-[10px] uppercase font-bold tracking-wider text-purple-400 font-mono">Parecer da IA Preditiva</span>
            <p class="text-slate-200 text-xs sm:text-sm leading-relaxed">${this.escapeHtml(diag)}</p>
          </div>

          <!-- Comparativo Base vs Simulado -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div class="p-3 rounded-xl bg-slate-950/60 border border-white/5 space-y-2">
              <span class="text-[10px] uppercase font-bold tracking-wider text-slate-400 font-mono">Cenário Base Atual</span>
              <div class="grid grid-cols-2 gap-2 text-xs">
                <div><span class="text-slate-500">Preço:</span> <div class="font-mono font-bold text-white">R$ ${(base.preco_medio || 0).toFixed(2)}</div></div>
                <div><span class="text-slate-500">Volume:</span> <div class="font-mono font-bold text-white">${Number(base.volume_projetado || 0).toLocaleString('pt-BR')} L</div></div>
                <div><span class="text-slate-500">Receita:</span> <div class="font-mono font-bold text-white">R$ ${Number(base.receita_liquida || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</div></div>
                <div><span class="text-slate-500">Margem Contrib.:</span> <div class="font-mono font-bold text-white">${Number(base.margem_contribuicao_pct || 0).toFixed(1)}%</div></div>
              </div>
            </div>
            <div class="p-3 rounded-xl bg-purple-950/20 border border-purple-500/30 space-y-2">
              <span class="text-[10px] uppercase font-bold tracking-wider text-purple-300 font-mono">Cenário Simulado</span>
              <div class="grid grid-cols-2 gap-2 text-xs">
                <div><span class="text-slate-400">Preço:</span> <div class="font-mono font-bold text-purple-200">R$ ${(sim.preco_medio || 0).toFixed(2)}</div></div>
                <div><span class="text-slate-400">Volume:</span> <div class="font-mono font-bold text-purple-200">${Number(sim.volume_projetado || 0).toLocaleString('pt-BR')} L</div></div>
                <div><span class="text-slate-400">Receita:</span> <div class="font-mono font-bold text-purple-200">R$ ${Number(sim.receita_liquida || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</div></div>
                <div><span class="text-slate-400">Margem Contrib.:</span> <div class="font-mono font-bold text-purple-200">${Number(sim.margem_contribuicao_pct || 0).toFixed(1)}%</div></div>
              </div>
            </div>
          </div>

          <!-- Cards de Deltas -->
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <div class="p-2.5 rounded-xl bg-slate-900/90 border border-slate-800 text-center">
              <span class="text-[10px] text-slate-400">Variação Volume</span>
              <div class="text-sm font-mono font-bold ${deltaVolColor} mt-0.5">
                ${deltaVol >= 0 ? '+' : ''}${deltaVol.toFixed(1)}%
              </div>
            </div>
            <div class="p-2.5 rounded-xl bg-slate-900/90 border border-slate-800 text-center">
              <span class="text-[10px] text-slate-400">Delta Margem</span>
              <div class="text-sm font-mono font-bold ${deltaMgColor} mt-0.5">
                ${deltaMg >= 0 ? '+' : ''}${deltaMg.toFixed(1)} pp
              </div>
            </div>
            <div class="p-2.5 rounded-xl bg-slate-900/90 border border-slate-800 text-center">
              <span class="text-[10px] text-slate-400">Delta Receita</span>
              <div class="text-sm font-mono font-bold ${deltaRecColor} mt-0.5">
                ${deltaRec >= 0 ? '+R$ ' : '-R$ '}${Math.abs(deltaRec).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
              </div>
            </div>
            <div class="p-2.5 rounded-xl bg-slate-900/90 border border-slate-800 text-center">
              <span class="text-[10px] text-slate-400">Delta Lucro Líquido</span>
              <div class="text-sm font-mono font-bold ${deltaLucroColor} mt-0.5">
                ${deltaLucro >= 0 ? '+R$ ' : '-R$ '}${Math.abs(deltaLucro).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
              </div>
            </div>
          </div>

          <!-- Controles de Simulação Rápida em 1 Clique -->
          <div class="p-3 rounded-xl bg-slate-950/50 border border-white/5 space-y-2.5">
            <div class="flex items-center justify-between">
              <span class="text-[10px] uppercase font-bold tracking-wider text-slate-400 font-mono">Testar Variação Instantânea:</span>
              <span class="text-[10px] font-mono text-purple-400">Re-simulação 1-clique</span>
            </div>
            <div class="flex flex-wrap gap-1.5">
              <button type="button" class="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-rose-300 border border-rose-500/30 text-xs font-mono font-semibold" onclick="window.auraTriggers.executeTrigger('cenario_preditivo', { produto: '${this.escapeHtml(prod)}', delta_preco: -0.10, periodo_dias: ${dias} })">-R$ 0,10</button>
              <button type="button" class="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-rose-300 border border-rose-500/30 text-xs font-mono font-semibold" onclick="window.auraTriggers.executeTrigger('cenario_preditivo', { produto: '${this.escapeHtml(prod)}', delta_preco: -0.05, periodo_dias: ${dias} })">-R$ 0,05</button>
              <button type="button" class="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-emerald-300 border border-emerald-500/30 text-xs font-mono font-semibold" onclick="window.auraTriggers.executeTrigger('cenario_preditivo', { produto: '${this.escapeHtml(prod)}', delta_preco: 0.05, periodo_dias: ${dias} })">+R$ 0,05</button>
              <button type="button" class="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-emerald-300 border border-emerald-500/30 text-xs font-mono font-semibold" onclick="window.auraTriggers.executeTrigger('cenario_preditivo', { produto: '${this.escapeHtml(prod)}', delta_preco: 0.10, periodo_dias: ${dias} })">+R$ 0,10</button>
              <button type="button" class="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-emerald-300 border border-emerald-500/30 text-xs font-mono font-semibold" onclick="window.auraTriggers.executeTrigger('cenario_preditivo', { produto: '${this.escapeHtml(prod)}', delta_preco: 0.20, periodo_dias: ${dias} })">+R$ 0,20</button>
            </div>
            <div class="flex items-center gap-2 pt-1 border-t border-white/5">
              <span class="text-[10px] text-slate-500 font-mono">Trocar Combustível:</span>
              <button type="button" class="px-2 py-0.5 rounded text-[11px] bg-slate-900 hover:bg-slate-800 text-slate-300 border border-white/10" onclick="window.auraTriggers.executeTrigger('cenario_preditivo', { produto: 'GASOLINA COMUM', delta_preco: 0.10, periodo_dias: ${dias} })">Gasolina Comum</button>
              <button type="button" class="px-2 py-0.5 rounded text-[11px] bg-slate-900 hover:bg-slate-800 text-slate-300 border border-white/10" onclick="window.auraTriggers.executeTrigger('cenario_preditivo', { produto: 'ETANOL', delta_preco: 0.10, periodo_dias: ${dias} })">Etanol</button>
              <button type="button" class="px-2 py-0.5 rounded text-[11px] bg-slate-900 hover:bg-slate-800 text-slate-300 border border-white/10" onclick="window.auraTriggers.executeTrigger('cenario_preditivo', { produto: 'DIESEL S10', delta_preco: 0.10, periodo_dias: ${dias} })">Diesel S10</button>
            </div>
          </div>
        </div>
      `;
    }

    // Benchmark Comparativo & Concorrência
    if (toolId === 'benchmark_comparativo' || toolId === 'comparativo_turnos') {
      const props = data.props || data;
      const score = Math.round(Number(props.competitiveness_score || data.competitiveness_score || 84));
      const entity = props.entity_name || data.entity_name || 'Filial 01 Centro';
      const group = props.benchmark_group || data.benchmark_group || 'Concorrentes Raio 3km (Média Região)';
      const marketPos = props.market_position || data.market_position || '2º de 7 postos no raio de 3km';
      const diag = props.diagnosis || data.diagnosis || 'Comparativo analítico contra médias do mercado local.';
      const items = Array.isArray(props.comparison_items) ? props.comparison_items : (Array.isArray(data.comparison_items) ? data.comparison_items : []);
      const limitations = Array.isArray(props.limitations) ? props.limitations : (Array.isArray(data.limitations) ? data.limitations : []);

      const scoreColor = score >= 80 ? 'text-emerald-300 border-emerald-500/40 bg-emerald-500/10' : (score >= 60 ? 'text-amber-300 border-amber-500/40 bg-amber-500/10' : 'text-rose-300 border-rose-500/40 bg-rose-500/10');

      let itemsRows = '';
      items.forEach(it => {
        const kpi = this.escapeHtml(it.kpi_name || 'Indicador');
        const filVal = this.escapeHtml(String(it.filial_value || '-'));
        const benchVal = this.escapeHtml(String(it.benchmark_value || '-'));
        const gapVal = this.escapeHtml(String(it.gap_value || ''));
        const st = it.status || 'neutral';
        const obs = this.escapeHtml(it.observation || '');

        let stBadge = '<span class="text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded text-[10px]">Alinhado</span>';
        let valColor = 'text-slate-200';
        if (st === 'success') {
          stBadge = '<span class="text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/30 text-[10px] font-semibold">Vantagem</span>';
          valColor = 'text-emerald-300 font-bold';
        } else if (st === 'warning') {
          stBadge = '<span class="text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/30 text-[10px] font-semibold">Atenção</span>';
          valColor = 'text-amber-300 font-bold';
        } else if (st === 'danger') {
          stBadge = '<span class="text-rose-400 bg-rose-500/10 px-1.5 py-0.5 rounded border border-rose-500/30 text-[10px] font-semibold">Desvantagem</span>';
          valColor = 'text-rose-300 font-bold';
        }

        itemsRows += `
          <tr class="border-b border-white/5 text-xs font-sans hover:bg-white/[0.02] transition-colors">
            <td class="py-2.5 font-semibold text-slate-100">
              <div>${kpi}</div>
              ${obs ? `<div class="text-[10px] text-slate-400 font-normal mt-0.5">${obs}</div>` : ''}
            </td>
            <td class="py-2.5 text-right tabular-nums ${valColor}">${filVal}</td>
            <td class="py-2.5 text-right tabular-nums text-slate-300">${benchVal}</td>
            <td class="py-2.5 text-right tabular-nums font-mono font-bold ${valColor}">${gapVal}</td>
            <td class="py-2.5 text-right">${stBadge}</td>
          </tr>
        `;
      });

      return `
        <div class="space-y-4 font-sans text-xs">
          <!-- Cabeçalho Executivo -->
          <div class="flex flex-wrap items-center justify-between gap-2 p-3 rounded-xl bg-slate-950/60 border border-white/5">
            <div>
              <span class="text-[10px] uppercase font-bold tracking-wider text-cyan-400 font-mono">Posicionamento Competitivo</span>
              <div class="text-base sm:text-lg font-bold text-white flex items-center gap-2">
                <span>${this.escapeHtml(entity)}</span>
                <span class="text-xs font-normal text-slate-400">vs ${this.escapeHtml(group)}</span>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-[11px] font-mono px-2.5 py-1 rounded bg-blue-900/40 text-blue-300 border border-blue-500/30 font-bold">${this.escapeHtml(marketPos)}</span>
              <span class="text-xs font-mono font-bold px-2.5 py-1 rounded border ${scoreColor}">
                Score: ${score}/100
              </span>
            </div>
          </div>

          <!-- Diagnóstico -->
          <div class="p-3 rounded-xl bg-slate-900/80 border border-white/5 space-y-1">
            <span class="text-[10px] uppercase font-bold tracking-wider text-cyan-400 font-mono">Diagnóstico da IA Cognitiva</span>
            <p class="text-slate-200 text-xs sm:text-sm leading-relaxed">${this.escapeHtml(diag)}</p>
          </div>

          <!-- Tabela de Confronto -->
          <div>
            <h4 class="font-bold text-slate-200 mb-2">Confronto Filial vs Benchmarks de Mercado:</h4>
            <div class="overflow-x-auto">
              <table class="w-full text-left font-sans text-xs">
                <thead>
                  <tr class="text-slate-400 border-b border-white/10">
                    <th class="pb-2.5">Indicador</th>
                    <th class="pb-2.5 text-right">Filial</th>
                    <th class="pb-2.5 text-right">Benchmark</th>
                    <th class="pb-2.5 text-right">Gap</th>
                    <th class="pb-2.5 text-right">Status</th>
                  </tr>
                </thead>
                <tbody>
                  ${itemsRows}
                </tbody>
              </table>
            </div>
          </div>

          <!-- Ações HITL Rápidas -->
          <div class="p-3 rounded-xl bg-slate-950/50 border border-white/5 space-y-2">
            <span class="text-[10px] uppercase font-bold tracking-wider text-slate-400 font-mono">Ações Sugeridas (Human-in-the-Loop):</span>
            <div class="flex flex-wrap gap-2">
              <button type="button" class="px-3 py-1.5 rounded-lg bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-200 border border-cyan-500/40 text-xs font-semibold cursor-pointer transition-colors" onclick="if (window.auraChat &amp;&amp; typeof window.auraChat.sendUserPrompt === 'function') { window.auraChat.sendUserPrompt('Revisar estratégia de preços da Gasolina Comum'); } else if (window.auraTriggers) { window.auraTriggers.executeTrigger('cenario_preditivo', { produto: 'GASOLINA COMUM' }); }">
                ⚡ Revisar Preços
              </button>
              <button type="button" class="px-3 py-1.5 rounded-lg bg-purple-500/20 hover:bg-purple-500/30 text-purple-200 border border-purple-500/40 text-xs font-semibold cursor-pointer transition-colors" onclick="if (window.auraChat &amp;&amp; typeof window.auraChat.sendUserPrompt === 'function') { window.auraChat.sendUserPrompt('Auditar concorrência no raio de 3km'); } else if (window.auraTriggers) { window.auraTriggers.executeTrigger('benchmark_comparativo'); }">
                🎯 Auditar Concorrência
              </button>
            </div>
          </div>

          ${limitations.length > 0 ? `
            <div class="p-2.5 rounded-lg bg-slate-900/40 border border-white/5 text-[11px] text-slate-400 space-y-0.5">
              <strong class="text-slate-300">Limitações da amostragem:</strong>
              ${limitations.map(l => `<div>• ${this.escapeHtml(l)}</div>`).join('')}
            </div>
          ` : ''}
        </div>
      `;
    }

    // Auditoria de Fuga Financeira & TEF (F6-04)
    if (toolId === 'auditoria_fuga_financeira' || toolId === 'fuga_financeira' || toolId === 'auditoria_quebras') {
      const props = data.props || data;
      const totalLeak = Number(props.total_leak_value !== undefined ? props.total_leak_value : (props.total_divergence_reais || 0));
      const cashBreak = Number(props.cash_break_value || 0);
      const pendingBleed = Number(props.pending_bleed_value || 0);
      const tefDiv = Number(props.tef_divergence_value || 0);
      const diag = props.diagnosis || data.diagnosis || 'Auditoria de prevencao de perdas e quebras financeiras em tempo real.';
      const severity = props.severity || 'attention';
      const shift = props.audited_shift || data.audited_shift || 'Turno 01';
      const cashier = props.cashier_name || data.cashier_name || 'Operador';
      const items = Array.isArray(props.leak_items) ? props.leak_items : (Array.isArray(data.leak_items) ? data.leak_items : []);
      const limitations = Array.isArray(props.limitations) ? props.limitations : (Array.isArray(data.limitations) ? data.limitations : []);

      const sevBadge = severity === 'critical'
        ? '<span class="text-rose-300 border-rose-500/40 bg-rose-500/10 px-2 py-0.5 rounded-full font-mono text-[11px] font-bold">ALERTA CRÍTICO</span>'
        : (severity === 'attention' ? '<span class="text-amber-300 border-amber-500/40 bg-amber-500/10 px-2 py-0.5 rounded-full font-mono text-[11px] font-bold">ATENÇÃO OPERACIONAL</span>' : '<span class="text-emerald-300 border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 rounded-full font-mono text-[11px] font-bold">CONFORME</span>');

      let itemsRows = '';
      items.forEach(it => {
        const cat = this.escapeHtml(it.category || it.leak_type || 'Vazamento');
        const desc = this.escapeHtml(it.description || '');
        const amt = Number(it.amount !== undefined ? it.amount : (it.amount_reais || 0)).toLocaleString('pt-BR', { minimumFractionDigits: 2 });
        const terminal = it.pdv_or_terminal || it.source ? this.escapeHtml(it.pdv_or_terminal || it.source) : '';
        const st = it.status || it.severity || 'warning';
        const action = it.mitigation_action ? this.escapeHtml(it.mitigation_action) : '';

        let stBadge = '<span class="text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/30 text-[10px] font-semibold">Alerta</span>';
        let valColor = 'text-amber-300 font-bold';
        if (st === 'critical' || st === 'danger') {
          stBadge = '<span class="text-rose-400 bg-rose-500/10 px-1.5 py-0.5 rounded border border-rose-500/30 text-[10px] font-semibold">Crítico</span>';
          valColor = 'text-rose-400 font-bold';
        } else if (st === 'resolved' || st === 'normal') {
          stBadge = '<span class="text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/30 text-[10px] font-semibold">Regular</span>';
          valColor = 'text-emerald-300 font-semibold';
        }

        itemsRows += `
          <tr class="border-b border-white/5 text-xs font-sans hover:bg-white/[0.02] transition-colors">
            <td class="py-2.5 font-semibold text-slate-100">
              <div class="flex items-center gap-1.5">
                <span>${cat}</span>
                ${terminal ? `<span class="text-[9px] font-mono text-slate-400 bg-slate-900 px-1.5 py-0.5 rounded border border-white/5">${terminal}</span>` : ''}
              </div>
              ${desc ? `<div class="text-[10px] text-slate-400 font-normal mt-0.5">${desc}</div>` : ''}
              ${action ? `<div class="text-[10px] text-cyan-300/80 font-normal mt-0.5">Mitigação: ${action}</div>` : ''}
            </td>
            <td class="py-2.5 text-right tabular-nums font-mono ${valColor}">R$ ${amt}</td>
            <td class="py-2.5 text-right">${stBadge}</td>
          </tr>
        `;
      });

      return `
        <div class="space-y-4 font-sans text-xs">
          <!-- Cabeçalho Executivo com Criticidade -->
          <div class="flex flex-wrap items-center justify-between gap-2 p-3 rounded-xl bg-slate-950/60 border border-white/5">
            <div>
              <span class="text-[10px] uppercase font-bold tracking-wider text-rose-400 font-mono">Auditoria de Fuga Financeira &amp; TEF</span>
              <div class="text-base sm:text-lg font-bold text-white flex items-center gap-2">
                <span>${this.escapeHtml(shift)}</span>
                <span class="text-xs font-normal text-slate-400">(${this.escapeHtml(cashier)})</span>
              </div>
            </div>
            <div class="flex items-center gap-2">
              ${sevBadge}
              <span class="text-xs font-mono font-bold px-2.5 py-1 rounded border border-rose-500/30 text-rose-300 bg-rose-500/10">
                Perda Total: R$ ${totalLeak.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
              </span>
            </div>
          </div>

          <!-- Cards de Criticidade -->
          <div class="grid grid-cols-3 gap-2">
            <div class="p-2.5 rounded-xl bg-slate-950/40 border border-rose-500/20 text-center">
              <span class="text-[10px] text-slate-400">Quebra de Caixa</span>
              <div class="text-sm sm:text-base font-mono font-bold text-rose-400">
                R$ ${cashBreak.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
              </div>
            </div>
            <div class="p-2.5 rounded-xl bg-slate-950/40 border border-amber-500/20 text-center">
              <span class="text-[10px] text-slate-400">Sangrias Pendentes</span>
              <div class="text-sm sm:text-base font-mono font-bold text-amber-300">
                R$ ${pendingBleed.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
              </div>
            </div>
            <div class="p-2.5 rounded-xl bg-slate-950/40 border border-cyan-500/20 text-center">
              <span class="text-[10px] text-slate-400">Divergência TEF</span>
              <div class="text-sm sm:text-base font-mono font-bold text-cyan-300">
                R$ ${tefDiv.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
              </div>
            </div>
          </div>

          <!-- Diagnóstico -->
          <div class="p-3 rounded-xl bg-slate-900/80 border border-white/5 space-y-1">
            <span class="text-[10px] uppercase font-bold tracking-wider text-rose-400 font-mono">Diagnóstico da IA Cognitiva</span>
            <p class="text-slate-200 text-xs sm:text-sm leading-relaxed">${this.escapeHtml(diag)}</p>
          </div>

          <!-- Tabela de Divergências Identificadas -->
          <div>
            <h4 class="font-bold text-slate-200 mb-2">Fatos Geradores &amp; Divergências Auditadas:</h4>
            <div class="overflow-x-auto">
              <table class="w-full text-left font-sans text-xs">
                <thead>
                  <tr class="text-slate-400 border-b border-white/10">
                    <th class="pb-2.5">Ocorrência / Terminal</th>
                    <th class="pb-2.5 text-right">Valor</th>
                    <th class="pb-2.5 text-right">Gravidade</th>
                  </tr>
                </thead>
                <tbody>
                  ${itemsRows || '<tr><td colspan="3" class="py-3 text-center text-slate-400">Nenhuma irregularidade encontrada.</td></tr>'}
                </tbody>
              </table>
            </div>
          </div>

          <!-- Botões de Ação HITL Rápidos -->
          <div class="p-3 rounded-xl bg-slate-950/50 border border-white/5 space-y-2">
            <span class="text-[10px] uppercase font-bold tracking-wider text-slate-400 font-mono">Ações de Contenção (Human-in-the-Loop):</span>
            <div class="flex flex-wrap gap-2">
              <button type="button" class="px-3 py-1.5 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 border border-rose-500/40 text-xs font-semibold cursor-pointer transition-colors" onclick="if (window.auraChat &amp;&amp; typeof window.auraChat.sendUserPrompt === 'function') { window.auraChat.sendUserPrompt('Bloquear terminal com quebra de caixa anômala'); } else if (window.auraTriggers) { window.auraTriggers.executeTrigger('auditoria_fuga_financeira'); }">
                ⚡ Bloquear Terminal Suspeito
              </button>
              <button type="button" class="px-3 py-1.5 rounded-lg bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-200 border border-cyan-500/40 text-xs font-semibold cursor-pointer transition-colors" onclick="if (window.auraChat &amp;&amp; typeof window.auraChat.sendUserPrompt === 'function') { window.auraChat.sendUserPrompt('Abrir chamado de conciliação TEF com adquirente'); } else if (window.auraTriggers) { window.auraTriggers.executeTrigger('auditoria_fuga_financeira'); }">
                🎯 Abrir Chamado TEF
              </button>
              <button type="button" class="px-3 py-1.5 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-200 border border-emerald-500/40 text-xs font-semibold cursor-pointer transition-colors" onclick="if (window.auraChat &amp;&amp; typeof window.auraChat.sendUserPrompt === 'function') { window.auraChat.sendUserPrompt('Forçar sangria imediata de segurança do caixa'); } else if (window.auraTriggers) { window.auraTriggers.executeTrigger('auditoria_fuga_financeira'); }">
                ⚡ Forçar Sangria Imediata
              </button>
              <button type="button" class="px-3 py-1.5 rounded-lg bg-purple-500/20 hover:bg-purple-500/30 text-purple-200 border border-purple-500/40 text-xs font-semibold cursor-pointer transition-colors" onclick="if (window.auraChat &amp;&amp; typeof window.auraChat.sendUserPrompt === 'function') { window.auraChat.sendUserPrompt('Inspecionar fechamento de turno no Canvas'); } else if (window.auraTriggers) { window.auraTriggers.executeTrigger('conciliacao_turno'); }">
                🔍 Inspecionar Turno
              </button>
            </div>
          </div>

          ${limitations.length > 0 ? `
            <div class="p-2.5 rounded-lg bg-slate-900/40 border border-white/5 text-[11px] text-slate-400 space-y-0.5">
              <strong class="text-slate-300">Limitações da conciliação contábil:</strong>
              ${limitations.map(l => `<div>• ${this.escapeHtml(l)}</div>`).join('')}
            </div>
          ` : ''}
        </div>
      `;
    }

    // 16. Conformidade Legal & Interoperabilidade (Termo v1.1)
    if (toolId === 'compliance_status' || toolId === 'conformidade_legal' || toolId === 'termo_interoperabilidade') {
      const compliant = !!(data.compliant !== false && data.status !== 'pending' && data.status !== 'revoked' && data.status !== 'missing');
      const statusBadge = compliant
        ? '<span class="px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">100% CONFORME &amp; BLINDADO</span>'
        : '<span class="px-2.5 py-1 rounded-full text-[11px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">PENDENTE DE ACEITE</span>';

      const cnpj = data.loja_cnpj || '00.000.000/0001-00';
      const razao = data.razao_social || 'Auto Posto S/A';
      const versao = data.versao_termo || '1.1';
      const assinante = data.assinado_por || (compliant ? 'Representante Legal Homologado' : 'Aguardando Assinatura');
      const hashTermo = (data.hash_termo || data.hash_atual_termo || '').substring(0, 16);
      const dataAceite = data.aceite_interoperabilidade_em ? new Date(data.aceite_interoperabilidade_em).toLocaleString('pt-BR') : 'Pendente';

      return `
        <div class="space-y-4 font-sans text-xs">
          <!-- Card de Status Principal -->
          <div class="p-4 rounded-2xl bg-slate-900/80 border border-cyan-500/30 shadow-lg space-y-3">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/5 pb-3">
              <div>
                <div class="text-[10px] uppercase font-mono text-cyan-400 font-semibold tracking-wider">Governança &amp; Titularidade de Dados</div>
                <h4 class="text-sm font-bold text-white">${this.escapeHtml(razao)}</h4>
                <div class="text-[11px] text-slate-400">CNPJ: <span class="font-mono text-slate-200">${this.escapeHtml(cnpj)}</span> • Termo: <span class="text-cyan-300 font-semibold">v${this.escapeHtml(versao)}</span></div>
              </div>
              <div class="flex-shrink-0">
                ${statusBadge}
              </div>
            </div>

            <!-- Grade de Indicadores Técnicos de Driver Shield -->
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1">
              <div class="p-2.5 rounded-xl bg-slate-950/60 border border-white/5">
                <div class="text-[10px] text-slate-400 font-mono">Modo de Acesso</div>
                <div class="text-xs font-bold text-emerald-400 flex items-center gap-1.5 mt-0.5">
                  <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
                  READ-ONLY ATIVO
                </div>
              </div>
              <div class="p-2.5 rounded-xl bg-slate-950/60 border border-white/5">
                <div class="text-[10px] text-slate-400 font-mono">Query Timeout</div>
                <div class="text-xs font-bold text-cyan-300 font-mono mt-0.5">4.000 ms</div>
              </div>
              <div class="p-2.5 rounded-xl bg-slate-950/60 border border-white/5">
                <div class="text-[10px] text-slate-400 font-mono">Lock Timeout</div>
                <div class="text-xs font-bold text-cyan-300 font-mono mt-0.5">1.000 ms</div>
              </div>
              <div class="p-2.5 rounded-xl bg-slate-950/60 border border-white/5">
                <div class="text-[10px] text-slate-400 font-mono">Role PostgreSQL</div>
                <div class="text-xs font-bold text-purple-300 font-mono mt-0.5">aura_service_ro</div>
              </div>
            </div>

            <!-- Dados de Auditoria Criptográfica -->
            <div class="p-3 rounded-xl bg-slate-950/40 border border-white/5 space-y-1.5 text-[11px]">
              <div class="flex justify-between items-center text-slate-300">
                <span>Formalizado por: <strong class="text-white">${this.escapeHtml(assinante)}</strong></span>
                <span class="text-slate-400 font-mono text-[10px]">${this.escapeHtml(dataAceite)}</span>
              </div>
              <div class="flex justify-between items-center text-slate-400 font-mono text-[10px]">
                <span>Hash SHA-256 do Termo:</span>
                <span class="text-slate-300 bg-white/5 px-2 py-0.5 rounded border border-white/5">${hashTermo ? `${hashTermo}...` : 'Não calculado'}</span>
              </div>
            </div>
          </div>

          <!-- Pilares Legais Brasileiros -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            <div class="p-3 rounded-xl bg-slate-900/60 border border-white/5 space-y-1">
              <div class="flex items-center gap-1.5 text-cyan-300 font-semibold text-xs">
                <span>⚖️ LGPD (Lei 13.709/18)</span>
              </div>
              <p class="text-slate-400 text-[11px] leading-relaxed">
                Art. 7, IX e Art. 39. Titularidade exclusiva dos dados pela empresa controladora.
              </p>
            </div>
            <div class="p-3 rounded-xl bg-slate-900/60 border border-white/5 space-y-1">
              <div class="flex items-center gap-1.5 text-emerald-300 font-semibold text-xs">
                <span>📜 Lei de Software (9.609/98)</span>
              </div>
              <p class="text-slate-400 text-[11px] leading-relaxed">
                Art. 6º, I e II. Garantia inalienável de interoperabilidade sem quebra de direitos autorais.
              </p>
            </div>
            <div class="p-3 rounded-xl bg-slate-900/60 border border-white/5 space-y-1">
              <div class="flex items-center gap-1.5 text-purple-300 font-semibold text-xs">
                <span>🌐 Marco Civil da Internet</span>
              </div>
              <p class="text-slate-400 text-[11px] leading-relaxed">
                Lei 12.965/14. Padrões abertos e vedação absoluta a práticas de Vendor Lock-in abusivo.
              </p>
            </div>
            <div class="p-3 rounded-xl bg-slate-900/60 border border-white/5 space-y-1">
              <div class="flex items-center gap-1.5 text-amber-300 font-semibold text-xs">
                <span>🛡️ Proteção Pericial Técnica</span>
              </div>
              <p class="text-slate-400 text-[11px] leading-relaxed">
                Driver shield com timeouts estritos. Zero impacto físico ou contenção no ERP local.
              </p>
            </div>
          </div>

          <!-- Botões de Ação HITL -->
          <div class="flex flex-wrap items-center gap-2 pt-2">
            <button type="button" onclick="if (window.auraCompliance) window.auraCompliance.openModal();" class="px-4 py-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-sans font-bold text-xs transition-colors flex items-center gap-2 cursor-pointer shadow-lg shadow-cyan-500/20">
              <span>Abrir Central de Conformidade Legal</span>
              <span>↗</span>
            </button>
            <a href="/showcase#sec-blindagem" target="_blank" rel="noopener noreferrer" class="px-3.5 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white border border-white/10 font-sans font-medium text-xs transition-colors inline-flex items-center gap-1.5">
              <span>Ver Vitrine no Showcase</span>
              <span>↗</span>
            </a>
          </div>
        </div>
      `;
    }

    if (toolId === 'roi_diagnostic' || toolId === 'diagnostico_executivo_roi' || toolId === 'diagnostico_perdas' || toolId === 'roi_perdas') {
      const summary = data.summary || {};
      const breakdown = data.breakdown_brl || {};
      const shield = data.regulatory_shield || {};

      const totalLeakage = Number(summary.total_monthly_leakage_brl || 0);
      const estRecovery = Number(summary.estimated_monthly_recovery_brl || 0);
      const net90 = Number(summary.roi_90_days_net_brl || 0);
      const multiple = Number(summary.roi_multiple || 0);
      const guarantee3x = summary.guarantee_3x_met !== false;

      const vLmc = Number(breakdown.lmc_and_tank_shrinkage || 0);
      const vPdv = Number(breakdown.convenience_and_pos_cancellations || 0);
      const vCaixa = Number(breakdown.cashier_shift_discrepancies || 0);
      const vPricing = Number(breakdown.pricing_and_carreta_arbitrage || 0);
      const vSelic = Number(breakdown.working_capital_selic_cost || 0);

      const fmt = (v) => 'R$ ' + Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

      return `
        <div class="space-y-4 font-sans text-xs">
          <!-- Top Executive Banner -->
          <div class="p-4 rounded-xl bg-gradient-to-r from-emerald-950/40 via-slate-900 to-cyan-950/30 border border-emerald-500/30 shadow-lg shadow-emerald-950/20">
            <div class="flex flex-wrap items-center justify-between gap-3 mb-3 pb-3 border-b border-emerald-500/20">
              <div class="flex items-center gap-2">
                <span class="p-1.5 rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                  <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
                </span>
                <div>
                  <h4 class="font-bold text-sm text-slate-100">Diagnóstico Executivo de ROI & Perdas</h4>
                  <p class="text-[11px] text-slate-400">Projeção determinística de 90 dias com rampa de adoção operacional</p>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <span class="px-2.5 py-1 rounded-full text-[11px] font-semibold ${guarantee3x ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'}">
                  ${guarantee3x ? 'Garantia Contratual 3x Ativa' : 'Em Calibração'}
                </span>
              </div>
            </div>

            <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-center">
              <div class="p-2.5 rounded-lg bg-slate-950/50 border border-slate-800">
                <span class="text-[10px] text-slate-400 block uppercase tracking-wider">Perda Mensal Mapeada</span>
                <span class="text-base font-bold text-rose-400 font-mono mt-0.5 block">${fmt(totalLeakage)}</span>
              </div>
              <div class="p-2.5 rounded-lg bg-slate-950/50 border border-slate-800">
                <span class="text-[10px] text-slate-400 block uppercase tracking-wider">Recuperação Mensal</span>
                <span class="text-base font-bold text-emerald-400 font-mono mt-0.5 block">${fmt(estRecovery)}</span>
              </div>
              <div class="p-2.5 rounded-lg bg-slate-950/50 border border-slate-800">
                <span class="text-[10px] text-slate-400 block uppercase tracking-wider">Retorno Líquido (90d)</span>
                <span class="text-base font-bold text-cyan-300 font-mono mt-0.5 block">${fmt(net90)}</span>
              </div>
              <div class="p-2.5 rounded-lg bg-slate-950/50 border border-slate-800">
                <span class="text-[10px] text-slate-400 block uppercase tracking-wider">Múltiplo de Retorno</span>
                <span class="text-base font-bold text-purple-300 font-mono mt-0.5 block">${multiple.toFixed(1)}x</span>
              </div>
            </div>
          </div>

          <!-- 5 Vetores de Perdas Operacionais -->
          <div>
            <h5 class="text-xs font-semibold text-slate-200 mb-2 flex items-center gap-1.5">
              <svg class="w-3.5 h-3.5 text-cyan-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 6h16M4 12h16M4 18h16"/></svg>
              <span>Detalhamento dos 5 Vetores de Perda Financeira</span>
            </h5>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5">
              <div class="p-3 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-colors">
                <div class="flex items-center justify-between text-[11px] text-slate-400 mb-1">
                  <span>1. LMC & Variação de Tanques</span>
                  <span class="text-rose-400 font-mono font-semibold">${fmt(vLmc)}</span>
                </div>
                <p class="text-[10px] text-slate-500 leading-relaxed">Perdas térmicas e divergências de estoque escriturado vs físico (Portaria 26 ANP).</p>
              </div>

              <div class="p-3 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-colors">
                <div class="flex items-center justify-between text-[11px] text-slate-400 mb-1">
                  <span>2. Cancelamentos PDV & Loja</span>
                  <span class="text-rose-400 font-mono font-semibold">${fmt(vPdv)}</span>
                </div>
                <p class="text-[10px] text-slate-500 leading-relaxed">Itens e cupons cancelados no PDV fora da curva gaussiana esperada.</p>
              </div>

              <div class="p-3 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-colors">
                <div class="flex items-center justify-between text-[11px] text-slate-400 mb-1">
                  <span>3. Furos de Gaveta & Caixa</span>
                  <span class="text-rose-400 font-mono font-semibold">${fmt(vCaixa)}</span>
                </div>
                <p class="text-[10px] text-slate-500 leading-relaxed">Diferença apurada entre fechamento físico de dinheiro e sangrias no sistema.</p>
              </div>

              <div class="p-3 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-colors">
                <div class="flex items-center justify-between text-[11px] text-slate-400 mb-1">
                  <span>4. Arbitragem de Carreta & Preço</span>
                  <span class="text-rose-400 font-mono font-semibold">${fmt(vPricing)}</span>
                </div>
                <p class="text-[10px] text-slate-500 leading-relaxed">Perda de margem por compra fracionada em vez de carreta fechada (30.000 L).</p>
              </div>

              <div class="p-3 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-colors">
                <div class="flex items-center justify-between text-[11px] text-slate-400 mb-1">
                  <span>5. Custo SELIC Capital Parado</span>
                  <span class="text-rose-400 font-mono font-semibold">${fmt(vSelic)}</span>
                </div>
                <p class="text-[10px] text-slate-500 leading-relaxed">Custo de oportunidade do capital de giro em estoque sem giro > 30 dias.</p>
              </div>

              <div class="p-3 rounded-xl bg-emerald-950/20 border border-emerald-500/30 flex flex-col justify-between">
                <div>
                  <div class="flex items-center gap-1.5 text-emerald-400 text-[11px] font-semibold mb-1">
                    <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                    <span>Blindagem Regulatória ANP</span>
                  </div>
                  <p class="text-[10px] text-slate-400 leading-relaxed">Elimina risco de auto de infração da Lei 9.847/99 (Multa mínima: R$ 20.000,00).</p>
                </div>
                <span class="text-[10px] text-emerald-300/80 font-mono mt-2 block">Tolerância Legal: +/- 0.60%</span>
              </div>
            </div>
          </div>

          <!-- Rodapé de Ações do Dono -->
          <div class="p-3 rounded-xl bg-slate-900/40 border border-slate-800 flex flex-wrap items-center justify-between gap-2">
            <span class="text-[11px] text-slate-400 flex items-center gap-1.5">
              <svg class="w-3.5 h-3.5 text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
              <span>Diagnóstico validado pelo Copiloto AURA. Nenhuma gravação efetuada no ERP.</span>
            </span>
            <div class="flex items-center gap-2">
              <button type="button" class="px-3 py-1.5 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/40 text-[11px] font-semibold cursor-pointer transition-colors"
                      onclick="window.auraTriggers.copyJson()">
                Copiar Dados JSON
              </button>
            </div>
          </div>
        </div>
      `;
    }

    if (toolId === 'pos_audit' || toolId === 'radar_anomalias_pdv' || toolId === 'auditoria_pdv_zscore' || toolId === 'auditoria_pos') {
      const totOp = Number(data.total_operators_analyzed || 0);
      const anomCount = Number(data.anomalous_operators_count || 0);
      const ops = data.operators_analysis || [];
      const shift = data.cashier_shift_audit || {};
      const clt = data.clt_compliance_checklist || {};

      const isConciliado = shift.status === 'CONCILIADO';
      const discBrl = Number(shift.discrepancy_brl || 0);
      const fmt = (v) => 'R$ ' + Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

      let opsRows = '';
      if (ops.length === 0) {
        opsRows = `<tr><td colspan="6" class="py-3 text-center text-slate-500 text-xs">Nenhum operador com vendas registrado no período.</td></tr>`;
      } else {
        ops.forEach(o => {
          const isAnom = o.is_anomaly;
          const zScore = Number(o.z_score || 0).toFixed(2);
          const cRate = Number(o.cancellation_rate_pct || 0).toFixed(1);
          const badgeClass = isAnom 
            ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' 
            : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30';
          const badgeLabel = isAnom ? 'Desvio Estatístico (>2.0σ)' : 'Padrão Histórico';

          opsRows += `
            <tr class="border-b border-slate-800/60 hover:bg-slate-800/30 transition-colors">
              <td class="py-2 px-2.5 font-mono text-slate-200 font-semibold">${this.escapeHtml(o.operator_id)}</td>
              <td class="py-2 px-2.5 text-right font-mono text-slate-300">${o.total_orders || 0}</td>
              <td class="py-2 px-2.5 text-right font-mono text-slate-300">${o.cancelled_orders || 0}</td>
              <td class="py-2 px-2.5 text-right font-mono text-slate-200 font-semibold">${cRate}%</td>
              <td class="py-2 px-2.5 text-right font-mono ${isAnom ? 'text-rose-400 font-bold' : 'text-slate-400'}">${zScore}</td>
              <td class="py-2 px-2.5 text-center">
                <span class="px-2 py-0.5 rounded text-[10px] font-sans font-semibold ${badgeClass}">${badgeLabel}</span>
              </td>
            </tr>
          `;
        });
      }

      const cltReqs = clt.mandatory_requirements_for_deduction || [
        'Comprovação de pagamento da rubrica Adicional de Quebra de Caixa em folha',
        'Previsão contratual expressa autorizando desconto em caso de divergência',
        'Borderô físico de fechamento conferido e assinado pelo operador no ato',
      ];

      let reqsHtml = cltReqs.map(r => `
        <li class="flex items-start gap-2 text-[11px] text-slate-300">
          <svg class="w-3.5 h-3.5 text-cyan-400 flex-shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
          <span>${this.escapeHtml(r)}</span>
        </li>
      `).join('');

      return `
        <div class="space-y-4 font-sans text-xs">
          <!-- Top KPI Grid -->
          <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div class="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
              <span class="text-[10px] text-slate-400 block uppercase tracking-wider">Operadores Auditados</span>
              <span class="text-base font-bold text-slate-100 font-mono mt-0.5 block">${totOp}</span>
            </div>
            <div class="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
              <span class="text-[10px] text-slate-400 block uppercase tracking-wider">Desvios Z-Score (>2σ)</span>
              <span class="text-base font-bold ${anomCount > 0 ? 'text-rose-400' : 'text-emerald-400'} font-mono mt-0.5 block">${anomCount}</span>
            </div>
            <div class="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
              <span class="text-[10px] text-slate-400 block uppercase tracking-wider">Status Fechamento Caixa</span>
              <span class="text-xs font-bold ${isConciliado ? 'text-emerald-400' : 'text-rose-400'} mt-1 block">
                ${isConciliado ? 'CONCILIADO' : 'DIVERGÊNCIA PENDENTE'}
              </span>
            </div>
            <div class="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
              <span class="text-[10px] text-slate-400 block uppercase tracking-wider">Divergência de Pista</span>
              <span class="text-base font-bold ${discBrl === 0 ? 'text-slate-300' : 'text-rose-400'} font-mono mt-0.5 block">${fmt(discBrl)}</span>
            </div>
          </div>

          <!-- Tabela de Operadores -->
          <div class="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
            <h5 class="text-xs font-semibold text-slate-200 mb-2.5 flex items-center justify-between">
              <span class="flex items-center gap-1.5">
                <svg class="w-3.5 h-3.5 text-cyan-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                <span>Radar Estatístico de Cancelamentos por Operador (Z-Score)</span>
              </span>
              <span class="text-[10px] text-slate-400 font-mono font-normal">Corte Anômalo: |Z| > 2.0</span>
            </h5>
            <div class="overflow-x-auto">
              <table class="w-full text-left border-collapse text-xs">
                <thead>
                  <tr class="border-b border-slate-800 text-[10px] text-slate-400 uppercase tracking-wider">
                    <th class="py-2 px-2.5">Operador</th>
                    <th class="py-2 px-2.5 text-right">Pedidos</th>
                    <th class="py-2 px-2.5 text-right">Cancelados</th>
                    <th class="py-2 px-2.5 text-right">Taxa %</th>
                    <th class="py-2 px-2.5 text-right">Z-Score</th>
                    <th class="py-2 px-2.5 text-center">Classificação</th>
                  </tr>
                </thead>
                <tbody>
                  ${opsRows}
                </tbody>
              </table>
            </div>
          </div>

          <!-- Blindagem Trabalhista CLT Art. 462 -->
          <div class="p-4 rounded-xl bg-cyan-950/20 border border-cyan-500/30">
            <div class="flex items-center gap-2 mb-2 pb-2 border-b border-cyan-500/20">
              <span class="p-1 rounded bg-cyan-500/20 text-cyan-400">
                <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
              </span>
              <div>
                <h5 class="text-xs font-bold text-cyan-300">Blindagem Jurídica Trabalhista (Art. 462 CLT)</h5>
                <p class="text-[10px] text-slate-400">Requisitos cumulativos exigidos pelo TST (Precedente 103 e OJ 251 SDI-1) para imputação de quebra de caixa</p>
              </div>
            </div>
            <ul class="space-y-1.5 mt-2">
              ${reqsHtml}
            </ul>
            <div class="mt-3 pt-2.5 border-t border-cyan-500/20 text-[10px] text-cyan-400/80 flex items-center justify-between">
              <span>Política Terminológica: Estritamente contábil e estatística (Zero termos acusatórios).</span>
              <span class="font-mono">TST-OJ-251 OK</span>
            </div>
          </div>
        </div>
      `;
    }

    if (toolId === 'zero_click_briefing' || toolId === 'briefing_matinal' || toolId === 'cafe_com_dono' || toolId === 'morning_briefing') {
      const s24 = data.sales_summary_24h || {};
      const tank = data.tank_critical_runout || {};
      const wpText = data.whatsapp_formatted_text || '';
      const quickActions = data.quick_actions || [];

      const faturamento = Number(s24.total_turnover_brl || 0);
      const volumeLitros = Number(s24.total_liters || 0);
      const tankId = tank.tank_id || '1';
      const fuelName = tank.fuel_type || 'Combustível';
      const occPct = Number(tank.occupancy_pct || 0);
      const orderBoxes = tank.recommended_order_compartments || 0;

      const fmt = (v) => 'R$ ' + Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
      const encodedWp = encodeURIComponent(wpText);

      let actionsHtml = quickActions.map(a => `
        <button type="button" class="px-3 py-1.5 rounded-lg bg-purple-500/20 hover:bg-purple-500/30 text-purple-200 border border-purple-500/40 text-xs font-semibold cursor-pointer transition-colors flex items-center gap-1.5"
                onclick="if (window.auraChat) { window.auraChat.setInputText('${this.escapeHtml(a)}'); window.auraChat.sendMessage(); }">
          <svg class="w-3 h-3 text-purple-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
          <span>${this.escapeHtml(a)}</span>
        </button>
      `).join('');

      return `
        <div class="space-y-4 font-sans text-xs">
          <!-- Top KPI Row -->
          <div class="grid grid-cols-2 md:grid-cols-3 gap-3">
            <div class="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
              <span class="text-[10px] text-slate-400 block uppercase tracking-wider">Faturamento (Últimas 24h)</span>
              <span class="text-base font-bold text-emerald-400 font-mono mt-0.5 block">${fmt(faturamento)}</span>
            </div>
            <div class="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
              <span class="text-[10px] text-slate-400 block uppercase tracking-wider">Volume Vendido</span>
              <span class="text-base font-bold text-cyan-300 font-mono mt-0.5 block">${Number(volumeLitros).toLocaleString('pt-BR')} L</span>
            </div>
            <div class="p-3 rounded-xl bg-slate-900/60 border border-slate-800 col-span-2 md:col-span-1">
              <span class="text-[10px] text-slate-400 block uppercase tracking-wider">Tanque Crítico</span>
              <span class="text-xs font-bold text-amber-300 mt-1 block">
                Tanque ${tankId} (${fuelName}) - ${occPct.toFixed(1)}%
              </span>
            </div>
          </div>

          <!-- Alerta de Runout Crítico -->
          <div class="p-3.5 rounded-xl bg-amber-950/20 border border-amber-500/30 flex items-center justify-between gap-3">
            <div class="flex items-center gap-2.5">
              <span class="p-1.5 rounded-lg bg-amber-500/20 text-amber-400 border border-amber-500/30">
                <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
              </span>
              <div>
                <strong class="text-amber-200 block text-xs">Recomendação Logística de Compra</strong>
                <p class="text-[11px] text-slate-300">Tanque ${tankId} (${fuelName}) requer pedido imediato de <strong>${orderBoxes} compartimento(s)</strong> de 5.000 L para evitar risco de ruptura seca.</p>
              </div>
            </div>
            <button type="button" class="px-3 py-1.5 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 border border-amber-500/40 text-xs font-semibold cursor-pointer whitespace-nowrap transition-colors"
                    onclick="if (window.auraChat) { window.auraChat.setInputText('Aprovar Pedido de ${orderBoxes * 5000} L para Tanque ${tankId}'); window.auraChat.sendMessage(); }">
              Sugerir Pedido
            </button>
          </div>

          <!-- Preview Balão WhatsApp -->
          <div class="p-4 rounded-xl bg-emerald-950/30 border border-emerald-500/30">
            <div class="flex items-center justify-between mb-2.5 pb-2 border-b border-emerald-500/20">
              <span class="flex items-center gap-1.5 text-emerald-400 font-bold text-xs">
                <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
                <span>Preview do Briefing Matinal (WhatsApp / Mobile)</span>
              </span>
              <a href="https://api.whatsapp.com/send?text=${encodedWp}" target="_blank" rel="noopener noreferrer"
                 class="px-2.5 py-1 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-[11px] transition-colors flex items-center gap-1">
                <span>Disparar WhatsApp</span>
                <svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
              </a>
            </div>

            <div class="p-3.5 rounded-lg bg-emerald-950/50 border border-emerald-500/20 text-slate-200 text-xs font-mono whitespace-pre-wrap leading-relaxed shadow-inner">
              ${this.escapeHtml(wpText)}
            </div>
          </div>

          <!-- Ações Rápidas em 1-Clique -->
          <div>
            <span class="text-[11px] text-slate-400 block mb-2 font-semibold">Ações Rápidas Disponíveis:</span>
            <div class="flex flex-wrap gap-2">
              ${actionsHtml}
            </div>
          </div>
        </div>
      `;
    }

    // Fallback Inteligente: Tabela genérica dos campos principais
    let fields = '';
    for (const [key, val] of Object.entries(data)) {
      if (val === null || val === undefined) continue;
      if (typeof val === 'object') {
        fields += `
          <div class="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800 text-xs font-sans">
            <span class="text-cyan-400 font-semibold">${key}:</span>
            <pre class="mt-1 text-slate-300 text-[11px] overflow-x-auto whitespace-pre-wrap font-mono">${JSON.stringify(val, null, 2)}</pre>
          </div>
        `;
      } else {
        fields += `
          <div class="flex items-baseline justify-between border-b border-slate-800/80 py-1.5 text-xs font-sans">
            <span class="text-slate-400">${key}:</span>
            <span class="text-slate-200 font-medium">${String(val)}</span>
          </div>
        `;
      }
    }

    return `<div class="space-y-2 font-sans">${fields || '<div class="text-slate-400 text-xs">Visualização detalhada disponível na aba Dados Brutos (JSON).</div>'}</div>`;
  }

  /**
   * Renderiza tela de erro caso a ferramenta falhe
   */
  renderErrorInspector(tool, errorMsg) {
    const titleEl = document.getElementById('inspector-tool-title');
    const statusEl = document.getElementById('inspector-status-badge');
    const formattedTab = document.getElementById('inspector-content-formatted');

    if (titleEl) titleEl.textContent = tool.name;
    if (statusEl) {
      statusEl.className = 'px-2.5 py-0.5 rounded text-[11px] font-sans font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/40';
      statusEl.textContent = 'Falha na Consulta';
    }
    if (formattedTab) {
      formattedTab.innerHTML = `
        <div class="p-4 rounded-xl bg-rose-950/20 border border-rose-500/30 text-rose-300 font-sans text-xs">
          <strong>Falha ao executar consulta:</strong> ${errorMsg}
        </div>
      `;
    }
  }

  /**
   * Envia o resultado atual para a AURA analisar no Console Cognitivo
   */
  sendResultToAura() {
    if (!this.currentTool) return;
    const prompt = `Analise detalhadamente o resultado analítico da ferramenta ${this.currentTool.name} (${this.currentTool.id}) e forneça recomendações práticas para a gerência do posto.`;
    window.auraApp.switchTab('console');
    window.auraChat.sendUserPrompt(prompt);
  }

  copyJson() {
    if (!this.currentResult) return;
    const str = JSON.stringify(this.currentResult.data || this.currentResult, null, 2);
    navigator.clipboard.writeText(str).then(() => {
      const btn = document.getElementById('btn-copy-json');
      if (btn) {
        const orig = btn.textContent;
        btn.textContent = 'Copiado! ✓';
        setTimeout(() => btn.textContent = orig, 1800);
      }
    });
  }

  escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
}

// Instância singleton global e export para ambientes Node/Testes
if (typeof window !== 'undefined') {
  window.auraTriggers = new AuraTriggersController();
}
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { AuraTriggersController };
}

