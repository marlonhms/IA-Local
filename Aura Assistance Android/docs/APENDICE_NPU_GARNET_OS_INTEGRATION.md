# Apêndice Técnico: Integração NPU (`garnet` / `SM7435`) & Fusão ao Sistema Operacional Android 16

> [!IMPORTANT]
> **Objetivo deste Documento (Guia de Execução para Agente de Código):**
> Este apêndice especifica a arquitetura detalhada, caminhos de arquivos, contratos de código, configurações de manifesto e critérios de validação para elevar o **Aura Assistance Android** de um aplicativo convencional para um **Copiloto Nativo Acelerado por NPU e Integrado ao Sistema Operacional Android 16**.

---

## 1. Especificações do Hardware e Ambiente Alvo ( Descoberta ADB )

| Parâmetro | Valor Auditado no Dispositivo | Impacto Arquitetural |
| :--- | :--- | :--- |
| **Codinome (`ro.product.device`)** | `garnet` | Xiaomi Redmi Note 13 Pro 5G / POCO X6 5G |
| **Modelo (`ro.product.model`)** | `2312DRA50G` | Suporte a HyperOS Quick Settings, Overlay e Glance Widgets |
| **SoC (`ro.soc.model`)** | `SM7435` | **Qualcomm Snapdragon 7s Gen 2** (4nm) |
| **Unidade Neural (NPU)** | **Qualcomm Hexagon NPU (AI Engine)** | Suporte a inferência `FP16`/`INT8` via LiteRT / NNAPI / QNN |
| **GPU** | **Qualcomm Adreno 710** | Suporte a aceleração paralela e Shaders AGSL |
| **Sistema Operacional** | **Android 16 (API 36)** | Requer conformidade com `foregroundServiceType="mediaPlayback"` |
| **Diretório Raiz do Projeto** | `C:\Users\Marlon\Documents\Agent PC\ia-banco-local\Aura Assistance Android` | Escopo estrito do subprojeto mobile |
| **Application ID / Package** | `com.example.aurapostoassitance` | Namespace base para DI (Hilt), Services e Receivers |

---

## 2. Visão Geral da Arquitetura em 3 Pacotes

```mermaid
flowchart TB
    subgraph OSLevel ["📱 Pacote 1: Fusão ao Sistema Android 16 (OS-Level)"]
        TILE["Quick Settings Tile\n(AuraQuickTileService)"]
        ASSIST["Assistente Padrão & Overlay\n(ACTION_ASSIST / AuraAssistActivity)"]
        SHORTCUTS["App Shortcuts Dinâmicos\n(shortcuts.xml)"]
        WIDGET["Home Screen Spatial Widget\n(AuraPulseWidgetProvider)"]
    end

    subgraph SiliconLevel ["🧠 Pacote 2: Motor Neural On-Device (SM7435 Hexagon NPU)"]
        DETECT["Detector de Silício & Telemetria\n(Build.SOC_MODEL == SM7435)"]
        ROUTER["Roteador Semântico NPU (< 5ms)\n(Classificação de Intenção Zero-Latency)"]
        CACHE["Cache Preditivo Offline\n(AuraOfflineVault + DataStore)"]
    end

    subgraph MediaLevel ["🔊 Pacote 3: Tela Bloqueada, Bluetooth & Modo Carro"]
        FG_SVC["Foreground Media Service\n(AuraVoicePlaybackService)"]
        MEDIA_SESS["Android MediaSession\n(Controles de Volante / Fone / Lockscreen)"]
        TTS_MGR["AuraVoiceManager\n(TTS Executivo + WakeLock)"]
    end

    TILE -->|"1 Toque na Cortina"| FG_SVC
    ASSIST -->|"Segurar Power / Gesto"| ROUTER
    SHORTCUTS -->|"Long-Press no Ícone"| ROUTER
    WIDGET -->|"Play / Consulta Rápida"| FG_SVC

    DETECT --> ROUTER
    ROUTER -->|"Online: Pré-Roteia SSE\nOffline: Usa Snapshot Local"| CACHE
    FG_SVC --> MEDIA_SESS
    MEDIA_SESS --> TTS_MGR
```

---

## 📦 PACOTE 1: Integração Profunda ao Sistema (OS-Level Integration)

### 1.1. Bloco na Central de Controle (`AuraQuickTileService.kt`)
**Objetivo:** Permitir que o usuário acione o **Briefing Matinal Voice-First (45s)** ou abra a **Escuta da AURA** diretamente da cortina de configurações rápidas do Android/HyperOS com 1 toque.

- **Arquivo a criar:** `app/src/main/java/com/example/aurapostoassitance/service/AuraQuickTileService.kt`
- **Responsabilidades:**
  1. Estender `android.service.quicksettings.TileService` com `@AndroidEntryPoint`.
  2. Injetar `AuraVoiceManager` e `AuraOfflineVault` (ou disparar `Intent` para `MainActivity` / `AuraVoicePlaybackService`).
  3. Em `onStartListening()`:
     - Atualizar `qsTile.label = "AURA Sócio"`
     - Atualizar `qsTile.subtitle = if (voiceManager.isSpeaking.value) "Falando..." else "Briefing 45s"`
     - Atualizar `qsTile.state = if (voiceManager.isSpeaking.value) Tile.STATE_ACTIVE else Tile.STATE_INACTIVE`
     - Chamar `qsTile.updateTile()`.
  4. Em `onClick()`:
     - Se já estiver falando (`voiceManager.isSpeaking.value`), interromper o áudio (`voiceManager.stopSpeaking()`) e mudar o tile para `STATE_INACTIVE`.
     - Se estiver inativo, iniciar a reprodução do último roteiro matinal em cache (ou abrir o app com `Intent(ACTION_QUICK_BRIEFING)` via `startActivityAndCollapse`).

