# APENDICE DE ENGENHARIA GUI & GENUI: EXPERIENCIA PREMIUM DE INTELIGENCIA FISCAL, TRIBUTARIA E CONTABIL (AURA)

> **Classificacao:** Especificacao Tecnica Executavel para Agente de IA (Frontend + Backend GenUI)  
> **Versao:** 2.1.0-DELUXE  
> **Branch Alvo:** `feature/partner-api-gateway`  
> **Repositorio Base:** `ia-banco-local`  
> **Design System:** `AURA Precision Glass Deluxe` (Dark Obsidian `#07090e`, Liquid Glass Acrylic, Geist / Newsreader / Geist Mono, GPU Guard 60fps, Modo Pista Alto Contraste)  
> **Regra Estrita e Inegociavel:** ZERO travessoes Unicode (`\u2014` e `\u2013`) em todo o codigo Python, JavaScript, HTML, CSS, comentarios, docstrings, mensagens de commit e testes. Utilizar exclusivamente hifens ASCII (`-`), dois pontos (`:`) ou setas (`->`).

---

## 1. OBJETIVO E VISAO EXECUTIVA PARA O AGENTE

O motor deterministico fiscal, tributario e contabil da AURA (`core/fiscal_engine.py` e `data/webposto_knowledge.db` com 48 regras normativas MOC 7.0, LC 192/2022, PIS/COFINS Tabela 4.3.10, SPED Fiscal Registros 1300/1310/1320, CFOP 5927, CEST Rejeicao 806 e Reforma Tributaria LC 214/2025) ja esta operacional no backend.

O objetivo deste plano e **otimizar a GUI e a camada GenUI (Intelligent UI / Companion Canvas)** para entregar uma experiencia tecnologica original, fluida e orientada a tomada de decisao imediata, dividida em **4 Fases de Execucao**.

### Diretrizes Inegociaveis (Zero Regressao e Zero Alucinacao):
1. **Zero Dependencias Externas (Offline-First):** Todo codigo JS/CSS deve manter a arquitetura Zero-Bundler nativa (`window.AuraGenUI`, `window.SecureComponentRegistry`, Tailwind local, Lucide local) e compatibilidade com CommonJS (Node.js) para testes headless.
2. **Zero Dados Ficticios:** Nenhum numero ou status fiscal pode ser hardcoded como dado real. Todo indicador exibido na GUI deve vir do retorno deterministico de `core/fiscal_engine.py` ou `core/webposto_rag.py`.
3. **Simbiose Chat + Companion Canvas:** Quando o Companion Canvas estiver ativo (`genui_active=True`), o texto do chat entrega um briefing executivo cirurgico (2 a 4 frases) e o Companion Canvas lateral projeta a densidade analitica, o decompositor visual de 44 digitos, a auditoria de itens do XML e o seletor de Dupla Persona.
4. **Preservacao Integral dos Testes:** Todos os testes em `tests/unit/test_fiscal_engine.py`, `tests/unit/test_generative_modular_ui.py` e `tests/unit/test_frontend_offline.py` devem passar com 100% de sucesso.

---

## 2. ARQUITETURA DOS 4 MODULOS DE OTIMIZACAO DA GUI

```
+---------------------------------------------------------------------------------------+
|                UPGRADE DE INTERFACE & GENUI FISCAL AURA (4 FASES)                     |
+---------------------------------------------------------------------------------------+
| FASE 1: Backend GenUI Hydration & Micro-Widget FiscalShieldInspectorUI                |
|         - Hidratacao completa de chave_acesso, xml_documento e consulta_rejeicao      |
|         - Switch Dupla Persona: [Visao Gestor / Pista] vs [Visao Contador / SPED]     |
|         - Barra Anatomica Interativa dos 44 Digitos da Chave SEFAZ (9 segmentos)      |
+---------------------------------------------------------------------------------------+
| FASE 2: Smart Fiscal Composer & Dropzone Instantaneo de XML / Chave 44d               |
|         - Deteccao automatica ao colar 44 digitos ou XML no input do chat             |
|         - Pilula interativa (Smart Paste Pill) para disparo em 1-clique               |
|         - Botao de upload/leitura local de arquivo .xml no composer                   |
+---------------------------------------------------------------------------------------+
| FASE 3: Central de Gatilhos em 1-Clique, Command Palette (Ctrl+K) e Menu Lateral      |
|         - Novos cards em aura-triggers.js: Escudo Fiscal SEFAZ & Auditor PIS/COFINS   |
|         - Renderizador visual executivo no Inspetor de Gatilhos (sem JSON cru)        |
|         - Novos atalhos rapidos no Command Palette (Ctrl+K)                           |
+---------------------------------------------------------------------------------------+
| FASE 4: Cockpit de Boas-Vindas, Estilos Liquid Glass, Modo Pista e Testes E2E         |
|         - Chip de prontidao "Escudo Fiscal & SEFAZ" no card inicial                   |
|         - Classes CSS com suporte a GPU Guard (60 FPS) e Modo Pista (Sol Forte)       |
|         - Suite de testes unitarios validando o contrato GenUI e higiene de codigo    |
+---------------------------------------------------------------------------------------+
```

