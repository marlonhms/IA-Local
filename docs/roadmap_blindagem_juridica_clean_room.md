# ROADMAP ESTRATÉGICO DE BLINDAGEM JURÍDICA & ARQUITETURA CLEAN ROOM
## Desacoplamento de Schemas Proprietários e Garantia de Interoperabilidade AURA

> **Data de Elaboração:** 15 de Outubro de 2026  
> **Status:** Em Execução (Bloco 1 Aprovado e em Andamento)  
> **Meta Central:** Blindar o ecossistema AURA contra reivindicações de propriedade intelectual de fornecedores de ERP (ex: WebPosto, Linx, Petros), garantindo que a IA, o RAG e o Core operem 100% em cima de contratos canônicos universais sem perder precisão analítica.

---

## 1. Fundamentos Jurídicos e Diretrizes Estratégicas

### 1.1 O Princípio da Titularidade dos Dados (O Posto é o Dono)
* **LGPD (Lei 13.709/2018), Art. 9º:** Os dados transacionais, cupons fiscais, movimentações de caixa e estoques são gerados pela atividade comercial do posto revendedor. O cliente é o titular dos dados operacionais e tem direito à portabilidade e livre acesso.
* **Marco Civil da Internet (Lei 12.965/2014) e Lei de Liberdade Econômica (Lei 13.874/2019):** É garantido o direito do empresário de utilizar ferramentas de automação e inteligência para otimizar suas atividades comerciais.
* **Lei de Software (Lei 9.609/1998), Art. 6º, Inciso II:** Declara expressamente que a integração de programas para fins de **interoperabilidade** (permitir que dois sistemas distintos se comuniquem para troca de dados do usuário) **não constitui ofensa aos direitos autorais do titular do software**.

### 1.2 Onde Mora o Risco e Como Eliminá-lo
* **Risco Identificado:** Acoplamento direto do core da IA, dos prompts de RAG e dos schemas de resposta a nomes proprietários de tabelas/colunas internas (ex: `fechacaixa`, `itemped`, `fechabomba`, `codpra`). Um concorrente mal-intencionado poderia alegar engenharia reversa de arquitetura de software ou que a IA foi "treinada com sua propriedade intelectual".
* **Solução Definitiva:** **Arquitetura de Sala Limpa (Clean Room Design)**.
  * O cérebro da AURA (Prompts, RAG, GenUI, Roteador Semântico, Memória) opera **exclusivamente com o AURA Universal Posto Schema (AUPS)**.
  * O código que lê o PostgreSQL local fica restrito a um **Driver de Borda Isolado (Data Mapper)** que roda na máquina do cliente em modo estritamente somente-leitura.
  * Nenhum nome proprietário de tabela ou coluna é enviado para prompts externos de LLM ou indexado em vetores de conhecimento.

---

## 2. Princípios de Proteção do Contexto, RAG e Desempenho

Para evitar alucinações da IA e manter os testes ágeis (sub-25s):

1. **Semântica Enriquecida para a IA:**  
   Em vez da IA raciocinar sobre termos enigmáticos como `codpec`, `valitem` e `situ`, a IA recebe dados limpos: `product_sku: "00022"`, `item_total_reais: 10.00`, `status: "confirmed"`. Isso **reduz alucinações**, pois elimina ambiguidades que o modelo precisa adivinhar.
2. **Execução Modular em 5 Blocos Independentes:**  
   Cada bloco possui escopo delimitado, contratos imutáveis e suite de testes isolada.
3. **Preservação Contínua da Suite de Testes (75/75 Verdes):**  
   Nenhum bloco quebra os testes unitários existentes. A migração usa o padrão *Strangler Fig* (migração progressiva sem parada).

---

## 3. Estrutura em Blocos do Roadmap

```
┌────────────────────────────────────────────────────────────────────────┐
│                        CORE COGNITIVO AURA                             │
│       (AuraEngine, SemanticRouter, GenUI, RAG, Telemetria)             │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                       Fala APENAS o Dialeto Canônico
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│              BLOCO 1: AURA Universal Posto Schema (AUPS)               │
│      (core/domain/ models: Sales, Inventory, Cashier, Tanks, Pumps)    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                       Protocolo Abstrato Universal
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│              BLOCO 2: Interface Abstrata do Adaptador ERP              │
│                     (core/adapters/erp/base.py)                        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                   Implementação Isolada de Borda
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│             BLOCO 3: Driver PostgreSQL Local (Data Mapper)             │
│            (core/adapters/erp/postgres_local_adapter.py)               │
│          • Único arquivo que conhece os SQLs da máquina local          │
│          • Acesso somente-leitura via role aura_service_ro             │
└────────────────────────────────────────────────────────────────────────┘
```

