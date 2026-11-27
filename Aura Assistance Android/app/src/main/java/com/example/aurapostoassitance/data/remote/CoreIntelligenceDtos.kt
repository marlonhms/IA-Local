package com.example.aurapostoassitance.data.remote

import kotlinx.serialization.Serializable

/**
 * Contratos Kotlinx Serialization espelhando 1:1 os modelos Pydantic v2 de
 * `core/simulation/models.py` e `core/intelligence/models.py`.
 */

@Serializable
data class SimulationBaselineDto(
    val unit_price: Double,
    val unit_cost: Double,
    val daily_volume: Double,
    val volume_std_dev_pct: Double = 5.0,
    val cost_std_dev_pct: Double = 2.0,
    val elasticity_mean: Double = -1.2,
    val elasticity_std_dev: Double = 0.25,
    val receivable_days: Double = 15.0,
    val payable_days: Double = 30.0,
    val annual_capital_cost_pct: Double = 10.75,
    val fixed_daily_cost: Double = 0.0,
    val extra_metrics: Map<String, Double> = emptyMap()
)

@Serializable
data class ShockVectorDto(
    val price_delta_pct: Double = 0.0,
    val discount_pct: Double = 0.0,
    val supplier_cost_delta_pct: Double = 0.0,
    val cost_passthrough_pct: Double = 0.0,
    val receivable_days_delta: Double = 0.0,
    val payable_days_delta: Double = 0.0,
    val capital_cost_delta_pct: Double = 0.0,
    val custom_shocks: Map<String, Double> = emptyMap()
)

@Serializable
data class SimulationRecomputeRequestDto(
    val tenant_id: String = "default",
    val pack_id: String,
    val simulation_id: String? = null,
    val scenario_type: String,
    val horizon_days: Int = 30,
    val baseline: SimulationBaselineDto? = null,
    val shocks: ShockVectorDto = ShockVectorDto(),
    val iterations: Int = 5000,
    val seed: Int = 42,
    val persist_snapshot: Boolean = false,
    val created_by: String = "operator"
)

@Serializable
data class MonteCarloBandsDto(
    val p10: Double,
    val p50: Double,
    val p90: Double,
    val mean: Double,
    val std_dev: Double,
    val prob_positive_pct: Double,
    val iterations: Int,
    val seed: Int
)

@Serializable
data class SensitivityDriverDto(
    val parameter: String,
    val impact_brl: Double,
    val impact_pct: Double,
    val direction: String
)

@Serializable
data class RuleViolationDto(
    val rule_id: String,
    val source: String,
    val rule_key: String,
    val metric: String,
    val operator: String,
    val threshold: Double,
    val threshold_upper: Double? = null,
    val observed_value: Double,
    val severity: String,
    val message: String
)

@Serializable
data class SimulationProvenanceDto(
    val baseline_source: String = "erp_historical",
    val active_rules_count: Int = 0,
    val yaml_rules_count: Int = 0,
    val memory_rules_count: Int = 0,
    val cited_documents: List<String> = emptyList()
)

@Serializable
data class SimulationRecomputeResponseDto(
    val simulation_id: String,
    val tenant_id: String,
    val pack_id: String,
    val scenario_type: String,
    val horizon_days: Int,
    val monte_carlo: MonteCarloBandsDto,
    val projected_metrics: Map<String, Double> = emptyMap(),
    val sensitivity: List<SensitivityDriverDto> = emptyList(),
    val violated_rules: List<RuleViolationDto> = emptyList(),
    val is_compliant: Boolean,
    val elapsed_ms: Double,
    val llm_calls: Int = 0,
    val provenance: SimulationProvenanceDto = SimulationProvenanceDto()
)

@Serializable
data class BusinessRuleDto(
    val rule_id: String,
    val tenant_id: String,
    val pack_id: String,
    val rule_key: String,
    val metric: String,
    val operator: String,
    val threshold_value: Double,
    val threshold_upper: Double? = null,
    val severity: String = "HIGH",
    val status: String = "active",
    val source: String = "business_memory",
    val origin: String = "manual",
    val author: String = "system",
    val description: String = ""
)

@Serializable
data class MemoryRuleListResponseDto(
    val tenant_id: String,
    val pack_id: String,
    val total: Int,
    val rules: List<BusinessRuleDto> = emptyList()
)

@Serializable
data class SuggestedSimulationCardDto(
    val card_id: String,
    val tenant_id: String,
    val pack_id: String,
    val topic_key: String,
    val entity_type: String,
    val metric_key: String,
    val hit_count: Int,
    val recommended_scenario: String,
    val suggested_shocks: ShockVectorDto = ShockVectorDto(),
    val title: String,
    val reason: String
)

@Serializable
data class MemoryGovernanceFeedResponseDto(
    val tenant_id: String,
    val pack_id: String,
    val candidate_rules: List<BusinessRuleDto> = emptyList(),
    val suggested_simulations: List<SuggestedSimulationCardDto> = emptyList(),
    val pending_count: Int = 0,
    val llm_calls: Int = 0
)

@Serializable
data class RuleDecisionRequestDto(
    val tenant_id: String = "default",
    val pack_id: String,
    val decision: String,
    val decided_by: String = "operator",
    val reason: String = ""
)

@Serializable
data class RuleDecisionResponseDto(
    val rule_id: String,
    val tenant_id: String,
    val pack_id: String,
    val previous_status: String,
    val new_status: String,
    val decided_by: String,
    val decided_at: String,
    val rule: BusinessRuleDto
)

@Serializable
data class BacktestItemResultDto(
    val simulation_id: String,
    val scenario_type: String,
    val horizon_days: Int,
    val created_at: String? = null,
    val realized_at: String? = null,
    val predicted_p10_brl: Double,
    val predicted_p50_brl: Double,
    val predicted_p90_brl: Double,
    val realized_brl: Double,
    val error_brl: Double,
    val error_pct: Double,
    val within_p10_p90: Boolean
)

@Serializable
data class CalibrationProposalDto(
    val rule_id: String,
    val tenant_id: String,
    val pack_id: String,
    val metric: String = "elasticity_calibration_factor",
    val current_factor: Double = 1.0,
    val suggested_factor: Double,
    val mean_bias_pct: Double,
    val sample_size: Int,
    val status: String = "candidate",
    val reason: String
)

@Serializable
data class BacktestRunRequestDto(
    val tenant_id: String = "default",
    val pack_id: String,
    val as_of: String? = null,
    val limit: Int = 50,
    val dry_run: Boolean = false
)

@Serializable
data class BacktestRunResponseDto(
    val tenant_id: String,
    val pack_id: String,
    val evaluated_count: Int,
    val items: List<BacktestItemResultDto> = emptyList(),
    val calibration_proposal: CalibrationProposalDto? = null,
    val llm_calls: Int = 0
)

@Serializable
data class RealizedRoiScorecardResponseDto(
    val tenant_id: String,
    val pack_id: String,
    val period_days: Int = 90,
    val projected_brl: Double = 0.0,
    val realized_brl: Double = 0.0,
    val total_realized_brl: Double = 0.0,
    val hit_rate_pct: Double = 0.0,
    val mean_abs_error_pct: Double = 0.0,
    val roi_multiple: Double = 0.0,
    val audited_actions_count: Int = 0,
    val items: List<BacktestItemResultDto> = emptyList(),
    val pending_calibration: CalibrationProposalDto? = null,
    val llm_calls: Int = 0
)
