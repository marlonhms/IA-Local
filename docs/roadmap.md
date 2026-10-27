# ROADMAP DE EXECUCAO TECNICA IMEDIATA: ALTO ROI, SEGURANCA B2B E BLINDAGEM DE BORDA (AURA)

> **Classificacao:** Plano Diretor de Engenharia para Execucao por Agente de IA  
> **Versao:** 2.0.0-PRO  
> **Branch Alvo:** `feature/partner-api-gateway` (posterior merge para `main`)  
> **Repositorio Base:** `ia-banco-local`  
> **Regra Estrita de Conformidade:** ZERO travessoes Unicode (`\u2014` e `\u2013`) em todo o codigo, comentarios, docstrings, templates e testes. Utilizar exclusivamente hifens comuns (`-`), dois pontos (`:`) ou parenteses.

---

## 1. OBJETIVO E CONTEXTO PARA O AGENTE EXECUTOR

Este documento contem as especificacoes tecnicas exatas, assinaturas de funcoes, contratos de dados, regras de negocio e criterios de aceite para implementar as **5 Melhorias de Impacto Imediato (Quick Wins de Alto ROI e Blindagem Tecnica)** extraidas do estudo estrategico da AURA.

### Diretrizes Inegociaveis de Execucao (Zero Regressao):
1. **Preservacao Total dos Testes Existentes:** Os mais de 650 testes unitarios atuais do projeto (incluindo `tests/unit/test_partner_api.py`, `tests/unit/test_transactional_outbox.py`, `tests/unit/test_desktop_notifier_wts.py` e `tests/unit/test_windows_scm_service.py`) devem continuar passando com 100% de sucesso.
2. **Arquitetura Deterministica (Zero Alucinacao Financeira):** Todos os calculos de ROI, desvios de LMC, quebras de caixa, Z-Score de cancelamentos e custos de oportunidade pela taxa Selic devem ser executados de forma 100% deterministica em Python, jamais delegando contas matematicas para a LLM.
3. **Compatibilidade Multi-Plataforma (Windows + Linux CI):** Todo codigo novo deve rodar nativamente tanto em Windows (ambiente de borda/producao) quanto em Ubuntu Linux (runners do GitHub Actions em Python 3.11 e 3.12).

---

## 2. ESCOPO DAS 5 MELHORIAS IMEDIATAS

```
+-----------------------------------------------------------------------------------+
|                   PACOTE DE UPGRADE IMEDIATO AURA (5 MODULOS)                     |
+-----------------------------------------------------------------------------------+
| MODULO 1: Calculadora Executiva e Endpoint de Diagnostico Retroativo de ROI       |
|           - Quantifica perdas em R$ (LMC, Caixa, Ruptura, Conveniencia, Estoque)  |
|           - Rota: GET /api/v1/partner/stations/{station_id}/roi-diagnostic        |
+-----------------------------------------------------------------------------------+
| MODULO 2: Cache Semantico Sincronizado ao raw-sync (data_version_hash)            |
|           - Invalida automaticamente no segundo em que novos dados entram         |
|           - Resposta < 20ms com custo zero de LLM para consultas equivalentes     |
+-----------------------------------------------------------------------------------+
| MODULO 3: Blindagem Zero-Trust do Partner Gateway (IP, LGPD e Schema Drift)       |
|           - Filtro heuristico Anti-Prompt Injection / Extraction                  |
|           - Pseudonimizacao deterministica de PII (HMAC-SHA256 em CPF/Nomes)      |
|           - Validador Pre-Flight de Invariantes Fisicas (bloqueia dados absurdos) |
+-----------------------------------------------------------------------------------+
| MODULO 4: Radar de Anomalias PDV, Trava Contabil CLT e Fluxos Zero-Click          |
|           - Calculo de Z-Score de cancelamentos por operador/turno                |
|           - Vocabulario estritamente contabil/estatistico + Checklist Art. 462 CLT|
|           - Briefing Matinal ("Cafe com o Dono") e Alerta de Descarga de Caminhao |
+-----------------------------------------------------------------------------------+
| MODULO 5: Blindagem de Borda (Edge Hardening: SQLite WAL e Sessao 0 Windows)      |
|           - PRAGMA wal_autocheckpoint=1000 e journal_size_limit=64MB no Outbox    |
|           - Protecao de timeout assincrono nao-bloqueante no DesktopNotifier      |
+-----------------------------------------------------------------------------------+
```

---

## 3. ESPECIFICACAO DETALHADA POR MODULO

### MODULO 1: Calculadora Executiva e Endpoint de Diagnostico Retroativo de ROI

#### 1.1. Contexto e Regra de Negocio
Ao conectar uma nova estacao via `raw-sync`, o parceiro de BI ou o consultor comercial da AURA precisa gerar em menos de 5 segundos um diagnostico financeiro comprovando quanto dinheiro a operacao esta perdendo silenciosamente e quanto a AURA recupera em 90 dias.

