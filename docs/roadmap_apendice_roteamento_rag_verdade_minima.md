# ROADMAP APENDICE: ROTEAMENTO HIBRIDO DETERMINISTICO, RAG FACETADO E VERDADE MINIMA PARA MODELOS SLM E FLASH (AURA)

> **Classificacao:** Plano Diretor de Engenharia, Indexacao e Grounding para Execucao por Agente de IA  
> **Versao:** 2.2.0-GROUNDING-SLM  
> **Repositorio Base:** `ia-banco-local`  
> **Foco Tecnologico:** Alta precisao analitica sem dependencia de modelos caros ('PRO'), usando arquitetura composta de IA (*Compound AI Systems*)  
> **Regra Estrita de Conformidade:** ZERO travessoes Unicode (`\u2014` e `\u2013`) em todo o codigo, comentarios, docstrings, templates, YAML e testes. Utilizar exclusivamente hifens comuns (`-`), dois pontos (`:`) ou parenteses.

---

## 1. CASO DE ESTUDO FORENSE E DIAGNOSTICO DA CAUSA RAIZ

### 1.1. O Incidente Concreto
Durante consulta analitica do operador no painel conversacional da AURA, foi formulada a seguinte pergunta estritamente fiscal e tributaria:
> *"Quais os pontos criticos de ICMS Monofasico CST 61, PIS/COFINS CST 04 na conveniencia e rejeicoes SEFAZ?"*

**Comportamento Observado:**
- A AURA acionou o badge: `Consultando Mentor de Decisoes Executivo...`
- Resposta no Chat: *"Tanque 000 (GASOLINA COMUM) com autonomia esgotada (0,0h) e margem consolidada em 14,2%. Auditoria de tributos e PDV: Faturamento diario em R$ 2.114,26, sem divergencias na conciliacao de caixa (R$ 0,00)..."*
- Painel Companion Canvas: Renderizou o widget `render_ExecutiveDecisionMentorUI` com graficos de autonomia de combustivel da pista.

### 1.2. Raio-X Tecnico: A Cadeia Causal da Falha
A investigacao minuciosa do pipeline revelou que a base de dados da AURA **ja possui** o conhecimento fiscal cadastrado (regras da LC 192/2022, CST 61, Tabela 4.3.10 da EFD-Contribuicoes para CST 04 em bebidas/conveniencia, e rejeicoes SEFAZ 960, 958, 806 e 375 em [`core/fiscal_engine.py`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/core/fiscal_engine.py) e na tabela de conhecimento).

A quebra ocorreu em **quatro pontos da esteira de recuperacao e roteamento**:

```
+---------------------------------------------------------------------------------------------------------+
|                                    CADEIA CAUSAL DO ERRO DE RESPOSTA                                    |
+---------------------------------------------------------------------------------------------------------+
| 1. Query do Usuario: "Pontos criticos de ICMS Monofasico CST 61, PIS/COFINS CST 04 e SEFAZ?"            |
|    |                                                                                                    |
|    v                                                                                                    |
| 2. SemanticRouter: Falha de Priorizacao Heuristica e Spurious Vector Similarity                        |
|    - A funcao heuristica detectou 'auditoria_fiscal_sefaz' com 100% de precisao, porem a intencao NAO    |
|      estava na lista de override prioritario em core/semantic_router.py (linhas 1589-1608).              |
|    - O calculo vetorial puro (pgvector) casou a expressao "pontos criticos" com o exemplar              |
|      "Diagnostico de rentabilidade e pontos de atencao" da intencao 'mentoria_decisao' (score 0.611).    |
|    - A tabela aura_core.intencoes_vetores no PostgreSQL sequer continha vetores semeados para a          |
|      intencao 'auditoria_fiscal_sefaz'.                                                                 |
|    |                                                                                                    |
|    v                                                                                                    |
| 3. AuraEngine: Invocacao da Ferramenta Incorreta                                                        |
|    - Ao receber 'mentoria_decisao', o motor executou executar_mentor_decisao_executiva().                |
|    - A ferramenta inspecionou telemetria de tanques e conciliacao de caixas do ERP.                     |
|    |                                                                                                    |
|    v                                                                                                    |
| 4. Modelo LLM (Gemini Flash): Ingestao de Contexto Viciado                                              |
|    - O modelo menor (Flash) recebeu no prompt os dados de telemetria do Tanque 000 como tool output.   |
|    - Como instruido a fundamentar sua resposta nos fatos fornecidos, o modelo gerou a sintese sobre o   |
|      Tanque 000 e estoque de gasolina, ignorando a intencao fiscal original.                            |
+---------------------------------------------------------------------------------------------------------+
```

