# GEMINI.md — Regras Arquiteturais Permanentes (AURA Local)

> Raiz do repositório: `ia-banco-local/`. Complementa `.agents/rules/lean-agentic-workflow.md` (sem duplicar regras de anti-loop/leitura parcial).

## 1. Mapa do Repositório & Comandos Reais
- **Core Python (FastAPI/PostgreSQL):** `core/`, `config/`, `server.py`, `main.py`, `AuraBackend.spec`, `tests/` (`pytest.ini` ignora `scripts/`).
- **Web & SDK (TypeScript/Vite):** `web-frontend/` (compila `src/main.ts` -> `web/dist/aura-sdk.{es,umd}.js`) e assets estáticos em `web/`.
- **Bundle Standalone (Windows SCM):** `dist/AuraBackend/_internal/web/` (gerado via PyInstaller `--onedir` por `AuraBackend.spec`).
- **App Android (Kotlin/Compose):** `Aura Assistance Android/` (`app/build.gradle.kts`, `compileSdk 35`, `minSdk 26`, JDK 17).
- **Testes Python:** `pytest tests/unit -v --tb=short` (nunca executar `pytest` em `scripts/`).
- **Build/Typecheck Web:** `cd web-frontend && npm run build` (`tsc --noEmit && vite build`) ou `npm run typecheck`.
- **Build Standalone:** `pyinstaller AuraBackend.spec` (ou `automacoes/build_aura_standalone.ps1`).
- **Build/Teste Android:** `cd "Aura Assistance Android" && .\gradlew.bat testDebugUnitTest` e `.\gradlew.bat assembleDebug`.

## 2. Invariantes do Core (FastAPI / Python)
- **Determinismo Financeiro/Fiscal:** Todo cálculo numérico, margem, tributação e regra fiscal executa em Python determinístico (`core/fiscal_engine.py`, `core/domain/`); nunca delegar matemática ao LLM.
- **SQL Read-Only Seguro:** Validar queries via `assert_readonly_safe_sql` com `sqlglot` (dialeto Postgres); proibido usar `TRIM()` em cláusulas `JOIN` (quebra índices).
- **Isolamento de Domínio:** Roteamento estrito por `pack_id` via `DomainToolRegistry`; zero fallback para `PostoTools` fora de `fuel_convenience`.
- **LGPD/PII:** Sanitizar dados pessoais com `spaCy` (`core/sanitizer.py`) antes de tráfego externo ou prompts ao LLM.
- **Cliente LLM:** Usar singleton `google-genai` (`core/llm_client.py`) com HTTP Keep-Alive; nunca instanciar clientes descartáveis por requisição.
- **Segurança de Sessão & Rede:** Localhost usa cookie `HttpOnly; SameSite=Strict`; acessos via LAN/Tailscale exigem `X-API-Key` válida. Nunca confiar cegamente em `X-Forwarded-For` para bypass de autenticação.
- **Resiliência SSE:** Emitir evento `stream_reset` em retentativas/fallbacks de geração para evitar texto duplicado ou corrompido no cliente.

## 3. Invariantes Web & SDK (Obsidian GenUI)
- **Transporte Único:** Todas as chamadas HTTP e SSE passam pelo `AuraHttpTransport` com `credentials: "include"`, zero `EventSource` nativo e tratamento explícito de `stream_reset`.
- **Identidade & Layout:** Preservar paleta Obsidian (`#07090E`), `AuraReasoningRibbon` e contratos GenUI com Zero-CLS.
- **Atalhos Globais:** Manter `Alt+P` (Companion) e `Alt+Shift+M` (Alto Contraste) funcionais sem regressões.
- **Sincronia de Distribuição:** Após build web (`web/dist/` ou `web/`), sincronizar arquivos e hashes com `dist/AuraBackend/_internal/web/`.
- **Empacotamento PyInstaller:** Manter `hiddenimports` de `AuraBackend.spec` atualizados (`google.genai`, `sqlglot` e qualquer novo submódulo `core.*`).

## 4. Invariantes Android (Kotlin / Compose / Hilt / Room)
- **Design System Obsidian Aurora:** Tema AMOLED (`#07090E` / `#030407`), tipografia `Newsreader` + `Geist` e componentes canônicos como `TankTile`.
- **Rede & Credenciais:** `OkHttp` (`okhttp-sse`) + Android Keystore injetando `X-API-Key` sobre Tailscale; nunca hardcodar segredos.
- **Streaming SSE:** Parser SSE deve processar `stream_reset` limpando o buffer da resposta parcial antes de retomar o stream.
- **Multi-Domínio:** Adaptar telas, métricas e ações dinamicamente conforme `pack_id` retornado pelo backend.
- **Hardware & Borda Isolados:** Módulos de borda (`CameraX`, `sherpa-onnx`, `NfcAdapter`, ML Kit/Biometria) devem permanecer desacoplados via injeção Hilt (testáveis e substituíveis).

## 5. Protocolo HiC (Human-in-Command)
- **Aprovação Explícita Obrigatória:** Nunca instalar/atualizar pacotes (`pip`, `npm`, Gradle), alterar serviços/arquivos de produção ou executar `git push` sem confirmação prévia do usuário.
- **Mudanças Cirúrgicas:** Preferir edições mínimas verificadas pelos testes da camada afetada antes de propor deploy ou empacotamento.
