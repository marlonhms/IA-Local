package com.example.aurapostoassitance.ui.genui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material.icons.rounded.Tune
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.aurapostoassitance.data.remote.BacktestItemResultDto
import com.example.aurapostoassitance.data.remote.CalibrationProposalDto
import com.example.aurapostoassitance.data.remote.RealizedRoiScorecardResponseDto
import com.example.aurapostoassitance.ui.components.AuraCard
import com.example.aurapostoassitance.ui.components.AuraPill
import com.example.aurapostoassitance.ui.components.ShimmerBox
import com.example.aurapostoassitance.ui.components.StatusDot
import com.example.aurapostoassitance.ui.intelligence.AuraIntelligenceFormatters
import com.example.aurapostoassitance.ui.intelligence.BacktestScorecardUiState
import com.example.aurapostoassitance.ui.theme.AuraCyan
import com.example.aurapostoassitance.ui.theme.AuraEmerald
import com.example.aurapostoassitance.ui.theme.AuraPostoAssitanceTheme
import com.example.aurapostoassitance.ui.theme.AuraPurple
import com.example.aurapostoassitance.ui.theme.AuraTypographyExt
import com.example.aurapostoassitance.ui.theme.BorderHairline
import com.example.aurapostoassitance.ui.theme.GlassBorderSoft
import com.example.aurapostoassitance.ui.theme.ObsidianBase
import com.example.aurapostoassitance.ui.theme.ObsidianBright
import com.example.aurapostoassitance.ui.theme.ObsidianLow
import com.example.aurapostoassitance.ui.theme.StatusDanger
import com.example.aurapostoassitance.ui.theme.StatusWarning
import com.example.aurapostoassitance.ui.theme.TextMuted
import com.example.aurapostoassitance.ui.theme.TextPrimary
import com.example.aurapostoassitance.ui.theme.TextSecondary

/**
 * Micro-widget GenUI de Backtesting comparando Previsto (faixa P10/P50/P90) vs. Realizado (30/60/90d),
 * erro percentual e controle HiC para aprovar/rejeitar fator de calibração sugerido.
 */
