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
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
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
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.aurapostoassitance.ui.components.AuraCard
import com.example.aurapostoassitance.ui.components.AuraGhostButton
import com.example.aurapostoassitance.ui.components.AuraGradientButton
import com.example.aurapostoassitance.ui.components.AuraPill
import com.example.aurapostoassitance.ui.components.SectionLabel
import com.example.aurapostoassitance.ui.components.StatusDot
import com.example.aurapostoassitance.ui.components.statusColor
import com.example.aurapostoassitance.ui.theme.AuraCyan
import com.example.aurapostoassitance.ui.theme.AuraEmerald
import com.example.aurapostoassitance.ui.theme.AuroraBrush
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

/** Card executivo nativo deluxe: cabecalho com glow, blocos empilhados com entrada escalonada e acoes HITL. */
@Composable
fun GenUiCardView(
    card: GenUiCard,
    onAction: (GenUiAction) -> Unit,
    modifier: Modifier = Modifier
) {
    var pending by remember { mutableStateOf<GenUiAction?>(null) }
    val isCritical = card.severity.equals("critical", true) || card.severity.equals("danger", true)
    val accent = if (isCritical) StatusDanger else AuraCyan

    AuraCard(
        modifier = modifier.fillMaxWidth(),
        accent = accent,
        glowActive = isCritical,
        contentPadding = PaddingValues(0.dp)
    ) {
        Column(
            verticalArrangement = Arrangement.spacedBy(16.dp),
            modifier = Modifier.padding(18.dp)
        ) {
            CardHeader(card)

            card.blocks.forEachIndexed { index, block ->
                Staggered(index) { BlockView(block) }
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
                        val click = {
                            if (action.requiresConfirmation) pending = action else onAction(action)
                        }
                        val formattedLabel = action.label.replace(" L)", "\u00A0L)")
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

    pending?.let { action ->
        val haptic = LocalHapticFeedback.current
        Dialog(onDismissRequest = { pending = null }) {
            AuraCard(
                shape = RoundedCornerShape(26.dp),
                accent = AuraCyan,
                glowActive = true,
                modifier = Modifier.fillMaxWidth(),
                contentPadding = PaddingValues(22.dp)
            ) {
                Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        StatusDot(color = AuraCyan, pulsing = true, size = 7.dp)
                        SectionLabel("CONFIRMAÇÃO HITL")
                    }
                    Text(
                        "Confirmar Ação",
                        style = MaterialTheme.typography.headlineSmall,
                        color = TextPrimary
                    )
                    Text(
                        "Você está prestes a solicitar:\n\n${action.label}\n\nA AURA registrará esta solicitação para validação executiva na rede do posto.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = TextSecondary
                    )
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        AuraGhostButton(
                            text = "Cancelar",
                            onClick = { pending = null },
                            modifier = Modifier.weight(1f),
                            tint = TextSecondary
                        )
                        AuraGradientButton(
                            text = "Confirmar",
                            onClick = {
                                haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                                pending = null
                                onAction(action)
                            },
                            modifier = Modifier.weight(1.2f)
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun CardHeader(card: GenUiCard) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            StatusDot(color = AuraEmerald, pulsing = true, size = 7.dp)
            SectionLabel("AURA COCKPIT")
            card.confidence?.let {
                Spacer(Modifier.weight(1f))
                AuraPill(
                    text = "${(it * 100).toInt()}% confiança",
                    color = AuraEmerald
                )
            }
        }
        Text(
            text = card.title,
            style = MaterialTheme.typography.headlineSmall,
            color = TextPrimary
        )
        (card.diagnosis ?: card.subtitle)?.let {
            Text(
                text = it,
                style = MaterialTheme.typography.bodyMedium,
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
private fun BlockView(block: GenUiBlock) {
    when (block) {
        is GenUiBlock.KpiGrid -> KpiGridBlock(block)
        is GenUiBlock.Comparison -> ComparisonBlock(block)
        is GenUiBlock.Ranking -> RankingBlock(block)
        is GenUiBlock.Timeline -> TimelineBlock(block)
        is GenUiBlock.AlertCallout -> AlertBlock(block.alert)
        is GenUiBlock.Tanks -> TanksBlock(block)
        is GenUiBlock.Note -> NoteBlock(block)
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

// ---------------------------------------------------------------- KPIs

@Composable
private fun KpiGridBlock(block: GenUiBlock.KpiGrid) {
    Column {
        BlockTitle(block.title, block.subtitle)
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            block.kpis.chunked(2).forEach { pair ->
                Row(
                    Modifier
                        .fillMaxWidth()
                        .height(IntrinsicSize.Max),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    pair.forEach { kpi -> KpiTile(kpi, Modifier.weight(1f).fillMaxHeight()) }
                    if (pair.size == 1) Spacer(Modifier.weight(1f))
                }
            }
        }
    }
}

@Composable
private fun KpiTile(kpi: GenUiKpi, modifier: Modifier = Modifier) {
    val color = statusColor(kpi.status)
    Column(
        modifier
            .clip(RoundedCornerShape(16.dp))
            .background(ObsidianLow)
            .border(1.dp, GlassBorderSoft, RoundedCornerShape(16.dp))
            .padding(14.dp),
        verticalArrangement = Arrangement.spacedBy(6.dp)
    ) {
        Text(
            text = kpi.label,
            style = MaterialTheme.typography.labelSmall,
            color = TextSecondary,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis
        )
        Text(
            text = kpi.value.replace(" L", "\u00A0L").replace(" h", "\u00A0h"),
            style = MaterialTheme.typography.headlineSmall.copy(fontSize = 24.sp),
            color = TextPrimary,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis
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
                maxLines = 2
            )
        }
    }
}

// ---------------------------------------------------------------- Comparativo

@Composable
private fun ComparisonBlock(block: GenUiBlock.Comparison) {
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
                    Column(horizontalAlignment = Alignment.End, verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(row.primary, style = MaterialTheme.typography.titleMedium, color = TextPrimary)
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
private fun RankingBlock(block: GenUiBlock.Ranking) {
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
                    Column(Modifier.weight(1f)) {
                        Text(item.title, style = MaterialTheme.typography.titleSmall, color = TextPrimary, maxLines = 1, overflow = TextOverflow.Ellipsis)
                        item.subtitle?.let { Text(it, style = MaterialTheme.typography.bodySmall, color = TextMuted, maxLines = 1) }
                    }
                    Column(horizontalAlignment = Alignment.End, verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(item.value, style = MaterialTheme.typography.titleMedium, color = TextPrimary)
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
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Icon(icon, null, tint = color, modifier = Modifier.size(22.dp))
        Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
            Text(alert.title, style = MaterialTheme.typography.titleSmall, color = color)
            if (alert.message.isNotBlank()) {
                Text(alert.message, style = MaterialTheme.typography.bodyMedium, color = TextSecondary)
            }
        }
    }
}

@Composable
private fun NoteBlock(block: GenUiBlock.Note) {
    Column {
        BlockTitle(block.title, null)
        Text(block.text, style = MaterialTheme.typography.bodyMedium, color = TextSecondary)
    }
}

// ---------------------------------------------------------------- Tanques Verticais Deluxe

@Composable
private fun TanksBlock(block: GenUiBlock.Tanks) {
    Column {
        BlockTitle(block.title, if (block.hiddenInactive > 0) "${block.hiddenInactive} tanques inativos ocultos" else null)
        LazyRow(
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            contentPadding = PaddingValues(horizontal = 2.dp, vertical = 4.dp)
        ) {
            items(block.tanks, key = { it.code + it.fuel }) { TankTile(it) }
        }
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
private fun TankTile(tank: GenUiTank) {
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
        }
    }
}
