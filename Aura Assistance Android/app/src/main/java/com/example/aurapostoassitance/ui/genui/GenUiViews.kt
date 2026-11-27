package com.example.aurapostoassitance.ui.genui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.slideInVertically
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
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowDownward
import androidx.compose.material.icons.filled.ArrowUpward
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.WarningAmber
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.geometry.RoundRect
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.clipPath
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import com.example.aurapostoassitance.data.remote.ShockVectorDto
import com.example.aurapostoassitance.ui.components.AuraCard
import com.example.aurapostoassitance.ui.components.AuraGhostButton
import com.example.aurapostoassitance.ui.components.AuraGradientButton
import com.example.aurapostoassitance.ui.components.AuraPill
import com.example.aurapostoassitance.ui.components.SectionLabel
import com.example.aurapostoassitance.ui.components.ShimmerBox
import com.example.aurapostoassitance.ui.components.StatusDot
import com.example.aurapostoassitance.ui.components.statusColor
import com.example.aurapostoassitance.ui.domain.AuraDomainAdapter
import com.example.aurapostoassitance.ui.intelligence.BacktestScorecardUiState
import com.example.aurapostoassitance.ui.intelligence.WhatIfUiState
import com.example.aurapostoassitance.ui.theme.AuraCyan
import com.example.aurapostoassitance.ui.theme.AuraEmerald
import com.example.aurapostoassitance.ui.theme.AuraPurple
import com.example.aurapostoassitance.ui.theme.AuraTypographyExt
import com.example.aurapostoassitance.ui.theme.AuroraBrush
import com.example.aurapostoassitance.ui.theme.BorderHairline
import com.example.aurapostoassitance.ui.theme.GlassBorderSoft
import com.example.aurapostoassitance.ui.theme.GlassHighlight
import com.example.aurapostoassitance.ui.theme.NewsreaderFamily
import com.example.aurapostoassitance.ui.theme.ObsidianBase
import com.example.aurapostoassitance.ui.theme.ObsidianBright
import com.example.aurapostoassitance.ui.theme.ObsidianLow
import com.example.aurapostoassitance.ui.theme.ObsidianMid
import com.example.aurapostoassitance.ui.theme.OutlineSoft
import com.example.aurapostoassitance.ui.theme.StatusDanger
import com.example.aurapostoassitance.ui.theme.StatusWarning
import com.example.aurapostoassitance.ui.theme.TextMuted
import com.example.aurapostoassitance.ui.theme.TextPrimary
import com.example.aurapostoassitance.ui.theme.TextSecondary
import kotlinx.coroutines.delay
import kotlin.math.sin

/** Slot geométrico estável Zero-CLS reservado ao receber SSE ui_skeleton antes de ui_complete. */
@Composable
fun GenUiSkeletonSlot(
    title: String? = null,
    modifier: Modifier = Modifier
) {
    AuraCard(
        modifier = modifier.fillMaxWidth(),
        accent = AuraCyan,
        contentPadding = PaddingValues(16.dp)
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                StatusDot(color = AuraCyan, size = 7.dp, pulsing = true)
                Text(
                    text = title?.takeIf { it.isNotBlank() } ?: "Hidratando diagnóstico determinístico...",
                    style = MaterialTheme.typography.labelMedium,
                    color = TextSecondary
                )
            }
            ShimmerBox(
                modifier = Modifier
                    .fillMaxWidth(0.55f)
                    .height(28.dp)
            )
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                ShimmerBox(modifier = Modifier.weight(1f).height(58.dp))
                ShimmerBox(modifier = Modifier.weight(1f).height(58.dp))
                ShimmerBox(modifier = Modifier.weight(1f).height(58.dp))
            }
            ShimmerBox(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(42.dp),
                shape = RoundedCornerShape(14.dp)
            )
        }
    }
}

/** Regra estrita multi-domínio: TankTile renderiza somente para o pack fuel_convenience. */
fun isTankTileAllowedForPack(packId: String?): Boolean =
    AuraDomainAdapter.normalizePackId(packId) == AuraDomainAdapter.PACK_FUEL

