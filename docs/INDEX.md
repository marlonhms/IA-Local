# INDICE MESTRE E MAPA DA DOCUMENTACAO TECNICA: AURA

> **Repositorio Base:** `ia-banco-local`  
> **Versao de Referencia:** `v2.1.0-NEXTGEN (Fases 1 a 4B Concluidas)`  
> **Status Geral do Sistema:** Producao Enterprise / B2B Gateway + Motor What-If Zero-Token, Governanca HiC e Backtesting ROI  
> **Regra Estrita de Conformidade:** ZERO travessoes Unicode (`\u2014` e `\u2013`) em toda a documentacao, codigos e testes. Utilizar exclusivamente hifens comuns (`-`), dois pontos (`:`) ou parenteses.

---

## 1. VISAO GERAL E ARQUITETURA DOCUMENTAL

Esta pasta reune toda a documentacao da plataforma **AURA**, dividida claramente entre o que pode se tornar **portal publico para parceiros e clientes** e o que pertence a **engenharia e operacao interna**:

1. **Portal Publico (`docs/public/`):** Documentacao pronta para publicacao externa (MkDocs/Docusaurus), organizada por Conceitos, Funcionalidades (Fases 1 a 4B), Integracao de Parceiros, Referencia de API e Seguranca/LGPD, livre de credenciais, IPs internos ou detalhes privados de infraestrutura.
2. **Engenharia Interna (`docs/internal/`, `architecture/`, `guides/`, `AUDITORIA_CARBON_*.md`):** Runbooks operacionais, migracoes, auditorias de codigo, tunelamento e manuais de infraestrutura local.
3. **Documentos Estrategicos, Compliance e Arquivo Historico (`compliance/`, `archive/`):** Pareceres juridicos LGPD, roadmaps concluidos e rascunhos historicos preservados para rastreabilidade.

