# ROADMAP ESTRATÉGICO DE BLINDAGEM JURÍDICA & ARQUITETURA CLEAN ROOM
## Desacoplamento de Schemas Proprietários e Garantia de Interoperabilidade AURA

> **Data de Elaboração:** 15 de Outubro de 2026  
> **Status:** Concluido Integralmente (Todos os 6 Blocos Concluidos com 100% de Sucesso: 200+ Testes Verdes)  
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

### BLOCO 4: Migração Gradual e Cirúrgica do `PostoTools` (Concluído)
**Objetivo:** Fazer com que o `PostoTools` consuma o adaptador do Bloco 3, eliminando gradualmente os comandos SQL diretos de `core/tools.py`.

A migração foi dividida em 4 etapas seguras, mantendo regressão zero (192 testes unitários 100% verdes):

* **Etapa 4.1: Vendas e Loja de Conveniência (Concluída)**
  * Métodos migrados: `consultar_analise_vendas_erp` e `auditar_cesta_conveniencia_vendas_cruzadas`.
  * O algoritmo Apriori de Market Basket passa a receber `List[UniversalSaleReceipt]`.
  * Validação: suíte unitária dedicada em `tests/unit/test_clean_room_stage4_1_sales.py`.
* **Etapa 4.2: Turno e Fuga Financeira (Concluída)**
  * Métodos migrados: `auditar_fechamento_turno` e `auditar_fuga_financeira`.
  * A conciliação de caixa e detecção de quebras passa a receber `List[UniversalCashierShift]`.
  * Validação: suíte unitária dedicada em `tests/unit/test_clean_room_stage4_2_shifts.py`.
* **Etapa 4.3: Tanques e Livro de Movimentação de Combustíveis (LMC) (Concluída)**
  * Métodos migrados: `prever_esgotamento_tanques` e `gerar_relatorio_lmc_anp`.
  * O cálculo de autonomia e tolerância ANP passa a receber `List[UniversalTankReading]`.
  * Validação: suíte unitária dedicada em `tests/unit/test_clean_room_stage4_3_tanks.py`.
* **Etapa 4.4: Pista e Desempenho de Bombas / Frentistas (Concluída)**
  * Método migrado: `auditar_desempenho_pista_frentistas`.
  * A telemetria de vazão, ranking de frentistas e anomalias passa a receber `List[UniversalDispenserLog]`.
  * Validação: suíte unitária dedicada em `tests/unit/test_clean_room_stage4_4_pumps.py`.

---

### BLOCO 5: Higienização de Prompts, RAG e Telemetria (Concluído)
**Objetivo:** Auditar todo o fluxo de linguagem natural e meta-RAG para assegurar que nenhum prompt enviado para modelos generativos ou indexado na base vetorial contenha nomenclaturas de schemas legados.

* **Ações Realizadas:**
  1. Criação do pacote modular `core/prompts/` com `system_prompts.py` e `__init__.py`, desacoplando completamente a engenharia de prompts do `AuraEngine`.
  2. Ajuste dos prompts sistêmicos e de auto-ajuda para utilizar terminologia conceitual de negócios pura, persona executiva, regras estritas de design system e diretrizes anti-alucinação SQL (a LLM nunca gera queries SQL nem cita tabelas relacionais internas).
  3. Higienização das fontes e labels retornados pelo `PostoTools` (ex: "Encerrantes Fisicos de Pista", "Fechamento de Caixa Declarado", "Encerrantes Fiscais de Pista").
  4. Suporte a entidades canônicas universais em `RCAEvidenceItem` (`dispenser_logs`, `cashier_shifts`, `sales_receipts`, `tank_readings`).
  5. Varredura completa da base de conhecimento RAG em `scripts/seed_aura_conhecimento.py`, assegurando zero menções a tabelas legadas.
* **Verificação do Bloco:**
  * Teste unitário de higienização de prompts em `tests/unit/test_prompt_clean_room.py` (8 testes aprovados em 0.21s).

---

### BLOCO 6: Documento de Conformidade & Opt-In do Lojista (Concluído)
**Objetivo:** Criar os termos técnicos e jurídicos oficiais para instalação da AURA no cliente, amparados na legislação brasileira e com verificação técnica automatizada.

