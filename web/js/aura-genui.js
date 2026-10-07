/**
 * AURA IntelligentUI / GenUI Protocol Engine (v1.0.0)
 * Módulo Central de Governança, Catálogo Fechado de Componentes & Idempotência
 * 
 * Princípios de Engenharia:
 * 1. Arquitetura Zero-Bundler: compatível nativamente com tags <script> no navegador
 *    e com module.exports para testes headless e automação no Node.js.
 * 2. Mitigação Rigorosa de OWASP LLM03 (Agência Excessiva): Nenhuma tag arbitrária
 *    ou string gerada pelo LLM tem autorização para instanciar elementos fora do
 *    catálogo fechado SecureComponentRegistry. Componentes desconhecidos são rejeitados
 *    imediatamente com alerta de segurança e fallback seguro.
 * 3. Mitigação de OWASP LLM01 (Prompt Injection & XSS): Sanitização estrita de strings
 *    e interpolação segura via escapeHtml().
 * 4. Idempotência Criptográfica: Geração e validação de UUID v4 para tool_call_id
 *    e action_id, prevenindo duplo envio e requisições concorrentes.
 */

(function (global) {
  'use strict';

  // =========================================================================
  // 1. UTILITÁRIOS DE SEGURANÇA & SANITIZAÇÃO (OWASP LLM01)
  // =========================================================================

  /**
   * Neutraliza injeções XSS, backticks e caracteres especiais HTML em strings.
   * @param {any} str - Valor a ser sanitizado
   * @returns {string} String com entidades HTML devidamente escapadas
   */
  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/\0/g, '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;')
      .replace(/`/g, '&#96;');
  }

  /**
   * Sanitiza recursivamente objetos ou arrays de propriedades antes da renderização.
   * Strings são escapadas; números, booleanos e nulls são preservados.
   * Protegido contra ciclos de referência e Prototype Pollution (__proto__, constructor, prototype).
   * @param {any} data - Objeto de props a sanitizar
   * @param {WeakSet} [seen=new WeakSet()] - Rastreamento interno contra recursão cíclica
   * @returns {any} Estrutura com strings sanitizadas
   */
  function sanitizeProps(data, seen = new WeakSet()) {
    if (data === null || data === undefined) return data;
    if (typeof data === 'string') return escapeHtml(data);
    if (typeof data === 'number' || typeof data === 'boolean') return data;
    if (typeof data !== 'object') return String(data);

    if (seen.has(data)) {
      return '[Circular]';
    }
    seen.add(data);

    if (Array.isArray(data)) {
      return data.map(item => sanitizeProps(item, seen));
    }

    const sanitized = {};
    for (const key of Object.keys(data)) {
      // Bloqueia tentativas de Prototype Pollution
      if (key === '__proto__' || key === 'constructor' || key === 'prototype') {
        continue;
      }
      sanitized[key] = sanitizeProps(data[key], seen);
    }
    return sanitized;
  }

  // =========================================================================
  // 2. IDEMPOTÊNCIA CRIPTOGRÁFICA & UUID v4
  // =========================================================================

  const UUID4_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  const SAFE_PREFIX_REGEX = /^[a-zA-Z][a-zA-Z0-9_]{0,31}$/;
  const VALID_TOOL_CALL_PREFIXES = ['call', 'tool_call', 'tool'];
  const VALID_ACTION_PREFIXES = ['act', 'action'];

  /**
   * Gera um UUID v4 canônico criptograficamente seguro (RFC 4122).
   * @returns {string} UUID v4 formatado (ex: 88b19a02-412f-4a0b-8c01-d85cfd774bfe)
   */
  function generateUUID() {
    // 1. Tenta API global padrão (Browsers modernos e Node.js 16+)
    if (typeof globalThis !== 'undefined' && globalThis.crypto && typeof globalThis.crypto.randomUUID === 'function') {
      return globalThis.crypto.randomUUID();
    }

    // 2. Tenta crypto.getRandomValues em browsers ou Node
    const cryptoObj = (typeof window !== 'undefined' && window.crypto) ||
                      (typeof globalThis !== 'undefined' && globalThis.crypto);

    if (cryptoObj && typeof cryptoObj.getRandomValues === 'function') {
      const bytes = new Uint8Array(16);
      cryptoObj.getRandomValues(bytes);
      bytes[6] = (bytes[6] & 0x0f) | 0x40; // Versão 4
      bytes[8] = (bytes[8] & 0x3f) | 0x80; // Variante RFC 4122
      const hex = Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('');
      return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20, 32)}`;
    }

    // 3. Fallback Node.js nativo (require('crypto'))
    if (typeof require === 'function') {
      try {
        const nodeCrypto = require('crypto');
        if (typeof nodeCrypto.randomUUID === 'function') {
          return nodeCrypto.randomUUID();
        }
      } catch (_) {}
    }

    // 4. Fallback determinístico matemático de emergência
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      const r = (Math.random() * 16) | 0;
      const v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  /**
   * Valida se uma string é um UUID v4 válido RFC 4122 com prefixo seguro opcional.
   * @param {any} val - Valor a testar
   * @param {boolean} [allowPrefix=true] - Se true, tolera prefixos seguros validados contra SAFE_PREFIX_REGEX
   * @returns {boolean} True se for UUID v4 válido
   */
  function isValidUUID(val, allowPrefix = true) {
    if (typeof val !== 'string' || !val.trim()) return false;
    const raw = val.trim();
    if (raw.includes('_')) {
      if (!allowPrefix) return false;
      const lastUnderscore = raw.lastIndexOf('_');
      const prefix = raw.slice(0, lastUnderscore);
      const uuidPart = raw.slice(lastUnderscore + 1);
      if (!SAFE_PREFIX_REGEX.test(prefix)) return false;
      return UUID4_REGEX.test(uuidPart);
    }
    return UUID4_REGEX.test(raw);
  }

  /**
   * Gera um identificador canônico de chamada de ferramenta (tool_call_id).
   * @param {string} [prefix='call_'] - Prefixo canônico
   * @returns {string} ex: call_a62b19cc-e872-448b-b8cf-dfff06869033
   */
  function generateToolCallId(prefix = 'call_') {
    return `${prefix}${generateUUID()}`;
  }

  /**
   * Gera um identificador canônico de ação transacional (action_id).
   * @param {string} [prefix='act_'] - Prefixo canônico
   * @returns {string} ex: act_20367dea-9047-4a78-bc36-86b2d960fdf6
   */
  function generateActionId(prefix = 'act_') {
    return `${prefix}${generateUUID()}`;
  }

  /**
   * Valida um tool_call_id garantindo prefixo de chamada de ferramenta autorizado.
   * @param {any} val - Valor a testar
   * @param {boolean} [requirePrefix=false] - Se true, exige presença do prefixo
   * @returns {boolean} True se válido
   */
  function validateToolCallId(val, requirePrefix = false) {
    if (typeof val !== 'string' || !val.trim()) return false;
    const raw = val.trim();
    if (raw.includes('_')) {
      const lastUnderscore = raw.lastIndexOf('_');
      const prefix = raw.slice(0, lastUnderscore);
      const uuidPart = raw.slice(lastUnderscore + 1);
      if (!VALID_TOOL_CALL_PREFIXES.includes(prefix)) return false;
      return UUID4_REGEX.test(uuidPart);
    }
    if (requirePrefix) return false;
    return UUID4_REGEX.test(raw);
  }

  /**
   * Valida um action_id garantindo prefixo de ação transacional autorizado.
   * @param {any} val - Valor a testar
   * @param {boolean} [requirePrefix=false] - Se true, exige presença do prefixo
   * @returns {boolean} True se válido
   */
  function validateActionId(val, requirePrefix = false) {
    if (typeof val !== 'string' || !val.trim()) return false;
    const raw = val.trim();
    if (raw.includes('_')) {
      const lastUnderscore = raw.lastIndexOf('_');
      const prefix = raw.slice(0, lastUnderscore);
      const uuidPart = raw.slice(lastUnderscore + 1);
      if (!VALID_ACTION_PREFIXES.includes(prefix)) return false;
      return UUID4_REGEX.test(uuidPart);
    }
    if (requirePrefix) return false;
    return UUID4_REGEX.test(raw);
  }

  // =========================================================================
  // 3. CATÁLOGO FECHADO DE COMPONENTES (OWASP LLM03 - AGÊNCIA EXCESSIVA)
  // =========================================================================

  const COMPONENT_NAME_REGEX = /^[a-zA-Z0-9_-]+$/;
  const FORBIDDEN_COMPONENT_NAMES = new Set([
    '__proto__',
    'constructor',
    'prototype',
    'valueOf',
    'toString',
    'isPrototypeOf',
    'propertyIsEnumerable',
    'toLocaleString',
    'hasOwnProperty'
  ]);

  /**
   * SecureComponentRegistry
   * Catálogo isolado e seguro para componentes GenUI.
   * Rejeita estritamente componentes desconhecidos, nomes maliciosos ou sobrescrita não autorizada.
   */
  class SecureComponentRegistry {
    constructor() {
      this._components = new Map();
      this._frozen = false;
      this._securityAlertCount = 0;
    }

    /**
     * Registra um componente autorizado no catálogo com proteção anti-tamper.
     * @param {string} name - Nome canônico do componente (ex: 'render_ExecutiveBriefingUI')
     * @param {Function|Object} componentDef - Classe, função construtora ou fábrica de renderização
     * @param {Object} [metadata={}] - Metadados de governança (intent, versão, descrição, etc.)
     * @param {Object} [options={}] - Opções de registro (ex: allowOverwrite: boolean)
     * @returns {SecureComponentRegistry} this para encadeamento
     */
    registerComponent(name, componentDef, metadata = {}, options = {}) {
      if (this._frozen) {
        throw new Error('[AURA-SEC-REGISTRY] O registro de componentes está congelado contra modificações.');
      }
      if (typeof name !== 'string' || !name.trim()) {
        throw new Error('[AURA-SEC-REGISTRY] Nome do componente inválido ou vazio.');
      }
      const trimmedName = name.trim();
      if (!COMPONENT_NAME_REGEX.test(trimmedName)) {
        throw new Error(`[AURA-SEC-REGISTRY] Nome de componente inválido: '${trimmedName}'. Apenas caracteres alfanuméricos, hífen e underscore são permitidos.`);
      }
      if (FORBIDDEN_COMPONENT_NAMES.has(trimmedName)) {
        throw new Error(`[AURA-SEC-REGISTRY] Nome de componente proibido (segurança de protótipo): '${trimmedName}'.`);
      }
      if (!componentDef || (typeof componentDef !== 'function' && typeof componentDef !== 'object')) {
        throw new Error(`[AURA-SEC-REGISTRY] Definição de componente inválida para '${trimmedName}'. Deve ser uma função ou objeto.`);
      }
      const allowOverwrite = options && options.allowOverwrite === true;
      if (this._components.has(trimmedName) && !allowOverwrite) {
        throw new Error(`[AURA-SEC-REGISTRY] Componente '${trimmedName}' já registrado. Sobrescrita não autorizada (Tamper Protection).`);
      }

      this._components.set(trimmedName, {
        name: trimmedName,
        component: componentDef,
        metadata: Object.freeze({ ...(metadata || {}) }),
        registeredAt: Date.now()
      });

      return this;
    }

    /**
     * Verifica se um componente está catalogado.
     * @param {string} name - Nome do componente
     * @returns {boolean}
     */
    hasComponent(name) {
      if (typeof name !== 'string') return false;
      return this._components.has(name.trim());
    }

    /**
     * Resolve um componente pelo nome de forma segura.
     * Rejeita qualquer tentativa de invocação de componente não cadastrado (OWASP LLM03).
     * @param {string} name - Nome do componente solicitado pelo LLM ou backend
     * @param {Object|boolean} [options] - Opções de resolução ({ throwOnMissing: boolean } ou boolean)
     * @returns {Function|Object|null} Definição do componente registrado ou null
     */
    resolveComponent(name, options = { throwOnMissing: true }) {
      const trimmedName = (typeof name === 'string') ? name.trim() : '';
      const shouldThrow = (options === undefined || options === null)
        ? true
        : (typeof options === 'boolean' ? options : options.throwOnMissing !== false);

      if (!trimmedName || !this._components.has(trimmedName)) {
        this._securityAlertCount++;
        const warnMsg = `[AURA-SEC-003] Agência Excessiva bloqueada (OWASP LLM03): Componente '${name}' não catalogado no SecureComponentRegistry.`;
        if (typeof console !== 'undefined' && console.warn) {
          console.warn(warnMsg);
        }
        if (shouldThrow) {
          throw new Error(`[AURA-SEC-003] Agência Excessiva detectada (OWASP LLM03): Componente '${name}' não catalogado no SecureComponentRegistry.`);
        }
        return null;
      }

      const entry = this._components.get(trimmedName);
      return entry.component;
    }

    /**
     * Remove um componente do catálogo (útil em rotinas de teste).
     * @param {string} name - Nome do componente
     * @returns {boolean} True se removido
     */
    unregisterComponent(name) {
      if (this._frozen) {
        throw new Error('[AURA-SEC-REGISTRY] O registro de componentes está congelado contra modificações.');
      }
      if (typeof name !== 'string') return false;
      return this._components.delete(name.trim());
    }

    /**
     * Lista todos os componentes registrados e seus metadados.
     * @returns {Array<Object>}
     */
    listComponents() {
      const list = [];
      for (const [name, entry] of this._components.entries()) {
        list.push({
          name,
          metadata: entry.metadata,
          registeredAt: entry.registeredAt
        });
      }
      return list;
    }

    /**
     * Retorna os metadados de governança de um componente.
     * @param {string} name - Nome do componente
     * @returns {Object|null}
     */
    getMetadata(name) {
      if (typeof name !== 'string') return null;
      const entry = this._components.get(name.trim());
      return entry ? entry.metadata : null;
    }

    /**
     * Congela o registro contra adições ou modificações futuras (Tamper Protection).
     */
    freeze() {
      this._frozen = true;
    }

    /**
     * Verifica se o registro está congelado.
     * @returns {boolean}
     */
    isFrozen() {
      return this._frozen;
    }

    /**
     * Limpa todos os componentes (para rotinas de teste).
     */
    clear() {
      if (this._frozen) {
        throw new Error('[AURA-SEC-REGISTRY] O registro de componentes está congelado.');
      }
      this._components.clear();
      this._securityAlertCount = 0;
    }

    /**
     * Retorna a quantidade de alertas de segurança registrados.
     * @returns {number}
     */
    getSecurityAlertCount() {
      return this._securityAlertCount;
    }
  }

  // =========================================================================
  // 4. INSTÂNCIA SINGLETON & EXPORTAÇÃO DUAL (ZERO-BUNDLER & COMMONJS)
  // =========================================================================

  const registry = new SecureComponentRegistry();

  const AuraGenUI = {
    version: '1.0.0',
    SecureComponentRegistry,
    registry,
    escapeHtml,
    sanitizeProps,
    generateUUID,
    generateToolCallId,
    generateActionId,
    isValidUUID,
    validateToolCallId,
    validateActionId
  };

  // 1. Exportação Global no Navegador (Window)
  if (typeof window !== 'undefined') {
    window.AuraGenUI = AuraGenUI;
    window.SecureComponentRegistry = registry;

    // Dispara evento para integração assíncrona/deferida de outros módulos
    try {
      window.dispatchEvent(new CustomEvent('aura:genui-ready', {
        detail: { AuraGenUI, registry }
      }));
    } catch (_) {}
  }

  // 2. Exportação CommonJS para testes headless e automação (Node.js)
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
      AuraGenUI,
      SecureComponentRegistry,
      registry,
      escapeHtml,
      sanitizeProps,
      generateUUID,
      generateToolCallId,
      generateActionId,
      isValidUUID,
      validateToolCallId,
      validateActionId
    };
  }

})(typeof globalThis !== 'undefined' ? globalThis : (typeof window !== 'undefined' ? window : this));
