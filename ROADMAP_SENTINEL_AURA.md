# ROADMAP DE ENGENHARIA ARQUITETURAL: MODERNIZAÇÃO DA AURA VIA SENTINEL

**Documento**: Especificação Técnica de Modernização e Resiliência de Borda  
**Sistema**: AURA (Autonomous Unified Retail Assistant)  
**Origem dos Padrões**: Projeto Sentinel (RAG WP)  
**Data**: 16 de Outubro de 2026  
**Versão**: 2.0.0-PROD  
**Localização Completa**: [docs/ROADMAP_SENTINEL_AURA.md](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/docs/ROADMAP_SENTINEL_AURA.md)

---

## 1. Sumário Executivo & Decisão Estrutural

A plataforma **AURA** possui maturidade analítica avançada no setor de postos de combustíveis e varejo (RAG híbrido, GenUI reativo em streaming SSE, 12 ferramentas de negócio e barramento RBAC). No entanto, para operar como infraestrutura crítica autônoma em computadores de caixa/PDV Windows (sem depender de suporte manual ou intervenção humana), ela precisa absorver os padrões de resiliência de borda desenvolvidos e homologados no projeto **Sentinel (RAG WP)**.

### A Decisão Estrutural
> **Veredito:** **NÃO unifique a AURA e o Sentinel no mesmo serviço ou processo executável.**  
> A arquitetura de produção adota **2 Serviços Windows Dedicados e Independentes (`SentinelAgent` e `AuraBackendService`)**, onde o **Sentinel atua como Watchdog Externo (Auto-Healing)** da AURA, enquanto a AURA **herda e reutiliza 8 módulos e padrões comprovados do Sentinel**.

---

## 2. Matriz de Reúso dos 8 Ativos do Sentinel

| # | Padrão / Ativo no Sentinel | Origem no Sentinel (RAG WP) | Destino na AURA (ia-banco-local) | Ganho Estrutural na Operação |
|---|---|---|---|---|
| **1** | **SCM Windows Service Host** | `src/station_agent/service.py:L52-L97` | `core/service.py` | Elimina download de `nssm.exe`. Adota padrão Supervisor-Worker nativo via `sc.exe` com auto-recuperação. |
| **2** | **Cofre Criptográfico DPAPI** | `src/station_agent/identity_store.py:L15-L71` | `core/identity_vault.py` | Criptografa senhas com chave do chip TPM/SO da máquina. Elimina senhas do ERP em `.env` e `.txt`. |
| **3** | **Hardware Circuit Breaker** | `src/station_agent/resource_watchdog.py:L77-L140` | `core/resource_watchdog.py` | Amostragem Win32 pura (sem `psutil`). Se a CPU do caixa passar de 80%, desacelera a IA para não travar a venda. |
| **4** | **Notificador Desktop HITL** | `src/station_agent/desktop_notifier.py:L64-L126` | `core/desktop_notifier.py` | Cruza Sessão 0 -> Sessão 1 (`WTSSendMessageW`). Exibe modal na tela do caixa mesmo com navegador fechado. |
| **5** | **Transactional Outbox (WAL)** | `src/channels/whatsapp/infrastructure/outbox_repository.py` | `core/outbox.py` | Fila durável em SQLite WAL com retentativa exponencial. Zero perda de mensagens no WhatsApp por queda de rede. |
| **6** | **Journal Persist-First** | `src/station_agent/command_journal.py:L13-L82` | `core/aura_api.py` / `core/aura_engine.py` | Gravação prévia de estado `RUNNING` em `POST /actions/execute`. Garante idempotência e evita repetição de compras. |
| **7** | **Shared pgvector Storage** | `src/station_agent/edge_storage.py:L20-L49` | `config/settings.py` / `scripts/` | Unificação na porta 5433 em schemas isolados (`aura_core` e `n3_sre`) no banco `posto_ai`. |
| **8** | **PyInstaller Standalone** | `SentinelAgent.spec:L1-L51` | `AuraBackend.spec` | Executável compilado com hooks de spaCy e assets web. Implantação em novos postos em 30 segundos. |