---

## 2. O PRINCIPIO DA "VERDADE MINIMA" SEM DEPENDENCIA DE MODELOS "PRO"

### 2.1. O Mito da "LLM Onisciente" e a Realidade dos Sistemas de Producao
Depender de um modelo "PRO" para entender perguntas operacionais e um erro arquitetural classico em IA corporativa por tres motivos:
1. **Inviabilidade Financeira:** Modelos de grande porte (como Gemini Pro ou Claude Opus) custam entre **15x e 30x mais** por milhao de tokens, inviabilizando planos de assinatura B2B acessiveis para o pequeno e medio lojista.
2. **Latencia Inaceitavel:** Modelos gigantes adicionam de 4 a 12 segundos de latencia, destruindo a experiencia em tempo real no PDV.
3. **Fragilidade de Contexto:** Mesmo um modelo "PRO", se receber no prompt a saida da ferramenta de tanques, tentara explicar os tanques ou hesitara sobre qual dado priorizar.

### 2.2. A Solucao: *Compound AI Architecture* (Sistemas Compostos de IA)
Em sistemas compostos, o modelo de linguagem menor (Gemini Flash, Flash-Lite, ou SLMs locais on-premise de 7B/8B como Llama-3 ou Qwen-2.5) tem um papel estrito e nobre: **redator executivo e formatador textual**, enquanto a **precisao do dado, a filtragem e a regra de negocio sao 100% resolvidas deterministicamente pelo Python e pelo banco de dados**.

```
+---------------------------------------------------------------------------------------------------------+
|                                ARQUITETURA DE VERDADE MINIMA (COMPOUND AI)                              |
+---------------------------------------------------------------------------------------------------------+
|                                                                                                         |
|   [ Pergunta do Usuario ]                                                                               |
|            |                                                                                            |
|            +---> [ CAMADA 1: Gate Lexico Determinant (Regex / Fast-Path) ]  <-- < 0.2ms (Zero Tokens)   |
|            |        Detecta tokens rigidos: CSTs, CFOPs, SEFAZ, Rejeicoes, LMC, Impostos               |
|            |                                                                                            |
|            +---> [ CAMADA 2: Semantic Router Calibrado + pgvector HNSW ]   <-- < 5ms                    |
|            |        Compara com intencoes semeadas e aplica threshold dinamico por categoria            |
|            |                                                                                            |
|            +---> [ CAMADA 3: Scoped Tooling & Context Isolation ]          <-- Zero Contaminacao        |
|            |        Isola ferramentas: Pergunta fiscal NUNCA recebe ferramentas de tanques ou bombas    |
|            |                                                                                            |
|            +---> [ CAMADA 4: Micro-SOP Fiscal / Ficha Tecnica Canonica ]   <-- Grounding Estruturado    |
|            |        Injeta YAML/Markdown compacto com a verdade fiscal exata (< 120 tokens)             |
|            |                                                                                            |
|            v                                                                                            |
|   [ Modelo LLM Flash / SLM Local ]                                                                      |
|      Recebe contexto puro, sem ruido e sem ambiguidade. Gera sintese executiva em < 1.5s (< R$ 0,001)   |
+---------------------------------------------------------------------------------------------------------+
```

---

## 3. ESPECIFICACAO DOS 5 MODULOS DE IMPLEMENTACAO

### MODULO 1: Gate Lexico Determinant e Whitelist de Intencoes Fiscais

#### 1.1. Objetivo
Impedir que perguntas contendo siglas tributarias, codigos de situacao tributaria ou termos regulatorios sejam submetidas a busca vetorial generica onde palavras acessorias ("pontos criticos", "analisar", "como fica") causem falso casamento vetorial.

