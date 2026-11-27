"""Router FastAPI para Governanca HiC da Memoria Institucional (Fase 2).

Expoe endpoints para listar regras (candidate/active/rejected) e aprovar ou
rejeitar candidatos explicitamente (POST /api/v1/memory/rules/{rule_id}/decision).
Protegido pela politica dual (HttpOnly localhost / X-API-Key ou Bearer LAN/Tailscale).
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

from contextlib import suppress
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from core.intelligence.intent_tracker import IntentTracker
from core.intelligence.memory_manager import MemoryManager
from core.intelligence.models import (
    MemoryGovernanceFeedResponse,
    MemoryRuleListResponse,
    RuleDecisionRequest,
    RuleDecisionResponse,
)
from core.simulation.models import BusinessRule, RuleStatus
from core.simulation.repository import SimulationRepository

logger = logging.getLogger("AuraMemoryAPI")

memory_router = APIRouter(
    prefix="/api/v1/memory",
    tags=["AURA Institutional Memory"],
)

_memory_manager_instance: MemoryManager | None = None


def get_memory_manager() -> MemoryManager:
    """Dependency Provider para o gerenciador de memoria institucional."""
    if _memory_manager_instance is not None:
        return _memory_manager_instance
    return MemoryManager(repository=SimulationRepository())


def set_memory_manager(manager: MemoryManager | None) -> None:
    """Permite injetar gerenciador customizado (ex: SQLite :memory: em testes)."""
    global _memory_manager_instance
    _memory_manager_instance = manager


def _verify_memory_auth(request: Request) -> bool:
    """Delega para verify_admin_auth evitando import circular com core.aura_api."""
    from core.aura_api import verify_admin_auth

    return verify_admin_auth(request)


@memory_router.get(
    "/rules",
    response_model=MemoryRuleListResponse,
    summary="Lista regras da memoria institucional filtradas por tenant_id, pack_id e status",
    dependencies=[Depends(_verify_memory_auth)],
)
async def list_memory_rules_endpoint(
    pack_id: str = Query(..., min_length=1),
    tenant_id: str = Query(default="default", min_length=1),
    status_filter: RuleStatus | None = Query(default=None, alias="status"),
    manager: MemoryManager = Depends(get_memory_manager),
) -> MemoryRuleListResponse:
    """Lista regras candidate, active ou rejected com isolamento estrito."""
    norm_pack = pack_id.strip().lower()
    try:
        rules = manager.list_rules(
            tenant_id=tenant_id,
            pack_id=norm_pack,
            status=status_filter,
        )
    except Exception as exc:  # noqa: BLE001
        with suppress(Exception):
            logger.warning("Regras da memoria institucional indisponiveis no momento: %s", exc)
        rules = []
    return MemoryRuleListResponse(
        tenant_id=tenant_id,
        pack_id=norm_pack,
        total=len(rules),
        rules=rules,
    )


@memory_router.get(
    "/suggestions",
    response_model=MemoryGovernanceFeedResponse,
    summary="Retorna regras candidate e simulacoes proativas pendentes de decisao HiC",
    dependencies=[Depends(_verify_memory_auth)],
)
async def get_memory_governance_feed_endpoint(
    pack_id: str = Query(..., min_length=1),
    tenant_id: str = Query(default="default", min_length=1),
    window_days: int = Query(default=7, ge=1, le=90),
    min_hits: int = Query(default=3, ge=1, le=50),
    manager: MemoryManager = Depends(get_memory_manager),
) -> MemoryGovernanceFeedResponse:
    """Alimenta o banner discreto HiC sem chamadas LLM."""
    norm_pack = pack_id.strip().lower()
    candidate_rules: list[BusinessRule] = []
    suggested_simulations = []

    try:
        candidate_rules = manager.list_rules(
            tenant_id=tenant_id,
            pack_id=norm_pack,
            status="candidate",
        )
    except Exception as exc:  # noqa: BLE001
        with suppress(Exception):
            logger.debug("Regras candidate indisponiveis no momento: %s", exc)

    try:
        tracker = IntentTracker(
            repository=manager._repo,
            recurrence_threshold=min_hits,
            window_days=window_days,
        )
        _, suggested_simulations = tracker.evaluate_recurrence(
            tenant_id=tenant_id,
            pack_id=norm_pack,
            window_days=window_days,
            min_hits=min_hits,
        )
    except Exception as exc:  # noqa: BLE001
        with suppress(Exception):
            logger.debug("Sugestoes de intencao indisponiveis no momento: %s", exc)

    return MemoryGovernanceFeedResponse(
        tenant_id=tenant_id,
        pack_id=norm_pack,
        candidate_rules=candidate_rules,
        suggested_simulations=suggested_simulations,
        pending_count=len(candidate_rules) + len(suggested_simulations),
        llm_calls=0,
    )


@memory_router.post(
    "/rules/{rule_id}/decision",
    response_model=RuleDecisionResponse,
    summary="Aprova ou rejeita explicitamente uma regra candidate (governanca HiC)",
    dependencies=[Depends(_verify_memory_auth)],
)
async def decide_memory_rule_endpoint(
    rule_id: str,
    payload: RuleDecisionRequest,
    manager: MemoryManager = Depends(get_memory_manager),
) -> RuleDecisionResponse:
    """Transiciona regra candidate para active (approve) ou rejected (reject)."""
    try:
        return manager.decide_rule(
            rule_id=rule_id,
            tenant_id=payload.tenant_id,
            pack_id=payload.pack_id,
            decision=payload.decision,
            decided_by=payload.decided_by,
            reason=payload.reason,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


__all__ = [
    "get_memory_manager",
    "memory_router",
    "set_memory_manager",
]