@Composable
fun RealizedRoiScorecardCard(
    state: BacktestScorecardUiState,
    onSelectHorizon: (Int) -> Unit,
    onApproveCalibration: () -> Unit,
    onRejectCalibration: () -> Unit,
    onRefresh: () -> Unit = {},
    modifier: Modifier = Modifier
) {
    val scorecard = state.scorecard
    val hasPendingCalibration = scorecard?.pending_calibration != null && state.calibrationResolution == null
    val accent = if (hasPendingCalibration) StatusWarning else AuraEmerald

    AuraCard(
        modifier = modifier.fillMaxWidth(),
        accent = accent,
        glowActive = hasPendingCalibration,
        contentPadding = PaddingValues(16.dp)
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
            ScorecardHeader(
                state = state,
                onSelectHorizon = onSelectHorizon,
                onRefresh = onRefresh
            )

            if (state.isLoading && scorecard == null) {
                ScorecardLoadingSkeleton()
                return@AuraCard
            }

            if (scorecard == null) {
                Text(
                    text = state.errorMessage ?: "Nenhuma ação auditada em backtesting para este pack ainda.",
                    style = MaterialTheme.typography.bodySmall,
                    color = if (state.errorMessage != null) StatusDanger else TextMuted
                )
                return@AuraCard
            }

            // Hero Previsto vs Realizado
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(16.dp))
                    .background(ObsidianLow)
                    .border(1.dp, AuraEmerald.copy(alpha = 0.32f), RoundedCornerShape(16.dp))
                    .padding(14.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(
                        text = "REALIZADO AUDITADO (${state.selectedHorizonDays}D)",
                        style = MaterialTheme.typography.labelSmall.copy(letterSpacing = 0.6.sp),
                        color = AuraEmerald
                    )
                    Text(
                        text = "Previsto ${AuraIntelligenceFormatters.formatBrl(scorecard.projected_brl)}",
                        style = AuraTypographyExt.monoAudit,
                        color = TextSecondary
                    )
                }

                val realizedTotal = if (scorecard.realized_brl != 0.0) {
                    scorecard.realized_brl
                } else {
                    scorecard.total_realized_brl
                }
                Text(
                    text = AuraIntelligenceFormatters.formatBrl(realizedTotal, signed = realizedTotal < 0),
                    style = AuraTypographyExt.kpiHero,
                    color = TextPrimary,
                    maxLines = 1
                )
            }

            // Barra 3 colunas: Erro Médio | Acerto P10-P90 | Ações Auditadas
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(IntrinsicSize.Max)
                    .clip(RoundedCornerShape(14.dp))
                    .background(ObsidianLow)
                    .border(1.dp, BorderHairline, RoundedCornerShape(14.dp))
                    .padding(vertical = 10.dp)
            ) {
                ScorecardStatCol(
                    label = "Erro Médio",
                    value = AuraIntelligenceFormatters.formatPct(scorecard.mean_abs_error_pct, signed = false),
                    color = if (scorecard.mean_abs_error_pct <= 12.0) AuraEmerald else StatusWarning,
                    modifier = Modifier.weight(1f)
                )
                Box(Modifier.width(1.dp).fillMaxHeight().background(BorderHairline))
                ScorecardStatCol(
                    label = "Acerto P10–P90",
                    value = "${"%.0f".format(scorecard.hit_rate_pct)}%",
                    color = if (scorecard.hit_rate_pct >= 75.0) AuraCyan else StatusWarning,
                    modifier = Modifier.weight(1f)
                )
                Box(Modifier.width(1.dp).fillMaxHeight().background(BorderHairline))
                ScorecardStatCol(
                    label = "Auditadas",
                    value = "${scorecard.audited_actions_count}",
                    color = TextPrimary,
                    modifier = Modifier.weight(1f)
                )
            }

            // Lista comparativa P10/P50/P90 vs Realizado
            val visibleItems = state.filteredItems.take(4)
            if (visibleItems.isNotEmpty()) {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(
                        text = "PREVISTO (P10 / P50 / P90) VS. REALIZADO",
                        style = MaterialTheme.typography.labelSmall.copy(
                            fontSize = 10.sp,
                            letterSpacing = 0.7.sp
                        ),
                        color = TextMuted
                    )
                    visibleItems.forEach { item ->
                        BacktestItemRow(item = item)
                    }
                }
            }

            // Controle HiC de calibração
            scorecard.pending_calibration?.let { proposal ->
                CalibrationHiCPanel(
                    proposal = proposal,
                    inFlight = state.calibrationDecisionInFlight,
                    resolution = state.calibrationResolution,
                    onApprove = onApproveCalibration,
                    onReject = onRejectCalibration
                )
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

@Composable
private fun ScorecardHeader(
    state: BacktestScorecardUiState,
    onSelectHorizon: (Int) -> Unit,
    onRefresh: () -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            StatusDot(
                color = if (state.scorecard?.pending_calibration != null) StatusWarning else AuraEmerald,
                pulsing = state.isLoading,
                size = 7.dp
            )
            Text(
                text = "BACKTESTING ROI",
                style = MaterialTheme.typography.labelSmall.copy(letterSpacing = 0.7.sp),
                color = TextSecondary
            )
            state.scorecard?.takeIf { it.roi_multiple > 0.0 }?.let {
                AuraPill(
                    text = "${"%.1f".format(it.roi_multiple)}x ROI",
                    color = AuraEmerald
                )
            }
            Spacer(Modifier.weight(1f))
            Row(
                modifier = Modifier
                    .clip(RoundedCornerShape(50))
                    .background(ObsidianBase)
                    .border(1.dp, BorderHairline, RoundedCornerShape(50))
                    .padding(2.dp),
                horizontalArrangement = Arrangement.spacedBy(2.dp)
            ) {
                listOf(30, 60, 90).forEach { days ->
                    val selected = days == state.selectedHorizonDays
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(50))
                            .background(if (selected) AuraEmerald.copy(alpha = 0.22f) else Color.Transparent)
                            .clickable { onSelectHorizon(days) }
                            .padding(horizontal = 8.dp, vertical = 4.dp)
                    ) {
                        Text(
                            text = "${days}d",
                            style = AuraTypographyExt.monoAudit.copy(fontSize = 10.sp),
                            color = if (selected) AuraEmerald else TextMuted
                        )
                    }
                }
            }
            Icon(
                imageVector = Icons.Rounded.Refresh,
                contentDescription = "Atualizar scorecard",
                tint = TextMuted,
                modifier = Modifier
                    .size(18.dp)
                    .clickable(onClick = onRefresh)
            )
        }

        Text(
            text = "Previsto vs. Realizado",
            style = MaterialTheme.typography.headlineSmall.copy(lineHeight = 27.sp),
            color = TextPrimary
        )
    }
}

