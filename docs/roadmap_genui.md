# Roadmap Executivo & Técnico: Implementação de GenUI & Server-Driven UI no AURA Edge AI

> **AURA IntelligentUI (GenUI/SDUI v1.0) — O Mentor de Decisões Executivo no Edge:** Transformando a AURA de um leitor passivo de relatórios ou medidor de telemetria em um **verdadeiro mentor de negócios especialista em análises profundas, previsões preditivas, consultas multidimensionais e comparações estratégicas para tomadas de decisão assertivas**.

- **Data de Criação:** 07/10/2026  
- **Versão do Documento:** 2.3.0 (Evolução Estratégica: Hardening de Seguranca Cibernetica & Governanca RBAC)  
- **Status:** Fases 0, 1, 2, 3, 4, 5, 6 e 7 Concluidas (P0 e P1 Homologados) | Fase 8 em Planejamento  
- **Documento de Referência Arquitetural:** [`docs/Arquitetura GenUI para Edge AI.md`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/docs/Arquitetura%20GenUI%20para%20Edge%20AI.md)  
- **Repositório:** `C:\Users\Marlon\Documents\Agent PC\ia-banco-local`  
- **Público-alvo:** Diretoria Executiva, Engenharia de Software, Arquitetura de IA e Gestores de Negócio B2B  

---

## 1. Visão Executiva & Reposicionamento Estratégico

### 1.1 O Fim do "Medidor Ambulante" e a Tese do Mentor de Decisão
Operações comerciais modernas (postos com sondas automáticas Veeder-Root/Companytec, lojas de conveniência, varejo e franquias) **já possuem hardware e painéis passivos que medem estoques e volumes brutos**. O mercado não precisa de mais um "medidor ambulante" que apenas repete o que sensores já registram.

O gargalo real do gestor e do dono da empresa é a **ausência de inteligência acionável e mentoria estratégica**:
1. **Dados Sem Lucro:** Sistemas legados mostram faturamento bruto, mas ocultam onde a margem está sendo corroída (taxas de cartão, produtos de baixa rentabilidade, descontos descontrolados).
2. **Incapacidade de Simulação (Cenários "What-If"):** O gestor não sabe o impacto de reajustar o preço em R$ 0,05, alterar o mix de vendas ou trocar a escala de operadores.
3. **Falta de Comparações Acionáveis:** Nenhuma ferramenta tradicional cruza organicamente o Turno A vs Turno B, Operador 1 vs Operador 2 em conversão de alto valor, ou Dia Atual vs Média Histórica com explicação causal de por que um performou melhor que o outro.
4. **Decisões Reativas e Tardias:** Quebras de caixa, desvios e estoques estagnados só são percebidos no fechamento do mês, quando o prejuízo já ocorreu.

A AURA assume o papel de **Mentor de Decisão de Borda (Executive Decision Mentor)**:
Ela combina a soberania do banco de dados local com GenUI e Server-Driven UI para entregar:
- **Análise Profunda:** Decomposição de margem real líquida por categoria, produto e modalidade de recebimento.
- **Previsões Preditivas:** Projeção de fluxo de caixa, demanda de pico e comportamento de clientes.
- **Consultas Multidimensionais:** Perguntas complexas respondidas com diagnósticos claros e memória de cálculo auditável.
- **Comparações & Benchmarks:** Confronto de turnos, colaboradores e períodos com identificação imediata de gaps e oportunidades de ganho.
- **Decisão Assertiva em 1 Toque:** Action Sheets executivas que permitem aplicar correções imediatas com segurança.

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

## 6. Catálogo Canônico de Micro-Widgets do Mentor de Decisões (Especificação de Contratos)

Abaixo está a especificação do catálogo canônico da AURA IntelligentUI, projetado para atuar como **mentor executivo de negócios**, indo muito além de telemetria estática:

