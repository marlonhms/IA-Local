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
          <div class="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto mb-3">
            <i data-lucide="fuel" class="w-6 h-6 text-emerald-400"></i>
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
              <i data-lucide="sparkles" class="w-4 h-4 text-purple-400"></i>
              <span>Perguntar no Chat</span>
            </button>
          </div>
        </div>`;
    }

    const splitContainer = document.getElementById('split-tanks-grid');
    if (splitContainer && (!this.tanksData || this.tanksData.length === 0)) {
      splitContainer.innerHTML = `
        <div class="col-span-full py-6 text-center text-slate-400 font-mono text-xs glass-panel p-4">
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
  }

  /**
   * Recarrega todos os dados operacionais em paralelo com máxima velocidade
   */
  async refreshAllData() {
    if (this.isLoading) return;
    this.isLoading = true;
    this.setRefreshSpinner(true);

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
              ⚠️ Dados volumétricos temporariamente indisponíveis no momento.
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
        if (b) b.innerHTML = '<div class="text-slate-500 font-mono text-xs col-span-full py-2">Sem sinal de bicos da pista (CBC04).</div>';
        const f = document.getElementById('cockpit-frentistas-table');
        if (f) f.innerHTML = '<div class="text-slate-500 font-mono text-xs py-2">Sem dados de frentistas disponíveis.</div>';
        const a = document.getElementById('cockpit-anomalias-list');
        if (a) a.innerHTML = '<div class="text-slate-500 font-mono text-xs py-2">Pista desconectada.</div>';
      }

      if (turnoRes && turnoRes.data) {
        this.turnoData = turnoRes.data;
        this.renderTurnoCard(turnoRes.data);
      } else if (!this.turnoData) {
        const t = document.getElementById('cockpit-turno-content');
        if (t) t.innerHTML = '<div class="text-slate-500 font-mono text-xs py-2">Turno não localizado ou caixa fechado.</div>';
      }

      if (lmcRes && lmcRes.data) {
        this.lmcData = lmcRes.data;
        this.renderLmcCard(lmcRes.data);
      } else if (!this.lmcData) {
        const l = document.getElementById('cockpit-lmc-content');
        if (l) l.innerHTML = '<div class="text-slate-500 font-mono text-xs py-2">Livro LMC não consultado.</div>';
      }

      if (combosRes && combosRes.data) {
        this.combosData = combosRes.data;
        this.renderTopCombosBanner(combosRes.data);
      } else if (!this.combosData) {
        const c = document.getElementById('cockpit-combos-container');
        if (c) c.innerHTML = '<div class="text-slate-500 font-mono text-xs col-span-full py-2">Sem regras de cesta registradas.</div>';
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
        <div class="col-span-full py-8 text-center text-slate-400 font-mono text-sm">
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

      // Alerta crítico sobrepõe cor do card
      if (isCritical && !isInativo) {
        borderAccent = 'border-rose-500/60 shadow-lg shadow-rose-950/20';
      }

      html += `
        <div class="glass-panel p-4 flex flex-col justify-between relative overflow-hidden transition-all hover:scale-[1.01] ${borderAccent}">
          <!-- Topo do Card -->
          <div class="flex items-start justify-between mb-3">
            <div>
              <div class="flex items-center gap-2">
                <span class="font-mono text-xs font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                  TQ-${cod}
                </span>
                <span class="text-xs font-semibold px-2 py-0.5 rounded border ${tagBg}">
                  ${comb}
                </span>
              </div>
              <div class="mt-1 text-slate-400 text-xs font-mono">
                Bicos: ${(tank.bicos_conectados && tank.bicos_conectados.length) ? tank.bicos_conectados.join(', ') : 'Nenhum'}
              </div>
            </div>

            <!-- Badge de Status de Risco -->
            <div>
              ${isInativo ? `
                <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-800 text-slate-400 border border-slate-700">
                  INATIVO
                </span>
              ` : isCritical ? `
                <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-500/20 text-rose-300 border border-rose-500/40 animate-pulse">
                  CRÍTICO &lt;15%
                </span>
              ` : pct < 30 ? `
                <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">
                  ATENÇÃO
                </span>
              ` : `
                <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                  REGULAR
                </span>
              `}
            </div>
          </div>

          <!-- Centro: Medidor Cilíndrico de Fluido + Métricas -->
          <div class="flex items-center gap-4 my-2">
            <!-- Cilindro 3D -->
            <div class="tank-gauge-container flex-shrink-0">
              <div class="tank-critical-line"></div>
              <div class="tank-liquid ${fuelClass}" style="height: ${isInativo ? 0 : pct}%;"></div>
            </div>

            <!-- Dados Volumétricos -->
            <div class="flex-1 space-y-1.5 font-mono text-xs">
              <div class="flex items-baseline justify-between border-b border-slate-800/80 pb-1">
                <span class="text-slate-400">Saldo Atual:</span>
                <span class="font-bold text-sm ${isCritical ? 'text-rose-300' : 'text-slate-100'}">
                  ${saldo.toLocaleString('pt-BR', { maximumFractionDigits: 0 })} L
                </span>
              </div>

              <div class="flex items-baseline justify-between border-b border-slate-800/80 pb-1">
                <span class="text-slate-400">Capacidade:</span>
                <span class="text-slate-300">${cap.toLocaleString('pt-BR', { maximumFractionDigits: 0 })} L</span>
              </div>

              <div class="flex items-baseline justify-between border-b border-slate-800/80 pb-1">
                <span class="text-slate-400">Nível:</span>
                <span class="font-bold ${pct < 15 ? 'text-rose-400' : pct < 35 ? 'text-amber-400' : 'text-emerald-400'}">
                  ${pct.toFixed(1)}%
                </span>
              </div>

              <div class="flex items-baseline justify-between border-b border-slate-800/80 pb-1">
                <span class="text-slate-400">Espaço Livre:</span>
                <span class="text-cyan-300 font-semibold">${ullage.toLocaleString('pt-BR', { maximumFractionDigits: 0 })} L</span>
              </div>

              <div class="flex items-baseline justify-between">
                <span class="text-slate-400">Comporta Carreta:</span>
                <span class="text-purple-300 font-bold">${comp5k}x 5.000 L</span>
              </div>
            </div>
          </div>

          <!-- Rodapé do Card: Autonomia & Ação Rápida -->
          <div class="mt-3 pt-2.5 border-t border-slate-800 flex items-center justify-between">
            <div class="font-mono text-[11px]">
              ${isInativo ? `
                <span class="text-slate-500">Sem consumo registrado</span>
              ` : isCritical ? `
                <span class="text-rose-400 font-semibold">
                  Autonomia: ~${horasAutonomia.toFixed(0)}h (${diasAutonomia.toFixed(1)}d)
                </span>
              ` : `
                <span class="text-slate-300">
                  Autonomia: ~${diasAutonomia.toFixed(1)} dias (${horasAutonomia.toFixed(0)}h)
                </span>
              `}
            </div>

            <button 
              onclick="window.auraApp.askAboutTank('${cod}', '${comb}')"
              class="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-cyan-400 hover:text-cyan-300 text-[11px] font-mono flex items-center gap-1 transition-colors"
              title="Perguntar à AURA sobre este tanque">
              <span>Perguntar</span>
              <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
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
        <div class="flex flex-wrap items-center gap-4 text-xs font-mono text-slate-300">
          <div>Tanques Ativos: <strong class="text-emerald-400">${totalAtivos}</strong></div>
          <div>Em Risco Crítico: <strong class="text-rose-400">${emRisco}</strong></div>
          <div>Capacidade Total: <strong class="text-slate-200">${capTot.toLocaleString('pt-BR')} L</strong></div>
          <div>Saldo Geral: <strong class="text-slate-200">${saldoTot.toLocaleString('pt-BR')} L</strong></div>
          <div>Ocupação Média: <strong class="text-cyan-400">${ocupMedia.toFixed(1)}%</strong></div>
          <div>Ullage Total: <strong class="text-purple-300">${ullageTot.toLocaleString('pt-BR')} L</strong></div>
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
          <div class="p-2.5 rounded-lg border ${isLento ? 'bg-amber-950/20 border-amber-500/50' : isInativo ? 'bg-slate-900/40 border-slate-800' : 'bg-slate-900/80 border-slate-800'} flex flex-col justify-between font-mono text-xs">
            <div class="flex items-center justify-between">
              <span class="font-bold text-slate-200">Bico ${b.bico}</span>
              <span class="text-[10px] text-slate-400">Bomba ${b.bomba_fisica}</span>
            </div>
            <div class="text-[11px] text-slate-400 truncate mt-1">${b.combustivel}</div>
            
            <div class="mt-2 pt-1 border-t border-slate-800 flex items-center justify-between">
              <span class="text-slate-500 text-[10px]">Vazão:</span>
              <span class="font-bold ${isLento ? 'text-amber-400' : isInativo ? 'text-slate-500' : 'text-emerald-400'}">
                ${isInativo ? '0.0' : vazao.toFixed(1)} L/min
              </span>
            </div>
            
            ${isLento ? `
              <div class="mt-1 text-[9px] text-amber-400 font-semibold flex items-center gap-1">
                <span>⚠️ Filtro Lento</span>
              </div>
            ` : ''}
          </div>
        `;
      });
      bicosContainer.innerHTML = bicosHtml || '<div class="text-slate-500 text-xs">Sem dados de bicos</div>';
    }

    // 2. Ranking de Frentistas
    const frentistasContainer = document.getElementById('cockpit-frentistas-table');
    if (frentistasContainer && pista.ranking_frentistas) {
      let frentHtml = `
        <table class="w-full text-left font-mono text-xs">
          <thead>
            <tr class="text-slate-400 border-b border-slate-800 text-[11px]">
              <th class="pb-2">#</th>
              <th class="pb-2">Frentista</th>
              <th class="pb-2 text-right">Litros</th>
              <th class="pb-2 text-right">Faturamento</th>
              <th class="pb-2 text-right">Ticket Médio</th>
              <th class="pb-2 text-right">Conv. Aditivada</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-800/60">
      `;

      pista.ranking_frentistas.forEach((f, idx) => {
        const conv = Number(f.conversao_aditivada_pct || 0);
        frentHtml += `
          <tr class="hover:bg-slate-800/30 transition-colors">
            <td class="py-2 text-slate-400">${idx + 1}</td>
            <td class="py-2 font-semibold text-slate-200">
              ${f.nome}
              ${f.destaque_performance ? `<span class="block text-[10px] text-emerald-400 font-normal">${f.destaque_performance}</span>` : ''}
            </td>
            <td class="py-2 text-right text-slate-300">${Number(f.total_litros || 0).toFixed(1)} L</td>
            <td class="py-2 text-right text-emerald-400 font-semibold">R$ ${Number(f.faturamento_reais || 0).toFixed(2)}</td>
            <td class="py-2 text-right text-slate-300">R$ ${Number(f.ticket_medio_reais || 0).toFixed(2)}</td>
            <td class="py-2 text-right">
              <span class="px-1.5 py-0.5 rounded text-[10px] ${conv > 15 ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-slate-800 text-slate-400'}">
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
        anomaliasContainer.innerHTML = '<div class="text-xs text-emerald-400 font-mono py-2">✓ Nenhuma anomalia crítica ou fraude na pista detectada.</div>';
      } else {
        let anomHtml = '';
        pista.anomalias_detectadas.slice(0, 5).forEach(a => {
          anomHtml += `
            <div class="p-2 rounded bg-slate-900 border border-slate-800 text-xs font-mono space-y-0.5">
              <div class="flex items-center justify-between text-[11px]">
                <span class="font-bold ${a.gravidade === 'ALTA' ? 'text-rose-400' : 'text-amber-400'}">
                  [${a.tipo}] Bico ${a.bico}
                </span>
                <span class="text-slate-400">${a.data_hora || ''}</span>
              </div>
              <div class="text-slate-300 text-[11px]">${a.motivo}</div>
              <div class="text-slate-400 text-[10px]">Volume: ${a.litros} L | Total: R$ ${Number(a.total_reais || 0).toFixed(2)} | Frentista: ${a.frentista}</div>
            </div>
          `;
        });
        anomaliasContainer.innerHTML = anomHtml;
      }
    }
  }

  /**
   * Renderiza card de Fechamento de Turno
   */
  renderTurnoCard(turno) {
    const el = document.getElementById('cockpit-turno-content');
    if (!el || !turno.resumo_executivo) return;

    const r = turno.resumo_executivo;
    const score = Number(r.score_conformidade_pct || 0);

    el.innerHTML = `
      <div class="space-y-3 font-mono text-xs">
        <div class="flex items-center justify-between">
          <span class="text-slate-400">Status da Conciliação:</span>
          <span class="font-bold px-2 py-0.5 rounded text-[11px] ${score >= 95 ? 'bg-emerald-500/20 text-emerald-300' : 'bg-cyan-500/20 text-cyan-300'}">
            ${r.status_conciliacao || 'Turno em Andamento'}
          </span>
        </div>

        <div class="grid grid-cols-2 gap-2 p-2 rounded bg-slate-900/80 border border-slate-800">
          <div>
            <div class="text-slate-400 text-[10px]">Faturamento Pista CBC04</div>
            <div class="text-sm font-bold text-slate-100">R$ ${Number(r.faturamento_pista_total || 0).toFixed(2)}</div>
          </div>
          <div>
            <div class="text-slate-400 text-[10px]">Faturamento Caixa PDV</div>
            <div class="text-sm font-bold text-cyan-300">R$ ${Number(r.faturamento_caixa_total || 0).toFixed(2)}</div>
          </div>
        </div>

        <div class="flex items-center justify-between text-xs border-t border-slate-800 pt-2">
          <span class="text-slate-400">Divergência Pista vs PDV:</span>
          <span class="font-bold ${Number(r.diferenca_financeira_caixa || 0) < 0 ? 'text-amber-400' : 'text-emerald-400'}">
            R$ ${Number(r.diferenca_financeira_caixa || 0).toFixed(2)}
          </span>
        </div>

        <div class="text-[11px] text-slate-400 bg-slate-900/40 p-2 rounded border border-slate-800/80">
          ${r.diagnostico_caixa || 'Conferência de turno em andamento.'}
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
      <div class="space-y-3 font-mono text-xs">
        <div class="flex items-center justify-between">
          <span class="text-slate-400">Conformidade Portaria 26/1992:</span>
          <span class="font-bold px-2 py-0.5 rounded text-[11px] ${isConforme ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' : 'bg-rose-500/20 text-rose-300 border border-rose-500/40'}">
            ${isConforme ? '✓ CONFORME ANP (±0.6%)' : '⚠️ ALERTA VOLUMÉTRICO'}
          </span>
        </div>

        <div class="grid grid-cols-2 gap-2 p-2 rounded bg-slate-900/80 border border-slate-800">
          <div>
            <div class="text-slate-400 text-[10px]">Tanques Auditados</div>
            <div class="text-sm font-bold text-slate-100">${r.total_tanques_analisados || 0} tanques</div>
          </div>
          <div>
            <div class="text-slate-400 text-[10px]">Variação Física vs Livro</div>
            <div class="text-sm font-bold ${isConforme ? 'text-emerald-400' : 'text-rose-400'}">
              ${(r.variacao_volumetrica_geral_pct || 0).toFixed(2)}%
            </div>
          </div>
        </div>

        <div class="text-[11px] text-slate-400">
          Estoque Físico Total: <strong class="text-slate-200">${(r.total_estoque_fisico_litros || 0).toLocaleString('pt-BR')} L</strong>
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
        <div class="p-3 rounded-lg bg-purple-950/20 border border-purple-500/30 flex flex-col justify-between font-mono text-xs">
          <div>
            <div class="flex items-center justify-between text-[11px] mb-1">
              <span class="text-purple-300 font-bold">LIFT: ${lift.toFixed(1)}x</span>
              <span class="text-slate-400">Confiança: ${conf.toFixed(0)}%</span>
            </div>
            <div class="text-slate-200 font-semibold">${c.produto_origem?.nompro}</div>
            <div class="text-emerald-400 text-[11px] mt-0.5">↳ + ${c.produto_recomendado?.nompro}</div>
          </div>

          <div class="mt-2 pt-2 border-t border-purple-900/40 text-[11px] text-slate-400">
            <span class="text-slate-300">${c.script_sugerido_caixa || ''}</span>
          </div>
        </div>
      `;
    });

    el.innerHTML = html;
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
      const ullage = Number(t.espaco_livre_ullage_litros || 0);
      const comp5k = t.compartimentos_5k || 0;
      const horasAutonomia = Number(t.autonomia_runout_horas || 0);

      let statusColor = 'text-emerald-400';
      let statusText = `Normal (~${horasAutonomia.toFixed(0)}h)`;
      let borderAccent = 'hover:border-emerald-500/50';

      if (isCritical) {
        statusColor = 'text-rose-400';
        statusText = `Crítico <15% (~${horasAutonomia.toFixed(0)}h)`;
        borderAccent = 'border-rose-500/40 hover:border-rose-400';
      } else if (pct < 35) {
        statusColor = 'text-amber-400';
        statusText = `Atenção (~${horasAutonomia.toFixed(0)}h)`;
        borderAccent = 'border-amber-500/30 hover:border-amber-400';
      }

      html += `
        <button onclick="window.auraApp.askAboutTank('${cod}', '${comb}')" class="p-3 rounded-lg bg-slate-900 border ${borderAccent} text-left font-mono text-xs transition-all group">
          <div class="flex items-center justify-between">
            <span class="font-bold text-slate-200 group-hover:text-white">TQ-${cod} ${comb}</span>
            <span class="text-[10px] font-bold ${statusColor}">${pct.toFixed(0)}%</span>
          </div>
          <div class="${statusColor} font-semibold mt-1">${statusText}</div>
          <div class="text-slate-400 text-[10px] mt-0.5">Ullage: ${ullage.toLocaleString('pt-BR')} L (${comp5k}x 5k)</div>
        </button>
      `;
    });

    container.innerHTML = html;
  }
}

// Instância singleton global
window.auraCockpit = new AuraCockpitController();
