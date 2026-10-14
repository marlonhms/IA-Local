/**
 * AURA Automation Coordinator (v1.0.0)
 * Gerencia a Central de Automacoes e Toggles de Monitoramento da AURA.
 * Permite ao gestor comutar a quente o Master Switch de background,
 * configurar horarios de auditoria de turnos e limites de alerta de tanques.
 * Zero travessoes em todo o arquivo.
 */

class AuraAutomationCoordinator {
  constructor() {
    this.modal = null;
    this.currentSettings = null;
    this.isSaving = false;
  }

  /**
   * Inicializa ouvintes de eventos e carrega configuracoes na inicializacao.
   */
  init() {
    this.modal = document.getElementById('aura-automation-modal');
    if (!this.modal) return;

    // Botoes de abertura
    const btnHeader = document.getElementById('btn-open-automations');
    if (btnHeader) {
      btnHeader.addEventListener('click', () => this.openModal());
    }

    const btnSidebar = document.getElementById('sidebar-btn-open-automations');
    if (btnSidebar) {
      btnSidebar.addEventListener('click', () => {
        // Fecha drawer lateral antes se estiver aberto
        if (window.auraApp && typeof window.auraApp.closeSidebar === 'function') {
          window.auraApp.closeSidebar();
        }
        this.openModal();
      });
    }

    // Botao de fechar
    const btnClose = document.getElementById('btn-close-automation-modal');
    if (btnClose) {
      btnClose.addEventListener('click', () => this.closeModal());
    }

    // Clique fora do container (backdrop)
    this.modal.addEventListener('click', (e) => {
      if (e.target === this.modal) {
        this.closeModal();
      }
    });

    // Tecla ESC
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.modal && !this.modal.classList.contains('hidden')) {
        this.closeModal();
      }
    });

    // Master Switch reativo
    const toggleMaster = document.getElementById('toggle-master-automation');
    if (toggleMaster) {
      toggleMaster.addEventListener('change', () => {
        this.applyMasterVisualState(toggleMaster.checked);
      });
    }

    // Botao Salvar
    const btnSave = document.getElementById('btn-save-automations');
    if (btnSave) {
      btnSave.addEventListener('click', () => this.saveSettings());
    }

    // Botao Restaurar Padrao
    const btnReset = document.getElementById('btn-reset-automation-defaults');
    if (btnReset) {
      btnReset.addEventListener('click', () => this.resetDefaults());
    }

    // Carregamento inicial silencioso
    this.fetchSettingsSilently();
  }

  /**
   * Abre o modal executivo e sincroniza os campos com o backend.
   */
  async openModal() {
    if (!this.modal) return;
    this.modal.classList.remove('hidden');
    await this.fetchSettings();
  }

  /**
   * Fecha o modal executivo.
   */
  closeModal() {
    if (!this.modal) return;
    this.modal.classList.add('hidden');
  }

  /**
   * Carrega configuracoes ativas da API e popula o formulario.
   */
  async fetchSettings() {
    try {
      const client = window.auraApi || new AuraApiClient();
      const res = await client.getAutomationSettings();
      if (res && res.settings) {
        this.currentSettings = res.settings;
        this.renderForm(res.settings);
        this.updateBadges(res.settings.master_enabled);
      }
    } catch (err) {
      console.warn('Erro ao carregar configuracoes de automacao:', err);
    }
  }

  /**
   * Carregamento silencioso em background na inicializacao.
   */
  async fetchSettingsSilently() {
    try {
      const client = window.auraApi || new AuraApiClient();
      const res = await client.getAutomationSettings();
      if (res && res.settings) {
        this.currentSettings = res.settings;
        this.updateBadges(res.settings.master_enabled);
      }
    } catch (_) {}
  }

  /**
   * Atualiza o estado visual do container de modulos baseado no Master Switch.
   */
  applyMasterVisualState(isEnabled) {
    const submodules = document.getElementById('automation-submodules');
    const badge = document.getElementById('automation-master-badge');

    if (submodules) {
      if (isEnabled) {
        submodules.classList.remove('opacity-40', 'pointer-events-none');
      } else {
        submodules.classList.add('opacity-40', 'pointer-events-none');
      }
    }

    if (badge) {
      if (isEnabled) {
        badge.textContent = 'ATIVO';
        badge.className = 'px-2 py-0.5 rounded-full text-[10px] font-sans font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40';
      } else {
        badge.textContent = 'DESATIVADO';
        badge.className = 'px-2 py-0.5 rounded-full text-[10px] font-sans font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40';
      }
    }
  }

  /**
   * Preenche os campos do formulario a partir do objeto de configuracao.
   */
  renderForm(s) {
    const setChecked = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.checked = Boolean(val);
    };

    const setValue = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.value = val !== undefined && val !== null ? val : '';
    };

    // Master
    setChecked('toggle-master-automation', s.master_enabled);
    this.applyMasterVisualState(s.master_enabled);

    // Turnos
    const shift = s.shift_audit || {};
    setChecked('toggle-shift-audit', shift.enabled);
    setValue('input-shift-schedules', Array.isArray(shift.schedules) ? shift.schedules.join(', ') : '06:05, 14:05, 22:05');
    setValue('input-shift-tolerance', shift.cash_tolerance_reais || 50.0);

    // Tanques
    const tank = s.tank_alerts || {};
    setChecked('toggle-tank-alerts', tank.enabled);
    setValue('input-tank-min-hours', tank.min_autonomy_hours || 12);
    setValue('input-tank-min-percent', tank.min_volume_percentage || 15.0);
    setValue('input-tank-interval', tank.check_interval_minutes || 60);

    // Pista & Bicos
    const pumps = s.pumps_audit || {};
    setChecked('toggle-pumps-audit', pumps.enabled);
    setChecked('toggle-pump-slow-flow', pumps.alert_slow_flow !== false);
    setChecked('toggle-pump-encerrante', pumps.alert_encerrante_divergence !== false);

    // Canais
    const notif = s.notifications || {};
    setChecked('toggle-channel-web', notif.web_banner !== false);
    setChecked('toggle-channel-webhook', notif.webhook_enabled);
    setValue('input-channel-webhook-url', notif.webhook_url || '');
  }

  /**
   * Coleta os dados do formulario e monta o payload estruturado.
   */
  collectPayload() {
    const getChecked = (id) => {
      const el = document.getElementById(id);
      return el ? Boolean(el.checked) : false;
    };

    const getValue = (id, fallback = '') => {
      const el = document.getElementById(id);
      return el ? el.value.trim() : fallback;
    };

    const getNumber = (id, fallback = 0) => {
      const el = document.getElementById(id);
      const val = el ? parseFloat(el.value) : NaN;
      return isNaN(val) ? fallback : val;
    };

    // Parse de horarios de turnos
    const schedulesRaw = getValue('input-shift-schedules', '06:05, 14:05, 22:05');
    const schedulesList = schedulesRaw
      .split(',')
      .map(s => s.trim())
      .filter(s => /^\d{2}:\d{2}$/.test(s));

    return {
      master_enabled: getChecked('toggle-master-automation'),
      shift_audit: {
        enabled: getChecked('toggle-shift-audit'),
        schedules: schedulesList.length > 0 ? schedulesList : ['06:05', '14:05', '22:05'],
        notify_cash_divergence: true,
        cash_tolerance_reais: getNumber('input-shift-tolerance', 50.0),
      },
      tank_alerts: {
        enabled: getChecked('toggle-tank-alerts'),
        min_autonomy_hours: parseInt(getNumber('input-tank-min-hours', 12), 10),
        min_volume_percentage: getNumber('input-tank-min-percent', 15.0),
        check_interval_minutes: parseInt(getNumber('input-tank-interval', 60), 10),
      },
      pumps_audit: {
        enabled: getChecked('toggle-pumps-audit'),
        alert_slow_flow: getChecked('toggle-pump-slow-flow'),
        alert_encerrante_divergence: getChecked('toggle-pump-encerrante'),
      },
      notifications: {
        web_banner: getChecked('toggle-channel-web'),
        webhook_enabled: getChecked('toggle-channel-webhook'),
        webhook_url: getValue('input-channel-webhook-url'),
      },
    };
  }

  /**
   * Salva as configuracoes no backend via API.
   */
  async saveSettings() {
    if (this.isSaving) return;
    this.isSaving = true;

    const btnSave = document.getElementById('btn-save-automations');
    const statusText = document.getElementById('automation-save-status');

    if (btnSave) {
      btnSave.disabled = true;
      btnSave.classList.add('opacity-60');
    }

    if (statusText) {
      statusText.textContent = 'Salvando preferências...';
      statusText.classList.remove('hidden', 'text-rose-400');
      statusText.classList.add('text-slate-400');
    }

    try {
      const payload = this.collectPayload();
      const client = window.auraApi || new AuraApiClient();
      const res = await client.updateAutomationSettings(payload);

      if (res && res.settings) {
        this.currentSettings = res.settings;
        this.renderForm(res.settings);
        this.updateBadges(res.settings.master_enabled);

        if (statusText) {
          statusText.textContent = 'Configurações salvas!';
          statusText.className = 'text-[11px] text-emerald-400 font-sans';
        }

        // Feedback sonoro se SFX estiver ativado
        if (window.auraAudio && typeof window.auraAudio.playChime === 'function') {
          window.auraAudio.playChime(780, 0.08);
        }

        setTimeout(() => {
          if (statusText) statusText.classList.add('hidden');
        }, 3000);
      }
    } catch (err) {
      console.error('Falha ao salvar configuracoes de automacao:', err);
      if (statusText) {
        statusText.textContent = `Erro: ${err.message}`;
        statusText.className = 'text-[11px] text-rose-400 font-sans';
      }
    } finally {
      this.isSaving = false;
      if (btnSave) {
        btnSave.disabled = false;
        btnSave.classList.remove('opacity-60');
      }
    }
  }

  /**
   * Restaura valores padrao recomendados (100% sob demanda).
   */
  resetDefaults() {
    const defaults = {
      master_enabled: false,
      shift_audit: {
        enabled: false,
        schedules: ['06:05', '14:05', '22:05'],
        notify_cash_divergence: true,
        cash_tolerance_reais: 50.0,
      },
      tank_alerts: {
        enabled: false,
        min_autonomy_hours: 12,
        min_volume_percentage: 15.0,
        check_interval_minutes: 60,
      },
      pumps_audit: {
        enabled: false,
        alert_slow_flow: true,
        alert_encerrante_divergence: true,
      },
      notifications: {
        web_banner: true,
        webhook_enabled: false,
        webhook_url: '',
      },
    };

    this.renderForm(defaults);

    const statusText = document.getElementById('automation-save-status');
    if (statusText) {
      statusText.textContent = 'Valores padrão carregados. Clique em Salvar para aplicar.';
      statusText.className = 'text-[11px] text-cyan-400 font-sans';
      statusText.classList.remove('hidden');
    }
  }

  /**
   * Atualiza badges visuais no header e na sidebar.
   */
  updateBadges(isMasterActive) {
    // Dot no header
    const headerDot = document.getElementById('header-automation-status-dot');
    if (headerDot) {
      if (isMasterActive) {
        headerDot.className = 'w-2 h-2 rounded-full bg-emerald-400 animate-pulse';
        headerDot.title = 'Monitoramento Automático: Ativo';
      } else {
        headerDot.className = 'w-2 h-2 rounded-full bg-slate-500';
        headerDot.title = 'Monitoramento Automático: Desativado (100% sob demanda)';
      }
    }

    // Badge no menu lateral
    const sidebarBadge = document.getElementById('sidebar-automation-badge');
    if (sidebarBadge) {
      if (isMasterActive) {
        sidebarBadge.textContent = 'Ativo';
        sidebarBadge.className = 'px-2 py-0.5 rounded text-[10px] font-sans font-medium bg-emerald-500/20 text-emerald-400 border border-emerald-500/30';
      } else {
        sidebarBadge.textContent = 'Inativo';
        sidebarBadge.className = 'px-2 py-0.5 rounded text-[10px] font-sans font-medium bg-slate-800 text-slate-400 border border-slate-700/50';
      }
    }
  }
}

// Instancia global
window.auraAutomations = new AuraAutomationCoordinator();

// Inicializacao quando o DOM estiver pronto
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => window.auraAutomations.init());
} else {
  window.auraAutomations.init();
}

// Exportacao CommonJS para testes headless (Node.js)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { AuraAutomationCoordinator };
}
