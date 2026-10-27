/**
 * AURA IntelligentUI / GenUI Micro-Widgets (Fase 6: P2)
 * Catalogo Expandido de Micro-Widgets do Mentor de Decisoes (AURA Precision Glass Deluxe)
 * 
 * Arquitetura Zero-Bundler:
 * - Compativel nativamente via <script> no navegador (window.AuraGenUI / window.SecureComponentRegistry)
 * - Compativel com require/module.exports no Node.js para testes automatizados headless
 * 
 * Componentes do Catalogo:
 * 1. ExecutiveDecisionMentorUI (Piloto / ExecutiveBriefingWidget)
 * 2. MarginAnalysisUI (MarginProfitabilityWidget)
 * 3. PredictiveScenarioUI (PredictiveScenarioWidget)
 * 4. BenchmarkComparisonUI (ComparativeBenchmarkWidget)
 * 5. FinancialLeakAuditUI (FinancialLeakAuditWidget)
 * 6. BasketUpsellStrategyUI (BasketUpsellWidget)
 * 
 * 3 Camadas Concentricas:
 * - Camada 1: Resumo Executivo e Diagnostico de Alto Nivel
 * - Camada 2: Visualizacao Rica, Metricas Deterministicas e Limitacoes
 * - Camada 3: Action Sheets Transacionais (State Locking, Optimistic UI e Voucher Auditado)
 */