| Invocação Canônica (`tool_name`) | Nome do Componente no Cliente | Contrato Backend Vinculado | Visualização Rica: Análise & Mentoria (Camada 2) | Action Sheet Transacional: Decisão Assertiva (Camada 3) |
| :--- | :--- | :--- | :--- | :--- |
| **`render_ExecutiveBriefingUI`** | `ExecutiveBriefingWidget` | `ExecutiveBriefingContract` | **Diagnóstico Executivo do Dia:** Lucro bruto estimado, margem líquida real, 3 pontos críticos de atenção no negócio e gap de faturamento vs meta. | • `Aplicar Recomendações do Dia`<br>• `Ajustar Metas de Pista/Caixa`<br>• `Projetar Cenário no Canvas` |
| **`render_MarginAnalysisUI`** | `MarginProfitabilityWidget` | `MarginAnalysisContract` | **Análise de Margem Real & Meios de Pagamento:** Decomposição de margem líquida por categoria (Combustíveis, Conveniência, Troca de Óleo) e impacto real de taxas de cartões e vouchers frota. | • `Simular Repasse de Taxa de Cartão`<br>• `Destacar Produtos de Alta Margem`<br>• `Auditar Custos no Canvas` |
| **`render_PredictiveScenarioUI`** | `PredictiveScenarioWidget` | `PredictiveForecastContract` | **Simulador Preditivo ("What-If"):** Projeção de fluxo de caixa para os próximos 3 a 7 dias, elasticidade de demanda em simulações de preço (+/- R$ 0,05) e previsão de pico de fluxo por horário. | • `Homologar Cenário Simulado`<br>• `Agendar Compra no Ponto Ótimo`<br>• `Exportar Estudo Preditivo` |
| **`render_BenchmarkComparisonUI`** | `ComparativeBenchmarkWidget` | `ComparativeBenchmarkContract` | **Comparações & Benchmarks Lado a Lado:** Turno 1 vs Turno 2 (faturamento, quebra de caixa, mix), Operador A vs B em conversão de aditivada/lubrificantes, e Este Período vs Mês Anterior. | • `Bonificar Operadores Destaque`<br>• `Acionar Treinamento de Abordagem`<br>• `Inspecionar Turnos no Canvas` |
| **`render_FinancialLeakAuditUI`** | `FinancialLeakAuditWidget` | `ShiftReconciliationContract` | **Mentor de Prevenção de Fugas & Quebras:** Auditoria contínua de caixa PDV, cancelamentos excessivos de cupons, sangrias e furos de estoque físico vs fiscal em tempo real. | • `Estancar Quebra de Caixa no Turno`<br>• `Bloquear Desconto Anômalo`<br>• `Auditar Caixa no Canvas` |
| **`render_BasketUpsellStrategyUI`** | `BasketUpsellWidget` | `MarketBasketContract` | **Mentor de Alavancagem de Ticket Médio:** Pares de vendas cruzadas com alto Lift (Pista x Conveniência x Serviços), impacto projetado no faturamento e script prático para a equipe. | • `Ativar Campanha de Balcão no PDV`<br>• `Imprimir Script de Abordagem`<br>• `Simular Impacto no Canvas` |

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

### Fase 0 — Inventário, Baseline & Arquitetura do Protocolo GenUI (P0) [CONCLUÍDA EM 07/10/2026]
**Objetivo:** Estabelecer o contrato formal do protocolo GenUI, configurar os identificadores de rastreabilidade e isolar o ambiente sem tocar nas rotas ativas de produção.

- [x] **F0-01 — Especificação Formal do Protocolo de Streaming GenUI:**  
  Documentação formal homologada em [`docs/protocolo_streaming_genui.md`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/docs/protocolo_streaming_genui.md). Mapeados e especificados os tipos canônicos de chunks SSE: `delta` (Resumo Executivo), `ui_skeleton` (placeholder sub-100ms), `ui_delta` (streaming de props), `ui_complete` (envelope canônico validado) e `ui_action_feedback` (confirmação com Action Voucher assinado).
- [x] **F0-02 — Criação do Registro Centralizado de Componentes no Frontend (`web/js/aura-genui.js`):**  
  Implementado `window.AuraGenUI` e `window.SecureComponentRegistry` com arquitetura Zero-Bundler (nativa para navegador e `module.exports` para Node.js). Inclui `registerComponent`, `resolveComponent` (mitigação estrita de OWASP LLM03 - Agência Excessiva), `escapeHtml` (mitigação de OWASP LLM01 - XSS) e integração no shell `web/index.html` com atributo `defer` e cache-buster.
- [x] **F0-03 — Padronização de IDs de Idempotência Criptográfica:**  
  Módulo `core/schemas/idempotency.py` criado e exportado em `core/schemas/__init__.py`. Geradores e validadores RFC 4122 UUID v4 padronizados para `tool_call_id` e `action_id` em Python e JavaScript (`web/js/aura-genui.js`), acompanhados do modelo Pydantic `IdempotencyKey`.
- [x] **F0-04 — Criação do Módulo de Testes de Linha de Base (`scripts/test_genui_baseline.py`):**  
  Suíte automatizada completa criada e executada com 100% de sucesso validando: (1) Idempotência Python; (2) Shell e rotas estáticas; (3) SecureComponentRegistry, bloqueio LLM03 e XSS no Node.js; (4) Zero regressão com 100% de aprovação nas 4 suítes analíticas existentes (`test_aura_aux_panel.py`, `test_phase5_specialized_responses.py`, `test_phase6_quality_resilience.py`, `test_aura_showcase.py`).

**Critério de Aceite da Fase 0 (100% Aprovado):**  
- [x] Contratos de protocolo documentados e revisados (`docs/protocolo_streaming_genui.md`).
- [x] `SecureComponentRegistry` declarado e acessível em `window.SecureComponentRegistry` e `window.AuraGenUI`.
- [x] Todos os testes de linha de base e suítes de regressão passando com 100% de sucesso (`scripts/test_genui_baseline.py`).

---

