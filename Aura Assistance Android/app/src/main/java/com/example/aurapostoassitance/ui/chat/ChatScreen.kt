package com.example.aurapostoassitance.ui.chat

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateColorAsState
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
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsFocusedAsState
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.asPaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.ime
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.ArrowUpward
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.example.aurapostoassitance.ui.components.AuraBrandTitle
import com.example.aurapostoassitance.ui.components.AuraCard
import com.example.aurapostoassitance.ui.components.AuraChip
import com.example.aurapostoassitance.ui.components.SectionLabel
import com.example.aurapostoassitance.ui.components.StatusDot
import com.example.aurapostoassitance.ui.components.ThinkingIndicator
import com.example.aurapostoassitance.ui.genui.GenUiAction
import com.example.aurapostoassitance.ui.genui.GenUiCardView
import com.example.aurapostoassitance.ui.genui.GenUiParser
import com.example.aurapostoassitance.ui.theme.AuraCyan
import com.example.aurapostoassitance.ui.theme.AuraEmerald
import com.example.aurapostoassitance.ui.theme.AuroraBrush
import com.example.aurapostoassitance.ui.theme.AuroraBrushSoft
import com.example.aurapostoassitance.ui.theme.GlassBorderSoft
import com.example.aurapostoassitance.ui.theme.GlassHighlight
import com.example.aurapostoassitance.ui.theme.NewsreaderFamily
import com.example.aurapostoassitance.ui.theme.ObsidianBase
import com.example.aurapostoassitance.ui.theme.ObsidianBright
import com.example.aurapostoassitance.ui.theme.ObsidianLow
import com.example.aurapostoassitance.ui.theme.ObsidianMid
import com.example.aurapostoassitance.ui.theme.OutlineSoft
import com.example.aurapostoassitance.ui.theme.StatusDanger
import com.example.aurapostoassitance.ui.theme.TextMuted
import com.example.aurapostoassitance.ui.theme.TextPrimary
import com.example.aurapostoassitance.ui.theme.TextSecondary
import dev.jeziellago.compose.markdowntext.MarkdownText

