package com.example.aurapostoassitance.ui.chat

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.compose.ui.platform.LocalContext
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
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.combinedClickable
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
import androidx.compose.material.icons.rounded.Mic
import androidx.compose.material.icons.rounded.Psychology
import androidx.compose.material.icons.rounded.Security
import androidx.compose.material.icons.rounded.Stop
import androidx.compose.material.icons.rounded.Tune
import androidx.compose.material.icons.rounded.VolumeUp
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
import com.example.aurapostoassitance.ui.components.AuraAmbientBackground
import com.example.aurapostoassitance.ui.components.AuraBrandTitle
import com.example.aurapostoassitance.ui.components.AuraCard
import com.example.aurapostoassitance.ui.components.AuraChip
import com.example.aurapostoassitance.ui.components.AuraDeepDiveModal
import com.example.aurapostoassitance.ui.components.AuraDynamicIsland
import com.example.aurapostoassitance.ui.components.AuraLivingOrb
import com.example.aurapostoassitance.ui.components.AuraMessageActionType
import com.example.aurapostoassitance.ui.components.AuraMessageContextMenuSheet
import com.example.aurapostoassitance.ui.components.AuraQuickCommandHubSheet
import com.example.aurapostoassitance.ui.components.AuraReasoningAccordion
import com.example.aurapostoassitance.ui.components.AuraVoiceOrbSheet
import com.example.aurapostoassitance.ui.components.LiquidGlassPill
import com.example.aurapostoassitance.ui.components.SectionLabel
import com.example.aurapostoassitance.ui.components.SpatialGlassCard
import com.example.aurapostoassitance.ui.components.StatusDot
import com.example.aurapostoassitance.ui.components.ThinkingIndicator
import com.example.aurapostoassitance.ui.genui.GenUiAction
import com.example.aurapostoassitance.ui.genui.GenUiCardView
import com.example.aurapostoassitance.ui.genui.GenUiParser
import com.example.aurapostoassitance.ui.theme.AuraCyan
import com.example.aurapostoassitance.ui.theme.AuraEmerald
import com.example.aurapostoassitance.ui.theme.AuraPurple
import com.example.aurapostoassitance.ui.theme.AuroraBrush
import com.example.aurapostoassitance.ui.theme.AuroraBrushSoft
import com.example.aurapostoassitance.ui.theme.GlassBorderSoft
import com.example.aurapostoassitance.ui.theme.GlassHighlight
import com.example.aurapostoassitance.ui.theme.LiquidGlassElevatedBrush
import com.example.aurapostoassitance.ui.theme.LiquidGlassSurfaceBrush
import com.example.aurapostoassitance.ui.theme.LiquidIridescentBorderBrush
import com.example.aurapostoassitance.ui.theme.LiquidIridescentSubtleBrush
import com.example.aurapostoassitance.ui.theme.LiquidSpecularHighlight
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

    // Fluxos de Voz e Fala Hands-Free
    val isListening by viewModel.isListening.collectAsState()
    val spokenText by viewModel.spokenText.collectAsState()
    val voiceRms by viewModel.voiceRms.collectAsState()
    val isSpeaking by viewModel.isSpeaking.collectAsState()
    val speakingMessageId by viewModel.speakingMessageId.collectAsState()

    val context = LocalContext.current
    val recordAudioLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (isGranted) {
            viewModel.startVoiceListening()
        }
    }

    val requestVoiceListening = {
        val hasPermission = ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.RECORD_AUDIO
        ) == PackageManager.PERMISSION_GRANTED

        if (hasPermission) {
            viewModel.startVoiceListening()
        } else {
            recordAudioLauncher.launch(Manifest.permission.RECORD_AUDIO)
        }
    }

    var inputText by remember { mutableStateOf(initialQuery ?: "") }
    var showMenu by remember { mutableStateOf(false) }
    var showSessionsSheet by remember { mutableStateOf(false) }
    var showCommandHubSheet by remember { mutableStateOf(false) }
    var selectedMenuMessage by remember { mutableStateOf<ChatMessage?>(null) }
    var activeModeTitle by remember { mutableStateOf<String?>(null) }

    val listState = rememberLazyListState()
    val haptic = LocalHapticFeedback.current

    val keyboardBottomPadding = WindowInsets.ime.asPaddingValues().calculateBottomPadding()
    LaunchedEffect(messages.size, messages.lastOrNull()?.text, messages.lastOrNull()?.envelopeJson, keyboardBottomPadding) {
        if (messages.isNotEmpty()) listState.animateScrollToItem(messages.size - 1)
    }

    val send: (String) -> Unit = { text ->
        if (text.isNotBlank()) {
            haptic.performHapticFeedback(HapticFeedbackType.LongPress)
            viewModel.sendMessage(text)
        }
    }

    val onAction: (GenUiAction) -> Unit = { action ->
        send("Confirmo a ação: ${action.label}")
    }

    AuraAmbientBackground {
        Scaffold(
            modifier = Modifier
                .fillMaxSize()
                .imePadding(),
            containerColor = Color.Transparent,
            topBar = {
                ChatHeader(
                    title = sessionTitle,
                    isTyping = isTyping,
                    activeMode = activeModeTitle,
                    onBack = onNavigateBack,
                    onHistory = { showSessionsSheet = true },
                    onNewChat = { viewModel.createNewChat("Novo Chat") },
                    onOpenCommandHub = { showCommandHubSheet = true },
                    onQueryAction = { query -> send(query) },
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
                                text = { Text("Aura Command Hub", color = TextPrimary) },
                                onClick = { showCommandHubSheet = true; showMenu = false },
                                leadingIcon = { Icon(Icons.Rounded.Tune, null, tint = AuraCyan) }
                            )
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
                Column {
                    AnimatedVisibility(
                        visible = isListening || spokenText.isNotBlank(),
                        enter = expandVertically() + fadeIn(),
                        exit = shrinkVertically() + fadeOut()
                    ) {
                        AuraVoiceOrbSheet(
                            isListening = isListening,
                            spokenText = spokenText,
                            voiceRms = voiceRms,
                            onCancel = { viewModel.cancelVoiceListening() },
                            onSend = { text ->
                                viewModel.sendVoiceQuery(text)
                            }
                        )
                    }

                    Composer(
                        text = inputText,
                        onTextChange = { inputText = it },
                        enabled = !isTyping,
                        onSend = {
                            val toSend = inputText
                            inputText = ""
                            send(toSend)
                        },
                        onStartVoice = requestVoiceListening,
                        voiceRms = if (isListening) voiceRms else 0.05f,
                        onOpenCommandHub = { showCommandHubSheet = true },
                        onSelectSuggestion = { suggestion ->
                            inputText = suggestion
                        }
                    )
                }
            }
        ) { padding ->
            Box(
                Modifier
                    .fillMaxSize()
                    .padding(padding)
            ) {
                if (messages.isEmpty() && !isTyping) {
                    EmptyState(
                        onSuggestion = { inputText = it },
                        onOpenCommandHub = { showCommandHubSheet = true }
                    )
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
                                onDrillDown = { send(it) },
                                speakingMessageId = speakingMessageId,
                                onToggleSpeech = { id, text -> viewModel.toggleSpeech(id, text) },
                                auraStatusMessage = auraStatusMessage,
                                onMessageLongClick = { selectedMenuMessage = it },
                                onDeepDive = {
                                    val clean = message.text.replace("\n", " ").replace("\"", "'").trim().take(110)
                                    send("Aprofunde o raciocínio detalhado, cálculos e fontes desta resposta: '$clean'")
                                },
                                onAuditAnp = {
                                    val clean = message.text.replace("\n", " ").replace("\"", "'").trim().take(110)
                                    send("Audite a conformidade deste dado segundo as normas da ANP, LMC (±0.60%) e critérios fiscais: '$clean'")
                                },
                                modifier = Modifier.animateItem()
                            )
                        }
                    }
                }
            }
        }
    }

    // Modal de Contexto da Mensagem (Spatial Liquid Glass)
    selectedMenuMessage?.let { msg ->
        AuraMessageContextMenuSheet(
            messageText = msg.text,
            isAuraMessage = !msg.isFromUser,
            onDismiss = { selectedMenuMessage = null },
            onActionSelected = { action ->
                when (action) {
                    AuraMessageActionType.COPY -> { /* Tratado internamente com clipboard */ }
                    AuraMessageActionType.DEEP_DIVE -> {
                        val clean = msg.text.replace("\n", " ").replace("\"", "'").trim().take(110)
                        send("Aprofunde o raciocínio detalhado, cálculos e fontes desta resposta: '$clean'")
                    }
                    AuraMessageActionType.AUDIT_ANP -> {
                        val clean = msg.text.replace("\n", " ").replace("\"", "'").trim().take(110)
                        send("Audite a conformidade deste dado segundo as normas da ANP, LMC (±0.60%) e critérios fiscais: '$clean'")
                    }
                    AuraMessageActionType.REGENERATE -> {
                        send("Por favor, reformule e aprofunde a resposta anterior com foco executivo e dados práticos do posto.")
                    }
                    AuraMessageActionType.SHARE -> { /* Tratado internamente com Share Intent */ }
                }
            }
        )
    }

    // Modal Aura Command Hub (Gatilhos do Posto & Modos Cognitivos)
    if (showCommandHubSheet) {
        AuraQuickCommandHubSheet(
            onDismiss = { showCommandHubSheet = false },
            onSelectMode = { modeTitle, promptPrefix ->
                activeModeTitle = modeTitle
                inputText = promptPrefix + inputText
            },
            onInjectFilter = { filterQuery ->
                send(filterQuery)
            }
        )
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
    activeMode: String? = null,
    onBack: () -> Unit,
    onHistory: () -> Unit,
    onNewChat: () -> Unit,
    onOpenCommandHub: () -> Unit,
    onQueryAction: (String) -> Unit = {},
    menuContent: @Composable () -> Unit
) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .background(LiquidGlassElevatedBrush)
            .drawBehind {
                // Linha de refração líquida / highlight especular no topo
                drawLine(
                    brush = Brush.horizontalGradient(
                        listOf(Color.Transparent, LiquidSpecularHighlight, Color.Transparent)
                    ),
                    start = Offset(0f, 1f),
                    end = Offset(size.width, 1f),
                    strokeWidth = 1.2.dp.toPx()
                )
            }
    ) {
        Column {
            Row(
                Modifier
                    .fillMaxWidth()
                    .statusBarsPadding()
                    .padding(horizontal = 8.dp, vertical = 8.dp),
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
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        if (title.equals("AURA", ignoreCase = true) || title.contains("Cockpit", ignoreCase = true)) {
                            AuraBrandTitle(
                                text = "AURA",
                                style = MaterialTheme.typography.titleLarge
                            )
                        } else {
                            Text(
                                text = title,
                                style = MaterialTheme.typography.titleMedium,
                                color = TextPrimary,
                                fontWeight = FontWeight.Bold,
                                maxLines = 1
                            )
                        }

                        if (activeMode != null) {
                            LiquidGlassPill(
                                text = activeMode,
                                accentColor = when (activeMode.lowercase()) {
                                    "pista" -> AuraCyan
                                    "gerência", "gerencia" -> AuraEmerald
                                    else -> AuraPurple
                                },
                                onClick = onOpenCommandHub
                            )
                        }
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

                IconButton(onClick = onOpenCommandHub) {
                    Icon(Icons.Rounded.Tune, "Aura Hub", tint = AuraCyan)
                }
                IconButton(onClick = onHistory) {
                    Icon(Icons.Default.History, "Histórico", tint = TextSecondary)
                }
                IconButton(onClick = onNewChat) {
                    Icon(Icons.Default.Add, "Novo Chat", tint = AuraCyan)
                }
                menuContent()
            }

            // Aura Dynamic Island: Cápsula de telemetria operacional ao vivo
            AuraDynamicIsland(
                onQueryAction = onQueryAction
            )

            Box(
                Modifier
                    .fillMaxWidth()
                    .height(1.dp)
                    .background(LiquidIridescentSubtleBrush)
            )
        }
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
private fun EmptyState(
    onSuggestion: (String) -> Unit,
    onOpenCommandHub: () -> Unit
) {
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
        Spacer(Modifier.height(24.dp))

        // Botão de acesso ao Aura Hub
        SpatialGlassCard(
            onClick = onOpenCommandHub,
            modifier = Modifier.fillMaxWidth(),
            accent = AuraCyan,
            iridescentBorder = true
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Box(
                    modifier = Modifier
                        .size(36.dp)
                        .clip(CircleShape)
                        .background(AuraCyan.copy(alpha = 0.20f)),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(Icons.Rounded.Tune, null, tint = AuraCyan, modifier = Modifier.size(18.dp))
                }
                Column(Modifier.weight(1f)) {
                    Text(
                        text = "Aura Command Hub",
                        style = MaterialTheme.typography.titleSmall,
                        color = TextPrimary,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = "Gatilhos operacionais para Pista, Gerência e Compliance",
                        style = MaterialTheme.typography.labelSmall,
                        color = TextMuted
                    )
                }
                Icon(Icons.Rounded.AutoAwesome, null, tint = AuraCyan, modifier = Modifier.size(18.dp))
            }
        }

        Spacer(Modifier.height(24.dp))
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
    onDrillDown: (String) -> Unit = {},
    speakingMessageId: String? = null,
    onToggleSpeech: (String, String) -> Unit = { _, _ -> },
    auraStatusMessage: String? = null,
    onMessageLongClick: (ChatMessage) -> Unit,
    onDeepDive: () -> Unit,
    onAuditAnp: () -> Unit,
    modifier: Modifier = Modifier
) {
    if (message.isFromUser) {
        UserBubble(
            text = message.text,
            onLongClick = { onMessageLongClick(message) },
            modifier = modifier
        )
    } else {
        AuraMessage(
            message = message,
            onAction = onAction,
            onDrillDown = onDrillDown,
            speakingMessageId = speakingMessageId,
            onToggleSpeech = onToggleSpeech,
            auraStatusMessage = auraStatusMessage,
            onLongClick = { onMessageLongClick(message) },
            onDeepDive = onDeepDive,
            onAuditAnp = onAuditAnp,
            modifier = modifier
        )
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun UserBubble(
    text: String,
    onLongClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val haptic = LocalHapticFeedback.current
    val shape = RoundedCornerShape(22.dp, 22.dp, 6.dp, 22.dp)

    Box(
        modifier = modifier.fillMaxWidth(),
        contentAlignment = Alignment.CenterEnd
    ) {
        Box(
            modifier = Modifier
                .widthIn(max = 320.dp)
                .clip(shape)
                .background(AuroraBrushSoft)
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
                .border(1.dp, LiquidIridescentSubtleBrush, shape)
                .combinedClickable(
                    onClick = {},
                    onLongClick = {
                        haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                        onLongClick()
                    }
                )
                .padding(horizontal = 16.dp, vertical = 12.dp)
        ) {
            Text(
                text = text,
                style = MaterialTheme.typography.bodyLarge,
                color = TextPrimary
            )
        }
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun AuraMessage(
    message: ChatMessage,
    onAction: (GenUiAction) -> Unit,
    onDrillDown: (String) -> Unit = {},
    speakingMessageId: String? = null,
    onToggleSpeech: (String, String) -> Unit = { _, _ -> },
    auraStatusMessage: String? = null,
    onLongClick: () -> Unit,
    onDeepDive: () -> Unit,
    onAuditAnp: () -> Unit,
    modifier: Modifier = Modifier
) {
    val card = remember(message.envelopeJson) { message.envelopeJson?.let(GenUiParser::parse) }
    val isError = message.text.startsWith("Sem conexão") ||
        message.text.startsWith("O sinal de rede") ||
        message.text.startsWith("Erro de conexão")
    val haptic = LocalHapticFeedback.current

    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        AuraAvatar()
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            // Acordeão de Raciocínio Transparente (visível tanto durante streaming quanto após concluído)
            if (message.reasoningSteps.isNotEmpty()) {
                AuraReasoningAccordion(
                    reasoningSteps = message.reasoningSteps,
                    isStreaming = message.isStreaming
                )
            }

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

                    // Card de vidro espacial envolvendo a resposta da IA
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(4.dp, 20.dp, 20.dp, 20.dp))
                            .background(LiquidGlassSurfaceBrush)
                            .drawBehind {
                                drawLine(
                                    brush = Brush.horizontalGradient(
                                        listOf(Color.Transparent, LiquidSpecularHighlight, Color.Transparent)
                                    ),
                                    start = Offset(0f, 1f),
                                    end = Offset(size.width, 1f),
                                    strokeWidth = 1.dp.toPx()
                                )
                            }
                            .border(1.dp, LiquidIridescentSubtleBrush, RoundedCornerShape(4.dp, 20.dp, 20.dp, 20.dp))
                            .combinedClickable(
                                onClick = {},
                                onLongClick = {
                                    haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                                    onLongClick()
                                }
                            )
                            .padding(14.dp)
                    ) {
                        MarkdownText(
                            markdown = formattedText,
                            style = MaterialTheme.typography.bodyLarge.copy(
                                color = TextPrimary,
                                lineHeight = MaterialTheme.typography.bodyLarge.lineHeight * 1.25f
                            ),
                            linkColor = AuraCyan
                        )
                    }

                    // Barra de Micro-Ações de Contexto da Aura (visível quando resposta concluída)
                    if (!message.isStreaming) {
                        Row(
                            horizontalArrangement = Arrangement.spacedBy(6.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier.padding(top = 2.dp)
                        ) {
                            val isSpeakingThis = speakingMessageId == message.id
                            LiquidGlassPill(
                                text = if (isSpeakingThis) "Parar" else "Ouvir",
                                icon = if (isSpeakingThis) Icons.Rounded.Stop else Icons.Rounded.VolumeUp,
                                accentColor = if (isSpeakingThis) StatusDanger else AuraCyan,
                                onClick = { onToggleSpeech(message.id, message.text) }
                            )

                            LiquidGlassPill(
                                text = "Raciocínio",
                                icon = Icons.Rounded.Psychology,
                                accentColor = AuraEmerald,
                                onClick = onDeepDive
                            )

                            LiquidGlassPill(
                                text = "ANP",
                                icon = Icons.Rounded.Security,
                                accentColor = AuraPurple,
                                onClick = onAuditAnp
                            )

                            LiquidGlassPill(
                                text = "Mais...",
                                icon = Icons.Rounded.AutoAwesome,
                                accentColor = AuraCyan,
                                onClick = onLongClick
                            )
                        }
                    }
                }
            }
            card?.let { GenUiCardView(card = it, onAction = onAction, onDrillDown = onDrillDown) }
        }
    }
}