#### 1.2. Arquivos a Modificar / Criar
- `core/partner_api.py` (novo endpoint e logica de agregacao sobre o staging isolado)
- `core/tools.py` (metodo deterministico auxiliar `calculate_executive_roi_diagnostic` se aplicavel)
- `tests/unit/test_partner_api.py` (novos testes unitarios validando a matematica do ROI)

#### 1.3. Especificacao Tecnica da Equacao Deterministica
Implementar a funcao `compute_station_roi_diagnostic(station_id: str, staging_store: PartnerStagingStore, monthly_subscription_brl: float = 490.0) -> dict[str, Any]` que analisa as tabelas em staging (`tanques`, `fechabomba`, `fechacaixa`, `pedido`, `itemped`) e calcula os 5 vetores de recuperacao:

1. **Vetor 1 - Variacao de Tanque e Desvio no LMC (`lmc_shrinkage_brl`):**
   - Cruza o volume vendido nos bicos (`enclts - encltsa - qtdeaf` em `fechabomba`) com a variacao dos tanques (`iniciodia - volume` em `tanques`).
   - Se houver dados reais de perda fisica no staging, calcula o valor em R$ pelo preco medio dos bicos (`preco`).
   - Caso o staging contenha apenas um snapshot parcial, projeta a perda mensal estimada usando o parametro conservador auditado (0.35% sobre o faturamento de pista estimado, com potencial de recuperacao AURA de 80%).
   - Sinaliza alerta regulatorio se a variacao fisica ultrapassar **0.50%** (proximo ao limite de tolerancia de **0.60%** da Resolucao ANP 884/2022 e Ajuste SINIEF 01/92).
2. **Vetor 2 - Quebra Operacional e Ruptura na Conveniencia (`convenience_loss_brl`):**
   - Aplica o indice setorial Abrappe (3.86% de perda sobre o faturamento de loja/produtos ou itens cancelados detectados em `pedido` com `situ == 'C'`), estimando potencial de recuperacao de 45%.
3. **Vetor 3 - Quebra de Caixa e Conciliacao de Turno (`cashier_discrepancy_brl`):**
   - Compara o faturamento liquido das bombas (`encdinh` em `fechabomba`) contra os valores declarados em `fechacaixa` (`valtot` - `valrefcai`).
   - Quantifica divergencias nao conciliadas e aplica potencial de recuperacao de 70%.
4. **Vetor 4 - Inercia de Precificacao e Arbitragem de Compra (`pricing_and_procurement_brl`):**
   - Calcula o ganho marginal potencial de R$ 0.03 a R$ 0.05 por litro comercializado via compra no momento otimo de compartimento de carreta (setas de 5.000 L) e ajuste de preco regional ANP.
5. **Vetor 5 - Custo de Oportunidade de Capital Parado (`working_capital_selic_brl`):**
   - Calcula o custo financeiro mensal do estoque inerte/excessivo indexado a taxa Selic mensalizada (padrao 0.85% a.m. se offline).
6. **Consolidacao e ROI de 90 Dias:**
   - `total_monthly_leakage_brl`: Soma das perdas mensais identificadas/projetadas.
   - `estimated_monthly_recovery_brl`: Soma ponderada da recuperacao mensal pela AURA.
   - `roi_90_days_net_brl`: `(estimated_monthly_recovery_brl * (0.50 + 0.80 + 1.00)) - (3 * monthly_subscription_brl)` (considerando rampa de adocao de 50% no Mes 1, 80% no Mes 2 e 100% no Mes 3).
   - `roi_multiple`: `round((estimated_monthly_recovery_brl * 2.3) / max(1.0, 3 * monthly_subscription_brl), 1)`.
   - `guarantee_eligible`: `bool(roi_multiple >= 3.0)` (Garantia contratual de pelo menos 3x o retorno em 90 dias).

#### 1.4. Contrato do Endpoint REST
- **Rota:** `GET /api/v1/partner/stations/{station_id}/roi-diagnostic`
- **Headers:** `X-Partner-Key`, `X-Station-ID` (opcional se igual a URL)
- **Query Params Opcionais:** `monthly_fee: float = 490.0`
- **Resposta HTTP 200 (JSON):**
  ```json
  {
    "station_id": "posto_01",
    "generated_at": "2026-10-26T12:00:00+00:00",
    "data_version_hash": "a1b2c3d4...",
    "breakdown_brl": {
      "lmc_and_tank_shrinkage": 4520.00,
      "convenience_and_pos_cancellations": 3100.00,
      "cashier_shift_discrepancies": 1850.00,
      "pricing_and_carreta_arbitrage": 6200.00,
      "working_capital_selic_cost": 1400.00
    },
    "summary": {
      "total_monthly_leakage_brl": 17070.00,
      "estimated_monthly_recovery_brl": 10450.00,
      "roi_90_days_net_brl": 22565.00,
      "roi_multiple": 16.4,
      "guarantee_3x_met": true
    },
    "regulatory_shield": {
      "anp_law_9847_min_fine_brl": 20000.00,
      "anp_lmc_tolerance_pct": 0.60,
      "clt_art_462_compliance_active": true
    }
  }
  ```

