# Apendice Tecnico: Sessoes Dedicadas de Retorno WhatsApp & Fronteira Real do Motor Fiscal (Web vs. PDV Local)

> [!IMPORTANT]
> **Objetivo deste Documento (Guia Executavel para Agentes de Codigo):**
> Este apendice especifica o fluxo ponta a ponta, a logica de correlacao, a sincronizacao ativa com a Evolution API v2, os contratos de API, o esquema de persistencia (SQLite WAL + Room Android), os componentes de interface Jetpack Compose, a fronteira estrita do Motor Fiscal (Entrada no Banco Web vs. Saida PDV no Banco Local `:5433`) e os criterios de validacao para execucao autonoma por um agente de desenvolvimento.
>
> **Regra de Conformidade:** ZERO travessoes Unicode neste documento, codigos ou testes gerados a partir dele. Utilizar apenas hifens comuns (`-`), dois pontos (`:`) ou parenteses.

---

## 1. Contexto Operacional e Descobertas de Infraestrutura Ao Vivo

### 1.1. Problema 1: Retorno de Conversas WhatsApp (Sem Poluir nem Rolar o Chat Principal)
- Quando o gestor dispara um encaminhamento pelo app Android (ex.: enviar relatorio de DANFE e foto recortada para o Contador, ou alerta de estoque para o Gerente de Pista via `POST /api/v1/partner/handoff`), o chat analitico com a AURA continua evoluindo com novas consultas.
- Atualizar apenas o card antigo onde o botao foi clicado torna a leitura inviavel porque o card sobe e exige rolagem massiva no historico.
- **Solucao Adotada (2 Camadas):**
  1. **Pilula Flutuante de Alerta no Topo do Chat Atual (`HandoffReplyTopBanner`):** aparece sobre o chat ativo sempre que chegar uma resposta nova de qualquer contato, independente de quanto a conversa principal tenha rolado, com botao **`Abrir`** de 1 toque.
  2. **Sessao Dedicada por Contato na Aba `Retornos WhatsApp` (`wa_handoff_<phone>`):** cada contato acionado ganha uma sessao separada no Historico de Conversas (separado por abas: `Analises AURA` | `Retornos WhatsApp`), onde o gestor visualiza o relatorio e a miniatura da nota que enviou, le todas as respostas do destinatario e responde diretamente da sessao para o WhatsApp daquele contato via Evolution API.

### 1.2. Descoberta Critica de Rede: Como Capturar Respostas sem Alterar o Webhook do Painel CRM
- **Fato Auditado na Instancia `webposto-n3` (`GET /webhook/find/webposto-n3` em `100.89.108.95:8080`):**
  - A Evolution API v2 possui **uma unica URL de webhook por instancia**, que ja esta configurada e ativa apontando para o Painel WhatsApp CRM: `http://host.docker.internal:3000/api/webhooks/whatsapp` (`events: ["MESSAGES_UPSERT"]`).
  - Portanto, depender exclusivamente de um webhook direto da Evolution API para `:8000` nao funcionaria sem sobrescrever o webhook do Painel CRM ou alterar o codigo do servidor `:3000`.
- **Arquitetura Dual-Sync (Pull Ativo na Evolution API + Push Passivo via Webhook):**
  1. **Pull Ativo Autonomo (`sync_evolution_inbound_for_active_threads`):**
     - A AURA Local (`:8000`) consulta diretamente a API REST da Evolution (`POST {EVOLUTION_API_URL}/chat/findMessages/{EVOLUTION_INSTANCE}`) apenas para os telefones que possuem handoff ativo nas ultimas 72 horas (com cache/cooldown de `6 segundos`).
     - Isso garante que qualquer resposta do Contador, Gerente ou Fornecedor apareca no App Android de forma **100% autonoma**, sem tocar na configuracao de webhook do Painel CRM!
  2. **Push Passivo (`POST /api/v1/partner/handoff-reply`):**
     - Continua disponivel para receber eventos encaminhados em tempo real pelo Painel CRM (`:3000`) ou por webhooks futuros.

### 1.3. Problema 2: Fronteira Estrita do Motor Fiscal (Banco Web vs. Banco Local `:5433`)
- **Regra Real do Ambiente WebPosto / Posto:**
  - **Notas Fiscais de Entrada (Compras / Fornecedores / Modelo 55):** ficam armazenadas **exclusivamente no Banco Web** da retaguarda, ao qual a AURA Local **nao possui acesso SQL**.
  - **Notas Fiscais de Saida / PDV (Cupons NFC-e / Modelo 65 de pista e conveniencia):** ficam armazenadas no **Banco Local PostgreSQL (`:5433`)**, acessivel em modo leitura (`aura_service_ro`).
- **Implicacao Direta no Motor Fiscal:**
  - Toda auditoria de nota de entrada (foto com recorte nos Olhos da AURA, codigo de barras 44 digitos, PDF ou XML NF-e) deve ser **100% autossuficiente sobre o documento capturado** e sobre as regras deterministicas de `core/fiscal_engine.py`, gravando pendencias no `CommandJournal` local (`SQLite WAL`) e gerando orientacoes de correcao para o WebPosto Web.
  - Consultas ao banco PostgreSQL `:5433` ficam restritas a notas/cupons emitidos no PDV de saida (NFC-e / CF-e) e dados operacionais locais da pista.

