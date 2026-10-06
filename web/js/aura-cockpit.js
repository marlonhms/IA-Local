/**
 * AURA Cockpit Operacional Controller
 * Gerencia a telemetria ao vivo da pista, tanques cilíndricos volumétricos,
 * bicos de vazão, frentistas e auditoria do turno.
 */

class AuraCockpitController {
  constructor() {
    this.tanksData = [];
    this.pistaData = null;
    this.turnoData = null;
    this.lmcData = null;
    this.combosData = null;
    this.stationStatus = null;
    this.isLoading = false;
  }

  /**
   * Inicializa o cockpit com estado sob demanda (sem polling ou consultas automáticas)
   */
  async init() {
    this.renderInitialPlaceholder();
  }

  renderInitialPlaceholder() {
    const container = document.getElementById('cockpit-tanks-grid');
    if (container && (!this.tanksData || this.tanksData.length === 0)) {
      container.innerHTML = `
        <div class="col-span-full py-10 px-6 text-center glass-panel border border-slate-800/80 rounded-2xl bg-gradient-to-b from-slate-900/40 to-slate-950/60 shadow-lg">
          <div class="w-14 h-14 rounded-2xl aura-brand-pedestal flex items-center justify-center mx-auto mb-3">
            <svg class="w-7 h-7 text-emerald-400 aura-glyph" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect x="3" y="3" width="11" height="18" rx="2" stroke="currentColor" stroke-width="1.75"/>
              <rect x="5.5" y="6" width="6" height="4" rx="0.8" stroke="currentColor" stroke-width="1.2" stroke-opacity="0.9"/>
              <path d="M14 8h2.5a2 2 0 0 1 2 2v6.5a1.5 1.5 0 0 0 3 0V9l-2-2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
              <line x1="2" y1="21" x2="15" y2="21" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>
              <line x1="6" y1="14" x2="11" y2="14" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
              <line x1="6" y1="17" x2="9" y2="17" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
            </svg>
          </div>
          <h4 class="text-white font-bold text-base mb-1">Panorama Operacional Sob Demanda</h4>
          <p class="text-slate-400 text-xs max-w-md mx-auto mb-4 leading-relaxed font-sans">
            A AURA opera sem consultas automáticas em segundo plano para economizar recursos e garantir máxima prontidão sob demanda.
          </p>
          <div class="flex flex-wrap items-center justify-center gap-3">
            <button onclick="window.auraCockpit.refreshAllData()" class="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-emerald-300 border border-emerald-500/30 text-xs font-semibold transition-all shadow-sm flex items-center gap-2">
              <i data-lucide="refresh-cw" class="w-4 h-4 text-emerald-400"></i>
              <span>Consultar Panorama Agora</span>
            </button>
            <button onclick="window.auraChat.sendUserPrompt('Qual a situação e autonomia de cada tanque agora?')" class="px-4 py-2 rounded-xl bg-purple-600/20 hover:bg-purple-600/30 text-purple-200 border border-purple-500/30 text-xs font-semibold transition-all shadow-sm flex items-center gap-2">
              <svg class="w-4 h-4 text-purple-300 aura-glyph aura-core-insignia" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <polygon points="12 2 20.66 7 20.66 17 12 22 3.34 17 3.34 7" stroke="currentColor" stroke-width="1.75" stroke-linejoin="round"/>
                <polygon points="12 6 17.2 9 17.2 15 12 18 6.8 15 6.8 9" stroke="currentColor" stroke-width="1.25" stroke-opacity="0.6" stroke-linejoin="round"/>
                <circle cx="12" cy="12" r="2.2" fill="currentColor"/>
                <line x1="12" y1="2" x2="12" y2="6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                <line x1="12" y1="18" x2="12" y2="22" stroke-width="1.5" stroke-linecap="round"/>
              </svg>
              <span>Perguntar no Chat</span>
            </button>
          </div>
        </div>`;
    }

    const splitContainer = document.getElementById('split-tanks-grid');
    if (splitContainer && (!this.tanksData || this.tanksData.length === 0)) {
      splitContainer.innerHTML = `
        <div class="col-span-full py-6 text-center text-slate-400 font-sans text-xs glass-panel p-4">
          Consultas 100% sob demanda. Pergunte no chat ao lado ou <button onclick="window.auraCockpit.refreshAllData()" class="text-cyan-400 hover:underline font-bold">clique aqui</button> para apurar.
        </div>`;
    }

    const summaryEl = document.getElementById('cockpit-runout-summary');
    if (summaryEl) {
      summaryEl.innerHTML = `
        <div class="text-xs text-slate-400 font-sans flex items-center gap-1.5">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
          <span>Consultas 100% sob demanda</span>
        </div>`;
    }

    // 3. Bicos da Pista
    const bicosContainer = document.getElementById('cockpit-bicos-grid');
    if (bicosContainer && !this.pistaData) {
      bicosContainer.innerHTML = `
        <div class="col-span-full py-6 text-center text-slate-400 font-sans text-xs glass-subcard p-4 rounded-xl border border-white/5">
          <span>Leitura de bicos e fluxo de abastecimento sob demanda.</span>
          <button onclick="window.auraCockpit.refreshAllData()" class="mt-2 block mx-auto px-3 py-1 bg-slate-800 hover:bg-slate-700 text-cyan-300 rounded border border-slate-700 text-xs transition-colors">
            Consultar Bicos ↺
          </button>
        </div>`;
    }

    // 4. Performance de Frentistas
    const frentistasContainer = document.getElementById('cockpit-frentistas-table');
    if (frentistasContainer && !this.pistaData) {
      frentistasContainer.innerHTML = `
        <div class="py-6 text-center text-slate-400 font-sans text-xs glass-subcard p-4 rounded-xl border border-white/5">
          Aguardando consulta de produtividade da pista.
        </div>`;
    }

    // 5. Conciliação de Turno
    const turnoContainer = document.getElementById('cockpit-turno-content');
    if (turnoContainer && !this.turnoData) {
      turnoContainer.innerHTML = `
        <div class="py-6 text-center text-slate-400 font-sans text-xs glass-subcard p-4 rounded-xl border border-white/5">
          <span>Conciliação contábil e física disponível sob demanda.</span>
          <button onclick="window.auraCockpit.refreshAllData()" class="mt-2 block mx-auto px-3 py-1 bg-slate-800 hover:bg-slate-700 text-cyan-300 rounded border border-slate-700 text-xs transition-colors">
            Auditar Turno Agora ↺
          </button>
        </div>`;
    }

    // 6. Livro LMC Oficial ANP
    const lmcContainer = document.getElementById('cockpit-lmc-content');
    if (lmcContainer && !this.lmcData) {
      lmcContainer.innerHTML = `
        <div class="py-6 text-center text-slate-400 font-sans text-xs glass-subcard p-4 rounded-xl border border-white/5">
          <span>Livro de Movimentação de Combustíveis (Portaria 26 ANP).</span>
          <button onclick="window.auraCockpit.refreshAllData()" class="mt-2 block mx-auto px-3 py-1 bg-slate-800 hover:bg-slate-700 text-purple-300 rounded border border-slate-700 text-xs transition-colors">
            Verificar Conformidade ANP ↺
          </button>
        </div>`;
    }

    // 7. Combos da Loja
    const combosContainer = document.getElementById('cockpit-combos-container');
    if (combosContainer && !this.combosData) {
      combosContainer.innerHTML = `
        <div class="col-span-full py-6 text-center text-slate-400 font-sans text-xs glass-subcard p-4 rounded-xl border border-white/5">
          Regras de associação e Combos da Loja sob demanda.
        </div>`;
    }
  }

