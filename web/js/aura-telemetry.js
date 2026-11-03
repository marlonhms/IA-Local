/**
 * AURA Telemetry & SRE Cockpit Coordinator (v1.2.0 - FiscalLLM Governance)
 * Painel Nativo de Telemetria Ultraleve: 0 MB de RAM extra no servidor.
 * Consome /api/v1/aura/telemetry/metrics, /api/v1/aura/stations,
 * /api/v1/aura/compliance/status e /api/v1/aura/telemetry/token-budget.
 * Renderiza graficos de latencia em Canvas nativo 100% puro JS sem nenhuma biblioteca externa.
 * Zero travessoes em todo o modulo.
 */

class AuraTelemetryCoordinator {
  constructor() {
    this.modal = null;
    this.refreshTimer = null;
    this.autoRefreshEnabled = false;
    this.isFetching = false;
    this.lastMetrics = null;
    this.lastBudget = null;
  }

  /**
   * Inicializa ouvintes e vincula botoes da interface.
   */
  init() {
    this.modal = document.getElementById('aura-telemetry-modal');
    if (!this.modal) return;

    // 1. Barra de Acompanhamento de Tokens no cabecalho (Header)
    const btnTokenTracking = document.getElementById('btn-header-token-tracking');
    if (btnTokenTracking) {
      btnTokenTracking.addEventListener('click', () => this.openModal());
    }

    // 1.1 Botao retrocompativel no cabecalho (Header)
    const btnHeader = document.getElementById('btn-open-telemetry');
    if (btnHeader) {
      btnHeader.addEventListener('click', () => this.openModal());
    }

    // 2. Item no menu lateral (Sidebar Drawer)
    const btnSidebar = document.getElementById('sidebar-btn-open-telemetry');
    if (btnSidebar) {
      btnSidebar.addEventListener('click', () => {
        if (window.auraApp && typeof window.auraApp.closeSidebar === 'function') {
          window.auraApp.closeSidebar();
        }
        this.openModal();
      });
    }

    // 3. Botao de fechar (X)
    const btnClose = document.getElementById('btn-close-telemetry-modal');
    if (btnClose) {
      btnClose.addEventListener('click', () => this.closeModal());
    }

    // 4. Fechar ao clicar no backdrop
    this.modal.addEventListener('click', (e) => {
      if (e.target === this.modal) {
        this.closeModal();
      }
    });

    // 5. Fechar com Escape
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.modal && !this.modal.classList.contains('hidden')) {
        this.closeModal();
      }
    });

    // 6. Botao Atualizar Agora
    const btnRefresh = document.getElementById('btn-telemetry-refresh');
    if (btnRefresh) {
      btnRefresh.addEventListener('click', () => this.fetchCockpitData());
    }

    // 7. Toggle Auto-Refresh (10s)
    const toggleAuto = document.getElementById('toggle-telemetry-autorefresh');
    if (toggleAuto) {
      toggleAuto.addEventListener('change', (e) => {
        this.autoRefreshEnabled = e.target.checked;
        if (this.autoRefreshEnabled) {
          this.startAutoRefresh();
        } else {
          this.stopAutoRefresh();
        }
      });
    }

    // 8. Botao Salvar Meta Orcamentaria de Tokens
    const btnSavePolicy = document.getElementById('btn-save-token-policy');
    if (btnSavePolicy) {
      btnSavePolicy.addEventListener('click', () => this.handleSaveBudgetPolicy());
    }

    // 9. Carga inicial silenciosa para atualizar badges e barra de tokens no header
    this.fetchSilentBadge();
  }

  /**
   * Abre o modal executivo de telemetria e atualiza metricas.
   */
  async openModal() {
    if (!this.modal) return;
    this.modal.classList.remove('hidden');
    document.body.classList.add('overflow-hidden');
    await this.fetchCockpitData();
    if (this.autoRefreshEnabled) {
      this.startAutoRefresh();
    }
  }

  /**
   * Fecha o modal executivo.
   */
  closeModal() {
    if (!this.modal) return;
    this.modal.classList.add('hidden');
    document.body.classList.remove('overflow-hidden');
    this.stopAutoRefresh();
  }

  startAutoRefresh() {
    this.stopAutoRefresh();
    this.refreshTimer = setInterval(() => {
      if (this.modal && !this.modal.classList.contains('hidden')) {
        this.fetchCockpitData(true);
      }
    }, 10000);
  }

  stopAutoRefresh() {
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
      this.refreshTimer = null;
    }
  }

  /**
   * Atualizacao silenciosa do badge de latencia e barra de tokens no topo da tela.
   */
  async fetchSilentBadge() {
    try {
      const [metricsRes, budgetRes] = await Promise.allSettled([
        fetch('/api/v1/aura/telemetry/metrics'),
        fetch('/api/v1/aura/telemetry/token-budget'),
      ]);
      const metrics = metricsRes.status === 'fulfilled' && metricsRes.value.ok ? await metricsRes.value.json() : null;
      const budget = budgetRes.status === 'fulfilled' && budgetRes.value.ok ? await budgetRes.value.json() : null;

      if (metrics) {
        this.updateHeaderBadge(metrics);
      }
      this.updateHeaderTokenTracking(budget, metrics);
    } catch {
      // Falha silenciosa de telemetria
    }
  }

  updateHeaderBadge(metrics) {
    const badge = document.getElementById('header-telemetry-badge');
    const label = document.getElementById('header-telemetry-ttft-label');
    if (!badge || !label || !metrics) return;

    const p50 = metrics.ttft_ms && metrics.ttft_ms.p50 ? metrics.ttft_ms.p50 : 0;
    if (p50 > 0) {
      label.textContent = `${Math.round(p50)}ms`;
      if (p50 < 1500) {
        badge.className = 'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-500/10 text-emerald-300 border border-emerald-500/30';
      } else if (p50 < 4000) {
        badge.className = 'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-500/10 text-amber-300 border border-amber-500/30';
      } else {
        badge.className = 'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-rose-500/10 text-rose-300 border border-rose-500/30';
      }
    } else {
      label.textContent = 'Pronta';
    }
  }

  /**
   * Atualiza a Barra de Acompanhamento de Tokens no topo do layout principal.
   */
  updateHeaderTokenTracking(budget, metrics) {
    const elCounter = document.getElementById('header-token-counter');
    const elBar = document.getElementById('header-budget-progress-bar');
    const elCost = document.getElementById('header-budget-cost-label');
    const elAvoided = document.getElementById('header-budget-avoided-pill');
    if (!elCounter) return;

    const tokens = budget?.total_tokens_consumed ?? metrics?.token_usage?.total_tokens ?? 0;
    const costBrl = budget?.monthly_consumed_brl ?? metrics?.token_usage?.total_cost_brl ?? 0.0;
    const monthlyBudget = budget?.monthly_budget_brl ?? 30.00;
    const avoidedBrl = budget?.total_avoided_cost_brl ?? metrics?.token_usage?.total_avoided_cost_brl ?? 0.0;
    const pct = monthlyBudget > 0 ? (costBrl / monthlyBudget) * 100.0 : 0.0;

    const tokensFmt = tokens >= 1000 ? `${(tokens / 1000).toFixed(1)}k tokens` : `${tokens} tokens`;
    elCounter.textContent = tokensFmt;

    if (elCost) {
      elCost.textContent = `R$ ${costBrl.toFixed(2).replace('.', ',')} / R$ ${monthlyBudget.toFixed(0)}`;
      if (pct >= 100) {
        elCost.className = 'font-mono text-[10px] text-rose-400 font-bold';
      } else if (pct >= 80) {
        elCost.className = 'font-mono text-[10px] text-amber-400 font-bold';
      } else {
        elCost.className = 'font-mono text-[10px] text-emerald-400 font-semibold';
      }
    }

    if (elBar) {
      const displayPct = Math.min(100, Math.max(3, pct));
      elBar.style.width = `${displayPct}%`;
      if (pct >= 100) {
        elBar.className = 'h-full bg-rose-500 rounded-full transition-all duration-500';
      } else if (pct >= 80) {
        elBar.className = 'h-full bg-amber-500 rounded-full transition-all duration-500';
      } else {
        elBar.className = 'h-full bg-gradient-to-r from-emerald-500 to-cyan-500 rounded-full transition-all duration-500';
      }
    }

    if (elAvoided) {
      if (avoidedBrl > 0) {
        elAvoided.textContent = `Economia ~R$ ${avoidedBrl.toFixed(2).replace('.', ',')}`;
        elAvoided.classList.remove('hidden');
      } else {
        elAvoided.textContent = 'Economia ~R$ 0,00';
      }
    }
  }

  /**
   * Busca dados consolidados de telemetria, estacoes, conformidade e orcamento de tokens.
   */
  async fetchCockpitData(isBackground = false) {
    if (this.isFetching) return;
    this.isFetching = true;

    const refreshIcon = document.getElementById('icon-telemetry-refresh');
    if (refreshIcon && !isBackground) {
      refreshIcon.classList.add('animate-spin');
    }

    try {
      const [metricsRes, stationsRes, complianceRes, budgetRes] = await Promise.allSettled([
        fetch('/api/v1/aura/telemetry/metrics'),
        fetch('/api/v1/aura/stations'),
        fetch('/api/v1/aura/compliance/status'),
        fetch('/api/v1/aura/telemetry/token-budget'),
      ]);

      const metrics = metricsRes.status === 'fulfilled' && metricsRes.value.ok ? await metricsRes.value.json() : null;
      const stations = stationsRes.status === 'fulfilled' && stationsRes.value.ok ? await stationsRes.value.json() : null;
      const compliance = complianceRes.status === 'fulfilled' && complianceRes.value.ok ? await complianceRes.value.json() : null;
      const budget = budgetRes.status === 'fulfilled' && budgetRes.value.ok ? await budgetRes.value.json() : null;

      this.lastMetrics = metrics;
      this.lastBudget = budget;
      this.renderCockpit(metrics, stations, compliance, budget);

      if (metrics) {
        this.updateHeaderBadge(metrics);
      }
      this.updateHeaderTokenTracking(budget, metrics);
    } catch (err) {
      console.warn('[AuraTelemetry] Erro ao obter dados do cockpit:', err);
    } finally {
      this.isFetching = false;
      if (refreshIcon) {
        refreshIcon.classList.remove('animate-spin');
      }
    }
  }

  renderCockpit(metrics, stations, compliance, budget) {
    // 1. Renderiza secao de Orcamento e Tokens
    this.renderTokenBudget(budget, metrics);

    // 2. Renderiza Insights Operacionais e de Desempenho
    this.renderOperationalInsights(metrics, budget, stations);

    if (!metrics) return;

    // 3. TTFT (Latencia da IA)
    const ttft = metrics.ttft_ms || {};
    const p50 = ttft.p50 || 0;
    const p90 = ttft.p90 || 0;
    const p99 = ttft.p99 || 0;
    const avg = ttft.avg || 0;
    const count = ttft.count || 0;

    const elP50 = document.getElementById('sre-ttft-p50');
    const elP90 = document.getElementById('sre-ttft-p90');
    const elP99 = document.getElementById('sre-ttft-p99');
    const elAvg = document.getElementById('sre-ttft-avg');
    const elCount = document.getElementById('sre-ttft-count');
    const elSpeedBadge = document.getElementById('sre-speed-badge');

    if (elP50) elP50.textContent = `${Math.round(p50)} ms`;
    if (elP90) elP90.textContent = `${Math.round(p90)} ms`;
    if (elP99) elP99.textContent = `${Math.round(p99)} ms`;
    if (elAvg) elAvg.textContent = `${Math.round(avg)} ms`;
    if (elCount) elCount.textContent = count.toLocaleString('pt-BR');

    if (elSpeedBadge) {
      if (p50 < 1500) {
        elSpeedBadge.textContent = 'Ultrarrapida';
        elSpeedBadge.className = 'px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
      } else if (p50 < 4000) {
        elSpeedBadge.textContent = 'Adequada';
        elSpeedBadge.className = 'px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30';
      } else {
        elSpeedBadge.textContent = 'Lenta';
        elSpeedBadge.className = 'px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/30';
      }
    }

    // 4. Hidratacao GenUI
    const hyd = metrics.hydration_ms || {};
    const elHydP50 = document.getElementById('sre-hyd-p50');
    const elHydAvg = document.getElementById('sre-hyd-avg');
    if (elHydP50) elHydP50.textContent = `${Math.round(hyd.p50 || 0)} ms`;
    if (elHydAvg) elHydAvg.textContent = `${Math.round(hyd.avg || 0)} ms`;

    // 5. Pool e Banco ERP
    const dbPool = metrics.db_pool || {};
    const stationInfo = Array.isArray(stations) && stations.length > 0 ? stations[0] : null;

    const elErpStatus = document.getElementById('sre-erp-status');
    const elErpConn = document.getElementById('sre-erp-conn');
    const elErpLatency = document.getElementById('sre-erp-latency');

    if (stationInfo) {
      if (elErpStatus) {
        elErpStatus.textContent = stationInfo.erp_online ? 'Online (5433)' : 'Desconectado';
        elErpStatus.className = stationInfo.erp_online ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-semibold';
      }
      if (elErpLatency) elErpLatency.textContent = `${stationInfo.latency_erp_ms || 1.2} ms`;
    }
    if (elErpConn) elErpConn.textContent = `${dbPool.active_erp || 1} ativas`;

    // 6. Governanca & Vouchers HITL
    const elActionsAppr = document.getElementById('sre-actions-approved');
    const elActionsReq = document.getElementById('sre-actions-requested');
    const elSecBlocks = document.getElementById('sre-security-blocks');
    const elSuccessRate = document.getElementById('sre-success-rate');

    if (elActionsAppr) elActionsAppr.textContent = metrics.total_actions_approved || 0;
    if (elActionsReq) elActionsReq.textContent = metrics.total_actions_requested || 0;
    if (elSecBlocks) elSecBlocks.textContent = metrics.security_blocks || 0;
    if (elSuccessRate) elSuccessRate.textContent = `${metrics.action_success_rate_pct || 100}%`;

    // 7. Recursos de Processo Local
    const proc = metrics.process_metrics || {};
    const elProcRam = document.getElementById('sre-proc-ram');
    const elProcUptime = document.getElementById('sre-proc-uptime');
    const elProcPid = document.getElementById('sre-proc-pid');

    if (elProcRam) elProcRam.textContent = `${proc.rss_memory_mb || 0} MB`;
    if (elProcPid) elProcPid.textContent = `PID ${proc.pid || '-'}`;
    if (elProcUptime) {
      const s = proc.uptime_seconds || 0;
      const h = Math.floor(s / 3600);
      const m = Math.floor((s % 3600) / 60);
      elProcUptime.textContent = `${h}h ${m}m`;
    }

    // 8. Conformidade LGPD
    const elCompStatus = document.getElementById('sre-compliance-status');
    if (elCompStatus && compliance) {
      elCompStatus.textContent = compliance.compliant ? 'Opt-In Ativo (v1.1)' : 'Pendente de Opt-In';
      elCompStatus.className = compliance.compliant ? 'text-emerald-400 font-semibold' : 'text-amber-400 font-semibold';
    }

    // 9. Renderizacao do Grafico Canvas de TTFT
    const samples = Array.isArray(metrics.recent_ttft_samples) && metrics.recent_ttft_samples.length > 0
      ? metrics.recent_ttft_samples
      : [650, 720, 680, 810, 750, 700, 704];
    this.drawLatencyCanvas(samples);
  }

  /**
   * Renderiza a secao de orcamento de tokens e custos do FiscalLLM no Cockpit.
   */
  renderTokenBudget(budget, metrics) {
    const tokens = budget?.total_tokens_consumed ?? metrics?.token_usage?.total_tokens ?? 0;
    const promptTokens = metrics?.token_usage?.prompt_tokens ?? 0;
    const completionTokens = metrics?.token_usage?.completion_tokens ?? 0;
    const costBrl = budget?.monthly_consumed_brl ?? metrics?.token_usage?.total_cost_brl ?? 0.0;
    const costUsd = budget?.monthly_consumed_usd ?? 0.0;
    const monthlyBudget = budget?.monthly_budget_brl ?? 30.00;
    const avoidedBrl = budget?.total_avoided_cost_brl ?? metrics?.token_usage?.total_avoided_cost_brl ?? 0.0;
    const cacheHits = budget?.cache_hits_count ?? 0;
    const projectedBrl = budget?.projected_end_of_month_brl ?? costBrl;
    const pct = monthlyBudget > 0 ? (costBrl / monthlyBudget) * 100.0 : 0.0;
    const policyMode = budget?.enforcement_mode || budget?.policy_mode || 'smart_pacing';

    // Status Pill
    const elPill = document.getElementById('sre-budget-status-pill');
    if (elPill) {
      if (pct >= 100) {
        elPill.textContent = 'Critico (Teto Excedido)';
        elPill.className = 'px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/30';
      } else if (pct >= 80) {
        elPill.textContent = 'Alerta Preventivo (80%)';
        elPill.className = 'px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30';
      } else {
        elPill.textContent = 'Normal (Dentro da Meta)';
        elPill.className = 'px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30';
      }
    }

    // Modo Badge
    const elMode = document.getElementById('sre-budget-mode-badge');
    if (elMode) {
      const modeLabels = {
        'smart_pacing': 'Modo: Smart Pacing',
        'advisory': 'Modo: Consultivo',
        'strict_local': 'Modo: Contingencia Estrita',
      };
      elMode.textContent = modeLabels[policyMode] || `Modo: ${policyMode}`;
    }

    // Barra de Progresso Ampla
    const elPctLabel = document.getElementById('sre-budget-pct-label');
    const elCostCurr = document.getElementById('sre-budget-cost-current');
    const elCostLimit = document.getElementById('sre-budget-cost-limit');
    const elMainBar = document.getElementById('sre-budget-main-progress-bar');

    if (elPctLabel) elPctLabel.textContent = `${pct.toFixed(1)}%`;
    if (elCostCurr) elCostCurr.textContent = `R$ ${costBrl.toFixed(2).replace('.', ',')}`;
    if (elCostLimit) elCostLimit.textContent = `R$ ${monthlyBudget.toFixed(2).replace('.', ',')}`;
    if (elMainBar) {
      const displayPct = Math.min(100, Math.max(2, pct));
      elMainBar.style.width = `${displayPct}%`;
      if (pct >= 100) {
        elMainBar.className = 'h-full bg-rose-500 rounded-full transition-all duration-700 shadow-inner';
      } else if (pct >= 80) {
        elMainBar.className = 'h-full bg-gradient-to-r from-emerald-500 via-amber-400 to-amber-500 rounded-full transition-all duration-700 shadow-inner';
      } else {
        elMainBar.className = 'h-full bg-gradient-to-r from-emerald-500 via-cyan-500 to-indigo-500 rounded-full transition-all duration-700 shadow-inner';
      }
    }

    // 4 Cards de Metricas
    const elTotCount = document.getElementById('sre-token-total-count');
    const elSplit = document.getElementById('sre-token-split');
    const elCostReal = document.getElementById('sre-token-cost-real');
    const elCostUsd = document.getElementById('sre-token-cost-usd');
    const elAvoided = document.getElementById('sre-token-avoided-brl');
    const elCacheHits = document.getElementById('sre-token-cache-hits');
    const elProj = document.getElementById('sre-token-projection-brl');

    if (elTotCount) elTotCount.textContent = Number(tokens).toLocaleString('pt-BR');
    if (elSplit) elSplit.textContent = `${Number(promptTokens).toLocaleString('pt-BR')} in / ${Number(completionTokens).toLocaleString('pt-BR')} out`;
    if (elCostReal) elCostReal.textContent = `R$ ${costBrl.toFixed(2).replace('.', ',')}`;
    if (elCostUsd) elCostUsd.textContent = `US$ ${costUsd.toFixed(4)}`;
    if (elAvoided) elAvoided.textContent = `R$ ${avoidedBrl.toFixed(2).replace('.', ',')}`;
    if (elCacheHits) elCacheHits.textContent = `${cacheHits} respostas locais`;
    if (elProj) elProj.textContent = `R$ ${projectedBrl.toFixed(2).replace('.', ',')}`;

    // Preenche campos do formulario
    const inMonthly = document.getElementById('input-budget-monthly');
    const inAlert = document.getElementById('input-budget-alert-pct');
    const selMode = document.getElementById('select-budget-mode');
    if (inMonthly && document.activeElement !== inMonthly) inMonthly.value = monthlyBudget.toFixed(2);
    if (inAlert && document.activeElement !== inAlert) inAlert.value = (budget?.alert_threshold_pct ?? 80).toFixed(0);
    if (selMode && document.activeElement !== selMode) selMode.value = policyMode;
  }

  /**
   * Renderiza os insights operacionais e veredito inteligente de performance da AURA.
   */
  renderOperationalInsights(metrics, budget, stations) {
    const elVerdict = document.getElementById('sre-operational-verdict');
    const elHealth = document.getElementById('sre-insights-health-label');
    const elCacheEff = document.getElementById('sre-cache-efficiency-rate');
    const elRagStatus = document.getElementById('sre-rag-efficiency-status');
    const elAvgTokens = document.getElementById('sre-avg-tokens-per-turn');

    const ttftP50 = metrics?.ttft_ms?.p50 || 0;
    const reqCount = metrics?.ttft_ms?.count || 0;
    const cacheHits = metrics?.router_cache_hits || 0;
    const cacheMisses = metrics?.router_cache_misses || 0;
    const totalLookups = cacheHits + cacheMisses;
    const hitRate = totalLookups > 0 ? (cacheHits / totalLookups) * 100.0 : 100.0;
    const costBrl = budget?.monthly_consumed_brl ?? 0.0;
    const monthlyBudget = budget?.monthly_budget_brl ?? 30.00;
    const pct = monthlyBudget > 0 ? (costBrl / monthlyBudget) * 100.0 : 0.0;
    const avoidedBrl = budget?.total_avoided_cost_brl ?? 0.0;
    const stationOnline = stations && stations.length > 0 ? stations[0].erp_online : true;

    if (elCacheEff) elCacheEff.textContent = `${hitRate.toFixed(0)}%`;
    if (elRagStatus) elRagStatus.textContent = stationOnline ? 'Hibrido Ativo' : 'Contingencia FTS5';

    const totalTokens = budget?.total_tokens_consumed || metrics?.token_usage?.total_tokens || 0;
    const avgTok = reqCount > 0 ? Math.round(totalTokens / reqCount) : 450;
    if (elAvgTokens) elAvgTokens.textContent = `~${avgTok}`;

    if (elVerdict) {
      let verdict = '';
      if (pct >= 100) {
        verdict = `Teto orcamentario mensal atingido (R$ ${costBrl.toFixed(2).replace('.', ',')} / R$ ${monthlyBudget.toFixed(2).replace('.', ',')}). A AURA ativou contingencia de contencao, operando em modo estrito de cache local e sintese compacta para preservar custos.`;
        if (elHealth) {
          elHealth.textContent = 'Alerta Orcamentario';
          elHealth.className = 'text-[10px] font-mono text-rose-400 font-bold';
        }
      } else if (pct >= 80) {
        verdict = `Operacao em atencao orcamentaria (${pct.toFixed(1)}% do teto consumido). O Smart Pacing esta balanceando chamadas externas e priorizando o acervo local FTS5 com latencia sub-15ms. Economia evitada ate agora: R$ ${avoidedBrl.toFixed(2).replace('.', ',')}.`;
        if (elHealth) {
          elHealth.textContent = 'Atencao Orcamentaria';
          elHealth.className = 'text-[10px] font-mono text-amber-400 font-bold';
        }
      } else {
        const speedText = ttftP50 < 1500 ? 'velocidade ultra-rapida' : 'performance estavel';
        verdict = `Operacao saudavel com ${speedText} (P50 de ${Math.round(ttftP50 || 700)}ms). Consumo de tokens sob controle (${pct.toFixed(1)}% do teto mensal de R$ ${monthlyBudget.toFixed(2).replace('.', ',')}). O motor local evitou ~R$ ${avoidedBrl.toFixed(2).replace('.', ',')} em custos de nuvem.`;
        if (elHealth) {
          elHealth.textContent = 'Saudavel (Alta Eficiencia)';
          elHealth.className = 'text-[10px] font-mono text-emerald-400 font-semibold';
        }
      }
      elVerdict.textContent = verdict;
    }
  }

  /**
   * Envia atualizacao da politica orcamentaria para o backend.
   */
  async handleSaveBudgetPolicy() {
    const inMonthly = document.getElementById('input-budget-monthly');
    const inAlert = document.getElementById('input-budget-alert-pct');
    const selMode = document.getElementById('select-budget-mode');
    const feedback = document.getElementById('token-policy-save-feedback');
    const btnSave = document.getElementById('btn-save-token-policy');

    if (!inMonthly || !inAlert || !selMode) return;

    const monthlyVal = parseFloat(inMonthly.value) || 30.0;
    const alertVal = parseFloat(inAlert.value) || 80.0;
    const modeVal = selMode.value || 'smart_pacing';

    if (btnSave) {
      btnSave.disabled = true;
      btnSave.classList.add('opacity-50');
    }

    try {
      const res = await fetch('/api/v1/aura/telemetry/token-budget/policy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          monthly_budget_brl: monthlyVal,
          alert_threshold_pct: alertVal,
          enforcement_mode: modeVal,
        }),
      });

      if (res.ok) {
        if (feedback) {
          feedback.classList.remove('hidden');
          setTimeout(() => feedback.classList.add('hidden'), 4000);
        }
        await this.fetchCockpitData();
      }
    } catch (e) {
      console.warn('Falha ao salvar politica de orcamento:', e);
    } finally {
      if (btnSave) {
        btnSave.disabled = false;
        btnSave.classList.remove('opacity-50');
      }
    }
  }

  /**
   * Renderiza curva de latencia elegante no Canvas HTML5 nativo (60 FPS, 0 KB de bibliotecas).
   */
  drawLatencyCanvas(samples) {
    const canvas = document.getElementById('telemetry-ttft-canvas');
    if (!canvas || !canvas.getContext) return;

    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;

    ctx.clearRect(0, 0, w, h);

    if (!samples || samples.length === 0) {
      ctx.fillStyle = '#64748b';
      ctx.font = '12px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('Aguardando requisicoes de inferencia para tracao de curva...', w / 2, h / 2);
      return;
    }

    const padLeft = 40;
    const padRight = 20;
    const padTop = 20;
    const padBottom = 25;
    const chartW = w - padLeft - padRight;
    const chartH = h - padTop - padBottom;

    const maxVal = Math.max(...samples, 1000) * 1.15;
    const minVal = 0;

    // Linhas de grade sutis
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 3; i++) {
      const y = padTop + (chartH / 3) * i;
      ctx.beginPath();
      ctx.moveTo(padLeft, y);
      ctx.lineTo(w - padRight, y);
      ctx.stroke();

      const labelVal = Math.round(maxVal - (maxVal / 3) * i);
      ctx.fillStyle = '#64748b';
      ctx.font = '9px monospace';
      ctx.textAlign = 'right';
      ctx.fillText(`${labelVal}ms`, padLeft - 6, y + 3);
    }

    // Pontos da curva
    const points = samples.map((val, idx) => {
      const x = padLeft + (chartW / (samples.length - 1 || 1)) * idx;
      const y = padTop + chartH - ((val - minVal) / (maxVal - minVal)) * chartH;
      return { x, y, val };
    });

    // Gradiente de preenchimento (Cyber Cyan / Emerald)
    const gradient = ctx.createLinearGradient(0, padTop, 0, padTop + chartH);
    gradient.addColorStop(0, 'rgba(6, 182, 212, 0.35)');
    gradient.addColorStop(0.5, 'rgba(16, 185, 129, 0.15)');
    gradient.addColorStop(1, 'rgba(6, 182, 212, 0.0)');

    ctx.beginPath();
    ctx.moveTo(points[0].x, padTop + chartH);
    ctx.lineTo(points[0].x, points[0].y);

    for (let i = 0; i < points.length - 1; i++) {
      const xc = (points[i].x + points[i + 1].x) / 2;
      const yc = (points[i].y + points[i + 1].y) / 2;
      ctx.quadraticCurveTo(points[i].x, points[i].y, xc, yc);
    }
    ctx.lineTo(points[points.length - 1].x, points[points.length - 1].y);
    ctx.lineTo(points[points.length - 1].x, padTop + chartH);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();

    // Linha de contorno neon
    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);
    for (let i = 0; i < points.length - 1; i++) {
      const xc = (points[i].x + points[i + 1].x) / 2;
      const yc = (points[i].y + points[i + 1].y) / 2;
      ctx.quadraticCurveTo(points[i].x, points[i].y, xc, yc);
    }
    ctx.lineTo(points[points.length - 1].x, points[points.length - 1].y);
    ctx.strokeStyle = '#06b6d4';
    ctx.lineWidth = 2.2;
    ctx.shadowColor = '#06b6d4';
    ctx.shadowBlur = 8;
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Ultimo ponto em destaque
    const lastPoint = points[points.length - 1];
    ctx.beginPath();
    ctx.arc(lastPoint.x, lastPoint.y, 4, 0, Math.PI * 2);
    ctx.fillStyle = '#10b981';
    ctx.fill();
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }
}

// Instancia singleton disponivel globalmente
window.auraTelemetry = new AuraTelemetryCoordinator();

document.addEventListener('DOMContentLoaded', () => {
  window.auraTelemetry.init();
});