---

## 2. Visao Geral do Fluxo Completo (Diagrama E2E)

```mermaid
sequenceDiagram
    autonumber
    participant User as Gestor (App Android)
    participant Local as AURA Local (:8000 / SQLite WAL)
    participant Evo as Evolution API (:8080 / webposto-n3)
    participant Dest as Contador / Gerente / Cliente (WhatsApp)

    User->>Local: POST /api/v1/partner/handoff (relatorio + anexo Base64)
    Local->>Local: Grava CommandJournal + aura_handoff_messages (OUTBOUND, epoch_ts)
    Local->>Evo: sendText + sendMedia (instance webposto-n3)
    Evo-->>Dest: Mensagem formatada + copia da nota recortada

    Note over Dest,Evo: Destinatario responde no WhatsApp
    Dest-->>Evo: Mensagem / Audio / Imagem

    User->>Local: Polling leve GET /api/v1/partner/handoffs (a cada 8s em foreground)
    Local->>Evo: POST /chat/findMessages/webposto-n3 (contatos com handoff ativo, cooldown 6s)
    Evo-->>Local: records[] (id, key.fromMe, key.remoteJid, message, messageTimestamp)
    Local->>Local: Filtra fromMe==false e messageTimestamp >= first_outbound_epoch, grava INBOUND (is_read=0)
    Local-->>User: Lista de threads com unread_count > 0 e ultima mensagem

    User->>User: Exibe Pilula no Topo do Chat: "Contador respondeu... [Abrir]"
    User->>Local: Toca em [Abrir] -> abre sessao "wa_handoff_<phone>" + POST .../read
    User->>Local: Digita ou envia nova foto na sessao -> POST /api/v1/partner/handoff
    Local->>Evo: Envia resposta direto no WhatsApp do contato
```

---

## 3. Especificacao da Fronteira Fiscal (Entrada Web vs. PDV Local)

### 3.1. Matriz de Decisao do Motor Fiscal (`core/fiscal_engine.py`, `core/tools.py`, `core/aura_engine.py`)

| Tipo de Documento / Pergunta | Origem no ERP Real | Acesso AURA Local (`:5433`) | Pipeline Obrigatorio da AURA |
| :--- | :--- | :---: | :--- |
| **NF-e Entrada (Mod. 55 / Compra / Fornecedor / DANFE / XML / PDF)** | **Banco Web (Sem acesso)** | **PROIBIDO consultar notas de entrada no DB local** | 1. Validar chave 44 digitos (`decompor_chave_acesso`, `validar_chave_acesso`)<br>2. Se houver XML, auditar via `auditar_documento_xml`<br>3. Validar somatorio de itens x `vProd` (W07-10), `vNF` (W16-10), NCM/CST monofasico (`LC 192/2022` - CST 61 diesel/gasolina, proibicao em etanol hidratado), PIS/COFINS monofasico (`CST 04`)<br>4. Consultar base de solucoes WebPosto via `webposto_rag` (`pilar="fiscal_tributario_sefaz"`)<br>5. Permitir gravar pendencia no `CommandJournal` local + enviar ao Contador via WhatsApp |
| **NFC-e / Cupom Saida PDV (Mod. 65 / Pista / Conveniencia)** | **Banco Local (`:5433`)** | **PERMITIDO (Read-Only)** | 1. Decompor chave 44 digitos se informada<br>2. Consultar registros locais de venda/cupom no PostgreSQL `:5433` quando o gestor pedir conferencia de emissao de pista<br>3. Aplicar regras SEFAZ/ACBr (`Rejeicao 375`, `531`, `535`, `629`, `958`, `959`, `960`) |

### 3.2. Regras de Implementacao no Motor Fiscal e Scanner Android
- **Arquivos envolvidos:**
  - `Aura Assistance Android/app/src/main/java/com/example/aurapostoassitance/data/vision/AuraVisionNpuScanner.kt`
  - `core/tools.py` (`auditar_documento_ou_chave_fiscal`)
  - `core/aura_engine.py` (instrucao de sistema / roteamento fiscal)
  - `core/partner_api.py` (`partner_quick_action_endpoint`)
- **Detalhamento:**
  1. Em `AuraVisionNpuScanner.scanXmlUri()`, quando um arquivo XML NF-e for lido, anexar ao final do `promptForAura` o trecho XML original (ou reconstruido com `<nfeProc><NFe><infNFe ...>...</infNFe></NFe></nfeProc>` limitado a 6.000 caracteres) para que `core/tools.py:auditar_documento_ou_chave_fiscal` acione `auditar_documento_xml()` deterministicamente.
  2. Em `core/aura_engine.py`, reforcar na diretiva fiscal: *"Notas fiscais de entrada (compra de mercadorias/combustiveis, Modelo 55) ficam exclusivamente no banco Web; nunca tente buscar notas de entrada no banco PostgreSQL local (:5433). Audite 100% com base nos dados extraidos do documento/XML/chave e nas regras da SEFAZ. Apenas cupons de saida emitidos no PDV (NFC-e Modelo 65) residem no banco local."*
  3. Em `core/partner_api.py` (`partner_quick_action_endpoint`), quando `action_type` contiver `"FISCAL"` ou `"PENDENCIA"`, gravar explicitamente os parametros (`chave_acesso`, `numero_nf`, `resumo_divergencia`, `fornecedor`) no `CommandJournal` com status `COMPLETED` e recibo rastreavel.

