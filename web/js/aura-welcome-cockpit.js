/**
 * AURA Welcome Cockpit (Fase 3: Cockpit de Prontidao do Posto)
 *
 * Substitui o texto longo estatico do card de boas-vindas por 3 mini-indicadores
 * operacionais lidos DIRETAMENTE das ferramentas analiticas ja existentes no backend
 * (POST /api/v1/aura/execute-intent via window.auraApi.executeIntent):
 *   1. Reserva de Tanques    <- ferramenta "run_out"           (autonomia critica < 24h)
 *   2. Conciliacao do Turno  <- ferramenta "conciliacao_turno" (batido ou divergente)
 *   3. Conformidade LMC      <- ferramenta "lmc_anp"           (tolerancia de 0,60% da ANP)
 *
 * Regras de integridade:
 * - Nenhum numero fixo: todo valor exibido vem do payload retornado pela API.
 * - Carregamento assincrono (apos ociosidade do navegador): nunca bloqueia a abertura do chat.
 * - Enquanto carrega: skeleton. Se a API falhar, vier vazia ou indisponivel: estado neutro
 *   "Sem dados no momento". Jamais valores ficticios apresentados como reais.
 * - Respeita prefers-reduced-motion e GPU Guard via CSS (aura.css, secao Fase 3).
 */
