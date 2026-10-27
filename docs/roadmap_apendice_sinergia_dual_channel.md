# APENDICE C: SINERGIA DUAL-CHANNEL, NITIDEZ OPTICA E FLUXO SEQUENCIAL (CHAT -> CANVAS)

> **Classificacao:** Plano Diretor de Engenharia de Experiencia, Tipografia Nida e Coreografia Cognitiva  
> **Versao:** 1.0.0-PRO  
> **Branch Alvo:** `feature/partner-api-gateway` (posterior merge para `main`)  
> **Repositorio Base:** `ia-banco-local`  
> **Regra Estrita de Conformidade:** ZERO travessoes Unicode (`\u2014` e `\u2013`) em todo o codigo, comentarios, docstrings, templates e testes. Utilizar exclusivamente hifens comuns (`-`), dois pontos (`:`) ou setas (`->`).

---

## 1. OBJETIVO E DIAGNOSTICO DE EXPERIENCIA DO USUARIO

Este documento especifica a solucao definitiva para o desacoplamento, complementaridade e coreografia de leitura entre o **Container de Chat** e o **Companion Canvas (GUI)** da AURA, resolvendo os tres gargalos apontados na validacao visual com o usuario:

1. **Percepcao de Texto Embaçado (Blurry Text):**
   - Causado pelo forçamento de `-webkit-font-smoothing: antialiased` no Windows (que desliga o ClearType nativo de subpixel), agravado por tamanho de fonte reduzido (`text-xs` / `12px`), cor de contraste medio (`#cbd5e1`) dentro de accordions e camadas residuais de composicao de GPU (`transform` residual de animacoes).
2. **Atropelamento da Jornada de Leitura (`autoOpen: true` precoce):**
   - O Companion Canvas abre automaticamente na metade direita da tela em `< 200ms` (no evento `ui_complete`), antes mesmo de a AURA comecar a escrever no chat. Esse movimento lateral brusco sequestra a atencao do gestor, fazendo a analise textual ser ignorada.
3. **Fadiga de Redundancia Textual Tripla (Chat x GUI):**
   - O mesmo bloco de texto (ex: apontamento de erro no item da cerveja) aparece tres vezes:
     1. No corpo do Chat;
     2. Na caixa monoespacada de *Visao Gestor* no topo do Canvas;
     3. No card individual de apontamento no pe do Canvas.
   - Alem disso, o chat exibia concorrentemente dois botoes de expansao conflitantes: `Explorar detalhamento textual completo (+Detalhes)` e `Ver no Painel >`.

---

## 2. ARQUITETURA DA JORNADA SEQUENCIAL COMPLEMENTAR

```
+-----------------------------------------------------------------------------------+
|               FLUXO COREOGRAFADO DE 2 ESTAGIOS (CHAT -> CANVAS)                   |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  ESTAGIO 1: CHAT EXECUTIVO (Leitura em 5 Segundos - Palco Principal)             |
|  ===================================================================              |
|  - Nitidez optica maxima: ClearType nativo, 0.94rem (15px), Slate-100 (#f1f5f9)   |
|  - Sintese Clusterizada: Diagnostico agrupado por causa raiz (SEM lista de itens) |
|  - Zero accordions "+Detalhes" competindo no chat                                 |
|  - Canvas lateral PERMANECE FECHADO/RECOLHIDO durante a leitura                   |
|                                                                                   |
|                                       |                                           |
|                                       v ( Apos a leitura, o usuario clica )       |
|                                                                                   |
|  ESTAGIO 2: COMPANION CANVAS (Inspecao Tabil, Matriz e Acao - Sob Demanda)       |
|  ========================================================================         |
|  - Acionado exclusivamente pelo Card de Transicao Contextual ao fim do texto      |
|  - Exibe o que texto nao entrega: Tabelas item a item, graficos, reguas e botoes  |
|  - Eliminacao de caixas de texto redundantes na Visao Gestor                      |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

---

## 3. ESPECIFICACAO DETALHADA POR FASE DE EXECUCAO

### FASE 1: Nitidez Optica e Renderizacao Cristalina do Texto (`web/css/aura.css`)

#### 1.1. Restauracao do Subpixel Rendering e Fim da Camada GPU Estagnada
No Windows, o texto com `-webkit-font-smoothing: antialiased` renderiza em escala de cinza, afinando as hastes das letras e diminuindo o contraste em telas 1080p padrão.
- Em `web/css/aura.css`:
  - Substituir `-webkit-font-smoothing: antialiased` nas bolhas de chat por renderizacao otimizada de legibilidade sem supressao de subpixel:
    ```css
    .chat-bubble-aura,
    .chat-bubble-user {
      -webkit-font-smoothing: subpixel-antialiased;
      -moz-osx-font-smoothing: auto;
      text-rendering: optimizeLegibility;
      transform: none !important;
      will-change: auto !important;
    }
    ```
  - Garantir que `.animate-fade-in` remova qualquer propriedade de `transform` ao final da execucao, evitando que o Chromium mantenha o texto em textura de composicao bitmap com subpixels desalinhados.

#### 1.2. Elevacao de Contraste e Escala Modular Anti-Embaçamento
- **Cor Base de Leitura:** Elevar de `#cbd5e1` (Slate-300) para `#e2e8f0` (Slate-200) com parágrafo de entrada em `#f8fafc` (Slate-50).
- **Tamanho Minimo de Leitura:** Fixar a fonte do chat em `0.935rem` (`~15px`) com `line-height: 1.65`.
- **Proibicao de `text-xs` (12px) no Fluxo Textual:** Eliminar aplicacoes de `text-xs` para blocos de leitura ou explicacoes no chat. Tamanho `12px` e reservado estritamente para metadados, chips de telemetria e timestamps.

