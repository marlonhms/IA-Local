package com.example.aurapostoassitance.ui.components

import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.aurapostoassitance.ui.theme.AuraCyan
import com.example.aurapostoassitance.ui.theme.AuraEmerald
import com.example.aurapostoassitance.ui.theme.AuroraBrush
import com.example.aurapostoassitance.ui.theme.GlassBorderBrush
import com.example.aurapostoassitance.ui.theme.GlassHighlight
import com.example.aurapostoassitance.ui.theme.ObsidianBase
import com.example.aurapostoassitance.ui.theme.ObsidianBright
import com.example.aurapostoassitance.ui.theme.ObsidianHigh
import com.example.aurapostoassitance.ui.theme.ObsidianLow
import com.example.aurapostoassitance.ui.theme.ObsidianMid
import com.example.aurapostoassitance.ui.theme.OutlineSoft
import com.example.aurapostoassitance.ui.theme.StatusDanger
import com.example.aurapostoassitance.ui.theme.StatusInfo
import com.example.aurapostoassitance.ui.theme.StatusSuccess
import com.example.aurapostoassitance.ui.theme.StatusWarning
import com.example.aurapostoassitance.ui.theme.TextMuted
import com.example.aurapostoassitance.ui.theme.TextPrimary
import com.example.aurapostoassitance.ui.theme.TextSecondary

/** Mapeia o status semantico do contrato GenUI para cor de acento. */
fun statusColor(status: String?): Color = when (status?.lowercase()) {
    "success", "ok", "conforme" -> StatusSuccess
    "warning", "attention", "alerta" -> StatusWarning
    "danger", "critical", "critico" -> StatusDanger
    "info" -> StatusInfo
    else -> Color(0xFF94A3B8)
}

/** Superficie de vidro Obsidian Deluxe: gradiente multicamadas, destaque superior e microescala ao tocar. */
@Composable
fun AuraCard(
    modifier: Modifier = Modifier,
    shape: Shape = RoundedCornerShape(20.dp),
    accent: Color? = null,
    glowActive: Boolean = false,
    onClick: (() -> Unit)? = null,
    contentPadding: PaddingValues = PaddingValues(16.dp),
    content: @Composable () -> Unit
) {
    val interactionSource = remember { MutableInteractionSource() }
    val isPressed by interactionSource.collectIsPressedAsState()
    val scale by animateFloatAsState(
        targetValue = if (isPressed && onClick != null) 0.985f else 1f,
        animationSpec = spring(dampingRatio = 0.7f, stiffness = 400f),
        label = "cardScale"
    )

    val glowAlpha = if (glowActive) {
        val transition = rememberInfiniteTransition(label = "glowPulse")
        transition.animateFloat(
            initialValue = 0.45f,
            targetValue = 0.95f,
            animationSpec = infiniteRepeatable(tween(1400, easing = LinearEasing), RepeatMode.Reverse),
            label = "glowAlpha"
        ).value
    } else 1f

    val borderBrush = when {
        glowActive && accent != null -> Brush.linearGradient(
            listOf(accent.copy(alpha = glowAlpha), accent.copy(alpha = glowAlpha * 0.45f))
        )
        glowActive -> Brush.linearGradient(
            listOf(AuraCyan.copy(alpha = glowAlpha), AuraEmerald.copy(alpha = glowAlpha))
        )
        accent != null -> Brush.verticalGradient(
            listOf(accent.copy(alpha = 0.65f), OutlineSoft)
        )
        else -> GlassBorderBrush
    }

    val cardBackground = Brush.verticalGradient(
        listOf(ObsidianHigh.copy(alpha = 0.85f), ObsidianMid.copy(alpha = 0.95f))
    )

    var base = modifier
        .graphicsLayer {
            scaleX = scale
            scaleY = scale
        }
        .clip(shape)
        .background(cardBackground)
        .drawBehind {
            // Efeito de iluminacao sutil na borda superior (top highlight)
            drawLine(
                brush = Brush.horizontalGradient(
                    listOf(Color.Transparent, GlassHighlight, Color.Transparent)
                ),
                start = Offset(0f, 1f),
                end = Offset(size.width, 1f),
                strokeWidth = 1.5.dp.toPx()
            )
        }
        .border(BorderStroke(1.dp, borderBrush), shape)

    if (onClick != null) {
        val haptic = LocalHapticFeedback.current
        base = base.clickable(
            interactionSource = interactionSource,
            indication = null
        ) {
            haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
            onClick()
        }
    }

    Box(base.padding(contentPadding)) { content() }
}