---

### MODULO 2: Cache Semantico Particionado por Tenant e Sincronizado ao `raw-sync`

#### 2.1. Contexto e Regra de Negocio
Mais de 60% das perguntas matinais de gestores e socios de postos se repetem (*"Como estao os tanques agora?"*, *"Qual o resumo do fechamento de caixa?"*). Para manter a margem bruta de SaaS acima de 90% e responder em menos de 20 ms, o gateway deve armazenar em cache as respostas associadas a chave `(station_id, data_version_hash, normalized_query)`. Assim que um novo `raw-sync` e recebido para aquele `station_id`, o `data_version_hash` muda e invalida automaticamente o cache anterior daquela filial.

#### 2.2. Especificacao Tecnica em `core/partner_api.py`
1. **Geracao do `data_version_hash` no `PartnerStagingStore`:**
   - Dentro de `PartnerStagingStore.save_raw_data(station_id, tables)`:
   - Calcular um hash SHA-256 deterministico do conteudo das tabelas sincronizadas:
     `version_hash = hashlib.sha256(json.dumps(self._cache[valid_station], sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]`
   - Armazenar `data_version_hash` em `self._metadata[valid_station]["data_version_hash"]` e retornalo no resultado de `save_raw_data` e `get_station_status`.
2. **Classe `PartnerSemanticResponseCache`:**
   - Implementar em `core/partner_api.py` um cache thread-safe em memoria com suporte a:
     - Normalizacao da pergunta (`normalized_query = re.sub(r"[^\w\s]", "", query.strip().lower())`, removendo espacos duplos e stopwords triviais).
     - Chave composta: `(station_id, data_version_hash, normalized_query)`.
     - Limite maximo de entradas por estacao (LRU simples de ex: 200 entradas por estacao) para evitar crescimento infinito de RAM.
     - Invalidação imediata de todas as chaves da estacao quando `save_raw_data` ou `clear_station` for chamado.
3. **Integracao no `partner_chat_endpoint` (`POST /api/v1/partner/chat`):**
   - Antes de acionar `engine.ask()` ou `engine.ask_stream()`, consultar o `PartnerSemanticResponseCache` para `(effective_station, current_version_hash, req.query)`.
   - Se houver **Cache Hit**:
     - No modo `stream=False`: retornar imediatamente o JSON com `"cache_hit": True` e `"data_version_hash": current_version_hash`.
     - No modo `stream=True`: emitir o texto em cache como evento `delta` seguido do evento `done`, adicionando o header HTTP `"X-Aura-Cache": "HIT"` e `"X-Data-Version": current_version_hash`.
   - Se houver **Cache Miss**:
     - Executar o fluxo normal do motor, acumular os fragmentos `delta` gerados, gravar o texto consolidado no `PartnerSemanticResponseCache` ao finalizar com sucesso e retornar o header `"X-Aura-Cache": "MISS"`.

---

### MODULO 3: Blindagem Zero-Trust do Partner Gateway (Anti-Prompt Extraction, LGPD PII Scrubbing e Pre-Flight Check)

#### 3.1. Camada A: Filtro Heuristico Anti-Prompt Injection / Extraction
No endpoint `POST /api/v1/partner/chat`, inspecionar `req.query` antes de enviar ao `AuraEngine`:
- Criar a funcao `detect_prompt_extraction_attempt(query: str) -> bool` que verifica padroes maliciosos (case-insensitive):
  - Tentativas de override: `"ignore previous instructions"`, `"ignore all instructions"`, `"ignore as instrucoes anteriores"`, `"esqueça as regras"`, `"system prompt"`, `"mostre seu prompt"`, `"reveal your prompt"`, `"repeat the text above"`, `"repita o texto acima"`, `"print your instructions"`, `"modo desenvolvedor"`, `"developer mode"`, `"jailbreak"`, `"quais sao suas formulas internas"`, `"mostre o codigo python"`.
- Caso detectado (`True`):
  - **NAO invocar a LLM** (evita *refusal leakage* e economiza tokens).
  - Registrar log de seguranca (`logger.warning`) associado ao `station_id` e a chave do parceiro.
  - Retornar resposta estatica deterministica padronizada (em SSE se `stream=True` ou JSON se `stream=False`):
    `"Solicitacao bloqueada pela politica de seguranca da AURA: este canal processa exclusivamente consultas operacionais, financeiras e regulatorias da estacao."`