---

### FASE 2: Coreografia Sequencial e Card de Ponte Contextual (`web/js/aura-chat.js`)

#### 2.1. Desativacao do `autoOpen` Apressado no Desktop
- Em `web/js/aura-chat.js` (metodo `hydrateGenUISlot` e callbacks de streaming):
  - Definir `autoOpen: false` como padrao ao processar `ui_complete`.
  - O Companion Canvas sera projetado e mantido no registro em background, mas **NAO abrira a split view automaticamente**.
  - O chat permanece em tela cheia/centralizado para permitir leitura sequencial sem quebras de layout.

#### 2.2. Remocao do Accordion Conflitante `+Detalhes` em Respostas com Canvas
- Quando a resposta possuir um Companion Canvas acoplado (`hasToolCard === true`):
  - **Desativar o encapsulamento em `<details class="aura-chat-disclosure">`**.
  - O chat deve conter **apenas o resumo executivo fluido** (2 a 3 paragrafos concisos).
  - O aprofundamento operacional e transferido integralmente para o Companion Canvas lateral, acabando com a duplicidade de botoes de expansao.

#### 2.3. Redesenho do Card de Transicao (`renderCompanionPortalCard`)
- O card que surge ao final da mensagem devera atuar como um convite contextual claro e convidativo:
  - Titulo: Nome do modulo analitico (ex: *"Diagnostico Fiscal & Regras SEFAZ"*).
  - Subtitulo: Indicador numerico do que sera explorado (ex: *"3 itens afetados, chave de 44 digitos e parecer contabil"*).
  - Botao de Acao: `[Explorar no Canvas ->]` ou `[Ver no Painel ->]`, abrindo o painel lateral com transicao suave e foco no elemento relevante.

---

### FASE 3: Contrato "Zero Repeticao" no Core do Backend (`core/aura_engine.py` e Prompts)

#### 3.1. Divisao Canonica de Conteudo (Clusterizacao Causal vs. Matriz Item a Item)
Padronizar em `core/aura_engine.py` (`_resolver_contexto_ferramenta` e `_gerar_sintese_contingencia_ferramenta`):

1. **O que vai para o CHAT (Sintese Representativa e Observavel):**
   - Agrupamento inteligente das causas raiz.
   - *Regra Estrita:* O texto do chat NUNCA lista produtos linha por linha ou itens individuais (nao escrever item 2 Heineken, item 17 Stella, etc.).
   - *Estrutura Padrao do Chat:*
     - **Veredito:** O status macro e a quantidade total de ocorrencias (ex: *"Documento bloqueado com 3 inconsistencias de valor negativo e ausencia de protocolo SEFAZ"*).
     - **Causa Raiz Geral:** A regra de negocio ou motivo legal que gerou o bloqueio (ex: *"Descontos comerciais de aplicativo foram declarados incorretamente como acrescimo negativo"*).
     - **Resolucao no ERP:** O caminho direto no webPosto (ex: *"Acesse Faturamento > Notas Fiscais e mova os valores para o campo Desconto (vDesc)"*).
     - **Ponte Contextual:** Orientacao para o Canvas (ex: *"Os 2 itens especificos, o totalizador e a nota tecnica para o contador estao no painel ao lado"*).

2. **O que vai para o CANVAS (Evidencia e Operacao):**
   - A tabela / matriz com todas as linhas afetadas (Item 2, Item 17, Totais).
   - Detalhes de tags XML (`<vOutro>`, `<vDesc>`), CSTs, CFOPs, codigos ANP e aliquotas.
   - Botoes de acao de 1-clique (Copiar Parecer para Contador, Despachar Pedido, Bloquear Caixa).