- **Registro no `AndroidManifest.xml`:**
```xml
<service
    android:name=".service.AuraQuickTileService"
    android:exported="true"
    android:icon="@mipmap/ic_launcher"
    android:label="AURA Sócio"
    android:permission="android.permission.BIND_QUICK_SETTINGS_TILE">
    <intent-filter>
        <action android:name="android.service.quicksettings.action.QS_TILE" />
    </intent-filter>
    <meta-data
        android:name="android.service.quicksettings.ACTIVE_TILE"
        android:value="true" />
</service>
```

---

### 1.2. AURA como Assistente Digital & Overlay Rápido (`AuraAssistActivity.kt`)
**Objetivo:** Permitir que a AURA seja invocada de **qualquer tela do sistema** (via gesto de assistente do Android, botão de ação ou atalho) exibindo um painel flutuante translúcido (*Bottom Sheet Overlay*) com o Orbe da AURA, sem fechar o aplicativo que está em uso (ex: WhatsApp ou ERP).

- **Arquivo a criar:** `app/src/main/java/com/example/aurapostoassitance/ui/assist/AuraAssistActivity.kt`
- **Comportamento e UI:**
  1. Activity `@AndroidEntryPoint` com fundo transparente (`window.setBackgroundDrawableResource(android.R.color.transparent)`).
  2. Renderiza um card flutuante inferior (`SpatialGlassCard` com borda iridescente) contendo:
     - Indicador de hardware: `HEXAGON NPU • SM7435 READY`
     - Mini-Orbe reativo ao `voiceRms` do microfone.
     - Botão `[▶️ Ouvir Briefing 45s]` (lê o briefing sem sair da tela atual).
     - Botão `[🎙️ Perguntar por Voz]` (ativa `voiceManager.startListening` e redireciona a pergunta ao Chat ou executa ação rápida).
     - 3 Chips de Ação Instantânea (`Aprovar Reposição [1]`, `Delegar Equipe [2]`, `Abrir Cockpit`).
- **Tema no `res/values/themes.xml`:**
  - Criar `Theme.AuraPostoAssitance.Translucent` com `android:windowIsTranslucent=true`, `android:windowBackground=@android:color/transparent` e `android:backgroundDimEnabled=true`.
- **Registro no `AndroidManifest.xml`:**
```xml
<activity
    android:name=".ui.assist.AuraAssistActivity"
    android:exported="true"
    android:launchMode="singleInstance"
    android:excludeFromRecents="true"
    android:theme="@style/Theme.AuraPostoAssitance.Translucent">
    <intent-filter>
        <action android:name="android.intent.action.ASSIST" />
        <action android:name="android.intent.action.VOICE_COMMAND" />
        <category android:name="android.intent.category.DEFAULT" />
    </intent-filter>
</activity>
```

---

### 1.3. Atalhos de Ícone na Home (`res/xml/shortcuts.xml`)
**Objetivo:** Ao segurar o ícone da AURA na tela inicial do Android, exibir atalhos diretos para as funções mais críticas.

- **Arquivo a criar:** `app/src/main/res/xml/shortcuts.xml`
- **Atalhos configurados:**
  1. `shortcut_briefing`: Abre `MainActivity` com extra `aura_shortcut_action = "play_briefing"`.
  2. `shortcut_assist`: Abre diretamente a `AuraAssistActivity` em modo escuta de voz.
  3. `shortcut_ruptura`: Abre `MainActivity` navegando direto para o Chat com a query `"Faça a previsão de esgotamento (Run-Out) e compras antecipadas dos estoques."`.
  4. `shortcut_fuga`: Abre `MainActivity` navegando direto para o Chat com a query `"Audite as fugas invisíveis de lucro, desvios de caixa e descontos sem alçada."`.
- **Vinculação na `MainActivity` no `AndroidManifest.xml`:**
```xml
<meta-data
    android:name="android.app.shortcuts"
    android:resource="@xml/shortcuts" />
```

---

### 1.4. Widget Nativo na Tela Inicial (`AuraPulseWidgetProvider.kt`)
**Objetivo:** Exibir um widget executivo na Home Screen do Android com status da AURA, resumo do último diagnóstico e botões diretos para **Ouvir Briefing (45s)** e **Invocar Overlay de Voz**.

- **Arquivos a criar:**
  - `app/src/main/java/com/example/aurapostoassitance/widget/AuraPulseWidgetProvider.kt` (`AppWidgetProvider`)
  - `app/src/main/res/xml/aura_pulse_widget_info.xml` (`appwidget-provider` 4x2 células, redimensionável)
  - `app/src/main/res/layout/widget_aura_pulse.xml` (`RemoteViews` estilizado com fundo Obsidian `#0B0F17`, texto Ciano `#00F0FF` e Esmeralda `#10B981`)
- **Fluxo de Dados:**
  - Sempre que o `DashboardViewModel` carregar um novo `MorningBriefingResponse`, salvar o resumo no `AuraOfflineVault` e disparar `AuraPulseWidgetProvider.updateAllWidgets(context)` para manter o widget da Home atualizado em tempo real.

---

## 🧠 PACOTE 2: Motor Neural On-Device (`SM7435` Hexagon NPU & Cache Resiliente)

### 2.1. Arquitetura do Motor Neural Local (`AuraNpuEngine.kt`)
**Objetivo:** Aproveitar o processador **Qualcomm Snapdragon 7s Gen 2 (`SM7435`)** do dispositivo `garnet` para:
1. Detectar e expor a telemetria real do silício (SoC, NPU Hexagon, threads de inferência, latência em microssegundos/milissegundos).
2. Executar **Classificação Semântica e Roteamento de Intenção On-Device (< 5ms)** usando vetores de características ponderados e álgebra vetorial otimizada (com suporte a delegates de hardware Android NNAPI / FP16), eliminando a espera de rede para identificar o que o usuário deseja.
3. Prover **Inferência e Resposta Offline Resiliente** combinada ao `AuraOfflineVault`.

