# APENDICE B DE ENGENHARIA UX & TIPOGRAFIA COGNITIVA: CONTAINER DE CHAT INTELIGENTE, EDITORIAL E ANTI-FADIGA (AURA)

> **Classificacao:** Especificacao Tecnica Executavel para Agente de IA (UX Writing + Tipografia Cognitiva + Simbiose Chat/GUI)  
> **Versao:** 2.2.0-EDITORIAL  
> **Branch Alvo:** `feature/partner-api-gateway`  
> **Repositorio Base:** `ia-banco-local`  
> **Paradigma de Design:** `Dual-Channel Cognitive UX` (GUI com foco 100% Visual e Interativo | Chat com foco 100% Textual, Editorial, Escaneavel e Anti-Fadiga)  
> **Regra Estrita e Inegociavel:** ZERO travessoes Unicode (`\u2014` e `\u2013`) em todo o codigo Python, JavaScript, HTML, CSS, comentarios, docstrings, mensagens de commit e testes. Utilizar exclusivamente hifens ASCII (`-`), dois pontos (`:`) ou setas (`->`).

---

## 1. OBJETIVO E FUNDAMENTACAO DE UX TEXTUAL

Em aplicacoes corporativas de uso diario continuo (como a gestao de pista, retaguarda fiscal e fechamento de caixa no posto), interfaces de chat tradicionais tornam-se rapidamente **"enjoativas" e visualmente exaustivas** devido a quatro falhas classicas de engenharia de interface:

1. **Inflacao de Negrito e Contraste Agressivo (Bold & Halation Fatigue):** Textos longos em branco puro (`#ffffff`) sobre fundo escuro com excesso de palavras em `font-weight: 700` e multiplos spans coloridos brilhantes causam ofuscamento na retina (*halation effect*) e anulam a hierarquia visual (quando tudo esta destacado, nada tem destaque).
2. **Duplicacao Cognitiva entre Chat e GUI:** Quando o Companion Canvas (GUI lateral) ja projeta cards ricos com KPIs, rankings e tabelas, o container do chat nao deve repetir as mesmas listas de numeros em texto bruto.
3. **Largura de Linha Descalibrada e Falta de Ritmo Vertical:** Linhas que ocupam 100% de um container largo (> 85 caracteres) exigem movimentos sacadicos longos dos olhos, gerando perda de linha e cansaco mental apos poucos minutos de leitura.
4. **Ausencia de Escaneabilidade Estruturada (F-Pattern, Layer-Cake e BLUF):** O leitor executivo nao le palavra por palavra; ele escaneia o veredito no topo (*Bottom Line Up Front*), busca ancoras numericas monoespacadas e so expande detalhes tecnicos quando necessario (*Progressive Disclosure*).

### Divisao Clara de Responsabilidades (Paradigma Dual-Channel AURA):
- **Foco da GUI (`#companion-canvas` / Widgets GenUI):** Entregar uma **experiencia visual, grafica e tatica** (cards modulares, semaforos luminosos, anatomia de chave 44 digitos, comparativos e botoes de acao em 1-clique).
- **Foco do Chat (`#chat-feed-container` / `.prose-aura`):** Entregar uma **experiencia textual editorial, limpa, inteligente e confortavel**, onde a tipografia guia o olho sem esforco, destaca dados criticos com precisao cirurgica e oculta a complexidade excessiva sob demanda.

---

## 2. ARQUITETURA DAS 4 FASES DE EVOLUCAO DO CHAT CONTAINER

```
+---------------------------------------------------------------------------------------+
|          UPGRADE DE TIPOGRAFIA COGNITIVA & UX TEXTUAL DO CHAT AURA (4 FASES)          |
+---------------------------------------------------------------------------------------+
| FASE 1: Ergonomia Tipografica, Escala Modular e Anti-Fadiga Visual (web/css/aura.css) |
|         - Calibracao de largura otima de leitura (65ch-70ch) e ritmo vertical (1.68)  |
|         - Sistema Tri-Tipografico: Geist Sans 400 (prosa) + Geist Mono (dados/metricas)|
|         - Fim da inflacao de bold e conversao de cores neon em Micro-Tokens sutis     |
+---------------------------------------------------------------------------------------+
| FASE 2: Motor de Formatacao Inteligente e Progressive Disclosure (web/js/aura-chat.js)|
|         - Auto-Tokenizacao de metricas (R$, Litros, %, CFOP, CST) em fonte tabular    |
|         - Lead Paragraph Editorial (BLUF: veredito destacado na primeira linha)       |
|         - Progressive Disclosure automatico (Acordeao para analises longas > 4 linhas)|
+---------------------------------------------------------------------------------------+
| FASE 3: UX Writing nos Prompts e Sintese Enxuta Dual-Channel (core/prompts & engine)  |
|         - Regra de Ouro nos Prompts: Briefing de 2-3 frases quando a GUI estiver ativa|
|         - Regra dos 10% de destaque (proibicao de frases inteiras em negrito)         |
|         - Enxugamento das sinteses de contingencia quando genui_active=True           |
+---------------------------------------------------------------------------------------+
| FASE 4: Controle de Densidade de Leitura e Suite de Testes (web/index.html & tests/)  |
|         - Toggle de Conforto no Chat: [Modo Executivo Conciso] vs [Modo Detalhado]    |
|         - Testes automatizados validando tokenizacao, CSS ergonomico e zero travessao |
+---------------------------------------------------------------------------------------+
```

