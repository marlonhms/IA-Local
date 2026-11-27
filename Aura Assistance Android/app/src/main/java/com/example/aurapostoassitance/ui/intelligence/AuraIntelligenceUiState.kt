package com.example.aurapostoassitance.ui.intelligence

import com.example.aurapostoassitance.data.remote.BacktestItemResultDto
import com.example.aurapostoassitance.data.remote.BusinessRuleDto
import com.example.aurapostoassitance.data.remote.RealizedRoiScorecardResponseDto
import com.example.aurapostoassitance.data.remote.ShockVectorDto
import com.example.aurapostoassitance.data.remote.SimulationBaselineDto
import com.example.aurapostoassitance.data.remote.SimulationProvenanceDto
import com.example.aurapostoassitance.data.remote.SimulationRecomputeResponseDto
import com.example.aurapostoassitance.data.remote.SuggestedSimulationCardDto
import com.example.aurapostoassitance.ui.domain.AuraDomainAdapter
import java.text.NumberFormat
import java.util.Locale
import kotlin.math.abs

data class WhatIfUiState(
    val packId: String = AuraDomainAdapter.PACK_FUEL,
    val scenarioType: String = "price_elasticity",
    val title: String = "Simulador What-If",
    val subtitle: String? = null,
    val horizonDays: Int = 30,
    val shocks: ShockVectorDto = ShockVectorDto(),
    val baseline: SimulationBaselineDto? = null,
    val response: SimulationRecomputeResponseDto? = null,
    val isLoading: Boolean = false,
    val errorMessage: String? = null
) {
    val hasViolations: Boolean
        get() = response?.violated_rules?.isNotEmpty() == true
}

data class GovernanceHiCUiState(
    val packId: String = AuraDomainAdapter.PACK_FUEL,
    val candidateRules: List<BusinessRuleDto> = emptyList(),
    val suggestedSimulations: List<SuggestedSimulationCardDto> = emptyList(),
    val pendingRuleDecisions: Set<String> = emptySet(),
    val resolvedDecisions: Map<String, String> = emptyMap(),
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
    val isExpanded: Boolean = true
) {
    val totalPendingCount: Int
        get() = candidateRules.count { it.rule_id !in resolvedDecisions } + suggestedSimulations.size

    val hasContent: Boolean
        get() = isLoading || candidateRules.isNotEmpty() || suggestedSimulations.isNotEmpty() || errorMessage != null
}

data class BacktestScorecardUiState(
    val packId: String = AuraDomainAdapter.PACK_FUEL,
    val selectedHorizonDays: Int = 90,
    val scorecard: RealizedRoiScorecardResponseDto? = null,
    val calibrationDecisionInFlight: Boolean = false,
    val calibrationResolution: String? = null,
    val isLoading: Boolean = false,
    val errorMessage: String? = null
) {
    val filteredItems: List<BacktestItemResultDto>
        get() {
            val all = scorecard?.items.orEmpty()
            if (all.isEmpty()) return emptyList()
            val withinHorizon = all.filter { it.horizon_days <= selectedHorizonDays }
            return withinHorizon.ifEmpty { all }
        }
}

object AuraIntelligenceFormatters {

    private val ptBr = Locale("pt", "BR")

    fun formatBrl(value: Double, signed: Boolean = false): String {
        val formatter = NumberFormat.getIntegerInstance(ptBr)
        val formatted = formatter.format(abs(value))
        return when {
            value < 0.0 -> "-R$ $formatted"
            signed && value > 0.0 -> "+R$ $formatted"
            else -> "R$ $formatted"
        }
    }

    fun formatPct(value: Double, signed: Boolean = true, decimals: Int = 1): String {
        val pattern = if (signed) "%+.${decimals}f%%" else "%.${decimals}f%%"
        return pattern.format(ptBr, value)
    }

