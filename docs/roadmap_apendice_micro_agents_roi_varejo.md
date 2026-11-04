# ROADMAP APENDICE: ARQUITETURA DE MICRO-AGENTES DE BAIXO CUSTO E MOTOR UNIVERSAL DE ROI PARA O VAREJO (AURA)

> **Classificacao:** Plano Diretor de Engenharia para Execucao por Agente de IA  
> **Versao:** 2.1.0-RETAIL  
> **Repositorio Base:** `ia-banco-local`  
> **Inspiracao Arquitetural:** Estudo *Bots in Production / Emergent.sh* ("Running 17 Claude Code Bots for $100/Month") adaptado para Escala SaaS B2B Multi-Vertical no Varejo Brasileiro  
> **Regra Estrita de Conformidade:** ZERO travessoes Unicode (`\u2014` e `\u2013`) em todo o codigo, comentarios, docstrings, templates, YAML e testes. Utilizar exclusivamente hifens comuns (`-`), dois pontos (`:`) ou parenteses.

---

## 1. OBJETIVO E CONTEXTO PARA O AGENTE EXECUTOR

Este documento especifica a implementacao tecnica para evoluir a AURA em duas frentes sinergicas:
1. **Eficiencia Extrema de Tokens por Micro-Agentes (Scoped Context & Zero-Token Gates):** Substituir prompts monoliticos e contextos verbosos por **Micro-SOPs (Standard Operating Procedures)** orientados por intencao e vertical, estado compacto em YAML (*Delta-Only Context*) e governanca de orcamento por papel de agente (`agent_role`).
2. **Motor Universal de ROI para o Varejo Geral (Multi-Vertical Retail ROI):** Desacoplar a comprovacao de retorno financeiro (ROI) do nicho exclusivo de postos de combustiveis, permitindo que **Supermercados, Atacarejos, Farmacias, Autocenters, Distribuidoras e Lojas de Conveniencia** recebam auditoria matematica deterministica dos 5 vetores universais de perda do varejo usando os cartuchos declarativos de [`config/domain_packs/`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/config/domain_packs/).

### Diretrizes Inegociaveis de Execucao (Zero Regressao):
1. **Retrocompatibilidade 100% Garantida:** Todos os 874+ testes unitarios existentes (incluindo os contratos atuais de `fuel_convenience` e `/api/v1/partner/stations/{station_id}/roi-diagnostic`) devem continuar passando sem quebra de assinatura.
2. **Zero Alucinacao Matematica:** Nenhum calculo de ROI, perda por vencimento (FEFO), ruptura fantasma de gondola, taxa de adquirente (TEF/Pix) ou custo Selic sobre estoque Curva C pode ser feito por LLM. O Python calcula de forma deterministica e entrega apenas o YAML estruturado para sintese executiva.
3. **Zero-Token Idle Loop:** Nenhum job em background ou micro-bot operacional pode invocar a API do Gemini se o pre-filtro deterministico em Python/SQLite indicar ausencia de novos eventos ou excecoes (`delta == 0`).

---

## 2. ARQUITETURA DOS 4 MODULOS DE IMPLEMENTACAO

```
+---------------------------------------------------------------------------------------+
|          APENDICE MICRO-AGENTES & ROI UNIVERSAL DE VAREJO (4 MODULOS)                 |
+---------------------------------------------------------------------------------------+
| MODULO 1: Decomposicao em Micro-SOPs por Intencao e Vertical (Scoped Context)         |
|           - Arquivo: core/prompts/micro_sops.py + integracao em core/aura_engine.py   |
|           - Corta 45% a 60% dos prompt_tokens injetando apenas a regra da intencao    |
|             parametrizada pelo DomainPack ativo (Supermercado, Farmacia, Posto, etc.) |
+---------------------------------------------------------------------------------------+
| MODULO 2: Governanca e Orcamento de Tokens por Papel de Agente (Agent Role Ledger)    |
|           - Arquivo: core/token_budget.py                                             |
|           - Rastreia consumo por agent_role, intent_category e vertical_pack          |
|           - Impede que triagem operacional de PDV drene a cota executiva do lojista   |
+---------------------------------------------------------------------------------------+
| MODULO 3: Compactador Stateless de Contexto ("Delta-Only YAML State")                 |
|           - Arquivos: core/tenant_memory.py + core/prompts/micro_sops.py              |
|           - Substitui historicos brutos longos por Snapshot YAML <= 150 tokens        |
+---------------------------------------------------------------------------------------+
| MODULO 4: Motor Universal de ROI Multi-Vertical + Squad de Micro-Bots de Operacao     |
|           - Arquivos: core/retail_roi_engine.py + core/ops_micro_bots.py              |
|           - Calcula ROI deterministico para Supermercados, Farmacias, Atacado e Posto |
|           - 3 Micro-Bots autonomos com Zero-Token Gate (RAG Miss, Sync Audit, ROI)    |
+---------------------------------------------------------------------------------------+
```