/** Card executivo nativo deluxe: hierarquia 1-3-N, confirmação inline 2-passos e ações HITL. */
@Composable
fun GenUiCardView(
    card: GenUiCard,
    onAction: (GenUiAction) -> Unit,
    onDrillDown: (String) -> Unit = {},
    companionText: String? = null,
    activePackId: String = AuraDomainAdapter.PACK_FUEL,
    whatIfState: WhatIfUiState? = null,
    onWhatIfShocksChange: ((ShockVectorDto) -> Unit)? = null,
    onWhatIfHorizonChange: ((Int) -> Unit)? = null,
    onWhatIfAuditWithAi: ((String) -> Unit)? = null,
    onWhatIfRetry: (() -> Unit)? = null,
    scorecardState: BacktestScorecardUiState? = null,
    onScorecardHorizonChange: ((Int) -> Unit)? = null,
    onApproveCalibration: (() -> Unit)? = null,
    onRejectCalibration: (() -> Unit)? = null,
    onRefreshScorecard: (() -> Unit)? = null,
    modifier: Modifier = Modifier
) {
    var armedActionId by remember(card.title) { mutableStateOf<String?>(null) }
    val haptic = LocalHapticFeedback.current
    val isCritical = card.severity.equals("critical", true) || card.severity.equals("danger", true)
    val accent = if (isCritical) StatusDanger else AuraCyan

    // Desarma confirmação inline após 6 segundos para evitar acionamento acidental
    LaunchedEffect(armedActionId) {
        if (armedActionId != null) {
            delay(6000L)
            armedActionId = null
        }
    }
    val cardContextSummary = remember(card) {
        buildList {
            add(card.title)
            (card.diagnosis ?: card.subtitle)?.takeIf { it.isNotBlank() }?.let { add(it) }
            card.blocks.forEach { block ->
                when (block) {
                    is GenUiBlock.AlertCallout -> {
                        val msg = listOf(block.alert.title, block.alert.message).filter { it.isNotBlank() }.joinToString(" — ")
                        if (msg.isNotBlank()) add(msg)
                    }
                    is GenUiBlock.KpiGrid -> {
                        val kpiLine = block.kpis.take(4).joinToString(" | ") { "${it.label}: ${it.value}" }
                        if (kpiLine.isNotBlank()) add(kpiLine)
                    }
                    is GenUiBlock.Note -> {
                        val noteLine = block.text.replace("\n", " ").trim().take(180)
                        if (noteLine.isNotBlank()) add(noteLine)
                    }
                    else -> Unit
                }
            }
        }.joinToString("\n").take(550)
    }

    AuraCard(
        modifier = modifier.fillMaxWidth(),
        accent = accent,
        glowActive = isCritical,
        contentPadding = PaddingValues(0.dp)
    ) {
        Column(
            verticalArrangement = Arrangement.spacedBy(14.dp),
            modifier = Modifier.padding(16.dp)
        ) {
            CardHeader(card, companionText = companionText)

            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(1.dp)
                    .background(GlassBorderSoft)
            )

            card.blocks.forEachIndexed { index, block ->
                Staggered(index) {
                    BlockView(
                        block = block,
                        onDrillDown = onDrillDown,
                        activePackId = activePackId,
                        whatIfState = whatIfState,
                        onWhatIfShocksChange = onWhatIfShocksChange,
                        onWhatIfHorizonChange = onWhatIfHorizonChange,
                        onWhatIfAuditWithAi = onWhatIfAuditWithAi,
                        onWhatIfRetry = onWhatIfRetry,
                        scorecardState = scorecardState,
                        onScorecardHorizonChange = onScorecardHorizonChange,
                        onApproveCalibration = onApproveCalibration,
                        onRejectCalibration = onRejectCalibration,
                        onRefreshScorecard = onRefreshScorecard
                    )
                }
            }

            if (card.limitations.isNotEmpty()) {
                Text(
                    text = card.limitations.joinToString(" "),
                    style = MaterialTheme.typography.bodySmall,
                    color = TextMuted
                )
            }

            if (card.actions.isNotEmpty()) {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    card.actions.forEach { action ->
                        val primary = action.variant == "primary"
                        val enriched = action.copy(
                            contextSummary = action.contextSummary ?: cardContextSummary
                        )
                        val isArmed = armedActionId == action.actionId
                        val formattedLabel = action.label.replace(" L)", "\u00A0L)")

                        if (isArmed) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                AuraGhostButton(
                                    text = "Cancelar",
                                    onClick = { armedActionId = null },
                                    modifier = Modifier.weight(0.85f),
                                    tint = TextSecondary
                                )
                                AuraGradientButton(
                                    text = "Confirmar TEE",
                                    onClick = {
                                        haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                                        armedActionId = null
                                        onAction(enriched)
                                    },
                                    modifier = Modifier.weight(1.35f)
                                )
                            }
                        } else {
                            val click = {
                                if (enriched.isHandoffAction() || !enriched.requiresConfirmation) {
                                    onAction(enriched)
                                } else {
                                    haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                                    armedActionId = action.actionId
                                }
                            }
                            if (primary) {
                                AuraGradientButton(formattedLabel, click, Modifier.fillMaxWidth())
                            } else {
                                AuraGhostButton(formattedLabel, click, Modifier.fillMaxWidth())
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun CardHeader(card: GenUiCard, companionText: String? = null) {
    val isCritical = card.severity.equals("critical", true) || card.severity.equals("danger", true)
    val isWarning = card.severity.equals("warning", true)
    val titleUpper = card.title.uppercase()
    val contextBadgeText = when {
        isCritical -> "ALERTA CRÍTICO"
        titleUpper.contains("SEFAZ") || titleUpper.contains("DANFE") || titleUpper.contains("FISCAL") -> "AUDITORIA FISCAL"
        titleUpper.contains("TANQUE") || titleUpper.contains("LMC") -> "TELEMETRIA DE PISTA"
        isWarning -> "ATENÇÃO OPERACIONAL"
        else -> "AURA INTELIGÊNCIA"
    }
    val contextBadgeColor = when {
        isCritical -> StatusDanger
        isWarning -> StatusWarning
        else -> AuraCyan
    }

    // Quando ja existe texto narrativo acoplado acima do card, evita duplicar o paragrafo longo de diagnostico
    val hasCompanionNarrative = !companionText.isNullOrBlank() && companionText.trim().length >= 30
    val headerSummary = remember(card.diagnosis, card.subtitle, hasCompanionNarrative) {
        if (hasCompanionNarrative) {
            card.subtitle?.takeIf { it.isNotBlank() && it.length <= 120 }
        } else {
            (card.diagnosis ?: card.subtitle)?.takeIf { it.isNotBlank() }
        }
    }

    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            StatusDot(color = contextBadgeColor, pulsing = isCritical, size = 7.dp)
            AuraPill(text = contextBadgeText, color = contextBadgeColor)
            Spacer(Modifier.weight(1f))
            card.confidence?.let {
                AuraPill(
                    text = "${(it * 100).toInt()}% confiança",
                    color = AuraEmerald
                )
            }
        }
        Text(
            text = card.title,
            style = MaterialTheme.typography.headlineSmall.copy(lineHeight = 28.sp),
            color = TextPrimary
        )
        headerSummary?.let {
            Text(
                text = it,
                style = MaterialTheme.typography.bodyMedium.copy(lineHeight = 20.sp),
                color = TextSecondary
            )
        }
    }
}

@Composable
private fun Staggered(index: Int, content: @Composable () -> Unit) {
    var visible by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) {
        delay(index * 70L)
        visible = true
    }
    AnimatedVisibility(
        visible = visible,
        enter = fadeIn(tween(350)) + slideInVertically(tween(350, easing = FastOutSlowInEasing)) { it / 8 }
    ) { content() }
}

@Composable
private fun BlockView(
    block: GenUiBlock,
    onDrillDown: (String) -> Unit,
    activePackId: String = AuraDomainAdapter.PACK_FUEL,
    whatIfState: WhatIfUiState? = null,
    onWhatIfShocksChange: ((ShockVectorDto) -> Unit)? = null,
    onWhatIfHorizonChange: ((Int) -> Unit)? = null,
    onWhatIfAuditWithAi: ((String) -> Unit)? = null,
    onWhatIfRetry: (() -> Unit)? = null,
    scorecardState: BacktestScorecardUiState? = null,
    onScorecardHorizonChange: ((Int) -> Unit)? = null,
    onApproveCalibration: (() -> Unit)? = null,
    onRejectCalibration: (() -> Unit)? = null,
    onRefreshScorecard: (() -> Unit)? = null
) {
    when (block) {
        is GenUiBlock.KpiGrid -> KpiGridBlock(block, onDrillDown)
        is GenUiBlock.Comparison -> ComparisonBlock(block, onDrillDown)
        is GenUiBlock.Ranking -> RankingBlock(block, onDrillDown)
        is GenUiBlock.Timeline -> TimelineBlock(block)
        is GenUiBlock.AlertCallout -> AlertBlock(block.alert)
        is GenUiBlock.Tanks -> {
            if (isTankTileAllowedForPack(activePackId)) {
                TanksBlock(block, onDrillDown)
            } else {
                NoteBlock(
                    GenUiBlock.Note(
                        title = block.title ?: "Visão de Estoque",
                        text = "Visualização de tanques físicos disponível apenas para o domínio Postos & Conveniência."
                    )
                )
            }
        }
        is GenUiBlock.Note -> NoteBlock(block)
        is GenUiBlock.WhatIfSimulator -> {
            if (whatIfState != null && onWhatIfShocksChange != null && onWhatIfHorizonChange != null) {
                WhatIfSimulatorCard(
                    state = whatIfState,
                    onShocksChange = onWhatIfShocksChange,
                    onHorizonChange = onWhatIfHorizonChange,
                    onAuditWithAi = onWhatIfAuditWithAi ?: onDrillDown,
                    onRetry = onWhatIfRetry ?: {}
                )
            } else {
                WhatIfSimulatorBlock(block, onDrillDown)
            }
        }
        is GenUiBlock.RealizedRoiScorecard -> {
            if (scorecardState != null && scorecardState.scorecard != null && onScorecardHorizonChange != null) {
                RealizedRoiScorecardCard(
                    state = scorecardState,
                    onSelectHorizon = onScorecardHorizonChange,
                    onApproveCalibration = onApproveCalibration ?: {},
                    onRejectCalibration = onRejectCalibration ?: {},
                    onRefresh = onRefreshScorecard ?: {}
                )
            } else {
                RealizedRoiScorecardBlock(block)
            }
        }
        is GenUiBlock.McpActionConfirmation -> McpActionConfirmationBlock(block)
    }
}

@Composable
private fun BlockTitle(title: String?, subtitle: String?) {
    if (title == null && subtitle == null) return
    Column(Modifier.padding(bottom = 8.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
        title?.let { SectionLabel(it) }
        subtitle?.let { Text(it, style = MaterialTheme.typography.bodySmall, color = TextMuted) }
    }
}

// ---------------------------------------------------------------- KPIs (Hierarquia 1-3-N)

@Composable
private fun KpiGridBlock(block: GenUiBlock.KpiGrid, onDrillDown: (String) -> Unit) {
    Column {
        BlockTitle(block.title, block.subtitle)
        if (block.kpis.size >= 3) {
            val hero = block.kpis.first()
            val supporting = block.kpis.drop(1).take(3)
            val rest = block.kpis.drop(4)
            HeroKpiTile(
                kpi = hero,
                onClick = {
                    onDrillDown("Explique em detalhes o indicador '${hero.label}' (${hero.value}${hero.delta?.let { " com variação $it" } ?: ""}) e sugira ações operacionais.")
                }
            )
            Spacer(Modifier.height(10.dp))
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(IntrinsicSize.Max)
                    .clip(RoundedCornerShape(14.dp))
                    .background(ObsidianLow)
                    .border(1.dp, BorderHairline, RoundedCornerShape(14.dp))
                    .padding(vertical = 10.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                supporting.forEachIndexed { idx, kpi ->
                    Column(
                        modifier = Modifier
                            .weight(1f)
                            .clickable {
                                onDrillDown("Detalhe o indicador '${kpi.label}' (${kpi.value}).")
                            }
                            .padding(horizontal = 10.dp),
                        verticalArrangement = Arrangement.spacedBy(3.dp)
                    ) {
                        Text(
                            text = kpi.label,
                            style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp),
                            color = TextMuted,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                        Text(
                            text = kpi.value.replace(" L", "\u00A0L").replace(" h", "\u00A0h"),
                            style = AuraTypographyExt.kpiCompact,
                            color = TextPrimary,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                        kpi.delta?.let { d ->
                            Text(
                                text = d,
                                style = AuraTypographyExt.monoAudit.copy(fontSize = 10.sp),
                                color = statusColor(kpi.status),
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis
                            )
                        }
                    }
                    if (idx < supporting.lastIndex) {
                        Box(
                            modifier = Modifier
                                .width(1.dp)
                                .fillMaxHeight()
                                .background(BorderHairline)
                        )
                    }
                }
            }
            if (rest.isNotEmpty()) {
                Spacer(Modifier.height(10.dp))
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    rest.chunked(2).forEach { pair ->
                        Row(
                            Modifier.fillMaxWidth().height(IntrinsicSize.Max),
                            horizontalArrangement = Arrangement.spacedBy(10.dp)
                        ) {
                            pair.forEach { kpi ->
                                KpiTile(
                                    kpi = kpi,
                                    onClick = { onDrillDown("Explique o indicador '${kpi.label}' (${kpi.value}).") },
                                    modifier = Modifier.weight(1f).fillMaxHeight()
                                )
                            }
                        }
                    }
                }
            }
            return
        }

        val rows = remember(block.kpis) {
            val result = mutableListOf<List<GenUiKpi>>()
            var pair = mutableListOf<GenUiKpi>()
            for (kpi in block.kpis) {
                val isWide = kpi.value.trim().length > 16 || (kpi.subtext?.length ?: 0) > 28
                if (isWide) {
                    if (pair.isNotEmpty()) {
                        result.add(pair)
                        pair = mutableListOf()
                    }
                    result.add(listOf(kpi))
                } else {
                    pair.add(kpi)
                    if (pair.size == 2) {
                        result.add(pair)
                        pair = mutableListOf()
                    }
                }
            }
            if (pair.isNotEmpty()) result.add(pair)
            result
        }

        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            rows.forEach { rowItems ->
                if (rowItems.size == 1) {
                    val kpi = rowItems.first()
                    KpiTile(
                        kpi = kpi,
                        onClick = {
                            onDrillDown("Explique em detalhes o indicador '${kpi.label}' (${kpi.value}${kpi.delta?.let { " com variação $it" } ?: ""}) e sugira ações operacionais.")
                        },
                        modifier = Modifier.fillMaxWidth()
                    )
                } else {
                    Row(
                        Modifier
                            .fillMaxWidth()
                            .height(IntrinsicSize.Max),
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        rowItems.forEach { kpi ->
                            KpiTile(
                                kpi = kpi,
                                onClick = {
                                    onDrillDown("Explique em detalhes o indicador '${kpi.label}' (${kpi.value}${kpi.delta?.let { " com variação $it" } ?: ""}) e sugira ações operacionais.")
                                },
                                modifier = Modifier.weight(1f).fillMaxHeight()
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun HeroKpiTile(kpi: GenUiKpi, onClick: () -> Unit) {
    val haptic = LocalHapticFeedback.current
    val color = statusColor(kpi.status)
    val formattedValue = kpi.value.replace(" L", "\u00A0L").replace(" h", "\u00A0h").trim()

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(ObsidianLow)
            .border(1.dp, color.copy(alpha = 0.30f), RoundedCornerShape(16.dp))
            .clickable {
                haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                onClick()
            }
            .padding(14.dp),
        verticalArrangement = Arrangement.spacedBy(6.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                StatusDot(color = color, size = 7.dp)
                Text(
                    text = kpi.label.uppercase(),
                    style = MaterialTheme.typography.labelSmall.copy(letterSpacing = 0.6.sp),
                    color = TextSecondary
                )
            }
            kpi.delta?.let { d ->
                AuraPill(text = d, color = color)
            }
        }
        Text(
            text = formattedValue,
            style = AuraTypographyExt.kpiHero,
            color = TextPrimary,
            maxLines = 2
        )
        kpi.subtext?.let {
            Text(
                text = it.replace(" L", "\u00A0L").replace(" h", "\u00A0h"),
                style = MaterialTheme.typography.bodySmall,
                color = TextMuted,
                maxLines = 2
            )
        }
    }
}

@Composable
private fun KpiTile(kpi: GenUiKpi, onClick: () -> Unit, modifier: Modifier = Modifier) {
    val haptic = LocalHapticFeedback.current
    val color = statusColor(kpi.status)
    val formattedValue = kpi.value.replace(" L", "\u00A0L").replace(" h", "\u00A0h").trim()
    val valueLen = formattedValue.length
    val valueSize = when {
        valueLen <= 7 -> 22.sp
        valueLen <= 14 -> 17.sp
        else -> 15.sp
    }
    val valueLineHeight = when {
        valueLen <= 7 -> 26.sp
        valueLen <= 14 -> 21.sp
        else -> 20.sp
    }
    val valueMaxLines = when {
        valueLen <= 7 -> 1
        valueLen <= 14 -> 2
        else -> 4
    }

    Column(
        modifier
            .clip(RoundedCornerShape(16.dp))
            .background(ObsidianLow)
            .border(1.dp, GlassBorderSoft, RoundedCornerShape(16.dp))
            .clickable {
                haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                onClick()
            }
            .padding(13.dp),
        verticalArrangement = Arrangement.spacedBy(6.dp)
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            if (kpi.status != null) {
                StatusDot(color = color, size = 6.dp)
            }
            Text(
                text = kpi.label,
                style = MaterialTheme.typography.labelSmall.copy(lineHeight = 14.sp),
                color = TextSecondary,
                maxLines = 2
            )
        }
        Text(
            text = formattedValue,
            style = AuraTypographyExt.kpiValue.copy(
                fontSize = valueSize,
                lineHeight = valueLineHeight,
                fontWeight = FontWeight.SemiBold
            ),
            color = TextPrimary,
            maxLines = valueMaxLines
        )
        kpi.delta?.let { d ->
            val icon: ImageVector? = when (kpi.trend) {
                "up" -> Icons.Filled.ArrowUpward
                "down" -> Icons.Filled.ArrowDownward
                else -> null
            }
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                icon?.let { Icon(it, null, tint = color, modifier = Modifier.size(13.dp)) }
                Text(
                    text = d,
                    style = MaterialTheme.typography.labelSmall,
                    color = color,
                    fontWeight = FontWeight.SemiBold
                )
            }
        }
        kpi.subtext?.let {
            Text(
                text = it.replace(" L", "\u00A0L").replace(" h", "\u00A0h"),
                style = MaterialTheme.typography.bodySmall,
                color = TextMuted,
                maxLines = 3
            )
        }
    }
}

// ---------------------------------------------------------------- Comparativo

@Composable
private fun ComparisonBlock(block: GenUiBlock.Comparison, onDrillDown: (String) -> Unit) {
    val haptic = LocalHapticFeedback.current
    Column {
        BlockTitle(block.title, block.subtitle)
        Column(
            Modifier
                .clip(RoundedCornerShape(16.dp))
                .background(ObsidianLow)
                .border(1.dp, GlassBorderSoft, RoundedCornerShape(16.dp))
        ) {
            block.rows.forEachIndexed { i, row ->
                Row(
                    Modifier
                        .fillMaxWidth()
                        .clickable {
                            haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                            onDrillDown("Analise a discrepância no comparativo '${row.name}': Nosso (${row.primary}) vs Mercado (${row.secondary})${row.gap?.let { " com gap de $it" } ?: ""}. O que a AURA recomenda?")
                        }
                        .padding(horizontal = 14.dp, vertical = 12.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                        Text(row.name, style = MaterialTheme.typography.titleSmall, color = TextPrimary)
                        Text(
                            "Mercado ${row.secondary}",
                            style = MaterialTheme.typography.bodySmall,
                            color = TextMuted
                        )
                    }
                    Spacer(Modifier.width(12.dp))
                    Column(horizontalAlignment = Alignment.End, verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(row.primary, style = MaterialTheme.typography.titleMedium, color = TextPrimary, textAlign = TextAlign.End)
                        row.gap?.let { AuraPill(it, statusColor(row.status)) }
                    }
                }
                if (i < block.rows.lastIndex) {
                    Box(Modifier.fillMaxWidth().height(1.dp).background(OutlineSoft))
                }
            }
        }
    }
}

// ---------------------------------------------------------------- Ranking

@Composable
private fun RankingBlock(block: GenUiBlock.Ranking, onDrillDown: (String) -> Unit) {
    val haptic = LocalHapticFeedback.current
    Column {
        BlockTitle(block.title, block.subtitle)
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            block.items.forEach { item ->
                Row(
                    Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(14.dp))
                        .background(ObsidianLow)
                        .border(1.dp, GlassBorderSoft, RoundedCornerShape(14.dp))
                        .clickable {
                            haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                            onDrillDown("Detalhe o desempenho de '${item.title}' (Posição #${item.rank}, Total: ${item.value}) no ranking da pista.")
                        }
                        .padding(12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Box(
                        Modifier
                            .size(32.dp)
                            .clip(CircleShape)
                            .background(
                                if (item.rank == 1) AuroraBrush else Brush.linearGradient(listOf(ObsidianBright, ObsidianBright))
                            ),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "${item.rank}",
                            style = MaterialTheme.typography.labelMedium,
                            color = if (item.rank == 1) ObsidianBase else TextSecondary,
                            fontWeight = FontWeight.Bold
                        )
                    }
                    Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                        Text(item.title, style = MaterialTheme.typography.titleSmall, color = TextPrimary, maxLines = 2)
                        item.subtitle?.let { Text(it, style = MaterialTheme.typography.bodySmall, color = TextMuted, maxLines = 2) }
                    }
                    Spacer(Modifier.width(4.dp))
                    Column(horizontalAlignment = Alignment.End, verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(item.value, style = MaterialTheme.typography.titleMedium, color = TextPrimary, textAlign = TextAlign.End)
                        item.tag?.let { AuraPill(it, statusColor(item.status)) }
                    }
                }
            }
        }
    }
}

// ---------------------------------------------------------------- Timeline

@Composable
private fun TimelineBlock(block: GenUiBlock.Timeline) {
    Column {
        BlockTitle(block.title, block.subtitle)
        Column {
            block.events.forEachIndexed { i, e ->
                Row(Modifier.height(IntrinsicSize.Min), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Box(Modifier.padding(top = 4.dp)) {
                            StatusDot(statusColor(e.status), size = 9.dp)
                        }
                        if (i < block.events.lastIndex) {
                            Box(
                                Modifier
                                    .width(2.dp)
                                    .weight(1f)
                                    .background(
                                        Brush.verticalGradient(
                                            listOf(statusColor(e.status).copy(alpha = 0.5f), OutlineSoft)
                                        )
                                    )
                            )
                        }
                    }
                    Column(Modifier.padding(bottom = 14.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                        Text(e.timestamp, style = MaterialTheme.typography.labelSmall, color = TextMuted)
                        Text(e.title, style = MaterialTheme.typography.titleSmall, color = TextPrimary)
                        e.description?.let { Text(it, style = MaterialTheme.typography.bodySmall, color = TextSecondary) }
                    }
                }
            }
        }
    }
}

// ---------------------------------------------------------------- Alerta

@Composable
private fun AlertBlock(alert: GenUiAlert) {
    val color = when (alert.severity.lowercase()) {
        "critical", "danger" -> StatusDanger
        "warning" -> StatusWarning
        "success" -> AuraEmerald
        else -> AuraCyan
    }
    val icon = when (alert.severity.lowercase()) {
        "critical", "danger" -> Icons.Filled.ErrorOutline
        "warning" -> Icons.Filled.WarningAmber
        else -> Icons.Filled.Info
    }
    Row(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(color.copy(alpha = 0.10f))
            .border(1.dp, color.copy(alpha = 0.35f), RoundedCornerShape(16.dp))
            .padding(14.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalAlignment = Alignment.Top
    ) {
        Icon(icon, null, tint = color, modifier = Modifier.padding(top = 2.dp).size(20.dp))
        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(alert.title, style = MaterialTheme.typography.titleSmall.copy(lineHeight = 19.sp), color = color)
            if (alert.message.isNotBlank()) {
                Text(alert.message, style = MaterialTheme.typography.bodyMedium.copy(lineHeight = 20.sp), color = TextSecondary)
            }
        }
    }
}

@Composable
private fun NoteBlock(block: GenUiBlock.Note) {
    Column {
        BlockTitle(block.title, null)
        val paragraphs = remember(block.text) {
            block.text.split("\n").map { it.trim() }.filter { it.isNotBlank() }
        }
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .height(IntrinsicSize.Min)
                .clip(RoundedCornerShape(16.dp))
                .background(ObsidianLow)
                .border(1.dp, GlassBorderSoft, RoundedCornerShape(16.dp))
        ) {
            Box(
                modifier = Modifier
                    .width(3.dp)
                    .fillMaxHeight()
                    .background(AuraCyan.copy(alpha = 0.8f))
            )
            Column(
                verticalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier
                    .weight(1f)
                    .padding(14.dp)
            ) {
                paragraphs.forEach { paragraph ->
                    val colonIndex = paragraph.indexOf(':')
                    val hasShortPrefix = colonIndex in 3..32
                    if (hasShortPrefix) {
                        val prefix = paragraph.substring(0, colonIndex + 1)
                        val body = paragraph.substring(colonIndex + 1).trimStart()
                        Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                            Text(
                                text = prefix,
                                style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold),
                                color = AuraCyan
                            )
                            Text(
                                text = body,
                                style = MaterialTheme.typography.bodyMedium.copy(lineHeight = 21.sp),
                                color = TextSecondary
                            )
                        }
                    } else {
                        Text(
                            text = paragraph,
                            style = MaterialTheme.typography.bodyMedium.copy(lineHeight = 21.sp),
                            color = TextSecondary
                        )
                    }
                }
            }
        }
    }
}

