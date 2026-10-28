# INDICE MESTRE E MAPA DA DOCUMENTACAO TECNICA: AURA

> **Repositorio Base:** `ia-banco-local`  
> **Status Geral do Sistema:** Producao Enterprise / B2B Gateway (Fase Ativa: Execucao do Roadmap de Alto ROI)  
> **Regra Estrita de Conformidade:** ZERO travessoes Unicode (`\u2014` e `\u2013`) em toda a documentacao, codigos e testes. Utilizar exclusivamente hifens comuns (`-`), dois pontos (`:`) ou parenteses.

---

## 1. VISAO GERAL E ARQUITETURA DOCUMENTAL

Esta pasta reune toda a inteligencia estrategica, arquitetura tecnica, manuais operacionais, termos de conformidade juridica e o historico de evolucao da plataforma **AURA**.

Para manter o foco do time de engenharia e dos agentes de IA executores, a documentacao e organizada em tres niveis:
1. **Documentos Ativos (Raiz de `docs/`):** O plano diretor em execucao (`roadmap.md`), o horizonte de longo prazo (`apendice_longo_prazo.md`), o estudo estrategico canônico (`Deep research...`) e o dossie tecnico.
2. **Guias e Especificacoes (`guides/`, `architecture/`, `compliance/`):** Manuais praticos de implantacao, protocolos de rede e salvaguardas legais.
3. **Arquivo Historico (`archive/`):** Todos os roadmaps e rascunhos de fases concluidas com sucesso no passado, preservados para consulta e rastreabilidade historica.

```
docs/
├── README.md                              <- Indice Mestre e Mapa de Navegacao (este documento)
├── INDEX.md                               <- Alias oficial de indexacao rapida
├── roadmap.md                             <- [ATIVO] Roadmap Oficial Imediato (5 Modulos de Alto ROI e B2B)
├── apendice_longo_prazo.md                <- [ATIVO] Visao Tecnica e Arquitetura 30-90+ Dias (DuckDB, SLMs, Packs)
├── Deep research Estrategia e Arquitetura da AURA.md <- [ATIVO] Estudo Estrategico Canonico
├── dossie_tecnico.md                      <- [ATIVO] Dossie Tecnico Consolidado do Sistema AURA
├── Estrategia de Produto IA AURA.md       <- [ATIVO] Diretrizes de Produto e Posicionamento B2B
│
├── guides/                                <- [GUIAS OPERACIONAIS E INTEGRACOES]
│   ├── GUIA_INTEGRACAO_PARCEIRO.md        <- Manual de Integracao com ERPs de Mercado (Opcao A / Partner API)
│   ├── guia_deploy_posto.md               <- Manual de Instalacao e Deploy Local em Ambiente de Borda
│   ├── guia_operacional_apis_publicas.md  <- Catalogo e Operacao dos Conectores de Dados Publicos (ANP, BCB, Confaz)
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
│   ├── 2026-10-07 08-35-50.mp4
│   └── Audio 1.ogg
│
└── archive/                               <- [HISTORICO E ARQUIVO MORTO]
    ├── roadmaps/                          <- Roadmaps de Fases Anteriores Ja Entregues e Concluidas
    │   ├── roadmap_producao_enterprise.md <- Fases P0 a P5: Producao Enterprise (100% Concluida)
    │   ├── roadmap_genui.md               <- Interface Generativa e Micro-Widgets (100% Concluida)
    │   ├── roadmap_integracao_apis_publicas.md <- Hub de Dados Publicos e Conectores (100% Concluida)
    │   ├── roadmap_uiux_inspiracao_lovable.md  <- Redesign UI/UX e Micro-Interacoes (100% Concluida)
    │   ├── roadmap_showcase.md            <- Construcao Inicial do Showcase Executivo (100% Concluida)
    │   ├── roadmap_blindagem_juridica_clean_room.md <- Protocolo Clean-Room Juridico (100% Concluido)
    │   ├── ROADMAP_SENTINEL_AURA.md       <- Especificacao Sentinel e Resiliencia Local (Concluido)
    │   ├── roadmap_aila.md                <- Rascunho da Assistente Aila (Pre-AURA)
    │   └── Roadmap Novo Aura Local.md     <- Primeiro Roadmap da Transicao Local (Historico)
    └── drafts/                            <- Rascunhos de Trabalho e Fragmentos de Copy
        ├── bloco hero.txt
        └── blocos de referencia harness.txt
```

