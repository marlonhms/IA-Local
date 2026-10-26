package com.example.aurapostoassitance.ui.components

import android.view.SoundEffectConstants
import android.view.View
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateContentSize
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
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
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material.icons.rounded.Assessment
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material.icons.rounded.LocalGasStation
import androidx.compose.material.icons.rounded.Mic
import androidx.compose.material.icons.rounded.PointOfSale
import androidx.compose.material.icons.rounded.Tune
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.hapticfeedback.HapticFeedback
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlin.math.cos
import kotlin.math.sin
import com.example.aurapostoassitance.ui.theme.AuraAmbientCyan
import com.example.aurapostoassitance.ui.theme.AuraAmbientPetroleum
import com.example.aurapostoassitance.ui.theme.AuraAmbientPurple
import com.example.aurapostoassitance.ui.theme.AuraBrandGradient
import com.example.aurapostoassitance.ui.theme.AuraCyan
import com.example.aurapostoassitance.ui.theme.AuraEmerald
import com.example.aurapostoassitance.ui.theme.AuraPurple
import com.example.aurapostoassitance.ui.theme.AuroraBrush
import com.example.aurapostoassitance.ui.theme.GlassBorderBrush
import com.example.aurapostoassitance.ui.theme.GlassHighlight
import com.example.aurapostoassitance.ui.theme.LiquidGlassElevatedBrush
import com.example.aurapostoassitance.ui.theme.LiquidGlassSurfaceBrush
import com.example.aurapostoassitance.ui.theme.LiquidIridescentBorderBrush
import com.example.aurapostoassitance.ui.theme.LiquidIridescentSubtleBrush
import com.example.aurapostoassitance.ui.theme.LiquidSpecularHighlight
import com.example.aurapostoassitance.ui.theme.ObsidianBase
import com.example.aurapostoassitance.ui.theme.ObsidianBright
import com.example.aurapostoassitance.ui.theme.ObsidianDeep
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

/** Utilitário central de feedback tátil e design sonoro háptico (Pilar 4). */
object AuraHaptics {
    fun click(view: View? = null, haptic: HapticFeedback? = null) {
        view?.playSoundEffect(SoundEffectConstants.CLICK)
        haptic?.performHapticFeedback(HapticFeedbackType.TextHandleMove)
    }

    fun heavy(view: View? = null, haptic: HapticFeedback? = null) {
        view?.playSoundEffect(SoundEffectConstants.CLICK)
        haptic?.performHapticFeedback(HapticFeedbackType.LongPress)
    }

    fun light(haptic: HapticFeedback? = null) {
        haptic?.performHapticFeedback(HapticFeedbackType.TextHandleMove)
    }
}

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

/**
 * Titulo com tipagem premium para a marca AURA:
 * Gradiente horizontal entre Azul (#38BDF8), Verde Petroleo (#0D9488) e Roxo (#A855F7).
 */
@Composable
fun AuraBrandTitle(
    text: String = "AURA",
    modifier: Modifier = Modifier,
    style: TextStyle = MaterialTheme.typography.titleLarge,
    fontWeight: FontWeight = FontWeight.ExtraBold,
    letterSpacing: TextUnit = 1.8.sp
) {
    Text(
        text = text,
        modifier = modifier,
        style = style.copy(
            brush = AuraBrandGradient,
            fontWeight = fontWeight,
            letterSpacing = letterSpacing
        )
    )
}

/**
 * Fundo com atmosfera Spatial UI & Aurora Fluida Viva:
 * Renderiza orbes dinamicos de luz AMOLED difusa com movimento suave sem overhead de GPU.
 */