  /**
   * Recarrega todos os dados operacionais em paralelo com máxima velocidade
   */
  async refreshAllData() {
    if (this.isLoading) return;
    this.isLoading = true;
    this.setRefreshSpinner(true);
    this.renderLoadingSkeletons();

    try {
      // 1. Identificação da Estação
      const stationPromise = window.auraApi.getStationStatus().catch(err => {
        console.warn('Erro ao carregar status da estação:', err);
        return null;
      });

      // 2. Previsão de Tanques (Run-Out)
      const runOutPromise = window.auraApi.executeIntent('run_out').catch(err => {
        console.warn('Erro ao carregar run_out:', err);
        return null;
      });

      // 3. Auditoria de Pista e Frentistas
      const pistaPromise = window.auraApi.executeIntent('desempenho_pista_frentistas').catch(err => {
        console.warn('Erro ao carregar pista:', err);
        return null;
      });

      // 4. Conciliação de Turno
      const turnoPromise = window.auraApi.executeIntent('conciliacao_turno').catch(err => {
        console.warn('Erro ao carregar turno:', err);
        return null;
      });

      // 5. LMC ANP
      const lmcPromise = window.auraApi.executeIntent('lmc_anp').catch(err => {
        console.warn('Erro ao carregar LMC:', err);
        return null;
      });

      // 6. Combos de Conveniência
      const combosPromise = window.auraApi.executeIntent('conveniencia_vendas_cruzadas').catch(err => {
        console.warn('Erro ao carregar combos:', err);
        return null;
      });

      const [stationRes, runOutRes, pistaRes, turnoRes, lmcRes, combosRes] = await Promise.all([
        stationPromise, runOutPromise, pistaPromise, turnoPromise, lmcPromise, combosPromise
      ]);

      if (stationRes) {
        this.stationStatus = stationRes;
        this.renderStationHeader(stationRes);
      }

      if (runOutRes && runOutRes.data) {
        this.tanksData = runOutRes.data.detalhamento_tanques || [];
        this.renderTanksMatrix(this.tanksData, runOutRes.data);
        this.renderSplitTanks(this.tanksData);
      } else {
        const container = document.getElementById('cockpit-tanks-grid');
        if (container && (!this.tanksData || this.tanksData.length === 0)) {
          container.innerHTML = `
            <div class="col-span-full py-8 text-center text-amber-400 font-sans text-sm glass-panel p-4">
              <span class="inline-flex items-center gap-2"><svg class="w-4 h-4 text-amber-400 inline" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" stroke-width="1.75"/><line x1="12" y1="9" x2="12" y2="13" stroke-width="1.75"/><circle cx="12" cy="17" r="1" fill="currentColor"/></svg> <span>Dados volumétricos temporariamente indisponíveis no momento.</span></span>
              <button onclick="window.auraCockpit.refreshAllData()" class="mt-2 block mx-auto px-3 py-1 bg-slate-800 text-cyan-300 rounded border border-slate-700 hover:bg-slate-700 text-xs">
                Tentar Novamente ↺
              </button>
            </div>`;
        }
      }

      if (pistaRes && pistaRes.data) {
        this.pistaData = pistaRes.data;
        this.renderPistaSection(pistaRes.data);
      } else if (!this.pistaData) {
        const b = document.getElementById('cockpit-bicos-grid');
        if (b) b.innerHTML = '<div class="text-slate-400 font-sans text-xs col-span-full py-2">Sem leitura dos bicos de abastecimento no momento.</div>';
        const f = document.getElementById('cockpit-frentistas-table');
        if (f) f.innerHTML = '<div class="text-slate-400 font-sans text-xs py-2">Sem dados de frentistas disponíveis.</div>';
        const a = document.getElementById('cockpit-anomalias-list');
        if (a) a.innerHTML = '<div class="text-slate-400 font-sans text-xs py-2">Comunicação com a pista temporariamente indisponível.</div>';
      }

      if (turnoRes && turnoRes.data) {
        this.turnoData = turnoRes.data;
        this.renderTurnoCard(turnoRes.data);
      } else if (!this.turnoData) {
        const t = document.getElementById('cockpit-turno-content');
        if (t) t.innerHTML = '<div class="text-slate-500 font-sans text-xs py-2">Turno não localizado ou caixa fechado.</div>';
      }

      if (lmcRes && lmcRes.data) {
        this.lmcData = lmcRes.data;
        this.renderLmcCard(lmcRes.data);
      } else if (!this.lmcData) {
        const l = document.getElementById('cockpit-lmc-content');
        if (l) l.innerHTML = '<div class="text-slate-500 font-sans text-xs py-2">Livro LMC não consultado.</div>';
      }

      if (combosRes && combosRes.data) {
        this.combosData = combosRes.data;
        this.renderTopCombosBanner(combosRes.data);
      } else if (!this.combosData) {
        const c = document.getElementById('cockpit-combos-container');
        if (c) c.innerHTML = '<div class="text-slate-500 font-sans text-xs col-span-full py-2">Sem regras de cesta registradas.</div>';
      }

      this.updateLastSyncTimestamp();
    } catch (err) {
      console.error('[AuraCockpit] Erro ao sincronizar cockpit:', err);
    } finally {
      this.isLoading = false;
      this.setRefreshSpinner(false);
    }
  }

  /**
   * Atualiza cabeçalho com identificação da filial
   */
  renderStationHeader(st) {
    const filialEl = document.getElementById('hud-filial-name');
    const sidebarFilialEl = document.getElementById('sidebar-filial-name');
    if (st) {
      const text = `${st.filial_nome || 'Posto Piloto'} (Filial ${st.filial_id || '59050'})`;
      if (filialEl) filialEl.textContent = text;
      if (sidebarFilialEl) sidebarFilialEl.textContent = text;
    }
  }