@Composable
private fun ScorecardStatCol(
    label: String,
    value: String,
    color: Color,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier.padding(horizontal = 10.dp),
        verticalArrangement = Arrangement.spacedBy(2.dp)
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp),
            color = TextMuted,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis
        )
        Text(
            text = value,
            style = AuraTypographyExt.kpiCompact,
            color = color,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis
        )
    }
}

@Composable
private fun BacktestItemRow(item: BacktestItemResultDto) {
    val badgeColor = if (item.within_p10_p90) AuraEmerald else StatusWarning

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .background(ObsidianLow)
            .border(1.dp, GlassBorderSoft, RoundedCornerShape(14.dp))
            .padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(6.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            Text(
                text = AuraIntelligenceFormatters.friendlyScenarioName(item.scenario_type),
                style = MaterialTheme.typography.titleSmall,
                color = TextPrimary,
                modifier = Modifier.weight(1f),
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
            AuraPill(text = "${item.horizon_days}d", color = AuraCyan)
            AuraPill(
                text = AuraIntelligenceFormatters.formatPct(item.error_pct),
                color = badgeColor
            )
        }

        BacktestBandMarker(item = item)

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(
                text = "P10 ${AuraIntelligenceFormatters.formatBrl(item.predicted_p10_brl)} • " +
                    "P50 ${AuraIntelligenceFormatters.formatBrl(item.predicted_p50_brl)} • " +
                    "P90 ${AuraIntelligenceFormatters.formatBrl(item.predicted_p90_brl)}",
                style = AuraTypographyExt.monoAudit.copy(fontSize = 10.sp),
                color = TextMuted,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f)
            )
            Spacer(Modifier.width(8.dp))
            Text(
                text = "Real ${AuraIntelligenceFormatters.formatBrl(item.realized_brl)}",
                style = AuraTypographyExt.monoAudit.copy(fontSize = 10.sp, fontWeight = FontWeight.Bold),
                color = badgeColor
            )
        }
    }
}