### Fase 1 — Backend: Protocolo SSE Multiplexado & Envelopes Tipados (P0) [CONCLUÍDA EM 07/10/2026]
**Objetivo:** Evoluir `core/aura_api.py` e `core/aura_engine.py` para emitir o fluxo de streaming em duas etapas bem demarcadas (Resumo Executivo inicial seguido de Structured Output encapsulado em envelope GenUI).

- [x] **F1-01 — Extensão do Modelo `AuraChunkType` em `core/aura_engine.py`:**  
  Adicionados os novos tipos de chunks no Enum:
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
- [x] **F1-02 — Envelope Pydantic Canônico para Componentes GenUI (`core/schemas/genui.py`):**  
  Criado schema unificado com metadados de ciclo de vida e idempotência:
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
- [x] **F1-03 — Ajuste do Gerador de Streaming no `AuraEngine.ask_stream()`:**  
  Ao processar uma pergunta com intenção analítica identificada:
  1. Emitir `ui_skeleton` com o nome do componente a ser renderizado e o texto contextual ("Consultando volumetria dos tanques...").
  2. Emitir tokens textuais do Resumo Executivo (`DELTA`) enquanto a ferramenta finaliza os cálculos.
  3. Emitir o evento `ui_complete` contendo a serialização do `GenUIEnvelope`.
  4. Finalizar com `DONE`.
- [x] **F1-04 — Suíte de Testes Automatizada do Backend (`scripts/test_genui_engine_sse.py`):**  
  Validação estrita da ordem cronológica de emissão (`intent` -> `ui_skeleton` -> `delta` -> `ui_complete` -> `done`), isolamento de JSON bruto e zero regressões.

**Critério de Aceite da Fase 1 (100% Aprovado):**  
- [x] O endpoint `/api/v1/aura/chat` transmite SSE compatível com clientes legados e com o novo protocolo GenUI.
- [x] Nenhum token de JSON vaza como texto comum no chat.
- [x] Teste `test_genui_engine_sse.py` aprovado com 100% de sucesso.

---

### Fase 2 — Frontend: Streaming Parser, Bufferização JSON & Skeleton UI (P0) [CONCLUÍDA EM 07/10/2026]
**Objetivo:** Evoluir `web/js/aura-api.js` e `web/js/aura-chat.js` para consumir o fluxo multiplexado, gerenciar buffer seguro de JSON e exibir skeletons com micro-copy contextual.

- [x] **F2-01 — Refatoração da Máquina de Estados de Streaming em `web/js/aura-api.js`:**  
  Garantir que eventos SSE multiplexados (`event: ui_skeleton`, `event: ui_delta`, `event: ui_complete`, `event: ui_action_feedback`) sejam despachados para callbacks específicos sem atrasar a renderização dos tokens textuais de Resumo Executivo (`event: delta`). Compatibilidade dual com `streamChat()` e `chatStream()` e exportação CommonJS para Node.js.
- [x] **F2-02 — Implementação do Buffer de Fragmentos JSON com Fallback Gracioso:**  
  Módulo `GenUIFragmentBuffer` implementado em `web/js/aura-genui.js` e integrado em `web/js/aura-api.js`. Caso a inferência transmita deltas fracionados de JSON (`ui_delta`), acumula em string buffer volátil indexado por `tool_call_id` com tratamento `try-catch` que silencia erros parciais de sintaxe até o evento `ui_complete` ou `[DONE]`.
- [x] **F2-03 — Injeção de Skeleton UI Reativo (`SkeletonPulse`) em `web/js/aura-chat.js`:**  
  No exato momento em que `ui_skeleton` é interceptado, aloca no DOM do chat um bloco visual com animação pulsante sutil (`animate-pulse`), status dot (`animate-ping`), classes AURA Precision Glass (`web/css/aura.css`) e texto explicativo da etapa em execução:
  ```html
  <div id="genui-skeleton-[tool_call_id]" class="genui-skeleton-slot p-4 rounded-xl border border-cyan-500/20 bg-slate-900/60 backdrop-blur-md">
    <div class="flex items-center gap-3">
      <div class="w-3 h-3 rounded-full bg-cyan-400 animate-ping"></div>
      <span class="text-xs font-mono text-cyan-300 tracking-wide uppercase font-semibold">
        AURA Engine: Analisando indicadores executivos...
      </span>
    </div>
    <div class="mt-3 space-y-2">
      <div class="h-4 bg-slate-800/80 rounded w-3/4 animate-pulse"></div>
      <div class="h-8 bg-slate-800/60 rounded w-full animate-pulse"></div>
    </div>
  </div>
  ```
- [x] **F2-04 — Hidratação Instantânea sem Layout Jank (Zero CLS):**  
  Assim que `ui_complete` é recebido, resolve o componente no `SecureComponentRegistry` (ou aplica fallback gracioso Precision Glass preparando o terreno para a Fase 3), substitui o esqueleto do DOM com transição de opacidade suave (150ms fade-in), e remove graciosamente slots órfãos (`cleanupSkeletonSlots`) se a resposta terminar em erro ou sem `ui_complete`.