```
docs/
├── README.md                              <- Indice Mestre e Mapa de Navegacao (sincronizado com INDEX.md)
├── INDEX.md                               <- Alias oficial de indexacao rapida
│
├── public/                                <- [PORTAL PUBLICO: PARCEIROS E CLIENTES]
│   ├── README.md                          <- Capa e Mapa do Portal Publico AURA
│   ├── 01-conceitos/
│   │   └── arquitetura-e-domain-packs.md  <- Modelo Hibrido Zero-Token, 5 Domain Packs e Protocolo HiC
│   ├── 02-funcionalidades/
│   │   └── motor-whatif-hic-backtesting.md <- What-If Monte Carlo, Governanca HiC, Backtesting 30/60/90d e Micro-Widgets
│   ├── 03-integracao-parceiros/
│   │   └── guia-rapido-parceiros.md       <- Onboarding ERP Read-Only, Domain Packs, SSE e APIs
│   ├── 04-referencia-api/
│   │   └── simulacao-memoria-backtesting.md <- Contratos HTTP/JSON de /api/v1/simulate/* e /api/v1/memory/*
│   └── 05-seguranca-lgpd/
│       └── governanca-e-privacidade.md    <- SQL Read-Only (sqlglot), Sanitizacao PII, Auth Dual e HiC
│
├── internal/                              <- [ENGENHARIA E OPERACAO INTERNA]
│   ├── README.md                          <- Mapa Interno e Regras de Fronteira (public vs. internal)
│   └── runbook-simulacao-memoria-migracoes.md <- Runbook Fases 1-4B, Esquema 0003_simulation_memory e Troubleshooting
│
├── AUDITORIA_CARBON_CORE.md               <- [INTERNO] Auditoria e Hardening do Core Python/FastAPI
├── AUDITORIA_CARBON_UI.md                 <- [INTERNO] Auditoria Obsidian UI, Zero-CLS e SDK Web
├── AUDITORIA_CARBON_ANDROID.md            <- [INTERNO] Auditoria Android Compose, Keystore/TEE e SSE
├── roadmap.md                             <- [CONCLUIDO] Roadmap Oficial 2.0.0-PRO (5 Modulos de Alto ROI e B2B)
├── roadmap_apendice_conhecimento_multicamada_rag.md <- [CONCLUIDO] RAG Multicamada (pgvector/FTS5 e RLS)
├── roadmap_apendice_gui_fiscal.md         <- [CONCLUIDO] GUI & GenUI Fiscal Deluxe (44 Digitos, XML Dropzone, Dupla Persona)
├── roadmap_apendice_sinergia_dual_channel.md <- [CONCLUIDO] Sinergia Dual-Channel e Fluxo Chat -> Canvas
├── roadmap_apendice_ux_textual_chat.md    <- [CONCLUIDO] Tipografia Cognitiva Editorial e Anti-Fadiga no Chat
├── roadmap_apendice_micro_agents_roi_varejo.md <- [CONCLUIDO] Micro-Agentes e Motor Universal de ROI Varejo
├── roadmap_apendice_roteamento_rag_verdade_minima.md <- [CONCLUIDO] Roteamento Hibrido e Verdade Minima para SLMs/Flash
├── roadmap_apendice_desenviesamento_holistico_e_resiliencia_streaming.md <- [CONCLUIDO] Desenviesamento Holistico e Streaming Atomico
├── APENDICE_SESSOES_RETORNO_WHATSAPP_E_MOTOR_FISCAL.md <- [ESPECIFICADO] Sessoes Retorno WhatsApp e Fronteira Fiscal
├── apendice_longo_prazo.md                <- [ATIVO] Visao Tecnica e Arquitetura 30-90+ Dias
├── Deep research Estratégia e Arquitetura da AURA.md <- [ATIVO] Estudo Estrategico Canonico
├── dossie_tecnico.md                      <- [ATIVO] Dossie Tecnico Consolidado do Sistema AURA
├── Estratégia de Produto IA AURA.md       <- [ATIVO] Diretrizes de Produto e Posicionamento B2B
│
├── guides/                                <- [GUIAS OPERACIONAIS E INTEGRACOES]
│   ├── PLANO_IMPLEMENTACAO_SUPER_INTELIGENCIA_UNIVERSAL.md <- Plano Diretor Fases 1 a 4 (Super Inteligencia)
│   ├── GUIA_INTEGRACAO_PARCEIRO.md        <- Manual Detalhado de Integracao com ERPs (Partner API)
│   ├── guia_ativacao_cerebro_central_vps_multitenant.md <- Ativacao do Cerebro Central na VPS, pgvector e RLS
│   ├── guia_deploy_posto.md               <- Manual de Instalacao e Deploy Local em Ambiente de Borda
│   ├── guia_operacional_apis_publicas.md  <- Catalogo e Operacao dos Conectores Publicos (ANP, BCB, Confaz)
│   └── guia_ponte_desenvolvimento_remoto_tailscale.md <- Configuracao de Tunel Remoto de Engenharia
│
├── architecture/                          <- [ARQUITETURA E PROTOCOLOS DE ENGENHARIA]
│   ├── Arquitetura GenUI para Edge AI.md  <- Padrao e Pipeline de Renderizacao Generativa Local
│   └── protocolo_streaming_genui.md       <- Contrato e Estrutura de Eventos SSE do Motor
│
├── compliance/                            <- [CONFORMIDADE LEGAL E JURIDICA]
│   ├── marco_legal_interoperabilidade_lgpd.md <- Parecer Juridico (LGPD, Marco Civil e Lei de Software)
│   └── termo_interoperabilidade_lgpd.md   <- Minuta Contratual e Termo de Adesao B2B
│
├── media/                                 <- [ASSETS DE AUDIO E VIDEO]
│   └── Audio 1.ogg
│
└── archive/                               <- [HISTORICO E ARQUIVO MORTO]
    ├── roadmaps/                          <- Roadmaps de Fases Anteriores Ja Entregues e Concluidas
    └── drafts/                            <- Rascunhos de Trabalho e Fragmentos de Copy
```

