/**
 * AURA Compliance & Interoperability Coordinator (v1.1.0)
 * Gerencia a Central de Conformidade Legal, Opt-In do Lojista e Blindagem Juridica (LGPD).
 * Permite visualizar o Termo de Interoperabilidade v1.1, conferir hashes criptograficos,
 * auditar os parametros tecnicos do driver shield e formalizar o opt-in em 1 clique.
 * Zero travessoes em todo o arquivo.
 */

class AuraComplianceCoordinator {
  constructor() {
    this.modal = null;
    this.currentStatus = null;
    this.termData = null;
    this.isSubmitting = false;
    this.activeTab = 'overview'; // 'overview' | 'term'
  }

  /**
   * Inicializa ouvintes de eventos e vincula pontos de entrada da interface.
   */
  init() {
    this.modal = document.getElementById('aura-compliance-modal');
    if (!this.modal) return;

    // 1. Botao no cabecalho (Header)
    const btnHeader = document.getElementById('btn-open-compliance');
    if (btnHeader) {
      btnHeader.addEventListener('click', () => this.openModal());
    }

    // 2. Item no menu lateral (Sidebar Drawer)
    const btnSidebar = document.getElementById('sidebar-btn-open-compliance');
    if (btnSidebar) {
      btnSidebar.addEventListener('click', () => {
        if (window.auraApp && typeof window.auraApp.closeSidebar === 'function') {
          window.auraApp.closeSidebar();
        }
        this.openModal();
      });
    }

    // 3. Botao de fechar (X)
    const btnClose = document.getElementById('btn-close-compliance-modal');
    if (btnClose) {
      btnClose.addEventListener('click', () => this.closeModal());
    }

    // 4. Fechamento ao clicar fora (backdrop)
    this.modal.addEventListener('click', (e) => {
      if (e.target === this.modal) {
        this.closeModal();
      }
    });

    // 5. Tecla Escape
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.modal && !this.modal.classList.contains('hidden')) {
        this.closeModal();
      }
    });

    // 6. Tabs internas do modal
    const tabOverview = document.getElementById('compliance-tab-btn-overview');
    const tabTerm = document.getElementById('compliance-tab-btn-term');
    if (tabOverview) {
      tabOverview.addEventListener('click', () => this.switchTab('overview'));
    }
    if (tabTerm) {
      tabTerm.addEventListener('click', () => this.switchTab('term'));
    }

    // 7. Botao de submissao do Opt-In
    const btnOptIn = document.getElementById('btn-submit-compliance-optin');
    if (btnOptIn) {
      btnOptIn.addEventListener('click', () => this.submitOptIn());
    }

    // 8. Botao de copiar Hash SHA-256
    const btnCopyHash = document.getElementById('btn-copy-term-hash');
    if (btnCopyHash) {
      btnCopyHash.addEventListener('click', () => this.copyTermHash());
    }

    // 9. Botao de copiar texto integral do Termo
    const btnCopyTerm = document.getElementById('btn-copy-term-content');
    if (btnCopyTerm) {
      btnCopyTerm.addEventListener('click', () => this.copyTermContent());
    }

    // 10. Carregamento inicial silencioso de status para atualizar badges
    this.fetchStatusSilently();
  }

  /**
   * Abre o modal executivo de conformidade e sincroniza dados em tempo real.
   */
  async openModal() {
    if (!this.modal) return;
    this.modal.classList.remove('hidden');
    this.switchTab(this.activeTab);
    await Promise.all([
      this.fetchComplianceStatus(),
      this.fetchTermContent()
    ]);
  }

  /**
   * Fecha o modal executivo de conformidade.
   */
  closeModal() {
    if (!this.modal) return;
    this.modal.classList.add('hidden');
  }

  /**
   * Comuta entre a aba de visao geral/blindagem e a aba do termo integral.
   */
  switchTab(tabName) {
    this.activeTab = tabName;
    const viewOverview = document.getElementById('compliance-view-overview');
    const viewTerm = document.getElementById('compliance-view-term');
    const btnOverview = document.getElementById('compliance-tab-btn-overview');
    const btnTerm = document.getElementById('compliance-tab-btn-term');

    if (tabName === 'term') {
      if (viewOverview) viewOverview.classList.add('hidden');
      if (viewTerm) viewTerm.classList.remove('hidden');

      if (btnOverview) {
        btnOverview.classList.remove('border-cyan-500', 'text-cyan-300', 'bg-cyan-500/10');
        btnOverview.classList.add('border-transparent', 'text-slate-400', 'hover:text-white');
      }
      if (btnTerm) {
        btnTerm.classList.add('border-cyan-500', 'text-cyan-300', 'bg-cyan-500/10');
        btnTerm.classList.remove('border-transparent', 'text-slate-400');
      }
    } else {
      if (viewOverview) viewOverview.classList.remove('hidden');
      if (viewTerm) viewTerm.classList.add('hidden');

      if (btnOverview) {
        btnOverview.classList.add('border-cyan-500', 'text-cyan-300', 'bg-cyan-500/10');
        btnOverview.classList.remove('border-transparent', 'text-slate-400');
      }
      if (btnTerm) {
        btnTerm.classList.remove('border-cyan-500', 'text-cyan-300', 'bg-cyan-500/10');
        btnTerm.classList.add('border-transparent', 'text-slate-400', 'hover:text-white');
      }
    }
  }

  /**
   * Carrega status de conformidade da API e renderiza a visao geral.
   */
  async fetchComplianceStatus() {
    try {
      const client = window.auraApi || new AuraApiClient();
      const res = await client.getComplianceStatus();
      if (res) {
        this.currentStatus = res;
        this.renderStatus(res);
      }
    } catch (err) {
      console.warn('Erro ao carregar status de conformidade:', err);
    }
  }

  /**
   * Carrega o texto integral do termo e o hash SHA-256.
   */
  async fetchTermContent() {
    try {
      const client = window.auraApi || new AuraApiClient();
      const res = await client.getComplianceTerm();
      if (res) {
        this.termData = res;
        this.renderTerm(res);
      }
    } catch (err) {
      console.warn('Erro ao carregar termo de conformidade:', err);
    }
  }

  /**
   * Carregamento silencioso em background na inicializacao.
   */
  async fetchStatusSilently() {
    try {
      const client = window.auraApi || new AuraApiClient();
      const res = await client.getComplianceStatus();
      if (res) {
        this.currentStatus = res;
        this.updateHeaderAndSidebarBadges(res.compliant);
      }
    } catch (_) {}
  }

  /**
   * Renderiza os dados de status na interface do modal.
   */
  renderStatus(data) {
    const isCompliant = data.compliant && data.status !== 'pending' && data.status !== 'revoked';

    // Badge principal no topo do modal
    const masterBadge = document.getElementById('compliance-master-badge');
    if (masterBadge) {
      if (isCompliant) {
        masterBadge.textContent = '100% CONFORME & BLINDADO';
        masterBadge.className = 'px-2.5 py-1 rounded-full text-[10px] font-sans font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40';
      } else {
        masterBadge.textContent = 'PENDENTE DE ACEITE';
        masterBadge.className = 'px-2.5 py-1 rounded-full text-[10px] font-sans font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40';
      }
    }

    // Campos cadastrais
    const elCnpj = document.getElementById('compliance-field-cnpj');
    if (elCnpj) elCnpj.textContent = data.loja_cnpj || '00.000.000/0001-00';

    const elRazao = document.getElementById('compliance-field-razao');
    if (elRazao) elRazao.textContent = data.razao_social || 'Auto Posto S/A';

    const elVersao = document.getElementById('compliance-field-versao');
    if (elVersao) elVersao.textContent = `v${data.versao_termo || '1.1'}`;

    const elAssinante = document.getElementById('compliance-field-assinante');
    if (elAssinante) {
      elAssinante.textContent = data.assinado_por || (isCompliant ? 'Representante Legal Homologado' : 'Aguardando Formalização');
    }

    const elDataAceite = document.getElementById('compliance-field-data-aceite');
    if (elDataAceite) {
      elDataAceite.textContent = data.aceite_interoperabilidade_em
        ? new Date(data.aceite_interoperabilidade_em).toLocaleString('pt-BR')
        : 'Pendente de formalização';
    }

    const elHash = document.getElementById('compliance-field-hash');
    if (elHash) {
      const h = data.hash_termo || data.hash_atual_termo || '';
      elHash.textContent = h ? `${h.substring(0, 24)}...` : 'Calculando...';
      elHash.title = h;
    }

    // Banner de formalizacao (se pendente)
    const formContainer = document.getElementById('compliance-optin-form-container');
    const signedContainer = document.getElementById('compliance-optin-signed-banner');

    if (isCompliant) {
      if (formContainer) formContainer.classList.add('hidden');
      if (signedContainer) signedContainer.classList.remove('hidden');
    } else {
      if (formContainer) formContainer.classList.remove('hidden');
      if (signedContainer) signedContainer.classList.add('hidden');

      // Preenche o campo de representante se vazio
      const inputSigner = document.getElementById('compliance-input-signer');
      if (inputSigner && !inputSigner.value) {
        inputSigner.value = 'Marlon / Diretor Operacional';
      }
    }

    // Atualiza badges no shell
    this.updateHeaderAndSidebarBadges(isCompliant);
  }

  /**
   * Renderiza o conteudo textual do termo na aba correspondente.
   */
  renderTerm(termData) {
    const elPre = document.getElementById('compliance-term-text');
    if (elPre && termData.content_markdown) {
      elPre.textContent = termData.content_markdown;
    }

    const elHashFull = document.getElementById('compliance-term-hash-full');
    if (elHashFull && termData.hash_sha256) {
      elHashFull.textContent = termData.hash_sha256;
    }
  }

  /**
   * Atualiza badges visuais no header e no menu lateral.
   */
  updateHeaderAndSidebarBadges(isCompliant) {
    const headerPill = document.getElementById('header-compliance-pill');
    if (headerPill) {
      if (isCompliant) {
        headerPill.innerHTML = '<span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span><span>Blindagem v1.1 Ativa</span>';
        headerPill.className = 'hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-sans font-medium bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 cursor-pointer hover:bg-emerald-500/20 transition-all';
      } else {
        headerPill.innerHTML = '<span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span><span>Opt-In Pendente</span>';
        headerPill.className = 'hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-sans font-medium bg-amber-500/10 text-amber-300 border border-amber-500/30 cursor-pointer hover:bg-amber-500/20 transition-all';
      }
    }

    const sidebarBadge = document.getElementById('sidebar-compliance-badge');
    if (sidebarBadge) {
      if (isCompliant) {
        sidebarBadge.textContent = 'v1.1 Ativo';
        sidebarBadge.className = 'px-1.5 py-0.5 rounded text-[10px] font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
      } else {
        sidebarBadge.textContent = 'Pendente';
        sidebarBadge.className = 'px-1.5 py-0.5 rounded text-[10px] font-mono bg-amber-500/20 text-amber-300 border border-amber-500/30';
      }
    }
  }

  /**
   * Submete o Opt-In formal de interoperabilidade via POST /api/v1/aura/compliance/opt-in.
   */
  async submitOptIn() {
    if (this.isSubmitting) return;

    const inputSigner = document.getElementById('compliance-input-signer');
    const signerName = inputSigner ? inputSigner.value.trim() : '';

    if (!signerName) {
      alert('Por favor, informe o nome e cargo do representante legal que autoriza o opt-in.');
      if (inputSigner) inputSigner.focus();
      return;
    }

    const checkConfirm = document.getElementById('compliance-check-confirm');
    if (checkConfirm && !checkConfirm.checked) {
      alert('Por favor, assinale a confirmacao de ciencia dos termos de interoperabilidade.');
      checkConfirm.focus();
      return;
    }

    const btnSubmit = document.getElementById('btn-submit-compliance-optin');
    const origHtml = btnSubmit ? btnSubmit.innerHTML : '';

    try {
      this.isSubmitting = true;
      if (btnSubmit) {
        btnSubmit.disabled = true;
        btnSubmit.innerHTML = '<span>Formalizando Aceite...</span>';
      }

      const client = window.auraApi || new AuraApiClient();
      const cnpj = (this.currentStatus && this.currentStatus.loja_cnpj) || '00.000.000/0001-00';
      const razao = (this.currentStatus && this.currentStatus.razao_social) || 'Auto Posto S/A';

      const payload = {
        loja_cnpj: cnpj,
        razao_social: razao,
        assinado_por: signerName,
        versao_termo: '1.1',
        metadata: {
          origem: 'painel_web_optin',
          ip_local: '127.0.0.1',
          navegador: navigator.userAgent || 'AURA Web Shell',
          data_submissao: new Date().toISOString()
        }
      };

      const res = await client.registerComplianceOptIn(payload);

      if (res && res.status === 'ok') {
        // Exibe toast de sucesso
        this.showToast('Opt-in formalizado com sucesso! Blindagem v1.1 ativa.', 'success');
        await this.fetchComplianceStatus();
      }
    } catch (err) {
      console.error('Falha ao formalizar opt-in:', err);
      alert(`Falha ao registrar opt-in de conformidade: ${err.message}`);
    } finally {
      this.isSubmitting = false;
      if (btnSubmit) {
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = origHtml;
      }
    }
  }

  /**
   * Copia o Hash SHA-256 do termo para a area de transferencia.
   */
  copyTermHash() {
    const hash = (this.termData && this.termData.hash_sha256) ||
                 (this.currentStatus && (this.currentStatus.hash_termo || this.currentStatus.hash_atual_termo)) || '';
    if (!hash) return;

    navigator.clipboard.writeText(hash).then(() => {
      this.showToast('Hash SHA-256 copiado para a área de transferência!', 'success');
    });
  }

  /**
   * Copia o conteudo integral do termo em markdown para a area de transferencia.
   */
  copyTermContent() {
    const content = this.termData && this.termData.content_markdown;
    if (!content) return;

    navigator.clipboard.writeText(content).then(() => {
      this.showToast('Texto integral do Termo copiado com sucesso!', 'success');
    });
  }

  /**
   * Exibe toast simples e elegante.
   */
  showToast(msg, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl font-sans text-xs shadow-2xl flex items-center gap-2 border transition-all transform translate-y-2 opacity-0 ${
      type === 'success'
        ? 'bg-slate-900 text-emerald-300 border-emerald-500/40'
        : 'bg-slate-900 text-cyan-300 border-cyan-500/40'
    }`;
    toast.innerHTML = `<span>🛡️</span><span>${msg}</span>`;
    document.body.appendChild(toast);

    requestAnimationFrame(() => {
      toast.classList.remove('translate-y-2', 'opacity-0');
      toast.classList.add('translate-y-0', 'opacity-100');
    });

    setTimeout(() => {
      toast.classList.remove('translate-y-0', 'opacity-100');
      toast.classList.add('translate-y-2', 'opacity-0');
      setTimeout(() => toast.remove(), 300);
    }, 3200);
  }
}

// 1. Exportacao Global no Navegador
if (typeof window !== 'undefined') {
  window.AuraComplianceCoordinator = AuraComplianceCoordinator;
  window.auraCompliance = new AuraComplianceCoordinator();

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      if (window.auraCompliance) window.auraCompliance.init();
    });
  } else {
    window.auraCompliance.init();
  }
}

// 2. Exportacao CommonJS para testes automatizados headless (Node.js)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    AuraComplianceCoordinator
  };
}