@Composable
fun AuraAmbientBackground(
    modifier: Modifier = Modifier,
    content: @Composable () -> Unit
) {
    val infiniteTransition = rememberInfiniteTransition(label = "ambientAurora")
    val phaseX by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 20000, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "phaseX"
    )
    val phaseY by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 26000, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "phaseY"
    )

    Box(
        modifier = modifier
            .fillMaxSize()
            .background(ObsidianDeep)
            .drawBehind {
                val center1 = Offset(
                    x = size.width * (0.20f + 0.35f * phaseX),
                    y = size.height * (0.12f + 0.22f * phaseY)
                )
                drawCircle(
                    brush = Brush.radialGradient(
                        colors = listOf(
                            AuraAmbientCyan,
                            AuraAmbientPetroleum,
                            Color.Transparent
                        ),
                        center = center1,
                        radius = size.width * 0.95f
                    ),
                    center = center1,
                    radius = size.width * 0.95f
                )

                val center2 = Offset(
                    x = size.width * (0.80f - 0.35f * phaseY),
                    y = size.height * (0.75f - 0.22f * phaseX)
                )
                drawCircle(
                    brush = Brush.radialGradient(
                        colors = listOf(
                            AuraAmbientPurple,
                            Color.Transparent
                        ),
                        center = center2,
                        radius = size.width * 0.90f
                    ),
                    center = center2,
                    radius = size.width * 0.90f
                )
            }
    ) {
        content()
    }
}

/**
 * Cartao de Vidro Liquido Spatial UI:
 * - Superficie translucida Obsidian multicamadas com micro-profundidade
 * - Borda iridescente liquida com reflexao espectral
 * - Linha de refracao luminosa no topo
 * - Fisica de mola tatil e micro-elevacao ao toque
 * - Suporte a clique simples e toque longo (long-press para menu contextual)
 */
@OptIn(ExperimentalFoundationApi::class)
@Composable
fun SpatialGlassCard(
    modifier: Modifier = Modifier,
    shape: Shape = RoundedCornerShape(22.dp),
    accent: Color? = null,
    glowActive: Boolean = false,
    iridescentBorder: Boolean = true,
    onClick: (() -> Unit)? = null,
    onLongClick: (() -> Unit)? = null,
    contentPadding: PaddingValues = PaddingValues(16.dp),
    content: @Composable () -> Unit
) {
    val interactionSource = remember { MutableInteractionSource() }
    val isPressed by interactionSource.collectIsPressedAsState()
    val scale by animateFloatAsState(
        targetValue = if (isPressed && (onClick != null || onLongClick != null)) 0.978f else 1f,
        animationSpec = spring(dampingRatio = 0.68f, stiffness = 420f),
        label = "spatialCardScale"
    )

    val glowAlpha = if (glowActive) {
        val transition = rememberInfiniteTransition(label = "spatialGlowPulse")
        transition.animateFloat(
            initialValue = 0.50f,
            targetValue = 1.0f,
            animationSpec = infiniteRepeatable(tween(1600, easing = LinearEasing), RepeatMode.Reverse),
            label = "spatialGlowAlpha"
        ).value
    } else 1f

    val borderBrush = when {
        glowActive && accent != null -> Brush.linearGradient(
            listOf(accent.copy(alpha = glowAlpha), accent.copy(alpha = glowAlpha * 0.45f))
        )
        glowActive -> LiquidIridescentBorderBrush
        accent != null -> Brush.verticalGradient(
            listOf(accent.copy(alpha = 0.70f), OutlineSoft)
        )
        iridescentBorder -> LiquidIridescentBorderBrush
        else -> GlassBorderBrush
    }

    var base = modifier
        .graphicsLayer {
            scaleX = scale
            scaleY = scale
            cameraDistance = 12f * density
        }
        .clip(shape)
        .background(LiquidGlassSurfaceBrush)
        .drawBehind {
            // Linha de refracao liquida / highlight especular na borda superior
            drawLine(
                brush = Brush.horizontalGradient(
                    listOf(Color.Transparent, LiquidSpecularHighlight, Color.Transparent)
                ),
                start = Offset(0f, 1.2f),
                end = Offset(size.width, 1.2f),
                strokeWidth = 1.5.dp.toPx()
            )
        }
        .border(BorderStroke(1.dp, borderBrush), shape)

    if (onClick != null || onLongClick != null) {
        val haptic = LocalHapticFeedback.current
        base = base.combinedClickable(
            interactionSource = interactionSource,
            indication = null,
            onClick = {
                if (onClick != null) {
                    haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                    onClick()
                }
            },
            onLongClick = {
                if (onLongClick != null) {
                    haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                    onLongClick()
                }
            }
        )
    }

    Box(base.padding(contentPadding)) { content() }
}

/**
 * Pilula Cilindrica Liquid Glass com reflexo e status
 */
