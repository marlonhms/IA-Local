# ROADMAP OFICIAL DE ENGENHARIA: HUB DE INTEGRAÇÃO DE APIS E DADOS PÚBLICOS DA AURA
## Enriquecimento Cognitivo de Borda: ANP, CONFAZ/SEFAZ, INMETRO e BACEN (Offline-First)

> **Documento de Engenharia & Especificação Técnica de Arquitetura (RFC)**  
> **Versão:** 1.1.0-PRO  
> **Data de Emissão:** Outubro de 2026  
> **Status:** [HOMOLOGADO EM PRODUÇÃO - 100% CONCLUÍDO]  
> **Classificação:** Arquitetura de Borda (Edge AI) / Clean Room / Dados Abertos Governamentais  
> **Repositório:** [`ia-banco-local`](./)  
> **Arquivos Relacionados do Repositório:**  
> - [`core/rag_engine.py`](./core/rag_engine.py)  
> - [`core/proactive_daemon.py`](./core/proactive_daemon.py)  
> - [`core/tools.py`](./core/tools.py)  
> - [`core/schemas/genui.py`](./core/schemas/genui.py)  
> - [`core/schemas/lmc_report.py`](./core/schemas/lmc_report.py)  
> - [`core/schemas/reconciliation.py`](./core/schemas/reconciliation.py)  
> - [`scripts/init_posto_database.py`](./scripts/init_posto_database.py)  
> - [`scripts/seed_aura_conhecimento.py`](./scripts/seed_aura_conhecimento.py)  
> - [`scripts/sync_public_data.py`](./scripts/sync_public_data.py)  
> - [`core/integrations/public_data/`](./core/integrations/public_data/)  
> - [`tests/unit/test_public_data_connectors.py`](./tests/unit/test_public_data_connectors.py)  
> - [`tests/unit/test_benchmark_comparativo.py`](./tests/unit/test_benchmark_comparativo.py)  
> - [`web/js/aura-genui-widgets.js`](./web/js/aura-genui-widgets.js)  

---

## 📌 1. Visão Geral, Princípios de Borda e Blindagem LGPD

### 1.1 Contexto e Justificativa Estratégica de Negócio
O ecossistema AURA opera como um copiloto autônomo de inteligência operacional de pista e conveniência instalado diretamente na borda (edge computing no servidor local do posto revendedor). Até o presente estágio, as ferramentas analíticas da AURA extraem inteligência exclusivamente dos dados internos da empresa: movimentações de caixa, encerramentos de turno, medição física de tanques, concentradores Companytec e cupons fiscais emitidos pelo ERP.

No entanto, o negócio de revenda de combustíveis no Brasil é profundamente influenciado por quatro vetores externos:
1. **Concorrência Local Intensa:** Variações diárias e semanais de preços na mesma microrregião, bairro e município;
2. **Regulamentação e Fiscalização Rigorosa:** Normas da ANP sobre limites de perdas e sobras no LMC e tolerâncias do INMETRO sobre aferição volumétrica de bicos medidores;
3. **Complexidade Tributária (ICMS-ST e ICMS Monofásico):** Pautas fiscais do CONFAZ (PMPF) e Atos COTEPE que determinam a carga tributária efetiva e oportunidades de restituição ou complementação;
4. **Custo Financeiro do Capital de Giro:** Estoques subterrâneos de alta liquidez e expressivo valor monetário (50.000 a 150.000 litros) sensíveis à taxa Selic, inflação (IPCA) e paridade internacional de importação via câmbio PTAX.

A integração de dados públicos governamentais abertos transformará a AURA em um oráculo estratégico contextualizado: a IA deixará de apenas constatar "você vendeu Gasolina Comum por R$ 5,89 com margem de R$ 0,42" e passará a orientar proativamente "o seu preço de bomba está R$ 0,11 acima da média do seu bairro segundo a última coleta ANP, o ICMS-ST recolhido está defasado em relação ao Ato COTEPE vigente e o custo financeiro Selic de carregamento do estoque sugere recompra em 36 horas".

### 1.2 Os 4 Pilares de Dados Públicos Integrados
O ecossistema público mapeado é composto por quatro fontes governamentais primárias:
* **ANP (Agência Nacional do Petróleo, Gás Natural e Biocombustíveis):**
  - **Série Semanal de Preços de Combustíveis:** Coleta semanal de preços de revenda e distribuição por município, bairro, produto (Gasolina Comum, Gasolina Aditivada, Etanol Hidratado, Diesel S10, Diesel S500, GNV) e distribuidora/bandeira, disponibilizada via Portal de Dados Abertos do Governo Federal (CKAN API / CSV).
  - **Base Cadastral de Revendedores (SICOP / Painel Dinâmico de Postos):** Relação completa de postos revendedores autorizados com CNPJ, razão social, nome fantasia, endereço, bairro, bandeira cadastrada e capacidade total de tancagem instalada.
* **CONFAZ / SEFAZ:**
  - **Atos COTEPE e Tabelas PMPF (Preço Médio Ponderado ao Consumidor Final):** Publicações quinzenais no Diário Oficial da União que fixam os valores de referência do PMPF para cálculo do ICMS por Substituição Tributária (ICMS-ST) em combustíveis não sujeitos à tributação monofásica pura (como Etanol Hidratado e GNV), permitindo auditoria de conformidade tributária e identificação de crédito de ressarcimento (Tema 201 STF).
* **INMETRO:**
  - **Portaria INMETRO nº 559/2016 e Regulamento Técnico Metrológico (RTM):** Critérios e tolerâncias metrológicas legais de bombas medidoras de combustíveis líquidos. Estabelece a tolerância máxima admissível de ±100 ml para cada ensaio volumétrico de 20 litros (tolerância relativa de ±0,50%), regras de ensaio de vazão nominal e reduzida, e parâmetros de auditoria de aferição física na pista sem cupom fiscal de venda.
* **BACEN (Banco Central do Brasil):**
  - **API SGS (Sistema Gerenciador de Séries Temporais):** Séries macroeconômicas diárias e mensais em formato JSON oficial:
    - Série 11: Taxa Selic diária acumulada no mês anualizada base 252;
    - Série 432: Meta da taxa Selic definida pelo COPOM (% ao ano);
    - Série 1: Taxa de câmbio PTAX dólar americano comercial (venda e compra);
    - Série 433: IPCA mensal (Índice Nacional de Preços ao Consumidor Amplo);
    - Série 189: IGP-M mensal.

### 1.3 Princípios de Engenharia de Borda (Edge Architecture)
A implementação do Hub de Dados Públicos obedece estritamente aos princípios de engenharia de missão crítica da AURA:

1. **Offline-First Absoluto (Zero Dependência Síncrona de Rede):**
   - O Core cognitivo da AURA, as ferramentas de inferência ([`core/tools.py`](./core/tools.py)), os endpoints da API ([`core/aura_api.py`](./core/aura_api.py)) e a interface gráfica GenUI jamais executam requisições HTTP externas no caminho síncrono do usuário.
   - Toda consulta analítica sobre médias de preços da ANP, pautas do CONFAZ ou taxas do BACEN consome exclusivamente tabelas de cache relacional locais no PostgreSQL (`posto_ai:5433`).
   - Se o link de internet do posto for interrompido por intempéries ou falhas de operadora, a AURA continua operando sem qualquer degradação funcional, utilizando o último snapshot sincronizado e informando a data/hora da base de referência no badge visual.
2. **Zero Disruption no ERP e nos Recursos da Estação:**
   - O processo de sincronização e download de arquivos externos é executado em segundo plano por workers desacoplados, fora dos horários de pico de pista (privilegiando horários noturnos e de baixa concorrência de I/O).
   - O consumo de memória RAM do sincronizador é estritamente limitado (processamento em streaming de CSVs em chunks de 64 KB via iteradores geradores, com teto rígido de 80 MB de memória RAM).
3. **Cache Relacional Local Estruturado:**
   - Os dados normalizados são persistidos no schema dedicado `aura_core` do banco local, indexados estrategicamente por município, UF, produto e data para garantir tempos de resposta de consulta sub-10ms no banco e sub-100ms na inferência da IA.
4. **Idempotência e Resiliência a Falhas:**
   - A ingestão utiliza comandos declarativos com cláusula `ON CONFLICT (chave_primaria) DO UPDATE` (upsert), garantindo que execuções parciais, quedas de energia no meio do download ou repetições de lote jamais gerem duplicações ou corrupção de dados.

### 1.4 Blindagem LGPD e Unidirecionalidade Estrita
O aspecto de segurança jurídica e proteção de dados é um requisito inegociável do projeto:

* **Fluxo 100% Unidirecional (Apenas Dados Públicos Entram):**
  - A comunicação com os serviços governamentais é estritamente receptiva (Inbound): a AURA apenas faz download de conjuntos de dados que já são de domínio público.
  - As requisições HTTP aos endpoints da ANP, CKAN, CONFAZ e BACEN utilizam chamadas padronizadas sem envio de cabeçalhos identificadores do posto, sem cookies rastreáveis, sem envio de CNPJ, sem telemetria da pista e sem transmissão de dados do cliente.
* **Zero Exfiltração de Dados Privados:**
  - Nenhum cupom fiscal, CPF de consumidor, faturamento do posto, margem real, volume de vendas, estoque medido ou dado pessoal de operador de caixa sai da rede local do posto em direção a qualquer serviço público ou servidor central.
  - Toda a inteligência competitiva e auditoria tributária é computada **localmente na máquina do posto**: a AURA cruza os dados privados locais do ERP com o cache público local, sem que nenhum terceiro tenha ciência do resultado da análise.

### 1.5 Diagrama Conceitual de Fluxo e Segurança Unidirecional

