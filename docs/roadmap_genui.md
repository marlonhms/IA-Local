# Roadmap Executivo & Técnico: Implementação de GenUI & Server-Driven UI no AURA Edge AI

> **AURA IntelligentUI (GenUI/SDUI v1.0)** — Transformando a interface conversacional da AURA em um cockpit transacional, efémero e determinístico no Edge, com micro-widgets reativos em 3 camadas, idempotência criptográfica, Guided Decoding e isolamento cibernético.

- **Data de Criação:** 07/10/2026  
- **Versão do Documento:** 2.0.0 (Revisão Técnica & Alinhamento Arquitetural Definitivo)  
- **Status:** Proposto para Execução Imediata  
- **Documento de Referência Arquitetural:** [`docs/Arquitetura GenUI para Edge AI.md`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/docs/Arquitetura%20GenUI%20para%20Edge%20AI.md)  
- **Repositório:** `C:\Users\Marlon\Documents\Agent PC\ia-banco-local`  
- **Público-alvo:** Engenharia de Software, Arquitetura de IA, UX/UI Designers e Operações de Postos B2B  

---

## 1. Visão Executiva & Contexto Estratégico

### 1.1 O Desafio e a Tese de Valor
O paradigma tradicional de interfaces para modelos de linguagem (LLMs) apoia-se na devolução de texto livre ou tabelas estáticas formatadas em **Markdown**. No contexto de operações críticas e de alta intensidade no varejo de combustíveis e lojas de conveniência (B2B), este formato impõe sérias deficiências cognitivas e operacionais:
1. **Sobrecarga Cognitiva (Cognitive Overhead):** O gestor do posto precisa garimpar blocos densos de texto para encontrar métricas vitais de autonomia de tanques, bicos com vazão defasada ou divergências de caixa PDV.
2. **Ausência de Affordances Transacionais:** Tabelas Markdown não oferecem botões de ação imediata (e.g., aprovação de compra de carreta, bloqueio de bico descalibrado ou homologação fiscal), forçando o operador a abrir o ERP legado, buscar telas secundárias e digitar dados manualmente.
3. **Riscos de Segurança Cibernética:** Parsers genéricos de Markdown expõem o cliente a vulnerabilidades de injeção de tags HTML/XSS e violam diretrizes do **OWASP Top 10 for LLMs** (especialmente **LLM01 - Prompt Injection** e **LLM03 - Excessive Agency**).

A arquitetura **Generative UI (GenUI)** combinada com **Server-Driven UI (SDUI)** resolve esses atritos. O modelo de linguagem deixa de ser um "gerador de texto livre" e assume a função de **motor de raciocínio, classificação e decisão de estado**. A interface no navegador transforma-se em um orquestrador efémero de **micro-widgets nativos em três camadas**, renderizados dinamicamente a partir de **Structured Outputs tipados** (Pydantic v2 no backend / contratos rígidos no cliente).

```
+----------------------------------------------------------------------------------------------------+
|                                    PARADIGMA TRADICIONAL (MARKDOWN)                                |
|  Usuário: "Como estão os tanques?"                                                                  |
|  LLM: "Olá! Segue o status:                                                                       |
|        - Tanque 04 (Diesel S10): 3.200 L restantes. Autonomia de 4.2 horas. Recomendo comprar."     |
|  [Problema: Sem ação direta, sem gráfico, requer digitação manual no ERP, risco de alucinação]     |
+----------------------------------------------------------------------------------------------------+
                                                  ▼
+----------------------------------------------------------------------------------------------------+
|                                    PARADIGMA GENUI / SDUI (AURA)                                   |
|  Usuário: "Como estão os tanques?"                                                                  |
|  Backend: Roteador -> Consulta SQL ERP 5433 -> Cálculo Determinístico -> Envelopamento GenUI        |
|  Stream SSE:                                                                                       |
|    1. Camada 1: Resumo Executivo em Streaming (TTFT < 300ms)                                       |
|    2. Camada 2: Skeleton UI -> Hidratação de Widget Nativo (Gauges SVG, 15% vs 0L, Espaço Livre)    |
|    3. Camada 3: Action Sheet Transacional com Idempotência [⚡ Aprovar Pedido de Carreta 15.000 L]  |
|  [Vantagem: 100% determinístico, zero código vindo do LLM, ação em 1 clique com rollback]          |
+----------------------------------------------------------------------------------------------------+
```

### 1.2 Princípios Inegociáveis de Engenharia da AURA
1. **Zero Regressão na Stack Existente:** Manter 100% da compatibilidade funcional com as 11 ferramentas analíticas (`core/tools.py`), os contratos Pydantic v1.0 (`core/schemas/`), o Companion Canvas de 4 perspectivas (`web/js/aura-aux-panel.js`), a suíte de DecisionCards (`web/js/aura-chat.js`) e as rotas do FastAPI (`core/aura_api.py`).
2. **Determinismo Numérico Inabalável:** Volumes de combustível, valores de caixa, tolerâncias legais da ANP (Portaria 26: ±0.60%) e métricas de frentistas **nunca são inventados pelo LLM**. São calculados pelas funções matemáticas do Python a partir de dados reais do PostgreSQL local (`posto_ai:5433`) e transmitidos via propriedades tipadas (`props`).
3. **Isolamento Transacional Read-Only com Gateway de Ação Human-in-the-Loop:** A consulta primária ao ERP permanece estritamente *Read-Only*. Qualquer ação transacional sugerida pela IA na Camada 3 requer autorização humana explícita (*Human-in-the-Loop*) e gera um **Action Voucher** assinado criptograficamente (`action_id` / `tool_call_id`), despachado via gateway auditado, prevenindo escrita cega e Agência Excessiva (OWASP LLM03).
4. **Compatibilidade Zero-Bundler no Frontend:** A interface web da AURA é uma Single-Page Application sem webpack, vite ou rollup (`web/index.html` carrega scripts nativos via tag `<script>`). Todos os módulos GenUI devem adotar o padrão global de namespace no navegador (`window.AuraGenUI` / `window.SecureComponentRegistry`) com export condicional CommonJS (`typeof module !== 'undefined'`) para suporte a testes headless em Node.js.
5. **Resiliência a Quedas e Baixa Conectividade (Edge Offline-Ready):** Se a conexão do posto oscilar ou alternar para link de backup 4G, os componentes GenUI devem manter funcionamento local com **Optimistic UI**, fila de sincronização (*Outbox Pattern*) e reversão graciosa (*Rollback*) em caso de timeout.

---

## 2. Diagnóstico da Stack Atual vs. Arquitetura Alvo

