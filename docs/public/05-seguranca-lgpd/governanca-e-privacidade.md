# Seguranca, Privacidade e Conformidade LGPD

A plataforma **AURA** foi projetada desde a fundacao com seguranca defensiva para ambientes de varejo em operacao continua.

---

## 1. Acesso SQL Estritamente Read-Only

Toda consulta executada no ERP do cliente passa por validacao sintatica e semantica baseada em AST (`sqlglot`, dialeto PostgreSQL) antes da execucao:

- Bloqueia comandos de escrita, DDL ou controle transacional (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `COPY`, `GRANT`).
- Bloqueia funcoes que degradam indices em juncoes (como `TRIM()` em clausulas `JOIN`), protegendo a performance do PDV em horarios de pico.
- O motor de backtesting (`core/simulation/backtest.py`) aplica exatamente as mesmas barreiras read-only ao apurar resultados realizados.

---

## 2. Protecao de Dados Pessoais (LGPD / PII)

Antes de qualquer trafego para servicos externos de sintese ou gravacao de telemetria de intencao:

- Um sanitizador local baseado em NLP e regras deterministicas (`spaCy` + expressoes regulares) redige dados pessoais sensiveis (CPF, CNPJ de pessoa fisica, telefones, e-mails, nomes proprios e sequencias numericas longas).
- A telemetria de intencoes armazena exclusivamente tokens normalizados e anonimizados, com **zero PII**.

---

## 3. Autenticacao, Sessao e Rede

- **Acesso Localhost:** Sessao protegida por cookie `HttpOnly; SameSite=Strict`.
- **Acesso LAN / VPN / Mobile:** Exige cabecalho `X-API-Key` valido (ou `Authorization: Bearer`) armazenado de forma segura no cliente (no Android, via Android Keystore).
- **Zero Bypass por Proxy:** Cabecalhos nao confiaveis como `X-Forwarded-For` nunca sao usados para burlar autenticacao.

---

## 4. Governanca Human-in-Command (HiC) e Auditabilidade

- **Bloqueio por padrao:** Regras extraidas da conversa ou propostas de calibracao de backtesting nascem sempre em estado `candidate` e nao alteram o comportamento do sistema sem decisao explicita (`approve` / `reject`).
- **Imutabilidade de Snapshots:** Simulacoes persistidas e resultados de backtesting sao gravados em modelo append-only, preservando a linha do tempo completa entre previsao `T0` e resultado realizado.
- **Rastreabilidade de Origem:** Cada resposta do simulador What-If informa no bloco `provenance` qual base de dados, quantas regras ativas e quais documentos fundamentaram o resultado.

---

## 5. Documentos Juridicos Complementares

Para clientes e departamentos juridicos, os textos formais de conformidade estao disponiveis em:
- [Marco Legal de Interoperabilidade e LGPD](../../compliance/marco_legal_interoperabilidade_lgpd.md)
- [Termo de Interoperabilidade e LGPD](../../compliance/termo_interoperabilidade_lgpd.md)