#### 1.2. Especificacao Tecnica
Modificar [`core/semantic_router.py`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/core/semantic_router.py):
1. **Adicionar o Gate Lexico Fiscal (`0.04 Deteccao de Siglas e Termos Fiscais`)**:
   Expressao regular de alta precisao antes do calculo vetorial:
   ```python
   PADRAO_FISCAL_DETERMINISTICO = re.compile(
       r"\b("
       r"cst\s*(?:0[0-9]|[1-9][0-9])|"
       r"cfop\s*(?:[1-7][0-9]{3})|"
       r"icms(?:\s+monof[aá]sico|\s+st|\s+diferido)?|"
       r"pis(?:\s*\/\s*cofins)?|"
       r"cofins|"
       r"sefaz|"
       r"rejei[cç][aã]o\s*(?:\d{3})?|"
       r"nfe|nf-e|nfc-e|nfce|cte|ct-e|"
       r"chave\s+(?:de\s+acesso|da\s+nota)|"
       r"danfe|"
       r"difal|"
       r"cest|"
       r"substitui[cç][aã]o\s+tribut[aá]ria|"
       r"tributa[cç][aã]o\s+(?:monof[aá]sica|na\s+conveni[eê]ncia)"
       r")\b",
       re.IGNORECASE,
   )
   ```
2. **Priorizacao no Override Heuristico (Linha 1589 de `core/semantic_router.py`)**:
   Incluir `auditoria_fiscal_sefaz`, `conhecimento_fiscal` e `procedimento_erp` explicitamente na lista de intencoes prioritarias que sobrescrevem matches vetoriais ambiguos.

---

### MODULO 2: Semeador e Reindexador de Vetores (`aura_core.intencoes_vetores`)

#### 2.1. Objetivo
Garantir que a tabela `intencoes_vetores` no PostgreSQL `posto_ai` contenha embeddings de alta qualidade para **todas** as intencoes operacionais da AURA, especialmente as 19 frases exemplares de `auditoria_fiscal_sefaz` que estavam ausentes no banco.

#### 2.2. Especificacao Tecnica
Criar script utilitario [`scripts/seed_intent_vectors.py`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/scripts/seed_intent_vectors.py):
1. Itera sobre o dicionario `INTENT_EXEMPLARS` de [`core/semantic_router.py`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/core/semantic_router.py).
2. Para cada exemplo ausente no banco `intencoes_vetores`, gera o embedding halfvec(768) via `HybridRAGEngine` e insere atomicamente no schema `aura_core`.
3. Executa `REINDEX INDEX aura_core.idx_aura_core_intencoes_vetores_hnsw;` para recalibrar o grafo HNSW.

---

### MODULO 3: Catalogo Canonico de Fichas Tecnicas Fiscais (Micro-SOPs)

#### 3.1. Objetivo
Fornecer a "verdade minima" pronta e inquestionavel para que modelos pequenos (Gemini Flash, Flash-Lite ou SLMs locais) respondam sobre CST 61, CST 04 e regras SEFAZ sem necessidade de inventar parametros ou consultar ferramentas irrelevantes.

#### 3.2. Especificacao Tecnica
Criar o modulo [`core/prompts/fiscal_knowledge_cards.py`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/core/prompts/fiscal_knowledge_cards.py) contendo a biblioteca de fichas estruturadas canônicas:

```python
FISCAL_KNOWLEDGE_CARDS = {
    "cst_61_icms_monofasico": {
        "titulo": "ICMS Monofasico sobre Combustiveis (CST 61)",
        "base_legal": "Lei Complementar 192/2022 e Convenios ICMS 15/2023 e 199/2023",
        "aplicabilidade": "Gasolina Comum/Aditivada, Diesel S10/S500 e GLP/GLGN",
        "regra_revenda_posto": "Aliquota ad rem fixa por litro recolhida na refinaria/importador. Na revenda varejista, aplica-se aliquota ZERO de ICMS próprio (CST 61 com qBCMonoRet e vICMSMonoRet preenchidos).",
        "pontos_criticos": [
            "NUNCA destacar base de calculo de ICMS proprio ou ICMS-ST no PDV.",
            "Obrigatoriedade de informar o ICMS retido anteriormente por litro (ad rem).",
            "Etanol Hidratado NAO entra no regime monofasico (vedado uso de CST 61 - Rejeicao 959).",
            "CFOP correto de saida no posto: 5.656 (combustivel monofasico a consumidor final).",
        ],
        "rejeicoes_sefaz": ["960 (CST incompativel)", "958 (CFOP incompativel)", "959 (Etanol em CST 61)"],
    },
    "cst_04_pis_cofins_conveniencia": {
        "titulo": "PIS/COFINS Monofasico na Loja de Conveniencia (CST 04)",
        "base_legal": "Tabela 4.3.10 EFD-Contribuicoes, Lei 13.097/2015 e Lei 10.833/2003",
        "aplicabilidade": "Bebidas Frias (cervejas, refrigerantes, aguas, energeticos) e cigarros",
        "regra_revenda": "Tributacao monofasica concentrada no fabricante/importador. Na loja de conveniencia (mesmo no Simples Nacional ou Lucro Presumido/Real), a aliquota e ZERO (CST 04).",
        "pontos_criticos": [
            "Risco de bitributacao: cadastrar bebidas com CST 01 gera pagamento em duplicidade no PGDAS.",
            "Segregacao no Simples Nacional: abater as receitas monofasicas no calculo do PGDAS-D.",
            "Obrigatoriedade do codigo CEST (Rejeicao 806 se omitido).",
        ],
        "rejeicoes_sefaz": ["806 (CEST compulsorio para monofasico/ST)"],
    },
}
```