/** Botao principal com gradiente Aurora, microescala tátil e alvo de toque minimo de 52dp. */
@Composable
fun AuraGradientButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    icon: ImageVector? = null
) {
    val haptic = LocalHapticFeedback.current
    val interactionSource = remember { MutableInteractionSource() }
    val isPressed by interactionSource.collectIsPressedAsState()
    val scale by animateFloatAsState(
        targetValue = if (isPressed && enabled) 0.97f else 1f,
        animationSpec = spring(dampingRatio = 0.65f, stiffness = 500f),
        label = "gradientBtnScale"
    )
    val shape = RoundedCornerShape(16.dp)

    Box(
        modifier = modifier
            .defaultMinSize(minHeight = 52.dp)
            .graphicsLayer {
                scaleX = scale
                scaleY = scale
            }
            .clip(shape)
            .background(
                if (enabled) AuroraBrush else Brush.linearGradient(listOf(ObsidianBright, ObsidianBright))
            )
            .drawBehind {
                if (enabled) {
                    // Sutil brilho no topo do botao
                    drawLine(
                        brush = Brush.horizontalGradient(
                            listOf(Color.Transparent, Color(0x66FFFFFF), Color.Transparent)
                        ),
                        start = Offset(0f, 1f),
                        end = Offset(size.width, 1f),
                        strokeWidth = 1.dp.toPx()
                    )
                }
            }
            .clickable(
                enabled = enabled,
                interactionSource = interactionSource,
                indication = null
            ) {
                haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                onClick()
            }
            .padding(horizontal = 16.dp, vertical = 14.dp),
        contentAlignment = Alignment.Center
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.Center
        ) {
            if (icon != null) {
                Icon(
                    imageVector = icon,
                    contentDescription = null,
                    tint = if (enabled) ObsidianBase else Color(0xFF64748B),
                    modifier = Modifier.size(18.dp)
                )
                Spacer(Modifier.width(8.dp))
            }
            Text(
                text = text,
                style = MaterialTheme.typography.labelLarge,
                color = if (enabled) ObsidianBase else Color(0xFF64748B),
                fontWeight = FontWeight.SemiBold,
                textAlign = TextAlign.Center
            )
        }
    }
}

/** Botao secundario translucido com borda suave e microescala. */
@Composable
fun AuraGhostButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    tint: Color = AuraCyan,
    icon: ImageVector? = null
) {
    val haptic = LocalHapticFeedback.current
    val interactionSource = remember { MutableInteractionSource() }
    val isPressed by interactionSource.collectIsPressedAsState()
    val scale by animateFloatAsState(
        targetValue = if (isPressed) 0.975f else 1f,
        animationSpec = spring(dampingRatio = 0.65f, stiffness = 500f),
        label = "ghostBtnScale"
    )
    val shape = RoundedCornerShape(16.dp)

    Box(
        modifier = modifier
            .defaultMinSize(minHeight = 52.dp)
            .graphicsLayer {
                scaleX = scale
                scaleY = scale
            }
            .clip(shape)
            .background(tint.copy(alpha = 0.10f))
            .border(1.dp, tint.copy(alpha = 0.35f), shape)
            .clickable(
                interactionSource = interactionSource,
                indication = null
            ) {
                haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                onClick()
            }
            .padding(horizontal = 16.dp, vertical = 14.dp),
        contentAlignment = Alignment.Center
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.Center
        ) {
            if (icon != null) {
                Icon(
                    imageVector = icon,
                    contentDescription = null,
                    tint = tint,
                    modifier = Modifier.size(18.dp)
                )
                Spacer(Modifier.width(8.dp))
            }
            Text(
                text = text,
                style = MaterialTheme.typography.labelLarge,
                color = tint,
                fontWeight = FontWeight.SemiBold,
                textAlign = TextAlign.Center
            )
        }
    }
}