---

## 4. Especificacao do Backend Python (`ia-banco-local`)

### 4.1. Normalizacao Canonica de Telefone e Variantes JID (`normalize_whatsapp_phone` & `whatsapp_jid_candidates`)
- No Brasil, o WhatsApp (Baileys / Evolution API) armazena alguns numeros antigos de celular sem o nono digito (`55` + `DDD` + `8 digitos` = 12 digitos) e outros com o nono digito (`55` + `DDD` + `9 digitos` = 13 digitos).
- Implementar em `core/command_journal.py`:
  1. `normalize_whatsapp_phone(raw_phone: str) -> str`:
     - Remove `@s.whatsapp.net`, `@c.us`, `:device` e caracteres nao numericos.
     - Se tiver `10` ou `11` digitos, prefixa `"55"`.
  2. `phone_match_key(raw_phone: str) -> str`:
     - Retorna `DDD + ultimos 8 digitos` (10 digitos finais) para numeros brasileiros (`len >= 10`), garantindo que `5527999227721` e `552799227721` resolvam para a **mesma thread**!
  3. `whatsapp_jid_candidates(norm_phone: str) -> list[str]`:
     - Para um numero BR de 13 digitos (`55` + DDD + `9` + 8 digitos), retorna `["55DD9XXXXXXXX@s.whatsapp.net", "55DDXXXXXXXX@s.whatsapp.net"]`.
     - Para 12 digitos (`55` + DDD + 8 digitos), retorna `["55DDXXXXXXXX@s.whatsapp.net", "55DD9XXXXXXXX@s.whatsapp.net"]`.

### 4.2. Esquema SQLite WAL `aura_handoff_messages` (`core/command_journal.py`)
- Adicionar no metodo `_init_schema()` de `AuraCommandJournal`:

```sql
CREATE TABLE IF NOT EXISTS aura_handoff_messages (
    message_id TEXT PRIMARY KEY,
    thread_phone TEXT NOT NULL,
    match_key TEXT NOT NULL,
    contact_name TEXT,
    role_label TEXT,
    station_id TEXT NOT NULL DEFAULT 'posto_01',
    command_key TEXT,
    direction TEXT NOT NULL,          -- 'OUTBOUND' | 'INBOUND'
    sender_label TEXT NOT NULL,
    message_text TEXT NOT NULL,
    has_media INTEGER NOT NULL DEFAULT 0,
    media_caption TEXT,
    source TEXT NOT NULL DEFAULT 'android_handoff',
    external_msg_id TEXT,
    epoch_ts INTEGER NOT NULL,
    is_read INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_handoff_thread_epoch
    ON aura_handoff_messages(thread_phone, epoch_ts ASC);

CREATE INDEX IF NOT EXISTS idx_handoff_match_key
    ON aura_handoff_messages(match_key, epoch_ts DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_handoff_external_msg_id
    ON aura_handoff_messages(external_msg_id)
    WHERE external_msg_id IS NOT NULL;
```

- **Metodos em `AuraCommandJournal`:**
  1. `record_handoff_message(...) -> dict[str, Any]`:
     - Verifica primeiro se ja existe thread para o mesmo `match_key`; se existir, reutiliza o `thread_phone`, `contact_name` (se nao informado) e `role_label` daquela thread para nunca duplicar sessoes por diferenca do 9o digito.
     - Se `external_msg_id` ja existir no banco, retorna o registro existente sem duplicar (`already_exists=True`).
  2. `find_active_handoff_contact(raw_phone: str, lookback_hours: int = 72) -> dict[str, Any] | None`:
     - Busca pelo `match_key` se houve pelo menos 1 mensagem `OUTBOUND` nas ultimas `lookback_hours` horas, retornando `thread_phone`, `contact_name`, `role_label`, `first_outbound_epoch` e `last_command_key`.
  3. `list_active_outbound_threads(lookback_hours: int = 72) -> list[dict[str, Any]]`:
     - Retorna as threads que possuem envio `OUTBOUND` recente (com `thread_phone`, `contact_name`, `role_label`, `first_outbound_epoch`) para alimentar o sincronizador ativo da Evolution API.
  4. `list_handoff_threads(limit: int = 30) -> list[dict[str, Any]]`:
     - Retorna a lista de threads ordenadas por `last_epoch_ts DESC`, incluindo `unread_count` (`SUM(CASE WHEN direction='INBOUND' AND is_read=0 THEN 1 ELSE 0 END)`) e a lista de `messages` da thread.
  5. `mark_handoff_thread_read(raw_phone: str) -> int`:
     - Marca `is_read = 1` para todas as mensagens `INBOUND` daquele `match_key`.