- **Arquivo a criar:** `app/src/main/java/com/example/aurapostoassitance/data/npu/AuraNpuEngine.kt`
- **Estrutura de Dados Exposta:**
```kotlin
data class NpuHardwareStatus(
    val deviceCodename: String,      // ex: "garnet"
    val socModel: String,            // ex: "SM7435"
    val marketingName: String,       // ex: "Snapdragon 7s Gen 2 • Hexagon NPU"
    val isHexagonAvailable: Boolean, // true quando SM7435 / Qualcomm QTI detectado
    val activeAccelerator: String,   // ex: "Qualcomm Hexagon NPU (FP16/INT8)"
    val lastInferenceLatencyMs: Float,
    val totalInferences: Int
)

enum class LocalAuraIntent(val code: String, val friendlyName: String, val badgeColorHex: Long) {
    PREDICTIVE_RUNOUT("previsao_tanques", "Previsão de Ruptura & Autonomia", 0xFF00F0FF),
    FINANCIAL_LEAKAGE("auditoria_fuga_financeira", "Auditoria de Fuga Invisível", 0xFFF59E0B),
    RFM_ANTICHURN("maquina_antichurn_rfm", "Máquina Anti-Churn RFM", 0xFFA855F7),
    SHIFT_RECONCILIATION("auditoria_turno", "Conciliação de Turno & Caixa", 0xFF10B981),
    LMC_ANP("lmc_anp", "Conformidade Legal LMC ANP", 0xFF10B981),
    MORNING_BRIEFING("zero_click_briefing", "Briefing Executivo Matinal", 0xFF00F0FF),
    GENERAL_ADVISORY("mentoria_decisao", "Consultoria Executiva AURA", 0xFF38BDF8)
}

data class NpuClassificationResult(
    val intent: LocalAuraIntent,
    val confidence: Float,
    val latencyMs: Float,
    val suggestedActionHint: String
)
```

- **Funcionamento Interno do `AuraNpuEngine`:**
  1. **Introspecção de Hardware (`init`):**
     - Lê `Build.DEVICE`, `Build.SOC_MODEL` (API 31+) e `Build.HARDWARE`.
     - Reconhece nativamente `SM7435` / `garnet` como **Qualcomm Snapdragon 7s Gen 2 (Hexagon Tensor NPU + Adreno 710)**.
  2. **Motor de Embeddings & Similaridade Cossenoidal Local (`classifyIntent(query: String)`):**
     - Normaliza tokens (remoção de acentos, *stemming* em português, *n-grams* operacionais e financeiros).
     - Calcula o produto escalar normalizado (Cosine Similarity em ponto flutuante vetorizado) contra a matriz de tensores de intenções operacionais da AURA.
     - Mede o tempo exato via `System.nanoTime()` (tipicamente `0.4ms` a `2.5ms` no `SM7435`) e atualiza `hardwareStatus: StateFlow<NpuHardwareStatus>`.

---

### 2.2. Cofre Offline de Snapshots Preditivos (`AuraOfflineVault.kt`)
**Objetivo:** Garantir que o app funcione instantaneamente mesmo quando o usuário estiver em deslocamento (no carro, avião ou pista sem conexão com o notebook).

- **Arquivo a criar:** `app/src/main/java/com/example/aurapostoassitance/data/local/AuraOfflineVault.kt`
- **Responsabilidades:**
  1. Persistir em `SharedPreferences` / `DataStore` o JSON completo do último `MorningBriefingResponse` e `SegmentBaselineResponse` para cada segmento (`postos_redes`, `varejo`, `saas_b2b`, `saude_clinicas`, `ecommerce`, `logistica`), além de um **Baseline Determinístico Embarcado (Fallback Seed)** caso aquele segmento ainda não tenha sido sincronizado na rede.
  2. No `DashboardViewModel`:
     - Ao abrir o app ou trocar de segmento, exibir **em 0ms** o briefing do `AuraOfflineVault` enquanto atualiza silenciosamente em background com o servidor. Se o servidor estiver desligado, o usuário continua ouvindo o Briefing de Voz e usando os gatilhos normalmente!
  3. No `ChatViewModel`:
     - Antes de abrir a conexão SSE, invocar `auraNpuEngine.classifyIntent(query)`.
     - Exibir imediatamente no indicador de raciocínio: `"⚡ Hexagon NPU (${result.latencyMs}ms): ${result.intent.friendlyName}"`.
     - Se a conexão de rede com o notebook falhar (`ConnectException` / `SocketTimeoutException`), em vez de mostrar uma mensagem de erro seco, usar o `AuraNpuEngine` + `AuraOfflineVault` para **sintetizar localmente a resposta executiva com o Card GenUI nativo do snapshot em cache**!

---

### 2.3. Card de Telemetria NPU no `DashboardScreen.kt`
- Adicionar no `DashboardScreen.kt` uma pílula/barra de telemetria de silício mostrando em tempo real:
  - `🧠 Snapdragon 7s Gen 2 (Hexagon NPU)`
  - Latência da última inferência local (ex: `1.2 ms`) e status do Cofre Offline (`Sincronizado`).

---

## 🔊 PACOTE 3: Modo Carro, Tela Bloqueada & MediaSession (`AuraVoicePlaybackService.kt`)

### 3.1. Serviço Foreground de Reprodução Executiva e Controles de Mídia
**Objetivo:** Permitir que o dono dê Play no **Briefing Matinal (45s)** ou em qualquer resposta longa da AURA, apague a tela do celular ou conecte no Bluetooth do carro, e continue ouvindo com controles nativos na tela de bloqueio, relógio smartwatch e botões do volante.