// ---------------------------------------------------------------- Core P1.3: What-If, Realized ROI & MCP HITL

@Composable
private fun WhatIfSimulatorBlock(
    block: GenUiBlock.WhatIfSimulator,
    onDrillDown: (String) -> Unit
) {
    val haptic = LocalHapticFeedback.current
    var priceDelta by remember(block) { mutableFloatStateOf(block.initialPriceDeltaPct.toFloat()) }
    var volumeDelta by remember(block) { mutableFloatStateOf(block.initialVolumeDeltaPct.toFloat()) }
    var batchDelta by remember(block) { mutableFloatStateOf(block.initialBatchDeltaPct.toFloat()) }

    // Cálculo determinístico instantâneo local (espelha POST /api/v1/aura/what-if/simulate)
    val effectiveVolumeFactor = 1.0 + (volumeDelta / 100.0) + ((priceDelta / 100.0) * block.elasticityFactor * 0.35)
    val marginBoostFactor = 1.0 + (priceDelta / 100.0) * (100.0 / block.baseMarginPct.coerceAtLeast(5.0)) * 0.45 + (batchDelta / 100.0) * 0.12
    val simulatedProfit = (block.baseMonthlyProfit * effectiveVolumeFactor * marginBoostFactor).coerceAtLeast(0.0)
    val deltaProfit = simulatedProfit - block.baseMonthlyProfit
    val deltaColor = if (deltaProfit >= 0) AuraEmerald else StatusDanger
    val deltaSign = if (deltaProfit >= 0) "+" else "-"
    val maxBar = maxOf(block.baseMonthlyProfit, simulatedProfit, 1.0)

    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        BlockTitle(block.title ?: "Simulador Interativo What-If", block.productScope)

        // Hero KPI do Impacto Simulado
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(16.dp))
                .background(ObsidianLow)
                .border(1.dp, AuraPurple.copy(alpha = 0.35f), RoundedCornerShape(16.dp))
                .padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "IMPACTO NO LUCRO MENSAL",
                    style = MaterialTheme.typography.labelSmall.copy(letterSpacing = 0.6.sp),
                    color = TextSecondary
                )
                AuraPill(
                    text = "${deltaSign}R$ ${GenUiParser.fmtNumber(kotlin.math.abs(deltaProfit))}",
                    color = deltaColor
                )
            }
            Text(
                text = "R$ ${GenUiParser.fmtNumber(simulatedProfit)}",
                style = AuraTypographyExt.kpiHero,
                color = TextPrimary
            )
            // Micro-barras comparativas Base (Cyan) vs Simulado (Violet)
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                ComparisonBarRow("Base", "R$ ${GenUiParser.fmtNumber(block.baseMonthlyProfit)}", (block.baseMonthlyProfit / maxBar).toFloat(), AuraCyan)
                ComparisonBarRow("Simulado", "R$ ${GenUiParser.fmtNumber(simulatedProfit)}", (simulatedProfit / maxBar).toFloat(), AuraPurple)
            }
        }

        // Sliders Táteis
        WhatIfSliderRow(
            label = "Ajuste de Preço",
            value = priceDelta,
            range = -10f..10f,
            suffix = "%",
            accent = AuraCyan,
            onValueChange = {
                if (it.toInt() != priceDelta.toInt()) {
                    haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                }
                priceDelta = it
            }
        )
        WhatIfSliderRow(
            label = "Variação de Volume",
            value = volumeDelta,
            range = -20f..25f,
            suffix = "%",
            accent = AuraPurple,
            onValueChange = {
                if (it.toInt() != volumeDelta.toInt()) {
                    haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                }
                volumeDelta = it
            }
        )
        WhatIfSliderRow(
            label = "Otimização de Lote",
            value = batchDelta,
            range = -15f..30f,
            suffix = "%",
            accent = AuraEmerald,
            onValueChange = {
                if (it.toInt() != batchDelta.toInt()) {
                    haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                }
                batchDelta = it
            }
        )

        AuraGhostButton(
            text = "Validar Cenário no Motor Python",
            onClick = {
                onDrillDown(
                    "Valide no motor determinístico o cenário What-If para ${block.productScope}: " +
                        "preço ${"%+.1f".format(priceDelta)}%, volume ${"%+.1f".format(volumeDelta)}%, lote ${"%+.1f".format(batchDelta)}%."
                )
            },
            modifier = Modifier.fillMaxWidth(),
            tint = AuraPurple
        )
    }
}

