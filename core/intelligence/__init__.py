"""Pacote de Inteligencia Proativa, Telemetria de Intencao e Memoria HiC (Fase 2).

Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

from core.intelligence.api import (
    get_memory_manager,
    memory_router,
    set_memory_manager,
)
from core.intelligence.intent_tracker import IntentTracker
from core.intelligence.memory_manager import MemoryManager
from core.intelligence.models import (
    AnomalyFinding,
    MemoryRuleListResponse,
    MetricSeriesPoint,
    OperatorIntentRecord,
    ProactiveAlert,
    PromotedMonitorTarget,
    RuleDecisionRequest,
    RuleDecisionResponse,
    SuggestedSimulationCard,
)
from core.intelligence.profiler import (
    FUEL_CONVENIENCE_SQL_TEMPLATES,
    BusinessProfiler,
    execute_readonly_query,
    register_pack_query_provider,
    validate_profiler_sql,
)
from core.intelligence.synthesizer import SecondOrderSynthesizer

__all__ = [
    "AnomalyFinding",
    "BusinessProfiler",
    "FUEL_CONVENIENCE_SQL_TEMPLATES",
    "IntentTracker",
    "MemoryManager",
    "MemoryRuleListResponse",
    "MetricSeriesPoint",
    "OperatorIntentRecord",
    "ProactiveAlert",
    "PromotedMonitorTarget",
    "RuleDecisionRequest",
    "RuleDecisionResponse",
    "SecondOrderSynthesizer",
    "SuggestedSimulationCard",
    "execute_readonly_query",
    "get_memory_manager",
    "memory_router",
    "register_pack_query_provider",
    "set_memory_manager",
    "validate_profiler_sql",
]
