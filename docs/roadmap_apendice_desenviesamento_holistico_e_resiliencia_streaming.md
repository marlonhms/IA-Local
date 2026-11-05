# ROADMAP APENDICE: DESENVIESAMENTO HOLISTICO DE PANORAMA, HIGIENIZACAO DE TELEMETRIA FANTASMA E RESILIENCIA ATOMICA DE STREAMING (AURA)

> **Classificacao:** Plano Diretor de Engenharia de Contexto, Sanitizacao de Telemetria e Resiliencia de Inferencia para Execucao por Agente de IA  
> **Versao:** 2.3.0-HOLISTIC-PANORAMA  
> **Repositorio Base:** `ia-banco-local`  
> **Foco Tecnologico:** Equilibrio Cognitivo Multi-Dominio (Faturamento, Margem, Caixa, Fiscal e Estoque), Expurgo de Tanques Fantasmas e Garantia de Integridade Textual no Streaming SSE  
> **Status de Execucao:** 100% CONCLUIDO E HOMOLOGADO (Etapas 1 a 5 validadas em testes unitarios e suite de regressao)
> **Regra Estrita de Conformidade:** ZERO travessoes Unicode (`\u2014` e `\u2013`) em todo o codigo, comentarios, docstrings, templates, YAML e testes. Utilizar exclusivamente hifens comuns (`-`), dois pontos (`:`) ou parenteses.

---

## 1. CASO DE ESTUDO FORENSE E DIAGNOSTICO DAS 3 DISTORCOES ARQUITETURAIS

### 1.1. O Incidente Concreto
Ao realizar um check-in executivo aberto e natural no console conversacional da AURA:
> *"Olá, Aura. Como estamos hoje?"*

**Comportamento Observado em Producao:**
1. **Roteamento:** Acionou corretamente a intencao `mentoria_decisao` (`Mentor de Decisoes Executivo`).
2. **Obsessao por Tanques e Falso Alarme (`Tanque 000`):** Tanto o texto do chat quanto o card do Companion Canvas abriram com um alarme de pane seca em um tanque inexistente/inativo:
   - **Chat:** *"Tanque 000 (Gasolina Comum) em estado crítico com 0,0h de autonomia, com margem consolidada em 14,2% e faturamento di"*
   - **Canvas (`render_ExecutiveDecisionMentorUI`):** *"Tanque 000 (GASOLINA COMUM) atingirá nível crítico em 0,0h, Margem consolidada em 14,2%. faturamento diário em R$ 2.114,26,"*
3. **Frase Cortada na Metade (Truncamento Abrupto):** A resposta textual no chat foi interrompida no meio da palavra `"faturamento di"`, sem concluir o raciocinio executivo.

---

### 1.2. Raio-X Forense: A Cadeia Causal Tripla

A investigacao profunda do codigo-fonte, da tabela `public.tanque` no PostgreSQL e do log operacional `logs/aura_service.log` comprovou que o problema decorre da combinacao de **tres distorcoes tecnicas independentes**:

```
+---------------------------------------------------------------------------------------------------------+
|                        CADEIA CAUSAL DO VIES DE TANQUES E TRUNCAMENTO DE STREAMING                      |
+---------------------------------------------------------------------------------------------------------+
| DISTORCAO 1: O "Fantasma do Tanque 000" na Telemetria e no Mentor Executivo (core/tools.py)             |
|   - Na tabela public.tanque do ERP, o primeiro registro e o 'Tanque 000 (GASOLINA COMUM)' com           |
|     capacidade=1000L, saldo=0.0L e bicos_conectados=[]. Trata-se de um registro virtual/inativo,        |
|     enquanto o Tanque 001 real de Gasolina Comum possui 25.550,48L (51,1% de ocupacao).                 |
|   - Em prever_esgotamento_tanques() (linha 2818), o codigo marca o Tanque 000 como 'INATIVO'.           |
|     Contudo, na linha 3115, calcula min_auto_crit_h sobre TODOS os tanques sem filtrar os inativos,     |
|     cravando autonomia_critica_horas = 0.0h e mantendo o Tanque 000 na posicao [0] da lista.            |
|   - Em gerar_diagnostico_mentoria_executiva() (linhas 8655-8671), o motor le detalhes_tq[0]             |
|     ('Tanque 000') e cai sempre na condicional 'elif autonomia_min_h < 12:', forcando 100% dos          |
|     diagnosticos gerais a comecarem por "Tanque 000 (GASOLINA COMUM) atingira nivel critico em 0,0h".   |
|                                                                                                         |
| DISTORCAO 2: Prompt Anchoring (Ancoragem Cognitiva em Tanques) (core/prompts/system_prompts.py)         |
|   - Em build_system_prompt() (linhas 230, 237 e 249), a diretriz de abertura (BLUF) e as regras         |
|     de cores usam "Tanque 1 (Gasolina Comum) critico com 14h de autonomia" como primeiro exemplo.       |
|   - Em modelos rapidos (Gemini Flash / Flash-Lite), o primeiro exemplo literal da regra de formato      |
|     atua como ancora semantica (Prompt Anchoring): diante de perguntas gerais ou ambiguas, a LLM        |
|     imita o template de tanque critico em detrimento de Faturamento, Margem, Caixa e Fiscal.            |
|                                                                                                         |
| DISTORCAO 3: Aceitacao de Stream Interrompida por Erro HTTP 503 (core/aura_engine.py)                   |
|   - O log registrou: "Timeout ou interrupcao no streaming da LLM (models/gemini-3.5-flash-lite):        |
|     503 This model is currently experiencing high demand."                                              |
|   - Nas linhas 5991-6020 de core/aura_engine.py, quando a API cai com erro 503 apos emitir apenas o     |
|     primeiro chunk ("...e faturamento di"), o bloco except executa 'break' e a linha 6018 valida        |
|     'if texto_completo: sucesso_llm = True', encerrando a resposta mutilada sem acionar o segundo       |
|     modelo de fallback nem a sintese deterministica completa.                                           |
+---------------------------------------------------------------------------------------------------------+
```

---

## 2. ARQUITETURA ALVO: EQUILIBRIO HOLISTICO DOS 4 PILARES E STREAMING ATOMICO

Para que a AURA atue como uma verdadeira **Gerente Supervisora e Mentora Executiva do Negocio**, o sistema deve tratar perguntas gerais e abertas (*"Como estamos hoje?"*, *"Qual o resumo do posto?"*, *"Me de um panorama"*) com **visao holistica equilibrada**, e nunca sequestrar a resposta com um unico indicador distorcido.

```
+---------------------------------------------------------------------------------------------------------+
|                    ARQUITETURA DE PANORAMA HOLISTICO E STREAMING RESILIENTE (v2.3.0)                    |
+---------------------------------------------------------------------------------------------------------+
|                                                                                                         |
|  1. CAMADA DE TELEMETRIA HIGIENIZADA (Zero Tanques Fantasmas)                                           |
|     - Filtragem estrita: Tanques com status_operacional == 'INATIVO' (ou cap <= 1000L e saldo == 0)     |
|       sao excluidos do calculo de autonomia minima, alertas criticos e manchetes executivas.            |
|     - Priorizacao de combustiveis com giro ativo na pista (bicos conectados e movimentacao real).       |
|                                                                                                         |
|  2. MOTOR DE MENTORIA DOS 4 PILARES EXECUTIVOS (gerar_diagnostico_mentoria_executiva)                   |
|     - Manchete Executiva (Diagnosis) construida de forma balanceada cobrindo:                           |
|       [Pilar 1: Faturamento do Dia] + [Pilar 2: Margem Consolidada] +                                   |
|       [Pilar 3: Conciliacao de Caixa/Turno] + [Pilar 4: Saude do Estoque Operacional Ativo]             |
|                                                                                                         |
|  3. PROMPT SISTEMICO DESENVIESADO (Neutral BLUF & Domain Fidelity)                                      |
|     - Exemplos BLUF multi-dominio equilibrados (Financeiro, Caixa, Comercial e Operacional).            |
|     - Regra explicita de Fidelidade de Escopo:                                                          |
|       * Pergunta Geral ("Como estamos hoje?") -> Sintese equilibrada dos 4 pilares do negocio.          |
|       * Pergunta Especifica (Fiscal, Caixa, Conveniencia) -> Foco 100% no dominio perguntado,           |
|         proibindo mencionar tanques se nao houver relacao com a pergunta.                               |
|                                                                                                         |
|  4. STREAMING ATOMICO ANTI-TRUNCAMENTO (Stream Integrity Guard)                                         |
|     - Rastreamento de flag 'stream_interrupted' no loop de chunks da LLM.                               |
|     - Se o stream sofrer queda (HTTP 503 / Timeout) no meio da geracao antes do StopAsyncIteration:     |
|       descarta ou substitui o fragmento truncado pela sintese deterministica completa ou segundo        |
|       modelo de fallback, garantindo 0% de frases cortadas pela metade no chat.                         |
+---------------------------------------------------------------------------------------------------------+
```