* **Artefatos Entregues:**
  1. `docs/compliance/termo_interoperabilidade_lgpd.md`:
     * Instrumento formal de autorização e titularidade de dados (Opt-In do Lojista).
     * Fundamentação jurídica federal completa: LGPD (Art. 7, IX; Art. 2; Art. 18), Lei de Software (Art. 6, I e II), Marco Civil da Internet (Art. 3 e 4) e CDC / Código Civil (vedação ao vendor lock-in abusivo).
     * Certificação técnica de não-interferência: leitura exclusiva via role `aura_service_ro`, transações estritamente `READ ONLY`, sem comandos de escrita e sem alteração de schemas ou DLLs.
     * Isolamento local através do AUPS e portas abstratas (`BaseERPAdapter`).
  2. `core/schemas/compliance.py`:
     * Contrato Pydantic v2 `ComplianceOptInStatus` e `ComplianceVerificationResult`.
  3. `core/compliance_manager.py`:
     * Gerenciador central `ComplianceManager` para registro, hashing SHA-256 e verificação de opt-in durável em SQLite e JSON.
  4. Integração no `AuraEngine` e API FastAPI:
     * Método nativo `check_compliance_opt_in()` no motor cognitivo headless.
     * Endpoints HTTP REST `GET /api/v1/aura/compliance/status` e `POST /api/v1/aura/compliance/opt-in` em `core/aura_api.py`.
  5. Testes Unitários Automatizados:
     * `tests/unit/test_compliance_opt_in.py` com 15 testes unitários validando schema, manager, hashing cross-platform, prevenção de split-brain, endpoints FastAPI e regra inegociável de zero travessões (< 0.45s).

---

## 4. Matriz de Riscos & Plano de Contingência

| Risco Potencial | Probabilidade | Impacto | Estratégia de Mitigação |
| :--- | :---: | :---: | :--- |
| **Aumento de Latência** na conversão de linhas para objetos de domínio | Baixa | Médio | Uso de Pydantic v2 nativo em C/Rust (`core_schema`), garantindo serialização em menos de 2 milissegundos para 500 registros. |
| **Quebra de Testes Legados** durante o desacoplamento | Média | Alto | Adoção do padrão Strangler Fig. O `PostoTools` mantém suas assinaturas públicas intactas; apenas o acesso interno aos dados é redirecionado para o adaptador. |
| **Inconsistência de Tipos** em bancos ERP descalibrados | Média | Médio | Validações flexíveis com `mode="before"` no adaptador para tolerar nulos e números em formatos variados do ERP. |

---

## 5. Conclusão Integral do Roadmap de Blindagem Jurídica & Clean Room

Todos os 6 blocos estruturantes do Roadmap Oficial de Blindagem Jurídica & Arquitetura Clean Room foram concluídos com 100% de sucesso:

1. **Bloco 1 (Domínio Canônico Universal AUPS):** Modelos Pydantic v2 imutáveis para Vendas, Tanques, Bombas e Caixas.
2. **Bloco 2 (Protocolo Abstrato ERP Port):** Interface formal `BaseERPAdapter` para desacoplamento de fornecedores.
3. **Bloco 3 (Driver de Borda PostgreSQL Local):** Conector isolado `PostgresLocalERPAdapter` com role somente-leitura `aura_service_ro`.
4. **Bloco 4 (Migração Gradual do PostoTools - 4 Etapas):** Vendas, Turno, Tanques e Pista migrados para AUPS com compatibilidade retroativa total.
5. **Bloco 5 (Higienização de Prompts, RAG e Telemetria):** Eliminação de nomenclaturas legadas em prompts, base vetorial e labels.
6. **Bloco 6 (Documento de Conformidade & Opt-In do Lojista):** Termo de interoperabilidade formal com fundamentação legal e verificação técnica automatizada via `ComplianceManager`.

O ecossistema AURA opera agora 100% blindado juridicamente, com integridade técnica certificada e suite completa de mais de 200 testes unitários verdes.