---

## 3. ESPECIFICACAO DETALHADA POR MODULO

### MODULO 1: Decomposicao em Micro-SOPs por Intencao e Vertical (`Scoped Context`)

#### 1.1. Problema que Resolve
Em vez de enviar um prompt de sistema monolitico com regras de todas as areas da loja em toda requisicao, a AURA passa a operar como uma frota de micro-especialistas: o roteador semantico ([`core/semantic_router.py`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/core/semantic_router.py)) identifica a intencao e o motor injeta exclusivamente o **Micro-SOP** correspondente (~25 a 40 linhas), ja traduzido para o vocabulario do [`DomainPackConfig`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/core/domain/domain_pack_loader.py) ativo.

#### 1.2. Arquivos a Criar / Modificar
- **Criar:** `core/prompts/micro_sops.py`
- **Modificar:** [`core/prompts/system_prompts.py`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/core/prompts/system_prompts.py) e [`core/aura_engine.py`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/core/aura_engine.py)
- **Criar Teste:** `tests/unit/test_micro_sops_and_token_roles.py`

#### 1.3. Catalogo dos 8 Micro-Agentes (SOPs Universais de Varejo)
Implementar em `core/prompts/micro_sops.py` o registro `RETAIL_MICRO_AGENT_SOPS` mapeando cada intencao universal AUDS para um perfil enxuto (`MicroAgentSpec`):

| `agent_role` | Intencoes Atendidas (`SemanticRouter`) | Escopo Estrito do Micro-SOP (Multi-Vertical) | Teto Recomendado (`max_prompt_tokens`) |
| :--- | :--- | :--- | :---: |
| `checkout_auditor_bot` | `auditoria_turno_caixa`, `auditoria_turno` | Conciliacao de PDV/checkout, sangrias atrasadas, sobras/faltas por operador e conformidade Art. 462 CLT. | 1.800 |
| `inventory_rupture_bot` | `previsao_runout_estoque`, `previsao_tanques`, `ruptura_invisivel_gondola`, `perdas_por_vencimento` | Ruptura fantasma de gondola, alerta FEFO de pereciveis/validade, giro de estoque e reposicao por lote multiplo (`default_lot_multiple`). | 1.800 |
| `regulatory_shrinkage_bot` | `lmc_anp`, `conformidade_estoque_regulamentar` | Balanco fisico vs. escriturado: SNGPC/ANVISA (Farmacias), Desossa/Rendimento e Quebra Abrappe (Supermercados) ou LMC ANP (Postos). | 2.000 |
| `pos_productivity_bot` | `desempenho_equipe_conversao`, `desempenho_pista_frentistas` | Produtividade de operadores de checkout/vendedores (itens/min, ticket medio, taxa de conversao de agregados). | 1.600 |
| `cross_merchandising_bot` | `market_basket_cross_sell`, `conveniencia_vendas_cruzadas`, `rentabilidade_por_secao` | Afinidade de cesta (Market Basket), combos de encarte, cross-merchandising entre secoes (padaria, acougue, hortifruti, conveniencia). | 1.800 |
| `financial_erosion_bot` | `erosao_financeira_tef_selic`, `auditoria_fuga_financeira` | Auditoria de taxas efetivas de cartao/TEF/Pix, antecipacao de recebiveis e custo de capital parado em estoque Curva C vs. Selic. | 1.800 |
| `margin_causal_bot` | `raio_x_causal_margem`, `investigar_causa_raiz` | Decomposicao matematica de erosao de margem bruta por secao/categoria, impacto de markdown e custo de reposicao. | 2.200 |
| `erp_sop_triage_bot` | `procedimento_sistema`, `ajuda_sistema` | Triagem rapida passo a passo de operacao do ERP e telas usando apenas os top-3 chunks do RAG Multicamada. | 1.400 |

