# 🧭 ROADMAP MESTRE DE EVOLUÇÃO: AURA UNIVERSAL DECISION ENGINE & ACTIONABLE BI
> **Documento de Diretrizes para Agente Autônomo de Código (Antigravity IDE)**  
> **Status:** Ativo | **Prioridade:** Alta | **Padrão de Qualidade:** Mission-Critical / Enterprise  
> **Objetivo Estratégico:** Evoluir a AURA de um assistente vertical sob demanda para uma **Plataforma Universal de Inteligência Prescritiva, Diagnóstico Causal Zero-Click e Execução Autônoma (Actionable BI)**, superando o paradigma de dashboards de BI estáticos tradicionais e mantendo 100% de compatibilidade com a suíte de +400 testes existentes.

---

## 🛡️ 0. REGRAS DE ENGAJAMENTO DO AGENTE (ANTIGRAVITY GUARDRAILS)

Antes de modificar qualquer arquivo do projeto, o Agente de Código DEVE respeitar estas 5 leis invioláveis:

1. **Não-Regressão Absoluta (+400 Testes Verdes):**
   - Nenhuma classe, método ou contrato existente (`AUPS`, `PostoTools`, `SemanticRouter`, `HybridRAGEngine`, `CentralLogSanitizer`) pode ser removido ou ter sua assinatura quebrada.
   - Toda generalização de domínio deve usar **Aliases de Retrocompatibilidade** (Pydantic / TypeAliases) para que todos os testes atuais em `tests/unit/` e `scripts/test_*.py` continuem passando 100%.