### 4.3. Sincronizador Ativo Evolution API (`sync_inbound_messages_from_evolution` em `core/webhooks.py`)
- Implementar funcao assincrona em `core/webhooks.py` com controle de cooldown em memoria (`_last_evolution_sync_ts: float = 0.0`, intervalo minimo `6.0` segundos):
  1. Chama `journal.list_active_outbound_threads(lookback_hours=72)`. Se vazio, retorna imediatamente (`0ms`).
  2. Para cada thread ativa (ate 5 threads recentes):
     - Consulta `POST {EVOLUTION_API_URL}/chat/findMessages/{EVOLUTION_INSTANCE}` com cabecalho `{"apikey": EVOLUTION_API_KEY}` e body:
       `{"where": {"key": {"remoteJid": jid}}, "limit": 15}` (testando os JIDs de `whatsapp_jid_candidates(thread_phone)`).
     - Percorre `response["messages"]["records"]`:
       - Filtra estritamente:
         - `record.get("key", {}).get("fromMe") is False`
         - `int(record.get("messageTimestamp") or 0) >= int(thread["first_outbound_epoch"]) - 5`
       - Extrai o texto de `record["message"]`:
         - `conversation`
         - `extendedTextMessage.text`
         - `imageMessage.caption` (ou `"[Imagem recebida no WhatsApp]"`)
         - `documentMessage.caption` / `documentMessage.fileName` (ou `"[Documento recebido no WhatsApp]"`)
         - `audioMessage` -> `"[Audio recebido no WhatsApp]"`
       - Grava via `journal.record_handoff_message(..., direction="INBOUND", external_msg_id=record["key"]["id"], epoch_ts=int(record["messageTimestamp"]), is_read=0)`.

### 4.4. Endpoints em `core/partner_api.py`
1. **`POST /api/v1/partner/handoff` (`partner_handoff_endpoint`):**
   - Adicionar campo opcional `role_label: str | None = Field(default=None)` em `PartnerHandoffRequest`.
   - Ao enviar mensagem (e midia opcional), registrar em `journal.record_handoff_message(...)` com `direction="OUTBOUND"`, `is_read=1`, `has_media=media_sent`.
   - Retornar tambem `session_id = f"wa_handoff_{norm_phone}"` e `thread_phone = norm_phone`.
2. **`POST /api/v1/partner/handoff-reply`:**
   - Suporta payload direto do Painel CRM (`phone`, `message_text`, `external_msg_id`) e payload webhook bruto `MESSAGES_UPSERT` da Evolution API.
   - Correlaciona com `journal.find_active_handoff_contact(phone)` e grava como `INBOUND` (`is_read=0`).
3. **`GET /api/v1/partner/handoffs`:**
   - Parametro opcional `sync_evolution: bool = Query(default=True)`.
   - Quando `sync_evolution=True`, chama `await sync_inbound_messages_from_evolution(journal)` antes de retornar `journal.list_handoff_threads()`.
4. **`POST /api/v1/partner/handoffs/{phone}/read`:**
   - Marca todas as mensagens `INBOUND` da thread como lidas (`is_read=1`).

---

## 5. Especificacao do App Android (`Aura Assistance Android`)

### 5.1. Persistencia da Miniatura do Documento por Thread (`ChatViewModel.kt`)
- Quando o gestor envia um handoff com anexo (`includeAttachment == true` e `cachedHandoffDocFile.exists()`):
  - Copiar `cachedHandoffDocFile` para `File(cacheDir, "vision_scans/handoff_${normPhone}_${System.currentTimeMillis()}.jpg")`.
  - Na sessao dedicada `wa_handoff_<normPhone>`, salvar a mensagem enviada pelo usuario com `envelopeJson` do tipo `user_vision_card` apontando `previewPath` para essa copia dedicada, garantindo que a miniatura da nota enviada permaneca visivel na conversa do Contador mesmo se outras notas forem escaneadas depois!

### 5.2. Uso dos Olhos da AURA Dentro de uma Sessao `wa_handoff_<phone>`
- Se o gestor estiver com uma sessao `wa_handoff_<phone>` aberta e tocar no botao da camera (**Olhos da AURA**), apos recortar e ler a foto:
  - Em `ChatViewModel.sendScannedDocument(telemetry)`:
    - Se `_currentSessionId.value.startsWith("wa_handoff_")`, em vez de enviar apenas para o chat analitico, envia o resumo extraido + a imagem recortada em anexo diretamente para o WhatsApp daquele contato via `dispatchPartnerHandoff` e registra o card visual na sessao `wa_handoff_<phone>`!

### 5.3. Polling Leve, Pilula Flutuante no Topo e Abas de Sessao (`ChatViewModel.kt` & `ChatScreen.kt`)
1. **Polling em Foreground (`ChatViewModel.kt`):**
   - Loop a cada `8.000ms` chamando `apiService.getHandoffThreads()`.
   - Sincroniza cada thread como `ChatSessionEntity(sessionId = "wa_handoff_${thread.thread_phone}", title = "📲 ${thread.role_label ?: "WhatsApp"} • ${thread.contact_name}")` e insere novas mensagens no `ChatDao` (usando `id = "wa_msg_${msg.message_id}"` com `OnConflictStrategy.IGNORE` ou preservando `previewPath` local nas mensagens `OUTBOUND`).
   - Guarda um `mutableSetOf<String>()` (`notifiedInboundMessageIds`): quando chegar uma mensagem `INBOUND` com `unread_count > 0` cujo `message_id` ainda nao foi alertado e a sessao ativa nao for aquela thread, popula `_incomingHandoffAlert.value = IncomingHandoffAlert(...)`.
