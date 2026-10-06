/**
 * AURA Gatilhos Analíticos em 1-Clique Controller
 * Gerencia a matriz de 11 ferramentas especializadas para execução direta em sub-100ms.
 */

class AuraTriggersController {
  constructor() {
    this.currentTool = null;
    this.currentResult = null;
    this.activeFilter = 'todos';
  }

  /**
   * Catálogo das 11 ferramentas analíticas
   */
  getToolsCatalog() {
    return [
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
        desc: 'Triangulação entre automação CBC04 Companytec, vendas PDV e balanço volumétrico de tanques.',
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
        name: 'Cesta de Compras & Cross-Selling',
        category: 'loja',
        icon: 'shopping-cart',
        color: 'purple',
        badge: 'Inteligência PDV',
        desc: 'Regras de associação Apriori de alta frequência com Lift, Confiança e scripts práticos para sugestão no caixa.',
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
        badge: 'RAG Híbrido',
        desc: 'Recuperação vetorial HNSW + lexical GIN FTS com Reciprocal Rank Fusion (RRF) de produtos e combustíveis.',
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
              <span class="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-semibold border ${tagBg}">
                ${tool.badge}
              </span>
              <span class="text-[11px] text-slate-400 font-mono group-hover:text-cyan-300 transition-colors flex items-center gap-1">
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

          <div class="mt-4 pt-3 border-t border-white/5 flex items-center justify-between font-mono text-[11px] text-slate-500">
            <span class="text-slate-400">alias: ${tool.id}</span>
            <span class="text-cyan-400 font-semibold group-hover:text-cyan-300 flex items-center gap-1.5">
              <span>Disparar</span>
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
    const catalog = this.getToolsCatalog();
    const tool = catalog.find(t => t.id === toolId) || { id: toolId, name: toolId };
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

    if (titleEl) titleEl.textContent = tool.name;
    if (statusEl) {
      statusEl.className = 'px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40';
      statusEl.textContent = '✓ 200 OK SUCCESS';
    }
    if (latencyEl) {
      latencyEl.innerHTML = `<span class="inline-flex items-center gap-1.5"><svg class="w-3.5 h-3.5 text-cyan-400" viewBox="0 0 24 24" fill="none" stroke="currentColor"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg> <span>Latência: ${response.clientLatencyMs || response.latency_ms || 25} ms</span></span>`;
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
    if (!data) return '<div class="text-slate-400">Nenhum dado retornado.</div>';

    // 1. Run-Out de Tanques
    if (toolId === 'run_out' && data.detalhamento_tanques) {
      let rows = '';
      data.detalhamento_tanques.forEach(t => {
        rows += `
          <tr class="border-b border-white/5 text-xs font-mono hover:bg-white/[0.02] transition-colors">
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
        <div class="space-y-4">
          <div class="p-3.5 rounded-xl glass-subcard border border-white/5 font-mono text-xs text-slate-300">
            <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div>Tanques Ativos: <strong class="text-emerald-400 tabular-nums">${totalAtivos}</strong></div>
              <div>Nível Crítico (&lt;15%): <strong class="${emRisco > 0 ? 'text-rose-400' : 'text-slate-400'} tabular-nums">${emRisco}</strong></div>
              <div>Saldo Total: <strong class="text-slate-100 tabular-nums">${saldoTot.toLocaleString('pt-BR')} L</strong></div>
              <div>Ullage Total: <strong class="text-cyan-300 tabular-nums">${ullageTot.toLocaleString('pt-BR')} L</strong></div>
            </div>
          </div>

          <div class="overflow-x-auto">
            <table class="w-full text-left font-mono text-xs">
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
        <div class="space-y-4 font-mono text-xs">
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
        ? '—'
        : `${diffVal < 0 ? '-' : diffVal > 0 ? '+' : ''}R$ ${Math.abs(diffVal).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

      const autRevText = (isNoMovement || isUnavailable)
        ? '—'
        : `R$ ${autRev.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

      const posRevText = (isNoMovement || isUnavailable)
        ? '—'
        : `R$ ${posRev.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

      const badgeLabel = assessment.badge_label || r.status_conciliacao || (isPartial ? 'Análise parcial (provisória)' : (isNoMovement ? 'Sem movimentação' : 'Turno em Andamento'));
      const diagText = r.diagnostico_caixa || c.explanation?.text || 'Conferência de turno executada.';

      return `
        <div class="space-y-4 font-mono text-xs">
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
                ${isPartial ? 'Caixa Aberto' : (isNoMovement || isUnavailable ? '—' : `${Number(r.score_conformidade_pct || 100)}%`)}
              </div>
            </div>
          </div>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-3 p-3 rounded bg-slate-900 border border-slate-800">
            <div>Faturamento Pista CBC04: <strong class="text-slate-100 block mt-0.5 tabular-nums">${autRevText}</strong></div>
            <div>Faturamento Caixa PDV: <strong class="text-cyan-300 block mt-0.5 tabular-nums">${posRevText}</strong></div>
            <div>${isPartial ? 'Diferença Provisória:' : 'Diferença Caixa:'} <strong class="${isPartial ? 'text-amber-400' : 'text-emerald-400'} block mt-0.5 tabular-nums">${diffFormatted}</strong></div>
            <div>Diagnóstico: <span class="text-slate-400 block mt-0.5">${this.escapeHtml(diagText)}</span></div>
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
            <div class="p-3 rounded-xl glass-subcard border ${isLento ? 'border-amber-500/50 shadow-md shadow-amber-950/20 text-amber-300' : 'border-white/10 text-slate-300'} font-mono text-xs transition-all hover:-translate-y-0.5">
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
            <tr class="border-b border-white/5 text-xs font-mono hover:bg-white/[0.02] transition-colors">
              <td class="py-2.5 text-slate-400">${idx + 1}</td>
              <td class="py-2.5 font-semibold text-slate-200">${f.nome}</td>
              <td class="py-2.5 text-right tabular-nums">${Number(f.total_litros || 0).toFixed(1)} L</td>
              <td class="py-2.5 text-right text-emerald-400 font-bold tabular-nums">R$ ${Number(f.faturamento_reais || 0).toFixed(2)}</td>
              <td class="py-2.5 text-right text-cyan-300 tabular-nums">${Number(f.conversao_aditivada_pct || 0).toFixed(1)}%</td>
            </tr>
          `;
        });
      }

      return `
        <div class="space-y-4 font-mono text-xs">
          <div>
            <h4 class="font-bold text-slate-200 mb-2">Auditoria de Vazão dos Bicos:</h4>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-2.5">${bicosList || '<div class="text-slate-500">Sem dados de bicos</div>'}</div>
          </div>
          <div>
            <h4 class="font-bold text-slate-200 mb-2">Ranking de Frentistas:</h4>
            <div class="overflow-x-auto">
              <table class="w-full text-left font-mono text-xs">
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
            <tr class="border-b border-white/5 text-xs font-mono hover:bg-white/[0.02] transition-colors">
              <td class="py-2 text-slate-200">${p.nompro || p.descricao || p.codpro}</td>
              <td class="py-2 text-right text-slate-300 tabular-nums">${Number(p.quantidade || p.quant || 0).toFixed(1)}</td>
              <td class="py-2 text-right text-emerald-400 font-semibold tabular-nums">R$ ${Number(p.valor_total || p.total || 0).toFixed(2)}</td>
            </tr>
          `;
        });
      }
      return `
        <div class="space-y-4 font-mono text-xs">
          <div class="grid grid-cols-2 md:grid-cols-3 gap-3 p-3.5 rounded-xl glass-subcard border border-white/5">
            <div>Status: <strong class="text-emerald-400">${data.status || 'OK'}</strong></div>
            <div>Destaque Hoje: <strong class="text-cyan-300">${data.ultimo_produto_vendido_destaque?.nompro || 'Registrado'}</strong></div>
            <div>Total Geral: <strong class="text-purple-300 tabular-nums">R$ ${Number(data.resumo_geral?.faturamento_total || 0).toFixed(2)}</strong></div>
          </div>
          <div>
            <h4 class="font-bold text-slate-200 mb-2">Top Produtos Mais Vendidos:</h4>
            <div class="overflow-x-auto">
              <table class="w-full text-left font-mono text-xs">
                <thead>
                  <tr class="text-slate-400 border-b border-white/10">
                    <th class="pb-2">Produto</th>
                    <th class="pb-2 text-right">Qtd</th>
                    <th class="pb-2 text-right">Faturamento</th>
                  </tr>
                </thead>
                <tbody>${topProds || '<tr><td colspan="3" class="py-2 text-slate-500">Sem itens</td></tr>'}</tbody>
              </table>
            </div>
          </div>
        </div>
      `;
    }

    // 6. Conveniência e Cross-Selling (Market Basket)
    if (toolId === 'conveniencia_vendas_cruzadas' && data.top_combos_cross_selling) {
      let cards = '';
      data.top_combos_cross_selling.forEach(c => {
        cards += `
          <div class="p-3.5 rounded-xl glass-subcard border border-purple-500/30 flex flex-col justify-between font-mono text-xs hover:-translate-y-0.5 transition-all">
            <div class="flex items-center justify-between text-[11px] mb-1.5 pb-1 border-b border-white/5">
              <span class="text-purple-300 font-bold tabular-nums">LIFT: ${c.metricas?.lift?.toFixed(1)}x</span>
              <span class="text-slate-400 tabular-nums">Confiança: ${(c.metricas?.confianca * 100).toFixed(0)}%</span>
            </div>
            <div class="text-slate-100 font-semibold">${c.produto_origem?.nompro}</div>
            <div class="text-emerald-400 text-xs mt-1">↳ + ${c.produto_recomendado?.nompro}</div>
            <div class="text-[11px] text-slate-300 mt-2.5 pt-2 border-t border-purple-900/30">
              "${c.script_sugerido_caixa}"
            </div>
          </div>
        `;
      });
      return `<div class="grid grid-cols-1 md:grid-cols-2 gap-3">${cards}</div>`;
    }

    // 7. Posição Geral de Estoque ERP
    if (toolId === 'estoque_posicao') {
      let estRows = '';
      if (data.maiores_estoques) {
        data.maiores_estoques.slice(0, 10).forEach(e => {
          estRows += `
            <tr class="border-b border-white/5 text-xs font-mono hover:bg-white/[0.02] transition-colors">
              <td class="py-2 text-slate-400">${e.codpro}</td>
              <td class="py-2 text-slate-200 font-semibold">${e.nompro}</td>
              <td class="py-2 text-right text-cyan-300 tabular-nums">${Number(e.estoque || 0).toFixed(1)} ${e.unidade || 'UN'}</td>
              <td class="py-2 text-right text-emerald-400 tabular-nums">R$ ${Number(e.precovenda || 0).toFixed(2)}</td>
            </tr>
          `;
        });
      }
      return `
        <div class="space-y-4 font-mono text-xs">
          <div class="p-3.5 rounded-xl glass-subcard border border-white/5 flex items-center justify-between">
            <span class="text-slate-400">Status do Estoque ERP:</span> <strong class="text-emerald-400">${data.status || 'ONLINE'}</strong>
          </div>
          <div>
            <h4 class="font-bold text-slate-200 mb-2">Maiores Posições de Estoque Cadastradas:</h4>
            <div class="overflow-x-auto">
              <table class="w-full text-left font-mono text-xs">
                <thead>
                  <tr class="text-slate-400 border-b border-white/10">
                    <th class="pb-2">SKU</th>
                    <th class="pb-2">Produto</th>
                    <th class="pb-2 text-right">Saldo</th>
                    <th class="pb-2 text-right">Preço Venda</th>
                  </tr>
                </thead>
                <tbody>${estRows || '<tr><td colspan="4" class="py-2 text-slate-500">Nenhum estoque</td></tr>'}</tbody>
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
            <tr class="border-b border-white/5 text-xs font-mono hover:bg-white/[0.02] transition-colors">
              <td class="py-2.5 text-slate-400">${idx + 1}</td>
              <td class="py-2.5 text-slate-200 font-semibold">${c.nome || c.cliente || 'Consumidor'}</td>
              <td class="py-2.5 text-right text-cyan-300 tabular-nums">${c.total_pedidos || 1} compras</td>
              <td class="py-2.5 text-right text-emerald-400 font-bold tabular-nums">R$ ${Number(c.total_gasto || c.faturamento || 0).toFixed(2)}</td>
            </tr>
          `;
        });
      }
      return `
        <div class="space-y-4 font-mono text-xs">
          <div class="grid grid-cols-2 gap-3 p-3.5 rounded-xl glass-subcard border border-white/5">
            <div>Clientes Cadastrados: <strong class="text-cyan-300 tabular-nums">${data.total_clientes_cadastrados || 'N/A'}</strong></div>
            <div>Observação PDV: <span class="text-slate-300">${data.observacao_pdv || 'Normal'}</span></div>
          </div>
          <div>
            <h4 class="font-bold text-slate-200 mb-2">Principais Clientes & Frotas:</h4>
            <div class="overflow-x-auto">
              <table class="w-full text-left font-mono text-xs">
                <thead>
                  <tr class="text-slate-400 border-b border-white/10">
                    <th class="pb-2.5">#</th>
                    <th class="pb-2.5">Cliente</th>
                    <th class="pb-2.5 text-right">Frequência</th>
                    <th class="pb-2.5 text-right">Faturamento</th>
                  </tr>
                </thead>
                <tbody>${cliRows || '<tr><td colspan="4" class="py-2 text-slate-500">Sem clientes</td></tr>'}</tbody>
              </table>
            </div>
          </div>
        </div>
      `;
    }

    // 9. Dados Cadastrais da Filial
    if (toolId === 'dados_filial') {
      return `
        <div class="space-y-3 font-mono text-xs p-4 rounded-xl glass-subcard border border-white/5">
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

    // 11. Busca no Catálogo de Produtos
    if (toolId === 'catalogo_produtos') {
      const results = data.resultados || data.produtos || [];
      let prodCards = '';
      results.forEach(p => {
        prodCards += `
          <div class="p-3 rounded-xl glass-subcard border border-purple-500/30 font-mono text-xs hover:-translate-y-0.5 transition-all">
            <div class="flex items-center justify-between text-[11px] text-slate-400">
              <span class="tabular-nums">SKU: ${p.codpro || p.codigo}</span>
              ${p.score ? `<span class="text-purple-300 font-bold tabular-nums">Score: ${(p.score * 100).toFixed(0)}%</span>` : ''}
            </div>
            <div class="font-bold text-slate-100 mt-1">${p.nompro || p.nome}</div>
            <div class="flex items-center justify-between mt-2.5 pt-1.5 border-t border-white/5 text-emerald-400 font-semibold">
              <span>Preço: <strong class="tabular-nums">R$ ${Number(p.precovenda || p.preco || 0).toFixed(2)}</strong></span>
              <span class="text-slate-400 text-[10px]">${p.grupo || 'GERAL'}</span>
            </div>
          </div>
        `;
      });
      return `
        <div class="space-y-3 font-mono text-xs">
          <div class="flex items-center justify-between p-3 rounded-xl glass-subcard border border-white/5">
            <span>Método de Busca: <strong class="text-purple-300">${data.metodo || 'Híbrido (HNSW + FTS)'}</strong></span>
            <span>Resultados: <strong class="text-cyan-300 tabular-nums">${results.length}</strong></span>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5">${prodCards || '<div class="text-slate-500">Nenhum produto encontrado.</div>'}</div>
        </div>
      `;
    }

    // Fallback Inteligente: Tabela genérica dos campos principais
    let fields = '';
    for (const [key, val] of Object.entries(data)) {
      if (val === null || val === undefined) continue;
      if (typeof val === 'object') {
        fields += `
          <div class="p-2 rounded bg-slate-900/60 border border-slate-800 text-xs font-mono">
            <span class="text-cyan-400 font-bold">${key}:</span>
            <pre class="mt-1 text-slate-300 text-[11px] overflow-x-auto whitespace-pre-wrap">${JSON.stringify(val, null, 2)}</pre>
          </div>
        `;
      } else {
        fields += `
          <div class="flex items-baseline justify-between border-b border-slate-800/80 py-1.5 text-xs font-mono">
            <span class="text-slate-400">${key}:</span>
            <span class="text-slate-200 font-semibold">${String(val)}</span>
          </div>
        `;
      }
    }

    return `<div class="space-y-2">${fields || '<div class="text-slate-400 text-xs">Visualização detalhada disponível na aba Payload JSON.</div>'}</div>`;
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
      statusEl.className = 'px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-rose-500/20 text-rose-300 border border-rose-500/40';
      statusEl.textContent = 'ERRO 400';
    }
    if (formattedTab) {
      formattedTab.innerHTML = `
        <div class="p-4 rounded-lg bg-rose-950/20 border border-rose-500/30 text-rose-300 font-mono text-xs">
          <strong>Falha ao executar ferramenta:</strong> ${errorMsg}
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

// Instância singleton global
window.auraTriggers = new AuraTriggersController();