#### 1.4. Assinaturas Exigidas em `core/prompts/micro_sops.py`
```python
from dataclasses import dataclass
from typing import Any
from core.domain.domain_pack_loader import DomainPackConfig

@dataclass(frozen=True)
class MicroAgentSpec:
    agent_role: str
    universal_intent: str
    preferred_model: str
    max_prompt_tokens: int
    sop_template: str

def resolve_micro_agent_spec(intent: str, pack: DomainPackConfig | None = None) -> MicroAgentSpec:
    """Resolve a especificacao do micro-agente a partir da intencao e do DomainPack."""

def build_scoped_micro_prompt(
    intent: str,
    pergunta_sanitizada: str,
    tool_output_yaml: str,
    compact_state_yaml: str = "",
    pack: DomainPackConfig | None = None,
    dados_filial: dict[str, Any] | None = None,
    genui_active: bool = False,
) -> tuple[str, MicroAgentSpec]:
    """
    Constroi um prompt cirurgico contendo apenas o SOP da intencao ativa e o vocabulario
    da vertical (ex: gondola/checkout/operador_caixa para supermercados ou tanque/bomba/frentista
    para postos), reduzindo em 45% a 60% o tamanho do prompt frente ao prompt monolitico.
    """
```

---

### MODULO 2: Governanca e Orcamento de Tokens por Papel de Agente (`core/token_budget.py`)

#### 2.1. Contexto e Regra de Negocio
Seguindo a telemetria do caso *17 Bots for $100/Month*, precisamos saber exatamente quanto cada micro-agente consome em cada loja (`filial_id`) e aplicar *smart downgrade* por papel: se um operador de caixa fizer dezenas de perguntas operacionais (`erp_sop_triage_bot`), ele jamais pode esgotar o orcamento reservado para o diagnostico financeiro e de margem do diretor da rede (`margin_causal_bot`).

#### 2.2. Modificacoes em [`core/token_budget.py`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/core/token_budget.py)
1. **Migracao Idempotente do Schema SQLite (`_init_db`):**
   - Garantir que `aura_token_ledger` possua as colunas adicionais (adicionadas via `ALTER TABLE` seguro caso o banco ja exista):
     - `agent_role TEXT DEFAULT 'general_assistant'`
     - `intent_category TEXT DEFAULT 'general'`
     - `vertical_pack TEXT DEFAULT 'fuel_convenience'`
2. **Evolucao de `record_usage(...)`:**
   - Aceitar parametros opcionais retrocompativeis: `agent_role: str = "general_assistant"`, `intent_category: str = "general"`, `vertical_pack: str = "fuel_convenience"`.
3. **Novo Metodo `get_usage_by_agent_role(self, filial_id: str, days: int = 30) -> list[dict[str, Any]]`:**
   - Retorna o breakdown percentual e absoluto de tokens e custo (BRL/USD) agrupado por `agent_role` e `intent_category`, permitindo auditar o peso de cada micro-agente na operacao.
4. **Novo Metodo `recommend_model_for_role(self, filial_id: str, agent_role: str, requested_model: str = "gemini-2.5-flash") -> dict[str, Any]`:**
   - Implementa roteamento economico de modelos:
     - Micro-agentes de triagem operacional (`erp_sop_triage_bot`, `pos_productivity_bot`) sao fixados em `gemini-2.5-flash` (menor custo).
     - Se o consumo diario da filial ultrapassar `alert_threshold_pct` (ex: 80%), faz downgrade automatico de qualquer chamada `pro` para `gemini-2.5-flash` e ativa compressao maxima de contexto, mantendo os bots operacionais sem estourar a fatura mensal.