2. **Pilula Flutuante no Topo (`HandoffReplyTopBanner` em `ChatScreen.kt`):**
   - Renderizada logo abaixo do `ChatHeader` com `AnimatedVisibility`.
   - Exibe: `💬 {roleLabel}: {contactName} respondeu`, previa da mensagem (`maxLines = 1`), botao **`Abrir`** (chama `viewModel.openHandoffThread(alert.sessionId, alert.phone)`) e botao `X` (`viewModel.dismissIncomingHandoffAlert()`).
3. **Modal de Historico com 2 Abas (`Analises AURA` | `Retornos WhatsApp`):**
   - Na abertura de `showSessionsSheet`:
     - Seletor horizontal de 2 abas no topo:
       - Aba 0: **`Analises AURA`** (filtra `!it.sessionId.startsWith("wa_handoff_")`).
       - Aba 1: **`Retornos WhatsApp`** com badge verde exibindo `totalUnreadHandoffs` quando `> 0`.
     - Cada item na aba `Retornos WhatsApp` exibe o nome/cargo, telefone, previa da ultima mensagem e badge de nao lidas (`unread_count`).
4. **Barra de Contexto e Resposta Direta na Sessao `wa_handoff_<phone>`:**
   - Quando `currentSessionId.startsWith("wa_handoff_")`:
     - Exibe barra superior compacta abaixo do `ChatHeader`: `"Canal Direto WhatsApp • {Nome} ({Telefone})"` com botao **`Voltar p/ AURA`** (que carrega a sessao `"default"`).
     - Qualquer mensagem enviada no `Composer` (sem prefixo `@aura`) chama `sendDirectWhatsAppReply(text)` -> `POST /api/v1/partner/handoff`, enviando direto ao WhatsApp do contato!
     - Se comecar com `@aura `, consulta a IA AURA normalmente dentro da propria sessao para ajudar a redigir ou tirar duvida.

---

## 6. Roteiro de Execucao em 5 Etapas e Validacao

1. **Etapa 1 (`core/command_journal.py`):** implementar `normalize_whatsapp_phone`, `phone_match_key`, `whatsapp_jid_candidates`, tabela `aura_handoff_messages` e metodos `record_handoff_message`, `find_active_handoff_contact`, `list_active_outbound_threads`, `list_handoff_threads`, `mark_handoff_thread_read`.
2. **Etapa 2 (`core/webhooks.py` & `core/partner_api.py`):** implementar `sync_inbound_messages_from_evolution`, atualizar `POST /api/v1/partner/handoff`, criar `POST /api/v1/partner/handoff-reply`, `GET /api/v1/partner/handoffs` e `POST /api/v1/partner/handoffs/{phone}/read`, e persistir pendencias fiscais em `partner_quick_action_endpoint`.
3. **Etapa 3 (`core/aura_engine.py` & `AuraVisionNpuScanner.kt`):** blindar diretiva fiscal (Entrada = Banco Web / Documento capturado; Saida PDV = Banco Local `:5433`) e incluir XML limpo no prompt de `scanXmlUri` para `auditar_documento_xml`.
4. **Etapa 4 (`AuraApiService.kt`, `ChatViewModel.kt`, `ChatScreen.kt`):** adicionar DTOs/rotas de handoff threads, polling de 8s, sincronizacao Room, `HandoffReplyTopBanner`, abas `Analises AURA` | `Retornos WhatsApp` e envio direto de texto/foto na sessao `wa_handoff_<phone>`.
5. **Etapa 5 (Testes e Deploy Local):**
   - Criar `tests/unit/test_handoff_threads.py` testando:
     - Criacao de thread `OUTBOUND`;
     - Correlacao com e sem 9o digito (`phone_match_key`);
     - Sincronizacao `findMessages` da Evolution API com filtro temporal `messageTimestamp >= first_outbound_epoch` e `fromMe == False`;
     - Ingestao via `POST /api/v1/partner/handoff-reply` e bloqueio de numeros sem handoff ativo;
     - Contagem de nao lidas (`unread_count`) e limpeza via `POST /api/v1/partner/handoffs/{phone}/read`.
   - Executar `pytest -q tests/unit/test_handoff_threads.py tests/unit/test_partner_api.py tests/unit/test_fiscal_engine.py`.
   - Compilar `.\gradlew assembleDebug` e instalar via `adb install -r` no dispositivo.

---

## 7. Fase 2: Evolucao UI/UX, Identidade Evolution API e Hub de Retornos por Contato

### 7.1. Diagnostico e Objetivos da Fase 2
Apos a validacao em producao do fluxo de handoff e captura de retornos (`@lid` / `remoteJidAlt`), tres pontos de experiencia do usuario (UI/UX) e enriquecimento de dados foram definidos para tornar a operacao mais intuitiva, moderna e executiva:

