/**
 * AURA Reasoning Ribbon (Fase P1-UI2: Transparencia em Tempo Real + Trust Pill)
 * Pipeline visual compacto de 28px em 4 estagios:
 *   1. Filtro LGPD & PII (#10B981)
 *   2. Fonte Read-Only / Cache Semantico (#22D3EE)
 *   3. Calculo Python Deterministico (#10B981)
 *   4. Sintese Executiva (#8B5CF6 / recalibracao #22D3EE em stream_reset)
 * Ao finalizar (done), contrai-se em uma Trust Pill clicavel com micro-painel auditavel.
 * Zero travessoes em todo o arquivo.
 */
(function (root) {
  'use strict';

  function esc(str) {
    return String(str === null || str === undefined ? '' : str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  class AuraReasoningRibbon {
    constructor() {
      this.states = new Map();
    }

    ensureState(containerId) {
      if (!this.states.has(containerId)) {
        this.states.set(containerId, {
          startedAt: Date.now(),
          lgpdCount: 0,
          sourceType: 'sql_ro',
          sourceLabel: 'SQL Read-Only',
          toolDisplayName: '',
          intentName: '',
          deterministicUsed: false,
          synthesisStarted: false,
          recalibrating: false,
          finalized: false,
          success: true,
          drawerOpen: false,
          telemetry: null,
          activeStage: 'lgpd',
          customLabel: ''
        });
      }
      return this.states.get(containerId);
    }

    getTargets(containerId) {
      if (typeof document === 'undefined') return [];
      const ids = [containerId + '-reasoning-ribbon', containerId + '-split-reasoning-ribbon'];
      return ids.map((id) => document.getElementById(id)).filter(Boolean);
    }

    start(containerId, initialLabel) {
      const st = this.ensureState(containerId);
      st.startedAt = Date.now();
      st.activeStage = 'lgpd';
      st.customLabel = initialLabel || '';
      this.renderLive(containerId);
    }

    markSource(containerId, { cacheHit = false, toolName = '', intentName = '', label = '' } = {}) {
      const st = this.ensureState(containerId);
      st.activeStage = 'source';
      if (cacheHit) {
        st.sourceType = 'cache';
        st.sourceLabel = 'Cache Semantico (0 tokens)';
      } else {
        st.sourceType = 'sql_ro';
        if (toolName) st.toolDisplayName = toolName;
        if (intentName) st.intentName = intentName;
        st.sourceLabel = label || (toolName ? `SQL Read-Only · ${toolName}` : 'SQL Read-Only');
      }
      this.renderLive(containerId);
    }

    markDeterministic(containerId, label = '') {
      const st = this.ensureState(containerId);
      st.deterministicUsed = true;
      st.activeStage = 'deterministic';
      if (label) st.customLabel = label;
      this.renderLive(containerId);
    }

    markSynthesis(containerId, { recalibrating = false, label = '' } = {}) {
      const st = this.ensureState(containerId);
      st.synthesisStarted = true;
      st.recalibrating = recalibrating;
      st.activeStage = 'synthesis';
      if (label) st.customLabel = label;
      this.renderLive(containerId);
    }

    updateTelemetry(containerId, telemetry) {
      const st = this.ensureState(containerId);
      st.telemetry = telemetry || {};
      if (telemetry && typeof telemetry.lgpd_sanitized_count === 'number') {
        st.lgpdCount = telemetry.lgpd_sanitized_count;
      }
      if (telemetry && telemetry.tokens && telemetry.tokens.contingency_zero_token) {
        st.sourceType = 'cache';
      }
      if (st.finalized) {
        this.renderTrustPill(containerId);
      } else {
        this.renderLive(containerId);
      }
    }

    finalize(containerId, { success = true, telemetry = null } = {}) {
      const st = this.ensureState(containerId);
      st.finalized = true;
      st.success = success;
      st.recalibrating = false;
      if (telemetry) {
        st.telemetry = telemetry;
        if (typeof telemetry.lgpd_sanitized_count === 'number') {
          st.lgpdCount = telemetry.lgpd_sanitized_count;
        }
      }
      this.renderTrustPill(containerId);
    }

    renderLive(containerId) {
      const st = this.ensureState(containerId);
      const targets = this.getTargets(containerId);
      if (targets.length === 0) return;

      const lgpdLabel = st.lgpdCount > 0 ? `LGPD: ${st.lgpdCount} mascarados` : 'Filtro LGPD Ativo';
      const sourceLabel = st.sourceLabel || 'SQL Read-Only';
      const detLabel = 'Calculo Python Auditado';
      const synthLabel = st.recalibrating
        ? (st.customLabel || 'Recalibrando modelo de contingencia...')
        : 'Sintetizando recomendacao...';

      const stageOrder = ['lgpd', 'source', 'deterministic', 'synthesis'];
      const activeIdx = stageOrder.indexOf(st.activeStage);

      const stepState = (name) => {
        const idx = stageOrder.indexOf(name);
        if (idx < activeIdx) return 'done';
        if (idx === activeIdx) return 'active';
        return 'pending';
      };

      const renderStep = (name, label, tone, dotColor) => {
        const state = stepState(name);
        if (state === 'pending' && name !== 'lgpd' && name !== 'source') {
          return '';
        }
        const pulse = state === 'active' ? 'animate-pulse' : '';
        return `
          <span class="aura-ribbon-step" data-stage="${name}" data-state="${state}" data-tone="${tone}">
            <span class="aura-ribbon-dot ${dotColor} ${pulse}"></span>
            <span>${esc(label)}</span>
          </span>
        `;
      };

      const html = `
        <div class="aura-reasoning-ribbon" role="status" aria-live="polite">
          ${renderStep('lgpd', lgpdLabel, 'emerald', 'bg-emerald-400')}
          ${renderStep('source', sourceLabel, 'cyan', 'bg-cyan-400')}
          ${st.deterministicUsed ? renderStep('deterministic', detLabel, 'emerald', 'bg-emerald-400') : ''}
          ${st.synthesisStarted ? renderStep('synthesis', synthLabel, st.recalibrating ? 'cyan' : 'violet', st.recalibrating ? 'bg-cyan-400' : 'bg-purple-400') : ''}
        </div>
      `;

      targets.forEach((el) => {
        el.innerHTML = html;
        el.classList.remove('hidden');
      });
    }

    renderTrustPill(containerId) {
      const st = this.ensureState(containerId);
      const targets = this.getTargets(containerId);
      if (targets.length === 0) return;

      const t = st.telemetry || {};
      const e2eMs = t.total_e2e_ms
        ? `${Number(t.total_e2e_ms).toFixed(0)}ms`
        : `${Math.max(40, Date.now() - st.startedAt)}ms`;
      const ttftMs = t.ttft_ms ? `${Number(t.ttft_ms).toFixed(0)}ms` : null;
      const model = t.llm_model || 'Gemini Flash';
      const tokens = t.tokens || {};
      const totalTokens = tokens.total_tokens || t.total_tokens || 0;
      const sourceShort = st.sourceType === 'cache' ? 'Cache Semantico' : 'SQL Read-Only';
      const detSegment = st.deterministicUsed ? ' · Calculo Deterministico' : '';
      const lgpdSegment = st.lgpdCount > 0 ? ` · LGPD (${st.lgpdCount})` : ' · LGPD Ativa';
      const statusDot = st.success ? 'text-emerald-400' : 'text-amber-400';
      const statusIcon = st.success ? '✓' : '!';

      const drawerId = `${containerId}-trust-drawer`;
      const html = `
        <div class="aura-trust-container">
          <button type="button"
                  class="aura-trust-pill"
                  data-trust-toggle="${esc(containerId)}"
                  aria-expanded="${st.drawerOpen ? 'true' : 'false'}"
                  aria-controls="${esc(drawerId)}">
            <span class="${statusDot} font-bold">${statusIcon}</span>
            <span>${esc(sourceShort)}${esc(detSegment)}${esc(lgpdSegment)} · <strong class="text-slate-100 tabular-nums">${esc(e2eMs)}</strong></span>
            <span class="text-slate-400 text-[10px]">${st.drawerOpen ? '▴' : '▾'}</span>
          </button>
          <div id="${esc(drawerId)}" class="aura-trust-drawer ${st.drawerOpen ? '' : 'hidden'}">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
              <div><span class="text-slate-500">Origem:</span> <span class="text-cyan-300">${esc(st.sourceType === 'cache' ? 'Cache Semantico Local' : 'PostgreSQL Read-Only')}</span></div>
              <div><span class="text-slate-500">Motor:</span> <span class="text-purple-300">${esc(model)}</span></div>
              <div><span class="text-slate-500">Latencia:</span> <span class="text-emerald-300 tabular-nums">${esc(e2eMs)}${ttftMs ? ` (TTFT ${esc(ttftMs)})` : ''}</span></div>
              <div><span class="text-slate-500">Privacidade:</span> <span class="text-emerald-300">LGPD Ativa (${st.lgpdCount} PII mascarados)</span></div>
              ${st.toolDisplayName ? `<div><span class="text-slate-500">Ferramenta:</span> <span class="text-slate-200">${esc(st.toolDisplayName)}</span></div>` : ''}
              ${totalTokens > 0 ? `<div><span class="text-slate-500">Tokens:</span> <span class="text-slate-300 tabular-nums">${totalTokens.toLocaleString('pt-BR')}</span></div>` : ''}
            </div>
            <div class="mt-2 pt-2 border-t border-white/5 flex justify-end">
              <button type="button"
                      class="text-[11px] text-cyan-300 hover:text-cyan-200 font-sans font-medium cursor-pointer"
                      data-open-audit-canvas="${esc(containerId)}">
                Abrir Linhagem &amp; Regras no Canvas ->
              </button>
            </div>
          </div>
        </div>
      `;

      targets.forEach((el) => {
        el.innerHTML = html;
        el.classList.remove('hidden');
        const toggleBtn = el.querySelector('[data-trust-toggle]');
        if (toggleBtn) {
          toggleBtn.addEventListener('click', () => {
            st.drawerOpen = !st.drawerOpen;
            this.renderTrustPill(containerId);
          });
        }
        const auditBtn = el.querySelector('[data-open-audit-canvas]');
        if (auditBtn) {
          auditBtn.addEventListener('click', () => {
            if (window.auraAuxPanel) {
              if (typeof window.auraAuxPanel.open === 'function') window.auraAuxPanel.open();
              if (typeof window.auraAuxPanel.switchTab === 'function') window.auraAuxPanel.switchTab('audit');
            }
          });
        }
      });
    }
  }

  if (typeof window !== 'undefined') {
    window.AuraReasoningRibbon = AuraReasoningRibbon;
    window.auraReasoningRibbon = new AuraReasoningRibbon();
  }

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { AuraReasoningRibbon };
  }
})(typeof window !== 'undefined' ? window : globalThis);
