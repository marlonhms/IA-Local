package com.example.aurapostoassitance.ui.genui

import androidx.compose.animation.AnimatedVisibility
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
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.WarningAmber
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.aurapostoassitance.data.remote.MonteCarloBandsDto
import com.example.aurapostoassitance.data.remote.RuleViolationDto
import com.example.aurapostoassitance.data.remote.ShockVectorDto
import com.example.aurapostoassitance.data.remote.SimulationProvenanceDto
import com.example.aurapostoassitance.data.remote.SimulationRecomputeResponseDto
import com.example.aurapostoassitance.ui.components.AuraCard
import com.example.aurapostoassitance.ui.components.AuraGradientButton
import com.example.aurapostoassitance.ui.components.AuraPill
import com.example.aurapostoassitance.ui.components.ShimmerBox
import com.example.aurapostoassitance.ui.components.StatusDot
import com.example.aurapostoassitance.ui.intelligence.AuraIntelligenceFormatters
import com.example.aurapostoassitance.ui.intelligence.WhatIfUiState
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
import com.example.aurapostoassitance.ui.theme.ObsidianMid
import com.example.aurapostoassitance.ui.theme.StatusDanger
import com.example.aurapostoassitance.ui.theme.StatusWarning
import com.example.aurapostoassitance.ui.theme.TextMuted
import com.example.aurapostoassitance.ui.theme.TextPrimary
import com.example.aurapostoassitance.ui.theme.TextSecondary
import kotlin.math.roundToInt

/**
 * Micro-widget GenUI nativo para simulação What-If determinística zero-token.
 * Todo arraste de slider aciona exclusivamente `/api/v1/simulate/recompute` via debounce no ViewModel;
 * chamadas ao LLM ocorrem somente ao clicar explicitamente em "Auditar este cenário com IA".
 */
@Composable
fun WhatIfSimulatorCard(
    state: WhatIfUiState,
    onShocksChange: (ShockVectorDto) -> Unit,
    onHorizonChange: (Int) -> Unit,
    onAuditWithAi: (String) -> Unit,
    onRetry: () -> Unit = {},
    modifier: Modifier = Modifier
) {
    val hasViolations = state.hasViolations
    val accent = if (hasViolations) StatusDanger else AuraPurple

    AuraCard(
        modifier = modifier.fillMaxWidth(),
        accent = accent,
        glowActive = hasViolations,
        contentPadding = PaddingValues(16.dp)
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
            WhatIfCardHeader(
                state = state,
                onHorizonChange = onHorizonChange
            )

            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(1.dp)
                    .background(GlassBorderSoft)
            )

            MonteCarloBandsPanel(state = state)

            AnimatedVisibility(visible = hasViolations) {
                RuleViolationsPanel(
                    violations = state.response?.violated_rules.orEmpty()
                )
            }

            if (state.errorMessage != null) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(12.dp))
                        .background(StatusDanger.copy(alpha = 0.12f))
                        .border(1.dp, StatusDanger.copy(alpha = 0.35f), RoundedCornerShape(12.dp))
                        .padding(horizontal = 12.dp, vertical = 10.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(
                        text = state.errorMessage,
                        style = MaterialTheme.typography.bodySmall,
                        color = StatusDanger,
                        modifier = Modifier.weight(1f),
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis
                    )
                    Spacer(Modifier.width(8.dp))
                    Text(
                        text = "Tentar",
                        style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold),
                        color = AuraCyan,
                        modifier = Modifier.clickable(onClick = onRetry)
                    )
                }
            }

            WhatIfSlidersPanel(
                shocks = state.shocks,
                onShocksChange = onShocksChange
            )

            state.response?.provenance?.let { provenance ->
                ProvenanceFooter(provenance = provenance)
            }

            AuraGradientButton(
                text = "Auditar este cenário com IA",
                icon = Icons.Rounded.AutoAwesome,
                onClick = { onAuditWithAi(AuraIntelligenceFormatters.buildWhatIfAuditPrompt(state)) },
                modifier = Modifier.fillMaxWidth()
            )
        }
    }
}