@Composable
private fun BacktestBandMarker(item: BacktestItemResultDto) {
    Canvas(
        modifier = Modifier
            .fillMaxWidth()
            .height(12.dp)
    ) {
        val minVal = minOf(item.predicted_p10_brl, item.realized_brl)
        val maxVal = maxOf(item.predicted_p90_brl, item.realized_brl)
        val span = (maxVal - minVal).takeIf { it > 0.0 } ?: 1.0

        val p10X = (((item.predicted_p10_brl - minVal) / span).toFloat()).coerceIn(0f, 1f) * size.width
        val p50X = (((item.predicted_p50_brl - minVal) / span).toFloat()).coerceIn(0f, 1f) * size.width
        val p90X = (((item.predicted_p90_brl - minVal) / span).toFloat()).coerceIn(0f, 1f) * size.width
        val realX = (((item.realized_brl - minVal) / span).toFloat()).coerceIn(0.03f, 0.97f) * size.width

        val barH = 5.dp.toPx()
        val topY = (size.height - barH) / 2f

        drawRoundRect(
            color = ObsidianBright,
            topLeft = Offset(0f, topY),
            size = Size(size.width, barH),
            cornerRadius = CornerRadius(barH / 2f, barH / 2f)
        )

        drawRoundRect(
            color = AuraCyan.copy(alpha = 0.45f),
            topLeft = Offset(p10X, topY),
            size = Size((p90X - p10X).coerceAtLeast(4.dp.toPx()), barH),
            cornerRadius = CornerRadius(barH / 2f, barH / 2f)
        )

        drawLine(
            color = TextPrimary.copy(alpha = 0.7f),
            start = Offset(p50X, topY - 2.dp.toPx()),
            end = Offset(p50X, topY + barH + 2.dp.toPx()),
            strokeWidth = 1.5.dp.toPx()
        )

        val dotColor = if (item.within_p10_p90) AuraEmerald else StatusWarning
        drawCircle(
            color = dotColor,
            radius = 4.5.dp.toPx(),
            center = Offset(realX, size.height / 2f)
        )
    }
}

