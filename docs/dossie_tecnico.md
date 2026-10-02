# 📋 DOSSIÊ TÉCNICO DE INTEGRAÇÃO — IA AGÊNTICA & SRE (SENTINEL)

**Data de Emissão:** 04/09/2026  
**Destinatário:** Agente Sentinel (Servidor SRE / Observabilidade)  
**Projeto:** Arquitetura Híbrida de IA do Posto + Banco Vetorial PostgreSQL 16 + pgvector  
**Status da Infraestrutura:** Operacional / Validada com Benchmarks  

---

## 1. 🌐 TOPOLOGIA DE REDE E BANCOS DE DADOS

O ecossistema local é composto por duas instâncias de banco de dados PostgreSQL 16 com responsabilidades segregadas:

```
+------------------------------------+        +------------------------------------+
|  PostgreSQL 16 (Windows Service)  |        |    PostgreSQL 16 (Docker pgvector) |
|  Host: localhost                   |        |    Host: localhost                 |
|  Porta: 5433                       |        |    Porta: 5434                     |
|  Banco: posto                      |        |    Banco: posto_ai                 |
|  Função: ERP Transacional          |        |    Função: Base Vetorial & Semântica|
+-----------------+------------------+        +-----------------+------------------+
                  |                                             |
                  | (ETL / Sincronização Periódica)             |
                  +----------------------> [ Motor de IA ] <----+
                                                  |
                                                  v
                                      [ Agente Sentinel / SRE ]
```

### Detalhes das Instâncias:
1. **Banco ERP Transacional (Relacional)**:
   - **Host:** `localhost` | **Porta:** `5433` | **Database:** `posto`
   - **Serviço Windows:** `postgresql-x64-16` (`C:\Program Files\PostgreSQL\16\data`)
   - **Usuário Padrão:** `suporte` / `postgres` | **Senha:** Carregada via `.env` (`ERP_DB_PASSWORD`)
   - **Tabelas Principais Validadas:** `produtos` (238 itens), `grupos`, `empresa`, `itemsai`, `abastecimentos`.
   - **Status da Conexão:** 🟢 **OPERACIONAL / DESBLOQUEADA** (Autenticação local via `pg_hba.conf` e credenciais seguras do `.env`).

2. **Banco de Inteligência e Vetores (pgvector)**:
   - **Host:** `localhost` | **Porta:** `5434` | **Database:** `posto_ai`
   - **Ambiente:** Container Docker com PostgreSQL 16.15 e extensão `vector 0.8.6`
   - **Usuário:** `postgres` | **Senha:** Carregada via `.env` (`VECTOR_DB_PASSWORD`)
   - **Função:** Armazenamento dos vetores de 768 dimensões, busca semântica densa, busca lexical esparsa e fusão de rankings.

---

## 2. 🗄️ ESTRUTURA DO BANCO VETORIAL (`posto_ai`)

### Tabela: `public.produtos_vetores`
Tabela principal que armazena os produtos enriquecidos, os vetores gerados pelo Gemini e a coluna de Full-Text Search.

```sql
CREATE TABLE public.produtos_vetores (
    codpro VARCHAR(10) PRIMARY KEY,
    nompro VARCHAR(120) NOT NULL,
    grupo VARCHAR(50),
    codbar VARCHAR(20),
    unidade VARCHAR(10),
    preco NUMERIC(15, 2),
    texto_busca TEXT NOT NULL,
    embedding vector(768),
    atualizado_em TIMESTAMP DEFAULT NOW(),
    tsv tsvector GENERATED ALWAYS AS (
        to_tsvector('portuguese', 
            coalesce(nompro, '') || ' ' || 
            coalesce(grupo, '') || ' ' || 
            coalesce(codbar, '') || ' ' || 
            coalesce(codpro, '') || ' ' ||
            coalesce(unidade, '')
        )
    ) STORED
);
```

### Índices Criados e Calibrados:
1. **Índice B-Tree (Chave Primária):**
   - `produtos_vetores_pkey` em `codpro`.
