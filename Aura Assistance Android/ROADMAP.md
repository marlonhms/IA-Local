# 📱 Roadmap de Desenvolvimento: Aura Posto Assistance (App Android)

**Visão Geral:** O App Android será um *Thin Client* (Cliente Leve) operando na rede interna do posto (Wi-Fi Local ou Tailscale IP). O backend da IA em FastAPI e o Banco Vetorial `pgvector` permanecem no PC ou Servidor Local. A interface do app deve ser fluida, responsiva e alinhada ao design "Aurora Boreal" do Painel Web existente.

### 🏛️ Fundações Arquiteturais (App Android)
*   **Padrão Arquitetural:** MVVM (Model-View-ViewModel) + Clean Architecture.
*   **UI/UX:** Jetpack Compose (Material Design 3 + Tematização inspirada no painel web - Cores Esmeralda, Ciano e Roxo).
*   **Conectividade Assíncrona:** Kotlin Coroutines e Flow (Essencial para SSE Stream).
*   **Cliente de Rede:** Retrofit + OkHttp (Com extensão para SSE - Server-Sent Events).
*   **Injeção de Dependências:** Hilt.

---

## 🚀 Fase 1: Setup do Projeto e Infraestrutura de Rede (Sprint 1)
**Foco:** Garantir que o aplicativo Android consiga se comunicar com o backend local do posto, superando as restrições de Cleartext e IP.

*   **1.1. Configurações Iniciais do Gradle:**
    *   Adicionar dependências essenciais: Jetpack Compose, Retrofit, OkHttp, Kotlin Serialization, Hilt e Navigation Compose.
*   **1.2. Segurança e Rede (networkSecurityConfig):**
    *   Configurar o Android para permitir conexões `HTTP` (sem HTTPS) estritamente para a rede local (ex: IPs `192.168.x.x` ou Tailscale `100.x.x.x`), pois a API FastAPI roda localmente na porta 8000.
*   **1.3. Gestão de Estado de Conexão e Onboarding:**
    *   Criar uma tela de "Setup/Configuração" simples onde o gerente informa o **IP do Servidor AURA** (caso não esteja usando descoberta de rede automática).
    *   Salvar esse IP de forma segura no `DataStore Preferences`.
*   **1.4. Mapeamento Retrofit (Endpoints Base):**
    *   `GET /api/v1/aura/health`: Monitorar a saúde da API.
    *   `GET /api/v1/aura/stations`: Validar conectividade com o ERP 5433 e pgvector 5434.

## 💬 Fase 2: Motor de Chat Inteligente via SSE (Sprint 2)
**Foco:** Construir a interface conversacional que consome os tokens gerados localmente pela IA (Gemini via Edge Python) com fluidez.

*   **2.1. Implementação do Cliente SSE (Server-Sent Events):**
    *   Configurar o `OkHttpClient` para consumir o endpoint `POST /api/v1/aura/chat` no formato stream (`text/event-stream`).
    *   Capturar a resposta token a token e convertê-la em um `StateFlow` na ViewModel para atualizar a UI reativamente (sensação de "Aura digitando...").
*   **2.2. Tela do Cockpit Cognitivo (Jetpack Compose):**
    *   Desenvolver a tela principal de Chat.
    *   Implementar a barra de texto (Input) com suporte a botões de ação rápida.
    *   Desenvolver o suporte a renderização de **Markdown nativo no Compose** (para tabelas de conversão, negritos e listas que o Gemini responde).
*   **2.3. Controle de Sessão:**
    *   Passar corretamente o `session_id` nas requisições HTTP para que a `AuraSessionMemory` (SQLite WAL no backend) mantenha o contexto da conversa, mesmo que o gerente feche e reabra o App.

## ⚡ Fase 3: Atalhos Visuais e Gatilhos Analíticos (Sprint 3)
**Foco:** Materializar os "Gatilhos 1-Clique" mapeados no seu roteador semântico como elementos visuais e de fácil acesso para o frentista ou gerente de pista.

*   **3.1. Cards de Decisão Rápida (Shortcuts):**
    *   Criar botões ou chips interativos na tela principal (abaixo da área de chat) que apontam para o endpoint `POST /api/v1/aura/execute-intent`.
    *   Gatilhos iniciais a serem mapeados no App:
        *   📊 **LMC ANP** (Tolerância $\pm 0.6\%$)
        *   ⛽ **Run-Out Forecast** (Autonomia de tanques)
        *   💰 **Conciliação de Turno** (Furos de caixa)
        *   🛒 **Vendas Cruzadas Conveniência**
*   **3.2. Interpretação de Intenções Especiais na UI:**
    *   Quando a IA devolver payloads estruturados, o App deve convertê-los em componentes visuais bonitos (Ex: em vez de ler um texto com o "nível do tanque", mostrar um gráfico de tanque vertical preenchido dinamicamente no Compose).

## 📡 Fase 4: Telemetria, Resiliência Offline e Persistência (Sprint 4)
**Foco:** Lidar com os problemas da vida real em postos de gasolina — o gerente caminhando na área dos tanques onde o sinal do Wi-Fi falha.

*   **4.1. Cache Local Inteligente com Room:**
    *   Armazenar mensagens do chat e resultados dos últimos diagnósticos localmente usando Room Database.
    *   Se o app perder a conexão Wi-Fi, exibir as conversas antigas e os últimos dados conhecidos em "modo offline/leitura" com uma badge visual (ex: *Dados atualizados às 14:05*).
*   **4.2. Monitoramento de Rede e Fallback Gracioso:**
    *   Implementar listeners de rede (ConnectivityManager) para alertar imediatamente caso o telefone perca comunicação com a VPN/Tailscale ou rede local do posto.

## 🔔 Fase 5: Notificações Nativas e Refinamento PWA (Sprint 5)
**Foco:** Engajar o gerente proativamente, sem que ele precise abrir o app para saber de problemas críticos.

*   **5.1. Background Workers (WorkManager):**
    *   Criar workers que consultam endpoints cruciais a cada X horas (ex: status dos tanques).
*   **5.2. Alertas Push Nativos (Local Notifications):**
    *   Disparar notificações Android padrão para alertas críticos reportados pelo RAG/FastAPI (Ex: *"Alerta Crítico: Filtro obstruído na Bomba 02"*).
*   **5.3. Integração Estilo "Aura Boreal":**
    *   Afinar paleta de cores (Esmeralda, Ciano e Roxo), animações (Material 3 Transitions) e polir a experiência mobile para imitar a fluidez projetada na versão Web.

## 🛡️ Fase 6: Segurança, Testes e Distribuição (Sprint 6)
**Foco:** Polimento, testes e deploy para os gerentes de pista.

*   **6.1. Segurança:**
    *   Implementação de ofuscação de código (ProGuard/R8) no Android.
    *   Garantir que não existam IPs ou tokens hardcoded (usar DataStore Preferences para o gerente digitar o IP do servidor local / Tailscale no primeiro acesso).
*   **6.2. Testes Automatizados:**
    *   Testes Unitários na camada de ViewModel.
    *   Testes de UI (Compose UI Tests) nas telas de Chat e Dashboard.
*   **6.3. Empacotamento e Distribuição (APK/MDM):**
    *   Geração do APK assinado.
    *   Distribuição B2B via sideload direto ou MDM nos coletores de pista.