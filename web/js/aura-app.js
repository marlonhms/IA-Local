/**
 * AURA Application Coordinator
 * Orquestra as visualizações do painel, alternância de abas, layout split,
 * áudio tático via Web Audio API, ícones com fallback offline e auto-refresh.
 */

class AuraAudio {
  constructor() {
    this.ctx = null;
    this.muted = true; // Mutado por padrão para discrição
  }

  ensureContext() {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) this.ctx = new AudioCtx();
    }
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  toggleMute() {
    this.muted = !this.muted;
    if (!this.muted) {
      this.ensureContext();
      this.playChime(660, 0.08);
    }
    return this.muted;
  }

  playChime(freq = 520, duration = 0.06) {
    if (this.muted) return;
    try {
      this.ensureContext();
      if (!this.ctx) return;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq, this.ctx.currentTime);
      gain.gain.setValueAtTime(0.04, this.ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.0001, this.ctx.currentTime + duration);
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start();
      osc.stop(this.ctx.currentTime + duration);
    } catch (_) {}
  }
}

window.auraAudio = new AuraAudio();

/**
 * AURA Proprietary Brand Iconography (v2.8.0)
 * Elimina o estigma de ícones genéricos Lucide e sparkles ✨ de IA,
 * fornecendo insígnias executivas e glifos técnicos de precisão para postos de combustíveis.
 */