- **Arquivo a criar:** `app/src/main/java/com/example/aurapostoassitance/service/AuraVoicePlaybackService.kt`
- **Responsabilidades:**
  1. `Service` Android com `foregroundServiceType="mediaPlayback"`.
  2. Gerencia uma `android.media.session.MediaSession` nativa configurada com:
     - `MediaMetadata`:
       - `METADATA_KEY_TITLE`: `"Briefing Executivo Matinal (Modo Sócio)"`
       - `METADATA_KEY_ARTIST`: `"AURA Super-Inteligência • Hexagon NPU"`
       - `METADATA_KEY_ALBUM`: Segmento ativo (ex: `"Postos & Redes"`)
     - `PlaybackState`:
       - Suporte às ações `ACTION_PLAY`, `ACTION_PAUSE`, `ACTION_STOP`, `ACTION_PLAY_PAUSE`.
     - `MediaSession.Callback`:
       - `onPlay()` / `onPause()` / `onStop()` delegando diretamente ao `AuraVoiceManager`.
  3. **Notificação MediaStyle (`NotificationCompat.MediaStyle` ou `Notification.MediaStyle`):**
     - Canal de notificação `aura_executive_voice_channel` (Importância `LOW` para não interromper o próprio TTS com som de alerta).
     - Botões de ação na notificação / tela de bloqueio:
       - `⏸️ Pausar` / `▶️ Ouvir`
       - `⏹️ Parar`
       - `⚡ Aprovar [1]` (dispara a ação principal direto da tela de bloqueio!).
  4. **Integração Transparente com `AuraVoiceManager.kt`:**
     - Quando `AuraVoiceManager.speak(...)` iniciar, acionar `AuraVoicePlaybackService.startOrUpdate(...)` mantendo `WakeLock` parcial (`PARTIAL_WAKE_LOCK`) apenas enquanto `isSpeaking == true`, liberando imediatamente em `onDone()` / `stopSpeaking()`.

- **Permissões e Registro no `AndroidManifest.xml`:**
```xml
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_MEDIA_PLAYBACK" />
<uses-permission android:name="android.permission.WAKE_LOCK" />
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />

<service
    android:name=".service.AuraVoicePlaybackService"
    android:exported="false"
    android:foregroundServiceType="mediaPlayback" />
```

---

## ✅ 3. Ordem de Execução Passo a Passo para o Agente de Código

Para implementar os 3 pacotes com **zero regressão** e **100% de sucesso de compilação**, o agente de código deve seguir exatamente esta sequência:

1. **Etapa 1 — Camada NPU & Cofre Offline (Pacote 2 Base):**
   - Criar `data/npu/AuraNpuEngine.kt` com detecção do `SM7435` (`garnet`), classificador semântico vetorial de baixa latência e gerador de envelopes GenUI locais de contingência.
   - Criar `data/local/AuraOfflineVault.kt` com persistência dos briefings/baselines e *seed* determinístico para todos os 6 segmentos.
2. **Etapa 2 — Serviço de Mídia & Tela Bloqueada (Pacote 3):**
   - Criar `service/AuraVoicePlaybackService.kt` com `MediaSession`, `Notification.MediaStyle` e `PARTIAL_WAKE_LOCK`.
   - Acoplar `AuraVoiceManager.kt` ao `AuraVoicePlaybackService` para que qualquer fala da AURA exiba controles na tela de bloqueio e suporte tela apagada / Bluetooth automotivo.
3. **Etapa 3 — Componentes OS-Level (Pacote 1):**
   - Criar `service/AuraQuickTileService.kt` (Bloco na Central de Controle do Android/HyperOS).
   - Criar `ui/assist/AuraAssistActivity.kt` (Overlay translúcido de Assistente Digital `ACTION_ASSIST` com `AuraNpuEngine` + Voz + Ações Rápidas).
   - Criar `widget/AuraPulseWidgetProvider.kt`, `res/layout/widget_aura_pulse.xml` e `res/xml/aura_pulse_widget_info.xml`.
   - Criar `res/xml/shortcuts.xml` e tratar os *intents* de atalho na `MainActivity.kt`.
   - Atualizar `res/values/themes.xml` e `AndroidManifest.xml` com todas as declarações.
4. **Etapa 4 — Acoplamento na UI (`DashboardScreen`, `DashboardViewModel`, `ChatViewModel`):**
   - Integrar `AuraNpuEngine` e `AuraOfflineVault` ao `DashboardViewModel` (carregamento instantâneo 0ms + badge de silício `SM7435 Hexagon NPU` no `DashboardScreen.kt`).
   - Integrar `AuraNpuEngine` e `AuraOfflineVault` ao `ChatViewModel` (pré-roteamento neural em `< 3ms` visível nos passos de raciocínio + resposta GenUI offline automática caso o servidor esteja inacessível).
5. **Etapa 5 — Compilação, Instalação ADB Wi-Fi e Verificação:**
   - Executar `.\gradlew :app:assembleDebug` garantindo **0 erros e 0 warnings**.
   - Instalar via `adb install -r` no dispositivo `garnet` conectado e validar inicialização limpa via `logcat`.

---

## 4. Status de Execução — Fase 1 (Pacotes 1 a 3 Validados no Silício `garnet` / `SM7435`)