2. **Índice HNSW para Busca Densa (pgvector):**
   - `idx_produtos_vetores_hnsw` USING `hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)`.
   - *Métrica HNSW:* `m=16` conexões bidirecionais por nó; `ef_construction=64` para equilíbrio ideal entre velocidade de indexação e recall.
3. **Índice GIN para Busca Esparsa (FTS):**
   - `idx_produtos_vetores_tsv_gin` USING `gin (tsv)`.
   - *Objetivo:* Resolução instantânea de termos exatos, SKUs, códigos de barras e viscosidades (`5W30`, `15W40`).

---

## 3. 🧠 MECANISMO DE BUSCA: RAG HÍBRIDO + RECIPROCAL RANK FUSION (RRF)

Em vez de depender unicamente da busca por distância de cosseno, o sistema implementa **Dual Retrieval com RRF nativo no PostgreSQL 16**, executado em uma única transação SQL:

```sql
SET LOCAL hnsw.ef_search = 100;

WITH dense_search AS (
    SELECT 
        codpro, nompro, grupo, preco,
        1 - (embedding <=> :query_vector::vector) AS cosine_similarity,
        ROW_NUMBER() OVER (ORDER BY embedding <=> :query_vector::vector) AS dense_rank
    FROM produtos_vetores
    WHERE embedding IS NOT NULL
    ORDER BY embedding <=> :query_vector::vector
    LIMIT 15
),
sparse_search AS (
    SELECT 
        codpro, nompro, grupo, preco,
        ts_rank_cd(tsv, to_tsquery('portuguese', :tsquery)) AS fts_score,
        ROW_NUMBER() OVER (
            ORDER BY ts_rank_cd(tsv, to_tsquery('portuguese', :tsquery)) DESC,
                     nompro ASC
        ) AS sparse_rank
    FROM produtos_vetores
    WHERE tsv @@ to_tsquery('portuguese', :tsquery)
       OR nompro ILIKE :like_term
    LIMIT 15
)
SELECT 
    COALESCE(d.codpro, s.codpro) AS codpro,
    COALESCE(d.nompro, s.nompro) AS nompro,
    COALESCE(d.preco, s.preco) AS preco,
    COALESCE(d.cosine_similarity, 0.0) AS cosine_similarity,
    COALESCE(s.fts_score, 0.0) AS fts_score,
    (
        0.5 * COALESCE(1.0 / (60 + d.dense_rank), 0.0) +
        0.5 * COALESCE(1.0 / (60 + s.sparse_rank), 0.0)
    ) AS rrf_score
FROM dense_search d
FULL OUTER JOIN sparse_search s ON d.codpro = s.codpro
ORDER BY rrf_score DESC
LIMIT 5;
```

---

## 4. 🔀 ARQUITETURA DO AGENTE: TOOL ROUTING & STREAMING

O agente conversacional (`agente_posto.py`) foi estruturado com separação estrita de intenções para evitar vazamento de contexto e consultas inadequadas no banco vetorial:

```
[ Usuário ] 
    │
    ▼
[ Classificador de Intenção / Router ]
    │
    ├──> "catalogo_produtos" ────> Tool RAG Híbrido (HNSW + GIN na porta 5434)
    ├──> "vendas_analitico"  ────> Tool Analítica SQL (ERP na porta 5433)
    ├──> "sre_metricas"      ────> Tool Telemetria SRE (pg_stat na porta 5434)
    └──> "dados_filial"      ────> Tool Metadados Cadastrais
```

### Otimização de Latência:
- **Streaming Ativo (`stream=True`):** Emissão token-a-token via Google Gemini.
- **Time-To-First-Token (TTFT):** Queda de percepção de latência de 29 segundos para **~2.6 segundos**.

---

## 5. 📊 MÉTRICAS E QUERIES ESSENCIAIS PARA O INTEGRADOR SRE (SENTINEL)

O Sentinel deve integrar os seguintes coletores de métricas do PostgreSQL 16 para monitoramento contínuo:

### Métrica 1: Buffer Cache Hit Ratio (Saúde Geral de Memória)
- **Frequência sugerida:** A cada 30 segundos.
- **Limiar de alerta:** Alerta Warning se `< 95%`, Critical se `< 90%`.
```sql
SELECT 
    datname,
    numbackends AS active_connections,
    ROUND(100.0 * blks_hit / NULLIF(blks_hit + blks_read, 0), 2) AS cache_hit_ratio_percent
FROM pg_stat_database 
WHERE datname = 'posto_ai';
```

