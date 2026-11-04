package com.example.aurapostoassitance.ui.components

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.TrendingUp
import androidx.compose.material.icons.rounded.Assessment
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material.icons.rounded.Close
import androidx.compose.material.icons.rounded.ContentCopy
import androidx.compose.material.icons.rounded.Forum
import androidx.compose.material.icons.rounded.LocalGasStation
import androidx.compose.material.icons.rounded.Psychology
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material.icons.rounded.Security
import androidx.compose.material.icons.rounded.Share
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.aurapostoassitance.ui.theme.AuraCyan
import com.example.aurapostoassitance.ui.theme.AuraEmerald
import com.example.aurapostoassitance.ui.theme.AuraPurple
import com.example.aurapostoassitance.ui.theme.LiquidGlassElevatedBrush
import com.example.aurapostoassitance.ui.theme.LiquidIridescentBorderBrush
import com.example.aurapostoassitance.ui.theme.LiquidSpecularHighlight
import com.example.aurapostoassitance.ui.theme.ObsidianLow
import com.example.aurapostoassitance.ui.theme.ObsidianMid
import com.example.aurapostoassitance.ui.theme.OutlineSoft
import com.example.aurapostoassitance.ui.theme.TextMuted
import com.example.aurapostoassitance.ui.theme.TextPrimary
import com.example.aurapostoassitance.ui.theme.TextSecondary

/** Ações disponíveis no Menu de Contexto de Mensagens da AURA */
enum class AuraMessageActionType {
    COPY,
    DEEP_DIVE,
    AUDIT_ANP,
    REGENERATE,
    SHARE
}