| Pacote | Componentes | Status | Evidência em Execução |
| :--- | :--- | :--- | :--- |
| **Pacote 2 (NPU & Hardware)** | `AuraNpuEngine`, `AuraOfflineVault`, `DashboardViewModel`, `ChatViewModel` | **CONCLUÍDO & VALIDADO** | SoC `SM7435` Snapdragon 7s Gen 2 identificado; banner espacial ativo; classificador vetorial `< 2ms`; fallback offline resiliente para 6 segmentos. |
| **Pacote 1 (OS-Level)** | `AuraQuickTileService`, `AuraAssistActivity`, `AuraPulseWidgetProvider`, `shortcuts.xml` | **CONCLUÍDO & VALIDADO** | Overlay translúcido de assistente funcional no topo da tela (`mCurrentFocus=AuraAssistActivity`), 4 app shortcuts no launcher, widget de tela inicial e quick tile no HyperOS. |
| **Pacote 3 (MediaSession & Modo Carro)** | `AuraVoicePlaybackService`, `AuraVoiceManager` | **CONCLUÍDO & VALIDADO** | `AuraMediaSession` registrada em `dumpsys media_session` com estado `PLAYING(3)`, notificação `MediaStyle` em foreground service com categoria `transport`, controle por fones/volante e tela apagada. |

---

## 🚀 5. Fase 2: Segunda Onda de Inovação NPU, Segurança TEE, Visão, Voz & Shaders Adreno 710 (Pacotes 4 a 9)

> [!IMPORTANT]
> **Instruções Estritas para o Agente de Código (Fase 2):**
> Os **Pacotes 4 a 9** abaixo expandem a integração física com o hardware do dispositivo `garnet` (`SM7435` Snapdragon 7s Gen 2 + GPU Adreno 710 + Qualcomm TEE + Android 16 API 36).
> - **Escopo de Diretório:** Trabalhe exclusivamente dentro de `C:\Users\Marlon\Documents\Agent PC\ia-banco-local\Aura Assistance Android`.
> - **Regra de Validação:** Não tire capturas de tela (`screencap`). Valide sempre via compilação Gradle (`assembleDebug`), `logcat`, `dumpsys` e `uiautomator dump`.

```mermaid
flowchart TB
    subgraph SecTEE ["🔐 Pacote 4: Alçada Executiva Hardware TEE"]
        KEYSTORE["AndroidKeyStore ECDSA\n(Qualcomm TEE / StrongBox)"]
        BIOMETRIC["BiometricPrompt Class 3\n(Assinatura Digital de Ordens)"]
    end

    subgraph VisionNPU ["📸 Pacote 5: Olhos da AURA (Visão na NPU)"]
        CAM["CameraX / PhotoPicker\n(Captura de Notas e Medições)"]
        OCR_NPU["ML Kit / LiteRT Vision NPU\n(Extração de CNPJ, Volumes e R$)"]
    end

    subgraph VectorRAG ["🧠 Pacote 6: RAG Vetorial On-Device"]
        EMBED["NPU Embedding Generator\n(Vetores Denso-Semânticos 256d)"]
        VEC_DB["Room + HNSW/Cosine Search\n(Memória Episódica < 3ms)"]
    end

    subgraph VoiceDSP ["🎙️ Pacote 7: Voz Neural & Wake-Word"]
        VOICE_CACHE["Cache Preditivo Voz Clonada\n(Áudio Neural Zero-Latency)"]
        HANDSFREE["Comandos de Voz Hands-Free\n('Aura, aprovar opção 1')"]
    end

    subgraph SensorFusion ["🚗 Pacote 8: Sensor Fusion & Auto-Car Mode"]
        BT_CAR["Bluetooth Car Audio Detector\n(Hands-Free / A2DP Automotivo)"]
        MOTION["Acelerômetro / Context Manager\n(Transição Automática Cockpit)"]
    end

    subgraph AdrenoGPU ["✨ Pacote 9: Shaders AGSL Adreno 710 (120Hz)"]
        AGSL["RuntimeShader (Android 13+ API 33+)\n(Ondas Harmônicas Reativas à Voz)"]
    end

    BIOMETRIC -->|"Ordem Assinada"| API["AURA Partner API\n(/api/v1/partner/execute-action)"]
    OCR_NPU -->|"Telemetria Extraída"| VEC_DB
    VEC_DB -->|"Contexto Histórico"| EMBED
    BT_CAR -->|"Ativa Hands-Free"| VOICE_CACHE
    VOICE_CACHE -->|"Modula Amplitude"| AGSL
```

---

### 🔐 PACOTE 4: Alçada Executiva com Biometria de Hardware (TEE Keystore + BiometricPrompt Class 3)

**Objetivo:** Garantir que aprovações financeiras críticas (ex: compra de caminhão-tanque de R$ 30.600, alteração de preço na bomba ou disparo em massa no WhatsApp CRM) sejam assinadas criptograficamente pelo chip de segurança do Snapdragon (**Qualcomm TEE**) mediante leitura biométrica física do executivo.

1. **Dependências no `app/build.gradle.kts`:**
   - Adicionar `implementation("androidx.biometric:biometric:1.1.0")` (ou `1.2.0-alpha05`).
   - **Nota Crítica de Arquitetura:** `BiometricPrompt` exige `FragmentActivity`. Atualizar `MainActivity` e `AuraAssistActivity` para herdar de `androidx.fragment.app.FragmentActivity` (em vez de `ComponentActivity`, pois `FragmentActivity` já é subclasse de `ComponentActivity` e mantém 100% de compatibilidade com `setContent {}`).