/** Indicador com efeito radar pulsante tecnologico. */
@Composable
fun StatusDot(
    color: Color,
    size: Dp = 8.dp,
    pulsing: Boolean = false,
    modifier: Modifier = Modifier
) {
    if (pulsing) {
        val transition = rememberInfiniteTransition(label = "radarDot")
        val rippleAlpha by transition.animateFloat(
            initialValue = 0.7f,
            targetValue = 0f,
            animationSpec = infiniteRepeatable(tween(1400, easing = FastOutSlowInEasing)),
            label = "rippleAlpha"
        )
        val rippleScale by transition.animateFloat(
            initialValue = 1f,
            targetValue = 2.4f,
            animationSpec = infiniteRepeatable(tween(1400, easing = FastOutSlowInEasing)),
            label = "rippleScale"
        )

        Box(
            modifier = modifier.size(size * 2.4f),
            contentAlignment = Alignment.Center
        ) {
            Canvas(modifier = Modifier.size(size * 2.4f)) {
                val centerOffset = Offset(size.toPx() * 1.2f, size.toPx() * 1.2f)
                val baseRadius = size.toPx() / 2f
                // Anel de radar expansivo
                drawCircle(
                    color = color.copy(alpha = rippleAlpha),
                    radius = baseRadius * rippleScale,
                    center = centerOffset
                )
                // Ponto solido central com glow
                drawCircle(
                    color = color,
                    radius = baseRadius,
                    center = centerOffset
                )
            }
        }
    } else {
        Box(
            modifier = modifier
                .size(size)
                .clip(CircleShape)
                .background(color)
                .border(1.dp, Color(0x33FFFFFF), CircleShape)
        )
    }
}

/** Pilula de status com acabamento de cápsula translúcida. */
@Composable
fun AuraPill(
    text: String,
    color: Color,
    modifier: Modifier = Modifier,
    icon: ImageVector? = null
) {
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(50))
            .background(color.copy(alpha = 0.12f))
            .border(1.dp, color.copy(alpha = 0.35f), RoundedCornerShape(50))
            .padding(horizontal = 10.dp, vertical = 4.dp),
        contentAlignment = Alignment.Center
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            if (icon != null) {
                Icon(
                    imageVector = icon,
                    contentDescription = null,
                    tint = color,
                    modifier = Modifier.size(12.dp)
                )
            }
            Text(
                text = text,
                style = MaterialTheme.typography.labelSmall,
                color = color,
                fontWeight = FontWeight.SemiBold
            )
        }
    }
}

/** Chip de sugestao moderno com acabamento de cápsula e microtoque. */
@Composable
fun AuraChip(
    label: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    tag: String? = null,
    icon: ImageVector? = null,
    accentColor: Color = AuraCyan
) {
    val haptic = LocalHapticFeedback.current
    val interactionSource = remember { MutableInteractionSource() }
    val isPressed by interactionSource.collectIsPressedAsState()
    val scale by animateFloatAsState(
        targetValue = if (isPressed) 0.96f else 1f,
        animationSpec = spring(dampingRatio = 0.7f, stiffness = 450f),
        label = "chipScale"
    )

    Box(
        modifier = modifier
            .graphicsLayer {
                scaleX = scale
                scaleY = scale
            }
            .clip(RoundedCornerShape(50))
            .background(ObsidianMid)
            .border(1.dp, OutlineSoft, RoundedCornerShape(50))
            .clickable(
                interactionSource = interactionSource,
                indication = null
            ) {
                haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                onClick()
            }
            .padding(horizontal = 14.dp, vertical = 8.dp)
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            if (tag != null) {
                Text(
                    text = tag.uppercase(),
                    style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp),
                    color = accentColor,
                    fontWeight = FontWeight.Bold
                )
            }
            if (icon != null) {
                Icon(
                    imageVector = icon,
                    contentDescription = null,
                    tint = accentColor,
                    modifier = Modifier.size(13.dp)
                )
            }
            Text(
                text = label,
                style = MaterialTheme.typography.labelSmall,
                color = TextPrimary
            )
        }
    }
}