@Composable
fun LiquidGlassPill(
    text: String,
    modifier: Modifier = Modifier,
    icon: ImageVector? = null,
    accentColor: Color = AuraCyan,
    pulsingDot: Boolean = false,
    onClick: (() -> Unit)? = null
) {
    val haptic = LocalHapticFeedback.current
    val shape = RoundedCornerShape(50)

    var baseModifier = modifier
        .clip(shape)
        .background(ObsidianMid.copy(alpha = 0.85f))
        .drawBehind {
            drawLine(
                brush = Brush.horizontalGradient(
                    listOf(Color.Transparent, LiquidSpecularHighlight.copy(alpha = 0.5f), Color.Transparent)
                ),
                start = Offset(0f, 1f),
                end = Offset(size.width, 1f),
                strokeWidth = 1.dp.toPx()
            )
        }
        .border(1.dp, accentColor.copy(alpha = 0.35f), shape)

    if (onClick != null) {
        baseModifier = baseModifier.clickable {
            haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
            onClick()
        }
    }

    Box(
        modifier = baseModifier.padding(horizontal = 12.dp, vertical = 6.dp),
        contentAlignment = Alignment.Center
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            if (pulsingDot) {
                StatusDot(color = accentColor, size = 6.dp, pulsing = true)
            } else if (icon != null) {
                Icon(
                    imageVector = icon,
                    contentDescription = null,
                    tint = accentColor,
                    modifier = Modifier.size(13.dp)
                )
            }
            Text(
                text = text,
                style = MaterialTheme.typography.labelSmall,
                color = TextPrimary,
                fontWeight = FontWeight.Medium
            )
        }
    }
}

/**
 * Acordeão de Raciocínio Transparente (Chain-of-Thought Audit Trail)
 * Apresenta as ferramentas, consultas ERP e validações ANP executadas pela IA em tempo real ou no histórico.
 */
@Composable
fun AuraReasoningAccordion(
    reasoningSteps: List<String>,
    isStreaming: Boolean,
    modifier: Modifier = Modifier,
    initialExpanded: Boolean = false
) {
    if (reasoningSteps.isEmpty() && !isStreaming) return

    var isExpanded by remember { mutableStateOf(initialExpanded || isStreaming) }
    val haptic = LocalHapticFeedback.current
    val chevronRotation by animateFloatAsState(
        targetValue = if (isExpanded) 180f else 0f,
        animationSpec = spring(stiffness = 400f),
        label = "accordionChevron"
    )

    Column(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .background(ObsidianLow.copy(alpha = 0.70f))
            .border(
                1.dp,
                if (isStreaming) AuraCyan.copy(alpha = 0.40f) else OutlineSoft.copy(alpha = 0.50f),
                RoundedCornerShape(14.dp)
            )
            .padding(10.dp)
    ) {
        // Cabeçalho do Acordeão (Pill clicável)
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .clickable {
                    haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                    isExpanded = !isExpanded
                },
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.weight(1f)
            ) {
                if (isStreaming) {
                    StatusDot(color = AuraCyan, size = 6.dp, pulsing = true)
                    Text(
                        text = "Raciocinando... (${reasoningSteps.size} etapas)",
                        style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.SemiBold),
                        color = AuraCyan
                    )
                } else {
                    StatusDot(color = AuraEmerald, size = 6.dp, pulsing = false)
                    Text(
                        text = "${reasoningSteps.size} etapas de análise executadas",
                        style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Medium),
                        color = TextSecondary
                    )
                }
            }

            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                Text(
                    text = if (isExpanded) "Ocultar" else "Ver trilha",
                    style = MaterialTheme.typography.labelSmall,
                    color = TextMuted
                )
                Icon(
                    imageVector = Icons.Filled.KeyboardArrowDown,
                    contentDescription = null,
                    tint = TextMuted,
                    modifier = Modifier
                        .size(16.dp)
                        .graphicsLayer { rotationZ = chevronRotation }
                )
            }
        }

        // Conteúdo Expandido: Linha do tempo de etapas executadas
        AnimatedVisibility(
            visible = isExpanded,
            enter = expandVertically(spring(stiffness = 500f)) + fadeIn(tween(200)),
            exit = shrinkVertically(spring(stiffness = 500f)) + fadeOut(tween(150))
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 10.dp, start = 4.dp, end = 4.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(1.dp)
                        .background(OutlineSoft.copy(alpha = 0.5f))
                )

                reasoningSteps.forEachIndexed { index, step ->
                    val isLast = index == reasoningSteps.lastIndex
                    val isCurrentRunning = isStreaming && isLast

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp),
                        verticalAlignment = Alignment.Top
                    ) {
                        Box(
                            modifier = Modifier.padding(top = 3.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            if (isCurrentRunning) {
                                StatusDot(color = AuraCyan, size = 7.dp, pulsing = true)
                            } else {
                                Box(
                                    modifier = Modifier
                                        .size(14.dp)
                                        .clip(CircleShape)
                                        .background(AuraEmerald.copy(alpha = 0.15f))
                                        .border(1.dp, AuraEmerald.copy(alpha = 0.40f), CircleShape),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Icon(
                                        imageVector = Icons.Filled.Check,
                                        contentDescription = null,
                                        tint = AuraEmerald,
                                        modifier = Modifier.size(10.dp)
                                    )
                                }
                            }
                        }

                        Text(
                            text = step,
                            style = MaterialTheme.typography.bodySmall.copy(
                                lineHeight = 16.sp,
                                color = if (isCurrentRunning) AuraCyan else TextSecondary
                            ),
                            modifier = Modifier.weight(1f)
                        )
                    }
                }

                // Rodapé de auditoria
                Text(
                    text = "Trilha auditável de telemetria, ERP e ANP",
                    style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp),
                    color = TextMuted,
                    modifier = Modifier.padding(top = 4.dp)
                )
            }
        }
    }
}