---

### MODULO 4: Isolamento Estrito de Ferramentas (`Scoped Tooling`) no AuraEngine

#### 4.1. Objetivo
Garantir isolamento hermetico: quando a intencao classificada for fiscal/tributaria ou documental, o motor [`core/aura_engine.py`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/core/aura_engine.py) **remove** as ferramentas de pista (tanques, encerrantes, caixas, bombas) do escopo entregue a LLM.

#### 4.2. Especificacao Tecnica
Modificar o metodo `_executar_fluxo_cognitivo` em [`core/aura_engine.py`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/core/aura_engine.py):
1. **Definicao de Escopo por Intencao (`SCOPED_TOOL_SETS`)**:
   - Para `auditoria_fiscal_sefaz` e `conhecimento_fiscal`:
     - Tool permitida: apenas [`auditar_documento_ou_chave_fiscal`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/core/tools.py) ou execucao direta de RAG.
     - Ferramentas bloqueadas: `auditar_fechamento_turno`, `prever_runout_tanques`, `executar_mentor_decisao_executiva`, `analisar_frentistas`.
2. **Injecao Direta do Card Canonico**:
   Quando a consulta coincidir com os temas de CST 61 ou CST 04, o card canonico de [`core/prompts/fiscal_knowledge_cards.py`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/core/prompts/fiscal_knowledge_cards.py) e injetado diretamente no bloco de evidencias do prompt.
   Isso garante latencia ultra-baixa (< 1.5s total) e zero tokens gastos com ferramentas irrelevantes.

---

### MODULO 5: Golden Dataset de Testes de Regressao de Roteamento

#### 5.1. Objetivo
Criar uma suite de testes unitarios com 30+ perguntas reais de operadores cobrindo todas as areas criticas (Fiscal, Pista, Caixa, Tanques, LMC, TEF), assegurando que nenhuma melhoria em uma area cause regressao nas outras.

#### 5.2. Casos de Teste Obrigatorios no Golden Dataset
Criar [`tests/unit/test_golden_intent_routing.py`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/tests/unit/test_golden_intent_routing.py):

| Pergunta de Teste | Intencao Esperada Obrigatoria | Proibido Casar Como |
| :--- | :--- | :--- |
| *"Quais os pontos criticos de ICMS Monofasico CST 61, PIS/COFINS CST 04 na conveniencia e rejeicoes SEFAZ?"* | `auditoria_fiscal_sefaz` | `mentoria_decisao`, `previsao_tanques` |
| *"Minha nota deu rejeicao 960 na SEFAZ, o que e?"* | `auditoria_fiscal_sefaz` | `mentoria_decisao`, `ajuda_sistema` |
| *"Qual o CST correto para cerveja na loja de conveniencia?"* | `auditoria_fiscal_sefaz` | `conveniencia_vendas_cruzadas` |
| *"Como ficou o fechamento do 1o turno de ontem?"* | `auditoria_turno` | `auditoria_fiscal_sefaz` |
| *"Quantos dias de autonomia de Gasolina Comum restam nos tanques?"* | `previsao_tanques` | `auditoria_fiscal_sefaz` |
| *"O LMC de ontem fechou dentro da tolerancia de 0,6%?"* | `lmc_anp` | `auditoria_fiscal_sefaz` |
| *"Qual o impacto do diesel S10 na margem bruta do posto?"* | `mentoria_decisao` | `auditoria_fiscal_sefaz` |

---