```
+────────────────────────────────────────────────────────────────────────+
│                      FONTES PÚBLICAS GOVERNAMENTAIS                    │
│   [ANP: Preços e SICOP]  [CONFAZ: PMPF COTEPE]  [BACEN: SGS Séries]    │
+───────────────────────────────────┬────────────────────────────────────+
                                    │
                       Download Unidirecional (GET)
                    Sem Autenticação Privada, Sem PII
                                    │
                                    ▼
+────────────────────────────────────────────────────────────────────────+
│             AURA SYNC WORKER (scripts/sync_public_data.py)             │
│        • Rate Limiting & Circuit Breaker                               │
│        • Validação Pydantic dos Modelos Canônicos                      │
│        • Sanitização e Parsing em Streaming (Baixo I/O)                │
+───────────────────────────────────┬────────────────────────────────────+
                                    │
                         Upsert Idempotente Local
                                    │
                                    ▼
+────────────────────────────────────────────────────────────────────────+
│              POSTGRESQL LOCAL DE BORDA (posto_ai:5433)                 │
│                                                                        │
│   Schema: aura_core                                                    │
│   ├── public_fuel_prices         (Preços Médios ANP por Município)     │
│   ├── public_dealers_registry    (Cadastro Geral de Concorrentes)      │
│   ├── public_tax_pmpf            (PMPF e Alíquotas CONFAZ/SEFAZ)       │
│   ├── public_macro_indicators    (Selic, PTAX, IPCA BACEN)             │
│   └── aura_conhecimento_vetores  (RAG Vetorial de Legislação ANP/INM)  │
+───────────────────────────────────┬────────────────────────────────────+
                                    │
                        Consultas SQL Sub-10ms (Local)
                                    │
                                    ▼
+────────────────────────────────────────────────────────────────────────+
│                   AURA COGNITIVE ENGINE & POSTO TOOLS                  │
│       • PostoTools.comparar_benchmark_concorrencia()                   │
│       • PostoTools.auditar_conformidade_lmc_anp()                      │
│       • Conciliação de Bombas com Tolerância INMETRO 559/2016          │
│       • Análise de Custo de Oportunidade de Estoque Selic              │
+───────────────────────────────────┬────────────────────────────────────+
                                    │
                         Payload GenUI Desacoplado
                                    │
                                    ▼
+────────────────────────────────────────────────────────────────────────+
│                     FRONTEND / OPERAÇÃO DO POSTO                       │
│    [BenchmarkComparisonUI]   [ShiftReconciliationUI]   [LMCReport]     │
│                     (Tempo de Resposta: < 100ms)                       │
+────────────────────────────────────────────────────────────────────────+
```

---

## 🧭 2. Arquitetura Geral do Hub de Dados Públicos

### 2.1 Visão em Camadas
O Hub de Dados Públicos está estruturado em quatro camadas estritamente desacopladas:

1. **Camada de Conectores Externos ([`core/integrations/public_data/`](./core/integrations/public_data/)):**
   - Módulos adaptadores responsáveis por interagir com os protocolos específicos de cada fonte governamental (REST/JSON para BACEN SGS, CKAN API / CSV para ANP, extração tabular estruturada para CONFAZ).
   - Isolamento total da rede externa: nenhuma outra camada do sistema possui permissão para invocar clientes HTTP diretamente.
2. **Camada de Domínio Canônico Universal (`core/domain/public_data.py`):**
   - Entidades Pydantic v2 imutáveis (`frozen=True`) que representam as informações públicas limpas, tipadas e validadas, independentes da forma física dos arquivos originais.
3. **Camada de Persistência e Cache Relacional (`aura_core.public_*`):**
   - Tabelas locais no banco PostgreSQL da estação com chaves primárias compostas determinísticas, garantindo versionamento temporal das séries e buscas instantâneas.
4. **Camada de Consumo Analítico ([`core/tools.py`](./core/tools.py) e [`core/rag_engine.py`](./core/rag_engine.py)):**
   - Funções analíticas de alto nível que cruzam os dados do ERP local com as tabelas de cache público para gerar diagnósticos preditivos e contratos GenUI.

### 2.2 Matriz de Fontes, Protocolos, Periodicidade e Destino

| Fonte Governamental | Dados Coletados | Protocolo / Formato | Periodicidade de Publicação | Frequência de Sincronização Local | Tabela Destino Local |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **ANP: Dados Abertos** | Preços de revenda e distribuição por município, bairro e produto | CKAN REST API / CSV compactado (dados.gov.br) | Semanal (toda segunda-feira) | Semanal (terças-feiras às 03:00) | `aura_core.public_fuel_prices` |
| **ANP: SICOP** | Cadastro de postos revendedores, localização, bandeira e tanques | Painel Dinâmico / CSV público | Mensal | Mensal (dia 05 às 03:30) | `aura_core.public_dealers_registry` |
| **CONFAZ / SEFAZ** | Atos COTEPE, PMPF de ICMS-ST e alíquotas estaduais | Portal CONFAZ / DOU (JSON / CSV tabular) | Quinzenal (dias 01 e 16) | Quinzenal (dias 02 e 17 às 04:00) | `aura_core.public_tax_pmpf` |
| **BACEN: SGS** | Taxa Selic (Séries 11 e 432), Dólar PTAX (Série 1), IPCA (Série 433) | REST API JSON oficial | Diária (dias úteis às 18:30) | Diária (segunda a sexta às 06:30) | `aura_core.public_macro_indicators` |
| **INMETRO & ANP RAG** | Portaria 559/2016, Portaria 26/1992, Resolução 894/2022 | Texto normativo oficial consolidado | Eventual (atualização regulatória) | Ingestão única com atualização sob demanda | `aura_core.aura_conhecimento_vetores` |

---

## 📚 3. Fase 1: Ingestão de Legislação e Normas Técnicas no RAG Local

### 3.1 Corpus Normativo Selecionado
A AURA deve possuir conhecimento nativo e instantâneo sobre as regras que regem a fiscalização e a operação metrológica e fiscal de um posto revendedor. A primeira fase do projeto foca na ingestão desse corpus no mecanismo de Hybrid RAG da AURA ([`core/rag_engine.py`](./core/rag_engine.py)), indexando-o na tabela `aura_core.aura_conhecimento_vetores`.

O acervo compreende:
1. **Portaria ANP nº 26/1992:**
   - Criação e obrigatoriedade da escrituração diária do Livro de Movimentação de Combustíveis (LMC).
   - Definição do prazo legal de lançamento diário (fechamento de estoques e vendas nas 24 horas seguintes).
   - Fixação do limite de perda ou sobra física tolerada de até **0,6% (zero vírgula seis por cento)** do volume movimentado no mês, calculado pela fórmula:
     `Variacao_Percentual = (Estoque_Fisico_Final - Estoque_Contabil_Final) / Total_Saidas * 100`
   - Procedimentos de comprovação técnica para justificar variações anormais (vazamento, evaporação térmica ou calibração).
2. **Resolução ANP nº 894/2022:**
   - Atualização e consolidação das regras de operação e fiscalização de postos revendedores de combustíveis.
   - Especificação de procedimentos de exibição de preços, direitos do consumidor, regras de funcionamento dos bicos e manutenção dos registros cadastrais e notas fiscais de entrada.
3. **Portaria INMETRO nº 559/2016 (e Regulamento Técnico Metrológico: RTM):**
   - Tolerâncias metrológicas de bombas medidoras de combustíveis líquidos:
     - Erro máximo admissível (EMA) em ensaios de vazão: **±100 ml para uma amostra de 20 litros** (ou seja, erro relativo de **±0,50%**).
     - Procedimentos para ensaio em vazão nominal (alta vazão, operação normal de abastecimento) e ensaio em vazão reduzida (baixa vazão, operação com gatilho travado no primeiro estágio).
     - Obrigatoriedade de aferição no início de cada turno utilizando medida de volume padrão de 20 litros aferida e lacrada pelo IPEM/INMETRO.
     - Registro contábil e operacional do retorno do combustível aferido ao respectivo tanque de armazenamento sem emissão de cupom fiscal de venda.
4. **Legislação Tributária de Combustíveis (CONFAZ e Emenda Constitucional):**
   - Distinção entre o regime de **ICMS Monofásico** (definido pela Lei Complementar nº 192/2022 com alíquotas fixas ad rem em R$/litro para Óleo Diesel, Biodiesel e GLP) e o regime de **ICMS Substituição Tributária (ICMS-ST com PMPF)** para Etanol Hidratado e GNV.
   - Normas para apuração de crédito e ressarcimento de ICMS quando a base de cálculo presumida for superior ao preço final efetivamente praticado ao consumidor na bomba (STF Tema 201).
5. **Diretrizes BACEN e Governança Financeira de Estoque:**
   - Metodologia de cálculo do Custo de Carregamento de Estoque (Carrying Cost) baseado na Taxa Selic sobre o volume total tancado.
   - Cálculo do ponto ótimo de compra de combustível (Economic Order Quantity adaptado para compartimentos padrão de 5.000 litros).

### 3.2 Estratégia de Chunking e Enriquecimento Semântico
Para garantir que o mecanismo de busca híbrida da AURA ([`HybridRAGEngine`](./core/rag_engine.py)) encontre com exatidão a resposta em menos de 5ms, os textos normativos serão decompostos em chunks semânticos atômicos com os seguintes atributos:
* **Tamanho do Chunk:** Entre 150 e 350 palavras, focados em uma única regra de negócio prática.
* **Metadados Estruturados:** Módulo (`legislacao_posto`), Tópico (`anp_lmc`, `inmetro_bombas`, `tributario_icms`, `bacen_financeiro`), Título curto e descritivo, Subtítulo contextual.
* **Tags Normativas:** Palavras-chave técnicas em português (`["LMC", "ANP 26/1992", "tolerancia 0.6%", "perda tanque", "sobra fisica"]`).
* **Elementos de UI e UI Actions:** Vínculos declarativos com os micro-widgets da AURA (`render_LMCReport`, `render_ShiftReconciliationUI`, `render_BenchmarkComparisonUI`).
* **Vetorização Densa:** Embeddings gerados com dimensões canônicas de 768d no tipo `halfvec` do PostgreSQL, indexados via HNSW com operadores de similaridade de cosseno (`halfvec_cosine_ops`).