---

## 3. ESPECIFICACAO TECNICA PASSO A PASSO

### FASE 1: Hidratacao GenUI no Backend e Micro-Widget `FiscalShieldInspectorUI`

#### 1.1. Correcao e Enriquecimento do Envelope em `core/aura_engine.py`
Localizar o bloco `elif intencao in ("auditoria_fiscal_sefaz", "conhecimento_fiscal", "fiscal_sefaz"):` (aproximadamente linhas 2703 a 2808 de `core/aura_engine.py`) e substituir pela hidratacao completa dos 3 subtipos retornados por `self.tools.auditar_documento_ou_chave_fiscal`:

1. **Subtipo A (`tipo == "chave_acesso"`):**
   - Ler `decomp = resultado_bruto.get("decomposicao") or {}` e `apontamentos = resultado_bruto.get("apontamentos") or []`.
   - Usar os campos reais de `ApontamentoFiscal` e `decompor_chave_acesso`:
     - `is_dv_valido = bool(decomp.get("is_dv_valido", False))`
     - `invalidos = [a for a in apontamentos if a.get("status") == "INVALID"]`
     - `tem_erro = len(invalidos) > 0 or not is_dv_valido`
     - `top_apont = invalidos[0] if invalidos else (apontamentos[0] if apontamentos else {})`
   - Montar os blocos:
     - `blk_chave_status` (`block_type: "alert_callout"`):
       - `severity`: `"critical"` se `tem_erro` senao `"success"`
       - `title`: `top_apont.get("titulo") or ("Chave Invalida" if tem_erro else "Chave Autentica e Valida (Modulo 11 OK)")`
       - `message`: `top_apont.get("explicacao_executiva") or "Estrutura de 44 digitos e digito verificador conferem com o padrao SEFAZ."`
       - `action_label`: `(top_apont.get("acoes_recomendadas") or ["Chave pronta para escrituracao fiscal."])[0]`
     - `blk_chave_anatomia` (`block_type: "custom_content"`):
       - Armazenar a decomposicao dos 9 segmentos da chave (`c_uf`, `aamm`, `cnpj_emitente`, `modelo`, `serie`, `numero_nfe`, `tipo_emissao`, `codigo_numerico`, `digito_verificador`, `dv_calculado`, `is_dv_valido`) em `props["access_key_anatomy"]` para renderizacao grafica segmentada no frontend.
     - `blk_chave_kpis` (`block_type: "kpi_grid"`):
       - KPIs:
         - `UF Emissora`: `f"{decomp.get('uf_sigla', '-')} ({decomp.get('c_uf', '-')})"`
         - `Documento`: `decomp.get("tipo_documento", "NF-e")`
         - `Numero / Serie`: `f"Nº {decomp.get('numero_nfe', '-')} / Serie {decomp.get('serie', '-')}"`
         - `CNPJ Emitente`: `str(decomp.get("cnpj_emitente", "-"))`
         - `Competencia (AAMM)`: `f"20{decomp.get('ano', '--')}/{decomp.get('mes', '--')}"`
         - `DV Modulo 11`: `f"DV {decomp.get('digito_verificador')} (Calculado: {decomp.get('dv_calculado')})"` com `status: "success" if is_dv_valido else "danger"`.
     - `blk_dupla_persona` (`block_type: "custom_content"`):
       - Preenche `props["persona_views"] = {"gestor": top_apont.get("explicacao_executiva", ""), "contador": top_apont.get("explicacao_tecnica", ""), "base_legal": top_apont.get("base_legal", [])}`.

