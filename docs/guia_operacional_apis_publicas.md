# GUIA OPERACIONAL: HUB DE INTEGRAÇÃO DE APIS E DADOS PÚBLICOS DA AURA
## Manual Técnico de Borda para Revendedores e Operadores de Postos de Combustíveis

> **Classificação:** Documento Técnico Operacional de Borda (Edge AI)  
> **Versão:** 1.0.0-PRO  
> **Data:** Outubro de 2026  
> **Status:** Homologado para Operação em Borda  
> **Repositório:** [`ia-banco-local`](./)  
> **Regra de Estilo:** Zero travessões em todo o documento.  

---

## 1. Visão Geral e Arquitetura de Borda

O Hub de Dados Públicos da AURA integra dados governamentais abertos diretamente no servidor local do posto (Edge Computing), proporcionando inteligência competitiva, conformidade regulatória e otimização financeira sem dependência de nuvem contínua.

### Fontes Governamentais Integradas
1. **ANP (Agência Nacional do Petróleo):** Levantamento semanal de preços de combustíveis por município e cadastro geral de postos revendedores.
2. **CONFAZ (Conselho Nacional de Política Fazendária):** Atos COTEPE e tabelas de PMPF (Preço Médio Ponderado a Consumidor Final) para ICMS-ST.
3. **BACEN SGS (Banco Central do Brasil):** Séries diárias e mensais da Taxa Selic (meta e efetiva), Câmbio PTAX, IPCA e IGP-M.
4. **INMETRO:** Critérios metrológicos da Portaria INMETRO 559/2016 (ensaio de 20L em aferidor padrão lacrado).

---

## 2. Monitoramento Semanal de Preços ANP e Posicionamento Competitivo

### 2.1 Funcionamento
O conector ANP processa os microdados semanais via streaming em lotes de 64 KB, isolando apenas os registros do município do posto. Os preços praticados na bomba pelo estabelecimento são comparados contra a distribuição estatística do município:
- **Mínimo:** Menor preço coletado na cidade na semana de referência.
- **Q1 (Primeiro Quartil):** Faixa de preços dos 25% postos mais baratos da praça.
- **Mediana (Q2):** Preço central do município (indicador robusto contra outliers).
- **Média:** Preço médio ponderado municipal.
- **Q3 (Terceiro Quartil):** Faixa de preços dos 25% postos mais caros da praça.
- **Máximo:** Maior preço coletado na cidade.

### 2.2 Diagnóstico e Gaps
- **Gap em R$ e %:** A AURA calcula a diferença exata `Preco_Posto - Media_Municipal`.
- **Posicionamento:** Classifica a bomba em "Agressivo (Q1)", "Alinhado à Mediana (Q2)" ou "Premium / Margem Alta (Q3+)".
- **Widget GenUI:** Renderiza o componente `BenchmarkComparisonUI` com botões táticos de ação direta: "Ajustar Preço de Bomba" e "Manter Estratégia de Margem".

---

## 3. Auditoria Diária de Conformidade do LMC (Portaria ANP 26/1992)

### 3.1 A Regra dos +-0,60%
A Portaria ANP 26/1992 e a Resolução ANP 894/2022 estipulam que a variação volumétrica diária entre o estoque físico medido na régua ou sensor e o estoque escriturado contabilmente não pode exceder o teto de **+-0,60%** do volume comercializado no período:
- **Variação Aceitável:** `-0,60% <= Variacao_Pct <= +0,60%` (Status: CONFORME).
- **Perda Excessiva (Quebra < -0,60%):** Indício de vazamento em linha subterrânea, problema de estanqueidade no tanque ou bico medidor desregulado entregando mais combustível que o registrado.
- **Sobra Excessiva (Ganho > +0,60%):** Indício de aferição de bico não retornada ao tanque, erro de escrituração no livro ou condensação/temperatura.

### 3.2 Ações Human-in-the-Loop (HITL) no Micro-Widget GenUI
Ao auditar o LMC, a AURA gera o micro-widget `LMCComplianceReportUI` com 3 ações interativas:
1. **Exportar LMC Formatado:** Gera o arquivo oficial do Livro de Movimentação pronto para fiscalização da ANP.
2. **Agendar Aferição INMETRO 20L:** Emite ordem de serviço de teste com medida de volume de 20 litros lacrada (Portaria INMETRO 559/2016, tolerância de +-100 ml).
3. **Inspecionar Calibração do Tanque:** Dispara análise da tabela volumétrica e régua de medição.

---

## 4. Custo Selic de Carregamento de Estoque e Pauta CONFAZ PMPF