### 3.3 DDL Declarativo Completo no pgvector (`aura_core.aura_conhecimento_vetores`)
A estrutura da tabela vetorial já está provisionada no banco convergente `posto_ai:5433` pelo script [`scripts/init_posto_database.py`](./scripts/init_posto_database.py). Abaixo o DDL declarativo completo, incluindo a coluna gerada `tsv` e índices HNSW e GIN:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS aura_core;

CREATE TABLE IF NOT EXISTS aura_core.aura_conhecimento_vetores (
    id SERIAL PRIMARY KEY,
    modulo VARCHAR(50) NOT NULL,
    topico VARCHAR(100) NOT NULL,
    titulo VARCHAR(150) NOT NULL,
    subtitulo VARCHAR(255),
    conteudo TEXT NOT NULL,
    elementos_ui JSONB,
    ui_action JSONB,
    tags TEXT[],
    embedding halfvec(768),
    hash_md5 VARCHAR(32),
    criado_em TIMESTAMP DEFAULT NOW(),
    tsv tsvector GENERATED ALWAYS AS (
        to_tsvector('portuguese'::regconfig,
            coalesce(titulo, '') || ' ' ||
            coalesce(subtitulo, '') || ' ' ||
            coalesce(modulo, '') || ' ' ||
            coalesce(topico, '') || ' ' ||
            coalesce(conteudo, '')
        )
    ) STORED,
    CONSTRAINT uq_aura_conhecimento_modulo_topico UNIQUE (modulo, topico)
);

CREATE INDEX IF NOT EXISTS idx_aura_core_conhecimento_vetores_hnsw
ON aura_core.aura_conhecimento_vetores
USING hnsw (embedding halfvec_cosine_ops)
WITH (m = 24, ef_construction = 128);

CREATE INDEX IF NOT EXISTS idx_aura_core_conhecimento_vetores_tsv
ON aura_core.aura_conhecimento_vetores USING gin (tsv);

CREATE INDEX IF NOT EXISTS idx_aura_core_conhecimento_modulo_topico
ON aura_core.aura_conhecimento_vetores (modulo, topico);
```

### 3.4 Catálogo de Chunks Normativos Estruturados (10 Chunks Canônicos)
A tabela a seguir define a carga inicial que será inserida via script de seed:

| ID Ref | Módulo | Tópico | Título | Conteúdo Sintetizado | UI Component / Ação |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **RAG-PUB-01** | `legislacao_posto` | `anp_lmc` | Tolerância Legal de Perdas e Sobras no LMC (0,6%) | A Portaria ANP nº 26/1992 estabelece que a variação volumétrica entre o estoque físico e o contábil não pode exceder 0,6% do total de saídas no mês. Variações superiores a 0,6% exigem sindicância interna, vistoria física e verificação de calibração metrológica. | `render_LMCReport` / Auditoria de Tanque |
| **RAG-PUB-02** | `legislacao_posto` | `anp_lmc` | Obrigatoriedade de Escrituração Diária do LMC | Conforme Resolução ANP 894/2022 e Portaria 26/1992, o LMC deve ser escriturado diariamente pelo posto até o encerramento do dia útil seguinte, registrando estoques iniciais, notas de compra, encerrantes e estoque final. A ausência de escrituração gera notificação e multa grave. | `render_LMCReport` / Fechamento Diário |
| **RAG-PUB-03** | `legislacao_posto` | `inmetro_bombas` | Tolerância Metrológica de Bombas (±100 ml em 20 Litros) | A Portaria INMETRO nº 559/2016 estipula que o Erro Máximo Admissível (EMA) nas bombas de combustíveis líquidos é de ±100 ml para cada 20 litros aferidos no balde padrão (erro relativo de ±0,5%). Diferenças maiores exigem interdição do bico e chamado de oficina autorizada IPEM. | `render_ShiftReconciliationUI` / Auditoria de Bico |
| **RAG-PUB-04** | `legislacao_posto` | `inmetro_bombas` | Regra de Aferição de Bicos e Retorno sem Venda Fiscal | Toda aferição de bico no início de turno deve ser efetuada com medida aferida de 20L e imediatamente despejada de volta no tanque de combustível de origem. O volume deve ser lançado no concentrador/ERP como aferição para abater do encerrante contábil sem emissão de cupom fiscal de venda. | `render_ShiftReconciliationUI` / Conciliação Turno |
| **RAG-PUB-05** | `legislacao_posto` | `inmetro_bombas` | Ensaio em Vazão Nominal vs Vazão Reduzida | O INMETRO exige que as bombas mantenham a precisão de ±100 ml tanto em vazão nominal (máxima vazão da pistola) quanto em vazão reduzida (gatilho estrangulado). Desvios em baixa vazão indicam desgaste do bloco medidor mecânico ou falha no pistão volumétrico. | `render_ShiftReconciliationUI` / Diagnóstico Metrológico |
| **RAG-PUB-06** | `legislacao_posto` | `tributario_icms` | Regime de ICMS Monofásico para Diesel e Biodiesel | A Lei Complementar nº 192/2022 estabeleceu a tributação monofásica do ICMS sobre Diesel, Biodiesel e GLP, com alíquota única nacional fixa em reais por litro (ad rem), recolhida na refinaria ou importador. O posto não calcula débito próprio de ICMS na venda de Diesel. | `render_MarginAnalysisUI` / Análise Tributária |
| **RAG-PUB-07** | `legislacao_posto` | `tributario_icms` | ICMS-ST com PMPF para Etanol Hidratado e GNV | O ICMS do Etanol e GNV permanece sob o regime de Substituição Tributária (ICMS-ST), onde o imposto é retido pela distribuidora com base no Preço Médio Ponderado ao Consumidor Final (PMPF) divulgado pelo CONFAZ em Atos COTEPE. | `render_MarginAnalysisUI` / Auditoria PMPF |
| **RAG-PUB-08** | `legislacao_posto` | `tributario_icms` | Restituição e Complementação de ICMS-ST | Se o posto vender o combustível por preço inferior ao PMPF fixado pelo CONFAZ, o revendedor tem direito de pleitear restituição do ICMS recolhido a maior junto à SEFAZ estadual (jurisprudência consolidada STF Tema 201). Se vender acima, pode haver complementação conforme estado. | `render_ExecutiveDecisionUI` / Oportunidade Fiscal |
| **RAG-PUB-09** | `macroeconomia` | `bacen_financeiro` | Custo de Oportunidade Selic em Estoques de Combustíveis | O capital imobilizado em estoques subterrâneos possui um custo diário equivalente à taxa Selic. A fórmula de custo de carregamento é: Volume * Custo_Unitario * (Selic_Anual / 252) * Dias_Estoque. Evitar estoques excessivos em períodos de taxa Selic alta maximiza o fluxo de caixa livre. | `render_PredictiveScenarioUI` / Otimização de Compras |
| **RAG-PUB-10** | `macroeconomia` | `bacen_financeiro` | Paridade de Importação e Sensibilidade ao Câmbio PTAX | O preço de refinaria dos combustíveis no Brasil acompanha a paridade internacional do petróleo Brent e a cotação do Dólar PTAX divulgada pelo BACEN. Flutuações acumuladas de câmbio superiores a 3% antecipam reajustes de preço da Petrobras em um horizonte de 7 a 14 dias. | `render_BenchmarkComparisonUI` / Projeção de Mercado |

### 3.5 Procedimento de Seed e Busca Híbrida RRF
A carga será adicionada ao arquivo [`scripts/seed_aura_conhecimento.py`](./scripts/seed_aura_conhecimento.py) de forma idempotente via delta hashing MD5 (`ON CONFLICT (modulo, topico) DO UPDATE`).
A recuperação das normas em tempo de execução utiliza o método [`HybridRAGEngine.search_hybrid_conhecimento()`](./core/rag_engine.py):

```python
# Invocação nativa da busca híbrida de legislação
resultado_rag = rag_engine.search_hybrid_conhecimento(
    query_text="tolerancia variacao estoque LMC ANP 0.6%",
    top_k=2,
    dense_weight=0.5,
    sparse_weight=0.5,
)
```

O método combina o ranking vetorial HNSW (`dense_rank`) com a busca textual exata em português (`sparse_rank` via `ts_rank_cd`), aplicando Reciprocal Rank Fusion com `k = 60` para garantir resposta em menos de 5ms no PostgreSQL local.

### 3.6 Checklist de Execucao e Homologacao da Fase 1 (Concluida em 19/10/2026)
- [x] **Ingestao Canonica e Metadados:** Ingestao de 11 chunks normativos e macroeconomicos canonicos (ANP, INMETRO, CONFAZ, BACEN) em [`scripts/seed_aura_conhecimento.py`](./scripts/seed_aura_conhecimento.py) totalizando 26 chunks no catalogo com metadados estruturados (orgao emissor, norma, tolerancia numerica, protocolo de recusa de combustivel fora de especificacao, ensaios de vazao nominal/reduzida e tela de aplicacao).
- [x] **DDL Idempotente e Compatibilidade Multi-Schema:** Correcao e extensao DDL para os schemas `aura_core` e `public` com colunas `metadados JSONB`, `hash_md5 VARCHAR(32)`, coluna gerada `tsv tsvector GENERATED ALWAYS AS (...) STORED` e restricao de unicidade `(modulo, topico)`.
- [x] **Fallback Deterministico e Resiliencia Offline:** Funcao `gerar_embedding_deterministico` com hashing SHA-256 e normalizacao L2 suportando 768d e 1536d, garantindo execucao hermetica mesmo sem API externa de embeddings ativa.
- [x] **Evolucao do Motor RAG:** Atualizacao de [`HybridRAGEngine.search_hybrid_conhecimento()`](./core/rag_engine.py) com recuperacao de metadados estruturados, correcao do fallback esparso em banco sem correspondencia e fallback transparente em memoria (`offline_memory_fallback`) caso a conexao com PostgreSQL local falhe.
- [x] **Suite de Testes Automatizados:** Implementacao de [`tests/unit/test_rag_normativo_publico.py`](./tests/unit/test_rag_normativo_publico.py) com 13 testes unitarios dedicados cobrindo integridade dos seeds, buscas hibridas e esparsas, tolerancia metrologica de bombas (±100 ml em 20L), limites de perdas LMC (0,60%), protocolo de recusa de combustivel adulterado, regras fiscais ICMS/PMPF, custo Selic e latencia sub-segundo.
- [x] **Homologacao e Analise Estatica:** 100% dos testes aprovados via pytest (22 testes verdes incluindo benchmark comparativo) e 100% de conformidade com ruff check sem advertencias.

---

## 🔌 4. Fase 2: Hub de Conectores de Dados Abertos (`core/integrations/public_data/`)

### 4.1 Arquitetura do Módulo e Árvore de Diretórios
A integração com fontes públicas será implementada no novo pacote modular sob [`core/integrations/public_data/`](./core/integrations/public_data/), respeitando os princípios de responsabilidade única e desacoplamento:

```
ia-banco-local/core/integrations/public_data/
├── __init__.py                    # Exportações públicas dos conectores e modelos
├── base.py                        # Classe abstrata BasePublicDataConnector e DTOs comuns
├── anp_connector.py               # Conector de Séries Semanais de Preços e Base SICOP da ANP
├── confaz_connector.py            # Conector de Atos COTEPE e Tabelas PMPF
├── bacen_connector.py             # Conector REST do Sistema de Séries Temporais (SGS) do BACEN
└── rate_limiter.py                # Utilitário de controle de vazão e Circuit Breaker
```

### 4.2 Contrato Abstrato Base (`core/integrations/public_data/base.py`)
```python
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class ConnectorHealthStatus(BaseModel):
    source_name: str
    is_healthy: bool
    last_sync_timestamp: Optional[datetime] = None
    response_latency_ms: float = 0.0
    error_message: Optional[str] = None