| Componente Arquitetural | Estado Atual (Baseline AURA) | Estado Alvo (GenUI / SDUI Alinhado ao Documento) | Impacto Técnico & Risco |
| :--- | :--- | :--- | :--- |
| **Protocolo de Streaming** | SSE em `/api/v1/aura/chat` emitindo eventos `delta`, `intent`, `tool_start`, `tool_result`, `telemetry`, `done`. | SSE multiplexado com suporte formal a `ui_skeleton`, `ui_delta`, `ui_complete` e `ui_action_feedback`. | Zero quebra: novos eventos são complementares; clientes legados ignoram eventos desconhecidos. |
| **Contratos de Saída** | Modelos Pydantic em `core/schemas/` (`TankForecastContract`, etc.) retornados em bloco dentro de `contrato`. | Envelope canônico `GenUIEnvelope` (Pydantic v2) encapsulando metadados de ciclo de vida, idempotência, 3 camadas e props tipadas. | Padronização universal em todos os 6 módulos analíticos. |
| **Arquitetura Frontend** | SPA Vanilla JS sem bundler (`web/js/aura-*.js`). DecisionCards em HTML concatenado dentro de `aura-chat.js`. | Catálogo de Componentes Fechado (`window.SecureComponentRegistry`) com ciclo de vida orientado a objetos (Mount, Hydrate, StateLock, Rollback). | Isolamento estrito contra OWASP LLM03 (Agência Excessiva) e eliminação de XSS. |
| **Estrutura Visual** | Cards estáticos com cabeçalho, tabela analítica e botões simples de atalho. | **Micro-Widget em 3 Camadas Concêntricas:**<br>1. Resumo Executivo (TTFT rápido)<br>2. Visualização Rica (Gauges SVG)<br>3. Action Sheet Transacional. | Aumento imediato do valor de produto e eficiência cognitiva do operador. |
| **Gestão de Estado** | Estado append-only no chat. Botões antigos no histórico permanecem habilitados indefinidamente. | **AuraStateManager Reativo:** Tabela hash de idempotência (`tool_call_id`), State Locking imediato no clique, TTL de expiração e Rollback em falhas. | Prevenção absoluta de pedidos ou conciliações duplicadas no ERP. |
| **Memória do Agente** | Histórico armazena textos de usuário e assistente. Ações de clique na interface não retroalimentam o LLM. | **Sincronização Bidirecional (Server-State vs Client-State):** Injeção de mensagem `role: 'tool'` com `tool_call_id` no histórico do `AuraEngine`. | Elimina amnésia contextual: o LLM sabe imediatamente se o operador já autorizou o pedido. |
| **Integração Workspace** | Companion Canvas (`aura-aux-panel.js`) e EvidenceDrawer ativados por chamada manual. | **GenUI Companion Bridge:** Todo micro-widget possui método nativo de projeção em tela dividida no desktop e slide-over no mobile. | Preserva a ergonomia desktop de tela dividida sem duplicar consultas ao banco. |

---

## 3. Pipeline de Orquestração em Dois Estágios (Dual-Stage Pipeline)

Um dos maiores desafios de arquitetura na fusão de LLMs com operações B2B críticas é conciliar a **natureza probabilística da IA** com a **necessidade de determinismo matemático absoluto**. 

Se o LLM for encarregado de calcular diretamente o volume restante de combustível ou a diferença contábil de um caixa, ele poderá sofrer alucinações numéricas com consequências desastrosas. Por outro lado, se a interface for 100% rígida, perde-se a maleabilidade conversacional da IA.

A solução da AURA é o **Pipeline de Orquestração em Dois Estágios**:

```
[Usuário no Chat: "Como estão os tanques hoje?"]
                     │
                     ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ ESTÁGIO 1: EXECUÇÃO DETERMINÍSTICA (ENGINE & TOOLS)         │
  │ 1. SemanticRouter classifica intenção ('previsao_tanques')  │
  │ 2. PostoTools.prever_esgotamento_tanques() roda no Python   │
  │ 3. Consulta SQL Read-Only no PostgreSQL local (5433)        │
  │ 4. Geração do Contrato Pydantic Oficial (TankForecast)      │
  └─────────────────────────────────────────────────────────────┘
                     │
                     ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ ESTÁGIO 2: ENVELOPAMENTO GENUI & SÍNTESE SEMÂNTICA          │
  │ 1. Backend monta o envelope: GenUIEnvelope                  │
  │    - tool_call_id: UUID v4 imutável                         │
  │    - props: Telemetria determinística oficial da ferramenta │
  │ 2. Backend envia chunk SSE: event: ui_skeleton              │
  │ 3. LLM (vLLM/Ollama) recebe dados e sintetiza:              │
  │    - Camada 1: Resumo Executivo -> stream event: delta      │
  │    - Camada 3: Parâmetros da Ação -> event: ui_complete     │
  └─────────────────────────────────────────────────────────────┘
                     │
                     ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ FRONTEND (CLIENT-STATE): RENDERIZAÇÃO & TRANSAÇÃO           │
  │ 1. Exibe Resumo Executivo em tempo real                     │
  │ 2. Hidrata TankForecastWidget nativo via Props              │
  │ 3. Operador clica em "Aprovar Pedido de Carreta"            │
  │ 4. State Lock imediato + Optimistic UI                      │
  │ 5. RPC POST /api/v1/aura/actions/execute                    │
  │ 6. Injeção de role: 'tool' no histórico do AuraEngine       │
  └─────────────────────────────────────────────────────────────┘
```

### Vantagens do Pipeline Dual:
- **Zero Alucinação Numérica:** Os litros, porcentagens e valores monetários exibidos no widget vêm 100% da consulta determinística ao ERP.
- **Latência Mínima de Primeira Resposta (TTFT):** O skeleton surge em < 100ms e os primeiros tokens do resumo executivo fluem enquanto a ferramenta finaliza os cálculos estruturados.
- **Separação Rígida de Responsabilidades:** O LLM atua como sintetizador e consultor estratégico; o código Python atua como autoridade contábil e volumétrica.

---

## 4. Anatomia do Micro-Widget GenUI no AURA (As 3 Camadas Concêntricas)

Todo componente interativo injetado no feed do chat da AURA respeita a arquitetura em **três camadas concêntricas e sequenciais**:

```
+──────────────────────────────────────────────────────────────────────────+
│ CAMADA 1: RESUMO EXECUTIVO TEXTUAL (TTFT Rápido via Streaming)           │
│ 🚨 Atenção: Tanque 001 (Gasolina Comum) atingirá nível crítico em 4.2h.  │
│    Ullage total disponível para descarga: 17.500 L (3 compartimentos).    │
+──────────────────────────────────────────────────────────────────────────+
│ CAMADA 2: VISUALIZAÇÃO RICA (Nativa, Hidratada via Props Determinísticas)│
│  [ Gauge SVG: 12.4% ]  [ Autonomia: 4.2h (15%) | 8.1h (0L) ]             │
│  [ Barra Volumétrica com marcador da reserva crítica de 15% ]            │
│  [ Tabela de Tanques com cores semânticas de acessibilidade WCAG ]       │
+──────────────────────────────────────────────────────────────────────────+
│ CAMADA 3: ACTION SHEET TRANSACIONAL (Affordance com Idempotência)        │
│  [⚡ Aprovar Pedido de Carreta (15.000 L)]   [🔍 Ver no Companion Canvas] │
│  Status: PROPOSED ──(clique)──> LOCKED ──(sucesso)──> VOUCHER EMITIDO   │
+──────────────────────────────────────────────────────────────────────────+
```

### Detalhamento das 3 Camadas:

#### Camada 1 — Resumo Executivo Textual (Âncora Cognitiva)
- **Mecanismo:** Emitido via streaming contínuo nos primeiros tokens (`AuraChunkType.DELTA`).
- **Objetivo:** Fornecer clareza situacional instantânea ao gestor antes que o widget visual pesado termine a renderização.
- **Copy Pattern:** `[Status/Alerta] + [Métrica-Chave com Unidade] + [Projeção Temporal / Impacto Imediato]`.

