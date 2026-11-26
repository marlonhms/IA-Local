"""Modelos Pydantic v2 para Inteligencia Proativa, Telemetria e Memoria HiC (Fase 2).

Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from core.simulation.models import (
    BusinessRule,
    RuleStatus,
    ScenarioType,
    ShockVector,
    SimulationRecomputeResponse,
)

AnomalyMetric = Literal["margin_pct", "daily_volume", "unit_cost", "net_cashflow_brl"]
AnomalyMethod = Literal["z_score", "iqr", "both"]
AnomalySeverity = Literal["CRITICAL", "HIGH", "MEDIUM"]
AnomalyDirection = Literal["drop", "spike"]
RuleDecisionAction = Literal["approve", "reject"]


class MetricSeriesPoint(BaseModel):
    """Ponto temporal agregado do ERP para calculo estatistico deterministico."""

    model_config = ConfigDict(extra="ignore")

    ref_date: str
    margin_pct: float | None = None
    daily_volume: float | None = None
    unit_cost: float | None = None
    unit_price: float | None = None
    net_cashflow_brl: float | None = None
    receivable_days: float = Field(default=15.0, ge=0.0)
    payable_days: float = Field(default=30.0, ge=0.0)
    fixed_daily_cost: float = Field(default=0.0, ge=0.0)


class AnomalyFinding(BaseModel):
    """Desvio estatistico detectado por Z-score ou IQR em Python deterministico."""

    model_config = ConfigDict(extra="ignore")

    metric: AnomalyMetric
    observed_value: float
    baseline_mean: float
    baseline_std_dev: float
    z_score: float
    iqr_lower: float
    iqr_upper: float
    method: AnomalyMethod
    severity: AnomalySeverity
    direction: AnomalyDirection
    is_priority_monitored: bool = False


class ProactiveAlert(BaseModel):
    """Alerta proativo estruturado contendo rascunho de simulacao e sintese opcional."""

    model_config = ConfigDict(extra="ignore")

    alert_id: str
    tenant_id: str
    pack_id: str
    snapshot_id: str
    anomalies: list[AnomalyFinding]
    draft_simulation: SimulationRecomputeResponse
    second_order_synthesis: str | None = None
    rag_references: list[str] = Field(default_factory=list)
    llm_calls: int = 0
    created_at: str


class OperatorIntentRecord(BaseModel):
    """Sinal sanitizado de intencao do operador persistido em operator_intent_signals."""

    model_config = ConfigDict(extra="ignore")

    signal_id: str
    tenant_id: str
    pack_id: str
    entity_type: str
    metric_key: str
    topic_key: str
    intent_name: str
    hit_count: int = 1
    last_seen_at: str | None = None


class PromotedMonitorTarget(BaseModel):
    """Topico/metrica promovido a monitoramento prioritario por recorrencia."""

    model_config = ConfigDict(extra="ignore")

    tenant_id: str
    pack_id: str
    entity_type: str
    metric_key: str
    topic_key: str
    hit_count: int


class SuggestedSimulationCard(BaseModel):
    """Card proativo de simulacao pronta sugerido ao operador por recorrencia."""

    model_config = ConfigDict(extra="ignore")

    card_id: str
    tenant_id: str
    pack_id: str
    topic_key: str
    entity_type: str
    metric_key: str
    hit_count: int
    recommended_scenario: ScenarioType
    suggested_shocks: ShockVector
    title: str
    reason: str


class MemoryRuleListResponse(BaseModel):
    """Resposta JSON da listagem de regras de memoria institucional."""

    tenant_id: str
    pack_id: str
    total: int
    rules: list[BusinessRule]


class RuleDecisionRequest(BaseModel):
    """Payload HiC para aprovar ou rejeitar regra candidate."""

    model_config = ConfigDict(extra="ignore")

    tenant_id: str = Field(default="default", min_length=1)
    pack_id: str = Field(min_length=1)
    decision: RuleDecisionAction
    decided_by: str = Field(default="operator", min_length=1)
    reason: str = Field(default="")


class RuleDecisionResponse(BaseModel):
    """Resposta JSON da decisao HiC sobre regra de memoria institucional."""

    rule_id: str
    tenant_id: str
    pack_id: str
    previous_status: RuleStatus
    new_status: RuleStatus
    decided_by: str
    decided_at: str
    rule: BusinessRule


__all__ = [
    "AnomalyDirection",
    "AnomalyFinding",
    "AnomalyMethod",
    "AnomalyMetric",
    "AnomalySeverity",
    "MemoryRuleListResponse",
    "MetricSeriesPoint",
    "OperatorIntentRecord",
    "ProactiveAlert",
    "PromotedMonitorTarget",
    "RuleDecisionAction",
    "RuleDecisionRequest",
    "RuleDecisionResponse",
    "SuggestedSimulationCard",
]