@Composable
private fun WhatIfCardHeader(
    state: WhatIfUiState,
    onHorizonChange: (Int) -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            StatusDot(
                color = if (state.hasViolations) StatusDanger else AuraCyan,
                pulsing = state.isLoading || state.hasViolations,
                size = 7.dp
            )
            AuraPill(text = "0 TOKENS LLM", color = AuraCyan)
            state.response?.let { resp ->
                AuraPill(
                    text = "${resp.elapsed_ms.roundToInt().coerceAtLeast(1)}ms",
                    color = AuraEmerald
                )
            }
            Spacer(Modifier.weight(1f))
            HorizonSelectorPills(
                selectedDays = state.horizonDays,
                onSelect = onHorizonChange
            )
        }

        Text(
            text = state.title,
            style = MaterialTheme.typography.headlineSmall.copy(lineHeight = 27.sp),
            color = TextPrimary
        )

        val subtitleText = state.subtitle?.takeIf { it.isNotBlank() }
            ?: "${AuraIntelligenceFormatters.friendlyScenarioName(state.scenarioType)} • Pack ${state.packId}"
        Text(
            text = subtitleText,
            style = MaterialTheme.typography.bodySmall,
            color = TextSecondary,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis
        )
    }
}

@Composable
private fun HorizonSelectorPills(
    selectedDays: Int,
    onSelect: (Int) -> Unit
) {
    Row(
        modifier = Modifier
            .clip(RoundedCornerShape(50))
            .background(ObsidianBase)
            .border(1.dp, BorderHairline, RoundedCornerShape(50))
            .padding(2.dp),
        horizontalArrangement = Arrangement.spacedBy(2.dp)
    ) {
        listOf(30, 60, 90).forEach { days ->
            val selected = days == selectedDays
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(50))
                    .background(if (selected) AuraPurple.copy(alpha = 0.25f) else Color.Transparent)
                    .clickable { onSelect(days) }
                    .padding(horizontal = 8.dp, vertical = 4.dp)
            ) {
                Text(
                    text = "${days}d",
                    style = AuraTypographyExt.monoAudit.copy(fontSize = 10.sp),
                    color = if (selected) TextPrimary else TextMuted
                )
            }
        }
    }
}

@Composable
private fun MonteCarloBandsPanel(state: WhatIfUiState) {
    val bands = state.response?.monte_carlo
    if (state.isLoading && bands == null) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(16.dp))
                .background(ObsidianLow)
                .border(1.dp, GlassBorderSoft, RoundedCornerShape(16.dp))
                .padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            ShimmerBox(modifier = Modifier.fillMaxWidth(0.45f).height(14.dp))
            ShimmerBox(modifier = Modifier.fillMaxWidth(0.65f).height(30.dp))
            ShimmerBox(modifier = Modifier.fillMaxWidth().height(10.dp), shape = RoundedCornerShape(50))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                ShimmerBox(modifier = Modifier.weight(1f).height(44.dp))
                ShimmerBox(modifier = Modifier.weight(1f).height(44.dp))
                ShimmerBox(modifier = Modifier.weight(1f).height(44.dp))
            }
        }
        return
    }

    if (bands == null) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(16.dp))
                .background(ObsidianLow)
                .border(1.dp, GlassBorderSoft, RoundedCornerShape(16.dp))
                .padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            Text(
                text = "PROJEÇÃO MONTE CARLO (${state.horizonDays} DIAS)",
                style = MaterialTheme.typography.labelSmall.copy(letterSpacing = 0.6.sp),
                color = TextSecondary
            )
            Text(
                text = "Ajuste os sliders abaixo para simular instantaneamente as faixas P10 / P50 / P90.",
                style = MaterialTheme.typography.bodySmall,
                color = TextMuted
            )
        }
        return
    }

    val p50Positive = bands.p50 >= 0.0
    val heroColor = if (p50Positive) AuraEmerald else StatusDanger
    val borderColor = if (state.hasViolations) StatusDanger.copy(alpha = 0.40f) else AuraPurple.copy(alpha = 0.35f)

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(ObsidianLow)
            .border(1.dp, borderColor, RoundedCornerShape(16.dp))
            .padding(14.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                Text(
                    text = "MEDIANA P50 (${state.horizonDays}D)",
                    style = MaterialTheme.typography.labelSmall.copy(letterSpacing = 0.6.sp),
                    color = TextSecondary
                )
                if (state.isLoading) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(12.dp),
                        strokeWidth = 1.6.dp,
                        color = AuraCyan
                    )
                }
            }
            AuraPill(
                text = "${"%.0f".format(bands.prob_positive_pct)}% prob. +",
                color = if (bands.prob_positive_pct >= 60.0) AuraEmerald else StatusWarning
            )
        }

        Text(
            text = AuraIntelligenceFormatters.formatBrl(bands.p50, signed = true),
            style = AuraTypographyExt.kpiHero,
            color = heroColor,
            maxLines = 1
        )

        MonteCarloRangeBar(bands = bands)

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .height(IntrinsicSize.Max)
                .clip(RoundedCornerShape(12.dp))
                .background(ObsidianBase)
                .border(1.dp, BorderHairline, RoundedCornerShape(12.dp))
                .padding(vertical = 8.dp)
        ) {
            BandColumn(
                label = "P10 CONSERV.",
                value = AuraIntelligenceFormatters.formatBrl(bands.p10, signed = true),
                color = if (bands.p10 >= 0.0) AuraCyan else StatusWarning,
                modifier = Modifier.weight(1f)
            )
            Box(Modifier.width(1.dp).fillMaxHeight().background(BorderHairline))
            BandColumn(
                label = "P50 BASE",
                value = AuraIntelligenceFormatters.formatBrl(bands.p50, signed = true),
                color = heroColor,
                modifier = Modifier.weight(1f)
            )
            Box(Modifier.width(1.dp).fillMaxHeight().background(BorderHairline))
            BandColumn(
                label = "P90 OTIMISTA",
                value = AuraIntelligenceFormatters.formatBrl(bands.p90, signed = true),
                color = AuraEmerald,
                modifier = Modifier.weight(1f)
            )
        }
    }
}