#### Camada 2 — Visualização Rica (Hidratação Nativa Determinística)
- **Mecanismo:** O frontend busca o construtor registrado no `SecureComponentRegistry` e injeta as propriedades estruturadas recebidas no evento `ui_complete`.
- **Independência Visual do LLM:** O LLM não envia tags HTML, CSS ou código Chart.js. Ele envia apenas o objeto de dados. O widget nativo aplica os gradientes da AURA (ciano neon `#00f2fe`, violeta `#9d4edd`, esmeralda `#10b981`, rubi `#ef4444`), fontes semânticas e acessibilidade WCAG 2.1 AA.
- **Economia Computacional no Edge:** Redução drástica de tokens de saída na GPU (economizando até 80% do tempo de geração).

#### Camada 3 — Action Sheets Transacionais (Affordances Idempotentes)
- **Mecanismo:** Controles interativos acoplados à decisão sugerida.
- **Classificação de Ações:**
  - **Ações Reversíveis (Baixo Risco):** `[Ver no Canvas ↗]`, `[Abrir Evidências 🔍]`, `[Exportar CSV 📄]`. Executadas localmente no cliente sem mutação de banco.
  - **Ações Irreversíveis / Financeiras (Alto Risco):** `[Aprovar Compra de Combustível]`, `[Homologar Fechamento de Caixa]`, `[Solicitar Aferição de Bico]`. Exigem estado provisório explícito (*"Proposto pela IA"*), confirmação do operador, bloqueio contra cliques concorrentes (*State Locking*) e emissão de comprovante auditável (*Action Voucher*).

#### A Ponte com o AURA Companion Canvas & EvidenceDrawer
Para usuários em Desktop com monitores widescreen (>= 768px), o AURA opera em modo **Dual Focus Workspace**:
- O micro-widget inline no chat mantém a visualização compacta executiva.
- Todo micro-widget implementa o método `.projectToCanvas()`, que projeta o relatório completo no painel lateral persistente (`window.auraAuxPanel.projectArtifact({ ... })`) sem abrir modais intrusivos e sem recarregar o chat.
- As abas de evidência do `EvidenceDrawer` (Resumo, Como foi calculado, Bicos/Pista, Caixas/PDV, Tanques/ANP) são alimentadas diretamente pelas propriedades da Camada 2.

---

## 5. Gestão de Estado, Idempotência & Resiliência Edge

### 5.1 Idempotência Criptográfica e State Locking
O maior risco operacional em interfaces B2B com LLM é a submissão acidental duplicada provocada por latência de rede ou cliques ansiosos do operador.

```
[Clique do Operador] 
       │
       ▼
1. State Lock Imediato no DOM:
   - Botão transiciona para pointer-events: none; opacity: 0.6;
   - Texto substitui para: "Processando autorização..." com spinner animado
       │
       ▼
2. Checagem no AuraStateManager local:
   - Verifica se action_id já consta no Set() de ações executadas
   - Se já constar: descarta silenciosamente (Prevenção de Duplo Clique)
       │
       ▼
3. Despacho RPC para o Backend:
   - POST /api/v1/aura/actions/execute com { tool_call_id, action_id, payload }
   - Backend valida unicidade do action_id na tabela de transações
```

### 5.2 Optimistic UI com Rollback Resiliente
Em postos de combustíveis remotos, a conectividade pode sofrer quedas momentâneas. O AURA aplica o padrão **Optimistic UI com Rollback Limpo**:

1. **Mutação Visual Instantânea:** Ao clicar em "Aprovar Pedido", o widget não espera a resposta de rede. Ele exibe imediatamente o badge `[✔ Pedido Autorizado - Transmitindo ao ERP...]`.
2. **Confirmação Assíncrona:** A requisição HTTP conclui com sucesso (status 200). O badge consolida: `[✔ Pedido Confirmado • Voucher #98412]`.
3. **Reversão em Caso de Erro (Rollback):** Se a requisição retornar timeout ou erro 500:
   - O widget remove o badge de sucesso de forma animada (sem recarregar o chat).
   - O botão de ação original é restaurado com o rótulo `[Tentar Novamente]`.
   - Um toast de erro não intrusivo informa: *"Falha na comunicação com o ERP. Nenhuma compra foi efetuada. Tente novamente."*

### 5.3 Detecção de Ações Expiradas (Stale Action TTL Guard)
No fluxo cronológico do chat, mensagens antigas permanecem visíveis ao rolar para cima. Se um gestor rolar para uma mensagem de 4 horas atrás e clicar em "Aprovar Compra de 15.000 L", o volume dos tanques pode ter mudado completamente.

**Regra de Expiração do AURA:**
- Toda proposta de ação carrega um `timestamp` de criação e um `ttl_seconds` (padrão: 900 segundos / 15 minutos).
- Ao renderizar uma sessão recuperada do histórico ou após o decurso do TTL, o widget desativa os botões irreversíveis e substitui por:
  `<span class="badge-expired">Proposta Expirada (Dados de telemetria desatualizados)</span>`
- O operador é instruído a fazer uma nova pergunta para obter a telemetria em tempo real.

### 5.4 Sincronização Bidirecional (Server-State vs Client-State)
A desconexão entre a interface visual do cliente e a memória do motor de IA gera **amnésia contextual**. Se o usuário autorizar uma compra no widget e perguntar em seguida *"Qual o status do pedido que acabei de fazer?"*, um LLM sem sincronização responderá que nenhum pedido existe.

**Mecanismo de Injeção no AURA:**
Assim que o backend valida o sucesso da ação no endpoint `/api/v1/aura/actions/execute`, ele injeta automaticamente uma mensagem estruturada na memória de sessão do `AuraEngine`:

```json
{
  "role": "tool",
  "tool_call_id": "call_c7a9e18b_412f",
  "name": "render_TankRunOutForecastUI",
  "content": {
    "action_id": "act_88b19a02",
    "status": "APPROVED",
    "timestamp": "2026-10-07T18:45:00Z",
    "litros_autorizados": 15000,
    "combustivel": "Diesel S10",
    "operador": "Gerente Carlos"
  }
}
```

Nas perguntas subsequentes da mesma sessão, os tokens de atenção do modelo incluem esta mensagem, permitindo que a IA reconheça a ação e ofereça respostas contextualmente coerentes.

---

## 6. Catálogo Canônico dos 6 Micro-Widgets Primários (Especificação de Contratos)

Abaixo está a especificação completa dos 6 micro-widgets que compõem o catálogo canônico da AURA IntelligentUI:

| Invocação Canônica (`tool_name`) | Nome do Componente no Cliente | Contrato Backend Vinculado | Visualização Rica (Camada 2) | Action Sheet Transacional (Camada 3) |
| :--- | :--- | :--- | :--- | :--- |
| **`render_TankRunOutForecastUI`** | `TankForecastWidget` | `TankForecastContract` | Gauges de nível, autonomia crítica (15%) vs run-out (0L), espaço livre para descarga em múltiplos de 5.000 L. | • `Aprovar Pedido de Carreta (15.000 L)`<br>• `Ver Detalhes dos Tanques no Canvas` |
| **`render_ShiftReconciliationUI`** | `ShiftReconciliationWidget` | `ShiftReconciliationContract` | Triangulação trilateral (Automação Companytec x Caixas PDV x Encerrantes físicos), quebra/sobra em R$. | • `Homologar Fechamento de Caixa`<br>• `Notificar Divergência de Turno`<br>• `Auditar no Canvas` |
| **`render_PumpPerformanceUI`** | `PumpPerformanceWidget` | `PumpPerformanceContract` | Ranking de frentistas por ticket médio, bicos com vazão lenta (<30 L/min), comparativo de produtividade. | • `Solicitar Aferição de Bico Lento`<br>• `Emitir Ordem de Manutenção`<br>• `Inspecionar Pista no Canvas` |
| **`render_LMCComplianceUI`** | `LMCComplianceWidget` | `LMCReportContract` | Régua visual de variação volumétrica ANP [-0.60% a +0.60%], status de conformidade da Portaria 26. | • `Validar Fechamento LMC do Dia`<br>• `Exportar Livro Digital ANP`<br>• `Inspecionar Livro no Canvas` |
| **`render_MarketBasketUI`** | `MarketBasketWidget` | `MarketBasketContract` | Cartões de top combos com Lift >= 2.0x, suporte e confiança, script prático sugerido para o operador de caixa. | • `Ativar Promoção no PDV`<br>• `Imprimir Script de Balcão`<br>• `Explorar Regras no Canvas` |
| **`render_StationHealthUI`** | `StationHealthWidget` | `StationStatus` | Latência dos bancos locais (5433 ERP, 5434 pgvector), status de conexões ativas, integridade de índices HNSW. | • `Forçar Sincronização de Dados`<br>• `Limpar Cache Semântico`<br>• `Diagnóstico de Rede` |

---

## 7. Segurança Cibernética, Governança & Human-in-the-Loop Gateway

### 7.1 Mitigação Estrita de OWASP LLM03 (Excessive Agency / Agência Excessiva)
- **Proibição Absoluta de Execução de Código Dinâmico:** O frontend **jamais** utiliza `eval()`, `new Function()` ou injeção de `<script>` para renderizar componentes.
- **Catálogo Fechado de Componentes (`SecureComponentRegistry`):** O modelo só pode escolher uma chave de componente pré-compilada no frontend. Se o LLM alucinar uma chave inexistente (e.g., `render_DeleteAllDatabasesUI`), o resolver de componentes rejeita imediatamente a invocação, registra um alerta de segurança e ativa o fallback textual seguro.
- **Isolamento de Escrita:** O modelo de IA não tem permissão direta de escrita nas tabelas do ERP. Toda transação é mediada por um botão na interface que requer o clique físico do operador.

### 7.2 Mitigação de OWASP LLM01 (Prompt Injection no Frontend)
- **Sanitização de Strings em Camadas Múltiplas:** Toda propriedade de texto renderizada em nós do DOM passa pela função nativa de escape `escapeHtml()`, neutralizando caracteres perigosos (`<`, `>`, `&`, `"`, `'`).
- **Coerção Estrita de Tipos:** Valores numéricos recebidos no JSON são convertidos explicitamente via `Number()` antes de serem inseridos em cálculos ou atributos de estilo, impedindo injeções de CSS malicioso.

### 7.3 Gateway de Ação Human-in-the-Loop & Voucher Transacional
Para atender ao princípio de **banco ERP somente-leitura** e ao mesmo tempo viabilizar fluxos transacionais modernos:
1. O clique no botão da Camada 3 dispara uma requisição para a rota interna da AURA: `POST /api/v1/aura/actions/execute`.
2. A AURA gera um **Action Voucher** contendo:
   - `voucher_id`: Identificador único (UUID v4).
   - `action_type`: Tipo da ação (e.g., `PEDIDO_CARRETA_COMBUSTIVEL`).
   - `payload`: Dados validados da transação.
   - `operator_id`: Usuário logado na sessão.
   - `signature`: Assinatura HMAC-SHA256 validando a integridade do voucher.
3. O voucher é persistido na tabela interna de auditoria `aura_transacoes_auditadas` e despachado para a fila de integração homologada do ERP ou webhook de supervisão.

---

## 8. Infraestrutura de Inferência Edge: vLLM & Guided Decoding

Para garantir que o motor de IA emita JSON rigorosamente aderente aos esquemas e com latência compatível com postos de combustíveis:

### 8.1 vLLM com Guided Decoding (Outlines / xgrammar)
Em servidores locais com GPU (RTX 4090 / RTX 3090 / A4000), o motor de produção da AURA deve operar com **vLLM** configurado com restrição gramatical baseada no JSON Schema do Pydantic:

```bash
# Inicialização do vLLM com Guided Decoding ativado
vllm serve Qwen/Qwen2.5-7B-Instruct \
  --host 127.0.0.1 \
  --port 8000 \
  --guided-decoding-backend outlines \
  --gpu-memory-utilization 0.85 \
  --max-model-len 8192
```

O backend da AURA compila o schema Pydantic `GenUIEnvelope.model_json_schema()` e injeta o parâmetro `guided_json` nas chamadas ao vLLM. O mecanismo de **token masking** mascara os logits nos passos de decodificação, tornando matematicamente impossível a geração de JSON com sintaxe quebrada ou campos fora do esquema.

### 8.2 Fallback Gracioso para Ollama & Ambientes com CPU
Em filiais que utilizam Ollama local (`ollama run qwen2.5:7b`):
- O backend solicita formato JSON via `format: "json"`.
- Um módulo resiliente de reparo (`json_repair`) intercepta o buffer de saída caso uma chave termine truncada por estouro de contexto, garantindo que o frontend nunca receba uma string inválida.

---

## 9. Plano de Implementação em Fases e Marcos (Fase 0 a Fase 9)

O plano de entrega está dividido em 10 fases incrementais (Fase 0 a Fase 9), priorizadas de P0 a P2, desenhadas para execução cirúrgica com verificação contínua e **zero risco de quebra dos fluxos existentes**.

```
[F0: Baseline & Registry] ──> [F1: Backend SSE & Envelopes] ──> [F2: Frontend Streaming & Skeleton]
                                                                          │
[F5: Sincronização Bidirecional] <── [F4: State Lock & Optimistic] <── [F3: Piloto TankForecastUI]
               │
               ▼
[F6: Expansão do Catálogo] ────────> [F7: Hardening & OWASP] ────────> [F8: Testes Automatizados E2E]
                                                                          │
                                                                          ▼
                                                                [F9: Rollout & Flags]
```

---

### Fase 0 — Inventário, Baseline & Arquitetura do Protocolo GenUI (P0)
**Objetivo:** Estabelecer o contrato formal do protocolo GenUI, configurar os identificadores de rastreabilidade e isolar o ambiente sem tocar nas rotas ativas de produção.

- [ ] **F0-01 — Especificação Formal do Protocolo de Streaming GenUI:**  
  Documentar os tipos canônicos de chunks SSE: `delta` (texto puro), `ui_skeleton` (ativação do skeleton no cliente), `ui_delta` (fragmentos parciais de JSON da ferramenta), `ui_complete` (payload final tipado e validado) e `ui_action_feedback` (retorno de ações executadas).
- [ ] **F0-02 — Criação do Registro Centralizado de Componentes no Frontend (`web/js/aura-genui.js`):**  
  Estruturar `window.SecureComponentRegistry` com suporte dual (global `window` no browser e `module.exports` para testes headless no Node.js). Nenhuma tag arbitrária gerada por IA terá autorização para instanciar elementos fora deste catálogo (mitigação de OWASP LLM03).