/** Composer flutuante com Spatial UI, gatilho do Aura Command Hub e iluminação de vidro líquido */
@Composable
private fun Composer(
    text: String,
    onTextChange: (String) -> Unit,
    enabled: Boolean,
    onSend: () -> Unit,
    onStartVoice: () -> Unit = {},
    voiceRms: Float = 0.05f,
    onOpenCommandHub: () -> Unit,
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

    Column(
        Modifier
            .background(LiquidGlassElevatedBrush)
            .drawBehind {
                drawLine(
                    brush = Brush.horizontalGradient(
                        listOf(Color.Transparent, LiquidSpecularHighlight, Color.Transparent)
                    ),
                    start = Offset(0f, 1f),
                    end = Offset(size.width, 1f),
                    strokeWidth = 1.dp.toPx()
                )
            }
    ) {
        // Chips deslizantes de sugestão rápida
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
                .padding(horizontal = 12.dp, vertical = 10.dp),
            verticalAlignment = Alignment.Bottom,
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            // Botão de Gatilho do Aura Command Hub
            Box(
                modifier = Modifier
                    .size(48.dp)
                    .clip(CircleShape)
                    .background(ObsidianMid)
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
                    .border(1.dp, LiquidIridescentSubtleBrush, CircleShape)
                    .clickable {
                        haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                        onOpenCommandHub()
                    },
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Rounded.Tune,
                    contentDescription = "Aura Command Hub",
                    tint = AuraCyan,
                    modifier = Modifier.size(22.dp)
                )
            }

            // Campo de Texto de Vidro Líquido
            Box(
                Modifier
                    .weight(1f)
                    .clip(fieldShape)
                    .background(ObsidianMid)
                    .drawBehind {
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
                        Box(Modifier.padding(horizontal = 18.dp, vertical = 14.dp)) {
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

            val isMic = text.isBlank()
            val buttonBackgroundModifier = if (canSend) {
                Modifier.background(AuroraBrush)
            } else {
                Modifier.background(ObsidianMid)
            }
            val buttonBorderModifier = if (isMic) {
                Modifier.border(1.dp, LiquidIridescentBorderBrush, CircleShape)
            } else {
                Modifier.border(1.dp, OutlineSoft, CircleShape)
            }

            // Botão Dinâmico: Orbe Vivo da AURA (em repouso/voz) ou Seta Aurora (ao digitar)
            Box(
                Modifier
                    .size(48.dp)
                    .graphicsLayer {
                        scaleX = sendScale
                        scaleY = sendScale
                    }
                    .clip(CircleShape)
                    .then(buttonBackgroundModifier)
                    .drawBehind {
                        if (isMic) {
                            drawCircle(
                                brush = Brush.radialGradient(
                                    listOf(AuraCyan.copy(alpha = 0.25f), Color.Transparent)
                                )
                            )
                        }
                    }
                    .then(buttonBorderModifier)
                    .clickable(
                        enabled = enabled,
                        interactionSource = sendInteraction,
                        indication = null
                    ) {
                        haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                        if (isMic) {
                            onStartVoice()
                        } else {
                            onSend()
                        }
                    },
                contentAlignment = Alignment.Center
            ) {
                if (isMic) {
                    AuraLivingOrb(
                        sizeDp = 34.dp,
                        voiceRms = voiceRms,
                        pulsing = true
                    )
                } else {
                    Icon(
                        imageVector = Icons.Default.ArrowUpward,
                        contentDescription = "Enviar",
                        tint = ObsidianBase,
                        modifier = Modifier.size(24.dp)
                    )
                }
            }
        }
    }
}