class ConnectorFetchResult(BaseModel):
    source_name: str
    records_count: int
    data_payload: List[BaseModel]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    execution_time_ms: float
    raw_hash_sha256: str

class BasePublicDataConnector(ABC):
    """Contrato base para adaptadores de dados governamentais públicos."""

    @abstractmethod
    def get_source_name(self) -> str:
        """Retorna o identificador único da fonte (ex: 'ANP_CKAN', 'BACEN_SGS')."""
        pass

    @abstractmethod
    def health_check(self) -> ConnectorHealthStatus:
        """Executa ping leve no endpoint público para verificar conectividade."""
        pass

    @abstractmethod
    def fetch_latest_data(self, since: Optional[datetime] = None, **kwargs) -> ConnectorFetchResult:
        """Coleta, valida e retorna os registros transformados em modelos canônicos."""
        pass
```

### 4.3 Conector ANP (`core/integrations/public_data/anp_connector.py`)
Responsável pela coleta de duas bases cruciais da Agência Nacional do Petróleo:

1. **Série Semanal de Preços de Combustíveis (CKAN API / CSV):**
   - **Origem:** Portal de Dados Abertos do Governo Federal (`https://dados.gov.br/dados/conjuntos-dados/serie-historica-de-precos-de-combustiveis-por-revenda`).
   - **Estratégia de Ingestão:**
     - Consulta à API CKAN (`/api/3/action/package_show?id=serie-historica-de-precos-de-combustiveis-por-revenda`) para descobrir a URL do arquivo CSV mais recente do semestre/ano corrente.
     - Download em streaming com chunk size de 64 KB e cálculo de hash SHA-256 em tempo real.
     - Detecção automática de encoding (`utf-8` ou `latin-1`) e delimitador (vírgula ou ponto-e-vírgula).
     - Filtragem precoce durante o parsing de linhas para descartar municípios não configurados para o posto corrente (economizando memória e CPU).
   - **Campos Mapeados:**
     `data_coleta`, `municipio`, `bairro`, `uf`, `produto`, `preco_venda`, `preco_compra`, `bandeira`, `razao_social`, `cnpj_revendedor`, `unidade_medida`.

2. **Base Cadastral SICOP de Revendedores:**
   - **Origem:** Painel Dinâmico de Postos Revendedores da ANP.
   - **Utilidade:** Permite identificar a quantidade de postos concorrentes ativos no mesmo município e bairro, capacidade total instalada de armazenagem e bandeiras atuantes.

#### Esqueleto Técnico do Conector ANP:
```python
from typing import Generator, Optional
from datetime import datetime
import csv
import io
import httpx
from core.integrations.public_data.base import BasePublicDataConnector, ConnectorHealthStatus, ConnectorFetchResult
from core.integrations.public_data.rate_limiter import PublicDataCircuitBreaker

class AnpPublicDataConnector(BasePublicDataConnector):
    """Conector resiliente para Séries de Preços e Base SICOP da ANP via CKAN."""

    def __init__(self, circuit_breaker: Optional[PublicDataCircuitBreaker] = None):
        self.cb = circuit_breaker or PublicDataCircuitBreaker(name="anp_ckan")
        self.ckan_base_url = "https://dados.gov.br/api/3/action"

    def get_source_name(self) -> str:
        return "ANP_CKAN"

    def health_check(self) -> ConnectorHealthStatus:
        t0 = datetime.now()
        try:
            with httpx.Client(timeout=5.0) as client:
                res = client.get(f"{self.ckan_base_url}/package_show?id=serie-historica-de-precos-de-combustiveis-por-revenda")
                latency = (datetime.now() - t0).total_seconds() * 1000
                return ConnectorHealthStatus(
                    source_name=self.get_source_name(),
                    is_healthy=(res.status_code == 200),
                    response_latency_ms=latency,
                    last_sync_timestamp=datetime.now(),
                )
        except Exception as exc:
            return ConnectorHealthStatus(
                source_name=self.get_source_name(),
                is_healthy=False,
                error_message=str(exc),
            )

    def stream_fuel_prices_csv(self, csv_url: str, target_municipio: Optional[str] = None) -> Generator[dict, None, None]:
        """Consome o CSV em streaming de 64 KB, filtrando linhas do município de interesse."""
        with httpx.stream("GET", csv_url, timeout=30.0) as response:
            response.raise_for_status()
            buffer = ""
            for chunk in response.iter_text():
                buffer += chunk
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    # Parsing de linha com filtro municipal antecipado
                    parts = line.split(";")
                    if len(parts) >= 10:
                        municipio_linha = parts[1].strip().upper()
                        if not target_municipio or municipio_linha == target_municipio.upper():
                            yield self._parse_csv_row(parts)
```

### 4.4 Conector CONFAZ / SEFAZ (`core/integrations/public_data/confaz_connector.py`)
Responsável pela ingestão das pautas fiscais de Preço Médio Ponderado ao Consumidor Final (PMPF) publicadas quinzenalmente pelo Conselho Nacional de Política Fazendária:
* **Origem:** Portal CONFAZ (`https://www.confaz.fazenda.gov.br/legislacao/atos/atos_cotepe/`) e publicações no Diário Oficial da União (DOU).
* **Estratégia de Ingestão:**
  - Extração de tabelas de Atos COTEPE específicos de PMPF vigentes.
  - Conversão de matriz de produtos por UF (Gasolina C, Gasolina Aditivada, Etanol Hidratado, GNV, Óleo Diesel S10, Óleo Diesel S500).
  - Versionamento com data de início e término de vigência do ato fiscal.

#### Esqueleto Técnico do Conector CONFAZ:
```python
from typing import List, Optional
from datetime import datetime, date
import httpx
from core.integrations.public_data.base import BasePublicDataConnector, ConnectorHealthStatus, ConnectorFetchResult
from core.domain.public_data import UniversalTaxPMPF

class ConfazPmpfConnector(BasePublicDataConnector):
    """Adaptador para leitura e normalização de Atos COTEPE PMPF do CONFAZ."""

    def get_source_name(self) -> str:
        return "CONFAZ_PMPF"

    def health_check(self) -> ConnectorHealthStatus:
        # Ping leve no portal CONFAZ
        return ConnectorHealthStatus(source_name=self.get_source_name(), is_healthy=True)

    def fetch_latest_data(self, target_uf: Optional[str] = None, **kwargs) -> ConnectorFetchResult:
        """Busca e normaliza o Ato COTEPE PMPF mais recente em objetos UniversalTaxPMPF."""
        # Parsing estruturado e retorno do lote tipado
        pass
```

### 4.5 Conector BACEN (`core/integrations/public_data/bacen_connector.py`)
Responsável pela ingestão de séries macroeconômicas oficiais via API REST do Banco Central:
* **Origem:** API de Dados Abertos do BACEN SGS:
  - Formato de requisição: `GET https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo_serie}/dados?formato=json&dataInicial={dd/mm/aaaa}&dataFinal={dd/mm/aaaa}`
* **Séries Monitoradas:**
  - **Série 11:** Taxa Selic diária (acumulada no mês e taxa média anualizada);
  - **Série 432:** Meta para a Taxa Selic anual fixada pelo COPOM (% ao ano);
  - **Série 1:** Taxa de câmbio PTAX Dólar americano comercial de venda (cotação de fechamento diário);
  - **Série 433:** IPCA (variação mensal %);
  - **Série 189:** IGP-M (variação mensal %).