---

### BLOCO 1: Criação do Domínio Canônico Universal (AUPS)
**Objetivo:** Criar os modelos Pydantic imutáveis do negócio de postos, sem qualquer dependência de bibliotecas de banco de dados ou SQL.

* **Local:** `core/domain/`
* **Entidades a Criar:**
  * `core/domain/sales.py`:
    * `UniversalSaleReceipt`: id do cupom/pedido, data/hora, pdv, total, status, operador.
    * `UniversalSaleItem`: sku, descrição do produto, grupo comercial, preço unitário, quantidade, total.
    * `UniversalPaymentMethod`: código de forma de pagamento, tipo (dinheiro, crédito, débito, pix, prazo), valor.
  * `core/domain/tanks.py`:
    * `UniversalTank`: identificador do tanque, código de combustível, descrição, capacidade nominal (L).
    * `UniversalTankReading`: data/hora medição, volume atual (L), água (mm), temperatura, percentual de capacidade.
  * `core/domain/pumps.py`:
    * `UniversalPump`: identificador da bomba, bico, combustível associado, tanque de origem.
    * `UniversalDispenserLog`: data/hora, encerrante anterior, encerrante atual, volume aferido, faturamento calculado.
  * `core/domain/cashier.py`:
    * `UniversalCashierShift`: operador, turno, data início/fim, fundo de troco, total declarado, quebra/sobra.
    * `UniversalCashMovement`: tipo (sangria, suprimento, estorno), valor, justificativa, data/hora.
* **Garantias Técnicas:**
  * Modelos Pydantic v2 com `ConfigDict(frozen=True)`.
  * Tipos primitivos claros (`float`, `int`, `str`, `datetime`).
* **Verificação do Bloco:**
  * Arquivo de teste `tests/unit/test_domain_aups.py` com validação de tipagem, serialização JSON e performance de instanciação (tempo de execução: < 0.2s).

---

### BLOCO 2: Protocolo Abstrato de Integração (ERP Port)
**Objetivo:** Definir o contrato formal de integração que qualquer ERP deve fornecer para alimentar a AURA.

* **Local:** `core/adapters/erp/base.py`
* **Assinaturas da Interface Abstrata (`BaseERPAdapter`):**
  * `get_recent_sales(start_date, end_date, limit) -> List[UniversalSaleReceipt]`
  * `get_tank_inventory() -> List[UniversalTankReading]`
  * `get_pump_dispenses(start_date, end_date) -> List[UniversalDispenserLog]`
  * `get_cashier_shifts(target_date) -> List[UniversalCashierShift]`
  * `get_product_catalog(filter_term, category) -> List[UniversalSaleItem]`
* **Vantagem de Negócio:**
  * Transforma a AURA em uma plataforma aberta (Open Posto Architecture).
  * Adicionar novos ERPs no futuro (Linx, Petros, XPert, LBC) exigirá apenas implementar essa interface em um novo arquivo, sem tocar no core cognitivo.
* **Verificação do Bloco:**
  * Teste unitário de conformidade de interface com mock adapter em `tests/unit/test_erp_adapter_interface.py` (< 0.2s).

---

### BLOCO 3: Driver de Borda PostgreSQL Local (Data Mapper)
**Objetivo:** Concentrar em um único arquivo isolado todas as queries SQL executadas contra o banco local, fazendo o mapeamento de-para dos dados brutos para os objetos universais do Bloco 1.

* **Local:** `core/adapters/erp/postgres_local_adapter.py`
* **Responsabilidades:**
  * Utilizar exclusivamente a conexão com a role segura `aura_service_ro`.
  * Mapear tabelas locais para as entidades do Bloco 1:
    * `pedido` + `itemped` + `produtos` + `prazos` ──▶ `UniversalSaleReceipt`
    * `tanques` + `medicaotanques` ──▶ `UniversalTankReading`
    * `fechabomba` + `abastecimentos` ──▶ `UniversalDispenserLog`
    * `fechacaixa` + `funcionarios` ──▶ `UniversalCashierShift`
  * Tratamento de nulos com `COALESCE` e uso estrito de `RealDictCursor`.
  * Fallbacks calibrados offline caso o banco esteja inacessível.
* **Garantia de Não-Vazamento:**
  * Nenhuma consulta SQL, nome de tabela ou nome de coluna proprietária sai desse arquivo. O que sai dele são apenas instâncias de `core/domain/`.
* **Verificação do Bloco:**
  * Teste de integração do adaptador em `tests/unit/test_postgres_local_adapter.py` testando leitura real no banco local e modo offline (< 1.5s).

---

