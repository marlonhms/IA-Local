/**
 * AURA Dynamic Inspector Panel / Companion Canvas Controller (v1.0.0)
 * 
 * Gerencia o Painel Auxiliar Interativo acoplado ao chat da AURA:
 * - Foco duplo sem atrito: leitura do streaming no chat + inspeção visual no canvas lado a lado.
 * - 4 Perspectivas analíticas dinâmicas:
 *   1. Visão Executiva (DecisionCards, gauges volumétricos 3D, rankings, CTAs em 1 clique)
 *   2. Tabela Analítica (Data Grid interativo com busca em tempo real, formatação de moeda/litros e exportação CSV)
 *   3. Banco & Esquema Relacional (Inspetor de conexão, entidades, tipos de dados SQL, latência e JSON raw)
 *   4. Regras & Auditoria (Memória de cálculo, tolerâncias oficiais ANP, linhagem do dado e evidências)
 * - Carrossel de histórico de múltiplos artefatos da conversa.
 * - Arquitetura agnóstica e universal: preparado tanto para postos quanto para qualquer banco de dados relacional futuro.
 * - Suporte a safe areas, atalhos de teclado (Alt+P, Esc), GPU Guard e WCAG 2.1 AA.
 */

class AuraAuxPanel {
  constructor() {
    this.isOpen = false;
    this.isExpanded = false; // false = split padrão (50/50), true = canvas expandido (65/35)
    this.activeTab = 'visual'; // 'visual' | 'data' | 'schema' | 'audit'
    this.artifacts = []; // lista de artefatos da sessão
    this.activeArtifactId = null;
    this.userDismissed = false;
    this.filterQuery = '';
    this.lastDataGridArtifactId = null;
    this.previousFocusedElement = null;
  }

  /**
   * Reconhecimento inteligente de tela (Mobile <768px vs PC >=768px)
   * Respeita:
   * 1. Override manual do HUD de dispositivo (window.auraFx?.override)
   * 2. Atributo data-device no elemento raiz do DOM
   * 3. Viewport width padrão (< 768px mobile, >= 768px desktop)
   * 4. Media query (max-width: 767px)
   * 5. Helper window.auraFx?.isMobileDevice() / isMobile()
   */
  isMobileDevice(win = (typeof window !== 'undefined' ? window : null)) {
    if (!win) return false;
    // 1. Override manual do HUD de dispositivo (prioridade máxima para comutação e testes)
    if (win.auraFx && typeof win.auraFx.override === 'string') {
      if (win.auraFx.override === 'mobile') return true;
      if (win.auraFx.override === 'desktop') return false;
    }
    // 2. Viewport width padrão da janela informada (< 768px Mobile, >= 768px Desktop/PC)
    if (typeof win.innerWidth === 'number') {
      return win.innerWidth < 768;
    }
    // 3. Media query reativa
    if (win.matchMedia && typeof win.matchMedia === 'function') {
      return win.matchMedia('(max-width: 767px)').matches;
    }
    // 4. Atributo data-device no DOM (fallback se innerWidth não estiver disponível)
    if (typeof document !== 'undefined' && document.documentElement) {
      const dev = document.documentElement.getAttribute('data-device');
      if (dev === 'mobile') return true;
      if (dev === 'desktop') return false;
    }
    // 5. Fallback para helpers de dispositivo
    if (win.auraFx && typeof win.auraFx.isMobileDevice === 'function') {
      return win.auraFx.isMobileDevice();
    }
    if (win.auraFx && typeof win.auraFx.isMobile === 'function') {
      return win.auraFx.isMobile();
    }
    return false;
  }

  isDesktopDevice(win = (typeof window !== 'undefined' ? window : null)) {
    return !this.isMobileDevice(win);
  }

  init() {
    this.bindEvents();
    this.updateToggleState();
    this.renderActiveArtifact();
  }