- [x] **F2-05 — Suíte de Testes Automatizada do Frontend (`scripts/test_genui_frontend_streaming.py`):**  
  Suíte automatizada completa em Python e Node.js validando: (1) Contratos estáticos e exportações; (2) Parser SSE multiplexado de `aura-api.js`; (3) Buffer de fragmentos parciais de `aura-genui.js`; (4) Ciclo de vida no DOM de `aura-chat.js` (inserção, hidratação, substituição 150ms e limpeza graciosa); (5) Zero regressão em todas as 4 suítes analíticas existentes (`test_genui_baseline.py`, `test_genui_engine_sse.py`, `test_aura_aux_panel.py`, `test_phase6_quality_resilience.py`).

**Critério de Aceite da Fase 2 (100% Aprovado):**  
- [x] Transição visual contínua: Resumo Executivo datilografado -> Skeleton ativo -> Widget hidratado.
- [x] Zero quebra de layout (*Zero Cumulative Layout Shift* - CLS).
- [x] Teste em Node.js simulando chunks SSE multiplexados comprovando montagem correta.
- [x] Todas as suítes analíticas existentes e testes da Fase 2 passando com 100% de sucesso (`scripts/test_genui_frontend_streaming.py`).

---

### Fase 3 - Micro-Widget Piloto em 3 Camadas: `ExecutiveDecisionMentorUI` (P0) [CONCLUÍDA EM 08/10/2026]
**Objetivo:** Construir a primeira implementação completa fim-a-fim da arquitetura GenUI para o fluxo de **Mentoria Executiva de Decisão & Briefing Estratégico do Negócio** (cruzando margem real, pontos de atenção operacional e recomendações prioritárias com simulação).

- [x] **F3-01 - Componente `ExecutiveDecisionMentorUI` no `SecureComponentRegistry` (`web/js/aura-genui-widgets.js`):**  
  Implementada a classe de componente no frontend em `web/js/aura-genui-widgets.js` registrada formalmente em `SecureComponentRegistry` com suporte Zero-Bundler (browser e Node.js). Inclui ciclo de vida de montagem (mount), hidratação via props tipadas, tolerância a falhas com fallback gracioso e sanitização de HTML contra OWASP LLM01.
- [x] **F3-02 - Construção da Visualização Rica (Camadas 1 e 2 - Resumo Executivo e Diagnóstico de Rentabilidade):**  
  Camada 1 com badge de status operacional e resumo executivo em tipografia AURA Precision Glass Deluxe. Camada 2 com grid de métricas financeiras (Receita, Margem Bruta, Margem Líquida, Quebra de Caixa), projeções de impacto preditivo (Run-Out de tanques, risco financeiro) e lista de evidências auditáveis de auditoria.
- [x] **F3-03 - Construção da Action Sheet Transacional (Camada 3 - Tomada de Decisão):**  
  Botões de ação executiva com variantes visuais (primary, secondary, danger) respeitando o contrato `GenUIActionOption`. Mecânica de Optimistic UI com bloqueio imediato contra duplo clique (`isLocked`), indicador de carregamento e rollback resiliente em caso de falha de rede ou timeout.
- [x] **F3-04 - Projeção Paralela no Companion Canvas e Integração com Backend:**  
  Integração automática com o painel lateral (`window.auraAuxPanel.projectArtifact`) via método `projectToCanvas()`, normalizador de payload em `web/js/aura-aux-panel.js`, e backend FastAPI/AuraEngine emitindo o envelope canônico com intent `mentoria_decisao` via SSE multiplexado e rota síncrona `/api/v1/aura/chat`.

**Critério de Aceite da Fase 3 (100% Aprovado):**  
- [x] Perguntas executivas como *"Qual o diagnóstico do meu negócio hoje?"* ou *"Onde estou perdendo margem?"* renderizam o Resumo, o widget analítico e a Action Sheet de decisão.
- [x] Componente 100% responsivo (Compact Card no Mobile e Dual Workspace no Desktop) com acessibilidade WCAG 2.1 AA e suporte a `prefers-reduced-motion`.
- [x] Suíte de testes completa automatizada em Python e Node.js com 100% de aprovação e zero regressão nas 5 suítes anteriores (`scripts/test_genui_decision_mentor.py`).

---

### Fase 4 - Motor de Gestao de Estado no Cliente, Idempotencia & Optimistic UI (P1) [CONCLUIDA EM 08/10/2026]
**Objetivo:** Implementar o gerenciador de estado reativo no cliente (`AuraStateManager`) para garantir idempotencia, bloqueio contra cliques duplicados, persistencia local e rollback limpo.