/**
 * Orbe Vivo e Fluido da AURA (Dynamic Liquid Plasma Consciousness)
 * Ondula em fluxo orgânico contínuo em repouso e reage com ondas senoidais
 * harmônicas de alta fidelidade à amplitude e tons de voz (60fps).
 */
@Composable
fun AuraLivingOrb(
    modifier: Modifier = Modifier,
    sizeDp: Dp = 40.dp,
    voiceRms: Float = 0.05f,
    pulsing: Boolean = true
) {
    val infiniteTransition = rememberInfiniteTransition(label = "livingOrbInfinite")

    // Tempo contínuo para fluxo líquido das ondas (60fps)
    val timePhase by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 2f * Math.PI.toFloat(),
        animationSpec = infiniteRepeatable(
            animation = tween(3800, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "timePhase"
    )

    // Respiração orgânica lenta (mesmo no silêncio absoluto)
    val idleBreath by infiniteTransition.animateFloat(
        initialValue = 0.90f,
        targetValue = 1.10f,
        animationSpec = infiniteRepeatable(
            animation = tween(2200, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "idleBreath"
    )

    // Amortecimento suave do RMS da voz para eliminar saltos rígidos
    val smoothRms by animateFloatAsState(
        targetValue = voiceRms.coerceIn(0.05f, 1.0f),
        animationSpec = spring(stiffness = 300f, dampingRatio = 0.70f),
        label = "smoothRms"
    )

    Box(
        modifier = modifier.size(sizeDp),
        contentAlignment = Alignment.Center
    ) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            val center = Offset(size.width / 2f, size.height / 2f)
            val baseRadius = (size.minDimension / 2.6f) * (if (pulsing) idleBreath else 1f)

            // 1. Halo Difuso Atmosférico
            val haloRadius = baseRadius * (1.6f + (smoothRms * 0.70f))
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(
                        AuraCyan.copy(alpha = 0.40f * (0.5f + smoothRms * 0.5f)),
                        AuraPurple.copy(alpha = 0.25f * (0.5f + smoothRms * 0.5f)),
                        Color.Transparent
                    ),
                    center = center,
                    radius = haloRadius
                ),
                radius = haloRadius,
                center = center
            )

            // 2. Ondas Harmônicas de Ressonância (Ondulação líquida polar)
            val steps = 36
            val stepAngle = (2f * Math.PI.toFloat()) / steps

            // Função geradora de contorno orgânico líquido
            fun buildLiquidPath(phaseOffset: Float, rMultiplier: Float, waveAmp: Float): Path {
                val path = Path()
                val points = ArrayList<Offset>(steps)

                for (i in 0 until steps) {
                    val angle = i * stepAngle
                    // Modulação harmônica com 3 frequências (octaves) senoidais
                    val harm1 = sin(3f * angle + timePhase + phaseOffset) * (0.09f + waveAmp * 0.22f)
                    val harm2 = cos(2f * angle - (timePhase * 1.3f) + phaseOffset) * (0.07f + waveAmp * 0.18f)
                    val harm3 = sin(4f * angle + (timePhase * 0.8f)) * (0.05f + waveAmp * 0.12f)

                    val r = baseRadius * rMultiplier * (1f + harm1 + harm2 + harm3)
                    val x = center.x + r * cos(angle.toDouble()).toFloat()
                    val y = center.y + r * sin(angle.toDouble()).toFloat()
                    points.add(Offset(x, y))
                }

                // Interpolação Bézier quadrática suave entre os pontos médios
                val firstMid = Offset(
                    (points[0].x + points[steps - 1].x) / 2f,
                    (points[0].y + points[steps - 1].y) / 2f
                )
                path.moveTo(firstMid.x, firstMid.y)

                for (i in 0 until steps) {
                    val current = points[i]
                    val next = points[(i + 1) % steps]
                    val mid = Offset((current.x + next.x) / 2f, (current.y + next.y) / 2f)
                    path.quadraticBezierTo(current.x, current.y, mid.x, mid.y)
                }
                path.close()
                return path
            }

            // Camada 1: Manto Líquido Externo
            val outerPath = buildLiquidPath(phaseOffset = 0f, rMultiplier = 1.0f + (smoothRms * 0.25f), waveAmp = smoothRms)
            drawPath(
                path = outerPath,
                brush = Brush.sweepGradient(
                    colors = listOf(
                        AuraCyan.copy(alpha = 0.88f),
                        AuraEmerald.copy(alpha = 0.80f),
                        AuraPurple.copy(alpha = 0.85f),
                        AuraCyan.copy(alpha = 0.88f)
                    ),
                    center = center
                )
            )

            // Borda iridescente fina de vidro líquido contornando a onda
            drawPath(
                path = outerPath,
                brush = Brush.linearGradient(
                    colors = listOf(
                        Color.White.copy(alpha = 0.85f),
                        AuraCyan.copy(alpha = 0.40f),
                        Color.White.copy(alpha = 0.75f)
                    )
                ),
                style = Stroke(width = 1.4.dp.toPx())
            )

            // Camada 2: Núcleo Secundário Contra-Rotativo (Efeito Moire Cósmico)
            val innerPath = buildLiquidPath(phaseOffset = 2.1f, rMultiplier = 0.78f, waveAmp = smoothRms * 0.8f)
            drawPath(
                path = innerPath,
                brush = Brush.radialGradient(
                    colors = listOf(
                        AuraPurple.copy(alpha = 0.70f),
                        AuraCyan.copy(alpha = 0.85f),
                        Color.Transparent
                    ),
                    center = center,
                    radius = baseRadius * 0.95f
                )
            )

            // Camada 3: Núcleo Incandescente de Plasma Branco/Ciano
            val coreR = baseRadius * 0.38f * (1f + smoothRms * 0.30f)
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(
                        Color.White,
                        Color.White.copy(alpha = 0.92f),
                        AuraCyan.copy(alpha = 0.85f),
                        Color.Transparent
                    ),
                    center = center,
                    radius = coreR
                ),
                radius = coreR,
                center = center
            )

            // Centelha Diamante no Centro
            drawCircle(
                color = Color.White,
                radius = baseRadius * 0.12f,
                center = center
            )
        }
    }
}