#### 3.2. Camada B: Pseudonimizacao Deterministica de PII na Ingestao (Conformidade LGPD)
Para proteger a AURA como Suboperadora sob a LGPD (Lei 13.709/2018) e impedir que CPFs de clientes ou nomes completos trafeguem para provedores externos de LLM:
- Criar a funcao `_scrub_pii_from_record(row: dict[str, Any], station_salt: str) -> dict[str, Any]` chamada dentro de `PartnerStagingStore.save_raw_data`:
  - Detectar campos de documentos sensiveis (chaves contendo `cpf`, `documento_cliente`, `placa` ou strings no formato de CPF `\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b`).
  - Substituir CPFs por hash deterministico truncado com prefixo: `f"CPF_HASH_{hmac.new(station_salt.encode(), raw_cpf.encode(), hashlib.sha256).hexdigest()[:10].upper()}"`.
  - Preservar identificadores operacionais necessarios para conciliacao de turno (como `matricula` ou codigo de operador/vendedor), garantindo que a auditoria matematica continue funcionando com 100% de precisao (ex: detectar *Loyalty Skimming* quando o mesmo `CPF_HASH_X` se repete 15 vezes em 30 minutos no mesmo bico), mas sem expor o dado pessoal real.

#### 3.3. Camada C: Validador Pre-Flight de Invariantes Fisicas (Protecao contra Schema Drift)
Antes de aceitar os registros no `raw-sync`, validar invariantes fisicas basicas na funcao `validate_physical_invariants(tables: dict[str, list[dict[str, Any]]]) -> dict[str, Any]`:
- Em `tanques`: rejeitar/sinalizar se `volume < 0` ou `capacidade < 0` ou `volume > capacidade * 1.15` (sobrecarga fisica impossivel).
- Em `fechabomba`: rejeitar/sinalizar se `enclts < encltsa` (encerrante final menor que o encerrante inicial sem flag de virada/manutencao) ou `preco < 0`.
- O endpoint `POST /raw-sync` deve suportar o parametro opcional `strict_physics: bool = False` (ou retornar uma lista `"physics_warnings": [...]` no payload de resposta HTTP 200, e se um registro individual violar gravemente a fisica basica como volume negativo, sanitiza ou isola o registro defeituoso na contagem `"quarantined_records"` sem derrubar o lote inteiro).

---

### MODULO 4: Radar de Anomalias PDV, Trava Contabil CLT e Fluxos Proativos Zero-Click

#### 4.1. Radar de Anomalias de Cancelamento por Operador (Z-Score) e Trava Contabil CLT
1. Implementar em `core/partner_api.py` (e expor via endpoint `GET /api/v1/partner/stations/{station_id}/pos-audit`) a funcao `audit_pos_and_cashier_anomalies(station_id: str, staging_store: PartnerStagingStore) -> dict[str, Any]`:
   - Agrupar cupons em `pedido` por operador (`vendedor` / `matricula`) e contabilizar total de vendas vs. vendas canceladas (`situ == 'C'`).
   - Calcular a media ($\mu$) e o desvio padrao ($\sigma$) da taxa de cancelamento entre os operadores da estacao.
   - Calcular o $Z\text{-Score}$ de cada operador: $Z = (x_i - \mu) / \sigma$ (quando $\sigma > 0$).
   - Sinalizar anomalia estatistica quando $Z \ge 2.0$ ou taxa de cancelamento $> 15\%$.
2. **Trava de Conformidade Trabalhista (Art. 462 CLT / Precedente Normativo 103 TST / OJ 251 SDI-1 TST):**
   - Garantir que todas as descricoes geradas pelo auditor utilizem **vocabulario estritamente contabil e estatistico** (ex: *"Divergencia fisica/financeira nao conciliada"* e *"Desvio estatistico de cancelamentos acima da media historica do terminal"*).
   - Proibir termos acusatorios (*"furto"*, *"roubo"*, *"fraude do funcionario"*, *"apropriacao indébita"*).
   - Anexar obrigatoriamente ao retorno da auditoria de caixa o bloco `clt_compliance_checklist`:
     ```json
     {
       "legal_basis": "Art. 462 CLT, Precedente Normativo 103 TST e OJ 251 SDI-1 TST",
       "mandatory_requirements_for_deduction": [
         "Comprovacao de pagamento da rubrica Adicional de Quebra de Caixa em folha conforme CCT vigente",
         "Previsao contratual expressa autorizando desconto em caso de divergencia conferida",
         "Bordero fisico de fechamento de turno conferido e assinado pelo operador e supervisor no ato"
       ],
       "terminology_policy": "STRICT_ACCOUNTING_STATISTICAL_ONLY"
     }
     ```

#### 4.2. Gerador de Fluxos Proativos Zero-Click (Briefing Matinal e Auditoria de Descarga)
Implementar o endpoint `GET /api/v1/partner/stations/{station_id}/zero-click-briefing` que gera o payload estruturado pronto para disparo via WhatsApp / Webhook do parceiro:
1. **Briefing Executivo Matinal ("Cafe com o Dono"):**
   - Consolida faturamento nas ultimas 24h, status de LMC frente ao limite de 0.6% da ANP, tanque com menor autonomia (run-out) e recomendacao de compra por seta de 5.000 L.
   - Retorna mensagem formatada em Markdown/WhatsApp (sem travessoes!) e lista de `quick_actions` (`["Aprovar Pedido Combustivel", "Emitir Justificativa LMC", "Gerar Termo Conferencia Turno"]`).