@Composable
private fun ComparisonBarRow(label: String, valueText: String, fraction: Float, color: Color) {
    val animated by animateFloatAsState(
        targetValue = fraction.coerceIn(0.05f, 1f),
        animationSpec = tween(220),
        label = "whatIfBar"
    )
    Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(label, style = MaterialTheme.typography.labelSmall, color = TextMuted)
            Text(valueText, style = AuraTypographyExt.monoAudit, color = TextSecondary)
        }
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(6.dp)
                .clip(RoundedCornerShape(50))
                .background(ObsidianBase)
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth(animated)
                    .fillMaxHeight()
                    .clip(RoundedCornerShape(50))
                    .background(color)
            )
        }
    }
}

@Composable
private fun WhatIfSliderRow(
    label: String,
    value: Float,
    range: ClosedFloatingPointRange<Float>,
    suffix: String,
    accent: Color,
    onValueChange: (Float) -> Unit
) {
    Column {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(label, style = MaterialTheme.typography.labelSmall, color = TextSecondary)
            Text(
                text = "${"%+.1f".format(value)}$suffix",
                style = AuraTypographyExt.monoAudit,
                color = accent
            )
        }
        Slider(
            value = value,
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
private fun RealizedRoiScorecardBlock(block: GenUiBlock.RealizedRoiScorecard) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        BlockTitle(block.title ?: "Outcome Tracker • ROI Realizado", "Impacto financeiro auditado em R$")
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(16.dp))
                .background(ObsidianLow)
                .border(1.dp, AuraEmerald.copy(alpha = 0.35f), RoundedCornerShape(16.dp))
                .padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "ROI LÍQUIDO ACUMULADO",
                    style = MaterialTheme.typography.labelSmall.copy(letterSpacing = 0.6.sp),
                    color = AuraEmerald
                )
                block.roiMultiple?.let { AuraPill(text = it, color = AuraEmerald) }
            }
            Text(
                text = block.totalRoiValue,
                style = AuraTypographyExt.kpiHero,
                color = AuraEmerald
            )
        }

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .height(IntrinsicSize.Max)
                .clip(RoundedCornerShape(14.dp))
                .background(ObsidianLow)
                .border(1.dp, BorderHairline, RoundedCornerShape(14.dp))
                .padding(vertical = 10.dp)
        ) {
            listOf(
                "Vazamentos" to block.leaksStopped,
                "Ganho Margem" to block.marginGain,
                "Captura" to block.captureRatePct
            ).forEachIndexed { idx, (label, v) ->
                Column(
                    modifier = Modifier.weight(1f).padding(horizontal = 10.dp),
                    verticalArrangement = Arrangement.spacedBy(2.dp)
                ) {
                    Text(label, style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp), color = TextMuted)
                    Text(v, style = AuraTypographyExt.kpiCompact, color = TextPrimary, maxLines = 1, overflow = TextOverflow.Ellipsis)
                }
                if (idx < 2) {
                    Box(Modifier.width(1.dp).fillMaxHeight().background(BorderHairline))
                }
            }
        }

        if (block.auditedVouchers.isNotEmpty()) {
            TimelineBlock(GenUiBlock.Timeline("Últimos Action Vouchers", null, block.auditedVouchers))
        }
    }
}