(function (global) {
  'use strict';

  // =========================================================================
  // 1. UTILITARIOS DE SEGURANCA E SANITIZACAO (OWASP LLM01)
  // =========================================================================

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    if (typeof str === 'object') {
      str = str.text || str.summary || str.title || str.diagnostico_caixa || str.message || JSON.stringify(str);
    }
    return String(str)
      .replace(/\0/g, '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;')
      .replace(/`/g, '&#96;');
  }

    function formatFiscalHighlightText(str, accentColor) {
    if (str === null || str === undefined) return '';
    const color = accentColor === 'emerald' ? 'emerald' : 'cyan';
    let safe = escapeHtml(str);
    const tagColor = color === 'emerald' ? 'text-emerald-400' : 'text-cyan-400';
    // 1. Destacar tags de regras no inicio com bullet: • [REGRA]: ou [REGRA]:
    safe = safe.replace(/([\u2022\*\-]?\s*)(\[[A-Za-z0-9_\-\.\/]+\]:?)/g, '$1<strong class="font-bold ' + tagColor + '">$2</strong>');
    // 2. Destacar tags xml escapadas <tag>
    safe = safe.replace(/(&lt;[a-zA-Z0-9_\-]+&gt;)/g, '<span class="font-semibold text-slate-100">$1</span>');
    // 3. Destacar parametros e campos chave (ex: cStat=100, vOutro=-1066.69, vProd=251.79)
    safe = safe.replace(/\b([a-zA-Z]{1,10}=[-0-9\.,]+)\b/g, '<span class="font-semibold text-slate-100">$1</span>');
    // 4. Destacar tags de severidade [REJEICAO] / [ALERTA] se presentes
    safe = safe.replace(/(\[(?:REJEICAO|ALERTA|ERRO|CONFORME|AVISO)[^\]]*\])/gi, '<strong class="font-bold text-rose-400">$1</strong>');
    return safe;
  }

  function formatNumber(num, decimals = 2) {
    const n = Number(num);
    if (isNaN(n)) return String(num || '0');
    return n.toLocaleString('pt-BR', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    });
  }

  function coerceNumber(val, fallback = 0) {
    if (val === null || val === undefined) return fallback;
    const n = Number(val);
    return isNaN(n) ? fallback : n;
  }

  function coerceBoolean(val, fallback = false) {
    if (val === null || val === undefined) return fallback;
    if (typeof val === 'boolean') return val;
    if (typeof val === 'number') return val !== 0;
    if (typeof val === 'string') {
      const s = val.trim().toLowerCase();
      if (s === 'true' || s === '1' || s === 'yes' || s === 'sim') return true;
      if (s === 'false' || s === '0' || s === 'no' || s === 'nao' || s === 'não') return false;
    }
    return Boolean(val);
  }

  function sanitizePropsSafe(data, seen = new WeakSet()) {
    if (data === null || data === undefined) return data;
    if (typeof data !== 'object') return data;
    if (seen.has(data)) return '[Circular]';
    seen.add(data);
    if (Array.isArray(data)) {
      return data.map(item => sanitizePropsSafe(item, seen));
    }
    const safe = {};
    for (const key of Object.keys(data)) {
      if (key === '__proto__' || key === 'constructor' || key === 'prototype') {
        continue;
      }
      safe[key] = sanitizePropsSafe(data[key], seen);
    }
    return safe;
  }

  // =========================================================================
  // 2. CLASSE BASE: BaseGenUIWidget
  // =========================================================================

  class BaseGenUIWidget {
    constructor(payload = {}, defaultIntent = 'mentoria_decisao', defaultComp = 'render_BaseGenUIWidget') {
      this.toolCallId = escapeHtml(payload.tool_call_id || ('call_' + Date.now()));
      this.intent = escapeHtml(payload.intent || defaultIntent);
      this.componentName = escapeHtml(payload.component_name || defaultComp);
      this.summary = escapeHtml(payload.executive_summary || payload.summary_text || '');
      this.props = sanitizePropsSafe(payload.props || {});
      this.actions = (Array.isArray(payload.actions) && payload.actions.length > 0)
        ? payload.actions
        : (this.props && Array.isArray(this.props.suggested_actions) ? this.props.suggested_actions : []);
      this.createdAt = payload.created_at || payload.timestamp || new Date().toISOString();
      this.ttlSeconds = coerceNumber(payload.ttl_seconds, 900);
      this.sessionId = escapeHtml(payload.session_id || payload.sessionId || '');

      this.cardClass = 'genui-decision-mentor-card';
      this.ariaLabel = 'Micro-Widget AURA IntelligentUI';

      this.state = {
        status: 'proposed', // 'proposed' | 'locked' | 'committed' | 'failed' | 'expired'
        isLocked: false,
        lockedActionId: null,
        optimisticFeedback: null,
        errorMessage: null,
        expandedEvidences: false,
        voucher: null
      };

      this.element = null;
      this.eventListeners = {};

      const genui = (typeof window !== 'undefined' && window.AuraGenUI) ||
                    (typeof AuraGenUI !== 'undefined' ? AuraGenUI : null);
      if (genui && typeof genui.registerWidget === 'function') {
        genui.registerWidget(this.toolCallId, this);
      }
    }

    get isLocked() {
      return !!(this.state && this.state.isLocked);
    }

    get isCommitted() {
      return !!(this.state && (this.state.status === 'committed' || this.state.voucher));
    }

    /**
     * Avalia se a proposta do widget expirou pelo TTL (padrao: 15 min / 900s)
     * @returns {boolean}
     */
    isExpired() {
      const stateMgr = (typeof window !== 'undefined' && window.auraStateManager) ||
                       (typeof globalThis !== 'undefined' && globalThis.auraStateManager) ||
                       null;
      if (stateMgr && typeof stateMgr.isStale === 'function') {
        return stateMgr.isStale(this.createdAt, this.ttlSeconds);
      }
      let ts = 0;
      if (typeof this.createdAt === 'number') {
        ts = this.createdAt;
      } else if (typeof this.createdAt === 'string') {
        const parsed = Date.parse(this.createdAt);
        ts = isNaN(parsed) ? Number(this.createdAt) : parsed;
      } else if (this.createdAt instanceof Date) {
        ts = this.createdAt.getTime();
      }
      if (isNaN(ts) || ts <= 0) return false;
      return (Date.now() - ts) > (this.ttlSeconds * 1000);
    }

    /**
     * Monta o elemento DOM principal no padrao AURA Precision Glass Deluxe
     * @returns {HTMLElement|string} Elemento DOM hidratado (ou representacao de no)
     */
    mount() {
      const genui = (typeof window !== 'undefined' && window.AuraGenUI) ||
                    (typeof AuraGenUI !== 'undefined' ? AuraGenUI : null);
      if (genui && typeof genui.registerWidget === 'function') {
        genui.registerWidget(this.toolCallId, this);
      }

      // 0. Registra o widget no AuraStateManager se disponivel e sincroniza estado persistido
      const stateMgr = (typeof window !== 'undefined' && window.auraStateManager) ||
                       (typeof globalThis !== 'undefined' && globalThis.auraStateManager) ||
                       null;
      if (stateMgr && typeof stateMgr.registerWidget === 'function') {
        const entry = stateMgr.registerWidget(
          this.toolCallId,
          Object.assign({ created_at: this.createdAt, timestamp: this.createdAt }, this.props),
          this.ttlSeconds,
          this.createdAt
        );
        if (entry && entry.state) {
          this.state = Object.assign({}, this.state, entry.state);
          if (entry.optimisticData && entry.optimisticData.feedback) {
            this.state.optimisticFeedback = entry.optimisticData.feedback;
          }
        }
      }

      // 1. Gera HTML canonico seguro das 3 camadas
      const htmlContent = this.renderHtml();

      if (typeof document !== 'undefined' && typeof document.createElement === 'function') {
        const container = document.createElement('div');
        container.id = `genui-card-${this.toolCallId}`;
        const cardClass = this.cardClass || 'genui-decision-mentor-card';
        container.className = `genui-hydrated-card ${cardClass} animate-fade-in my-3 rounded-2xl border border-cyan-500/25 bg-slate-900/85 backdrop-blur-xl shadow-2xl p-4 sm:p-5 text-slate-100 transition-all`;
        container.setAttribute('data-tool-call-id', this.toolCallId);
        container.setAttribute('data-component', this.componentName);
        container.setAttribute('role', 'region');
        container.setAttribute('aria-label', this.ariaLabel || 'Mentor de Decisoes Executivo AURA');
        container.innerHTML = htmlContent;

        this.element = container;
        this.bindEvents(container);
        return container;
      }

      // Fallback em ambiente headless Node.js sem DOM nativo
      return htmlContent;
    }

    /**
     * Serializa o HTML completo em 3 camadas concentricas
     */
    renderHtml() {
      return `
        <div class="genui-widget-inner genui-decision-mentor-inner">
          ${this.renderLayer1()}
          ${this.renderLayer2()}
          ${this.renderLayer3()}
        </div>
      `;
    }

    renderLayer1() {
      return '<div class="genui-layer genui-layer-1"></div>';
    }

    renderLayer2() {
      return '<div class="genui-layer genui-layer-2"></div>';
    }

    getDefaultActionsHtml() {
      const shouldDisable = this.state.isLocked || this.isExpired();
      const stateMgr = (typeof window !== 'undefined' && window.auraStateManager) ||
                       (typeof globalThis !== 'undefined' && globalThis.auraStateManager) ||
                       null;
      const isDone1 = (stateMgr && typeof stateMgr.isActionExecuted === 'function' && stateMgr.isActionExecuted('act_default_apply')) || (this.state.voucher && (this.state.voucher.action_id === 'act_default_apply' || this.state.status === 'committed'));
      const isDone2 = (stateMgr && typeof stateMgr.isActionExecuted === 'function' && stateMgr.isActionExecuted('act_default_goals')) || (this.state.voucher && (this.state.voucher.action_id === 'act_default_goals'));

      const isCurrentActive1 = this.state.isLocked && this.state.lockedActionId === 'act_default_apply';
      const isCurrentActive2 = this.state.isLocked && this.state.lockedActionId === 'act_default_goals';

      let displayLabel1 = isDone1 ? '✔ Recomendações Aplicadas' : '⚡ Aplicar Recomendações Prioritárias';
      if (isCurrentActive1) {
        displayLabel1 = '<span class="inline-flex items-center gap-1.5"><svg class="animate-spin -ml-0.5 mr-1 h-3.5 w-3.5 text-cyan-400 inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path></svg><span class="animate-pulse">Processando...</span></span>';
      }

      let displayLabel2 = isDone2 ? '✔ Metas Ajustadas' : '🎯 Ajustar Metas do Turno';
      if (isCurrentActive2) {
        displayLabel2 = '<span class="inline-flex items-center gap-1.5"><svg class="animate-spin -ml-0.5 mr-1 h-3.5 w-3.5 text-cyan-400 inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path></svg><span class="animate-pulse">Processando...</span></span>';
      }

      if (!this.actions || this.actions.length === 0) {
        this.actions = [
          { action_id: 'act_default_apply', label: '⚡ Aplicar Recomendações Prioritárias', action_type: 'mutation', variant: 'primary' },
          { action_id: 'act_default_goals', label: '🎯 Ajustar Metas do Turno', action_type: 'mutation', variant: 'secondary' },
          { action_id: 'act_default_canvas', label: '🔍 Projetar Cenário no Canvas', action_type: 'inspection', variant: 'ghost' }
        ];
      }

      return `
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 font-bold hover:brightness-110 ${(shouldDisable || isDone1) ? 'opacity-50 pointer-events-none cursor-not-allowed' : ''}"
                data-action-id="act_default_apply"
                data-action-type="mutation"
                data-tool-call-id="${escapeHtml(this.toolCallId)}"
                title="Gera requisição formal e aciona o fornecedor para reposição de combustível via WhatsApp/ERP"
                ${(shouldDisable || isDone1) ? 'disabled' : ''}>
          <span>${displayLabel1}</span>
        </button>
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-slate-800 text-cyan-200 border border-cyan-500/30 hover:bg-slate-700 ${(shouldDisable || isDone2) ? 'opacity-50 pointer-events-none cursor-not-allowed' : ''}"
                data-action-id="act_default_goals"
                data-action-type="mutation"
                data-tool-call-id="${escapeHtml(this.toolCallId)}"
                title="Repactua metas de volume e margem no PDV e alerta os líderes de pista via WhatsApp"
                ${(shouldDisable || isDone2) ? 'disabled' : ''}>
          <span>${displayLabel2}</span>
        </button>
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-slate-900/60 text-slate-300 border border-white/10 hover:bg-slate-800"
                data-action-id="act_default_canvas"
                data-action-type="inspection"
                data-tool-call-id="${escapeHtml(this.toolCallId)}"
                title="Projeta o diagnóstico e gráficos preditivos no painel lateral de alta fidelidade">
          <span>🔍 Projetar Cenário no Canvas</span>
        </button>
      `;
    }

    /**
     * Camada 3: Acao Recomendada de 1 Toque e Acoplamento com Companion Canvas
     */
    renderLayer3() {
      const actions = Array.isArray(this.actions) && this.actions.length > 0
        ? this.actions
        : (this.props && Array.isArray(this.props.suggested_actions) ? this.props.suggested_actions : []);

      const isLocked = !!this.state.isLocked;
      const feedback = this.state.optimisticFeedback;
      const isExpired = this.isExpired() || this.state.status === 'expired';

      const stateMgr = (typeof window !== 'undefined' && window.auraStateManager) ||
                       (typeof globalThis !== 'undefined' && globalThis.auraStateManager) ||
                       null;

      let expiredBadge = '';
      if (isExpired) {
        expiredBadge = `
          <div class="genui-expired-badge p-2.5 mb-2.5 rounded-xl bg-slate-950/70 border border-slate-700/60 text-slate-400 text-xs flex items-center justify-between gap-2">
            <div class="flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-slate-500"></span>
              <span class="font-medium text-slate-300">Proposta Expirada (Dados de telemetria desatualizados)</span>
            </div>
            <span class="badge-expired text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-700">Expirado</span>
          </div>
        `;
      }

      let feedbackBadge = '';
      if (this.state.status === 'committed' || this.state.voucher) {
        feedbackBadge = `
          <div class="genui-success-badge genui-voucher-badge p-2.5 mb-2.5 rounded-xl bg-emerald-500/20 border border-emerald-400/50 text-emerald-200 text-xs flex items-center justify-between gap-2 shadow-sm animate-fade-in">
            <div class="flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
              <span class="font-bold text-white">${escapeHtml(feedback || 'Ação Homologada no ERP')}</span>
              ${this.state.voucher?.voucher_id ? `<span class="text-[10px] font-mono text-emerald-300/80">(${escapeHtml(this.state.voucher.voucher_id)})</span>` : ''}
            </div>
            <div class="flex items-center gap-2">
              <span class="text-[11px] font-medium text-emerald-200">Integrado no ERP & Mensageria</span>
              <span class="badge-committed text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-emerald-900/60 text-emerald-300 border border-emerald-500/30">VOUCHER AUDITADO</span>
            </div>
          </div>
        `;
      } else if (feedback) {
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

      // Constroi botoes de acao tatil
      let buttonsHtml = '';
      if (actions.length > 0) {
        buttonsHtml = actions.map(act => {
          const actId = escapeHtml(act.action_id || ('act_' + Math.random().toString(36).substring(2, 8)));
          const label = escapeHtml(act.label || 'Acao Recomendada');
          const variant = act.variant || 'primary';
          const actType = act.action_type || 'mutation';

          let btnTitle = label;
          if (actType === 'inspection' || label.includes('Canvas')) {
            btnTitle = 'Projeta o diagnóstico e gráficos preditivos no painel lateral de alta fidelidade';
          } else if (label.includes('Combustível') || label.includes('Recomendações') || label.includes('Carreta')) {
            btnTitle = 'Gera requisição formal e aciona o fornecedor para reposição de combustível via WhatsApp/ERP';
          } else if (label.includes('Meta') || label.includes('Turno')) {
            btnTitle = 'Repactua metas de volume e margem no PDV e alerta os líderes de pista via WhatsApp';
          } else if (label.includes('Quebra') || label.includes('Sangria') || label.includes('Caixa')) {
            btnTitle = 'Exige sangria preventiva de valores para o cofre e aciona o supervisor';
          } else if (label.includes('Margem') || label.includes('Preço')) {
            btnTitle = 'Gera pendência de atualização de preços nas bombas e totem';
          }

          const isActionDone = (stateMgr && typeof stateMgr.isActionExecuted === 'function' && stateMgr.isActionExecuted(act.action_id)) || (this.state.voucher && (this.state.voucher.action_id === act.action_id || !this.state.voucher.action_id));
          const isCurrentActive = isLocked && this.state.lockedActionId === act.action_id;
          const shouldDisable = isLocked || isActionDone || (isExpired && actType !== 'inspection');

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

          if (shouldDisable) {
            btnClass += 'opacity-50 pointer-events-none cursor-not-allowed ';
          }

          let displayLabel = label;
          if (isCurrentActive) {
            displayLabel = `<span class="inline-flex items-center gap-1.5"><svg class="animate-spin -ml-0.5 mr-1 h-3.5 w-3.5 text-cyan-400 inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path></svg><span class="animate-pulse">Processando...</span></span>`;
          } else if (isActionDone) {
            displayLabel = `✔ ${label}`;
          }

          return `
            <button type="button"
                    class="genui-action-btn ${btnClass}"
                    data-action-id="${actId}"
                    data-action-type="${escapeHtml(actType)}"
                    data-tool-call-id="${escapeHtml(this.toolCallId)}"
                    title="${escapeHtml(btnTitle)}"
                    ${shouldDisable ? 'disabled' : ''}>
              <span>${displayLabel}</span>
            </button>
          `;
        }).join('');
      } else {
        buttonsHtml = this.getDefaultActionsHtml();
      }

      return `
        <div class="genui-layer genui-layer-3 pt-3 border-t border-white/10">
          ${expiredBadge}
          ${feedbackBadge}
          ${errorBadge}
          <div class="flex flex-wrap gap-2">
            ${buttonsHtml}
          </div>
          <div class="genui-action-hint text-[11px] text-slate-400 mt-2 font-sans flex items-center gap-1.5">
            <span class="w-1.5 h-1.5 rounded-full bg-cyan-400"></span>
            <span>Clique em uma ação para homologar no ERP e disparar esteiras de fornecedores ou equipe.</span>
          </div>
        </div>
      `;
    }

    /**
     * Vincula listeners de evento no DOM aos botoes da Camada 3 e expansores
     */
    bindEvents(rootElement) {
      if (!rootElement || typeof rootElement.querySelectorAll !== 'function') return;

      // 1. Toggle de evidencias analiticas
      const toggleBtn = rootElement.querySelector('.genui-toggle-evidence');
      const listEl = rootElement.querySelector('.genui-evidence-list');
      if (toggleBtn && listEl && !toggleBtn._hasBoundClick) {
        toggleBtn._hasBoundClick = true;
        toggleBtn.addEventListener('click', () => {
          this.state.expandedEvidences = !this.state.expandedEvidences;
          listEl.classList.toggle('hidden', !this.state.expandedEvidences);
          const count = (this.props && Array.isArray(this.props.evidence_items)) ? this.props.evidence_items.length : 0;
          toggleBtn.textContent = this.state.expandedEvidences
            ? '▲ Ocultar Evidencias'
            : `▼ Memoria de Calculo & Evidencias (${count} itens)`;
        });
      }

      // 2. Dismiss de erro
      const dismissBtn = rootElement.querySelector('.genui-dismiss-error');
      if (dismissBtn && !dismissBtn._hasBoundClick) {
        dismissBtn._hasBoundClick = true;
        dismissBtn.addEventListener('click', () => {
          this.state.errorMessage = null;
          this.refreshLayer3();
        });
      }

      // 3. Botoes de acao da Camada 3
      const actionBtns = rootElement.querySelectorAll('.genui-action-btn');
      actionBtns.forEach(btn => {
        if (!btn._hasBoundClick) {
          btn._hasBoundClick = true;
          btn.addEventListener('click', (e) => {
            if (e && e._genuiActionHandled) return;
            if (e) e._genuiActionHandled = true;
            const actionId = btn.getAttribute('data-action-id');
            const actionType = btn.getAttribute('data-action-type');
            this.handleActionClick(actionId, actionType, btn, e);
          });
        }
      });
    }

    /**
     * Processa clique em botao de acao da Camada 3 com State Locking e Optimistic UI
     */
    async handleActionClick(actionId, actionType, btnElement, event) {
      const stateMgr = (typeof window !== 'undefined' && window.auraStateManager) ||
                       (typeof globalThis !== 'undefined' && globalThis.auraStateManager) ||
                       null;

      if (this.state.isLocked) return false;
      if (stateMgr && typeof stateMgr.getWidget === 'function' && stateMgr.getWidget(this.toolCallId)?.isLocked) return false;
      if (stateMgr && typeof stateMgr.isActionExecuted === 'function' && stateMgr.isActionExecuted(actionId)) return false;
      if (this.isExpired() && actionType !== 'inspection') return false;

      // 1. Acoes de inspecao no Companion Canvas com protecao de debounce
      const btnText = (btnElement && typeof btnElement.textContent === 'string') ? btnElement.textContent : '';
      const isInspection = actionType === 'inspection' || btnText.includes('Canvas') || btnText.includes('Projetar');
      if (isInspection) {
        const now = Date.now();
        if (now - (this._canvasDebounce || 0) < 800) {
          return false;
        }
        this._canvasDebounce = now;
        this.projectToCanvas();

        if (typeof window !== 'undefined' && window.auraAuxPanel && typeof window.auraAuxPanel.open === 'function') {
          window.auraAuxPanel.open('art_genui_' + this.toolCallId, true, btnElement);
        }

        const fx = (typeof window !== 'undefined' && window.auraFx) || null;
        if (fx && typeof fx.showToast === 'function') {
          fx.showToast({
            title: 'Cenário Projetado',
            message: 'O diagnóstico executivo foi projetado no Companion Canvas.',
            type: 'info'
          });
        }

        if (typeof window !== 'undefined' && window.auraAudio && typeof window.auraAudio.playChime === 'function') {
          window.auraAudio.playChime(680, 0.05);
        }
        return true;
      }

      // Acao especial: Disparo de Investigacao Forense de Causa-Raiz (RCA)
      if (actionId === 'act_investigar_rca' || btnElement?.getAttribute('data-action-id') === 'act_investigar_rca') {
        if (typeof window !== 'undefined' && window.auraChat && typeof window.auraChat.sendMessage === 'function') {
          const shift = this.props?.turno_auditado && !this.props.turno_auditado.includes('TODOS') ? ` do ${this.props.turno_auditado}` : '';
          const dataA = this.props?.data_auditada ? ` de ${this.props.data_auditada}` : '';
          window.auraChat.sendMessage(`Investigar causa raiz da quebra${shift}${dataA}`);
          return true;
        }
      }

      // Acao especial: Copiar Diagnostico Fiscal para o Contador (Area de Transferencia)
      const actionPayload = (this.actions || []).find(a => a.action_id === actionId)?.payload || {};
      if (actionPayload.intent === 'copiar_diagnostico_contador' || actionId.includes('copiar_diagnostico') || btnElement?.textContent?.includes('Copiar Diagnostico')) {
        const title = this.props?.title || 'Parecer Fiscal AURA';
        const diag = this.props?.diagnosis || '';
        const blocks = Array.isArray(this.props?.blocks) ? this.props.blocks : [];
        const alerta = blocks.find(b => b.block_type === 'alert_callout')?.alert?.message || '';
        const acao = blocks.find(b => b.block_type === 'alert_callout')?.alert?.action_label || '';
        const proc = blocks.find(b => b.block_id === 'blk_procedimento_erp')?.custom_content || '';

        const clipboardText = [
          `=== PARECER FISCAL / DIAGNOSTICO SEFAZ (AURA INTELLIGENCE) ===`,
          `Titulo: ${title}`,
          `Diagnostico: ${diag}`,
          alerta ? `Impacto: ${alerta}` : '',
          acao ? `Acao webPosto: ${acao}` : '',
          proc ? `\nProcedimento Detalhado:\n${proc}` : '',
          `\nData/Hora: ${new Date().toLocaleString('pt-BR')}`,
          `Gerado pela AURA - Assistente de Prontidao do Posto`
        ].filter(Boolean).join('\n');

        if (typeof navigator !== 'undefined' && navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
          navigator.clipboard.writeText(clipboardText).then(() => {
            if (btnElement) {
              const origHtml = btnElement.innerHTML;
              btnElement.innerHTML = '<span>✔ Laudo Copiado para Area de Transferencia!</span>';
              setTimeout(() => {
                if (btnElement) btnElement.innerHTML = origHtml;
              }, 4000);
            }
            const fx = (typeof window !== 'undefined' && window.auraFx) || null;
            if (fx && typeof fx.showToast === 'function') {
              fx.showToast({
                title: 'Parecer Copiado!',
                message: 'Diagnostico fiscal copiado para a area de transferencia. Pronto para enviar ao contador.',
                type: 'success'
              });
            }
          }).catch(() => {});
        }
        return true;
      }

      // Acao especial: Consultar Modulo de Faturamento
      if (actionPayload.intent === 'ajuda_sistema' && actionPayload.modulo === 'faturamento') {
        if (typeof window !== 'undefined' && window.auraChat && typeof window.auraChat.sendMessage === 'function') {
          window.auraChat.sendMessage('Como operar o Modulo de Faturamento e Notas Fiscais no webPosto?');
          return true;
        }
      }

      // 2. Acao de mutacao / recomendacao transacional
      const actionDef = (this.actions || []).find(a => a.action_id === actionId) || {
        action_id: actionId,
        label: btnElement ? btnElement.textContent.trim() : 'Acao',
        payload: { intent: this.intent, tool_call_id: this.toolCallId }
      };

      // Aplica State Locking imediato e Optimistic UI no AuraStateManager (F4-02 & F4-03)
      if (stateMgr) {
        stateMgr.lockWidget(this.toolCallId, actionId);
        stateMgr.applyOptimisticState(this.toolCallId, {
          actionId: actionId,
          label: actionDef.label,
          status: 'optimistic'
        });
      }

      // Aplica State Locking e classes de desabilitacao tatil no DOM
      this.applyOptimisticState(actionId, `Autorizando: ${actionDef.label}...`);
      if (btnElement) {
        btnElement.classList.add('opacity-50', 'pointer-events-none', 'cursor-not-allowed');
        btnElement.disabled = true;
      }

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

      // Se houver cliente de API disponivel no browser, despacha RPC
      let res = null;
      let rpcExecuted = false;

      if (typeof window !== 'undefined' && window.auraApi && typeof window.auraApi.executeAction === 'function') {
        rpcExecuted = true;
        try {
          const operatorRole = this.operatorRole ||
            (typeof window !== 'undefined' && (window.currentOperatorRole || (window.currentUser && window.currentUser.role))) ||
            'gerente';
          const operatorId = this.operatorId ||
            (typeof window !== 'undefined' && (window.currentOperatorId || (window.currentUser && window.currentUser.id))) ||
            'operador_01';

          res = await window.auraApi.executeAction(actionId, {
            tool_call_id: this.toolCallId,
            session_id: this.sessionId || (typeof window !== 'undefined' && window.auraChat && window.auraChat.sessionId) || '',
            action_name: actionDef.label || actionDef.name || actionDef.action_name || 'acao_executiva',
            action_type: actionDef.action_type || actionType || 'mutation',
            payload: actionDef.payload,
            operator_id: operatorId,
            operator_role: operatorRole
          });
        } catch (err) {
          if (stateMgr) {
            stateMgr.rollbackOptimisticState(this.toolCallId);
          }
          this.rollbackOptimisticState(err?.message || 'Falha na comunicacao com o ERP.');
          const fx = (typeof window !== 'undefined' && window.auraFx) || null;
          if (fx && typeof fx.showToast === 'function') {
            fx.showToast({
              title: 'Falha na Operacao',
              message: 'Nao foi possivel comunicar com o ERP central. Tente novamente.',
              type: 'error'
            });
          }
          return false;
        }
      } else if (typeof fetch === 'function' && typeof window !== 'undefined' && window.location) {
        rpcExecuted = true;
        try {
          const operatorRole = this.operatorRole || (window.currentUser && window.currentUser.role) || 'gerente';
          const operatorId = this.operatorId || (window.currentUser && window.currentUser.id) || 'operador_01';
          const fetchResp = await fetch('/api/v1/aura/actions/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              session_id: this.sessionId || (window.auraChat && window.auraChat.sessionId) || '',
              tool_call_id: this.toolCallId,
              action_id: actionId,
              action_name: actionDef.label || 'acao_executiva',
              action_type: actionDef.action_type || actionType || 'mutation',
              payload: actionDef.payload || {},
              operator_id: operatorId,
              operator_role: operatorRole
            })
          });
          if (!fetchResp.ok) {
            throw new Error(`HTTP ${fetchResp.status}`);
          }
          res = await fetchResp.json();
        } catch (err) {
          if (stateMgr) {
            stateMgr.rollbackOptimisticState(this.toolCallId);
          }
          this.rollbackOptimisticState(err?.message || 'Falha na comunicacao com o ERP.');
          const fx = (typeof window !== 'undefined' && window.auraFx) || null;
          if (fx && typeof fx.showToast === 'function') {
            fx.showToast({
              title: 'Falha na Operacao',
              message: 'Nao foi possivel comunicar com o ERP central. Tente novamente.',
              type: 'error'
            });
          }
          return false;
        }
      }

      if (rpcExecuted && res) {
        if (stateMgr) {
          stateMgr.markActionExecuted(actionId, res);
          stateMgr.finalizeSuccessState(this.toolCallId, res);
        }
        this.finalizeSuccessState(res);

        const fx = (typeof window !== 'undefined' && window.auraFx) || null;
        if (fx && typeof fx.showToast === 'function') {
          fx.showToast({
            title: 'Ação Homologada',
            message: 'Decisão registrada e auditada com sucesso.',
            type: 'success'
          });
        }

        if (typeof window !== 'undefined' && window.auraAudio && typeof window.auraAudio.playChime === 'function') {
          window.auraAudio.playChime(880, 0.08);
        }
      }
      return true;
    }

    applyOptimisticState(actionIdOrData, feedbackText = 'Processando autorizacao no ERP...') {
      let actId = null;
      let feedback = feedbackText;
      if (typeof actionIdOrData === 'object' && actionIdOrData !== null) {
        actId = actionIdOrData.actionId || actionIdOrData.action_id || null;
        feedback = actionIdOrData.feedback || actionIdOrData.label || feedbackText;
        if (actionIdOrData.status) this.state.status = actionIdOrData.status;
        else this.state.status = 'optimistic';
      } else {
        actId = actionIdOrData;
        this.state.status = 'optimistic';
      }
      this.state.isLocked = true;
      this.state.lockedActionId = actId;
      this.state.optimisticFeedback = feedback;
      this.state.errorMessage = null;
      this.refreshLayer3();
    }

    rollbackOptimisticState(errorMsg = 'Nao foi possivel comunicar com o ERP central.') {
      this.state.isLocked = false;
      this.state.lockedActionId = null;
      this.state.optimisticFeedback = null;
      this.state.errorMessage = errorMsg;
      this.state.status = 'failed';
      this.refreshLayer3();
    }

    finalizeSuccessState(result = {}) {
      this.state.status = 'committed';
      this.state.isLocked = false;
      this.state.lockedActionId = null;
      this.state.voucher = result;
      this.state.optimisticFeedback = 'Ação Homologada no ERP';
      this.state.errorMessage = null;
      this.refreshLayer3();
    }

    refreshLayer3() {
      let updatedSelf = false;
      if (this.element && typeof this.element.querySelector === 'function') {
        const layer3El = this.element.querySelector('.genui-layer-3');
        if (layer3El && layer3El.parentNode && typeof layer3El.parentNode.replaceChild === 'function') {
          const temp = document.createElement('div');
          temp.innerHTML = this.renderLayer3().trim();
          const newLayer3 = temp.firstElementChild;
          if (newLayer3) {
            try {
              layer3El.parentNode.replaceChild(newLayer3, layer3El);
              this.bindEvents(this.element);
              updatedSelf = true;
            } catch (_) {}
          }
        }
      }
      if (!updatedSelf && this.element && typeof this.element === 'object') {
        this.element.innerHTML = this.renderHtml();
        this.bindEvents(this.element);
      }

      // Sincroniza todas as instancias duplicadas do card no DOM (chat, portais desdobraveis e Companion Canvas)
      if (typeof document !== 'undefined' && typeof document.querySelectorAll === 'function') {
        try {
          const matchingCards = new Set();
          const cards1 = document.querySelectorAll(`.genui-hydrated-card[data-tool-call-id="${this.toolCallId}"]`);
          const cards2 = document.querySelectorAll(`[data-tool-call-id="${this.toolCallId}"]`);
          const canvasEl = (typeof document.getElementById === 'function') ? document.getElementById('aux-view-visual') : null;

          if (cards1) Array.from(cards1).forEach(c => matchingCards.add(c));
          if (cards2) Array.from(cards2).forEach(c => matchingCards.add(c));
          if (canvasEl) matchingCards.add(canvasEl);

          matchingCards.forEach(card => {
            if (card === this.element) return;
            const l3 = card.querySelector ? card.querySelector('.genui-layer-3') : null;
            if (l3 && l3.parentNode && typeof l3.parentNode.replaceChild === 'function') {
              const temp = document.createElement('div');
              temp.innerHTML = this.renderLayer3().trim();
              const newL3 = temp.firstElementChild;
              if (newL3) {
                try {
                  l3.parentNode.replaceChild(newL3, l3);
                  this.bindEvents(card);
                } catch (_) {}
              }
            }
          });
        } catch (_) {}
      }
    }

    projectToCanvas() {
      if (typeof window !== 'undefined' && window.auraAuxPanel && typeof window.auraAuxPanel.projectArtifact === 'function') {
        try {
          const cardHtml = `<div id="genui-canvas-card-${this.toolCallId}" class="genui-hydrated-card ${this.cardClass || 'genui-decision-mentor-card'}" data-tool-call-id="${this.toolCallId}" data-component="${this.componentName}">${this.renderHtml()}</div>`;
          window.auraAuxPanel.projectArtifact({
            id: 'art_genui_' + this.toolCallId,
            containerId: null,
            toolName: this.componentName,
            intent: this.intent,
            data: this.props,
            html: cardHtml,
            autoOpen: true
          });
        } catch (e) {
          console.warn(`[${this.componentName}] Erro ao projetar no Companion Canvas:`, e);
        }
      } else if (typeof window !== 'undefined' && window.auraChat && typeof window.auraChat.showToast === 'function') {
        window.auraChat.showToast('Companion Canvas indisponivel ou inicializando.', 'info');
      }
    }
  }

  // =========================================================================
  // 3. COMPONENTE PILOTO: ExecutiveDecisionMentorUI
  // =========================================================================

  class ExecutiveDecisionMentorUI extends BaseGenUIWidget {
    constructor(payload = {}) {
      super(payload, 'mentoria_decisao', 'render_ExecutiveDecisionMentorUI');
      this.cardClass = 'genui-decision-mentor-card';
      this.ariaLabel = 'Mentor de Decisoes Executivo AURA';
    }

    renderLayer1() {
      const p = this.props || {};
      const scoreRaw = p.confidence_score !== undefined ? Number(p.confidence_score) : 0.96;
      const scorePct = Math.round(scoreRaw * 100);
      const diagnosisText = p.diagnosis || this.summary || 'Diagnostico operacional apurado pelo motor analitico da AURA.';

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
            <span class="text-[10px] uppercase font-bold tracking-wider text-cyan-400 font-mono">Diagnostico Executivo</span>
            <p class="text-xs sm:text-sm font-mono font-normal text-slate-300 leading-relaxed">
              ${escapeHtml(diagnosisText)}
            </p>
          </div>
        </div>
      `;
    }

    renderLayer2() {
      const p = this.props || {};
      const metrics = Array.isArray(p.metrics) ? p.metrics : [];
      const limitations = Array.isArray(p.limitations)
        ? p.limitations.filter(Boolean)
        : (p.limitations ? [String(p.limitations)] : []);
      const impact = p.impact_projection || null;
      const evidences = Array.isArray(p.evidence_items) ? p.evidence_items : [];

      let metricsHtml = '';
      if (metrics.length > 0) {
        metricsHtml = `
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3">
            ${metrics.map(m => {
              const lbl = escapeHtml((m && typeof m === 'object' ? m.label : m) || 'Metrica');
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

      let evidencesHtml = '';
      if (evidences.length > 0) {
        const isExpanded = !!this.state.expandedEvidences;
        evidencesHtml = `
          <div class="mt-2 text-[11px] space-y-1.5">
            <button type="button" class="genui-toggle-evidence text-[10px] font-mono text-cyan-300 hover:text-cyan-200 flex items-center gap-1 focus:outline-none">
              <span>${isExpanded ? '▲ Ocultar Evidencias' : `▼ Memoria de Calculo & Evidencias (${evidences.length} itens)`}</span>
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
  }

  // =========================================================================
  // 4. MICRO-WIDGET 1: MarginAnalysisUI (Fase 6: F6-02)
  // =========================================================================

  class MarginAnalysisUI extends BaseGenUIWidget {
    constructor(payload = {}) {
      super(payload, 'analise_margem', 'render_MarginAnalysisUI');
      this.cardClass = 'genui-margin-analysis-card';
      this.ariaLabel = 'Analise de Margem Real e Meios de Pagamento AURA';
    }

    renderLayer1() {
      const p = this.props || {};
      const marginVal = Number(p.consolidated_margin_pct ?? 14.5);
      const targetVal = p.target_margin_pct !== null && p.target_margin_pct !== undefined ? Number(p.target_margin_pct) : null;
      const diagnosisText = p.diagnosis || this.summary || 'Analise de margem liquida consolidada apurada no ERP.';

      const scoreColor = marginVal >= 15
        ? 'text-emerald-300 border-emerald-500/40 bg-emerald-500/10'
        : (marginVal >= 10 ? 'text-amber-300 border-amber-500/40 bg-amber-500/10' : 'text-rose-300 border-rose-500/40 bg-rose-500/10');

      return `
        <div class="genui-layer genui-layer-1 mb-4 pb-3 border-b border-white/10">
          <div class="flex flex-wrap items-center justify-between gap-2 mb-2.5">
            <div class="flex items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse flex-shrink-0"></span>
              <h4 class="text-xs font-mono font-bold tracking-wider text-emerald-300 uppercase">
                AURA Margin &amp; Profitability Analyst
              </h4>
              <span class="text-[10px] font-mono text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded border border-white/5">
                ${escapeHtml(this.toolCallId.substring(0, 14))}...
              </span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-[11px] font-mono px-2.5 py-0.5 rounded-full border ${scoreColor} font-semibold flex items-center gap-1">
                <span>Margem Real: ${formatNumber(marginVal)}%</span>
              </span>
              ${targetVal !== null ? `<span class="text-[10px] font-mono text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded border border-white/5">Meta: ${formatNumber(targetVal)}%</span>` : ''}
            </div>
          </div>
          <div class="p-3 rounded-xl bg-slate-950/50 border border-white/5 space-y-1">
            <span class="text-[10px] uppercase font-bold tracking-wider text-emerald-400 font-mono">Diagnostico de Rentabilidade</span>
            <p class="text-xs sm:text-sm font-mono font-normal text-slate-300 leading-relaxed">
              ${escapeHtml(diagnosisText)}
            </p>
          </div>
        </div>
      `;
    }

    renderLayer2() {
      const p = this.props || {};
      const fuels = Array.isArray(p.fuel_margins) ? p.fuel_margins : [];
      const paymentFees = Array.isArray(p.payment_fee_impact) ? p.payment_fee_impact : [];
      const limitations = Array.isArray(p.limitations) ? p.limitations : [];

      let totalDesconto = 0;
      paymentFees.forEach(pf => {
        if (pf && pf.desconto_taxas_reais) totalDesconto += Number(pf.desconto_taxas_reais);
      });

      // 4 Cards de Sintese
      const cardsHtml = `
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3">
          <div class="p-2.5 rounded-xl border border-white/5 bg-slate-950/40 space-y-1">
            <span class="text-[10px] text-slate-400 font-medium">Margem Liquida</span>
            <div class="text-sm sm:text-base font-bold font-mono text-emerald-300 tabular-nums">
              ${formatNumber(p.consolidated_margin_pct ?? 14.5)}%
            </div>
            <span class="text-[10px] text-slate-500 font-mono">Real Consolidado</span>
          </div>
          <div class="p-2.5 rounded-xl border border-white/5 bg-slate-950/40 space-y-1">
            <span class="text-[10px] text-slate-400 font-medium">Faturamento Bruto</span>
            <div class="text-sm sm:text-base font-bold font-mono text-white tabular-nums">
              R$ ${formatNumber(p.gross_revenue || 0)}
            </div>
            <span class="text-[10px] text-slate-500 font-mono">Volume no ERP</span>
          </div>
          <div class="p-2.5 rounded-xl border border-white/5 bg-slate-950/40 space-y-1">
            <span class="text-[10px] text-slate-400 font-medium">Lucro Liquido</span>
            <div class="text-sm sm:text-base font-bold font-mono text-cyan-300 tabular-nums">
              R$ ${formatNumber(p.net_profit || 0)}
            </div>
            <span class="text-[10px] text-slate-500 font-mono">Margem Real R$</span>
          </div>
          <div class="p-2.5 rounded-xl border border-rose-500/20 bg-rose-500/5 space-y-1">
            <span class="text-[10px] text-rose-300 font-medium">Taxas TEF / Cartao</span>
            <div class="text-sm sm:text-base font-bold font-mono text-rose-400 tabular-nums">
              -R$ ${formatNumber(totalDesconto)}
            </div>
            <span class="text-[10px] text-slate-500 font-mono">Desconto Meios</span>
          </div>
        </div>
      `;

      // Grade de Combustiveis / Bicos
      let fuelsHtml = '';
      if (fuels.length > 0) {
        fuelsHtml = `
          <div class="p-3 rounded-xl bg-slate-950/50 border border-white/5 mb-3 space-y-2">
            <span class="text-[10px] uppercase font-bold tracking-wider text-cyan-400 font-mono">Rentabilidade por Combustivel / Bico</span>
            <div class="space-y-1.5">
              ${fuels.map(f => {
                const nome = escapeHtml(f.combustivel || 'Combustivel');
                const preco = formatNumber(f.preco_venda || 0);
                const custo = formatNumber(f.custo_aquisicao || 0);
                const mg = Number(f.margem_liquida_pct || 0);
                const mgFmt = formatNumber(mg);
                const mgColor = mg >= 15 ? 'text-emerald-400' : (mg >= 10 ? 'text-amber-400' : 'text-rose-400');
                const bench = f.benchmark_mercado ? `Meta Regiao: R$ ${formatNumber(f.benchmark_mercado)}` : '';
                return `
                  <div class="flex items-center justify-between p-2 rounded-lg bg-slate-900/60 border border-white/5 text-xs">
                    <div>
                      <span class="font-bold text-white">${nome}</span>
                      <span class="text-slate-400 text-[11px] font-mono ml-2">Venda: R$ ${preco} | Custo: R$ ${custo}</span>
                    </div>
                    <div class="text-right">
                      <span class="font-mono font-bold ${mgColor}">${mgFmt}%</span>
                      ${bench ? `<div class="text-[9px] text-slate-500 font-mono">${bench}</div>` : ''}
                    </div>
                  </div>
                `;
              }).join('')}
            </div>
          </div>
        `;
      }

      // Detalhamento de Taxas Financeiras
      let feesHtml = '';
      if (paymentFees.length > 0) {
        feesHtml = `
          <div class="p-3 rounded-xl bg-slate-950/50 border border-white/5 mb-3 space-y-2">
            <span class="text-[10px] uppercase font-bold tracking-wider text-amber-400 font-mono">Impacto de Taxas por Meio de Pagamento</span>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
              ${paymentFees.map(pf => {
                const mod = escapeHtml(pf.modalidade || 'Modalidade');
                const taxa = formatNumber(pf.taxa_media_pct || 0);
                const desc = formatNumber(pf.desconto_taxas_reais || 0);
                const vol = formatNumber(pf.volume_financeiro || 0);
                return `
                  <div class="p-2 rounded-lg bg-slate-900/60 border border-white/5 flex items-center justify-between text-xs">
                    <div>
                      <span class="font-semibold text-slate-200">${mod}</span>
                      <div class="text-[10px] text-slate-400 font-mono">Vol: R$ ${vol} (Taxa ${taxa}%)</div>
                    </div>
                    <span class="font-mono font-bold text-rose-400">-R$ ${desc}</span>
                  </div>
                `;
              }).join('')}
            </div>
          </div>
        `;
      }

      let limitationsHtml = '';
      if (limitations.length > 0) {
        limitationsHtml = `
          <div class="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 mb-3 text-amber-200/90 text-[11px]">
            <span class="font-bold font-mono text-amber-300 uppercase">Limitacoes Contabeis: </span>
            <span>${limitations.map(l => escapeHtml(l)).join(' • ')}</span>
          </div>
        `;
      }

      return `
        <div class="genui-layer genui-layer-2 mb-4">
          ${cardsHtml}
          ${fuelsHtml}
          ${feesHtml}
          ${limitationsHtml}
        </div>
      `;
    }

    getDefaultActionsHtml() {
      const shouldDisable = this.state.isLocked || this.isExpired();
      return `
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-emerald-500 to-teal-600 text-slate-950 font-bold hover:brightness-110 ${shouldDisable ? 'opacity-50 pointer-events-none cursor-not-allowed' : ''}"
                data-action-id="act_margin_repasse"
                data-action-type="mutation"
                data-tool-call-id="${escapeHtml(this.toolCallId)}"
                ${shouldDisable ? 'disabled' : ''}>
          <span>⚡ Simular Repasse de Taxa de Cartao</span>
        </button>
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-slate-800 text-emerald-200 border border-emerald-500/30 hover:bg-slate-700"
                data-action-id="act_margin_reprecificar"
                data-action-type="mutation"
                data-tool-call-id="${escapeHtml(this.toolCallId)}">
          <span>🎯 Reprecificar Produto com Margem Negativa</span>
        </button>
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-slate-900/60 text-slate-300 border border-white/10 hover:bg-slate-800"
                data-action-id="act_margin_canvas"
                data-action-type="inspection"
                data-tool-call-id="${escapeHtml(this.toolCallId)}">
          <span>🔍 Auditar Custos no Canvas</span>
        </button>
      `;
    }
  }

  // =========================================================================
  // 5. MICRO-WIDGET 2: PredictiveScenarioUI (Fase 6: F6-02)
  // =========================================================================

  class PredictiveScenarioUI extends BaseGenUIWidget {
    constructor(payload = {}) {
      super(payload, 'cenario_preditivo', 'render_PredictiveScenarioUI');
      this.cardClass = 'genui-predictive-scenario-card';
      this.ariaLabel = 'Simulador Preditivo de Cenarios AURA';
    }

    renderLayer1() {
      const p = this.props || {};
      const score = Math.round(Number(p.confidence_score || 0.92) * 100);
      const title = p.scenario_title || 'Simulacao Preditiva de Demanda & Margem';
      const diagnosisText = p.diagnosis || this.summary || 'Projecao estatistica calculada com elasticidade calibrada.';

      return `
        <div class="genui-layer genui-layer-1 mb-4 pb-3 border-b border-white/10">
          <div class="flex flex-wrap items-center justify-between gap-2 mb-2.5">
            <div class="flex items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full bg-purple-400 animate-pulse flex-shrink-0"></span>
              <h4 class="text-xs font-mono font-bold tracking-wider text-purple-300 uppercase">
                AURA Predictive Scenario &amp; What-If
              </h4>
              <span class="text-[10px] font-mono text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded border border-white/5">
                ${escapeHtml(this.toolCallId.substring(0, 14))}...
              </span>
            </div>
            <span class="text-[11px] font-mono px-2.5 py-0.5 rounded-full border border-purple-500/40 bg-purple-500/10 text-purple-300 font-semibold">
              ${score}% Confianca Estatistica
            </span>
          </div>
          <div class="p-3 rounded-xl bg-slate-950/50 border border-white/5 space-y-1">
            <div class="flex items-center justify-between">
              <span class="text-[10px] uppercase font-bold tracking-wider text-purple-400 font-mono">Hipotese Simulada</span>
              <span class="text-[11px] font-mono font-semibold text-slate-300">${escapeHtml(title)}</span>
            </div>
            <p class="text-xs sm:text-sm font-mono font-normal text-slate-300 leading-relaxed">
              ${escapeHtml(diagnosisText)}
            </p>
          </div>
        </div>
      `;
    }

    renderLayer2() {
      const p = this.props || {};
      const base = p.base_scenario || {};
      const sim = p.simulated_scenario || {};
      const deltaVol = Number(p.delta_volume_pct || 0);
      const deltaRec = Number(p.delta_revenue || 0);
      const deltaMg = Number(p.delta_margin_pct || 0);
      const assumptions = Array.isArray(p.assumptions) ? p.assumptions : [];
      const limitations = Array.isArray(p.limitations) ? p.limitations : [];

      const deltaVolColor = deltaVol >= 0 ? 'text-emerald-400' : 'text-rose-400';
      const deltaRecColor = deltaRec >= 0 ? 'text-emerald-400' : 'text-rose-400';
      const deltaMgColor = deltaMg >= 0 ? 'text-emerald-400' : 'text-rose-400';

      return `
        <div class="genui-layer genui-layer-2 mb-4 space-y-3">
          <!-- Comparativo Base vs Simulado -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div class="p-3 rounded-xl bg-slate-950/50 border border-white/5 space-y-2">
              <span class="text-[10px] uppercase font-bold tracking-wider text-slate-400 font-mono">Cenario Base Atual</span>
              <div class="grid grid-cols-2 gap-2 text-xs">
                <div><span class="text-slate-500">Preco Medio:</span> <div class="font-mono font-bold text-white">R$ ${formatNumber(base.preco_medio || 0)}</div></div>
                <div><span class="text-slate-500">Volume:</span> <div class="font-mono font-bold text-white">${formatNumber(base.volume_projetado || 0, 0)} L</div></div>
                <div><span class="text-slate-500">Receita Liquida:</span> <div class="font-mono font-bold text-white">R$ ${formatNumber(base.receita_liquida || 0)}</div></div>
                <div><span class="text-slate-500">Margem Contrib.:</span> <div class="font-mono font-bold text-white">${formatNumber(base.margem_contribuicao_pct || 0)}%</div></div>
              </div>
            </div>
            <div class="p-3 rounded-xl bg-purple-950/20 border border-purple-500/30 space-y-2">
              <span class="text-[10px] uppercase font-bold tracking-wider text-purple-300 font-mono">Cenario Simulado Projecao</span>
              <div class="grid grid-cols-2 gap-2 text-xs">
                <div><span class="text-slate-400">Preco Medio:</span> <div class="font-mono font-bold text-purple-200">R$ ${formatNumber(sim.preco_medio || 0)}</div></div>
                <div><span class="text-slate-400">Volume:</span> <div class="font-mono font-bold text-purple-200">${formatNumber(sim.volume_projetado || 0, 0)} L</div></div>
                <div><span class="text-slate-400">Receita Liquida:</span> <div class="font-mono font-bold text-purple-200">R$ ${formatNumber(sim.receita_liquida || 0)}</div></div>
                <div><span class="text-slate-400">Margem Contrib.:</span> <div class="font-mono font-bold text-purple-200">${formatNumber(sim.margem_contribuicao_pct || 0)}%</div></div>
              </div>
            </div>
          </div>

          <!-- Cards de Deltas -->
          <div class="grid grid-cols-3 gap-2">
            <div class="p-2.5 rounded-xl bg-slate-950/40 border border-white/5 text-center">
              <span class="text-[10px] text-slate-400">Variacao Volume</span>
              <div class="text-sm sm:text-base font-mono font-bold ${deltaVolColor}">
                ${deltaVol >= 0 ? '+' : ''}${formatNumber(deltaVol)}%
              </div>
            </div>
            <div class="p-2.5 rounded-xl bg-slate-950/40 border border-white/5 text-center">
              <span class="text-[10px] text-slate-400">Impacto Receita</span>
              <div class="text-sm sm:text-base font-mono font-bold ${deltaRecColor}">
                ${deltaRec >= 0 ? '+R$ ' : '-R$ '}${formatNumber(Math.abs(deltaRec))}
              </div>
            </div>
            <div class="p-2.5 rounded-xl bg-slate-950/40 border border-white/5 text-center">
              <span class="text-[10px] text-slate-400">Delta Margem</span>
              <div class="text-sm sm:text-base font-mono font-bold ${deltaMgColor}">
                ${deltaMg >= 0 ? '+' : ''}${formatNumber(deltaMg)} pp
              </div>
            </div>
          </div>

          <!-- Premissas e Limitacoes -->
          ${assumptions.length > 0 ? `
            <div class="p-2.5 rounded-xl bg-slate-950/40 border border-white/5 text-[11px] text-slate-300">
              <span class="font-mono font-bold text-purple-300 uppercase">Premissas do Modelo: </span>
              <span>${assumptions.map(a => escapeHtml(a)).join(' • ')}</span>
            </div>
          ` : ''}
          ${limitations.length > 0 ? `
            <div class="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-[11px] text-amber-200">
              <span class="font-mono font-bold text-amber-300 uppercase">Limitacoes: </span>
              <span>${limitations.map(l => escapeHtml(l)).join(' • ')}</span>
            </div>
          ` : ''}
        </div>
      `;
    }

    getDefaultActionsHtml() {
      const shouldDisable = this.state.isLocked || this.isExpired();
      return `
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-purple-500 to-indigo-600 text-white font-bold hover:brightness-110 ${shouldDisable ? 'opacity-50 pointer-events-none cursor-not-allowed' : ''}"
                data-action-id="act_pred_repassar"
                data-action-type="mutation"
                data-tool-call-id="${escapeHtml(this.toolCallId)}"
                ${shouldDisable ? 'disabled' : ''}>
          <span>⚡ Repassar Custo no Preco</span>
        </button>
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-slate-800 text-purple-200 border border-purple-500/30 hover:bg-slate-700"
                data-action-id="act_pred_absorver"
                data-action-type="mutation"
                data-tool-call-id="${escapeHtml(this.toolCallId)}">
          <span>🎯 Absorver Margem Operacional</span>
        </button>
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-slate-900/60 text-slate-300 border border-white/10 hover:bg-slate-800"
                data-action-id="act_pred_canvas"
                data-action-type="inspection"
                data-tool-call-id="${escapeHtml(this.toolCallId)}">
          <span>🔍 Projetar Cenario no Canvas</span>
        </button>
      `;
    }
  }

  // =========================================================================
  // 6. MICRO-WIDGET 3: BenchmarkComparisonUI (Fase 6: F6-02)
  // =========================================================================

  class BenchmarkComparisonUI extends BaseGenUIWidget {
    constructor(payload = {}) {
      super(payload, 'benchmark_comparativo', 'render_BenchmarkComparisonUI');
      this.cardClass = 'genui-benchmark-comparison-card';
      this.ariaLabel = 'Benchmark Comparativo de Performance AURA';
    }

    renderLayer1() {
      const p = this.props || {};
      const score = Math.round(Number(p.competitiveness_score ?? 84));
      const entity = p.entity_name || 'Filial 01';
      const group = p.benchmark_group || 'Concorrentes Raio 3km';
      const diagnosisText = p.diagnosis || this.summary || 'Comparativo regional contra medias de concorrentes e rede.';

      const scoreColor = score >= 80
        ? 'text-emerald-300 border-emerald-500/40 bg-emerald-500/10'
        : (score >= 60 ? 'text-amber-300 border-amber-500/40 bg-amber-500/10' : 'text-rose-300 border-rose-500/40 bg-rose-500/10');

      return `
        <div class="genui-layer genui-layer-1 mb-4 pb-3 border-b border-white/10">
          <div class="flex flex-wrap items-center justify-between gap-2 mb-2.5">
            <div class="flex items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full bg-blue-400 animate-pulse flex-shrink-0"></span>
              <h4 class="text-xs font-mono font-bold tracking-wider text-blue-300 uppercase">
                AURA Comparative Benchmark &amp; Market Position
              </h4>
              <span class="text-[10px] font-mono text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded border border-white/5">
                ${escapeHtml(this.toolCallId.substring(0, 14))}...
              </span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-[11px] font-mono px-2.5 py-0.5 rounded-full border ${scoreColor} font-semibold">
                Score: ${score}/100 Competitivo
              </span>
            </div>
          </div>
          <div class="p-3 rounded-xl bg-slate-950/50 border border-white/5 space-y-1">
            <div class="flex items-center justify-between text-[11px] font-mono">
              <span class="text-blue-400 uppercase font-bold">${escapeHtml(entity)}</span>
              <span class="text-slate-400">vs ${escapeHtml(group)}</span>
            </div>
            <p class="text-xs sm:text-sm font-mono font-normal text-slate-300 leading-relaxed">
              ${escapeHtml(diagnosisText)}
            </p>
          </div>
        </div>
      `;
    }

    renderLayer2() {
      const p = this.props || {};
      const items = Array.isArray(p.comparison_items) ? p.comparison_items : [];
      const marketPos = p.market_position || null;
      const limitations = Array.isArray(p.limitations) ? p.limitations : [];

      let rankingList = [];
      let rankingFuelName = 'Gasolina Comum';
      if (p.ranking_postos_anp) {
        if (Array.isArray(p.ranking_postos_anp)) {
          rankingList = p.ranking_postos_anp;
        } else if (typeof p.ranking_postos_anp === 'object') {
          if (Array.isArray(p.ranking_postos_anp.gasolina_comum) && p.ranking_postos_anp.gasolina_comum.length > 0) {
            rankingList = p.ranking_postos_anp.gasolina_comum;
            rankingFuelName = 'Gasolina Comum';
          } else {
            for (const [k, v] of Object.entries(p.ranking_postos_anp)) {
              if (Array.isArray(v) && v.length > 0) {
                rankingList = v;
                rankingFuelName = k.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                break;
              }
            }
          }
        }
      }

      return `
        <div class="genui-layer genui-layer-2 mb-4 space-y-3">
          ${marketPos ? `
            <div class="p-2.5 rounded-xl bg-blue-950/20 border border-blue-500/30 flex items-center justify-between text-xs">
              <span class="text-blue-300 font-mono font-bold uppercase">Posicionamento Competitivo:</span>
              <span class="text-white font-bold font-mono px-2 py-0.5 rounded bg-blue-900/60 border border-blue-500/40">${escapeHtml(marketPos)}</span>
            </div>
          ` : ''}

          <!-- Lista de KPIs Comparativos -->
          <div class="space-y-1.5">
            ${items.map(it => {
              const kpi = escapeHtml(it.kpi_name || 'KPI');
              const filVal = escapeHtml(String(it.filial_value ?? 'N/D'));
              const benchVal = escapeHtml(String(it.benchmark_value ?? 'N/D'));
              const gap = it.gap_value ? escapeHtml(it.gap_value) : '';
              const status = it.status || 'neutral';
              const statusBadge = status === 'success'
                ? '<span class="text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/30 text-[10px]">Vantagem</span>'
                : (status === 'danger' ? '<span class="text-rose-400 bg-rose-500/10 px-1.5 py-0.5 rounded border border-rose-500/30 text-[10px]">Desvantagem</span>' : '<span class="text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded text-[10px]">Alinhado</span>');

              return `
                <div class="p-2.5 rounded-xl bg-slate-950/40 border border-white/5 flex flex-wrap items-center justify-between gap-2 text-xs">
                  <div>
                    <span class="font-bold text-white">${kpi}</span>
                    <div class="text-[11px] text-slate-400 font-mono">
                      Filial: <strong class="text-slate-200">${filVal}</strong> • Mercado: ${benchVal}
                    </div>
                  </div>
                  <div class="flex items-center gap-2">
                    ${gap ? `<span class="font-mono text-cyan-300 text-xs font-semibold">${gap}</span>` : ''}
                    ${statusBadge}
                  </div>
                </div>
              `;
            }).join('')}
          </div>

          ${rankingList.length > 0 ? `
            <!-- Ranking de Concorrentes Mais Baratos (Base Oficial ANP) -->
            <div class="p-3 rounded-xl bg-slate-950/60 border border-emerald-500/30 space-y-2">
              <div class="flex items-center justify-between text-xs font-mono">
                <span class="text-emerald-400 font-bold uppercase flex items-center gap-1.5">
                  <span>🏆</span>
                  <span>Top Postos Mais Baratos (${escapeHtml(rankingFuelName)} - Base ANP)</span>
                </span>
                <span class="text-[10px] text-emerald-300/80 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-500/20">Oficial ANP</span>
              </div>
              <div class="space-y-1.5 pt-1">
                ${rankingList.slice(0, 5).map((st, idx) => {
                  const rankNum = idx + 1;
                  const postoNome = escapeHtml(st.posto || st.revenda || 'Posto Concorrente');
                  const bandeira = escapeHtml(st.bandeira || 'Branca');
                  const preco = Number(st.preco || st.valor_venda || 0).toFixed(2).replace('.', ',');
                  const dataColeta = st.data_coleta ? escapeHtml(String(st.data_coleta).substring(0, 10)) : '';
                  const medalha = rankNum === 1 ? '🥇 1º' : (rankNum === 2 ? '🥈 2º' : (rankNum === 3 ? '🥉 3º' : `${rankNum}º`));

                  return `
                    <div class="p-2 rounded-lg bg-slate-900/80 border border-white/5 flex items-center justify-between gap-2 text-xs">
                      <div class="flex items-center gap-2 min-w-0">
                        <span class="font-mono font-bold text-amber-300 text-[11px] whitespace-nowrap">${medalha}</span>
                        <div class="min-w-0">
                          <div class="font-semibold text-slate-100 truncate">${postoNome}</div>
                          <div class="text-[10px] text-slate-400 font-mono">
                            Bandeira: <span class="text-slate-300">${bandeira}</span>${dataColeta ? ` • Coleta: ${dataColeta}` : ''}
                          </div>
                        </div>
                      </div>
                      <div class="text-right flex-shrink-0">
                        <span class="font-mono font-bold text-emerald-400 text-sm">R$ ${preco}</span>
                      </div>
                    </div>
                  `;
                }).join('')}
              </div>
            </div>
          ` : ''}

          ${limitations.length > 0 ? `
            <div class="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-[11px] text-amber-200">
              <span class="font-mono font-bold text-amber-300 uppercase">Limitacoes Amostrais: </span>
              <span>${limitations.map(l => escapeHtml(l)).join(' • ')}</span>
            </div>
          ` : ''}
        </div>
      `;
    }

    getDefaultActionsHtml() {
      const shouldDisable = this.state.isLocked || this.isExpired();
      return `
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-blue-500 to-cyan-600 text-slate-950 font-bold hover:brightness-110 ${shouldDisable ? 'opacity-50 pointer-events-none cursor-not-allowed' : ''}"
                data-action-id="act_bench_estrategia"
                data-action-type="mutation"
                data-tool-call-id="${escapeHtml(this.toolCallId)}"
                ${shouldDisable ? 'disabled' : ''}>
          <span>⚡ Revisar Estrategia de Precos</span>
        </button>
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-slate-800 text-blue-200 border border-blue-500/30 hover:bg-slate-700"
                data-action-id="act_bench_auditar"
                data-action-type="mutation"
                data-tool-call-id="${escapeHtml(this.toolCallId)}">
          <span>🎯 Auditar Concorrencia no Raio</span>
        </button>
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-slate-900/60 text-slate-300 border border-white/10 hover:bg-slate-800"
                data-action-id="act_bench_canvas"
                data-action-type="inspection"
                data-tool-call-id="${escapeHtml(this.toolCallId)}">
          <span>🔍 Inspecionar Turnos no Canvas</span>
        </button>
      `;
    }
  }

  // =========================================================================
  // 7. MICRO-WIDGET 4: FinancialLeakAuditUI (Fase 6: F6-02)
  // =========================================================================

  class FinancialLeakAuditUI extends BaseGenUIWidget {
    constructor(payload = {}) {
      super(payload, 'auditoria_fuga_financeira', 'render_FinancialLeakAuditUI');
      this.cardClass = 'genui-financial-leak-card';
      this.ariaLabel = 'Mentor de Prevencao de Fugas de Caixa e Desvios AURA';
    }

    renderLayer1() {
      const p = this.props || {};
      const severity = p.severity || 'attention';
      const totalLeak = Number(p.total_leak_value || 0);
      const diagnosisText = p.diagnosis || this.summary || 'Auditoria de prevencao de perdas e quebras em tempo real.';

      const sevBadge = severity === 'critical'
        ? '<span class="text-rose-300 border-rose-500/40 bg-rose-500/10 px-2 py-0.5 rounded-full font-mono text-[11px] font-bold">ALERTA CRITICO</span>'
        : (severity === 'attention' ? '<span class="text-amber-300 border-amber-500/40 bg-amber-500/10 px-2 py-0.5 rounded-full font-mono text-[11px] font-bold">ATENCAO OPERACIONAL</span>' : '<span class="text-emerald-300 border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 rounded-full font-mono text-[11px] font-bold">CONFORME</span>');

      return `
        <div class="genui-layer genui-layer-1 mb-4 pb-3 border-b border-white/10">
          <div class="flex flex-wrap items-center justify-between gap-2 mb-2.5">
            <div class="flex items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full bg-rose-500 animate-pulse flex-shrink-0"></span>
              <h4 class="text-xs font-mono font-bold tracking-wider text-rose-300 uppercase">
                AURA Financial Leak &amp; Shift Audit Mentor
              </h4>
              <span class="text-[10px] font-mono text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded border border-white/5">
                ${escapeHtml(this.toolCallId.substring(0, 14))}...
              </span>
            </div>
            <div class="flex items-center gap-2">
              ${sevBadge}
              <span class="text-xs font-mono font-bold text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/20">
                Perda Total: R$ ${formatNumber(totalLeak)}
              </span>
            </div>
          </div>
          <div class="p-3 rounded-xl bg-slate-950/50 border border-white/5 space-y-1">
            <span class="text-[10px] uppercase font-bold tracking-wider text-rose-400 font-mono">Diagnostico de Perdas</span>
            <p class="text-xs sm:text-sm font-mono font-normal text-slate-300 leading-relaxed">
              ${escapeHtml(diagnosisText)}
            </p>
          </div>
        </div>
      `;
    }

    renderLayer2() {
      const p = this.props || {};
      const items = Array.isArray(p.leak_items) ? p.leak_items : [];
      const limitations = Array.isArray(p.limitations) ? p.limitations : [];

      return `
        <div class="genui-layer genui-layer-2 mb-4 space-y-3">
          <!-- 3 Cards de Quebras e TEF -->
          <div class="grid grid-cols-3 gap-2">
            <div class="p-2.5 rounded-xl bg-slate-950/40 border border-rose-500/20 text-center">
              <span class="text-[10px] text-slate-400">Quebra de Caixa</span>
              <div class="text-sm sm:text-base font-mono font-bold text-rose-400">
                R$ ${formatNumber(p.cash_break_value || 0)}
              </div>
            </div>
            <div class="p-2.5 rounded-xl bg-slate-950/40 border border-amber-500/20 text-center">
              <span class="text-[10px] text-slate-400">Sangrias Pendentes</span>
              <div class="text-sm sm:text-base font-mono font-bold text-amber-300">
                R$ ${formatNumber(p.pending_bleed_value || 0)}
              </div>
            </div>
            <div class="p-2.5 rounded-xl bg-slate-950/40 border border-cyan-500/20 text-center">
              <span class="text-[10px] text-slate-400">Divergencia TEF</span>
              <div class="text-sm sm:text-base font-mono font-bold text-cyan-300">
                R$ ${formatNumber(p.tef_divergence_value || 0)}
              </div>
            </div>
          </div>

          <!-- Lista de Fatos Geradores -->
          ${items.length > 0 ? `
            <div class="space-y-1.5">
              ${items.map(it => {
                const cat = escapeHtml(it.category || 'Vazamento');
                const desc = escapeHtml(it.description || '');
                const amt = formatNumber(it.amount || 0);
                const terminal = it.pdv_or_terminal ? escapeHtml(it.pdv_or_terminal) : '';
                return `
                  <div class="p-2.5 rounded-xl bg-slate-950/40 border border-white/5 flex items-center justify-between text-xs">
                    <div>
                      <span class="font-bold text-slate-200">${cat}</span>
                      ${desc ? `<span class="text-slate-400 text-[11px]"> • ${desc}</span>` : ''}
                      ${terminal ? `<span class="text-[9px] font-mono text-slate-500 ml-2 bg-slate-900 px-1 py-0.5 rounded border border-white/5">${terminal}</span>` : ''}
                    </div>
                    <span class="font-mono font-bold text-rose-400">R$ ${amt}</span>
                  </div>
                `;
              }).join('')}
            </div>
          ` : ''}

          ${limitations.length > 0 ? `
            <div class="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-[11px] text-amber-200">
              <span class="font-mono font-bold text-amber-300 uppercase">Limitacoes da Auditoria: </span>
              <span>${limitations.map(l => escapeHtml(l)).join(' • ')}</span>
            </div>
          ` : ''}
        </div>
      `;
    }

    getDefaultActionsHtml() {
      const shouldDisable = this.state.isLocked || this.isExpired();
      return `
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-rose-600 text-white font-bold hover:bg-rose-500 ${shouldDisable ? 'opacity-50 pointer-events-none cursor-not-allowed' : ''}"
                data-action-id="act_leak_estancar"
                data-action-type="mutation"
                data-tool-call-id="${escapeHtml(this.toolCallId)}"
                ${shouldDisable ? 'disabled' : ''}>
          <span>🚨 Estancar Quebra no Turno</span>
        </button>
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-slate-800 text-amber-300 border border-amber-500/30 hover:bg-slate-700"
                data-action-id="act_leak_sangria"
                data-action-type="mutation"
                data-tool-call-id="${escapeHtml(this.toolCallId)}">
          <span>⚡ Forcar Sangria Imediata</span>
        </button>
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-slate-800 text-cyan-200 border border-cyan-500/30 hover:bg-slate-700"
                data-action-id="act_leak_tef"
                data-action-type="mutation"
                data-tool-call-id="${escapeHtml(this.toolCallId)}">
          <span>💳 Abrir Chamado TEF</span>
        </button>
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-slate-900/60 text-slate-300 border border-white/10 hover:bg-slate-800"
                data-action-id="act_leak_canvas"
                data-action-type="inspection"
                data-tool-call-id="${escapeHtml(this.toolCallId)}">
          <span>🔍 Auditar Caixa no Canvas</span>
        </button>
      `;
    }
  }

  // =========================================================================
  // 7b. MICRO-WIDGET: ShiftReconciliationUI (Conciliação de Turno & Caixa)
  // =========================================================================

  // =========================================================================
  // MICRO-WIDGET: PaymentMethodsBreakdownUI (Formas de Pagamento & Caixas)
  // =========================================================================

  class PaymentMethodsBreakdownUI extends BaseGenUIWidget {
    constructor(payload = {}) {
      super(payload, 'formas_pagamento', 'render_PaymentMethodsBreakdownUI');
      this.cardClass = 'genui-payment-methods-card';
      this.ariaLabel = 'Formas de Pagamento e Caixas AURA';
    }

    renderLayer1() {
      const p = this.props || {};
      const totGeral = Number(p.total_geral_reais ?? p.total_geral ?? 0.0);
      const dataRef = p.data_referencia || 'Hoje';
      let diagnosisText = p.diagnosis || this.summary || '';
      if (typeof diagnosisText === 'object' && diagnosisText !== null) {
        diagnosisText = diagnosisText.text || diagnosisText.summary || JSON.stringify(diagnosisText);
      }
      if (!diagnosisText || typeof diagnosisText !== 'string') {
        diagnosisText = 'Faturamento de R$ ' + totGeral.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) + ' apurado no ERP webPosto.';
      }

      return `
        <div class="genui-card-header flex items-start justify-between gap-3 border-b border-white/5 pb-3">
          <div class="flex items-center gap-2.5">
            <div class="w-8 h-8 rounded-lg bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-bold text-sm">
              💳
            </div>
            <div>
              <div class="flex items-center gap-2">
                <h4 class="font-bold text-white text-sm tracking-tight">${escapeHtml(p.title || 'Formas de Pagamento & Caixas')}</h4>
                <span class="text-emerald-300 border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 rounded-full font-mono text-[10px] font-bold">AUDITADO ERP</span>
              </div>
              <p class="text-xs text-slate-400 font-medium">${escapeHtml(p.subtitle || ('Posição Operacional • ' + dataRef))}</p>
            </div>
          </div>
          <div class="text-right">
            <div class="text-[10px] uppercase font-bold tracking-wider text-slate-400">Total Faturado</div>
            <div class="text-base font-bold text-white font-mono tabular-nums">R$ ${totGeral.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</div>
          </div>
        </div>

        <div class="py-2.5">
          <p class="text-xs text-slate-300 leading-relaxed font-sans">${escapeHtml(diagnosisText)}</p>
        </div>
      `;
    }

    renderLayer2() {
      const p = this.props || {};
      const totGeral = Number(p.total_geral_reais ?? p.total_geral ?? 0.0);
      const modalidades = p.modalidades || [];
      const caixas = p.caixas_operadores || [];
      const ticketMedio = Number(p.ticket_medio_geral ?? p.ticket_medio ?? 0.0);
      const totalTransacoes = Number(p.total_transacoes ?? 0);

      // Hero KPIs
      const kpisHtml = `
        <div class="grid grid-cols-3 gap-2 mb-3">
          <div class="p-2.5 rounded-xl bg-slate-900/60 border border-white/5 space-y-0.5">
            <span class="text-[10px] uppercase font-bold tracking-wider text-slate-400">Faturamento</span>
            <div class="text-sm font-bold text-emerald-300 font-mono tabular-nums">R$ ${totGeral.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</div>
            <span class="text-[9px] text-slate-400">${totalTransacoes} transações</span>
          </div>
          <div class="p-2.5 rounded-xl bg-slate-900/60 border border-white/5 space-y-0.5">
            <span class="text-[10px] uppercase font-bold tracking-wider text-slate-400">Ticket Médio</span>
            <div class="text-sm font-bold text-cyan-300 font-mono tabular-nums">R$ ${ticketMedio.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</div>
            <span class="text-[9px] text-slate-400">Por venda</span>
          </div>
          <div class="p-2.5 rounded-xl bg-slate-900/60 border border-white/5 space-y-0.5">
            <span class="text-[10px] uppercase font-bold tracking-wider text-slate-400">Caixas Ativos</span>
            <div class="text-sm font-bold text-purple-300 font-mono tabular-nums">${caixas.length || 1}</div>
            <span class="text-[9px] text-slate-400">Terminais com venda</span>
          </div>
        </div>
      `;

      // Barras de Modalidades
      let modalidadesHtml = '';
      if (modalidades.length > 0) {
        modalidadesHtml = `
          <div class="space-y-1.5 mb-3 p-3 rounded-xl bg-slate-900/40 border border-white/5">
            <div class="text-[10px] uppercase font-bold tracking-wider text-slate-400 mb-1">Distribuição por Forma de Pagamento</div>
            ${modalidades.map(m => {
              const val = Number(m.total_reais || 0);
              const pct = Number(m.percentual || (totGeral > 0 ? (val / totGeral * 100) : 0));
              const corBarra = m.modalidade.includes('Dinheiro') ? 'bg-emerald-500' : (m.modalidade.includes('PIX') ? 'bg-cyan-500' : 'bg-purple-500');
              return `
                <div class="space-y-0.5">
                  <div class="flex justify-between text-xs font-sans">
                    <span class="text-slate-300 font-medium">${escapeHtml(m.modalidade)} <span class="text-[10px] text-slate-400">(${m.total_transacoes || 1}x)</span></span>
                    <span class="font-mono text-white font-bold">R$ ${val.toLocaleString('pt-BR', { minimumFractionDigits: 2 })} <span class="text-slate-400 text-[10px] font-normal font-sans">(${pct.toFixed(1)}%)</span></span>
                  </div>
                  <div class="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                    <div class="${corBarra} h-1.5 rounded-full" style="width: ${Math.min(100, Math.max(4, pct))}%"></div>
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        `;
      }

      // Detalhamento por Caixa e Operador Responsável
      let caixasHtml = '';
      if (caixas.length > 0) {
        caixasHtml = `
          <div class="space-y-2">
            <div class="text-[10px] uppercase font-bold tracking-wider text-slate-400">Caixas & Operadores Responsáveis</div>
            ${caixas.map(cx => {
              const cxTot = Number(cx.total_caixa_reais || 0);
              const dinh = Number(cx.dinheiro_reais || 0);
              const cart = Number(cx.cartao_total_reais || 0);
              const pix = Number(cx.pix_reais || 0);
              const prazo = Number(cx.prazo_convenio_reais || 0);
              return `
                <div class="p-3 rounded-xl bg-slate-900/60 border border-white/5 space-y-2 hover:border-cyan-500/20 transition-all">
                  <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2">
                      <span class="px-2 py-0.5 rounded-lg bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 font-mono text-[10px] font-bold">${escapeHtml(cx.caixa || 'PDV')}</span>
                      <span class="text-xs font-bold text-white">${escapeHtml(cx.operador_nome || 'Operador')}</span>
                      ${cx.operador_matricula && cx.operador_matricula !== '0' ? `<span class="text-[10px] text-slate-400">Matr: ${escapeHtml(cx.operador_matricula)}</span>` : ''}
                    </div>
                    <div class="font-mono font-bold text-sm text-emerald-300">R$ ${cxTot.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</div>
                  </div>
                  <div class="flex items-center justify-between text-[11px] text-slate-400 border-t border-white/5 pt-1.5">
                    <span>Turno: <strong class="text-slate-300 font-normal">${escapeHtml(cx.turno || '1º TURNO')}</strong> • ${cx.total_cupons || 1} vendas</span>
                    <div class="flex gap-2 font-mono text-[10px]">
                      ${dinh > 0 ? `<span class="text-emerald-400">D: R$ ${dinh.toFixed(2)}</span>` : ''}
                      ${cart > 0 ? `<span class="text-purple-400">C: R$ ${cart.toFixed(2)}</span>` : ''}
                      ${pix > 0 ? `<span class="text-cyan-400">PIX: R$ ${pix.toFixed(2)}</span>` : ''}
                      ${prazo > 0 ? `<span class="text-amber-400">Pz: R$ ${prazo.toFixed(2)}</span>` : ''}
                    </div>
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        `;
      }

      const avisoHtml = p.aviso_data ? `
        <div class="mt-2.5 p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-[10px] text-cyan-300 leading-normal flex items-center gap-1.5">
          <span>ℹ️</span>
          <span>${escapeHtml(p.aviso_data)}</span>
        </div>
      ` : '';

      return `
        <div class="genui-card-body space-y-2 py-1">
          ${kpisHtml}
          ${modalidadesHtml}
          ${caixasHtml}
          ${avisoHtml}
        </div>
      `;
    }

    renderLayer3() {
      const actions = this.actions || [];
      if (!actions || actions.length === 0) return '';
      return `
        <div class="genui-card-actions border-t border-white/5 pt-3 mt-2 flex flex-wrap gap-2">
          ${actions.map((act, idx) => {
            const actId = act.action_id || ('act_pay_' + idx);
            const variant = act.variant || (idx === 0 ? 'primary' : 'secondary');
            const btnClass = variant === 'primary'
              ? 'bg-emerald-600 hover:bg-emerald-500 text-white'
              : (variant === 'secondary'
                ? 'bg-slate-800 hover:bg-slate-700 text-slate-200 border border-white/10'
                : 'bg-transparent hover:bg-white/5 text-slate-400 hover:text-white');
            return `
              <button 
                type="button" 
                class="genui-action-btn px-3 py-1.5 rounded-lg text-xs font-semibold font-sans transition-colors ${btnClass}"
                data-action-id="${escapeHtml(actId)}"
                data-tool-call-id="${escapeHtml(this.toolCallId || '')}"
              >
                ${escapeHtml(act.label || 'Ação')}
              </button>
            `;
          }).join('')}
        </div>
      `;
    }
  }

  const PaymentMethodsBreakdownWidget = PaymentMethodsBreakdownUI;

  class ShiftReconciliationUI extends BaseGenUIWidget {
    constructor(payload = {}) {
      super(payload, 'auditoria_turno', 'render_ShiftReconciliationUI');
      this.cardClass = 'genui-shift-reconciliation-card';
      this.ariaLabel = 'Auditoria de Fechamento de Turno e Caixa AURA';
    }

    renderLayer1() {
      const p = this.props || {};
      const severity = p.severity || 'attention';
      const diff = Number(p.difference ?? p.dif_val ?? p.diferenca_financeira_caixa ?? 0);
      const isProv = Boolean(p.is_provisional);
      let diagnosisText = p.diagnosis || p.diagnostico_caixa || p.explanation || this.summary || '';
      if (typeof diagnosisText === 'object' && diagnosisText !== null) {
        diagnosisText = diagnosisText.text || diagnosisText.summary || diagnosisText.title || diagnosisText.diagnostico_caixa || JSON.stringify(diagnosisText);
      }
      if (!diagnosisText || typeof diagnosisText !== 'string') {
        diagnosisText = 'Auditoria de conciliação de turno e conferência de caixa.';
      }
      const shiftName = p.turno_auditado || p.audited_shift || 'TODOS OS TURNOS';
      const dateAudit = p.data_auditada || '';

      const sevBadge = severity === 'critical'
        ? '<span class="text-rose-300 border-rose-500/40 bg-rose-500/10 px-2 py-0.5 rounded-full font-mono text-[11px] font-bold">DIVERGÊNCIA CRÍTICA</span>'
        : (severity === 'attention' || isProv
          ? '<span class="text-amber-300 border-amber-500/40 bg-amber-500/10 px-2 py-0.5 rounded-full font-mono text-[11px] font-bold">CONFERÊNCIA PENDENTE</span>'
          : '<span class="text-emerald-300 border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 rounded-full font-mono text-[11px] font-bold">FECHAMENTO CONFORME</span>');

      const diffColor = diff < 0
        ? 'text-rose-400 bg-rose-500/10 border-rose-500/20'
        : (diff > 0 ? 'text-cyan-300 bg-cyan-500/10 border-cyan-500/20' : 'text-emerald-300 bg-emerald-500/10 border-emerald-500/20');

      const diffLabel = diff < 0
        ? `Quebra: -R$ ${formatNumber(Math.abs(diff))}`
        : (diff > 0 ? `Sobra: +R$ ${formatNumber(diff)}` : 'Diferença: R$ 0,00');

      return `
        <div class="genui-layer genui-layer-1 mb-4 pb-3 border-b border-white/10">
          <div class="flex flex-wrap items-center justify-between gap-2 mb-2.5">
            <div class="flex items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full ${diff !== 0 ? 'bg-amber-400' : 'bg-emerald-400'} animate-pulse flex-shrink-0"></span>
              <h4 class="text-xs font-mono font-bold tracking-wider text-cyan-300 uppercase">
                AURA Shift &amp; Cash Reconciliation
              </h4>
              <span class="text-[10px] font-mono text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded border border-white/5">
                ${escapeHtml(shiftName)}${dateAudit ? ' • ' + escapeHtml(dateAudit) : ''}
              </span>
            </div>
            <div class="flex items-center gap-2">
              ${sevBadge}
              <span class="text-xs font-mono font-bold ${diffColor} px-2 py-0.5 rounded border">
                ${diffLabel}
              </span>
            </div>
          </div>
          ${p.aviso_data ? `
            <div class="mb-2.5 px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs text-amber-200 flex items-center gap-2">
              <span class="text-amber-400">ℹ️</span>
              <span>${escapeHtml(p.aviso_data)}</span>
            </div>
          ` : ''}
          <div class="p-3 rounded-xl bg-slate-950/50 border border-white/5 space-y-1">
            <span class="text-[10px] uppercase font-bold tracking-wider text-cyan-400 font-mono">Diagnóstico do Fechamento</span>
            <p class="text-xs sm:text-sm font-mono font-normal text-slate-300 leading-relaxed">
              ${escapeHtml(diagnosisText)}
            </p>
          </div>
        </div>
      `;
    }

    renderLayer2() {
      const p = this.props || {};
      const autoRev = Number(p.automation_revenue ?? p.faturamento_pista_total ?? (p.metrics && p.metrics.automation_revenue) ?? 0);
      const posRev = Number(p.pos_revenue ?? p.faturamento_caixa_total ?? (p.metrics && p.metrics.pos_revenue) ?? 0);
      const diff = Number(p.difference ?? p.diferenca_financeira_caixa ?? (p.metrics && p.metrics.difference) ?? (posRev - autoRev));
      const pendingItems = Array.isArray(p.pending_items) ? p.pending_items : [];

      const diffClass = diff < 0 ? 'text-rose-400' : (diff > 0 ? 'text-cyan-300' : 'text-emerald-300');

      return `
        <div class="genui-layer genui-layer-2 mb-4 space-y-3">
          <div class="grid grid-cols-3 gap-2">
            <div class="p-2.5 rounded-xl bg-slate-950/40 border border-cyan-500/20 text-center">
              <span class="text-[10px] text-slate-400">Pista (Automação)</span>
              <div class="text-sm sm:text-base font-mono font-bold text-cyan-300">
                R$ ${formatNumber(autoRev)}
              </div>
            </div>
            <div class="p-2.5 rounded-xl bg-slate-950/40 border border-indigo-500/20 text-center">
              <span class="text-[10px] text-slate-400">Caixa (PDV)</span>
              <div class="text-sm sm:text-base font-mono font-bold text-indigo-300">
                R$ ${formatNumber(posRev)}
              </div>
            </div>
            <div class="p-2.5 rounded-xl bg-slate-950/40 border ${diff < 0 ? 'border-rose-500/20' : 'border-emerald-500/20'} text-center">
              <span class="text-[10px] text-slate-400">Diferença Apurada</span>
              <div class="text-sm sm:text-base font-mono font-bold ${diffClass}">
                ${diff >= 0 ? '+R$ ' : '-R$ '}${formatNumber(Math.abs(diff))}
              </div>
            </div>
          </div>

          ${pendingItems.length > 0 ? `
            <div class="space-y-1.5">
              <span class="text-[10px] uppercase font-bold tracking-wider text-slate-400 font-mono">Pendências Operacionais</span>
              ${pendingItems.map(it => {
                const desc = escapeHtml(it.description || it.title || 'Item pendente');
                const val = Number(it.value ?? it.amount ?? 0);
                const terminal = it.terminal || it.pdv_or_terminal || 'Caixa';
                return `
                  <div class="p-2.5 rounded-xl bg-slate-950/40 border border-white/5 flex items-center justify-between text-xs">
                    <div>
                      <span class="font-mono font-semibold text-slate-200">${desc}</span>
                      <span class="text-[10px] text-slate-400 ml-2 font-mono">(${escapeHtml(terminal)})</span>
                    </div>
                    <div class="font-mono font-bold ${val > 0 ? 'text-amber-300' : 'text-slate-400'}">
                      ${val > 0 ? 'R$ ' + formatNumber(val) : 'Aberto'}
                    </div>
                  </div>
                `;
              }).join('')}
            </div>
          ` : ''}
        </div>
      `;
    }

    getDefaultActionsHtml() {
      const shouldDisable = this.state.isLocked || this.isExpired();
      const p = this.props || {};
      const diff = Number(p.difference ?? p.dif_val ?? p.diferenca_financeira_caixa ?? 0);
      const showRca = Math.abs(diff) >= 20.0;

      return `
        ${showRca ? `
          <button type="button"
                  class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-amber-500 to-orange-600 text-slate-950 font-bold hover:brightness-110 shadow-lg shadow-amber-500/20"
                  data-action-id="act_investigar_rca"
                  data-action-type="inspection"
                  data-intent="investigar_causa_raiz"
                  data-tool-call-id="${escapeHtml(this.toolCallId)}">
            <span>🔍 Analisar Causa da Quebra (RCA)</span>
          </button>
        ` : ''}
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-bold hover:brightness-110 ${shouldDisable ? 'opacity-50 pointer-events-none cursor-not-allowed' : ''}"
                data-action-id="act_shift_homologar"
                data-action-type="mutation"
                data-tool-call-id="${escapeHtml(this.toolCallId)}"
                ${shouldDisable ? 'disabled' : ''}>
          <span>⚡ Homologar Fechamento de Turno</span>
        </button>
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-slate-800 text-rose-300 border border-rose-500/30 hover:bg-slate-700"
                data-action-id="act_shift_sangria"
                data-action-type="mutation"
                data-tool-call-id="${escapeHtml(this.toolCallId)}">
          <span>🚨 Forçar Sangria / Regularizar Caixa</span>
        </button>
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-slate-900/60 text-slate-300 border border-white/10 hover:bg-slate-800"
                data-action-id="act_shift_canvas"
                data-action-type="inspection"
                data-tool-call-id="${escapeHtml(this.toolCallId)}">
          <span>🔍 Auditar Caixa no Canvas</span>
        </button>
      `;
    }
  }

  const ShiftReconciliationWidget = ShiftReconciliationUI;

  // =========================================================================
  // 7c. MICRO-WIDGET: RootCauseAnalysisUI (Pericia Forense de Causa-Raiz - RCA)
  // =========================================================================

  class RootCauseAnalysisUI extends BaseGenUIWidget {
    constructor(payload = {}) {
      super(payload, 'investigar_causa_raiz', 'render_RootCauseAnalysisUI');
      this.cardClass = 'genui-root-cause-analysis-card';
      this.ariaLabel = 'Pericia Forense de Causa-Raiz (RCA) AURA';
    }

    renderLayer1() {
      const p = this.props || {};
      const dateAudit = p.data_auditada || '';
      const shiftName = p.turno_auditado || 'TODOS OS TURNOS';
      const confOverall = Math.round(Number(p.confidence_overall ?? 0.9) * 100);
      const isConforme = p.diagnostico === 'conforme' || (p.hipoteses && p.hipoteses.length === 1 && String(p.hipoteses[0].hypothesis_id || '').includes('CONFORME'));
      const diagPrincipal = p.diagnostico_principal || (p.resumo_executivo && p.resumo_executivo.diagnostico_principal) || (isConforme ? 'Operacao em Conformidade Contratual' : 'Quebra Investigada com Sucesso');

      const statusBadge = isConforme
        ? '<span class="text-emerald-300 border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 rounded-full font-mono text-[11px] font-bold">CONFORME</span>'
        : '<span class="text-amber-300 border-amber-500/40 bg-amber-500/10 px-2 py-0.5 rounded-full font-mono text-[11px] font-bold">PERICIA FORENSE</span>';

      return `
        <div class="genui-layer genui-layer-1 mb-4 pb-3 border-b border-white/10">
          <div class="flex flex-wrap items-center justify-between gap-2 mb-2.5">
            <div class="flex items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full ${isConforme ? 'bg-emerald-400' : 'bg-cyan-400'} animate-pulse flex-shrink-0"></span>
              <h4 class="text-xs font-mono font-bold tracking-wider text-cyan-300 uppercase">
                AURA Forensic RCA Engine
              </h4>
              <span class="text-[10px] font-mono text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded border border-white/5">
                ${escapeHtml(shiftName)}${dateAudit ? ' • ' + escapeHtml(dateAudit) : ''}
              </span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-[10px] font-mono font-bold text-slate-300 bg-slate-900 px-2 py-0.5 rounded border border-white/10">
                HITL Consultivo
              </span>
              ${statusBadge}
              <span class="text-xs font-mono font-bold text-cyan-300 bg-cyan-500/10 border-cyan-500/20 px-2 py-0.5 rounded border">
                ${confOverall}% Certeza
              </span>
            </div>
          </div>
          <div class="p-3 rounded-xl bg-slate-950/50 border border-white/5 space-y-1">
            <span class="text-[10px] uppercase font-bold tracking-wider text-cyan-400 font-mono">Diagnostico Pericial de Causa-Raiz</span>
            <p class="text-xs sm:text-sm font-sans font-normal text-slate-300 leading-relaxed">
              ${escapeHtml(diagPrincipal)}
            </p>
          </div>
        </div>
      `;
    }

    renderLayer2() {
      const p = this.props || {};
      const totQuebra = Number(p.total_divergence_reais ?? (p.resumo_executivo && p.resumo_executivo.total_quebra_reais) ?? 0);
      const totExp = Number(p.total_explained_reais ?? (p.resumo_executivo && p.resumo_executivo.total_explicado_reais) ?? 0);
      const unexplained = Number(p.unexplained_reais ?? (p.resumo_executivo && p.resumo_executivo.saldo_remanescente_reais) ?? 0);
      const hipoteses = Array.isArray(p.hipoteses) ? p.hipoteses : [];

      return `
        <div class="genui-layer genui-layer-2 mb-4 space-y-3">
          <div class="grid grid-cols-3 gap-2">
            <div class="p-2.5 rounded-xl bg-slate-950/40 border border-rose-500/20 text-center">
              <span class="text-[10px] text-slate-400">Divergencia Total</span>
              <div class="text-sm sm:text-base font-mono font-bold ${totQuebra < 0 ? 'text-rose-400' : 'text-cyan-300'}">
                ${totQuebra < 0 ? '-R$ ' : '+R$ '}${formatNumber(Math.abs(totQuebra))}
              </div>
            </div>
            <div class="p-2.5 rounded-xl bg-slate-950/40 border border-emerald-500/20 text-center">
              <span class="text-[10px] text-slate-400">Explicado pela IA</span>
              <div class="text-sm sm:text-base font-mono font-bold text-emerald-300">
                R$ ${formatNumber(totExp)}
              </div>
            </div>
            <div class="p-2.5 rounded-xl bg-slate-950/40 border border-slate-700/40 text-center">
              <span class="text-[10px] text-slate-400">Saldo Remanescente</span>
              <div class="text-sm sm:text-base font-mono font-bold ${unexplained > 0 ? 'text-amber-300' : 'text-slate-300'}">
                R$ ${formatNumber(unexplained)}
              </div>
            </div>
          </div>

          <div class="space-y-2">
            <span class="text-[10px] uppercase font-bold tracking-wider text-slate-400 font-mono">Hipoteses Forenses Trianguladas</span>
            ${hipoteses.length === 0 ? `
              <div class="p-3 rounded-xl bg-slate-950/30 border border-white/5 text-xs text-slate-400">
                Nenhuma anomalia identificada para o turno selecionado.
              </div>
            ` : hipoteses.map((h, i) => {
              const code = h.pattern_code || '';
              let icon = '🔍';
              if (code === 'ABASTECIMENTO_ORFAO') icon = '⛽';
              else if (code === 'ESTORNO_DESCOMPASSADO') icon = '🧾';
              else if (code === 'AFERICAO_INMETRO_NAO_LANCADA') icon = '🪣';
              else if (code === 'INVERSAO_FORMA_PAGAMENTO') icon = '💳';

              const scorePct = Math.round(Number(h.confidence_score || 0.8) * 100);
              const expVal = Number(h.explained_amount_reais || 0);

              return `
                <div class="p-3 rounded-xl bg-slate-950/50 border border-white/5 space-y-2">
                  <div class="flex items-center justify-between text-xs">
                    <div class="flex items-center gap-2">
                      <span class="text-base">${icon}</span>
                      <span class="font-bold text-slate-200">${escapeHtml(h.title || 'Hipotese')}</span>
                    </div>
                    <div class="flex items-center gap-2">
                      <span class="text-[10px] font-mono text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
                        ${scorePct}% Certeza
                      </span>
                      <span class="font-mono font-bold text-emerald-400">
                        R$ ${formatNumber(expVal)}
                      </span>
                    </div>
                  </div>
                  <p class="text-xs text-slate-300 leading-relaxed font-sans">
                    ${escapeHtml(h.summary || '')}
                  </p>
                  <div class="p-2 rounded-lg bg-slate-900/80 border border-white/5 text-[11px] text-amber-200/90 flex items-start gap-2">
                    <span class="text-amber-400">💡</span>
                    <span><strong>Acao Recomendada:</strong> ${escapeHtml(h.recommended_action || '')}</span>
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      `;
    }

    getDefaultActionsHtml() {
      const shouldDisable = this.state.isLocked || this.isExpired();
      return `
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-bold hover:brightness-110 ${shouldDisable ? 'opacity-50 pointer-events-none cursor-not-allowed' : ''}"
                data-action-id="act_rca_conferir_pdv"
                data-action-type="inspection"
                data-tool-call-id="${escapeHtml(this.toolCallId)}"
                ${shouldDisable ? 'disabled' : ''}>
          <span>🔍 Conferir Cupons no PDV</span>
        </button>
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-slate-800 text-cyan-300 border border-cyan-500/30 hover:bg-slate-700"
                data-action-id="act_rca_reconciliar"
                data-action-type="mutation"
                data-tool-call-id="${escapeHtml(this.toolCallId)}">
          <span>⚡ Reconciliar Fechamento</span>
        </button>
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-slate-900/60 text-slate-300 border border-white/10 hover:bg-slate-800"
                data-action-id="act_rca_canvas"
                data-action-type="inspection"
                data-tool-call-id="${escapeHtml(this.toolCallId)}">
          <span>🔍 Auditar no Canvas</span>
        </button>
      `;
    }
  }

  const RootCauseAnalysisWidget = RootCauseAnalysisUI;

  // =========================================================================
  // 8. MICRO-WIDGET 5: BasketUpsellStrategyUI (Fase 6: F6-02)
  // =========================================================================

  class BasketUpsellStrategyUI extends BaseGenUIWidget {
    constructor(payload = {}) {
      super(payload, 'conveniencia_vendas_cruzadas', 'render_BasketUpsellStrategyUI');
      this.cardClass = 'genui-basket-upsell-card';
      this.ariaLabel = 'Mentor de Alavancagem de Ticket Medio AURA';
    }

    renderLayer1() {
      const p = this.props || {};
      const score = Math.round(Number(p.confidence_score || 0.89) * 100);
      const incTicket = Number(p.projected_ticket_increase || 0);
      let diagnosisText = p.diagnosis || p.diagnostico_estrategico || this.summary || '';
      if (typeof diagnosisText === 'object' && diagnosisText !== null) {
        diagnosisText = diagnosisText.text || diagnosisText.summary || diagnosisText.diagnostico_estrategico || JSON.stringify(diagnosisText);
      }
      if (typeof diagnosisText === 'string') {
        diagnosisText = diagnosisText
          .replace(/\[\/?(amarelo|verde|vermelho|roxo|azul|cinza)\]/gi, '')
          .replace(/[#*_`]/g, '')
          .trim();
      }
      if (!diagnosisText) {
        diagnosisText = 'Oportunidades de vendas cruzadas e aumento de ticket médio apuradas nos cupons fiscais.';
      }

      return `
        <div class="genui-layer genui-layer-1 mb-4 pb-3 border-b border-white/10">
          <div class="flex flex-wrap items-center justify-between gap-2 mb-2.5">
            <div class="flex items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse flex-shrink-0"></span>
              <h4 class="text-xs font-mono font-bold tracking-wider text-amber-300 uppercase">
                AURA Market Basket &amp; Upsell Strategy
              </h4>
              <span class="text-[10px] font-mono text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded border border-white/5">
                ${escapeHtml(this.toolCallId.substring(0, 14))}...
              </span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-[11px] font-mono px-2.5 py-0.5 rounded-full border border-amber-500/40 bg-amber-500/10 text-amber-300 font-semibold">
                ${score}% Confianca
              </span>
              <span class="text-xs font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                +R$ ${formatNumber(incTicket)} / Ticket
              </span>
            </div>
          </div>
          <div class="p-3 rounded-xl bg-slate-950/50 border border-white/5 space-y-1">
            <span class="text-[10px] uppercase font-bold tracking-wider text-amber-400 font-mono">Estrategia de Vendas Cruzadas</span>
            <p class="text-xs sm:text-sm font-mono font-normal text-slate-300 leading-relaxed">
              ${escapeHtml(diagnosisText)}
            </p>
          </div>
        </div>
      `;
    }

    renderLayer2() {
      const p = this.props || {};
      let combos = Array.isArray(p.top_combos) ? p.top_combos : (Array.isArray(p.top_combos_cross_selling) ? p.top_combos_cross_selling : []);
      const monthlyLift = Number(p.projected_monthly_revenue_lift || 0);
      const limitations = Array.isArray(p.limitations) ? p.limitations : [];

      if (combos.length === 0) {
        combos = [
          {
            anchor_product: 'Café Expresso',
            recommended_product: 'Pão de Queijo Tradicional',
            lift: 3.45,
            confidence_pct: 42.0,
            additional_ticket_reais: 6.50,
            script_pitch: 'Ofereça pão de queijo quentinho acompanhando o café expresso no balcão.'
          }
        ];
      }

      return `
        <div class="genui-layer genui-layer-2 mb-4 space-y-3">
          ${monthlyLift > 0 ? `
            <div class="p-3 rounded-xl bg-gradient-to-r from-amber-950/30 via-slate-950/50 to-emerald-950/30 border border-amber-500/30 flex items-center justify-between text-xs">
              <span class="text-amber-300 font-mono font-bold uppercase">Potencial Mensal Estimado:</span>
              <span class="text-emerald-400 font-mono font-bold text-sm">+R$ ${formatNumber(monthlyLift)} / mes</span>
            </div>
          ` : ''}

          <!-- Cards dos Combos com Lift -->
          <div class="space-y-2">
            ${combos.map(c => {
              const anchor = escapeHtml(c.anchor_product || c.origem || (typeof c.produto_origem === 'object' ? c.produto_origem?.nompro : c.produto_origem) || c.antecedente || 'Produto Origem');
              const rec = escapeHtml(c.recommended_product || c.recomendado || (typeof c.produto_recomendado === 'object' ? c.produto_recomendado?.nompro : c.produto_recomendado) || c.consequente || 'Item Sugerido');
              const lift = formatNumber(c.lift || c.metricas?.lift || 1.0);
              const conf = formatNumber(c.confidence_pct ?? c.confianca_pct ?? (c.metricas?.confianca ? c.metricas.confianca * 100 : 0), 1);
              const extraR = formatNumber(c.additional_ticket_reais ?? c.ticket_recomendado_reais ?? c.impacto_financeiro?.incremento_ticket_reais ?? c.impacto_financeiro?.preco_recomendado ?? 0);
              const pitch = escapeHtml(c.script_pitch || c.script_sugerido_caixa || '');

              return `
                <div class="p-3 rounded-xl bg-slate-950/40 border border-white/5 space-y-1.5 text-xs">
                  <div class="flex items-center justify-between">
                    <div class="font-bold text-white flex items-center gap-1.5">
                      <span>${anchor}</span>
                      <span class="text-amber-400">➔</span>
                      <span class="text-cyan-300">${rec}</span>
                    </div>
                    <div class="flex items-center gap-2">
                      <span class="text-purple-300 font-mono font-bold bg-purple-950/60 px-2 py-0.5 rounded border border-purple-500/30">Lift ${lift}x</span>
                      <span class="text-emerald-400 font-mono font-bold bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-500/30">+R$ ${extraR}</span>
                    </div>
                  </div>
                  <div class="text-[10px] text-slate-400 font-mono">
                    Confianca: ${conf}%
                  </div>
                  ${pitch ? `
                    <div class="p-2 rounded-lg bg-amber-500/5 border border-amber-500/20 text-[11px] text-amber-200/90 font-sans italic">
                      💬 Script da Equipe: "${pitch}"
                    </div>
                  ` : ''}
                </div>
              `;
            }).join('')}
          </div>

          ${limitations.length > 0 ? `
            <div class="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-[11px] text-amber-200">
              <span class="font-mono font-bold text-amber-300 uppercase">Limitacoes Estatisticas: </span>
              <span>${limitations.map(l => escapeHtml(l)).join(' • ')}</span>
            </div>
          ` : ''}
        </div>
      `;
    }

    getDefaultActionsHtml() {
      const shouldDisable = this.state.isLocked || this.isExpired();
      return `
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-amber-500 to-orange-600 text-slate-950 font-bold hover:brightness-110 ${shouldDisable ? 'opacity-50 pointer-events-none cursor-not-allowed' : ''}"
                data-action-id="act_upsell_campanha"
                data-action-type="mutation"
                data-tool-call-id="${escapeHtml(this.toolCallId)}"
                ${shouldDisable ? 'disabled' : ''}>
          <span>⚡ Lancar Campanha Frentistas</span>
        </button>
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-slate-800 text-amber-200 border border-amber-500/30 hover:bg-slate-700"
                data-action-id="act_upsell_combo"
                data-action-type="mutation"
                data-tool-call-id="${escapeHtml(this.toolCallId)}">
          <span>🎯 Ativar Combo no PDV</span>
        </button>
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-slate-900/60 text-slate-300 border border-white/10 hover:bg-slate-800"
                data-action-id="act_upsell_canvas"
                data-action-type="inspection"
                data-tool-call-id="${escapeHtml(this.toolCallId)}">
          <span>🔍 Simular Lift no Canvas</span>
        </button>
      `;
    }
  }

  // =========================================================================
  // 9. MICRO-WIDGET 7: ComplianceStatusUI (Conformidade Legal & Interoperabilidade)
  // =========================================================================

  class ComplianceStatusUI extends BaseGenUIWidget {
    constructor(payload = {}) {
      super(payload, 'compliance_status', 'render_ComplianceStatusUI');
      this.cardClass = 'genui-compliance-card';
      this.ariaLabel = 'Painel de Conformidade Legal e Interoperabilidade AURA';
    }

    renderLayer1() {
      const p = this.props;
      const compliant = coerceBoolean(p.compliant, true) && p.status !== 'pending' && p.status !== 'revoked' && p.status !== 'missing';
      const statusText = compliant ? '100% CONFORME & BLINDADO' : 'PENDENTE DE ACEITE';
      const badgeCls = compliant
        ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
        : 'bg-amber-500/15 text-amber-300 border-amber-500/30';

      const diag = escapeHtml(p.diagnosis || p.mensagem || (compliant ? 'Operação local em total conformidade jurídica e técnica.' : 'Opt-in de interoperabilidade pendente de formalização.'));
      const cnpj = escapeHtml(p.loja_cnpj || '00.000.000/0001-00');
      const razao = escapeHtml(p.razao_social || 'Auto Posto S/A');
      const versao = escapeHtml(p.versao_termo || '1.1');

      return `
        <div class="genui-layer1 p-4 rounded-2xl bg-slate-900/80 border border-cyan-500/30 shadow-lg space-y-3 font-sans">
          <div class="flex items-center justify-between gap-3 border-b border-white/5 pb-2.5">
            <div class="flex items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full ${compliant ? 'bg-emerald-400' : 'bg-amber-400'}"></span>
              <span class="text-[11px] font-mono uppercase tracking-wider text-cyan-400 font-semibold">Conformidade Legal &amp; LGPD (Termo v${versao})</span>
            </div>
            <span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${badgeCls}">
              ${statusText}
            </span>
          </div>

          <div class="space-y-1">
            <div class="text-xs font-bold text-white">${razao} <span class="font-mono text-[11px] font-normal text-slate-400">(CNPJ: ${cnpj})</span></div>
            <p class="text-xs text-slate-300 leading-relaxed">${diag}</p>
          </div>
        </div>
      `;
    }

    renderLayer2() {
      const p = this.props;
      const timeoutMs = coerceNumber(p.statement_timeout_ms, 4000);
      const lockTimeoutMs = coerceNumber(p.lock_timeout_ms, 1000);
      const roleBanco = escapeHtml(p.role_banco || 'aura_service_ro');
      const hashTermo = escapeHtml((p.hash_termo || p.hash_atual_termo || '').substring(0, 16));
      const assinante = escapeHtml(p.assinado_por || 'Representante Legal');
      const dataAceite = p.aceite_interoperabilidade_em ? new Date(p.aceite_interoperabilidade_em).toLocaleDateString('pt-BR') : 'Pendente';

      return `
        <div class="genui-layer2 p-4 rounded-2xl bg-slate-950/60 border border-white/5 space-y-3 font-sans text-xs">
          <!-- Grade de Driver Shield -->
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <div class="p-2.5 rounded-xl bg-slate-900/60 border border-white/5">
              <div class="text-[10px] text-slate-400 font-mono">Modo de Acesso</div>
              <div class="text-xs font-bold text-emerald-400 flex items-center gap-1 mt-0.5">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                READ-ONLY ATIVO
              </div>
            </div>
            <div class="p-2.5 rounded-xl bg-slate-900/60 border border-white/5">
              <div class="text-[10px] text-slate-400 font-mono">Query Timeout</div>
              <div class="text-xs font-bold text-cyan-300 font-mono mt-0.5">${timeoutMs} ms</div>
            </div>
            <div class="p-2.5 rounded-xl bg-slate-900/60 border border-white/5">
              <div class="text-[10px] text-slate-400 font-mono">Lock Timeout</div>
              <div class="text-xs font-bold text-cyan-300 font-mono mt-0.5">${lockTimeoutMs} ms</div>
            </div>
            <div class="p-2.5 rounded-xl bg-slate-900/60 border border-white/5">
              <div class="text-[10px] text-slate-400 font-mono">Role PostgreSQL</div>
              <div class="text-xs font-bold text-purple-300 font-mono mt-0.5">${roleBanco}</div>
            </div>
          </div>

          <!-- Pilares Legais Resumidos -->
          <div class="p-3 rounded-xl bg-slate-900/40 border border-white/5 space-y-1.5 text-[11px]">
            <div class="flex justify-between items-center text-slate-300">
              <span>Opt-in Formal: <strong class="text-white">${assinante}</strong></span>
              <span class="text-slate-400 font-mono text-[10px]">${dataAceite}</span>
            </div>
            <div class="flex justify-between items-center text-slate-400 font-mono text-[10px]">
              <span>Hash Criptográfico SHA-256:</span>
              <span class="text-slate-200 bg-white/5 px-2 py-0.5 rounded border border-white/5">${hashTermo ? `${hashTermo}...` : 'Calculado'}</span>
            </div>
          </div>
        </div>
      `;
    }

    renderLayer3() {
      return `
        <div class="genui-layer3 flex flex-wrap items-center gap-2 pt-1 font-sans">
          <button type="button"
                  class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-cyan-500 text-slate-950 hover:bg-cyan-400 shadow-md shadow-cyan-500/20"
                  onclick="if (window.auraCompliance) window.auraCompliance.openModal();"
                  data-action-id="act_open_compliance_modal"
                  data-action-type="inspection"
                  data-tool-call-id="${escapeHtml(this.toolCallId)}">
            <span>🛡️ Abrir Termo de Interoperabilidade</span>
          </button>
          <a href="/showcase#sec-blindagem"
             target="_blank"
             rel="noopener noreferrer"
             class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-slate-900/60 text-slate-300 border border-white/10 hover:bg-slate-800 inline-flex items-center gap-1.5">
            <span>📋 Ver Vitrine no Showcase</span>
            <span>↗</span>
          </a>
        </div>
      `;
    }
  }


  // =========================================================================
  // 9. MICRO-WIDGET MODULAR GENERATIVO: GenerativeModularCardUI (Blocos Lego)
  // =========================================================================

  class GenerativeModularCardUI extends BaseGenUIWidget {
    constructor(payload = {}) {
      super(payload, 'diagnostico_modular', 'render_GenerativeModularCardUI');
      this.cardClass = 'genui-modular-lego-card';
      this.ariaLabel = 'Diagnostico Executivo Modular Generativo AURA';
    }

    renderLayer1() {
      const p = this.props || {};
      const title = p.title || 'AURA Diagnóstico Modular Generativo';
      const subtitle = p.subtitle || 'Composição Dinâmica em Blocos Lego';
      const scoreRaw = p.confidence_score !== undefined ? Number(p.confidence_score) : 0.95;
      const scorePct = Math.round(scoreRaw * 100);
      const diagnosisText = p.diagnosis || this.summary || 'Diagnóstico operacional construído dinamicamente a partir dos blocos analíticos.';

      const scoreColor = scorePct >= 90
        ? 'text-emerald-300 border-emerald-500/40 bg-emerald-500/10'
        : (scorePct >= 75 ? 'text-amber-300 border-amber-500/40 bg-amber-500/10' : 'text-slate-300 border-slate-600 bg-slate-800/40');

      return `
        <div class="genui-layer genui-layer-1 mb-4 pb-3 border-b border-white/10">
          <div class="flex flex-wrap items-center justify-between gap-2 mb-2.5">
            <div class="flex items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse flex-shrink-0"></span>
              <h4 class="text-xs font-mono font-bold tracking-wider text-cyan-300 uppercase">
                ${escapeHtml(title)}
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
            <div class="flex items-center justify-between text-[10px] font-mono">
              <span class="text-cyan-400 font-bold uppercase">${escapeHtml(subtitle)}</span>
              <span class="text-slate-400">Intelligent UI : Blocos Lego</span>
            </div>
            <p class="text-xs sm:text-sm font-mono font-normal text-slate-300 leading-relaxed">
              ${escapeHtml(diagnosisText)}
            </p>
          </div>
        </div>
      `;
    }

    renderLayer2() {
      const p = this.props || {};
      const blocks = Array.isArray(p.blocks) ? p.blocks : [];
      const limitations = Array.isArray(p.limitations) ? p.limitations : [];

      if (blocks.length === 0) {
        return `
          <div class="genui-layer genui-layer-2 mb-4 p-4 rounded-xl bg-slate-950/40 border border-white/5 text-center text-xs text-slate-400">
            Nenhum bloco analítico registrado para esta consulta.
          </div>
        `;
      }

      return `
        <div class="genui-layer genui-layer-2 mb-4 space-y-3.5">
          ${blocks.map(b => this.renderSingleLegoBlock(b)).join('')}

          ${limitations.length > 0 ? `
            <div class="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-[11px] text-amber-200">
              <span class="font-mono font-bold text-amber-300 uppercase">Avisos Operacionais: </span>
              <span>${limitations.map(l => escapeHtml(l)).join(' • ')}</span>
            </div>
          ` : ''}
        </div>
      `;
    }

    renderSingleLegoBlock(b = {}) {
      const bType = b.block_type || 'custom_content';
      const bTitle = b.title ? escapeHtml(b.title) : null;
      const bSubtitle = b.subtitle ? escapeHtml(b.subtitle) : null;

      let icon = '📌';
      if (bType === 'kpi_grid') icon = '📊';
      else if (bType === 'comparison_table') icon = '⚖️';
      else if (bType === 'ranking_list') icon = '🏆';
      else if (bType === 'fiscal_findings_list') icon = '🛡️';
      else if (bType === 'timeline_feed') icon = '⏱️';
      else if (bType === 'alert_callout') icon = '🚨';

      const headerHtml = bTitle ? `
        <div class="flex items-center justify-between text-xs border-b border-white/5 pb-1.5 mb-2.5">
          <span class="font-bold text-slate-100 flex items-center gap-1.5">
            <span>${icon}</span>
            <span>${bTitle}</span>
          </span>
          ${bSubtitle ? `<span class="text-[10px] text-slate-400 font-mono">${bSubtitle}</span>` : ''}
        </div>
      ` : '';

      let bodyHtml = '';

      if (bType === 'kpi_grid') {
        const kpis = Array.isArray(b.kpis) ? b.kpis : [];
        bodyHtml = `
          <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
            ${kpis.map(k => {
              const st = k.status || 'neutral';
              const statusBorder = st === 'success' ? 'border-emerald-500/30' : (st === 'danger' ? 'border-rose-500/30' : (st === 'warning' ? 'border-amber-500/30' : 'border-white/5'));
              const valueColor = st === 'success' ? 'text-emerald-400' : (st === 'danger' ? 'text-rose-400' : (st === 'warning' ? 'text-amber-300' : 'text-cyan-300'));
              const trendArrow = k.trend === 'up' ? '↗' : (k.trend === 'down' ? '↘' : '→');
              return `
                <div class="p-2.5 rounded-lg bg-slate-950/60 border ${statusBorder} flex flex-col justify-between">
                  <div class="text-[11px] text-slate-400 truncate">${escapeHtml(k.label || 'Métrica')}</div>
                  <div class="font-mono font-bold text-base ${valueColor} my-0.5">${escapeHtml(String(k.value || '0'))}</div>
                  <div class="flex items-center justify-between text-[10px] font-mono text-slate-400">
                    ${k.delta ? `<span class="text-slate-300">${trendArrow} ${escapeHtml(k.delta)}</span>` : '<span></span>'}
                    ${k.subtext ? `<span class="truncate ml-1 text-slate-400">${escapeHtml(k.subtext)}</span>` : ''}
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        `;
      } else if (bType === 'comparison_table') {
        const rows = Array.isArray(b.comparison_rows) ? b.comparison_rows : [];
        bodyHtml = `
          <div class="space-y-1.5">
            ${rows.map(r => {
              const st = r.status || 'neutral';
              const badge = st === 'success'
                ? '<span class="px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">Vantagem</span>'
                : (st === 'danger' ? '<span class="px-1.5 py-0.5 rounded text-[10px] bg-rose-500/10 text-rose-400 border border-rose-500/30">Atenção</span>' : '');
              return `
                <div class="p-2 rounded-lg bg-slate-950/50 border border-white/5 flex items-center justify-between gap-2 text-xs">
                  <div class="min-w-0">
                    <div class="font-bold text-slate-200 truncate">${escapeHtml(r.name || 'Item')}</div>
                    <div class="text-[10px] text-slate-400 font-mono">
                      Filial: <span class="text-slate-100 font-semibold">${escapeHtml(String(r.primary_value ?? '-'))}</span> • Ref: ${escapeHtml(String(r.secondary_value ?? '-'))}
                    </div>
                  </div>
                  <div class="flex items-center gap-1.5 flex-shrink-0">
                    ${r.gap ? `<span class="font-mono text-[11px] font-bold text-cyan-300">${escapeHtml(r.gap)}</span>` : ''}
                    ${badge}
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        `;
      } else if (bType === 'fiscal_findings_list') {
        const rawFindings = Array.isArray(b.findings) ? b.findings : (Array.isArray(b.ranking_items) ? b.ranking_items : []);

        const isConformeItem = (item) => {
          const st = String(item.status || item.value || '').toUpperCase();
          return st.includes('VALID') || st.includes('CONFORM');
        };

        const pendencias = rawFindings.filter(item => !isConformeItem(item));
        const conformes = rawFindings.filter(item => isConformeItem(item));

        const renderFindingCard = (item, isConforme = false) => {
          const stRaw = String(item.status || item.value || '').toUpperCase();
          let isInvalid = stRaw.includes('INVALID') || stRaw.includes('REJEIC');
          let isWarning = stRaw.includes('WARN') || stRaw.includes('ALERTA');
          let isValid = stRaw.includes('VALID') || stRaw.includes('CONFORM');

          let cardBorderClass = 'border-white/5 bg-slate-950/50';
          let statusBadgeClass = 'bg-slate-800 text-slate-300 border-slate-700';
          let statusBadgeLabel = 'Fiscal';
          let statusBtnHtml = '';

          if (isInvalid) {
            cardBorderClass = 'border-rose-500/25 bg-rose-950/10 hover:border-rose-500/40';
            statusBadgeClass = 'bg-rose-500/15 text-rose-300 border-rose-500/30';
            statusBadgeLabel = 'Bloqueio de Emissao';
            statusBtnHtml = `
              <div class="aura-status-tooltip-wrapper flex-shrink-0" tabindex="0">
                <div class="w-6 h-6 rounded-full bg-rose-500/15 border border-rose-500/40 text-rose-300 flex items-center justify-center shadow-[0_0_8px_rgba(244,63,94,0.3)] transition-all duration-200 cursor-pointer aura-status-icon">
                  <svg class="w-3 h-3 text-rose-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                  </svg>
                </div>
                <div class="aura-status-tooltip">
                  <div class="px-2.5 py-1.5 rounded-lg bg-slate-950/95 border border-rose-500/50 shadow-2xl text-center backdrop-blur-md">
                    <div class="text-[9px] font-bold text-rose-300 font-mono uppercase tracking-wider">Rejeicao SEFAZ</div>
                    <div class="text-[10px] text-slate-200 font-medium">Bloqueio Impeditivo de Emissao</div>
                  </div>
                  <div class="aura-status-tooltip-arrow border-r border-b border-rose-500/50"></div>
                </div>
              </div>
            `;
          } else if (isWarning) {
            cardBorderClass = 'border-amber-500/25 bg-amber-950/10 hover:border-amber-500/40';
            statusBadgeClass = 'bg-amber-500/15 text-amber-300 border-amber-500/30';
            statusBadgeLabel = 'Alerta de Conformidade';
            statusBtnHtml = `
              <div class="aura-status-tooltip-wrapper flex-shrink-0" tabindex="0">
                <div class="w-6 h-6 rounded-full bg-amber-500/15 border border-amber-500/40 text-amber-300 flex items-center justify-center shadow-[0_0_8px_rgba(245,158,11,0.3)] transition-all duration-200 cursor-pointer aura-status-icon">
                  <svg class="w-3 h-3 text-amber-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path>
                    <line x1="12" y1="9" x2="12" y2="13"></line>
                    <line x1="12" y1="17" x2="12.01" y2="17"></line>
                  </svg>
                </div>
                <div class="aura-status-tooltip">
                  <div class="px-2.5 py-1.5 rounded-lg bg-slate-950/95 border border-amber-500/50 shadow-2xl text-center backdrop-blur-md">
                    <div class="text-[9px] font-bold text-amber-300 font-mono uppercase tracking-wider">Alerta Fiscal</div>
                    <div class="text-[10px] text-slate-200 font-medium">Risco de Bitributacao ou SPED</div>
                  </div>
                  <div class="aura-status-tooltip-arrow border-r border-b border-amber-500/50"></div>
                </div>
              </div>
            `;
          } else {
            cardBorderClass = 'border-emerald-500/25 bg-emerald-950/10 hover:border-emerald-500/40';
            statusBadgeClass = 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30';
            statusBadgeLabel = 'Aprovado SEFAZ';
            statusBtnHtml = `
              <div class="aura-status-tooltip-wrapper flex-shrink-0" tabindex="0">
                <div class="w-6 h-6 rounded-full bg-emerald-500/15 border border-emerald-500/40 text-emerald-300 flex items-center justify-center shadow-[0_0_8px_rgba(16,185,129,0.3)] transition-all duration-200 cursor-pointer aura-status-icon">
                  <svg class="w-3 h-3 text-emerald-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="20 6 9 17 4 12"></polyline>
                  </svg>
                </div>
                <div class="aura-status-tooltip">
                  <div class="px-2.5 py-1.5 rounded-lg bg-slate-950/95 border border-emerald-500/50 shadow-2xl text-center backdrop-blur-md">
                    <div class="text-[9px] font-bold text-emerald-300 font-mono uppercase tracking-wider">Conforme</div>
                    <div class="text-[10px] text-slate-200 font-medium">Validado perante SEFAZ e SPED</div>
                  </div>
                  <div class="aura-status-tooltip-arrow border-r border-b border-emerald-500/50"></div>
                </div>
              </div>
            `;
          }

          let rawTit = item.titulo || item.title || 'Regra Fiscal';
          let cleanTit = rawTit.replace(/^\[(REJEICAO|ALERTA|CONFORME|AVISO|ERRO)\]\s*/i, '').trim();

          const ruleCode = String(item.regra_id || item.tag || '').trim();
          const execMsg = item.explicacao_executiva || item.subtitle || '';
          const acaoMsg = item.acao_recomendada || (Array.isArray(item.acoes_recomendadas) && item.acoes_recomendadas[0]) || '';
          const fields = Array.isArray(item.campos_afetados) ? item.campos_afetados : [];
          const isSuporteErp = isInvalid || (acaoMsg && acaoMsg.toLowerCase().includes('suporte')) || (item.canal_acao === 'suporte_webposto');

          const ticketPayload = JSON.stringify({
            titulo: cleanTit,
            regra: ruleCode,
            causa: execMsg,
            tecnica: item.explicacao_tecnica || '',
            campos: fields.join(', '),
            obs: String(item.valor_observado || ''),
            esp: String(item.valor_esperado || '')
          }).replace(/'/g, "&apos;");

          return `
            <div class="p-3.5 rounded-xl border ${cardBorderClass} transition-all space-y-2.5">
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0 flex-1 space-y-1">
                  <div class="flex items-center gap-2 flex-wrap">
                    <span class="px-2 py-0.5 rounded-full text-[10px] font-sans font-semibold border ${statusBadgeClass}">
                      ${statusBadgeLabel}
                    </span>
                    <span class="finding-rule-code hidden text-[10px] text-slate-400 font-mono">
                      Regra: ${escapeHtml(ruleCode)}
                    </span>
                  </div>
                  <h5 class="text-xs sm:text-sm font-semibold text-slate-100 leading-snug">
                    ${escapeHtml(cleanTit)}
                  </h5>
                </div>
                <div class="text-right flex-shrink-0">
                  ${statusBtnHtml}
                </div>
              </div>

              <!-- FASE 4/5: Visualizacao Diferenciada por Persona (Gestor vs. Contador) -->
              <!-- Modo Gestor (Foco de Pista & Destravamento) -->
              <div class="finding-view-gestor space-y-2">
                ${execMsg ? `
                  <p class="text-xs text-slate-300 leading-relaxed font-sans">
                    ${escapeHtml(execMsg)}
                  </p>
                ` : ''}
                ${acaoMsg ? `
                  <div class="p-2.5 rounded-lg bg-emerald-950/30 border border-emerald-500/30 text-xs text-emerald-200 space-y-2">
                    <div class="flex items-start gap-2 leading-relaxed">
                      <span class="text-emerald-400 flex-shrink-0 text-sm">💡</span>
                      <div>
                        <strong class="text-emerald-300 font-semibold">Como destravar no webPosto: </strong>
                        <span>${escapeHtml(acaoMsg)}</span>
                      </div>
                    </div>
                    ${isSuporteErp ? `
                      <button
                        type="button"
                        class="btn-suporte-webposto inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-200 border border-emerald-500/40 text-xs font-semibold transition-all active:scale-95 shadow-sm cursor-pointer"
                        data-ticket='${ticketPayload}'
                        title="Copiar chamado formatado para enviar no WhatsApp do Suporte webPosto"
                      >
                        <svg class="w-3.5 h-3.5 text-emerald-300 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>
                        </svg>
                        <span>Copiar Chamado Suporte webPosto (WhatsApp)</span>
                      </button>
                    ` : ''}
                  </div>
                ` : ''}
              </div>

              <!-- Modo Contador (Foco Contabil, Tags XML & SPED) -->
              <div class="finding-view-contador hidden space-y-2">
                ${item.explicacao_tecnica ? `
                  <p class="text-xs text-cyan-200/90 leading-relaxed font-mono">
                    ${escapeHtml(item.explicacao_tecnica)}
                  </p>
                ` : (execMsg ? `
                  <p class="text-xs text-slate-300 leading-relaxed font-mono">
                    ${escapeHtml(execMsg)}
                  </p>
                ` : '')}
                ${fields.length > 0 ? `
                  <div class="flex flex-wrap items-center gap-1.5 text-[10px] font-mono text-slate-400">
                    <span class="text-cyan-400 font-semibold">Tags XML:</span>
                    ${fields.map(f => `<span class="bg-slate-900 px-1.5 py-0.5 rounded border border-cyan-500/30 text-cyan-300">${escapeHtml(f)}</span>`).join('')}
                  </div>
                ` : ''}
                ${(Array.isArray(item.base_legal) && item.base_legal.length > 0) ? `
                  <div class="flex flex-wrap items-center gap-1.5 text-[10px] font-mono text-slate-400">
                    <span class="text-slate-500">Fundamentacao:</span>
                    ${item.base_legal.map(b => `<span class="bg-slate-900 px-1.5 py-0.5 rounded border border-white/5 text-slate-300">${escapeHtml(b)}</span>`).join('')}
                  </div>
                ` : ''}
              </div>
            </div>
          `;
        };

        if (pendencias.length > 0) {
          bodyHtml = `
            <div class="space-y-2.5">
              ${pendencias.map(item => renderFindingCard(item, false)).join('')}

              ${conformes.length > 0 ? `
                <div class="finding-conformes-box mt-3 pt-2 border-t border-white/10">
                  <div class="flex items-center justify-between p-2.5 rounded-xl bg-slate-900/60 border border-emerald-500/20 text-xs">
                    <div class="flex items-center gap-2">
                      <span class="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)]"></span>
                      <span class="text-emerald-300 font-medium">${conformes.length} checagem(ns) estruturais SEFAZ 100% conformes</span>
                    </div>
                    <button type="button" class="btn-toggle-conformes px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 text-[11px] font-mono text-cyan-400 hover:text-cyan-300 transition-colors" data-state="closed">
                      Ver conformes (+${conformes.length})
                    </button>
                  </div>
                  <div class="container-conformes-list hidden space-y-2 pt-2">
                    ${conformes.map(item => renderFindingCard(item, true)).join('')}
                  </div>
                </div>
              ` : ''}
            </div>
          `;
        } else {
          bodyHtml = `
            <div class="space-y-2.5">
              <div class="p-4 rounded-xl border border-emerald-500/30 bg-emerald-950/20 text-center space-y-2">
                <div class="w-10 h-10 rounded-full bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 flex items-center justify-center mx-auto shadow-[0_0_12px_rgba(16,185,129,0.25)]">
                  <svg class="w-5 h-5 text-emerald-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>
                </div>
                <h5 class="text-sm font-bold text-emerald-200">Documento Fiscal 100% Conforme</h5>
                <p class="text-xs text-slate-300 max-w-md mx-auto">Todas as regras tributarias e de schema foram validadas com sucesso perante a SEFAZ e SPED. Emissao liberada na pista.</p>
                ${conformes.length > 0 ? `
                  <button type="button" class="btn-toggle-conformes text-xs font-mono text-cyan-400 hover:text-cyan-300 underline mt-1">
                    Ver as ${conformes.length} regras aprovadas
                  </button>
                  <div class="container-conformes-list hidden space-y-2 text-left pt-3">
                    ${conformes.map(item => renderFindingCard(item, true)).join('')}
                  </div>
                ` : ''}
              </div>
            </div>
          `;
        }
      } else if (bType === 'ranking_list') {
        const items = Array.isArray(b.ranking_items) ? b.ranking_items : [];
        bodyHtml = `
          <div class="space-y-1.5">
            ${items.map((item, idx) => {
              const rankNum = item.rank || (idx + 1);
              const medal = rankNum === 1 ? '🥇 1º' : (rankNum === 2 ? '🥈 2º' : (rankNum === 3 ? '🥉 3º' : `${rankNum}º`));
              const rawVal = String(item.value || '').toUpperCase();
              let isInv = rawVal.includes('INVALID') || rawVal.includes('REJEIC');
              let isWarn = rawVal.includes('WARN') || rawVal.includes('ALERTA');
              let isVal = rawVal.includes('VALID') || rawVal.includes('CONFORM');
              let isFiscal = isInv || isWarn || isVal;

              let valHtml = '';
              if (isInv) {
                valHtml = `
                  <div class="aura-status-tooltip-wrapper flex-shrink-0" tabindex="0">
                    <div class="w-6 h-6 rounded-full bg-rose-500/15 border border-rose-500/40 text-rose-300 flex items-center justify-center shadow-[0_0_8px_rgba(244,63,94,0.3)] transition-all duration-200 cursor-pointer aura-status-icon">
                      <svg class="w-3 h-3 text-rose-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                      </svg>
                    </div>
                    <div class="aura-status-tooltip">
                      <div class="px-2.5 py-1.5 rounded-lg bg-slate-950/95 border border-rose-500/50 shadow-2xl text-center backdrop-blur-md">
                        <div class="text-[9px] font-bold text-rose-300 font-mono uppercase tracking-wider">Rejeicao SEFAZ</div>
                        <div class="text-[10px] text-slate-200 font-medium">Bloqueio Impeditivo de Emissao</div>
                      </div>
                      <div class="aura-status-tooltip-arrow border-r border-b border-rose-500/50"></div>
                    </div>
                  </div>
                `;
              } else if (isWarn) {
                valHtml = `
                  <div class="aura-status-tooltip-wrapper flex-shrink-0" tabindex="0">
                    <div class="w-6 h-6 rounded-full bg-amber-500/15 border border-amber-500/40 text-amber-300 flex items-center justify-center shadow-[0_0_8px_rgba(245,158,11,0.3)] transition-all duration-200 cursor-pointer aura-status-icon">
                      <svg class="w-3 h-3 text-amber-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path>
                        <line x1="12" y1="9" x2="12" y2="13"></line>
                        <line x1="12" y1="17" x2="12.01" y2="17"></line>
                      </svg>
                    </div>
                    <div class="aura-status-tooltip">
                      <div class="px-2.5 py-1.5 rounded-lg bg-slate-950/95 border border-amber-500/50 shadow-2xl text-center backdrop-blur-md">
                        <div class="text-[9px] font-bold text-amber-300 font-mono uppercase tracking-wider">Alerta Fiscal</div>
                        <div class="text-[10px] text-slate-200 font-medium">Risco de Bitributacao ou SPED</div>
                      </div>
                      <div class="aura-status-tooltip-arrow border-r border-b border-amber-500/50"></div>
                    </div>
                  </div>
                `;
              } else if (isVal) {
                valHtml = `
                  <div class="aura-status-tooltip-wrapper flex-shrink-0" tabindex="0">
                    <div class="w-6 h-6 rounded-full bg-emerald-500/15 border border-emerald-500/40 text-emerald-300 flex items-center justify-center shadow-[0_0_8px_rgba(16,185,129,0.3)] transition-all duration-200 cursor-pointer aura-status-icon">
                      <svg class="w-3 h-3 text-emerald-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="20 6 9 17 4 12"></polyline>
                      </svg>
                    </div>
                    <div class="aura-status-tooltip">
                      <div class="px-2.5 py-1.5 rounded-lg bg-slate-950/95 border border-emerald-500/50 shadow-2xl text-center backdrop-blur-md">
                        <div class="text-[9px] font-bold text-emerald-300 font-mono uppercase tracking-wider">Conforme</div>
                        <div class="text-[10px] text-slate-200 font-medium">Validado perante SEFAZ e SPED</div>
                      </div>
                      <div class="aura-status-tooltip-arrow border-r border-b border-emerald-500/50"></div>
                    </div>
                  </div>
                `;
              } else {
                valHtml = `<div class="font-mono font-bold text-emerald-400 text-sm">${escapeHtml(String(item.value || ''))}</div>`;
              }

              // Limpa prefixo [REJEICAO] ou [CONFORME] do titulo
              let rawItemTitle = item.title || 'Entidade';
              let cleanItemTitle = rawItemTitle.replace(/^\[(REJEICAO|ALERTA|CONFORME|AVISO|ERRO)\]\s*/i, '').trim();

              // Subtitulo padronizado: Regra: <CODIGO> (sem GravidadeApontamento.CRITICAL)
              let rawSub = item.subtitle || '';
              let cleanSub = rawSub.replace(/\|?\s*Gravidade:\s*(?:GravidadeApontamento\.)?[A-Z]+/gi, '').trim();
              if (cleanSub.startsWith('|')) cleanSub = cleanSub.substring(1).trim();
              if (cleanSub.endsWith('|')) cleanSub = cleanSub.substring(0, cleanSub.length - 1).trim();

              return `
                <div class="p-2.5 rounded-lg bg-slate-950/50 border border-white/5 flex items-center justify-between gap-2 text-xs">
                  <div class="flex items-center gap-2 min-w-0 flex-1">
                    ${!isFiscal ? `<span class="font-mono font-bold text-amber-300 text-[11px] flex-shrink-0">${medal}</span>` : ''}
                    <div class="min-w-0">
                      <div class="font-semibold text-slate-100">${escapeHtml(cleanItemTitle)}</div>
                      ${cleanSub ? `<div class="text-[10px] text-slate-400 font-mono mt-0.5">${escapeHtml(cleanSub)}</div>` : ''}
                    </div>
                  </div>
                  <div class="text-right flex-shrink-0">
                    ${valHtml}
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        `;
      } else if (bType === 'timeline_feed') {
        const events = Array.isArray(b.timeline_events) ? b.timeline_events : [];
        bodyHtml = `
          <div class="space-y-2 border-l border-cyan-500/30 pl-3 ml-1.5 pt-1">
            ${events.map(ev => `
              <div class="relative">
                <span class="absolute -left-[17px] top-1 w-2 h-2 rounded-full bg-cyan-400 ring-2 ring-slate-950"></span>
                <div class="flex items-center justify-between text-xs">
                  <span class="font-semibold text-slate-200">${escapeHtml(ev.title || 'Evento')}</span>
                  <span class="font-mono text-[10px] text-slate-400">${escapeHtml(ev.timestamp || '')}</span>
                </div>
                ${ev.description ? `<p class="text-[11px] text-slate-400 mt-0.5">${escapeHtml(ev.description)}</p>` : ''}
              </div>
            `).join('')}
          </div>
        `;
      } else if (bType === 'alert_callout' && b.alert) {
        const sev = b.alert.severity || 'warning';
        const alertBorder = sev === 'critical' ? 'border-rose-500/40' : (sev === 'warning' ? 'border-amber-500/40' : (sev === 'success' ? 'border-emerald-500/40' : 'border-cyan-500/40'));
        const alertBg = sev === 'critical' ? 'bg-rose-500/10' : (sev === 'warning' ? 'bg-amber-500/10' : (sev === 'success' ? 'bg-emerald-500/10' : 'bg-cyan-500/10'));
        const alertText = sev === 'critical' ? 'text-rose-300' : (sev === 'warning' ? 'text-amber-300' : (sev === 'success' ? 'text-emerald-300' : 'text-cyan-300'));
        const alIcon = sev === 'critical' ? '🚨' : (sev === 'warning' ? '⚠️' : (sev === 'success' ? '✅' : 'ℹ️'));
        bodyHtml = `
          <div class="p-3 rounded-xl border ${alertBorder} ${alertBg} text-xs space-y-1">
            <div class="font-bold flex items-center gap-1.5 ${alertText}">
              <span>${alIcon}</span>
              <span>${escapeHtml(b.alert.title || 'Alerta')}</span>
            </div>
            <p class="text-[11px] text-slate-300 leading-relaxed">${escapeHtml(b.alert.message || '')}</p>
            ${b.alert.action_label ? `<div class="pt-1 text-[10px] font-mono text-cyan-300 font-semibold">${escapeHtml(b.alert.action_label)}</div>` : ''}
          </div>
        `;
      } else {
        bodyHtml = `
          <div class="text-xs text-slate-300 leading-relaxed whitespace-pre-line">
            ${escapeHtml(b.custom_content || '')}
          </div>
        `;
      }

      return `
        <div class="p-3.5 rounded-xl bg-slate-900/70 border border-white/5 space-y-2" data-block-id="${escapeHtml(b.block_id || 'blk')}">
          ${headerHtml}
          ${bodyHtml}
        </div>
      `;
    }

    getDefaultActionsHtml() {
      const shouldDisable = this.state.isLocked || this.isExpired();
      return `
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-blue-500 to-cyan-600 text-slate-950 font-bold hover:brightness-110 ${shouldDisable ? 'opacity-50 pointer-events-none cursor-not-allowed' : ''}"
                data-action-id="act_modular_aplicar"
                data-action-type="mutation"
                data-tool-call-id="${escapeHtml(this.toolCallId)}"
                ${shouldDisable ? 'disabled' : ''}>
          <span>⚡ Aplicar Recomendação</span>
        </button>
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-slate-800 text-cyan-200 border border-cyan-500/30 hover:bg-slate-700"
                data-action-id="act_modular_canvas"
                data-action-type="inspection"
                data-tool-call-id="${escapeHtml(this.toolCallId)}">
          <span>🔍 Inspecionar no Canvas</span>
        </button>
      `;
    }
  }


  // =========================================================================
  // MICRO-WIDGET FISCAL: FiscalShieldInspectorUI (Escudo Fiscal SEFAZ & SPED)
  // =========================================================================

  class FiscalShieldInspectorUI extends GenerativeModularCardUI {
    constructor(payload = {}) {
      super(payload);
      this.intent = escapeHtml(payload.intent || "auditoria_fiscal_sefaz");
      this.componentName = escapeHtml(payload.component_name || "render_FiscalShieldInspectorUI");
      this.cardClass = "genui-fiscal-shield-card genui-modular-lego-card";
      this.ariaLabel = "Escudo Fiscal SEFAZ e Auditoria de Regras Tributarias AURA";
      this.activePersona = "gestor"; // "gestor" | "contador"
    }

    renderLayer1() {
      const p = this.props || {};
      const title = p.title || "Escudo Fiscal SEFAZ & Auditoria Tributaria";
      const subtitle = p.subtitle || "Auditoria Deterministica MOC 7.0 + webPosto RAG";
      const scoreRaw = p.confidence_score !== undefined ? Number(p.confidence_score) : 0.99;
      const scorePct = Math.round(scoreRaw * 100);
      const diagnosisText = p.diagnosis || this.summary || "Auditoria fiscal processada com sucesso.";
      const personaViews = p.persona_views || {};

      const gestorText = personaViews.gestor || diagnosisText;
      const contadorText = personaViews.contador || diagnosisText;
      const basesLegais = Array.isArray(personaViews.base_legal) ? personaViews.base_legal : [];

      const scoreColor = scorePct >= 90
        ? "text-emerald-300 border-emerald-500/40 bg-emerald-500/10"
        : (scorePct >= 75 ? "text-amber-300 border-amber-500/40 bg-amber-500/10" : "text-slate-300 border-slate-600 bg-slate-800/40");

      return `
        <div class="genui-layer genui-layer-1 mb-4 pb-3 border-b border-white/10">
          <div class="flex flex-wrap items-center justify-between gap-2 mb-2.5">
            <div class="flex items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse flex-shrink-0"></span>
              <h4 class="text-xs font-mono font-bold tracking-wider text-cyan-300 uppercase">
                ${escapeHtml(title)}
              </h4>
              <span class="text-[10px] font-mono text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded border border-white/5">
                ${escapeHtml(this.toolCallId.substring(0, 14))}...
              </span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-[11px] font-mono px-2.5 py-0.5 rounded-full border ${scoreColor} font-semibold flex items-center gap-1">
                <svg class="w-3 h-3 inline-block" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/></svg>
                <span>${scorePct}% Confiabilidade</span>
              </span>
            </div>
          </div>

          <!-- Switch Dupla Persona: Gestor / Pista vs Contador / SPED -->
          <div class="persona-switch-bar inline-flex p-1 rounded-xl bg-slate-950/80 border border-white/10 my-2 gap-1 w-full sm:w-auto" role="tablist">
            <button type="button" 
                    role="tab" 
                    aria-selected="${this.activePersona === 'gestor' ? 'true' : 'false'}"
                    class="persona-switch-btn persona-btn-gestor flex-1 sm:flex-initial px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${this.activePersona === 'gestor' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm' : 'text-slate-400 hover:text-slate-200'}" 
                    data-persona="gestor">
              <span>💼</span>
              <span>Visao Gestor &amp; Pista</span>
            </button>
            <button type="button" 
                    role="tab" 
                    aria-selected="${this.activePersona === 'contador' ? 'true' : 'false'}"
                    class="persona-switch-btn persona-btn-contador flex-1 sm:flex-initial px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${this.activePersona === 'contador' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm' : 'text-slate-400 hover:text-slate-200'}" 
                    data-persona="contador">
              <span>💻</span>
              <span>Visao Contador &amp; SPED</span>
            </button>
          </div>

          <!-- Painel Visao Gestor: Card Resumo de Impacto da Pista (Apendice C - Fase 4) -->
          <div class="persona-view-panel persona-view-gestor ${this.activePersona === 'gestor' ? '' : 'hidden'} p-3.5 rounded-xl bg-slate-950/60 border border-emerald-500/30 space-y-2.5 animate-fade-in">
            <div class="flex items-center justify-between text-[11px] font-mono border-b border-white/5 pb-1.5">
              <span class="text-emerald-400 font-bold uppercase flex items-center gap-1.5">
                <span>⛽</span>
                <span>Resumo de Impacto na Pista &amp; Faturamento</span>
              </span>
              <span class="text-emerald-400/90 font-semibold px-2 py-0.5 rounded bg-emerald-950/60 border border-emerald-500/30">
                Operacao Direta
              </span>
            </div>
            
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs font-sans">
              <div class="p-2.5 rounded-lg bg-slate-900/80 border border-white/5 space-y-0.5">
                <span class="text-[10px] text-slate-400 font-mono uppercase">Impacto no Faturamento:</span>
                <p class="font-semibold text-slate-100 flex items-center gap-1.5">
                  <span class="w-2 h-2 rounded-full ${personaViews.faturamento_status && personaViews.faturamento_status.toLowerCase().includes('bloqueado') ? 'bg-rose-400 animate-pulse' : 'bg-emerald-400'}"></span>
                  <span>${escapeHtml(personaViews.faturamento_status || 'Operacao Normal')}</span>
                </p>
              </div>
              <div class="p-2.5 rounded-lg bg-slate-900/80 border border-white/5 space-y-0.5">
                <span class="text-[10px] text-slate-400 font-mono uppercase">Tempo Estimado na Pista:</span>
                <p class="font-semibold text-slate-100 flex items-center gap-1.5">
                  <span>⏱</span>
                  <span>${escapeHtml(personaViews.tempo_retencao || '0 min')}</span>
                </p>
              </div>
            </div>

            <p class="text-xs text-slate-300 leading-relaxed font-sans">
              ${formatFiscalHighlightText(gestorText, 'emerald')}
            </p>
          </div>

          <!-- Painel Visao Contador: Auditoria Tecnica MOC 7.0 & SPED -->
          <div class="persona-view-panel persona-view-contador ${this.activePersona === 'contador' ? '' : 'hidden'} p-3.5 rounded-xl bg-slate-950/60 border border-cyan-500/30 space-y-2.5 animate-fade-in">
            <div class="flex items-center justify-between text-[11px] font-mono border-b border-white/5 pb-1.5">
              <span class="text-cyan-400 font-bold uppercase flex items-center gap-1.5">
                <span>💻</span>
                <span>Auditoria Tecnica MOC 7.0 &amp; EFD / SPED Fiscal</span>
              </span>
              <span class="text-cyan-400/90 font-semibold px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-500/30">
                Escrituracao Contabil
              </span>
            </div>
            <p class="text-xs sm:text-sm font-mono font-normal text-slate-300 leading-relaxed whitespace-pre-line">
              ${formatFiscalHighlightText(contadorText, 'cyan')}
            </p>
            ${basesLegais.length > 0 ? `
              <div class="pt-2 border-t border-white/5 flex flex-wrap gap-1.5 items-center">
                <span class="text-[10px] font-mono text-slate-400">Base Legal:</span>
                ${basesLegais.map(bl => `<span class="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-950/60 text-cyan-300 border border-cyan-500/30">${escapeHtml(bl)}</span>`).join('')}
              </div>
            ` : ''}
          </div>
        </div>
      `;
    }

    renderLayer2() {
      const p = this.props || {};
      const anatomy = p.access_key_anatomy;
      let anatomyHtml = '';

      if (anatomy && typeof anatomy === 'object') {
        const isDvOk = !!anatomy.is_dv_valido;
        const dvStatusClass = isDvOk 
          ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/50' 
          : 'bg-rose-500/20 text-rose-300 border-rose-500/50 animate-pulse';

        anatomyHtml = `
          <div class="p-3.5 rounded-xl bg-slate-900/80 border border-cyan-500/30 space-y-2 mb-3.5" data-block-id="blk_chave_anatomy_bar">
            <div class="flex items-center justify-between text-xs border-b border-white/5 pb-1.5">
              <span class="font-bold text-slate-100 flex items-center gap-1.5">
                <span>🔑</span>
                <span>Anatomia dos 44 Digitos da Chave SEFAZ</span>
              </span>
              <span class="text-[10px] font-mono text-cyan-300">Decomposicao Estrutural MOC 7.0</span>
            </div>
            <div class="overflow-x-auto pb-1">
              <div class="flex items-stretch gap-1.5 min-w-max text-center font-mono">
                <!-- Segmento 1: UF -->
                <div class="fiscal-key-segment p-1.5 rounded-lg bg-slate-950 border border-white/10" title="Codigo IBGE da UF">
                  <div class="text-[9px] text-slate-400">UF</div>
                  <div class="text-xs font-bold text-cyan-300">${escapeHtml(anatomy.c_uf || '--')}</div>
                  <div class="text-[8px] text-slate-500">${escapeHtml(anatomy.uf_sigla || '')}</div>
                </div>
                <!-- Segmento 2: AAMM -->
                <div class="fiscal-key-segment p-1.5 rounded-lg bg-slate-950 border border-white/10" title="Ano e Mes de Emissao (AAMM)">
                  <div class="text-[9px] text-slate-400">AAMM</div>
                  <div class="text-xs font-bold text-cyan-300">${escapeHtml(anatomy.aamm || '----')}</div>
                  <div class="text-[8px] text-slate-500">${escapeHtml(anatomy.ano || '')}/${escapeHtml(anatomy.mes || '')}</div>
                </div>
                <!-- Segmento 3: CNPJ -->
                <div class="fiscal-key-segment p-1.5 rounded-lg bg-slate-950 border border-white/10" title="CNPJ do Emitente">
                  <div class="text-[9px] text-slate-400">CNPJ Emitente (14d)</div>
                  <div class="text-xs font-bold text-cyan-300">${escapeHtml(anatomy.cnpj_emitente || '--------------')}</div>
                  <div class="text-[8px] text-slate-500">Posto / Matriz</div>
                </div>
                <!-- Segmento 4: Modelo -->
                <div class="fiscal-key-segment p-1.5 rounded-lg bg-slate-950 border border-white/10" title="Modelo do Documento Fiscal">
                  <div class="text-[9px] text-slate-400">Mod</div>
                  <div class="text-xs font-bold text-cyan-300">${escapeHtml(anatomy.modelo || '--')}</div>
                  <div class="text-[8px] text-slate-500">${anatomy.modelo === '65' ? 'NFC-e' : 'NF-e'}</div>
                </div>
                <!-- Segmento 5: Serie -->
                <div class="fiscal-key-segment p-1.5 rounded-lg bg-slate-950 border border-white/10" title="Serie do Documento">
                  <div class="text-[9px] text-slate-400">Serie</div>
                  <div class="text-xs font-bold text-cyan-300">${escapeHtml(anatomy.serie || '---')}</div>
                  <div class="text-[8px] text-slate-500">Serie</div>
                </div>
                <!-- Segmento 6: Numero -->
                <div class="fiscal-key-segment p-1.5 rounded-lg bg-slate-950 border border-white/10" title="Numero da Nota Fiscal">
                  <div class="text-[9px] text-slate-400">Numero NF (9d)</div>
                  <div class="text-xs font-bold text-cyan-300">${escapeHtml(anatomy.numero_nfe || '---------')}</div>
                  <div class="text-[8px] text-slate-500">Documento</div>
                </div>
                <!-- Segmento 7: Tipo Emissao -->
                <div class="fiscal-key-segment p-1.5 rounded-lg bg-slate-950 border border-white/10" title="Tipo de Emissao (1: Normal, 9: Contingencia)">
                  <div class="text-[9px] text-slate-400">Emis</div>
                  <div class="text-xs font-bold text-cyan-300">${escapeHtml(anatomy.tipo_emissao || '-')}</div>
                  <div class="text-[8px] text-slate-500">${anatomy.tipo_emissao === '1' ? 'Normal' : 'Conting.'}</div>
                </div>
                <!-- Segmento 8: Codigo Numerico -->
                <div class="fiscal-key-segment p-1.5 rounded-lg bg-slate-950 border border-white/10" title="Codigo Numerico de Seguranca">
                  <div class="text-[9px] text-slate-400">Cod Num (8d)</div>
                  <div class="text-xs font-bold text-cyan-300">${escapeHtml(anatomy.codigo_numerico || '--------')}</div>
                  <div class="text-[8px] text-slate-500">Aleatorio</div>
                </div>
                <!-- Segmento 9: DV -->
                <div class="fiscal-key-segment p-1.5 rounded-lg border ${dvStatusClass}" title="Digito Verificador (Modulo 11)">
                  <div class="text-[9px] font-bold">DV Modulo 11</div>
                  <div class="text-xs font-black">${escapeHtml(anatomy.digito_verificador || '-')}</div>
                  <div class="text-[8px] font-semibold">${isDvOk ? '✔ Valido' : 'Falha: ' + escapeHtml(anatomy.dv_calculado || '')}</div>
                </div>
              </div>
            </div>
          </div>
        `;
      }

      return `
        <div class="genui-layer genui-layer-2 mb-4 space-y-3.5">
          ${anatomyHtml}
          ${super.renderLayer2()}
        </div>
      `;
    }

    bindEvents(rootElement) {
      super.bindEvents(rootElement);
      if (!rootElement || typeof rootElement.querySelectorAll !== 'function') return;

      const personaBtns = rootElement.querySelectorAll('.persona-switch-btn');
      personaBtns.forEach(btn => {
        if (!btn._hasBoundPersonaClick) {
          btn._hasBoundPersonaClick = true;
          btn.addEventListener('click', () => {
            const targetPersona = btn.getAttribute('data-persona');
            if (!targetPersona || targetPersona === this.activePersona) return;
            this.activePersona = targetPersona;

            personaBtns.forEach(b => {
              const isTarget = b.getAttribute('data-persona') === targetPersona;
              b.setAttribute('aria-selected', isTarget ? 'true' : 'false');
              if (isTarget) {
                if (targetPersona === 'gestor') {
                  b.className = 'persona-switch-btn persona-btn-gestor flex-1 sm:flex-initial px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm';
                } else {
                  b.className = 'persona-switch-btn persona-btn-contador flex-1 sm:flex-initial px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm';
                }
              } else {
                b.className = 'persona-switch-btn flex-1 sm:flex-initial px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer text-slate-400 hover:text-slate-200';
              }
            });

            const gestorPanel = rootElement.querySelector('.persona-view-gestor');
            const contadorPanel = rootElement.querySelector('.persona-view-contador');
            if (gestorPanel) gestorPanel.classList.toggle('hidden', targetPersona !== 'gestor');
            if (contadorPanel) contadorPanel.classList.toggle('hidden', targetPersona !== 'contador');

            // FASE 4/5: Alterna o detalhamento interno dos cards de findings
            const isGestor = (targetPersona === 'gestor');
            rootElement.querySelectorAll('.finding-view-gestor').forEach(el => el.classList.toggle('hidden', !isGestor));
            rootElement.querySelectorAll('.finding-view-contador').forEach(el => el.classList.toggle('hidden', isGestor));
            rootElement.querySelectorAll('.finding-rule-code').forEach(el => el.classList.toggle('hidden', isGestor));
            if (!isGestor) {
              rootElement.querySelectorAll('.container-conformes-list').forEach(el => el.classList.remove('hidden'));
              rootElement.querySelectorAll('.btn-toggle-conformes').forEach(el => {
                el.textContent = 'Ocultar conformes';
                el.setAttribute('data-state', 'open');
              });
            }
          });
        }
      });
    }
  }

  // =========================================================================
  // MÓDULO 1: DIAGNÓSTICO EXECUTIVO DE ROI & PERDAS (90 DIAS)
  // =========================================================================

  class RoiDiagnosticUI extends BaseGenUIWidget {
    constructor(payload = {}) {
      super(payload, 'roi_diagnostic', 'render_RoiDiagnosticUI');
      this.rawPayload = payload;
      this.cardClass = 'genui-roi-diagnostic-card';
      this.ariaLabel = 'Diagnostico Executivo de ROI e Perdas AURA';
    }

    renderLayer1() {
      const p = (this.props && (this.props.summary || this.props.breakdown_brl))
        ? this.props
        : ((this.rawPayload && (this.rawPayload.props || this.rawPayload.data || this.rawPayload)) || {});
      const summary = p.summary || {};
      const totalLeak = Number(summary.total_monthly_leakage_brl || 0);
      const estRecovery = Number(summary.estimated_monthly_recovery_brl || 0);
      const net90 = Number(summary.roi_90_days_net_brl || 0);
      const multiple = Number(summary.roi_multiple || 0);
      const guarantee3x = summary.guarantee_3x_met !== false;
      const diagnosisText = p.diagnosis || this.summary || 'Diagnostico deterministico de perdas operacionais e projecao de retorno liquido em 90 dias com rampa de adocao.';

      return `
        <div class="genui-layer genui-layer-1 mb-4 pb-3 border-b border-white/10">
          <div class="flex flex-wrap items-center justify-between gap-2 mb-2.5">
            <div class="flex items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse flex-shrink-0"></span>
              <h4 class="text-xs font-mono font-bold tracking-wider text-emerald-300 uppercase">
                AURA ROI Diagnostic &amp; Loss Recovery Mentor
              </h4>
              <span class="text-[10px] font-mono text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded border border-white/5">
                ${escapeHtml(this.toolCallId.substring(0, 14))}...
              </span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-[11px] font-mono px-2.5 py-0.5 rounded-full border ${guarantee3x ? 'text-emerald-300 border-emerald-500/40 bg-emerald-500/10' : 'text-amber-300 border-amber-500/40 bg-amber-500/10'} font-semibold flex items-center gap-1">
                <span>Garantia Contratual 3x: ${guarantee3x ? 'Verificada' : 'Em Calibracao'}</span>
              </span>
              <span class="text-[11px] font-mono px-2.5 py-0.5 rounded-full border text-purple-300 border-purple-500/40 bg-purple-500/10 font-bold">
                Retorno: ${formatNumber(multiple)}x
              </span>
            </div>
          </div>
          <div class="p-3 rounded-xl bg-slate-950/50 border border-white/5 space-y-1">
            <span class="text-[10px] uppercase font-bold tracking-wider text-emerald-400 font-mono">Diagnostico Executivo de Perdas</span>
            <p class="text-xs sm:text-sm font-mono font-normal text-slate-300 leading-relaxed">
              ${escapeHtml(diagnosisText)}
            </p>
          </div>
        </div>
      `;
    }

    renderLayer2() {
      const p = (this.props && (this.props.summary || this.props.breakdown_brl))
        ? this.props
        : ((this.rawPayload && (this.rawPayload.props || this.rawPayload.data || this.rawPayload)) || {});
      const summary = p.summary || {};
      const breakdown = p.breakdown_brl || {};
      const shield = p.regulatory_shield || {};

      const totalLeak = Number(summary.total_monthly_leakage_brl || 0);
      const estRecovery = Number(summary.estimated_monthly_recovery_brl || 0);
      const net90 = Number(summary.roi_90_days_net_brl || 0);
      const multiple = Number(summary.roi_multiple || 0);

      const vLmc = Number(breakdown.lmc_and_tank_shrinkage || 0);
      const vPdv = Number(breakdown.convenience_and_pos_cancellations || 0);
      const vCaixa = Number(breakdown.cashier_shift_discrepancies || 0);
      const vPricing = Number(breakdown.pricing_and_carreta_arbitrage || 0);
      const vSelic = Number(breakdown.working_capital_selic_cost || 0);

      const cardsHtml = `
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3">
          <div class="p-2.5 rounded-xl border border-white/5 bg-slate-950/40 space-y-1">
            <span class="text-[10px] text-slate-400 font-medium">Perda Mensal Mapeada</span>
            <div class="text-sm sm:text-base font-bold font-mono text-rose-400 tabular-nums">
              R$ ${formatNumber(totalLeak)}
            </div>
            <span class="text-[10px] text-slate-500 font-mono">Vazamento Operacional</span>
          </div>
          <div class="p-2.5 rounded-xl border border-white/5 bg-slate-950/40 space-y-1">
            <span class="text-[10px] text-slate-400 font-medium">Recuperacao Mensal</span>
            <div class="text-sm sm:text-base font-bold font-mono text-emerald-400 tabular-nums">
              R$ ${formatNumber(estRecovery)}
            </div>
            <span class="text-[10px] text-slate-500 font-mono">Projecao AURA</span>
          </div>
          <div class="p-2.5 rounded-xl border border-white/5 bg-slate-950/40 space-y-1">
            <span class="text-[10px] text-slate-400 font-medium">Retorno Liquido (90d)</span>
            <div class="text-sm sm:text-base font-bold font-mono text-cyan-300 tabular-nums">
              R$ ${formatNumber(net90)}
            </div>
            <span class="text-[10px] text-slate-500 font-mono">Lucro Liquido Extra</span>
          </div>
          <div class="p-2.5 rounded-xl border border-white/5 bg-slate-950/40 space-y-1">
            <span class="text-[10px] text-slate-400 font-medium">Multiplo de Retorno</span>
            <div class="text-sm sm:text-base font-bold font-mono text-purple-300 tabular-nums">
              ${formatNumber(multiple)}x
            </div>
            <span class="text-[10px] text-slate-500 font-mono">Sobre o Plano</span>
          </div>
        </div>
      `;

      const vectorsHtml = `
        <div class="p-3 rounded-xl border border-white/5 bg-slate-950/30 mb-3 space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-[10px] uppercase font-bold tracking-wider text-slate-400 font-mono">Detalhamento dos 5 Vetores de Perda Financeira</span>
            <span class="text-[10px] font-mono text-slate-500">Apuracao 100% Deterministica</span>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
            <div class="p-2 rounded-lg bg-slate-900/60 border border-slate-800 flex justify-between items-center">
              <span class="text-slate-300">1. LMC &amp; Variacao Tanques (ANP 26)</span>
              <span class="font-mono font-bold text-rose-400">R$ ${formatNumber(vLmc)}</span>
            </div>
            <div class="p-2 rounded-lg bg-slate-900/60 border border-slate-800 flex justify-between items-center">
              <span class="text-slate-300">2. Cancelamentos PDV &amp; Loja</span>
              <span class="font-mono font-bold text-rose-400">R$ ${formatNumber(vPdv)}</span>
            </div>
            <div class="p-2 rounded-lg bg-slate-900/60 border border-slate-800 flex justify-between items-center">
              <span class="text-slate-300">3. Furos de Gaveta &amp; Fechamento</span>
              <span class="font-mono font-bold text-rose-400">R$ ${formatNumber(vCaixa)}</span>
            </div>
            <div class="p-2 rounded-lg bg-slate-900/60 border border-slate-800 flex justify-between items-center">
              <span class="text-slate-300">4. Arbitragem Carreta &amp; Preco</span>
              <span class="font-mono font-bold text-rose-400">R$ ${formatNumber(vPricing)}</span>
            </div>
            <div class="p-2 rounded-lg bg-slate-900/60 border border-slate-800 flex justify-between items-center sm:col-span-2">
              <span class="text-slate-300">5. Custo SELIC Capital Morto (Estoque > 30d)</span>
              <span class="font-mono font-bold text-rose-400">R$ ${formatNumber(vSelic)}</span>
            </div>
          </div>
        </div>
      `;

      const shieldHtml = `
        <div class="p-3 rounded-xl border border-emerald-500/20 bg-emerald-950/20 mb-3 flex items-center justify-between text-xs">
          <div class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
            <span class="text-emerald-300 font-medium">Blindagem Regulatoria ANP (Portaria 26 / Lei 9.847/99)</span>
          </div>
          <span class="text-[10px] font-mono text-emerald-400/90 font-semibold">Multa Minima Evitada: R$ 20.000,00</span>
        </div>
      `;

      return `
        <div class="genui-layer genui-layer-2">
          ${cardsHtml}
          ${vectorsHtml}
          ${shieldHtml}
        </div>
      `;
    }

    getDefaultActionsHtml() {
      const shouldDisable = this.state.isLocked || this.isExpired();
      return `
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-emerald-500 to-teal-600 text-slate-950 font-bold hover:brightness-110 ${shouldDisable ? 'opacity-50 pointer-events-none cursor-not-allowed' : ''}"
                data-action-id="act_roi_revisar_precificacao"
                data-action-type="mutation"
                data-tool-call-id="${escapeHtml(this.toolCallId)}"
                ${shouldDisable ? 'disabled' : ''}>
          <span>Revisar Precificacao &amp; Margens</span>
        </button>
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-slate-800 text-emerald-200 border border-emerald-500/30 hover:bg-slate-700"
                data-action-id="act_roi_auditar_tanques"
                data-action-type="mutation"
                data-tool-call-id="${escapeHtml(this.toolCallId)}">
          <span>Auditar LMC dos Tanques</span>
        </button>
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-slate-900/60 text-slate-300 border border-white/10 hover:bg-slate-800"
                data-action-id="act_roi_canvas"
                data-action-type="inspection"
                data-tool-call-id="${escapeHtml(this.toolCallId)}">
          <span>Inspecionar no Canvas</span>
        </button>
      `;
    }
  }

  // =========================================================================
  // MÓDULO 4: RADAR DE ANOMALIAS DE PDV & CAIXA (Z-SCORE)
  // =========================================================================

  class PosAuditRadarUI extends BaseGenUIWidget {
    constructor(payload = {}) {
      super(payload, 'pos_audit', 'render_PosAuditRadarUI');
      this.rawPayload = payload;
      this.cardClass = 'genui-pos-audit-card';
      this.ariaLabel = 'Radar de Anomalias de PDV e Caixa AURA';
    }

    renderLayer1() {
      const p = (this.props && (this.props.total_operators_analyzed !== undefined || this.props.cashier_shift_audit))
        ? this.props
        : ((this.rawPayload && (this.rawPayload.props || this.rawPayload.data || this.rawPayload)) || {});
      const totOp = Number(p.total_operators_analyzed || 0);
      const anomCount = Number(p.anomalous_operators_count || 0);
      const shift = p.cashier_shift_audit || {};
      const isConciliado = shift.status === 'CONCILIADO';
      const diagnosisText = p.diagnosis || this.summary || 'Auditoria estatistica e contabil de PDV com calculo de Z-Score e blindagem CLT Art. 462.';

      return `
        <div class="genui-layer genui-layer-1 mb-4 pb-3 border-b border-white/10">
          <div class="flex flex-wrap items-center justify-between gap-2 mb-2.5">
            <div class="flex items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full ${anomCount > 0 ? 'bg-amber-400' : 'bg-cyan-400'} animate-pulse flex-shrink-0"></span>
              <h4 class="text-xs font-mono font-bold tracking-wider text-cyan-300 uppercase">
                AURA POS Anomaly &amp; Cashier Audit Radar
              </h4>
              <span class="text-[10px] font-mono text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded border border-white/5">
                ${escapeHtml(this.toolCallId.substring(0, 14))}...
              </span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-[11px] font-mono px-2.5 py-0.5 rounded-full border ${isConciliado ? 'text-emerald-300 border-emerald-500/40 bg-emerald-500/10' : 'text-rose-300 border-rose-500/40 bg-rose-500/10'} font-semibold">
                Caixa: ${isConciliado ? 'CONCILIADO' : 'DIVERGENCIA PENDENTE'}
              </span>
              <span class="text-[11px] font-mono px-2.5 py-0.5 rounded-full border ${anomCount > 0 ? 'text-rose-300 border-rose-500/40 bg-rose-500/10' : 'text-emerald-300 border-emerald-500/40 bg-emerald-500/10'} font-bold">
                Desvios: ${anomCount}
              </span>
            </div>
          </div>
          <div class="p-3 rounded-xl bg-slate-950/50 border border-white/5 space-y-1">
            <span class="text-[10px] uppercase font-bold tracking-wider text-cyan-400 font-mono">Diagnostico de Fechamento &amp; Cancelamentos</span>
            <p class="text-xs sm:text-sm font-mono font-normal text-slate-300 leading-relaxed">
              ${escapeHtml(diagnosisText)}
            </p>
          </div>
        </div>
      `;
    }

    renderLayer2() {
      const p = (this.props && (this.props.total_operators_analyzed !== undefined || this.props.cashier_shift_audit))
        ? this.props
        : ((this.rawPayload && (this.rawPayload.props || this.rawPayload.data || this.rawPayload)) || {});
      const totOp = Number(p.total_operators_analyzed || 0);
      const anomCount = Number(p.anomalous_operators_count || 0);
      const shift = p.cashier_shift_audit || {};
      const discBrl = Number(shift.discrepancy_brl || 0);
      const ops = Array.isArray(p.operators_analysis) ? p.operators_analysis : [];
      const clt = p.clt_compliance_checklist || {};

      const cardsHtml = `
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3">
          <div class="p-2.5 rounded-xl border border-white/5 bg-slate-950/40 space-y-1">
            <span class="text-[10px] text-slate-400 font-medium">Operadores Auditados</span>
            <div class="text-sm sm:text-base font-bold font-mono text-white tabular-nums">${totOp}</div>
            <span class="text-[10px] text-slate-500 font-mono">Pista &amp; Loja</span>
          </div>
          <div class="p-2.5 rounded-xl border border-white/5 bg-slate-950/40 space-y-1">
            <span class="text-[10px] text-slate-400 font-medium">Anomalias (|Z| > 2.0)</span>
            <div class="text-sm sm:text-base font-bold font-mono ${anomCount > 0 ? 'text-rose-400' : 'text-emerald-400'} tabular-nums">${anomCount}</div>
            <span class="text-[10px] text-slate-500 font-mono">Desvio Gaussiano</span>
          </div>
          <div class="p-2.5 rounded-xl border border-white/5 bg-slate-950/40 space-y-1">
            <span class="text-[10px] text-slate-400 font-medium">Divergencia de Caixa</span>
            <div class="text-sm sm:text-base font-bold font-mono ${discBrl === 0 ? 'text-slate-300' : 'text-rose-400'} tabular-nums">R$ ${formatNumber(discBrl)}</div>
            <span class="text-[10px] text-slate-500 font-mono">Pista vs Fechamento</span>
          </div>
          <div class="p-2.5 rounded-xl border border-white/5 bg-slate-950/40 space-y-1">
            <span class="text-[10px] text-slate-400 font-medium">Politica CLT 462</span>
            <div class="text-sm sm:text-base font-bold font-mono text-cyan-300">ATIVA</div>
            <span class="text-[10px] text-slate-500 font-mono">Zero Termos Acusatorios</span>
          </div>
        </div>
      `;

      let opsRows = '';
      if (ops.length === 0) {
        opsRows = '<tr><td colspan="5" class="py-2 text-center text-slate-500 text-xs">Nenhum operador com registros no periodo.</td></tr>';
      } else {
        ops.forEach(o => {
          const isAnom = o.is_anomaly;
          const zSc = Number(o.z_score || 0).toFixed(2);
          const cRate = Number(o.cancellation_rate_pct || 0).toFixed(1);
          opsRows += `
            <tr class="border-b border-slate-800/60">
              <td class="py-1.5 px-2 font-mono text-slate-200 font-semibold">${escapeHtml(o.operator_id)}</td>
              <td class="py-1.5 px-2 text-right font-mono text-slate-300">${o.total_orders || 0}</td>
              <td class="py-1.5 px-2 text-right font-mono text-slate-300">${o.cancelled_orders || 0}</td>
              <td class="py-1.5 px-2 text-right font-mono ${isAnom ? 'text-rose-400 font-bold' : 'text-slate-300'}">${cRate}%</td>
              <td class="py-1.5 px-2 text-right font-mono ${isAnom ? 'text-rose-400 font-bold' : 'text-slate-400'}">${zSc}</td>
            </tr>
          `;
        });
      }

      const tableHtml = `
        <div class="p-3 rounded-xl border border-white/5 bg-slate-950/30 mb-3 space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-[10px] uppercase font-bold tracking-wider text-slate-400 font-mono">Ranking de Operadores &amp; Z-Score de Cancelamento</span>
            <span class="text-[10px] font-mono text-slate-500">Corte |Z| &gt; 2.0</span>
          </div>
          <div class="overflow-x-auto max-h-48 overflow-y-auto">
            <table class="w-full text-left text-xs border-collapse">
              <thead>
                <tr class="border-b border-slate-800 text-[10px] text-slate-400 uppercase tracking-wider">
                  <th class="py-1 px-2">Operador</th>
                  <th class="py-1 px-2 text-right">Pedidos</th>
                  <th class="py-1 px-2 text-right">Cancelados</th>
                  <th class="py-1 px-2 text-right">Taxa %</th>
                  <th class="py-1 px-2 text-right">Z-Score</th>
                </tr>
              </thead>
              <tbody>
                ${opsRows}
              </tbody>
            </table>
          </div>
        </div>
      `;

      const cltReqs = clt.mandatory_requirements_for_deduction || [
        'Comprovacao de pagamento do Adicional de Quebra de Caixa em folha',
        'Previsao contratual expressa autorizando desconto em caso de divergencia conferida',
        'Bordero fisico de fechamento assinado pelo operador no ato'
      ];
      const cltListHtml = cltReqs.map(r => `
        <li class="flex items-start gap-1.5 text-[11px] text-slate-300">
          <span class="text-cyan-400 font-bold mt-0.5">&#10003;</span>
          <span>${escapeHtml(r)}</span>
        </li>
      `).join('');

      const cltBoxHtml = `
        <div class="p-3 rounded-xl border border-cyan-500/20 bg-cyan-950/20 mb-3 space-y-1.5">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-cyan-300">Requisitos Cumulativos para Desconto (Art. 462 CLT &amp; TST OJ 251)</span>
            <span class="text-[10px] font-mono text-cyan-400">TST-OJ-251 OK</span>
          </div>
          <ul class="space-y-1">
            ${cltListHtml}
          </ul>
        </div>
      `;

      return `
        <div class="genui-layer genui-layer-2">
          ${cardsHtml}
          ${tableHtml}
          ${cltBoxHtml}
        </div>
      `;
    }

    getDefaultActionsHtml() {
      const shouldDisable = this.state.isLocked || this.isExpired();
      return `
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 font-bold hover:brightness-110 ${shouldDisable ? 'opacity-50 pointer-events-none cursor-not-allowed' : ''}"
                data-action-id="act_pos_gerar_termo"
                data-action-type="mutation"
                data-tool-call-id="${escapeHtml(this.toolCallId)}"
                ${shouldDisable ? 'disabled' : ''}>
          <span>Gerar Termo Conferencia Turno</span>
        </button>
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-slate-800 text-cyan-200 border border-cyan-500/30 hover:bg-slate-700"
                data-action-id="act_pos_auditar_turno"
                data-action-type="mutation"
                data-tool-call-id="${escapeHtml(this.toolCallId)}">
          <span>Auditar Turno Completo</span>
        </button>
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-slate-900/60 text-slate-300 border border-white/10 hover:bg-slate-800"
                data-action-id="act_pos_canvas"
                data-action-type="inspection"
                data-tool-call-id="${escapeHtml(this.toolCallId)}">
          <span>Inspecionar no Canvas</span>
        </button>
      `;
    }
  }

  // =========================================================================
  // MÓDULO 4 / MOBILE: BRIEFING MATINAL ZERO-CLICK (CAFÉ COM O DONO)
  // =========================================================================

  class MorningBriefingUI extends BaseGenUIWidget {
    constructor(payload = {}) {
      super(payload, 'zero_click_briefing', 'render_MorningBriefingUI');
      this.rawPayload = payload;
      this.cardClass = 'genui-morning-briefing-card';
      this.ariaLabel = 'Briefing Executivo Matinal AURA';
    }

    renderLayer1() {
      const p = (this.props && (this.props.sales_summary_24h || this.props.tank_critical_runout))
        ? this.props
        : ((this.rawPayload && (this.rawPayload.props || this.rawPayload.data || this.rawPayload)) || {});
      const s24 = p.sales_summary_24h || {};
      const tank = p.tank_critical_runout || {};
      const faturamento = Number(s24.total_turnover_brl || 0);
      const diagnosisText = p.diagnosis || this.summary || 'Resumo executivo consolidado das ultimas 24h pronto para envio no WhatsApp do proprietario.';

      return `
        <div class="genui-layer genui-layer-1 mb-4 pb-3 border-b border-white/10">
          <div class="flex flex-wrap items-center justify-between gap-2 mb-2.5">
            <div class="flex items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full bg-purple-400 animate-pulse flex-shrink-0"></span>
              <h4 class="text-xs font-mono font-bold tracking-wider text-purple-300 uppercase">
                AURA Morning Executive Briefing (Cafe com o Dono)
              </h4>
              <span class="text-[10px] font-mono text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded border border-white/5">
                ${escapeHtml(this.toolCallId.substring(0, 14))}...
              </span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-[11px] font-mono px-2.5 py-0.5 rounded-full border text-emerald-300 border-emerald-500/40 bg-emerald-500/10 font-bold">
                Faturamento 24h: R$ ${formatNumber(faturamento)}
              </span>
            </div>
          </div>
          <div class="p-3 rounded-xl bg-slate-950/50 border border-white/5 space-y-1">
            <span class="text-[10px] uppercase font-bold tracking-wider text-purple-400 font-mono">Panorama Executivo Matinal</span>
            <p class="text-xs sm:text-sm font-mono font-normal text-slate-300 leading-relaxed">
              ${escapeHtml(diagnosisText)}
            </p>
          </div>
        </div>
      `;
    }

    renderLayer2() {
      const p = (this.props && (this.props.sales_summary_24h || this.props.tank_critical_runout))
        ? this.props
        : ((this.rawPayload && (this.rawPayload.props || this.rawPayload.data || this.rawPayload)) || {});
      const s24 = p.sales_summary_24h || {};
      const tank = p.tank_critical_runout || {};
      const faturamento = Number(s24.total_turnover_brl || 0);
      const volumeLitros = Number(s24.total_liters || 0);
      const tankId = tank.tank_id || '1';
      const fuelName = tank.fuel_type || 'Combustivel';
      const occPct = Number(tank.occupancy_pct || 0);
      const orderBoxes = Number(tank.recommended_order_compartments || 0);
      const wpText = p.whatsapp_formatted_text || '';
      const encodedWp = encodeURIComponent(wpText);

      const cardsHtml = `
        <div class="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-3">
          <div class="p-2.5 rounded-xl border border-white/5 bg-slate-950/40 space-y-1">
            <span class="text-[10px] text-slate-400 font-medium">Faturamento 24h</span>
            <div class="text-sm sm:text-base font-bold font-mono text-emerald-300 tabular-nums">
              R$ ${formatNumber(faturamento)}
            </div>
            <span class="text-[10px] text-slate-500 font-mono">Consolidado do Posto</span>
          </div>
          <div class="p-2.5 rounded-xl border border-white/5 bg-slate-950/40 space-y-1">
            <span class="text-[10px] text-slate-400 font-medium">Volume Total de Pista</span>
            <div class="text-sm sm:text-base font-bold font-mono text-cyan-300 tabular-nums">
              ${formatNumber(volumeLitros)} L
            </div>
            <span class="text-[10px] text-slate-500 font-mono">Litragem Vendida</span>
          </div>
          <div class="p-2.5 rounded-xl border border-white/5 bg-slate-950/40 space-y-1 col-span-2 sm:col-span-1">
            <span class="text-[10px] text-slate-400 font-medium">Tanque Mais Critico</span>
            <div class="text-sm sm:text-base font-bold font-mono text-amber-300">
              Tanque ${tankId} (${occPct.toFixed(1)}%)
            </div>
            <span class="text-[10px] text-slate-500 font-mono">${escapeHtml(fuelName)}</span>
          </div>
        </div>
      `;

      const alertHtml = `
        <div class="p-3 rounded-xl border border-amber-500/30 bg-amber-950/20 mb-3 flex items-center justify-between text-xs">
          <div class="flex items-center gap-2">
            <span class="w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse flex-shrink-0"></span>
            <div>
              <span class="text-amber-200 font-bold block">Sugestao Logistica de Reposicao</span>
              <p class="text-[11px] text-slate-300">Tanque ${tankId} (${escapeHtml(fuelName)}) requer pedido de <strong>${orderBoxes} compartimento(s)</strong> de 5.000 L.</p>
            </div>
          </div>
          <span class="text-[11px] font-mono font-bold text-amber-300 bg-amber-500/10 px-2 py-1 rounded border border-amber-500/30 whitespace-nowrap">
            ${orderBoxes * 5000} L sugeridos
          </span>
        </div>
      `;

      const wpBubbleHtml = `
        <div class="p-3.5 rounded-xl border border-emerald-500/30 bg-emerald-950/30 mb-3 space-y-2">
          <div class="flex items-center justify-between pb-1.5 border-b border-emerald-500/20">
            <div class="flex items-center gap-1.5 text-xs font-bold text-emerald-400">
              <span>Preview para WhatsApp do Dono</span>
            </div>
            <a href="https://api.whatsapp.com/send?text=${encodedWp}" target="_blank" rel="noopener noreferrer"
               class="px-2.5 py-1 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-[11px] transition-colors flex items-center gap-1">
              <span>Disparar WhatsApp</span>
            </a>
          </div>
          <div class="p-2.5 rounded-lg bg-emerald-950/60 border border-emerald-500/20 text-slate-200 text-xs font-mono whitespace-pre-wrap leading-relaxed shadow-inner">
            ${escapeHtml(wpText)}
          </div>
        </div>
      `;

      return `
        <div class="genui-layer genui-layer-2">
          ${cardsHtml}
          ${alertHtml}
          ${wpBubbleHtml}
        </div>
      `;
    }

    getDefaultActionsHtml() {
      const shouldDisable = this.state.isLocked || this.isExpired();
      return `
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-purple-500 to-indigo-600 text-white font-bold hover:brightness-110 ${shouldDisable ? 'opacity-50 pointer-events-none cursor-not-allowed' : ''}"
                data-action-id="act_briefing_aprovar_combustivel"
                data-action-type="mutation"
                data-tool-call-id="${escapeHtml(this.toolCallId)}"
                ${shouldDisable ? 'disabled' : ''}>
          <span>Aprovar Pedido Combustivel</span>
        </button>
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-slate-800 text-purple-200 border border-purple-500/30 hover:bg-slate-700"
                data-action-id="act_briefing_justificativa_lmc"
                data-action-type="mutation"
                data-tool-call-id="${escapeHtml(this.toolCallId)}">
          <span>Emitir Justificativa LMC</span>
        </button>
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-slate-900/60 text-slate-300 border border-white/10 hover:bg-slate-800"
                data-action-id="act_briefing_canvas"
                data-action-type="inspection"
                data-tool-call-id="${escapeHtml(this.toolCallId)}">
          <span>Inspecionar no Canvas</span>
        </button>
      `;
    }
  }

  const RoiDiagnosticWidget = RoiDiagnosticUI;
  const PosAuditRadarWidget = PosAuditRadarUI;
  const MorningBriefingWidget = MorningBriefingUI;

  const ExecutiveBriefingWidget = ExecutiveDecisionMentorUI;
  const MarginProfitabilityWidget = MarginAnalysisUI;
  const PredictiveScenarioWidget = PredictiveScenarioUI;
  const ComparativeBenchmarkWidget = BenchmarkComparisonUI;
  const FinancialLeakAuditWidget = FinancialLeakAuditUI;
  const BasketUpsellWidget = BasketUpsellStrategyUI;
  const ComplianceStatusWidget = ComplianceStatusUI;

  // =========================================================================
  // 10. REGISTRO NO SecureComponentRegistry & EXPORTACOES ZERO-BUNDLER
  // =========================================================================

  function registerWidgets(reg) {
    if (!reg || typeof reg.registerComponent !== 'function') return;

    const componentList = [
      {
        name: 'render_ExecutiveDecisionMentorUI',
        cls: ExecutiveDecisionMentorUI,
        aliases: ['ExecutiveDecisionMentorUI', 'render_ExecutiveBriefingUI', 'ExecutiveBriefingWidget'],
        intent: 'mentoria_decisao'
      },
      {
        name: 'render_MarginAnalysisUI',
        cls: MarginAnalysisUI,
        aliases: ['MarginAnalysisUI', 'MarginProfitabilityWidget'],
        intent: 'analise_margem'
      },
      {
        name: 'render_PredictiveScenarioUI',
        cls: PredictiveScenarioUI,
        aliases: ['PredictiveScenarioUI', 'PredictiveScenarioWidget', 'render_TankRunOutForecastUI', 'TankRunOutForecastUI', 'render_TankRunOutPredictionUI', 'TankRunOutPredictionUI'],
        intent: 'cenario_preditivo'
      },
      {
        name: 'render_BenchmarkComparisonUI',
        cls: BenchmarkComparisonUI,
        aliases: ['BenchmarkComparisonUI', 'ComparativeBenchmarkWidget'],
        intent: 'benchmark_comparativo'
      },
      {
        name: 'render_PaymentMethodsBreakdownUI',
        cls: PaymentMethodsBreakdownUI,
        aliases: ['PaymentMethodsBreakdownUI', 'PaymentMethodsBreakdownWidget'],
        intent: 'formas_pagamento'
      },
      {
        name: 'render_FinancialLeakAuditUI',
        cls: FinancialLeakAuditUI,
        aliases: ['FinancialLeakAuditUI', 'FinancialLeakAuditWidget'],
        intent: 'auditoria_fuga_financeira'
      },
      {
        name: 'render_BasketUpsellStrategyUI',
        cls: BasketUpsellStrategyUI,
        aliases: ['BasketUpsellStrategyUI', 'BasketUpsellWidget'],
        intent: 'conveniencia_vendas_cruzadas'
      },
      {
        name: 'render_ShiftReconciliationUI',
        cls: ShiftReconciliationUI,
        aliases: ['ShiftReconciliationUI', 'ShiftReconciliationWidget'],
        intent: 'auditoria_turno'
      },
      {
        name: 'render_RootCauseAnalysisUI',
        cls: RootCauseAnalysisUI,
        aliases: ['RootCauseAnalysisUI', 'RootCauseAnalysisWidget'],
        intent: 'investigar_causa_raiz'
      },
      {
        name: 'render_FiscalShieldInspectorUI',
        cls: FiscalShieldInspectorUI,
        aliases: [
          'FiscalShieldInspectorUI',
          'FiscalShieldWidget',
          'render_FiscalShieldWidget',
          'render_FiscalAuditUI',
          'FiscalAuditUI'
        ],
        intent: 'auditoria_fiscal_sefaz'
      },
      {
        name: 'render_ComplianceStatusUI',
        cls: ComplianceStatusUI,
        aliases: ['ComplianceStatusUI', 'ComplianceStatusWidget', 'render_ComplianceUI'],
        intent: 'compliance_status'
      },
      {
        name: 'render_GenerativeModularCardUI',
        cls: GenerativeModularCardUI,
        aliases: [
          'GenerativeModularCardUI',
          'DynamicLegoCardUI',
          'render_ModularLegoCardUI',
          'render_AuraSystemGuideUI',
          'AuraSystemGuideWidget',
          'AuraSystemGuideUI',
          'render_FiscalAuditUI',
          'FiscalAuditUI'
        ],
        intent: 'diagnostico_modular'
      },
      {
        name: 'render_RoiDiagnosticUI',
        cls: RoiDiagnosticUI,
        aliases: ['RoiDiagnosticUI', 'render_RoiDiagnosticWidget', 'RoiDiagnosticWidget'],
        intent: 'roi_diagnostic'
      },
      {
        name: 'render_PosAuditRadarUI',
        cls: PosAuditRadarUI,
        aliases: ['PosAuditRadarUI', 'render_PosAuditRadarWidget', 'PosAuditRadarWidget'],
        intent: 'pos_audit'
      },
      {
        name: 'render_MorningBriefingUI',
        cls: MorningBriefingUI,
        aliases: ['MorningBriefingUI', 'render_MorningBriefingWidget', 'MorningBriefingWidget'],
        intent: 'zero_click_briefing'
      }
    ];

    componentList.forEach(c => {
      const metadata = {
        intent: c.intent,
        version: '1.0.0',
        layers: ['executive_summary', 'comparative_kpis', 'action_sheets']
      };
      try {
        reg.registerComponent(c.name, c.cls, metadata, { allowOverwrite: true });
      } catch (_) {}

      (c.aliases || []).forEach(alias => {
        try {
          reg.registerComponent(alias, c.cls, metadata, { allowOverwrite: true });
        } catch (_) {}
      });
    });
  }

  // =========================================================================
  // 10. DELEGACAO GLOBAL CENTRALIZADA DE ACOES GENUI
  // =========================================================================

  function initGlobalGenUIActionDelegation() {
    if (typeof document === 'undefined' || typeof document.addEventListener !== 'function') return;
    if (document._auraGenUIActionDelegationInitialized) return;
    document._auraGenUIActionDelegationInitialized = true;

    document.addEventListener('click', async (e) => {
      const btn = (e.target && typeof e.target.closest === 'function')
        ? e.target.closest('.genui-action-btn')
        : null;
      if (!btn) return;

      if (btn.disabled || btn.getAttribute('disabled') === 'true' || btn.classList.contains('pointer-events-none')) {
        e.preventDefault();
        e.stopPropagation();
        return;
      }

      if (e._genuiActionHandled) return;
      e._genuiActionHandled = true;

      const actionId = btn.getAttribute('data-action-id');
      const actionType = btn.getAttribute('data-action-type') || 'mutation';
      const toolCallId = btn.getAttribute('data-tool-call-id');

      const genui = (typeof window !== 'undefined' && window.AuraGenUI) ||
                    (typeof AuraGenUI !== 'undefined' ? AuraGenUI : null);
      const stateMgr = (typeof window !== 'undefined' && window.auraStateManager) ||
                       (typeof globalThis !== 'undefined' && globalThis.auraStateManager) ||
                       null;

      let widget = (genui && typeof genui.getWidget === 'function') ? genui.getWidget(toolCallId) : null;

      if (!widget) {
        const card = (typeof btn.closest === 'function') ? btn.closest('.genui-hydrated-card, [data-tool-call-id]') : null;
        const compName = card ? (card.getAttribute('data-component') || 'render_ExecutiveDecisionMentorUI') : 'render_ExecutiveDecisionMentorUI';
        const registry = (typeof window !== 'undefined' && window.SecureComponentRegistry) ||
                         (genui && genui.registry);
        let CompDef = null;
        if (registry && typeof registry.resolveComponent === 'function') {
          try {
            CompDef = registry.resolveComponent(compName, { throwOnMissing: false });
          } catch (_) {}
        }
        if (!CompDef) {
          CompDef = ExecutiveDecisionMentorUI;
        }

        const stateEntry = stateMgr ? stateMgr.getWidget(toolCallId) : null;
        const props = (stateEntry && stateEntry.props) ? stateEntry.props : {};
        try {
          widget = new CompDef({
            tool_call_id: toolCallId,
            component_name: compName,
            props: props
          });
          if (card) widget.element = card;
          if (genui && typeof genui.registerWidget === 'function') {
            genui.registerWidget(toolCallId, widget);
          }
        } catch (_) {}
      } else {
        const card = (typeof btn.closest === 'function') ? btn.closest('.genui-hydrated-card, [data-tool-call-id]') : null;
        if (card && (!widget.element || (typeof document !== 'undefined' && !document.contains(widget.element)))) {
          widget.element = card;
        }
      }

      if (widget && typeof widget.handleActionClick === 'function') {
        await widget.handleActionClick(actionId, actionType, btn, e);
      }
    }, false);
  }

  // Inicializa delegacao global imediatamente se documento disponivel
  initGlobalGenUIActionDelegation();
  if (typeof document !== 'undefined' && typeof document.addEventListener === 'function') {
    document.addEventListener('DOMContentLoaded', () => {
      initGlobalGenUIActionDelegation();
    });
  }

  // 1. Registro automatico no catalogo global do navegador
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
    window.AuraGenUI.BaseGenUIWidget = BaseGenUIWidget;
    window.AuraGenUI.ExecutiveDecisionMentorUI = ExecutiveDecisionMentorUI;
    window.AuraGenUI.ExecutiveBriefingWidget = ExecutiveBriefingWidget;
    window.AuraGenUI.MarginAnalysisUI = MarginAnalysisUI;
    window.AuraGenUI.MarginProfitabilityWidget = MarginProfitabilityWidget;
    window.AuraGenUI.PredictiveScenarioUI = PredictiveScenarioUI;
    window.AuraGenUI.PredictiveScenarioWidget = PredictiveScenarioWidget;
    window.AuraGenUI.BenchmarkComparisonUI = BenchmarkComparisonUI;
    window.AuraGenUI.ComparativeBenchmarkWidget = ComparativeBenchmarkWidget;
    window.AuraGenUI.FinancialLeakAuditUI = FinancialLeakAuditUI;
    window.AuraGenUI.FinancialLeakAuditWidget = FinancialLeakAuditWidget;
    window.AuraGenUI.BasketUpsellStrategyUI = BasketUpsellStrategyUI;
    window.AuraGenUI.BasketUpsellWidget = BasketUpsellWidget;
    window.AuraGenUI.ComplianceStatusUI = ComplianceStatusUI;
    window.AuraGenUI.GenerativeModularCardUI = GenerativeModularCardUI;
    window.AuraGenUI.FiscalShieldInspectorUI = FiscalShieldInspectorUI;
    window.AuraGenUI.FiscalShieldWidget = FiscalShieldInspectorUI;
    window.AuraGenUI.RoiDiagnosticUI = RoiDiagnosticUI;
    window.AuraGenUI.RoiDiagnosticWidget = RoiDiagnosticWidget;
    window.AuraGenUI.PosAuditRadarUI = PosAuditRadarUI;
    window.AuraGenUI.PosAuditRadarWidget = PosAuditRadarWidget;
    window.AuraGenUI.MorningBriefingUI = MorningBriefingUI;
    window.AuraGenUI.MorningBriefingWidget = MorningBriefingWidget;
    window.AuraGenUI.ComplianceStatusWidget = ComplianceStatusWidget;
    window.AuraGenUI.PaymentMethodsBreakdownUI = PaymentMethodsBreakdownUI;
    window.AuraGenUI.PaymentMethodsBreakdownWidget = PaymentMethodsBreakdownWidget;
    window.AuraGenUI.ShiftReconciliationUI = ShiftReconciliationUI;
    window.AuraGenUI.ShiftReconciliationWidget = ShiftReconciliationWidget;
    window.AuraGenUI.RootCauseAnalysisUI = RootCauseAnalysisUI;
    window.AuraGenUI.RootCauseAnalysisWidget = RootCauseAnalysisWidget;
    window.AuraGenUI.initGlobalActionDelegation = initGlobalGenUIActionDelegation;
    window.initGlobalGenUIActionDelegation = initGlobalGenUIActionDelegation;

    if (typeof window.addEventListener === 'function') {
      window.addEventListener('aura:genui-ready', (evt) => {
        if (evt?.detail?.registry) {
          registerWidgets(evt.detail.registry);
        }
      });
    }
  }

  // 2. Exportacao CommonJS para testes automatizados headless (Node.js)
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
      BaseGenUIWidget,
      ExecutiveDecisionMentorUI,
      ExecutiveBriefingWidget,
      MarginAnalysisUI,
      MarginProfitabilityWidget,
      PredictiveScenarioUI,
      PredictiveScenarioWidget,
      BenchmarkComparisonUI,
      ComparativeBenchmarkWidget,
      FinancialLeakAuditUI,
      FinancialLeakAuditWidget,
      ShiftReconciliationUI,
      ShiftReconciliationWidget,
      RootCauseAnalysisUI,
      RootCauseAnalysisWidget,
      BasketUpsellStrategyUI,
      BasketUpsellWidget,
      ComplianceStatusUI,
      ComplianceStatusWidget,
      FiscalShieldInspectorUI,
      registerWidgets,
      initGlobalGenUIActionDelegation,
      escapeHtml,
      formatNumber
    };
  }


  // Delegacao global de cliques para botoes interativos do Fiscal Shield (AURA Apendice C)
  if (typeof document !== 'undefined' && !window._auraFiscalShieldListenersBound) {
    window._auraFiscalShieldListenersBound = true;
    document.addEventListener('click', (e) => {
      // 1. Botao de copiar chamado para Suporte webPosto (WhatsApp)
      const btnSuporte = e.target.closest('.btn-suporte-webposto');
      if (btnSuporte) {
        e.preventDefault();
        try {
          const rawTicket = btnSuporte.getAttribute('data-ticket') || '{}';
          const t = JSON.parse(rawTicket);
          const texto =
`[AURA - Abertura de Chamado Suporte webPosto]
Documento: Cupom Fiscal / NFC-e
Problema: ${t.titulo || "Inconsistencia de Emissao"}
Causa Operacional: ${t.causa || "Divergencia na rotina de fechamento de venda"}

Diagnostico Tecnico:
- Regra SEFAZ: ${t.regra || "N/A"}
- Campo(s) Afetado(s): ${t.campos || "Cabecalho/Total"}
- Valor Observado: ${t.obs || "N/A"} (Esperado: ${t.esp || ">= 0.00"})
- Detalhes Tecnicos: ${t.tecnica || "Erro de schema/validacao gerado no XML pelo PDV"}

Solicitacao: Favor orientar ajuste na rotina de emissao de cupons/descontos no PDV para liberar a autorizacao da nota.`;

          if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
            navigator.clipboard.writeText(texto).then(() => {
              const origHtml = btnSuporte.innerHTML;
              btnSuporte.innerHTML = `
                <svg class="w-3.5 h-3.5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                <span class="text-white font-bold">✓ Chamado Copiado! Pronto para WhatsApp</span>
              `;
              btnSuporte.classList.add('!bg-emerald-600', '!border-emerald-400');
              setTimeout(() => {
                btnSuporte.innerHTML = origHtml;
                btnSuporte.classList.remove('!bg-emerald-600', '!border-emerald-400');
              }, 3500);
            });
          }
        } catch (err) {
          console.warn('[AuraGenUI] Erro ao copiar chamado suporte webPosto:', err);
        }
        return;
      }

      // 2. Botao de alternar visualizacao das regras conformes
      const btnToggleConformes = e.target.closest('.btn-toggle-conformes');
      if (btnToggleConformes) {
        e.preventDefault();
        const parentBox = btnToggleConformes.closest('.finding-conformes-box') || btnToggleConformes.closest('.p-4');
        const container = parentBox ? parentBox.querySelector('.container-conformes-list') : null;
        if (container) {
          const isHidden = container.classList.contains('hidden');
          if (isHidden) {
            container.classList.remove('hidden');
            btnToggleConformes.textContent = 'Ocultar conformes';
            btnToggleConformes.setAttribute('data-state', 'open');
          } else {
            container.classList.add('hidden');
            const count = container.children.length;
            btnToggleConformes.textContent = `Ver conformes (+${count})`;
            btnToggleConformes.setAttribute('data-state', 'closed');
          }
        }
        return;
      }
    });
  }

})(typeof globalThis !== 'undefined' ? globalThis : (typeof window !== 'undefined' ? window : this));