---

### MODULO 5: Blindagem de Borda (Edge Hardening: SQLite WAL e Sessao 0 Windows)

#### 5.1. Contexto Tecnico
Nas instalacoes locais do servico Windows da AURA (`AuraBackendService`), quedas prolongadas de internet ou picos de eventos poderiam fazer o arquivo `.db-wal` do SQLite crescer indefinidamente no disco do posto. Alem disso, chamadas de notificacao na Sessao 0 precisam de garantia absoluta contra bloqueio de thread.

#### 5.2. Alteracoes em `core/outbox.py`
No metodo `AuraTransactionalOutbox._apply_pragmas(conn: sqlite3.Connection)` (linhas 308-315 de `core/outbox.py`), adicionar as duas novas diretivas de contencao de tamanho de log e checkpoint automatico:
```python
    @staticmethod
    def _apply_pragmas(conn: sqlite3.Connection) -> None:
        """Aplica as diretivas de resiliencia SQLite WAL, autocheckpoint e limite de tamanho em disco."""
        try:
            conn.execute("PRAGMA busy_timeout=5000;")
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA wal_autocheckpoint=1000;")
            conn.execute("PRAGMA journal_size_limit=67108864;")  # Limite estrito de 64 MB no arquivo .wal
        except sqlite3.OperationalError:
            pass
```

#### 5.3. Verificacao e Blindagem de Timeout Assincrono em `core/desktop_notifier.py`
- Garantir que `DesktopNotifier` mantenha `default_timeout_sec` limitado de forma segura e adicionar protecao de execucao com timeout de seguranca para que nenhuma falha de driver grafico na Sessao 0 jamais bloqueie a thread chamadora por mais que o tempo limite estipulado.

---

## 4. CRITERIOS DE ACEITE E SUITE DE TESTES OBRIGATORIA

Para considerar este Roadmap 100% concluido, o agente executor devera:
1. Implementar os Modulos 1 a 5 sem introduzir nenhum caractere de travessao (`\u2014` ou `\u2013`).
2. Adicionar testes unitarios abrangentes em `tests/unit/test_partner_api.py` e `tests/unit/test_transactional_outbox.py` validando:
   - Calculo do diagnostico de ROI (`/roi-diagnostic`) e elegibilidade da garantia de 3x;
   - Funcionamento do `PartnerSemanticResponseCache` (Cache HIT na segunda pergunta identica e Cache MISS imediato apos novo `raw-sync`);
   - Bloqueio deterministico de tentativa de *Prompt Injection / Extraction* no `/chat`;
   - Mascaramento deterministico de CPF (`CPF_HASH_...`) no `raw-sync` e isolamento de registros com invariantes fisicas invalidas (`enclts < encltsa` ou `volume < 0`);
   - Calculo de $Z\text{-Score}$ de cancelamentos no `/pos-audit` com checklist trabalhista Art. 462 CLT e ausencia de palavras acusatorias;
   - Geracao do Briefing Matinal Zero-Click (`/zero-click-briefing`);
   - Aplicacao efetiva dos novos PRAGMAs (`wal_autocheckpoint=1000` e `journal_size_limit=67108864`) no `AuraTransactionalOutbox`.
3. Executar `pytest` e `ruff check` garantindo 100% de aprovacao.


---

# APENDICE A: OTIMIZACAO DA GUI & GENUI PARA INTELIGENCIA FISCAL, TRIBUTARIA E CONTABIL (FASE 1 A 4)

> **Documento Espelho Completo:** `docs/roadmap_apendice_gui_fiscal.md`  
> **Escopo:** Integracao Visual Premium (`AURA Precision Glass Deluxe`) do Motor Fiscal Deterministico (`core/fiscal_engine.py`) e Acervo Normativo Local (`data/webposto_knowledge.db`) no Companion Canvas, Chat Composer, Central de Gatilhos em 1-Clique e Welcome Cockpit.  
> **Regra Inegociavel:** ZERO travessoes Unicode (`\u2014` e `\u2013`) em qualquer arquivo modificado ou criado.

## A.1. DIAGNOSTICO TECNICO DOS PONTOS DE OTIMIZACAO NA GUI ATUAL

1. **Hidratacao Incompleta de `xml_documento` no Companion Canvas (`core/aura_engine.py`, linhas 2703-2776):**
   - Atualmente, `build_canonical_genui_envelope` trata apenas `tipo == "chave_acesso"` e `tipo == "consulta_rejeicao_fiscal"`, caindo em `else: blocks = []` quando o usuario audita um arquivo ou trecho XML (`tipo == "xml_documento"`).