@Composable
private fun McpActionConfirmationBlock(block: GenUiBlock.McpActionConfirmation) {
    var remainingSec by remember(block) { mutableIntStateOf(block.ttlSeconds.coerceAtLeast(0)) }
    LaunchedEffect(block) {
        while (remainingSec > 0) {
            delay(1000L)
            remainingSec--
        }
    }
    val expired = remainingSec <= 0

    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        BlockTitle(block.title ?: "Governança MCP • Human-in-the-Loop", "${block.targetSystem} • ${block.operation}")
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            AuraPill(
                text = if (block.reversible) "Reversível" else "Irreversível",
                color = if (block.reversible) AuraCyan else StatusWarning
            )
            AuraPill(
                text = if (expired) "Proposta Expirada" else "TTL ${remainingSec}s",
                color = if (expired) StatusDanger else AuraEmerald
            )
        }
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(14.dp))
                .background(ObsidianLow)
                .border(1.dp, BorderHairline, RoundedCornerShape(14.dp))
                .padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            Text("ANTES", style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp), color = TextMuted)
            Text(block.beforeSummary, style = AuraTypographyExt.monoAudit, color = TextSecondary)
            Box(Modifier.fillMaxWidth().height(1.dp).background(BorderHairline))
            Text("DEPOIS", style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp), color = AuraCyan)
            Text(block.afterSummary, style = AuraTypographyExt.monoAudit, color = TextPrimary)
            block.voucherHash?.let { hash ->
                Spacer(Modifier.height(2.dp))
                Text("HMAC Voucher: ${hash.take(18)}...", style = AuraTypographyExt.monoAudit.copy(fontSize = 10.sp), color = AuraEmerald)
            }
        }
    }
}

