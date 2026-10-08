/**
 * AURA State Manager (Fase 4: P1)
 * Motor de Gestao de Estado no Cliente, Idempotencia, State Locking & Optimistic UI
 *
 * Arquitetura Zero-Bundler:
 * - Compativel nativamente via <script> no navegador (window.AuraStateManager / window.auraStateManager)
 * - Compativel com CommonJS (require/module.exports) para testes headless no Node.js
 *
 * Funcionalidades centrais:
 * 1. Tabela hash de widgets indexada por tool_call_id
 * 2. State Locking imediato contra cliques concorrentes ou duplicados
 * 3. Idempotencia local com conjunto (Set) de acoes executadas
 * 4. Optimistic UI com snapshots de rollback resiliente em caso de falha
 * 5. Inspecao de TTL (Stale Action Guard: padrao 15 minutos / 900s)
 * 6. Persistencia de curto prazo isolada em sessionStorage com try-catch
 */

(function (global) {
  'use strict';

  class AuraStateManager {
    constructor(options = {}) {
      this.storageKey = (options && options.storageKey) || 'aura_state_manager_v1';
      this.widgets = new Map(); // tool_call_id -> widgetEntry
      this.executedActions = new Set(); // action_id
      this.actionResults = new Map(); // action_id -> result
      this.loadFromSessionStorage();
    }

    /**
     * Registra um novo micro-widget no gerenciador de estado.
     * @param {string} toolCallId - Identificador RFC 4122 v4 da invocacao
     * @param {Object} [initialProps={}] - Propriedades iniciais recebidas no envelope
     * @param {number} [ttlSeconds=900] - Tempo de vida util da proposta em segundos
     * @param {number|string|Date} [customTimestamp=null] - Timestamp de criacao da proposta
     * @returns {Object} Entrada do widget registrada
     */
    registerWidget(toolCallId, initialProps = {}, ttlSeconds = 900, customTimestamp = null) {
      if (!toolCallId) {
        throw new Error('[AuraStateManager] toolCallId obrigatorio para registro de widget');
      }
      const idStr = String(toolCallId).trim();
      const ttl = Number(ttlSeconds) > 0 ? Number(ttlSeconds) : 900;

      let ts = Date.now();
      const rawTs = customTimestamp || (initialProps && (initialProps.timestamp || initialProps.created_at));
      if (rawTs) {
        if (typeof rawTs === 'number') {
          ts = rawTs;
        } else if (typeof rawTs === 'string') {
          const parsed = Date.parse(rawTs);
          ts = isNaN(parsed) ? (Number(rawTs) || Date.now()) : parsed;
        } else if (rawTs instanceof Date) {
          ts = rawTs.getTime();
        }
      }

      let entry = this.widgets.get(idStr);
      if (entry) {
        if (initialProps && typeof initialProps === 'object') {
          entry.props = Object.assign({}, entry.props, initialProps);
        }
        entry.ttlSeconds = ttl;
        if (rawTs && (!entry.timestamp || entry.timestamp > ts)) {
          entry.timestamp = ts;
        }
        return entry;
      }

      entry = {
        toolCallId: idStr,
        initialProps: (initialProps && typeof initialProps === 'object') ? Object.assign({}, initialProps) : {},
        props: (initialProps && typeof initialProps === 'object') ? Object.assign({}, initialProps) : {},
        snapshot: null,
        state: {
          status: 'proposed', // 'proposed' | 'locked' | 'optimistic' | 'committed' | 'failed' | 'expired'
          isLocked: false,
          lockedActionId: null
        },
        isLocked: false,
        lockedActionId: null,
        optimisticData: null,
        result: null,
        timestamp: ts,
        ttlSeconds: ttl
      };

      this.widgets.set(idStr, entry);
      this.persistToSessionStorage();
      return entry;
    }

    /**
     * Recupera entrada de um widget pelo tool_call_id.
     * @param {string} toolCallId
     * @returns {Object|null}
     */
    getWidget(toolCallId) {
      if (!toolCallId) return null;
      return this.widgets.get(String(toolCallId).trim()) || null;
    }

    /**
     * Aplica State Locking imediato no widget para prevenir duplo clique.
     * @param {string} toolCallId
     * @param {string} [actionId=null]
     * @returns {Object|null}
     */
    lockWidget(toolCallId, actionId = null) {
      let entry = this.getWidget(toolCallId);
      if (!entry) {
        entry = this.registerWidget(toolCallId);
      }
      entry.isLocked = true;
      entry.lockedActionId = actionId ? String(actionId).trim() : null;
      entry.state.status = 'locked';
      entry.state.isLocked = true;
      entry.state.lockedActionId = entry.lockedActionId;

      this.persistToSessionStorage();
      return entry;
    }

    /**
     * Desbloqueia o widget permitindo novas interacoes.
     * @param {string} toolCallId
     * @returns {Object|null}
     */
    unlockWidget(toolCallId) {
      const entry = this.getWidget(toolCallId);
      if (!entry) return null;

      entry.isLocked = false;
      entry.lockedActionId = null;
      if (entry.state.status === 'locked' || entry.state.status === 'optimistic') {
        entry.state.status = 'proposed';
      }
      entry.state.isLocked = false;
      entry.state.lockedActionId = null;

      this.persistToSessionStorage();
      return entry;
    }

    /**
     * Verifica se uma acao ja foi executada previamente (Idempotencia).
     * @param {string} actionId
     * @returns {boolean}
     */
    isActionExecuted(actionId) {
      if (!actionId) return false;
      return this.executedActions.has(String(actionId).trim());
    }

    /**
     * Marca uma acao como executada com sucesso e persiste historico.
     * @param {string} actionId
     * @param {Object} [result=null]
     * @returns {boolean}
     */
    markActionExecuted(actionId, result = null) {
      if (!actionId) return false;
      const actIdStr = String(actionId).trim();
      this.executedActions.add(actIdStr);
      if (result !== undefined && result !== null) {
        this.actionResults.set(actIdStr, result);
      }
      this.persistToSessionStorage();
      return true;
    }

    /**
     * Avalia se uma acao ou proposta expirou de acordo com seu timestamp e TTL (padrao: 15 min / 900s).
     * @param {number|string|Date} timestamp - Momento de criacao da proposta
     * @param {number} [ttlSeconds=900] - Limite em segundos
     * @returns {boolean} True se expirado
     */
    isStale(timestamp, ttlSeconds = 900) {
      if (!timestamp) return false;
      let ts = 0;
      if (typeof timestamp === 'number') {
        ts = timestamp;
      } else if (typeof timestamp === 'string') {
        const parsed = Date.parse(timestamp);
        ts = isNaN(parsed) ? Number(timestamp) : parsed;
      } else if (timestamp instanceof Date) {
        ts = timestamp.getTime();
      }

      if (isNaN(ts) || ts <= 0) return false;
      const ttl = (Number(ttlSeconds) > 0 ? Number(ttlSeconds) : 900) * 1000;
      return (Date.now() - ts) > ttl;
    }

    /**
     * Aplica mutacao de interface otimista (Optimistic UI) salvando snapshot previo para rollback.
     * @param {string} toolCallId
     * @param {Object} optimisticData
     * @returns {Object} Entrada do widget atualizada
     */
    applyOptimisticState(toolCallId, optimisticData = {}) {
      let entry = this.getWidget(toolCallId);
      if (!entry) {
        entry = this.registerWidget(toolCallId);
      }

      // 1. Salva snapshot do estado anterior para reversao perfeita em caso de falha
      entry.snapshot = {
        state: Object.assign({}, entry.state),
        isLocked: entry.isLocked,
        lockedActionId: entry.lockedActionId,
        optimisticData: entry.optimisticData
      };

      // 2. Normaliza dados otimistas
      const data = (typeof optimisticData === 'object' && optimisticData !== null)
        ? optimisticData
        : { feedback: String(optimisticData) };

      entry.isLocked = true;
      if (data.actionId) {
        entry.lockedActionId = String(data.actionId).trim();
      }
      entry.optimisticData = data;
      entry.state = Object.assign({}, entry.state, {
        status: data.status || 'optimistic',
        isLocked: true,
        lockedActionId: entry.lockedActionId
      }, data);

      this.persistToSessionStorage();
      return entry;
    }

    /**
     * Reverte mutacao otimista restaurando snapshot anterior (Rollback Limpo).
     * @param {string} toolCallId
     * @returns {Object|null}
     */
    rollbackOptimisticState(toolCallId) {
      const entry = this.getWidget(toolCallId);
      if (!entry) return null;

      if (entry.snapshot) {
        entry.state = Object.assign({}, entry.snapshot.state);
        entry.isLocked = entry.snapshot.isLocked !== undefined ? entry.snapshot.isLocked : false;
        entry.lockedActionId = entry.snapshot.lockedActionId || null;
        entry.optimisticData = entry.snapshot.optimisticData || null;
        entry.snapshot = null;
      } else {
        entry.isLocked = false;
        entry.lockedActionId = null;
        entry.optimisticData = null;
        entry.state = {
          status: 'proposed',
          isLocked: false,
          lockedActionId: null
        };
      }

      this.persistToSessionStorage();
      return entry;
    }

    /**
     * Consolida a confirmacao com sucesso da acao no backend (Action Voucher).
     * @param {string} toolCallId
     * @param {Object} [result={}]
     * @returns {Object|null}
     */
    finalizeSuccessState(toolCallId, result = {}) {
      const entry = this.getWidget(toolCallId);
      if (!entry) return null;

      const actId = entry.lockedActionId;
      entry.isLocked = false;
      entry.lockedActionId = null;
      entry.snapshot = null;
      entry.result = result;
      entry.status = 'committed';
      entry.state = Object.assign({}, entry.state, {
        status: 'committed',
        isLocked: false,
        lockedActionId: null,
        result: result
      });

      if (actId) {
        this.markActionExecuted(actId, result);
      }

      this.persistToSessionStorage();
      return entry;
    }

    /**
     * Salva o estado dos widgets e acoes executadas no sessionStorage de forma segura.
     * @returns {boolean} True se persistido
     */
    persistToSessionStorage() {
      try {
        const storage = (typeof window !== 'undefined' && window.sessionStorage) ||
                        (typeof globalThis !== 'undefined' && globalThis.sessionStorage) ||
                        null;
        if (!storage || typeof storage.setItem !== 'function') return false;

        const widgetsObj = {};
        for (const [k, v] of this.widgets.entries()) {
          widgetsObj[k] = {
            toolCallId: v.toolCallId,
            initialProps: v.initialProps,
            props: v.props,
            state: v.state,
            isLocked: v.isLocked,
            lockedActionId: v.lockedActionId,
            optimisticData: v.optimisticData,
            result: v.result,
            timestamp: v.timestamp,
            ttlSeconds: v.ttlSeconds
          };
        }

        const executedActionsArr = Array.from(this.executedActions);
        const actionResultsObj = {};
        for (const [k, v] of this.actionResults.entries()) {
          actionResultsObj[k] = v;
        }

        const serialized = JSON.stringify({
          widgets: widgetsObj,
          executedActions: executedActionsArr,
          actionResults: actionResultsObj,
          savedAt: Date.now()
        });

        storage.setItem(this.storageKey, serialized);
        return true;
      } catch (err) {
        return false;
      }
    }

    /**
     * Carrega estado previo do sessionStorage com tratamento isolado contra erros.
     * @returns {boolean} True se recuperado com sucesso
     */
    loadFromSessionStorage() {
      try {
        const storage = (typeof window !== 'undefined' && window.sessionStorage) ||
                        (typeof globalThis !== 'undefined' && globalThis.sessionStorage) ||
                        null;
        if (!storage || typeof storage.getItem !== 'function') return false;

        const raw = storage.getItem(this.storageKey);
        if (!raw) return false;

        const data = JSON.parse(raw);
        if (!data || typeof data !== 'object') return false;

        if (data.widgets && typeof data.widgets === 'object') {
          for (const [k, v] of Object.entries(data.widgets)) {
            if (v && v.toolCallId) {
              this.widgets.set(k, {
                ...v,
                snapshot: null
              });
            }
          }
        }

        if (Array.isArray(data.executedActions)) {
          data.executedActions.forEach(act => {
            if (act) this.executedActions.add(String(act));
          });
        } else if (data.executedActions && typeof data.executedActions === 'object') {
          Object.keys(data.executedActions).forEach(act => {
            if (act) this.executedActions.add(String(act));
          });
        }

        if (data.actionResults && typeof data.actionResults === 'object') {
          for (const [k, v] of Object.entries(data.actionResults)) {
            this.actionResults.set(k, v);
          }
        }

        return true;
      } catch (err) {
        return false;
      }
    }

    /**
     * Verifica se determinado widget especifico esta expirado pelo TTL.
     * @param {string} toolCallId
     * @returns {boolean}
     */
    isWidgetStale(toolCallId) {
      const entry = this.getWidget(toolCallId);
      if (!entry) return false;
      return this.isStale(entry.timestamp, entry.ttlSeconds);
    }

    /**
     * Limpa o estado em memoria e na storage (util para testes e reinicializacao).
     */
    clear() {
      this.widgets.clear();
      this.executedActions.clear();
      this.actionResults.clear();
      try {
        const storage = (typeof window !== 'undefined' && window.sessionStorage) ||
                        (typeof globalThis !== 'undefined' && globalThis.sessionStorage) ||
                        null;
        if (storage && typeof storage.removeItem === 'function') {
          storage.removeItem(this.storageKey);
        }
      } catch (_) {}
    }
  }

  // Instancia singleton padrao
  const auraStateManager = new AuraStateManager();

  // 1. Exportacao Global no Navegador (Window)
  if (typeof window !== 'undefined') {
    window.AuraStateManager = AuraStateManager;
    window.auraStateManager = auraStateManager;

    try {
      window.dispatchEvent(new CustomEvent('aura:state-manager-ready', {
        detail: { AuraStateManager, auraStateManager }
      }));
    } catch (_) {}
  }

  // 2. Exportacao Global em globalThis (Node.js ou WebWorkers)
  if (typeof globalThis !== 'undefined') {
    globalThis.AuraStateManager = AuraStateManager;
    globalThis.auraStateManager = auraStateManager;
  }

  // 3. Exportacao CommonJS para testes headless e automacao (Node.js)
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
      AuraStateManager,
      auraStateManager
    };
  }

})(typeof globalThis !== 'undefined' ? globalThis : (typeof window !== 'undefined' ? window : this));
