package com.example.aurapostoassitance.ui.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateContentSize
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.rounded.Shield
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.aurapostoassitance.ui.theme.AuraCyan
import com.example.aurapostoassitance.ui.theme.AuraEmerald
import com.example.aurapostoassitance.ui.theme.AuraPurple
import com.example.aurapostoassitance.ui.theme.AuraTypographyExt
import com.example.aurapostoassitance.ui.theme.BorderHairline
import com.example.aurapostoassitance.ui.theme.ObsidianLow
import com.example.aurapostoassitance.ui.theme.TextMuted
import com.example.aurapostoassitance.ui.theme.TextSecondary

/** Metadados de confiança e telemetria auditável da resposta (Carbon Core P0.3/P0.4). */
data class AuraTrustMetadata(
    val sourceLabel: String = "SQL Read-Only",
    val isDeterministic: Boolean = true,
    val isCacheHit: Boolean = false,
    val piiRedactedCount: Int = 0,
    val latencyMs: Long? = null,
    val ttftMs: Long? = null,
    val didStreamReset: Boolean = false
)

/**
 * AuraReasoningRibbon (Paridade Carbon UI P1-UI2):
 * - Durante streaming: exibe faixa silenciosa de 28dp com o estágio ativo (LGPD -> SQL -> Motor -> Síntese).
 * - Após conclusão: contrai suavemente numa Trust Pill clicável (✓ SQL Read-Only · Determinístico · LGPD · 680ms ▾).
 */
@Composable
fun AuraReasoningRibbon(
    reasoningSteps: List<String>,
    isStreaming: Boolean,
    liveStatusLabel: String?,
    trust: AuraTrustMetadata,
    trailFooterLabel: String,
    modifier: Modifier = Modifier
) {
    var expanded by remember { mutableStateOf(false) }
    val haptic = LocalHapticFeedback.current
    val chevronRotation by animateFloatAsState(
        targetValue = if (expanded) 180f else 0f,
        animationSpec = spring(stiffness = 420f),
        label = "ribbonChevron"
    )

    val activeStageColor = when {
        trust.didStreamReset && isStreaming -> AuraCyan
        isStreaming && liveStatusLabel?.contains("LGPD", ignoreCase = true) == true -> AuraEmerald
        isStreaming && liveStatusLabel?.contains("SQL", ignoreCase = true) == true -> AuraCyan
        isStreaming && liveStatusLabel?.contains("Python", ignoreCase = true) == true -> AuraEmerald
        isStreaming -> AuraPurple
        else -> AuraEmerald
    }

    val trustSummary = remember(trust) {
        buildList {
            add(if (trust.isCacheHit) "Cache Local" else trust.sourceLabel)
            if (trust.isDeterministic && !trust.isCacheHit) add("Determinístico")
            add(if (trust.piiRedactedCount > 0) "LGPD (${trust.piiRedactedCount})" else "LGPD")
            trust.latencyMs?.let { add("${it}ms") }
        }.joinToString(" · ")
    }

    Column(
        modifier = modifier
            .fillMaxWidth()
            .animateContentSize(animationSpec = spring(dampingRatio = 0.85f, stiffness = 420f))
    ) {
        Row(
            modifier = Modifier
                .clip(RoundedCornerShape(50))
                .background(ObsidianLow.copy(alpha = 0.85f))
                .border(
                    width = 1.dp,
                    color = if (isStreaming) activeStageColor.copy(alpha = 0.42f) else BorderHairline,
                    shape = RoundedCornerShape(50)
                )
                .clickable(enabled = reasoningSteps.isNotEmpty() || !isStreaming) {
                    haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                    expanded = !expanded
                }
                .padding(horizontal = 10.dp, vertical = 5.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            if (isStreaming) {
                StatusDot(color = activeStageColor, size = 6.dp, pulsing = true)
                Text(
                    text = liveStatusLabel?.takeIf { it.isNotBlank() } ?: "Sintetizando recomendação...",
                    style = MaterialTheme.typography.labelSmall.copy(
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Medium
                    ),
                    color = activeStageColor,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f, fill = false)
                )
            } else {
                Icon(
                    imageVector = Icons.Rounded.Shield,
                    contentDescription = null,
                    tint = AuraEmerald,
                    modifier = Modifier.size(12.dp)
                )
                Text(
                    text = trustSummary,
                    style = AuraTypographyExt.monoAudit.copy(fontSize = 10.5.sp),
                    color = TextSecondary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f, fill = false)
                )
                if (reasoningSteps.isNotEmpty()) {
                    Icon(
                        imageVector = Icons.Filled.KeyboardArrowDown,
                        contentDescription = "Expandir auditoria",
                        tint = TextMuted,
                        modifier = Modifier
                            .size(14.dp)
                            .graphicsLayer { rotationZ = chevronRotation }
                    )
                }
            }
        }

        AnimatedVisibility(
            visible = expanded && reasoningSteps.isNotEmpty(),
            enter = expandVertically(spring(stiffness = 460f)) + fadeIn(tween(180)),
            exit = shrinkVertically(spring(stiffness = 460f)) + fadeOut(tween(140))
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 8.dp)
                    .clip(RoundedCornerShape(14.dp))
                    .background(ObsidianLow.copy(alpha = 0.78f))
                    .border(1.dp, BorderHairline, RoundedCornerShape(14.dp))
                    .padding(12.dp),
                verticalArrangement = Arrangement.spacedBy(7.dp)
            ) {
                reasoningSteps.forEachIndexed { idx, step ->
                    val isLastRunning = isStreaming && idx == reasoningSteps.lastIndex
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalAlignment = Alignment.Top
                    ) {
                        Box(modifier = Modifier.padding(top = 3.dp)) {
                            if (isLastRunning) {
                                StatusDot(color = AuraCyan, size = 6.dp, pulsing = true)
                            } else {
                                Box(
                                    modifier = Modifier
                                        .size(13.dp)
                                        .clip(CircleShape)
                                        .background(AuraEmerald.copy(alpha = 0.14f)),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Icon(
                                        imageVector = Icons.Filled.Check,
                                        contentDescription = null,
                                        tint = AuraEmerald,
                                        modifier = Modifier.size(9.dp)
                                    )
                                }
                            }
                        }
                        Text(
                            text = step,
                            style = MaterialTheme.typography.bodySmall.copy(lineHeight = 16.sp),
                            color = if (isLastRunning) AuraCyan else TextSecondary,
                            modifier = Modifier.weight(1f)
                        )
                    }
                }

                Spacer(modifier = Modifier.height(2.dp))
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(1.dp)
                        .background(BorderHairline)
                )
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = trailFooterLabel,
                        style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp),
                        color = TextMuted,
                        modifier = Modifier.weight(1f),
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                    trust.ttftMs?.let { ttft ->
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "TTFT ${ttft}ms",
                            style = AuraTypographyExt.monoAudit.copy(fontSize = 10.sp),
                            color = AuraCyan
                        )
                    }
                }
            }
        }
    }
}