---

## 3. ESPECIFICACAO TECNICA PASSO A PASSO

### FASE 1: Ergonomia Tipografica, Escala Modular e Anti-Fadiga Visual (`web/css/aura.css`)

#### 1.1. Reengenharia de `.prose-aura` para Leitura Confortavel de Longa Duracao
Atualizar as regras de `.prose-aura` em `web/css/aura.css` aplicando os principios de neuroergonomia visual e tipografia editorial:

1. **Cor Base Anti-Ofuscamento e Ritmo Vertical:**
   - Alterar a cor base do texto de `#e2e8f0` para `#cbd5e1` (Slate-300: contraste suave de ~11:1 sobre `#090e1a`, eliminando o brilho estourado na retina).
   - Definir `font-family: var(--font-sans)` com `font-weight: 400` (nunca `500` ou `600` no corpo corrido).
   - Definir `font-size: 0.915rem` (14.6px) com `line-height: 1.68` e `letter-spacing: 0.005em`.
2. **Largura Otima de Linha (Optimal Measure - Regra de Bringhurst):**
   - Aplicar `max-width: 68ch` em `.prose-aura p`, `.prose-aura ul`, `.prose-aura ol` e `.prose-aura blockquote`, mantendo tabelas e blocos de codigo livres para ate `100%`.
3. **Veredito Inicial (Lead Paragraph BLUF):**
   - Estilizar `.prose-aura > p:first-of-type`:
     - `color: #f1f5f9` (Slate-100, levemente mais claro que os paragrafos seguintes para ancorar o olhar).
     - `font-size: 0.94rem`.
     - `line-height: 1.6`.
     - `margin-bottom: 0.85rem`.
4. **Controle de Negrito (`strong` / `b`) sem Fadiga:**
   - Alterar `.prose-aura strong, .prose-aura b` de `font-weight: 700; color: #ffffff` para:
     - `font-weight: 600` (SemiBold equilibrado).
     - `color: #f8fafc` (Slate-50).
     - `letter-spacing: -0.005em`.
5. **Listas Escaneaveis (Layer-Cake Pattern):**
   - Substituir marcadores padrao pesados por marcadores sutis em ciano/ardosia (`::marker { color: #64748b; font-family: var(--font-mono); font-size: 0.8em; }`).
   - Espacamento entre itens `.prose-aura li`: `margin-bottom: 0.45rem; padding-left: 0.25rem;`.

#### 1.2. Micro-Tokens Semanticos e Dados Tabulares (`.aura-data-token`)
Criar em `web/css/aura.css` a classe `.aura-data-token` e refinar os destaques coloridos dentro do chat para evitar o aspecto "arvore de natal" (excesso de cores neon brilhantes):

1. **Classe `.aura-data-token` (Numeros, R$, Litros, %, CFOP, CST):**
   ```css
   .prose-aura .aura-data-token {
     font-family: var(--font-mono);
     font-variant-numeric: tabular-nums;
     font-size: 0.86em;
     font-weight: 500;
     color: #e2e8f0;
     background: rgba(255, 255, 255, 0.04);
     border: 1px solid rgba(255, 255, 255, 0.08);
     padding: 0.08rem 0.35rem;
     border-radius: 5px;
     white-space: nowrap;
   }
   ```