private val SUGGESTIONS = listOf(
    Triple("Tanques", "Autonomia dos tanques", "Qual a autonomia dos tanques?"),
    Triple("Diretoria", "Diagnóstico executivo", "Monte um diagnóstico modular para a diretoria"),
    Triple("Mercado", "Meu preço vs ANP", "Como está meu preço de gasolina comum comparado com a ANP na cidade?"),
    Triple("Compliance", "Auditar LMC", "Audite a conformidade do LMC dos tanques de combustível")
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(
    onNavigateBack: () -> Unit,
    initialQuery: String? = null,
    viewModel: ChatViewModel = hiltViewModel()
) {
    val messages by viewModel.messages.collectAsState()
    val isTyping by viewModel.isAuraTyping.collectAsState()
    val auraStatusMessage by viewModel.auraStatusMessage.collectAsState()
    val sessionTitle by viewModel.currentSessionTitle.collectAsState()
    val sessions by viewModel.sessions.collectAsState()

    var inputText by remember { mutableStateOf(initialQuery ?: "") }
    var showMenu by remember { mutableStateOf(false) }
    var showSessionsSheet by remember { mutableStateOf(false) }

    val listState = rememberLazyListState()
    val haptic = LocalHapticFeedback.current

    val keyboardBottomPadding = WindowInsets.ime.asPaddingValues().calculateBottomPadding()
    LaunchedEffect(messages.size, messages.lastOrNull()?.text, messages.lastOrNull()?.envelopeJson, keyboardBottomPadding) {
        if (messages.isNotEmpty()) listState.animateScrollToItem(messages.size - 1)
    }

    val send: (String) -> Unit = { text ->
        if (text.isNotBlank() && !isTyping) {
            haptic.performHapticFeedback(HapticFeedbackType.LongPress)
            viewModel.sendMessage(text)
        }
    }

    val onAction: (GenUiAction) -> Unit = { action ->
        send("Confirmo a ação: ${action.label}")
    }

    Scaffold(
        modifier = Modifier
            .fillMaxSize()
            .imePadding(),
        containerColor = ObsidianBase,
        topBar = {
            ChatHeader(
                title = sessionTitle,
                isTyping = isTyping,
                onBack = onNavigateBack,
                onHistory = { showSessionsSheet = true },
                onNewChat = { viewModel.createNewChat("Novo Chat") },
                menuContent = {
                    IconButton(onClick = { showMenu = true }) {
                        Icon(Icons.Default.MoreVert, "Opções", tint = TextSecondary)
                    }
                    DropdownMenu(
                        expanded = showMenu,
                        onDismissRequest = { showMenu = false },
                        containerColor = ObsidianMid
                    ) {
                        DropdownMenuItem(
                            text = { Text("Limpar esta conversa", color = TextPrimary) },
                            onClick = { viewModel.clearCurrentChat(); showMenu = false }
                        )
                        DropdownMenuItem(
                            text = { Text("Nova conversa", color = TextPrimary) },
                            onClick = { viewModel.createNewChat("Novo Chat"); showMenu = false }
                        )
                    }
                }
            )
        },
        bottomBar = {
            Composer(
                text = inputText,
                onTextChange = { inputText = it },
                enabled = !isTyping,
                onSend = {
                    val toSend = inputText
                    inputText = ""
                    send(toSend)
                },
                onSelectSuggestion = { suggestion ->
                    inputText = suggestion
                }
            )
        }
    ) { padding ->
        Box(
            Modifier
                .fillMaxSize()
                .background(ObsidianBase)
                .padding(padding)
        ) {
            if (messages.isEmpty() && !isTyping) {
                EmptyState(onSuggestion = { inputText = it })
            } else {
                LazyColumn(
                    state = listState,
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(horizontal = 16.dp, vertical = 16.dp),
                    verticalArrangement = Arrangement.spacedBy(20.dp)
                ) {
                    items(messages, key = { it.id }) { message ->
                        MessageItem(
                            message = message,
                            onAction = onAction,
                            auraStatusMessage = auraStatusMessage,
                            modifier = Modifier.animateItem()
                        )
                    }
                }
            }
        }
    }

    if (showSessionsSheet) {
        ModalBottomSheet(
            onDismissRequest = { showSessionsSheet = false },
            containerColor = ObsidianLow,
            shape = RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp)
        ) {
            Column(
                Modifier
                    .fillMaxWidth()
                    .navigationBarsPadding()
                    .padding(horizontal = 20.dp)
                    .padding(bottom = 28.dp)
            ) {
                Text(
                    "Histórico de Conversas",
                    style = MaterialTheme.typography.headlineSmall,
                    color = TextPrimary
                )
                Spacer(Modifier.height(4.dp))
                Text(
                    "Retome uma análise ou diagnóstico anterior",
                    style = MaterialTheme.typography.bodyMedium,
                    color = TextSecondary
                )
                Spacer(Modifier.height(18.dp))

                AuraCard(
                    onClick = {
                        viewModel.createNewChat("Novo Chat")
                        showSessionsSheet = false
                    },
                    accent = AuraCyan,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        Icon(Icons.Default.Add, null, tint = AuraCyan)
                        Text(
                            "Nova conversa",
                            style = MaterialTheme.typography.titleSmall,
                            color = TextPrimary,
                            fontWeight = FontWeight.SemiBold
                        )
                    }
                }

                Spacer(Modifier.height(14.dp))

                LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(sessions, key = { it.sessionId }) { session ->
                        Row(
                            Modifier
                                .fillMaxWidth()
                                .clip(RoundedCornerShape(16.dp))
                                .background(ObsidianMid)
                                .border(1.dp, GlassBorderSoft, RoundedCornerShape(16.dp))
                                .clickable {
                                    viewModel.loadSession(session.sessionId, session.title)
                                    showSessionsSheet = false
                                }
                                .padding(start = 16.dp, top = 6.dp, bottom = 6.dp, end = 6.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = session.title,
                                style = MaterialTheme.typography.bodyLarge,
                                color = TextPrimary,
                                modifier = Modifier.weight(1f),
                                maxLines = 1
                            )
                            IconButton(onClick = { viewModel.deleteSession(session.sessionId) }) {
                                Icon(Icons.Default.Delete, "Excluir conversa", tint = TextMuted)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ChatHeader(
    title: String,
    isTyping: Boolean,
    onBack: () -> Unit,
    onHistory: () -> Unit,
    onNewChat: () -> Unit,
    menuContent: @Composable () -> Unit
) {
    Column(Modifier.background(ObsidianBase)) {
        Row(
            Modifier
                .fillMaxWidth()
                .statusBarsPadding()
                .padding(horizontal = 6.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(onClick = onBack) {
                Icon(Icons.AutoMirrored.Filled.ArrowBack, "Voltar", tint = TextSecondary)
            }
            Column(
                Modifier
                    .weight(1f)
                    .clickable(onClick = onHistory)
            ) {
                if (title.equals("AURA", ignoreCase = true) || title.contains("Cockpit", ignoreCase = true)) {
                    AuraBrandTitle(
                        text = "AURA",
                        style = MaterialTheme.typography.titleLarge
                    )
                } else {
                    Text(
                        text = title,
                        style = MaterialTheme.typography.titleLarge,
                        color = TextPrimary,
                        maxLines = 1
                    )
                }
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    StatusDot(color = AuraEmerald, size = 6.dp, pulsing = isTyping)
                    Text(
                        text = if (isTyping) "AURA sintetizando..." else "Online na rede do posto",
                        style = MaterialTheme.typography.labelSmall,
                        color = TextMuted
                    )
                }
            }
            IconButton(onClick = onHistory) {
                Icon(Icons.Default.History, "Histórico", tint = TextSecondary)
            }
            IconButton(onClick = onNewChat) {
                Icon(Icons.Default.Add, "Novo Chat", tint = AuraCyan)
            }
            menuContent()
        }
        Box(
            Modifier
                .fillMaxWidth()
                .height(1.dp)
                .background(OutlineSoft)
        )
    }
}

@Composable
private fun AuraAvatar(size: Dp = 32.dp) {
    Box(
        Modifier
            .size(size)
            .clip(CircleShape)
            .background(AuroraBrush)
            .border(1.dp, Color(0x44FFFFFF), CircleShape),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = "A",
            style = MaterialTheme.typography.titleMedium.copy(
                fontFamily = NewsreaderFamily,
                fontSize = (size.value * 0.55f).sp
            ),
            color = ObsidianBase,
            fontWeight = FontWeight.Bold
        )
    }
}

@Composable
private fun EmptyState(onSuggestion: (String) -> Unit) {
    Column(
        Modifier
            .fillMaxSize()
            .padding(horizontal = 24.dp),
        verticalArrangement = Arrangement.Center
    ) {
        AuraAvatar(size = 56.dp)
        Spacer(Modifier.height(22.dp))
        Text(
            text = "Como posso ajudar\nno posto hoje?",
            style = MaterialTheme.typography.displayMedium,
            color = TextPrimary
        )
        Spacer(Modifier.height(8.dp))
        Text(
            text = "Peça diagnósticos, compare preços da ANP ou audite a conformidade da pista.",
            style = MaterialTheme.typography.bodyLarge,
            color = TextSecondary
        )
        Spacer(Modifier.height(30.dp))
        SectionLabel("Sugestões Rápidas")
        Spacer(Modifier.height(12.dp))
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            SUGGESTIONS.forEach { (tag, label, prompt) ->
                AuraCard(
                    onClick = { onSuggestion(prompt) },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                            Text(
                                text = tag.uppercase(),
                                style = MaterialTheme.typography.labelSmall,
                                color = AuraCyan,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = label,
                                style = MaterialTheme.typography.titleMedium,
                                color = TextPrimary
                            )
                        }
                        Icon(
                            imageVector = Icons.Default.ArrowUpward,
                            contentDescription = null,
                            tint = TextMuted,
                            modifier = Modifier.size(18.dp)
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun MessageItem(
    message: ChatMessage,
    onAction: (GenUiAction) -> Unit,
    auraStatusMessage: String? = null,
    modifier: Modifier = Modifier
) {
    if (message.isFromUser) {
        UserBubble(message.text, modifier)
    } else {
        AuraMessage(
            message = message,
            onAction = onAction,
            auraStatusMessage = auraStatusMessage,
            modifier = modifier
        )
    }
}

@Composable
private fun UserBubble(text: String, modifier: Modifier = Modifier) {
    val shape = RoundedCornerShape(22.dp, 22.dp, 6.dp, 22.dp)
    Box(
        modifier = modifier.fillMaxWidth(),
        contentAlignment = Alignment.CenterEnd
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.bodyLarge,
            color = TextPrimary,
            modifier = Modifier
                .widthIn(max = 320.dp)
                .clip(shape)
                .background(AuroraBrushSoft)
                .border(1.dp, AuraCyan.copy(alpha = 0.35f), shape)
                .padding(horizontal = 16.dp, vertical = 12.dp)
        )
    }
}

@Composable
private fun AuraMessage(
    message: ChatMessage,
    onAction: (GenUiAction) -> Unit,
    auraStatusMessage: String? = null,
    modifier: Modifier = Modifier
) {
    val card = remember(message.envelopeJson) { message.envelopeJson?.let(GenUiParser::parse) }
    val isError = message.text.startsWith("Sem conexão") ||
        message.text.startsWith("O sinal de rede") ||
        message.text.startsWith("Erro de conexão")

    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        AuraAvatar()
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            if (message.isStreaming && message.text.isBlank()) {
                val thinkingLabel = auraStatusMessage ?: "AURA sintetizando resposta..."
                ThinkingIndicator(label = thinkingLabel)
            } else if (message.text.isNotBlank()) {
                if (isError) {
                    Text(message.text, style = MaterialTheme.typography.bodyMedium, color = StatusDanger)
                } else {
                    val formattedText = AuraMarkupFormatter.format(
                        if (message.isStreaming) message.text + " \u258A" else message.text
                    )
                    MarkdownText(
                        markdown = formattedText,
                        style = MaterialTheme.typography.bodyLarge.copy(
                            color = TextPrimary,
                            lineHeight = MaterialTheme.typography.bodyLarge.lineHeight * 1.25f
                        ),
                        linkColor = AuraCyan
                    )
                }
            }
            card?.let { GenUiCardView(card = it, onAction = onAction) }
        }
    }
}

/** Composer flutuante deluxe: chips deslizantes, borda com glow dinamico ao focar e botao com microescala. */
@Composable
private fun Composer(
    text: String,
    onTextChange: (String) -> Unit,
    enabled: Boolean,
    onSend: () -> Unit,
    onSelectSuggestion: (String) -> Unit
) {
    val interaction = remember { MutableInteractionSource() }
    val focused by interaction.collectIsFocusedAsState()

    val sendInteraction = remember { MutableInteractionSource() }
    val sendPressed by sendInteraction.collectIsPressedAsState()

    val canSend = text.isNotBlank() && enabled
    val sendScale by animateFloatAsState(
        targetValue = if (sendPressed) 0.90f else if (canSend) 1f else 0.92f,
        animationSpec = spring(dampingRatio = 0.60f, stiffness = 500f),
        label = "sendScale"
    )

    val borderColor by animateColorAsState(
        targetValue = if (focused) AuraCyan else OutlineSoft,
        animationSpec = tween(280),
        label = "composerBorder"
    )

    val fieldShape = RoundedCornerShape(26.dp)
    val haptic = LocalHapticFeedback.current

    Column(Modifier.background(ObsidianBase)) {
        // Chips deslizantes de sugestao rapida logo acima do composer: recolhem suavemente em foco
        AnimatedVisibility(
            visible = !focused,
            enter = expandVertically() + fadeIn(),
            exit = shrinkVertically() + fadeOut()
        ) {
            LazyRow(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 12.dp, vertical = 6.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                items(SUGGESTIONS) { (tag, label, prompt) ->
                    AuraChip(
                        label = label,
                        tag = tag,
                        icon = Icons.Rounded.AutoAwesome,
                        onClick = { onSelectSuggestion(prompt) }
                    )
                }
            }
        }

        Box(
            Modifier
                .fillMaxWidth()
                .height(1.dp)
                .background(OutlineSoft)
        )

        Row(
            Modifier
                .fillMaxWidth()
                .navigationBarsPadding()
                .padding(horizontal = 14.dp, vertical = 10.dp),
            verticalAlignment = Alignment.Bottom,
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Box(
                Modifier
                    .weight(1f)
                    .clip(fieldShape)
                    .background(ObsidianMid)
                    .drawBehind {
                        // Sutil destaque de vidro no topo do campo
                        drawLine(
                            brush = Brush.horizontalGradient(
                                listOf(Color.Transparent, GlassHighlight, Color.Transparent)
                            ),
                            start = Offset(0f, 1f),
                            end = Offset(size.width, 1f),
                            strokeWidth = 1.dp.toPx()
                        )
                    }
                    .border(1.dp, borderColor, fieldShape)
            ) {
                BasicTextField(
                    value = text,
                    onValueChange = onTextChange,
                    interactionSource = interaction,
                    textStyle = MaterialTheme.typography.bodyLarge.copy(color = TextPrimary),
                    cursorBrush = SolidColor(AuraCyan),
                    maxLines = 5,
                    decorationBox = { inner ->
                        Box(Modifier.padding(horizontal = 20.dp, vertical = 14.dp)) {
                            if (text.isEmpty()) {
                                Text(
                                    "Pergunte à AURA sobre o posto...",
                                    style = MaterialTheme.typography.bodyLarge,
                                    color = TextMuted
                                )
                            }
                            inner()
                        }
                    }
                )
            }

            Box(
                Modifier
                    .size(52.dp)
                    .graphicsLayer {
                        scaleX = sendScale
                        scaleY = sendScale
                    }
                    .clip(CircleShape)
                    .background(
                        if (canSend) AuroraBrush else Brush.linearGradient(listOf(ObsidianBright, ObsidianBright))
                    )
                    .clickable(
                        enabled = canSend,
                        interactionSource = sendInteraction,
                        indication = null
                    ) {
                        haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                        onSend()
                    },
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Default.ArrowUpward,
                    contentDescription = "Enviar",
                    tint = if (canSend) ObsidianBase else TextMuted,
                    modifier = Modifier.size(24.dp)
                )
            }
        }
    }
}