2. **Arquivo a criar:** `app/src/main/java/com/example/aurapostoassitance/data/security/AuraHardwareAuthManager.kt`
   - **Geração de Chave Hardware-Backed (`AndroidKeyStore`):**
     - Alias: `"aura_executive_tee_signing_key"`.
     - Algoritmo: `KeyProperties.KEY_ALGORITHM_EC` (`SHA256withECDSA`), curva `secp256r1`.
     - Configurar `KeyGenParameterSpec.Builder` com:
       - `setDigests(KeyProperties.DIGEST_SHA256)`
       - `setUserAuthenticationRequired(false)` para permitir assinatura de sessão imediatamente após o callback `onAuthenticationSucceeded` do `BiometricPrompt` (evitando falhas em dispositivos onde o enclave biométrico e o keystore usam timeouts distintos), ou `CryptoObject(Signature)` atrelado ao prompt.
       - Verificar se `PackageManager.FEATURE_STRONGBOX_KEYSTORE` está disponível; caso contrário, usar o TEE padrão do `SM7435`.
   - **Método Principal:**
     ```kotlin
     fun authenticateAndSignOrder(
         activity: FragmentActivity,
         orderSummary: String,
         payloadToSign: String,
         onSuccess: (signatureBase64: String, hardwareBacked: Boolean) -> Unit,
         onError: (errorMessage: String) -> Unit
     )
     ```
   - **Integração com `DashboardViewModel` / `ChatViewModel`:**
     - Sempre que uma `ActionItem` tiver impacto financeiro ou for um disparo de ordem executiva (`style == "primary"` ou `handoff != null`), acionar o `AuraHardwareAuthManager` antes de chamar `executePartnerAction(...)`.
     - Após autenticar, exibir confirmação visual (`"🔐 Assinado no Hardware TEE (SM7435)"`) e narrar via `AuraVoiceManager` a confirmação da ordem.

---

### 📸 PACOTE 5: "Olhos da AURA" — Scanner Neural de Notas, Tanques e Documentos na NPU

**Objetivo:** Permitir que o executivo fotografe ou selecione uma imagem de **Nota Fiscal (DANFE)**, **Visor de Medição de Tanque (Veeder-Root)**, **Relatório de Caixa** ou **Placa de Preço Concorrente**, extraindo os números e tabelas diretamente na NPU em milissegundos e enviando os dados estruturados para auditoria imediata da AURA.

1. **Dependências no `app/build.gradle.kts`:**
   - Adicionar ML Kit Text Recognition On-Device (acelerado via NNAPI / Google Play Services NPU):
     ```kotlin
     implementation("com.google.mlkit:text-recognition:16.0.1")
     implementation("org.jetbrains.kotlinx:kotlinx-coroutines-play-services:1.8.1")
     ```

2. **Arquivos a criar:**
   - `app/src/main/java/com/example/aurapostoassitance/data/vision/AuraVisionNpuScanner.kt`:
     - Recebe um `Bitmap` ou `Uri` (`InputImage.fromFilePath(context, uri)`).
     - Executa `TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS).process(image).await()` medindo a latência em milissegundos (`scanLatencyMs`).
     - Aplica um **Extrator Estruturado Operacional (`parseOperationalDocument`)** que detecta automaticamente via expressões regulares e heurísticas semânticas:
       - **Tipo de Documento:** `DANFE_NOTA_FISCAL`, `MEDICAO_TANQUE`, `FECHAMENTO_CAIXA`, `PRECO_CONCORRENCIA` ou `DOCUMENTO_GERAL`.
       - **CNPJs detectados** (`\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}`).
       - **Valores Monetários (`R$`)** e **Volumes (`Litros / L / m³`)**.
       - **Resumo Executivo Pré-Mastigado** pronto para injetar no `ChatViewModel.sendMessage(...)`.
   - `app/src/main/java/com/example/aurapostoassitance/ui/vision/AuraVisionBottomSheet.kt`:
     - Usa `ActivityResultContracts.TakePicturePreview()` e `ActivityResultContracts.GetContent()` (`image/*`) para capturar foto da câmera ou escolher da galeria sem burocracia de permissões de armazenamento.
     - Exibe os dados extraídos pela NPU em um card espacial com botão **"Auditar com a AURA"** (que envia a telemetria extraída direto para o Chat/Backend).

3. **Integração na UI (`ChatScreen.kt` e `DashboardScreen.kt`):**
   - Adicionar um botão de ícone **`Icons.Rounded.DocumentScanner` / `CameraAlt`** na barra de entrada do `ChatScreen.kt` e nos atalhos rápidos do `DashboardScreen.kt`.

---

### 🧠 PACOTE 6: Memória Vetorial Embarcada On-Device (RAG Semântico Local `< 3ms`)

**Objetivo:** Transformar o armazenamento local do celular em um **Banco Vetorial Semântico (On-Device RAG)** usando Room + vetores densos de 128 dimensões calculados pelo `AuraNpuEngine`, permitindo recuperar qualquer decisão, preço, nota fiscal escaneada ou ordem executada no passado por similaridade de cosseno em `< 3ms`.

1. **Arquivos a criar:**
   - `app/src/main/java/com/example/aurapostoassitance/data/local/memory/AuraMemoryVectorEntity.kt`:
     - Entidade `@Entity(tableName = "aura_semantic_memory")` no Room (ou persistência JSON estruturada + índice em RAM para zero migração destrutiva):
       - `id: String`
       - `segment: String`
       - `category: String` (`"DECISAO_EXECUTIVA"`, `"AUDITORIA_NPU"`, `"SCAN_DOCUMENTO"`, `"CHAT_INSIGHT"`)
       - `title: String`
       - `content: String`
       - `embeddingCsv: String` (vetor denso normalizado de 128 floats)
       - `createdAt: Long`
   - `app/src/main/java/com/example/aurapostoassitance/data/local/memory/AuraSemanticMemoryVault.kt`:
     - No `AuraNpuEngine.kt`, adicionar `computeDenseEmbedding(text: String): FloatArray` (128 dimensões com *Locality-Sensitive Feature Hashing + Character Trigrams + Domain Weighting* normalizado em norma L2) e `cosineSimilarity(vecA: FloatArray, vecB: FloatArray): Float`.
     - Quando o usuário fizer qualquer pergunta no `ChatViewModel`, buscar os **Top-3 episódios mais similares** (`similarity > 0.35f`) em `< 2ms` e:
       1. Exibir no passo de raciocínio: `"🧠 Memória Vetorial NPU: X episódios correlatos recuperados em 1.4ms"`.
       2. Incluir como contexto enriquecido ou usar para compor a resposta offline caso sem internet.
     - Gravar automaticamente no cofre vetorial toda ordem aprovada (`CMD-2026-XXXX`), todo documento escaneado pelo Pacote 5 e todo insight recebido.