// ---------------------------------------------------------------- Tanques Verticais Deluxe

@Composable
private fun TanksBlock(block: GenUiBlock.Tanks, onDrillDown: (String) -> Unit) {
    var inspectingTank by remember { mutableStateOf<GenUiTank?>(null) }

    Column {
        BlockTitle(
            block.title,
            if (block.hiddenInactive > 0) "${block.hiddenInactive} tanques inativos ocultos" else "Toque para inspecionar lastro e autonomia"
        )
        LazyRow(
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            contentPadding = PaddingValues(horizontal = 2.dp, vertical = 4.dp)
        ) {
            items(block.tanks, key = { it.code + it.fuel }) { tank ->
                TankTile(tank = tank, onClick = { inspectingTank = tank })
            }
        }
    }

    inspectingTank?.let { tank ->
        TankDetailModal(
            tank = tank,
            onDismiss = { inspectingTank = null },
            onDrillDown = onDrillDown
        )
    }
}

private fun fuelColor(fuel: String): Color = when {
    fuel.contains("GASOLINA", true) && fuel.contains("ADIT", true) -> Color(0xFFF59E0B)
    fuel.contains("GASOLINA", true) -> Color(0xFFFBBF24)
    fuel.contains("ETANOL", true) -> Color(0xFF34D399)
    fuel.contains("DIESEL", true) -> Color(0xFF60A5FA)
    else -> AuraCyan
}