2. **Suavizacao de `.text-emerald`, `.text-amber`, `.text-rose`, `.text-cyan`, `.text-purple` dentro de `.prose-aura`:**
   - Remover o `text-shadow` neon pesado quando aplicado dentro de `.prose-aura`.
   - Usar `font-family: var(--font-mono)`, `font-size: 0.88em`, `font-weight: 500`, `padding: 0.08rem 0.38rem`, `border-radius: 5px` e fundo sutil de `8%` de opacidade (`rgba(..., 0.08)`), transformando palavras coloridas soltas em micro-badges editoriais elegantes.

---

### FASE 2: Motor de Formatacao Inteligente e Progressive Disclosure (`web/js/aura-chat.js`)

#### 2.1. Auto-Tokenizador de Dados Operacionais (`applySmartTypographyTokens`)
Em `web/js/aura-chat.js`, adicionar o metodo `applySmartTypographyTokens(htmlContent)` chamado ao final de `formatMarkdown(rawMarkdown, isStillStreaming)` (apenas fora de tags HTML e blocos `<pre>`/`<code>`):

1. Identificar automaticamente padroes numericos e fiscais chave no texto renderizado:
   - Valores monetarios: `R\$\s?-?\d{1,3}(?:\.\d{3})*(?:,\d{2})?`
   - Volumes e vazoes: `\b\d{1,3}(?:\.\d{3})*(?:,\d+)?\s?(?:L|L\/min|L\/h|litros)\b`
   - Percentuais e desvios: `[+\-]?\d+(?:[.,]\d+)?%`
   - Codigos fiscais e operacionais: `\b(?:CFOP\s?\d{4}|CST\s?\d{2,3}|NCM\s?\d{4,8}|Rejeicao\s?\d{3}|cStat\s?=\s?\d{3})\b`
2. Envolver essas ocorrencias (quando ainda nao estiverem dentro de `<code>`, `<strong>` ou `<span>`) com `<span class="aura-data-token">...</span>`, garantindo que todos os numeros da conversa fiquem perfeitamente alinhados em `Geist Mono` (`tabular-nums`).

#### 2.2. Progressive Disclosure no Chat (`applyProgressiveDisclosure`)
Para impedir que respostas extensas gerem fadiga visual no feed:

1. Implementar em `web/js/aura-chat.js` o metodo `applyProgressiveDisclosure(htmlContent, isStillStreaming, hasToolCard)`:
   - Executar apenas quando `isStillStreaming === false` (resposta concluida).
   - Se a mensagem possuir **Companion Canvas ativo (`hasToolCard === true`)** e o HTML do chat contiver mais de 3 blocos (`<p>`, `<ul>`, `<ol>`, `<table>`), manter visiveis os **2 primeiros blocos** (o veredito BLUF e o resumo principal) e agrupar o restante dentro de um container colapsavel:
     ```html
     <details class="aura-chat-disclosure mt-2.5 rounded-xl border border-white/10 bg-slate-950/40 overflow-hidden">
       <summary class="px-3 py-1.5 text-[11px] font-mono text-slate-400 hover:text-cyan-300 cursor-pointer flex items-center justify-between select-none transition-colors">
         <span>Explorar detalhamento textual completo</span>
         <span class="text-[10px] bg-slate-800/80 px-1.5 py-0.5 rounded text-slate-300">+Detalhes</span>
       </summary>
       <div class="p-3 pt-2 border-t border-white/5 space-y-2 text-xs text-slate-300">
         <!-- blocos complementares -->
       </div>
     </details>
     ```
   - Se o usuario estiver com o modo `"expanded"` ativo nas preferencias de leitura, exibir tudo aberto por padrao.

#### 2.3. Cadencia de Streaming e Rodape de Telemetria Discreto
1. Em `updateTelemetryBadge(containerId, t)` (`web/js/aura-chat.js`):
   - Tornar o rodape de telemetria (`Resposta em Xms • Motor: ...`) mais discreto (`opacity-60 hover:opacity-100 transition-opacity font-mono text-[10px]`), evitando competir visualmente com a resposta principal da AURA.

---

### FASE 3: Engenharia de Prompt Editorial e Sintese Enxuta Dual-Channel (`core/prompts/system_prompts.py` e `core/aura_engine.py`)

#### 3.1. Diretrizes de UX Writing em `core/prompts/system_prompts.py`
Atualizar `build_system_prompt`, `build_fiscal_audit_prompt` e `build_help_prompt`:

1. **Metodologia BLUF (Bottom Line Up Front):**
   - A primeira frase deve entregar a resposta direta em no maximo 2 linhas, sem saudacoes repetitivas (*"Ola gestor, analisei os dados..."*).