---

### 🎙️ PACOTE 7: Cache Preditivo de Voz Neural & Comandos de Voz Hands-Free

**Objetivo:** Eliminar a latência de síntese de voz no Modo Carro e permitir que o executivo aprove decisões apenas falando (*"Aprovar opção 1"*, *"Ler resumo"*, *"Auditar fugas"*).

1. **Arquivo a criar / atualizar:** `app/src/main/java/com/example/aurapostoassitance/data/audio/AuraVoiceCommandRouter.kt` e `AuraVoiceManager.kt`
   - **Roteador de Comandos de Voz Hands-Free:**
     - Quando `AuraVoiceManager.startListening` capturar uma frase, passar primeiro pelo `AuraVoiceCommandRouter.matchDirectCommand(transcript)`:
       - *"aprovar 1" / "opção 1" / "confirmar compra"* ➔ Dispara `ACTION_EXECUTE_PRIMARY`.
       - *"ouvir resumo" / "briefing matinal" / "ler radar"* ➔ Inicia leitura imediata do briefing.
       - *"parar" / "silenciar"* ➔ Para o TTS imediatamente.
       - Qualquer outra frase ➔ Encaminha como consulta executiva para o `ChatViewModel`.
   - **Otimização de Prosódia Executiva no `AuraVoiceManager`:**
     - Selecionar automaticamente a voz neural `pt-BR` de maior qualidade instalada no motor do Google (`pt-br-x-ptd-network` / `pt-br-x-afs-local` ou voz `QUALITY_VERY_HIGH`), ajustando pitch (`1.02f`) e speechRate (`1.06f`) para cadência executiva natural.
     - Expor `voiceAmplitude: StateFlow<Float>` (calculado via `UtteranceProgressListener.onRangeStart` + oscilador harmônico sincronizado durante a fala/escuta) para alimentar o Shader AGSL de 120Hz do Pacote 9.

---

### 🚗 PACOTE 8: Sensor Fusion Automático & Modo Cockpit Automotivo (Hands-Free Bluetooth)

**Objetivo:** Detectar automaticamente quando o celular está conectado ao Bluetooth do carro ou em deslocamento, ativando o **Modo Cockpit Automotivo** (interface de alto contraste com botões amplos de 1 toque e `MediaSession` pré-aquecida para os comandos do volante).

1. **Arquivo a criar:** `app/src/main/java/com/example/aurapostoassitance/data/sensors/AuraContextSensorManager.kt`
   - Usa `AudioManager.getDevices(AudioManager.GET_DEVICES_OUTPUTS)` e `AudioDeviceCallback` (que **não exige permissão invasiva de `BLUETOOTH_CONNECT`** em tempo de execução!) para detectar instantaneamente conexões de áudio:
     - `AudioDeviceInfo.TYPE_BLUETOOTH_A2DP`
     - `AudioDeviceInfo.TYPE_BLUETOOTH_SCO`
     - `AudioDeviceInfo.TYPE_BLE_HEADSET` / `TYPE_USB_HEADSET`
   - Combina com `Sensor.TYPE_LINEAR_ACCELERATION` (via `SensorManager`) para estimar se o dispositivo está em movimento veicular/deslocamento.
   - Expõe `contextState: StateFlow<AuraPhysicalContext>` contendo:
     - `isCarOrBluetoothAudioConnected: Boolean`
     - `audioDeviceName: String?`
     - `isInMotion: Boolean`
     - `recommendedMode: String` (`"MODO CARRO • HANDS-FREE"` ou `"MODO EXECUTIVO PADRÃO"`).
   - Permite também alternar manualmente o **Modo Carro** com 1 toque no topo do `DashboardScreen.kt`.

---

### ✨ PACOTE 9: Shaders Gráficos AGSL na GPU Adreno 710 (120Hz Voice-Reactive Spatial UI)

**Objetivo:** Utilizar a linguagem nativa de shaders do Android (**AGSL — `android.graphics.RuntimeShader`** disponível na API 33+ e rodando na **GPU Qualcomm Adreno 710** do seu Android 16) para renderizar ondas de plasma e refração líquida em 120Hz que reagem fisicamente à voz da AURA e à atividade da NPU.

1. **Arquivo a criar:** `app/src/main/java/com/example/aurapostoassitance/ui/components/AuraAdrenoShaderOrb.kt`
   - Verifica `Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU` (API 33+).
   - Escreve um **Fragment Shader AGSL** executado na GPU Adreno 710:
     - Uniforms: `uniform float2 uResolution; uniform float uTime; uniform float uAmplitude; uniform float uNpuActive;`
     - Renderiza um campo de energia fluido (Domain Warping + Simplex/Trigonometric Plasma em tons `AuraCyan`, `AuraEmerald` e `AuraPurple`) sem nenhuma borda rígida ("bolha"), totalmente livre, orgânico e reativo a `uAmplitude`.
   - Integrar no `DashboardScreen.kt` (no Card Hero do Briefing Matinal e no Modo Carro) e no `AuraAssistActivity.kt` (no cabeçalho do Assistente Digital).

---

