# Documentacao Publica da Plataforma AURA

> **Audiencia:** Clientes, Parceiros de ERP/ISV e Integradores Tecnicos  
> **Escopo:** Visao de produto, funcionalidades centrais, integracao de parceiros, referencia de API e seguranca/LGPD.  
> **Politica de Fronteira:** Todo o conteudo sob `docs/public/` e redigido para publicacao externa, livre de credenciais, enderecos internos ou detalhes privados de infraestrutura.

---

## Mapa do Portal

| Secao | Conteudo | Para quem e |
| :--- | :--- | :--- |
| **[01. Conceitos e Arquitetura](01-conceitos/arquitetura-e-domain-packs.md)** | Modelo Edge AI hibrido, calculo deterministico zero-token, 5 Domain Packs oficiais e protocolo Human-in-Command (HiC). | Gestores, Arquitetos e Parceiros |
| **[02. Funcionalidades (Fases 1 a 4B)](02-funcionalidades/motor-whatif-hic-backtesting.md)** | Simulador What-If Monte Carlo (`P10/P50/P90`), Memoria Institucional HiC, Sugestoes Proativas, Backtesting de ROI (`30/60/90d`) e Micro-Widgets GenUI (Web e Android). | Clientes, Produto e Engenharia |
| **[03. Integracao para Parceiros](03-integracao-parceiros/guia-rapido-parceiros.md)** | Como conectar ERPs (leitura somente leitura), configurar um Domain Pack, autenticar via `X-API-Key` e consumir os canais Web/Mobile. | Parceiros ERP e ISVs |
| **[04. Referencia de API](04-referencia-api/simulacao-memoria-backtesting.md)** | Contratos HTTP/JSON oficiais de `/api/v1/simulate/*` e `/api/v1/memory/*`, schemas, exemplos e codigos de resposta. | Desenvolvedores e Integradores |
| **[05. Seguranca, Privacidade e LGPD](05-seguranca-lgpd/governanca-e-privacidade.md)** | Blindagem SQL Read-Only, sanitizacao de PII, isolamento multi-tenant/multi-dominio e trilha auditavel HiC. | Compliance, Juridico e TI |

---

## Principios da Plataforma AURA

1. **Determinismo Financeiro e Fiscal:** Toda conta de margem, elasticidade, fluxo de caixa, tributacao e backtesting roda em motor matematico deterministico. Modelos de linguagem (LLM) nunca substituem calculo financeiro.
2. **Zero-Token na Exploracao Interativa:** Ajustes de cenarios What-If, validacao de regras de negocio, feed de governanca HiC e scorecards de backtesting executam com `llm_calls = 0`, acionando sintese de IA apenas sob demanda explicita do operador.
3. **Human-in-Command (HiC):** Nenhuma regra descoberta, ajuste de calibracao ou acao operacional entra em vigor automaticamente sem aprovacao explicita de um responsavel humano.
4. **Multi-Dominio Estrito:** Cada vertical de varejo opera isolada pelo seu `pack_id`, sem vazamento de metricas, ferramentas ou widgets especificos entre segmentos.
5. **Privacidade na Borda (LGPD):** Consultas ao ERP sao estritamente `READ-ONLY` e dados pessoais (PII) sao sanitizados antes de qualquer sintese externa.