@Composable
private fun BandColumn(
    label: String,
    value: String,
    color: Color,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier.padding(horizontal = 8.dp),
        verticalArrangement = Arrangement.spacedBy(2.dp)
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall.copy(fontSize = 9.5.sp),
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
private fun MonteCarloRangeBar(bands: MonteCarloBandsDto) {
    Canvas(
        modifier = Modifier
            .fillMaxWidth()
            .height(14.dp)
    ) {
        val trackHeight = 6.dp.toPx()
        val trackTop = (size.height - trackHeight) / 2f
        val corner = CornerRadius(trackHeight / 2f, trackHeight / 2f)

        drawRoundRect(
            color = ObsidianBright,
            topLeft = Offset(0f, trackTop),
            size = Size(size.width, trackHeight),
            cornerRadius = corner
        )

        val span = (bands.p90 - bands.p10).takeIf { it > 0.0 } ?: 1.0
        val p50Fraction = ((bands.p50 - bands.p10) / span).toFloat().coerceIn(0.08f, 0.92f)

        drawRoundRect(
            brush = Brush.horizontalGradient(
                listOf(AuraCyan.copy(alpha = 0.75f), AuraPurple, AuraEmerald)
            ),
            topLeft = Offset(0f, trackTop),
            size = Size(size.width, trackHeight),
            cornerRadius = corner
        )

        val p50X = size.width * p50Fraction
        drawCircle(
            color = TextPrimary,
            radius = 5.5.dp.toPx(),
            center = Offset(p50X, size.height / 2f)
        )
        drawCircle(
            color = AuraPurple,
            radius = 3.dp.toPx(),
            center = Offset(p50X, size.height / 2f)
        )
    }
}

@Composable
private fun RuleViolationsPanel(violations: List<RuleViolationDto>) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .background(StatusDanger.copy(alpha = 0.08f))
            .border(1.dp, StatusDanger.copy(alpha = 0.40f), RoundedCornerShape(14.dp))
            .padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            Icon(
                imageVector = Icons.Filled.ErrorOutline,
                contentDescription = null,
                tint = StatusDanger,
                modifier = Modifier.size(16.dp)
            )
            Text(
                text = "REGRAS DURAS VIOLADAS (${violations.size})",
                style = MaterialTheme.typography.labelSmall.copy(
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 0.6.sp
                ),
                color = StatusDanger
            )
        }

        violations.forEach { violation ->
            val sevColor = when (violation.severity.uppercase()) {
                "CRITICAL", "HIGH" -> StatusDanger
                else -> StatusWarning
            }
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(10.dp))
                    .background(ObsidianBase.copy(alpha = 0.85f))
                    .border(1.dp, sevColor.copy(alpha = 0.30f), RoundedCornerShape(10.dp))
                    .padding(10.dp),
                verticalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    Icon(
                        imageVector = Icons.Filled.WarningAmber,
                        contentDescription = null,
                        tint = sevColor,
                        modifier = Modifier.size(14.dp)
                    )
                    AuraPill(text = violation.severity.uppercase(), color = sevColor)
                    Text(
                        text = violation.rule_key,
                        style = AuraTypographyExt.monoAudit,
                        color = TextPrimary,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.weight(1f)
                    )
                }
                Text(
                    text = violation.message,
                    style = MaterialTheme.typography.bodySmall,
                    color = TextSecondary
                )
                Text(
                    text = "Observado ${"%.2f".format(violation.observed_value)} • Limite ${violation.operator} ${"%.2f".format(violation.threshold)}",
                    style = AuraTypographyExt.monoAudit.copy(fontSize = 10.sp),
                    color = TextMuted
                )
            }
        }
    }
}