1. **Acesso Direto no Rodape da Pagina Principal (`DashboardScreen.kt`):**
   - O gestor precisa de um **icone dedicado de Retornos WhatsApp fixo no rodape (Bottom Dock)** da tela principal (`DashboardScreen`), ao lado do botao principal de abertura do AURA Chat.
   - Esse icone deve exibir em tempo real um **badge pulsante de mensagens nao lidas** e levar com 1 toque diretamente para a sessao de **Retornos WhatsApp** (`onNavigateToChat("OPEN_WHATSAPP_HANDOFFS_TAB")`).

2. **Enriquecimento Automatico de Identidade via Evolution API (`pushName` e Perfil do Contato):**
   - Nenhum contato na sessao de retornos deve aparecer como um "numero flutuante" (ex: `5527992277217`) ou apenas com o rotulo generico do cargo (`Contador`) quando a Evolution API possui o nome real do contato no WhatsApp (ex: `Marlon Henrique`).
   - O backend deve resolver e persistir o nome real do contato a partir de duas fontes da Evolution API v2:
     - **Busca Ativa de Contatos (`POST {EVOLUTION_API_URL}/chat/findContacts/{EVOLUTION_INSTANCE}`):** consulta por `remoteJid` nos candidatos do telefone (`whatsapp_jid_candidates(phone)`), extraindo `pushName`, `name`, `verifiedName` e `profilePicUrl`.
     - **Captura Passiva/Ativa em Mensagens (`findMessages` e Webhook `MESSAGES_UPSERT`):** extrai o `pushName` de todas as mensagens recebidas (`fromMe == False`) e atualiza retroativamente (`backfill`) os registros daquela thread em `aura_handoff_messages` cujo `contact_name` esteja vazio, seja igual ao numero do telefone ou seja identico ao `role_label` (`Contador`, `Gerente`, etc.).
   - O payload de `GET /api/v1/partner/handoffs` passa a expor claramente:
     - `contact_name`: Nome real da pessoa obtido no Evolution/WhatsApp (ex: `"Marlon Henrique"`).
     - `role_label`: Cargo ou funcao operacional (ex: `"Contador"`, `"Gerente"`, `"Fornecedor"`).
     - `formatted_phone`: Numero formatado para leitura humana (ex: `"+55 (27) 99227-7217"`), exibido apenas como metadado secundario.
     - `profile_pic_url`: URL opcional da foto de perfil retornada pela Evolution API.

3. **Separacao Visual dos Retornos por Contato (`ChatScreen.kt` - Hub Master-Detail):**
   - Na aba **Retornos WhatsApp**, os retornos devem ser **separados e organizados por contato** de forma visualmente imediata, evitando misturar fluxos ou jogar o usuario em um numero solto.
   - A aba **Retornos WhatsApp** passa a operar com uma arquitetura **Hub de Contatos + Conversa Isolada (Master-Detail Fluido)**:
     - **Nivel 1 - Hub de Contatos (`WhatsAppContactsHubView`):** grade/lista executiva de cards separados por contato, com filtros rapidos (`Todos`, `Nao Lidos`, `Respondidos`), avatar com iniciais/foto e indicador de presenca, **Nome do Evolution em destaque**, **Badge colorido do Cargo** (`Contador`, `Gerente`), telefone formatado discreto, previa da ultima mensagem (`INBOUND` ou `OUTBOUND`), horario relativo e contador de nao lidas.
     - **Nivel 2 - Conversa Exclusiva do Contato (`WhatsAppContactConversationView`):** ao tocar em um contato no Hub, abre o historico exclusivo daquele contato com:
       - **Header de Identidade do Contato:** Nome real (`Marlon Henrique`), badge do cargo (`Contador`), telefone formatado (`+55 (27) 99227-7217`) e botao **`<- Contatos`** para voltar ao Hub de Contatos.
       - **Faixa Rapida de Alternancia entre Contatos (`QuickContactSwitcherRow`):** chips horizontais no topo da conversa permitindo alternar de um contato para outro (ex: de `Marlon Henrique (Contador)` para `Marcos (Gerente)`) com 1 toque e badge individual de nao lidas por contato.

---

### 7.2. Fluxo Arquitetural da Fase 2 (Mermaid)

```mermaid
flowchart TD
    subgraph Dashboard["Dashboard Principal (Rodape Fixo)"]
        Dock["Spatial Bottom Dock\n[Abrir AURA Chat] + [Icone Retornos WhatsApp c/ Badge]"]
    end

    subgraph Backend["Backend FastAPI + Evolution API v2"]
        FindContacts["POST /chat/findContacts/{instance}\n(pushName + profilePicUrl)"]
        FindMessages["POST /chat/findMessages/{instance}\n(remoteJid + remoteJidAlt + pushName)"]
        Backfill["AuraCommandJournal.update_thread_contact_identity()\nSubstitui numero cru/cargo pelo pushName real"]
    end

    subgraph WhatsAppHub["Sessao Retornos WhatsApp (UI Separada por Contatos)"]
        HubList["Nivel 1: Hub de Contatos\nCards separados por Contato (Nome Evolution + Cargo + Previa + Badge)"]
        ConvView["Nivel 2: Conversa Isolada do Contato\nChips Rapidos de Contatos no Topo + Historico + Resposta Direta"]
    end

    Dock -->|"1 Toque no Icone do Rodape"| HubList
    FindContacts --> Backfill
    FindMessages --> Backfill
    Backfill -->|"GET /api/v1/partner/handoffs"| HubList
    HubList -->|"Seleciona Contato"| ConvView
    ConvView -->|"Botao Contatos ou Chip Superior"| HubList
```