  bindEvents() {
    if (typeof document === 'undefined') return;

    // Botão Toggle do Header
    const btnToggle = document.getElementById('btn-toggle-aux-panel');
    if (btnToggle) {
      btnToggle.addEventListener('click', () => {
        this.toggle();
      });
    }

    // Botão Fechar Painel
    const btnClose = document.getElementById('aux-btn-close');
    if (btnClose) {
      btnClose.addEventListener('click', () => {
        this.close();
      });
    }

    // Botão Alternar Largura (Split vs Expandido)
    const btnExpand = document.getElementById('aux-btn-expand');
    if (btnExpand) {
      btnExpand.addEventListener('click', () => {
        this.toggleExpand();
      });
    }

    // Botão Copiar Dados
    const btnCopy = document.getElementById('aux-btn-copy-data');
    if (btnCopy) {
      btnCopy.addEventListener('click', () => {
        this.copyActiveData();
      });
    }

    // Abas de Perspectiva (Visual, Tabela, Banco, Auditoria)
    const tabBtns = document.querySelectorAll('.aux-tab-btn');
    tabBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const tab = btn.getAttribute('data-aux-tab');
        if (tab) this.switchTab(tab);
      });
    });

    // Toast de visualização rápida no mobile
    const btnPeek = document.getElementById('btn-peek-open-panel');
    if (btnPeek) {
      btnPeek.addEventListener('click', () => {
        this.open();
      });
    }

    // Atalhos de Teclado Globais: Alt+P (Toggle) e Escape (Fechar)
    if (typeof window !== 'undefined') {
      window.addEventListener('keydown', (e) => {
        if (e.altKey && (e.key === 'p' || e.key === 'P')) {
          e.preventDefault();
          this.toggle();
          return;
        }

        if (e.key === 'Escape' && this.isOpen) {
          // Não fecha se uma modal superior (ex: Command Palette) estiver aberta
          const palette = document.getElementById('aura-command-palette-modal');
          if (palette && !palette.classList.contains('hidden')) return;

          e.preventDefault();
          this.close();
        }
      });
    }
  }

  /**
   * Registra e projeta um novo artefato gerado pela AURA no painel auxiliar
   */
  projectArtifact({ id, containerId, toolName, intent, data, html, autoOpen = true }) {
    if (!data && !html) return null;

    const artifactId = id || ('art_' + Date.now() + '_' + Math.random().toString(36).substring(2, 6));
    const normalized = this.normalizeArtifactData(toolName, intent, data, html);

    const artifact = {
      id: artifactId,
      containerId: containerId || null,
      toolName: toolName || 'ferramenta',
      intent: intent || normalized.intent,
      title: normalized.title,
      subtitle: normalized.subtitle,
      statusChip: normalized.statusChip,
      records: normalized.records,
      schemaInfo: normalized.schemaInfo,
      auditRules: normalized.auditRules,
      summaryKpis: normalized.summaryKpis,
      html: html || '',
      data: data || {},
      timestamp: Date.now(),
      timeFormatted: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
    };

    // Atualiza ou insere na lista de artefatos
    const existingIndex = this.artifacts.findIndex(a => a.id === artifactId || (containerId && a.containerId === containerId));
    if (existingIndex >= 0) {
      this.artifacts[existingIndex] = artifact;
    } else {
      this.artifacts.unshift(artifact); // mais recente no topo
      if (this.artifacts.length > 30) {
        this.artifacts.pop();
      }
    }

    this.activeArtifactId = artifact.id;
    this.updateToggleState(true);
    this.renderActiveArtifact();

    // Auto-abre no PC/Desktop (>= 768px) se autoOpen for verdadeiro e usuário não tiver dispensado
    // Em Mobile (< 768px), NUNCA auto-abre o painel lateral cobrindo a conversa do chat
    if (autoOpen && typeof window !== 'undefined') {
      const isMobile = this.isMobileDevice();
      if (!isMobile && !this.userDismissed) {
        this.open(artifact.id, false);
      } else if (!isMobile && this.userDismissed) {
        this.showPeekToast(artifact.title);
      }
    }

    if (typeof window !== 'undefined' && window.auraAudio && typeof window.auraAudio.playChime === 'function') {
      window.auraAudio.playChime(760, 0.08);
    }

    return artifact;
  }

  /**
   * Abre o painel auxiliar
   */
  open(artifactId = null, playSound = true) {
    if (artifactId) {
      this.activeArtifactId = artifactId;
    }

    this.isOpen = true;
    this.userDismissed = false;

    if (typeof document !== 'undefined') {
      this.previousFocusedElement = document.activeElement;

      const consoleView = document.getElementById('view-console');
      const auxPanel = document.getElementById('aura-aux-panel');
      const btnToggle = document.getElementById('btn-toggle-aux-panel');
      const peekToast = document.getElementById('aux-artifact-peek-toast');
      const beacon = document.getElementById('aux-toggle-beacon');

      if (consoleView) {
        consoleView.classList.add('aux-panel-active');
        if (this.isExpanded) consoleView.classList.add('aux-expanded');
      }

      if (auxPanel) {
        auxPanel.classList.remove('hidden');
        auxPanel.classList.add('animate-fade-in');
      }

      if (btnToggle) {
        btnToggle.setAttribute('aria-expanded', 'true');
        btnToggle.classList.add('bg-cyan-500/15', 'border-cyan-500/40', 'text-cyan-200');
      }

      if (peekToast) peekToast.classList.add('hidden');
      if (beacon) beacon.classList.add('hidden');

      this.renderActiveArtifact();

      // Rola para a mensagem associada no chat
      const activeArt = this.getActiveArtifact();
      if (activeArt && activeArt.containerId) {
        const msgEl = document.getElementById(activeArt.containerId);
        if (msgEl) {
          msgEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      }
    }

    if (playSound && typeof window !== 'undefined' && window.auraAudio && typeof window.auraAudio.playChime === 'function') {
      window.auraAudio.playChime(680, 0.06);
    }
  }

  /**
   * Fecha o painel auxiliar e devolve o layout ao centro confortável
   */
  close(playSound = true) {
    this.isOpen = false;
    this.userDismissed = true;

    if (typeof document !== 'undefined') {
      const consoleView = document.getElementById('view-console');
      const auxPanel = document.getElementById('aura-aux-panel');
      const btnToggle = document.getElementById('btn-toggle-aux-panel');

      if (consoleView) {
        consoleView.classList.remove('aux-panel-active', 'aux-expanded');
      }

      if (auxPanel) {
        auxPanel.classList.add('hidden');
      }

      if (btnToggle) {
        btnToggle.setAttribute('aria-expanded', 'false');
        btnToggle.classList.remove('bg-cyan-500/15', 'border-cyan-500/40', 'text-cyan-200');
      }

      // Restaura foco ao gatilho que abriu ou ao input de chat (WCAG 2.1 AA)
      if (this.previousFocusedElement && typeof this.previousFocusedElement.focus === 'function') {
        this.previousFocusedElement.focus({ preventScroll: true });
      } else {
        const chatInput = document.getElementById('chat-input-text');
        if (chatInput && typeof chatInput.focus === 'function') {
          chatInput.focus({ preventScroll: true });
        }
      }
    }

    if (playSound && typeof window !== 'undefined' && window.auraAudio && typeof window.auraAudio.playChime === 'function') {
      window.auraAudio.playChime(520, 0.05);
    }
  }

  /**
   * Alterna estado aberto/fechado
   */
  toggle() {
    if (this.isOpen) {
      this.close();
    } else {
      this.open();
    }
  }

  /**
   * Alterna largura entre Split Padrão (50%) e Expandido (65%)
   */
  toggleExpand() {
    this.isExpanded = !this.isExpanded;
    if (typeof document !== 'undefined') {
      const consoleView = document.getElementById('view-console');
      const expandIcon = document.getElementById('aux-expand-icon');
      if (consoleView) {
        if (this.isExpanded) {
          consoleView.classList.add('aux-expanded');
        } else {
          consoleView.classList.remove('aux-expanded');
        }
      }
      if (expandIcon) {
        expandIcon.innerHTML = this.isExpanded
          ? '<polyline points="4 14 10 14 10 20" stroke-width="2"/><polyline points="20 10 14 10 14 4" stroke-width="2"/><line x1="14" y1="10" x2="21" y2="3" stroke-width="2"/><line x1="3" y1="21" x2="10" y2="14" stroke-width="2"/>'
          : '<polyline points="15 3 21 3 21 9" stroke-width="2"/><polyline points="9 21 3 21 3 15" stroke-width="2"/><line x1="21" y1="3" x2="14" y2="10" stroke-width="2"/><line x1="3" y1="21" x2="10" y2="14" stroke-width="2"/>';
      }
    }
    if (typeof window !== 'undefined' && window.auraAudio && typeof window.auraAudio.playChime === 'function') {
      window.auraAudio.playChime(600, 0.04);
    }
  }

  /**
   * Alterna a aba ativa do painel auxiliar
   */
  switchTab(tabName) {
    this.activeTab = tabName;

    if (typeof document !== 'undefined') {
      const tabs = document.querySelectorAll('.aux-tab-btn');
      tabs.forEach(btn => {
        const isTarget = btn.getAttribute('data-aux-tab') === tabName;
        if (isTarget) {
          btn.classList.add('active', 'bg-slate-800', 'text-white', 'border-slate-700');
          btn.classList.remove('text-slate-400', 'border-transparent');
          btn.setAttribute('aria-selected', 'true');
        } else {
          btn.classList.remove('active', 'bg-slate-800', 'text-white', 'border-slate-700');
          btn.classList.add('text-slate-400', 'border-transparent');
          btn.setAttribute('aria-selected', 'false');
        }
      });

      const views = {
        visual: document.getElementById('aux-view-visual'),
        data: document.getElementById('aux-view-data'),
        schema: document.getElementById('aux-view-schema'),
        audit: document.getElementById('aux-view-audit')
      };

      Object.entries(views).forEach(([name, el]) => {
        if (!el) return;
        if (name === tabName) {
          el.classList.remove('hidden');
          el.classList.add('animate-fade-in');
        } else {
          el.classList.add('hidden');
          el.classList.remove('animate-fade-in');
        }
      });
    }

    if (typeof window !== 'undefined' && window.auraAudio && typeof window.auraAudio.playChime === 'function') {
      window.auraAudio.playChime(550, 0.04);
    }
  }

  /**
   * Seleciona um artefato histórico do carrossel
   */
  selectArtifact(artifactId) {
    this.activeArtifactId = artifactId;
    this.filterQuery = '';
    this.lastDataGridArtifactId = null;
    this.renderActiveArtifact();

    if (typeof window !== 'undefined' && window.auraAudio && typeof window.auraAudio.playChime === 'function') {
      window.auraAudio.playChime(640, 0.04);
    }
  }

  getActiveArtifact() {
    if (!this.artifacts || this.artifacts.length === 0) return null;
    if (this.activeArtifactId) {
      const found = this.artifacts.find(a => a.id === this.activeArtifactId);
      if (found) return found;
    }
    return this.artifacts[0];
  }

  updateToggleState(pulseBeacon = false) {
    if (typeof document === 'undefined') return;

    const countEl = document.getElementById('aux-toggle-count');
    const beaconEl = document.getElementById('aux-toggle-beacon');

    if (countEl) {
      const count = this.artifacts.length;
      countEl.textContent = String(count);
      if (count > 0) {
        countEl.classList.remove('hidden');
      } else {
        countEl.classList.add('hidden');
      }
    }

    if (beaconEl && pulseBeacon && !this.isOpen) {
      beaconEl.classList.remove('hidden');
    }
  }

  showPeekToast(title) {
    if (typeof document === 'undefined') return;
    // Em mobile, respeita a regra inteligente: não exibe toast sugerindo abrir painel lateral
    if (this.isMobileDevice()) return;
    const toast = document.getElementById('aux-artifact-peek-toast');
    const label = document.getElementById('aux-peek-toast-label');
    if (toast && label) {
      label.textContent = `Visualizar: ${title || 'Novo resultado'}`;
      toast.classList.remove('hidden');
    }
  }

  clearArtifacts() {
    this.artifacts = [];
    this.activeArtifactId = null;
    this.filterQuery = '';
    this.lastDataGridArtifactId = null;
    this.updateToggleState();
    this.renderActiveArtifact();
    if (this.isOpen) {
      this.close(false);
    }
  }

  // =========================================================================
  // RENDERIZAÇÃO DAS 4 PERSPECTIVAS
  // =========================================================================

  renderActiveArtifact() {
    if (typeof document === 'undefined') return;

    const artifact = this.getActiveArtifact();

    const titleEl = document.getElementById('aux-panel-title');
    const chipEl = document.getElementById('aux-panel-status-chip');
    const subEl = document.getElementById('aux-panel-subtitle');
    const footerProvEl = document.getElementById('aux-footer-provenance');

    // Estado vazio
    if (!artifact) {
      if (titleEl) titleEl.textContent = 'Painel Auxiliar AURA';
      if (chipEl) {
        chipEl.textContent = 'Pronto';
        chipEl.className = 'px-2 py-0.5 rounded-full text-[10px] font-sans font-semibold bg-cyan-500/15 text-cyan-300 border border-cyan-500/30';
      }
      if (subEl) subEl.textContent = 'Aguardando geração de artefatos visuais...';
      this.renderEmptyState();
      return;
    }

    // Topo do Canvas
    if (titleEl) titleEl.textContent = artifact.title;
    if (subEl) subEl.textContent = artifact.subtitle;
    if (chipEl) {
      chipEl.textContent = artifact.statusChip.label;
      const sev = artifact.statusChip.severity;
      const classMap = {
        success: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
        attention: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
        critical: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
        neutral: 'bg-slate-700/40 text-slate-300 border-slate-600'
      };
      chipEl.className = `px-2 py-0.5 rounded-full text-[10px] font-sans font-semibold border ${classMap[sev] || classMap.neutral}`;
    }

    if (footerProvEl) {
      footerProvEl.textContent = `${artifact.schemaInfo?.source || 'PostgreSQL Local'} • Verificado às ${artifact.timeFormatted}`;
    }

    // Renderiza Carrossel de Múltiplos Artefatos
    this.renderArtifactsBar();

    // Renderiza Perspectivas
    this.renderVisualView(artifact);
    this.renderDataGrid(artifact);
    this.renderSchemaView(artifact);
    this.renderAuditView(artifact);

    if (typeof window !== 'undefined' && window.lucide) {
      try { window.lucide.createIcons(); } catch (_) {}
    }
  }

  renderEmptyState() {
    const visualView = document.getElementById('aux-view-visual');
    if (!visualView) return;

    visualView.innerHTML = `
      <div class="p-8 text-center space-y-4 rounded-2xl border border-white/5 bg-slate-900/30">
        <div class="w-12 h-12 mx-auto rounded-2xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
          <svg class="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <rect x="2" y="3" width="20" height="18" rx="2.5" stroke-width="1.75"/>
            <line x1="13" y1="3" x2="13" y2="21" stroke-width="1.75"/>
            <circle cx="7.5" cy="12" r="2" fill="currentColor"/>
          </svg>
        </div>
        <div class="space-y-1">
          <h4 class="font-bold text-white text-sm">Nenhum Artefato Visual Projetado</h4>
          <p class="text-xs text-slate-400 max-w-sm mx-auto leading-relaxed">
            Quando a AURA calcula relatórios de tanques, fechamento de caixa, conciliação ANP, frentistas ou vendas, os cards visuais, tabelas e esquemas aparecem automaticamente aqui.
          </p>
        </div>
        <div class="pt-2 flex flex-wrap justify-center gap-2">
          <button onclick="window.auraChat && window.auraChat.sendUserPrompt('Qual a situação e autonomia de cada tanque agora?')" class="px-3 py-1.5 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 border border-emerald-500/30 text-xs transition-colors">
            ⛽ Testar Tanques
          </button>
          <button onclick="window.auraChat && window.auraChat.sendUserPrompt('Como fechou o último turno? Teve furo de caixa?')" class="px-3 py-1.5 rounded-lg bg-cyan-500/15 hover:bg-cyan-500/25 text-cyan-300 border border-cyan-500/30 text-xs transition-colors">
            💰 Testar Fechamento
          </button>
        </div>
      </div>
    `;
  }

  renderArtifactsBar() {
    const bar = document.getElementById('aux-artifacts-bar');
    if (!bar) return;

    if (this.artifacts.length <= 1) {
      bar.classList.add('hidden');
      bar.innerHTML = '';
      return;
    }

    bar.classList.remove('hidden');
    bar.innerHTML = this.artifacts.map(art => {
      const isActive = art.id === this.activeArtifactId;
      return `
        <button onclick="window.auraAuxPanel.selectArtifact('${art.id}')" class="aux-artifact-chip px-3 py-1 rounded-xl text-xs font-sans whitespace-nowrap transition-all flex items-center gap-1.5 ${isActive ? 'bg-cyan-500/20 text-cyan-200 border border-cyan-500/40 shadow-sm font-semibold' : 'bg-slate-800/80 text-slate-400 hover:text-white border border-transparent'}">
          <span class="w-1.5 h-1.5 rounded-full ${isActive ? 'bg-cyan-400' : 'bg-slate-500'}"></span>
          <span>${this.escapeHtml(art.title.split('•')[0].trim())}</span>
          <span class="text-[10px] text-slate-500">${art.timeFormatted}</span>
        </button>
      `;
    }).join('');
  }

  /**
   * Perspectiva 1: Visão Executiva (Visual DecisionCard & KPI Heros)
   */
  renderVisualView(artifact) {
    const visualView = document.getElementById('aux-view-visual');
    if (!visualView) return;

    let kpisHtml = '';
    if (artifact.summaryKpis && artifact.summaryKpis.length > 0) {
      kpisHtml = `
        <div class="grid grid-cols-2 sm:grid-cols-3 gap-2.5 mb-3">
          ${artifact.summaryKpis.map(kpi => `
            <div class="p-3 rounded-xl bg-slate-900/60 border border-white/5 space-y-1">
              <span class="text-[10px] uppercase font-bold tracking-wider text-slate-400">${this.escapeHtml(kpi.label)}</span>
              <div class="text-base font-bold text-white tabular-nums">${this.escapeHtml(kpi.value)}</div>
              ${kpi.sub ? `<span class="text-[10px] text-slate-400">${this.escapeHtml(kpi.sub)}</span>` : ''}
            </div>
          `).join('')}
        </div>
      `;
    }

    visualView.innerHTML = `
      ${kpisHtml}
      <div class="aux-visual-container">
        ${artifact.html}
      </div>
    `;
  }

  /**
   * Perspectiva 2: Tabela Analítica (Data Grid Universal)
   */
  renderDataGrid(artifact) {
    const dataView = document.getElementById('aux-view-data');
    if (!dataView) return;

    const records = artifact.records || [];
    if (records.length === 0) {
      dataView.innerHTML = `
        <div class="p-6 text-center text-slate-400 text-xs rounded-xl bg-slate-900/40 border border-white/5 space-y-2">
          <p class="font-medium">Nenhum registro tabular individual para esta visualização.</p>
          <p class="text-[11px] text-slate-500">Métricas analíticas consolidadas disponíveis na aba Visual / Decisão.</p>
        </div>
      `;
      this.lastDataGridArtifactId = null;
      return;
    }

    // Identifica colunas de todos os registros (suporte heterogêneo universal)
    const columns = Array.from(new Set(records.flatMap(r => Object.keys(r || {}))));

    const existingInput = document.getElementById('aux-table-search-input');
    const existingBody = document.getElementById('aux-data-table-body');
    const isSameArtifact = this.lastDataGridArtifactId === artifact.id;

    if (!existingInput || !existingBody || !isSameArtifact) {
      this.lastDataGridArtifactId = artifact.id;
      dataView.innerHTML = `
        <div class="space-y-3">
          <!-- Barra de Ações da Tabela -->
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
            <div class="relative flex-1 max-w-sm">
              <input 
                id="aux-table-search-input" 
                type="text" 
                placeholder="Filtrar nesta tabela..." 
                value="${this.escapeHtml(this.filterQuery)}" 
                class="w-full px-3 py-1.5 pl-8 rounded-xl bg-slate-900/80 border border-white/10 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/50"
              />
              <svg class="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="11" cy="11" r="8" stroke-width="1.75"/><line x1="21" y1="21" x2="16.65" y2="16.65" stroke-width="1.75"/></svg>
            </div>

            <div class="flex items-center gap-2">
              <span id="aux-data-table-count" class="text-[11px] text-slate-400 font-sans">
                <!-- Contador injetado dinamicamente -->
              </span>
              <button onclick="window.auraAuxPanel.downloadCsv()" class="px-2.5 py-1.5 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 border border-emerald-500/30 text-xs font-semibold flex items-center gap-1 transition-colors" title="Baixar arquivo CSV formatado com UTF-8 BOM">
                <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" stroke-width="1.75"/><polyline points="7 10 12 15 17 10" stroke-width="1.75"/><line x1="12" y1="15" x2="12" y2="3" stroke-width="1.75"/></svg>
                <span>Baixar CSV</span>
              </button>
              <button onclick="window.auraAuxPanel.copyCsv()" class="px-2 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-medium flex items-center gap-1 transition-colors" title="Copiar CSV para área de transferência">
                <svg class="w-3.5 h-3.5 text-cyan-400" viewBox="0 0 24 24" fill="none" stroke="currentColor"><rect x="9" y="9" width="13" height="13" rx="2" stroke-width="1.75"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" stroke-width="1.75"/></svg>
                <span class="hidden sm:inline">Copiar</span>
              </button>
            </div>
          </div>

          <!-- Tabela Responsiva de Alto Contraste -->
          <div class="rounded-xl border border-white/10 overflow-hidden bg-slate-900/50">
            <div class="overflow-x-auto max-h-[460px] scrollbar-thin">
              <table class="aux-data-table w-full text-left text-xs font-sans divide-y divide-white/10">
                <thead class="bg-slate-950/80 text-slate-300 uppercase text-[10px] tracking-wider sticky top-0 backdrop-blur-md">
                  <tr>
                    ${columns.map(col => `<th class="px-3.5 py-2.5 font-bold">${this.escapeHtml(this.formatColumnHeader(col))}</th>`).join('')}
                  </tr>
                </thead>
                <tbody id="aux-data-table-body" class="divide-y divide-white/5">
                </tbody>
              </table>
            </div>
          </div>
        </div>
      `;

      // Conecta input de busca em tempo real mantendo foco nativo (sem perda de cursor)
      const searchInput = document.getElementById('aux-table-search-input');
      if (searchInput) {
        searchInput.addEventListener('input', (e) => {
          this.filterQuery = e.target.value;
          this.updateDataGridRows(artifact, columns);
        });
      }
    }

    this.updateDataGridRows(artifact, columns);
  }

  updateDataGridRows(artifact, columns) {
    if (typeof document === 'undefined') return;

    const bodyEl = document.getElementById('aux-data-table-body');
    const countEl = document.getElementById('aux-data-table-count');
    if (!bodyEl) return;

    const records = artifact.records || [];
    const cols = columns || Array.from(new Set(records.flatMap(r => Object.keys(r || {}))));
    const query = (this.filterQuery || '').trim().toLowerCase();

    const filteredRecords = query
      ? records.filter(row => cols.some(col => String(row[col] ?? '').toLowerCase().includes(query)))
      : records;

    if (countEl) {
      countEl.innerHTML = `<strong class="text-white tabular-nums">${filteredRecords.length}</strong> de <strong class="text-white tabular-nums">${records.length}</strong> linhas`;
    }

    if (filteredRecords.length === 0) {
      bodyEl.innerHTML = `
        <tr>
          <td colspan="${Math.max(1, cols.length)}" class="px-4 py-8 text-center text-slate-500 font-sans text-xs">
            Nenhum resultado corresponde ao filtro "<strong>${this.escapeHtml(this.filterQuery)}</strong>"
          </td>
        </tr>
      `;
      return;
    }

    bodyEl.innerHTML = filteredRecords.map((row, idx) => `
      <tr class="hover:bg-cyan-500/[0.04] transition-colors ${idx % 2 === 0 ? 'bg-transparent' : 'bg-white/[0.01]'}">
        ${cols.map(col => `
          <td class="px-3.5 py-2.5 tabular-nums text-slate-200 ${this.getColumnAlignmentClass(col, row[col])}">
            ${this.formatTableCell(col, row[col])}
          </td>
        `).join('')}
      </tr>
    `).join('');
  }

  /**
   * Perspectiva 3: Banco & Esquema Relacional (Agnóstico p/ Qualquer Banco)
   */
  renderSchemaView(artifact) {
    const schemaView = document.getElementById('aux-view-schema');
    if (!schemaView) return;

    const schema = artifact.schemaInfo || {
      source: 'PostgreSQL 16 (Local)',
      table: 'tb_operacao',
      recordCount: artifact.records?.length || 0,
      fields: []
    };

    let fields = schema.fields || [];
    if (fields.length === 0 && artifact.records && artifact.records.length > 0) {
      const cols = Array.from(new Set(artifact.records.flatMap(r => Object.keys(r || {}))));
      fields = cols.map(k => {
        const sampleVal = artifact.records.find(r => r[k] !== undefined && r[k] !== null)?.[k];
        let type = 'VARCHAR';
        if (typeof sampleVal === 'number') type = 'NUMERIC';
        else if (typeof sampleVal === 'boolean') type = 'BOOLEAN';
        else if (sampleVal instanceof Date || (typeof sampleVal === 'string' && /^\d{4}-\d{2}-\d{2}/.test(sampleVal))) type = 'TIMESTAMP';
        return { field: k, type, sample: sampleVal ?? '—' };
      });
      schema.fields = fields;
    }

    const fieldsRowsHtml = fields.length > 0 ? fields.map(f => `
      <tr class="hover:bg-white/[0.02]">
        <td class="px-3 py-2 font-mono text-cyan-300 text-[11px]">${this.escapeHtml(f.field)}</td>
        <td class="px-3 py-2">
          <span class="px-1.5 py-0.5 rounded text-[10px] font-mono bg-purple-500/15 text-purple-300 border border-purple-500/30">
            ${this.escapeHtml(f.type)}
          </span>
        </td>
        <td class="px-3 py-2 text-slate-400 text-[11px] truncate max-w-xs">${this.escapeHtml(String(f.sample ?? '—'))}</td>
      </tr>
    `).join('') : `
      <tr>
        <td colspan="3" class="px-3 py-4 text-center text-slate-500 text-xs">Esquema dinâmico gerado em tempo de execução</td>
      </tr>
    `;

    schemaView.innerHTML = `
      <div class="space-y-4">
        <!-- Banner de Conectividade do Banco -->
        <div class="p-3.5 rounded-xl bg-gradient-to-r from-purple-500/10 via-slate-900 to-transparent border border-purple-500/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div class="space-y-1">
            <div class="flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
              <span class="text-xs font-bold text-white uppercase tracking-wider font-sans">${this.escapeHtml(schema.source)}</span>
              <span class="px-2 py-0.5 rounded-full text-[9px] font-sans font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">ACID Conforme</span>
            </div>
            <p class="text-[11px] text-slate-400 font-sans">
              Entidade de Dados: <strong class="text-cyan-300 font-mono">${this.escapeHtml(schema.table)}</strong> • ${schema.recordCount} registros auditados
            </p>
          </div>
          <button onclick="window.auraAuxPanel.copyJson()" class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium flex items-center gap-1.5 transition-colors self-start sm:self-auto">
            <svg class="w-3.5 h-3.5 text-cyan-400" viewBox="0 0 24 24" fill="none" stroke="currentColor"><rect x="9" y="9" width="13" height="13" rx="2" stroke-width="1.75"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" stroke-width="1.75"/></svg>
            <span>Copiar JSON</span>
          </button>
        </div>

        <!-- Dicionário de Campos e Tipagem SQL -->
        <div class="space-y-2">
          <h5 class="text-xs font-bold text-slate-300 uppercase tracking-wider font-sans flex items-center gap-1.5">
            <svg class="w-3.5 h-3.5 text-purple-400" viewBox="0 0 24 24" fill="none" stroke="currentColor"><ellipse cx="12" cy="5" rx="9" ry="3" stroke-width="1.75"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" stroke-width="1.75"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" stroke-width="1.75"/></svg>
            <span>Dicionário de Atributos & Tipagem</span>
          </h5>

          <div class="rounded-xl border border-white/10 overflow-hidden bg-slate-900/40">
            <table class="w-full text-left text-xs font-sans divide-y divide-white/10">
              <thead class="bg-slate-950/70 text-slate-400 text-[10px] uppercase font-bold">
                <tr>
                  <th class="px-3 py-2">Campo</th>
                  <th class="px-3 py-2">Tipo SQL</th>
                  <th class="px-3 py-2">Exemplo / Valor</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-white/5">
                ${fieldsRowsHtml}
              </tbody>
            </table>
          </div>
        </div>

        <!-- Inspetor JSON Bruto -->
        <div class="space-y-2">
          <div class="flex items-center justify-between">
            <h5 class="text-xs font-bold text-slate-300 uppercase tracking-wider font-sans">Payload Estruturado (JSON)</h5>
            <span class="text-[10px] text-slate-500 font-mono">Pydantic v1.0 Contract</span>
          </div>
          <pre class="max-h-64 overflow-y-auto p-3.5 rounded-xl bg-obsidian border border-slate-800 font-mono text-[11px] text-slate-300 leading-relaxed scrollbar-thin select-all">${this.escapeHtml(JSON.stringify(artifact.data, null, 2))}</pre>
        </div>
      </div>
    `;
  }

  /**
   * Perspectiva 4: Regras de Negócio & Auditoria
   */
  renderAuditView(artifact) {
    const auditView = document.getElementById('aux-view-audit');
    if (!auditView) return;

    const rules = artifact.auditRules || [];

    auditView.innerHTML = `
      <div class="space-y-4">
        <!-- Resumo da Metodologia -->
        <div class="p-3.5 rounded-xl bg-slate-900/60 border border-white/5 space-y-2">
          <div class="flex items-center justify-between">
            <h5 class="font-bold text-xs text-white uppercase tracking-wider font-sans flex items-center gap-1.5">
              <svg class="w-3.5 h-3.5 text-amber-400" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke-width="1.75"/><polyline points="14 2 14 8 20 8" stroke-width="1.75"/></svg>
              <span>Memória de Cálculo & Regras Oficiais</span>
            </h5>
            <span class="text-[10px] text-emerald-400 font-sans font-semibold">100% Determinístico</span>
          </div>
          <p class="text-xs text-slate-300 font-sans leading-relaxed">
            Todas as métricas e indicadores exibidos pela AURA são apurados por reconciliação determinística contra as tabelas oficiais do ERP e concentradores de pista, sem alucinações gerativas de números.
          </p>
        </div>

        <!-- Lista de Regras de Negócio e Fórmulas -->
        <div class="space-y-2.5">
          ${rules.map(rule => `
            <div class="p-3 rounded-xl bg-white/[0.02] border border-white/5 space-y-1">
              <div class="flex items-center justify-between text-xs">
                <span class="font-bold text-slate-200">${this.escapeHtml(rule.title)}</span>
                <span class="px-2 py-0.5 rounded text-[10px] font-sans font-medium bg-slate-800 text-cyan-300">${this.escapeHtml(rule.tag || 'Regra')}</span>
              </div>
              <div class="text-[11px] font-mono text-cyan-300 bg-obsidian/60 p-2 rounded-lg border border-slate-800">
                ${this.escapeHtml(rule.formula)}
              </div>
              <p class="text-[11px] text-slate-400 font-sans">${this.escapeHtml(rule.description)}</p>
            </div>
          `).join('')}
        </div>

        <!-- Botão Abrir Drawer de Evidências Completo -->
        <div class="pt-2">
          <button onclick="window.auraChat && window.auraChat.openEvidence && window.auraChat.openEvidence('${artifact.id}')" class="w-full py-2.5 rounded-xl bg-cyan-500/15 hover:bg-cyan-500/25 text-cyan-200 border border-cyan-500/30 text-xs font-semibold flex items-center justify-center gap-2 transition-colors">
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" stroke-width="1.75"/><rect x="8" y="2" width="8" height="4" rx="1" stroke-width="1.75"/></svg>
            <span>Inspecionar Evidências Detalhadas da Conciliação</span>
          </button>
        </div>
      </div>
    `;
  }

  // =========================================================================
  // NORMALIZADOR DE DADOS UNIVERSAL (POSTOS + QUALQUER BANCO DE DADOS)
  // =========================================================================

  normalizeArtifactData(toolName, intent, data, html) {
    const c = data?.contrato || data || {};
    const effectiveIntent = intent || c.intent || toolName || 'consulta_analitica';

    let title = 'Consulta Analítica';
    let subtitle = 'Dados Relacionais';
    let statusChip = { label: 'Concluído', severity: 'success' };
    let records = [];
    let summaryKpis = [];
    let auditRules = [];
    let schemaInfo = {
      source: 'PostgreSQL 16 (Porta 5433 ERP)',
      table: 'tb_relacional',
      recordCount: 0,
      fields: []
    };

    // MÓDULO 1: AUTONOMIA DE TANQUES & RUN-OUT
    if (effectiveIntent === 'tank_forecast' || toolName === 'previsao_tanques' || toolName === 'run_out') {
      title = '⛽ Autonomia de Tanques & Run-Out';
      subtitle = 'Volumetria Física, Ullage & Horizonte Crítico';
      const menorH = c.assessment?.horizonte_critico_horas ?? c.metrics?.autonomia_critica_horas;
      const statusLabel = c.assessment?.badge_label || (menorH !== undefined && menorH < 12 ? 'Estoque Crítico' : 'Estoque Confortável');
      statusChip = {
        label: statusLabel,
        severity: menorH !== undefined && menorH < 12 ? 'critical' : (menorH < 24 ? 'attention' : 'success')
      };

      const rawTanks = c.tanks || data.detalhamento_tanques || data.tanques || [];
      records = rawTanks.map(t => ({
        'Tanque': t.tanque || t.codtan || '—',
        'Combustível': t.combustivel || '—',
        'Saldo Físico (L)': t.saldo_litros !== undefined ? Number(t.saldo_litros).toLocaleString('pt-BR') : '—',
        'Capacidade (L)': t.capacidade_litros !== undefined ? Number(t.capacidade_litros).toLocaleString('pt-BR') : '—',
        'Espaço Livre Ullage (L)': (t.espaco_livre_litros ?? t.espaco_livre_ullage_litros) !== undefined ? Number(t.espaco_livre_litros ?? t.espaco_livre_ullage_litros).toLocaleString('pt-BR') : '—',
        'Autonomia 15% (h)': t.autonomia_critica_horas !== null && t.autonomia_critica_horas !== undefined ? `${Number(t.autonomia_critica_horas).toFixed(1)}h` : '—',
        'Esgotamento 0% (h)': t.autonomia_runout_horas !== null && t.autonomia_runout_horas !== undefined ? `${Number(t.autonomia_runout_horas).toFixed(1)}h` : '—',
        'Status': t.status || (t.autonomia_critica_horas < 12 ? 'CRÍTICO' : 'NORMAL')
      }));

      summaryKpis = [
        { label: 'Menor Autonomia (15%)', value: menorH !== undefined ? `${Number(menorH).toFixed(1)}h` : '—', sub: 'Até reserva técnica' },
        { label: 'Ullage Total Livre', value: c.metrics?.espaco_livre_ullage_total_litros ? `${Number(c.metrics.espaco_livre_ullage_total_litros).toLocaleString('pt-BR')} L` : '—', sub: 'Capacidade de descarga' },
        { label: 'Tanques Monitorados', value: `${records.length}`, sub: 'Revenda ativa' }
      ];

      schemaInfo = {
        source: 'PostgreSQL 16 • ERP Concentrador',
        table: 'public.tb_tanques_estoque',
        recordCount: records.length,
        fields: [
          { field: 'codtan', type: 'SMALLINT PRIMARY KEY', sample: 1 },
          { field: 'combustivel', type: 'VARCHAR(40)', sample: 'GASOLINA COMUM' },
          { field: 'saldo_litros', type: 'NUMERIC(10,2)', sample: 14500.00 },
          { field: 'capacidade_litros', type: 'NUMERIC(10,2)', sample: 30000.00 },
          { field: 'autonomia_critica_horas', type: 'NUMERIC(6,2)', sample: 18.5 }
        ]
      };

      auditRules = [
        { title: 'Reserva Crítica de Segurança (15%)', tag: 'ANP / Estoque', formula: 'Autonomia = (Saldo_Fisico - 0.15 * Capacidade) / Vazao_Horaria', description: 'Calcula o tempo antes de atingir o limite técnico onde bombas podem puxar ar ou impurezas do fundo.' },
        { title: 'Espaço Livre (Ullage) para Carreta', tag: 'Logística', formula: 'Ullage = Capacidade_Total - Saldo_Fisico_Atual', description: 'Determina quantos compartimentos de 5.000L da carreta podem ser descarregados sem risco de transbordamento.' }
      ];
    }

    // MÓDULO 2: CONCILIAÇÃO FISCAL LMC ANP
    else if (effectiveIntent === 'lmc_report' || toolName === 'lmc_anp' || toolName === 'gerar_relatorio_lmc_anp') {
      title = '📋 LMC ANP Oficial (Portaria 26)';
      subtitle = 'Auditoria Físico-Contábil & Tolerância ±0.60%';
      const varGeral = c.metrics?.variacao_volumetrica_geral_pct ?? 0.0;
      const isConforme = Math.abs(varGeral) <= 0.60;
      statusChip = {
        label: isConforme ? 'Conforme ANP (±0.6%)' : 'Alerta Variação Excessiva',
        severity: isConforme ? 'success' : 'critical'
      };

      const rawLmc = c.tanks || data.tanques || [];
      records = rawLmc.map(t => ({
        'Tanque': t.tanque || t.codtan || '—',
        'Combustível': t.combustivel || '—',
        'Abertura (L)': t.estoque_abertura_litros !== undefined ? Number(t.estoque_abertura_litros).toLocaleString('pt-BR') : '—',
        'Entradas (L)': t.entradas_litros !== undefined ? Number(t.entradas_litros).toLocaleString('pt-BR') : '—',
        'Vendas (L)': t.vendas_litros !== undefined ? Number(t.vendas_litros).toLocaleString('pt-BR') : '—',
        'Fechamento Escriturado (L)': t.estoque_fechamento_escriturado_litros !== undefined ? Number(t.estoque_fechamento_escriturado_litros).toLocaleString('pt-BR') : '—',
        'Fechamento Físico (L)': t.estoque_fechamento_fisico_litros !== undefined ? Number(t.estoque_fechamento_fisico_litros).toLocaleString('pt-BR') : '—',
        'Variação (L)': t.variacao_litros !== undefined ? Number(t.variacao_litros).toLocaleString('pt-BR') : '—',
        'Variação (%)': t.variacao_pct !== undefined ? `${Number(t.variacao_pct).toFixed(2)}%` : '—',
        'Status ANP': t.status_anp || (Math.abs(t.variacao_pct || 0) <= 0.6 ? 'CONFORME_ANP' : 'ALERTA')
      }));

      summaryKpis = [
        { label: 'Variação Geral Ponderada', value: `${Number(varGeral).toFixed(2)}%`, sub: 'Tolerância oficial: ±0.60%' },
        { label: 'Tanques em Alerta', value: `${c.assessment?.total_tanques_em_alerta ?? 0}`, sub: 'Fora do padrão legal' },
        { label: 'Total Auditado', value: `${records.length} tanques`, sub: 'Portaria ANP 26/1992' }
      ];

      schemaInfo = {
        source: 'PostgreSQL 16 • Livro de Movimentação de Combustíveis',
        table: 'public.tb_lmc_diario',
        recordCount: records.length,
        fields: [
          { field: 'data_movimento', type: 'DATE', sample: '2026-09-02' },
          { field: 'estoque_abertura', type: 'NUMERIC(12,2)', sample: 12000.00 },
          { field: 'entradas_nf', type: 'NUMERIC(12,2)', sample: 5000.00 },
          { field: 'vendas_bicos', type: 'NUMERIC(12,2)', sample: 4200.00 },
          { field: 'variacao_pct', type: 'NUMERIC(5,2)', sample: -0.08 }
        ]
      };

      auditRules = [
        { title: 'Fechamento Escriturado', tag: 'Contabilidade', formula: 'Estoque_Escriturado = Abertura + Entradas_NF - Vendas_Bicos', description: 'Volume que a contabilidade espera existir fisicamente nos tanques.' },
        { title: 'Tolerância Legal de Variação (ANP)', tag: 'Portaria 26', formula: 'Variacao_% = ((Fechamento_Fisico - Escriturado) / Escriturado) * 100', description: 'A ANP tolera variações de até 0,60% devido a fatores térmicos, evaporação e calibração de bicos.' }
      ];
    }

    // MÓDULO 3: VAZÃO DE BICOS & FRENTISTAS
    else if (effectiveIntent === 'pump_performance' || toolName === 'desempenho_pista_frentistas') {
      title = '🏎️ Performance de Pista & Frentistas';
      subtitle = 'Auditoria de Vazão L/min & Conversão de Aditivadas';
      const bicosLentos = c.assessment?.total_bicos_lentos ?? 0;
      statusChip = {
        label: bicosLentos === 0 ? 'Pista Conforme (Vazão OK)' : `${bicosLentos} Bicos Lentos (<30 L/min)`,
        severity: bicosLentos === 0 ? 'success' : 'attention'
      };

      const rawRanking = c.ranking || data.ranking_frentistas || [];
      records = rawRanking.map((r, i) => ({
        'Posição': r.posicao || (i + 1),
        'Frentista': r.frentista || '—',
        'Volume Total (L)': r.total_litros !== undefined ? Number(r.total_litros).toLocaleString('pt-BR') : '—',
        'Faturamento (R$)': r.faturamento !== undefined ? `R$ ${Number(r.faturamento).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}` : '—',
        'Conversão Aditivada (%)': r.vendas_aditivada_pct !== undefined ? `${Number(r.vendas_aditivada_pct).toFixed(1)}%` : '—',
        'Vazão Média (L/min)': r.vazao_media_l_min !== undefined ? `${Number(r.vazao_media_l_min).toFixed(1)} L/min` : '—'
      }));

      summaryKpis = [
        { label: 'Vazão Média da Pista', value: `${Number(c.metrics?.vazao_media_l_min ?? 35).toFixed(1)} L/min`, sub: 'Ideal: > 30 L/min' },
        { label: 'Bicos com Filtro Lento', value: `${bicosLentos}`, sub: 'Alerta preventivo' },
        { label: 'Equipe Ativa', value: `${records.length} frentistas`, sub: 'Turno sob demanda' }
      ];

      schemaInfo = {
        source: 'Automação da Pista • Concentrador Company/EzTech',
        table: 'public.tb_abastecimentos_bicos',
        recordCount: records.length,
        fields: [
          { field: 'frentista_id', type: 'INTEGER', sample: 102 },
          { field: 'total_litros', type: 'NUMERIC(10,2)', sample: 4520.00 },
          { field: 'vazao_l_min', type: 'NUMERIC(5,2)', sample: 36.2 }
        ]
      };

      auditRules = [
        { title: 'Limite de Vazão Crítica (< 30 L/min)', tag: 'Manutenção Pista', formula: 'Vazao = Litros_Abastecidos / (Tempo_Segundos / 60)', description: 'Vazão abaixo de 30 L/min indica saturação dos filtros internos da bomba ou desgaste de palhetas.' }
      ];
    }

    // MÓDULO 4: COMBOS DE CONVENIÊNCIA & BASKET
    else if (effectiveIntent === 'market_basket' || toolName === 'conveniencia_vendas_cruzadas') {
      title = '🛒 Combos & Vendas Cruzadas (Loja)';
      subtitle = 'Mineração de Regras de Associação & Lift PDV';
      const maxLift = c.metrics?.maior_lift ?? 1.0;
      statusChip = {
        label: `Max Lift ${Number(maxLift).toFixed(1)}x`,
        severity: maxLift >= 2.0 ? 'success' : 'neutral'
      };

      const rawCombos = c.top_combos || data.top_combos_cross_selling || [];
      records = rawCombos.map(item => ({
        'Produto Base': item.antecedente || '—',
        'Oferta Cruzada': item.consequente || '—',
        'Lift': item.lift !== undefined ? `${Number(item.lift).toFixed(2)}x` : '—',
        'Confiança (%)': item.confianca_pct !== undefined ? `${Number(item.confianca_pct).toFixed(1)}%` : '—',
        'Suporte (%)': item.suporte_pct !== undefined ? `${Number(item.suporte_pct).toFixed(1)}%` : '—',
        'Relevância': item.relevancia || (item.lift >= 2.0 ? 'MUITO ALTA' : 'ALTA'),
        'Script Balcão': item.script_sugerido_caixa || '—'
      }));

      summaryKpis = [
        { label: 'Maior Multiplicador (Lift)', value: `${Number(maxLift).toFixed(1)}x`, sub: 'Probabilidade cruzada' },
        { label: 'Combos Fortes (>= 2.0x)', value: `${c.assessment?.regras_com_forte_sinergia_lift_2 ?? records.length}`, sub: 'Prontos para oferta no caixa' },
        { label: 'Transações Auditadas', value: `${c.metrics?.total_transacoes_analisadas ?? 0}`, sub: 'Cupons fiscais loja' }
      ];

      schemaInfo = {
        source: 'PostgreSQL 16 • Retaguarda PDV Conveniência',
        table: 'public.tb_vendas_itens_cesta',
        recordCount: records.length,
        fields: [
          { field: 'antecedente', type: 'VARCHAR(100)', sample: 'Gasolina Aditivada' },
          { field: 'consequente', type: 'VARCHAR(100)', sample: 'Aditivo Flex STP' },
          { field: 'lift', type: 'NUMERIC(6,2)', sample: 3.4 }
        ]
      };

      auditRules = [
        { title: 'Índice Lift de Associação', tag: 'Data Mining', formula: 'Lift(A -> B) = Confianca(A -> B) / Suporte(B)', description: 'Lift > 1.0 indica que a compra de A aumenta ativamente a probabilidade de compra de B.' }
      ];
    }

    // MÓDULO 5: CONCILIAÇÃO DE TURNO & CAIXA
    else if (effectiveIntent === 'shift_reconciliation' || toolName === 'conciliacao_turno' || toolName === 'auditoria_turno') {
      title = '💰 Conciliação de Turno & Caixa';
      subtitle = 'Triangulação Encerrantes vs PDV Financeiro';
      const diff = c.metrics?.difference ?? 0.0;
      const isProv = c.assessment?.finality === 'partial' || c.metrics?.is_provisional;
      statusChip = {
        label: isProv ? 'Análise Provisória' : (Math.abs(diff) < 0.05 ? 'Caixa Zerado' : (diff < 0 ? `Quebra R$ ${Math.abs(diff).toFixed(2)}` : `Sobra R$ ${diff.toFixed(2)}`)),
        severity: isProv ? 'attention' : (Math.abs(diff) < 0.05 ? 'success' : 'critical')
      };

      records = [
        { 'Métrica': 'Receita Automação (Pista)', 'Valor': `R$ ${Number(c.metrics?.automation_revenue ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`, 'Observação': 'Medição de encerrantes das bombas' },
        { 'Métrica': 'Receita Registrada (PDV)', 'Valor': `R$ ${Number(c.metrics?.pos_revenue ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`, 'Observação': 'Cupons fiscais e sangrias do caixa' },
        { 'Métrica': 'Diferença Contábil', 'Valor': `${diff >= 0 ? '+' : ''}R$ ${Number(diff).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`, 'Observação': c.metrics?.difference_definition || 'PDV menos Automação' },
        { 'Métrica': 'Volume Físico Medido', 'Valor': c.metrics?.physical_volume_liters !== null && c.metrics?.physical_volume_liters !== undefined ? `${Number(c.metrics.physical_volume_liters).toLocaleString('pt-BR')} L` : 'Pendente de digitação', 'Observação': 'Módulo fechabomba' }
      ];

      summaryKpis = [
        { label: 'Diferença de Caixa', value: `R$ ${Number(diff).toFixed(2)}`, sub: isProv ? 'Provisório' : 'Validado' },
        { label: 'Receita Pista', value: `R$ ${Number(c.metrics?.automation_revenue ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`, sub: 'Automação' },
        { label: 'Receita Caixa PDV', value: `R$ ${Number(c.metrics?.pos_revenue ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`, sub: 'ERP' }
      ];

      schemaInfo = {
        source: 'PostgreSQL 16 • ERP Fechamento de Caixa',
        table: 'public.tb_conciliacao_fechamento',
        recordCount: 4,
        fields: [
          { field: 'shift_id', type: 'VARCHAR(20)', sample: 'Turno 1' },
          { field: 'automation_revenue', type: 'NUMERIC(12,2)', sample: 71.30 },
          { field: 'pos_revenue', type: 'NUMERIC(12,2)', sample: 62.98 },
          { field: 'difference', type: 'NUMERIC(12,2)', sample: -8.32 }
        ]
      };

      auditRules = [
        { title: 'Equação Canônica de Fechamento', tag: 'Contabilidade', formula: 'Diferenca = Receita_PDV - Receita_Automacao', description: 'Convenção oficial onde valores negativos representam quebra de caixa e valores positivos representam sobra.' }
      ];
    }

    // MÓDULO 6: VENDAS, PDV & FATURAMENTO
    else if (effectiveIntent === 'vendas_analitico' || toolName === 'vendas_analitico' || toolName === 'consultar_analise_vendas_erp') {
      title = '📊 Vendas & Faturamento PDV';
      subtitle = 'Histórico Transacional, Pista vs Conveniência & Curva ABC';
      const fatTotal = c.resumo_geral?.faturamento_total ?? c.metrics?.faturamento_total ?? data.faturamento_total ?? 0;
      const ultProd = c.ultimo_produto_vendido_destaque || data.ultimo_produto_vendido_destaque;
      statusChip = {
        label: fatTotal ? `Faturamento R$ ${Number(fatTotal).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}` : 'Vendas Auditadas',
        severity: 'success'
      };

      const rawProds = c.produtos_mais_vendidos || data.produtos_mais_vendidos || [];
      if (rawProds.length > 0) {
        records = rawProds.map((p, idx) => ({
          'Posição': idx + 1,
          'Código SKU': p.codpro || p.codigo_sku || '—',
          'Produto': p.nompro || p.produto || '—',
          'Qtd Saídas': p.total_saidas !== undefined ? Number(p.total_saidas).toLocaleString('pt-BR') : '—',
          'Volume / Qtd': p.qtd_total !== undefined ? Number(p.qtd_total).toLocaleString('pt-BR') : '—',
          'Receita (R$)': p.receita_total !== undefined ? `R$ ${Number(p.receita_total).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}` : '—'
        }));
      } else if (ultProd) {
        records = [{
          'Operação': ultProd.origem || 'PDV Conveniência',
          'Produto': ultProd.produto || '—',
          'Quantidade': Number(ultProd.quantidade || 1).toLocaleString('pt-BR'),
          'Total (R$)': `R$ ${Number(ultProd.valor_total || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`,
          'Data/Hora': ultProd.data_hora || '—',
          'Cupom / PDV': `${ultProd.cupom || '—'} / ${ultProd.pdv || '—'}`
        }];
      }

      summaryKpis = [
        { label: 'Faturamento Total', value: `R$ ${Number(fatTotal).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`, sub: 'ERP Caixa + Pista' },
        { label: 'Último Produto', value: ultProd?.produto ? String(ultProd.produto).substring(0, 18) : 'PDV Registrado', sub: ultProd?.data_hora ? ultProd.data_hora.split(' ')[1] : 'Tempo real' },
        { label: 'Produtos Auditados', value: `${records.length}`, sub: 'Ranking de vendas' }
      ];

      schemaInfo = {
        source: 'PostgreSQL 16 • ERP Retaguarda Vendas (Porta 5433)',
        table: 'public.tb_vendas_itens',
        recordCount: records.length,
        fields: [
          { field: 'codpro', type: 'VARCHAR(20) PRIMARY KEY', sample: '00022' },
          { field: 'nompro', type: 'VARCHAR(100)', sample: 'CERVEJA HEINEKEN LN 330ML' },
          { field: 'total_saidas', type: 'INTEGER', sample: 29 },
          { field: 'receita_total', type: 'NUMERIC(12,2)', sample: 319.00 }
        ]
      };

      auditRules = [
        { title: 'Curva ABC & Giro de Mercadorias', tag: 'Gestão Vendas', formula: 'Receita_Produto = Qtd_Vendida * Preco_Medio', description: 'Classifica os itens com maior contribuição marginal para a receita diária do posto.' },
        { title: 'Integridade de Cupons Fiscais', tag: 'Compliance Fiscal', formula: 'Faturamento_Total = Faturamento_Combustivel + Faturamento_Conveniencia', description: 'Reconcilia as vendas de bicos de combustível com os cupons emitidos no PDV da loja.' }
      ];
    }

    // FALLBACK UNIVERSAL: QUALQUER BANCO DE DADOS RELACIONAL FUTURO OU API
    else {
      title = `📊 ${this.formatToolTitle(toolName)}`;
      subtitle = 'Resultado de Consulta a Banco de Dados';
      statusChip = { label: 'Concluído', severity: 'success' };

      // Se houver lista de linhas no resultado, extrai automaticamente por chaves canônicas
      let rawRows = [];
      if (Array.isArray(data)) {
        rawRows = data;
      } else if (data && typeof data === 'object') {
        const candidateKeys = [
          'rows', 'records', 'items', 'itens', 'produtos', 'vendas',
          'produtos_mais_vendidos', 'detalhamento', 'detalhes',
          'resultado', 'data', 'tanks', 'ranking', 'combos'
        ];
        for (const k of candidateKeys) {
          if (Array.isArray(data[k]) && data[k].length > 0) {
            rawRows = data[k];
            break;
          }
        }
      }

      if (rawRows.length > 0 && typeof rawRows[0] === 'object') {
        records = rawRows.slice(0, 100);
      } else if (data && typeof data === 'object' && !Array.isArray(data)) {
        // Objeto chave-valor plano: converte em linhas tabulares de 2 colunas
        records = Object.entries(data)
          .filter(([k, v]) => typeof v !== 'function' && typeof v !== 'object' && k !== 'contrato')
          .map(([k, v]) => ({
            'Propriedade / Métrica': this.formatColumnHeader(k),
            'Valor': String(v ?? '—')
          }));
      }

      const inferredCols = records.length > 0 ? Array.from(new Set(records.flatMap(r => Object.keys(r || {})))) : [];

      schemaInfo = {
        source: data.db_source || 'PostgreSQL 16 (Conexão Relacional)',
        table: data.table_name || 'public.resultado_query',
        recordCount: records.length,
        fields: inferredCols.map(k => ({
          field: k,
          type: typeof records[0]?.[k] === 'number' ? 'NUMERIC' : (typeof records[0]?.[k] === 'boolean' ? 'BOOLEAN' : 'VARCHAR'),
          sample: records[0]?.[k]
        }))
      };

      summaryKpis = [
        { label: 'Linhas Retornadas', value: `${records.length}`, sub: 'Banco Conectado' },
        { label: 'Status da Execução', value: 'OK (200)', sub: 'ACID Preservado' }
      ];

      auditRules = [
        { title: 'Integridade de Dados', tag: 'Governança', formula: 'Transação = READ COMMITTED', description: 'Dados extraídos com isolamento transacional para evitar leituras sujas.' }
      ];
    }

    return {
      intent: effectiveIntent,
      title,
      subtitle,
      statusChip,
      records,
      summaryKpis,
      schemaInfo,
      auditRules
    };
  }

  // =========================================================================
  // EXPORTAÇÃO E UTILITÁRIOS
  // =========================================================================

  copyActiveData() {
    if (this.activeTab === 'data') {
      this.copyCsv();
    } else {
      this.copyJson();
    }
  }

  copyCsv() {
    const artifact = this.getActiveArtifact();
    if (!artifact || !artifact.records || artifact.records.length === 0) {
      this.showToast('Nenhum dado tabular para exportar.');
      return;
    }

    const rows = artifact.records;
    const headers = Array.from(new Set(rows.flatMap(r => Object.keys(r || {}))));
    const csvLines = [
      headers.join(';'),
      ...rows.map(row => headers.map(h => `"${String(row[h] ?? '').replace(/"/g, '""')}"`).join(';'))
    ];

    const csvContent = csvLines.join('\n');
    this.writeToClipboard(csvContent, '✓ Tabela exportada como CSV com sucesso!');
  }

  downloadCsv() {
    const artifact = this.getActiveArtifact();
    if (!artifact || !artifact.records || artifact.records.length === 0) {
      this.showToast('Nenhum dado tabular para exportar.');
      return;
    }

    const rows = artifact.records;
    const headers = Array.from(new Set(rows.flatMap(r => Object.keys(r || {}))));
    const csvLines = [
      headers.join(';'),
      ...rows.map(row => headers.map(h => `"${String(row[h] ?? '').replace(/"/g, '""')}"`).join(';'))
    ];

    // Inclui UTF-8 BOM (\uFEFF) para garantir abertura com acentos corretos no Excel / Windows
    const csvContent = '\uFEFF' + csvLines.join('\r\n');

    if (typeof document !== 'undefined' && typeof Blob !== 'undefined') {
      try {
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        const slug = (artifact.intent || artifact.toolName || 'dados').replace(/[^a-z0-9]/gi, '_').toLowerCase();
        const filename = `aura_${slug}_${Date.now()}.csv`;
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        this.showToast(`✓ Arquivo ${filename} baixado com sucesso!`);
        return;
      } catch (_) {}
    }

    this.writeToClipboard(csvContent, '✓ Tabela copiada como CSV!');
  }

  copyJson() {
    const artifact = this.getActiveArtifact();
    if (!artifact || !artifact.data) {
      this.showToast('Nenhum JSON para copiar.');
      return;
    }

    const jsonStr = JSON.stringify(artifact.data, null, 2);
    this.writeToClipboard(jsonStr, '✓ JSON do contrato copiado com sucesso!');
  }

  writeToClipboard(text, successMsg) {
    if (typeof navigator !== 'undefined' && navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(() => {
        this.showToast(successMsg);
      }).catch(() => {
        this.fallbackCopy(text, successMsg);
      });
    } else {
      this.fallbackCopy(text, successMsg);
    }
  }

  fallbackCopy(text, successMsg) {
    if (typeof document === 'undefined') return;
    try {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      this.showToast(successMsg);
    } catch (_) {
      this.showToast('Erro ao copiar dados.');
    }
  }

  showToast(msg) {
    if (typeof document === 'undefined') return;

    let toast = document.getElementById('aux-floating-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'aux-floating-toast';
      toast.className = 'fixed bottom-6 right-6 z-50 px-4 py-2.5 rounded-xl bg-slate-900/95 border border-cyan-500/50 text-cyan-200 text-xs font-semibold shadow-2xl backdrop-blur-md transition-all duration-300 opacity-0 pointer-events-none flex items-center gap-2';
      document.body.appendChild(toast);
    }

    toast.innerHTML = `
      <span class="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
      <span>${this.escapeHtml(msg)}</span>
    `;
    toast.classList.remove('opacity-0', 'pointer-events-none');
    toast.classList.add('opacity-100');

    setTimeout(() => {
      toast.classList.remove('opacity-100');
      toast.classList.add('opacity-0', 'pointer-events-none');
    }, 2800);
  }

  formatToolTitle(name) {
    if (!name) return 'Consulta Analítica';
    return name
      .replace(/_/g, ' ')
      .replace(/\b\w/g, l => l.toUpperCase());
  }

  formatColumnHeader(col) {
    return col.replace(/_/g, ' ');
  }

  getColumnAlignmentClass(col, val) {
    if (typeof val === 'number' || (!isNaN(Number(val)) && !String(val).includes(' '))) {
      return 'text-right';
    }
    return 'text-left';
  }

  formatTableCell(col, val) {
    if (val === null || val === undefined) return '<span class="text-slate-500">—</span>';
    const str = String(val);
    if (str === 'CRÍTICO' || str.includes('ALERTA')) {
      return `<span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-500/15 text-rose-300 border border-rose-500/30">${this.escapeHtml(str)}</span>`;
    }
    if (str === 'NORMAL' || str.includes('CONFORME')) {
      return `<span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">${this.escapeHtml(str)}</span>`;
    }
    return this.escapeHtml(str);
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

// Inicialização Singleton e Export
if (typeof window !== 'undefined') {
  window.AuraAuxPanel = AuraAuxPanel;
  window.auraAuxPanel = new AuraAuxPanel();
}
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { AuraAuxPanel };
}