- [ ] **F0-03 — Padronização de IDs de Idempotência Criptográfica:**  
  Garantir que toda requisição e todo bloco de resposta estruturado possua um UUID canônico (`tool_call_id` no backend e `action_id` para cada ação proposta no payload).
- [ ] **F0-04 — Criação do Módulo de Testes de Linha de Base:**  
  Criar o script `scripts/test_genui_baseline.py` para verificar a integridade dos contratos atuais antes de qualquer modificação.

**Critério de Aceite da Fase 0:**  
- Contratos de protocolo documentados e revisados.
- `SecureComponentRegistry` declarado e acessível em `window.SecureComponentRegistry`.
- Todos os testes de linha de base passando com 100% de sucesso.

---

### Fase 1 — Backend: Protocolo SSE Multiplexado & Envelopes Tipados (P0)
**Objetivo:** Evoluir `core/aura_api.py` e `core/aura_engine.py` para emitir o fluxo de streaming em duas etapas bem demarcadas (Resumo Executivo inicial seguido de Structured Output encapsulado em envelope GenUI).

- [ ] **F1-01 — Extensão do Modelo `AuraChunkType` em `core/aura_engine.py`:**  
  Adicionar os novos tipos de chunks no Enum:
  ```python
  class AuraChunkType(str, Enum):
      DELTA = "delta"                      # Texto puro em streaming (Resumo Executivo)
      INTENT = "intent"                    # Intenção classificada
      UI_SKELETON = "ui_skeleton"          # Sinal para exibir esqueleto do widget
      UI_DELTA = "ui_delta"                # Fragmentos fracionados de JSON de props
      UI_COMPLETE = "ui_complete"          # Payload completo e validado da ferramenta
      UI_ACTION_RESULT = "ui_action_result"# Confirmação de ação transacional executada
      CACHE_HIT = "cache_hit"              # Cache vetorial
      TELEMETRY = "telemetry"              # Métricas de latência SRE
      ERROR = "error"                      # Notificação de falha
      DONE = "done"                        # Finalização do stream
  ```
- [ ] **F1-02 — Envelope Pydantic Canônico para Componentes GenUI (`core/schemas/genui.py`):**  
  Criar schema unificado com metadados de ciclo de vida e idempotência:
  ```python
  class GenUIActionOption(BaseModel):
      model_config = ConfigDict(frozen=True)
      action_id: str = Field(..., description="UUID único da ação transacional")
      label: str = Field(..., description="Rótulo visual do botão")
      action_type: Literal["mutation", "inspection", "navigation"] = "mutation"
      variant: Literal["primary", "secondary", "danger", "ghost"] = "primary"
      is_destructive: bool = False
      requires_confirmation: bool = True
      payload: Dict[str, Any] = Field(default_factory=dict)

  class GenUIEnvelope(BaseModel):
      model_config = ConfigDict(frozen=True)
      schema_version: str = Field(default="1.0")
      tool_call_id: str = Field(..., description="UUID da invocação gerada pelo backend")
      component_name: str = Field(..., description="Nome no SecureComponentRegistry")
      intent: str = Field(..., description="Intenção canônica (ex: tank_forecast)")
      executive_summary: str = Field(..., description="Camada 1: Resumo Executivo")
      props: Dict[str, Any] = Field(..., description="Camada 2: Propriedades puras do widget")
      actions: List[GenUIActionOption] = Field(default_factory=list, description="Camada 3: Action Sheets")
  ```
- [ ] **F1-03 — Ajuste do Gerador de Streaming no `AuraEngine.ask_stream()`:**  
  Ao processar uma pergunta com intenção analítica identificada:
  1. Emitir `ui_skeleton` com o nome do componente a ser renderizado e o texto contextual ("Consultando volumetria dos tanques...").
  2. Emitir tokens textuais do Resumo Executivo (`DELTA`) enquanto a ferramenta finaliza os cálculos.
  3. Emitir o evento `ui_complete` contendo a serialização do `GenUIEnvelope`.
  4. Finalizar com `DONE`.
- [ ] **F1-04 — Suíte de Testes Automatizada do Backend (`scripts/test_genui_engine_sse.py`):**  
  Validar a ordem cronológica estrita de emissão dos chunks, sem quebra de formato SSE.

**Critério de Aceite da Fase 1:**  
- O endpoint `/api/v1/aura/chat` transmite SSE compatível com clientes legados e com o novo protocolo GenUI.
- Nenhum token de JSON vaza como texto comum no chat.
- Teste `test_genui_engine_sse.py` aprovado com 100% de sucesso.

---

### Fase 2 — Frontend: Streaming Parser, Bufferização JSON & Skeleton UI (P0)
**Objetivo:** Evoluir `web/js/aura-api.js` e `web/js/aura-chat.js` para consumir o fluxo multiplexado, gerenciar buffer seguro de JSON e exibir skeletons com micro-copy contextual.

- [ ] **F2-01 — Refatoração da Máquina de Estados de Streaming em `web/js/aura-api.js`:**  
  Garantir que eventos SSE multiplexados (`event: ui_skeleton`, `event: ui_delta`, `event: ui_complete`) sejam despachados para callbacks específicos sem atrasar a renderização dos tokens textuais de Resumo Executivo (`event: delta`).
- [ ] **F2-02 — Implementação do Buffer de Fragmentos JSON com Fallback Gracioso:**  
  No cliente, caso a inferência transmita deltas fracionados de JSON (`ui_delta`), acumular em string buffer local em memória volátil com tratamento `try-catch` que silencia erros parciais de sintaxe até o evento `ui_complete` ou `[DONE]`.
- [ ] **F2-03 — Injeção de Skeleton UI Reativo (`SkeletonPulse`):**  
  No exato momento em que `ui_skeleton` é interceptado, alocar no DOM do chat um bloco visual com animação pulsante sutil (`animate-pulse`) e texto explicativo da etapa em execução:
  ```html
  <div class="genui-skeleton-slot p-4 rounded-xl border border-cyan-500/20 bg-slate-900/60 backdrop-blur-md">
    <div class="flex items-center gap-3">
      <div class="w-3 h-3 rounded-full bg-cyan-400 animate-ping"></div>
      <span class="text-xs font-mono text-cyan-300 tracking-wide uppercase">
        Aura Engine: Processando volumetria dos tanques...
      </span>
    </div>
    <div class="mt-3 space-y-2">
      <div class="h-4 bg-slate-800/80 rounded w-3/4 animate-pulse"></div>
      <div class="h-8 bg-slate-800/60 rounded w-full animate-pulse"></div>
    </div>
  </div>
  ```
- [ ] **F2-04 — Hidratação Instantânea sem Layout Jank:**  
  Assim que `ui_complete` é recebido, validar as propriedades contra o contrato esperado, destruir o esqueleto do DOM e injetar o micro-widget com transição de opacidade suave (150ms).

**Critério de Aceite da Fase 2:**  
- Transição visual contínua: Resumo Executivo datilografado -> Skeleton ativo -> Widget hidratado.
- Zero quebra de layout (*Zero Cumulative Layout Shift* - CLS).
- Teste em Node.js simulando chunks SSE com atraso artificial comprovando montagem correta.

---

