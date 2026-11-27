package com.example.aurapostoassitance.ui.dashboard

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.spring
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
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
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.Chat
import androidx.compose.material.icons.automirrored.rounded.VolumeUp
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material.icons.rounded.CheckCircle
import androidx.compose.material.icons.rounded.Close
import androidx.compose.material.icons.rounded.DirectionsCar
import androidx.compose.material.icons.rounded.Fingerprint
import androidx.compose.material.icons.rounded.Key
import androidx.compose.material.icons.rounded.Memory
import androidx.compose.material.icons.rounded.PlayArrow
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material.icons.rounded.Stop
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.example.aurapostoassitance.ui.components.AuraAmbientBackground
import com.example.aurapostoassitance.ui.components.AuraBottomGlassDock
import com.example.aurapostoassitance.ui.components.AuraBrandTitle
import com.example.aurapostoassitance.ui.components.AuraChip
import com.example.aurapostoassitance.ui.components.AuraDynamicIsland
import com.example.aurapostoassitance.ui.components.AuraGradientButton
import com.example.aurapostoassitance.ui.components.AuraLivingOrb
import com.example.aurapostoassitance.ui.components.AuraNavTab
import com.example.aurapostoassitance.ui.components.AuraOrbMode
import com.example.aurapostoassitance.ui.components.LiquidGlassPill
import com.example.aurapostoassitance.ui.components.SectionLabel
import com.example.aurapostoassitance.ui.components.SpatialGlassCard
import com.example.aurapostoassitance.ui.components.findFragmentActivity
import com.example.aurapostoassitance.ui.domain.AuraDomainAdapter
import com.example.aurapostoassitance.ui.domain.DomainTrigger
import com.example.aurapostoassitance.ui.genui.GovernanceHiCBanner
import com.example.aurapostoassitance.ui.genui.RealizedRoiScorecardCard
import com.example.aurapostoassitance.ui.genui.WhatIfSimulatorCard
import com.example.aurapostoassitance.ui.intelligence.AuraIntelligenceViewModel
import com.example.aurapostoassitance.ui.theme.AuraCyan
import com.example.aurapostoassitance.ui.theme.AuraEmerald
import com.example.aurapostoassitance.ui.theme.AuraPurple
import com.example.aurapostoassitance.ui.theme.AuraTypographyExt
import com.example.aurapostoassitance.ui.theme.BorderHairline
import com.example.aurapostoassitance.ui.theme.NewsreaderFamily
import com.example.aurapostoassitance.ui.theme.ObsidianBase
import com.example.aurapostoassitance.ui.theme.ObsidianLow
import com.example.aurapostoassitance.ui.theme.StatusDanger
import com.example.aurapostoassitance.ui.theme.StatusSuccess
import com.example.aurapostoassitance.ui.theme.StatusWarning
import com.example.aurapostoassitance.ui.theme.TextMuted
import com.example.aurapostoassitance.ui.theme.TextPrimary
import com.example.aurapostoassitance.ui.theme.TextSecondary
import com.example.aurapostoassitance.ui.vision.AuraVisionBottomSheet

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(
    onNavigateToChat: (String?) -> Unit,
    onNavigateToSetup: () -> Unit = {},
    viewModel: DashboardViewModel = hiltViewModel(),
    intelligenceViewModel: AuraIntelligenceViewModel = hiltViewModel()
) {
    var selectedTab by remember { mutableStateOf(AuraNavTab.PULSO) }
    val context = LocalContext.current
    val activity = remember(context) { context.findFragmentActivity() }
    var showVisionScanner by remember { mutableStateOf(false) }
    var showSiliconSheet by remember { mutableStateOf(false) }
    var showWhatIfSheet by remember { mutableStateOf(false) }

    val selectedSegment by viewModel.selectedSegment.collectAsState()
    val whatIfState by intelligenceViewModel.whatIfState.collectAsState()
    val governanceState by intelligenceViewModel.governanceState.collectAsState()
    val scorecardState by intelligenceViewModel.scorecardState.collectAsState()
    val activeProfile = remember(selectedSegment) { AuraDomainAdapter.profileFor(selectedSegment) }
    val isServerOnline by viewModel.isServerOnline.collectAsState()
    val authExpiredMessage by viewModel.authExpiredMessage.collectAsState()
    val islandTelemetry by viewModel.islandTelemetry.collectAsState()
    val briefingState by viewModel.briefingState.collectAsState()
    val hardwareStatus by viewModel.hardwareStatus.collectAsState()
    val isSpeaking by viewModel.isSpeaking.collectAsState()
    val speakingMessageId by viewModel.speakingMessageId.collectAsState()
    val voiceAmplitude by viewModel.voiceAmplitude.collectAsState()
    val physicalContext by viewModel.physicalContext.collectAsState()
    val actionFeedback by viewModel.actionFeedback.collectAsState()
    val signedActions by viewModel.signedActions.collectAsState()
    val isExecutingAction by viewModel.isExecutingAction.collectAsState()
    val handoffUnreadCount by viewModel.handoffUnreadCount.collectAsState()
    val handoffThreadCount by viewModel.handoffThreadCount.collectAsState()

    LaunchedEffect(Unit) {
        selectedTab = AuraNavTab.PULSO
        viewModel.refreshHandoffSummary()
        viewModel.refreshLiveTelemetry(selectedSegment)
    }

    val isPlayingBriefing = isSpeaking && speakingMessageId == "briefing_$selectedSegment"

    val (statusLabel, statusAccent, statusPulse) = when (isServerOnline) {
        true -> Triple("Online", StatusSuccess, true)
        false -> Triple("Vault Offline", StatusWarning, false)
        null -> Triple("Sincronizando...", AuraCyan, true)
    }

    AuraAmbientBackground {
        Scaffold(
            containerColor = Color.Transparent,
            topBar = {
                TopAppBar(
                    title = {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            AuraBrandTitle(
                                text = "AURA",
                                style = MaterialTheme.typography.titleLarge
                            )
                            LiquidGlassPill(
                                text = statusLabel,
                                accentColor = statusAccent,
                                pulsingDot = statusPulse,
                                onClick = { viewModel.refreshLiveTelemetry(selectedSegment) }
                            )
                        }
                    },
                    actions = {
                        // Telemetria de Silício compacta sob demanda (libera o topo do Dashboard)
                        LiquidGlassPill(
                            text = "${"%.0f".format(hardwareStatus.lastInferenceLatencyMs)}ms NPU",
                            icon = Icons.Rounded.Memory,
                            accentColor = AuraPurple,
                            onClick = { showSiliconSheet = true },
                            modifier = Modifier.padding(end = 12.dp)
                        )
                    },
                    colors = TopAppBarDefaults.topAppBarColors(
                        containerColor = Color.Transparent
                    )
                )
            },
            bottomBar = {
                AuraBottomGlassDock(
                    selectedTab = selectedTab,
                    handoffUnreadCount = handoffUnreadCount,
                    handoffThreadCount = handoffThreadCount,
                    resourceTabLabel = activeProfile.resourceTabLabel,
                    resourceTabIcon = activeProfile.resourceTabIcon,
                    onTabSelected = { tab ->
                        selectedTab = tab
                        when (tab) {
                            AuraNavTab.PULSO -> Unit
                            AuraNavTab.COCKPIT -> onNavigateToChat(null)
                            AuraNavTab.RETORNOS -> onNavigateToChat("OPEN_WHATSAPP_RETURNS")
                            AuraNavTab.TANQUES -> onNavigateToChat(activeProfile.resourceTabQuery)
                            AuraNavTab.CONEXAO -> onNavigateToSetup()
                        }
                    }
                )
            }
        ) { paddingValues ->
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(paddingValues)
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = 20.dp, vertical = 8.dp)
            ) {
                // Alerta de Sessão 401 (Alinhamento Carbon Core P0.1)
                AnimatedVisibility(visible = authExpiredMessage != null) {
                    authExpiredMessage?.let { msg ->
                        SpatialGlassCard(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(bottom = 12.dp),
                            accent = StatusDanger,
                            glowActive = true,
                            contentPadding = PaddingValues(14.dp),
                            onClick = {
                                viewModel.dismissAuthExpired()
                                onNavigateToSetup()
                            }
                        ) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(10.dp)
                            ) {
                                Icon(
                                    imageVector = Icons.Rounded.Key,
                                    contentDescription = null,
                                    tint = StatusDanger,
                                    modifier = Modifier.size(20.dp)
                                )
                                Column(modifier = Modifier.weight(1f)) {
                                    Text(
                                        text = "CHAVE DE ACESSO NECESSÁRIA",
                                        style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                                        color = StatusDanger
                                    )
                                    Text(
                                        text = "$msg Toque para configurar.",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = TextPrimary
                                    )
                                }
                            }
                        }
                    }
                }

                // Banner de Modo Carro / Hands-Free
                if (physicalContext.isCarModeActive) {
                    SpatialGlassCard(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(bottom = 12.dp),
                        accent = AuraEmerald,
                        contentPadding = PaddingValues(12.dp)
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Row(
                                modifier = Modifier.weight(1f),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Icon(
                                    imageVector = Icons.Rounded.DirectionsCar,
                                    contentDescription = null,
                                    tint = AuraEmerald,
                                    modifier = Modifier.size(20.dp)
                                )
                                Spacer(modifier = Modifier.width(10.dp))
                                Column {
                                    Text(
                                        text = "MODO COCKPIT AUTOMOTIVO",
                                        style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                                        color = AuraEmerald
                                    )
                                    Text(
                                        text = physicalContext.recommendedModeLabel,
                                        style = MaterialTheme.typography.bodySmall,
                                        color = TextPrimary
                                    )
                                }
                            }
                            AuraChip(
                                label = "Sair",
                                icon = Icons.Rounded.Close,
                                onClick = { viewModel.toggleCarMode() }
                            )
                        }
                    }
                }

                // Header Editorial Deluxe
                Text(
                    text = "Pulso Executivo",
                    style = MaterialTheme.typography.displayMedium.copy(
                        fontFamily = NewsreaderFamily,
                        letterSpacing = (-0.5).sp
                    ),
                    color = TextPrimary
                )
                Spacer(modifier = Modifier.height(3.dp))
                Text(
                    text = activeProfile.subtitle,
                    style = MaterialTheme.typography.bodyMedium,
                    color = TextSecondary
                )

                Spacer(modifier = Modifier.height(14.dp))

                // Dynamic Island de Telemetria Real (Zero-Click Feed)
                AuraDynamicIsland(
                    telemetry = islandTelemetry,
                    onQueryAction = { query -> onNavigateToChat(query) }
                )

                Spacer(modifier = Modifier.height(16.dp))

                // Seletor dos 5 Domain Packs Oficiais (com estado selecionado corrigido!)
                SectionLabel(text = "Vertical Operacional (Domain Pack)")
                Spacer(modifier = Modifier.height(8.dp))
                LazyRow(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    contentPadding = PaddingValues(bottom = 4.dp)
                ) {
                    items(viewModel.availableProfiles, key = { it.packId }) { profile ->
                        val isSelected = profile.packId == activeProfile.packId
                        AuraChip(
                            label = profile.shortLabel,
                            icon = profile.icon,
                            selected = isSelected,
                            accentColor = AuraCyan,
                            onClick = { viewModel.selectSegment(profile.packId) }
                        )
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))

                // CARD BRIEFING MATINAL VOICE-FIRST (Orbe integrado no header, sem espaço morto)
                val briefingOrbSize by animateDpAsState(
                    targetValue = if (isPlayingBriefing) 54.dp else 48.dp,
                    animationSpec = spring(dampingRatio = 0.78f, stiffness = 320f),
                    label = "briefingOrbSize"
                )
                SpatialGlassCard(
                    modifier = Modifier.fillMaxWidth(),
                    accent = if (isPlayingBriefing) AuraPurple else AuraCyan,
                    glowActive = isPlayingBriefing,
                    iridescentBorder = isPlayingBriefing,
                    contentPadding = PaddingValues(18.dp)
                ) {
                    Column(modifier = Modifier.fillMaxWidth()) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                modifier = Modifier.weight(1f)
                            ) {
                                AuraLivingOrb(
                                    sizeDp = briefingOrbSize,
                                    voiceRms = if (isPlayingBriefing) voiceAmplitude else 0.06f,
                                    pulsing = true,
                                    activeColor = if (isPlayingBriefing) AuraPurple else AuraCyan,
                                    mode = when {
                                        briefingState is BriefingUiState.Loading -> AuraOrbMode.THINKING
                                        isPlayingBriefing -> AuraOrbMode.ACTIVE
                                        else -> AuraOrbMode.IDLE
                                    }
                                )
                                Spacer(modifier = Modifier.width(10.dp))
                                Column {
                                    Text(
                                        text = "BRIEFING MATINAL",
                                        style = MaterialTheme.typography.labelSmall.copy(
                                            fontWeight = FontWeight.Bold,
                                            letterSpacing = 1.2.sp
                                        ),
                                        color = if (isPlayingBriefing) AuraPurple else AuraCyan
                                    )
                                    Text(
                                        text = "Modo Sócio Consultor (45s)",
                                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold),
                                        color = TextPrimary,
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis
                                    )
                                }
                            }

                            Spacer(modifier = Modifier.width(8.dp))

                            LiquidGlassPill(
                                text = if (isPlayingBriefing) "Voz Ativa" else "Pronto",
                                accentColor = if (isPlayingBriefing) AuraPurple else StatusSuccess,
                                pulsingDot = isPlayingBriefing
                            )
                        }

                        Spacer(modifier = Modifier.height(12.dp))

                        when (val state = briefingState) {
                            is BriefingUiState.Loading -> {
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(vertical = 14.dp),
                                    horizontalArrangement = Arrangement.Center,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    CircularProgressIndicator(
                                        modifier = Modifier.size(20.dp),
                                        color = AuraCyan,
                                        strokeWidth = 2.dp
                                    )
                                    Spacer(modifier = Modifier.width(10.dp))
                                    Text(
                                        text = "Sintetizando diagnóstico executivo...",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = TextSecondary
                                    )
                                }
                            }

                            is BriefingUiState.Error -> {
                                Column(modifier = Modifier.fillMaxWidth()) {
                                    Text(
                                        text = state.message,
                                        style = MaterialTheme.typography.bodySmall,
                                        color = StatusWarning
                                    )
                                    Spacer(modifier = Modifier.height(8.dp))
                                    AuraChip(
                                        label = "Tentar novamente",
                                        icon = Icons.Rounded.Refresh,
                                        onClick = { viewModel.loadBriefing() }
                                    )
                                }
                            }

                            is BriefingUiState.Success -> {
                                val briefing = state.briefing
                                Text(
                                    text = briefing.oralVoiceScript,
                                    style = MaterialTheme.typography.bodySmall.copy(lineHeight = 19.sp),
                                    color = TextSecondary,
                                    maxLines = 4,
                                    overflow = TextOverflow.Ellipsis
                                )

                                Spacer(modifier = Modifier.height(14.dp))

                                AuraGradientButton(
                                    text = if (isPlayingBriefing) "Pausar Áudio do Dia" else "Ouvir Resumo do Dia (45s)",
                                    icon = if (isPlayingBriefing) Icons.Rounded.Stop else Icons.Rounded.PlayArrow,
                                    onClick = { viewModel.togglePlayBriefing() },
                                    modifier = Modifier.fillMaxWidth()
                                )

                                if (briefing.suggestedActions.isNotEmpty()) {
                                    Spacer(modifier = Modifier.height(16.dp))
                                    Text(
                                        text = "GATILHOS DE 1 TOQUE (ASSINATURA TEE)",
                                        style = MaterialTheme.typography.labelSmall.copy(
                                            letterSpacing = 0.8.sp,
                                            fontWeight = FontWeight.Bold
                                        ),
                                        color = TextMuted
                                    )
                                    Spacer(modifier = Modifier.height(8.dp))

                                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                        briefing.suggestedActions.forEach { action ->
                                            val signedReceipt = signedActions[action.code]
                                            Row(
                                                modifier = Modifier
                                                    .fillMaxWidth()
                                                    .clip(RoundedCornerShape(12.dp))
                                                    .background(ObsidianBase.copy(alpha = 0.65f))
                                                    .border(
                                                        width = 1.dp,
                                                        color = if (signedReceipt != null) AuraEmerald.copy(alpha = 0.45f) else BorderHairline,
                                                        shape = RoundedCornerShape(12.dp)
                                                    )
                                                    .clickable(enabled = !isExecutingAction && signedReceipt == null) {
                                                        val act = activity ?: context.findFragmentActivity()
                                                        if (act != null) {
                                                            viewModel.authenticateAndExecuteBriefingAction(
                                                                act,
                                                                action.code,
                                                                action.description ?: action.label
                                                            )
                                                        } else {
                                                            viewModel.executeBriefingAction(
                                                                action.code,
                                                                action.description ?: action.label
                                                            )
                                                        }
                                                    }
                                                    .padding(horizontal = 14.dp, vertical = 10.dp),
                                                verticalAlignment = Alignment.CenterVertically,
                                                horizontalArrangement = Arrangement.SpaceBetween
                                            ) {
                                                Row(
                                                    modifier = Modifier.weight(1f),
                                                    verticalAlignment = Alignment.CenterVertically
                                                ) {
                                                    Box(
                                                        modifier = Modifier
                                                            .size(24.dp)
                                                            .clip(CircleShape)
                                                            .background(AuraCyan.copy(alpha = 0.16f)),
                                                        contentAlignment = Alignment.Center
                                                    ) {
                                                        Text(
                                                            text = action.code,
                                                            style = AuraTypographyExt.kpiCompact.copy(fontSize = 11.sp),
                                                            color = AuraCyan
                                                        )
                                                    }
                                                    Spacer(modifier = Modifier.width(10.dp))
                                                    Text(
                                                        text = action.label,
                                                        style = MaterialTheme.typography.bodySmall.copy(fontWeight = FontWeight.Medium),
                                                        color = TextPrimary,
                                                        maxLines = 1,
                                                        overflow = TextOverflow.Ellipsis
                                                    )
                                                }
                                                Row(verticalAlignment = Alignment.CenterVertically) {
                                                    if (signedReceipt != null) {
                                                        Icon(
                                                            imageVector = Icons.Rounded.CheckCircle,
                                                            contentDescription = "Assinado TEE",
                                                            tint = AuraEmerald,
                                                            modifier = Modifier.size(15.dp)
                                                        )
                                                        Spacer(modifier = Modifier.width(4.dp))
                                                        Text(
                                                            text = signedReceipt,
                                                            style = AuraTypographyExt.monoAudit,
                                                            color = AuraEmerald
                                                        )
                                                    } else if (isExecutingAction) {
                                                        CircularProgressIndicator(
                                                            modifier = Modifier.size(14.dp),
                                                            strokeWidth = 2.dp,
                                                            color = AuraCyan
                                                        )
                                                    } else {
                                                        Icon(
                                                            imageVector = Icons.Rounded.Fingerprint,
                                                            contentDescription = "Assinar TEE",
                                                            tint = AuraCyan,
                                                            modifier = Modifier.size(15.dp)
                                                        )
                                                        Spacer(modifier = Modifier.width(4.dp))
                                                        Text(
                                                            text = "Assinar",
                                                            style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.SemiBold),
                                                            color = AuraCyan
                                                        )
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            BriefingUiState.Idle -> Unit
                        }
                    }
                }

                // Feedback do Command Journal
                AnimatedVisibility(
                    visible = actionFeedback != null,
                    enter = fadeIn(),
                    exit = fadeOut()
                ) {
                    actionFeedback?.let { feedback ->
                        Spacer(modifier = Modifier.height(12.dp))
                        SpatialGlassCard(
                            modifier = Modifier.fillMaxWidth(),
                            accent = AuraEmerald,
                            contentPadding = PaddingValues(14.dp)
                        ) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Row(
                                    modifier = Modifier.weight(1f),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Icon(
                                        imageVector = Icons.Rounded.CheckCircle,
                                        contentDescription = null,
                                        tint = StatusSuccess,
                                        modifier = Modifier.size(18.dp)
                                    )
                                    Spacer(modifier = Modifier.width(10.dp))
                                    Text(
                                        text = feedback,
                                        style = MaterialTheme.typography.bodySmall,
                                        color = TextPrimary
                                    )
                                }
                                IconButton(
                                    onClick = { viewModel.clearFeedback() },
                                    modifier = Modifier.size(28.dp)
                                ) {
                                    Icon(
                                        imageVector = Icons.Rounded.Close,
                                        contentDescription = "Fechar",
                                        tint = TextMuted,
                                        modifier = Modifier.size(16.dp)
                                    )
                                }
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(18.dp))

                if (governanceState.hasContent) {
                    GovernanceHiCBanner(
                        state = governanceState,
                        onToggleExpanded = { intelligenceViewModel.toggleGovernanceExpanded() },
                        onApproveRule = { ruleId ->
                            intelligenceViewModel.decideCandidateRule(ruleId, approve = true)
                        },
                        onRejectRule = { ruleId ->
                            intelligenceViewModel.decideCandidateRule(ruleId, approve = false)
                        },
                        onSimulateSuggestion = { card ->
                            intelligenceViewModel.applySuggestedSimulation(card)
                            showWhatIfSheet = true
                        }
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                }

                RealizedRoiScorecardCard(
                    state = scorecardState,
                    onSelectHorizon = { days -> intelligenceViewModel.selectScorecardHorizon(days) },
                    onApproveCalibration = { intelligenceViewModel.decideCalibration(approve = true) },
                    onRejectCalibration = { intelligenceViewModel.decideCalibration(approve = false) },
                    onRefresh = { intelligenceViewModel.refreshScorecard(activeProfile.packId) }
                )

                Spacer(modifier = Modifier.height(22.dp))

                SectionLabel(text = "Motores Preditivos • ${activeProfile.shortLabel}")
                Spacer(modifier = Modifier.height(12.dp))

                // Grid 2x2 de Triggers Dinâmicos por Pack (Contenção 85-10-5)
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    activeProfile.triggers.chunked(2).forEach { rowTriggers ->
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(IntrinsicSize.Max),
                            horizontalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            rowTriggers.forEach { trigger ->
                                ExecutiveTriggerCard(
                                    trigger = trigger,
                                    modifier = Modifier
                                        .weight(1f)
                                        .fillMaxHeight(),
                                    onClick = {
                                        if (trigger.query == "VISION_SCANNER_TRIGGER") {
                                            showVisionScanner = true
                                        } else {
                                            onNavigateToChat(trigger.query)
                                        }
                                    }
                                )
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(22.dp))

                SectionLabel(text = "Consultas Rápidas")
                Spacer(modifier = Modifier.height(10.dp))

                LazyRow(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    contentPadding = PaddingValues(bottom = 8.dp)
                ) {
                    items(activeProfile.quickPrompts) { prompt ->
                        AuraChip(
                            label = prompt,
                            icon = Icons.Rounded.AutoAwesome,
                            onClick = { onNavigateToChat(prompt) }
                        )
                    }
                }

                Spacer(modifier = Modifier.height(20.dp))

                AuraGradientButton(
                    text = "Abrir Cockpit AURA",
                    onClick = { onNavigateToChat(null) },
                    icon = Icons.AutoMirrored.Rounded.Chat,
                    modifier = Modifier.fillMaxWidth()
                )

                Spacer(modifier = Modifier.height(20.dp))
            }
        }

        if (showVisionScanner) {
            AuraVisionBottomSheet(
                onDismiss = { showVisionScanner = false },
                onAuditWithAura = { telemetry ->
                    viewModel.submitVisionScan(telemetry)
                    onNavigateToChat(null)
                },
                scanner = viewModel.visionScanner
            )
        }

        if (showWhatIfSheet) {
            ModalBottomSheet(
                onDismissRequest = { showWhatIfSheet = false },
                containerColor = ObsidianLow,
                shape = RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp)
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .verticalScroll(rememberScrollState())
                        .navigationBarsPadding()
                        .padding(horizontal = 16.dp, vertical = 8.dp)
                        .padding(bottom = 24.dp)
                ) {
                    WhatIfSimulatorCard(
                        state = whatIfState,
                        onShocksChange = { intelligenceViewModel.onShocksChanged(it) },
                        onHorizonChange = { intelligenceViewModel.onHorizonChanged(it) },
                        onAuditWithAi = { prompt ->
                            showWhatIfSheet = false
                            onNavigateToChat(prompt)
                        },
                        onRetry = { intelligenceViewModel.recomputeNow() }
                    )
                }
            }
        }

        if (showSiliconSheet) {
            ModalBottomSheet(
                onDismissRequest = { showSiliconSheet = false },
                containerColor = ObsidianLow,
                shape = RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp)
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .navigationBarsPadding()
                        .padding(horizontal = 22.dp, vertical = 12.dp)
                        .padding(bottom = 24.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    SectionLabel("Diagnóstico de Silício & Rede")
                    Text(
                        text = hardwareStatus.marketingName,
                        style = MaterialTheme.typography.headlineSmall,
                        color = TextPrimary
                    )
                    Text(
                        text = "${hardwareStatus.activeAccelerator} • ${hardwareStatus.cpuCores} Cores • Android Keystore + TEE",
                        style = AuraTypographyExt.monoAudit,
                        color = TextSecondary
                    )
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        LiquidGlassPill(
                            text = "Inferência: ${"%.1f".format(hardwareStatus.lastInferenceLatencyMs)} ms",
                            accentColor = AuraEmerald
                        )
                        LiquidGlassPill(
                            text = "Pack: ${activeProfile.packId}",
                            accentColor = AuraCyan
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun ExecutiveTriggerCard(
    trigger: DomainTrigger,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    SpatialGlassCard(
        modifier = modifier,
        accent = trigger.accentColor,
        iridescentBorder = false,
        onClick = onClick,
        contentPadding = PaddingValues(14.dp)
    ) {
        Column(
            modifier = Modifier.fillMaxSize(),
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            Box(
                modifier = Modifier
                    .size(34.dp)
                    .clip(RoundedCornerShape(10.dp))
                    .background(trigger.accentColor.copy(alpha = 0.14f)),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = trigger.icon,
                    contentDescription = null,
                    tint = trigger.accentColor,
                    modifier = Modifier.size(18.dp)
                )
            }
            Spacer(modifier = Modifier.height(12.dp))
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(
                    text = trigger.title,
                    style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.SemiBold),
                    color = TextPrimary,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis
                )
                Text(
                    text = trigger.description,
                    style = MaterialTheme.typography.bodySmall.copy(lineHeight = 16.sp),
                    color = TextMuted,
                    maxLines = 3,
                    overflow = TextOverflow.Ellipsis
                )
            }
        }
    }
}
