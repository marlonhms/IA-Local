"""Modelos Pydantic v2 para o Motor Deterministico What-If e Memoria do Negocio (Fase 1).

Zero dependencias externas alem de Pydantic e stdlib. Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ScenarioType = Literal[
    "price_discount_change",
    "cost_supplier_variation",
    "payment_term_cashflow",
]
HorizonDays = Literal[30, 60, 90]
RuleOperator = Literal[">=", "<=", ">", "<", "==", "!=", "between"]
RuleStatus = Literal["candidate", "active", "rejected"]
RuleSeverity = Literal["CRITICAL", "HIGH", "MEDIUM", "INFO"]
RuleSource = Literal["yaml", "business_memory"]


class SimulationBaseline(BaseModel):
    """Estado base T0 da operacao, agnostico de dominio."""

    model_config = ConfigDict(extra="ignore")

    unit_price: float = Field(gt=0, description="Preco unitario medio atual (R$)")
    unit_cost: float = Field(ge=0, description="Custo unitario medio atual (R$)")
    daily_volume: float = Field(gt=0, description="Volume diario medio baseline")
    volume_std_dev_pct: float = Field(default=5.0, ge=0, description="Desvio padrao percentual do volume diario")
    cost_std_dev_pct: float = Field(default=2.0, ge=0, description="Desvio padrao percentual do custo unitario")
    elasticity_mean: float = Field(default=-1.2, description="Elasticidade-preco media esperada")
    elasticity_std_dev: float = Field(default=0.25, ge=0, description="Desvio padrao da elasticidade")
    receivable_days: float = Field(default=15.0, ge=0, description="Prazo medio de recebimento (dias)")
    payable_days: float = Field(default=30.0, ge=0, description="Prazo medio de pagamento a fornecedores (dias)")
    annual_capital_cost_pct: float = Field(default=10.75, ge=0, description="Custo anual de capital (% a.a.)")
    fixed_daily_cost: float = Field(default=0.0, ge=0, description="Custo fixo diario alocado (R$)")
    extra_metrics: dict[str, float] = Field(
        default_factory=dict,
        description="Metricas numericas adicionais especificas do tenant/dominio",
    )


class ShockVector(BaseModel):
    """Vetor de parametros de choque ajustados interativamente pelo operador."""

    model_config = ConfigDict(extra="ignore")

    price_delta_pct: float = Field(default=0.0, description="Variacao percentual no preco de venda")
    discount_pct: float = Field(default=0.0, ge=0.0, le=99.9, description="Desconto promocional percentual")
    supplier_cost_delta_pct: float = Field(default=0.0, description="Variacao percentual no custo do fornecedor")
    cost_passthrough_pct: float = Field(
        default=0.0,
        ge=0.0,
        le=200.0,
        description="Percentual do choque de custo repassado ao preco final",
    )
    receivable_days_delta: float = Field(default=0.0, description="Variacao em dias no prazo de recebimento")
    payable_days_delta: float = Field(default=0.0, description="Variacao em dias no prazo de pagamento")
    capital_cost_delta_pct: float = Field(default=0.0, description="Variacao em pontos percentuais no custo de capital")
    custom_shocks: dict[str, float] = Field(
        default_factory=dict,
        description="Parametros extras de choque especificos de adaptadores de dominio",
    )


class BusinessRule(BaseModel):
    """Regra dura estruturada para avaliacao binaria em simulacoes."""

    model_config = ConfigDict(extra="ignore")

    rule_id: str
    tenant_id: str
    pack_id: str
    rule_key: str
    metric: str
    operator: RuleOperator
    threshold_value: float
    threshold_upper: float | None = None
    severity: RuleSeverity = "HIGH"
    status: RuleStatus = "active"
    source: RuleSource = "business_memory"
    origin: str = "manual"
    author: str = "system"
    description: str = ""


class RuleViolation(BaseModel):
    """Violacao binaria detectada pelo RulesEvaluator."""

    rule_id: str
    source: RuleSource
    rule_key: str
    metric: str
    operator: RuleOperator
    threshold: float
    threshold_upper: float | None = None
    observed_value: float
    severity: RuleSeverity
    message: str


class SensitivityDriver(BaseModel):
    """Impacto marginal de um parametro de choque sobre o P50."""

    parameter: str
    impact_brl: float
    impact_pct: float
    direction: Literal["positive", "negative", "neutral"]


class MonteCarloBands(BaseModel):
    """Bandas estatisticas da simulacao Monte Carlo."""

    p10: float
    p50: float
    p90: float
    mean: float
    std_dev: float
    prob_positive_pct: float
    iterations: int
    seed: int


class SimulationRecomputeRequest(BaseModel):
    """Payload de entrada para recalculo deterministico Zero-LLM."""

    model_config = ConfigDict(extra="ignore")

    tenant_id: str = Field(default="default", min_length=1)
    pack_id: str = Field(min_length=1)
    simulation_id: str | None = None
    scenario_type: ScenarioType
    horizon_days: HorizonDays = 30
    baseline: SimulationBaseline | None = None
    shocks: ShockVector = Field(default_factory=ShockVector)
    iterations: int = Field(default=5000, ge=100, le=50000)
    seed: int = 42
    persist_snapshot: bool = False
    created_by: str = "operator"


class SimulationProvenance(BaseModel):
    """Metadados de proveniencia deterministica da simulacao What-If."""

    model_config = ConfigDict(extra="ignore")

    baseline_source: str = "erp_historical"
    active_rules_count: int = 0
    yaml_rules_count: int = 0
    memory_rules_count: int = 0
    cited_documents: list[str] = Field(default_factory=list)


class SimulationRecomputeResponse(BaseModel):
    """Resposta JSON estruturada do endpoint /api/v1/simulate/recompute."""

    simulation_id: str
    tenant_id: str
    pack_id: str
    scenario_type: ScenarioType
    horizon_days: HorizonDays
    monte_carlo: MonteCarloBands
    projected_metrics: dict[str, float]
    sensitivity: list[SensitivityDriver]
    violated_rules: list[RuleViolation]
    is_compliant: bool
    elapsed_ms: float
    llm_calls: int = 0
    provenance: SimulationProvenance = Field(default_factory=SimulationProvenance)


class BacktestItemResult(BaseModel):
    """Comparacao deterministica entre snapshot vencido (30/60/90d) e resultado realizado."""

    model_config = ConfigDict(extra="ignore")

    simulation_id: str
    scenario_type: ScenarioType
    horizon_days: HorizonDays
    created_at: str | None = None
    realized_at: str | None = None
    predicted_p10_brl: float
    predicted_p50_brl: float
    predicted_p90_brl: float
    realized_brl: float
    error_brl: float
    error_pct: float
    within_p10_p90: bool


class CalibrationProposal(BaseModel):
    """Sugestao de auto-calibracao de elasticidade sujeita a aprovacao HiC."""

    model_config = ConfigDict(extra="ignore")

    rule_id: str
    tenant_id: str
    pack_id: str
    metric: str = "elasticity_calibration_factor"
    current_factor: float = 1.0
    suggested_factor: float
    mean_bias_pct: float
    sample_size: int
    status: RuleStatus = "candidate"
    reason: str


class BacktestRunRequest(BaseModel):
    """Payload de entrada para execucao deterministica de backtesting (30/60/90d)."""

    model_config = ConfigDict(extra="ignore")

    tenant_id: str = Field(default="default", min_length=1)
    pack_id: str = Field(min_length=1)
    as_of: str | None = None
    limit: int = Field(default=50, ge=1, le=500)
    dry_run: bool = False


class BacktestRunResponse(BaseModel):
    """Resposta JSON da execucao de backtesting e calibracao sugerida."""

    tenant_id: str
    pack_id: str
    evaluated_count: int
    items: list[BacktestItemResult] = Field(default_factory=list)
    calibration_proposal: CalibrationProposal | None = None
    llm_calls: int = 0


class RealizedRoiScorecardResponse(BaseModel):
    """Scorecard consolidado Previsto vs. Realizado para o RealizedRoiScorecardUI."""

    tenant_id: str
    pack_id: str
    period_days: int = 90
    projected_brl: float = 0.0
    realized_brl: float = 0.0
    total_realized_brl: float = 0.0
    hit_rate_pct: float = 0.0
    mean_abs_error_pct: float = 0.0
    roi_multiple: float = 0.0
    audited_actions_count: int = 0
    items: list[BacktestItemResult] = Field(default_factory=list)
    pending_calibration: CalibrationProposal | None = None
    llm_calls: int = 0


class BusinessProfileSnapshotRecord(BaseModel):
    """Snapshot estatistico historico da operacao."""

    snapshot_id: str
    tenant_id: str
    pack_id: str
    reference_period: str
    means: dict[str, float]
    std_devs: dict[str, float]
    seasonality: dict[str, Any] = Field(default_factory=dict)
    abc_curve: dict[str, Any] = Field(default_factory=dict)
    sample_size: int = 0


__all__ = [
    "BacktestItemResult",
    "BacktestRunRequest",
    "BacktestRunResponse",
    "BusinessProfileSnapshotRecord",
    "BusinessRule",
    "CalibrationProposal",
    "HorizonDays",
    "MonteCarloBands",
    "RealizedRoiScorecardResponse",
    "RuleOperator",
    "RuleSeverity",
    "RuleSource",
    "RuleStatus",
    "RuleViolation",
    "ScenarioType",
    "SensitivityDriver",
    "ShockVector",
    "SimulationBaseline",
    "SimulationProvenance",
    "SimulationRecomputeRequest",
    "SimulationRecomputeResponse",
]