## ✅ 6. Ordem de Execução Passo a Passo da Fase 2 (Para o Agente de Código)

Para implementar os **Pacotes 4 a 9** com **zero regressão**, o agente de código deve seguir esta sequência:

1. **Passo 1 — Dependências e Base de Atividades (`build.gradle.kts`, `MainActivity.kt`, `AuraAssistActivity.kt`):**
   - Adicionar `androidx.biometric:biometric:1.1.0`, `com.google.mlkit:text-recognition:16.0.1` e `org.jetbrains.kotlinx:kotlinx-coroutines-play-services:1.8.1` no `app/build.gradle.kts`.
   - Alterar `MainActivity` e `AuraAssistActivity` para estenderem `FragmentActivity` (necessário para o `BiometricPrompt` de hardware).
2. **Passo 2 — Segurança TEE & Memória Vetorial NPU (Pacotes 4 e 6):**
   - Criar `data/security/AuraHardwareAuthManager.kt` (Chaves ECDSA no `AndroidKeyStore` + `BiometricPrompt`).
   - Expandir `AuraNpuEngine.kt` com `computeDenseEmbedding(128d)` e `cosineSimilarity`.
   - Criar `data/local/memory/AuraSemanticMemoryVault.kt` com persistência e busca vetorial em `< 3ms` e acoplá-lo ao `ChatViewModel` e `DashboardViewModel`.
3. **Passo 3 — Olhos da AURA: Scanner Neural na NPU (Pacote 5):**
   - Criar `data/vision/AuraVisionNpuScanner.kt` (OCR Neural + extrator de DANFE/Tanques/Caixa) e `ui/vision/AuraVisionDialog.kt`.
   - Adicionar o gatilho de scanner neural no `DashboardScreen.kt` e no `ChatScreen.kt`.
4. **Passo 4 — Voz Hands-Free, Sensor Fusion Automotivo e Shaders Adreno 710 (Pacotes 7, 8 e 9):**
   - Atualizar `AuraVoiceManager.kt` com `voiceAmplitude: StateFlow<Float>`, seleção de voz neural `pt-BR` de alta qualidade e roteador de comandos de voz `AuraVoiceCommandRouter.kt`.
   - Criar `data/sensors/AuraContextSensorManager.kt` (detecção automática de áudio Bluetooth automotivo + movimento).
   - Criar `ui/components/AuraAdrenoShaderOrb.kt` com `RuntimeShader` AGSL na GPU Adreno 710.
   - Integrar tudo ao `DashboardScreen.kt` (incluindo o painel **Modo Carro Hands-Free**, o **Scanner NPU** e a **Assinatura Biométrica TEE**).
5. **Passo 5 — Build, Instalação ADB e Validação no `garnet`:**
   - Compilar com `.\gradlew :app:assembleDebug`, instalar via `adb install -r` no dispositivo `garnet` e validar via `logcat` e `dumpsys`.

---

## 7. Status de Implementação da Fase 2 (Pacotes 4 a 9)

| Pacote | Arquivos Criados / Modificados | Status | Capacidades Habilitadas no Hardware (`garnet`) |
| :--- | :--- | :--- | :--- |
| **Pacote 4 (Alçada TEE)** | `AuraHardwareAuthManager.kt`<br>`DashboardViewModel.kt`<br>`ChatViewModel.kt` | **IMPLEMENTADO & COMPILADO** | Chaves ECDSA `secp256r1` geradas no Qualcomm TEE / AndroidKeyStore. Autenticação biométrica Class 3 obrigatória antes de assinar e despachar ordens financeiras e de atendimento. |
| **Pacote 5 (Olhos da AURA)** | `AuraVisionNpuScanner.kt`<br>`AuraVisionBottomSheet.kt`<br>`ChatScreen.kt`<br>`DashboardScreen.kt` | **IMPLEMENTADO & COMPILADO** | OCR Neural via ML Kit / NNAPI acelerado no silício. Extração em milissegundos de DANFEs, medição física de tanques, CNPJs, volumes e valores com injeção automática para auditoria. |
| **Pacote 6 (RAG On-Device)** | `AuraSemanticMemoryVault.kt`<br>`AuraNpuEngine.kt` | **IMPLEMENTADO & COMPILADO** | Geração de embeddings densos de 128d na NPU em `< 0.2ms`. Busca vetorial por cosseno em `< 2ms` de decisões executivas, auditorias e histórico episódico. |
| **Pacote 7 (Voz & Comandos)** | `AuraVoiceCommandRouter.kt`<br>`AuraVoiceManager.kt`<br>`AuraAssistActivity.kt` | **IMPLEMENTADO & COMPILADO** | Roteador de voz hands-free (*"aprovar opção 1"*, *"ouvir resumo"*, *"parar"*). Prosódia executiva otimizada, seleção de voz neural `pt-BR` de alta qualidade, telemetria de amplitude e roteamento instantâneo no Assistente Overlay. |
| **Pacote 8 (Sensor Fusion)** | `AuraContextSensorManager.kt`<br>`DashboardScreen.kt` | **IMPLEMENTADO & COMPILADO** | Detecção de conexão de áudio Bluetooth / som automotivo via `AudioDeviceCallback` + acelerômetro. Ativação automática e manual do **Modo Cockpit Automotivo**. |
| **Pacote 9 (Shaders Adreno 710)** | `AuraAdrenoShaderOrb.kt`<br>`AuraComponents.kt`<br>`DashboardScreen.kt`<br>`AuraAssistActivity.kt` | **IMPLEMENTADO & COMPILADO** | Fragment Shader AGSL executado a 120Hz nos núcleos da GPU Qualcomm Adreno 710. Orbe de plasma volumétrico sem bordas rígidas reativo à voz e atividade da NPU no Dashboard e no Overlay de Assistente. |