### Fase 3 — Micro-Widget Piloto em 3 Camadas: `TankRunOutForecastUI` (P0)
**Objetivo:** Construir a primeira implementação completa fim-a-fim da arquitetura GenUI para o fluxo crítico de **Previsão de Esgotamento de Tanques e Pedido de Carreta**.

- [ ] **F3-01 — Componente `TankForecastWidget` no `SecureComponentRegistry`:**  
  Implementar a classe de componente no frontend em `web/js/genui/tank-widget.js`:
  ```javascript
  class TankForecastWidget {
    constructor(payload) {
      this.toolCallId = payload.tool_call_id;
      this.summary = payload.executive_summary;
      this.props = payload.props;
      this.actions = payload.actions || [];
      this.state = { status: 'proposed', isLocked: false };
      this.eventListeners = {};
    }
    mount() { /* Constrói as 3 camadas em elementos DOM puros */ }
    renderLayer1() { /* Resumo Executivo com badge de urgência */ }
    renderLayer2() { /* Gauges de nível, autonomia 15% vs 0L, espaço livre */ }
    renderLayer3() { /* Action Sheet: Botão de aprovação de carreta */ }
    applyOptimisticState(newState) { /* Trava o botão e exibe badge otimista */ }
    rollbackOptimisticState(errorMsg) { /* Restaura estado e exibe erro */ }
    projectToCanvas() { /* Despacha visualização para window.auraAuxPanel */ }
  }
  ```
- [ ] **F3-02 — Construção da Visualização Rica (Camada 2):**  
  Renderizar medidores visuais de combustível com gradientes semânticos (vermelho para estoque <15%, amarelo para atenção, verde para estável) e cálculo do espaço livre para descarga em compartimentos de 5.000 L.
- [ ] **F3-03 — Construção da Action Sheet Transacional (Camada 3):**  
  Implementar o botão `⚡ Aprovar Pedido de Carreta (15.000 L)` com dados pré-parametrizados e indicação de status `Proposta pela IA (Requer Confirmação)`.
- [ ] **F3-04 — Projeção Paralela no Companion Canvas:**  
  Ao renderizar o widget inline no chat, sincronizar automaticamente a projeção detalhada para o painel auxiliar (`window.auraAuxPanel.projectArtifact`), permitindo inspeção profunda em tela dividida no PC sem perder o foco do diálogo.

**Critério de Aceite da Fase 3:**  
- Pergunta *"Qual a previsão dos tanques?"* renderiza o Resumo, o widget com gauges e a Action Sheet.
- Componente 100% responsivo (Compact Card no Mobile e Dual Workspace no Desktop).
- Verificação funcional com dados reais do banco PostgreSQL do posto.

---

### Fase 4 — Motor de Gestão de Estado no Cliente, Idempotência & Optimistic UI (P1)
**Objetivo:** Implementar o gerenciador de estado reativo no cliente (`AuraStateManager`) para garantir idempotência, bloqueio contra cliques duplicados, persistência local e rollback limpo.

- [ ] **F4-01 — Criação do `AuraStateManager` (`web/js/aura-state-manager.js`):**  
  Gerenciador central com tabela hash de estados indexada por `tool_call_id` e persistência de curto prazo em `sessionStorage`:
  ```javascript
  class AuraStateManager {
    constructor() {
      this.widgets = new Map(); // tool_call_id -> { state, locked, timestamp }
      this.executedActions = new Set(); // action_id
      this.loadFromSessionStorage();
    }
    registerWidget(toolCallId, initialProps) { ... }
    lockWidget(toolCallId, actionId) { ... }
    unlockWidget(toolCallId) { ... }
    isActionExecuted(actionId) { return this.executedActions.has(actionId); }
    markActionExecuted(actionId) { 
      this.executedActions.add(actionId);
      this.persistToSessionStorage();
    }
    isStale(timestamp, ttlSeconds = 900) {
      return (Date.now() - timestamp) > (ttlSeconds * 1000);
    }
  }
  ```
- [ ] **F4-02 — State Locking Imediato contra Duplo Clique:**  
  No evento de clique da Action Sheet:
  1. Verificar se `action_id` já foi executado. Se sim, ignorar o evento.
  2. Mudar a classe CSS do botão para `opacity-50 pointer-events-none cursor-not-allowed`.
  3. Substituir o texto do botão por um badge animado: `<span class="animate-pulse">Emitindo pedido no ERP...</span>`.
- [ ] **F4-03 — Fluxo Otimista com Rollback Resiliente:**  
  ```javascript
  widget.applyOptimisticState({ status: 'approved', locked: true });
  try {
    const result = await window.auraApi.executeAction(actionId, widget.props);
    AuraStateManager.markActionExecuted(actionId);
    widget.finalizeSuccessState(result);
  } catch (err) {
    widget.rollbackOptimisticState();
    window.auraFx.showToast({
      title: 'Falha na Operação',
      message: 'Não foi possível comunicar com o ERP central. Tente novamente.',
      type: 'error'
    });
  }
  ```
- [ ] **F4-04 — Expiração de Ações no Histórico do Chat:**  
  Ao carregar conversas anteriores ou após nova interação do usuário, transicionar botões de widgets antigos para o estado `Expirado` caso o timestamp da ação tenha ultrapassado o limite de validade operacional (TTL padrão: 15 minutos).

**Critério de Aceite da Fase 4:**  
- Cliques múltiplos no mesmo botão geram apenas uma única chamada de rede.
- Simulação de erro 500 ou queda de conexão reverte o estado do botão instantaneamente com feedback visual claro.
- Suíte de testes em Node.js cobrindo o ciclo de vida completo de mutação e rollback.

---

### Fase 5 — Sincronização Bidirecional (Server-State vs. Client-State) & Memória do Agente (P1)
**Objetivo:** Conectar as mutações de interface no cliente de volta ao cérebro do agente (`Server-State`), eliminando a amnésia contextual da IA.

- [ ] **F5-01 — Endpoint de Execução de Ações Transacionais:**  
  Criar a rota `POST /api/v1/aura/actions/execute` em `core/aura_api.py`:
  - Recebe `session_id`, `tool_call_id`, `action_id`, `action_name` e `payload`.
  - Valida a idempotência no banco de dados / cache de transações em memória.
  - Executa a rotina de negócio autorizada em `core/tools.py`.
  - Retorna comprovante estruturado da transação (Voucher).
- [ ] **F5-02 — Injeção de `tool_result` no Histórico do `AuraEngine`:**  
  Ao concluir a ação no endpoint, injetar diretamente no histórico da sessão uma mensagem com formato canônico:
  ```json
  {
    "role": "tool",
    "tool_call_id": "c7a9e18b-...",
    "name": "render_TankRunOutForecastUI",
    "content": "{\"status\": \"APPROVED\", \"action_id\": \"...\", \"litros\": 15000, \"fornecedor\": \"Distribuidora Oficial\", \"executado_por\": \"operador_01\"}"
  }
  ```
- [ ] **F5-03 — Teste de Consistência Contextual Subsequente:**  
  Testar pergunta seguinte do usuário (e.g., *"Qual o status daquele pedido de combustível?"*): o modelo de linguagem deve responder categoricamente que o pedido de 15.000 L já foi submetido com sucesso, sem recalcular a sugestão como pendente.

**Critério de Aceite da Fase 5:**  
- Ação executada na interface atualiza imediatamente o histórico do motor de IA.
- Nenhuma duplicidade de recomendação ocorre em interações consecutivas.
- Teste automatizado validando a integridade da memória do agente em sessão de múltiplos turnos.