---

## 3. Diagrama Arquitetural de Coexistência Windows

```text
+----------------------------------------------------------------------------------------------------+
|                         ESTAÇÃO DE PISTA / CAIXA PDV (WINDOWS 10/11 IoT)                           |
+----------------------------------------------------------------------------------------------------+
|  [ SESSÃO 1: ÁREA DE TRABALHO INTERATIVA (Operador / Caixa) ]                                      |
|   +------------------------------------+    +---------------------------------------------------+  |
|   |   ERP / Frente de Caixa (webPosto) |    |  Notificações Desktop Topmost (wtsapi32.dll)      |  |
|   |   (Faturamento, Bicos, Cupons)     |    |  - Alerta Sangria Gaveta (MB_SYSTEMMODAL)         |  |
|   |                                    |    |  - Confirmação Pedido Combustível [Sim/Não]       |  |
|   +------------------------------------+    +-------------------------^-------------------------+  |
|                                                                       | WTSSendMessageW            |
|  ================================== ISOLAMENTO SESSÃO 0 / 1 ==========|===========================  |
|  [ SESSÃO 0: SERVIÇOS NATIVOS DO WINDOWS (SCM / LocalSystem) ]        |                            |
|                                                                       |                            |
|   +-------------------------------------------------------------+     |                            |
|   | SERVIÇO 1: SentinelAgent (Supervisão SRE de Infraestrutura) |     |                            |
|   | - Monitor de processos de automação, concentrador e TEF     |     |                            |
|   | - Prober HTTP de saúde da Aura (:8000/api/v1/aura/health)   |     |                            |
|   | - Auto-Healing externo: taskkill /F + sc start se travar    |     |                            |
|   +------------------------------+------------------------------+     |                            |
|                                  | monitora / protege                 |                            |
|                                  v                                    |                            |
|   +-------------------------------------------------------------+     |                            |
|   | SERVIÇO 2: AuraBackendService (Motor Cognitivo & Negócio)   |     |                            |
|   |  • Processo Pai: SCM Dispatcher Host (win32serviceutil)     |     |                            |
|   |  • Processo Filho: Worker Uvicorn/FastAPI isolado           |     |                            |
|   |    - Hardware Circuit Breaker (CPU/RAM Host Protection) ----+     |                            |
|   |    - DesktopNotifier (WTSSendMessageW Topmost HITL) --------+-----+                            |
|   |    - Transactional Outbox (SQLite WAL aura_outbox.db) ----------> WhatsApp / n8n               |
|   |    - Persist-First Command Journal (aura_sessions.db) ----------> POST /actions/execute        |
|   |    - Identity Vault (Windows DPAPI CryptProtectData) -----------> %ProgramData%\Aura\vault.bin |
|   |    - Motor Cognitivo (AuraEngine, RAG Híbrido, 12 Tools)                                       |
|   +------------------------------+-----------------------------------------------------------------+
|                                  | Porta 5433 (PostgreSQL 16 Nativo Windows)
|                                  v
|   +---------------------------------------------------------------------------------------------+
|   | BANCO LOCAL POSTGRESQL 16 (Serviço Windows: postgresql-x64-16)                              |
|   |  • Banco 'posto': ERP webPosto (Acesso estrito aura_service_ro)                             |
|   |  • Banco 'posto_ai': pgvector compartilhado (Schemas 'aura_core' e 'n3_sre')                |
|   +---------------------------------------------------------------------------------------------+
```

---

## 4. As 8 Fases de Implementação

* **Fase 1: Fundação do Serviço Windows SCM Nativo (Fim do NSSM) [CONCLUÍDA]**
  * Criado `core/service.py` com arquitetura Supervisor-Worker nativa do Windows via `sc.exe` e reciclagem in-process < 1s.
  * Adicionados argumentos `--service`, `--service-worker`, `--install-service`, `--start-service`, `--stop-service`, `--service-status`, `--service-info` e `--uninstall-service` no `server.py`.
  * Criado script de gestão `scripts/gerenciar_servico_aura.bat` e atualizado `scripts/instalar_posto.ps1` e suíte `tests/unit/test_windows_scm_service.py`.