2. **Mapeamento de Chaves Legadas em `chave_acesso` (`core/aura_engine.py`, linhas 2709-2734):**
   - O builder consulta chaves antigas (`nivel`, `numero_nf`, `dv_valido`) em vez dos campos do contrato `ApontamentoFiscal` e `decompor_chave_acesso` (`status`, `gravidade`, `numero_nfe`, `is_dv_valido`, `explicacao_executiva`, `explicacao_tecnica`, `base_legal`).
3. **Nota Contabil Estatica (`core/aura_engine.py`, linha 2773):**
   - O bloco `blk_procedimento_erp` exibe texto fixo sobre `Registro C113` mesmo para regras de ICMS Monofasico (LC 192/2022), PIS/COFINS Monofasico (Tabela 4.3.10), LMC (Registro 1300) ou Reforma Tributaria (LC 214/2025).
4. **Ausencia de Ferramenta Fiscal Dedicada nos Gatilhos em 1-Clique (`web/js/aura-triggers.js`) e Composer (`web/index.html`):**
   - O catalogo de gatilhos rapidos ainda nao possui o card `auditoria_fiscal_sefaz` e o composer nao detecta colagem de chaves de 44 digitos ou upload de arquivos `.xml`.

---

## A.2. ESPECIFICACAO DE EXECUCAO POR FASE

### FASE 1: Backend GenUI Hydration (`core/aura_engine.py`) & Micro-Widget `FiscalShieldInspectorUI` (`web/js/aura-genui-widgets.js`)

1. **Em `core/aura_engine.py` (`build_canonical_genui_envelope`):**
   - **Para `tipo == "chave_acesso"`:**
     - Ler `is_dv_valido = bool(decomp.get("is_dv_valido", False))` e `invalidos = [a for a in apontamentos if a.get("status") == "INVALID"]`.
     - Popular `props["access_key_anatomy"]` com os 9 segmentos oficiais da chave de 44 digitos (`c_uf`, `uf_sigla`, `aamm`, `cnpj_emitente`, `modelo`, `serie`, `numero_nfe`, `tipo_emissao`, `codigo_numerico`, `digito_verificador`, `dv_calculado`, `is_dv_valido`).
     - Popular `props["persona_views"]` com `{"gestor": top_apont.get("explicacao_executiva"), "contador": top_apont.get("explicacao_tecnica"), "base_legal": top_apont.get("base_legal", [])}`.
   - **Para `tipo == "xml_documento"`:**
     - Construir `blk_xml_status` (`alert_callout`), `blk_xml_kpis` (`kpi_grid` com Modelo, UF Origem -> Destino, Erros Impeditivos e Alertas Contabeis) e `blk_xml_apontamentos` (`ranking_list` detalhando cada violacao como `SEFAZ-REJ-960`, `SEFAZ-REJ-806`, `SPED-RISCO-BITRIBUTACAO-PISCOFINS`, `SEFAZ-I08-10`).
     - Popular `props["persona_views"]` separando a visao executiva de pista/retaguarda e a visao contabil/SPED.
   - **Para `tipo == "consulta_rejeicao_fiscal"`:**
     - Extrair dinamicamente `metadados_json` do registro retornado pelo SQLite FTS5 (`base_legal`, `gravidade`, `campos_xml`) e alimentar `blk_procedimento_erp` e `props["persona_views"]` sem texto fixo engessado.

2. **Em `web/js/aura-genui-widgets.js`:**
   - Implementar suporte nativo em `GenerativeModularCardUI` (e alias `FiscalShieldInspectorUI`) para:
     - **Switch Dupla Persona:** Botoes `[Visao Gestor & Pista]` e `[Visao Contador & SPED]` que alternam instantaneamente a exibicao entre o resumo executivo/operacional e a especificacao tecnica XML/SPED.
     - **Barra Anatomica de 44 Digitos:** Renderizacao visual dos 9 blocos da chave de acesso quando `props.access_key_anatomy` estiver presente, destacando o DV Modulo 11 em verde esmeralda (valido) ou vermelho rosa (invalido).
     - **Acao de Copia em 1-Clique (`copiar_diagnostico_contador`):** Copia para a area de transferencia um parecer tecnico estruturado pronto para envio ao contador via WhatsApp/E-mail.

### FASE 2: Smart Fiscal Composer & Leitor Local de XML (`web/index.html` e `web/js/aura-chat.js`)

1. **Pilula de Deteccao Instantanea (`#fiscal-smart-paste-pill`):**
   - Detectar via regex no evento `input`/`paste` de `#chat-input-text` quando o usuario colar 44 digitos (`/\b\d{44}\b/`) ou tags `<infNFe`/`<nfeProc`, exibindo uma pilula interativa acima do composer para disparo imediato da auditoria.
2. **Botao de Inspecao de Arquivo XML (`#btn-upload-fiscal-xml`):**
   - Adicionar botao com icone `file-code-2` ao lado do botao de voz no composer que abre seletor de arquivo `.xml`, le o conteudo localmente via `FileReader` (100% offline) e submete para auditoria deterministica.