/**
 * Orbe de Voz Holográfico Reativo (Push-to-Talk Hands-Free da AURA)
 * Apresenta a consciência viva da AURA reagindo à voz e transcrição em tempo real.
 */
@Composable
fun AuraVoiceOrbSheet(
    isListening: Boolean,
    spokenText: String,
    voiceRms: Float,
    onCancel: () -> Unit,
    onSend: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    if (!isListening && spokenText.isBlank()) return

    val haptic = LocalHapticFeedback.current

    Column(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp))
            .background(LiquidGlassElevatedBrush)
            .border(1.dp, LiquidIridescentBorderBrush, RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp))
            .padding(horizontal = 20.dp, vertical = 18.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Barra Superior
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                StatusDot(color = AuraCyan, size = 8.dp, pulsing = true)
                SectionLabel(if (isListening) "AURA SINTONIZADA • OUVINDO" else "TRANSCRIÇÃO CONCLUÍDA")
            }

            AuraGhostButton(
                text = "Cancelar",
                onClick = onCancel,
                tint = TextMuted
            )
        }

        // Orbe Vivo da AURA (Consciência visual orgânica líquida)
        AuraLivingOrb(
            sizeDp = 140.dp,
            voiceRms = voiceRms,
            pulsing = true
        )

        // Pré-visualização do texto falado
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(16.dp))
                .background(ObsidianMid)
                .border(1.dp, OutlineSoft.copy(alpha = 0.40f), RoundedCornerShape(16.dp))
                .padding(14.dp),
            contentAlignment = Alignment.Center
        ) {
            if (spokenText.isBlank()) {
                Text(
                    text = "AURA está ouvindo... Fale sobre bombas, tanques ou fechamento",
                    style = MaterialTheme.typography.bodyMedium,
                    color = TextMuted,
                    textAlign = TextAlign.Center
                )
            } else {
                Text(
                    text = "\"$spokenText\"",
                    style = MaterialTheme.typography.bodyLarge.copy(
                        fontWeight = FontWeight.Medium,
                        color = TextPrimary
                    ),
                    textAlign = TextAlign.Center
                )
            }
        }

        // Botões de Ação
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            AuraGhostButton(
                text = "Descartar",
                onClick = onCancel,
                modifier = Modifier.weight(1f)
            )

            val canSend = spokenText.isNotBlank()
            AuraGradientButton(
                text = "Enviar Pergunta",
                onClick = {
                    if (canSend) {
                        haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                        onSend(spokenText)
                    }
                },
                modifier = Modifier.weight(1.5f),
                enabled = canSend
            )
        }
    }
}

