package com.example.aurapostoassitance.ui.chat

import android.Manifest
import android.content.Context
import android.content.ContextWrapper
import android.content.pm.PackageManager
import android.graphics.BitmapFactory
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
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
import androidx.compose.foundation.layout.heightIn
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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.ArrowUpward
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material.icons.rounded.Chat
import androidx.compose.material.icons.rounded.DocumentScanner
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
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontFamily
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import java.io.File
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.hilt.navigation.compose.hiltViewModel
import com.example.aurapostoassitance.data.local.HandoffContact
import com.example.aurapostoassitance.ui.components.AuraAmbientBackground
import com.example.aurapostoassitance.ui.components.AuraBrandTitle
import com.example.aurapostoassitance.ui.components.AuraCard
import com.example.aurapostoassitance.ui.components.AuraChip
import com.example.aurapostoassitance.ui.components.AuraDeepDiveModal
import com.example.aurapostoassitance.ui.components.AuraDynamicIsland
import com.example.aurapostoassitance.ui.vision.AuraVisionBottomSheet
import com.example.aurapostoassitance.ui.components.AuraGhostButton
import com.example.aurapostoassitance.ui.components.AuraGradientButton
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
import com.example.aurapostoassitance.ui.components.findFragmentActivity
import com.example.aurapostoassitance.ui.genui.AuraWhatsAppReportFormatter
import com.example.aurapostoassitance.ui.genui.GenUiAction
import com.example.aurapostoassitance.ui.genui.GenUiCardView
import com.example.aurapostoassitance.ui.genui.GenUiParser
import com.example.aurapostoassitance.ui.genui.isHandoffAction
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
    val currentSessionId by viewModel.currentSessionId.collectAsState()
    val sessionTitle by viewModel.currentSessionTitle.collectAsState()
    val sessions by viewModel.sessions.collectAsState()
    val handoffThreads by viewModel.handoffThreads.collectAsState()
    val totalUnreadHandoffs by viewModel.totalUnreadHandoffs.collectAsState()
    val incomingHandoffAlert by viewModel.incomingHandoffAlert.collectAsState()
    val isDirectWhatsAppSession = currentSessionId.startsWith("wa_handoff_")
    val activeHandoffThread = remember(currentSessionId, handoffThreads) {
        handoffThreads.firstOrNull {
            it.session_id == currentSessionId || "wa_handoff_${it.thread_phone}" == currentSessionId
        }
    }

    // Fluxos de Voz e Fala Hands-Free
    val isListening by viewModel.isListening.collectAsState()
    val spokenText by viewModel.spokenText.collectAsState()
    val voiceRms by viewModel.voiceRms.collectAsState()
    val isSpeaking by viewModel.isSpeaking.collectAsState()
    val speakingMessageId by viewModel.speakingMessageId.collectAsState()
    val voiceError by viewModel.voiceError.collectAsState()
    val isVoiceConversationActive by viewModel.isVoiceConversationActive.collectAsState()
    val openVisionScannerRequest by viewModel.openVisionScannerRequest.collectAsState()
    val handoffContacts by viewModel.handoffContacts.collectAsState()
    val lastHandoffRole by viewModel.lastHandoffRole.collectAsState()
    val pendingWhatsAppUrl by viewModel.pendingWhatsAppUrl.collectAsState()
    val hasScannedDocument by viewModel.hasScannedDocument.collectAsState()
    val lastScannedDocumentTitle by viewModel.lastScannedDocumentTitle.collectAsState()

    val context = LocalContext.current

    LaunchedEffect(pendingWhatsAppUrl) {
        val url = pendingWhatsAppUrl ?: return@LaunchedEffect
        runCatching {
            val intent = android.content.Intent(android.content.Intent.ACTION_VIEW, android.net.Uri.parse(url))
            context.startActivity(intent)
        }
        viewModel.consumePendingWhatsAppUrl()
    }
    val recordAudioLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (isGranted) {
            viewModel.startVoiceConversation()
        }
    }

    val requestVoiceListening = {
        val hasPermission = ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.RECORD_AUDIO
        ) == PackageManager.PERMISSION_GRANTED

        if (hasPermission) {
            viewModel.startVoiceConversation()
        } else {
            recordAudioLauncher.launch(Manifest.permission.RECORD_AUDIO)
        }
    }

    var inputText by remember { mutableStateOf(initialQuery ?: "") }
    var showMenu by remember { mutableStateOf(false) }
    var showSessionsSheet by remember { mutableStateOf(false) }
    var showCommandHubSheet by remember { mutableStateOf(false) }
    var showVisionScanner by remember { mutableStateOf(false) }
    var selectedMenuMessage by remember { mutableStateOf<ChatMessage?>(null) }
    var pendingHandoffAction by remember { mutableStateOf<GenUiAction?>(null) }
    var activeModeTitle by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(openVisionScannerRequest) {
        if (openVisionScannerRequest) {
            showVisionScanner = true
            viewModel.consumeVisionScannerRequest()
        }
    }

    LaunchedEffect(voiceError) {
        if (voiceError != null) {
            kotlinx.coroutines.delay(4000)
            viewModel.clearVoiceError()
        }
    }

    val listState = rememberLazyListState()
    val haptic = LocalHapticFeedback.current

    val keyboardBottomPadding = WindowInsets.ime.asPaddingValues().calculateBottomPadding()
    LaunchedEffect(messages.size, messages.lastOrNull()?.text, messages.lastOrNull()?.envelopeJson, keyboardBottomPadding) {
        if (messages.isNotEmpty()) listState.animateScrollToItem(messages.size - 1)
    }

    val send: (String) -> Unit = { text ->
        if (text.isNotBlank()) {
            haptic.performHapticFeedback(HapticFeedbackType.LongPress)
            viewModel.sendMessage(
                query = text,
                speakResponse = isVoiceConversationActive,
                voiceMode = isVoiceConversationActive
            )
        }
    }

    val activity = remember(context) { context.findFragmentActivity() }

    val executeSignedOrDirect: (GenUiAction) -> Unit = { action ->
        val act = activity ?: context.findFragmentActivity()
        if (act != null && (action.requiresConfirmation || action.isDestructive || action.isHandoffAction())) {
            viewModel.handleSignedGenUiAction(act, action)
        } else {
            viewModel.handleGenUiAction(action)
        }
    }

    val onAction: (GenUiAction) -> Unit = { action ->
        if (action.isHandoffAction() && action.targetPhone.isNullOrBlank()) {
            pendingHandoffAction = action
        } else {
            executeSignedOrDirect(action)
        }
    }

    AuraAmbientBackground {
        Scaffold(
            modifier = Modifier
                .fillMaxSize()
                .imePadding(),
            containerColor = Color.Transparent,
            topBar = {
                Column {
                    ChatHeader(
                        title = sessionTitle,
                        isTyping = isTyping,
                        activeMode = activeModeTitle,
                        isVoiceConversationActive = isVoiceConversationActive,
                        totalUnreadHandoffs = totalUnreadHandoffs,
                        onToggleVoiceConversation = {
                            if (isVoiceConversationActive) {
                                viewModel.endVoiceConversation()
                            } else {
                                requestVoiceListening()
                            }
                        },
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

                    AnimatedVisibility(
                        visible = incomingHandoffAlert != null,
                        enter = expandVertically() + fadeIn(),
                        exit = shrinkVertically() + fadeOut()
                    ) {
                        incomingHandoffAlert?.let { alert ->
                            HandoffReplyTopBanner(
                                alert = alert,
                                onOpen = { viewModel.openHandoffThread(alert.sessionId, alert.phone) },
                                onDismiss = { viewModel.dismissIncomingHandoffAlert() }
                            )
                        }
                    }

                    AnimatedVisibility(
                        visible = isDirectWhatsAppSession,
                        enter = expandVertically() + fadeIn(),
                        exit = shrinkVertically() + fadeOut()
                    ) {
                        val phone = currentSessionId.removePrefix("wa_handoff_")
                        val name = activeHandoffThread?.contact_name?.takeIf { it.isNotBlank() } ?: sessionTitle
                        ActiveWhatsAppSessionBar(
                            contactName = name,
                            phone = phone,
                            onBackToAura = { viewModel.loadSession("default", "AURA") }
                        )
                    }
                }
            },
            bottomBar = {
                Column {
                    AnimatedVisibility(
                        visible = isVoiceConversationActive || isListening || spokenText.isNotBlank(),
                        enter = expandVertically() + fadeIn(),
                        exit = shrinkVertically() + fadeOut()
                    ) {
                        AuraVoiceOrbSheet(
                            isListening = isListening,
                            spokenText = spokenText,
                            voiceRms = voiceRms,
                            onCancel = { viewModel.endVoiceConversation() },
                            onSend = { text ->
                                viewModel.sendVoiceQuery(text)
                            },
                            isConversationActive = isVoiceConversationActive,
                            isThinking = isTyping,
                            isAuraSpeaking = isSpeaking,
                            voiceError = voiceError,
                            onOrbTap = { viewModel.interruptAndListen() }
                        )
                    }

                    AnimatedVisibility(
                        visible = !isVoiceConversationActive && voiceError != null && !isListening && spokenText.isBlank(),
                        enter = expandVertically() + fadeIn(),
                        exit = shrinkVertically() + fadeOut()
                    ) {
                        voiceError?.let { err ->
                            Box(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(horizontal = 16.dp, vertical = 6.dp),
                                contentAlignment = Alignment.Center
                            ) {
                                LiquidGlassPill(
                                    text = err,
                                    accentColor = StatusDanger,
                                    onClick = { viewModel.clearVoiceError() }
                                )
                            }
                        }
                    }

                    Composer(
                        text = inputText,
                        onTextChange = { inputText = it },
                        enabled = !isTyping,
                        placeholderText = if (isDirectWhatsAppSession) {
                            "Responder no WhatsApp (ou @aura p/ perguntar à IA)..."
                        } else {
                            "Pergunte à AURA sobre o posto..."
                        },
                        onSend = {
                            val toSend = inputText
                            inputText = ""
                            send(toSend)
                        },
                        onStartVoice = requestVoiceListening,
                        voiceRms = if (isListening || (isVoiceConversationActive && isSpeaking)) voiceRms else 0.05f,
                        onOpenCommandHub = { showCommandHubSheet = true },
                        onOpenVisionScanner = { showVisionScanner = true },
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

        if (showVisionScanner) {
            AuraVisionBottomSheet(
                onDismiss = { showVisionScanner = false },
                onAuditWithAura = { telemetry ->
                    viewModel.sendScannedDocument(telemetry)
                },
                scanner = viewModel.visionScanner,
                onDocumentCaptured = { uri, title ->
                    viewModel.setLastScannedDocument(uri, title)
                }
            )
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
        LaunchedEffect(showSessionsSheet) {
            viewModel.refreshHandoffThreads(syncEvolution = true)
        }
        var selectedHistoryTab by remember { mutableStateOf(if (totalUnreadHandoffs > 0) 1 else 0) }
        val analysisSessions = remember(sessions) {
            sessions.filter { !it.sessionId.startsWith("wa_handoff_") }
        }
        val localHandoffSessions = remember(sessions) {
            sessions.filter { it.sessionId.startsWith("wa_handoff_") }
        }

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
                    "Alternar entre análises com a AURA e retornos no WhatsApp",
                    style = MaterialTheme.typography.bodyMedium,
                    color = TextSecondary
                )
                Spacer(Modifier.height(14.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    val isAuraTab = selectedHistoryTab == 0
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .clip(RoundedCornerShape(14.dp))
                            .background(if (isAuraTab) AuraCyan.copy(alpha = 0.16f) else ObsidianMid)
                            .border(
                                1.dp,
                                if (isAuraTab) AuraCyan else GlassBorderSoft,
                                RoundedCornerShape(14.dp)
                            )
                            .clickable { selectedHistoryTab = 0 }
                            .padding(vertical = 10.dp, horizontal = 12.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "Análises AURA",
                            style = MaterialTheme.typography.labelLarge,
                            color = if (isAuraTab) AuraCyan else TextSecondary,
                            fontWeight = FontWeight.SemiBold,
                            maxLines = 1
                        )
                    }

                    val isWaTab = selectedHistoryTab == 1
                    Row(
                        modifier = Modifier
                            .weight(1f)
                            .clip(RoundedCornerShape(14.dp))
                            .background(if (isWaTab) AuraEmerald.copy(alpha = 0.16f) else ObsidianMid)
                            .border(
                                1.dp,
                                if (isWaTab) AuraEmerald else GlassBorderSoft,
                                RoundedCornerShape(14.dp)
                            )
                            .clickable { selectedHistoryTab = 1 }
                            .padding(vertical = 10.dp, horizontal = 12.dp),
                        horizontalArrangement = Arrangement.Center,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "Retornos WhatsApp",
                            style = MaterialTheme.typography.labelLarge,
                            color = if (isWaTab) AuraEmerald else TextSecondary,
                            fontWeight = FontWeight.SemiBold,
                            maxLines = 1
                        )
                        if (totalUnreadHandoffs > 0) {
                            Spacer(Modifier.width(6.dp))
                            Box(
                                modifier = Modifier
                                    .clip(CircleShape)
                                    .background(AuraEmerald)
                                    .padding(horizontal = 6.dp, vertical = 2.dp),
                                contentAlignment = Alignment.Center
                            ) {
                                Text(
                                    text = totalUnreadHandoffs.toString(),
                                    style = MaterialTheme.typography.labelSmall,
                                    color = ObsidianBase,
                                    fontWeight = FontWeight.Bold
                                )
                            }
                        }
                    }
                }

                Spacer(Modifier.height(14.dp))

                if (selectedHistoryTab == 0) {
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

                    Spacer(Modifier.height(12.dp))

                    LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        items(analysisSessions, key = { it.sessionId }) { session ->
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
                } else {
                    if (handoffThreads.isEmpty() && localHandoffSessions.isEmpty()) {
                        Text(
                            text = "Nenhum contato acionado via WhatsApp ainda. Envie um relatório pela AURA para abrir uma conversa dedicada aqui.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = TextMuted,
                            modifier = Modifier.padding(vertical = 12.dp)
                        )
                    } else if (handoffThreads.isNotEmpty()) {
                        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            items(handoffThreads, key = { it.session_id }) { thread ->
                                val hasUnread = thread.unread_count > 0
                                Row(
                                    Modifier
                                        .fillMaxWidth()
                                        .clip(RoundedCornerShape(16.dp))
                                        .background(ObsidianMid)
                                        .border(
                                            1.dp,
                                            if (hasUnread) AuraEmerald.copy(alpha = 0.65f) else GlassBorderSoft,
                                            RoundedCornerShape(16.dp)
                                        )
                                        .clickable {
                                            viewModel.openHandoffThread(thread.session_id, thread.thread_phone)
                                            showSessionsSheet = false
                                        }
                                        .padding(horizontal = 14.dp, vertical = 10.dp),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                                ) {
                                    Icon(
                                        imageVector = Icons.Rounded.Chat,
                                        contentDescription = null,
                                        tint = if (hasUnread) AuraEmerald else AuraCyan,
                                        modifier = Modifier.size(20.dp)
                                    )
                                    Column(Modifier.weight(1f)) {
                                        Row(
                                            verticalAlignment = Alignment.CenterVertically,
                                            horizontalArrangement = Arrangement.spacedBy(6.dp)
                                        ) {
                                            Text(
                                                text = "${thread.role_label ?: "WhatsApp"} • ${thread.contact_name ?: thread.thread_phone}",
                                                style = MaterialTheme.typography.titleSmall,
                                                color = TextPrimary,
                                                fontWeight = FontWeight.SemiBold,
                                                maxLines = 1,
                                                overflow = TextOverflow.Ellipsis,
                                                modifier = Modifier.weight(1f, fill = false)
                                            )
                                            Text(
                                                text = thread.thread_phone,
                                                style = MaterialTheme.typography.labelSmall,
                                                color = TextMuted,
                                                maxLines = 1
                                            )
                                        }
                                        Spacer(Modifier.height(2.dp))
                                        Text(
                                            text = thread.last_message_text.ifBlank { "Sem prévia" },
                                            style = MaterialTheme.typography.bodySmall,
                                            color = if (hasUnread) AuraEmerald else TextSecondary,
                                            maxLines = 1,
                                            overflow = TextOverflow.Ellipsis
                                        )
                                    }
                                    if (hasUnread) {
                                        Box(
                                            modifier = Modifier
                                                .clip(CircleShape)
                                                .background(AuraEmerald)
                                                .padding(horizontal = 8.dp, vertical = 3.dp),
                                            contentAlignment = Alignment.Center
                                        ) {
                                            Text(
                                                text = thread.unread_count.toString(),
                                                style = MaterialTheme.typography.labelSmall,
                                                color = ObsidianBase,
                                                fontWeight = FontWeight.Bold
                                            )
                                        }
                                    }
                                }
                            }
                        }
                    } else {
                        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            items(localHandoffSessions, key = { it.sessionId }) { session ->
                                Row(
                                    Modifier
                                        .fillMaxWidth()
                                        .clip(RoundedCornerShape(16.dp))
                                        .background(ObsidianMid)
                                        .border(1.dp, GlassBorderSoft, RoundedCornerShape(16.dp))
                                        .clickable {
                                            viewModel.openHandoffThread(session.sessionId)
                                            showSessionsSheet = false
                                        }
                                        .padding(horizontal = 16.dp, vertical = 12.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Text(
                                        text = session.title,
                                        style = MaterialTheme.typography.bodyLarge,
                                        color = TextPrimary,
                                        modifier = Modifier.weight(1f),
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    pendingHandoffAction?.let { handoffAction ->
        AuraHandoffRecipientDialog(
            action = handoffAction,
            contacts = handoffContacts,
            defaultRole = handoffAction.targetRole ?: lastHandoffRole,
            hasScannedDocument = hasScannedDocument,
            scannedDocumentTitle = lastScannedDocumentTitle,
            onDismiss = { pendingHandoffAction = null },
            onConfirm = { role, contactName, phone, customSummary, attachDoc ->
                val normalized = viewModel.normalizeWhatsAppPhone(phone)
                val cleanName = contactName.trim().ifBlank { role }
                viewModel.saveHandoffContact(
                    HandoffContact(
                        role = role,
                        name = cleanName,
                        phone = normalized
                    )
                )
                pendingHandoffAction = null
                executeSignedOrDirect(
                    handoffAction.copy(
                        targetRole = role,
                        targetContactName = cleanName,
                        targetPhone = normalized,
                        contextSummary = customSummary.trim().ifBlank { handoffAction.contextSummary },
                        includeAttachment = attachDoc
                    )
                )
            }
        )
    }
}

@Composable
private fun AuraHandoffRecipientDialog(
    action: GenUiAction,
    contacts: List<HandoffContact>,
    defaultRole: String,
    hasScannedDocument: Boolean,
    scannedDocumentTitle: String?,
    onDismiss: () -> Unit,
    onConfirm: (role: String, name: String, phone: String, summary: String, includeAttachment: Boolean) -> Unit
) {
    val roles = remember(contacts) {
        contacts.map { it.role }.ifEmpty { listOf("Contador", "Gerente de Pista", "Fornecedor", "Outro") }
    }
    var selectedRole by remember(action.actionId, defaultRole) {
        mutableStateOf(roles.firstOrNull { it.equals(defaultRole, ignoreCase = true) } ?: roles.first())
    }
    val initialContact = remember(selectedRole, contacts) {
        contacts.firstOrNull { it.role.equals(selectedRole, ignoreCase = true) }
    }
    var contactName by remember(action.actionId) {
        mutableStateOf(initialContact?.name?.ifBlank { selectedRole } ?: selectedRole)
    }
    var phoneInput by remember(action.actionId) {
        mutableStateOf(initialContact?.phone.orEmpty())
    }
    var summaryText by remember(action.actionId) {
        mutableStateOf(action.contextSummary.orEmpty())
    }
    var includeAttachment by remember(action.actionId, hasScannedDocument) {
        mutableStateOf(hasScannedDocument)
    }
    val digitsCount = phoneInput.count { it.isDigit() }
    val isPhoneValid = digitsCount >= 10

    val textFieldColors = OutlinedTextFieldDefaults.colors(
        focusedBorderColor = AuraCyan,
        unfocusedBorderColor = GlassBorderSoft,
        focusedTextColor = TextPrimary,
        unfocusedTextColor = TextPrimary,
        focusedLabelColor = AuraCyan,
        unfocusedLabelColor = TextSecondary,
        cursorColor = AuraCyan,
        focusedContainerColor = ObsidianLow,
        unfocusedContainerColor = ObsidianLow
    )

    Dialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(usePlatformDefaultWidth = false)
    ) {
        AuraCard(
            shape = RoundedCornerShape(26.dp),
            accent = AuraCyan,
            glowActive = true,
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 18.dp),
            contentPadding = PaddingValues(20.dp)
        ) {
            Column(
                verticalArrangement = Arrangement.spacedBy(14.dp),
                modifier = Modifier.verticalScroll(rememberScrollState())
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    StatusDot(color = AuraEmerald, pulsing = true, size = 7.dp)
                    SectionLabel("WHATSAPP HANDOFF • TEE")
                }

                Text(
                    text = action.label,
                    style = MaterialTheme.typography.headlineSmall,
                    color = TextPrimary
                )

                Text(
                    text = "Selecione ou salve o destinatário no posto para encaminhar com contexto no Command Journal.",
                    style = MaterialTheme.typography.bodySmall,
                    color = TextSecondary
                )

                LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(roles) { role ->
                        val isSelected = selectedRole.equals(role, ignoreCase = true)
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(50))
                                .background(
                                    if (isSelected) AuraCyan.copy(alpha = 0.18f) else ObsidianLow
                                )
                                .border(
                                    width = 1.dp,
                                    color = if (isSelected) AuraCyan else GlassBorderSoft,
                                    shape = RoundedCornerShape(50)
                                )
                                .clickable {
                                    selectedRole = role
                                    val saved = contacts.firstOrNull { it.role.equals(role, ignoreCase = true) }
                                    contactName = saved?.name?.ifBlank { role } ?: role
                                    phoneInput = saved?.phone.orEmpty()
                                }
                                .padding(horizontal = 14.dp, vertical = 8.dp)
                        ) {
                            Text(
                                text = role,
                                style = MaterialTheme.typography.labelMedium,
                                color = if (isSelected) AuraCyan else TextSecondary
                            )
                        }
                    }
                }

                OutlinedTextField(
                    value = contactName,
                    onValueChange = { contactName = it },
                    label = { Text("Nome / Setor") },
                    singleLine = true,
                    colors = textFieldColors,
                    shape = RoundedCornerShape(14.dp),
                    modifier = Modifier.fillMaxWidth()
                )

                OutlinedTextField(
                    value = phoneInput,
                    onValueChange = { next ->
                        phoneInput = next.filter { it.isDigit() || it == '+' || it == ' ' || it == '-' || it == '(' || it == ')' }
                    },
                    label = { Text("WhatsApp (DDD + número)") },
                    placeholder = { Text("Ex.: 5527999999999", color = TextMuted) },
                    supportingText = {
                        Text(
                            text = if (isPhoneValid) "Contato será salvo para '$selectedRole'." else "Informe ao menos 10 dígitos (DDD + número).",
                            color = if (isPhoneValid) AuraEmerald else TextMuted
                        )
                    },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
                    colors = textFieldColors,
                    shape = RoundedCornerShape(14.dp),
                    modifier = Modifier.fillMaxWidth()
                )

                OutlinedTextField(
                    value = summaryText,
                    onValueChange = { summaryText = it.take(3000) },
                    label = { Text("Relatório formatado para WhatsApp") },
                    minLines = 5,
                    maxLines = 8,
                    colors = textFieldColors,
                    shape = RoundedCornerShape(14.dp),
                    modifier = Modifier.fillMaxWidth()
                )

                if (hasScannedDocument) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(14.dp))
                            .background(ObsidianLow)
                            .border(
                                1.dp,
                                if (includeAttachment) AuraEmerald.copy(alpha = 0.6f) else GlassBorderSoft,
                                RoundedCornerShape(14.dp)
                            )
                            .clickable { includeAttachment = !includeAttachment }
                            .padding(horizontal = 14.dp, vertical = 10.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                            Text(
                                text = "Anexar cópia da nota escaneada",
                                style = MaterialTheme.typography.labelLarge,
                                color = TextPrimary
                            )
                            Text(
                                text = scannedDocumentTitle ?: "Documento / DANFE capturado",
                                style = MaterialTheme.typography.bodySmall,
                                color = if (includeAttachment) AuraEmerald else TextMuted
                            )
                        }
                        Switch(
                            checked = includeAttachment,
                            onCheckedChange = { includeAttachment = it },
                            colors = SwitchDefaults.colors(
                                checkedThumbColor = ObsidianBase,
                                checkedTrackColor = AuraEmerald
                            )
                        )
                    }
                }

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    AuraGhostButton(
                        text = "Cancelar",
                        onClick = onDismiss,
                        modifier = Modifier.weight(1f),
                        tint = TextSecondary
                    )
                    AuraGradientButton(
                        text = "Assinar e Enviar",
                        enabled = isPhoneValid,
                        onClick = {
                            onConfirm(selectedRole, contactName, phoneInput, summaryText, includeAttachment)
                        },
                        modifier = Modifier.weight(1.3f)
                    )
                }
            }
        }
    }
}

