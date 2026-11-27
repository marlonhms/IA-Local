package com.example.aurapostoassitance.ui.genui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material.icons.rounded.Tune
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.aurapostoassitance.data.remote.BusinessRuleDto
import com.example.aurapostoassitance.data.remote.ShockVectorDto
import com.example.aurapostoassitance.data.remote.SuggestedSimulationCardDto
import com.example.aurapostoassitance.ui.components.AuraCard
import com.example.aurapostoassitance.ui.components.AuraPill
import com.example.aurapostoassitance.ui.components.ShimmerBox
import com.example.aurapostoassitance.ui.components.StatusDot
import com.example.aurapostoassitance.ui.intelligence.AuraIntelligenceFormatters
import com.example.aurapostoassitance.ui.intelligence.GovernanceHiCUiState
import com.example.aurapostoassitance.ui.theme.AuraCyan
import com.example.aurapostoassitance.ui.theme.AuraEmerald
import com.example.aurapostoassitance.ui.theme.AuraPostoAssitanceTheme
import com.example.aurapostoassitance.ui.theme.AuraPurple
import com.example.aurapostoassitance.ui.theme.AuraTypographyExt
import com.example.aurapostoassitance.ui.theme.BorderHairline
import com.example.aurapostoassitance.ui.theme.GlassBorderSoft
import com.example.aurapostoassitance.ui.theme.ObsidianBase
import com.example.aurapostoassitance.ui.theme.ObsidianLow
import com.example.aurapostoassitance.ui.theme.StatusDanger
import com.example.aurapostoassitance.ui.theme.StatusWarning
import com.example.aurapostoassitance.ui.theme.TextMuted
import com.example.aurapostoassitance.ui.theme.TextPrimary
import com.example.aurapostoassitance.ui.theme.TextSecondary

/**
 * Banner/card compacto e não intrusivo para governança Human-in-Command (HiC):
 * - Sugestões proativas geradas pelo profiler (abrem o simulador zero-token)
 * - Regras candidatas (`status = candidate`) com aprovação/rejeição imediata
 */
@Composable
fun GovernanceHiCBanner(
    state: GovernanceHiCUiState,
    onToggleExpanded: () -> Unit,
    onApproveRule: (String) -> Unit,
    onRejectRule: (String) -> Unit,
    onSimulateSuggestion: (SuggestedSimulationCardDto) -> Unit,
    modifier: Modifier = Modifier
) {
    if (!state.hasContent) return

    val hasCriticalRule = state.candidateRules.any {
        it.rule_id !in state.resolvedDecisions &&
            (it.severity.equals("CRITICAL", true) || it.severity.equals("HIGH", true))
    }
    val accent = if (hasCriticalRule) StatusWarning else AuraCyan

    AuraCard(
        modifier = modifier.fillMaxWidth(),
        accent = accent,
        glowActive = hasCriticalRule && state.totalPendingCount > 0,
        contentPadding = PaddingValues(14.dp)
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable(onClick = onToggleExpanded),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                StatusDot(
                    color = accent,
                    pulsing = state.totalPendingCount > 0,
                    size = 7.dp
                )
                Text(
                    text = "Governança HiC & Sugestões",
                    style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.SemiBold),
                    color = TextPrimary,
                    modifier = Modifier.weight(1f),
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                if (state.totalPendingCount > 0) {
                    AuraPill(
                        text = "${state.totalPendingCount} pendentes",
                        color = accent
                    )
                }
                Icon(
                    imageVector = if (state.isExpanded) Icons.Filled.KeyboardArrowUp else Icons.Filled.KeyboardArrowDown,
                    contentDescription = if (state.isExpanded) "Recolher" else "Expandir",
                    tint = TextSecondary,
                    modifier = Modifier.size(18.dp)
                )
            }

            if (state.isLoading && state.candidateRules.isEmpty() && state.suggestedSimulations.isEmpty()) {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    ShimmerBox(modifier = Modifier.fillMaxWidth().height(54.dp))
                    ShimmerBox(modifier = Modifier.fillMaxWidth().height(64.dp))
                }
                return@AuraCard
            }

            AnimatedVisibility(visible = state.isExpanded) {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    if (state.suggestedSimulations.isNotEmpty()) {
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text(
                                text = "SIMULAÇÕES SUGERIDAS PELO PROFILER",
                                style = MaterialTheme.typography.labelSmall.copy(
                                    fontSize = 10.sp,
                                    letterSpacing = 0.7.sp
                                ),
                                color = AuraPurple
                            )
                            state.suggestedSimulations.forEach { card ->
                                SuggestedSimulationRow(
                                    card = card,
                                    onSimulate = { onSimulateSuggestion(card) }
                                )
                            }
                        }
                    }

                    if (state.candidateRules.isNotEmpty()) {
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text(
                                text = "REGRAS CANDIDATAS PARA APROVAÇÃO",
                                style = MaterialTheme.typography.labelSmall.copy(
                                    fontSize = 10.sp,
                                    letterSpacing = 0.7.sp
                                ),
                                color = accent
                            )
                            state.candidateRules.forEach { rule ->
                                CandidateRuleRow(
                                    rule = rule,
                                    isInFlight = rule.rule_id in state.pendingRuleDecisions,
                                    resolution = state.resolvedDecisions[rule.rule_id],
                                    onApprove = { onApproveRule(rule.rule_id) },
                                    onReject = { onRejectRule(rule.rule_id) }
                                )
                            }
                        }
                    }

                    state.errorMessage?.let { err ->
                        Text(
                            text = err,
                            style = MaterialTheme.typography.bodySmall,
                            color = StatusDanger
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun SuggestedSimulationRow(
    card: SuggestedSimulationCardDto,
    onSimulate: () -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .background(ObsidianLow)
            .border(1.dp, AuraPurple.copy(alpha = 0.35f), RoundedCornerShape(14.dp))
            .padding(12.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Column(
            modifier = Modifier.weight(1f),
            verticalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                Text(
                    text = card.title,
                    style = MaterialTheme.typography.titleSmall,
                    color = TextPrimary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f, fill = false)
                )
                AuraPill(text = "${card.hit_count}x", color = AuraPurple)
            }
            Text(
                text = card.reason,
                style = MaterialTheme.typography.bodySmall,
                color = TextSecondary,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis
            )
        }

        Row(
            modifier = Modifier
                .clip(RoundedCornerShape(12.dp))
                .background(AuraPurple.copy(alpha = 0.16f))
                .border(1.dp, AuraPurple.copy(alpha = 0.45f), RoundedCornerShape(12.dp))
                .clickable(onClick = onSimulate)
                .padding(horizontal = 10.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            Icon(
                imageVector = Icons.Rounded.Tune,
                contentDescription = null,
                tint = AuraPurple,
                modifier = Modifier.size(14.dp)
            )
            Text(
                text = "Simular",
                style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.SemiBold),
                color = TextPrimary
            )
        }
    }
}