window.AuraIcons = {
  // 1. Núcleo AURA / Prisma Hexagonal / Glifo Executivo (Substitui Sparkles ✨ de IA)
  core: (cls = 'w-4 h-4 text-purple-400') => `
    <svg class="${cls} aura-glyph aura-core-insignia" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <polygon points="12 2 20.66 7 20.66 17 12 22 3.34 17 3.34 7" stroke="currentColor" stroke-width="1.75" stroke-linejoin="round"/>
      <polygon points="12 6 17.2 9 17.2 15 12 18 6.8 15 6.8 9" stroke="currentColor" stroke-width="1.25" stroke-opacity="0.6" stroke-linejoin="round"/>
      <circle cx="12" cy="12" r="2.2" fill="currentColor"/>
      <line x1="12" y1="2" x2="12" y2="6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      <line x1="12" y1="18" x2="12" y2="22" stroke-width="1.5" stroke-linecap="round"/>
    </svg>
  `.trim(),

  // 2. Panorama Operacional: Telemetria Integrada de Pista & Bombas (Substitui Gauge)
  telemetry: (cls = 'w-4 h-4 text-emerald-400') => `
    <svg class="${cls} aura-glyph" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="3" y="3" width="8" height="18" rx="2" stroke="currentColor" stroke-width="1.75"/>
      <rect x="5" y="6" width="4" height="4" rx="0.75" stroke="currentColor" stroke-width="1.2" stroke-opacity="0.8"/>
      <line x1="5" y1="13" x2="9" y2="13" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      <line x1="5" y1="16" x2="8" y2="16" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      <rect x="13" y="7" width="8" height="14" rx="2" stroke="currentColor" stroke-width="1.75"/>
      <line x1="15" y1="11" x2="19" y2="11" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      <line x1="15" y1="14" x2="19" y2="14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      <line x1="15" y1="17" x2="17" y2="17" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      <circle cx="17" cy="4" r="1.5" fill="currentColor"/>
      <path d="M11 5h4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    </svg>
  `.trim(),

  // 3. Ações Rápidas: Gatilho de Diagnóstico Analítico (Substitui Zap de super-herói)
  diagnostics: (cls = 'w-4 h-4 text-cyan-400') => `
    <svg class="${cls} aura-glyph" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.75"/>
      <line x1="12" y1="1.5" x2="12" y2="5" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>
      <line x1="12" y1="19" x2="12" y2="22.5" stroke-width="1.75" stroke-linecap="round"/>
      <line x1="1.5" y1="12" x2="5" y2="12" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>
      <line x1="19" y1="12" x2="22.5" y2="12" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>
      <path d="M8 12.5l2.8 2.8L16.5 8.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
  `.trim(),

  // 4. Visão Integrada: Monitor Duplo de Telemetria & Auditoria (Substitui Layout Grid)
  split: (cls = 'w-4 h-4 text-sky-400') => `
    <svg class="${cls} aura-glyph" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="2" y="3" width="20" height="18" rx="2.5" stroke="currentColor" stroke-width="1.75"/>
      <line x1="12" y1="3" x2="12" y2="21" stroke="currentColor" stroke-width="1.75"/>
      <line x1="5" y1="8" x2="9" y2="8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      <line x1="5" y1="12" x2="8" y2="12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      <line x1="5" y1="16" x2="10" y2="16" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      <rect x="14" y="7" width="5.5" height="3.5" rx="1" stroke="currentColor" stroke-width="1.2" stroke-opacity="0.8"/>
      <line x1="14" y1="14" x2="18.5" y2="14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      <line x1="14" y1="17" x2="17" y2="17" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    </svg>
  `.trim(),

  // 5. Dispenser de Pista & Combustível Executivo (Substitui Fuel genérico de brinquedo)
  dispenser: (cls = 'w-4 h-4 text-emerald-400') => `
    <svg class="${cls} aura-glyph" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="3" y="3" width="11" height="18" rx="2" stroke="currentColor" stroke-width="1.75"/>
      <rect x="5.5" y="6" width="6" height="4" rx="0.8" stroke="currentColor" stroke-width="1.2" stroke-opacity="0.9"/>
      <path d="M14 8h2.5a2 2 0 0 1 2 2v6.5a1.5 1.5 0 0 0 3 0V9l-2-2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
      <line x1="2" y1="21" x2="15" y2="21" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>
      <line x1="6" y1="14" x2="11" y2="14" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
      <line x1="6" y1="17" x2="9" y2="17" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
    </svg>
  `.trim(),

  // 6. Tanque Subterrâneo & Volumetria / Ullage
  tank: (cls = 'w-4 h-4 text-emerald-400') => `
    <svg class="${cls} aura-glyph" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="3" y="6" width="18" height="12" rx="6" stroke="currentColor" stroke-width="1.75"/>
      <line x1="9" y1="6" x2="9" y2="18" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
      <line x1="15" y1="6" x2="15" y2="18" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
      <circle cx="12" cy="12" r="1.5" fill="currentColor"/>
      <line x1="12" y1="3" x2="12" y2="6" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>
    </svg>
  `.trim(),

  // 7. Conciliação de Turno & Caixa Financeiro (Substitui saco de dinheiro 💰)
  cash: (cls = 'w-4 h-4 text-cyan-400') => `
    <svg class="${cls} aura-glyph" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="2" y="5" width="20" height="14" rx="2" stroke="currentColor" stroke-width="1.75"/>
      <circle cx="12" cy="12" r="3.5" stroke="currentColor" stroke-width="1.5"/>
      <line x1="6" y1="12" x2="6.01" y2="12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      <line x1="18" y1="12" x2="18.01" y2="12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    </svg>
  `.trim(),

  // 8. LMC ANP Oficial / Portaria 26 (Substitui prancheta de desenho 📋)
  audit: (cls = 'w-4 h-4 text-purple-400') => `
    <svg class="${cls} aura-glyph" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>
      <path d="M4 4.5A2.5 2.5 0 0 1 6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15z" stroke="currentColor" stroke-width="1.75" stroke-linejoin="round"/>
      <path d="M9 10l2 2 4-4" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
  `.trim(),

  // 9. Cesta da Loja / Market Basket (Substitui carrinho de supermercado 🛒)
  basket: (cls = 'w-4 h-4 text-amber-400') => `
    <svg class="${cls} aura-glyph" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z" stroke="currentColor" stroke-width="1.75" stroke-linejoin="round"/>
      <line x1="3" y1="6" x2="21" y2="6" stroke="currentColor" stroke-width="1.75"/>
      <path d="M16 10a4 4 0 0 1-8 0" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>
    </svg>
  `.trim(),

  // 10. Vazão de Bicos & Desempenho de Frentistas
  nozzle: (cls = 'w-4 h-4 text-amber-400') => `
    <svg class="${cls} aura-glyph" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M3 13l4-4 4 4" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M7 9v12" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>
      <path d="M14 5l4 4-4 4" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>
      <path d="M18 9H10" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>
      <circle cx="18" cy="18" r="3" stroke="currentColor" stroke-width="1.5"/>
    </svg>
  `.trim(),

  // 11. Clientes VIP & Ranking de Frotas (Substitui troféu de desenho 🏆)
  fleet: (cls = 'w-4 h-4 text-rose-400') => `
    <svg class="${cls} aura-glyph" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" stroke="currentColor" stroke-width="1.75" stroke-linejoin="round"/>
      <circle cx="12" cy="11" r="2.5" fill="currentColor" fill-opacity="0.3"/>
    </svg>
  `.trim(),

  // 12. Caminhão-Tanque / Pedido de Carreta (Substitui caminhão emoji 🚚)
  truck: (cls = 'w-3.5 h-3.5 text-purple-400') => `
    <svg class="${cls} aura-glyph" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="1" y="4" width="14" height="12" rx="1.5" stroke="currentColor" stroke-width="1.75"/>
      <path d="M15 8h4.5l2.5 3.5V16h-7V8z" stroke="currentColor" stroke-width="1.75" stroke-linejoin="round"/>
      <circle cx="5.5" cy="18.5" r="2.5" stroke="currentColor" stroke-width="1.75"/>
      <circle cx="18.5" cy="18.5" r="2.5" stroke="currentColor" stroke-width="1.75"/>
    </svg>
  `.trim(),

  // 13. Alerta Operacional Técnico (Substitui triângulo emoji ⚠️)
  alert: (cls = 'w-3.5 h-3.5 text-rose-400') => `
    <svg class="${cls} aura-glyph" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" stroke="currentColor" stroke-width="1.75" stroke-linejoin="round"/>
      <line x1="12" y1="9" x2="12" y2="13" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>
      <circle cx="12" cy="17" r="1" fill="currentColor"/>
    </svg>
  `.trim(),

  // 14. Pulso de Diagnóstico (Substitui raio emoji ⚡)
  pulse: (cls = 'w-3.5 h-3.5 text-cyan-400') => `
    <svg class="${cls} aura-glyph" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
  `.trim(),

  renderAll: () => {
    document.querySelectorAll('[data-aura-icon]').forEach(el => {
      const name = el.getAttribute('data-aura-icon');
      const cls = el.className || 'w-4 h-4';
      if (window.AuraIcons[name]) {
        el.outerHTML = window.AuraIcons[name](cls);
      }
    });
  }
};