2. **Subtipo B (`tipo == "xml_documento"`):**
   - Ler `res_xml = resultado_bruto.get("resultado") or {}`.
   - Extrair `valido = bool(res_xml.get("valido", False))`, `erros_count = int(res_xml.get("erros_impeditivos", 0))`, `alertas_count = int(res_xml.get("alertas_fiscais", 0))`, `apontamentos = res_xml.get("apontamentos") or []`.
   - Montar os blocos:
     - `blk_xml_status` (`block_type: "alert_callout"`):
       - `severity`: `"critical"` se `erros_count > 0` senao (`"warning"` se `alertas_count > 0` senao `"success"`)
       - `title`: `"Documento XML com Rejeicoes Impeditivas"` se `erros_count > 0` senao (`"XML Autorizavel com Alertas de Bitributacao/SPED"` se `alertas_count > 0` senao `"Documento XML 100% Conforme e Homologado"`)
       - `message`: Resumo executivo do primeiro apontamento critico/alerta ou confirmacao de conformidade.
     - `blk_xml_kpis` (`block_type: "kpi_grid"`):
       - KPIs: `Modelo` (`Mod 55` ou `Mod 65`), `UF Origem -> Destino` (`f"{res_xml.get('emit_uf', 'SP')} -> {res_xml.get('dest_uf', 'SP')}"`), `Erros Impeditivos` (`str(erros_count)`), `Alertas Contabeis` (`str(alertas_count)`).
     - `blk_xml_apontamentos` (`block_type: "ranking_list"` ou `"data_table"`):
       - Lista cada apontamento (`INVALID` e `WARNING`) com `regra_id`, `titulo`, `valor_esperado`, `valor_observado`, `explicacao_executiva` e `explicacao_tecnica`.
     - `props["persona_views"]`:
       - Consolida as explicacoes executivas (Visao Gestor) e as explicacoes tecnicas com tags XML e base legal (Visao Contador).

3. **Subtipo C (`tipo == "consulta_rejeicao_fiscal"`):**
   - Ler `resultados = resultado_bruto.get("resultados") or []` e `top_res = resultados[0] if resultados else {}`.
   - Extrair dinamicamente `meta = top_res.get("metadados_json") or {}` (se vier como string JSON, fazer `json.loads` seguro).
   - Substituir o texto fixo da linha 2773 por dados dinamicos reais do registro normativo:
     - `base_legal_str = meta.get("base_legal") or "MOC 7.0 / Normativa SEFAZ & SPED"`
     - `tags_xml_str = ", ".join(meta.get("campos_xml") or [])`
     - `gravidade_str = meta.get("gravidade") or "ALTA"`
   - Popular `props["persona_views"]`:
     - `gestor`: `f"{top_res.get('resumo_executivo', '')}\n\nImpacto Financeiro: {top_res.get('impacto_financeiro', '')}\n\nAcao no webPosto: {top_res.get('acao_recomendada', '')}"`
     - `contador`: `f"{top_res.get('conteudo_completo', '')}\n\nBase Legal: {base_legal_str}\nTags/Registros Afetados: {tags_xml_str or top_res.get('tabelas_banco', '')}"`

#### 1.2. Componente Frontend `FiscalShieldInspectorUI` em `web/js/aura-genui-widgets.js`
Criar a classe `FiscalShieldInspectorUI extends GenerativeModularCardUI` (ou aperfeicoar `GenerativeModularCardUI` e registrar o alias `render_FiscalShieldInspectorUI` / `auditoria_fiscal_sefaz`):
1. **Toggle Switch de Dupla Persona no Topo do Card:**
   - Renderizar um Segmented Control elegante com 2 botoes:
     - `[Visao Gestor & Pista]` (icone `briefcase` / destaque esmeralda/ciano): exibe o diagnostico executivo, impacto no caixa/pista e passo a passo no webPosto.
     - `[Visao Contador & SPED]` (icone `code-2` / destaque roxo/ciano): exibe o detalhamento tecnico, tags XML, regras do MOC/SPED, `valor_esperado` vs `valor_observado` e base legal.
   - A troca de aba ocorre instantaneamente no cliente (0ms) alternando classes CSS sem recarregar a pagina.
2. **Renderizador da Barra Anatomica de 44 Digitos (`access_key_anatomy`):**
   - Quando `this.props.access_key_anatomy` estiver presente, renderizar uma barra horizontal em fonte monoespacada (`font-mono text-xs`) dividida em chips coloridos com tooltip/legenda:
     - `[UF: 2d]` `[AAMM: 4d]` `[CNPJ: 14d]` `[Mod: 2d]` `[Serie: 3d]` `[Numero: 9d]` `[Emis: 1d]` `[Cod: 8d]` `[DV: 1d]`.