### Métrica 2: Utilização Efetiva do Índice HNSW (Evitar Seq Scans)
- **Importância:** Se `idx_scan` não subir após consultas vetoriais, o PostgreSQL está fazendo Sequential Scan em disco.
```sql
SELECT 
    indexrelname AS nome_indice,
    idx_scan AS total_consultas_via_indice,
    idx_tup_read AS tuplas_lidas,
    idx_tup_fetch AS tuplas_recuperadas
FROM pg_stat_user_indexes
WHERE relname = 'produtos_vetores';
```

### Métrica 3: Consumo de Memória e Tamanho em Disco
- **Importância:** Vetores ocupam memória considerável. Monitorar o crescimento do grafo HNSW:
```sql
SELECT 
    pg_size_pretty(pg_relation_size('produtos_vetores')) AS table_size,
    pg_size_pretty(pg_relation_size('idx_produtos_vetores_hnsw')) AS hnsw_index_size,
    pg_size_pretty(pg_relation_size('idx_produtos_vetores_tsv_gin')) AS gin_index_size,
    pg_size_pretty(pg_total_relation_size('produtos_vetores')) AS total_footprint;
```

### Métrica 4: Telemetria E2E da Requisição de IA
- Cada chamada do agente expõe:
  - `embedding_latency_ms`: Tempo de ida e volta da API de Embeddings (normal: 300-450ms).
  - `db_rrf_latency_ms`: Tempo de execução da query CTE RRF no Postgres (normal: 15-80ms).
  - `ttft_ms`: Tempo até o primeiro token emitido pelo LLM (normal: 1500-2800ms).
  - `total_e2e_ms`: Latência total ponta a ponta.

---

## 6. 🛡️ DIRETRIZES DE SEGURANÇA E CONFORMIDADE LGPD

Para futuras integrações de consultas a clientes (cadastro, fidelidade, faturamento) na esteira da IA:

1. **Princípio do Privilégio Mínimo no ERP (5433):**
   - Não utilizar `superuser` nas conexões regulares de monitoramento/IA.
   - Criar usuário com permissão apenas de `SELECT` (`agente_sre`).

2. **Sanitização Pré-LLM (Data Masking Mandatório):**
   - Nenhum dado pessoal identificável (PII) completo pode ser injetado nos prompts da IA:
     - **CPF:** Sempre mascarado (`123.***.***-99`).
     - **Nome:** Apenas primeiro nome e inicial (`Marlon S.`).
     - **Endereço residencial, telefone, e-mail e dados de pagamento:** 100% omitidos da camada de prompt.
   - Apenas metadados de negócio devem trafegar para a IA: `categoria` (ex: VIP, Frotista), `placa_resumida`, `pontos_fidelidade`.

---

## 7. 📁 MAPEAMENTO DOS ARQUIVOS NO REPOSITÓRIO LOCAL

- [`hybrid_rag.py`](file:///c:/Users/Marlon/Documents/Agent%20PC/hybrid_rag.py): Módulo core com a classe `HybridRAGEngine` e coletores `get_sre_metrics()`.
- [`agente_posto.py`](file:///c:/Users/Marlon/Documents/Agent%20PC/agente_posto.py): Agente conversacional com Tool Routing e Streaming de tokens.
- [`benchmark_rag.py`](file:///c:/Users/Marlon/Documents/Agent%20PC/benchmark_rag.py): Suite de benchmark e validação comparativa (Dense vs Sparse vs RRF).
- [`index_produtos.py`](file:///c:/Users/Marlon/Documents/Agent%20PC/index_produtos.py): Pipeline de sincronização e indexação entre ERP e base vetorial.
- [`walkthrough.md`](file:///C:/Users/Marlon/.gemini/antigravity-ide/brain/197d9cc1-5a3b-4b9f-8cb8-079fe5207172/walkthrough.md): Histórico completo de testes, benchmarks e validações.