(function (root) {
  'use strict';

  const ANP_TOLERANCE_PCT_DEFAULT = 0.6;
  const TANK_RESERVE_HOURS = 24;
  const CACHE_TTL_MS = 60000;
  const REQUEST_TIMEOUT_MS = 10000;
  const NEUTRAL_VALUE = 'Sem dados no momento';

  function toNum(v) {
    if (v === null || v === undefined || v === '') return null;
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  }

  function fmtDecimal(n, digits) {
    return Number(n).toLocaleString('pt-BR', {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
  }

  function fmtMoney(n) {
    return 'R$ ' + fmtDecimal(Math.abs(n), 2);
  }

  function fmtSignedPct(n) {
    return (n > 0 ? '+' : '') + fmtDecimal(n, 2) + '%';
  }

  function fmtIsoDay(iso) {
    const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso || ''));
    return m ? m[3] + '/' + m[2] : '';
  }

  function neutral(detail) {
    return { state: 'neutral', value: NEUTRAL_VALUE, detail: detail || '' };
  }

  /**
   * Extrai o payload da ferramenta do envelope de execute-intent ou objeto direto.
   * Retorna null para circuit breaker aberto, resposta vazia ou erro.
   */
  function unwrap(res) {
    if (!res || typeof res !== 'object') return null;
    if (res.status === 'circuit_open' || res.status === 'error') return null;
    const d = (res.data && typeof res.data === 'object') ? res.data : res;
    if (!d || typeof d !== 'object') return null;
    if (d.circuit_open) return null;
    if (d.status && d.status !== 'ok' && d.status !== 'sem_movimento' && d.status !== 'success') return null;
    return d;
  }

  function tankLabel(t) {
    const cod = t.codtan !== undefined && t.codtan !== null ? 'TQ-' + t.codtan : 'Tanque';
    return t.combustivel ? cod + ' ' + t.combustivel : cod;
  }

  /**
   * Indicador 1: Reserva de Tanques (autonomia critica abaixo de 24h).
   * Tanques INATIVOS ou SEM CONSUMO registrado nao entram na previsao (autonomia 0 nao significa risco).
   */
  function evaluateTanques(res) {
    const d = unwrap(res);
    if (!d) return neutral('Aguardando leitura dos tanques');
    const list = Array.isArray(d.detalhamento_tanques)
      ? d.detalhamento_tanques
      : (Array.isArray(d.tanks) ? d.tanks : null);
    if (!list || list.length === 0) return neutral('Aguardando leitura dos tanques');

    const rows = list
      .filter((t) => {
        if (!t || typeof t !== 'object') return false;
        const st = String(t.status_operacional || '').toUpperCase();
        return !(st.indexOf('INATIVO') !== -1 || st.indexOf('SEM CONSUMO') !== -1);
      })
      .map((t) => ({
        label: tankLabel(t),
        hours: toNum(t.autonomia_critica_horas),
        critical: t.alerta_critico === true,
      }));

    if (rows.length === 0) return neutral('Sem consumo registrado para prever a autonomia');

    const reserve = rows.filter((r) => r.critical || (r.hours !== null && r.hours < TANK_RESERVE_HOURS));
    if (reserve.length > 0) {
      reserve.sort((a, b) => (a.hours === null ? 0 : a.hours) - (b.hours === null ? 0 : b.hours));
      const worst = reserve[0];
      const n = reserve.length;
      const detail = worst.hours !== null && worst.hours > 0
        ? 'Menor autonomia: ' + fmtDecimal(worst.hours, 1) + ' h (' + worst.label + ')'
        : worst.label + ': nível crítico atingido';
      return {
        state: 'alert',
        value: n + (n === 1 ? ' tanque em reserva' : ' tanques em reserva'),
        detail: detail,
      };
    }

    const withHours = rows.filter((r) => r.hours !== null);
    if (withHours.length === 0) return neutral('Aguardando histórico de consumo');
    withHours.sort((a, b) => a.hours - b.hours);
    return {
      state: 'ok',
      value: 'Acima de ' + TANK_RESERVE_HOURS + ' h',
      detail: 'Menor autonomia crítica: ' + fmtDecimal(withHours[0].hours, 1) + ' h (' + withHours[0].label + ')',
    };
  }

  /**
   * Indicador 2: Conciliacao do ultimo turno (batido ou divergente).
   */
  function evaluateTurno(res) {
    const d = unwrap(res);
    if (!d) return neutral('Aguardando leitura de turno');
    if (d.status === 'sem_movimento') return neutral('Sem movimentação no período');

    const resumo = d.resumo_executivo || {};
    const contrato = d.contrato || {};
    const assessment = d.assessment || contrato.assessment || {};
    const metrics = d.metrics || contrato.metrics || {};

    if (assessment.finality === 'unavailable') return neutral('Aguardando leitura de turno');
    if (assessment.finality === 'no_movement') return neutral('Sem movimentação no período');

    const code = String(resumo.status_conciliacao || assessment.status_code || '').toUpperCase();
    if (!code) return neutral('Aguardando leitura de turno');

    const diffRaw = toNum(metrics.difference !== undefined ? metrics.difference : resumo.diferenca_financeira_caixa);
    const day = fmtIsoDay(d.data_auditada);
    const suffix = day ? ' (turno de ' + day + ')' : '';

    if (code.indexOf('TURNO_EM_ANDAMENTO') === 0) {
      const prov = diffRaw !== null ? ' Diferença provisória: ' + (diffRaw < 0 ? '-' : (diffRaw > 0 ? '+' : '')) + fmtMoney(diffRaw) + '.' : '';
      return { state: 'attention', value: 'Em andamento', detail: 'Caixa aberto, conferência provisória.' + prov };
    }
    if (code === 'CONCILIADO') {
      return { state: 'ok', value: 'Batido', detail: 'Pista e caixa conferem' + suffix };
    }
    if (code === 'FURO_DE_CAIXA') {
      return {
        state: 'alert',
        value: 'Divergente',
        detail: (diffRaw !== null ? 'Falta de ' + fmtMoney(diffRaw) + ' no caixa' : 'Furo de caixa apurado') + suffix,
      };
    }
    if (code === 'SOBRA_DE_CAIXA') {
      return {
        state: 'alert',
        value: 'Divergente',
        detail: (diffRaw !== null ? 'Sobra de ' + fmtMoney(diffRaw) + ' no caixa' : 'Sobra de caixa apurada') + suffix,
      };
    }
    if (code === 'DIVERGENCIA_CRITICA') {
      return { state: 'alert', value: 'Divergente', detail: 'Divergência crítica entre caixa e pista' + suffix };
    }
    if (code === 'DIVERGENCIA_PISTA') {
      return { state: 'alert', value: 'Divergente', detail: 'Diferença de litros entre encerrante e automação' + suffix };
    }
    if (code === 'PENDENCIA_ENCERRANTE') {
      return { state: 'attention', value: 'Pendente', detail: 'Encerrantes ainda não lançados' + suffix };
    }
    return neutral('Aguardando leitura de turno');
  }

  /**
   * Indicador 3: Conformidade do LMC frente a tolerancia de 0,60% da ANP.
   */
  function evaluateLmc(res) {
    const d = unwrap(res);
    if (!d) return neutral('Aguardando escrituração LMC');
    const r = d.resumo_executivo;
    if (!r || typeof r !== 'object' || !r.status_geral_anp) return neutral('Aguardando escrituração LMC');

    const total = toNum(r.total_tanques_analisados);
    if (!total) return neutral('Nenhum tanque auditado');

    const metrics = d.metrics || {};
    const tolRaw = toNum(metrics.tolerancia_oficial_pct);
    const tol = tolRaw !== null ? tolRaw : ANP_TOLERANCE_PCT_DEFAULT;
    const tolText = '±' + fmtDecimal(tol, 2) + '%';
    const alerts = Array.isArray(r.tanques_em_alerta) ? r.tanques_em_alerta : [];
    const alertCount = toNum(r.total_tanques_alerta) || alerts.length;

    if (r.status_geral_anp === 'CONFORME_ANP' && alertCount === 0) {
      const v = toNum(r.variacao_volumetrica_geral_pct);
      return {
        state: 'ok',
        value: 'Conforme',
        detail: (v !== null ? 'Variação geral ' + fmtSignedPct(v) + ' ' : '') + '(tolerância ' + tolText + ')',
      };
    }

    let worst = null;
    alerts.forEach((a) => {
      const p = toNum(a && a.variacao_pct);
      if (p !== null && (worst === null || Math.abs(p) > Math.abs(worst.pct))) {
        worst = { pct: p, tanque: a.tanque };
      }
    });
    const n = alertCount || 1;
    return {
      state: 'alert',
      value: n + (n === 1 ? ' tanque fora' : ' tanques fora') + ' da tolerância',
      detail: worst
        ? 'Maior desvio: TQ-' + worst.tanque + ' ' + fmtSignedPct(worst.pct) + ' (limite ' + tolText + ')'
        : 'Limite regulamentar ' + tolText,
    };
  }

  const INDICATORS = [
    {
      key: 'tanques',
      tool: 'run_out',
      label: 'Reserva de Tanques',
      hint: 'Toque para consultar a autonomia de cada tanque.',
      prompt: 'Qual a situação e autonomia de cada tanque agora?',
      chip: true,
      evaluate: evaluateTanques,
      icon: '<svg class="w-3.5 h-3.5 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true"><rect x="3" y="3" width="11" height="18" rx="2" stroke-width="1.75"/><line x1="2" y1="21" x2="15" y2="21" stroke-width="1.75"/><path d="M14 8h2.5a2 2 0 0 1 2 2v6.5a1.5 1.5 0 0 0 3 0V9l-2-2" stroke-width="1.5"/></svg>',
    },
    {
      key: 'turno',
      tool: 'conciliacao_turno',
      label: 'Conciliação do Turno',
      hint: 'Toque para ver como fechou o último turno.',
      prompt: 'Como fechou o último turno? Teve furo de caixa?',
      chip: true,
      evaluate: evaluateTurno,
      icon: '<svg class="w-3.5 h-3.5 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true"><rect x="2" y="6" width="20" height="12" rx="2" stroke-width="1.75"/><circle cx="12" cy="12" r="3" stroke-width="1.75"/><path d="M6 12h.01M18 12h.01" stroke-width="2"/></svg>',
    },
    {
      key: 'lmc',
      tool: 'lmc_anp',
      label: 'Conformidade LMC',
      hint: 'Toque para auditar o LMC frente à tolerância da ANP.',
      prompt: 'O LMC está dentro da tolerância oficial de 0,6% da ANP?',
      chip: false,
      evaluate: evaluateLmc,
      icon: '<svg class="w-3.5 h-3.5 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true"><path d="M12 2L20.5 7.2V16.8L12 22L3.5 16.8V7.2L12 2Z" stroke-width="1.75" stroke-linejoin="round"/><polyline points="8.5 12 11 14.5 15.5 9.5" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    },
  ];

  /**
   * Markup do cockpit em estado de carregamento (skeleton). Fonte unica usada por
   * aura-chat.js (addWelcomeMessage) e espelhada literalmente em web/index.html.
   */
  function shellHtml() {
    const cards = INDICATORS.map((def) => (
      '<button type="button" class="welcome-indicator" data-indicator="' + def.key + '" data-state="loading"'
      + ' onclick="window.auraChat.sendUserPrompt(\'' + def.prompt + '\')"'
      + ' aria-label="' + def.label + ': carregando. ' + def.hint + '">'
      + '<span class="welcome-indicator-label"><span class="welcome-indicator-dot" aria-hidden="true"></span>'
      + def.icon + '<span>' + def.label + '</span></span>'
      + '<span class="welcome-indicator-skeleton" aria-hidden="true">'
      + '<span class="skeleton-shimmer welcome-skel-value"></span><span class="skeleton-shimmer welcome-skel-detail"></span></span>'
      + '<span class="welcome-indicator-body"><span class="welcome-indicator-value" data-role="value"></span>'
      + '<span class="welcome-indicator-detail" data-role="detail"></span></span>'
      + '</button>'
    )).join('');

    return '<section id="welcome-readiness-cockpit" class="welcome-cockpit" role="region"'
      + ' aria-label="Cockpit de prontidão do posto" aria-busy="true" aria-live="polite">'
      + '<div class="welcome-cockpit-header"><h2 class="welcome-cockpit-title">Prontidão do posto agora</h2>'
      + '<button type="button" id="welcome-cockpit-refresh" class="welcome-cockpit-refresh"'
      + ' aria-label="Atualizar indicadores do posto"'
      + ' onclick="window.auraWelcomeCockpit &amp;&amp; window.auraWelcomeCockpit.refresh({ force: true })">'
      + '<svg class="w-3.5 h-3.5 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">'
      + '<path d="M21 12a9 9 0 1 1-2.64-6.36" stroke-width="1.75" stroke-linecap="round"/>'
      + '<polyline points="21 3 21 9 15 9" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/></svg>'
      + '<span>Atualizar</span></button></div>'
      + '<div class="welcome-cockpit-grid">' + cards + '</div>'
      + '<p class="welcome-cockpit-meta" data-role="meta">Lendo dados do posto...</p>'
      + '</section>';
  }

  function withTimeout(promise, ms) {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('timeout')), ms);
      Promise.resolve(promise).then(
        (v) => { clearTimeout(timer); resolve(v); },
        (e) => { clearTimeout(timer); reject(e); }
      );
    });
  }

  class AuraWelcomeCockpit {
    constructor() {
      this.cache = null;
      this.seq = 0;
      this.initialized = false;
    }

    getRoot() {
      if (typeof document === 'undefined') return null;
      const el = document.getElementById('welcome-readiness-cockpit');
      return el && el.isConnected ? el : null;
    }

    schedule(fn) {
      if (typeof root.requestIdleCallback === 'function') {
        root.requestIdleCallback(fn, { timeout: 1500 });
      } else {
        setTimeout(fn, 250);
      }
    }

    init() {
      if (this.initialized) return;
      this.initialized = true;
      this.schedule(() => this.refresh());
    }

    /** Chamado apos o card ser recriado dinamicamente (Nova Conversa). */
    mount() {
      this.schedule(() => this.refresh());
    }

    /** Invalida leituras em andamento ao iniciar a conversa sem remover o cockpit da historia do chat. */
    dismiss() {
      this.seq += 1;
    }

    setState(el, result) {
      el.dataset.state = result.state;
      const valueEl = el.querySelector('[data-role="value"]');
      const detailEl = el.querySelector('[data-role="detail"]');
      if (valueEl) valueEl.textContent = result.value;
      if (detailEl) detailEl.textContent = result.detail || '';
      const def = INDICATORS.find((i) => i.key === el.dataset.indicator);
      if (def) {
        const summary = result.value + (result.detail ? '. ' + result.detail : '');
        el.setAttribute('aria-label', def.label + ': ' + summary + '. ' + def.hint);
        if (def.chip) {
          document.querySelectorAll('[data-welcome-chip="' + def.key + '"]').forEach((chip) => {
            chip.classList.toggle('is-attention', result.state === 'alert' || result.state === 'attention');
          });
        }
      }
    }

    renderIndicator(key, result) {
      const rootEl = this.getRoot();
      if (!rootEl) return;
      const el = rootEl.querySelector('[data-indicator="' + key + '"]');
      if (el) this.setState(el, result);
    }

    setLoading(rootEl) {
      rootEl.setAttribute('aria-busy', 'true');
      rootEl.querySelectorAll('[data-indicator]').forEach((el) => { el.dataset.state = 'loading'; });
      const meta = rootEl.querySelector('[data-role="meta"]');
      if (meta) meta.textContent = 'Lendo dados do posto...';
    }

    finish(rootEl, results, ts) {
      rootEl.setAttribute('aria-busy', 'false');
      const meta = rootEl.querySelector('[data-role="meta"]');
      if (!meta) return;
      const anyData = results.some((r) => r && r.state !== 'neutral');
      if (anyData) {
        const hhmm = new Date(ts).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
        meta.textContent = 'Atualizado às ' + hhmm + ' (leitura somente leitura do sistema do posto)';
      } else {
        meta.textContent = 'Sem dados no momento. Toque em Atualizar para tentar novamente.';
      }
    }

    async refresh(options) {
      const force = !!(options && options.force);
      const rootEl = this.getRoot();
      if (!rootEl) return;

      if (!force && this.cache && (Date.now() - this.cache.ts) < CACHE_TTL_MS) {
        INDICATORS.forEach((def, i) => this.renderIndicator(def.key, this.cache.results[i]));
        this.finish(rootEl, this.cache.results, this.cache.ts);
        return;
      }

      this.seq += 1;
      const seq = this.seq;
      this.setLoading(rootEl);

      const api = root.auraApi;
      const jobs = INDICATORS.map(async (def) => {
        let res = null;
        if (api && typeof api.executeIntent === 'function') {
          try {
            res = await withTimeout(api.executeIntent(def.tool), REQUEST_TIMEOUT_MS);
          } catch (_) {
            res = null;
          }
        }
        const result = def.evaluate(res);
        if (seq === this.seq) this.renderIndicator(def.key, result);
        return result;
      });

      const results = await Promise.all(jobs);
      if (seq !== this.seq) return;
      const ts = Date.now();
      if (results.some((r) => r.state !== 'neutral')) {
        this.cache = { ts: ts, results: results };
      }
      const current = this.getRoot();
      if (current) this.finish(current, results, ts);
    }
  }

  const api = {
    AuraWelcomeCockpit: AuraWelcomeCockpit,
    evaluateTanques: evaluateTanques,
    evaluateTurno: evaluateTurno,
    evaluateLmc: evaluateLmc,
    shellHtml: shellHtml,
    INDICATORS: INDICATORS,
  };

  if (typeof window !== 'undefined') {
    window.AuraWelcomeCockpit = api;
    window.auraWelcomeCockpit = new AuraWelcomeCockpit();
    const start = () => window.auraWelcomeCockpit.init();
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', start);
    } else {
      start();
    }
  }

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }
})(typeof window !== 'undefined' ? window : globalThis);