/**
 * Menu de Contexto Spatial Liquid Glass acionado por long-press ou toque contextual na mensagem.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AuraMessageContextMenuSheet(
    messageText: String,
    isAuraMessage: Boolean,
    onDismiss: () -> Unit,
    onActionSelected: (AuraMessageActionType) -> Unit
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    val context = LocalContext.current
    val haptic = LocalHapticFeedback.current
    val view = LocalView.current

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = ObsidianLow,
        scrimColor = Color.Black.copy(alpha = 0.65f),
        shape = RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .navigationBarsPadding()
                .padding(horizontal = 20.dp)
                .padding(bottom = 24.dp)
        ) {
            // Header do Menu
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Box(
                    modifier = Modifier
                        .size(36.dp)
                        .clip(CircleShape)
                        .background(if (isAuraMessage) AuraCyan.copy(alpha = 0.15f) else AuraPurple.copy(alpha = 0.15f)),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = if (isAuraMessage) Icons.Rounded.AutoAwesome else Icons.Rounded.Psychology,
                        contentDescription = null,
                        tint = if (isAuraMessage) AuraCyan else AuraPurple,
                        modifier = Modifier.size(18.dp)
                    )
                }
                Column {
                    Text(
                        text = if (isAuraMessage) "Ações na Resposta AURA" else "Opções da Pergunta",
                        style = MaterialTheme.typography.titleMedium,
                        color = TextPrimary,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = "Toque rápido para interações cognitivas do posto",
                        style = MaterialTheme.typography.labelSmall,
                        color = TextMuted
                    )
                }
            }

            Spacer(Modifier.height(14.dp))

            // Prévia do texto com visual de vidro
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(14.dp))
                    .background(ObsidianMid)
                    .border(1.dp, OutlineSoft, RoundedCornerShape(14.dp))
                    .padding(12.dp)
            ) {
                Text(
                    text = messageText.take(160) + if (messageText.length > 160) "..." else "",
                    style = MaterialTheme.typography.bodySmall,
                    color = TextSecondary,
                    maxLines = 3,
                    overflow = TextOverflow.Ellipsis
                )
            }

            Spacer(Modifier.height(18.dp))

            // Lista de ações
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                ContextMenuItem(
                    icon = Icons.Rounded.ContentCopy,
                    title = "Copiar Texto Completo",
                    subtitle = "Copia para a área de transferência do dispositivo",
                    accentColor = AuraCyan,
                    onClick = {
                        AuraHaptics.heavy(view, haptic)
                        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                        val clip = ClipData.newPlainText("Aura Message", messageText)
                        clipboard.setPrimaryClip(clip)
                        Toast.makeText(context, "Texto copiado para a área de transferência!", Toast.LENGTH_SHORT).show()
                        onActionSelected(AuraMessageActionType.COPY)
                        onDismiss()
                    }
                )

                if (isAuraMessage) {
                    ContextMenuItem(
                        icon = Icons.Rounded.Psychology,
                        title = "Aprofundar Raciocínio (Deep Dive)",
                        subtitle = "Inspeção cognitiva de fórmulas, premissas e fontes",
                        accentColor = AuraEmerald,
                        onClick = {
                            AuraHaptics.heavy(view, haptic)
                            onActionSelected(AuraMessageActionType.DEEP_DIVE)
                            onDismiss()
                        }
                    )

                    ContextMenuItem(
                        icon = Icons.Rounded.Security,
                        title = "Auditar Regra ANP & Fiscal",
                        subtitle = "Valide a conformidade com LMC, tolerância legal e Portarias",
                        accentColor = AuraPurple,
                        onClick = {
                            AuraHaptics.heavy(view, haptic)
                            onActionSelected(AuraMessageActionType.AUDIT_ANP)
                            onDismiss()
                        }
                    )

                    ContextMenuItem(
                        icon = Icons.Rounded.Refresh,
                        title = "Regenerar com Outra Perspectiva",
                        subtitle = "Sintetizar novamente com mais concisão ou mais dados",
                        accentColor = AuraCyan,
                        onClick = {
                            AuraHaptics.heavy(view, haptic)
                            onActionSelected(AuraMessageActionType.REGENERATE)
                            onDismiss()
                        }
                    )
                }

                ContextMenuItem(
                    icon = Icons.Rounded.Share,
                    title = "Compartilhar Diagnóstico",
                    subtitle = "Enviar via WhatsApp, Telegram ou e-mail corporativo",
                    accentColor = Color(0xFF38BDF8),
                    onClick = {
                        AuraHaptics.heavy(view, haptic)
                        val shareIntent = Intent(Intent.ACTION_SEND).apply {
                            type = "text/plain"
                            putExtra(Intent.EXTRA_SUBJECT, "Diagnóstico AURA - Posto de Combustíveis")
                            putExtra(Intent.EXTRA_TEXT, messageText)
                        }
                        context.startActivity(Intent.createChooser(shareIntent, "Compartilhar via"))
                        onActionSelected(AuraMessageActionType.SHARE)
                        onDismiss()
                    }
                )
            }
        }
    }
}

/** Item individual do menu de contexto com feedback tátil e iluminação de vidro */
@Composable
private fun ContextMenuItem(
    icon: ImageVector,
    title: String,
    subtitle: String,
    accentColor: Color,
    onClick: () -> Unit
) {
    val interactionSource = remember { MutableInteractionSource() }
    val isPressed by interactionSource.collectIsPressedAsState()
    val shape = RoundedCornerShape(16.dp)

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(shape)
            .background(if (isPressed) accentColor.copy(alpha = 0.12f) else ObsidianMid)
            .drawBehind {
                drawLine(
                    brush = Brush.horizontalGradient(
                        listOf(Color.Transparent, LiquidSpecularHighlight.copy(alpha = 0.35f), Color.Transparent)
                    ),
                    start = Offset(0f, 1f),
                    end = Offset(size.width, 1f),
                    strokeWidth = 1.dp.toPx()
                )
            }
            .border(
                1.dp,
                if (isPressed) accentColor.copy(alpha = 0.45f) else OutlineSoft,
                shape
            )
            .clickable(
                interactionSource = interactionSource,
                indication = null,
                onClick = onClick
            )
            .padding(horizontal = 14.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(40.dp)
                .clip(CircleShape)
                .background(accentColor.copy(alpha = 0.15f))
                .border(1.dp, accentColor.copy(alpha = 0.30f), CircleShape),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = accentColor,
                modifier = Modifier.size(20.dp)
            )
        }
        Spacer(Modifier.width(14.dp))
        Column(Modifier.weight(1f)) {
            Text(
                text = title,
                style = MaterialTheme.typography.bodyMedium,
                color = TextPrimary,
                fontWeight = FontWeight.SemiBold
            )
            Text(
                text = subtitle,
                style = MaterialTheme.typography.labelSmall,
                color = TextMuted,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
        }
    }
}