  /**
   * Renderiza os tanques volumétricos cilíndricos com simulação de fluido
   */
  renderTanksMatrix(tanks, rawRunOut) {
    const container = document.getElementById('cockpit-tanks-grid');
    if (!container) return;

    if (!tanks || tanks.length === 0) {
      container.innerHTML = `
        <div class="col-span-full py-8 text-center text-slate-400 font-sans text-sm">
          Nenhum tanque configurado ou telemetria indisponível.
        </div>`;
      return;
    }

    // Ordena por criticidade (menor ocupação primeiro, excluindo inativos se houver)
    const sortedTanks = [...tanks].sort((a, b) => {
      if (a.status_operacional === 'INATIVO') return 1;
      if (b.status_operacional === 'INATIVO') return -1;
      return (a.ocupacao_pct || 0) - (b.ocupacao_pct || 0);
    });

    let html = '';

    sortedTanks.forEach(tank => {
      const cod = tank.codtan || '000';
      const comb = (tank.combustivel || 'COMBUSTÍVEL').toUpperCase();
      const cap = Number(tank.capacidade_litros || 0);
      const saldo = Number(tank.saldo_atual_litros || 0);
      const pct = Math.min(100, Math.max(0, Number(tank.ocupacao_pct || 0)));
      const ullage = Number(tank.espaco_livre_ullage_litros || 0);
      const comp5k = tank.compartimentos_5k || 0;
      const horasAutonomia = Number(tank.autonomia_runout_horas || 0);
      const diasAutonomia = Number(tank.autonomia_runout_dias || 0);
      const horasCritica = Number(tank.autonomia_critica_horas ?? 0);
      const statusOp = tank.status_operacional || 'NORMAL';
      const isCritical = tank.alerta_critico || pct < 15;
      const isInativo = statusOp === 'INATIVO';

      // Cor do fluido baseada no produto
      let fuelClass = 'fuel-gasolina-comum';
      let borderAccent = 'border-emerald-500/40';
      let tagBg = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';

      if (comb.includes('ADITIVADA')) {
        fuelClass = 'fuel-gasolina-aditivada';
        borderAccent = 'border-emerald-400/50';
        tagBg = 'bg-emerald-400/10 text-emerald-300 border-emerald-400/30';
      } else if (comb.includes('ETANOL') || comb.includes('ALCOOL')) {
        fuelClass = 'fuel-etanol';
        borderAccent = 'border-cyan-500/50';
        tagBg = 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30';
      } else if (comb.includes('S10')) {
        fuelClass = 'fuel-diesel-s10';
        borderAccent = 'border-indigo-500/50';
        tagBg = 'bg-indigo-500/10 text-indigo-300 border-indigo-500/30';
      } else if (comb.includes('S500') || comb.includes('DIESEL')) {
        fuelClass = 'fuel-diesel-s500';
        borderAccent = 'border-purple-500/50';
        tagBg = 'bg-purple-500/10 text-purple-300 border-purple-500/30';
      } else if (comb.includes('ARLA')) {
        fuelClass = 'fuel-arla';
        borderAccent = 'border-sky-500/50';
        tagBg = 'bg-sky-500/10 text-sky-300 border-sky-500/30';
      }

      // Alerta crítico ou atenção sobrepõe cor do card e do fluido com gradientes de advertência
      if (isCritical && !isInativo) {
        fuelClass += ' fuel-critical';
        borderAccent = 'border-rose-500/60 shadow-lg shadow-rose-950/20';
      } else if (pct < 25 && !isInativo) {
        fuelClass += ' fuel-warning';
        borderAccent = 'border-amber-500/50 shadow-md shadow-amber-950/20';
      }

      html += `
        <div class="glass-panel p-4 flex flex-col justify-between relative overflow-hidden transition-all duration-300 hover:scale-[1.01] ${borderAccent}">
          <!-- Topo do Card -->
          <div class="flex items-start justify-between mb-3 pb-2.5 border-b border-white/5">
            <div>
              <div class="flex items-center gap-2">
                <span class="font-sans text-xs font-semibold px-2 py-0.5 rounded-md bg-white/5 text-slate-200 border border-white/10 tracking-wide">
                  TQ-${cod}
                </span>
                <span class="text-xs font-semibold px-2.5 py-0.5 rounded-full border ${tagBg}">
                  ${comb}
                </span>
              </div>
              <div class="mt-1.5 text-slate-400 text-[11px] font-sans flex items-center gap-1">
                <span class="text-slate-500">Bicos:</span>
                <span class="text-slate-300">${(tank.bicos_conectados && tank.bicos_conectados.length) ? tank.bicos_conectados.join(', ') : 'Nenhum'}</span>
              </div>
            </div>

            <!-- Badge de Status de Risco -->
            <div>
              ${isInativo ? `
                <span class="px-2.5 py-0.5 rounded-full text-[10px] font-sans font-semibold bg-slate-800 text-slate-400 border border-slate-700">
                  INATIVO
                </span>
              ` : isCritical ? `
                <span class="px-2.5 py-0.5 rounded-full text-[10px] font-sans font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/40 animate-pulse">
                  CRÍTICO &lt;15%
                </span>
              ` : pct < 30 ? `
                <span class="px-2.5 py-0.5 rounded-full text-[10px] font-sans font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/40">
                  ATENÇÃO
                </span>
              ` : `
                <span class="px-2.5 py-0.5 rounded-full text-[10px] font-sans font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                  REGULAR
                </span>
              `}
            </div>
          </div>

          <!-- Centro: Medidor Cápsula Precision Glass + Métricas Executivas -->
          <div class="flex items-center gap-4 my-2">
            <!-- Cápsula Precision Glass -->
            <div class="tank-gauge-container flex-shrink-0" title="Nível: ${pct.toFixed(1)}%">
              <div class="tank-tick-75"></div>
              <div class="tank-tick-50"></div>
              <div class="tank-tick-25"></div>
              <div class="tank-critical-line"></div>
              <div class="tank-liquid ${fuelClass}" style="height: ${isInativo ? 0 : pct}%;"></div>
            </div>

            <!-- Dados Volumétricos Executivos -->
            <div class="flex-1 space-y-1.5 font-sans text-xs">
              <div class="border-b border-white/5 pb-1">
                <div class="text-[10px] uppercase tracking-wider text-slate-400 font-medium">Saldo Atual</div>
                <div class="text-xl font-bold font-sans tabular-nums tracking-tight ${isCritical ? 'text-rose-400' : 'text-slate-100'}">
                  ${saldo.toLocaleString('pt-BR', { maximumFractionDigits: 0 })} <span class="text-xs font-normal text-slate-400">L</span>
                </div>
              </div>

              <div class="flex items-center justify-between border-b border-white/5 py-1">
                <span class="text-slate-400">Capacidade:</span>
                <span class="text-slate-300 tabular-nums">${cap.toLocaleString('pt-BR', { maximumFractionDigits: 0 })} L</span>
              </div>

              <div class="flex items-center justify-between border-b border-white/5 py-1">
                <span class="text-slate-400">Ocupação:</span>
                <span class="font-bold tabular-nums ${pct < 15 ? 'text-rose-400' : pct < 35 ? 'text-amber-400' : 'text-emerald-400'}">
                  ${pct.toFixed(1)}%
                </span>
              </div>

              <div class="flex items-center justify-between border-b border-white/5 py-1">
                <span class="text-slate-400">Espaço Livre (Ullage):</span>
                <span class="text-cyan-300 font-semibold tabular-nums">${ullage.toLocaleString('pt-BR', { maximumFractionDigits: 0 })} L</span>
              </div>

              <div class="flex items-center justify-between pt-1">
                <span class="text-slate-400">Descarga Carreta:</span>
                <span class="text-purple-300 font-semibold tabular-nums flex items-center gap-1.5">
                  <svg class="w-3.5 h-3.5 text-purple-400 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><rect x="1" y="4" width="14" height="12" rx="1.5" stroke-width="1.75"/><path d="M15 8h4.5l2.5 3.5V16h-7V8z" stroke-width="1.75" stroke-linejoin="round"/><circle cx="5.5" cy="18.5" r="2.5" stroke-width="1.75"/><circle cx="18.5" cy="18.5" r="2.5" stroke-width="1.75"/></svg>
                  <span>${comp5k}x 5.000 L</span>
                </span>
              </div>
            </div>
          </div>

          <!-- Rodapé do Card: Autonomia & Ação Rápida -->
          <div class="mt-3 pt-2.5 border-t border-white/5 flex items-center justify-between">
            <div class="font-sans text-[11px] leading-tight">
              ${isInativo ? `
                <span class="text-slate-500">Sem consumo registrado</span>
              ` : isCritical ? `
                <div class="text-rose-400 font-semibold space-y-0.5">
                  <div class="flex items-center gap-1.5">
                    <svg class="w-3.5 h-3.5 text-rose-400 inline flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" stroke-width="1.75" stroke-linejoin="round"/><line x1="12" y1="9" x2="12" y2="13" stroke-width="1.75" stroke-linecap="round"/><circle cx="12" cy="17" r="1" fill="currentColor"/></svg>
                    <span>Reserva Crítica (&lt;15%)</span>
                  </div>
                  <div class="text-slate-400 text-[10px]">Esgotamento: <strong class="text-rose-300 tabular-nums">~${horasAutonomia.toFixed(0)}h</strong> (~${diasAutonomia.toFixed(1)}d)</div>
                </div>
              ` : `
                <div class="text-slate-300 space-y-0.5">
                  <div>Autonomia 15%: <strong class="text-cyan-300 tabular-nums font-semibold">~${horasCritica.toFixed(0)}h</strong></div>
                  <div class="text-slate-400 text-[10px]">Esgotamento: <strong class="text-emerald-300 tabular-nums font-semibold">~${horasAutonomia.toFixed(0)}h</strong> (~${diasAutonomia.toFixed(1)}d)</div>
                </div>
              `}
            </div>

            <button 
              onclick="window.auraApp.askAboutTank('${cod}', '${comb}')"
              class="px-3 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-cyan-300 hover:text-white border border-cyan-500/30 text-xs font-sans font-medium flex items-center gap-1.5 transition-all shadow-sm active:scale-95"
              title="Consultar à AURA sobre este tanque">
              <span>Consultar</span>
              <svg class="w-3.5 h-3.5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
            </button>
          </div>
        </div>
      `;
    });

    container.innerHTML = html;

    // Atualiza resumo executivo do Run-Out se disponível
    const summaryEl = document.getElementById('cockpit-runout-summary');
    if (summaryEl && tanks && tanks.length > 0) {
      const activeTanks = tanks.filter(t => t.status_operacional !== 'INATIVO');
      const totalAtivos = activeTanks.length;
      const emRisco = activeTanks.filter(t => t.alerta_critico).length;
      const capTot = activeTanks.reduce((sum, t) => sum + (Number(t.capacidade_litros) || 0), 0);
      const saldoTot = activeTanks.reduce((sum, t) => sum + (Number(t.saldo_atual_litros) || 0), 0);
      const ullageTot = activeTanks.reduce((sum, t) => sum + (Number(t.espaco_livre_ullage_litros) || 0), 0);
      const ocupMedia = capTot > 0 ? (saldoTot / capTot) * 100 : 0;

      summaryEl.innerHTML = `
        <div class="flex flex-wrap items-center gap-2 text-xs font-sans">
          <div class="px-3 py-1 rounded-full bg-slate-900/70 border border-white/10 text-slate-300 flex items-center gap-1.5 shadow-sm">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            <span>Tanques Ativos:</span>
            <strong class="text-emerald-400 tabular-nums font-semibold">${totalAtivos}</strong>
          </div>
          <div class="px-3 py-1 rounded-full bg-slate-900/70 border ${emRisco > 0 ? 'border-rose-500/30' : 'border-white/10'} text-slate-300 flex items-center gap-1.5 shadow-sm">
            <span class="w-1.5 h-1.5 rounded-full ${emRisco > 0 ? 'bg-rose-400 animate-pulse' : 'bg-slate-500'}"></span>
            <span>Abaixo de 15%:</span>
            <strong class="${emRisco > 0 ? 'text-rose-400' : 'text-slate-400'} tabular-nums font-semibold">${emRisco}</strong>
          </div>
          <div class="px-3 py-1 rounded-full bg-slate-900/70 border border-white/10 text-slate-300 flex items-center gap-1.5 shadow-sm">
            <span class="text-slate-400">Saldo Total:</span>
            <strong class="text-slate-100 tabular-nums font-semibold">${saldoTot.toLocaleString('pt-BR')} L</strong>
          </div>
          <div class="px-3 py-1 rounded-full bg-slate-900/70 border border-white/10 text-slate-300 flex items-center gap-1.5 shadow-sm">
            <span class="text-slate-400">Ocupação Média:</span>
            <strong class="text-cyan-300 tabular-nums font-semibold">${ocupMedia.toFixed(1)}%</strong>
          </div>
          <div class="px-3 py-1 rounded-full bg-slate-900/70 border border-white/10 text-slate-300 flex items-center gap-1.5 shadow-sm">
            <span class="text-slate-400">Ullage Total:</span>
            <strong class="text-purple-300 tabular-nums font-semibold">${ullageTot.toLocaleString('pt-BR')} L</strong>
          </div>
        </div>
      `;
    }
  }

