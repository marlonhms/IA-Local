"""Router FastAPI Zero-LLM para recalculo What-If em tempo real (<100ms) (Fase 1).

Protegido pela mesma politica dual de autenticacao (HttpOnly localhost /
X-API-Key ou Bearer LAN/Tailscale). Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import logging
from contextlib import suppress
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from core.simulation.backtest import SimulationBacktester
from core.simulation.engine import SimulationEngine
from core.simulation.models import (
    BacktestRunRequest,
    BacktestRunResponse,
    BusinessRule,
    RealizedRoiScorecardResponse,
    SimulationRecomputeRequest,
    SimulationRecomputeResponse,
)
from core.simulation.repository import SimulationRepository, _parse_utc_timestamp

logger = logging.getLogger("AuraSimulationAPI")

simulation_router = APIRouter(
    prefix="/api/v1/simulate",
    tags=["AURA What-If Simulation"],
)

_engine_singleton = SimulationEngine()
_repository_instance: SimulationRepository | None = None
_backtester_instance: SimulationBacktester | None = None


def get_simulation_repository() -> SimulationRepository:
    """Dependency Provider para o repositorio de simulacao."""
    if _repository_instance is not None:
        return _repository_instance
    return SimulationRepository()


def set_simulation_repository(repo: SimulationRepository | None) -> None:
    """Permite injetar repositorio customizado (ex: SQLite :memory: em testes)."""
    global _repository_instance
    _repository_instance = repo


def get_simulation_backtester(
    repo: SimulationRepository = Depends(get_simulation_repository),
) -> SimulationBacktester:
    """Dependency Provider para o motor deterministico de backtesting."""
    if _backtester_instance is not None:
        return _backtester_instance
    return SimulationBacktester(repository=repo)


def set_simulation_backtester(backtester: SimulationBacktester | None) -> None:
    """Permite injetar SimulationBacktester customizado em testes."""
    global _backtester_instance
    _backtester_instance = backtester


def _verify_simulation_auth(request: Request) -> bool:
    """Delega para verify_admin_auth evitando import circular com core.aura_api."""
    from core.aura_api import verify_admin_auth

    return verify_admin_auth(request)


@simulation_router.post(
    "/recompute",
    response_model=SimulationRecomputeResponse,
    summary="Recalcula simulacao What-If em Python puro (Zero-LLM, <100ms)",
    dependencies=[Depends(_verify_simulation_auth)],
)
async def recompute_simulation_endpoint(
    payload: SimulationRecomputeRequest,
    repo: SimulationRepository = Depends(get_simulation_repository),
) -> SimulationRecomputeResponse:
    """Recebe vetor de choque ajustado + baseline/simulation_id e retorna P10/P50/P90 e regras."""
    try:
        memory_rules: list[BusinessRule] | None = None
        active_repo: SimulationRepository | None = repo

        if repo._external_conn is None and payload.baseline is not None and not payload.persist_snapshot:
            try:
                memory_rules = repo.list_business_rules(
                    tenant_id=payload.tenant_id,
                    pack_id=payload.pack_id,
                    status="active",
                )
            except Exception as exc:  # noqa: BLE001
                with suppress(Exception):
                    logger.debug(
                        "Repositorio Postgres indisponivel durante recompute efemero; usando apenas regras YAML: %s",
                        exc,
                    )
                memory_rules = []
                active_repo = None

        return _engine_singleton.run_simulation(
            request=payload,
            repository=active_repo,
            memory_rules=memory_rules,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@simulation_router.post(
    "/backtest/run",
    response_model=BacktestRunResponse,
    summary="Executa backtesting deterministico (30/60/90d) e sugere calibracao HiC",
    dependencies=[Depends(_verify_simulation_auth)],
)
async def run_simulation_backtest_endpoint(
    payload: BacktestRunRequest,
    backtester: SimulationBacktester = Depends(get_simulation_backtester),
) -> BacktestRunResponse:
    """Compara snapshots vencidos com valores realizados via SQL read-only e propoe ajuste."""
    as_of_dt: datetime | None = None
    if payload.as_of:
        as_of_dt = _parse_utc_timestamp(payload.as_of)
        if as_of_dt is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parametro 'as_of' invalido; use formato ISO-8601 UTC.",
            )
    try:
        return backtester.run_backtest(
            tenant_id=payload.tenant_id,
            pack_id=payload.pack_id,
            as_of=as_of_dt,
            limit=payload.limit,
            dry_run=payload.dry_run,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@simulation_router.get(
    "/backtest/scorecard",
    response_model=RealizedRoiScorecardResponse,
    summary="Retorna scorecard Previsto vs. Realizado e calibracao pendente HiC",
    dependencies=[Depends(_verify_simulation_auth)],
)
async def get_backtest_scorecard_endpoint(
    pack_id: str = Query(..., min_length=1),
    tenant_id: str = Query(default="default", min_length=1),
    limit: int = Query(default=20, ge=1, le=200),
    backtester: SimulationBacktester = Depends(get_simulation_backtester),
) -> RealizedRoiScorecardResponse:
    """Alimenta o RealizedRoiScorecardUI sem consumir tokens LLM."""
    try:
        return backtester.build_scorecard(
            tenant_id=tenant_id,
            pack_id=pack_id,
            limit=limit,
        )
    except Exception as exc:  # noqa: BLE001
        with suppress(Exception):
            logger.debug("Scorecard fallback vazio por indisponibilidade de banco: %s", exc)
        return RealizedRoiScorecardResponse(
            tenant_id=tenant_id,
            pack_id=pack_id.strip().lower(),
        )


__all__ = [
    "get_simulation_backtester",
    "get_simulation_repository",
    "set_simulation_backtester",
    "set_simulation_repository",
    "simulation_router",
]