---

### 7.3. Especificacao Tecnica do Backend (Fase 2)

#### 7.3.1. Formatacao Humana e Backfill de Identidade (`core/command_journal.py`)
1. **Funcao `format_brazil_phone_display(raw_phone: str | None) -> str`:**
   - Converte `"5527992277217"` em `"+55 (27) 99227-7217"` e `"552792277217"` em `"+55 (27) 9227-7217"`.
2. **Funcao `is_generic_or_numeric_name(name: str | None, phone: str | None = None, role: str | None = None) -> bool`:**
   - Retorna `True` quando `name` e vazio, contem apenas digitos/simbolos de telefone, coincide com `phone_match_key(phone)` ou coincide com rotulos genericos (`"whatsapp"`, `"contador"`, `"gerente"`, `"fornecedor"`, `"financeiro"`, `"contato"`).
3. **Metodo `update_thread_contact_identity(self, raw_phone: str, contact_name: str, role_label: str | None = None) -> int`:**
   - Atualiza todos os registros daquele `match_key` em `aura_handoff_messages` onde `contact_name` seja nulo ou generico/numerico, gravando o nome real vindo da Evolution API (`pushName`).
4. **Enriquecimento em `list_handoff_threads()`:**
   - Ao consolidar as mensagens de uma thread:
     - Prioriza o primeiro `contact_name` nao-generico; se todos os `contact_name` salvos forem genericos/numericos, inspeciona o `sender_label` das mensagens `INBOUND` (que guarda o `pushName` da Evolution) e promove-o automaticamente para `contact_name`!
     - Inclui no dicionario de cada thread o campo `"formatted_phone": format_brazil_phone_display(t_phone)`.

#### 7.3.2. Lookup de Contato na Evolution API (`core/webhooks.py`)
1. **Funcao Assincrona `fetch_evolution_contact_profile(phone: str, http_client: httpx.AsyncClient | None = None) -> dict[str, str | None]`:**
   - Consulta `POST {EVOLUTION_API_URL}/chat/findContacts/{EVOLUTION_INSTANCE}` para os candidatos JID de `phone`.
   - Caso a busca filtrada retorne vazio, faz fallback seguro filtrando por `phone_match_key` sobre os contatos retornados.
   - Extrai:
     - `push_name`: primeiro valor util entre `pushName`, `name`, `verifiedName`, `notify`.
     - `profile_pic_url`: `profilePicUrl` quando presente.
   - Mantem cache em memoria (`_evolution_contact_cache: dict[str, tuple[float, dict]]`, TTL de `300s`) para zero latencia adicional no polling.
2. **Integracao em `sync_inbound_messages_from_evolution` (`core/webhooks.py`):**
   - Sempre que uma mensagem `INBOUND` trouxer `rec.get("pushName")` valido (ex: `"Marlon Henrique"`), passa esse nome tambem para `journal.update_thread_contact_identity(thread_phone, push_name)` e salva no `record_handoff_message(..., contact_name=resolved_contact_name)`.
   - Se a thread ainda estiver com `contact_name` generico/numerico mesmo sem novas mensagens, consulta `fetch_evolution_contact_profile(thread_phone)` e atualiza `journal.update_thread_contact_identity(...)` imediatamente.

---

### 7.4. Especificacao Tecnica do App Android (Fase 2)

#### 7.4.1. Rodape Fixo na Pagina Principal com Icone de Retornos (`DashboardScreen.kt` e `DashboardViewModel.kt`)
1. **Contador de Retornos no Dashboard (`DashboardViewModel.kt`):**
   - Adiciona `handoffUnreadCount: StateFlow<Int>` e `handoffTotalThreads: StateFlow<Int>` alimentados por `apiService.getHandoffThreads(syncEvolution = true)` na inicializacao e em polling leve (`15.000ms`), permitindo exibir o badge no rodape mesmo antes de abrir o Chat.
2. **Barra de Rodape Espacial (`DashboardBottomDock` em `DashboardScreen.kt`):**
   - Posicionada no `bottomBar` do `Scaffold` (ou fixada na base da tela com glassmorphism `ObsidianSurface` + borda luminescente):
     - **Botao Principal (Esquerda/Centro - `weight(1f)`):** `"Abrir AURA Chat"` (`AuraGradientButton`).
     - **Botao de Retornos WhatsApp (Direita - Icone Dedicado 56x56dp):** container circular/arredondado em vidro esmeralda (`StatusSuccess.copy(alpha = 0.16f)` com borda `StatusSuccess.copy(alpha = 0.45f)`), icone `Icons.Rounded.Forum` / `Icons.AutoMirrored.Rounded.ReplyAll`, rotulo compacto `"Retornos"` e **Badge pulsante** no canto superior direito exibindo `handoffUnreadCount` (ou ponto indicador ativo quando houver conversas abertas).
     - Ao clicar no icone do rodape, navega direto para `onNavigateToChat("OPEN_WHATSAPP_HANDOFFS_TAB")`.