* **Fase 2: Cofre Criptográfico DPAPI (Fim das Senhas em Texto Claro) [CONCLUÍDA]**
  * Criado `core/identity_vault.py` com `CryptProtectData` (escopo máquina `CRYPTPROTECT_LOCAL_MACHINE`), cabeçalho `AURAVAULT1\0` e fallback defensivo multiplataforma.
  * Atualizado `config/settings.py` e `scripts/solicitar_senha_erp.py` com salvamento no cofre DPAPI, marcador `DPAPI_ENCRYPTED` no `.env` e expurgo automático de arquivos legados `.txt`.
  * Criada suíte de testes unitários `tests/unit/test_identity_vault_dpapi.py` com 15 testes aprovados em sub-segundo.

* **Fase 3: Hardware Circuit Breaker para PDV (Proteção do Caixa) [CONCLUÍDA]**
  * Criado `core/resource_watchdog.py` com monitoramento nativo Win32 (ctypes GlobalMemoryStatusEx e GetSystemTimes) sem biblioteca externa psutil e fallback defensivo Linux/CI.
  * Implementada máquina de estados do Circuit Breaker (`CLOSED`, `OPEN`, `HALF_OPEN`) com limiares configuráveis (`AURA_MAX_CPU_PERCENT`, `AURA_MAX_RAM_PERCENT`, `AURA_CIRCUIT_COOLDOWN_SEC`).
  * Integrado ao motor cognitivo `core/aura_engine.py` com síntese leve imediata para ferramentas analíticas pesadas e ao `core/proactive_daemon.py` para pausa de ciclos sob estresse.
  * Criada suíte de testes unitários `tests/unit/test_hardware_circuit_breaker.py` com 24 testes aprovados.

* **Fase 4: Notificador Desktop HITL Sessão 0 para Sessão 1 (`WTSSendMessageW`) [CONCLUÍDA]**
  * Criado `core/desktop_notifier.py` com integração nativa Win32 (`WTSGetActiveConsoleSessionId` e `WTSSendMessageW`), flags `MB_TOPMOST`, `MB_SETFOREGROUND` e `MB_SYSTEMMODAL`, controle de cooldown anti-spam e fallback seguro para ambientes headless/CI/Linux.
  * Integrado ao `core/proactive_daemon.py` para disparo de alertas visuais Topmost em sangrias urgentes de caixa e tanques em nível crítico, e expostos endpoints `/api/v1/aura/desktop/notify`, `/api/v1/aura/desktop/confirm` e `/api/v1/aura/desktop/history` no `core/aura_api.py`.
  * Criada suíte de testes unitários `tests/unit/test_desktop_notifier_wts.py` com 100% dos testes aprovados.

* **Fase 5: Mensageria Resiliente com Transactional Outbox (SQLite WAL) [CONCLUÍDA]**
  * Criado `core/outbox.py` com fila SQLite durável em modo WAL (`%ProgramData%\Aura\data\aura_outbox.db`), protocolo Persist-Before-Send (`enqueue`), deduplicação por `idempotency_key`, backoff exponencial com jitter, recuperação de mensagens órfãs (`recover_stale_processing`), gestão de DLQ (`DEAD_LETTER`) e worker em background thread-safe.
  * Integrado `AuraWebhookDispatcher` (`core/webhook_dispatcher.py` e `core/webhooks.py`) à `AuraTransactionalOutbox` e adicionados os endpoints `/api/v1/aura/outbox/stats`, `/api/v1/aura/outbox/messages`, `/api/v1/aura/outbox/flush` e `/api/v1/aura/outbox/requeue-dlq` no `core/aura_api.py`.
  * Criada suíte de testes unitários `tests/unit/test_transactional_outbox.py` com 100% dos testes aprovados.

