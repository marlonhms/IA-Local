# Guia Rapido de Integracao para Parceiros (ERP / ISV)

Este guia orienta parceiros de software, ERPs e integradores sobre como conectar sua plataforma ao ecossistema **AURA**.

---

## 1. Pre-Requisitos de Integracao

1. **Acesso Read-Only ao ERP:** A AURA exige exclusivamente credencial de leitura (`SELECT`) para consultas analiticas e backtesting. Nenhuma operacao de escrita direta no banco do ERP e executada pelo motor analitico.
2. **Identificacao de Escopo:** Cada requisicao deve informar:
   - `tenant_id`: identificador unico da rede ou unidade cliente (padrao `"default"` em instalacao single-tenant).
   - `pack_id`: identificador do Domain Pack ativo (`fuel_convenience`, `pharmacy_health`, `retail_supermarket`, `autocenter_parts` ou `wholesale_distribution`).
3. **Autenticacao:**
   - Em acessos remotos ou via rede corporativa/VPN: enviar cabecalho HTTP `X-API-Key: <sua-chave>` (ou `Authorization: Bearer <sua-chave>`).
   - Em sessoes web no mesmo host (`localhost`): cookie de sessao `HttpOnly; SameSite=Strict`.

---

## 2. Fluxo Recomendado de Integracao

### Passo 1: Selecionar ou configurar o Domain Pack
Defina qual `pack_id` representa a vertical do cliente. Cada Domain Pack possui:
- Regras duras declarativas em YAML (pisos de margem, limites operacionais e guardrails de risco).
- Adaptador de ferramentas isolado por dominio (`DomainToolRegistry`).
- Perfil visual e prompts de contexto adaptados a terminologia do segmento.

### Passo 2: Conectar o fluxo conversacional e GenUI (SSE)
- Consuma o endpoint de streaming SSE da AURA utilizando transporte HTTP com suporte a reconexao e tratamento do evento `stream_reset` (que limpa o buffer parcial antes de retomar a resposta em contingencia).
- Renderize os envelopes GenUI estruturados ou utilize o SDK Web (`aura-sdk`) / cliente Android nativo.

### Passo 3: Habilitar Simulacao What-If Zero-Token
- Para exploracao interativa (sliders de preco, desconto, custo e prazo), envie chamadas com debounce (`150ms` a `200ms`) para `POST /api/v1/simulate/recompute` com `persist_snapshot: false`.
- Quando o operador decidir aprovar e acompanhar um cenario no mundo real, grave o snapshot com `persist_snapshot: true`.

### Passo 4: Integrar Governanca HiC e Backtesting
- Consulte `GET /api/v1/memory/suggestions?pack_id=<pack>&tenant_id=<tenant>` para alimentar o banner de regras candidatas e simulacoes sugeridas.
- Processe aprovacoes e rejeicoes explicitas do usuario via `POST /api/v1/memory/rules/{rule_id}/decision`.
- Agende execucoes periodicas de `POST /api/v1/simulate/backtest/run` e exiba a acuracia historica no cliente consumindo `GET /api/v1/simulate/backtest/scorecard`.

---

## 3. Verificacao de Saude e Prontidao

Antes de iniciar o fluxo de integracao, valide a conectividade do gateway com:

```http
GET /api/v1/aura/health
```

Resposta esperada (`200 OK`):

```json
{
  "status": "healthy"
}
```

Para detalhes completos de payloads, parametros e codigos HTTP dos endpoints de simulacao, memoria e backtesting, consulte a **[Referencia de API](../04-referencia-api/simulacao-memoria-backtesting.md)**.