### 4.1 Carrying Cost Financeiro do Combustível Subterrâneo
Manter tanques cheios imobiliza capital de giro substancial. A AURA quantifica diariamente o custo de oportunidade financeiro através da taxa Selic do BACEN SGS:
```
Custo_Diario_Carregamento = (Volume_Estoque_Litros * Preco_Custo_Compra) * (Taxa_Selic_Anual / 252)
Custo_Mensal_Carregamento = Custo_Diario_Carregamento * 21
```
*Nota técnica: adota-se a convenção de mercado de 252 dias úteis por ano e 21 dias úteis por mês.*

### 4.2 Spread da Pauta PMPF (ICMS-ST)
A AURA confronta o preço de compra e venda com a pauta fiscal PMPF vigente no Estado:
- **Spread Positivo (Preço Venda > PMPF):** Risco de complementação de ICMS-ST em fiscalizações estaduais.
- **Spread Negativo (Preço Venda < PMPF):** Oportunidade de pedido de ressarcimento ou restituição de ICMS pago a maior na substituição tributária (Tema 201 do STF).

---

## 5. Sincronização via CLI e Operação em Segundo Plano

### 5.1 Comandos do Sincronizador CLI
O script `scripts/sync_public_data.py` é o utilitário oficial de carga e sincronização de dados:

```bash
# Execucao unica completa para todas as fontes governamentais
python scripts/sync_public_data.py --source all --once

# Sincronizacao individual da base semanal de precos da ANP
python scripts/sync_public_data.py --source anp --once

# Sincronizacao individual das pautas de PMPF do CONFAZ
python scripts/sync_public_data.py --source confaz --once

# Sincronizacao dos indicadores economicos do BACEN SGS (Selic, PTAX, IPCA)
python scripts/sync_public_data.py --source bacen --once

# Execucao em modo de testes / mock hermetico offline
python scripts/sync_public_data.py --source all --mock --once
```

### 5.2 Parâmetros Suportados
- `--source`: Fonte alvo (`anp`, `confaz`, `bacen`, `all`). Padrão: `all`.
- `--once`: Executa um ciclo único e encerra o processo com código de saída 0.
- `--interval`: Intervalo em segundos para execução contínua em modo daemon (ex: 86400 para 24h).
- `--mock`: Utiliza dados sintéticos em memória para testes offline sem rede externa.
- `--db-path`: Caminho customizado para banco de dados SQLite local de contingência.
- `--max-records`: Limite de registros a processar na base ANP para controle de tempo.

---

## 6. Motor Proativo de Borda (AuraProactiveDaemon)

O `AuraProactiveDaemon` vigia a pista 24/7 com regras analíticas periódicas:
1. **Regra de Conformidade LMC:**
   - Avalia a variação percentual física diária de cada tanque.
   - Dispara alerta `CRITICAL` se `|Variacao| > 0,60%`.
   - Aplica Smart Cooldown de **4 horas** (14.400 segundos) por tanque para evitar saturação.
2. **Regra de Defasagem de Dados Públicos (Staleness):**
   - Verifica se a última coleta da ANP ou CONFAZ possui mais de 7 dias.
   - Se os dados estiverem defasados e o Circuit Breaker estiver em estado `CLOSED`, agenda sincronização não-bloqueante em background.
   - Dispara alerta `WARNING` com Smart Cooldown de **24 horas** (86.400 segundos).
3. **Canais de Despacho In-App e Integrados na AURA:**
   - Ecossistema In-App da AURA (Canal primario): alertas sao entregues diretamente na interface web da AURA via stream SSE (/proactive/stream), cards contextuais interativos com acoes rapidas na coluna de chat e notificacoes toast no console cognitivo.
   - Popups Modais do Windows: desativados por padrao (desktop_notify=False), garantindo que alertas nao interrompam as operacoes de caixa no Windows, ocorrendo estritamente dentro da AURA.
   - Webhook n8n para automacoes de retaguarda.
   - WhatsApp via Evolution API para notificacao ao revendedor.

---

## 7. Garantias Unidirecionais de Privacidade e Blindagem LGPD

A arquitetura pública da AURA opera sob o princípio estrito de **Coleta Unidirecional Clean Room**:
1. **Zero Envio de Telemetria Privada:** Os conectores externos realizam exclusivamente requisições HTTP GET para endpoints públicos do Governo Federal (dados.gov.br, confaz.fazenda.gov.br, bcb.gov.br).
2. **Anonimato Absoluto:** Nenhuma requisição externa contém CNPJ, Razão Social, volume de vendas, faturamento, preços internos ou localização GPS do posto cliente.
3. **Cruzamento Exclusivamente Local:** A junção entre os dados públicos e os dados confidenciais do revendedor ocorre inteiramente dentro do servidor do posto (PostgreSQL/SQLite em `localhost`), sem trânsito por nenhum servidor intermediário ou nuvem pública.