* **Resiliência:** Requisições assíncronas com timeout estrito de 8 segundos, retry exponencial e fallback para o último valor gravado no banco local caso a API retorne código de indisponibilidade (502, 503, 504).

#### Esqueleto Técnico do Conector BACEN:
```python
from typing import Dict, Any, Optional
from datetime import datetime, date
import httpx
from core.integrations.public_data.base import BasePublicDataConnector, ConnectorHealthStatus, ConnectorFetchResult
from core.domain.public_data import UniversalMacroIndicators

class BacenSgsConnector(BasePublicDataConnector):
    """Conector oficial da API REST de Séries Temporais (SGS) do Banco Central do Brasil."""

    SERIES_MAP = {
        "selic_diaria": 11,
        "selic_meta": 432,
        "ptax_dolar": 1,
        "ipca_mensal": 433,
        "igpm_mensal": 189,
    }

    def get_source_name(self) -> str:
        return "BACEN_SGS"

    def fetch_indicator_series(self, serie_id: int, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        dt_ini = start_date.strftime("%d/%m/%Y")
        dt_fim = end_date.strftime("%d/%m/%Y")
        url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie_id}/dados?formato=json&dataInicial={dt_ini}&dataFinal={dt_fim}"
        with httpx.Client(timeout=8.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.json()
```

### 4.6 Schemas de Domínio Canônicos Universais (Pydantic v2)
Os dados trafegam internamente encapsulados em contratos canônicos imutáveis:

```python
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class UniversalPublicFuelPrice(BaseModel):
    """Preço médio de combustível coletado pela ANP."""
    model_config = ConfigDict(frozen=True)

    data_coleta: date
    regiao: str
    uf: str
    municipio: str
    bairro: str
    produto: str
    preco_venda: float
    preco_compra: Optional[float] = None
    desvio_padrao: Optional[float] = None
    margem_media_revenda: Optional[float] = None
    bandeira: str
    fonte: str = "ANP"

class UniversalDealerRegistry(BaseModel):
    """Cadastro de posto revendedor da base SICOP/ANP."""
    model_config = ConfigDict(frozen=True)

    cnpj: str
    razao_social: str
    nome_fantasia: Optional[str] = None
    uf: str
    municipio: str
    bairro: str
    endereco: str
    cep: str
    bandeira: str
    capacidade_tancagem_litros: Optional[float] = None
    status_operacional: str

class UniversalTaxPMPF(BaseModel):
    """Pauta fiscal de PMPF publicada pelo CONFAZ em Atos COTEPE."""
    model_config = ConfigDict(frozen=True)

    uf: str
    produto: str
    valor_pmpf: float
    ato_cotepe_numero: str
    vigencia_inicio: date
    vigencia_fim: Optional[date] = None
    aliquota_icms_percentual: Optional[float] = None

class UniversalMacroIndicators(BaseModel):
    """Indicadores macroeconômicos do Banco Central do Brasil (SGS)."""
    model_config = ConfigDict(frozen=True)

    data_referencia: date
    selic_diaria_aa: float
    selic_meta_copom: float
    ptax_dolar_venda: float
    ptax_dolar_compra: float
    ipca_mensal: Optional[float] = None
    igpm_mensal: Optional[float] = None
```

### 4.7 Utilitário de Resiliência: Rate Limiter e Circuit Breaker (`rate_limiter.py`)
O utilitário [`core/integrations/public_data/rate_limiter.py`](./core/integrations/public_data/rate_limiter.py) implementará o padrão Circuit Breaker de 3 estados:
* **CLOSED (Operação Normal):** Requisições fluem com espaçamento mínimo de 2 segundos entre chamadas (`PublicDataRateLimiter`).
* **OPEN (Circuito Aberto por Falha):** Se ocorrerem 3 falhas consecutivas de rede (timeout ou HTTP 5xx), o conector suspende novas requisições externas por 60 minutos, preservando os recursos da máquina e evitando bloqueio de IP.
* **HALF-OPEN (Verificação Canário):** Após o período de resfriamento, o conector dispara uma única requisição leve de teste (ex: `health_check`). Se for bem-sucedida, o circuito retorna a CLOSED; se falhar, retorna a OPEN por mais 120 minutos.

### 4.8 Checklist de Execucao e Homologacao da Fase 2 (Concluida em 19/10/2026)
- [x] **Arquitetura Modular de Conectores:** Criacao de [`core/integrations/__init__.py`](./core/integrations/__init__.py) e [`core/integrations/public_data/__init__.py`](./core/integrations/public_data/__init__.py) exportando `BasePublicDataConnector`, `AnpPublicDataConnector`, `ConfazPmpfConnector`, `BacenSgsConnector`, `PublicDataCircuitBreaker`, `CircuitState` e `ConnectorFetchResult`.
- [x] **Contrato Base e Circuit Breaker Nativo:** Implementacao em [`core/integrations/public_data/base.py`](./core/integrations/public_data/base.py) do padrao de 3 estados (CLOSED, OPEN, HALF_OPEN) com monitoramento de falhas consecutivas, bloqueio por cooldown e recuperacao canario transparente.
- [x] **Conector ANP (Precos Semanais e SICOP):** Implementacao em [`core/integrations/public_data/anp_connector.py`](./core/integrations/public_data/anp_connector.py) com parsing em streaming de 64 KB, suporte a delimitadores `;` e `,`, fallback de encoding latin1/utf-8 e filtragem in-flight por municipio/UF com teto de memoria e tempo sub-100ms para 10.000 linhas.
- [x] **Conector CONFAZ (Atos COTEPE e PMPF):** Implementacao em [`core/integrations/public_data/confaz_connector.py`](./core/integrations/public_data/confaz_connector.py) com parsing estruturado por UF para as 27 UFs brasileiras, normalizacao de produtos canonicos e conversao de decimais monetarios em reais.
- [x] **Conector BACEN SGS:** Implementacao em [`core/integrations/public_data/bacen_connector.py`](./core/integrations/public_data/bacen_connector.py) das series 11 (Selic), 10813 (PTAX USD) e 433 (IPCA), consolidacao de snapshot financeiro e calculo de custo de carregamento de estoques subterraneos com fail-fast.
- [x] **Blindagem por Circuit Breaker:** Integracao transparente do Circuit Breaker em todos os conectores para tratar quedas HTTP 5xx e timeouts sem quebrar a aplicacao.
- [x] **Suite de Testes Unitarios:** Implementacao de [`tests/unit/test_public_data_connectors.py`](./tests/unit/test_public_data_connectors.py) com 9 testes automatizados cobrindo transicoes de circuito, falha em half-open, streaming CSV, eficiencia de memoria (10k linhas < 100ms), extracao COTEPE, series BACEN, integracao de falhas de rede, health check e verificacao estrita de zero travessoes Unicode.
- [x] **Homologacao e Conformidade:** 100% dos testes aprovados (22/22 testes verdes no pytest cobrindo conectores e RAG normativo) e 100% de conformidade com ruff check sem advertencias.

---

## 💾 5. Fase 3: Cache Relacional Local e Sincronizador em Segundo Plano

### 5.1 DDL Declarativo Completo das Tabelas Relacionais (`aura_core.public_*`)
Para garantir armazenamento eficiente e buscas com tempo de execução inferior a 10ms, as tabelas serão provisionadas no schema `aura_core` do banco local `posto_ai:5433`:

```sql
-- 1. Preços Semanais de Combustíveis ANP
CREATE TABLE IF NOT EXISTS aura_core.public_fuel_prices (
    id BIGSERIAL PRIMARY KEY,
    data_coleta DATE NOT NULL,
    semana_inicio DATE,
    semana_fim DATE,
    uf VARCHAR(2) NOT NULL,
    municipio VARCHAR(100) NOT NULL,
    bairro VARCHAR(100) NOT NULL,
    produto VARCHAR(50) NOT NULL,
    preco_venda NUMERIC(10, 3) NOT NULL,
    preco_compra NUMERIC(10, 3),
    desvio_padrao NUMERIC(10, 3),
    margem_media NUMERIC(10, 3),
    bandeira VARCHAR(60) NOT NULL,
    fonte VARCHAR(20) DEFAULT 'ANP_CKAN',
    criado_em TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_public_fuel_prices UNIQUE (data_coleta, uf, municipio, bairro, produto, bandeira)
);

CREATE INDEX IF NOT EXISTS idx_fuel_prices_municipio_produto
ON aura_core.public_fuel_prices (municipio, produto, data_coleta DESC);

CREATE INDEX IF NOT EXISTS idx_fuel_prices_bairro
ON aura_core.public_fuel_prices (bairro, produto);

-- 2. Base Cadastral de Postos Revendedores (SICOP / ANP)
CREATE TABLE IF NOT EXISTS aura_core.public_dealers_registry (
    cnpj VARCHAR(18) PRIMARY KEY,
    razao_social VARCHAR(150) NOT NULL,
    nome_fantasia VARCHAR(150),
    uf VARCHAR(2) NOT NULL,
    municipio VARCHAR(100) NOT NULL,
    bairro VARCHAR(100),
    endereco VARCHAR(200),
    cep VARCHAR(10),
    bandeira VARCHAR(60) NOT NULL,
    capacidade_tancagem_litros NUMERIC(15, 2),
    status_operacional VARCHAR(30) DEFAULT 'ATIVO',
    atualizado_em TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dealers_municipio_bairro
ON aura_core.public_dealers_registry (municipio, bairro);

-- 3. Pauta Fiscal CONFAZ / Atos COTEPE (PMPF ICMS-ST)
CREATE TABLE IF NOT EXISTS aura_core.public_tax_pmpf (
    id SERIAL PRIMARY KEY,
    uf VARCHAR(2) NOT NULL,
    produto VARCHAR(50) NOT NULL,
    valor_pmpf NUMERIC(10, 4) NOT NULL,
    ato_cotepe_numero VARCHAR(50) NOT NULL,
    vigencia_inicio DATE NOT NULL,
    vigencia_fim DATE,
    aliquota_icms NUMERIC(5, 2),
    criado_em TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_public_tax_pmpf UNIQUE (uf, produto, ato_cotepe_numero, vigencia_inicio)
);

CREATE INDEX IF NOT EXISTS idx_tax_pmpf_vigencia
ON aura_core.public_tax_pmpf (uf, produto, vigencia_inicio DESC);

-- 4. Indicadores Macroeconômicos BACEN SGS
CREATE TABLE IF NOT EXISTS aura_core.public_macro_indicators (
    data_referencia DATE PRIMARY KEY,
    selic_diaria_aa NUMERIC(8, 4) NOT NULL,
    selic_meta_copom NUMERIC(8, 4) NOT NULL,
    ptax_dolar_venda NUMERIC(10, 4) NOT NULL,
    ptax_dolar_compra NUMERIC(10, 4) NOT NULL,
    ipca_mensal NUMERIC(6, 3),
    igpm_mensal NUMERIC(6, 3),
    atualizado_em TIMESTAMP DEFAULT NOW()
);

-- 5. Diário de Auditoria de Sincronizações Públicas
CREATE TABLE IF NOT EXISTS aura_core.public_sync_journal (
    id SERIAL PRIMARY KEY,
    fonte VARCHAR(50) NOT NULL,
    iniciado_em TIMESTAMP NOT NULL,
    finalizado_em TIMESTAMP NOT NULL,
    status VARCHAR(20) NOT NULL, -- 'SUCESSO', 'FALHA', 'SEM_ALTERACAO'
    registros_ingeridos INTEGER DEFAULT 0,
    latencia_total_ms NUMERIC(10, 2),
    hash_payload VARCHAR(64),
    mensagem_erro TEXT
);
```