---

## 2. MATRIZ DE RASTREABILIDADE DOCUMENTAL

A tabela abaixo conecta cada documento ao seu papel no ciclo de vida da AURA:

| Documento | Caminho Relativo | Categoria | Status | Proposito / Escopo |
| :--- | :--- | :---: | :---: | :--- |
| **Roadmap Atual** | [`roadmap.md`](roadmap.md) | Engenharia | **EM EXECUCAO** | Plano diretor dos 5 modulos imediatos: `/roi-diagnostic`, Semantic Cache, Zero-Trust Gateway, Z-Score CLT e Edge Hardening. |
| **Apendice Longo Prazo** | [`apendice_longo_prazo.md`](apendice_longo_prazo.md) | Arquitetura | **ATIVO** | Visao 30-90+ dias: DuckDB Hypertenancy colunar, SLMs locais na borda, Domain Packs e Pricing B2B. |
| **Apendice Conhecimento Multicamada** | [`roadmap_apendice_conhecimento_multicamada_rag.md`](roadmap_apendice_conhecimento_multicamada_rag.md) | Arquitetura / RAG | **EM EXECUCAO** | RAG Multicamada (core, vertical, erp, tenant) no pgvector 0.8.6, chunking do Confluence, isolamento LGPD e busca hibrida. |
| **Deep Research Estrategia** | [`Deep research Estrategia e Arquitetura da AURA.md`](Deep%20research%20Estratégia%20e%20Arquitetura%20da%20AURA.md) | Estrategia | **ATIVO** | Estudo aprofundado de viabilidade, retorno sobre investimento, dados nacionais de perdas no varejo e diferenciais de borda. |
| **Dossie Tecnico** | [`dossie_tecnico.md`](dossie_tecnico.md) | Sistema | **ATIVO** | Sintese de componentes, requisitos, stack tecnologica e topologia de execucao. |
| **Estrategia de Produto** | [`Estrategia de Produto IA AURA.md`](Estratégia%20de%20Produto%20IA%20AURA.md) | Produto | **ATIVO** | Posicionamento estrategico, abordagem nao-invasiva e canais de monetizacao. |
| **Integracao Parceiros** | [`guides/GUIA_INTEGRACAO_PARCEIRO.md`](guides/GUIA_INTEGRACAO_PARCEIRO.md) | Guia | **ATIVO** | Especificacao tecnica do gateway para conexao com WebPosto e outros ERPs via `raw-sync` e `chat`. |
| **Deploy em Posto** | [`guides/guia_deploy_posto.md`](guides/guia_deploy_posto.md) | Operacao | **ATIVO** | Passo a passo de instalacao do servico Windows local e configuracao de servico. |
| **Conectores Publicos** | [`guides/guia_operacional_apis_publicas.md`](guides/guia_operacional_apis_publicas.md) | Operacao | **ATIVO** | Procedimentos operacionais para integracoes com ANP, Bacen e Confaz. |
| **Tunel Tailscale** | [`guides/guia_ponte_desenvolvimento_remoto_tailscale.md`](guides/guia_ponte_desenvolvimento_remoto_tailscale.md) | DevOps | **ATIVO** | Guia de acesso remoto seguro e pareamento ponto a ponto. |
| **Arquitetura GenUI** | [`architecture/Arquitetura GenUI para Edge AI.md`](architecture/Arquitetura%20GenUI%20para%20Edge%20AI.md) | Arquitetura | **ATIVO** | Design system e ciclo de vida de micro-widgets renderizados na borda local. |
| **Protocolo GenUI** | [`architecture/protocolo_streaming_genui.md`](architecture/protocolo_streaming_genui.md) | Arquitetura | **ATIVO** | Formato de eventos SSE e payload JSON de streaming de widgets. |
| **Marco Legal LGPD** | [`compliance/marco_legal_interoperabilidade_lgpd.md`](compliance/marco_legal_interoperabilidade_lgpd.md) | Juridico | **ATIVO** | Parecer formal de legalidade para leitura somente de leitura em bancos de dados. |
| **Termo LGPD** | [`compliance/termo_interoperabilidade_lgpd.md`](compliance/termo_interoperabilidade_lgpd.md) | Juridico | **ATIVO** | Contrato e termo de responsabilidade para assinatura entre cliente e AURA. |
| **Producao Enterprise** | [`archive/roadmaps/roadmap_producao_enterprise.md`](archive/roadmaps/roadmap_producao_enterprise.md) | Arquivo | **CONCLUIDO** | Fases P0 a P5 que consolidaram os 650+ testes, modo offline e outbox transacional. |
| **Roadmap GenUI** | [`archive/roadmaps/roadmap_genui.md`](archive/roadmaps/roadmap_genui.md) | Arquivo | **CONCLUIDO** | Implementacao dos widgets de decisao, cartoes interativos e streaming. |
| **APIs Publicas** | [`archive/roadmaps/roadmap_integracao_apis_publicas.md`](archive/roadmaps/roadmap_integracao_apis_publicas.md) | Arquivo | **CONCLUIDO** | Integracao com tabelas publicas de combustiveis e indices economicos. |
| **UI/UX Lovable** | [`archive/roadmaps/roadmap_uiux_inspiracao_lovable.md`](archive/roadmaps/roadmap_uiux_inspiracao_lovable.md) | Arquivo | **CONCLUIDO** | Evolucao visual do chat, paleta Obsidian e cockpit executivo. |
| **Showcase Inicial** | [`archive/roadmaps/roadmap_showcase.md`](archive/roadmaps/roadmap_showcase.md) | Arquivo | **CONCLUIDO** | Construcao da landing page e showcase interativo em `web/showcase.html`. |
| **Clean Room Juridico** | [`archive/roadmaps/roadmap_blindagem_juridica_clean_room.md`](archive/roadmaps/roadmap_blindagem_juridica_clean_room.md) | Arquivo | **CONCLUIDO** | Processo de auditoria de propriedade intelectual e isolamento de codigo. |
| **Roadmap Sentinel** | [`archive/roadmaps/ROADMAP_SENTINEL_AURA.md`](archive/roadmaps/ROADMAP_SENTINEL_AURA.md) | Arquivo | **LEGADO** | Especificacao do servico de monitoramento continuo e resiliencia. |
| **Roadmap Aila** | [`archive/roadmaps/roadmap_aila.md`](archive/roadmaps/roadmap_aila.md) | Arquivo | **LEGADO** | Fase conceitual previa a adocao da arquitetura AURA. |
| **Roadmap Aura Local** | [`archive/roadmaps/Roadmap Novo Aura Local.md`](archive/roadmaps/Roadmap%20Novo%20Aura%20Local.md) | Arquivo | **LEGADO** | Documento inicial da transicao para modelo offline-first. |

---

## 3. INSTRUCOES PARA AGENTES DE IA E NOVOS CONTRIBUIDORES

1. **Plano de Execucao Vigente:** O unico documento que define as prioridades atuais de implementacao de codigo e o [`roadmap.md`](roadmap.md). Qualquer tarefa de desenvolvimento imediato deve obrigatoriamente se basear nos 5 modulos ali especificados.
2. **Consultas Historicas:** Nao reescreva solucoes ja implementadas no passado. Se precisar entender como o Outbox transacional, a suite de testes offline ou o motor GenUI foram construidos, consulte a pasta [`archive/roadmaps/`](archive/roadmaps/).
3. **Integracoes de Terceiros:** Para plugar novos parceiros de ERP ou BI sem instalacao de agente de borda, o documento canonico e o [`guides/GUIA_INTEGRACAO_PARCEIRO.md`](guides/GUIA_INTEGRACAO_PARCEIRO.md).
4. **Regra Inegociavel de Codificacao:** Nunca insira travessoes Unicode (`\u2014` ou `\u2013`) em nenhum arquivo do projeto. Use apenas `-` comum.