---

## 2. MATRIZ DE RASTREABILIDADE DOCUMENTAL

| Documento | Caminho Relativo | Camada | Status | Proposito / Escopo |
| :--- | :--- | :---: | :---: | :--- |
| **Portal Publico AURA** | [`public/README.md`](public/README.md) | Publico | **ATIVO** | Capa oficial para parceiros, clientes e integradores externos. |
| **Arquitetura & Domain Packs** | [`public/01-conceitos/arquitetura-e-domain-packs.md`](public/01-conceitos/arquitetura-e-domain-packs.md) | Publico | **ATIVO** | Arquitetura Zero-Token, 5 Domain Packs, isolamento e protocolo HiC. |
| **Motor What-If, HiC & Backtest** | [`public/02-funcionalidades/motor-whatif-hic-backtesting.md`](public/02-funcionalidades/motor-whatif-hic-backtesting.md) | Publico | **ATIVO** | Especificacao funcional das Fases 1 a 4B e micro-widgets Web/Android. |
| **Guia Rapido de Parceiros** | [`public/03-integracao-parceiros/guia-rapido-parceiros.md`](public/03-integracao-parceiros/guia-rapido-parceiros.md) | Publico | **ATIVO** | Onboarding passo a passo para ERPs e integradores ISV. |
| **Referencia API (Simulacao & HiC)** | [`public/04-referencia-api/simulacao-memoria-backtesting.md`](public/04-referencia-api/simulacao-memoria-backtesting.md) | Publico | **ATIVO** | Contratos JSON/HTTP de `/api/v1/simulate/*` e `/api/v1/memory/*`. |
| **Seguranca & LGPD** | [`public/05-seguranca-lgpd/governanca-e-privacidade.md`](public/05-seguranca-lgpd/governanca-e-privacidade.md) | Publico | **ATIVO** | SQL Read-Only (`sqlglot`), sanitizacao PII, Auth Dual e trilha HiC. |
| **Mapa Interno de Engenharia** | [`internal/README.md`](internal/README.md) | Interno | **ATIVO** | Guia de engenharia e regras de fronteira `public/` vs. `internal/`. |
| **Runbook Fases 1 a 4B** | [`internal/runbook-simulacao-memoria-migracoes.md`](internal/runbook-simulacao-memoria-migracoes.md) | Interno | **ATIVO** | Modulos Python/Android, esquema `0003_simulation_memory` e troubleshooting. |
| **Plano Super Inteligencia** | [`guides/PLANO_IMPLEMENTACAO_SUPER_INTELIGENCIA_UNIVERSAL.md`](guides/PLANO_IMPLEMENTACAO_SUPER_INTELIGENCIA_UNIVERSAL.md) | Interno | **CONCLUIDO** | Plano arquitetural completo das Fases 1 a 4. |
| **Auditoria Carbon Core** | [`AUDITORIA_CARBON_CORE.md`](AUDITORIA_CARBON_CORE.md) | Interno | **ATIVO** | Auditoria tecnica de backend Python/FastAPI. |
| **Auditoria Carbon UI** | [`AUDITORIA_CARBON_UI.md`](AUDITORIA_CARBON_UI.md) | Interno | **ATIVO** | Auditoria de design system Obsidian, Zero-CLS e SDK Web. |
| **Auditoria Carbon Android** | [`AUDITORIA_CARBON_ANDROID.md`](AUDITORIA_CARBON_ANDROID.md) | Interno | **ATIVO** | Auditoria do aplicativo nativo Android Compose + Keystore/TEE. |
| **Roadmap 2.0.0-PRO** | [`roadmap.md`](roadmap.md) | Engenharia | **CONCLUIDO** | Plano diretor dos 5 modulos de alto ROI: `/roi-diagnostic`, Semantic Cache, Zero-Trust Gateway, Z-Score CLT e Edge Hardening. |
| **Apendice Conhecimento Multicamada** | [`roadmap_apendice_conhecimento_multicamada_rag.md`](roadmap_apendice_conhecimento_multicamada_rag.md) | Arquitetura / RAG | **CONCLUIDO** | RAG Multicamada no pgvector e FTS5 com isolamento RLS. |
| **Apendice GUI & GenUI Fiscal** | [`roadmap_apendice_gui_fiscal.md`](roadmap_apendice_gui_fiscal.md) | Frontend / GenUI | **CONCLUIDO** | Micro-widget `FiscalShieldInspectorUI`, decompositor de 44 digitos SEFAZ e Smart Paste XML. |
| **Apendice Sinergia Dual-Channel** | [`roadmap_apendice_sinergia_dual_channel.md`](roadmap_apendice_sinergia_dual_channel.md) | UX / Coreografia | **CONCLUIDO** | Nitidez optica ClearType e fluxo sequencial `Chat -> Canvas`. |
| **Apendice UX Textual Chat** | [`roadmap_apendice_ux_textual_chat.md`](roadmap_apendice_ux_textual_chat.md) | UX / Tipografia | **CONCLUIDO** | Ergonomia tipografica, tokenizacao tabular de metricas e Progressive Disclosure. |
| **Apendice Micro-Agentes & ROI Varejo** | [`roadmap_apendice_micro_agents_roi_varejo.md`](roadmap_apendice_micro_agents_roi_varejo.md) | Arquitetura / ROI | **CONCLUIDO** | Micro-SOPs por intencao e Motor Universal de ROI Multi-Vertical. |
| **Apendice Verdade Minima SLM** | [`roadmap_apendice_roteamento_rag_verdade_minima.md`](roadmap_apendice_roteamento_rag_verdade_minima.md) | Engenharia / RAG | **CONCLUIDO** | Gate lexico deterministico e Scoped Tooling para modelos Flash. |
| **Apendice Desenviesamento Holistico** | [`roadmap_apendice_desenviesamento_holistico_e_resiliencia_streaming.md`](roadmap_apendice_desenviesamento_holistico_e_resiliencia_streaming.md) | Engenharia / Resiliencia | **CONCLUIDO** | Equilibrio dos 4 pilares executivos e streaming atomico com `stream_reset`. |
| **Apendice Retorno WhatsApp e Motor Fiscal** | [`APENDICE_SESSOES_RETORNO_WHATSAPP_E_MOTOR_FISCAL.md`](APENDICE_SESSOES_RETORNO_WHATSAPP_E_MOTOR_FISCAL.md) | Android / Fiscal | **ESPECIFICADO** | Sessoes dedicadas de retorno WhatsApp e fronteira fiscal. |
| **Apendice Longo Prazo** | [`apendice_longo_prazo.md`](apendice_longo_prazo.md) | Arquitetura | **ATIVO** | Visao 30-90+ dias: DuckDB Hypertenancy, SLMs na borda e Domain Packs. |
| **Deep Research Estrategia** | [`Deep research Estratégia e Arquitetura da AURA.md`](Deep%20research%20Estratégia%20e%20Arquitetura%20da%20AURA.md) | Estrategia | **ATIVO** | Estudo aprofundado de viabilidade, ROI e diferenciais de borda. |
| **Dossie Tecnico** | [`dossie_tecnico.md`](dossie_tecnico.md) | Sistema | **ATIVO** | Sintese de componentes, requisitos e topologia de execucao. |
| **Estrategia de Produto** | [`Estratégia de Produto IA AURA.md`](Estratégia%20de%20Produto%20IA%20AURA.md) | Produto | **ATIVO** | Posicionamento estrategico e canais de monetizacao. |
| **Integracao Parceiros (Completo)** | [`guides/GUIA_INTEGRACAO_PARCEIRO.md`](guides/GUIA_INTEGRACAO_PARCEIRO.md) | Guia | **ATIVO** | Especificacao tecnica detalhada do gateway para conexao com ERPs. |
| **Ativacao Cerebro Central** | [`guides/guia_ativacao_cerebro_central_vps_multitenant.md`](guides/guia_ativacao_cerebro_central_vps_multitenant.md) | Infra / RLS | **ATIVO** | Manual de implantacao da VPS, setup do pgvector e RLS multi-tenant. |
| **Deploy em Posto** | [`guides/guia_deploy_posto.md`](guides/guia_deploy_posto.md) | Operacao | **ATIVO** | Passo a passo de instalacao do servico Windows local. |
| **Conectores Publicos** | [`guides/guia_operacional_apis_publicas.md`](guides/guia_operacional_apis_publicas.md) | Operacao | **ATIVO** | Procedimentos operacionais para integracoes com ANP, Bacen e Confaz. |
| **Tunel Tailscale** | [`guides/guia_ponte_desenvolvimento_remoto_tailscale.md`](guides/guia_ponte_desenvolvimento_remoto_tailscale.md) | DevOps | **ATIVO** | Guia de acesso remoto seguro e pareamento ponto a ponto. |
| **Arquitetura GenUI** | [`architecture/Arquitetura GenUI para Edge AI.md`](architecture/Arquitetura%20GenUI%20para%20Edge%20AI.md) | Arquitetura | **ATIVO** | Design system e ciclo de vida de micro-widgets renderizados na borda. |
| **Protocolo GenUI** | [`architecture/protocolo_streaming_genui.md`](architecture/protocolo_streaming_genui.md) | Arquitetura | **ATIVO** | Formato de eventos SSE e payload JSON de streaming de widgets. |
| **Marco Legal LGPD** | [`compliance/marco_legal_interoperabilidade_lgpd.md`](compliance/marco_legal_interoperabilidade_lgpd.md) | Juridico | **ATIVO** | Parecer formal de legalidade para leitura read-only em bancos de dados. |
| **Termo LGPD** | [`compliance/termo_interoperabilidade_lgpd.md`](compliance/termo_interoperabilidade_lgpd.md) | Juridico | **ATIVO** | Contrato e termo de responsabilidade para assinatura entre cliente e AURA. |
| **Arquivo Historico** | [`archive/roadmaps/roadmap_producao_enterprise.md`](archive/roadmaps/roadmap_producao_enterprise.md) | Arquivo | **CONCLUIDO** | Roadmaps legados e entregas P0 a P5 em `archive/roadmaps/`. |

---

## 3. INSTRUCOES PARA AGENTES DE IA E NOVOS CONTRIBUIDORES

1. **Separacao Publico vs. Interno:** Documentacao voltada a clientes, parceiros e integracao de API vai em [`public/`](public/README.md). Auditorias, runbooks de infraestrutura local e scripts operacionais ficam em [`internal/`](internal/README.md), [`guides/`](guides/) e [`architecture/`](architecture/).
2. **Consultas Historicas:** Nao reescreva solucoes ja implementadas no passado; consulte [`archive/roadmaps/`](archive/roadmaps/).
3. **Integracoes de Terceiros:** Utilize [`public/03-integracao-parceiros/guia-rapido-parceiros.md`](public/03-integracao-parceiros/guia-rapido-parceiros.md), [`public/04-referencia-api/simulacao-memoria-backtesting.md`](public/04-referencia-api/simulacao-memoria-backtesting.md) e [`guides/GUIA_INTEGRACAO_PARCEIRO.md`](guides/GUIA_INTEGRACAO_PARCEIRO.md).
4. **Regra Inegociavel de Codificacao:** Nunca insira travessoes Unicode (`\u2014` ou `\u2013`) em nenhum arquivo do projeto. Use apenas `-` comum.