@Composable
private fun HandoffReplyTopBanner(
    alert: IncomingHandoffAlert,
    onOpen: () -> Unit,
    onDismiss: () -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 6.dp)
            .clip(RoundedCornerShape(18.dp))
            .background(ObsidianLow.copy(alpha = 0.96f))
            .border(1.dp, AuraEmerald.copy(alpha = 0.75f), RoundedCornerShape(18.dp))
            .clickable { onOpen() }
            .padding(horizontal = 12.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        StatusDot(color = AuraEmerald, size = 8.dp, pulsing = true)
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = "💬 ${alert.roleLabel}: ${alert.contactName} respondeu",
                style = MaterialTheme.typography.labelLarge,
                color = AuraEmerald,
                fontWeight = FontWeight.Bold,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
            Text(
                text = alert.previewText,
                style = MaterialTheme.typography.bodySmall,
                color = TextPrimary,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
        }
        Box(
            modifier = Modifier
                .clip(RoundedCornerShape(12.dp))
                .background(AuraEmerald)
                .clickable { onOpen() }
                .padding(horizontal = 10.dp, vertical = 5.dp)
        ) {
            Text(
                text = "Abrir",
                style = MaterialTheme.typography.labelMedium,
                color = ObsidianBase,
                fontWeight = FontWeight.Bold
            )
        }
        IconButton(
            onClick = onDismiss,
            modifier = Modifier.size(28.dp)
        ) {
            Icon(
                imageVector = Icons.Default.Close,
                contentDescription = "Fechar alerta",
                tint = TextMuted,
                modifier = Modifier.size(16.dp)
            )
        }
    }
}