---

### Fase 6 — Expansão do Catálogo de Micro-Widgets Inteligentes (P2)
**Objetivo:** Migrar os demais módulos analíticos da AURA para o padrão GenUI de 3 camadas com Action Sheets.

- [ ] **F6-01 — Micro-Widget `ShiftReconciliationUI` (Auditoria de Turno & Caixa):**  
  - **Camada 1:** Resumo Executivo informando status de conciliação e divergência apurada em R$.
  - **Camada 2:** Matriz comparativa entre valores de encerrantes de bico, caixas PDV e cartões.
  - **Camada 3:** Action Sheet com botões: `Homologar Fechamento de Caixa` e `Exportar Relatório Fiscal`.
- [ ] **F6-02 — Micro-Widget `PumpPerformanceUI` (Vazão de Bicos & Frentistas):**  
  - **Camada 1:** Diagnóstico da pista (média de vazão L/min e bicos com alerta metrológico).
  - **Camada 2:** Gráfico comparativo de vazão e tabela de desempenho da equipe de pista.
  - **Camada 3:** Action Sheet: `Solicitar Aferição de Bico Lento (<30 L/min)` e `Imprimir Escala`.
- [ ] **F6-03 — Micro-Widget `LMCComplianceUI` (Auditoria ANP Portaria 26):**  
  - **Camada 1:** Síntese de conformidade do Livro de Movimentação de Combustíveis do dia.
  - **Camada 2:** Régua visual da tolerância legal de variação física [-0.60% a +0.60%].
  - **Camada 3:** Action Sheet: `Validar Livro Digital ANP` e `Auditar Tanques com Variação`.
- [ ] **F6-04 — Micro-Widget `MarketBasketUI` (Combos & Conveniência):**  
  - **Camada 1:** Oportunidades de vendas cruzadas com alto coeficiente de Lift.
  - **Camada 2:** Cartões dos top combos com métricas de Suporte, Confiança e Ticket Médio Adicional.
  - **Camada 3:** Action Sheet: `Ativar Sugestão no PDV` e `Imprimir Script de Balcão`.
- [ ] **F6-05 — Micro-Widget `StationHealthUI` (Status de Conexão e Borda):**  
  - **Camada 1:** Resumo de saúde operacional da filial do posto.
  - **Camada 2:** Latência de ping do ERP local (5433) e do banco pgvector (5434).
  - **Camada 3:** Action Sheet: `Forçar Reconexão de Banco` e `Limpar Cache Semântico`.

**Critério de Aceite da Fase 6:**  
- Todos os 6 módulos possuem renderizadores nativos padronizados registrados no `SecureComponentRegistry`.
- A estética de design segue com perfeição o tema AURA Precision Glass.

---

### Fase 7 — Hardening de Segurança Cibernética, OWASP LLM & Governança (P0/P1)
**Objetivo:** Blindar o sistema contra as principais vulnerabilidades de sistemas de IA generativa em ambientes industriais B2B.

- [ ] **F7-01 — Mitigação Estrita de OWASP LLM03 (Excessive Agency):**  
  - Proibição absoluta de execução de código JavaScript vindo do LLM (sem `eval`, sem `new Function`, sem injeção de `<script>`).
  - O LLM apenas escolhe a chave do catálogo (`component_name`) e fornece parâmetros tipados.
  - Qualquer chave não registrada dispara fallback seguro imediato para visualização de texto bruto sanitizado.
- [ ] **F7-02 — Mitigação de OWASP LLM01 (Prompt Injection no Frontend):**  
  - Todas as propriedades textuais injetadas em nós de texto passam por sanitização via `escapeHtml()`.
  - Campos numéricos e booleanos são forçados aos seus tipos primitivos no momento da desserialização no cliente.
- [ ] **F7-03 — Governança de Autorização de Operador:**  
  - Ações transacionais na Camada 3 verificam o perfil de permissões do operador logado (e.g., Frentista pode apenas visualizar; Gerente pode autorizar compra de combustível).
- [ ] **F7-04 — Trilha de Auditoria Transacional (Audit Log):**  
  - Toda ação disparada registra evento detalhado no banco de dados com timestamp, identificador do posto, usuário, `tool_call_id` e resposta do ERP.

**Critério de Aceite da Fase 7:**  
- Tentativa de injeção de payload com tags HTML maliciosas é completamente neutralizada.
- Requisições a ferramentas inexistentes são bloqueadas com log de segurança.
- Trilha de auditoria operacional gravando eventos transacionais.

---

### Fase 8 — Qualidade, Suíte de Testes Automatizados & Validação Fim-a-Fim (P0)
**Objetivo:** Provar o funcionamento do sistema completo através de testes de execução reais no backend e no frontend, com zero regressão.

- [ ] **F8-01 — Suíte de Testes de Contratos GenUI (`scripts/test_genui_contracts.py`):**  
  Validar a serialização, validação Pydantic e robustez dos schemas de envelope GenUI.
- [ ] **F8-02 — Suíte de Testes de Streaming e Bufferização (`scripts/test_genui_streaming.py`):**  
  Simular transmissão SSE com chunks fracionados e verificar se o parser acumula e hidrata sem exceções.
- [ ] **F8-03 — Suíte de Testes de Ciclo de Vida Frontend via Node.js (`scripts/test_genui_frontend_lifecycle.py`):**  
  Testar programaticamente via script headless:
  1. Instanciação de todos os 6 componentes do catálogo.
  2. Transição de Skeleton para Componente Hidratado.
  3. Disparo de evento de clique e ativação imediata do State Lock.
  4. Execução otimista e reversão (Rollback) simulando falha de rede.
  5. Neutralização de XSS em strings de props.
- [ ] **F8-04 — Teste de Não-Regressão Geral da AURA:**  
  Executar suítes já existentes (`test_aura_aux_panel.py`, `test_phase5_specialized_responses.py`, `test_phase6_quality_resilience.py`, `test_aura_engine.py`) comprovando 100% de aprovação.

**Critério de Aceite da Fase 8:**  
- 100% de aprovação em todos os testes novos e testes legados.
- Relatório de testes gerado com métricas de tempo de execução.

---

### Fase 9 — Rollout Gradual, Feature Flags & Observabilidade SRE (P2)
**Objetivo:** Publicar a nova experiência com controle total de reversão e telemetria de produção.

- [ ] **F9-01 — Feature Flag `ENABLE_GENUI`:**  
  Permitir ligar/desligar a experiência GenUI dinamicamente via query param (`?genui=1`), flag de configuração no `.env` ou seletor no cockpit.
- [ ] **F9-02 — Telemetria de Desempenho e UX:**  
  Monitorar no backend e frontend:
  - TTFT (Time-to-First-Token) do Resumo Executivo.
  - Tempo de hidratação do micro-widget (ms entre `ui_skeleton` e `ui_complete`).
  - Taxa de sucesso de ações transacionais vs taxa de rollback.
- [ ] **F9-03 — Procedimento de Contingência e Rollback Imediato:**  
  Caso qualquer inconsistência seja detectada em campo, comutar a flag para `false`: o sistema retorna imediatamente para os DecisionCards clássicos sem necessidade de restart de container.

---

## 10. Matriz de Esforço, Dependências e Cronograma Sugerido