2. **Isolamento Clean Room & Read-Only Inegociável:**
   - Toda conexão com o banco transacional do cliente (`core/db_pool.py` e `core/adapters/erp/`) deve forçar em nível de sessão/driver:
     `options="-c default_transaction_read_only=on -c statement_timeout=4000 -c lock_timeout=1000"`.
   - Jamais gerar queries com `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, `ALTER` ou `DROP` contra o banco do ERP.
3. **Proteção de Hardware do PDV (`Hardware Circuit Breaker`):**
   - Qualquer nova ferramenta analítica pesada deve respeitar a trava do `core/resource_watchdog.py` (abortar/adiar se CPU ou RAM do host > 80%).
4. **Anatomia Executiva Obrigatória (Padrão AURA):**
   - Todo output analítico (seja via Chat SSE ou Card GenUI Zero-Click) deve conter obrigatoriamente:
     1. `diagnostico_direto`: 1 linha executiva com severidade clara;
     2. `prova_matematica`: Memória de cálculo determinística, impacto em R$ e comparativo percentual;
     3. `acao_recomendada_hitl`: Payload estruturado para decisão e execução imediata em 1-clique (WhatsApp / Ordem Interna / Campanha).
5. **Execução Incremental por Fases:**
   - Conclua uma Sub-Fase por vez, crie os testes unitários correspondentes em `tests/unit/` e execute `pytest` antes de avançar para a próxima etapa.

---

## 📦 FASE 1: SANITIZAÇÃO CLEAN ROOM & ARQUITETURA "AURA UNIVERSAL CORE" (AUDS)

**Objetivo:** Remover qualquer acoplamento exclusivo ao nicho de postos de combustíveis no núcleo do sistema, transformando a AURA em um motor horizontal plugável em qualquer banco de dados relacional através de **Domain Packs declarativos em YAML**, além de higienizar metadados sensíveis da documentação.

### 1.1. Higienização de Rastros Locais e Metadados (Segurança de Repositório)
- **Arquivos-Alvo:** `README.md`, `docs/*.md`, `termo_interoperabilidade_lgpd.md`, `scripts/test_ponte_tailscale.py`.
- **Tarefas do Agente:**
  - [x] Substituir todas as ocorrências de caminhos absolutos locais (`file:///c:/Users/Marlon/...` ou `file:///C:/Users/Marlon/...`) por links relativos limpos do repositório (ex: `./core/semantic_router.py`).
  - [x] Substituir todas as menções ao hostname específico `marlonh-supwp` por `aura-edge-node01`.
  - [x] Remover menções nominais a marcas de ERPs proprietários onde houver risco de conflito de propriedade intelectual, padronizando para nomenclatura técnica neutra.

### 1.2. Evolução de `AUPS` para `AUDS` (`AURA Universal Domain Schema`)
- **Arquivos-Alvo:** `core/domain/`, `core/schemas/`, `core/adapters/erp/yaml_data_mapper.py`.
- **Tarefas do Agente:**
  - [x] Criar em `core/domain/universal_entities.py` os contratos canônicos universais em Pydantic v2:
    - `UniversalSaleTransaction` (generaliza `UniversalSaleReceipt` para qualquer venda de PDV/Faturamento).
    - `UniversalInventoryNode` (generaliza `UniversalTankReading` para qualquer estoque físico, gôndola, depósito ou reservatório volumétrico, suportando `lot_multiple` genérico em vez de apenas múltiplos fixos de 5.000L).
    - `UniversalEquipmentTelemetry` (generaliza `UniversalDispenserLog` para qualquer equipamento, sensor de vazão, terminal ou leitor).
    - `UniversalCashierSession` (generaliza `UniversalCashierShift` para qualquer fechamento de turno/caixa).
    - `UniversalFinancialSettlement` (novo contrato para recebíveis de cartões/TEF, PIX, taxas de adquirentes, prazos D+N e contas a pagar).
  - [x] Manter `UniversalSaleReceipt = UniversalSaleTransaction` (e demais aliases) nos arquivos originais de `core/domain/` para garantir 100% de compatibilidade com os testes legados.

### 1.3. Sistema de Cartuchos de Negócio (`Domain Packs YAML`)
- **Arquivos-Alvo:** `config/domain_packs/` (novo diretório), `config/erp_mappings/`, `core/semantic_router.py`.
- **Tarefas do Agente:**
  - [x] Criar a estrutura de configuração de vertical em `config/domain_packs/`:
    - `pack_fuel_convenience.yaml`: Define vocabulário, tolerâncias (ex: ANP ±0.6%, lote de 5.000L, vazão L/min) e intenções específicas de postos e conveniência.
    - `pack_retail_supermarket.yaml`: Define vocabulário e regras para varejo geral, supermercados e farmácias (ruptura de gôndola, perecibilidade, lote mínimo de caixas/pallets, margem por seção, quebra de inventário).
    - `pack_wholesale_distribution.yaml`: Define regras para distribuidoras e atacado (giro de estoque, inadimplência, ticket médio por vendedor, curva ABC).
  - [x] Atualizar o `SemanticRouter` (`core/semantic_router.py`) para mapear as intenções operacionais universais (`auditoria_turno_caixa`, `previsao_runout_estoque`, `desempenho_equipe_conversao`, `market_basket_cross_sell`, `erosao_financeira_tef_selic`, `raio_x_causal_margem`), preservando os nomes das 11 rotas originais como aliases diretos.
- **Critério de Aceite (Pytest):** Criar `tests/unit/test_auds_domain_packs.py` validando a carga de múltiplos Domain Packs sem quebra das 11 rotas originais.

---

## ⚡ FASE 2: PARADIGMA "ZERO-CLICK GenUI" & VITRINE DE SEGURANÇA AUDITÁVEL

**Objetivo:** Eliminar a sensação de que o usuário "precisa pensar em uma pergunta para extrair valor" (principal objeção de quem está acostumado com dashboards estáticos) e comprovar visualmente a segurança da conexão local com o banco de dados.

### 2.1. Feed Executivo Zero-Click (O Anti-Dashboard Estático)
- **Conceito:** Um BI tradicional joga 30 gráficos estáticos na tela (misturando métricas normais com problemas). A AURA deve abrir o Cockpit exibindo automaticamente apenas os **Top 3 a 5 Cards de Exceção e Oportunidade Financeira do Momento** (Zero-Click).
- **Arquivos-Alvo:** `core/proactive_daemon.py`, `core/aura_api.py`, `core/schemas/`, `web/index.html`, `web-frontend/src/types/aura-contracts.ts`.
- **Tarefas do Agente:**
  - [x] Criar no `core/proactive_daemon.py` o método `generate_executive_zero_click_feed(tenant_id: str) -> List[ExecutiveExceptionCard]`.
  - [x] O motor deve varrer silenciosamente em background (respeitando o `Hardware Circuit Breaker` e cache TTL) os indicadores vitais e ranquear pelo **Maior Impacto Financeiro em R$ (`financial_impact_brl`)**:
    1. Divergências/Quebras de Caixa ou Sangrias não conciliadas no turno atual;
    2. Risco de Run-Out de Estoque/Tanque nas próximas 48h ou oportunidade de compra otimizada;
    3. Queda de Margem / Conversão da equipe abaixo da meta no dia;
    4. Oportunidade de Combo (Market Basket Lift >= 2.0) ou Capital Morto estagnado;
    5. Anomalia de Equipamento/Operação ou Taxa Financeira divergente.
  - [x] Expor o endpoint REST/SSE `GET /api/v1/cockpit/zero-click-feed` em `core/aura_api.py`.
  - [x] Atualizar o Cockpit Web (`web/index.html` e `web-frontend/`) para renderizar o **Feed Executivo de Prontidão** no topo da interface assim que a página carrega, antes mesmo de o usuário digitar qualquer comando no chat.

### 2.2. Componente "Security by Design & SQL Auditável" no Cockpit e Showcase
- **Arquivos-Alvo:** `core/compliance_manager.py`, `core/aura_api.py`, `web/showcase.html`, `web/index.html`.
- **Tarefas do Agente:**
  - [x] Adicionar no `core/compliance_manager.py` o método `get_live_security_telemetry()` que retorna em tempo real:
    - Status da sessão PostgreSQL (`default_transaction_read_only: "on"`, `statement_timeout: "4000ms"`, `lock_timeout: "1000ms"`);
    - Status do `Hardware Circuit Breaker` (CPU %, RAM %, Estado do Circuito: `FECHADO_SEGURO` ou `ABERTO_PROTECAO_PDV`);
    - Contador de entidades PII sanitizadas na sessão (`CentralLogSanitizer`);
    - Hash SHA-256 do Termo de Interoperabilidade e Clean Room ativo (`termo_interoperabilidade_lgpd.md`).
  - [x] Criar na interface (`web/showcase.html` e `web/index.html`) o modal/drawer **"Arquitetura de Confiança & Script SQL Auditável"**, exibindo o diagrama de 3 camadas (Banco Local -> Borda Clean Room Read-Only -> Motor GenUI) e o botão para copiar/inspecionar o script SQL exato da role `aura_service_ro`.
- **Critério de Aceite (Pytest):** Criar `tests/unit/test_zero_click_cockpit_and_security.py`.

---

## 🧠 FASE 3: NOVOS MOTORES COGNITIVOS PRESCRITIVOS (SUPERANDO O BI DESCRITIVO)

**Objetivo:** Enquanto um BI comum apenas agrupa vendas e formas de pagamento do passado (`SELECT SUM`), a AURA deve cruzar dados transacionais com indicadores macroeconômicos oficiais (`BACEN`, `ANP`, `CONFAZ`) e modelos matemáticos causais para entregar respostas que nenhum dashboard estático consegue calcular.

### 3.1. Motor 1: Auditor de Erosão Financeira, Taxas TEF/Pagamentos & Arbitragem Selic
- **Supera qual tela do BI comum?** Supera o gráfico estático de "Vendas por Forma de Pagamento".
- **Arquivos-Alvo:** `core/tools.py`, `core/integrations/public_data/bacen_connector.py`.
- **Lógica Matemática a Implementar (`PostoTools.auditar_erosao_financeira_e_recebiveis`):**
  - [x] Cruzar o volume vendido por meio de pagamento (PIX, Dinheiro, Débito, Crédito Vista, Crédito Parcelado, Convênios/Frotas) com as taxas MDR contratadas vs. taxas reais descontadas nos recebíveis:
    $$\text{Perda por Divergência de Taxa} = \sum \text{Venda}_i \times (\text{Taxa Descontada}_i - \text{Taxa Contratada}_i)$$
  - [x] Consumir a **Taxa Selic Diária Anualizada (Série 11 do BACEN SGS)** já presente no cache local (`aura_core.bacen_series_historicas`) para calcular o **Valor Presente Líquido (VPL)** das vendas a prazo e o custo real de antecipação de recebíveis frente aos boletos/carretas que vencem nas próximas 72h.
  - [x] Entregar diagnóstico prescritivo: apontar qual modalidade está corroendo a margem líquida e qual a forma mais barata de cobrir o fluxo de caixa da semana.

### 3.2. Motor 2: Caçador de Capital Morto (Selic) & Ruptura Invisível de Gôndola
- **Supera qual tela do BI comum?** Supera a tabela estática de "Posição de Estoque e Produtos Mais Vendidos".
- **Arquivos-Alvo:** `core/tools.py`.
- **Lógica Matemática a Implementar (`PostoTools.diagnosticar_capital_morto_e_ruptura_invisivel`):**
  - [x] **Custo de Oportunidade de Estoque Parado (Capital Morto):** Identificar itens com estoque positivo sem giro há mais de $N$ dias (ex: 30/45 dias) e multiplicar o capital imobilizado ($\text{Estoque} \times \text{Custo Unitário}$) pela Taxa Selic Diária acumulada no período. Sugerir automaticamente um **Combo de Liquidação** pareando o item encalhado com um produto de alto giro identificado pelo motor Apriori (`Lift >= 2.0`), mostrando que um desconto de $X\%$ custa menos que manter o dinheiro parado.
  - [x] **Detecção de Ruptura Fantasma (Estoque Virtual vs. Geladeira/Gôndola Vazia):** Detectar itens de Curva A cujo saldo no ERP é $> 0$, mas cuja velocidade horária de venda ($T_{\text{hora}}$) caiu a zero por mais de $K$ horas consecutivas em horário de pico (ex: 3 desvios-padrão abaixo da média histórica daquele dia da semana/turno). Emitir alerta imediato de reposição física.

### 3.3. Motor 3: Raio-X de Sangria de Margem (Decomposição Causal Waterfall)
- **Supera qual tela do BI comum?** Supera o gráfico de "Evolução de Lucro Bruto / CMV".
- **Arquivos-Alvo:** `core/tools.py`.
- **Lógica Matemática a Implementar (`PostoTools.diagnosticar_variacao_margem_causal`):**
  - [x] Quando questionada sobre por que o lucro ou a margem caiu (ou automaticamente no Feed Zero-Click), decompor a variação financeira total ($\Delta \text{Margem R\$}$) entre o período atual e o período anterior em 4 fatores matemáticos isolados:
    1. **Efeito Custo de Reposição (CMV Não Repassado):** Aumento no custo da Nota Fiscal de entrada sem atualização imediata do preço de venda no PDV/Bomba (calculando quantas horas o estabelecimento vendeu com margem comprimida e quantos R$ deixou na mesa);
    2. **Efeito Mix / Conversão ($\Delta \tau$):** Queda na proporção de venda de produtos premium/aditivados de maior margem em relação aos básicos;
    3. **Efeito Volume Puro ($\Delta V$):** Retração de fluxo de clientes em horários específicos (horários de vale);
    4. **Efeito Perdas / Descontos / Quebras ($\Delta \text{Perdas}$):** Descontos manuais concedidos no PDV, aferições ou variações físicas de inventário/LMC.

### 3.4. Motor 4: Simulador de Elasticidade Dinâmica & Otimizador de Lote
- **Supera qual tela do BI comum?** Supera o relatório de "Sugestão de Compras Simples".
- **Arquivos-Alvo:** `core/tools.py`, `core/integrations/public_data/anp_connector.py`.
- **Lógica Matemática a Implementar (`PostoTools.simular_elasticidade_e_lote_compra`):**
  - [x] Cruzar o espaço livre de estoque/tanque (*Ullage*) com o lote mínimo de compra (ex: múltiplos de 5.000L ou caixas fechadas) e o posicionamento de preço frente ao mercado local (Quartis Q1/Q2/Q3).
  - [x] Simular quanto uma micro-redução promocional temporária ou campanha via WhatsApp acelera a taxa de queima horária ($T_{\text{hora}}$) para abrir o espaço físico exato necessário para receber um lote fechado antes do fim de semana, maximizando o desconto logístico do fornecedor.
- **Critério de Aceite da Fase 3 (Pytest):** Criar `tests/unit/test_prescriptive_engines_phase3.py` cobrindo os 4 novos motores com dados sintéticos e mocks das séries do BACEN/ANP.

---

## 🎨 FASE 4: LOOP FECHADO DE AÇÃO ("ACTIONABLE BI") & REFATORAÇÃO UI/UX APPLE STUDIO

**Objetivo:** Garantir que toda decisão tomada na AURA seja executada em 1 clique (gravando diretivas com Persist-First na Transactional Outbox SQLite WAL, gerando briefings de áudio com visual Waveform e instruções táticas de pista) e refatorar a interface do **Cockpit Nativo da AURA** para um design executivo ultra-clean (padrão Apple Studio / Linear / ElevenLabs), eliminando o aspecto de planilha técnica.

### 4.1. Integração do Loop Fechado: `AURA Core` -> `Transactional Outbox` -> Diretivas HITL em 1-Clique
- **Arquivos-Alvo:** `core/outbox.py`, `core/aura_api.py`, `core/schemas/genui.py`.
- **Tarefas do Agente:**
  - [x] Padronizar o envelope de ação `ActionableDirectivePayload` gerado pelos botões HITL dos cards da AURA, contendo:
    - `roteiro_voz_consultor`: Texto natural humanizado pronto para síntese de voz (TTS / Briefing Executivo);
    - `treinamento_equipe_15s`: Instrução tática direta para o gerente/equipe de pista em 15 segundos;
    - `campanha_clientes_whatsapp`: Mensagem persuasiva segmentada para recuperação de fluxo/margem.
  - [x] Integrar com `core/outbox.py`: Endpoint `POST /api/v1/aura/directives/dispatch` persistindo na outbox SQLite WAL com deduplicação por `idempotency_key` e rastreabilidade total.
  - [x] Endpoint `GET /api/v1/aura/directives/recent` e `GET /api/v1/aura/directives/{id}/audio-waveform` para inspeção e simulação de áudio.

### 4.2. Refatoração UI/UX do Cockpit Executivo AURA (Padrão Apple Studio / Linear)
- **Diretrizes Visuais do Frontend (`web/index.html` e `web/js/aura-cockpit.js`):**
  1. **Limpeza Semântica Total (Ocultar Sala de Máquinas):**
     - [x] Substituir badges sobrecarregados por indicador minimalista: ponto verde pulsante + `Inteligência Ativa (Zero-Click)`.
  2. **Eliminação do "Box-in-Box" (Fim do Aspecto de Planilha):**
     - [x] Remover caixas internas pesadas com bordas nos cards do Feed Zero-Click, deixando a tipografia respirar (`text-zinc-300 leading-relaxed font-sans`).
     - [x] Hero Metric grande e limpa (`text-2xl sm:text-3xl font-bold font-mono tracking-tight text-emerald-400`), com pílulas de status sem reticências.
     - [x] Superfícies translúcidas (*Apple Glassmorphism*): `bg-zinc-900/50 backdrop-blur-md border border-white/[0.08] hover:border-white/[0.16] rounded-2xl p-5 shadow-xl transition-all`.
  3. **Unificação de Navegação com Segmented Control (iOS/macOS Style):**
     - [x] Implementar Segmented Control elegante no topo do Cockpit alternando entre `Feed Zero-Click`, `Pista & Tanques` e `Segurança & Read-Only`.
  4. **Player de Áudio Visual (Waveform SVG) & Ação em 1-Clique na Diretiva:**
     - [x] Componente visual de Waveform SVG estilizado com barras dinâmicas, contador de tempo (`0:35`), transcrição editorial límpida e instrução tática de 15 segundos para a pista.
     - [x] Disparo em 1-clique com feedback visual instantâneo confirmando gravação na Outbox local.
- **Critério de Aceite (Pytest):** Criar `tests/unit/test_actionable_bi_phase4.py` cobrindo o loop fechado de diretivas, endpoints na API, persistência na outbox e integridade de contratos TypeScript.

---

## ✅ CHECKLIST DE VALIDAÇÃO FINAL PARA O AGENTE

Ao concluir cada fase, o agente deve executar e comprovar no terminal:
1. `pytest tests/unit/ -v` -> **100% dos testes aprovados (anteriores + novos)**.
2. Verificação de segurança (`git grep -i "Users/Marlon"` e `git grep -i "marlonh-supwp"`) -> **0 ocorrências retornadas**.
3. Validação de contratos estáticos TypeScript (`pytest tests/unit/test_frontend_typescript_contracts.py -v`) -> **100% sincronizado**.