### 5.2 Script de Ingestão e Sincronização em Lote ([`scripts/sync_public_data.py`](./scripts/sync_public_data.py))
Será desenvolvido um script de automação modular e idempotente:
* **Parâmetros da CLI:**
  - `--source {all, anp, confaz, bacen}`: Especifica a fonte a sincronizar;
  - `--municipio {NOME}`: Filtra apenas o município do posto piloto para acelerar a ingestão;
  - `--uf {UF}`: Filtra o estado do posto piloto (ex: `SP`, `MG`, `PR`);
  - `--dry-run`: Executa o download e validação sem persistir no PostgreSQL;
  - `--force`: Ignora hash de integridade e força reprocessamento completo.
* **Processamento com Baixo Footprint:**
  - Streaming direto do arquivo de dados sem carregar múltiplos megabytes em arrays Python.
  - Gravação em lotes (batch chunks de 1.000 linhas) utilizando `psycopg2.extras.execute_values()` com transações atômicas isoladas e cláusula `ON CONFLICT DO UPDATE`.

### 5.3 Agendamento e Autonomia no Daemon Proativo ([`core/proactive_daemon.py`](./core/proactive_daemon.py))
O motor de vigilância contínua da AURA (`AuraProactiveDaemon`) incorporará avaliações periódicas integradas à sua suíte de regras:
* **Horários Agendados (Time Windows):**
  - **BACEN SGS:** Execução diária às 06:30 da manhã (dados de fechamento do dia anterior e PTAX consolidada).
  - **ANP Preços:** Execução semanal nas terças-feiras às 03:00 da madrugada (janela em que a ANP publica os consolidados da semana anterior).
  - **CONFAZ PMPF:** Execução quinzenal nos dias 02 e 17 de cada mês às 04:00 da madrugada.
* **Regras de Não Interferência na Pista:**
  - O daemon verifica o estado do posto antes de iniciar o download. Se houver concorrência de CPU > 70% ou fechamento de turno em andamento, o processo é postergado em 30 minutos.
* **Alertas Proativos de Inteligência Competitiva:**
  - Método `evaluate_competitive_pricing_rules()`: se a média municipal da ANP para Gasolina sofrer redução superior a R$ 0,08/L em relação à semana anterior e o preço de bomba do posto ainda não tiver sido reajustado, o daemon emite alerta executivo sugerindo reavaliação de margem.

### 5.4 Garantia de Performance Sub-100ms e Isolamento de Recursos
* As consultas SQL realizadas pelas tools utilizam filtros restritos por município configurado no `.env` (`POSTO_MUNICIPIO`, `POSTO_UF`).
* Com os índices parciais e compostos propostos, a leitura do preço médio da concorrência e do PMPF consome entre 1ms e 4ms no PostgreSQL, garantindo que o tempo total da inferência cognitiva da IA permaneça inferior a 100ms.

### 5.5 Checklist de Execucao e Homologacao da Fase 3 (Concluida em 19/10/2026)
- [x] **DDL Declarativo e Idempotente (`aura_core` e `public`):** Criacao de [`scripts/init_public_data_cache.sql`](./scripts/init_public_data_cache.sql) com tabelas relacionais dedicadas `aura_core.anp_precos_semanais`, `aura_core.confaz_pmpf`, `aura_core.bacen_series_historicas` e `aura_core.public_sync_telemetry`, indices compostos e views equivalentes em `public`.
- [x] **Repositorio de Cache Relacional Local:** Implementacao de [`PublicDataRepository`](./core/integrations/public_data/repository.py) com suporte a pool de conexao do PostgreSQL (`get_vector_connection`) e fallback em memoria / SQLite isolado para execucao hermetica offline.
- [x] **Persistencia Idempotente por UPSERT:** Ingestao em lote com clausulas `ON CONFLICT DO UPDATE` prevenindo duplicacoes em coletas repetidas de precos semanais da ANP, pautas fiscais PMPF e series SGS.
- [x] **Consultas Analiticas de Alta Performance (Sub-50ms):** Metodos `get_preco_benchmark_anp()`, `get_pmpf_atual()` e `get_indicadores_economicos_recentes()` com calculo de media, mediana, quartis, desvio padrao e postos amostrados.
- [x] **Worker CLI e Sincronizador de Retaguarda:** Script [`scripts/sync_public_data.py`](./scripts/sync_public_data.py) com streaming de baixo footprint (< 80 MB RAM), protecao por Circuit Breaker, modos daemon e mock para CI/CD.
- [x] **Auditoria e Telemetria em Tempo Real:** Registro transacional de cada rodada de sincronizacao em `public_sync_telemetry` com metricas de latencia, contagem de registros e diagnostico de erros.
- [x] **Suite de Testes Unitarios e Homologacao:** Criacao de [`tests/unit/test_public_data_sync.py`](./tests/unit/test_public_data_sync.py) com 8 testes cobrindo idempotencia, UPSERT, pautas fiscais, series BACEN, auditoria e fluxo mock.
- [x] **Aprovacao Integral:** 100% dos testes aprovados (30/30 testes verdes no pytest cobrindo fases 1, 2 e 3) e 100% de conformidade com ruff check sem advertencias.

---

## 🧠 6. Fase 4: Integração Cognitiva nas Ferramentas Analíticas da AURA

### 6.1 `PostoTools.comparar_benchmark_concorrencia` e `BenchmarkComparisonUI`
No arquivo [`core/tools.py`](./core/tools.py), a ferramenta de benchmark existente será expandida para cruzar a precificação real da pista com os dados públicos locais da ANP, mantendo rigorosa retrocompatibilidade com a assinatura e contratos existentes:

```python
def comparar_benchmark_concorrencia(
    self,
    grupo_benchmark: Optional[str] = None,
    data: Optional[str] = None,
    turno: Optional[str] = None,
    custom_benchmarks: Optional[Dict[str, Any]] = None,
    filial_nome: Optional[str] = None,
    produto: Optional[str] = None,
    bairro_comparacao: Optional[str] = None,
    usar_cache_publico_anp: bool = True,
) -> Dict[str, Any]:
    """
    Compara o posicionamento competitivo da filial frente a concorrentes locais e médias de rede.
    Lê preços reais de combustíveis na tabela produtos (valvenda) do ERP local.
    Quando usar_cache_publico_anp=True, cruza com as médias semanais oficiais coletadas pela ANP
    (schema aura_core.public_fuel_prices) para o município e bairro especificados.
    Retorna o contrato canônico BenchmarkComparisonProps para o micro-widget BenchmarkComparisonUI (F6-03).
    """
```

* **Inteligência Gerada:**
  - Cálculo do **Spread de Competitividade Local**: diferença em R$/litro entre o preço na bomba e a média da ANP para o mesmo bairro e para o município geral.
  - Cálculo do **Posicionamento Relativo no Mix**: classificação do posto como "Líder de Preço", "Alinhado à Média" ou "Premium/Margem Alta".
  - Identificação da dispersão de preços (desvio padrão) na microrregião para aferir se o mercado está agressivo ou estável.
* **Renderização Visual via GenUI:**
  - Alimenta diretamente o contrato Pydantic `BenchmarkComparisonProps` ([`core/schemas/genui.py`](./core/schemas/genui.py)), renderizando no frontend o componente interativo [`BenchmarkComparisonUI`](./web/js/aura-genui-widgets.js) com barras comparativas e botões de ação tática (`Ajustar Preço de Bomba`, `Manter Estratégia de Margem`).

### 6.2 `PostoTools.auditar_conformidade_lmc_anp` e `LMCReportContract`
O ecossistema disponibiliza o método oficial de auditoria regulatória do LMC, construído sobre a engine [`PostoTools.gerar_relatorio_lmc_anp()`](./core/tools.py) e o contrato [`LMCReportContract`](./core/schemas/lmc_report.py):