| Fase | Título | Prioridade | Dependências | Esforço Estimado |
| :--- | :--- | :--- | :--- | :--- |
| **Fase 0** | Inventário, Baseline & Arquitetura do Protocolo | **P0** | Nenhuma | 1–2 dias |
| **Fase 1** | Backend: Protocolo SSE Multiplexado & Envelopes | **P0** | Fase 0 | 2–3 dias |
| **Fase 2** | Frontend: Streaming Parser, Buffer & Skeleton UI | **P0** | Fase 1 | 2–3 dias |
| **Fase 3** | Micro-Widget Piloto: `TankRunOutForecastUI` | **P0** | Fase 1, Fase 2 | 2–4 dias |
| **Fase 4** | Gestão de Estado, Idempotência & Optimistic UI | **P1** | Fase 3 | 2–3 dias |
| **Fase 5** | Sincronização Bidirecional & Memória do Agente | **P1** | Fase 4 | 2–3 dias |
| **Fase 6** | Expansão do Catálogo de Micro-Widgets | **P2** | Fase 3, Fase 4 | 3–5 dias |
| **Fase 7** | Hardening de Segurança Cibernética & OWASP | **P0/P1** | Fase 5, Fase 6 | 2–3 dias |
| **Fase 8** | Qualidade, Testes Automatizados & Validação E2E | **P0** | Contínuo desde F1 | 2–3 dias finais |
| **Fase 9** | Rollout Gradual, Feature Flags & Observabilidade | **P2** | Fase 8 | 1–2 dias |

- **Total de Esforço Estimado:** 19 a 31 dias úteis para entrega completa com grau industrial de robustez.  
- **Menor Entrega Utilizável (MVP GenUI):** Fases 0, 1, 2, 3 e 4 (Piloto de Tanques funcional com streaming, skeleton, widget de 3 camadas e state locking) em **9 a 15 dias**.

---

## 11. Contratos de Dados e Blueprint Técnico de Referência

### 11.1 Schema Pydantic do Envelope GenUI (Backend)
```python
# core/schemas/genui.py
from __future__ import annotations
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class GenUIActionOption(BaseModel):
    """Opção de ação transacional na Camada 3 de um micro-widget GenUI."""
    model_config = ConfigDict(frozen=True)

    action_id: str = Field(..., description="UUID único da ação transacional (Transaction Guard)")
    label: str = Field(..., description="Rótulo visual do botão")
    action_type: Literal["mutation", "inspection", "navigation"] = "mutation"
    variant: Literal["primary", "secondary", "danger", "ghost"] = "primary"
    is_destructive: bool = False
    requires_confirmation: bool = True
    payload: Dict[str, Any] = Field(default_factory=dict, description="Parâmetros pré-computados para o RPC")


class GenUIEnvelope(BaseModel):
    """Envelope canônico de entrega de micro-widgets GenUI sobre SSE."""
    model_config = ConfigDict(frozen=True)

    schema_version: str = Field(default="1.0", description="Versão do contrato GenUI")
    tool_call_id: str = Field(..., description="UUID único da chamada da ferramenta")
    component_name: str = Field(..., description="Nome do componente no SecureComponentRegistry")
    intent: str = Field(..., description="Intenção canônica (ex: tank_forecast, shift_reconciliation)")
    executive_summary: str = Field(..., description="Camada 1: Resumo Executivo emitido no streaming")
    props: Dict[str, Any] = Field(..., description="Camada 2: Dados e telemetria pura para o widget nativo")
    actions: List[GenUIActionOption] = Field(default_factory=list, description="Camada 3: Action Sheets")
```

### 11.2 Interceptador no Frontend (`SecureComponentRegistry`)
```javascript
// web/js/aura-genui.js
/**
 * AURA IntelligentUI - Secure Component Registry
 * Padrão Zero-Bundler compatível com script nativo no navegador (window) 
 * e export CommonJS para testes automatizados headless via Node.js.
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) {
    // Ambiente Node.js (Suítes de Teste)
    module.exports = factory();
  } else {
    // Ambiente Browser (Navegador do Posto)
    root.AuraGenUI = factory();
    root.SecureComponentRegistry = root.AuraGenUI.SecureComponentRegistry;
  }
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const registry = {};

  function registerComponent(name, componentClass) {
    if (typeof name !== 'string' || !name.trim()) {
      throw new Error('[GenUI] Nome de componente inválido.');
    }
    if (typeof componentClass !== 'function') {
      throw new Error('[GenUI] Construtor de componente deve ser uma classe ou função.');
    }
    registry[name] = componentClass;
  }

  function resolveComponent(name) {
    const ComponentClass = registry[name];
    if (!ComponentClass) {
      console.warn(`[GenUI Security Alert] Componente não autorizado no catálogo: ${name}`);
      return null;
    }
    return ComponentClass;
  }

  return {
    SecureComponentRegistry: registry,
    registerComponent,
    resolveComponent
  };
});
```

---

## 12. Matriz de Riscos & Planos de Mitigação

| Risco Técnico Identificado | Severidade | Probabilidade | Mitigação Arquitetural Implementada |
| :--- | :--- | :--- | :--- |
| **Fragmentos JSON Corrompidos durante Streaming** | Alta | Média | Parser no cliente com try-catch silencioso durante o delta; validação estrita contra o schema apenas no evento de fechamento `ui_complete`. |
| **Cliques Duplicados em Ações Financeiras** | Crítica | Alta | `State Locking` imediato no DOM no primeiro clique (`pointer-events: none`); validação de idempotência no backend via tabela de `action_id`. |
| **Falha de Rede pós-Ação Otimista (Desconexão no Posto)** | Alta | Média | `Optimistic UI com Rollback`: restauração do botão, exibição de toast não-intrusivo de erro e opção de repetição. |
| **Amnésia do Agente após Ação no Frontend** | Média | Alta | Sincronização bidirecional: injeção de evento canônico `role: 'tool'` no histórico do `AuraEngine` após confirmação do RPC. |
| **Agência Excessiva (Injeção de Widgets Não-Autorizados)** | Crítica | Baixa | Catálogo fechado (`SecureComponentRegistry`). Qualquer nome fora do registro é bloqueado e registrado no log de segurança. |
| **Regressão na Exibição dos DecisionCards Legados** | Média | Baixa | Modo de coexistência com `Feature Flag` e fallback para `renderToolInlineWidget` caso o payload não seja um envelope GenUI. |

---

## 13. Conclusão e Próximos Passos Imediatos

A implementação da arquitetura **GenUI e Server-Driven UI no AURA** eleva a plataforma da condição de mero assistente conversacional para a de **cockpit transacional inteligente no Edge**. Ao combinar **determinismo numérico rígido**, **segurança contra OWASP LLM03**, **resiliência contra cliques duplicados** e **micro-widgets nativos em 3 camadas**, a AURA entrega uma experiência sob demanda, veloz, esteticamente impecável e acionável diretamente no posto.

### Ação Imediata Recomendada:
1. **Aprovação do Roadmap:** Validação deste documento pela liderança técnica.
2. **Início da Fase 0 & Fase 1:** Criação do módulo `core/schemas/genui.py` e extensão dos tipos em `AuraChunkType`.
3. **Construção do Piloto na Fase 2 & Fase 3:** Prova de conceito completa com `TankRunOutForecastUI` para validação em ambiente real.