3. **Tratamento da Acao `copiar_diagnostico_contador`:**
   - Quando o usuario clicar no botao **"Copiar Diagnostico para o Contador"**, montar um laudo formatado em texto limpo (com cabecalho, codigo da regra, diagnostico tecnico, base legal e acao recomendada), copiar via `navigator.clipboard.writeText(...)` e exibir feedback otimista imediato no botao: `"Laudo Copiado para Area de Transferencia!"`.

---

### FASE 2: Smart Fiscal Composer & Detector Instantaneo de Chave 44d / XML

#### 2.1. Modificacoes em `web/index.html` e `web/js/aura-chat.js`
1. **Pilula Inteligente de Deteccao Fiscal (`#fiscal-smart-paste-pill`):**
   - Em `web/index.html`, logo acima de `.message-composer-container` (linha 1069), adicionar um container oculto por padrao:
     ```html
     <div id="fiscal-smart-paste-pill" class="hidden px-3.5 py-2 rounded-xl bg-slate-900/95 border border-cyan-500/40 flex items-center justify-between gap-2 text-xs text-cyan-300 backdrop-blur-md shadow-xl animate-fade-in">
       <div class="flex items-center gap-2 min-w-0">
         <span class="w-2 h-2 rounded-full bg-emerald-400 animate-ping flex-shrink-0"></span>
         <span id="fiscal-smart-pill-text" class="font-medium truncate">Chave SEFAZ de 44 digitos detectada</span>
       </div>
       <button id="btn-trigger-smart-fiscal" type="button" class="px-2.5 py-1 rounded-lg bg-cyan-500/20 hover:bg-cyan-500/30 text-white text-[11px] font-semibold border border-cyan-500/30 transition-all flex-shrink-0">
         Auditar Agora ->
       </button>
     </div>
     ```
2. **Botao de Upload/Inspecao Local de XML no Composer (`#btn-upload-fiscal-xml`):**
   - Na barra `.message-composer-container` (ao lado do `#btn-voice-input`), adicionar um input `<input type="file" id="fiscal-xml-file-input" accept=".xml" class="hidden" />` e um botao discreto com icone `file-code-2` (`title="Importar e Auditar XML de NF-e/NFC-e"`).
   - Em `web/js/aura-chat.js`:
     - Escutar o evento `input` / `paste` em `#chat-input-text`:
       - Se o texto contiver 44 digitos numericos seguidos (`/\b\d{44}\b/`), exibir `#fiscal-smart-paste-pill` com o texto `"Chave de Acesso SEFAZ (44 digitos) pronta para auditoria Modulo 11"`.
       - Se o texto contiver `<infNFe` ou `<nfeProc`, exibir `#fiscal-smart-paste-pill` com o texto `"Documento XML Fiscal detectado para auditoria completa"`.
     - Quando o usuario selecionar um arquivo `.xml` pelo botao `#btn-upload-fiscal-xml` (ou arrastar um `.xml` sobre o chat), ler o arquivo via `FileReader.readAsText` no navegador e enviar automaticamente para auditoria na AURA.

---

### FASE 3: Central de Gatilhos em 1-Clique (`aura-triggers.js`) e Command Palette (`Ctrl+K`)

#### 3.1. Inclusao dos Cards Fiscais em `web/js/aura-triggers.js`
1. No metodo `getToolsCatalog()` de `AuraTriggersController` (`web/js/aura-triggers.js`), adicionar na categoria `'fiscal'`:
   - **Card 1: `auditoria_fiscal_sefaz`**
     - `id`: `'auditoria_fiscal_sefaz'`
     - `aliases`: `['conhecimento_fiscal', 'fiscal_sefaz']`
     - `name`: `'Escudo Fiscal SEFAZ & Tributacao Monofasica'`
     - `category`: `'fiscal'`
     - `icon`: `'shield-check'`
     - `color`: `'cyan'`
     - `badge`: `'SEFAZ / LC 192 / SPED'`
     - `desc`: `'Auditoria deterministica de chaves de 44 digitos, XML, Rejeicoes SEFAZ (375, 629, 806, 958, 960), ICMS Monofasico (CST 61) e PIS/COFINS Conveniencia (CST 04).'`
     - `defaultParams`: `{ query: 'Quais as regras de ICMS Monofasico CST 61, PIS/COFINS CST 04 na conveniencia e principais rejeicoes SEFAZ?' }`