#### 7.4.2. Separacao por Contatos na Sessao de Retornos (`ChatViewModel.kt` e `ChatScreen.kt`)
1. **Estado de Navegacao Interna do Hub (`ChatViewModel.kt`):**
   - Quando o usuario entra na aba **`Retornos WhatsApp`** (seja pelo icone do rodape da pagina principal, pelo card do Dashboard ou pela aba superior do Chat):
     - Introduz `_isViewingWhatsAppContactList: MutableStateFlow<Boolean>`:
       - Por padrao, ao tocar na aba **`Retornos WhatsApp`** ou no icone do rodape, abre o **Hub de Contatos (`_isViewingWhatsAppContactList = true`)** separando claramente cada contato que possui handoff/retorno ativo.
       - Ao tocar em um contato especifico (ou no botao `Abrir` do banner de alerta no topo), define `_isViewingWhatsAppContactList = false` e carrega a sessao `wa_handoff_<phone>` daquele contato.
       - O botao **`<- Contatos`** na barra superior da conversa volta imediatamente para `_isViewingWhatsAppContactList = true`.
2. **Design do Hub de Contatos (`WhatsAppContactsHubView` em `ChatScreen.kt`):**
   - **Header Resumo do Hub:** exibe total de contatos em acompanhamento, total de retornos nao lidos e botao de sincronizacao imediata (`Sincronizar agora`).
   - **Filtros Rapidos (Chips):** `Todos ({N})`, `Nao Lidos ({Unread})`, `Respondidos ({Inbound})`.
   - **Cards Executivos por Contato (`WhatsAppContactThreadCard`):**
     - **Avatar Identitario:** circulo com iniciais do nome real (ex: `MH` para `Marlon Henrique`) + ponto de status verde quando houve resposta (`last_direction == "INBOUND"`).
     - **Linha Principal:** Nome real do Evolution em destaque (`Marlon Henrique`) + **Pill Badge do Cargo** ao lado (`Contador` em ciano/esmeralda).
     - **Subtitulo Discreto:** Telefone formatado (`+55 (27) 99227-7217`) - nunca solto sem nome!
     - **Box de Ultima Mensagem:** indica claramente se foi `↩ Resposta recebida:` (destaque esmeralda) ou `↗ Enviado pelo AURA:`, com previa de ate 2 linhas, horario e **Badge de Nao Lidas** (`unread_count`).
3. **Faixa Superior de Contatos Dentro da Conversa (`QuickContactSwitcherRow` em `ChatScreen.kt`):**
   - Mesmo dentro da conversa de um contato (`_isViewingWhatsAppContactList == false`), exibe uma barra horizontal deslizante de chips compactos com todos os contatos ativos (ex: `[← Todos os Contatos]  [🟢 Marlon Henrique • Contador]  [⚪ Marcos • Gerente]`).
   - Permite alternar entre os retornos de diferentes contatos com 1 unico toque e ver o nome real + cargo no cabecalho da conversa.

---

### 7.5. Roteiro de Implementacao da Fase 2 (Etapas 6 a 8)

1. **Etapa 6 (Backend - Identidade Evolution API e Backfill):**
   - Atualizar `core/command_journal.py` (`format_brazil_phone_display`, `is_generic_or_numeric_name`, `update_thread_contact_identity` e fallback automatico para `sender_label` de mensagens `INBOUND` em `list_handoff_threads`).
   - Atualizar `core/webhooks.py` (`fetch_evolution_contact_profile` via `/chat/findContacts/{instance}` + backfill imediato em `sync_inbound_messages_from_evolution`) e `core/partner_api.py` (enriquecer `contact_name` no `POST /api/v1/partner/handoff` e `POST /api/v1/partner/handoff-reply`).
   - Adicionar testes unitarios em `tests/unit/test_handoff_threads.py` cobrindo o enriquecimento de nome via `pushName` / `findContacts` e substituicao de numeros flutuantes.
2. **Etapa 7 (Android - Icone de Retornos no Rodape Principal):**
   - Atualizar `DashboardViewModel.kt` e `DashboardScreen.kt` adicionando o `DashboardBottomDock` fixo no rodape da pagina principal com o botao `"Abrir AURA Chat"` e o icone dedicado de **`Retornos WhatsApp`** com badge ao vivo.
3. **Etapa 8 (Android - Hub de Retornos Separado por Contato e Header Rico):**
   - Atualizar `AuraApiService.kt` (`formatted_phone`, `profile_pic_url`), `ChatViewModel.kt` (`isViewingWhatsAppContactList`, `showWhatsAppContactsHub()`, formatacao de nome/telefone) e `ChatScreen.kt` (`WhatsAppContactsHubView`, `WhatsAppContactThreadCard`, `QuickContactSwitcherRow` e `ActiveWhatsAppSessionBar` com Nome Evolution + Cargo + Telefone formatado).
   - Compilar APK (`.\gradlew assembleDebug`), instalar via ADB (`adb install -r`) e validar em producao.