@Composable
private fun WhatIfSlidersPanel(
    shocks: ShockVectorDto,
    onShocksChange: (ShockVectorDto) -> Unit
) {
    val haptic = LocalHapticFeedback.current

    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        DeterministicSliderRow(
            label = "Ajuste de Preço",
            value = shocks.price_delta_pct.toFloat(),
            range = -15f..15f,
            accent = AuraCyan,
            onValueChange = { next ->
                val rounded = (next * 2f).roundToInt() / 2f
                if (rounded.toInt() != shocks.price_delta_pct.toInt()) {
                    haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                }
                onShocksChange(shocks.copy(price_delta_pct = rounded.toDouble()))
            }
        )
        DeterministicSliderRow(
            label = "Desconto Comercial",
            value = shocks.discount_pct.toFloat(),
            range = 0f..20f,
            accent = AuraPurple,
            onValueChange = { next ->
                val rounded = (next * 2f).roundToInt() / 2f
                if (rounded.toInt() != shocks.discount_pct.toInt()) {
                    haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                }
                onShocksChange(shocks.copy(discount_pct = rounded.toDouble()))
            }
        )
        DeterministicSliderRow(
            label = "Custo Fornecedor",
            value = shocks.supplier_cost_delta_pct.toFloat(),
            range = -15f..20f,
            accent = StatusWarning,
            onValueChange = { next ->
                val rounded = (next * 2f).roundToInt() / 2f
                if (rounded.toInt() != shocks.supplier_cost_delta_pct.toInt()) {
                    haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                }
                onShocksChange(shocks.copy(supplier_cost_delta_pct = rounded.toDouble()))
            }
        )
        DeterministicSliderRow(
            label = "Repasse de Custo",
            value = shocks.cost_passthrough_pct.toFloat(),
            range = 0f..100f,
            accent = AuraEmerald,
            onValueChange = { next ->
                val rounded = (next / 5f).roundToInt() * 5f
                if (rounded.toInt() != shocks.cost_passthrough_pct.toInt()) {
                    haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                }
                onShocksChange(shocks.copy(cost_passthrough_pct = rounded.toDouble()))
            }
        )
    }
}

@Composable
private fun DeterministicSliderRow(
    label: String,
    value: Float,
    range: ClosedFloatingPointRange<Float>,
    accent: Color,
    onValueChange: (Float) -> Unit
) {
    Column {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(label, style = MaterialTheme.typography.labelSmall, color = TextSecondary)
            Text(
                text = AuraIntelligenceFormatters.formatPct(value.toDouble(), signed = range.start < 0f),
                style = AuraTypographyExt.monoAudit,
                color = accent
            )
        }
        Slider(
            value = value.coerceIn(range.start, range.endInclusive),
            onValueChange = onValueChange,
            valueRange = range,
            colors = SliderDefaults.colors(
                thumbColor = accent,
                activeTrackColor = accent,
                inactiveTrackColor = ObsidianBright
            )
        )
    }
}

@Composable
private fun ProvenanceFooter(provenance: SimulationProvenanceDto) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(10.dp))
            .background(ObsidianBase.copy(alpha = 0.7f))
            .border(1.dp, BorderHairline, RoundedCornerShape(10.dp))
            .padding(horizontal = 10.dp, vertical = 7.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp)
    ) {
        Icon(
            imageVector = Icons.Filled.Info,
            contentDescription = null,
            tint = TextMuted,
            modifier = Modifier.size(13.dp)
        )
        Text(
            text = AuraIntelligenceFormatters.formatProvenanceLine(provenance),
            style = AuraTypographyExt.monoAudit.copy(fontSize = 10.sp),
            color = TextMuted,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis
        )
    }
}

