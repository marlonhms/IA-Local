/**
 * AURA Domain Theme Adapter (Fase P1-UI5: Shell Executivo Domain-Agnostic)
 * Adapta titulos, badges, placeholders e contexto operacional conforme o pack_id ativo,
 * preservando integralmente os visuais especializados quando fuel_convenience esta em uso.
 * 100% das chamadas roteadas pelo window.auraApi (AuraHttpTransport).
 * Zero travessoes em todo o arquivo.
 */
(function (root) {
  'use strict';

  const DOMAIN_PACKS = {
    fuel_convenience: {
      packId: 'fuel_convenience',
      badgeLabel: 'Combustiveis & Conveniencia',
      docTitle: 'AURA // Assistente de Prontidao (Gerente Supervisora do Posto)',
      sidebarSubtitle: 'Menu Executivo do Posto',
      consoleHeaderLabel: 'Console Conversacional',
      defaultFilialLabel: 'ANALISE TECNICA REVENDA',
      composerPlaceholder: 'Pergunte sobre tanques, fechamento de turno, LMC ou margem...',
      welcomeLeadHtml: 'Ola! Sou a <strong>AURA</strong>. Este e o resumo do seu posto antes mesmo de voce perguntar.',
      cockpitTitle: 'Prontidao do posto agora',
      cockpitLoadingMeta: 'Lendo dados do posto...',
      cockpitSourceLabel: 'leitura somente leitura do sistema do posto',
      initialReasoningLabel: 'Consultando telemetria operacional...',
      indicators: {
        tanques: {
          label: 'Reserva de Tanques',
          prompt: 'Qual a situacao e autonomia de cada tanque agora?',
          hint: 'Toque para consultar a autonomia de cada tanque.'
        },
        turno: {
          label: 'Conciliacao do Turno',
          prompt: 'Como fechou o ultimo turno? Teve furo de caixa?',
          hint: 'Toque para ver como fechou o ultimo turno.'
        },
        lmc: {
          label: 'Conformidade LMC',
          prompt: 'O LMC esta dentro da tolerancia oficial de 0,6% da ANP?',
          hint: 'Toque para auditar o LMC frente a tolerancia da ANP.'
        }
      }
    },
    pharmacy_health: {
      packId: 'pharmacy_health',
      badgeLabel: 'Farmacia & Saude',
      docTitle: 'AURA // Copiloto Executivo (Gestao Farmaceutica)',
      sidebarSubtitle: 'Menu Executivo da Farmacia',
      consoleHeaderLabel: 'Console Farmaceutico & PBM',
      defaultFilialLabel: 'UNIDADE FARMACIA',
      composerPlaceholder: 'Pergunte sobre ruptura curva A, fechamento PBM/caixa, SNGPC ou margem...',
      welcomeLeadHtml: 'Ola! Sou a <strong>AURA</strong>. Este e o resumo da sua farmacia antes mesmo de voce perguntar.',
      cockpitTitle: 'Prontidao da farmacia agora',
      cockpitLoadingMeta: 'Lendo dados da farmacia...',
      cockpitSourceLabel: 'leitura somente leitura do ERP farmaceutico',
      initialReasoningLabel: 'Consultando indicadores de estoque e PBM...',
      indicators: {
        tanques: {
          label: 'Ruptura Curva A',
          prompt: 'Quais itens da Curva A estao com risco de ruptura ou validade proxima?',
          hint: 'Toque para auditar ruptura e estoque critico.'
        },
        turno: {
          label: 'Fechamento PBM/Caixa',
          prompt: 'Como fechou o ultimo turno de caixa e repasses PBM?',
          hint: 'Toque para auditar fechamento de caixa e PBM.'
        },
        lmc: {
          label: 'Conformidade SNGPC',
          prompt: 'Qual o status de conformidade SNGPC e controlados hoje?',
          hint: 'Toque para verificar conformidade regulatoria.'
        }
      }
    },
    retail_supermarket: {
      packId: 'retail_supermarket',
      badgeLabel: 'Varejo & Supermercado',
      docTitle: 'AURA // Copiloto Executivo (Gestao de Varejo)',
      sidebarSubtitle: 'Menu Executivo da Loja',
      consoleHeaderLabel: 'Console de Operacao de Loja',
      defaultFilialLabel: 'LOJA VAREJO',
      composerPlaceholder: 'Pergunte sobre ruptura de gondolas, quebra de caixa, margem ou giro...',
      welcomeLeadHtml: 'Ola! Sou a <strong>AURA</strong>. Este e o resumo da sua loja antes mesmo de voce perguntar.',
      cockpitTitle: 'Prontidao da loja agora',
      cockpitLoadingMeta: 'Lendo dados da loja...',
      cockpitSourceLabel: 'leitura somente leitura do ERP da loja',
      initialReasoningLabel: 'Consultando indicadores de loja e PDV...',
      indicators: {
        tanques: {
          label: 'Ruptura de Gondola',
          prompt: 'Quais categorias ou SKUs apresentam maior risco de ruptura hoje?',
          hint: 'Toque para consultar risco de ruptura de estoque.'
        },
        turno: {
          label: 'Conciliacao PDV',
          prompt: 'Como fechou o ultimo turno dos caixas PDV? Houve divergencia?',
          hint: 'Toque para auditar fechamento de PDV.'
        },
        lmc: {
          label: 'Conformidade Fiscal',
          prompt: 'Ha divergencias fiscais ou alertas de NFC-e no periodo?',
          hint: 'Toque para auditar conformidade fiscal.'
        }
      }
    },
    autocenter_parts: {
      packId: 'autocenter_parts',
      badgeLabel: 'Autocenter & Pecas',
      docTitle: 'AURA // Copiloto Executivo (Autocenter & Servicos)',
      sidebarSubtitle: 'Menu Executivo do Autocenter',
      consoleHeaderLabel: 'Console de Oficina & Pecas',
      defaultFilialLabel: 'UNIDADE AUTOCENTER',
      composerPlaceholder: 'Pergunte sobre estoque de pecas, ordens de servico, caixa ou margem...',
      welcomeLeadHtml: 'Ola! Sou a <strong>AURA</strong>. Este e o resumo do seu autocenter antes mesmo de voce perguntar.',
      cockpitTitle: 'Prontidao do autocenter agora',
      cockpitLoadingMeta: 'Lendo dados do autocenter...',
      cockpitSourceLabel: 'leitura somente leitura do ERP de oficina',
      initialReasoningLabel: 'Consultando ordens de servico e estoque...',
      indicators: {
        tanques: {
          label: 'Estoque de Pecas',
          prompt: 'Quais pecas de alto giro estao abaixo do ponto de pedido?',
          hint: 'Toque para consultar estoque critico de pecas.'
        },
        turno: {
          label: 'Fechamento OS & Caixa',
          prompt: 'Como fechou o faturamento de OS e caixa no ultimo turno?',
          hint: 'Toque para auditar fechamento de OS e caixa.'
        },
        lmc: {
          label: 'Conformidade Fiscal',
          prompt: 'Ha pendencias de NF-e, NFS-e ou tributacao de pecas?',
          hint: 'Toque para verificar conformidade fiscal.'
        }
      }
    },
    wholesale_distribution: {
      packId: 'wholesale_distribution',
      badgeLabel: 'Atacado & Distribuicao',
      docTitle: 'AURA // Copiloto Executivo (Atacado & Distribuicao)',
      sidebarSubtitle: 'Menu Executivo da Distribuidora',
      consoleHeaderLabel: 'Console de Distribuicao & Margem',
      defaultFilialLabel: 'CENTRO DE DISTRIBUICAO',
      composerPlaceholder: 'Pergunte sobre cobertura de estoque, carteira B2B, margem ou fiscal...',
      welcomeLeadHtml: 'Ola! Sou a <strong>AURA</strong>. Este e o resumo da sua operacao antes mesmo de voce perguntar.',
      cockpitTitle: 'Prontidao da operacao agora',
      cockpitLoadingMeta: 'Lendo dados da distribuidora...',
      cockpitSourceLabel: 'leitura somente leitura do ERP corporativo',
      initialReasoningLabel: 'Consultando estoque B2B e faturamento...',
      indicators: {
        tanques: {
          label: 'Cobertura de Estoque',
          prompt: 'Quais linhas de produto estao com cobertura critica de estoque?',
          hint: 'Toque para consultar cobertura de estoque.'
        },
        turno: {
          label: 'Faturamento & Caixa',
          prompt: 'Como fechou o faturamento e conciliacao financeira do ultimo ciclo?',
          hint: 'Toque para auditar faturamento e recebiveis.'
        },
        lmc: {
          label: 'Conformidade NF-e',
          prompt: 'Existem alertas de tributacao, ST ou rejeicoes NF-e no periodo?',
          hint: 'Toque para auditar conformidade fiscal.'
        }
      }
    }
  };

  class AuraDomainThemeAdapter {
    constructor() {
      this.activePackId = 'fuel_convenience';
      this.activeProfile = DOMAIN_PACKS.fuel_convenience;
      this.initialized = false;
    }

    getProfile(packId) {
      const key = String(packId || this.activePackId || 'fuel_convenience').trim().toLowerCase();
      return DOMAIN_PACKS[key] || DOMAIN_PACKS.fuel_convenience;
    }

    getActivePackId() {
      return this.activePackId;
    }

    isFuelDomain() {
      return this.activePackId === 'fuel_convenience';
    }

    getInitialReasoningLabel() {
      return this.activeProfile.initialReasoningLabel;
    }

    async detectAndApply() {
      let resolvedPack = null;

      // 1. Permite override explicito via query param ?pack= ou localStorage para homologacao
      if (typeof window !== 'undefined' && window.location) {
        try {
          const params = new URLSearchParams(window.location.search || '');
          const qPack = params.get('pack') || params.get('pack_id');
          if (qPack && DOMAIN_PACKS[qPack.toLowerCase()]) {
            resolvedPack = qPack.toLowerCase();
          }
        } catch (_) {}
      }

      // 2. Consulta /api/v1/aura/stations via AuraHttpTransport (window.auraApi)
      if (!resolvedPack && root.auraApi && typeof root.auraApi.getStations === 'function') {
        try {
          const stations = await root.auraApi.getStations();
          const first = Array.isArray(stations) ? stations[0] : stations;
          const candidate = first && (first.pack_id || first.domain_pack || first.vertical);
          if (candidate && DOMAIN_PACKS[String(candidate).toLowerCase()]) {
            resolvedPack = String(candidate).toLowerCase();
          }
        } catch (_) {}
      }

      // 3. Fallback para /api/v1/aura/health via AuraHttpTransport
      if (!resolvedPack && root.auraApi && typeof root.auraApi.getHealth === 'function') {
        try {
          const health = await root.auraApi.getHealth();
          const candidate = health && (health.pack_id || health.domain_pack);
          if (candidate && DOMAIN_PACKS[String(candidate).toLowerCase()]) {
            resolvedPack = String(candidate).toLowerCase();
          }
        } catch (_) {}
      }

      this.applyPack(resolvedPack || 'fuel_convenience');
      return this.activePackId;
    }

    applyPack(packId) {
      const profile = this.getProfile(packId);
      this.activePackId = profile.packId;
      this.activeProfile = profile;

      if (typeof document === 'undefined') return profile;

      document.documentElement.setAttribute('data-domain-pack', profile.packId);
      if (document.body) {
        document.body.setAttribute('data-domain-pack', profile.packId);
      }

      // Preserva intactos os textos originais quando fuel_convenience esta ativo
      if (profile.packId === 'fuel_convenience') {
        return profile;
      }

      document.title = profile.docTitle;

      const sidebarSub = document.getElementById('sidebar-domain-subtitle');
      if (sidebarSub) sidebarSub.textContent = profile.sidebarSubtitle;

      const consoleHeader = document.getElementById('console-domain-header-label');
      if (consoleHeader) consoleHeader.textContent = profile.consoleHeaderLabel;

      const hudFilial = document.getElementById('hud-filial-name');
      if (hudFilial && (!hudFilial.textContent || hudFilial.textContent.trim() === 'ANALISE TECNICA REVENDA')) {
        hudFilial.textContent = profile.defaultFilialLabel;
      }

      const composer = document.getElementById('chat-input-text');
      if (composer) {
        composer.setAttribute('placeholder', profile.composerPlaceholder);
      }

      const welcomeLead = document.getElementById('welcome-greeting-lead');
      if (welcomeLead) {
        welcomeLead.innerHTML = profile.welcomeLeadHtml;
      }

      const cockpitTitle = document.getElementById('welcome-cockpit-title');
      if (cockpitTitle) {
        cockpitTitle.textContent = profile.cockpitTitle;
      }

      const cockpit = document.getElementById('welcome-readiness-cockpit');
      if (cockpit) {
        cockpit.setAttribute('aria-label', profile.cockpitTitle);
        Object.keys(profile.indicators).forEach((key) => {
          const indCfg = profile.indicators[key];
          const btn = cockpit.querySelector(`[data-indicator="${key}"]`);
          if (!btn) return;
          const labelSpan = btn.querySelector('.welcome-indicator-label > span:last-child');
          if (labelSpan) labelSpan.textContent = indCfg.label;
          btn.setAttribute('aria-label', `${indCfg.label}: ${indCfg.hint}`);
          btn.onclick = () => {
            if (window.auraChat && typeof window.auraChat.sendUserPrompt === 'function') {
              window.auraChat.sendUserPrompt(indCfg.prompt);
            }
          };
        });
      }

      return profile;
    }

    init() {
      if (this.initialized) return;
      this.initialized = true;
      this.detectAndApply().catch(() => {});
    }
  }

  const exported = {
    AuraDomainThemeAdapter,
    DOMAIN_PACKS
  };

  if (typeof window !== 'undefined') {
    window.AuraDomainThemeAdapter = AuraDomainThemeAdapter;
    window.auraDomainAdapter = new AuraDomainThemeAdapter();
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => window.auraDomainAdapter.init());
    } else {
      window.auraDomainAdapter.init();
    }
  }

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = exported;
  }
})(typeof window !== 'undefined' ? window : globalThis);