---

### MODULO 3: Compactador Stateless de Contexto ("Delta-Only YAML State")

#### 3.1. Contexto e Regra de Negocio
No estudo dos 17 bots, a maior economia de tokens de entrada veio de tornar os agentes **stateless entre execucoes**: em vez de concatenar 10 mensagens antigas do chat no prompt, o sistema mantem um **Estado Compacto da Loja em YAML** (`<= 150 tokens`) atualizado pelos motores deterministicos.

#### 3.2. Arquivos a Modificar
- [`core/tenant_memory.py`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/core/tenant_memory.py)
- `core/prompts/micro_sops.py`

#### 3.3. Especificacao Tecnica
Implementar a funcao `build_compact_retail_state_yaml(filial_id: str, vertical: str, kpi_snapshot: dict[str, Any], recent_turns: list[dict[str, Any]] | None = None) -> str`:
- Converte o estado operacional atual da loja em um bloco YAML enxuto (sem chaves JSON verbosas, sem espacamento desnecessario e sem repeticao de texto das respostas passadas).
- Limita o resumo de continuidade conversacional aos ultimos **2 turnos sintetizados** (apenas `intent`, `entidade_alvo` e `veredito_numerico`), garantindo uma reducao superior a **70% nos tokens de historico de sessao**.

---

### MODULO 4: Motor Universal de ROI Multi-Vertical e Squad de Micro-Bots de Operacao

#### 4.1. Contexto e Regra de Negocio
Para que a AURA comprove a **Garantia Auditada de 3x ROI em 90 dias** em **qualquer segmento do varejo** (Supermercados, Farmacias, Atacarejos, Autocenters e Postos), criaremos o motor [`core/retail_roi_engine.py`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/core/retail_roi_engine.py) parametrizado pelos cartuchos de [`config/domain_packs/`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/config/domain_packs/).

#### 4.2. Novos Domain Packs e Expansao dos Existentes
1. Preservar e utilizar [`config/domain_packs/pack_retail_supermarket.yaml`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/config/domain_packs/pack_retail_supermarket.yaml), [`config/domain_packs/pack_wholesale_distribution.yaml`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/config/domain_packs/pack_wholesale_distribution.yaml) e [`config/domain_packs/pack_fuel_convenience.yaml`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/config/domain_packs/pack_fuel_convenience.yaml).
2. Criar dois novos cartuchos declarativos em `config/domain_packs/`:
   - `config/domain_packs/pack_pharmacy_health.yaml` (`vertical: "pharmacy_retail"`, foco em SNGPC/ANVISA, controle de vencimento FEFO de medicamentos/dermocosmeticos, perdas de alto valor PAR/GLP-1 e tabela CMED).
   - `config/domain_packs/pack_autocenter_parts.yaml` (`vertical: "autocenter_retail"`, foco em auditoria de oleo/insumos a granel, margem combinada Pecas + Mao de Obra por Ordem de Servico e capital imobilizado em pecas Curva C).

#### 4.3. Os 5 Vetores Universais de ROI no Varejo (`core/retail_roi_engine.py`)
Implementar `compute_universal_retail_roi(store_id: str, staging_store: Any, domain_pack: str = "retail_supermarket", monthly_subscription_brl: float = 490.0) -> dict[str, Any]`:

| Vetor Universal | Supermercados / Atacarejos (`retail_supermarket`) | Farmacias (`pharmacy_health`) | Atacado / Distribuidora (`wholesale_distribution`) | Autocenters / Autopecas (`autocenter_parts`) | Postos e Conveniencia (`fuel_convenience`) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Quebra Fisica e Perecibilidade** (`inventory_and_perishability_shrinkage_brl`) | Perda por validade (FEFO), quebra de hortifruti/padaria e rendimento de desossa no acougue (indice Abrappe 2.1% a 3.8%). | Vencimento de lotes FEFO, divergencia de psicotropicos SNGPC e furto de itens de alto valor (PAR). | Avarias de movimentacao no CD, quebra de paletizacao e perda de ativos retornaveis (vasilhames). | Desvio de fluido/oleo a granel vs. OS faturadas e extravio de pecas de giro rapido. | Variacao volumetrica de tanques no LMC (tolerancia ANP 0.6%) e evaporacao/descarga. |
| **2. Ruptura de Gondola e Cancelamentos PDV** (`pos_cancellations_and_rupture_brl`) | Ruptura fantasma (estoque virtual > 0 com zero vendas no checkout) + cancelamentos anomalos de cupom (Z-Score). | Falta de medicamento de uso continuo em prateleira com saldo virtual travado + estornos de PDV. | Corte de pedido por furo de estoque virtual no faturamento de rota + devolucoes em doca. | Perda de venda de servico por falta de filtro/peca basica com saldo incorreto no ERP. | Cancelamentos na conveniencia e bicos inativos em horario de pico. |
| **3. Divergencia de Checkout e Caixa** (`checkout_and_cash_discrepancy_brl`) | Quebras de fechamento de operadores de checkout, sangrias retidas e divergencias de balanca no caixa. | Diferencas de fechamento de turno de caixa e conciliacao de convenios/descontos de laboratorio (PBM). | Divergencia no acerto cego de rota de motoristas (canhotos vs. Pix vs. numerario devolvido). | Descontos manuais nao autorizados em balcao e divergencia no fechamento de OS. | Diferenca entre encerrantes de bomba e valores declarados no fechamento de turno. |
| **4. Arbitragem de Compra e Markdown Preventivo** (`procurement_and_markdown_arbitrage_brl`) | Liquidacao dinamica (*Markdown* preventivo 5 a 10 dias antes do vencimento salvando 60% do CMV) + compra por lote otimo. | Compra otimizada ante reajuste anual CMED e liquidacao preventiva de dermocosmeticos proximos ao vencimento. | Otimizacao de cubagem de frete e compra em palete fechado com bonificacao de industria. | Margem combinada (*Blended Margin*) Pecas + Mao de Obra e compra programada de pneus/oleo. | Arbitragem de compartimento de carreta (setas de 5.000 L) e repricing competitivo regional. |
| **5. Capital de Giro (Selic) e Erosao de Taxas** (`working_capital_and_acquirer_erosion_brl`) | Capital imobilizado em produtos Curva C (> 60 dias de cobertura) remunerado pela Selic + divergencia de taxas TEF/Pix. | Estoque parado de perfumaria de baixo giro vs. Selic + taxas de parcelamento e antecipacao de cartoes. | Inadimplencia/atraso de boletos B2B e estoque obsoleto no galpao vs. custo financeiro Selic. | Pecas especificas sem giro ha > 90 dias drenando caixa vs. Selic + taxas de parcelamento em 10x. | Estoque morto de conveniencia/lubrificantes vs. Selic + sobretaxas de adquirentes TEF. |

#### 4.4. Endpoints B2B no [`core/partner_api.py`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/core/partner_api.py)
- Manter intacto o endpoint existente `GET /api/v1/partner/stations/{station_id}/roi-diagnostic` (aceitando opcionalmente query param `?domain_pack=retail_supermarket` com default `fuel_convenience` para nao quebrar nenhum teste atual).
- Adicionar a rota universal `GET /api/v1/partner/stores/{store_id}/roi-diagnostic` (default `domain_pack="retail_supermarket"`), retornando o contrato universal enriquecido com `vertical`, `domain_pack_id`, `vocabulary_applied`, `universal_vectors_brl` e `summary` (incluindo `guarantee_3x_met`).

#### 4.5. Squad de 3 Micro-Bots Operacionais com "Zero-Token Gate" (`core/ops_micro_bots.py`)
Implementar em `core/ops_micro_bots.py` tres micro-bots autonomos inspirados diretamente na arquitetura *Bots in Production*:
1. **`RagMissTrackerBot`:**
   - Inspeciona logs/consultas locais onde o score do RAG ficou abaixo de `0.45`.
   - **Zero-Token Gate:** Se `len(low_score_queries) == 0`, encerra em `< 2ms` com `llm_called = False` e `tokens_used = 0`. Se houver lacunas, agrupa os topicos faltantes por vertical (`supermarket_retail`, `pharmacy_retail`, `fuel_retail`) para curadoria.
