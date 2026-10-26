# ROADMAP DE ENGENHARIA ARQUITETURAL: MODERNIZAÇÃO DA AURA VIA SENTINEL

**Documento**: Especificação Técnica de Modernização e Resiliência de Borda  
**Sistema**: AURA (Autonomous Unified Retail Assistant)  
**Origem dos Padrões**: Projeto Sentinel (RAG WP)  
**Data**: 16 de Outubro de 2026  
**Versão**: 2.0.0-PROD  

---

## 1. Sumário Executivo & Diagnóstico

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

## 4. Roadmap Detalhado por Fases

### 🟢 Fase 1: Fundação do Serviço Windows SCM Nativo (Fim do NSSM) [CONCLUÍDA]
* **Objetivo**: Backend como serviço nativo do Windows com padrão Supervisor-Worker, iniciando antes do login e sem dependência do `nssm.exe`.
* **Arquivos Criados/Modificados**:
  * `core/service.py` *(novo)*: Implementação de `win32serviceutil.ServiceFramework` com loop de reciclagem in-process (até 3 tentativas em < 1s).
  * `server.py`: Adição dos argumentos `--service` (SCM), `--service-worker` (Uvicorn background com flag `CREATE_NO_WINDOW = 0x08000000`), `--install-service`, `--start-service`, `--stop-service`, `--service-status`, `--service-info` e `--uninstall-service`.
  * `scripts/gerenciar_servico_aura.bat` *(novo)*: Script com auto-elevação administrativa para instalar, iniciar, parar e diagnosticar o serviço.
  * `scripts/instalar_posto.ps1`: Registro nativo com política de recuperação:
    ```cmd
    sc.exe create AuraBackendService binPath= "\"C:\Aura\AuraBackend.exe\" --service" start= auto DisplayName= "Aura Cognitive Service" depend= postgresql-x64-16
    sc.exe failure AuraBackendService reset= 86400 actions= restart/5000/restart/10000/restart/30000
    ```
  * `tests/unit/test_windows_scm_service.py` *(novo)*: Suíte completa de testes unitários validando reciclagem < 1s, CLI e ciclo de vida `sc.exe`.
* **Critério de Aceite**: Finalizar forçadamente o processo worker no Gerenciador de Tarefas; o supervisor pai recicla o processo em menos de 1 segundo sem derrubar o serviço no SCM. **Status: Concluído com 100% dos testes unitários aprovados.**

---

### Fase 2: Cofre Criptográfico DPAPI (Fim das Senhas em Texto Claro) [CONCLUÍDA]
* **Objetivo**: Criptografia de senhas do banco de dados atrelada à máquina física via API nativa do Windows (DPAPI).
* **Arquivos Criados/Modificados**:
  * `core/identity_vault.py` *(novo)*: Implementa `CryptProtectData` e `CryptUnprotectData` via `ctypes.windll.crypt32` com escopo `CRYPTPROTECT_LOCAL_MACHINE` (0x4), assinatura binária mágica `AURAVAULT1\0` e fallback criptográfico defensivo para CI/Linux.
  * `config/settings.py`: Resolução com priorização do cofre `%ProgramData%\Aura\vault\vault.bin` e suporte a `DPAPI_ENCRYPTED`.
  * `scripts/solicitar_senha_erp.py`: Salva a senha no cofre DPAPI, grava `DPAPI_ENCRYPTED` no `.env` e expurga arquivos legados em texto claro (`backups/erp_password.txt`).
  * `tests/unit/test_identity_vault_dpapi.py` *(novo)*: Suíte com 15 testes unitários cobrindo CRUD, tamperamento, fallback de software, auto-migração e isolamento.
* **Critério de Aceite**: Varredura `findstr /S /I "senha" *.env *.txt *.json` retorna zero senhas reais, e a AURA conecta ao PostgreSQL descriptografando a chave em memória. **Status: Concluído com 100% dos testes unitários aprovados.**

---

### Fase 3: Hardware Circuit Breaker para PDV (Proteção do Caixa) [CONCLUÍDA]
* **Objetivo**: Impedir que consultas pesadas de IA causem lentidão no faturamento ou na emissão de cupom fiscal na pista.
* **Arquivos Criados/Modificados**:
  * `core/resource_watchdog.py` *(novo)*: Monitor Win32 nativo via `ctypes` (`kernel32.GlobalMemoryStatusEx` e `kernel32.GetSystemTimes`) sem dependência de `psutil` e fallback limpo para Linux/CI.
  * `core/aura_engine.py`: Consulta `is_heavy_operation_allowed()` antes de disparar ferramentas analíticas pesadas (`conveniencia_vendas_cruzadas`, `auditoria_fuga_financeira`, etc.). Sob circuito `OPEN`, devolve síntese leve imediata sem acionar LLM nem travar o PDV.
  * `core/proactive_daemon.py`: Em `evaluate_rules()`, pausa ciclos analíticos em segundo plano quando o circuito estiver `OPEN`.
  * `tests/unit/test_hardware_circuit_breaker.py` *(novo)*: Suíte com 24 testes unitários cobrindo métricas Win32, fallback Linux/CI, transições de estado (`CLOSED` -> `OPEN` -> `HALF_OPEN` -> `CLOSED`), degradação graciosa no `AuraEngine` e ausência estrita de travessões.