```python
def auditar_conformidade_lmc_anp(
    self,
    data: Optional[str] = None,
    combustivel: Optional[str] = None,
    tanque: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Audita a conformidade regulatória do Livro de Movimentação de Combustíveis (LMC)
    frente às exigências estritas da Portaria ANP nº 26/1992 e Resolução ANP nº 894/2022.
    Avalia a variação volumétrica entre medição física e contábil contra o limite legal de ±0,6%.
    Retorna o contrato oficial LMCReportContract com status, alertas e parecer jurídico.
    """
```

* **Cruzamento de Limite Legal de 0,6%:**
  - O cálculo de variação volumétrica de tanques compara a perda/sobra física contra o limite legal estrito de 0,6% do total de saídas no período.
  - Se a variação estiver entre 0,0% e 0,59%, o status emitido é `REGULAR`.
  - Se a variação atingir entre 0,60% e 0,80%, emite-se status `ATENÇÃO_RISCO_FISCAL` com recomendação de calibração metrológica.
  - Se a variação superar 0,80%, emite-se status `CRÍTICO_NÃO_CONFORME` com plano de contenção para evitar autuação e interdição em caso de fiscalização da ANP.
* **Geração de Parecer Jurídico-Técnico Automático:**
  - A AURA redige automaticamente a justificativa técnica pronta para anexação no Livro de Movimentação de Combustíveis, citando a Portaria ANP 26/1992 e os registros de temperatura e aferições do período.

### 6.3 Auditoria Metrológica de Bombas e Bicos no `ShiftReconciliationUI`
Na conciliação de fechamento de turnos (`PostoTools.auditar_fechamento_turno` e contrato [`ShiftReconciliationContract`](./core/schemas/reconciliation.py)):
* **Auditoria de Aferições Diárias com Tolerância INMETRO 559/2016:**
  - Todo volume retirado da bomba para fins de aferição matinal deve corresponder estritamente a múltiplos de 20 litros (amostra do balde aferidor padrão).
  - O desvio tolerado entre o medidor da bomba e o padrão aferido é fixado em no máximo **±100 ml a cada 20L (±0,50%)**.
  - O sistema verifica se o volume lançado como aferição no ERP coincide rigorosamente com o retorno físico registrado no tanque de origem, prevenindo desvios operacionais onde combustível de aferição é furtado ou extraviado.

### 6.4 Motor de Custo de Capital e Projeção Financeira de Estoques Subterrâneos
Cruzamento da posição volumétrica dos tanques com a taxa Selic do BACEN:
* **Cálculo do Carrying Cost Financeiro:**
  `Custo_Diario_Carregamento = (Volume_Estocado * Preco_Custo_Compra) * (Taxa_Selic_Anual / 252)`
* **Projeção de Recompra Ótima:**
  - Identifica se o custo financeiro de manter tanques cheios supera o ganho potencial de comprar combustível antes de um aumento da refinaria.
  - Fornece ao proprietário do posto uma recomendação clara: "Seu capital empatado em 45.000L de Gasolina Comum gera um custo Selic de R$ 38,40 por dia. O pedido ótimo para reposição deve ocorrer em até 4 dias úteis".

### 6.5 Entregáveis Concluídos da Fase 4 (Pilar 5)
- [x] **Enriquecimento Cognitivo do Benchmark Municipal:** Integração em [`PostoTools.comparar_benchmark_concorrencia()`](./core/tools.py) consultando o cache local da ANP (`PublicDataRepository.get_preco_benchmark_anp`), calculando quartis (Q1, Mediana, Q3), valores minimos e maximos, gap exato em R$ e % frente a media da cidade, posicionamento competitivo e fallback 100% compativel com o contrato canônico `BenchmarkComparisonProps`.
- [x] **Auditoria Volumétrica de Conformidade LMC ANP:** Implementacao do metodo [`PostoTools.auditar_conformidade_lmc_anp()`](./core/tools.py) fundamentado na Portaria ANP 26/1992 e Resolucao ANP 894/2022, auditando variacao volumetrica contra a tolerancia legal de +-0.60%, classificando tanques em CONFORME ou CRITICO e retornando o micro-widget GenUI `LMCComplianceReportUI` com 3 acoes HITL interativas ("📄 Exportar LMC Formatado", "📏 Agendar Aferição INMETRO 20L", "🔍 Inspecionar Calibração do Tanque").
- [x] **Analise Macroeconomica de Custo de Estoque e Pauta CONFAZ:** Implementacao de [`PostoTools.analisar_custo_estoque_macroeconomico()`](./core/tools.py) calculando custo de carregamento diario e mensal via taxa Selic anualizada do BACEN SGS (convencao de 252 d.u.), cambio PTAX e spread fiscal frente a pauta PMPF do CONFAZ (ICMS-ST) via contrato `MacroeconomicInventoryCostProps`.
- [x] **Registro e Despacho no Motor da AURA:** Mapeamento completo em [`core/aura_engine.py`](./core/aura_engine.py) em `GENUI_COMPONENT_REGISTRY_MAP`, despacho direto em `execute_tool_direct`, resolucao de contexto em `_resolver_contexto_ferramenta`, sintese de contingencia deterministica rica e envelopes canônicos GenUI.
- [x] **Roteamento Semântico e Heurístico Enriquecido:** Atualizacao de [`core/semantic_router.py`](./core/semantic_router.py) com catalogacao de exemplares em `INTENT_EXEMPLARS` para `custo_estoque_macro` e `auditar_conformidade_lmc_anp`, alem de regras heuristicas sub-milissegundo para variacoes de LMC, tolerancia de 0.60%, pautas COTEPE/PMPF e indicadores macroeconomicos.
- [x] **Suite de Testes Unitarios e Homologacao:** Criacao e aprovacao integral de [`tests/unit/test_ferramentas_cognitivas_publicas.py`](./tests/unit/test_ferramentas_cognitivas_publicas.py) com testes cobrindo ANP, LMC, Macro, despacho direto com `PostoTools` real, fallback offline e zero travessoes Unicode.

---

## 🛡️ 7. Fase 5: Matriz de Riscos, Políticas de Fallback, Rate Limiting e Testes

### 7.1 Matriz de Riscos Técnicos e Mitigações

| Risco Técnico Identificado | Impacto | Probabilidade | Estratégia de Mitigação |
| :--- | :--- | :--- | :--- |
| **Indisponibilidade ou Timeout na API do Governo (ANP / BACEN / CONFAZ)** | Médio | Alta | Arquitetura estritamente Offline-First: o sistema nunca falha em tempo de execução para o usuário. Continua operando com o último snapshot salvo no PostgreSQL local. |
| **Mudança Estrutural no Layout do CSV da ANP ou no Portal CONFAZ** | Alto | Média | Normalização desacoplada no conector com cabeçalhos dinâmicos flexíveis (aliasing de colunas) e logging estruturado de advertência sem quebra do core. |
| **Bloqueio Temporário de IP por Excesso de Requisições (Rate Limit Governamental)** | Baixo | Média | Implementação de Rate Limiting rígido na origem (máximo de 1 requisição a cada 3 segundos) e Circuit Breaker local. |
| **Interrupção de Energia no Posto Durante o Download de Grandes CSVs** | Médio | Média | Download para arquivo temporário `.tmp` com verificação de integridade SHA-256 e gravação transacional atômica no banco de dados. |
| **Inconsistência ou Dado Corrompido no Cadastro Público da ANP** | Baixo | Baixa | Validação estrita via esquemas Pydantic v2: linhas mal formatadas são descartadas para um log de quarentena sem interromper o lote. |

### 7.2 Políticas de Fallback, TTL e Degradação Graciosa
Para garantir confiabilidade total, cada conjunto de dados públicos possui uma política de validade temporal (TTL):
* **ANP Preços Semanais:** TTL Nominal de 7 dias; TTL Limite de Resiliência de **45 dias**.
* **CONFAZ PMPF:** TTL Nominal de 15 dias; TTL Limite de Resiliência de **60 dias**.
* **BACEN Indicadores:** TTL Nominal de 1 dia; TTL Limite de Resiliência de **30 dias**.
* **Comportamento em Modo Degradado:**
  - Se a sincronização falhar sucessivamente por ausência de internet no posto, a AURA continua calculando todos os indicadores, mas adiciona um badge informativo na interface GenUI:
    `status_referencia: "Dados ANP de 08/10/2026 (Cache Local: Conexão Externa Pendente)"`.

### 7.3 Mecanismo de Rate Limiting e Circuit Breaker
O utilitário [`core/integrations/public_data/rate_limiter.py`](./core/integrations/public_data/rate_limiter.py) implementará o padrão Circuit Breaker:
* **CLOSED (Operação Normal):** Requisições fluem com espaçamento mínimo de 2 segundos entre chamadas.
* **OPEN (Circuito Aberto por Falha):** Se ocorrerem 3 falhas consecutivas de rede (timeout ou HTTP 5xx), o conector interrompe qualquer tentativa de chamada externa por 60 minutos, preservando os recursos da máquina e evitando penalizações de rede.
* **HALF-OPEN (Verificação Canário):** Após o período de resfriamento, o conector dispara uma única requisição leve de teste (ex: `health_check`). Se for bem-sucedida, o circuito retorna a CLOSED; se falhar, retorna a OPEN por mais 120 minutos.

### 7.4 Plano e Estrutura da Suíte de Testes Unitários ([`tests/unit/test_public_data_connectors.py`](./tests/unit/test_public_data_connectors.py))
Nenhum conector público dependerá de rede ativa para a execução da suíte de testes automatizados (`pytest`). Todos os testes serão 100% determinísticos e herméticos utilizando mocks e fixtures locais:

* **Casos de Teste Essenciais da Suíte:**
  1. `test_anp_connector_csv_stream_parsing`: Validação do parsing de CSV da ANP simulado em memória com diferentes delimitadores (vírgula e ponto-e-vírgula) e encodings (`utf-8` e `latin-1`).
  2. `test_anp_connector_filter_by_target_municipality`: Garantia de que postos de outros municípios são descartados durante o streaming sem alocação desnecessária de memória.
  3. `test_bacen_sgs_json_normalization`: Verificação de conversão de datas no formato DD/MM/AAAA para objetos `date` ISO e parsing de taxas flutuantes.
  4. `test_confaz_cotepe_table_extraction`: Validação da captura de pautas de PMPF por estado para Etanol e GNV.
  5. `test_circuit_breaker_transition_open_and_recovery`: Simulação de falhas de conexão consecutivas e validação da abertura do circuito com suspensão de requisições.
  6. `test_cache_resilience_offline_fallback`: Validação de que as ferramentas analíticas ([`PostoTools.comparar_benchmark_concorrencia`](./core/tools.py)) retornam dados válidos do cache local mesmo com mock de rede offline absoluto.
  7. `test_pydantic_contracts_validation_error_quarantine`: Garantia de que registros públicos mal formatados são descartados para quarentena sem derrubar a aplicação.

### 7.5 Entregáveis Concluídos da Fase 5 (Pilar 6: Homologação em Produção e E2E)
- [x] **Daemon Proativo com Alertas LMC e Staleness de Dados Públicos:** Monitoramento contínuo em [`core/proactive_daemon.py`](./core/proactive_daemon.py) avaliando variação volumétrica de tanques (> +-0.60%) e defasagem governamental (> 7 dias) com smart cooldown (4h LMC, 24h staleness), integração CDC e despacho multi-canal in-app na AURA (chat stream SSE, container de alertas na UI, toasts in-app, webhooks e WhatsApp; popups nativos do Windows desativados por padrão).
- [x] **Endpoints HTTP de Telemetria e Health de Dados Abertos:** Exposição de `GET /api/v1/aura/public-data/health` (inspeção de Circuit Breakers e conexão) e `GET /api/v1/aura/public-data/telemetry` (histórico de syncs, staleness e datas de coleta) em [`core/aura_api.py`](./core/aura_api.py).
- [x] **Validação E2E com Consultas Reais de Revendedores:** Suíte [`tests/unit/test_public_data_e2e_api.py`](./tests/unit/test_public_data_e2e_api.py) validando os 3 fluxos conversacionais prioritários do revendedor via `/api/v1/aura/chat` (benchmark ANP municipal, auditoria LMC e custo Selic de estoques).
- [x] **Guia Operacional e Manual de Borda:** Documentação completa em [`docs/guia_operacional_apis_publicas.md`](./docs/guia_operacional_apis_publicas.md) cobrindo rotinas de fiscalização, benchmarks de quartis, auditoria metrológica, carrying cost, comandos CLI e conformidade LGPD.

---

## 📅 8. Cronograma de Implementação e Critérios de Conclusão (Definition of Done)

### 8.1 Fases e Entregáveis Sequenciais

```
+────────────────────────────────────────────────────────────────────────+
│ BLOCO 1: Ingestão de Legislação e Normas Técnicas no RAG Local         │
│ • Seed de 10 chunks canônicos em scripts/seed_aura_conhecimento.py     │
│ • Validação de similaridade HNSW e FTS no HybridRAGEngine              │
│ • Critério de Aceite: Busca sub-5ms por "tolerância LMC ANP" verde     │
+───────────────────────────────────┬────────────────────────────────────+
                                    │
                                    ▼
+────────────────────────────────────────────────────────────────────────+
│ BLOCO 2: Hub de Conectores e Schemas Canônicos Universais              │
│ • Pacote core/integrations/public_data/ (ANP, CONFAZ, BACEN)           │
│ • Modelos Pydantic v2 congelados e RateLimiter com Circuit Breaker     │
│ • Critério de Aceite: 100% dos conectores testados com mocks herméticos│
+───────────────────────────────────┬────────────────────────────────────+
                                    │
                                    ▼
+────────────────────────────────────────────────────────────────────────+
│ BLOCO 3: Cache Relacional Local e Sincronizador de Segundo Plano       │
│ • Provisionamento DDL no schema aura_core (posto_ai:5433)              │
│ • Script scripts/sync_public_data.py com suporte a streaming e upsert  │
│ • Integração de thread periódica em core/proactive_daemon.py           │
│ • Critério de Aceite: Ingestão idempotente completa sub-15s            │
+───────────────────────────────────┬────────────────────────────────────+
                                    │
                                    ▼
+────────────────────────────────────────────────────────────────────────+
│ BLOCO 4: Enriquecimento das Ferramentas Analíticas e GenUI             │
│ • Integração em PostoTools.comparar_benchmark_concorrencia()           │
│ • Auditoria regulatória em PostoTools.auditar_conformidade_lmc_anp()   │
│ • Auditoria metrológica de bombas (INMETRO) em ShiftReconciliationUI   │
│ • Custo financeiro Selic em estoques subterrâneos                      │
│ • Critério de Aceite: Contratos BenchmarkComparisonProps validados     │
+───────────────────────────────────┬────────────────────────────────────+
                                    │
                                    ▼
+────────────────────────────────────────────────────────────────────────+
│ BLOCO 5: Suíte de Testes, Homologação e Documentação Operacional       │
│ • Criação de tests/unit/test_public_data_connectors.py                 │
│ • Execução da suíte completa de testes unitários da AURA               │
│ • Atualização dos guias operacionais de deploy em posto                │
│ • Critério de Aceite: Todos os testes verdes sem quebra de regressão   │
+────────────────────────────────────────────────────────────────────────+
```

### 8.2 Critérios Globais de Aceite (Definition of Done)
Para que a integração de dados públicos seja considerada concluída e pronta para implantação em produção:
1. **Zero Travessões:** Ausência estrita de caracteres de travessão em todo o código, documentação e comentários.
2. **Offline-First Comprovado:** Todas as ferramentas funcionam com simulação de rede desligada, consultando exclusivamente o PostgreSQL local.
3. **Isolamento de Memória:** O sincronizador não pode alocar mais de 80 MB de memória RAM na estação durante o parsing de bases volumosas da ANP.
4. **Blindagem LGPD:** Nenhuma requisição externa contém identificadores do estabelecimento ou telemetria operacional privada.
5. **Cobertura de Testes Automatizados:** 100% dos testes unitários dos conectores e schemas passam com sucesso no runner pytest em menos de 10 segundos.

### 8.3 Log de Execução e Status por Fase

| Fase | Pilar / Escopo | Status | Data de Conclusão | Entregáveis Principais |
| :--- | :--- | :---: | :---: | :--- |
| **Fase 1** | Pilar 2: RAG Técnico Normativo e Regulatório Local (ANP, INMETRO, CONFAZ, BACEN) | `CONCLUÍDA` | 19/10/2026 | [`scripts/seed_aura_conhecimento.py`](./scripts/seed_aura_conhecimento.py), [`core/rag_engine.py`](./core/rag_engine.py), [`tests/unit/test_rag_normativo_publico.py`](./tests/unit/test_rag_normativo_publico.py). 26 chunks indexados, busca híbrida HNSW + FTS com metadados, protocolo de recusa de cargas fora de especificação e fallback de memória offline. 22/22 testes unitários verdes. |
| **Fase 2** | Pilar 1: Hub de Conectores de Dados Abertos (`core/integrations/public_data/`) | `CONCLUÍDA` | 19/10/2026 | [`core/integrations/public_data/`](./core/integrations/public_data/), [`tests/unit/test_public_data_connectors.py`](./tests/unit/test_public_data_connectors.py). Conectores ANP, CONFAZ e BACEN SGS, Circuit Breaker nativo de 3 estados, parsing em streaming de 64 KB, eficiencia sub-100ms em 10.000 linhas e 22/22 testes unitarios 100% verdes. |
| **Fase 3** | Pilar 3: Cache Relacional Local e Sincronizacao em Segundo Plano | `CONCLUÍDA` | 19/10/2026 | [`scripts/init_public_data_cache.sql`](./scripts/init_public_data_cache.sql), [`core/integrations/public_data/repository.py`](./core/integrations/public_data/repository.py), [`scripts/sync_public_data.py`](./scripts/sync_public_data.py), [`tests/unit/test_public_data_sync.py`](./tests/unit/test_public_data_sync.py). DDLs idempotentes em `aura_core` e `public`, UPSERT de precos e pautas, consultas sub-50ms, worker CLI em streaming e 30/30 testes verdes. |
| **Fase 4** | Pilar 4: Enriquecimento das Ferramentas Analíticas e GenUI | `CONCLUÍDA` | 20/10/2026 | [`core/tools.py`](./core/tools.py), [`core/aura_engine.py`](./core/aura_engine.py), [`core/semantic_router.py`](./core/semantic_router.py), [`tests/unit/test_ferramentas_cognitivas_publicas.py`](./tests/unit/test_ferramentas_cognitivas_publicas.py). Enriquecimento de benchmark com estatisticas e quartis ANP, auditoria de conformidade LMC (+-0.60%) com micro-widget LMCComplianceReportUI, analise de custo de oportunidade Selic (252 d.u.) e pauta PMPF CONFAZ com MacroeconomicInventoryCostUI, despacho direto Headless, sintese de contingencia e 35/35 testes verdes. |
| **Fase 5** | Pilar 6: Homologação Geral, Testes E2E e Documentação Operacional | `CONCLUÍDA` | 20/10/2026 | [`core/proactive_daemon.py`](./core/proactive_daemon.py), [`core/aura_api.py`](./core/aura_api.py), [`tests/unit/test_public_data_e2e_api.py`](./tests/unit/test_public_data_e2e_api.py), [`docs/guia_operacional_apis_publicas.md`](./docs/guia_operacional_apis_publicas.md). Integracao do daemon com alertas LMC (+-0.60%) e staleness com smart cooldown, rotas de health e telemetria publica, teste E2E das 3 perguntas operacionais do revendedor, guia operacional completo e suíte 100% verde sub-segundo. |
