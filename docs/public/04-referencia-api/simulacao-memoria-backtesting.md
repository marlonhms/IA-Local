# Referencia de API: Simulacao What-If, Memoria HiC e Backtesting

Todos os endpoints abaixo sao **deterministicos (`llm_calls = 0`)**, respeitam isolamento estrito por `(tenant_id, pack_id)` e exigem autenticacao valida (`X-API-Key` em acessos LAN/remotos ou cookie `HttpOnly` em `localhost`).

---

## 1. Simulacao What-If Zero-Token

### `POST /api/v1/simulate/recompute`

Recalcula um cenario What-If em Python puro via simulacao Monte Carlo, avalia regras duras (YAML + Memoria Institucional `active`) e retorna faixas `P10 / P50 / P90` e proveniencia.

#### Corpo da Requisicao (`SimulationRecomputeRequest`)

```json
{
  "tenant_id": "default",
  "pack_id": "retail_supermarket",
  "simulation_id": null,
  "scenario_type": "price_discount_change",
  "horizon_days": 30,
  "baseline": {
    "unit_price": 12.50,
    "unit_cost": 8.90,
    "daily_volume": 420.0,
    "volume_std_dev_pct": 5.0,
    "cost_std_dev_pct": 2.0,
    "elasticity_mean": -1.2,
    "elasticity_std_dev": 0.25,
    "receivable_days": 15.0,
    "payable_days": 30.0,
    "annual_capital_cost_pct": 10.75,
    "fixed_daily_cost": 450.0,
    "extra_metrics": {}
  },
  "shocks": {
    "price_delta_pct": 2.5,
    "discount_pct": 1.0,
    "supplier_cost_delta_pct": 0.0,
    "cost_passthrough_pct": 0.0,
    "receivable_days_delta": 0.0,
    "payable_days_delta": 0.0,
    "capital_cost_delta_pct": 0.0,
    "custom_shocks": {}
  },
  "iterations": 5000,
  "seed": 42,
  "persist_snapshot": false,
  "created_by": "operator"
}
```

#### Valores validos de enums
- `scenario_type`: `"price_discount_change"` | `"cost_supplier_variation"` | `"payment_term_cashflow"`
- `horizon_days`: `30` | `60` | `90`

#### Resposta (`200 OK` - `SimulationRecomputeResponse`)

```json
{
  "simulation_id": "sim_9a1b2c3d4e5f",
  "tenant_id": "default",
  "pack_id": "retail_supermarket",
  "scenario_type": "price_discount_change",
  "horizon_days": 30,
  "monte_carlo": {
    "p10": 8400.0,
    "p50": 14950.0,
    "p90": 22400.0,
    "mean": 15120.0,
    "std_dev": 3400.0,
    "prob_positive_pct": 94.0,
    "iterations": 5000,
    "seed": 42
  },
  "projected_metrics": {
    "projected_margin_pct": 29.4,
    "projected_daily_volume": 411.6
  },
  "sensitivity": [
    {
      "parameter": "price_delta_pct",
      "impact_brl": 9120.0,
      "impact_pct": 61.0,
      "direction": "positive"
    }
  ],
  "violated_rules": [],
  "is_compliant": true,
  "elapsed_ms": 14.2,
  "llm_calls": 0,
  "provenance": {
    "baseline_source": "erp_historical",
    "active_rules_count": 4,
    "yaml_rules_count": 2,
    "memory_rules_count": 2,
    "cited_documents": ["politica_comercial.pdf"]
  }
}
```

#### Codigos de erro
- `400 Bad Request`: baseline ausente ou parametros invalidos.
- `401 Unauthorized`: credencial ausente ou invalida.
- `404 Not Found`: `simulation_id` informado nao localizado para o `(tenant_id, pack_id)`.

---

## 2. Memoria Institucional e Governanca HiC

### `GET /api/v1/memory/suggestions`

Retorna o feed consolidado de governanca HiC sem chamadas LLM: regras com `status = "candidate"` e cards de simulacoes proativas gerados por recorrencia de intencoes.

#### Query Parameters
- `pack_id` (obrigatorio, string)
- `tenant_id` (opcional, padrao `"default"`)
- `window_days` (opcional, inteiro `1..90`, padrao `7`)
- `min_hits` (opcional, inteiro `1..50`, padrao `3`)

#### Resposta (`200 OK` - `MemoryGovernanceFeedResponse`)

```json
{
  "tenant_id": "default",
  "pack_id": "retail_supermarket",
  "candidate_rules": [
    {
      "rule_id": "rule_ab12cd34ef56",
      "tenant_id": "default",
      "pack_id": "retail_supermarket",
      "rule_key": "margin_pct_guard_ef56",
      "metric": "projected_margin_pct",
      "operator": ">=",
      "threshold_value": 18.0,
      "threshold_upper": null,
      "severity": "HIGH",
      "status": "candidate",
      "source": "business_memory",
      "origin": "chat_operator_correction",
      "author": "operator",
      "description": "Nunca operar abaixo de 18% de margem na Curva A."
    }
  ],
  "suggested_simulations": [
    {
      "card_id": "sug_01",
      "tenant_id": "default",
      "pack_id": "retail_supermarket",
      "topic_key": "margem_curva_a",
      "entity_type": "category",
      "metric_key": "projected_margin_pct",
      "hit_count": 5,
      "recommended_scenario": "price_discount_change",
      "suggested_shocks": {
        "price_delta_pct": 3.0,
        "discount_pct": 0.0,
        "supplier_cost_delta_pct": 0.0,
        "cost_passthrough_pct": 0.0,
        "receivable_days_delta": 0.0,
        "payable_days_delta": 0.0,
        "capital_cost_delta_pct": 0.0,
        "custom_shocks": {}
      },
      "title": "Revisao Preventiva de Margem",
      "reason": "5 consultas recorrentes nos ultimos 7 dias."
    }
  ],
  "pending_count": 2,
  "llm_calls": 0
}
```