@Composable
private fun ActiveWhatsAppSessionBar(
    contactName: String,
    phone: String,
    onBackToAura: () -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(AuraEmerald.copy(alpha = 0.12f))
            .border(0.5.dp, AuraEmerald.copy(alpha = 0.4f))
            .padding(horizontal = 14.dp, vertical = 7.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Icon(
            imageVector = Icons.Rounded.Chat,
            contentDescription = null,
            tint = AuraEmerald,
            modifier = Modifier.size(16.dp)
        )
        Text(
            text = "Canal Direto WhatsApp • $contactName ($phone)",
            style = MaterialTheme.typography.labelMedium,
            color = TextPrimary,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.weight(1f)
        )
        Box(
            modifier = Modifier
                .clip(RoundedCornerShape(12.dp))
                .background(ObsidianMid)
                .border(1.dp, AuraCyan.copy(alpha = 0.6f), RoundedCornerShape(12.dp))
                .clickable { onBackToAura() }
                .padding(horizontal = 10.dp, vertical = 4.dp)
        ) {
            Text(
                text = "Voltar p/ AURA",
                style = MaterialTheme.typography.labelSmall,
                color = AuraCyan,
                fontWeight = FontWeight.SemiBold
            )
        }
    }
}

@Composable
private fun ChatHeader(
    title: String,
    isTyping: Boolean,
    activeMode: String? = null,
    isVoiceConversationActive: Boolean = false,
    totalUnreadHandoffs: Int = 0,
    onToggleVoiceConversation: () -> Unit = {},
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

                IconButton(onClick = onToggleVoiceConversation) {
                    Icon(
                        imageVector = if (isVoiceConversationActive) Icons.Rounded.Stop else Icons.Rounded.Mic,
                        contentDescription = if (isVoiceConversationActive) "Encerrar Voz" else "Conversa por Voz",
                        tint = if (isVoiceConversationActive) StatusDanger else AuraCyan
                    )
                }
                IconButton(onClick = onOpenCommandHub) {
                    Icon(Icons.Rounded.Tune, "Aura Hub", tint = AuraCyan)
                }
                IconButton(onClick = onHistory) {
                    Box {
                        Icon(Icons.Default.History, "Histórico", tint = TextSecondary)
                        if (totalUnreadHandoffs > 0) {
                            Box(
                                modifier = Modifier
                                    .align(Alignment.TopEnd)
                                    .size(9.dp)
                                    .clip(CircleShape)
                                    .background(AuraEmerald)
                            )
                        }
                    }
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
            envelopeJson = message.envelopeJson,
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

private data class UserVisionAttachmentCard(
    val title: String,
    val sourceFormat: String,
    val accessKey: String?,
    val accessKeyVerified: Boolean,
    val highlights: String,
    val previewPath: String?
)

private fun parseUserVisionCard(envelopeJson: String?): UserVisionAttachmentCard? {
    if (envelopeJson.isNullOrBlank()) return null
    return runCatching {
        val obj = Json.parseToJsonElement(envelopeJson).jsonObject
        if (obj["type"]?.jsonPrimitive?.contentOrNull != "user_vision_card") return null
        UserVisionAttachmentCard(
            title = obj["title"]?.jsonPrimitive?.contentOrNull ?: "Documento Auditado",
            sourceFormat = obj["sourceFormat"]?.jsonPrimitive?.contentOrNull ?: "NPU",
            accessKey = obj["accessKey"]?.jsonPrimitive?.contentOrNull,
            accessKeyVerified = obj["accessKeyVerified"]?.jsonPrimitive?.booleanOrNull ?: false,
            highlights = obj["highlights"]?.jsonPrimitive?.contentOrNull.orEmpty(),
            previewPath = obj["previewPath"]?.jsonPrimitive?.contentOrNull
        )
    }.getOrNull()
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun UserBubble(
    text: String,
    envelopeJson: String? = null,
    onLongClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val haptic = LocalHapticFeedback.current
    val shape = RoundedCornerShape(22.dp, 22.dp, 6.dp, 22.dp)
    val visionCard = remember(envelopeJson) { parseUserVisionCard(envelopeJson) }
    val previewBitmap by produceState<ImageBitmap?>(initialValue = null, key1 = visionCard?.previewPath) {
        val path = visionCard?.previewPath
        value = if (path != null) {
            withContext(Dispatchers.IO) {
                runCatching {
                    val file = File(path)
                    if (file.exists()) {
                        val opts = BitmapFactory.Options().apply { inSampleSize = 2 }
                        BitmapFactory.decodeFile(file.absolutePath, opts)?.asImageBitmap()
                    } else null
                }.getOrNull()
            }
        } else null
    }

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
                .padding(horizontal = 14.dp, vertical = 12.dp)
        ) {
            if (visionCard != null) {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    previewBitmap?.let { img ->
                        Image(
                            bitmap = img,
                            contentDescription = visionCard.title,
                            contentScale = ContentScale.Crop,
                            modifier = Modifier
                                .fillMaxWidth()
                                .heightIn(max = 140.dp)
                                .clip(RoundedCornerShape(12.dp))
                                .border(1.dp, GlassBorderSoft, RoundedCornerShape(12.dp))
                        )
                    }
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Rounded.DocumentScanner,
                            contentDescription = null,
                            tint = AuraCyan,
                            modifier = Modifier.size(16.dp)
                        )
                        Text(
                            text = visionCard.title,
                            style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                            color = TextPrimary,
                            modifier = Modifier.weight(1f)
                        )
                    }
                    if (!visionCard.accessKey.isNullOrBlank()) {
                        Text(
                            text = "Chave: ${visionCard.accessKey.chunked(4).joinToString(" ")}" +
                                if (visionCard.accessKeyVerified) " ✓" else "",
                            style = MaterialTheme.typography.labelSmall.copy(
                                fontFamily = FontFamily.Monospace,
                                fontSize = 10.sp
                            ),
                            color = if (visionCard.accessKeyVerified) AuraEmerald else AuraCyan
                        )
                    }
                    if (visionCard.highlights.isNotBlank()) {
                        Text(
                            text = visionCard.highlights,
                            style = MaterialTheme.typography.bodySmall,
                            color = TextSecondary
                        )
                    }
                    Text(
                        text = text,
                        style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Medium),
                        color = TextPrimary
                    )
                }
            } else {
                Text(
                    text = text,
                    style = MaterialTheme.typography.bodyLarge,
                    color = TextPrimary
                )
            }
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
    val contextUpper = remember(message.text, card?.title) {
        "${card?.title.orEmpty()} ${message.text}".uppercase()
    }
    val isFiscalContext = remember(contextUpper) {
        listOf("SEFAZ", "DANFE", "NF-E", "NFE", "NFC-E", "ICMS", "CFOP", "NOTA FISCAL", "VPROD", "REJEI").any {
            contextUpper.contains(it)
        }
    }
    val isTankContext = remember(contextUpper) {
        listOf("TANQUE", "LMC", "BOMBA", "BICO", "LITROS", "ESTOQUE").any {
            contextUpper.contains(it)
        }
    }
    val domainBadgeLabel = when {
        message.isStreaming -> "Analisando..."
        isFiscalContext -> "Fiscal • SEFAZ"
        isTankContext -> "Pista • ANP"
        else -> "Consultor"
    }
    val domainBadgeAccent = when {
        message.isStreaming -> AuraCyan
        isFiscalContext -> AuraCyan
        isTankContext -> AuraEmerald
        else -> AuraPurple
    }

    Column(
        modifier = modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        // Cabeçalho compacto libera toda a largura horizontal para o texto e cards GenUI
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            AuraAvatar(size = 22.dp)
            Text(
                text = "AURA",
                style = MaterialTheme.typography.labelMedium,
                color = TextPrimary
            )
            LiquidGlassPill(
                text = domainBadgeLabel,
                accentColor = domainBadgeAccent
            )
        }

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
                        .clip(RoundedCornerShape(6.dp, 20.dp, 20.dp, 20.dp))
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
                        .border(1.dp, LiquidIridescentSubtleBrush, RoundedCornerShape(6.dp, 20.dp, 20.dp, 20.dp))
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

                // Barra de Micro-Ações de Contexto da Aura (rolável horizontalmente e sensível ao domínio)
                if (!message.isStreaming) {
                    LazyRow(
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(top = 2.dp)
                    ) {
                        item {
                            val isSpeakingThis = speakingMessageId == message.id
                            LiquidGlassPill(
                                text = if (isSpeakingThis) "Parar" else "Ouvir",
                                icon = if (isSpeakingThis) Icons.Rounded.Stop else Icons.Rounded.VolumeUp,
                                accentColor = if (isSpeakingThis) StatusDanger else AuraCyan,
                                onClick = { onToggleSpeech(message.id, message.text) }
                            )
                        }

                        item {
                            LiquidGlassPill(
                                text = "Raciocínio",
                                icon = Icons.Rounded.Psychology,
                                accentColor = AuraEmerald,
                                onClick = onDeepDive
                            )
                        }

                        item {
                            if (isFiscalContext) {
                                LiquidGlassPill(
                                    text = "Validar SEFAZ",
                                    icon = Icons.Rounded.Security,
                                    accentColor = AuraCyan,
                                    onClick = {
                                        onDrillDown("Me dê o passo a passo exato para corrigir ou validar essa divergência fiscal na nota / SEFAZ sem travar a operação.")
                                    }
                                )
                            } else {
                                LiquidGlassPill(
                                    text = "ANP",
                                    icon = Icons.Rounded.Security,
                                    accentColor = AuraPurple,
                                    onClick = onAuditAnp
                                )
                            }
                        }

                        item {
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
        }
        card?.let { parsedCard ->
            GenUiCardView(
                card = parsedCard,
                onAction = { action ->
                    if (action.isHandoffAction()) {
                        val richReport = AuraWhatsAppReportFormatter.buildReport(
                            card = parsedCard,
                            narrativeText = message.text,
                            actionLabel = action.label
                        )
                        onAction(action.copy(contextSummary = richReport))
                    } else {
                        onAction(action)
                    }
                },
                onDrillDown = onDrillDown
            )
        }
    }
}

/** Composer flutuante com Spatial UI, gatilho do Aura Command Hub e iluminação de vidro líquido */
@Composable
private fun Composer(
    text: String,
    onTextChange: (String) -> Unit,
    enabled: Boolean,
    placeholderText: String = "Pergunte à AURA sobre o posto...",
    onSend: () -> Unit,
    onStartVoice: () -> Unit = {},
    voiceRms: Float = 0.05f,
    onOpenCommandHub: () -> Unit,
    onOpenVisionScanner: () -> Unit = {},
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

            // Botão Olhos da AURA (Scanner Neural NPU)
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
                        onOpenVisionScanner()
                    },
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Rounded.DocumentScanner,
                    contentDescription = "Olhos da AURA (Scanner NPU)",
                    tint = AuraCyan,
                    modifier = Modifier.size(20.dp)
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
                                    placeholderText,
                                    style = MaterialTheme.typography.bodyLarge,
                                    color = TextMuted,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis
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