* **Fase 6: Journal de Comandos Persist-First & Idempotência Transacional [CONCLUÍDA]**
  * Criado `core/command_journal.py` com persistência SQLite WAL (`%ProgramData%\Aura\data\aura_command_journal.db`), protocolo Persist-First Atomic Claim (`begin_command`), bloqueio de concorrência (`RUNNING` -> HTTP 409 Conflict), replay idempotente (`COMPLETED`), rollback transacional (`ROLLED_BACK`) e crash recovery forense (`recover_interrupted_commands` -> `INTERRUPTED_BY_CRASH`).
  * Integrado `AuraCommandJournal` às rotas `POST /api/v1/aura/actions/execute` e `POST /api/v1/aura/actions/rollback` e adicionados os endpoints `GET /api/v1/aura/actions/journal` e `POST /api/v1/aura/actions/journal/recover` no `core/aura_api.py`.
  * Criada suíte de testes unitários `tests/unit/test_command_journal_idempotency.py` e `tests/unit/test_action_vouchers.py` com 100% dos testes aprovados.

* **Fase 7: Convergência do Armazenamento pgvector Local (`posto_ai`) [CONCLUÍDA]**
  * Padronizado PostgreSQL 16 na porta 5433 e banco `posto_ai` com schemas isolados (`aura_core` e `n3_sre`) em `config/settings.py` e `core/db_pool.py`.
  * Atualizado `scripts/init_posto_database.py` para provisionamento declarativo de schemas, tabelas com índices HNSW (`aura_core.intencoes_vetores`, `aura_core.produtos_vetores`, `aura_core.aura_conhecimento_vetores`, `n3_sre.knowledge_base`, `n3_sre.sre_runbooks`, `n3_sre.incident_fingerprints`, `n3_sre.sre_telemetry_events`) e views retrocompatíveis.
  * Atualizado `n3-agent.toml` e `edge_storage.py` do Sentinel para porta 5433 compartilhada sem conflito de portas.
  * Criada suíte de testes unitários `tests/unit/test_shared_pgvector_convergence.py` com 100% dos testes aprovados.

* **Fase 8: Distribuição Binária Standalone via PyInstaller [CONCLUÍDA]**
  * Criado `AuraBackend.spec` para empacotamento standalone `--onedir` com todos os módulos essenciais, assets estáticos web e mappings de ERP.
  * Criado script de compilação automatizada `scripts/build_aura_standalone.ps1`.
  * Criado instalador autônomo 1-clique com auto-elevação UAC e regras de firewall em `scripts/installer/Instalar-Aura.bat`.
  * Criada suíte de testes unitários `tests/unit/test_pyinstaller_standalone_spec.py` com 100% dos testes aprovados.

---

## 5. Cronograma Sugerido de Rollout

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ SEMANA 1: FUNDAÇÃO & SEGURANÇA ESTRUTURAL                                  │
│ • Fase 1: Serviço Windows SCM Nativo (Supervisor-Worker) + Remoção do NSSM │
│ • Fase 2: Cofre Criptográfico DPAPI de Máquina + Limpeza de Senhas Claras  │
└─────────────────────────────────────┬──────────────────────────────────────┘
                                      ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ SEMANA 2: RESILIÊNCIA OPERACIONAL & BLINDAGEM DE TRANSAÇÕES                │
│ • Fase 3: Hardware Circuit Breaker para PDV (Proteção CPU/RAM do Caixa)    │
│ • Fase 4: Notificador Desktop HITL Sessão 0 -> 1 (WTSSendMessageW)         │
│ • Fase 5: Transactional Outbox Pattern para WhatsApp (SQLite WAL)          │
│ • Fase 6: Persist-First Command Journal em POST /actions/execute           │
└─────────────────────────────────────┬──────────────────────────────────────┘
                                      ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ SEMANA 3: CONVERGÊNCIA & DISTRIBUIÇÃO EM ESCALA                            │
│ • Fase 7: Unificação do pgvector no PostgreSQL 16 (Porta 5433 / posto_ai)  │
│ • Fase 8: Distribuição Standalone via PyInstaller + Instalador de 1 Clique │
└────────────────────────────────────────────────────────────────────────────┘
```