#### 3.2. Atualizacao dos Prompts Sistematicos (`core/prompts/system_prompts.py`)
- Em `build_system_prompt` e `build_fiscal_audit_prompt`:
  - Incluir clausula explicita: *"Quando o Companion Canvas estiver ativo, NUNCA descreva itens individuais, produtos linha por linha ou tabelas repetitivas no texto. Agrupe os fatos geradores pela causa raiz e convide o gestor a inspecionar os detalhes tabulares no Canvas."*

---

### FASE 4: Limpeza da Redundancia Interna no Canvas (`web/js/aura-genui-widgets.js` e `core/aura_engine.py`)

#### 4.1. Remocao do Bloco Monoespacado Duplicado no Topo do Canvas
- No card fiscal (`build_canonical_genui_envelope` e `FiscalShieldInspectorUI`):
  - Remover a geracao de listas redundantes de bullets (`textos_gestor.append(...)`) em `props["persona_views"]["gestor"]` que repetem as explicacoes executivas dos cards de baixo.
- Substituir o topo da Visao Gestor por um **Card Resumo de Impacto da Pista**:
  - Destaque do impacto imediato no faturamento;
  - Tempo estimado de retencao de veiculo na pista;
  - Botao de resolucao guiada.

#### 4.2. Comportamento Inteligente da Barra de Persona (Gestor vs. Contador)
- Alternar a visualizacao dos proprios cards e tabelas de apontamentos:
  - **Na Visao Gestor:** Foco em linguagem de posto (nome do produto comercial, bico, frentista, orientacao de como destravar no webPosto).
  - **Na Visao Contador:** Foco em linguagem contabil/fiscal (tags XML, codigos de rejeicao MOC 7.0, base legal e registros SPED C113/1300).

---

### FASE 5: Suite de Testes Automatizados e Sincronizacao (`tests/unit/test_sinergia_dual_channel.py`)

1. **Testes de CSS e Nitidez Optica:**
   - Validar que `.chat-bubble-aura` utiliza propriedades de subpixel e nao possui `transform` estatico residual.
   - Validar que a cor base de `.prose-aura` e `#e2e8f0` ou superior.
   - Validar que nenhuma regra de texto corrido no chat cai para `text-xs` (`12px`).
2. **Testes de Coreografia no Frontend (Node/Jest/Pytest):**
   - Validar que `autoOpen` e `false` durante o recebimento de mensagens com GenUI.
   - Validar que respostas com `hasToolCard = true` nao geram `<details class="aura-chat-disclosure">` duplicado no chat.
3. **Testes de Backend de Nao-Duplicacao:**
   - Validar que a sintese deterministica de `xml_documento` nao contem listagem exaustiva de itens individuais quando `genui_active=True`.
   - Validar que `persona_views.gestor` nao repete a lista de `findings`.
4. **Sincronizacao de Distribuicao:**
   - Garantir paridade 100% entre `web/` e `dist/AuraBackend/_internal/web/`.
5. **Regra de Conformidade Estrita:**
   - 0 ocorrencias de travessoes Unicode (`\u2014` e `\u2013`) em todos os arquivos modificados e criados.

---

## 4. CHECKLIST DE VERIFICACAO FINAL PARA O AGENTE EXECUTOR

- [x] `web/css/aura.css` atualizado com nitidez optica máxima (ClearType nativo, `#e2e8f0`, tamanho `0.935rem` e zero `transform` residual).
- [x] `web/js/aura-chat.js` configurado com `autoOpen: false` no fluxo padrao e remocao de `<details>` concorrente quando houver Canvas.
- [x] `core/aura_engine.py` ajustado para clusterizar causas raiz no chat e eliminar duplicacao textual em `persona_views.gestor`.
- [x] `core/prompts/system_prompts.py` atualizado com regra estrita de clusterizacao causal sem despejo de itens repetidos.
- [x] `web/js/aura-genui-widgets.js` ajustado para limpar textos redundantes no topo da visualizacao do Canvas e introduzir visualizacao adaptativa por persona.
- [x] Arquivos sincronizados em `dist/AuraBackend/_internal/web/`.
- [x] Nova suite de testes `tests/unit/test_sinergia_dual_channel.py` implementada e passando com 100% de sucesso.
- [x] Zero ocorrencias de `\u2014` e `\u2013` confirmadas.
- [x] `pytest` executado com 100% de aprovacao em todo o repositorio (829 testes aprovados, 1 pulado, 0 falhas).