---

### `GET /api/v1/memory/rules`

Lista regras persistidas da Memoria Institucional filtradas por `tenant_id`, `pack_id` e `status` opcional (`candidate`, `active`, `rejected`).

#### Query Parameters
- `pack_id` (obrigatorio, string)
- `tenant_id` (opcional, padrao `"default"`)
- `status` (opcional: `"candidate"` | `"active"` | `"rejected"`)

#### Resposta (`200 OK` - `MemoryRuleListResponse`)

```json
{
  "tenant_id": "default",
  "pack_id": "retail_supermarket",
  "total": 1,
  "rules": []
}
```

---

### `POST /api/v1/memory/rules/{rule_id}/decision`

Processa a decisao humana explicita (HiC) sobre uma regra `candidate` (incluindo propostas de calibracao geradas pelo backtesting), promovendo para `active` ou marcando como `rejected`.

#### Corpo da Requisicao (`RuleDecisionRequest`)

```json
{
  "tenant_id": "default",
  "pack_id": "retail_supermarket",
  "decision": "approve",
  "decided_by": "gerente_loja",
  "reason": "Politica validada com a diretoria"
}
```

- `decision`: `"approve"` | `"reject"`

#### Resposta (`200 OK` - `RuleDecisionResponse`)

```json
{
  "rule_id": "rule_ab12cd34ef56",
  "tenant_id": "default",
  "pack_id": "retail_supermarket",
  "previous_status": "candidate",
  "new_status": "active",
  "decided_by": "gerente_loja",
  "decided_at": "2026-11-27T12:00:00+00:00",
  "rule": {
    "rule_id": "rule_ab12cd34ef56",
    "tenant_id": "default",
    "pack_id": "retail_supermarket",
    "rule_key": "margin_pct_guard_ef56",
    "metric": "projected_margin_pct",
    "operator": ">=",
    "threshold_value": 18.0,
    "severity": "HIGH",
    "status": "active",
    "source": "business_memory",
    "origin": "chat_operator_correction",
    "author": "operator",
    "description": "Nunca operar abaixo de 18% de margem na Curva A."
  }
}
```

#### Codigos de erro
- `404 Not Found`: regra nao encontrada para o `(tenant_id, pack_id)`.
- `409 Conflict`: a regra ja saiu do estado `candidate` (decisao duplicada bloqueada).

---

## 3. Backtesting de ROI (Previsto vs. Realizado)

### `POST /api/v1/simulate/backtest/run`

Executa a auditoria deterministica de snapshots vencidos (`30/60/90d`) comparando as faixas previstas com o lucro realizado obtido via SQL Read-Only do ERP.

#### Corpo da Requisicao (`BacktestRunRequest`)

```json
{
  "tenant_id": "default",
  "pack_id": "retail_supermarket",
  "as_of": null,
  "limit": 50,
  "dry_run": false
}
```

---

### `GET /api/v1/simulate/backtest/scorecard`

Retorna o scorecard consolidado de acuracia (Previsto vs. Realizado), historico de itens auditados e eventual proposta pendente de calibracao HiC.

#### Query Parameters
- `pack_id` (obrigatorio, string)
- `tenant_id` (opcional, padrao `"default"`)
- `limit` (opcional, inteiro `1..200`, padrao `20`)

#### Resposta (`200 OK` - `RealizedRoiScorecardResponse`)

```json
{
  "tenant_id": "default",
  "pack_id": "retail_supermarket",
  "period_days": 90,
  "projected_brl": 42000.0,
  "realized_brl": 45800.0,
  "total_realized_brl": 45800.0,
  "hit_rate_pct": 86.0,
  "mean_abs_error_pct": 7.4,
  "roi_multiple": 4.2,
  "audited_actions_count": 7,
  "items": [
    {
      "simulation_id": "sim_01",
      "scenario_type": "price_discount_change",
      "horizon_days": 30,
      "created_at": "2026-10-01T10:00:00+00:00",
      "realized_at": "2026-11-01T10:00:00+00:00",
      "predicted_p10_brl": 11000.0,
      "predicted_p50_brl": 14500.0,
      "predicted_p90_brl": 18200.0,
      "realized_brl": 15400.0,
      "error_brl": 900.0,
      "error_pct": 6.2,
      "within_p10_p90": true
    }
  ],
  "pending_calibration": {
    "rule_id": "calib_rule_01",
    "tenant_id": "default",
    "pack_id": "retail_supermarket",
    "metric": "elasticity_calibration_factor",
    "current_factor": 1.0,
    "suggested_factor": 1.12,
    "mean_bias_pct": 11.3,
    "sample_size": 7,
    "status": "candidate",
    "reason": "Realizado superou consistentemente o P50 nos ultimos 60 dias."
  },
  "llm_calls": 0
}
```