// ============================================================================
// PILAR 3: AURA DYNAMIC ISLAND & BOTTOM GLASS DOCK (SPATIAL UI DELUXE)
// ============================================================================

/** Telemetria em tempo real da pista consumida pela Aura Dynamic Island. */
data class AuraIslandTelemetry(
    val tankAlert: String = "T-01: 18%",
    val isTankAlertCritical: Boolean = true,
    val todayVolume: String = "42.8k L",
    val anpStatus: String = "LMC ±0.18%",
    val tankDetail: String = "T-01 Gasolina Comum • 3.600 L / 20.000 L • Autonomia: 6.4 h",
    val lmcDetail: String = "Variação LMC hoje: +0.18% (Tolerância legal ANP: ±0.60%)",
    val shiftDetail: String = "Turno Manhã (5.3h abertas) • Sangrias 100% conciliadas"
)

/**
 * Aura Dynamic Island: Cápsula de telemetria operacional com micro-status ao vivo.
 * Ao tocar, expande via mola elástica (Spring HUD) revelando diagnósticos de tancagem,
 * LMC e conciliação de caixa com gatilhos de 1 toque para o Cockpit AURA.
 */
@Composable
fun AuraDynamicIsland(
    modifier: Modifier = Modifier,
    telemetry: AuraIslandTelemetry = remember { AuraIslandTelemetry() },
    onQueryAction: (String) -> Unit
) {
    var expanded by remember { mutableStateOf(false) }
    val haptic = LocalHapticFeedback.current

    Box(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 4.dp),
        contentAlignment = Alignment.Center
    ) {
        Surface(
            modifier = Modifier
                .animateContentSize(
                    animationSpec = spring(
                        dampingRatio = 0.82f,
                        stiffness = 380f
                    )
                ),
            shape = if (expanded) RoundedCornerShape(22.dp) else RoundedCornerShape(50),
            color = ObsidianMid.copy(alpha = 0.94f),
            border = BorderStroke(
                width = 1.dp,
                brush = if (expanded) LiquidIridescentBorderBrush else LiquidIridescentSubtleBrush
            ),
            shadowElevation = if (expanded) 10.dp else 2.dp
        ) {
            Column(
                modifier = Modifier
                    .then(
                        if (expanded) Modifier.fillMaxWidth().padding(14.dp)
                        else Modifier.padding(horizontal = 14.dp, vertical = 7.dp)
                    )
            ) {
                if (!expanded) {
                    // Cápsula Compacta
                    Row(
                        modifier = Modifier
                            .clickable(
                                interactionSource = remember { MutableInteractionSource() },
                                indication = null
                            ) {
                                haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                                expanded = true
                            },
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        StatusDot(
                            color = if (telemetry.isTankAlertCritical) StatusWarning else StatusSuccess,
                            size = 7.dp,
                            pulsing = true
                        )
                        Icon(
                            imageVector = Icons.Rounded.LocalGasStation,
                            contentDescription = null,
                            tint = if (telemetry.isTankAlertCritical) StatusWarning else AuraCyan,
                            modifier = Modifier.size(13.dp)
                        )
                        Text(
                            text = telemetry.tankAlert,
                            style = MaterialTheme.typography.labelSmall.copy(
                                fontWeight = FontWeight.SemiBold,
                                fontSize = 11.sp
                            ),
                            color = TextPrimary
                        )

                        Text(
                            text = "•",
                            style = MaterialTheme.typography.labelSmall,
                            color = TextMuted.copy(alpha = 0.45f)
                        )

                        Text(
                            text = "📊 ${telemetry.todayVolume}",
                            style = MaterialTheme.typography.labelSmall.copy(fontSize = 11.sp),
                            color = TextSecondary
                        )

                        Text(
                            text = "•",
                            style = MaterialTheme.typography.labelSmall,
                            color = TextMuted.copy(alpha = 0.45f)
                        )

                        Text(
                            text = "🛡️ ${telemetry.anpStatus}",
                            style = MaterialTheme.typography.labelSmall.copy(
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Medium
                            ),
                            color = AuraEmerald
                        )

                        Spacer(modifier = Modifier.width(2.dp))

                        Icon(
                            imageVector = Icons.Filled.KeyboardArrowDown,
                            contentDescription = "Expandir HUD",
                            tint = TextMuted,
                            modifier = Modifier.size(15.dp)
                        )
                    }
                } else {
                    // HUD Expandido
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(6.dp)
                        ) {
                            StatusDot(color = AuraCyan, size = 6.dp, pulsing = true)
                            Text(
                                text = "TELEMETRIA AO VIVO DA PISTA",
                                style = MaterialTheme.typography.labelSmall.copy(
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 10.sp,
                                    letterSpacing = 0.8.sp
                                ),
                                color = AuraCyan
                            )
                        }

                        Icon(
                            imageVector = Icons.Filled.KeyboardArrowUp,
                            contentDescription = "Recolher HUD",
                            tint = TextSecondary,
                            modifier = Modifier
                                .size(22.dp)
                                .clip(CircleShape)
                                .clickable {
                                    haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                                    expanded = false
                                }
                        )
                    }

                    Spacer(modifier = Modifier.height(10.dp))

                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        // 1. Tanques & Autonomia
                        IslandDiagnosticItem(
                            icon = Icons.Rounded.LocalGasStation,
                            badgeColor = StatusWarning,
                            title = "Tanques & Autonomia",
                            headline = telemetry.tankDetail,
                            actionLabel = "Simular Compra 5.000 L",
                            onAction = {
                                haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                                expanded = false
                                onQueryAction("Simular compra de combustível para abastecer o T-01 considerando compartimentos de 5.000 L")
                            }
                        )

                        // 2. Livro Fiscal LMC ANP
                        IslandDiagnosticItem(
                            icon = Icons.Rounded.Assessment,
                            badgeColor = AuraEmerald,
                            title = "Livro Fiscal LMC (ANP)",
                            headline = telemetry.lmcDetail,
                            actionLabel = "Auditar LMC",
                            onAction = {
                                haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                                expanded = false
                                onQueryAction("Gere o relatório completo do LMC ANP de hoje.")
                            }
                        )

                        // 3. Fechamento de Turno & Sangrias
                        IslandDiagnosticItem(
                            icon = Icons.Rounded.PointOfSale,
                            badgeColor = AuraPurple,
                            title = "Conciliação de Turno & Caixa",
                            headline = telemetry.shiftDetail,
                            actionLabel = "Auditar Turno",
                            onAction = {
                                haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                                expanded = false
                                onQueryAction("Audite o fechamento de turno de hoje.")
                            }
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun IslandDiagnosticItem(
    icon: ImageVector,
    badgeColor: Color,
    title: String,
    headline: String,
    actionLabel: String,
    onAction: () -> Unit
) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(ObsidianBase.copy(alpha = 0.60f))
            .border(1.dp, OutlineSoft.copy(alpha = 0.35f), RoundedCornerShape(12.dp))
            .padding(10.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(34.dp)
                    .clip(CircleShape)
                    .background(badgeColor.copy(alpha = 0.15f)),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = icon,
                    contentDescription = null,
                    tint = badgeColor,
                    modifier = Modifier.size(17.dp)
                )
            }

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = title,
                    style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                    color = TextPrimary
                )
                Text(
                    text = headline,
                    style = MaterialTheme.typography.bodySmall.copy(fontSize = 11.sp, lineHeight = 14.sp),
                    color = TextSecondary,
                    maxLines = 2
                )
            }

            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(50))
                    .background(AuroraBrush)
                    .clickable(onClick = onAction)
                    .padding(horizontal = 9.dp, vertical = 6.dp)
            ) {
                Text(
                    text = actionLabel,
                    style = MaterialTheme.typography.labelSmall.copy(
                        fontWeight = FontWeight.Bold,
                        fontSize = 10.sp
                    ),
                    color = Color.White
                )
            }
        }
    }
}

