/**
 * AURA Local Cache & Session Storage Manager (Fase P3 & GenUI Persistence)
 * Armazenamento local de alta performance com IndexedDB nativo e fallback para localStorage.
 * Garante que a conversa, o historico e os envelopes GenUI sobrevivam ao F5 / recarregamento.
 * Zero dependencias externas, zero travessoes.
 */

(function (window) {
  'use strict';

  const DB_NAME = 'AuraChatCacheDB';
  const DB_VERSION = 1;
  const STORE_SESSIONS = 'sessions';
  const STORE_MESSAGES = 'messages';
  const ACTIVE_SESSION_KEY = 'aura_active_session_id';

  class AuraLocalCacheManager {
    constructor() {
      this.db = null;
      this.isIndexedDBAvailable = typeof window !== 'undefined' && 'indexedDB' in window;
      this.initPromise = null;
    }

    /**
     * Inicializa o banco de dados IndexedDB de forma idempotente.
     */
    async init() {
      if (this.initPromise) return this.initPromise;

      this.initPromise = new Promise((resolve) => {
        if (!this.isIndexedDBAvailable) {
          console.warn('[AuraStorage] IndexedDB indisponivel. Operando em modo contingencia localStorage.');
          return resolve(false);
        }

        try {
          const req = window.indexedDB.open(DB_NAME, DB_VERSION);

          req.onupgradeneeded = (event) => {
            const db = event.target.result;

            // Store de Sessoes
            if (!db.objectStoreNames.contains(STORE_SESSIONS)) {
              const sessionStore = db.createObjectStore(STORE_SESSIONS, { keyPath: 'session_id' });
              sessionStore.createIndex('idx_updated_at', 'updated_at', { unique: false });
            }

            // Store de Mensagens
            if (!db.objectStoreNames.contains(STORE_MESSAGES)) {
              const msgStore = db.createObjectStore(STORE_MESSAGES, { keyPath: 'id' });
              msgStore.createIndex('idx_session_id', 'session_id', { unique: false });
              msgStore.createIndex('idx_timestamp', 'timestamp', { unique: false });
            }
          };

          req.onsuccess = (event) => {
            this.db = event.target.result;
            resolve(true);
          };

          req.onerror = (err) => {
            console.warn('[AuraStorage] Falha ao abrir IndexedDB:', err);
            this.isIndexedDBAvailable = false;
            resolve(false);
          };
        } catch (e) {
          console.warn('[AuraStorage] Excecao ao inicializar IndexedDB:', e);
          this.isIndexedDBAvailable = false;
          resolve(false);
        }
      });

      return this.initPromise;
    }

    /**
     * Gera identificador unico de sessao.
     */
    generateSessionId() {
      return 'aura_ui_' + Math.random().toString(36).substring(2, 10);
    }

    /**
     * Retorna a sessao ativa persistida no localStorage ou cria uma nova se nao existir.
     */
    getActiveSessionId() {
      try {
        let sid = localStorage.getItem(ACTIVE_SESSION_KEY);
        if (!sid || sid.trim() === '') {
          sid = this.generateSessionId();
          localStorage.setItem(ACTIVE_SESSION_KEY, sid);
        }
        return sid;
      } catch (_) {
        return this.generateSessionId();
      }
    }

    /**
     * Define a sessao ativa no localStorage.
     */
    setActiveSessionId(sessionId) {
      try {
        if (sessionId) {
          localStorage.setItem(ACTIVE_SESSION_KEY, sessionId);
        }
      } catch (_) {}
    }

    /**
     * Inicia uma nova conversa e define como sessao ativa.
     */
    async startNewSession(title = 'Nova Conversa') {
      const newId = this.generateSessionId();
      this.setActiveSessionId(newId);

      const sessionObj = {
        session_id: newId,
        title: title,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        message_count: 0
      };

      await this._putSession(sessionObj);
      return newId;
    }

    /**
     * Salva uma mensagem na sessao ativa.
     */
    async saveMessage(sessionId, message) {
      if (!sessionId || !message) return null;
      await this.init();

      const msgId = message.id || 'msg_' + Date.now() + '_' + Math.random().toString(36).substring(2, 6);
      const timestamp = message.timestamp || Date.now();

      const record = {
        id: msgId,
        session_id: sessionId,
        role: message.role || 'user',
        text: message.text || '',
        intent: message.intent || null,
        genuiEnvelope: message.genuiEnvelope || message.genui || null,
        toolName: message.toolName || null,
        toolResult: message.toolResult || null,
        telemetry: message.telemetry || null,
        timestamp: timestamp
      };

      // 1. Grava mensagem no IndexedDB ou localStorage
      if (this.db) {
        await new Promise((resolve) => {
          try {
            const tx = this.db.transaction([STORE_MESSAGES], 'readwrite');
            const store = tx.objectStore(STORE_MESSAGES);
            store.put(record);
            tx.oncomplete = () => resolve(true);
            tx.onerror = () => resolve(false);
          } catch (_) {
            resolve(false);
          }
        });
      } else {
        this._saveMessageFallback(sessionId, record);
      }

      // 2. Atualiza resumo da sessao
      await this._updateSessionMetadata(sessionId, record);
      return record;
    }

    /**
     * Recupera todas as mensagens de uma sessao em ordem cronologica.
     */
    async getMessages(sessionId) {
      if (!sessionId) return [];
      await this.init();

      if (this.db) {
        return new Promise((resolve) => {
          try {
            const tx = this.db.transaction([STORE_MESSAGES], 'readonly');
            const store = tx.objectStore(STORE_MESSAGES);
            const index = store.index('idx_session_id');
            const req = index.getAll(IDBKeyRange.only(sessionId));

            req.onsuccess = () => {
              const msgs = req.result || [];
              msgs.sort((a, b) => (a.timestamp || 0) - (b.timestamp || 0));
              resolve(msgs);
            };

            req.onerror = () => {
              resolve(this._getMessagesFallback(sessionId));
            };
          } catch (_) {
            resolve(this._getMessagesFallback(sessionId));
          }
        });
      }

      return this._getMessagesFallback(sessionId);
    }

    /**
     * Lista todas as sessoes registradas localmente.
     */
    async listSessions(limit = 30) {
      await this.init();

      if (this.db) {
        return new Promise((resolve) => {
          try {
            const tx = this.db.transaction([STORE_SESSIONS], 'readonly');
            const store = tx.objectStore(STORE_SESSIONS);
            const req = store.getAll();

            req.onsuccess = () => {
              const list = req.result || [];
              list.sort((a, b) => new Date(b.updated_at || 0) - new Date(a.updated_at || 0));
              resolve(list.slice(0, limit));
            };

            req.onerror = () => resolve(this._listSessionsFallback());
          } catch (_) {
            resolve(this._listSessionsFallback());
          }
        });
      }

      return this._listSessionsFallback();
    }

    /**
     * Exclui uma sessao e todas as mensagens associadas.
     */
    async deleteSession(sessionId) {
      if (!sessionId) return false;
      await this.init();

      if (this.db) {
        return new Promise((resolve) => {
          try {
            const tx = this.db.transaction([STORE_SESSIONS, STORE_MESSAGES], 'readwrite');
            tx.objectStore(STORE_SESSIONS).delete(sessionId);

            const msgStore = tx.objectStore(STORE_MESSAGES);
            const index = msgStore.index('idx_session_id');
            const req = index.openCursor(IDBKeyRange.only(sessionId));

            req.onsuccess = (e) => {
              const cursor = e.target.result;
              if (cursor) {
                cursor.delete();
                cursor.continue();
              }
            };

            tx.oncomplete = () => resolve(true);
            tx.onerror = () => resolve(false);
          } catch (_) {
            resolve(false);
          }
        });
      } else {
        this._deleteSessionFallback(sessionId);
        return true;
      }
    }

    /**
     * Limpa as mensagens da sessao ativa e inicia uma nova.
     */
    async clearCurrentSession() {
      const currentId = this.getActiveSessionId();
      await this.deleteSession(currentId);
      return this.startNewSession();
    }

    /**
     * Limpa absolutamente todas as sessoes e mensagens locais do IndexedDB e localStorage.
     */
    async clearAllSessions() {
      await this.init();
      if (this.db) {
        await new Promise((resolve) => {
          try {
            const tx = this.db.transaction([STORE_SESSIONS, STORE_MESSAGES], 'readwrite');
            tx.objectStore(STORE_SESSIONS).clear();
            tx.objectStore(STORE_MESSAGES).clear();
            tx.oncomplete = () => resolve(true);
            tx.onerror = () => resolve(false);
          } catch (_) {
            resolve(false);
          }
        });
      }
      this._clearAllFallback();
      return this.startNewSession();
    }

    _clearAllFallback() {
      try {
        if (typeof window !== 'undefined' && window.localStorage) {
          const toRemove = [];
          for (let i = 0; i < window.localStorage.length; i++) {
            const k = window.localStorage.key(i);
            if (k && (k.startsWith('aura_session_') || k.startsWith('aura_msgs_') || k === ACTIVE_SESSION_KEY)) {
              toRemove.push(k);
            }
          }
          toRemove.forEach((k) => window.localStorage.removeItem(k));
        }
      } catch (_) {}
    }

    // =========================================================================
    // METODOS AUXILIARES E FALLBACKS (localStorage)
    // =========================================================================

    async _putSession(sessionObj) {
      if (this.db) {
        return new Promise((resolve) => {
          try {
            const tx = this.db.transaction([STORE_SESSIONS], 'readwrite');
            tx.objectStore(STORE_SESSIONS).put(sessionObj);
            tx.oncomplete = () => resolve(true);
            tx.onerror = () => resolve(false);
          } catch (_) {
            resolve(false);
          }
        });
      }
      this._saveSessionFallback(sessionObj);
      return true;
    }

    async _updateSessionMetadata(sessionId, messageRecord) {
      const nowIso = new Date().toISOString();
      let session = null;

      if (this.db) {
        session = await new Promise((resolve) => {
          try {
            const tx = this.db.transaction([STORE_SESSIONS], 'readonly');
            const req = tx.objectStore(STORE_SESSIONS).get(sessionId);
            req.onsuccess = () => resolve(req.result || null);
            req.onerror = () => resolve(null);
          } catch (_) {
            resolve(null);
          }
        });
      }

      if (!session) {
        let title = 'Nova Conversa';
        if (messageRecord.role === 'user' && messageRecord.text) {
          title = messageRecord.text.trim();
          if (title.length > 55) title = title.substring(0, 52) + '...';
        }
        session = {
          session_id: sessionId,
          title: title,
          created_at: nowIso,
          updated_at: nowIso,
          message_count: 1
        };
      } else {
        session.updated_at = nowIso;
        session.message_count = (session.message_count || 0) + 1;
        if (session.title === 'Nova Conversa' && messageRecord.role === 'user' && messageRecord.text) {
          let title = messageRecord.text.trim();
          if (title.length > 55) title = title.substring(0, 52) + '...';
          session.title = title;
        }
      }

      await this._putSession(session);
    }

    _saveMessageFallback(sessionId, record) {
      try {
        const key = `aura_msgs_${sessionId}`;
        const raw = localStorage.getItem(key);
        const list = raw ? JSON.parse(raw) : [];
        list.push(record);
        if (list.length > 100) list.shift();
        localStorage.setItem(key, JSON.stringify(list));
      } catch (_) {}
    }

    _getMessagesFallback(sessionId) {
      try {
        const key = `aura_msgs_${sessionId}`;
        const raw = localStorage.getItem(key);
        return raw ? JSON.parse(raw) : [];
      } catch (_) {
        return [];
      }
    }

    _saveSessionFallback(sessionObj) {
      try {
        const raw = localStorage.getItem('aura_session_index');
        const map = raw ? JSON.parse(raw) : {};
        map[sessionObj.session_id] = sessionObj;
        localStorage.setItem('aura_session_index', JSON.stringify(map));
      } catch (_) {}
    }

    _listSessionsFallback() {
      try {
        const raw = localStorage.getItem('aura_session_index');
        if (!raw) return [];
        const map = JSON.parse(raw);
        const list = Object.values(map);
        list.sort((a, b) => new Date(b.updated_at || 0) - new Date(a.updated_at || 0));
        return list;
      } catch (_) {
        return [];
      }
    }

    _deleteSessionFallback(sessionId) {
      try {
        localStorage.removeItem(`aura_msgs_${sessionId}`);
        const raw = localStorage.getItem('aura_session_index');
        if (raw) {
          const map = JSON.parse(raw);
          delete map[sessionId];
          localStorage.setItem('aura_session_index', JSON.stringify(map));
        }
      } catch (_) {}
    }
  }

  // Exportacao global
  window.AuraStorage = new AuraLocalCacheManager();

})(typeof window !== 'undefined' ? window : this);