- [x] **F4-01 - Criacao do `AuraStateManager` (`web/js/aura-state-manager.js`):**  
  Gerenciador central com tabela hash de estados indexada por `tool_call_id` e persistencia de curto prazo em `sessionStorage`:
  ```javascript
  class AuraStateManager {
    constructor(options = {}) {
      this.storageKey = (options && options.storageKey) || 'aura_state_manager_v1';
      this.widgets = new Map(); // tool_call_id -> widgetEntry
      this.executedActions = new Set(); // action_id
      this.actionResults = new Map(); // action_id -> result
      this.loadFromSessionStorage();
    }
    registerWidget(toolCallId, initialProps, ttlSeconds, customTimestamp) { ... }
    getWidget(toolCallId) { ... }
    lockWidget(toolCallId, actionId) { ... }
    unlockWidget(toolCallId) { ... }
    isActionExecuted(actionId) { return this.executedActions.has(actionId); }
    markActionExecuted(actionId, result) { 
      this.executedActions.add(actionId);
      if (result) this.actionResults.set(actionId, result);
      this.persistToSessionStorage();
    }
    isStale(timestamp, ttlSeconds = 900) { ... }
    isWidgetStale(toolCallId) { ... }
    applyOptimisticState(toolCallId, optimisticData) { ... }
    rollbackOptimisticState(toolCallId) { ... }
    finalizeSuccessState(toolCallId, result) { ... }
    persistToSessionStorage() { ... }
    loadFromSessionStorage() { ... }
  }
  ```
- [x] **F4-02 - State Locking Imediato contra Duplo Clique:**  
  No evento de clique da Action Sheet (`handleActionClick` em `web/js/aura-genui-widgets.js`):
  1. Verificacao imediata se `action_id` ja foi executado (`isActionExecuted`) ou se o widget esta bloqueado (`isLocked`), descartando cliques subsequentes de forma idempotente.
  2. Aplicacao de classes CSS tateis de desabilitacao imediata (`opacity-50 pointer-events-none cursor-not-allowed`).
  3. Substituicao de texto e feedback visual animado com icone de spinner e estado transicional claro.
- [x] **F4-03 - Fluxo Otimista com Rollback Resiliente:**  
  1. Aplicacao de snapshot de estado anterior e mutacao otimista visual (`applyOptimisticState`).
  2. Chamada RPC de execucao transacional (`window.auraApi.executeAction(actionId, widget.props)`).
  3. Em caso de sucesso, marcacao definitiva (`markActionExecuted`), gravacao de voucher e finalizacao (`finalizeSuccessState`).
  4. Em caso de falha de rede ou timeout, reversao perfeita do snapshot previo (`rollbackOptimisticState`), restauracao tatil do botao e disparo de notificacao toast nao intrusiva (`window.auraFx.showToast`).
- [x] **F4-04 - Expiracao de Acoes no Historico do Chat (Stale Action Guard):**  
  Verificacao de TTL (padrao 15 minutos / 900s) via `isStale` e `isExpired()`. Acoes antigas no feed do chat recebem badge semantico visual de proposta expirada (`.badge-expired`, `.genui-expired-badge`) e tem botoes de mutacao desabilitados no DOM, impedindo mutacoes defasadas. `AuraChatController.expireStaleWidgets()` implementado para varredura periodica do historico.

**Criterio de Aceite da Fase 4 (100% Aprovado):**  
- [x] Cliques multiplos no mesmo botao geram apenas uma unica chamada de rede (prevencao absoluta de duplo clique).
- [x] Simulacao de erro ou queda de conexao reverte o estado do botao instantaneamente com snapshot e feedback via toast.
- [x] Inspecao de TTL desabilita acoes no historico com badge de proposta expirada apos 15 minutos (900s).
- [x] Suite de testes automatizada em Python e Node.js cobrindo o ciclo de vida completo de mutacao, storage e rollback com 100% de sucesso e zero regressao (`scripts/test_genui_state_manager.py`).

---

### Fase 5 - Sincronizacao Bidirecional (Server-State vs. Client-State) & Memoria do Agente (P1) [CONCLUIDA EM 08/10/2026]
**Objetivo:** Conectar as mutacoes de interface no cliente de volta ao cerebro do agente (Server-State), eliminando a amnesia contextual da IA.

- [x] **F5-01 - Endpoint de Execucao de Acoes Transacionais (`POST /api/v1/aura/actions/execute`):**  
  Implementado em `core/aura_api.py` com contratos tipados Pydantic v2 `ActionExecuteRequest` e `ActionVoucher` em `core/schemas/genui.py`. Valida estritamente a idempotencia (duplo envio com mesmo `action_id` retorna o voucher previamente gerado sem reprocessar), gera `voucher_id` (UUID v4), assina com HMAC-SHA256 auditavel e despacha rotinas de negocio autorizadas de postos (pedidos de combustivel, estancamento de quebra/sangria, ajuste de margem e conciliacao de turno).