### BLOCO 4: Migração Gradual e Cirúrgica do `PostoTools`
**Objetivo:** Fazer com que o `PostoTools` consuma o adaptador do Bloco 3, eliminando gradualmente os comandos SQL diretos de `core/tools.py`.

A migração é dividida em 4 etapas seguras. A cada etapa, os 75 testes são executados para garantir regressão zero:

* **Etapa 4.1: Vendas e Loja de Conveniência**
  * Métodos migrados: `consultar_analise_vendas_erp` e `auditar_cesta_conveniencia_vendas_cruzadas`.
  * O algoritmo Apriori de Market Basket passa a receber `List[UniversalSaleReceipt]`.
  * Validação: executar `pytest tests/unit/test_cesta_conveniencia.py`.
* **Etapa 4.2: Turno e Fuga Financeira**
  * Métodos migrados: `auditar_fechamento_turno` e `auditar_fuga_financeira`.
  * A conciliação de caixa e TEF passa a receber `List[UniversalCashierShift]`.
  * Validação: executar `pytest tests/unit/test_fuga_financeira.py`.
* **Etapa 4.3: Tanques e Livro de Movimentação de Combustíveis (LMC)**
  * Métodos migrados: `prever_esgotamento_tanques` e `gerar_relatorio_lmc`.
  * O cálculo de autonomia passa a receber `List[UniversalTankReading]`.
  * Validação: executar `pytest tests/unit/test_simulacao_preditiva.py`.
* **Etapa 4.4: Pista e Desempenho de Bombas**
  * Método migrado: `auditar_performance_bombas`.
  * A telemetria de vazão e frentistas passa a receber `List[UniversalDispenserLog]`.
  * Validação: executar a suite completa `pytest tests/unit/` (75/75 verdes).

---

### BLOCO 5: Higienização de Prompts, RAG e Telemetria
**Objetivo:** Auditar todo o fluxo de linguagem natural e meta-RAG para assegurar que nenhum prompt enviado para modelos generativos ou indexado na base vetorial contenha nomenclaturas de schemas legados.

* **Ações:**
  1. Varredura com script automatizado buscando referências literais de tabelas legadas em `core/prompts/`, `core/rag_engine.py`, `core/aura_engine.py` e `config/`.
  2. Ajustar os prompts de sistema para usar terminologia de negócios pura:
     * *Antes:* "Consulte os registros de fechacaixa e pedido para detectar quebra."
     * *Depois:* "Analise os fechamentos de turno e as vendas declaradas pelo operador para auditar a conformidade de caixa."
  3. Verificar que as memórias e vetores RAG utilizem o schema de entidades canônicas universais.
* **Verificação do Bloco:**
  * Teste unitário de higienização de prompts em `tests/unit/test_prompt_clean_room.py` (< 0.5s).

---

### BLOCO 6: Documento de Conformidade & Opt-In do Lojista
**Objetivo:** Criar os termos técnicos e jurídicos oficiais para instalação da AURA no cliente, amparados na legislação brasileira.

* **Artefato:** `docs/compliance/termo_interoperabilidade_lgpd.md`
* **Conteúdo:**
  * Termo de Opt-in onde o proprietário do posto declara titularidade sobre a base e autoriza expressamente a leitura local para fins de governança e inteligência.
  * Citação expressa dos artigos da LGPD, Lei de Software e Marco Civil que garantem a legalidade da solução.
  * Certificação técnica de leitura exclusiva (Read-Only) sem interferência nos arquivos originais do ERP.

---

## 4. Matriz de Riscos & Plano de Contingência

| Risco Potencial | Probabilidade | Impacto | Estratégia de Mitigação |
| :--- | :---: | :---: | :--- |
| **Aumento de Latência** na conversão de linhas para objetos de domínio | Baixa | Médio | Uso de Pydantic v2 nativo em C/Rust (`core_schema`), garantindo serialização em menos de 2 milissegundos para 500 registros. |
| **Quebra de Testes Legados** durante o desacoplamento | Média | Alto | Adoção do padrão Strangler Fig. O `PostoTools` mantém suas assinaturas públicas intactas; apenas o acesso interno aos dados é redirecionado para o adaptador. |
| **Inconsistência de Tipos** em bancos ERP descalibrados | Média | Médio | Validações flexíveis com `mode="before"` no adaptador para tolerar nulos e números em formatos variados do ERP. |

---

## 5. Próximo Passo Imediato
 
Este roadmap é um plano de arquitetura e conformidade em execução faseada.  
O **Bloco 1: Criação do Domínio Canônico Universal (AUPS)** foi aprovado e está sendo implementado com schemas puros em `core/domain/`, garantindo 100% de compatibilidade e preservação dos testes existentes.