/** Placeholder de carregamento (skeleton) com brilho angular deslizante deluxe. */
@Composable
fun ShimmerBox(modifier: Modifier = Modifier, shape: Shape = RoundedCornerShape(12.dp)) {
    val transition = rememberInfiniteTransition(label = "shimmer")
    val x = transition.animateFloat(
        initialValue = -400f,
        targetValue = 1000f,
        animationSpec = infiniteRepeatable(tween(1400, easing = LinearEasing)),
        label = "shimmerX"
    ).value

    Box(
        modifier = modifier
            .clip(shape)
            .background(ObsidianLow)
            .drawBehind {
                drawRect(
                    Brush.linearGradient(
                        colors = listOf(
                            Color.Transparent,
                            Color(0x22FFFFFF),
                            Color(0x35FFFFFF),
                            Color(0x22FFFFFF),
                            Color.Transparent
                        ),
                        start = Offset(x, 0f),
                        end = Offset(x + 350f, size.height)
                    )
                )
            }
    )
}

/** Indicador visual tecnologico de raciocinio da IA com orbe pulsante e ondas sincronizadas. */
@Composable
fun ThinkingIndicator(label: String, modifier: Modifier = Modifier) {
    val transition = rememberInfiniteTransition(label = "think")
    val pulseBorder by transition.animateFloat(
        initialValue = 0.3f,
        targetValue = 0.8f,
        animationSpec = infiniteRepeatable(tween(1000, easing = LinearEasing), RepeatMode.Reverse),
        label = "thinkBorder"
    )

    Row(
        modifier = modifier
            .clip(RoundedCornerShape(50))
            .background(ObsidianMid)
            .border(
                1.dp,
                Brush.horizontalGradient(
                    listOf(
                        AuraCyan.copy(alpha = pulseBorder),
                        AuraEmerald.copy(alpha = pulseBorder)
                    )
                ),
                RoundedCornerShape(50)
            )
            .padding(horizontal = 16.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        repeat(3) { i ->
            val a by transition.animateFloat(
                initialValue = 0.3f,
                targetValue = 1f,
                animationSpec = infiniteRepeatable(
                    tween(600, delayMillis = i * 160, easing = LinearEasing),
                    RepeatMode.Reverse
                ),
                label = "thinkDot$i"
            )
            Box(
                Modifier
                    .size(7.dp)
                    .alpha(a)
                    .clip(CircleShape)
                    .background(if (i == 1) AuraEmerald else AuraCyan)
            )
            Spacer(Modifier.width(6.dp))
        }
        Spacer(Modifier.width(4.dp))
        Text(
            text = label,
            style = MaterialTheme.typography.labelMedium,
            color = TextSecondary,
            fontWeight = FontWeight.Medium
        )
    }
}

/** Rotulo de secao editorial limpo. */
@Composable
fun SectionLabel(text: String, modifier: Modifier = Modifier) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = modifier
    ) {
        Box(
            modifier = Modifier
                .size(width = 3.dp, height = 10.dp)
                .clip(RoundedCornerShape(2.dp))
                .background(AuraCyan)
        )
        Spacer(modifier = Modifier.width(6.dp))
        Text(
            text = text.uppercase(),
            style = MaterialTheme.typography.labelSmall,
            color = Color(0xFF64748B),
            letterSpacing = 1.3.sp,
            fontWeight = FontWeight.SemiBold
        )
    }
}