2. **orcamento Estrito de Negrito (Bold Budget - Maximo 10%):**
   - Instruir explicitamente: *"Use negrito (**termo**) com extrema parcimonia: destaque no maximo 1 a 2 ancoras curtas por topico (apenas o valor final ou nome da entidade). NUNCA coloque frases inteiras ou explicacoes longas em negrito."*
3. **Simbiose Estrita Chat vs. GUI (`genui_active=True`):**
   - Quando a GUI estiver ativa, o texto do chat deve ter no maximo **3 paragrafos curtos (ou 1 paragrafo de veredito + 2 bullets concisos)**, atuando como um guia executivo para o card visual ao lado.

#### 3.2. Otimizacao das Sinteses Deterministicas em `core/aura_engine.py`
Em `_gerar_sintese_contingencia_ferramenta` (`core/aura_engine.py`):

1. Verificar o parametro `genui_active: bool = False` nos ramos principais (`roi_diagnostic`, `pos_audit`, `cenario_preditivo`, `conciliacao_caixa`, `estoque_combustivel`, `previsao_esgotamento_tanques`, `conformidade_lmc_anp`):
   - Quando `genui_active=True`, retornar uma **Sintese Editorial Enxuta (3 a 4 linhas)** contendo:
     1. Veredito direto com o indicador critico principal;
     2. Principal ponto de atencao ou oportunidade financeira;
     3. Orientacao direta para interacao no card visual projetado ao lado.
   - Quando `genui_active=False` (modo somente texto / API / WhatsApp), manter o relatorio textual completo estruturado em topicos escaneaveis.

---

### FASE 4: Controle de Conforto de Leitura e Testes Automatizados (`web/index.html`, `web/js/aura-chat.js` e `tests/unit/`)

#### 4.1. Toggle de Conforto de Leitura no Chat (`web/index.html` e `web/js/aura-chat.js`)
1. Adicionar no cabecalho superior da coluna de chat um seletor discreto `#btn-chat-reading-density` com icone tipografico (`Aa` / `book-open`), alternando entre:
   - `concise` (**Leitura Dinamica / Resumo Executivo** - padrao: ativa Progressive Disclosure e largura `68ch`);
   - `comfort` (**Leitura Expandida / Editorial** - abre todos os blocos de texto automaticamente e aumenta levemente o corpo da fonte para `0.96rem`).
2. Persistir a escolha do usuario em `localStorage.getItem('aura_chat_reading_mode')`.

#### 4.2. Suite de Testes Unitarios (`tests/unit/test_chat_typography_ux.py`)
Criar `tests/unit/test_chat_typography_ux.py` validando:
1. Presenca das regras ergonomicas em `web/css/aura.css` (`max-width: 68ch`, `.aura-data-token`, `.aura-chat-disclosure`, `tabular-nums`).
2. Tokenizacao automatica de valores (`R$`, `L`, `%`, `CFOP`, `CST`) em `AuraChatController.prototype.formatMarkdown`.
3. Encapsulamento Progressive Disclosure (`<details class="aura-chat-disclosure">`) quando uma mensagem longa possui card GenUI acoplado.
4. Sinteses deterministicas concisas em `_gerar_sintese_contingencia_ferramenta` quando `genui_active=True`.
5. Sincronizacao 100% identica entre `web/` e `dist/AuraBackend/_internal/web/`.
6. Ausencia absoluta de travessoes Unicode (`\u2014` e `\u2013`) em todos os arquivos do projeto.

---

## 4. CHECKLIST DE VERIFICACAO FINAL PARA O AGENTE EXECUTOR

- [x] `web/css/aura.css` contem a calibracao `.prose-aura` (`#cbd5e1`, `max-width: 68ch`, `line-height: 1.68`, `strong` em `600`, `.aura-data-token` com `tabular-nums` e `.aura-chat-disclosure`).
- [x] `web/js/aura-chat.js` implementa `applySmartTypographyTokens` e `applyProgressiveDisclosure`, alem do toggle `#btn-chat-reading-density`.
- [x] `core/prompts/system_prompts.py` aplica as regras BLUF e Bold Budget (maximo 10% de palavras em negrito).
- [x] `core/aura_engine.py` respeita `genui_active=True` em `_gerar_sintese_contingencia_ferramenta`, evitando despejar listas longas no chat quando o card GenUI ja esta visivel.
- [x] Arquivos modificados em `web/` foram copiados para `dist/AuraBackend/_internal/web/`.
- [x] Zero ocorrencias de `\u2014` ou `\u2013` verificadas via script Python.
- [x] `pytest` executa com 100% de aprovacao.