  /**
   * Renderiza a seção de Bicos e Frentistas
   */
  renderPistaSection(pista) {
    // 1. Grid de Bicos com alerta de vazão
    const bicosContainer = document.getElementById('cockpit-bicos-grid');
    if (bicosContainer && pista.auditoria_vazao_bicos) {
      let bicosHtml = '';
      pista.auditoria_vazao_bicos.forEach(b => {
        const vazao = Number(b.vazao_media_l_min || 0);
        const isLento = b.alerta_filtro_lento || (b.status_operacional === 'ATIVO' && vazao > 0 && vazao < 30);
        const isInativo = b.status_operacional?.includes('INATIVO');

        bicosHtml += `
          <div class="p-3 rounded-xl glass-subcard border ${isLento ? 'border-amber-500/50 shadow-md shadow-amber-950/25' : isInativo ? 'border-white/5 opacity-70' : 'border-white/10'} flex flex-col justify-between font-sans text-xs transition-all hover:-translate-y-0.5">
            <div class="flex items-center justify-between">
              <span class="font-bold text-slate-200">Bico ${b.bico}</span>
              <span class="text-[10px] text-slate-400 px-1.5 py-0.5 rounded bg-slate-800/80">Bomba ${b.bomba_fisica}</span>
            </div>
            <div class="text-[11px] text-slate-400 truncate mt-1">${b.combustivel}</div>
            
            <div class="mt-2 pt-1 border-t border-white/5 flex items-center justify-between">
              <span class="text-slate-400 text-[10px]">Vazão Média:</span>
              <span class="font-bold tabular-nums ${isLento ? 'text-amber-300 text-sm' : isInativo ? 'text-slate-500' : 'text-emerald-400'}">
                ${isInativo ? '0.0' : vazao.toFixed(1)} L/min
              </span>
            </div>
            
            ${isLento ? `
              <div class="mt-1.5 text-[10px] text-amber-300 font-semibold flex items-center gap-1.5 bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/30">
                <svg class="w-3 h-3 text-amber-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" stroke-width="1.75" stroke-linejoin="round"/><line x1="12" y1="9" x2="12" y2="13" stroke-width="1.75" stroke-linecap="round"/><circle cx="12" cy="17" r="1" fill="currentColor"/></svg>
                <span>Filtro Lento (&lt;30 L/min)</span>
              </div>
            ` : ''}
          </div>
        `;
      });
      bicosContainer.innerHTML = bicosHtml || '<div class="text-slate-500 text-xs font-sans">Sem dados de bicos</div>';
    }

    // 2. Ranking de Frentistas
    const frentistasContainer = document.getElementById('cockpit-frentistas-table');
    if (frentistasContainer && pista.ranking_frentistas) {
      let frentHtml = `
        <table class="w-full text-left font-sans text-xs">
          <thead>
            <tr class="text-slate-400 border-b border-white/10 text-[11px]">
              <th class="pb-2">#</th>
              <th class="pb-2">Frentista</th>
              <th class="pb-2 text-right">Litros</th>
              <th class="pb-2 text-right">Faturamento</th>
              <th class="pb-2 text-right">Ticket Médio</th>
              <th class="pb-2 text-right">Conv. Aditivada</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-white/5">
      `;

      pista.ranking_frentistas.forEach((f, idx) => {
        const conv = Number(f.conversao_aditivada_pct || 0);
        frentHtml += `
          <tr class="hover:bg-white/[0.03] transition-colors">
            <td class="py-2.5 text-slate-400 tabular-nums">${idx + 1}</td>
            <td class="py-2.5 font-semibold text-slate-200">
              ${f.nome}
              ${f.destaque_performance ? `<span class="block text-[10px] text-emerald-400 font-normal">${f.destaque_performance}</span>` : ''}
            </td>
            <td class="py-2.5 text-right text-slate-300 tabular-nums">${Number(f.total_litros || 0).toFixed(1)} L</td>
            <td class="py-2.5 text-right text-emerald-300 font-semibold tabular-nums">R$ ${Number(f.faturamento_reais || 0).toFixed(2)}</td>
            <td class="py-2.5 text-right text-slate-300 tabular-nums">R$ ${Number(f.ticket_medio_reais || 0).toFixed(2)}</td>
            <td class="py-2.5 text-right">
              <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold tabular-nums ${conv > 15 ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-slate-800 text-slate-400'}">
                ${conv.toFixed(1)}%
              </span>
            </td>
          </tr>
        `;
      });

      frentHtml += `</tbody></table>`;
      frentistasContainer.innerHTML = frentHtml;
    }

    // 3. Anomalias de Pista (Abastecimentos manuais, micro-vendas)
    const anomaliasContainer = document.getElementById('cockpit-anomalias-list');
    if (anomaliasContainer && pista.anomalias_detectadas) {
      if (pista.anomalias_detectadas.length === 0) {
        anomaliasContainer.innerHTML = '<div class="text-xs text-emerald-400 font-sans py-2">✓ Nenhuma anomalia crítica ou fraude na pista detectada.</div>';
      } else {
        let anomHtml = '';
        pista.anomalias_detectadas.slice(0, 5).forEach(a => {
          anomHtml += `
            <div class="p-2.5 rounded-xl glass-subcard border border-slate-800 text-xs font-sans space-y-0.5">
              <div class="flex items-center justify-between text-[11px]">
                <span class="font-bold ${a.gravidade === 'ALTA' ? 'text-rose-400' : 'text-amber-400'}">
                  [${a.tipo}] Bico ${a.bico}
                </span>
                <span class="text-slate-400 tabular-nums">${a.data_hora || ''}</span>
              </div>
              <div class="text-slate-300 text-[11px]">${a.motivo}</div>
              <div class="text-slate-400 text-[10px]">Volume: <span class="tabular-nums">${a.litros} L</span> | Total: <span class="tabular-nums">R$ ${Number(a.total_reais || 0).toFixed(2)}</span> | Frentista: ${a.frentista}</div>
            </div>
          `;
        });
        anomaliasContainer.innerHTML = anomHtml;
      }
    }
  }

