/**
 * AURA History Drawer Controller (Abordagem C: Gaveta Lateral de Historico)
 * Gerencia a navegacao entre conversas anteriores com agrupamento temporal,
 * busca em tempo real, badges de dominio operacional e reidratacao instantanea.
 * Zero dependencias externas, zero travessoes.
 */

(function (window) {
  'use strict';

  function parseDateSafe(str) {
    if (!str) return new Date();
    if (typeof str === 'number') return new Date(str);
    let s = String(str).trim();
    if (s.includes(' ') && !s.includes('T')) {
      s = s.replace(' ', 'T');
    }
    const d = new Date(s);
    return isNaN(d.getTime()) ? new Date() : d;
  }

  class AuraHistoryDrawerController {
    constructor() {
      this.isOpen = false;
      this.currentSearchFilter = '';
      this.drawerEl = null;
      this.overlayEl = null;
      this.groupsContainerEl = null;
      this.searchInputEl = null;
      this.clearSearchBtnEl = null;
      this.totalChipEl = null;
      this.openBtnEl = null;
      this.chatOpenBtnEl = null;
      this.sidebarOpenBtnEl = null;
      this.closeBtnEl = null;
      this.drawerNewChatBtnEl = null;
      this.clearAllBtnEl = null;
      this.lastFocusedElement = null;

      this.init();
    }

    init() {
      if (typeof document === 'undefined') return;

      this.drawerEl = document.getElementById('aura-history-drawer');
      this.overlayEl = document.getElementById('aura-history-drawer-overlay');
      this.groupsContainerEl = document.getElementById('history-groups-container');
      this.searchInputEl = document.getElementById('history-search-input');
      this.clearSearchBtnEl = document.getElementById('btn-history-clear-search');
      this.totalChipEl = document.getElementById('history-total-chip');
      this.openBtnEl = document.getElementById('btn-open-history');
      this.chatOpenBtnEl = document.getElementById('btn-chat-open-history');
      this.sidebarOpenBtnEl = document.getElementById('sidebar-btn-open-history');
      this.closeBtnEl = document.getElementById('btn-close-history-drawer');
      this.drawerNewChatBtnEl = document.getElementById('btn-drawer-new-chat');
      this.clearAllBtnEl = document.getElementById('btn-clear-all-history');

      this.bindEvents();
    }

    bindEvents() {
      if (this.openBtnEl) {
        this.openBtnEl.addEventListener('click', () => this.toggle());
      }
      if (this.chatOpenBtnEl) {
        this.chatOpenBtnEl.addEventListener('click', () => this.toggle());
      }
      if (this.sidebarOpenBtnEl) {
        this.sidebarOpenBtnEl.addEventListener('click', () => {
          const sidebar = document.getElementById('aura-sidebar-drawer');
          if (sidebar && sidebar.classList.contains('translate-x-0')) {
            const sidebarOverlay = document.getElementById('aura-sidebar-overlay');
            if (sidebarOverlay) sidebarOverlay.click();
          }
          this.open();
        });
      }
      if (this.closeBtnEl) {
        this.closeBtnEl.addEventListener('click', () => this.close());
      }
      if (this.overlayEl) {
        this.overlayEl.addEventListener('click', () => this.close());
      }
      if (this.drawerNewChatBtnEl) {
        this.drawerNewChatBtnEl.addEventListener('click', () => this.handleNewChat());
      }
      if (this.clearAllBtnEl) {
        this.clearAllBtnEl.addEventListener('click', () => this.handleClearAll());
      }
      if (this.searchInputEl) {
        this.searchInputEl.addEventListener('input', (e) => this.handleSearchInput(e.target.value));
      }
      if (this.clearSearchBtnEl) {
        this.clearSearchBtnEl.addEventListener('click', () => this.clearSearch());
      }

      // Atalhos de teclado: Ctrl+H (ou Cmd+H), Escape e Focus Trap
      document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && (e.key === 'h' || e.key === 'H')) {
          e.preventDefault();
          this.toggle();
          return;
        }

        if (this.isOpen) {
          if (e.key === 'Escape') {
            e.preventDefault();
            e.stopPropagation();
            this.close();
            return;
          }

          if (e.key === 'Tab') {
            this.handleFocusTrap(e);
          }
        }
      });
    }

    handleFocusTrap(e) {
      if (!this.drawerEl) return;
      const focusable = this.drawerEl.querySelectorAll('button:not([disabled]), [tabindex]:not([tabindex="-1"]), [href], input, select, textarea');
      if (focusable.length === 0) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (!this.drawerEl.contains(document.activeElement)) {
        e.preventDefault();
        first.focus();
        return;
      }

      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }

    open() {
      if (!this.drawerEl) {
        this.drawerEl = document.getElementById('aura-history-drawer');
      }
      if (!this.overlayEl) {
        this.overlayEl = document.getElementById('aura-history-drawer-overlay');
      }
      if (!this.groupsContainerEl) {
        this.groupsContainerEl = document.getElementById('history-groups-container');
      }
      if (!this.searchInputEl) {
        this.searchInputEl = document.getElementById('history-search-input');
      }
      if (!this.totalChipEl) {
        this.totalChipEl = document.getElementById('history-total-chip');
      }

      if (!this.drawerEl) return;
      this.lastFocusedElement = document.activeElement;

      // Manipula classes e estilos inline explicitamente para nunca depender de especificidade CSS
      this.drawerEl.classList.remove('translate-x-full');
      this.drawerEl.classList.add('translate-x-0', 'open');
      this.drawerEl.style.transform = 'translateX(0)';
      this.drawerEl.style.visibility = 'visible';
      this.drawerEl.style.pointerEvents = 'auto';
      this.drawerEl.setAttribute('aria-hidden', 'false');

      if (this.overlayEl) {
        this.overlayEl.classList.remove('opacity-0', 'pointer-events-none');
        this.overlayEl.classList.add('opacity-100', 'pointer-events-auto', 'open');
        this.overlayEl.style.opacity = '1';
        this.overlayEl.style.pointerEvents = 'auto';
        this.overlayEl.style.visibility = 'visible';
        this.overlayEl.setAttribute('aria-hidden', 'false');
      }

      this.isOpen = true;
      this.renderHistory(this.currentSearchFilter);

      setTimeout(() => {
        if (this.searchInputEl) {
          this.searchInputEl.focus();
        }
      }, 50);

      this.refreshLucideIcons();
    }

    close() {
      if (!this.drawerEl) {
        this.drawerEl = document.getElementById('aura-history-drawer');
      }
      if (!this.overlayEl) {
        this.overlayEl = document.getElementById('aura-history-drawer-overlay');
      }
      if (!this.drawerEl) return;

      this.drawerEl.classList.remove('translate-x-0', 'open');
      this.drawerEl.classList.add('translate-x-full');
      this.drawerEl.style.transform = 'translateX(100%)';
      this.drawerEl.style.visibility = 'hidden';
      this.drawerEl.style.pointerEvents = 'none';
      this.drawerEl.setAttribute('aria-hidden', 'true');

      if (this.overlayEl) {
        this.overlayEl.classList.remove('opacity-100', 'pointer-events-auto', 'open');
        this.overlayEl.classList.add('opacity-0', 'pointer-events-none');
        this.overlayEl.style.opacity = '0';
        this.overlayEl.style.pointerEvents = 'none';
        this.overlayEl.style.visibility = 'hidden';
        this.overlayEl.setAttribute('aria-hidden', 'true');
      }

      this.isOpen = false;

      if (this.lastFocusedElement && typeof this.lastFocusedElement.focus === 'function') {
        try {
          this.lastFocusedElement.focus();
        } catch (_) {}
      }
    }

    toggle() {
      if (this.isOpen) {
        this.close();
      } else {
        this.open();
      }
    }

    handleSearchInput(term) {
      this.currentSearchFilter = (term || '').trim();
      if (this.clearSearchBtnEl) {
        if (this.currentSearchFilter.length > 0) {
          this.clearSearchBtnEl.classList.remove('hidden');
        } else {
          this.clearSearchBtnEl.classList.add('hidden');
        }
      }
      this.renderHistory(this.currentSearchFilter);
    }

    clearSearch() {
      if (this.searchInputEl) {
        this.searchInputEl.value = '';
        this.searchInputEl.focus();
      }
      if (this.clearSearchBtnEl) {
        this.clearSearchBtnEl.classList.add('hidden');
      }
      this.currentSearchFilter = '';
      this.renderHistory('');
    }

    classifyDomain(session) {
      if (!session) {
        return {
          key: 'operacao',
          label: 'Operacao',
          badgeClass: 'bg-slate-700/40 text-slate-300 border border-slate-600/40',
          icon: 'activity'
        };
      }

      const text = ((session.title || '') + ' ' + (typeof session.last_message === 'string' ? session.last_message : '')).toLowerCase();

      // Caixa / Financeiro
      if (
        text.includes('pagamento') ||
        text.includes('formas') ||
        text.includes('cartao') ||
        text.includes('cartão') ||
        text.includes('pix') ||
        text.includes('dinheiro') ||
        text.includes('sangria') ||
        text.includes('fechamento') ||
        text.includes('caixa') ||
        text.includes('pdv') ||
        text.includes('turno') ||
        text.includes('faturamento') ||
        text.includes('conciliacao') ||
        text.includes('conciliação') ||
        text.includes('diferenca') ||
        text.includes('diferença') ||
        text.includes('suprimento') ||
        text.includes('financeiro') ||
        text.includes('recebimento')
      ) {
        return {
          key: 'caixa',
          label: 'Caixa / Financeiro',
          badgeClass: 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30',
          icon: 'wallet'
        };
      }

      // Tanques / Pista
      if (
        text.includes('tanque') ||
        text.includes('bico') ||
        text.includes('bomba') ||
        text.includes('combustivel') ||
        text.includes('combustível') ||
        text.includes('gasolina') ||
        text.includes('etanol') ||
        text.includes('diesel') ||
        text.includes('autonomia') ||
        text.includes('afericao') ||
        text.includes('aferição') ||
        text.includes('pista') ||
        text.includes('frentista') ||
        text.includes('abastecimento') ||
        text.includes('run-out') ||
        text.includes('capacidade')
      ) {
        return {
          key: 'tanques',
          label: 'Tanques / Pista',
          badgeClass: 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30',
          icon: 'fuel'
        };
      }

      // LMC / Compliance
      if (
        text.includes('lmc') ||
        text.includes('livro') ||
        text.includes('anp') ||
        text.includes('resolucao') ||
        text.includes('resolução') ||
        text.includes('inmetro') ||
        text.includes('conformidade') ||
        text.includes('fiscalizacao') ||
        text.includes('fiscalização') ||
        text.includes('regulamentacao') ||
        text.includes('regulamentação') ||
        text.includes('perda') ||
        text.includes('sobra') ||
        text.includes('0.60') ||
        text.includes('tolerancia') ||
        text.includes('tolerância') ||
        text.includes('portaria')
      ) {
        return {
          key: 'lmc',
          label: 'LMC / Compliance',
          badgeClass: 'bg-purple-500/15 text-purple-300 border border-purple-500/30',
          icon: 'shield-check'
        };
      }

      // Vendas / Loja
      if (
        text.includes('loja') ||
        text.includes('conveniencia') ||
        text.includes('conveniência') ||
        text.includes('produto') ||
        text.includes('combo') ||
        text.includes('market basket') ||
        text.includes('itens') ||
        text.includes('vendas') ||
        text.includes('ticket') ||
        text.includes('cerveja') ||
        text.includes('lubrificante') ||
        text.includes('cross-sell')
      ) {
        return {
          key: 'vendas',
          label: 'Vendas / Loja',
          badgeClass: 'bg-amber-500/15 text-amber-300 border border-amber-500/30',
          icon: 'shopping-bag'
        };
      }

      // Operacao (fallback padrao)
      return {
        key: 'operacao',
        label: 'Operacao',
        badgeClass: 'bg-slate-700/40 text-slate-300 border border-slate-600/40',
        icon: 'activity'
      };
    }

    groupSessionsByTime(sessions) {
      const now = new Date();
      const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
      const startOfYesterday = startOfToday - 86400000;
      const sevenDaysAgo = startOfToday - (6 * 86400000);

      const groups = [
        { groupName: 'Hoje', sessions: [] },
        { groupName: 'Ontem', sessions: [] },
        { groupName: 'Ultimos 7 dias', sessions: [] },
        { groupName: 'Anteriores', sessions: [] }
      ];

      for (const s of sessions) {
        if (!s) continue;
        const d = parseDateSafe(s.updated_at || s.created_at).getTime();
        if (d >= startOfToday) {
          groups[0].sessions.push(s);
        } else if (d >= startOfYesterday) {
          groups[1].sessions.push(s);
        } else if (d >= sevenDaysAgo) {
          groups[2].sessions.push(s);
        } else {
          groups[3].sessions.push(s);
        }
      }

      return groups.filter(g => g.sessions.length > 0);
    }

    formatSessionTime(isoString) {
      if (!isoString) return '';
      try {
        const d = parseDateSafe(isoString);
        const hours = String(d.getHours()).padStart(2, '0');
        const mins = String(d.getMinutes()).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        const month = String(d.getMonth() + 1).padStart(2, '0');

        const now = new Date();
        const isToday = d.toDateString() === now.toDateString();

        if (isToday) {
          return `${hours}:${mins}`;
        }
        return `${day}/${month} ${hours}:${mins}`;
      } catch (_) {
        return '';
      }
    }

    escapeHtml(text) {
      if (!text) return '';
      return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }

    async renderHistory(searchFilter = '') {
      if (!this.groupsContainerEl) {
        this.groupsContainerEl = document.getElementById('history-groups-container');
      }
      if (!this.groupsContainerEl) return;

      // 1. Busca sessoes locais do IndexedDB / Cache
      let localSessions = [];
      if (window.AuraStorage && typeof window.AuraStorage.listSessions === 'function') {
        try {
          localSessions = await window.AuraStorage.listSessions(100);
        } catch (e) {
          console.warn('[AuraHistoryDrawer] Erro ao carregar sessoes do cache local:', e);
        }
      }

      // 2. Busca todas as sessoes duraveis do backend SQLite
      let backendSessions = [];
      if (typeof fetch !== 'undefined') {
        try {
          const resp = await fetch('/api/v1/aura/sessions?limit=100');
          if (resp.ok) {
            const data = await resp.json();
            if (data.status === 'success' && Array.isArray(data.sessions)) {
              backendSessions = data.sessions;
            }
          }
        } catch (_) {}
      }

      // 3. Mescla sem duplicidade por session_id (preserva metadados mais recentes)
      const sessionMap = new Map();
      for (const s of backendSessions) {
        if (s && s.session_id) sessionMap.set(s.session_id, s);
      }
      for (const s of localSessions) {
        if (s && s.session_id) {
          const prev = sessionMap.get(s.session_id) || {};
          sessionMap.set(s.session_id, Object.assign({}, prev, s));
        }
      }

      let sessions = Array.from(sessionMap.values());
      sessions.sort((a, b) => parseDateSafe(b.updated_at || b.created_at).getTime() - parseDateSafe(a.updated_at || a.created_at).getTime());

      const activeSessionId = (window.AuraStorage && typeof window.AuraStorage.getActiveSessionId === 'function')
        ? window.AuraStorage.getActiveSessionId()
        : (window.auraChat ? window.auraChat.sessionId : null);

      // Filtro de busca em tempo real
      let filteredSessions = sessions;
      if (searchFilter && searchFilter.length > 0) {
        const q = searchFilter.toLowerCase();
        filteredSessions = sessions.filter(s => {
          if (!s) return false;
          const title = (s.title || '').toLowerCase();
          const domain = this.classifyDomain(s);
          return title.includes(q) || domain.label.toLowerCase().includes(q);
        });
      }

      // Atualiza o contador de sessoes no topo
      if (this.totalChipEl) {
        const count = filteredSessions.length;
        this.totalChipEl.textContent = `${count} ${count === 1 ? 'conversa' : 'conversas'}`;
      }

      if (filteredSessions.length === 0) {
        this.groupsContainerEl.innerHTML = `
          <div class="text-center py-12 px-4 text-slate-400 font-sans">
            <div class="w-12 h-12 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center mx-auto mb-3 text-slate-500">
              <i data-lucide="message-square-dashed" class="w-6 h-6"></i>
            </div>
            <p class="font-medium text-slate-200 text-sm">Nenhuma conversa encontrada</p>
            <p class="text-[11px] text-slate-500 mt-1 max-w-[240px] mx-auto">
              ${searchFilter ? 'Nenhum resultado corresponde aos termos pesquisados.' : 'Suas conversas anteriores ficarao salvas e organizadas aqui.'}
            </p>
          </div>
        `;
        this.refreshLucideIcons();
        return;
      }

      const groups = this.groupSessionsByTime(filteredSessions);
      let html = '';

      for (const group of groups) {
        html += `
          <div class="history-group space-y-2">
            <div class="flex items-center justify-between px-1">
              <span class="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-bold">${group.groupName}</span>
              <span class="text-[10px] font-mono text-slate-500">${group.sessions.length}</span>
            </div>
            <div class="space-y-1.5">
        `;

        for (const s of group.sessions) {
          const isActive = (s.session_id === activeSessionId);
          const domain = this.classifyDomain(s);
          const timeFormatted = this.formatSessionTime(s.updated_at || s.created_at);
          const msgCount = s.message_count || 1;
          const displayTitle = this.escapeHtml(s.title || 'Conversa sem titulo');

          html += `
            <div
              class="history-session-card group relative p-3 rounded-xl border transition-all cursor-pointer flex items-start justify-between gap-2.5 ${
                isActive
                  ? 'bg-cyan-950/25 border-cyan-500/50 shadow-sm shadow-cyan-950/40 ring-1 ring-cyan-500/20'
                  : 'bg-slate-900/50 hover:bg-slate-900/90 border-white/5 hover:border-cyan-500/30'
              }"
              data-session-id="${s.session_id}"
              role="button"
              tabindex="0"
              aria-label="Abrir conversa: ${displayTitle}"
            >
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-1.5 mb-1.5 flex-wrap">
                  <span class="px-2 py-0.5 rounded-full text-[10px] font-sans font-semibold flex items-center gap-1 ${domain.badgeClass}">
                    <i data-lucide="${domain.icon}" class="w-3 h-3"></i>
                    <span>${domain.label}</span>
                  </span>
                  ${isActive ? '<span class="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">ATIVA</span>' : ''}
                </div>
                <h4 class="text-xs font-medium text-slate-200 line-clamp-2 leading-snug group-hover:text-white transition-colors">
                  ${displayTitle}
                </h4>
                <div class="flex items-center gap-2 mt-2 text-[10px] font-mono text-slate-500">
                  <span class="flex items-center gap-1">
                    <i data-lucide="clock" class="w-2.5 h-2.5"></i>
                    ${timeFormatted}
                  </span>
                  <span>-</span>
                  <span class="flex items-center gap-1">
                    <i data-lucide="message-square" class="w-2.5 h-2.5"></i>
                    ${msgCount} ${msgCount === 1 ? 'msg' : 'msgs'}
                  </span>
                </div>
              </div>

              <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity flex-shrink-0 pt-0.5">
                <button
                  type="button"
                  class="btn-delete-session p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 border border-transparent hover:border-rose-500/20 transition-all"
                  data-delete-session-id="${s.session_id}"
                  title="Excluir esta conversa"
                  aria-label="Excluir conversa ${displayTitle}"
                >
                  <i data-lucide="trash-2" class="w-3.5 h-3.5 pointer-events-none"></i>
                </button>
              </div>
            </div>
          `;
        }

        html += `
            </div>
          </div>
        `;
      }

      this.groupsContainerEl.innerHTML = html;
      this.attachCardEvents();
      this.refreshLucideIcons();
    }

    attachCardEvents() {
      if (!this.groupsContainerEl) return;

      const cards = this.groupsContainerEl.querySelectorAll('.history-session-card');
      cards.forEach(card => {
        card.addEventListener('click', (e) => {
          if (e.target.closest('.btn-delete-session')) return;
          const sessionId = card.getAttribute('data-session-id');
          if (sessionId) {
            this.switchSession(sessionId);
          }
        });

        card.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            if (e.target.closest('.btn-delete-session')) return;
            e.preventDefault();
            const sessionId = card.getAttribute('data-session-id');
            if (sessionId) {
              this.switchSession(sessionId);
            }
          }
        });
      });

      const delBtns = this.groupsContainerEl.querySelectorAll('.btn-delete-session');
      delBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          e.preventDefault();
          const sessionId = btn.getAttribute('data-delete-session-id');
          if (sessionId) {
            this.deleteSession(sessionId, e);
          }
        });
      });
    }

    async switchSession(sessionId) {
      if (!sessionId) return;

      const activeId = window.AuraStorage ? window.AuraStorage.getActiveSessionId() : null;
      if (sessionId === activeId && window.auraChat && window.auraChat.sessionId === sessionId) {
        this.close();
        return;
      }

      if (window.AuraStorage && typeof window.AuraStorage.setActiveSessionId === 'function') {
        window.AuraStorage.setActiveSessionId(sessionId);
      }

      if (window.auraChat) {
        window.auraChat.sessionId = sessionId;
        window.auraChat.renderSessionId();
        await window.auraChat.restoreChatHistory();
      }

      this.close();
      this.renderHistory(this.currentSearchFilter);
    }

    async deleteSession(sessionId, event) {
      if (event) {
        event.stopPropagation();
        event.preventDefault();
      }

      if (!window.confirm('Deseja excluir esta conversa do historico?')) {
        return;
      }

      try {
        if (window.AuraStorage && typeof window.AuraStorage.deleteSession === 'function') {
          await window.AuraStorage.deleteSession(sessionId);
        }

        if (typeof fetch !== 'undefined') {
          fetch(`/api/v1/aura/sessions/${sessionId}`, { method: 'DELETE' }).catch(() => {});
        }

        const activeId = window.AuraStorage ? window.AuraStorage.getActiveSessionId() : null;
        if (sessionId === activeId) {
          if (window.auraChat && typeof window.auraChat.clearSession === 'function') {
            window.auraChat.clearSession();
          }
        }

        await this.renderHistory(this.currentSearchFilter);
      } catch (err) {
        console.warn('[AuraHistoryDrawer] Falha ao excluir sessao:', err);
      }
    }

    async handleClearAll() {
      if (!window.confirm('Deseja realmente limpar todo o historico de conversas? Esta acao nao pode ser desfeita.')) {
        return;
      }

      try {
        // 1. Busca todas as sessoes ativas no backend SQLite
        let backendSessions = [];
        if (typeof fetch !== 'undefined') {
          try {
            const resp = await fetch('/api/v1/aura/sessions?limit=100');
            if (resp.ok) {
              const data = await resp.json();
              if (data.status === 'success' && Array.isArray(data.sessions)) {
                backendSessions = data.sessions;
              }
            }
          } catch (_) {}
        }

        // 2. Exclui cada sessao no backend SQLite (funciona imediatamente sem depender de restart do servico)
        if (backendSessions.length > 0 && typeof fetch !== 'undefined') {
          await Promise.all(
            backendSessions.map((s) =>
              fetch(`/api/v1/aura/sessions/${encodeURIComponent(s.session_id)}`, { method: 'DELETE' }).catch(() => {})
            )
          );
        }

        // 3. Tenta tambem o endpoint de limpeza em massa
        if (typeof fetch !== 'undefined') {
          try {
            await fetch('/api/v1/aura/sessions', { method: 'DELETE' });
          } catch (_) {}
        }

        // 4. Limpa todas as sessoes locais do IndexedDB e localStorage
        if (window.AuraStorage && typeof window.AuraStorage.clearAllSessions === 'function') {
          await window.AuraStorage.clearAllSessions();
        } else if (window.AuraStorage && typeof window.AuraStorage.clearCurrentSession === 'function') {
          await window.AuraStorage.clearCurrentSession();
        }

        // 5. Reinicia o chat para uma nova conversa limpa
        if (window.auraChat && typeof window.auraChat.clearSession === 'function') {
          window.auraChat.clearSession();
        }

        // 6. Atualiza a lista na gaveta
        await this.renderHistory('');
      } catch (err) {
        console.warn('[AuraHistoryDrawer] Falha ao limpar todo o historico:', err);
      }
    }

    handleNewChat() {
      if (window.auraChat && typeof window.auraChat.clearSession === 'function') {
        window.auraChat.clearSession();
      }
      this.close();
      this.renderHistory(this.currentSearchFilter);
    }

    refreshLucideIcons() {
      if (typeof window !== 'undefined' && window.lucide && typeof window.lucide.createIcons === 'function') {
        try {
          window.lucide.createIcons();
        } catch (_) {}
      }
    }
  }

  // Helpers globais de abertura resiliente
  window.openAuraHistory = function () {
    if (!window.auraHistoryDrawer && typeof AuraHistoryDrawerController !== 'undefined') {
      window.auraHistoryDrawer = new AuraHistoryDrawerController();
    }
    if (window.auraHistoryDrawer) {
      window.auraHistoryDrawer.open();
    }
  };

  window.toggleAuraHistory = function () {
    if (!window.auraHistoryDrawer && typeof AuraHistoryDrawerController !== 'undefined') {
      window.auraHistoryDrawer = new AuraHistoryDrawerController();
    }
    if (window.auraHistoryDrawer) {
      window.auraHistoryDrawer.toggle();
    }
  };

  window.closeAuraHistory = function () {
    if (window.auraHistoryDrawer) {
      window.auraHistoryDrawer.close();
    }
  };

  // Inicializacao automatica quando DOM estiver pronto
  if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => {
        if (!window.auraHistoryDrawer) {
          window.auraHistoryDrawer = new AuraHistoryDrawerController();
        }
      });
    } else {
      if (!window.auraHistoryDrawer) {
        window.auraHistoryDrawer = new AuraHistoryDrawerController();
      }
    }
  }

  window.AuraHistoryDrawerController = AuraHistoryDrawerController;
})(typeof window !== 'undefined' ? window : this);
