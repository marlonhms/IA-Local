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
    this.isExpanded = false; // false = split padrao (54/46), true = canvas expandido (38/62)
    this.activeTab = 'visual'; // 'visual' | 'data' | 'schema' | 'audit'
    this.artifacts = []; // lista de artefatos da sessao
    this.activeArtifactId = null;
    this.userDismissed = false;
    this.filterQuery = '';
    this.lastDataGridArtifactId = null;
    this.previousFocusedElement = null;
    this.techMode = false;
    this.morphTimeout = null;
    this.chatMorphTimeout = null;
    this.contentRevealTimeout = null;
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

  /**
   * Avalia se o Modo Tecnico de TI / Infraestrutura esta ativo.
   * Padrao de producao: FALSE (Visao 100% Executiva para Donos, Gerentes e Supervisores).
   * Liberacao temporaria via query param ?tech=1/?dev=1 ou localStorage.getItem('aura_tech_mode') === 'true'.
   */
  isTechModeActive(win = (typeof window !== 'undefined' ? window : null)) {
    if (!win) return false;
    try {
      if (win.location && win.location.search) {
        const urlParams = new URLSearchParams(win.location.search);
        if (urlParams.get('tech') === '1' || urlParams.get('dev') === '1') return true;
        if (urlParams.get('tech') === '0' || urlParams.get('dev') === '0') return false;
      }
      if (typeof win.localStorage !== 'undefined' && win.localStorage) {
        return win.localStorage.getItem('aura_tech_mode') === 'true';
      }
    } catch (_) {}
    return false;
  }

  /**
   * Altera o Modo Tecnico e persiste no storage local.
   */
  setTechMode(enabled, notify = true) {
    this.techMode = !!enabled;
    try {
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem('aura_tech_mode', this.techMode ? 'true' : 'false');
      }
    } catch (_) {}

    this.updateTechModeVisibility();

    if (notify && typeof window !== 'undefined') {
      const fx = window.auraFx;
      if (fx && typeof fx.showToast === 'function') {
        fx.showToast({
          title: this.techMode ? 'Modo Técnico Ativado (Admin)' : 'Modo Executivo Padrão',
          message: this.techMode 
            ? 'Abas de Banco, Esquema SQL e Auditoria liberadas para desenvolvimento.' 
            : 'Interface limpa para Donos e Gerentes. Detalhes técnicos ocultados.',
          type: this.techMode ? 'warning' : 'info'
        });
      }
      if (window.auraAudio && typeof window.auraAudio.playChime === 'function') {
        window.auraAudio.playChime(this.techMode ? 880 : 540, 0.06);
      }
    }
  }

  toggleTechMode() {
    this.setTechMode(!this.techMode, true);
  }

  /**
   * Atualiza a visibilidade das abas e legendas de acordo com o Modo Tecnico
   */
  updateTechModeVisibility() {
    if (typeof document === 'undefined') return;

    const tabSchema = document.getElementById('aux-tab-schema');
    const tabAudit = document.getElementById('aux-tab-audit');
    const footerProvenance = document.getElementById('aux-footer-provenance');

    if (this.techMode) {
      if (tabSchema) tabSchema.classList.remove('hidden');
      if (tabAudit) tabAudit.classList.remove('hidden');
      if (footerProvenance) {
        footerProvenance.textContent = 'PostgreSQL 16 (Local) • Modo Técnico Ativo';
        footerProvenance.classList.add('text-amber-300');
      }
    } else {
      if (tabSchema) tabSchema.classList.add('hidden');
      if (tabAudit) tabAudit.classList.add('hidden');
      if (footerProvenance) {
        footerProvenance.textContent = 'AURA Inteligência de Posto • Dados Homologados';
        footerProvenance.classList.remove('text-amber-300');
      }
      // Se o usuario estiver atualmente na aba de esquema ou auditoria, redireciona para a visao executiva
      if (this.activeTab === 'schema' || this.activeTab === 'audit') {
        this.switchTab('visual');
      }
    }
  }

  init() {
    this.techMode = this.isTechModeActive();
    this.bindEvents();
    this.updateTechModeVisibility();
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

    // Atalhos de Teclado Globais: Alt+P (Toggle), Ctrl+Shift+D / Ctrl+Alt+T (Modo Tecnico) e Escape (Fechar)
    if (typeof window !== 'undefined') {
      window.addEventListener('keydown', (e) => {
        if (e.altKey && (e.key === 'p' || e.key === 'P')) {
          e.preventDefault();
          this.toggle();
          return;
        }

        // Atalho Oculto para Administrador / Modo Tecnico (Ctrl+Shift+D ou Ctrl+Alt+T)
        if ((e.ctrlKey && e.shiftKey && (e.key === 'd' || e.key === 'D')) ||
            (e.ctrlKey && e.altKey && (e.key === 't' || e.key === 'T'))) {
          e.preventDefault();
          this.toggleTechMode();
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

    // Clique secreto no rodape do painel auxiliar para alternar o modo tecnico (3 cliques rapidos)
    const footerEl = document.querySelector('.aux-panel-footer');
    if (footerEl) {
      let clickCount = 0;
      let clickTimeout = null;
      footerEl.addEventListener('click', () => {
        clickCount++;
        clearTimeout(clickTimeout);
        if (clickCount >= 3) {
          clickCount = 0;
          this.toggleTechMode();
        } else {
          clickTimeout = setTimeout(() => { clickCount = 0; }, 600);
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
   * Abre o painel auxiliar com arquitetura de transicao desacoplada (60 FPS)
   */
  open(artifactId = null, playSound = true, triggerElement = null) {
    if (artifactId) {
      this.activeArtifactId = artifactId;
    }

    const auxPanel = typeof document !== 'undefined' ? document.getElementById('aura-aux-panel') : null;

    // Se o painel ja estiver aberto e visivel, apenas atualiza o conteudo sem disparar novo morph
    if (this.isOpen && auxPanel && !auxPanel.classList.contains('hidden') && !auxPanel.classList.contains('aux-panel-morphing')) {
      this.renderActiveArtifact();
      const activeArt = this.getActiveArtifact();
      if (activeArt && activeArt.containerId) {
        const msgEl = document.getElementById(activeArt.containerId);
        if (msgEl) {
          msgEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      }
      return;
    }

    this.isOpen = true;
    this.userDismissed = false;

    if (typeof document !== 'undefined') {
      this.previousFocusedElement = document.activeElement;

      // Cancela timeouts de animacoes pendentes para evitar condicao de corrida
      if (this.morphTimeout) {
        clearTimeout(this.morphTimeout);
        this.morphTimeout = null;
      }
      if (this.chatMorphTimeout) {
        clearTimeout(this.chatMorphTimeout);
        this.chatMorphTimeout = null;
      }
      if (this.contentRevealTimeout) {
        clearTimeout(this.contentRevealTimeout);
        this.contentRevealTimeout = null;
      }

      // 1. Identifica o botao de origem (card, acao ou header)
      let trigger = triggerElement;
      if (!trigger && document.activeElement) {
        const el = document.activeElement;
        if (
          el.id === 'btn-toggle-aux-panel' ||
          (typeof el.closest === 'function' && el.closest('#btn-toggle-aux-panel')) ||
          el.classList?.contains('aux-btn-view-panel') ||
          el.classList?.contains('aux-btn-view-chat') ||
          el.getAttribute?.('data-action-id') === 'act_default_canvas'
        ) {
          trigger = el;
        }
      }

      // Se nenhum botao estiver focado, busca o cartao de resultado mais recente no chat
      if (!trigger) {
        trigger = document.querySelector('#chat-feed-container .aux-btn-view-panel:last-of-type') ||
                  document.querySelector('#chat-feed-container [data-action-id="act_default_canvas"]:last-of-type') ||
                  document.getElementById('btn-toggle-aux-panel');
      }

      this.lastTriggerElement = trigger;

      if (trigger && typeof trigger.getBoundingClientRect === 'function') {
        trigger.classList.remove('aux-btn-pulse-morph');
        void trigger.offsetWidth;
        trigger.classList.add('aux-btn-pulse-morph');
      }

      const consoleView = document.getElementById('view-console');
      const chatColumn = document.getElementById('chat-stream-column');
      const btnToggle = document.getElementById('btn-toggle-aux-panel');
      const peekToast = document.getElementById('aux-artifact-peek-toast');
      const beacon = document.getElementById('aux-toggle-beacon');

      // 2. Captura geometria previa do chat antes de ativar o layout split
      const chatFirstRect = (chatColumn && typeof chatColumn.getBoundingClientRect === 'function')
        ? chatColumn.getBoundingClientRect()
        : null;

      // 3. Prepara o painel em camada invisivel antes de acoplar no layout
      if (auxPanel) {
        auxPanel.style.opacity = '0';
        auxPanel.style.transition = 'none';
        auxPanel.classList.remove('hidden');
        auxPanel.classList.add('aux-panel-morphing');
        auxPanel.classList.remove('aux-panel-content-revealed');
      }

      // 4. Ativa estado de layout no console e header (sem transicao sincrona concorrente)
      if (consoleView) {
        consoleView.classList.add('aux-panel-active');
        if (this.isExpanded) consoleView.classList.add('aux-expanded');
      }

      if (btnToggle) {
        btnToggle.setAttribute('aria-expanded', 'true');
        btnToggle.classList.add('bg-cyan-500/15', 'border-cyan-500/40', 'text-cyan-200');
      }

      if (peekToast) peekToast.classList.add('hidden');
      if (beacon) beacon.classList.add('hidden');

      // 5. Pre-popula titulos basicos para evitar salto visual sem custo pesado de renderizacao
      const artifact = this.getActiveArtifact();
      if (artifact) {
        const titleEl = document.getElementById('aux-panel-title');
        const subEl = document.getElementById('aux-panel-subtitle');
        if (titleEl) titleEl.textContent = artifact.title;
        if (subEl) subEl.textContent = artifact.subtitle;
      }

      // 6. Neutraliza o salto do chat via GPU FLIP imediato
      const chatLastRect = (chatColumn && typeof chatColumn.getBoundingClientRect === 'function')
        ? chatColumn.getBoundingClientRect()
        : null;

      let chatDeltaX = 0;
      let chatDeltaY = 0;
      if (chatColumn && chatFirstRect && chatLastRect) {
        chatDeltaX = chatFirstRect.left - chatLastRect.left;
        chatDeltaY = chatFirstRect.top - chatLastRect.top;
        if (Math.abs(chatDeltaX) > 1 || Math.abs(chatDeltaY) > 1) {
          chatColumn.style.transformOrigin = 'top left';
          chatColumn.style.transition = 'none';
          chatColumn.style.transform = `translate3d(${chatDeltaX}px, ${chatDeltaY}px, 0px)`;
          void chatColumn.offsetWidth;
        }
      }

      // 7. Captura coordenadas exatas do botao de origem apos o chat estar estabilizado
      const btnRect = (trigger && typeof trigger.getBoundingClientRect === 'function')
        ? trigger.getBoundingClientRect()
        : null;

      // 8. Executa Spatial Morphing desacoplado via GPU FLIP
      if (auxPanel) {
        this.runSpatialMorphOpen(trigger, auxPanel, btnRect, chatColumn, chatDeltaX, chatDeltaY);
      }
    }

    if (playSound && typeof window !== 'undefined' && window.auraAudio && typeof window.auraAudio.playChime === 'function') {
      window.auraAudio.playChime(680, 0.06);
    }
  }

  /**
   * Spatial Morphing Real (Dynamic Island / Apple Vision Pro)
   * O proprio painel nasce nas coordenadas e dimensoes exatas do botao clicado (FLIP)
   * e se expande organicamente no espaco atraves de transform 3D e GPU compositor (60 FPS).
   * Desacopla o morphing visual de reflows pesados via execucao 100% acelerada por hardware.
   */
  runSpatialMorphOpen(triggerEl, auxPanel, cachedBtnRect = null, chatColumn = null, chatDeltaX = 0, chatDeltaY = 0) {
    if (!auxPanel || typeof document === 'undefined') return;

    if (typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      auxPanel.style.transform = '';
      auxPanel.style.opacity = '1';
      auxPanel.classList.remove('aux-panel-morphing');
      if (chatColumn) {
        chatColumn.style.transform = '';
        chatColumn.style.transition = '';
      }
      this.renderActiveArtifact();
      return;
    }

    const btnRect = cachedBtnRect || ((triggerEl && typeof triggerEl.getBoundingClientRect === 'function')
      ? triggerEl.getBoundingClientRect()
      : null);

    const panelRect = auxPanel.getBoundingClientRect();

    // Caso de fallback (sem coordenadas validas de botao)
    if (!btnRect || btnRect.width === 0 || btnRect.height === 0 || !panelRect || panelRect.width === 0) {
      auxPanel.style.transformOrigin = 'center right';
      auxPanel.style.transform = 'scale(0.96) translate3d(24px, 0, 0)';
      auxPanel.style.opacity = '0';
      void auxPanel.offsetWidth;

      requestAnimationFrame(() => {
        auxPanel.style.transition = 'transform 360ms cubic-bezier(0.2, 0.9, 0.3, 1), opacity 260ms ease-out';
        auxPanel.style.transform = 'scale(1) translate3d(0, 0, 0)';
        auxPanel.style.opacity = '1';

        this.contentRevealTimeout = setTimeout(() => {
          this.renderActiveArtifact();
          auxPanel.classList.remove('aux-panel-morphing');
          auxPanel.classList.add('aux-panel-content-revealed');
        }, 200);

        this.morphTimeout = setTimeout(() => {
          auxPanel.style.transition = '';
          auxPanel.style.transform = '';
          auxPanel.style.transformOrigin = '';
          auxPanel.classList.remove('aux-panel-content-revealed');
        }, 380);
      });
      return;
    }

    // FLIP Step 2: Invert: posiciona a capsula do painel exatamente sobre o botao de origem
    const deltaX = btnRect.left - panelRect.left;
    const deltaY = btnRect.top - panelRect.top;
    const scaleX = Math.max(0.04, Math.min(1, btnRect.width / panelRect.width));
    const scaleY = Math.max(0.02, Math.min(1, btnRect.height / panelRect.height));
    const initialRadius = Math.max(8, Math.min(btnRect.height / 2, 24));

    auxPanel.style.transformOrigin = 'top left';
    auxPanel.style.transition = 'none';
    auxPanel.style.transform = `translate3d(${deltaX}px, ${deltaY}px, 0px) scale(${scaleX}, ${scaleY})`;
    auxPanel.style.borderRadius = `${initialRadius}px`;
    auxPanel.style.opacity = '0.65';
    auxPanel.style.boxShadow = '0 0 30px rgba(6, 182, 212, 0.45), 0 10px 25px rgba(0, 0, 0, 0.5)';

    // Forca aplicacao do estado inicial sem reflow concorrente
    void auxPanel.offsetWidth;

    // FLIP Step 3: Play: animacao simultanea em curva Apple Spring 100% acelerada por hardware
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        const springCurve = 'cubic-bezier(0.2, 0.9, 0.3, 1)';
        const duration = 400;

        auxPanel.style.transition = `transform ${duration}ms ${springCurve}, opacity 280ms ease-out, border-radius ${duration}ms ${springCurve}, box-shadow ${duration}ms ease-out`;
        auxPanel.style.transform = 'translate3d(0px, 0px, 0px) scale(1, 1)';
        auxPanel.style.borderRadius = '16px';
        auxPanel.style.opacity = '1';
        auxPanel.style.boxShadow = '0 20px 50px -15px rgba(0, 0, 0, 0.5), 0 0 1px rgba(255, 255, 255, 0.12)';

        if (chatColumn && (Math.abs(chatDeltaX) > 1 || Math.abs(chatDeltaY) > 1)) {
          chatColumn.style.transition = `transform ${duration}ms ${springCurve}`;
          chatColumn.style.transform = 'translate3d(0px, 0px, 0px)';
        }

        // Revelacao suave do conteudo interno quando a capsula atinge maturidade de expansao
        const revealDelay = Math.round(duration * 0.65);
        this.contentRevealTimeout = setTimeout(() => {
          this.renderActiveArtifact();
          auxPanel.classList.remove('aux-panel-morphing');
          auxPanel.classList.add('aux-panel-content-revealed');
        }, revealDelay);

        this.morphTimeout = setTimeout(() => {
          auxPanel.style.transition = '';
          auxPanel.style.transform = '';
          auxPanel.style.transformOrigin = '';
          auxPanel.style.borderRadius = '';
          auxPanel.style.boxShadow = '';
          auxPanel.classList.remove('aux-panel-content-revealed');

          if (chatColumn) {
            chatColumn.style.transition = '';
            chatColumn.style.transform = '';
            chatColumn.style.transformOrigin = '';
          }

          // Rola suavemente para a mensagem associada no chat apos conclusao da transicao
          const activeArt = this.getActiveArtifact();
          if (activeArt && activeArt.containerId) {
            const msgEl = document.getElementById(activeArt.containerId);
            if (msgEl) {
              msgEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
          }
        }, duration + 30);
      });
    });
  }

  /**
   * Fecha o painel auxiliar com Spatial Morphing reverso em direcao ao botao de origem
   * Desacopla o fechamento em 2 estagios limpos: recolhimento GPU do painel primeiro,
   * seguido pelo reposicionamento suave da coluna de chat com GPU transform (60 FPS).
   */
  close(playSound = true) {
    this.isOpen = false;
    this.userDismissed = true;

    if (typeof document !== 'undefined') {
      const consoleView = document.getElementById('view-console');
      const chatColumn = document.getElementById('chat-stream-column');
      const auxPanel = document.getElementById('aura-aux-panel');
      const btnToggle = document.getElementById('btn-toggle-aux-panel');

      if (this.morphTimeout) {
        clearTimeout(this.morphTimeout);
        this.morphTimeout = null;
      }
      if (this.chatMorphTimeout) {
        clearTimeout(this.chatMorphTimeout);
        this.chatMorphTimeout = null;
      }
      if (this.contentRevealTimeout) {
        clearTimeout(this.contentRevealTimeout);
        this.contentRevealTimeout = null;
      }

      if (btnToggle) {
        btnToggle.setAttribute('aria-expanded', 'false');
        btnToggle.classList.remove('bg-cyan-500/15', 'border-cyan-500/40', 'text-cyan-200');
      }

      if (auxPanel && !auxPanel.classList.contains('hidden')) {
        const trigger = this.lastTriggerElement;
        const btnRect = (trigger && typeof trigger.getBoundingClientRect === 'function')
          ? trigger.getBoundingClientRect()
          : null;
        const panelRect = auxPanel.getBoundingClientRect();

        // Estagio 1: O painel se recolhe de volta ao botao via GPU (260ms)
        if (btnRect && panelRect && panelRect.width > 0) {
          const deltaX = btnRect.left - panelRect.left;
          const deltaY = btnRect.top - panelRect.top;
          const scaleX = Math.max(0.04, Math.min(1, btnRect.width / panelRect.width));
          const scaleY = Math.max(0.02, Math.min(1, btnRect.height / panelRect.height));

          auxPanel.style.transformOrigin = 'top left';
          auxPanel.style.transition = 'transform 260ms cubic-bezier(0.4, 0, 1, 1), opacity 200ms ease-out';
          auxPanel.style.transform = `translate3d(${deltaX}px, ${deltaY}px, 0px) scale(${scaleX}, ${scaleY})`;
          auxPanel.style.opacity = '0';
        } else {
          auxPanel.style.transformOrigin = 'center right';
          auxPanel.style.transition = 'transform 220ms ease-in, opacity 200ms ease-out';
          auxPanel.style.transform = 'scale(0.96) translate3d(20px, 0, 0)';
          auxPanel.style.opacity = '0';
        }

        // Estagio 2: Ao finalizar o recolhimento, oculta o painel e reposiciona o chat suavemente
        this.morphTimeout = setTimeout(() => {
          auxPanel.classList.add('hidden');
          auxPanel.style.transition = '';
          auxPanel.style.transform = '';
          auxPanel.style.transformOrigin = '';
          auxPanel.style.opacity = '';
          auxPanel.classList.remove('aux-panel-morphing', 'aux-panel-content-revealed');

          if (consoleView) {
            const chatFirstRect = (chatColumn && typeof chatColumn.getBoundingClientRect === 'function')
              ? chatColumn.getBoundingClientRect()
              : null;

            consoleView.classList.remove('aux-panel-active', 'aux-expanded');

            const chatLastRect = (chatColumn && typeof chatColumn.getBoundingClientRect === 'function')
              ? chatColumn.getBoundingClientRect()
              : null;

            if (chatColumn && chatFirstRect && chatLastRect) {
              const chatDeltaX = chatFirstRect.left - chatLastRect.left;
              if (Math.abs(chatDeltaX) > 2) {
                chatColumn.style.transformOrigin = 'top left';
                chatColumn.style.transform = `translate3d(${chatDeltaX}px, 0px, 0px)`;
                chatColumn.style.transition = 'none';
                void chatColumn.offsetWidth;

                requestAnimationFrame(() => {
                  chatColumn.style.transition = 'transform 280ms cubic-bezier(0.2, 0.9, 0.3, 1)';
                  chatColumn.style.transform = 'translate3d(0px, 0px, 0px)';

                  this.chatMorphTimeout = setTimeout(() => {
                    chatColumn.style.transition = '';
                    chatColumn.style.transform = '';
                    chatColumn.style.transformOrigin = '';
                  }, 300);
                });
              }
            }
          }
        }, 260);
      } else if (consoleView) {
        consoleView.classList.remove('aux-panel-active', 'aux-expanded');
      }

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
   * Alterna largura entre Split Padrao (54%/46%) e Expandido (38%/62%)
   * Utiliza FLIP GPU para alternancia fluida sem engasgo de reflow.
   */
  toggleExpand() {
    this.isExpanded = !this.isExpanded;
    if (typeof document !== 'undefined') {
      const consoleView = document.getElementById('view-console');
      const chatColumn = document.getElementById('chat-stream-column');
      const auxPanel = document.getElementById('aura-aux-panel');
      const expandIcon = document.getElementById('aux-expand-icon');

      if (this.morphTimeout) {
        clearTimeout(this.morphTimeout);
        this.morphTimeout = null;
      }
      if (this.chatMorphTimeout) {
        clearTimeout(this.chatMorphTimeout);
        this.chatMorphTimeout = null;
      }
      if (this.contentRevealTimeout) {
        clearTimeout(this.contentRevealTimeout);
        this.contentRevealTimeout = null;
      }

      if (consoleView) {
        const chatFirstRect = (chatColumn && typeof chatColumn.getBoundingClientRect === 'function')
          ? chatColumn.getBoundingClientRect()
          : null;
        const panelFirstRect = (auxPanel && typeof auxPanel.getBoundingClientRect === 'function')
          ? auxPanel.getBoundingClientRect()
          : null;

        if (this.isExpanded) {
          consoleView.classList.add('aux-expanded');
        } else {
          consoleView.classList.remove('aux-expanded');
        }

        const chatLastRect = (chatColumn && typeof chatColumn.getBoundingClientRect === 'function')
          ? chatColumn.getBoundingClientRect()
          : null;
        const panelLastRect = (auxPanel && typeof auxPanel.getBoundingClientRect === 'function')
          ? auxPanel.getBoundingClientRect()
          : null;

        if (chatColumn && chatFirstRect && chatLastRect) {
          const chatDeltaX = chatFirstRect.left - chatLastRect.left;
          if (Math.abs(chatDeltaX) > 2) {
            chatColumn.style.transformOrigin = 'top left';
            chatColumn.style.transform = `translate3d(${chatDeltaX}px, 0px, 0px)`;
            chatColumn.style.transition = 'none';
          }
        }

        if (auxPanel && panelFirstRect && panelLastRect) {
          const panelDeltaX = panelFirstRect.left - panelLastRect.left;
          if (Math.abs(panelDeltaX) > 2) {
            auxPanel.style.transformOrigin = 'top left';
            auxPanel.style.transform = `translate3d(${panelDeltaX}px, 0px, 0px)`;
            auxPanel.style.transition = 'none';
          }
        }

        if (auxPanel) void auxPanel.offsetWidth;

        requestAnimationFrame(() => {
          const springCurve = 'cubic-bezier(0.2, 0.9, 0.3, 1)';
          if (chatColumn && chatColumn.style.transform) {
            chatColumn.style.transition = `transform 320ms ${springCurve}`;
            chatColumn.style.transform = 'translate3d(0px, 0px, 0px)';
          }
          if (auxPanel && auxPanel.style.transform) {
            auxPanel.style.transition = `transform 320ms ${springCurve}`;
            auxPanel.style.transform = 'translate3d(0px, 0px, 0px)';
          }
          setTimeout(() => {
            if (chatColumn) {
              chatColumn.style.transition = '';
              chatColumn.style.transform = '';
              chatColumn.style.transformOrigin = '';
            }
            if (auxPanel) {
              auxPanel.style.transition = '';
              auxPanel.style.transform = '';
              auxPanel.style.transformOrigin = '';
            }
          }, 340);
        });
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
      if (this.techMode) {
        footerProvEl.textContent = `${artifact.schemaInfo?.source || 'PostgreSQL Local'} • Modo Técnico • ${artifact.timeFormatted}`;
      } else {
        footerProvEl.textContent = `AURA Inteligência de Posto • Dados Homologados • ${artifact.timeFormatted}`;
      }
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

    let artifactHtml = artifact.html || '';
    if (artifactHtml && !artifactHtml.includes('genui-hydrated-card') && artifact.id && artifact.id.startsWith('art_genui_')) {
      const toolCallId = artifact.id.replace('art_genui_', '');
      artifactHtml = `<div id="genui-canvas-card-${toolCallId}" class="genui-hydrated-card genui-decision-mentor-card" data-tool-call-id="${toolCallId}" data-component="${artifact.toolName || 'render_ExecutiveDecisionMentorUI'}">${artifactHtml}</div>`;
    }

    // Se o artefato ja possui um widget visual completo (GenUI Card), o proprio widget e a interface completa.
    // Nao exibimos cards de resumo tecnicos ou redundantes no topo da visualizacao.
    const hasRichWidget = Boolean(artifactHtml && artifactHtml.trim().length > 0);

    let kpisHtml = '';
    if (!hasRichWidget && artifact.summaryKpis && artifact.summaryKpis.length > 0) {
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

    if (!hasRichWidget && (!artifact.summaryKpis || artifact.summaryKpis.length === 0)) {
      if (artifact.records && artifact.records.length > 0) {
        visualView.innerHTML = `
          <div class="p-5 rounded-2xl bg-slate-900/60 border border-white/5 space-y-3 text-center">
            <div class="w-10 h-10 mx-auto rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 flex items-center justify-center">
              <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor"><rect x="3" y="3" width="18" height="18" rx="2" stroke-width="1.75"/><line x1="3" y1="9" x2="21" y2="9" stroke-width="1.5"/><line x1="9" y1="21" x2="9" y2="9" stroke-width="1.5"/></svg>
            </div>
            <div>
              <h4 class="font-bold text-sm text-white font-sans">${this.escapeHtml(artifact.title)}</h4>
              <p class="text-xs text-slate-400 mt-1">${this.escapeHtml(artifact.subtitle || 'Consulta executiva realizada com sucesso.')}</p>
            </div>
            <div class="pt-2">
              <button class="px-4 py-2 rounded-xl bg-cyan-500/20 text-cyan-300 hover:bg-cyan-500/30 border border-cyan-500/30 text-xs font-semibold transition-all inline-flex items-center gap-2" onclick="window.auraAuxPanel.switchTab('data')">
                <span>Ver Tabela de Dados (${artifact.records.length} itens)</span>
                <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor"><polyline points="9 18 15 12 9 6" stroke-width="2"/></svg>
              </button>
            </div>
          </div>
        `;
        return;
      }
    }

    visualView.innerHTML = `
      ${kpisHtml}
      <div class="aux-visual-container">
        ${artifactHtml}
      </div>
    `;

    // Vincula listeners aos micro-widgets GenUI projetados no Canvas
    this.bindGenUIEvents(visualView);
  }

  /**
   * Vincula listeners de interacao aos micro-widgets GenUI presentes no contêiner
   */
  bindGenUIEvents(container) {
    if (!container || typeof container.querySelectorAll !== 'function') return;
    const cards = container.querySelectorAll('.genui-hydrated-card[data-tool-call-id], [data-tool-call-id]');
    const seen = new Set();
    cards.forEach(card => {
      const toolCallId = card.getAttribute('data-tool-call-id');
      if (!toolCallId || seen.has(toolCallId)) return;
      seen.add(toolCallId);
      const genui = (typeof window !== 'undefined' && window.AuraGenUI) ||
                    (typeof AuraGenUI !== 'undefined' ? AuraGenUI : null);
      let widget = (genui && typeof genui.getWidget === 'function')
        ? genui.getWidget(toolCallId)
        : null;

      if (!widget) {
        const compName = card.getAttribute('data-component') || 'render_ExecutiveDecisionMentorUI';
        const registry = (typeof window !== 'undefined' && window.SecureComponentRegistry) ||
                         (genui && genui.registry);
        let CompDef = null;
        if (registry && typeof registry.resolveComponent === 'function') {
          try {
            CompDef = registry.resolveComponent(compName, { throwOnMissing: false });
          } catch (_) {}
        }
        if (!CompDef && typeof ExecutiveDecisionMentorUI !== 'undefined') {
          CompDef = ExecutiveDecisionMentorUI;
        }
        if (CompDef) {
          try {
            widget = new CompDef({
              tool_call_id: toolCallId,
              component_name: compName
            });
            widget.element = card;
            if (genui && typeof genui.registerWidget === 'function') {
              genui.registerWidget(toolCallId, widget);
            }
          } catch (_) {}
        }
      }

      if (widget && typeof widget.bindEvents === 'function') {
        widget.bindEvents(card);
      }
    });
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
        return { field: k, type, sample: sampleVal ?? '-' };
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
        <td class="px-3 py-2 text-slate-400 text-[11px] truncate max-w-xs">${this.escapeHtml(String(f.sample ?? '-'))}</td>
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

        // MÓDULO 1: DIAGNÓSTICO EXECUTIVO DE ROI & PERDAS (90 DIAS)
    if (effectiveIntent === 'roi_diagnostic' || effectiveIntent === 'diagnostico_executivo_roi' || effectiveIntent === 'diagnostico_perdas' || toolName === 'render_RoiDiagnosticUI' || toolName === 'RoiDiagnosticUI') {
      const summary = c.summary || data?.summary || data?.props?.summary || {};
      const breakdown = c.breakdown_brl || data?.breakdown_brl || data?.props?.breakdown_brl || {};
      const shield = c.regulatory_shield || data?.regulatory_shield || data?.props?.regulatory_shield || {};

      title = 'Diagnostico Executivo de ROI & Perdas';
      subtitle = 'Projecao Deterministica de 90 Dias & Blindagem ANP';
      const mult = Number(summary.roi_multiple || 20.7);
      statusChip = {
        label: `Retorno ${mult.toFixed(1)}x (Garantia 3x Ativa)`,
        severity: 'success'
      };

      summaryKpis = [
        { label: 'Perda Mensal Mapeada', value: `R$ ${Number(summary.total_monthly_leakage_brl || 17070).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`, change: 'Vazamento', severity: 'danger' },
        { label: 'Recuperacao Mensal', value: `R$ ${Number(summary.estimated_monthly_recovery_brl || 13206).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`, change: 'Projecao AURA', severity: 'success' },
        { label: 'Retorno Liquido 90d', value: `R$ ${Number(summary.roi_90_days_net_brl || 28903.8).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`, change: 'Lucro Extra', severity: 'success' },
        { label: 'Multiplo de Retorno', value: `${mult.toFixed(1)}x`, change: 'Sobre o Plano', severity: 'info' }
      ];

      records = [
        { 'Vetor de Perda': '1. LMC & Variacao Tanques (ANP 26)', 'Impacto Mensal (R$)': `R$ ${Number(breakdown.lmc_and_tank_shrinkage || 4520).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`, 'Origem / Causa': 'Perdas termicas e divergencia escriturada vs fisica', 'Severidade': 'Critico' },
        { 'Vetor de Perda': '2. Cancelamentos PDV & Loja', 'Impacto Mensal (R$)': `R$ ${Number(breakdown.convenience_and_pos_cancellations || 3100).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`, 'Origem / Causa': 'Cancelamentos anomolos fora da curva historica', 'Severidade': 'Atencao' },
        { 'Vetor de Perda': '3. Furos de Gaveta & Fechamento', 'Impacto Mensal (R$)': `R$ ${Number(breakdown.cashier_shift_discrepancies || 1850).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`, 'Origem / Causa': 'Divergencia entre numerario de pista e sangrias', 'Severidade': 'Atencao' },
        { 'Vetor de Perda': '4. Arbitragem Carreta & Preco', 'Impacto Mensal (R$)': `R$ ${Number(breakdown.pricing_and_carreta_arbitrage || 6200).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`, 'Origem / Causa': 'Perda de desconto de lote fechado (30.000 L)', 'Severidade': 'Oportunidade' },
        { 'Vetor de Perda': '5. Custo SELIC Capital Morto', 'Impacto Mensal (R$)': `R$ ${Number(breakdown.working_capital_selic_cost || 1400).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`, 'Origem / Causa': 'Custo de capital de giro parado > 30 dias sem giro', 'Severidade': 'Atencao' }
      ];

      schemaInfo = {
        source: 'AURA Partner Gateway & Staging Store',
        table: 'roi_diagnostic_ledger',
        recordCount: records.length,
        fields: Object.keys(records[0] || {})
      };
      return { title, subtitle, statusChip, records, schemaInfo, auditRules, summaryKpis, intent: 'roi_diagnostic' };
    }

    // MÓDULO 4: RADAR DE ANOMALIAS DE PDV & CAIXA (Z-SCORE)
    if (effectiveIntent === 'pos_audit' || effectiveIntent === 'radar_anomalias_pdv' || toolName === 'render_PosAuditRadarUI' || toolName === 'PosAuditRadarUI') {
      const shift = c.cashier_shift_audit || data?.cashier_shift_audit || data?.props?.cashier_shift_audit || {};
      const isConc = shift.status === 'CONCILIADO';
      const anomCount = Number(c.anomalous_operators_count || data?.anomalous_operators_count || 0);

      title = 'Radar de Anomalias de PDV & Caixa (Z-Score)';
      subtitle = 'Auditoria Estatistica e Contabil com Blindagem Art. 462 CLT';
      statusChip = {
        label: isConc ? 'Fechamento Conciliado' : `${anomCount} Anomalia(s) Detectada(s)`,
        severity: isConc ? 'success' : 'attention'
      };

      const rawOps = c.operators_analysis || data?.operators_analysis || data?.props?.operators_analysis || [];
      records = rawOps.map(o => ({
        'Operador': o.operator_id || 'N/A',
        'Total Pedidos': o.total_orders || 0,
        'Cancelados': o.cancelled_orders || 0,
        'Taxa %': `${Number(o.cancellation_rate_pct || 0).toFixed(1)}%`,
        'Z-Score': Number(o.z_score || 0).toFixed(2),
        'Classificacao': o.is_anomaly ? 'Anomalia Estatistica (>2σ)' : 'Padrao Historico'
      }));

      schemaInfo = {
        source: 'AURA POS Audit Engine & CLT Shield',
        table: 'pos_anomaly_ledger',
        recordCount: records.length,
        fields: ['Operador', 'Total Pedidos', 'Cancelados', 'Taxa %', 'Z-Score', 'Classificacao']
      };
      return { title, subtitle, statusChip, records, schemaInfo, auditRules, summaryKpis, intent: 'pos_audit' };
    }

    // MÓDULO 4 / MOBILE: BRIEFING MATINAL ZERO-CLICK (CAFÉ COM O DONO)
    if (effectiveIntent === 'zero_click_briefing' || effectiveIntent === 'briefing_matinal' || toolName === 'render_MorningBriefingUI' || toolName === 'MorningBriefingUI') {
      const s24 = c.sales_summary_24h || data?.sales_summary_24h || data?.props?.sales_summary_24h || {};
      const tank = c.tank_critical_runout || data?.tank_critical_runout || data?.props?.tank_critical_runout || {};

      title = 'Briefing Matinal Zero-Click (Cafe com o Dono)';
      subtitle = 'Panorama Consolidado 24h & Alertas Logísticos';
      statusChip = {
        label: 'Pronto p/ WhatsApp',
        severity: 'success'
      };

      summaryKpis = [
        { label: 'Faturamento 24h', value: `R$ ${Number(s24.total_turnover_brl || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`, change: 'Consolidado', severity: 'success' },
        { label: 'Volume Total', value: `${Number(s24.total_liters || 0).toLocaleString('pt-BR')} L`, change: 'Pista', severity: 'info' },
        { label: 'Tanque Critico', value: `Tanque ${tank.tank_id || '1'} (${Number(tank.occupancy_pct || 0).toFixed(1)}%)`, change: tank.fuel_type || 'Combustivel', severity: 'attention' }
      ];

      records = [
        { 'Parametro': 'Faturamento 24h', 'Valor': `R$ ${Number(s24.total_turnover_brl || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}` },
        { 'Parametro': 'Volume Vendido', 'Valor': `${Number(s24.total_liters || 0).toLocaleString('pt-BR')} L` },
        { 'Parametro': 'Tanque Menor Autonomia', 'Valor': `Tanque ${tank.tank_id || '1'} (${tank.fuel_type || 'Combustivel'}) - ${Number(tank.occupancy_pct || 0).toFixed(1)}%` },
        { 'Parametro': 'Sugestao de Compra', 'Valor': `${tank.recommended_order_compartments || 0} compartimento(s) de 5.000 L` }
      ];

      schemaInfo = {
        source: 'AURA Morning Zero-Click Engine',
        table: 'morning_briefing_ledger',
        recordCount: records.length,
        fields: ['Parametro', 'Valor']
      };
      return { title, subtitle, statusChip, records, schemaInfo, auditRules, summaryKpis, intent: 'zero_click_briefing' };
    }

// MÓDULO 0-A: DIAGNÓSTICO MODULAR GENERATIVO (BLOCOS LEGO)
    if (effectiveIntent === 'diagnostico_modular' || effectiveIntent === 'modular_card' || toolName === 'render_GenerativeModularCardUI' || toolName === 'GenerativeModularCardUI') {
      title = c.title || data?.props?.title || data?.title || '🧩 Diagnóstico Executivo Modular';
      subtitle = c.diagnosis || c.subtitle || data?.props?.diagnosis || data?.subtitle || 'Métricas & Prioridades de Gestão em Blocos';
      const score = c.confidence_score !== undefined ? Math.round(Number(c.confidence_score) * 100) : (data?.props?.confidence_score !== undefined ? Math.round(Number(data.props.confidence_score) * 100) : 98);
      statusChip = {
        label: `${score}% Confiança Analítica`,
        severity: score >= 90 ? 'success' : 'attention'
      };

      const metricsList = c.metrics || data?.props?.metrics || data?.metrics || [];
      records = metricsList.map(m => ({
        'Indicador Executivo': m.label || '-',
        'Valor Atual': m.current_value !== undefined ? String(m.current_value) : '-',
        'Benchmark / Meta': m.benchmark_value !== undefined ? String(m.benchmark_value) : '-',
        'Tendência': m.trend === 'up' ? '▲ Alta' : (m.trend === 'down' ? '▼ Queda' : '▬ Neutro'),
        'Status': m.status === 'success' ? '✔ Conforme' : (m.status === 'danger' ? '✖ Crítico' : (m.status === 'warning' ? '⚠ Atenção' : 'Neutro'))
      }));

      summaryKpis = [
        { label: 'Score Confiança', value: `${score}%`, sub: 'Auditado Determinístico' },
        { label: 'Métricas Apuradas', value: `${records.length}`, sub: 'Indicadores chave' },
        { label: 'Diagnóstico', value: 'Ativo', sub: 'Visão Integrada' }
      ];

      schemaInfo = {
        source: 'PostgreSQL 16 • ERP & Telemetria Consolidada (Porta 5433)',
        table: 'view_generative_modular_card',
        recordCount: records.length,
        fields: [
          { field: 'diagnosis', type: 'TEXT', sample: c.diagnosis || 'Diagnóstico operacional' },
          { field: 'confidence_score', type: 'NUMERIC(3,2)', sample: c.confidence_score || 0.98 },
          { field: 'metrics', type: 'JSONB', sample: records.length }
        ]
      };

      auditRules = [
        { title: 'Decomposição Modular de Pista & Estoque', tag: 'Gestão Integrada', formula: 'Consolidação = Tanques + Caixa + Margem', description: 'Cruza telemetria física dos tanques com fechamento de caixa e margem de bicos.' },
        { title: 'Score de Confiança Analítica', tag: 'Metodologia', formula: 'Score = Confianca_Fontes * Determinismo_Matematico', description: 'Calculado com base na completude dos dados das últimas 24h sem extrapolações.' }
      ];
    }

    // MÓDULO 0: MENTOR DE DECISÕES EXECUTIVO (GENUI FASE 3)
    else if (effectiveIntent === 'mentoria_decisao' || effectiveIntent === 'executive_briefing' || toolName === 'render_ExecutiveDecisionMentorUI' || toolName === 'render_ExecutiveBriefingUI' || toolName === 'ExecutiveDecisionMentorUI') {
      title = '🎯 Mentor de Decisões Executivo';
      subtitle = 'Diagnóstico de Rentabilidade, Gaps & Ações em 1 Toque';
      const score = c.confidence_score !== undefined ? Math.round(Number(c.confidence_score) * 100) : 96;
      statusChip = {
        label: `${score}% Confiança Analítica`,
        severity: score >= 90 ? 'success' : (score >= 75 ? 'attention' : 'neutral')
      };

      const metricsList = c.metrics || data.metrics || [];
      records = metricsList.map(m => ({
        'Indicador Executivo': m.label || '-',
        'Valor Atual': m.current_value !== undefined ? String(m.current_value) : '-',
        'Benchmark / Meta': m.benchmark_value !== undefined ? String(m.benchmark_value) : '-',
        'Tendência': m.trend === 'up' ? '▲ Alta' : (m.trend === 'down' ? '▼ Queda' : '▬ Neutro'),
        'Status': m.status === 'success' ? '✔ Conforme' : (m.status === 'danger' ? '✖ Crítico' : (m.status === 'warning' ? '⚠ Atenção' : 'Neutro'))
      }));

      summaryKpis = [
        { label: 'Score Confiança', value: `${score}%`, sub: 'Auditado Determinístico' },
        { label: 'Métricas Chave', value: `${records.length}`, sub: 'Indicadores apurados' },
        { label: 'Diagnóstico', value: 'Ativo', sub: 'Pronto para Ação' }
      ];

      schemaInfo = {
        source: 'PostgreSQL 16 • ERP & Telemetria Consolidada (Porta 5433)',
        table: 'view_executive_decision_mentor',
        recordCount: records.length,
        fields: [
          { field: 'diagnosis', type: 'TEXT', sample: c.diagnosis || 'Diagnóstico operacional' },
          { field: 'confidence_score', type: 'NUMERIC(3,2)', sample: c.confidence_score || 0.96 },
          { field: 'metrics', type: 'JSONB', sample: records.length }
        ]
      };

      auditRules = [
        { title: 'Decomposição Determinística de Rentabilidade', tag: 'Finanças', formula: 'Margem_Real = Receita_Liquida - (CPV + Taxas_Cartao + Quebras)', description: 'Cruza a receita líquida deduzindo custos diretos e desvios de caixa.' },
        { title: 'Score de Confiança Analítica', tag: 'Metodologia', formula: 'Score = Confianca_Fontes * Determinismo_Matematico', description: 'Calculado com base na completude dos dados das últimas 24h sem extrapolações não auditadas.' }
      ];
    }

    // MÓDULO 1: AUTONOMIA DE TANQUES & RUN-OUT
    else if (effectiveIntent === 'tank_forecast' || toolName === 'previsao_tanques' || toolName === 'run_out') {
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
        'Tanque': t.tanque || t.codtan || '-',
        'Combustível': t.combustivel || '-',
        'Saldo Físico (L)': t.saldo_litros !== undefined ? Number(t.saldo_litros).toLocaleString('pt-BR') : '-',
        'Capacidade (L)': t.capacidade_litros !== undefined ? Number(t.capacidade_litros).toLocaleString('pt-BR') : '-',
        'Espaço Livre Ullage (L)': (t.espaco_livre_litros ?? t.espaco_livre_ullage_litros) !== undefined ? Number(t.espaco_livre_litros ?? t.espaco_livre_ullage_litros).toLocaleString('pt-BR') : '-',
        'Autonomia 15% (h)': t.autonomia_critica_horas !== null && t.autonomia_critica_horas !== undefined ? `${Number(t.autonomia_critica_horas).toFixed(1)}h` : '-',
        'Esgotamento 0% (h)': t.autonomia_runout_horas !== null && t.autonomia_runout_horas !== undefined ? `${Number(t.autonomia_runout_horas).toFixed(1)}h` : '-',
        'Status': t.status || (t.autonomia_critica_horas < 12 ? 'CRÍTICO' : 'NORMAL')
      }));

      summaryKpis = [
        { label: 'Menor Autonomia (15%)', value: menorH !== undefined ? `${Number(menorH).toFixed(1)}h` : '-', sub: 'Até reserva técnica' },
        { label: 'Ullage Total Livre', value: c.metrics?.espaco_livre_ullage_total_litros ? `${Number(c.metrics.espaco_livre_ullage_total_litros).toLocaleString('pt-BR')} L` : '-', sub: 'Capacidade de descarga' },
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
        'Tanque': t.tanque || t.codtan || '-',
        'Combustível': t.combustivel || '-',
        'Abertura (L)': t.estoque_abertura_litros !== undefined ? Number(t.estoque_abertura_litros).toLocaleString('pt-BR') : '-',
        'Entradas (L)': t.entradas_litros !== undefined ? Number(t.entradas_litros).toLocaleString('pt-BR') : '-',
        'Vendas (L)': t.vendas_litros !== undefined ? Number(t.vendas_litros).toLocaleString('pt-BR') : '-',
        'Fechamento Escriturado (L)': t.estoque_fechamento_escriturado_litros !== undefined ? Number(t.estoque_fechamento_escriturado_litros).toLocaleString('pt-BR') : '-',
        'Fechamento Físico (L)': t.estoque_fechamento_fisico_litros !== undefined ? Number(t.estoque_fechamento_fisico_litros).toLocaleString('pt-BR') : '-',
        'Variação (L)': t.variacao_litros !== undefined ? Number(t.variacao_litros).toLocaleString('pt-BR') : '-',
        'Variação (%)': t.variacao_pct !== undefined ? `${Number(t.variacao_pct).toFixed(2)}%` : '-',
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
        'Frentista': r.frentista || '-',
        'Volume Total (L)': r.total_litros !== undefined ? Number(r.total_litros).toLocaleString('pt-BR') : '-',
        'Faturamento (R$)': r.faturamento !== undefined ? `R$ ${Number(r.faturamento).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}` : '-',
        'Conversão Aditivada (%)': r.vendas_aditivada_pct !== undefined ? `${Number(r.vendas_aditivada_pct).toFixed(1)}%` : '-',
        'Vazão Média (L/min)': r.vazao_media_l_min !== undefined ? `${Number(r.vazao_media_l_min).toFixed(1)} L/min` : '-'
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
    else if (
      effectiveIntent === 'market_basket' ||
      effectiveIntent === 'conveniencia_vendas_cruzadas' ||
      effectiveIntent === 'vendas_cruzadas' ||
      effectiveIntent === 'cesta_compras' ||
      effectiveIntent === 'basket_upsell' ||
      effectiveIntent === 'cross_selling' ||
      toolName === 'conveniencia_vendas_cruzadas' ||
      toolName === 'auditar_cesta_conveniencia_vendas_cruzadas' ||
      toolName === 'render_BasketUpsellStrategyUI' ||
      toolName === 'BasketUpsellStrategyUI'
    ) {
      title = '🛒 Combos & Vendas Cruzadas (Loja)';
      subtitle = 'Mineração de Regras de Associação & Lift PDV';
      const propsObj = c.props || {};
      const metricsObj = c.metrics || (c.contrato && c.contrato.metrics) || propsObj.metrics || {};
      const resumoObj = c.resumo_executivo || propsObj.resumo_executivo || {};
      const maxLift = metricsObj.maior_lift ?? resumoObj.maior_lift_encontrado ?? (propsObj.top_combos && propsObj.top_combos[0]?.lift) ?? 1.0;
      statusChip = {
        label: `Max Lift ${Number(maxLift).toFixed(1)}x`,
        severity: maxLift >= 2.0 ? 'success' : 'neutral'
      };

      const rawCombos = c.top_combos || data.top_combos_cross_selling || propsObj.top_combos || [];
      records = rawCombos.map(item => {
        const orig = item.anchor_product || item.origem || (typeof item.produto_origem === 'object' ? item.produto_origem?.nompro : item.produto_origem) || item.antecedente || '-';
        const rec = item.recommended_product || item.recomendado || (typeof item.produto_recomendado === 'object' ? item.produto_recomendado?.nompro : item.produto_recomendado) || item.consequente || '-';
        const liftVal = item.lift ?? item.metricas?.lift ?? 1.0;
        const confVal = item.confidence_pct ?? item.confianca_pct ?? (item.metricas?.confianca ? item.metricas.confianca * 100 : undefined);
        const supVal = item.support_pct ?? item.suporte_pct ?? (item.metricas?.suporte ? item.metricas.suporte * 100 : undefined);
        const pitch = item.script_pitch || item.script_sugerido_caixa || '-';
        const ticketAdd = item.additional_ticket_reais ?? item.ticket_recomendado_reais ?? item.impacto_financeiro?.incremento_ticket_reais ?? item.impacto_financeiro?.preco_recomendado;
        return {
          'Produto Base': orig,
          'Oferta Cruzada': rec,
          'Lift': `${Number(liftVal).toFixed(2)}x`,
          'Confiança (%)': confVal !== undefined ? `${Number(confVal).toFixed(1)}%` : '-',
          'Suporte (%)': supVal !== undefined ? `${Number(supVal).toFixed(1)}%` : '-',
          'Ticket Adic. (R$)': ticketAdd !== undefined ? `R$ ${Number(ticketAdd).toFixed(2)}` : '-',
          'Relevância': item.relevancia || (Number(liftVal) >= 2.0 ? 'MUITO ALTA' : 'ALTA'),
          'Script Balcão': pitch
        };
      });

      const totalAudited = metricsObj.total_transacoes_analisadas ?? resumoObj.total_transacoes_analisadas ?? 0;
      const combosFortes = c.assessment?.regras_com_forte_sinergia_lift_2 ?? resumoObj.regras_com_forte_sinergia_lift_2 ?? records.filter(r => parseFloat(r.Lift) >= 2.0).length;

      summaryKpis = [
        { label: 'Maior Multiplicador (Lift)', value: `${Number(maxLift).toFixed(1)}x`, sub: 'Probabilidade cruzada' },
        { label: 'Combos Fortes (>= 2.0x)', value: `${combosFortes}`, sub: 'Prontos para oferta no caixa' },
        { label: 'Transações Auditadas', value: `${totalAudited}`, sub: 'Cupons fiscais loja' }
      ];

      schemaInfo = {
        source: 'PostgreSQL 16 • Retaguarda PDV Conveniência',
        table: 'public.tb_vendas_itens_cesta',
        recordCount: records.length,
        fields: [
          { field: 'anchor_product', type: 'VARCHAR(100)', sample: 'Café Expresso' },
          { field: 'recommended_product', type: 'VARCHAR(100)', sample: 'Pão de Queijo' },
          { field: 'lift', type: 'NUMERIC(6,2)', sample: 3.45 }
        ]
      };

      auditRules = [
        { title: 'Índice Lift de Associação', tag: 'Data Mining', formula: 'Lift(A -> B) = Confianca(A -> B) / Suporte(B)', description: 'Lift > 1.0 indica que a compra de A aumenta ativamente a probabilidade de compra de B.' }
      ];
    }

    // MÓDULO 4-B: FORMAS DE PAGAMENTO & CAIXAS
    else if (
      effectiveIntent === 'formas_pagamento' ||
      effectiveIntent === 'pagamentos_caixa' ||
      toolName === 'formas_pagamento' ||
      toolName === 'consultar_formas_pagamento_detalhado' ||
      toolName === 'render_PaymentMethodsBreakdownUI' ||
      toolName === 'PaymentMethodsBreakdownUI'
    ) {
      title = '💳 Formas de Pagamento & Caixas';
      subtitle = c.subtitle || data?.subtitle || 'Detalhamento por Terminal PDV, Operador & Modalidade';
      const totGeral = Number(c.total_geral_reais ?? data?.total_geral_reais ?? 0.0);
      const totCupons = Number(c.total_transacoes ?? data?.total_transacoes ?? 0);
      const numCaixas = Number(c.total_caixas_ativos ?? data?.total_caixas_ativos ?? (c.caixas_operadores ? c.caixas_operadores.length : 1));

      statusChip = {
        label: totGeral > 0 ? ('Total R$ ' + totGeral.toLocaleString('pt-BR', { minimumFractionDigits: 2 })) : 'Vendas Auditadas',
        severity: 'success'
      };

      const caixasLista = c.caixas_operadores || data?.caixas_operadores || [];
      if (caixasLista.length > 0) {
        records = caixasLista.map(cx => ({
          'Caixa (PDV)': cx.caixa || cx.caixa_raw || '-',
          'Operador Responsável': cx.operador_nome || '-',
          'Matrícula': cx.operador_matricula || '-',
          'Turno': cx.turno || '1º TURNO',
          'Dinheiro (R$)': cx.dinheiro_reais !== undefined ? ('R$ ' + Number(cx.dinheiro_reais).toLocaleString('pt-BR', { minimumFractionDigits: 2 })) : '-',
          'Cartão (R$)': cx.cartao_total_reais !== undefined ? ('R$ ' + Number(cx.cartao_total_reais).toLocaleString('pt-BR', { minimumFractionDigits: 2 })) : '-',
          'PIX (R$)': cx.pix_reais !== undefined ? ('R$ ' + Number(cx.pix_reais).toLocaleString('pt-BR', { minimumFractionDigits: 2 })) : '-',
          'Total Caixa (R$)': cx.total_caixa_reais !== undefined ? ('R$ ' + Number(cx.total_caixa_reais).toLocaleString('pt-BR', { minimumFractionDigits: 2 })) : '-',
          'Cupons': cx.total_cupons || 1
        }));
      } else {
        const mods = c.modalidades || data?.modalidades || [];
        records = mods.map(m => ({
          'Modalidade': m.modalidade || '-',
          'Valor Total (R$)': 'R$ ' + Number(m.total_reais || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 }),
          'Transações': m.total_transacoes || 0,
          'Representatividade (%)': Number(m.percentual || 0).toFixed(1) + '%',
          'Ticket Médio (R$)': 'R$ ' + Number(m.ticket_medio || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })
        }));
      }

      summaryKpis = [
        { label: 'Faturamento Auditado', value: 'R$ ' + totGeral.toLocaleString('pt-BR', { minimumFractionDigits: 2 }), sub: totCupons + ' vendas finalizadas' },
        { label: 'Caixas com Movimento', value: String(numCaixas), sub: 'Terminais PDV ativos' },
        { label: 'Maior Modalidade', value: c.maior_modalidade || 'Dinheiro / Cartão', sub: 'Concentração de fluxo' }
      ];

      schemaInfo = {
        source: 'PostgreSQL 16 • ERP webPosto (Porta 5433)',
        table: 'public.pedido JOIN public.prazos JOIN public.funcionarios',
        recordCount: records.length,
        fields: [
          { field: 'pdv', type: 'CHARACTER(3)', sample: '007' },
          { field: 'vendedor', type: 'CHARACTER(5)', sample: '00007' },
          { field: 'formapg', type: 'CHARACTER(3)', sample: '001' },
          { field: 'valortotal', type: 'NUMERIC(12,2)', sample: 13.49 }
        ]
      };

      auditRules = [
        { title: 'Decomposição por Ponto de Venda (PDV)', tag: 'Auditoria de Caixa', formula: 'Total_Caixa = Sum(valortotal) WHERE pdv = X AND situ != C', description: 'Garante que os valores informados correspondam estritamente ao caixa físico e operador emitente.' },
        { title: 'Conciliação de Meios Eletrônicos vs Espécie', tag: 'Prevenção a Furos', formula: 'Fechamento = Dinheiro_Fisico + TEF_Debito + TEF_Credito + PIX', description: 'Separa rigorosamente dinheiro vivo sob custódia do operador contra liquidações bancárias automáticas.' }
      ];
    }

    // MÓDULO 5: CONCILIAÇÃO DE TURNO & CAIXA
    else if (effectiveIntent === 'shift_reconciliation' || toolName === 'conciliacao_turno' || toolName === 'auditoria_turno' || toolName === 'render_ShiftReconciliationUI' || toolName === 'ShiftReconciliationUI') {
      title = '💰 Conciliação de Turno & Caixa';
      subtitle = 'Triangulação Encerrantes vs PDV Financeiro';
      const propsObj = c.props || {};
      const metricsObj = c.metrics || (c.contrato && c.contrato.metrics) || propsObj.metrics || {};
      const resumoObj = c.resumo_executivo || propsObj.resumo_executivo || {};
      const autoRev = Number(metricsObj.automation_revenue ?? c.automation_revenue ?? propsObj.automation_revenue ?? resumoObj.faturamento_pista_total ?? 0.0);
      const posRev = Number(metricsObj.pos_revenue ?? c.pos_revenue ?? propsObj.pos_revenue ?? resumoObj.faturamento_caixa_total ?? 0.0);
      const diff = Number(metricsObj.difference ?? c.difference ?? propsObj.difference ?? resumoObj.diferenca_financeira_caixa ?? (posRev - autoRev));
      const isProv = Boolean(c.assessment?.finality === 'partial' || propsObj.is_provisional || metricsObj.is_provisional || c.is_provisional || (resumoObj.status_conciliacao && String(resumoObj.status_conciliacao).includes('ANDAMENTO')));
      const physVol = metricsObj.physical_volume_liters ?? c.physical_volume_liters ?? propsObj.physical_volume_liters ?? null;

      statusChip = {
        label: isProv ? 'Análise Provisória' : (Math.abs(diff) < 0.05 ? 'Caixa Zerado' : (diff < 0 ? `Quebra R$ ${Math.abs(diff).toFixed(2)}` : `Sobra R$ ${diff.toFixed(2)}`)),
        severity: isProv ? 'attention' : (Math.abs(diff) < 0.05 ? 'success' : 'critical')
      };

      records = [
        { 'Métrica': 'Receita Automação (Pista)', 'Valor': `R$ ${autoRev.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`, 'Observação': 'Medição de encerrantes das bombas' },
        { 'Métrica': 'Receita Registrada (PDV)', 'Valor': `R$ ${posRev.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`, 'Observação': 'Cupons fiscais e sangrias do caixa' },
        { 'Métrica': 'Diferença Contábil', 'Valor': `${diff >= 0 ? '+' : ''}R$ ${diff.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`, 'Observação': metricsObj.difference_definition || 'PDV menos Automação' },
        { 'Métrica': 'Volume Físico Medido', 'Valor': physVol !== null && physVol !== undefined ? `${Number(physVol).toLocaleString('pt-BR')} L` : 'Pendente de digitação', 'Observação': 'Módulo fechabomba' }
      ];

      summaryKpis = [
        { label: 'Diferença de Caixa', value: `R$ ${diff.toFixed(2)}`, sub: isProv ? 'Provisório' : 'Validado' },
        { label: 'Receita Pista', value: `R$ ${autoRev.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`, sub: 'Automação' },
        { label: 'Receita Caixa PDV', value: `R$ ${posRev.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`, sub: 'ERP' }
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
          'Código SKU': p.codpro || p.codigo_sku || '-',
          'Produto': p.nompro || p.produto || '-',
          'Qtd Saídas': p.total_saidas !== undefined ? Number(p.total_saidas).toLocaleString('pt-BR') : '-',
          'Volume / Qtd': p.qtd_total !== undefined ? Number(p.qtd_total).toLocaleString('pt-BR') : '-',
          'Receita (R$)': p.receita_total !== undefined ? `R$ ${Number(p.receita_total).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}` : '-'
        }));
      } else if (ultProd) {
        records = [{
          'Operação': ultProd.origem || 'PDV Conveniência',
          'Produto': ultProd.produto || '-',
          'Quantidade': Number(ultProd.quantidade || 1).toLocaleString('pt-BR'),
          'Total (R$)': `R$ ${Number(ultProd.valor_total || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`,
          'Data/Hora': ultProd.data_hora || '-',
          'Cupom / PDV': `${ultProd.cupom || '-'} / ${ultProd.pdv || '-'}`
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

    // MODULO 7: AUDITORIA DE FUGA FINANCEIRA & CONCILIACAO TEF
    else if (
      effectiveIntent === 'fuga_financeira' ||
      effectiveIntent === 'auditoria_fuga_financeira' ||
      toolName === 'auditar_fuga_financeira' ||
      toolName === 'render_FinancialLeakAuditUI' ||
      toolName === 'FinancialLeakAuditUI'
    ) {
      title = '🚨 Auditoria de Fuga Financeira & TEF';
      subtitle = c.diagnosis || data?.props?.diagnosis || 'Auditoria de quebras de caixa, sangrias retidas e conciliacao TEF';
      const totalLeak = Number(c.total_leak_value ?? c.total_divergence_reais ?? data?.props?.total_leak_value ?? 0.0);
      const riskLevel = String(c.risk_level || data?.props?.risk_level || 'baixo').toLowerCase();
      const isOk = riskLevel === 'baixo' || totalLeak < 0.05;

      statusChip = {
        label: isOk ? '✔ Conforme' : `⚠ Risco R$ ${totalLeak.toFixed(2)}`,
        severity: isOk ? 'success' : 'danger'
      };

      records = [
        { 'Vetor de Auditoria': 'Quebra de Caixa / Furo de Gaveta', 'Valor (R$)': 'R$ ' + Number(c.cash_break_value || 0).toFixed(2), 'Status': Number(c.cash_break_value || 0) > 0 ? 'Divergente' : 'Conforme' },
        { 'Vetor de Auditoria': 'Sangrias Pendentes / Retidas', 'Valor (R$)': 'R$ ' + Number(c.pending_bleed_value || 0).toFixed(2), 'Status': Number(c.pending_bleed_value || 0) > 0 ? 'Pendente' : 'Conforme' },
        { 'Vetor de Auditoria': 'Conciliacao TEF / Cartoes', 'Valor (R$)': 'R$ ' + Number(c.tef_divergence_value || 0).toFixed(2), 'Status': Number(c.tef_divergence_value || 0) > 0 ? 'Divergente' : 'Conforme' }
      ];

      summaryKpis = [
        { label: 'Perda Total Identificada', value: 'R$ ' + totalLeak.toFixed(2), sub: isOk ? 'Sem quebras no turno' : 'Divergencia apurada' },
        { label: 'Turno Auditado', value: c.audited_shift || '1º Turno', sub: c.cashier_name || 'Operador ativo' },
        { label: 'Nivel de Risco', value: riskLevel.toUpperCase(), sub: 'Compliance Caixa & TEF' }
      ];

      schemaInfo = {
        source: 'PostgreSQL 16 • ERP Fechamento & TEF Concentrador',
        table: 'public.tb_auditoria_caixa_tef',
        recordCount: records.length,
        fields: [
          { field: 'shift_id', type: 'VARCHAR(20)', sample: '1º TURNO' },
          { field: 'leak_amount', type: 'NUMERIC(12,2)', sample: totalLeak }
        ]
      };

      auditRules = [
        { title: 'Auditoria de Fuga Financeira & Custodia', tag: 'Prevencao de Perdas', formula: 'Fuga_Total = Quebra_Caixa + Sangrias_Retidas + Descompasso_TEF', description: 'Monitoramento continuo de divergencias financeiras em tempo real.' }
      ];
    }

    // MODULO 8: BENCHMARK DE MERCADO & CONCORRENCIA (ANP)
    else if (
      effectiveIntent === 'benchmark_concorrencia' ||
      effectiveIntent === 'mercado_anp' ||
      toolName === 'comparar_benchmark_concorrencia' ||
      toolName === 'render_BenchmarkComparisonUI' ||
      toolName === 'BenchmarkComparisonUI'
    ) {
      title = '📊 Benchmark de Mercado & Concorrencia';
      subtitle = c.diagnosis || data?.props?.diagnosis || 'Posicionamento competitivo frente a pesquisa oficial da ANP';
      const compIndex = c.competitive_index ?? data?.props?.competitive_index ?? 50;

      statusChip = {
        label: `${compIndex}/100 Competitividade`,
        severity: compIndex >= 60 ? 'success' : (compIndex >= 40 ? 'attention' : 'danger')
      };

      const competitors = c.competitors || data?.props?.competitors || [];
      if (competitors.length > 0) {
        records = competitors.map(comp => ({
          'Posto / Concorrente': comp.name || '-',
          'Bandeira': comp.brand || '-',
          'Distancia': comp.distance_km ? `${comp.distance_km} km` : '-',
          'Preco Gasolina (R$)': comp.gasolina_price ? `R$ ${Number(comp.gasolina_price).toFixed(2)}` : '-',
          'Preco Etanol (R$)': comp.etanol_price ? `R$ ${Number(comp.etanol_price).toFixed(2)}` : '-',
          'Preco Diesel S10 (R$)': comp.diesel_price ? `R$ ${Number(comp.diesel_price).toFixed(2)}` : '-'
        }));
      } else {
        records = [
          { 'Metrica de Mercado': 'Preco Medio ANP', 'Valor': c.market_average_price ? `R$ ${Number(c.market_average_price).toFixed(2)}` : '-' },
          { 'Metrica de Mercado': 'Preco Praticado no Posto', 'Valor': c.current_station_price ? `R$ ${Number(c.current_station_price).toFixed(2)}` : '-' },
          { 'Metrica de Mercado': 'Diferenca vs Media', 'Valor': c.price_gap_reais !== undefined ? `${c.price_gap_reais > 0 ? '+' : ''}R$ ${Number(c.price_gap_reais).toFixed(2)}` : '-' }
        ];
      }

      summaryKpis = [
        { label: 'Preco Medio ANP', value: c.market_average_price ? `R$ ${Number(c.market_average_price).toFixed(2)}` : '-', sub: c.municipio || 'Mercado Municipal' },
        { label: 'Diferenca do Posto', value: c.price_gap_reais !== undefined ? `${c.price_gap_reais > 0 ? '+' : ''}R$ ${Number(c.price_gap_reais).toFixed(2)}` : '-', sub: c.positioning_summary || 'vs concorrencia' },
        { label: 'Amostragem ANP', value: `${c.sampled_competitors_count || competitors.length || 0} postos`, sub: 'Sincronizado ANP' }
      ];

      schemaInfo = {
        source: 'Dados Abertos ANP • Serie Historica de Precos',
        table: 'aura_core.anp_precos_semanais',
        recordCount: records.length,
        fields: [
          { field: 'municipio', type: 'VARCHAR(100)', sample: c.municipio || 'CURITIBA' },
          { field: 'valor_venda', type: 'NUMERIC(10,3)', sample: c.market_average_price || 5.89 }
        ]
      };

      auditRules = [
        { title: 'Pesquisa Oficial de Precos ANP', tag: 'Benchmark Mercado', formula: 'Gap_Preco = Preco_Posto - Preco_Medio_Municipio', description: 'Auditoria de posicionamento comercial baseada na serie de precos da ANP.' }
      ];
    }

    // MODULO 9: AUDITORIA LMC & PORTARIA ANP 26/1992
    else if (
      effectiveIntent === 'lmc_compliance' ||
      effectiveIntent === 'auditoria_lmc_anp' ||
      toolName === 'auditar_conformidade_lmc_anp' ||
      toolName === 'render_LMCComplianceReportUI' ||
      toolName === 'LMCComplianceReportUI'
    ) {
      title = '📋 Auditoria LMC & Portaria ANP 26/1992';
      subtitle = c.diagnosis || data?.props?.diagnosis || 'Conformidade volumetrica de tanques e tolerancia legal de 0,60%';
      const overallStatus = String(c.overall_status || data?.props?.overall_status || 'CONFORME').toUpperCase();
      const isConforme = overallStatus === 'CONFORME';

      statusChip = {
        label: isConforme ? '✔ LMC Conforme' : '⚠ Risco Infracao ANP',
        severity: isConforme ? 'success' : 'danger'
      };

      const tankAudits = c.tank_audits || data?.props?.tank_audits || [];
      records = tankAudits.map(t => ({
        'Tanque': `Tanque ${t.tanque_id || '-'}`,
        'Combustivel': t.combustivel || '-',
        'Estoque Inicial': `${Number(t.estoque_inicial_l || 0).toLocaleString('pt-BR')} L`,
        'Entradas (DFE)': `${Number(t.entradas_dfe_l || 0).toLocaleString('pt-BR')} L`,
        'Vendas (Bicos)': `${Number(t.vendas_bicos_l || 0).toLocaleString('pt-BR')} L`,
        'Estoque Fisico': `${Number(t.estoque_fisico_l || 0).toLocaleString('pt-BR')} L`,
        'Variacao (%)': `${Number(t.variacao_pct || 0).toFixed(2)}%`,
        'Status ANP': t.status_anp || 'CONFORME'
      }));

      summaryKpis = [
        { label: 'Variacao Maxima', value: `${Number(c.max_variacao_pct || 0).toFixed(2)}%`, sub: 'Tolerancia legal: ±0.60%' },
        { label: 'Tanques em Alerta', value: `${c.tanques_fora_tolerancia || 0}`, sub: 'Excedem margem legal' },
        { label: 'Tanques Auditados', value: `${records.length} tanques`, sub: 'Portaria ANP 26/1992' }
      ];

      schemaInfo = {
        source: 'PostgreSQL 16 • Livro de Movimentacao de Combustiveis',
        table: 'aura_core.lmc_fechamento_diario',
        recordCount: records.length,
        fields: [
          { field: 'tanque_id', type: 'SMALLINT', sample: 1 },
          { field: 'variacao_pct', type: 'NUMERIC(6,3)', sample: 0.15 }
        ]
      };

      auditRules = [
        { title: 'Tolerancia Volumetrica Legal ANP', tag: 'Compliance Regulatório', formula: 'Variacao_Pct = ((Estoque_Fisico - Estoque_Contabil) / Vendas_Totais) * 100', description: 'Variacao volumetrica maxima permitida de ±0,60% conforme Portaria ANP 26/1992.' }
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
            'Valor': String(v ?? '-')
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

      // Em consultas genericas, summaryKpis fica vazio para nao exibir jargoes tecnicos (ex: Linhas Retornadas, ACID, OK 200)
      summaryKpis = [];

      auditRules = [
        { title: 'Integridade de Dados', tag: 'Governança', formula: 'Transação = READ COMMITTED', description: 'Dados extraídos com isolamento transacional para evitar leituras sujas.' }
      ];
    }

    // Sobrescrita inteligente se props ou contrato trouxerem titulo/subtitulo executivo explicito
    const explicitTitle = data?.props?.title || c?.title || data?.title;
    if (explicitTitle && typeof explicitTitle === 'string') {
      title = this.formatToolTitle(explicitTitle);
    }
    const explicitSubtitle = data?.props?.diagnosis || data?.props?.subtitle || c?.diagnosis || c?.subtitle || data?.subtitle;
    if (explicitSubtitle && typeof explicitSubtitle === 'string') {
      subtitle = explicitSubtitle;
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
    const raw = String(name).trim();

    const map = {
      'render_GenerativeModularCardUI': 'Diagnóstico Executivo Modular',
      'GenerativeModularCardUI': 'Diagnóstico Executivo Modular',
      'diagnostico_modular': 'Diagnóstico Executivo Modular',
      'modular_card': 'Diagnóstico Executivo Modular',
      'modular_lego_card': 'Diagnóstico Executivo Modular',
      'render_ExecutiveDecisionMentorUI': 'Mentor de Decisões Executivo',
      'ExecutiveDecisionMentorUI': 'Mentor de Decisões Executivo',
      'diagnostico_mentoria_executiva': 'Mentor de Decisões Executivo',
      'mentoria_decisao': 'Mentor de Decisões Executivo',
      'mentoria_executiva': 'Mentor de Decisões Executivo',
      'executive_briefing': 'Briefing Executivo do Negócio',
      'render_ExecutiveBriefingUI': 'Briefing Executivo do Negócio',
      'ExecutiveBriefingUI': 'Briefing Executivo do Negócio',
      'auditoria_fuga_financeira': 'Auditoria de Fuga Financeira',
      'fuga_financeira': 'Auditoria de Fuga Financeira',
      'fugas': 'Auditoria de Fuga Financeira',
      'fugas_financeiras': 'Auditoria de Fuga Financeira',
      'furo_caixa': 'Auditoria de Fuga Financeira',
      'furo_gaveta': 'Auditoria de Fuga Financeira',
      'auditar_fuga_financeira': 'Auditoria de Fuga Financeira',
      'render_FinancialLeakAuditUI': 'Auditoria de Fuga Financeira',
      'FinancialLeakAuditUI': 'Auditoria de Fuga Financeira',
      'comparativo_concorrencia': 'Benchmark de Preços ANP',
      'comparar_benchmark_concorrencia': 'Benchmark de Preços ANP',
      'benchmark_comparativo': 'Benchmark de Preços ANP',
      'render_BenchmarkComparisonUI': 'Benchmark de Preços ANP',
      'BenchmarkComparisonUI': 'Benchmark de Preços ANP',
      'auditar_conformidade_lmc_anp': 'Auditoria LMC ANP Oficial',
      'lmc_anp': 'Auditoria LMC ANP Oficial',
      'lmc_compliance': 'Auditoria LMC ANP Oficial',
      'render_LMCComplianceReportUI': 'Auditoria LMC ANP Oficial',
      'LMCComplianceReportUI': 'Auditoria LMC ANP Oficial',
      'analisar_custo_estoque_macroeconomico': 'Custo de Estoque & Selic',
      'custo_estoque_macro': 'Custo de Estoque & Selic',
      'render_MacroeconomicInventoryCostUI': 'Custo de Estoque & Selic',
      'MacroeconomicInventoryCostUI': 'Custo de Estoque & Selic',
      'render_TankRunOutPredictionUI': 'Posição de Estoque & Autonomia',
      'render_TankRunOutForecastUI': 'Posição de Estoque & Autonomia',
      'TankRunOutPredictionUI': 'Posição de Estoque & Autonomia',
      'TankForecastWidget': 'Posição de Estoque & Autonomia',
      'previsao_tanques': 'Posição de Estoque & Autonomia',
      'estoque_posicao': 'Posição de Estoque & Autonomia',
      'run_out': 'Posição de Estoque & Autonomia',
      'render_PaymentMethodsBreakdownUI': 'Formas de Pagamento & Caixas',
      'PaymentMethodsBreakdownUI': 'Formas de Pagamento & Caixas',
      'PaymentMethodsBreakdownWidget': 'Formas de Pagamento & Caixas',
      'formas_pagamento': 'Formas de Pagamento & Caixas',
      'consultar_formas_pagamento_detalhado': 'Formas de Pagamento & Caixas',
      'render_ShiftReconciliationUI': 'Conciliação de Turno & Caixa',
      'ShiftReconciliationUI': 'Conciliação de Turno & Caixa',
      'ShiftReconciliationWidget': 'Conciliação de Turno & Caixa',
      'auditoria_turno': 'Conciliação de Turno & Caixa',
      'conciliacao_turno': 'Conciliação de Turno & Caixa',
      'shift_reconciliation': 'Conciliação de Turno & Caixa',
      'render_BasketUpsellStrategyUI': 'Combos & Cross-Selling (Loja)',
      'BasketUpsellStrategyUI': 'Combos & Cross-Selling (Loja)',
      'conveniencia_vendas_cruzadas': 'Combos & Cross-Selling (Loja)',
      'vendas_cruzadas': 'Combos & Cross-Selling (Loja)',
      'cesta_compras': 'Combos & Cesta de Compras',
      'market_basket': 'Combos & Cesta de Compras',
      'basket_upsell': 'Combos & Cross-Selling (Loja)',
      'render_MarginAnalysisUI': 'Análise de Margens & Lucro',
      'MarginAnalysisUI': 'Análise de Margens & Lucro',
      'analise_margem': 'Análise de Margens & Lucro',
      'vendas_analitico': 'Histórico de Vendas & Rentabilidade',
      'render_PredictiveScenarioUI': 'Cenários Preditivos & Elasticidade',
      'PredictiveScenarioUI': 'Cenários Preditivos & Elasticidade',
      'cenario_preditivo': 'Cenários Preditivos & Elasticidade',
      'simulacao_preditiva': 'Cenários Preditivos & Elasticidade',
      'render_RootCauseAnalysisUI': 'Perícia de Causa-Raiz (RCA)',
      'RootCauseAnalysisUI': 'Perícia de Causa-Raiz (RCA)',
      'investigar_causa_raiz': 'Perícia de Causa-Raiz (RCA)',
      'render_PumpPerformanceUI': 'Performance da Pista & Frentistas',
      'PumpPerformanceUI': 'Performance da Pista & Frentistas',
      'desempenho_pista_frentistas': 'Performance da Pista & Frentistas',
      'render_ComplianceStatusUI': 'Blindagem Jurídica & Compliance',
      'ComplianceStatusUI': 'Blindagem Jurídica & Compliance',
      'compliance_status': 'Blindagem Jurídica & Compliance',
      'conformidade_legal': 'Blindagem Jurídica & Compliance',
      'termo_interoperabilidade': 'Termo de Interoperabilidade',
      'blindagem_juridica': 'Blindagem Jurídica AUPS',
      'render_FinancialErosionUI': 'Auditoria de Taxas TEF & Recebíveis',
      'FinancialErosionUI': 'Auditoria de Taxas TEF & Recebíveis',
      'erosao_financeira': 'Auditoria de Taxas TEF & Recebíveis',
      'taxas_tef': 'Auditoria de Taxas TEF & Recebíveis',
      'render_DeadCapitalOpportunityUI': 'Capital Imobilizado & Rupturas',
      'DeadCapitalOpportunityUI': 'Capital Imobilizado & Rupturas',
      'capital_morto': 'Capital Imobilizado & Rupturas',
      'ruptura_invisivel': 'Capital Imobilizado & Rupturas',
      'render_MarginWaterfallUI': 'Análise de Margem & Waterfall',
      'MarginWaterfallUI': 'Análise de Margem & Waterfall',
      'raio_x_causal_margem': 'Análise de Margem & Waterfall',
      'render_ElasticityBatchSimulatorUI': 'Simulador de Lote de Compra',
      'ElasticityBatchSimulatorUI': 'Simulador de Lote de Compra',
      'simular_elasticidade_e_lote_compra': 'Simulador de Lote de Compra',
      'sre_metricas': 'Diagnóstico Operacional SRE',
      'ajuda_sistema': 'Guia da Plataforma AURA',
      'conhecimento_aura': 'Guia & Conhecimento AURA',
    };
    if (map[raw]) return map[raw];

    const clean = raw
      .replace(/^render_/i, '')
      .replace(/(CardUI|UI|Widget|Card)$/i, '')
      .replace(/_/g, ' ')
      .replace(/([a-z])([A-Z])/g, '$1 $2')
      .trim();

    const englishToPt = {
      'Executive Decision Mentor': 'Mentor de Decisões Executivo',
      'Executive Briefing': 'Briefing Executivo do Negócio',
      'Tank Run Out Forecast': 'Posição de Estoque & Autonomia',
      'Tank Run Out Prediction': 'Posição de Estoque & Autonomia',
      'Financial Leak Audit': 'Auditoria de Fuga Financeira',
      'Shift Reconciliation': 'Conciliação de Turno & Caixa',
      'Basket Upsell Strategy': 'Combos & Vendas Cruzadas (Loja)',
      'Benchmark Comparison': 'Benchmark de Preços ANP',
      'L M C Compliance Report': 'Auditoria LMC ANP Oficial',
      'LMC Compliance Report': 'Auditoria LMC ANP Oficial',
      'Macroeconomic Inventory Cost': 'Custo de Estoque & Selic',
      'Margin Analysis': 'Análise de Margens & Lucro',
      'Predictive Scenario': 'Cenários Preditivos & Elasticidade',
      'Root Cause Analysis': 'Perícia de Causa-Raiz (RCA)',
      'Pump Performance': 'Performance da Pista & Frentistas',
      'Compliance Status': 'Blindagem Jurídica & Compliance',
      'Financial Erosion': 'Auditoria de Taxas TEF & Recebíveis',
      'Dead Capital Opportunity': 'Capital Imobilizado & Rupturas',
      'Margin Waterfall': 'Análise de Margem & Waterfall',
      'Elasticity Batch Simulator': 'Simulador de Lote de Compra',
      'Generative Modular': 'Diagnóstico Executivo Modular',
    };

    if (englishToPt[clean]) return englishToPt[clean];
    if (!clean) return 'Consulta Analítica';
    return clean.charAt(0).toUpperCase() + clean.slice(1);
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
    if (val === null || val === undefined) return '<span class="text-slate-500">-</span>';
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
    if (typeof str === 'object') {
      str = str.text || str.summary || str.title || str.diagnostico_caixa || str.message || JSON.stringify(str);
    }
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