2. **`PartnerSyncContractBot`:**
   - Audita falhas de invariantes fisicas ou drift de colunas nos lotes enviados pelos ERPs parceiros via `raw-sync`.
   - **Zero-Token Gate:** So gera parecer de correcao quando detecta rejeicoes ou anomalias reais no staging.
3. **`WeeklyRetailRoiDigestBot`:**
   - Roda sobre todas as lojas ativas no `PartnerStagingStore`, calcula o ROI acumulado de cada CNPJ via `compute_universal_retail_roi` de forma 100% deterministica e formata o Resumo Executivo de Retencao (*Risk-Reversal 90 dias*) pronto para disparo via Webhook/WhatsApp com custo zero de LLM.

---

## 4. CRITERIOS DE ACEITE E SUITE DE TESTES

Para considerar este Apendice **100% Concluido**, o agente executor deve criar e validar:
1. `tests/unit/test_micro_sops_and_token_roles.py`:
   - Comprova que `build_scoped_micro_prompt` reduz o tamanho do prompt em pelo menos **45%** comparado ao prompt monolitico.
   - Comprova que o vocabulario do prompt muda dinamicamente conforme o `DomainPackConfig` (`gondola`/`checkout` para supermercados vs `tanque`/`bomba` para postos vs `SNGPC`/`FEFO` para farmacias).
   - Comprova que `TokenBudgetManager` registra e agrega corretamente `agent_role`, `intent_category` e `vertical_pack`, aplicando downgrade para `gemini-2.5-flash` quando o orcamento atinge o limiar de alerta.
   - Comprova que `build_compact_retail_state_yaml` gera snapshots YAML concisos (`<= 150 tokens` estimados).
2. `tests/unit/test_universal_retail_roi_and_bots.py`:
   - Valida o calculo deterministico de `compute_universal_retail_roi` para todas as 5 verticais (`retail_supermarket`, `pharmacy_health`, `wholesale_distribution`, `autocenter_parts`, `fuel_convenience`).
   - Valida o endpoint `GET /api/v1/partner/stores/{store_id}/roi-diagnostic` e o parametro `domain_pack` em `GET /api/v1/partner/stations/{station_id}/roi-diagnostic`.
   - Valida os 3 micro-bots (`RagMissTrackerBot`, `PartnerSyncContractBot`, `WeeklyRetailRoiDigestBot`) comprovando que o **Zero-Token Gate** retorna `tokens_used == 0` quando nao ha anomalias ou quando opera em modo deterministico.
3. **Verificacao Global de Qualidade:**
   - `ruff check . --select E9,F63,F7,F82` com **zero erros**.
   - Varredura de zero travessoes Unicode (`\u2014` e `\u2013`) em todos os arquivos criados/modificados.
   - Execucao completa da suite `pytest` passando com 100% de sucesso.

---

## 5. PROMPT PRONTO PARA SOLICITAR A EXECUCAO AO AGENTE

Quando desejar que o agente execute este roadmap, basta enviar o comando abaixo:

> **Comando para o Agente:**  
> *"Execute integralmente o plano descrito em `docs/roadmap_apendice_micro_agents_roi_varejo.md` (Modulos 1 a 4), criando os novos Domain Packs de varejo (`pack_pharmacy_health.yaml` e `pack_autocenter_parts.yaml`), os Micro-SOPs por intencao (`core/prompts/micro_sops.py`), a governanca de orcamento por `agent_role` (`core/token_budget.py`), o motor universal de ROI para o varejo (`core/retail_roi_engine.py`), o squad de micro-bots operacionais (`core/ops_micro_bots.py`) e toda a suite de testes unitarios exigida na Secao 4, garantindo zero regressoes e zero travessoes Unicode."*
