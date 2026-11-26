"""Router FastAPI Zero-LLM para recalculo What-If em tempo real (<100ms) (Fase 1).

Protegido pela mesma politica dual de autenticacao (HttpOnly localhost /
X-API-Key ou Bearer LAN/Tailscale). Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import logging
from contextlib import suppress

from fastapi import APIRouter, Depends, HTTPException, Request, status

from core.simulation.engine import SimulationEngine
from core.simulation.models import (
    BusinessRule,
    SimulationRecomputeRequest,
    SimulationRecomputeResponse,
)
from core.simulation.repository import SimulationRepository

logger = logging.getLogger("AuraSimulationAPI")

simulation_router = APIRouter(
    prefix="/api/v1/simulate",
    tags=["AURA What-If Simulation"],
)

_engine_singleton = SimulationEngine()
_repository_instance: SimulationRepository | None = None


def get_simulation_repository() -> SimulationRepository:
    """Dependency Provider para o repositorio de simulacao."""
    if _repository_instance is not None:
        return _repository_instance
    return SimulationRepository()


def set_simulation_repository(repo: SimulationRepository | None) -> None:
    """Permite injetar repositorio customizado (ex: SQLite :memory: em testes)."""
    global _repository_instance
    _repository_instance = repo


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


__all__ = [
    "get_simulation_repository",
    "set_simulation_repository",
    "simulation_router",
]