@Composable
private fun CandidateRuleRow(
    rule: BusinessRuleDto,
    isInFlight: Boolean,
    resolution: String?,
    onApprove: () -> Unit,
    onReject: () -> Unit
) {
    val sevColor = when (rule.severity.uppercase()) {
        "CRITICAL", "HIGH" -> StatusDanger
        "MEDIUM" -> StatusWarning
        else -> AuraCyan
    }

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .background(ObsidianLow)
            .border(1.dp, GlassBorderSoft, RoundedCornerShape(14.dp))
            .padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            AuraPill(text = rule.severity.uppercase(), color = sevColor)
            Text(
                text = rule.rule_key,
                style = AuraTypographyExt.monoAudit,
                color = TextPrimary,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f)
            )
            Text(
                text = rule.origin,
                style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp),
                color = TextMuted
            )
        }

        Text(
            text = AuraIntelligenceFormatters.formatRuleExpression(
                metric = rule.metric,
                operator = rule.operator,
                threshold = rule.threshold_value,
                upper = rule.threshold_upper
            ),
            style = AuraTypographyExt.monoAudit,
            color = AuraCyan
        )

        if (rule.description.isNotBlank()) {
            Text(
                text = rule.description,
                style = MaterialTheme.typography.bodySmall,
                color = TextSecondary,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis
            )
        }

        when {
            resolution == "approved" -> {
                AuraPill(
                    text = "Regra aprovada e ativa",
                    color = AuraEmerald,
                    icon = Icons.Filled.Check
                )
            }
            resolution == "rejected" -> {
                AuraPill(
                    text = "Regra rejeitada",
                    color = TextMuted,
                    icon = Icons.Filled.Close
                )
            }
            isInFlight -> {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(14.dp),
                        strokeWidth = 2.dp,
                        color = AuraCyan
                    )
                    Text(
                        text = "Registrando decisão HiC...",
                        style = MaterialTheme.typography.labelSmall,
                        color = TextSecondary
                    )
                }
            }
            else -> {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    CompactDecisionButton(
                        label = "Rejeitar",
                        color = StatusDanger,
                        icon = Icons.Filled.Close,
                        onClick = onReject,
                        modifier = Modifier.weight(1f)
                    )
                    CompactDecisionButton(
                        label = "Aprovar",
                        color = AuraEmerald,
                        icon = Icons.Filled.Check,
                        onClick = onApprove,
                        modifier = Modifier.weight(1f)
                    )
                }
            }
        }
    }
}