// ---------------------------------------------------------------- Previews

private fun previewSimulationResponse(violated: List<RuleViolationDto> = emptyList()) =
    SimulationRecomputeResponseDto(
        simulation_id = "sim_preview_01",
        tenant_id = "default",
        pack_id = "retail_supermarket",
        scenario_type = "price_elasticity",
        horizon_days = 30,
        monte_carlo = MonteCarloBandsDto(
            p10 = if (violated.isEmpty()) 8400.0 else -3200.0,
            p50 = if (violated.isEmpty()) 14950.0 else 1850.0,
            p90 = if (violated.isEmpty()) 22400.0 else 7400.0,
            mean = if (violated.isEmpty()) 15120.0 else 2010.0,
            std_dev = 3400.0,
            prob_positive_pct = if (violated.isEmpty()) 94.0 else 58.0,
            iterations = 5000,
            seed = 42
        ),
        violated_rules = violated,
        is_compliant = violated.isEmpty(),
        elapsed_ms = 14.2,
        llm_calls = 0,
        provenance = SimulationProvenanceDto(
            baseline_source = "erp_historical",
            active_rules_count = 4,
            yaml_rules_count = 2,
            memory_rules_count = 2,
            cited_documents = listOf("politica_margem_2026.pdf", "historico_pdv_90d")
        )
    )

@Preview(name = "WhatIf - Normal", showBackground = true, backgroundColor = 0xFF07090E, widthDp = 390)
@Composable
private fun WhatIfSimulatorPreviewNormal() {
    AuraPostoAssitanceTheme {
        Box(Modifier.background(ObsidianBase).padding(16.dp)) {
            WhatIfSimulatorCard(
                state = WhatIfUiState(
                    packId = "retail_supermarket",
                    title = "Simulador What-If • Curva A",
                    subtitle = "Elasticidade preço-volume em tempo real",
                    shocks = ShockVectorDto(price_delta_pct = 2.5, discount_pct = 1.0),
                    response = previewSimulationResponse()
                ),
                onShocksChange = {},
                onHorizonChange = {},
                onAuditWithAi = {}
            )
        }
    }
}

@Preview(name = "WhatIf - Regra Violada", showBackground = true, backgroundColor = 0xFF07090E, widthDp = 390)
@Composable
private fun WhatIfSimulatorPreviewViolated() {
    AuraPostoAssitanceTheme {
        Box(Modifier.background(ObsidianBase).padding(16.dp)) {
            WhatIfSimulatorCard(
                state = WhatIfUiState(
                    packId = "pharmacy_health",
                    title = "Simulador What-If • Linha OTC",
                    shocks = ShockVectorDto(discount_pct = 14.0, supplier_cost_delta_pct = 6.0),
                    response = previewSimulationResponse(
                        violated = listOf(
                            RuleViolationDto(
                                rule_id = "rule_min_margin",
                                source = "business_memory",
                                rule_key = "margem_minima_otc",
                                metric = "gross_margin_pct",
                                operator = ">=",
                                threshold = 18.0,
                                observed_value = 13.4,
                                severity = "CRITICAL",
                                message = "Margem projetada (13,4%) viola o piso institucional de 18,0%."
                            )
                        )
                    )
                ),
                onShocksChange = {},
                onHorizonChange = {},
                onAuditWithAi = {}
            )
        }
    }
}

@Preview(name = "WhatIf - Carregando", showBackground = true, backgroundColor = 0xFF07090E, widthDp = 390)
@Composable
private fun WhatIfSimulatorPreviewLoading() {
    AuraPostoAssitanceTheme {
        Box(Modifier.background(ObsidianBase).padding(16.dp)) {
            WhatIfSimulatorCard(
                state = WhatIfUiState(
                    packId = "wholesale_distribution",
                    title = "Simulador What-If • Lote B2B",
                    isLoading = true,
                    response = null
                ),
                onShocksChange = {},
                onHorizonChange = {},
                onAuditWithAi = {}
            )
        }
    }
}