2. No metodo de formatacao do inspetor de gatilhos em `web/js/aura-triggers.js`:
   - Adicionar suporte visual para `auditoria_fiscal_sefaz`, exibindo:
     - Barra de busca rapida interna no proprio inspetor onde o usuario pode digitar qualquer codigo de rejeicao, NCM, CFOP ou colar uma chave de 44 digitos e ver os cards formatados (`Diagnostico`, `Acao no webPosto`, `Impacto Financeiro` e `Base Legal`).

#### 3.2. Atalhos no Menu Lateral e Command Palette (`web/index.html`)
1. No Cluster 2 (`Acoes Rapidas em 1-Clique`) da Sidebar em `web/index.html`, adicionar o botao **"Escudo Fiscal & SEFAZ"** (`onclick="if(window.auraApp){window.auraApp.askFrequent('Quais os pontos criticos de ICMS Monofasico CST 61, PIS/COFINS CST 04 na conveniencia e rejeicoes SEFAZ?'); window.auraApp.closeSidebar();}"`).
2. Na lista de sugestoes iniciais do card de boas-vindas (`#welcome-suggestions-container` em `web/index.html`), incluir o chip rapido **"Escudo Fiscal & SEFAZ"**.

---

### FASE 4: Estilos Liquid Glass, Modo Pista e Suite de Testes Automatizados

#### 4.1. Regras CSS em `web/css/aura.css`
Adicionar na secao final de `web/css/aura.css` as classes utilitarias para:
- `.fiscal-key-segment`: chips anatomicos da chave de 44 digitos com bordas translúcidas e destaque tabular (`font-variant-numeric: tabular-nums`).
- `.persona-switch-bar` e `.persona-switch-btn`: seletor tatil (altura minima `38px`) com transicao suave baseada apenas em `opacity` e `transform` (100% compativel com `body.gpu-guard-active` e `body.modo-pista-active`).

#### 4.2. Suite de Testes Obrigatoria
1. Em `tests/unit/test_fiscal_engine.py` ou `tests/unit/test_generative_modular_ui.py`:
   - Testar `build_canonical_genui_envelope` para `intencao="auditoria_fiscal_sefaz"` nos 3 cenarios:
     - Cenario 1: `tipo="chave_acesso"` (garantir presenca de `access_key_anatomy`, KPIs corretos com `numero_nfe` e `is_dv_valido`, e `persona_views`).
     - Cenario 2: `tipo="xml_documento"` (garantir que `blocks` nao venha vazio e contenha os apontamentos de `SEFAZ-REJ-806` / `SPED-RISCO-BITRIBUTACAO-PISCOFINS`).
     - Cenario 3: `tipo="consulta_rejeicao_fiscal"` (garantir extracao dinamica da base legal sem texto fixo engessado).
2. Teste de Higiene Zero Travessoes:
   - Verificar que `core/aura_engine.py`, `web/js/aura-genui-widgets.js`, `web/js/aura-triggers.js`, `web/js/aura-chat.js`, `web/index.html` e `web/css/aura.css` nao possuem nenhum caractere `\u2014` ou `\u2013`.

---

## 4. CHECKLIST DE EXECUCAO PARA O AGENTE

- [ ] **Passo 1:** Atualizar `build_canonical_genui_envelope` em `core/aura_engine.py` para hidratar `chave_acesso`, `xml_documento` e `consulta_rejeicao_fiscal` com `access_key_anatomy` e `persona_views`.
- [ ] **Passo 2:** Atualizar `web/js/aura-genui-widgets.js` para renderizar o Switch Dupla Persona (`Visao Gestor` vs `Visao Contador`), a Barra Anatomica de 44 digitos e a copia em 1-clique do laudo contabil para area de transferencia.
- [ ] **Passo 3:** Adicionar o Smart Fiscal Paste Pill e botao de leitura local de `.xml` em `web/index.html` e `web/js/aura-chat.js`.
- [ ] **Passo 4:** Adicionar o card `auditoria_fiscal_sefaz` e o formatador executivo correspondente em `web/js/aura-triggers.js`.
- [ ] **Passo 5:** Adicionar as classes de estilo em `web/css/aura.css` respeitando `modo-pista` e `gpu-guard`.
- [ ] **Passo 6:** Criar e executar os testes unitarios em `tests/unit/test_fiscal_engine.py` garantindo 100% de aprovacao e zero travessoes Unicode.