- [x] **F5-02 - Injecao de `tool_result` no Historico do `AuraEngine` (`AuraSessionMemory`):**  
  Ao concluir a acao no endpoint, injeta diretamente no historico da sessao uma mensagem canonica com `role: "tool"`, `tool_call_id`, `name` e payload JSON contendo status APPROVED, action_id, voucher_id e detalhes. Tabela SQLite `aura_messages` estendida com colunas `tool_call_id` e `name`, e tabela `aura_action_vouchers` para rastreabilidade permanente. Suporte integral a recuperacoes canônicas para IA de nuvem (Gemini/OpenAI/Anthropic).
- [x] **F5-03 - Consistencia Contextual Subsequente (Prevencao de Amnesia Contextual):**  
  Historico formatado para o prompt do LLM (`format_history_for_prompt`) inclui registros de acoes confirmadas (`Acao Confirmada [{action_name}]`). Perguntas subsequentes na mesma sessao (ex: "Qual o status daquele pedido de combustivel?") reconhecem a acao executada via voucher e confirmam que o pedido ja foi homologado no ERP, sem recalcular a sugestao como pendente.
- [x] **F5-04 - Conexao Frontend no Cliente (`web/js/aura-api.js` & `web/js/aura-genui-widgets.js`):**  
  `AuraApiClient.executeAction()` integrado a rota real `/api/v1/aura/actions/execute` com timeout, tratamento de erros e retorno de voucher. `ExecutiveDecisionMentorUI` atualiza `AuraStateManager` (`finalizeSuccessState` e `markActionExecuted`) e exibe badge visual `.genui-success-badge` / `.badge-committed` (VOUCHER AUDITADO) no DOM.
- [x] **F5-05 - Suite de Testes Automatizada da Fase 5 (`scripts/test_genui_server_sync.py`):**  
  Suite completa cobrindo: (1) Contratos Pydantic e assinaturas HMAC; (2) Endpoint FastAPI e formato de voucher; (3) Idempotencia estrita contra duplo envio; (4) Injecao de `role: "tool"` e persistencia no SQLite; (5) Consistencia contextual multiturn sem amnesia; (6) Integracao cliente em Node.js headless; (7) Zero regressao em todas as 5 suites homologadas anteriores.

**Criterio de Aceite da Fase 5 (100% Aprovado):**  
- [x] Acao executada na interface atualiza imediatamente o historico do motor de IA.
- [x] Nenhuma duplicidade de recomendacao ocorre em interacoes consecutivas.
- [x] Teste automatizado validando a integridade da memoria do agente em sessao de multiplos turnos.
- [x] Regressao zero em todas as suites anteriores (`test_genui_baseline.py`, `test_genui_engine_sse.py`, `test_genui_frontend_streaming.py`, `test_genui_decision_mentor.py`, `test_genui_state_manager.py`).

---

### Fase 6 — Expansão do Catálogo de Micro-Widgets do Mentor de Decisões (P2)
**Objetivo:** Implementar os módulos analíticos avançados de mentoria estratégica, comparações multidimensionais e simulação de cenários no padrão GenUI de 3 camadas com Action Sheets assertivas.

- [x] **F6-01: Micro-Widget `MarginAnalysisUI` (Analise de Margem Real & Meios de Pagamento):**  
  - **Camada 1:** Sintese executiva da margem liquida real consolidada e impacto de taxas financeiras.
  - **Camada 2:** Decomposicao visual de rentabilidade por linha de negocio (Combustiveis, Conveniencia, Lubrificantes/Servicos) e taxa media de desconto por bandeira de cartao/voucher.
  - **Camada 3:** Action Sheet: `Simular Repasse de Taxa de Cartao`, `Reprecificar Produto com Margem Negativa` e `Auditar Custos no Canvas`.
- [x] **F6-02: Micro-Widget `PredictiveScenarioUI` (Simulador de Cenarios "What-If" & Demanda):**  
  - **Camada 1:** Projecao preditiva de faturamento e volume para os proximos 3 a 7 dias com base em historico e sazonalidade.
  - **Camada 2:** Grafico interativo com simulacoes prontas (+/- R$ 0,05 no preco, impacto no volume e margem de contribuicao).
  - **Camada 3:** Action Sheet: `Aplicar Cenario Simulado`, `Agendar Compras no Ponto Otimo` e `Exportar Projecao`.
- [x] **F6-03: Micro-Widget `BenchmarkComparisonUI` (Comparacoes & Benchmarks Lado a Lado):**  
  - **Camada 1:** Resumo executivo de contraste apontando onde esta o gap de desempenho e quem puxou o resultado para cima ou para baixo.
  - **Camada 2:** Painel comparativo em colunas paralelas (Turno A vs Turno B, Operador 1 vs Operador 2 em conversao de aditivada/lubrificantes, ou Dia Atual vs Media Historica).
  - **Camada 3:** Action Sheet: `Bonificar Colaborador Destaque`, `Acionar Treinamento de Abordagem de Pista` e `Inspecionar Turnos no Canvas`.