/**
 * Aura Command Hub:
 * Menu suspenso de ações contextuais do posto integrado ao Composer.
 * Permite alternar modo cognitivo (Pista, Gerência, Compliance) e injetar filtros inteligentes.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AuraQuickCommandHubSheet(
    onDismiss: () -> Unit,
    onSelectMode: (modeTitle: String, promptPrefix: String) -> Unit,
    onInjectFilter: (filterQuery: String) -> Unit
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    val haptic = LocalHapticFeedback.current

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = ObsidianLow,
        scrimColor = Color.Black.copy(alpha = 0.70f),
        shape = RoundedCornerShape(topStart = 32.dp, topEnd = 32.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .navigationBarsPadding()
                .padding(horizontal = 20.dp)
                .padding(bottom = 28.dp)
        ) {
            // Header do Command Hub
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Column {
                    AuraBrandTitle(
                        text = "AURA COMMAND HUB",
                        style = MaterialTheme.typography.titleMedium,
                        letterSpacing = 2.sp
                    )
                    Text(
                        text = "Gatilhos Operacionais & Modos Cognitivos",
                        style = MaterialTheme.typography.labelSmall,
                        color = TextSecondary
                    )
                }
                StatusDot(color = AuraEmerald, size = 8.dp, pulsing = true)
            }

            Spacer(Modifier.height(18.dp))

            SectionLabel("Modos de Análise do Posto")
            Spacer(Modifier.height(10.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                ModeCard(
                    title = "Pista & Frentistas",
                    description = "Bicos, turnos e sangrias imediatas",
                    icon = Icons.Rounded.LocalGasStation,
                    accent = AuraCyan,
                    modifier = Modifier.weight(1f),
                    onClick = {
                        haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                        onSelectMode("Pista", "No contexto operacional da pista e abastecimentos: ")
                        onDismiss()
                    }
                )

                ModeCard(
                    title = "Gerência & DRE",
                    description = "Margem, conciliação e ticket médio",
                    icon = Icons.AutoMirrored.Rounded.TrendingUp,
                    accent = AuraEmerald,
                    modifier = Modifier.weight(1f),
                    onClick = {
                        haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                        onSelectMode("Gerência", "No contexto de gestão financeira e DRE do posto: ")
                        onDismiss()
                    }
                )

                ModeCard(
                    title = "Compliance ANP",
                    description = "LMC ±0.60%, notas e perdas térmicas",
                    icon = Icons.Rounded.Security,
                    accent = AuraPurple,
                    modifier = Modifier.weight(1f),
                    onClick = {
                        haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                        onSelectMode("Compliance", "No contexto de auditoria e conformidade ANP: ")
                        onDismiss()
                    }
                )
            }

            Spacer(Modifier.height(22.dp))

            SectionLabel("Filtros Contextuais Instantâneos")
            Spacer(Modifier.height(10.dp))

            val quickFilters = listOf(
                "Comparar preços da cidade com ANP hoje" to Icons.Rounded.Assessment,
                "Verificar perdas térmicas e desvios de tanques" to Icons.Rounded.LocalGasStation,
                "Auditar divergências de sangria de caixa por turno" to Icons.AutoMirrored.Rounded.TrendingUp,
                "Previsão de run-out (dias restantes de combustível)" to Icons.Rounded.AutoAwesome
            )

            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                quickFilters.forEach { (query, icon) ->
                    ContextMenuItem(
                        icon = icon,
                        title = query,
                        subtitle = "Executar diagnóstico direto na base de dados",
                        accentColor = AuraCyan,
                        onClick = {
                            haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                            onInjectFilter(query)
                            onDismiss()
                        }
                    )
                }
            }
        }
    }
}

/** Card de Modo Cognitivo com acabamento Liquid Glass */
@Composable
private fun ModeCard(
    title: String,
    description: String,
    icon: ImageVector,
    accent: Color,
    modifier: Modifier = Modifier,
    onClick: () -> Unit
) {
    val interactionSource = remember { MutableInteractionSource() }
    val isPressed by interactionSource.collectIsPressedAsState()
    val shape = RoundedCornerShape(18.dp)

    val backgroundBrush = if (isPressed) {
        Brush.linearGradient(listOf(accent.copy(alpha = 0.22f), accent.copy(alpha = 0.12f)))
    } else {
        LiquidGlassElevatedBrush
    }

    val borderBrush = if (isPressed) {
        Brush.linearGradient(listOf(accent.copy(alpha = 0.65f), accent.copy(alpha = 0.45f)))
    } else {
        LiquidIridescentBorderBrush
    }

    Box(
        modifier = modifier
            .clip(shape)
            .background(backgroundBrush)
            .drawBehind {
                drawLine(
                    brush = Brush.horizontalGradient(
                        listOf(Color.Transparent, LiquidSpecularHighlight.copy(alpha = 0.45f), Color.Transparent)
                    ),
                    start = Offset(0f, 1f),
                    end = Offset(size.width, 1f),
                    strokeWidth = 1.dp.toPx()
                )
            }
            .border(1.dp, borderBrush, shape)
            .clickable(
                interactionSource = interactionSource,
                indication = null,
                onClick = onClick
            )
            .padding(12.dp)
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Box(
                modifier = Modifier
                    .size(32.dp)
                    .clip(CircleShape)
                    .background(accent.copy(alpha = 0.18f)),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = icon,
                    contentDescription = null,
                    tint = accent,
                    modifier = Modifier.size(16.dp)
                )
            }
            Text(
                text = title,
                style = MaterialTheme.typography.labelMedium,
                color = TextPrimary,
                fontWeight = FontWeight.Bold,
                maxLines = 1
            )
            Text(
                text = description,
                style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp),
                color = TextMuted,
                lineHeight = 13.sp,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis
            )
        }
    }
}

