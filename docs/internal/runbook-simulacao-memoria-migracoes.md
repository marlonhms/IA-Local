# Runbook Interno: Simulacao What-If, Memoria HiC, Backtesting e Migracoes (Fases 1 a 4B)

Este runbook documenta os modulos recem-implementados nas Fases 1 a 4B, o esquema de banco de dados e os procedimentos operacionais de validacao e diagnostico.

---

## 1. Mapa de Codigo (Fases 1 a 4B)

### Backend Python (`core/simulation/` e `core/intelligence/`)
- `core/simulation/models.py`: contratos Pydantic v2 (`SimulationBaseline`, `ShockVector`, `BusinessRule`, `RuleViolation`, `MonteCarloBands`, `SimulationRecomputeRequest/Response`, `BacktestItemResult`, `CalibrationProposal`, `RealizedRoiScorecardResponse`).
- `core/simulation/engine.py`: motor deterministico Monte Carlo (zero LLM).
- `core/simulation/rules_evaluator.py`: avaliacao binaria de regras YAML + `business_memory_rules` (`status='active'`).
- `core/simulation/repository.py`: persistencia isolada por `(tenant_id, pack_id)` com sanitizacao LGPD em `operator_intent_signals`.
- `core/simulation/backtest.py`: backtesting 30/60/90d com validacao SQL read-only via `sqlglot` (`build_readonly_realized_sql`).
- `core/simulation/api.py`: router `/api/v1/simulate/*` (`POST /recompute`, `POST /backtest/run`, `GET /backtest/scorecard`).
- `core/intelligence/models.py`: modelos de anomalias, alertas proativos, sugestoes e decisoes HiC.
- `core/intelligence/memory_manager.py`: extracao e governanca HiC (`candidate` -> `active` / `rejected`).
- `core/intelligence/intent_tracker.py`: tracking sanitizado de intencoes e geracao de `SuggestedSimulationCard`.
- `core/intelligence/profiler.py` e `core/intelligence/synthesizer.py`: deteccao Z-score/IQR e sintese opcional sob demanda.
- `core/intelligence/api.py`: router `/api/v1/memory/*` (`GET /rules`, `GET /suggestions`, `POST /rules/{rule_id}/decision`).

### Frontend Web (`web-frontend/`) e App Android (`Aura Assistance Android/`)
- `data/remote/CoreIntelligenceDtos.kt` e `AuraIntelligenceRepository.kt`: contratos Kotlinx Serialization e repositorio Fase 4A sincronizado com `DomainPackStateHolder`.
- `ui/intelligence/AuraIntelligenceUiState.kt` e `AuraIntelligenceViewModel.kt`: estado de UI e pipeline reativo com `Channel(Channel.CONFLATED)` + `debounce(180ms)` zero-token.
- `ui/genui/WhatIfSimulatorCard.kt`, `GovernanceHiCBanner.kt`, `RealizedRoiScorecardCard.kt`: micro-widgets nativos Obsidian Aurora com 3 `@Preview`s cada.
- `ui/genui/GenUiViews.kt`: `isTankTileAllowedForPack(packId)` garantindo `TankTile` apenas em `fuel_convenience`.

---

## 2. Banco de Dados e Migracoes (`0003_simulation_memory`)

- Revisao declarativa: `alembic/versions/0003_simulation_and_business_memory.py` (`0003_simulation_memory`).
- Tabelas gerenciadas:
  1. `business_profile_snapshots`
  2. `business_memory_rules`
  3. `operator_intent_signals`
  4. `simulation_snapshots`
- Bootstrap automatico no startup: `bootstrap_autonomous_brain_schema()` em `core/migrations.py` executa `ensure_autonomous_brain_schema()` e `ensure_simulation_memory_schema()` de forma idempotente no banco vetorial (`posto_ai`).

---

## 3. Validacao Automatizada

### Python (Core, Simulacao, Inteligencia e Migracoes)
```powershell
pytest tests/unit/test_simulation_engine.py tests/unit/test_business_intelligence.py tests/unit/test_simulation_backtest.py tests/unit/test_autonomous_brain.py tests/unit/test_alembic_migrations.py -v --tb=short
```

### Android (Jetpack Compose, ViewModel e Build Debug)
```powershell
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
.\gradlew.bat testDebugUnitTest assembleDebug --no-daemon
```

---

## 4. Troubleshooting Rapido

1. **HTTP 500 em `/api/v1/memory/rules` (`UndefinedTable: business_memory_rules`):**
   - Causa: banco `posto_ai` sem as tabelas da revisao `0003_simulation_memory`.
   - Correcao: executar `python -c "from core.migrations import bootstrap_autonomous_brain_schema; print(bootstrap_autonomous_brain_schema())"` com role dona do schema (`aura_brain_rw`) e garantir o codigo atualizado em `core/intelligence/api.py` (que devolve `200 OK` vazio em degradacao).
2. **Reinicio do Servico Windows (`AuraBackendService`):**
   - O servico roda via `bin\nssm.exe` com `uvicorn core.aura_api:app --host 0.0.0.0 --port 8000 --workers 2`.
   - Para aplicar alteracoes Python no servico em execucao, executar `automacoes/reiniciar_servico_aura.ps1` como Administrador.
3. **Scorecard ou Banner HiC vazios apos provisionamento inicial:**
   - Comportamento normal enquanto `simulation_snapshots` (com `persist_snapshot=true`), `business_memory_rules` (`status='candidate'`) e `operator_intent_signals` (`hit_count >= 3`) estiverem vazios.