- [x] **F6-04: Micro-Widget `FinancialLeakAuditUI` (Mentor de Prevencao de Fugas de Caixa & Desvios):**  
  - **Camada 1:** Alerta em tempo real de quebras de caixa, sangrias anomalas ou cancelamentos de cupons fiscais.
  - **Camada 2:** Matriz de conferencia centavo a centavo entre faturamento registrado, gaveta fisica e conciliacao de cartoes TEF.
  - **Camada 3:** Action Sheet: `Estancar Quebra no Turno Vigente`, `Auditar Cancelamentos Suspeitos` e `Homologar Fechamento no Canvas`.
- [x] **F6-05: Micro-Widget `BasketUpsellStrategyUI` (Alavancagem de Ticket Medio & Cross-Selling):**  
  - **Camada 1:** Oportunidades de vendas cruzadas com alto coeficiente de Lift (ex: Pista + Conveniencia, Combustivel + Aditivo).
  - **Camada 2:** Cartoes dos top combos com metricas de Suporte, Confianca e potencial de faturamento adicional em R$.
  - **Camada 3:** Action Sheet: `Ativar Campanha de Balcao no PDV`, `Imprimir Script de Abordagem para Operadores` e `Simular Ganho Mensal`.

**Criterio de Aceite da Fase 6 (100% Aprovado):**  
- [x] Todos os 5 modulos de inteligencia decisoria possuem renderizadores nativos padronizados registrados no `SecureComponentRegistry`.
- [x] A estetica de design segue com perfeicao o tema AURA Precision Glass.
- [x] Consultas complexas do usuario acionam o widget analitico correspondente com diagnostico e opcoes de decisao assertivas.
- [x] Suite automatizada `scripts/test_genui_catalog_expansion.py` homologada com 100% de sucesso.

---

### Fase 7 - Hardening de Seguranca Cibernetica, OWASP LLM & Governanca (P0/P1) [CONCLUIDA EM 08/10/2026]
**Objetivo:** Blindar o sistema contra as principais vulnerabilidades de sistemas de IA generativa em ambientes industriais B2B.

- [x] **F7-01 - Mitigacao Estrita de OWASP LLM03 (Excessive Agency / Agencia Excessiva):**  
  - Proibicao absoluta de execucao de codigo JavaScript dinamico vindo do LLM (sem `eval`, sem `new Function`, sem injecao de `<script>`).
  - O LLM apenas escolhe a chave do catalogo (`component_name`) e fornece parametros tipados.
  - Qualquer chave nao registrada dispara fallback imediato e gracioso para visualizacao de texto bruto sanitizado (`renderSafeFallback`), registrando log de alerta de seguranca `[AURA-SEC-003]` no backend e no frontend.
- [x] **F7-02 - Mitigacao de OWASP LLM01 (Prompt Injection no Frontend & Coercao Estrita):**  
  - Todas as propriedades textuais injetadas em nos de texto passam por sanitizacao rigorosa via `escapeHtml()`.
  - Coercao estrita de tipos para numeros (`coerceNumber` / `Number()`) e booleanos (`coerceBoolean` / `Boolean()`), impedindo injecoes de atributos maliciosos.
  - Protecao recursiva contra prototype pollution e ciclos de referencia em `sanitizeProps()`.
- [x] **F7-03 - Governanca RBAC de Autorizacao de Operador (Human-in-the-Loop Gateway):**  
  - Validacao de perfil/permissao de operador baseada em roles minimas no endpoint `POST /api/v1/aura/actions/execute` e modelo `ActionExecuteRequest.operator_role`.
  - Roles suportadas: `frentista` (nivel 1), `caixa` (nivel 2), `gerente` (nivel 3), `administrador` (nivel 4).
  - Mutacoes de alto impacto (`pedido_combustivel`, `ajustar_margem`, etc.) bloqueiam operadores de nivel inferior (frentista, caixa) com HTTP 403 Forbidden.
  - Acoes de caixa (`estancar_quebra`, `forcar_sangria`, etc.) exigem ao menos perfil caixa, bloqueando frentistas com HTTP 403 Forbidden.
  - Acoes de inspecao e navegacao liberadas para qualquer role.
- [x] **F7-04 - Trilha de Auditoria Transacional Duravel (Audit Log):**  
  - Tabela duravel `aura_action_audit_log` no SQLite do `AuraSessionMemory` com persistencia de `audit_id` (UUID v4), `timestamp` ISO UTC, `tool_call_id`, `action_id`, `operator_id`, `operator_role`, `authorized`, `status` (APPROVED, REJECTED_FORBIDDEN, FAILED), `details` JSON e `client_ip`.
  - Metodos `save_audit_log(...)` e `get_audit_logs(...)` no motor.
  - Endpoint `GET /api/v1/aura/audit/logs` para consulta de conformidade e auditoria de acoes executadas.