@Composable
private fun TankTile(tank: GenUiTank, onClick: () -> Unit) {
    val haptic = LocalHapticFeedback.current
    val target = (tank.occupancyPct / 100.0).coerceIn(0.0, 1.0).toFloat()
    val fill by animateFloatAsState(
        targetValue = target,
        animationSpec = tween(1200, easing = FastOutSlowInEasing),
        label = "tankFill"
    )
    val color = if (tank.critical) StatusDanger else fuelColor(tank.fuel)

    // Animacao suave de onda do líquido
    val waveTransition = rememberInfiniteTransition(label = "tankWave")
    val wavePhase by waveTransition.animateFloat(
        initialValue = 0f,
        targetValue = 2f * Math.PI.toFloat(),
        animationSpec = infiniteRepeatable(tween(2400, easing = LinearEasing)),
        label = "wavePhase"
    )

    Row(
        Modifier
            .widthIn(min = 210.dp)
            .clip(RoundedCornerShape(18.dp))
            .background(ObsidianLow)
            .border(
                1.dp,
                if (tank.critical) StatusDanger.copy(alpha = 0.5f) else GlassBorderSoft,
                RoundedCornerShape(18.dp)
            )
            .clickable {
                haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                onClick()
            }
            .padding(14.dp),
        horizontalArrangement = Arrangement.spacedBy(14.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        // Coluna Vertical do Tanque (Cilindro com líquido animado e reflexo de vidro)
        Canvas(Modifier.size(width = 44.dp, height = 98.dp)) {
            val corner = CornerRadius(12.dp.toPx())
            val roundRectPath = Path().apply {
                addRoundRect(
                    RoundRect(
                        rect = Rect(Offset.Zero, size),
                        cornerRadius = corner
                    )
                )
            }

            // Fundo escuro com gradiente de profundidade do tubo de vidro
            drawRoundRect(
                brush = Brush.verticalGradient(
                    listOf(Color(0xFF0F1726), Color(0xFF060910))
                ),
                size = size,
                cornerRadius = corner
            )

            // Marcadores de medicao no vidro (25%, 50%, 75%)
            for (pct in listOf(0.25f, 0.50f, 0.75f)) {
                val tickY = size.height * (1f - pct)
                drawLine(
                    color = Color(0x30FFFFFF),
                    start = Offset(size.width - 5.dp.toPx(), tickY),
                    end = Offset(size.width, tickY),
                    strokeWidth = 1.dp.toPx()
                )
            }

            // O conteudo liquido e recortado estritamente pelas bordas arredondadas do cilindro
            clipPath(roundRectPath) {
                val fillH = (size.height * fill).coerceIn(0f, size.height)
                if (fillH > 0f) {
                    val topY = size.height - fillH
                    val path = Path().apply {
                        moveTo(0f, size.height)
                        lineTo(0f, topY)
                        val waveAmp = if (fillH > 8f && fillH < size.height - 8f) 2.2f else 0f
                        val steps = 20
                        for (i in 1..steps) {
                            val px = size.width * (i.toFloat() / steps)
                            val py = topY + sin(wavePhase + (i * 0.4f)) * waveAmp
                            lineTo(px, py)
                        }
                        lineTo(size.width, size.height)
                        close()
                    }

                    drawPath(
                        path = path,
                        brush = Brush.verticalGradient(
                            colors = listOf(color, color.copy(alpha = 0.55f)),
                            startY = topY,
                            endY = size.height
                        )
                    )

                    // Brilho na superficie do liquido
                    drawLine(
                        color = Color.White.copy(alpha = 0.65f),
                        start = Offset(0f, topY),
                        end = Offset(size.width, topY),
                        strokeWidth = 1.5.dp.toPx()
                    )
                }

                // Marcador da reserva critica de seguranca (15%)
                val reserveY = size.height * 0.85f
                drawLine(
                    color = StatusDanger.copy(alpha = 0.85f),
                    start = Offset(0f, reserveY),
                    end = Offset(size.width, reserveY),
                    strokeWidth = 1.5.dp.toPx(),
                    cap = StrokeCap.Round
                )
            }

            // Reflexo de luz na curvatura esquerda do vidro
            drawLine(
                brush = Brush.verticalGradient(
                    listOf(GlassHighlight, Color.Transparent, GlassHighlight)
                ),
                start = Offset(4.dp.toPx(), 6.dp.toPx()),
                end = Offset(4.dp.toPx(), size.height - 6.dp.toPx()),
                strokeWidth = 1.5.dp.toPx()
            )

            // Reflexo suave na curvatura direita
            drawLine(
                brush = Brush.verticalGradient(
                    listOf(Color(0x18FFFFFF), Color.Transparent, Color(0x18FFFFFF))
                ),
                start = Offset(size.width - 3.dp.toPx(), 8.dp.toPx()),
                end = Offset(size.width - 3.dp.toPx(), size.height - 8.dp.toPx()),
                strokeWidth = 1.dp.toPx()
            )

            // Borda de vidro exterior polida
            drawRoundRect(
                color = Color(0x38FFFFFF),
                size = size,
                cornerRadius = corner,
                style = Stroke(1.2.dp.toPx())
            )
        }

        // Informacoes e Telemetria do Tanque
        val fuelTitle = tank.fuel.split(" ").joinToString(" ") { word ->
            word.lowercase().replaceFirstChar(Char::titlecase)
        }
        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = "T-${tank.code}",
                    style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                    color = color
                )
                Spacer(Modifier.width(6.dp))
                if (tank.critical) {
                    AuraPill(text = "CRÍTICO", color = StatusDanger)
                }
            }
            Text(
                text = fuelTitle,
                style = MaterialTheme.typography.titleSmall,
                color = TextPrimary,
                maxLines = 1
            )
            Text(
                text = "${"%.0f".format(tank.occupancyPct)}%",
                style = MaterialTheme.typography.headlineSmall.copy(
                    fontFamily = NewsreaderFamily,
                    fontSize = 26.sp,
                    fontWeight = FontWeight.SemiBold
                ),
                color = color
            )
            Text(
                text = "${GenUiParser.fmtNumber(tank.balanceL)} / ${GenUiParser.fmtNumber(tank.capacityL)}\u00A0L",
                style = MaterialTheme.typography.bodySmall,
                color = TextSecondary
            )
            tank.autonomyHours?.let {
                Text(
                    text = "Autonomia ${"%.1f".format(it)}\u00A0h",
                    style = MaterialTheme.typography.labelSmall,
                    color = if (tank.critical) StatusDanger else TextMuted
                )
            }
            Text(
                text = "Inspecionar detalhes →",
                style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp),
                color = AuraCyan.copy(alpha = 0.85f),
                modifier = Modifier.padding(top = 2.dp)
            )
        }
    }
}