  /**
   * Renderiza card de Fechamento de Turno
   * AURA Precision Glass v1.0: Contrato Semântico & Diferença Provisória
   */
  renderTurnoCard(turno) {
    const el = document.getElementById('cockpit-turno-content');
    if (!el || (!turno.resumo_executivo && !turno.contrato)) return;

    const c = turno.contrato || turno;
    const assessment = c.assessment || {};
    const metrics = c.metrics || {};
    const r = turno.resumo_executivo || {};
    const score = Number(r.score_conformidade_pct || 0);

    const finality = assessment.finality || (r.status_conciliacao?.includes('ANDAMENTO') ? 'partial' : 'final');
    const isPartial = finality === 'partial';
    const isNoMovement = finality === 'no_movement' || turno.status === 'sem_movimento';
    const isUnavailable = finality === 'unavailable' || turno.status === 'indisponivel';

    let badgeClass = 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30';
    let badgeText = assessment.badge_label || r.status_conciliacao || 'Turno';

    if (isPartial) {
      badgeClass = 'bg-amber-500/20 text-amber-300 border border-amber-500/30';
      badgeText = assessment.badge_label || 'Análise parcial (provisória)';
    } else if (isNoMovement) {
      badgeClass = 'bg-slate-800 text-slate-400 border border-slate-700';
      badgeText = 'Sem movimentação';
    } else if (isUnavailable) {
      badgeClass = 'bg-rose-500/20 text-rose-300 border border-rose-500/30';
      badgeText = 'Fonte indisponível';
    } else if (assessment.severity === 'critical' || r.status_conciliacao?.includes('FURO') || r.status_conciliacao?.includes('DIVERGENCIA')) {
      badgeClass = 'bg-rose-500/20 text-rose-300 border border-rose-500/30';
      badgeText = assessment.badge_label || 'Divergência confirmada';
    } else if (score >= 95 || assessment.finality === 'final') {
      badgeClass = 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
      badgeText = assessment.badge_label || 'Conciliação validada';
    }

    const diffVal = Number(metrics.difference ?? r.diferenca_financeira_caixa ?? 0);
    const autRev = Number(metrics.automation_revenue ?? r.faturamento_pista_total ?? 0);
    const posRev = Number(metrics.pos_revenue ?? r.faturamento_caixa_total ?? 0);

    let diffLabel = 'Divergência Pista vs PDV:';
    let diffColorClass = 'text-emerald-400';
    if (isPartial) {
      diffLabel = 'Diferença Provisória (Caixa Aberto):';
      diffColorClass = diffVal < 0 ? 'text-amber-400' : 'text-emerald-400';
    } else if (isNoMovement || isUnavailable) {
      diffLabel = 'Situação:';
      diffColorClass = 'text-slate-400';
    } else if (diffVal < 0) {
      diffLabel = 'Falta Apurada no Caixa:';
      diffColorClass = 'text-rose-400';
    }

    const diffFormatted = (isNoMovement || isUnavailable)
      ? '—'
      : `${diffVal < 0 ? '-' : diffVal > 0 ? '+' : ''}R$ ${Math.abs(diffVal).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    const autRevText = (isNoMovement || isUnavailable)
      ? '—'
      : `R$ ${autRev.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    const posRevText = (isNoMovement || isUnavailable)
      ? '—'
      : `R$ ${posRev.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    const limitation = assessment.limitation;
    const diagText = r.diagnostico_caixa || c.explanation?.text || 'Conferência de turno executada com sucesso.';

    el.innerHTML = `
      <div class="space-y-3 font-sans text-xs">
        <div class="flex items-center justify-between">
          <span class="text-slate-400">Status da Conciliação:</span>
          <span class="font-bold px-2 py-0.5 rounded text-[11px] ${badgeClass}">
            ${this.escapeHtml(badgeText)}
          </span>
        </div>

        <div class="grid grid-cols-2 gap-2.5 p-3 rounded-xl glass-subcard border border-white/5">
          <div>
            <div class="text-slate-400 text-[10px]">Faturamento Automação Pista</div>
            <div class="text-sm font-bold text-slate-100 tabular-nums">${autRevText}</div>
          </div>
          <div>
            <div class="text-slate-400 text-[10px]">Faturamento Caixa PDV</div>
            <div class="text-sm font-bold text-cyan-300 tabular-nums">${posRevText}</div>
          </div>
        </div>

        <div class="flex items-center justify-between text-xs border-t border-white/5 pt-2">
          <span class="text-slate-400">${this.escapeHtml(diffLabel)}</span>
          <span class="font-bold tabular-nums ${diffColorClass}">
            ${diffFormatted}
          </span>
        </div>

        ${limitation && !isNoMovement && !isUnavailable ? `
          <div class="text-[11px] text-amber-300 bg-amber-500/10 p-2.5 rounded-xl border border-amber-500/25 flex items-start gap-1.5">
            <svg class="w-3.5 h-3.5 text-amber-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" stroke-width="1.75" stroke-linejoin="round"/><line x1="12" y1="9" x2="12" y2="13" stroke-width="1.75" stroke-linecap="round"/><circle cx="12" cy="17" r="1" fill="currentColor"/></svg>
            <div><strong>Limitação:</strong> ${this.escapeHtml(limitation)}</div>
          </div>
        ` : ''}

        <div class="text-[11px] text-slate-300 glass-subcard p-2.5 rounded-xl border border-white/5">
          ${this.escapeHtml(diagText)}
        </div>

        <div class="pt-2 border-t border-white/5 flex items-center justify-between font-sans">
          <span class="text-[10px] text-slate-400 font-sans">ERP Somente Leitura</span>
          <button 
            type="button"
            onclick="if (typeof window !== 'undefined') { window.__auraEvidenceStore = window.__auraEvidenceStore || {}; window.__auraEvidenceStore['cockpit_turno'] = window.auraCockpit?.turnoData; if (window.auraChat) window.auraChat.openEvidence('cockpit_turno', 'resumo'); }"
            class="px-2.5 py-1.5 rounded-lg bg-slate-800/90 hover:bg-slate-700 text-cyan-300 hover:text-white border border-cyan-500/30 transition-all text-[11px] flex items-center gap-1.5 cursor-pointer shadow-sm active:scale-95">
            <span>Ver Evidências</span>
            <span>↗</span>
          </button>
        </div>
      </div>
    `;
  }

  /**
   * Renderiza card de LMC ANP
   */
  renderLmcCard(lmc) {
    const el = document.getElementById('cockpit-lmc-content');
    if (!el || !lmc.resumo_executivo) return;

    const r = lmc.resumo_executivo;
    const isConforme = r.status_geral_anp === 'CONFORME_ANP';

    el.innerHTML = `
      <div class="space-y-3 font-sans text-xs">
        <div class="flex items-center justify-between">
          <span class="text-slate-400">Conformidade Portaria 26/1992:</span>
          <span class="font-bold px-2.5 py-0.5 rounded text-[11px] inline-flex items-center gap-1.5 ${isConforme ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' : 'bg-rose-500/20 text-rose-300 border border-rose-500/40'}">
            ${isConforme ? '<svg class="w-3.5 h-3.5 text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor"><polyline points="20 6 9 17 4 12" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg> CONFORME ANP (±0.6%)' : '<svg class="w-3.5 h-3.5 text-rose-400" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" stroke-width="1.75"/><line x1="12" y1="9" x2="12" y2="13" stroke-width="1.75"/><circle cx="12" cy="17" r="1" fill="currentColor"/></svg> ALERTA VOLUMÉTRICO'}
          </span>
        </div>

        <div class="grid grid-cols-2 gap-2.5 p-3 rounded-xl glass-subcard border border-white/5">
          <div>
            <div class="text-slate-400 text-[10px]">Tanques Auditados</div>
            <div class="text-sm font-bold text-slate-100 tabular-nums">${r.total_tanques_analisados || 0} tanques</div>
          </div>
          <div>
            <div class="text-slate-400 text-[10px]">Variação Física vs Livro</div>
            <div class="text-sm font-bold tabular-nums ${isConforme ? 'text-emerald-400' : 'text-rose-400'}">
              ${(r.variacao_volumetrica_geral_pct || 0).toFixed(2)}%
            </div>
          </div>
        </div>

        <div class="text-[11px] text-slate-400">
          Estoque Físico Total: <strong class="text-slate-200 tabular-nums font-semibold">${(r.total_estoque_fisico_litros || 0).toLocaleString('pt-BR')} L</strong>
        </div>
      </div>
    `;
  }

  /**
   * Renderiza os Top Combos de Conveniência (Market Basket Apriori)
   */
  renderTopCombosBanner(combos) {
    const el = document.getElementById('cockpit-combos-container');
    if (!el || !combos.top_combos_cross_selling) return;

    const list = combos.top_combos_cross_selling.slice(0, 3);
    let html = '';

    list.forEach(c => {
      const lift = Number(c.metricas?.lift || 0);
      const conf = Number(c.metricas?.confianca || 0) * 100;
      const incPct = Number(c.impacto_financeiro?.incremento_ticket_pct || 0);

      html += `
        <div class="p-3.5 rounded-xl glass-subcard border border-purple-500/30 flex flex-col justify-between font-sans text-xs hover:-translate-y-0.5 transition-all">
          <div>
            <div class="flex items-center justify-between text-[11px] mb-1.5 pb-1 border-b border-white/5">
              <span class="text-purple-300 font-bold tabular-nums">LIFT: ${lift.toFixed(1)}x</span>
              <span class="text-slate-400 tabular-nums">Confiança: ${conf.toFixed(0)}%</span>
            </div>
            <div class="text-slate-200 font-semibold">${c.produto_origem?.nompro}</div>
            <div class="text-emerald-400 text-[11px] mt-0.5">↳ + ${c.produto_recomendado?.nompro}</div>
          </div>

          <div class="mt-2.5 pt-2 border-t border-purple-900/30 text-[11px] text-slate-400">
            <span class="text-slate-300">${c.script_sugerido_caixa || ''}</span>
          </div>
        </div>
      `;
    });

    el.innerHTML = html;
  }

  /**
   * Renderiza skeleton loaders translúcidos em vidro líquido (shimmer wave)
   * para tanques volumétricos, bicos, frentistas e cartões durante o carregamento.
   */
  renderLoadingSkeletons() {
    // 1. Tanques Volumétricos (Cockpit)
    const tanksContainer = document.getElementById('cockpit-tanks-grid');
    if (tanksContainer) {
      let html = '';
      for (let i = 0; i < 4; i++) {
        html += `
          <div class="skeleton-glass p-4 rounded-2xl flex flex-col justify-between min-h-[190px] border border-white/10 space-y-3">
            <div class="flex items-center justify-between">
              <div class="skeleton-shimmer h-4 w-20"></div>
              <div class="skeleton-shimmer h-4 w-14 rounded-full"></div>
            </div>
            <div class="space-y-2 my-1">
              <div class="skeleton-shimmer h-5 w-36"></div>
              <div class="skeleton-shimmer h-12 w-full rounded-xl"></div>
              <div class="flex justify-between items-center pt-1">
                <div class="skeleton-shimmer h-3 w-24"></div>
                <div class="skeleton-shimmer h-4 w-16"></div>
              </div>
            </div>
            <div class="pt-2 border-t border-white/5 flex justify-between items-center">
              <div class="skeleton-shimmer h-3 w-28"></div>
              <div class="skeleton-shimmer h-3 w-16"></div>
            </div>
          </div>
        `;
      }
      tanksContainer.innerHTML = html;
    }

    // 2. Tanques Compactos (Split View)
    const splitTanksContainer = document.getElementById('split-tanks-grid');
    if (splitTanksContainer) {
      let splitHtml = '';
      for (let i = 0; i < 4; i++) {
        splitHtml += `
          <div class="skeleton-glass p-3 rounded-xl border border-white/10 space-y-2">
            <div class="flex justify-between items-center">
              <div class="skeleton-shimmer h-3.5 w-24"></div>
              <div class="skeleton-shimmer h-3.5 w-10"></div>
            </div>
            <div class="skeleton-shimmer h-3 w-32"></div>
            <div class="skeleton-shimmer h-2.5 w-20"></div>
          </div>
        `;
      }
      splitTanksContainer.innerHTML = splitHtml;
    }

    // 3. Bicos da Pista
    const bicosContainer = document.getElementById('cockpit-bicos-grid');
    if (bicosContainer) {
      let bicosHtml = '';
      for (let i = 0; i < 6; i++) {
        bicosHtml += `
          <div class="skeleton-glass p-2.5 rounded-xl border border-white/5 space-y-1.5">
            <div class="flex justify-between items-center">
              <div class="skeleton-shimmer h-3 w-12"></div>
              <div class="skeleton-shimmer h-3 w-10 rounded"></div>
            </div>
            <div class="skeleton-shimmer h-4 w-20"></div>
            <div class="skeleton-shimmer h-2 w-full rounded-full"></div>
          </div>
        `;
      }
      bicosContainer.innerHTML = bicosHtml;
    }

    // 4. Performance de Frentistas
    const frentistasContainer = document.getElementById('cockpit-frentistas-table');
    if (frentistasContainer) {
      let frentistasHtml = '';
      for (let i = 0; i < 3; i++) {
        frentistasHtml += `
          <div class="skeleton-glass p-2.5 rounded-xl border border-white/5 mb-2 flex items-center justify-between">
            <div class="flex items-center gap-2">
              <div class="skeleton-shimmer w-7 h-7 rounded-full"></div>
              <div class="space-y-1">
                <div class="skeleton-shimmer h-3.5 w-24"></div>
                <div class="skeleton-shimmer h-2.5 w-16"></div>
              </div>
            </div>
            <div class="skeleton-shimmer h-4 w-16"></div>
          </div>
        `;
      }
      frentistasContainer.innerHTML = frentistasHtml;
    }

    // 5. Auditoria & Anomalias
    const anomaliasContainer = document.getElementById('cockpit-anomalias-list');
    if (anomaliasContainer) {
      let anomaliasHtml = '';
      for (let i = 0; i < 2; i++) {
        anomaliasHtml += `
          <div class="skeleton-glass p-3 rounded-xl border border-white/5 space-y-2">
            <div class="skeleton-shimmer h-3 w-28"></div>
            <div class="skeleton-shimmer h-4 w-full"></div>
          </div>
        `;
      }
      anomaliasContainer.innerHTML = anomaliasHtml;
    }

    // 6. Conciliação de Turno
    const turnoContainer = document.getElementById('cockpit-turno-content');
    if (turnoContainer) {
      turnoContainer.innerHTML = `
        <div class="skeleton-glass p-4 rounded-xl border border-cyan-500/20 space-y-3">
          <div class="flex justify-between">
            <div class="skeleton-shimmer h-4 w-32"></div>
            <div class="skeleton-shimmer h-4 w-16 rounded-full"></div>
          </div>
          <div class="grid grid-cols-2 gap-3 py-1">
            <div class="skeleton-shimmer h-12 w-full rounded-lg"></div>
            <div class="skeleton-shimmer h-12 w-full rounded-lg"></div>
          </div>
          <div class="skeleton-shimmer h-3 w-48"></div>
        </div>
      `;
    }

    // 7. Livro LMC Oficial ANP
    const lmcContainer = document.getElementById('cockpit-lmc-content');
    if (lmcContainer) {
      lmcContainer.innerHTML = `
        <div class="skeleton-glass p-4 rounded-xl border border-emerald-500/20 space-y-3">
          <div class="flex justify-between">
            <div class="skeleton-shimmer h-4 w-36"></div>
            <div class="skeleton-shimmer h-4 w-20 rounded-full"></div>
          </div>
          <div class="skeleton-shimmer h-8 w-full rounded-lg"></div>
          <div class="skeleton-shimmer h-3 w-40"></div>
        </div>
      `;
    }

    // 8. Combos da Loja
    const combosContainer = document.getElementById('cockpit-combos-container');
    if (combosContainer) {
      let combosHtml = '';
      for (let i = 0; i < 3; i++) {
        combosHtml += `
          <div class="skeleton-glass p-3.5 rounded-xl border border-purple-500/20 space-y-2">
            <div class="flex justify-between">
              <div class="skeleton-shimmer h-4 w-28"></div>
              <div class="skeleton-shimmer h-4 w-12 rounded"></div>
            </div>
            <div class="skeleton-shimmer h-3 w-36"></div>
            <div class="skeleton-shimmer h-3 w-24"></div>
          </div>
        `;
      }
      combosContainer.innerHTML = combosHtml;
    }

    // 9. Summary Pill
    const summaryEl = document.getElementById('cockpit-runout-summary');
    if (summaryEl) {
      summaryEl.innerHTML = `
        <div class="skeleton-shimmer h-6 w-28 rounded-full"></div>
      `;
    }
  }

  setRefreshSpinner(isSpinning) {
    const btn = document.getElementById('btn-refresh-cockpit');
    if (btn) {
      if (isSpinning) {
        btn.classList.add('animate-spin');
      } else {
        btn.classList.remove('animate-spin');
      }
    }
  }

  updateLastSyncTimestamp() {
    const el = document.getElementById('hud-last-sync');
    if (el) {
      const now = new Date();
      el.textContent = `Sincronizado: ${now.toLocaleTimeString('pt-BR')}`;
    }
  }

  renderSplitTanks(tanks) {
    const container = document.getElementById('split-tanks-grid');
    if (!container || !tanks || tanks.length === 0) return;

    let html = '';
    tanks.forEach(t => {
      const cod = t.codtan || '000';
      const comb = (t.combustivel || 'COMBUSTÍVEL').toUpperCase();
      const pct = Math.min(100, Math.max(0, Number(t.ocupacao_pct || 0)));
      const isCritical = t.alerta_critico || pct < 15;
      const saldo = Number(t.saldo_atual_litros || 0);
      const ullage = Number(t.espaco_livre_ullage_litros || 0);
      const comp5k = t.compartimentos_5k || 0;
      const horasAutonomia = Number(t.autonomia_runout_horas || 0);

      let statusColor = 'text-emerald-400';
      let barColor = 'bg-emerald-400';
      let statusText = `Normal (~${horasAutonomia.toFixed(0)}h)`;
      let borderAccent = 'hover:border-emerald-500/50';

      if (isCritical) {
        statusColor = 'text-rose-400';
        barColor = 'bg-rose-400';
        statusText = `Crítico <15% (~${horasAutonomia.toFixed(0)}h)`;
        borderAccent = 'border-rose-500/40 hover:border-rose-400 shadow-md shadow-rose-950/20';
      } else if (pct < 35) {
        statusColor = 'text-amber-400';
        barColor = 'bg-amber-400';
        statusText = `Atenção (~${horasAutonomia.toFixed(0)}h)`;
        borderAccent = 'border-amber-500/30 hover:border-amber-400 shadow-md shadow-amber-950/20';
      }

      html += `
        <button onclick="window.auraApp.askAboutTank('${cod}', '${comb}')" class="p-3.5 rounded-xl glass-subcard border ${borderAccent} text-left font-sans text-xs transition-all duration-200 hover:-translate-y-0.5 group">
          <div class="flex items-center justify-between mb-1.5">
            <div class="flex items-center gap-1.5">
              <span class="text-xs font-semibold px-2 py-0.5 rounded-md bg-white/5 border border-white/10 text-slate-200">TQ-${cod}</span>
              <span class="font-medium text-slate-200 group-hover:text-white">${comb}</span>
            </div>
            <span class="text-xs font-bold ${statusColor} tabular-nums">${pct.toFixed(0)}%</span>
          </div>

          <div class="w-full h-1.5 rounded-full bg-slate-800/80 overflow-hidden my-2 border border-white/5">
            <div class="h-full rounded-full ${barColor} transition-all duration-500" style="width: ${pct}%"></div>
          </div>

          <div class="flex items-center justify-between text-[11px] mt-1">
            <span class="${statusColor} font-medium tabular-nums">${statusText}</span>
            <span class="text-slate-400 tabular-nums">${saldo.toLocaleString('pt-BR', { maximumFractionDigits: 0 })} L</span>
          </div>
          <div class="text-slate-400 text-[10px] mt-1 flex items-center justify-between">
            <span>Ullage: <strong class="text-cyan-300 tabular-nums">${ullage.toLocaleString('pt-BR')} L</strong></span>
            <span class="text-purple-300 tabular-nums font-medium">${comp5k}x 5k</span>
          </div>
        </button>
      `;
    });

    container.innerHTML = html;
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
window.auraCockpit = new AuraCockpitController();