**Criterio de Aceite da Fase 7 (100% Aprovado):**  
- [x] Tentativa de injecao de payload com tags HTML maliciosas e scripts e neutralizada com sucesso.
- [x] Requisicoes a ferramentas inexistentes ou alucinadas sao bloqueadas com log de seguranca e fallback seguro.
- [x] Controle de acesso RBAC bloqueia tentativas nao autorizadas com HTTP 403 Forbidden e registra a recusa no log.
- [x] Trilha de auditoria operacional gravando eventos transacionais duraveis em SQLite com consulta via endpoint.
- [x] Suite automatizada `scripts/test_genui_security_hardening.py` homologada com 100% de sucesso.

---

### Fase 8 - Qualidade, Suite de Testes Automatizados & Validacao Fim-a-Fim (P0) [CONCLUIDA EM 08/10/2026]
**Objetivo:** Provar o funcionamento do sistema completo atraves de testes de execucao reais no backend e no frontend, com zero regressao.

- [x] **F8-01 - Suite de Testes de Contratos GenUI (`scripts/test_genui_contracts.py`):**  
  Validacao de serializacao, imutabilidade tipada (Pydantic v2), idempotencia RFC 4122 v4 e assinatura HMAC-SHA256 de vouchers de acao para todos os 6 micro-widgets do catalogo.
- [x] **F8-02 - Suite de Testes de Streaming e Bufferizacao (`scripts/test_genui_streaming.py`):**  
  Emissao multiplexada SSE (`intent` -> `ui_skeleton` -> `delta` -> `ui_complete` -> `done`), simulacao de fragmentacao arbitraria de pacotes TCP (16 a 128 bytes), blindagem contra vazamento de JSON em texto e resiliencia contra aborto/desconexao.
- [x] **F8-03 - Suite de Testes de Ciclo de Vida Frontend via Node.js (`scripts/test_genui_frontend_lifecycle.py`):**  
  Validacao programatica em ambiente headless Node.js: montagem dos 6 micro-widgets nas 3 camadas, transicao Zero CLS de Skeleton para Card Hidratado, State Locking imediato no clique contra duplo envio, Optimistic UI com Rollback e toast em falhas, neutralizacao estrita de XSS (OWASP LLM01) e finalizacao com badge auditado (`VOUCHER AUDITADO`).
- [x] **F8-04 - Suite de Validacao Fim-a-Fim Consolidada (`scripts/test_genui_e2e_quality.py`):**  
  Runner mestre integrado que orquestra as suites F8-01, F8-02 e F8-03 com medicao de latencia individual, relatorio tabular estruturado (< 60s total, sem loops recursivos) e 100% de sucesso.
- [x] **F8-05 - Documentacao e Homologacao Git:**  
  Documentacao formal atualizada no roadmap com rastreabilidade completa e versionamento no repositorio principal.

**Criterio de Aceite da Fase 8 (100% Aprovado):**  
- [x] 100% de aprovacao em todos os contratos, streaming e testes de ciclo de vida.
- [x] Relatorio consolidado de metricas de execucao e latencia gerado com sucesso (< 60s).
- [x] Regressao zero comprovada nas suites analiticas existentes.

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
| **Fase 0** | Inventário, Baseline & Arquitetura do Protocolo | **P0** | Nenhuma | Concluída (07/10/2026) |
| **Fase 1** | Backend: Protocolo SSE Multiplexado & Envelopes | **P0** | Fase 0 | Concluída (07/10/2026) |
| **Fase 2** | Frontend: Streaming Parser, Buffer & Skeleton UI | **P0** | Fase 1 | Concluída (08/10/2026) |
| **Fase 3** | Micro-Widget Piloto: `ExecutiveDecisionMentorUI` | **P0** | Fase 1, Fase 2 | Concluída (08/10/2026) |
| **Fase 4** | Gestao de Estado, Idempotencia & Optimistic UI | **P1** | Fase 3 | Concluida (08/10/2026) |
| **Fase 5** | Sincronizacao Bidirecional & Memoria do Agente | **P1** | Fase 4 | Concluida (08/10/2026) |
| **Fase 6** | Expansao do Catalogo de Micro-Widgets | **P2** | Fase 3, Fase 4 | Concluida (08/10/2026) |
| **Fase 7** | Hardening de Seguranca Cibernetica & OWASP | **P0/P1** | Fase 5, Fase 6 | Concluida (08/10/2026) |
| **Fase 8** | Qualidade, Testes Automatizados & Validacao E2E | **P0** | Continuo desde F1 | Concluida (08/10/2026) |
| **Fase 9** | Rollout Gradual, Feature Flags & Observabilidade | **P2** | Fase 8 | 1-2 dias |

- **Total de Esforço Estimado:** 19 a 31 dias úteis para entrega completa com grau industrial de robustez.  
- **Menor Entrega Utilizável (MVP GenUI):** Fases 0, 1, 2, 3 e 4 (Piloto ExecutiveDecisionMentorUI funcional com streaming, skeleton, widget de 3 camadas e state locking) em **9 a 15 dias**.

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