/**
 * Modal executivo de telemetria e ações do Tanque (GenUI 2.0 Interativo)
 */
@Composable
private fun TankDetailModal(
    tank: GenUiTank,
    onDismiss: () -> Unit,
    onDrillDown: (String) -> Unit
) {
    val haptic = LocalHapticFeedback.current
    val color = if (tank.critical) StatusDanger else fuelColor(tank.fuel)
    val freeL = maxOf(0.0, tank.capacityL - tank.balanceL)
    val comp5k = (freeL / 5000.0).toInt()

    Dialog(onDismissRequest = onDismiss) {
        AuraCard(
            shape = RoundedCornerShape(26.dp),
            accent = color,
            glowActive = tank.critical,
            modifier = Modifier.fillMaxWidth(),
            contentPadding = PaddingValues(20.dp)
        ) {
            Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
                // Header: Tank and Fuel Info
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        StatusDot(color = color, pulsing = tank.critical, size = 8.dp)
                        Text(
                            text = "Tanque ${tank.code}",
                            style = MaterialTheme.typography.headlineSmall.copy(fontWeight = FontWeight.Bold),
                            color = TextPrimary
                        )
                    }
                    if (tank.critical) {
                        AuraPill("NÍVEL CRÍTICO", StatusDanger)
                    } else {
                        AuraPill("${"%.0f".format(tank.occupancyPct)}% OCUPADO", color)
                    }
                }

                Text(
                    text = tank.fuel,
                    style = MaterialTheme.typography.titleMedium,
                    color = color
                )

                // Grid 2x2 com métricas operacionais
                Column(
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(16.dp))
                        .background(ObsidianMid)
                        .padding(14.dp)
                ) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Column {
                            Text("Saldo Físico Atual", style = MaterialTheme.typography.labelSmall, color = TextMuted)
                            Text("${GenUiParser.fmtNumber(tank.balanceL)} L", style = MaterialTheme.typography.titleMedium, color = TextPrimary)
                        }
                        Column(horizontalAlignment = Alignment.End) {
                            Text("Capacidade Nominal", style = MaterialTheme.typography.labelSmall, color = TextMuted)
                            Text("${GenUiParser.fmtNumber(tank.capacityL)} L", style = MaterialTheme.typography.titleMedium, color = TextPrimary)
                        }
                    }

                    Box(Modifier.fillMaxWidth().height(1.dp).background(OutlineSoft.copy(alpha = 0.5f)))

                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Column {
                            Text("Lastro Livre (Descarga)", style = MaterialTheme.typography.labelSmall, color = TextMuted)
                            Text("${GenUiParser.fmtNumber(freeL)} L", style = MaterialTheme.typography.titleMedium, color = AuraEmerald)
                        }
                        Column(horizontalAlignment = Alignment.End) {
                            Text("Caminhão-Tanque", style = MaterialTheme.typography.labelSmall, color = TextMuted)
                            Text(
                                if (comp5k > 0) "Cabe $comp5k comp. (5k L)" else "Sem lastro para 5k L",
                                style = MaterialTheme.typography.titleMedium,
                                color = if (comp5k > 0) AuraCyan else TextMuted
                            )
                        }
                    }

                    tank.autonomyHours?.let { hours ->
                        Box(Modifier.fillMaxWidth().height(1.dp).background(OutlineSoft.copy(alpha = 0.5f)))
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("Autonomia Operacional Estimada", style = MaterialTheme.typography.labelSmall, color = TextMuted)
                            Text(
                                "${"%.1f".format(hours)} horas",
                                style = MaterialTheme.typography.titleSmall,
                                color = if (tank.critical) StatusDanger else TextPrimary
                            )
                        }
                    }
                }

                // Ações Rápidas Cognitivas (Drill-Down 1-tap)
                SectionLabel("AÇÕES DE CONTEXTO AURA")
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    if (comp5k > 0) {
                        AuraGradientButton(
                            text = "Simular Pedido (${comp5k * 5000} L)",
                            onClick = {
                                haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                                onDismiss()
                                onDrillDown("Simular pedido de compra para o Tanque ${tank.code} (${tank.fuel}) aproveitando o espaço livre para ${comp5k * 5000} L (em compartimentos de 5.000 L).")
                            },
                            modifier = Modifier.fillMaxWidth()
                        )
                    }

                    AuraGhostButton(
                        text = "Auditar Medição ANP e Variação",
                        onClick = {
                            haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                            onDismiss()
                            onDrillDown("Auditar histórico de perdas, sobras e conformidade LMC/ANP do Tanque ${tank.code} (${tank.fuel}).")
                        },
                        modifier = Modifier.fillMaxWidth()
                    )

                    AuraGhostButton(
                        text = "Previsão de Esgotamento por Turno",
                        onClick = {
                            haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                            onDismiss()
                            onDrillDown("Qual a vazão média horária e a previsão de esgotamento por turno para o Tanque ${tank.code} (${tank.fuel})?")
                        },
                        modifier = Modifier.fillMaxWidth(),
                        tint = TextSecondary
                    )
                }

                AuraGhostButton(
                    text = "Fechar",
                    onClick = onDismiss,
                    modifier = Modifier.fillMaxWidth(),
                    tint = TextMuted
                )
            }
        }
    }
}