/** Abas de navegação do Dock Espacial da AURA. */
enum class AuraNavTab(
    val label: String,
    val icon: ImageVector
) {
    PULSO("Pulso", Icons.Rounded.Assessment),
    COCKPIT("Cockpit", Icons.Rounded.AutoAwesome),
    TANQUES("Tanques", Icons.Rounded.LocalGasStation),
    CONEXAO("Servidor", Icons.Rounded.Tune)
}

/**
 * Aura Bottom Glass Dock: Barra de navegação espacial translúcida com Liquid Glassmorphism,
 * borda iridescente especular e micro-interações táteis para alternar entre Pulso, Cockpit, Tanques e Servidor.
 */
@Composable
fun AuraBottomGlassDock(
    selectedTab: AuraNavTab,
    onTabSelected: (AuraNavTab) -> Unit,
    modifier: Modifier = Modifier
) {
    val haptic = LocalHapticFeedback.current

    Box(
        modifier = modifier
            .fillMaxWidth()
            .navigationBarsPadding()
            .padding(horizontal = 20.dp, vertical = 8.dp),
        contentAlignment = Alignment.Center
    ) {
        Surface(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(28.dp),
            color = ObsidianMid.copy(alpha = 0.90f),
            border = BorderStroke(1.2.dp, LiquidIridescentBorderBrush),
            shadowElevation = 10.dp
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 8.dp, vertical = 6.dp),
                horizontalArrangement = Arrangement.SpaceAround,
                verticalAlignment = Alignment.CenterVertically
            ) {
                AuraNavTab.values().forEach { tab ->
                    val isSelected = tab == selectedTab
                    val interactionSource = remember { MutableInteractionSource() }
                    val isPressed by interactionSource.collectIsPressedAsState()
                    val scale by animateFloatAsState(
                        targetValue = if (isPressed) 0.92f else 1f,
                        animationSpec = spring(dampingRatio = 0.7f, stiffness = 400f),
                        label = "dockTabScale"
                    )

                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .graphicsLayer {
                                scaleX = scale
                                scaleY = scale
                            }
                            .clip(RoundedCornerShape(20.dp))
                            .then(
                                if (isSelected) {
                                    Modifier
                                        .background(
                                            Brush.horizontalGradient(
                                                listOf(
                                                    AuraCyan.copy(alpha = 0.20f),
                                                    AuraPurple.copy(alpha = 0.15f)
                                                )
                                            )
                                        )
                                        .border(
                                            1.dp,
                                            AuraCyan.copy(alpha = 0.40f),
                                            RoundedCornerShape(20.dp)
                                        )
                                } else {
                                    Modifier
                                }
                            )
                            .clickable(
                                interactionSource = interactionSource,
                                indication = null
                            ) {
                                haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                                onTabSelected(tab)
                            }
                            .padding(vertical = 8.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(3.dp)
                        ) {
                            Icon(
                                imageVector = tab.icon,
                                contentDescription = tab.label,
                                tint = if (isSelected) AuraCyan else TextMuted,
                                modifier = Modifier.size(20.dp)
                            )
                            Text(
                                text = tab.label,
                                style = MaterialTheme.typography.labelSmall.copy(
                                    fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                                    fontSize = 10.5.sp
                                ),
                                color = if (isSelected) TextPrimary else TextMuted
                            )
                        }
                    }
                }
            }
        }
    }
}