---

## 3. ESPECIFICACAO TECNICA DOS 5 MODULOS DE IMPLEMENTACAO

### ETAPA 1: Saneamento de Tanques Inativos/Fantasmas no Motor de Estoque (`core/tools.py`)

#### 1.1. Objetivo
Impedir que registros de tanques inativos, virtuais ou desativados no ERP (como o `Tanque 000` com capacidade de 1.000L e saldo 0,0L, ou tanques sem bicos e sem giro) contaminem a métrica `autonomia_critica_horas` e gerem falsos alertas de pane seca.

#### 1.2. Regras de Implementacao em `prever_esgotamento_tanques`
1. **Classificacao de Tanque Inativo / Sem Operacao:**
   - Um tanque deve ser marcado como `is_inativo = True` quando:
     - `cap <= Decimal("1000.0") and saldo == Decimal("0.0")` (ex: `Tanque 000` virtual), **OU**
     - `saldo == Decimal("0.0") and not bicos and codtan not in dispenses_por_tanque` (tanque vazio sem nenhum bico conectado e sem nenhum abastecimento historico).
2. **Ordenacao Limpa de `tanques_retorno`:**
   - Ordenar `tanques_processados` de forma que tanques operacionais ativos (`status_operacional != "INATIVO"`) venham sempre antes de tanques inativos, e dentro dos ativos, ordenados pelos que possuem giro real e menor autonomia operacional.
3. **Calculo Estrito sobre `tanques_ativos`:**
   - Calcular `has_crit_hours`, `has_crit_alert`, `min_auto_crit_h`, `min_auto_crit_d`, `min_auto_ro_h` e `min_auto_ro_d` **exclusivamente sobre `tanques_ativos`** (e preferencialmente sobre `tanques_com_saldo` quando houver tanques operacionais abastecidos para o mesmo combustivel, evitando que um tanque reserva seco gere falso `0.0h` quando o tanque principal do mesmo combustivel esta cheio).
   - Se o posto possui `Tanque 001 (GASOLINA COMUM)` com `25.550 L`, o `Tanque 000 (GASOLINA COMUM)` inativo jamais podera zerar a autonomia da Gasolina Comum.

---

### ETAPA 2: Reengenharia Holistica do Mentor de Decisoes Executivo - 4 Pilares (`core/tools.py` e `core/aura_engine.py`)

#### 2.1. Objetivo
Transformar o diagnóstico de `gerar_diagnostico_mentoria_executiva` (usado para responder `"Como estamos hoje?"` e briefings executivos) em um **panorama gerencial equilibrado dos 4 pilares do posto** (Faturamento, Margem, Caixa e Estoque Ativo), eliminando o sequestro da manchete por tanques.

#### 2.2. Regras de Implementacao em `gerar_diagnostico_mentoria_executiva`
1. **Selecao Correta do Tanque de Referencia:**
   - Em vez de fazer `t_top = detalhes_tq[0]` (que pegava o `Tanque 000`), buscar o `tanque_operacional_mais_critico` em `dados_tanques.get("operational_summary")` ou filtrar explicitamente `[t for t in detalhes_tq if t.get("status_operacional") != "INATIVO" and float(t.get("saldo_atual_litros") or 0) > 0]`.
   - Utilizar a autonomia critica desse tanque operacional ativo como `autonomia_min_h`.
2. **Construcao Holistica do `diagnostico`:**
   - A manchete executiva (`diagnosis`) deve sempre liderar com o **Panorama Financeiro e Operacional do Dia**, estruturada de forma equilibrada:
     - **Caso Normal / Estavel:**
       `"Panorama do dia: Faturamento acumulado em R$ {fat_total}, margem líquida consolidada em {margem_estimada_pct}% (meta {benchmark_margem_pct}%) e conciliação de caixa sem divergências (R$ {diff_caixa}). Menor autonomia operacional em {autonomia_min_h}h no Tanque {tanque_critico} ({comb_critico})."`
     - **Caso com Quebra de Caixa Relevante (`diff_caixa < -50`):**
       `"Panorama do dia: Faturamento em R$ {fat_total} e margem consolidada em {margem_estimada_pct}%, com alerta de diferença de caixa de R$ {abs(diff_caixa)} no turno. Estoque operacional com autonomia mínima de {autonomia_min_h}h ({comb_critico})."`
     - **Caso com Estoque Operacional em Atencao (`autonomia_min_h < 18` em tanque ativo):**
       `"Panorama do dia: Faturamento em R$ {fat_total}, margem líquida em {margem_estimada_pct}% e caixa conciliado (R$ {diff_caixa}). Atenção de reposição para {comb_critico} (Tanque {tanque_critico} com {autonomia_min_h}h de autonomia)."`