function applyIconsFallback() {
  // Renderiza ícones proprietários AURA primeiro
  if (window.AuraIcons && typeof window.AuraIcons.renderAll === 'function') {
    window.AuraIcons.renderAll();
  }

  // Intercepta e substitui qualquer ícone genérico residual antes do Lucide
  const proprietaryMap = {
    'sparkles': window.AuraIcons ? window.AuraIcons.core('w-3.5 h-3.5 text-white') : '',
    'fuel': window.AuraIcons ? window.AuraIcons.dispenser('w-4 h-4 text-emerald-400') : '',
    'gauge': window.AuraIcons ? window.AuraIcons.telemetry('w-4 h-4 text-cyan-400') : '',
    'zap': window.AuraIcons ? window.AuraIcons.diagnostics('w-4 h-4 text-cyan-400') : '',
    'layout-grid': window.AuraIcons ? window.AuraIcons.split('w-4 h-4 text-sky-400') : ''
  };

  document.querySelectorAll('i[data-lucide]').forEach(el => {
    const iconName = el.getAttribute('data-lucide');
    if (proprietaryMap[iconName]) {
      el.outerHTML = proprietaryMap[iconName];
    }
  });

  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
    return;
  }

  const svgMap = {
    'fuel': window.AuraIcons.dispenser('w-4 h-4 text-emerald-400'),
    'gauge': window.AuraIcons.telemetry('w-4 h-4 text-cyan-400'),
    'zap': window.AuraIcons.diagnostics('w-4 h-4 text-cyan-400'),
    'terminal': '<svg class="w-4 h-4 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><polyline stroke-width="2" points="4 17 10 11 4 5"/><line stroke-width="2" x1="12" y1="19" x2="20" y2="19"/></svg>',
    'layout-grid': window.AuraIcons.split('w-4 h-4 text-sky-400'),
    'refresh-cw': '<svg class="w-4 h-4 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/></svg>',
    'volume-2': '<svg class="w-4 h-4 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><polygon stroke-width="2" points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.07 4.93a10 10 0 010 14.14M15.54 8.46a5 5 0 010 7.07"/></svg>',
    'volume-x': '<svg class="w-4 h-4 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><polygon stroke-width="2" points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><line stroke-width="2" x1="23" y1="9" x2="17" y2="15"/><line stroke-width="2" x1="17" y1="9" x2="23" y2="15"/></svg>',
    'send': '<svg class="w-4 h-4 text-slate-900" fill="none" stroke="currentColor" viewBox="0 0 24 24"><line stroke-width="2" x1="22" y1="2" x2="11" y2="13"/><polygon stroke-width="2" points="22 2 15 22 11 13 2 9 22 2"/></svg>',
    'trash-2': '<svg class="w-3.5 h-3.5 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><polyline stroke-width="2" points="3 6 5 6 21 6"/><path stroke-width="2" d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>',
    'shield-check': '<svg class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10zM9 12l2 2 4-4"/></svg>',
    'layers': '<svg class="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><polygon stroke-width="2" points="12 2 2 7 12 12 22 7 12 2"/><polyline stroke-width="2" points="2 17 12 22 22 17"/><polyline stroke-width="2" points="2 12 12 17 22 12"/></svg>',
    'users': '<svg class="w-4 h-4 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-width="2" d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4" stroke-width="2"/><path stroke-width="2" d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/></svg>',
    'shield-alert': '<svg class="w-4 h-4 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-width="2" d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10zM12 8v4M12 16h.01"/></svg>',
    'receipt': '<svg class="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-width="2" d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1-2-1zM8 7h8M8 11h8M8 15h5"/></svg>',
    'book-check': '<svg class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-width="2" d="M4 19.5A2.5 2.5 0 016.5 17H20M4 4.5A2.5 2.5 0 016.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15zM9 10l2 2 4-4"/></svg>',
    'shopping-bag': '<svg class="w-4 h-4 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-width="2" d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4zM3 6h18M16 10a4 4 0 01-8 0"/></svg>',
    'sparkles': window.AuraIcons.core('w-3.5 h-3.5 text-white'),
    'square': '<svg class="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16" rx="2"/></svg>',
    'monitor': '<svg class="w-3.5 h-3.5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><rect x="2" y="3" width="20" height="14" rx="2" stroke-width="2"/><line x1="8" y1="21" x2="16" y2="21" stroke-width="2"/><line x1="12" y1="17" x2="12" y2="21" stroke-width="2"/></svg>',
    'clock': '<svg class="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke-width="2"/><polyline points="12 6 12 12 16 14"/></svg>',
    'message-square': '<svg class="w-4 h-4 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-width="2" d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
    'menu': '<svg class="w-5 h-5 text-auraCyan" fill="none" stroke="currentColor" viewBox="0 0 24 24"><line stroke-width="2" x1="3" y1="12" x2="21" y2="12"/><line stroke-width="2" x1="3" y1="6" x2="21" y2="6"/><line stroke-width="2" x1="3" y1="18" x2="21" y2="18"/></svg>',
    'x': '<svg class="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><line stroke-width="2" x1="18" y1="6" x2="6" y2="18"/><line stroke-width="2" x1="6" y1="6" x2="18" y2="18"/></svg>',
    'plus': '<svg class="w-3.5 h-3.5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><line stroke-width="2" x1="12" y1="5" x2="12" y2="19"/><line stroke-width="2" x1="5" y1="12" x2="19" y2="12"/></svg>',
    'plus-circle': '<svg class="w-3.5 h-3.5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke-width="2"/><line stroke-width="2" x1="12" y1="8" x2="12" y2="16"/><line stroke-width="2" x1="8" y1="12" x2="16" y2="12"/></svg>',
    'info': '<svg class="w-3.5 h-3.5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke-width="2"/><line x1="12" y1="16" x2="12" y2="12" stroke-width="2"/><line x1="12" y1="8" x2="12.01" y2="8" stroke-width="2"/></svg>',
    'file-check-2': '<svg class="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>',
    'arrow-down': '<svg class="w-3.5 h-3.5 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><line x1="12" y1="5" x2="12" y2="19" stroke-width="2"/><polyline points="19 12 12 19 5 12" stroke-width="2"/></svg>',
  };

  document.querySelectorAll('i[data-lucide]').forEach(el => {
    const iconName = el.getAttribute('data-lucide');
    if (svgMap[iconName]) {
      el.outerHTML = svgMap[iconName];
    }
  });
}