// ============================================================================
// PILAR 5: AURA DEEP DIVE INSPECTOR (SPATIAL COGNITIVE HUD)
// ============================================================================

/**
 * Aura Deep Dive Inspector: Modal 3D Spatial com Liquid Glassmorphism
 * que disseca o raciocínio, premissas de pista, regras ANP e fórmulas matemáticas da resposta.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AuraDeepDiveModal(
    messageText: String,
    reasoningSteps: List<String> = emptyList(),
    onDismiss: () -> Unit,
    onAskFollowUp: (String) -> Unit
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    val context = LocalContext.current
    val haptic = LocalHapticFeedback.current
    val view = LocalView.current

    // Categorização semântica automática para postos de combustíveis
    val isTanks = messageText.contains("tanque", ignoreCase = true) ||
        messageText.contains("autonomia", ignoreCase = true) ||
        messageText.contains("pane seca", ignoreCase = true) ||
        messageText.contains("litro", ignoreCase = true)
    val isLmc = messageText.contains("lmc", ignoreCase = true) ||
        messageText.contains("anp", ignoreCase = true) ||
        messageText.contains("tolerância", ignoreCase = true) ||
        messageText.contains("fiscal", ignoreCase = true)
    val isCashier = messageText.contains("turno", ignoreCase = true) ||
        messageText.contains("sangria", ignoreCase = true) ||
        messageText.contains("caixa", ignoreCase = true) ||
        messageText.contains("frentista", ignoreCase = true)

    val categoryBadge = when {
        isTanks -> "Tancagem & Autonomia de Pista" to AuraCyan
        isLmc -> "Conformidade Fiscal LMC (ANP)" to AuraEmerald
        isCashier -> "Conciliação de Turno & Caixa" to AuraPurple
        else -> "Inteligência Executiva do Posto" to AuraCyan
    }

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = ObsidianLow,
        scrimColor = Color.Black.copy(alpha = 0.72f),
        shape = RoundedCornerShape(topStart = 32.dp, topEnd = 32.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .navigationBarsPadding()
                .padding(horizontal = 20.dp)
                .verticalScroll(rememberScrollState())
                .padding(bottom = 32.dp)
        ) {
            // Header do Deep Dive
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Box(
                        modifier = Modifier
                            .size(38.dp)
                            .clip(CircleShape)
                            .background(AuraEmerald.copy(alpha = 0.16f))
                            .border(1.dp, AuraEmerald.copy(alpha = 0.35f), CircleShape),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Rounded.Psychology,
                            contentDescription = null,
                            tint = AuraEmerald,
                            modifier = Modifier.size(20.dp)
                        )
                    }
                    Column {
                        Text(
                            text = "AURA DEEP DIVE",
                            style = MaterialTheme.typography.titleMedium.copy(
                                fontWeight = FontWeight.Bold,
                                letterSpacing = 1.sp
                            ),
                            color = TextPrimary
                        )
                        Text(
                            text = "Inspeção Cognitiva & Fundamentação Técnica",
                            style = MaterialTheme.typography.labelSmall,
                            color = TextMuted
                        )
                    }
                }

                IconButton(onClick = onDismiss) {
                    Icon(
                        imageVector = Icons.Rounded.Close,
                        contentDescription = "Fechar",
                        tint = TextSecondary
                    )
                }
            }

            Spacer(Modifier.height(16.dp))

            // Badge de Categoria Semântica
            LiquidGlassPill(
                text = categoryBadge.first,
                accentColor = categoryBadge.second,
                pulsingDot = true
            )

            Spacer(Modifier.height(14.dp))

            // Card do Diagnóstico Analisado
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(16.dp))
                    .background(LiquidGlassElevatedBrush)
                    .drawBehind {
                        drawLine(
                            brush = Brush.horizontalGradient(
                                listOf(Color.Transparent, LiquidSpecularHighlight.copy(alpha = 0.5f), Color.Transparent)
                            ),
                            start = Offset(0f, 1f),
                            end = Offset(size.width, 1f),
                            strokeWidth = 1.2.dp.toPx()
                        )
                    }
                    .border(1.dp, LiquidIridescentBorderBrush, RoundedCornerShape(16.dp))
                    .padding(14.dp)
            ) {
                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text(
                        text = "DIAGNÓSTICO ANALISADO",
                        style = MaterialTheme.typography.labelSmall.copy(
                            fontWeight = FontWeight.Bold,
                            letterSpacing = 0.8.sp
                        ),
                        color = categoryBadge.second
                    )
                    Text(
                        text = messageText,
                        style = MaterialTheme.typography.bodyMedium.copy(lineHeight = 20.sp),
                        color = TextPrimary
                    )
                }
            }

            Spacer(Modifier.height(20.dp))

            // Trilha de Inferência / Raciocínio Passo a Passo
            SectionLabel("Trilha de Inferência (Chain of Thought)")
            Spacer(Modifier.height(10.dp))

            val stepsToRender = if (reasoningSteps.isNotEmpty()) {
                reasoningSteps
            } else {
                listOf(
                    "Telemetria da Pista: Leitura de bicos, níveis de tanques e encerrantes eletrônicos.",
                    "Compliance & Fórmulas Legais: Aplicação de limites de tolerância fiscal ANP (±0.60%) e vazões.",
                    "Síntese Estratégica: Validação de risco de pane seca e conciliação financeira de sangrias."
                )
            }

            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                stepsToRender.forEachIndexed { index, step ->
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(12.dp))
                            .background(ObsidianMid)
                            .border(1.dp, OutlineSoft.copy(alpha = 0.35f), RoundedCornerShape(12.dp))
                            .padding(12.dp)
                    ) {
                        Row(
                            verticalAlignment = Alignment.Top,
                            horizontalArrangement = Arrangement.spacedBy(10.dp)
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(24.dp)
                                    .clip(CircleShape)
                                    .background(AuraCyan.copy(alpha = 0.15f)),
                                contentAlignment = Alignment.Center
                            ) {
                                Text(
                                    text = "${index + 1}",
                                    style = MaterialTheme.typography.labelSmall.copy(
                                        fontWeight = FontWeight.Bold,
                                        fontSize = 11.sp
                                    ),
                                    color = AuraCyan
                                )
                            }
                            Text(
                                text = step,
                                style = MaterialTheme.typography.bodySmall.copy(
                                    lineHeight = 17.sp,
                                    fontSize = 12.5.sp
                                ),
                                color = TextSecondary,
                                modifier = Modifier.weight(1f)
                            )
                        }
                    }
                }
            }

            Spacer(Modifier.height(20.dp))

            // Fórmulas & Regras de Pista Aplicadas
            SectionLabel("Fórmulas Operacionais & Normas do Posto")
            Spacer(Modifier.height(10.dp))

            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(14.dp))
                    .background(ObsidianMid)
                    .border(1.dp, OutlineSoft.copy(alpha = 0.35f), RoundedCornerShape(14.dp))
                    .padding(14.dp)
            ) {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    FormulaItem(
                        label = "Variação Legal do LMC (ANP)",
                        formula = "Δ (%) = ((Estoque Final + Vendas) - (Estoque Inicial + Entradas)) ÷ Estoque Inicial",
                        detail = "Tolerância ANP: ±0.60% considerando variação térmica padrão a 20°C."
                    )
                    FormulaItem(
                        label = "Autonomia de Pista & Run-Out",
                        formula = "T (horas) = Volume Atual (L) ÷ Consumo Médio Horário (L/h)",
                        detail = "Previsão de pane seca considerando horários de pico e fins de semana."
                    )
                    FormulaItem(
                        label = "Lote Mínimo de Reposição",
                        formula = "Q_compra = n × 5.000 Litros",
                        detail = "Múltiplos de compartimentos selados de caminhão-tanque rodoviário."
                    )
                }
            }

            Spacer(Modifier.height(24.dp))

            // Ações de 1 Toque
            SectionLabel("Ações Executivas de Aprofundamento")
            Spacer(Modifier.height(10.dp))

            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                // Aprofundar via Chat
                ContextMenuItem(
                    icon = Icons.Rounded.Forum,
                    title = "Aprofundar via Chat com AURA",
                    subtitle = "Solicita detalhamento adicional em tempo real no Cockpit",
                    accentColor = AuraCyan,
                    onClick = {
                        AuraHaptics.heavy(view, haptic)
                        val clean = messageText.replace("\n", " ").replace("\"", "'").trim().take(110)
                        onDismiss()
                        onAskFollowUp("Aprofunde o raciocínio detalhado, cálculos e fontes desta resposta: '$clean'")
                    }
                )

                // Auditar ANP
                ContextMenuItem(
                    icon = Icons.Rounded.Security,
                    title = "Auditar Regra ANP & Fiscal",
                    subtitle = "Executa validação formal de conformidade do LMC e Portarias",
                    accentColor = AuraEmerald,
                    onClick = {
                        AuraHaptics.heavy(view, haptic)
                        val clean = messageText.replace("\n", " ").replace("\"", "'").trim().take(110)
                        onDismiss()
                        onAskFollowUp("Audite a conformidade deste dado segundo as normas da ANP, LMC (±0.60%) e critérios fiscais: '$clean'")
                    }
                )

                // Copiar Relatório Completo
                ContextMenuItem(
                    icon = Icons.Rounded.ContentCopy,
                    title = "Copiar Relatório Técnico Completo",
                    subtitle = "Copia análise com dados e fórmulas para a área de transferência",
                    accentColor = AuraPurple,
                    onClick = {
                        AuraHaptics.heavy(view, haptic)
                        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                        val report = buildString {
                            appendLine("=== RELATÓRIO TÉCNICO AURA POSTO ASSISTANCE ===")
                            appendLine("Categoria: ${categoryBadge.first}")
                            appendLine()
                            appendLine("--- CONTEXTO ANALISADO ---")
                            appendLine(messageText)
                            appendLine()
                            appendLine("--- TRILHA DE RACIOCÍNIO ---")
                            stepsToRender.forEachIndexed { i, s -> appendLine("${i + 1}. $s") }
                            appendLine()
                            appendLine("--- FÓRMULAS & PARÂMETROS ---")
                            appendLine("• LMC ANP: Tolerância legal ±0.60% (Portaria ANP nº 41/2013)")
                            appendLine("• Padrão de Compra: Compartimentos de 5.000 L")
                            appendLine("• Timestamp: ${java.text.SimpleDateFormat("dd/MM/yyyy HH:mm", java.util.Locale.getDefault()).format(java.util.Date())}")
                        }
                        clipboard.setPrimaryClip(ClipData.newPlainText("Relatório AURA", report))
                        Toast.makeText(context, "Relatório técnico copiado!", Toast.LENGTH_SHORT).show()
                        onDismiss()
                    }
                )
            }
        }
    }
}

@Composable
private fun FormulaItem(label: String, formula: String, detail: String) {
    Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
            color = TextPrimary
        )
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(8.dp))
                .background(ObsidianLow)
                .padding(horizontal = 8.dp, vertical = 6.dp)
        ) {
            Text(
                text = formula,
                style = MaterialTheme.typography.labelSmall.copy(
                    fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace,
                    fontSize = 11.sp
                ),
                color = AuraCyan
            )
        }
        Text(
            text = detail,
            style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.5.sp),
            color = TextMuted
        )
    }
}