* **Calibração de Estados**:
  * `CLOSED`: CPU < 80.0% e RAM < 85.0%. Operação analítica plena.
  * `OPEN`: CPU >= 80.0% ou RAM >= 85.0%. Modo de proteção ativo; ferramentas pesadas rejeitadas com síntese protetiva imediata; background daemon pausado.
  * `HALF_OPEN`: Testando recuperação do hardware após expiração do cooldown (padrão 30s).
* **Critério de Aceite**: Durante pico de estresse no PDV, a AURA bloqueia chamadas analíticas pesadas instantaneamente e protege 100% dos recursos do caixa. **Status: Concluído com 100% dos testes unitários aprovados.**

---

### Fase 4: Notificador Desktop HITL Sessão 0 para Sessão 1 (`WTSSendMessageW`) [CONCLUÍDA]
* **Objetivo**: Exibir mensagens e confirmações críticas na tela do operador, mesmo com o navegador fechado.
* **Arquivos Criados/Modificados**:
  * `core/desktop_notifier.py` *(novo)*: Implementa `WTSSendMessageW` da biblioteca nativa `wtsapi32.dll` e `WTSGetActiveConsoleSessionId` via `kernel32.dll`, com deduplicação/cooldown e fallback defensivo.
  * `core/proactive_daemon.py`: Disparo visual para sangrias urgentes e tanques em nível crítico.
  * `core/aura_api.py`: Rotas `POST /api/v1/aura/desktop/notify`, `POST /api/v1/aura/desktop/confirm` (diálogo HITL `[Sim/Não]`) e `GET /api/v1/aura/desktop/history`.
  * `tests/unit/test_desktop_notifier_wts.py` *(novo)*: Suíte completa de testes unitários cobrindo invocação WTS, respostas HITL (`IDYES`, `IDNO`, `IDTIMEOUT`), cooldown anti-spam, fallback sem sessão ativa (`0xFFFFFFFF`) e integração FastAPI/Daemon.
* **Estilo Visual**: `MB_TOPMOST (0x40000)`, `MB_SETFOREGROUND (0x10000)` e `MB_SYSTEMMODAL (0x1000)` garantem sobreposição a qualquer janela do ERP.
* **Critério de Aceite**: Alerta disparado pelo serviço em Sessão 0 surge imediatamente no monitor do caixa (Sessão 1), bloqueia a interface e coleta a resposta do operador. **Status: Concluído com 100% dos testes unitários aprovados.**

---

### Fase 5: Mensageria Resiliente com Transactional Outbox (SQLite WAL) [CONCLUÍDA]
* **Objetivo**: Garantir entrega de resumos de turno e alertas para WhatsApp (Evolution API) e n8n mesmo com internet instável.
* **Arquivos Criados/Modificados**:
  * `core/outbox.py` *(novo)*: Implementa `AuraTransactionalOutbox` com persistência SQLite WAL (`PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA busy_timeout=5000;`) em `%ProgramData%\Aura\data\aura_outbox.db`, deduplicação por `idempotency_key`, backoff exponencial com jitter, recuperação de mensagens órfãs em `PROCESSING` (`recover_stale_processing`), DLQ (`DEAD_LETTER`) e worker em background thread-safe.
  * `core/webhook_dispatcher.py` e `core/webhooks.py`: Integração de `AuraWebhookDispatcher` (`dispatch_n8n`, `dispatch_whatsapp`) e funções de notificação ao protocolo Persist-Before-Send da Outbox, preservando 100% de retrocompatibilidade.
  * `core/aura_api.py`: Rotas `GET /api/v1/aura/outbox/stats`, `GET /api/v1/aura/outbox/messages`, `POST /api/v1/aura/outbox/flush` e `POST /api/v1/aura/outbox/requeue-dlq`.
  * `tests/unit/test_transactional_outbox.py` *(novo)*: Suíte completa de testes unitários cobrindo SQLite WAL, deduplicação, ciclo de vida completo, falha transiente com backoff, DLQ e reabilitação, crash recovery de `PROCESSING`, integração `AuraWebhookDispatcher` (offline/online) e endpoints FastAPI.
* **Critério de Aceite**: Desconectar o cabo de rede durante fechamento de turno; o evento fica retido no SQLite (`FAILED_RETRY`) e é entregue automaticamente (`DELIVERED`) assim que a rede volta. **Status: Concluído com 100% dos testes unitários aprovados.**

---