class AuraApp {
  constructor() {
    this.currentTab = 'console';
    this.sidebarOpen = false;
  }

  init() {
    this.bindNavigationTabs();
    this.bindSidebarEvents();
    this.initGpuGuard();
    this.startClock();

    // Inicializa subsistemas
    window.auraCockpit.init();
    window.auraTriggers.renderGrid();
    window.auraChat.init();

    // Inicia diretamente no Console Cognitivo (Mobile-First Workspace)
    this.switchTab('console');

    applyIconsFallback();
  }

  bindSidebarEvents() {
    const btnToggle = document.getElementById('btn-toggle-sidebar');
    const btnClose = document.getElementById('btn-close-sidebar');
    const overlay = document.getElementById('aura-sidebar-overlay');
    const btnNewChat = document.getElementById('btn-new-chat');

    if (btnToggle) {
      btnToggle.addEventListener('click', () => {
        this.toggleSidebar();
      });
    }

    if (btnNewChat) {
      btnNewChat.addEventListener('click', () => {
        window.auraAudio.playChime(500, 0.05);
        if (window.auraChat) window.auraChat.clearSession();
      });
    }

    if (btnClose) {
      btnClose.addEventListener('click', () => {
        this.closeSidebar();
      });
    }

    if (overlay) {
      overlay.addEventListener('click', () => {
        this.closeSidebar();
      });
    }

    // Atalho ESC e Focus Trap para a gaveta lateral (F4-08)
    window.addEventListener('keydown', (e) => {
      if (!this.sidebarOpen) return;

      if (e.key === 'Escape') {
        e.preventDefault();
        e.stopPropagation();
        this.closeSidebar();
        return;
      }

      if (e.key === 'Tab') {
        const drawer = document.getElementById('aura-sidebar-drawer');
        if (!drawer) return;
        const focusables = drawer.querySelectorAll('button:not([disabled]), [tabindex]:not([tabindex="-1"]), a[href]');
        if (focusables.length === 0) return;
        const first = focusables[0];
        const last = focusables[focusables.length - 1];

        if (!drawer.contains(document.activeElement)) {
          e.preventDefault();
          first.focus();
          return;
        }

        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    });

    // Botão Limpar Chat na Gaveta
    const btnSidebarClear = document.getElementById('sidebar-btn-chat-clear');
    if (btnSidebarClear) {
      btnSidebarClear.addEventListener('click', () => {
        window.auraAudio.playChime(500, 0.05);
        if (window.auraChat) window.auraChat.clearSession();
        this.closeSidebar();
      });
    }

    // Botão Command Palette na Gaveta
    const btnSidebarPalette = document.getElementById('sidebar-btn-palette');
    if (btnSidebarPalette) {
      btnSidebarPalette.addEventListener('click', () => {
        this.closeSidebar();
        if (window.auraGlance && typeof window.auraGlance.openCommandPalette === 'function') {
          window.auraGlance.openCommandPalette();
        } else {
          const btnPalette = document.getElementById('btn-open-palette');
          if (btnPalette) btnPalette.click();
        }
      });
    }

    // Botão SFX na Gaveta
    const btnSidebarSfx = document.getElementById('sidebar-btn-toggle-sfx');
    if (btnSidebarSfx) {
      btnSidebarSfx.addEventListener('click', () => {
        const isMuted = window.auraAudio.toggleMute();
        this.syncSfxButtons(isMuted);
      });
    }
  }

  openSidebar() {
    this.previousActiveElement = document.activeElement;
    this.sidebarOpen = true;
    const drawer = document.getElementById('aura-sidebar-drawer');
    const overlay = document.getElementById('aura-sidebar-overlay');
    if (drawer) drawer.classList.add('open');
    if (overlay) overlay.classList.add('open');
    window.auraAudio.playChime(660, 0.05);

    // Foco inicial no botão fechar para acessibilidade
    const btnClose = document.getElementById('btn-close-sidebar');
    if (btnClose) {
      setTimeout(() => btnClose.focus(), 50);
    }
  }

  closeSidebar() {
    this.sidebarOpen = false;
    const drawer = document.getElementById('aura-sidebar-drawer');
    const overlay = document.getElementById('aura-sidebar-overlay');
    if (drawer) drawer.classList.remove('open');
    if (overlay) overlay.classList.remove('open');

    // Devolve o foco ao acionador
    if (this.previousActiveElement && typeof this.previousActiveElement.focus === 'function') {
      this.previousActiveElement.focus();
    } else {
      const btnToggle = document.getElementById('btn-toggle-sidebar');
      if (btnToggle) btnToggle.focus();
    }
  }

  toggleSidebar() {
    if (this.sidebarOpen) {
      this.closeSidebar();
    } else {
      this.openSidebar();
    }
  }

  askFrequent(prompt) {
    this.closeSidebar();
    if (this.currentTab !== 'console') {
      this.switchTab('console');
    }
    if (window.auraChat) {
      window.auraChat.sendUserPrompt(prompt);
    }
  }

  syncSfxButtons(isMuted) {
    const btnToggleSfx = document.getElementById('btn-toggle-sfx');
    const sfxBadge = document.getElementById('sidebar-sfx-badge');
    const sfxIcon = document.getElementById('sidebar-sfx-icon');

    if (btnToggleSfx) {
      btnToggleSfx.title = isMuted ? 'Áudio Mudo (Clique para Ativar SFX)' : 'Áudio Ativo (Clique para Mutar)';
      btnToggleSfx.className = isMuted 
        ? 'p-1.5 rounded-xl bg-slate-900/80 hover:bg-slate-800 text-slate-400 hover:text-white border border-slate-800 transition-colors shadow-sm'
        : 'p-1.5 rounded-xl bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 transition-colors shadow-sm';
    }

    if (sfxBadge) {
      sfxBadge.textContent = isMuted ? 'Mudo' : 'Ativo';
      sfxBadge.className = isMuted 
        ? 'px-2 py-0.5 rounded text-[10px] font-sans font-medium bg-slate-800 text-slate-400' 
        : 'px-2 py-0.5 rounded text-[10px] font-sans font-medium bg-emerald-500/20 text-emerald-400 border border-emerald-500/30';
    }

    if (sfxIcon) {
      sfxIcon.setAttribute('class', isMuted ? 'w-4 h-4 text-slate-400' : 'w-4 h-4 text-emerald-400');
    }
  }

  bindNavigationTabs() {
    const tabs = document.querySelectorAll('.nav-tab-btn');
    tabs.forEach(btn => {
      btn.addEventListener('click', () => {
        const target = btn.getAttribute('data-tab');
        if (target) {
          window.auraAudio.playChime(600, 0.05);
          this.switchTab(target);
          this.closeSidebar();
        }
      });
    });

    // Filtros de gatilhos 1-clique
    const filterBtns = document.querySelectorAll('.trigger-filter-btn');
    filterBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const filter = btn.getAttribute('data-filter');
        if (filter) {
          window.auraAudio.playChime(500, 0.04);
          window.auraTriggers.setFilter(filter);
          applyIconsFallback();
        }
      });
    });

    // Botão de refresh manual do cockpit
    const btnRefresh = document.getElementById('btn-refresh-cockpit');
    if (btnRefresh) {
      btnRefresh.addEventListener('click', () => {
        window.auraAudio.playChime(700, 0.06);
        window.auraCockpit.refreshAllData();
      });
    }

    // Botão SFX Audio no Header
    const btnToggleSfx = document.getElementById('btn-toggle-sfx');
    if (btnToggleSfx) {
      btnToggleSfx.addEventListener('click', () => {
        const isMuted = window.auraAudio.toggleMute();
        this.syncSfxButtons(isMuted);
      });
    }

    // Botão copiar JSON
    const btnCopyJson = document.getElementById('btn-copy-json');
    if (btnCopyJson) {
      btnCopyJson.addEventListener('click', () => {
        window.auraAudio.playChime(800, 0.05);
        window.auraTriggers.copyJson();
      });
    }

    // Botão enviar resultado para a AURA
    const btnSendToAura = document.getElementById('btn-send-to-aura');
    if (btnSendToAura) {
      btnSendToAura.addEventListener('click', () => {
        window.auraAudio.playChime(750, 0.07);
        window.auraTriggers.sendResultToAura();
      });
    }

    // Abas internas do Inspetor de Gatilhos (Formatado vs JSON)
    const tabInspectorFormatted = document.getElementById('tab-inspector-formatted');
    const tabInspectorJson = document.getElementById('tab-inspector-json');
    const contentFormatted = document.getElementById('inspector-content-formatted');
    const contentJson = document.getElementById('inspector-content-json');

    if (tabInspectorFormatted && tabInspectorJson && contentFormatted && contentJson) {
      tabInspectorFormatted.addEventListener('click', () => {
        window.auraAudio.playChime(540, 0.04);
        tabInspectorFormatted.classList.add('bg-slate-800', 'text-white');
        tabInspectorFormatted.classList.remove('text-slate-400');
        tabInspectorJson.classList.remove('bg-slate-800', 'text-white');
        tabInspectorJson.classList.add('text-slate-400');
        contentFormatted.classList.remove('hidden');
        contentJson.classList.add('hidden');
      });

      tabInspectorJson.addEventListener('click', () => {
        window.auraAudio.playChime(540, 0.04);
        tabInspectorJson.classList.add('bg-slate-800', 'text-white');
        tabInspectorJson.classList.remove('text-slate-400');
        tabInspectorFormatted.classList.remove('bg-slate-800', 'text-white');
        tabInspectorFormatted.classList.add('text-slate-400');
        contentJson.classList.remove('hidden');
        contentFormatted.classList.add('hidden');
      });
    }
  }

  /**
   * Inicializa o Modo Alta Performance (GPU Guard) a partir das preferências do usuário
   */
  initGpuGuard() {
    let saved = false;
    try {
      saved = localStorage.getItem('aura_gpu_guard') === 'true';
    } catch (_) {}
    this.applyGpuGuard(saved);

    const btnGpu = document.getElementById('sidebar-btn-toggle-gpu-guard');
    if (btnGpu) {
      btnGpu.addEventListener('click', () => {
        const nextState = !this.isGpuGuardActive();
        this.applyGpuGuard(nextState);
        try {
          localStorage.setItem('aura_gpu_guard', nextState ? 'true' : 'false');
        } catch (_) {}
        if (window.auraAudio) window.auraAudio.playChime(nextState ? 750 : 500, 0.05);
      });
    }
  }

  isGpuGuardActive() {
    return document.documentElement.classList.contains('gpu-guard-active');
  }

  applyGpuGuard(enabled) {
    const root = document.documentElement;
    const body = document.body;
    if (enabled) {
      root.classList.add('gpu-guard-active');
      if (body) body.classList.add('gpu-guard-active');
    } else {
      root.classList.remove('gpu-guard-active');
      if (body) body.classList.remove('gpu-guard-active');
    }

    const badge = document.getElementById('sidebar-gpu-badge');
    const icon = document.getElementById('sidebar-gpu-icon');
    const btnGpu = document.getElementById('sidebar-btn-toggle-gpu-guard');
    if (btnGpu) {
      btnGpu.setAttribute('aria-checked', enabled ? 'true' : 'false');
    }
    if (badge) {
      badge.textContent = enabled ? 'Ativo (60 FPS)' : 'Desativado';
      badge.className = enabled
        ? 'px-2 py-0.5 rounded text-[10px] font-sans font-medium bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
        : 'px-2 py-0.5 rounded text-[10px] font-sans font-medium bg-slate-800 text-slate-400';
    }
    if (icon) {
      icon.setAttribute('class', enabled ? 'w-4 h-4 text-emerald-400' : 'w-4 h-4 text-slate-400');
    }
  }

  /**
   * Alterna a visualização ativa com transição fluida e cinematográfica
   */
  switchTab(tabName) {
    const views = {
      cockpit: document.getElementById('view-cockpit'),
      triggers: document.getElementById('view-triggers'),
      console: document.getElementById('view-console')
    };

    // Previne repetição abrupta da animação se a aba atual já estiver visível
    if (this.currentTab === tabName) {
      const currentEl = views[tabName];
      if (currentEl && !currentEl.classList.contains('hidden')) {
        if (tabName === 'console') {
          const input = document.getElementById('chat-input-text');
          if (input) input.focus({ preventScroll: true });
        }
        return;
      }
    }

    this.currentTab = tabName;

    document.querySelectorAll('.nav-tab-btn').forEach(btn => {
      const isTarget = btn.getAttribute('data-tab') === tabName;
      if (isTarget) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    Object.values(views).forEach(v => {
      if (v) {
        v.classList.add('hidden');
        v.classList.remove('view-transition-active');
      }
    });

    const targetView = views[tabName];
    if (targetView) {
      targetView.classList.remove('hidden');
      // Força reflow para disparar transição cinematográfica (200ms cubic-bezier)
      void targetView.offsetWidth;
      targetView.classList.add('view-transition-active');
    }

    if (tabName === 'console') {
      const input = document.getElementById('chat-input-text');
      if (input) input.focus({ preventScroll: true });
    }

    applyIconsFallback();
  }

  /**
   * Atalho acionado a partir de um card de tanque
   */
  askAboutTank(codtan, combustivel) {
    const prompt = `Qual a previsão de esgotamento e a autonomia estimada para o tanque ${codtan} (${combustivel})? Devemos emitir pedido de carreta para hoje?`;
    this.switchTab('console');
    window.auraChat.sendUserPrompt(prompt);
  }

  startClock() {
    const clockEl = document.getElementById('hud-live-clock');
    const clockMobile = document.getElementById('hud-live-clock-mobile');
    if (!clockEl && !clockMobile) return;

    const update = () => {
      const now = new Date();
      const timeStr = now.toLocaleTimeString('pt-BR');
      if (clockEl) clockEl.textContent = timeStr;
      if (clockMobile) clockMobile.textContent = timeStr;
    };
    update();
    setInterval(update, 1000);
  }
}

// Instanciação e boot
window.auraApp = new AuraApp();
document.addEventListener('DOMContentLoaded', () => {
  window.auraApp.init();
});