---

### ETAPA 3: Desenviesamento Cognitivo do System Prompt e Micro-SOPs (`core/prompts/system_prompts.py` e `core/prompts/micro_sops.py`)

#### 3.1. Objetivo
Remover o efeito de *Prompt Anchoring* em tanques do prompt principal e adicionar diretrizes explicitas de **Equilibrio Holistico em Perguntas Gerais** e **Isolamento de Dominio em Perguntas Especificas**.

#### 3.2. Alteracoes em `core/prompts/system_prompts.py`
1. **Substituir a Ancoragem em Tanques no BLUF:**
   - Trocar o primeiro exemplo de BLUF de `"Tanque 1 (Gasolina Comum) critico..."` por um exemplo de panorama executivo de negocios:
     `(ex: "Operacao do dia com faturamento de R$ 14.850,00, margem liquida em 14,2% e caixa conciliado sem quebras", "Turno 1 conciliado sem furos de caixa ou pista", "Variacao volumetrica dentro da tolerancia de +-0.6%")`.
2. **Inserir a Regra de Equilibrio Holistico vs Foco de Dominio:**
   - Em perguntas abertas de check-in (`"Como estamos hoje?"`), focar no resultado geral do negocio (Faturamento, Margem, Caixa, Estoque Ativo).
   - Em perguntas de dominios especificos (Fiscal, Caixa, Conveniencia), focar 100% no assunto perguntado e nunca puxar tanques.

---

### ETAPA 4: Blindagem Atomica de Streaming contra Truncamento HTTP 503 (`core/aura_engine.py`)

#### 4.1. Objetivo
Garantir que uma queda de conexao ou erro `503 High Demand` da API Google Gemini no meio da geracao de um texto **nunca mais deixe uma frase cortada na metade da palavra** no console conversacional do usuario.

#### 4.2. Alteracoes no Loop de Streaming em `core/aura_engine.py`
1. **Deteccao de Interrupcao Prematura (`stream_interrupted`):**
   - Rastrear flag `stream_interrupted` no loop assíncrono.
2. **Validacao de Integridade Sintatica da Resposta Parcial:**
   - Se `stream_interrupted` ocorrer antes de uma conclusao gramatical valida, acionar a contingencia deterministica completa para que a resposta final entregue ao usuario seja 100% integra e consistente.

---

### ETAPA 5: Suite de Testes Automatizados Anti-Vies e Anti-Truncamento

#### 5.1. Objetivo
Criar a suíte `tests/unit/test_holistic_panorama_and_streaming.py` cobrindo todas as 4 frentes:
1. `Tanque 000` inativo nao zera autonomia nem lidera diagnostico.
2. Panorama geral apresenta Faturamento, Margem e Caixa antes de estoques.
3. System prompt possui regra anti-vies.
4. Simulação de interrupcao 503 no streaming recompõe a resposta com sucesso.

---

## 4. CRITERIOS DE ACEITE E METRICAS DE QUALIDADE

1. **Zero Fantasma `Tanque 000`:** Em nenhuma consulta de panorama ou previsao de estoque o `Tanque 000` inativo e reportado como gargalo de `0.0h`.
2. **Equilibrio dos 4 Pilares:** Respostas a `"Como estamos hoje?"` apresentam Faturamento, Margem, Caixa e Estoque Ativo proporcionalmente.
3. **Integridade Textual 100% (Zero Truncamento):** Sob erro `503 High Demand` no meio do streaming, o texto final entregue e completo, gramaticalmente fechado e sem palavras cortadas.
4. **Conformidade CI/CD:** 100% dos testes unitarios passando em Python 3.11 e 3.12 e zero travessoes Unicode (`\u2014` ou `\u2013`).