### Fase 6: Journal de Comandos Persist-First & Idempotência Transacional [CONCLUÍDA]
* **Objetivo**: Evitar repetição de pedidos de compra ou sangrias se o computador for reiniciado ou houver duplo clique durante o processamento.
* **Arquivos Criados/Modificados**:
  * `core/command_journal.py` *(novo)*: Implementa `AuraCommandJournal` com persistência SQLite em modo WAL (`PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA busy_timeout=5000;`) em `%ProgramData%\Aura\data\aura_command_journal.db`, reivindicação atômica Persist-First (`begin_command`), ciclo de vida (`RUNNING`, `COMPLETED`, `FAILED`, `ROLLED_BACK`, `INTERRUPTED_BY_CRASH`), wrapper `execute_idempotent` e crash recovery (`recover_interrupted_commands`).
  * `core/aura_api.py` e `core/aura_engine.py`: Refatoração de `POST /api/v1/aura/actions/execute` com Persist-First Journal, adição de `POST /api/v1/aura/actions/rollback` com transição para `ROLLED_BACK` e endpoints de auditoria `GET /api/v1/aura/actions/journal` e `POST /api/v1/aura/actions/journal/recover`.
  * `tests/unit/test_command_journal_idempotency.py` e `tests/unit/test_action_vouchers.py` *(novos)*: Suítes completas de testes unitários cobrindo SQLite WAL, garantia Persist-First em disco durante a execução, concorrência multi-thread, falha e retentativa controlada, crash recovery e ciclo completo nos endpoints FastAPI.
* **Fluxo**:
  1. Reivindica atomicamente o comando com estado `RUNNING` no SQLite WAL antes de chamar o ERP (`BEGIN IMMEDIATE`).
  2. Se uma requisição concorrente chegar enquanto `RUNNING`: bloqueia imediatamente com HTTP 409 Conflict.
  3. Se a mesma requisição chegar após `COMPLETED`: devolve o voucher original sem reexecutar a rotina de negócio.
  4. Atualiza para `COMPLETED` com assinatura HMAC-SHA256 após sucesso ou `ROLLED_BACK` em estorno.
* **Critério de Aceite**: Reenviar a mesma requisição com mesmo `action_id` ou `idempotency_key` nunca gera nova gravação no ERP. **Status: Concluído com 100% dos testes unitários aprovados.**

---

### Fase 7: Convergência do Armazenamento pgvector Local (`posto_ai`) [CONCLUÍDA]
* **Objetivo**: Unificar os dados de IA da AURA e do Sentinel na mesma instância do PostgreSQL 16 na porta 5433.
* **Arquivos Criados/Modificados**:
  * `config/settings.py` e `core/db_pool.py`: Padronizada porta 5433 e banco `posto_ai` com schemas isolados (`aura_core` e `n3_sre`) e options com `search_path=aura_core,public`.
  * `scripts/init_posto_database.py`: Provisiona declarativamente os schemas:
    * `aura_core`: Rotas semânticas (`intencoes_vetores`), catálogo (`produtos_vetores`), perguntas em cache (`perguntas_cache`) e base de conhecimento (`aura_conhecimento_vetores`) com índices HNSW (`halfvec_cosine_ops`).
    * `n3_sre`: Base de conhecimento SRE (`knowledge_base`), impressões digitais anti-storm (`incident_fingerprints`), runbooks operacionais locais (`sre_runbooks`) e eventos de telemetria (`sre_telemetry_events`).
    * Views retrocompatíveis em `public` para garantir compatibilidade com consultas legadas.
  * `RAG WP/src/station_agent/n3-agent.toml` e `RAG WP/src/station_agent/edge_storage.py`: Configurada a porta do Sentinel para 5433 compartilhada.
  * `tests/unit/test_shared_pgvector_convergence.py`: Suíte completa de testes unitários homologando DDLs, configurações, interoperabilidade e isolamento.
* **Critério de Aceite**: Ambos os sistemas compartilham a mesma base PostgreSQL sem conflito de portas e com schemas isolados. **Status: Concluído com 100% dos testes unitários aprovados.**

---

### Fase 8: Distribuição Binária Standalone via PyInstaller [CONCLUÍDA]
* **Objetivo**: Empacotar a AURA em distribuição autônoma de um clique, sem necessidade de instalar Python no posto.
* **Arquivos Criados/Modificados**:
  * `AuraBackend.spec` *(novo)*: Configuração PyInstaller `--onedir` com todos os módulos essenciais, Uvicorn, FastAPI, Win32 SCM, assets web (`web/`) e mapeamentos de ERP (`config/erp_mappings/`).
  * `scripts/build_aura_standalone.ps1` *(novo)*: Script automatizado de compilação com limpeza de builds antigos, validação de integridade e medição de tamanho do pacote.
  * `scripts/installer/Instalar-Aura.bat` *(novo)*: Instalador autônomo com auto-elevação UAC, registro do serviço Windows nativo (`--install-service`), partida automática, regra no Firewall para a porta 8000 e abertura do navegador.
  * `tests/unit/test_pyinstaller_standalone_spec.py` *(novo)*: Suíte completa de testes unitários homologando sintaxe do manifesto, módulos ocultos, scripts de compilação e instalador.
* **Critério de Aceite**: Executar `Instalar-Aura.bat` em máquina Windows limpa sem Python; o serviço sobe e a interface abre no navegador em menos de 30 segundos. **Status: Concluído com 100% dos testes unitários aprovados.**

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