@Composable
private fun CompactDecisionButton(
    label: String,
    color: Color,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier
            .defaultMinSize(minHeight = 40.dp)
            .clip(RoundedCornerShape(12.dp))
            .background(color.copy(alpha = 0.14f))
            .border(1.dp, color.copy(alpha = 0.42f), RoundedCornerShape(12.dp))
            .clickable(onClick = onClick)
            .padding(horizontal = 12.dp, vertical = 8.dp),
        horizontalArrangement = Arrangement.Center,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            tint = color,
            modifier = Modifier.size(15.dp)
        )
        Spacer(Modifier.width(6.dp))
        Text(
            text = label,
            style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold),
            color = color
        )
    }
}

// ---------------------------------------------------------------- Previews

@Preview(name = "HiC - Normal", showBackground = true, backgroundColor = 0xFF07090E, widthDp = 390)
@Composable
private fun GovernanceHiCBannerPreviewNormal() {
    AuraPostoAssitanceTheme {
        Box(Modifier.background(ObsidianBase).padding(16.dp)) {
            GovernanceHiCBanner(
                state = GovernanceHiCUiState(
                    packId = "retail_supermarket",
                    suggestedSimulations = listOf(
                        SuggestedSimulationCardDto(
                            card_id = "sug_1",
                            tenant_id = "default",
                            pack_id = "retail_supermarket",
                            topic_key = "margem_hortifruti",
                            entity_type = "category",
                            metric_key = "gross_margin_pct",
                            hit_count = 6,
                            recommended_scenario = "price_elasticity",
                            suggested_shocks = ShockVectorDto(price_delta_pct = 3.0),
                            title = "Reajuste Preventivo Hortifrúti",
                            reason = "6 consultas recentes sobre erosão de margem nesta categoria."
                        )
                    ),
                    candidateRules = listOf(
                        BusinessRuleDto(
                            rule_id = "rule_cand_1",
                            tenant_id = "default",
                            pack_id = "retail_supermarket",
                            rule_key = "desconto_max_caixa",
                            metric = "discount_pct",
                            operator = "<=",
                            threshold_value = 8.0,
                            severity = "MEDIUM",
                            status = "candidate",
                            origin = "profiler",
                            description = "Limitar desconto sem alçada no PDV em itens de giro rápido."
                        )
                    )
                ),
                onToggleExpanded = {},
                onApproveRule = {},
                onRejectRule = {},
                onSimulateSuggestion = {}
            )
        }
    }
}

@Preview(name = "HiC - Regra Crítica", showBackground = true, backgroundColor = 0xFF07090E, widthDp = 390)
@Composable
private fun GovernanceHiCBannerPreviewCriticalRule() {
    AuraPostoAssitanceTheme {
        Box(Modifier.background(ObsidianBase).padding(16.dp)) {
            GovernanceHiCBanner(
                state = GovernanceHiCUiState(
                    packId = "pharmacy_health",
                    candidateRules = listOf(
                        BusinessRuleDto(
                            rule_id = "rule_cand_crit",
                            tenant_id = "default",
                            pack_id = "pharmacy_health",
                            rule_key = "piso_margem_pbm",
                            metric = "net_margin_pct",
                            operator = ">=",
                            threshold_value = 12.0,
                            severity = "CRITICAL",
                            status = "candidate",
                            origin = "backtest_bias",
                            description = "Evitar vendas PBM abaixo da margem líquida mínima de 12%."
                        )
                    )
                ),
                onToggleExpanded = {},
                onApproveRule = {},
                onRejectRule = {},
                onSimulateSuggestion = {}
            )
        }
    }
}

@Preview(name = "HiC - Carregando", showBackground = true, backgroundColor = 0xFF07090E, widthDp = 390)
@Composable
private fun GovernanceHiCBannerPreviewLoading() {
    AuraPostoAssitanceTheme {
        Box(Modifier.background(ObsidianBase).padding(16.dp)) {
            GovernanceHiCBanner(
                state = GovernanceHiCUiState(
                    packId = "autocenter_parts",
                    isLoading = true
                ),
                onToggleExpanded = {},
                onApproveRule = {},
                onRejectRule = {},
                onSimulateSuggestion = {}
            )
        }
    }
}