### FASE 3: Central de Gatilhos em 1-Clique (`web/js/aura-triggers.js`) e Navegacao Rapida (`web/index.html`)

1. **Novo Gatilho `auditoria_fiscal_sefaz` em `getToolsCatalog()` (`web/js/aura-triggers.js`):**
   - Adicionar card na categoria `fiscal` com badge `SEFAZ / LC 192 / SPED`, permitindo executar diagnosticos de rejeicoes, ICMS Monofasico (CST 61) e PIS/COFINS (CST 04) em 1-clique.
   - Implementar formatador visual executivo no inspetor de gatilhos para exibir cartoes estruturados em vez de JSON puro.
2. **Atalhos no Card de Boas-Vindas e Menu Lateral (`web/index.html`):**
   - Adicionar chip `"Escudo Fiscal & SEFAZ"` nas sugestoes executivas iniciais e no Cluster 2 do Menu Lateral.

### FASE 4: Estilos Liquid Glass (`web/css/aura.css`) e Testes Automatizados (`tests/unit/test_fiscal_engine.py`)

1. **Estilos em `web/css/aura.css`:**
   - Adicionar estilos para `.fiscal-key-segment` e `.persona-switch-bar` garantindo compatibilidade total com `body.modo-pista-active` (alto contraste sob sol forte) e `body.gpu-guard-active` (60 FPS sem `backdrop-filter` pesado).
2. **Testes Unitarios em `tests/unit/test_fiscal_engine.py`:**
   - Validar a geracao do envelope GenUI para `chave_acesso`, `xml_documento` e `consulta_rejeicao_fiscal` e validar ausencia absoluta de travessoes Unicode (`\u2014` e `\u2013`) em todos os arquivos modificados.

---

# APENDICE B: ENGENHARIA DE TIPOGRAFIA COGNITIVA, UX WRITING E LEITURA INTELIGENTE NO CHAT CONTAINER (FASE 1 A 4)

> **Documento Espelho Completo:** `docs/roadmap_apendice_ux_textual_chat.md`  
> **Escopo:** Separacao estrita de responsabilidades entre GUI (foco 100% visual e interativo) e Container de Chat (foco 100% textual, editorial, escaneavel e anti-fadiga), aplicando neuroergonomia de leitura digital (Regra de Bringhurst 68ch, BLUF, Layer-Cake Scannability, Auto-Tokenizacao Tabular e Progressive Disclosure).  
> **Regra Inegociavel:** ZERO travessoes Unicode (`\u2014` e `\u2013`) em qualquer arquivo modificado ou criado.

## B.1. DIAGNOSTICO DE FADIGA VISUAL E COGNITIVA NO CHAT ATUAL

1. **Inflacao de Negrito e Ofuscamento (Bold & Halation Fatigue):**
   - Textos corridos em `#e2e8f0`/`#ffffff` com excesso de `strong` (`700`) e spans coloridos com `text-shadow` neon causam cansaco ocular rapido e destroem a hierarquia de escaneamento.
2. **Duplicacao entre Chat e GUI (Companion Canvas):**
   - Quando a GUI lateral ja exibe os cards interativos, o chat ainda repete listas longas de numeros em algumas sinteses deterministicas (`core/aura_engine.py`).
3. **Largura de Linha Excessiva e Falta de Ancoras Tabulares:**
   - Paragrafos sem limite de largura (`ch`) forcam movimentos oculares longos, e metricas misturadas na fonte proporcional dificultam a comparacao rapida de valores (`R$`, `L`, `%`).

---

## B.2. ESPECIFICACAO DE EXECUCAO POR FASE

### FASE 1: Ergonomia Tipografica, Escala Modular e Anti-Fadiga Visual (`web/css/aura.css`)

1. **Calibracao de `.prose-aura`:**
   - Cor base suave `#cbd5e1` (Slate-300), peso estritamente `400` no texto corrido, `line-height: 1.68` e largura otima de leitura `max-width: 68ch` para paragrafos, listas e citacoes.
   - Primeiro paragrafo (`.prose-aura > p:first-of-type`) estilizado como **Lead Paragraph (BLUF)** em `#f1f5f9` para ancorar o veredito imediato.
   - Reducao de `strong`/`b` para `font-weight: 600` (`#f8fafc`), eliminando o aspecto pesado.
2. **Micro-Tokens de Dados (`.aura-data-token`) e Badges Sutilizados:**
   - Criacao de `.aura-data-token` com `font-family: var(--font-mono)`, `font-variant-numeric: tabular-nums`, fundo translúcido de `4%` e borda de `8%`.
   - Remocao de `text-shadow` neon pesado nas classes semanticas dentro de `.prose-aura`, convertendo-as em micro-pilulas editoriais discretas.

### FASE 2: Motor de Formatacao Inteligente e Progressive Disclosure (`web/js/aura-chat.js`)