    fun formatRuleExpression(
        metric: String,
        operator: String,
        threshold: Double,
        upper: Double? = null
    ): String {
        val metricLabel = metric.replace("_", " ").trim()
        val thresholdFmt = "%.2f".format(ptBr, threshold)
        return if (upper != null) {
            val upperFmt = "%.2f".format(ptBr, upper)
            "$metricLabel $operator [$thresholdFmt .. $upperFmt]"
        } else {
            "$metricLabel $operator $thresholdFmt"
        }
    }

    fun formatProvenanceLine(provenance: SimulationProvenanceDto): String {
        val sourceLabel = when (provenance.baseline_source.lowercase()) {
            "erp_historical" -> "Base ERP histórica"
            "manual_baseline" -> "Base informada"
            "snapshot" -> "Snapshot auditado"
            else -> provenance.baseline_source.replace("_", " ")
        }
        val rulesBreakdown = buildString {
            append("${provenance.active_rules_count} regras ativas")
            if (provenance.yaml_rules_count > 0 || provenance.memory_rules_count > 0) {
                append(" (${provenance.yaml_rules_count} YAML + ${provenance.memory_rules_count} Memória)")
            }
        }
        val docsPart = if (provenance.cited_documents.isEmpty()) {
            "0 docs citados"
        } else {
            val preview = provenance.cited_documents.take(2).joinToString(", ")
            val suffix = if (provenance.cited_documents.size > 2) " +${provenance.cited_documents.size - 2}" else ""
            "Docs: $preview$suffix"
        }
        return "$sourceLabel • $rulesBreakdown • $docsPart"
    }

    fun friendlyScenarioName(scenarioType: String): String = when (scenarioType.lowercase()) {
        "price_elasticity" -> "Elasticidade de Preço"
        "margin_protection" -> "Proteção de Margem"
        "working_capital" -> "Capital de Giro"
        "promo_discount" -> "Campanha de Desconto"
        "supplier_passthrough" -> "Repasse de Custo"
        else -> scenarioType.replace("_", " ").replaceFirstChar { it.uppercase() }
    }

    fun buildWhatIfAuditPrompt(state: WhatIfUiState): String {
        val shocksSummary = buildList {
            if (state.shocks.price_delta_pct != 0.0) {
                add("preço ${formatPct(state.shocks.price_delta_pct)}")
            }
            if (state.shocks.discount_pct != 0.0) {
                add("desconto ${formatPct(state.shocks.discount_pct, signed = false)}")
            }
            if (state.shocks.supplier_cost_delta_pct != 0.0) {
                add("custo fornecedor ${formatPct(state.shocks.supplier_cost_delta_pct)}")
            }
            if (state.shocks.cost_passthrough_pct != 0.0) {
                add("repasse de custo ${formatPct(state.shocks.cost_passthrough_pct, signed = false)}")
            }
        }.ifEmpty { listOf("sem choques aplicados (cenário base)") }.joinToString(", ")

        val bandsSummary = state.response?.monte_carlo?.let { mc ->
            "Faixas Monte Carlo (${state.horizonDays}d): P10 ${formatBrl(mc.p10, signed = true)}, " +
                "P50 ${formatBrl(mc.p50, signed = true)}, P90 ${formatBrl(mc.p90, signed = true)} " +
                "(prob. positiva ${"%.0f".format(mc.prob_positive_pct)}%)."
        } ?: "Horizonte: ${state.horizonDays} dias."

        val violationsSummary = state.response?.violated_rules?.takeIf { it.isNotEmpty() }?.let { rules ->
            " Regras violadas: " + rules.joinToString("; ") { "${it.rule_key} (${it.message})" } + "."
        }.orEmpty()

        return "Audite este cenário What-If no pack '${state.packId}' (${friendlyScenarioName(state.scenarioType)}): " +
            "ajustes [$shocksSummary]. $bandsSummary$violationsSummary " +
            "Quais riscos, oportunidades e plano de execução você recomenda?"
    }
}