@Composable
private fun CalibrationHiCPanel(
    proposal: CalibrationProposalDto,
    inFlight: Boolean,
    resolution: String?,
    onApprove: () -> Unit,
    onReject: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .background(AuraPurple.copy(alpha = 0.08f))
            .border(1.dp, StatusWarning.copy(alpha = 0.40f), RoundedCornerShape(14.dp))
            .padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            Icon(
                imageVector = Icons.Rounded.Tune,
                contentDescription = null,
                tint = StatusWarning,
                modifier = Modifier.size(16.dp)
            )
            Text(
                text = "CALIBRAÇÃO SUGERIDA (HiC)",
                style = MaterialTheme.typography.labelSmall.copy(
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 0.6.sp
                ),
                color = StatusWarning,
                modifier = Modifier.weight(1f)
            )
            AuraPill(text = "n=${proposal.sample_size}", color = AuraPurple)
        }

        Text(
            text = "${proposal.metric}: ${"%.2f".format(proposal.current_factor)} → ${"%.2f".format(proposal.suggested_factor)} " +
                "(viés ${AuraIntelligenceFormatters.formatPct(proposal.mean_bias_pct)})",
            style = AuraTypographyExt.monoAudit,
            color = TextPrimary
        )

        Text(
            text = proposal.reason,
            style = MaterialTheme.typography.bodySmall,
            color = TextSecondary
        )

        when {
            resolution == "approved" -> {
                AuraPill(
                    text = "Calibração aprovada e aplicada",
                    color = AuraEmerald,
                    icon = Icons.Filled.Check
                )
            }
            resolution == "rejected" -> {
                AuraPill(
                    text = "Calibração rejeitada",
                    color = TextMuted,
                    icon = Icons.Filled.Close
                )
            }
            inFlight -> {
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
                        text = "Aplicando calibração...",
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
                    CalibrationActionBtn(
                        label = "Rejeitar",
                        color = StatusDanger,
                        icon = Icons.Filled.Close,
                        onClick = onReject,
                        modifier = Modifier.weight(1f)
                    )
                    CalibrationActionBtn(
                        label = "Aprovar Fator",
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
private fun CalibrationActionBtn(
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

@Composable
private fun ScorecardLoadingSkeleton() {
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        ShimmerBox(modifier = Modifier.fillMaxWidth().height(84.dp), shape = RoundedCornerShape(16.dp))
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            ShimmerBox(modifier = Modifier.weight(1f).height(52.dp))
            ShimmerBox(modifier = Modifier.weight(1f).height(52.dp))
            ShimmerBox(modifier = Modifier.weight(1f).height(52.dp))
        }
        ShimmerBox(modifier = Modifier.fillMaxWidth().height(72.dp), shape = RoundedCornerShape(14.dp))
    }
}

// ---------------------------------------------------------------- Previews

private fun previewScorecardResponse(withCalibration: Boolean = false) =
    RealizedRoiScorecardResponseDto(
        tenant_id = "default",
        pack_id = "retail_supermarket",
        period_days = 90,
        projected_brl = 42000.0,
        realized_brl = 45800.0,
        total_realized_brl = 45800.0,
        hit_rate_pct = 86.0,
        mean_abs_error_pct = 7.4,
        roi_multiple = 4.2,
        audited_actions_count = 7,
        items = listOf(
            BacktestItemResultDto(
                simulation_id = "sim_1",
                scenario_type = "price_elasticity",
                horizon_days = 30,
                predicted_p10_brl = 11000.0,
                predicted_p50_brl = 14500.0,
                predicted_p90_brl = 18200.0,
                realized_brl = 15400.0,
                error_brl = 900.0,
                error_pct = 6.2,
                within_p10_p90 = true
            ),
            BacktestItemResultDto(
                simulation_id = "sim_2",
                scenario_type = "margin_protection",
                horizon_days = 60,
                predicted_p10_brl = 24000.0,
                predicted_p50_brl = 27500.0,
                predicted_p90_brl = 31000.0,
                realized_brl = if (withCalibration) 32600.0 else 30400.0,
                error_brl = if (withCalibration) 5100.0 else 2900.0,
                error_pct = if (withCalibration) 18.5 else 10.5,
                within_p10_p90 = !withCalibration
            )
        ),
        pending_calibration = if (withCalibration) {
            CalibrationProposalDto(
                rule_id = "calib_1",
                tenant_id = "default",
                pack_id = "retail_supermarket",
                metric = "elasticity_calibration_factor",
                current_factor = 1.0,
                suggested_factor = 1.14,
                mean_bias_pct = 13.8,
                sample_size = 7,
                reason = "Realizado superou consistentemente o P50 nos últimos 60 dias."
            )
        } else null
    )

@Preview(name = "Scorecard - Normal", showBackground = true, backgroundColor = 0xFF07090E, widthDp = 390)
@Composable
private fun RealizedRoiScorecardPreviewNormal() {
    AuraPostoAssitanceTheme {
        Box(Modifier.background(ObsidianBase).padding(16.dp)) {
            RealizedRoiScorecardCard(
                state = BacktestScorecardUiState(
                    packId = "retail_supermarket",
                    selectedHorizonDays = 90,
                    scorecard = previewScorecardResponse(withCalibration = false)
                ),
                onSelectHorizon = {},
                onApproveCalibration = {},
                onRejectCalibration = {}
            )
        }
    }
}

@Preview(name = "Scorecard - Calibração / Desvio", showBackground = true, backgroundColor = 0xFF07090E, widthDp = 390)
@Composable
private fun RealizedRoiScorecardPreviewCalibrationAlert() {
    AuraPostoAssitanceTheme {
        Box(Modifier.background(ObsidianBase).padding(16.dp)) {
            RealizedRoiScorecardCard(
                state = BacktestScorecardUiState(
                    packId = "pharmacy_health",
                    selectedHorizonDays = 60,
                    scorecard = previewScorecardResponse(withCalibration = true)
                ),
                onSelectHorizon = {},
                onApproveCalibration = {},
                onRejectCalibration = {}
            )
        }
    }
}

@Preview(name = "Scorecard - Carregando", showBackground = true, backgroundColor = 0xFF07090E, widthDp = 390)
@Composable
private fun RealizedRoiScorecardPreviewLoading() {
    AuraPostoAssitanceTheme {
        Box(Modifier.background(ObsidianBase).padding(16.dp)) {
            RealizedRoiScorecardCard(
                state = BacktestScorecardUiState(
                    packId = "wholesale_distribution",
                    isLoading = true,
                    scorecard = null
                ),
                onSelectHorizon = {},
                onApproveCalibration = {},
                onRejectCalibration = {}
            )
        }
    }
}