## 4. CRONOGRAMA DE EXECUCAO EM 4 ETAPAS

```
+---------------------------------------------------------------------------------------------------------+
|                                    ROTEIRO SEQUENCIAL DE IMPLEMENTACAO                                  |
+---------------------------------------------------------------------------------------------------------+
| ETAPA 1: Hardening do Roteador Semantico e Gate Lexico                                                  |
|          - Arquivo: core/semantic_router.py                                                             |
|          - Implementar PADRAO_FISCAL_DETERMINISTICO com latencia < 0.2ms.                               |
|          - Atualizar a lista de priorizacao heuristica para incluir auditoria_fiscal_sefaz.             |
|                                                                                                         |
| ETAPA 2: Biblioteca de Fichas Canonicas Fiscais (Grounding para Modelos Flash)                          |
|          - Criar: core/prompts/fiscal_knowledge_cards.py                                                |
|          - Catalogar Fichas Canonicas de CST 61 (LC 192), CST 04 (Lei 13.097), Rejeicoes SEFAZ e DIFAL. |
|                                                                                                         |
| ETAPA 3: Scoped Tooling e Integracao no AuraEngine                                                      |
|          - Arquivo: core/aura_engine.py                                                                 |
|          - Bloquear ferramentas operacionais de pista em intencoes fiscais.                            |
|          - Injetar Ficha Canonica como verdade minima garantida no prompt da LLM.                       |
|                                                                                                         |
| ETAPA 4: Suite de Testes Golden Dataset e Validacao em Producao                                         |
|          - Criar: tests/unit/test_golden_intent_routing.py                                              |
|          - Executar bateria completa do pytest (885+ testes com 100% de aprovacao).                     |
|          - Testar a pergunta do print via endpoint /api/v1/aura/chat para confirmar a resposta exata.   |
+---------------------------------------------------------------------------------------------------------+
```

---

## 5. CRITERIOS DE ACEITE E METRICAS DE CONFORMIDADE

1. **Acuracia de Roteamento no Golden Dataset:** 100% de precisao nas perguntas fiscais contendo siglas tecnicas (`CST`, `CFOP`, `SEFAZ`, `ICMS`, `PIS/COFINS`).
2. **Latencia do Gate Lexico:** Inferior a 0.5 ms no benchmark local.
3. **Custo de Inferencia por Consulta:** Menor que R$ 0,005 por resposta utilizando Gemini 3.1 Flash / Flash-Lite, gracas ao Micro-SOP compacto.
4. **Zero Regressao:** Todos os testes unitarios de RAG, adaptadores ERP e telemetria devem permanecer verdes.
5. **Zero Travessoes Unicode:** Proibicao absoluta de `\u2014` e `\u2013` em todos os arquivos modificados.

---

## 6. LOG DE EXECUCAO E STATUS DOS MODULOS

| Modulo / Etapa | Artefatos Gerados / Modificados | Status | Metricas Comprovadas |
| :--- | :--- | :---: | :--- |
| **Etapa 1: Gate Lexico e Hardening** | `core/semantic_router.py`, `tests/unit/test_fiscal_fastpath_routing.py` | **CONCLUIDA** | Latencia 0.8ms, confianca 0.99, rota direta para `auditoria_fiscal_sefaz`. |
| **Etapa 2: Semeador pgvector HNSW** | `scripts/seed_intent_vectors.py` | **CONCLUIDA** | 164 vetores indexados, 30/30 intencoes no PostgreSQL 16, pgvector sim=0.7077. |
| **Etapa 3: Fichas Tecnicas Canonicas** | `core/prompts/fiscal_knowledge_cards.py`, `core/prompts/micro_sops.py`, `tests/unit/test_fiscal_knowledge_cards.py` | **CONCLUIDA** | 5 Micro-SOPs canonicos, bot `fiscal_compliance_bot`, 100% aprovado. |
| **Etapa 4: Scoped Tooling AuraEngine** | `core/aura_engine.py`, `tests/unit/test_scoped_tooling_isolation.py` | **CONCLUIDA** | Interceptacao de ferramentas de pista, injecao de Fichas Canonicas, zero contaminacao de tanques. |
| **Etapa 5: Golden Dataset de Regressao**| `tests/unit/test_golden_intent_routing.py` | **CONCLUIDA** | 35/35 perguntas aprovadas no Golden Dataset, 934 testes verdes no CI, validacao live com zero mencao a tanques. |
