/**
 * AURA IntelligentUI / GenUI Micro-Widgets (Fase 3: P0)
 * Micro-Widget Piloto: ExecutiveDecisionMentorUI (AURA Precision Glass Deluxe)
 * 
 * Arquitetura Zero-Bundler:
 * - Compatível nativamente via <script> no navegador (window.AuraGenUI / window.SecureComponentRegistry)
 * - Compatível com require/module.exports no Node.js para testes automatizados headless
 * 
 * 3 Camadas Concêntricas:
 * - Camada 1: Resumo Executivo e Diagnóstico de Alto Nível (score, status, diagnóstico direto sem ruído)
 * - Camada 2: Visualização Comparativa e Projeção de Impacto (métricas tabulares, tendências, limitações)
 * - Camada 3: Ação Recomendada de 1 Toque e Acoplamento com Companion Canvas (botões táteis auditados)
 */

(function (global) {
  'use strict';

  // =========================================================================
  // 1. UTILITÁRIOS DE SEGURANÇA E SANITIZAÇÃO (OWASP LLM01)
  // =========================================================================

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/\0/g, '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;')
      .replace(/`/g, '&#96;');
  }

  function formatNumber(num, decimals = 2) {
    const n = Number(num);
    if (isNaN(n)) return String(num || '0');
    return n.toLocaleString('pt-BR', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    });
  }

  // =========================================================================
  // 2. COMPONENTE PILOTO: ExecutiveDecisionMentorUI
  // =========================================================================

  class ExecutiveDecisionMentorUI {
    constructor(payload = {}) {
      this.toolCallId = payload.tool_call_id || ('call_' + Date.now());
      this.intent = payload.intent || 'mentoria_decisao';
      this.componentName = payload.component_name || 'render_ExecutiveDecisionMentorUI';
      this.summary = payload.executive_summary || payload.summary_text || '';
      this.props = payload.props || {};
      this.actions = payload.actions || [];
      this.createdAt = payload.created_at || payload.timestamp || new Date().toISOString();
      this.ttlSeconds = Number(payload.ttl_seconds || 900);

      this.state = {
        status: 'proposed', // 'proposed' | 'locked' | 'committed' | 'failed' | 'expired'
        isLocked: false,
        lockedActionId: null,
        optimisticFeedback: null,
        errorMessage: null,
        expandedEvidences: false
      };

      this.element = null;
      this.eventListeners = {};
    }

    /**
     * Monta o elemento DOM principal no padrão AURA Precision Glass Deluxe
     * @returns {HTMLElement|string} Elemento DOM hidratado (ou representação de nó)
     */
    mount() {
      // 1. Gera HTML canônico seguro das 3 camadas
      const htmlContent = this.renderHtml();

      if (typeof document !== 'undefined' && typeof document.createElement === 'function') {
        const container = document.createElement('div');
        container.id = `genui-card-${this.toolCallId}`;
        container.className = 'genui-hydrated-card genui-decision-mentor-card animate-fade-in my-3 rounded-2xl border border-cyan-500/25 bg-slate-900/85 backdrop-blur-xl shadow-2xl p-4 sm:p-5 text-slate-100 transition-all';
        container.setAttribute('data-tool-call-id', this.toolCallId);
        container.setAttribute('data-component', this.componentName);
        container.setAttribute('role', 'region');
        container.setAttribute('aria-label', 'Mentor de Decisões Executivo AURA');
        container.innerHTML = htmlContent;

        this.element = container;
        this.bindEvents(container);
        return container;
      }

      // Fallback em ambiente headless Node.js sem DOM nativo
      return htmlContent;
    }

    /**
     * Camada 1: Resumo Executivo e Diagnóstico de Alto Nível
     */
    renderLayer1() {
      const p = this.props || {};
      const scoreRaw = p.confidence_score !== undefined ? Number(p.confidence_score) : 0.96;
      const scorePct = Math.round(scoreRaw * 100);
      const diagnosisText = p.diagnosis || this.summary || 'Diagnóstico operacional apurado pelo motor analítico da AURA.';

      const scoreColor = scorePct >= 90
        ? 'text-emerald-300 border-emerald-500/40 bg-emerald-500/10'
        : (scorePct >= 75 ? 'text-amber-300 border-amber-500/40 bg-amber-500/10' : 'text-slate-300 border-slate-600 bg-slate-800/40');

      return `
        <div class="genui-layer genui-layer-1 mb-4 pb-3 border-b border-white/10">
          <div class="flex flex-wrap items-center justify-between gap-2 mb-2.5">
            <div class="flex items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse flex-shrink-0"></span>
              <h4 class="text-xs font-mono font-bold tracking-wider text-cyan-300 uppercase">
                AURA Executive Decision Mentor
              </h4>
              <span class="text-[10px] font-mono text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded border border-white/5">
                ${escapeHtml(this.toolCallId.substring(0, 14))}...
              </span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-[11px] font-mono px-2.5 py-0.5 rounded-full border ${scoreColor} font-semibold flex items-center gap-1">
                <svg class="w-3 h-3 inline-block" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                <span>${scorePct}% Confiança</span>
              </span>
            </div>
          </div>
          <div class="p-3 rounded-xl bg-slate-950/50 border border-white/5 space-y-1">
            <span class="text-[10px] uppercase font-bold tracking-wider text-cyan-400 font-mono">Diagnóstico Executivo</span>
            <p class="text-xs sm:text-sm font-sans font-medium text-slate-100 leading-relaxed">
              ${escapeHtml(diagnosisText)}
            </p>
          </div>
        </div>
      `;
    }

    /**
     * Camada 2: Visualização Comparativa e Projeção de Impacto
     */
    renderLayer2() {
      const p = this.props || {};
      const metrics = Array.isArray(p.metrics) ? p.metrics : [];
      const limitations = Array.isArray(p.limitations)
        ? p.limitations.filter(Boolean)
        : (p.limitations ? [String(p.limitations)] : []);
      const impact = p.impact_projection || null;
      const evidences = Array.isArray(p.evidence_items) ? p.evidence_items : [];

      // 2.1 Grade de Métricas Executivas
      let metricsHtml = '';
      if (metrics.length > 0) {
        metricsHtml = `
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3">
            ${metrics.map(m => {
              const lbl = escapeHtml((m && typeof m === 'object' ? m.label : m) || 'Métrica');
              const val = escapeHtml(String((m && typeof m === 'object' ? m.current_value : m) ?? 'N/D'));
              const bench = (m && typeof m === 'object' && m.benchmark_value !== undefined && m.benchmark_value !== null && m.benchmark_value !== '')
                ? escapeHtml(String(m.benchmark_value))
                : null;
              const trend = (m && typeof m === 'object' ? m.trend : 'neutral') || 'neutral';
              const status = (m && typeof m === 'object' ? m.status : 'neutral') || 'neutral';

              const trendIcon = trend === 'up'
                ? '<span class="text-emerald-400">▲</span>'
                : (trend === 'down' ? '<span class="text-rose-400">▼</span>' : '<span class="text-slate-400">▬</span>');

              const statusBorder = status === 'danger'
                ? 'border-rose-500/30 bg-rose-500/5'
                : (status === 'warning' ? 'border-amber-500/30 bg-amber-500/5' : 'border-white/5 bg-slate-950/40');

              return `
                <div class="p-2.5 rounded-xl border ${statusBorder} space-y-1">
                  <div class="flex items-center justify-between text-[10px] text-slate-400 font-medium">
                    <span class="truncate pr-1">${lbl}</span>
                    ${trendIcon}
                  </div>
                  <div class="text-sm sm:text-base font-bold font-mono text-white tabular-nums tracking-tight">
                    ${val}
                  </div>
                  ${bench ? `<div class="text-[10px] text-slate-500 truncate font-mono">Meta: ${bench}</div>` : ''}
                </div>
              `;
            }).join('')}
          </div>
        `;
      }

      // 2.2 Projeção de Impacto Financeiro / Operacional (suporta ganho, perda ou neutro)
      let impactHtml = '';
      if (impact) {
        const impactSummary = (typeof impact === 'object' && impact !== null) ? (impact.summary || '') : String(impact || '');
        const hasImpactVal = (typeof impact === 'object' && impact !== null && impact.estimated_financial_impact !== undefined && impact.estimated_financial_impact !== null);
        const rawImpactVal = hasImpactVal ? Number(impact.estimated_financial_impact) : null;
        let impactBadge = '';
        if (rawImpactVal !== null && !isNaN(rawImpactVal)) {
          if (rawImpactVal > 0) {
            impactBadge = `<span class="text-xs font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">+R$ ${formatNumber(rawImpactVal)}</span>`;
          } else if (rawImpactVal < 0) {
            impactBadge = `<span class="text-xs font-mono font-bold text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/20">-R$ ${formatNumber(Math.abs(rawImpactVal))}</span>`;
          } else {
            impactBadge = `<span class="text-xs font-mono font-bold text-slate-300 bg-slate-800/60 px-2 py-0.5 rounded border border-slate-700/40">R$ 0,00</span>`;
          }
        }
        const timeframe = (typeof impact === 'object' && impact !== null && impact.timeframe) ? escapeHtml(impact.timeframe) : 'Estimado';

        impactHtml = `
          <div class="p-3 rounded-xl bg-gradient-to-r from-cyan-950/30 via-slate-950/50 to-purple-950/30 border border-cyan-500/20 mb-3 space-y-1">
            <div class="flex items-center justify-between">
              <span class="text-[10px] uppercase font-bold tracking-wider text-purple-300 font-mono flex items-center gap-1.5">
                <svg class="w-3.5 h-3.5 text-cyan-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
                <span>Projeção de Impacto (${timeframe})</span>
              </span>
              ${impactBadge}
            </div>
            <p class="text-xs text-slate-200 leading-relaxed font-sans">
              ${escapeHtml(impactSummary)}
            </p>
          </div>
        `;
      }

      // 2.3 Aviso de Limitações dos Dados (Governança & Risco)
      let limitationsHtml = '';
      if (limitations.length > 0) {
        limitationsHtml = `
          <div class="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 mb-3 text-amber-200/90 text-[11px] leading-relaxed flex items-start gap-2">
            <span class="text-amber-400 font-bold flex-shrink-0 mt-0.5">⚠</span>
            <div class="space-y-0.5">
              <span class="font-bold text-[10px] uppercase tracking-wider font-mono text-amber-300">Limitações do Dado Apurado:</span>
              <ul class="list-disc list-inside space-y-0.5 text-slate-300 text-[11px]">
                ${limitations.map(l => `<li>${escapeHtml(l)}</li>`).join('')}
              </ul>
            </div>
          </div>
        `;
      }

      // 2.4 Evidências Analíticas para Inspeção Aprofundada
      let evidencesHtml = '';
      if (evidences.length > 0) {
        const isExpanded = !!this.state.expandedEvidences;
        evidencesHtml = `
          <div class="mt-2 text-[11px] space-y-1.5">
            <button type="button" class="genui-toggle-evidence text-[10px] font-mono text-cyan-300 hover:text-cyan-200 flex items-center gap-1 focus:outline-none">
              <span>${isExpanded ? '▲ Ocultar Evidências' : `▼ Memória de Cálculo & Evidências (${evidences.length} itens)`}</span>
            </button>
            <div class="genui-evidence-list space-y-1 ${isExpanded ? '' : 'hidden'}">
              ${evidences.map(ev => {
                const title = typeof ev === 'object' && ev !== null ? escapeHtml(ev.title || '') : escapeHtml(String(ev ?? ''));
                const detail = typeof ev === 'object' && ev !== null ? escapeHtml(ev.detail || '') : '';
                const source = typeof ev === 'object' && ev !== null && ev.source ? escapeHtml(ev.source) : '';
                return `
                  <div class="p-2 rounded-lg bg-slate-950/40 border border-white/5 flex items-center justify-between text-[11px]">
                    <div>
                      <span class="font-semibold text-slate-200">${title}</span>
                      ${detail ? `<span class="text-slate-400"> • ${detail}</span>` : ''}
                    </div>
                    ${source ? `<span class="text-[10px] font-mono text-slate-500 bg-slate-900 px-1.5 py-0.5 rounded border border-white/5">${source}</span>` : ''}
                  </div>
                `;
              }).join('')}
            </div>
          </div>
        `;
      }

      return `
        <div class="genui-layer genui-layer-2 mb-4">
          ${metricsHtml}
          ${impactHtml}
          ${limitationsHtml}
          ${evidencesHtml}
        </div>
      `;
    }

    /**
     * Camada 3: Ação Recomendada de 1 Toque e Acoplamento com Companion Canvas
     */
    renderLayer3() {
      const actions = Array.isArray(this.actions) && this.actions.length > 0
        ? this.actions
        : (this.props && Array.isArray(this.props.suggested_actions) ? this.props.suggested_actions : []);

      const isLocked = this.state.isLocked;
      const feedback = this.state.optimisticFeedback;

      let feedbackBadge = '';
      if (feedback) {
        feedbackBadge = `
          <div class="genui-optimistic-badge p-2.5 mb-2.5 rounded-xl bg-emerald-500/15 border border-emerald-500/40 text-emerald-200 text-xs flex items-center gap-2 animate-fade-in">
            <span class="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
            <span class="font-medium">${escapeHtml(feedback)}</span>
          </div>
        `;
      }

      let errorBadge = '';
      if (this.state.errorMessage) {
        errorBadge = `
          <div class="genui-error-badge p-2.5 mb-2.5 rounded-xl bg-rose-500/15 border border-rose-500/40 text-rose-200 text-xs flex items-center justify-between gap-2 animate-fade-in">
            <span>${escapeHtml(this.state.errorMessage)}</span>
            <button type="button" class="genui-dismiss-error text-[10px] text-rose-300 underline">Fechar</button>
          </div>
        `;
      }

      // Constrói botões de ação tátil
      let buttonsHtml = '';
      if (actions.length > 0) {
        buttonsHtml = actions.map(act => {
          const actId = escapeHtml(act.action_id || ('act_' + Math.random().toString(36).substring(2, 8)));
          const label = escapeHtml(act.label || 'Ação Recomendada');
          const variant = act.variant || 'primary';
          const actType = act.action_type || 'mutation';

          let btnClass = 'px-3 py-2 rounded-xl text-xs font-semibold font-sans transition-all flex items-center justify-center gap-1.5 shadow-sm ';
          if (variant === 'primary') {
            btnClass += 'bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold border border-cyan-400/30 ';
          } else if (variant === 'secondary') {
            btnClass += 'bg-slate-800 hover:bg-slate-700 text-cyan-200 border border-cyan-500/30 ';
          } else if (variant === 'danger') {
            btnClass += 'bg-rose-600 hover:bg-rose-500 text-white border border-rose-400/30 ';
          } else {
            // ghost
            btnClass += 'bg-slate-900/60 hover:bg-slate-800 text-slate-300 border border-white/10 ';
          }

          if (isLocked) {
            btnClass += 'opacity-50 pointer-events-none cursor-not-allowed ';
          }

          return `
            <button type="button"
                    class="genui-action-btn ${btnClass}"
                    data-action-id="${actId}"
                    data-action-type="${escapeHtml(actType)}"
                    data-tool-call-id="${escapeHtml(this.toolCallId)}"
                    ${isLocked ? 'disabled' : ''}>
              <span>${label}</span>
            </button>
          `;
        }).join('');
      } else {
        // Ação padrão caso nenhuma venha no payload
        buttonsHtml = `
          <button type="button"
                  class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 font-bold hover:brightness-110"
                  data-action-id="act_default_1"
                  data-action-type="inspection"
                  data-tool-call-id="${escapeHtml(this.toolCallId)}">
            <span>⚡ Aplicar Recomendações Prioritárias</span>
          </button>
          <button type="button"
                  class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-slate-800 text-cyan-200 border border-cyan-500/30 hover:bg-slate-700"
                  data-action-id="act_default_canvas"
                  data-action-type="inspection"
                  data-tool-call-id="${escapeHtml(this.toolCallId)}">
            <span>🔍 Projetar no Companion Canvas</span>
          </button>
        `;
      }

      return `
        <div class="genui-layer genui-layer-3 pt-3 border-t border-white/10">
          ${feedbackBadge}
          ${errorBadge}
          <div class="flex flex-wrap gap-2">
            ${buttonsHtml}
          </div>
        </div>
      `;
    }

    /**
     * Serializa o HTML completo em 3 camadas concêntricas
     */
    renderHtml() {
      return `
        <div class="genui-decision-mentor-inner">
          ${this.renderLayer1()}
          ${this.renderLayer2()}
          ${this.renderLayer3()}
        </div>
      `;
    }

    /**
     * Vincula listeners de evento no DOM aos botões da Camada 3 e expansores
     */
    bindEvents(rootElement) {
      if (!rootElement || typeof rootElement.querySelectorAll !== 'function') return;

      // 1. Toggle de evidências analíticas com proteção contra múltiplos binds
      const toggleBtn = rootElement.querySelector('.genui-toggle-evidence');
      const listEl = rootElement.querySelector('.genui-evidence-list');
      if (toggleBtn && listEl && !toggleBtn._hasBoundClick) {
        toggleBtn._hasBoundClick = true;
        toggleBtn.addEventListener('click', () => {
          this.state.expandedEvidences = !this.state.expandedEvidences;
          listEl.classList.toggle('hidden', !this.state.expandedEvidences);
          const count = (this.props && Array.isArray(this.props.evidence_items)) ? this.props.evidence_items.length : 0;
          toggleBtn.textContent = this.state.expandedEvidences
            ? '▲ Ocultar Evidências'
            : `▼ Memória de Cálculo & Evidências (${count} itens)`;
        });
      }

      // 2. Dismiss de erro com proteção contra múltiplos binds
      const dismissBtn = rootElement.querySelector('.genui-dismiss-error');
      if (dismissBtn && !dismissBtn._hasBoundClick) {
        dismissBtn._hasBoundClick = true;
        dismissBtn.addEventListener('click', () => {
          this.state.errorMessage = null;
          this.refreshLayer3();
        });
      }

      // 3. Botões de ação da Camada 3 com proteção contra múltiplos binds
      const actionBtns = rootElement.querySelectorAll('.genui-action-btn');
      actionBtns.forEach(btn => {
        if (!btn._hasBoundClick) {
          btn._hasBoundClick = true;
          btn.addEventListener('click', (e) => {
            const actionId = btn.getAttribute('data-action-id');
            const actionType = btn.getAttribute('data-action-type');
            this.handleActionClick(actionId, actionType, btn, e);
          });
        }
      });
    }

    /**
     * Processa clique em botão de ação da Camada 3 com State Locking e Optimistic UI
     */
    async handleActionClick(actionId, actionType, btnElement, event) {
      if (this.state.isLocked) return;

      // 1. Ações de inspeção no Companion Canvas com proteção de debounce
      if (actionType === 'inspection' || (btnElement && btnElement.textContent.includes('Canvas'))) {
        const now = Date.now();
        if (now - (this._canvasDebounce || 0) < 800) {
          return;
        }
        this._canvasDebounce = now;
        this.projectToCanvas();
        return;
      }

      // 2. Ação de mutação / recomendação transacional
      const actionDef = (this.actions || []).find(a => a.action_id === actionId) || {
        action_id: actionId,
        label: btnElement ? btnElement.textContent.trim() : 'Ação',
        payload: { intent: this.intent, tool_call_id: this.toolCallId }
      };

      // Aplica State Locking imediato e Optimistic UI (F4-02 & F4-03)
      this.applyOptimisticState(actionId, `Autorizando: ${actionDef.label}...`);

      // Dispara evento customizado auditado para controladores externos
      if (typeof window !== 'undefined' && typeof window.dispatchEvent === 'function') {
        try {
          const customEv = new CustomEvent('aura:action-click', {
            detail: {
              toolCallId: this.toolCallId,
              actionId: actionId,
              action: actionDef,
              props: this.props
            },
            bubbles: true
          });
          if (btnElement && typeof btnElement.dispatchEvent === 'function') {
            btnElement.dispatchEvent(customEv);
          } else {
            window.dispatchEvent(customEv);
          }
        } catch (_) {}
      }

      // Se houver cliente de API disponível no browser, despacha RPC
      if (typeof window !== 'undefined' && window.auraApi && typeof window.auraApi.executeAction === 'function') {
        try {
          const res = await window.auraApi.executeAction(actionId, {
            tool_call_id: this.toolCallId,
            payload: actionDef.payload
          });
          this.state.status = 'committed';
          this.state.optimisticFeedback = `✔ Ação Homologada com Sucesso (Voucher: ${res?.voucher_id || 'OK'})`;
          this.refreshLayer3();
        } catch (err) {
          this.rollbackOptimisticState(err?.message || 'Falha na comunicação com o ERP.');
        }
      }
    }

    /**
     * Aplica mutação otimista visual e trava botões contra cliques concorrentes
     */
    applyOptimisticState(actionId, feedbackText = 'Processando autorização no ERP...') {
      this.state.isLocked = true;
      this.state.lockedActionId = actionId;
      this.state.optimisticFeedback = feedbackText;
      this.state.errorMessage = null;
      this.refreshLayer3();
    }

    /**
     * Reverte estado otimista em caso de falha com restauração graciosa
     */
    rollbackOptimisticState(errorMsg = 'Não foi possível comunicar com o ERP central.') {
      this.state.isLocked = false;
      this.state.lockedActionId = null;
      this.state.optimisticFeedback = null;
      this.state.errorMessage = errorMsg;
      this.refreshLayer3();
    }

    /**
     * Redesenha a Camada 3 no DOM após alteração de estado reativo
     */
    refreshLayer3() {
      if (!this.element || typeof this.element.querySelector !== 'function') return;
      const layer3El = this.element.querySelector('.genui-layer-3');
      if (layer3El) {
        const temp = document.createElement('div');
        temp.innerHTML = this.renderLayer3().trim();
        const newLayer3 = temp.firstElementChild;
        if (newLayer3) {
          layer3El.parentNode.replaceChild(newLayer3, layer3El);
          this.bindEvents(this.element);
        }
      }
    }

    /**
     * Projeta o relatório aprofundado no Companion Canvas lateral (window.auraAuxPanel)
     */
    projectToCanvas() {
      if (typeof window !== 'undefined' && window.auraAuxPanel && typeof window.auraAuxPanel.projectArtifact === 'function') {
        try {
          window.auraAuxPanel.projectArtifact({
            id: 'art_genui_' + this.toolCallId,
            containerId: null,
            toolName: this.componentName,
            intent: this.intent,
            data: this.props,
            html: this.renderHtml(),
            autoOpen: true
          });
        } catch (e) {
          console.warn('[ExecutiveDecisionMentorUI] Erro ao projetar no Companion Canvas:', e);
        }
      } else if (typeof window !== 'undefined' && window.auraChat && typeof window.auraChat.showToast === 'function') {
        window.auraChat.showToast('Companion Canvas indisponível ou inicializando.', 'info');
      }
    }
  }

  // Alias para compatibilidade canônica com especificações do roadmap
  const ExecutiveBriefingWidget = ExecutiveDecisionMentorUI;

  // =========================================================================
  // 3. REGISTRO NO SecureComponentRegistry & EXPORTAÇÕES ZERO-BUNDLER
  // =========================================================================

  function registerWidgets(reg) {
    if (!reg || typeof reg.registerComponent !== 'function') return;

    const metadata = {
      intent: 'mentoria_decisao',
      version: '1.0.0',
      description: 'Micro-Widget Piloto do Mentor de Decisões Executivo (P0)',
      layers: ['executive_summary', 'comparative_kpis', 'action_sheets']
    };

    try {
      reg.registerComponent('render_ExecutiveDecisionMentorUI', ExecutiveDecisionMentorUI, metadata, { allowOverwrite: true });
    } catch (_) {}

    try {
      reg.registerComponent('render_ExecutiveBriefingUI', ExecutiveDecisionMentorUI, metadata, { allowOverwrite: true });
    } catch (_) {}

    try {
      reg.registerComponent('ExecutiveDecisionMentorUI', ExecutiveDecisionMentorUI, metadata, { allowOverwrite: true });
    } catch (_) {}

    try {
      reg.registerComponent('ExecutiveBriefingWidget', ExecutiveBriefingWidget, metadata, { allowOverwrite: true });
    } catch (_) {}
  }

  // 1. Registro automático no catálogo global do navegador
  if (typeof window !== 'undefined') {
    if (window.SecureComponentRegistry) {
      registerWidgets(window.SecureComponentRegistry);
    }
    if (window.AuraGenUI && window.AuraGenUI.registry) {
      registerWidgets(window.AuraGenUI.registry);
    }

    if (!window.AuraGenUI) {
      window.AuraGenUI = {};
    }
    window.AuraGenUI.ExecutiveDecisionMentorUI = ExecutiveDecisionMentorUI;
    window.AuraGenUI.ExecutiveBriefingWidget = ExecutiveBriefingWidget;

    // Escuta evento de inicialização deferida do registry
    window.addEventListener('aura:genui-ready', (evt) => {
      if (evt?.detail?.registry) {
        registerWidgets(evt.detail.registry);
      }
    });
  }

  // 2. Exportação CommonJS para testes automatizados headless (Node.js)
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
      ExecutiveDecisionMentorUI,
      ExecutiveBriefingWidget,
      registerWidgets,
      escapeHtml
    };
  }

})(typeof globalThis !== 'undefined' ? globalThis : (typeof window !== 'undefined' ? window : this));