1. **Auto-Tokenizador de Metricas (`applySmartTypographyTokens`):**
   - Detector automatico em `formatMarkdown` que envolve valores monetarios (`R$`), volumes (`L`, `L/min`), percentuais (`%`) e codigos fiscais (`CFOP`, `CST`, `NCM`, `Rejeicao`, `cStat`) em `<span class="aura-data-token">`.
2. **Progressive Disclosure Automatico (`applyProgressiveDisclosure`):**
   - Quando a resposta possuir card visual na GUI (`hasToolCard === true`) e mais de 3 blocos textuais, manter visiveis os 2 primeiros blocos (veredito + sintese) e agrupar o detalhamento complementar em `<details class="aura-chat-disclosure">`.
3. **Telemetria Discreta:**
   - Suavizar o rodape de telemetria (`opacity-60 hover:opacity-100 font-mono text-[10px]`) para nao competir com o texto principal.

### FASE 3: UX Writing nos Prompts e Sintese Enxuta Dual-Channel (`core/prompts/system_prompts.py` e `core/aura_engine.py`)

1. **Regras BLUF e Bold Budget (Maximo 10%) em `core/prompts/system_prompts.py`:**
   - Instruir a LLM a iniciar sempre pelo veredito direto sem saudacoes repetitivas e limitar o uso de negrito a no maximo 1 a 2 ancoras curtas por topico.
2. **Enxugamento Dual-Channel em `_gerar_sintese_contingencia_ferramenta` (`core/aura_engine.py`):**
   - Quando `genui_active=True`, retornar um briefing executivo conciso de 3 a 4 linhas para todas as ferramentas (`roi_diagnostic`, `pos_audit`, `cenario_preditivo`, `conciliacao_caixa`, `estoque_combustivel`, `previsao_esgotamento_tanques`, `conformidade_lmc_anp`), delegando a densidade de tabelas e listas para o Companion Canvas.

### FASE 4: Controle de Conforto de Leitura e Testes Automatizados (`web/index.html`, `web/js/aura-chat.js` e `tests/unit/test_chat_typography_ux.py`)

1. **Toggle de Modo de Leitura (`#btn-chat-reading-density`):**
   - Botao discreto no cabecalho do chat permitindo alternar entre **Modo Executivo Conciso** (padrao, com Progressive Disclosure) e **Modo Leitura Expandida** (todos os detalhes abertos e fonte `0.96rem`), persistido em `localStorage`.
2. **Suite de Testes (`tests/unit/test_chat_typography_ux.py`):**
   - Validar regras CSS ergonomicas, tokenizacao automatica de numeros, Progressive Disclosure, concisao com `genui_active=True` e zero travessoes Unicode (`\u2014` e `\u2013`).

---

# APENDICE C: SINERGIA DUAL-CHANNEL, NITIDEZ OPTICA E FLUXO SEQUENCIAL (CHAT -> CANVAS) [CONCLUIDO]

> **Status:** 100% Concluido (Fases 1, 2, 3, 4 e 5 implementadas e validadas com 829 testes aprovados)  
> **Documento Espelho Completo:** `docs/roadmap_apendice_sinergia_dual_channel.md`  
> **Escopo:** Desacoplamento temporal e cognitivo entre Chat e Canvas (leitura primeiro no chat, abertura sob demanda do Canvas), restauracao de nitidez optica no Windows (ClearType subpixel sem blur de GPU) e eliminacao definitiva de redundancia textual tripla no core do sistema.  
> **Regra Inegociavel:** ZERO travessoes Unicode (`\u2014` e `\u2013`) em qualquer arquivo modificado ou criado.

## C.1. FASES DO APENDICE C [100% CONCLUIDAS]
1. **Fase 1 - Nitidez Optica e Renderizacao Cristalina (`web/css/aura.css`):** [CONCLUIDA] Subpixel ClearType nativo no Windows, fim de transforms residuais e contraste elevado (`#e2e8f0` / `0.935rem`).
2. **Fase 2 - Coreografia Sequencial e Card de Ponte Contextual (`web/js/aura-chat.js`):** [CONCLUIDA] `autoOpen: false` para evitar atropelamento da leitura, remocao de `<details>` concorrente no chat e botao `Explorar no Canvas ->`.
3. **Fase 3 - Contrato "Zero Repeticao" no Core (`core/aura_engine.py` e Prompts):** [CONCLUIDA] Clusterizacao causal no chat (sem listar itens) e detalhamento item a item exclusivo no Canvas.
4. **Fase 4 - Higienizacao de Redundancia no Canvas (`web/js/aura-genui-widgets.js`):** [CONCLUIDA] Cockpit de Resumo de Impacto da Pista no topo da Visao Gestor e alternancia inteligente de persona nos cards de apontamentos.
5. **Fase 5 - Suite de Testes e Sincronizacao (`tests/unit/test_sinergia_dual_channel.py`):** [CONCLUIDA] 21 testes unitarios dedicados, paridade 100% de distribuicao com `dist/`, zero travessoes Unicode e 829 testes aprovados no repositrio.


