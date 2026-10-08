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

  // =========================================================================
  // 2. CLASSE BASE: BaseGenUIWidget
  // =========================================================================

  class BaseGenUIWidget {
    constructor(payload = {}, defaultIntent = 'mentoria_decisao', defaultComp = 'render_BaseGenUIWidget') {
      this.toolCallId = escapeHtml(payload.tool_call_id || ('call_' + Date.now()));
      this.intent = escapeHtml(payload.intent || defaultIntent);
      this.componentName = escapeHtml(payload.component_name || defaultComp);
      this.summary = escapeHtml(payload.executive_summary || payload.summary_text || '');
      this.props = (typeof AuraGenUI !== 'undefined' && typeof AuraGenUI.sanitizeProps === 'function')
        ? AuraGenUI.sanitizeProps(payload.props || {})
        : (payload.props || {});
      this.actions = Array.isArray(payload.actions) ? payload.actions : [];
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
      return `
        <button type="button"
                class="genui-action-btn px-3 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 font-bold hover:brightness-110 ${shouldDisable ? 'opacity-50 pointer-events-none cursor-not-allowed' : ''}"
                data-action-id="act_default_1"
                data-action-type="inspection"
                data-tool-call-id="${escapeHtml(this.toolCallId)}"
                ${shouldDisable ? 'disabled' : ''}>
          <span>⚡ Aplicar Recomendacoes Prioritarias</span>
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
              <span class="font-bold text-white">${escapeHtml(feedback || 'Acao Homologada no ERP')}</span>
            </div>
            <span class="badge-committed text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-emerald-900/60 text-emerald-300 border border-emerald-500/30">VOUCHER AUDITADO</span>
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

          const isActionDone = stateMgr && typeof stateMgr.isActionExecuted === 'function' && stateMgr.isActionExecuted(act.action_id);
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
          if (isActionDone) {
            displayLabel = `✔ ${label}`;
          } else if (isCurrentActive) {
            displayLabel = `<span class="inline-flex items-center gap-1.5"><svg class="animate-spin -ml-0.5 mr-1 h-3.5 w-3.5 text-cyan-400 inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path></svg><span class="animate-pulse">Processando...</span></span>`;
          }

          return `
            <button type="button"
                    class="genui-action-btn ${btnClass}"
                    data-action-id="${actId}"
                    data-action-type="${escapeHtml(actType)}"
                    data-tool-call-id="${escapeHtml(this.toolCallId)}"
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
      if (actionType === 'inspection' || btnText.includes('Canvas')) {
        const now = Date.now();
        if (now - (this._canvasDebounce || 0) < 800) {
          return false;
        }
        this._canvasDebounce = now;
        this.projectToCanvas();
        return true;
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
      if (typeof window !== 'undefined' && window.auraApi && typeof window.auraApi.executeAction === 'function') {
        try {
          const res = await window.auraApi.executeAction(actionId, {
            tool_call_id: this.toolCallId,
            session_id: this.sessionId || (typeof window !== 'undefined' && window.auraChat && window.auraChat.sessionId) || '',
            action_name: actionDef.label || actionDef.name || actionDef.action_name || 'acao_executiva',
            action_type: actionDef.action_type || actionType || 'mutation',
            payload: actionDef.payload,
            operator_id: 'operador_01'
          });
          if (stateMgr) {
            stateMgr.markActionExecuted(actionId, res);
            stateMgr.finalizeSuccessState(this.toolCallId, res);
          }
          this.finalizeSuccessState(res);
          return true;
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
      return true;
    }

    applyOptimisticState(actionIdOrData, feedbackText = 'Processando autorizacao no ERP...') {
      let actId = null;
      let feedback = feedbackText;
      if (typeof actionIdOrData === 'object' && actionIdOrData !== null) {
        actId = actionIdOrData.actionId || actionIdOrData.action_id || null;
        feedback = actionIdOrData.feedback || actionIdOrData.label || feedbackText;
        if (actionIdOrData.status) this.state.status = actionIdOrData.status;
      } else {
        actId = actionIdOrData;
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
      if (this.state.status === 'locked' || this.state.status === 'optimistic') {
        this.state.status = 'failed';
      }
      this.refreshLayer3();
    }

    finalizeSuccessState(result = {}) {
      this.state.status = 'committed';
      this.state.isLocked = false;
      this.state.lockedActionId = null;
      this.state.voucher = result;
      this.state.optimisticFeedback = `✔ Acao Homologada com Sucesso (Voucher: ${result?.voucher_id || 'OK'})`;
      this.state.errorMessage = null;
      this.refreshLayer3();
    }

    refreshLayer3() {
      if (!this.element) return;
      if (typeof this.element.querySelector === 'function') {
        const layer3El = this.element.querySelector('.genui-layer-3');
        if (layer3El && layer3El.parentNode && typeof layer3El.parentNode.replaceChild === 'function') {
          const temp = document.createElement('div');
          temp.innerHTML = this.renderLayer3().trim();
          const newLayer3 = temp.firstElementChild;
          if (newLayer3) {
            try {
              layer3El.parentNode.replaceChild(newLayer3, layer3El);
              this.bindEvents(this.element);
              return;
            } catch (_) {}
          }
        }
      }
      if (typeof this.element === 'object') {
        this.element.innerHTML = this.renderHtml();
        this.bindEvents(this.element);
      }
    }

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
            <p class="text-xs sm:text-sm font-sans font-medium text-slate-100 leading-relaxed">
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
            <p class="text-xs sm:text-sm font-sans font-medium text-slate-100 leading-relaxed">
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
            <p class="text-xs sm:text-sm font-sans font-medium text-slate-100 leading-relaxed">
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
            <p class="text-xs sm:text-sm font-sans font-medium text-slate-100 leading-relaxed">
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
            <p class="text-xs sm:text-sm font-sans font-medium text-slate-100 leading-relaxed">
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
      const diagnosisText = p.diagnosis || this.summary || 'Oportunidades de vendas cruzadas e aumento de ticket medio no PDV e pista.';

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
            <p class="text-xs sm:text-sm font-sans font-medium text-slate-100 leading-relaxed">
              ${escapeHtml(diagnosisText)}
            </p>
          </div>
        </div>
      `;
    }

    renderLayer2() {
      const p = this.props || {};
      const combos = Array.isArray(p.top_combos) ? p.top_combos : [];
      const monthlyLift = Number(p.projected_monthly_revenue_lift || 0);
      const limitations = Array.isArray(p.limitations) ? p.limitations : [];

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
              const anchor = escapeHtml(c.anchor_product || 'Origem');
              const rec = escapeHtml(c.recommended_product || 'Recomendado');
              const lift = formatNumber(c.lift || 1.0);
              const conf = formatNumber(c.confidence_pct || 0, 1);
              const extraR = formatNumber(c.additional_ticket_reais || 0);
              const pitch = escapeHtml(c.script_pitch || '');

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
  // 9. ALIASES E NOMES CANONICOS DO ROADMAP
  // =========================================================================

  const ExecutiveBriefingWidget = ExecutiveDecisionMentorUI;
  const MarginProfitabilityWidget = MarginAnalysisUI;
  const PredictiveScenarioWidget = PredictiveScenarioUI;
  const ComparativeBenchmarkWidget = BenchmarkComparisonUI;
  const FinancialLeakAuditWidget = FinancialLeakAuditUI;
  const BasketUpsellWidget = BasketUpsellStrategyUI;

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
        aliases: ['PredictiveScenarioUI', 'PredictiveScenarioWidget'],
        intent: 'cenario_preditivo'
      },
      {
        name: 'render_BenchmarkComparisonUI',
        cls: BenchmarkComparisonUI,
        aliases: ['BenchmarkComparisonUI', 'ComparativeBenchmarkWidget'],
        intent: 'benchmark_comparativo'
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
      BasketUpsellStrategyUI,
      BasketUpsellWidget,
      registerWidgets,
      escapeHtml,
      formatNumber
    };
  }

})(typeof globalThis !== 'undefined' ? globalThis : (typeof window !== 'undefined' ? window : this));
